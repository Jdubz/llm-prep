# Module 07 Deep Dive: Take-Home & Live Coding Mastery

> Going beyond "good enough" — the details that turn a passing submission into a standout one.

---

## Table of Contents

1. [Building a Take-Home Template Repo](#building-a-take-home-template-repo)
2. [README Template](#readme-template)
3. [Git Commit Strategy](#git-commit-strategy)
4. [Testing Strategy for Take-Homes](#testing-strategy-for-take-homes)
5. [Common Mistakes That Get You Rejected](#common-mistakes-that-get-you-rejected)
6. [Handling Ambiguity in Requirements](#handling-ambiguity-in-requirements)
7. [Following Up on Take-Home Submissions](#following-up-on-take-home-submissions)

---

## Building a Take-Home Template Repo

Have these ready before interview season. When you receive a take-home, you should be running code within 10 minutes, not fighting with toolchain configuration.

### TypeScript Template

```
ts-take-home/
  src/
    index.ts           <- Entry point
    routes/            <- Express/Fastify route handlers
    services/          <- Business logic
    models/            <- Types and interfaces
    middleware/         <- Error handling, validation, logging
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

**Pre-configured:**
- TypeScript with strict mode
- ESLint + Prettier with a reasonable config
- Jest with ts-jest for testing
- Express or Fastify with typed request/response
- A health check endpoint that works out of the box
- Error handling middleware
- Environment variable loading (dotenv)
- Makefile with `make setup`, `make dev`, `make test`, `make lint`

**Key dependencies to include:**
- `zod` or `joi` for input validation
- `pino` or `winston` for structured logging
- `supertest` for HTTP testing
- Database driver of choice (pg, better-sqlite3)

### Python Template

```
python-take-home/
  src/
    __init__.py
    main.py            <- Entry point
    routes/            <- FastAPI/Flask route handlers
    services/          <- Business logic
    models/            <- Pydantic models / SQLAlchemy models
    middleware/         <- Error handling
  tests/
    conftest.py        <- Shared fixtures
    test_api.py        <- Integration tests
    test_services.py   <- Unit tests
  .env.example
  .gitignore
  pyproject.toml
  Makefile
  requirements.txt (or use pyproject.toml exclusively)
```

**Pre-configured:**
- Python 3.11+ with type hints throughout
- Ruff for linting and formatting
- pytest with fixtures and parametrize
- FastAPI or Flask with Pydantic validation
- Structured error responses
- Makefile with standard targets

### Go Template

```
go-take-home/
  cmd/
    server/
      main.go          <- Entry point
  internal/
    handler/           <- HTTP handlers
    service/           <- Business logic
    model/             <- Data types
    middleware/         <- Logging, error handling
  tests/
    integration_test.go
  .env.example
  .gitignore
  go.mod
  go.sum
  Makefile
```

**Pre-configured:**
- Standard library HTTP or Chi/Echo router
- Go test with table-driven tests
- golangci-lint configuration
- Structured logging (slog or zerolog)
- Graceful shutdown handling
- Makefile with `make run`, `make test`, `make lint`

### Template Maintenance

- **Update quarterly** — keep dependencies current
- **Test the template** — run `make setup && make test` after every update
- **Keep it minimal** — the template should take under 2 minutes to understand
- **Keep it private** — do not publish your interview templates publicly

---

## README Template

Use this as a starting point. Adapt it to the specific project.

```markdown
# Project Name

Brief description of what this project does and why. (2-3 sentences max)

## Quick Start

### Prerequisites

- Node.js 20+ (or Python 3.11+, Go 1.21+)
- PostgreSQL 15+ (if applicable)

### Setup

(Exact commands. Copy-paste should work.)

### Running

(How to start the application.)

### Testing

(How to run all tests.)

## API Reference

(If applicable. Brief endpoint documentation with example requests.)

## Architecture

(Brief description of your design decisions.)

### Key Decisions

- **[Decision]**: [Why you made this choice]
- **[Decision]**: [Why you made this choice]

## Trade-offs & Future Work

(What you would do differently with more time. Be specific.)

- [ ] Add pagination to list endpoints
- [ ] Implement caching for frequently accessed data
- [ ] Add rate limiting
- [ ] Improve error messages for edge case X
```

**Guidelines:**
- Total README length: 50-100 lines
- Every command should be copy-pasteable
- If setup requires more than 3 commands, something is wrong
- Include example API calls with expected responses
- The "Trade-offs" section is your opportunity to show awareness without over-building

---

## Git Commit Strategy

### Atomic Commits

Each commit should represent a single logical change that leaves the codebase in a working state.

**Atomic commit examples:**
```
Add Express server with health check endpoint
Add User model with email validation
Implement POST /api/users with input validation
Add unit tests for User model validation
Add integration tests for POST /api/users
Implement GET /api/users with pagination
Add error handling middleware with structured responses
Update README with setup instructions and API docs
```

**Non-atomic commits (avoid):**
```
Add user feature                    <- Too broad
Fix typo and add pagination         <- Two unrelated changes
WIP                                 <- Not a complete thought
```

### Meaningful Messages

**Format:**
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

Before you submit, clean up your history:

1. **Review commits:** `git log --oneline`
2. **Squash fixup commits:** Use interactive rebase to combine fix commits with their originals
3. **Reorder if needed:** Ensure the progression is logical
4. **Verify each commit builds:** Every commit should leave the project in a runnable state

This is the one time interactive rebase is strongly encouraged. Your final history should read like a narrative.

---

## Testing Strategy for Take-Homes

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

### Test Organization

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

- Framework behavior (Express routing, React rendering)
- Third-party library internals
- Trivial functions (simple getters, identity transforms)
- Implementation details (internal state, private methods)

### Testing Anti-Patterns in Take-Homes

- **Tests that only test the mock:** If your test is entirely about verifying mock calls, it is not testing real behavior
- **Snapshot tests as a substitute for assertions:** Snapshots are fragile and do not demonstrate understanding
- **Commented-out tests:** Remove them or make them pass. Commented-out tests signal rushed work
- **Tests that depend on execution order:** Each test should be independent

---

## Common Mistakes That Get You Rejected

### 1. The Code Does Not Run

The single most common reason for rejection. The reviewer clones your repo, follows your README, and gets an error.

**Prevention:**
- Clone your repo to a fresh directory and follow your own README
- Test on a clean machine or container if possible
- List exact versions of required tools
- Include a `.tool-versions` or `.nvmrc` file for language version

### 2. No Error Handling

Your code works for the happy path but crashes on any unexpected input.

**Prevention:**
- Add input validation at every entry point
- Return meaningful error messages (not stack traces)
- Handle database errors, network failures, and missing data

### 3. No Tests

Some candidates skip tests to "save time" and implement more features. This is almost always the wrong tradeoff.

**Prevention:**
- Tests are not optional for senior roles
- A smaller feature set with tests beats a larger set without

### 4. Over-Engineering

You built an event-driven microservice architecture for a CRUD app. The reviewer spent 20 minutes trying to understand your dependency injection framework.

**Prevention:**
- Match the complexity of your solution to the complexity of the problem
- If you can explain your architecture in 30 seconds, it is probably right-sized
- Save your architecture skills for the README's "Future Work" section

### 5. Ignoring the Requirements

You built something impressive but not what was asked. The take-home says "build a REST API" and you built a GraphQL service.

**Prevention:**
- Re-read the requirements after you finish, before you submit
- Highlight each requirement and verify you have addressed it
- If you deviated from the requirements, explain why in the README

### 6. Poor README or No README

The reviewer opens your repo and sees no instructions. They spend 5 minutes guessing how to run it, fail, and move to the next candidate.

**Prevention:**
- README is mandatory
- Setup instructions must work on the first try
- Include example commands and expected output

### 7. Hardcoded Values and Secrets

Database URLs, API keys, or port numbers hardcoded in the source code.

**Prevention:**
- Use environment variables for all configuration
- Include a `.env.example` file
- Add `.env` to `.gitignore`
- Never commit real credentials

### 8. Inconsistent Code Style

Half the file uses tabs, half uses spaces. Some functions use arrow syntax, others use function declarations. No linter configured.

**Prevention:**
- Configure a linter and formatter before you start coding
- Run them as part of your build/test process
- This takes 5 minutes and prevents an entire category of negative signals

---

## Handling Ambiguity in Requirements

### The Right Response to Ambiguity

Ambiguity in take-home requirements is usually intentional. It tests whether you can make reasonable decisions independently.

**When you have a way to ask (email, Slack):**
- Ask 1-2 clarifying questions maximum
- Ask about core requirements, not minor details
- Frame questions as "I am planning to do X because of Y. Does that align with your expectations?"

**When you cannot ask:**
- Document your assumptions in the README
- Choose the simpler interpretation
- Implement the core behavior and note alternatives in "Trade-offs"

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

## Following Up on Take-Home Submissions

### The Submission Email

Keep it brief and professional:

```
Subject: Take-Home Submission - [Your Name] - [Role]

Hi [Name],

I have completed the take-home assignment. The repository is here: [link]

A few highlights:
- [Core feature implemented with brief description]
- [Testing approach]
- [One interesting decision you made]

I documented trade-offs and future improvements in the README.
Please let me know if you have any questions or need anything else.

Best,
[Your Name]
```

### If You Hear Nothing

- **Wait 3-5 business days** before following up
- **Follow up once** — a brief email asking about timeline
- **Do not follow up more than twice** — if they are not responding, move on

### Preparing for the Review Discussion

Many companies follow a take-home with a discussion about your submission. Prepare for:

- **"Walk me through your architecture"** — Be ready to explain your decisions in 2-3 minutes
- **"Why did you choose X over Y?"** — Have specific reasons for your technology and pattern choices
- **"What would you do differently?"** — Reference your README's trade-offs section
- **"How would this scale?"** — Think about 10x and 100x the current load
- **"Show me your tests"** — Know your test strategy and be able to explain coverage decisions
- **"I noticed [issue]. Can you explain?"** — Do not be defensive. Acknowledge, explain your reasoning, and discuss how you would fix it

### What They Are Actually Evaluating in the Discussion

- **Can you articulate technical decisions?** — Not just "I chose X" but "I chose X because of Y, and the tradeoff is Z"
- **Do you know the limitations of your code?** — Self-awareness is a senior signal
- **Can you discuss alternatives?** — Shows breadth of knowledge
- **Are you open to feedback?** — How you react to criticism of your code says a lot about working with you
- **Does your verbal explanation match the code?** — They are checking if you actually wrote and understand it
