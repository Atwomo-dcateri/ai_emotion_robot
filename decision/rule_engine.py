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
        '小机器人': '我在呢',
        '小提琴': '我在呢',
        '嗨': '嗨，今天心情怎么样',
        '哈喽': '哈喽，有什么可以帮你的吗',
        '谢谢': '不客气，很高兴能帮到你',
        '拜拜': '再见，下次再聊',
        '再见': '再见，祝你开心'
    }

    # 健康数据告警规则（基础模板，阈值从 config 读取）
    _HEALTH_RULES_TEMPLATE = {
        'high_heart_rate': {
            'oled': '惊讶',
            'speech': ['心率有点快，要不要休息一下', '放松一下，深呼吸'],
            'action': None
        },
        'low_heart_rate': {
            'oled': '平静',
            'speech': ['心率有点慢，需要活动一下吗'],
            'action': None
        },
        'low_oxygen': {
            'oled': '惊讶',
            'speech': ['血氧偏低，注意呼吸', '建议深呼吸'],
            'action': None
        },
        'no_finger': {
            'oled': '平静',
            'speech': ['请将手指放在传感器上', '请贴紧传感器'],
            'action': None
        },
        'sensor_error': {
            'oled': '愤怒',
            'speech': ['传感器异常，请检查连接', '传感器需要校准'],
            'action': None
        }
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

        # 加载健康告警阈值
        self._hr_high_threshold = getattr(config, 'HEART_RATE_HIGH_THRESHOLD', 100) if config else 100
        self._hr_low_threshold = getattr(config, 'HEART_RATE_LOW_THRESHOLD', 60) if config else 60
        self._oxygen_low_threshold = getattr(config, 'OXYGEN_LOW_THRESHOLD', 95) if config else 95

        # 支持自定义健康告警规则
        custom_health_rules = getattr(config, 'HEALTH_ALERT_RULES', None) if config else None
        if custom_health_rules:
            self._health_rules = custom_health_rules
        else:
            self._health_rules = self._HEALTH_RULES_TEMPLATE.copy()
            # 动态添加阈值到规则中（供日志使用）
            self._health_rules['high_heart_rate']['threshold'] = self._hr_high_threshold
            self._health_rules['low_heart_rate']['threshold'] = self._hr_low_threshold
            self._health_rules['low_oxygen']['threshold'] = self._oxygen_low_threshold

        logger.info(f"RuleEngine 初始化完成 (HR阈值: {self._hr_low_threshold}-{self._hr_high_threshold}, O2阈值: {self._oxygen_low_threshold})")

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

    def _check_health_alerts(self, user_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检查健康数据告警

        Args:
            user_state: 用户状态字典

        Returns:
            告警动作列表，无告警返回空列表
        """
        actions = []

        hr = user_state.get('heart_rate')
        hr_valid = user_state.get('heart_rate_valid', False)
        oxygen = user_state.get('oxygen')
        oxygen_valid = user_state.get('oxygen_valid', False)
        finger = user_state.get('is_finger_detected', False)
        sensor_status = user_state.get('sensor_status')
        is_fresh = user_state.get('is_health_data_fresh', False)

        # 传感器错误（不受 fresh 限制）
        if sensor_status == 'error':
            rule = self._health_rules.get('sensor_error')
            if rule:
                actions.append(create_oled_action(rule['oled'], 80))
                if rule['speech']:
                    actions.append(create_speak_action(rule['speech'][0]))
                logger.info(f"健康告警: 传感器错误")
            return actions

        # 没有新鲜健康数据时，跳过所有健康告警
        if not is_fresh:
            return actions

        # 手指未检测到（仅在有健康数据连接时触发）
        if not finger:
            rule = self._health_rules.get('no_finger')
            if rule:
                actions.append(create_oled_action(rule['oled'], 50))
                if rule['speech']:
                    actions.append(create_speak_action(rule['speech'][0]))
                logger.info(f"健康告警: 未检测到手指")
            return actions

        # 心率检查（使用配置的阈值）
        if hr_valid and hr:
            if hr > self._hr_high_threshold:
                rule = self._health_rules.get('high_heart_rate')
                if rule:
                    actions.append(create_oled_action(rule['oled'], 75))
                    if rule['speech']:
                        actions.append(create_speak_action(rule['speech'][0]))
                    logger.info(f"健康告警: 心率过高 ({hr} > {self._hr_high_threshold})")
                    return actions
            elif hr < self._hr_low_threshold:
                rule = self._health_rules.get('low_heart_rate')
                if rule:
                    actions.append(create_oled_action(rule['oled'], 75))
                    if rule['speech']:
                        actions.append(create_speak_action(rule['speech'][0]))
                    logger.info(f"健康告警: 心率过低 ({hr} < {self._hr_low_threshold})")
                    return actions

        # 血氧检查
        if oxygen_valid and oxygen:
            if oxygen < self._oxygen_low_threshold:
                rule = self._health_rules.get('low_oxygen')
                if rule:
                    actions.append(create_oled_action(rule['oled'], 75))
                    if rule['speech']:
                        actions.append(create_speak_action(rule['speech'][0]))
                    logger.info(f"健康告警: 血氧过低 ({oxygen} < {self._oxygen_low_threshold})")
                    return actions

        return actions

    def decide(self, user_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据用户状态生成动作指令

        决策优先级：
        1. 健康数据告警（最高优先级）
        2. 语音关键词响应
        3. 情绪响应

        Args:
            user_state: Fusion 状态字典

        Returns:
            动作指令列表
        """
        actions = []

        # 优先级1：健康数据告警
        health_actions = self._check_health_alerts(user_state)
        if health_actions:
            return health_actions

        # 获取状态信息
        face_emotion = user_state.get('face_emotion')
        speech_text = user_state.get('speech_text')

        # 优先级2：语音关键词响应
        if speech_text:
            keyword_response = self._check_keyword_response(speech_text)
            if keyword_response:
                actions.append(create_speak_action(keyword_response))
                actions.append(create_servo_action('nod', 1))
                logger.info(f"规则引擎响应: 关键词={speech_text[:20]}, 回复={keyword_response}")
                return actions

        # 优先级3：基于情绪的响应
        if face_emotion:
            emotion_cn = face_emotion.get('emotion_cn')
            confidence = face_emotion.get('confidence', 50)
            rule = self._get_response(emotion_cn)

            # OLED 显示表情
            actions.append(create_oled_action(rule['oled'], confidence))

            # 语音回复
            speech_text_used = None
            if rule['speech']:
                speech_text_used = self._get_random_speech(rule['speech'])
                actions.append(create_speak_action(speech_text_used))

            # 舵机动作
            if rule['action']:
                actions.append(create_servo_action(rule['action'], 1))

            logger.info(f"规则引擎响应: 情绪={emotion_cn}, 回复={speech_text_used or '无'}")
            return actions

        # 无人脸检测且无语音时
        return [create_none_action()]

    def is_ready(self) -> bool:
        """规则引擎始终就绪"""
        return True

    def update_thresholds(self, hr_high: int = None, hr_low: int = None, oxygen_low: int = None):
        """
        动态更新健康告警阈值

        Args:
            hr_high: 心率过高阈值
            hr_low: 心率过低阈值
            oxygen_low: 血氧过低阈值
        """
        if hr_high is not None:
            self._hr_high_threshold = hr_high
            self._health_rules['high_heart_rate']['threshold'] = hr_high
        if hr_low is not None:
            self._hr_low_threshold = hr_low
            self._health_rules['low_heart_rate']['threshold'] = hr_low
        if oxygen_low is not None:
            self._oxygen_low_threshold = oxygen_low
            self._health_rules['low_oxygen']['threshold'] = oxygen_low

        logger.info(f"更新健康阈值: HR({self._hr_low_threshold}-{self._hr_high_threshold}), O2({self._oxygen_low_threshold})")
        