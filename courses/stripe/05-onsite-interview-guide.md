# 05 — Stripe TSE Onsite Interview Guide

Your onsite has 4 interviews (~3h45m + breaks, ~5 hours total on Zoom):

| # | Interview | Duration | Type |
|---|-----------|----------|------|
| 1 | Programming Exercise | 1 hour | Paired coding — build from scratch |
| 2 | Integration Exercise | 1 hour | Code within existing system, HTTP/API work |
| 3 | Bug Squash | 1 hour | Debug a bug in an open-source project |
| 4 | User First & Curious / Experience & Goals | 45 min | Behavioral — user empathy, career fit |

All interviews are on the same Zoom link. Shadow interviewers may be present (normal — they observe, you interact with the primary interviewer only). AI tools are **strictly prohibited** (Copilot, TabNine, Gemini, AI search).

---

## What Stripe Evaluates (Across All Rounds)

- **Problem solving** — Can you understand the problem and devise a solution?
- **Design** — Is your code well-organized with clean interfaces?
- **Correctness** — Do you reason about correctness, use tests, handle edge/error cases?
- **Debugging** — Can you spot and fix bugs?
- **Language familiarity** — Is your code idiomatic?
- **Tools familiarity** — Are you productive in your environment?
- **Navigating codebases** — Can you orient in unfamiliar code?
- **Communication** — Do you explain your thinking? Respond to feedback? Ask for help when stuck?
- **Stripe's operating principles** — Does your approach align with Stripe's culture?

---

## Interview 1: Programming Exercise (1 hour)

### What It Is

An in-depth paired programming project. Format mirrors the CodeSignal assessment you already passed, but communication and collaboration are the primary differentiators. You write code on your machine, screen-sharing with the interviewer.

### What To Expect

- A practical, multi-part problem (NOT LeetCode algorithms)
- Problems build iteratively — Part 1 unlocks Part 2, etc.
- Data handling focus: parse input, transform, return structured output
- ~45 minutes coding + 15 minutes buffer
- Your machine, your IDE, your language

### Evaluated On

- Correctness / Testing / Debugging
- Interaction and collaboration
- Thought process and abstractions
- Writing code (quality, readability, idiomaticness)

### Common Problem Patterns

Based on candidate reports:
- **Transaction/balance processing** — given transactions, calculate balances, detect rejected ones, handle edge cases like negative balances
- **User deduplication/record linking** — given records with weighted similarity scores, identify matches; follow-up: transitive relationships (A matches B, B matches C → A matches C)
- **Scheduling/reservation system** — `is_available(id, timestamp)`, `acquire(id, duration)`; follow-up: LRU-based auto-selection
- **Rate limiter** — design and implement from scratch
- **Log sanitization** — blur/redact credit card numbers from log output
- **Data parsing** — CSV/JSON transformation, building lookup structures

### Key Data Structures Used

- Hash maps for fast lookups (very common)
- Graph traversal for transitive relationships
- State management with timestamps
- String parsing (CSV, JSON, config files)
- NOT: dynamic programming, complex graph algorithms, binary trees

### Strategy

1. **Read the problem carefully.** Ask clarifying questions before coding
2. **Spend 3-5 minutes designing** before writing code — sketch data structures, talk through approach
3. **Vocalize trade-offs** — "I'm using a hash map here because we need O(1) lookups by ID"
4. **Write clean code** — descriptive variable names (`payment_amount` not `x`), helper functions, logical organization
5. **Run code every 5-10 lines** — not after 50 lines
6. **Prioritize correctness over completeness** — a working Part 1 beats broken Parts 1-3
7. **Check in with the interviewer** about your approach periodically
8. **Handle edge cases explicitly** — empty inputs, zero amounts, duplicate entries

### Practice Problems

Practice these timed at 45 minutes each, talking out loud:
- Build a simple bank ledger: process deposits/withdrawals, reject overdrafts, report balances
- Build a rate limiter: `allow(user_id, timestamp)` returns true/false, max N requests per window
- Parse a CSV of user records, deduplicate by email (case-insensitive), merge metadata
- Build a simple key-value store with TTL (time-to-live) expiration

---

## Interview 2: Integration Exercise (1 hour)

### What It Is

Evaluates your ability to write code within an existing system, work with libraries, and combine existing code to fulfill a spec. Heavy emphasis on HTTP requests to APIs and **testing**.

### What To Expect

- A spec and documentation provided at the start
- You clone a private GitHub repo and work within it
- Involves popular libraries in your language + HTTP requests to a public API
- Progressive parts (Part 1 → Part 2 → Part 3)
- Testing is a **very important factor** — you're adding/modifying code in an existing system

### Evaluated On

- Ability to help yourself (reading docs, figuring things out)
- Abstractions and writing code
- Correctness / Testing / Debugging
- Interaction and collaboration

### What "Integration" Looks Like

Reported patterns:
- Call specified API endpoints, parse JSON responses, transform and store data
- Build a payment flow using Stripe-like API calls
- Build a webhook handler that processes incoming events
- Fetch data from an API, perform ETL operations, output results
- Implement an email scheduling system with dynamic time offsets

### HTTP Client Fluency (Critical Prep)

The prep doc explicitly states: *"You should have a working familiarity of an HTTP client of your choice."*

**TypeScript/Node.js — native `fetch` (zero dependencies):**
```typescript
// GET request
const response = await fetch('https://api.example.com/data', {
  headers: { 'Authorization': 'Bearer sk_test_xxx' },
});
if (!response.ok) throw new Error(`HTTP ${response.status}`);
const data = await response.json();

// POST request with JSON body
const response = await fetch('https://api.example.com/charges', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer sk_test_xxx',
  },
  body: JSON.stringify({ amount: 2000, currency: 'usd' }),
});

// IMPORTANT: fetch does NOT reject on 4xx/5xx — always check response.ok
```

**Python — `requests`:**
```python
import requests

# GET
resp = requests.get('https://api.example.com/data',
                    headers={'Authorization': 'Bearer sk_test_xxx'},
                    timeout=5)
resp.raise_for_status()  # throws on 4xx/5xx
data = resp.json()

# POST with JSON
resp = requests.post('https://api.example.com/charges',
                     json={'amount': 2000, 'currency': 'usd'},
                     headers={'Authorization': 'Bearer sk_test_xxx'},
                     timeout=5)

# Session for multiple calls to same API
with requests.Session() as s:
    s.headers.update({'Authorization': 'Bearer sk_test_xxx'})
    r1 = s.get(url1)
    r2 = s.post(url2, json=payload)
```

### Strategy

1. **READ THE SPEC THOROUGHLY** before writing code — understand all requirements first
2. **Read the existing codebase** — understand what's there before adding code
3. **Develop incrementally** — write 5 lines, run, verify. Not 50 then test
4. **Write tests** — this is explicitly evaluated. Even simple assertions count
5. **Handle errors** — what if the API returns a 4xx? What if the response is malformed?
6. **Use docs freely** — Google, Stack Overflow, official API docs are all allowed
7. **Ask clarifying questions** — "What should happen if the API returns an error?"
8. **Use descriptive names and clean abstractions** — code quality matters as much as correctness

### Practice

- Build a small project that calls a real public API (JSONPlaceholder, or Stripe test mode)
- Time yourself: can you go from zero to a working GET request in under 2 minutes?
- Practice reading unfamiliar API docs and implementing a call you've never made before
- Build a simple webhook receiver that validates and processes incoming POST requests
- Practice writing tests for code that calls external APIs (mock the HTTP layer)

---

## Interview 3: Bug Squash (1 hour)

### What It Is

You debug a real bug in an open-source project. Clone a repo, run failing tests, find the bug, fix it. This is Stripe's signature interview round.

### What To Expect

- You receive a codebase from GitHub (a real or forked open-source project)
- There are failing tests that reveal the bug
- The bugs are based on real bugs Stripe has encountered
- The bugs themselves aren't necessarily complex — the challenge is navigating an **unfamiliar codebase**
- You can use any debugging approach: print statements, debugger, whatever works

### Evaluated On

- Can you navigate an unfamiliar codebase and figure out what's going on?
- Debugging methodology (structured, not random guessing)
- Tool proficiency
- Communication of reasoning

### Critical Insight

From Jake Zimmerman (who helped design this round at Stripe): **"Even with knowledge of the exact bug ahead of time, you'll fail the interview unless you demonstrate a repeatable, methodical debugging process."** The process matters more than the fix.

There is literally a **rubric checkbox** for:
- Did the candidate use a debugger?
- Did the candidate form hypotheses and test them?
- Did the candidate build a mental model of the codebase?
- Did the candidate communicate their reasoning?

### The Process (Follow This Exactly)

**Phase 1: Orient (first 5-10 minutes)**
1. Read the prompt carefully. Confirm with the interviewer what the expected vs. actual behavior is
2. Run the failing test to see the actual error output / stack trace
3. Read the README for project structure hints
4. Identify the entry point — what does the test call? What file/function is that?

**Phase 2: Investigate (next 20-30 minutes)**
5. **Read the failing test** — understand what it expects
6. **Follow the call chain** — what does the test call? What does that call?
7. **Form a hypothesis** — "I think the bug is in X because the error says Y"
8. **Set a breakpoint or add a print** at the function the test calls. Run. Inspect variables
9. **Binary search the bug** — if a function has 5 steps, check state at step 3. Correct? Bug is in steps 4-5. Wrong? Steps 1-2
10. **Narrate your reasoning** throughout

**Phase 3: Fix (remaining time)**
11. Once found, write the fix
12. Run the failing test to confirm it passes
13. Run the broader test suite to confirm you didn't break anything
14. Explain what the bug was and why the fix works

### Reading Stack Traces

- **Python:** Read bottom-up. Last frame is where the error occurred. Exception type + message at the very bottom
- **JavaScript/Node.js:** Read top-down. First frame is the throw site
- **Key info to extract:** File, line number, function name, error message. Then trace backward through the call chain
- **Look for project code** in the trace vs. library internals — the bug is almost always in the project code

### Common Failure Modes (Avoid These)

- Not reading the documentation — docs explain what things SHOULD do
- Chasing the first "good idea" instead of systematically narrowing down
- Running the full test suite (too much noise) — run only the failing test
- Trying to understand the entire codebase instead of focusing on the relevant path
- Silence — not explaining your reasoning

### Navigating Unfamiliar Codebases Quickly

- **Search aggressively** — `grep -r "function_name"` or IDE search for definitions and usages
- **Look at directory structure first** — most projects follow conventions (`src/`, `lib/`, `test/`)
- **Read types/interfaces** — function signatures tell you data flow without reading every line
- **Read tests as documentation** — tests show intended behavior
- **Do NOT try to understand everything** — focus only on the path from failing test to the bug

### Practice

This is the round that benefits most from practice:
1. Clone a popular open-source project in your language (a small web framework, CLI tool, or library)
2. Go to its GitHub Issues and find a closed bug report
3. Check out the commit BEFORE the fix
4. Set a 60-minute timer
5. Try to find and fix the bug while talking out loud
6. Compare your fix to the actual fix

Good projects for this:
- **Python:** Flask, Click, httpx, or any small well-tested library
- **TypeScript/Node.js:** Express middleware, a small CLI tool, or Stripe's own open-source libraries
- **Go:** Any small Go tool from the standard ecosystem

Also: make sure your debugger works before interview day:
- **Python:** `breakpoint()` or `import pdb; pdb.set_trace()`
- **Node.js:** `debugger` statement + `node --inspect`, or VS Code breakpoints
- **Go:** Delve (`dlv test`) or `fmt.Printf` debugging

---

## Interview 4: Behavioral (45 minutes)

This likely combines **User First & Curious** and **Experience & Goals**.

### Part A: User First & Curious

**What they evaluate:** User-centric approach, curiosity

**Prepare stories (STAR format) for:**
- A time you designed a solution with the user/customer in mind
- A time you took initiative to understand user needs and balanced them against your own objectives
- A time you faced challenges affecting multiple users and navigated changes while keeping UX at the forefront
- A time you learned something new, resolved a misunderstanding, or adjusted your approach based on new insights
- A time you went above and beyond for a customer/user
- A time you proactively identified and fixed a UX/developer-experience issue nobody asked you to fix

**Connect to Stripe's operating principles:**
- "Users First" — start with the user and work backwards
- "Stay Curious" — show perpetual learning drive
- "Really, really, really care" — genuine investment in outcomes

### Part B: Experience & Goals

**What they evaluate:** Career fit, communication, work experience

**Prepare to discuss:**
- One technically challenging project you led (architecture decisions, trade-offs, outcomes, what you learned)
- A technical contribution that allowed others to be successful
- A cross-functional project you worked on
- What you're looking for in your next role and why Stripe specifically
- How your past experience relates to the TSE role

**Sample questions reported by candidates:**
- "Describe a technically challenging project and how you approached it"
- "Tell me about a time you disagreed with a team decision. What did you do?"
- "Tell me about a time you made a mistake. What did you learn?"
- "What's the hardest bug you've ever debugged?"
- "How would you improve Stripe Payments?" (tests user-first thinking)
- "Tell me about a time you explained something technical to a non-technical person"

**For TSE specifically — emphasize:**
- Developer empathy — times you helped another developer debug an issue
- Documentation — times you wrote docs that unblocked people
- API design — times you identified confusing interfaces and improved them
- Cross-language flexibility — show you can context-switch between languages/codebases

---

## Stripe Operating Principles (Know These Cold)

These are evaluated across every interview. Reference them naturally in behavioral answers and demonstrate them in technical rounds.

| Principle | What It Means | How To Show It |
|-----------|---------------|----------------|
| **Users First** | Prioritize user needs above all; engage directly with customers | Ask clarifying questions about the user impact; handle edge cases thoughtfully |
| **Create with Craft and Beauty** | Excellence in everything; quality demonstrates care | Write clean, well-organized code; take care with naming and structure |
| **Move with Urgency and Focus** | Speed matters; invest in efficiency | Don't over-engineer; solve the problem directly; manage your time well |
| **Collaborate Egolessly** | No silos; debate ideas, not people; credit others | Treat the interviewer as a collaborator; incorporate feedback gracefully; ask for help |
| **Obsess Over Talent** | Rigorous hiring; support growth | Show high standards in your own work |
| **Stay Curious** | Perpetual learning; discovery over comfortable certainty | Ask thoughtful questions; show enthusiasm for understanding things deeply |

**Cultural phrases to know:** "We haven't won yet", "Be meticulous about foundations", "Disagree and commit", "Really, really, really care"

---

## Questions To Ask Your Interviewers

Stripe's prep doc specifically recommends coming with questions. Julia Evans' list (referenced in the prep doc) is a good source. Pick 2-3 per interview:

**Engineering practices:**
- How do you balance support work and feature development on the TSE team?
- What does a typical week look like for a TSE?
- How do you handle serious production bugs? What's the incident response process?
- Is it easy to talk to the internal engineering teams when you identify a product issue?

**Culture / team:**
- How are disagreements solved — both technical and non-technical?
- Can you give me an example of a TSE who has grown in the role? How did their responsibilities change?
- What's the most interesting support case you've seen recently?

**Hard questions (Stripe says: "Don't be afraid to ask"):**
- What's the biggest challenge facing the TSE team right now?
- What would you change about how Stripe works if you could?
- How does Stripe handle the tension between shipping fast and maintaining quality?

---

## Environment Setup Checklist (Do Before Interview Day)

- [ ] Personal computer (not employer's) set up for development
- [ ] Your preferred IDE / editor ready and familiar
- [ ] Can compile and run code in your interview language
- [ ] Can clone a private GitHub repo (SSH keys or prepared to "Download ZIP")
- [ ] HTTP client library installed and tested (fetch/axios for Node, requests for Python)
- [ ] Debugger working (breakpoints or print-style)
- [ ] Stripe's language-specific setup repo cloned and tests passing (see prep doc for links)
- [ ] Zoom installed and tested (camera, microphone, screen sharing)
- [ ] Second monitor or split-screen setup for reading docs while coding
- [ ] Browser tabs ready: language docs, Stack Overflow, Stripe API docs

---

## 7-Day Preparation Plan

All drills are in `drills/`, all simulations are in `projects/`. Run drills with `npx tsx drills/drill_01_rate_limiter.ts`, simulations with `npx tsx projects/01-programming-sim/starter.ts`.

### Day 1 (Wednesday 3/18): Environment + Foundations
- [ ] Complete environment setup checklist above
- [ ] Clone and run Stripe's language-specific setup repo, ensure tests pass
- [ ] Review `drills/toolbox.ts` — study all 10 pattern categories, run it to verify
- [ ] Review lessons 01-02 (API Fundamentals, Payments Deep Dive)
- [ ] Complete **Drill 03 (Transaction Ledger)** — levels 1-2 only. Focus on clean code, not speed

### Day 2 (Thursday 3/19): Programming Exercise Prep
- [ ] Complete **Drill 01 (Rate Limiter)** — all 4 levels, timed at 35 min. Talk out loud
- [ ] Complete **Drill 02 (Record Dedup)** — all 4 levels, timed at 35 min. Talk out loud
- [ ] Review your code from both drills: Are variable names descriptive? Helper functions? Would a stranger understand it?
- [ ] Re-study `toolbox.ts` patterns you reached for: `groupBy`, `countBy`, `UnionFind`, `multiSort`
- [ ] Finish **Drill 03 (Transaction Ledger)** levels 3-4 if not done

### Day 3 (Friday 3/20): Integration Exercise Prep
- [ ] Complete **Drill 05 (API Client)** — all 4 levels, timed at 35 min
- [ ] Complete **Drill 06 (Express API)** — all 4 levels, timed at 40 min
- [ ] Review lessons 03-04 (Billing, Connect) for product breadth
- [ ] Re-study `toolbox.ts` HTTP patterns: `httpGet`, `httpPost`, `paginateAll`

### Day 4 (Saturday 3/21): Bug Squash Prep
- [ ] Complete **Drill 04 (Log Sanitizer)** — all 4 levels (warms up regex/string debugging skills)
- [ ] Run **Bug Squash Simulation** (`projects/03-bug-squash-sim/`):
  - Read `README.md` for the debugging methodology
  - Set a 50-min timer
  - Run `npx tsx buggy.ts`, read failures, find and fix all 5 bugs
  - Talk through your reasoning the entire time
  - Compare against `fixed.ts` when done
- [ ] Practice: use your debugger (breakpoints or `console.log`) to trace through unfamiliar code
- [ ] Note which bugs you found fast vs. slow — what methodology gaps surfaced?

### Day 5 (Sunday 3/22): Behavioral Prep
- [ ] Complete **Behavioral Workbook** (`projects/04-behavioral-prep/workbook.md`):
  - Section 1: Stripe Operating Principles alignment (20 min)
  - Section 2: Technical project deep dives (20 min)
  - Section 3: User First story bank (15 min)
  - Section 4: Questions for interviewers (10 min)
  - Section 5: Pre-interview checklist (5 min)
  - Section 6: Self-evaluation rubric
- [ ] Practice telling each story OUT LOUD, timed at 2 min each
- [ ] Read 2-3 recent Stripe engineering blog posts for conversation material:
  - "Can AI agents build real Stripe integrations?" (March 2026)
  - "Real-time analytics for Stripe Billing" (September 2025)
  - "Test clocks for Stripe Billing" (May 2024)

### Day 6 (Monday 3/23): Full Simulation Day
- [ ] **Programming Exercise Simulation** (`projects/01-programming-sim/`):
  - Read `README.md` spec, set 50-min timer, implement in `starter.ts`
  - Target: pass Parts 1-2 cleanly, attempt Part 3
  - Compare against `solution.ts` when done
- [ ] 15-min break
- [ ] **Integration Exercise Simulation** (`projects/02-integration-sim/`):
  - Read `README.md` spec + `server.ts` existing code, set 50-min timer, implement in `starter.ts`
  - Target: pass Parts 1-2 cleanly, attempt Part 3
  - Compare against `solution.ts` when done
- [ ] 15-min break
- [ ] Review gaps from both simulations. Re-do any drill that covers a weak pattern
- [ ] Run through behavioral stories one final time

### Day 7 (Tuesday 3/24): Light Review + Rest
- [ ] Quick scan of lessons 01-04 (just the "Check Yourself" sections)
- [ ] Re-read this guide's strategy sections for each interview type
- [ ] Skim `toolbox.ts` one final time — make sure patterns are in muscle memory
- [ ] Run through your top 4 STAR stories and your top 3 interviewer questions
- [ ] Test your Zoom, camera, mic, screen sharing one final time
- [ ] Go to bed early — the prep doc says: "Be well-rested and ready to think on your feet"

---

## Day-Of Checklist

- [ ] Close all unnecessary apps (notifications, Slack, email)
- [ ] Have water and snacks ready
- [ ] Have your IDE open with a clean workspace
- [ ] Have browser tabs ready: language docs, Stripe docs, Stack Overflow
- [ ] Have a notepad for jotting quick notes during the interview
- [ ] Remember: the interviewer is a collaborator, not an examiner. Think out loud
- [ ] Remember: it's OK to look things up. It's OK to ask questions. It's OK to say "I'm not sure, let me think about this"
- [ ] Remember: prioritize correctness over completeness. Working Part 1 > broken Parts 1-3
- [ ] You stay on the same Zoom link between interviews — don't log off
- [ ] Ask for breaks if you need them — the interviewers expect this
