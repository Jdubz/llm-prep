# 02 – Classic Dropbox Problems

These problems appear with high frequency in Dropbox interviews. Study the patterns, not just the solutions — interviewers often add twists and follow-ups.

---

## 1. Id Allocator

**Frequency:** Extremely popular — onsites
**Difficulty:** Medium
**Time:** 45 minutes

### Problem

Design a system that allocates and releases integer IDs from a pool of `[0, max_id)`.

```
allocate() → returns the smallest available ID
release(id) → returns the ID to the pool
```

### Approach: Min-Heap

```python
import heapq

class IdAllocator:
    def __init__(self, max_id: int):
        self.max_id = max_id
        self.heap = list(range(max_id))  # O(n) heapify
        heapq.heapify(self.heap)
        self.allocated = set()
    
    def allocate(self) -> int:
        if not self.heap:
            raise RuntimeError("No IDs available")
        id = heapq.heappop(self.heap)
        self.allocated.add(id)
        return id  # O(log n)
    
    def release(self, id: int) -> None:
        if id not in self.allocated:
            return  # idempotent
        self.allocated.discard(id)
        heapq.heappush(self.heap, id)  # O(log n)
```

**Complexity:** allocate O(log n), release O(log n), space O(n)

### Follow-ups (Expect These)

1. **"What if max_id is very large (10^9)?"** — Can't pre-allocate the heap. Use a sorted set or segment tree. Or: track allocated ranges and find gaps.
2. **"Make it thread-safe."** — Add a mutex/lock around allocate and release.
3. **"What if IDs need to be persistent across restarts?"** — Persist the allocated set to disk/DB. Rebuild heap on startup.

---

## 2. Game of Life

**Frequency:** Extremely popular — phone screens
**Difficulty:** Medium
**Time:** 30-40 minutes

### Problem

Implement Conway's Game of Life. Given a board of cells (0=dead, 1=alive), compute the next state in-place.

Rules:
- Live cell with 2-3 neighbors → survives
- Dead cell with exactly 3 neighbors → becomes alive
- All other cells die or stay dead

### Approach: In-Place with State Encoding

```python
def game_of_life(board: list[list[int]]) -> None:
    # Encode transitions in unused bits:
    # 0 → 0: stays dead (0)
    # 1 → 0: was alive, now dead (1)
    # 0 → 1: was dead, now alive (2)
    # 1 → 1: stays alive (3)
    
    rows, cols = len(board), len(board[0])
    
    def count_neighbors(r, c):
        count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    count += board[nr][nc] & 1  # check original state
        return count
    
    # First pass: encode transitions
    for r in range(rows):
        for c in range(cols):
            neighbors = count_neighbors(r, c)
            if board[r][c] == 1:  # currently alive
                if neighbors in (2, 3):
                    board[r][c] = 3  # alive → alive
                # else stays 1 (alive → dead)
            else:  # currently dead
                if neighbors == 3:
                    board[r][c] = 2  # dead → alive
    
    # Second pass: extract new state
    for r in range(rows):
        for c in range(cols):
            board[r][c] >>= 1  # shift right to get new state
```

**Complexity:** O(m×n) time, O(1) space (in-place)

### Follow-ups

1. **"What if the board is infinite?"** — Use a set of live cell coordinates instead of a 2D array. Only process live cells and their neighbors.
2. **"What if the board is very large and sparse?"** — Same as infinite: set-based representation.
3. **"Optimize for repeated simulation?"** — Hashlife algorithm (memoize subgrids).

---

## 3. Web Crawler

**Frequency:** Extremely popular — onsites
**Difficulty:** Medium-Hard
**Time:** 45 minutes

### Problem

Crawl all pages of a website starting from a root URL. Only follow links within the same domain.

### Phase 1: Single-Threaded BFS

```python
from collections import deque
from urllib.parse import urlparse

def crawl(start_url: str) -> list[str]:
    domain = urlparse(start_url).netloc
    visited = set()
    queue = deque([start_url])
    result = []
    
    while queue:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        
        # fetch_page and extract_links are given
        page = fetch_page(url)
        result.append(url)
        
        for link in extract_links(page):
            parsed = urlparse(link)
            if parsed.netloc == domain and link not in visited:
                queue.append(link)
    
    return result
```

### Phase 2: Multi-Threaded (The Real Question)

```python
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor

class WebCrawler:
    def __init__(self, start_url: str, max_workers: int = 10):
        self.domain = urlparse(start_url).netloc
        self.visited = set()
        self.lock = threading.Lock()
        self.results = []
        self.start_url = start_url
    
    def crawl(self) -> list[str]:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = set()
            futures.add(executor.submit(self._process_url, self.start_url))
            
            while futures:
                done = {f for f in futures if f.done()}
                for f in done:
                    futures.discard(f)
                    new_urls = f.result()
                    for url in new_urls:
                        futures.add(executor.submit(self._process_url, url))
        
        return self.results
    
    def _process_url(self, url: str) -> list[str]:
        with self.lock:
            if url in self.visited:
                return []
            self.visited.add(url)
        
        page = fetch_page(url)  # I/O bound — benefits from threading
        
        with self.lock:
            self.results.append(url)
        
        new_urls = []
        for link in extract_links(page):
            parsed = urlparse(link)
            with self.lock:
                if parsed.netloc == self.domain and link not in self.visited:
                    new_urls.append(link)
        
        return new_urls
```

### Follow-ups

1. **"How do you handle rate limiting?"** — Token bucket per domain. Semaphore to limit concurrent requests.
2. **"How do you handle infinite loops / spider traps?"** — URL normalization, max depth limit, max pages limit.
3. **"How do you scale to millions of pages?"** — Distributed crawling with consistent hashing. Each worker owns a set of URL hashes. Shared queue (Redis/Kafka).
4. **"How do you handle politeness?"** — Respect robots.txt, crawl-delay headers, concurrent request limits per domain.

---

## 4. Token Bucket (Rate Limiter)

**Frequency:** Somewhat popular — onsites
**Difficulty:** Medium
**Time:** 30 minutes

### Problem

Implement a thread-safe rate limiter using the token bucket algorithm.

```python
import threading
import time

class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # tokens added per second
        self.capacity = capacity  # max tokens
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()
    
    def allow(self) -> bool:
        with self.lock:
            self._refill()
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now
```

### Follow-ups

1. **"Sliding window vs. token bucket?"** — Sliding window counts requests in a time window (fixed or sliding). Token bucket allows bursts up to capacity.
2. **"Distributed rate limiting?"** — Redis with atomic increment + TTL. Or: token bucket state in a shared store with CAS operations.
3. **"Per-user rate limiting?"** — Dictionary of buckets keyed by user ID. Lazy initialization.

---

## 5. Hit Counter

**Frequency:** Phone screens
**Difficulty:** Easy-Medium
**Time:** 20 minutes

### Problem

Design a hit counter that counts hits in the past 5 minutes (300 seconds).

```python
from collections import deque

class HitCounter:
    def __init__(self):
        self.hits = deque()  # (timestamp,) pairs
    
    def hit(self, timestamp: int) -> None:
        self.hits.append(timestamp)
    
    def get_hits(self, timestamp: int) -> int:
        # Remove hits older than 300 seconds
        while self.hits and self.hits[0] <= timestamp - 300:
            self.hits.popleft()
        return len(self.hits)
```

**Optimization for high throughput:** Use a fixed-size circular buffer of 300 slots (one per second), with each slot storing a count and timestamp.

```python
class HitCounter:
    def __init__(self):
        self.times = [0] * 300
        self.counts = [0] * 300
    
    def hit(self, timestamp: int) -> None:
        idx = timestamp % 300
        if self.times[idx] != timestamp:
            self.times[idx] = timestamp
            self.counts[idx] = 1
        else:
            self.counts[idx] += 1
    
    def get_hits(self, timestamp: int) -> int:
        total = 0
        for i in range(300):
            if timestamp - self.times[i] < 300:
                total += self.counts[i]
        return total
```

---

## 6. Find Duplicate Files

**Frequency:** Phone screens
**Difficulty:** Medium
**Time:** 30 minutes

### Problem

Given a file system path, find all groups of duplicate files (same content).

```python
import os
import hashlib
from collections import defaultdict

def find_duplicates(root: str) -> list[list[str]]:
    # Phase 1: Group by size (fast filter)
    size_groups = defaultdict(list)
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            size = os.path.getsize(filepath)
            size_groups[size].append(filepath)
    
    # Phase 2: Group by hash (only for size-matched files)
    hash_groups = defaultdict(list)
    for size, files in size_groups.items():
        if len(files) < 2:
            continue
        for filepath in files:
            file_hash = hash_file(filepath)
            hash_groups[file_hash].append(filepath)
    
    # Phase 3: Return groups with 2+ files
    return [files for files in hash_groups.values() if len(files) >= 2]

def hash_file(filepath: str) -> str:
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()
```

### Optimizations

1. **Size filter first** — files with unique sizes can't be duplicates
2. **Partial hash** — hash only the first 4KB before computing full hash
3. **Parallel hashing** — use thread pool for I/O-bound hashing
4. **Streaming hash** — read in chunks to handle large files

---

## 7. Other Problems to Know

These appear less frequently but are worth knowing:

| Problem | Key Pattern | Difficulty |
|---------|------------|------------|
| **Space Panorama** | LRU cache + server scaling | Medium-Hard |
| **Download File / BitTorrent** | File assembly, verification | Medium |
| **Phone Number / Dictionary** | T9 keypad, trie | Medium |
| **Find Byte Pattern** | Rabin-Karp rolling hash | Medium-Hard |
| **Search the DOM** | Tree traversal (BFS/DFS) | Medium |
| **Sharpness Value** | Dynamic programming | Medium |

---

## 8. General Interview Tips for Onsite Coding

- **Always talk through your reasoning out loud.** Dropbox explicitly values communication.
- **Always discuss complexity.** Time and space — even if the interviewer doesn't ask.
- **Always ask if there are more parts.** Onsite problems build in complexity. Don't stop.
- **Start with correctness, then optimize.** A working brute force beats an incomplete optimal solution.
- **Test your code.** Walk through an example input step by step.
- **AI is banned in onsite rounds.** Only the CodeSignal OA allows (requires) AI assistance.
