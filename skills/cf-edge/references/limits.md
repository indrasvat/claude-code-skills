# Cloudflare Free Tier Limits Reference

Complete limits for all free tier services. All daily limits reset at 00:00 UTC.

## Workers (Serverless Compute)

| Metric | Free Limit |
|--------|------------|
| Requests | 100,000/day |
| CPU time | 10 ms/invocation |
| Memory | 128 MB |
| Worker size | 3 MB compressed |
| Workers per account | 100 |
| Environment variables | 64 |
| Subrequests per request | 50 |
| Startup time | 400 ms |

**CPU Time Clarification**: 10ms is *CPU* time, not wall-clock. A request waiting on fetch/DB doesn't count. Actual request can run much longer.

**Exceeding Limits**: Requests beyond 100K/day return errors. Configure fail-open (bypass worker) or fail-closed (show error) in dashboard.

## Pages (Static Hosting)

| Metric | Free Limit |
|--------|------------|
| Sites | Unlimited |
| Bandwidth | **Unlimited** |
| Requests | **Unlimited** |
| Builds | 500/month |
| Concurrent builds | 1 |
| Build timeout | 20 minutes |
| Files per deployment | 20,000 |
| Max file size | 25 MiB |
| Custom domains | 100 per project |

**Best For**: Static sites, SPAs, JAMstack. Always prefer Pages over Workers for static content.

## D1 (SQL Database)

| Metric | Free Limit |
|--------|------------|
| Storage | 5 GB total |
| Rows read | 5,000,000/day |
| Rows written | 100,000/day |
| Databases | 10 per account |
| Max DB size | 500 MB per database |
| Query timeout | 30 seconds |

**Row Counting**:
- `SELECT * FROM users` on 1000 rows = 1000 rows read
- Unindexed WHERE scans entire table
- Indexes reduce rows read significantly
- `INSERT` of 10 rows = 10 rows written

**Optimization Tips**:
```sql
-- Create indexes for filtered columns
CREATE INDEX idx_users_email ON users(email);

-- Use LIMIT to reduce reads
SELECT * FROM users WHERE active = 1 LIMIT 100;

-- Batch inserts when possible
INSERT INTO logs (msg) VALUES ('a'), ('b'), ('c');
```

## KV (Key-Value Store)

| Metric | Free Limit |
|--------|------------|
| Storage | 1 GB |
| Reads | 100,000/day |
| Writes | 1,000/day |
| Deletes | 1,000/day |
| Lists | 1,000/day |
| Max key size | 512 bytes |
| Max value size | 25 MB |
| Namespaces | Unlimited |

**Characteristics**:
- Eventually consistent (60s propagation)
- Optimized for read-heavy workloads (100:1 read:write ratio in free tier)
- Global replication automatic

**Best For**: Configuration, feature flags, caching, session data

## R2 (Object Storage)

| Metric | Free Limit |
|--------|------------|
| Storage | 10 GB |
| Class A ops (write) | 1,000,000/month |
| Class B ops (read) | 10,000,000/month |
| Egress | **$0 always** |

**Requires Credit Card**: Yes, but won't charge under limits. Set billing alerts.

**Class A Operations**: PUT, POST, COPY, LIST, CREATE multipart
**Class B Operations**: GET, HEAD

**Best For**: Images, files, media, backups, large assets (>25MB that Pages can't handle)

## Durable Objects (Stateful Compute)

| Metric | Free Limit |
|--------|------------|
| Requests | 100,000/day |
| Duration | 13,000 GB-s/day |
| Storage | 5 GB |
| Rows read | 5,000,000/day |
| Rows written | 100,000/day |

**Free Plan Restriction**: Only SQLite storage backend (not key-value)

**Best For**: WebSockets, real-time collaboration, rate limiting, game state

## Workers AI

| Metric | Free Limit |
|--------|------------|
| Neurons | 10,000/day |

**Neuron Costs (approximate)**:
| Model | Input | Output |
|-------|-------|--------|
| Llama 3.2 1B | ~2.5K neurons/M tokens | ~18K neurons/M tokens |
| Llama 3.2 3B | ~4.6K neurons/M tokens | ~30K neurons/M tokens |
| Llama 3.1 8B | ~4.1K neurons/M tokens | ~35K neurons/M tokens |

**Practical Capacity**: 10K neurons ≈ 500-1000 simple LLM queries/day

## Hyperdrive (Database Proxy)

| Metric | Free Limit |
|--------|------------|
| Queries | 100,000/day |

**Use Case**: Connection pooling for external PostgreSQL databases

## Email Routing

| Metric | Free Limit |
|--------|------------|
| Addresses | **Unlimited** |
| Forwarding rules | 200 |
| Message size | 25 MB |

**Note**: Forwarding only. Cannot send emails from Cloudflare.

## Tunnels

| Metric | Free Limit |
|--------|------------|
| Tunnels | **Unlimited** |
| Bandwidth | **Unlimited** |

**Quick Tunnel Limits**: 200 concurrent requests, no SSE support

## Zero Trust

| Metric | Free Limit |
|--------|------------|
| Users | 50 |
| DNS queries | 150K/user/month |

## Capacity Planning

### Small Blog/Portfolio
- Pages: More than enough
- No Workers/D1 needed for static content

### Personal API (< 1000 users)
- Workers: ~100 req/user/day = 1000 users max
- D1: 5M reads = 5000 reads/user/day
- KV: 100K reads for caching

### Side Project Web App
- Realistically serves 500-2000 DAU comfortably
- Add caching layer (KV) to stretch D1 limits
- Use Pages for all static assets

### High-Traffic Scenario
If approaching limits:
1. Add aggressive caching (KV, browser cache headers)
2. Move static assets to Pages
3. Consider upgrading to Workers Paid ($5/mo)

## Monitoring Commands

```bash
# Check D1 usage
wrangler d1 info <database-name>

# Live Worker logs
wrangler tail

# Dashboard for all metrics
# https://dash.cloudflare.com → Workers & Pages → Analytics
```
