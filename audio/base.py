"""
模块名称：base.py
功能描述：语音模块抽象接口定义
依赖：无
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Callable


class SpeechRecognitionInterface(ABC):
    """语音识别抽象接口"""

    @abstractmethod
    def start(self) -> bool:
        """启动识别服务，返回成功与否"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止识别服务"""
        pass

    @abstractmethod
    def get_text(self) -> Optional[str]:
        """非阻塞获取最新识别文本，无新内容返回 None"""
        pass

    @abstractmethod
    def is_listening(self) -> bool:
        """返回当前是否正在监听"""
        pass

    @abstractmethod
    def set_wake_words(self, words: List[str]) -> None:
        """设置唤醒词列表"""
        pass


class SpeechSynthesisInterface(ABC):
    """语音合成抽象接口"""

    @abstractmethod
    def speak(self, text: str) -> bool:
        """同步播放语音，返回是否成功"""
        pass

    @abstractmethod
    def speak_async(self, text: str) -> Optional[str]:
        """异步播放，返回任务 ID"""
        pass

    @abstractmethod
    def is_speaking(self) -> bool:
        """返回是否正在播放"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止当前播放"""
        pass

    @abstractmethod
    def set_voice(self, voice_id: str) -> None:
        """切换音色"""
        pass