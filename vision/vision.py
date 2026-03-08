print("[vision.py] 开始加载模块")
import sys
print("[vision.py] sys 导入成功")
import io
print("[vision.py] io 导入成功")
# 解决 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import cv2
print("[vision.py] cv2 导入成功")
from deepface import DeepFace
print("[vision.py] deepface 导入成功")
import threading
print("[vision.py] threading 导入成功")

import queue
print("[vision.py] queue 导入成功")
import time
print("[vision.py] time 导入成功")
import logging
print("[vision.py] logging 导入成功")
import os
print("[vision.py] os 导入成功")
from collections import deque
print("[vision.py] collections 导入成功")
# 禁用 TensorFlow 冗余输出
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['DEEPFACE_VERBOSE'] = 'False'
logging.getLogger().setLevel(logging.ERROR)

# 禁用 tqdm 进度条（DeepFace 依赖）
from tqdm import tqdm
from functools import partialmethod
tqdm.__init__ = partialmethod(tqdm.__init__, disable=True)

# 情绪中英文映射（可选）
EMOTION_CN = {
    'angry': '愤怒', 'disgust': '厌恶', 'fear': '恐惧',
    'happy': '开心', 'sad': '悲伤', 'surprise': '惊讶',
    'neutral': '平静'
}


class VisionModule:
    """
    视觉模块：实时摄像头人脸情绪识别
    后台线程持续检测，外部通过 get_emotion() 获取最新结果
    """

    def __init__(self, camera_id=0, analysis_interval=0.5):
        """
        初始化视觉模块
        """
        print(f"[VisionModule] 初始化中... camera_id={camera_id}")
        self.camera_id = camera_id
        self.analysis_interval = analysis_interval
        
        # 线程间通信队列
        self.frame_queue = queue.Queue(maxsize=2)
        self.result_queue = queue.Queue(maxsize=2)
        
        # 控制标志
        self.running = False
        self.threads = []
        
        # 最新结果缓存
        self.latest_result = None
        self.lock = threading.Lock()
        
        print("[VisionModule] 正在启动摄像头...")
        # 启动摄像头和检测线程
        self._start()
        print("[VisionModule] 初始化完成")

    def _start(self):
        """启动后台线程"""
        self.running = True
        # 摄像头读取线程
        t_read = threading.Thread(target=self._camera_reader, daemon=True)
        t_read.start()
        self.threads.append(t_read)

        # 情绪分析线程
        t_analyze = threading.Thread(target=self._emotion_analyzer, daemon=True)
        t_analyze.start()
        self.threads.append(t_analyze)

        # 等待摄像头启动
        time.sleep(1.0)

    def _camera_reader(self):
        """
        摄像头读取线程：只负责从摄像头读取帧，放入队列
        """
        # 强制使用 DirectShow 后端（Windows 稳定）
        cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[VisionModule] 错误：无法打开摄像头")
            self.running = False
            return

        # 设置分辨率（可调节）
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少缓冲，降低延迟

        print("[VisionModule] 摄像头读取线程已启动")

        while self.running:
            ret, frame = cap.read()
            if ret and frame is not None:
                # 如果队列满了，丢弃旧帧以保持实时性
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.frame_queue.put(frame)
            else:
                # 读取失败时短暂休眠
                time.sleep(0.01)

        cap.release()
        print("[VisionModule] 摄像头读取线程已停止")

    def _emotion_analyzer(self):
        """
        情绪分析线程：从帧队列取帧，进行情绪分析，结果放入结果队列
        """
        print("[VisionModule] 情绪分析线程已启动")
        last_analysis_time = 0

        while self.running:
            try:
                # 等待一帧，超时1秒
                frame = self.frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # 控制分析频率
            now = time.time()
            if now - last_analysis_time < self.analysis_interval:
                continue

            try:
                # 缩小图像以加快分析
                small = cv2.resize(frame, (320, 240))

                # 调用 DeepFace 分析
                result = DeepFace.analyze(
                    img_path=small,
                    actions=['emotion'],
                    enforce_detection=False,
                    silent=True
                )

                if result and len(result) > 0:
                    last_analysis_time = now
                    res = result[0]

                    # 提取关键信息
                    emotion = res['dominant_emotion']
                    confidence = res['emotion'][emotion]
                    emotion_cn = EMOTION_CN.get(emotion, emotion)

                    result_data = {
                        'emotion': emotion,           # 英文标签
                        'emotion_cn': emotion_cn,     # 中文标签
                        'confidence': confidence,
                        'all_emotions': res['emotion'],
                        'region': res.get('region', {})
                    }

                    # 放入结果队列
                    if self.result_queue.full():
                        try:
                            self.result_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self.result_queue.put(result_data)

                    # 同时更新最新结果缓存（线程安全）
                    with self.lock:
                        self.latest_result = result_data

            except Exception as e:
                # 静默失败（通常是人脸未检测到）
                pass

        print("[VisionModule] 情绪分析线程已停止")

    def get_emotion(self):
        """
        获取最新情绪检测结果（非阻塞）
        :return: 字典，包含 emotion, emotion_cn, confidence, all_emotions, region；
                 如果尚未检测到任何结果，返回 None
        """
        # 首先尝试从结果队列中取出最新结果（刷新缓存）
        try:
            while not self.result_queue.empty():
                with self.lock:
                    self.latest_result = self.result_queue.get_nowait()
        except queue.Empty:
            pass

        # 返回缓存的最新结果（可能为 None）
        with self.lock:
            # 为了避免外部修改，返回一个副本
            if self.latest_result is not None:
                return self.latest_result.copy()
            return None

    def stop(self):
        """停止所有后台线程，释放资源"""
        self.running = False
        for t in self.threads:
            t.join(timeout=2.0)
        print("[VisionModule] 已停止")


# 简单的自测代码（当直接运行此文件时执行）
if __name__ == "__main__":
    import time

    print("测试 VisionModule...")
    vision = VisionModule(camera_id=0)

    try:
        for i in range(100):  # 测试约10秒
            result = vision.get_emotion()
            if result:
                print(f"情绪: {result['emotion_cn']} ({result['confidence']:.1f}%)")
            else:
                print("未检测到人脸")
            time.sleep(0.1)
    finally:
        vision.stop()