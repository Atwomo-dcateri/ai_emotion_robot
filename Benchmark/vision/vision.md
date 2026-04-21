作为嵌入式测试工程师，我已审阅并记录当前 `audio` 模块的完整代码。以下是更新后的模块状态记录。

---

## Audio 模块代码状态记录（2026-04-21）

### 一、文件清单

| 文件 | 状态 | 关键特性 |
|------|------|----------|
| `audio_controller.py` | ⚠️ 有重复方法 | 状态机，含两个 `_handle_listening` |
| `speech_recognition.py` | ✅ 已优化 | Vosk + 重采样 + 唤醒词过滤开关 |
| `speech_synthesis.py` | ✅ 稳定 | espeak 命令行 TTS |

---

### 二、当前代码问题

#### 问题 1：`audio_controller.py` 存在两个 `_handle_listening` 方法

**位置**：第 130 行和第 165 行

```python
# 第一个版本（简单版）
def _handle_listening(self):
    self._wake_word_enabled = False
    start_time = time.time()
    collected_text = []
    while time.time() - start_time < self._listen_timeout:
        text = self._stt.get_text()
        if text:
            collected_text.append(text)
            start_time = time.time()
        time.sleep(0.1)
    # ...

# 第二个版本（带过滤开关）
def _handle_listening(self):
    self._wake_word_enabled = False
    if hasattr(self._stt, 'enable_wake_word_filter'):
        self._stt.enable_wake_word_filter(False)
    # ...
```

**影响**：Python 会使用后定义的方法（第二个），第一个被覆盖。

**建议**：保留第二个版本（带 `enable_wake_word_filter`），删除第一个。

---

#### 问题 2：`start()` 方法中 `target_sample_rate` 被硬编码覆盖

**位置**：`speech_recognition.py` 第 170 行

```python
def start(self) -> bool:
    # ...
    self.device_sample_rate = self._detect_device_sample_rate()
    self.target_sample_rate = 16000  # ← 硬编码覆盖了配置值
```

**影响**：配置文件中设置的 `AUDIO_SAMPLE_RATE` 被忽略。

**建议**：删除这行，使用 `__init__` 中传入的 `sample_rate`。

---

#### 问题 3：`_detect_device_sample_rate` 返回值可能为 16000 但不准确

**位置**：`speech_recognition.py` 第 95-115 行

```python
def _detect_device_sample_rate(self) -> int:
    # ...
    test_rates = [44100, 48000, 16000, 8000]
    for rate in test_rates:
        try:
            is_supported = p.is_format_supported(...)
            if is_supported:
                return rate
        except:
            continue
    return 44100
```

**实际情况**：设备 2 不支持 16000，但 `is_format_supported` 可能返回 True（ALSA 插件支持转换）。

**建议**：优先使用设备默认采样率，而非测试列表第一个。

---

### 三、当前架构优点

| 特性 | 实现方式 |
|------|----------|
| 唤醒词过滤开关 | `enable_wake_word_filter(True/False)` |
| 重采样支持 | scipy / librosa / simple 三级降级 |
| 状态机 | IDLE → LISTENING → PROCESSING → SPEAKING |
| 回调机制 | `on_wake_word`, `on_state_change` |
| 资源管理 | `_cleanup()` 正确释放 PyAudio |

---

### 四、测试状态汇总

| 测试项 | 结果 | 备注 |
|--------|------|------|
| 测试1: 音频设备 | ✓ | 设备2 可用 |
| 测试2: TTS 播放 | ✓ | espeak 正常 |
| 测试3: 麦克风 | ✓ | 最大振幅 348 |
| 测试4: Vosk 模型 | ✓ | small 模型加载成功 |
| 测试5: 唤醒词检测 | ✓ | "你好" 识别成功 |
| 测试6: 状态机 | ✓ | 转换正常 |
| 测试7: 监听超时 | ✓ | 3秒超时正常 |
| 测试8: 完整对话 | ⚠️ 部分失败 | 短语音识别延迟 |

---

### 五、当前阻塞问题

**短语音识别延迟/失败**：
- 原因：Vosk 需要足够音频帧才能触发 `AcceptWaveform()`
- 临时方案：重复说多次或说长句子
- 待优化：增加部分结果收集和静音检测

---

### 六、记录已更新

我已记住当前模块的完整代码状态。后续讨论将基于此版本进行。