"""
模块名称：baidu_stt.py
功能描述：百度云 ASR 在线语音识别
依赖：requests, pyaudio
"""

import json
import time
import queue
import logging
import threading
from typing import Optional, List

import requests
from audio.base import SpeechRecognitionInterface

logger = logging.getLogger(__name__)

# ============================================================
# 百度 ASR API 常量
# ============================================================
BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
BAIDU_ASR_URL = "https://vop.baidu.com/server_api"
BAIDU_LANG = 1537   # 中文普通话
BAIDU_CUID = "ai_emotion_robot"


class BaiduRecognition(SpeechRecognitionInterface):
    """
    百度云 ASR 在线语音识别

    录音 + 静音检测 → 发送到百度 ASR → 返回识别文本

    Args:
        api_key: 百度云 API Key
        secret_key: 百度云 Secret Key
        app_id: 百度云 App ID
        sample_rate: 采样率
        device_index: 音频输入设备索引
        silence_timeout: 静音超时（秒）
        min_audio_duration: 最小录音时长（秒）
    """

    def __init__(self, api_key: str, secret_key: str, app_id: str = "",
                 sample_rate: int = 16000,
                 device_index: int = None,
                 silence_timeout: float = 0.8,
                 min_audio_duration: float = 0.5):
        self.api_key = api_key
        self.secret_key = secret_key
        self.app_id = app_id
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.silence_timeout = silence_timeout
        self.min_audio_duration = min_audio_duration

        self._access_token = None
        self._token_expires = 0
        self._running = False
        self._result_queue = queue.Queue(maxsize=10)
        self._wake_words = []
        self._filter_wake_words = False  # 在线 ASR 不过滤唤醒词
        self._process_thread = None

        # 录音
        self._stream = None
        self._pa = None

    def set_wake_words(self, words: List[str]) -> None:
        self._wake_words = words

    def enable_wake_word_filter(self, enable: bool) -> None:
        self._filter_wake_words = enable

    # ========== Token 管理 ==========

    def _get_token(self) -> Optional[str]:
        """获取或刷新百度 ASR access_token"""
        now = time.time()
        if self._access_token and now < self._token_expires - 60:
            return self._access_token

        logger.info("获取百度 ASR token...")
        try:
            resp = requests.post(BAIDU_TOKEN_URL, params={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key,
            }, timeout=10)
            data = resp.json()
            if "access_token" in data:
                self._access_token = data["access_token"]
                self._token_expires = now + data.get("expires_in", 2592000)
                logger.info("百度 ASR token 获取成功")
                return self._access_token
            else:
                logger.error(f"获取 token 失败: {data}")
                return None
        except Exception as e:
            logger.error(f"获取 token 异常: {e}")
            return None

    # ========== 录音 ==========

    def _init_recorder(self):
        """初始化录音"""
        if self._stream:
            return True

        import pyaudio
        self._pa = pyaudio.PyAudio()

        # 检测设备原生采样率
        self.device_rate = 16000
        for rate in [44100, 48000, 16000]:
            try:
                self._pa.is_format_supported(rate,
                    input_device=self.device_index,
                    input_channels=1,
                    input_format=pyaudio.paInt16)
                self.device_rate = rate
                break
            except:
                continue

        try:
            self._stream = self._pa.open(
                rate=self.device_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=int(self.device_rate * 0.1),
            )
            self._audio_buf = []       # [(bytes, rms_energy), ...]
            self._buf_lock = threading.Lock()
            self._max_rms = 0
            logger.info(f"录音启动: {self.device_rate}Hz")
            return True
        except Exception as e:
            logger.error(f"录音启动失败: {e}")
            return False

    def _resample(self, audio_bytes: bytes) -> bytes:
        import numpy as np
        if self.device_rate == self.sample_rate:
            return audio_bytes
        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        ratio = self.sample_rate / self.device_rate
        new_len = int(len(audio) * ratio)
        old_idx = np.arange(len(audio))
        new_idx = np.linspace(0, len(audio) - 1, new_len)
        resampled = np.interp(new_idx, old_idx, audio)
        return resampled.astype(np.int16).tobytes()

    def _calc_rms(self, data: bytes) -> float:
        """计算音频 RMS 能量"""
        import numpy as np
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        return float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0

    def _record_loop(self):
        """录音循环：持续录音，计算每帧能量用于 VAD"""
        import numpy as np
        while self._running:
            try:
                data = self._stream.read(int(self.device_rate * 0.1),
                                         exception_on_overflow=False)
                resampled = self._resample(data)
                # 增益提升（麦克风信号弱，放大 3 倍）
                audio = np.frombuffer(resampled, dtype=np.int16).astype(np.int32)
                audio = np.clip(audio * 3, -32768, 32767).astype(np.int16)
                resampled = audio.tobytes()
                rms = self._calc_rms(resampled)
                with self._buf_lock:
                    self._audio_buf.append((resampled, rms))
                    if rms > self._max_rms:
                        self._max_rms = rms
                    if len(self._audio_buf) > 150:
                        self._audio_buf = self._audio_buf[-150:]
            except Exception as e:
                logger.error(f"录音异常: {e}")
                time.sleep(0.1)

    def _is_speaking(self) -> bool:
        """检测最近 5 帧是否有人声"""
        with self._buf_lock:
            if not self._audio_buf:
                return False
            recent = self._audio_buf[-5:]

        # 有足够音频数据后再判断
        if self._max_rms < 30:
            return False

        threshold = self._max_rms * 0.4  # 最高音量的 40%
        return any(rms > threshold for _, rms in recent)

    def _pop_audio(self, max_sec: float = 4.0) -> bytes:
        """取出最近的人声音频并清空缓冲区"""
        with self._buf_lock:
            if not self._audio_buf:
                return b''
            n = int(max_sec / 0.1)
            frames = self._audio_buf[-n:]
            self._audio_buf = []
        return b''.join(f[0] for f in frames)

    # ========== 百度 ASR API 调用 ==========

    def _recognize(self, audio_bytes: bytes) -> Optional[str]:
        """
        发送音频到百度 ASR

        Args:
            audio_bytes: 16kHz 16bit PCM 音频数据

        Returns:
            识别文本
        """
        token = self._get_token()
        if not token:
            return None

        try:
            resp = requests.post(BAIDU_ASR_URL, params={
                "dev_pid": BAIDU_LANG,
                "cuid": BAIDU_CUID,
                "token": token,
            }, headers={"Content-Type": f"audio/pcm;rate={self.sample_rate}"},
               data=audio_bytes, timeout=15)

            result = resp.json()
            err_no = result.get("err_no", -1)

            if err_no == 0:
                texts = result.get("result", [])
                if texts:
                    return texts[0]
                return None
            elif err_no == 3301:
                logger.warning("ASR: 音频质量问题，忽略")
                return None
            elif err_no == 3302:
                logger.warning("ASR: token 失效，重新获取")
                self._access_token = None
                return None
            else:
                logger.debug(f"ASR 错误码 {err_no}: {result}")
                return None

        except Exception as e:
            logger.error(f"ASR 请求异常: {e}")
            return None

    # ========== 主处理循环 ==========

    def _process_loop(self):
        """
        后台处理循环（基于音频能量 VAD）：
        1. 检测人声开始
        2. 检测人声结束（连续 N 帧低能量）
        3. 发送音频到 ASR
        """
        was_speaking = False
        silence_frames = 0
        SILENCE_FRAMES_MAX = int(self.silence_timeout / 0.1)  # 约 8 帧

        while self._running:
            now_speaking = self._is_speaking()

            if now_speaking:
                if not was_speaking:
                    logger.debug("语音开始")
                was_speaking = True
                silence_frames = 0

            elif was_speaking:
                # 之前在说话，现在停了 → 计数静音帧
                silence_frames += 1
                if silence_frames >= SILENCE_FRAMES_MAX:
                    logger.debug("语音结束，发送 ASR")
                    audio = self._pop_audio()
                    min_bytes = int(self.sample_rate * self.min_audio_duration * 2)
                    if len(audio) > min_bytes:
                        self._queue_result(self._recognize(audio))
                    was_speaking = False
                    silence_frames = 0

            time.sleep(0.1)

    def _queue_result(self, text: Optional[str]):
        """将识别结果放入队列"""
        if not text or not text.strip():
            return

        logger.info(f"ASR: '{text}'")
        try:
            self._result_queue.put_nowait(text.strip())
        except queue.Full:
            try:
                self._result_queue.get_nowait()
                self._result_queue.put_nowait(text.strip())
            except queue.Empty:
                pass

    # ========== 接口方法 ==========

    def start(self) -> bool:
        if self._running:
            return True

        if not self.api_key or not self.secret_key:
            logger.error("百度 ASR 未配置 API Key / Secret Key")
            return False

        if not self._init_recorder():
            return False

        self._running = True
        self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()

        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()

        logger.info("百度 ASR 启动成功")
        return True

    def stop(self) -> None:
        self._running = False
        for t in [self._record_thread, self._process_thread]:
            if t:
                t.join(timeout=2.0)
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
        logger.info("百度 ASR 已停止")

    def is_listening(self) -> bool:
        return self._running

    def get_text(self) -> Optional[str]:
        try:
            text = self._result_queue.get_nowait()
            if self._filter_wake_words and self._wake_words:
                for word in self._wake_words:
                    if word in text:
                        return text
                return None
            return text
        except queue.Empty:
            return None


# ============================================================
def create_speech_recognition(config) -> SpeechRecognitionInterface:
    """工厂函数"""
    engine = getattr(config, 'AUDIO_STT_ENGINE', 'vosk')

    if engine == "baidu":
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
        from audio.speech_recognition import VoskRecognition
        return VoskRecognition(
            model_path=config.AUDIO_VOSK_MODEL_PATH,
            sample_rate=config.AUDIO_SAMPLE_RATE,
            device_index=getattr(config, 'AUDIO_DEVICE_INDEX', None),
        )
