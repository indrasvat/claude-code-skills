#!/usr/bin/env bash
# Tests for the pr-evidence skill's scripts, against real ffmpeg/uv (and shux
# when present). Each case guards a failure that reached a real PR.
#
# Usage: tests/pr-evidence/test.sh [SKILL_DIR]   (default: skills/pr-evidence)
set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
S=$(cd "${1:-$here/../../skills/pr-evidence}" && pwd)
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
cd "$W" || exit 1

if [ -t 1 ]; then G=$'\e[32m' R=$'\e[31m' Y=$'\e[33m' C=$'\e[1;36m' X=$'\e[0m'; else G='' R='' Y='' C='' X=''; fi
pass=0 fail=0 skip=0
ok() { printf '  %s✓%s %s\n' "$G" "$X" "$1"; pass=$((pass + 1)); }
ko() { printf '  %s✗ %s%s\n' "$R" "$1" "$X"; [ -n "${2:-}" ] && printf '%s\n' "$2" | sed 's/^/      /'; fail=$((fail + 1)); }
sk() { printf '  %s- skip: %s%s\n' "$Y" "$1" "$X"; skip=$((skip + 1)); }
check() { local name=$1; shift; if "$@"; then ok "$name"; else ko "$name"; fi; }
section() { printf '%s▶ %s%s\n' "$C" "$1" "$X"; }
# expect NAME WANT_EXIT GREP_OR_EMPTY -- CMD...: run CMD, check exit code and output.
expect() {
  local name=$1 want=$2 needle=$3 out rc
  shift 4
  out=$("$@" 2>&1); rc=$?
  if [ "$rc" -ne "$want" ]; then ko "$name (exit $rc, want $want)" "$out"; return; fi
  if [ -n "$needle" ] && ! grep -qE -- "$needle" <<<"$out"; then ko "$name (no /$needle/)" "$out"; return; fi
  ok "$name"
}
clip() { # OUT [extra ffmpeg output args...]: a 2 s 15 fps test clip
  local out=$1; shift
  ffmpeg -v error -y -f lavfi -i testsrc2=s=320x240:r=15 -t 2 "$@" "$out"
}
ENC=(-c:v libx264 -profile:v high -pix_fmt yuv420p)

section "check_video.sh: the phone-playback gate"
clip good.mp4 "${ENC[@]}" -level:v 4.2 -movflags +faststart
expect "passes a phone-safe clip" 0 '^check_video: PASS' -- bash "$S/scripts/check_video.sh" good.mp4
check "writes the poster frame" test -s good.poster.png
ffmpeg -v error -y -display_rotation 90 -i good.mp4 -c copy -movflags +faststart rotated.mp4
expect "reads a phone video with rotation side data" 0 '^check_video: PASS' -- bash "$S/scripts/check_video.sh" rotated.mp4
clip l62.mp4 "${ENC[@]}" -level:v 6.2 -movflags +faststart
expect "rejects H.264 level 6.2" 1 'level 62' -- bash "$S/scripts/check_video.sh" l62.mp4
clip yuvj.mp4 -c:v libx264 -pix_fmt yuvj420p -movflags +faststart
expect "rejects yuvj420p and names the fix" 1 'pix_fmt yuv420p' -- bash "$S/scripts/check_video.sh" yuvj.mp4
clip slow.mp4 "${ENC[@]}" -level:v 4.2
expect "rejects a clip without faststart" 1 'faststart' -- bash "$S/scripts/check_video.sh" slow.mp4
ffmpeg -v error -y -f lavfi -i testsrc2=s=320x240:r=15 -t 2 \
  -vf "setpts='if(lt(N,10),N/15,10/15+(N-10)/4)/TB'" -fps_mode vfr "${ENC[@]}" -movflags +faststart vfr.mp4
expect "rejects a variable frame rate" 1 'frame rate' -- bash "$S/scripts/check_video.sh" vfr.mp4
ffmpeg -v error -y -i good.mp4 -c copy -metadata title=moov mkv.mkv && mv mkv.mkv mkv.mp4
expect "rejects a Matroska file named .mp4" 1 'container' -- bash "$S/scripts/check_video.sh" mkv.mp4
ffmpeg -v error -y -i good.mp4 -c copy -f mov -movflags +faststart qt.mp4
expect "rejects a QuickTime file named .mp4" 1 'QuickTime' -- bash "$S/scripts/check_video.sh" qt.mp4
ffmpeg -v error -y -f lavfi -i testsrc2=s=640x360:r=30 -t 4 "${ENC[@]}" -level:v 4.2 -movflags +faststart big.mp4
cp big.mp4 corrupt.mp4
python3 -I -c 'import sys,os; p=sys.argv[1]; n=os.path.getsize(p); f=open(p,"r+b"); f.seek(n*6//10); f.write(bytes(n-n*6//10))' corrupt.mp4
expect "rejects a clip whose frames do not decode" 1 'decode' -- bash "$S/scripts/check_video.sh" corrupt.mp4
ffmpeg -v error -y -f lavfi -i testsrc2=s=1920x1080:r=90 -t 0.5 "${ENC[@]}" -level:v 4.2 -movflags +faststart fast.mp4
expect "rejects 1080p90 that overruns level 4.2's macroblock rate" 1 'macroblocks' -- bash "$S/scripts/check_video.sh" fast.mp4
expect "usage error exits 2" 2 'usage' -- bash "$S/scripts/check_video.sh"

section "evidence_img.py: marks on stills"
ffmpeg -v error -y -f lavfi -i color=c=0x1e1e2e:s=720x456 -frames:v 1 frame.png
expect "marks by terminal cell" 0 'wrote' -- uv run -q "$S/scripts/evidence_img.py" mark frame.png -o marked.png \
  --cell 9x19 --box 2,3,10,1,bad,"broken" --box 2,8,10,1,good,"fixed"
expect "pairs base and branch" 0 'wrote' -- uv run -q "$S/scripts/evidence_img.py" pair frame.png marked.png \
  -o pair.png --labels "before · v1" "after · this PR"

section "evidence_video.py: compose, mark, sheet"
clip base.mp4 "${ENC[@]}"
ffmpeg -v error -y -f lavfi -i testsrc2=s=360x200:r=4 -t 3 "${ENC[@]}" branch.mp4
expect "stacks clips of different size and rate into a phone-safe file" 0 '^check_video: PASS' -- \
  uv run -q "$S/scripts/evidence_video.py" stack base.mp4 branch.mp4 -o stacked.mp4 --labels "before · v1" "after · this PR"
dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 stacked.mp4 2>/dev/null)
check "stack lasts as long as the longer clip ($dur s)" awk -v d="${dur:-0}" 'BEGIN{exit !(d>=2.9 && d<=3.2)}'
expect "marks a stretch of video" 0 '^check_video: PASS' -- \
  uv run -q "$S/scripts/evidence_video.py" mark good.mp4 -o marked.mp4 --from 0.5 --to 1.5 --box 10,10,100,40,bad,"wrong"
h=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=nw=1:nk=1 marked.mp4 2>/dev/null)
check "video marks get a legend bar above the frame ($h px)" test "${h:-0}" -gt 240
expect "builds a frame sheet to read a video without playing it" 0 'wrote' -- \
  uv run -q "$S/scripts/evidence_video.py" sheet stacked.mp4 -o sheet.png --frames 6
ffmpeg -v error -y -f lavfi -i testsrc2=s=321x240:r=15 -t 1 -c:v libx264 -pix_fmt yuv444p odd.mp4
expect "stacks an odd-width 4:4:4 clip over a 4:2:0 one" 0 '^check_video: PASS' -- \
  uv run -q "$S/scripts/evidence_video.py" stack odd.mp4 base.mp4 -o odd-stack.mp4 --labels a b
ffmpeg -v error -y -f lavfi -i testsrc2=s=320x240:r=15:d=1 -f lavfi -i sine=d=3 "${ENC[@]}" -c:a aac audio3.mp4
expect "holds to the longer clip's video, not its audio" 0 '^check_video: PASS' -- \
  uv run -q "$S/scripts/evidence_video.py" stack audio3.mp4 base.mp4 -o av-stack.mp4 --labels a b
dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 av-stack.mp4 2>/dev/null)
check "audio-padded stack lasts the 2 s of video ($dur s)" awk -v d="${dur:-0}" 'BEGIN{exit !(d>=1.9 && d<=2.2)}'
ffmpeg -v error -y -f lavfi -i testsrc2=s=320x240:r=4 -t 1 "${ENC[@]}" short.mp4
expect "builds a sheet of a 1 s, 4 fps clip" 0 'wrote' -- \
  uv run -q "$S/scripts/evidence_video.py" sheet short.mp4 -o short-sheet.png --frames 9
expect "refuses a reversed mark range" 2 'from' -- \
  uv run -q "$S/scripts/evidence_video.py" mark good.mp4 -o rev.mp4 --from 1.5 --to 0.5 --box 1,1,9,9,bad,x
ffmpeg -v error -y -f lavfi -i testsrc2=s=1920x480:r=15:d=1 "${ENC[@]}" wide.mp4
expect "stacks two 1920x480 clips at a level its own gate accepts" 0 '^check_video: PASS' -- \
  uv run -q "$S/scripts/evidence_video.py" stack wide.mp4 wide.mp4 -o wide-stack.mp4 --labels a b
# Phones store portrait video as landscape pixels plus a rotation; ffmpeg turns
# the frames upright, so sizes must come from the displayed frame.
ffmpeg -v error -y -f lavfi -i testsrc2=s=200x360:r=15:d=1 "${ENC[@]}" tall.mp4
ffmpeg -v error -y -display_rotation 90 -i tall.mp4 -c copy -movflags +faststart turned.mp4
expect "stacks a clip whose rotation turns it wider than the other" 0 '^check_video: PASS' -- \
  uv run -q "$S/scripts/evidence_video.py" stack tall.mp4 turned.mp4 -o turned-stack.mp4 --labels a b
w=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of default=nw=1:nk=1 turned-stack.mp4 2>/dev/null)
check "rotated stack is as wide as the upright frame ($w px)" test "${w:-0}" -eq 360

section "check_evidence.sh: the gate before posting"
cp good.mp4 demo.mp4 && cp marked.png still.png
printf '## Evidence\n\n![demo](./demo.mp4)\n\n![still](./still.png)\n' >ev.md
expect "passes a clean comment" 0 '^check_evidence: PASS' -- bash "$S/scripts/check_evidence.sh" ev.md
printf '## Evidence\n\nRan from %s/src/app\n\n![demo](./demo.mp4)\n' "$HOME" >home.md
expect "rejects a home path in the text" 1 'home' -- bash "$S/scripts/check_evidence.sh" home.md
printf '![gone](./missing.png)\n' >missing.md
expect "rejects a missing artifact" 1 'missing.png' -- bash "$S/scripts/check_evidence.sh" missing.md
cp l62.mp4 bad.mp4 && printf '![bad](./bad.mp4)\n' >badvid.md
expect "rejects a video that fails the phone gate" 1 'bad.mp4' -- bash "$S/scripts/check_evidence.sh" badvid.md
git init -q repo && cp still.png repo/ && printf '![s](./still.png)\n' >repo/ev.md
git -C repo add still.png
in_repo() { (cd repo && bash "$S/scripts/check_evidence.sh" ev.md); }
expect "rejects an artifact tracked by git" 1 'tracked' -- in_repo
printf '<video src=\x27gone.mp4\x27></video>\n<source src = "gone2.MP4">\n![ref][r]\n\n[r]: ./gone3.png\n' >html.md
expect "finds HTML and reference-style artifacts" 1 'artifacts=3' -- bash "$S/scripts/check_evidence.sh" html.md
# shellcheck disable=SC2016  # literal markdown, backticks included
printf '![d](./demo.mp4?raw=1#t=2)\n![s](<./still.png> "a title")\n\n```\n![x](./not-real.png)\n```\n' >tricky.md
expect "strips query/fragment and skips code blocks" 0 '^check_evidence: PASS' -- bash "$S/scripts/check_evidence.sh" tricky.md
# shellcheck disable=SC2016  # literal markdown, backticks included
printf '![s](./still.png)\n\n    ![x](./indented.png)\n\n````\n```\n![y](./inner.png)\n```\n````\n' >code.md
expect "skips indented and nested fenced code" 0 '^check_evidence: PASS' -- bash "$S/scripts/check_evidence.sh" code.md
# shellcheck disable=SC2016  # literal markdown, backticks included
printf '````\n````~\n````\n![live](./live-missing.png)\n' >fence.md
expect "a fence closes only on a bare run of its own character" 1 'live-missing.png' -- bash "$S/scripts/check_evidence.sh" fence.md
printf '![f](file:///etc/a.png)\n' >file.md
expect "rejects a file:// reference" 1 'local path' -- bash "$S/scripts/check_evidence.sh" file.md
printf 'token ghp_%s\n' "abcdefghijklmnopqrstuvwxyz0123456789" >tok.md
expect "rejects a token-shaped string" 1 'token' -- bash "$S/scripts/check_evidence.sh" tok.md
expect "fails closed when HOME is unset" 1 'HOME' -- env -u HOME bash "$S/scripts/check_evidence.sh" ev.md
expect "usage error exits 2" 2 'usage' -- bash "$S/scripts/check_evidence.sh"

section "doctor.sh: the preflight contract"
expect "prints the contract line and the skill dir" 0 "^doctor: core=ok .* skill=$S\$" -- bash "$S/scripts/doctor.sh"
expect "checks the shux binary SHUX_BIN names" 0 'terminal=missing' -- env SHUX_BIN=/no/such/shux bash "$S/scripts/doctor.sh"
# shellcheck disable=SC2016  # the literal string is the point: it must not run
expect "treats SHUX_BIN as a name, never as code" 0 'terminal=missing' -- env SHUX_BIN='$(printf shux)' bash "$S/scripts/doctor.sh"
expect "outside a repo, cannot promise a comment will post" 0 'publish=manual' -- env -u GH_REPO bash "$S/scripts/doctor.sh"
if gh auth status >/dev/null 2>&1; then
  in_checkout() { (cd "$here" && env -u GH_REPO bash "$S/scripts/doctor.sh"); }
  expect "in a checkout gh can comment on, publishes with --attach" 0 'publish=attach' -- in_checkout
else
  sk "gh not logged in: the publish=attach case"
fi

section "record.sh + observe.sh: timing"
# A stand-in shux: frame 1 is red and its snapshot stalls 2 s, the rest are black.
ffmpeg -v error -y -f lavfi -i color=c=red:s=64x64 -frames:v 1 red.png
ffmpeg -v error -y -f lavfi -i color=c=black:s=64x64 -frames:v 1 black.png
cat >fakeshux <<EOF
#!/usr/bin/env bash
while [ "\$#" -gt 0 ]; do [ "\$1" = -o ] && out=\$2; shift; done
n=\$(cat "$W/fake.n" 2>/dev/null || echo 0); echo \$((n + 1)) >"$W/fake.n"
if [ "\$n" -eq 1 ]; then cp "$W/red.png" "\$out"; sleep 2; else cp "$W/black.png" "\$out"; fi
EOF
chmod +x fakeshux
red_seconds() { # MP4: how long the red frame is on screen, sampled at 10 fps
  ffmpeg -v error -i "$1" -vf fps=10,scale=1:1 -f rawvideo -pix_fmt rgb24 - |
    od -An -v -tu1 | tr -s ' ' '\n' | grep . |
    awk 'NR%3==1{r=$1} NR%3==2{if (r>128 && $1<64) n++} END{printf "%.1f", n/10}'
}
expect "record.sh encodes a stalled snapshot at its real duration" 0 '^check_video: PASS' -- \
  env SHUX_BIN="$W/fakeshux" bash "$S/scripts/record.sh" -s fake -o stall.mp4 -t 4 -f 4 -x 1
red=$(red_seconds stall.mp4)
check "the stalled frame stays on screen for the stall ($red s, want >= 1.8)" awk -v r="${red:-0}" 'BEGIN{exit !(r>=1.8)}'
( sleep 3; touch "$W/slow.stop" ) &
t0=$SECONDS
bash "$S/scripts/observe.sh" -u "$W/slow.stop" -i 0.2 -T 1 -- 'slow::sleep 8; echo late' >obs.out 2>&1
took=$((SECONDS - t0)); wait
check "observe.sh cuts off a slow probe and names it" grep -q 'timed out after 1s' obs.out
check "observe.sh runs to its stop file past a slow probe (stopped in ${took}s, want 3-6)" \
  test "$took" -ge 3 -a "$took" -le 6

section "record.sh + observe.sh over shux"
if command -v shux >/dev/null; then
  unset SHUX_SOCKET  # it outranks XDG_RUNTIME_DIR: never touch the caller's daemon
  export XDG_RUNTIME_DIR="$W/rt"
  trap 'shux daemon stop >/dev/null 2>&1; rm -r -f "$W"' EXIT
  stop="$W/obs.stop"
  shux session create ev -d --cwd "$W" -- bash "$S/scripts/observe.sh" -u "$stop" -i 0.3 -- 'needle::echo observing' >/dev/null
  shux pane wait-for -s ev --text observing --timeout-ms 10000 >/dev/null
  ( sleep 3; touch "$stop" ) &
  expect "records a window to a phone-safe mp4 (SHUX=1 in env)" 0 '^check_video: PASS' -- \
    env SHUX=1 bash "$S/scripts/record.sh" -s ev -o rec.mp4 -u "$stop" -t 20 -f 4 -x 1
  wait
  shux session kill ev >/dev/null 2>&1; shux daemon stop >/dev/null 2>&1
elif [ -n "${REQUIRE_SHUX:-}" ]; then
  ko "shux not installed (REQUIRE_SHUX is set)"
else
  sk "shux not installed"
fi

printf '\n%s%d passed%s, %s%d failed%s, %d skipped\n' "$G" "$pass" "$X" "$R" "$fail" "$X" "$skip"
[ "$fail" -eq 0 ]
