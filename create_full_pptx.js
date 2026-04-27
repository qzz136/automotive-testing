const PptxGenJS = require('pptxgenjs');
const pptx = new PptxGenJS();

// 设置主题颜色
const colors = {
    primary: '667EEA',
    secondary: '764BA2',
    accent: '4FACFE',
    dark: '0A0A0F',
    text: 'FFFFFF',
    textSecondary: 'CCCCCC',
    cardBg: '141423'
};

// 设置默认布局
pptx.layout = 'LAYOUT_16x9';

// 辅助函数：创建带背景的slide
function createSlide(title, subtitle = '') {
    let slide = pptx.addSlide();
    slide.background = { color: colors.dark };
    if (title) {
        slide.addText(title, {
            x: 0.5, y: 0.3, w: 9, h: 0.6,
            fontSize: 32, color: colors.text, bold: true
        });
    }
    if (subtitle) {
        slide.addText(subtitle, {
            x: 0.5, y: 0.9, w: 9, h: 0.4,
            fontSize: 16, color: colors.textSecondary, italic: true
        });
    }
    return slide;
}

// ===== 第1页：标题页 =====
let slide1 = pptx.addSlide();
slide1.background = { color: colors.dark };
slide1.addText('🚗', { x: 4.5, y: 1.2, w: 1, h: 0.8, fontSize: 60, align: 'center' });
slide1.addText('OpenCode Agent', { x: 0.5, y: 2.2, w: 9, h: 0.8, fontSize: 48, color: colors.text, bold: true, align: 'center' });
slide1.addText('车载DKC测试指南', { x: 0.5, y: 3.0, w: 9, h: 0.8, fontSize: 48, color: '667EEA', bold: true, align: 'center' });
slide1.addText('基于MCP协议和Agent技能系统的全流程自动化测试解决方案', { x: 0.5, y: 4.2, w: 9, h: 0.6, fontSize: 18, color: colors.textSecondary, align: 'center' });

// 添加数据指标
slide1.addShape('rect', { x: 1, y: 5.2, w: 2.3, h: 0.8, fill: { color: colors.cardBg }, line: { color: colors.primary, width: 1 } });
slide1.addText('12+', { x: 1, y: 5.3, w: 2.3, h: 0.4, fontSize: 28, color: colors.accent, bold: true, align: 'center' });
slide1.addText('测试步骤类型', { x: 1, y: 5.6, w: 2.3, h: 0.3, fontSize: 12, color: colors.textSecondary, align: 'center' });

slide1.addShape('rect', { x: 3.8, y: 5.2, w: 2.3, h: 0.8, fill: { color: colors.cardBg }, line: { color: colors.primary, width: 1 } });
slide1.addText('2', { x: 3.8, y: 5.3, w: 2.3, h: 0.4, fontSize: 28, color: colors.accent, bold: true, align: 'center' });
slide1.addText('核心MCP工具', { x: 3.8, y: 5.6, w: 2.3, h: 0.3, fontSize: 12, color: colors.textSecondary, align: 'center' });

slide1.addShape('rect', { x: 6.6, y: 5.2, w: 2.3, h: 0.8, fill: { color: colors.cardBg }, line: { color: colors.primary, width: 1 } });
slide1.addText('100%', { x: 6.6, y: 5.3, w: 2.3, h: 0.4, fontSize: 28, color: colors.accent, bold: true, align: 'center' });
slide1.addText('自动化测试', { x: 6.6, y: 5.6, w: 2.3, h: 0.3, fontSize: 12, color: colors.textSecondary, align: 'center' });

// ===== 第2页：什么是车载DKC测试 =====
let slide2 = createSlide('📋 什么是车载DKC测试？OpenCode Agent如何改变传统测试？');

slide2.addText('DKC（数字钥匙控制器）是汽车数字钥匙系统的核心，负责无钥匙进入、启动授权、身份认证等功能。', {
    x: 0.5, y: 1.5, w: 9, h: 0.6, fontSize: 16, color: colors.text
});

slide2.addText('通过OpenCode Agent，测试人员可以用自然语言描述测试场景，Agent自动执行复杂的测试序列。', {
    x: 0.5, y: 2.2, w: 9, h: 0.6, fontSize: 16, color: colors.text
});

// 6个功能卡片
const features = [
    { icon: '📡', title: 'CAN/CANFD 报文收发', desc: '支持单帧发送、周期发送、报文接收等多种通信模式，覆盖车载网络测试的核心需求。' },
    { icon: '🔍', title: 'DBC信号解码', desc: '使用DBC文件定义报文格式，自动将原始字节解码为有意义的信号值，支持复杂的数据结构。' },
    { icon: '⏱️', title: '时序信号检查', desc: '验证信号在指定时间窗口内保持特定值，支持多信号联合检查，确保时序逻辑正确。' },
    { icon: '🤖', title: '智能设备控制', desc: '集成智能小车和机械臂控制，实现物理世界的自动化测试操作。' },
    { icon: '📝', title: '自动日志记录', desc: '测试过程中自动记录BLF/ASC格式的报文日志，便于事后分析和问题追溯。' },
    { icon: '🎯', title: '场景化测试', desc: '通过定义测试场景和步骤序列，轻松构建复杂的测试用例，支持步骤间的数据传递。' }
];

let xPos = 0.5, yPos = 3.2;
features.forEach((feat, idx) => {
    if (idx === 3) { xPos = 0.5; yPos = 5.0; }
    slide2.addShape('rect', { x: xPos, y: yPos, w: 2.9, h: 1.6, fill: { color: colors.cardBg }, line: { color: colors.primary, width: 1 } });
    slide2.addText(feat.icon, { x: xPos + 0.1, y: yPos + 0.1, w: 0.5, h: 0.4, fontSize: 24 });
    slide2.addText(feat.title, { x: xPos + 0.1, y: yPos + 0.5, w: 2.7, h: 0.3, fontSize: 14, color: colors.text, bold: true });
    slide2.addText(feat.desc, { x: xPos + 0.1, y: yPos + 0.85, w: 2.7, h: 0.7, fontSize: 10, color: colors.textSecondary });
    xPos += 3.1;
});

// ===== 第3页：4层架构图 - 上 =====
let slide3 = createSlide('🏗️ OpenCode Agent 完整架构（4层）');

// Layer 1: 用户提示词层
slide3.addShape('rect', { x: 0.5, y: 1.3, w: 9, h: 0.9, fill: { color: '1E2761' }, line: { color: '667EEA', width: 2 } });
slide3.addText('Layer 1', { x: 0.7, y: 1.4, w: 1.5, h: 0.25, fontSize: 12, color: colors.textSecondary });
slide3.addText('👤 用户提示词层', { x: 0.7, y: 1.7, w: 3, h: 0.3, fontSize: 18, color: colors.accent, bold: true });
slide3.addText('User Prompt - 自然语言描述测试需求', { x: 4, y: 1.7, w: 5, h: 0.3, fontSize: 14, color: colors.text });

// Layer 2: LLM层
slide3.addShape('rect', { x: 0.5, y: 2.4, w: 9, h: 0.9, fill: { color: '065A82' }, line: { color: '4FACFE', width: 2 } });
slide3.addText('Layer 2', { x: 0.7, y: 2.5, w: 1.5, h: 0.25, fontSize: 12, color: colors.textSecondary });
slide3.addText('🧠 LLM层', { x: 0.7, y: 2.8, w: 2, h: 0.3, fontSize: 18, color: colors.accent, bold: true });
slide3.addText('OpenCode Agent - 意图理解、步骤规划、工具选择', { x: 3, y: 2.8, w: 6, h: 0.3, fontSize: 14, color: colors.text });

// Layer 3: 工具层
slide3.addShape('rect', { x: 0.5, y: 3.5, w: 9, h: 1.3, fill: { color: '6D2E46' }, line: { color: 'A26769', width: 2 } });
slide3.addText('Layer 3', { x: 0.7, y: 3.6, w: 1.5, h: 0.25, fontSize: 12, color: colors.textSecondary });
slide3.addText('🛠️ 工具层', { x: 0.7, y: 3.9, w: 2, h: 0.3, fontSize: 18, color: colors.accent, bold: true });

// 工具层内部3列
slide3.addText('🛠️ 内置工具', { x: 0.7, y: 4.3, w: 2.5, h: 0.25, fontSize: 12, color: colors.text, bold: true });
slide3.addText('read | edit | write | bash | grep | lsp_*', { x: 0.7, y: 4.55, w: 2.8, h: 0.2, fontSize: 10, color: colors.textSecondary });

slide3.addText('📚 Skills', { x: 3.5, y: 4.3, w: 2.5, h: 0.25, fontSize: 12, color: colors.text, bold: true });
slide3.addText('automotive-testing | mcp-builder | docx/excel/pdf', { x: 3.5, y: 4.55, w: 3, h: 0.2, fontSize: 10, color: colors.textSecondary });

slide3.addText('📦 MCP Servers', { x: 6.5, y: 4.3, w: 2.5, h: 0.25, fontSize: 12, color: colors.text, bold: true });
slide3.addText('automotive-testing | filesystem | database', { x: 6.5, y: 4.55, w: 2.8, h: 0.2, fontSize: 10, color: colors.textSecondary });

// ===== 第4页：4层架构图 - 下（外部环境层） =====
let slide4 = createSlide('🔌 外部环境层（Layer 4）');

// 4个外部环境组
const externalGroups = [
    { icon: '🔌', title: 'TSMaster API', items: ['COM接口', 'CAN/CANFD', '信号编解码'] },
    { icon: '🌐', title: '网络服务', items: ['TCP (智能小车)', 'HTTP (机械臂)', '数据库服务'] },
    { icon: '💾', title: '文件系统', items: ['DBC文件读取', 'BLF/ASC日志', '视频录制存储'] },
    { icon: '🔧', title: '物理设备', items: ['CAN Hardware', 'DKC Device', 'Smart Car / Arm'] }
];

xPos = 0.5; yPos = 1.5;
externalGroups.forEach((group, idx) => {
    slide4.addShape('rect', { x: xPos, y: yPos, w: 2.1, h: 2.2, fill: { color: 'B85042' }, line: { color: 'E7E8D1', width: 1 } });
    slide4.addText(group.icon, { x: xPos + 0.1, y: yPos + 0.1, w: 0.4, h: 0.3, fontSize: 20 });
    slide4.addText(group.title, { x: xPos + 0.5, y: yPos + 0.15, w: 1.5, h: 0.3, fontSize: 14, color: colors.text, bold: true });
    
    let itemY = yPos + 0.6;
    group.items.forEach(item => {
        slide4.addText('• ' + item, { x: xPos + 0.1, y: itemY, w: 1.9, h: 0.25, fontSize: 11, color: colors.textSecondary });
        itemY += 0.35;
    });
    
    xPos += 2.4;
});

// ===== 第5页：Automotive Testing MCP核心架构 =====
let slide5 = createSlide('📡 Automotive Testing MCP 核心架构');

slide5.addText('本MCP Server是一个综合性的车载测试解决方案，集成智能小车控制、机械臂操作、NFC刷卡、视频录制等多种物理设备交互功能。', {
    x: 0.5, y: 1.2, w: 9, h: 0.5, fontSize: 14, color: colors.textSecondary, italic: true
});

// 工具1: tsmaster_run_simulation
slide5.addShape('rect', { x: 0.5, y: 1.9, w: 5.5, h: 2.0, fill: { color: colors.cardBg }, line: { color: colors.primary, width: 2 } });
slide5.addText('📡 核心工具', { x: 0.7, y: 2.0, w: 2, h: 0.3, fontSize: 12, color: colors.accent });
slide5.addText('tsmaster_run_simulation', { x: 0.7, y: 2.35, w: 4, h: 0.3, fontSize: 16, color: colors.text, bold: true });
slide5.addText('执行DKC仿真测试场景，支持12+种测试步骤类型', { x: 0.7, y: 2.7, w: 5, h: 0.25, fontSize: 11, color: colors.textSecondary });

// 功能分组
slide5.addText('🚗 物理设备控制', { x: 0.7, y: 3.05, w: 2.5, h: 0.2, fontSize: 10, color: colors.text, bold: true });
slide5.addText('智能小车开关控制 | 区域移动 | 机械臂旋转 | NFC刷卡+视频录制', { x: 0.7, y: 3.25, w: 5, h: 0.2, fontSize: 9, color: colors.textSecondary });

slide5.addText('📡 CAN/CANFD通信', { x: 0.7, y: 3.5, w: 2.5, h: 0.2, fontSize: 10, color: colors.text, bold: true });
slide5.addText('单帧报文收发 | 周期报文发送 | 报文接收验证 | BLF/ASC日志记录', { x: 0.7, y: 3.7, w: 5, h: 0.2, fontSize: 9, color: colors.textSecondary });

// 工具2: encode_can_signal
slide5.addShape('rect', { x: 6.2, y: 1.9, w: 3.3, h: 2.0, fill: { color: colors.cardBg }, line: { color: 'F093FB', width: 2 } });
slide5.addText('🔧 辅助工具', { x: 6.4, y: 2.0, w: 2, h: 0.3, fontSize: 12, color: colors.accent });
slide5.addText('encode_can_signal', { x: 6.4, y: 2.35, w: 3, h: 0.3, fontSize: 16, color: colors.text, bold: true });
slide5.addText('CAN信号编码', { x: 6.4, y: 2.7, w: 3, h: 0.25, fontSize: 11, color: colors.textSecondary });
slide5.addText('• DBC文件解析\n• 信号值到字节编码\n• 报文ID自动识别\n• 多信号同时编码', { x: 6.4, y: 3.05, w: 2.9, h: 0.8, fontSize: 10, color: colors.textSecondary });

// 通信协议层
slide5.addShape('rect', { x: 0.5, y: 4.2, w: 9, h: 1.3, fill: { color: colors.cardBg }, line: { color: colors.primary, width: 1 } });
slide5.addText('🔌 多协议设备通信层', { x: 0.7, y: 4.3, w: 3, h: 0.3, fontSize: 14, color: colors.accent, bold: true });

slide5.addText('🔌 TSMaster COM API', { x: 0.7, y: 4.7, w: 2.5, h: 0.2, fontSize: 11, color: colors.text, bold: true });
slide5.addText('CAN/CANFD | 报文收发 | 信号编解码', { x: 0.7, y: 4.9, w: 2.5, h: 0.2, fontSize: 9, color: colors.textSecondary });

slide5.addText('🌐 TCP/IP', { x: 3.5, y: 4.7, w: 2.5, h: 0.2, fontSize: 11, color: colors.text, bold: true });
slide5.addText('192.168.1.1:2001 | 智能小车控制', { x: 3.5, y: 4.9, w: 2.5, h: 0.2, fontSize: 9, color: colors.textSecondary });

slide5.addText('📹 HTTP + OpenCV', { x: 6.3, y: 4.7, w: 2.5, h: 0.2, fontSize: 11, color: colors.text, bold: true });
slide5.addText('192.168.2.1 | 机械臂控制 | 视频录制', { x: 6.3, y: 4.9, w: 2.8, h: 0.2, fontSize: 9, color: colors.textSecondary });

// ===== 第6页：MCP Server实现 - 代码1 =====
let slide6 = createSlide('🐍 MCP Server实现 - 主入口');

slide6.addText('automotive-testing.py - MCP Server主入口', {
    x: 0.5, y: 1.0, w: 9, h: 0.3, fontSize: 14, color: colors.textSecondary, fontFace: 'Courier New'
});

const code1 = `# Automotive Testing MCP Server - 车载DKC综合测试解决方案
# 功能包括：CAN/CANFD通信、智能小车控制、机械臂操作、NFC刷卡、视频录制
from mcp.server.fastmcp import FastMCP
from tsmaster import (
    ECUSimulationScenario, 
    _ensure_connected,
    _execute_step,
    encode_can_signal
)

# 初始化 MCP Server
mcp = FastMCP("automotive-testing")

if __name__ == "__main__":
    mcp.run()`;

slide6.addText(code1, {
    x: 0.5, y: 1.4, w: 9, h: 3.5,
    fontSize: 11, color: colors.text, fontFace: 'Courier New',
    fill: { color: '0D0D12' },
    inset: 0.2
});

// ===== 第7页：MCP Server实现 - 代码2 =====
let slide7 = createSlide('🐍 MCP Server实现 - MCP工具定义');

slide7.addText('@mcp.tool装饰器定义', {
    x: 0.5, y: 1.0, w: 9, h: 0.3, fontSize: 14, color: colors.textSecondary
});

const code2 = `@mcp.tool(
    name="tsmaster_run_simulation",
    annotations={
        "title": "执行DKC仿真测试场景",
    },
)
async def tsmaster_run_simulation(scenario: ECUSimulationScenario) -> str:
    """执行测试序列"""
    _ensure_connected()
    sorted_steps = sorted(scenario.steps, key=lambda s: s.order)
    step_results = []
    
    for step in sorted_steps:
        result = _execute_step(step, scenario.channel)
        step_results.append(result)
    
    return json.dumps({
        "scenario_name": scenario.scenario_name,
        "status": "completed",
        "step_results": step_results
    })

@mcp.tool(name="encode_can_signal")
async def encode_can_signal(dbc_path: str, signals: List[SignalInput]) -> str:
    """CAN信号编码"""
    # 使用DBC文件编码信号`;

slide7.addText(code2, {
    x: 0.5, y: 1.4, w: 9, h: 3.8,
    fontSize: 10, color: colors.text, fontFace: 'Courier New',
    fill: { color: '0D0D12' },
    inset: 0.2
});

// ===== 第8页：MCP Server实现 - 代码3 =====
let slide8 = createSlide('🐍 MCP Server实现 - 数据模型');

slide8.addText('tsmaster/models.py - Pydantic数据模型', {
    x: 0.5, y: 1.0, w: 9, h: 0.3, fontSize: 14, color: colors.textSecondary
});

const code3 = `class StepType(Enum):
    INIT = "init"
    SEND_SINGLE = "send_single"
    START_CYCLIC = "start_cyclic"
    WAIT = "wait"
    RECEIVE = "receive"
    SMART_CAR_ZONE = "smart_car_zone"
    MACHINE_ARM_ROTATION = "machine_arm_rotation"
    NFC_START = "nfc_start"
    CHECK_SIGNALS = "check_signals"

class MessageFrame(BaseModel):
    channel: int = 0
    identifier: Union[int, str]
    data: List[int]
    is_extended_id: bool = False

class TestStep(BaseModel):
    step_id: str
    step_type: StepType
    order: int
    message: Optional[MessageFrame] = None
    duration_ms: Optional[int] = None
    zone_value: Optional[int] = None
    angle: Optional[int] = None
    conditions: Optional[List[Dict]] = None

class ECUSimulationScenario(BaseModel):
    scenario_name: str
    channel: int = 0
    steps: List[TestStep]`;

slide8.addText(code3, {
    x: 0.5, y: 1.4, w: 9, h: 4.0,
    fontSize: 10, color: colors.text, fontFace: 'Courier New',
    fill: { color: '0D0D12' },
    inset: 0.2
});

// ===== 第9页：测试步骤类型（1/2） =====
let slide9 = createSlide('🔌 测试步骤类型（1/2）');

const stepTypes1 = [
    { icon: '🔌', name: 'INIT', type: '初始化', desc: '初始化测试环境，启动TSMaster报文记录（BLF格式），设置日志文件路径' },
    { icon: '📤', name: 'SEND_SINGLE', type: '报文发送', desc: '发送单帧CAN/CANFD报文，支持标准帧和扩展帧，可配置数据长度码' },
    { icon: '🔄', name: 'START_CYCLIC', type: '周期发送', desc: '启动周期报文发送，可配置发送周期（10ms-60s），模拟持续信号输出' },
    { icon: '📥', name: 'RECEIVE', type: '报文接收', desc: '接收并验证总线报文，可指定期望接收的报文ID列表，支持超时检测' },
    { icon: '⏸️', name: 'WAIT', type: '延时等待', desc: '等待指定时长，用于模拟真实场景中的时间延迟，或等待系统响应' }
];

yPos = 1.4;
stepTypes1.forEach((step, idx) => {
    slide9.addShape('rect', { x: 0.5, y: yPos, w: 9, h: 0.75, fill: { color: idx % 2 === 0 ? colors.cardBg : '0A0A0F' } });
    slide9.addText(step.icon, { x: 0.6, y: yPos + 0.15, w: 0.4, h: 0.4, fontSize: 18 });
    slide9.addText(step.name, { x: 1.0, y: yPos + 0.15, w: 2, h: 0.3, fontSize: 13, color: colors.text, bold: true });
    slide9.addText(step.type, { x: 2.8, y: yPos + 0.15, w: 1.5, h: 0.3, fontSize: 11, color: colors.accent });
    slide9.addText(step.desc, { x: 4.2, y: yPos + 0.15, w: 5, h: 0.5, fontSize: 10, color: colors.textSecondary });
    yPos += 0.85;
});

// ===== 第10页：测试步骤类型（2/2） =====
let slide10 = createSlide('🚗 测试步骤类型（2/2）');

const stepTypes2 = [
    { icon: '🚗', name: 'SMART_CAR_SWITCH', type: '智能小车', desc: '智能小车单次按键控制 (switch_value + keytime_ms)' },
    { icon: '🔛', name: 'SMART_CAR_SWITCH_ALLTIME', type: '持续开关', desc: '智能小车持续开关控制 (switch_value + enable_disable)' },
    { icon: '📍', name: 'SMART_CAR_ZONE', type: '区域控制', desc: '智能小车区域移动控制 (zone_value)' },
    { icon: '🦾', name: 'MACHINE_ARM_ROTATION', type: '机械臂', desc: '机械臂旋转控制 (angle: 0-180度)' },
    { icon: '💳', name: 'NFC_START', type: 'NFC刷卡', desc: '机械臂NFC刷卡触发 (name: 测试名称标识)，带视频录制' },
    { icon: '🔍', name: 'CHECK_SIGNALS', type: '信号检查', desc: '检查信号条件是否满足（支持多信号、时序检查）' },
    { icon: '📊', name: 'DECODE_SIGNALS', type: '信号解码', desc: '从CAN/CANFD报文解码信号' }
];

yPos = 1.3;
stepTypes2.forEach((step, idx) => {
    slide10.addShape('rect', { x: 0.5, y: yPos, w: 9, h: 0.65, fill: { color: idx % 2 === 0 ? colors.cardBg : '0A0A0F' } });
    slide10.addText(step.icon, { x: 0.6, y: yPos + 0.12, w: 0.4, h: 0.35, fontSize: 16 });
    slide10.addText(step.name, { x: 1.0, y: yPos + 0.12, w: 2.2, h: 0.25, fontSize: 12, color: colors.text, bold: true });
    slide10.addText(step.type, { x: 3.0, y: yPos + 0.12, w: 1.3, h: 0.25, fontSize: 10, color: colors.accent });
    slide10.addText(step.desc, { x: 4.2, y: yPos + 0.12, w: 5, h: 0.45, fontSize: 9, color: colors.textSecondary });
    yPos += 0.72;
});

// ===== 第11页：五步工作流程（1/2） =====
let slide11 = createSlide('📋 五步完成测试流程（1/2）', '用户零代码，Agent全自动');

// 步骤1
slide11.addShape('oval', { x: 0.5, y: 1.5, w: 0.7, h: 0.7, fill: { color: '4FACFE' } });
slide11.addText('1', { x: 0.5, y: 1.55, w: 0.7, h: 0.6, fontSize: 28, color: colors.text, bold: true, align: 'center' });
slide11.addText('👤 用户', { x: 1.4, y: 1.45, w: 2, h: 0.25, fontSize: 12, color: colors.accent });
slide11.addText('要求从Excel读取测试用例', { x: 1.4, y: 1.75, w: 4, h: 0.3, fontSize: 16, color: colors.text, bold: true });
slide11.addText('"请从Excel文件读取测试用例，执行数字钥匙认证测试场景"', { x: 1.4, y: 2.15, w: 7, h: 0.3, fontSize: 11, color: colors.textSecondary, italic: true });

// 步骤2
slide11.addShape('oval', { x: 0.5, y: 2.8, w: 0.7, h: 0.7, fill: { color: '667EEA' } });
slide11.addText('2', { x: 0.5, y: 2.85, w: 0.7, h: 0.6, fontSize: 28, color: colors.text, bold: true, align: 'center' });
slide11.addText('🤖 Agent', { x: 1.4, y: 2.75, w: 2, h: 0.25, fontSize: 12, color: colors.accent });
slide11.addText('自动构建测试场景', { x: 1.4, y: 3.05, w: 4, h: 0.3, fontSize: 16, color: colors.text, bold: true });
slide11.addText('Agent理解用户需求，自动转换为结构化测试场景，配置测试步骤、报文参数和信号检查条件', { x: 1.4, y: 3.45, w: 7.5, h: 0.4, fontSize: 10, color: colors.textSecondary });

// 步骤3
slide11.addShape('oval', { x: 0.5, y: 4.1, w: 0.7, h: 0.7, fill: { color: '667EEA' } });
slide11.addText('3', { x: 0.5, y: 4.15, w: 0.7, h: 0.6, fontSize: 28, color: colors.text, bold: true, align: 'center' });
slide11.addText('🤖 Agent', { x: 1.4, y: 4.05, w: 2, h: 0.25, fontSize: 12, color: colors.accent });
slide11.addText('执行测试序列', { x: 1.4, y: 4.35, w: 4, h: 0.3, fontSize: 16, color: colors.text, bold: true });
slide11.addText('自动调用MCP工具，建立TSMaster连接，执行CAN报文收发、智能小车控制和信号检查', { x: 1.4, y: 4.75, w: 7.5, h: 0.4, fontSize: 10, color: colors.textSecondary });

// ===== 第12页：五步工作流程（2/2） =====
let slide12 = createSlide('📋 五步完成测试流程（2/2）');

// 步骤4
slide12.addShape('oval', { x: 0.5, y: 1.4, w: 0.7, h: 0.7, fill: { color: '667EEA' } });
slide12.addText('4', { x: 0.5, y: 1.45, w: 0.7, h: 0.6, fontSize: 28, color: colors.text, bold: true, align: 'center' });
slide12.addText('🤖 Agent', { x: 1.4, y: 1.35, w: 2, h: 0.25, fontSize: 12, color: colors.accent });
slide12.addText('自动验证信号', { x: 1.4, y: 1.65, w: 4, h: 0.3, fontSize: 16, color: colors.text, bold: true });
slide12.addText('自动解码CAN报文，验证信号值是否符合预期。支持时序检查（连续多帧保持值）和多信号联合验证', { x: 1.4, y: 2.05, w: 7.5, h: 0.4, fontSize: 10, color: colors.textSecondary });

// 步骤5
slide12.addShape('oval', { x: 0.5, y: 2.9, w: 0.7, h: 0.7, fill: { color: '667EEA' } });
slide12.addText('5', { x: 0.5, y: 2.95, w: 0.7, h: 0.6, fontSize: 28, color: colors.text, bold: true, align: 'center' });
slide12.addText('🤖 Agent', { x: 1.4, y: 2.85, w: 2, h: 0.25, fontSize: 12, color: colors.accent });
slide12.addText('自动回填测试结果到Excel', { x: 1.4, y: 3.15, w: 5, h: 0.3, fontSize: 16, color: colors.text, bold: true });
slide12.addText('测试完成后，Agent自动使用Excel skill将执行结果、耗时、通过/失败状态回填到原始测试用例表格中，生成完整测试报告', { x: 1.4, y: 3.55, w: 7.5, h: 0.5, fontSize: 10, color: colors.textSecondary });

// 底部强调
slide12.addShape('rect', { x: 0.5, y: 4.6, w: 9, h: 0.7, fill: { color: colors.primary } });
slide12.addText('💡 用户只需用自然语言描述需求，Agent完成所有技术工作！', {
    x: 0.5, y: 4.75, w: 9, h: 0.4, fontSize: 16, color: colors.text, bold: true, align: 'center'
});

// ===== 第13页：完整测试示例 - DKC数字钥匙 =====
let slide13 = createSlide('📝 完整测试示例 - DKC数字钥匙认证测试');

slide13.addText('测试场景：通过智能小车搭载数字钥匙模拟数字钥匙靠近车辆、身份认证、解锁车门', {
    x: 0.5, y: 1.1, w: 9, h: 0.4, fontSize: 13, color: colors.textSecondary, italic: true
});

const dkcSteps = [
    { step: '1', type: 'INIT', desc: '初始化测试环境，启动CAN报文记录' },
    { step: '2', type: 'SEND_SINGLE', desc: '发送数字钥匙唤醒信号 (NW_WakeUP_signal)' },
    { step: '3', type: 'SMART_CAR_ZONE', desc: '智能小车移动到区域2 (模拟钥匙靠近)' },
    { step: '4', type: 'WAIT', desc: '等待车辆响应' },
    { step: '5', type: 'CHECK_SIGNALS', desc: '检查DKC认证状态信号' },
    { step: '6', type: 'SWITCH', desc: '通过智能小车控制数字钥匙模拟按键解锁' },
    { step: '7', type: 'CHECK_SIGNALS', desc: '验证DoorUnLock信号 (0x251)' },
    { step: '8', type: 'CHECK_SIGNALS', desc: '验证AllDoorSW信号 (0x116)' }
];

yPos = 1.6;
dkcSteps.forEach((item, idx) => {
    slide13.addShape('rect', { x: 0.5, y: yPos, w: 9, h: 0.45, fill: { color: idx % 2 === 0 ? colors.cardBg : '0A0A0F' } });
    slide13.addText(item.step, { x: 0.6, y: yPos + 0.08, w: 0.3, h: 0.25, fontSize: 12, color: colors.accent, bold: true });
    slide13.addText(item.type, { x: 0.9, y: yPos + 0.08, w: 1.8, h: 0.25, fontSize: 11, color: colors.text });
    slide13.addText(item.desc, { x: 2.8, y: yPos + 0.08, w: 6.5, h: 0.3, fontSize: 10, color: colors.textSecondary });
    yPos += 0.52;
});

// ===== 第14页：完整测试示例 - 智能小车 =====
let slide14 = createSlide('🚗 完整测试示例 - 智能小车区域移动测试');

const carSteps = [
    { step: '1', type: 'INIT', desc: '初始化' },
    { step: '2', type: 'SMART_CAR_ZONE', desc: '移动到Zone 0 (远离车辆)' },
    { step: '3', type: 'WAIT', desc: '等待移动完成' },
    { step: '4', type: 'SMART_CAR_ZONE', desc: '移动到Zone 1 (进入迎宾区)' },
    { step: '5', type: 'WAIT', desc: '等待并验证迎宾信号' },
    { step: '6', type: 'SMART_CAR_ZONE', desc: '移动到Zone 2 (进入解锁区)' },
    { step: '7', type: 'CHECK_SIGNALS', desc: '检查解锁信号' },
    { step: '8', type: 'SMART_CAR_SWITCH', desc: '按下开关测试 (模拟按键)' }
];

yPos = 1.3;
carSteps.forEach((item, idx) => {
    slide14.addShape('rect', { x: 0.5, y: yPos, w: 9, h: 0.45, fill: { color: idx % 2 === 0 ? colors.cardBg : '0A0A0F' } });
    slide14.addText(item.step, { x: 0.6, y: yPos + 0.08, w: 0.3, h: 0.25, fontSize: 12, color: colors.accent, bold: true });
    slide14.addText(item.type, { x: 0.9, y: yPos + 0.08, w: 2.2, h: 0.25, fontSize: 11, color: colors.text });
    slide14.addText(item.desc, { x: 3.2, y: yPos + 0.08, w: 6, h: 0.3, fontSize: 10, color: colors.textSecondary });
    yPos += 0.52;
});

// ===== 第15页：完整测试示例 - 机械臂NFC =====
let slide15 = createSlide('🦾 完整测试示例 - 机械臂NFC刷卡测试');

slide15.addText('模拟NFC卡片刷卡动作并录制视频', {
    x: 0.5, y: 1.1, w: 9, h: 0.3, fontSize: 13, color: colors.textSecondary, italic: true
});

const nfcSteps = [
    { step: '1', type: 'INIT', desc: '初始化CAN记录' },
    { step: '2', type: 'MACHINE_ARM_ROTATION', desc: '机械臂旋转到初始位置 (0°)' },
    { step: '3', type: 'WAIT', desc: '等待机械臂就位' },
    { step: '4', type: 'MACHINE_ARM_ROTATION', desc: '旋转到刷卡位置 (90°)' },
    { step: '5', type: 'NFC_START', desc: '执行NFC刷卡 (带视频录制)' },
    { step: '6', type: 'WAIT', desc: '等待刷卡响应' },
    { step: '7', type: 'CHECK_SIGNALS', desc: '检查NFC认证信号' },
    { step: '8', type: 'MACHINE_ARM_ROTATION', desc: '机械臂归位 (0°)' }
];

yPos = 1.5;
nfcSteps.forEach((item, idx) => {
    slide15.addShape('rect', { x: 0.5, y: yPos, w: 9, h: 0.45, fill: { color: idx % 2 === 0 ? colors.cardBg : '0A0A0F' } });
    slide15.addText(item.step, { x: 0.6, y: yPos + 0.08, w: 0.3, h: 0.25, fontSize: 12, color: colors.accent, bold: true });
    slide15.addText(item.type, { x: 0.9, y: yPos + 0.08, w: 2.5, h: 0.25, fontSize: 11, color: colors.text });
    slide15.addText(item.desc, { x: 3.5, y: yPos + 0.08, w: 5.7, h: 0.3, fontSize: 10, color: colors.textSecondary });
    yPos += 0.52;
});

// ===== 第16页：测试执行报告 =====
let slide16 = createSlide('📊 测试执行报告示例');

slide16.addText('DKC数字钥匙认证测试执行结果', {
    x: 0.5, y: 1.0, w: 9, h: 0.3, fontSize: 14, color: colors.text, bold: true
});

// 表格头部
slide16.addShape('rect', { x: 0.5, y: 1.4, w: 9, h: 0.4, fill: { color: colors.primary } });
slide16.addText('步骤ID', { x: 0.6, y: 1.45, w: 1.5, h: 0.3, fontSize: 11, color: colors.text, bold: true });
slide16.addText('类型', { x: 2.0, y: 1.45, w: 1.5, h: 0.3, fontSize: 11, color: colors.text, bold: true });
slide16.addText('描述', { x: 3.5, y: 1.45, w: 3, h: 0.3, fontSize: 11, color: colors.text, bold: true });
slide16.addText('状态', { x: 6.8, y: 1.45, w: 1, h: 0.3, fontSize: 11, color: colors.text, bold: true });
slide16.addText('耗时', { x: 8.0, y: 1.45, w: 1, h: 0.3, fontSize: 11, color: colors.text, bold: true });

// 表格数据
const results = [
    { id: 'init', type: 'INIT', desc: '初始化环境', status: '✓ PASSED', time: '150ms' },
    { id: 'send_dkey_wake', type: 'SEND_SINGLE', desc: '发送唤醒信号', status: '✓ PASSED', time: '50ms' },
    { id: 'car_move_zone2', type: 'SMART_CAR_ZONE', desc: '小车移动到Zone 2', status: '✓ PASSED', time: '2500ms' },
    { id: 'wait_auth', type: 'WAIT', desc: '等待认证响应', status: '✓ PASSED', time: '3000ms' },
    { id: 'check_dkey_auth', type: 'CHECK_SIGNALS', desc: '验证认证信号', status: '✓ PASSED', time: '1040ms' },
    { id: 'send_unlock', type: 'SEND_SINGLE', desc: '发送解锁指令', status: '✓ PASSED', time: '45ms' },
    { id: 'check_unlock', type: 'CHECK_SIGNALS', desc: '验证车门解锁', status: '✓ PASSED', time: '520ms' }
];

yPos = 1.85;
results.forEach((row, idx) => {
    slide16.addShape('rect', { x: 0.5, y: yPos, w: 9, h: 0.38, fill: { color: idx % 2 === 0 ? colors.cardBg : '0A0A0F' } });
    slide16.addText(row.id, { x: 0.6, y: yPos + 0.08, w: 1.4, h: 0.25, fontSize: 9, color: colors.text });
    slide16.addText(row.type, { x: 2.0, y: yPos + 0.08, w: 1.4, h: 0.25, fontSize: 9, color: colors.text });
    slide16.addText(row.desc, { x: 3.5, y: yPos + 0.08, w: 3.2, h: 0.25, fontSize: 9, color: colors.textSecondary });
    slide16.addText(row.status, { x: 6.8, y: yPos + 0.08, w: 1.2, h: 0.25, fontSize: 9, color: '27C93F' });
    slide16.addText(row.time, { x: 8.0, y: yPos + 0.08, w: 0.8, h: 0.25, fontSize: 9, color: colors.textSecondary });
    yPos += 0.4;
});

// JSON结果
const jsonResult = `{
  "scenario_name": "DKC数字钥匙认证测试",
  "status": "completed",
  "total_steps": 7,
  "passed_steps": 7,
  "failed_steps": 0,
  "total_duration_ms": 9305
}`;

slide16.addText(jsonResult, {
    x: 0.5, y: 4.6, w: 9, h: 1.0,
    fontSize: 10, color: colors.text, fontFace: 'Courier New',
    fill: { color: '0D0D12' },
    inset: 0.15
});

// ===== 第17页：视频演示 =====
let slide17 = createSlide('📹 视频演示', '观看实际测试过程');

slide17.addText('OpenCode Agent DKC测试演示', {
    x: 0.5, y: 1.5, w: 9, h: 0.5, fontSize: 24, color: colors.text, bold: true, align: 'center'
});

slide17.addShape('rect', { x: 1.5, y: 2.2, w: 7, h: 3.5, fill: { color: colors.cardBg }, line: { color: colors.primary, width: 2 } });
slide17.addText('🎬', { x: 4, y: 3.5, w: 2, h: 1, fontSize: 60, align: 'center' });
slide17.addText('DKC_TEST.gif', { x: 2, y: 4.8, w: 6, h: 0.3, fontSize: 12, color: colors.textSecondary, align: 'center', fontFace: 'Courier New' });

// ===== 第18页：结尾页 =====
let slide18 = pptx.addSlide();
slide18.background = { color: colors.dark };
slide18.addText('🚗', { x: 4.5, y: 1.5, w: 1, h: 0.8, fontSize: 60, align: 'center' });
slide18.addText('OpenCode DKC Testing', { x: 0.5, y: 2.5, w: 9, h: 0.7, fontSize: 40, color: colors.text, bold: true, align: 'center' });
slide18.addText('基于MCP协议的车载DKC智能测试解决方案', { x: 0.5, y: 3.4, w: 9, h: 0.5, fontSize: 18, color: colors.textSecondary, align: 'center' });
slide18.addText('让测试更智能、更高效、更可靠', { x: 0.5, y: 4.2, w: 9, h: 0.5, fontSize: 24, color: colors.accent, bold: true, align: 'center' });

// 保存
pptx.writeFile({ fileName: 'OpenCode_Agent_DKC测试指南_完整版.pptx' })
    .then(() => console.log('完整版PPTX已生成!'))
    .catch(err => console.error('生成失败:', err));
