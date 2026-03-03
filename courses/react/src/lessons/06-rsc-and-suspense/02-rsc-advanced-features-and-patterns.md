# RSC Advanced Features and Patterns

Advanced internals and architectural topics for senior-level understanding.

## Table of Contents

1. [Next.js App Router](#nextjs-app-router)
2. [Caching in RSC](#caching-in-rsc)
3. [RSC Wire Protocol (Flight)](#rsc-wire-protocol-flight)
4. [Partial Prerendering (PPR)](#partial-prerendering-ppr)
5. [Server Actions Internals](#server-actions-internals)
6. [ISR vs SSG vs SSR vs Streaming SSR](#isr-vs-ssg-vs-ssr-vs-streaming-ssr)
7. [Edge Rendering](#edge-rendering)
8. [React cache() and Dedupe Patterns](#react-cache-and-dedupe-patterns)
9. [Composition Patterns](#composition-patterns)
10. [Migration: Pages Router to App Router](#migration-pages-router-to-app-router)

---

## Next.js App Router

### File conventions

```
app/
  layout.tsx       // Root layout (persists across navigations)
  page.tsx         // Home (/)
  loading.tsx      // Suspense fallback
  error.tsx        // Error boundary (must be client component)
  not-found.tsx    // 404
  global-error.tsx // Catches root layout errors

  dashboard/
    layout.tsx     // Nested layout
    page.tsx       // /dashboard
    loading.tsx    // Dashboard loading state
    error.tsx      // Dashboard error boundary
    template.tsx   // Like layout but RE-MOUNTS on navigation
    [teamId]/
      page.tsx     // /dashboard/:teamId

  (marketing)/     // Route group (no URL segment)
    about/page.tsx // /about

  @modal/          // Parallel route (named slot)
    login/page.tsx
```

### File Convention Reference

| File | Purpose | Component Type |
|---|---|---|
| `layout.tsx` | Shared UI for segment and children. Persists across navigations. | Server (default) |
| `page.tsx` | Unique UI for a route. Makes the route publicly accessible. | Server (default) |
| `loading.tsx` | Loading UI (auto-wrapped in Suspense). | Server (default) |
| `error.tsx` | Error UI (auto-wrapped in Error Boundary). | **Must be Client** |
| `template.tsx` | Like layout but re-mounts on navigation. | Server (default) |
| `not-found.tsx` | 404 UI for the segment. | Server (default) |
| `global-error.tsx` | Root-level error boundary (catches layout errors). | **Must be Client** |
| `route.ts` | API endpoint (GET, POST, PUT, DELETE, PATCH). | N/A (handler) |
| `default.tsx` | Fallback for parallel routes when no match. | Server (default) |
| `middleware.ts` | Runs before every request (at `/` root only). | Edge Runtime |

### Layout vs Template

**Layout** persists across navigations (state preserved). **Template** re-mounts on every navigation (useful for animations, per-page analytics, resetting state).

### Nesting order (what wraps what)

```
<Layout>
  <Template>
    <ErrorBoundary fallback={<Error />}>
      <Suspense fallback={<Loading />}>
        <Page />
      </Suspense>
    </ErrorBoundary>
  </Template>
</Layout>
```

---

## Caching in RSC

### Fetch caching

```tsx
await fetch(url);                                  // Cached indefinitely (default)
await fetch(url, { next: { revalidate: 60 } });    // Revalidate every 60s
await fetch(url, { cache: 'no-store' });            // Never cache
await fetch(url, { next: { tags: ['posts'] } });    // Tag-based revalidation
```

### Route-Level Config

```tsx
export const dynamic = 'force-dynamic';  // No caching
export const dynamic = 'force-static';   // Build-time only
export const revalidate = 60;            // Revalidation interval (seconds)
export const dynamicParams = true;       // Allow params beyond generateStaticParams
```

### Non-fetch caching

```tsx
import { unstable_cache } from 'next/cache';

const getCachedUser = unstable_cache(
  async (id: string) => db.user.findUnique({ where: { id } }),
  ['user-by-id'],
  { revalidate: 3600, tags: ['users'] }
);
```

### Four caching layers

```
1. Request Memoization   -- Dedupes identical requests within ONE render pass
2. Data Cache            -- Persists across requests; controlled by revalidate/tags
3. Full Route Cache      -- Build-time HTML + RSC payload for static routes
4. Router Cache          -- Client-side RSC payload cache (0s dynamic, 5min static)
```

### Cache Layers Summary

```
Request Memoization  -> Per-request dedupe         -> Automatic for fetch, manual via cache()
Data Cache           -> Cross-request persistence   -> Controlled via fetch options / unstable_cache
Full Route Cache     -> Build-time HTML + RSC cache -> Static routes only, invalidated with data cache
Router Cache         -> Client-side nav cache       -> 0s dynamic, 5min static (Next.js 15)
```

### On-demand revalidation

```tsx
import { revalidatePath, revalidateTag } from 'next/cache';

revalidatePath('/profile');          // Specific path
revalidatePath('/profile', 'layout'); // Path + all sub-pages
revalidateTag('posts');               // All fetches tagged 'posts'
```

---

## RSC Wire Protocol (Flight)

The Flight protocol is the serialization format React uses to represent server-rendered component trees. It is a **line-delimited** streaming format.

### Payload format

```
0:"$Sreact.suspense"
1:["$","div",null,{"className":"page","children":[["$","h1",null,{"children":"Dashboard"}],["$","$L2",null,{"data":[{"id":1,"name":"Alice"}]}]]}]
2:I["./ClientChart.js","ClientChart"]
```

Each line: `ID:TYPE_PREFIX JSON_DATA`. Key row types:

- No prefix / `J` -- serialized React element tree
- `I` -- client module reference (import pointer)
- `S` -- Symbol (`react.suspense`, `react.fragment`)
- `HL` -- Hint (preload directive)
- `$L` -- lazy reference (not yet resolved)
- `$` -- React element `["$", type, key, props]`

### Serialization behavior

Server components execute and their output is inlined as React elements. Client components are NOT executed on the server in this phase -- they become **module references** (`I["./ClientChart.js", "ClientChart"]`). Props crossing the boundary are serialized inline with the reference.

As async components resolve, new lines are appended to the stream:

```
// Initial (immediate):
0:["$","div",null,{"children":["$","$Sreact.suspense",null,{"fallback":"Loading...","children":"$L1"}]}]

// Streamed later when async component resolves:
1:["$","p",null,{"children":"Resolved content"}]
```

### Navigation payloads

Client-side navigation fetches the RSC payload (not HTML) via `Accept: text/x-component`. React reconciles the payload against the current tree for SPA-like transitions with server-rendered content.

---

## Partial Prerendering (PPR)

PPR combines **static** and **dynamic** content in a single HTTP response -- the convergence of ISR and streaming SSR.

```tsx
export default function ProductPage({ params }: { params: { id: string } }) {
  return (
    <div>
      <Header />                        {/* STATIC: built at build time */}
      <ProductDetails id={params.id} /> {/* STATIC */}

      <Suspense fallback={<PriceSkeleton />}>
        <DynamicPrice id={params.id} /> {/* DYNAMIC: uses cookies */}
      </Suspense>

      <Suspense fallback={<ReviewsSkeleton />}>
        <LiveReviews id={params.id} />  {/* DYNAMIC: real-time data */}
      </Suspense>

      <Footer />                        {/* STATIC */}
    </div>
  );
}
```

**Build time:** Static content outside Suspense is prerendered. Suspense fallbacks become placeholder holes.
**Request time:** Edge serves prerendered HTML instantly (TTFB = CDN latency). Server streams dynamic content into the Suspense holes.

Content becomes dynamic when it accesses `cookies()`, `headers()`, or uncached data. Enable with `experimental: { ppr: true }` in `next.config.ts`.

---

## Server Actions Internals

### How form submissions become RPC calls

1. React generates a unique **action ID** for each server action at build time.
2. A hidden `$ACTION_ID` field is injected into the form.
3. On submit: POST to the current URL with form data + action ID.
4. Server looks up the action by ID, deserializes arguments, executes.
5. Response is an RSC payload reflecting the updated UI.

```
POST /dashboard HTTP/1.1
Content-Type: multipart/form-data
$ACTION_ID: abc123def456
name: Alice
-->
Server: lookup abc123def456 -> createUser(formData)
     -> revalidatePath('/dashboard')
     -> re-render /dashboard as RSC payload
     -> respond with RSC payload
-->
Client: React reconciles -> DOM updates (no full reload)
```

### Bound arguments

`.bind()` pre-binds server-side values to actions. Bound arguments are **encrypted** by Next.js before being sent as hidden form fields -- the client cannot tamper with them.

```tsx
export default async function UserList() {
  const users = await getUsers();
  return users.map(user => {
    const deleteWithId = deleteUser.bind(null, user.id); // id encrypted
    return (
      <form key={user.id} action={deleteWithId}>
        <span>{user.name}</span>
        <button type="submit">Delete</button>
      </form>
    );
  });
}
```

### Optimistic updates with server actions

```tsx
'use client';
import { useOptimistic } from 'react';
import { addTodo } from '@/app/actions';

export function TodoList({ todos }: { todos: Todo[] }) {
  const [optimisticTodos, addOptimistic] = useOptimistic(
    todos,
    (state: Todo[], newText: string) => [
      ...state,
      { id: `temp-${Date.now()}`, text: newText, completed: false },
    ]
  );

  async function handleSubmit(formData: FormData) {
    const text = formData.get('text') as string;
    addOptimistic(text);       // Immediate UI update
    await addTodo(formData);    // Server round-trip
  }

  return (
    <form action={handleSubmit}>
      <input name="text" />
      <button>Add</button>
      <ul>{optimisticTodos.map(t => <li key={t.id}>{t.text}</li>)}</ul>
    </form>
  );
}
```

---

## ISR vs SSG vs SSR vs Streaming SSR

| Strategy | Rendered When | Data Freshness | TTFB | Best For |
|---|---|---|---|---|
| **SSG** | Build time only | Stale until rebuild | Fastest (CDN) | Docs, marketing, blogs |
| **ISR** | Build + background revalidation | Stale-while-revalidate | Fast (CDN) | Product pages, catalogs |
| **SSR** | Every request | Always fresh | Slower (origin) | Personalized dashboards |
| **Streaming SSR** | Every request, progressive | Always fresh | Fast shell + streamed | Mixed-speed data pages |

### ISR at scale

```tsx
// Generate top 1000 products at build time; rest on-demand
export async function generateStaticParams() {
  const top = await db.product.findMany({ orderBy: { views: 'desc' }, take: 1000 });
  return top.map(p => ({ slug: p.slug }));
}

export const dynamicParams = true;  // Unknown slugs generated on-demand
export const revalidate = 3600;     // Revalidate every hour
```

---

## Edge Rendering

Edge functions run in **V8 isolates** -- lightweight sandboxes with near-zero cold starts (~0-5ms vs ~250ms for Node.js).

```
Node.js Runtime:              Edge Runtime:
  Full Node.js APIs             Web API subset
  File system access            No file system
  Any npm package               Limited packages (bundle size limits)
  ~250ms cold start             ~0-5ms cold start
  Single region                 Every CDN PoP globally
  Unlimited execution time      Limited (30s on Vercel)
```

Opt in with `export const runtime = 'edge';` on pages or route handlers.

**Cannot use:** `fs`, `path`, most ORMs without edge adapters, large packages, persistent connections.
**Can use:** `fetch`, Web Crypto, edge-compatible DBs (Planetscale, Neon, Turso, Upstash), KV stores.

---

## React cache() and Dedupe Patterns

### Automatic fetch() deduplication

Identical `fetch()` calls within a single render are automatically deduplicated by React.

### Manual deduplication with cache()

```tsx
import { cache } from 'react';

export const getUser = cache(async (id: string) => {
  return db.user.findUnique({ where: { id }, include: { profile: true } });
});
// Component A calls getUser('123') -> executes query
// Component B calls getUser('123') -> returns memoized result (same render)
```

### cache() vs unstable_cache()

```
React.cache():
  - Dedupes within ONE request/render
  - No persistence across requests
  - Use for: avoiding redundant work in a single render

unstable_cache():
  - Persists across MULTIPLE requests
  - Supports time-based + tag-based revalidation
  - Use for: caching expensive ops across requests
```

Combine both for maximum efficiency:

```tsx
const getCachedAnalytics = unstable_cache(
  async (teamId: string) => db.analytics.aggregate({ where: { teamId } }),
  ['team-analytics'],
  { revalidate: 300, tags: ['analytics'] }
);

// Per-request dedupe wrapping cross-request cache
export const getAnalytics = cache(async (teamId: string) => {
  return getCachedAnalytics(teamId);
});
```

---

## Composition Patterns

### The donut pattern

Client component wraps server content via `children`:

```tsx
// ClientAnimationWrapper.tsx
'use client';
import { motion } from 'framer-motion';
export function ClientAnimationWrapper({ children }: { children: React.ReactNode }) {
  return <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>{children}</motion.div>;
}

// ServerPage.tsx -- server content flows through the client wrapper
import { ClientAnimationWrapper } from './ClientAnimationWrapper';
export default async function ServerPage() {
  const data = await fetchData();
  return <ClientAnimationWrapper><h1>{data.title}</h1><ServerContent data={data} /></ClientAnimationWrapper>;
}
```

### Provider pattern

Single `"use client"` entry for all context providers:

```tsx
// Providers.tsx
'use client';
export function Providers({ children }: { children: React.ReactNode }) {
  return <AuthProvider><ThemeProvider><QueryProvider>{children}</QueryProvider></ThemeProvider></AuthProvider>;
}

// app/layout.tsx (server component)
import { Providers } from './Providers';
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html><body><Providers>{children}</Providers></body></html>;
}
```

### Minimize the client boundary

Extract only the interactive part into a client component:

```tsx
// ProductCard.tsx (SERVER component -- no directive)
export function ProductCard({ product }: { product: Product }) {
  return (
    <div>
      <Image src={product.image} alt={product.name} />
      <h3>{product.name}</h3>
      <p>{product.description}</p>
      <AddToCartButton productId={product.id} /> {/* Only this is client */}
    </div>
  );
}

// AddToCartButton.tsx
'use client';
export function AddToCartButton({ productId }: { productId: string }) {
  const [isPending, startTransition] = useTransition();
  return (
    <button onClick={() => startTransition(() => addToCart(productId))} disabled={isPending}>
      {isPending ? 'Adding...' : 'Add to Cart'}
    </button>
  );
}
```

---

## Migration: Pages Router to App Router

### Incremental strategy

Both routers coexist. Migrate route by route.

```
Phase 1: Add /app alongside /pages. Migrate simple pages first.
Phase 2: Create app/layout.tsx (replaces _app.tsx + _document.tsx). Move providers.
Phase 3: Migrate data fetching:
  - getServerSideProps  -> async server component
  - getStaticProps      -> async server component + export const revalidate
  - getStaticPaths      -> generateStaticParams()
  - API routes for data -> direct DB access in server components
Phase 4: Move pages one by one. Convert useEffect fetching to RSC.
Phase 5: Remove /pages directory.
```

### Key API changes

```
useRouter: next/router -> next/navigation
router.query.id -> params.id (page props) or useParams()
router.events -> No equivalent; use usePathname() + useEffect
Head from next/head -> export const metadata / generateMetadata()
_error.tsx -> error.tsx per segment
```

### Pitfalls

- Same route in both `/pages` and `/app` = conflict.
- App Router `router.push()` does soft navigation (RSC payload); Pages Router does full navigation.
- Client components need explicit `"use client"` -- nothing is implicitly client anymore.
- Global CSS imports must go in `app/layout.tsx`.
- Middleware works with both routers; no changes needed.

---

## Practice

- **Caching strategy exercise**: For a blog with posts and comments, design the caching strategy: which routes use `force-cache`, which use `no-store`, and which use `revalidate`? Justify each choice.
- **Server action**: Build a form that submits via a server action (not an API route). Use `useActionState` to track pending state and display form-level errors. Verify it works with and without JavaScript.
- **PPR mental model**: Take an e-commerce product page and identify: (1) the static shell (product name, images, description), (2) the dynamic holes (price, stock status, reviews). Sketch how PPR would serve this.
- **Migration planning**: If you have a Next.js Pages Router project, plan the migration to App Router for one route. Identify: `getServerSideProps` to replace, `useRouter` imports to update, and providers to move to `layout.tsx`.
- **Flight protocol trace**: Open the Network tab on a Next.js App Router app and navigate between pages. Find the RSC payload requests (look for `?_rsc=` or `text/x-component`). Examine the payload format.

### Related Lessons

- [Server Components & Suspense](01-server-components-and-suspense.md) -- fundamentals of server vs client components, Suspense boundaries, streaming SSR
- [Performance: Tools & Advanced Patterns](../03-performance/02-performance-tools-and-advanced-patterns.md) -- code splitting, selective hydration, and bundle optimization in the context of SSR
- [State Management Libraries](../05-state-management/02-state-libraries-and-solutions.md) -- TanStack Query for client-side data caching alongside RSC server-side fetching
