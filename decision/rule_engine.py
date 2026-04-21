"""
模块名称：rule_engine.py
功能描述：基于规则的情感响应引擎（降级/离线方案）
依赖：random, logging
"""

import random
import logging
from typing import Dict, Any, List, Optional

from decision.base import DecisionInterface, create_oled_action, create_speak_action, create_servo_action, create_none_action

logger = logging.getLogger(__name__)


class RuleEngine(DecisionInterface):
    """
    基于规则的情感响应引擎

    特点：
        - 完全离线可用
        - 响应速度快
        - 规则可自定义配置
    """

    # 情绪响应规则表
    _DEFAULT_RULES = {
        '开心': {
            'oled': '开心',
            'speech': ['你看起来心情不错', '什么事这么开心', '开心就好', '和你聊天我也很开心'],
            'action': 'nod'
        },
        '悲伤': {
            'oled': '悲伤',
            'speech': ['别难过，我在这里陪着你', '需要聊聊吗', '一切都会好起来的', '抱抱你'],
            'action': None
        },
        '愤怒': {
            'oled': '平静',
            'speech': ['深呼吸，冷静一下', '生气对身体不好', '我陪着你，慢慢来'],
            'action': None
        },
        '恐惧': {
            'oled': '惊讶',
            'speech': ['别害怕，我在这里', '没事的，一切安全', '需要我帮忙吗'],
            'action': None
        },
        '惊讶': {
            'oled': '惊讶',
            'speech': ['哇，真的吗', '这很有趣', '真是没想到'],
            'action': None
        },
        '平静': {
            'oled': '平静',
            'speech': ['我在听', '有什么想聊的吗', '今天过得怎么样', '需要我做点什么吗'],
            'action': None
        }
    }

    _DEFAULT_RULE = {
        'oled': '平静',
        'speech': ['你好呀', '有什么可以帮你的吗'],
        'action': None
    }

    # 关键词响应规则
    _KEYWORD_RULES = {
        '你好': '你好呀，很高兴见到你',
        '嗨': '嗨，今天心情怎么样',
        '哈喽': '哈喽，有什么可以帮你的吗',
        '谢谢': '不客气，很高兴能帮到你',
        '拜拜': '再见，下次再聊',
        '再见': '再见，祝你开心'
    }

    def __init__(self, config=None, custom_rules: Optional[Dict] = None):
        """
        初始化规则引擎

        Args:
            config: Config 实例（可选）
            custom_rules: 自定义规则（覆盖默认规则）
        """
        self._config = config
        self._rules = custom_rules if custom_rules else self._DEFAULT_RULES.copy()

        # 支持从 config 加载自定义规则
        if config:
            custom = getattr(config, 'DECISION_FALLBACK_RULES', None)
            if custom:
                self._rules.update(custom)

        logger.info("RuleEngine 初始化完成")

    def _get_response(self, emotion: Optional[str]) -> Dict:
        """根据情绪获取响应"""
        if emotion and emotion in self._rules:
            return self._rules[emotion]
        return self._DEFAULT_RULE

    def _get_random_speech(self, speeches: List[str]) -> str:
        """随机选择一条回复语"""
        if not speeches:
            return "你好呀"
        return random.choice(speeches)

    def _check_keyword_response(self, speech_text: str) -> Optional[str]:
        """检查关键词响应"""
        if not speech_text:
            return None

        for keyword, response in self._KEYWORD_RULES.items():
            if keyword in speech_text:
                return response
        return None

    def decide(self, user_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据用户状态生成动作指令

        Args:
            user_state: Fusion 状态字典

        Returns:
            动作指令列表
        """
        actions = []

        # 获取情绪信息
        face_emotion = user_state.get('face_emotion')
        speech_text = user_state.get('speech_text')

        # 有语音输入时优先响应（关键词匹配）
        if speech_text:
            keyword_response = self._check_keyword_response(speech_text)
            if keyword_response:
                actions.append(create_speak_action(keyword_response))
                actions.append(create_servo_action('nod', 1))
                logger.info(f"规则引擎响应: 关键词={speech_text[:20]}, 回复={keyword_response}")
                return actions

        # 基于情绪的响应
        if face_emotion:
            emotion_cn = face_emotion.get('emotion_cn')
            confidence = face_emotion.get('confidence', 50)
            rule = self._get_response(emotion_cn)

            # OLED 显示表情
            actions.append(create_oled_action(rule['oled'], confidence))

            # 语音回复（变量在 if 块内定义，用于后续日志）
            speech_text_used = None
            if rule['speech']:
                speech_text_used = self._get_random_speech(rule['speech'])
                actions.append(create_speak_action(speech_text_used))

            # 舵机动作
            if rule['action']:
                actions.append(create_servo_action(rule['action'], 1))

            logger.info(f"规则引擎响应: 情绪={emotion_cn}, 回复={speech_text_used or '无'}")
            return actions

        # 无人脸检测时
        if not actions:
            # 默认静默或简单问候
            pass

        return actions if actions else [create_none_action()]

    def is_ready(self) -> bool:
        """规则引擎始终就绪"""
        return True