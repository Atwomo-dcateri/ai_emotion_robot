# decision/llm_cloud.py
"""
云端LLM情感决策引擎 - 调用DeepSeek API生成智能反应
"""

import requests
import json
import os

class CloudLLMEngine:
    """云端LLM决策引擎（DeepSeek API）"""
    
    def __init__(self, api_key=None, api_url="https://api.deepseek.com/v1/chat/completions"):
        """
        初始化云端LLM引擎
        :param api_key: DeepSeek API密钥，如果不提供则从环境变量读取
        :param api_url: API地址
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("请提供DeepSeek API密钥，或设置环境变量 DEEPSEEK_API_KEY")
        
        self.api_url = api_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 系统提示词 - 定义LLM的角色和行为
        self.system_prompt = """你是一个情感交互机器人的决策中枢。你的任务是根据用户的多模态状态，生成机器人的反应。

用户状态包含：
- face_emotion: 面部情绪（如开心、悲伤、愤怒、惊讶、平静等）
- speech_text: 用户说的话（如果有）
- heart_rate: 心率状态（预留）

你必须以JSON格式输出机器人的反应，包含以下字段：
{
    "emotion": "机器人的情绪（开心/同情/惊讶/平静等）",
    "speech": "机器人要说的话（简短自然，1-2句话，用中文）",
    "oled": "要显示的ASCII表情符号（开心:😊, 悲伤:😢, 愤怒:😠, 惊讶:😲, 平静:😐, 默认:🤖）",
    "action": "机器人的动作（nod:点头, shake:摇头, none:无）"
}

要求：
1. 反应要自然、有同理心
2. 根据用户情绪选择合适的回应
3. 如果用户说话，要结合说话内容
4. 输出必须是合法的JSON格式，不要包含其他文字
"""
        
        print("[CloudLLM] 初始化完成，使用DeepSeek API")
    
    def _build_messages(self, user_state):
        """构建消息列表"""
        # 提取用户状态
        face_info = "未知"
        speech = "无"
        
        if user_state.get('face_emotion'):
            emotion = user_state['face_emotion'].get('emotion', '未知')
            confidence = user_state['face_emotion'].get('confidence', 0)
            face_info = f"{emotion}(置信度:{confidence:.0f}%)"
        
        if user_state.get('speech_text'):
            speech = user_state['speech_text']
        
        # 构建用户输入
        user_content = f"""当前用户状态：
- 面部情绪：{face_info}
- 用户说话："{speech}"

请生成机器人的反应（JSON格式）："""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content}
        ]
        return messages
    
    def _call_api(self, messages):
        """调用DeepSeek API"""
        payload = {
            "model": "deepseek-chat",  # 使用通用模型
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500,
            "response_format": {"type": "json_object"}  # 强制返回JSON（DeepSeek支持）
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # 提取返回内容
            content = result['choices'][0]['message']['content']
            
            # 尝试解析JSON
            try:
                return json.loads(content)
            except:
                print(f"[CloudLLM] 返回不是合法JSON: {content}")
                return None
                
        except Exception as e:
            print(f"[CloudLLM] API调用失败: {e}")
            return None
    
    def decide(self, user_state):
        """
        根据用户状态生成机器人反应
        """
        messages = self._build_messages(user_state)
        llm_response = self._call_api(messages)
        
        if llm_response and isinstance(llm_response, dict):
            return self._format_actions(llm_response)
        else:
            # API失败时使用备选规则
            return self._fallback(user_state)
    
    def _format_actions(self, llm_output):
        """格式化LLM输出为标准动作"""
        actions = []
        
        # OLED显示（使用LLM返回的emoji或文字）
        oled_emoji = llm_output.get('oled', '🤖')
        actions.append({
            'type': 'oled',
            'effect': 'show',
            'emotion': oled_emoji,  # 直接显示emoji
            'text': llm_output.get('emotion', '平静')
        })
        
        # 语音输出
        speech = llm_output.get('speech', '你好')
        actions.append({
            'type': 'speak',
            'text': speech
        })
        
        # 动作输出
        action_type = llm_output.get('action', 'none')
        if action_type != 'none':
            actions.append({
                'type': 'servo',
                'move': action_type,
                'times': 1
            })
        
        return actions
    
    def _fallback(self, user_state):
        """API失败时的备选规则"""
        actions = []
        
        if user_state.get('face_emotion'):
            emotion = user_state['face_emotion'].get('emotion', '平静')
            
            # 简单映射
            emoji_map = {
                '愤怒': '😠', '开心': '😊', '悲伤': '😢',
                '惊讶': '😲', '平静': '😐'
            }
            speech_map = {
                '愤怒': "请冷静一下",
                '开心': "看到你开心我也很高兴",
                '悲伤': "别难过",
                '惊讶': "哇",
                '平静': "你好"
            }
            
            oled = emoji_map.get(emotion, '🤖')
            speech = speech_map.get(emotion, "你好")
            
            actions.append({'type': 'oled', 'effect': 'show', 'emotion': oled})
            actions.append({'type': 'speak', 'text': speech})
        
        return actions
    
    def decide_pretty(self, user_state):
        """返回可读的决策结果"""
        actions = self.decide(user_state)
        
        result = []
        for action in actions:
            if action['type'] == 'oled':
                result.append(f"OLED:{action.get('emotion', '')}")
            elif action['type'] == 'speak':
                result.append(f"语音:\"{action.get('text', '')}\"")
            elif action['type'] == 'servo':
                result.append(f"动作:{action.get('move', '')}")
        
        return " | ".join(result)