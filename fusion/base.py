"""
模块名称：base.py
功能描述：融合模块抽象接口定义
依赖：无
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class FusionInterface(ABC):
    """融合模块抽象接口"""

    @abstractmethod
    def get_user_state(self) -> Dict[str, Any]:
        """
        获取当前用户状态快照

        Returns:
            {
                'timestamp': float,           # Unix 时间戳
                'has_face': bool,             # 是否检测到人脸
                'has_speech': bool,           # 是否有新语音输入
                'face_emotion': dict | None,  # 情绪结果
                'speech_text': str | None,    # 语音识别文本
                'speech_has_new': bool,       # 是否有未消费的新输入
                'heart_rate': None,           # 预留
                'fusion_ready': bool          # 融合数据是否有效
            }
        """
        pass

    @abstractmethod
    def has_face(self) -> bool:
        """是否检测到人脸"""
        pass

    @abstractmethod
    def has_speech(self) -> bool:
        """是否有新的语音输入（未消费）"""
        pass

    @abstractmethod
    def get_emotion(self) -> Optional[Dict[str, Any]]:
        """快捷获取情绪结果"""
        pass

    @abstractmethod
    def get_speech_text(self) -> Optional[str]:
        """快捷获取语音文本（自动消费）"""
        pass

    @abstractmethod
    def reset_speech_consumed(self) -> None:
        """重置语音消费标记"""
        pass