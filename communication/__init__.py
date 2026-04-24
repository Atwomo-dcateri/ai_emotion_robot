"""
模块名称：communication
功能描述：通信模块，与 STM32 进行串口通信
"""

from communication.base import CommunicationInterface
from communication.comm_controller import CommController
from communication.protocol import (
    TYPE_HEARTBEAT, TYPE_SENSOR_STATUS, TYPE_ACK, TYPE_NAK,
    TYPE_OLED, TYPE_SERVO, TYPE_QUERY_SENSOR, TYPE_CONFIG,
    pack_frame, unpack_frame,
    pack_oled_emotion, pack_oled_text, pack_oled_clear,
    pack_servo_move, pack_query_sensor,
    unpack_health_data, unpack_sensor_status
)

__all__ = [
    'CommunicationInterface',
    'CommController',
    'TYPE_HEARTBEAT',
    'TYPE_SENSOR_STATUS',
    'TYPE_ACK',
    'TYPE_NAK',
    'TYPE_OLED',
    'TYPE_SERVO',
    'TYPE_QUERY_SENSOR',
    'TYPE_CONFIG',
    'pack_frame',
    'unpack_frame',
    'pack_oled_emotion',
    'pack_oled_text',
    'pack_oled_clear',
    'pack_servo_move',
    'pack_query_sensor',
    'unpack_health_data',
    'unpack_sensor_status',
]