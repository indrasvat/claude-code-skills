#!/usr/bin/env bash
# Runs inside the eval container (see run.sh): install the skill with the
# skills CLI, build the sample PR, and let Codex follow the skill.
# Mounts: /repo (ro), /out (rw), /codex-home (CODEX_HOME holding auth.json).
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$(mktemp -d)"
npx -y skills add /repo --skill pr-evidence --global --agent codex --yes --copy
ls ~/.agents/skills/pr-evidence/
sample="$HOME/work/sample"
bash "$here/mksample.sh" "$sample"
export CODEX_HOME=/codex-home
prompt=$(sed "s|{SAMPLE}|$sample|g" "$here/prompt.txt")
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
  --color always -C "$sample" -o /out/last.md "$prompt" 2>&1 | tee /out/codex.log
