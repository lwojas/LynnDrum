#!/bin/sh
# usage: run_seq_scenarios.sh <lxr_ref_seq> <scenario_dir> <out_dir>
# Writes <out_dir>/<name>.ev (the logical event stream) for every scenario; exit 1 on any failure.
R="$1"; D="$2"; O="$3"; fail=0; mkdir -p "$O"
for f in "$D"/*.lxr; do
  n=$(basename "$f" .lxr)
  case "$n" in dev_*) [ -n "$WITH_DEV" ] || continue;; esac
  "$R" "$f" -o "$O/.x" --events "$O/$n.ev" >/dev/null 2>"$O/.err" || { echo "FAIL $n: $(head -2 "$O/.err")"; fail=1; }
done
rm -f "$O/.x"* "$O/.err"; echo "$(ls "$O"/*.ev | wc -l | tr -d ' ') event streams"; exit $fail
