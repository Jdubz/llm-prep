# Experience Mapping: Your Background → Stripe TSE Interviews

This maps your actual professional experience to each of Stripe's 6 operating principles, identifies the strongest stories for each interview round, and suggests how to frame them for maximum impact in a TSE context.

---

## Why Your Background Is Unusually Strong for TSE

Before diving into specifics — the TSE role is "the glue that supports developer-users." Your career is a near-perfect arc for this:

1. **You've been on the other side of the integration.** At Fulfil you integrated with Stripe, Doordash, Uber Eats, and Amazon Fresh. You know exactly what it feels like to read a partner's API docs, work through their edge cases, and troubleshoot when things break. This is the TSE job — but from Stripe's side.

2. **You've built unified APIs across messy real-world partners.** The unified ordering API across 3 marketplace partners is exactly the kind of abstraction thinking Stripe values. You didn't just integrate — you designed the integration layer.

3. **You've shipped under zero-tolerance conditions.** Britelite's live broadcast work and Fulfil's robotic grocery operations (a jug of milk falls, the system must compensate in real-time) demonstrate composure under pressure that maps directly to supporting production payment systems.

4. **You run your own tools.** Job Finder, Imagineer, App Monitor, Blinky Time — these aren't toy projects. They show deep curiosity and the "build it yourself" mentality Stripe prizes.

---

## Principle-by-Principle Mapping

### 1. Users First

> "We work backwards from our users' needs."

**Your strongest stories:**

**Story A: Fulfil — Partner Dashboards (Best for TSE)**
You built custom monitoring dashboards for select partners (Amazon, Doordash) so they could observe system health during high-throughput events. You didn't wait for them to ask — you identified that partners were anxious during peak times and proactively gave them visibility. This directly reduced inbound support volume and built trust.

- *TSE frame:* "I've been the developer on the receiving end of an opaque integration. At Fulfil, I realized our partners couldn't see what was happening inside our system during peak load. So I built custom Grafana dashboards tailored to each partner's specific concerns — Amazon cared about order lifecycle latency, Doordash cared about delivery driver dispatch timing. This cut partner support requests during peak events significantly and converted a source of friction into a trust-building moment."
- *Principle connection:* You worked backwards from what partners actually needed (visibility), not what was easiest to build.

**Story B: Fulfil — Consumer Ordering App**
You worked on the customer-facing PWA while simultaneously supporting operations creating test orders. Same tool, two very different user populations. You had to balance consumer UX with operator power-user workflows.

- *TSE frame:* "The ordering app served two completely different user types — end consumers placing grocery orders and internal operators running test scenarios. I had to understand both user flows deeply. For consumers, speed and clarity mattered most. For operators, configurability and edge-case coverage mattered. I designed the interface to serve both without compromising either — default simple, but with operator-mode features accessible to those who needed them."

**Story C: Opna — McDonald's Dialogflow**
You implemented McDonald's entire menu into a conversational UI — substitutions, modifications, coupons. This is inherently user-first: the entire product IS the user experience.

---

### 2. Create with Craft and Beauty

> "Surprisingly great work comes from careful thought. Quality demonstrates user care."

**Your strongest stories:**

**Story A: Fulfil — Unified Ordering API (Best)**
You created a single unified ordering API that handled secure order placement from Doordash, Uber Eats, and Amazon Fresh — each with different protocols (FTP sync, REST, webhooks). Instead of three bespoke integrations, you built one abstraction that was clean enough to onboard new partners easily.

- *TSE frame:* "When we onboarded our third marketplace partner, I recognized we were building the same integration plumbing for the third time with slight variations. I designed a unified ordering API with a common internal model, and adapters for each partner's idiosyncrasies — FTP inventory sync for one, REST for another, webhooks for the third. The abstraction was clean enough that when Amazon Fresh came along, onboarding took weeks instead of months. That's the kind of craft that compounds."
- *Principle connection:* You invested in a beautiful abstraction that paid dividends.

**Story B: Fulfil — Structured Logging Refactor**
You migrated from Elastic to Grafana/Loki/Prometheus. You reduced network/storage load by 60% while simultaneously improving developer experience AND decreasing incident response times. This is craft — making something better on every dimension at once.

- *TSE frame:* "Our logging system was expensive, slow to query, and developers avoided using it. I led the migration to Grafana/Loki/Prometheus and didn't just port the old setup — I rethought how we structured logs for developer ergonomics. We added PagerDuty/Slack integrations with configurable triggers. The result: 60% cost reduction, faster queries, and developers who actually wanted to use observability because it was well-designed. We started catching problems before users noticed."

**Story C: Portfolio Website**
315+ automated tests, Lighthouse-optimized, serverless contact form with bot detection and rate limiting. This is over-engineered for a portfolio site — in the best way. It shows you care about craft even when nobody's watching.

---

### 3. Move with Urgency and Focus

> "Speed matters. We aspire to be the world's fastest organization."

**Your strongest stories:**

**Story A: Fulfil — Startup Growth (Best)**
You joined as employee 98 with no real clients and a single test factory. In 3+ years you were supporting Amazon, Doordash, Uber Eats, and Lucky's across 3 fully automated stores running 12+ hours/day. You didn't just write code — you helped build the company.

- *TSE frame:* "When I joined Fulfil, we had zero paying customers and one test facility. Three years later we had Amazon Fresh, Doordash, and Uber Eats running through our system across three states. That pace required constant prioritization — sometimes the right move was a quick-turn integration for a new partner, sometimes it was investing in the unified API that would save months later. I learned to feel the difference between urgency that creates debt and urgency that creates leverage."

**Story B: Britelite — Live Broadcast**
Celebrity events, millions of viewers, zero-tolerance for errors. The Instagram Instastop / Twitter Golden Screen was live on air with no room for mistakes. IR touch screens malfunctioned under flood lights. You had to solve problems in real-time.

- *TSE frame:* "At Britelite, our software ran live during award show broadcasts reaching millions of viewers. There was no 'we'll hotfix it later' — it had to work perfectly the first time. I learned to build systems that are resilient to unpredictable conditions. IR touch screens triggered ghost touches from flood lights. I had to diagnose and work around that on-site, live, with cameras rolling."

**Story C: Fulfil — HOG (High Throughput Order Generator)**
You designed a testing tool and in the process discovered and fixed a critical performance bottleneck, doubling system throughput.

---

### 4. Collaborate Egolessly

> "No information silos or territorial behavior. Question assumptions, debate vigorously, abandon inferior ideas."

**Your strongest stories:**

**Story A: Fulfil — Amazon Fresh Integration (Best)**
A year-long project working directly with Amazon's team. You had to translate their business requirements into feasible requirements that worked with Fulfil's different architecture. Two companies, two architectures, one shared goal. Required constant negotiation and compromise.

- *TSE frame:* "The Amazon Fresh integration was a year-long collaboration between our 5-person team and Amazon's much larger org. They had strict requirements around failure handling that didn't map cleanly to our architecture. Instead of pushing back, I worked to understand their actual concerns — which were fundamentally about reliability guarantees for their customers. We co-designed an event-based architecture using Pub/Sub that satisfied their failure-handling requirements while being implementable in our system. The key was treating it as 'our shared problem' rather than 'their requirement vs. our architecture.'"
- *Principle connection:* No ego about whose architecture was 'right.' Focus on the shared outcome.

**Story B: Fulfil — "Everyone Is a Full Stack Developer"**
Feature ownership model where you gathered requirements, interviewed stakeholders, drafted RFCs, then paired with SMEs to implement. This is egoless by design.

**Story C: Opna — Guild Model**
You formed a consulting guild where engineers shared work and resources while maintaining autonomy. As the technical leader, you had to balance directing architectural decisions with respecting independent contributors' expertise.

---

### 5. Obsess Over Talent

> "Every employee shares responsibility for recruiting. Managers maintain rigorous hiring standards."

**Your strongest stories:**

**Story A: Opna — Building and Leading a Team (Best)**
As co-founder and lead engineer, you were the face of the company — pitching clients, architecting solutions, AND building the team. You assembled like-minded freelancers into a guild that delivered high-quality work for Intuit, JLL, McDonald's, and others.

- *TSE frame:* "At Opna, I built the team from scratch. I was the first to meet every new client and the solution architect for every contract, but more importantly I had to identify and bring on engineers who could execute independently in very different technical contexts — one month Dialogflow microservices for JLL, the next vanilla JS widgets for Intuit. I learned that the best engineers aren't the ones with the longest skill lists; they're the ones who learn quickly and communicate well. That's a lesson I carry into every team I join."

**Story B: Closing notes mention mentoring**
"I love pairing, mentoring, and raising the quality bar." Have a specific example ready — a time you mentored someone and it changed their trajectory or improved the team.

---

### 6. Stay Curious

> "Learning about business operations and global dynamics drives organizational energy. Perpetual discovery excitement."

**Your strongest stories — this is your superpower:**

**Story A: Career Arc (Best for Experience & Goals)**
CNC machinist → music degree at UCSC → Max/MSP audio-reactive lighting → TouchDesigner/GLSL installations for Facebook/Instagram → Hack Reactor bootcamp → full-stack engineering → AI/ML platforms. This is one of the most curiosity-driven career paths I've seen.

- *TSE frame:* "My path to software engineering started with a Max/MSP program that triggered lighting changes based on musical events. I was a music student who got curious about how computers could respond to sound in real-time. That curiosity led me to build interactive installations for Facebook and Instagram's live events, then to a coding bootcamp, then to building production systems at scale. I'm still driven by the same impulse — my most recent personal project is a TinyML system that trains a neural network to detect beats in music and drive LED patterns on a microcontroller. I never stopped being curious about the intersection of hardware and software, audio and visuals, humans and machines."
- *Principle connection:* This isn't performed curiosity. It's your actual life pattern.

**Story B: Blinky Time — TinyML Project**
A custom causal CNN (9K params, INT8 quantized to ~20KB) for real-time beat detection on a Cortex-M4F microcontroller. This is absurdly deep for a personal project. It shows you learn for the joy of learning.

**Story C: Personal Projects Breadth**
Job Finder (AI/ML, LiteLLM, embedding-based deduplication), Imagineer (Stable Diffusion, multi-LoRA stacking), App Monitor (autonomous AI agents with 7-phase task lifecycle). Each explores a completely different technical domain.

---

## Interview-Specific Recommendations

### Programming Exercise (1 hr) — No behavioral content, but demonstrate principles through actions

- **Move with Urgency:** Manage your time visibly. "I have 15 minutes for Part 1, let me start with the data structure."
- **Create with Craft:** Use descriptive variable names. Extract helper functions. Your code IS your craft.
- **Collaborate Egolessly:** Treat the interviewer as a collaborator. Ask clarifying questions. Incorporate suggestions.

### Integration Exercise (1 hr) — Your strongest round

You have literally done this job. Lean into it:
- "At Fulfil, I integrated with Stripe for payment processing, Doordash and Uber Eats for marketplace orders, and Amazon Fresh for grocery fulfillment. I'm very comfortable reading API documentation and writing integration code."
- If you encounter an unfamiliar library or API pattern, say: "This reminds me of when we integrated with Amazon's event-based system — let me read the docs first before jumping in."

### Bug Squash (1 hr) — Draw on your observability experience

- The structured logging refactor at Fulfil proves you can navigate unfamiliar systems and debug systematically.
- "I migrated our entire observability stack, which required me to trace through every logging path in the codebase to restructure it." — This is exactly the Bug Squash skill.

### Behavioral (45 min) — Story Selection Strategy

For **User First & Curious**, lead with:
1. **Partner dashboards** — proactively building monitoring for partners (User First)
2. **Career arc** — music → installations → engineering → AI/ML (Stay Curious)
3. **Blinky Time** — TinyML beat detection as a personal project (Stay Curious depth)

For **Experience & Goals**, lead with:
1. **Fulfil → Amazon Fresh integration** — your most technically complex, cross-functional project
2. **Unified ordering API** — demonstrates design thinking and abstraction
3. **Why Stripe/TSE:** "I've been the developer integrating with partner APIs my entire career. I've felt the friction firsthand — confusing docs, opaque error messages, missing edge cases. I want to be on the other side of that, making the integration experience excellent for developers who are where I've been."

---

## The "Why Stripe? Why TSE?" Answer

Synthesize from your actual experience:

> "I've spent my career building integrations — Stripe, Doordash, Uber Eats, Amazon Fresh. I know what it's like to be the developer reading the docs at 11pm trying to figure out why a webhook isn't firing or why an order status isn't updating. The best integrations I've worked with were the ones where the partner's support team actually understood the technical problems and could help me debug in my own language and context. That's what I want to do at Stripe. I want to be the person who makes another developer's integration experience great — because I've been that developer, and I know what good support looks like from the receiving end."

This is authentic, specific, and directly maps your experience to the role.

---

## Stories to Avoid or Handle Carefully

- **CNC machinist / Wentworth Precision** — Don't hide it, but don't lead with it. If asked about your background, it's great color for the "Stay Curious" arc. Don't volunteer it unprompted in a technical discussion.
- **Meow Wolf** — Short tenure (4 months). Only mention if specifically asked about React or pub/sub experience. Don't make it a featured story.
- **Type 1 diabetes** — Powerful for demonstrating resilience and composure under pressure, but only share if the conversation naturally leads there (e.g., "what shaped who you are?"). Don't use it to explain gaps or challenges unless asked directly.
- **Closing notes say "Will not relocate" and "Will not work outside 8am-8pm Pacific"** — Don't volunteer constraints. If asked, state them matter-of-factly. The TSE role is listed as remote.

---

## Cheat Sheet: One Story Per Principle

Keep this list handy for quick reference. Each story is distinct (no repeats):

| Principle | Story | 2-Sentence Version |
|-----------|-------|--------------------|
| **Users First** | Partner monitoring dashboards | "I realized our marketplace partners couldn't see system health during peak load. I proactively built custom Grafana dashboards for each partner, cutting their support requests and building trust." |
| **Craft & Beauty** | Unified ordering API | "Three marketplace partners, three different protocols. I designed one clean abstraction that made onboarding the fourth partner take weeks instead of months." |
| **Urgency & Focus** | Fulfil startup growth (employee 98 → Amazon/Doordash/Uber) | "I joined a 98-person startup with zero paying customers. Three years later we were running automated grocery fulfillment for Amazon Fresh across three states." |
| **Collaborate Egolessly** | Amazon Fresh year-long integration | "We spent a year co-designing an event architecture with Amazon's team. The key was treating their strict requirements as our shared problem, not a burden." |
| **Obsess Over Talent** | Building Opna's engineering guild | "I assembled a team of independent engineers into a consulting guild and led solution architecture across clients like Intuit and McDonald's." |
| **Stay Curious** | Career arc + Blinky Time TinyML project | "I went from music student to CNC machinist to interactive installations to full-stack engineering. My latest project trains a neural network to detect beats in music on a microcontroller." |
