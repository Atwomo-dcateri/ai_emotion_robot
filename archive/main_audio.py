#!/usr/bin/env python3
# main_audio.py
"""
AI情感机器人 - 音频版主程序
集成视觉、决策、显示和音频功能
"""

import sys
import os
import time
import signal
import threading

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from archive.visionn import VisionModule
from decision.llm_cloud import DecisionEngine
from hardware.oled_driver import OLEDDisplay
from archive.audio_module_simple import AudioModule


class AudioEmotionRobot:
    """带音频功能的AI情感机器人"""

    def __init__(self, camera_id=0, oled_config=None):
        self.running = False

        # 默认OLED配置
        if oled_config is None:
            oled_config = {
                'address': 0x3C,
                'port': 1,
                'device_type': 'sh1106'
            }

        print("=============================================================")
        print("初始化AI情感机器人 - 音频版")
        print("=============================================================")

        # 初始化各个模块
        self.vision = VisionModule(camera_id=camera_id)
        self.decision = DecisionEngine()
        self.oled = OLEDDisplay(oled_config)
        self.audio = AudioModule()

        print("所有模块初始化完成！")

    def _audio_interaction_loop(self):
        """音频交互循环"""
        while self.running:
            try:
                # 录音并识别
                print("[音频] 开始录音识别...")
                text = self.audio.record_and_recognize(duration=3)

                if text:
                    print(f"[音频] 用户说: {text}")

                    # 根据语音内容生成回复
                    if "你好" in text or "hello" in text.lower():
                        response = "你好！我是AI情感机器人，很高兴见到你！"
                    elif "再见" in text or "bye" in text.lower():
                        response = "再见！希望很快再见到你！"
                    elif "开心" in text:
                        response = "我看到你很开心，我也为你感到高兴！"
                    elif "难过" in text or "伤心" in text:
                        response = "我理解你的感受，希望你能早日开心起来！"
                    else:
                        response = f"我听到你说了：{text}"

                    # 语音回复
                    print(f"[音频] 回复: {response}")
                    self.audio.speak(response)

                    # OLED显示语音交互状态
                    self.oled.show_emotion("平静")
                    time.sleep(2)

                else:
                    print("[音频] 未识别到语音")

            except Exception as e:
                print(f"[音频] 交互出错: {e}")

            # 短暂暂停，避免过于频繁的交互
            time.sleep(1)

    def start(self):
        """启动机器人"""
        if self.running:
            print("机器人已经在运行中")
            return

        self.running = True
        print("=============================================================")
        print("AI情感机器人 - 音频版 启动中...")
        print("=============================================================")

        try:
            # 启动视觉模块
            self.vision.start()

            # 启动音频交互线程
            audio_thread = threading.Thread(target=self._audio_interaction_loop, daemon=True)
            audio_thread.start()
            print("[音频] 语音交互线程已启动")

            # 主循环
            print("=============================================================")
            print("机器人运行中... 按 Ctrl+C 退出")
            print("支持语音交互和视觉检测")
            print("=============================================================")

            while self.running:
                # 获取当前视觉信息
                emotion = self.vision.get_emotion()
                confidence = self.vision.get_confidence()

                # 显示在OLED上
                if emotion:
                    self.oled.show_emotion(emotion)
                    print(f"[视觉] 检测到表情: {emotion} (置信度: {confidence:.2f})")

                # 短暂延迟
                time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n收到停止信号，正在关闭...")
        except Exception as e:
            print(f"运行出错: {e}")
        finally:
            self.stop()

    def stop(self):
        """停止机器人"""
        if not self.running:
            return

        print("正在关闭系统...")
        self.running = False

        # 停止各个模块
        if hasattr(self, 'vision'):
            self.vision.stop()

        if hasattr(self, 'oled'):
            self.oled.close()

        print("系统已关闭")

    def __del__(self):
        """析构函数"""
        self.stop()


def main():
    """主函数"""
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='AI情感机器人 - 音频版')
    parser.add_argument('--camera', type=int, default=0, help='摄像头ID (默认: 0)')
    parser.add_argument('--oled-address', type=lambda x: int(x, 16), default=0x3C, help='OLED I2C地址 (默认: 0x3C)')
    parser.add_argument('--oled-port', type=int, default=1, help='OLED I2C端口 (默认: 1)')
    parser.add_argument('--oled-type', choices=['ssd1306', 'sh1106'], default='sh1106', help='OLED设备类型 (默认: sh1106)')

    args = parser.parse_args()

    # OLED配置
    oled_config = {
        'address': args.oled_address,
        'port': args.oled_port,
        'device_type': args.oled_type
    }

    # 创建机器人实例
    robot = AudioEmotionRobot(camera_id=args.camera, oled_config=oled_config)

    # 设置信号处理
    def signal_handler(signum, frame):
        print(f"\n收到信号 {signum}，正在关闭...")
        robot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动机器人
    robot.start()


if __name__ == "__main__":
    main()