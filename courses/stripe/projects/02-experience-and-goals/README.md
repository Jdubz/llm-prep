# Experience & Goals — Ali Riaz

**11:45 AM – 12:45 PM (60 min)**

This is a full hour. Ali will go deep on your projects. Expect follow-up questions on architecture decisions, trade-offs, what you'd do differently, and how your work impacted others.

## What Ali Evaluates

- Career fit
- Communication
- Work experience

## What To Expect

From Stripe's prep doc: "You and the interviewer will discuss one of the more technically challenging projects you've worked on (ideally a project you've led). You will also discuss what you're looking for in your next role."

Sample topics:
- A technically challenging project and how you approached it
- A technical contribution that allowed others to be successful
- A cross-functional project

Use STAR+R format (Situation, Task, Action, Result, Reflection).

## Your Lead Stories

**Do NOT reuse these in Tyler's round.**

| Story | Key Points | Target Time |
|---|---|---|
| **Amazon Fresh integration** | Year-long, two companies, co-designed event architecture, shared problem framing | 3 min |
| **Unified ordering API** | 3 partners, 3 protocols, one abstraction, 4th partner onboarded in weeks | 2 min |
| **Structured logging refactor** | Elastic → Grafana/Loki, 60% cost reduction, better DX, PagerDuty/Slack | 2 min |

## "Why Stripe? Why TSE?"

Ali will ask this. Have it ready:

> "I've spent my career building integrations — Stripe, Doordash, Uber Eats, Amazon Fresh. I know what it's like to be the developer reading the docs at 11pm trying to figure out why a webhook isn't firing. The best integrations I worked with were the ones where the partner's support team actually understood the technical problems and could help me debug in my own language and context. That's what I want to do at Stripe."

## Common Questions

- "Describe a technically challenging project and how you approached it"
- "Tell me about a time you disagreed with a team decision"
- "Tell me about a time you made a mistake. What did you learn?"
- "What's the hardest bug you've ever debugged?"
- "What are you looking for in your next role?"
- "Tell me about a technical contribution that allowed others to be successful"
- "Describe a project that was very cross-functional"

## Questions to Ask Ali

Pick 2-3:

- [ ] "Can you tell me about a TSE who has grown significantly in the role?"
- [ ] "When a TSE identifies a bug or API design issue through support, what does the path to getting it fixed look like?"
- [ ] "What's the biggest challenge facing the TSE team right now?"
- [ ] "What does the path from TSE to senior TSE look like?"

---

## Project Deep Dive Worksheet

Prepare 2-3 projects. Fill in every field — Ali will ask follow-ups on anything you leave blank.

### Project 1

```
Project Name: Amazon integration
One-sentence summary: Built a real-time event pipeline between Fulfil's warehouse system and Amazon's fulfillment network — hundreds of pub/sub events tracking every item state change across two incompatible data models, with a hard launch deadline."
Your role: Owner of the order/item event pipeline. Point of contact with AZ's integration team for event spec alignment.
Duration: 1 year
Team size: Fulfil: 15 AZ: 10+ (exact number unknown)

TECHNICAL ARCHITECTURE
What was the system?
We created an event based system to alert AZ of every change of every item in every order. It used Webhooks to recieve new orders, then pub/sub to send messages on hundreds of discreet events, tracking both AZ ids and Fulfil Ids. 

Key technical decisions you made or influenced:
1. How are order lifecycle events managed and reconciled between our system and their system.
2. How do we communicate inventory changes in real time, specifically concerning upcoming orders.
3. How do we recover from real-world problems elegantly? Bad/broken items, etc.
  - "Chose pub/sub over polling for order lifecycle events because AZ required sub-second state sync and
  our order volumes would spike 10x during peak hours"
  - "Designed dual-ID tracking (AZ ID + Fulfil ID) per item because the two systems had fundamentally
  different identity models"
  - "Implemented idempotent event delivery with retry + reconciliation because dropped events would cause
  AZ's inventory counts to drift"


THE CHALLENGE
What made this hard?
Two companies with incompatible data models building simultaneously against a 20-page spec with ambiguous requirements agains an immovable deadline.

What constraints did you face?
The go live date was set in stone. A hard project dependency. We also had to guarantee that all events lined up to represent the state of the system EXACTLY, meaning event ids with retrys and reconciliation on failed delivery.

What trade-offs did you make? What did you sacrifice and why?
With an overwhelming number of requiements, some inherrently incompatible, we had to work very closely to figure out how how we could deliver a best effort product within the timeline, and at least gave a path to completion for the requirements that didn't fit. For example labor planning tools around predicted order backlogs. Our system worked in real time to figure out what neededto got where in the moment, and had no future planning capabilities as the hardware was not aware of scheduled and queued orders until ther were being fulfilled, so there was no mechanism for predicting order arrival locations.

"We sacrificed: predictive labor planning (our system was real-time, no scheduled order awareness). We kept: exact event-level consistency (non-negotiable for AZ). Why: the hard deadline meant we couldn't build a forecasting system, but if events were wrong, the entire integration was worthless."

YOUR CONTRIBUTION
What did YOU specifically do? (not the team — you)
I implemented hundred of order and item pubsub events according to the AZ spec. This meant structuring the data pipeline in a way to not knock over our DB instances on massive R/W spikes when order volumes were high.
— how? What was technically hard? The DB scaling mention is the most
  interesting part and it's one sentence. Expand: what was the R/W spike pattern? What did you do about
  it? Batch writes? Queue backpressure? Read replicas?

How did you enable others?
I worked closely with the AZ team and Fulfil leadership to helped to develop a mutual understanding of the delta between the spec and the existing system with enough technical detail to brainstorm workarounds and compromises without overloading on implementation specifics.

What was the measurable outcome/impact?
We launched the product on time. AZ immediately ordered 3 more stores. 

LESSONS LEARNED
What would you do differently?
I would have abstraced the data lifecycle and event factories to a seperate service that could scale independently of the API monolith.

What did this project teach you that you still carry?
How to dig into the why of a requirement beyond the language in the line item on a document. 

TSE RELEVANCE
How does this project relate to the TSE role at Stripe?
I supported AZ in implementing our eventing system and API as we developed it. We collaborated on the spec, then built simultaneously, and discovered that every time language wasn't perfectly specific we would end up with 2 different interpretations.
"This was essentially a TSE role — I was the technical bridge between our API team and AZ's integration engineers. I learned that every ambiguous sentence in a spec produces two different implementations, and that the TSE's job is to catch those gaps before they become production bugs."
```

### Project 2

```
Project Name: _______________________________________________
One-sentence summary: ______________________________________
Your role: __________________________________________________
Duration: ___________________________________________________
Team size: __________________________________________________

TECHNICAL ARCHITECTURE
What was the system?
_____________________________________________________________
_____________________________________________________________

Key technical decisions:
1. ___________________________________________________________
2. ___________________________________________________________
3. ___________________________________________________________

THE CHALLENGE
What made this hard?
_____________________________________________________________

What constraints did you face?
_____________________________________________________________

What trade-offs did you make?
_____________________________________________________________

YOUR CONTRIBUTION
What did YOU specifically do?
_____________________________________________________________
_____________________________________________________________

How did you enable others?
_____________________________________________________________

What was the measurable outcome/impact?
_____________________________________________________________

LESSONS LEARNED
What would you do differently?
_____________________________________________________________

What did this project teach you?
_____________________________________________________________

TSE RELEVANCE
How does this relate to the TSE role?
_____________________________________________________________
```

### Project 3 (optional)

```
Project Name: _______________________________________________
One-sentence summary: ______________________________________
Your role: __________________________________________________
Duration: ___________________________________________________
Team size: __________________________________________________

What was the system? _________________________________________
What made it hard? ___________________________________________
What did YOU do? _____________________________________________
Measurable impact? __________________________________________
What would you do differently? _______________________________
TSE relevance? ______________________________________________
```

---

## "Why" Questions

Write your answers now. If you can't write them, you'll stumble when asked.

**Why Stripe?**
```
_____________________________________________________________
_____________________________________________________________
_____________________________________________________________
```

**Why TSE specifically (not SWE, not product, not sales)?**
```
_____________________________________________________________
_____________________________________________________________
_____________________________________________________________
```

**What are you looking for in your next role?**
```
_____________________________________________________________
_____________________________________________________________
_____________________________________________________________
```
