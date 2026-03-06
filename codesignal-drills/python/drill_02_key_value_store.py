"""
Drill 02 — Key-Value Store

Implement a KeyValueStore class with CRUD, prefix scanning,
nested transactions, and value history.

────────────────────────────────────────
Level 1 — Basic Operations

  set(key, value) -> None
    Set a key to a value. Overwrites if key already exists.

  get(key) -> str | None
    Returns the value for key, or None if not found.

  delete(key) -> bool
    Removes the key. Returns True if deleted, False if not found.

  count(value) -> int
    Returns the number of keys that currently have this value.

────────────────────────────────────────
Level 2 — Scanning

  keys() -> list[str]
    Returns all keys, sorted alphabetically.

  prefix(p) -> list[str]
    Returns all keys starting with p, sorted alphabetically.

────────────────────────────────────────
Level 3 — Transactions

  begin() -> None
    Start a new transaction. Transactions can be nested.

  commit() -> bool
    Commit the current transaction.
    Returns False if there is no active transaction.

  rollback() -> bool
    Rollback the current transaction, discarding all changes
    made since the matching begin().
    Returns False if there is no active transaction.

  Notes:
  - Nested transactions work like a stack.
  - Rolling back an inner transaction discards only that
    transaction's changes.
  - Committing an inner transaction merges its changes into
    the outer transaction (or into the main store if outermost).
  - get, count, keys, prefix all reflect uncommitted changes
    within the current transaction.

────────────────────────────────────────
Level 4 — History

  get_history(key) -> list[str]
    Returns all values ever successfully set for this key, in order.
    Does not include deletions. Returns [] if never set.
    Rolled-back sets do not appear in history.

  undo_set(key) -> bool
    Reverts key to its previous value (or deletes it if only set once).
    Returns False if no history exists for this key.
    Removes the undone value from history.
"""

from __future__ import annotations


class KeyValueStore:
    def __init__(self) -> None:
        # TODO: initialize your data structures
        pass

    def set(self, key: str, value: str) -> None:
        raise NotImplementedError("TODO: implement set")

    def get(self, key: str) -> str | None:
        raise NotImplementedError("TODO: implement get")

    def delete(self, key: str) -> bool:
        raise NotImplementedError("TODO: implement delete")

    def count(self, value: str) -> int:
        raise NotImplementedError("TODO: implement count")

    def keys(self) -> list[str]:
        raise NotImplementedError("TODO: implement keys")

    def prefix(self, p: str) -> list[str]:
        raise NotImplementedError("TODO: implement prefix")

    def begin(self) -> None:
        raise NotImplementedError("TODO: implement begin")

    def commit(self) -> bool:
        raise NotImplementedError("TODO: implement commit")

    def rollback(self) -> bool:
        raise NotImplementedError("TODO: implement rollback")

    def get_history(self, key: str) -> list[str]:
        raise NotImplementedError("TODO: implement get_history")

    def undo_set(self, key: str) -> bool:
        raise NotImplementedError("TODO: implement undo_set")


# ─── Self-Checks (do not edit below this line) ──────────────────


def _check(label: str, actual: object, expected: object) -> None:
    if actual == expected:
        return
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def _run_self_checks() -> None:
    # ── Level 1 ──
    s1 = KeyValueStore()
    s1.set("a", "apple")
    s1.set("b", "banana")
    s1.set("c", "apple")
    _check("L1 get", s1.get("a"), "apple")
    _check("L1 get missing", s1.get("z"), None)
    _check("L1 count apple", s1.count("apple"), 2)
    _check("L1 count banana", s1.count("banana"), 1)
    _check("L1 count missing", s1.count("cherry"), 0)
    _check("L1 delete", s1.delete("c"), True)
    _check("L1 count after delete", s1.count("apple"), 1)
    _check("L1 delete missing", s1.delete("z"), False)
    s1.set("a", "avocado")
    _check("L1 overwrite", s1.get("a"), "avocado")
    _check("L1 count old val", s1.count("apple"), 0)

    # ── Level 2 ──
    s2 = KeyValueStore()
    s2.set("app", "1")
    s2.set("api", "2")
    s2.set("beta", "3")
    _check("L2 keys", s2.keys(), ["api", "app", "beta"])
    _check("L2 prefix ap", s2.prefix("ap"), ["api", "app"])
    _check("L2 prefix z", s2.prefix("z"), [])

    # ── Level 3 ──
    s3 = KeyValueStore()
    s3.set("x", "1")
    s3.begin()
    s3.set("x", "2")
    _check("L3 read in txn", s3.get("x"), "2")
    _check("L3 rollback", s3.rollback(), True)
    _check("L3 after rollback", s3.get("x"), "1")

    s3.begin()
    s3.set("y", "10")
    _check("L3 commit", s3.commit(), True)
    _check("L3 after commit", s3.get("y"), "10")

    # nested
    s3.begin()
    s3.set("z", "outer")
    s3.begin()
    s3.set("z", "inner")
    _check("L3 nested read", s3.get("z"), "inner")
    _check("L3 inner rollback", s3.rollback(), True)
    _check("L3 after inner rollback", s3.get("z"), "outer")
    _check("L3 outer commit", s3.commit(), True)
    _check("L3 after outer commit", s3.get("z"), "outer")

    _check("L3 no txn rollback", s3.rollback(), False)
    _check("L3 no txn commit", s3.commit(), False)

    # ── Level 4 ──
    s4 = KeyValueStore()
    s4.set("k", "first")
    s4.set("k", "second")
    s4.set("k", "third")
    _check("L4 history", s4.get_history("k"), ["first", "second", "third"])
    _check("L4 undo", s4.undo_set("k"), True)
    _check("L4 after undo", s4.get("k"), "second")
    _check("L4 history after undo", s4.get_history("k"), ["first", "second"])
    _check("L4 undo again", s4.undo_set("k"), True)
    _check("L4 after undo 2", s4.get("k"), "first")
    _check("L4 undo last", s4.undo_set("k"), True)
    _check("L4 after full undo", s4.get("k"), None)
    _check("L4 no more undo", s4.undo_set("k"), False)
    _check("L4 empty history", s4.get_history("k"), [])
    _check("L4 never set", s4.get_history("unknown"), [])


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
