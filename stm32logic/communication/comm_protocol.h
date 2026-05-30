
/**
 * @file comm_protocol.h
 * @brief 协议编解码（帧打包/解析/校验）- CRC16-CCITT 版本
 */

#ifndef COMM_PROTOCOL_H
#define COMM_PROTOCOL_H

#include <stdint.h>
#include "comm_config.h"

/* 帧数据结构 */
typedef struct {
    uint8_t type;                       // 帧类型
    uint8_t len;                        // 数据长度
    uint8_t data[MAX_DATA_LEN];         // 数据负载
} Frame;

/* ========== API 函数 ========== */

/**
 * @brief 计算 CRC16-CCITT 校验值
 * @param data 数据指针
 * @param len 数据长度
 * @return CRC16 值
 */
uint16_t Proto_CalcCRC16(const uint8_t *data, uint8_t len);

/**
 * @brief 打包帧
 * @param frame 帧结构体指针
 * @param buffer 输出缓冲区
 * @return 完整帧长度，失败返回 0
 */
uint16_t Proto_Pack(const Frame *frame, uint8_t *buffer);

/**
 * @brief 解析帧
 * @param buffer 输入缓冲区
 * @param len 缓冲区长度
 * @param frame 输出帧结构体指针
 * @return 0:成功, -1:失败
 */
int8_t Proto_Unpack(const uint8_t *buffer, uint16_t len, Frame *frame);
/**
 * @brief 创建 OLED 表情帧
 * @param emotion 表情名称字符串
 * @param confidence 置信度 0-100
 * @param frame 输出帧结构体
 */
void Proto_BuildOledEmotion(const char *emotion, uint8_t confidence, Frame *frame);

/**
 * @brief 创建 OLED 文本帧
 * @param text 文本字符串
 * @param x X 坐标
 * @param y Y 坐标
 * @param frame 输出帧结构体
 */
void Proto_BuildOledText(const char *text, uint8_t x, uint8_t y, Frame *frame);

/**
 * @brief 创建 OLED 清屏帧
 * @param frame 输出帧结构体
 */
void Proto_BuildOledClear(Frame *frame);

/**
 * @brief 创建舵机控制帧
 * @param servo_id 舵机 ID
 * @param angle 角度 0-180
 * @param speed 速度 1-10
 * @param frame 输出帧结构体
 */
void Proto_BuildServoMove(uint8_t servo_id, uint8_t angle, uint8_t speed, Frame *frame);

/**
 * @brief 创建健康数据帧（心率+血氧）
 * @param hr_val 心率值
 * @param hr_ok 心率有效标志
 * @param oxygen_val 血氧值
 * @param oxygen_ok 血氧有效标志
 * @param frame 输出帧结构体
 */
void Proto_BuildHeartbeat(uint8_t hr_val, uint8_t hr_ok,
                          uint8_t oxygen_val, uint8_t oxygen_ok,
                          Frame *frame);

/**
 * @brief 创建传感器状态帧
 * @param status 状态码（0=离线,1=在线,2=错误）
 * @param err_code 错误码
 * @param frame 输出帧结构体
 */
void Proto_BuildSensorStatus(uint8_t status, uint8_t err_code, Frame *frame);

/**
 * @brief 创建 ACK 帧
 * @param frame 输出帧结构体
 */
void Proto_BuildAck(Frame *frame);

/**
 * @brief 创建 NAK 帧
 * @param frame 输出帧结构体
 */
void Proto_BuildNak(Frame *frame);

#endif /* COMM_PROTOCOL_H */
