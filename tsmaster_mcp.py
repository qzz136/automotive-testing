#!/usr/bin/env python3
"""
MCP Server for TSMaster CAN/LIN Tool.

本服务器提供与TSMaster交互的工具，通过COM API实现：
- CAN/CANFD/LIN报文收发
- ECU仿真测试序列执行
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

# 初始化FastMCP服务器
mcp = FastMCP("tsmaster_mcp")

# 全局变量：存储TSMaster应用实例和COM对象
_app: Optional[Any] = None  # TSMaster应用程序对象
_com: Optional[Any] = None  # TSMaster COM接口对象
_is_connected: bool = False  # 连接状态标志


# =============================================================================
# ECU仿真测试相关数据模型
# =============================================================================


class StepType(str, Enum):
    """
    测试步骤类型枚举

    定义了ECU仿真测试序列中可能包含的各种操作类型：
    - SEND_SINGLE: 单帧发送（发送一次CAN/CANFD报文）
    - START_CYCLIC: 启动周期发送（开始循环发送报文）
    - STOP_CYCLIC: 停止周期发送（停止循环发送报文）
    - WAIT: 等待延时（暂停执行一段时间）
    - RECEIVE: 接收验证（监听总线报文并验证）
    - POWER_ON: 电源开启（预留扩展）
    - POWER_OFF: 电源关闭（预留扩展）
    - RELAY_ON: 继电器闭合（预留扩展）
    - RELAY_OFF: 继电器断开（预留扩展）
    """

    SEND_SINGLE = "send_single"  # 单帧发送
    START_CYCLIC = "start_cyclic"  # 启动周期发送
    STOP_CYCLIC = "stop_cyclic"  # 停止周期发送
    WAIT = "wait"  # 等待延时
    RECEIVE = "receive"  # 接收验证
    POWER_ON = "power_on"  # 电源开启（预留）
    POWER_OFF = "power_off"  # 电源关闭（预留）
    RELAY_ON = "relay_on"  # 继电器闭合（预留）
    RELAY_OFF = "relay_off"  # 继电器断开（预留）


class MessageFrame(BaseModel):
    """
    CAN/CANFD报文结构体模型

    用于描述一条CAN或CANFD报文的所有属性：
    - channel: CAN通道号（0-7）
    - is_extended_id: 是否为扩展帧（29位ID）
    - is_edl: 是否为CANFD帧（扩展数据长度）
    - is_brs: 是否启用位速率切换
    - is_esi: 错误状态指示位
    - identifier: 报文ID（支持整型或hex字符串如'0x3040201'）
    - data: 报文数据字节列表
    """

    channel: int = Field(default=0, ge=0, le=7, description="CAN通道号 (0-7)")
    is_extended_id: bool = Field(default=False, description="是否为扩展帧 (29-bit ID)")
    is_edl: bool = Field(default=True, description="是否为CANFD帧 (扩展数据长度)")
    is_brs: bool = Field(default=False, description="位速率切换")
    is_esi: bool = Field(default=False, description="错误状态指示位")
    identifier: Union[int, str] = Field(..., description="报文ID (整型或hex字符串)")
    data: List[int] = Field(default_factory=list, description="报文数据字节列表")


class TestStep(BaseModel):
    """
    单个测试步骤模型

    定义仿真测试序列中的每一个独立步骤：
    - step_id: 步骤唯一标识符
    - step_type: 步骤类型（参考StepType枚举）
    - order: 执行顺序（数字越小越先执行）
    - message: 报文配置（发送类步骤必需）
    - period_ms: 周期发送的间隔（毫秒）
    - duration_ms: 等待延时（毫秒）
    - expected_ids: 期望接收的报文ID列表
    - timeout_ms: 接收超时时间（毫秒）
    - expected_data_patterns: 期望的数据模式（用于数据验证）
    """

    step_id: str = Field(..., description="步骤唯一标识符")
    step_type: StepType = Field(..., description="步骤执行类型")
    order: int = Field(..., description="执行顺序 (数字越小越先执行)")
    message: Optional[MessageFrame] = Field(
        None, description="报文配置 (发送类步骤必需)"
    )
    period_ms: Optional[int] = Field(
        None, ge=10, le=60000, description="周期发送间隔 (毫秒)"
    )
    duration_ms: Optional[int] = Field(
        None, ge=10, le=60000, description="等待延时 (毫秒)"
    )
    expected_ids: List[Union[int, str]] = Field(
        default_factory=list, description="期望接收的报文ID列表"
    )
    timeout_ms: Optional[int] = Field(
        default=1000, ge=100, le=60000, description="接收超时时间 (毫秒)"
    )
    expected_data_patterns: Optional[List[Dict[str, Any]]] = Field(
        None, description="期望的数据模式"
    )


class ECUSimulationScenario(BaseModel):
    """
    ECU仿真测试序列模型

    完整的ECU仿真测试场景，包含多个有序步骤：
    - scenario_name: 测试场景名称
    - description: 测试场景描述
    - channel: 使用的CAN通道号
    - steps: 测试步骤列表（按order排序执行）
    """

    scenario_name: str = Field(..., description="测试场景名称")
    description: Optional[str] = Field(None, description="测试场景描述")
    channel: int = Field(default=0, ge=0, le=7, description="CAN通道号 (0-7)")
    steps: List[TestStep] = Field(..., description="测试步骤序列")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "scenario_name": "ECU电源循环测试",
                "description": "测试ECU在电源循环后的CAN通信恢复",
                "channel": 0,
                "steps": [
                    {
                        "step_id": "s1",
                        "step_type": "receive",
                        "order": 0,
                        "expected_ids": ["0x100"],
                        "timeout_ms": 2000,
                    },
                    {
                        "step_id": "s2",
                        "step_type": "wait",
                        "order": 1,
                        "duration_ms": 1000,
                    },
                    {
                        "step_id": "s3",
                        "step_type": "send_single",
                        "order": 2,
                        "message": {"identifier": "0x200", "data": [1, 2, 3, 4]},
                    },
                    {
                        "step_id": "s4",
                        "step_type": "receive",
                        "order": 3,
                        "expected_ids": ["0x300"],
                        "timeout_ms": 1000,
                    },
                ],
            }
        },
    )


class StepResult(BaseModel):
    """
    单个步骤执行结果模型

    记录每个测试步骤的执行结果：
    - step_id: 步骤标识符
    - step_type: 步骤类型
    - status: 执行状态 (passed/failed/error/skipped)
    - received_messages: 接收到的报文列表（接收类步骤）
    - error_message: 错误信息（如有）
    - timestamp: 执行时间戳
    """

    step_id: str = Field(..., description="步骤标识符")
    step_type: str = Field(..., description="步骤类型")
    status: str = Field(..., description="执行状态 (passed/failed/error/skipped)")
    received_messages: List[Dict[str, Any]] = Field(
        default_factory=list, description="接收到的报文列表"
    )
    error_message: Optional[str] = Field(None, description="错误信息")
    timestamp: str = Field(..., description="执行时间戳")


class SimulationReport(BaseModel):
    """
    仿真测试报告模型

    完整的仿真测试执行报告：
    - scenario_name: 测试场景名称
    - status: 整体状态
    - total_steps: 总步骤数
    - passed_steps: 成功步骤数
    - failed_steps: 失败步骤数
    - step_results: 各步骤详细结果列表
    - total_duration_ms: 总执行时长（毫秒）
    """

    scenario_name: str = Field(..., description="测试场景名称")
    status: str = Field(..., description="整体状态")
    total_steps: int = Field(..., description="总步骤数")
    passed_steps: int = Field(..., description="成功步骤数")
    failed_steps: int = Field(..., description="失败步骤数")
    step_results: List[StepResult] = Field(..., description="各步骤详细结果")
    total_duration_ms: int = Field(..., description="总执行时长 (毫秒)")


# =============================================================================
# 原有数据模型（保留向后兼容）
# =============================================================================


class CANMessageInput(BaseModel):
    """CAN报文输入模型（传统CAN 2.0）"""

    channel: int = Field(default=0, description="CAN通道号 (0-7)", ge=0, le=7)
    is_tx: bool = Field(default=True, description="True=发送, False=接收")
    is_extended_id: bool = Field(default=False, description="是否为扩展帧 (29-bit)")
    is_remote: bool = Field(default=False, description="是否为远程帧")
    identifier: int = Field(..., description="CAN报文ID", ge=0, le=0x1FFFFFFF)
    dlc: int = Field(default=8, description="数据长度 (0-8)", ge=0, le=64)
    data: List[int] = Field(default_factory=list, description="报文数据字节 (0-255)")
    timestamp_us: int = Field(default=0, description="时间戳 (微秒)", ge=0)


class ConnectInput(BaseModel):
    """
    TSMaster连接参数模型

    用于配置与TSMaster硬件的连接：
    - can_channel_count: CAN通道数量 (1-8)
    - lin_channel_count: LIN通道数量 (0-8)
    - can_baudrate: CAN波特率 (kbps)
    - can_fd_baudrate: CANFD数据场波特率 (kbps)
    - device_type: 硬件设备类型 (3=TOSUN)
    - device_subtype: 设备子类型 (8=TC1014, 10=TC1026, 12=TC1012)
    - device_name: 设备名称
    """

    can_channel_count: int = Field(default=1, description="CAN通道数量", ge=1, le=8)
    lin_channel_count: int = Field(default=0, description="LIN通道数量", ge=0, le=8)
    can_baudrate: int = Field(default=500, description="CAN波特率 (kbps)")
    can_fd_baudrate: int = Field(default=2000, description="CANFD数据场波特率 (kbps)")
    device_type: int = Field(default=3, description="硬件设备类型 (3=TOSUN)")
    device_subtype: int = Field(
        default=12, description="设备子类型 (8=TC1014, 10=TC1026, 12=TC1012)"
    )
    device_name: str = Field(default="TC1014", description="设备名称")


class CANFDMessageInput(BaseModel):
    """CANFD报文输入模型"""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    channel: int = Field(default=0, description="CAN FD通道号 (0-7)", ge=0, le=7)
    is_tx: bool = Field(default=True, description="True=发送, False=接收")
    is_extended_id: bool = Field(default=False, description="是否为扩展帧 (29-bit)")
    is_edl: bool = Field(default=True, description="是否为CANFD帧")
    is_brs: bool = Field(default=False, description="位速率切换")
    is_esi: bool = Field(default=False, description="错误状态指示位")
    identifier: int = Field(..., description="CAN FD报文ID", ge=0, le=0x1FFFFFFF)
    dlc: int = Field(default=16, description="数据长度代码 (10=64bytes)", ge=0, le=64)
    data: List[int] = Field(default_factory=list, description="报文数据字节")
    timestamp_us: int = Field(default=0, description="时间戳 (微秒)")


class MonitorCANInput(BaseModel):
    """CAN总线监控输入模型"""

    channel: int = Field(default=0, description="监控的CAN通道 (0-7)", ge=0, le=7)
    duration_ms: int = Field(
        default=1000, description="监控时长 (毫秒)", ge=100, le=60000
    )


class TransmitReceiveInput(BaseModel):
    """
    发送并接收输入模型

    用于发送CANFD报文并等待响应：
    - channel: CANFD通道号 (0-7)
    - is_extended_id: 是否为扩展帧
    - is_edl: 是否为CANFD帧
    - is_brs: 位速率切换
    - is_esi: 错误状态指示位
    - identifier: 报文ID (整型或hex字符串)
    - data: 报文数据
    - timeout_ms: 接收超时 (毫秒)
    - filter_ids: 只接收指定ID的报文（空=接收所有）
    """

    channel: int = Field(default=0, description="CAN FD通道号 (0-7)", ge=0, le=7)
    is_extended_id: bool = Field(default=False, description="是否为扩展帧 (29-bit)")
    is_edl: bool = Field(default=True, description="扩展数据长度 (FD帧)")
    is_brs: bool = Field(default=False, description="位速率切换")
    is_esi: bool = Field(default=False, description="错误状态指示位")
    identifier: Union[int, str] = Field(
        ..., description="报文ID (整型或hex字符串如'0x3040101')"
    )
    data: List[int] = Field(default_factory=list, description="报文数据字节")
    timeout_ms: int = Field(
        default=1000, description="接收超时 (毫秒)", ge=100, le=60000
    )
    filter_ids: List[Union[int, str]] = Field(
        default_factory=list, description="过滤ID列表 (空=接收所有)"
    )


class GetChannelCountInput(BaseModel):
    """获取通道数量输入模型"""

    protocol: str = Field(default="CAN", description="协议类型: CAN 或 LIN")


# =============================================================================
# 内部辅助函数
# =============================================================================


def _ensure_com_initialized():
    """
    确保COM组件已初始化

    初始化Python COM环境并创建TSMaster应用程序实例。
    这是使用TSMaster API前的必要步骤。
    全局变量_app和_com会被初始化。
    """
    global _app, _com
    pythoncom.CoInitialize()  # 初始化Python COM环境
    if _app is None:
        # 创建TSMaster应用程序对象
        _app = win32com.client.Dispatch("TSMaster.TSApplication")
        # 获取TSMaster COM接口
        _com = _app.TSCOM()


def _ensure_connected():
    """
    确保已连接到TSMaster硬件

    检查连接状态，如未连接则尝试连接。
    会调用_ensure_com_initialized确保COM组件已就绪。
    """
    global _is_connected
    _ensure_com_initialized()
    if not _is_connected:
        try:
            _app.connect()  # 连接到TSMaster硬件
            _is_connected = True
        except Exception:
            pass


def _create_variant_array(data: List[int]) -> Any:
    """
    创建COM VARIANT字节数组

    将Python字节列表转换为COM VARIANT数组格式，
    用于与TSMaster API交互。

    Args:
        data: 字节数据列表

    Returns:
        COM VARIANT数组对象
    """
    if not data:
        # 空数据返回8字节零数组
        return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, tuple([0] * 8))
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, tuple(data))


def _parse_id(value: Union[int, str]) -> int:
    """
    解析报文ID为整型

    支持整型或hex字符串格式的ID输入。

    Args:
        value: ID值（整型或hex字符串如'0x3040201'）

    Returns:
        整型ID值

    Examples:
        >>> _parse_id(0x123)
        291
        >>> _parse_id('0x3040201')
        50598529
        >>> _parse_id('3040201')
        50598529
    """
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("0x") or value.startswith("0X"):
            return int(value, 16)  # hex格式
        return int(value, 10)  # 十进制格式
    return value


def _data_length_to_dlc(length: int) -> int:
    """
    将数据长度转换为DLC代码

    CANFD协议使用DLC（Data Length Code）来表示数据长度，
    该函数将实际字节数转换为对应的DLC值。

    Args:
        length: 实际数据字节数 (0-64)

    Returns:
        DLC代码值 (0-15)

    Note:
        DLC 0-8 直接表示字节数
        DLC 9-15 对应固定字节数: 9=12, 10=16, 11=20, 12=24, 13=32, 14=48, 15=64
    """
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


# =============================================================================
# CANFD报文发送/接收函数
# =============================================================================


def _transmit_single_canfd(
    channel: int,
    identifier: Union[int, str],
    data: List[int],
    is_extended_id: bool = False,
    is_brs: bool = False,
    is_esi: bool = False,
    is_edl: bool = True,
) -> bool:
    """
    发送单帧CANFD报文

    异步发送一条CANFD报文到指定通道。

    Args:
        channel: CAN通道号 (0-7)
        identifier: 报文ID (整型或hex字符串)
        data: 报文数据字节列表
        is_extended_id: 是否为扩展帧 (29-bit ID)
        is_brs: 是否启用位速率切换
        is_esi: 错误状态指示位
        is_edl: 是否为CANFD帧

    Returns:
        True=发送成功, False=发送失败
    """
    global _com
    try:
        # 创建CANFD报文结构体
        cfd = win32com.client.Record("TCANFD", _app)
        cfd.FIdxChn = channel  # 通道号
        cfd.FIsTX = 1  # 发送方向
        cfd.FIsExtendedId = 1 if is_extended_id else 0  # 扩展帧标志
        cfd.FIsEDL = 1 if is_edl else 0  # CANFD帧标志
        cfd.FIsBRS = 1 if is_brs else 0  # 位速率切换
        cfd.FIsESI = 1 if is_esi else 0  # 错误状态指示
        cfd.FIdentifier = _parse_id(identifier)  # 报文ID
        data_len = len(data)
        cfd.FDLC = _data_length_to_dlc(data_len)  # DLC代码
        cfd.FTimeUS = 0  # 时间戳

        # 填充数据（不足64字节则补0）
        data_arr = data[:64] if len(data) >= 64 else data + [0] * (64 - len(data))
        cfd.FDatas = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, tuple(data_arr))

        # 异步发送报文
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
    """
    启动周期发送CANFD报文

    开始循环发送指定的CANFD报文，报文会按固定周期自动发送，
    直到调用_stop_cyclic_canfd停止。

    Args:
        channel: CAN通道号 (0-7)
        identifier: 报文ID (整型或hex字符串)
        data: 报文数据字节列表
        period_ms: 发送周期 (毫秒, 10-60000)
        is_extended_id: 是否为扩展帧
        is_brs: 是否启用位速率切换

    Returns:
        True=启动成功, False=启动失败
    """
    global _com
    try:
        _com.add_cyclic_msg_canfd_verbose(
            channel,  # 通道号
            1 if is_extended_id else 0,  # 扩展帧标志
            int(_parse_id(identifier)),  # 报文ID
            len(data),  # 数据长度
            ",".join(str(b) for b in data),  # 数据（逗号分隔字符串）
            period_ms,  # 周期（毫秒）
        )
        return True
    except Exception:
        return False


def _stop_cyclic_canfd(
    channel: int, identifier: Union[int, str], is_extended_id: bool = False
) -> bool:
    """
    停止周期发送CANFD报文

    停止之前通过_start_cyclic_canfd启动的周期发送。

    Args:
        channel: CAN通道号 (0-7)
        identifier: 报文ID (整型或hex字符串)
        is_extended_id: 是否为扩展帧

    Returns:
        True=停止成功, False=停止失败
    """
    global _com
    try:
        _com.delete_cyclic_msg_canfd_verbose(
            channel, 1 if is_extended_id else 0, int(_parse_id(identifier))
        )
        return True
    except Exception:
        return False


def _start_canfd_reception(channel: int) -> bool:
    """
    开启CANFD接收（第一步）

    使能FIFO接收模式并清空接收缓冲区。
    调用此函数后，CANFD报文将被缓存到接收FIFO中。
    注意：此函数只开启接收，不获取报文。

    Args:
        channel: CAN通道号 (0-7)

    Returns:
        True=开启成功, False=开启失败
    """
    global _com
    try:
        _com.fifo_enable_receive_fifo()  # 使能接收FIFO
        _com.fifo_clear_canfd_receive_buffers(channel)  # 清空接收缓冲区
        return True
    except Exception:
        return False


def _get_canfd_messages(
    channel: int,
    timeout_ms: int,
    expected_ids: List[Union[int, str]] = None,
    max_messages: int = 1000,
) -> List[Dict[str, Any]]:
    """
    获取CANFD报文（第二步）

    从FIFO缓冲区获取已接收的CANFD报文，支持ID过滤。
    注意：需要先调用_start_canfd_reception开启接收。

    Args:
        channel: CAN通道号 (0-7)
        timeout_ms: 接收超时时间 (毫秒)
        expected_ids: 期望接收的报文ID列表（空=接收所有）
        max_messages: 最大接收消息数

    Returns:
        接收到的报文列表，每条报文包含:
        - id: 报文ID (hex字符串)
        - dlc: 数据长度代码
        - timestamp_us: 时间戳 (微秒)
        - is_extended: 是否为扩展帧
        - is_fd: 是否为CANFD帧
        - is_brs: 是否启用位速率切换
        - data: 数据字节列表
    """
    global _com
    messages = []
    if expected_ids is None:
        expected_ids = []
    # 解析期望的ID列表
    parsed_filter_ids = [_parse_id(fid) for fid in expected_ids]

    end_time = time.time() * 1000 + timeout_ms

    while time.time() * 1000 < end_time and len(messages) < max_messages:
        try:
            result = _com.fifo_receive_canfd_msg(channel, False)
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
                    # ID过滤
                    if parsed_filter_ids and identifier not in parsed_filter_ids:
                        continue
                    # 解析数据
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
# ECU仿真测试步骤执行器
# =============================================================================


def _execute_step(step: TestStep, channel: int) -> StepResult:
    """
    执行单个ECU仿真测试步骤

    根据步骤类型执行相应的操作：
    - SEND_SINGLE: 发送单帧报文
    - START_CYCLIC: 启动周期发送
    - STOP_CYCLIC: 停止周期发送
    - WAIT: 等待延时
    - RECEIVE: 接收并验证报文
    - POWER_ON/OFF: 电源控制（预留）
    - RELAY_ON/OFF: 继电器控制（预留）

    Args:
        step: 测试步骤定义
        channel: CAN通道号

    Returns:
        StepResult: 步骤执行结果
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    step_type_str = (
        step.step_type.value if isinstance(step.step_type, StepType) else step.step_type
    )

    try:
        # ===================== 单帧发送 =====================
        if step.step_type == StepType.SEND_SINGLE:
            if not step.message:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No message configured for send_single step",
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

        # ===================== 启动周期发送 =====================
        elif step.step_type == StepType.START_CYCLIC:
            if not step.message or step.period_ms is None:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No message or period_ms configured for start_cyclic step",
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

        # ===================== 停止周期发送 =====================
        elif step.step_type == StepType.STOP_CYCLIC:
            if not step.message:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No message configured for stop_cyclic step",
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

        # ===================== 等待延时 =====================
        elif step.step_type == StepType.WAIT:
            if step.duration_ms is None:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No duration_ms configured for wait step",
                    timestamp=timestamp,
                )
            time.sleep(step.duration_ms / 1000.0)
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed",
                timestamp=timestamp,
            )

        # ===================== 接收验证 =====================
        elif step.step_type == StepType.RECEIVE:
            # 第一步：开启接收
            _start_canfd_reception(channel)
            # 第二步：获取报文
            messages = _get_canfd_messages(
                channel=channel,
                timeout_ms=step.timeout_ms or 1000,
                expected_ids=step.expected_ids,
            )
            received_ids = [msg["id"] for msg in messages]
            expected_ids_parsed = (
                [f"0x{_parse_id(eid):X}" for eid in step.expected_ids]
                if step.expected_ids
                else []
            )

            # 验证是否收到期望的报文ID
            if expected_ids_parsed:
                all_found = all(eid in received_ids for eid in expected_ids_parsed)
                status = "passed" if all_found else "failed"
                if not all_found:
                    missing = [
                        eid for eid in expected_ids_parsed if eid not in received_ids
                    ]
                    error_msg = f"Expected IDs {expected_ids_parsed}, but only received {received_ids}. Missing: {missing}"
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

        # ===================== 电源控制（预留） =====================
        elif step.step_type == StepType.POWER_ON:
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="skipped",
                error_message="Power control not implemented - hardware extension required",
                timestamp=timestamp,
            )

        elif step.step_type == StepType.POWER_OFF:
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="skipped",
                error_message="Power control not implemented - hardware extension required",
                timestamp=timestamp,
            )

        # ===================== 继电器控制（预留） =====================
        elif step.step_type == StepType.RELAY_ON:
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="skipped",
                error_message="Relay control not implemented - hardware extension required",
                timestamp=timestamp,
            )

        elif step.step_type == StepType.RELAY_OFF:
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="skipped",
                error_message="Relay control not implemented - hardware extension required",
                timestamp=timestamp,
            )

        # ===================== 未知步骤类型 =====================
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
# MCP工具定义
# =============================================================================


@mcp.tool(
    name="tsmaster_connect",
    annotations={
        "title": "连接TSMaster硬件",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tsmaster_connect(params: ConnectInput) -> str:
    """
    连接TSMaster硬件并配置通道

    初始化TSMaster，设置CAN/LIN通道映射和波特率参数。
    这是使用其他TSMaster工具前的必要第一步。

    Args:
        params (ConnectInput): 连接参数，包含通道数量、波特率、设备类型等

    Returns:
        JSON字符串，包含连接状态和通道数量信息
    """
    try:
        _ensure_com_initialized()
        _app.set_can_channel_count(params.can_channel_count)
        _app.set_lin_channel_count(params.lin_channel_count)

        # 配置CAN通道映射
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

        # 配置CANFD波特率
        for ch in range(params.can_channel_count):
            _app.configure_baudrate_canfd(
                ch, params.can_baudrate, params.can_fd_baudrate, 1, 0, True
            )

        # 配置LIN波特率
        for ch in range(params.lin_channel_count):
            _app.configure_baudrate_lin(ch, 19.2, 3)

        _ensure_connected()

        return f'{{"status": "connected", "can_channels": {params.can_channel_count}, "lin_channels": {params.lin_channel_count}}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


@mcp.tool(
    name="tsmaster_disconnect",
    annotations={
        "title": "断开TSMaster连接",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tsmaster_disconnect() -> str:
    """
    断开TSMaster硬件连接

    断开与TSMaster硬件的连接，释放资源。

    Returns:
        JSON字符串，包含断开状态
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
        "title": "发送CANFD报文并接收响应",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def tsmaster_transmit_and_receive(params: TransmitReceiveInput) -> str:
    """
    发送CANFD报文并等待响应

    清空接收缓冲区，使能FIFO，发送指定报文，
    然后在超时时间内接收所有总线上的报文。

    Args:
        params (TransmitReceiveInput): 报文参数，包含通道、ID、数据、超时等

    Returns:
        JSON字符串，包含发送状态和接收到的报文列表
    """
    try:
        _ensure_connected()

        _com.fifo_enable_receive_fifo()
        _com.fifo_clear_can_receive_buffers(params.channel)
        _com.fifo_clear_canfd_receive_buffers(params.channel)
        time.sleep(0.1)

        # 构建CANFD报文
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

        # 发送报文
        _com.transmit_canfd_async(cfd)

        # 接收响应
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
        "title": "获取TSMaster状态",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tsmaster_get_status() -> str:
    """
    获取TSMaster当前状态和配置

    返回当前连接状态和已配置的CAN/LIN通道数量。

    Returns:
        JSON字符串，包含连接状态和通道数量
    """
    global _is_connected
    try:
        _ensure_com_initialized()

        can_count = _app.get_can_channel_count()
        lin_count = _app.get_lin_channel_count()

        return f'{{"connected": {_is_connected}, "can_channels": {can_count}, "lin_channels": {lin_count}}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


class StartReceptionInput(BaseModel):
    """
    开启接收输入模型

    用于开启CANFD接收功能，清空接收缓冲区并使能FIFO。
    """

    channel: int = Field(default=0, description="CAN通道号 (0-7)", ge=0, le=7)


class ReceiveMessagesInput(BaseModel):
    """
    获取接收消息输入模型

    用于从FIFO获取已接收的CANFD报文。
    注意：需要先调用tsmaster_start_reception开启接收。
    """

    channel: int = Field(default=0, description="CAN通道号 (0-7)", ge=0, le=7)
    timeout_ms: int = Field(
        default=1000, description="接收超时 (毫秒)", ge=100, le=60000
    )
    expected_ids: List[Union[int, str]] = Field(
        default_factory=list, description="期望接收的报文ID列表 (空=接收所有)"
    )


@mcp.tool(
    name="tsmaster_start_reception",
    annotations={
        "title": "开启CANFD接收",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tsmaster_start_reception(params: StartReceptionInput) -> str:
    """
    开启CANFD接收（第一步）

    使能FIFO接收模式并清空接收缓冲区。
    调用此函数后，CANFD报文将被缓存到接收FIFO中。

    使用流程：
    1. 调用 tsmaster_start_reception 开启接收
    2. 执行其他操作（发送报文、等待等）
    3. 调用 tsmaster_receive 获取接收结果

    与tsmaster_receive配合使用，实现先开启接收再获取结果的分离式接收模式，
    适用于需要先启动监听再发送命令的场景（如ECU查询场景）。

    Args:
        params (StartReceptionInput): 包含通道号

    Returns:
        JSON字符串，包含开启状态
    """
    try:
        _ensure_connected()
        success = _start_canfd_reception(params.channel)
        return json.dumps(
            {
                "status": "success" if success else "failed",
                "action": "start_reception",
                "channel": params.channel,
            }
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool(
    name="tsmaster_receive",
    annotations={
        "title": "获取CANFD接收结果",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def tsmaster_receive(params: ReceiveMessagesInput) -> str:
    """
    获取CANFD接收结果（第二步）

    从FIFO缓冲区获取已接收的CANFD报文，支持ID过滤。
    注意：需要先调用tsmaster_start_reception开启接收。

    使用流程：
    1. 调用 tsmaster_start_reception 开启接收
    2. 执行其他操作（发送报文、等待等）
    3. 调用 tsmaster_receive 获取接收结果

    Args:
        params (ReceiveMessagesInput): 包含通道号、超时时间和过滤ID

    Returns:
        JSON字符串，包含接收到的报文列表:
        - status: 执行状态
        - channel: 通道号
        - received_count: 接收报文数量
        - messages: 报文列表，每条包含id、dlc、timestamp_us、data等
    """
    try:
        _ensure_connected()
        messages = _get_canfd_messages(
            channel=params.channel,
            timeout_ms=params.timeout_ms,
            expected_ids=params.expected_ids,
        )
        return json.dumps(
            {
                "status": "completed",
                "channel": params.channel,
                "received_count": len(messages),
                "messages": messages,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


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
    支持的步骤类型包括：
    - send_single: 发送单帧CAN/CANFD报文
    - start_cyclic: 启动周期报文发送
    - stop_cyclic: 停止周期报文发送
    - wait: 等待指定时长
    - receive: 接收并验证总线报文（两步式：先清空buffer并使能FIFO，再获取报文）
    - power_on/power_off: 电源控制（预留扩展）
    - relay_on/relay_off: 继电器控制（预留扩展）

    receive步骤说明：
    该步骤内部自动执行两步操作：
    1. 调用fifo_enable_receive_fifo使能接收，调用fifo_clear清空缓冲区
    2. 在超时时间内轮询fifo_receive_canfd_msg获取报文

    对于需要先开启接收再发送的场景（如ECU查询），建议：
    - 使用独立的tsmaster_start_reception + tsmaster_receive工具
    - 或在仿真序列中先执行一个expected_ids为空的receive步骤来初始化接收

    Args:
        scenario (ECUSimulationScenario): 包含测试场景名称、通道和步骤序列

    Returns:
        JSON字符串，包含完整的测试报告，包括：
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

        # 按order字段排序步骤
        sorted_steps = sorted(scenario.steps, key=lambda s: s.order)

        step_results = []
        start_time = time.time() * 1000

        # 依次执行每个步骤
        for step in sorted_steps:
            result = _execute_step(step, scenario.channel)
            step_results.append(result)

        end_time = time.time() * 1000
        total_duration = int(end_time - start_time)

        # 统计执行结果
        passed = sum(1 for r in step_results if r.status == "passed")
        failed = sum(1 for r in step_results if r.status in ("failed", "error"))
        skipped = sum(1 for r in step_results if r.status == "skipped")

        report = SimulationReport(
            scenario_name=scenario.scenario_name,
            status="completed",
            total_steps=len(step_results),
            passed_steps=passed,
            failed_steps=failed,
            step_results=step_results,
            total_duration_ms=total_duration,
        )

        # 返回JSON格式的测试报告
        return json.dumps(
            {
                "scenario_name": report.scenario_name,
                "status": report.status,
                "total_steps": report.total_steps,
                "passed_steps": report.passed_steps,
                "failed_steps": report.failed_steps,
                "skipped_steps": skipped,
                "total_duration_ms": report.total_duration_ms,
                "step_results": [
                    {
                        "step_id": r.step_id,
                        "step_type": r.step_type,
                        "status": r.status,
                        "received_messages": r.received_messages,
                        "error_message": r.error_message,
                        "timestamp": r.timestamp,
                    }
                    for r in report.step_results
                ],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(
            {
                "status": "error",
                "message": str(e),
            }
        )


if __name__ == "__main__":
    mcp.run()
