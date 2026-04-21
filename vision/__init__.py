"""
模块名称：vision
功能描述：视觉识别模块，提供人脸检测与情绪分析能力
"""

from vision.base import VisionInterface
from vision.vision import VisionModule

__all__ = [
    'VisionInterface',
    'VisionModule',
]