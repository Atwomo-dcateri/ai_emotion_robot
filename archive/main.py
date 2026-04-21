# # main.py
# import sys
# import io
# import os
# import time
# import signal
# from collections import deque

# # 设置控制台编码
# if sys.platform == 'win32':
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# # 添加项目根目录到模块搜索路径
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# # 导入视觉模块
# from vision.vision import VisionModule

# class EmotionRobot:
#     """情感机器人主类"""
    
#     def __init__(self):
#         self.running = True
#         self.modules = {}
#         self.emotion_history = deque(maxlen=10)  # 保存最近10次情绪检测结果
        
#         # 注册信号处理
#         signal.signal(signal.SIGINT, self.signal_handler)
#         signal.signal(signal.SIGTERM, self.signal_handler)
        
#     def signal_handler(self, signum, frame):
#         """处理退出信号"""
#         print("\n\n[Notice] 接收到退出信号，正在关闭机器人...")
#         self.running = False
        
#     def init_modules(self):
#         """初始化所有模块"""
#         print("=" * 60)
#         sys.stdout.flush()
#         print("--- 情感交互机器人系统启动 ---")
#         sys.stdout.flush()
#         print("=" * 60)
#         sys.stdout.flush()
        
#         try:
#             # 初始化视觉模块
#             print("[System] 初始化视觉模块...")
#             sys.stdout.flush()
#             self.modules['vision'] = VisionModule(camera_id=0)
#             print("    [OK] 视觉模块初始化成功")
#             sys.stdout.flush()
            
#         except Exception as e:
#             print(f"    [Error] 模块初始化失败: {e}")
#             import traceback
#             traceback.print_exc()
#             return False
        
#         return True
    
#     def analyze_emotion_trend(self):
#         """分析情绪趋势"""
#         if not self.emotion_history:
#             return "未知"
        
#         # 统计最近的情绪
#         from collections import Counter
#         emotions = [e['emotion_cn'] for e in self.emotion_history if e]
#         if not emotions:
#             return "未知"
        
#         counter = Counter(emotions)
#         most_common = counter.most_common(1)[0]
#         return f"{most_common[0]} ({most_common[1]}/{len(emotions)})"
        
#     def run(self):
#         """主运行循环"""
#         if not self.init_modules():
#             print("[Error] 系统初始化失败，退出")
#             return
        
#         print("\n[Running] 系统运行中... 按 Ctrl+C 退出\n")
#         print("-" * 60)
#         print(f"{'时间':<10} {'情绪':<8} {'置信度':<8} {'趋势'}")
#         print("-" * 60)
        
#         try:
#             while self.running:
#                 # 获取视觉结果
#                 emotion_data = self.modules['vision'].get_emotion()
                
#                 current_time = time.strftime("%H:%M:%S")
                
#                 if emotion_data:
#                     # 保存到历史记录
#                     self.emotion_history.append(emotion_data)
                    
#                     # 分析趋势
#                     trend = self.analyze_emotion_trend()
                    
#                     # 显示结果
#                     print(f"{current_time:<5} "
#                           f"{emotion_data['emotion_cn']:<8} "
#                           f"{emotion_data['confidence']:>6.1f}%    "
#                           f"趋势: {trend}")
#                     sys.stdout.flush()
#                 else:
#                     print(f"{current_time:<10} {'无人脸':<8} {'-':>8}   -")
#                     sys.stdout.flush()
                
#                 # 控制循环频率
#                 time.sleep(0.5)
                
#         except KeyboardInterrupt:
#             print("\n\n[System] 检测到键盘中断")
#         except Exception as e:
#             print(f"\n[Error] 运行错误: {e}")
#             import traceback
#             traceback.print_exc()
#         finally:
#             self.cleanup()
            
#     def cleanup(self):
#         """清理资源"""
#         print("\n[System] 正在清理资源...")
        
#         # 停止所有模块
#         for name, module in self.modules.items():
#             try:
#                 if hasattr(module, 'stop'):
#                     module.stop()
#                     print(f"    [OK] {name} 模块已停止")
#             except Exception as e:
#                 print(f"    [Error] {name} 模块停止失败: {e}")
        
#         print("=" * 60)
#         print("--- 系统已退出。再见！ ---")
#         print("=" * 60)

# def main():
#     """程序入口"""
#     robot = EmotionRobot()
#     robot.run()

# if __name__ == "__main__":
#     main()


# main_cloud_llm.py
import sys
import os
import time

# 添加项目根目录到模块搜索路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from archive.visionn import VisionModule
from hardware.oled_simulator import HardwareSimulator
from decision.llm_cloud import CloudLLMEngine

def main():
    print("=" * 60)
    print("情感交互机器人 - 云端LLM智能决策版")
    print("=" * 60)
    
    # 请在这里设置你的DeepSeek API密钥
    # 方法1：直接填写（注意不要泄露）
    API_KEY = "sk-c5db5d2b11c8432c943364007d252df1"  # 替换为真实密钥
    
    # 方法2：从环境变量读取（更安全）
    # API_KEY = os.environ.get("DEEPSEEK_API_KEY")
    
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