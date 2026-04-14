"""
TSMaster数据模型
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator


class StepType(str, Enum):
    """测试步骤类型枚举"""

    INIT = "init"
    SEND_SINGLE = "send_single"
    START_CYCLIC = "start_cyclic"
    STOP_CYCLIC = "stop_cyclic"
    WAIT = "wait"
    RECEIVE = "receive"
    SMART_CAR_SWITCH = "smart_car_switch"
    SMART_CAR_SWITCH_ALLTIME = "smart_car_switch_alltime"
    SMART_CAR_ZONE = "smart_car_zone"
    MACHINE_ARM_ROTATION = "machine_arm_rotation"
    NFC_START = "nfc_start"
    DECODE_SIGNALS = "decode_signals"
    CHECK_SIGNALS = "check_signals"


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
    data: List[Union[int, str]] = Field(default_factory=list, description="报文数据字节列表")

    @field_validator('data', mode='before')
    @classmethod
    def parse_hex_data(cls, v):
        if not isinstance(v, list):
            raise ValueError("data must be a list")
        result = []
        for item in v:
            if isinstance(item, str):
                item = item.strip()
                if item.startswith(('0x', '0X')):
                    item = int(item, 16)
                else:
                    item = int(item, 10)
            elif isinstance(item, int):
                pass  # keep as is
            else:
                raise ValueError(f"data items must be int or str, got {type(item)}")
            result.append(item)
        return result


class TestStep(BaseModel):
    """单个测试步骤"""

    step_id: str = Field(..., description="步骤唯一标识符")
    step_type: StepType = Field(..., description="步骤类型")
    order: int = Field(..., description="执行顺序")
    message: Optional[MessageFrame] = Field(None, description="报文配置")
    period_ms: Optional[int] = Field(
        None, ge=10, le=60000, description="周期发送间隔(毫秒)"
    )
    duration_ms: Optional[int] = Field(
        None, ge=10, le=60000, description="等待延时(毫秒)"
    )
    expected_ids: List[Union[int, str]] = Field(
        default_factory=list, description="期望接收的报文ID列表"
    )
    timeout_ms: Optional[int] = Field(
        default=1000, ge=100, le=60000, description="接收超时(毫秒)"
    )
    include_tx: bool = Field(default=True, description="是否包含发送报文")
    # 智能小车控制参数
    switch_value: Optional[int] = Field(
        None, ge=0, le=255, description="智能小车开关值"
    )
    keytime_ms: Optional[int] = Field(
        None, ge=0, le=5000, description="智能小车按键持续时间(毫秒)"
    )
    enable_disable: Optional[int] = Field(
        None, ge=0, le=255, description="智能小车持续开关启用/禁用标志"
    )
    zone_value: Optional[int] = Field(
        None, ge=0, le=255, description="智能小车区域控制值"
    )
    # 机械臂控制参数
    angle: Optional[int] = Field(
        None, ge=0, le=180, description="机械臂旋转角度 (0-180度)"
    )
    name: Optional[str] = Field(
        None, description="NFC测试名称标识"
    )
    # DECODE_SIGNALS 参数
    dbc_path: Optional[str] = Field(None, description="DBC文件路径")
    decode_message_ids: Optional[List[Union[int, str]]] = Field(
        default_factory=list, description="要解码的报文ID列表"
    )
    decode_timeout_ms: Optional[int] = Field(
        default=1000, ge=100, le=60000, description="解码超时(ms)"
    )
    decode_max_frames: Optional[int] = Field(
        default=10, ge=1, le=1000, description="最大解码帧数"
    )
    # CHECK_SIGNALS 参数
    check_dbc_path: Optional[str] = Field(None, description="CHECK_SIGNALS的DBC文件路径")
    check_message_ids: Optional[List[Union[int, str]]] = Field(
        default_factory=list, description="CHECK_SIGNALS的报文ID列表"
    )
    wait_before_check_ms: Optional[int] = Field(
        default=5000, ge=0, le=60000, description="CHECK_SIGNALS执行前等待时间(ms)"
    )
    check_lookback_ms: Optional[int] = Field(
        default=15000, ge=1000, le=300000, description="CHECK_SIGNALS检查回溯时间窗口(ms)，只检查这个时间窗口内的报文"
    )
    conditions: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="信号条件列表，格式: [{'signal': 'xxx', 'operator': '==', 'value': 3, 'hold_max_frames': 20, 'hold_duration_ms': 2000}]"
    )
    # 时序信号检查参数
    hold_duration_ms: Optional[int] = Field(
        None, ge=0, le=60000, description="信号必须保持的毫秒数"
    )
    hold_max_frames: Optional[int] = Field(
        None, ge=1, le=1000, description="信号必须保持的连续帧数"
    )
    tolerance_value: Optional[float] = Field(
        None, ge=0, description="比较值的容差范围（用于浮点比较）"
    )


class ECUSimulationScenario(BaseModel):
    """ECU仿真测试序列"""

    scenario_name: str = Field(..., description="测试场景名称")
    description: Optional[str] = Field(None, description="测试场景描述")
    channel: int = Field(default=0, ge=0, le=7, description="CAN通道号 (0-7)")
    steps: List[TestStep] = Field(..., description="测试步骤列表")


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


class SignalInput(BaseModel):
    """CAN信号输入"""

    signal: str = Field(..., description="信号名称")
    value: float = Field(..., description="信号值")


class EncodeResult(BaseModel):
    """CAN信号编码结果"""

    frame_id: int = Field(..., description="报文帧ID")
    message_name: str = Field(..., description="报文名称")
    data: List[int] = Field(..., description="编码后的报文数据字节列表")
