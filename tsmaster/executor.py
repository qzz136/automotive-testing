"""
TSMaster测试步骤执行器
"""

import os
import time
from datetime import datetime
from tsmaster.models import StepType, TestStep, StepResult
from tsmaster.api import (
    _transmit_single_canfd,
    _start_cyclic_canfd,
    _stop_cyclic_canfd,
    _get_canfd_messages,
    _parse_id,
    _start_logging,
    _stop_logging,
    _set_blf_log_file,
    _get_blf_log_file,
    _read_messages_from_blf,
    _read_messages_from_asc,
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
        if step.step_type == StepType.INIT:
            # 设置BLF日志文件路径
            log_dir = os.path.join(os.getcwd(), "logs", "can_messages")
            os.makedirs(log_dir, exist_ok=True)
            blf_file = os.path.join(log_dir, f"can_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{step.step_id}.blf")
            _set_blf_log_file(blf_file)
            print(f"[INIT] BLF log file: {blf_file}")
            
            # 启动TSMaster报文记录（BLF格式）
            success = _start_logging(blf_file)
            
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

            # 验证每个条件的hold参数（hold_max_frames和hold_duration_ms不能同时存在）
            for idx, cond in enumerate(step.conditions):
                cond_hold_frames = cond.get('hold_max_frames')
                cond_hold_ms = cond.get('hold_duration_ms')
                if cond_hold_frames is not None and cond_hold_frames > 0 and cond_hold_ms is not None and cond_hold_ms > 0:
                    return StepResult(
                        step_id=step.step_id,
                        step_type=step_type_str,
                        status="failed",
                        error_message=f"Condition [{idx}] has both hold_max_frames and hold_duration_ms, they cannot be used together",
                        timestamp=timestamp,
                    )

            # 检查是否为时序模式（任意条件有hold参数即启用）
            is_temporal_mode = any(
                (cond.get('hold_max_frames') is not None and cond.get('hold_max_frames') > 0) or
                (cond.get('hold_duration_ms') is not None and cond.get('hold_duration_ms') > 0)
                for cond in step.conditions
            )

            # 步骤1: 等待指定时间（让信号稳定）
            wait_ms = step.wait_before_check_ms or 5000
            if wait_ms > 0:
                time.sleep(wait_ms / 1000.0)

            # 步骤2: 停止录制，让TSMaster写入文件
            _stop_logging()
            time.sleep(3)  # 等待TSMaster完成文件写入和格式转换

            # 步骤3: 查找最新的ASC文件
            log_dir = os.path.join(os.getcwd(), "logs", "can_messages")
            asc_files = []
            if os.path.exists(log_dir):
                for f in os.listdir(log_dir):
                    if f.endswith('.asc'):
                        full_path = os.path.join(log_dir, f)
                        asc_files.append((full_path, os.path.getmtime(full_path)))
            
            if not asc_files:
                # 没有找到ASC文件，尝试使用BLF
                blf_file = _get_blf_log_file()
                if blf_file and os.path.exists(blf_file):
                    asc_files = [(blf_file, os.path.getmtime(blf_file))]
                else:
                    # 重新开始录制
                    new_blf = os.path.join(log_dir, f"can_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_resume.blf")
                    _set_blf_log_file(new_blf)
                    _start_logging(new_blf)
                    return StepResult(
                        step_id=step.step_id,
                        step_type=step_type_str,
                        status="failed",
                        error_message="No ASC or BLF log file found",
                        timestamp=timestamp,
                    )
            
            # 按修改时间排序，取最新的
            asc_files.sort(key=lambda x: x[1], reverse=True)
            latest_asc_file = asc_files[0][0]
            print(f"[CHECK_SIGNALS] Reading from: {latest_asc_file}")
            
            # 步骤4: 计算回溯时间
            lookback_ms = step.check_lookback_ms or 15000
            lookback_seconds = lookback_ms / 1000.0
            
            # 步骤5: 从ASC文件读取报文（取最后N秒的消息）
            if latest_asc_file.endswith('.asc'):
                all_messages = _read_messages_from_asc(latest_asc_file, lookback_seconds=lookback_seconds)
            else:
                all_messages = _read_messages_from_blf(latest_asc_file, lookback_seconds=lookback_seconds)
            
            # 步骤6: 按报文ID过滤
            expected_ids = step.check_message_ids or []
            if expected_ids:
                parsed_filter_ids = [_parse_id(fid) for fid in expected_ids]
                messages = [msg for msg in all_messages if _parse_id(msg['id']) in parsed_filter_ids]
                print(f"[CHECK_SIGNALS] Filtered by IDs {expected_ids}: {len(all_messages)} -> {len(messages)} messages")
                # 调试：显示所有报文ID的分布
                id_counts = {}
                for msg in all_messages:
                    msg_id = msg.get('id', 'unknown')
                    id_counts[msg_id] = id_counts.get(msg_id, 0) + 1
                print(f"[CHECK_SIGNALS] All message IDs in window: {id_counts}")
            else:
                messages = all_messages

            if not messages:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message=f"No messages in log file within time window [last {lookback_ms}ms]",
                    timestamp=timestamp,
                )

            if is_temporal_mode:
                # ========== 时序模式 ==========
                # 初始化时序跟踪: 每个条件独立跟踪
                # {condition_index: {"first_frame_timestamp": None, "consecutive_count": 0}}
                condition_trackers = {}
                for idx, cond in enumerate(step.conditions):
                    condition_trackers[idx] = {
                        "first_frame_timestamp": None,
                        "consecutive_count": 0
                    }

                # 调试：统计每个信号值的分布
                signal_value_counts = {cond.get('signal'): {} for cond in step.conditions}

                # 每个条件独立跟踪，完全独立判断
                for msg in messages:
                    try:
                        decoded = decode_can_signal(step.check_dbc_path, msg['id'], msg['data'])
                        signals = decoded.get('signals', {})
                        # 使用报文自己的时间戳（转换为毫秒）
                        current_time = msg.get('timestamp_us', 0) / 1000.0

                        # 调试：统计信号值分布
                        for signal_name in signal_value_counts:
                            if signal_name in signals:
                                val = signals[signal_name]
                                signal_value_counts[signal_name][val] = signal_value_counts[signal_name].get(val, 0) + 1

                        # 独立处理每个条件，互不影响
                        for idx, cond in enumerate(step.conditions):
                            signal_name = cond.get('signal')
                            operator = cond.get('operator')
                            expected_value = cond.get('value')
                            # 获取该条件特有的hold参数
                            cond_hold_max_frames = cond.get('hold_max_frames') if cond.get('hold_max_frames') is not None else step.hold_max_frames
                            cond_hold_duration_ms = cond.get('hold_duration_ms') if cond.get('hold_duration_ms') is not None else step.hold_duration_ms
                            
                            tracker = condition_trackers[idx]

                            if operator in ('exists', 'not_exists'):
                                signal_found = signal_name in signals
                                if (operator == 'exists' and signal_found) or (operator == 'not_exists' and not signal_found):
                                    # 条件满足，不累加（exists/not_exists不需要hold）
                                    tracker["passed"] = True
                                else:
                                    tracker["passed"] = False
                            else:
                                if signal_name not in signals:
                                    # 信号不存在，重置该条件的tracker
                                    tracker["first_frame_timestamp"] = None
                                    tracker["consecutive_count"] = 0
                                    tracker["passed"] = False
                                    continue

                                actual = signals[signal_name]
                                tolerance = step.tolerance_value
                                condition_match = _evaluate_condition(actual, operator, expected_value, tolerance)

                                if condition_match:
                                    # 信号值匹配，累加计数（独立于其他条件）
                                    if tracker["first_frame_timestamp"] is None:
                                        tracker["first_frame_timestamp"] = current_time
                                    tracker["consecutive_count"] += 1

                                    # 检查该条件自己的hold参数
                                    hold_satisfied = True
                                    if cond_hold_max_frames and cond_hold_max_frames > 0:
                                        if tracker["consecutive_count"] < cond_hold_max_frames:
                                            hold_satisfied = False
                                    if cond_hold_duration_ms and cond_hold_duration_ms > 0:
                                        elapsed = current_time - tracker["first_frame_timestamp"]
                                        if elapsed < cond_hold_duration_ms:
                                            hold_satisfied = False
                                    
                                    tracker["passed"] = hold_satisfied
                                else:
                                    # 信号值不匹配，重置计数器（但保留已满足的passed状态）
                                    tracker["first_frame_timestamp"] = None
                                    tracker["consecutive_count"] = 0
                                    # 只有当条件还没满足时才重置passed
                                    # 一旦满足，保持passed=True直到检查结束

                        # 检查是否所有条件都满足
                        all_conditions_passed = all(
                            condition_trackers[idx].get("passed", False) 
                            for idx in range(len(step.conditions))
                        )

                        # 如果所有条件都满足，返回成功
                        if all_conditions_passed:
                            # 步骤7: 重新开始录制（返回前）
                            new_blf = os.path.join(log_dir, f"can_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_resume.blf")
                            _set_blf_log_file(new_blf)
                            _start_logging(new_blf)
                            print(f"[CHECK_SIGNALS] Resumed logging to: {new_blf}")
                            
                            return StepResult(
                                step_id=step.step_id,
                                step_type=step_type_str,
                                status="passed",
                                timestamp=timestamp,
                            )
                    except Exception:
                        continue

                # 调试：打印信号值分布
                print("[CHECK_SIGNALS] Signal value distribution:")
                for signal_name, value_counts in signal_value_counts.items():
                    print(f"  {signal_name}: {value_counts}")

                # 构建详细的失败信息
                total_frames_checked = len(messages)

                failed_info_parts = [
                    f"[CHECK_SIGNALS Failed] Checked {total_frames_checked} frames from log file"
                ]

                # 添加每个条件的状态（独立报告）
                for idx, cond in enumerate(step.conditions):
                    signal_name = cond.get('signal')
                    operator = cond.get('operator')
                    expected_value = cond.get('value')
                    cond_hold_max_frames = cond.get('hold_max_frames') if cond.get('hold_max_frames') is not None else step.hold_max_frames
                    cond_hold_duration_ms = cond.get('hold_duration_ms') if cond.get('hold_duration_ms') is not None else step.hold_duration_ms
                    tracker = condition_trackers[idx]

                    # 查找该信号的最后实际值
                    last_actual = None
                    for msg in messages:
                        try:
                            decoded = decode_can_signal(step.check_dbc_path, msg['id'], msg['data'])
                            if signal_name in decoded.get('signals', {}):
                                last_actual = decoded['signals'][signal_name]
                        except Exception:
                            continue

                    hold_req_str = []
                    if cond_hold_max_frames:
                        hold_req_str.append(f"{cond_hold_max_frames} frames")
                    if cond_hold_duration_ms:
                        hold_req_str.append(f"{cond_hold_duration_ms}ms")

                    if tracker.get("passed", False):
                        # 条件已满足
                        failed_info_parts.append(
                            f"  - [{idx}] Signal '{signal_name}': actual={last_actual}, expected {operator} {expected_value}, "
                            f"PASSED (required: {', '.join(hold_req_str) if hold_req_str else 'immediate'})"
                        )
                    elif tracker["consecutive_count"] > 0:
                        elapsed = current_time - tracker["first_frame_timestamp"] if tracker["first_frame_timestamp"] else 0
                        hold_status = []
                        if cond_hold_max_frames:
                            hold_status.append(f"{tracker['consecutive_count']}/{cond_hold_max_frames} frames")
                        if cond_hold_duration_ms:
                            hold_status.append(f"{elapsed:.0f}/{cond_hold_duration_ms}ms")

                        failed_info_parts.append(
                            f"  - [{idx}] Signal '{signal_name}': actual={last_actual}, expected {operator} {expected_value}, "
                            f"held {', '.join(hold_status)} (required: {', '.join(hold_req_str)})"
                        )
                    else:
                        failed_info_parts.append(
                            f"  - [{idx}] Signal '{signal_name}': actual={last_actual}, expected {operator} {expected_value}, "
                            f"held 0 frames (required: {', '.join(hold_req_str) if hold_req_str else 'immediate'})"
                        )

                # 步骤7: 重新开始录制（返回前）
                new_blf = os.path.join(log_dir, f"can_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_resume.blf")
                _set_blf_log_file(new_blf)
                _start_logging(new_blf)
                print(f"[CHECK_SIGNALS] Resumed logging to: {new_blf}")
                
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    received_messages=[],
                    error_message="\n".join(failed_info_parts),
                    timestamp=timestamp,
                )

            else:
                # ========== 立即模式 (原有逻辑) ==========
                # 使用已经过滤好的 messages（在时序模式前已处理）
                failed_conditions = []

                for msg in messages:
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
                            # 步骤7: 重新开始录制（返回前）
                            new_blf = os.path.join(log_dir, f"can_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_resume.blf")
                            _set_blf_log_file(new_blf)
                            _start_logging(new_blf)
                            print(f"[CHECK_SIGNALS] Resumed logging to: {new_blf}")
                            
                            return StepResult(
                                step_id=step.step_id,
                                step_type=step_type_str,
                                status="passed",
                                received_messages=[decoded],
                                timestamp=timestamp,
                            )
                    except Exception:
                        continue

                # 步骤7: 重新开始录制（返回前）
                new_blf = os.path.join(log_dir, f"can_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_resume.blf")
                _set_blf_log_file(new_blf)
                _start_logging(new_blf)
                print(f"[CHECK_SIGNALS] Resumed logging to: {new_blf}")
                
                return StepResult(
                    step_id=step.step_id,
                    step_type=step_type_str,
                    status="failed",
                    error_message="; ".join(failed_conditions) if failed_conditions else "No matching message found",
                    timestamp=timestamp,
                )

            # 步骤7: 时序模式结束后重新开始录制（失败时）
            new_blf = os.path.join(log_dir, f"can_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_resume.blf")
            _set_blf_log_file(new_blf)
            _start_logging(new_blf)
            print(f"[CHECK_SIGNALS] Resumed logging to: {new_blf}")

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
