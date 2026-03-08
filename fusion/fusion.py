# fusion/fusion.py
import time

class FusionModule:
    """多模态信息融合模块"""
    
    def __init__(self, vision_module, speech_module):
        self.vision = vision_module
        self.speech = speech_module
        self.last_user_state = None
        
    def get_user_state(self):
        """获取当前用户状态"""
        state = {
            'timestamp': time.time(),
            'face_emotion': None,
            'speech_text': None,
            'heart_rate': None  # 预留生理模块
        }
        
        # 获取视觉结果
        vision_result = self.vision.get_emotion()
        if vision_result:
            state['face_emotion'] = {
                'emotion': vision_result['emotion'],
                'emotion_cn': vision_result['emotion_cn'],
                'confidence': vision_result['confidence']
            }
        
        # 获取语音结果（如果有新的话）
        speech_text = self.speech.get_text()
        if speech_text:
            state['speech_text'] = speech_text
        
        self.last_user_state = state
        return state
        
    def get_pretty_state(self):
        """返回可打印的状态字符串"""
        state = self.get_user_state()
        lines = []
        lines.append(f"时间: {time.strftime('%H:%M:%S', time.localtime(state['timestamp']))}")
        
        if state['face_emotion']:
            fe = state['face_emotion']
            lines.append(f"面部情绪: {fe['emotion_cn']} ({fe['confidence']:.1f}%)")
        else:
            lines.append("面部情绪: 未检测到人脸")
            
        if state['speech_text']:
            lines.append(f"语音输入: {state['speech_text']}")
        else:
            lines.append("语音输入: 无")
            
        return "\n".join(lines)