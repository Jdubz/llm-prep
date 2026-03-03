# 03 — Advanced Agent Systems

## Multi-Agent Architectures

When a single agent cannot handle the full scope of a task — due to context window limits, the need for specialized expertise, or the complexity of parallel workstreams — multi-agent architectures distribute the work.

**Warning:** Multi-agent systems add significant complexity. Start with a single agent. Only split into multiple agents when you have proven that a single agent cannot handle the task. Every agent boundary is a new failure mode, a new logging challenge, and a new testing surface.

### Architecture 1: Supervisor / Orchestrator

A single orchestrator agent decomposes tasks and delegates to specialized sub-agents. The orchestrator collects results and synthesizes the final output.

```
User Request
     │
     ▼
┌───────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                   │
│                  (capable model: Opus)                 │
│                                                       │
│  - Understand the overall goal                        │
│  - Decompose into sub-tasks                           │
│  - Route to specialized agents                        │
│  - Collect and synthesize results                     │
└─────────┬─────────────────────────────┬───────────────┘
          │                             │
          ▼                             ▼
┌─────────────────┐           ┌──────────────────────┐
│  Research Agent │           │  Data Analysis Agent │
│  (Sonnet)       │           │  (Sonnet)            │
│                 │           │                      │
│  Tools:         │           │  Tools:              │
│  - web_search   │           │  - query_database    │
│  - scrape_page  │           │  - run_python        │
│  - extract_data │           │  - generate_chart    │
└─────────────────┘           └──────────────────────┘
```

**When to use:** Task cleanly decomposes into independent sub-problems with well-defined interfaces. One orchestrator decides; workers execute. Easy to reason about and debug.

### Architecture 2: Peer-to-Peer

Agents communicate as equals, passing messages to each other without a central coordinator.

```
Agent A ↔ Agent B ↔ Agent C
```

**When to use:** Collaborative tasks where agents need to negotiate, critique each other's work, or iteratively refine outputs. Less structured, harder to debug.

**Example use case:** A drafting agent writes, a critic agent identifies weaknesses, a revising agent improves — all without a central orchestrator.

### Architecture 3: Hierarchical

Multiple layers of orchestrators and workers. Used for complex enterprise tasks with many subtasks.

```
Orchestrator (Opus)
├── Sub-orchestrator A (Sonnet)
│   ├── Worker A1 (Haiku)
│   └── Worker A2 (Haiku)
└── Sub-orchestrator B (Sonnet)
    ├── Worker B1 (Haiku)
    └── Worker B2 (Haiku)
```

**When to use:** Enterprise-scale workflows where sub-tasks themselves are complex enough to need their own orchestration layer.

### Architecture Comparison

| Architecture | Complexity | Debuggability | Reliability | Best For |
|---|---|---|---|---|
| Single agent | Low | Excellent | High | Most tasks |
| Supervisor | Medium | Good | Good | Independent parallel sub-tasks |
| Peer-to-peer | High | Poor | Lower | Collaborative refinement |
| Hierarchical | Very high | Very poor | Complex | Enterprise-scale automation |

**Key insight:** Supervisor architectures are the most common and most practical. Peer-to-peer is powerful but difficult to make reliable. Always start with the simplest architecture that could work.

---

## Long-Running Agents

Agents that run for minutes to hours require persistence, checkpointing, and resumability that ephemeral agents don't need.

### State Persistence

```python
from dataclasses import dataclass, field
import json

@dataclass
class AgentCheckpoint:
    agent_id: str
    task: str
    status: str  # "running", "paused", "completed", "failed"
    messages: list[dict] = field(default_factory=list)
    tool_call_count: int = 0
    completed_subtasks: list[str] = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)  # Created files, results
    created_at: str = ""
    updated_at: str = ""
    error: str | None = None

    def save(self, storage):
        storage.set(f"agent:{self.agent_id}", json.dumps(asdict(self)))

    @classmethod
    def load(cls, agent_id: str, storage) -> "AgentCheckpoint":
        data = storage.get(f"agent:{agent_id}")
        return cls(**json.loads(data))
```

### Handling Context Window Limits in Long Tasks

For very long tasks, the accumulated conversation history may exceed the context window:

```python
def manage_long_task_context(
    messages: list[dict],
    max_context_tokens: int = 150_000
) -> list[dict]:
    """Manage context for long-running tasks."""

    # Always preserve: system prompt (messages[0]) + last 5 turns
    protected = messages[:1] + messages[-10:]
    compressible = messages[1:-10]

    total_tokens = count_tokens(messages)
    if total_tokens <= max_context_tokens:
        return messages  # No compression needed

    # Progressive compression
    # First pass: summarize compressible section
    summary = llm_call(
        f"Summarize the key decisions, discoveries, and state from this "
        f"conversation segment:\n\n{format_messages(compressible)}"
    )

    return protected[:1] + [
        {
            "role": "system",
            "content": f"[Task progress summary: {summary}]"
        }
    ] + protected[1:]
```

### Idempotent Tool Calls for Resumability

When a long-running agent is interrupted (process crash, network failure, budget exhaustion) and resumes, it should not re-execute operations that already completed:

```python
def idempotent_tool_call(
    tool_name: str,
    args: dict,
    checkpoint: AgentCheckpoint
) -> dict:
    """Execute a tool but skip if already completed."""

    # Create a deterministic key for this specific tool call + args
    call_key = f"{tool_name}:{json.dumps(args, sort_keys=True)}"

    # Check if we've already done this
    if call_key in checkpoint.artifacts:
        return {
            "result": checkpoint.artifacts[call_key],
            "cached": True,
            "message": "Retrieved from checkpoint (already executed)"
        }

    # Execute and persist the result
    result = execute_tool(tool_name, args)
    checkpoint.artifacts[call_key] = result
    checkpoint.save(storage)

    return result
```

---

## Human-in-the-Loop Patterns

Full automation is not always appropriate. Human oversight should be integrated into agent workflows for high-stakes decisions.

### Approval Workflow

```python
class HumanInTheLoop:
    def __init__(self, notification_service, approval_store):
        self.notification = notification_service
        self.approvals = approval_store

    def request_approval(
        self,
        agent_id: str,
        action_description: str,
        risk_level: str,
        context: dict,
        timeout_seconds: int = 3600
    ) -> dict:
        """Pause agent and request human approval."""

        approval_id = generate_id()

        # Notify the approver
        self.notification.send(
            f"Agent {agent_id} is requesting approval:\n"
            f"Action: {action_description}\n"
            f"Risk: {risk_level}\n"
            f"Context: {json.dumps(context, indent=2)}\n"
            f"Approve at: {approval_url(approval_id)}"
        )

        # Wait for approval (with timeout)
        result = self.approvals.wait_for_decision(
            approval_id,
            timeout=timeout_seconds
        )

        return {
            "approved": result.decision == "approved",
            "reason": result.reason,
            "approver": result.approver_id,
            "decision_at": result.timestamp
        }
```

### Confidence-Based Routing

```python
def confidence_router(
    action: dict,
    model_confidence: float,
    action_risk: str
) -> str:
    """Route actions to auto-execute or human review based on confidence."""

    thresholds = {
        "read": {"auto": 0.0, "review": 1.1},         # Always auto
        "write": {"auto": 0.90, "review": 0.70},      # Auto if high confidence
        "financial": {"auto": 0.95, "review": 0.80},  # High bar for auto
        "destructive": {"auto": 1.1, "review": 0.0},  # Never auto
    }

    threshold = thresholds.get(action_risk, thresholds["write"])

    if model_confidence >= threshold["auto"]:
        return "auto"
    elif model_confidence >= threshold["review"]:
        return "review"
    else:
        return "reject"
```

---

## Agent Evaluation

Evaluating agents is harder than evaluating single LLM calls because agent quality involves the entire trajectory, not just the final output.

### Evaluation Dimensions

| Metric | Measurement | Target |
|---|---|---|
| Task completion rate | % of tasks fully completed | > 80% |
| Step efficiency | Actual steps / minimal steps | < 1.5× optimal |
| Tool call accuracy | Correct tool + correct args | > 90% |
| Error recovery rate | % of errors the agent recovers from | > 70% |
| Cost per task | Average dollars per completed task | Task-dependent |
| Time to completion | Average seconds per task | Task-dependent |

### Trajectory Evaluation

```python
def evaluate_trajectory(trajectory: list[dict]) -> dict:
    """Evaluate the quality of an agent's execution path."""

    analysis_prompt = f"""Analyze this agent execution trajectory and evaluate:

1. Task completion: Did the agent fully complete the task?
2. Efficiency: Were there unnecessary steps or tool calls?
3. Error handling: How well did the agent handle errors?
4. Decision quality: Were tool choices appropriate?
5. Final quality: How good is the final output?

Trajectory:
{format_trajectory(trajectory)}

Output JSON with scores (0-10) and explanations for each dimension."""

    result = llm_call(analysis_prompt)
    return json.loads(result)
```

### Benchmark Evaluation

Standard benchmarks for agent evaluation:

| Benchmark | Task Type | What It Tests |
|---|---|---|
| SWE-Bench | Software engineering | Fix bugs in real GitHub issues |
| WebArena | Web browsing | Complete web-based tasks |
| HotpotQA | Multi-hop QA | Multi-step retrieval reasoning |
| GAIA | Real-world tasks | Tool use, reasoning, planning |
| AgentBench | General | Multiple task categories |

---

## Agent Frameworks

When to use a framework vs. build your own:

| Consideration | Use a Framework | Build Your Own |
|---|---|---|
| Time to first working agent | Faster | Slower |
| Operational control | Less | Full |
| Performance overhead | Some (abstraction cost) | None |
| Debugging complexity | Can be harder (abstraction layers) | Direct |
| Production reliability | Depends on framework maturity | Depends on your quality |

**"Just write a loop" argument:** For many production agent systems, a well-designed custom agent loop (100–200 lines of Python) is more maintainable and debuggable than a framework. The core loop is simple; frameworks add value in state management, multi-agent coordination, and observability tooling.

### Framework Comparison

| Framework | Strengths | Weaknesses | Best For |
|---|---|---|---|
| **LangGraph** | Graph-based flows, checkpointing, HITL support, well-maintained | Steep learning curve, complex API | Complex stateful workflows |
| **CrewAI** | Simple multi-agent setup, role-based | Less flexible for custom patterns | Multi-agent role-play |
| **AutoGen** | Research-oriented, conversational agents | Heavy, Microsoft-centric | Experimental multi-agent |
| **Custom loop** | Full control, no dependencies | More code to write | Production systems |

**LangGraph** is currently the most production-ready option for complex workflows. For simpler single-agent systems, raw SDK code is often better.

---

## Error Handling in Agents

### Error Taxonomy

| Error Type | Cause | Retry? | Response to Model |
|---|---|---|---|
| Tool timeout | Network/service slow | Yes (1×) | "Tool timed out. Try a different approach." |
| Invalid arguments | Model formatting error | Yes | "Invalid args: {validation_error}. Please check the schema." |
| Resource not found | Incorrect ID/path | No | "Resource not found. Please verify the identifier." |
| Permission denied | Access control | No | "Access denied. This action requires escalation." |
| Service unavailable | External system down | Yes (2×) | "Service unavailable. Try later or use an alternative." |
| Rate limited | Too many calls | Yes (after wait) | "Rate limited. Waiting 2 seconds then retrying." |

### Loop Detection

```python
def detect_loop(
    messages: list[dict],
    window: int = 6
) -> bool:
    """Detect if the agent is repeating the same tool calls."""

    # Get recent tool calls
    recent_tool_calls = [
        (msg["name"], json.dumps(msg.get("args", {}), sort_keys=True))
        for msg in messages[-window:]
        if msg["role"] == "tool_call"
    ]

    if len(recent_tool_calls) < 4:
        return False

    # Check for repetition
    unique_calls = set(recent_tool_calls)
    repetition_rate = 1 - len(unique_calls) / len(recent_tool_calls)

    return repetition_rate > 0.5  # >50% repetition = likely stuck
```

---

## Computer Use and Browser Agents

A frontier capability: agents that can control computer interfaces — clicking, typing, navigating UIs — just like a human would.

### How It Works

The agent receives screenshots (or structured accessibility trees) of the computer screen, reasons about what to do, and outputs actions:

```python
tools = [
    {
        "name": "screenshot",
        "description": "Take a screenshot of the current screen",
    },
    {
        "name": "click",
        "description": "Click at a specific location on the screen",
        "parameters": {
            "x": {"type": "integer"},
            "y": {"type": "integer"}
        }
    },
    {
        "name": "type",
        "description": "Type text at the current cursor position",
        "parameters": {
            "text": {"type": "string"}
        }
    },
    {
        "name": "key",
        "description": "Press keyboard shortcuts",
        "parameters": {
            "keys": {"type": "string", "description": "e.g., 'Return', 'ctrl+c'"}
        }
    }
]
```

### Current State and Limitations

- **Anthropic Claude computer use:** Available in API, works well for structured workflows with predictable UIs
- **OpenAI Operator:** Browser-based task automation
- **Reliability:** Still brittle. UI changes break agents. Error recovery is limited.
- **Speed:** Screenshot + inference + action is 2–5 seconds per step; complex tasks take minutes
- **Security concerns:** Agent has full desktop access — sandboxing is critical

**When to use:** Automating legacy systems with no API, web scraping at human-interaction level, internal tools that expose no API.

**When NOT to use:** When an API exists (always prefer API over computer use), when reliability requirements are high, when the UI is unstable.

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 6: Implement a Simple Orchestrator** [multi-agent] -- Implements the "Supervisor / Orchestrator" architecture from "Multi-Agent Architectures." You will build keyword-based intent classification and delegate to specialist agents -- the simplest version of the orchestrator pattern shown in the architecture diagram. Applies "Architecture Comparison" (supervisor is most common and debuggable).
- **Exercise 5: Build a Tool Call Validator** [safety] -- Supports the error handling patterns from "Error Handling in Agents." Validation prevents invalid arguments from reaching tool execution, which is critical for the "Error Taxonomy" (invalid arguments -> retry with corrected schema).
- **Exercise 1: Build a Complete Agent Loop** [core] -- The foundation that "Long-Running Agents" and "Human-in-the-Loop Patterns" build upon. Understanding the basic loop is prerequisite to adding checkpointing, idempotent tool calls, and approval workflows.

See also `examples.py`:
- `OrchestratorAgent` (Example 7) -- LLM-based routing to specialist agents with tool definitions
- `AgentConfig` and `specialists` dict (Example 7) -- specialist configuration and delegation
- `safe_execute_tool()` (Example 6) -- validation + approval check before execution

---

## Interview Q&A: Advanced Agent Systems

**Q: Compare different multi-agent architectures.**

Three main patterns: supervisor (one orchestrator coordinates specialized sub-agents), peer (agents collaborate as equals), and hierarchical (multiple layers of orchestrators and workers). Supervisor is the most common and most debuggable — a single model routes and coordinates, easy to reason about. Peer architectures are more flexible but harder to debug — agents negotiate without central control, which can lead to loops or conflicts. Hierarchical is for complex enterprise workflows where sub-tasks themselves need orchestration. My default recommendation: start with a single agent. Add agents only when proven necessary. Multi-agent architectures add failure modes, observability challenges, and testing complexity that single agents avoid.

**Q: How do you handle errors and safety in agent systems?**

Errors at multiple layers. Tool-level: wrap every execution in error handling and return structured messages the model can reason about — the model is surprisingly good at recovering when given useful error context. Agent-level: cap iterations, implement circuit breakers (same tool failing 3 times = stop calling it), have fallback behavior — the model should explain what it couldn't accomplish rather than silently failing. Safety is about constraining the action space: categorize tools by risk level (read = auto, write = confirm, destructive = human approval), validate tool inputs before execution (never trust model-generated SQL or shell commands blindly), and rate-limit expensive tools. The hardest challenge is indirect prompt injection: malicious content in retrieved documents instructing the agent to call tools with harmful arguments. Defense: validate tool arguments independently of the model's reasoning.

**Q: When would you choose LangGraph over writing a custom agent loop?**

LangGraph when: the workflow is genuinely complex (branching paths, checkpointing, human-in-the-loop at multiple points), the team is familiar with graph-based thinking, and the framework's abstractions match the problem structure. Custom loop when: the workflow is relatively linear, you need full control over every aspect of execution, debuggability is paramount (no framework abstraction layers), or the team does not have LangGraph expertise. The "just write a loop" argument: a well-designed 200-line custom agent loop is more maintainable than a complex LangGraph setup for many production cases. Frameworks add value in state management, multi-agent coordination, and built-in observability. Evaluate whether you actually need those features before adopting the complexity.

**Q: How do you evaluate agent quality?**

Agents require trajectory-level evaluation, not just output-level. Measure: task completion rate (did it actually finish the task?), step efficiency (did it take the minimal reasonable path?), tool call accuracy (right tool, right arguments), error recovery rate, and cost per task. For trajectory evaluation, use an LLM-as-judge that scores each dimension of the execution path. Build a golden evaluation set of representative tasks with expected behavior (not just expected outputs, but expected tool call sequences). Run it after every significant change. Monitor production: sample real agent runs, check for repetition patterns, cost anomalies, and error spikes. Track cost per completed task — an agent that completes tasks cheaply is better than one that is slightly more accurate but costs 10× more.
