#!/usr/bin/env bash
# check-usage.sh
# Quick check of Cloudflare free tier usage status
# Run: ./check-usage.sh [database-name]

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         Cloudflare Free Tier Usage Check                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check wrangler auth
echo "Checking authentication..."
if ! wrangler whoami &> /dev/null; then
    echo -e "${RED}✗ Not authenticated. Run: wrangler login${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Authenticated${NC}"
echo ""

# Free tier limits
echo "═══════════════════════════════════════════════════════════"
echo "FREE TIER LIMITS (Daily reset at 00:00 UTC)"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Workers:         100,000 requests/day, 10ms CPU/request"
echo "Pages:           Unlimited bandwidth, 500 builds/month"
echo "D1:              5M reads/day, 100K writes/day, 5 GB storage"
echo "KV:              100K reads/day, 1K writes/day, 1 GB storage"
echo "R2:              10 GB storage, free egress"
echo "Durable Objects: 100K requests/day, 5 GB storage"
echo "Workers AI:      10,000 neurons/day"
echo ""

# List Workers
echo "═══════════════════════════════════════════════════════════"
echo "DEPLOYED WORKERS"
echo "═══════════════════════════════════════════════════════════"
wrangler deployments list 2>/dev/null || echo "No workers deployed or unable to list"
echo ""

# List D1 databases
echo "═══════════════════════════════════════════════════════════"
echo "D1 DATABASES"
echo "═══════════════════════════════════════════════════════════"
wrangler d1 list 2>/dev/null || echo "No databases or unable to list"
echo ""

# If database name provided, show info
if [ -n "$1" ]; then
    echo "═══════════════════════════════════════════════════════════"
    echo "D1 DATABASE: $1"
    echo "═══════════════════════════════════════════════════════════"
    wrangler d1 info "$1" 2>/dev/null || echo "Unable to get database info"
    echo ""
fi

# List KV namespaces
echo "═══════════════════════════════════════════════════════════"
echo "KV NAMESPACES"
echo "═══════════════════════════════════════════════════════════"
wrangler kv:namespace list 2>/dev/null || echo "No KV namespaces or unable to list"
echo ""

# List R2 buckets
echo "═══════════════════════════════════════════════════════════"
echo "R2 BUCKETS"
echo "═══════════════════════════════════════════════════════════"
wrangler r2 bucket list 2>/dev/null || echo "No R2 buckets or unable to list"
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "For detailed analytics, visit:"
echo "https://dash.cloudflare.com → Workers & Pages → Analytics"
echo "═══════════════════════════════════════════════════════════"
