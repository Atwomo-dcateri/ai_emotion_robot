# hardware/oled_driver.py
"""
真实的OLED显示屏驱动模块
支持SSD1306/SH1106 OLED显示屏，I2C接口
"""

import time
import threading
from PIL import Image, ImageDraw, ImageFont
import os
import sys

class OLEDDisplay:
    """
    OLED显示屏驱动类
    支持表情显示、文本显示、动画等功能
    """

    def __init__(self, width=128, height=64, i2c_address=0x3C, i2c_port=1, device_type='ssd1306'):
        """
        初始化OLED显示屏
        :param width: 屏幕宽度
        :param height: 屏幕高度
        :param i2c_address: I2C地址 (默认0x3C)
        :param i2c_port: I2C端口号
        :param device_type: OLED驱动类型 ('ssd1306' 或 'sh1106')
        """
        self.width = width
        self.height = height
        self.i2c_address = i2c_address
        self.i2c_port = i2c_port
        self.device_type = device_type.lower()

        # 初始化显示设备
        self.device = None
        self._init_device()

        # 表情映射 (像素艺术)
        self.emotion_pixels = self._create_emotion_pixels()

        # 字体
        self.font_small = None
        self.font_large = None
        self._init_fonts()

        # 显示状态
        self.current_emotion = None
        self.confidence = 0
        self.is_animating = False

        print(f"[OLED驱动] 初始化完成 {width}x{height} 显示屏 (I2C:0x{i2c_address:02X}, 类型:{self.device_type})")

    def _init_device(self):
        """初始化OLED设备"""
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306, sh1106

            # 创建I2C接口
            serial = i2c(port=self.i2c_port, address=self.i2c_address)

            # 根据设备类型创建显示设备
            if self.device_type in ('sh1106', 'ssd1106', 'ssd110', 'sh110'):
                self.device = sh1106(serial, width=self.width, height=self.height)
                device_name = 'SH1106'
            else:
                self.device = ssd1306(serial, width=self.width, height=self.height)
                device_name = 'SSD1306'

            # 清屏
            self.clear()

            print(f"[OLED驱动] {device_name}设备初始化成功")

        except ImportError as e:
            print(f"[OLED驱动] 错误：缺少依赖库 - {e}")
            print("[OLED驱动] 请安装: pip install luma.oled pillow")
            self.device = None
        except Exception as e:
            print(f"[OLED驱动] 设备初始化失败: {e}")
            print("[OLED驱动] 切换到模拟模式")
            self.device = None

    def _init_fonts(self):
        """初始化字体"""
        try:
            # 使用系统字体或内置字体
            self.font_small = ImageFont.load_default()
            # 尝试加载更大的字体
            try:
                self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            except:
                self.font_large = self.font_small
        except:
            self.font_small = None
            self.font_large = None

    def _create_emotion_pixels(self):
        """
        创建表情的像素艺术
        每个表情是一个16x16的像素矩阵
        """
        return {
            '平静': [
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
            ],
            '开心': [
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
            ],
            '悲伤': [
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
            ],
            '痛苦': [
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
            ],
            '惊讶': [
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
            ],
            '愤怒': [
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
            ],
            '恐惧': [
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,
                0,0,1,0,0,1,0,0,0,0,1,0,0,1,0,0,
                0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,
                0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
            ],
            '默认': [
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
            ]
        }

    def clear(self):
        """清空屏幕"""
        if self.device:
            self.device.clear()
        else:
            print("[OLED模拟] 清空屏幕")

    def show_emotion(self, emotion, confidence=75.0):
        """
        显示表情
        :param emotion: 表情名称
        :param confidence: 置信度
        """
        self.current_emotion = emotion
        self.confidence = confidence

        if self.device:
            # 创建图像
            image = Image.new('1', (self.width, self.height), 0)
            draw = ImageDraw.Draw(image)

            # 绘制表情像素艺术 (居中显示)
            emotion_data = self.emotion_pixels.get(emotion, self.emotion_pixels['默认'])
            pixel_size = 2  # 每个像素放大倍数

            start_x = (self.width - 16 * pixel_size) // 2
            start_y = (self.height - 16 * pixel_size) // 2

            for y in range(16):
                for x in range(16):
                    if emotion_data[y * 16 + x]:
                        draw.rectangle([
                            start_x + x * pixel_size,
                            start_y + y * pixel_size,
                            start_x + (x + 1) * pixel_size - 1,
                            start_y + (y + 1) * pixel_size - 1
                        ], fill=255)

            # 绘制置信度条形图
            bar_width = int((confidence / 100) * (self.width - 20))
            draw.rectangle([10, self.height - 8, 10 + bar_width, self.height - 4], fill=255)

            # 绘制表情名称
            if self.font_small:
                text = f"{emotion} {confidence:.0f}%"
                draw.text((10, 10), text, font=self.font_small, fill=255)

            # 显示图像
            self.device.display(image)

        else:
            # 模拟模式
            print(f"[OLED模拟] 显示表情: {emotion} ({confidence:.1f}%)")

    def show_text(self, text, x=0, y=0, font_size='small'):
        """
        显示文本
        :param text: 文本内容
        :param x: X坐标
        :param y: Y坐标
        :param font_size: 字体大小 ('small' 或 'large')
        """
        if self.device:
            image = Image.new('1', (self.width, self.height), 0)
            draw = ImageDraw.Draw(image)

            font = self.font_small if font_size == 'small' else self.font_large
            if font:
                draw.text((x, y), text, font=font, fill=255)

            self.device.display(image)
        else:
            print(f"[OLED模拟] 显示文本: {text}")

    def show_animation(self, emotion, frames=3, duration=0.3):
        """
        显示表情动画
        :param emotion: 表情类型
        :param frames: 动画帧数
        :param duration: 每帧持续时间
        """
        if self.is_animating:
            return

        self.is_animating = True

        try:
            # 简单的闪烁动画
            for i in range(frames):
                if i % 2 == 0:
                    self.show_emotion(emotion, self.confidence)
                else:
                    self.clear()
                time.sleep(duration)

            # 最终显示表情
            self.show_emotion(emotion, self.confidence)

        finally:
            self.is_animating = False

    def show_status(self, status_info):
        """
        显示状态信息
        :param status_info: 状态信息字典
        """
        if self.device:
            image = Image.new('1', (self.width, self.height), 0)
            draw = ImageDraw.Draw(image)

            y_offset = 5
            if self.font_small:
                for key, value in status_info.items():
                    text = f"{key}: {value}"
                    draw.text((5, y_offset), text, font=self.font_small, fill=255)
                    y_offset += 12
                    if y_offset > self.height - 15:
                        break

            self.device.display(image)
        else:
            print("[OLED模拟] 显示状态:")
            for key, value in status_info.items():
                print(f"  {key}: {value}")

    def close(self):
        """关闭显示屏"""
        if self.device:
            self.clear()
            # 释放资源
            pass
        print("[OLED驱动] 已关闭")


class RealOLEDHardware:
    """
    真实OLED硬件接口
    集成到现有的硬件模拟器架构中
    """

    def __init__(self, use_real_oled=True, i2c_address=0x3C, i2c_port=1, device_type='ssd1306'):
        """
        初始化真实OLED硬件
        :param use_real_oled: 是否使用真实OLED
        :param i2c_address: I2C地址
        :param i2c_port: I2C端口
        :param device_type: OLED驱动类型 ('ssd1306' 或 'sh1106')
        """
        self.use_real_oled = use_real_oled

        if use_real_oled:
            self.oled = OLEDDisplay(i2c_address=i2c_address, i2c_port=i2c_port, device_type=device_type)
        else:
            # 回退到模拟器
            from .oled_simulator import OLEDSimulator
            self.oled = OLEDSimulator(use_ascii=True)

        print(f"[真实OLED] 硬件初始化完成 (真实模式: {use_real_oled})")

    def show_face(self, emotion, confidence=None):
        """显示表情"""
        return self.oled.show_emotion(emotion, confidence or 75.0)

    def show_animation(self, emotion, frames=3, duration=0.3):
        """显示动画"""
        return self.oled.show_animation(emotion, frames, duration)

    def show_text(self, text, x=0, y=0):
        """显示文本"""
        return self.oled.show_text(text, x, y)

    def clear(self):
        """清空屏幕"""
        return self.oled.clear()

    def show_status_display(self, status_info):
        """显示状态"""
        return self.oled.show_status(status_info)

    def close(self):
        """关闭硬件"""
        if hasattr(self.oled, 'close'):
            self.oled.close()