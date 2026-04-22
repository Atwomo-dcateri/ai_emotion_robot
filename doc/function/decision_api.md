## Decision模块 API 说明文档

```markdown
# Decision 模块 API 说明

## 模块概述

决策模块，根据用户状态（来自 Fusion 模块）生成机器人的动作指令。支持两种决策引擎：

- **LLM 引擎**：调用云端大语言模型（DeepSeek API）生成自然语言反应
- **规则引擎**：基于预定义规则的离线响应（降级方案）

**决策控制器**自动优先使用 LLM，失败时降级到规则引擎。

---

## 一、核心类：DecisionController

决策控制器，对外提供统一的决策接口，自动管理 LLM/规则引擎切换。

### 初始化

```python
from decision import DecisionController
from config import Config

decision = DecisionController(Config)
```

### 主要方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `decide(user_state)` | 根据用户状态生成动作指令列表 | `List[Dict[str, Any]]` |
| `is_ready()` | 返回决策引擎是否就绪 | `bool` |

---

## 二、动作指令格式

`decide()` 返回的动作指令列表，每条指令包含 `type` 字段和对应参数。

### 动作类型枚举

| 类型 | 说明 | 参数字段 |
|------|------|----------|
| `oled` | OLED 显示表情 | `emotion`, `confidence` |
| `oled_text` | OLED 显示文本 | `text`, `x`, `y` |
| `speak` | 语音播放 | `text` |
| `servo` | 舵机动作 | `move`, `times` |
| `wait` | 等待 | `duration` |
| `none` | 空动作 | 无 |

### 动作指令示例

```python
# OLED 显示表情
{'type': 'oled', 'emotion': '开心', 'confidence': 85.0}

# OLED 显示文本
{'type': 'oled_text', 'text': '你好', 'x': 10, 'y': 20}

# 语音播放
{'type': 'speak', 'text': '你好呀，很高兴见到你'}

# 舵机动作
{'type': 'servo', 'move': 'nod', 'times': 1}

# 等待
{'type': 'wait', 'duration': 0.5}

# 空动作
{'type': 'none'}
```

### 舵机动作枚举

| 动作 | 说明 |
|------|------|
| `nod` | 点头 |
| `shake` | 摇头 |
| `none` | 无动作 |

---

## 三、决策控制器方法详解

### 1. `decide(user_state)` - 生成动作指令

```python
actions = decision.decide(user_state)

for action in actions:
    if action['type'] == 'oled':
        oled.show_emotion(action['emotion'], action['confidence'])
    elif action['type'] == 'speak':
        audio.respond(action['text'])
    elif action['type'] == 'servo':
        servo.execute(action['move'], action.get('times', 1))
    elif action['type'] == 'wait':
        time.sleep(action['duration'])
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `user_state` | Dict | Fusion.get_user_state() 返回的状态字典 |

**返回值：** 动作指令列表，可能为空列表

**行为：**
- 优先使用 LLM 引擎
- LLM 失败/超时/未配置时自动降级到规则引擎
- 始终返回有效动作列表（可能包含 `none` 动作）

### 2. `is_ready()` - 检查引擎就绪状态

```python
if decision.is_ready():
    actions = decision.decide(user_state)
```

**返回值：** 始终返回 `True`（规则引擎保证可用）

---

## 四、辅助函数（创建动作指令）

提供工厂函数，用于手动创建标准格式的动作指令。

```python
from decision import (
    create_oled_action,
    create_oled_text_action,
    create_speak_action,
    create_servo_action,
    create_wait_action,
    create_none_action
)
```

### 函数列表

| 函数 | 参数 | 返回值示例 |
|------|------|-------------|
| `create_oled_action(emotion, confidence=75.0)` | emotion: 表情名称（中文）<br>confidence: 置信度 | `{'type': 'oled', 'emotion': '开心', 'confidence': 85.0}` |
| `create_oled_text_action(text, x=0, y=0)` | text: 文本内容<br>x: X坐标<br>y: Y坐标 | `{'type': 'oled_text', 'text': '你好', 'x': 10, 'y': 20}` |
| `create_speak_action(text)` | text: 播报文本 | `{'type': 'speak', 'text': '你好'}` |
| `create_servo_action(move, times=1)` | move: nod/shake<br>times: 重复次数 | `{'type': 'servo', 'move': 'nod', 'times': 1}` |
| `create_wait_action(duration)` | duration: 等待秒数 | `{'type': 'wait', 'duration': 0.5}` |
| `create_none_action()` | 无 | `{'type': 'none'}` |

---

## 五、配置项说明

`config.py` 中 Decision 相关配置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DECISION_USE_LLM` | bool | True | 是否启用 LLM 引擎 |
| `DECISION_LLM_API_KEY` | str | 环境变量 | DeepSeek API 密钥 |
| `DECISION_LLM_API_URL` | str | DeepSeek URL | API 地址 |
| `DECISION_LLM_MODEL` | str | deepseek-chat | 模型名称 |
| `DECISION_LLM_TIMEOUT` | int | 15 | 请求超时（秒） |
| `DECISION_FALLBACK_RULES` | dict | None | 自定义规则（覆盖默认） |

**环境变量设置：**
```bash
export DEEPSEEK_API_KEY="your-api-key"
```

---

## 六、完整使用示例

### 示例 1：基础使用

```python
from config import Config
from fusion import FusionModule
from decision import DecisionController
from vision import VisionModule
from audio import AudioController
from hardware.oled_display import OLEDDisplay

# 初始化各模块
config = Config()
vision = VisionModule(config)
audio = AudioController(config)
fusion = FusionModule(vision, audio, config)
decision = DecisionController(config)
oled = OLEDDisplay(config)

# 启动服务
vision.start()
audio.start()

# 主循环
try:
    while True:
        # 获取用户状态
        state = fusion.get_user_state()
        
        # 只在有变化时决策
        if state['has_face'] or state['speech_has_new']:
            actions = decision.decide(state)
            
            for action in actions:
                if action['type'] == 'oled':
                    oled.show_emotion(action['emotion'], action['confidence'])
                elif action['type'] == 'speak':
                    audio.respond(action['text'])
                elif action['type'] == 'wait':
                    time.sleep(action['duration'])
        
        time.sleep(0.1)

except KeyboardInterrupt:
    pass
finally:
    vision.stop()
    audio.stop()
```

### 示例 2：仅使用规则引擎（离线模式）

```python
# 配置中禁用 LLM
config.DECISION_USE_LLM = False

decision = DecisionController(config)
# 始终使用规则引擎，完全离线可用
```

### 示例 3：手动构建动作指令

```python
from decision import (
    create_oled_action,
    create_speak_action,
    create_servo_action
)

# 构建复合动作
actions = [
    create_oled_action('开心', 95.0),
    create_speak_action('今天天气真好'),
    create_servo_action('nod', 2)
]

# 执行动作
for action in actions:
    if action['type'] == 'oled':
        oled.show_emotion(action['emotion'], action['confidence'])
    elif action['type'] == 'speak':
        audio.respond(action['text'])
    elif action['type'] == 'servo':
        servo.execute(action['move'], action['times'])
```

### 示例 4：自定义规则扩展

```python
# 在 config.py 中添加自定义规则
DECISION_FALLBACK_RULES = {
    '疲惫': {
        'oled': '平静',
        'speech': ['辛苦了，休息一下吧', '需要我为你做点什么吗'],
        'action': None
    },
    '期待': {
        'oled': '开心',
        'speech': ['有什么好消息吗', '真让人期待'],
        'action': 'nod'
    }
}
```

---

## 七、LLM 响应格式

LLM 引擎要求返回严格的 JSON 格式：

```json
{
    "oled_emotion": "开心",
    "speech": "你看起来心情不错",
    "action": "nod"
}
```

| 字段 | 类型 | 说明 | 可选值 |
|------|------|------|--------|
| `oled_emotion` | str | 机器人显示的表情 | 开心/悲伤/愤怒/恐惧/惊讶/平静 |
| `speech` | str | 机器人说的话 | 中文，1-2句 |
| `action` | str | 舵机动作 | nod/shake/none |

---

## 八、规则引擎响应规则

### 情绪响应表

| 用户情绪 | 显示表情 | 回复语示例 | 舵机动作 |
|----------|----------|------------|----------|
| 开心 | 开心 | "你看起来心情不错"、"什么事这么开心" | 点头 |
| 悲伤 | 悲伤 | "别难过，我在这里陪着你" | 无 |
| 愤怒 | 平静 | "深呼吸，冷静一下" | 无 |
| 恐惧 | 惊讶 | "别害怕，我在这里" | 无 |
| 惊讶 | 惊讶 | "哇，真的吗" | 无 |
| 平静 | 平静 | "我在听"、"有什么想聊的吗" | 无 |

### 关键词响应表

| 关键词 | 回复语 |
|--------|--------|
| 你好 | "你好呀，很高兴见到你" |
| 嗨 | "嗨，今天心情怎么样" |
| 哈喽 | "哈喽，有什么可以帮你的吗" |
| 谢谢 | "不客气，很高兴能帮到你" |
| 拜拜/再见 | "再见，下次再聊" |

---

## 九、注意事项

1. **LLM 依赖网络**：需要互联网连接和有效的 API Key
2. **降级机制**：LLM 失败时自动降级到规则引擎，不影响机器人运行
3. **响应速度**：规则引擎 < 10ms，LLM 引擎 1-3 秒（含网络延迟）
4. **动作顺序**：返回的动作指令列表按顺序执行
5. **空动作**：`none` 类型可用于占位或跳过

---

## 十、接口对照表

| 组件 | 主要方法 | 说明 |
|------|----------|------|
| `DecisionController` | `decide()` | 统一决策入口，自动降级 |
| `RuleEngine` | `decide()` | 离线规则响应 |
| `LLMEngine` | `decide()` | 云端 LLM 响应 |
| 辅助函数 | `create_xxx_action()` | 创建标准动作指令 |

---

**文档版本：** v1.0  
**更新日期：** 2026-04-21
```