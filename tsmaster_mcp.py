#!/usr/bin/env python3
"""
MCP Server for TSMaster CAN/LIN Tool.

This server provides tools to interact with TSMaster via COM API,
including CAN/CANFD/LIN message transmission and reception.
"""

import asyncio
import pythoncom
import win32com.client
from win32com.client import VARIANT
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tsmaster_mcp")

_app: Optional[Any] = None
_com: Optional[Any] = None
_is_connected: bool = False


class CANMessageInput(BaseModel):
    channel: int = Field(default=0, description="CAN channel index (0-based)", ge=0, le=7)
    is_tx: bool = Field(default=True, description="True for transmit, False for receive")
    is_extended_id: bool = Field(default=False, description="True for extended ID (29-bit), False for standard (11-bit)")
    is_remote: bool = Field(default=False, description="True for remote frame")
    identifier: int = Field(..., description="CAN message ID (hex format)", ge=0, le=0x1FFFFFFF)
    dlc: int = Field(default=8, description="Data length code (0-8 for CAN, 0-64 for CANFD)", ge=0, le=64)
    data: List[int] = Field(default_factory=list, description="Message data bytes (0-255 each)")
    timestamp_us: int = Field(default=0, description="Message timestamp in microseconds", ge=0)


class ConnectInput(BaseModel):
    can_channel_count: int = Field(default=1, description="Number of CAN channels", ge=1, le=8)
    lin_channel_count: int = Field(default=0, description="Number of LIN channels", ge=0, le=8)
    can_baudrate: int = Field(default=500, description="CAN baudrate in kbps")
    can_fd_baudrate: int = Field(default=2000, description="CAN FD data baudrate in kbps")
    device_type: int = Field(default=3, description="Hardware device type (3=TOSUN)")
    device_subtype: int = Field(default=8, description="Device subtype (8=TC1014)")
    device_name: str = Field(default="TC1014", description="Device name")


class CANFDMessageInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    channel: int = Field(default=0, description="CAN FD channel index (0-based)", ge=0, le=7)
    is_tx: bool = Field(default=True, description="True for transmit, False for receive")
    is_extended_id: bool = Field(default=False, description="True for extended ID (29-bit), False for standard (11-bit)")
    is_edl: bool = Field(default=True, description="Extended data length (FD frame)")
    is_brs: bool = Field(default=False, description="Bit rate switch")
    is_esi: bool = Field(default=False, description="Error state indicator")
    identifier: int = Field(..., description="CAN FD message ID", ge=0, le=0x1FFFFFFF)
    dlc: int = Field(default=16, description="Data length code (10=64bytes)", ge=0, le=64)
    data: List[int] = Field(default_factory=list, description="Message data bytes")
    timestamp_us: int = Field(default=0, description="Message timestamp in microseconds")


class LINMessageInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    channel: int = Field(default=0, description="LIN channel index (0-based)", ge=0, le=7)
    is_tx: bool = Field(default=True, description="True for transmit, False for receive")
    identifier: int = Field(..., description="LIN message ID", ge=0, le=0x3F)
    dlc: int = Field(default=8, description="Data length (1-8)", ge=0, le=8)
    data: List[int] = Field(default_factory=list, description="Message data bytes")
    timestamp_us: int = Field(default=0, description="Message timestamp in microseconds")


class ReceiveCANInput(BaseModel):
    channel: int = Field(default=0, description="CAN channel to read from", ge=0, le=7)
    timeout_ms: int = Field(default=100, description="Timeout in milliseconds", ge=1, le=10000)


class EnableFIFOInput(BaseModel):
    channel: int = Field(default=0, description="Channel to enable FIFO for", ge=0, le=7)
    protocol: str = Field(default="CAN", description="Protocol: CAN, CANFD, or LIN")


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


@mcp.tool(
    name="tsmaster_connect",
    annotations={
        "title": "Connect to TSMaster",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
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
            _app.configure_baudrate_canfd(ch, params.can_baudrate, params.can_fd_baudrate, 0, 0, True)
        
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
        "openWorldHint": False
    }
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
    name="tsmaster_transmit_can",
    annotations={
        "title": "Transmit CAN Message",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def tsmaster_transmit_can(params: CANMessageInput) -> str:
    """Transmit a Classic CAN message asynchronously.
    
    This sends a CAN message on the specified channel. The message is transmitted
    once without waiting for acknowledgment.
    
    Args:
        params (CANMessageInput): Message parameters including channel, ID, data, etc.
    
    Returns:
        JSON string with transmission status
    """
    try:
        _ensure_connected()
        
        c = win32com.client.Record("TCAN", _app)
        c.FIdxChn = params.channel
        c.FIsTX = 1 if params.is_tx else 0
        c.FIsRemote = 1 if params.is_remote else 0
        c.FIsExtendedId = 1 if params.is_extended_id else 0
        c.FDLC = params.dlc
        c.FIdentifier = params.identifier
        c.FTimeUs = params.timestamp_us
        c.FDatas = _create_variant_array(params.data[:8] if len(params.data) >= 8 else params.data + [0] * (8 - len(params.data)))
        
        _com.transmit_can_async(c)
        
        return f'{{"status": "transmitted", "id": "0x{params.identifier:X}", "channel": {params.channel}, "dlc": {params.dlc}, "data": {params.data[:8]}}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


@mcp.tool(
    name="tsmaster_transmit_canfd",
    annotations={
        "title": "Transmit CAN FD Message",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def tsmaster_transmit_canfd(params: CANFDMessageInput) -> str:
    """Transmit a CAN FD message asynchronously.
    
    This sends a CAN FD message which supports longer data lengths (up to 64 bytes)
    and higher baudrates.
    
    Args:
        params (CANFDMessageInput): Message parameters including channel, ID, data, etc.
    
    Returns:
        JSON string with transmission status
    """
    try:
        _ensure_connected()
        
        cfd = win32com.client.Record("TCANFD", _app)
        cfd.FIdxChn = params.channel
        cfd.FIsTx = 1 if params.is_tx else 0
        cfd.FIsRemote = 0
        cfd.FIsExtendedId = 1 if params.is_extended_id else 0
        cfd.FIsEDL = 1 if params.is_edl else 0
        cfd.FIsBRS = 1 if params.is_brs else 0
        cfd.FIsESI = 1 if params.is_esi else 0
        cfd.FIdentifier = params.identifier
        cfd.FDLC = params.dlc
        cfd.FTimeUs = params.timestamp_us
        
        data_arr = params.data[:64] if len(params.data) >= 64 else params.data + [0] * (64 - len(params.data))
        cfd.FDatas = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, tuple(data_arr))
        
        _com.transmit_canfd_async(cfd)
        
        return f'{{"status": "transmitted", "id": "0x{params.identifier:X}", "channel": {params.channel}, "dlc": {params.dlc}, "is_fd": true, "is_brs": {params.is_brs}}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


@mcp.tool(
    name="tsmaster_transmit_lin",
    annotations={
        "title": "Transmit LIN Message",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def tsmaster_transmit_lin(params: LINMessageInput) -> str:
    """Transmit a LIN message asynchronously.
    
    This sends a LIN message on the specified channel.
    
    Args:
        params (LINMessageInput): Message parameters including channel, ID, data, etc.
    
    Returns:
        JSON string with transmission status
    """
    try:
        _ensure_connected()
        
        lin = win32com.client.Record("TLIBLIN", _app)
        lin.FIdxChn = params.channel
        lin.FIsTX = 1 if params.is_tx else 0
        lin.FIsError = 0
        lin.FIdentifier = params.identifier
        lin.FDLC = params.dlc
        lin.FTimeUs = params.timestamp_us
        
        data_arr = params.data[:8] if len(params.data) >= 8 else params.data + [0] * (8 - len(params.data))
        lin.FDatas = _create_variant_array(data_arr)
        
        _com.transmit_lin_async(lin)
        
        return f'{{"status": "transmitted", "id": {params.identifier}, "channel": {params.channel}, "dlc": {params.dlc}}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


@mcp.tool(
    name="tsmaster_receive_can",
    annotations={
        "title": "Receive CAN Message",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def tsmaster_receive_can(params: ReceiveCANInput) -> str:
    """Receive a CAN message from the FIFO buffer.
    
    This reads a CAN message from the specified channel's receive buffer.
    Call this after enabling receive FIFO and waiting for messages to arrive.
    
    Args:
        params (ReceiveCANInput): Channel and timeout parameters.
    
    Returns:
        JSON string with received message or empty result
    """
    try:
        _ensure_connected()
        
        a_idx_chn_req = params.channel
        a_include_tx = 1
        a_idx_chn_resp = 0
        a_is_remote = 0
        a_is_extended = 0
        a_dlc = 0
        a_identifier = 0
        a_timestamp_us = 0
        
        result = _com.fifo_receive_can_msg(
            a_idx_chn_req, a_include_tx,
            a_idx_chn_resp, a_is_remote, a_is_extended,
            a_dlc, a_identifier, a_timestamp_us
        )
        
        if result:
            return f'{{"status": "received", "channel": {params.channel}, "id": "0x{a_identifier:X}", "dlc": {a_dlc}, "timestamp_us": {a_timestamp_us}, "is_extended": {a_is_extended == 1}}}'
        else:
            return f'{{"status": "no_message", "channel": {params.channel}}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


@mcp.tool(
    name="tsmaster_enable_receive_fifo",
    annotations={
        "title": "Enable Receive FIFO",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def tsmaster_enable_receive_fifo(params: EnableFIFOInput) -> str:
    """Enable the receive FIFO for a specific channel.
    
    This enables receiving messages into the FIFO buffer where they can be
    read using the receive functions.
    
    Args:
        params (EnableFIFOInput): Channel and protocol parameters.
    
    Returns:
        JSON string with status
    """
    try:
        _ensure_connected()
        
        if params.protocol.upper() == "CAN":
            _com.fifo_enable_receive_fifo(params.channel, True)
        elif params.protocol.upper() == "CANFD":
            _com.fifo_enable_receive_fifo(params.channel, True)
        elif params.protocol.upper() == "LIN":
            _com.fifo_enable_receive_fifo(params.channel, True)
        
        return f'{{"status": "enabled", "channel": {params.channel}, "protocol": "{params.protocol}"}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


@mcp.tool(
    name="tsmaster_get_channel_count",
    annotations={
        "title": "Get Channel Count",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def tsmaster_get_channel_count(params: GetChannelCountInput) -> str:
    """Get the number of configured channels.
    
    Args:
        params (GetChannelCountInput): Protocol parameter.
    
    Returns:
        JSON string with channel count
    """
    try:
        _ensure_com_initialized()
        
        if params.protocol.upper() == "CAN":
            count = _app.get_can_channel_count()
        else:
            count = _app.get_lin_channel_count()
        
        return f'{{"protocol": "{params.protocol}", "count": {count}}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


@mcp.tool(
    name="tsmaster_get_status",
    annotations={
        "title": "Get TSMaster Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
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
