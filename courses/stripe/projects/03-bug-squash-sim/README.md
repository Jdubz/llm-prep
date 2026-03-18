# Bug Squash Simulation: EventBus

**Set a 50-minute timer. Start it now.**

This simulates the Stripe Bug Squash interview round. You have a TypeScript library with failing tests. Your job is to find and fix the bugs.

## Setup

```bash
npx tsx buggy.ts
```

You will see a mix of passing and failing tests. There are **5 bugs** planted in the code. Some tests already pass -- do not break them.

## Rules

- Fix bugs one at a time
- Run the tests after each fix to confirm progress
- **DO NOT read `fixed.ts` until you are done** (it contains the answers)
- Talk through your reasoning out loud (this is evaluated)

## Debugging Methodology (What Stripe Evaluates)

The rubric values **structured process over speed**. Stripe interviewers are looking for:

1. **Run failing tests, read the output carefully.** What is the test expecting vs. what it got? Which tests fail together -- do they share a code path?

2. **Form hypotheses.** Before touching code, say what you think is wrong and why. "This test expects handlers to run in priority order but they're reversed -- maybe the sort comparator is wrong."

3. **Use the debugger or strategic console.logs.** Don't just stare at the code. Insert prints to confirm or reject your hypothesis. Remove them when done.

4. **Narrow scope with binary search.** If you don't know where the bug is, bisect. Comment out half the logic, see if the test still fails. Narrow from there.

5. **Communicate your reasoning out loud.** The interviewer wants to hear your thought process. Silence is the worst signal. Say things like: "I'm looking at the publish method because three failing tests all go through it."

## What "Good" Looks Like

- You find 4-5 bugs in 50 minutes
- Each fix is minimal and targeted (not a rewrite)
- You explain why each bug caused the symptoms you observed
- You verify each fix doesn't break passing tests
- You stay calm and methodical, not frantic

## Scoring

| Bugs Fixed | Signal        |
|------------|---------------|
| 5          | Strong hire   |
| 4          | Hire          |
| 3          | Lean hire     |
| 2          | Lean no-hire  |
| 0-1        | No hire       |

The above is approximate. Process and communication matter as much as the count.
