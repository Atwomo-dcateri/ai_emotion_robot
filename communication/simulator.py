"""
模块名称：simulator.py
功能描述：STM32 模拟器（无硬件调试用）
依赖：threading, time
"""

import time
import logging
import threading
import random
from typing import Optional, Callable

from communication.protocol import (
    pack_frame, unpack_frame,
    TYPE_HEARTBEAT, TYPE_ACK, TYPE_OLED, TYPE_SERVO, TYPE_QUERY_SENSOR,
    unpack_health_data, unpack_sensor_status
)

logger = logging.getLogger(__name__)


class STM32Simulator:
    """
    STM32 模拟器

    模拟行为：
        - 自动应答所有请求帧
        - 定期产生模拟健康数据
        - 打印接收到的控制帧（用于调试）
    """

    def __init__(self):
        self._running = False
        self._frame_callback = None
        self._simulate_thread = None

        # 模拟数据
        self._heart_rate = 75
        self._oxygen = 98

        logger.info("STM32Simulator 初始化完成")

    def start(self) -> bool:
        """启动模拟器"""
        if self._running:
            return True

        self._running = True
        self._simulate_thread = threading.Thread(target=self._simulate_loop, daemon=True)
        self._simulate_thread.start()

        logger.info("STM32Simulator 已启动")
        return True

    def stop(self) -> None:
        """停止模拟器"""
        self._running = False
        if self._simulate_thread:
            self._simulate_thread.join(timeout=1.0)
        logger.info("STM32Simulator 已停止")

    def send_frame(self, frame: bytes) -> None:
        """
        发送帧给模拟器（模拟 STM32 接收）

        Args:
            frame: 完整帧数据
        """
        result = unpack_frame(frame)
        if result is None:
            logger.warning(f"模拟器收到无效帧: {frame.hex()}")
            return

        frame_type, data = result

        if frame_type == TYPE_OLED:
            self._handle_oled(data)
            self._send_ack()
        elif frame_type == TYPE_SERVO:
            self._handle_servo(data)
            self._send_ack()
        elif frame_type == TYPE_QUERY_SENSOR:
            self._send_health_data()
        else:
            logger.debug(f"模拟器收到未知类型: {hex(frame_type)}")

    def on_frame(self, callback: Callable[[bytes], None]) -> None:
        """注册帧接收回调（对外发送）"""
        self._frame_callback = callback

    def _send_frame(self, frame_type: int, data: bytes) -> None:
        """发送帧（通过回调）"""
        if self._frame_callback:
            frame = pack_frame(frame_type, data)
            self._frame_callback(frame)

    def _send_ack(self) -> None:
        """发送应答"""
        self._send_frame(TYPE_ACK, b'\x00')

    def _send_health_data(self) -> None:
        """发送健康数据"""
        # 模拟数据变化
        self._heart_rate = 70 + random.randint(-5, 10)
        self._oxygen = 95 + random.randint(0, 5)

        # 限制范围
        self._heart_rate = max(40, min(120, self._heart_rate))
        self._oxygen = max(85, min(100, self._oxygen))

        data = bytes([
            self._heart_rate,
            1,  # HR_OK
            self._oxygen,
            1   # OXYGEN_OK
        ])
        self._send_frame(TYPE_HEARTBEAT, data)
        logger.debug(f"模拟器发送健康数据: HR={self._heart_rate}, O2={self._oxygen}")

    def _send_sensor_status(self, status: int, error_code: int = 0) -> None:
        """发送传感器状态"""
        data = bytes([status, error_code])
        self._send_frame(TYPE_SENSOR_STATUS, data)

    def _handle_oled(self, data: bytes) -> None:
        """处理 OLED 指令"""
        if len(data) < 1:
            return

        cmd = data[0]
        if cmd == 0x00:  # 表情
            confidence = data[1] if len(data) > 1 else 75
            emotion = data[2:].decode('utf-8', errors='ignore')
            logger.info(f"[模拟器] OLED 显示表情: {emotion} (置信度 {confidence}%)")
        elif cmd == 0x01:  # 文本
            x = data[1] if len(data) > 1 else 0
            y = data[2] if len(data) > 2 else 0
            text = data[3:].decode('utf-8', errors='ignore')
            logger.info(f"[模拟器] OLED 显示文本: '{text}' @ ({x}, {y})")
        elif cmd == 0x02:  # 清屏
            logger.info(f"[模拟器] OLED 清屏")

    def _handle_servo(self, data: bytes) -> None:
        """处理舵机指令"""
        if len(data) >= 3:
            servo_id = data[0]
            angle = data[1]
            speed = data[2]
            servo_name = "点头" if servo_id == 0 else "摇头"
            logger.info(f"[模拟器] 舵机 {servo_name} 转到 {angle}° (速度 {speed})")

    def _simulate_loop(self):
        """模拟循环：定期发送健康数据"""
        while self._running:
            time.sleep(1.0)
            if self._frame_callback:
                self._send_health_data()

