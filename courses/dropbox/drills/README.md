# Dropbox CodeSignal Drills

Progressive coding drills modeled after reported Dropbox CodeSignal OA problems. Each drill is a class you implement level by level, with a self-check harness that validates your work.

**Primary language: Python** (recommended for CodeSignal OA speed).
TypeScript versions available for cross-training.

### Framework Note

Dropbox does **not** use Flask, Django, or FastAPI. Their Python backend is a
~3M-line monolith ("Metaserver") running on a custom proprietary framework,
currently being decomposed into gRPC microservices (project "Atlas"). Dash
specifically uses Python for RAG/AI pipelines, feature engineering (PySpark),
and orchestration — not traditional web framework route handlers. The Go layer
handles low-latency feature serving (~20ms). These drills intentionally test
**pure Python problem-solving** (data structures, algorithms, systems thinking)
rather than framework knowledge, which matches what the interview evaluates.

---

## Cosmo Simulation Guidelines

Dropbox **requires** you to use CodeSignal's AI assistant (Cosmo) during the OA. They monitor usage — not using it is a red flag. These drills are designed to help you practice the AI-assisted workflow.

### How to Simulate Cosmo

Use any AI assistant (Claude, Copilot, ChatGPT, Cursor) as your "fake Cosmo" during timed practice. The goal is to develop a natural AI-assisted coding rhythm.

### Rules for Practice Sessions

**DO use your AI assistant for:**
- Clarifying the problem spec ("What should happen if the file already exists?")
- Generating boilerplate (class skeleton, data structure initialization)
- Suggesting data structures ("What's the best structure for prefix search?")
- Catching edge cases ("What edge cases am I missing?")
- Debugging ("This test fails — what's wrong with my logic?")
- Verifying approach before coding ("Is a hash map the right choice here?")

**DO NOT use your AI assistant for:**
- Copying a complete solution wholesale without understanding it
- Skipping levels (ask for help on the current level, not "solve the whole thing")

**Practice prompts to use with your AI:**
1. "Here's the spec for Level 1. What data structures should I use?"
2. "I'm thinking of using a dict keyed by filename. Is there a better approach for the search method?"
3. "This test is failing: [paste test]. Here's my code: [paste code]. What's wrong?"
4. "What edge cases should I handle for the undo operation?"
5. "Can you generate the boilerplate for Level 3 methods?"
6. "I have 15 minutes left and 2 levels to go. Should I optimize Level 2 or move to Level 3?"

### Timed Practice Sessions

**OA simulation (60 min):**
1. Pick 1 drill you haven't done
2. Set a 60-minute timer
3. Open your AI assistant alongside your editor
4. Work through all 4 levels
5. Target: complete Levels 1-3, attempt Level 4
6. Run self-checks after each level

**Speed drill (30 min):**
1. Pick a drill you've done before
2. Set a 30-minute timer
3. Use AI aggressively for boilerplate
4. Target: all 4 levels

**No-AI drill (45 min):**
1. Pick any drill
2. No AI assistant — this simulates the onsite coding rounds (where AI is prohibited)
3. Target: Levels 1-3

---

## Drill Overview

| # | Class | Dropbox Context | Skills Tested |
|---|-------|----------------|---------------|
| 01 | **CloudStorage** | Directly reported CodeSignal OA problem | Hash maps, sorting, capacity, undo |
| 02 | **FileChunker** | Recruiter hint: file transfer techniques | Chunking, hashing, reassembly, dedup |
| 03 | **HitCounter** | Classic Dropbox interview problem | Sliding window, time-based data, top-K |
| 04 | **PermissionManager** | Dropbox connector permissions | Trees, inheritance, group resolution |
| 05 | **WebCrawler** | Classic Dropbox problem (single then multi-threaded) | BFS, dedup, domain filtering, concurrency |
| 06 | **SearchIndex** | Dash universal search | Inverted index, ranking, prefix search, multi-source |

## Level Structure

- **Level 1:** Core methods — get the basics right (10 min)
- **Level 2:** New methods that build on Level 1 (10 min)
- **Level 3:** Constraints/complexity that affect existing methods (10 min)
- **Level 4:** Advanced feature — the stretch goal (15 min)

## Run

```bash
# From courses/dropbox/drills/

# Python
make py1    # Cloud Storage
make py2    # File Chunker
make py3    # Hit Counter
make py4    # Permission Manager
make py5    # Web Crawler
make py6    # Search Index
make all-py # all Python drills

# TypeScript
make ts1    # Cloud Storage
make ts2    # File Chunker
make ts3    # Hit Counter
make ts4    # Permission Manager
make ts5    # Web Crawler
make ts6    # Search Index
make all-ts # all TypeScript drills

make all    # everything
```

## React Onsite Challenges

The CodeSignal drills above prepare you for the **OA** (with AI). For the **onsite coding rounds** (no AI), see [REACT_CHALLENGES.md](./REACT_CHALLENGES.md):

| Challenge | Interview | What You Build |
|-----------|-----------|----------------|
| 01 — File Search UI | Frontend (React/TS) | Debounced search, keyboard nav, source filtering, URL state |
| 02 — Chunked File Upload | Frontend (React/TS) | Drag-drop, chunked upload, progress, pause/resume |
| 03 — Streaming AI Answer | Frontend (React/TS) | Token-by-token streaming, citations, error recovery |
| 04 — Connector Settings | Frontend (React/TS) | Optimistic UI, connect/disconnect, drawer, focus trap |
| 05 — File Explorer | Full-Stack (React + Python) | Python API + React file tree |
| 06 — Activity Feed | Full-Stack (React + Python) | Python event store + React feed with polling |

**Practice environment:** `npm create vite@latest -- --template react-ts`

## Recommended Practice Schedule

| Day | Session | Drills | Mode |
|-----|---------|--------|------|
| 1 | Learn the format | Drill 01 (Cloud Storage) | Untimed, with AI |
| 2 | OA simulation #1 | Drill 02 (File Chunker) | 60 min, with AI |
| 3 | OA simulation #2 | Drill 03 (Hit Counter) | 60 min, with AI |
| 4 | Speed round | Drill 01 again | 30 min, with AI |
| 5 | OA simulation #3 | Drill 04 (Permission Manager) | 60 min, with AI |
| 6 | No-AI practice | Drill 05 (Web Crawler) | 45 min, no AI |
| 7 | Final simulation | Drill 06 (Search Index) | 60 min, with AI |

## Tips

- **Read the full spec before coding.** The levels build on each other — knowing what's coming helps you choose data structures.
- **Level 4 is the stretch goal.** In a real OA, completing Levels 1-3 cleanly is often enough to pass.
- **Use AI for the boring parts.** Let it write boilerplate, parse edge cases, and catch bugs. Save your brain for the logic.
- **Code quality matters.** Candidate reports suggest Dropbox evaluates structure and clarity beyond just passing tests.
- **Practice the Cosmo workflow.** Develop a rhythm: spec → AI discussion → code → test → fix → next level.
