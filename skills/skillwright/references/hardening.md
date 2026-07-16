# Hardening: prose to machinery

Reached at workflow step 5, once per failing instruction. Match the symptom, not
the technique. Every technique has a cost (last column). Harness capabilities
drift; detect and degrade at runtime, never hardcode a capability table.

| Symptom in output | Technique | Mechanism (load-bearing detail) | Cost |
|---|---|---|---|
| Model grades its own work; anchors on its first guess | Blind reviewers | Two sub-agents that never see each other: A = judgment, B = deterministic evidence (lint/test). A finishes before B enters synthesis (cheap signals anchor). Synthesis weaves, never concatenates. | 2x agent cost; sub-agent support/permission varies by harness |
| "Give 3 options" returns one idea in three skins | Force divergence | Ban the model's own reflex picks by name (2nd-order: if the aesthetic is guessable from the category, rework); inject an unchosen entropy seed (random or hashed); squint test = each variant earns a distinct concrete-noun label | seeds wander off-brief without the squint gate |
| One rulebook fits no case; context bloat | Route (MoE) | SKILL.md is a thin router: pick a register (first-match-wins), load the one expert reference needed, nothing else | a routing error costs a turn |
| No handoff across commands or sessions | Memory | A context script reads persistent state each session; one command writes a snapshot, the next reads the latest as its backlog; key the store off the resolved path, not the user's phrasing | storage shape becomes a contract; stale snapshots mislead |
| Skill only works when explicitly invoked | Fight-back hook | PostToolUse runs after every edit and injects findings via `hookSpecificOutput.additionalContext`. PreToolUse gate blocks a bad write. Re-entrancy guard via a depth env var. | fires on unrelated edits if the pattern is loose |
| Static prose gets skimmed and ignored | Script talks back | The script's stdout *is* the instruction, computed fresh from env/git/state; body says "follow whatever it prints"; a runtime directive outranks static text | busts the prompt cache; output shape is a contract |
| Chat is a bad control surface for a live artifact | Live-wire | Long-poll (agent<->server, cap each request under the server request-timeout), SSE (server->browser, auto-reconnect), POST (browser->agent); expose coarse knobs as CSS vars, bake on accept, no regeneration | reconnect + timeout plumbing |
| Breaks moving across Claude / Codex / Cursor | Compile + degrade | Treat the skill as source: a build absorbs mechanical diffs (dirs, syntax, placeholders); detect-and-degrade the behavioral diffs at runtime (who may spawn a sub-agent; whether a background job auto-wakes the thread) | a build to maintain; capability facts rot, verify live and date them |
| Great on Opus, breaks on Haiku or Codex | Weakest-model gates | Non-compressible gates ("stop at every gate"); explicit step lists (weaker models skip anything implicit); test on the weakest target, not the strongest | verbosity cost on strong models |

## Hook exit codes (the footgun)

- Inject context, do not block: exit 0 with JSON `additionalContext`. Never exit
  1, it blocks nothing and fails silently.
- Block: PreToolUse exit 2 (stderr goes to the model) or JSON
  `permissionDecision: deny`. PostToolUse cannot undo a completed tool.
- Never let a hook break the turn on its own bug: guard, then exit 0 unless
  deliberately blocking.

## Script rules

- Solve, do not punt: handle the error in-script (create the missing file, fall
  back), do not return a stack trace for the model to untangle.
- No voodoo constants: justify every magic number in a comment, or the model
  cannot either.
- Prefer a bundled utility over generated code: more reliable, token-free,
  consistent across runs.
- Plan then validate then execute for batch/destructive ops: emit a plan file,
  validate it with a verbose script (name the bad field AND the valid options),
  then apply.
- List dependencies; do not assume installed. claude.ai installs from
  npm/PyPI/GitHub; the bare API has no network.
- MCP tools fully qualified: `Server:tool`.
