# Boulder Care Plant Watering Interview Exercise

Your first task is to write a barebones "service" (just a few functions) in vanilla JS to act as a
record keeping system for the watering schedule of house plants.

This exercise does not involve complex algorithms or obscure trivia. Our intent is to see how you
write basic, real-world-ish code, with boilerplate and libraries out of the way.

## Files

* `plantService.js`: A shell of an implementation. Implement the 3 functions here to satisfy the
  tests. Data can just be stored in memory and doesn't need to be persisted.
* `tests.js`: Pre-written tests. We want to make these pass.
* `test-runner.js`: Some vanilla JS helper functions to make the tests more readable and usable.

## Testing

Run `node tests.js` to run the tests. Failures will include stack traces.

Add `--fail-fast` to stop after the first failure.

## Bonus Tasks

If you have time left, pick and choose from these in any order:

* Improve input validation
  * We want to improve the robustness of the application, and prevent it from crashing or doing
    strange things when users input surprising values.
  * If you already focused a lot on validation, maybe skip this one.
* Support listing plants that need to be watered today
  * Not _now_, but any time today.
  * Don't let timezones bog you down! Do everything in UTC.
* Support updating the watering interval for a plant

---

## Related Course Modules

This project connects to several modules in the General Interview course. Use it as a practical companion alongside the written material.

### Module 07 — [Take-Home & Live Coding Projects](../../07-take-home-live-coding/)

This plant-watering exercise is a realistic example of the kind of take-home you will encounter in senior-level interviews. It exemplifies many of the best practices discussed in Module 07:

- **Scope management:** The project asks for a focused set of functions rather than an entire application. Module 07's golden rule -- "do less, but do it well" -- applies directly. Implement `addPlant`, `listPlants`, and `waterPlant` cleanly before pursuing any bonus tasks.
- **Code readability over cleverness:** The service uses plain Maps and straightforward date arithmetic. There is no framework overhead or unnecessary abstraction. Reviewers can understand the code in minutes, which is exactly what the Take-Home Submission Guide recommends.
- **Pre-written tests as a quality contract:** The provided `tests.js` file mirrors the integration test pattern from Module 07 -- test the happy path, test idempotency, test edge cases (non-existent plant, interval boundaries). When you complete a take-home, your test coverage should look like this.
- **In-memory data storage as a deliberate simplification:** Module 07 advises documenting assumptions and trade-offs. Here, the instruction to store data in memory is an intentional scope reduction. In a real submission, you would note in your README that you would use a persistent store in production.
- **Bonus tasks mirror the "should have / nice to have" tiers:** Input validation, listing plants needing watering today, and updating intervals map directly to the prioritization framework in Module 07. Tackle them only after the core is solid.

Use this project to practice your take-home workflow end to end: read the spec, plan your approach, implement incrementally, and write a README documenting your decisions.

### Module 06 — [Coding Interview Patterns](../../06-coding-patterns/)

The implementation patterns in this project connect to concepts from Module 06:

- **Hash map for O(1) lookups:** The `db` Map and per-user plant Maps are a direct application of the hash map pattern for fast key-value access. Module 06 covers when and why to reach for hash maps.
- **Data structure selection:** Choosing a Map over an array for plant storage is a deliberate decision -- O(1) lookup by `plantId` vs O(n) scanning. The data structure decision framework in Module 06 explains this reasoning.
- **Edge case handling:** The tests cover idempotency, missing data, and boundary conditions. Module 06's edge case checklist (empty input, single element, boundary values) applies to service-level code just as much as algorithm problems.

### Module 03 — [Technical Communication](../../03-technical-communication/)

- **Code as documentation:** The function signatures with JSDoc-style comments (`userId /* string */`, `now /* Date */`) demonstrate the code explanation skills covered in Module 03. Clear parameter names and inline type annotations make the code self-documenting.
- **Explaining architecture decisions:** If this were a real take-home submission, you would walk a reviewer through your choices during the follow-up discussion. Module 03's frameworks for explaining past projects and justifying technology choices apply directly to discussing this code.
- **README quality:** Module 03's guidance on writing for skimming, leading with the "what," and keeping documentation concise applies to any take-home README you write.

## Practice

- Complete the core implementation and all bonus tasks as a timed exercise (target: 60-90 minutes).
- Write a brief README as if you were submitting this as a real take-home. Include setup instructions, architecture notes, and a trade-offs section following the template in [Module 07's Take-Home Submission Guide](../../07-take-home-live-coding/01-take-home-submission-guide.md).
- After completing the exercise, practice explaining your implementation decisions out loud using the code walkthrough framework from [Module 03](../../03-technical-communication/01-communication-fundamentals.md).
