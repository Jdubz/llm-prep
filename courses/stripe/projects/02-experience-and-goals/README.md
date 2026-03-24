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
We created an event based system to alert AZ of every change of every item in every order. It used Webhooks to receive new orders, then pub/sub to send messages on hundreds of discrete events, tracking both AZ ids and Fulfil Ids. 

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
Two companies with incompatible data models building simultaneously against a 20-page spec with ambiguous requirements against an immovable deadline.

What constraints did you face?
The go live date was set in stone. A hard project dependency. We also had to guarantee that all events lined up to represent the state of the system EXACTLY, meaning event ids with retries and reconciliation on failed delivery.

What trade-offs did you make? What did you sacrifice and why?
With an overwhelming number of requirements, some inherently incompatible, we had to work very closely to figure out how we could deliver a best effort product within the timeline, and at least gave a path to completion for the requirements that didn't fit. For example labor planning tools around predicted order backlogs. Our system worked in real time to figure out what needed to go where in the moment, and had no future planning capabilities as the hardware was not aware of scheduled and queued orders until they were being fulfilled, so there was no mechanism for predicting order arrival locations.

"We sacrificed: predictive labor planning (our system was real-time, no scheduled order awareness). We kept: exact event-level consistency (non-negotiable for AZ). Why: the hard deadline meant we couldn't build a forecasting system, but if events were wrong, the entire integration was worthless."

YOUR CONTRIBUTION
What did YOU specifically do? (not the team — you)
I implemented hundreds of order and item pubsub events according to the AZ spec. This meant structuring the data pipeline in a way to not knock over our DB instances on massive R/W spikes when order volumes were high.
— how? What was technically hard? The DB scaling mention is the most
  interesting part and it's one sentence. Expand: what was the R/W spike pattern? What did you do about
  it? Batch writes? Queue backpressure? Read replicas?

How did you enable others?
I worked closely with the AZ team and Fulfil leadership to develop a mutual understanding of the delta between the spec and the existing system with enough technical detail to brainstorm workarounds and compromises without overloading on implementation specifics.

What was the measurable outcome/impact?
We launched the product on time. AZ immediately ordered 3 more stores. 

LESSONS LEARNED
What would you do differently?
I would have abstracted the data lifecycle and event factories to a separate service that could scale independently of the API monolith.

What did this project teach you that you still carry?
How to dig into the why of a requirement beyond the language in the line item on a document. 

TSE RELEVANCE
How does this project relate to the TSE role at Stripe?
I supported AZ in implementing our eventing system and API as we developed it. We collaborated on the spec, then built simultaneously, and discovered that every time language wasn't perfectly specific we would end up with 2 different interpretations.
"This was essentially a TSE role — I was the technical bridge between our API team and AZ's integration engineers. I learned that every ambiguous sentence in a spec produces two different implementations, and that the TSE's job is to catch those gaps before they become production bugs."
```

### Project 2

```
Project Name: Unified ordering abstraction layer
One-sentence summary: Built an abstraction layer to unify 3 marketplace order pipelines (Fulfil, Uber Eats, DoorDash) behind a single management interface, enabling new source onboarding in days instead of weeks.
Your Role: Feature Owner. I designed, gathered stakeholder feedback, implemented, and tested the feature from start to finish, then supported after production deployment.
Duration: 1 month
Team size: 3 Engineers

TECHNICAL ARCHITECTURE
What was the system?
3 sources: Fulfil order PWA, Uber Eats, Doordash. Each system used a different combination of webhooks, API requests, last mile delivery mechanisms, payment processing, and customer communication. We needed a DRY way to manage all order pipelines and onboard new ones.

Key technical decisions:
1. While a complete abstraction layer allowing for source onboarding with only a new source config record would be ideal, there were enough unique needs to make that implausible. Unique webhooks and status update APIs, battle tested code, and inventory syncing that a branching central pipeline with hardcoded switches based on order properties was the only feasible solution. 
2. Creating a new table for each source to record the original order placement was necessary vs simple logging for sql searchability. 
3. The order pipeline required enough references to the unique source properties that our internal order schema was extended with a polymorphic foreign key vs. normalizing all properties.

THE CHALLENGE
What made this hard?
Each source had many unique features that the consolidated pipeline had to support. Some required async queue job processing, some required scheduled orders up to a week ahead of time, some required us to manage the payment and delivery. Each feature had to be abstracted to allow switching based on order data to guarantee proper handling of each order.

What constraints did you face?
Some internal systems required properties that some sources did not provide. We had to normalize data that didn't exist and assign meaningful values in its place. 

What trade-offs did you make?
Each source's code would have been much simpler if we simply hardcoded the steps to support each individually. The headache that would have caused would surface during the rapid iteration in our system. A change in our system would have meant changes to all code paths.

YOUR CONTRIBUTION
What did YOU specifically do?
I wrote the abstraction layer and created the new data schemas to normalize the properties required by our systems. I also tested and supported all 3 implementations.

How did you enable others?
This abstraction allowed for the AZ integration to happen smoothly and efficiently. Very little new code or changes to our internal order management had to be made to support an entirely new order marketplace.

What was the measurable outcome/impact?
Logging, debugging, order tracking, and management was all consolidated behind a single dashboard that was able to handle all issues from all order sources uniformly. Previously 3 operators were required, 1 for each source, after 1 could handle a standard order volume. implementing the new AZ source only took a few days where the previous implementations took multiple weeks.

LESSONS LEARNED
What would you do differently?
One of the sources originally required the initial creation to sit behind a queue job, so we implemented that pattern across all 3 sources. This created difficulties in log tracing, each job was a new trace and log source separated from the original order request. It also complicated the mental model when tracing the code path.

What did this project teach you?
There is a balance to be maintained between abstraction and simplicity. Overly abstracted code, while composable, can be difficult to troubleshoot and debug.

TSE RELEVANCE
How does this relate to the TSE role?
I've been on the implementation side of public APIs enough times to know the headaches that come with dependence on a vendor's product for business critical operations and how important timely support is. 
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
I have experience with the Stripe API. It's design is clean and obvious. Clear documentation, predictable and helpful error patterns, and reliable webhooks. I want to learn what goes into achieving such an elegant public api. I also admire the culture and reputation that Stripe has achieved as a company, I believe I can contribute happily where Stripe is clearly putting in the effort to have a positive impact.
```

**Why TSE specifically (not SWE, not product, not sales)?**
```
I have been on the other side of the fence, debugging at the last minute under a time crunch, and want to be able to support and enable others in the struggle I've personally faced. I enjoy being people focused and want to be able to interact with the real users that our product is impacting.
```

**What are you looking for in your next role?**
```
It's enticing to have my primary KPI be quantifiable day-to-day. I want to have a clear, measurable impact through the developers I've helped, not just peer review cycles. I'm looking for mentorship, cross-functional
  exposure beyond pure engineering, and a team that takes craft seriously.
```
