#!/usr/bin/env python3
"""
MCP Server for TSMaster CAN/LIN Tool.

This server provides tools to interact with TSMaster via COM API,
including CAN/CANFD/LIN message transmission and reception.
"""

import asyncio
import time
import pythoncom
import win32com.client
from win32com.client import VARIANT
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tsmaster_mcp")

_app: Optional[Any] = None
_com: Optional[Any] = None
_is_connected: bool = False


class CANMessageInput(BaseModel):
    channel: int = Field(
        default=0, description="CAN channel index (0-based)", ge=0, le=7
    )
    is_tx: bool = Field(
        default=True, description="True for transmit, False for receive"
    )
    is_extended_id: bool = Field(
        default=False,
        description="True for extended ID (29-bit), False for standard (11-bit)",
    )
    is_remote: bool = Field(default=False, description="True for remote frame")
    identifier: int = Field(
        ..., description="CAN message ID (hex format)", ge=0, le=0x1FFFFFFF
    )
    dlc: int = Field(
        default=8,
        description="Data length code (0-8 for CAN, 0-64 for CANFD)",
        ge=0,
        le=64,
    )
    data: List[int] = Field(
        default_factory=list, description="Message data bytes (0-255 each)"
    )
    timestamp_us: int = Field(
        default=0, description="Message timestamp in microseconds", ge=0
    )


class ConnectInput(BaseModel):
    can_channel_count: int = Field(
        default=1, description="Number of CAN channels", ge=1, le=8
    )
    lin_channel_count: int = Field(
        default=0, description="Number of LIN channels", ge=0, le=8
    )
    can_baudrate: int = Field(default=500, description="CAN baudrate in kbps")
    can_fd_baudrate: int = Field(
        default=2000, description="CAN FD data baudrate in kbps"
    )
    device_type: int = Field(default=3, description="Hardware device type (3=TOSUN)")
    device_subtype: int = Field(
        default=12, description="Device subtype (8=TC1014, 10=TC1026, 12=TC1012)"
    )
    device_name: str = Field(default="TC1014", description="Device name")


class CANFDMessageInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    channel: int = Field(
        default=0, description="CAN FD channel index (0-based)", ge=0, le=7
    )
    is_tx: bool = Field(
        default=True, description="True for transmit, False for receive"
    )
    is_extended_id: bool = Field(
        default=False,
        description="True for extended ID (29-bit), False for standard (11-bit)",
    )
    is_edl: bool = Field(default=True, description="Extended data length (FD frame)")
    is_brs: bool = Field(default=False, description="Bit rate switch")
    is_esi: bool = Field(default=False, description="Error state indicator")
    identifier: int = Field(..., description="CAN FD message ID", ge=0, le=0x1FFFFFFF)
    dlc: int = Field(
        default=16, description="Data length code (10=64bytes)", ge=0, le=64
    )
    data: List[int] = Field(default_factory=list, description="Message data bytes")
    timestamp_us: int = Field(
        default=0, description="Message timestamp in microseconds"
    )


class MonitorCANInput(BaseModel):
    channel: int = Field(default=0, description="CAN channel to monitor", ge=0, le=7)
    duration_ms: int = Field(
        default=1000,
        description="Monitoring duration in milliseconds",
        ge=100,
        le=60000,
    )


class TransmitReceiveInput(BaseModel):
    channel: int = Field(
        default=0, description="CAN FD channel index (0-based)", ge=0, le=7
    )
    is_extended_id: bool = Field(
        default=False, description="True for extended ID (29-bit)"
    )
    is_edl: bool = Field(default=True, description="Extended data length (FD frame)")
    is_brs: bool = Field(default=False, description="Bit rate switch")
    is_esi: bool = Field(default=False, description="Error state indicator")
    identifier: Union[int, str] = Field(
        ..., description="CAN FD message ID (int or hex string like '0x3040101')"
    )
    data: List[int] = Field(default_factory=list, description="Message data bytes")
    timeout_ms: int = Field(
        default=1000, description="Receive timeout in milliseconds", ge=100, le=60000
    )
    filter_ids: List[Union[int, str]] = Field(
        default_factory=list,
        description="Filter IDs to receive (empty = receive all), e.g. ['0x3040101']",
    )


class GetChannelCountInput(BaseModel):
    protocol: str = Field(default="CAN", description="Protocol: CAN or LIN")


def _ensure_com_initialized():
    global _app, _com
    pythoncom.CoInitialize()
    if _app is None:
        _app = win32com.client.Dispatch("TSMaster.TSApplication")
        _com = _app.TSCOM()


def _ensure_connected():
    global _is_connected
    _ensure_com_initialized()
    if not _is_connected:
        try:
            _app.connect()
            _is_connected = True
        except Exception:
            pass


def _create_variant_array(data: List[int]) -> Any:
    if not data:
        return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, tuple([0] * 8))
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, tuple(data))


def _parse_id(value: Union[int, str]) -> int:
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("0x") or value.startswith("0X"):
            return int(value, 16)
        return int(value, 10)
    return value


def _data_length_to_dlc(length: int) -> int:
    if length <= 8:
        return length
    elif length == 12:
        return 9
    elif length == 16:
        return 10
    elif length == 20:
        return 11
    elif length == 24:
        return 12
    elif length == 32:
        return 13
    elif length == 48:
        return 14
    elif length == 64:
        return 15
    else:
        return min(length, 64)


@mcp.tool(
    name="tsmaster_connect",
    annotations={
        "title": "Connect to TSMaster",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tsmaster_connect(params: ConnectInput) -> str:
    """Connect to TSMaster hardware and configure channels.

    This tool initializes TSMaster, sets up channel mapping, and connects to the hardware.
    Call this first before any other operations.

    Args:
        params (ConnectInput): Connection parameters including channel counts and baudrates.

    Returns:
        JSON string with connection status
    """
    try:
        _ensure_com_initialized()
        _app.set_can_channel_count(params.can_channel_count)
        _app.set_lin_channel_count(params.lin_channel_count)

        for ch in range(params.can_channel_count):
            r = win32com.client.Record("TTSMapping", _app)
            r.FAppName = "PythonApp"
            r.FAppChannelIndex = ch
            r.FAppChannelType = 0
            r.FHWIndex = 0
            r.FHWDeviceType = params.device_type
            r.FHWDeviceSubType = params.device_subtype
            r.FHWChannelIndex = ch
            r.FHWDeviceName = params.device_name
            r.FMappingDisabled = False
            _app.set_mapping(r)

        for ch in range(params.can_channel_count):
            _app.configure_baudrate_canfd(
                ch, params.can_baudrate, params.can_fd_baudrate, 1, 0, True
            )

        for ch in range(params.lin_channel_count):
            _app.configure_baudrate_lin(ch, 19.2, 3)

        _ensure_connected()

        return f'{{"status": "connected", "can_channels": {params.can_channel_count}, "lin_channels": {params.lin_channel_count}}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


@mcp.tool(
    name="tsmaster_disconnect",
    annotations={
        "title": "Disconnect from TSMaster",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tsmaster_disconnect() -> str:
    """Disconnect from TSMaster hardware.

    This disconnects from the TSMaster hardware and cleans up resources.

    Returns:
        JSON string with disconnection status
    """
    global _is_connected
    try:
        if _is_connected:
            _app.disconnect()
            _is_connected = False
        return '{"status": "disconnected"}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


@mcp.tool(
    name="tsmaster_transmit_and_receive",
    annotations={
        "title": "Transmit CAN FD and Receive Response",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def tsmaster_transmit_and_receive(params: TransmitReceiveInput) -> str:
    """Transmit a CAN FD message and wait for responses.

    This tool clears the receive buffer, enables FIFO, sends the specified message,
    then waits for and returns all received messages within the timeout period.

    Args:
        params (TransmitReceiveInput): Message parameters including channel, ID, data, and timeout.

    Returns:
        JSON string with transmission status and all received messages
    """
    try:
        _ensure_connected()

        _com.fifo_enable_receive_fifo()
        _com.fifo_clear_can_receive_buffers(params.channel)
        _com.fifo_clear_canfd_receive_buffers(params.channel)
        time.sleep(0.1)

        cfd = win32com.client.Record("TCANFD", _app)
        cfd.FIdxChn = params.channel
        cfd.FIsTX = 1
        cfd.FIsExtendedId = 1 if params.is_extended_id else 0
        cfd.FIsEDL = 1 if params.is_edl else 0
        cfd.FIsBRS = 1 if params.is_brs else 0
        cfd.FIsESI = 1 if params.is_esi else 0
        cfd.FIdentifier = _parse_id(params.identifier)
        data_len = len(params.data)
        cfd.FDLC = _data_length_to_dlc(data_len)
        cfd.FTimeUS = 0

        data_arr = (
            params.data[:64]
            if len(params.data) >= 64
            else params.data + [0] * (64 - len(params.data))
        )
        cfd.FDatas = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, tuple(data_arr))

        _com.transmit_canfd_async(cfd)

        messages = []
        end_time = time.time() * 1000 + params.timeout_ms

        while time.time() * 1000 < end_time:
            result = _com.fifo_receive_canfd_msg(params.channel, False)

            if result:
                (
                    success,
                    idx_chn_resp,
                    is_remote,
                    is_extended,
                    is_edl,
                    is_brs,
                    dlc,
                    identifier,
                    timestamp_us,
                    datas,
                ) = result

                if success and identifier > 0:
                    parsed_filter_ids = (
                        [_parse_id(fid) for fid in params.filter_ids]
                        if params.filter_ids
                        else []
                    )
                    if parsed_filter_ids and identifier not in parsed_filter_ids:
                        continue
                    data_list = [int(x) for x in datas.split(",")] if datas else []

                    messages.append(
                        {
                            "id": f"0x{identifier:X}",
                            "dlc": dlc,
                            "timestamp_us": timestamp_us,
                            "is_extended": bool(is_extended),
                            "is_fd": bool(is_edl),
                            "is_brs": bool(is_brs),
                            "data": data_list,
                        }
                    )

            time.sleep(0.01)

        return f'{{"status": "completed", "tx_id": "0x{_parse_id(params.identifier):X}", "tx_data_len": {data_len}, "received_count": {len(messages)}, "messages": {messages}}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


@mcp.tool(
    name="tsmaster_get_status",
    annotations={
        "title": "Get TSMaster Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tsmaster_get_status() -> str:
    """Get current TSMaster connection status and configuration.

    Returns:
        JSON string with current status
    """
    global _is_connected
    try:
        _ensure_com_initialized()

        can_count = _app.get_can_channel_count()
        lin_count = _app.get_lin_channel_count()

        return f'{{"connected": {_is_connected}, "can_channels": {can_count}, "lin_channels": {lin_count}}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


if __name__ == "__main__":
    mcp.run()
