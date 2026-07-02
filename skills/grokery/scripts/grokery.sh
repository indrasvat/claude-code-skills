#!/usr/bin/env bash
#
# Orchestrating one grokery run: fan out every enabled source in parallel,
# assemble a combined raw-signal markdown doc, save a snapshot, and optionally
# render an HTML brief. The calling agent then dedupes, ranks, and synthesizes
# per the references/.
#
# This script only GATHERS. Synthesis, wit-scoring, comparison, and the *rich*
# HTML are the agent's job (see SKILL.md). `--html` here renders the raw doc as a
# deterministic fallback brief.
#
# Usage:
#   grokery.sh <topic> [--days N] [--max N] [--mode research|hiring|competitors]
#              [--timeout SECONDS_PER_CHANNEL] [--github-user <handle>]
#              [--save-dir <path>] [--save-suffix <s>] [--store] [--no-save]
#              [--html] [--model <name>]
#
# Env: EXCLUDE_SOURCES=youtube,polymarket   GROKERY_MEMORY_DIR=~/Documents/Grokery
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

usage() { echo "usage: grokery.sh <topic> [--days N] [--max N] [--mode M] [--timeout S] [--github-user H] [--save-dir P] [--save-suffix S] [--store] [--no-save] [--html] [--model NAME]" >&2; exit 2; }

topic=""; days=30; max=5; mode="research"; ghuser=""; suffix=""; social_timeout=420
save_dir="${GROKERY_MEMORY_DIR:-$HOME/Documents/Grokery}"; do_save=1; do_store=0; do_html=0; model=""
while [ $# -gt 0 ]; do
  case "$1" in
    --days)        days="${2:?"$1 needs a value"}"; shift 2 ;;
    --max)         max="${2:?"$1 needs a value"}"; shift 2 ;;
    --mode)        mode="${2:?"$1 needs a value"}"; shift 2 ;;
    --timeout)     social_timeout="${2:?"$1 needs a value"}"; shift 2 ;;
    --github-user) ghuser="${2:?"$1 needs a value"}"; shift 2 ;;
    --save-dir)    save_dir="${2:?"$1 needs a value"}"; shift 2 ;;
    --save-suffix) suffix="${2:?"$1 needs a value"}"; shift 2 ;;
    --store)       do_store=1; shift ;;
    --no-save)     do_save=0; shift ;;
    --html)        do_html=1; shift ;;
    --model)       model="${2:?"$1 needs a value"}"; shift 2 ;;
    -h|--help)     usage ;;
    --*)           echo "grokery: unknown flag: $1" >&2; usage ;;
    *)             if [ -z "$topic" ]; then topic="$1"; shift; else topic="$topic $1"; shift; fi ;;
  esac
done
[ -n "$topic" ] || usage

# --- validate inputs (fail loud, not silently mislabelled) ------------------
is_uint() { case "${1:-x}" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac; }
is_uint "$days"           || { echo "grokery: --days must be a non-negative integer (got '$days')" >&2; exit 2; }
is_uint "$max"            || { echo "grokery: --max must be a non-negative integer (got '$max')" >&2; exit 2; }
is_uint "$social_timeout" || { echo "grokery: --timeout must be a non-negative integer (got '$social_timeout')" >&2; exit 2; }
case "$mode" in research|hiring|competitors) ;; *) echo "grokery: --mode must be research|hiring|competitors (got '$mode')" >&2; exit 2 ;; esac

# Is a source enabled? (suppressed via EXCLUDE_SOURCES=a,b,c)
enabled() {
  case ",${EXCLUDE_SOURCES:-}," in
    *",$1,"*) return 1 ;;
    *) return 0 ;;
  esac
}

soc=$(mktemp -t grokery-soc); hn=$(mktemp -t grokery-hn)
gh=$(mktemp -t grokery-gh); pm=$(mktemp -t grokery-pm); yt=$(mktemp -t grokery-yt)
cleanup() { rm -f "$soc" "$hn" "$gh" "$pm" "$yt"; }
trap cleanup EXIT

# Fan out. Each fetcher self-degrades and exits 0, printing its section header
# first, so a crash still leaves a marker. stderr is NOT suppressed here — a real
# fetcher-level failure should be visible, not masked.
if enabled social; then
  if [ -n "$model" ]; then
    bash "$here/fetch-social.sh" "$topic" --days "$days" --mode "$mode" --timeout "$social_timeout" --model "$model" >"$soc" &
  else
    bash "$here/fetch-social.sh" "$topic" --days "$days" --mode "$mode" --timeout "$social_timeout" >"$soc" &
  fi
fi
enabled hackernews && bash "$here/fetch-hn.sh" "$topic" --days "$days" --max "$max" >"$hn" &
if enabled github; then
  if [ -n "$ghuser" ]; then bash "$here/fetch-github.sh" --user "$ghuser" --max "$max" >"$gh" &
  else bash "$here/fetch-github.sh" "$topic" --max "$max" --pushed-days "$days" >"$gh" & fi
fi
enabled polymarket && bash "$here/fetch-polymarket.sh" "$topic" --max "$max" >"$pm" &
enabled youtube    && bash "$here/fetch-youtube.sh"    "$topic" --max "$max" >"$yt" &
wait

stamp=$(date -u +%Y-%m-%dT%H:%MZ)
doc=$(
  printf '# grokery — "%s"\n' "$topic"
  printf '_generated %s · mode: %s · window: X/Reddit/Web/HN/GitHub ≤ %sd; Polymarket & YouTube show current top results_\n\n' "$stamp" "$mode" "$days"
  for f in "$soc" "$hn" "$gh" "$pm" "$yt"; do
    if [ -s "$f" ]; then cat "$f"; printf '\n\n'; fi
  done
)
printf '%s\n' "$doc"

# Persist a snapshot (markdown), mirroring last30days' per-run memory file.
if [ "$do_save" -eq 1 ]; then
  slug=$(printf '%s' "$topic" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')
  [ -n "$slug" ] || slug="topic"
  if [ -n "$suffix" ]; then
    cleansuffix=$(printf '%s' "$suffix" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')
    [ -n "$cleansuffix" ] && slug="${slug}-${cleansuffix}"
  fi
  mkdir -p "$save_dir"
  out="${save_dir}/${slug}-raw.md"
  printf '%s\n' "$doc" >"$out"
  echo "[grokery] snapshot saved: $out" >&2
  if [ "$do_store" -eq 1 ] && command -v python3 >/dev/null 2>&1; then
    if python3 "$here/store.py" --db "${save_dir}/grokery.sqlite3" --topic "$topic" --slug "$slug" --file "$out"; then
      echo "[grokery] stored run in ${save_dir}/grokery.sqlite3" >&2
    else
      echo "[grokery] WARNING: --store failed to write SQLite" >&2
    fi
  fi
  if [ "$do_html" -eq 1 ]; then
    htmlout="${out%.md}.html"
    if bash "$here/render-html.sh" "$out" --title "grokery — ${topic}" --out "$htmlout" >/dev/null; then
      echo "[grokery] HTML brief: $htmlout" >&2
    else
      echo "[grokery] WARNING: --html render failed" >&2
    fi
  fi
elif [ "$do_html" -eq 1 ]; then
  # --html with --no-save: render from a throwaway markdown file into the cwd.
  tmpmd=$(mktemp -t grokery-md); printf '%s\n' "$doc" >"$tmpmd"
  bash "$here/render-html.sh" "$tmpmd" --title "grokery — ${topic}" --out "./grokery-brief.html" >/dev/null \
    && echo "[grokery] HTML brief: ./grokery-brief.html" >&2 || echo "[grokery] WARNING: --html render failed" >&2
  rm -f "$tmpmd"
fi
