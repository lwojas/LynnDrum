/* Host shim for the STM32 HAL / CMSIS surface that the LXR DSP and parameter
 * code touches. Only what the reference harness needs; behaviour follows the
 * ARMv7E-M definitions. Not part of upstream. */
#ifndef LXR_HOST_STM32F7XX_HAL_H
#define LXR_HOST_STM32F7XX_HAL_H

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

#define UNUSED(x) ((void)(x))

/* ---- memory placement attributes are meaningless on the host ---- */
#define INDTCM
#define INDTCMZ

/* ---- ARM intrinsics (CMSIS cmsis_gcc.h / cmsis_compiler.h semantics) ---- */
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

static inline uint32_t __USAT(int32_t val, uint32_t sat)
{
    if (sat <= 31U) {
        const uint32_t max = ((1U << sat) - 1U);
        if (val > (int32_t)max) return max;
        if (val < 0) return 0U;
    }
    return (uint32_t)val;
}

static inline int32_t lxr_sat16_(int32_t v) { return v > 32767 ? 32767 : (v < -32768 ? -32768 : v); }

/* packed signed halfword saturating add / subtract, plain (modular) add */
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
    const uint32_t lo = ((op1 & 0xFFFFU) + (op2 & 0xFFFFU)) & 0xFFFFU;
    const uint32_t hi = ((op1 >> 16) + (op2 >> 16)) & 0xFFFFU;
    return lo | (hi << 16);
}

/* 32-bit saturating add / subtract */
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

/* pack halfword bottom (op1) with top (op2 << shift) */
#define __PKHBT(ARG1, ARG2, ARG3) \
    ((((uint32_t)(ARG1)) & 0x0000FFFFUL) | ((((uint32_t)(ARG2)) << (ARG3)) & 0xFFFF0000UL))
#define __PKHTB(ARG1, ARG2, ARG3) \
    ((((uint32_t)(ARG1)) & 0xFFFF0000UL) | ((((uint32_t)(ARG2)) >> (ARG3)) & 0x0000FFFFUL))

/* dual 16x16 multiply, accumulate into 64 bit */
static inline uint64_t __SMLALD(uint32_t op1, uint32_t op2, uint64_t acc)
{
    return (uint64_t)((int64_t)acc
        + (int64_t)(int16_t)(op1 & 0xFFFFU) * (int16_t)(op2 & 0xFFFFU)
        + (int64_t)(int16_t)(op1 >> 16) * (int16_t)(op2 >> 16));
}

static inline uint8_t __CLZ(uint32_t value)
{
    return value == 0U ? 32U : (uint8_t)__builtin_clz(value);
}

/* float -> uint32 with the Cortex-M7 (VCVT.U32.F32) semantics the FM code relies on:
 * round toward zero, negative and NaN -> 0, overflow saturates. Plain C casts of
 * such values are undefined and differ between ARM and x86-64. (patch H5) */
static inline uint32_t lxr_f2u32(float x)
{
    if (!(x > 0.0f)) return 0u;
    if (x >= 4294967296.0f) return 0xFFFFFFFFu;
    return (uint32_t)x;
}

/* ---- FPU / APSR ----
 * The host cannot expose the condition flags of the preceding instruction.
 * Oscillator.c:calcNoise() reads APSR.V; the harness patch (see patches/)
 * replaces that read with an explicit signed-overflow computation. */
typedef struct { uint32_t w; } APSR_Type_;

/* ---- RNG (deterministic xorshift32, seeded by the harness) ---- */
typedef struct { int unused; } RNG_HandleTypeDef;
extern RNG_HandleTypeDef hrng;
uint32_t lxr_host_rng_next(void);
void lxr_host_rng_seed(uint32_t seed);
#define HAL_RNG_GetRandomNumber(h) (lxr_host_rng_next())

typedef struct { int unused; } SPI_HandleTypeDef;

/* interrupt / tick bookkeeping used by a few DSP files */
extern volatile uint32_t systick_ticks;
#define __disable_irq() ((void)0)
#define __enable_irq()  ((void)0)

#ifdef __cplusplus
}
#endif
#endif
