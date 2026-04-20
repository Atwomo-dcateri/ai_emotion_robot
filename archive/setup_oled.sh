#!/bin/bash
# setup_oled.sh - OLED显示屏设置脚本
# 用于在Raspberry Pi上配置SSD1306 OLED显示屏

echo "========================================"
echo "AI Emotion Robot - OLED设置脚本"
echo "========================================"

# 检查是否为root用户
if [[ $EUID -eq 0 ]]; then
   echo "请不要使用root用户运行此脚本"
   exit 1
fi

echo "检查系统环境..."

# 检查Raspberry Pi型号
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "警告: 未检测到Raspberry Pi，可能无法正常工作"
fi

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 启用I2C接口
echo "启用I2C接口..."
sudo raspi-config nonint do_i2c 0

# 检查I2C是否启用
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "添加I2C配置到 /boot/config.txt"
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt > /dev/null
fi

# 安装系统依赖
echo "安装系统依赖..."
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip i2c-tools

# 检查I2C设备
echo "检查I2C设备..."
i2c_devices=$(i2cdetect -y 1 2>/dev/null | grep -E "3[0-9a-f] [0-9a-f]" | wc -l)
if [ $i2c_devices -gt 0 ]; then
    echo "✅ 检测到 $i2c_devices 个I2C设备"
    echo "I2C总线扫描结果:"
    i2cdetect -y 1
else
    echo "⚠️  未检测到I2C设备，请检查硬件连接"
fi

# 安装Python依赖
echo "安装Python依赖..."
cd /home/afr/project/ai_emotion_robot
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# 测试OLED驱动
echo "测试OLED驱动..."
python3 -c "
try:
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306
    print('✅ luma.oled库安装成功')
    
    # 尝试初始化设备
    try:
        serial = i2c(port=1, address=0x3C)
        device = ssd1306(serial, width=128, height=64)
        device.clear()
        print('✅ OLED设备初始化成功')
    except Exception as e:
        print(f'⚠️  OLED设备初始化失败: {e}')
        print('可能是硬件未连接或地址错误')
        
except ImportError as e:
    print(f'❌ luma.oled库安装失败: {e}')
"

echo ""
echo "========================================"
echo "OLED设置完成！"
echo "========================================"
echo ""
echo "使用方法:"
echo "1. 硬件连接:"
echo "   - OLED VCC → Raspberry Pi 3.3V"
echo "   - OLED GND → Raspberry Pi GND"
echo "   - OLED SCL → Raspberry Pi SCL (GPIO 3)"
echo "   - OLED SDA → Raspberry Pi SDA (GPIO 2)"
echo ""
echo "2. 运行程序:"
echo "   python3 main_oled_real.py              # 真实OLED模式"
echo "   python3 main_oled_real.py --simulator  # 模拟器模式"
echo ""
echo "3. 测试OLED:"
echo "   python3 test_oled_driver.py"
echo ""
echo "注意事项:"
echo "- 如果OLED不工作，检查I2C地址 (可能需要0x3D)"
echo "- 使用 --i2c-address=0x3D 参数指定不同地址"
echo "- 确保OLED模块支持SSD1306芯片"
echo ""