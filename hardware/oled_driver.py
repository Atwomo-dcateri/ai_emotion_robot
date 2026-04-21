"""
模块名称：oled_driver.py
功能描述：OLED 驱动兼容层，提供与旧代码相同的接口
依赖：hardware.oled_display, PIL
"""

import time
import logging
from typing import Dict, Any

from PIL import Image, ImageDraw

from hardware.oled_display import OLEDDisplay as _OLEDDisplay

logger = logging.getLogger(__name__)


class OLEDDisplay(_OLEDDisplay):
    """
    OLED 显示屏驱动类（兼容层）
    保持与旧代码的接口兼容性
    """

    def __init__(self, width=128, height=64, i2c_address=0x3C, i2c_port=1, device_type='ssd1306'):
        """
        兼容旧接口的初始化方法

        Args:
            width: 屏幕宽度
            height: 屏幕高度
            i2c_address: I2C 地址
            i2c_port: I2C 端口
            device_type: OLED 驱动类型
        """
        # 创建模拟配置对象
        class _MockConfig:
            pass

        config = _MockConfig()
        config.OLED_WIDTH = width
        config.OLED_HEIGHT = height
        config.OLED_I2C_ADDRESS = i2c_address
        config.OLED_I2C_PORT = i2c_port
        config.OLED_DEVICE_TYPE = device_type

        super().__init__(config)

    def show_emotion(self, emotion, confidence=75.0):
        """显示表情（兼容旧接口）"""
        return super().show_emotion(emotion, confidence)

    def show_text(self, text, x=0, y=0, font_size='small'):
        """
        显示文本（兼容旧接口）

        Args:
            font_size: 字体大小（忽略，自动选择最佳字体）
        """
        return super().show_text(text, x, y)

    def show_animation(self, emotion, frames=3, duration=0.3):
        """
        显示表情动画

        Args:
            emotion: 表情类型
            frames: 动画帧数
            duration: 每帧持续时间
        """
        # 安全获取置信度
        conf = getattr(self, 'confidence', 75.0)

        for i in range(frames):
            if i % 2 == 0:
                self.show_emotion(emotion, conf)
            else:
                self.clear()
            time.sleep(duration)

        self.show_emotion(emotion, conf)

    def show_status(self, status_info: Dict[str, Any]):
        """
        显示状态信息

        Args:
            status_info: 状态信息字典
        """
        if not self._device:
            raise RuntimeError("OLED 设备未初始化")

        image = Image.new('1', (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)

        y_offset = 5
        font = self._fonts.get('small')
        if font:
            for key, value in status_info.items():
                text = f"{key}: {value}"
                draw.text((5, y_offset), text, font=font, fill=255)
                y_offset += 12
                if y_offset > self.height - 15:
                    break

        self._device.display(image)
