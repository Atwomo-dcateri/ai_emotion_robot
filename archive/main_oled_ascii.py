# main_oled_ascii.py
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from archive.visionn import VisionModule
from hardware.oled_simulator import HardwareSimulator
from decision.engine_oled import DecisionEngine

def main():
    print("=" * 60)
    print("情感交互机器人 - OLED表情版 (ASCII模式)")
    print("=" * 60)
    
    # 初始化视觉模块
    print("\n初始化视觉模块...")
    vision = VisionModule(camera_id=0)
    
    # 初始化OLED模拟器（使用ASCII模式）
    print("\n初始化OLED屏幕...")
    hardware = HardwareSimulator(use_ascii=True)  # 关键：设为True
    
    # 初始化决策引擎（使用ASCII模式）
    print("\n初始化决策引擎...")
    engine = DecisionEngine(use_ascii=True)  # 关键：设为True
    
    print("\n系统运行中... 按 Ctrl+C 退出\n")
    
    try:
        while True:
            # 获取视觉结果
            result = vision.get_emotion()
            current_time = time.strftime("%H:%M:%S")
            
            # 构建用户状态
            user_state = {
                'timestamp': current_time,
                'face_emotion': None
            }
            
            if result:
                user_state['face_emotion'] = {
                    'emotion': result['emotion_cn'],
                    'confidence': result['confidence']
                }
            
            # 决策
            actions = engine.decide(user_state)
            
            # 执行动作
            for action in actions:
                if action.get('type') != 'none':
                    hardware.execute_action(action)
            
            # 打印状态行
            if result:
                emotion = result['emotion_cn']
                confidence = result['confidence']
                reaction = engine.decide_pretty(user_state)
                print(f"[{current_time}] {emotion} {confidence:.1f}% → {reaction}")
            else:
                print(f"[{current_time}] 无人脸 → 显示默认表情")
            
            time.sleep(2)  # 每2秒一个周期
            
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