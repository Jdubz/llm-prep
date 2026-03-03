# 02 -- FDE Deployment Patterns

Being a Forward Deployed Engineer means writing production code in someone else's environment, under someone else's constraints, with someone else's team watching. This file covers the engagement model, the practical skills for navigating unfamiliar codebases, and the soft skills for being effective as a technical outsider embedded in a customer's organization.

---

## The FDE Engagement Model

### Engagement Lifecycle

Every FDE engagement follows a predictable arc. Understanding where you are in the lifecycle tells you what to focus on.

```
Kickoff → Ramp-Up → Delivery → Transition → Support
(Week 1)  (Weeks 2-4)  (Weeks 5-N)  (Final 2-3 weeks)  (Post-engagement)
```

**Phase 1: Kickoff (Week 1)**
- Meet stakeholders on both sides (your company + customer)
- Review the Statement of Work (SOW) line by line
- Agree on success criteria, communication cadence, and escalation paths
- Get access: repos, CI/CD, Slack/Teams, Jira/Linear, cloud consoles
- Set up your local development environment on the customer's stack

**Phase 2: Ramp-Up (Weeks 2-4)**
- Read the codebase (the "first week playbook" below)
- Ship a small, low-risk change to prove you can commit and deploy
- Build relationships with the key engineers on the customer team
- Identify technical risks and surface them early
- Refine the project plan based on what you learn in the codebase

**Phase 3: Delivery (Weeks 5 through end minus 3 weeks)**
- Ship features, integrations, or infrastructure changes
- Run weekly standups or check-ins with customer stakeholders
- Track progress against milestones in the SOW
- Document as you go — do not leave documentation for the end
- Flag scope changes and timeline risks as soon as you see them

**Phase 4: Transition (Final 2-3 weeks)**
- Code review all outstanding work
- Write or update runbooks and architecture docs
- Pair program with the customer team member who will own this code
- Run a knowledge transfer session (live walkthrough + Q&A)
- Get explicit sign-off on deliverables

**Phase 5: Support (Post-engagement)**
- Typically 2-4 weeks of async support via Slack
- Answer questions from the customer team
- Review PRs related to code you wrote
- Escalate issues that need product-level fixes

### Typical Engagement Lengths

| Engagement Type | Duration | Example |
|----------------|----------|---------|
| **Sprint** | 2-4 weeks | Build a specific integration, fix a critical deployment issue |
| **Standard** | 6-12 weeks | Implement a new feature, build a data pipeline, platform migration |
| **Extended** | 3-6 months | Full product deployment, complex multi-system integration |
| **Ongoing** | 6+ months | Embedded team member for strategic accounts |

### Success Criteria

Define these at kickoff. Good success criteria are:
- **Specific**: "User authentication via SAML is working with Okta" not "SSO works"
- **Measurable**: "API response time is under 200ms at p95" not "API is fast"
- **Time-bound**: "Data migration completes within a 4-hour maintenance window"
- **Customer-validated**: The customer agrees these are the right criteria

### How FDE Differs from Consulting

| Dimension | FDE | Consultant |
|-----------|-----|-----------|
| **Relationship to product** | You represent a specific product | You are vendor-neutral (in theory) |
| **Code ownership** | You ship code the customer will maintain | You may ship throwaway POC code |
| **Team integration** | Embedded in the customer team | External advisor |
| **Scope** | Defined by SOW around your product | Broader, may include strategy |
| **Success metric** | Customer successfully uses your product | Recommendations delivered |
| **Loyalty** | Your company + customer | Consulting firm + client |

---

## On-Site vs Remote FDE

### Trade-offs

| Factor | On-Site | Remote |
|--------|---------|--------|
| **Relationship building** | Fast — hallway conversations, lunch, whiteboard | Slower — requires intentional effort |
| **Context absorption** | High — you see how the team works, overhear conversations | Lower — you see only what is shared with you |
| **Security/compliance** | Required for classified, ITAR, FedRAMP-High environments | Acceptable for most commercial work |
| **Cost** | Travel, housing, per diem | Minimal |
| **Flexibility** | Customer's schedule, commute | Your schedule, focused deep work |
| **Burnout risk** | Higher — travel fatigue, isolation from home team | Lower — but Zoom fatigue, feeling disconnected |

### When On-Site Is Necessary

- **Classified or air-gapped environments**: You physically cannot access the network remotely.
- **First 1-2 weeks of any engagement**: Building trust and context in person is dramatically faster.
- **When things are going badly**: If the engagement is off-track, a week on-site to recalibrate is worth it.
- **Cultural reasons**: Some organizations (government, traditional enterprise, Japan-based companies) value physical presence.
- **Complex whiteboard sessions**: Some architectural discussions are genuinely better in person.

### Remote FDE Best Practices

1. **Over-communicate**: Share daily written updates even when there is nothing dramatic to report.
2. **Camera on**: Default to video for all meetings. It builds trust.
3. **Async documentation**: Write things down that you would say out loud on-site. Slack messages, Notion docs, Loom recordings.
4. **Time zone overlap**: Ensure at least 4 hours of overlap with the customer team's core hours.
5. **Weekly video check-in**: Not a status update — a relationship-building conversation. Ask how their week is going.
6. **Ship early and often**: Visible progress builds trust when you cannot build it through physical presence.

---

## Navigating Customer Codebases

### The First Week Playbook

When you land in a new codebase, follow this sequence. Do not try to understand everything at once. Focus on the paths that matter for your deliverables.

**Day 1: Find the foundations**
```
1. README.md — Does it exist? Is it current?
2. Setup instructions — Can you run the app locally?
3. .env.example or configuration — What are the knobs?
4. CI/CD pipeline — How does code get to production?
5. Package manager / dependencies — What is the tech stack?
```

**Day 2: Find the tests**
```
1. Test directory structure — unit, integration, e2e?
2. Run the full test suite — Does it pass? How long?
3. Test coverage report — Where are the gaps?
4. Fixture/factory patterns — How is test data created?
```

**Day 3: Find the patterns**
```
1. Directory structure — How is code organized?
2. A recent PR — What does good code look like here?
3. Error handling patterns — How are exceptions handled?
4. Logging patterns — Where do logs go? What format?
5. Data access patterns — ORM? Raw SQL? Repository pattern?
```

**Day 4: Find the deployment**
```
1. Deployment pipeline — What triggers a deploy?
2. Environments — dev, staging, production?
3. Feature flags — Are they used? Which system?
4. Rollback procedure — How do you undo a bad deploy?
5. Monitoring — Dashboards? Alerting?
```

**Day 5: Ship something small**
```
1. Pick a small bug fix or documentation update
2. Follow their branching strategy
3. Write a PR in their style
4. Get it reviewed and merged
5. Verify it deploys successfully
```

### How to Ask Good Questions

The art of asking questions as an FDE is getting the information you need without appearing unprepared.

**Bad**: "How does this work?" (Too broad, wastes their time)

**Good**: "I've been reading through the OrderService and I see that order creation goes through a saga pattern with three steps. I understand steps 1 and 2, but I'm not clear on how step 3 handles the case where the payment service is down. Can you walk me through the retry logic?"

**The formula:**
1. State what you have already investigated
2. State what you understand
3. Ask about the specific gap

This shows you have done your homework and respects their time.

### Working Within Customer Tech Debt

Every codebase has tech debt. As an FDE, you need to work within it, not crusade against it.

**Rules:**
- **Do not refactor what you do not need to touch.** Your scope is your SOW, not "make the codebase better."
- **Match the existing style**, even if you disagree with it. Consistency is more valuable than your preference.
- **Document the debt you encounter** if it affects your deliverables. Surface it as a risk, not a criticism.
- **Propose improvements only when they directly unblock your work.** "I need to refactor this module to add the feature" is valid. "This module should really use dependency injection" is not your call.

---

## Shipping Code in Someone Else's Repo

### Following Customer Coding Standards

Before writing any code, find and read:
1. **CONTRIBUTING.md** or equivalent
2. **Linter/formatter configuration** (`.eslintrc`, `ruff.toml`, `.editorconfig`)
3. **A recent PR that was approved quickly** — this shows what "good" looks like here
4. **The code review checklist** if one exists

Adopt their conventions even if they differ from yours:
- Tabs vs spaces — use what they use
- Naming conventions — `camelCase` vs `snake_case` vs whatever they chose
- Comment style — JSDoc, docstrings, inline, none
- Import ordering — absolute vs relative, grouping
- Error handling — exceptions, error codes, Result types

### Understanding Their Review Process

| Question | Why it matters |
|----------|---------------|
| Who reviews your PRs? | Know who to tag and their availability |
| What is the expected turnaround time? | Plan your work around review cycles |
| Are there required reviewers or CODEOWNERS? | Auto-assigned reviewers may not know your context |
| Is there a PR template? | Follow it exactly |
| What CI checks must pass? | Do not submit PRs that fail CI |
| What is the merge strategy? | Squash? Rebase? Merge commit? |

### Working Within Their CI/CD Pipeline

- **Run CI locally before pushing** whenever possible. Do not be the person who breaks the build.
- **Understand the pipeline stages**: lint, test, build, deploy. Know what each stage checks.
- **If CI is slow**, ask about running a subset of tests locally. Do not skip tests.
- **If you need a new CI step** (e.g., for a new integration test), propose it as a separate PR.

### Pull Request Etiquette

**The "guest in someone's house" mindset:**

1. **Small, focused PRs.** One concern per PR. Easier to review, easier to revert.
2. **Descriptive titles and bodies.** Include the "why" not just the "what."
3. **Link to the ticket/issue.** Every PR should reference the work item it addresses.
4. **Self-review before requesting review.** Read your own diff. Add inline comments explaining non-obvious decisions.
5. **Respond to review comments promptly.** You are a guest — do not leave reviewers waiting.
6. **Accept feedback gracefully.** If they want a change, make it. This is their codebase.
7. **Do not force-push after review.** Push new commits so reviewers can see what changed.

### Managing Access and Permissions

Track your access in a document. At the end of the engagement, you and the customer should revoke everything:

| System | Access Level | Granted | Revoked |
|--------|-------------|---------|---------|
| GitHub (customer org) | Write to specific repos | Week 1 | End of engagement |
| AWS (dev account) | PowerUser role | Week 1 | End of engagement |
| Jira | Project contributor | Week 1 | End of engagement |
| Slack | Guest in #eng channels | Week 1 | End of engagement |
| VPN | Certificate-based | Week 1 | End of engagement |

---

## Embedded Team Dynamics

### Building Trust as an Outsider

Trust is earned through consistent delivery and genuine respect for the team and their work.

**Week 1-2: Observe and listen.** Attend their standups. Listen more than you speak. Understand their pressures and priorities before offering opinions.

**Week 3-4: Deliver small wins.** Ship something useful. Fix a bug they have been ignoring. Improve a test. Show that you can be productive in their environment.

**Week 5+: Earn a voice.** Once you have demonstrated competence and respect, the team will welcome your input on larger decisions.

**Things that build trust:**
- Following their processes without complaining
- Being available when you said you would be
- Admitting when you do not know something
- Giving credit to their team members publicly
- Shipping quality code that does not break things
- Writing documentation without being asked

**Things that destroy trust:**
- Criticizing their codebase or architecture in front of others
- Going around the team to their management
- Missing deadlines without early warning
- Pushing back on their coding standards
- Name-dropping your own company's engineering practices as superior

### Standing Up for Your Product Without Being Defensive

When the customer is frustrated with your product, your job is to:
1. **Acknowledge the frustration.** "I understand this is blocking you. That's not acceptable."
2. **Separate fact from emotion.** Understand the specific technical issue, not just the feeling.
3. **Own the problem.** "Let me investigate this and get back to you with options."
4. **Escalate internally.** File a detailed bug report with reproduction steps.
5. **Communicate the plan.** "Here's what we're doing about it, and here's the timeline."

Never say: "That's just how the product works" or "That's a known issue."

### Managing Dual Loyalty

You represent both your company and the customer's success. When these conflict:

| Situation | Wrong Response | Right Response |
|-----------|---------------|----------------|
| Customer wants a feature that does not exist | Promise it will be built | "That's not available today. Let me file a feature request with context on your use case and find a workaround." |
| Customer complains about pricing | Offer a discount | "I understand the cost concern. Let me connect you with your AE to discuss options. Meanwhile, here's how to optimize usage." |
| Customer asks you to do work outside your SOW | Say yes to avoid conflict | "I want to help. That falls outside my current scope. Let me check with my team on the right way to expand this engagement." |
| Customer asks you to criticize your own product | Agree to be likable | "There are areas where we can improve, and I'm documenting them. Here's what works well for your use case." |

---

## Scope Management for FDEs

### The Most Common FDE Failure Mode: Scope Creep

Scope creep is the number one reason FDE engagements go sideways. It happens gradually:
- "While you're in that file, can you also..."
- "This is kind of related to the SOW..."
- "It would only take an hour..."

Each individual request seems reasonable. In aggregate, they consume your entire engagement and you deliver none of your actual milestones.

### How to Say No Diplomatically

**Framework: Acknowledge → Explain → Redirect**

1. **Acknowledge**: "That's a great idea and I can see why it would be valuable."
2. **Explain**: "It falls outside the current SOW scope, and I want to make sure I deliver on the agreed milestones first."
3. **Redirect**: "Let me document this as a follow-on item. We can discuss adding it formally if there's capacity, or it could be part of a future engagement."

**Specific phrases:**
- "I want to make sure we stay focused on [milestone X] which is due in two weeks."
- "That's definitely worth doing. Can we add it to the backlog and prioritize it against our existing commitments?"
- "Let me check with my team lead on whether that fits within our current scope."

### Escalation Paths

When scope pressure comes from the customer's engineering manager or VP, you need an escalation path:

```
You (FDE) → Your SE/Account Team → Your Manager → Customer's Project Sponsor
```

Never escalate directly to the customer's leadership. Work through your account team.

### SOW Interpretation

The SOW is your shield. Know it thoroughly.

**Grey areas:** When a request is arguably in scope, default to discussing it with your account team before committing. The cost of a 15-minute internal chat is much lower than the cost of setting a precedent for unlimited scope.

**Tracking scope changes:** Maintain a running document:

| Request | Date | In Scope? | Decision | Impact |
|---------|------|-----------|----------|--------|
| Add CSV export to dashboard | Week 3 | Stretch | Approved — small effort | +2 days |
| Build custom reporting module | Week 5 | Out of scope | Deferred to Phase 2 | Would add 3 weeks |
| Fix performance issue in unrelated service | Week 6 | Out of scope | Declined — customer's team | N/A |

### When to Flex vs When to Hold Firm

**Flex** (do the work) when:
- It takes less than 2 hours
- It directly enables your in-scope deliverable
- The customer has been exceptionally collaborative
- Your account team approves

**Hold firm** (decline or defer) when:
- It would delay an agreed milestone
- It sets a precedent for unlimited scope
- It requires expertise you do not have
- It is a product feature that should be built by your engineering team

---

## Knowledge Transfer and Exit

### Planning Your Departure from Day One

The best FDE engagements end with the customer barely noticing you left. This requires planning from the start.

**Documentation you should produce throughout the engagement:**

| Document | When to write | Purpose |
|----------|--------------|---------|
| **Architecture decision records (ADRs)** | When you make a design choice | Explain why decisions were made |
| **Runbooks** | When you build operational procedures | Enable the customer to operate what you built |
| **Code comments** | While coding | Explain non-obvious logic |
| **Integration guides** | After each integration works | Enable the customer to debug and extend |
| **Known issues / tech debt log** | Throughout | Honest accounting of what needs future attention |

### Training Customer Team Members

1. **Identify the successor** early. Who on the customer's team will own this code?
2. **Pair program** during the Delivery phase, not just during Transition. The successor should be writing code alongside you.
3. **Gradually shift ownership**: first you lead and they watch, then you pair, then they lead and you review, then they work independently and you are available for questions.
4. **Run a formal knowledge transfer session**: a 2-3 hour recorded walkthrough covering architecture, key decisions, operational procedures, and known issues.

### The Handoff Process

**Week T-3 (three weeks before exit):**
- Schedule the knowledge transfer session
- Identify all open work items and their status
- Begin closing out PRs and branches

**Week T-2:**
- Run the knowledge transfer session (record it)
- The successor starts owning new work with your review
- Finalize all documentation

**Week T-1:**
- The successor is working independently
- You are reviewing code and answering questions only
- Conduct a final sign-off meeting with stakeholders

**Post-exit:**
- 2-4 weeks of async Slack availability
- Review critical PRs if asked
- Provide warm introduction to support channels

### Ensuring Customer Can Maintain What You Built

The ultimate test of a successful FDE engagement: three months after you leave, can the customer's team confidently modify, extend, and debug the code you wrote? If yes, you succeeded. If they are paging your account team every week, you did not transfer knowledge effectively.

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 3: FDE Scope Definer** -- Applies the scope management framework from "Scope Management for FDEs." You will categorize customer requests as in-scope, out-of-scope, or stretch, and generate boundary definitions and escalation triggers based on SOW constraints.
- **Exercise 5: QBR Preparation Builder** -- While QBRs are covered in the next file (03-customer-success-and-expansion.md), FDE engagement progress is often reviewed in QBRs. This exercise builds a QBR document that includes FDE milestone tracking.

See also `examples.py`:
- `FDEEngagementTracker` (Section 3) -- engagement lifecycle manager with scope tracking and milestone monitoring

---

## Interview Q&A: FDE Deployment Patterns

**Q: You join a new customer engagement and their codebase is a mess. How do you approach it?**

Every codebase looks messy to an outsider in the first week. I start by assuming there are reasons for the decisions that were made, even if I do not understand them yet. I follow my first-week playbook: find the README, find the tests, find the deployment pipeline, find the logging. I ship a small, low-risk change within the first week to prove I can commit and deploy. I ask targeted questions — showing what I have already investigated and where specifically I am stuck. I never criticize the codebase to the customer's team. If I discover genuine issues that affect my deliverables, I surface them as risks in our status meetings with proposed solutions, not as complaints. I match their coding style and conventions even if I disagree. My job is to deliver value within their constraints, not to refactor their architecture.

**Q: How do you handle scope creep in an FDE engagement?**

Scope creep is the most common failure mode for FDE engagements, and the key is having a system for managing it before it starts. At kickoff, I review the SOW line by line with both the customer and my account team so everyone agrees on what is in scope. Throughout the engagement, I maintain a scope tracking document where every new request is logged with a classification: in-scope, stretch, or out-of-scope. When someone asks for something outside scope, I use the acknowledge-explain-redirect framework: I validate the request, explain why it falls outside current commitments, and propose a path forward — either documenting it for a future engagement, or discussing a formal scope change with the account team. The SOW is my shield, but I wield it diplomatically. I am willing to flex on small items that take under two hours and directly enable my in-scope work, but I hold firm on anything that would delay a milestone or set a precedent for unlimited scope.

**Q: Describe your approach to knowledge transfer at the end of an FDE engagement.**

I plan for my departure from day one. Throughout the engagement, I write architecture decision records, runbooks, and code comments as I go — not as a last-minute exercise. I identify the customer team member who will own my code early in the engagement and progressively shift ownership: first they observe me, then we pair program, then they lead while I review, then they work independently while I am available for questions. In the final two to three weeks, I run a formal knowledge transfer session — a recorded walkthrough of the architecture, key decisions, operational procedures, and known issues. The successor starts owning new work with my review. I make sure they can deploy, debug, and extend what I built independently. After the engagement ends, I remain available on Slack for two to four weeks. The test of success is whether three months later, the customer's team can confidently maintain and extend the code without needing to contact me.
