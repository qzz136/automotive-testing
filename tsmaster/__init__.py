"""
TSMaster模块 - ECU仿真测试功能
"""

from tsmaster.models import (
    StepType,
    MessageFrame,
    TestStep,
    ECUSimulationScenario,
    StepResult,
    SimulationReport,
)

from tsmaster.connection import (
    _ensure_com_initialized,
    _ensure_connected,
    _app,
    _com,
    _is_connected,
)

from tsmaster.api import (
    _transmit_single_canfd,
    _start_cyclic_canfd,
    _stop_cyclic_canfd,
    _stop_all_cyclic_messages,
    _start_canfd_reception,
    _get_canfd_messages,
    _parse_id,
    _data_length_to_dlc,
)

from tsmaster.executor import _execute_step

__all__ = [
    "StepType",
    "MessageFrame",
    "TestStep",
    "ECUSimulationScenario",
    "StepResult",
    "SimulationReport",
    "_ensure_com_initialized",
    "_ensure_connected",
    "_app",
    "_com",
    "_is_connected",
    "_transmit_single_canfd",
    "_start_cyclic_canfd",
    "_stop_cyclic_canfd",
    "_start_canfd_reception",
    "_get_canfd_messages",
    "_parse_id",
    "_data_length_to_dlc",
    "_execute_step",
]
