#!/usr/bin/env bash
#
# Fetching YouTube videos for a topic via yt-dlp (optional, keyless). Results are
# in YouTube's search-relevance order (flat-playlist mode does not return view
# counts to sort by); view counts are shown per item when available. With
# --transcripts, also pulls the top result's auto-captions (distillable into
# quotes by the calling agent). Degrades to a notice if yt-dlp is absent. Exits 0.
#
# Usage: fetch-youtube.sh <topic> [--max N] [--transcripts]
set -euo pipefail

usage() { echo "usage: fetch-youtube.sh <topic> [--max N] [--transcripts]" >&2; exit 2; }

topic=""; max=5; want_tx=0
while [ $# -gt 0 ]; do
  case "$1" in
    --max)         max="${2:?"$1 needs a value"}"; shift 2 ;;
    --transcripts) want_tx=1; shift ;;
    -h|--help)     usage ;;
    --*)           echo "fetch-youtube: unknown flag: $1" >&2; usage ;;
    *)             if [ -z "$topic" ]; then topic="$1"; shift; else echo "fetch-youtube: unexpected arg: $1" >&2; usage; fi ;;
  esac
done
[ -n "$topic" ] || usage
case "${max}" in ''|*[!0-9]*) echo "fetch-youtube: --max must be an integer (got '$max')" >&2; exit 2 ;; esac

echo "## YouTube"
if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "_skipped — yt-dlp not installed (\`brew install yt-dlp\` to enable)_"
  exit 0
fi

# One flat-playlist search call; tab-separated fields parsed line by line.
listing=$(yt-dlp "ytsearch${max}:${topic}" --flat-playlist --skip-download \
  --print "%(view_count)s\t%(title)s\t%(webpage_url)s" 2>/dev/null || true)
if [ -z "$listing" ]; then
  echo "_no results_"
  exit 0
fi
printf '%s\n' "$listing" | while IFS=$'\t' read -r views title url; do
  [ -n "$url" ] || continue
  printf -- "- **%s** views — %s\n  <%s>\n" "${views:-?}" "$title" "$url"
done

if [ "$want_tx" -eq 1 ]; then
  top_url=$(printf '%s\n' "$listing" | head -1 | cut -f3 || true)
  if [ -n "$top_url" ]; then
    tmpsub=$(mktemp -t grokery-ytsub)
    yt-dlp --skip-download --write-auto-subs --sub-format vtt --sub-langs en \
      -o "$tmpsub" "$top_url" >/dev/null 2>&1 || true
    sub=""
    for cand in "${tmpsub}"*.vtt; do [ -e "$cand" ] && { sub="$cand"; break; }; done
    if [ -n "$sub" ]; then
      echo
      echo "**Top-video transcript excerpt**"
      grep -vE '^(WEBVTT|[0-9]|$|.*-->)' "$sub" 2>/dev/null | awk '!seen[$0]++' | head -25 || true
      rm -f "${tmpsub}"*.vtt
    fi
    rm -f "$tmpsub"
  fi
fi
