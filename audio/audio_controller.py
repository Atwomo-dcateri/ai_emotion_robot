"""
模块名称：audio_controller.py
功能描述：语音控制器，管理 STT/TTS 状态机
依赖：threading, time
"""

import logging
import threading
import time
from enum import Enum
from typing import Optional, Callable, List

from audio.speech_recognition import create_speech_recognition
from audio.speech_synthesis import create_speech_synthesis

logger = logging.getLogger(__name__)


class AudioState(Enum):
    """语音控制器状态"""
    IDLE = "idle"           # 空闲，监听唤醒词
    LISTENING = "listening" # 监听用户输入
    PROCESSING = "processing"  # 处理中（等待决策）
    SPEAKING = "speaking"   # 播放语音


class AudioController:
    """
    语音控制器

    状态机：IDLE -> LISTENING -> PROCESSING -> SPEAKING -> IDLE

    对外接口：
        - start() / stop()
        - get_user_input()     获取用户语音输入
        - respond()            语音回复
        - ask_question()       主动提问并等待回答
        - enable_wake_word()   启用/禁用唤醒词
        - on_wake_word()       注册唤醒词回调
        - on_state_change()    注册状态变化回调
    """

    def __init__(self, config):
        """
        Args:
            config: Config 类实例
        """
        self.config = config

        # 初始化 STT
        self._stt = create_speech_recognition(config)

        # 初始化 TTS
        self._tts = create_speech_synthesis(config)

        # 唤醒词设置
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

        # 回调
        self._wake_word_callback = None
        self._state_change_callback = None

        # 内部线程
        self._running = False
        self._worker_thread = None

        # 设置唤醒词
        self._stt.set_wake_words(self._wake_words)

    def start(self) -> bool:
        """启动语音服务"""
        if self._running:
            logger.warning("语音服务已在运行")
            return True

        # 启动 STT
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
        """停止所有语音服务"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)

        self._stt.stop()
        self._tts.stop()

        self._set_state(AudioState.IDLE)
        logger.info("语音控制器已停止")

    def _set_state(self, new_state: AudioState):
        """设置状态并触发回调"""
        with self._state_lock:
            old_state = self._state
            if old_state == new_state:
                return
            self._state = new_state
            logger.debug(f"状态转换: {old_state.value} -> {new_state.value}")

        # 触发回调
        if self._state_change_callback:
            try:
                self._state_change_callback(new_state.value, old_state.value)
            except Exception as e:
                logger.error(f"状态回调异常: {e}")

    def _get_state(self) -> AudioState:
        with self._state_lock:
            return self._state

    def _state_worker(self):
        """状态机工作线程"""
        while self._running:
            current_state = self._get_state()

            if current_state == AudioState.IDLE:
                self._handle_idle()
            elif current_state == AudioState.LISTENING:
                self._handle_listening()
            elif current_state == AudioState.PROCESSING:
                self._handle_processing()
            elif current_state == AudioState.SPEAKING:
                self._handle_speaking()

            time.sleep(0.05)

    def _handle_idle(self):
        """IDLE 状态：监听唤醒词"""
        if not self._wake_word_enabled:
            return

        text = self._stt.get_text()
        if text:
            # 检查唤醒词
            for word in self._wake_words:
                if word in text:
                    logger.info(f"检测到唤醒词: '{word}'")
                    if self._wake_word_callback:
                        self._wake_word_callback()
                    self._set_state(AudioState.LISTENING)
                    break

    def _handle_listening(self):
        """LISTENING 状态：获取用户输入"""
        # 禁用唤醒词检测
        self._wake_word_enabled = False

        # 设置超时
        start_time = time.time()
        collected_text = []

        while time.time() - start_time < self._listen_timeout:
            text = self._stt.get_text()
            if text:
                collected_text.append(text)
                logger.debug(f"收集到: {text}")
                # 重置超时计时器（有输入时延长）
                start_time = time.time()

            time.sleep(0.1)

        # 超时或无输入
        if collected_text:
            full_text = "".join(collected_text)
            with self._pending_text_lock:
                self._pending_text = full_text
            logger.info(f"用户输入: {full_text}")
            self._set_state(AudioState.PROCESSING)
        else:
            logger.info("监听超时，无输入")
            self._wake_word_enabled = True
            self._set_state(AudioState.IDLE)

    def _handle_processing(self):
        """PROCESSING 状态：等待外部调用 respond()"""
        # 此状态不主动做任何事，等待外部触发
        # 防止空转，短暂休眠
        time.sleep(0.05)

    def _handle_speaking(self):
        """SPEAKING 状态：等待 TTS 播放完成"""
        if not self._tts.is_speaking():
            logger.debug("语音播放完成")
            self._wake_word_enabled = True
            self._set_state(AudioState.IDLE)

    # ========== 对外接口 ==========

    def get_user_input(self, timeout: float = 0.1) -> Optional[str]:
        """
        非阻塞获取用户语音输入

        Args:
            timeout: 等待超时（秒）

        Returns:
            用户输入文本，若无新输入返回 None
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            with self._pending_text_lock:
                if self._pending_text is not None:
                    text = self._pending_text
                    self._pending_text = None
                    return text
            time.sleep(0.02)
        return None

    def respond(self, text: str) -> bool:
        """
        语音回复用户

        Args:
            text: 回复内容

        Returns:
            是否成功开始播放
        """
        if not text:
            logger.warning("回复内容为空")
            self._wake_word_enabled = True
            self._set_state(AudioState.IDLE)
            return False

        # 异步播放
        task_id = self._tts.speak_async(text)
        if task_id:
            self._set_state(AudioState.SPEAKING)
            logger.info(f"开始语音回复: {text[:50]}...")
            return True
        else:
            logger.error("语音回复失败")
            self._wake_word_enabled = True
            self._set_state(AudioState.IDLE)
            return False

    def ask_question(self, text: str, timeout: float = 10.0) -> Optional[str]:
        """
        主动提问并等待回答

        Args:
            text: 提问内容
            timeout: 等待回答超时（秒）

        Returns:
            用户回答文本，超时返回 None
        """
        # 先异步播放问题
        task_id = self._tts.speak_async(text)
        if not task_id:
            logger.error("提问语音播放失败")
            return None

        logger.info(f"主动提问: {text}")

        # 等待语音播放完成（简单等待，可优化）
        while self._tts.is_speaking():
            time.sleep(0.1)

        # 进入监听状态
        self._wake_word_enabled = False
        self._set_state(AudioState.LISTENING)

        # 清空之前的输入
        with self._pending_text_lock:
            self._pending_text = None

        # 等待回答
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self._pending_text_lock:
                if self._pending_text is not None:
                    answer = self._pending_text
                    self._pending_text = None
                    logger.info(f"用户回答: {answer}")
                    self._wake_word_enabled = True
                    self._set_state(AudioState.IDLE)
                    return answer
            time.sleep(0.1)

        logger.warning(f"提问超时，无回答: {text}")
        self._wake_word_enabled = True
        self._set_state(AudioState.IDLE)
        return None

    def enable_wake_word(self, enable: bool) -> None:
        """启用/禁用唤醒词监听"""
        self._wake_word_enabled = enable
        logger.debug(f"唤醒词监听: {'启用' if enable else '禁用'}")

    def on_wake_word(self, callback: Callable) -> None:
        """注册唤醒词回调"""
        self._wake_word_callback = callback
        logger.info("唤醒词回调已注册")

    def on_state_change(self, callback: Callable[[str, str], None]) -> None:
        """
        注册状态变化回调

        Args:
            callback: 回调函数，参数为 (new_state, old_state)
        """
        self._state_change_callback = callback
        logger.info("状态变化回调已注册")

    def get_state(self) -> str:
        """获取当前状态"""
        return self._get_state().value

    def is_speaking(self) -> bool:
        """是否正在播放语音"""
        return self._tts.is_speaking()