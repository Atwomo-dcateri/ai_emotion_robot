"""
模块名称：oled_display.py
功能描述：真实 OLED 显示屏驱动（SSD1306/SH1106，I2C 接口）
依赖：luma.oled, pillow
"""

import logging
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

from hardware.base import DisplayInterface

logger = logging.getLogger(__name__)


class OLEDDisplay(DisplayInterface):
    """
    OLED 显示屏驱动类
    支持 SSD1306/SH1106 驱动，I2C 接口
    """

    # 类常量
    DEFAULT_WIDTH = 128
    DEFAULT_HEIGHT = 64
    DEFAULT_I2C_ADDRESS = 0x3C
    DEFAULT_I2C_PORT = 1
    DEFAULT_DEVICE_TYPE = 'ssd1106'

    # 表情像素放大倍数
    EMOTION_PIXEL_SIZE = 2
    EMOTION_SIZE = 16  # 16x16 像素

    # 置信度条形图位置
    BAR_X = 10
    BAR_Y_OFFSET = 8  # 距离底部的偏移
    BAR_HEIGHT = 4

    def __init__(self, config=None):
        """
        初始化 OLED 显示屏

        Args:
            config: Config 类实例，包含以下配置项：
                - OLED_ENABLED: 是否启用
                - OLED_I2C_ADDRESS: I2C 地址
                - OLED_I2C_PORT: I2C 端口
                - OLED_DEVICE_TYPE: 驱动类型 (ssd1306/sh1106)
                - OLED_WIDTH: 屏幕宽度
                - OLED_HEIGHT: 屏幕高度
        """
        self.config = config

        # 读取配置
        self.width = getattr(config, 'OLED_WIDTH', self.DEFAULT_WIDTH) if config else self.DEFAULT_WIDTH
        self.height = getattr(config, 'OLED_HEIGHT', self.DEFAULT_HEIGHT) if config else self.DEFAULT_HEIGHT
        self.i2c_address = getattr(config, 'OLED_I2C_ADDRESS', self.DEFAULT_I2C_ADDRESS) if config else self.DEFAULT_I2C_ADDRESS
        self.i2c_port = getattr(config, 'OLED_I2C_PORT', self.DEFAULT_I2C_PORT) if config else self.DEFAULT_I2C_PORT
        self.device_type = getattr(config, 'OLED_DEVICE_TYPE', self.DEFAULT_DEVICE_TYPE) if config else self.DEFAULT_DEVICE_TYPE

        # 显示设备
        self._device = None
        self._fonts = {'small': None, 'large': None}

        # 状态
        self.current_emotion = None
        self.confidence = 0

        # 初始化
        self._init_device()
        self._init_fonts()

        logger.info(f"OLED 驱动初始化完成 {self.width}x{self.height} (I2C:0x{self.i2c_address:02X}, 类型:{self.device_type})")

    def _init_device(self):
        """初始化 OLED 设备"""
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306, sh1106

            serial = i2c(port=self.i2c_port, address=self.i2c_address)

            if self.device_type in ('sh1106', 'ssd1106', 'ssd110', 'sh110'):
                self._device = sh1106(serial, width=self.width, height=self.height)
                device_name = 'SH1106'
            else:
                self._device = ssd1306(serial, width=self.width, height=self.height)
                device_name = 'SSD1306'

            self.clear()
            logger.info(f"{device_name} 设备初始化成功")

        except ImportError as e:
            logger.error(f"缺少依赖库: {e}")
            logger.error("请安装: pip install luma.oled pillow")
            raise
        except Exception as e:
            logger.error(f"设备初始化失败: {e}")
            raise

    def _init_fonts(self):
        """初始化字体"""
        try:
            self._fonts['small'] = ImageFont.load_default()

            # 尝试加载更大字体
            font_paths = [
                # 文泉驿字体
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                # Noto 字体
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                # DejaVu（不支持中文，作为备选）
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
            for path in font_paths:
                try:
                    self._fonts['large'] = ImageFont.truetype(path, 16)
                    break
                except:
                    continue

            if not self._fonts['large']:
                self._fonts['large'] = self._fonts['small']

        except Exception as e:
            logger.warning(f"字体初始化失败: {e}")
            self._fonts['small'] = None
            self._fonts['large'] = None

    def _create_emotion_pixels(self) -> Dict[str, List[int]]:
        """
        创建表情的像素艺术（16x16 像素矩阵）

        Returns:
            表情名称 -> 像素数据列表的映射
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
            ]
        }

    def _draw_emotion_pixel_art(self, draw: ImageDraw, emotion: str) -> None:
        """
        绘制表情像素艺术

        Args:
            draw: PIL ImageDraw 对象
            emotion: 表情名称
        """
        emotion_pixels = self._create_emotion_pixels()
        pixels = emotion_pixels.get(emotion, emotion_pixels.get('平静', []))

        if not pixels:
            return

        start_x = (self.width - self.EMOTION_SIZE * self.EMOTION_PIXEL_SIZE) // 2
        start_y = (self.height - self.EMOTION_SIZE * self.EMOTION_PIXEL_SIZE) // 2

        for y in range(self.EMOTION_SIZE):
            for x in range(self.EMOTION_SIZE):
                if pixels[y * self.EMOTION_SIZE + x]:
                    draw.rectangle([
                        start_x + x * self.EMOTION_PIXEL_SIZE,
                        start_y + y * self.EMOTION_PIXEL_SIZE,
                        start_x + (x + 1) * self.EMOTION_PIXEL_SIZE - 1,
                        start_y + (y + 1) * self.EMOTION_PIXEL_SIZE - 1
                    ], fill=255)

    def _draw_confidence_bar(self, draw: ImageDraw, confidence: float) -> None:
        """
        绘制置信度条形图

        Args:
            draw: PIL ImageDraw 对象
            confidence: 置信度 0-100
        """
        bar_width = int((confidence / 100) * (self.width - self.BAR_X * 2))
        bar_y = self.height - self.BAR_Y_OFFSET
        draw.rectangle(
            [self.BAR_X, bar_y, self.BAR_X + bar_width, bar_y + self.BAR_HEIGHT],
            fill=255
        )

    def show_emotion(self, emotion: str, confidence: float = 75.0) -> None:
        """
        显示表情

        Args:
            emotion: 表情名称（中文），如：平静/开心/悲伤/愤怒/恐惧/惊讶
            confidence: 置信度 0-100
        """
        self.current_emotion = emotion
        self.confidence = confidence

        # 创建图像
        image = Image.new('1', (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)

        # 绘制表情像素艺术
        self._draw_emotion_pixel_art(draw, emotion)

        # 绘制置信度条形图
        self._draw_confidence_bar(draw, confidence)

        # 绘制表情名称和置信度
        if self._fonts['small']:
            text = f"{emotion} {confidence:.0f}%"
            draw.text((self.BAR_X, self.BAR_X), text, font=self._fonts['small'], fill=255)

        # 显示
        if self._device:
            self._device.display(image)

        logger.debug(f"显示表情: {emotion} ({confidence:.1f}%)")

    def show_text(self, text: str, x: int = 0, y: int = 0) -> None:
        """
        显示文本

        Args:
            text: 文本内容
            x: X 坐标
            y: Y 坐标
        """
        if not self._device:
            raise RuntimeError("OLED 设备未初始化")

        image = Image.new('1', (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)

        font = self._fonts['large'] if self._fonts['large'] else self._fonts['small']
        if font:
            draw.text((x, y), text, font=font, fill=255)

        self._device.display(image)
        logger.debug(f"显示文本: {text}")

    def clear(self) -> None:
        """清空屏幕"""
        if self._device:
            self._device.clear()
            logger.debug("屏幕已清空")

    def close(self) -> None:
        """关闭显示设备"""
        if self._device:
            self.clear()
            self._device = None
            logger.info("OLED 设备已关闭")