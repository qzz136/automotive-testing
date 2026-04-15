# Automotive Testing MCP Server Architecture

## Overview

The Automotive Testing MCP Server is a Python-based server that provides ECU simulation testing capabilities through CAN/CANFD message transmission and reception using COM API.

汽车测试MCP服务器是一个基于Python的服务器，通过COM API提供ECU仿真测试功能，支持CAN/CANFD报文收发。

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Client (OpenCode)                    │
│                    MCP客户端 (OpenCode)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ JSON-RPC
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP Server: automotive-testing.py               │
│              MCP服务器: automotive-testing.py                │
│  ┌─────────────────┐  ┌──────────────────────────────────┐  │
│  │ tsmaster_run_   │  │     encode_can_signal            │  │
│  │ _simulation()   │  │     (CAN signal encoding)        │  │
│  │ (测试场景执行)   │  │     (CAN信号编码)                │  │
│  └────────┬────────┘  └────────┬─────────────────────────┘  │
└───────────┼────────────────────┼────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    tsmaster Package                          │
│                    tsmaster包                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   models    │  │   encoder   │  │     connection      │  │
│  │ (数据模型)   │  │ (编解码)    │  │    (COM连接)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │     api     │  │   executor  │  │    smart_car        │  │
│  │ (CANFD操作)  │  │ (步骤执行)  │  │   (智能小车)         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ COM Interface
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 TSMaster COM API                             │
│              TSMaster COM接口                                │
└──────────────────────────┬──────────────────────────────────┘
                           │ Hardware Interface
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              CAN/CANFD Hardware (TSMaster)                   │
│              CAN/CANFD硬件设备                               │
└─────────────────────────────────────────────────────────────┘
```

## Module Dependencies

### 1. MCP Server Layer (automotive-testing.py)

**Responsibilities:**
- Define MCP tools using FastMCP
- Handle JSON-RPC requests from clients
- Coordinate test execution

**Key Components:**
- `tsmaster_run_simulation()`: Execute test scenarios
- `encode_can_signal()`: Encode CAN signals using DBC files

**Dependencies:**
- `tsmaster` package
- `mcp.server.fastmcp`

### 2. Data Models (tsmaster/models.py)

**Responsibilities:**
- Define Pydantic models for type safety
- Validate input parameters
- Serialize/deserialize data

**Key Classes:**
- `StepType`: Enumeration of test step types
- `MessageFrame`: CAN/CANFD message structure
- `TestStep`: Single test step definition
- `ECUSimulationScenario`: Complete test scenario
- `SignalInput`: CAN signal input format
- `StepResult`: Step execution result

**Dependencies:**
- `pydantic`
- `typing`

### 3. CAN Signal Encoding (tsmaster/encoder.py)

**Responsibilities:**
- Load and parse DBC files
- Encode physical signal values to raw bytes
- Decode raw bytes to physical values

**Key Functions:**
- `encode_can_signal()`: Encode signals to message bytes
- `decode_can_signal()`: Decode message bytes to signals

**Dependencies:**
- `cantools`
- DBC files

### 4. COM Connection (tsmaster/connection.py)

**Responsibilities:**
- Initialize COM components
- Manage connection to TSMaster hardware
- Handle connection state

**Key Functions:**
- `_ensure_com_initialized()`: Initialize COM
- `_ensure_connected()`: Connect to hardware

**Dependencies:**
- `pythoncom`
- `win32com.client`

### 5. CANFD API (tsmaster/api.py)

**Responsibilities:**
- Send single CANFD messages
- Start/stop cyclic transmission
- Receive messages from FIFO
- Control logging to BLF/ASC files

**Key Functions:**
- `_transmit_single_canfd()`: Send single frame
- `_start_cyclic_canfd()`: Start cyclic transmission
- `_stop_cyclic_canfd()`: Stop cyclic transmission
- `_get_canfd_messages()`: Receive messages
- `_start_logging()`, `_stop_logging()`: Log control

**Dependencies:**
- `connection` module
- TSMaster COM API

### 6. Step Executor (tsmaster/executor.py)

**Responsibilities:**
- Execute individual test steps
- Handle step-specific logic
- Return step results

**Supported Step Types:**
- `INIT`: Initialize environment
- `SEND_SINGLE`: Send single message
- `START_CYCLIC`: Start cyclic transmission
- `STOP_CYCLIC`: Stop cyclic transmission
- `WAIT`: Wait duration
- `RECEIVE`: Receive and verify messages
- `SMART_CAR_*`: Smart car control
- `MACHINE_ARM_ROTATION`: Machine arm control
- `NFC_START`: NFC trigger
- `DECODE_SIGNALS`: Decode signals
- `CHECK_SIGNALS`: Check signal conditions

**Dependencies:**
- `api` module
- `smart_car` module
- `encoder` module

### 7. Smart Car Control (tsmaster/smart_car.py)

**Responsibilities:**
- Control smart car via TCP
- Send zone and switch commands

**Key Functions:**
- `send_switch_value()`: Send switch command
- `send_switch_value_alltime()`: Send persistent switch
- `send_zone_value()`: Send zone command

**Dependencies:**
- TCP socket

## Data Flow

### 1. Test Scenario Execution Flow

```
User Request → MCP Server → tsmaster_run_simulation()
                                    │
                                    ▼
                        _ensure_connected()
                                    │
                                    ▼
                        For each step in scenario:
                                    │
                                    ├──► _execute_step()
                                    │          │
                                    │          ├──► Step-specific handler
                                    │          │          │
                                    │          │          ├──► api.py functions
                                    │          │          │
                                    │          │          ├──► smart_car.py functions
                                    │          │          │
                                    │          │          └──► encoder.py functions
                                    │          │
                                    │          └──► Return StepResult
                                    │
                                    ▼
                        _stop_all_cyclic_messages()
                                    │
                                    ▼
                        _stop_logging()
                                    │
                                    ▼
                        Return JSON report
```

### 2. CAN Signal Encoding Flow

```
encode_can_signal() → Load DBC file (cantools)
                              │
                              ▼
                      Find message by signal name
                              │
                              ▼
                      Validate signal value range
                              │
                              ▼
                      Encode to bytes
                              │
                              ▼
                      Return {frame_id, message_name, data}
```

### 3. Signal Check Flow (CHECK_SIGNALS)

```
_check_signals_step() → Read BLF/ASC log file
                                │
                                ▼
                        Decode messages using DBC
                                │
                                ▼
                        Extract signal values
                                │
                                ▼
                        Check conditions against signals
                                │
                                ▼
                        Track hold duration/frames
                                │
                                ▼
                        Return pass/fail result
```

## Key Design Patterns

### 1. Pydantic Models
All data structures use Pydantic for validation and serialization:

```python
class TestStep(BaseModel):
    step_id: str = Field(..., description="步骤唯一标识符")
    step_type: StepType = Field(..., description="步骤类型")
    order: int = Field(..., description="执行顺序")
    # ... additional fields with validation
```

### 2. Step Pattern
Test scenarios consist of ordered steps executed sequentially:

```python
for step in sorted(scenario.steps, key=lambda x: x.order):
    result = _execute_step(step, scenario.channel)
```

### 3. Resource Management
Cleanup is performed in finally blocks:

```python
try:
    _ensure_connected()
    # Execute steps
finally:
    _stop_all_cyclic_messages()
    _stop_logging()
```

### 4. Error Handling
API layer returns boolean status, executor provides detailed errors:

```python
# API layer - silent failure
def _transmit_single_canfd(...) -> bool:
    try:
        _com.transmit_canfd_async(cfd)
        return True
    except Exception:
        return False

# Executor layer - detailed error
except Exception as e:
    return StepResult(
        step_id=step.step_id,
        status="error",
        error_message=str(e),
    )
```

## External Dependencies

### Python Packages
- `mcp`: MCP server framework
- `pydantic`: Data validation
- `cantools`: DBC file parsing
- `pywin32`: COM interface (Windows only)

### Hardware
- TSMaster hardware device
- CAN/CANFD bus connection

### Files
- DBC files for signal definitions
- BLF/ASC files for log replay

## Extension Points

To add new functionality:

1. **New Step Type**: Add to `StepType` enum in models.py, then add handler in executor.py
2. **New API Function**: Add to api.py, call from executor.py
3. **New MCP Tool**: Add to automotive-testing.py with proper annotations

## Thread Safety

- COM components must be initialized per thread (using `pythoncom.CoInitialize()`)
- Global state is managed through module-level variables (`_app`, `_com`, `_is_connected`)
- Cyclic message tracking uses a global dictionary
