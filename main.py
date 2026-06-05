#!/usr/bin/env python3
"""
AI 情感机器人 — 主程序

工作模式：
  1. OLED 始终显示摄像头检测到的人脸表情（实时）
  2. 说唤醒词"你好"后，可与 LLM 语音聊天
  3. 心率异常时主动语音提醒（有冷却，不阻塞交互）

运行:
  python3 main.py
"""

import sys
import os
import time
import signal
import logging

from config import Config

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from vision import VisionModule
from audio import AudioController
from communication import CommController
from fusion import FusionModule
from decision import DecisionController

# ============================================================
shutdown_flag = False


def signal_handler(sig, frame):
    global shutdown_flag
    logger.info("收到退出信号，正在清理...")
    shutdown_flag = True


def safe_call(fn, *args, name="", default=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.warning(f"{name} 异常: {e}")
        return default


# ============================================================
def main():
    global shutdown_flag

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 50)
    logger.info("AI 情感机器人启动中...")
    logger.info("=" * 50)

    # ========== 初始化 ==========
    logger.info("初始化视觉模块...")
    vision = VisionModule(Config)
    if not vision.start():
        logger.warning("视觉服务启动失败")

    logger.info("初始化语音模块...")
    audio = AudioController(Config)
    if not audio.start():
        logger.warning("语音服务启动失败")

    logger.info("初始化通信模块...")
    comm = CommController(Config)
    if not comm.start():
        logger.warning("通信服务启动失败")

    logger.info("初始化融合模块...")
    fusion = FusionModule(vision if vision.is_running() else None,
                          audio, comm, Config)

    logger.info("初始化决策模块...")
    decision = DecisionController(Config)
    llm_ready = decision._llm_engine is not None and decision._llm_engine.is_ready()
    logger.info(f"决策模式: {'LLM + 规则引擎' if llm_ready else '仅规则引擎'}")

    time.sleep(1)
    logger.info("所有服务已启动，进入主循环")
    logger.info("=" * 50)

    # ========== 状态追踪 ==========
    last_oled_emotion = None
    last_oled_clear = False
    last_health_alert_time = 0      # 上次健康告警时间（冷却用）
    HEALTH_ALERT_COOLDOWN = 8.0      # 同类型告警最少间隔（秒）

    # ========== 主循环 ==========
    try:
        while not shutdown_flag:
            now = time.time()

            # ---- 1. 获取融合状态 ----
            state = safe_call(fusion.get_user_state, name="get_user_state",
                              default={
                                  'has_face': False, 'face_emotion': None,
                                  'speech_text': None, 'speech_has_new': False,
                                  'heart_rate': None, 'heart_rate_valid': False,
                                  'oxygen': None, 'oxygen_valid': False,
                                  'is_finger_detected': False,
                                  'is_health_data_fresh': False,
                              })

            # ---- 2. 健康告警（有冷却，不阻塞循环） ----
            health_alert_triggered = False
            if state.get('is_health_data_fresh'):
                hr = state.get('heart_rate')
                hr_valid = state.get('heart_rate_valid', False)
                ox = state.get('oxygen')
                ox_valid = state.get('oxygen_valid', False)

                if hr_valid and hr and hr > Config.HEART_RATE_HIGH_THRESHOLD:
                    if now - last_health_alert_time > HEALTH_ALERT_COOLDOWN:
                        logger.info(f"健康告警: 心率 {hr}bpm")
                        safe_call(comm.send_oled_emotion, "惊讶", 80, name="oled")
                        last_oled_emotion = "惊讶"
                        safe_call(audio.respond, "心率有点快，要不要休息一下", name="speak")
                        last_health_alert_time = now
                    health_alert_triggered = True

                if ox_valid and ox and ox < Config.OXYGEN_LOW_THRESHOLD:
                    if now - last_health_alert_time > HEALTH_ALERT_COOLDOWN:
                        logger.info(f"健康告警: 血氧 {ox}%")
                        safe_call(comm.send_oled_emotion, "惊讶", 75, name="oled")
                        last_oled_emotion = "惊讶"
                        safe_call(audio.respond, "血氧偏低，注意呼吸", name="speak")
                        last_health_alert_time = now
                    health_alert_triggered = True

            # ---- 3. 实时 OLED 表情显示 ----
            face_emotion = state.get('face_emotion')
            if face_emotion:
                emotion_cn = face_emotion.get('emotion_cn', '平静')
                confidence = face_emotion.get('confidence', 70)
                if last_oled_emotion != emotion_cn:
                    safe_call(comm.send_oled_emotion, emotion_cn, confidence, name="oled")
                    last_oled_emotion = emotion_cn
                    last_oled_clear = False
            else:
                if not last_oled_clear:
                    safe_call(comm.send_oled_clear, name="oled_clear")
                    last_oled_clear = True
                    last_oled_emotion = None

            # ---- 4. 语音交互 ----
            speech_text = state.get('speech_text')
            speech_has_new = state.get('speech_has_new', False)

            if speech_has_new and speech_text:
                text = speech_text.strip()
                logger.info(f"语音输入: '{text}'")

                # 4a. 关键词快速回复
                keyword_map = {
                    "你好": "你好呀，很高兴见到你",
                    "小机器人": "我在呢",
                    "小提琴": "我在呢",
                    "谢谢": "不客气，很高兴能帮到你",
                    "再见": "再见，下次再聊",
                    "拜拜": "再见，下次再聊",
                }
                matched = False
                for keyword, response in keyword_map.items():
                    if keyword in text:
                        logger.info(f"关键词匹配: '{keyword}'")
                        safe_call(audio.respond, response, name="speak")
                        safe_call(comm.send_servo_move, 0, 90, 5, name="servo")
                        time.sleep(0.3)
                        safe_call(comm.send_servo_move, 0, 0, 5, name="servo")
                        matched = True
                        break

                if matched:
                    continue

                # 4b. LLM / 规则引擎决策
                using_llm = decision._llm_engine is not None and decision._llm_engine.is_ready()
                logger.info(f"调用决策引擎 LLM={using_llm}: '{text[:40]}'")
                actions = safe_call(decision.decide, state,
                                    name="decision", default=[])
                logger.info(f"决策输出: {[a.get('type') for a in actions]}")

                for action in actions:
                    atype = action.get('type')
                    if atype == 'speak':
                        reply = action.get('text', '')
                        if reply:
                            logger.info(f"语音回复: {reply[:50]}")
                            safe_call(audio.respond, reply, name="speak")
                    elif atype == 'oled':
                        emo = action.get('emotion', '平静')
                        safe_call(comm.send_oled_emotion, emo,
                                  action.get('confidence', 75), name="oled")
                        last_oled_emotion = emo
                    elif atype == 'servo':
                        move = action.get('move')
                        if move == 'nod':
                            safe_call(comm.send_servo_move, 0, 90, 5, name="servo")
                            time.sleep(0.3)
                            safe_call(comm.send_servo_move, 0, 0, 5, name="servo")
                        elif move == 'shake':
                            safe_call(comm.send_servo_move, 1, 45, 5, name="servo")
                            time.sleep(0.3)
                            safe_call(comm.send_servo_move, 1, 135, 5, name="servo")
                    elif atype == 'oled_text':
                        safe_call(comm.send_oled_text,
                                  action.get('text', ''),
                                  action.get('x', 0),
                                  action.get('y', 0), name="oled_text")
                    elif atype == 'wait':
                        dur = action.get('duration', 0.1)
                        for _ in range(int(dur / 0.05)):
                            if shutdown_flag:
                                break
                            time.sleep(0.05)

            # ---- 5. 休眠 ----
            time.sleep(0.05)

    except KeyboardInterrupt:
        logger.info("收到键盘中断")
    except Exception as e:
        logger.error(f"主循环异常: {e}", exc_info=True)
    finally:
        logger.info("正在清理资源...")
        safe_call(vision.stop, name="vision_stop")
        safe_call(audio.stop, name="audio_stop")
        safe_call(comm.stop, name="comm_stop")
        logger.info("系统已安全退出")


if __name__ == "__main__":
    main()
