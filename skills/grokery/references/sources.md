# grokery sources

How each last30days source maps onto grokery, and what each script emits.

## Core — zero setup

| Source | grokery path | Signal | Script |
|---|---|---|---|
| **X / Twitter** | `grok` first-party search | Real-time expert threads, breaking reactions, engagement | `fetch-social.sh` |
| **Reddit** | `grok` (web/Reddit tools) | Unfiltered community takes + upvotes (avoids the keyless `.json` 403) | `fetch-social.sh` |
| **Web** | `grok` grounded search | Editorial coverage, blogs — replaces last30days' Brave **and** Perplexity Sonar | `fetch-social.sh` |
| **Hacker News** | Algolia public API | Developer consensus (high points / high comments) | `fetch-hn.sh` |
| **GitHub** | REST search + events | Repos by stars; person mode = recent PRs/pushes + top repos | `fetch-github.sh` |
| **Polymarket** | Gamma `public-search` | Market question + real-money $ volume (the honest sentiment gauge); per-outcome odds live on the linked event page | `fetch-polymarket.sh` |

Why this is the whole point: last30days needs a vendored Bird client + browser
session for X, a Brave key for web, and an OpenRouter key for Perplexity. grokery
folds **all three** into the one `grok` call you already pay for.

## Optional — free, if the tool is present
- **YouTube** (`fetch-youtube.sh`) — needs `yt-dlp`. Lists top videos by views; `--transcripts` pulls the top video's auto-captions for quote distillation. Skips with a notice if `yt-dlp` is absent.
- **GitHub auth** — export `GITHUB_TOKEN` to lift the 10 req/min unauthenticated ceiling.

## Source control
- `EXCLUDE_SOURCES=youtube,polymarket` — suppress sources (comma-separated), honored by `grokery.sh`.
- Individual fetchers can also be run alone for debugging, e.g. `bash scripts/fetch-hn.sh "topic" --days 7`.

## Out of scope (paid-only in last30days)
TikTok, Instagram Reels, Pinterest, Threads **native** engagement, and Digg's
~1000-account AI leaderboard all require the paid **ScrapeCreators** API. grokery
deliberately omits them to stay keyless — grok's web/X pass will still surface
*mentions* and cross-posts, just not first-party metrics. Bluesky (AT Protocol,
free app password) is a candidate for a future `fetch-bluesky.sh`.

## Reliability notes
- Every fetcher **self-degrades and exits 0** — one dead source never blocks a run.
- The `grok` pass is the slow one (~2–3 min for live X). `fetch-social.sh --timeout` bounds it; default 300s.
