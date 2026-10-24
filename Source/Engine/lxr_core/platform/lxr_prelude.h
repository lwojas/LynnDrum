/* force-included into every lxr_core translation unit */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <math.h>
#include <stdio.h>
/* all remaining __attribute__ uses are ITCM/DTCM section placement (meaningless on the host);
 * defined after the system headers so their own attributes are untouched */
#define __attribute__(x)
#include "lxr_state.h"
