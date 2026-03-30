#!/usr/bin/env python3
"""
MCP Server for TSMaster ECU Simulation.

本服务器提供ECU仿真测试功能，通过COM API执行CAN/CANFD报文收发测试。
仅包含tsmaster_run_simulation工具。
"""

import asyncio
import time
import json
from enum import Enum
import pythoncom
import win32com.client
from win32com.client import VARIANT
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tsmaster_mcp")

_app: Optional[Any] = None
_com: Optional[Any] = None
_is_connected: bool = False


# =============================================================================
# 数据模型
# =============================================================================


class StepType(str, Enum):
    """
    测试步骤类型枚举
    """

    INIT_FIFO = "init_fifo"  # 初始化FIFO（清空buffer，使能接收）
    SEND_SINGLE = "send_single"  # 单帧发送
    START_CYCLIC = "start_cyclic"  # 启动周期发送
    STOP_CYCLIC = "stop_cyclic"  # 停止周期发送
    WAIT = "wait"  # 等待延时
    RECEIVE = "receive"  # 接收验证（不清空buffer）
    POWER_ON = "power_on"  # 电源开启（预留）
    POWER_OFF = "power_off"  # 电源关闭（预留）
    RELAY_ON = "relay_on"  # 继电器闭合（预留）
    RELAY_OFF = "relay_off"  # 继电器断开（预留）


class MessageFrame(BaseModel):
    """CAN/CANFD报文结构"""

    channel: int = Field(default=0, ge=0, le=7, description="CAN通道号 (0-7)")
    is_extended_id: bool = Field(default=False, description="是否为扩展帧 (29-bit ID)")
    is_edl: bool = Field(default=True, description="是否为CANFD帧 (False=CAN2.0)")
    is_brs: bool = Field(default=False, description="位速率切换 (CANFD加速)")
    is_esi: bool = Field(default=False, description="错误状态指示位")
    identifier: Union[int, str] = Field(
        ..., description="报文ID (如'0x3040201'或整型50598529)"
    )
    data: List[int] = Field(
        default_factory=list, description="报文数据字节列表 (如[1,2,3]或[0x01,0x02])"
    )


class TestStep(BaseModel):
    """单个测试步骤"""

    step_id: str = Field(..., description="步骤唯一标识符 (如's1')")
    step_type: StepType = Field(
        ...,
        description="步骤类型: init_fifo/send_single/start_cyclic/stop_cyclic/wait/receive",
    )
    order: int = Field(..., description="执行顺序 (数字越小越先执行)")
    message: Optional[MessageFrame] = Field(
        None, description="报文配置 (send_single/start_cyclic/stop_cyclic步骤必需)"
    )
    period_ms: Optional[int] = Field(
        None, ge=10, le=60000, description="周期发送间隔 (毫秒, start_cyclic步骤必需)"
    )
    duration_ms: Optional[int] = Field(
        None, ge=10, le=60000, description="等待延时 (毫秒, wait步骤必需)"
    )
    expected_ids: List[Union[int, str]] = Field(
        default_factory=list, description="期望接收的报文ID列表 (如['0x3040101'])"
    )
    timeout_ms: Optional[int] = Field(
        default=1000, ge=100, le=60000, description="接收超时 (毫秒, receive步骤用)"
    )
    include_tx: bool = Field(
        default=True,
        description="是否包含发送报文 (True=包含自己发送的, False=只接收总线上的)",
    )


class ECUSimulationScenario(BaseModel):
    """ECU仿真测试序列"""

    scenario_name: str = Field(..., description="测试场景名称")
    description: Optional[str] = Field(None, description="测试场景描述")
    channel: int = Field(default=0, ge=0, le=7, description="CAN通道号 (0-7)")
    steps: List[TestStep] = Field(..., description="测试步骤列表，按order顺序执行")


class StepResult(BaseModel):
    """步骤执行结果"""

    step_id: str
    step_type: str
    status: str
    received_messages: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
    timestamp: str


class SimulationReport(BaseModel):
    """仿真测试报告"""

    scenario_name: str
    status: str
    total_steps: int
    passed_steps: int
    failed_steps: int
    step_results: List[StepResult]
    total_duration_ms: int


# =============================================================================
# 内部辅助函数
# =============================================================================


def _ensure_com_initialized():
    """初始化COM组件"""
    global _app, _com
    pythoncom.CoInitialize()
    if _app is None:
        _app = win32com.client.Dispatch("TSMaster.TSApplication")
        _com = _app.TSCOM()


def _ensure_connected():
    """确保已连接TSMaster硬件"""
    global _is_connected
    _ensure_com_initialized()
    if not _is_connected:
        try:
            _app.set_can_channel_count(1)
            _app.set_lin_channel_count(0)

            # 配置CAN通道映射
            r = win32com.client.Record("TTSMapping", _app)
            r.FAppName = "PythonApp"
            r.FAppChannelIndex = 0
            r.FAppChannelType = 0
            r.FHWIndex = 0
            r.FHWDeviceType = 3  # TOSUN
            r.FHWDeviceSubType = 12  # TC1012
            r.FHWChannelIndex = 0
            r.FHWDeviceName = "TC1014"
            r.FMappingDisabled = False
            _app.set_mapping(r)

            # 配置CANFD波特率
            _app.configure_baudrate_canfd(0, 500, 2000, 1, 0, True)

            _app.connect()
            _is_connected = True
        except Exception as e:
            print(f"Connection error: {e}")


def _parse_id(value: Union[int, str]) -> int:
    """解析报文ID为整型"""
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("0x") or value.startswith("0X"):
            return int(value, 16)
        return int(value, 10)
    return value


def _data_length_to_dlc(length: int) -> int:
    """将数据长度转换为DLC代码"""
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


def _transmit_single_canfd(
    channel: int,
    identifier: Union[int, str],
    data: List[int],
    is_extended_id: bool = False,
    is_brs: bool = False,
    is_esi: bool = False,
    is_edl: bool = True,
) -> bool:
    """发送单帧CANFD报文"""
    global _com
    try:
        cfd = win32com.client.Record("TCANFD", _app)
        cfd.FIdxChn = channel
        cfd.FIsTX = 1
        cfd.FIsExtendedId = 1 if is_extended_id else 0
        cfd.FIsEDL = 1 if is_edl else 0
        cfd.FIsBRS = 1 if is_brs else 0
        cfd.FIsESI = 1 if is_esi else 0
        cfd.FIdentifier = _parse_id(identifier)
        cfd.FDLC = _data_length_to_dlc(len(data))
        cfd.FTimeUS = 0
        data_arr = data[:64] if len(data) >= 64 else data + [0] * (64 - len(data))
        cfd.FDatas = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, tuple(data_arr))
        _com.transmit_canfd_async(cfd)
        return True
    except Exception:
        return False


def _start_cyclic_canfd(
    channel: int,
    identifier: Union[int, str],
    data: List[int],
    period_ms: int,
    is_extended_id: bool = False,
    is_brs: bool = False,
) -> bool:
    """启动周期发送CANFD报文"""
    global _com
    try:
        cfd = win32com.client.Record("TCANFD", _app)
        cfd.FIdxChn = channel
        cfd.FIsTX = 1
        cfd.FIsExtendedId = 1 if is_extended_id else 0
        cfd.FIsEDL = 1
        cfd.FIsBRS = 1 if is_brs else 0
        cfd.FIsESI = 0
        cfd.FIdentifier = _parse_id(identifier)
        cfd.FDLC = _data_length_to_dlc(len(data))
        cfd.FTimeUS = 0
        data_arr = data[:64] if len(data) >= 64 else data + [0] * (64 - len(data))
        cfd.FDatas = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, tuple(data_arr))
        _com.add_cyclic_msg_canfd(cfd, period_ms)
        return True
    except Exception as e:
        print(f"Cyclic send error: {e}")
        return False


def _stop_cyclic_canfd(
    channel: int, identifier: Union[int, str], is_extended_id: bool = False
) -> bool:
    """停止周期发送CANFD报文"""
    global _com, _is_connected
    print(
        f"[DEBUG] _stop_cyclic_canfd called: channel={channel}, id={identifier}, is_extended={is_extended_id}, _is_connected={_is_connected}"
    )
    try:
        _com.delete_cyclic_msg_canfd_verbose(
            channel, 1 if is_extended_id else 0, int(_parse_id(identifier))
        )
        print(f"[DEBUG] delete_cyclic_msg_canfd_verbose succeeded")
        return True
    except Exception as e:
        print(f"[DEBUG] Stop cyclic error: {e}")
        return False


def _start_canfd_reception(channel: int) -> bool:
    """开启CANFD接收（第一步）：使能FIFO并清空缓冲区"""
    global _com
    try:
        _com.fifo_enable_receive_fifo()
        _com.fifo_clear_canfd_receive_buffers(channel)
        return True
    except Exception:
        return False


def _get_canfd_messages(
    channel: int,
    timeout_ms: int,
    expected_ids: List[Union[int, str]] = None,
    max_messages: int = 1000,
    include_tx: bool = False,
) -> List[Dict[str, Any]]:
    """获取CANFD报文（第二步）：从FIFO读取报文

    Args:
        channel: CAN通道号
        timeout_ms: 超时时间
        expected_ids: 期望的报文ID列表
        max_messages: 最大消息数
        include_tx: 是否包含发送报文 (True=包含自己发送的, False=只接收总线上的)
    """
    global _com
    messages = []
    if expected_ids is None:
        expected_ids = []
    parsed_filter_ids = [_parse_id(fid) for fid in expected_ids]

    end_time = time.time() * 1000 + timeout_ms

    while time.time() * 1000 < end_time and len(messages) < max_messages:
        try:
            # 第二个参数: AIncludeTx - True=包含发送报文, False=只接收总线上的
            result = _com.fifo_receive_canfd_msg(channel, include_tx)
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
        except Exception:
            pass
        time.sleep(0.01)

    return messages


# =============================================================================
# 步骤执行器
# =============================================================================


def _execute_step(step: TestStep, channel: int) -> StepResult:
    """执行单个ECU仿真测试步骤"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    step_type_str = (
        step.step_type.value if isinstance(step.step_type, StepType) else step.step_type
    )

    try:
        if step.step_type == StepType.INIT_FIFO:
            success = _start_canfd_reception(channel)
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed" if success else "failed",
                timestamp=timestamp,
            )

        elif step.step_type == StepType.SEND_SINGLE:
            if not step.message:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No message configured",
                    timestamp=timestamp,
                )
            success = _transmit_single_canfd(
                channel=channel,
                identifier=step.message.identifier,
                data=step.message.data,
                is_extended_id=step.message.is_extended_id,
                is_brs=step.message.is_brs,
                is_esi=step.message.is_esi,
                is_edl=step.message.is_edl,
            )
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed" if success else "failed",
                timestamp=timestamp,
            )

        elif step.step_type == StepType.START_CYCLIC:
            if not step.message or step.period_ms is None:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No message or period_ms configured",
                    timestamp=timestamp,
                )
            success = _start_cyclic_canfd(
                channel=channel,
                identifier=step.message.identifier,
                data=step.message.data,
                period_ms=step.period_ms,
                is_extended_id=step.message.is_extended_id,
                is_brs=step.message.is_brs,
            )
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed" if success else "failed",
                timestamp=timestamp,
            )

        elif step.step_type == StepType.STOP_CYCLIC:
            if not step.message:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No message configured",
                    timestamp=timestamp,
                )
            success = _stop_cyclic_canfd(
                channel=channel,
                identifier=step.message.identifier,
                is_extended_id=step.message.is_extended_id,
            )
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed" if success else "failed",
                timestamp=timestamp,
            )

        elif step.step_type == StepType.WAIT:
            if step.duration_ms is None:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No duration_ms configured",
                    timestamp=timestamp,
                )
            time.sleep(step.duration_ms / 1000.0)
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed",
                timestamp=timestamp,
            )

        elif step.step_type == StepType.RECEIVE:
            # 注意：不调用_start_canfd_reception，因为那会清空buffer
            # 消息应该在上一步发送或等待时就已经到达FIFO了
            messages = _get_canfd_messages(
                channel=channel,
                timeout_ms=step.timeout_ms or 1000,
                expected_ids=step.expected_ids,
                include_tx=step.include_tx,
            )
            received_ids = [msg["id"] for msg in messages]
            expected_ids_parsed = (
                [f"0x{_parse_id(eid):X}" for eid in step.expected_ids]
                if step.expected_ids
                else []
            )

            if expected_ids_parsed:
                all_found = all(eid in received_ids for eid in expected_ids_parsed)
                status = "passed" if all_found else "failed"
                if not all_found:
                    missing = [
                        eid for eid in expected_ids_parsed if eid not in received_ids
                    ]
                    error_msg = f"Expected {expected_ids_parsed}, received {received_ids}. Missing: {missing}"
                else:
                    error_msg = None
            else:
                status = "passed"
                error_msg = None

            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status=status,
                received_messages=messages,
                error_message=error_msg,
                timestamp=timestamp,
            )

        elif step.step_type in (
            StepType.POWER_ON,
            StepType.POWER_OFF,
            StepType.RELAY_ON,
            StepType.RELAY_OFF,
        ):
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="skipped",
                error_message="Not implemented",
                timestamp=timestamp,
            )

        else:
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="failed",
                error_message=f"Unknown step type: {step.step_type}",
                timestamp=timestamp,
            )

    except Exception as e:
        return StepResult(
            step_id=step.step_id,
            step_type=step_type_str,
            status="error",
            error_message=str(e),
            timestamp=timestamp,
        )


# =============================================================================
# MCP工具
# =============================================================================


@mcp.tool(
    name="tsmaster_run_simulation",
    annotations={
        "title": "执行ECU仿真测试场景",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def tsmaster_run_simulation(scenario: ECUSimulationScenario) -> str:
    """
    执行ECU仿真测试序列

    按照指定顺序执行一系列测试步骤，模拟真实的ECU测试场景。

    支持的步骤类型：
    - init_fifo: 初始化FIFO（使能接收并清空buffer）
    - send_single: 发送单帧CAN/CANFD报文
    - start_cyclic: 启动周期报文发送
    - stop_cyclic: 停止周期报文发送
    - wait: 等待指定时长
    - receive: 接收并验证总线报文（从FIFO获取消息，不清空buffer）
             可通过 include_tx 参数选择是否包含发送的报文 (默认True=包含自己发送的)
    - power_on/power_off: 电源控制（预留）
    - relay_on/relay_off: 继电器控制（预留）

    Args:
        scenario: 包含测试场景名称、通道和步骤序列

    Returns:
        JSON字符串，包含完整测试报告：
        - scenario_name: 测试场景名称
        - status: 整体执行状态
        - total_steps: 总步骤数
        - passed_steps: 成功步骤数
        - failed_steps: 失败步骤数
        - skipped_steps: 跳过步骤数
        - total_duration_ms: 总执行时长
        - step_results: 每个步骤的详细结果列表
    """
    try:
        _ensure_connected()

        sorted_steps = sorted(scenario.steps, key=lambda s: s.order)
        step_results = []
        start_time = time.time() * 1000

        for step in sorted_steps:
            result = _execute_step(step, scenario.channel)
            step_results.append(result)

        end_time = time.time() * 1000
        total_duration = int(end_time - start_time)

        passed = sum(1 for r in step_results if r.status == "passed")
        failed = sum(1 for r in step_results if r.status in ("failed", "error"))
        skipped = sum(1 for r in step_results if r.status == "skipped")

        return json.dumps(
            {
                "scenario_name": scenario.scenario_name,
                "status": "completed",
                "total_steps": len(step_results),
                "passed_steps": passed,
                "failed_steps": failed,
                "skipped_steps": skipped,
                "total_duration_ms": total_duration,
                "step_results": [
                    {
                        "step_id": r.step_id,
                        "step_type": r.step_type,
                        "status": r.status,
                        "received_messages": r.received_messages,
                        "error_message": r.error_message,
                        "timestamp": r.timestamp,
                    }
                    for r in step_results
                ],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    mcp.run()
