# Cloudflare Services Configuration Reference

Detailed configurations, patterns, and examples for each service.

## Workers

### Full wrangler.toml Reference

```toml
name = "my-worker"
main = "src/index.ts"
compatibility_date = "2024-01-01"
compatibility_flags = ["nodejs_compat"]

# Account (optional, from wrangler whoami)
account_id = "your-account-id"

# Custom domain routing
routes = [
  { pattern = "api.example.com/*", zone_name = "example.com" }
]

# Or use workers.dev subdomain (default)
# workers_dev = true

# Build configuration (if using bundler)
[build]
command = "npm run build"
watch_dir = "src"

# Environment variables
[vars]
ENVIRONMENT = "production"
API_VERSION = "v1"

# Secrets (set via: wrangler secret put SECRET_NAME)
# Access in code: env.SECRET_NAME

# D1 Databases
[[d1_databases]]
binding = "DB"
database_name = "production-db"
database_id = "xxxxx-xxxx-xxxx"

# KV Namespaces
[[kv_namespaces]]
binding = "CACHE"
id = "xxxxx"

# R2 Buckets
[[r2_buckets]]
binding = "STORAGE"
bucket_name = "my-bucket"

# Durable Objects
[[durable_objects.bindings]]
name = "COUNTER"
class_name = "Counter"

[[migrations]]
tag = "v1"
new_classes = ["Counter"]

# Workers AI
[ai]
binding = "AI"

# Cron Triggers
[triggers]
crons = ["0 * * * *"]  # Every hour

# Tail Workers (logging)
[[tail_consumers]]
service = "log-worker"
```

### TypeScript Setup

```bash
wrangler init my-worker --type typescript
```

```typescript
// src/index.ts
export interface Env {
  DB: D1Database;
  KV: KVNamespace;
  BUCKET: R2Bucket;
  AI: Ai;
  ENVIRONMENT: string;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    // Handler code
  },
  
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    // Cron handler
  }
};
```

### Request/Response Patterns

```javascript
// JSON API response
return Response.json({ data }, { 
  headers: { 'Cache-Control': 'max-age=60' }
});

// Redirect
return Response.redirect('https://example.com', 301);

// HTML response
return new Response(html, {
  headers: { 'Content-Type': 'text/html' }
});

// Stream response
const { readable, writable } = new TransformStream();
return new Response(readable, {
  headers: { 'Content-Type': 'text/event-stream' }
});

// Error response
return new Response('Not Found', { status: 404 });
```

### Middleware Pattern

```javascript
// Compose handlers
const withAuth = (handler) => async (request, env) => {
  const token = request.headers.get('Authorization');
  if (!token) return new Response('Unauthorized', { status: 401 });
  return handler(request, env);
};

const withCors = (handler) => async (request, env) => {
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      }
    });
  }
  const response = await handler(request, env);
  response.headers.set('Access-Control-Allow-Origin', '*');
  return response;
};

export default {
  fetch: withCors(withAuth(mainHandler))
};
```

## D1 (SQL Database)

### Schema Migrations

```bash
# Create migrations folder
mkdir -p migrations

# Create migration file
cat << 'EOF' > migrations/0001_init.sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

CREATE TABLE posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  content TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_posts_user ON posts(user_id);
EOF

# Apply migration
wrangler d1 execute my-db --file ./migrations/0001_init.sql
```

### Query Patterns

```javascript
// Single row
const user = await env.DB.prepare('SELECT * FROM users WHERE id = ?')
  .bind(userId)
  .first();

// Multiple rows
const { results } = await env.DB.prepare('SELECT * FROM posts WHERE user_id = ?')
  .bind(userId)
  .all();

// Insert and get ID
const { meta } = await env.DB.prepare('INSERT INTO users (email, name) VALUES (?, ?)')
  .bind(email, name)
  .run();
const newId = meta.last_row_id;

// Batch operations (single round-trip)
const batch = await env.DB.batch([
  env.DB.prepare('INSERT INTO logs (msg) VALUES (?)').bind('action1'),
  env.DB.prepare('INSERT INTO logs (msg) VALUES (?)').bind('action2'),
  env.DB.prepare('UPDATE counters SET value = value + 1 WHERE name = ?').bind('actions'),
]);

// Transaction-like behavior with batch
const results = await env.DB.batch([
  env.DB.prepare('UPDATE accounts SET balance = balance - ? WHERE id = ?').bind(100, fromId),
  env.DB.prepare('UPDATE accounts SET balance = balance + ? WHERE id = ?').bind(100, toId),
]);
```

### Optimizing for Free Tier

```javascript
// BAD: Full table scan (reads ALL rows)
const users = await env.DB.prepare('SELECT * FROM users WHERE status = ?').bind('active').all();

// GOOD: Use index + limit
// First create index: CREATE INDEX idx_users_status ON users(status);
const users = await env.DB.prepare(
  'SELECT * FROM users WHERE status = ? LIMIT 100'
).bind('active').all();

// GOOD: Select only needed columns
const emails = await env.DB.prepare(
  'SELECT email FROM users WHERE status = ?'
).bind('active').all();

// GOOD: Use pagination
const page = await env.DB.prepare(
  'SELECT * FROM posts ORDER BY id DESC LIMIT ? OFFSET ?'
).bind(20, pageNum * 20).all();
```

## KV (Key-Value Store)

### Operations

```javascript
// Write with TTL (seconds)
await env.KV.put('session:123', JSON.stringify(data), { expirationTtl: 3600 });

// Write with expiration timestamp
await env.KV.put('key', 'value', { expiration: Math.floor(Date.now()/1000) + 86400 });

// Read
const value = await env.KV.get('key');              // string
const json = await env.KV.get('key', 'json');       // parsed JSON
const buffer = await env.KV.get('key', 'arrayBuffer');
const stream = await env.KV.get('key', 'stream');

// Read with metadata
const { value, metadata } = await env.KV.getWithMetadata('key', 'json');

// Write with metadata
await env.KV.put('key', 'value', { metadata: { version: 1 } });

// Delete
await env.KV.delete('key');

// List keys
const { keys, cursor, list_complete } = await env.KV.list({ prefix: 'user:' });
// Pagination: await env.KV.list({ prefix: 'user:', cursor: previousCursor });
```

### Caching Pattern

```javascript
async function getCachedData(env, key, fetchFn, ttl = 3600) {
  // Try cache first
  const cached = await env.KV.get(key, 'json');
  if (cached) return cached;
  
  // Fetch fresh data
  const data = await fetchFn();
  
  // Cache it (don't await, fire and forget)
  env.KV.put(key, JSON.stringify(data), { expirationTtl: ttl });
  
  return data;
}

// Usage
const user = await getCachedData(
  env, 
  `user:${id}`,
  () => env.DB.prepare('SELECT * FROM users WHERE id = ?').bind(id).first()
);
```

## R2 (Object Storage)

### Operations

```javascript
// Upload
await env.BUCKET.put('images/photo.jpg', imageData, {
  httpMetadata: { contentType: 'image/jpeg' },
  customMetadata: { uploadedBy: 'user123' }
});

// Upload from request body
await env.BUCKET.put('file.pdf', request.body, {
  httpMetadata: { contentType: request.headers.get('Content-Type') }
});

// Download
const object = await env.BUCKET.get('images/photo.jpg');
if (object === null) return new Response('Not Found', { status: 404 });

return new Response(object.body, {
  headers: {
    'Content-Type': object.httpMetadata.contentType,
    'ETag': object.etag
  }
});

// Head (metadata only)
const head = await env.BUCKET.head('file.pdf');

// Delete
await env.BUCKET.delete('file.pdf');

// List
const { objects, truncated, cursor } = await env.BUCKET.list({ prefix: 'images/' });
```

### Public Bucket Access

```bash
# Enable public access in dashboard or:
# Workers & Pages → R2 → Bucket → Settings → Public Access

# Access via: https://pub-<hash>.r2.dev/<key>
# Or connect custom domain in dashboard
```

## Durable Objects

### Definition

```javascript
// src/counter.js
export class Counter {
  constructor(state, env) {
    this.state = state;
  }
  
  async fetch(request) {
    const url = new URL(request.url);
    
    // SQLite storage (free tier)
    const sql = this.state.storage.sql;
    
    if (url.pathname === '/init') {
      sql.exec('CREATE TABLE IF NOT EXISTS counts (name TEXT PRIMARY KEY, value INTEGER)');
      return new Response('Initialized');
    }
    
    if (url.pathname === '/increment') {
      sql.exec('INSERT INTO counts (name, value) VALUES (?, 1) ON CONFLICT(name) DO UPDATE SET value = value + 1', 'hits');
      const row = sql.exec('SELECT value FROM counts WHERE name = ?', 'hits').one();
      return Response.json({ count: row.value });
    }
    
    return new Response('Not found', { status: 404 });
  }
}

// Main worker
export default {
  async fetch(request, env) {
    const id = env.COUNTER.idFromName('global');
    const stub = env.COUNTER.get(id);
    return stub.fetch(request);
  }
};
```

### wrangler.toml for Durable Objects

```toml
[[durable_objects.bindings]]
name = "COUNTER"
class_name = "Counter"

[[migrations]]
tag = "v1"
new_sqlite_classes = ["Counter"]  # SQLite backend (free tier)
```

## Workers AI

### Available Free Models

```javascript
// Text Generation
await env.AI.run('@cf/meta/llama-3.2-1b-instruct', { prompt: '...' });
await env.AI.run('@cf/meta/llama-3.2-3b-instruct', { prompt: '...' });
await env.AI.run('@cf/mistral/mistral-7b-instruct-v0.2', { prompt: '...' });

// Text Embeddings
await env.AI.run('@cf/baai/bge-base-en-v1.5', { text: '...' });

// Image Classification
await env.AI.run('@cf/microsoft/resnet-50', { image: [...] });

// Speech to Text
await env.AI.run('@cf/openai/whisper', { audio: [...] });

// Translation
await env.AI.run('@cf/meta/m2m100-1.2b', { text: '...', source_lang: 'en', target_lang: 'es' });
```

### Chat Pattern

```javascript
const messages = [
  { role: 'system', content: 'You are a helpful assistant.' },
  { role: 'user', content: userMessage }
];

const response = await env.AI.run('@cf/meta/llama-3.2-3b-instruct', { messages });
return Response.json({ reply: response.response });
```

## Tunnels

### Config File for Multiple Services

```yaml
# ~/.cloudflared/config.yml
tunnel: <tunnel-id>
credentials-file: /path/to/<tunnel-id>.json

ingress:
  - hostname: app.example.com
    service: http://localhost:3000
  - hostname: api.example.com
    service: http://localhost:8080
  - hostname: grafana.example.com
    service: http://localhost:3001
  - service: http_status:404  # Catch-all (required)
```

### Run as Service

```bash
# macOS
sudo cloudflared service install
sudo launchctl start com.cloudflare.cloudflared

# Linux (systemd)
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

## Pages Functions (Serverless on Pages)

For dynamic functionality in Pages projects:

```
my-site/
├── functions/
│   ├── api/
│   │   └── hello.js      # /api/hello
│   └── [[path]].js       # Catch-all
├── public/
│   └── index.html
└── wrangler.toml         # Optional config
```

```javascript
// functions/api/hello.js
export async function onRequest(context) {
  return Response.json({ message: 'Hello from Pages Functions!' });
}
```

## Email Workers

```javascript
// Triggered by email to your domain
export default {
  async email(message, env, ctx) {
    const { from, to } = message;
    const subject = message.headers.get('subject');
    
    // Read body
    const body = await new Response(message.raw).text();
    
    // Forward to another address
    await message.forward('[email protected]');
    
    // Or process with AI
    const summary = await env.AI.run('@cf/meta/llama-3.2-1b-instruct', {
      prompt: `Summarize this email: ${body}`
    });
    
    // Store in D1
    await env.DB.prepare('INSERT INTO emails (from_addr, subject, summary) VALUES (?, ?, ?)')
      .bind(from, subject, summary.response)
      .run();
  }
};
```
