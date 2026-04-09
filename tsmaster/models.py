"""
TSMaster数据模型
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class StepType(str, Enum):
    """测试步骤类型枚举"""

    INIT_FIFO = "init_fifo"
    SEND_SINGLE = "send_single"
    START_CYCLIC = "start_cyclic"
    STOP_CYCLIC = "stop_cyclic"
    WAIT = "wait"
    RECEIVE = "receive"
    SMART_CAR_SWITCH = "smart_car_switch"
    SMART_CAR_SWITCH_ALLTIME = "smart_car_switch_alltime"
    SMART_CAR_ZONE = "smart_car_zone"


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
    data: List[int] = Field(default_factory=list, description="报文数据字节列表")


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
