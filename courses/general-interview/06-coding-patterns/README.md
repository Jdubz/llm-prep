# Module 06: Coding Interview Patterns (Senior Refresher)

> Pattern recognition over grinding. If you can identify the pattern, you can solve the problem. This module is a refresher — not a course on algorithms from scratch.

---

## Table of Contents

1. [Time Management During Live Coding](#time-management-during-live-coding)
2. [Sliding Window](#sliding-window)
3. [Two Pointers](#two-pointers)
4. [BFS / DFS](#bfs--dfs)
5. [Dynamic Programming](#dynamic-programming)
6. [Graph Algorithms](#graph-algorithms)
7. [Tree Patterns](#tree-patterns)
8. [Hash Maps for O(1) Lookups](#hash-maps-for-o1-lookups)
9. [Heap / Priority Queue](#heap--priority-queue)
10. [Backtracking](#backtracking)
11. [Binary Search](#binary-search)

---

## Time Management During Live Coding

Before diving into patterns, internalize this timeline. It is the difference between finishing and flailing.

| Phase | Time | What to Do |
|-------|------|-----------|
| **Understand** | 0-5 min | Repeat the problem back. Clarify inputs, outputs, constraints. Ask about edge cases. |
| **Plan** | 5-10 min | Identify the pattern. Walk through approach verbally. Discuss complexity. Get interviewer buy-in. |
| **Code** | 10-30 min | Write clean code. Talk through what you are doing. Do not optimize prematurely. |
| **Test** | 30-35 min | Trace through with an example. Test edge cases. Fix bugs calmly. |

**Senior-level signals:**
- You ask clarifying questions before touching the keyboard
- You verbalize your thought process — the interviewer cannot evaluate what they cannot hear
- You discuss tradeoffs ("I could sort first for O(n log n), or use a hash map for O(n) with O(n) space")
- You recognize when you are stuck and pivot rather than spiraling

---

## Sliding Window

### When to Recognize It

- "Find the longest/shortest **substring/subarray** that satisfies a condition"
- Contiguous sequence of elements
- A brute-force approach would check all O(n^2) subarrays

### Fixed-Size Window

The window size is given. Slide it across the array, updating state as elements enter and leave.

```
Template (pseudocode):
    window_state = compute(arr[0..k])
    for i in range(k, n):
        add arr[i] to window_state
        remove arr[i-k] from window_state
        update answer
```

**Example — Maximum Sum Subarray of Size K:**
Maintain a running sum. Add the new element, subtract the element leaving the window. O(n) time, O(1) space.

### Variable-Size Window

Expand the right pointer to include elements; shrink the left pointer when the condition is violated.

```
Template (pseudocode):
    left = 0
    for right in range(n):
        add arr[right] to window_state
        while window_state violates condition:
            remove arr[left] from window_state
            left += 1
        update answer with (right - left + 1) or window_state
```

**Example — Longest Substring Without Repeating Characters:**
Use a hash set for the window. Expand right, adding characters. When a duplicate is found, shrink from left until the duplicate is removed. O(n) time, O(min(n, alphabet)) space.

**Example — Minimum Window Substring:**
Find the smallest window in S that contains all characters of T. Use a frequency map for T, track how many characters are satisfied. Expand right to satisfy, shrink left to minimize. O(n) time.

### String Problems with Sliding Window

- Anagram detection: fixed-size window matching a frequency map
- Longest substring with at most K distinct characters: variable window with a frequency map
- Permutation in string: fixed window of target length, compare frequency maps

---

## Two Pointers

### When to Recognize It

- **Sorted array** and you need to find pairs or triplets
- **Linked list** problems (find cycle, middle, nth from end)
- Reducing O(n^2) brute force to O(n)

### Sorted Array — Opposite Ends

Start one pointer at the beginning, one at the end. Move based on comparison with target.

```
Template (pseudocode):
    left, right = 0, n-1
    while left < right:
        current = arr[left] + arr[right]
        if current == target: found
        elif current < target: left += 1
        else: right -= 1
```

**Example — Two Sum (sorted):** O(n) time, O(1) space. Move left pointer right if sum is too small, right pointer left if too large.

**Example — Three Sum:** Sort the array. For each element, run two-pointer on the remainder. O(n^2) time. Skip duplicates to avoid duplicate triplets.

### Fast / Slow Pointers

Two pointers moving at different speeds through a linked list.

```
Template (pseudocode):
    slow = head
    fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast: cycle detected
```

**Example — Detect Cycle in Linked List:** Fast moves 2 steps, slow moves 1. If they meet, there is a cycle (Floyd's algorithm).

**Example — Find Middle of Linked List:** When fast reaches the end, slow is at the middle.

**Example — Linked List Cycle Start:** After detection, reset one pointer to head. Move both at speed 1. They meet at the cycle start.

### Same-Direction Pointers

Both pointers start at the beginning, one moves conditionally.

**Example — Remove Duplicates from Sorted Array:** Slow pointer marks the write position. Fast pointer scans ahead. When fast finds a new value, write it at slow and advance slow.

---

## BFS / DFS

### When to Recognize It

- **Tree traversal** (in-order, pre-order, post-order, level-order)
- **Graph exploration** (shortest path in unweighted graph, connectivity, cycle detection)
- **Matrix traversal** ("island" problems, flood fill, shortest path in grid)

### BFS — Breadth-First Search

Explores level by level. Uses a **queue**. Finds shortest path in unweighted graphs.

```
Template (pseudocode):
    queue = [start]
    visited = {start}
    while queue:
        node = queue.dequeue()
        process(node)
        for neighbor in adjacents(node):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.enqueue(neighbor)
```

**Level-order traversal (trees):** Process one level at a time by tracking queue size at each step.

```
    while queue:
        level_size = len(queue)
        for i in range(level_size):
            node = queue.dequeue()
            process(node)
            enqueue children
```

**Example — Shortest Path in Grid:** BFS from source, each cell is a node, neighbors are adjacent cells. First time you reach the target is the shortest path.

### DFS — Depth-First Search

Explores as deep as possible before backtracking. Uses a **stack** (or recursion).

```
Template — Recursive (pseudocode):
    def dfs(node, visited):
        visited.add(node)
        process(node)
        for neighbor in adjacents(node):
            if neighbor not in visited:
                dfs(neighbor, visited)

Template — Iterative (pseudocode):
    stack = [start]
    visited = {start}
    while stack:
        node = stack.pop()
        process(node)
        for neighbor in adjacents(node):
            if neighbor not in visited:
                visited.add(neighbor)
                stack.push(neighbor)
```

**Tree traversals:**
- **Pre-order:** Process node, then left, then right (serialize a tree)
- **In-order:** Left, process node, right (sorted order for BST)
- **Post-order:** Left, right, process node (delete tree, evaluate expressions)

### Matrix Traversal

Treat the grid as an implicit graph. Neighbors are 4-directional (or 8-directional).

```
    directions = [(0,1), (0,-1), (1,0), (-1,0)]
    for dr, dc in directions:
        nr, nc = row + dr, col + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] is valid:
            explore(nr, nc)
```

**Example — Number of Islands:** For each unvisited land cell, run DFS/BFS to mark all connected land. Count how many times you start a new exploration.

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

Near O(1) amortized per operation with path compression + union by rank.

**Example — Number of Connected Components:** Union all edges, count distinct roots.

### Cycle Detection

- **Undirected graph:** DFS — if you visit a node already in the current path (visited but not the parent), cycle exists. Or use Union-Find.
- **Directed graph:** DFS with three states (unvisited, in-progress, completed). If you visit an in-progress node, cycle exists.

---

## Tree Patterns

### Traversals

Covered above in BFS/DFS. Key insight: **in-order traversal of a BST yields sorted order.**

### BST Properties

- Left subtree values < node value < right subtree values (for all nodes)
- Search, insert, delete: O(h) where h is height
- Balanced BST: h = O(log n). Unbalanced: h = O(n).

**Validate BST:** Pass min/max bounds down the tree. Each node must be within (min, max). Update bounds: go left -> upper bound = node value. Go right -> lower bound = node value.

### Lowest Common Ancestor (LCA)

**Binary Tree (general):**
```
def lca(root, p, q):
    if root is None or root == p or root == q:
        return root
    left = lca(root.left, p, q)
    right = lca(root.right, p, q)
    if left and right: return root  // p and q on different sides
    return left if left else right
```

**BST:** If both p and q are less than root, go left. If both greater, go right. Otherwise, root is the LCA.

### Tree Construction

- **From in-order + pre-order:** Pre-order first element is root. Find root in in-order to split left/right subtrees. Recurse.
- **From in-order + post-order:** Post-order last element is root. Same splitting logic.
- **Serialization:** Pre-order with null markers. Or level-order with null markers.

### Common Tree Patterns

| Problem Type | Approach |
|-------------|----------|
| Max depth / height | Recursive: `1 + max(left_depth, right_depth)` |
| Path sum | Pass running sum down, check at leaves |
| Diameter | At each node: left_depth + right_depth. Track max. |
| Symmetric / mirror | Compare left subtree with right subtree recursively |
| Invert tree | Swap left and right children, recurse |
| Level averages | BFS level-order, compute average per level |

---

## Hash Maps for O(1) Lookups

### When to Recognize It

- "Find if there exists..." (membership check)
- "Find pairs that sum to..." (complement lookup)
- "Group elements by..." (categorization)
- "Count frequency of..." (frequency map)

### Two Sum Pattern

The classic pattern: for each element, check if its complement exists in the map.

```
Template (pseudocode):
    seen = {}
    for i, num in enumerate(arr):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
```

O(n) time, O(n) space. One pass.

### Frequency Counting

```
Template (pseudocode):
    freq = {}
    for item in collection:
        freq[item] = freq.get(item, 0) + 1
```

**Example — First Unique Character:** Build frequency map, then scan string again for first character with count 1.

**Example — Valid Anagram:** Compare frequency maps of both strings.

### Grouping

```
Template (pseudocode):
    groups = defaultdict(list)
    for item in collection:
        key = compute_key(item)
        groups[key].append(item)
```

**Example — Group Anagrams:** Key = sorted characters of each word. All anagrams sort to the same key.

---

## Heap / Priority Queue

### When to Recognize It

- "Find the **K largest/smallest** elements"
- "Merge **K sorted** lists/arrays"
- "Continuously find the **median** of a stream"

### Top-K Pattern

Use a **min-heap of size K** for K largest elements.

```
Template (pseudocode):
    heap = []  // min-heap
    for item in collection:
        heappush(heap, item)
        if len(heap) > k:
            heappop(heap)  // remove smallest
    return heap  // contains K largest
```

O(n log k) time, O(k) space. Better than sorting when k << n.

### Merge K Sorted Lists

Push the first element of each list into a min-heap. Pop the smallest, push the next element from that list.

```
Template (pseudocode):
    heap = [(list[i][0], i, 0) for i in range(k)]  // (value, list_index, element_index)
    heapify(heap)
    while heap:
        val, list_idx, elem_idx = heappop(heap)
        result.append(val)
        if elem_idx + 1 < len(lists[list_idx]):
            heappush(heap, (lists[list_idx][elem_idx + 1], list_idx, elem_idx + 1))
```

O(n log k) where n is total elements, k is number of lists.

### Sliding Window Median / Two-Heap Pattern

Maintain a max-heap (left half) and min-heap (right half). Balance them so they differ in size by at most 1.

- **Max-heap** stores the smaller half (top = median candidate)
- **Min-heap** stores the larger half (top = median candidate)
- Median = top of max-heap (odd count) or average of both tops (even count)

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

## Binary Search

### When to Recognize It

- Sorted array — find element or boundary
- "Search space reduction" — answer is in a range, you can check if a value works
- "Find the first/last element that satisfies a condition"

### Standard Binary Search

```
Template (pseudocode):
    left, right = 0, n - 1
    while left <= right:
        mid = left + (right - left) // 2
        if arr[mid] == target: return mid
        elif arr[mid] < target: left = mid + 1
        else: right = mid - 1
    return -1  // not found
```

### Find Boundary (First True)

Find the first index where a condition is true. This is the most versatile template.

```
Template (pseudocode):
    left, right = 0, n - 1
    result = -1
    while left <= right:
        mid = left + (right - left) // 2
        if condition(mid):
            result = mid
            right = mid - 1  // keep searching left
        else:
            left = mid + 1
```

**Example — First Bad Version:** Condition is `isBadVersion(mid)`. Find the first one.

**Example — Search in Rotated Sorted Array:** Determine which half is sorted, decide which half to search.

### Search Space Reduction

The search space is not an array — it is a range of possible answers.

**Example — Koko Eating Bananas:** Binary search on the eating speed. For each speed, check if Koko can finish in time.

```
    left, right = 1, max(piles)
    while left < right:
        mid = (left + right) // 2
        if can_finish(mid, piles, hours):
            right = mid
        else:
            left = mid + 1
    return left
```

---

## Summary: Pattern Recognition Decision Tree

When you see a new problem, ask these questions in order:

1. **Is the input sorted or can I sort it?** -> Binary search, two pointers
2. **Am I looking for a contiguous subarray/substring?** -> Sliding window
3. **Am I exploring all paths/configurations?** -> Backtracking, DFS
4. **Does the problem have optimal substructure + overlapping subproblems?** -> DP
5. **Am I working with a graph or tree structure?** -> BFS/DFS, graph algorithms
6. **Do I need fast lookups?** -> Hash map
7. **Do I need repeated min/max access?** -> Heap
8. **Am I looking for pairs or triplets in an array?** -> Two pointers (sorted) or hash map
9. **Can I reduce the search space by half each step?** -> Binary search

The pattern is your starting point, not your destination. Adapt the template to the specific problem.
