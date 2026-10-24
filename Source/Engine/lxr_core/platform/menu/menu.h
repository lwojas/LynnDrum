/* Only the mod-target table types of upstream menu.h (the table itself is derived data). */
#ifndef LXR_PLATFORM_MENU_H
#define LXR_PLATFORM_MENU_H
#include "lxr_state.h"
#include "lxr_text_ids.h"
#define pgm_read_byte(x) (*((uint8_t *)(x)))
#define pgm_read_word(x) (*((uint16_t *)(x)))
#define pgm_read_dword(x) (*((uint32_t *)(x)))
typedef struct ModTargStruct { const uint8_t nameIdx; const uint16_t param; } ModTarg;
typedef struct ModTargetVoiceOffsetStruct { uint8_t start; uint8_t end; } ModTargetVoiceOffset;
extern const ModTarg modTargets[];
extern const ModTargetVoiceOffset modTargetVoiceOffsets[6];
extern uint8_t paramToModTarget[END_OF_SOUND_PARAMETERS];
#endif
