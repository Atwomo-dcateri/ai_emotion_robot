/**
 * @file comm_handler.h
 * @brief 指令分发 + 数据上报管理
 */

#ifndef COMM_HANDLER_H
#define COMM_HANDLER_H

#include <stdint.h>
#include <stdbool.h>
#include "comm_config.h"
#include "comm_protocol.h"

/* 通信状态 */
typedef enum {
    COMM_STATE_DISCONNECTED,    // 未收到任何帧
    COMM_STATE_CONNECTED,       // 正常通信
    COMM_STATE_ERROR            // 通信异常
} CommState_t;

/* ========== API 函数 ========== */

/**
 * @brief 初始化处理器
 */
void Handler_Init(void);

/**
 * @brief 主循环周期性调用（用于超时检测、定时上报）
 */
void Handler_Tick(void);

/**
 * @brief 帧处理入口（作为 Parser 回调）
 * @param frame 接收到的帧
 */
void Handler_OnFrame(const Frame *frame);

/**
 * @brief 发送帧（通过 USART DMA）
 * @param frame 待发送的帧
 * @return true: 发送成功, false: 发送失败
 */
bool Handler_SendFrame(const Frame *frame);

/**
 * @brief 获取当前通信状态
 * @return 通信状态
 */
CommState_t Handler_GetState(void);

/**
 * @brief 设置健康数据上报间隔
 * @param interval_ms 间隔毫秒数
 */
void Handler_SetHeartbeatInterval(uint32_t interval_ms);

#endif /* COMM_HANDLER_H */
