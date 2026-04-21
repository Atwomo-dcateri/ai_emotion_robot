"""
模块名称：decision_controller.py
功能描述：决策控制器，切换 LLM 和规则引擎
依赖：logging
"""

import logging
from typing import Dict, Any, List

from decision.base import DecisionInterface
from decision.rule_engine import RuleEngine
from decision.llm_engine import LLMEngine

logger = logging.getLogger(__name__)


class DecisionController(DecisionInterface):
    """
    决策控制器

    职责：
        - 优先使用 LLM 引擎
        - LLM 失败/超时/未配置时降级到规则引擎
        - 对外提供统一的 decide 接口
    """

    def __init__(self, config):
        """
        初始化决策控制器

        Args:
            config: Config 实例
                - DECISION_USE_LLM: 是否启用 LLM（默认 True）
                - DECISION_LLM_API_KEY: API 密钥
                - DECISION_FALLBACK_RULES: 自定义规则
        """
        self._config = config

        # 是否启用 LLM
        self._use_llm = getattr(config, 'DECISION_USE_LLM', True)

        # 初始化规则引擎（始终可用）
        self._rule_engine = RuleEngine(config)

        # 初始化 LLM 引擎（可选）
        self._llm_engine = None
        if self._use_llm:
            try:
                self._llm_engine = LLMEngine(config)
                if not self._llm_engine.is_ready():
                    logger.warning("LLM 引擎未就绪（缺少 API Key），将使用规则引擎")
                    self._llm_engine = None
            except Exception as e:
                logger.warning(f"LLM 引擎初始化失败: {e}，将使用规则引擎")
                self._llm_engine = None

        logger.info(f"DecisionController 初始化完成 (LLM: {'启用' if self._llm_engine else '禁用'})")

    def decide(self, user_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据用户状态生成动作指令

        优先使用 LLM，失败时降级到规则引擎

        Args:
            user_state: Fusion.get_user_state() 返回的状态字典

        Returns:
            动作指令列表
        """
        # 优先使用 LLM
        if self._llm_engine and self._llm_engine.is_ready():
            try:
                actions = self._llm_engine.decide(user_state)
                if actions:
                    return actions
                else:
                    logger.debug("LLM 决策无输出，使用规则引擎")
            except Exception as e:
                logger.warning(f"LLM 决策异常: {e}，降级到规则引擎")

        # 降级到规则引擎
        return self._rule_engine.decide(user_state)

    def is_ready(self) -> bool:
        """返回决策引擎是否就绪（规则引擎始终就绪）"""
        return True