"""
模块名称：base.py
功能描述：视觉模块抽象接口定义
依赖：无
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class VisionInterface(ABC):
    """视觉模块抽象接口"""

    @abstractmethod
    def start(self) -> bool:
        """启动视觉服务"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止视觉服务"""
        pass

    @abstractmethod
    def get_emotion(self) -> Optional[Dict[str, Any]]:
        """
        非阻塞获取情绪检测结果

        Returns:
            {
                'emotion': str,      # 英文标签: happy/sad/angry/fear/surprise/neutral
                'emotion_cn': str,   # 中文标签: 开心/悲伤/愤怒/恐惧/惊讶/平静
                'confidence': float, # 置信度 0-100
                'face_count': int,   # 检测到的人脸数量
                'region': tuple      # (x, y, w, h) 人脸区域
            }
            未检测到人脸返回 None
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """返回服务是否正在运行"""
        pass

    def close(self) -> None:
        """关闭服务（stop 的别名）"""
        self.stop()