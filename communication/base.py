"""
模块名称：base.py
功能描述：通信模块抽象接口定义
依赖：无
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable


class CommunicationInterface(ABC):
    """通信模块抽象接口"""

    @abstractmethod
    def start(self) -> bool:
        """启动通信服务"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止通信服务"""
        pass

    @abstractmethod
    def send_oled_emotion(self, emotion: str, confidence: float) -> bool:
        """发送 OLED 表情指令"""
        pass

    @abstractmethod
    def send_oled_text(self, text: str, x: int = 0, y: int = 0) -> bool:
        """发送 OLED 文本指令"""
        pass

    @abstractmethod
    def send_oled_clear(self) -> bool:
        """发送 OLED 清屏指令"""
        pass

    @abstractmethod
    def send_servo_move(self, servo_id: int, angle: int, speed: int = 5) -> bool:
        """发送舵机控制指令"""
        pass

    @abstractmethod
    def query_sensor(self) -> bool:
        """主动请求传感器数据"""
        pass

    @abstractmethod
    def get_health_data(self) -> Optional[Dict[str, Any]]:
        """获取最新健康数据"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """STM32 是否连接"""
        pass

    @abstractmethod
    def on_health_data(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """注册健康数据回调"""
        pass

    @abstractmethod
    def on_sensor_status(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """注册传感器状态回调"""
        pass

    