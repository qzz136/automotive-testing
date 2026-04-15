"""
Example 3: MCP Tool Usage
MCP工具调用示例

This example demonstrates how to call MCP tools in OpenCode.
展示如何在OpenCode中调用MCP工具执行测试任务。
"""

# Tool: tsmaster_run_simulation
# 工具: 执行ECU仿真测试场景
TSMASTER_RUN_SIMULATION = {
    "scenario_name": "Smart Car NFC Test",
    "channel": 0,
    "steps": [
        {
            "step_id": "init",
            "step_type": "init",
            "order": 0
        },
        {
            "step_id": "move_zone",
            "step_type": "smart_car_zone",
            "order": 1,
            "zone_value": 3
        },
        {
            "step_id": "nfc_trigger",
            "step_type": "nfc_start",
            "order": 2,
            "name": "nfc_auth_test"
        },
        {
            "step_id": "wait_response",
            "step_type": "wait",
            "order": 3,
            "duration_ms": 3000
        }
    ]
}


# Tool: encode_can_signal
# 工具: CAN信号编码
ENCODE_CAN_SIGNAL = {
    "dbc_path": "D31L_15.3_CAN4_DKC_20251204_Draft.dbc",
    "signals": [
        {"signal": "PwrSta", "value": 3},
        {"signal": "Voltage", "value": 12.5}
    ]
}


# Example: Complete test scenario with signal check
# 示例: 完整的信号检查测试场景
COMPLETE_TEST_SCENARIO = {
    "scenario_name": "Door Lock Signal Check",
    "channel": 0,
    "steps": [
        # Initialize test
        {
            "step_id": "init",
            "step_type": "init",
            "order": 0
        },
        
        # Send control message
        {
            "step_id": "send_lock_cmd",
            "step_type": "send_single",
            "order": 1,
            "message": {
                "channel": 0,
                "identifier": "0x116",
                "data": [0, 0, 0, 18, 0, 0, 0, 0]
            }
        },
        
        # Wait for processing
        {
            "step_id": "wait",
            "step_type": "wait",
            "order": 2,
            "duration_ms": 1000
        },
        
        # Check response signals
        {
            "step_id": "check_lock_status",
            "step_type": "check_signals",
            "order": 3,
            "check_dbc_path": "body_control.dbc",
            "check_message_ids": ["0x200"],
            "check_lookback_ms": 5000,
            "wait_before_check_ms": 500,
            "conditions": [
                {
                    "signal": "DoorLockStatus",
                    "operator": "==",
                    "value": 1,
                    "hold_max_frames": 5
                }
            ]
        }
    ]
}


# Example: Cyclic message test
# 示例: 周期报文测试
CYCLIC_MESSAGE_TEST = {
    "scenario_name": "Heartbeat Message Test",
    "channel": 0,
    "steps": [
        {
            "step_id": "init",
            "step_type": "init",
            "order": 0
        },
        {
            "step_id": "start_heartbeat",
            "step_type": "start_cyclic",
            "order": 1,
            "period_ms": 100,
            "message": {
                "channel": 0,
                "identifier": "0x100",
                "data": [1, 2, 3, 4, 5, 6, 7, 8]
            }
        },
        {
            "step_id": "run_for_10s",
            "step_type": "wait",
            "order": 2,
            "duration_ms": 10000
        },
        {
            "step_id": "stop_heartbeat",
            "step_type": "stop_cyclic",
            "order": 3
        }
    ]
}


# Usage in OpenCode:
# 在OpenCode中的使用方式:
#
# @mcp tsmaster_run_simulation with:
#   scenario_name: "My Test"
#   channel: 0
#   steps: [...]
#
# @mcp encode_can_signal with:
#   dbc_path: "test.dbc"
#   signals:
#     - signal: "PwrSta"
#       value: 3
