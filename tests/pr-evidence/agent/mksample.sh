#!/usr/bin/env bash
# Build a tiny git repo whose branch fixes a lifecycle bug: `fanout` starts
# worker processes and, on its deadline, exits while the workers keep running.
set -euo pipefail
dir=${1:?usage: mksample.sh DIR}
mkdir -p "$dir"
cd "$dir"
git init -q -b main
git config user.email dev@example.invalid
git config user.name dev
cat >fanout <<'EOF'
#!/usr/bin/env bash
# fanout N DEADLINE: start N workers, give up after DEADLINE seconds.
set -euo pipefail
n=${1:-4} deadline=${2:-3}
for i in $(seq 1 "$n"); do
  bash -c "exec -a fanout-worker-$i sleep 600" &
  printf '\033[36mstarted\033[0m worker %s (pid %s)\n' "$i" "$!"
done
sleep "$deadline"
printf '\033[33mdeadline reached after %ss, exiting\033[0m\n' "$deadline"
EOF
chmod +x fanout
printf '# fanout\n\nStarts N workers and stops at a deadline.\n' >README.md
git add fanout README.md && git commit -qm "feat: fanout"
git checkout -qb fix/orphaned-workers
cat >fanout <<'EOF'
#!/usr/bin/env bash
# fanout N DEADLINE: start N workers, give up after DEADLINE seconds.
set -euo pipefail
n=${1:-4} deadline=${2:-3}
pids=()
stop() { kill "${pids[@]}" 2>/dev/null || true; wait 2>/dev/null || true; }
trap stop EXIT
for i in $(seq 1 "$n"); do
  bash -c "exec -a fanout-worker-$i sleep 600" &
  pids+=("$!")
  printf '\033[36mstarted\033[0m worker %s (pid %s)\n' "$i" "$!"
done
sleep "$deadline"
printf '\033[33mdeadline reached after %ss, stopping %s workers\033[0m\n' "$deadline" "$n"
EOF
git commit -qam "fix: stop workers when the deadline passes"
git log --oneline
