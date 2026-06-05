"""
模块名称：fusion.py
功能描述：多模态数据融合模块，汇集 Vision、Speech 和 Health 数据
依赖：time, logging, threading
"""

import time
import logging
import threading
from typing import Dict, Any, Optional

from fusion.base import FusionInterface

logger = logging.getLogger(__name__)


class FusionModule(FusionInterface):
    """
    多模态数据融合模块
    """

    # 健康数据最大有效期（秒），超过此时间认为数据过期
    HEALTH_DATA_MAX_AGE = 3.0

    def __init__(self, vision_module, audio_controller, comm_controller=None, config=None):
        """
        Args:
            vision_module: VisionModule 实例
            audio_controller: AudioController 实例
            comm_controller: CommController 实例（可选，用于获取健康数据）
            config: Config 实例（可选）
        """
        self._vision = vision_module
        self._audio = audio_controller
        self._comm = comm_controller
        self._config = config

        # 语音消费管理
        self._last_speech_text = None
        self._speech_consumed = True

        # 健康数据缓存（带时间戳）
        self._health_data = None
        self._health_timestamp = 0
        self._sensor_status = None
        self._sensor_status_timestamp = 0
        self._health_lock = threading.Lock()

        # 消费模式配置
        self._auto_consume = getattr(config, 'FUSION_CONSUME_SPEECH', True) if config else True

        # 健康数据过期时间
        self._health_max_age = getattr(config, 'HEALTH_DATA_MAX_AGE', self.HEALTH_DATA_MAX_AGE) if config else self.HEALTH_DATA_MAX_AGE

        # 注册健康数据回调
        if self._comm:
            self._comm.on_health_data(self._on_health_data)
            self._comm.on_sensor_status(self._on_sensor_status)
            logger.info("FusionModule 已注册健康数据回调")

        logger.info("FusionModule 初始化完成")

    def _on_health_data(self, health: Dict[str, Any]) -> None:
        """健康数据回调"""
        with self._health_lock:
            self._health_data = health
            self._health_timestamp = time.time()
            logger.debug(f"健康数据更新: HR={health.get('heart_rate')}, O2={health.get('oxygen')}")

    def _on_sensor_status(self, status: Dict[str, Any]) -> None:
        """传感器状态回调"""
        with self._health_lock:
            self._sensor_status = status
            self._sensor_status_timestamp = time.time()
            logger.debug(f"传感器状态更新: {status}")

    def _get_current_health_data(self) -> Dict[str, Any]:
        """
        获取当前健康数据（带时效检查）

        Returns:
            健康数据字典，过期或无效时返回带默认值的字典
        """
        result = {
            'heart_rate': None,
            'heart_rate_valid': False,
            'oxygen': None,
            'oxygen_valid': False,
            'is_finger_detected': False,
            'sensor_status': None,
            'is_health_data_fresh': False
        }

        with self._health_lock:
            if self._health_data:
                data_age = time.time() - self._health_timestamp
                is_fresh = data_age < self._health_max_age

                if is_fresh:
                    result['heart_rate'] = self._health_data.get('heart_rate')
                    result['heart_rate_valid'] = self._health_data.get('heart_rate_valid', False)
                    result['oxygen'] = self._health_data.get('oxygen')
                    result['oxygen_valid'] = self._health_data.get('oxygen_valid', False)
                    result['is_health_data_fresh'] = True

                result['is_finger_detected'] = result['heart_rate_valid'] or result['oxygen_valid']

            if self._sensor_status:
                status_age = time.time() - self._sensor_status_timestamp
                if status_age < self._health_max_age:
                    result['sensor_status'] = self._sensor_status.get('status')

        return result

    def get_user_state(self) -> Dict[str, Any]:
        """
        获取当前用户状态快照
        """
        timestamp = time.time()

        # 获取视觉模块结果
        emotion_result = self._vision.get_emotion() if self._vision else None
        has_face = emotion_result is not None

        # 获取语音模块结果（极短超时轮流检查 pending/stt，在线 ASR 场景）
        speech_text = self._audio.get_user_input(timeout=0.0) if self._audio else None

        # 管理语音消费标记
        if speech_text is not None:
            self._last_speech_text = speech_text
            self._speech_consumed = False

        speech_has_new = not self._speech_consumed and self._last_speech_text is not None

        # 获取健康数据（带时效检查）
        health = self._get_current_health_data()

        # 构建状态字典
        state = {
            'timestamp': timestamp,
            'has_face': has_face,
            'has_speech': speech_has_new,
            'face_emotion': emotion_result,
            'speech_text': self._last_speech_text if speech_has_new else None,
            'speech_has_new': speech_has_new,
            'heart_rate': health['heart_rate'],
            'heart_rate_valid': health['heart_rate_valid'],
            'oxygen': health['oxygen'],
            'oxygen_valid': health['oxygen_valid'],
            'is_finger_detected': health['is_finger_detected'],
            'sensor_status': health['sensor_status'],
            'is_health_data_fresh': health['is_health_data_fresh'],
            'fusion_ready': self._vision is not None or self._audio is not None
        }

        # 自动消费语音
        if self._auto_consume and speech_has_new:
            self._speech_consumed = True

        return state

    def has_face(self) -> bool:
        """是否检测到人脸"""
        if not self._vision:
            return False
        emotion = self._vision.get_emotion()
        return emotion is not None

    def has_speech(self) -> bool:
        """是否有新的语音输入（未消费）"""
        return not self._speech_consumed and self._last_speech_text is not None

    def get_emotion(self) -> Optional[Dict[str, Any]]:
        """快捷获取情绪结果"""
        if not self._vision:
            return None
        return self._vision.get_emotion()

    def get_speech_text(self) -> Optional[str]:
        """
        快捷获取语音文本（自动消费）

        **重要提示：**
            此方法不会主动从 AudioController 获取新语音。
            需要先调用 get_user_state() 更新内部缓存，此方法才能返回有效值。
            推荐使用 get_user_state() 中的 'speech_text' 字段。

        Returns:
            语音文本，若无新语音返回 None
        """
        if self._speech_consumed or self._last_speech_text is None:
            return None

        text = self._last_speech_text
        self._speech_consumed = True
        logger.debug(f"消费语音: {text}")
        return text

    def get_health_data(self) -> Optional[Dict[str, Any]]:
        """获取最新健康数据"""
        with self._health_lock:
            if self._health_data:
                return self._health_data.copy()
            return None

    def is_finger_detected(self) -> bool:
        """是否检测到手指（传感器有效）"""
        with self._health_lock:
            if self._health_data:
                return self._health_data.get('heart_rate_valid', False) or \
                       self._health_data.get('oxygen_valid', False)
            return False

    def reset_speech_consumed(self) -> None:
        """重置语音消费标记"""
        self._speech_consumed = True
        self._last_speech_text = None
        logger.debug("语音消费标记已重置")

    def to_dict(self) -> Dict[str, Any]:
        """get_user_state 别名"""
        return self.get_user_state()

    def get_pretty_state(self, state: Optional[Dict[str, Any]] = None) -> str:
        """
        获取格式化的状态字符串（用于调试/日志）

        Args:
            state: 状态字典，为 None 时调用 get_user_state()

        Returns:
            格式化的状态字符串
        """
        if state is None:
            state = self.get_user_state()

        # 安全获取时间格式配置
        timestamp_format = '%H:%M:%S'
        if self._config:
            timestamp_format = getattr(self._config, 'FUSION_TIMESTAMP_FORMAT', '%H:%M:%S')

        timestamp_str = time.strftime(timestamp_format, time.localtime(state['timestamp']))

        lines = [
            f"[{timestamp_str}] 用户状态:",
            f"  人脸检测: {'✓' if state['has_face'] else '✗'}",
            f"  新语音: {'✓' if state['has_speech'] else '✗'}",
        ]

        if state['face_emotion']:
            emo = state['face_emotion']
            emotion_cn = emo.get('emotion_cn', '未知')
            confidence = emo.get('confidence', 0)
            lines.append(f"  情绪: {emotion_cn} ({confidence:.0f}%)")

        if state['speech_text']:
            lines.append(f"  语音: {state['speech_text']}")

        # 健康数据
        if state['is_finger_detected']:
            hr_info = f"{state['heart_rate']}bpm" if state['heart_rate_valid'] else "无效"
            ox_info = f"{state['oxygen']}%" if state['oxygen_valid'] else "无效"
            lines.append(f"  健康: 心率={hr_info}, 血氧={ox_info}")
        elif state['sensor_status']:
            lines.append(f"  传感器: {state['sensor_status']}")

        return "\n".join(lines)