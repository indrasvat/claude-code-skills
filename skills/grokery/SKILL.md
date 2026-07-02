---
name: grokery
description: >
  Scanning the live internet for what people are actually saying about a topic,
  then synthesizing an engagement-ranked brief — grok-powered first-party X
  search plus Hacker News, GitHub, Reddit, Polymarket, YouTube and the open web,
  with no API keys or browser login. Use when the user says "grokery", "what's
  the buzz on", "what is X / the internet saying about", "scan the discourse",
  "vibe check", "trend check", "social signals on", "what are people saying
  about <topic>", "research the chatter on", or wants real-time cross-platform
  sentiment, a comparison ("A vs B"), or a shareable HTML signal brief on a
  tech / culture / product / person topic.
allowed-tools: Bash, Read, Write, WebFetch
argument-hint: <topic | A vs B> [--days N] [--mode hiring|competitors] [--github-user H] [--html]
---

# grokery 🛒

Grok-powered cross-platform signal scan. Like `last30days`, but the auth-walled,
key-hungry sources (X, Reddit, grounded web search) all run through the **`grok`
CLI on your X subscription** — so there is **no Bird client, no browser login,
no Brave/Perplexity keys**. _"Searches people, not editors. Ranked by upvotes,
likes, and real money."_

## Prerequisites
- **`grok`** CLI, logged in (`grok login`) — powers X + Reddit + web. Required for those sources; everything else still runs without it.
- **`curl`** + **`jq`** — for Hacker News, GitHub, Polymarket (keyless).
- Optional: **`yt-dlp`** (YouTube), **`GITHUB_TOKEN`** (higher GitHub limits), **`python3`** (`--store` trend DB + HTML render).

## Quickstart
Run the orchestrator — it fans out every source in parallel and prints combined
raw signal (also saved to `~/Documents/Grokery/<slug>-raw.md`):

```bash
bash skills/grokery/scripts/grokery.sh "grok cli" --days 30
```
> The grok pass is one combined session over X + Reddit + web and is the slow part — typically **3–7 min** (default `--timeout 420`s; after that it degrades gracefully and every other source still returns). The keyless sources (HN/GitHub/Polymarket) return in seconds. Run it and wait; do not abort.

Then **you synthesize** the raw output into the final brief (this is the agent's
job, mirroring last30days' "scripts gather, agent synthesizes" split):
read [`references/ranking.md`](references/ranking.md) and
[`references/modes.md`](references/modes.md), then produce the brief.

## Pipeline (what to do)
1. **Resolve** — grok identifies key handles / subreddits / repos / hashtags internally (entity resolution).
2. **Gather** — `grokery.sh` queries all enabled sources in parallel.
3. **Dedup** — merge the same story across platforms into one cluster ([ranking.md](references/ranking.md)).
4. **Rank** — order by real engagement (likes, upvotes, views, $ volume), not SEO.
5. **Synthesize** — write a tight narrative with citations; surface genuinely witty/viral one-liners verbatim ([modes.md](references/modes.md)).
6. **Emit** — markdown by default; `--html` → self-contained dark brief ([html-brief.md](references/html-brief.md)).

## Modes & options (detail → [references/modes.md](references/modes.md))
- **`A vs B vs C`** — run `grokery.sh` once per side, then compare side-by-side.
- **`--mode competitors`** — auto-discover top peers and run the comparison.
- **`--mode hiring`** / `--github-user <h>` — focus/career signals; person mode.
- **`--days N`**, **`--max N`**, **`--save-suffix`**, **`--store`** (SQLite trend log), **`--no-save`**.
- **`EXCLUDE_SOURCES=youtube,polymarket`** env to suppress sources.
- **`eli5`** — after a run, ask to rewrite the synthesis jargon-free.

## References (load on demand)
| File | When to read |
|---|---|
| [`references/sources.md`](references/sources.md) | Per-source detail, grok mapping, optional deps, honest gaps vs last30days |
| [`references/modes.md`](references/modes.md) | Comparison / competitors / hiring / person / eli5 recipes + synthesis & wit guidance |
| [`references/ranking.md`](references/ranking.md) | Cross-platform engagement normalization + dedup/clustering |
| [`references/html-brief.md`](references/html-brief.md) | HTML emit: `render-html.sh` or hand-craft from `brief-template.html` |

## Honest gaps vs last30days
- **Paid-only sources:** TikTok / Instagram / Pinterest / Threads **native** metrics and Digg's curated leaderboard need the paid ScrapeCreators API and are **out of scope** — grok's web/X pass surfaces mentions, not first-party engagement numbers.
- **Data fidelity trade-off:** last30days reads X/Reddit through deterministic API clients (exact counts). grokery reads them through the grok LLM, which is faster to set up but can **approximate or misreport** engagement numbers. Treat grok-sourced metrics as indicative, prefer the cited URL as ground truth, and spot-check any number you'll quote. The curl sources (HN / GitHub / Polymarket) are exact.

Everything else is at or near parity, with far less setup.
