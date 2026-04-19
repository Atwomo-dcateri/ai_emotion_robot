# main_working.py
import sys
import os
import time

# 添加项目根目录到模块搜索路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入视觉模块
from vision.vision import VisionModule

def main():
    print("=" * 50)
    print("情感交互机器人 - 工作版")
    print("=" * 50)
    
    try:
        # 初始化视觉模块
        print("初始化视觉模块...")
        vision = VisionModule(camera_id=0)
        print("视觉模块初始化成功")
        
        print("\n开始实时检测，按 Ctrl+C 停止\n")
        print("-" * 50)
        print("时间\t\t情绪\t置信度")
        print("-" * 50)
        
        while True:
            result = vision.get_emotion()
            current_time = time.strftime("%H:%M:%S")
            
            if result:
                print(f"{current_time}\t{result['emotion_cn']}\t{result['confidence']:.1f}%")
            else:
                print(f"{current_time}\t无人脸\t-")
            
            time.sleep(0.5)  # 控制检测频率
            
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        if 'vision' in locals():
            vision.stop()
            print("视觉模块已停止")
        print("程序退出")
        input("按回车键关闭窗口...")  # 防止控制台闪退

if __name__ == "__main__":
    main()