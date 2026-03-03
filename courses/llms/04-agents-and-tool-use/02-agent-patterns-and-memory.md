# 02 — Agent Patterns and Memory

## What is an Agent?

An agent is an LLM-based system that autonomously decides what actions to take, executes those actions via tools, observes the results, and continues until it completes a task or reaches a stopping condition. Unlike a simple chatbot that responds once per turn, an agent can take multiple sequential actions, adapting based on what it observes.

The minimum viable agent:
```
1. Receive a goal or task
2. Decide what action to take (tool call or final response)
3. Execute the action
4. Observe the result
5. Update context
6. Go to step 2 (loop until done or max iterations reached)
```

---

## The Core Agent Loop

### Architecture

```
User Input
     │
     ▼
┌────────────────────────────────────────────┐
│              AGENT LOOP                     │
│                                            │
│  ┌─────────────────────────────────────┐  │
│  │         LLM (Decision Maker)        │  │
│  │                                     │  │
│  │  Input: conversation history +      │  │
│  │         tool definitions +          │  │
│  │         system prompt               │  │
│  │                                     │  │
│  │  Output: text response OR           │  │
│  │          tool call(s)               │  │
│  └───────────────┬─────────────────────┘  │
│                  │                         │
│      Text? → Exit loop → Return to user   │
│                  │                         │
│      Tool calls? ↓                         │
│  ┌───────────────▼─────────────────────┐  │
│  │         Tool Executor               │  │
│  │                                     │  │
│  │  - Validate arguments               │  │
│  │  - Execute tool (API call, DB, etc) │  │
│  │  - Handle errors                    │  │
│  │  - Return structured result         │  │
│  └───────────────┬─────────────────────┘  │
│                  │                         │
│  Append result to conversation history    │
│  Check: iteration limit reached?           │
│  Loop back to LLM ←──────────────────────┘│
└────────────────────────────────────────────┘
```

### Implementation

```python
import json
from dataclasses import dataclass, field

@dataclass
class AgentState:
    messages: list[dict] = field(default_factory=list)
    iteration: int = 0
    tool_call_counts: dict = field(default_factory=dict)

def run_agent(
    user_input: str,
    system_prompt: str,
    tools: list[dict],
    tool_implementations: dict,
    max_iterations: int = 10
) -> str:
    state = AgentState(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    while state.iteration < max_iterations:
        state.iteration += 1

        # Get model decision
        response = llm_call_with_tools(state.messages, tools)
        state.messages.append(response.to_dict())

        # If text response, we're done
        if not response.tool_calls:
            return response.text

        # Execute each tool call
        for tool_call in response.tool_calls:
            tool_name = tool_call.name

            # Circuit breaker: avoid infinite loops on same tool
            state.tool_call_counts[tool_name] = state.tool_call_counts.get(tool_name, 0) + 1
            if state.tool_call_counts[tool_name] > 3:
                result = {
                    "error": "tool_limit_exceeded",
                    "message": f"Tool '{tool_name}' has been called too many times. "
                               "Please provide your best answer with available information."
                }
            else:
                result = execute_tool_safely(tool_name, tool_call.args, tool_implementations)

            state.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

    # Max iterations reached — get final answer
    state.messages.append({
        "role": "user",
        "content": "You've reached the maximum number of steps. Please provide your best "
                   "answer based on the information gathered so far."
    })
    final = llm_call(state.messages)
    return final
```

---

## Exit Conditions and Safety

**Never let an agent loop indefinitely.** Multiple exit conditions are required:

| Condition | Response |
|---|---|
| Model returns text with no tool calls | Normal exit — return the response |
| Maximum iterations reached | Request a final answer from the model with what it has |
| Same tool called >3 times | Circuit breaker — return error to model |
| Error rate too high | Stop and explain what couldn't be accomplished |
| Destructive action without confirmation | Pause and request user confirmation |
| Budget/cost limit exceeded | Stop with explanation |

---

## Planning Patterns

### Implicit Planning (Most Common)

Modern models with strong tool-use capabilities plan implicitly — they decide what to do next based on the current conversation context. No explicit plan is generated.

```
User: "Find the top 3 products by revenue this quarter and compare to last quarter"

Model response (implicit planning):
Tool call: query_database("SELECT product_id, SUM(revenue) FROM sales WHERE quarter='Q4-2024' GROUP BY product_id ORDER BY SUM(revenue) DESC LIMIT 3")
[executes]
Tool call: query_database("SELECT product_id, SUM(revenue) FROM sales WHERE quarter='Q3-2024' AND product_id IN (top_3_ids) GROUP BY product_id")
[executes]
Text: "Here's the comparison: ..."
```

### Explicit Plan-Then-Execute

For complex multi-step tasks, have the model first generate a plan and present it for approval, then execute:

```python
def plan_then_execute(
    task: str,
    tools: list[dict],
    require_approval: bool = True
) -> str:
    # Phase 1: Generate plan
    plan_prompt = f"""You are planning how to complete the following task.
Generate a numbered step-by-step plan. Be specific about what actions and
information you need at each step.

Task: {task}

Available tools: {json.dumps([t['name'] for t in tools])}

Generate the plan only — do not execute yet."""

    plan = llm_call(plan_prompt)

    if require_approval:
        print(f"Proposed plan:\n{plan}")
        approval = input("Approve? (yes/no/modify): ")
        if approval.lower() == "no":
            return "Task cancelled by user."
        elif approval.lower() == "modify":
            modifications = input("What changes? ")
            plan = revise_plan(plan, modifications)

    # Phase 2: Execute the plan
    return execute_plan(plan, tools)
```

### Plan-and-Revise

For tasks where circumstances change during execution, the agent revises its plan based on what it discovers:

```python
def adaptive_execute(task: str, plan: str, discovery: str) -> str:
    """Update the plan when new information changes the approach."""
    revise_prompt = f"""The original plan was:
{plan}

During execution, we discovered:
{discovery}

Given this new information, revise the remaining steps of the plan.
Only output the revised remaining steps."""

    return llm_call(revise_prompt)
```

---

## The ReAct Pattern

ReAct (Reasoning + Acting) structures agent behavior as an explicit Thought → Action → Observation loop. Each step the model explicitly reasons about what to do before acting.

```
User: "What is the current weather in the top 3 cities by population?"

Thought: I need to find the top 3 cities by population, then get weather for each.
Action: search_web("top 3 cities by population 2024")
Observation: [Results: Tokyo (13.96M), Delhi (32.94M), Shanghai (24.87M)]

Thought: I have the cities. Now I'll get weather for each. I can call them in parallel.
Action: get_weather({"city": "Tokyo"}), get_weather({"city": "Delhi"}), get_weather({"city": "Shanghai"})
Observation: [Tokyo: 18°C, partly cloudy], [Delhi: 32°C, sunny], [Shanghai: 22°C, overcast]

Thought: I have all the information needed for a complete answer.
Response: Here is the current weather for the top 3 cities by population...
```

### Explicit vs. Implicit ReAct

**Explicit ReAct:** Structure the prompt to require Thought/Action/Observation formatting. More debuggable — every reasoning step is visible. Uses more tokens.

**Implicit ReAct:** Modern models with native tool use do this internally without explicit formatting. Less verbose, but less transparent.

**Recommendation:** Use implicit ReAct (native tool use) for production systems. Use explicit formatting for debugging and understanding why the agent is making specific choices.

---

## Memory Systems

Agents need memory to function beyond a single interaction. Different memory types serve different purposes.

### Memory Architecture

```
┌─────────────────────────────────────────────────┐
│                  AGENT MEMORY                   │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  IN-CONTEXT MEMORY (working memory)     │   │
│  │  Full conversation history              │   │
│  │  Available immediately                  │   │
│  │  Limited by context window              │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  EXTERNAL MEMORY                        │   │
│  │  ┌─────────────┐  ┌──────────────────┐  │   │
│  │  │  Episodic   │  │  Semantic/Long-  │  │   │
│  │  │  (memories  │  │  Term (facts,    │  │   │
│  │  │  of past    │  │  preferences,    │  │   │
│  │  │  sessions)  │  │  knowledge base) │  │   │
│  │  └─────────────┘  └──────────────────┘  │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  TOOL STATE (read-only access to        │   │
│  │  databases, APIs, files — not "memory"  │   │
│  │  but serves the same function)          │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Conversation History Strategies

**Full History**
```python
# Simple: keep everything
messages = [system_prompt] + full_history + [current_user_message]
```
- Pro: Complete context, no information loss
- Con: Token cost grows linearly, eventually hits context limit

**Sliding Window**
```python
# Keep only the last N turns
MAX_TURNS = 10
recent_messages = conversation_history[-(MAX_TURNS * 2):]
messages = [system_prompt] + recent_messages + [current_user_message]
```
- Pro: Predictable cost, prevents context overflow
- Con: Silently loses older context

**Summarization**
```python
def manage_history_with_summary(
    messages: list[dict],
    max_messages: int = 20
) -> tuple[list[dict], str]:
    """Compress old messages into a summary when history gets long."""

    if len(messages) <= max_messages:
        return messages, ""

    # Split: keep recent turns verbatim, summarize older turns
    to_summarize = messages[:-10]  # All but the last 5 turns
    to_keep = messages[-10:]       # Keep last 5 turns verbatim

    summary = llm_call(
        f"Summarize the key information from this conversation, "
        f"including decisions made, information gathered, and current task state:\n\n"
        f"{format_messages(to_summarize)}"
    )

    return to_keep, summary

# Usage:
recent_messages, summary = manage_history_with_summary(full_history)
if summary:
    summary_context = {
        "role": "system",
        "content": f"Earlier conversation summary: {summary}"
    }
    messages = [system_prompt, summary_context] + recent_messages + [current_message]
```

**Retrieval-Based Memory**
```python
class AgentMemoryStore:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def save_memory(self, session_id: str, content: str, importance: float):
        embedding = embed(content)
        self.vector_store.upsert({
            "id": f"{session_id}_{timestamp()}",
            "vector": embedding,
            "metadata": {
                "content": content,
                "session_id": session_id,
                "importance": importance,
                "timestamp": timestamp()
            }
        })

    def retrieve_relevant(self, query: str, k: int = 5) -> list[str]:
        query_embedding = embed(query)
        results = self.vector_store.query(
            vector=query_embedding,
            top_k=k,
            filter={"importance": {"$gte": 0.5}}
        )
        return [r["metadata"]["content"] for r in results]
```

### Memory System Comparison

| Type | Capacity | Retrieval | Best For |
|---|---|---|---|
| Full conversation history | Context window | Immediate | Short sessions |
| Sliding window | Fixed N turns | Immediate | Controlled cost |
| Summarization | Unlimited (compressed) | Immediate (in context) | Long sessions |
| Retrieval-based | Unlimited (in vector store) | 10–50ms | Long-term user preferences, past session recall |
| External database | Unlimited | Query-time | Structured facts, exact lookup |

---

## Guardrails for Agents

### Tool Risk Categories

```python
TOOL_RISK_LEVELS = {
    "search_knowledge_base": "read",       # Auto-execute
    "get_order_status": "read",            # Auto-execute
    "send_email": "write",                 # Confirm before executing
    "update_user_profile": "write",        # Confirm before executing
    "initiate_refund": "write_financial",  # Explicit user confirmation
    "delete_account": "destructive",       # Require typed confirmation
}

def should_execute_tool(tool_name: str, args: dict, conversation: list) -> bool:
    risk = TOOL_RISK_LEVELS.get(tool_name, "unknown")

    if risk == "read":
        return True  # Auto-execute

    if risk == "write":
        # Check if user has implicitly authorized
        return user_has_authorized_write_operations(conversation)

    if risk in ("write_financial", "destructive"):
        # Require explicit confirmation
        return False  # Must ask user first

    return False  # Unknown risk = don't execute
```

### Confirmation Pattern

```python
def execute_with_confirmation(
    tool_name: str,
    args: dict,
    get_user_confirmation: callable
) -> dict:
    risk = TOOL_RISK_LEVELS.get(tool_name, "unknown")

    if risk in ("write_financial", "destructive"):
        # Present the action and get explicit confirmation
        action_summary = format_action_summary(tool_name, args)
        confirmed = get_user_confirmation(
            f"I'd like to perform this action:\n{action_summary}\n\nProceed? (yes/no)"
        )

        if not confirmed:
            return {
                "result": "cancelled",
                "message": "Action was cancelled by the user."
            }

    return execute_tool(tool_name, args)
```

### Sandboxing Tool Execution

```python
import subprocess
import tempfile
import os

def execute_code_safely(code: str, language: str = "python") -> dict:
    """Execute model-generated code in an isolated environment."""

    if language == "python":
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True,
                text=True,
                timeout=30,           # Hard timeout
                # Resource constraints (Linux)
                env={
                    **os.environ,
                    "PYTHONPATH": "",   # Restrict imports
                },
                # No network access in production
            )
            return {
                "stdout": result.stdout[:5000],   # Limit output size
                "stderr": result.stderr[:1000],
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "timeout", "message": "Code execution exceeded 30 seconds"}
        finally:
            os.unlink(temp_path)
```

---

## MCP: Model Context Protocol

MCP (Model Context Protocol) is an open protocol originated by Anthropic that standardizes how AI applications connect to external tools and data sources.

### The Problem MCP Solves

Without MCP, every tool integration requires custom code:
```
LLM App A needs Tool X → custom integration code
LLM App B needs Tool X → different custom integration code
LLM App A needs Tool Y → another custom integration
```

With MCP, tool providers build once and all MCP-compatible clients can use it:
```
Tool X → MCP Server (built once)
Tool Y → MCP Server (built once)
LLM App A → MCP Client → connects to any MCP server
LLM App B → MCP Client → connects to any MCP server
```

### MCP Architecture

```
┌────────────────────────────┐    ┌────────────────────────────┐
│      MCP HOST              │    │        MCP SERVER          │
│  (AI application)          │    │    (tool/data provider)    │
│                            │    │                            │
│  ┌──────────────────────┐  │    │  ┌──────────────────────┐  │
│  │   MCP CLIENT         │◄─┼────┼─►│  Tools               │  │
│  │   - Discovers tools  │  │    │  │  - search_files()    │  │
│  │   - Calls tools      │  │    │  │  - run_query()       │  │
│  │   - Reads resources  │  │    │  │  Resources           │  │
│  └──────────────────────┘  │    │  │  - database://table  │  │
│                            │    │  │  Prompts             │  │
└────────────────────────────┘    │  │  - templates         │  │
                                  │  └──────────────────────┘  │
                                  └────────────────────────────┘
```

### Key MCP Concepts

| Concept | Description |
|---|---|
| **Tool** | A callable function exposed by the server (like function calling) |
| **Resource** | A data source with a URI (like a file or database table) |
| **Prompt** | A reusable prompt template exposed by the server |
| **Transport** | How client and server communicate (stdio for local, HTTP/SSE for remote) |
| **Discovery** | Client lists available tools/resources from the server at startup |

### Connection Flow

```
1. Server starts (stdio or HTTP)
2. Client connects
3. Client calls list_tools() → server returns tool definitions
4. Client calls list_resources() → server returns available data sources
5. User makes request to LLM
6. LLM may call a tool → client forwards to server → server executes → result returned
7. LLM uses result in response
```

### Why MCP Matters in Interviews

- Growing ecosystem: many enterprise tool providers are building MCP servers
- Standardization benefit: one integration standard instead of N custom ones
- Interview signal: mentioning MCP shows awareness of the current ecosystem and production concerns
- Practical: Claude Desktop, Cursor, and other AI tools already support MCP natively

---

## Agent Debugging Checklist

```
Before blaming the model:
□ Is the system prompt clear about the agent's purpose and constraints?
□ Are tool descriptions specific enough to guide correct tool selection?
□ Are tool schemas precise (correct types, enums, required fields)?
□ Is conversation history being passed correctly?

Execution issues:
□ Are tool errors being returned to the model (not thrown as exceptions)?
□ Is the tool result format what the model expects?
□ Are parallel tool calls being handled correctly (all results before next call)?

Reliability issues:
□ Is there a maximum iteration limit?
□ Are there circuit breakers for repeated tool failures?
□ Is there a timeout for individual tool executions?
□ What happens if the LLM provider call fails?

Observability:
□ Is every tool call logged with arguments, result, and latency?
□ Is the agent's decision at each step logged?
□ Is the total cost per agent run being tracked?
```

---

## Key Numbers

| Metric | Value |
|---|---|
| Default max agent iterations | 10–15 |
| Tool call circuit breaker | 3 same-tool calls |
| Tool execution timeout | 30 seconds |
| Max recommended concurrent tool calls | 5 |
| Agent loop cost multiplier | 3–10× vs single call |
| Recommended max tools in one agent | 20–30 |

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 1: Build a Complete Agent Loop** [core] -- Directly implements "The Core Agent Loop" architecture: send messages to LLM, detect tool calls, execute tools, append results, loop until text or max iterations. Also applies "Exit Conditions and Safety" (max iteration limit).
- **Exercise 2: Implement the ReAct Pattern** [reasoning] -- Implements "The ReAct Pattern": explicit Thought/Action/Observation trace. You will track each reasoning step, execute tool calls, record observations, and detect the final answer.
- **Exercise 4: Implement Conversation Memory with Sliding Window** [memory] -- Implements the memory strategies from "Memory Systems": sliding window (keep last N messages) + summarization (compress older messages). Applies "Conversation History Strategies" and "Memory System Comparison."
- **Exercise 6: Implement a Simple Orchestrator** [multi-agent] -- Uses the agent loop from this file as the execution engine for specialist agents. The orchestrator classifies intent and delegates -- applying patterns from "The Core Agent Loop" at the specialist level.

See also `examples.py`:
- `agent_loop()` (Example 1) -- async agent loop with tool execution
- `react_agent()` and `REACT_SYSTEM_PROMPT` (Example 5) -- ReAct pattern with trace logging
- `ConversationMemory` and `agent_with_memory()` (Example 4) -- memory with summarization

---

## Interview Q&A: Agent Patterns and Memory

**Q: Design an agent loop. What are the key considerations?**

The core loop: send messages plus tool definitions to the LLM, check if the response contains tool calls or text. If text, return to the user. If tool calls, execute each, append results to message history, and loop. Cap at a maximum iteration count (10–15) to prevent infinite loops. Key considerations beyond the basic loop: error handling (return structured error messages to the model so it can reason about alternatives, not crash the loop), parallel vs. sequential tool execution (parallel when the provider supports it, reduces round trips), guardrails (categorize tools by risk level — reads execute automatically, writes need confirmation, destructive actions need explicit approval), context management (long tool results fill the context window fast — summarize or truncate large outputs), and observability (log every iteration with decision, tool called, result, and time).

**Q: What is the ReAct pattern?**

ReAct (Reasoning + Acting) is an agent pattern where the model explicitly alternates between reasoning and acting: Thought (reason about what to do next), Action (call a tool), Observation (process the result). This chain continues until the model has enough information to answer. The key insight: explicit reasoning steps improve tool-use accuracy. Without ReAct, the model might jump to a tool call without considering whether it's the right approach. With ReAct, the reasoning step forces deliberate planning. In practice, use implicit ReAct (native tool use loop) for production systems. Use explicit Thought/Action/Observation formatting for debugging when you need to understand the model's decision-making.

**Q: How do you choose a memory strategy for an agent?**

It depends on session length and what needs to be remembered. For short tasks (< 20 turns), full history works fine — simplest implementation, no information loss. For longer sessions, use summarization: compress older turns while keeping recent turns verbatim for conversational coherence. For multi-session memory (user preferences, past decisions), use retrieval-based memory: embed and store important memories in a vector store, retrieve relevant ones at each turn. The system prompt is always present — it's the agent's identity and constraints. Never truncate the system prompt. A hybrid approach often works best: full recent history + running summary + retrieval for very old context.
