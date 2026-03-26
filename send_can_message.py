import pythoncom
import win32com.client
from win32com.client import VARIANT
import sys
sys.stdout.reconfigure(encoding='utf-8')

pythoncom.CoInitialize()

app = win32com.client.Dispatch("TSMaster.TSApplication")
com = app.TSCOM()

app.set_can_channel_count(1)
app.set_lin_channel_count(0)

r = win32com.client.Record("TTSMapping", app)
r.FAppName = "PythonApp"
r.FAppChannelIndex = 0
r.FAppChannelType = 0
r.FHWIndex = 0
r.FHWDeviceType = 3
r.FHWDeviceSubType = 8
r.FHWChannelIndex = 0
r.FHWDeviceName = "TC1014"
r.FMappingDisabled = False
app.set_mapping(r)

app.configure_baudrate_canfd(0, 500, 2000, 0, 0, True)
try:
    app.connect()
except Exception:
    pass

c = win32com.client.Record("TCAN", app)
c.FIdxChn = 0
c.FIsTX = 1
c.FIsRemote = False
c.FIsExtendedId = 0
c.FDLC = 8
c.FIdentifier = 0x123
c.FTimeUs = 0
c.FDatas = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, [1, 2, 3, 4, 5, 6, 7, 8])

print("Sending CAN message...")
com.transmit_can_async(c)
print(f"Sent: ID=0x123, Data=[1,2,3,4,5,6,7,8]")
