#!/bin/sh
# usage: run_scenarios.sh <renderer> <scenario_dir> <out_manifest>
# Runs every scenario, writes "name dac1hash dac2hash" lines (sorted). Exit 1 on any failure.
R="$1"; D="$2"; M="$3"; T=$(mktemp -d); fail=0
: > "$M.tmp"
for f in "$D"/*.lxr; do
  n=$(basename "$f" .lxr)
  o=$("$R" "$f" -o "$T/x" 2>"$T/err") || { echo "FAIL $n: $(head -2 "$T/err")"; fail=1; continue; }
  echo "$n $(echo "$o" | sed 's/.*dac1=\([0-9a-f]*\) dac2=\([0-9a-f]*\)/\1 \2/')" >> "$M.tmp"
done
sort "$M.tmp" > "$M"; rm -f "$M.tmp"; rm -rf "$T"
echo "$(wc -l < "$M") scenarios ok"; exit $fail
