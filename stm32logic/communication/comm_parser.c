/**
 * @file comm_parser.c
 * @brief 接收解析器实现
 */

#include "comm_parser.h"
#include <string.h>

/* 环形缓冲区结构 */
typedef struct {
    uint8_t buffer[COMM_RX_BUF_SIZE];
    uint16_t head;          // 写指针
    uint16_t tail;          // 读指针
    uint16_t count;         // 已存字节数
} RingBuffer_t;

/* 解析器状态机 */
typedef enum {
    PARSER_STATE_IDLE,      // 空闲，搜索帧头
    PARSER_STATE_HEAD_2,    // 收到 0xAA，等待 0x55
    PARSER_STATE_HEADER,    // 收到帧头，等待 TYPE + LEN
    PARSER_STATE_DATA       // 收集中，等待帧尾
} ParserState_t;

/* 解析器上下文 */
static struct {
    RingBuffer_t rx_buf;
    frame_callback_t callback;
    ParserState_t state;
    
    /* 当前帧缓存 */
    uint8_t current_frame[FRAME_MIN_LEN + MAX_DATA_LEN];
    uint16_t frame_pos;
    uint8_t frame_len;      // 期望的总帧长度（含头尾）
    uint32_t frame_timeout; // 超时计数
    
    /* 统计 */
    uint32_t frame_count;
    uint32_t error_count;
} g_parser;

/* 辅助函数：初始化环形缓冲区 */
static void ringbuf_init(RingBuffer_t *rb)
{
    rb->head = 0;
    rb->tail = 0;
    rb->count = 0;
    memset(rb->buffer, 0, COMM_RX_BUF_SIZE);
}

/* 辅助函数：写入环形缓冲区 */
static uint8_t ringbuf_write(RingBuffer_t *rb, uint8_t byte)
{
    if (rb->count >= COMM_RX_BUF_SIZE) {
        return 0;  // 缓冲区满
    }
    rb->buffer[rb->head] = byte;
    rb->head = (rb->head + 1) % COMM_RX_BUF_SIZE;
    rb->count++;
    return 1;
}

/* 辅助函数：查看但不移除 */
static uint8_t ringbuf_peek(RingBuffer_t *rb, uint16_t offset, uint8_t *byte)
{
    if (offset >= rb->count) {
        return 0;
    }
    uint16_t index = (rb->tail + offset) % COMM_RX_BUF_SIZE;
    *byte = rb->buffer[index];
    return 1;
}

/* 辅助函数：跳过指定字节数 */
static void ringbuf_skip(RingBuffer_t *rb, uint16_t count)
{
    for (uint16_t i = 0; i < count && rb->count > 0; i++) {
        rb->tail = (rb->tail + 1) % COMM_RX_BUF_SIZE;
        rb->count--;
    }
}

void Parser_Init(void)
{
    ringbuf_init(&g_parser.rx_buf);
    g_parser.callback = NULL;
    g_parser.state = PARSER_STATE_IDLE;
    g_parser.frame_pos = 0;
    g_parser.frame_len = 0;
    g_parser.frame_timeout = 0;
    g_parser.frame_count = 0;
    g_parser.error_count = 0;
}

void Parser_Feed(uint8_t byte)
{
    ringbuf_write(&g_parser.rx_buf, byte);
}

void Parser_FeedBatch(const uint8_t *data, uint16_t len)
{
    for (uint16_t i = 0; i < len; i++) {
        ringbuf_write(&g_parser.rx_buf, data[i]);
    }
}

static void parser_reset_state(void)
{
    g_parser.state = PARSER_STATE_IDLE;
    g_parser.frame_pos = 0;
    g_parser.frame_len = 0;
}

static void parser_frame_complete(void)
{
    Frame frame;
    if (Proto_Unpack(g_parser.current_frame, g_parser.frame_len, &frame) == 0) {
        g_parser.frame_count++;
        if (g_parser.callback) {
            g_parser.callback(&frame);
        }
    } else {
        g_parser.error_count++;
    }
    parser_reset_state();
}

void Parser_Process(void)
{
    uint8_t byte;
    
    while (g_parser.rx_buf.count > 0) {
        if (ringbuf_peek(&g_parser.rx_buf, 0, &byte) == 0) {
            break;
        }
        
        switch (g_parser.state) {
            case PARSER_STATE_IDLE:
                if (byte == FRAME_HEAD_H) {
                    g_parser.current_frame[0] = byte;
                    g_parser.frame_pos = 1;
                    g_parser.state = PARSER_STATE_HEAD_2;
                }
                ringbuf_skip(&g_parser.rx_buf, 1);
                break;
                
            case PARSER_STATE_HEAD_2:
                g_parser.current_frame[1] = byte;
                g_parser.frame_pos = 2;
                if (byte == FRAME_HEAD_L) {
                    g_parser.state = PARSER_STATE_HEADER;
                } else {
                    parser_reset_state();
                }
                ringbuf_skip(&g_parser.rx_buf, 1);
                break;
                
            case PARSER_STATE_HEADER:
                // 等待 TYPE + LEN 共 2 字节
                g_parser.current_frame[g_parser.frame_pos++] = byte;
                ringbuf_skip(&g_parser.rx_buf, 1);
                
                if (g_parser.frame_pos == 4) {  // HEAD(2) + TYPE(1) + LEN(1)
                    uint8_t data_len = g_parser.current_frame[3];
                    if (data_len > MAX_DATA_LEN) {
                        parser_reset_state();
                    } else {
                        g_parser.frame_len = 2 + 1 + 1 + data_len + 2 + 1;  // HEAD + TYPE + LEN + DATA + CRC(2) + TAIL
                        g_parser.state = PARSER_STATE_DATA;
                    }
                }
                break;
                
            case PARSER_STATE_DATA:
                g_parser.current_frame[g_parser.frame_pos++] = byte;
                ringbuf_skip(&g_parser.rx_buf, 1);
                
                if (g_parser.frame_pos >= g_parser.frame_len) {
                    // 检查帧尾
                    if (g_parser.current_frame[g_parser.frame_len - 1] == FRAME_TAIL) {
                        parser_frame_complete();
                    } else {
                        parser_reset_state();
                        g_parser.error_count++;
                    }
                }
                break;
        }
    }
}

void Parser_OnFrame(frame_callback_t callback)
{
    g_parser.callback = callback;
}

void Parser_GetStats(uint32_t *frame_count, uint32_t *error_count)
{
    if (frame_count) *frame_count = g_parser.frame_count;
    if (error_count) *error_count = g_parser.error_count;
}
