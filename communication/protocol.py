"""
模块名称：protocol.py
功能描述：帧协议编解码（帧打包/解析/校验）
依赖：struct
"""

import struct
from typing import Optional, Tuple

# ========== 帧格式常量 ==========
FRAME_HEAD = b'\xAA\x55'
FRAME_TAIL = b'\xBB'
MAX_DATA_LEN = 250

# 帧头长度 + 类型(1) + 数据长度(1) + CRC(2) + 帧尾(1)
FRAME_MIN_LEN = 2 + 1 + 1 + 2 + 1  # 7 bytes

# ========== 方向：STM32 → 树莓派 ==========
TYPE_HEARTBEAT = 0x01      # 心率+血氧数据上报
TYPE_SENSOR_STATUS = 0x03  # 传感器状态
TYPE_ACK = 0x04            # 应答
TYPE_NAK = 0x05            # 否定应答

# ========== 方向：树莓派 → STM32 ==========
TYPE_OLED = 0x10           # OLED 控制
TYPE_SERVO = 0x11          # 舵机控制
TYPE_QUERY_SENSOR = 0x12   # 查询传感器
TYPE_CONFIG = 0x13         # 参数配置

# ========== OLED 子命令 ==========
OLED_CMD_EMOTION = 0x00    # 显示表情
OLED_CMD_TEXT = 0x01       # 显示文本
OLED_CMD_CLEAR = 0x02      # 清屏


# ========== CRC16-CCITT 查表法（与 STM32 实现完全一致） ==========
_CRC16_TABLE = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
    0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
    0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
    0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
    0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
    0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
    0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
    0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
    0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0,
]


def calc_crc(data: bytes) -> int:
    """
    计算 CRC16-CCITT 校验值（查表法，与 STM32 实现完全一致）

    Args:
        data: 待校验数据

    Returns:
        16 位 CRC 值
    """
    crc = 0xFFFF
    for b in data:
        crc = ((crc << 8) ^ _CRC16_TABLE[((crc >> 8) ^ b) & 0xFF]) & 0xFFFF
    return crc


def pack_frame(frame_type: int, data: bytes) -> bytes:
    """
    将类型和数据打包为完整帧

    帧格式：
        HEAD(2) + TYPE(1) + LEN(1) + DATA(N) + CRC(2) + TAIL(1)

    Args:
        frame_type: 帧类型
        data: 数据负载

    Returns:
        完整的二进制帧
    """
    if len(data) > MAX_DATA_LEN:
        raise ValueError(f"数据过长: {len(data)} > {MAX_DATA_LEN}")

    # 构建帧体（不含头尾）
    body = struct.pack('>BB', frame_type, len(data)) + data
    crc = calc_crc(body)

    # 完整帧
    frame = FRAME_HEAD + body + struct.pack('>H', crc) + FRAME_TAIL
    return frame


def unpack_frame(frame: bytes) -> Optional[Tuple[int, bytes]]:
    """
    解析二进制帧

    Args:
        frame: 完整帧数据

    Returns:
        (frame_type, data) 或 None（校验失败）
    """
    frame_len = len(frame)

    # 最小长度检查
    if frame_len < FRAME_MIN_LEN:
        return None

    # 检查帧头
    if frame[:2] != FRAME_HEAD:
        return None

    # 检查帧尾
    if frame[-1:] != FRAME_TAIL:
        return None

    # 解析类型和长度
    frame_type = frame[2]
    data_len = frame[3]

    # 检查长度一致性
    expected_len = 2 + 1 + 1 + data_len + 2 + 1
    if frame_len != expected_len:
        return None

    # 提取数据和 CRC
    data = frame[4:4 + data_len]
    received_crc = struct.unpack('>H', frame[4 + data_len:6 + data_len])[0]

    # 验证 CRC
    body = frame[2:4 + data_len]  # TYPE + LEN + DATA
    if calc_crc(body) != received_crc:
        return None

    return frame_type, data


def pack_oled_emotion(emotion: str, confidence: float) -> bytes:
    """
    打包 OLED 表情指令

    Args:
        emotion: 表情名称（中文）
        confidence: 置信度 0-100

    Returns:
        二进制帧
    """
    # 编码：CMD(1) + CONFIDENCE(1) + LEN(1) + STRING(N)  （STM32 侧要求带长度）
    confidence_byte = max(0, min(255, int(confidence)))
    emotion_bytes = emotion.encode('utf-8')[:MAX_DATA_LEN - 3]
    name_len = len(emotion_bytes)

    data = struct.pack('>BBB', OLED_CMD_EMOTION, confidence_byte, name_len) + emotion_bytes
    return pack_frame(TYPE_OLED, data)


def pack_oled_text(text: str, x: int = 0, y: int = 0) -> bytes:
    """
    打包 OLED 文本指令

    Args:
        text: 文本内容
        x: X 坐标（0-127）
        y: Y 坐标（0-63）

    Returns:
        二进制帧
    """
    x_byte = max(0, min(255, x))
    y_byte = max(0, min(255, y))
    text_bytes = text.encode('utf-8')[:MAX_DATA_LEN - 4]
    text_len = len(text_bytes)

    data = struct.pack('>BBBB', OLED_CMD_TEXT, x_byte, y_byte, text_len) + text_bytes
    return pack_frame(TYPE_OLED, data)


def pack_oled_clear() -> bytes:
    """打包 OLED 清屏指令"""
    data = struct.pack('>B', OLED_CMD_CLEAR)
    return pack_frame(TYPE_OLED, data)


def pack_servo_move(servo_id: int, angle: int, speed: int = 5) -> bytes:
    """
    打包舵机控制指令

    Args:
        servo_id: 0=点头舵机, 1=摇头舵机
        angle: 目标角度 0-180
        speed: 速度 1-10

    Returns:
        二进制帧
    """
    servo_byte = max(0, min(255, servo_id))
    angle_byte = max(0, min(180, angle))
    speed_byte = max(1, min(10, speed))

    data = struct.pack('>BBB', servo_byte, angle_byte, speed_byte)
    return pack_frame(TYPE_SERVO, data)


def pack_query_sensor() -> bytes:
    """打包查询传感器指令"""
    return pack_frame(TYPE_QUERY_SENSOR, b'')


def unpack_health_data(data: bytes) -> Optional[dict]:
    """
    解析健康数据帧

    DATA = HR_VAL(uint8) + HR_OK(uint8) + OXYGEN_VAL(uint8) + OXYGEN_OK(uint8)

    Returns:
        {'heart_rate': int, 'heart_rate_valid': bool, 'oxygen': int, 'oxygen_valid': bool}
    """
    if len(data) != 4:
        return None

    hr_val, hr_ok, oxygen_val, oxygen_ok = struct.unpack('>BBBB', data)

    return {
        'heart_rate': hr_val,
        'heart_rate_valid': hr_ok == 1,
        'oxygen': oxygen_val,
        'oxygen_valid': oxygen_ok == 1
    }


def unpack_sensor_status(data: bytes) -> Optional[dict]:
    """
    解析传感器状态帧

    DATA = STATUS(uint8) + ERR_CODE(uint8)

    Returns:
        {'status': str, 'error_code': int}
    """
    if len(data) != 2:
        return None

    status_code, err_code = struct.unpack('>BB', data)

    status_map = {
        0: 'offline',
        1: 'online',
        2: 'error'
    }

    return {
        'status': status_map.get(status_code, 'unknown'),
        'error_code': err_code
    }
