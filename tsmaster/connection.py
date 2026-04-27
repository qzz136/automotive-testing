"""
TSMaster COM连接管理
"""

import pythoncom
import win32com.client
from typing import Optional, Any

_app: Optional[Any] = None
_com: Optional[Any] = None
_is_connected: bool = False


def _is_app_connected() -> bool:
    """检查TSMaster应用是否真正连接（心跳检测）"""
    global _app, _com, _is_connected
    if _app is None:
        return False
    try:
        # 尝试获取TSCOM对象来检测连接是否有效
        _app.TSCOM()
        return True
    except Exception:
        # 连接失效，释放僵尸对象引用
        print("TSMaster connection lost, resetting COM objects...")
        _app = None
        _com = None
        _is_connected = False
        return False


def _ensure_com_initialized():
    """初始化COM组件"""
    global _app, _com
    pythoncom.CoInitialize()
    
    # 心跳检测：如果app对象已失效，重建连接
    if not _is_app_connected():
        _app = win32com.client.Dispatch("TSMaster.TSApplication")
        _com = _app.TSCOM()


def _ensure_connected():
    """确保已连接TSMaster硬件"""
    global _is_connected
    _ensure_com_initialized()
    
    # 心跳检测连接有效性
    if _is_connected and not _is_app_connected():
        print("TSMaster connection lost, reconnecting...")
        _is_connected = False
    
    if not _is_connected:
        try:
            _app.set_can_channel_count(1)
            _app.set_lin_channel_count(0)

            r = win32com.client.Record("TTSMapping", _app)
            r.FAppName = "PythonApp"
            r.FAppChannelIndex = 0
            r.FAppChannelType = 0
            r.FHWIndex = 0
            r.FHWDeviceType = 3
            r.FHWDeviceSubType = 12
            r.FHWChannelIndex = 0
            r.FHWDeviceName = "TC1011"
            r.FMappingDisabled = False
            _app.set_mapping(r)

            _app.configure_baudrate_canfd(0, 500, 2000, 1, 0, True)

            _app.connect()
            _is_connected = True
        except Exception as e:
            print(f"Connection error: {e}")
