# 01 — Function Calling and Tool Use

## What is Tool Use?

Tool use (also called function calling) is the mechanism that transforms LLMs from text generators into autonomous systems that can take actions in the real world. The model does not execute anything itself — it outputs structured requests describing what action to take, and your application code executes those actions and returns the results.

**The fundamental pattern:**
```
1. You define available tools as schemas (name, description, parameters)
2. You send the tool definitions along with the conversation
3. The model either responds with text OR outputs a tool call request
4. Your code validates the arguments, executes the tool, returns the result
5. The model processes the result and either calls another tool or responds to the user
```

This separation is what makes tool use safe: your application is the execution layer and the trust boundary. The model can only request actions; your code decides whether to execute them.

---

## Tool Schema Design

The tool schema is how you communicate what a tool does, when to use it, and how to call it. The description field is the most important — the model uses it to decide when and how to invoke each tool.

### OpenAI Format

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search the internal product knowledge base for relevant articles, "
                "FAQs, and documentation. Use this when the user asks a product "
                "question that may be answered in our documentation. "
                "Do NOT use for account-specific questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Be specific and use product terminology."
                    },
                    "category": {
                        "type": "string",
                        "enum": ["product", "billing", "technical", "account"],
                        "description": "Category to filter results. Use 'technical' for errors and bugs."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return. Default: 5, max: 10.",
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            }
        }
    }
]
```

### Anthropic Format

```python
tools = [
    {
        "name": "search_knowledge_base",
        "description": (
            "Search the internal product knowledge base for relevant articles, "
            "FAQs, and documentation. Use this when the user asks a product "
            "question that may be answered in our documentation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific."
                },
                "category": {
                    "type": "string",
                    "enum": ["product", "billing", "technical", "account"]
                }
            },
            "required": ["query"]
        }
    }
]
```

### Google (Gemini) Format

```python
from google.generativeai.types import FunctionDeclaration, Tool

search_kb = FunctionDeclaration(
    name="search_knowledge_base",
    description="Search the internal knowledge base for product information.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "category": {"type": "string", "enum": ["product", "billing", "technical"]}
        },
        "required": ["query"]
    }
)
tools = Tool(function_declarations=[search_kb])
```

---

## Tool Design Best Practices

### Write Descriptions That Guide the Model

The model uses the description to decide WHEN to call a tool and HOW to format the arguments. Treat descriptions as prompts:

```python
# Bad: vague, model won't know when to use this
"description": "Gets information"

# Good: specific about when to use and what it does
"description": (
    "Look up a customer's account information by their email address or customer ID. "
    "Use this when the user mentions their account, subscription, billing, or when "
    "you need to verify their identity. Do NOT call this more than once per conversation "
    "unless the user provides a different email/ID."
)
```

### Error Messages Enable Recovery

When a tool fails, return a structured error message that helps the model reason about alternatives:

```python
def execute_tool(name: str, args: dict) -> dict:
    try:
        return tool_implementations[name](**args)
    except DatabaseConnectionError:
        return {
            "error": "database_unavailable",
            "message": "The database is temporarily unavailable. "
                       "Please try again in a moment or use the cached data endpoint.",
            "retry_after": 5
        }
    except ResourceNotFoundError as e:
        return {
            "error": "not_found",
            "message": f"No record found for {e.resource_type}: {e.identifier}. "
                       "Please verify the input and try with different search terms.",
        }
    except PermissionError:
        return {
            "error": "insufficient_permissions",
            "message": "This action requires elevated permissions. "
                       "Please ask the user to contact support for this request.",
            "escalate": True
        }
```

### Make Tools Idempotent

Idempotent tools can be called multiple times with the same arguments and produce the same result. This is essential for agent reliability:

```python
# Good: idempotent
def set_email_preference(user_id: str, preference: str) -> dict:
    """Always sets the preference to the given value, regardless of current state."""
    db.update("users", user_id, {"email_preference": preference})
    return {"success": True, "email_preference": preference}

# Problematic: not idempotent
def toggle_email_notifications(user_id: str) -> dict:
    """Flips the current state — calling twice returns to original state."""
    current = db.get("users", user_id)["email_notifications"]
    new_state = not current
    db.update("users", user_id, {"email_notifications": new_state})
    return {"email_notifications": new_state}
```

### Parameter Design Rules

1. **Specific types over strings:** Use `enum` for constrained values, `integer` for numbers, `boolean` for flags. The model produces better-formatted arguments with specific types.
2. **Required vs. optional:** Only mark parameters as required if the tool cannot function without them.
3. **Clear default values:** Describe defaults in the parameter description.
4. **Avoid ambiguous parameters:** If a parameter could be interpreted multiple ways, name it more specifically.
5. **Limit the number of parameters:** More than 5–7 parameters increases the chance of the model misformatting arguments.

---

## Executing Tool Calls: OpenAI

```python
from openai import OpenAI
import json

client = OpenAI()

def run_with_tools(
    messages: list[dict],
    tools: list[dict],
    tool_implementations: dict
) -> str:
    """Run a single turn with potential tool calls."""

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto"  # or "required" to force tool use
        )

        message = response.choices[0].message

        # Add the assistant's message to history
        messages.append(message.model_dump(exclude_none=True))

        # If no tool calls, return the text response
        if not message.tool_calls:
            return message.content

        # Execute all tool calls
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            # Execute the tool
            result = tool_implementations.get(tool_name, unknown_tool)(tool_args)

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })
        # Loop back to get the next model response
```

**Parallel tool calls:** OpenAI supports calling multiple tools in a single response. The model returns multiple tool calls; execute them all before the next model call:

```python
# Response may contain parallel tool calls:
# tool_calls = [
#     ToolCall(name="lookup_order", args={"order_id": "123"}),
#     ToolCall(name="check_inventory", args={"product_id": "456"})
# ]
# Execute both before the next model call — reduces round trips
```

---

## Executing Tool Calls: Anthropic

```python
import anthropic
import json

client = anthropic.Anthropic()

def run_with_tools(
    messages: list[dict],
    tools: list[dict],
    tool_implementations: dict
) -> str:
    """Run a single turn with potential tool calls."""

    while True:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        # Add assistant response to messages
        messages.append({
            "role": "assistant",
            "content": response.content
        })

        # If no tool use blocks, extract and return text
        if response.stop_reason != "tool_use":
            text_blocks = [b for b in response.content if b.type == "text"]
            return text_blocks[0].text if text_blocks else ""

        # Execute each tool use block
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = tool_implementations.get(block.name, unknown_tool)(block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result)
                })

        # Add tool results and loop
        messages.append({
            "role": "user",
            "content": tool_results
        })
```

---

## Provider Feature Comparison

| Feature | OpenAI | Anthropic | Google (Gemini) |
|---|---|---|---|
| Parallel tool calls | Yes | Yes | Yes |
| Tool choice (force specific tool) | Yes | Yes | Yes |
| Streaming with tool calls | Yes | Yes | Yes |
| Tool result format | `role: "tool"` | Content block in user message | FunctionResponse |
| Structured output | JSON mode + schema | Tool use | Similar |
| Vision in tool context | Yes | Yes | Yes |

---

## Structured Output vs. Tool Use

When you need the model to produce structured data, you have two options:

| | Tool Use for Output | JSON Mode / Schema |
|---|---|---|
| **Guarantee** | Strong (provider-enforced schema) | Strong (with json_schema) |
| **Semantics** | "The model is calling a tool to submit data" | "The model is generating a response in a format" |
| **Best for** | When you want to frame it as an "action" | When the output is clearly a response, not an action |
| **Anthropic recommendation** | Use tool use for structured extraction | Both work |
| **OpenAI recommendation** | Both work | json_schema for responses |

**Anthropic's recommendation:** Use tool use when you want Claude to produce structured data reliably, even when it's not taking a real action. Define a tool like `extract_entities` and force its use with `tool_choice={"type": "tool", "name": "extract_entities"}`.

---

## Tool Call Validation

Never blindly trust tool arguments from the model. Validate before executing:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class SearchKnowledgeBaseArgs(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = Field(None, pattern="^(product|billing|technical|account)$")
    max_results: int = Field(5, ge=1, le=10)

    @validator("query")
    def no_injection(cls, v):
        # Basic injection detection
        suspicious_patterns = ["ignore previous", "system prompt", "jailbreak"]
        if any(p in v.lower() for p in suspicious_patterns):
            raise ValueError("Query contains suspicious patterns")
        return v

def execute_tool_safely(name: str, raw_args: dict) -> dict:
    schemas = {
        "search_knowledge_base": SearchKnowledgeBaseArgs,
        # ... other tools
    }

    if name not in schemas:
        return {"error": "unknown_tool", "message": f"Tool '{name}' not found"}

    try:
        validated_args = schemas[name](**raw_args)
        return tool_implementations[name](**validated_args.model_dump())
    except ValidationError as e:
        return {
            "error": "invalid_arguments",
            "message": f"Invalid tool arguments: {e}",
            "details": e.errors()
        }
```

---

## Key Numbers for Tool Use

| Metric | Value |
|---|---|
| Tool call latency overhead | ~100–300ms per round trip |
| Max recommended tools (practical) | 20–30 (model performance degrades with more) |
| Parallel tool calls | Up to 5 in a single response (common limit) |
| Agent loop max iterations | 10–15 (default ceiling) |
| Tool description optimal length | 2–4 sentences |
| Input schema parameter count | ≤ 7 (beyond this, argument quality degrades) |

---

## Interview Q&A: Function Calling and Tool Use

**Q: How does function calling / tool use work?**

You define available tools as schemas — name, description, and parameter definitions in JSON Schema format. The description is critical because the model uses it to decide when to invoke each tool. You send the tool definitions alongside the conversation, and the model either responds with text or outputs a structured tool call. Your code validates the arguments, executes the tool, and returns the result. The model then incorporates the result and either makes another tool call or responds to the user. The model never executes anything itself — it only outputs structured requests. Your application is the execution layer and the trust boundary. Different providers have slightly different APIs but the pattern is universal.

**Q: What makes a good tool description?**

A good description tells the model exactly when to use this tool, what it does, and any important constraints. Think of it as a prompt that guides tool selection. Include: what the tool does, when to call it (specific trigger conditions), when NOT to call it (disambiguation from similar tools), and any important side effects (this action cannot be undone, costs money, sends an email). Bad descriptions are vague — "gets information" — and lead to incorrect tool selection. The description is more important than the schema parameters for correct tool use behavior.

**Q: How do you handle tool call validation and security?**

Never trust model-generated tool arguments without validation. Use Pydantic or equivalent to validate argument types, ranges, and formats against the expected schema. Check for injection attempts in string arguments — the model might be following malicious instructions from retrieved content. For destructive operations, implement confirmation patterns: the model proposes the action, your code asks the user to confirm before executing. Apply the principle of least privilege: each tool should only be able to do what it needs to do, with the minimum permissions required. Log every tool call and its arguments for auditability.
