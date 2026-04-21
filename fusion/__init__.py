"""
模块名称：fusion
功能描述：多模态数据融合模块，汇集 Vision 和 Speech 输出
"""

from fusion.base import FusionInterface
from fusion.fusion import FusionModule

__all__ = [
    'FusionInterface',
    'FusionModule',
]