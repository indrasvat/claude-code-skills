# grokery ranking & dedup

The fetchers pre-sort within each source. Cross-source ranking and clustering is
the agent's job — engagement is the currency, not SEO.

## 1. Normalize engagement across platforms
Different platforms, different scales. Judge by **reach within a platform's norms**, not raw counts:

| Platform | Primary signal | "High signal" rule of thumb |
|---|---|---|
| X | likes + reposts + views | 4-figure+ likes, or high views relative to author size |
| Reddit | upvotes + comments | 3-figure+ upvotes, or top comment of a big thread |
| Hacker News | points + comments | 100+ pts; comment count ≈ controversy |
| YouTube | views + recency | high views for the topic's niche |
| GitHub | stars + push recency | stars signal adoption; recent pushes signal momentum |
| Polymarket | $ volume (odds on event page) | high volume = real conviction; open the event link for the crowd's number |

Weight by **independence**: 5 unrelated accounts > 1 account quoted 5 times.

## 2. Dedup / cluster
Merge the same story across sources into one cluster:
- Same URL, or same event/claim described by multiple platforms → one bullet, list the corroborating sources.
- Quote-reposts and reaction threads collapse into the original.
- A claim appearing on X **and** HN **and** Reddit is *stronger* — say so; don't list it three times.

## 3. Recency
Within the `--days` window, prefer fresher items on fast-moving topics; for
evergreen topics, let engagement dominate.

## 4. Confidence labels
- **Consensus** — corroborated across ≥3 independent sources/platforms.
- **Contested** — strong takes on both sides; present both.
- **Single loud voice** — one high-reach account; flag as not-yet-corroborated.

## 5. Final order
Lead with the highest-confidence, highest-engagement cluster. Bury low-signal
chatter or drop it. A short, sharp brief beats an exhaustive dump.
