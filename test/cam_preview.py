#!/usr/bin/env python3
"""
摄像头实时人脸检测预览 — 帮助诊断人脸检测问题

用法:
  python3 test/cam_preview.py          # 显示 OpenCV 窗口
  python3 test/cam_preview.py --headless  # 无窗口模式（只打印检测结果）
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['OPENCV_IO_MAX_IMAGE_PIXELS'] = str(10**9)

import cv2
import numpy as np

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--headless', action='store_true', help='无窗口模式')
    parser.add_argument('--duration', type=int, default=30, help='headless 模式运行秒数')
    args = parser.parse_args()

    # 加载分类器
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

    print(f"{'='*50}")
    print(f"  摄像头实时人脸检测")
    print(f"{'='*50}")
    print(f"  分类器: {'✅' if not face_cascade.empty() else '❌'} 人脸")
    print(f"          {'✅' if not eye_cascade.empty() else '❌'} 眼睛")
    print(f"          {'✅' if not smile_cascade.empty() else '❌'} 嘴巴")
    print(f"{'='*50}")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 无法打开摄像头")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("摄像头已打开，按 Ctrl+C 退出\n")

    start = time.time()
    frame_count = 0
    face_count_total = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            frame_count += 1
            h, w = frame.shape[:2]

            # --- 人脸检测 (缩放到 320x240 加速) ---
            small = cv2.resize(frame, (320, 240))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))

            # 映射回原图坐标
            scale_x = w / 320
            scale_y = h / 240
            scaled_faces = []
            for (x, y, fw, fh) in faces:
                x = int(x * scale_x)
                y = int(y * scale_y)
                fw = int(fw * scale_x)
                fh = int(fh * scale_y)
                scaled_faces.append((x, y, fw, fh))

            if scaled_faces:
                face_count_total += 1
                # 检测眼睛和嘴巴
                for (fx, fy, fw, fh) in scaled_faces:
                    # 眼睛 (上半部分)
                    eye_roi = gray[int(fy/scale_y):int((fy+fh*0.6)/scale_y),
                                   int(fx/scale_x):int((fx+fw)/scale_x)]
                    eyes = eye_cascade.detectMultiScale(eye_roi, 1.1, 3, minSize=(20, 20))

                    # 嘴巴 (下半部分)
                    mouth_roi = gray[int((fy+fh*0.5)/scale_y):int((fy+fh)/scale_y),
                                     int(fx/scale_x):int((fx+fw)/scale_x)]
                    mouths = smile_cascade.detectMultiScale(mouth_roi, 1.1, 3, minSize=(20, 20))

                    print(f"\r  🤦 人脸 ({len(faces)}) | 眼睛: {len(eyes)} | 嘴巴: {len(mouths)} | 帧: {frame_count}", end='', flush=True)

                    if not args.headless:
                        # 绘制
                        cv2.rectangle(frame, (fx, fy), (fx+fw, fy+fh), (0, 255, 0), 2)
                        cv2.putText(frame, f'Face {len(faces)}', (fx, fy-10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            else:
                if frame_count % 10 == 0:
                    print(f"\r  🙅 无人脸 | 帧: {frame_count}", end='', flush=True)

            if not args.headless:
                cv2.imshow('Camera Preview (press q to quit)', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            elapsed = time.time() - start
            if args.headless and elapsed > args.duration:
                break

    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        cap.release()
        if not args.headless:
            cv2.destroyAllWindows()

        elapsed = time.time() - start
        print(f"\n\n{'='*50}")
        print(f"  统计:")
        print(f"  总帧数: {frame_count}")
        print(f"  检测到人脸的帧数: {face_count_total}")
        if frame_count > 0:
            print(f"  人脸检测率: {face_count_total/frame_count*100:.1f}%")
        print(f"  运行时长: {elapsed:.1f}秒")
        print(f"{'='*50}")

if __name__ == '__main__':
    main()
