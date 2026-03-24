# Stripe TSE Onsite — March 25, 2026

## Your Schedule

| Time (PDT) | Round | Interviewer | Duration | Type |
|---|---|---|---|---|
| 11:00–11:45 | Programming Exercise | Nicholas Xavier | 45 min | Paired coding — build from scratch |
| 11:45–12:45 | Experience & Goals | Ali Riaz | 60 min | Behavioral — career fit, projects, why Stripe |
| 12:45–1:30 | **Lunch break** | — | 45 min | Eat. Reset. |
| 1:30–2:15 | Users First & Curious | Tyler Martin | 45 min | Behavioral — user empathy, curiosity |
| 2:15–2:30 | **Break** | — | 15 min | — |
| 2:30–3:30 | Integration | Adam Fuller | 60 min | Code in existing system, HTTP/API, testing |

All on Zoom, same link. Shadow interviewers may be present. AI tools **strictly prohibited** (Copilot, ChatGPT, Gemini, TabNine — including AI in search).

---

## Recruiter Prep Call (day before)

The recruiter is your advocate — they want you to pass. Use this call to gather intel, not to impress.

### Questions to ask

1. **"Can you tell me anything specific about what to expect in the programming or integration exercise?"** — They sometimes share the general topic area or format hints.
2. **"Is there anything about my background that I should be prepared to address?"** — Reveals if there's a concern on their side so you can prepare a response.
3. **"What do the strongest candidates do differently in the behavioral rounds?"** — They see hundreds of debriefs. They know the patterns.
4. **"Is there anything about the format or logistics beyond the prep doc?"** — Screen sharing setup, paired vs solo, time structure.
5. **"Can you tell me anything about the interviewers' styles?"** — Sometimes they'll share useful context.
6. **"What's the most common reason TSE candidates don't pass the onsite?"** — Tells you exactly what to avoid.

### What NOT to do

- Don't ask questions answered by the prep doc (schedule, format, tools policy) — signals you didn't read it
- Don't ask about comp or timeline — save for after you pass
- Don't try to impress technically — they're helping you, not evaluating you
- Have the interview schedule in front of you so you can ask about specific rounds
- Write your questions down beforehand

---

## What Stripe Evaluates (All Rounds)

From the official prep doc, Stripe assesses these across every interview:

- **Problem solving** — Can you understand a problem and devise a solution?
- **Design** — Is your code well-organized with clean interfaces?
- **Correctness** — Do you reason about correctness, use tests, handle edge cases?
- **Debugging** — Can you spot and fix bugs in your own code?
- **Language familiarity** — Is your TypeScript idiomatic?
- **Tools familiarity** — Are you productive in your environment?
- **Navigating codebases** — Can you orient in unfamiliar code?
- **Communication** — Do you explain your thinking, respond to feedback, ask for help?
- **Operating principles** — Does your approach align with Stripe's culture?

---

## Round 1: Programming Exercise (45 min) — Nicholas Xavier

### What It Is

A paired programming project. You screen-share your IDE and build something from scratch. The format mirrors your CodeSignal assessment but with live collaboration.

### What To Expect

- A practical, multi-part problem (NOT LeetCode/algorithms)
- Parts build iteratively — Part 1 unlocks Part 2
- Data handling: parse input, transform, return structured output
- ~35 min coding + ~10 min intro/questions
- Your machine, your IDE, your language

### What They Evaluate

- Correctness / Testing / Debugging
- Interaction and collaboration
- Thought process and abstractions
- Writing code (quality, readability, idiomaticness)

### Common Problem Patterns

From candidate reports:
- **Transaction/balance processing** — process events, calculate balances, detect overdrafts
- **Record deduplication** — match records by similarity, handle transitive relationships
- **Scheduling/reservation** — `is_available(id, timestamp)`, `acquire(id, duration)`
- **Rate limiter** — fixed window, sliding window, token bucket
- **Log sanitization** — regex redaction of sensitive data
- **Data parsing** — CSV/JSON transformation, building lookup structures

### Strategy

1. **Read the spec fully** before writing code. Ask clarifying questions.
2. **Spend 2-3 min designing** — sketch data structures, talk through approach.
3. **Vocalize trade-offs** — "I'm using a Map here for O(1) lookups by customer ID."
4. **Write clean code** — `paymentAmount` not `x`. Extract helpers. Name things well.
5. **Run every 5-10 lines.** Not after 50.
6. **Parts 1-2 clean > Parts 1-3 broken.** Prioritize correctness over completeness.
7. **Check in with the interviewer** about your approach.
8. **Handle edge cases** — empty inputs, zero amounts, duplicates.

### Pacing (45-min round)

| Part | Target | Cumulative |
|---|---|---|
| Read spec + design | 3 min | 3 min |
| Part 1 | 12 min | 15 min |
| Part 2 | 13 min | 28 min |
| Part 3 | 10 min | 38 min |
| Questions | 5 min | 43 min |

If stuck on a part for 3+ minutes past target, move on.

### Practice

- `drills/drill_01_rate_limiter.ts` — timed at 30 min
- `drills/drill_02_record_dedup.ts` — timed at 30 min
- `drills/drill_03_transaction_ledger.ts` — timed at 30 min
- `projects/01-programming-sim/` — full simulation, timed at 40 min

---

## How to Think in Every Behavioral Answer

This applies to both Ali's and Tyler's rounds. No matter what story you tell, filter it through these lenses. These are the signals that separate hire from no-hire at Stripe, specifically for TSE.

### The TSE Lens: Everything Is About Making Other Developers Succeed

TSE is the most customer-facing technical role at Stripe. The job is fundamentally about helping other developers be successful — debugging in someone else's context, writing docs and code samples, finding friction proactively, and advocating for DX internally. Every story you tell should connect back to: **did this make someone else's life better?**

This is different from SWE stories. Don't just talk about what you built — talk about who it helped, how you knew they needed it, and what happened for them after.

### Six Themes to Hit Across All Stories

**1. Work backwards from the user, not the architecture.**
Stripe's most important principle is "Users first." When you describe a project, start with the user's problem, not the technical stack. "Our partners couldn't see system health during peak load" is better than "I built Grafana dashboards." The decision to build dashboards should flow from the user need, not the other way around.

This means: when asked about technical decisions, frame them as user decisions. "I chose X because it gave developers Y" not "I chose X because it was technically elegant."

**2. Show you prefer investigating to being right.**
Stripe's definition of "Curious" is: "We prefer investigating to being right." This is the single most important behavioral signal for the Users First & Curious round. In practice it means:
- Say "I don't know, but here's how I'd find out" — never bluff
- Tell stories where you changed your mind after learning something new
- Show that you were wrong about something, discovered why, and adjusted
- Demonstrate comfort with ambiguity and unfamiliar territory

Patrick Collison: "I think it's much better to be right than to be consistent." Stripe wants people who update their beliefs when presented with new evidence, not people who defend their original position.

**3. Own outcomes, not tasks.**
Stripe uses a DRI model — Directly Responsible Individual. Every story should show you owned the outcome, not just executed a task someone assigned you. The difference:
- Task: "I was assigned to build the integration and I built it"
- Outcome: "I owned the Amazon Fresh integration end-to-end. When their failure-handling requirements didn't map to our architecture, I reframed it as a shared problem and co-designed the event architecture"

Quantify impact. "Cut support requests" is okay. "Cut partner support requests by 40% during peak events" is a hire signal. One candidate was rejected despite acing all technical rounds because they couldn't demonstrate "large impact projects."

**4. Give credit. Be exothermic.**
Stripe screens for "intrinsically happy" people. "Exothermic" means you release energy into the room, not absorb it. In your stories:
- Name teammates and what they contributed: "My colleague Sarah designed the schema, which made my API layer much cleaner"
- Frame collaborations as "our shared problem" not "their requirement vs. my architecture"
- Show genuine enthusiasm for what you learned, not just what you accomplished
- Never be negative about past employers, teammates, or technologies

John Collison: "When you hire this person, you're not only bringing them, but you're bringing their effect on the culture."

**5. Show craft and detail orientation.**
Patrick Collison: "There's a culture at Stripe of just really prizing the small details." and "We talk a lot about craftsmanship and rigor and abstractions that can endure over decades."

When you describe technical work, show that you cared about quality beyond what was required:
- "I didn't just port the old logging setup — I rethought how we structured logs for developer ergonomics"
- "The fourth partner onboarded in weeks instead of months because I invested in a clean abstraction"
- Show you made things not just functional but excellent

This is the difference between "I integrated with the API" and "I designed a unified abstraction across three different partner protocols so the system could scale."

**6. Be macro-optimistic, micro-pessimistic.**
Patrick Collison: "We want to be micro pessimists and macro optimists." In your stories:
- **Macro:** Believe the problem is solvable. Approach challenges with "how might this work?" not "why will this fail?" Show you see obstacles as tractable.
- **Micro:** Be relentlessly critical of what exists today. Show you notice every friction point, every bug, every suboptimal experience. "The logging system worked, but developers avoided using it because queries were slow and expensive — that's a problem worth solving."

### What Kills You

These are the no-hire signals from Stripe debrief reports. Avoid them:

- **All "I", no "we"** — every story is a solo act with no teammates
- **Tech without user impact** — you describe architecture elegance without saying who it helped
- **Bluffing** — you pretend to know something you don't, contradicting "prefer investigating to being right"
- **Negativity** — complaining about past employers, teammates, or tools
- **Rambling** — can't tell a story in under 2 minutes; Stripe has a writing culture and values concise, structured communication
- **No evidence of curiosity** — career shows comfort-seeking, not growth-seeking
- **No numbers** — "it was faster" vs "it was 60% cheaper with faster queries"

### The STAR+R Format

Stripe recommends STAR. Add R (Reflection) to stand out:

- **Situation** — set the scene in 2 sentences
- **Task** — what was your responsibility (frame as ownership, not assignment)
- **Action** — what you specifically did (give credit to others too)
- **Result** — quantified outcome
- **Reflection** — what you learned, what you'd do differently, how it changed your thinking

The reflection is what separates "I completed a project" from "I grew as an engineer." It directly signals the Curious principle.

---

## Round 2: Experience & Goals (60 min) — Ali Riaz

### What It Is

Behavioral interview focused on your career, technical depth, and fit for the TSE role. Ali will discuss technically challenging projects you've led and what you're looking for next.

### What They Evaluate

- Career fit
- Communication
- Work experience
- Ability to articulate impact at scale

### What To Expect

From the official prep doc:
- Discuss one of the more technically challenging projects you've worked on (ideally one you led)
- Discuss what you're looking for in your next role
- Sample topics: a technically challenging project, a technical contribution that enabled others, a cross-functional project
- STAR format recommended (Situation, Task, Action, Results — with data and metrics)

### Prepare These Stories

**Lead story: Amazon Fresh integration**
- Year-long cross-functional project, co-designing event architecture with Amazon's team
- Hit: scale (multiple teams, two companies), trade-offs (their requirements vs. your architecture), shared problem framing
- TSE angle: "I've been the developer on the receiving end of a partner integration — I know what good support looks like"

**Second story: Unified ordering API**
- Three marketplace partners (Doordash, Uber Eats, Amazon Fresh), three protocols, one abstraction
- Hit: design thinking, craft, compounding investment — fourth partner onboarded in weeks instead of months

**Third story: Structured logging refactor (Elastic → Grafana/Loki/Prometheus)**
- 60% cost reduction, faster queries, better developer experience, PagerDuty/Slack integrations
- Hit: craft, measurable impact, enabling others

**"Why Stripe? Why TSE?"**
> "I've spent my career building integrations — Stripe, Doordash, Uber Eats, Amazon Fresh. I know what it's like to be the developer reading the docs at 11pm trying to figure out why a webhook isn't firing. The best integrations I've worked with were the ones where the partner's support team actually understood the technical problems and could help me debug in my language and context. That's what I want to do at Stripe."

### Common Questions

- "Describe a technically challenging project and how you approached it"
- "Tell me about a time you disagreed with a team decision. What did you do?"
- "Tell me about a time you made a mistake. What did you learn?"
- "What's the hardest bug you've ever debugged?"
- "What are you looking for in your next role?"
- "Tell me about a technical contribution that allowed others to be successful"

### Warning

One candidate on Levels.fyi aced all 4 technical rounds but failed Experience & Goals due to "lack of signal in highlighting large impact projects with large number of contributors." Startup experience is fine, but quantify your impact and show you worked across teams/companies at scale. The Amazon Fresh story covers this.

### Questions to Ask Ali

- "Can you tell me about a TSE who has grown significantly in the role? What did their trajectory look like?"
- "When a TSE identifies a bug or API design issue through support work, what does the path to getting it fixed look like?"
- "What's the biggest challenge facing the TSE team right now?"

---

## Round 3: Users First & Curious (45 min) — Tyler Martin

### What It Is

Behavioral interview evaluating user empathy and intellectual curiosity. Named after two of Stripe's core operating principles.

### What They Evaluate

- User-centric approach
- Curiosity

### What To Expect

From the official prep doc: Think about specific situations where you designed solutions with the user in mind, took initiative to understand user needs, and moments when you learned something new or adjusted your approach based on new insights.

### Prepare These Stories (Distinct From Ali's Round)

Tyler and Ali will compare notes. Zero overlap.

**Lead story: Partner monitoring dashboards (Users First)**
- Realized marketplace partners couldn't see system health during peak load
- Proactively built custom Grafana dashboards for each partner's specific concerns
- Cut partner support requests, converted friction into trust
- TSE angle: "I worked backwards from what partners actually needed — visibility — not what was easiest to build"

**Second story: Career arc (Curious)**
- CNC machinist → music degree → Max/MSP audio-reactive lighting → TouchDesigner/GLSL installations for Facebook/Instagram → Hack Reactor → full-stack engineering → AI/ML
- TSE angle: "I never stopped being curious. My latest project trains a neural network to detect beats in music on a microcontroller."

**Third story: Blinky Time TinyML (Curious — depth)**
- Custom causal CNN, 9K params, INT8 quantized to ~20KB, real-time beat detection on Cortex-M4F
- Shows you learn for the joy of learning, not because someone assigned it

**Fourth story (backup): Fulfil consumer ordering app (Users First)**
- Two completely different user populations: end consumers and internal operators
- Designed interface to serve both without compromising either

### Common Questions

- "Tell me about a time you designed a solution starting from the user's perspective"
- "Tell me about a time you proactively identified a UX issue nobody asked you to fix"
- "Tell me about a time you went deep on something out of pure curiosity"
- "Describe a time you changed your mind after learning new information"
- "Tell me about a time you adjusted your approach based on new insights"

### Questions to Ask Tyler

- "How does Stripe keep the 'Users First' principle alive in practice — in daily decisions, not just hiring?"
- "What's the most interesting support case you've seen recently?"
- "If you could change one thing about how Stripe works, what would it be?"

---

## Round 4: Integration Exercise (60 min) — Adam Fuller

### What It Is

Evaluates your ability to write code within an existing system, work with libraries, and fulfill a spec. Heavy emphasis on HTTP requests and **testing**.

This is your last round. You'll be 3+ hours in. Lean on muscle memory.

### What To Expect

From the official prep doc:
- A spec and documentation provided at the start
- You clone a private GitHub repo and work within it
- Involves popular libraries in your language + HTTP requests to a public API
- Progressive parts (Part 1 → Part 2 → Part 3)
- Testing is a **very important factor**
- It's fine to look things up (Google, Stack Overflow, docs)

From candidate reports:
- Clone a repo, read JSON files, make HTTP REST calls, parse responses, perform ETL
- Typically ~5 tasks; solving 3 is solid
- Focuses on **how you work** — resourcefulness, reading docs, handling the unfamiliar

### What They Evaluate

- Ability to help yourself (reading docs, figuring things out)
- Abstractions and writing code
- Correctness / Testing / Debugging
- Interaction and collaboration

### HTTP Client Patterns (Know These Cold)

```typescript
// GET
const res = await fetch('https://api.example.com/data', {
  headers: { 'Authorization': 'Bearer sk_test_xxx' },
});
if (!res.ok) throw new Error(`HTTP ${res.status}`);
const data = await res.json();

// POST with JSON body
const res = await fetch('https://api.example.com/charges', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer sk_test_xxx',
  },
  body: JSON.stringify({ amount: 2000, currency: 'usd' }),
});

// IMPORTANT: fetch does NOT reject on 4xx/5xx — always check res.ok
```

### Strategy

1. **Read the entire spec before coding.** Understand all requirements first.
2. **Read the existing codebase.** Understand what's already there.
3. **Develop incrementally** — 5 lines, run, verify. Not 50 then test.
4. **Write tests.** This is explicitly evaluated. Even simple assertions count.
5. **Handle errors** — what if the API returns 4xx? Malformed response?
6. **Use docs freely** — Google, Stack Overflow, official docs are all allowed.
7. **Ask clarifying questions.** "What should happen if the API returns an error?"
8. **Clean code matters as much as correctness.** Descriptive names, good abstractions.

### Practice

- `drills/drill_05_api_client.ts` — timed at 30 min
- `drills/drill_06_express_api.ts` — timed at 35 min
- `projects/04-integration/` — full simulation, timed at 50 min
- Practice this sim **last** on practice day to simulate fatigue

---

## Stripe Operating Principles

From the official "What to Expect" doc: Stripe recently refined their operating principles from 16 to 6. The behavioral interviews are aligned to the original 16, which remain deeply integral. Know both.

### The 6 Refined Principles

| Principle | What It Means |
|---|---|
| **Users first** | Keep user needs front and center in all we do |
| **Move with urgency and focus** | Focus on what matters most, invest in what makes us faster |
| **Be meticulous in your craft** | Craftsmanship for its own sake; quality demonstrates care |
| **Seek feedback** | Intellectual honesty; refine ideas collaboratively |
| **Deliver outstanding results** | End-to-end accountability |
| **Curious** | Investigate over being right; genuine interest in the unknown |

### The Full 16 (Grouped)

**How we work:** Users first, Move with urgency and focus, Be meticulous in your craft, Seek feedback, Deliver outstanding results

**Who we are:** Curious, Resilient, Humble, Macro-optimistic, Exothermic

**Leaders:** Obsess over talent, Elevate ambitions, Set the pace and energy, Make decisions and be accountable, Lead with clarity and context, Solve problems

### Phrases to Know

"We haven't won yet" · "Disagree and commit" · "Be politely relentless" · "Really, really, really care"

---

## Environment Setup

Do this before interview day:

- [ ] Personal computer (not employer's) ready for development
- [ ] IDE open, can compile and run TypeScript (`npx tsx file.ts`)
- [ ] Can clone a private GitHub repo (SSH keys or "Download ZIP" fallback)
- [ ] `fetch` working for HTTP requests (Node 18+ has it built in)
- [ ] Zoom installed, camera/mic/screen sharing tested
- [ ] Browser tabs ready: TypeScript docs, Stripe API docs, Stack Overflow
- [ ] Second monitor or split-screen for reading docs while coding
- [ ] Stripe's JS interview prep repo cloned and working

---

## 5-Day Prep Plan (Fri 3/20 → Tue 3/24)

Interview: **Wednesday March 25.** Five full days of prep.

### Drill Priority

Not all 10 drills are equal. Based on reported Stripe problem frequency:

| Priority | Drill | Why | Time |
|---|---|---|---|
| **Must do** | 07 Tiered Pricing | #1 most reported Stripe problem | 30 min |
| **Must do** | 01 Rate Limiter | Top 5 reported | 30 min |
| **Must do** | 09 String Parsing | Accept-Language is top 5 reported | 30 min |
| **Must do** | 05 API Client | Direct Integration round prep | 30 min |
| **Must do** | 06 Express API | Direct Integration round prep | 35 min |
| If time | 08 Currency Conversion | Graph BFS/DFS, well-known classic | 30 min |
| If time | 02 Record Dedup | Union-find, reported | 30 min |
| If time | 10 Event Scheduler | Store closing penalty (LC 2483) | 30 min |
| Skip | 03 Transaction Ledger | Levels 1-2 done, patterns overlap with 07/01 |  |
| Skip | 04 Log Sanitizer | Regex patterns overlap with 09 |  |

### Day 1 — Friday 3/20: Programming Drills (Highest Frequency)

The patterns most likely to appear with Nicholas Xavier.

- [ ] Review `drills/toolbox.ts` — skim all 10 pattern categories
- [ ] **Drill 07 (Tiered Pricing)** — all levels, timed at 30 min, talk out loud
- [ ] **Drill 01 (Rate Limiter)** — all levels, timed at 30 min, talk out loud
- [ ] **Drill 09 (String Parsing)** — all levels, timed at 30 min, talk out loud
- [ ] Review your code: descriptive names? Helper functions? Clean?

### Day 2 — Saturday 3/21: Integration Drills + Programming Gaps

Prep for Adam Fuller's round AND fill remaining programming patterns.

- [ ] **Drill 05 (API Client)** — all levels, timed at 30 min. HTTP patterns, pagination, retry, webhooks.
- [ ] **Drill 06 (Express API)** — all levels, timed at 35 min. Routes, middleware, testing.
- [ ] **Drill 08 (Currency Conversion)** — all levels, timed at 30 min. Graph BFS/DFS. *Skip if short on time.*
- [ ] Read lessons 01-02 (API Fundamentals, Payments Deep Dive)
- [ ] Drill `fetch` GET/POST until automatic — you'll be tired by 2:30 PM on interview day

### Day 3 — Sunday 3/22: Behavioral Prep (Both Rounds)

Almost half your interview day is behavioral. This day matters.

- [ ] Fill in `projects/02-experience-and-goals/README.md` — all project worksheets + "Why" questions
- [ ] Fill in `projects/03-users-first-and-curious/README.md` — all 6 STAR story prompts
- [ ] Practice Ali stories out loud, timed:
  - Amazon Fresh integration (3 min)
  - Unified ordering API (2 min)
  - Structured logging refactor (2 min)
  - "Why Stripe? Why TSE?" (90 sec)
  - 5-min project walkthrough: architecture → trade-offs → outcomes → lessons
- [ ] Practice Tyler stories out loud, timed:
  - Partner monitoring dashboards (2 min)
  - Career arc (2 min)
  - Blinky Time TinyML (2 min)
- [ ] **Verify zero overlap** between Ali and Tyler stories
- [ ] Pick 2-3 questions per interviewer (all 4)
- [ ] Read the "How to Think in Every Behavioral Answer" section of this guide
- [ ] Read lessons 03-04 (Billing, Connect) for product breadth

### Day 4 — Monday 3/23: Full Simulation

Run through all 4 interviews in order. This is your dress rehearsal.

- [ ] **Programming sim** (`projects/01-programming-sim/`) — 40 min timer, talk out loud
- [ ] 15-min break
- [ ] **Behavioral rehearsal: Ali** — run through all Experience & Goals stories, timed
- [ ] **Behavioral rehearsal: Tyler** — run through all Users First & Curious stories, timed. Confirm no overlap.
- [ ] 45-min lunch break (simulate the real 12:45–1:30 break)
- [ ] **Integration sim** (`projects/04-integration/`) — 50 min timer, do this LAST (simulates 2:30 PM fatigue)
- [ ] Review gaps: which drill covers the pattern you struggled with? Re-do that one drill.

### Day 5 — Tuesday 3/24: Sharpen + Rest

Light day. Trust your prep.

- [ ] Re-do ONE drill — whichever pattern felt weakest on Day 4
- [ ] If time: pick one of Drill 02 (Record Dedup) or 10 (Event Scheduler)
- [ ] Run through stories one final time out loud
- [ ] Run through interviewer questions (2-3 per person)
- [ ] Skim `toolbox.ts` one final time
- [ ] Test Zoom, camera, mic, screen sharing
- [ ] Go to bed early

### Tuesday Night

- [ ] Stop studying by 8 PM
- [ ] Set alarm with buffer — first interview is 11:00 AM PDT
- [ ] Lay out your setup (water, snacks, lunch, notepad, clean desk)

---

## Day-Of: March 25

### Before 11:00 AM

- [ ] Eat a real meal
- [ ] Water bottle + lunch + snacks at desk
- [ ] IDE open with clean workspace
- [ ] Browser tabs: TypeScript docs, Stripe API docs, Stack Overflow
- [ ] Notepad for quick notes
- [ ] Close everything else (email, Slack, notifications)
- [ ] Phone on silent

### Flow

| Time | What | Key reminder |
|---|---|---|
| 11:00–11:45 | **Programming** (Nicholas Xavier) | Screen share. Get Part 1 done in 12 min. Clean code > more parts. |
| 11:45–12:45 | **Experience & Goals** (Ali Riaz) | No screen share. Lead with Amazon Fresh. Have "why Stripe" ready. |
| 12:45–1:30 | **Lunch** | Eat real food. Do not review notes. Reset. |
| 1:30–2:15 | **Users First & Curious** (Tyler Martin) | Different stories than Ali. Lead with partner dashboards + career arc. |
| 2:15–2:30 | **Break** | Drink water. Stand up. |
| 2:30–3:30 | **Integration** (Adam Fuller) | Screen share. You'll be tired — lean on muscle memory. Read the spec first. |

### Mindset

- The interviewer is a collaborator, not an examiner
- It's OK to look things up, ask questions, say "let me think about this"
- Correctness > completeness. Working Part 1 > broken Parts 1-3
- Talk out loud the entire time. Silence is the worst signal.
