"""
Drill 03 — Hit Counter

Implement a HitCounter class that counts hits within a sliding time window.
Classic Dropbox interview problem — used for rate limiting and analytics.

────────────────────────────────────────
Level 1 — Basic Counter (10 min)

  hit(timestamp: int) -> None
    Record a hit at the given timestamp (in seconds).
    Timestamps are monotonically non-decreasing.

  get_hits(timestamp: int) -> int
    Return the number of hits in the past 300 seconds.
    Window is (timestamp - 300, timestamp], i.e. inclusive of
    timestamp, exclusive of timestamp - 300.

────────────────────────────────────────
Level 2 — Per-Endpoint Tracking (10 min)

  hit(timestamp: int, endpoint: str = "/") -> None
    Record a hit at the given timestamp for the given endpoint.

  get_hits(timestamp: int, endpoint: str | None = None) -> int
    If endpoint is provided, return hits for just that endpoint
    within the window. If None, return total across all endpoints.

  get_endpoints() -> list[str]
    Return all endpoints that have been hit, sorted alphabetically.

────────────────────────────────────────
Level 3 — Configurable Window (10 min)

  Constructor accepts window: int (default 300) — the time window
  in seconds. All methods use this configurable window.

  get_hit_rate(timestamp: int, endpoint: str | None = None) -> float
    Return hits per second in the current window (hits / window).
    Return 0.0 if no hits in the window.

────────────────────────────────────────
Level 4 — Top K (15 min)

  top_endpoints(timestamp: int, k: int) -> list[tuple[str, int]]
    Return the top k endpoints by hit count in the current window.
    Sorted by count descending, then endpoint ascending for ties.
    Return list of (endpoint, count) tuples.

  clear_before(timestamp: int) -> int
    Remove all hits strictly before the given timestamp.
    Return the count of hits removed.
"""
from __future__ import annotations
from collections import defaultdict

class HitCounter:
    def __init__(self, window: int = 300) -> None:
        self.hits = defaultdict(list)
        self.window = window
        pass

    def hit(self, timestamp: int, endpoint: str = "/") -> None:
        self.hits[endpoint].append(timestamp)
    # REVIEW: Clean. Lists stay sorted naturally since timestamps are non-decreasing
    #   — a property you could exploit with bisect for O(log n) window queries.

    def get_hits(self, timestamp: int, endpoint: str | None = None) -> int:
        hits = []
        if endpoint:
            hits += self.hits.get(endpoint, [])
        else:
            for h in self.hits.values():
                hits += h
        total_hits = [h for h in hits if h <= timestamp and h > timestamp - self.window]

        return len(total_hits)
    # REVIEW: `if endpoint:` is a falsy check, not a None check. An empty string ""
    #   would fall through to the all-endpoints branch. Use `if endpoint is not None`.
    #   Also builds a flat list then filters — O(n) space. Could sum counts in-place.

    def get_endpoints(self) -> list[str]:
        return list(self.hits.keys())
    # REVIEW: Spec says "sorted alphabetically" — this returns insertion order.
    #   Tests pass by coincidence. Use `sorted(self.hits.keys())`.
    #   Also returns endpoints even after all their hits are cleared.

    def get_hit_rate(self, timestamp: int, endpoint: str | None = None) -> float:
        hits = self.get_hits(timestamp, endpoint)
        return hits / self.window
    # REVIEW: Clean. Good reuse of get_hits.

    def top_endpoints(self, timestamp: int, k: int) -> list[tuple[str, int]]:
        all_hits = []
        for endpoint in self.hits.keys():
            total_hits = self.get_hits(timestamp, endpoint)
            if total_hits > 0:
                all_hits.append((endpoint, total_hits))
        sorted_hits = sorted(all_hits, key=lambda hit: (-hit[1], hit[0]))
        return sorted_hits[:k]
    # REVIEW: Correct. Good (-count, endpoint) sort key for desc count + alpha tiebreak.

    def clear_before(self, timestamp: int) -> int:
        removed = 0
        for endpoint, hits in self.hits.items():
            self.hits[endpoint] = [h for h in hits if h > timestamp]
            removed += len(hits) - len(self.hits[endpoint])

        return removed
    # REVIEW: Correct. Mutating dict values while iterating .items() is safe in Python
    #   (you're replacing values, not adding/removing keys) — but an interviewer may
    #   ask about it. Leaves empty lists for fully-cleared endpoints, so get_endpoints
    #   still returns them.

# ─── Self-Checks (do not edit below this line) ──────────────────

_passed = 0
_failed = 0


def _check(label: str, actual: object, expected: object) -> None:
    global _passed, _failed
    if actual == expected:
        _passed += 1
        print(f"  \u2713 {label}")
    else:
        _failed += 1
        print(f"  \u2717 {label}")
        print(f"    expected: {expected!r}")
        print(f"         got: {actual!r}")


def _level(name: str, fn) -> None:
    global _failed
    print(name)
    try:
        fn()
    except NotImplementedError as e:
        print(f"  \u25cb {e}")
    except Exception as e:
        _failed += 1
        print(f"  \u2717 {e}")


def _run_self_checks() -> None:
    def level_1():
        c = HitCounter()

        # no hits yet
        _check("no hits", c.get_hits(1), 0)

        # single hit
        c.hit(1)
        _check("one hit", c.get_hits(1), 1)

        # multiple hits at same timestamp
        c.hit(1)
        c.hit(1)
        _check("three hits at t=1", c.get_hits(1), 3)

        # hits within window
        c.hit(100)
        c.hit(200)
        _check("all hits in window", c.get_hits(300), 5)

        # hit exactly at window boundary — t=1 is NOT in (0, 300]
        # wait, (300-300, 300] = (0, 300] so t=1 IS included
        _check("boundary inclusive", c.get_hits(300), 5)

        # hits falling outside the window
        _check("expired hits", c.get_hits(301), 2)  # t=1 hits expire, t=100 and t=200 remain

        # all expired
        _check("all expired", c.get_hits(600), 0)

        # new hit after expiry
        c.hit(600)
        _check("fresh hit after gap", c.get_hits(600), 1)

    _level("Level 1 \u2014 Basic Counter", level_1)

    def level_2():
        c = HitCounter()

        # default endpoint
        c.hit(1)
        _check("default endpoint total", c.get_hits(1), 1)
        _check("default endpoint specific", c.get_hits(1, "/"), 1)

        # multiple endpoints
        c.hit(2, "/api")
        c.hit(3, "/api")
        c.hit(4, "/home")
        _check("total all endpoints", c.get_hits(10), 4)
        _check("/api count", c.get_hits(10, "/api"), 2)
        _check("/home count", c.get_hits(10, "/home"), 1)
        _check("/ count", c.get_hits(10, "/"), 1)

        # unknown endpoint
        _check("unknown endpoint", c.get_hits(10, "/missing"), 0)

        # get_endpoints sorted
        _check("sorted endpoints", c.get_endpoints(), ["/", "/api", "/home"])

    _level("Level 2 \u2014 Per-Endpoint Tracking", level_2)

    def level_3():
        # custom window
        c = HitCounter(window=10)
        c.hit(1)
        c.hit(5)
        c.hit(10)
        _check("all in 10s window", c.get_hits(10), 3)
        _check("one expired", c.get_hits(11), 2)  # t=1 is outside (1, 11]

        # hit rate
        _check("hit rate", c.get_hit_rate(10), 3 / 10)

        # hit rate with no hits
        c2 = HitCounter(window=60)
        _check("hit rate no hits", c2.get_hit_rate(100), 0.0)

        # hit rate per endpoint
        c3 = HitCounter(window=100)
        c3.hit(10, "/a")
        c3.hit(20, "/a")
        c3.hit(30, "/b")
        _check("rate for /a", c3.get_hit_rate(50, "/a"), 2 / 100)
        _check("rate for /b", c3.get_hit_rate(50, "/b"), 1 / 100)
        _check("rate total", c3.get_hit_rate(50), 3 / 100)

        # default window still works
        c4 = HitCounter()
        c4.hit(1)
        _check("default 300s window", c4.get_hits(300), 1)

    _level("Level 3 \u2014 Configurable Window", level_3)

    def level_4():
        c = HitCounter(window=100)

        c.hit(10, "/a")
        c.hit(20, "/a")
        c.hit(30, "/a")
        c.hit(40, "/b")
        c.hit(50, "/b")
        c.hit(60, "/c")

        # top endpoints
        _check("top 2", c.top_endpoints(60, 2), [("/a", 3), ("/b", 2)])
        _check("top all", c.top_endpoints(60, 5), [("/a", 3), ("/b", 2), ("/c", 1)])
        _check("top 0", c.top_endpoints(60, 0), [])

        # ties — sorted by endpoint asc
        c2 = HitCounter(window=100)
        c2.hit(10, "/x")
        c2.hit(20, "/y")
        c2.hit(30, "/z")
        _check("tie breaking", c2.top_endpoints(30, 3), [("/x", 1), ("/y", 1), ("/z", 1)])

        # clear_before
        c3 = HitCounter(window=300)
        c3.hit(10)
        c3.hit(20)
        c3.hit(30)
        c3.hit(100)
        removed = c3.clear_before(25)
        _check("clear_before count", removed, 2)
        _check("hits after clear", c3.get_hits(100), 2)

        # clear_before with nothing to clear
        _check("clear nothing", c3.clear_before(5), 0)

        # top_endpoints respects window
        c4 = HitCounter(window=10)
        c4.hit(1, "/old")
        c4.hit(50, "/new")
        _check("top respects window", c4.top_endpoints(50, 5), [("/new", 1)])

    _level("Level 4 \u2014 Top K", level_4)


def main() -> None:
    print("\nHit Counter\n")
    _run_self_checks()
    total = _passed + _failed
    print(f"\n{_passed}/{total} passed")
    if _failed == 0 and total > 0:
        print("All tests passed.")


if __name__ == "__main__":
    main()
