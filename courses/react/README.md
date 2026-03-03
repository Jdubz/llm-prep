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

Each lesson contains numbered files. Read them in order.

### 01 — Hooks Deep Dive

- [01 – Hooks and State Management](./src/lessons/01-hooks-deep-dive/01-hooks-and-state-management.md)
- [02 – Hooks Internals and Advanced Patterns](./src/lessons/01-hooks-deep-dive/02-hooks-internals-and-advanced-patterns.md)

### 02 — Custom Hooks

- [01 – Custom Hooks Fundamentals](./src/lessons/02-custom-hooks/01-custom-hooks-fundamentals.md)
- [02 – Custom Hooks Testing and Advanced](./src/lessons/02-custom-hooks/02-custom-hooks-testing-and-advanced.md)

### 03 — Performance

- [01 – React Rendering and Optimization](./src/lessons/03-performance/01-react-rendering-and-optimization.md)
- [02 – Performance Tools and Advanced Patterns](./src/lessons/03-performance/02-performance-tools-and-advanced-patterns.md)

### 04 — Advanced Patterns

- [01 – Component Patterns and Composition](./src/lessons/04-advanced-patterns/01-component-patterns-and-composition.md)
- [02 – Advanced Component APIs](./src/lessons/04-advanced-patterns/02-advanced-component-apis.md)

### 05 — State Management

- [01 – State Management Fundamentals](./src/lessons/05-state-management/01-state-management-fundamentals.md)
- [02 – State Libraries and Solutions](./src/lessons/05-state-management/02-state-libraries-and-solutions.md)
- [03 – Advanced State Patterns](./src/lessons/05-state-management/03-advanced-state-patterns.md)

### 06 — RSC and Suspense

- [01 – Server Components and Suspense](./src/lessons/06-rsc-and-suspense/01-server-components-and-suspense.md)
- [02 – RSC Advanced Features and Patterns](./src/lessons/06-rsc-and-suspense/02-rsc-advanced-features-and-patterns.md)

### 07 — Testing

- [01 – React Testing Library Fundamentals](./src/lessons/07-testing/01-react-testing-library-fundamentals.md)
- [02 – Testing Strategies and Mocking](./src/lessons/07-testing/02-testing-strategies-and-mocking.md)

### 08 — React Internals

- [01 – React Fiber and Rendering](./src/lessons/08-react-internals/01-react-fiber-and-rendering.md)
- [02 – Re-Renders and Optimization](./src/lessons/08-react-internals/02-re-renders-and-optimization.md)
- [03 – React Internals Deep Dive](./src/lessons/08-react-internals/03-react-internals-deep-dive.md)

## Interactive Demos

The Vite app (`npm run dev`) has interactive component demos for hands-on practice:

```bash
cd courses/react
npm install
npm run dev
```

Currently implemented: Lesson 02 (Custom Hooks) with useFetch and usePrevious demos.

## Study Strategy

**Quick prep (4-6 hours)**: Read file 01 for each lesson. These cover core interview knowledge in a concise, pattern-focused format.

**Deep prep (12-16 hours)**: Work through all files in order. Later files (02, 03) cover internals, edge cases, and advanced patterns.

**During the interview**: The cheat-sheet tables and decision trees are embedded inline throughout the files for quick scanning.

## Prerequisites
- 10+ years TypeScript experience with production React
- Review [Lesson 00: React Fundamentals](00-react-fundamentals.md) to ensure the basics are sharp
