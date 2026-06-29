# grokery modes & synthesis

## Synthesis (always)
After `grokery.sh` returns raw signal, write the brief:
- **Lead with the verdict** — 2–3 sentences: the dominant take + the strongest counter-take.
- **Group by theme**, not by platform. Each theme cites its strongest 1–2 sources with engagement numbers.
- **Quote wit verbatim.** Surface genuinely funny / viral one-liners — they carry signal and are why people read these. (last30days calls this "humor scoring".)
- **Numbers over adjectives** — "365K views · 117♥" beats "went viral".
- **Cite everything** — every claim links to a concrete URL.
- **Flag confidence** — call out when a take is one loud account vs broad consensus.

## Research (default)
Single topic. Run:
```bash
bash skills/grokery/scripts/grokery.sh "<topic>" --days 30
```

## Comparison — `A vs B [vs C]`
Detect `vs` in the request. Run the orchestrator **once per side**, then synthesize a side-by-side:
```bash
bash skills/grokery/scripts/grokery.sh "OpenClaw" --save-suffix cmp --days 30
bash skills/grokery/scripts/grokery.sh "Hermes"   --save-suffix cmp --days 30
```
Compare on the axes people actually argue about (architecture, reliability, price, momentum) and include live GitHub stars per side.

## `--mode competitors`
Pass `--mode competitors`; grok names the top ~3 peers in its `### Competitors`
subsection. Then run a comparison pass on those names.

## `--mode hiring` / `--github-user <handle>` (person mode)
- `--mode hiring` adds a `### Hiring signals` subsection (open roles, careers-page shifts) — reveals where a person/company is focusing.
- `--github-user steipete` switches GitHub to person mode: recent PRs/pushes + top repos. Combine with the topic for a full "what is this person up to" brief.

## `eli5` (post-run)
If the user says `eli5 on`, rewrite the existing synthesis in plain language —
short sentences, no jargon, concrete analogies — without re-running sources.
`eli5 off` restores the standard brief.

## Persistence
- Snapshots auto-save to `~/Documents/Grokery/<slug>-raw.md` (override `--save-dir`, disable `--no-save`).
- `--store` appends the run to `grokery.sqlite3` for trend monitoring; diff successive `<slug>-raw.md` snapshots to see what changed since last time.
