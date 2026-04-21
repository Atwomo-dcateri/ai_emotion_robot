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
            '痛苦': '😣',
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
            '痛苦': [
                "   😣   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯  ╰╮ ",
                "╰╮--╭╯ ",
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
        显示表情符号 - 增强版
        :param emotion: 情绪名称（中文）
        :param confidence: 置信度（可选）
        """
        if self.use_ascii:
            # ASCII模式 - 增强显示效果
            ascii_face = self.emotion_ascii.get(emotion, self.emotion_ascii['默认'])
            
            # 根据置信度调整显示效果
            display_confidence = confidence or 75.0
            
            # 高置信度时添加视觉增强效果
            if display_confidence > 80:
                border_char = "█"
                title = f"[OLED屏幕] 🎯 高精度表情检测"
            elif display_confidence > 60:
                border_char = "▓"
                title = f"[OLED屏幕] ✅ 表情检测"
            else:
                border_char = "░"
                title = f"[OLED屏幕] ❓ 表情检测"
            
            print(f"\n{border_char * 40}")
            print(f"{title}")
            print(f"{border_char * 40}")
            
            # 显示表情艺术
            for line in ascii_face:
                print(f"          {line}")
            
            # 显示置信度和状态信息
            if confidence:
                confidence_bar = self._create_confidence_bar(confidence)
                print(f"          置信度: {confidence_bar} {confidence:.1f}%")
            
            # 添加表情描述
            emotion_descriptions = {
                '开心': '😄 检测到笑容！',
                '悲伤': '😢 看起来有些难过',
                '痛苦': '😣 看起来很痛苦',
                '愤怒': '😠 似乎不太高兴',
                '恐惧': '😨 感到害怕或紧张',
                '惊讶': '😲 哇！很惊讶！',
                '平静': '😐 保持平静',
                '默认': '🤖 等待表情...'
            }
            description = emotion_descriptions.get(emotion, f'检测到{emotion}表情')
            print(f"          {description}")
            
            print(f"{border_char * 40}")
            
        else:
            # Emoji模式 - 保持原有逻辑但增强
            face = self.emotion_faces.get(emotion, self.emotion_faces['默认'])
            self.current_display = f"{face} {emotion}"
            
            print("\n" + "=" * 25)
            print(f"[OLED屏幕 - 表情模式]")
            print(f"表情: {face} {emotion}")
            if confidence:
                print(f"置信度: {confidence:.1f}%")
            print("=" * 25)
        
        return True
    
    def show_emotion(self, emotion, confidence=75.0):
        """
        显示表情 (兼容RealOLEDHardware接口)
        :param emotion: 表情类型
        :param confidence: 置信度
        """
        return self.show_face(emotion, confidence)
    
    def _create_confidence_bar(self, confidence):
        """
        创建置信度可视化条形图
        :param confidence: 置信度值 (0-100)
        :return: 条形图字符串
        """
        bar_length = 10
        filled = int((confidence / 100) * bar_length)
        empty = bar_length - filled
        
        # 使用不同字符表示不同置信度级别
        if confidence >= 80:
            filled_char = "█"
            empty_char = "░"
        elif confidence >= 60:
            filled_char = "▓"
            empty_char = "░"
        else:
            filled_char = "▒"
            empty_char = "░"
        
        bar = filled_char * filled + empty_char * empty
        return f"[{bar}]"
    
    def show_animation(self, emotion, frames=3, duration=0.3):
        """
        显示表情动画 - 增强版
        :param emotion: 表情类型
        :param frames: 动画帧数
        :param duration: 每帧持续时间
        """
        if self.use_ascii:
            print(f"\n[OLED动画] 🎬 播放 {emotion} 动画 ({frames}帧)")
            
            # 为不同表情创建不同的动画效果
            if emotion == '眨眼':
                self._play_blink_animation(frames, duration)
            elif emotion == '开心':
                self._play_happy_animation(frames, duration)
            elif emotion == '惊讶':
                self._play_surprise_animation(frames, duration)
            else:
                # 默认动画：简单闪烁
                for i in range(frames):
                    self.show_face(emotion, confidence=70 + i * 5)
                    import time
                    time.sleep(duration)
        else:
            # 原有的emoji动画逻辑
            print(f"[OLED动画] 播放 {emotion} 动画 {frames}帧")
        
        return True
    
    def _play_blink_animation(self, frames, duration):
        """播放眨眼动画"""
        import time
        
        # 眨眼动画帧
        blink_frames = [
            # 睁眼
            [
                "   😐   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯--╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            # 半闭眼
            [
                "   😐   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯--╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            # 闭眼
            [
                "   😐   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯--╰╮ ",
                "╰╮--╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            # 半闭眼
            [
                "   😐   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯--╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            # 睁眼
            [
                "   😐   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯--╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ]
        ]
        
        for i in range(min(frames, len(blink_frames))):
            print(f"\n{'█' * 40}")
            print("[OLED动画] 👀 眨眼动画")
            print(f"{'█' * 40}")
            
            for line in blink_frames[i]:
                print(f"          {line}")
            print(f"          帧 {i+1}/{frames}")
            print(f"{'█' * 40}")
            
            time.sleep(duration)
    
    def _play_happy_animation(self, frames, duration):
        """播放开心动画"""
        import time
        
        # 开心动画帧 - 嘴巴逐渐变大
        happy_frames = [
            # 小笑
            [
                "   😊   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯  ╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            # 中笑
            [
                "   😊   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯\\╱╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            # 大笑
            [
                "   😊   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯◉◉╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            # 最大笑
            [
                "   😄   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯○○╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ]
        ]
        
        for i in range(min(frames, len(happy_frames))):
            print(f"\n{'█' * 40}")
            print("[OLED动画] 😄 开心动画")
            print(f"{'█' * 40}")
            
            for line in happy_frames[i]:
                print(f"          {line}")
            print(f"          帧 {i+1}/{frames}")
            print(f"{'█' * 40}")
            
            time.sleep(duration)
    
    def _play_surprise_animation(self, frames, duration):
        """播放惊讶动画"""
        import time
        
        # 惊讶动画帧 - 眼睛逐渐睁大
        surprise_frames = [
            # 正常
            [
                "   😐   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯--╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            # 轻微惊讶
            [
                "   😲   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯○○╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            # 中等惊讶
            [
                "   😲   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯◉◉╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ],
            # 非常惊讶
            [
                "   😱   ",
                "  ╭╮   ",
                " ╭╯╰╮  ",
                "╭╯◎◎╰╮ ",
                "╰╮  ╭╯ ",
                " ╰╮╭╯  ",
                "  ╰╯   "
            ]
        ]
        
        for i in range(min(frames, len(surprise_frames))):
            print(f"\n{'█' * 40}")
            print("[OLED动画] 😲 惊讶动画")
            print(f"{'█' * 40}")
            
            for line in surprise_frames[i]:
                print(f"          {line}")
            print(f"          帧 {i+1}/{frames}")
            print(f"{'█' * 40}")
            
            time.sleep(duration)
    
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
        
        return True
    
    def show_emotion_transition(self, from_emotion, to_emotion, steps=3, confidence=75.0):
        """
        显示表情过渡动画
        :param from_emotion: 起始表情
        :param to_emotion: 目标表情
        :param steps: 过渡步数
        :param confidence: 置信度
        """
        import time
        
        print(f"\n[OLED过渡] 🎭 {from_emotion} → {to_emotion} ({steps}步过渡)")
        
        for step in range(steps + 1):
            # 计算当前表情的混合权重
            progress = step / steps
            
            # 简单过渡：交替显示两个表情
            if step % 2 == 0:
                current_emotion = from_emotion
            else:
                current_emotion = to_emotion
            
            self.oled.show_face(current_emotion, confidence)
            time.sleep(0.2)
        
        # 最终显示目标表情
        self.oled.show_face(to_emotion, confidence)
        print(f"[OLED过渡] ✅ 过渡完成")
        return True
    
    def show_emotion_intensity(self, emotion, base_confidence=60.0, max_confidence=95.0, steps=5):
        """
        显示表情强度变化动画
        :param emotion: 表情类型
        :param base_confidence: 基础置信度
        :param max_confidence: 最大置信度
        :param steps: 变化步数
        """
        import time
        
        print(f"\n[OLED强度] 📈 {emotion} 强度变化 ({steps}级)")
        
        confidence_range = max_confidence - base_confidence
        
        for step in range(steps + 1):
            current_confidence = base_confidence + (confidence_range * step / steps)
            self.oled.show_face(emotion, current_confidence)
            time.sleep(0.3)
        
        print(f"[OLED强度] ✅ 强度变化完成")
    
    def show_status_display(self, status_info):
        """
        显示状态信息面板
        :param status_info: 状态信息字典
        """
        print(f"\n{'█' * 50}")
        print("[OLED状态面板] 📊 系统状态")
        print(f"{'█' * 50}")
        
        # 显示各种状态信息
        if 'emotion' in status_info:
            emotion = status_info['emotion']
            confidence = status_info.get('confidence', 0)
            print(f"当前表情: {emotion} ({confidence:.1f}%)")
        
        if 'face_count' in status_info:
            face_count = status_info['face_count']
            print(f"检测人脸: {face_count} 个")
        
        if 'uptime' in status_info:
            uptime = status_info['uptime']
            print(f"运行时间: {uptime}")
        
        if 'cpu_temp' in status_info:
            cpu_temp = status_info['cpu_temp']
            print(f"CPU温度: {cpu_temp}°C")
        
        if 'memory' in status_info:
            memory = status_info['memory']
            print(f"内存使用: {memory}%")
        
        print(f"{'█' * 50}")
    
    def create_emotion_sequence(self, emotion_sequence, interval=1.0):
        """
        创建表情序列动画
        :param emotion_sequence: 表情序列列表
        :param interval: 每个表情的显示间隔
        """
        import time
        
        print(f"\n[OLED序列] 🎬 表情序列动画 ({len(emotion_sequence)}个表情)")
        
        for i, emotion_data in enumerate(emotion_sequence):
            if isinstance(emotion_data, dict):
                emotion = emotion_data.get('emotion', '平静')
                confidence = emotion_data.get('confidence', 75.0)
                duration = emotion_data.get('duration', interval)
            else:
                emotion = emotion_data
                confidence = 75.0
                duration = interval
            
            print(f"[序列 {i+1}/{len(emotion_sequence)}] 显示: {emotion}")
            self.oled.show_face(emotion, confidence)
            time.sleep(duration)
        
        print(f"[OLED序列] ✅ 序列播放完成")
        return True