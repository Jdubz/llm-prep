# 03 – Algorithm Patterns

The key data structure and algorithm patterns that appear in Dropbox coding interviews. Focus on these patterns over memorizing individual problems.

---

## 1. Pattern Priority for Dropbox

Based on reported interview problems, prioritize these:

| Priority | Pattern | Why |
|----------|---------|-----|
| **High** | Hash maps / sets | Foundation for most problems (dedup, grouping, counting) |
| **High** | BFS / DFS | Web crawler, DOM search, graph problems |
| **High** | Sliding window | OA pattern, substring problems |
| **High** | Heaps / priority queues | Id Allocator, top-K problems |
| **Medium** | Dynamic programming | Sharpness value, optimization problems |
| **Medium** | Backtracking | OA pattern, combinatorial problems |
| **Medium** | Concurrency / threading | Web crawler multi-threaded, token bucket |
| **Medium** | Union-Find | Connected components, grouping |
| **Lower** | Tries | Phone number dictionary, autocomplete |
| **Lower** | Rolling hash | Find byte pattern (Rabin-Karp) |

---

## 2. BFS / DFS

The most important pattern for Dropbox — web crawler, DOM search, graph traversal.

### BFS (Level-Order, Shortest Path)

```python
from collections import deque

def bfs(graph: dict[str, list[str]], start: str) -> list[str]:
    visited = {start}
    queue = deque([start])
    order = []
    
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    
    return order

# BFS with level tracking
def bfs_levels(root):
    if not root:
        return []
    queue = deque([root])
    levels = []
    while queue:
        level_size = len(queue)
        level = []
        for _ in range(level_size):
            node = queue.popleft()
            level.append(node.val)
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        levels.append(level)
    return levels
```

**When to use BFS:** Shortest path in unweighted graph, level-order traversal, "minimum steps" problems.

### DFS (Explore Fully, Detect Cycles)

```python
# Iterative DFS (use when recursion depth might overflow)
def dfs_iterative(graph, start):
    visited = set()
    stack = [start]
    order = []
    
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        order.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                stack.append(neighbor)
    
    return order

# Recursive DFS with cycle detection (directed graph)
def has_cycle(graph, n):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = [WHITE] * n
    
    def dfs(node):
        color[node] = GRAY
        for neighbor in graph[node]:
            if color[neighbor] == GRAY:
                return True  # back edge = cycle
            if color[neighbor] == WHITE and dfs(neighbor):
                return True
        color[node] = BLACK
        return False
    
    return any(color[i] == WHITE and dfs(i) for i in range(n))
```

**When to use DFS:** Cycle detection, topological sort, path finding, connected components.

### Grid BFS (Number of Islands Pattern)

```python
def num_islands(grid: list[list[str]]) -> int:
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    count = 0
    
    def bfs(r, c):
        queue = deque([(r, c)])
        grid[r][c] = '0'
        while queue:
            r, c = queue.popleft()
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '1':
                    grid[nr][nc] = '0'
                    queue.append((nr, nc))
    
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                bfs(r, c)
                count += 1
    
    return count
```

---

## 3. Sliding Window

Common in OAs. Two flavors: fixed-size and variable-size.

### Fixed-Size Window

```python
# Maximum sum subarray of size k
def max_sum_subarray(arr: list[int], k: int) -> int:
    window_sum = sum(arr[:k])
    max_sum = window_sum
    
    for i in range(k, len(arr)):
        window_sum += arr[i] - arr[i - k]
        max_sum = max(max_sum, window_sum)
    
    return max_sum
```

### Variable-Size Window

```python
# Longest substring without repeating characters
def length_of_longest_substring(s: str) -> int:
    char_index = {}
    left = 0
    max_len = 0
    
    for right, char in enumerate(s):
        if char in char_index and char_index[char] >= left:
            left = char_index[char] + 1
        char_index[char] = right
        max_len = max(max_len, right - left + 1)
    
    return max_len

# Minimum window substring
def min_window(s: str, t: str) -> str:
    need = Counter(t)
    missing = len(t)
    left = 0
    best = (0, float('inf'))
    
    for right, char in enumerate(s):
        if need[char] > 0:
            missing -= 1
        need[char] -= 1
        
        while missing == 0:
            if right - left < best[1] - best[0]:
                best = (left, right)
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    
    return '' if best[1] == float('inf') else s[best[0]:best[1]+1]
```

---

## 4. Heaps / Priority Queues

Id Allocator, top-K problems, merge-K sorted lists.

```python
import heapq

# Top K frequent elements
def top_k_frequent(nums: list[int], k: int) -> list[int]:
    count = Counter(nums)
    return heapq.nlargest(k, count.keys(), key=count.get)

# Merge K sorted lists
def merge_k_lists(lists: list[list[int]]) -> list[int]:
    heap = []
    for i, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst[0], i, 0))
    
    result = []
    while heap:
        val, list_idx, elem_idx = heapq.heappop(heap)
        result.append(val)
        if elem_idx + 1 < len(lists[list_idx]):
            next_val = lists[list_idx][elem_idx + 1]
            heapq.heappush(heap, (next_val, list_idx, elem_idx + 1))
    
    return result

# Running median (two heaps)
class MedianFinder:
    def __init__(self):
        self.lo = []  # max-heap (negated)
        self.hi = []  # min-heap
    
    def add(self, num: int):
        heapq.heappush(self.lo, -num)
        heapq.heappush(self.hi, -heapq.heappop(self.lo))
        if len(self.hi) > len(self.lo):
            heapq.heappush(self.lo, -heapq.heappop(self.hi))
    
    def median(self) -> float:
        if len(self.lo) > len(self.hi):
            return -self.lo[0]
        return (-self.lo[0] + self.hi[0]) / 2
```

---

## 5. Dynamic Programming

### Framework

1. **Define state** — what variables describe the subproblem?
2. **Define transition** — how does state[i] relate to smaller subproblems?
3. **Define base case** — what's the simplest subproblem?
4. **Define answer** — which state gives the final answer?

```python
# Coin change (classic)
def coin_change(coins: list[int], amount: int) -> int:
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    
    for coin in coins:
        for a in range(coin, amount + 1):
            dp[a] = min(dp[a], dp[a - coin] + 1)
    
    return dp[amount] if dp[amount] != float('inf') else -1

# Longest increasing subsequence
def length_of_lis(nums: list[int]) -> int:
    if not nums:
        return 0
    dp = [1] * len(nums)
    
    for i in range(1, len(nums)):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    
    return max(dp)

# LIS in O(n log n) using binary search
from bisect import bisect_left

def length_of_lis_fast(nums: list[int]) -> int:
    tails = []
    for num in nums:
        pos = bisect_left(tails, num)
        if pos == len(tails):
            tails.append(num)
        else:
            tails[pos] = num
    return len(tails)
```

---

## 6. Backtracking

Common in OAs. Generate combinations, permutations, subsets.

```python
# Combination Sum (candidates can be reused)
def combination_sum(candidates: list[int], target: int) -> list[list[int]]:
    result = []
    
    def backtrack(start: int, remaining: int, path: list[int]):
        if remaining == 0:
            result.append(path[:])
            return
        for i in range(start, len(candidates)):
            if candidates[i] > remaining:
                break
            path.append(candidates[i])
            backtrack(i, remaining - candidates[i], path)
            path.pop()
    
    candidates.sort()
    backtrack(0, target, [])
    return result

# Word Search (grid backtracking)
def exist(board: list[list[str]], word: str) -> bool:
    rows, cols = len(board), len(board[0])
    
    def dfs(r, c, idx):
        if idx == len(word):
            return True
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return False
        if board[r][c] != word[idx]:
            return False
        
        temp = board[r][c]
        board[r][c] = '#'  # mark visited
        
        found = any(
            dfs(r + dr, c + dc, idx + 1)
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]
        )
        
        board[r][c] = temp  # restore
        return found
    
    return any(
        dfs(r, c, 0)
        for r in range(rows)
        for c in range(cols)
    )
```

---

## 7. Concurrency Patterns

Important for Web Crawler and Token Bucket problems.

### Thread Pool with Shared State

```python
import threading
from concurrent.futures import ThreadPoolExecutor

class ThreadSafeSet:
    """Thread-safe set using a lock."""
    def __init__(self):
        self._set = set()
        self._lock = threading.Lock()
    
    def add(self, item) -> bool:
        """Returns True if item was added (not already present)."""
        with self._lock:
            if item in self._set:
                return False
            self._set.add(item)
            return True
    
    def __contains__(self, item) -> bool:
        with self._lock:
            return item in self._set

# Producer-consumer with bounded queue
from queue import Queue

def producer_consumer():
    q = Queue(maxsize=100)
    
    def producer():
        for item in generate_items():
            q.put(item)  # blocks if full
        q.put(None)  # sentinel
    
    def consumer():
        while True:
            item = q.get()  # blocks if empty
            if item is None:
                break
            process(item)
```

### Key Concurrency Concepts

| Concept | When to Use |
|---------|-------------|
| **Lock / Mutex** | Protect shared mutable state |
| **Semaphore** | Limit concurrent access (e.g., max 10 connections) |
| **Queue** | Producer-consumer pattern, bounded buffer |
| **ThreadPoolExecutor** | Fan-out I/O operations (HTTP requests, file reads) |
| **Event** | Signal between threads (one-time or repeating) |

---

## 8. Union-Find

Useful for grouping / connected component problems.

```python
class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.components = n
    
    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # path compression
        return self.parent[x]
    
    def union(self, x: int, y: int) -> bool:
        px, py = self.find(x), self.find(y)
        if px == py:
            return False  # already connected
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        self.components -= 1
        return True

# Example: Number of connected components
def count_components(n: int, edges: list[list[int]]) -> int:
    uf = UnionFind(n)
    for u, v in edges:
        uf.union(u, v)
    return uf.components
```

---

## 9. Quick Reference: Complexity Cheat Sheet

| Data Structure | Access | Search | Insert | Delete |
|---------------|--------|--------|--------|--------|
| Array | O(1) | O(n) | O(n) | O(n) |
| Hash Map | — | O(1) avg | O(1) avg | O(1) avg |
| Heap | — | O(n) | O(log n) | O(log n) |
| BST (balanced) | — | O(log n) | O(log n) | O(log n) |
| Trie | — | O(k) | O(k) | O(k) |
| Union-Find | — | O(α(n)) | O(α(n)) | — |

| Algorithm | Time | Space |
|-----------|------|-------|
| BFS/DFS | O(V+E) | O(V) |
| Binary Search | O(log n) | O(1) |
| Merge Sort | O(n log n) | O(n) |
| Quick Sort | O(n log n) avg | O(log n) |
| Dijkstra | O((V+E) log V) | O(V) |
| Topological Sort | O(V+E) | O(V) |
