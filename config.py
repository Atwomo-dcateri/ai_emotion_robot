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
    AUDIO_STT_ENGINE = "baidu"  # vosk / baidu（离线/在线）
    AUDIO_VOSK_MODEL_PATH = "models/vosk-model-small-cn-0.22"
    AUDIO_WAKE_WORDS = ["你好", "小机器人", "小提琴"]
    AUDIO_LISTEN_TIMEOUT = 5.0
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_DEVICE_INDEX = 1  # USB 麦克风设备索引 (USB PnP Sound Device)

    # 百度 ASR 配置（engine="baidu" 时使用）
    BAIDU_ASR_APP_ID = os.environ.get('BAIDU_ASR_APP_ID', '')
    BAIDU_ASR_API_KEY = os.environ.get('BAIDU_ASR_API_KEY', '')
    BAIDU_ASR_SECRET_KEY = os.environ.get('BAIDU_ASR_SECRET_KEY', '')
    ASR_SILENCE_TIMEOUT = 0.8       # 静音判定超时（秒）
    ASR_MIN_AUDIO_DURATION = 0.5    # 最小录音时长（秒）

    # TTS 配置
    AUDIO_TTS_ENGINE = "espeak"  # espeak / none
    AUDIO_TTS_RATE = 180
    AUDIO_TTS_VOLUME = 1.0
    AUDIO_TTS_VOICE = 'zh'
    AUDIO_TTS_DEVICE = 'plughw:2,0'  # espeak 输出设备（None = 系统默认）

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

    # ========== 通信配置 ==========
    COMM_ENABLED = True                      # 是否启用串口通信
    COMM_SIMULATION_MODE = False             # 是否启用 STM32 模拟器（无硬件调试用）
    COMM_SERIAL_PORT = '/dev/serial0'           # 串口设备路径
    COMM_BAUDRATE = 115200                   # 波特率
    COMM_TIMEOUT = 0.1                       # 读取超时（秒）
    COMM_RECONNECT_INTERVAL = 3.0            # 断线重连间隔
    COMM_HEARTBEAT_INTERVAL = 1.0            # 健康数据上报间隔（由 STM32 控制）
    # ========== 健康告警配置 ==========
    HEART_RATE_HIGH_THRESHOLD = 300   # 心率过高阈值（bpm）
    HEART_RATE_LOW_THRESHOLD = 60      # 心率过低阈值（bpm）
    OXYGEN_LOW_THRESHOLD = 20          # 血氧过低阈值（%）
    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        cls.DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
        cls.LLM_SIMULATION_MODE = not bool(cls.DEEPSEEK_API_KEY)
        return cls