# decision/engine_oled.py
"""
情感决策引擎 - OLED版
根据用户状态决定机器人反应（OLED显示表情）
"""

class DecisionEngine:
    """情感决策引擎"""
    
    def __init__(self, use_ascii=False):
        self.use_ascii = use_ascii
        
        # 情绪到表情的映射（保留，可能用于显示）
        self.emotion_faces = {
            '愤怒': '😠',
            '厌恶': '😖',
            '恐惧': '😨',
            '开心': '😊',
            '悲伤': '😢',
            '惊讶': '😲',
            '平静': '😐'
        }
        
        # 情绪到语音的映射（保持不变）
        self.emotion_speeches = {
            '愤怒': "请冷静一下",
            '厌恶': "不喜欢这个吗",
            '恐惧': "别害怕，我在这里",
            '开心': "看到你开心我也很高兴",
            '悲伤': "别难过，一切都会好起来的",
            '惊讶': "哇，真的吗",
            '平静': "今天过得怎么样"
        }
        
        # 情绪到动画的映射
        self.emotion_animations = {
            '愤怒': 3,
            '开心': 5,
            '惊讶': 4,
            '悲伤': 3
        }
    
    def decide(self, user_state):
        """
        根据用户状态决定机器人反应
        user_state: 包含 face_emotion 的字典
        """
        actions = []
        
        # 获取情绪
        emotion = None
        confidence = 0
        if user_state.get('face_emotion'):
            emotion = user_state['face_emotion'].get('emotion')
            confidence = user_state['face_emotion'].get('confidence', 0)
            
            # 置信度太低时不反应
            if confidence < 50:
                return [{'type': 'none', 'reason': 'confidence too low'}]
        
        if emotion:
            # OLED显示表情
            oled_action = {
                'type': 'oled',
                'effect': 'show',
                'emotion': emotion,
                'confidence': confidence
            }
            
            # 如果是高置信度，播放动画
            if confidence > 90 and emotion in self.emotion_animations:
                oled_action = {
                    'type': 'oled',
                    'effect': 'animation',
                    'emotion': emotion,
                    'frames': self.emotion_animations[emotion]
                }
            
            # 如果使用ASCII模式
            if self.use_ascii:
                oled_action['effect'] = 'ascii'
            
            actions.append(oled_action)
            
            # 语音动作
            speech = self.emotion_speeches.get(emotion, "你好")
            actions.append({
                'type': 'speak',
                'text': speech
            })
            
        else:
            # 没检测到人脸时显示默认表情
            actions.append({
                'type': 'oled',
                'effect': 'show',
                'emotion': '默认',
                'text': '等待中...'
            })
        
        return actions
        
    def decide_pretty(self, user_state):
        """返回可读的决策结果"""
        actions = self.decide(user_state)
        
        if not actions or actions[0].get('type') == 'none':
            return "无反应"
        
        result = []
        for action in actions:
            if action['type'] == 'oled':
                emotion = action.get('emotion', '')
                effect = action.get('effect', 'show')
                
                if self.use_ascii:
                    # ASCII模式显示文本
                    if effect == 'animation':
                        result.append(f"OLED动画: {emotion}")
                    else:
                        result.append(f"OLED: [{emotion}]")
                else:
                    # Emoji模式
                    face = self.emotion_faces.get(emotion, '🤖')
                    if effect == 'animation':
                        result.append(f"OLED动画: {face} {emotion}")
                    else:
                        result.append(f"OLED: {face} {emotion}")
                        
            elif action['type'] == 'speak':
                result.append(f"语音: \"{action.get('text', '')}\"")
        
        return " | ".join(result)