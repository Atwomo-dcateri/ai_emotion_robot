"""
模块名称：speech_recognition.py
功能描述：语音识别实现（Vosk + 模拟降级）
依赖：vosk, pyaudio, numpy
"""

import queue
import json
import logging
import threading
from typing import Optional, List

import numpy as np

from audio.base import SpeechRecognitionInterface

logger = logging.getLogger(__name__)


class VoskRecognition(SpeechRecognitionInterface):
    """Vosk 离线语音识别（优化版）"""

    def __init__(self, model_path: str, sample_rate: int = 16000):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self._model = None
        self._recognizer = None
        self._stream = None
        self._pa = None
        self._running = False
        self._text_queue = queue.Queue(maxsize=20)
        self._wake_words = []
        self._listen_thread = None

    def start(self) -> bool:
        try:
            import pyaudio
            import vosk

            self._model = vosk.Model(self.model_path)
            self._recognizer = vosk.KaldiRecognizer(self._model, self.sample_rate)
            
            # 优化配置
            self._recognizer.SetWords(False)
            self._recognizer.SetPartialWords(False)

            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                rate=self.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=8000,
                input_device_index=None,
                stream_callback=None
            )

            self._running = True
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()

            logger.info(f"Vosk 识别启动成功，模型: {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Vosk 启动失败: {e}")
            return False

    def _listen_loop(self):
        """后台监听循环（优化版）"""
        import time
        
        silent_chunks = 0
        accumulated_text = []
        
        while self._running:
            try:
                data = self._stream.read(8000, exception_on_overflow=False)
                
                if data and self._recognizer:
                    if self._recognizer.AcceptWaveform(data):
                        result = json.loads(self._recognizer.Result())
                        text = result.get("text", "").strip()
                        
                        if text:
                            accumulated_text.append(text)
                            logger.debug(f"识别片段: {text}")
                            
                            # 检测句子结束
                            if text.endswith(('。', '！', '？', '；', '!', '?')):
                                full_text = "".join(accumulated_text)
                                self._text_queue.put(full_text)
                                accumulated_text = []
                                silent_chunks = 0
                    else:
                        # 可选：处理部分结果
                        pass
                        
            except IOError as e:
                logger.warning(f"音频读取错误: {e}")
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"识别循环异常: {e}")
                time.sleep(0.05)
        
        # 清理剩余文本
        if accumulated_text:
            self._text_queue.put("".join(accumulated_text))

    def get_text(self) -> Optional[str]:
        try:
            return self._text_queue.get_nowait()
        except queue.Empty:
            return None

    def is_listening(self) -> bool:
        return self._running

    def set_wake_words(self, words: List[str]) -> None:
        self._wake_words = words
        logger.info(f"设置唤醒词: {words}")

    def stop(self) -> None:
        self._running = False
        if self._listen_thread:
            self._listen_thread.join(timeout=1.0)
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._pa:
            self._pa.terminate()
        logger.info("Vosk 识别已停止")


class SimulatedRecognition(SpeechRecognitionInterface):
    """模拟语音识别（用于测试或无麦克风场景）"""

    def __init__(self):
        self._listening = False
        self._wake_words = []
        self._simulated_text = None

    def start(self) -> bool:
        self._listening = True
        logger.info("模拟识别模式启动（在控制台输入文本）")
        return True

    def stop(self) -> None:
        self._listening = False
        logger.info("模拟识别模式停止")

    def get_text(self) -> Optional[str]:
        """非阻塞获取模拟输入"""
        import select
        import sys

        if not self._listening:
            return None

        # 检查是否有输入
        if select.select([sys.stdin], [], [], 0.0)[0]:
            try:
                text = sys.stdin.readline().strip()
                if text:
                    logger.info(f"[模拟输入] {text}")
                    return text
            except:
                pass
        return None

    def is_listening(self) -> bool:
        return self._listening

    def set_wake_words(self, words: List[str]) -> None:
        self._wake_words = words


def create_speech_recognition(engine: str, model_path: str = None, sample_rate: int = 16000) -> SpeechRecognitionInterface:
    """
    工厂函数：创建语音识别实例

    Args:
        engine: vosk / none
        model_path: Vosk 模型路径
        sample_rate: 采样率

    Returns:
        SpeechRecognitionInterface 实例
    """
    if engine == "vosk" and model_path:
        try:
            import vosk
            recognizer = VoskRecognition(model_path, sample_rate)
            if recognizer.start():
                return recognizer
            else:
                logger.warning("Vosk 启动失败，降级到模拟模式")
        except ImportError:
            logger.warning("vosk 未安装，降级到模拟模式")
        except Exception as e:
            logger.warning(f"Vosk 初始化异常: {e}，降级到模拟模式")

    logger.info("使用模拟语音识别模式")
    return SimulatedRecognition()