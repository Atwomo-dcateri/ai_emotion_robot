"""
模块名称：llm_engine.py
功能描述：云端 LLM 决策引擎（DeepSeek API）
依赖：requests, json
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional

from decision.base import DecisionInterface, create_oled_action, create_speak_action, create_servo_action

logger = logging.getLogger(__name__)


class LLMEngine(DecisionInterface):
    """
    云端 LLM 决策引擎

    使用 DeepSeek API 生成自然语言反应
    """

    # 系统提示词
    SYSTEM_PROMPT = """你是一个情感交互机器人，需要根据用户状态生成自然反应。

输入格式：
- emotion: 用户情绪（开心/悲伤/愤怒/恐惧/惊讶/平静）
- confidence: 情绪置信度（0-100）
- speech: 用户说的话（可能为空）

输出格式（严格 JSON，不要输出其他内容）：
{
    "oled_emotion": "机器人应显示的表情（开心/悲伤/愤怒/恐惧/惊讶/平静）",
    "speech": "机器人要说的话（中文，1-2句，简短自然）",
    "action": "动作（nod/点头，shake/摇头，none/无）"
}

交互原则：
- 有同理心：对用户情绪做出恰当反应
- 简洁自然：话语简短，像朋友聊天
- 主动关怀：情绪低落时可主动询问
- 安全边界：不提供医疗、心理咨询建议
"""

    def __init__(self, config):
        """
        初始化 LLM 引擎

        Args:
            config: Config 实例
                - DECISION_LLM_API_KEY: API 密钥
                - DECISION_LLM_API_URL: API 地址
                - DECISION_LLM_MODEL: 模型名称
                - DECISION_LLM_TIMEOUT: 超时时间
        """
        self._config = config

        # 读取配置
        self.api_key = getattr(config, 'DECISION_LLM_API_KEY', None)
        self.api_url = getattr(config, 'DECISION_LLM_API_URL', 'https://api.deepseek.com/v1/chat/completions')
        self.model = getattr(config, 'DECISION_LLM_MODEL', 'deepseek-chat')
        self.timeout = getattr(config, 'DECISION_LLM_TIMEOUT', 15)

        self._ready = bool(self.api_key)

        if not self._ready:
            logger.warning("LLM 引擎未配置 API Key，不可用")
        else:
            logger.info("LLM 引擎初始化完成")

    def _build_prompt(self, user_state: Dict[str, Any]) -> str:
        """构建用户提示词"""
        face_emotion = user_state.get('face_emotion')
        speech_text = user_state.get('speech_text')

        if face_emotion:
            emotion = face_emotion.get('emotion_cn', '平静')
            confidence = face_emotion.get('confidence', 50)
            prompt = f"用户情绪：{emotion}（置信度 {confidence:.0f}%）\n用户说话：{speech_text if speech_text else '无'}"
        else:
            prompt = f"用户情绪：未检测到\n用户说话：{speech_text if speech_text else '无'}"

        return prompt

    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON
            response_text = response_text.strip()

            # 移除可能的 markdown 代码块标记
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            result = json.loads(response_text.strip())

            # 验证必需字段
            if 'oled_emotion' in result and 'speech' in result:
                return result
            else:
                logger.warning(f"LLM 响应缺少必需字段: {result}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}, 原始响应: {response_text[:200]}")
            return None

    def decide(self, user_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        调用 LLM 生成动作指令

        Args:
            user_state: Fusion 状态字典

        Returns:
            动作指令列表
        """
        if not self._ready:
            logger.warning("LLM 引擎未就绪")
            return []

        # 构建请求
        prompt = self._build_prompt(user_state)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
            "max_tokens": 200
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            content = data['choices'][0]['message']['content']

            result = self._parse_response(content)
            if not result:
                return []

            # 转换为动作指令
            actions = []

            # OLED 表情
            oled_emotion = result.get('oled_emotion', '平静')
            confidence = user_state.get('face_emotion', {}).get('confidence', 75) if user_state.get('face_emotion') else 75
            actions.append({'type': 'oled', 'emotion': oled_emotion, 'confidence': confidence})

            # 语音回复
            speech_text = result.get('speech')
            if speech_text:
                actions.append({'type': 'speak', 'text': speech_text})

            # 舵机动作
            action = result.get('action', 'none')
            if action in ['nod', 'shake']:
                actions.append({'type': 'servo', 'move': action, 'times': 1})

            logger.info(f"LLM 决策: {result}")
            return actions

        except requests.Timeout:
            logger.error("LLM 请求超时")
            return []
        except requests.RequestException as e:
            logger.error(f"LLM 请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"LLM 决策异常: {e}")
            return []

    def is_ready(self) -> bool:
        """返回 LLM 引擎是否就绪"""
        return self._ready