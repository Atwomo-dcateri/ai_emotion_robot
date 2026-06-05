"""
模块名称：vision.py
功能描述：真实摄像头人脸情绪识别模块
依赖：opencv-python, numpy
"""

import threading
import queue
import time
import logging
from typing import Optional, Dict, Any

import cv2

from vision.base import VisionInterface
from vision.face_analyzer import FaceAnalyzer

logger = logging.getLogger(__name__)


class VisionModule(VisionInterface):
    """
    视觉模块：真实摄像头人脸检测与表情分析
    后台线程持续检测，外部通过 get_emotion() 获取最新结果
    """

    def __init__(self, config):
        """
        Args:
            config: Config 类实例
        """
        self.config = config

        # 摄像头配置
        self.camera_id = getattr(config, 'CAMERA_ID', 0)
        self.frame_width = getattr(config, 'CAMERA_WIDTH', 640)
        self.frame_height = getattr(config, 'CAMERA_HEIGHT', 480)
        self.analysis_interval = getattr(config, 'VISION_ANALYSIS_INTERVAL', 0.5)

        # 线程间通信队列
        self._frame_queue = queue.Queue(maxsize=2)
        self._result_queue = queue.Queue(maxsize=2)

        # 控制标志
        self._running = False
        self._threads = []

        # 最新结果缓存
        self._latest_result = None
        self._lock = threading.Lock()

        # 表情分析器
        self._analyzer = FaceAnalyzer(config)

        logger.info("VisionModule 初始化完成")

    def start(self) -> bool:
        """启动视觉服务"""
        if self._running:
            logger.warning("视觉服务已在运行")
            return True

        self._running = True

        # 摄像头读取线程
        t_read = threading.Thread(target=self._camera_reader, daemon=True)
        t_read.start()
        self._threads.append(t_read)

        # 人脸检测线程
        t_detect = threading.Thread(target=self._face_detector, daemon=True)
        t_detect.start()
        self._threads.append(t_detect)

        # 等待摄像头启动
        time.sleep(1.0)

        logger.info("视觉服务启动成功")
        return True

    def stop(self) -> None:
        """停止视觉服务"""
        self._running = False

        for t in self._threads:
            t.join(timeout=2.0)

        self._threads.clear()
        logger.info("视觉服务已停止")

    def close(self) -> None:
        """关闭服务（stop 别名）"""
        self.stop()

    def is_running(self) -> bool:
        """返回服务是否正在运行"""
        return self._running

    def _camera_reader(self):
        """
        摄像头读取线程：从摄像头读取帧，放入队列
        """
        logger.info("正在打开摄像头...")
        # 使用 V4L2 后端（USB 摄像头兼容性更好）
        cap = cv2.VideoCapture(self.camera_id, cv2.CAP_V4L2)

        if not cap.isOpened():
            logger.error("无法打开摄像头")
            self._running = False
            return

        # 设置分辨率
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # 优化摄像头画质（对 USB 摄像头有效）
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 关闭自动曝光

        logger.info(f"摄像头已打开: {self.frame_width}x{self.frame_height}")

        while self._running:
            ret, frame = cap.read()
            if ret and frame is not None:
                # 队列满时丢弃旧帧
                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                self._frame_queue.put(frame)
            else:
                time.sleep(0.01)

        cap.release()
        logger.info("摄像头读取线程已停止")

    def _face_detector(self):
        """
        人脸检测线程：从帧队列取帧，进行检测，结果放入队列
        """
        logger.info("人脸检测线程已启动")
        last_analysis_time = 0

        while self._running:
            try:
                frame = self._frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # 控制分析频率
            now = time.time()
            if now - last_analysis_time < self.analysis_interval:
                continue

            try:
                # 检测人脸
                faces = self._analyzer.detect_faces(frame)

                if faces:
                    # 使用第一个检测到的人脸
                    face_rect = faces[0]
                    emotion_result = self._analyzer.analyze_emotion(frame, face_rect)

                    result_data = {
                        'emotion': emotion_result['emotion'],
                        'emotion_cn': emotion_result['emotion_cn'],
                        'confidence': emotion_result['confidence'],
                        'face_count': len(faces),
                        'region': face_rect
                    }
                else:
                    result_data = None

                last_analysis_time = now

                # 放入结果队列
                if self._result_queue.full():
                    try:
                        self._result_queue.get_nowait()
                    except queue.Empty:
                        pass
                self._result_queue.put(result_data)

                # 更新缓存
                with self._lock:
                    self._latest_result = result_data

            except Exception as e:
                logger.debug(f"检测异常: {e}")

        logger.info("人脸检测线程已停止")

    def get_emotion(self) -> Optional[Dict[str, Any]]:
        """
        非阻塞获取情绪检测结果

        Returns:
            {
                'emotion': str,      # 英文标签
                'emotion_cn': str,   # 中文标签
                'confidence': float, # 置信度
                'face_count': int,   # 人脸数量
                'region': tuple      # (x, y, w, h)
            }
            未检测到人脸返回 None
        """
        # 刷新队列到缓存
        try:
            while not self._result_queue.empty():
                with self._lock:
                    self._latest_result = self._result_queue.get_nowait()
        except queue.Empty:
            pass

        # 返回缓存副本
        with self._lock:
            if self._latest_result is not None:
                return self._latest_result.copy()
            return None