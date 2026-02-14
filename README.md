# LLM Interview Prep

Study materials for professional-level LLM knowledge. Covers foundations, prompt engineering, RAG, agents, production concerns, and interview-specific prep.

All content is provider-agnostic. Python examples use generic interfaces (Protocols, dataclasses) that map to any provider (OpenAI, Anthropic, open-source, etc.). Studying these materials doubles as a way to sharpen modern Python skills — type hints, `dataclasses`, `async`/`await`, `Protocol`, and more.

---

## Study Order

### Day 1: Foundations & Core Skills (3-4 hours)

| # | File | Time | What You'll Learn |
|---|---|---|---|
| 1 | `01-foundations/concepts.md` | 45 min | How LLMs work — transformers, attention, tokenization, context windows, temperature |
| 2 | `01-foundations/key-terminology.md` | 20 min | Quick-reference glossary — skim now, refer back during study |
| 3 | `02-prompt-engineering/techniques.md` | 45 min | Core techniques — zero/few-shot, CoT, system prompts, output structuring |
| 4 | `02-prompt-engineering/patterns.md` | 30 min | Applied patterns — classification, extraction, summarization, code gen |
| 5 | `02-prompt-engineering/examples.py` | 45 min | Read and understand the Python implementations |

### Day 2: RAG & Agents (3-4 hours)

| # | File | Time | What You'll Learn |
|---|---|---|---|
| 6 | `03-rag-and-embeddings/concepts.md` | 40 min | Embeddings, vector similarity, chunking strategies, retrieval pipelines |
| 7 | `03-rag-and-embeddings/architecture.md` | 40 min | End-to-end RAG architecture, vector DBs, hybrid search, evaluation |
| 8 | `03-rag-and-embeddings/examples.py` | 40 min | Python RAG pipeline implementation |
| 9 | `04-agents-and-tool-use/concepts.md` | 30 min | Function calling, tool schemas, agent loops |
| 10 | `04-agents-and-tool-use/patterns.md` | 30 min | ReAct, orchestration, error handling, guardrails |
| 11 | `04-agents-and-tool-use/examples.py` | 40 min | Python agent implementation |

### Day 3: Production & Interview Prep (2-3 hours)

| # | File | Time | What You'll Learn |
|---|---|---|---|
| 12 | `05-production-concerns/guide.md` | 40 min | Streaming, caching, cost, evals, safety, observability |
| 13 | `05-production-concerns/examples.py` | 30 min | Production Python patterns |
| 14 | `06-interview-prep/questions.md` | 45 min | Likely questions with concise answers — practice speaking these aloud |
| 15 | `06-interview-prep/system-design.md` | 30 min | Framework for LLM system design questions |

---

## If You Only Have a Few Hours

Focus on these files in order:

1. **`01-foundations/concepts.md`** — Must be able to explain how LLMs work
2. **`02-prompt-engineering/techniques.md`** — Core practical skill
3. **`06-interview-prep/questions.md`** — Direct interview prep with concise answers
4. **`01-foundations/key-terminology.md`** — Quick glossary review

---

## Python Concepts Covered

The code examples double as a tour of modern Python patterns:

| Python Feature | Where It Appears |
|---|---|
| `dataclasses` | All examples — structured data without boilerplate |
| `Protocol` (structural subtyping) | Generic interfaces for LLM/embedding functions |
| Type hints (`list[str]`, `dict[str, Any]`, `X \| None`) | Throughout — modern 3.10+ syntax |
| `Literal` types | Constrained string unions (roles, categories) |
| `async` / `await` | All LLM calls, tool execution, pipelines |
| `AsyncIterator` | Streaming responses |
| Generic functions (`[T]`) | Retry wrapper with type preservation |
| Comprehensions & generators | Data transformation patterns |
| `OrderedDict` for LRU caching | Response cache implementation |
| `Callable` type aliases | Higher-order function patterns |

---

## File Structure

```
llm-prep/
├── README.md                          ← You are here
├── LICENSE                            # MIT License
├── CONTRIBUTING.md                    # How to contribute
├── CODE_OF_CONDUCT.md                 # Contributor Covenant
├── CHANGELOG.md                       # Version history
├── pyproject.toml                     # Project metadata & tool config
├── .editorconfig                      # Editor formatting rules
├── .github/
│   ├── workflows/lint.yml             # CI: ruff + mypy
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md              # Error report template
│   │   └── feature_request.md         # Content request template
│   └── PULL_REQUEST_TEMPLATE.md       # PR template
├── 01-foundations/
│   ├── concepts.md                    # How LLMs work (transformers, attention, etc.)
│   └── key-terminology.md             # Quick-reference glossary
├── 02-prompt-engineering/
│   ├── techniques.md                  # Core prompt engineering techniques
│   ├── patterns.md                    # Applied patterns (classification, extraction, etc.)
│   └── examples.py                    # Annotated Python examples
├── 03-rag-and-embeddings/
│   ├── concepts.md                    # Embeddings, vector search, chunking
│   ├── architecture.md                # RAG architecture, vector DBs, hybrid search
│   └── examples.py                    # Python RAG pipeline
├── 04-agents-and-tool-use/
│   ├── concepts.md                    # Function calling, tool schemas, agent loops
│   ├── patterns.md                    # ReAct, orchestration, guardrails
│   └── examples.py                    # Python agent implementation
├── 05-production-concerns/
│   ├── guide.md                       # Streaming, caching, cost, evals, safety
│   └── examples.py                    # Production Python patterns
└── 06-interview-prep/
    ├── questions.md                   # Interview questions with answers
    └── system-design.md               # LLM system design framework
```

---

## Tips for Studying

- **Read the markdown first, then the code.** The concepts inform the implementation.
- **Practice explaining out loud.** Interviews test communication, not just knowledge.
- **For system design questions,** use the framework in `06-interview-prep/system-design.md` — interviewers love structured thinking.
- **The Python examples are meant to be read, not run.** They demonstrate patterns and interfaces, not boilerplate apps. To make them runnable, plug in a provider SDK (e.g., `openai`, `anthropic`).

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
