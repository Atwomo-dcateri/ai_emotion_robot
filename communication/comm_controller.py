"""
模块名称：comm_controller.py
功能描述：通信控制器，整合 SerialComm 和协议层，对外提供 CommunicationInterface
依赖：serial_comm, protocol
"""

import logging
import threading
from typing import Dict, Any, Optional, Callable

from communication.base import CommunicationInterface
from communication.serial_comm import SerialComm
from communication.simulator import STM32Simulator
from communication.protocol import (
    pack_oled_emotion, pack_oled_text, pack_oled_clear,
    pack_servo_move, pack_query_sensor,
    unpack_frame, unpack_health_data, unpack_sensor_status,
    TYPE_HEARTBEAT, TYPE_SENSOR_STATUS, TYPE_ACK
)

logger = logging.getLogger(__name__)


class CommController(CommunicationInterface):
    """
    通信控制器

    职责：
        - SIMULATION_MODE=True  时使用 STM32Simulator（调试用）
        - SIMULATION_MODE=False 时使用 SerialComm（真实硬件）
        - 统一对外提供 send_oled_emotion / send_servo_move 等接口
        - 后台解析接收帧，分发健康数据/传感器状态回调
    """

    def __init__(self, config):
        self._config = config
        self._running = False

        # 健康数据回调
        self._health_callback = None
        self._sensor_status_callback = None

        # 接收帧解析线程
        self._parse_thread = None
        self._latest_health = None

        simulation_mode = getattr(config, 'COMM_SIMULATION_MODE', False)

        if simulation_mode:
            logger.info("CommController: 使用 STM32Simulator 模式")
            self._simulator = STM32Simulator()
            self._serial = None
            self._simulator.on_frame(self._on_received_frame)
        else:
            logger.info("CommController: 使用 SerialComm 模式")
            self._serial = SerialComm(
                port=getattr(config, 'COMM_SERIAL_PORT', '/dev/ttyS0'),
                baudrate=getattr(config, 'COMM_BAUDRATE', 115200),
                timeout=getattr(config, 'COMM_TIMEOUT', 0.1),
                reconnect_interval=getattr(config, 'COMM_RECONNECT_INTERVAL', 3.0)
            )
            self._simulator = None
            self._serial.on_frame(self._on_received_frame)

    def start(self) -> bool:
        """启动通信服务"""
        if self._running:
            logger.warning("通信服务已在运行")
            return True

        self._running = True

        if self._simulator:
            self._simulator.start()
        elif self._serial:
            self._serial.start()

        # 启动帧解析线程
        self._parse_thread = threading.Thread(target=self._parse_loop, daemon=True)
        self._parse_thread.start()

        logger.info("CommController 启动成功")
        return True

    def stop(self) -> None:
        """停止通信服务"""
        self._running = False

        if self._parse_thread:
            self._parse_thread.join(timeout=2.0)

        if self._simulator:
            self._simulator.stop()
        if self._serial:
            self._serial.stop()

        logger.info("CommController 已停止")

    def _on_received_frame(self, frame: bytes) -> None:
        """收到原始帧回调（由 SerialComm 或 Simulator 触发）"""
        result = unpack_frame(frame)
        if result is None:
            return

        frame_type, data = result

        if frame_type == TYPE_HEARTBEAT:
            health = unpack_health_data(data)
            if health:
                self._latest_health = health
                if self._health_callback:
                    try:
                        self._health_callback(health)
                    except Exception as e:
                        logger.error(f"健康数据回调异常: {e}")

        elif frame_type == TYPE_SENSOR_STATUS:
            status = unpack_sensor_status(data)
            if status and self._sensor_status_callback:
                try:
                    self._sensor_status_callback(status)
                except Exception as e:
                    logger.error(f"传感器状态回调异常: {e}")

        elif frame_type == TYPE_ACK:
            logger.debug("收到 ACK")

    def _parse_loop(self):
        """后台解析循环（预留，实际解析在回调中完成）"""
        while self._running:
            threading.Event().wait(0.1)

    # ========== 发送接口 ==========

    def send_oled_emotion(self, emotion: str, confidence: float) -> bool:
        """
        发送 OLED 表情指令

        Args:
            emotion: 表情名称（中文）
            confidence: 置信度 0-100

        Returns:
            是否成功放入发送队列
        """
        try:
            frame = pack_oled_emotion(emotion, confidence)
            return self._send_frame(frame)
        except Exception as e:
            logger.error(f"发送 OLED 表情失败: {e}")
            return False

    def send_oled_text(self, text: str, x: int = 0, y: int = 0) -> bool:
        """
        发送 OLED 文本指令

        Args:
            text: 文本内容
            x: X 坐标
            y: Y 坐标

        Returns:
            是否成功放入发送队列
        """
        try:
            frame = pack_oled_text(text, x, y)
            return self._send_frame(frame)
        except Exception as e:
            logger.error(f"发送 OLED 文本失败: {e}")
            return False

    def send_oled_clear(self) -> bool:
        """
        发送 OLED 清屏指令

        Returns:
            是否成功放入发送队列
        """
        try:
            frame = pack_oled_clear()
            return self._send_frame(frame)
        except Exception as e:
            logger.error(f"发送 OLED 清屏失败: {e}")
            return False

    def send_servo_move(self, servo_id: int, angle: int, speed: int = 5) -> bool:
        """
        发送舵机控制指令

        Args:
            servo_id: 0=点头舵机, 1=摇头舵机
            angle: 目标角度 0-180
            speed: 速度 1-10

        Returns:
            是否成功放入发送队列
        """
        try:
            frame = pack_servo_move(servo_id, angle, speed)
            return self._send_frame(frame)
        except Exception as e:
            logger.error(f"发送舵机指令失败: {e}")
            return False

    def query_sensor(self) -> bool:
        """
        主动请求传感器数据

        Returns:
            是否成功放入发送队列
        """
        try:
            frame = pack_query_sensor()
            return self._send_frame(frame)
        except Exception as e:
            logger.error(f"查询传感器失败: {e}")
            return False

    def _send_frame(self, frame: bytes) -> bool:
        """统一发送帧"""
        if self._simulator:
            self._simulator.send_frame(frame)
            return True
        elif self._serial:
            return self._serial.send_frame(frame)
        return False

    # ========== 查询接口 ==========

    def get_health_data(self) -> Optional[Dict[str, Any]]:
        """获取最新健康数据"""
        return self._latest_health.copy() if self._latest_health else None

    def is_connected(self) -> bool:
        """STM32 是否连接"""
        if self._simulator:
            return True
        if self._serial:
            return self._serial.is_connected()
        return False

    # ========== 回调注册 ==========

    def on_health_data(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """注册健康数据回调"""
        self._health_callback = callback

    def on_sensor_status(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """注册传感器状态回调"""
        self._sensor_status_callback = callback
