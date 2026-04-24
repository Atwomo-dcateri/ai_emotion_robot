"""
模块名称：protocol.py
功能描述：帧协议编解码（帧打包/解析/校验）
依赖：struct, crcmod / 内置 CRC
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


def calc_crc(data: bytes) -> int:
    """
    计算 CRC16-CCITT 校验值

    Args:
        data: 待校验数据

    Returns:
        16 位 CRC 值
    """
    # 使用 CRC-16/CCITT-FALSE
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
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
    # 编码：CMD(1) + CONFIDENCE(1) + EMOTION_NAME(UTF-8)
    confidence_byte = max(0, min(255, int(confidence)))
    emotion_bytes = emotion.encode('utf-8')[:MAX_DATA_LEN - 2]

    data = struct.pack('>BB', OLED_CMD_EMOTION, confidence_byte) + emotion_bytes
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
    text_bytes = text.encode('utf-8')[:MAX_DATA_LEN - 3]

    data = struct.pack('>BBB', OLED_CMD_TEXT, x_byte, y_byte) + text_bytes
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
