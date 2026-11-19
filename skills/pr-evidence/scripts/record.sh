#!/usr/bin/env bash
# Record a shux window (or one pane) to an mp4, from shux's own snapshots.
#
# Usage:
#   record.sh -s SESSION [-w WINDOW | -p PANE] -o OUT.mp4 (-u STOPFILE | -t SECONDS)
#             [-c COLSxROWS] [-f FPS] [-x SPEED] [-k KEEP_DIR]
#
#   -s  shux session to record (uses the caller's XDG_RUNTIME_DIR / SHUX_SOCKET;
#       $SHUX_BIN picks the shux binary, default `shux` on PATH. Not $SHUX:
#       shux sets SHUX=1 inside every pane)
#   -w  window number, name or id (default: the session's active window)
#   -p  record one pane instead of the window (pane id)
#   -o  output mp4
#   -u  stop when this file exists (preferred: the driver touches it when done)
#   -t  stop after this many seconds (an upper bound; required with -u as a cap)
#   -c  compose the window at this size, e.g. 160x30 (window recordings only)
#   -f  capture rate, frames per second (default 4)
#   -x  playback speed: 1 = real time, 1.5 = 1.5x faster (default 1.5)
#
# Playback speed is true: frames are encoded at the rate they were actually
# captured, times -x, so a 10 s event plays in 10/x s whatever the snapshot cost.
set -euo pipefail

session="" window="" pane="" out="" stopfile="" seconds="" fps=4 speed=1.5 size=""
while getopts "s:w:p:o:u:t:c:f:x:" opt; do
  case "$opt" in
    s) session=$OPTARG ;; w) window=$OPTARG ;; p) pane=$OPTARG ;; o) out=$OPTARG ;;
    u) stopfile=$OPTARG ;; t) seconds=$OPTARG ;; f) fps=$OPTARG ;; x) speed=$OPTARG ;;
    c) size=$OPTARG ;;
    *) sed -n '2,19p' "$0" >&2; exit 2 ;;
  esac
done
[ -n "$session" ] && [ -n "$out" ] && [ -n "$seconds" ] || {
  echo "record.sh: -s, -o and -t are required (-t caps every recording)" >&2; exit 2; }
shux=${SHUX_BIN:-shux}
[ -n "$pane" ] && [ -n "$size" ] && {
  echo "record.sh: -c sizes a window recording; a pane records at its own size" >&2; exit 2; }
for tool in "$shux" ffmpeg ffprobe perl; do
  command -v "$tool" >/dev/null || { echo "record.sh: $tool not found" >&2; exit 2; }
done

sized=() win=()
[ -n "$size" ] && sized=(--cols "${size%x*}" --rows "${size#*x}")
[ -n "$window" ] && win=(-w "$window")
frames=$(mktemp -d)
trap 'rm -rf "$frames"' EXIT

now() { perl -MTime::HiRes=time -e 'printf "%.3f\n", time()'; }
interval=$(awk -v f="$fps" 'BEGIN{printf "%.3f", 1/f}')
start=$(now); n=0
while :; do
  t=$(now)
  [ -n "$stopfile" ] && [ -e "$stopfile" ] && break
  awk -v a="$start" -v b="$t" -v s="$seconds" 'BEGIN{exit !(b-a>=s)}' && break
  file=$(printf '%s/%05d.png' "$frames" "$n")
  if [ -n "$pane" ]; then
    "$shux" pane snapshot -s "$session" -p "$pane" -o "$file" >/dev/null
  else
    "$shux" window snapshot -s "$session" ${win[@]+"${win[@]}"} ${sized[@]+"${sized[@]}"} -o "$file" >/dev/null
  fi
  [ -s "$file" ] || { echo "record.sh: snapshot $n is empty" >&2; exit 1; }
  n=$((n + 1))
  left=$(awk -v i="$interval" -v a="$t" -v b="$(now)" 'BEGIN{d=i-(b-a); printf "%.3f", (d>0?d:0)}')
  # shellcheck disable=SC2016  # perl's own $ARGV
  perl -e 'select(undef,undef,undef,$ARGV[0])' "$left"
done
elapsed=$(awk -v a="$start" -v b="$(now)" 'BEGIN{printf "%.3f", b-a}')
[ "$n" -ge 2 ] || { echo "record.sh: only $n frame(s) captured" >&2; exit 1; }

captured=$(awk -v n="$n" -v e="$elapsed" 'BEGIN{printf "%.4f", n/e}')
rate=$(awk -v c="$captured" -v x="$speed" 'BEGIN{printf "%.4f", c*x}')
# Even dimensions for yuv420p; never upscale (crisp source pixels). Pin the
# level: left alone, x264 can pick 6.x (see check_video.sh).
IFS=x read -r w h < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
  -of csv=s=x:p=0 "$frames/00000.png")
level=4.2
[ $(( ((w + 15) / 16) * ((h + 15) / 16) )) -gt 8704 ] && level=5.1
ffmpeg -hide_banner -loglevel error -y -framerate "$rate" -i "$frames/%05d.png" \
  -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2:color=black" \
  -c:v libx264 -profile:v high -level:v "$level" -preset slow -crf 16 \
  -pix_fmt yuv420p -movflags +faststart "$out"
bash "$(dirname "$0")/check_video.sh" "$out"
printf 'record.sh: %d frames over %.1fs (%.2f fps captured) -> %s at %sx, %.1fs long\n' \
  "$n" "$elapsed" "$captured" "$out" "$speed" "$(awk -v e="$elapsed" -v x="$speed" 'BEGIN{print e/x}')"
