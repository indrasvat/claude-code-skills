#!/usr/bin/env bash
# Cross-agent portability eval: a clean Linux container, pr-evidence installed
# the way a Codex user installs it (npx skills add), a sample PR with a
# lifecycle bug, and Codex asked to capture its evidence. Read OUT/evidence.md,
# its artifacts and OUT/last.md (Codex's own account of the skill) afterwards.
#
# Usage: tests/pr-evidence/agent/run.sh OUT_DIR
#   OUT_DIR must be a path your container runtime shares (colima: under $HOME).
# Codex logs in with a copy of $CODEX_HOME/auth.json (default ~/.codex) whose
# refresh token is blanked, so the container can never rotate your login.
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../../.." && pwd)
out=${1:?usage: run.sh OUT_DIR}
mkdir -p "$out"
out=$(cd "$out" && pwd)
auth="${CODEX_HOME:-$HOME/.codex}/auth.json"
[ -f "$auth" ] || { echo "run.sh: no Codex login at $auth (run codex login)" >&2; exit 2; }

# A fresh 0700 dir per run, gone on any exit: the copy never outlives the run.
codex_home=$(mktemp -d "$out/.codex-home.XXXXXX")
trap 'rm -rf "$codex_home"' EXIT
python3 -I - "$auth" "$codex_home/auth.json" <<'EOF'
import json, os, sys
a = json.load(open(sys.argv[1]))
if a.get("tokens"):
    a["tokens"]["refresh_token"] = ""
fd = os.open(sys.argv[2], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.write(fd, json.dumps(a).encode())
os.close(fd)
EOF

docker build -t pr-evidence-linux "$repo/tests/pr-evidence"
docker run --rm -v "$repo:/repo:ro" -v "$out:/out" -v "$codex_home:/codex-home" \
  pr-evidence-linux bash /repo/tests/pr-evidence/agent/in-container.sh
printf 'run.sh: done; read %s/evidence.md and %s/last.md\n' "$out" "$out"
