# OpenCode 车载ECU测试 - Presentation Content

---

## Slide 1: 封面

**主标题**: OpenCode 车载ECU测试

**副标题**: MCP驱动的智能测试解决方案

**简短介绍**:
基于MCP协议的车载电子控制单元(ECU)仿真测试平台，提供CAN/CANFD报文收发、信号编码解码、智能设备控制等完整测试能力。通过TSMaster COM API实现硬件级总线通信，支持BLF日志录制与回放，满足汽车电子工程师的自动化测试需求。

---

## Slide 2: 系统架构

**架构概述**:
采用MCP Server架构，封装TSMaster硬件接口，提供声明式测试场景定义。核心包含7个功能模块，实现从底层连接到高层测试逻辑的完整链路。

**7个核心模块**:

1. **models.py - 数据模型**
   - 定义Pydantic数据模型: StepType, MessageFrame, TestStep
   - ECUSimulationScenario测试场景容器
   - 严格的字段校验与类型安全

2. **connection.py - COM连接管理**
   - 初始化COM组件: `_ensure_com_initialized()`
   - TSMaster硬件连接: `_ensure_connected()`
   - 全局状态管理: `_app`, `_com`, `_is_connected`

3. **api.py - CANFD操作**
   - 单帧发送: `_transmit_single_canfd()`
   - 周期报文控制: `_start_cyclic_canfd()` / `_stop_cyclic_canfd()`
   - 报文接收: `_start_canfd_reception()` / `_get_canfd_messages()`
   - BLF日志: `_start_logging()` / `_stop_logging()`

4. **executor.py - 步骤执行器**
   - `_execute_step()` 统一执行所有测试步骤
   - 支持13种步骤类型的调度与状态跟踪
   - 自动清理: `_stop_all_cyclic_messages()`

5. **encoder.py - 信号编码/解码**
   - `encode_can_signal()`: DBC文件编码信号为报文
   - `decode_can_signal()`: 解析报文为信号值
   - 异常处理: SignalNotFoundError, DecodeError等

6. **smart_car.py - 智能小车控制**
   - TCP协议通信
   - `send_switch_value()`: 单次开关控制
   - `send_switch_value_alltime()`: 持续开关控制
   - `send_zone_value()`: 区域移动控制

7. **machine_arm.py - 机械臂控制**
   - `machine_arm_rotation()`: 旋转角度控制(0-180度)
   - `nfc_start()`: NFC刷卡触发
   - 视频录制同步

---

## Slide 3: 核心功能

**tsmaster_run_simulation 工具**

执行完整的ECU仿真测试场景。

| 参数 | 类型 | 说明 |
|------|------|------|
| scenario | ECUSimulationScenario | 测试场景定义，包含场景名称、通道号、步骤列表 |

**返回值**:
- scenario_name: 测试场景名称
- status: 执行状态 (completed/error)
- total_steps: 总步骤数
- passed_steps / failed_steps / skipped_steps: 各类状态统计
- total_duration_ms: 总执行时长
- step_results: 详细步骤结果列表

**encode_can_signal 工具**

使用DBC文件将信号名称和物理值编码为CAN报文字节。

| 参数 | 类型 | 说明 |
|------|------|------|
| dbc_path | str | DBC数据库文件路径 |
| signals | List[SignalInput] | 信号列表，每项包含signal(名称)和value(物理值) |

**返回值**:
- status: "success" 或 "error"
- frame_id: 报文ID (十六进制，如"0x116")
- message_name: 报文名称
- data: 编码后的数据字节列表

---

## Slide 4: 测试流程

**13种测试步骤类型**

| 步骤类型 | 功能描述 |
|----------|----------|
| **init** | 初始化测试环境，启动TSMaster报文记录(BLF格式) |
| **send_single** | 发送单帧CAN/CANFD报文 |
| **start_cyclic** | 启动周期报文发送，可设置period_ms间隔 |
| **stop_cyclic** | 停止指定的周期报文发送 |
| **wait** | 等待指定时长(duration_ms) |
| **receive** | 接收并验证总线报文，支持expected_ids过滤 |
| **smart_car_switch** | 智能小车单次按键控制，参数: switch_value + keytime_ms |
| **smart_car_switch_alltime** | 智能小车持续开关控制，参数: switch_value + enable_disable |
| **smart_car_zone** | 智能小车区域移动控制，参数: zone_value |
| **machine_arm_rotation** | 机械臂旋转控制，参数: angle (0-180度) |
| **nfc_start** | 机械臂NFC刷卡触发，参数: name (测试名称标识) |
| **decode_signals** | 从CAN/CANFD报文解码信号值，基于DBC文件 |
| **check_signals** | 检查信号条件是否满足，支持时序验证 |

**CHECK_SIGNALS 高级特性**:
- check_lookback_ms: 回溯时间窗口(默认15000ms)
- wait_before_check_ms: 执行前等待时间(默认5000ms)
- conditions: 多信号条件列表
- hold_max_frames: 连续帧数保持检查
- hold_duration_ms: 持续时间保持检查
- 操作符: ==, !=, >, <, >=, <=, exists, not_exists

---

## Slide 5: 代码示例

**示例1: 完整的信号检查测试场景**

```python
from tsmaster import (
    ECUSimulationScenario, TestStep, MessageFrame, StepType,
    _execute_step, _ensure_connected, _stop_all_cyclic_messages, _stop_logging
)

async def test():
    scenario = ECUSimulationScenario(
        scenario_name='Test CHECK_SIGNALS',
        channel=0,
        steps=[
            TestStep(step_id='init', step_type=StepType.INIT, order=0),
            TestStep(step_id='zone0', step_type=StepType.SMART_CAR_ZONE, order=1, zone_value=0),
            TestStep(
                step_id='cyclic_500',
                step_type=StepType.START_CYCLIC,
                order=2,
                period_ms=700,
                message=MessageFrame(channel=0, identifier='0x500', data=[0,0,0,0,0,0,0,0])
            ),
            TestStep(step_id='wait', step_type=StepType.WAIT, order=3, duration_ms=2000),
            TestStep(
                step_id='check_signals',
                step_type=StepType.CHECK_SIGNALS,
                order=4,
                check_dbc_path=r'D31L_15.3_CAN4_DKC_20251204_Draft.dbc',
                check_message_ids=['0x251'],
                check_lookback_ms=15000,
                wait_before_check_ms=1000,
                conditions=[
                    {'signal': 'P_DKey_Welcome', 'operator': '==', 'value': 1, 'hold_max_frames': 20},
                    {'signal': 'P_DKey_Area_PS', 'operator': '==', 'value': 2, 'hold_duration_ms': 2000}
                ]
            ),
        ]
    )
```

**示例2: CAN信号编码调用**

```python
from tsmaster import encode_can_signal

# 编码单个信号
result = encode_can_signal(
    dbc_path="C:/path/to/test.dbc",
    signals=[{"signal": "PwrSta", "value": 3}]
)
# 返回: {"status": "success", "frame_id": "0x116", 
#        "message_name": "FD_VCU1", "data": [0, 0, 0, 18, ...]}

# 编码多个信号
result = encode_can_signal(
    dbc_path="vehicle.dbc",
    signals=[
        {"signal": "VehicleSpeed", "value": 60.5},
        {"signal": "EngineTemp", "value": 95.0}
    ]
)
```

**示例3: 时序信号检查配置**

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

---

## Slide 6: 使用场景

**场景1: 智能小车测试**

用于车载智能钥匙系统的功能验证。

- **区域切换测试**: 通过 `smart_car_zone` 控制小车进入不同区域
- **开关响应测试**: 使用 `smart_car_switch` 模拟按键操作，验证ECU响应
- **持续状态测试**: `smart_car_switch_alltime` 测试长按/持续激活场景
- **信号验证**: 配合 `check_signals` 验证P_DKey_Welcome、P_DKey_Area_PS等信号值

**场景2: 信号检查时序验证**

用于验证ECU信号的稳定性和持续性。

- **多条件并行检查**: 同时验证多个信号是否满足各自条件
- **帧数保持检查**: 确保信号在连续N帧内保持稳定
- **时间保持检查**: 确保信号在指定时间窗口内不波动
- **容差比较**: 支持浮点信号的容差范围比较

**场景3: 机械臂控制与NFC测试**

用于自动化物理交互测试。

- **角度控制**: `machine_arm_rotation` 精确控制0-180度旋转
- **NFC刷卡**: `nfc_start` 触发NFC标签读取，配合视频录制
- **流程自动化**: 将机械臂动作编排进测试序列

---

## Slide 7: 技术亮点

**1. MCP协议集成**

- 基于FastMCP框架实现标准化工具接口
- 声明式工具定义，支持丰富的元数据注解
- 异步执行模型，非阻塞I/O操作

**2. 实时CAN总线测试**

- 通过TSMaster COM API直连硬件
- 支持CAN 2.0和CANFD双模式
- 周期报文发送与实时接收FIFO
- 多通道并行(0-7通道)

**3. DBC信号编码/解码**

- 完整支持Vector DBC数据库格式
- 物理值到原始值的自动转换
- 多信号打包到单条报文
- 精确的错误定位(SignalNotFoundError等)

**4. 智能硬件控制**

- TCP协议控制智能小车
- 机械臂旋转角度精确控制
- NFC刷卡自动化
- 多设备协同调度

**5. BLF日志录制**

- 测试全程自动录制为BLF格式
- 支持日志回放与分析
- 基于日志的信号后验检查
- ASC格式兼容

**6. 时序信号检查**

- 支持连续帧数保持验证
- 支持持续时间保持验证
- 多条件并行判断
- 回溯时间窗口检查

---

## Slide 8: 结语

**项目总结**:

OpenCode 车载ECU测试是一个完整的MCP驱动的测试解决方案，将传统车载测试流程标准化为可编排的声明式场景。通过模块化设计和丰富的步骤类型，工程师可以快速构建复杂的自动化测试用例，提升测试效率和覆盖率。

**核心技术栈**:

- Python 3.x + Pydantic (数据模型)
- FastMCP (MCP服务器框架)
- TSMaster COM API (硬件接口)
- cantools (DBC解析)
- win32com (Windows COM组件)

**适用领域**:

- 车身控制器(BCM)功能测试
- 智能钥匙系统验证
- CAN总线通信测试
- ECU仿真与HIL测试

**链接与联系**:

- GitHub: [项目仓库链接待补充]
- 文档: AGENTS.md
- 联系: [联系方式待补充]

---

*End of Content*
