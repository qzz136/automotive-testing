"""
Example 1: Basic ECU Simulation Test Scenario
基本ECU仿真测试场景示例

This example demonstrates how to create and run a complete ECU simulation test.
展示如何创建并运行完整的ECU仿真测试场景。
"""

import asyncio
import json
from tsmaster import (
    ECUSimulationScenario,
    TestStep,
    MessageFrame,
    StepType,
    _execute_step,
    _ensure_connected,
    _stop_all_cyclic_messages,
    _stop_logging,
)


async def run_ecu_test():
    """Run a complete ECU simulation test scenario."""
    
    # Step 1: Create test scenario with multiple steps
    # 创建包含多个步骤的测试场景
    scenario = ECUSimulationScenario(
        scenario_name="Digital Key Welcome Test",
        channel=0,  # CAN channel 0
        steps=[
            # Initialize test environment
            # 初始化测试环境
            TestStep(
                step_id="init",
                step_type=StepType.INIT,
                order=0
            ),
            
            # Move smart car to zone 0
            # 移动智能小车到区域0
            TestStep(
                step_id="zone0",
                step_type=StepType.SMART_CAR_ZONE,
                order=1,
                zone_value=0
            ),
            
            # Start cyclic message transmission
            # 启动周期报文发送
            TestStep(
                step_id="cyclic_500",
                step_type=StepType.START_CYCLIC,
                order=2,
                period_ms=700,
                message=MessageFrame(
                    channel=0,
                    identifier="0x500",
                    data=[0, 0, 0, 0, 0, 0, 0, 0]
                )
            ),
            
            # Wait for system stabilization
            # 等待系统稳定
            TestStep(
                step_id="wait",
                step_type=StepType.WAIT,
                order=3,
                duration_ms=2000
            ),
            
            # Check signal conditions
            # 检查信号条件
            TestStep(
                step_id="check_signals",
                step_type=StepType.CHECK_SIGNALS,
                order=4,
                check_dbc_path="D31L_15.3_CAN4_DKC_20251204_Draft.dbc",
                check_message_ids=["0x251"],
                check_lookback_ms=15000,
                wait_before_check_ms=1000,
                conditions=[
                    {
                        "signal": "P_DKey_Welcome",
                        "operator": "==",
                        "value": 1,
                        "hold_max_frames": 20
                    },
                    {
                        "signal": "P_DKey_Area_PS",
                        "operator": "==",
                        "value": 2,
                        "hold_duration_ms": 2000
                    }
                ]
            ),
        ]
    )
    
    # Step 2: Ensure connection to TSMaster hardware
    # 确保连接到TSMaster硬件
    _ensure_connected()
    
    # Step 3: Execute all test steps
    # 执行所有测试步骤
    results = []
    for step in sorted(scenario.steps, key=lambda x: x.order):
        result = _execute_step(step, scenario.channel)
        results.append(result)
    
    # Step 4: Cleanup - stop cyclic messages and logging
    # 清理 - 停止周期发送和日志记录
    _stop_all_cyclic_messages()
    _stop_logging()
    
    # Step 5: Return test report as JSON
    # 返回JSON格式的测试报告
    return json.dumps({
        "scenario_name": scenario.scenario_name,
        "status": "completed",
        "total_steps": len(results),
        "step_results": [r.model_dump() for r in results]
    }, indent=2, ensure_ascii=False)


# Run the test
if __name__ == "__main__":
    result = asyncio.run(run_ecu_test())
    print(result)
