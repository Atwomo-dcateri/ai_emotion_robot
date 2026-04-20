"""
模块名称：audio
功能描述：语音识别与合成模块
"""

from audio.audio_controller import AudioController, AudioState
from audio.base import SpeechRecognitionInterface, SpeechSynthesisInterface

__all__ = [
    'AudioController',
    'AudioState',
    'SpeechRecognitionInterface',
    'SpeechSynthesisInterface',
]