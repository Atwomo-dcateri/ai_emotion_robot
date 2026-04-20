"""
模块名称：speech_synthesis.py
功能描述：espeak 离线语音合成
依赖：espeak 系统命令
"""

import logging
import threading
import subprocess
from typing import Optional

from audio.base import SpeechSynthesisInterface

logger = logging.getLogger(__name__)


class EspeakSynthesis(SpeechSynthesisInterface):
    """espeak 离线语音合成"""

    def __init__(self, rate: int = 150, volume: int = 100, voice: str = 'zh'):
        """
        Args:
            rate: 语速（单词/分钟），默认 150，中文建议 130-160
            volume: 音量 0-200，默认 100
            voice: 语音，'zh' 为中文，'en' 为英文，'zh+f1' 为女声
        """
        self.rate = rate
        self.volume = volume
        self.voice = voice
        self._speaking = False
        self._lock = threading.Lock()
        self._available = None
        

    def _check_espeak(self) -> bool:
        """检查 espeak 是否可用（缓存结果）"""
        if self._available is not None:
            return self._available

        try:
            result = subprocess.run(
                ['espeak', '--version'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                self._available = True
                logger.info("espeak 可用")
                return True
        except FileNotFoundError:
            logger.error("espeak 未安装，请运行: sudo apt-get install espeak -y")
        except Exception as e:
            logger.error(f"检查 espeak 失败: {e}")

        self._available = False
        return False

    def speak(self, text: str) -> bool:
        """
        同步播放语音

        Args:
            text: 要播放的文本

        Returns:
            是否成功
        """
        if not text:
            return False

        if not self._check_espeak():
            logger.error("espeak 不可用，无法播放")
            return False

        with self._lock:
            self._speaking = True

            # 构建命令
            # -v zh : 中文语音
            # -s 150 : 语速
            # -a 100 : 音量
            cmd = [
                'espeak',
                '-v', self.voice,
                '-s', str(self.rate),
                '-a', str(self.volume),
                text
            ]

            logger.info(f"TTS 播放: {text[:50]}...")

            try:
                # 使用 subprocess.run 等待完成
                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                self._speaking = False
                return True

            except subprocess.TimeoutExpired:
                logger.error("TTS 播放超时")
            except Exception as e:
                logger.error(f"TTS 播放失败: {e}")

            self._speaking = False
            return False

    def speak_async(self, text: str) -> Optional[str]:
        """
        异步播放语音

        Args:
            text: 要播放的文本

        Returns:
            任务 ID
        """
        import uuid
        task_id = str(uuid.uuid4())[:8]

        def _play():
            self.speak(text)

        thread = threading.Thread(target=_play, daemon=True)
        thread.start()

        logger.debug(f"异步 TTS 任务启动: {task_id}")
        return task_id

    def is_speaking(self) -> bool:
        """返回是否正在播放"""
        with self._lock:
            return self._speaking

    def stop(self) -> None:
        """停止当前播放"""
        with self._lock:
            self._speaking = False
            logger.info("TTS 播放已停止")

    def set_voice(self, voice_id: str) -> None:
        """
        切换音色

        可用语音:
        - zh : 中文（男声）
        - zh+f1 : 中文（女声）
        - zh+f2 : 中文（女声，更高音）
        - en : 英文
        - en-us : 美式英语
        - en-uk : 英式英语
        """
        self.voice = voice_id
        logger.info(f"切换语音: {voice_id}")

    def list_voices(self) -> list:
        """列出所有可用语音"""
        try:
            result = subprocess.run(
                ['espeak', '--voices'],
                capture_output=True,
                text=True,
                timeout=5
            )
            voices = []
            for line in result.stdout.split('\n')[1:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        voices.append({
                            'name': parts[3],
                            'language': parts[1],
                            'code': parts[0]
                        })
            return voices
        except Exception as e:
            logger.error(f"获取语音列表失败: {e}")
            return []


def create_speech_synthesis(config) -> SpeechSynthesisInterface:
    """
    工厂函数：创建语音合成实例

    Args:
        config: Config 类实例

    Returns:
        SpeechSynthesisInterface 实例
    """
    # 统一使用 espeak
    return EspeakSynthesis(
        rate=getattr(config, 'AUDIO_TTS_RATE', 150),
        volume=100,
        voice=getattr(config, 'AUDIO_TTS_VOICE', 'zh')
    )