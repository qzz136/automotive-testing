#!/usr/bin/env python3
"""
MCP Server for Automotive Testing.

本服务器提供ECU仿真测试功能，通过COM API执行CAN/CANFD报文收发测试。
"""

import asyncio
import time
import json
from typing import List
from mcp.server.fastmcp import FastMCP

from tsmaster import (
    ECUSimulationScenario,
    StepResult,
    _ensure_connected,
    _execute_step,
    _stop_all_cyclic_messages,
)
from tsmaster import encode_can_signal as _encode_can_signal
from tsmaster.models import SignalInput

mcp = FastMCP("automotive-testing")


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
    测试结束后自动停止所有周期报文发送。

    支持的步骤类型：
    - init_fifo: 初始化FIFO（使能接收并清空buffer）
    - send_single: 发送单帧CAN/CANFD报文
    - start_cyclic: 启动周期报文发送
    - stop_cyclic: 停止周期报文发送
    - wait: 等待指定时长
    - receive: 接收并验证总线报文（从FIFO获取消息，不清空buffer）
              可通过 include_tx 参数选择是否包含发送的报文 (默认True=包含自己发送的)
    - smart_car_switch: 智能小车单次按键控制 (switch_value + keytime_ms)
    - smart_car_switch_alltime: 智能小车持续开关控制 (switch_value + enable_disable)
    - smart_car_zone: 智能小车区域移动控制 (zone_value)
    - machine_arm_rotation: 机械臂旋转控制 (angle: 0-180度)
    - nfc_start: 机械臂NFC刷卡触发 (name: 测试名称标识)

    注意：周期发送会在测试流程结束时自动停止，如需提前停止可使用 stop_cyclic 步骤。

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

        result_json = json.dumps(
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
        result_json = json.dumps({"status": "error", "message": str(e)})
    finally:
        _stop_all_cyclic_messages()

    return result_json


@mcp.tool(
    name="encode_can_signal",
    annotations={
        "title": "CAN信号编码",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def encode_can_signal(dbc_path: str, signals: List[SignalInput]) -> str:
    """
    Encode CAN signals to CAN message bytes using DBC file.

    Takes a list of signal name-value pairs and encodes them into a CAN message
    based on the signal definitions in the specified DBC file.

    Args:
        dbc_path: Path to the DBC file containing signal definitions
        signals: List of signal name-value pairs to encode

    Returns:
        JSON string containing the encoding result:
        - status: "success" or "error"
        - frame_id: CAN message frame ID
        - message_name: Name of the CAN message
        - data: Encoded message data as byte list
        On error returns: {"status": "error", "message": "..."}
    """
    try:
        signal_values = {s.signal: s.value for s in signals}
        result = _encode_can_signal(dbc_path, signal_values)
        return json.dumps(
            {
                "status": "success",
                "frame_id": f"0x{result['frame_id']:X}",
                "message_name": result["message_name"],
                "data": result["data"],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
