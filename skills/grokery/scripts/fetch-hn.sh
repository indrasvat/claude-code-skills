#!/usr/bin/env bash
#
# Fetching top Hacker News stories for a topic via the public Algolia API.
# Keyless. Filters by points + recency client-side (robust against the API's
# fragile numericFilters parsing). Emits a markdown section on stdout and always
# exits 0 so an orchestrator is never blocked by a single dead source.
#
# Usage: fetch-hn.sh <topic> [--days N] [--max N] [--min-points N]
set -euo pipefail

usage() { echo "usage: fetch-hn.sh <topic> [--days N] [--max N] [--min-points N]" >&2; exit 2; }

topic=""; days=30; max=5; min_points=20
while [ $# -gt 0 ]; do
  case "$1" in
    --days)       days="${2:?"$1 needs a value"}"; shift 2 ;;
    --max)        max="${2:?"$1 needs a value"}"; shift 2 ;;
    --min-points) min_points="${2:?"$1 needs a value"}"; shift 2 ;;
    -h|--help)    usage ;;
    --*)          echo "fetch-hn: unknown flag: $1" >&2; usage ;;
    *)            if [ -z "$topic" ]; then topic="$1"; shift; else echo "fetch-hn: unexpected arg: $1" >&2; usage; fi ;;
  esac
done
[ -n "$topic" ] || usage
for v in "$days:--days" "$max:--max" "$min_points:--min-points"; do
  case "${v%%:*}" in ''|*[!0-9]*) echo "fetch-hn: ${v#*:} must be an integer" >&2; exit 2 ;; esac
done

enc=$(jq -rn --arg q "$topic" '$q|@uri')
if date -v-1d >/dev/null 2>&1; then
  cutoff=$(date -v-"${days}"d +%s)          # BSD/macOS
else
  cutoff=$(date -d "-${days} days" +%s)     # GNU/Linux
fi

echo "## Hacker News"
resp=$(curl -fsS --max-time 20 \
  "https://hn.algolia.com/api/v1/search_by_date?query=${enc}&tags=story&numericFilters=points%3E${min_points}" \
  2>/dev/null || true)
if [ -z "$resp" ]; then
  echo "_unavailable (network or API error)_"
  exit 0
fi

out=$(printf '%s' "$resp" | jq -r --argjson cut "$cutoff" --argjson max "$max" '
  [.hits[]? | select(.created_at_i > $cut)]
  | sort_by(-.points) | .[:$max][]
  | "- **\(.points)** pts · \(.num_comments) comments — \(.title)\n  <https://news.ycombinator.com/item?id=\(.objectID)>"
' 2>/dev/null || true)

if [ -z "$out" ]; then
  echo "_no stories above ${min_points} pts in the last ${days}d_"
else
  printf '%s\n' "$out"
fi
