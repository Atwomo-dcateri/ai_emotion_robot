"""
模块名称：serial_comm.py
功能描述：串口管理（后台读写线程、队列、粘包处理）
依赖：pyserial, threading, queue
"""

import time
import logging
import threading
import queue
import serial
import serial.tools.list_ports

from communication.protocol import FRAME_HEAD, FRAME_TAIL, MAX_DATA_LEN, FRAME_MIN_LEN, unpack_frame

logger = logging.getLogger(__name__)


class SerialComm:
    """
    串口通信管理器

    职责：
        - 管理串口设备打开/关闭
        - 后台线程接收数据，处理粘包
        - 后台线程发送数据，从队列取帧
        - 连接状态检测与自动重连
    """

    def __init__(self, port: str = '/dev/ttyAMA0', baudrate: int = 115200,
                 timeout: float = 0.1, reconnect_interval: float = 3.0):
        """
        Args:
            port: 串口设备路径
            baudrate: 波特率
            timeout: 读取超时（秒）
            reconnect_interval: 断线重连间隔（秒）
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.reconnect_interval = reconnect_interval

        self._serial: serial.Serial = None
        self._running = False
        self._connected = False

        # 发送队列
        self._send_queue = queue.Queue(maxsize=50)

        # 线程
        self._read_thread: threading.Thread = None
        self._write_thread: threading.Thread = None
        self._reconnect_thread: threading.Thread = None

        # 回调
        self._frame_callback = None
        self._connected_callback = None

        # 锁
        self._lock = threading.Lock()

        logger.info(f"SerialComm 初始化: {port} @ {baudrate}")

    def start(self) -> bool:
        """启动串口服务"""
        if self._running:
            logger.warning("串口服务已在运行")
            return True

        self._running = True

        # 尝试打开串口
        if not self._open_serial():
            logger.warning(f"无法打开串口 {self.port}，将进入重连模式")
            self._start_reconnect_thread()

        # 启动读写线程
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._write_thread = threading.Thread(target=self._write_loop, daemon=True)
        self._read_thread.start()
        self._write_thread.start()

        logger.info("串口服务已启动")
        return True

    def stop(self) -> None:
        """停止串口服务"""
        self._running = False

        if self._read_thread:
            self._read_thread.join(timeout=2.0)
        if self._write_thread:
            self._write_thread.join(timeout=2.0)
        if self._reconnect_thread:
            self._reconnect_thread.join(timeout=2.0)

        self._close_serial()
        logger.info("串口服务已停止")

    def _open_serial(self) -> bool:
        """打开串口"""
        try:
            with self._lock:
                self._serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=self.timeout
                )
                self._connected = True
                logger.info(f"串口已打开: {self.port}")
                if self._connected_callback:
                    self._connected_callback(True)
                return True
        except Exception as e:
            logger.error(f"打开串口失败: {e}")
            self._connected = False
            return False

    def _close_serial(self):
        """关闭串口"""
        with self._lock:
            if self._serial:
                try:
                    self._serial.close()
                except:
                    pass
                self._serial = None
            self._connected = False

        if self._connected_callback:
            self._connected_callback(False)

    def _start_reconnect_thread(self):
        """启动重连线程"""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return

        self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()

    def _reconnect_loop(self):
        """重连循环"""
        while self._running:
            if not self._connected:
                logger.info(f"尝试重连 {self.port}...")
                if self._open_serial():
                    logger.info("重连成功")
                    break
                time.sleep(self.reconnect_interval)
            else:
                break

    def _read_loop(self):
        """接收线程：读取串口数据，处理粘包"""
        buffer = b''

        while self._running:
            # 等待串口可用
            while not self._connected and self._running:
                time.sleep(0.1)

            if not self._running:
                break

            with self._lock:
                ser = self._serial

            if not ser:
                time.sleep(0.1)
                continue

            try:
                data = ser.read(256)
                if data:
                    # 用 LEN 字段定位帧边界，避免误判 0xBB
                    frames, buffer = self._extract_frames(buffer + data)
                    for frame in frames:
                        if self._frame_callback:
                            self._frame_callback(frame)
                    # buffer 已被 _extract_frames 修剪，无需额外操作
                else:
                    # 超时无数据，检查连接状态
                    time.sleep(0.01)
            except Exception as e:
                logger.error(f"读取异常: {e}")
                self._close_serial()
                time.sleep(0.1)

    def _extract_frames(self, buffer: bytes) -> tuple:
        """
        基于 LEN 字段提取完整帧（与 STM32 comm_parser.c 逻辑一致）

        先通过 FRAME_HEAD 定位帧头，再读取 LEN 字段计算帧长，
        收齐后通过 unpack_frame 验证 CRC+TAIL，避免 payload 中的 0xBB 误匹配。

        Args:
            buffer: 接收缓冲区

        Returns:
            (frames, remaining): 完整帧列表 + 剩余未处理数据
        """
        frames = []

        while True:
            if len(buffer) < FRAME_MIN_LEN:
                break

            head = buffer.find(FRAME_HEAD)
            if head == -1:
                # 无帧头，保留最后一个字节防止丢 AA
                buffer = buffer[-1:]
                break

            if head > 0:
                # 丢弃帧头前的垃圾数据
                buffer = buffer[head:]
                continue

            # 已对齐帧头，检查能否获取 LEN
            if len(buffer) < 4:
                break  # 等更多数据

            data_len = buffer[3]
            if data_len > MAX_DATA_LEN:
                buffer = buffer[1:]  # 丢弃误匹配的 AA
                continue

            total = 2 + 1 + 1 + data_len + 2 + 1  # HEAD + TYPE + LEN + DATA + CRC + TAIL
            if len(buffer) < total:
                break  # 等更多数据

            candidate = buffer[:total]
            if unpack_frame(candidate) is not None:
                frames.append(candidate)
                buffer = buffer[total:]
            else:
                # CRC/TAIL 校验失败，推进一个字节
                buffer = buffer[1:]

        return frames, buffer

    def _write_loop(self):
        """发送线程：从队列取帧并发送"""
        while self._running:
            try:
                frame = self._send_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # 等待串口可用
            while not self._connected and self._running:
                time.sleep(0.1)

            if not self._running:
                break

            with self._lock:
                ser = self._serial

            if not ser:
                continue

            try:
                ser.write(frame)
                logger.debug(f"发送帧: {frame.hex()[:20]}...")
            except Exception as e:
                logger.error(f"发送失败: {e}")
                self._close_serial()
                # 重放回队列
                try:
                    self._send_queue.put(frame, block=False)
                except queue.Full:
                    pass

    def send_frame(self, frame: bytes) -> bool:
        """
        将帧放入发送队列

        Args:
            frame: 完整帧数据

        Returns:
            是否成功放入队列
        """
        try:
            self._send_queue.put(frame, block=False)
            return True
        except queue.Full:
            logger.warning("发送队列满，丢弃帧")
            return False

    def on_frame(self, callback):
        """注册接收到完整帧时的回调"""
        self._frame_callback = callback

    def on_connected(self, callback):
        """注册连接状态变化回调"""
        self._connected_callback = callback

    def is_connected(self) -> bool:
        """返回连接状态"""
        return self._connected
    

    