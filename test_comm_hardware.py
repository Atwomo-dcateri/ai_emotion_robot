#!/usr/bin/env python3
"""
通信模块 — 阶段 3：真实硬件通信测试

测试上位机（树莓派）与下位机（STM32）之间的串口通信。
顺序执行以下测试：
  1. 串口连接测试
  2. OLED 表情显示
  3. OLED 文本显示
  4. OLED 清屏
  5. 舵机控制（点头 + 摇头）
  6. 健康数据接收

用法:
  python3 test_comm_hardware.py                          # 默认 /dev/ttyS0
  python3 test_comm_hardware.py --port /dev/ttyAMA0      # 指定串口
  python3 test_comm_hardware.py --loop                    # 循环接收健康数据
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from communication.comm_controller import CommController


PASS = 0
FAIL = 0


def info(msg):
    print(f"  ℹ️  {msg}")


def step(name):
    print(f"\n{'─' * 50}")
    print(f"  ▶ {name}")
    print(f"{'─' * 50}")


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  ✅ {name}")
        PASS += 1
    else:
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))
        FAIL += 1


def wait_enter(msg="按 Enter 继续..."):
    input(f"  ⏎ {msg}")


# ============================================================
def test_connect(comm):
    """测试串口连接"""
    step("测试 1：串口连接")

    connected = comm.is_connected()
    check("串口连接状态", connected,
          "请检查串口线和电源")
    if not connected:
        info("等待重连中...")
        for i in range(10):
            time.sleep(1)
            if comm.is_connected():
                check("串口重连成功", True)
                return True
        check("串口重连失败", False)
        return False

    return True


# ============================================================
def test_oled_emotion(comm):
    """测试 OLED 表情显示"""
    step("测试 2：OLED 表情显示")

    tests = [
        ("开心", 85),
        ("悲伤", 78),
        ("愤怒", 80),
        ("恐惧", 82),
        ("惊讶", 82),
        ("平静", 90),
    ]

    for emotion, confidence in tests:
        info(f"发送 OLED 表情: {emotion} ({confidence}%)")
        ok = comm.send_oled_emotion(emotion, confidence)
        check(f"OLED '{emotion}'", ok)
        time.sleep(1.5)

    wait_enter("确认 OLED 已依次显示 5 种表情后按 Enter")


# ============================================================
def test_oled_text(comm):
    """测试 OLED 文本显示"""
    step("测试 3：OLED 文本显示")

    texts = [
        ("你好，机器人", 0, 0),
        ("心率: 72 bpm", 0, 20),
        ("血氧: 98%", 0, 40),
    ]

    for text, x, y in texts:
        info(f"发送 OLED 文本: '{text}' @ ({x}, {y})")
        ok = comm.send_oled_text(text, x, y)
        check(f"OLED 文本 '{text[:12]}'", ok)
        time.sleep(2)

    wait_enter("确认 OLED 已显示 3 行文本后按 Enter")


# ============================================================
def test_oled_clear(comm):
    """测试 OLED 清屏"""
    step("测试 4：OLED 清屏")

    ok = comm.send_oled_clear()
    check("OLED 清屏指令", ok)

    wait_enter("确认 OLED 已清空后按 Enter")


# ============================================================
def test_servo(comm):
    """测试舵机控制"""
    step("测试 5：舵机控制")

    # 点头舵机 (servo_id=0)
    info("点头舵机: 0° → 90° → 0°")
    for angle in [0, 90, 0]:
        ok = comm.send_servo_move(0, angle, speed=5)
        check(f"点头舵机 {angle}°", ok)
        time.sleep(1)

    wait_enter("确认点头舵机已动作后按 Enter")

    # 摇头舵机 (servo_id=1)
    info("摇头舵机: 45° → 135° → 45°")
    for angle in [45, 135, 45]:
        ok = comm.send_servo_move(1, angle, speed=5)
        check(f"摇头舵机 {angle}°", ok)
        time.sleep(1)

    wait_enter("确认摇头舵机已动作后按 Enter")


# ============================================================
def test_health_data(comm):
    """测试健康数据接收"""
    step("测试 6：健康数据接收")

    received_data = []

    def on_health(health):
        received_data.append(health)
        hr = health.get('heart_rate', '?')
        hr_ok = health.get('heart_rate_valid', False)
        ox = health.get('oxygen', '?')
        ox_ok = health.get('oxygen_valid', False)
        print(f"  📊 健康数据: 心率={hr}{'✅' if hr_ok else '❌'} 血氧={ox}{'✅' if ox_ok else '❌'}")

    comm.on_health_data(on_health)

    info("等待 STM32 上报健康数据（最多 10 秒）...")
    for i in range(10):
        time.sleep(1)
        if received_data:
            break

    if received_data:
        check("收到健康数据", True, f"共收到 {len(received_data)} 条")
        latest = received_data[-1]
        check("心率字段存在", 'heart_rate' in latest)
        check("血氧字段存在", 'oxygen' in latest)
    else:
        check("收到健康数据", False, "10 秒内未收到任何数据")
        info("提示: STM32 是否已启动并配置为定期上报 TYPE_HEARTBEAT？")


# ============================================================
def loop_monitor(comm):
    """循环监控模式"""
    step("循环监控模式（按 Ctrl+C 退出）")

    def on_health(health):
        hr = health.get('heart_rate', '?')
        hr_ok = health.get('heart_rate_valid', False)
        ox = health.get('oxygen', '?')
        ox_ok = health.get('oxygen_valid', False)
        finger = "🖐" if (hr_ok or ox_ok) else "  "
        print(f"  {finger} 心率={hr:>3} {'✅' if hr_ok else '  '}  血氧={ox:>3} {'✅' if ox_ok else '  '}")

    comm.on_health_data(on_health)
    info("正在监听，每 1 秒显示一次健康数据...")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        info("监控已停止")


# ============================================================
def main():
    parser = argparse.ArgumentParser(description="STM32 通信硬件测试")
    parser.add_argument('--port', default=None,
                        help='串口设备路径（默认使用 Config 中的配置）')
    parser.add_argument('--loop', action='store_true',
                        help='进入循环监控模式（持续显示健康数据）')
    args = parser.parse_args()

    # 允许命令行覆盖串口
    if args.port:
        Config.COMM_SERIAL_PORT = args.port

    print("=" * 50)
    print("  通信模块硬件测试")
    print("=" * 50)
    print(f"  串口: {Config.COMM_SERIAL_PORT}")
    print(f"  波特率: {Config.COMM_BAUDRATE}")
    print(f"  模式: {'循环监控' if args.loop else '逐项测试'}")
    print("=" * 50)

    # 关闭模拟模式
    Config.COMM_SIMULATION_MODE = False

    comm = CommController(Config)
    comm.start()
    time.sleep(1)

    try:
        if args.loop:
            loop_monitor(comm)
        else:
            # 逐项测试
            if not test_connect(comm):
                info("串口连接失败，退出测试")
                return

            test_oled_emotion(comm)
            test_oled_text(comm)
            test_oled_clear(comm)
            test_servo(comm)
            test_health_data(comm)

            # 汇总
            print(f"\n{'=' * 50}")
            total = PASS + FAIL
            print(f"  测试汇总: ✅ {PASS} 通过, ❌ {FAIL} 失败, 共 {total} 项")
            print(f"{'=' * 50}")

            if FAIL == 0 and PASS > 0:
                info("🎉 全部通过！上位机与 STM32 通信正常。")
    finally:
        comm.stop()


if __name__ == "__main__":
    main()
