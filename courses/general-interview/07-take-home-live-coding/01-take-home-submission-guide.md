# Take-Home Submission Guide

> Take-homes are where senior engineers should shine. The code you write here is closer to real work than any whiteboard exercise. Treat it that way.

---

## What Reviewers Actually Look For

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

### Evaluation Criteria by Role Level

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

## Project Structure

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

### Language-Specific Template Structures

**TypeScript template:**
```
ts-take-home/
  src/
    index.ts           <- Entry point
    routes/            <- Express/Fastify route handlers
    services/          <- Business logic
    models/            <- Types and interfaces
    middleware/        <- Error handling, validation, logging
    utils/             <- Helper functions
  tests/
    integration/       <- API endpoint tests
    unit/              <- Service/utility tests
    fixtures/          <- Test data
  .env.example
  .gitignore
  .eslintrc.json
  .prettierrc
  jest.config.ts
  tsconfig.json
  package.json
  Makefile
```

Pre-configure with: TypeScript strict mode, ESLint + Prettier, Jest with ts-jest, Express/Fastify with typed request/response, error handling middleware, dotenv, Makefile with `make setup`, `make dev`, `make test`, `make lint`.

Key dependencies: `zod` or `joi` (input validation), `pino` or `winston` (structured logging), `supertest` (HTTP testing), database driver.

**Python template:**
```
python-take-home/
  src/
    __init__.py
    main.py            <- Entry point
    routes/            <- FastAPI/Flask route handlers
    services/          <- Business logic
    models/            <- Pydantic models / SQLAlchemy models
    middleware/        <- Error handling
  tests/
    conftest.py        <- Shared fixtures
    test_api.py        <- Integration tests
    test_services.py   <- Unit tests
  .env.example
  .gitignore
  pyproject.toml
  Makefile
```

Pre-configure with: Python 3.11+ with type hints, Ruff for linting/formatting, pytest with fixtures, FastAPI or Flask with Pydantic validation.

**Go template:**
```
go-take-home/
  cmd/
    server/
      main.go          <- Entry point
  internal/
    handler/           <- HTTP handlers
    service/           <- Business logic
    model/             <- Data types
    middleware/        <- Logging, error handling
  tests/
    integration_test.go
  .env.example
  .gitignore
  go.mod
  go.sum
  Makefile
```

Pre-configure with: standard library HTTP or Chi/Echo router, table-driven tests, golangci-lint, slog or zerolog, graceful shutdown.

**Template maintenance:**
- Update quarterly — keep dependencies current
- Test the template — run `make setup && make test` after every update
- Keep it minimal — the template should take under 2 minutes to understand
- Keep it private — do not publish your interview templates publicly

---

## README Quality

The README is the first thing a reviewer reads. Many reviewers decide whether to run your code based on the README alone.

### Essential Sections

1. **Overview** — What does this project do? (2-3 sentences)
2. **Setup** — How to run it. Exact commands. Assume nothing about the reviewer's environment.
3. **Usage** — How to interact with it. Example requests/commands.
4. **Architecture** — Brief description of key decisions. Why you structured it this way.
5. **Testing** — How to run tests. What is covered.
6. **Trade-offs & Future Work** — What you would do with more time. This is critical — it shows you know the limitations.

**What to exclude:** Do not write a novel. Do not explain basic concepts. Do not document every function. Keep it under 100 lines.

### README Template

```markdown
# Project Name

Brief description of what this project does and why. (2-3 sentences max)

## Quick Start

### Prerequisites

- Node.js 20+ (or Python 3.11+, Go 1.21+)
- PostgreSQL 15+ (if applicable)

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
- **[Decision]**: [Why you made this choice]
- **[Decision]**: [Why you made this choice]

## Trade-offs & Future Work
- What you would improve with more time
- What you intentionally skipped and why
```

**Guidelines:**
- Total README length: 50-100 lines
- Every command should be copy-pasteable
- If setup requires more than 3 commands, something is wrong
- Include example API calls with expected responses
- The "Trade-offs" section is your opportunity to show awareness without over-building

### Example Assumptions Documentation

```markdown
## Assumptions

- **Authentication:** Not implemented. The spec mentioned "user management"
  but did not specify auth requirements. I focused on the CRUD operations
  and would add JWT-based auth as a next step.
- **Database:** Used SQLite for simplicity. In production, I would use
  PostgreSQL with connection pooling.
- **Pagination:** Implemented cursor-based pagination (more scalable than
  offset) with a default page size of 20.
```

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

| Phase | Time | Focus |
|-------|------|-------|
| Plan | 0:00 - 0:30 | Read spec, plan architecture, set up project |
| Build | 0:30 - 2:30 | Core feature implementation |
| Test | 2:30 - 3:15 | Tests for happy path + key error cases |
| Polish | 3:15 - 3:45 | Error handling, edge cases, code cleanup |
| Document | 3:45 - 4:00 | README, git history cleanup, final review |

**8-hour take-home:**

| Phase | Time | Focus |
|-------|------|-------|
| Plan | 0:00 - 1:00 | Spec analysis, architecture, project setup |
| Build | 1:00 - 4:00 | All primary features |
| Test | 4:00 - 5:30 | Comprehensive test suite |
| Harden | 5:30 - 6:30 | Error handling, validation, logging |
| Polish | 6:30 - 7:30 | Refactor, clean up, documentation |
| Document | 7:30 - 8:00 | README, git history, final review |

**Weekend project:**

| Phase | Time | Focus |
|-------|------|-------|
| Day 1 AM | 3-4h | Planning, setup, core implementation |
| Day 1 PM | 3-4h | Complete features, basic tests |
| Day 2 AM | 3-4h | Comprehensive tests, error handling |
| Day 2 PM | 2-3h | Polish, documentation, final review |

---

## Code Organization and Quality

### Readability

This is the single most important quality. A reviewer spends 15-30 minutes on your submission. If they cannot understand your code quickly, it is a negative signal regardless of correctness.

**Practical readability tips:**
- Functions should do one thing and be under 30 lines
- Variable names should describe what they hold: `userEmail` not `e`, `remainingAttempts` not `r`
- Avoid nested ternaries, complex one-liners, and "clever" tricks
- Group related code, separate unrelated code with blank lines
- Consistent style throughout — configure a linter and formatter

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

### Good Naming

- **Functions:** Verb + noun. `createUser`, `validateEmail`, `calculateTotal`
- **Booleans:** `isValid`, `hasPermission`, `shouldRetry`
- **Collections:** Plural. `users`, `orderItems`, `pendingRequests`
- **Constants:** UPPER_SNAKE_CASE. `MAX_RETRY_COUNT`, `DEFAULT_PAGE_SIZE`
- **Files:** Match what they export. `user-service.ts` exports `UserService`

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

---

## Testing Strategy

### What to Test

**Priority order:**
1. **Happy path** — The core feature works with valid input
2. **Validation** — Bad input returns appropriate errors
3. **Edge cases** — Empty data, boundary values, special characters
4. **Error handling** — What happens when dependencies fail?

### Coverage Expectations by Time Limit

| Time Limit | Expected Coverage |
|-----------|------------------|
| 2-4 hours | Happy path + 2-3 error cases for the core feature |
| 4-8 hours | Comprehensive happy path + validation + key edge cases |
| Weekend | Full coverage of business logic + integration tests |

### Test Structure (Arrange-Act-Assert)

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

**Unit tests — test business logic in isolation:**
```
describe("calculateShippingCost", () => {
    it("returns free shipping for orders over $50", ...);
    it("calculates standard rate for domestic orders", ...);
    it("applies international surcharge for foreign addresses", ...);
    it("throws on negative order total", ...);
});
```

**Integration tests — test endpoints end-to-end:**
```
describe("POST /api/orders", () => {
    it("creates an order and returns 201", ...);
    it("returns 400 for missing required fields", ...);
    it("returns 400 for invalid product IDs", ...);
    it("returns 409 for duplicate order reference", ...);
});
```

### What NOT to Test

- Framework internals (do not test that Express routes exist)
- Third-party library internals
- Trivial getters/setters
- External libraries
- Implementation details (internal state, private methods)

### Testing Anti-Patterns

- **Tests that only test the mock:** If your test is entirely about verifying mock calls, it is not testing real behavior
- **Snapshot tests as a substitute for assertions:** Snapshots are fragile and do not demonstrate understanding
- **Commented-out tests:** Remove them or make them pass. Commented-out tests signal rushed work
- **Tests that depend on execution order:** Each test should be independent

---

## Git Commit Strategy

### Clean History

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

### Commit Message Format

```
<verb> <what> [with <detail>]

Verb: Add, Implement, Fix, Refactor, Update, Remove, Configure
```

**Good messages:**
- `Add rate limiting middleware with sliding window counter`
- `Fix off-by-one error in pagination offset calculation`
- `Refactor user service to separate validation from persistence`
- `Configure Jest with TypeScript support and coverage thresholds`

**Bad messages:**
- `update` (what was updated?)
- `fix bug` (what bug?)
- `changes` (what changes?)
- `final version` (famous last words)

### Pre-Submission Cleanup

1. Review commits: `git log --oneline`
2. Squash fixup commits: Use interactive rebase to combine fix commits with their originals
3. Reorder if needed: Ensure the progression is logical
4. Verify each commit builds: Every commit should leave the project in a runnable state

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

## Common Mistakes and Instant Rejection Signals

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

## Handling Ambiguity in Requirements

Ambiguity in take-home requirements is usually intentional. It tests whether you can make reasonable decisions independently.

**When you have a way to ask (email, Slack):**
- Ask 1-2 clarifying questions maximum
- Ask about core requirements, not minor details
- Frame questions as "I am planning to do X because of Y. Does that align with your expectations?"

**When you cannot ask:**
- Document your assumptions in the README
- Choose the simpler interpretation
- Implement the core behavior and note alternatives in "Trade-offs"

### Common Ambiguities and Reasonable Defaults

| Ambiguity | Reasonable Default |
|-----------|-------------------|
| No database specified | SQLite (simple) or PostgreSQL (realistic) |
| No auth requirement mentioned | Skip it, document the assumption |
| "Build an API" (no framework specified) | Use the most popular framework for your language |
| No deployment requirement | Do not deploy, but mention how you would |
| "Well-tested" (no coverage target) | 70-80% coverage of business logic |
| "Handle errors" (no specifics) | Validate input, return appropriate HTTP codes, log errors |

---

## Before You Submit Checklist

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

## Before the Take-Home

- **Read the requirements at least twice** before writing any code
- **Identify the core ask** — what is the minimum viable submission?
- **Set a timer** — take-home deadlines are real; do not burn 12 hours on a 4-hour project
- **Prepare your environment** — dependencies installed, editor configured, boilerplate ready

## During the Take-Home

- **Commit early and often** — you can rewrite history later, but you cannot recover lost work
- **Do not research while coding** — if you need to look up an API, fine. If you need a tutorial, you picked the wrong tool.
- **Test as you go** — do not write everything, then debug everything
- **Take breaks** — a 5-minute walk solves more bugs than an hour of staring
