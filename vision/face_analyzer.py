"""
模块名称：face_analyzer.py
功能描述：基于 Haar Cascade 的面部特征表情分析
依赖：opencv-python
"""

import cv2
import logging
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


class FaceAnalyzer:
    """
    面部表情分析器
    基于眼睛和嘴巴的特征进行表情分类
    """

    # 表情映射
    EMOTION_MAP = {
        'happy': '开心',
        'sad': '悲伤',
        'angry': '愤怒',
        'fear': '恐惧',
        'surprise': '惊讶',
        'neutral': '平静'
    }

    def __init__(self, config):
        """
        Args:
            config: Config 类实例，包含视觉相关阈值配置
        """
        self.config = config

        # 加载 Haar Cascade 分类器
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        self.mouth_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_smile.xml'
        )

        self._check_classifiers()

    def _check_classifiers(self):
        """检查分类器是否加载成功"""
        if self.face_cascade.empty():
            logger.warning("无法加载人脸检测器")
        if self.eye_cascade.empty():
            logger.warning("无法加载眼睛检测器")
        if self.mouth_cascade.empty():
            logger.warning("无法加载嘴巴检测器")

    def detect_faces(self, frame) -> list:
        """
        检测人脸

        Args:
            frame: BGR 图像帧

        Returns:
            人脸区域列表 [(x, y, w, h), ...]
        """
        if frame is None:
            return []

        # 缩小图像加快检测
        small = cv2.resize(frame, (320, 240))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        # 将坐标映射回原图尺寸
        scale_x = frame.shape[1] / 320
        scale_y = frame.shape[0] / 240
        scaled_faces = [
            (int(x * scale_x), int(y * scale_y), int(w * scale_x), int(h * scale_y))
            for (x, y, w, h) in faces
        ]

        return scaled_faces

    def analyze_emotion(self, frame, face_rect: Tuple[int, int, int, int]) -> Dict[str, Any]:
        """
        分析单个人脸的表情

        Args:
            frame: BGR 图像帧
            face_rect: 人脸区域 (x, y, w, h)

        Returns:
            表情分析结果字典
        """
        x, y, w, h = face_rect

        # 转换灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 提取人脸区域
        face_roi = gray[y:y + h, x:x + w]
        if face_roi.size == 0:
            return self._default_result()

        # 检测眼睛（上半部分人脸）
        eye_region = gray[y:y + int(h * 0.6), x:x + w]
        eyes = self.eye_cascade.detectMultiScale(
            eye_region, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20)
        )

        # 检测嘴巴（下半部分人脸）
        mouth_region = gray[y + int(h * 0.5):y + h, x:x + w]
        mouths = self.mouth_cascade.detectMultiScale(
            mouth_region, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20)
        )

        # 分类表情
        return self._classify_emotion(eyes, mouths, w, h)

    def _classify_emotion(self, eyes, mouths, face_width: int, face_height: int) -> Dict[str, Any]:
        """
        根据检测到的特征分类表情

        Args:
            eyes: 检测到的眼睛列表
            mouths: 检测到的嘴巴列表
            face_width: 人脸宽度
            face_height: 人脸高度

        Returns:
            表情分类结果
        """
        # 获取阈值配置
        eye_size_threshold = getattr(self.config, 'VISION_EYE_SIZE_THRESHOLD', 0.025)
        mouth_size_threshold = getattr(self.config, 'VISION_MOUTH_SIZE_THRESHOLD', 0.04)
        mouth_position_threshold = getattr(self.config, 'VISION_MOUTH_POSITION_THRESHOLD', 0.6)
        eye_size_small = getattr(self.config, 'VISION_EYE_SIZE_SMALL', 0.02)
        mouth_size_small = getattr(self.config, 'VISION_MOUTH_SIZE_SMALL', 0.02)

        num_eyes = len(eyes)
        num_mouths = len(mouths)

        # 计算平均眼睛大小
        eye_sizes = []
        for (ex, ey, ew, eh) in eyes:
            eye_sizes.append((ew * eh) / (face_width * face_height))
        avg_eye_size = sum(eye_sizes) / len(eye_sizes) if eye_sizes else 0

        # 计算平均嘴巴大小
        mouth_sizes = []
        for (mx, my, mw, mh) in mouths:
            mouth_sizes.append((mw * mh) / (face_width * face_height))
        avg_mouth_size = sum(mouth_sizes) / len(mouth_sizes) if mouth_sizes else 0

        # 计算平均嘴巴位置
        mouth_positions = []
        for (mx, my, mw, mh) in mouths:
            mouth_y_relative = (my + int(face_height * 0.5)) / face_height
            mouth_positions.append(mouth_y_relative)
        avg_mouth_position = sum(mouth_positions) / len(mouth_positions) if mouth_positions else 0.5

        confidence = 75.0
        emotion = 'neutral'

        # 表情分类逻辑
        if num_eyes >= 2 and avg_eye_size > eye_size_threshold and \
           num_mouths >= 1 and avg_mouth_size > mouth_size_threshold and \
           avg_mouth_position > mouth_position_threshold:
            emotion = 'fear'
            confidence = 82.0

        elif num_eyes >= 2 and num_mouths >= 1 and \
             avg_mouth_size < mouth_size_small and avg_eye_size < eye_size_small:
            emotion = 'angry'
            confidence = 78.0

        elif num_eyes >= 2 and num_mouths >= 1 and \
             avg_mouth_position > mouth_position_threshold and avg_eye_size < eye_size_small:
            emotion = 'sad'
            confidence = 80.0

        elif num_mouths >= 1 and avg_mouth_size > mouth_size_threshold and num_eyes >= 2:
            emotion = 'happy'
            confidence = 85.0

        elif num_eyes >= 2 and avg_eye_size > eye_size_threshold and \
             (num_mouths == 0 or avg_mouth_size < mouth_size_threshold):
            emotion = 'surprise'
            confidence = 83.0

        elif num_eyes >= 2 or num_mouths >= 1:
            emotion = 'neutral'
            confidence = 70.0

        return {
            'emotion': emotion,
            'emotion_cn': self.EMOTION_MAP.get(emotion, '平静'),
            'confidence': confidence,
            'face_width': face_width,
            'face_height': face_height,
            'eye_count': num_eyes,
            'mouth_count': num_mouths
        }

    def _default_result(self) -> Dict[str, Any]:
        """默认表情结果"""
        return {
            'emotion': 'neutral',
            'emotion_cn': '平静',
            'confidence': 50.0,
            'face_width': 0,
            'face_height': 0,
            'eye_count': 0,
            'mouth_count': 0
        }