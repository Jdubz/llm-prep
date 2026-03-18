/*
TypeScript Interview Toolbox — Speed Reference

Patterns you reach for without thinking. Run this file to verify
everything works: npx tsx drills/toolbox.ts

Organized by problem shape, not by data structure.
*/

// ═══════════════════════════════════════════════════════════════
// 1. LOOKUP / DEDUP / COUNTING — use Map and Set
// ═══════════════════════════════════════════════════════════════

// Count occurrences
function countBy<T>(items: T[], key: (item: T) => string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const item of items) {
    const k = key(item);
    counts.set(k, (counts.get(k) ?? 0) + 1);
  }
  return counts;
}

// Group items by key
function groupBy<T>(items: T[], key: (item: T) => string): Map<string, T[]> {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const k = key(item);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k)!.push(item);
  }
  return groups;
}

// Deduplicate by key (keeps first occurrence)
function dedupBy<T>(items: T[], key: (item: T) => string): T[] {
  const seen = new Set<string>();
  return items.filter(item => {
    const k = key(item);
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

// Index by unique key (last wins)
function indexBy<T>(items: T[], key: (item: T) => string): Map<string, T> {
  const index = new Map<string, T>();
  for (const item of items) index.set(key(item), item);
  return index;
}

// ═══════════════════════════════════════════════════════════════
// 2. SORTING — multi-key comparators
// ═══════════════════════════════════════════════════════════════

// Sort by multiple keys: negative = descending, positive = ascending
// Usage: items.sort(multiSort(x => -x.score, x => x.name))
function multiSort<T>(...fns: ((item: T) => string | number)[]): (a: T, b: T) => number {
  return (a, b) => {
    for (const fn of fns) {
      const va = fn(a), vb = fn(b);
      if (va < vb) return -1;
      if (va > vb) return 1;
    }
    return 0;
  };
}

// Quick pattern: sort descending by number, ascending by string for ties
// items.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));

// Top-N without full sort (for large arrays)
function topN<T>(items: T[], n: number, cmp: (a: T, b: T) => number): T[] {
  return [...items].sort(cmp).slice(0, n);
}

// ═══════════════════════════════════════════════════════════════
// 3. STRING PARSING — CSV, key=value, templates
// ═══════════════════════════════════════════════════════════════

// Parse CSV (handles basic cases, not quoted commas)
function parseCSV(raw: string): { headers: string[]; rows: Record<string, string>[] } {
  const lines = raw.trim().split("\n");
  const headers = lines[0].split(",").map(h => h.trim());
  const rows = lines.slice(1).map(line => {
    const vals = line.split(",").map(v => v.trim());
    const row: Record<string, string> = {};
    headers.forEach((h, i) => (row[h] = vals[i] ?? ""));
    return row;
  });
  return { headers, rows };
}

// Parse key=value lines (like config files)
function parseKV(raw: string): Map<string, string> {
  const result = new Map<string, string>();
  for (const line of raw.trim().split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx === -1) continue;
    result.set(trimmed.slice(0, idx).trim(), trimmed.slice(idx + 1).trim());
  }
  return result;
}

// ═══════════════════════════════════════════════════════════════
// 4. TIME / SLIDING WINDOW — rate limiting, scheduling
// ═══════════════════════════════════════════════════════════════

// Sliding window rate limiter
class SlidingWindowRateLimiter {
  private windows = new Map<string, number[]>();
  constructor(private maxRequests: number, private windowMs: number) {}

  allow(key: string, now: number = Date.now()): boolean {
    const timestamps = this.windows.get(key) ?? [];
    const cutoff = now - this.windowMs;
    // Remove expired timestamps
    while (timestamps.length > 0 && timestamps[0] <= cutoff) timestamps.shift();
    if (timestamps.length >= this.maxRequests) return false;
    timestamps.push(now);
    this.windows.set(key, timestamps);
    return true;
  }
}

// Fixed window rate limiter (simpler, faster)
class FixedWindowRateLimiter {
  private windows = new Map<string, { count: number; windowStart: number }>();
  constructor(private maxRequests: number, private windowMs: number) {}

  allow(key: string, now: number = Date.now()): boolean {
    const entry = this.windows.get(key);
    const windowStart = Math.floor(now / this.windowMs) * this.windowMs;
    if (!entry || entry.windowStart !== windowStart) {
      this.windows.set(key, { count: 1, windowStart });
      return true;
    }
    if (entry.count >= this.maxRequests) return false;
    entry.count++;
    return true;
  }
}

// ═══════════════════════════════════════════════════════════════
// 5. GRAPH / UNION-FIND — transitive relationships, cycle detection
// ═══════════════════════════════════════════════════════════════

class UnionFind {
  private parent: Map<string, string> = new Map();
  private rank: Map<string, number> = new Map();

  find(x: string): string {
    if (!this.parent.has(x)) {
      this.parent.set(x, x);
      this.rank.set(x, 0);
    }
    if (this.parent.get(x) !== x) {
      this.parent.set(x, this.find(this.parent.get(x)!)); // path compression
    }
    return this.parent.get(x)!;
  }

  union(x: string, y: string): void {
    const rx = this.find(x), ry = this.find(y);
    if (rx === ry) return;
    const rankX = this.rank.get(rx)!, rankY = this.rank.get(ry)!;
    if (rankX < rankY) { this.parent.set(rx, ry); }
    else if (rankX > rankY) { this.parent.set(ry, rx); }
    else { this.parent.set(ry, rx); this.rank.set(rx, rankX + 1); }
  }

  connected(x: string, y: string): boolean {
    return this.find(x) === this.find(y);
  }
}

// Cycle detection in a directed graph (adjacency list)
function hasCycle(graph: Map<string, string[]>): boolean {
  const visited = new Set<string>();
  const inStack = new Set<string>();

  function dfs(node: string): boolean {
    if (inStack.has(node)) return true;
    if (visited.has(node)) return false;
    visited.add(node);
    inStack.add(node);
    for (const neighbor of graph.get(node) ?? []) {
      if (dfs(neighbor)) return true;
    }
    inStack.delete(node);
    return false;
  }

  for (const node of graph.keys()) {
    if (dfs(node)) return true;
  }
  return false;
}

// ═══════════════════════════════════════════════════════════════
// 6. HTTP CLIENT PATTERNS — fetch (Node 18+, zero deps)
// ═══════════════════════════════════════════════════════════════

// GET with error handling
async function httpGet<T>(url: string, headers: Record<string, string> = {}): Promise<T> {
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`GET ${url} → ${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

// POST with JSON body
async function httpPost<T>(
  url: string,
  body: Record<string, unknown>,
  headers: Record<string, string> = {},
): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`POST ${url} → ${res.status}: ${errBody}`);
  }
  return res.json() as Promise<T>;
}

// Paginate through a cursor-based API (Stripe-style)
async function paginateAll<T>(
  fetchPage: (startingAfter?: string) => Promise<{ data: T[]; has_more: boolean }>,
  getId: (item: T) => string,
): Promise<T[]> {
  const all: T[] = [];
  let cursor: string | undefined;
  while (true) {
    const page = await fetchPage(cursor);
    all.push(...page.data);
    if (!page.has_more || page.data.length === 0) break;
    cursor = getId(page.data[page.data.length - 1]);
  }
  return all;
}

// ═══════════════════════════════════════════════════════════════
// 7. STATE MACHINE — status transitions with validation
// ═══════════════════════════════════════════════════════════════

type Transitions<S extends string> = Partial<Record<S, S[]>>;

class StateMachine<S extends string> {
  constructor(
    private current: S,
    private transitions: Transitions<S>,
  ) {}

  get state(): S { return this.current; }

  transition(to: S): boolean {
    const allowed = this.transitions[this.current];
    if (!allowed || !allowed.includes(to)) return false;
    this.current = to;
    return true;
  }

  canTransition(to: S): boolean {
    return this.transitions[this.current]?.includes(to) ?? false;
  }
}

// ═══════════════════════════════════════════════════════════════
// 8. SNAPSHOT / UNDO — clone state for history
// ═══════════════════════════════════════════════════════════════

// Deep clone for Maps (one level — Map<string, primitive>)
function cloneMap<K, V>(m: Map<K, V>): Map<K, V> { return new Map(m); }

// Undo stack pattern
class UndoStack<T> {
  private stack: T[] = [];
  save(snapshot: T): void { this.stack.push(snapshot); }
  undo(): T | undefined { return this.stack.pop(); }
  canUndo(): boolean { return this.stack.length > 0; }
}

// ═══════════════════════════════════════════════════════════════
// 9. COMMON PATTERNS IN ONE-LINERS
// ═══════════════════════════════════════════════════════════════

// Array → Map of first occurrence index
const firstIndex = <T>(arr: T[], key: (x: T) => string) =>
  arr.reduce((m, x, i) => m.has(key(x)) ? m : m.set(key(x), i), new Map<string, number>());

// Sum an array
const sum = (arr: number[]) => arr.reduce((a, b) => a + b, 0);

// Chunk an array
const chunk = <T>(arr: T[], size: number): T[][] =>
  Array.from({ length: Math.ceil(arr.length / size) }, (_, i) => arr.slice(i * size, i * size + size));

// Flatten one level
const flatten = <T>(arr: T[][]): T[] => ([] as T[]).concat(...arr);

// Clamp
const clamp = (n: number, min: number, max: number) => Math.min(Math.max(n, min), max);

// Deep equal (for tests — JSON round-trip)
const deepEq = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

// ═══════════════════════════════════════════════════════════════
// 10. TESTING PATTERNS — quick assertion helpers
// ═══════════════════════════════════════════════════════════════

function assert(condition: boolean, msg: string): void {
  if (!condition) throw new Error(`ASSERT FAILED: ${msg}`);
}

function assertEqual<T>(actual: T, expected: T, label: string): void {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a !== e) throw new Error(`${label}: expected ${e}, got ${a}`);
}

// ═══════════════════════════════════════════════════════════════
// SELF-CHECK — verify everything above works
// ═══════════════════════════════════════════════════════════════

function main(): void {
  let passed = 0, failed = 0;
  function check(label: string, actual: unknown, expected: unknown): void {
    const a = JSON.stringify(actual), e = JSON.stringify(expected);
    if (Object.is(actual, expected) || a === e) { passed++; console.log(`  ✓ ${label}`); }
    else { failed++; console.log(`  ✗ ${label}\n    expected: ${e}\n         got: ${a}`); }
  }

  console.log("\nToolbox Self-Check\n");

  console.log("countBy / groupBy / dedupBy / indexBy");
  const items = [
    { name: "alice", dept: "eng" },
    { name: "bob", dept: "eng" },
    { name: "carol", dept: "sales" },
    { name: "alice", dept: "eng" },
  ];
  check("countBy", Object.fromEntries(countBy(items, x => x.dept)), { eng: 3, sales: 1 });
  check("groupBy keys", [...groupBy(items, x => x.dept).keys()].sort(), ["eng", "sales"]);
  check("dedupBy", dedupBy(items, x => x.name).length, 3);
  check("indexBy", indexBy(items, x => x.name).get("bob")?.dept, "eng");

  console.log("multiSort");
  const scores = [
    { name: "bob", score: 90 },
    { name: "alice", score: 90 },
    { name: "carol", score: 100 },
  ];
  const sorted = [...scores].sort(multiSort(x => -x.score, x => x.name));
  check("multi-key sort", sorted.map(x => x.name), ["carol", "alice", "bob"]);

  console.log("parseCSV / parseKV");
  const csv = "name,age\nalice,30\nbob,25";
  check("csv rows", parseCSV(csv).rows.length, 2);
  check("csv value", parseCSV(csv).rows[0].name, "alice");
  const kv = "host=localhost\nport=3000\n# comment\n";
  check("kv", parseKV(kv).get("port"), "3000");
  check("kv comment skipped", parseKV(kv).size, 2);

  console.log("SlidingWindowRateLimiter");
  const rl = new SlidingWindowRateLimiter(3, 1000);
  check("rl allow 1", rl.allow("u1", 100), true);
  check("rl allow 2", rl.allow("u1", 200), true);
  check("rl allow 3", rl.allow("u1", 300), true);
  check("rl deny 4", rl.allow("u1", 400), false);
  check("rl window expired", rl.allow("u1", 1200), true);

  console.log("FixedWindowRateLimiter");
  const frl = new FixedWindowRateLimiter(2, 1000);
  check("frl allow 1", frl.allow("u1", 0), true);
  check("frl allow 2", frl.allow("u1", 500), true);
  check("frl deny 3", frl.allow("u1", 900), false);
  check("frl new window", frl.allow("u1", 1000), true);

  console.log("UnionFind");
  const uf = new UnionFind();
  uf.union("a", "b");
  uf.union("b", "c");
  check("uf connected", uf.connected("a", "c"), true);
  check("uf not connected", uf.connected("a", "d"), false);

  console.log("hasCycle");
  const acyclic = new Map([["a", ["b"]], ["b", ["c"]], ["c", []]]);
  const cyclic = new Map([["a", ["b"]], ["b", ["c"]], ["c", ["a"]]]);
  check("no cycle", hasCycle(acyclic), false);
  check("has cycle", hasCycle(cyclic), true);

  console.log("StateMachine");
  type PayStatus = "pending" | "processing" | "completed" | "failed";
  const sm = new StateMachine<PayStatus>("pending", {
    pending: ["processing", "failed"],
    processing: ["completed", "failed"],
  });
  check("sm initial", sm.state, "pending");
  check("sm valid transition", sm.transition("processing"), true);
  check("sm after transition", sm.state, "processing");
  check("sm invalid transition", sm.transition("pending"), false);

  console.log("UndoStack");
  const us = new UndoStack<Map<string, number>>();
  const state = new Map([["x", 1]]);
  us.save(cloneMap(state));
  state.set("x", 2);
  check("undo can", us.canUndo(), true);
  const prev = us.undo()!;
  check("undo restores", prev.get("x"), 1);
  check("undo empty", us.canUndo(), false);

  console.log("one-liners");
  check("sum", sum([1, 2, 3, 4]), 10);
  check("chunk", chunk([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]]);
  check("clamp low", clamp(-5, 0, 100), 0);
  check("clamp high", clamp(150, 0, 100), 100);
  check("deepEq", deepEq({ a: 1 }, { a: 1 }), true);

  const total = passed + failed;
  console.log(`\n${passed}/${total} passed`);
  if (failed === 0 && total > 0) console.log("All checks passed.");
}

main();
