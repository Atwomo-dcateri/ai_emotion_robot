# test_oled_emotion_display.py - OLED表情显示功能测试脚本
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hardware.oled_simulator import HardwareSimulator

def test_enhanced_oled_display():
    print("测试增强版OLED表情显示功能...")
    print("=" * 60)

    # 创建硬件模拟器（ASCII模式）
    hardware = HardwareSimulator(use_ascii=True)

    print("开始测试各种OLED显示功能...")
    print("-" * 60)

    try:
        import time

        # 1. 测试基础表情显示
        print("\n1. 基础表情显示测试")
        emotions = ['开心', '悲伤', '愤怒', '恐惧', '惊讶', '平静']
        for emotion in emotions:
            print(f"\n显示 {emotion} 表情:")
            hardware.oled.show_face(emotion, confidence=80.0)
            time.sleep(1)

        # 2. 测试动画功能
        print("\n2. 动画功能测试")
        print("\n开心动画:")
        hardware.oled.show_animation('开心', frames=4, duration=0.5)

        print("\n惊讶动画:")
        hardware.oled.show_animation('惊讶', frames=4, duration=0.5)

        print("\n眨眼动画:")
        hardware.oled.show_animation('眨眼', frames=5, duration=0.3)

        # 3. 测试表情过渡
        print("\n3. 表情过渡测试")
        hardware.show_emotion_transition('平静', '开心', steps=3)

        # 4. 测试表情强度变化
        print("\n4. 表情强度变化测试")
        hardware.show_emotion_intensity('惊讶', base_confidence=50.0, max_confidence=95.0, steps=5)

        # 5. 测试状态面板
        print("\n5. 状态面板测试")
        status_info = {
            'emotion': '开心',
            'confidence': 85.0,
            'face_count': 1,
            'uptime': '00:15:30',
            'cpu_temp': 45.2,
            'memory': 68.5
        }
        hardware.show_status_display(status_info)

        # 6. 测试表情序列
        print("\n6. 表情序列测试")
        emotion_sequence = [
            {'emotion': '平静', 'confidence': 70.0, 'duration': 0.8},
            {'emotion': '惊讶', 'confidence': 85.0, 'duration': 1.0},
            {'emotion': '开心', 'confidence': 90.0, 'duration': 1.2},
            {'emotion': '平静', 'confidence': 75.0, 'duration': 0.8}
        ]
        hardware.create_emotion_sequence(emotion_sequence, interval=1.0)

        # 7. 测试组合动作
        print("\n7. 组合动作测试")
        combined_action = {
            'type': 'combined',
            'name': 'greeting',
            'oled': {
                'type': 'oled',
                'effect': 'animation',
                'emotion': '开心',
                'frames': 3
            }
        }
        hardware.execute_action(combined_action)

        print("\n" + "=" * 60)
        print("✅ 所有OLED表情显示功能测试完成！")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n测试中断")
    except Exception as e:
        print(f"\n测试出错: {e}")
    finally:
        print("测试结束")

if __name__ == "__main__":
    test_enhanced_oled_display()