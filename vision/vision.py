print("[vision.py] 开始加载模块 - 真实摄像头版")
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

# 禁用 TensorFlow 冗余输出（如果有的话）
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.getLogger().setLevel(logging.ERROR)


class VisionModule:
    """
    视觉模块：真实摄像头人脸检测
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
        
        # 加载 Haar Cascade 人脸检测器
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        if self.face_cascade.empty():
            print("[VisionModule] 警告：无法加载人脸检测器")
        
        # 加载眼睛和嘴巴检测器用于表情分析
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.mouth_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
        
        if self.eye_cascade.empty():
            print("[VisionModule] 警告：无法加载眼睛检测器")
        if self.mouth_cascade.empty():
            print("[VisionModule] 警告：无法加载嘴巴检测器")
        
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

        # 人脸检测线程
        t_analyze = threading.Thread(target=self._face_detector, daemon=True)
        t_analyze.start()
        self.threads.append(t_analyze)

        # 等待摄像头启动
        time.sleep(1.0)

    def _camera_reader(self):
        """
        摄像头读取线程：只负责从摄像头读取帧，放入队列
        """
        print("[VisionModule] 正在打开摄像头...")
        cap = cv2.VideoCapture(self.camera_id)
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

    def _face_detector(self):
        """
        人脸检测和表情分析线程：从帧队列取帧，进行人脸检测和表情分析，结果放入结果队列
        """
        print("[VisionModule] 人脸检测线程已启动")
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
                # 缩小图像以加快检测
                small = cv2.resize(frame, (320, 240))
                
                # 转换为灰度图
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                
                # 检测人脸
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                
                last_analysis_time = now
                
                if len(faces) > 0:
                    # 检测到人脸，进行表情分析
                    face = faces[0]  # 使用第一个检测到的人脸
                    emotion_result = self._analyze_emotion(gray, face)
                    
                    result_data = {
                        'emotion': emotion_result['emotion'],           # 英文标签
                        'emotion_cn': emotion_result['emotion_cn'],     # 中文标签
                        'confidence': emotion_result['confidence'],     # 置信度
                        'all_emotions': emotion_result['all_emotions'], # 表情分布
                        'region': face,                                 # 人脸区域
                        'face_count': len(faces)                        # 人脸数量
                    }
                else:
                    # 未检测到人脸
                    result_data = None
                
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
                # 静默失败
                pass

    def _analyze_emotion(self, gray_frame, face_rect):
        """
        基于面部特征的表情分析
        :param gray_frame: 灰度图像
        :param face_rect: 人脸区域 (x, y, w, h)
        :return: 表情分析结果
        """
        x, y, w, h = face_rect
        
        # 提取人脸区域
        face_roi = gray_frame[y:y+h, x:x+w]
        if face_roi.size == 0:
            return self._default_emotion()
        
        # 检测眼睛（在上半部分人脸）
        eye_region = gray_frame[y:y+int(h*0.6), x:x+w]
        eyes = self.eye_cascade.detectMultiScale(eye_region, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
        
        # 检测嘴巴（在下半部分人脸）
        mouth_region = gray_frame[y+int(h*0.5):y+h, x:x+w]
        mouths = self.mouth_cascade.detectMultiScale(mouth_region, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
        
        # 基于检测结果分析表情
        return self._classify_emotion(eyes, mouths, w, h)
    
    def _classify_emotion(self, eyes, mouths, face_width, face_height):
        """
        根据检测到的特征分类表情
        支持的表情类型：平静、开心、惊讶、悲伤、愤怒、恐惧
        """
        # 计算特征数量和位置
        num_eyes = len(eyes)
        num_mouths = len(mouths)
        
        # 计算眼睛大小（相对人脸大小）
        eye_sizes = []
        for (ex, ey, ew, eh) in eyes:
            eye_sizes.append((ew * eh) / (face_width * face_height))
        avg_eye_size = sum(eye_sizes) / len(eye_sizes) if eye_sizes else 0
        
        # 计算嘴巴大小
        mouth_sizes = []
        for (mx, my, mw, mh) in mouths:
            mouth_sizes.append((mw * mh) / (face_width * face_height))
        avg_mouth_size = sum(mouth_sizes) / len(mouth_sizes) if mouth_sizes else 0
        
        # 计算嘴巴位置（相对人脸高度）
        mouth_positions = []
        for (mx, my, mw, mh) in mouths:
            # my是嘴巴在mouth_region内的y坐标，需要转换为人脸坐标
            mouth_y_relative = (my + int(face_height*0.5)) / face_height
            mouth_positions.append(mouth_y_relative)
        avg_mouth_position = sum(mouth_positions) / len(mouth_positions) if mouth_positions else 0.5
        
        # 表情分类逻辑 - 扩展版
        confidence = 75.0  # 基础置信度
        
        # 恐惧：大眼睛 + 张开的嘴巴（嘴巴位置较低）
        if num_eyes >= 2 and avg_eye_size > 0.025 and num_mouths >= 1 and avg_mouth_size > 0.04 and avg_mouth_position > 0.6:
            emotion = 'fear'
            emotion_cn = '恐惧'
            confidence = 82.0
            
        # 愤怒：紧闭的嘴巴 + 正常眼睛（嘴巴小，位置正常）
        elif num_eyes >= 2 and num_mouths >= 1 and avg_mouth_size < 0.02 and avg_eye_size < 0.025:
            emotion = 'angry'
            emotion_cn = '愤怒'
            confidence = 78.0
            
        # 悲伤：下垂的嘴巴 + 较小眼睛（嘴巴位置较低，眼睛偏小）
        elif num_eyes >= 2 and num_mouths >= 1 and avg_mouth_position > 0.65 and avg_eye_size < 0.02:
            emotion = 'sad'
            emotion_cn = '悲伤'
            confidence = 80.0
            
        # 开心：大嘴巴 + 正常眼睛
        elif num_mouths >= 1 and avg_mouth_size > 0.05 and num_eyes >= 2:
            emotion = 'happy'
            emotion_cn = '开心'
            confidence = 85.0
            
        # 惊讶：大眼睛 + 正常嘴巴
        elif num_eyes >= 2 and avg_eye_size > 0.025 and (num_mouths == 0 or avg_mouth_size < 0.04):
            emotion = 'surprise'
            emotion_cn = '惊讶'
            confidence = 83.0
            
        # 平静：检测到特征但不满足其他条件
        elif num_eyes >= 2 or num_mouths >= 1:
            emotion = 'neutral'
            emotion_cn = '平静'
            confidence = 70.0
            
        # 默认情况
        else:
            emotion = 'neutral'
            emotion_cn = '平静'
            confidence = 60.0
        
        # 创建表情分布（只显示主要表情）
        all_emotions = {emotion: confidence}
        
        return {
            'emotion': emotion,
            'emotion_cn': emotion_cn,
            'confidence': confidence,
            'all_emotions': all_emotions
        }
    
    def _default_emotion(self):
        """默认表情结果"""
        return {
            'emotion': 'neutral',
            'emotion_cn': '平静',
            'confidence': 50.0,
            'all_emotions': {'neutral': 50.0}
        }

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