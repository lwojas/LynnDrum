#!/bin/sh
# Regenerates Source/UI/web/src/readout.golden.json from the derived engine (needs build-core/lxr_core built).
set -e
R="$(cd "$(dirname "$0")/../.." && pwd)"
cc -o /tmp/readout_tables "$R/Tools/params/readout_tables.c" -I"$R/Source/Engine/lxr_core/platform" -I"$R/Source/Engine/lxr_core/inc" -include "$R/Source/Engine/lxr_core/platform/lxr_prelude.h" "$R/build-core/lxr_core/liblxr_core.a" -lm
/tmp/readout_tables > "$R/Source/UI/web/src/readout.golden.json"
