#!/usr/bin/env bash
#
# Fetching prediction-market signal for a topic from Polymarket's public Gamma
# API (keyless). Real-money odds/volume are a uniquely honest sentiment gauge.
# Emits markdown; always exits 0.
#
# Usage: fetch-polymarket.sh <topic> [--max N]
set -euo pipefail

usage() { echo "usage: fetch-polymarket.sh <topic> [--max N]" >&2; exit 2; }

topic=""; max=5
while [ $# -gt 0 ]; do
  case "$1" in
    --max)     max="${2:?"$1 needs a value"}"; shift 2 ;;
    -h|--help) usage ;;
    --*)       echo "fetch-polymarket: unknown flag: $1" >&2; usage ;;
    *)         if [ -z "$topic" ]; then topic="$1"; shift; else echo "fetch-polymarket: unexpected arg: $1" >&2; usage; fi ;;
  esac
done
[ -n "$topic" ] || usage
case "${max}" in ''|*[!0-9]*) echo "fetch-polymarket: --max must be an integer (got '$max')" >&2; exit 2 ;; esac

enc=$(jq -rn --arg q "$topic" '$q|@uri')

echo "## Prediction markets (Polymarket)"
resp=$(curl -fsS --max-time 20 \
  "https://gamma-api.polymarket.com/public-search?q=${enc}&limit_per_type=${max}" \
  2>/dev/null || true)
if [ -z "$resp" ]; then
  echo "_unavailable (network or API error)_"
  exit 0
fi
out=$(printf '%s' "$resp" | jq -r --argjson max "$max" '
  def num: if type=="string" then (tonumber? // 0) elif type=="number" then . else 0 end;
  (.events // [])[:$max][]
  | "- **\(.title)** — $\(((.volume // .volume24hr) | num | floor)) volume — <https://polymarket.com/event/\(.slug)>"
' 2>/dev/null || true)
if [ -z "$out" ]; then
  echo "_no active markets for this topic_"
else
  printf '%s\n' "$out"
fi
