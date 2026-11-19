#!/usr/bin/env bash
# Gate an evidence comment before it is posted: every artifact it references
# exists, plays on a phone, is not committed, and nothing in the text leaks a
# local path or this machine's name.
#
# Usage: check_evidence.sh COMMENT.md [TEXT ...]
#
#   COMMENT.md  the comment body; local references like ![x](./a.png) are
#               resolved against its directory (http(s) links are skipped)
#   TEXT        extra text to scan for leaks, e.g. `shux pane capture` output
#               of every captured frame (pixels cannot be grepped; their text can)
#
# Last line is the contract:
#   check_evidence: PASS|FAIL file=COMMENT.md artifacts=N
# Exit 0 on PASS, 1 on FAIL, 2 on bad usage.
set -uo pipefail

md=${1:?usage: check_evidence.sh COMMENT.md [TEXT ...]}
[ -f "$md" ] || { echo "check_evidence: no such file $md" >&2; exit 2; }
shift
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
dir=$(cd "$(dirname "$md")" && pwd)
fail=0 n=0
bad() { printf 'check_evidence: FAIL %s\n' "$*" >&2; fail=1; }

# Local targets of markdown links/images and of src="…" attributes.
refs=$( { grep -oE '\]\([^)[:space:]]+' "$md" | cut -c3-
          grep -oE 'src="[^"]+"' "$md" | cut -d'"' -f2; } | grep -vE '^(https?:|mailto:|#)' || true)
while IFS= read -r ref; do
  [ -n "$ref" ] || continue
  n=$((n + 1))
  case $ref in /*|~*|file:*) bad "$ref is an absolute local path; reviewers cannot open it"; continue ;; esac
  f="$dir/${ref#./}"
  if [ ! -s "$f" ]; then bad "$ref is missing or empty"; continue; fi
  if git -C "$(dirname "$f")" ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    bad "$ref is tracked by git; evidence is attached to the PR, never committed"
  fi
  bytes=$(wc -c <"$f" | tr -d ' ')
  [ "$bytes" -le 10485760 ] || echo "check_evidence: WARN $ref is $((bytes / 1048576)) MB; GitHub caps images at 10 MB and videos at 10 MB on free plans" >&2
  case $(printf '%s' "$ref" | tr '[:upper:]' '[:lower:]') in
    *.mp4|*.mov|*.m4v)
      bash "$here/check_video.sh" "$f" >/dev/null 2>&1 || bad "$ref fails the phone gate: run check_video.sh $ref" ;;
    *.png|*.jpg|*.jpeg|*.gif|*.webp)
      ffprobe -v error "$f" >/dev/null 2>&1 || bad "$ref is not a readable image" ;;
  esac
done <<<"$refs"

# Leaks: this machine's home, user dirs and host name, in the comment and any extra text.
host=$(hostname -s 2>/dev/null || hostname)
for t in "$md" "$@"; do
  [ -f "$t" ] || { bad "no such text file $t"; continue; }
  grep -nF -- "$HOME" "$t" | sed "s|^|  $t:|" >&2 && bad "$(basename "$t") shows the home path"
  grep -nE '(/Users|/home)/[A-Za-z0-9._-]+/' "$t" | sed "s|^|  $t:|" >&2 && bad "$(basename "$t") shows a home-directory path"
  if [ "${#host}" -ge 4 ] && [ "$host" != localhost ]; then
    grep -niwF -- "$host" "$t" | sed "s|^|  $t:|" >&2 && bad "$(basename "$t") shows this machine's host name"
  fi
done

verdict=PASS
[ "$fail" -eq 0 ] || verdict=FAIL
printf 'check_evidence: %s file=%s artifacts=%d\n' "$verdict" "$md" "$n"
exit "$fail"
