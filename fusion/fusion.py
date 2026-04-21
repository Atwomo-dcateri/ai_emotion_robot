"""
模块名称：fusion.py
功能描述：多模态数据融合模块，汇集 Vision 和 Speech 模块输出
依赖：time, logging
"""

import time
import logging
from typing import Dict, Any, Optional

from fusion.base import FusionInterface

logger = logging.getLogger(__name__)


class FusionModule(FusionInterface):
    """
    多模态数据融合模块

    职责：
        - 汇集 Vision 和 Speech 模块的最新输出
        - 统一时间戳
        - 输出结构化的用户状态字典
        - 管理语音消费标记，避免重复处理

    设计原则：
        - 轻量聚合，不做复杂推理
        - 非阻塞读取各模块的 get_xxx() 接口
        - 以调用时刻的时间戳作为状态快照的统一时间

    **重要使用说明：**
        - 主循环应统一调用 get_user_state() 获取状态快照
        - get_speech_text() 依赖于 get_user_state() 先更新内部缓存
        - 推荐使用 get_user_state() 中的 'speech_has_new' 字段判断新语音
        - 避免混用 get_user_state() 和 get_speech_text() 两种消费方式
    """

    def __init__(self, vision_module, audio_controller, config=None):
        """
        Args:
            vision_module: VisionModule 实例
            audio_controller: AudioController 实例
            config: Config 实例（可选）
        """
        self._vision = vision_module
        self._audio = audio_controller
        self._config = config

        # 语音消费管理
        self._last_speech_text = None
        self._speech_consumed = True

        # 消费模式配置
        self._auto_consume = getattr(config, 'FUSION_CONSUME_SPEECH', True) if config else True

        logger.info("FusionModule 初始化完成")

    def get_user_state(self) -> Dict[str, Any]:
        """
        获取当前用户状态快照（推荐使用）

        此方法是 Fusion 模块的主要接口，每次调用会：
        1. 从 AudioController 获取最新语音（自动更新内部缓存）
        2. 从 VisionModule 获取最新情绪结果
        3. 返回统一时间戳的状态字典

        **推荐使用方式：**
            state = fusion.get_user_state()
            if state['speech_has_new']:
                handle_speech(state['speech_text'])

        Returns:
            用户状态字典，包含以下字段：
            {
                'timestamp': float,           # Unix 时间戳
                'has_face': bool,             # 是否检测到人脸
                'has_speech': bool,           # 是否有新语音输入
                'face_emotion': dict | None,  # 情绪结果
                'speech_text': str | None,    # 语音识别文本
                'speech_has_new': bool,       # 是否有未消费的新输入
                'heart_rate': None,           # 预留生理模块
                'fusion_ready': bool          # 融合数据是否有效
            }
        """
        timestamp = time.time()

        # 获取视觉模块结果
        emotion_result = self._vision.get_emotion() if self._vision else None
        has_face = emotion_result is not None

        # 获取语音模块结果（从 AudioController 主动获取）
        speech_text = self._audio.get_user_input(timeout=0.0) if self._audio else None

        # 管理语音消费标记
        if speech_text is not None:
            # 新语音到达
            self._last_speech_text = speech_text
            self._speech_consumed = False
            logger.debug(f"新语音: {speech_text}")

        # 判断是否有未消费的语音
        speech_has_new = not self._speech_consumed and self._last_speech_text is not None

        # 构建状态字典
        state = {
            'timestamp': timestamp,
            'has_face': has_face,
            'has_speech': speech_has_new,
            'face_emotion': emotion_result,
            'speech_text': self._last_speech_text if speech_has_new else None,
            'speech_has_new': speech_has_new,
            'heart_rate': None,  # 预留生理模块
            'fusion_ready': self._vision is not None or self._audio is not None
        }

        # 自动消费：如果启用了自动消费模式，且语音已被返回，则标记为已消费
        if self._auto_consume and speech_has_new:
            self._speech_consumed = True

        return state

    def has_face(self) -> bool:
        """
        是否检测到人脸

        Returns:
            True: 检测到人脸，False: 未检测到
        """
        if not self._vision:
            return False
        emotion = self._vision.get_emotion()
        return emotion is not None

    def has_speech(self) -> bool:
        """
        是否有新的语音输入（未消费）

        Returns:
            True: 有新语音且未消费，False: 无新语音或已消费
        """
        return not self._speech_consumed and self._last_speech_text is not None

    def get_emotion(self) -> Optional[Dict[str, Any]]:
        """
        快捷获取情绪结果

        Returns:
            情绪结果字典，无检测结果返回 None
        """
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

        return "\n".join(lines)