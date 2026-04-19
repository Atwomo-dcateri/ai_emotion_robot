# hardware/oled_simulator.py 中的 OLEDSimulator 类

class OLEDSimulator:
    """OLED屏幕模拟器"""
    
    def __init__(self, width=128, height=64, use_ascii=False):
        self.width = width
        self.height = height
        self.current_display = None
        self.brightness = 100
        self.use_ascii = use_ascii  # 新增：是否使用ASCII模式
        
        # 表情符号映射（保留，用于非ASCII模式）
        self.emotion_faces = {
            '愤怒': '😠',
            '厌恶': '😖',
            '恐惧': '😨',
            '开心': '😊',
            '悲伤': '😢',
            '惊讶': '😲',
            '平静': '😐',
            '默认': '🤖'
        }
        
        # 新增：ASCII表情艺术
        self.emotion_ascii = {
            '愤怒': [
                "   😠   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯  ╰╮ ",
                "╰╮--╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            '恐惧': [
                "   😨   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯OO╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            '悲伤': [
                "   😢   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯  ╰╮ ",
                "╰╮__╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            '开心': [
                "   😊   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯  ╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            '惊讶': [
                "   😲   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯OO╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            '平静': [
                "   😐   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯--╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            '默认': [
                "   🤖   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯[]╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ]
        }
        
        print(f"[OLED模拟] 已初始化 {width}x{height} 屏幕 (ASCII模式: {use_ascii})")
    
    def show_face(self, emotion, confidence=None):
        """
        显示表情符号
        :param emotion: 情绪名称（中文）
        :param confidence: 置信度（可选）
        """
        if self.use_ascii:
            # ASCII模式
            ascii_face = self.emotion_ascii.get(emotion, self.emotion_ascii['默认'])
            
            print("\n" + "-" * 30)
            print("[OLED屏幕] ASCII表情:")
            for line in ascii_face:
                print(f"          {line}")
            if confidence:
                print(f"          置信度: {confidence:.1f}%")
            print("-" * 30)
            
        else:
            # Emoji模式
            face = self.emotion_faces.get(emotion, self.emotion_faces['默认'])
            self.current_display = f"{face} {emotion}"
            
            print("\n" + "-" * 20)
            print(f"[OLED屏幕]")
            print(f"表情: {face} {emotion}")
            if confidence:
                print(f"置信度: {confidence:.1f}%")
            print("-" * 20)
        
        return True
    
    def show_animation(self, emotion, frames=3):
        """显示简单动画"""
        if self.use_ascii:
            print(f"[OLED动画] 播放 {emotion} 动画 {frames}帧")
            # ASCII动画可以简单显示几次表情
            for i in range(frames):
                self.show_face(emotion)
                import time
                time.sleep(0.3)
        else:
            # 原有的emoji动画逻辑
            pass
        
        return True
    
    # 其他方法保持不变...
    
    def show_text(self, text, line=0):
        """
        显示文本
        :param text: 要显示的文本
        :param line: 行号（0-7）
        """
        print(f"[OLED屏幕] 行{line}: {text}")
        return True
    
    def clear(self):
        """清空屏幕"""
        self.current_display = None
        print("[OLED屏幕] 已清空")
        return True
    
    def show_ascii_face(self, emotion):
        """
        显示ASCII艺术风格的人脸（备选）
        """
        ascii_face = self.emotion_ascii.get(emotion, self.emotion_ascii['默认'])
        
        print("[OLED屏幕] ASCII显示:")
        for line in ascii_face:
            print(f"          {line}")
        
        return True


class HardwareSimulator:
    """硬件模拟器集合（OLED版）"""
    
    def __init__(self, use_ascii=False):
        """
        初始化硬件模拟器
        :param use_ascii: 是否使用ASCII替代emoji
        """
        self.oled = OLEDSimulator(use_ascii=use_ascii)  # 传递参数
        self.servo = None
        self.speaker = None
        self.use_ascii = use_ascii
        
        print(f"[硬件模拟] OLED屏幕已初始化 (ASCII模式: {use_ascii})")
        
    def init_servo(self):
        """初始化舵机（需要时再创建）"""
        if not self.servo:
            # 这里可以导入舵机模块
            print("[硬件模拟] 舵机模块未实现")
    
    def init_speaker(self):
        """初始化扬声器（需要时再创建）"""
        if not self.speaker:
            # 这里可以导入扬声器模块
            print("[硬件模拟] 扬声器模块未实现")
    
    def execute_action(self, action):
        """
        执行动作指令
        action: 字典，包含要执行的动作
        """
        action_type = action.get('type', 'none')
        
        if action_type == 'oled':
            emotion = action.get('emotion')
            confidence = action.get('confidence')
            effect = action.get('effect', 'show')
            
            if effect == 'show':
                if emotion:
                    self.oled.show_face(emotion, confidence)
                else:
                    text = action.get('text', '')
                    if text:
                        self.oled.show_text(text)
                        
            elif effect == 'animation':
                frames = action.get('frames', 3)
                self.oled.show_animation(emotion, frames)
                
            elif effect == 'ascii':
                if self.use_ascii and emotion:
                    self.oled.show_ascii_face(emotion)
                    
            elif effect == 'clear':
                self.oled.clear()
        
        # 其他硬件模块预留
        elif action_type == 'servo':
            print(f"[舵机模拟] 动作: {action}")
        
        elif action_type == 'speak':
            print(f"[语音模拟] 说话: {action.get('text', '')}")
        
        elif action_type == 'combined':
            print(f"[硬件模拟] 组合动作: {action.get('name', 'unknown')}")
            if 'oled' in action:
                self.execute_action(action['oled'])
            if 'servo' in action:
                self.execute_action(action['servo'])
            if 'speak' in action:
                self.execute_action(action['speak'])