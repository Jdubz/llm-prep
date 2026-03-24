# Users First & Curious — Tyler Martin

**1:30 PM – 2:15 PM (45 min)**

Tyler evaluates two specific Stripe operating principles: your ability to put users first and your intellectual curiosity. Every story should hit one or both.

## What Tyler Evaluates

- User-centric approach
- Curiosity

## What To Expect

From Stripe's prep doc: "Think about specific situations where you designed solutions with the user in mind, took initiative to understand user needs, and moments when you learned something new or adjusted your approach based on new insights."

This is NOT a rehash of Ali's round. Tyler and Ali compare notes. **Zero story overlap.**

## Your Lead Stories

**Do NOT reuse these from Ali's round.**

| Story | Principle | Key Points | Target Time |
|---|---|---|---|
| **Partner monitoring dashboards** | Users First | Proactively built Grafana dashboards for each partner, cut support requests | 2 min |
| **Career arc** | Curious | CNC machinist → music → installations → engineering → AI/ML | 2 min |
| **Blinky Time TinyML** | Curious | Custom CNN, 9K params, INT8 quantized, beat detection on Cortex-M4F | 2 min |
| **Consumer ordering app** (backup) | Users First | Two user populations, designed interface to serve both | 2 min |

## Common Questions

- "Tell me about a time you designed a solution starting from the user's perspective"
- "Tell me about a time you proactively identified a UX issue nobody asked you to fix"
- "Tell me about a time you went deep on something out of pure curiosity"
- "Describe a time you changed your mind after learning new information"
- "Tell me about a time you adjusted your approach based on new insights"
- "Tell me about a time you went above and beyond for a customer or end user"

## Questions to Ask Tyler

Pick 2-3:

- [ ] "How does Stripe keep 'Users First' alive in practice — in daily decisions, not just hiring?"
- [ ] "What's the most interesting support case you've seen recently?"
- [ ] "If you could change one thing about how Stripe works, what would it be?"

---

## Story Bank

For each prompt, write a STAR story. Have at least 4 distinct stories across these 6 prompts.

### Story 1: Designing from the user's perspective

*"Tell me about a time you designed a solution starting from the user's perspective rather than the technical architecture."*

```
Situation:
"Our roboticized warehouses hit a hard throughput ceiling at 90% capacity — orders would start backing up, but we couldn't reproduce the problem without disrupting real customer orders." 

Task:
I was asked to build an automated test order generator based on an existing spec. But the spec inherited the same limitations the team was already struggling with.

Action:
After reviewing the spec I realized that the tool spec was simply an extension of our existing test order system, and would likely inherit the same shortfalls that the warehouse team was already experiencing. I needed to dig deeper into the actual problems and how the team is using the testing tooling day to day. I interviewed a few of the actual users and discovered that the recipes needed to be able to target the actual bottlenecks which were physical space and pathing issues, and could not be targeted with the existing ordering paradigm which was built for the consumer order app (grocery categories), not for the robotics team to search by real world location. I pivoted to designing a new order generation system where they could search for items by physical location and create test order batches specifically to challenge the pathing algorithms.

  1. "I read the spec and realized it was just the existing test system with a cron job" (you questioned  
  the requirement)
  2. "I interviewed the robotics team and discovered they needed to target physical locations, not grocery
   categories" (you went to the user)                                                                     
  3. "I designed a new order generator where they could search by physical location and create batches 
  targeting specific pathing challenges" (you built what they actually needed) 

Result:
Through the use of this new test order approach the robotics team was able to eliminate the critical performance drop at 90% capacity, it also doubled overall throughput of the system. The services I developed for that new order generation approach then became the basis for many of the operator dashboards moving forward as it was designed for the real users of that system, not the consumers on the other end who needed a very different product.

Curiosity Angle — What did you learn about the user that surprised you?
The robotics team tended to think in terms of the tools they were given, as opposed to what is actually possible. They were very talented engineers and used the cloud tooling day to day, so I had assumed that they had a better understanding of the data structures and what was possible. It turns out they are hyper focused on the hardware in front of them, and didnt know what they could actually ask for.
```

### Story 2: Proactive UX/DX improvement

*"Tell me about a time you proactively identified a UX or developer experience issue nobody asked you to fix."*

```
Situation:
Our item error rate was 1 in 20 and operators couldn't trace what went wrong because the order management UI was essentially useless.

Task:
The self-assigned task was to make this critical page actually useful. I was the primary developer supporting the order management UI. When I inherited it there were only a few properties exposed and they were mislabeled and error prone.

Action:
I analyzed and traced the 2 data systems that were represented and conflated in the UI. There was the state of the order in the system itself, internal and stored in mongoDB on-prem. Then there was the state of the order in the cloud system, external and stored in MySQL.
First I separated the data sets into different columns to clarify what was internal machine state, and what was consumer facing. Previously the "status" of the order was constantly confused and miscommunicated because operator had no way to tell the statuses apart.
Secondly I discovered that we were already storing an audit trail for every operation on an order record in the cloud system. I added an order history UI that also connected to system logs and factory events. It clearly showed what happened and when, and easily linked to deeper system information.

Result:
The operators were immediately able to produce a list of detailed error reports. What happened, when, why, and how to reproduce. This was basically impossible before. It enabled the robotics team to cut the item error rate in half in the first month. The little history widget was called out for being the highest impact surprise feature that quarter at the company all-hands.

Curiosity Angle — How did you notice the problem? What made you dig in?
I was trying to help the operators troubleshoot issues with orders. They often blamed the cloud system for data discrepancies and it was a challenge to find evidence either way. I noticed that I didn't really understand the difference between the 2 "order" entities and decided that this was an important distinction to make in the UI.
```

### Story 3: Learning from a user interaction

*"Tell me about a time you learned something unexpected from a user, customer, or stakeholder interaction."*

```
Situation:
_____________________________________________________________

Task:
_____________________________________________________________

Action:
_____________________________________________________________
_____________________________________________________________

Result:
_____________________________________________________________

What assumption did this break? How did it change your approach?
_____________________________________________________________
```

### Story 4: Balancing user needs against constraints

*"Tell me about a time you had to balance what the user wanted against what was technically feasible."*

```
Situation:
_____________________________________________________________

Task:
_____________________________________________________________

Action:
_____________________________________________________________
_____________________________________________________________

Result:
_____________________________________________________________

How did you figure out what the user actually needed vs. what they asked for?
_____________________________________________________________
```

### Story 5: Going deep out of curiosity

*"Tell me about a time you went deep on something out of pure curiosity — not because anyone asked you to."*

```
Situation:
The engineering team had decided that Elastic no longer met our needs as a logging platform. It only captured 60-80% of the logs, and became cost prohibitive at the scale that we needed. The on-prem warehouse systems generated a massive amount of logs and metrics.

Task:
I was tasked with refactoring the logging service in the cloud API to be compatible with Grafana / Loki / Prometheus (Promtail). The original ask was merely to get it working so that 100% of our logs were captured and searchable.

Action:
During the refactor I noticed that a significant number of our logs were unstructured strings, and encoded line breaks in json structures, making the bulk of the log searches disconnected and difficult to organize. In order to properly leverage the power and composability of Grafana dashboards the logs needed to be JSON structured with predictable keys.
I took the time to add additional optional arguments to the logging service. These were backwards compatible, and offered searchable fields, enabling custom dashboards for specific tasks and users. Including partners using our systems.

Result:
After re-organizing and de-duplicating logger calls I reduced log volume by 60%, while greatly increasing observability. The developers took a minute to get used to the new log format, but quickly cut the time to resolution in half for most issues. The Grafana dashboards quickly became a key feature that all engineers and operators were trained on.

What sparked the curiosity? Where did it lead you that you didn't expect?
When some of the most powerful features of the Grafana stack were difficult or impossible to implement I knew that there was a deeper issue with our logging beyond the logging service and ingestion pipeline. I did not expect to be training the rest of the team on logging best practices and advocating for migrating away from deprecated formats. Some of the old habits went deep in the team, but they quickly came around once they experienced the observability improvements.
```

### Story 6: Changing approach based on new information

*"Tell me about a time you changed your approach based on new information, and it led to a better outcome."*

```
Situation:
_____________________________________________________________

Task:
_____________________________________________________________

Action:
_____________________________________________________________
_____________________________________________________________

Result:
_____________________________________________________________

What made you willing to change course rather than sticking with your plan?
_____________________________________________________________
```

---

## Self-Check

- [ ] I have at least 4 distinct stories across the 6 prompts above
- [ ] Each story is under 2 minutes when told out loud
- [ ] At least 2 stories demonstrate BOTH user empathy AND curiosity
- [ ] NONE of these stories overlap with what I'm telling Ali
- [ ] Each story has a concrete result (numbers, outcomes, user feedback)
- [ ] I've practiced these stories OUT LOUD, not just written them
