#!/usr/bin/env bash
# Gate a video before it is attached: it must play on a phone, not just on the
# desktop browser that made it. iPhone Safari shows a crossed-out play button
# for files desktop Chrome and macOS play fine.
#
# Usage: check_video.sh VIDEO.mp4 [POSTER.png]
#
# Fails when the stream is:
#   - not H.264, or not yuv420p (yuvj420p from JPEG frames included)
#   - H.264 level above 4.2 (5.1 only above ~2.1 MP; ffmpeg picks 6.x on its
#     own when the input timing is odd, as after looping stills or stacking)
#   - variable or bogus frame rate (r_frame_rate 1000000/1 from looped stills)
#   - odd-sized, or with the moov atom after mdat (no +faststart)
# Every failure line names the ffmpeg flag that fixes it.
#
# Writes the FIRST frame to POSTER.png (default: VIDEO.poster.png): players show
# it before anyone presses play, so read it. A shell prompt or an empty pane
# there is a leak or a dud.
#
# Last line is the contract:
#   check_video: PASS|FAIL file=… level=… size=WxH fps=… duration=…s poster=…
# Exit 0 on PASS, 1 on FAIL, 2 when the file cannot be read as video.
set -euo pipefail

v="${1:?usage: check_video.sh VIDEO.mp4 [POSTER.png]}"
poster="${2:-${v%.*}.poster.png}"
fail=0
bad() { printf 'check_video: FAIL %s\n' "$*" >&2; fail=1; }

# One field per call, value only: csv output grows trailing fields when the
# stream carries side data (a phone video's rotation), so never parse csv.
probe() { ffprobe -v error -select_streams v:0 -show_entries "stream=$1" -of default=nw=1:nk=1 "$v" | head -1; }
codec=$(probe codec_name || true)
[ -n "$codec" ] || { echo "check_video: FAIL $v has no video stream ffprobe can read" >&2; exit 2; }
pix=$(probe pix_fmt)
level=$(probe level)
w=$(probe width)
h=$(probe height)
rfr=$(probe r_frame_rate)
afr=$(probe avg_frame_rate)
dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$v")

[ "$codec" = h264 ] || bad "codec $codec: re-encode with -c:v libx264 -profile:v high"
[ "$pix" = yuv420p ] || bad "pix_fmt $pix: add -pix_fmt yuv420p (and -color_range tv for yuvj input)"
if [ $((w % 2)) -ne 0 ] || [ $((h % 2)) -ne 0 ]; then
  bad "odd size ${w}x${h}: add -vf pad=ceil(iw/2)*2:ceil(ih/2)*2"
fi

# 8192 macroblocks (about 2.1 MP, e.g. 1920x1088) is the largest frame level 4.x allows.
mbs=$(( ((w + 15) / 16) * ((h + 15) / 16) ))
max=42
[ "$mbs" -gt 8192 ] && max=51
[ "$level" -le "$max" ] || bad "H.264 level $level for ${w}x${h}: add -level:v $([ "$max" = 42 ] && echo 4.2 || echo 5.1)"

num=${rfr%/*} den=${rfr#*/}
if [ "$den" -le 0 ] || [ $((num / den)) -gt 120 ]; then
  bad "r_frame_rate $rfr is a bogus timebase: add an fps=N filter and -r N"
fi
[ "$rfr" = "$afr" ] || bad "variable frame rate (r=$rfr avg=$afr): add an fps=N filter and -r N"

first=$(head -c 1048576 "$v" | LC_ALL=C grep -aoE -m1 'moov|mdat' | head -1 || true)
[ "$first" = moov ] || bad "moov atom after mdat: add -movflags +faststart"

ffmpeg -v error -y -i "$v" -frames:v 1 "$poster"
verdict=PASS
[ "$fail" -eq 0 ] || verdict=FAIL
printf 'check_video: %s file=%s level=%s size=%sx%s fps=%s duration=%.1fs poster=%s\n' \
  "$verdict" "$v" "$level" "$w" "$h" "$rfr" "$dur" "$poster"
exit "$fail"
