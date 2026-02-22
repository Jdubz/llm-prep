# Module 06 Cheat Sheet: Coding Interview Patterns

> Quick-reference for pattern recognition and templates. Glance at this before your interview.

---

## Pattern Recognition Table

| Problem Characteristics | Pattern | Time Complexity |
|------------------------|---------|-----------------|
| Contiguous subarray/substring, "longest/shortest that..." | **Sliding Window** | O(n) |
| Sorted array, find pair/triplet | **Two Pointers** | O(n) or O(n^2) |
| Linked list cycle, middle, nth from end | **Fast/Slow Pointers** | O(n) |
| Tree/graph traversal, shortest path (unweighted) | **BFS** | O(V + E) |
| Tree/graph traversal, explore all paths | **DFS** | O(V + E) |
| Optimal min/max/count, overlapping subproblems | **Dynamic Programming** | Varies |
| Shortest path (weighted graph) | **Dijkstra** | O((V+E) log V) |
| Task ordering, dependencies | **Topological Sort** | O(V + E) |
| "Are these connected?" dynamic groups | **Union-Find** | ~O(1) amortized |
| Find K largest/smallest, merge K sorted | **Heap** | O(n log k) |
| Generate all permutations/combinations | **Backtracking** | O(2^n) or O(n!) |
| Sorted data, find boundary, search space | **Binary Search** | O(log n) |
| "Next greater/smaller element" | **Monotonic Stack** | O(n) |
| Merge/overlap intervals | **Sort + Sweep** | O(n log n) |
| Find single/unique element, bit state | **Bit Manipulation** | O(n) |
| Fast key lookup, complement, frequency | **Hash Map** | O(n) |

---

## Template Pseudocode

### Sliding Window (Variable)

```
left = 0
for right in range(n):
    add arr[right] to state
    while state is invalid:
        remove arr[left] from state
        left += 1
    update answer
```

### Two Pointers (Sorted Array)

```
left, right = 0, n - 1
while left < right:
    sum = arr[left] + arr[right]
    if sum == target: return result
    elif sum < target: left += 1
    else: right -= 1
```

### BFS (Level-Order)

```
queue = [start], visited = {start}
while queue:
    level_size = len(queue)
    for i in range(level_size):
        node = queue.dequeue()
        for neighbor in adj(node):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.enqueue(neighbor)
```

### DFS (Recursive)

```
def dfs(node, visited):
    visited.add(node)
    for neighbor in adj(node):
        if neighbor not in visited:
            dfs(neighbor, visited)
```

### Dynamic Programming

```
// 1. Define state: dp[i] = ...
// 2. Base case: dp[0] = ...
// 3. Transition: dp[i] = f(dp[i-1], dp[i-2], ...)
// 4. Answer: dp[n] or max(dp)
for i in range(1, n+1):
    dp[i] = transition(dp[i-1], ...)
```

### Binary Search (Find Boundary)

```
left, right = lo, hi
while left < right:
    mid = (left + right) // 2
    if condition(mid):
        right = mid
    else:
        left = mid + 1
return left
```

### Backtracking

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

### Union-Find

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

### Dijkstra

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

### Monotonic Stack (Next Greater)

```
stack = []
for i in range(n):
    while stack and arr[i] > arr[stack[-1]]:
        result[stack.pop()] = arr[i]
    stack.append(i)
```

---

## Big-O for Common Operations

| Data Structure | Access | Search | Insert | Delete |
|---------------|--------|--------|--------|--------|
| Array | O(1) | O(n) | O(n) | O(n) |
| Linked List | O(n) | O(n) | O(1)* | O(1)* |
| Hash Map | - | O(1) avg | O(1) avg | O(1) avg |
| BST (balanced) | - | O(log n) | O(log n) | O(log n) |
| Heap | - | O(n) | O(log n) | O(log n) |
| Stack/Queue | O(1)** | O(n) | O(1) | O(1) |

*With reference to the node. **Top/front only.

---

## Time Management Timeline (35-Minute Problem)

```
[0:00 - 5:00]  UNDERSTAND
                - Restate the problem
                - Clarify: input types, sizes, constraints
                - Ask: edge cases? empty input? duplicates?
                - Write 2-3 examples

[5:00 - 10:00] PLAN
                - Identify pattern
                - Discuss brute force first
                - Propose optimized approach
                - State time/space complexity
                - Get interviewer confirmation

[10:00 - 30:00] CODE
                - Write clean, readable code
                - Use descriptive variable names
                - Talk while coding
                - Do not chase premature optimization

[30:00 - 35:00] TEST
                - Trace through with a simple example
                - Test edge cases (empty, single element, duplicates)
                - Fix bugs calmly — no panicking
                - Discuss potential improvements
```

---

## Edge Cases Checklist

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

## Common DP Categories Quick Reference

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
