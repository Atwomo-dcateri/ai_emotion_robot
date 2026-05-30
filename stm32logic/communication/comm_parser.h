/**
 * @file comm_parser.h
 * @brief 接收解析器（环形缓冲 + 粘包处理）
 */

#ifndef COMM_PARSER_H
#define COMM_PARSER_H

#include <stdint.h>
#include "comm_config.h"
#include "comm_protocol.h"

/* 帧接收回调函数类型 */
typedef void (*frame_callback_t)(const Frame *frame);

/* ========== API 函数 ========== */

/**
 * @brief 初始化解析器
 */
void Parser_Init(void);

/**
 * @brief 喂数据（单字节，USART 中断中调用）
 * @param byte 接收到的字节
 */
void Parser_Feed(uint8_t byte);

/**
 * @brief 喂数据（批量，DMA 接收完成时调用）
 * @param data 数据指针
 * @param len 数据长度
 */
void Parser_FeedBatch(const uint8_t *data, uint16_t len);

/**
 * @brief 处理缓冲区中的完整帧（主循环中调用）
 */
void Parser_Process(void);

/**
 * @brief 注册帧接收回调
 * @param callback 回调函数指针
 */
void Parser_OnFrame(frame_callback_t callback);

/**
 * @brief 获取当前解析器状态（调试用）
 * @param frame_count 输出已处理的帧计数
 * @param error_count 输出错误计数
 */
void Parser_GetStats(uint32_t *frame_count, uint32_t *error_count);

#endif /* COMM_PARSER_H */
