# React Interview Prep

Advanced React course for senior engineers. Each lesson covers what you need to explain and demonstrate in an interview, with optional deeper dives and cheat sheets for quick reference.

> **For TypeScript engineers with 10+ years experience**: This skips the basics entirely. Assumes strong JS/TS fundamentals and production React experience.

---

## Lessons

| # | Topic | What You'll Nail |
|---|-------|-----------------|
| 00 | [React Fundamentals](00-react-fundamentals.md) | Components, props, state, effects, refs, events, context, TypeScript patterns |
| 01 | [Hooks Deep Dive](src/lessons/01-hooks-deep-dive/) | useState pitfalls, useEffect mastery, rules of hooks internals |
| 02 | [Custom Hooks](src/lessons/02-custom-hooks/) | Extraction patterns, composition, real-world hook implementations |
| 03 | [Performance](src/lessons/03-performance/) | Memoization decision-making, React Compiler, profiling, virtualization |
| 04 | [Advanced Patterns](src/lessons/04-advanced-patterns/) | Compound components, polymorphic types, headless UI, error boundaries |
| 05 | [State Management](src/lessons/05-state-management/) | Zustand vs Jotai vs Redux, TanStack Query, state colocation |
| 06 | [RSC & Suspense](src/lessons/06-rsc-and-suspense/) | Server components, streaming SSR, Next.js App Router, caching |
| 07 | [Testing](src/lessons/07-testing/) | RTL patterns, MSW mocking, async testing, accessibility |
| 08 | [React Internals](src/lessons/08-react-internals/) | Fiber architecture, reconciliation, concurrent rendering, scheduler |

## Content Per Lesson

Each lesson directory contains:

- **`README.md`** — Core interview knowledge. Concise, pattern-focused, interview-ready.
- **`deep-dive.md`** — Optional extended content. Internals, edge cases, advanced patterns.
- **`cheat-sheet.md`** — Quick reference card. Syntax, APIs, gotchas — scannable during prep.

## Interactive Demos

The Vite app (`npm run dev`) has interactive component demos for hands-on practice:

```bash
cd courses/react
npm install
npm run dev
```

Currently implemented: Lesson 02 (Custom Hooks) with useFetch and usePrevious demos.

## Study Strategy

**Quick prep (4-6 hours)**: Read the README.md for each lesson + review cheat sheets before the interview.

**Deep prep (12-16 hours)**: Work through all READMEs, then deep-dive.md for your weaker areas.

**During the interview**: Cheat sheets are designed to be scannable for quick refreshers.

## Prerequisites
- 10+ years TypeScript experience with production React
- Review [Lesson 00: React Fundamentals](00-react-fundamentals.md) to ensure the basics are sharp
