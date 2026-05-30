#!/usr/bin/env python3
"""
最简串口通信测试 — 纯裸收发，不涉及任何协议封装

用法:
  sudo python3 test_comm_ping.py                        # 只看接收
  sudo python3 test_comm_ping.py --send                 # 发一条 "hello" 再等回复
  sudo python3 test_comm_ping.py --query                # 发送协议帧（查询传感器）
  sudo python3 test_comm_ping.py --loopback             # 自发自收回路测试
"""

import sys
import os
import time
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='/dev/serial0')
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--send', action='store_true', help='发送 "hello" 并等待回复')
    parser.add_argument('--query', action='store_true', help='发送协议帧（查询传感器）并等待回复')
    parser.add_argument('--loopback', action='store_true', help='回路测试：发→收')
    parser.add_argument('--duration', type=int, default=10)
    args = parser.parse_args()

    import serial

    print("=" * 50)
    print("  最简串口通信测试")
    print("=" * 50)
    print(f"  端口:   {args.port}")
    print(f"  波特率: {args.baud}")
    print(f"  模式:   {'回路测试' if args.loopback else '接收测试'}")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
        print(f"\n  ✅ 串口已打开: {ser.name}")
    except Exception as e:
        print(f"\n  ❌ 无法打开串口: {e}")
        print(f"     提示: 需要 sudo 权限，或检查设备路径")
        sys.exit(1)

    if args.loopback:
        # 自发自收回路测试（需要将 TX 和 RX 短接）
        print("\n  [回路测试] 发送 hello...")
        ser.write(b'hello\n')
        time.sleep(0.5)
        reply = ser.read(100)
        if reply:
            print(f"  收到: {reply!r}")
            print("  ✅ 回路测试通过 — 树莓派串口工作正常")
        else:
            print("  ❌ 回路测试失败 — 未收到回复")
            print("     提示: 请将 GPIO14(TX) 和 GPIO15(RX) 短接")
        ser.close()
        return

    if args.send:
        # 发送数据给 STM32
        msg = b'hello\n'
        print(f"\n  发送: {msg!r}")
        ser.write(msg)
        time.sleep(0.5)

    if args.query:
        # 发送协议帧（查询传感器指令）
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from communication.protocol import pack_query_sensor
        frame = pack_query_sensor()
        print(f"\n  发送查询传感器帧: {frame.hex()}")
        ser.write(frame)
        print(f"  已发送 {len(frame)} 字节")
        time.sleep(0.5)

    # 接收监听
    print(f"\n  监听 STM32 回复（{args.duration} 秒，Ctrl+C 中断）...")
    print("-" * 50)

    count = 0
    start = time.time()
    try:
        while time.time() - start < args.duration:
            data = ser.read(256)
            if data:
                count += 1
                print(f"  [{count}] 收到 {len(data)} 字节: {data!r}")
            else:
                # 每 2 秒打一个点表示还在监听
                sys.stdout.write('.')
                sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n  用户中断")
    finally:
        ser.close()

    print("-" * 50)
    if count > 0:
        print(f"  ✅ 收到 {count} 条数据，通信成功")
    else:
        print(f"  ❌ 未收到任何数据")
        print(f"     排查方向:")
        print(f"     1. 检查连线: Pi TX(GPIO14) ↔ STM32 RX, Pi RX(GPIO15) ↔ STM32 TX, GND↔GND")
        print(f"     2. 检查 STM32 是否上电、固件是否运行")
        print(f"     3. 确认波特率双方一致（默认 115200）")
        print(f"     4. 可选: 短接 TX-RX 做回路测试确认树莓派串口本身没有问题")
    print("=" * 50)


if __name__ == '__main__':
    main()
