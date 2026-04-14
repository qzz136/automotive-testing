"""
TSMaster CANFD API函数
"""

import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

# 尝试导入python-can用于BLF文件读取
try:
    from can.io.blf import BLFReader
    _CAN_BLF_AVAILABLE = True
except ImportError:
    _CAN_BLF_AVAILABLE = False
    print("Warning: python-can not installed, BLF reading will not be available")

import pythoncom
import win32com.client
from win32com.client import VARIANT

def _get_com():
    """获取COM对象，确保已连接"""
    from tsmaster.connection import _ensure_connected, _com

    _ensure_connected()
    return _com


def _get_app():
    """获取APP对象，确保已连接"""
    from tsmaster.connection import _ensure_connected, _app

    _ensure_connected()
    return _app


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
    try:
        _com = _get_com()
        _app = _get_app()
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
    try:
        _com = _get_com()
        _app = _get_app()
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
    try:
        _com = _get_com()
        _com.delete_cyclic_msg_canfd_verbose(
            channel, 1 if is_extended_id else 0, int(_parse_id(identifier))
        )
        return True
    except Exception as e:
        print(f"Stop cyclic error: {e}")
        return False


def _stop_all_cyclic_messages() -> bool:
    """停止所有周期发送的报文（测试结束后自动清理）"""
    try:
        _com = _get_com()
        _com.delete_cyclic_msgs()
        return True
    except Exception as e:
        print(f"Stop all cyclic error: {e}")
        return False


def _start_canfd_reception(channel: int) -> bool:
    """开启CANFD接收：使能FIFO并清空缓冲区"""
    try:
        _com = _get_com()
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
    """获取CANFD报文：从FIFO读取报文，并自动保存到日志文件"""
    _com = _get_com()
    messages = []
    if expected_ids is None:
        expected_ids = []
    parsed_filter_ids = [_parse_id(fid) for fid in expected_ids]

    end_time = time.time() * 1000 + timeout_ms

    while time.time() * 1000 < end_time and len(messages) < max_messages:
        try:
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
                    msg = {
                        "id": f"0x{identifier:X}",
                        "dlc": dlc,
                        "timestamp_us": timestamp_us,
                        "is_extended": bool(is_extended),
                        "is_fd": bool(is_edl),
                        "is_brs": bool(is_brs),
                        "data": data_list,
                    }
                    messages.append(msg)
        except Exception:
            pass
        time.sleep(0.01)

    # 自动保存到日志文件
    if messages:
        _append_messages_to_log(messages)

    return messages


def _start_logging(log_file_path: str = "") -> bool:
    """启动报文记录，记录为BLF格式
    
    Args:
        log_file_path: 记录文件路径（后缀为.blf），空字符串则使用TSMaster默认路径
    
    Returns:
        True: 成功, False: 失败
    """
    try:
        _com = _get_com()
        result = _com.start_logging(log_file_path)
        print(f"[TSMaster] start_logging result: {result}")
        # TSMaster可能返回None或其他值，只要不是异常就算成功
        return True
    except Exception as e:
        print(f"Start logging error: {e}")
        return False


def _stop_logging() -> bool:
    """停止报文记录
    
    Returns:
        True: 成功, False: 失败
    """
    try:
        _com = _get_com()
        _com.stop_logging()
        return True
    except Exception as e:
        print(f"Stop logging error: {e}")
        return False


# 全局变量：当前BLF日志文件路径
_current_blf_file: Optional[str] = None


def _set_blf_log_file(blf_path: Optional[str]) -> None:
    """设置当前场景的BLF日志文件路径"""
    global _current_blf_file
    _current_blf_file = blf_path


def _get_blf_log_file() -> Optional[str]:
    """获取当前场景的BLF日志文件路径"""
    return _current_blf_file


def _read_messages_from_blf(
    blf_path: str,
    lookback_seconds: Optional[float] = None
) -> List[Dict[str, Any]]:
    """从BLF文件读取报文
    
    Args:
        blf_path: BLF文件路径
        lookback_seconds: 回溯时间（秒），None表示读取所有报文，否则只读取最后N秒的报文
    
    Returns:
        报文列表，格式与 _get_canfd_messages 返回的相同
    """
    if not _CAN_BLF_AVAILABLE:
        print("Error: python-can not installed, cannot read BLF file")
        return []
    
    if not os.path.exists(blf_path):
        print(f"Error: BLF file not found: {blf_path}")
        return []
    
    all_messages = []
    try:
        with BLFReader(blf_path) as reader:
            for msg in reader:
                # 获取报文时间戳（秒）- 这是相对时间
                msg_timestamp = msg.timestamp
                
                # 转换为内部格式
                all_messages.append({
                    'timestamp': msg_timestamp,  # 保持为相对时间
                    'id': f"0x{msg.arbitration_id:X}",
                    'data': list(msg.data),
                    'dlc': msg.dlc,
                    'timestamp_us': int(msg_timestamp * 1_000_000),
                    'is_extended': msg.is_extended_id,
                    'is_fd': getattr(msg, 'is_fd', False),
                    'is_brs': getattr(msg, 'bitrate_switch', False),
                })
    except Exception as e:
        print(f"Error reading BLF file: {e}")
        return []
    
    # 如果需要回溯过滤
    if lookback_seconds is not None and lookback_seconds > 0 and all_messages:
        # 找到最后一条消息的时间戳
        max_timestamp = max(msg['timestamp'] for msg in all_messages)
        # 计算时间窗口起点
        window_start = max_timestamp - lookback_seconds
        # 过滤消息
        messages = [msg for msg in all_messages if msg['timestamp'] >= window_start]
        print(f"[BLF] Total messages: {len(all_messages)}, Filtered (last {lookback_seconds}s): {len(messages)}")
        return messages
    
    return all_messages


def _read_messages_from_asc(
    asc_path: str,
    lookback_seconds: Optional[float] = None
) -> List[Dict[str, Any]]:
    """从ASC文件读取报文（TSMaster生成的ASCII格式）
    
    Args:
        asc_path: ASC文件路径
        lookback_seconds: 回溯时间（秒），None表示读取所有报文，否则只读取最后N秒的报文
    
    Returns:
        报文列表，格式与 _get_canfd_messages 返回的相同
    """
    if not _CAN_BLF_AVAILABLE:
        print("Error: python-can not installed, cannot read ASC file")
        return []
    
    if not os.path.exists(asc_path):
        print(f"Error: ASC file not found: {asc_path}")
        return []
    
    # 尝试导入ASCReader
    try:
        from can.io.asc import ASCReader
    except ImportError:
        print("Error: ASCReader not available in python-can")
        return []
    
    all_messages = []
    try:
        with ASCReader(asc_path) as reader:
            for msg in reader:
                # 获取报文时间戳（秒）- 这是相对时间（从日志开始）
                msg_timestamp = msg.timestamp
                
                # 转换为内部格式
                all_messages.append({
                    'timestamp': msg_timestamp,  # 保持为相对时间（秒）
                    'id': f"0x{msg.arbitration_id:X}",
                    'data': list(msg.data),
                    'dlc': msg.dlc,
                    'timestamp_us': int(msg_timestamp * 1_000_000),
                    'is_extended': msg.is_extended_id,
                    'is_fd': getattr(msg, 'is_fd', False),
                    'is_brs': getattr(msg, 'bitrate_switch', False),
                })
    except Exception as e:
        print(f"Error reading ASC file: {e}")
        return []
    
    # 如果需要回溯过滤
    if lookback_seconds is not None and lookback_seconds > 0 and all_messages:
        # 找到最后一条消息的时间戳
        max_timestamp = max(msg['timestamp'] for msg in all_messages)
        # 计算时间窗口起点
        window_start = max_timestamp - lookback_seconds
        # 过滤消息
        messages = [msg for msg in all_messages if msg['timestamp'] >= window_start]
        print(f"[ASC] Total messages: {len(all_messages)}, Filtered (last {lookback_seconds}s): {len(messages)}")
        return messages
    
    return all_messages
