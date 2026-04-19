# test_extended_emotions.py - 扩展表情分析测试脚本
import cv2
import numpy as np
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vision.vision import VisionModule

def test_extended_emotions():
    print("测试扩展表情分析功能...")
    print("=" * 50)

    # 创建视觉模块
    vision = VisionModule(camera_id=0)

    print("等待扩展表情分析结果...")
    print("支持的表情类型：平静、开心、惊讶、悲伤、愤怒、恐惧")
    print("-" * 60)

    try:
        import time
        start_time = time.time()
        detected_emotions = set()

        while time.time() - start_time < 30:  # 测试30秒
            result = vision.get_emotion()

            if result:
                emotion = result['emotion_cn']
                detected_emotions.add(emotion)

                print(f"检测结果: {emotion} ({result['confidence']:.1f}%)")
                print(f"表情分布: {result['all_emotions']}")
                print(f"人脸数量: {result.get('face_count', 1)}")
                print("-" * 40)
            else:
                print("无人脸检测")
                print("-" * 40)

            time.sleep(2)  # 每2秒检查一次

        print("\n测试完成！")
        print(f"在测试期间检测到的表情类型: {sorted(detected_emotions)}")
        print(f"总共检测到 {len(detected_emotions)} 种不同表情")

    except KeyboardInterrupt:
        print("\n测试中断")
    finally:
        vision.stop()
        print("测试完成")

if __name__ == "__main__":
    test_extended_emotions()