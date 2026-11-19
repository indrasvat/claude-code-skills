#!/usr/bin/env bash
# Gate an evidence comment before it is posted: every artifact it references
# exists, plays on a phone, is not committed, and nothing in the text leaks a
# local path, this machine's name or a token.
#
# Usage: check_evidence.sh COMMENT.md [TEXT ...]
#
#   COMMENT.md  the comment body. Local references are found in markdown links
#               and images (inline and reference-style), and in HTML src=
#               attributes; code blocks are skipped, ?query/#fragment dropped,
#               http(s) links ignored. Paths resolve against its directory.
#   TEXT        extra text to scan for leaks, e.g. `shux pane capture` output
#               of every captured frame (pixels cannot be grepped; their text can)
#
# Leaks are reported as file:line only, never the line itself.
# Last line is the contract:
#   check_evidence: PASS|FAIL file=COMMENT.md artifacts=N
# Exit 0 on PASS, 1 on FAIL, 2 on bad usage.
set -uo pipefail

if [ $# -lt 1 ] || [ ! -f "$1" ]; then
  echo "usage: check_evidence.sh COMMENT.md [TEXT ...]" >&2
  exit 2
fi
md=$1
shift
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
dir=$(cd "$(dirname "$md")" && pwd)
fail=0 n=0
bad() { printf 'check_evidence: FAIL %s\n' "$*" >&2; fail=1; }

refs=$(python3 -I - "$md" <<'EOF'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
# Fenced code: a closing fence is at least as long as the opening one.
text = re.sub(r"(?ms)^ {0,3}(`{3,}|~{3,}).*?(^ {0,3}\1[`~]*[ \t]*$|\Z)", "", text)
text = re.sub(r"(?m)^(?: {4}|\t).*$", "", text)                       # indented code
text = re.sub(r"`[^`\n]*`", "", text)                                  # inline code
dest = r"(<[^>\n]+>|[^\s)]+)"
found = re.findall(r"\]\(\s*" + dest, text)                            # [x](d) and ![x](d)
found += re.findall(r"(?m)^ {0,3}\[[^\]\n]+\]:\s*" + dest, text)       # [id]: d
found += ["".join(m) for m in re.findall(                                # src="d" / 'd' / d
    r"""(?i)(?<![\w-])src\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+))""", text)]
for d in found:
    d = d.strip("<>").split("#")[0].split("?")[0]
    if d.lower().startswith("file:") or (d and not re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", d)):
        print(d)
EOF
) || { echo "check_evidence: could not parse $md" >&2; exit 2; }

while IFS= read -r ref; do
  [ -n "$ref" ] || continue
  n=$((n + 1))
  case $ref in /*|~*|[Ff][Ii][Ll][Ee]:*) bad "$ref is an absolute local path; reviewers cannot open it"; continue ;; esac
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

# Leaks, in the comment and any extra text. Fail closed: no HOME, no scan.
home=${HOME:-}
[ -n "$home" ] || bad "HOME is unset, so the home-path scan cannot run"
host=$(hostname -s 2>/dev/null || hostname)
where() { grep -n "$@" | cut -d: -f1 | paste -sd, -; }
for t in "$md" "$@"; do
  [ -f "$t" ] || { bad "no such text file $t"; continue; }
  name=$(basename "$t")
  if [ -n "$home" ]; then
    l=$(where -F -- "$home" "$t"); [ -z "$l" ] || bad "$name:$l shows the home path"
  fi
  l=$(where -E '(/Users|/home)/[A-Za-z0-9._-]+' "$t"); [ -z "$l" ] || bad "$name:$l shows a home-directory path"
  l=$(where -E '(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY)' "$t")
  [ -z "$l" ] || bad "$name:$l holds a token or key"
  if [ "${#host}" -ge 4 ] && [ "$host" != localhost ]; then
    l=$(where -iwF -- "$host" "$t"); [ -z "$l" ] || bad "$name:$l shows this machine's host name"
  fi
done

verdict=PASS
[ "$fail" -eq 0 ] || verdict=FAIL
printf 'check_evidence: %s file=%s artifacts=%d\n' "$verdict" "$md" "$n"
exit "$fail"
