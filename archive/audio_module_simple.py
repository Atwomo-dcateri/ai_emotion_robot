# audio/audio_module.py
"""
AI情感机器人音频模块 - 简化版
使用系统命令进行录音和播放，避免复杂的Python音频库
"""

import os
import subprocess
import threading
import time
from typing import Optional, Callable
from gtts import gTTS
import playsound


class AudioRecorder:
    """音频录音器 - 使用系统arecord命令"""

    def __init__(self, device="hw:3,0", sample_rate=44100, channels=1):
        self.device = device
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.current_process = None

    def start_recording(self, filename: str, duration: Optional[int] = None) -> bool:
        """开始录音

        Args:
            filename: 输出文件名
            duration: 录音时长(秒)，None表示手动停止

        Returns:
            bool: 是否成功开始录音
        """
        if self.is_recording:
            print("[AudioRecorder] 已经在录音中")
            return False

        try:
            cmd = [
                "arecord",
                "-D", self.device,
                "-f", "cd",  # CD质量: 16位, 44100Hz
                "-c", str(self.channels),
                "-t", "wav",
                filename
            ]

            if duration:
                cmd.extend(["-d", str(duration)])

            print(f"[AudioRecorder] 开始录音: {' '.join(cmd)}")
            self.current_process = subprocess.Popen(cmd)
            self.is_recording = True
            return True

        except Exception as e:
            print(f"[AudioRecorder] 录音启动失败: {e}")
            return False

    def stop_recording(self) -> bool:
        """停止录音

        Returns:
            bool: 是否成功停止
        """
        if not self.is_recording:
            return False

        try:
            if self.current_process:
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
            self.is_recording = False
            print("[AudioRecorder] 录音已停止")
            return True
        except Exception as e:
            print(f"[AudioRecorder] 停止录音失败: {e}")
            return False

    def record_for_duration(self, filename: str, duration: int) -> bool:
        """录音指定时长

        Args:
            filename: 输出文件名
            duration: 录音时长(秒)

        Returns:
            bool: 是否成功录音
        """
        if not self.start_recording(filename, duration):
            return False

        # 等待录音完成
        time.sleep(duration + 1)
        return self.stop_recording()


class TextToSpeech:
    """文字转语音合成器 - 使用gTTS"""

    def __init__(self, language="zh-CN", slow=False):
        self.language = language
        self.slow = slow

    def speak(self, text: str, filename: Optional[str] = None, play_immediately=True) -> bool:
        """将文字转换为语音

        Args:
            text: 要合成的文字
            filename: 输出文件名，默认使用临时文件
            play_immediately: 是否立即播放

        Returns:
            bool: 是否成功
        """
        try:
            if not filename:
                filename = f"temp_speech_{int(time.time())}.mp3"

            # 生成语音文件
            tts = gTTS(text=text, lang=self.language, slow=self.slow)
            tts.save(filename)
            print(f"[TextToSpeech] 语音文件已生成: {filename}")

            if play_immediately:
                self._play_audio(filename)
                # 如果是临时文件，播放后删除
                if filename.startswith("temp_speech_"):
                    os.remove(filename)

            return True

        except Exception as e:
            print(f"[TextToSpeech] 语音合成失败: {e}")
            return False

    def _play_audio(self, filename: str):
        """播放音频文件"""
        try:
            playsound.playsound(filename)
            print("[TextToSpeech] 播放完成")
        except Exception as e:
            print(f"[TextToSpeech] 播放失败: {e}")


class SpeechRecognizer:
    """语音识别器 - 使用系统命令调用百度/腾讯API (简化版)"""

    def __init__(self, language="zh-CN"):
        self.language = language
        print("[SpeechRecognizer] 初始化完成 (使用系统命令模式)")

    def recognize_from_file(self, filename: str) -> Optional[str]:
        """从音频文件识别语音 (简化实现)

        Args:
            filename: 音频文件路径

        Returns:
            Optional[str]: 识别结果，失败返回None
        """
        print(f"[SpeechRecognizer] 处理文件: {filename}")

        # 这里可以集成各种语音识别服务
        # 暂时返回模拟结果用于测试
        print("[SpeechRecognizer] 注意: 当前使用模拟识别结果")
        return "你好，我是AI情感机器人"

    def listen_once(self, timeout=5) -> Optional[str]:
        """监听一次语音输入 (简化实现)

        Args:
            timeout: 超时时间(秒)

        Returns:
            Optional[str]: 识别结果
        """
        print(f"[SpeechRecognizer] 监听 {timeout} 秒...")

        # 暂时返回模拟结果
        time.sleep(1)  # 模拟处理时间
        print("[SpeechRecognizer] 注意: 当前使用模拟识别结果")
        return "你好"


class AudioModule:
    """完整的音频处理模块 - 简化版"""

    def __init__(self):
        self.recorder = AudioRecorder()
        self.recognizer = SpeechRecognizer()
        self.tts = TextToSpeech()
        print("[AudioModule] 音频模块初始化完成 (简化版)")

    def record_and_recognize(self, duration=3) -> Optional[str]:
        """录音并识别语音

        Args:
            duration: 录音时长(秒)

        Returns:
            Optional[str]: 识别结果
        """
        temp_file = f"temp_record_{int(time.time())}.wav"

        try:
            # 录音
            if not self.recorder.record_for_duration(temp_file, duration):
                return None

            # 等待文件写入完成
            time.sleep(0.5)

            # 识别
            text = self.recognizer.recognize_from_file(temp_file)
            return text

        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def speak(self, text: str):
        """语音合成并播放

        Args:
            text: 要播放的文字
        """
        self.tts.speak(text)

    def test_audio_devices(self) -> dict:
        """测试音频设备状态

        Returns:
            dict: 设备状态信息
        """
        status = {
            "recorder_available": False,
            "microphone_available": False,
            "speaker_available": False
        }

        # 测试录音设备
        try:
            result = subprocess.run(["arecord", "-l"],
                                  capture_output=True, text=True, timeout=5)
            status["recorder_available"] = "USB PnP Sound Device" in result.stdout
        except:
            pass

        # 测试麦克风 (简化检查)
        status["microphone_available"] = status["recorder_available"]

        # 测试扬声器
        try:
            result = subprocess.run(["aplay", "-l"],
                                  capture_output=True, text=True, timeout=5)
            status["speaker_available"] = len(result.stdout.strip()) > 0
        except:
            pass

        return status