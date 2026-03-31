"""
TSMaster CANFD API函数
"""

import time
import pythoncom
import win32com.client
from win32com.client import VARIANT
from typing import List, Dict, Any, Optional, Union


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
    """获取CANFD报文：从FIFO读取报文"""
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
