---
name: rollout-check
description: >
  Verify Kubernetes deployment health — pod status, rollout progress, events,
  readiness, HPA state, and recent errors. Use when the user says "check rollout",
  "is deploy healthy", "rollout status", "deployment health", "pod status",
  "check pods", "why is deploy failing", "k8s health", "verify deployment",
  "are pods ready", "check deployment", or wants to verify a Kubernetes
  deployment is healthy after a rollout.
allowed-tools: Bash, Read, Grep, Glob
argument-hint: <deployment-name> [-n namespace] [--context ctx]
---

# Rollout Health Check

Read-only deployment inspection. Lead with the health dashboard table.

## 1. Prerequisites

- `command -v kubectl` -- REQUIRED. Abort immediately if missing.
- Run `kubectl cluster-info --request-timeout=5s` to confirm cluster access. If unreachable, stop and report.
- Print the current context (`kubectl config current-context`).
- If `--context` is in `$ARGUMENTS`, pass `--context <value>` to every subsequent kubectl command.

## 2. Input

Parse `$ARGUMENTS` for:
- **Deployment name** -- first positional arg. REQUIRED. Abort if missing.
- `--namespace` / `-n` -- optional. Default: current context namespace.
- `--context` -- optional. Default: current context.

Store the namespace flag as `NS_FLAG` (e.g., `-n production`) and context flag as `CTX_FLAG` for reuse.

## 3. Checks

Run these in parallel where possible. Capture stdout/stderr and exit code for each.

**Rollout status**: `kubectl rollout status deployment/<name> --timeout=10s $NS_FLAG $CTX_FLAG`. Classify: complete, progressing, or failed.

**Pod status**: `kubectl get pods -l app=<name> -o wide $NS_FLAG $CTX_FLAG`. Count pods by state: Ready, NotReady, Pending, CrashLoopBackOff, Evicted. Flag any pod not fully ready.

**Recent events**: Collect events for the deployment AND its pods: `kubectl get events --sort-by=.lastTimestamp $NS_FLAG $CTX_FLAG` and filter for events where `involvedObject.name` matches the deployment, its ReplicaSets, or its pods (use label selector `app=<name>` to identify related objects). Flag Warning-type events, back-off messages, and errors.

**Resource usage**: `kubectl top pods -l app=<name> $NS_FLAG $CTX_FLAG`. If metrics-server is unavailable (non-zero exit), skip gracefully and note it. Flag pods using >80% of their CPU or memory limits.

**HPA status**: `kubectl get hpa $NS_FLAG $CTX_FLAG` and filter rows matching the deployment name. Report current vs desired replicas and any scaling events. If no HPA exists, report N/A.

**Container logs** (unhealthy pods ONLY): For each pod in CrashLoopBackOff, Error, or not-ready state, run `kubectl logs <pod> --tail=20 $NS_FLAG $CTX_FLAG`. If the pod is crashlooping, also run with `--previous` to capture the last crash output. Skip this entirely if all pods are healthy.

## 4. Secret Masking

Before displaying ANY kubectl output, filter every line for keys matching (case-insensitive): `password`, `secret`, `token`, `key`, `credential`. Replace their values with `[REDACTED]`. Use: `sed -E 's/(password|secret|token|key|credential)([=:][[:space:]]*)[^[:space:],"]*/\1\2[REDACTED]/gi'` on all captured output.

## 5. Output

Print the health dashboard table FIRST:

```
| Check           | Status | Detail                              |
|-----------------|--------|-------------------------------------|
| Rollout         | OK     | Successfully rolled out             |
| Pods (3/3)      | OK     | All pods ready                      |
| Events          | WARN   | 2 warning events in last 10m        |
| Resources       | OK     | All pods within limits              |
| HPA             | N/A    | No HPA configured                   |
```

Status values: OK, WARN, FAIL. For any non-OK row, print the relevant log/event excerpts below the table under a heading matching the check name. No preamble, no commentary outside the structured output.

## 6. Idempotency

Strictly read-only inspection. No resources are created, modified, or deleted. Safe to re-run at any time.

$ARGUMENTS
