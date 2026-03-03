# Pattern Optimization and Edge Cases

> Advanced coding patterns, dynamic programming depth, backtracking, graph algorithms, and edge case handling. These topics distinguish strong candidates in senior and staff-level interviews. Know when to reach for them.

---

## Dynamic Programming

### When to Recognize It

- "Find the **optimal** (min/max/count) way to do X"
- Problem has **overlapping subproblems** (same sub-computation repeated)
- Problem has **optimal substructure** (optimal solution built from optimal sub-solutions)
- Brute force would be exponential

### Identifying Subproblems

Ask yourself: "If I knew the answer for a smaller version of this problem, could I build the answer for the full problem?"

**Framework:**
1. Define the **state** — what variables describe a subproblem? (e.g., `dp[i]` = answer for first i elements)
2. Define the **transition** — how does the current state relate to previous states?
3. Define the **base case** — what is the answer for the smallest subproblem?
4. Define the **answer** — which state contains the final answer?

Template pseudocode:
```
// 1. Define state: dp[i] = ...
// 2. Base case: dp[0] = ...
// 3. Transition: dp[i] = f(dp[i-1], dp[i-2], ...)
// 4. Answer: dp[n] or max(dp)
for i in range(1, n+1):
    dp[i] = transition(dp[i-1], ...)
```

### Top-Down vs Bottom-Up

| Approach | Implementation | Pros | Cons |
|----------|---------------|------|------|
| **Top-Down (Memoization)** | Recursive + cache | Intuitive, only computes needed states | Stack overflow risk, function call overhead |
| **Bottom-Up (Tabulation)** | Iterative, fill table | No stack overflow, often faster | Must determine fill order, computes all states |

**Interview advice:** Start with top-down (easier to reason about), then convert to bottom-up if asked for optimization.

### 1D DP

State depends on a single dimension: `dp[i]`.

**Example — Climbing Stairs:** `dp[i] = dp[i-1] + dp[i-2]`. Ways to reach step i = ways to reach step i-1 (take 1 step) + ways to reach step i-2 (take 2 steps).

**Example — House Robber:** `dp[i] = max(dp[i-1], dp[i-2] + nums[i])`. Either skip this house or rob it (plus the max from two houses ago).

### 2D DP

State depends on two dimensions: `dp[i][j]`.

**Example — Longest Common Subsequence:**
```
dp[i][j] = length of LCS of s1[0..i] and s2[0..j]
if s1[i] == s2[j]: dp[i][j] = dp[i-1][j-1] + 1
else: dp[i][j] = max(dp[i-1][j], dp[i][j-1])
```

**Example — Edit Distance:**
```
dp[i][j] = min edits to convert s1[0..i] to s2[0..j]
if s1[i] == s2[j]: dp[i][j] = dp[i-1][j-1]
else: dp[i][j] = 1 + min(dp[i-1][j-1], dp[i-1][j], dp[i][j-1])
                     (replace)        (delete)    (insert)
```

### Common DP Categories

| Category | Pattern | Examples |
|----------|---------|----------|
| **0/1 Knapsack** | Include or exclude each item | Subset sum, partition equal subset |
| **Unbounded Knapsack** | Include items unlimited times | Coin change, rod cutting |
| **LCS/LIS** | Subsequence comparison | Edit distance, longest increasing subsequence |
| **Matrix Chain** | Optimal split point | Burst balloons, matrix multiplication |
| **Interval** | Process subarrays/substrings | Palindrome problems, stone game |
| **State Machine** | Transitions between states | Stock buy/sell with cooldown, regex matching |

### DP Categories Quick Reference

| Category | State | Transition Idea |
|----------|-------|-----------------|
| Fibonacci-type | `dp[i]` | `dp[i] = dp[i-1] + dp[i-2]` |
| 0/1 Knapsack | `dp[i][w]` | Include item i or skip it |
| Unbounded Knapsack | `dp[w]` | Can reuse items |
| LCS | `dp[i][j]` | Match or skip from either string |
| LIS | `dp[i]` | Longest ending at i |
| Coin Change | `dp[amount]` | Try each coin denomination |
| Grid Paths | `dp[r][c]` | Come from top or left |
| Palindrome | `dp[i][j]` | Expand from center or check endpoints |
| State Machine | `dp[i][state]` | Transition between defined states |

---

## Backtracking

### When to Recognize It

- "Generate all **permutations/combinations/subsets**"
- "Find all valid configurations" (N-Queens, Sudoku)
- "Explore all paths" with constraints

### Template

```
Template (pseudocode):
    def backtrack(state, choices):
        if is_solution(state):
            result.append(copy(state))
            return
        for choice in choices:
            if is_valid(choice, state):
                make_choice(state, choice)
                backtrack(state, remaining_choices)
                undo_choice(state, choice)  // backtrack
```

Cheat-sheet shorthand:
```
def backtrack(state, choices):
    if is_complete(state):
        result.append(copy(state))
        return
    for choice in choices:
        if is_valid(choice):
            state.add(choice)
            backtrack(state, next_choices)
            state.remove(choice)
```

**Example — Permutations:**
```
    def permute(nums, path, result):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for num in nums:
            if num not in path:
                path.append(num)
                permute(nums, path, result)
                path.pop()
```

**Example — Combinations (n choose k):**
```
    def combine(n, k, start, path, result):
        if len(path) == k:
            result.append(path[:])
            return
        for i in range(start, n + 1):
            path.append(i)
            combine(n, k, i + 1, path, result)
            path.pop()
```

**Pruning is critical:** The earlier you can reject a branch, the faster your backtracking runs. Check constraints before recursing, not after.

---

## Graph Algorithms

### Shortest Path

**BFS (unweighted):** O(V + E). Use when all edges have equal weight.

**Dijkstra (non-negative weights):** O((V + E) log V) with a min-heap.

```
Template (pseudocode):
    dist = {node: infinity for all nodes}
    dist[source] = 0
    heap = [(0, source)]
    while heap:
        d, u = heap.extract_min()
        if d > dist[u]: continue  // stale entry
        for (v, weight) in neighbors(u):
            if dist[u] + weight < dist[v]:
                dist[v] = dist[u] + weight
                heap.insert((dist[v], v))
```

Cheat-sheet shorthand:
```
dist[source] = 0, heap = [(0, source)]
while heap:
    d, u = heappop(heap)
    if d > dist[u]: continue
    for v, w in adj(u):
        if dist[u] + w < dist[v]:
            dist[v] = dist[u] + w
            heappush(heap, (dist[v], v))
```

**Bellman-Ford (negative weights):** O(VE). Relax all edges V-1 times. Can detect negative cycles.

### Topological Sort

**When:** Directed Acyclic Graph (DAG) — ordering tasks with dependencies.

**Kahn's Algorithm (BFS-based):**
1. Compute in-degree for each node
2. Enqueue all nodes with in-degree 0
3. Process queue: for each node, reduce in-degree of its neighbors
4. Enqueue neighbors that reach in-degree 0

If not all nodes are processed, the graph has a cycle.

**DFS-based:** Reverse post-order. After DFS completes for a node, add it to the front of the result.

### Union-Find (Disjoint Set Union)

**When:** "Are these two nodes in the same group?" Dynamic connectivity.

```
Template (pseudocode):
    parent = [i for i in range(n)]
    rank = [0] * n

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])  // path compression
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px == py: return
        if rank[px] < rank[py]: swap(px, py)
        parent[py] = px  // union by rank
        if rank[px] == rank[py]: rank[px] += 1
```

Cheat-sheet shorthand:
```
def find(x):
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]

def union(x, y):
    px, py = find(x), find(y)
    if rank[px] < rank[py]: swap
    parent[py] = px
```

Near O(1) amortized per operation with path compression + union by rank.

**Example — Number of Connected Components:** Union all edges, count distinct roots.

### Cycle Detection

- **Undirected graph:** DFS — if you visit a node already in the current path (visited but not the parent), cycle exists. Or use Union-Find.
- **Directed graph:** DFS with three states (unvisited, in-progress, completed). If you visit an in-progress node, cycle exists.

---

## Monotonic Stack / Queue

### When to Recognize It

- "Next greater/smaller element" for each position
- "Maximum/minimum in a sliding window"
- Problems involving comparing elements to their neighbors in a specific direction

### Monotonic Stack — Next Greater Element

Maintain a stack where elements are in increasing (or decreasing) order. When a new element breaks the monotonic property, pop elements and record answers.

```
Template — Next Greater Element (pseudocode):
    stack = []  // stores indices
    result = [-1] * n
    for i in range(n):
        while stack and arr[i] > arr[stack[-1]]:
            idx = stack.pop()
            result[idx] = arr[i]
        stack.append(i)
```

Cheat-sheet shorthand:
```
stack = []
for i in range(n):
    while stack and arr[i] > arr[stack[-1]]:
        result[stack.pop()] = arr[i]
    stack.append(i)
```

O(n) time — each element is pushed and popped at most once.

**Example — Daily Temperatures:** "For each day, how many days until a warmer temperature?" Use a monotonic decreasing stack. When you find a warmer day, pop all cooler days and compute the distance.

**Example — Largest Rectangle in Histogram:** For each bar, find the first shorter bar to the left and right (using monotonic stack). Width = right_boundary - left_boundary - 1. Area = height * width.

### Monotonic Deque — Sliding Window Maximum

Maintain a deque where the front is always the maximum in the current window.

```
Template (pseudocode):
    deque = []  // stores indices, front is max
    for i in range(n):
        // Remove elements outside the window
        while deque and deque[0] < i - k + 1:
            deque.popleft()
        // Remove elements smaller than current (they will never be the max)
        while deque and arr[deque[-1]] <= arr[i]:
            deque.pop()
        deque.append(i)
        if i >= k - 1:
            result.append(arr[deque[0]])
```

O(n) time, O(k) space.

---

## Interval Problems

### When to Recognize It

- Input is a list of intervals (start, end)
- Merging, inserting, finding overlaps, scheduling

### Key Insight: Sort by Start Time

Almost all interval problems begin with sorting by start time.

### Merge Intervals

```
Template (pseudocode):
    intervals.sort(by start)
    merged = [intervals[0]]
    for interval in intervals[1:]:
        if interval.start <= merged[-1].end:
            merged[-1].end = max(merged[-1].end, interval.end)
        else:
            merged.append(interval)
```

O(n log n) time (sorting dominates).

### Insert Interval

Three phases: add all intervals that end before the new one, merge all overlapping intervals, add remaining.

### Meeting Rooms II (Minimum Rooms)

"What is the maximum number of overlapping intervals at any point?"

**Approach 1 — Min-heap:** Sort by start time. For each meeting, if the earliest-ending meeting has ended (heap top < current start), pop it. Push the current meeting's end time. Heap size = rooms needed.

**Approach 2 — Event sweep:** Create events for each start (+1) and end (-1). Sort events. Sweep through, tracking running count. Maximum count = answer.

### Non-Overlapping Intervals

"Minimum intervals to remove so the rest do not overlap." Sort by end time. Greedily keep intervals that end earliest.

---

## Bit Manipulation Patterns

### When to Recognize It

- "Find the single element" (XOR)
- "Count bits," "power of 2"
- Space-constrained problems where each bit encodes a boolean

### Essential Operations

| Operation | Code | Purpose |
|-----------|------|---------|
| Check bit i | `(n >> i) & 1` | Is bit i set? |
| Set bit i | `n \| (1 << i)` | Turn on bit i |
| Clear bit i | `n & ~(1 << i)` | Turn off bit i |
| Toggle bit i | `n ^ (1 << i)` | Flip bit i |
| Clear lowest set bit | `n & (n - 1)` | Useful for counting set bits |
| Isolate lowest set bit | `n & (-n)` | Useful in BIT (Fenwick tree) |
| Check power of 2 | `n > 0 and n & (n-1) == 0` | Only one bit set |

### XOR Tricks

- `a ^ a = 0` (element cancels itself)
- `a ^ 0 = a` (identity)
- XOR is commutative and associative

**Example — Single Number:** XOR all elements. Pairs cancel, the single element remains. O(n) time, O(1) space.

**Example — Single Number III (two unique):** XOR all elements gives `a ^ b`. Find any set bit (it differs between a and b). Partition elements by that bit and XOR each group.

### Bitmask DP

Use an integer as a set representation. Bit i being set means element i is "selected."

```
Template (pseudocode):
    dp[mask] = answer for the subset represented by mask
    for mask in range(1 << n):
        for i in range(n):
            if mask & (1 << i):  // i is in the subset
                dp[mask] = transition from dp[mask ^ (1 << i)]
```

**Example — Travelling Salesman (small n):** `dp[mask][i]` = min cost to visit cities in mask, ending at city i.

---

## String Matching Algorithms

### KMP (Knuth-Morris-Pratt)

**Problem:** Find all occurrences of pattern P in text T.

**Key insight:** When a mismatch occurs, you have already matched some prefix. The failure function tells you how much to skip.

**Failure function (partial match table):**
- For each position i in the pattern, compute the length of the longest proper prefix that is also a suffix of pattern[0..i]

**Algorithm:**
1. Precompute the failure function in O(m) time
2. Scan the text: on mismatch, jump back in the pattern using the failure function instead of restarting

O(n + m) time, O(m) space. No backtracking in the text.

### Rabin-Karp

**Key insight:** Use a rolling hash to check if the current window matches the pattern's hash. Only do character-by-character comparison when hashes match.

**Rolling hash:**
```
hash(s[i+1..i+m]) = (hash(s[i..i+m-1]) - s[i] * base^(m-1)) * base + s[i+m]
```

O(n + m) expected time, O(nm) worst case (many hash collisions). Choose a large prime modulus to minimize collisions.

**When to prefer over KMP:** Multiple pattern search (compute hash for each pattern). Rabin-Karp extends naturally; KMP needs to be run per pattern (or use Aho-Corasick).

---

## Advanced Graph Algorithms

### Minimum Spanning Tree (MST)

**When:** "Connect all nodes with minimum total edge weight." Network design, clustering.

**Kruskal's Algorithm:**
1. Sort all edges by weight
2. For each edge (lightest first), add it if it does not create a cycle (use Union-Find)
3. Stop when you have V-1 edges

O(E log E) time. Best for sparse graphs.

**Prim's Algorithm:**
1. Start from any node, add it to the MST
2. Add the cheapest edge connecting MST to a non-MST node (use a min-heap)
3. Repeat until all nodes are in the MST

O(E log V) time with a binary heap. Best for dense graphs.

### Strongly Connected Components (SCCs)

**What:** In a directed graph, a maximal set of vertices where every vertex is reachable from every other vertex in the set.

**Tarjan's Algorithm:**
- Single DFS pass
- Track discovery time and lowest reachable discovery time for each node
- When a node's lowest reachable time equals its discovery time, it is the root of an SCC

**Kosaraju's Algorithm:**
1. DFS on the original graph, record finish order
2. Reverse the graph
3. DFS on the reversed graph in reverse finish order — each DFS tree is an SCC

Both O(V + E).

**Use cases:** Dependency analysis, compiler optimizations, 2-SAT.

### Network Flow (Overview)

**Problem:** Given a directed graph with capacities, find the maximum flow from source to sink.

**Ford-Fulkerson method:**
1. Find an augmenting path from source to sink (BFS = Edmonds-Karp)
2. Push flow along the path (min capacity = bottleneck)
3. Update residual capacities
4. Repeat until no augmenting path exists

**Max-Flow Min-Cut Theorem:** Maximum flow = minimum cut capacity. The cut is the minimum capacity set of edges whose removal disconnects source from sink.

**Interview context:** You rarely implement network flow from scratch. Know the concept, recognize when a problem reduces to max-flow (bipartite matching, edge-disjoint paths, min-cut problems).

---

## Math-Based Problems

### Modular Arithmetic

When dealing with large numbers, compute results modulo a large prime (typically 10^9 + 7).

**Key properties:**
```
(a + b) % m = ((a % m) + (b % m)) % m
(a * b) % m = ((a % m) * (b % m)) % m
(a - b) % m = ((a % m) - (b % m) + m) % m  // add m to handle negatives
```

**Modular exponentiation (fast power):**
```
def power(base, exp, mod):
    result = 1
    base = base % mod
    while exp > 0:
        if exp % 2 == 1:
            result = (result * base) % mod
        exp = exp >> 1
        base = (base * base) % mod
    return result
```

O(log exp) time.

### GCD (Greatest Common Divisor)

**Euclidean algorithm:**
```
def gcd(a, b):
    while b:
        a, b = b, a % b
    return a
```

O(log(min(a, b))) time. LCM(a, b) = a * b / GCD(a, b).

### Sieve of Eratosthenes

Find all primes up to n.

```
Template (pseudocode):
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, sqrt(n) + 1):
        if is_prime[i]:
            for j in range(i*i, n + 1, i):
                is_prime[j] = False
```

O(n log log n) time, O(n) space.

**Example — Count Primes:** Direct application of the sieve.

---

## System Design Coding

These are data structure design problems that bridge coding and system design interviews.

### LRU Cache

**Requirement:** O(1) get and put, evict least recently used when capacity is exceeded.

**Data structure:** Hash map + doubly linked list.
- Hash map: key -> linked list node (O(1) lookup)
- Doubly linked list: maintains access order (O(1) insert/remove)
- Most recently used at head, least recently used at tail

```
Template (pseudocode):
    class LRUCache:
        map: key -> node
        list: doubly linked list (head = MRU, tail = LRU)

        get(key):
            if key in map:
                move node to head
                return node.value
            return -1

        put(key, value):
            if key in map:
                update node.value
                move node to head
            else:
                if at capacity:
                    remove tail (LRU)
                    delete from map
                create node, add to head
                add to map
```

### Rate Limiter

**Sliding window counter approach:**
- Divide time into fixed windows
- Track count in current and previous window
- Estimate: `prev_count * overlap_percentage + current_count`

**Token bucket approach:**
- Bucket holds tokens (max = burst capacity)
- Tokens added at a fixed rate
- Each request consumes one token
- Request rejected if no tokens available

```
Template (pseudocode):
    class TokenBucket:
        tokens: float
        max_tokens: int
        refill_rate: float  // tokens per second
        last_refill: timestamp

        allow_request():
            refill()
            if tokens >= 1:
                tokens -= 1
                return True
            return False

        refill():
            now = current_time()
            tokens = min(max_tokens, tokens + (now - last_refill) * refill_rate)
            last_refill = now
```

### Consistent Hashing Implementation

```
Template (pseudocode):
    class ConsistentHash:
        ring: sorted map of hash -> node
        virtual_nodes: int  // per physical node

        add_node(node):
            for i in range(virtual_nodes):
                hash = hash_function(f"{node}:{i}")
                ring[hash] = node

        remove_node(node):
            for i in range(virtual_nodes):
                hash = hash_function(f"{node}:{i}")
                ring.remove(hash)

        get_node(key):
            hash = hash_function(key)
            // Find first ring entry >= hash (wrap around if needed)
            return ring.ceiling(hash) or ring.first()
```

---

## Edge Cases Checklist

Always test these before considering your solution complete.

**Arrays/Strings:**
- [ ] Empty input
- [ ] Single element
- [ ] All elements identical
- [ ] Already sorted / reverse sorted
- [ ] Negative numbers
- [ ] Integer overflow
- [ ] Very large input (n = 10^5+)

**Linked Lists:**
- [ ] Empty list (null head)
- [ ] Single node
- [ ] Cycle present
- [ ] Two nodes only

**Trees:**
- [ ] Empty tree (null root)
- [ ] Single node
- [ ] Left-skewed or right-skewed (degenerate)
- [ ] All same values

**Graphs:**
- [ ] Disconnected components
- [ ] Self-loops
- [ ] Parallel edges
- [ ] Single node, no edges

**Numbers:**
- [ ] Zero
- [ ] Negative values
- [ ] Integer min/max boundaries
- [ ] Floating-point precision

---

## Summary

Advanced patterns are rarely the first tool you should reach for. In an interview:

1. Start with a brute-force approach
2. Identify bottlenecks
3. Apply the simplest pattern that eliminates the bottleneck
4. Only reach for advanced patterns when the problem specifically demands them

The value of knowing these patterns is not using them every time — it is recognizing the rare problem where they are exactly the right tool and applying them confidently.

**Common DP, backtracking, and graph problems by difficulty progression:**
- 1D DP: Fibonacci, climbing stairs, house robber, coin change
- 2D DP: Unique paths, edit distance, LCS, knapsack
- Trees/Graphs: Number of islands, course schedule (topological sort), clone graph
- Advanced: Word break II (backtracking + DP), serialize/deserialize binary tree, alien dictionary
- System design coding: LRU cache, design Twitter, implement trie

---

## Practice

- For dynamic programming, practice the framework: define state, transition, base case, and answer for three problems (one 1D, one 2D, one from the categories table). Start with top-down memoization, then convert to bottom-up tabulation.
- Implement the LRU cache from the system design coding section from scratch without looking at the template. Time yourself. This is one of the most commonly asked coding questions and should be doable in 20 minutes with clean code.
- Run through the edge case checklist at the end of this guide against your last three coding interview solutions (or LeetCode submissions). How many edge cases did you miss? Make the checklist a habit before marking any solution as complete.
- For graph algorithms, practice recognizing which algorithm applies: given a one-sentence problem description, decide between BFS, Dijkstra, Bellman-Ford, topological sort, or Union-Find. Do this for 10 problems to build pattern recognition speed.

---

## Cross-References

- **[Module 06 — Core Coding Patterns](01-core-coding-patterns.md):** Read the core patterns guide first. This file builds on those foundational patterns with advanced techniques. The core patterns (sliding window, two pointers, BFS/DFS, binary search) cover the majority of interview questions; reach for the advanced patterns here only when the problem demands it.
- **[Module 05 — Common Technical Questions](../05-common-technical/):** The system design coding section here (LRU cache, rate limiter, consistent hashing) bridges Module 05's theoretical concepts with practical implementation. Module 05 explains WHY these data structures matter; this module shows HOW to implement them.
- **[Module 07 — Take-Home & Live Coding](../07-take-home-live-coding/):** The edge case checklist at the end of this file is directly applicable to take-home submissions. Module 07's testing strategy section recommends testing happy path, validation, edge cases, and error handling -- use this checklist to identify which edge cases to test. The [plant-watering project](../projects/plant-watering/) is a concrete take-home that exercises data structure selection and edge case handling.
- **[Module 03 — Technical Communication](../03-technical-communication/):** When discussing your approach to a DP problem or graph algorithm in an interview, use Module 03's trade-off voicing pattern: "Option A gives us X but costs Y. Option B gives us Z but costs W. I am choosing A because..."
