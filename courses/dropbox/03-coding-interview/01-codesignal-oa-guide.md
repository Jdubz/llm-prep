# 01 – CodeSignal OA Guide

Dropbox uses CodeSignal for their online assessment. This round has a unique twist: **you are required to use the AI assistant (Cosmo)**. Here's everything you need to know.

---

## 1. Format

| Detail | Value |
|--------|-------|
| **Platform** | CodeSignal |
| **Time limit** | 60 minutes |
| **Questions** | Up to 4 |
| **Passing bar** | ~3 of 4 correct to advance |
| **Proctoring** | Non-proctored (unless specifically requested) |
| **Language** | Your choice: Python, Java, C++, JavaScript/TypeScript, Go, etc. |
| **AI assistant** | **Required** — you must use Cosmo (CodeSignal's AI) |

### The Cosmo Requirement

This is unique to Dropbox. Most companies ban AI tools in assessments. Dropbox **requires** you to use CodeSignal's built-in AI assistant (Cosmo). This signals:
- Dropbox values engineers who can effectively leverage AI tools
- They want to see how you **direct** AI, not just how you code
- The problems may be calibrated harder to account for AI assistance

**How to use Cosmo effectively:**
- Ask it to explain problem constraints you're unsure about
- Use it for boilerplate (parsing input, setting up data structures)
- Ask it to verify your approach before coding
- Don't blindly copy its solutions — review, understand, and modify
- Use it to catch edge cases you might miss

**Practice beforehand:** Go to CodeSignal and familiarize yourself with the Cosmo interface. Don't waste assessment time learning the tool.

---

## 2. Problem Difficulty

Difficulty is **LeetCode medium to medium-hard**. Problems are contextual and practical — not pure algorithmic puzzles.

### Reported Problem Types

| Pattern | Frequency |
|---------|-----------|
| Backtracking | Common |
| Sliding window | Common |
| Graph traversal (BFS/DFS) | Common |
| Dynamic programming | Occasional |
| String manipulation | Common |
| Hash map / set operations | Very common |
| Tree traversal | Occasional |

### Key Differences from LeetCode

- Problems are more **contextual** — framed as real scenarios, not abstract math
- Multiple parts that build in complexity
- You need to handle edge cases and input validation
- Time pressure is real: 15 minutes per question average

---

## 3. Strategy

### Time Management

```
Questions 1-2: ~10-12 min each (easier, get them done fast)
Question 3:    ~15 min (medium difficulty)
Question 4:    ~18-20 min (hardest, may not finish — that's OK)
Buffer:        ~5 min for review
```

### Approach Per Question

1. **Read carefully** — understand all constraints before coding
2. **Think before typing** — 2 minutes of planning saves 5 minutes of debugging
3. **Start with brute force** — get a correct solution, then optimize if time allows
4. **Test with examples** — run through the provided examples manually
5. **Handle edge cases** — empty input, single element, max values

### Common Mistakes

- Spending too long on optimization when brute force passes
- Not reading the full problem (missing constraints)
- Off-by-one errors in sliding window / binary search
- Forgetting to handle the empty input case
- Not using Cosmo (they specifically check for AI usage)

---

## 4. Practice Plan

### Immediate Prep (Use `codesignal-drills/` in This Repo)

The repo already has a CodeSignal practice environment. Use it:

```bash
cd codesignal-drills
# Enable CodeSignal-like editor restrictions
bash toggle-codesignal-mode.sh on
```

### LeetCode Problems That Match Dropbox OA Patterns

**Sliding Window:**
- LC 3: Longest Substring Without Repeating Characters
- LC 76: Minimum Window Substring
- LC 438: Find All Anagrams in a String

**Backtracking:**
- LC 39: Combination Sum
- LC 46: Permutations
- LC 79: Word Search

**Graph Traversal:**
- LC 200: Number of Islands
- LC 207: Course Schedule
- LC 994: Rotting Oranges

**Hash Map / String:**
- LC 49: Group Anagrams
- LC 560: Subarray Sum Equals K
- LC 380: Insert Delete GetRandom O(1)

**Dynamic Programming:**
- LC 322: Coin Change
- LC 300: Longest Increasing Subsequence
- LC 1143: Longest Common Subsequence

### Timed Practice

Do at least 3 timed sessions before the OA:
1. Pick 4 medium LeetCode problems
2. Set a 60-minute timer
3. Use an AI assistant (Copilot, Cursor, or similar) to simulate Cosmo
4. Aim for 3/4 correct solutions

---

## 5. Language Choice

Use whatever language you're fastest in. The OA is language-agnostic.

**Python advantages:**
- Fastest to write (less boilerplate)
- Built-in data structures (defaultdict, Counter, heapq, deque)
- Easy string manipulation
- Cosmo works well with Python

**TypeScript/JavaScript advantages:**
- If it's your strongest language, use it
- Map/Set are solid; array methods are expressive

**Recommendation:** Python for OAs unless you're significantly faster in another language. The time savings from Python's brevity matter in a 60-minute assessment.

---

## 6. Template (Python)

```python
from collections import defaultdict, Counter, deque
from typing import List, Optional
import heapq

# Read input (adjust based on CodeSignal format)
def solve(input_data):
    # 1. Parse input
    # 2. Build data structures
    # 3. Core algorithm
    # 4. Return result
    pass

# Common patterns to have ready:

# BFS template
def bfs(graph, start):
    visited = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

# Sliding window template
def sliding_window(arr, k):
    window = defaultdict(int)
    left = 0
    result = 0
    for right in range(len(arr)):
        window[arr[right]] += 1
        while not valid(window):  # shrink condition
            window[arr[left]] -= 1
            left += 1
        result = max(result, right - left + 1)
    return result

# Binary search template
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

# Union-Find template
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
    
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True
```
