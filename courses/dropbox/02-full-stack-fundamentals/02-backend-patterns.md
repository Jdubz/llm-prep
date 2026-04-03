# 02 – Backend Patterns

The backend stack powering Dropbox Dash: Python services (Metaserver/Atlas), Go for performance-critical paths, API design patterns, and data pipeline architecture.

---

## 1. Dropbox Backend Stack

| Technology | Role |
|-----------|------|
| **Python** | Core backend (Metaserver monolith + Atlas services), ML pipelines, agent execution |
| **Go** | Performance-critical services, networking |
| **Rust** | Storage (Magic Pocket), sync engine (Smart Sync) |
| **PostgreSQL** | Primary OLTP database |
| **MongoDB** | Document storage for certain services |
| **Kafka** | Event streaming |
| **Databricks** | Analytics and data processing |

---

## 2. Metaserver → Atlas Migration

This is the defining backend architectural story at Dropbox. Understanding it shows systems maturity.

### Metaserver (The Monolith)

- Python web application — the original Dropbox backend
- Handles file metadata, user accounts, sharing, collaboration
- ~50% of all commits historically touched Metaserver
- Deployed as a single unit
- Growing pain: slow deploys, blast radius of bugs, difficulty scaling individual features

### Atlas (The Managed Platform)

Atlas is Dropbox's internal platform for building and deploying services:

```
Developer writes service code
    → Atlas handles: packaging, deployment, scaling, monitoring, routing
    → Service runs independently with its own:
        - Database connections
        - Rate limits
        - Scaling policies
        - Health checks
        - Service mesh routing
```

**Key properties:**
- **Serverless-ish** — developers don't manage infrastructure
- **Independent deploys** — each service ships on its own cadence
- **Auto-scaling** — scales horizontally based on load
- **Standardized observability** — logging, metrics, tracing built in
- **Service mesh** — inter-service communication with load balancing and circuit breaking

### What This Means for Dash

Dash is almost certainly built on Atlas:
- Each Dash capability (search, AI answers, Stacks, connectors) is a separate service
- Independent scaling — search API scales differently than connector sync
- Fast iteration — Dash team deploys without coordinating with the monolith
- Clear API boundaries — well-defined contracts between services

---

## 3. API Design Patterns

### REST with Internal Conventions

Dropbox APIs follow REST conventions with some internal patterns:

```python
# Typical Dropbox API endpoint structure
@app.route('/2/dash/search', methods=['POST'])
def search():
    """
    POST /2/dash/search
    {
        "query": "Q3 revenue",
        "filters": {
            "sources": ["gdrive", "gmail"],
            "date_range": {"start": "2025-01-01", "end": "2025-12-31"}
        },
        "cursor": "eyJ...",  # pagination cursor
        "limit": 25
    }
    
    Response:
    {
        "results": [...],
        "ai_answer": {...},
        "cursor": "eyJ...",  # next page cursor
        "has_more": true
    }
    """
```

**Patterns to know:**
- **Cursor-based pagination** — offset-based doesn't work at scale (expensive for deep pages)
- **POST for search** — complex query objects don't fit in URL params
- **Versioned paths** (`/2/dash/...`) — API versioning via URL prefix
- **Consistent error format** — structured error responses with error codes

### Rate Limiting

At Dropbox's scale, rate limiting is critical:

```python
# Token bucket rate limiter (common interview question + real pattern)
class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # tokens per second
        self.capacity = capacity  # max burst
        self.tokens = capacity
        self.last_refill = time.monotonic()
    
    def consume(self, tokens: int = 1) -> bool:
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now
```

**Rate limiting tiers:**
- Per-user limits (protect against runaway clients)
- Per-service limits (protect downstream dependencies)
- Per-connector limits (respect third-party API rate limits)

### Webhook Processing

Connectors receive webhooks from third-party apps for real-time updates:

```python
# Webhook handler pattern
@app.route('/webhooks/slack', methods=['POST'])
def handle_slack_webhook(request):
    # 1. Verify signature (CRITICAL — prevents spoofing)
    if not verify_slack_signature(request):
        return Response(status=401)
    
    # 2. Return 200 immediately (don't process inline)
    event = request.json
    enqueue_webhook_processing(event)
    return Response(status=200)

# Async processor
def process_webhook(event):
    # 3. Idempotency check (webhooks can be delivered multiple times)
    if already_processed(event['event_id']):
        return
    
    # 4. Process the event
    match event['type']:
        case 'message':
            index_new_message(event)
        case 'file_shared':
            index_new_file(event)
        case 'channel_archive':
            remove_channel_from_index(event)
    
    # 5. Mark as processed
    mark_processed(event['event_id'])
```

---

## 4. Connector Backend Architecture

Each third-party integration (Slack, Gmail, Google Drive, etc.) requires a connector service.

### Connector Lifecycle

```
User connects app
    → OAuth2 flow → obtain access + refresh tokens
    → Initial sync: crawl all accessible content
    → Index: extract text, metadata, permissions
    → Ongoing sync: webhooks + periodic polling
    → Token refresh: handle token expiration
    → Disconnect: remove indexed content, revoke tokens
```

### Sync Engine

```python
# Connector sync pattern
class SlackConnector:
    def initial_sync(self, user_id: str):
        """Full crawl of user's accessible Slack data."""
        channels = self.client.list_channels(user_id)
        for channel in channels:
            messages = self.client.get_channel_history(channel.id)
            for msg in messages:
                self.index_message(user_id, channel, msg)
    
    def incremental_sync(self, event: WebhookEvent):
        """Process a single webhook event."""
        match event.type:
            case 'message':
                self.index_message(event.user_id, event.channel, event.message)
            case 'message_deleted':
                self.remove_from_index(event.message_id)
            case 'member_joined_channel':
                self.update_permissions(event.user_id, event.channel)
    
    def periodic_sync(self, user_id: str):
        """Catch anything missed by webhooks."""
        last_sync = self.get_last_sync_time(user_id)
        changes = self.client.get_changes_since(last_sync)
        for change in changes:
            self.process_change(user_id, change)
```

### Permission Mapping

Each source app has a different permission model. The connector must translate:

| Source App | Permission Model | Dash Mapping |
|-----------|-----------------|--------------|
| Google Drive | File-level ACLs, shared drives | Per-document permission check |
| Slack | Channel membership | User sees messages from channels they're in |
| Gmail | Account-level (your email is yours) | User sees only their own email |
| Jira | Project roles + issue security levels | Per-issue permission check |
| Notion | Page-level sharing + workspace | Per-page permission check |

**Critical rule:** When in doubt, don't show the result. False negatives (missing a result) are much better than false positives (showing unauthorized content).

---

## 5. Data Pipeline Patterns

### Event-Driven Architecture

```
Connector sync events
    → Kafka topic: connector.events
    → Consumers:
        → Index updater (update search index)
        → Embedding pipeline (compute embeddings for new content)
        → Feature pipeline (update engagement features)
        → Audit log (compliance tracking)
```

### Idempotent Processing

Every pipeline stage must be idempotent — processing the same event twice should produce the same result:

```python
# Idempotent index update
def index_document(doc_id: str, content: str, metadata: dict):
    """Upsert — same doc_id always produces same index state."""
    index.upsert(
        id=doc_id,
        content=content,
        metadata=metadata,
        embedding=compute_embedding(content),
    )
    # If called twice with same inputs, index state is identical
```

### Batch vs. Stream Processing

| Pattern | Use Case | Technology |
|---------|---------|------------|
| **Streaming** | New content indexing, real-time search freshness | Kafka consumers |
| **Batch** | Feature computation, model training data, analytics | Spark on Databricks |
| **Micro-batch** | Embedding computation (batch for GPU efficiency) | Custom: collect N events, batch embed |

---

## 6. Go Services at Dropbox

Go is used for performance-critical backend services. If the role involves Go:

### Common Patterns

```go
// HTTP service with graceful shutdown
func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/api/search", handleSearch)
    
    srv := &http.Server{
        Addr:         ":8080",
        Handler:      mux,
        ReadTimeout:  5 * time.Second,
        WriteTimeout: 10 * time.Second,
    }
    
    // Graceful shutdown
    go func() {
        sigCh := make(chan os.Signal, 1)
        signal.Notify(sigCh, syscall.SIGTERM)
        <-sigCh
        ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
        defer cancel()
        srv.Shutdown(ctx)
    }()
    
    srv.ListenAndServe()
}
```

### Concurrency for Fan-Out Search

```go
// Fan out search to multiple connectors concurrently
func search(ctx context.Context, query string, connectors []Connector) ([]Result, error) {
    g, ctx := errgroup.WithContext(ctx)
    resultsCh := make(chan []Result, len(connectors))
    
    for _, c := range connectors {
        c := c // capture
        g.Go(func() error {
            results, err := c.Search(ctx, query)
            if err != nil {
                return err
            }
            resultsCh <- results
            return nil
        })
    }
    
    if err := g.Wait(); err != nil {
        return nil, err
    }
    close(resultsCh)
    
    var all []Result
    for results := range resultsCh {
        all = append(all, results...)
    }
    return all, nil
}
```

---

## 7. Interview-Ready Talking Points

1. **"How would you design the connector architecture?"** — Each connector is a service with: OAuth2 auth, initial full sync, webhook-based incremental sync, periodic catch-up sync. Permission mapping per source. Idempotent processing throughout.

2. **"How do you handle third-party rate limits?"** — Per-connector token bucket rate limiter. Respect the source API's rate limit headers. Back off exponentially on 429s. Queue sync work and process at sustainable throughput.

3. **"Monolith vs. microservices — when do you split?"** — Split when services have different scaling needs, deployment cadences, or team ownership. Dropbox's Metaserver → Atlas is a case study: the monolith served them well initially but became a bottleneck for independent team velocity.

4. **"How do you ensure data freshness?"** — Webhooks for real-time (seconds), polling for near-real-time (minutes), full resync for catch-up (daily). Freshness SLA depends on the source app's capabilities.

5. **"How do you handle webhook reliability?"** — Return 200 immediately, process async. Idempotency by event ID. Reconciliation via periodic sync catches anything webhooks miss. Dead letter queue for failed processing.
