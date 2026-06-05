"""
模块名称：speech_recognition.py
功能描述：Vosk 离线语音识别（支持重采样）
依赖：vosk, pyaudio, numpy, scipy（或 librosa）
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
    """Vosk 离线语音识别（支持重采样）"""

    def __init__(self, model_path: str, sample_rate: int = 16000, device_index: int = None):
        """
        Args:
            model_path: Vosk 模型路径
            sample_rate: 目标采样率（Vosk 需要 16000）
            device_index: 输入设备索引
        """
        self.model_path = model_path
        self.target_sample_rate = sample_rate  # Vosk 需要的采样率
        self.device_index = device_index
        
        # 实际录音采样率（从设备检测）
        self.device_sample_rate = None
        
        self._model = None
        self._recognizer = None
        self._stream = None
        self._pa = None
        self._running = False
        self._text_queue = queue.Queue(maxsize=20)
        self._wake_words = []
        self._filter_wake_words = True  # 新增：是否过滤唤醒词
        self._listen_thread = None
        
        # 重采样器
        self._resampler = None

    def _detect_device_sample_rate(self) -> int:
        import pyaudio
        p = pyaudio.PyAudio()
        # 优先测试硬件最可能支持的速率
        test_rates = [44100, 48000, 16000, 8000]
        supported_rate = 44100 # 默认保底

        for rate in test_rates:
            try:
                # 关键：添加异常保护，并确保检测完不立即销毁 p
                is_supported = p.is_format_supported(
                    rate, 
                    input_device=self.device_index, 
                    input_channels=1, 
                    input_format=pyaudio.paInt16
                )
                if is_supported: # 这里 PyAudio 有自带的检测方法
                    supported_rate = rate
                    logger.info(f"设备原生支持采样率: {rate} Hz")
                    break
            except Exception:
                continue
        
        p.terminate() # 循环结束后再销毁
        return supported_rate

    def _init_resampler(self):
        """初始化重采样器"""
        if self.device_sample_rate == self.target_sample_rate:
            self._resampler = None
            logger.info("采样率匹配，无需重采样")
            return
        
        try:
            from scipy import signal
            self._resampler = 'scipy'
            logger.info(f"使用 scipy 重采样: {self.device_sample_rate} → {self.target_sample_rate}")
        except ImportError:
            try:
                import librosa
                self._resampler = 'librosa'
                logger.info(f"使用 librosa 重采样: {self.device_sample_rate} → {self.target_sample_rate}")
            except ImportError:
                # 使用简单的线性插值
                self._resampler = 'simple'
                logger.warning(f"使用简单重采样: {self.device_sample_rate} → {self.target_sample_rate}")
                logger.warning("建议安装 scipy 获得更好效果: pip3 install scipy")

    def _resample(self, data: bytes) -> bytes:
        """重采样音频数据"""
        if self._resampler is None:
            return data
        
        # 转换为 numpy 数组
        audio = np.frombuffer(data, dtype=np.int16)
        
        if self._resampler == 'scipy':
            from scipy import signal
            # 计算重采样比例
            ratio = self.target_sample_rate / self.device_sample_rate
            # 重采样
            resampled = signal.resample(audio, int(len(audio) * ratio))
            return resampled.astype(np.int16).tobytes()
        
        elif self._resampler == 'librosa':
            import librosa
            # 转换为浮点数
            audio_float = audio.astype(np.float32) / 32768.0
            # 重采样
            resampled = librosa.resample(
                audio_float, 
                orig_sr=self.device_sample_rate, 
                target_sr=self.target_sample_rate
            )
            # 转换回 int16
            return (resampled * 32767).astype(np.int16).tobytes()
        
        else:
            # 简单线性插值
            ratio = self.target_sample_rate / self.device_sample_rate
            old_len = len(audio)
            new_len = int(old_len * ratio)
            
            old_indices = np.arange(old_len)
            new_indices = np.linspace(0, old_len - 1, new_len)
            
            resampled = np.interp(new_indices, old_indices, audio)
            return resampled.astype(np.int16).tobytes()

    def start(self) -> bool:
        import pyaudio
        import vosk

        try:
            vosk.SetLogLevel(-1) # 减少冗余日志
            
            # 1. 检测真实硬件速率（你会得到 44100）
            self.device_sample_rate = self._detect_device_sample_rate()
            # 2. Vosk 必须使用 16000 才能获得最佳效果
            self.target_sample_rate = 16000 
            
            self._init_resampler()
            
            self._model = vosk.Model(self.model_path)
            # 识别器必须和最终喂给它的数据频率一致（即重采样后的 16k）
            self._recognizer = vosk.KaldiRecognizer(self._model, self.target_sample_rate)

            self._pa = pyaudio.PyAudio()
            
            # 3. 打开音频流时使用硬件的原生速率
            self._stream = self._pa.open(
                rate=self.device_sample_rate,
                channels=1, # 强制单声道，解决 -9998
                format=pyaudio.paInt16,
                input=True,
                input_device_index=self.device_index,
                # 稍微加大缓冲区，防止树莓派处理重采样时溢出
                frames_per_buffer=int(self.device_sample_rate * 0.2) 
            )
            # ... 其余代码保持不变 ...

            self._running = True
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()
            print(f"[DEBUG] Vosk 启动: device={self.device_index}, rate={self.device_sample_rate}")
            logger.info(f"Vosk 识别启动成功")
            return True

        except Exception as e:
            logger.error(f"Vosk 启动失败: {e}")
            self._cleanup()
            return False

    # def _listen_loop(self):
    #     """后台监听循环"""
    #     import time
        
    #     while self._running:
    #         try:
    #             # 读取原始数据
    #             chunk_size = int(self.device_sample_rate * 0.1)  # 100ms
    #             data = self._stream.read(chunk_size, exception_on_overflow=False)
                
    #             if data and len(data) > 0:
    #                 # 重采样
    #                 resampled_data = self._resample(data)
                    
    #                 if self._recognizer.AcceptWaveform(resampled_data):
    #                     result = json.loads(self._recognizer.Result())
    #                     text = result.get("text", "").strip()
    #                     if text:
    #                         self._text_queue.put(text)
    #                         logger.debug(f"识别: {text}")

    #         except IOError as e:
    #             if e.errno not in (-9999, -9981):
    #                 logger.warning(f"音频错误: {e}")
    #             time.sleep(0.05)
    #         except Exception as e:
    #             logger.error(f"识别循环异常: {e}")
    #             time.sleep(0.1)
    def _listen_loop(self):
        """后台监听循环（支持部分结果收集和静音强制结束）"""
        import time
        
        silence_frames = 0
        SILENCE_THRESHOLD = 15  # 约 1.5 秒静音后强制结束（每帧 100ms）
        last_partial = ""
        
        while self._running:
            try:
                # 读取原始数据
                chunk_size = int(self.device_sample_rate * 0.1)  # 100ms
                data = self._stream.read(chunk_size, exception_on_overflow=False)
                
                if data and len(data) > 0:
                    # 重采样
                    resampled_data = self._resample(data)
                    
                    if self._recognizer.AcceptWaveform(resampled_data):
                        # 最终结果
                        result = json.loads(self._recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            self._text_queue.put(text)
                            logger.debug(f"识别: {text}")
                            last_partial = ""
                            silence_frames = 0
                    else:
                        # 部分结果
                        partial = json.loads(self._recognizer.PartialResult())
                        partial_text = partial.get("partial", "").strip()
                        
                        if partial_text:
                            # 有部分结果，重置静音计数
                            last_partial = partial_text
                            silence_frames = 0
                            logger.debug(f"部分: {partial_text}")
                        else:
                            # 无部分结果，增加静音计数
                            silence_frames += 1
                            
                            # 静音超时且有部分结果，强制结束
                            if silence_frames > SILENCE_THRESHOLD and last_partial:
                                # 强制获取最终结果
                                final_result = json.loads(self._recognizer.FinalResult())
                                final_text = final_result.get("text", "").strip()
                                if final_text:
                                    self._text_queue.put(final_text)
                                    logger.debug(f"强制结束: {final_text}")
                                else:
                                    # 如果没有最终结果，使用部分结果
                                    self._text_queue.put(last_partial)
                                    logger.debug(f"使用部分结果: {last_partial}")
                                last_partial = ""
                                silence_frames = 0

            except IOError as e:
                if e.errno not in (-9999, -9981):
                    logger.warning(f"音频错误: {e}")
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"识别循环异常: {e}")
                time.sleep(0.1)

    def _cleanup(self):
        """清理资源"""
        if self._stream:
            try:
                self._stream.close()
            except:
                pass
        if self._pa:
            try:
                self._pa.terminate()
            except:
                pass

    # def get_text(self) -> Optional[str]:
    #     """非阻塞获取最新识别文本"""
    #     try:
    #         text = self._text_queue.get_nowait()
    #         if self._wake_words:
    #             for word in self._wake_words:
    #                 if word in text:
    #                     return text
    #             return None
    #         return text
    #     except queue.Empty:
    #         return None
    # def get_text(self) -> Optional[str]:
    #     """非阻塞获取最新识别文本"""
    #     try:
    #         text = self._text_queue.get_nowait()
            
    #         # 如果启用了唤醒词过滤
    #         if self._filter_wake_words and self._wake_words:
    #             for word in self._wake_words:
    #                 if word in text:
    #                     return text
    #             return None  # 不包含唤醒词，丢弃
            
    #         return text
    #     except queue.Empty:
    #         return None

    def get_text(self) -> Optional[str]:
        """非阻塞获取最新识别文本"""
        try:
            text = self._text_queue.get_nowait()
            
            # 如果启用了唤醒词过滤（IDLE 状态）
            if self._filter_wake_words and self._wake_words:
                for word in self._wake_words:
                    if word in text:
                        return text
                return None  # 不包含唤醒词，丢弃
            
            # LISTENING 状态不过滤，返回所有文本
            return text
        except queue.Empty:
            return None

    def is_listening(self) -> bool:
        return self._running

    def set_wake_words(self, words: List[str]) -> None:
        self._wake_words = words
        logger.info(f"设置唤醒词: {words}")

    def enable_wake_word_filter(self, enable: bool) -> None:
        """
        启用/禁用唤醒词过滤
        
        Args:
            enable: True=只返回包含唤醒词的文本，False=返回所有文本
        """
        self._filter_wake_words = enable
        logger.debug(f"唤醒词过滤: {'启用' if enable else '禁用'}")

    def stop(self) -> None:
        """停止识别服务"""
        self._running = False
        
        if self._listen_thread:
            self._listen_thread.join(timeout=1.0)
        
        self._cleanup()
        logger.info("Vosk 识别已停止")


def create_speech_recognition(config) -> SpeechRecognitionInterface:
    """工厂函数"""
    if config.AUDIO_STT_ENGINE == "vosk":
        return VoskRecognition(
            model_path=config.AUDIO_VOSK_MODEL_PATH,
            sample_rate=config.AUDIO_SAMPLE_RATE,
            device_index=getattr(config, 'AUDIO_DEVICE_INDEX', None)
        )
    elif config.AUDIO_STT_ENGINE == "baidu":
        from audio.baidu_stt import BaiduRecognition
        return BaiduRecognition(
            api_key=getattr(config, 'BAIDU_ASR_API_KEY', ''),
            secret_key=getattr(config, 'BAIDU_ASR_SECRET_KEY', ''),
            app_id=getattr(config, 'BAIDU_ASR_APP_ID', ''),
            sample_rate=getattr(config, 'AUDIO_SAMPLE_RATE', 16000),
            device_index=getattr(config, 'AUDIO_DEVICE_INDEX', None),
            silence_timeout=getattr(config, 'ASR_SILENCE_TIMEOUT', 0.8),
            min_audio_duration=getattr(config, 'ASR_MIN_AUDIO_DURATION', 0.5),
        )
    else:
        raise ValueError(f"不支持的 STT 引擎: {config.AUDIO_STT_ENGINE}")