#!/usr/bin/env bash
#
# Validate every skills/<name>/SKILL.md in two layers:
#   1. Parse each frontmatter with js-yaml (the engine skills.sh uses) and
#      enforce the Agent Skills spec — see scripts/validate-skills.mjs.
#   2. Cross-check with the real `skills` CLI over the working tree: it silently
#      drops skills whose frontmatter it can't parse, so a discovered count below
#      the number of SKILL.md files means one was dropped.
#
# Usage: make validate-skills   (or: bash scripts/validate-skills.sh)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node is required (it ships on GitHub runners; install Node 18+ locally)" >&2
  exit 1
fi

# --- Layer 1: parse + spec checks -------------------------------------------
if ! node -e 'require.resolve("js-yaml")' >/dev/null 2>&1; then
  echo "==> Installing js-yaml@4 (not found)"
  npm install --no-save --no-package-lock --silent js-yaml@4
fi

echo "==> Parsing SKILL.md frontmatter"
node scripts/validate-skills.mjs

# --- Layer 2: real-consumer cross-check -------------------------------------
echo
echo "==> Cross-checking discovery with the skills CLI"
dirs=$(find skills -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ')
# `|| true` guards every stage: pipefail + set -e would otherwise abort on a
# non-zero exit from npx, a no-match grep, or head closing the pipe early.
out=$(npx -y skills add . --list -y 2>&1 | sed 's/\x1b\[[0-9;]*m//g' || true)
found=$(printf '%s\n' "${out}" | grep -oE 'Found [0-9]+ skills' | grep -oE '[0-9]+' | head -1 || true)

echo "SKILL.md files: ${dirs} | skills CLI discovered: ${found:-<none>}"
if [ -z "${found}" ]; then
  echo "WARNING: skills CLI reported no count (network/version issue) — relying on the parser above"
elif [ "${found}" != "${dirs}" ]; then
  echo "ERROR: skills CLI discovered ${found} of ${dirs} skills — $((dirs - found)) silently dropped (unparseable frontmatter)" >&2
  exit 1
else
  echo "OK: all ${dirs} skills discovered by the skills CLI"
fi

echo
echo "All skill validation passed."
