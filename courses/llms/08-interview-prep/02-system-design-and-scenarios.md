# System Design and Interview Scenarios

Four complete system design walkthroughs plus the interview framework, scenario Q&A, and behavioral guidance.

---

## System Design Interview Framework

Use this structure for any LLM system design question. Interviewers are evaluating whether you think systematically about requirements, tradeoffs, and production concerns — not whether you memorize specific architectures.

```
STEP 1: CLARIFY REQUIREMENTS (2 min)
  Functional: Core task? Knowledge needs? Actions? Interface?
  Non-functional: Latency? Scale? Accuracy? Cost?
  Safety: What can go wrong? Who are the users? Compliance requirements?

STEP 2: HIGH-LEVEL ARCHITECTURE (3 min)
  Draw the data flow. Identify the pattern:
    - Simple Prompt (classification, extraction)
    - RAG (knowledge-grounded Q&A)
    - Agent (multi-step, tool use)
    - Pipeline (staged processing)
  Most real systems combine multiple patterns.

STEP 3: DEEP DIVE (5-10 min)
  Pick 2-3 most interesting/complex components.
  For each: what it does, why this approach, tradeoffs.
  Show concrete details: prompt snippets, schemas, data models.

STEP 4: PRODUCTION CONCERNS (2-3 min)
  Reliability: retries, fallbacks, circuit breakers
  Performance: streaming, caching, model routing
  Cost: tiering, token optimization, monitoring
  Observability: logging, tracing, alerting

STEP 5: EVALUATION (2 min)
  Offline: test set, automated scoring, regression checks
  Online: sampled quality monitoring, user feedback, A/B tests

STEP 6: COST ESTIMATION (1 min)
  Tokens × price × volume = $/day
  Is this financially viable?
```

---

## Design 1: RAG-Powered Customer Support System

### Requirements Gathering

Ask these questions before drawing anything.

**Functional:**
- What is the scope? Products, billing, technical troubleshooting, all of the above?
- What knowledge sources? Help center articles, product docs, internal runbooks?
- Can the system take actions? (Check order status, initiate refunds, update account settings?)
- Multi-turn conversations or single-shot Q&A?
- Does it need to hand off to human agents?

**Non-Functional:**
- Scale: How many conversations per day? (assume 10K for this exercise)
- Latency: User-facing chat, so sub-3-second responses expected
- Accuracy requirements: Customer-facing, so factual correctness is critical
- Compliance: PII handling, logging, data residency

**Assumptions for this design:**
- Full-scope customer support (product, billing, technical)
- Knowledge base of ~5,000 help articles, updated weekly
- Can check order status and initiate refunds via internal APIs
- Multi-turn conversations with escalation to human agents
- 10K conversations/day, average 6 turns each

---

### Architecture

```
                         ┌──────────────────────┐
                         │    User Interface     │
                         │  (Web Chat Widget)    │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │    API Gateway        │
                         │  (Auth, Rate Limit)   │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │  Conversation Service │
                         │  (Session Management) │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │      Intent Classifier        │
                    │   (Small/Fast Model: Haiku)    │
                    │                               │
                    │  → knowledge_question          │
                    │  → account_action              │
                    │  → escalate_to_human           │
                    │  → chitchat / off_topic        │
                    └─────┬─────────┬─────────┬─────┘
                          │         │         │
              ┌───────────▼──┐  ┌──▼────────────┐  ┌──▼──────────┐
              │  RAG Path    │  │  Agent Path    │  │  Escalation  │
              │              │  │                │  │  Path        │
              │ Embed query  │  │ Tool calls:    │  │              │
              │ Vector search│  │ - order_status │  │ Handoff to   │
              │ Rerank       │  │ - refund       │  │ human agent  │
              │ Generate     │  │ - update_acct  │  │ with context │
              └──────┬───────┘  └──────┬─────────┘  └──────┬──────┘
                     │                 │                    │
                     └─────────┬───────┘────────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Safety Filter      │
                    │  (PII, Content,      │
                    │   Injection Check)   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Response to User    │
                    │   (Streaming SSE)     │
                    └──────────────────────┘
```

---

### Deep Dive: Knowledge Path (RAG)

**Ingestion Pipeline:**

```
Help Center Articles (5K docs)
    │
    ▼
Parse (HTML → Markdown → Plain Text)
    │
    ▼
Chunk (Recursive splitting, ~500 tokens, 10% overlap)
    │    └── Prepend section title + article title to each chunk (contextual chunking)
    ▼
Embed (text-embedding-3-small, batch of 100)
    │
    ▼
Store in Vector DB (pgvector — team already uses Postgres)
    │    └── Metadata: article_id, section, category, last_updated
    ▼
~25K chunks indexed
```

**Retrieval Pipeline:**

```
User Query: "How do I return a damaged item?"
    │
    ▼
Query Rewriting (for multi-turn):
    Previous: "I ordered a laptop" → Current: "How do I return it?"
    Rewritten: "How do I return a damaged laptop?"
    │
    ▼
Hybrid Search:
    ├── Vector search (top 20)
    └── BM25 keyword search (top 20)
    │
    ▼
Reciprocal Rank Fusion → merged top 20
    │
    ▼
Cross-Encoder Reranker → top 3 chunks
    │
    ▼
Prompt Assembly:
    System: "You are a customer support agent for [Company]. Answer using
            ONLY the provided context. If unsure, say so and offer to
            connect the user with a human agent. Cite source articles."
    Context: [3 retrieved chunks with article titles]
    History: [last 5 turns]
    Query: [rewritten user query]
    │
    ▼
Generate (Claude Sonnet, streaming)
```

**Why pgvector over a dedicated vector DB:**
- Team already operates Postgres — no new infrastructure.
- Metadata filtering via standard SQL joins.
- ACID transactions for ingestion updates.
- At 25K chunks, pgvector performance is more than adequate.
- Scale inflection: consider migrating to Qdrant/Pinecone if chunks grow past 1M.

---

### Deep Dive: Agent Path (Account Actions)

```python
tools = [
    {
        "name": "lookup_order",
        "description": "Look up order details by order ID or customer email. "
                      "Returns order status, items, shipping, and dates.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "customer_email": {"type": "string"},
            },
        },
    },
    {
        "name": "initiate_refund",
        "description": "Initiate a refund for an order. Requires order_id and reason. "
                      "IMPORTANT: Always confirm with the customer before calling this.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "reason": {"type": "string"},
                "amount": {"type": "number", "description": "Refund amount in cents"},
            },
            "required": ["order_id", "reason"],
        },
    },
]
```

**Guardrails:**
- Read operations (lookup_order): execute automatically.
- Write operations (initiate_refund): require explicit user confirmation first.
- Agent loop capped at 5 iterations.
- Tool errors returned to the model with context for recovery.
- All tool calls logged with request ID for audit trail.

---

### Deep Dive: Conversation Management

**Session State:**
```python
{
    "session_id": "sess_abc123",
    "customer_id": "cust_456",
    "messages": [...],           # Full message history
    "summary": "...",            # Running summary of older turns
    "intent_history": [...],     # Track intent shifts
    "tools_used": [...],         # Audit trail of actions taken
    "escalation_score": 0.3,     # Rising frustration indicator
    "created_at": "...",
    "last_active": "...",
}
```

**Context Management:**
- Keep last 5 turns verbatim + running summary of older history.
- System prompt always included (~300 tokens).
- RAG context: 3 chunks (~1500 tokens).
- Total context budget: ~4000 tokens per turn.
- Summary updated every 5 turns by a cheap model.

**Escalation Logic:**
- Explicit request: "Let me talk to a human."
- Repeated failures: same question asked 3+ times.
- Negative sentiment detection over conversation.
- Tool failures the model cannot recover from.
- Topic outside the defined scope.

---

### Evaluation Strategy

**Offline (run before every deployment):**
- 200 curated test cases across all intent categories.
- Intent classification accuracy (target: > 95%).
- RAG answer correctness on knowledge questions (LLM-as-judge, target: > 85%).
- Tool call correctness: right tool, right parameters (target: > 90%).

**Online:**
- Customer satisfaction (post-conversation survey, target: > 4.0/5.0).
- Resolution rate without escalation (target: > 70%).
- Average conversation length (fewer turns = faster resolution).
- Escalation rate by category (identify weak areas).
- Cost per conversation (track and optimize).

**Monitoring:**
- Latency: TTFT < 500ms, total response < 3s at p95.
- Error rate: API failures, tool failures, malformed responses.
- Cost: per conversation and aggregate daily.
- Quality: LLM-as-judge on 5% sample of production conversations.

---

### Cost Estimation

```
10K conversations/day × 6 turns average = 60K LLM calls/day

Intent Classification (Haiku-class):
  60K calls × ~200 tokens each = 12M tokens/day
  At $0.25/1M input, $1.25/1M output: ~$5/day

RAG Generation (Sonnet-class, ~70% of calls):
  42K calls × ~3000 input + 500 output tokens
  Input: 126M × $3/1M = $378/day
  Output: 21M × $15/1M = $315/day
  Total: ~$693/day

Agent Path (Sonnet-class, ~20% of calls):
  12K calls × ~2000 input + 300 output tokens (avg across iterations)
  ~$100/day

Embeddings (query embedding):
  42K queries × ~20 tokens = 840K tokens/day
  At $0.02/1M: ~$0.02/day (negligible)

Reranking:
  42K queries × 20 passages: ~$10/day

TOTAL: ~$810/day ≈ $24K/month

Optimization opportunities:
- Prompt caching saves ~30% on RAG path (repeated system prompt + tool defs)
- Response caching for common questions saves ~10-15%
- Optimized to ~$17K/month after caching
```

---

## Design 2: AI Coding Assistant (like Copilot/Cursor)

### Requirements Gathering

**Functional:**
- What modes? Inline completion, chat sidebar, agent mode (multi-file edits)?
- What languages? All, or focus on top 5?
- Codebase awareness? Current file only, or full project context?
- Can it run code, execute terminal commands, or just suggest?

**Non-Functional:**
- Latency: Inline completion must feel instant (< 500ms to first token).
- Scale: Millions of developers, each making 50-200 completion requests/hour.
- Privacy: Code never leaves the enterprise for some customers (self-hosted option?).
- Cost: Must be viable at $20/month per user.

**Assumptions:**
- Three modes: inline completion, chat, and agent (autonomous multi-file edits).
- Full project awareness via smart context gathering.
- Support for all major languages.
- Cloud-hosted with enterprise self-hosted option.

---

### Architecture

```
┌──────────────────────────────────────────────────────┐
│                IDE Plugin (VS Code / JetBrains)       │
│                                                       │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────┐ │
│  │   Inline     │ │    Chat      │ │    Agent      │ │
│  │   Completion │ │    Sidebar   │ │    Mode       │ │
│  └──────┬──────┘ └──────┬───────┘ └──────┬────────┘ │
│         │               │                │           │
│  ┌──────▼───────────────▼────────────────▼────────┐ │
│  │            Context Gathering Engine             │ │
│  │  - Current file + cursor position               │ │
│  │  - Open tabs                                    │ │
│  │  - Recently edited files                        │ │
│  │  - Project structure / file tree                │ │
│  │  - Language server data (types, definitions)    │ │
│  │  - Terminal output                              │ │
│  └──────────────────────┬─────────────────────────┘ │
└─────────────────────────┼──────────────────────────┘
                          │
                ┌─────────▼─────────┐
                │   API Gateway     │
                │   (Auth, Routing, │
                │    Rate Limiting) │
                └─────────┬─────────┘
                          │
          ┌───────────────▼───────────────┐
          │        Model Router           │
          │                               │
          │  Inline → Fast model (Flash)  │
          │  Chat → Medium model (Sonnet) │
          │  Agent → Capable model (Opus) │
          └───────┬───────┬───────┬───────┘
                  │       │       │
           ┌──────▼┐  ┌──▼────┐ ┌▼───────┐
           │ Fast  │  │Medium │ │Capable │
           │ Model │  │ Model │ │ Model  │
           └───────┘  └───────┘ └────────┘
```

---

### Deep Dive: Context Gathering Engine

This is the most important component. The model is only as good as the context you give it.

**For Inline Completion:**
```
Context budget: ~4K tokens (must be fast)

1. Current file: lines before cursor (up to 2K tokens)
2. Current file: lines after cursor (up to 500 tokens, "suffix")
3. Imports/type definitions from current file (~500 tokens)
4. Most relevant open tab snippets (~1K tokens)
   - Ranked by: same directory > same language > recency

Assembled as FIM (Fill-in-the-Middle):
  <prefix>{code before cursor}</prefix>
  <suffix>{code after cursor}</suffix>
  <middle>  ← model completes here
```

**For Chat:**
```
Context budget: ~32K tokens (can afford more)

1. Current file: full content (~2-4K tokens)
2. Selected code (if any)
3. Open tabs: relevant snippets (~4K tokens)
4. Project-level context:
   - Package manifest (package.json, pyproject.toml)
   - Key config files
   - Directory structure (top 2 levels)
5. Recent terminal output (if relevant to the question)
6. Conversation history

Relevance ranking: embed the user's question, compare against
file/snippet embeddings to pick the most relevant context.
```

**For Agent Mode:**
```
Context budget: ~128K tokens (long context model)

Everything from Chat, plus:
1. Full content of files the agent is editing
2. Test files related to modified code
3. CI/CD output from recent runs
4. Git diff (what has changed so far in this session)
5. Error messages and stack traces

Agent has tools:
- read_file(path) → file contents
- write_file(path, content) → write/create file
- run_terminal(command) → execute and return output
- search_codebase(query) → semantic search across project
- list_directory(path) → directory listing
```

---

### Deep Dive: Inline Completion Latency

Inline completion is the most latency-sensitive feature. Target: < 500ms to first visible suggestion.

**Latency Budget:**
```
Context gathering:      50ms (local, cached file analysis)
Network round trip:     50-100ms (to nearest edge)
Model prefill:          100-200ms (process prompt tokens)
First decode token:     20-50ms
─────────────────────────────
Total TTFT:             220-400ms ✓
```

**Optimizations:**
- Speculative requests: start generating when the user pauses typing (300ms debounce), cancel if they keep typing.
- Client-side caching: if the user types the start of a previously suggested completion, serve from cache.
- Model selection: use the fastest available model (Gemini Flash, GPT-4o-mini) for inline. Accuracy matters less than speed.
- Request cancellation: aggressive cancellation of stale requests when user types more.
- Prefix caching: the system prompt and project context change infrequently; provider prompt caching reduces prefill time.
- Edge deployment: route to the nearest inference endpoint.

**Debounce / Cancellation Strategy:**
```
Keystroke → start 300ms timer
  If user types again → cancel timer, restart
  If timer fires → send completion request
  If completion arrives but user has moved cursor → discard
  If user types start of completion → accept and extend
```

---

### Deep Dive: Agent Mode

```
User Request: "Add input validation to the signup form and write tests"
    │
    ▼
Plan Phase:
    1. Read the signup form component
    2. Identify input fields and current validation
    3. Add validation logic (email format, password strength, etc.)
    4. Read existing test file
    5. Write new tests for validation
    6. Run tests to verify
    │
    ▼
Execute Phase (agent loop):
    Iteration 1: read_file("src/components/SignupForm.tsx")
    Iteration 2: read_file("src/components/SignupForm.test.tsx")
    Iteration 3: write_file("src/components/SignupForm.tsx", updated_code)
    Iteration 4: write_file("src/components/SignupForm.test.tsx", new_tests)
    Iteration 5: run_terminal("npm test -- --testPathPattern=SignupForm")
    Iteration 6: [if tests fail] read error, fix, and re-run
    │
    ▼
Present Changes:
    Diff view showing all modifications
    User can accept, reject, or edit each change
```

**Safety:**
- All file writes are staged (not applied until user confirms).
- Terminal commands are sandboxed (no sudo, no rm -rf, no network access beyond localhost).
- Agent has a max iteration limit of 25.
- Cost cap per request ($1 max, alert at $0.50).
- User can interrupt and undo at any point.

---

### Scaling and Cost

```
1M active developers, each making:
- 100 inline completions/hour × 8 hours = 800/day
- 20 chat messages/day
- 2 agent requests/day

Daily volume:
- 800M inline completions → fast model at ~$0.10/1M tokens
  Average 2K tokens in, 200 tokens out per request
  Input: 1.6T tokens × $0.10/1M = $160K/day
  Output: 160B tokens × $0.40/1M = $64K/day

- 20M chat messages → medium model at ~$3/1M tokens
  Average 8K tokens in, 1K tokens out per request
  ~$540K/day

- 2M agent requests → capable model at ~$15/1M tokens
  Average 50K tokens in, 5K tokens out per request (across all iterations)
  ~$1.65M/day

Total: ~$2.4M/day → ~$72M/month → ~$864M/year

At $20/user/month revenue: $20M/month → $240M/year

GAP: This does not work at these prices.

Optimization levers:
1. Prompt caching reduces inline costs by 50-80% (repeated prefix)
2. Client-side caching avoids 30-40% of inline requests
3. Self-hosted or fine-tuned small model for inline (10x cheaper)
4. Speculative decoding for inline completion
5. Aggressive request cancellation drops 20-30% of inline volume
6. Tiered pricing: free tier gets fewer features, enterprise pays more

After optimization: ~$15M/month, viable with tiered pricing
```

This is an important lesson: always do the cost math. The first-pass estimate may reveal that the architecture is not financially viable, which forces you to find the optimization path before you build.

---

## Design 3: Real-Time Content Moderation Pipeline

### Requirements Gathering

**Functional:**
- What content types? Text, images, video, or just text for now?
- What categories? Hate speech, violence, NSFW, spam, self-harm, illegal content?
- What actions? Remove, flag for review, reduce distribution, warn user?
- Appeals process?

**Non-Functional:**
- Scale: 50M messages/day (social platform).
- Latency: Content visible within 500ms of posting (cannot block on moderation).
- Accuracy: False positive rate < 1% (removing legitimate content is worse than missing some bad content at first pass).
- Coverage: False negative rate < 5% for severe categories (hate speech, CSAM, violence).
- Cost: Must be sustainable at scale.

---

### Architecture

```
User Posts Content
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│                   STAGE 1: Fast Filter                    │
│            (Regex + ML Classifier, <10ms)                 │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐    │
│  │ Keyword/     │  │ ML Text      │  │ Known-bad     │    │
│  │ Regex Filter │  │ Classifier   │  │ Hash Match    │    │
│  │ (blocklist)  │  │ (fine-tuned  │  │ (repeat       │    │
│  │              │  │  DistilBERT) │  │  offenders)   │    │
│  └──────┬──────┘  └──────┬───────┘  └──────┬────────┘    │
│         └──────────┬──────┘─────────────────┘             │
│                    │                                      │
│         Score: 0.0 ──────────────── 1.0                   │
│         PASS (<0.3)  REVIEW (0.3-0.8)  BLOCK (>0.8)       │
└──────────┬──────────────────┬──────────────────┬─────────┘
           │                  │                  │
     Content Live       ┌────▼─────┐     Content Hidden
     (no delay)         │ Queue    │     (immediate)
                        └────┬─────┘
                             │
┌────────────────────────────▼──────────────────────────────┐
│                 STAGE 2: LLM Review                       │
│          (Async, <5 min, for uncertain cases)             │
│                                                           │
│  Prompt: "Analyze this content for policy violations.     │
│   Consider context, intent, and severity.                 │
│   Categories: [hate_speech, violence, nsfw, spam, ...]    │
│   Output: {category, confidence, reasoning, action}"      │
│                                                           │
│  Model: GPT-4o-mini or Sonnet (balance speed/accuracy)    │
│  Structured output with confidence scores                 │
└──────────┬──────────────────────┬────────────────────────┘
           │                      │
     PASS: publish         UNCERTAIN or VIOLATION:
     content               push to Stage 3
                                  │
┌─────────────────────────────────▼────────────────────────┐
│              STAGE 3: Human Review                        │
│         (For high-stakes or uncertain cases)              │
│                                                           │
│  - Prioritized queue (severity-ranked)                    │
│  - Human moderator sees: content, LLM reasoning,         │
│    user history, similar past decisions                   │
│  - Decision: approve, remove, warn, escalate              │
│  - Decision feeds back into training data                 │
└──────────────────────────────────────────────────────────┘
```

---

### Deep Dive: Stage 1 — Fast Filter

This must be extremely fast and cheap because it runs on every single message.

**Components:**
- **Regex / keyword filter:** Known slurs and severe terms. Nearly zero latency. High precision (if matched, definitely bad) but low recall (easy to evade).
- **ML classifier:** Fine-tuned DistilBERT or similar small model. Runs on GPU with batch inference. < 10ms per message. Outputs a continuous score per violation category.
- **Hash matching:** Exact or fuzzy hash match against known-bad content database. Catches repeat offenders and known viral harmful content.

**Thresholds (tuned per category):**
```
Hate speech:   block > 0.85, review > 0.40
Violence:      block > 0.90, review > 0.45
NSFW:          block > 0.80, review > 0.35
Spam:          block > 0.75, review > 0.30
Self-harm:     block > 0.70, review > 0.25  (lower threshold = more caution)
```

**Volume flow:**
```
50M messages/day
  → 90% pass Stage 1 (45M → live immediately)
  → 8% to Stage 2 review queue (4M)
  → 2% blocked immediately (1M, obvious violations)
```

---

### Deep Dive: Stage 2 — LLM Review

**Why an LLM?** The ML classifier catches obvious cases but struggles with sarcasm, context-dependent content, coded language, and borderline content. LLMs understand nuance, context, and intent in ways that classifiers cannot.

**Prompt Design:**
```
System: You are a content moderation specialist. Analyze the following
user-generated content for policy violations.

Consider:
- Literal meaning AND implied meaning
- Whether the content targets a protected group
- Context and likely intent
- Severity level (mild, moderate, severe)

Categories: hate_speech, violence, sexual_content, spam,
self_harm, harassment, misinformation, illegal_activity

<content>
{user_message}
</content>

<user_context>
Account age: {account_age}
Previous violations: {violation_count}
Content type: {content_type}
</user_context>

Output JSON:
{
  "primary_category": "category or none",
  "confidence": 0.0-1.0,
  "severity": "none|mild|moderate|severe",
  "reasoning": "brief explanation",
  "action": "approve|flag_for_review|remove|warn_user"
}
```

**Batch Processing:**
- Process the 4M daily review queue in near-real-time.
- Batch requests for throughput (provider batch APIs).
- Prioritize by Stage 1 score (higher scores reviewed first).
- Target: all queued content reviewed within 5 minutes.

**Cost:**
```
4M LLM reviews/day
Average: ~800 input tokens, 200 output tokens
At $0.15/1M input, $0.60/1M output (GPT-4o-mini pricing):
  Input: 3.2B × $0.15/1M = $480/day
  Output: 800M × $0.60/1M = $480/day
Total: ~$960/day ≈ $29K/month
```

---

### Deep Dive: Feedback Loops

The system must improve continuously.

**Loop 1: Human decisions train Stage 1**
```
Human Review Decision
    → Labeled example (content, category, action)
    → Added to training dataset
    → Monthly retrain of ML classifier
    → A/B test new classifier vs current
    → Deploy if precision/recall improve
```

**Loop 2: LLM decisions calibrate thresholds**
```
LLM Review Results (4M/day with confidence scores)
    → Analyze: where does the classifier disagree with the LLM?
    → Adjust Stage 1 thresholds:
       If LLM frequently overturns blocks → lower block threshold
       If LLM frequently catches what classifier missed → lower review threshold
    → Weekly threshold recalibration
```

**Loop 3: User appeals improve all stages**
```
User Appeal
    → Human reviews the original decision
    → If overturned: negative example for both classifier and LLM
    → If upheld: positive example
    → Track appeal overturn rate per category as a health metric
```

---

### Tradeoffs

| Decision | Choice | Alternative | Why |
|---|---|---|---|
| Publish before moderation | Yes (Stage 1 only blocks) | Block until reviewed | UX: users expect instant publishing. Accept risk of brief exposure. |
| ML classifier vs LLM for Stage 1 | ML classifier | LLM | Cost: $960/day for 8% vs $6K+/day for 100% at LLM prices |
| Human review queue | Priority by severity | FIFO | Severe content should not wait behind spam |
| Single LLM vs ensemble | Single | Multiple models voting | Cost and latency; single model is good enough for triage |
| Threshold tuning | Per-category | Global | Different categories have different tolerance for false positives |

---

## Design 4: Multi-Agent Research Assistant

### Requirements Gathering

**Functional:**
- What kind of research? Market research, academic literature review, competitive analysis?
- What sources? Web, internal docs, databases, APIs?
- Output format? Report, summary, slides, structured data?
- How much autonomy? Fully autonomous or human-in-the-loop checkpoints?

**Non-Functional:**
- Latency: Research takes time; users expect minutes, not seconds.
- Quality: Outputs will be used for business decisions; accuracy is critical.
- Cost: Research tasks are high-value; willing to spend $1-10 per query.
- Depth: Should produce better output than a human spending 30 minutes.

**Assumptions:**
- Market and competitive research for a strategy team.
- Sources: web search, company documents, financial data APIs.
- Output: structured research reports with citations.
- Human-in-the-loop: approve plan before execution, review before delivery.

---

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    User Request                           │
│  "Analyze the competitive landscape for AI coding tools   │
│   in the enterprise market"                               │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│                   ORCHESTRATOR AGENT                      │
│              (Claude Opus / GPT-4o — capable model)       │
│                                                           │
│  Responsibilities:                                        │
│  - Decompose research request into sub-tasks              │
│  - Assign sub-tasks to specialist agents                  │
│  - Collect and synthesize results                         │
│  - Produce final report                                   │
└──────┬────────────┬────────────┬────────────┬────────────┘
       │            │            │            │
┌──────▼──────┐┌───▼──────┐┌───▼──────┐┌───▼──────────┐
│  Web Search ││ Document  ││  Data    ││  Synthesis   │
│  Agent      ││ Analysis  ││ Extract  ││  Agent       │
│             ││ Agent     ││ Agent    ││              │
│ Tools:      ││ Tools:    ││ Tools:   ││ Tools:       │
│ - web_search││ - read_doc││ - query  ││ - outline    │
│ - scrape    ││ - summarize│ - api_call│ - write_sect │
│ - extract   ││ - compare ││ - parse  ││ - format     │
│             ││           ││          ││              │
│ Model:      ││ Model:    ││ Model:   ││ Model:       │
│ Sonnet      ││ Sonnet    ││ Haiku    ││ Opus         │
└──────┬──────┘└───┬───────┘└───┬──────┘└───┬──────────┘
       │           │            │            │
       └───────────┴────────────┴────────────┘
                           │
                ┌──────────▼───────────┐
                │   Quality Assurance   │
                │                       │
                │ - Fact-check claims    │
                │ - Verify citations     │
                │ - Check for gaps       │
                │ - Score completeness   │
                └──────────┬───────────┘
                           │
                ┌──────────▼───────────┐
                │   Human Review       │
                │   (Final approval)   │
                └──────────────────────┘
```

---

### Deep Dive: Orchestrator Agent

**Plan Generation:**
```python
{
  "tasks": [
    {
      "id": "T1",
      "agent": "web_search",
      "description": "Identify top 10 AI coding tools targeting enterprise",
      "depends_on": []
    },
    {
      "id": "T2",
      "agent": "web_search",
      "description": "For each tool from T1: gather pricing, features, target customer",
      "depends_on": ["T1"]
    },
    {
      "id": "T3",
      "agent": "data_extract",
      "description": "Gather funding/revenue data for each company from T1",
      "depends_on": ["T1"]
    },
    {
      "id": "T4",
      "agent": "document_analysis",
      "description": "Analyze internal docs for our competitive positioning",
      "depends_on": []
    },
    {
      "id": "T5",
      "agent": "synthesis",
      "description": "Produce competitive landscape report from T1-T4",
      "depends_on": ["T2", "T3", "T4"]
    }
  ]
}
```

**Execution Strategy:**
- Tasks without dependencies run in parallel (T1 and T4 simultaneously).
- Dependent tasks wait for their prerequisites.
- Each task has a timeout (5 minutes per agent task).
- If a task fails, orchestrator can retry with modified instructions or skip and note the gap.

**Human Checkpoint:**
- After plan generation, present the plan to the user for approval.
- User can modify, add, or remove tasks.
- After execution, present draft report for review.
- User can request deeper investigation on specific topics.

---

### Deep Dive: Web Search Agent

```
Tools:
  web_search(query) → list of {title, url, snippet}
  scrape_page(url) → markdown content of page
  extract_structured(content, schema) → structured data

Agent Loop (for task "Identify top 10 AI coding tools"):

  Thought: I need to search for AI coding assistants targeting enterprise.
  Action: web_search("top AI coding assistants enterprise 2026")
  Observation: [results including Copilot, Cursor, Cody, Tabnine, ...]

  Thought: I have a good initial list. Let me verify with another search.
  Action: web_search("enterprise AI code completion tools comparison")
  Observation: [overlapping results, plus CodeWhisperer, Windsurf, ...]

  Thought: I should also check recent funding/launches.
  Action: web_search("AI coding startup funding 2025 2026")
  Observation: [news about recent raises and launches]

  Thought: I have a comprehensive list. Let me compile.
  Result: {
    "companies": [
      {"name": "GitHub Copilot", "company": "Microsoft/GitHub", ...},
      {"name": "Cursor", "company": "Anysphere", ...},
      ...
    ]
  }
```

**Quality Controls:**
- Cross-reference multiple sources (minimum 2 sources per claim).
- Track source URLs for citations.
- Flag low-confidence findings for human review.
- Rate limit web requests to avoid IP blocking.

---

### Deep Dive: Memory and Context Management

Each agent maintains its own working memory; the orchestrator maintains global state.

**Agent-Level Memory:**
```python
{
    "task_id": "T2",
    "agent": "web_search",
    "findings": [
        {
            "entity": "Cursor",
            "data": {"pricing": "$20/mo individual, custom enterprise", ...},
            "sources": ["https://cursor.com/pricing", ...],
            "confidence": "high",
        },
    ],
    "pages_visited": [...],
    "searches_performed": [...],
    "token_usage": {"input": 45000, "output": 8000},
}
```

**Orchestrator-Level Memory:**
```python
{
    "request": "Analyze competitive landscape...",
    "plan": {...},
    "task_results": {
        "T1": {"status": "complete", "data": {...}},
        "T2": {"status": "in_progress", "data": {...}},
    },
    "global_context": "...",  # Summary of all findings so far
    "cost_so_far": 2.45,
    "time_elapsed": "4m 30s",
}
```

**Context Passing:**
- Orchestrator summarizes upstream task results before passing to dependent tasks.
- Avoids passing raw data (too many tokens); passes structured summaries.
- Each agent gets: its task description, relevant upstream summaries, and its tools.
- Total context per agent call: 8-16K tokens.

---

### Quality Assurance Stage

Before delivering the final report, a QA pass checks for:

```
1. Citation verification:
   - Every factual claim has at least one source URL
   - Spot-check: scrape 3-5 cited URLs and verify the claim

2. Completeness check:
   - Does the report cover all companies identified in T1?
   - Are there obvious gaps? (missing pricing, missing a major player)

3. Consistency check:
   - Do numbers add up? (market size vs individual revenues)
   - Are comparative claims consistent? ("X is cheaper than Y" — verify)

4. Recency check:
   - Are sources from the last 6 months?
   - Flag any data older than 1 year

5. Scoring:
   {
     "completeness": 0.85,
     "citation_coverage": 0.92,
     "recency": 0.78,
     "overall_quality": 0.83,
     "gaps_identified": ["Missing Windsurf pricing details", ...]
   }
```

---

### Cost and Performance

```
Typical research request lifecycle:

Orchestrator (plan + synthesis): 3 calls × ~10K tokens = 30K tokens (Opus)
Web Search Agent: 15 tool iterations × ~3K tokens = 45K tokens (Sonnet)
Document Analysis Agent: 5 iterations × ~8K tokens = 40K tokens (Sonnet)
Data Extraction Agent: 8 iterations × ~2K tokens = 16K tokens (Haiku)
Synthesis Agent: 3 iterations × ~15K tokens = 45K tokens (Opus)
QA Agent: 2 iterations × ~10K tokens = 20K tokens (Sonnet)

Total: ~200K tokens across models
Estimated cost: $3-8 per research request
Time: 5-15 minutes end-to-end

At 100 research requests/day:
- Cost: $300-800/day ≈ $10-24K/month
- Value: replaces 2-4 hours of analyst time per request
```

---

## Scenario and Behavioral Questions

### Walk me through how you would build an LLM feature from scratch.

Define the task precisely first. Write 20-50 examples of what good input and output look like. These become your eval set. Then start simple: zero-shot prompt with a capable model. Run the eval. That is your baseline, and you should be surprised how often this is good enough.

If the baseline is not sufficient, iterate systematically. Add few-shot examples for ambiguous tasks, chain-of-thought for reasoning tasks, structured output for programmatic consumption. Each change gets an eval run. If the model needs knowledge it does not have, add RAG. If it needs to take actions, add tool use. Only fine-tune if you have proven that prompt engineering and RAG cannot reach your quality bar. Throughout, every decision is eval-driven: you know exactly what your current quality is and whether each change improves it.

Once the evals are green, add production concerns: streaming, caching, error handling, cost tracking, monitoring. Ship, then iterate based on production data.

Key points: define the task and build evals first, start simple (zero-shot) and establish baseline, iterate based on eval results not intuition, add complexity (RAG, tools, fine-tuning) only when justified, ship early and iterate based on real usage data.

---

### Tell me about a time an LLM system failed in production.

Structure your answer as: the system, what failed, how you detected it, what you did, and what you changed. The best answers show systematic debugging and process improvements, not hero-mode firefighting.

Good themes to hit:
- A model update silently degraded quality on an edge case category. Detected by automated evals catching a quality dip. Fixed by adding targeted test cases and model-specific prompt adjustments.
- An agent loop entered a retry spiral due to a tool returning ambiguous error messages. Detected by latency spike alerts. Fixed by improving error messages and adding iteration caps.
- RAG started returning stale information after a document ingestion pipeline silently failed. Detected by user reports. Fixed by adding ingestion monitoring and freshness checks.

The meta-message: you build systems that detect and recover from failures, not systems that never fail.

---

### How do you stay current with the LLM field?

The field moves fast, but the foundations are stable. Follow the major model releases and understand their capabilities — new context windows, new tool-use features, reasoning model improvements. Read Anthropic's and OpenAI's engineering blogs for production patterns and best practices. Follow a curated set of researchers and practitioners and read the papers that multiple trusted sources highlight.

Practically: maintain a few baseline evals that you re-run when major new models drop to understand if migration is worth it. Prototype with new features on side projects before bringing them to production. Do not chase every new framework or paper — the signal-to-noise ratio in this field is low. Focus on patterns that have proven durable: RAG, agent loops, eval-driven development, prompt engineering fundamentals. These have been stable for 2+ years even as the underlying models change rapidly.

Key points: follow major releases and capability deltas, engineering blogs from major providers for production patterns, curated sources (not everything), re-run baseline evals on new models, focus on durable patterns not hype cycles, prototype before bringing new capabilities to production.

---

### How do you handle model migrations and provider switches?

This is why evals and abstraction layers matter. If you have a comprehensive eval suite, migrating models is straightforward: run the new model against your test set, compare scores, and deploy if quality holds. Without evals, every migration is a scary manual process.

Architecturally, abstract the LLM provider behind an interface so your application code does not directly depend on OpenAI or Anthropic SDK specifics. Define a common interface (message format, tool call format, response parsing) and implement provider-specific adapters. This lets you swap providers, A/B test models, and implement fallback chains without touching application logic.

The practical reality: different models have different strengths, prompt sensitivities, and quirks. Prompts optimized for GPT-4 may need adjustment for Claude or Gemini. Budget time for prompt re-optimization during any migration and test thoroughly across your eval suite.

Key points: comprehensive evals make migration a measurable decision, abstract the LLM provider behind an interface, provider-specific adapters behind a common API, enables fallback chains and A/B testing, prompts may need re-optimization per model, budget time for prompt tuning during migrations.

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file. Each exercise references specific sections above and relevant patterns in `examples.py`.

- **Exercise 1: Build a Basic RAG Pipeline (15 min)** — Directly implements the RAG architecture described in "Design 1: RAG-Powered Customer Support System" (document ingestion, chunking, embedding, retrieval, context assembly). The design walkthrough's retrieval pipeline and chunk sizing discussion inform how to approach this exercise. Reference: `examples.py` Example 1 (`SimpleRAGPipeline`).

- **Exercise 2: Implement an Agent Loop (15 min)** — Practices the agent loop pattern described in "Design 4: Multi-Agent Research Assistant" (tool execution, error handling, iteration limits, message history). The design's orchestrator pattern and tool definitions inform the exercise structure. Reference: `examples.py` Example 2 (`AgentLoop`).

- **Exercise 3: Design an Eval Suite (20 min)** — Implements STEP 5 (EVALUATION) from the System Design Interview Framework. The eval approaches described in each design walkthrough (automated test cases, quality scoring, category-level analysis) directly inform the exercise requirements. Reference: `examples.py` Example 3 (`EvalPipeline`).

- **Exercise 5: Code Review (10 min)** — Applies STEP 4 (PRODUCTION CONCERNS) from the Framework. The production concerns discussed in every design walkthrough (reliability, observability, cost tracking, security) are exactly the categories of problems to identify. Reference: `examples.py` Example 5 (`ModelRouter` with cost tracking).

- **Exercise 6: Streaming Chat with Memory (20 min)** — Combines streaming (discussed in "Design 1" and "Design 2" as critical for user-facing chat) with conversation memory management (discussed in "Design 1" under context window management and summarization strategy). Reference: `examples.py` Examples 4 and 6 (`StreamingHandler`, `ConversationMemory`).

---

## Framework Recap: Use This in Any LLM System Design Interview

```
1. CLARIFY (2 min)
   - Functional: What does it do?
   - Non-functional: Scale, latency, accuracy, cost
   - Safety: What can go wrong?

2. ARCHITECTURE (3 min)
   - Draw the high-level data flow
   - Identify which pattern: Simple Prompt / RAG / Agent / Pipeline
   - Most systems are combinations

3. DEEP DIVE (5-10 min)
   - Pick 2-3 most interesting components
   - Discuss what, why, and tradeoffs for each
   - Show concrete details: prompt design, tool schemas, data models

4. PRODUCTION (2-3 min)
   - Reliability: retries, fallbacks, circuit breakers
   - Performance: streaming, caching, model routing
   - Cost: model tiering, token optimization, cost tracking
   - Observability: logging, tracing, alerting

5. EVALUATION (2 min)
   - Offline evals: test set, automated scoring
   - Online metrics: user satisfaction, task completion
   - Feedback loops: how the system improves over time

6. COST ESTIMATION (1 min)
   - Back-of-envelope: tokens × price × volume
   - Is this financially viable?
```
