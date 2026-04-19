# AI Emotion Robot - Raspberry Pi Camera Version

一个运行在树莓派上的情感交互机器人项目，现已支持真实摄像头、表情分析和语音交互。

## 项目架构

```
ai_emotion_robot/
├── main_light.py          # 摄像头版主入口
├── main_oled_real.py      # 真实OLED显示版主入口
├── main_audio.py          # 音频交互版主入口
├── vision/                # 视觉模块（OpenCV人脸+表情分析）
├── hardware/              # 硬件模块（OLED驱动+模拟器）
├── decision/              # 决策引擎
├── audio/                 # 语音模块（录音+语音合成）
├── fusion/                # 多模态融合（预留）
├── test_*.py              # 测试脚本
├── setup_oled.sh          # OLED硬件设置脚本
└── utils/                 # 工具函数
```

## 当前功能

- ✅ **真实摄像头**：使用 OpenCV + Haar Cascade 人脸检测
- ✅ **表情分析**：基于面部特征（眼睛、嘴巴）分析表情
- ✅ **实时检测**：后台线程持续检测，0.5秒间隔
- ✅ **ASCII 显示**：控制台显示表情艺术
- ✅ **真实OLED显示**：支持SSD1306/SH1106硬件显示屏
- ✅ **像素表情**：16x16像素艺术表情显示
- ✅ **动画效果**：表情切换和闪烁动画
- ✅ **状态显示**：系统状态信息面板
- ✅ **语音录音**：USB麦克风录音功能
- ✅ **语音合成**：文字转语音播放
- ✅ **语音交互**：录音+识别+回复一体化
- ✅ **模块化设计**：保留原有架构，便于后续扩展
- ✅ **树莓派友好**：优化后的轻量实现

## 支持的表情类型

- 😐 **平静** (neutral) - 默认表情，检测到人脸但特征不明显
- 😊 **开心** (happy) - 检测到大嘴巴时
- 😲 **惊讶** (surprise) - 检测到大眼睛时
- 😢 **悲伤** (sad) - 检测到下垂嘴巴和较小眼睛
- 😠 **愤怒** (angry) - 检测到紧闭嘴巴和正常眼睛
- 😨 **恐惧** (fear) - 检测到大眼睛和大嘴巴位置较低

## 表情分析原理

使用 OpenCV Haar Cascade 检测器：
1. **人脸检测**：检测面部位置
2. **特征提取**：检测眼睛和嘴巴
3. **表情分类**：根据特征大小和位置推断表情
4. **置信度计算**：基于检测质量计算置信度

## 语音交互功能

### 硬件要求
- USB麦克风 (支持的设备: USB PnP Sound Device)
- 扬声器 (树莓派内置音频或外接扬声器)

### 语音功能
- 🎤 **录音功能**：使用 `arecord` 命令录音
- 🔊 **语音合成**：使用 Google Text-to-Speech (gTTS)
- 🎯 **语音识别**：简化实现，支持关键词识别
- 💬 **交互回复**：根据语音内容智能回复

### 支持的语音命令
- "你好" / "hello" → 问候回复
- "再见" / "bye" → 告别回复
- "开心" → 积极回应
- "难过" / "伤心" → 安慰回复

## 安装和运行

### 1. 环境要求
- Raspberry Pi 4 (或更高)
- Python 3.9+
- OpenCV 4.13+
- 摄像头模块
- USB麦克风
- OLED显示屏 (可选)

### 2. 安装依赖
```bash
cd /home/afr/project/ai_emotion_robot
python3 -m pip install -r requirements.txt
```

### 3. 运行不同版本

#### 摄像头版
```bash
python3 main_light.py
```

#### OLED显示版
```bash
python3 main_oled_real.py
```

#### 音频交互版 ⭐ **新增**
```bash
python3 main_audio.py
```

### 4. 音频版预期输出
```
============================================================
初始化AI情感机器人 - 音频版
============================================================

[SpeechRecognizer] 初始化完成 (使用系统命令模式)
[AudioModule] 音频模块初始化完成 (简化版)
所有模块初始化完成！

============================================================
AI情感机器人 - 音频版 启动中...
============================================================

[音频] 语音交互线程已启动
============================================================
机器人运行中... 按 Ctrl+C 退出
支持语音交互和视觉检测
============================================================

[视觉] 检测到表情: 平静 (置信度: 0.85)
[音频] 开始录音识别...
[音频] 用户说: 你好
[音频] 回复: 你好！我是AI情感机器人，很高兴见到你！
```

## OLED显示屏集成

### 硬件要求
- SSD1306 OLED显示屏 (128x64像素)
- I2C接口连接
- Raspberry Pi GPIO引脚

### 硬件连接
```
OLED VCC → Raspberry Pi 3.3V (Pin 1)
OLED GND → Raspberry Pi GND (Pin 6)
OLED SCL → Raspberry Pi SCL (Pin 5, GPIO 3)
OLED SDA → Raspberry Pi SDA (Pin 3, GPIO 2)
```

### OLED设置
1. **运行设置脚本**：
```bash
chmod +x setup_oled.sh
./setup_oled.sh
```

2. **手动配置**（如果脚本失败）：
```bash
# 启用I2C
sudo raspi-config nonint do_i2c 0

# 安装依赖
sudo apt-get install -y python3-dev i2c-tools
python3 -m pip install luma.oled luma.core pillow

# 检查I2C设备
i2cdetect -y 1
```

### OLED运行
```bash
# 真实OLED模式
python3 main_oled_real.py

# 模拟器模式（测试用）
python3 main_oled_real.py --simulator

# 指定I2C地址（如果不是0x3C）
python3 main_oled_real.py --i2c-address=0x3D
```

### OLED测试
```bash
# 测试OLED驱动
python3 test_oled_driver.py
```

### OLED表情显示
- **像素艺术**：16x16像素的表情图标
- **动画效果**：表情切换时的闪烁动画
- **状态面板**：显示系统状态和检测信息
- **实时更新**：跟随摄像头检测结果更新显示

## 后续扩展

当性能允许时，可以逐步添加：

1. **真实视觉**：安装 OpenCV，启用摄像头检测
2. **语音输入**：添加 SpeechRecognition
3. **情绪识别**：集成 DeepFace 或轻量模型
4. **硬件控制**：连接真实 OLED/舵机
5. **云决策**：启用 LLM 智能反应

## 性能考虑

- 当前版本 CPU 占用 < 5%
- 内存使用 < 50MB
- 适合树莓派 4B 长期运行

## 故障排除

- 如果运行出错，检查 Python 版本：`python3 --version`
- 确认依赖安装：`python3 -m pip list`
- 查看日志输出以诊断问题