# config.py
import os

class Config:
    # ========== 视觉配置 ==========
    CAMERA_ID = 0                    # 摄像头设备 ID
    CAMERA_WIDTH = 640               # 采集宽度
    CAMERA_HEIGHT = 480              # 采集高度
    CAMERA_FPS = 30                  # 目标帧率

    VISION_ENABLED = True            # 是否启用视觉模块
    VISION_ANALYSIS_INTERVAL = 0.5   # 分析间隔（秒）

    # 表情分析阈值（可调节）
    VISION_EYE_SIZE_THRESHOLD = 0.025      # 大眼睛/小眼睛阈值
    VISION_MOUTH_SIZE_THRESHOLD = 0.04     # 大嘴巴阈值
    VISION_MOUTH_POSITION_THRESHOLD = 0.6  # 嘴巴位置阈值（低=高，高=低）
    VISION_EYE_SIZE_SMALL = 0.02           # 小眼睛阈值
    VISION_MOUTH_SIZE_SMALL = 0.02         # 小嘴巴阈值

    # ========== 语音配置 ==========
    # STT 配置
    AUDIO_STT_ENGINE = "vosk"  # vosk / none（none 时跳过语音输入）
    AUDIO_VOSK_MODEL_PATH = "models/vosk-model-small-cn-0.22"
    AUDIO_WAKE_WORDS = ["你好", "小机器人"]
    AUDIO_LISTEN_TIMEOUT = 5.0
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_DEVICE_INDEX = 2  # USB 麦克风设备索引，None 为默认设备

    # TTS 配置
    AUDIO_TTS_ENGINE = "espeak"  # espeak / none
    AUDIO_TTS_RATE = 180
    AUDIO_TTS_VOLUME = 1.0
    AUDIO_TTS_VOICE = 'zh'

        # ========== OLED 配置 ==========
    OLED_ENABLED = True
    OLED_I2C_ADDRESS = 0x3C
    OLED_I2C_PORT = 1
    OLED_DEVICE_TYPE = 'ssd1106'  # ssd1306 或 sh1106
    OLED_WIDTH = 128
    OLED_HEIGHT = 64
    # ========== Fusion 配置 ==========
    FUSION_CONSUME_SPEECH = True           # 是否自动消费语音输入
    FUSION_TIMESTAMP_FORMAT = '%H:%M:%S'   # 时间格式化（用于日志）
    
    # ========== Decision 配置 ==========
    DECISION_USE_LLM = True                      # 是否启用 LLM
    DECISION_LLM_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')  # API 密钥
    DECISION_LLM_API_URL = 'https://api.deepseek.com/v1/chat/completions'
    DECISION_LLM_MODEL = 'deepseek-chat'
    DECISION_LLM_TIMEOUT = 15                    # 请求超时（秒）
    DECISION_FALLBACK_RULES = None               # 自定义规则（可选）

    # ========== 日志配置 ==========
    LOG_LEVEL = 'INFO'
    LOG_DIR = 'logs'

    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        cls.DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
        cls.LLM_SIMULATION_MODE = not bool(cls.DEEPSEEK_API_KEY)
        return cls