# Module 07: Take-Home & Live Coding Projects

> Take-homes and live coding are where senior engineers should shine. The code you write here is closer to real work than any whiteboard exercise. Treat it that way.

---

## Table of Contents

1. [Take-Home Submissions](#take-home-submissions)
2. [Time Management](#time-management)
3. [What Reviewers Actually Look For](#what-reviewers-actually-look-for)
4. [Live Pair Programming](#live-pair-programming)
5. [Coding Environment Setup](#coding-environment-setup)
6. [Common Take-Home Types](#common-take-home-types)
7. [Evaluation Criteria by Company Type](#evaluation-criteria-by-company-type)
8. [Portfolio Projects](#portfolio-projects)
9. [Interview Tips](#interview-tips)

---

## Take-Home Submissions

### Structuring Your Project

A take-home is not just about working code. It is about demonstrating how you work. The structure of your submission communicates as much as the code itself.

**Directory structure example:**
```
project/
  README.md          <- Start here. Always.
  src/               <- Application code
  tests/             <- Test files (mirror src/ structure)
  .env.example       <- Environment variables template (never commit .env)
  .gitignore         <- Properly configured
  Makefile / scripts/ <- Common commands (setup, test, run, lint)
  package.json / requirements.txt / go.mod  <- Dependencies
```

### README — Your First Impression

The README is the first thing a reviewer reads. Many reviewers decide whether to run your code based on the README alone.

**Essential sections:**
1. **Overview** — What does this project do? (2-3 sentences)
2. **Setup** — How to run it. Exact commands. Assume nothing about the reviewer's environment.
3. **Usage** — How to interact with it. Example requests/commands.
4. **Architecture** — Brief description of key decisions. Why you structured it this way.
5. **Testing** — How to run tests. What is covered.
6. **Trade-offs & Future Work** — What you would do with more time. This is critical — it shows you know the limitations.

**What to exclude from the README:** Do not write a novel. Do not explain basic concepts. Do not document every function. Keep it under 100 lines.

### Clean Git History

Your git history tells a story. Reviewers who check it (and senior-level reviewers will) want to see:

- **Atomic commits** — Each commit does one thing
- **Meaningful messages** — "Add user authentication endpoint with JWT" not "fix stuff"
- **Logical progression** — Setup, core feature, tests, polish
- **No commit fixing a previous commit's mistake** — Use interactive rebase to squash fixups before submitting

**Bad history:**
```
"initial commit"
"WIP"
"fix"
"actually fix"
"add tests"
"fix tests"
```

**Good history:**
```
"Initialize project with Express, TypeScript, and Jest config"
"Add user model with validation and database migration"
"Implement POST /users endpoint with input validation"
"Add unit tests for user model and integration tests for /users"
"Add error handling middleware with structured error responses"
"Add API documentation to README"
```

### What Reviewers Actually Look For (Overview)

In order of importance for most reviewers:
1. **Does it work?** — Can they run it and get the expected output?
2. **Is it readable?** — Can they understand the code without your explanation?
3. **Is it tested?** — Are there meaningful tests?
4. **Is it well-structured?** — Separation of concerns, clear architecture
5. **Does it handle errors?** — What happens when things go wrong?

What they do NOT care about:
- Cleverness — Write boring, readable code
- 100% test coverage — Strategic coverage is better
- Premature optimization — Clarity over performance

---

## Time Management

This is where most senior candidates stumble. You have the skills but try to do too much.

### The Golden Rule

**Do less, but do it well.** A polished, working subset beats an ambitious, broken whole.

### Prioritization Framework

When you read the requirements, immediately categorize:

**Must have (ship it):**
- Core functionality that demonstrates the main ask
- Basic error handling (do not crash on bad input)
- At least a few meaningful tests
- A README with setup instructions
- Working code that a reviewer can run

**Should have (if time allows):**
- Comprehensive test coverage
- Input validation
- Logging
- Clean error messages
- Good commit history

**Nice to have (only if you are ahead of schedule):**
- Docker setup
- CI configuration
- Performance optimization
- Additional features beyond the spec
- API documentation (Swagger/OpenAPI)

### What to Skip and What to Polish

**Always skip:**
- Perfect CSS (unless it is a frontend-focused take-home)
- Authentication (unless explicitly required)
- Deployment configuration
- Features not in the requirements
- Over-abstraction "for future extensibility"

**Always polish:**
- The README
- Error messages (a reviewer will send bad input)
- The happy path (make sure the core feature works flawlessly)
- Naming (variables, functions, files)
- The first file a reviewer will open

### Time Allocation by Project Duration

**4-hour take-home:**
```
0:00 - 0:30  Read requirements, plan architecture, set up project
0:30 - 2:30  Core implementation
2:30 - 3:15  Tests for core functionality
3:15 - 3:45  Error handling, edge cases, cleanup
3:45 - 4:00  README, final review, clean git history
```

**8-hour take-home:**
```
0:00 - 1:00  Requirements analysis, architecture planning, project setup
1:00 - 4:00  Core implementation (all primary features)
4:00 - 5:30  Comprehensive testing
5:30 - 6:30  Error handling, validation, logging
6:30 - 7:30  Code cleanup, refactoring, documentation
7:30 - 8:00  README, git history cleanup, final review
```

**Weekend project:**
```
Day 1: Planning + core implementation + basic tests
Day 2: Polish, comprehensive tests, documentation, cleanup
Reserve 2+ hours at the end for README and review
```

---

## What Reviewers Actually Look For

### Readability

This is the single most important quality. A reviewer spends 15-30 minutes on your submission. If they cannot understand your code quickly, it is a negative signal regardless of correctness.

**Practical readability tips:**
- Functions should do one thing and be under 30 lines
- Variable names should describe what they hold: `userEmail` not `e`, `remainingAttempts` not `r`
- Avoid nested ternaries, complex one-liners, and "clever" tricks
- Group related code, separate unrelated code with blank lines
- Consistent style throughout — configure a linter and formatter

### Testing

**What to test:**
- Happy path (core functionality works with valid input)
- Error cases (invalid input, missing data, boundary conditions)
- Edge cases (empty input, very large input, special characters)

**What NOT to test:**
- Framework internals (do not test that Express routes exist)
- Trivial getters/setters
- External libraries

**Test structure (Arrange-Act-Assert):**
```
describe("UserService.createUser", () => {
    it("creates a user with valid input", () => {
        // Arrange: set up test data
        // Act: call the function
        // Assert: verify the result
    });

    it("rejects duplicate email addresses", () => {
        // ...
    });

    it("validates email format", () => {
        // ...
    });
});
```

### Error Handling

Reviewers will try to break your code. Handle failures gracefully:

- **Validate input early** — Return clear error messages, not stack traces
- **Use appropriate HTTP status codes** — 400 for bad input, 404 for not found, 500 for server errors
- **Catch and handle exceptions** — Never let an unhandled exception crash the server
- **Log errors** — Even a simple `console.error` shows awareness

### Separation of Concerns

Demonstrate that you understand architecture, not just coding:

- **Routes/controllers** — Handle HTTP concerns (request parsing, response formatting)
- **Services/business logic** — Core logic, independent of HTTP
- **Data access** — Database queries, isolated from business logic
- **Models/types** — Data shapes and validation

This does not mean you need 47 files for a 4-hour take-home. It means your HTTP handler should not contain SQL queries.

### Avoiding Over-Engineering

This is the most common senior engineer mistake. You know how to build scalable systems, and you want to demonstrate it. Resist.

**Over-engineering signals (avoid these):**
- Abstract factory pattern for a CRUD endpoint
- Microservices architecture for a single-feature take-home
- Custom ORM wrapper around an already simple ORM
- Dependency injection framework for 3 classes
- Event sourcing for a TODO app

**Right-sizing signals (do these):**
- Simple, direct code that solves the stated problem
- Comments explaining "why" not "what" (only when the why is non-obvious)
- A note in the README about what you would change at scale

### Good Naming

- **Functions:** Verb + noun. `createUser`, `validateEmail`, `calculateTotal`
- **Booleans:** `isValid`, `hasPermission`, `shouldRetry`
- **Collections:** Plural. `users`, `orderItems`, `pendingRequests`
- **Constants:** UPPER_SNAKE_CASE. `MAX_RETRY_COUNT`, `DEFAULT_PAGE_SIZE`
- **Files:** Match what they export. `user-service.ts` exports `UserService`

### Consistent Style

Pick a style and stick with it. Inconsistency is a stronger negative signal than an unconventional style choice.

- Configure ESLint/Prettier (JS/TS), Black/Ruff (Python), gofmt (Go) — and run them
- Be consistent with quotes, semicolons, indentation, bracket placement
- Be consistent with patterns — if one route validates input in the controller, all should

---

## Live Pair Programming

### Collaboration Signals

Live coding is as much about collaboration as it is about code. The interviewer is evaluating what it would be like to work with you.

**Asking questions:**
- "Would you prefer I optimize for readability or performance here?"
- "I am thinking about using X approach because of Y. Does that align with what you are looking for?"
- "I am not sure about this edge case. Can you clarify the expected behavior for [specific scenario]?"

**Thinking aloud:**
- Narrate your thought process continuously
- "I am considering two approaches here..."
- "Let me first handle the happy path, then I will come back for error cases..."
- "I think this is O(n log n) because..."

**Accepting suggestions:**
- When the interviewer hints, take the hint. They are trying to help you succeed.
- "That is a great point, let me adjust my approach..."
- "I had not considered that. Let me refactor this part..."
- Never dismiss a suggestion without consideration, even if you disagree

**Building on interviewer's ideas:**
- "Building on what you said about caching, I think we could also..."
- Treat it as a real pair programming session, not a test

**Recovering from mistakes:**
- Everyone makes mistakes. How you recover matters more than the mistake.
- "I see the issue — I have an off-by-one error here. Let me fix that."
- Do not panic, do not apologize excessively, just fix it and move on
- If you are stuck, say so: "I am stuck on this part. Let me step back and think about the overall approach."

### The STAR Method for Live Coding

- **Situation:** Restate the problem
- **Task:** Explain your approach
- **Action:** Write the code, narrating
- **Result:** Test it, discuss complexity, suggest improvements

---

## Coding Environment Setup

### Before the Interview

You should have all of this ready before interview season, not the night before.

**Editor configuration:**
- Font size large enough for screen sharing (14pt minimum)
- High-contrast theme (dark or light — just make sure it is readable)
- Line numbers enabled
- Disable distracting notifications and plugins
- Know your keyboard shortcuts for: find/replace, move lines, duplicate lines, multi-cursor

**Boilerplate repos:**
- Have template projects ready for your primary languages
- Pre-configured: linter, formatter, test runner, basic project structure
- Tested — make sure they actually run on your current machine
- Keep them private (do not publish interview templates publicly)

**Terminal setup:**
- Clean prompt (no clutter)
- Aliases for common commands (`alias t="npm test"`, `alias r="npm run dev"`)
- Split terminal if possible — one for running, one for commands

### During the Interview

- Close Slack, email, and all notifications
- Use a clean desktop
- Have a glass of water nearby
- If remote, test your audio/video setup beforehand
- Have the job description and your notes in a separate window (not visible when screen sharing)

---

## Common Take-Home Types

### CRUD API

**What they are testing:** Can you build a clean, well-structured API?

**Approach:**
1. Set up project with your framework of choice
2. Define data model with validation
3. Implement endpoints: Create, Read (single + list with pagination), Update, Delete
4. Add error handling for each endpoint
5. Write integration tests for each endpoint
6. Add a README with curl/httpie examples

**Differentiators:**
- Pagination done correctly (cursor-based or offset with proper metadata)
- Input validation with clear error messages
- Proper HTTP status codes and response formatting
- Database migrations (not just raw SQL in code)

### Data Processing Pipeline

**What they are testing:** Can you handle data at scale with clean code?

**Approach:**
1. Understand the input format and output requirements
2. Design the pipeline stages (read, transform, aggregate, output)
3. Implement with clear separation between stages
4. Handle malformed data gracefully (log and skip, do not crash)
5. Test with edge cases (empty file, malformed rows, very large input)

**Differentiators:**
- Streaming processing instead of loading everything into memory
- Clear logging of skipped/malformed records
- Performance awareness (mention Big-O of your approach)

### Frontend Feature

**What they are testing:** Component architecture, state management, UX awareness.

**Approach:**
1. Plan component hierarchy before coding
2. Build from the inside out (smallest components first)
3. Handle loading, error, and empty states
4. Make it accessible (keyboard navigation, semantic HTML, ARIA labels)
5. Write tests for component behavior (not implementation details)

**Differentiators:**
- Proper loading and error states (not just the happy path)
- Responsive design (even if not required)
- Accessibility basics
- Clean component API (good props, no prop drilling)

### Full-Stack App

**What they are testing:** Can you deliver a working feature end-to-end?

**Approach:**
1. Start with the API — get the backend working first
2. Build a minimal frontend that exercises the API
3. Focus on one complete feature rather than many incomplete ones
4. Wire up error handling end-to-end (API errors surface in the UI)

**Differentiators:**
- End-to-end testing (at least one happy path)
- Proper API error handling surfaced in the UI
- Clean separation between frontend and backend
- Type safety across the boundary (if using TypeScript)

---

## Evaluation Criteria by Company Type

### Startup (Early-Stage)

**What they value:**
- Speed of delivery — did you ship something working quickly?
- Pragmatic choices — did you pick the simple solution over the "correct" one?
- Product thinking — did you consider the user experience?
- Adaptability — can you work with ambiguous requirements?

**How to demonstrate:**
- Ship fast, note what you would improve
- Choose simple, well-known tools
- Add a note about product considerations
- Ask clarifying questions (or document assumptions)

### Big Tech

**What they value:**
- Scalability awareness — does your solution handle 10x or 100x load?
- Testing rigor — comprehensive test coverage, edge cases
- Code quality — clean, well-documented, follows language idioms
- System design thinking — even in a take-home

**How to demonstrate:**
- Discuss scalability in your README
- Write thorough tests
- Follow the language's conventions precisely
- Mention caching, indexing, and performance considerations

### Mid-Size Company

**What they value:**
- Balance of speed and quality
- Maintainability — could another engineer extend this?
- Communication — clear README, clear code, clear commit messages
- Real-world readiness — error handling, logging, configuration

**How to demonstrate:**
- Clean, readable code with good structure
- Meaningful tests (not exhaustive, not minimal)
- Good README with architecture explanation
- Production-ready patterns (environment config, error handling)

---

## Portfolio Projects

### What Makes a Good Portfolio Project

A portfolio project is NOT a tutorial follow-along. It demonstrates independent technical judgment.

**Good portfolio projects:**
- Solve a real problem (even a small one)
- Use technologies relevant to your target roles
- Have a live demo or clear screenshots
- Include a README that explains architectural decisions
- Show clean code, not just working code

**Bad portfolio projects:**
- TODO apps (unless the technology is the point)
- Clones of popular apps (unless you add something novel)
- Incomplete projects with "WIP" in the README
- Projects with no tests
- Projects with hardcoded API keys in the source

### GitHub Profile Optimization

- **Pin 4-6 repositories** that represent your best work
- **Write descriptions** for each pinned repo
- **Add READMEs** with screenshots or demos
- **Maintain a contribution graph** — consistency matters more than volume
- **Clean up old repos** — archive or make private anything embarrassing
- **Profile README** — keep it brief, professional, link to your best work

---

## Interview Tips

### Before the Take-Home

- **Read the requirements at least twice** before writing any code
- **Identify the core ask** — what is the minimum viable submission?
- **Set a timer** — take-home deadlines are real; do not burn 12 hours on a 4-hour project
- **Prepare your environment** — dependencies installed, editor configured, boilerplate ready

### During the Take-Home

- **Commit early and often** — you can rewrite history later, but you cannot recover lost work
- **Do not research while coding** — if you need to look up an API, fine. If you need a tutorial, you picked the wrong tool.
- **Test as you go** — do not write everything, then debug everything
- **Take breaks** — a 5-minute walk solves more bugs than an hour of staring

### Before Live Coding

- **Practice in the actual environment** — if it is CoderPad, practice on CoderPad
- **Warm up** — solve one easy problem to get your brain in gear
- **Prepare your introduction** — "I have been a full-stack engineer for 10+ years, most recently at..."
- **Have questions ready** — for the interviewer, about the role, team, or codebase

### During Live Coding

- **Do not start typing immediately** — understand, plan, then code
- **Name things well from the start** — renaming during a live session is awkward
- **Write a function signature first** — inputs, outputs, then implementation
- **Test incrementally** — write a small piece, test it, continue
- **If stuck for more than 2 minutes, say something** — "I am considering whether to use X or Y here"

### After the Interview

- **Do not second-guess** — what is done is done
- **Write down what went well and what did not** — for next time
- **Follow up** — a brief thank-you email is professional and appropriate
- **Keep your take-home code** — you might want to reference it later or reuse the template
