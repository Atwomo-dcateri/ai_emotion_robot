"""
模块名称：audio
功能描述：语音识别与合成模块
"""

from audio.audio_controller import AudioController, AudioState
from audio.base import SpeechRecognitionInterface, SpeechSynthesisInterface
from audio.speech_recognition import create_speech_recognition
from audio.speech_synthesis import create_speech_synthesis

__all__ = [
    'AudioController',
    'AudioState',
    'SpeechRecognitionInterface',
    'SpeechSynthesisInterface',
    'create_speech_recognition',
    'create_speech_synthesis',
]