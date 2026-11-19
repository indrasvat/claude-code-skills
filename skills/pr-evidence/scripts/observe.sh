#!/usr/bin/env bash
# An independent observer for timing and lifecycle evidence: a running clock,
# then each probe's live output, redrawn in place. Run it in its own pane next
# to the pane that drives the scenario, so the recording shows the system's real
# state over time, not the driver's own account of it.
#
# Usage:
#   observe.sh -u STOPFILE [-i SECONDS] -- 'LABEL::COMMAND' ['LABEL::COMMAND' ...]
#
#   -u  stop when this file exists
#   -i  redraw interval (default 0.5)
#
# Example probes:
#   'daemon state::ps -o pid=,stat=,command= -p "$(cat "$RT/app.pid")"'
#   'socket::test -S "$RT/app.sock" && echo listening || echo gone'
#   'needle procs::ps -axo pid=,command= | grep -E "^ *[0-9]+ sleep 5[0-9]{4}$" || echo none'
#
# Probes must be read-only: never a command that can start or change what it
# watches (a CLI that auto-starts a daemon restarts the one just stopped).
set -euo pipefail

stopfile="" interval=0.5
while getopts "u:i:" opt; do
  case "$opt" in u) stopfile=$OPTARG ;; i) interval=$OPTARG ;; *) exit 2 ;; esac
done
shift $((OPTIND - 1))
[ "${1:-}" = "--" ] && shift
[ -n "$stopfile" ] && [ "$#" -gt 0 ] || { sed -n '2,15p' "$0" >&2; exit 2; }

C=$'\e[36m' B=$'\e[1m' D=$'\e[2m' X=$'\e[0m' K=$'\e[K'
start=$(perl -MTime::HiRes=time -e 'printf "%.3f", time()')
printf '\e[?25l\e[2J'
trap 'printf "\e[?25h"' EXIT
while [ ! -e "$stopfile" ]; do
  out=$(
    t=$(perl -MTime::HiRes=time -e 'printf "%.3f", time()')
    printf '%s%s⏱  %s  +%5.1fs%s%s\n' "$B" "$C" "$(date +%H:%M:%S)" \
      "$(awk -v a="$start" -v b="$t" 'BEGIN{print b-a}')" "$X" "$K"
    for probe in "$@"; do
      label=${probe%%::*} cmd=${probe#*::}
      # Clear the blank separator row too: after a resize it still holds
      # text from an earlier layout, and the redraw only clears written rows.
      printf '%s\n%s%s%s%s\n' "$K" "$B" "$label" "$X" "$K"
      bash -c "$cmd" 2>&1 | head -12 | sed "s/\$/$K/;s/^/  /" || true
    done
  )
  printf '\e[H%s\e[J' "$out"
  # shellcheck disable=SC2016  # perl's own $ARGV
  perl -e 'select(undef,undef,undef,$ARGV[0])' "$interval"
done
printf '\n%sobserver stopped%s\n' "$D" "$X"
