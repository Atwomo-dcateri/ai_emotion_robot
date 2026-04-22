## OLED模块 API 说明文档

```markdown
# OLED 模块 API 说明

## 模块概述

OLED 显示屏驱动模块，支持 SSD1306/SH1106 驱动芯片，I2C 接口。提供表情显示、文本显示、置信度条形图等功能。

**依赖安装（树莓派）：**
```bash
pip install luma.oled pillow
```

**硬件连接：**
| OLED 引脚 | 树莓派引脚 |
|-----------|------------|
| VCC | 3.3V (Pin 1) |
| GND | GND (Pin 6) |
| SCL | SCL (Pin 5, GPIO 3) |
| SDA | SDA (Pin 3, GPIO 2) |

---

## 一、核心类：OLEDDisplay

真实 OLED 显示屏驱动，继承自 `DisplayInterface`。

### 初始化

```python
from hardware.oled_display import OLEDDisplay
from config import Config

# 使用配置文件
oled = OLEDDisplay(Config)

# 或使用默认参数
oled = OLEDDisplay()  # 使用类默认常量
```

**配置项（config.py）：**

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `OLED_ENABLED` | bool | True | 是否启用 |
| `OLED_I2C_ADDRESS` | int | 0x3C | I2C 地址 |
| `OLED_I2C_PORT` | int | 1 | I2C 端口 |
| `OLED_DEVICE_TYPE` | str | 'ssd1306' | 驱动类型（ssd1306/sh1106） |
| `OLED_WIDTH` | int | 128 | 屏幕宽度 |
| `OLED_HEIGHT` | int | 64 | 屏幕高度 |

### 主要方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `show_emotion(emotion, confidence=75.0)` | 显示表情和置信度 | `None` |
| `show_text(text, x=0, y=0)` | 显示文本 | `None` |
| `clear()` | 清空屏幕 | `None` |
| `close()` | 关闭显示设备 | `None` |

---

## 二、显示方法详解

### 1. 显示表情 `show_emotion()`

```python
oled.show_emotion(emotion: str, confidence: float = 75.0) -> None
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `emotion` | str | 表情名称（中文），支持：平静、开心、悲伤、愤怒、恐惧、惊讶 |
| `confidence` | float | 置信度 0-100，默认 75.0 |

**显示内容：**
- 16x16 像素表情艺术（居中显示）
- 置信度条形图（屏幕底部）
- 表情名称和置信度百分比（左上角）

**示例：**
```python
# 显示开心表情，置信度 85%
oled.show_emotion('开心', confidence=85.0)

# 显示平静表情，使用默认置信度
oled.show_emotion('平静')
```

### 2. 显示文本 `show_text()`

```python
oled.show_text(text: str, x: int = 0, y: int = 0) -> None
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `text` | str | 要显示的文本 |
| `x` | int | X 坐标（像素），默认 0 |
| `y` | int | Y 坐标（像素），默认 0 |

**示例：**
```python
# 在左上角显示文本
oled.show_text('你好，机器人')

# 在指定位置显示
oled.show_text('状态: 运行中', x=10, y=20)
```

### 3. 清空屏幕 `clear()`

```python
oled.clear() -> None
```

**示例：**
```python
oled.clear()  # 清空屏幕内容
```

### 4. 关闭设备 `close()`

```python
oled.close() -> None
```

**示例：**
```python
oled.close()  # 清空屏幕并释放设备资源
```

---

## 三、兼容层：OLEDDisplayCompat（旧接口兼容）

保留原 `oled_driver.py` 文件名，提供与旧代码相同的接口。

```python
from hardware.oled_driver import OLEDDisplay

# 旧接口初始化（支持位置参数）
oled = OLEDDisplay(
    width=128,
    height=64,
    i2c_address=0x3C,
    i2c_port=1,
    device_type='ssd1306'
)
```

### 扩展方法

| 方法 | 说明 |
|------|------|
| `show_animation(emotion, frames=3, duration=0.3)` | 显示表情闪烁动画 |
| `show_status(status_info)` | 显示状态信息字典 |

**示例：**
```python
# 显示动画
oled.show_animation('开心', frames=3, duration=0.2)

# 显示状态信息
status = {'表情': '开心', '置信度': '85%', '人脸数': 1}
oled.show_status(status)
```

---

## 四、完整使用示例

### 示例 1：基础用法

```python
from config import Config
from hardware.oled_display import OLEDDisplay

# 初始化
oled = OLEDDisplay(Config)

# 显示表情
oled.show_emotion('开心', confidence=92.0)

# 等待 2 秒
import time
time.sleep(2)

# 显示文本
oled.clear()
oled.show_text('你好，AI机器人', x=20, y=25)

time.sleep(2)

# 关闭
oled.close()
```

### 示例 2：与视觉模块集成

```python
from config import Config
from vision import VisionModule
from hardware.oled_display import OLEDDisplay

# 初始化模块
vision = VisionModule(Config)
oled = OLEDDisplay(Config)

# 启动视觉服务
vision.start()

try:
    while True:
        result = vision.get_emotion()
        if result:
            # 在 OLED 上显示识别到的表情
            oled.show_emotion(
                emotion=result['emotion_cn'],
                confidence=result['confidence']
            )
        time.sleep(0.3)
finally:
    vision.stop()
    oled.close()
```

### 示例 3：使用兼容层

```python
from hardware.oled_driver import OLEDDisplay

# 旧接口初始化
oled = OLEDDisplay(width=128, height=64)

# 显示动画
oled.show_animation('开心', frames=5, duration=0.1)

# 显示状态
oled.show_status({
    'System': 'Running',
    'Emotion': 'Happy',
    'Face': 'Detected'
})

# 关闭
oled.close()
```

---

## 五、支持的表情列表

| 表情名称 | 说明 | 像素艺术特征 |
|----------|------|--------------|
| `'平静'` | 默认表情 | 正常眼睛和嘴巴 |
| `'开心'` | 高兴 | 嘴角上扬的嘴巴 |
| `'悲伤'` | 难过 | 下垂的嘴巴 |
| `'愤怒'` | 生气 | 紧皱的眉毛 |
| `'恐惧'` | 害怕 | 睁大的眼睛 |
| `'惊讶'` | 吃惊 | 圆形的嘴巴 |

---

## 六、注意事项

1. **I2C 接口**：使用前需启用树莓派 I2C 接口
   ```bash
   sudo raspi-config → Interface Options → I2C → Enable
   ```

2. **设备地址检测**：可用 `i2cdetect -y 1` 确认 OLED 地址（通常为 0x3C 或 0x3D）

3. **字体**：默认使用 PIL 内置字体，如需中文字体需安装中文字体包

4. **资源释放**：程序退出前调用 `close()` 方法清屏并释放资源

5. **错误处理**：设备初始化失败会抛出异常，调用方需处理

---

## 七、常见问题

**Q: 屏幕无显示？**
- 检查 I2C 连接是否正确
- 运行 `i2cdetect -y 1` 确认设备地址
- 检查 `config.py` 中的 `OLED_I2C_ADDRESS` 配置

**Q: 中文显示乱码？**
- PIL 默认字体不支持中文，需安装中文字体：
  ```bash
  sudo apt-get install fonts-wqy-microhei
  ```
- 或使用 `show_emotion()` 方法显示预设表情

**Q: 屏幕闪烁？**
- 降低刷新频率，避免连续调用 `show_emotion()`
- 使用 `analysis_interval` 控制检测频率

---

**文档版本：** v1.0  
**更新日期：** 2026-04-21
```