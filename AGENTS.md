# Automotive Testing MCP Server

## 项目介绍
这是一个汽车测试相关的MCP服务器，提供ECU仿真测试功能，通过COM API执行CAN/CANFD报文收发测试。

## 项目结构
```
automotive-testing/
├── automotive-testing.py      # MCP服务器主入口
├── tsmaster/                 # TSMaster功能模块
│   ├── __init__.py          # 包导出
│   ├── models.py            # 数据模型 (Pydantic)
│   ├── encoder.py           # CAN信号编码 (DBC文件)
│   ├── connection.py        # COM连接管理
│   ├── api.py               # CANFD API函数
│   ├── executor.py          # 测试步骤执行器
│   ├── smart_car.py         # 智能小车TCP控制
│   └── machine_arm.py       # 机械臂控制(NFC刷卡、视频录制)
├── encode_signal.py          # CAN信号编码CLI工具 (独立使用)
├── MPLibCode.cpp            # TSMaster Mini Program C++源码
├── requirements.txt         # Python依赖
└── TSMaster_COM API_Python编程指导.pdf  # TSMaster API文档
```

## 运行与测试

### 运行测试（Python方式）
```bash
# 完整测试
python -c "
import sys
sys.path.insert(0, '.')
import asyncio
import json
import automotive_testing as tsm
from tsmaster import ECUSimulationScenario, TestStep, MessageFrame, StepType

async def test():
    data = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]
    scenario = ECUSimulationScenario(
        scenario_name='Test',
        channel=0,
        steps=[
            TestStep(step_id='init', step_type=StepType.INIT_FIFO, order=0),
            TestStep(step_id='send', step_type=StepType.SEND_SINGLE, order=1,
                message=MessageFrame(channel=0, identifier='0x123', data=data)),
        ]
    )
    return await tsm.tsmaster_run_simulation(scenario)

result = asyncio.run(test())
print(result)
"
```

### Lint检查
```bash
# 使用ruff（项目已配置）
ruff check .

# 或手动安装并运行
pip install ruff
ruff check .
```

## 开发指南

### 新增功能步骤
1. 查看PDF文档 `@TSMaster_COM API_Python编程指导.pdf` 了解API用法
2. 在 `tsmaster/api.py` 添加新的API函数
3. 在 `tsmaster/executor.py` 添加步骤处理逻辑
4. 在 `tsmaster/__init__.py` 导出新函数（如需要）

### 模块说明

#### tsmaster/encoder.py - CAN信号编码/解码
- `encode_can_signal()`: 使用DBC文件编码CAN信号
- `decode_can_signal()`: 使用DBC文件解码CAN报文为信号值
- 编码异常: `SignalNotFoundError`, `ValueOutOfRangeError`, `AmbiguousSignalError`, `SignalsNotInSameMessageError`
- 解码异常: `DecodeError`

#### tsmaster/connection.py - 连接管理
- `_ensure_com_initialized()`: 初始化COM组件
- `_ensure_connected()`: 连接TSMaster硬件
- 全局变量: `_app`, `_com`, `_is_connected`

#### tsmaster/api.py - CANFD操作
- `_transmit_single_canfd()`: 发送单帧
- `_start_cyclic_canfd()`: 启动周期发送
- `_stop_cyclic_canfd()`: 停止周期发送
- `_stop_all_cyclic_messages()`: 停止所有周期发送
- `_start_canfd_reception()`: 开启接收FIFO
- `_get_canfd_messages()`: 获取接收报文

#### tsmaster/executor.py - 步骤执行
- `_execute_step()`: 执行单个测试步骤
- 支持: init_fifo, send_single, start_cyclic, stop_cyclic, wait, receive,
  smart_car_switch, smart_car_switch_alltime, smart_car_zone,
  machine_arm_rotation, nfc_start, decode_signals, check_signals

#### tsmaster/smart_car.py - 智能小车控制
- `send_switch_value()`: 发送开关控制指令 (单次)
- `send_switch_value_alltime()`: 发送持续开关控制指令
- `send_zone_value()`: 发送区域控制指令

#### tsmaster/models.py - 数据模型
- `StepType`: 步骤类型枚举
- `MessageFrame`: CAN/CANFD报文结构
  - `data` 字段支持十进制整数和十六进制字符串 (如 `"0x12"`)
- `TestStep`: 测试步骤定义
- `ECUSimulationScenario`: 测试场景定义
- `StepResult`: 步骤执行结果
- `SignalInput`: CAN信号输入 (signal: str, value: float)
- `EncodeResult`: 编码结果 (frame_id, message_name, data)

#### CHECK_SIGNALS 步骤 - 信号条件检查
支持时序信号检查，可检测信号在一段时间或多帧内保持指定值。

**参数**:
- `check_dbc_path`: DBC文件路径
- `check_message_ids`: 要检查的报文ID列表
- `check_timeout_ms`: 超时时间（默认1000ms）
- `check_max_frames`: 最大检查帧数（默认10）
- `conditions`: 信号条件列表，格式: `[{"signal": "信号名", "operator": "==", "value": 值}]`
- `hold_duration_ms`: 信号必须保持的毫秒数（可选，用于时序检查）
- `hold_max_frames`: 信号必须保持的连续帧数（可选，用于时序检查）
- `tolerance_value`: 比较值的容差范围（可选，用于浮点比较）

**操作符**: `==`, `!=`, `>`, `<`, `>=`, `<=`, `exists`, `not_exists`

**示例**:
```python
# 检查信号在连续3帧内保持值
TestStep(
    step_id='check_hold',
    step_type=StepType.CHECK_SIGNALS,
    check_dbc_path='test.dbc',
    check_message_ids=['0x100'],
    hold_max_frames=3,
    conditions=[{'signal': 'PwrSta', 'operator': '==', 'value': 3}]
)

# 检查信号在2000ms内保持值
TestStep(
    step_id='check_duration',
    step_type=StepType.CHECK_SIGNALS,
    check_dbc_path='test.dbc',
    check_message_ids=['0x100'],
    hold_duration_ms=2000,
    conditions=[{'signal': 'Voltage', 'operator': '==', 'value': 5}]
)
```

#### decode_can_signal 函数
```python
def decode_can_signal(
    dbc_path: str,
    frame_id: Union[int, str],
    data: List[int]
) -> Dict[str, Any]:
    """Decode CAN message bytes to signal values using DBC file.

    Args:
        dbc_path: Path to the DBC file
        frame_id: Message frame ID (int or hex string like '0x100')
        data: Message data bytes (list of integers)

    Returns:
        Dictionary with frame_id, message_name, and signals (dict of signal->value)

    Raises:
        DecodeError: Message ID not found in DBC or decoding failed
    """
```

## 代码风格规范

### 导入规范
```python
# 标准库放前面
import asyncio
import time
import json
from enum import Enum

# 第三方库
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

# 本地导入（相对）
from tsmaster.models import StepType
from tsmaster.api import _transmit_single_canfd
```

### 命名规范
| 类型 | 规范 | 示例 |
|------|------|------|
| 模块/包 | 小写下划线 | `api.py`, `connection.py` |
| 类 | PascalCase | `StepResult`, `ECUSimulationScenario` |
| 函数/方法 | 小写下划线 | `_transmit_single_canfd()` |
| 常量 | 大写下划线 | `VT_ARRAY`, `VT_I1` |
| 私有函数 | 前置下划线 | `_ensure_connected()` |
| 类型变量 | PascalCase | `List[int]`, `Dict[str, Any]` |

### 类型提示
```python
from typing import Optional, List, Dict, Any, Union

def _parse_id(value: Union[int, str]) -> int:
    ...

def _get_canfd_messages(
    channel: int,
    timeout_ms: int,
    expected_ids: Optional[List[Union[int, str]]] = None,
    max_messages: int = 1000,
    include_tx: bool = False,
) -> List[Dict[str, Any]]:
    ...
```

### 错误处理
```python
# API层 - 静默失败，返回bool
def _transmit_single_canfd(...) -> bool:
    try:
        _com.transmit_canfd_async(cfd)
        return True
    except Exception:
        return False

# 执行器层 - 详细错误信息
except Exception as e:
    return StepResult(
        step_id=step.step_id,
        step_type=step_type_str,
        status="error",
        error_message=str(e),
        timestamp=timestamp,
    )
```

### Pydantic模型
```python
class MessageFrame(BaseModel):
    channel: int = Field(default=0, ge=0, le=7, description="CAN通道号")
    is_extended_id: bool = Field(default=False, description="扩展帧")
    identifier: Union[int, str] = Field(..., description="报文ID")
    data: List[int] = Field(default_factory=list)
```

### COM组件使用
```python
import pythoncom
import win32com.client
from win32com.client import VARIANT

# 创建COM Record
cfd = win32com.client.Record("TCANFD", _app)
cfd.FIdxChn = channel
cfd.FIdentifier = _parse_id(identifier)
cfd.FDatas = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I1, tuple(data_arr))
```

### MCP工具定义
```python
@mcp.tool(
    name="tool_name",
    annotations={
        "title": "工具标题",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def tool_name(param: ParamModel) -> str:
    """文档字符串"""
    ...
```

### MCP工具 - encode_can_signal
```python
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
    使用DBC文件编码CAN信号为报文字节

    Args:
        dbc_path: DBC文件路径
        signals: 信号列表，每项包含 signal(信号名) 和 value(物理值)

    Returns:
        JSON字符串，包含:
        - status: "success" 或 "error"
        - frame_id: 报文ID (十六进制格式，如 "0x116")
        - message_name: 报文名称
        - data: 编码后的报文数据 (十进制整数列表)

    示例:
        dbc_path = "C:/path/to/test.dbc"
        signals = [SignalInput(signal="PwrSta", value=3)]
        # 返回: {"status": "success", "frame_id": "0x116", "message_name": "FD_VCU1", "data": [0, 0, 0, 18, ...]}
    """
```

## 注意事项
1. 使用MCP Builder技能学习如何编写MCP工具
2. 实现新功能前，先查阅 `TSMaster_COM API_Python编程指导.pdf`
3. TSMaster COM API参数类型：BSTR类型不能传二进制数据，需用Record结构体
4. 测试结束后会自动调用 `_stop_all_cyclic_messages()` 清理周期发送
