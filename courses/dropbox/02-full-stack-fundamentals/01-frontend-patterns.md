# 01 – Frontend Patterns

The frontend stack for Dropbox Dash: React + TypeScript, API-QL, and the UI patterns that matter for building AI-powered search experiences.

---

## 1. Dropbox Frontend Stack

| Technology | Role |
|-----------|------|
| **React** | Primary UI framework |
| **TypeScript** | Type safety across the frontend |
| **API-QL** | Client-side GraphQL layer bridging Apollo and REST |
| **react-testing-library** | Component and integration testing |
| **HTML/CSS** | Standard web technologies |

### API-QL: Dropbox's Internal Pattern

This is the most Dropbox-specific thing about the frontend. API-QL is a lightweight GraphQL server that runs **in the client**, not on a backend server.

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

## 4. Performance Patterns

### Code Splitting

Dash has multiple product surfaces (search, Stacks, settings, connectors). Split by route:

```typescript
const Search = lazy(() => import('./pages/Search'));
const Stacks = lazy(() => import('./pages/Stacks'));
const Settings = lazy(() => import('./pages/Settings'));
```

### Memoization

Search result rendering is expensive with highlight matching:

```typescript
const MemoizedResultCard = memo(ResultCard, (prev, next) => 
  prev.result.id === next.result.id && prev.query === next.query
);
```

### Image Optimization

Dash shows file previews and thumbnails:
- Lazy load images below the fold
- Use `srcset` for responsive images
- Show placeholder/skeleton until image loads
- Cache thumbnails aggressively

---

## 5. Testing Strategy

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

---

## 6. Interview-Ready Talking Points

1. **"How would you build a search UI?"** — Debounced input, request cancellation (AbortController), streaming results, progressive rendering (instant suggestions → lexical results → AI answer), keyboard navigation, virtualized list for performance.

2. **"How do you handle data from different sources?"** — Unified result schema with source-specific renderers. Consistent card layout across all sources. Source icon + metadata for attribution.

3. **"What's your approach to state management?"** — Query in local state, filters in URL params, server data in React Query/SWR cache, streaming AI in useReducer. No global store needed for search.

4. **"How do you test AI-powered features?"** — Mock the streaming API, test progressive rendering, test loading/error states, test citation rendering. Snapshot testing for AI answer cards.

5. **"What performance optimizations matter for search?"** — Debouncing, request cancellation, virtualized lists, code splitting by route, memoized result cards, lazy-loaded images, aggressive caching of recent search results.
