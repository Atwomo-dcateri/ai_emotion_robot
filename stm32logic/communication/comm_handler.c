/**
 * @file comm_handler.c
 * @brief 指令分发 + 数据上报实现
 */

#include "comm_handler.h"
#include <string.h>
#include "oled.h"
#include "servo_device.h"

/* 外部声明的 USART 发送函数（需根据实际实现） */
extern void UART_SendBytes(const uint8_t *data, uint16_t len);

/* 处理器上下文 */
static struct {
    CommState_t state;
    uint32_t last_rx_tick;
    uint32_t last_heartbeat_tick;
    uint32_t heartbeat_interval_ms;
    uint32_t timeout_ms;
} g_handler;

static bool oled_show_text(const char *text, uint8_t x, uint8_t y)
{
    uint8_t page;

    if (text == NULL) {
        return false;
    }

    page = (uint8_t)(y / 8U);
    if (page > 7U) {
        page = 7U;
    }

    OLED_ShowString(x, page, (uint8_t *)text, 16);
    return true;
}

static bool oled_show_emotion(const char *emotion, uint8_t confidence)
{
    if (emotion == NULL) {
        return false;
    }

    OLED_Clear();
    OLED_ShowString(0, 0, (uint8_t *)emotion, 16);
    OLED_ShowString(0, 2, (uint8_t *)"CF:", 16);
    OLED_ShowNum(24, 2, confidence, 3, 16);
    return true;
}

static bool oled_clear(void)
{
    OLED_Clear();
    return true;
}

static bool servo_set_angle(uint8_t servo_id, uint8_t angle, uint8_t speed)
{
    return Servo_DeviceSetById(servo_id, angle, speed);
}

static void read_health_data(uint8_t *hr, uint8_t *oxygen, bool *finger_detected, uint8_t *status)
{
    extern uint8_t g_hr_value;
    extern uint8_t g_spo2_value;

    uint8_t local_hr = g_hr_value;
    uint8_t local_oxygen = g_spo2_value;

    if (hr != NULL) {
        *hr = local_hr;
    }
    if (oxygen != NULL) {
        *oxygen = local_oxygen;
    }
    if (finger_detected != NULL) {
        *finger_detected = (local_hr != 0U) && (local_oxygen != 0U);
    }
    if (status != NULL) {
        *status = ((local_hr != 0U) || (local_oxygen != 0U)) ? 1U : 2U;
    }
}

/* 获取当前系统 tick（需根据实际 HAL 实现） */
static uint32_t get_tick(void)
{
    // 使用 HAL_GetTick() 或自定义
    extern uint32_t HAL_GetTick(void);
    return HAL_GetTick();
}

void Handler_Init(void)
{
    g_handler.state = COMM_STATE_DISCONNECTED;
    g_handler.last_rx_tick = get_tick();
    g_handler.last_heartbeat_tick = get_tick();
    g_handler.heartbeat_interval_ms = COMM_HEARTBEAT_IVAL_MS;
    g_handler.timeout_ms = COMM_CONNECT_TIMEOUT_MS;
}

static void send_ack(void)
{
    Frame frame;
    Proto_BuildAck(&frame);
    Handler_SendFrame(&frame);
}

static void send_nak(void)
{
    Frame frame;
    Proto_BuildNak(&frame);
    Handler_SendFrame(&frame);
}

static void send_heartbeat(void)
{
    Frame frame;
    uint8_t hr;
    uint8_t oxygen;
    uint8_t status;
    bool finger;

    read_health_data(&hr, &oxygen, &finger, &status);
    
    Proto_BuildHeartbeat(hr, finger ? 1 : 0, oxygen, finger ? 1 : 0, &frame);
    Handler_SendFrame(&frame);
    
    // 同时上报传感器状态（如有变化可优化）
    Frame status_frame;
    Proto_BuildSensorStatus(status, 0, &status_frame);
    Handler_SendFrame(&status_frame);
}

static void process_oled_frame(const Frame *frame)
{
    if (frame->len < 1) {
        send_nak();
        return;
    }
    
    uint8_t cmd = frame->data[0];
    
    switch (cmd) {
        case OLED_CMD_EMOTION:  // 显示表情
            if (frame->len >= 3) {  // CMD + CONFIDENCE + LENGTH
                uint8_t confidence = frame->data[1];
                uint8_t name_len = frame->data[2];
                if (frame->len >= 3 + name_len) {
                    char emotion[MAX_DATA_LEN + 1];
                    memcpy(emotion, &frame->data[3], name_len);
                    emotion[name_len] = '\0';
                    if (oled_show_emotion(emotion, confidence)) {
                        send_ack();
                    } else {
                        send_nak();
                    }
                } else {
                    send_nak();
                }
            } else {
                send_nak();
            }
            break;
            
        case OLED_CMD_TEXT:  // 显示文本
            if (frame->len >= 4) {  // CMD + X + Y + LENGTH
                uint8_t x = frame->data[1];
                uint8_t y = frame->data[2];
                uint8_t text_len = frame->data[3];
                if (frame->len >= 4 + text_len) {
                    char text[MAX_DATA_LEN + 1];
                    memcpy(text, &frame->data[4], text_len);
                    text[text_len] = '\0';
                    if (oled_show_text(text, x, y)) {
                        send_ack();
                    } else {
                        send_nak();
                    }
                } else {
                    send_nak();
                }
            } else {
                send_nak();
            }
            break;
            
        case OLED_CMD_CLEAR:  // 清屏
            if (oled_clear()) {
                send_ack();
            } else {
                send_nak();
            }
            break;
            
        default:
            send_nak();
            break;
    }
}

static void process_servo_frame(const Frame *frame)
{
    if (frame->len < 3) {
        send_nak();
        return;
    }
    
    uint8_t servo_id = frame->data[0];
    uint8_t angle = frame->data[1];
    uint8_t speed = frame->data[2];
    
    if (servo_set_angle(servo_id, angle, speed)) {
        send_ack();
    } else {
        send_nak();
    }
}

static void process_query_sensor_frame(const Frame *frame)
{
    (void)frame;
    send_heartbeat();  // 立即上报一次健康数据
    send_ack();
}

static void process_config_frame(const Frame *frame)
{
    if (frame->len == 4U) {
        uint32_t interval_ms = ((uint32_t)frame->data[0] << 24) |
                               ((uint32_t)frame->data[1] << 16) |
                               ((uint32_t)frame->data[2] << 8) |
                               (uint32_t)frame->data[3];
        Handler_SetHeartbeatInterval(interval_ms);
        send_ack();
        return;
    }

    send_nak();
}

void Handler_OnFrame(const Frame *frame)
{
    if (frame == NULL) return;
    
    // 更新最后接收时间
    g_handler.last_rx_tick = get_tick();
    if (g_handler.state == COMM_STATE_DISCONNECTED) {
        g_handler.state = COMM_STATE_CONNECTED;
    }
    
    // 按类型分发
    switch (frame->type) {
        case TYPE_OLED:
            process_oled_frame(frame);
            break;
        case TYPE_SERVO:
            process_servo_frame(frame);
            break;
        case TYPE_QUERY_SENSOR:
            process_query_sensor_frame(frame);
            break;
        case TYPE_CONFIG:
            process_config_frame(frame);
            break;
        default:
            send_nak();
            break;
    }
}

bool Handler_SendFrame(const Frame *frame)
{
    if (frame == NULL) return false;
    
    uint8_t buffer[FRAME_MIN_LEN + MAX_DATA_LEN];
    uint16_t len = Proto_Pack(frame, buffer);
    
    if (len == 0) return false;
    
    // 通过 USART 发送（阻塞或 DMA）
    // HAL_UART_Transmit(&COMM_UART_HANDLE, buffer, len, 100);
    UART_SendBytes(buffer, len);
    return true;
}

void Handler_Tick(void)
{
    uint32_t now = get_tick();
    
    // 连接超时检测
    if (g_handler.state == COMM_STATE_CONNECTED) {
        if ((now - g_handler.last_rx_tick) >= g_handler.timeout_ms) {
            g_handler.state = COMM_STATE_DISCONNECTED;
        }
    }
    
    // 定时上报健康数据（仅当连接时）
    if (g_handler.state == COMM_STATE_CONNECTED) {
        if ((now - g_handler.last_heartbeat_tick) >= g_handler.heartbeat_interval_ms) {
            g_handler.last_heartbeat_tick = now;
            send_heartbeat();
        }
    }
}

CommState_t Handler_GetState(void)
{
    return g_handler.state;
}

void Handler_SetHeartbeatInterval(uint32_t interval_ms)
{
    if (interval_ms >= 100) {
        g_handler.heartbeat_interval_ms = interval_ms;
    }
}
