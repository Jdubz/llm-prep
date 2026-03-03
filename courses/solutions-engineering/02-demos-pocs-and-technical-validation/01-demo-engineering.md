# 01 -- Demo Engineering

The demo is the single most important touchpoint in the SE sales cycle. It is the moment where the prospect stops reading about your product and starts seeing it. A great demo converts skeptics into champions. A bad demo loses deals that were otherwise winnable. This file covers everything: narrative structure, audience adaptation, environment prep, live coding, failure recovery, and the anti-patterns that kill demos.

---

## Demo Narrative Arc

Every effective demo follows a narrative arc. You are not walking through a feature list — you are telling a story where the prospect is the main character and your product is the solution to their problem.

### The Five-Act Structure

```
1. Hook (0:00 - 0:30)    → Capture attention with a provocative insight or outcome
2. Context (0:30 - 2:00)  → Frame the business problem (their problem, not your product)
3. Solution (2:00 - 15:00) → Walk through features mapped to their specific pain points
4. Wow Moment (15:00-18:00)→ The "aha!" — the thing they cannot do today
5. Close (18:00 - 20:00)  → Recap value, propose next steps
```

### Act 1: The Hook (First 30 Seconds)

The hook determines whether the audience pays attention for the next 20 minutes or starts checking email. It must be provocative, relevant, and short.

**Effective hook patterns:**

| Pattern | Example |
|---------|---------|
| Provocative statistic | "Your data team spends 40% of their week on pipeline maintenance. We're going to show you how to get that to under 5%." |
| Mirror their pain | "Last week you mentioned that a single schema change takes your team 3 days to propagate. Let me show you what that looks like in 30 seconds." |
| Outcome-first | "By the end of this demo, you'll see how Company X reduced their data ingestion errors by 90% — and they had the same stack you have." |
| Contrast | "Here's what this workflow looks like today [show their pain]. Now here's what it looks like with us." |

**Bad hooks:** "So let me just walk you through our platform..." or "Thanks everyone, let me share my screen and we'll get started with an overview of our product." These are not hooks. They are invitations to tune out.

### Act 2: Context (Business Problem Framing)

After the hook, frame the business problem you are solving. This is not a recap of your discovery call — it is a concise restatement that confirms you understood them.

```
"Based on our conversation last week, your team is dealing with three main challenges:
1. Schema changes in upstream systems break your dashboards weekly
2. Your data engineers spend most of their time on maintenance, not new projects
3. When something breaks, it takes hours to identify the root cause

Today I want to show you how we address each of these. Let me start with the one
you said was most painful — the schema change problem."
```

This accomplishes three things: it proves you listened, it gives them a chance to correct or reprioritize, and it sets the agenda so they know what to expect.

### Act 3: Solution Walkthrough (Features Mapped to Pain)

The solution walkthrough is the core of the demo. Each segment should follow this pattern:

```
Pain Point → Feature → Live Demonstration → Business Outcome
```

**Example for a data platform:**

| Pain Point | Feature Shown | Outcome Stated |
|------------|---------------|----------------|
| Schema changes break pipelines | Auto-schema evolution | "No more 3am pages when upstream changes a column type" |
| Root cause analysis takes hours | Data lineage graph | "Click once and see exactly which upstream change caused which downstream failure" |
| New data sources take weeks to onboard | No-code connectors | "Your analysts can add a new source in 15 minutes without filing an engineering ticket" |

**The "show, don't tell" principle:** Never say "our platform is really fast" — show a query executing in 200ms. Never say "our UI is intuitive" — let them watch you accomplish a task without explaining the UI. Never say "it's easy to set up" — set it up live in front of them.

**Pacing:** Spend 60-70% of the solution time on the prospect's top pain point. If you have three pain points, the split might be 60/25/15. Do not try to show everything.

### Act 4: The Wow Moment

The wow moment is the thing the prospect cannot do today, shown in a way that makes them say "wait, it can do that?" This is not your biggest feature — it is the feature that creates the widest gap between their current reality and what is possible.

**Characteristics of a great wow moment:**
- It solves a problem they thought was unsolvable or too expensive to solve
- It happens live, not on a slide
- It is visually dramatic (a graph updating in real-time, a pipeline building itself, a report generating instantly)
- It connects directly to money, time, or risk

**Example:** "Now watch this — I'm going to break the schema on purpose [changes a column type in the source database]. See that alert? The pipeline already detected it, automatically mapped the new type, and your dashboard didn't skip a beat. Zero downtime. Zero engineering time."

### Act 5: Close

The close is not a summary slide. It is a direct conversation about next steps.

```
"We covered three things today:
1. Auto-schema evolution eliminates your weekly dashboard breakages
2. Data lineage cuts your root cause analysis from hours to seconds
3. No-code connectors let analysts self-serve new data sources

Based on what you've seen, does this address your top priorities?
[Pause — let them respond]

Here's what I'd suggest as a next step: a focused POC on schema evolution
with your actual data sources. We can have that running in two weeks.
What does your team's availability look like?"
```

### Example Narrative Arc: SaaS Data Platform Demo

```
HOOK:     "Your team told us schema changes are their #1 pain. In the next
           15 minutes, I'll break a schema live and show you zero-impact
           recovery."

CONTEXT:  "You're running Airflow + dbt + Snowflake. Schema changes upstream
           break 3-4 dashboards per week. Your 6-person data team spends
           Monday mornings firefighting instead of building."

SEGMENT 1 (60%): Auto-schema evolution
  - Show a live data source with a defined schema
  - Change a column type in the source
  - Watch the platform detect, adapt, and continue processing
  - Show the alert and audit log
  - Outcome: "No broken dashboards. No engineering ticket. No 3am page."

SEGMENT 2 (25%): Data lineage and root cause
  - Click on a dashboard metric
  - Trace lineage back through transformations to raw source
  - Show impact analysis: "If this source changes, these 12 dashboards
    are affected"
  - Outcome: "Root cause in seconds instead of hours."

SEGMENT 3 (15%): Self-serve connectors
  - Walk through adding a new Salesforce data source
  - Show the no-code mapping interface
  - Outcome: "Analysts do this themselves. No engineering backlog."

WOW:      Break the schema live. Show zero-impact recovery in real time.

CLOSE:    Recap three outcomes. Propose a 2-week POC on schema evolution
          with their actual Airflow + Snowflake stack.
```

---

## Audience Adaptation

The same product looks completely different to an executive, an architect, a developer, and an end user. You must adapt your demo for each audience — or lose them.

### Audience Adaptation Matrix

| Dimension | Executive (VP/C-level) | Architect | Developer | End User |
|-----------|----------------------|-----------|-----------|----------|
| **Demo focus** | Business outcomes, ROI, risk reduction | Architecture, integration, scalability, security | API, SDK, code samples, developer experience | Workflows, UX, daily tasks |
| **Duration** | 2-5 minutes | 20-30 minutes | 30-45 minutes (with live coding) | 15-20 minutes |
| **Depth** | Surface — outcomes only | Deep — how it works under the hood | Deep — code level | Medium — task-oriented |
| **Language** | Business value, dollars, time saved | Protocols, patterns, SLAs, compliance | Languages, frameworks, endpoints, errors | Steps, clicks, features, shortcuts |
| **Questions they ask** | "What's the ROI? Who else uses this? What's the risk?" | "How does it scale? What's the failure mode? How does auth work?" | "Is there a Python SDK? What does the error response look like? Can I see the API docs?" | "Can I do X? How many clicks? Can I customize this view?" |
| **What impresses them** | Customer logos, metrics, time-to-value | Architecture diagrams, SLA numbers, security certifications | Clean API design, good docs, fast SDK setup | Simple workflows, good UX, keyboard shortcuts |
| **What loses them** | Technical detail, jargon, feature lists | Hand-waving about architecture, no diagrams | No code, no API examples, marketing language | Complexity, too many steps, poor UI |

### Handling Mixed Audiences

In practice, you rarely demo to a single audience type. A typical demo room has the VP who scheduled the meeting, two architects who will evaluate, and a developer who will do the POC.

**Strategy: Layer the demo.**

1. Start with the executive layer (2-3 minutes): business context, outcomes, customer proof points. The VP gets what they need early and can leave or stay.
2. Transition to the architect layer (10-15 minutes): architecture overview, integration patterns, security model. Show how the pieces fit together.
3. Go deep on the developer layer (10-15 minutes): live coding, API walkthrough, SDK demo. The developer sees enough to believe the POC will work.

**Signal to watch for:** When the VP starts checking their phone, you have been in the weeds too long. When the developer looks bored, you have been too high-level. Read the room and adjust.

**Explicit agenda:** "I want to make sure everyone gets what they need from this session. Sarah, I know you're focused on the business case — I'll cover that in the first few minutes. Tom and Raj, I'll get into the architecture and API details after that. Does that work for everyone?"

---

## Demo Environment Preparation

The demo environment is the most underrated element of a successful demo. A broken demo environment is worse than no demo at all — it destroys credibility.

### Building a Reliable Demo Environment

**Principles:**
1. **Isolation:** Your demo environment must be completely separate from production, staging, and any shared environments. Nobody else's changes should be able to break your demo.
2. **Determinism:** The same demo should produce the same result every time. No race conditions, no dependence on external services that might be down.
3. **Story data:** Your seed data should tell a story. Do not use test data with IDs like `user_123` and company names like `ACME_TEST`. Use realistic data that matches the prospect's industry.
4. **Reset speed:** You must be able to reset your demo environment to a known state in under 60 seconds.

### The "Golden Path"

The golden path is a pre-planned, tested route through your product that you follow during every demo. It is the sequence of clicks, commands, and screens that you know will work.

```
Golden Path Checklist:
□ Every click, command, and screen transition is documented
□ Every data point used in the demo is seeded and verified
□ Every API call has been tested within the last 24 hours
□ Every environment variable, credential, and connection string is current
□ Fallback screenshots/video exist for every segment
□ The golden path has been run start-to-finish within 4 hours of the demo
```

### Seed Data That Tells a Story

| Prospect Industry | Seed Data Theme | Example Entities |
|-------------------|----------------|------------------|
| Healthcare | Patient flow optimization | Regional hospital network, 3 locations, 50K patient records |
| Fintech | Transaction monitoring | Digital bank, 100K transactions, fraud detection alerts |
| E-commerce | Inventory and fulfillment | Online retailer, 5K SKUs, 3 warehouses, seasonal demand patterns |
| SaaS | Customer success metrics | B2B platform, 200 accounts, health scores, churn indicators |

### Environment Checklist (T-Minus Countdown)

| Timing | Action |
|--------|--------|
| T-24 hours | Run golden path end-to-end. Fix anything broken. |
| T-4 hours | Refresh seed data. Verify all API endpoints respond. Check credentials. |
| T-1 hour | Close unnecessary applications. Clear browser tabs. Set Do Not Disturb. Disable OS updates. |
| T-30 minutes | Open demo environment in browser. Pre-load all tabs. Test screen sharing. Check audio/video. |
| T-5 minutes | Run the first two steps of the golden path to warm caches. Position windows. |
| T-0 | Start with confidence. |

### When the Demo Environment Breaks

It will break. The question is not if, but when. Your response determines whether you win or lose the deal.

**Immediate options:**
1. **Acknowledge and redirect:** "Looks like our staging environment is having a moment. Let me show you this on our backup — same data, same workflow." Switch to screenshots or a pre-recorded video.
2. **Debug transparently (only if quick):** "Interesting — let me check something real quick." Only do this if you are 90% sure you can fix it in under 30 seconds. If not, go to option 1.
3. **Use it as a teaching moment:** "This is actually a great example of what happens when [relevant scenario]. In production, our monitoring would catch this and [explain recovery]."

---

## Live Coding in Demos

Live coding is the highest-risk, highest-reward demo technique. When it works, it is the most convincing proof that your product is real, usable, and developer-friendly. When it fails, it is painful for everyone.

### When to Live-Code vs Show Pre-Built

| Live-Code | Show Pre-Built |
|-----------|---------------|
| The prospect is a developer audience | The audience is non-technical |
| You need to prove the DX is real | The workflow is complex and time-consuming |
| The setup is fast (< 5 minutes) | Setup requires dependencies that could fail |
| You have practiced this exact sequence 10+ times | You have not done this exact sequence recently |
| The prospect specifically asked to see code | Nobody asked, and slides would suffice |

### Live Coding Best Practices

1. **Practice the exact sequence 10+ times.** Not "I know this works" — actually run it 10 times. Muscle memory prevents fumbling.
2. **Use a large font.** 18pt minimum for screen sharing. If people cannot read your code, you have lost them.
3. **Pre-type long strings.** Have snippets ready to paste for API keys, URLs, and complex configuration. Nobody wants to watch you type `https://api.example.com/v2/data-pipelines/config`.
4. **Narrate as you type.** "I'm importing our SDK... now I'll initialize the client with my API key... and here I'll define the schema." Silence during typing is dead air.
5. **Use a clean editor.** No distracting extensions, no notifications, no embarrassing autocomplete suggestions. A fresh VS Code profile for demos is worth the setup time.
6. **Have the "I prepared this earlier" escape hatch.** If something goes wrong mid-coding, have the completed version ready in a separate tab. "Let me jump to the finished version so we don't lose time — but you can see the pattern is the same."

### Common Live-Coding Pitfalls

| Pitfall | Prevention |
|---------|-----------|
| Typo breaks the code | Pre-type and paste complex strings. Practice the exact sequence. |
| Wrong environment activated | Check `which python` or equivalent before starting. Pin the correct terminal profile. |
| API key expired or missing | Verify credentials T-4 hours before demo. Have them in a `.env` file, not typed live. |
| Package not installed | Run `pip install` (or equivalent) in the prep window, not during the demo. |
| Network issues | Have a local fallback. Pre-cache API responses if possible. |
| Autocomplete shows embarrassing suggestions | Use a clean editor profile with history cleared. |

---

## Handling Demo Failures

The demo gods will smite you. It is not a matter of if, but when. The difference between a junior SE and a senior SE is not whether their demos break — it is how they recover.

### The Demo Recovery Framework

```
1. PAUSE    — Do not panic. Take a breath. The audience takes their cue from you.
2. ASSESS   — Is this fixable in 10 seconds? 30 seconds? Not quickly?
3. DECIDE   — Fix it live (< 10 seconds), switch to backup (> 10 seconds),
               or acknowledge and move on.
4. REDIRECT — Bridge back to the narrative. "Now, as I was showing you..."
```

### Recovery Options by Failure Type

| Failure Type | Recovery |
|-------------|----------|
| Page won't load | "Let me switch to our backup environment." Open pre-loaded backup tab. |
| API returns error | "Let me show you what the successful response looks like." Switch to pre-captured response. |
| Data looks wrong | "Looks like our test data was refreshed. Let me pull up the expected view." Show screenshot. |
| Live code won't run | "Let me jump to the completed version." Open pre-built file in adjacent tab. |
| Entire environment down | "I have a recorded walkthrough of exactly this flow. Let me play that." Switch to video. |
| Feature works differently than expected | "That's actually the new behavior in our latest release. Let me walk you through what changed." Buy time to figure out what happened. |

### What NOT to Do When a Demo Breaks

- **Do not apologize repeatedly.** One acknowledgment is fine. Repeated apologies make it seem bigger than it is.
- **Do not blame your team.** "Our DevOps team must have pushed something" is a terrible look.
- **Do not pretend it didn't happen.** If everyone saw the error, acknowledge it.
- **Do not spend 5 minutes debugging live.** After 30 seconds, switch to backup.
- **Do not skip the segment entirely.** Use a backup format to still show the capability.

---

## Virtual vs In-Person Demos

### Virtual Demo Best Practices

- **Share only the relevant window**, not your entire screen. Desktop notifications, Slack messages, and calendar reminders will appear at the worst possible moment.
- **Use a wired internet connection** when possible. WiFi drops at the worst times.
- **Disable notifications** on your OS, Slack, email, and phone. All of them.
- **Keep engagement high.** Ask a question every 3-5 minutes. "Does this match what you're seeing in your environment?" or "Is this the kind of workflow your team would use?"
- **Use the chat.** Post links, code snippets, and screenshots in the chat so people can follow along asynchronously.
- **Record the demo** (with permission) so absent stakeholders can watch later.
- **Check your camera and audio** before the call. Bad audio destroys credibility faster than any broken feature.

### In-Person Demo Best Practices

- **Arrive early.** Test the projector/screen, WiFi, and power. Every conference room has a different HDMI adapter situation.
- **Bring your own adapter, charger, and hotspot.** Do not rely on the customer's infrastructure.
- **Whiteboard before you screen-share.** Draw the architecture, the workflow, or the problem space on a whiteboard first. This creates engagement and context before you show the product.
- **Stand up.** If you can stand while presenting, do it. Standing conveys energy and confidence.
- **Read the room.** Watch body language. Crossed arms and phone-checking mean you are losing them. Leaning in and note-taking mean you are winning.

---

## Demo Anti-Patterns

| Anti-Pattern | Why It Kills Demos | What to Do Instead |
|-------------|-------------------|-------------------|
| **Feature dumping** | Showing every feature overwhelms the audience and buries the value. | Show 3-4 features mapped to their specific pain points. |
| **Not tailoring** | A generic demo says "we don't understand your business." | Reference their industry, their tools, their pain points by name. |
| **Talking over the UI** | Narrating while clicking rapidly means they see nothing. | Click, pause, explain. Let the UI breathe. |
| **No pauses for questions** | Running straight through without stopping signals you don't care about their input. | Pause after each segment: "Does this make sense? Any questions before I move on?" |
| **Demoing bugs as features** | "Oh that's actually a feature..." when something clearly broke. | Acknowledge it, use the recovery framework, and move on. |
| **Going overtime** | Exceeding the scheduled time disrespects their calendar. | Finish 5 minutes early. Use remaining time for Q&A. |
| **Starting with login** | The first thing they see is a login screen and MFA prompt. | Pre-authenticate. The first thing they should see is the value. |
| **Demoing in chronological product order** | The product tour starts at "Settings" and ends at the actual feature. | Start with the highest-impact feature. |
| **Reading slides** | A slide deck is not a demo. | If you are reading slides, you are not demoing. Show the product. |

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 1: Demo Script Builder** -- Practices the "Demo Narrative Arc" section end-to-end: constructing a hook, context framing, solution segments mapped to pain points, a wow moment, and a close with next steps. Also applies the "Audience Adaptation" matrix to tailor the script to specific roles. The function takes a prospect profile and maps product features to pain points using the five-act structure.

- **Exercise 5: Demo Failure Recovery Planner** -- Directly applies the "Demo Recovery Framework" (PAUSE-ASSESS-DECIDE-REDIRECT) and the "Recovery Options by Failure Type" table. The function takes a demo plan and failure scenario, then generates ranked recovery options with timing impact, practicing the triage decision-making described in the "Handling Demo Failures" section.

See also `examples.py` section 1 (Demo Narrative Engine) and section 5 (Demo Environment Checklist) for runnable reference implementations.

---

## Interview Q&A: Demo Engineering

**Q: Walk me through how you prepare for and deliver a product demo.**

My preparation starts with discovery notes — I need to understand the prospect's pain points, technical stack, and who will be in the room. From there I build a narrative arc: a hook tied to their biggest pain, context framing that proves I listened during discovery, three demo segments mapped to their top priorities (spending 60% of time on the most important one), a wow moment that shows something they cannot do today, and a close with a concrete next step. On the environment side, I run the golden path end-to-end 24 hours before, refresh seed data 4 hours before, and warm the environment 5 minutes before. I always have a backup plan — screenshots, a recorded walkthrough, or a second demo instance. During the demo, I adapt to the audience: executives get business outcomes in the first 2 minutes, architects get integration and architecture details, developers get code and API examples. I pause after each segment for questions and watch body language to know when to go deeper or move on.

**Q: How do you handle it when a demo breaks in front of a customer?**

First, I do not panic — the audience takes their cue from my reaction. I mentally run through the recovery framework: pause, assess whether it is fixable in 10 seconds, and decide whether to fix it live, switch to a backup, or acknowledge and move on. If it is a page not loading or an API error, I switch to a pre-loaded backup tab or show a pre-captured response. If live code fails, I jump to a completed version in an adjacent tab. The key is having backups prepared for every segment. I never spend more than 30 seconds debugging live, I never blame my team, and I never pretend the failure did not happen. One honest acknowledgment, a smooth transition to the backup, and a bridge back to the narrative. Often, the recovery itself demonstrates competence — prospects remember how you handled the problem more than the problem itself.

**Q: How do you tailor demos to different audiences — say a CTO versus a developer?**

The CTO and the developer need completely different demos. For a CTO, I lead with business outcomes: ROI, risk reduction, customer proof points, and time-to-value. The entire demo might be 5 minutes with a high-level architecture slide and one wow moment. For a developer, I lead with the developer experience: I live-code an integration, show the API response structure, walk through error handling, and demonstrate the SDK. That demo might be 30-45 minutes with deep technical Q&A. In mixed audiences — which is the norm — I layer it: executive context first (so the VP can leave early if they want), then architecture, then code. I set this up explicitly at the start: "Sarah, I'll cover the business case in the first few minutes. Tom, I'll get into the API details after that." This way everyone knows when their section is coming and nobody sits through irrelevant content.
