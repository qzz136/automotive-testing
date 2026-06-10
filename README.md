# Automotive Testing MCP Server

基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的汽车 ECU 仿真测试服务器，通过 TSMaster COM API 执行 CAN/CANFD 报文收发与信号测试。

## 功能概述

- **ECU 仿真测试** — 定义并执行多步骤测试场景，涵盖报文发送、信号检查、周期发送等
- **CAN 信号编码/解码** — 基于 DBC 文件编码信号值为报文字节，或从报文解码信号
- **智能小车控制** — 通过 TCP 协议控制智能小车（按键、区域移动、持续开关）
- **机械臂控制** — NFC 刷卡触发及机械臂旋转控制
- **TSMaster 集成** — 连接 TSMaster 硬件进行 CAN/CANFD 报文收发、BLF 录制与回放

```
automotive-testing/
├── automotive-testing.py      # MCP 服务器主入口
├── tsmaster/
│   ├── __init__.py            # 包导出
│   ├── models.py              # Pydantic 数据模型
│   ├── encoder.py             # CAN 信号编码/解码（DBC 文件）
│   ├── connection.py          # TSMaster COM 连接管理
│   ├── api.py                 # CANFD API 函数（发送、接收、周期、录制）
│   ├── executor.py            # 测试步骤执行器
│   ├── smart_car.py           # 智能小车 TCP 控制
│   └── machine_arm.py         # 机械臂控制（NFC 刷卡、视频录制）
├── MPLibCode.cpp              # TSMaster Mini Program C++ 源码
├── requirements.txt           # Python 依赖
└── AGENTS.md                  # 项目开发指南
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行 MCP 服务器

```bash
python automotive-testing.py
```

服务器将以 MCP 标准协议启动，供支持 MCP 的客户端（如 OpenCode）调用以下工具。

## MCP 工具

### `tsmaster_run_simulation`

执行 ECU 仿真测试场景。支持多步骤序列，自动清理周期发送和录制资源。

**支持的步骤类型：**

| 步骤类型 | 说明 |
|----------|------|
| `init` | 初始化测试环境，启动 BLF 录制 |
| `send_single` | 发送单帧 CAN/CANFD 报文 |
| `start_cyclic` | 启动周期报文发送 |
| `stop_cyclic` | 停止周期报文发送 |
| `wait` | 等待指定时长 |
| `receive` | 从 FIFO 接收并验证总线报文 |
| `smart_car_switch` | 智能小车按键控制（支持 press / long_press / double_press） |
| `smart_car_switch_alltime` | 智能小车持续开关控制 |
| `smart_car_zone` | 智能小车区域移动 |
| `machine_arm_rotation` | 机械臂旋转（0-180°） |
| `nfc_start` | 机械臂 NFC 刷卡触发 |
| `decode_signals` | 从 CAN 报文解码信号 |
| `check_signals` | 检查信号条件（支持多信号时序检查） |

### `encode_can_signal`

使用 DBC 文件将 CAN 信号编码为报文字节。

## 开发

### Lint 检查

```bash
ruff check .
```

### 添加新功能

1. 查阅 [TSMaster COM API 文档] 了解 API 用法
2. 在 `tsmaster/api.py` 添加新的 API 函数
3. 在 `tsmaster/executor.py` 添加步骤处理逻辑
4. 在 `tsmaster/__init__.py` 导出新函数

## 技术栈

- **Python 3.10+**
- **FastMCP** — MCP 服务器框架
- **Pydantic** — 数据模型与验证
- **cantools** — DBC 文件解析
- **python-can** — BLF 日志文件读取
- **OpenCV** — NFC 视频录制
- **win32com** — TSMaster COM API 交互（Windows Only）

## 环境要求

- **操作系统**：Windows（依赖 TSMaster COM API）
- **TSMaster**：需安装并配置 TSMaster 软件及硬件
- **Python**：3.10 或更高版本
