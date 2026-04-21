"""
模块名称：base.py
功能描述：决策模块抽象接口定义
依赖：无
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum


class ActionType(str, Enum):
    """动作类型枚举"""
    OLED = "oled"
    OLED_TEXT = "oled_text"
    SPEAK = "speak"
    SERVO = "servo"
    WAIT = "wait"
    NONE = "none"


class ServoMove(str, Enum):
    """舵机动作枚举"""
    NOD = "nod"      # 点头
    SHAKE = "shake"  # 摇头
    NONE = "none"


class DecisionInterface(ABC):
    """决策模块抽象接口"""

    @abstractmethod
    def decide(self, user_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据用户状态生成动作指令列表

        Args:
            user_state: Fusion.get_user_state() 返回的状态字典

        Returns:
            动作指令列表，每个指令包含 type 和对应参数

        动作指令格式：
            - {'type': 'oled', 'emotion': str, 'confidence': float}
            - {'type': 'oled_text', 'text': str, 'x': int, 'y': int}
            - {'type': 'speak', 'text': str}
            - {'type': 'servo', 'move': str, 'times': int}
            - {'type': 'wait', 'duration': float}
            - {'type': 'none'}
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """返回决策引擎是否就绪"""
        pass


def create_oled_action(emotion: str, confidence: float = 75.0) -> Dict[str, Any]:
    """创建 OLED 显示表情动作"""
    return {'type': ActionType.OLED, 'emotion': emotion, 'confidence': confidence}


def create_oled_text_action(text: str, x: int = 0, y: int = 0) -> Dict[str, Any]:
    """创建 OLED 显示文本动作"""
    return {'type': ActionType.OLED_TEXT, 'text': text, 'x': x, 'y': y}


def create_speak_action(text: str) -> Dict[str, Any]:
    """创建语音播放动作"""
    return {'type': ActionType.SPEAK, 'text': text}


def create_servo_action(move: str, times: int = 1) -> Dict[str, Any]:
    """创建舵机动作"""
    return {'type': ActionType.SERVO, 'move': move, 'times': times}


def create_wait_action(duration: float) -> Dict[str, Any]:
    """创建等待动作"""
    return {'type': ActionType.WAIT, 'duration': duration}


def create_none_action() -> Dict[str, Any]:
    """创建空动作"""
    return {'type': ActionType.NONE}