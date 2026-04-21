# main_light.py - 树莓派轻量版入口
import sys
import os
import time

# 添加项目根目录到模块搜索路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from archive.visionn import VisionModule
from hardware.oled_simulator import HardwareSimulator

def main():
    print("=" * 60)
    print("情感交互机器人 - 树莓派摄像头版")
    print("功能：真实摄像头人脸检测 + ASCII 显示")
    print("=" * 60)

    # 初始化视觉模块（轻量人脸检测）
    print("\n初始化视觉模块...")
    vision = VisionModule(camera_id=0)

    # 初始化硬件模拟器（ASCII模式）
    print("\n初始化OLED屏幕...")
    hardware = HardwareSimulator(use_ascii=True)

    print("\n系统运行中... 按 Ctrl+C 退出\n")
    print("-" * 70)
    print("时间\t\t状态\t\t显示")
    print("-" * 70)

    try:
        while True:
            # 获取视觉结果
            result = vision.get_emotion()
            current_time = time.strftime("%H:%M:%S")

            if result:
                # 检测到人脸，显示“平静”表情
                hardware.oled.show_face('平静', result['confidence'])
                print(f"{current_time}\t检测到人脸\t平静 ({result['confidence']:.1f}%)")
            else:
                # 未检测到人脸，显示默认表情
                hardware.oled.show_face('默认')
                print(f"{current_time}\t无人脸\t\t等待中...")

            time.sleep(1)  # 每秒检测一次

    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n清理资源...")
        vision.stop()
        print("程序退出")

if __name__ == "__main__":
    main()