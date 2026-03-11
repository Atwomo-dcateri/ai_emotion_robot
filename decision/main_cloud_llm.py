# main_cloud_llm.py
import sys
import os
import time

# 添加项目根目录到模块搜索路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vision.vision import VisionModule
from hardware.oled_simulator import HardwareSimulator
from decision.llm_cloud import CloudLLMEngine

def main():
    print("=" * 60)
    print("情感交互机器人 - 云端LLM智能决策版")
    print("=" * 60)
    
    # 请在这里设置你的DeepSeek API密钥
    # 方法1：直接填写（注意不要泄露）
    # API_KEY = "sk-c5db5d2b11c8432c943364007d252df1"  # 替换为真实密钥
    
    # 方法2：从环境变量读取（更安全）
    API_KEY = os.environ.get("DEEPSEEK_API_KEY")
    
    # if not API_KEY or API_KEY == "sk-c5db5d2b11c8432c943364007d252df1":
    #     print("\n❌ 请先设置DeepSeek API密钥")
    #     print("   1. 访问 https://platform.deepseek.com/ 注册获取")
    #     print("   2. 在代码中填写 API_KEY 或设置环境变量 DEEPSEEK_API_KEY")
    #     return
    
    # 初始化视觉模块
    print("\n初始化视觉模块...")
    vision = VisionModule(camera_id=0)
    
    # 初始化OLED模拟器（ASCII模式）
    print("\n初始化OLED屏幕...")
    hardware = HardwareSimulator(use_ascii=True)
    
    # 初始化云端LLM引擎
    print("\n初始化云端LLM引擎...")
    try:
        engine = CloudLLMEngine(api_key=API_KEY)
        print("✅ 云端LLM引擎初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return
    
    print("\n系统运行中... 按 Ctrl+C 退出\n")
    print("-" * 70)
    
    try:
        while True:
            # 获取视觉结果
            result = vision.get_emotion()
            current_time = time.strftime("%H:%M:%S")
            
            # 构建用户状态
            user_state = {
                'timestamp': current_time,
                'face_emotion': None,
                'speech_text': None  # 预留语音
            }
            
            if result:
                user_state['face_emotion'] = {
                    'emotion': result['emotion_cn'],
                    'confidence': result['confidence']
                }
            
            # 调用LLM决策
            print(f"\n[{current_time}] 调用LLM决策中...")
            actions = engine.decide(user_state)
            
            # 执行动作
            for action in actions:
                hardware.execute_action(action)
            
            # 打印状态行
            if result:
                emotion = result['emotion_cn']
                confidence = result['confidence']
                reaction = engine.decide_pretty(user_state)
                print(f"[{current_time}] {emotion} {confidence:.1f}% → {reaction}")
            else:
                print(f"[{current_time}] 无人脸 → 等待中")
            
            time.sleep(3)  # 每3秒一次决策
            
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