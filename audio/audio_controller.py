"""
模块名称：audio_controller.py
功能描述：语音控制器，管理 STT/TTS 状态机
依赖：threading, time

设计要点（在线 ASR 场景）：
  - 半双工：TTS 播放期间不处理 ASR 结果，避免回声干扰
  - get_user_input 是 STT 的唯一消费者，无竞态
  - _handle_idle / _handle_listening 不读取 STT
"""

import logging
import threading
import time
from enum import Enum
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)


class AudioState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


class AudioController:
    """
    语音控制器

    状态机：IDLE -> LISTENING -> PROCESSING -> SPEAKING -> IDLE
    在线 ASR 场景：get_user_input 直接从 STT 读取，状态机仅维护 TTS 播放状态。
    """

    # TTS 播放结束后忽略 ASR 结果的冷却时间（秒），防止回声干扰
    TTS_COOLDOWN = 4.0

    def __init__(self, config):
        from audio.speech_recognition import create_speech_recognition
        from audio.speech_synthesis import create_speech_synthesis
        self.config = config

        self._stt = create_speech_recognition(config)
        self._tts = create_speech_synthesis(config)

        self._wake_words = getattr(config, 'AUDIO_WAKE_WORDS', ["你好", "小机器人"])
        self._listen_timeout = getattr(config, 'AUDIO_LISTEN_TIMEOUT', 5.0)

        # 状态管理
        self._state = AudioState.IDLE
        self._state_lock = threading.Lock()
        self._wake_word_enabled = True
        self._pending_text = None
        self._pending_text_lock = threading.Lock()
        self._ask_question_result = None
        self._ask_question_event = threading.Event()

        # TTS 回声冷却
        self._tts_end_time = 0.0

        # 回调
        self._wake_word_callback = None
        self._state_change_callback = None

        self._running = False
        self._worker_thread = None

        self._stt.set_wake_words(self._wake_words)

        print(f"[DEBUG] AudioController 唤醒词: {self._wake_words}")
        print(f"[DEBUG] STT 实例 ID: {id(self._stt)}")

    def start(self) -> bool:
        if self._running:
            return True
        if not self._stt.start():
            logger.error("STT 启动失败")
            return False
        self._running = True
        self._worker_thread = threading.Thread(target=self._state_worker, daemon=True)
        self._worker_thread.start()
        self._set_state(AudioState.IDLE)
        logger.info("语音控制器启动成功")
        return True

    def stop(self) -> None:
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
        self._stt.stop()
        self._tts.stop()
        self._set_state(AudioState.IDLE)
        logger.info("语音控制器已停止")

    def _set_state(self, new_state: AudioState):
        with self._state_lock:
            old_state = self._state
            if old_state == new_state:
                return
            self._state = new_state
            logger.debug(f"状态转换: {old_state.value} -> {new_state.value}")
        if self._state_change_callback:
            try:
                self._state_change_callback(new_state.value, old_state.value)
            except Exception as e:
                logger.error(f"状态回调异常: {e}")

    def _get_state(self) -> AudioState:
        with self._state_lock:
            return self._state

    # ---------- 状态机（仅用于 TTS 播放状态追踪） ----------

    def _state_worker(self):
        while self._running:
            state = self._get_state()
            if state == AudioState.SPEAKING:
                self._handle_speaking()
            elif state == AudioState.LISTENING:
                self._handle_listening()
            elif state == AudioState.PROCESSING:
                self._handle_processing()
            elif state == AudioState.IDLE:
                self._handle_idle()
            time.sleep(0.1)

    def _handle_idle(self):
        """IDLE 状态：检测唤醒词（不读取 STT，由 get_user_input 处理）"""
        # 在线 ASR 场景下，唤醒词检测由主循环通过 get_user_input 完成
        pass

    def _handle_listening(self):
        """LISTENING 状态：等待超时或外部 respond（在线 ASR 不过滤文本）"""
        if hasattr(self._stt, 'enable_wake_word_filter'):
            self._stt.enable_wake_word_filter(False)

        time.sleep(self._listen_timeout)

        if hasattr(self._stt, 'enable_wake_word_filter'):
            self._stt.enable_wake_word_filter(True)

        self._wake_word_enabled = True
        self._set_state(AudioState.IDLE)

    def _handle_processing(self):
        """PROCESSING 状态：等待外部 respond()"""
        time.sleep(0.05)

    def _handle_speaking(self):
        """SPEAKING 状态：等待 TTS 播放完成，记录结束时间"""
        if not self._tts.is_speaking():
            self._tts_end_time = time.time()
            logger.debug(f"TTS 播放完成，设置冷却 {self.TTS_COOLDOWN}s")
            self._wake_word_enabled = True
            self._set_state(AudioState.IDLE)

    # ---------- 对外接口 ----------

    def get_user_input(self, timeout: float = 0.1) -> Optional[str]:
        """
        获取用户语音输入（在线 ASR 场景的唯一 STT 消费者）

        半双工控制：
          - TTS 播放结束后的冷却期内不返回结果（避免回声干扰）
          - 冷却期后直接从 STT 引擎读取

        Args:
            timeout: 等待超时（秒）

        Returns:
            用户输入文本，或无
        """
        # TTS 播放中不处理 ASR 结果（防止回声干扰）
        if self._tts.is_speaking():
            return None

        # TTS 冷却期：清空 STT 队列（丢弃回声），不返回结果
        since_tts = time.time() - self._tts_end_time
        if since_tts < self.TTS_COOLDOWN:
            # 丢弃冷却期内所有 ASR 结果（TTS 回声）
            try:
                while self._stt.get_text() is not None:
                    pass
            except Exception:
                pass
            return None

        # 每次调用至少检查一次 STT
        try:
            text = self._stt.get_text()
            if text:
                logger.debug(f"[STT] 识别: '{text[:40]}'")
                return text
        except Exception:
            pass

        # timeout > 0 时继续轮询
        if timeout > 0:
            end = time.time() + timeout
            while time.time() < end:
                try:
                    text = self._stt.get_text()
                    if text:
                        return text
                except Exception:
                    pass

                with self._pending_text_lock:
                    if self._pending_text is not None:
                        t = self._pending_text
                        self._pending_text = None
                        return t
                time.sleep(0.02)

            time.sleep(0.02)

        return None

    def respond(self, text: str) -> bool:
        if not text:
            self._wake_word_enabled = True
            self._set_state(AudioState.IDLE)
            return False
        task_id = self._tts.speak_async(text)
        if task_id:
            self._set_state(AudioState.SPEAKING)
            logger.info(f"开始语音回复: {text[:50]}...")
            return True
        else:
            self._wake_word_enabled = True
            self._set_state(AudioState.IDLE)
            return False

    def ask_question(self, text: str, timeout: float = 10.0) -> Optional[str]:
        task_id = self._tts.speak_async(text)
        if not task_id:
            return None
        logger.info(f"主动提问: {text}")
        while self._tts.is_speaking():
            time.sleep(0.1)
        self._wake_word_enabled = False
        self._set_state(AudioState.LISTENING)
        with self._pending_text_lock:
            self._pending_text = None
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self._pending_text_lock:
                if self._pending_text is not None:
                    answer = self._pending_text
                    self._pending_text = None
                    self._wake_word_enabled = True
                    self._set_state(AudioState.IDLE)
                    return answer
            time.sleep(0.1)
        self._wake_word_enabled = True
        self._set_state(AudioState.IDLE)
        return None

    def enable_wake_word(self, enable: bool):
        self._wake_word_enabled = enable

    def on_wake_word(self, callback: Callable):
        self._wake_word_callback = callback
        logger.info("唤醒词回调已注册")

    def on_state_change(self, callback: Callable[[str, str], None]):
        self._state_change_callback = callback
        logger.info("状态变化回调已注册")

    def get_state(self) -> str:
        return self._get_state().value

    def is_speaking(self) -> bool:
        return self._tts.is_speaking()
