/* Force-included (-include) into every upstream translation unit.
 * Pre-defines __MAIN_H so the upstream Core/Inc/main.h (HAL pin map, I2S/UART
 * handles, DWT delay) is skipped wherever it is reached by a relative include,
 * then provides the few symbols of it that the DSP/sequencer code uses. */
#ifndef LXR_HOST_PRELUDE_H
#define LXR_HOST_PRELUDE_H

#define __MAIN_H
#include "stm32f7xx_hal.h"

/* Jack-detect GPIO: every jack reports "available" so the mixer's hardware
 * routing fallback is the identity (plugin = all outputs connected). */
typedef struct { volatile uint32_t IDR; } GPIO_TypeDef;
extern GPIO_TypeDef lxr_host_gpio_all_high;
#define switch_l1_GPIO_Port (&lxr_host_gpio_all_high)
#define switch_r1_GPIO_Port (&lxr_host_gpio_all_high)
#define switch_l2_GPIO_Port (&lxr_host_gpio_all_high)
#define switch_r2_GPIO_Port (&lxr_host_gpio_all_high)
#define switch_l1_Pin 0x1u
#define switch_r1_Pin 0x1u
#define switch_l2_Pin 0x1u
#define switch_r2_Pin 0x1u

/* Every __attribute__ left in the upstream sources is a linker-section placement
 * (ITCM/DTCM) that Mach-O rejects; none carries semantics. Defined after all
 * system headers pulled in above so their own attributes are untouched. */
#define __attribute__(x)

extern float debugWatch;
void Error_Handler(void);

#endif
