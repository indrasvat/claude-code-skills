#!/usr/bin/env bash
# Gate a video before it is attached: it must play on a phone, not just on the
# desktop browser that made it. iPhone Safari shows a crossed-out play button
# for files desktop Chrome and macOS play fine.
#
# Usage: check_video.sh VIDEO.mp4 [POSTER.png]
#
# Fails when the file is not an MP4 whose every frame decodes, or its H.264
# stream is not High-or-lower, yuv420p, constant-rate, even-sized and within
# its level's frame-size and macroblock-rate limits; when the level is above
# 4.2 for a frame that fits 4.2 (ffmpeg picks 6.x on its own after looping
# stills or stacking); or when the moov box comes after mdat (no faststart).
# Every failure line names the ffmpeg flag that fixes it.
#
# Writes the FIRST frame to POSTER.png (default: VIDEO.poster.png): players show
# it before anyone presses play, so read it. A shell prompt or an empty pane
# there is a leak or a dud.
#
# Last line is the contract:
#   check_video: PASS|FAIL file=… level=… size=WxH fps=… duration=…s poster=…
# Exit 0 on PASS, 1 on FAIL, 2 on bad usage or a file that is not video.
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
  echo "usage: check_video.sh VIDEO.mp4 [POSTER.png]" >&2
  exit 2
fi
v=$1
poster="${2:-${v%.*}.poster.png}"
fail=0
bad() { printf 'check_video: FAIL %s\n' "$*" >&2; fail=1; }

# One field per call, value only: csv output grows trailing fields when the
# stream carries side data (a phone video's rotation), so never parse csv.
probe() { ffprobe -v error -select_streams v:0 -show_entries "stream=$1" -of default=nw=1:nk=1 "$v" | head -1; }
codec=$(probe codec_name || true)
[ -n "$codec" ] || { echo "check_video: FAIL $v has no video stream ffprobe can read" >&2; exit 2; }
format=$(ffprobe -v error -show_entries format=format_name -of default=nw=1:nk=1 "$v")
pix=$(probe pix_fmt)
level=$(probe level)
w=$(probe width)
h=$(probe height)
rfr=$(probe r_frame_rate)
afr=$(probe avg_frame_rate)
dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$v")

# Which of moov/mdat comes first among the top-level ISO BMFF boxes, read by
# size and type (a byte grep is fooled by those letters inside other boxes).
first_box() {
  local off=0 total size type n=0
  total=$(wc -c <"$v" | tr -d ' ')
  while [ "$off" -lt "$total" ] && [ "$n" -lt 64 ]; do
    # shellcheck disable=SC2046  # split od's bytes into positional args
    set -- $(od -An -tu1 -j "$off" -N 16 "$v")
    [ $# -ge 8 ] || return 0
    size=$(( ($1 << 24) | ($2 << 16) | ($3 << 8) | $4 ))
    type=$(tail -c +$((off + 5)) "$v" | head -c 4)
    if [ "$size" -eq 1 ] && [ $# -ge 16 ]; then  # 64-bit "largesize"
      size=$(( ($9 << 56) | (${10} << 48) | (${11} << 40) | (${12} << 32) | (${13} << 24) | (${14} << 16) | (${15} << 8) | ${16} ))
    fi
    case $type in moov|mdat) echo "$type"; return 0 ;; esac
    [ "$size" -ge 8 ] || return 0  # 0 = runs to the end of the file
    off=$((off + size)) n=$((n + 1))
  done
}

case ",$format," in *,mp4,*) ;; *) bad "container $format is not MP4: remux with ffmpeg -i in -c copy -movflags +faststart out.mp4" ;; esac
[ "$codec" = h264 ] || bad "codec $codec: re-encode with -c:v libx264 -profile:v high"
[ "$pix" = yuv420p ] || bad "pix_fmt $pix: add -pix_fmt yuv420p (and -color_range tv for yuvj input)"
if [ $((w % 2)) -ne 0 ] || [ $((h % 2)) -ne 0 ]; then
  bad "odd size ${w}x${h}: add -vf pad=ceil(iw/2)*2:ceil(ih/2)*2"
fi

# H.264 Annex A, table A-1: level -> max macroblocks per second, max frame size
# in macroblocks. A frame dimension may not exceed sqrt(8 * max frame size).
case $level in
  10) lim="1485 99" ;; 11) lim="3000 396" ;; 12) lim="6000 396" ;; 13|20) lim="11880 396" ;;
  21) lim="19800 792" ;; 22) lim="20250 1620" ;; 30) lim="40500 1620" ;; 31) lim="108000 3600" ;;
  32) lim="216000 5120" ;; 40|41) lim="245760 8192" ;; 42) lim="522240 8704" ;;
  50) lim="589824 22080" ;; 51|52) lim="983040 36864" ;; *) lim="" ;;
esac
num=${rfr%/*} den=${rfr#*/}
mbw=$(( (w + 15) / 16 )) mbh=$(( (h + 15) / 16 ))
mbs=$((mbw * mbh))
if [ -z "$lim" ]; then
  bad "H.264 level $level is unknown or unsupported: add -level:v 4.2"
else
  read -r maxmbps maxfs <<<"$lim"
  [ "$mbs" -le "$maxfs" ] || bad "${w}x${h} is $mbs macroblocks, over level $level's $maxfs: scale down or raise -level:v"
  side=$(awk -v f="$maxfs" 'BEGIN{printf "%d", sqrt(8 * f)}')
  [ "$mbw" -le "$side" ] && [ "$mbh" -le "$side" ] || bad "${w}x${h} has a side over level $level's $side macroblocks: scale it"
  rate=$((mbs * num / (den > 0 ? den : 1)))
  [ "$rate" -le "$maxmbps" ] || bad "${w}x${h} at $rfr fps is $rate macroblocks/s, over level $level's $maxmbps: lower -r or scale down"
fi
# Phones decode up to 4.2 everywhere; 5.1 only when the frame needs it.
max=42
[ "$mbs" -gt 8704 ] && max=51
[ "$level" -le "$max" ] || bad "H.264 level $level for ${w}x${h}: add -level:v $([ "$max" = 42 ] && echo 4.2 || echo 5.1)"

if [ "$den" -le 0 ] || [ $((num / den)) -gt 120 ]; then
  bad "r_frame_rate $rfr is a bogus timebase: add an fps=N filter and -r N"
fi
[ "$rfr" = "$afr" ] || bad "variable frame rate (r=$rfr avg=$afr): add an fps=N filter and -r N"

[ "$(first_box)" = moov ] || bad "moov box is not before mdat: add -movflags +faststart"

errs=$(ffmpeg -v error -xerror -i "$v" -map 0:v:0 -f null - 2>&1 || echo "exit $?")
[ -z "$errs" ] || bad "frames do not decode cleanly ($(printf '%s' "$errs" | head -1)): re-encode"

ffmpeg -v error -y -i "$v" -frames:v 1 "$poster" || bad "could not write the poster frame"
verdict=PASS
[ "$fail" -eq 0 ] || verdict=FAIL
printf 'check_video: %s file=%s level=%s size=%sx%s fps=%s duration=%.1fs poster=%s\n' \
  "$verdict" "$v" "$level" "$w" "$h" "$rfr" "$dur" "$poster"
exit "$fail"
