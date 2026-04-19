# main_oled_real.py - 真实OLED显示版主程序
import sys
import os
import time
import signal
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vision.vision import VisionModule
from hardware.oled_driver import RealOLEDHardware
from decision.engine_oled import DecisionEngine

class EmotionRobotOLED:
    """真实OLED显示的情感机器人"""

    def __init__(self, use_real_oled=True):
        """
        初始化机器人
        :param use_real_oled: 是否使用真实OLED硬件
        """
        print("=" * 60)
        print("情感交互机器人 - 真实OLED显示版")
        print("=" * 60)

        self.running = False

        # 初始化视觉模块
        print("\n初始化视觉模块...")
        self.vision = VisionModule(camera_id=0)

        # 初始化真实OLED硬件
        print("\n初始化OLED显示屏...")
        self.hardware = RealOLEDHardware(use_real_oled=use_real_oled, device_type='sh1106')

        # 初始化决策引擎
        print("\n初始化决策引擎...")
        self.engine = DecisionEngine(use_ascii=False)  # 不使用ASCII模式

        # 状态变量
        self.last_emotion = None
        self.emotion_start_time = 0
        self.emotion_duration = 0

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print("\n系统初始化完成！")
        print("按 Ctrl+C 退出程序")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n收到信号 {signum}，正在关闭...")
        self.stop()

    def start(self):
        """启动机器人"""
        self.running = True
        print("\n" + "=" * 60)
        print("机器人运行中...")
        print("=" * 60)

        try:
            while self.running:
                # 获取视觉结果
                result = self.vision.get_emotion()
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

                    # 显示表情
                    emotion = result['emotion_cn']
                    confidence = result['confidence']

                    # 检查是否需要切换表情或播放动画
                    current_time = time.time()

                    if emotion != self.last_emotion:
                        # 表情切换
                        print(f"\n表情变化: {self.last_emotion} → {emotion}")
                        self.last_emotion = emotion
                        self.emotion_start_time = current_time

                        # 显示新表情
                        self.hardware.show_face(emotion, confidence)

                    elif current_time - self.emotion_start_time > 5.0:
                        # 同一个表情持续5秒，播放动画
                        print(f"播放 {emotion} 动画")
                        self.hardware.show_animation(emotion, frames=3, duration=0.3)
                        self.emotion_start_time = current_time

                    # 定期显示状态信息
                    if int(current_time) % 30 == 0:  # 每30秒
                        status_info = {
                            'emotion': emotion,
                            'confidence': f"{confidence:.0f}%",
                            'face_count': result.get('face_count', 1),
                            'time': current_time,
                            'status': 'active'
                        }
                        self.hardware.show_status_display(status_info)
                        time.sleep(1)  # 避免重复显示

                else:
                    # 无人脸检测
                    if self.last_emotion != '默认':
                        print("\n无人脸检测，显示默认表情")
                        self.last_emotion = '默认'
                        self.hardware.show_face('默认', 50.0)

                # 控制循环频率
                time.sleep(0.5)

        except Exception as e:
            print(f"\n运行时错误: {e}")
        finally:
            self.stop()

    def stop(self):
        """停止机器人"""
        if not self.running:
            return

        self.running = False
        print("\n正在关闭系统...")

        # 关闭各个模块
        try:
            if hasattr(self.vision, 'stop'):
                self.vision.stop()
        except:
            pass

        try:
            self.hardware.close()
        except:
            pass

        print("系统已关闭")
        sys.exit(0)

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='情感机器人 - 真实OLED显示版')
    parser.add_argument('--simulator', action='store_true',
                       help='使用模拟器模式（不连接真实OLED）')
    parser.add_argument('--i2c-address', type=lambda x: int(x, 0), default=0x3C,
                       help='OLED I2C地址 (默认: 0x3C)')
    parser.add_argument('--i2c-port', type=int, default=1,
                       help='I2C端口号 (默认: 1)')

    args = parser.parse_args()

    # 创建机器人实例
    use_real_oled = not args.simulator

    if use_real_oled:
        print(f"OLED配置: I2C地址=0x{args.i2c_address:02X}, 端口={args.i2c_port}")
        print("注意: 请确保OLED硬件已正确连接")
    else:
        print("运行模式: 模拟器模式")

    robot = EmotionRobotOLED(use_real_oled=use_real_oled)
    robot.start()

if __name__ == "__main__":
    main()