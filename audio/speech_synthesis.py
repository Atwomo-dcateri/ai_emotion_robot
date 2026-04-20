"""
模块名称：speech_synthesis.py
功能描述：语音合成实现（pyttsx3 + 模拟降级）
依赖：pyttsx3 / gtts
"""

import logging
import threading
from typing import Optional

from audio.base import SpeechSynthesisInterface

logger = logging.getLogger(__name__)


class Pyttsx3Synthesis(SpeechSynthesisInterface):
    """pyttsx3 离线语音合成"""

    def __init__(self, rate: int = 180, volume: float = 1.0):
        self.rate = rate
        self.volume = volume
        self._engine = None
        self._speaking = False
        self._lock = threading.Lock()

    def _init_engine(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', self.rate)
            self._engine.setProperty('volume', self.volume)
            logger.info("pyttsx3 初始化成功")
            return True
        except Exception as e:
            logger.error(f"pyttsx3 初始化失败: {e}")
            return False

    def speak(self, text: str) -> bool:
        with self._lock:
            if self._engine is None and not self._init_engine():
                return False
            try:
                self._speaking = True
                self._engine.say(text)
                self._engine.runAndWait()
                self._speaking = False
                logger.info(f"TTS 播放: {text[:50]}...")
                return True
            except Exception as e:
                logger.error(f"TTS 播放失败: {e}")
                self._speaking = False
                return False

    def speak_async(self, text: str) -> Optional[str]:
        """异步播放（pyttsx3 不支持原生异步，使用线程模拟）"""
        import uuid
        task_id = str(uuid.uuid4())[:8]

        def _play():
            self.speak(text)

        thread = threading.Thread(target=_play, daemon=True)
        thread.start()
        logger.debug(f"异步 TTS 任务启动: {task_id}")
        return task_id

    def is_speaking(self) -> bool:
        return self._speaking

    def stop(self) -> None:
        if self._engine:
            try:
                self._engine.stop()
            except:
                pass
        self._speaking = False
        logger.info("TTS 播放已停止")

    def set_voice(self, voice_id: str) -> None:
        if self._engine:
            try:
                voices = self._engine.getProperty('voices')
                for voice in voices:
                    if voice_id in voice.id or voice_id in voice.name:
                        self._engine.setProperty('voice', voice.id)
                        logger.info(f"切换音色: {voice.name}")
                        return
                logger.warning(f"未找到音色: {voice_id}")
            except Exception as e:
                logger.error(f"切换音色失败: {e}")


class GttsSynthesis(SpeechSynthesisInterface):
    """gTTS 在线语音合成（需网络）"""

    def __init__(self, lang: str = 'zh'):
        self.lang = lang
        self._speaking = False
        self._current_process = None

    def speak(self, text: str) -> bool:
        try:
            from gtts import gTTS
            import playsound
            import tempfile
            import os

            self._speaking = True
            tts = gTTS(text=text, lang=self.lang)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_path = fp.name
            tts.save(temp_path)
            playsound.playsound(temp_path)
            os.unlink(temp_path)
            self._speaking = False
            logger.info(f"gTTS 播放: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"gTTS 播放失败: {e}")
            self._speaking = False
            return False

    def speak_async(self, text: str) -> Optional[str]:
        import uuid
        task_id = str(uuid.uuid4())[:8]

        def _play():
            self.speak(text)

        thread = threading.Thread(target=_play, daemon=True)
        thread.start()
        return task_id

    def is_speaking(self) -> bool:
        return self._speaking

    def stop(self) -> None:
        self._speaking = False

    def set_voice(self, voice_id: str) -> None:
        logger.warning("gTTS 不支持切换音色")


class SimulatedSynthesis(SpeechSynthesisInterface):
    """模拟语音合成（仅打印）"""

    def __init__(self):
        self._speaking = False

    def speak(self, text: str) -> bool:
        print(f"\n[模拟TTS] {text}\n")
        logger.info(f"[模拟TTS] {text}")
        return True

    def speak_async(self, text: str) -> Optional[str]:
        import uuid
        task_id = str(uuid.uuid4())[:8]
        threading.Thread(target=lambda: self.speak(text), daemon=True).start()
        return task_id

    def is_speaking(self) -> bool:
        return False

    def stop(self) -> None:
        pass

    def set_voice(self, voice_id: str) -> None:
        pass


def create_speech_synthesis(engine: str, rate: int = 180, volume: float = 1.0) -> SpeechSynthesisInterface:
    """
    工厂函数：创建语音合成实例

    Args:
        engine: pyttsx3 / gtts / none
        rate: 语速（仅 pyttsx3）
        volume: 音量（仅 pyttsx3）

    Returns:
        SpeechSynthesisInterface 实例
    """
    if engine == "pyttsx3":
        try:
            import pyttsx3
            synthesizer = Pyttsx3Synthesis(rate, volume)
            # 测试初始化
            if synthesizer._init_engine():
                return synthesizer
            else:
                logger.warning("pyttsx3 初始化失败，降级到模拟模式")
        except ImportError:
            logger.warning("pyttsx3 未安装，降级到模拟模式")

    elif engine == "gtts":
        try:
            from gtts import gTTS
            synthesizer = GttsSynthesis()
            logger.info("gTTS 初始化成功")
            return synthesizer
        except ImportError:
            logger.warning("gtts 未安装，降级到模拟模式")

    logger.info("使用模拟语音合成模式")
    return SimulatedSynthesis()
