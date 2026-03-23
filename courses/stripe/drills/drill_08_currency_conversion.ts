/*
Drill 08 — Currency Conversion

Build a currency converter that supports graph traversal for
multi-hop conversions. This is a well-known Stripe interview
classic that tests graph modeling and traversal algorithms.

Target time: 30 minutes for all 4 levels.

────────────────────────────────────────
Level 1 — Direct Conversion (5 min)


────────────────────────────────────────
Level 2 — Multi-Hop Conversion via DFS (15 min)

────────────────────────────────────────
Level 3 — Shortest Path via BFS (10 min)

convertBFS(from: string, to: string, amount: number):
{ path: string[]; rate: number; amount: number } | null

Find the path with fewest intermediate conversions using BFS.
Track parent pointers and accumulate rates along the path.
Return the shortest path result (same shape as Level 2).

────────────────────────────────────────
Level 4 — Best Rate Path (10 min)

convertBestRate(from: string, to: string, amount: number):
{ path: string[]; rate: number; amount: number } | null

Find the path that gives the best (highest) conversion rate.
Explore all paths (modified DFS) to find the optimal one.
Return the best-rate result (same shape as Level 2).
*/

export class CurrencyConverter {
  rateMap: Map<string, Map<string, number>>;
  constructor(ratesStr: string) {
    this.rateMap = new Map();
    const conversions = ratesStr.split(',');
    conversions.forEach(c => {
      const [from, to, rate] = c.split(':');
      
      this.createOrSet(from, to, +rate);
      this.createOrSet(to, from, 1/+rate);
    });
  }
  
  private createOrSet(from: string, to: string, rate: number) {
    let fromMap = this.rateMap.get(from);
    if (!fromMap) {
      fromMap = new Map();
      this.rateMap.set(from, fromMap);
    }
    fromMap.set(to, rate);
  }
  // REVIEW: Constructor and createOrSet are clean. Good extraction
  // of the bidirectional insert logic. This is the kind of helper
  // that saves you time later — you wrote it once and called it
  // twice. Good instinct.

  // Level 1
  // constructor(ratesStr: string)
  //   Parse exchange rates from a string like
  //   "USD:EUR:0.85,USD:JPY:110,EUR:GBP:0.88".
  //   Build a bidirectional rate map: if USD→EUR = 0.85,
  //   then EUR→USD = 1/0.85.
  
  // convert(from: string, to: string, amount: number): number
  //   Return the converted amount using a direct rate.
  //   If from === to, return amount unchanged.
  //   Return -1 if no direct rate exists.
  convert(from: string, to: string, amount: number): number {
    if (from === to) return amount;
    const fromMap = this.rateMap.get(from);
    const rate = fromMap?.get(to);
    if (!rate) return -1;
    return amount * rate;
  }
  // REVIEW: Clean. One edge case: if a valid rate is exactly 0,
  // `if (!rate)` would return -1. Use `if (rate === undefined)`
  // instead. Same bug pattern as drill_07's `!product.unitPrice`.

  getDirectRate(from: string, to: string): number | undefined {
    if (from === to) return;
    const fromMap = this.rateMap.get(from);
    return fromMap?.get(to);
  }
  // REVIEW: This helper is only used by convertDFS and convertBestRate
  // for the "peek ahead" optimization. It adds a second way to find
  // rates (alongside iterating rateMap entries), which means two code
  // paths that can diverge. In convertDFS and convertBestRate, you use
  // BOTH: the loop gives you childRate, AND you call getDirectRate for
  // the next hop. This caused your original rate bug (double-counting).
  //
  // Simpler: drop getDirectRate entirely. Let the recursion handle
  // discovery naturally — when `child === to`, you've found it. No
  // peeking needed. Fewer code paths = fewer bugs.

/* convertDFS(from: string, to: string, amount: number):
{ path: string[]; rate: number; amount: number } | null

Find any valid conversion path using depth-first search.
Track visited nodes to avoid cycles.
Multiply rates along the path.
Return { path, rate, amount } or null if no path exists.
Example: USD→EUR→GBP, rate = 0.85 * 0.88 = 0.748,
amount = 100 * 0.748 = 74.8 */
  // Level 2
  convertDFS(from: string, to: string, amount: number): { path: string[]; rate: number; amount: number } | null {

    const dfs = (parent: string, path: string[], rate: number, visited: Set<string>): { path: string[], rate: number } | undefined => {
      if (parent === to) return { path, rate };
      const fromMap = this.rateMap.get(parent)!;
      for (const [child, childRate] of fromMap.entries()) {
        const newRate = rate * childRate;
        const dirRate = this.getDirectRate(child, to);
        const newPath = [...path, child];
        if (dirRate) return { path: [...newPath, to], rate: newRate * dirRate };
        if (!visited.has(child)) {
          visited.add(child);
          const childResult = dfs(child, newPath, newRate * childRate, new Set(visited));
          if (childResult) return childResult;
        }
      }
    }

    const result = dfs(from, [from], 1, new Set());
    if (!result) return null;
    return { ...result, amount: amount * result.rate };

  }
  // REVIEW: Works but has two issues that would bite you in a
  // larger graph:
  //
  // 1. Line 107: `newRate * childRate` double-multiplies. You
  //    already computed `newRate = rate * childRate` on line 101,
  //    then pass `newRate * childRate` to the recursive call. That's
  //    `rate * childRate * childRate`. It works here only because
  //    the peek-ahead on line 104 returns before the recursive call
  //    reaches the destination. If the graph had a longer path that
  //    didn't hit the peek-ahead, the rate would be wrong.
  //
  // 2. `new Set(visited)` on line 107 copies the entire Set on every
  //    recursive call. This is O(n) per call. For backtracking DFS,
  //    mutate + delete is standard:
  //      visited.add(child);
  //      const result = dfs(child, newPath, newRate, visited);
  //      if (result) return result;
  //      visited.delete(child);  // backtrack
  //
  // 3. The base case `if (parent === to)` on line 98 is correct but
  //    it's never reached because the peek-ahead always catches the
  //    destination one hop early. Dead code under the current logic.
  //    If you removed getDirectRate and let recursion handle it,
  //    the base case would actually fire and the function would be
  //    simpler.

  // Level 3
  
/* convertBFS(from: string, to: string, amount: number):
{ path: string[]; rate: number; amount: number } | null

Find the path with fewest intermediate conversions using BFS.
Track parent pointers and accumulate rates along the path.
Return the shortest path result (same shape as Level 2). */

  convertBFS(from: string, to: string, amount: number): { path: string[]; rate: number; amount: number } | null {
    
    const visited = new Set();
    const queue: [string, string[], number][] = [[from, [from], 1]];

    while (queue.length) {
      const [node, path, rate] = queue.shift()!;
      const nodeRates = this.rateMap.get(node)!;
      for (const [next, r] of nodeRates.entries()) {
        if (visited.has(next)) continue;
        const newRate = rate * r;
        const newPath = [...path, next];
        if (next === to) return { path: newPath, rate: newRate, amount: amount * newRate };
        visited.add(next);
        queue.push([next, newPath, newRate]);
      }
    }
    return null;

  }
  // REVIEW: Excellent. This is the cleanest function in the file.
  // Correct BFS pattern: visited on enqueue, tuple queue with
  // [node, path, rate], early return when destination found.
  //
  // One minor issue: `this.rateMap.get(node)!` on line 135 will
  // throw if a node has no outgoing edges (not in rateMap). Use
  // `this.rateMap.get(node) || new Map()` or `?.entries() ?? []`.
  // Won't happen with the current test data, but an interviewer
  // might ask "what if a currency has no outgoing rates?"
  //
  // Also: `visited` doesn't include `from`. If there's a cycle
  // back to `from`, it could be re-enqueued. Add `visited.add(from)`
  // before the loop. Not a correctness issue here (from === to is
  // checked by the test separately), but good practice.

  // Level 4
/*   convertBestRate(from: string, to: string, amount: number):
{ path: string[]; rate: number; amount: number } | null

Find the path that gives the best (highest) conversion rate.
Explore all paths (modified DFS) to find the optimal one.
Return the best-rate result (same shape as Level 2). */
  convertBestRate(from: string, to: string, amount: number): { path: string[]; rate: number; amount: number } | null {
    const allRates: {path: string[], rate: number}[] = [];
    
    const dfs = (parent: string, path: string[], rate: number, visited: Set<string>): void => {
      if (parent === to) allRates.push({ path, rate });
      const fromMap = this.rateMap.get(parent)!;
      for (const [child, childRate] of fromMap.entries()) {
        const newRate = rate * childRate;
        const dirRate = this.getDirectRate(child, to);
        const newPath = [...path, child];
        if (dirRate) allRates.push({ path: [...newPath, to], rate: newRate * dirRate });
        if (!visited.has(child)) {
          visited.add(child);
          dfs(child, newPath, newRate * childRate, new Set(visited));
        }
      }
    }

    dfs(from, [from], 1, new Set());

    if (!allRates.length) return null;
    allRates.sort((a,b) => b.rate - a.rate);
    const { path, rate } = allRates[0];
    return { path, rate, amount: amount * rate };
  }
  // REVIEW: Works but has the same two bugs as convertDFS that
  // happen to cancel out in the test data:
  //
  // 1. Line 169: `newRate * childRate` double-multiplies (same as DFS).
  //
  // 2. Line 166: peek-ahead with getDirectRate uses `newRate * dirRate`
  //    which is correct, but the recursive path on line 169 uses
  //    `newRate * childRate` which is `rate * childRate * childRate`.
  //    These two paths produce different rates for the same edge.
  //
  // 3. `new Set(visited)` copies on every call — same O(n) issue.
  //    For best-rate you DO need to explore all paths, so you need
  //    backtracking. But copy-on-call is expensive. Use add/delete:
  //      visited.add(child);
  //      dfs(child, newPath, newRate, visited);
  //      visited.delete(child);
  //
  // 4. Collecting all paths then sorting is correct but wasteful.
  //    You can track a running best instead:
  //      if (parent === to) { if (rate > bestRate) { best = ...; } return; }
  //    Avoids the array + sort overhead. Minor for small graphs but
  //    shows the interviewer you're thinking about efficiency.
  //
  // Overall: the approach (explore all paths, pick best) is right.
  // The implementation would break on a graph where the peek-ahead
  // doesn't fire. Drop getDirectRate, let recursion handle it, and
  // all three traversal functions become simpler and consistent.
}

// ─── Self-Checks (do not edit below this line) ──────────────────

let _passed = 0;
let _failed = 0;

function check(label: string, actual: unknown, expected: unknown): void {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (Object.is(actual, expected) || a === e) {
    _passed++;
    console.log(`  ✓ ${label}`);
  } else {
    _failed++;
    console.log(`  ✗ ${label}`);
    console.log(`    expected: ${e}`);
    console.log(`         got: ${a}`);
  }
}

function level(name: string, fn: () => void): void {
  console.log(name);
  try {
    fn();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("TODO:")) {
      console.log(`  ○ ${msg}`);
    } else {
      _failed++;
      console.log(`  ✗ ${msg}`);
    }
  }
}

function runSelfChecks(): void {
  const RATES = "USD:EUR:0.85,USD:JPY:110,EUR:GBP:0.88,GBP:CHF:1.18";

  level("Level 1 — Direct Conversion", () => {
    const cc = new CurrencyConverter(RATES);
    check("same currency", cc.convert("USD", "USD", 100), 100);
    check("USD to EUR", cc.convert("USD", "EUR", 100), 85);
    check("EUR to USD (reverse)", cc.convert("EUR", "USD", 85), 100);
    check("no direct rate", cc.convert("USD", "GBP", 100), -1);
  });

  level("Level 2 — Multi-Hop DFS", () => {
    const cc = new CurrencyConverter(RATES);
    const result = cc.convertDFS("USD", "GBP", 100);
    check("DFS path exists", result !== null, true);
    check("DFS path is USD→EUR→GBP", result!.path, ["USD", "EUR", "GBP"]);
    check("DFS rate", result!.rate, 0.85 * 0.88);
    check("DFS amount", result!.amount, 100 * 0.85 * 0.88);
    const same = cc.convertDFS("USD", "USD", 50);
    check("DFS same currency", same, { path: ["USD"], rate: 1, amount: 50 });
    const none = cc.convertDFS("USD", "XYZ", 100);
    check("DFS no path", none, null);
  });

  level("Level 3 — Shortest Path BFS", () => {
    // Two paths exist from USD to CHF:
    //   Short: USD→EUR→CHF (2 hops) via direct EUR:CHF rate
    //   Long:  USD→EUR→GBP→CHF (3 hops)
    // BFS should find the shorter one.
    const rates = RATES + ",EUR:CHF:1.08";
    const cc = new CurrencyConverter(rates);
    const result = cc.convertBFS("USD", "CHF", 100);
    check("BFS path exists", result !== null, true);
    check("BFS shortest path", result!.path, ["USD", "EUR", "CHF"]);
    const expectedRate = 0.85 * 1.08;
    check("BFS rate", result!.rate, expectedRate);
    check("BFS amount", result!.amount, 100 * expectedRate);
    check("BFS no path", cc.convertBFS("USD", "XYZ", 100), null);
  });

  level("Level 4 — Best Rate Path", () => {
    // Two paths from USD to GBP:
    //   Direct: USD→GBP = 0.72
    //   Via EUR: USD→EUR→GBP = 0.85 * 0.88 = 0.748
    // Best rate is via EUR (0.748 > 0.72)
    const rates = "USD:EUR:0.85,USD:GBP:0.72,EUR:GBP:0.88";
    const cc = new CurrencyConverter(rates);
    const result = cc.convertBestRate("USD", "GBP", 100);
    check("best rate path exists", result !== null, true);
    check("best rate picks higher", result!.path, ["USD", "EUR", "GBP"]);
    check("best rate", result!.rate, 0.85 * 0.88);
    check("best rate amount", result!.amount, 100 * 0.85 * 0.88);
    check("best rate no path", cc.convertBestRate("USD", "XYZ", 100), null);
  });
}

function main(): void {
  console.log("\nCurrency Conversion\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
