/* Host platform layer for lxr_core: the subset of the STM32 HAL / CMSIS surface the derived DSP
 * code touches, with ARMv7E-M semantics for the intrinsics. Not derived from upstream. */
#ifndef LXR_PLATFORM_HAL_H
#define LXR_PLATFORM_HAL_H

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <math.h>

#define UNUSED(x) ((void)(x))
#define INDTCM
#define INDTCMZ

static inline int32_t __SSAT(int32_t val, uint32_t sat)
{
    if (sat >= 1U && sat <= 32U) {
        const int32_t max = (int32_t)((1U << (sat - 1U)) - 1U);
        const int32_t min = -1 - max;
        if (val > max) return max;
        if (val < min) return min;
    }
    return val;
}
static inline int32_t lxr_sat16_(int32_t v) { return v > 32767 ? 32767 : (v < -32768 ? -32768 : v); }
static inline uint32_t __QADD16(uint32_t op1, uint32_t op2)
{
    const int32_t lo = lxr_sat16_((int16_t)(op1 & 0xFFFFU) + (int16_t)(op2 & 0xFFFFU));
    const int32_t hi = lxr_sat16_((int16_t)(op1 >> 16) + (int16_t)(op2 >> 16));
    return ((uint32_t)lo & 0xFFFFU) | ((uint32_t)hi << 16);
}
static inline uint32_t __QSUB16(uint32_t op1, uint32_t op2)
{
    const int32_t lo = lxr_sat16_((int16_t)(op1 & 0xFFFFU) - (int16_t)(op2 & 0xFFFFU));
    const int32_t hi = lxr_sat16_((int16_t)(op1 >> 16) - (int16_t)(op2 >> 16));
    return ((uint32_t)lo & 0xFFFFU) | ((uint32_t)hi << 16);
}
static inline uint32_t __SADD16(uint32_t op1, uint32_t op2)
{
    return (((op1 & 0xFFFFU) + (op2 & 0xFFFFU)) & 0xFFFFU) | ((((op1 >> 16) + (op2 >> 16)) & 0xFFFFU) << 16);
}
static inline int32_t __QADD(int32_t op1, int32_t op2)
{
    const int64_t r = (int64_t)op1 + (int64_t)op2;
    return r > INT32_MAX ? INT32_MAX : (r < INT32_MIN ? INT32_MIN : (int32_t)r);
}
static inline int32_t __QSUB(int32_t op1, int32_t op2)
{
    const int64_t r = (int64_t)op1 - (int64_t)op2;
    return r > INT32_MAX ? INT32_MAX : (r < INT32_MIN ? INT32_MIN : (int32_t)r);
}
#define __PKHBT(ARG1, ARG2, ARG3) \
    ((((uint32_t)(ARG1)) & 0x0000FFFFUL) | ((((uint32_t)(ARG2)) << (ARG3)) & 0xFFFF0000UL))
static inline uint8_t __CLZ(uint32_t value) { return value == 0U ? 32U : (uint8_t)__builtin_clz(value); }

/* float -> uint32 with Cortex-M7 VCVT.U32.F32 semantics (negative/NaN -> 0, saturating) */
static inline uint32_t lxr_f2u32(float x)
{
    if (!(x > 0.0f)) return 0u;
    if (x >= 4294967296.0f) return 0xFFFFFFFFu;
    return (uint32_t)x;
}

typedef struct { int unused; } RNG_HandleTypeDef;
#endif
