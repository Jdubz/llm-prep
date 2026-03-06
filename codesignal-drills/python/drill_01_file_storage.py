"""
Drill 01 — File Storage

Implement a FileStorage class that manages files in memory.
Each level adds new methods. Keep all previous methods working.

────────────────────────────────────────
Level 1 — Basic Operations

  add_file(name, size) -> bool
    Add a file. Returns True if added, False if name already exists.

  get_file_size(name) -> int
    Returns the file's size, or -1 if not found.

  delete_file(name) -> bool
    Removes the file. Returns True if deleted, False if not found.

────────────────────────────────────────
Level 2 — Copy & Search

  copy_file(source, dest) -> bool
    Copy source to dest (overwrites dest if it exists).
    Returns False if source does not exist.

  search(prefix) -> list[str]
    Returns up to 10 file names that start with prefix.
    Sort by size descending, then name ascending for ties.

────────────────────────────────────────
Level 3 — Capacity

  Constructor accepts an optional capacity (max total bytes).
  No capacity means unlimited storage.

  add_file returns False if adding would exceed capacity.
  copy_file returns False if copying would exceed capacity
    (only counts the net change — overwriting a file replaces its size).

  get_used_space() -> int — total bytes stored
  get_remaining_space() -> float — bytes remaining (math.inf if unlimited)

────────────────────────────────────────
Level 4 — Undo

  undo() -> bool
    Reverts the last successful add, delete, or copy.
    Returns False if there is nothing to undo.
    Multiple undo() calls walk back through history.
"""

from __future__ import annotations

import math


class FileStorage:
    def __init__(self, capacity: int | None = None) -> None:
        # TODO: initialize your data structures
        pass

    def add_file(self, name: str, size: int) -> bool:
        raise NotImplementedError("TODO: implement add_file")

    def get_file_size(self, name: str) -> int:
        raise NotImplementedError("TODO: implement get_file_size")

    def delete_file(self, name: str) -> bool:
        raise NotImplementedError("TODO: implement delete_file")

    def copy_file(self, source: str, dest: str) -> bool:
        raise NotImplementedError("TODO: implement copy_file")

    def search(self, prefix: str) -> list[str]:
        raise NotImplementedError("TODO: implement search")

    def get_used_space(self) -> int:
        raise NotImplementedError("TODO: implement get_used_space")

    def get_remaining_space(self) -> float:
        raise NotImplementedError("TODO: implement get_remaining_space")

    def undo(self) -> bool:
        raise NotImplementedError("TODO: implement undo")


# ─── Self-Checks (do not edit below this line) ──────────────────


def _check(label: str, actual: object, expected: object) -> None:
    if actual == expected:
        return
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def _run_self_checks() -> None:
    # ── Level 1 ──
    s1 = FileStorage()
    _check("L1 add new", s1.add_file("a.txt", 100), True)
    _check("L1 add dup", s1.add_file("a.txt", 999), False)
    _check("L1 get exists", s1.get_file_size("a.txt"), 100)
    _check("L1 get missing", s1.get_file_size("z.txt"), -1)
    _check("L1 delete exists", s1.delete_file("a.txt"), True)
    _check("L1 delete missing", s1.delete_file("a.txt"), False)
    _check("L1 get after delete", s1.get_file_size("a.txt"), -1)

    # ── Level 2 ──
    s2 = FileStorage()
    s2.add_file("app.js", 300)
    s2.add_file("api.js", 300)
    s2.add_file("assets.zip", 100)
    s2.add_file("readme.md", 50)
    _check("L2 copy ok", s2.copy_file("app.js", "app_backup.js"), True)
    _check("L2 copy missing", s2.copy_file("nope.txt", "x.txt"), False)
    _check("L2 search", s2.search("a"),
           ["api.js", "app.js", "app_backup.js", "assets.zip"])
    _check("L2 search no match", s2.search("zzz"), [])

    # ── Level 3 ──
    s3 = FileStorage(500)
    _check("L3 add within", s3.add_file("a.txt", 200), True)
    _check("L3 add within 2", s3.add_file("b.txt", 200), True)
    _check("L3 add exceeds", s3.add_file("c.txt", 200), False)
    _check("L3 used", s3.get_used_space(), 400)
    _check("L3 remaining", s3.get_remaining_space(), 100)
    s3b = FileStorage()
    s3b.add_file("x.txt", 1000)
    _check("L3 no limit remaining", s3b.get_remaining_space(), math.inf)

    # ── Level 4 ──
    s4 = FileStorage()
    s4.add_file("file.txt", 100)
    s4.delete_file("file.txt")
    _check("L4 after delete", s4.get_file_size("file.txt"), -1)
    _check("L4 undo delete", s4.undo(), True)
    _check("L4 restored", s4.get_file_size("file.txt"), 100)
    _check("L4 undo add", s4.undo(), True)
    _check("L4 fully undone", s4.get_file_size("file.txt"), -1)
    _check("L4 nothing left", s4.undo(), False)

    s4b = FileStorage()
    s4b.add_file("src.txt", 200)
    s4b.copy_file("src.txt", "dst.txt")
    _check("L4 copy created", s4b.get_file_size("dst.txt"), 200)
    _check("L4 undo copy", s4b.undo(), True)
    _check("L4 copy undone", s4b.get_file_size("dst.txt"), -1)
    _check("L4 src intact", s4b.get_file_size("src.txt"), 200)


def main() -> None:
    try:
        _run_self_checks()
    except NotImplementedError as e:
        print(str(e))
        return
    except (AssertionError, AssertionError) as e:
        print(f"FAIL: {e}")
        return

    print("All self-checks passed.")


if __name__ == "__main__":
    main()
