#include "app_main.h"
#include "tim.h"
#include "oled.h"
#include "max30102.h"
#include "communication/comm_parser.h"
#include "communication/comm_handler.h"
#include <stdio.h>

/* 避免包含 algorithm.h（内含 static 数组浪费 RAM） */
void maxim_heart_rate_and_oxygen_saturation(uint32_t *pun_ir_buffer, int32_t n_ir_buffer_length,
    uint32_t *pun_red_buffer, int32_t *pn_spo2, int8_t *pch_spo2_valid,
    int32_t *pn_heart_rate, int8_t *pch_hr_valid);

extern UART_HandleTypeDef huart1;

#define TEST_LED_GPIO_Port GPIOC
#define TEST_LED_Pin       GPIO_PIN_13

volatile uint8_t g_max30102_int_flag = 0U;
static uint8_t s_oled_ack_ok = 0U;
static uint8_t s_max30102_ok = 0U;

/* MAX30102 非阻塞采样缓冲区 */
#define MAX30102_BUF_LEN  500

static uint32_t s_red_buf[MAX30102_BUF_LEN];
static uint32_t s_ir_buf[MAX30102_BUF_LEN];
static volatile uint16_t s_sample_count = 0;
static volatile uint8_t  s_samples_ready = 0;
static volatile uint8_t  s_recalc_needed = 0;  /* 主循环检测此标志后运行算法 */
uint8_t g_hr_value = 0;
uint8_t g_spo2_value = 0;

/* UART 中断接收字节缓冲区 */
static uint8_t s_uart_rx_byte = 0U;

static void led_test_delay(volatile uint32_t count)
{
    while (count-- > 0U) {
        __NOP();
    }
}

static void led_test_init(void)
{
    GPIO_InitTypeDef gpio_init = {0};

    __HAL_RCC_GPIOC_CLK_ENABLE();

    gpio_init.Pin = TEST_LED_Pin;
    gpio_init.Mode = GPIO_MODE_OUTPUT_PP;
    gpio_init.Pull = GPIO_NOPULL;
    gpio_init.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(TEST_LED_GPIO_Port, &gpio_init);

    /* Blue Pill 板载 LED 常见为 PC13 低电平点亮，默认先熄灭。 */
    HAL_GPIO_WritePin(TEST_LED_GPIO_Port, TEST_LED_Pin, GPIO_PIN_SET);
}

static void oled_gpio_init(void)
{
    GPIO_InitTypeDef gpio_init = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();

    gpio_init.Pin = GPIO_PIN_6 | GPIO_PIN_7;
    gpio_init.Mode = GPIO_MODE_OUTPUT_PP;
    gpio_init.Pull = GPIO_PULLUP;
    gpio_init.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOA, &gpio_init);

    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_6 | GPIO_PIN_7, GPIO_PIN_SET);
}

static void i2c_line_scl(uint8_t high)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_6, high ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static void i2c_line_sda(uint8_t high)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_7, high ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static uint8_t i2c_read_sda(void)
{
    return (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_7) == GPIO_PIN_SET) ? 1U : 0U;
}

static void i2c_delay_short(void)
{
    led_test_delay(80U);
}

static void i2c_sda_input(void)
{
    GPIO_InitTypeDef gpio_init = {0};

    gpio_init.Pin = GPIO_PIN_7;
    gpio_init.Mode = GPIO_MODE_INPUT;
    gpio_init.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOA, &gpio_init);
}

static void i2c_sda_output(void)
{
    GPIO_InitTypeDef gpio_init = {0};

    gpio_init.Pin = GPIO_PIN_7;
    gpio_init.Mode = GPIO_MODE_OUTPUT_PP;
    gpio_init.Pull = GPIO_PULLUP;
    gpio_init.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOA, &gpio_init);
}

static void i2c_start(void)
{
    i2c_sda_output();
    i2c_line_sda(1U);
    i2c_line_scl(1U);
    i2c_delay_short();
    i2c_line_sda(0U);
    i2c_delay_short();
    i2c_line_scl(0U);
    i2c_delay_short();
}

static void i2c_stop(void)
{
    i2c_sda_output();
    i2c_line_sda(0U);
    i2c_delay_short();
    i2c_line_scl(1U);
    i2c_delay_short();
    i2c_line_sda(1U);
    i2c_delay_short();
}

static void i2c_write_byte(uint8_t data)
{
    uint8_t i;

    i2c_sda_output();
    for (i = 0U; i < 8U; i++) {
        i2c_line_scl(0U);
        i2c_line_sda((data & 0x80U) ? 1U : 0U);
        i2c_delay_short();
        i2c_line_scl(1U);
        i2c_delay_short();
        data <<= 1;
    }
    i2c_line_scl(0U);
}

static uint8_t i2c_wait_ack(void)
{
    uint8_t ack;

    i2c_sda_input();
    i2c_delay_short();
    i2c_line_scl(1U);
    i2c_delay_short();
    ack = (uint8_t)(i2c_read_sda() == 0U);
    i2c_line_scl(0U);
    i2c_sda_output();
    return ack;
}

static uint8_t sh1106_probe_address(void)
{
    uint8_t ack;

    i2c_start();
    i2c_write_byte(0x78U); /* 0x3C << 1, write */
    ack = i2c_wait_ack();
    i2c_stop();
    return ack;
}

static void led_show_probe_result(void)
{
    uint8_t i;
    uint8_t blink_times = s_oled_ack_ok ? 3U : 1U;

    for (i = 0U; i < blink_times; i++) {
        HAL_GPIO_WritePin(TEST_LED_GPIO_Port, TEST_LED_Pin, GPIO_PIN_RESET);
        led_test_delay(200000U);
        HAL_GPIO_WritePin(TEST_LED_GPIO_Port, TEST_LED_Pin, GPIO_PIN_SET);
        led_test_delay(200000U);
    }

    led_test_delay(1200000U);
}

void vPwmInit(void)
{
    StaticPwmDeviceParamTdf pwm_cfg;

    MX_TIM2_Init();

    pwm_cfg.phtim = &htim2;
    pwm_cfg.channel = TIM_CHANNEL_1;
    vPwmDeviceStaticParamInit(&pwm_cfg, PWM0);
}

void vServoInit(void)
{
    StaticServoDeviceParamTdf sv_cfg;

    sv_cfg.angle = 0.0f;
    vServoDeviceStaticParamInit(&sv_cfg, SERVO0);

    /* 初始归中 */
    Servo_DeviceSetById(0U, 90U, 50U);
    HAL_Delay(500);
}

void UART_SendBytes(const uint8_t *data, uint16_t len)
{
    if (data == NULL || len == 0U) {
        return;
    }

    HAL_UART_Transmit(&huart1, (uint8_t *)data, len, 100U);
}

void vCommOnUartRxCplt(UART_HandleTypeDef *huart)
{
    /* 串口连通性测试：收到什么回什么 */
    HAL_UART_Transmit(huart, &s_uart_rx_byte, 1, 100);

    Parser_Feed(s_uart_rx_byte);
    HAL_UART_Receive_IT(huart, &s_uart_rx_byte, 1);
}

static void max30102_i2c_pin_init(void)
{
    GPIO_InitTypeDef gpio_init = {0};

    __HAL_RCC_GPIOB_CLK_ENABLE();

    /* PB8(SCL), PB9(SDA) — open-drain output with pull-up for bit-bang I2C */
    gpio_init.Pin = GPIO_PIN_8 | GPIO_PIN_9;
    gpio_init.Mode = GPIO_MODE_OUTPUT_OD;
    gpio_init.Pull = GPIO_PULLUP;
    gpio_init.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOB, &gpio_init);

    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8 | GPIO_PIN_9, GPIO_PIN_SET);
}

void vAppInit(void)
{
    g_max30102_int_flag = 0U;
    led_test_init();
    oled_gpio_init();
    s_oled_ack_ok = sh1106_probe_address();

    vPwmInit();
    vServoInit();

    if (s_oled_ack_ok) {
        OLED_ShowString(0, 4, (uint8_t *)"Servo init OK", 16);
    }

    /* MAX30102 I2C 引脚初始化 */
    max30102_i2c_pin_init();

    /* 复位 MAX30102 */
    max30102_reset();
    HAL_Delay(100);

    /* 读 PART_ID 验证 I2C 通信 (MAX30102 PART_ID = 0x15) */
    {
        uint8_t part_id = 0U;
        part_id = max30102_Bus_Read(REG_PART_ID);
        s_max30102_ok = (part_id == 0x15U);
        if (s_max30102_ok) {
            max30102_init();

            /* 启动 TIM1 100Hz 采样定时器 */
            MX_TIM1_Init();
            HAL_TIM_Base_Start_IT(&htim1);

            if (s_oled_ack_ok) {
                OLED_ShowString(0, 6, (uint8_t *)"MAX30102 OK", 16);
            }
        } else {
            if (s_oled_ack_ok) {
                OLED_ShowString(0, 6, (uint8_t *)"MAX30102 ERR", 16);
            }
        }
    }

    /* 初始化通信协议解析 + 命令处理 */
    Parser_Init();
    Parser_OnFrame(Handler_OnFrame);
    Handler_Init();
    HAL_UART_Receive_IT(&huart1, &s_uart_rx_byte, 1);
}

/* TIM1 周期回调：非阻塞读取 MAX30102 FIFO（直接轮询 INT 引脚电平） */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM1) {
        if (s_sample_count >= MAX30102_BUF_LEN) {
            return;
        }

        /* 直接读取 INT 引脚电平（低电平 = 数据就绪），不依赖 EXTI 中断 */
        if (HAL_GPIO_ReadPin(MAX30102_INT_GPIO_Port, MAX30102_INT_Pin) == GPIO_PIN_RESET) {
            uint8_t temp[6];

            max30102_FIFO_ReadBytes(REG_FIFO_DATA, temp);

            s_red_buf[s_sample_count] = ((uint32_t)(temp[0] & 0x03) << 16)
                                       | ((uint32_t)temp[1] << 8) | temp[2];
            s_ir_buf[s_sample_count]  = ((uint32_t)(temp[3] & 0x03) << 16)
                                       | ((uint32_t)temp[4] << 8) | temp[5];
            s_sample_count++;

            if (s_sample_count >= MAX30102_BUF_LEN) {
                s_recalc_needed = 1;
            }
        }
    }
}

void vExecute(void)
{
    static uint8_t s_phase = 0U;
    vShowBmpTest();

    switch (s_phase) {

        case 0U: /* LED 指示 + OLED 显示 MAX30102 检测结果 */
            led_show_probe_result();
            OLED_Clear();
            OLED_ShowString(0, 0, (uint8_t *)"MAX30102 Test", 16);
            if (s_max30102_ok) {
                OLED_ShowString(0, 2, (uint8_t *)"Sensor: OK", 16);
            } else {
                OLED_ShowString(0, 2, (uint8_t *)"Sensor: FAIL", 16);
            }
            OLED_ShowString(0, 4, (uint8_t *)"Servo test...", 16);
            s_phase = 1U;
            break;

        case 1U: /* 舵机 0° */
            Servo_DeviceSetById(0U, 0U, 50U);
            HAL_Delay(1000);
            s_phase = 2U;
            break;

        case 2U: /* 舵机 90° */
            Servo_DeviceSetById(0U, 90U, 50U);
            HAL_Delay(1000);
            s_phase = 3U;
            break;

        case 3U: /* 舵机 180° */
            Servo_DeviceSetById(0U, 180U, 50U);
            HAL_Delay(1000);
            s_phase = 4U;
            break;

        case 4U: /* 舵机 90° */
            Servo_DeviceSetById(0U, 90U, 50U);
            HAL_Delay(1000);
            s_phase = 5U;
            break;

        case 5U: /* 舵机归中 */
            Servo_DeviceSetById(0U, 90U, 50U);
            HAL_Delay(1000);
            OLED_ShowString(0, 4, (uint8_t *)"Servo done!   ", 16);
            if (s_max30102_ok) {
                OLED_ShowString(0, 6, (uint8_t *)"Sampling...    ", 16);
            } else {
                OLED_ShowString(0, 6, (uint8_t *)"Sensor FAIL    ", 16);
            }
            s_phase = 6U;
            break;

        case 6U: /* 采样 / 连续显示 + 通信处理 */
        {
            static uint32_t s_last_update = 0U;
            char buf[21];

            /* 通信处理必须始终运行，不受 MAX30102 状态影响 */
            Parser_Process();
            Handler_Tick();

            if (s_max30102_ok) {
                /* 缓冲区满 → 运行算法 + 滑窗移位 */
                if (s_recalc_needed) {
                int32_t n_sp02 = 0, n_hr = 0;
                int8_t ch_spo2_valid = 0, ch_hr_valid = 0;
                uint16_t i;

                s_recalc_needed = 0;

                maxim_heart_rate_and_oxygen_saturation(
                    s_ir_buf, MAX30102_BUF_LEN,
                    s_red_buf, &n_sp02, &ch_spo2_valid,
                    &n_hr, &ch_hr_valid);

                /* 仅保存有效结果 */
                if (ch_hr_valid && n_hr > 0 && n_hr < 255)
                    g_hr_value = (uint8_t)n_hr;
                if (ch_spo2_valid && n_sp02 > 0 && n_sp02 < 255)
                    g_spo2_value = (uint8_t)n_sp02;

                /* 滑窗：丢弃最早 100 个样本，保留后 400 个，继续采 100 个新样本 */
                for (i = 100; i < MAX30102_BUF_LEN; i++) {
                    s_red_buf[i - 100] = s_red_buf[i];
                    s_ir_buf[i - 100] = s_ir_buf[i];
                }
                s_sample_count = MAX30102_BUF_LEN - 100;
            }
            }  /* if (s_max30102_ok) */

            /* 限速刷新 OLED（每 500ms）避免闪烁 */
            if (HAL_GetTick() - s_last_update >= 500) {
                s_last_update = HAL_GetTick();

                if (g_spo2_value > 0) {
                    snprintf(buf, sizeof(buf), "HR:%3d SpO2:%3d",
                             g_hr_value, g_spo2_value);
                } else if (g_hr_value > 0) {
                    snprintf(buf, sizeof(buf), "HR:%3d SpO2:---",
                             g_hr_value);
                } else {
                    snprintf(buf, sizeof(buf), "HR:--- SpO2:---");
                }
                OLED_ShowString(0, 6, (uint8_t *)buf, 16);
            }
            break;
        }

        default:
            s_phase = 0U;
            break;
    }
}



