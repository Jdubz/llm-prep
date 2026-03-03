"""
Module 04: Agents & Tool Use — Exercises

Complete the TODO sections. Each exercise focuses on a core agent pattern
you should be able to implement and explain in an interview.

Run with: python exercises.py (uses assert-based tests at the bottom)

Reference files in this directory:
  - 01-function-calling-and-tool-use.md  (tool schemas, execution loops, validation)
  - 02-agent-patterns-and-memory.md      (agent loop, ReAct, memory, guardrails, MCP)
  - 03-advanced-agent-systems.md         (multi-agent, long-running, evaluation)
  - examples.py                          (runnable reference implementations)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Shared types (same as examples.py — provided for you)
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    role: str
    content: str
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


@dataclass
class LLMResponse:
    """Simulated LLM response for testing without an API."""
    content: str = ""
    tool_calls: list[ToolCall] | None = None


# ---------------------------------------------------------------------------
# Exercise 1: Build a Complete Agent Loop
#
# READ FIRST:
#   02-agent-patterns-and-memory.md
#     -> "## The Core Agent Loop" (architecture diagram + implementation)
#     -> "## Exit Conditions and Safety" (when to stop looping)
#   01-function-calling-and-tool-use.md
#     -> "## Executing Tool Calls: OpenAI" (the while-loop pattern)
#
# ALSO SEE:
#   examples.py
#     -> "Example 1: Complete Agent Loop with Tool Execution"
#        - agent_loop()    (the async agent loop you will replicate synchronously)
#        - execute_tool()  (how tool results are appended as Message objects)
#
# Implement the core agent loop that:
# - Sends messages to an LLM (simulated)
# - Detects tool calls in the response
# - Executes tools and appends results
# - Loops until text response or max iterations
# ---------------------------------------------------------------------------

def execute_tool_sync(name: str, arguments: dict[str, Any]) -> str:
    """Simulated tool execution. Maps tool names to mock results."""
    mock_results = {
        "get_weather": json.dumps({"temp": 22, "condition": "sunny", "city": arguments.get("city", "unknown")}),
        "search_orders": json.dumps({"order_id": arguments.get("order_id", ""), "status": "shipped"}),
        "get_user": json.dumps({"name": "Alice", "email": "alice@example.com"}),
    }
    if name not in mock_results:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return mock_results[name]


def agent_loop(
    llm_responses: list[LLMResponse],
    tools: list[dict],
    initial_message: str,
    max_iterations: int = 10,
) -> tuple[str, list[Message]]:
    """
    Implement the agent loop.

    Args:
        llm_responses: Pre-scripted LLM responses (simulates the API).
                       Pop from the front for each iteration.
        tools: Tool definitions (for context, not used in execution).
        initial_message: The user's initial message.
        max_iterations: Safety limit on iterations.

    Returns:
        Tuple of (final_text_response, full_message_history)

    The loop should:
    1. Start with a system message and user message in the history
    2. For each iteration:
       a. Get the next LLM response (pop from llm_responses)
       b. If no tool calls -> return the text content
       c. If tool calls -> execute each tool, append results to history
    3. If max iterations reached, return "Max iterations reached."
    """
    messages: list[Message] = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content=initial_message),
    ]

    # TODO: Implement the agent loop
    #
    # Step-by-step:
    #   for iteration in range(max_iterations):
    #       if not llm_responses:
    #           break
    #       response = llm_responses.pop(0)
    #
    #       # Append assistant message to history
    #       messages.append(Message(
    #           role="assistant",
    #           content=response.content,
    #           tool_calls=response.tool_calls,
    #       ))
    #
    #       # If no tool calls -> final text answer
    #       if not response.tool_calls:
    #           return (response.content, messages)
    #
    #       # Execute each tool call and append result
    #       for tc in response.tool_calls:
    #           result = execute_tool_sync(tc.name, tc.arguments)
    #           messages.append(Message(
    #               role="tool",
    #               content=result,
    #               tool_call_id=tc.id,
    #           ))
    #
    #   return ("Max iterations reached.", messages)

    pass  # Replace with your implementation


# ---------------------------------------------------------------------------
# Exercise 2: Implement the ReAct Pattern
#
# READ FIRST:
#   02-agent-patterns-and-memory.md
#     -> "## The ReAct Pattern" (Thought -> Action -> Observation example)
#     -> "### Explicit vs. Implicit ReAct" (formatting vs native tool use)
#
# ALSO SEE:
#   examples.py
#     -> "Example 5: ReAct Pattern Implementation"
#        - REACT_SYSTEM_PROMPT  (the prompt that structures Thought/Action/Observation)
#        - react_agent()        (async ReAct loop with trace logging)
#
# Build a ReAct agent that maintains an explicit trace of
# Thought -> Action -> Observation steps.
# ---------------------------------------------------------------------------

@dataclass
class ReActStep:
    """One step in the ReAct trace."""
    thought: str
    action: str | None = None       # Tool name, or None if final answer
    action_input: dict | None = None
    observation: str | None = None   # Tool result


def react_agent(
    llm_responses: list[LLMResponse],
    max_steps: int = 5,
) -> tuple[str, list[ReActStep]]:
    """
    Implement a ReAct agent that tracks Thought/Action/Observation.

    Args:
        llm_responses: Pre-scripted responses. Each response has:
            - content: The "Thought" text
            - tool_calls: The "Action" (or None if final answer)
        max_steps: Maximum reasoning steps.

    Returns:
        Tuple of (final_answer, list_of_react_steps)

    For each step:
    1. Get the next LLM response
    2. Record the Thought (response.content)
    3. If tool_calls is None -> this is the final answer, return it
    4. If tool_calls exists -> execute the tool, record the Observation
    5. Continue until done or max_steps reached
    """
    trace: list[ReActStep] = []

    # TODO: Implement the ReAct loop
    #
    # Step-by-step:
    #   for step in range(max_steps):
    #       if not llm_responses:
    #           break
    #       response = llm_responses.pop(0)
    #
    #       # No tool calls -> final answer
    #       if not response.tool_calls:
    #           trace.append(ReActStep(thought=response.content))
    #           return (response.content, trace)
    #
    #       # Has tool calls -> record Thought + Action + Observation
    #       tc = response.tool_calls[0]  # one action per step
    #       observation = execute_tool_sync(tc.name, tc.arguments)
    #       trace.append(ReActStep(
    #           thought=response.content,
    #           action=tc.name,
    #           action_input=tc.arguments,
    #           observation=observation,
    #       ))
    #
    #   return ("Max steps reached.", trace)

    pass  # Replace with your implementation


# ---------------------------------------------------------------------------
# Exercise 3: Design Tool Schemas for a Customer Service Agent
#
# READ FIRST:
#   01-function-calling-and-tool-use.md
#     -> "## Tool Schema Design" -> "### OpenAI Format" (the JSON structure)
#     -> "## Tool Design Best Practices"
#        -> "### Write Descriptions That Guide the Model"
#        -> "### Parameter Design Rules"
#
# ALSO SEE:
#   examples.py
#     -> "Example 2: Tool Definitions with JSON Schema"
#        - CUSTOMER_SERVICE_TOOLS  (three complete tool definitions to use as template)
#        Each tool has: "type": "function", "function": {name, description, parameters}
#
# Define tool schemas for three customer service tools.
# Focus on clear descriptions that guide the model.
# ---------------------------------------------------------------------------

def create_customer_service_tools() -> list[dict]:
    """
    Create tool definitions for a customer service agent with three tools:

    1. search_knowledge_base
       - Searches company docs for product info, policies, FAQs
       - Parameters: query (required, string), category (optional, enum),
         max_results (optional, integer 1-10)

    2. create_ticket
       - Creates a support ticket for unresolved issues
       - Parameters: title (required, string), description (required, string),
         priority (required, enum: low/medium/high/urgent),
         customer_email (optional, string)

    3. transfer_to_human
       - Transfers the conversation to a human agent
       - Parameters: reason (required, string),
         department (required, enum: billing/technical/general),
         urgency (optional, enum: normal/high)

    Return a list of tool definitions in OpenAI format.
    Each tool description should clearly state:
    - What the tool does
    - When to use it (trigger conditions)
    - What it returns
    """

    # TODO: Define the three tool schemas
    #
    # Use the OpenAI format. Each tool follows this structure:
    #   {
    #       "type": "function",
    #       "function": {
    #           "name": "tool_name",
    #           "description": "What it does. When to use it. What it returns.",
    #           "parameters": {
    #               "type": "object",
    #               "properties": {
    #                   "param_name": {"type": "string", "description": "..."},
    #                   "enum_param": {"type": "string", "enum": ["a", "b", "c"]},
    #                   "int_param":  {"type": "integer", "minimum": 1, "maximum": 10},
    #               },
    #               "required": ["param_name"]
    #           }
    #       }
    #   }
    #
    # Key: descriptions should tell the model WHEN to use each tool and WHEN NOT to.
    # See examples.py CUSTOMER_SERVICE_TOOLS for a complete working example.

    tools = []

    # Tool 1: search_knowledge_base
    # TODO

    # Tool 2: create_ticket
    # TODO

    # Tool 3: transfer_to_human
    # TODO

    return tools


# ---------------------------------------------------------------------------
# Exercise 4: Implement Conversation Memory with Sliding Window
#
# READ FIRST:
#   02-agent-patterns-and-memory.md
#     -> "## Memory Systems" -> "### Memory Architecture" (diagram)
#     -> "### Conversation History Strategies"
#        - "Sliding Window" (keep last N turns)
#        - "Summarization" (compress old messages)
#     -> "### Memory System Comparison" (table of tradeoffs)
#
# ALSO SEE:
#   examples.py
#     -> "Example 4: Conversation Memory with Summarization"
#        - ConversationMemory class  (add, get_messages, needs_summarization, summarize)
#        - agent_with_memory()       (how memory integrates into the agent loop)
#
# Build a memory system that keeps recent messages and summarizes old ones.
# ---------------------------------------------------------------------------

@dataclass
class SlidingWindowMemory:
    """
    Conversation memory with sliding window and summarization.

    Keeps all messages but only returns recent ones to the LLM,
    with a summary of older messages prepended.
    """
    messages: list[Message] = field(default_factory=list)
    summary: str = ""
    window_size: int = 10

    def add_message(self, message: Message) -> None:
        """Add a message to the history."""
        # TODO: Append the message to self.messages
        # One line: self.messages.append(message)
        pass

    def get_context(self) -> list[Message]:
        """
        Return messages to send to the LLM.

        Rules:
        1. Always include system messages (role == "system") first
        2. If there's a summary, include it as a system message
        3. Include only the last `window_size` non-system messages
        """
        # TODO: Implement context retrieval
        #
        # Step-by-step:
        #   system_msgs = [m for m in self.messages if m.role == "system"]
        #   non_system  = [m for m in self.messages if m.role != "system"]
        #
        #   result = list(system_msgs)
        #   if self.summary:
        #       result.append(Message(
        #           role="system",
        #           content=f"Summary of earlier conversation:\n{self.summary}"
        #       ))
        #   result.extend(non_system[-self.window_size:])
        #   return result
        pass

    def should_summarize(self) -> bool:
        """Return True if there are more non-system messages than 2x window_size."""
        # TODO: Check if summarization is needed
        #   non_system = [m for m in self.messages if m.role != "system"]
        #   return len(non_system) > self.window_size * 2
        pass

    def create_summary_prompt(self) -> list[Message]:
        """
        Create messages to send to an LLM for summarization.

        Should include:
        1. A system message instructing the LLM to summarize
        2. The messages that need summarization (everything before the window)
        """
        # TODO: Build the summarization prompt
        #
        # Step-by-step:
        #   non_system = [m for m in self.messages if m.role != "system"]
        #   to_summarize = non_system[:-self.window_size]
        #   return [
        #       Message(role="system", content=(
        #           "Summarize the following conversation concisely. "
        #           "Preserve key facts, decisions, and user preferences."
        #       )),
        #       *to_summarize,
        #   ]
        pass

    def apply_summary(self, summary_text: str) -> None:
        """
        Apply a generated summary.

        1. Store the summary text in self.summary
        2. Remove the summarized messages (keep system + recent window_size)
        """
        # TODO: Apply the summary and trim old messages
        #
        # Step-by-step:
        #   self.summary = summary_text
        #   system_msgs = [m for m in self.messages if m.role == "system"]
        #   non_system  = [m for m in self.messages if m.role != "system"]
        #   self.messages = system_msgs + non_system[-self.window_size:]
        pass


# ---------------------------------------------------------------------------
# Exercise 5: Build a Tool Call Validator
#
# READ FIRST:
#   01-function-calling-and-tool-use.md
#     -> "## Tool Call Validation" (Pydantic example, injection detection)
#     -> "## Tool Design Best Practices" -> "### Parameter Design Rules"
#        (types, enums, required vs optional)
#
# ALSO SEE:
#   examples.py
#     -> "Example 6: Tool Call Validation and Error Handling"
#        - validate_tool_call()  (checks required params, enum, type, range)
#        - safe_execute_tool()   (validation + permission check + execution)
#
# Implement validation that checks tool call arguments against their schemas.
# ---------------------------------------------------------------------------

@dataclass
class ValidationError:
    field: str
    message: str


def validate_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    tool_schemas: list[dict],
) -> list[ValidationError]:
    """
    Validate a tool call's arguments against the tool's JSON schema.

    Checks:
    1. Tool name exists in the schema list
    2. All required parameters are present
    3. No unknown parameters are provided
    4. Enum values are valid
    5. Integer values respect min/max constraints
    6. String parameters are actually strings

    Args:
        tool_name: Name of the tool being called
        arguments: Arguments provided by the model
        tool_schemas: List of tool definitions (OpenAI format)

    Returns:
        List of ValidationError objects. Empty list means valid.
    """
    errors: list[ValidationError] = []

    # TODO: Step 1 - Find the tool schema by name
    # If not found, return an error with field="tool_name"
    #
    #   schema = None
    #   for tool in tool_schemas:
    #       func_def = tool.get("function", tool)
    #       if func_def.get("name") == tool_name:
    #           schema = func_def
    #           break
    #   if not schema:
    #       return [ValidationError(field="tool_name", message=f"Unknown tool: {tool_name}")]

    # TODO: Step 2 - Check required parameters
    # For each required param not in arguments, add a ValidationError
    #
    #   params = schema.get("parameters", {})
    #   properties = params.get("properties", {})
    #   for req in params.get("required", []):
    #       if req not in arguments:
    #           errors.append(ValidationError(field=req, message=f"Missing required: '{req}'"))

    # TODO: Step 3 - Check for unknown parameters
    # For each argument not in properties, add a ValidationError
    #
    #   for key in arguments:
    #       if key not in properties:
    #           errors.append(ValidationError(field=key, message=f"Unknown parameter: '{key}'"))

    # TODO: Step 4 - Validate enum values
    # If a property has an "enum" and the value isn't in it, add error
    #
    #   for key, value in arguments.items():
    #       if key not in properties:
    #           continue
    #       prop = properties[key]
    #       if "enum" in prop and value not in prop["enum"]:
    #           errors.append(ValidationError(field=key, message=f"Invalid enum value: '{value}'"))

    # TODO: Step 5 - Validate integer constraints
    # Check "minimum" and "maximum" for integer/number types
    #
    #       if "minimum" in prop and isinstance(value, (int, float)):
    #           if value < prop["minimum"]:
    #               errors.append(ValidationError(field=key, message=f"Below minimum {prop['minimum']}"))
    #       if "maximum" in prop and isinstance(value, (int, float)):
    #           if value > prop["maximum"]:
    #               errors.append(ValidationError(field=key, message=f"Above maximum {prop['maximum']}"))

    # TODO: Step 6 - Validate string types
    # If type is "string" and value isn't a string, add error
    #
    #       if prop.get("type") == "string" and not isinstance(value, str):
    #           errors.append(ValidationError(field=key, message=f"Expected string, got {type(value).__name__}"))

    return errors


# ---------------------------------------------------------------------------
# Exercise 6: Implement a Simple Orchestrator
#
# READ FIRST:
#   03-advanced-agent-systems.md
#     -> "## Multi-Agent Architectures"
#        -> "### Architecture 1: Supervisor / Orchestrator" (diagram + when to use)
#        -> "### Architecture Comparison" (single vs supervisor vs peer)
#   02-agent-patterns-and-memory.md
#     -> "## The Core Agent Loop" (the loop the specialist will run)
#
# ALSO SEE:
#   examples.py
#     -> "Example 7: Simple Multi-Agent Pattern (Orchestrator + Specialists)"
#        - OrchestratorAgent.route()          (classifies intent, delegates)
#        - OrchestratorAgent._build_routing_prompt() (how routing decisions work)
#        - AgentConfig / specialists dict     (specialist configuration)
#
# Build an orchestrator that classifies intent and delegates to specialists.
# ---------------------------------------------------------------------------

@dataclass
class SpecialistConfig:
    """Configuration for a specialist agent."""
    name: str
    description: str
    keywords: list[str]  # Simple keyword matching for routing
    system_prompt: str
    tools: list[dict]


def classify_intent(
    message: str,
    specialists: list[SpecialistConfig],
) -> str:
    """
    Classify the user's message to determine which specialist should handle it.

    Simple implementation using keyword matching.
    In production, you'd use an LLM for classification.

    Args:
        message: The user's message
        specialists: Available specialist configurations

    Returns:
        Name of the specialist that should handle the request.
        If no match, return the first specialist's name as default.
    """
    # TODO: Implement keyword-based intent classification
    #
    # Step-by-step:
    #   msg_lower = message.lower()
    #   best_name = specialists[0].name      # default to first
    #   best_count = 0
    #
    #   for spec in specialists:
    #       count = sum(1 for kw in spec.keywords if kw.lower() in msg_lower)
    #       if count > best_count:
    #           best_count = count
    #           best_name = spec.name
    #
    #   return best_name

    pass


def orchestrator(
    message: str,
    specialists: list[SpecialistConfig],
    llm_responses: dict[str, list[LLMResponse]],
) -> tuple[str, str]:
    """
    Orchestrator that routes to the right specialist and runs their agent loop.

    Args:
        message: User's message
        specialists: Available specialists
        llm_responses: Map of specialist name -> their scripted LLM responses

    Returns:
        Tuple of (specialist_name, final_response)
    """
    # TODO: Implement the orchestrator
    #
    # Step-by-step:
    #   # Step 1 - Classify intent
    #   specialist_name = classify_intent(message, specialists)
    #
    #   # Step 2 - Find the specialist config
    #   spec = next(s for s in specialists if s.name == specialist_name)
    #
    #   # Step 3 - Get the specialist's scripted LLM responses
    #   responses = llm_responses.get(specialist_name, [])
    #
    #   # Step 4 - Run agent_loop with the specialist's tools and responses
    #   response, _ = agent_loop(
    #       llm_responses=responses,
    #       tools=spec.tools,
    #       initial_message=message,
    #   )
    #
    #   return (specialist_name, response)

    pass


# ====================================================================
# TESTS — Run with: python exercises.py
# ====================================================================

def test_exercise_1_agent_loop():
    """Test the agent loop with a two-step tool interaction."""
    responses = [
        # Step 1: Model wants to call get_weather
        LLMResponse(
            content="Let me check the weather.",
            tool_calls=[ToolCall(id="call_1", name="get_weather", arguments={"city": "Tokyo"})]
        ),
        # Step 2: Model has enough info, responds with text
        LLMResponse(content="It's 22 degrees and sunny in Tokyo!"),
    ]

    result, messages = agent_loop(responses, [], "What's the weather in Tokyo?")

    assert result == "It's 22 degrees and sunny in Tokyo!", f"Expected final text, got: {result}"
    assert len(messages) >= 4, f"Expected at least 4 messages, got {len(messages)}"
    # system, user, assistant (with tool call), tool result, assistant (final)
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    print("Exercise 1: PASSED")


def test_exercise_1_max_iterations():
    """Test that the agent loop respects max iterations."""
    # All responses have tool calls -- should hit max iterations
    responses = [
        LLMResponse(
            content="Checking...",
            tool_calls=[ToolCall(id=f"call_{i}", name="get_weather", arguments={"city": "Tokyo"})]
        )
        for i in range(20)
    ]

    result, messages = agent_loop(responses, [], "Weather?", max_iterations=3)
    assert result == "Max iterations reached.", f"Expected max iterations message, got: {result}"
    print("Exercise 1 (max iterations): PASSED")


def test_exercise_2_react():
    """Test the ReAct pattern implementation."""
    responses = [
        # Step 1: Think, then search
        LLMResponse(
            content="I need to find the weather in Tokyo.",
            tool_calls=[ToolCall(id="call_1", name="get_weather", arguments={"city": "Tokyo"})]
        ),
        # Step 2: Have enough info, provide answer
        LLMResponse(content="The weather in Tokyo is 22 degrees and sunny."),
    ]

    answer, trace = react_agent(responses)

    assert answer == "The weather in Tokyo is 22 degrees and sunny."
    assert len(trace) == 2, f"Expected 2 steps, got {len(trace)}"
    assert trace[0].thought == "I need to find the weather in Tokyo."
    assert trace[0].action == "get_weather"
    assert trace[0].observation is not None
    assert trace[1].action is None  # Final answer, no action
    print("Exercise 2: PASSED")


def test_exercise_3_tool_schemas():
    """Test that tool schemas are well-formed."""
    tools = create_customer_service_tools()

    assert len(tools) == 3, f"Expected 3 tools, got {len(tools)}"

    names = {t["function"]["name"] for t in tools}
    assert "search_knowledge_base" in names
    assert "create_ticket" in names
    assert "transfer_to_human" in names

    # Check search_knowledge_base has required query parameter
    search_tool = next(t for t in tools if t["function"]["name"] == "search_knowledge_base")
    params = search_tool["function"]["parameters"]
    assert "query" in params.get("required", []), "query should be required"
    assert "query" in params["properties"]

    # Check create_ticket has required fields
    ticket_tool = next(t for t in tools if t["function"]["name"] == "create_ticket")
    params = ticket_tool["function"]["parameters"]
    assert "title" in params.get("required", [])
    assert "priority" in params.get("required", [])
    assert "enum" in params["properties"]["priority"], "priority should be an enum"

    # Check transfer_to_human
    transfer_tool = next(t for t in tools if t["function"]["name"] == "transfer_to_human")
    params = transfer_tool["function"]["parameters"]
    assert "reason" in params.get("required", [])
    assert "department" in params.get("required", [])

    print("Exercise 3: PASSED")


def test_exercise_4_memory():
    """Test sliding window memory."""
    memory = SlidingWindowMemory(window_size=3)

    # Add a system message
    memory.add_message(Message(role="system", content="You are helpful."))

    # Add 6 user/assistant messages
    for i in range(6):
        role = "user" if i % 2 == 0 else "assistant"
        memory.add_message(Message(role=role, content=f"Message {i}"))

    context = memory.get_context()

    # Should have: system message + last 3 non-system messages
    non_system_context = [m for m in context if m.role != "system"]
    assert len(non_system_context) == 3, f"Expected 3 non-system messages, got {len(non_system_context)}"
    assert non_system_context[0].content == "Message 3"
    assert non_system_context[1].content == "Message 4"
    assert non_system_context[2].content == "Message 5"

    # Test summarization trigger
    assert memory.should_summarize(), "Should need summarization (6 > 2*3)"

    # Test summary application
    memory.apply_summary("User discussed messages 0-2.")
    assert memory.summary == "User discussed messages 0-2."

    context_after = memory.get_context()
    # Should now include the summary as a system message
    system_msgs = [m for m in context_after if m.role == "system"]
    assert any("summary" in m.content.lower() or "messages 0-2" in m.content for m in system_msgs), \
        "Summary should appear in system messages"

    print("Exercise 4: PASSED")


def test_exercise_5_validation():
    """Test tool call validation."""
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "search_orders",
                "description": "Search orders",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "shipped", "delivered"]
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    # Valid call
    errors = validate_tool_call("search_orders", {"query": "laptop", "limit": 10}, schemas)
    assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    # Unknown tool
    errors = validate_tool_call("unknown_tool", {}, schemas)
    assert len(errors) == 1
    assert errors[0].field == "tool_name"

    # Missing required parameter
    errors = validate_tool_call("search_orders", {"limit": 5}, schemas)
    assert any(e.field == "query" for e in errors), "Should flag missing 'query'"

    # Invalid enum value
    errors = validate_tool_call("search_orders", {"query": "test", "status": "cancelled"}, schemas)
    assert any(e.field == "status" for e in errors), "Should flag invalid enum value"

    # Out of range integer
    errors = validate_tool_call("search_orders", {"query": "test", "limit": 100}, schemas)
    assert any(e.field == "limit" for e in errors), "Should flag limit > 50"

    # Unknown parameter
    errors = validate_tool_call("search_orders", {"query": "test", "foo": "bar"}, schemas)
    assert any(e.field == "foo" for e in errors), "Should flag unknown param 'foo'"

    # Wrong type (integer instead of string)
    errors = validate_tool_call("search_orders", {"query": 123}, schemas)
    assert any(e.field == "query" for e in errors), "Should flag wrong type for 'query'"

    print("Exercise 5: PASSED")


def test_exercise_6_orchestrator():
    """Test intent classification and orchestrator routing."""
    specialists = [
        SpecialistConfig(
            name="order_agent",
            description="Handles order-related queries",
            keywords=["order", "shipping", "tracking", "delivery", "ORD-"],
            system_prompt="You handle orders.",
            tools=[],
        ),
        SpecialistConfig(
            name="product_agent",
            description="Handles product questions",
            keywords=["product", "feature", "spec", "price", "compare"],
            system_prompt="You answer product questions.",
            tools=[],
        ),
        SpecialistConfig(
            name="billing_agent",
            description="Handles billing issues",
            keywords=["bill", "charge", "refund", "payment", "invoice"],
            system_prompt="You handle billing.",
            tools=[],
        ),
    ]

    # Test classification
    assert classify_intent("Where is my order ORD-123?", specialists) == "order_agent"
    assert classify_intent("What are the product features?", specialists) == "product_agent"
    assert classify_intent("I need a refund on my last charge", specialists) == "billing_agent"
    assert classify_intent("Hello there", specialists) == "order_agent"  # Default to first

    # Test orchestrator routing
    llm_responses = {
        "order_agent": [
            LLMResponse(content="Your order ORD-123 is being shipped."),
        ],
    }

    specialist_name, response = orchestrator(
        "Where is my order ORD-123?",
        specialists,
        llm_responses,
    )

    assert specialist_name == "order_agent"
    assert "ORD-123" in response
    print("Exercise 6: PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("Module 04: Agents & Tool Use — Exercise Tests")
    print("=" * 60)
    print()

    tests = [
        ("Exercise 1: Agent Loop", test_exercise_1_agent_loop),
        ("Exercise 1b: Max Iterations", test_exercise_1_max_iterations),
        ("Exercise 2: ReAct Pattern", test_exercise_2_react),
        ("Exercise 3: Tool Schemas", test_exercise_3_tool_schemas),
        ("Exercise 4: Sliding Window Memory", test_exercise_4_memory),
        ("Exercise 5: Tool Call Validation", test_exercise_5_validation),
        ("Exercise 6: Orchestrator", test_exercise_6_orchestrator),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except (AssertionError, Exception) as e:
            print(f"{name}: FAILED - {e}")
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")

    if failed == 0:
        print("All exercises complete!")
    else:
        print("Keep working on the failed exercises.")
