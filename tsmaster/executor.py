"""
TSMaster测试步骤执行器
"""

import time
from tsmaster.models import StepType, TestStep, StepResult
from tsmaster.api import (
    _transmit_single_canfd,
    _start_cyclic_canfd,
    _stop_cyclic_canfd,
    _start_canfd_reception,
    _get_canfd_messages,
    _parse_id,
)
from tsmaster.smart_car import send_switch_value, send_switch_value_alltime, send_zone_value
from tsmaster.machine_arm import nfc_start, machine_arm_rotation
from tsmaster.encoder import decode_can_signal


def _evaluate_condition(actual: float, operator: str, expected: float, tolerance: float = None) -> bool:
    """Evaluate a single condition with optional tolerance"""
    if tolerance is not None and tolerance > 0:
        if operator == "==":
            return abs(actual - expected) <= tolerance
        elif operator == "!=":
            return abs(actual - expected) > tolerance
        elif operator == ">":
            return actual > expected + tolerance
        elif operator == "<":
            return actual < expected - tolerance
        elif operator == ">=":
            return actual >= expected - tolerance
        elif operator == "<=":
            return actual <= expected + tolerance

    # No tolerance - use exact comparison
    if operator == "==":
        return actual == expected
    elif operator == "!=":
        return actual != expected
    elif operator == ">":
        return actual > expected
    elif operator == "<":
        return actual < expected
    elif operator == ">=":
        return actual >= expected
    elif operator == "<=":
        return actual <= expected
    return False


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

        elif step.step_type == StepType.SMART_CAR_SWITCH:
            if step.switch_value is None:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No switch_value configured",
                    timestamp=timestamp,
                )
            keytime = step.keytime_ms if step.keytime_ms is not None else 100
            success, message = send_switch_value(
                switch_value=step.switch_value,
                keytime_ms=keytime,
            )
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed" if success else "failed",
                error_message=None if success else message,
                timestamp=timestamp,
            )

        elif step.step_type == StepType.SMART_CAR_SWITCH_ALLTIME:
            if step.switch_value is None or step.enable_disable is None:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No switch_value or enable_disable configured",
                    timestamp=timestamp,
                )
            success, message = send_switch_value_alltime(
                switch_value=step.switch_value,
                enable_disable=step.enable_disable,
            )
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed" if success else "failed",
                error_message=None if success else message,
                timestamp=timestamp,
            )

        elif step.step_type == StepType.SMART_CAR_ZONE:
            if step.zone_value is None:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No zone_value configured",
                    timestamp=timestamp,
                )
            success, message = send_zone_value(
                zone_value=step.zone_value,
            )
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed" if success else "failed",
                error_message=None if success else message,
                timestamp=timestamp,
            )

        elif step.step_type == StepType.MACHINE_ARM_ROTATION:
            if step.angle is None:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No angle configured",
                    timestamp=timestamp,
                )
            success, message = machine_arm_rotation(
                angle=step.angle,
            )
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed" if success else "failed",
                error_message=None if success else message,
                timestamp=timestamp,
            )

        elif step.step_type == StepType.NFC_START:
            name = step.name if step.name is not None else "nfc_test"
            success, message = nfc_start(name=name)
            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed" if success else "failed",
                error_message=None if success else message,
                timestamp=timestamp,
            )

        elif step.step_type == StepType.DECODE_SIGNALS:
            # 验证参数
            if not step.dbc_path:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No dbc_path configured",
                    timestamp=timestamp,
                )

            # 从FIFO获取报文
            timeout = step.decode_timeout_ms or 1000
            messages = _get_canfd_messages(
                channel=channel,
                timeout_ms=timeout,
                expected_ids=step.decode_message_ids or [],
                include_tx=True,
            )

            # 如果没有收到报文
            if not messages:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No messages received",
                    timestamp=timestamp,
                )

            # 解码每条报文
            decoded_results = []
            for msg in messages[: (step.decode_max_frames or 10)]:
                try:
                    decoded = decode_can_signal(step.dbc_path, msg['id'], msg['data'])
                    decoded_results.append(decoded)
                except Exception as e:
                    # 单条解码失败不影响其他报文
                    decoded_results.append({'error': str(e), 'frame_id': msg['id']})

            return StepResult(
                step_id=step.step_id,
                step_type=step_type_str,
                status="passed",
                received_messages=decoded_results,
                timestamp=timestamp,
            )

        elif step.step_type == StepType.CHECK_SIGNALS:
            # 验证参数
            if not step.check_dbc_path:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No check_dbc_path configured",
                    timestamp=timestamp,
                )
            if not step.conditions:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="No conditions configured",
                    timestamp=timestamp,
                )

            # 检查是否为时序模式
            is_temporal_mode = (step.hold_max_frames is not None and step.hold_max_frames > 0) or \
                               (step.hold_duration_ms is not None and step.hold_duration_ms > 0)

            if is_temporal_mode:
                # ========== 时序模式 ==========
                # 初始化时序跟踪: {signal_name: {"first_frame_timestamp": None, "consecutive_count": 0}}
                signal_trackers = {}
                for cond in step.conditions:
                    signal_name = cond.get('signal')
                    if signal_name:
                        signal_trackers[signal_name] = {
                            "first_frame_timestamp": None,
                            "consecutive_count": 0
                        }

                # 从FIFO获取报文
                timeout = step.check_timeout_ms or 1000

                # 如果设置了 clear_fifo_before，清空FIFO缓冲区
                if step.clear_fifo_before:
                    _start_canfd_reception(channel)

                messages = _get_canfd_messages(
                    channel=channel,
                    timeout_ms=timeout,
                    expected_ids=step.check_message_ids or [],
                    include_tx=True,
                )

                if not messages:
                    return StepResult(
                        step_id=step.step_id,
                        step_type=step_type_str,
                        status="failed",
                        error_message="No messages received",
                        timestamp=timestamp,
                    )

                # 获取当前时间作为基准
                import time as time_module

                for msg in messages[: (step.check_max_frames or 10)]:
                    try:
                        decoded = decode_can_signal(step.check_dbc_path, msg['id'], msg['data'])
                        signals = decoded.get('signals', {})
                        current_time = time_module.time() * 1000

                        # 检查所有条件
                        all_conditions_met = True
                        condition_holds = {}  # signal_name -> bool (是否满足hold)

                        for cond in step.conditions:
                            signal_name = cond.get('signal')
                            operator = cond.get('operator')
                            expected_value = cond.get('value')

                            if operator in ('exists', 'not_exists'):
                                signal_found = signal_name in signals
                                if operator == 'exists' and not signal_found:
                                    condition_holds[signal_name] = False
                                    all_conditions_met = False
                                elif operator == 'not_exists' and signal_found:
                                    condition_holds[signal_name] = False
                                    all_conditions_met = False
                                else:
                                    condition_holds[signal_name] = True
                            else:
                                if signal_name not in signals:
                                    condition_holds[signal_name] = False
                                    all_conditions_met = False
                                    continue

                                actual = signals[signal_name]
                                tolerance = step.tolerance_value
                                condition_match = _evaluate_condition(actual, operator, expected_value, tolerance)

                                tracker = signal_trackers.get(signal_name, {
                                    "first_frame_timestamp": None,
                                    "consecutive_count": 0
                                })

                                if condition_match:
                                    # 信号值匹配，累加计数
                                    if tracker["first_frame_timestamp"] is None:
                                        tracker["first_frame_timestamp"] = current_time
                                    tracker["consecutive_count"] += 1
                                    signal_trackers[signal_name] = tracker

                                    # 检查hold条件
                                    hold_satisfied = False
                                    if step.hold_max_frames and step.hold_max_frames > 0:
                                        if tracker["consecutive_count"] >= step.hold_max_frames:
                                            hold_satisfied = True
                                    if step.hold_duration_ms and step.hold_duration_ms > 0:
                                        elapsed = current_time - tracker["first_frame_timestamp"]
                                        if elapsed >= step.hold_duration_ms:
                                            hold_satisfied = True

                                    condition_holds[signal_name] = hold_satisfied
                                    if not hold_satisfied:
                                        all_conditions_met = False
                                else:
                                    # 信号值不匹配，重置
                                    tracker["first_frame_timestamp"] = None
                                    tracker["consecutive_count"] = 0
                                    signal_trackers[signal_name] = tracker
                                    condition_holds[signal_name] = False
                                    all_conditions_met = False

                        # 如果所有条件都满足hold，返回成功
                        if all_conditions_met and condition_holds:
                            return StepResult(
                                step_id=step.step_id,
                                step_type=step_type_str,
                                status="passed",
                                received_messages=[decoded],
                                timestamp=timestamp,
                            )
                    except Exception:
                        continue

                # 构建失败信息
                failed_info = []
                for signal_name, tracker in signal_trackers.items():
                    if tracker["consecutive_count"] > 0:
                        failed_info.append(
                            f"Signal '{signal_name}': held {tracker['consecutive_count']} frames, "
                            f"elapsed {current_time - tracker['first_frame_timestamp']:.0f}ms"
                        )

                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="; ".join(failed_info) if failed_info else "Hold conditions not satisfied",
                    timestamp=timestamp,
                )

            else:
                # ========== 立即模式 (原有逻辑) ==========
                # 从FIFO获取报文
                timeout = step.check_timeout_ms or 1000

                # 如果设置了 clear_fifo_before，清空FIFO缓冲区
                if step.clear_fifo_before:
                    _start_canfd_reception(channel)

                messages = _get_canfd_messages(
                    channel=channel,
                    timeout_ms=timeout,
                    expected_ids=step.check_message_ids or [],
                    include_tx=True,
                )

                if not messages:
                    return StepResult(
                        step_id=step.step_id,
                        step_type=step_type_str,
                        status="failed",
                        error_message="No messages received",
                        timestamp=timestamp,
                    )

                failed_conditions = []

                for msg in messages[: (step.check_max_frames or 10)]:
                    try:
                        decoded = decode_can_signal(step.check_dbc_path, msg['id'], msg['data'])
                        signals = decoded.get('signals', {})

                        all_passed = True
                        for cond in step.conditions:
                            signal_name = cond.get('signal')
                            operator = cond.get('operator')
                            expected_value = cond.get('value')

                            if operator in ('exists', 'not_exists'):
                                signal_found = signal_name in signals
                                if operator == 'exists' and not signal_found:
                                    failed_conditions.append(f"Signal '{signal_name}' not found")
                                    all_passed = False
                                elif operator == 'not_exists' and signal_found:
                                    failed_conditions.append(f"Signal '{signal_name}' should not exist")
                                    all_passed = False
                            else:
                                if signal_name not in signals:
                                    failed_conditions.append(f"Signal '{signal_name}' not found")
                                    all_passed = False
                                    continue
                                actual = signals[signal_name]
                                tolerance = step.tolerance_value
                                if not _evaluate_condition(actual, operator, expected_value, tolerance):
                                    failed_conditions.append(
                                        f"Signal '{signal_name}': actual={actual}, expected {operator} {expected_value}"
                                    )
                                    all_passed = False

                        if all_passed:
                            return StepResult(
                                step_id=step.step_id,
                                step_type=step_type_str,
                                status="passed",
                                received_messages=[decoded],
                                timestamp=timestamp,
                            )
                    except Exception:
                        continue

                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="; ".join(failed_conditions) if failed_conditions else "No matching message found",
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
