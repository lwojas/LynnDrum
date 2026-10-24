/* host platform layer for lxr_seq (ours) */
#ifndef LXRSEQ_HAL_H
#define LXRSEQ_HAL_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <math.h>
#define UNUSED(x) ((void)(x))
#define INDTCM
#define INDTCMZ
static inline uint8_t __CLZ(uint32_t value) { return value == 0U ? 32U : (uint8_t)__builtin_clz(value); }
#endif
