# config.py
import os

class Config:
    # ========== 硬件配置 ==========
    OLED_ENABLED = True
    OLED_I2C_ADDRESS = 0x3C
    OLED_I2C_PORT = 1
    OLED_DEVICE_TYPE = 'ssd1306'

    CAMERA_ID = 0
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480

    FACE_DETECTION_INTERVAL = 0.5

    # ========== 语音配置 ==========
    # STT 配置
    AUDIO_STT_ENGINE = "vosk"  # vosk / google / none
    AUDIO_VOSK_MODEL_PATH = "models/vosk-model-small-cn-0.22"
    AUDIO_WAKE_WORDS = ["你好", "小机器人"]
    AUDIO_LISTEN_TIMEOUT = 5.0
    AUDIO_SAMPLE_RATE = 16000

    # TTS 配置
    AUDIO_TTS_ENGINE = "pyttsx3"  # pyttsx3 / gtts / none
    AUDIO_TTS_RATE = 180
    AUDIO_TTS_VOLUME = 1.0

    # ========== API 配置 ==========
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    LLM_SIMULATION_MODE = not bool(DEEPSEEK_API_KEY)

    # ========== 日志配置 ==========
    LOG_LEVEL = 'INFO'
    LOG_DIR = 'logs'

    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        cls.DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
        cls.LLM_SIMULATION_MODE = not bool(cls.DEEPSEEK_API_KEY)
        return cls
    
