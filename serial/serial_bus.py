import serial
import threading
import time

# 1. 初始化串口
ser = serial.Serial('/dev/serial0', 115200, timeout=0.1)

# 2. 定义接收线程函数
def serial_receive_thread():
    while True:
        if ser.in_waiting > 0:
            try:
                # 读取一行数据并解码
                data = ser.readline().decode('utf-8').strip()
                if data:
                    print(f"\n[STM32 -> Pi 收到数据]: {data}")
                    # 在这里可以加入数据解析逻辑
            except Exception as e:
                print(f"解码错误: {e}")

# 3. 启动接收子线程 (设置为守护线程，主程序退出时自动退出)
rx_thread = threading.Thread(target=serial_receive_thread, daemon=True)
rx_thread.start()

print("双向串口通信已启动...")

# 4. 主线程负责主动发送指令
cmd_count = 0
try:
    while True:
        # 模拟树莓派大脑主动下发指令 (例如：控制舵机)
        cmd_str = f"SET_SERVO:1,ANGLE:45,ID:{cmd_count}"
        ser.write((cmd_str + '\n').encode('utf-8'))
        print(f"[Pi -> STM32 发送指令]: {cmd_str}")
        
        cmd_count += 1
        time.sleep(2) # 每两秒发送一次指令

except KeyboardInterrupt:
    print("程序退出")
finally:
    ser.close()
