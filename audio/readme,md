## audio模块方法说明文档

```markdown
# audio 模块 API 说明

## 模块概述

语音识别与合成模块，提供唤醒词检测、语音输入、语音输出功能。

**依赖要求（树莓派）：**
```bash
sudo apt-get install espeak espeak-data
pip3 install vosk pyaudio numpy
# 可选（提高重采样质量）：pip3 install scipy
```

---

## 一、核心类：AudioController

语音控制器，管理 STT/TTS 状态机。**推荐使用此类作为主要接口。**

### 初始化

```python
from audio import AudioController
from config import Config

ctrl = AudioController(Config)
```

### 生命周期

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `start()` | 启动语音服务 | `bool` |
| `stop()` | 停止所有语音服务 | `None` |

### 获取用户输入

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `get_user_input(timeout=0.1)` | 非阻塞获取语音输入 | `Optional[str]` |

```python
# 主循环中获取输入
while True:
    text = ctrl.get_user_input(timeout=0.1)
    if text:
        print(f"用户说: {text}")
```

### 语音回复

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `respond(text)` | 语音回复用户 | `bool` |

```python
ctrl.respond("你好，我是AI机器人")
```

### 主动提问

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `ask_question(text, timeout=10.0)` | 提问并等待回答 | `Optional[str]` |

```python
answer = ctrl.ask_question("你叫什么名字？", timeout=5.0)
if answer:
    print(f"用户回答: {answer}")
```

### 唤醒词控制

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `enable_wake_word(enable)` | 启用/禁用唤醒词监听 | `None` |
| `on_wake_word(callback)` | 注册唤醒词回调 | `None` |

```python
def on_wake():
    print("用户唤醒了我")

ctrl.on_wake_word(on_wake)
ctrl.enable_wake_word(True)   # 启用
```

### 状态监听

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `on_state_change(callback)` | 注册状态变化回调 | `None` |
| `get_state()` | 获取当前状态 | `str` |
| `is_speaking()` | 是否正在播放语音 | `bool` |

```python
def on_state(new_state, old_state):
    print(f"状态: {old_state} -> {new_state}")

ctrl.on_state_change(on_state)
print(ctrl.get_state())   # idle / listening / processing / speaking
```

---

## 二、状态机说明

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| `IDLE` | 空闲，监听唤醒词 | 启动后 / 播放完成 / 超时 |
| `LISTENING` | 监听用户输入 | 检测到唤醒词 |
| `PROCESSING` | 处理中（等待回复） | 获取到用户输入后 |
| `SPEAKING` | 播放语音 | 调用 `respond()` 后 |

**状态流转：**

```
IDLE ──(唤醒词)──> LISTENING ──(有输入)──> PROCESSING ──(respond)──> SPEAKING
  ^                    │                                    │
  └──(超时/完成)───────┴────────────────────────────────────┘
```

---

## 三、底层接口（高级用法）

如需直接使用 STT 或 TTS，可通过工厂函数创建。

### 语音识别

```python
from audio.speech_recognition import create_speech_recognition

stt = create_speech_recognition(config)  # config 需包含 AUDIO_STT_ENGINE 等配置

stt.start()
text = stt.get_text()   # 非阻塞获取
stt.stop()
```

**SpeechRecognitionInterface 方法：**

| 方法 | 说明 |
|------|------|
| `start()` | 启动识别 |
| `stop()` | 停止识别 |
| `get_text()` | 非阻塞获取识别文本 |
| `is_listening()` | 是否正在监听 |
| `set_wake_words(words)` | 设置唤醒词列表 |

### 语音合成

```python
from audio.speech_synthesis import create_speech_synthesis

tts = create_speech_synthesis(config)  # config 需包含 AUDIO_TTS_RATE 等配置

tts.speak("你好")                # 同步播放
tts.speak_async("你好")          # 异步播放，返回任务ID
tts.is_speaking()                # 是否正在播放
tts.stop()                       # 停止播放
tts.set_voice("zh+f1")           # 切换音色
```

**SpeechSynthesisInterface 方法：**

| 方法 | 说明 |
|------|------|
| `speak(text)` | 同步播放语音 |
| `speak_async(text)` | 异步播放，返回任务ID |
| `is_speaking()` | 是否正在播放 |
| `stop()` | 停止当前播放 |
| `set_voice(voice_id)` | 切换音色 |

**espeak 可用音色：**

| 音色 | 说明 |
|------|------|
| `zh` | 中文（男声，默认） |
| `zh+f1` | 中文（女声） |
| `zh+f2` | 中文（女声，更高音） |
| `en` | 英文 |
| `en-us` | 美式英语 |
| `en-uk` | 英式英语 |

---

## 四、配置项说明

`config.py` 中与 audio 模块相关的配置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `AUDIO_STT_ENGINE` | str | `"vosk"` | 固定为 vosk |
| `AUDIO_VOSK_MODEL_PATH` | str | `"models/vosk-model-cn-0.22"` | Vosk模型路径 |
| `AUDIO_WAKE_WORDS` | list | `["你好", "小机器人"]` | 唤醒词列表 |
| `AUDIO_LISTEN_TIMEOUT` | float | `5.0` | 监听超时（秒） |
| `AUDIO_SAMPLE_RATE` | int | `16000` | 目标采样率 |
| `AUDIO_DEVICE_INDEX` | int | `None` | 麦克风设备索引（可选） |
| `AUDIO_TTS_RATE` | int | `150` | 语速（单词/分钟） |
| `AUDIO_TTS_VOICE` | str | `"zh"` | 音色 |

---

## 五、完整使用示例

```python
#!/usr/bin/env python3
"""语音模块使用示例"""

import logging
from config import Config
from audio import AudioController

logging.basicConfig(level=logging.INFO)

def main():
    # 初始化
    ctrl = AudioController(Config)
    
    # 注册回调
    def on_wake():
        print("\n[唤醒] 我在听...")
    
    def on_state(new_state, old_state):
        print(f"[状态] {old_state} -> {new_state}")
    
    ctrl.on_wake_word(on_wake)
    ctrl.on_state_change(on_state)
    
    # 启动
    if not ctrl.start():
        print("启动失败")
        return
    
    print("机器人已启动，说唤醒词'你好'或'小机器人'开始对话")
    
    try:
        while True:
            text = ctrl.get_user_input(timeout=0.1)
            if text:
                if "再见" in text:
                    ctrl.respond("再见")
                    break
                elif "天气" in text:
                    ctrl.respond("我不太清楚天气呢")
                else:
                    ctrl.respond(f"你说：{text}")
    except KeyboardInterrupt:
        print("\n退出...")
    finally:
        ctrl.stop()

if __name__ == "__main__":
    main()
```

---

## 六、注意事项

1. **唤醒词**：默认启用，检测到后自动进入监听状态
2. **监听超时**：默认5秒无输入自动回到空闲状态
3. **主动提问**：会暂时禁用唤醒词，避免被自身语音误唤醒
4. **重采样**：若麦克风不支持16000Hz，模块自动重采样。建议安装 `scipy` 提高质量
5. **espeak**：首次使用前需安装 `sudo apt-get install espeak espeak-data`
6. **线程安全**：`get_user_input()` 和 `respond()` 可在任意线程调用

---

**文档版本：** v1.1  
**更新日期：** 2026-04-21
```