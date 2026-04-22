## Fusion模块 API 说明文档

```markdown
# Fusion 模块 API 说明

## 模块概述

多模态数据融合模块，汇集视觉（Vision）和语音（Audio）模块的输出，提供统一的用户状态接口。模块轻量聚合，不做复杂推理，以调用时刻的时间戳作为状态快照的统一时间。

**设计原则：**
- 轻量聚合，不做复杂推理
- 非阻塞读取各模块的 `get_xxx()` 接口
- 管理语音消费标记，避免重复处理

---

## 一、核心类：FusionModule

多模态数据融合模块，汇集 Vision 和 Speech 模块输出。

### 初始化

```python
from fusion import FusionModule
from config import Config

fusion = FusionModule(vision_module, audio_controller, config=Config)
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `vision_module` | VisionModule | 视觉模块实例 |
| `audio_controller` | AudioController | 音频控制器实例 |
| `config` | Config | 配置实例（可选） |

### 主要方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `get_user_state()` | 获取当前用户状态快照 | `Dict[str, Any]` |
| `has_face()` | 是否检测到人脸 | `bool` |
| `has_speech()` | 是否有新的语音输入（未消费） | `bool` |
| `get_emotion()` | 快捷获取情绪结果 | `Optional[Dict]` |
| `get_speech_text()` | 快捷获取语音文本（自动消费） | `Optional[str]` |
| `reset_speech_consumed()` | 重置语音消费标记 | `None` |
| `to_dict()` | `get_user_state()` 别名 | `Dict[str, Any]` |
| `get_pretty_state(state)` | 获取格式化的状态字符串 | `str` |

---

## 二、方法详解

### 1. `get_user_state()` - 获取用户状态快照

```python
state = fusion.get_user_state()
```

**返回值结构：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | float | Unix 时间戳 |
| `has_face` | bool | 是否检测到人脸 |
| `has_speech` | bool | 是否有新的语音输入 |
| `face_emotion` | dict \| None | 情绪结果（见下方结构） |
| `speech_text` | str \| None | 语音识别文本（仅当有新语音时） |
| `speech_has_new` | bool | 是否有未消费的新输入 |
| `heart_rate` | None | 预留生理模块 |
| `fusion_ready` | bool | 融合数据是否有效 |

**`face_emotion` 结构：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `emotion` | str | 英文标签：happy/sad/angry/fear/surprise/neutral |
| `emotion_cn` | str | 中文标签：开心/悲伤/愤怒/恐惧/惊讶/平静 |
| `confidence` | float | 置信度 0-100 |
| `face_count` | int | 检测到的人脸数量 |
| `region` | tuple | 人脸区域 (x, y, w, h) |

**示例：**
```python
state = fusion.get_user_state()
print(state)
# {
#     'timestamp': 1713715200.123,
#     'has_face': True,
#     'has_speech': True,
#     'face_emotion': {'emotion': 'happy', 'emotion_cn': '开心', 'confidence': 85.0, ...},
#     'speech_text': '你好',
#     'speech_has_new': True,
#     'heart_rate': None,
#     'fusion_ready': True
# }
```

---

### 2. `has_face()` - 检测是否有人脸

```python
if fusion.has_face():
    print("检测到人脸")
```

**返回值：** `True` 检测到人脸，`False` 无人脸

---

### 3. `has_speech()` - 是否有新语音输入

```python
if fusion.has_speech():
    print("有新语音输入，尚未处理")
```

**注意：** 此方法判断的是未消费的语音输入，调用 `get_speech_text()` 后会标记为已消费。

---

### 4. `get_emotion()` - 快捷获取情绪结果

```python
emotion = fusion.get_emotion()
if emotion:
    print(f"情绪: {emotion['emotion_cn']} ({emotion['confidence']:.0f}%)")
```

**返回值：** 情绪结果字典，无人脸时返回 `None`

---

### 5. `get_speech_text()` - 快捷获取语音文本

```python
text = fusion.get_speech_text()
if text:
    print(f"用户说: {text}")
```

**特点：**
- 自动消费语音（调用后 `has_speech()` 返回 `False`）
- 若无新语音返回 `None`

**注意：** 此方法不会主动从 AudioController 获取新语音，需先调用 `get_user_state()` 更新内部状态。

---

### 6. `reset_speech_consumed()` - 重置语音消费标记

```python
fusion.reset_speech_consumed()
```

**用途：** 手动重置语音消费状态，使语音可被重新获取

---

### 7. `get_pretty_state()` - 格式化状态输出

```python
state = fusion.get_user_state()
pretty = fusion.get_pretty_state(state)
print(pretty)

# 输出示例：
# [14:30:25] 用户状态:
#   人脸检测: ✓
#   新语音: ✓
#   情绪: 开心 (85%)
#   语音: 你好
```

**参数：**
- `state`: 状态字典（可选，为 None 时自动调用 `get_user_state()`）

---

## 三、配置项说明

`config.py` 中 Fusion 相关配置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `FUSION_CONSUME_SPEECH` | bool | True | 是否自动消费语音输入 |
| `FUSION_TIMESTAMP_FORMAT` | str | '%H:%M:%S' | 时间格式化（用于 `get_pretty_state()`） |

---

## 四、使用示例

### 示例 1：基础使用

```python
from config import Config
from vision import VisionModule
from audio import AudioController
from fusion import FusionModule

# 初始化模块
vision = VisionModule(Config)
audio = AudioController(Config)
fusion = FusionModule(vision, audio, Config)

# 启动服务
vision.start()
audio.start()

# 主循环
while True:
    state = fusion.get_user_state()

    if state['speech_has_new']:
        # 有新语音，优先处理
        print(f"用户说: {state['speech_text']}")
        audio.respond(f"你说的是：{state['speech_text']}")

    elif state['has_face']:
        # 有人脸，可触发主动交互
        emotion = state['face_emotion']['emotion_cn']
        print(f"检测到情绪: {emotion}")

    time.sleep(0.1)
```

### 示例 2：使用快捷方法

```python
# 检查人脸
if fusion.has_face():
    emotion = fusion.get_emotion()
    print(f"情绪: {emotion['emotion_cn']}")

# 检查语音（自动消费）
text = fusion.get_speech_text()
if text:
    print(f"语音: {text}")
    # 再次调用返回 None（已消费）
    text2 = fusion.get_speech_text()  # None
```

### 示例 3：手动消费模式

```python
# 禁用自动消费（在 config 中设置 FUSION_CONSUME_SPEECH = False）

state = fusion.get_user_state()
if state['speech_has_new']:
    # 手动决定何时消费
    if need_process:
        text = fusion.get_speech_text()
        process(text)
    else:
        # 丢弃当前语音
        fusion.reset_speech_consumed()
```

### 示例 4：调试输出

```python
state = fusion.get_user_state()
print(fusion.get_pretty_state(state))

# 输出：
# [10:30:45] 用户状态:
#   人脸检测: ✓
#   新语音: ✗
#   情绪: 平静 (70%)
```

---

## 五、语音消费机制说明

| 场景 | 行为 |
|------|------|
| `FUSION_CONSUME_SPEECH = True` | `get_user_state()` 返回后自动标记语音为已消费 |
| `FUSION_CONSUME_SPEECH = False` | 需手动调用 `get_speech_text()` 或 `reset_speech_consumed()` |
| 调用 `get_speech_text()` | 立即消费并返回语音文本 |
| 调用 `reset_speech_consumed()` | 清空语音状态，丢弃未消费语音 |

**推荐使用模式：**

```python
# 主循环中统一调用 get_user_state()
while True:
    state = fusion.get_user_state()
    
    if state['speech_has_new']:
        handle_speech(state['speech_text'])
    
    if state['has_face']:
        handle_emotion(state['face_emotion'])
```

---

## 六、注意事项

1. **依赖模块**：`FusionModule` 依赖 `VisionModule` 和 `AudioController`，需先初始化
2. **语音消费**：`get_speech_text()` 依赖 `get_user_state()` 先调用更新内部缓存
3. **线程安全**：方法均为非阻塞，可在主循环中安全调用
4. **预留字段**：`heart_rate` 为生理模块预留，当前始终为 `None`
5. **配置可选**：`config` 参数为可选，不传时使用默认行为

---

## 七、接口对照表

| 方法 | 用途 | 是否阻塞 | 是否消费语音 |
|------|------|----------|--------------|
| `get_user_state()` | 获取完整状态 | 否 | 取决于配置 |
| `has_face()` | 快速检查人脸 | 否 | 否 |
| `has_speech()` | 快速检查新语音 | 否 | 否 |
| `get_emotion()` | 快速获取情绪 | 否 | 否 |
| `get_speech_text()` | 获取并消费语音 | 否 | 是 |
| `reset_speech_consumed()` | 重置语音状态 | 否 | 否 |

---

**文档版本：** v1.0  
**更新日期：** 2026-04-21
```