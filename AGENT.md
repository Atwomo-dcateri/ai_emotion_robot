# AI Emotion Robot — 项目架构报告

## 项目概述

AI Emotion Robot 是一个运行在 **树莓派 (Raspberry Pi) + STM32** 双处理器架构上的情感交互机器人。它通过摄像头捕捉用户面部表情、麦克风拾取语音、MAX30102 传感器采集心率和血氧，多模态融合判断用户情绪状态后，通过 OLED 显示表情、舵机做动作、扬声器语音回复来与用户互动。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Raspberry Pi (上位机)                         │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ Vision   │  │  Audio   │  │  Comm      │  │  Decision     │  │
│  │ Module   │  │Controller│  │ Controller │  │  Controller   │  │
│  │ (OpenCV) │  │ (Vosk+)  │  │ (Serial)   │  │ (LLM/Rules)   │  │
│  └────┬─────┘  └────┬─────┘  └─────┬──────┘  └───────┬───────┘  │
│       │             │              │                  │          │
│       └──────┬──────┘              │                  │          │
│              │                     │                  │          │
│        ┌─────▼──────┐             │                  │          │
│        │   Fusion   │◄────────────┘                  │          │
│        │   Module   │                                │          │
│        └─────┬──────┘                                │          │
│              │                                       │          │
│              └──────────────────┬────────────────────┘          │
│                                 │                                │
│                          ┌──────▼──────┐                        │
│                          │  主循环      │                        │
│                          │  main.py    │                        │
│                          └──────┬──────┘                        │
└─────────────────────────────────┼────────────────────────────────┘
                                  │ UART (自定义帧协议)
┌─────────────────────────────────┼────────────────────────────────┐
│                     STM32 (下位机)                                │
│                          ┌──────▼──────┐                        │
│                          │  通信解析器   │                        │
│                          │  Parser     │                        │
│                          └──────┬──────┘                        │
│                                 │                                │
│                    ┌────────────┼────────────┐                  │
│                    ▼            ▼            ▼                  │
│             ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│             │ OLED     │ │ Servo    │ │ MAX30102 │            │
│             │ 显示屏    │ │ 舵机     │ │ 心率血氧  │            │
│             └──────────┘ └──────────┘ └──────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 硬件平台

| 组件 | 型号/规格 | 接口 |
|------|----------|------|
| 上位机 | Raspberry Pi (任一版本) | UART (/dev/serial0) |
| 下位机 | STM32 (Blue Pill 等) | USART1 |
| 摄像头 | USB 摄像头 / CSI | V4L2 |
| 麦克风 | USB 麦克风 | ALSA / PyAudio |
| 扬声器 | 3.5mm / HDMI 音频 | ALSA |
| 显示屏 | OLED SSD1306/SH1106 128×64 | I2C (bit-bang GPIO) |
| 心率血氧 | MAX30102 | I2C (bit-bang PB8/PB9) |
| 舵机 | 标准 PWM 舵机 (×2: 点头/摇头) | TIM2 PWM |

> **注意**: OLED 和 MAX30102 在 STM32 侧使用 GPIO 模拟 I2C（bit-bang），非硬件 I2C 外设。

---

## 软件模块详解

### 1. 视觉模块 [vision/]

**文件:**
- [vision/base.py](vision/base.py) — 抽象接口 `VisionInterface`
- [vision/vision.py](vision/vision.py) — `VisionModule` 实现（多线程 + 队列）
- [vision/face_analyzer.py](vision/face_analyzer.py) — 基于 Haar Cascade 的表情分类

**数据流:**
```
Camera → _camera_reader [线程] → FrameQueue → _face_detector [线程]
                                               → FaceAnalyzer.detect_faces()
                                               → FaceAnalyzer.analyze_emotion()
                                               → ResultQueue → get_emotion()
```

**识别结果:**
```json
{
  "emotion": "happy",        // 英文标签
  "emotion_cn": "开心",      // 中文标签
  "confidence": 85.0,       // 置信度 0-100
  "face_count": 1,          // 检测到的人脸数
  "region": (x, y, w, h)    // 人脸区域坐标
}
```

**支持 6 种表情:** 开心 / 悲伤 / 愤怒 / 恐惧 / 惊讶 / 平静，基于眼睛大小和嘴巴大小/位置规则分类。

---

### 2. 语音模块 [audio/]

**文件:**
- [audio/base.py](audio/base.py) — 抽象接口 `SpeechRecognitionInterface` + `SpeechSynthesisInterface`
- [audio/speech_recognition.py](audio/speech_recognition.py) — Vosk 离线语音识别（支持重采样）
- [audio/speech_synthesis.py](audio/speech_synthesis.py) — espeak 离线语音合成
- [audio/audio_controller.py](audio/audio_controller.py) — 状态机控制器

**状态机:**
```
IDLE ──(唤醒词)──→ LISTENING ──(超时)──→ PROCESSING ──(respond())──→ SPEAKING
  ↑                                                                       │
  └───────────────────────────────────────────────────────────────────────┘
```

**关键特性:**
- 唤醒词: "你好" / "小机器人"（可配置）
- STT: Vosk 离线模型，自动检测硬件采样率并重采样至 16kHz
- TTS: espeak，支持中英文切换
- 主动提问: `ask_question()` 实现交互式问答

---

### 3. 通信模块 [communication/]

**文件:**
- [communication/base.py](communication/base.py) — 抽象接口 `CommunicationInterface`
- [communication/protocol.py](communication/protocol.py) — 帧协议编解码（打包/解析/CRC）
- [communication/serial_comm.py](communication/serial_comm.py) — 串口管理（粘包处理、自动重连）
- [communication/simulator.py](communication/simulator.py) — STM32 模拟器（无硬件调试用）
- [communication/comm_controller.py](communication/comm_controller.py) — 通信控制器（整合层）

#### 帧协议格式

```
┌──────┬──────┬──────┬──────────┬──────────┬──────┐
│ HEAD │ TYPE │ LEN  │ DATA(N)  │ CRC16    │ TAIL │
│ AA55 │  1B  │  1B  │  ≤250B   │  2B      │  BB  │
└──────┴──────┴──────┴──────────┴──────────┴──────┘
```

- **CRC**: CRC16-CCITT（多项式 0x1021，初值 0xFFFF）
- **最小帧**: 7 字节（空数据）
- **最大帧**: 261 字节

#### 帧类型

| 类型码 | 方向 | 名称 | 数据说明 |
|--------|------|------|---------|
| 0x01 | STM32→Pi | `TYPE_HEARTBEAT` | HR(1) + HR_OK(1) + SpO2(1) + O2_OK(1) |
| 0x03 | STM32→Pi | `TYPE_SENSOR_STATUS` | status(1) + err_code(1) |
| 0x04 | STM32→Pi | `TYPE_ACK` | 空 |
| 0x05 | STM32→Pi | `TYPE_NAK` | 空 |
| 0x10 | Pi→STM32 | `TYPE_OLED` | 见子命令 |
| 0x11 | Pi→STM32 | `TYPE_SERVO` | servo_id(1) + angle(1) + speed(1) |
| 0x12 | Pi→STM32 | `TYPE_QUERY_SENSOR` | 空 |
| 0x13 | Pi→STM32 | `TYPE_CONFIG` | interval_ms(4) |

#### OLED 子命令

| 子命令 | 名称 | 数据格式 |
|--------|------|---------|
| 0x00 | 显示表情 | `[CMD, 置信度, 名称长度, 名称UTF8...]` |
| 0x01 | 显示文本 | `[CMD, X, Y, 文本长度, 文本UTF8...]` |
| 0x02 | 清屏 | `[CMD]` |

---

### 4. STM32 固件 [stm32logic/]

**与树莓派侧的协议对应关系:**

| 树莓派 (Python) | STM32 (C) | 功能 |
|-----------------|-----------|------|
| `protocol.py` | `comm_protocol.c/.h` | 帧编解码 + CRC16 |
| `serial_comm.py` | `comm_parser.c/.h` | 串口数据接收 + 粘包解析 |
| `comm_controller.py` | `comm_handler.c/.h` | 指令分发 + 健康数据上报 |
| — | `comm_config.h` | 帧常量、类型定义、超时配置 |

**初始化流程 (app_main.c):**
```
vAppInit()
├── LED 初始化
├── OLED GPIO + I2C 探测
├── PWM + 舵机初始化
├── MAX30102 I2C 探测 + 初始化
│   └── 失败时 s_max30102_ok = 0（通信仍可用）
└── Parser + Handler 初始化 + UART 接收使能

vExecute() [主循环状态机]
├── phase 0: LED 闪烁 + OLED 显示 (±5s)
├── phase 1-4: 舵机自检 (0°→90°→180°→90°) (±4s)
├── phase 5: 舵机归中 + "Servo done!" (±1s)
└── phase 6: 通信处理 + 采样 + OLED 刷新（持续运行）
    ├── Parser_Process()   ← 解析接收到的协议帧
    ├── Handler_Tick()     ← 定时上报健康数据（1s 间隔）
    ├── MAX30102 算法（如有传感器）
    └── OLED 刷新
```

---

### 5. 融合模块 [fusion/]

**文件:**
- [fusion/base.py](fusion/base.py) — 抽象接口 `FusionInterface`
- [fusion/fusion.py](fusion/fusion.py) — `FusionModule` 实现

**职责:** 汇聚三大输入源，为决策模块提供统一的状态快照。

**返回的状态字典:**
```python
{
    'timestamp': float,           # Unix 时间戳
    'has_face': bool,             # 是否检测到人脸
    'face_emotion': dict|None,    # 视觉情绪结果
    'speech_text': str|None,      # 语音输入文本
    'speech_has_new': bool,       # 是否有未消费的语音
    'heart_rate': int|None,       # 心率值
    'heart_rate_valid': bool,     # 心率是否有效
    'oxygen': int|None,           # 血氧值
    'oxygen_valid': bool,         # 血氧是否有效
    'is_finger_detected': bool,   # 手指是否在传感器上
    'sensor_status': str|None,    # 传感器状态
    'is_health_data_fresh': bool, # 健康数据是否在有效期内（3s）
    'fusion_ready': bool          # 融合数据是否可用
}
```

---

### 6. 决策模块 [decision/]

**文件:**
- [decision/base.py](decision/base.py) — 抽象接口 + 动作类型枚举 + 工厂函数
- [decision/rule_engine.py](decision/rule_engine.py) — 规则引擎（离线可用）
- [decision/llm_engine.py](decision/llm_engine.py) — DeepSeek LLM 引擎
- [decision/decision_controller.py](decision/decision_controller.py) — 决策控制器（切换 LLM/规则）

**决策优先级:**
```
LLM 可用? ──是──→ LLMEngine.decide()
                  └── 失败/超时 ──→ 降级
否 ─────────────────────┘

RuleEngine.decide():
  1. 健康告警 (高心率/低血氧/传感器错误)  ← 最高优先级
  2. 语音关键词响应
  3. 情绪响应
  4. 默认: 无动作
```

**动作指令格式:**
```python
[
    {'type': 'oled',       'emotion': '开心', 'confidence': 85},
    {'type': 'oled_text',  'text': '你好', 'x': 0, 'y': 0},
    {'type': 'speak',      'text': '你好呀'},
    {'type': 'servo',      'move': 'nod', 'times': 1},
    {'type': 'wait',       'duration': 0.5},
    {'type': 'none'},
]
```

---

## 主循环流程 (main.py)

```
初始化各模块 → 启动服务 → 进入主循环

主循环每 50ms:
  state = fusion.get_user_state()
  if state['has_face'] or state['speech_has_new'] or state['is_finger_detected']:
      actions = decision.decide(state)
      for action in actions:
          if oled:       → comm.send_oled_emotion()
          if oled_text:  → comm.send_oled_text()
          if speak:      → audio.respond()
          if servo:      → comm.send_servo_move()
          if wait:       → time.sleep()
```

---

## 配置说明 [config.py](config.py)

配置类 `Config` 集中管理所有模块的参数，通过 `getattr(config, 'KEY', default)` 模式读取，每个模块可以独立开关：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `CAMERA_ID` | `0` | 摄像头设备 ID |
| `VISION_ENABLED` | `True` | 启用视觉模块 |
| `AUDIO_STT_ENGINE` | `"vosk"` | 语音识别引擎 |
| `AUDIO_TTS_ENGINE` | `"espeak"` | 语音合成引擎 |
| `COMM_SERIAL_PORT` | `"/dev/serial0"` | 串口设备路径 |
| `COMM_BAUDRATE` | `115200` | 串口波特率 |
| `COMM_SIMULATION_MODE` | `False` | 是否使用 STM32 模拟器 |
| `DECISION_USE_LLM` | `True` | 是否启用 LLM 决策 |
| `DECISION_LLM_API_KEY` | 环境变量 | DeepSeek API 密钥 |
| `OLED_ENABLED` | `True` | 启用 OLED 显示 |
| `LOG_LEVEL` | `"INFO"` | 日志级别 |

---

## 开发指南

### 环境要求

```bash
# 树莓派
pip install opencv-python vosk pyaudio numpy scipy pyserial requests

# Vosk 中文模型
wget https://.../vosk-model-small-cn-0.22.zip
unzip vosk-model-small-cn-0.22.zip -d models/

# espeak 语音合成
sudo apt-get install espeak
```

### 运行

```bash
# 主程序
python3 main.py

# 连通性测试（无需协议）
sudo python3 test_comm_ping.py --send

# 协议查询测试
sudo python3 test_comm_ping.py --query

# 全指令硬件测试
sudo python3 test_comm_hardware.py

# 循环监控健康数据
sudo python3 test_comm_hardware.py --loop
```

### STM32 固件编译

STM32 源码位于 [stm32logic/](stm32logic/)，使用 Keil / STM32CubeIDE 编译，将 `app_main.c` 及 `communication/` 目录下的文件加入项目即可。

---

## 通信调试检查清单

当上位机和下位机通信异常时，按以下顺序排查：

1. **硬件连接**: Pi TX(GPIO14) ↔ STM32 RX, Pi RX(GPIO15) ↔ STM32 TX, GND ↔ GND
2. **串口可用**: `ls -l /dev/serial0` → 应指向 `ttyAMA0`
3. **控制台占用**: `sudo systemctl status serial-getty@ttyAMA0.service` → 应为 `inactive`
4. **字节回显**: `test_comm_ping.py --send` → 应收到 `hello\n` 回显
5. **协议帧**: `test_comm_ping.py --query` → 应收到 HEARTBEAT + ACK 帧
6. **OLED/舵机**: `test_comm_hardware.py` → OLED 显示 + 舵机动作
7. **数据上报**: 等待 1s 后 `Handler_Tick()` 自动上报健康数据

---

## 项目文件索引

| 文件 | 说明 |
|------|------|
| [config.py](config.py) | 全局配置 |
| [mainpybak](mainpybak) | 主循环入口 |
| [vision/](vision/) | 视觉模块（人脸检测 + 表情分析） |
| [audio/](audio/) | 语音模块（Vosk STT + espeak TTS） |
| [communication/](communication/) | 通信模块（串口 + 帧协议 + STM32 驱动） |
| [fusion/](fusion/) | 融合模块（多模态数据汇聚） |
| [decision/](decision/) | 决策模块（LLM + 规则引擎） |
| [stm32logic/](stm32logic/) | STM32 固件源码 |
| [doc/](doc/) | 各模块 API 文档 |
| [test_comm_ping.py](test_comm_ping.py) | 串口连通性测试（裸收发） |
| [test_comm_hardware.py](test_comm_hardware.py) | 硬件全指令测试 |
| [通信模块测试任务.md](通信模块测试任务.md) | 通信测试任务跟踪 |
