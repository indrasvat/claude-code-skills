#!/usr/bin/env bash
# Preflight for pr-evidence: which capture routes work on this machine, and the
# exact install command for each missing piece. Run it first, on any agent.
#
# Usage: doctor.sh
#
# Prints one line per check, then a last line that is the contract:
#   doctor: core=ok|missing terminal=ok|missing web=ok|missing publish=attach|manual skill=<dir>
# Exit 0 when core (stills + video encoding + gating) works, 1 when it does not.
# terminal = shux capture; web = agent-browser; publish=attach means
# `gh pr comment --attach` is available and gh is logged in.
set -uo pipefail

skill=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
os=$(uname -s)
if [ -t 1 ]; then G=$'\e[32m' R=$'\e[31m' Y=$'\e[33m' B=$'\e[1m' X=$'\e[0m'; else G='' R='' Y='' B='' X=''; fi

# The install command for a package on this OS.
pkg() {
  if [ "$os" = Darwin ]; then echo "brew install $1"
  elif command -v apt-get >/dev/null; then echo "sudo apt-get install -y $2"
  elif command -v dnf >/dev/null; then echo "sudo dnf install -y $2"
  else echo "install $2 with the system package manager"; fi
}

core=ok terminal=ok web=ok publish=attach
# Tests pipe into plain grep, never grep -q: -q exits at the first match, the
# writer dies of SIGPIPE, and pipefail reports a tool that is there as missing.
check() { # GROUP NAME TEST HINT
  if eval "$3" >/dev/null 2>&1; then printf '  %s✓%s %s\n' "$G" "$X" "$2"
  else
    case $1 in core) core=missing ;; terminal) terminal=missing ;; web) web=missing ;; publish) publish=manual ;; esac
    c=$R; [ "$1" = core ] || c=$Y
    printf '  %s✗%s %s  %s→ %s%s\n' "$c" "$X" "$2" "$B" "$4" "$X"
  fi
}

printf '%spr-evidence doctor%s  (%s %s)\n' "$B" "$X" "$os" "$(uname -m)"
echo "core: stills, video encoding, the phone-playback gate"
check core "ffmpeg with libx264" "ffmpeg -hide_banner -encoders | grep libx264" "$(pkg ffmpeg ffmpeg)"
check core "ffprobe" "command -v ffprobe" "$(pkg ffmpeg ffmpeg)"
check core "uv (runs evidence_img.py)" "command -v uv" "curl -LsSf https://astral.sh/uv/install.sh | sh"
if [ "$os" != Darwin ]; then
  check core "a monospace font (fontconfig)" "fc-match -f '%{file}' monospace | grep ." "$(pkg fontconfig 'fontconfig fonts-dejavu-core')"
fi
echo "terminal: CLIs and TUIs"
shux_bin=${SHUX_BIN:-shux}
# shellcheck disable=SC2016  # expanded by check's eval, never re-parsed as code
check terminal "shux ($shux_bin)" 'command -v "$shux_bin"' "curl -sSfL https://shux.pages.dev/install.sh | sh"
check terminal "perl with Time::HiRes (record.sh, observe.sh)" "perl -MTime::HiRes -e1" "$(pkg perl perl)"
check terminal "jq" "command -v jq" "$(pkg jq jq)"
echo "web: browser UIs"
check web "agent-browser" "command -v agent-browser" "npm install -g agent-browser && agent-browser install"
echo "publish: one PR comment with uploaded files"
check publish "gh with --attach" "gh pr comment --help | grep -- --attach" "upgrade gh (needs a release with --attach): $(pkg gh gh)"
check publish "gh logged in" "gh auth status" "gh auth login (or set GH_TOKEN)"

printf 'doctor: core=%s terminal=%s web=%s publish=%s skill=%s\n' "$core" "$terminal" "$web" "$publish" "$skill"
[ "$core" = ok ]
