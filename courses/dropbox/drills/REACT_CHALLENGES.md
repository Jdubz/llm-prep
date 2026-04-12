# React Onsite Coding Challenges

Practice challenges for the **frontend coding interview** (Interview 1: React/TypeScript) and the **full-stack coding interview** (Interview 2: React/TypeScript + Python).

**Environment:** CodeSignal live IDE with Monaco editor, integrated terminal, npm, and live preview at port 3000. Starter code/boilerplate is typically provided.

**Format:** Single problem with 3-4 escalating phases. 1 hour total. **AI is strictly prohibited.**

**How to practice:** Use a local Vite + React + TypeScript project. Set a 60-minute timer. Build each challenge from the starter code without AI assistance.

---

## Setup

```bash
# Create a practice environment (one-time)
npm create vite@latest dropbox-react-drills -- --template react-ts
cd dropbox-react-drills
npm install
npm run dev
# Open http://localhost:5173
```

---

## Challenge 01 — File Search UI

**Simulates:** The Dash search experience. This is the most likely frontend challenge for a Dash Experiences role.

**Time:** 60 minutes

### Phase 1 — Search Input with Results (15 min)

Build a search interface that:
- Has a text input for the search query
- Filters a provided list of files by name (case-insensitive substring match)
- Displays matching files as a list with name, size, and source icon
- Shows "No results" when nothing matches

```typescript
// Starter data provided
const FILES = [
  { id: "1", name: "Q3 Budget Report.xlsx", size: 245000, source: "gdrive", modified: "2025-12-01" },
  { id: "2", name: "Sprint Planning Notes", size: 12000, source: "notion", modified: "2025-12-10" },
  { id: "3", name: "Budget Review Meeting", size: 0, source: "gcal", modified: "2025-12-15" },
  { id: "4", name: "RE: Q3 Budget Questions", size: 8500, source: "gmail", modified: "2025-11-28" },
  { id: "5", name: "#finance-team discussion", size: 3200, source: "slack", modified: "2025-12-12" },
  // ... 20+ items
];
```

### Phase 2 — Debounced API Search (15 min)

Replace client-side filtering with simulated API calls:
- Debounce the search input (300ms)
- Show a loading indicator while searching
- Cancel in-flight requests when the query changes (AbortController)
- Handle error states

```typescript
// Simulated API (provided)
async function searchAPI(query: string, signal: AbortSignal): Promise<File[]> {
  await new Promise(r => setTimeout(r, 500 + Math.random() * 500));
  if (signal.aborted) throw new DOMException("Aborted", "AbortError");
  return FILES.filter(f => f.name.toLowerCase().includes(query.toLowerCase()));
}
```

### Phase 3 — Keyboard Navigation (15 min)

Add full keyboard support:
- Arrow up/down to navigate results
- Enter to select (log to console)
- Escape to clear the search
- Active item highlighted visually
- Scroll active item into view

### Phase 4 — Source Filtering + URL State (15 min)

- Add filter chips for each source (Gmail, Slack, GDrive, etc.)
- Clicking a chip toggles that source on/off
- Active filters are reflected in the URL (`?q=budget&source=gmail,gdrive`)
- Refreshing the page restores the search state from the URL
- Show result count per source

### What They Evaluate

- Component decomposition (separate SearchInput, ResultCard, FilterChips, etc.)
- Correct hooks usage (useEffect cleanup, dependency arrays)
- TypeScript types (no `any`)
- Race condition handling
- Accessibility (ARIA combobox pattern, keyboard nav)
- Loading/error/empty states

---

## Challenge 02 — Chunked File Upload

**Simulates:** The full-stack coding interview. React frontend + Python-style backend logic.

**Time:** 60 minutes

### Phase 1 — File Picker + Upload (15 min)

Build a file upload component:
- Drag-and-drop zone that accepts files
- Click to browse (file input)
- Show file name, size (human-readable), and type after selection
- "Upload" button that sends the file to a simulated endpoint

```typescript
// Simulated upload (provided)
async function uploadFile(file: File): Promise<{ id: string }> {
  await new Promise(r => setTimeout(r, 1000));
  return { id: crypto.randomUUID() };
}
```

### Phase 2 — Chunked Upload with Progress (15 min)

Replace single upload with chunked upload:
- Split file into 1MB chunks
- Upload chunks sequentially
- Show progress bar (chunks uploaded / total chunks)
- Show upload speed estimate

```typescript
async function uploadChunk(
  uploadId: string, chunkIndex: number, data: Blob
): Promise<void> {
  await new Promise(r => setTimeout(r, 200 + Math.random() * 300));
}
```

### Phase 3 — Pause/Resume/Cancel (15 min)

- Pause button: stops uploading after current chunk completes
- Resume button: continues from where it left off
- Cancel button: aborts current chunk, resets progress
- State machine: idle → uploading → paused → uploading → complete (or error)

### Phase 4 — Multiple Concurrent Uploads (15 min)

- Support uploading multiple files simultaneously
- Each file shows independent progress
- Limit concurrent uploads to 3 (queue additional files)
- Show overall progress across all uploads
- Allow canceling individual uploads

### What They Evaluate

- State machine design (upload lifecycle)
- File API knowledge (File, Blob, slice)
- Progress tracking accuracy
- Pause/resume correctness (no lost or duplicated chunks)
- Component architecture (reusable UploadItem component)
- Error handling and recovery

---

## Challenge 03 — Streaming AI Answer Card

**Simulates:** Dash AI answer rendering — the core Dash Experiences feature.

**Time:** 60 minutes

### Phase 1 — Static Answer Card (12 min)

Build a card component that displays:
- A question at the top
- An answer body (markdown-like text)
- A list of source citations at the bottom (app icon + title + link)
- A "thumbs up / thumbs down" feedback row

```typescript
type AIAnswer = {
  question: string;
  answer: string;
  sources: { title: string; url: string; app: "gmail" | "slack" | "gdrive" | "notion" }[];
};
```

### Phase 2 — Streaming Render (18 min)

Replace static answer with token-by-token streaming:
- Answer text streams in word by word (simulated with a generator)
- Show a blinking cursor at the end while streaming
- Sources appear after streaming completes
- Feedback buttons appear after sources

```typescript
// Simulated streaming (provided)
async function* streamAnswer(question: string): AsyncGenerator<string> {
  const words = "Based on your documents, the Q3 revenue was $4.2M, representing a 15% increase over Q2. The primary growth driver was the enterprise segment, which grew 23% quarter-over-quarter.".split(" ");
  for (const word of words) {
    await new Promise(r => setTimeout(r, 50 + Math.random() * 100));
    yield word + " ";
  }
}
```

### Phase 3 — Inline Citations (15 min)

- Answer text now contains citation markers: `[1]`, `[2]`, etc.
- Render citation markers as clickable superscript links
- Hovering a citation shows a tooltip with the source title and app
- Clicking opens the source URL in a new tab
- Citations map to the sources array by index

### Phase 4 — Error Recovery + Retry (15 min)

- Handle stream interruption (simulated: 20% chance of error mid-stream)
- Show "Answer generation failed" with a "Retry" button
- On retry, restart the stream from the beginning
- If the answer is partially streamed when error occurs, keep what was received and show "[incomplete]"
- Add a "Copy answer" button that copies the full text (only when complete)

### What They Evaluate

- Async generator / streaming consumption
- Progressive UI rendering (no flash of complete content)
- Citation parsing and inline rendering
- Error boundary thinking
- Copy-to-clipboard API
- Clean component decomposition

---

## Challenge 04 — Connector Settings Panel

**Simulates:** Dash connector management UI.

**Time:** 60 minutes

### Phase 1 — Connected Apps List (12 min)

Display a list of connected SaaS apps:
- Each shows: app name, icon, connection status (connected/disconnected/syncing), last sync time
- "Connect" button for disconnected apps
- "Disconnect" button for connected apps

```typescript
type Connector = {
  id: string;
  name: string;
  icon: string;  // emoji or letter
  status: "connected" | "disconnected" | "syncing";
  lastSync: string | null;  // ISO date string
  documentCount: number;
};
```

### Phase 2 — Connect/Disconnect with Optimistic UI (15 min)

- Clicking "Connect" → immediately shows "syncing" state → simulated API call → resolves to "connected"
- Clicking "Disconnect" → immediately shows "disconnected" → simulated API call → resolves
- On API failure: roll back to previous state, show error toast
- Disable the button during the API call

### Phase 3 — Search Within Connectors (15 min)

- Add a search bar that filters connectors by name
- Add tabs: "All", "Connected", "Disconnected"
- Tab counts update in real time
- Empty state for filtered results: "No apps match your search"

### Phase 4 — Sync Details Drawer (18 min)

- Clicking a connected app opens a side drawer/panel
- Drawer shows: sync history (last 5 syncs with timestamp + document count), indexed document count, storage used
- Drawer has a "Force Sync" button
- Drawer closes on Escape or clicking outside
- Focus traps inside the drawer while open (accessibility)

### What They Evaluate

- Optimistic UI pattern (show expected state, rollback on error)
- Tab/filter composition
- Drawer/panel component (portal, focus trap, escape handling)
- Loading/error state management
- Accessible interactive patterns

---

## Full-Stack Challenges (Interview 2)

These challenges span React/TypeScript on the frontend AND Python on the backend. In practice, you'd have both files open in CodeSignal's IDE.

**Framework note:** Dropbox uses a custom proprietary Python framework (not
Flask/Django/FastAPI), with gRPC for service communication. For the interview,
the Python backend is likely plain Python with simple HTTP handling (e.g.,
`http.server` or a minimal provided harness) — focus on clean data modeling and
API design rather than framework-specific patterns.

### Challenge 05 — File Explorer with Python API

**Phase 1:** Python backend: implement `list_files(path)`, `create_file(path, content)`, `delete_file(path)` with in-memory filesystem.

**Phase 2:** React frontend: file tree component, click to navigate folders, show file contents in a preview pane.

**Phase 3:** Add file upload: drag file onto a folder in the tree → call Python API → update tree.

**Phase 4:** Add search: search bar that calls Python API `search(query)` → highlight matching files in tree.

### Challenge 06 — Activity Feed with Python Backend

**Phase 1:** Python backend: `record_event(user, action, resource)`, `get_events(limit)` — in-memory event store.

**Phase 2:** React frontend: scrollable activity feed showing events with user avatar, action description, timestamp (relative: "2 min ago").

**Phase 3:** Add filtering: filter by user, action type, date range. Filters call the Python API.

**Phase 4:** Add real-time updates: polling every 5 seconds for new events, new events slide in at the top with animation.

---

## Practice Tips

1. **Time yourself strictly.** In the real interview, 60 minutes goes fast. Practice stopping at the timer even if you're mid-phase.
2. **Talk out loud** while building. Narrate your component decomposition, state decisions, and trade-offs.
3. **Start with types.** Define your TypeScript interfaces first — it structures your thinking and impresses interviewers.
4. **Handle states early.** Loading, error, and empty states should be in Phase 1, not afterthoughts.
5. **Don't over-style.** Basic CSS is fine. They care about logic, not pixel-perfection.
6. **Ask "are there more parts?"** In the real interview, the interviewer will keep adding requirements.
