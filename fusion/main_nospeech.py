# main_nospeech.py
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vision.vision import VisionModule

def main():
    print("=" * 50)
    print("情感交互机器人 - 视觉版")
    print("=" * 50)
    
    # 初始化视觉模块
    print("\n初始化视觉模块...")
    vision = VisionModule(camera_id=0)
    
    print("\n系统运行中... 按 Ctrl+C 退出\n")
    print("-" * 60)
    print("时间\t\t表情\t置信度")
    print("-" * 60)
    
    try:
        while True:
            result = vision.get_emotion()
            current_time = time.strftime("%H:%M:%S")
            
            if result:
                print(f"{current_time}\t{result['emotion_cn']}\t{result['confidence']:.1f}%")
            else:
                print(f"{current_time}\t无人脸\t-")
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
    finally:
        print("\n清理资源...")
        vision.stop()
        print("程序退出")

if __name__ == "__main__":
    main()