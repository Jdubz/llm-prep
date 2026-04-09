# 01 – Frontend Patterns

The frontend stack for Dropbox Dash: React + TypeScript, the DIG design system, and the UI patterns that matter for building AI-powered search experiences.

> **Interview format (confirmed from recruiter screen):** For this role, the coding rounds are **React/TypeScript** (Interview 1: frontend) and **React/TypeScript + Python** (Interview 2: full stack). Historically, some Dropbox frontend roles have tested vanilla JavaScript, but this role tests React directly. Vanilla JS fundamentals are still valuable background knowledge — see the [Vanilla JS & React Interview Prep](#11-vanilla-js--react-interview-prep) section at the end of this file.

---

## 1. Dropbox Frontend Stack

### Confirmed Production Technologies

| Technology | Role | Source |
|-----------|------|--------|
| **React** | Primary UI framework | Job listings, engineering blog |
| **TypeScript** | Type safety (migrated from CoffeeScript in 2017) | [dropbox.tech blog post](https://dropbox.tech/frontend/the-great-coffeescript-to-typescript-migration-of-2017) |
| **DIG** (Dropbox Interface Guidelines) | Internal design system — 87% of product code uses it | [Design case study](https://www.laurenloprete.com/dropbox-interface-guidelines) |
| **Redux** (with code-splitting) | State management — async reducer registration | [dropbox.tech blog post](https://dropbox.tech/frontend/redux-with-code-splitting-and-type-checking) |
| **SCSS + BEM** | CSS authoring with namespaced conventions | [github.com/dropbox/css-style-guide](https://github.com/dropbox/css-style-guide) |
| **Apollo Client** | GraphQL client for API-QL pattern | Job descriptions |
| **API-QL** | Client-side GraphQL layer bridging Apollo and REST | Internal (not publicly documented) |
| **Edison** | Go + Node.js web server with pagelet architecture | [dropbox.tech blog post](https://dropbox.tech/frontend/edison-webserver-a-faster-more-powerful-dropbox-on-the-web) |
| **Bazel** | Build system | [github.com/dropbox/dbx_build_tools](https://github.com/dropbox/dbx_build_tools) |
| **Rollup** | JS bundler (replaced custom bundler → 33% bundle size reduction) | [dropbox.tech blog post](https://dropbox.tech/frontend/how-we-reduced-the-size-of-our-javascript-bundles-by-33-percent) |
| **@dropbox/ttvc** | Time to Visually Complete — open-source performance metric | [github.com/dropbox/ttvc](https://github.com/dropbox/ttvc) |
| **Stormcrow** | Feature flags / A/B experiment system | [dropbox.tech blog post](https://dropbox.tech/infrastructure/introducing-stormcrow) |
| **Selenium** | End-to-end UI testing (post-submit) | [dropbox.tech Athena post](https://dropbox.tech/infrastructure/athena-our-automated-build-health-management-system) |
| **react-testing-library** | Component and integration testing | Job listings |
| **Electron** | Desktop app support (Edison serves to Electron) | Edison blog post |

### DIG: Dropbox Interface Guidelines

Dropbox's internal design system. This is the most important thing to understand about how frontend development actually works at Dropbox.

**What it is:**
- Unified design system covering **all 4 platforms**: web, desktop (Win/Mac), mobile (iOS/Android)
- Shared tokens (color, spacing, typography), icons, and component libraries
- Before DIG, Dropbox had **4 outdated design systems** and **2,000+ raw hex values** in web code
- Now at **87% adoption** across product code
- Internal self-service portal for designers and engineers

**What it means for the role:**
- You'll build with DIG components and tokens, not from scratch
- Understanding design systems (tokens, variants, composition) is essential
- You'll collaborate with designers who work in Figma and reference DIG specs

### Edison Architecture

Edison is how Dropbox serves the web frontend. Knowing this shows systems awareness.

```
Browser → CDN (static bundles)
       → Envoy proxy → Edison Server (Go)
                          → Streaming Reactserver (Go-wrapped Node.js for SSR)
                          → Courier/gRPC calls to backend services
```

**Key properties:**
- **Pagelet architecture** — each page section (nav, content, sidebar) is an independent React app that renders into an HTML slot. Pagelets execute in parallel and stream to the browser.
- **SPA deployment** — client bundles deploy to CDN, not served from the webserver
- **gRPC data fetching** — Edison makes async gRPC calls (via Dropbox's Courier framework) during server-side rendering
- **Electron support** — same architecture serves the desktop app

### API-QL: Dropbox's Internal Pattern

API-QL is a lightweight GraphQL server that runs **in the client**, not on a backend server. Not publicly documented, but referenced in job descriptions and likely used on Dash.

```
Traditional:  Client → GraphQL Server → REST APIs
Dropbox:      Client → API-QL (in-client) → REST APIs
```

**How it works:**
- Apollo Client sends GraphQL queries
- API-QL resolves them by calling REST endpoints
- Data aggregation happens client-side
- Frontend devs get GraphQL DX; backend devs maintain REST APIs

**Why this matters:**
- Decouples frontend data needs from backend API evolution
- No need to maintain a server-side GraphQL schema
- Frontend can aggregate data from multiple REST endpoints in a single "query"
- Reduces backend coupling — services stay RESTful

**Interview angle:** If asked about data fetching architecture, this is a sophisticated pattern that shows you understand the trade-offs between GraphQL and REST at scale.

### Redux with Code-Splitting

Dropbox's Redux architecture supports **async reducer registration**, solving the problem of large monolithic apps where each page only needs a subset of reducers.

```typescript
// Reducers can be registered asynchronously when a route loads
store.registerReducer('search', searchReducer);
store.registerReducer('stacks', stacksReducer);
// Each code-split bundle registers only its own reducers
```

**Why this matters:** In a large app like Dash with multiple surfaces (search, Stacks, settings, connectors), you don't want to load all state management code upfront. Code-split Redux means each route only loads the reducers it needs.

### Stormcrow: Feature Flags

Dropbox's in-house feature gating system. Relevant for a 0→1 product like Dash.

- JSON config deploys to production servers
- Supports percentage-based rollouts, A/B experiments, cookie-based gating
- Frontend code checks flags to show/hide features
- Critical for iterative shipping in early-stage product work

---

## 2. Search UI Patterns

Building search interfaces has specific UX and technical challenges. These patterns are directly relevant to the Dash Experiences role.

### Instant Search with Debouncing

```typescript
// Search input with debounced query
const [query, setQuery] = useState('');
const debouncedQuery = useDebounce(query, 300);

useEffect(() => {
  if (debouncedQuery) {
    fetchResults(debouncedQuery);
  }
}, [debouncedQuery]);
```

**Key decisions:**
- **Debounce interval** — 200-300ms balances responsiveness vs. API load
- **Minimum query length** — skip single-character queries
- **Request cancellation** — abort in-flight requests when the query changes (AbortController)

### Streaming Results

Dash streams AI answers token-by-token. The frontend handles this via:

```typescript
// Streaming AI response
async function streamAnswer(query: string, onToken: (token: string) => void) {
  const response = await fetch('/api/ai-answer', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
  
  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  
  while (reader) {
    const { done, value } = await reader.read();
    if (done) break;
    onToken(decoder.decode(value));
  }
}
```

**Patterns to know:**
- **ReadableStream API** for SSE/streaming responses
- **Progressive rendering** — show search results immediately, stream AI answer below
- **Loading states** — skeleton screens for results, animated dots for AI generation
- **Error boundaries** — gracefully handle stream interruptions

### Result Rendering

Search results come from different sources with different schemas. The frontend needs to:

```typescript
// Unified result component with source-specific rendering
type SearchResult = {
  id: string;
  title: string;
  snippet: string;
  source: 'gmail' | 'slack' | 'gdrive' | 'notion' | 'jira';
  url: string;
  metadata: Record<string, unknown>;
  timestamp: string;
};

function ResultCard({ result }: { result: SearchResult }) {
  return (
    <div className="result-card">
      <SourceIcon source={result.source} />
      <div>
        <h3>{highlightMatches(result.title, query)}</h3>
        <p>{highlightMatches(result.snippet, query)}</p>
        <span className="meta">
          {result.source} · {formatRelativeTime(result.timestamp)}
        </span>
      </div>
    </div>
  );
}
```

**Cross-source consistency:** Every result — regardless of source — should feel like it belongs in the same list. Consistent card layout, consistent interaction patterns.

### Keyboard Navigation

Search-heavy UIs need excellent keyboard support:
- Arrow keys to navigate results
- Enter to open
- Cmd/Ctrl+K to focus search
- Tab to move between result sections
- Escape to clear/close

### Virtualized Lists

For large result sets:

```typescript
// React virtualization for large result lists
import { useVirtualizer } from '@tanstack/react-virtual';

function ResultsList({ results }: { results: SearchResult[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: results.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80, // estimated row height
  });
  // ... render only visible items
}
```

---

## 3. State Management for Search

### What State Exists

| State | Where | Why |
|-------|-------|-----|
| **Query text** | Local (useState) | Changes rapidly, no need to persist |
| **Search results** | Server cache (React Query / SWR) | Fetched from API, cacheable |
| **AI answer stream** | Local (useReducer) | Accumulated token-by-token |
| **Filters** | URL params | Shareable, bookmarkable |
| **Connected apps** | Server cache | Rarely changes, cacheable |
| **User preferences** | Server cache + local | Theme, default filters |

### URL-Driven Search State

Filters and query should live in the URL for shareability:

```typescript
// Search state in URL params
function useSearchParams() {
  const [searchParams, setSearchParams] = useSearchParams();
  
  return {
    query: searchParams.get('q') ?? '',
    source: searchParams.get('source') ?? 'all',
    dateRange: searchParams.get('date') ?? 'any',
    setQuery: (q: string) => setSearchParams({ ...params, q }),
  };
}
```

### Optimistic Updates

For Stacks (bookmarking collections):
- User adds item to Stack → immediately show it in the UI
- Fire API request in background
- Roll back on failure with toast notification

---

## 4. CSS & Responsive Design

The job listing explicitly calls out **HTML, CSS, TypeScript, and React** as core technologies. CSS knowledge is expected to be strong, not incidental.

### Layout Patterns

```css
/* Flexbox — the workhorse for component-level layout */
.search-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
}

/* Grid — for page-level layout and multi-column views */
.dashboard {
  display: grid;
  grid-template-columns: 260px 1fr;      /* sidebar + main */
  grid-template-rows: 56px 1fr;          /* header + content */
  height: 100vh;
}

/* Grid for responsive card layouts */
.stacks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
```

**When to use which:**
- **Flexbox** — single-axis layouts (nav bars, result cards, action rows)
- **Grid** — two-axis layouts (page scaffolding, dashboards, card grids)
- **Both together** — Grid for the page layout, Flexbox for components within grid cells

### Responsive Design

Dash works "across web, mobile, desktop." Responsive patterns matter.

```css
/* Mobile-first breakpoints */
.search-container {
  padding: 8px 12px;
}

@media (min-width: 768px) {
  .search-container {
    padding: 16px 24px;
    max-width: 720px;
    margin: 0 auto;
  }
}

@media (min-width: 1024px) {
  .search-container {
    max-width: 960px;
  }
}

/* Container queries — component-level responsiveness */
.result-card-container {
  container-type: inline-size;
}

@container (min-width: 400px) {
  .result-card {
    flex-direction: row;  /* side-by-side above 400px */
  }
}

@container (max-width: 399px) {
  .result-card {
    flex-direction: column;  /* stacked on narrow */
  }
}
```

**Key responsive patterns for Dash:**
- **Collapsible sidebar** — full sidebar on desktop, hamburger or bottom nav on mobile
- **Adaptive search bar** — full-width on mobile, centered with max-width on desktop
- **Result density** — compact result cards on mobile, richer previews on desktop
- **Touch targets** — minimum 44×44px on mobile for clickable elements

### CSS Architecture: SCSS + BEM at Dropbox

Dropbox has a [public CSS style guide](https://github.com/dropbox/css-style-guide) using SCSS with BEM-based naming and reserved namespaces.

```scss
// Dropbox BEM naming conventions with namespaced prefixes
.c-result-card {                    // .c- = component
  display: flex;
  align-items: flex-start;
  gap: $spacing-md;                 // DIG design token
  padding: $spacing-md $spacing-lg;
  
  &__title {                        // BEM element
    font-size: $font-size-heading-sm;
    color: $color-text-primary;
  }
  
  &__snippet {                      // BEM element
    color: $color-text-secondary;
  }
  
  &--highlighted {                  // BEM modifier
    border-left: 3px solid $color-primary;
  }
}

.o-media {                          // .o- = reusable CSS object (e.g., Flag pattern)
  display: flex;
  gap: $spacing-sm;
}

.u-visually-hidden {                // .u- = utility
  position: absolute;
  clip: rect(0, 0, 0, 0);
}

.is-active { }                      // state classes
.has-results { }
```

**Dropbox CSS conventions:**
- `.o-` — CSS objects (common layout patterns like the Flag object)
- `.c-` — CSS components (buttons, inputs, modals, result cards)
- `.u-` — Utilities and helpers
- `.is-` / `.has-` — Stateful classes
- Nesting limited to **3 levels deep**
- Media queries placed **within** CSS selectors (SMACSS pattern)
- DIG design tokens replace raw values (color, spacing, typography)

### Animations & Transitions

```css
/* Smooth transitions for search result appearance */
.result-card {
  opacity: 0;
  transform: translateY(4px);
  animation: fadeIn 150ms ease-out forwards;
}

@keyframes fadeIn {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* AI answer streaming cursor */
.ai-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: currentColor;
  animation: blink 1s step-end infinite;
}

/* Prefer reduced motion */
@media (prefers-reduced-motion: reduce) {
  .result-card { animation: none; opacity: 1; transform: none; }
  .ai-cursor { animation: none; }
}
```

---

## 5. Frontend Performance

The listing says: *"Optimize frontend performance to deliver fast and efficient user experiences, considering factors such as page load times, rendering speed, and responsiveness."* This is a dedicated responsibility, not a nice-to-have.

### Core Web Vitals

| Metric | What It Measures | Target | Dash Context |
|--------|-----------------|--------|--------------|
| **LCP** (Largest Contentful Paint) | When the main content is visible | < 2.5s | Search bar + initial results visible |
| **INP** (Interaction to Next Paint) | Responsiveness to user input | < 200ms | Typing in search → seeing suggestions |
| **CLS** (Cumulative Layout Shift) | Visual stability | < 0.1 | AI answer appearing shouldn't push results down |

### Code Splitting

Dash has multiple product surfaces (search, Stacks, settings, connectors). Split by route:

```typescript
const Search = lazy(() => import('./pages/Search'));
const Stacks = lazy(() => import('./pages/Stacks'));
const Settings = lazy(() => import('./pages/Settings'));
```

### Bundle Optimization

```typescript
// Dynamic import for heavy libraries only used in specific flows
const renderMarkdown = async (content: string) => {
  const { marked } = await import('marked');   // only loaded when needed
  return marked.parse(content);
};

// Tree shaking — import only what you use
import { useVirtualizer } from '@tanstack/react-virtual';  // good
// import * as TanStack from '@tanstack/react-virtual';     // bad — pulls everything
```

**Bundle analysis tools:** `webpack-bundle-analyzer`, `source-map-explorer` — identify unexpectedly large dependencies.

### Rendering Performance

```typescript
// Memoize expensive result card rendering
const MemoizedResultCard = memo(ResultCard, (prev, next) => 
  prev.result.id === next.result.id && prev.query === next.query
);

// useMemo for expensive computations
const highlightedResults = useMemo(
  () => results.map(r => ({
    ...r,
    title: highlightMatches(r.title, query),
    snippet: highlightMatches(r.snippet, query),
  })),
  [results, query]
);

// useTransition for non-urgent updates (React 18+)
const [isPending, startTransition] = useTransition();

function handleFilterChange(filter: string) {
  // Urgent: update the filter UI immediately
  setActiveFilter(filter);
  // Non-urgent: re-render the full result list
  startTransition(() => {
    setFilteredResults(applyFilter(results, filter));
  });
}
```

### Image & Asset Optimization

Dash shows file previews and thumbnails:
- **Lazy load** images below the fold (`loading="lazy"`)
- **`srcset`** for responsive images (serve smaller images on mobile)
- **Skeleton placeholders** until image loads
- **Cache thumbnails aggressively** — file previews rarely change
- **WebP/AVIF** formats for smaller payloads

### Preventing Layout Shift (CLS)

```typescript
// Reserve space for AI answer to prevent content push
function SearchResults({ results, aiAnswer }: Props) {
  return (
    <div>
      {/* AI answer slot — always rendered, min-height prevents CLS */}
      <div style={{ minHeight: aiAnswer ? 'auto' : 120 }}>
        {aiAnswer ? <AIAnswer answer={aiAnswer} /> : <AIAnswerSkeleton />}
      </div>
      <ResultsList results={results} />
    </div>
  );
}
```

### Performance Profiling

- **React DevTools Profiler** — identify unnecessary re-renders
- **Chrome Performance tab** — flame chart for rendering bottlenecks
- **Lighthouse** — automated audit for LCP, INP, CLS, accessibility
- **Real User Monitoring (RUM)** — track actual user performance, not just lab tests

---

## 6. AI UX Patterns

The listing says: *"Implement interactive user interfaces that effectively communicate complex AI functionalities and data insights to end-users."* This goes beyond just streaming tokens.

### Streaming AI Answer UX

```typescript
// State machine for AI answer display
type AIAnswerState =
  | { status: 'idle' }
  | { status: 'searching'; query: string }           // retrieving sources
  | { status: 'generating'; text: string; sources: Source[] }  // streaming
  | { status: 'complete'; text: string; sources: Source[]; citations: Citation[] }
  | { status: 'error'; error: string; fallback?: string };

function AIAnswerCard({ state }: { state: AIAnswerState }) {
  switch (state.status) {
    case 'searching':
      return <SearchingSkeleton query={state.query} />;
    case 'generating':
      return (
        <div>
          <StreamingText text={state.text} />
          <SourcePills sources={state.sources} />
        </div>
      );
    case 'complete':
      return (
        <div>
          <AnswerText text={state.text} citations={state.citations} />
          <SourcePills sources={state.sources} />
          <FeedbackButtons answerId={state.answerId} />
        </div>
      );
    case 'error':
      return <ErrorCard message={state.error} fallback={state.fallback} />;
  }
}
```

### Confidence & Attribution

- **Inline citations** — clickable references to source documents within the AI answer
- **Source pills** — show which connected apps contributed to the answer (Slack, GDrive, etc.)
- **"Based on N sources"** — transparency about how many documents informed the answer
- **Highlight sourced vs. synthesized** — users need to know what came from their data vs. what the model generated

### Feedback Mechanisms

```typescript
// Thumbs up/down + optional feedback
function FeedbackButtons({ answerId }: { answerId: string }) {
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null);
  
  const handleFeedback = async (type: 'positive' | 'negative') => {
    setFeedback(type);  // optimistic update
    await submitFeedback(answerId, type);
    if (type === 'negative') {
      // Optionally show follow-up: "What was wrong?" (incorrect, incomplete, irrelevant)
      setShowFollowUp(true);
    }
  };
  // ...
}
```

### Progressive Disclosure

- **Search results appear first** (fast, < 1s), AI answer streams below (slower, < 2s)
- **"Show more" for long answers** — don't overwhelm with a wall of AI text
- **Expandable source cards** — summary visible, full context on click
- **Contextual suggestions** — "Ask a follow-up" or "Refine your search" after an answer

### Error & Edge States

| Scenario | UX Pattern |
|----------|-----------|
| AI answer failed | Show search results (always work), subtle error message: "AI summary unavailable" |
| No results found | Helpful empty state: "Try different keywords" or "Connect more apps" |
| Partial connector failure | Show available results, indicator: "Some sources unavailable" |
| Slow AI response | Progress indicator with "Analyzing N documents..." |
| Low-confidence answer | Softer language: "Here's what I found..." vs. definitive statements |

---

## 7. Designer Collaboration

The listing says: *"Work closely with UX/UI designers to ensure seamless integration of design elements, branding, and usability principles into the frontend development process."*

### DIG Design System Integration

DIG (Dropbox Interface Guidelines) is the single source of truth for design at Dropbox. It replaced 4 outdated systems and 2,000+ raw hex values with shared tokens and components.

```scss
// DIG design tokens in SCSS — shared variables between design (Figma) and code
// These replace raw values like #0061FE or 16px everywhere

// Colors
$color-primary: #0061FE;              // Dropbox blue
$color-text-primary: #1e1919;
$color-text-secondary: #637282;
$color-surface-default: #ffffff;
$color-surface-elevated: #ffffff;
$color-border-default: #d5dce0;

// Spacing scale
$spacing-xs: 4px;
$spacing-sm: 8px;
$spacing-md: 16px;
$spacing-lg: 24px;
$spacing-xl: 32px;

// Typography
$font-size-body-md: 14px;
$line-height-body-md: 20px;
$font-size-heading-sm: 16px;
$font-weight-semibold: 600;
```

### Building Component APIs That Match Design

```typescript
// Component API that maps cleanly to design specs
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  icon?: ReactNode;
  loading?: boolean;
  children: ReactNode;
}

// Designers think in variants + states — mirror that in your component API
// Avoids "design drift" where code diverges from Figma
```

### Practical Collaboration Patterns

- **Design reviews** — review Figma specs before coding, flag feasibility or performance issues early
- **Component inventory** — shared understanding of what exists vs. what needs building
- **Responsive behavior specs** — agree on breakpoints and how layouts adapt (don't guess)
- **Interaction specs** — animations, transitions, hover/focus states defined upfront
- **Accessibility requirements** — color contrast, focus indicators, screen reader behavior agreed in design

### What Interviewers Look For

- You proactively consider design intent, not just pixel-perfect implementation
- You push back constructively when a design would harm performance or accessibility
- You suggest improvements: "This animation would cause layout shift — how about a fade instead?"
- You communicate trade-offs: "We can do a custom dropdown or use the native one — here are the costs of each"

---

## 8. Data-Driven Decisions

The listing requires: *"Ability to make data-driven decisions, using tools like Databricks."* This means using product data to inform what you build and how.

### How Frontend Engineers Use Databricks

Databricks at Dropbox isn't just for data engineers — product teams use it for:

- **Feature usage dashboards** — how often is a feature used? By whom? Drop-off points?
- **A/B experiment analysis** — compare conversion metrics between variants
- **Search quality metrics** — click-through rate, time-to-click, query refinement rate
- **Performance monitoring** — real-user latency percentiles (p50, p95, p99) by device/region

### Key Metrics for Dash Experiences

| Metric | What It Tells You | Decision It Drives |
|--------|------------------|--------------------|
| **Search CTR** | Are results relevant? | Ranking changes, UI adjustments |
| **AI answer engagement** | Do users find AI answers useful? | Answer format, citation UX |
| **Time-to-first-click** | How fast do users find what they need? | Result ordering, instant suggestions |
| **Query refinement rate** | Are initial results insufficient? | Autocomplete, filters, query expansion |
| **Connector adoption** | Which integrations do users set up? | Onboarding flow, connector prominence |
| **Feature retention** | Do users keep using Stacks/AI answers? | Feature investment, UX improvements |

### Data-Driven Interview Angle

When discussing past projects, frame decisions with data:
- "We noticed the click-through rate on AI answers was 15% lower than search results, so we added inline citations — CTR improved by 22%"
- "Databricks showed 40% of users never connected a second app, so we redesigned the onboarding flow"
- "We A/B tested two result card layouts — the compact version had 12% higher engagement on mobile"

---

## 9. Testing Strategy

### Component Testing

```typescript
// Testing search results rendering
test('renders results from multiple sources', () => {
  render(<ResultsList results={mockResults} query="budget" />);
  
  expect(screen.getByText('Q3 Budget Report')).toBeInTheDocument();
  expect(screen.getByText('gmail')).toBeInTheDocument();
  expect(screen.getByText('gdrive')).toBeInTheDocument();
});

// Testing streaming AI answer
test('renders streamed AI answer progressively', async () => {
  render(<AIAnswer query="What was Q3 revenue?" />);
  
  // Initially shows loading state
  expect(screen.getByTestId('ai-loading')).toBeInTheDocument();
  
  // After streaming completes
  await waitFor(() => {
    expect(screen.getByText(/Q3 revenue was/)).toBeInTheDocument();
    expect(screen.getByTestId('citation-link')).toBeInTheDocument();
  });
});
```

### Integration Testing

- Test full search flow: type query → see results → click result
- Test filter interactions: apply filter → results update → URL updates
- Test connector management: connect app → see in settings → disconnect

### Accessibility Testing

- Screen reader compatibility for search results
- ARIA labels for dynamic content (AI answers streaming in)
- Focus management during keyboard navigation
- Color contrast for highlighted search terms
- `prefers-reduced-motion` respected for animations
- Touch target sizes on mobile (minimum 44×44px)

---

## 10. Interview-Ready Talking Points

1. **"How would you build a search UI?"** — Debounced input, request cancellation (AbortController), streaming results, progressive rendering (instant suggestions → lexical results → AI answer), keyboard navigation, virtualized list for performance.

2. **"How do you handle data from different sources?"** — Unified result schema with source-specific renderers. Consistent card layout across all sources. Source icon + metadata for attribution.

3. **"What's your approach to state management?"** — Query in local state, filters in URL params, server data in React Query/SWR cache, streaming AI in useReducer. No global store needed for search.

4. **"How do you test AI-powered features?"** — Mock the streaming API, test progressive rendering, test loading/error states, test citation rendering. Snapshot testing for AI answer cards.

5. **"What performance optimizations matter for search?"** — Core Web Vitals as the framework: LCP (fast initial render with code splitting), INP (debounced input, useTransition for non-urgent updates), CLS (reserved space for AI answer). Plus: virtualized lists, memoized result cards, lazy-loaded images, bundle analysis.

6. **"How do you build UIs for AI features?"** — State machine for AI answer states (searching → generating → complete → error). Progressive disclosure: results first, AI answer streams below. Inline citations for trust. Feedback buttons for quality signal. Graceful degradation when AI is slow or fails.

7. **"How do you work with designers?"** — Design tokens as shared source of truth. Component APIs that mirror design specs (variants, sizes, states). Proactive design reviews before coding. Constructive pushback on performance or accessibility concerns. Responsive behavior agreed upfront, not guessed.

8. **"How do you make data-driven product decisions?"** — Use Databricks dashboards to track feature usage, search quality metrics (CTR, time-to-click), and A/B experiment results. Frame feature work around measurable outcomes. Example: "AI answer citation click-through was low, so we redesigned the source attribution — engagement went up X%."

9. **"How do you handle responsive design for a product like Dash?"** — Mobile-first CSS, container queries for component-level responsiveness, adaptive layouts (collapsible sidebar, touch-friendly targets on mobile), test across breakpoints. Consider that Dash runs on web, mobile, and desktop surfaces.

10. **"Tell me about Dropbox's frontend architecture."** — Edison (Go + Node.js web server), pagelet architecture where each section is an independent React app. SPA bundles deploy to CDN. gRPC/Courier for data fetching. Rollup for bundling (33% size reduction from custom bundler). DIG design system at 87% adoption. Redux with code-splitting for state management. SCSS + BEM for styling.

---

## 11. Vanilla JS & React Interview Prep

> **For this role:** The coding rounds are confirmed as React/TypeScript (Interview 1) and React/TypeScript + Python (Interview 2). The React challenges below are your primary prep target. The vanilla JS section is still valuable — understanding what React abstracts away strengthens your React code and helps if interviewers probe fundamentals. Historically, some Dropbox frontend roles tested vanilla JS exclusively.

### Vanilla JS: What Dropbox Tests

**Reported coding challenges:**
1. **`getByClassName(root, className)`** — return all DOM nodes matching a class name without using native browser APIs. Requires recursive DOM traversal.
2. **`getByClassHierarchy(root, "a>d")`** — match nodes by a hierarchical class relationship.
3. **`getElementsByTagName`** — implement DOM element retrieval by tag name.
4. **Image carousel** — build a fully functional carousel with vanilla JS, HTML, and CSS. No frameworks.
5. **Image gallery** — build an interactive gallery.
6. **Template rendering** — implement `loadTemplate` and `render` functions.

**Reported debugging round:**
- You're dropped into a **buggy vanilla JS codebase** and must reproduce and fix bugs
- No unit tests provided — describing how you'd write tests earns bonus points
- Common gotchas interviewers watch for:
  - Not knowing `for...in` vs. `for...of`
  - Not knowing browser APIs (`addEventListener`, `getElementById`, `fetch`) because you only know framework abstractions
  - Only knowing HTML as React JSX, not actual HTML elements and attributes

### Vanilla JS: DOM Fundamentals to Practice

```javascript
// DOM traversal — the core of getByClassName
function getByClassName(root, className) {
  const results = [];
  
  function traverse(node) {
    // Check if this node has the target class
    if (node.classList && node.classList.contains(className)) {
      results.push(node);
    }
    // Recurse into children
    for (const child of node.children) {
      traverse(child);
    }
  }
  
  traverse(root);
  return results;
}

// Event delegation — handle events on dynamic content
document.querySelector('.results-list').addEventListener('click', (e) => {
  const card = e.target.closest('.result-card');
  if (card) {
    const resultId = card.dataset.resultId;
    navigateToResult(resultId);
  }
});

// createElement + appendChild — building UI without JSX
function createResultCard(result) {
  const card = document.createElement('div');
  card.className = 'c-result-card';
  card.dataset.resultId = result.id;
  
  const title = document.createElement('h3');
  title.textContent = result.title;
  
  const snippet = document.createElement('p');
  snippet.textContent = result.snippet;
  
  card.appendChild(title);
  card.appendChild(snippet);
  return card;
}

// Fetch API — no axios, no React Query
async function searchResults(query) {
  const controller = new AbortController();
  
  try {
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
      signal: controller.signal,
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (err) {
    if (err.name === 'AbortError') return null;
    throw err;
  }
}
```

### Key Vanilla JS Concepts to Review

| Concept | What to Know |
|---------|-------------|
| **DOM traversal** | `children`, `childNodes`, `parentElement`, `closest()`, `querySelector/All` |
| **Event handling** | `addEventListener`, event delegation, `e.target` vs `e.currentTarget`, bubbling vs capturing |
| **`for...in` vs `for...of`** | `for...in` = object keys (strings), `for...of` = iterable values. Explicitly called out as a candidate pitfall. |
| **`this` binding** | Arrow functions vs regular functions, `bind/call/apply` |
| **Closures** | Stale closures in loops, IIFE pattern, closure in event handlers |
| **Promises** | `Promise.all`, `Promise.race`, async/await, error handling |
| **Array methods** | `map`, `filter`, `reduce`, `find`, `some`, `every` — without reaching for lodash |
| **CSS from JS** | `element.style`, `classList.add/remove/toggle`, `getComputedStyle` |

### React Coding Challenges

If the coding round does use React (or for general React interview prep), these are the most commonly reported challenges at senior level:

**The canonical challenge — Autocomplete/Typeahead:**

```typescript
// This single component tests almost everything a senior React dev should know
function Autocomplete({ fetchSuggestions }: Props) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isOpen, setIsOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  
  // Debounced fetch with race condition handling
  useEffect(() => {
    if (!query) { setSuggestions([]); return; }
    
    // Cancel previous request
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    
    const timer = setTimeout(async () => {
      try {
        const results = await fetchSuggestions(query, abortRef.current!.signal);
        setSuggestions(results);
        setIsOpen(true);
      } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') return;
        setSuggestions([]);
      }
    }, 300);
    
    return () => clearTimeout(timer);
  }, [query, fetchSuggestions]);
  
  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex(i => Math.min(i + 1, suggestions.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex(i => Math.max(i - 1, -1));
        break;
      case 'Enter':
        if (activeIndex >= 0) selectSuggestion(suggestions[activeIndex]);
        break;
      case 'Escape':
        setIsOpen(false);
        break;
    }
  };
  
  return (
    <div role="combobox" aria-expanded={isOpen} aria-haspopup="listbox">
      <input
        value={query}
        onChange={e => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        aria-autocomplete="list"
        aria-controls="suggestions-list"
        aria-activedescendant={activeIndex >= 0 ? `suggestion-${activeIndex}` : undefined}
      />
      {isOpen && suggestions.length > 0 && (
        <ul id="suggestions-list" role="listbox">
          {suggestions.map((s, i) => (
            <li
              key={s}
              id={`suggestion-${i}`}
              role="option"
              aria-selected={i === activeIndex}
              onClick={() => selectSuggestion(s)}
            >
              {highlightMatch(s, query)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

**What this tests:** debouncing, race conditions (AbortController), keyboard navigation, ARIA accessibility, controlled input, effect cleanup, state management decisions.

**Other common React challenges:**
- **Infinite scroll** — Intersection Observer, virtualization, loading states, "load more" trigger
- **File explorer / tree view** — recursive rendering, expand/collapse, keyboard navigation
- **Data table** — sorting, filtering, pagination, column resizing
- **Modal dialog** — portals, focus trapping, ARIA roles, Escape to close, click-outside

### Custom Hooks to Know How to Implement

```typescript
// useDebounce — delay value updates
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  
  return debouncedValue;
}

// useClickOutside — detect clicks outside an element
function useClickOutside(ref: RefObject<HTMLElement>, handler: () => void) {
  useEffect(() => {
    const listener = (e: MouseEvent) => {
      if (!ref.current || ref.current.contains(e.target as Node)) return;
      handler();
    };
    document.addEventListener('mousedown', listener);
    return () => document.removeEventListener('mousedown', listener);
  }, [ref, handler]);
}

// usePrevious — track previous value of a prop/state
function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T>();
  useEffect(() => { ref.current = value; });
  return ref.current;
}
```

### Common Senior React Pitfalls

| Pitfall | What Goes Wrong | Fix |
|---------|----------------|-----|
| **Stale closures** | `setInterval` callback reads old state | Use functional updates: `setCount(prev => prev + 1)` |
| **Race conditions** | Multiple fetch calls overwrite state out of order | AbortController + cleanup in useEffect |
| **Over-memoization** | Wrapping everything in memo/useMemo/useCallback | Only memoize when you've measured a performance problem |
| **Inline references** | `style={{...}}` or `onClick={() => ...}` creates new references every render | Extract to useMemo/useCallback only when passed to memoized children |
| **Missing cleanup** | Subscriptions, intervals, or listeners not cleaned up | Return cleanup function from useEffect |
| **Key prop misuse** | Using array index as key in dynamic lists | Use stable, unique identifiers |
