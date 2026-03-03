"""
Module 08: Timed Interview Challenges

Exercises designed to simulate real interview conditions. Each exercise has:
- A time limit (what you would get in an actual interview)
- Clear requirements
- Hints (use only if stuck)
- A test function to verify your solution

Rules:
- No external dependencies. Standard library only.
- Read the full docstring before starting the timer.
- Prioritize working code over perfect code.
- Talk through your approach before coding (even if alone).

Scoring yourself:
- Finished within time, all tests pass: Strong hire
- Finished within time, most tests pass: Hire
- Finished over time, tests pass: Needs practice
- Could not finish: Study the golden examples in examples.py
"""

from __future__ import annotations

import json
import math
import time
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Shared types for exercises
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: str
    content: str


@dataclass
class Document:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Mock utilities (provided -- do not modify)
# ---------------------------------------------------------------------------

def mock_embed(text: str) -> list[float]:
    """Deterministic mock embedding based on character frequency.

    This produces vectors that have rough semantic similarity --
    texts with similar character distributions get similar vectors.
    Not a real embedding model, but good enough for testing pipelines.
    """
    vec = [0.0] * 26
    text_lower = text.lower()
    for char in text_lower:
        if 'a' <= char <= 'z':
            vec[ord(char) - ord('a')] += 1
    # Normalize
    magnitude = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / magnitude for v in vec]


def mock_llm(messages: list[Message], **kwargs) -> Message:
    """Mock LLM that returns the last user message reversed.
    For exercises that need an actual LLM, swap this with a real API call.
    """
    user_msgs = [m for m in messages if m.role == "user"]
    last = user_msgs[-1].content if user_msgs else ""
    return Message(role="assistant", content=f"Response to: {last[:100]}")


SAMPLE_DOCUMENTS = [
    Document(
        id="doc-refunds",
        text=(
            "Refund Policy: Customers may request a full refund within 30 days of purchase. "
            "Items must be returned in original packaging and unused condition. "
            "Digital products and gift cards are non-refundable. "
            "Refunds are processed to the original payment method within 5-7 business days. "
            "Shipping costs are non-refundable unless the return is due to our error."
        ),
        metadata={"category": "policy", "last_updated": "2025-01-15"},
    ),
    Document(
        id="doc-shipping",
        text=(
            "Shipping Information: We offer free standard shipping on all orders over $50. "
            "Standard shipping takes 5-7 business days. "
            "Express shipping is available for $12.99 and arrives in 2-3 business days. "
            "Next-day shipping is available for $24.99 in select areas. "
            "International shipping rates vary by destination and are calculated at checkout."
        ),
        metadata={"category": "shipping", "last_updated": "2025-02-01"},
    ),
    Document(
        id="doc-returns",
        text=(
            "Return Process: To initiate a return, log into your account and go to Order History. "
            "Select the order and click 'Return Items'. Print the prepaid shipping label. "
            "Pack the items securely and drop off at any authorized shipping location. "
            "You will receive a confirmation email once we receive and inspect the return. "
            "If approved, your refund will be processed within 5-7 business days."
        ),
        metadata={"category": "policy", "last_updated": "2025-01-20"},
    ),
    Document(
        id="doc-warranty",
        text=(
            "Warranty Coverage: All electronics come with a 1-year manufacturer warranty. "
            "Warranty covers defects in materials and workmanship under normal use. "
            "Warranty does not cover damage from misuse, accidents, or unauthorized modifications. "
            "To file a warranty claim, contact support with your order number and description of the issue. "
            "Replacement products are shipped within 3-5 business days after claim approval."
        ),
        metadata={"category": "warranty", "last_updated": "2024-11-10"},
    ),
    Document(
        id="doc-account",
        text=(
            "Account Management: You can update your email, password, and shipping address "
            "from the Account Settings page. Two-factor authentication is available and recommended. "
            "To delete your account, contact support. Account deletion is permanent and cannot be undone. "
            "Order history is retained for 7 years for tax and compliance purposes even after deletion."
        ),
        metadata={"category": "account", "last_updated": "2025-01-05"},
    ),
]


# ===========================================================================
# Exercise 1: Build a Basic RAG Pipeline
# Time limit: 15 minutes
#
# READ FIRST:
#   01-interview-fundamentals-and-reference.md
#     -> "### RAG" section — walk-through of a RAG pipeline architecture
#        (ingestion: parse -> chunk -> embed -> store; query: embed query
#        -> similarity search -> top-K -> assemble prompt -> generate).
#     -> "### RAG" in 30-Second Answers — chunking, hybrid search, reranking.
#
# ALSO SEE:
#   examples.py
#     -> Example 1 "RAG Pipeline from Scratch" — SimpleRAGPipeline with
#        chunk_text() (overlap logic), cosine_similarity() (dot/norm formula),
#        ingest() and retrieve() methods showing the full flow.
#
# ===========================================================================

def exercise_1_rag_pipeline():
    """BUILD A RAG PIPELINE

    Time limit: 15 minutes

    Requirements:
    1. Implement a function that takes a list of Documents and a query string
    2. Chunk each document into pieces of roughly 200 characters with 50-char overlap
    3. Embed all chunks using the provided mock_embed function
    4. For a given query, embed it and find the top-K most similar chunks (cosine similarity)
    5. Return the top-K chunks as context strings

    Implement these functions:
        chunk_documents(docs, chunk_size=200, overlap=50) -> list of (doc_id, chunk_text)
        cosine_similarity(vec_a, vec_b) -> float
        rag_retrieve(docs, query, embed_fn, top_k=3) -> list of str

    Hints:
    - Cosine similarity = dot(a,b) / (|a| * |b|)
      Step-by-step:
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        return dot_product / (norm_a * norm_b)  # handle zero norms
    - Chunk by slicing text[start:start+chunk_size], advancing by (chunk_size - overlap):
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start:start+chunk_size].strip())
            start += chunk_size - overlap
    - rag_retrieve pattern:
        1. chunks = chunk_documents(docs)
        2. embedded_chunks = [(doc_id, text, embed_fn(text)) for doc_id, text in chunks]
        3. query_vec = embed_fn(query)
        4. scored = [(text, cosine_similarity(query_vec, emb)) for _, text, emb in embedded_chunks]
        5. scored.sort(key=lambda x: x[1], reverse=True)
        6. return [text for text, _ in scored[:top_k]]
    """

    # YOUR CODE HERE
    def chunk_documents(
        docs: list[Document], chunk_size: int = 200, overlap: int = 50,
    ) -> list[tuple[str, str]]:
        raise NotImplementedError("Implement chunk_documents")

    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        raise NotImplementedError("Implement cosine_similarity")

    def rag_retrieve(
        docs: list[Document],
        query: str,
        embed_fn: Callable[[str], list[float]] = mock_embed,
        top_k: int = 3,
    ) -> list[str]:
        raise NotImplementedError("Implement rag_retrieve")

    return chunk_documents, cosine_similarity, rag_retrieve


# ===========================================================================
# Exercise 2: Implement an Agent Loop
# Time limit: 15 minutes
#
# READ FIRST:
#   01-interview-fundamentals-and-reference.md
#     -> "### Agents and Tool Use" — how function calling works (schema ->
#        model outputs structured request -> your code executes -> return
#        result), agent loop design, key considerations (error handling,
#        max iterations, guardrails), and the ReAct pattern.
#
# ALSO SEE:
#   examples.py
#     -> Example 2 "Agent Loop with Tool Execution" — AgentLoop class with
#        run() method showing the while loop pattern, _execute_tool() with
#        error handling (unknown tool, TypeError, generic Exception), and
#        the max_iterations guard with summary request on exhaust.
#
# ===========================================================================

def exercise_2_agent_loop():
    """IMPLEMENT AN AGENT LOOP

    Time limit: 15 minutes

    Requirements:
    1. Build an agent loop that can use 3 tools to answer questions:
       - calculator(expression: str) -> str  (evaluates math expressions)
       - lookup(topic: str) -> str  (returns info about a topic)
       - weather(city: str) -> str  (returns weather for a city)
    2. The loop should:
       - Accept a user message
       - Call the LLM (use the provided mock)
       - If the LLM response contains a tool call (JSON with "tool" and "args" keys),
         execute the tool and feed the result back
       - Repeat until the LLM returns a response without a tool call or max_iterations is reached
       - Return the final response string and a list of tool calls made

    The mock LLM for this exercise is provided below. It simulates
    an LLM that makes tool calls by returning JSON.

    Implement:
        run_agent(user_message: str, max_iterations: int = 5) -> tuple[str, list[dict]]

    Hints:
    - Core loop pattern:
        messages = [Message(role="user", content=user_message)]
        tool_calls_made = []
        for _ in range(max_iterations):
            response = agent_mock_llm(messages)
            messages.append(response)
            # Try to parse as tool call:
            try:
                parsed = json.loads(response.content)
                if "tool" in parsed and "args" in parsed:
                    tool_name = parsed["tool"]
                    tool_args = parsed["args"]
                    handler = tool_handlers.get(tool_name)
                    result = handler(**tool_args) if handler else "Unknown tool"
                    tool_calls_made.append({"tool": tool_name, "args": tool_args, "result": result})
                    messages.append(Message(role="tool", content=result))
                    continue
            except (json.JSONDecodeError, KeyError):
                pass  # Not a tool call — treat as final response
            return response.content, tool_calls_made
        return messages[-1].content, tool_calls_made
    """

    # Provided tools
    def calculator(expression: str) -> str:
        try:
            # Safe eval for basic math only
            allowed = set("0123456789+-*/.(). ")
            if all(c in allowed for c in expression):
                return str(eval(expression))
            return "Error: invalid expression"
        except Exception as e:
            return f"Error: {e}"

    def lookup(topic: str) -> str:
        data = {
            "python": "Python is a programming language created by Guido van Rossum in 1991.",
            "rag": "RAG stands for Retrieval-Augmented Generation, a technique that combines retrieval with LLM generation.",
            "transformer": "The Transformer architecture was introduced in 'Attention Is All You Need' (2017).",
        }
        return data.get(topic.lower(), f"No information found for: {topic}")

    def weather(city: str) -> str:
        data = {
            "tokyo": "Tokyo: 22C, sunny",
            "london": "London: 14C, cloudy",
            "new york": "New York: 18C, partly cloudy",
        }
        return data.get(city.lower(), f"Weather data not available for: {city}")

    tool_handlers = {"calculator": calculator, "lookup": lookup, "weather": weather}

    # Mock LLM that simulates tool-calling behavior
    call_count = {"n": 0}

    def agent_mock_llm(messages: list[Message], **kwargs) -> Message:
        """Simulates an LLM that uses tools.

        On first call: returns a tool call if the query seems to need one.
        On subsequent calls (after tool results): returns a text answer.
        """
        call_count["n"] += 1
        last_msg = messages[-1].content.lower()

        # If last message looks like a tool result, synthesize an answer
        if messages[-1].role == "tool" or "result:" in last_msg:
            return Message(
                role="assistant",
                content=f"Based on the tool result, here is your answer: {messages[-1].content}",
            )

        # Otherwise, decide which tool to call based on the query
        user_msgs = [m.content.lower() for m in messages if m.role == "user"]
        query = user_msgs[-1] if user_msgs else ""

        if "weather" in query:
            city = "tokyo"
            for c in ["tokyo", "london", "new york"]:
                if c in query:
                    city = c
            return Message(
                role="assistant",
                content=json.dumps({"tool": "weather", "args": {"city": city}}),
            )
        elif "calculat" in query or "math" in query or any(c.isdigit() for c in query):
            return Message(
                role="assistant",
                content=json.dumps({"tool": "calculator", "args": {"expression": "42 * 3"}}),
            )
        elif "what is" in query or "tell me about" in query:
            topic = query.split("about")[-1].strip() if "about" in query else "python"
            return Message(
                role="assistant",
                content=json.dumps({"tool": "lookup", "args": {"topic": topic}}),
            )
        else:
            return Message(role="assistant", content=f"I can help with that: {query}")

    # YOUR CODE HERE
    def run_agent(
        user_message: str, max_iterations: int = 5,
    ) -> tuple[str, list[dict]]:
        raise NotImplementedError("Implement run_agent")

    return run_agent, tool_handlers, agent_mock_llm


# ===========================================================================
# Exercise 3: Design and Implement an Eval Suite
# Time limit: 20 minutes
#
# READ FIRST:
#   01-interview-fundamentals-and-reference.md
#     -> "### Production and Deployment" — "How do you evaluate?" in the
#        30-Second Answers (offline test set, LLM-as-judge, user feedback).
#     -> "### Prompt Engineering" — "How do you systematically optimize
#        prompts?" (eval-driven development, test sets of 20-50 cases,
#        baseline-then-iterate approach).
#   02-system-design-and-scenarios.md
#     -> "STEP 5: EVALUATION" in the System Design Framework — offline
#        evals, online metrics, and feedback loops.
#
# ALSO SEE:
#   examples.py
#     -> Example 3 "Eval Pipeline with LLM-as-Judge" — EvalPipeline class
#        with JUDGE_PROMPT template (score 0-1 with JSON output),
#        _run_single() running the system under test then the judge,
#        run() aggregating by category into an EvalReport.
#
# ===========================================================================

def exercise_3_eval_suite():
    """DESIGN AN EVAL SUITE FOR A SUMMARIZATION SYSTEM

    Time limit: 20 minutes

    Requirements:
    1. Define at least 5 test cases for a text summarization system.
       Each case: (input_text, reference_summary, category)
    2. Implement three scoring functions:
       - length_score(summary, reference) -> float
         Score based on how close the summary length is to the reference length (0-1)
       - keyword_score(summary, reference) -> float
         Score based on what fraction of important keywords from the reference
         appear in the summary (0-1)
       - llm_judge_score(summary, reference, judge_fn) -> tuple[float, str]
         Use an LLM to score the summary (returns score and reasoning)
    3. Implement a run_eval function that:
       - Takes a summarization function and test cases
       - Runs all test cases
       - Returns aggregate results: total, passed (score > 0.6), average score,
         and per-category breakdown

    Implement:
        get_test_cases() -> list of (input_text, reference_summary, category)
        length_score(summary: str, reference: str) -> float
        keyword_score(summary: str, reference: str) -> float
        llm_judge_score(summary: str, reference: str, judge_fn) -> tuple[float, str]
        run_eval(summarize_fn, test_cases, judge_fn) -> dict

    Hints:
    - length_score formula:
        return max(0.0, 1.0 - abs(len(summary) - len(reference)) / max(len(reference), 1))
    - keyword_score step-by-step:
        ref_keywords = {w.lower() for w in reference.split() if len(w) > 4}
        if not ref_keywords: return 1.0
        summary_lower = summary.lower()
        found = sum(1 for kw in ref_keywords if kw in summary_lower)
        return found / len(ref_keywords)
    - llm_judge_score pattern:
        prompt = f"Score this summary 0-1.\\nReference: {reference}\\nSummary: {summary}\\n"
                 f"Respond JSON: {{\"score\": 0.0, \"reasoning\": \"...\"}}"
        response = judge_fn([Message(role="user", content=prompt)])
        parsed = json.loads(response.content)  # try/except for safety
        return (parsed.get("score", 0.0), parsed.get("reasoning", ""))
    - run_eval aggregation:
        For each test case: generate summary, compute scores, track per-category.
        Return {"total": N, "passed": count(score>0.6), "average_score": mean,
                "by_category": {cat: {"total": ..., "passed": ..., "avg": ...}}}
    """

    # YOUR CODE HERE
    def get_test_cases() -> list[tuple[str, str, str]]:
        raise NotImplementedError("Define at least 5 test cases")

    def length_score(summary: str, reference: str) -> float:
        raise NotImplementedError("Implement length_score")

    def keyword_score(summary: str, reference: str) -> float:
        raise NotImplementedError("Implement keyword_score")

    def llm_judge_score(
        summary: str, reference: str,
        judge_fn: Callable[[list[Message]], Message] = mock_llm,
    ) -> tuple[float, str]:
        raise NotImplementedError("Implement llm_judge_score")

    def run_eval(
        summarize_fn: Callable[[str], str],
        test_cases: list[tuple[str, str, str]],
        judge_fn: Callable[[list[Message]], Message] = mock_llm,
    ) -> dict:
        raise NotImplementedError("Implement run_eval")

    return get_test_cases, length_score, keyword_score, llm_judge_score, run_eval


# ===========================================================================
# Exercise 4: Debug a Broken Prompt Chain
# Time limit: 10 minutes
#
# READ FIRST:
#   01-interview-fundamentals-and-reference.md
#     -> "### Prompt Engineering" — prompt chaining (breaking complex tasks
#        into focused steps), structured output (JSON), and the importance
#        of correct message roles (system vs user vs assistant).
#     -> "## Red Flags and Anti-Patterns" -> "### Prompt Engineering
#        Anti-Patterns" — monolithic prompts, not parsing output.
#
# ALSO SEE:
#   examples.py
#     -> Example 1 "RAG Pipeline from Scratch" — SimpleRAGPipeline.query()
#        shows a two-step chain: retrieve context, then generate with
#        system + user messages in the correct roles.
#     -> Example 3 "Eval Pipeline" — _run_single() shows JSON parsing
#        of LLM output with try/except and fallback handling.
#
# ===========================================================================

def exercise_4_debug_prompt_chain():
    """DEBUG A BROKEN PROMPT CHAIN

    Time limit: 10 minutes

    The following code implements a two-step prompt chain:
    1. Extract key entities from text
    2. Generate a summary focusing on those entities

    There are 5 bugs. Find and fix them all.

    Bugs are in the logic, not syntax -- the code runs but produces wrong results.

    After fixing, the chain should:
    - Step 1: Extract entities from the input text
    - Step 2: Generate a summary that mentions the extracted entities
    - Return a dict with 'entities' (list) and 'summary' (str)

    Hints -- the 5 bugs and how to fix them:
    1. BUG 1: System instruction uses role="user" instead of role="system".
       Fix: Change to Message(role="system", content="Extract key entities...")
    2. BUG 2: The input text is sent as role="assistant" instead of role="user".
       Fix: Change to Message(role="user", content=text)
    3. BUG 3: The JSON response is not parsed — entities is a raw string.
       Fix: entities = json.loads(extraction_response.content).get("entities", [])
    4. BUG 4: Step 2 passes entities as the user content instead of original text.
       Fix: Message(role="user", content=text)  — pass the original text
    5. BUG 5: Returns {"result": ...} instead of {"entities": ..., "summary": ...}.
       Fix: return {"entities": entities, "summary": summary_response.content}
    """

    def broken_prompt_chain(
        text: str,
        complete_fn: Callable[[list[Message]], Message],
    ) -> dict[str, Any]:
        # Step 1: Extract entities
        # BUG 1: System message has wrong role
        extraction_messages = [
            Message(role="user", content="Extract key entities (people, places, organizations) "
                    "from the text. Return as JSON: {\"entities\": [\"entity1\", ...]}"),
            # BUG 2: The text input is missing from the messages
            Message(role="assistant", content=text),
        ]

        extraction_response = complete_fn(extraction_messages)

        # BUG 3: Not parsing the JSON response
        entities = extraction_response.content

        # Step 2: Generate summary
        summary_messages = [
            Message(role="system", content="Write a concise summary of the following text. "
                    "Make sure to mention these entities: " + str(entities)),
            # BUG 4: Passing entities instead of original text
            Message(role="user", content=str(entities)),
        ]

        summary_response = complete_fn(summary_messages)

        # BUG 5: Returning wrong structure
        return {"result": summary_response.content}

    return broken_prompt_chain


# ===========================================================================
# Exercise 5: Code Review — Find Problems in Production LLM Integration
# Time limit: 10 minutes
#
# READ FIRST:
#   01-interview-fundamentals-and-reference.md
#     -> "## Red Flags and Anti-Patterns" — all sections: architecture,
#        prompt engineering, RAG, agent, and production anti-patterns.
#     -> "### Prompt Engineering" -> prompt injection defense (delimiters,
#        instruction hierarchy, input validation).
#     -> "### Production and Deployment" -> observability, cost optimization,
#        reliability/failover answers.
#
# ALSO SEE:
#   examples.py
#     -> Example 5 "Model Router with Cost Tracking" — shows proper
#        cost estimation, usage logging, and budget management.
#     -> Example 2 "Agent Loop" — _execute_tool() demonstrates error
#        handling patterns (try/except with structured error returns).
#
# ===========================================================================

def exercise_5_code_review():
    """CODE REVIEW: FIND PROBLEMS IN A PRODUCTION LLM INTEGRATION

    Time limit: 10 minutes

    The following code is a "production" LLM-powered classification endpoint.
    There are at least 8 problems (bugs, anti-patterns, and security issues).

    Find as many as you can. Write your answers as a list of strings,
    each describing one problem and how you would fix it.

    Categories of problems to look for:
    - Security vulnerabilities
    - Missing error handling
    - Performance issues
    - Cost concerns
    - Observability gaps
    - Correctness bugs

    Specific areas to examine:
    1. Prompt: Is the ticket text safely delimited from instructions?
    2. Messages: Should there be a system message separating instructions from data?
    3. Error handling: What if the LLM call throws an exception (timeout, rate limit)?
    4. Output parsing: Is the raw string cleaned/validated against known categories?
    5. Validation: Does the result get checked against the allowed category list?
    6. Missing entirely: No retry logic, no timeout, no cost tracking
    7. Injection: Raw user content is interpolated into the prompt (f-string)
    8. Observability: No logging of request/response, latency, model, or cost
    """

    # -- START of code to review --

    def classify_ticket(
        ticket_text: str,
        llm_fn: Callable[[list[Message]], Message],
    ) -> str:
        """Classify a support ticket into a category."""

        # Problem 1: ??? (hint: look at the prompt)
        prompt = f"""Classify this support ticket into exactly one category:
        billing, technical, shipping, account, other.

        Ticket: {ticket_text}

        Category:"""

        # Problem 2: ??? (hint: look at the message structure)
        messages = [Message(role="user", content=prompt)]

        # Problem 3: ??? (hint: what if this fails?)
        response = llm_fn(messages)

        # Problem 4: ??? (hint: look at how the result is used)
        category = response.content

        # Problem 5: ??? (hint: what categories are valid?)
        return category

    # Problem 6: ??? (hint: what is missing from this function entirely?)
    # Problem 7: ??? (hint: think about injection)
    # Problem 8: ??? (hint: think about observability)

    # -- END of code to review --

    # YOUR ANSWERS HERE:
    def get_review_findings() -> list[str]:
        """Return a list of problems found and suggested fixes."""
        raise NotImplementedError(
            "Return a list of strings, each describing a problem and fix"
        )

    return classify_ticket, get_review_findings


# ===========================================================================
# Exercise 6: Build a Streaming Chat Endpoint with Conversation Memory
# Time limit: 20 minutes
#
# READ FIRST:
#   01-interview-fundamentals-and-reference.md
#     -> "### Production and Deployment" -> "How do you handle streaming?"
#        (SSE, buffer for JSON, tool calls, backpressure).
#   02-system-design-and-scenarios.md
#     -> "## Design 1: RAG-Powered Customer Support System" — conversation
#        memory management section with summarization strategy.
#
# ALSO SEE:
#   examples.py
#     -> Example 6 "Conversation Memory with Summarization" —
#        ConversationMemory class with add_turn(), _update_summary(),
#        get_messages() (always keeps system prompt, trims to budget),
#        and get_stats().
#     -> Example 4 "Streaming Response Handler" — StreamingHandler with
#        process_chunk(), text buffer assembly, and tool call reconstruction.
#
# ===========================================================================

def exercise_6_streaming_chat():
    """BUILD A STREAMING CHAT WITH CONVERSATION MEMORY

    Time limit: 20 minutes

    Requirements:
    1. Implement a ConversationMemory class that:
       - Stores conversation turns (role, content)
       - Has a max_turns limit; when exceeded, drops the oldest non-system turns
       - Always keeps the system prompt
       - Returns messages in the correct format for an LLM call

    2. Implement a stream_response function that:
       - Takes a list of "stream chunks" (simulating a streaming API)
       - Yields each chunk to the caller (generator pattern)
       - After the stream completes, returns the full assembled text
       - Handles a stream that ends with an error chunk gracefully

    3. Implement a chat_turn function that ties it together:
       - Takes user input and a ConversationMemory
       - Adds the user message to memory
       - "Calls" the LLM (use mock) and streams the response
       - Adds the assistant response to memory
       - Returns the full response text

    Implement:
        class ConversationMemory:
            __init__(system_prompt, max_turns=20)
            add(role, content) -> None
            get_messages() -> list[Message]

        stream_response(chunks: list[str]) -> Generator[str, None, str]

        chat_turn(user_input: str, memory: ConversationMemory,
                  llm_fn, stream_chunks: list[str]) -> str

    Hints:
    - ConversationMemory pattern:
        def __init__(self, system_prompt, max_turns=20):
            self._system = system_prompt
            self._turns = []          # list of Message
            self._max_turns = max_turns

        def add(self, role, content):
            self._turns.append(Message(role=role, content=content))
            while len(self._turns) > self._max_turns:
                self._turns.pop(0)    # drop oldest non-system turn

        def get_messages(self):
            return [Message(role="system", content=self._system)] + self._turns

    - stream_response pattern (generator with return value):
        def stream_response(chunks):
            buffer = []
            for chunk in chunks:
                if chunk.startswith("ERROR:"):
                    return "".join(buffer)  # stop on error
                if chunk:  # skip empty strings
                    buffer.append(chunk)
                    yield chunk
            return "".join(buffer)

    - chat_turn ties it together:
        memory.add("user", user_input)
        # Use stream_chunks if provided, otherwise call LLM:
        if stream_chunks:
            gen = stream_response(stream_chunks)
            full = ""
            try:
                while True: full_chunk = next(gen)
            except StopIteration as e: full = e.value
            # Or simply: for _ in gen: pass; full = ...
        response_text = full or "..."
        memory.add("assistant", response_text)
        return response_text
    """

    # YOUR CODE HERE
    class ConversationMemory:
        def __init__(self, system_prompt: str, max_turns: int = 20):
            raise NotImplementedError

        def add(self, role: str, content: str) -> None:
            raise NotImplementedError

        def get_messages(self) -> list[Message]:
            raise NotImplementedError

    def stream_response(chunks: list[str]):
        raise NotImplementedError

    def chat_turn(
        user_input: str,
        memory: ConversationMemory,
        llm_fn: Callable = mock_llm,
        stream_chunks: list[str] | None = None,
    ) -> str:
        raise NotImplementedError

    return ConversationMemory, stream_response, chat_turn


# ===========================================================================
# Test Functions
# ===========================================================================

def test_exercise_1():
    """Test the RAG pipeline exercise."""
    print("Testing Exercise 1: RAG Pipeline")
    chunk_documents, cosine_similarity, rag_retrieve = exercise_1_rag_pipeline()

    # Test chunking
    chunks = chunk_documents(SAMPLE_DOCUMENTS[:2], chunk_size=200, overlap=50)
    assert len(chunks) > 2, f"Expected more than 2 chunks, got {len(chunks)}"
    assert all(isinstance(c, tuple) and len(c) == 2 for c in chunks), \
        "Chunks should be (doc_id, chunk_text) tuples"
    print(f"  Chunking: {len(chunks)} chunks created")

    # Test cosine similarity
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(v1, v2) - 1.0) < 0.01, "Identical vectors should have similarity 1.0"
    assert abs(cosine_similarity(v1, v3)) < 0.01, "Orthogonal vectors should have similarity ~0.0"
    print("  Cosine similarity: correct")

    # Test retrieval
    results = rag_retrieve(SAMPLE_DOCUMENTS, "refund policy returns", mock_embed, top_k=2)
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    assert all(isinstance(r, str) for r in results), "Results should be strings"
    print(f"  Retrieval: {len(results)} results returned")

    print("  PASSED\n")


def test_exercise_2():
    """Test the agent loop exercise."""
    print("Testing Exercise 2: Agent Loop")
    run_agent, tool_handlers, agent_mock_llm = exercise_2_agent_loop()

    # Test weather query
    response, tool_calls = run_agent("What is the weather in Tokyo?")
    assert isinstance(response, str) and len(response) > 0, "Should return a non-empty response"
    assert len(tool_calls) > 0, "Should have made at least one tool call"
    assert any(tc.get("tool") == "weather" for tc in tool_calls), \
        "Should have called the weather tool"
    print(f"  Weather query: '{response[:80]}...' ({len(tool_calls)} tool calls)")

    # Test query that does not need tools
    response2, tool_calls2 = run_agent("Hello, how are you?")
    assert isinstance(response2, str) and len(response2) > 0, "Should return a response"
    print(f"  Simple query: '{response2[:80]}...' ({len(tool_calls2)} tool calls)")

    print("  PASSED\n")


def test_exercise_3():
    """Test the eval suite exercise."""
    print("Testing Exercise 3: Eval Suite")
    get_test_cases, length_score, keyword_score, llm_judge_score, run_eval = exercise_3_eval_suite()

    # Test: should have at least 5 test cases
    cases = get_test_cases()
    assert len(cases) >= 5, f"Expected at least 5 test cases, got {len(cases)}"
    assert all(len(c) == 3 for c in cases), "Each case should be (input, reference, category)"
    print(f"  Test cases: {len(cases)} defined")

    # Test length_score
    score = length_score("short summary", "this is a reference summary of similar length")
    assert 0.0 <= score <= 1.0, f"Score should be 0-1, got {score}"
    perfect = length_score("exact", "exact")
    assert perfect == 1.0, f"Identical length should score 1.0, got {perfect}"
    print(f"  Length score: {score:.2f} (short vs long), {perfect:.2f} (identical)")

    # Test keyword_score
    ref = "The transformer architecture enables parallel processing"
    summary_good = "Transformers enable parallel processing of tokens"
    summary_bad = "The sky is blue today"
    good_score = keyword_score(summary_good, ref)
    bad_score = keyword_score(summary_bad, ref)
    assert good_score > bad_score, "Good summary should score higher than bad"
    print(f"  Keyword score: {good_score:.2f} (good) vs {bad_score:.2f} (bad)")

    # Test run_eval with a simple mock summarizer
    def mock_summarizer(text: str) -> str:
        words = text.split()
        return " ".join(words[:len(words) // 3]) + "..."

    report = run_eval(mock_summarizer, cases[:3])
    assert "total" in report and "passed" in report and "average_score" in report, \
        "Report should have total, passed, average_score"
    print(f"  Eval report: {report['passed']}/{report['total']} passed, "
          f"avg score: {report['average_score']:.2f}")

    print("  PASSED\n")


def test_exercise_4():
    """Test the debug exercise."""
    print("Testing Exercise 4: Debug Prompt Chain")
    broken_chain = exercise_4_debug_prompt_chain()

    # The mock LLM for this test returns entity-like JSON for extraction
    # and a summary string for the summary step
    call_number = {"n": 0}

    def mock_chain_llm(messages: list[Message], **kwargs) -> Message:
        call_number["n"] += 1
        if call_number["n"] == 1:
            # First call: entity extraction
            return Message(
                role="assistant",
                content='{"entities": ["Python", "Guido van Rossum", "Netherlands"]}',
            )
        else:
            # Second call: summary
            user_text = next((m.content for m in messages if m.role == "user"), "")
            return Message(
                role="assistant",
                content=f"Summary: Python was created by Guido van Rossum. Text length: {len(user_text)}",
            )

    call_number["n"] = 0
    result = broken_chain(
        "Python was created by Guido van Rossum in the Netherlands in 1991.",
        mock_chain_llm,
    )

    assert isinstance(result, dict), "Should return a dict"
    assert "entities" in result, f"Should have 'entities' key, got keys: {list(result.keys())}"
    assert "summary" in result, f"Should have 'summary' key, got keys: {list(result.keys())}"
    assert isinstance(result["entities"], list), "Entities should be a list"
    assert len(result["entities"]) > 0, "Should have extracted at least one entity"
    assert isinstance(result["summary"], str), "Summary should be a string"
    print(f"  Entities: {result['entities']}")
    print(f"  Summary: {result['summary'][:80]}...")
    print("  PASSED\n")


def test_exercise_5():
    """Test the code review exercise."""
    print("Testing Exercise 5: Code Review")
    classify_ticket, get_review_findings = exercise_5_code_review()

    findings = get_review_findings()
    assert isinstance(findings, list), "Should return a list of strings"
    assert len(findings) >= 6, f"Expected at least 6 findings, got {len(findings)}"
    assert all(isinstance(f, str) for f in findings), "Each finding should be a string"

    print(f"  Found {len(findings)} problems:")
    for i, finding in enumerate(findings, 1):
        print(f"    {i}. {finding[:100]}...")
    print("  PASSED\n")


def test_exercise_6():
    """Test the streaming chat exercise."""
    print("Testing Exercise 6: Streaming Chat")
    ConversationMemory, stream_response, chat_turn = exercise_6_streaming_chat()

    # Test ConversationMemory
    memory = ConversationMemory("You are a helpful assistant.", max_turns=4)
    memory.add("user", "Hello")
    memory.add("assistant", "Hi there!")
    msgs = memory.get_messages()
    assert msgs[0].role == "system", "First message should be system prompt"
    assert len(msgs) == 3, f"Expected 3 messages (system + 2 turns), got {len(msgs)}"

    # Test max_turns truncation
    for i in range(10):
        memory.add("user", f"Message {i}")
        memory.add("assistant", f"Response {i}")
    msgs = memory.get_messages()
    assert msgs[0].role == "system", "System prompt should always be present"
    # max_turns=4 means at most 4 non-system messages + system
    assert len(msgs) <= 5, f"Expected at most 5 messages (system + 4 turns), got {len(msgs)}"
    print(f"  Memory: {len(msgs)} messages after truncation")

    # Test stream_response
    chunks = ["Hello", " world", "!", ""]
    collected = []
    gen = stream_response(chunks)
    for chunk in gen:
        collected.append(chunk)
    assert "".join(collected) == "Hello world!", \
        f"Expected 'Hello world!', got '{''.join(collected)}'"
    print(f"  Streaming: assembled '{' '.join(collected)}'")

    # Test chat_turn
    fresh_memory = ConversationMemory("You are a helpful assistant.", max_turns=20)
    result = chat_turn(
        "What is Python?",
        fresh_memory,
        mock_llm,
        stream_chunks=["Python ", "is a ", "programming ", "language."],
    )
    assert isinstance(result, str), "Should return a string"
    assert len(result) > 0, "Should return non-empty response"
    final_msgs = fresh_memory.get_messages()
    assert any(m.role == "user" for m in final_msgs), "Memory should contain user message"
    assert any(m.role == "assistant" for m in final_msgs), "Memory should contain assistant response"
    print(f"  Chat turn: '{result[:60]}...'")

    print("  PASSED\n")


# ===========================================================================
# Run all tests
# ===========================================================================

def run_all_tests():
    """Run all exercise tests. Exercises that are not implemented will fail
    with NotImplementedError -- that is expected until you complete them."""

    exercises = [
        ("Exercise 1: RAG Pipeline (15 min)", test_exercise_1),
        ("Exercise 2: Agent Loop (15 min)", test_exercise_2),
        ("Exercise 3: Eval Suite (20 min)", test_exercise_3),
        ("Exercise 4: Debug Prompt Chain (10 min)", test_exercise_4),
        ("Exercise 5: Code Review (10 min)", test_exercise_5),
        ("Exercise 6: Streaming Chat (20 min)", test_exercise_6),
    ]

    results: list[tuple[str, str]] = []

    for name, test_fn in exercises:
        try:
            test_fn()
            results.append((name, "PASSED"))
        except NotImplementedError:
            results.append((name, "NOT IMPLEMENTED"))
            print(f"  {name}: Not yet implemented\n")
        except AssertionError as e:
            results.append((name, f"FAILED: {e}"))
            print(f"  {name}: FAILED - {e}\n")
        except Exception as e:
            results.append((name, f"ERROR: {e}"))
            print(f"  {name}: ERROR - {e}\n")

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for name, status in results:
        print(f"  {status:20s}  {name}")


if __name__ == "__main__":
    run_all_tests()
