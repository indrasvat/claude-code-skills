#!/usr/bin/env bash
# Record a shux window (or one pane) to an mp4, from shux's own snapshots.
#
# Usage:
#   record.sh -s SESSION [-w WINDOW | -p PANE] -o OUT.mp4 (-u STOPFILE | -t SECONDS)
#             [-c COLSxROWS] [-f FPS] [-x SPEED]
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
# Playback speed is true: each frame stays on screen from its own capture to the
# next, divided by -x, so a 10 s event plays in 10/x s and a snapshot that
# stalls shows as the pause it was, not as time spread over every frame.
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
  echo "$t" >>"$frames/times"
  n=$((n + 1))
  left=$(awk -v i="$interval" -v a="$t" -v b="$(now)" 'BEGIN{d=i-(b-a); printf "%.3f", (d>0?d:0)}')
  # shellcheck disable=SC2016  # perl's own $ARGV
  perl -e 'select(undef,undef,undef,$ARGV[0])' "$left"
done
end=$(now)
elapsed=$(awk -v a="$start" -v b="$end" 'BEGIN{printf "%.3f", b-a}')
[ "$n" -ge 2 ] || { echo "record.sh: only $n frame(s) captured" >&2; exit 1; }

captured=$(awk -v n="$n" -v e="$elapsed" 'BEGIN{printf "%.4f", n/e}')
# A concat list holds each frame for its real span; the demuxer wants the last
# file listed twice for its duration to count.
awk -v end="$end" -v x="$speed" -v d="$frames" '{t[NR] = $1} END {
  for (i = 1; i <= NR; i++) {
    printf "file \047%s/%05d.png\047\nduration %.4f\n", d, i - 1, ((i < NR ? t[i + 1] : end) - t[i]) / x
  }
  printf "file \047%s/%05d.png\047\n", d, NR - 1
}' "$frames/times" >"$frames/list.txt"
# Phones need a constant rate: resample the timed frames onto one.
rate=$(awk -v f="$fps" -v x="$speed" 'BEGIN{r = f * x; r = (r == int(r)) ? r : int(r) + 1; print (r < 15 ? 15 : r)}')
# Even dimensions for yuv420p; never upscale (crisp source pixels). Pin the
# level: left alone, x264 can pick 6.x (see check_video.sh).
IFS=x read -r w h < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
  -of csv=s=x:p=0 "$frames/00000.png")
level=4.2
[ $(( ((w + 15) / 16) * ((h + 15) / 16) )) -gt 8704 ] && level=5.1
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$frames/list.txt" \
  -vf "fps=$rate,pad=ceil(iw/2)*2:ceil(ih/2)*2:color=black" \
  -c:v libx264 -profile:v high -level:v "$level" -preset slow -crf 16 \
  -pix_fmt yuv420p -movflags +faststart "$out"
bash "$(dirname "$0")/check_video.sh" "$out"
printf 'record.sh: %d frames over %.1fs (%.2f fps captured) -> %s at %sx, %.1fs long\n' \
  "$n" "$elapsed" "$captured" "$out" "$speed" "$(awk -v e="$elapsed" -v x="$speed" 'BEGIN{print e/x}')"
