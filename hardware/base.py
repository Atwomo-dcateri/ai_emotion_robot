"""
模块名称：base.py
功能描述：硬件模块抽象接口定义
依赖：无
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class DisplayInterface(ABC):
    """显示设备抽象接口"""

    @abstractmethod
    def show_emotion(self, emotion: str, confidence: float = 75.0) -> None:
        """
        显示表情

        Args:
            emotion: 表情名称（中文），如：平静/开心/悲伤/愤怒/恐惧/惊讶
            confidence: 置信度 0-100
        """
        pass

    @abstractmethod
    def show_text(self, text: str, x: int = 0, y: int = 0) -> None:
        """显示文本"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空屏幕"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭显示设备"""
        pass


class ServoInterface(ABC):
    """舵机控制抽象接口（预留）"""

    @abstractmethod
    def set_angle(self, angle: int) -> None:
        """设置舵机角度"""
        pass

    @abstractmethod
    def close(self) -> None:
        """释放舵机资源"""
        pass