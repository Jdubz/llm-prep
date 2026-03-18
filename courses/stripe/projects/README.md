# Onsite Interview Simulation Projects

Four full simulations, one per interview round. Each is timed and self-contained.

| # | Directory | Interview | Time | Format |
|---|-----------|-----------|------|--------|
| 01 | `01-programming-sim/` | Programming Exercise | 50 min | Read spec → implement 4 parts → self-check |
| 02 | `02-integration-sim/` | Integration Exercise | 50 min | Read spec + existing code → add features + tests |
| 03 | `03-bug-squash-sim/` | Bug Squash | 50 min | Run failing tests → find and fix 5 bugs |
| 04 | `04-behavioral-prep/` | Behavioral (User First & Curious + Experience & Goals) | 70 min | Fill-in workbook → rehearse stories out loud |

## How to use

1. Read the README in each project directory first — it's your spec
2. Set a timer (time listed above)
3. Talk out loud the entire time (simulate the real interview)
4. Run the starter/buggy file to check your work: `npx tsx starter.ts` or `npx tsx buggy.ts`
5. Do NOT open solution.ts / fixed.ts until you've completed your attempt
6. After finishing, compare against the reference and note gaps

## Recommended order

- **Day 1:** `04-behavioral-prep/` (no code — just fill in the workbook and rehearse)
- **Day 2:** `01-programming-sim/` (warm up on a from-scratch build)
- **Day 3:** `03-bug-squash-sim/` (practice debugging methodology)
- **Day 4:** `02-integration-sim/` (hardest — reading existing code + spec + API docs)
- **Day 5:** Redo whichever project you scored lowest on
- **Day 6:** Full mock — do all 3 technical projects back-to-back with 15 min breaks

## Scoring yourself

After each simulation, assess on Stripe's actual criteria:

- [ ] Did I read the spec/tests before coding?
- [ ] Did I talk through my reasoning the whole time?
- [ ] Did I finish Part 1 and Part 2 cleanly? (Parts 3-4 are stretch)
- [ ] Is my code clean and readable?
- [ ] Did I handle errors and edge cases?
- [ ] Did I ask clarifying questions (even to yourself)?
- [ ] Did I run my code frequently (every 5-10 lines)?
