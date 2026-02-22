# Module 07 Cheat Sheet: Take-Home & Live Coding

> Quick-reference checklists and templates. Review before starting any take-home or live coding session.

---

## Take-Home Submission Checklist

### Before You Submit

- [ ] **README exists** with setup, run, and test instructions
- [ ] **Code runs** — clone to a fresh directory and follow your own README
- [ ] **Tests pass** — all tests are green
- [ ] **Linter passes** — no warnings or errors
- [ ] **No secrets committed** — check for .env files, API keys, passwords
- [ ] **`.gitignore` is configured** — no `node_modules`, `__pycache__`, `.env`
- [ ] **`.env.example` exists** — if env vars are needed
- [ ] **Error handling** — send bad input, verify graceful responses
- [ ] **Git history is clean** — atomic commits, meaningful messages
- [ ] **Requirements are met** — re-read the spec, verify every point
- [ ] **Trade-offs documented** — what would you do with more time?

### Quality Bar

- [ ] Can a stranger run this in under 3 minutes?
- [ ] Can a stranger understand the code in under 15 minutes?
- [ ] Does the happy path work flawlessly?
- [ ] Are error messages helpful (not stack traces)?
- [ ] Is the code style consistent throughout?

---

## README Template

```markdown
# Project Name

One-paragraph description of what this does.

## Quick Start

### Prerequisites
- Language version
- Database (if any)

### Setup
$ exact commands here

### Run
$ exact command here

### Test
$ exact command here

## API Reference (if applicable)

### POST /api/resource
Request body, example response.

### GET /api/resource/:id
Example response.

## Architecture

Brief description. Key decisions:
- **Choice**: Reason
- **Choice**: Reason

## Trade-offs & Future Work
- What you would improve with more time
- What you intentionally skipped and why
```

---

## Time Allocation Guide

### 4-Hour Project

| Phase | Time | Focus |
|-------|------|-------|
| Plan | 0:00 - 0:30 | Read spec, plan architecture, set up project |
| Build | 0:30 - 2:30 | Core feature implementation |
| Test | 2:30 - 3:15 | Tests for happy path + key error cases |
| Polish | 3:15 - 3:45 | Error handling, edge cases, code cleanup |
| Document | 3:45 - 4:00 | README, git history cleanup, final review |

### 8-Hour Project

| Phase | Time | Focus |
|-------|------|-------|
| Plan | 0:00 - 1:00 | Spec analysis, architecture, project setup |
| Build | 1:00 - 4:00 | All primary features |
| Test | 4:00 - 5:30 | Comprehensive test suite |
| Harden | 5:30 - 6:30 | Error handling, validation, logging |
| Polish | 6:30 - 7:30 | Refactor, clean up, documentation |
| Document | 7:30 - 8:00 | README, git history, final review |

### Weekend Project

| Phase | Time | Focus |
|-------|------|-------|
| Day 1 AM | 3-4h | Planning, setup, core implementation |
| Day 1 PM | 3-4h | Complete features, basic tests |
| Day 2 AM | 3-4h | Comprehensive tests, error handling |
| Day 2 PM | 2-3h | Polish, documentation, final review |

---

## Live Coding Setup Checklist

### Environment

- [ ] Editor font size 14pt+ (readable when screen sharing)
- [ ] High-contrast theme enabled
- [ ] Line numbers visible
- [ ] Notifications disabled (Slack, email, OS)
- [ ] Clean desktop (no personal tabs/windows visible)
- [ ] Terminal ready with clean prompt
- [ ] Audio/video tested (if remote)
- [ ] Glass of water nearby
- [ ] Quiet environment secured

### Knowledge

- [ ] Key shortcuts memorized (find, replace, move line, multi-cursor)
- [ ] Standard library functions fresh in mind for your language
- [ ] Common data structure APIs fresh (map, set, heap, queue)
- [ ] Warmed up with one easy problem

### Materials

- [ ] Job description reviewed
- [ ] Company notes accessible (not visible when sharing screen)
- [ ] Questions prepared for the interviewer

---

## Evaluation Criteria by Role Level

| Criteria | Mid-Level Expected | Senior Expected | Staff Expected |
|----------|-------------------|-----------------|----------------|
| **Working code** | Must work | Must work | Must work |
| **Tests** | Some tests | Comprehensive | Comprehensive + clear strategy |
| **Error handling** | Basic | Thorough | Thorough + graceful degradation |
| **Architecture** | Reasonable | Well-structured | Justified decisions, extensible |
| **README** | Setup instructions | Setup + decisions | Setup + decisions + trade-offs |
| **Performance** | Not expected | Awareness | Analysis + optimization |
| **Git history** | Not evaluated | Clean, atomic | Tells a clear story |
| **Code style** | Consistent | Idiomatic | Idiomatic + opinionated |

---

## Common Mistakes to Avoid

### Instant Rejection

| Mistake | Fix |
|---------|-----|
| Code does not run | Test in a fresh environment before submitting |
| No README | Always include one, even if brief |
| Hardcoded secrets | Use .env, add .env to .gitignore |
| Plagiarized code | Write it yourself. Reviewers check. |

### Strong Negative Signals

| Mistake | Fix |
|---------|-----|
| No tests | Write at least happy-path tests |
| No error handling | Validate input, catch exceptions |
| Inconsistent style | Configure linter + formatter |
| Over-engineered | Match solution complexity to problem complexity |
| Ignored requirements | Re-read spec before submitting |
| Giant single commit | Use atomic commits with meaningful messages |

### Missed Opportunity Signals

| Mistake | Fix |
|---------|-----|
| No trade-offs discussed | Add "Future Work" to README |
| No input validation | Validate at every entry point |
| No logging | Add basic structured logging |
| No pagination | Add it for list endpoints |
| Hardcoded configuration | Use environment variables |

---

## Live Coding Phrases

### Starting

- "Let me make sure I understand the problem. We need to..."
- "Before I start coding, let me think through my approach..."
- "A few clarifying questions: What is the expected input size? Can there be duplicates?"

### During

- "I am going to start with the brute-force approach, then optimize..."
- "I think the right data structure here is X because..."
- "Let me handle the happy path first, then circle back for edge cases..."
- "I notice this is O(n^2). I think we can do better with a hash map..."

### When Stuck

- "I am stuck on this part. Let me step back and reconsider..."
- "I think the issue is with my [specific area]. Let me trace through..."
- "Can I talk through my current thinking? I see two possible approaches..."

### Finishing

- "Let me trace through this with a small example to verify..."
- "The time complexity is O(n log n) due to the sort, and space is O(n)..."
- "With more time, I would add handling for [edge case]..."
