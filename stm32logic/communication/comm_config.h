/**
 * @file comm_config.h
 * @brief 通信模块配置常量
 */

#ifndef COMM_CONFIG_H
#define COMM_CONFIG_H

#include "main.h"

/* ========== 缓冲区大小配置 ========== */
#define COMM_RX_BUF_SIZE        512     // 环形缓冲区大小（字节）
#define COMM_TX_QUEUE_SIZE      20      // 发送队列大小（帧数）
#define COMM_DMA_BUF_SIZE       256     // DMA 接收缓冲区大小

/* ========== 超时配置（毫秒） ========== */
#define COMM_FRAME_TIMEOUT_MS   500     // 帧接收超时（帧头后未收齐则丢弃）
#define COMM_CONNECT_TIMEOUT_MS 3000    // 连接断开判定（无帧接收超时）
#define COMM_HEARTBEAT_IVAL_MS  1000    // 健康数据上报间隔

/* ========== 帧格式常量 ========== */
#define FRAME_HEAD_H            0xAA
#define FRAME_HEAD_L            0x55
#define FRAME_TAIL              0xBB
#define MAX_DATA_LEN            250
#define FRAME_MIN_LEN           7       // HEAD(2) + TYPE(1) + LEN(1) + CRC(2) + TAIL(1)

/* ========== 帧类型定义 ========== */
// STM32 → 树莓派
#define TYPE_HEARTBEAT          0x01    // 心率+血氧数据上报
#define TYPE_SENSOR_STATUS      0x03    // 传感器状态
#define TYPE_ACK                0x04    // 应答
#define TYPE_NAK                0x05    // 否定应答

// 树莓派 → STM32
#define TYPE_OLED               0x10    // OLED 控制
#define TYPE_SERVO              0x11    // 舵机控制
#define TYPE_QUERY_SENSOR       0x12    // 查询传感器
#define TYPE_CONFIG             0x13    // 参数配置

/* ========== OLED 子命令 ========== */
#define OLED_CMD_EMOTION        0x00    // 显示表情
#define OLED_CMD_TEXT           0x01    // 显示文本
#define OLED_CMD_CLEAR          0x02    // 清屏

/* ========== 舵机 ID ========== */
#define SERVO_ID_NOD            0x00    // 点头舵机
#define SERVO_ID_SHAKE          0x01    // 摇头舵机

/* ========== USART 句柄（需根据实际修改） ========== */
extern UART_HandleTypeDef huart1;
#define COMM_UART_HANDLE        huart1

#endif /* COMM_CONFIG_H */
