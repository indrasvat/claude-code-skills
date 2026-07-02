#!/usr/bin/env bash
#
# Fetching the auth-walled / messy half of the web through the `grok` CLI in ONE
# session: first-party X (no browser login), Reddit (no 403), and grounded web
# search (no Brave/Perplexity key). This is what makes grokery zero-setup — it
# replaces last30days' vendored Bird client + Brave + Perplexity with the grok
# subscription.
#
# Why one call, not parallel per-source calls: grok routes through a shared
# leader process (~/.grok/leader.sock), so concurrent `grok -p` invocations
# contend and serialize — slower, not faster. A single agent session searches
# all three sources in one loop, sharing context. It is the slow part of a run
# (typically 3-7 min); the keyless sources return in seconds regardless.
#
# Reports the ACTUAL failure cause (timeout / auth / empty) — never a blanket
# "timed out". Emits markdown; always exits 0.
#
# Usage: fetch-social.sh <topic> [--days N] [--mode research|hiring|competitors]
#                        [--timeout SECONDS] [--model NAME]
set -euo pipefail

usage() { echo "usage: fetch-social.sh <topic> [--days N] [--mode research|hiring|competitors] [--timeout S] [--model NAME]" >&2; exit 2; }

topic=""; days=30; mode="research"; timeout_s=420; model=""
while [ $# -gt 0 ]; do
  case "$1" in
    --days)    days="${2:?"$1 needs a value"}"; shift 2 ;;
    --mode)    mode="${2:?"$1 needs a value"}"; shift 2 ;;
    --timeout) timeout_s="${2:?"$1 needs a value"}"; shift 2 ;;
    --model)   model="${2:?"$1 needs a value"}"; shift 2 ;;
    -h|--help) usage ;;
    --*)       echo "fetch-social: unknown flag: $1" >&2; usage ;;
    *)         if [ -z "$topic" ]; then topic="$1"; shift; else echo "fetch-social: unexpected arg: $1" >&2; usage; fi ;;
  esac
done
[ -n "$topic" ] || usage
for v in "$days:--days" "$timeout_s:--timeout"; do
  case "${v%%:*}" in ''|*[!0-9]*) echo "fetch-social: ${v#*:} must be an integer" >&2; exit 2 ;; esac
done
case "$mode" in research|hiring|competitors) ;; *) echo "fetch-social: --mode must be research|hiring|competitors" >&2; exit 2 ;; esac

echo "## X · Reddit · Web (via grok)"
if ! command -v grok >/dev/null 2>&1; then
  echo "_grok CLI not found — install from https://x.ai/cli and run \`grok login\`_"
  exit 0
fi

prompt="You are a social-signal researcher. Topic: \"${topic}\". Window: the last ${days} days.
First, internally resolve the key entities (X handles, subreddits, hashtags, project names). Then, in ONE pass, use your X search, Reddit, and web tools to find the most SIGNIFICANT, high-engagement discussion.
Return ONLY markdown with these subsections in order, each with up to 4 bullets ranked by engagement (skip a subsection entirely if nothing notable):
### X (Twitter)
### Reddit
### Web
Each bullet: a one-line takeaway, the author/source, engagement metrics if available (likes/reposts/views, upvotes), and a cited URL. Prefer concrete numbers and quote genuinely witty or viral lines verbatim. Be concise. No preamble, no closing summary."
case "$mode" in
  hiring)      prompt="${prompt}
Also add '### Hiring signals': open roles / careers-page changes that reveal where this person/company is focusing." ;;
  competitors) prompt="${prompt}
Also add '### Competitors': the top 3 peers people compare this against, each with one line on how sentiment differs." ;;
  *) : ;;
esac

timeout_bin=""
if command -v timeout >/dev/null 2>&1; then timeout_bin="timeout"
elif command -v gtimeout >/dev/null 2>&1; then timeout_bin="gtimeout"; fi

run_grok() {
  if [ -n "$model" ]; then
    if [ -n "$timeout_bin" ]; then "$timeout_bin" "${timeout_s}s" grok -p "$prompt" --model "$model" --output-format json
    else grok -p "$prompt" --model "$model" --output-format json; fi
  else
    if [ -n "$timeout_bin" ]; then "$timeout_bin" "${timeout_s}s" grok -p "$prompt" --output-format json
    else grok -p "$prompt" --output-format json; fi
  fi
}

errlog=$(mktemp -t grokery-grokerr)
json=$(run_grok 2>"$errlog") && rc=0 || rc=$?

if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
  echo "_grok exceeded ${timeout_s}s — narrow the topic or raise --timeout; the keyless sources above/below still returned_"
elif [ "$rc" -ne 0 ]; then
  # Classify precisely. Note: "Transport channel closed ... Auth(AuthorizationRequired)"
  # is grok's transient worker-restart noise, NOT a real login failure — don't
  # mislabel it as one.
  if grep -iqE 'spending.?limit|out of credits|run out of credits|need a grok subscription|insufficient.*credit|quota' "$errlog" 2>/dev/null; then
    echo "_grok is out of credits / hit its usage limit — check https://grok.com/?_s=usage or wait for the quota window to reset; the keyless sources still returned_"
  elif grep -iqE 'not logged in|please log ?in|run .?grok login|sign in|no credentials|authentication required' "$errlog" 2>/dev/null; then
    # shellcheck disable=SC2016  # backticks are literal markdown, not a subshell
    echo "_grok is not authenticated — run \`grok login\`_"
  elif grep -iqE 'transport channel closed|connection refused|connectionrefused|worker quit|rate.?limit|429' "$errlog" 2>/dev/null; then
    echo "_grok hit a transient worker/connection error (often a flaky session or rate-limit) — retry; the keyless sources still returned_"
  else
    echo "_grok failed (exit ${rc}): $(grep -iE 'error|fatal' "$errlog" 2>/dev/null | tail -1 | cut -c1-160 || true)_"
  fi
else
  out=$(printf '%s' "$json" | jq -r '.text // empty' 2>/dev/null || true)
  [ -z "$out" ] && out=$(printf '%s' "$json")
  if [ -z "$out" ]; then echo "_grok returned no content_"; else printf '%s\n' "$out"; fi
fi
rm -f "$errlog"
