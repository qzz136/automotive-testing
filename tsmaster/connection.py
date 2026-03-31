"""
TSMaster COM连接管理
"""

import pythoncom
import win32com.client
from typing import Optional, Any

_app: Optional[Any] = None
_com: Optional[Any] = None
_is_connected: bool = False


def _ensure_com_initialized():
    """初始化COM组件"""
    global _app, _com
    pythoncom.CoInitialize()
    if _app is None:
        _app = win32com.client.Dispatch("TSMaster.TSApplication")
        _com = _app.TSCOM()


def _ensure_connected():
    """确保已连接TSMaster硬件"""
    global _is_connected
    _ensure_com_initialized()
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
            r.FHWDeviceName = "TC1014"
            r.FMappingDisabled = False
            _app.set_mapping(r)

            _app.configure_baudrate_canfd(0, 500, 2000, 1, 0, True)

            _app.connect()
            _is_connected = True
        except Exception as e:
            print(f"Connection error: {e}")
