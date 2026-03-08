# audio/speech.py
import speech_recognition as sr
import time
import threading
import queue

class SpeechModule:
    """语音识别模块，后台线程持续监听"""
    
    def __init__(self, energy_threshold=300, pause_threshold=0.8):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.running = False
        self.text_queue = queue.Queue()
        self.thread = None
        
        # 调整环境噪音
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        self.recognizer.energy_threshold = self.energy_threshold
        self.recognizer.pause_threshold = self.pause_threshold
        
        print("[SpeechModule] 初始化完成，已调整环境噪音")
        
    def _listen_loop(self):
        """后台监听循环"""
        while self.running:
            try:
                with self.microphone as source:
                    print("[SpeechModule] 正在倾听...")
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                print("[SpeechModule] 识别中...")
                text = self.recognizer.recognize_google(audio, language='zh-CN')
                print(f"[SpeechModule] 识别结果: {text}")
                
                # 将结果放入队列
                self.text_queue.put(text)
                
            except sr.WaitTimeoutError:
                # 超时，继续监听
                continue
            except sr.UnknownValueError:
                print("[SpeechModule] 无法识别")
            except sr.RequestError as e:
                print(f"[SpeechModule] 服务错误: {e}")
            except Exception as e:
                print(f"[SpeechModule] 错误: {e}")
                
    def start(self):
        """启动语音监听线程"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            print("[SpeechModule] 已启动")
            
    def stop(self):
        """停止语音监听"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        print("[SpeechModule] 已停止")
        
    def get_text(self, timeout=0):
        """获取最新的识别文本，非阻塞"""
        try:
            return self.text_queue.get_nowait()
        except queue.Empty:
            return None
            
    def get_text_blocking(self, timeout=None):
        """阻塞直到获取到一句话（用于测试）"""
        try:
            return self.text_queue.get(timeout=timeout)
        except queue.Empty:
            return None