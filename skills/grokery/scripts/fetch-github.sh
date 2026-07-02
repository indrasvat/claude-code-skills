#!/usr/bin/env bash
#
# Fetching GitHub signal for a topic (repos by stars) or a person (--user:
# recent PRs/pushes + top repos). Keyless; honors GITHUB_TOKEN if exported
# (raises the 10 req/min unauthenticated limit). Emits markdown; always exits 0.
#
# Usage:
#   fetch-github.sh <topic> [--max N] [--pushed-days N]
#   fetch-github.sh --user <handle> [--max N]
set -euo pipefail

usage() { echo "usage: fetch-github.sh <topic> [--max N] [--pushed-days N] | --user <handle> [--max N]" >&2; exit 2; }

topic=""; user=""; max=5; pushed_days=180
while [ $# -gt 0 ]; do
  case "$1" in
    --user)        user="${2:?"$1 needs a value"}"; shift 2 ;;
    --max)         max="${2:?"$1 needs a value"}"; shift 2 ;;
    --pushed-days) pushed_days="${2:?"$1 needs a value"}"; shift 2 ;;
    -h|--help)     usage ;;
    --*)           echo "fetch-github: unknown flag: $1" >&2; usage ;;
    *)             if [ -z "$topic" ]; then topic="$1"; shift; else echo "fetch-github: unexpected arg: $1" >&2; usage; fi ;;
  esac
done
for v in "$max:--max" "$pushed_days:--pushed-days"; do
  case "${v%%:*}" in ''|*[!0-9]*) echo "fetch-github: ${v#*:} must be an integer" >&2; exit 2 ;; esac
done

# GET that appends the HTTP status as a trailing line, so callers can tell a
# rate-limit / error apart from a genuinely empty result. bash 3.2 + set -u safe
# (no empty-array expansion). On total network failure, status is 000.
gh_get() {
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    curl -sS --max-time 20 -w '\n%{http_code}' -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" "$1" 2>/dev/null || printf '\n000'
  else
    curl -sS --max-time 20 -w '\n%{http_code}' -H "Accept: application/vnd.github+json" "$1" 2>/dev/null || printf '\n000'
  fi
}

# Human message for a non-2xx status; empty string for 2xx (so callers proceed).
gh_msg() {
  case "$1" in
    2*)  echo "" ;;
    000) echo "_unavailable (network error / timeout)_" ;;
    403) echo "_GitHub rate-limited or forbidden — export GITHUB_TOKEN to raise limits_" ;;
    *)   echo "_GitHub API error (HTTP $1)_" ;;
  esac
}

if [ -n "$user" ]; then
  # Reject anything that isn't a valid GitHub handle — stops path traversal
  # like `--user ../orgs/google` from re-pointing the API URL.
  case "$user" in
    *[!A-Za-z0-9-]*|-*|*-) echo "## GitHub — @${user}"; echo "_invalid GitHub handle_"; exit 0 ;;
  esac
  echo "## GitHub — @${user}"
  raw=$(gh_get "https://api.github.com/users/${user}/repos?sort=pushed&per_page=${max}")
  code="${raw##*$'\n'}"; repos="${raw%$'\n'*}"
  msg=$(gh_msg "$code")
  if [ -n "$msg" ]; then echo "$msg"; exit 0; fi
  rout=$(printf '%s' "$repos" | jq -r --argjson max "$max" '
    if type=="array" then (.[:$max][] | "- **\(.stargazers_count)** ★ — [\(.full_name)](\(.html_url)) — \(.description // "no description") _(pushed \(.pushed_at[0:10]))_")
    else empty end' 2>/dev/null || true)
  [ -n "$rout" ] && { echo "**Recently pushed repos**"; printf '%s\n' "$rout"; } || echo "_no public repos found_"

  eraw=$(gh_get "https://api.github.com/users/${user}/events/public?per_page=30")
  events="${eraw%$'\n'*}"
  eout=$(printf '%s' "$events" | jq -r '
    if type=="array" then
      ([.[] | select(.type=="PullRequestEvent")] | .[:5][]
       | "- PR \(.payload.action) — [\(.repo.name)](https://github.com/\(.repo.name)): \(.payload.pull_request.title // "") _(\(.created_at[0:10]))_")
    else empty end' 2>/dev/null || true)
  [ -n "$eout" ] && { echo; echo "**Recent pull requests**"; printf '%s\n' "$eout"; }
  exit 0
fi

[ -n "$topic" ] || usage

enc=$(jq -rn --arg q "$topic" '$q|@uri')
if date -v-1d >/dev/null 2>&1; then
  since=$(date -v-"${pushed_days}"d +%Y-%m-%d)
else
  since=$(date -d "-${pushed_days} days" +%Y-%m-%d)
fi

echo "## GitHub"
raw=$(gh_get "https://api.github.com/search/repositories?q=${enc}+pushed:>=${since}&sort=stars&order=desc&per_page=${max}")
code="${raw##*$'\n'}"; resp="${raw%$'\n'*}"
msg=$(gh_msg "$code")
if [ -n "$msg" ]; then echo "$msg"; exit 0; fi
out=$(printf '%s' "$resp" | jq -r --argjson max "$max" '
  (.items // [])[:$max][]
  | "- **\(.stargazers_count)** ★ — [\(.full_name)](\(.html_url)) — \(.description // "no description")"
' 2>/dev/null || true)
if [ -z "$out" ]; then
  echo "_no active repos (pushed since ${since})_"
else
  printf '%s\n' "$out"
fi
