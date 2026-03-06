/*
Drill 02 — Key-Value Store

Implement a KeyValueStore class with CRUD, prefix scanning,
nested transactions, and value history.

────────────────────────────────────────
Level 1 — Basic Operations

  set(key: string, value: string): void
    Set a key to a value. Overwrites if key already exists.

  get(key: string): string | null
    Returns the value for key, or null if not found.

  delete(key: string): boolean
    Removes the key. Returns true if deleted, false if not found.

  count(value: string): number
    Returns the number of keys that currently have this value.

────────────────────────────────────────
Level 2 — Scanning

  keys(): string[]
    Returns all keys, sorted alphabetically.

  prefix(p: string): string[]
    Returns all keys starting with p, sorted alphabetically.

────────────────────────────────────────
Level 3 — Transactions

  begin(): void
    Start a new transaction. Transactions can be nested.

  commit(): boolean
    Commit the current transaction.
    Returns false if there is no active transaction.

  rollback(): boolean
    Rollback the current transaction, discarding all changes
    made since the matching begin().
    Returns false if there is no active transaction.

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

  getHistory(key: string): string[]
    Returns all values ever successfully set for this key, in order.
    Does not include deletions. Returns [] if never set.
    Rolled-back sets do not appear in history.

  undoSet(key: string): boolean
    Reverts key to its previous value (or deletes it if only set once).
    Returns false if no history exists for this key.
    Removes the undone value from history.
*/

export class KeyValueStore {
  constructor() {
    // TODO: initialize your data structures
  }

  set(key: string, value: string): void {
    throw new Error("TODO: implement set");
  }

  get(key: string): string | null {
    throw new Error("TODO: implement get");
  }

  delete(key: string): boolean {
    throw new Error("TODO: implement delete");
  }

  count(value: string): number {
    throw new Error("TODO: implement count");
  }

  keys(): string[] {
    throw new Error("TODO: implement keys");
  }

  prefix(p: string): string[] {
    throw new Error("TODO: implement prefix");
  }

  begin(): void {
    throw new Error("TODO: implement begin");
  }

  commit(): boolean {
    throw new Error("TODO: implement commit");
  }

  rollback(): boolean {
    throw new Error("TODO: implement rollback");
  }

  getHistory(key: string): string[] {
    throw new Error("TODO: implement getHistory");
  }

  undoSet(key: string): boolean {
    throw new Error("TODO: implement undoSet");
  }
}

// ─── Self-Checks (do not edit below this line) ──────────────────

function check(label: string, actual: unknown, expected: unknown): void {
  if (Object.is(actual, expected)) return;
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a === e) return;
  throw new Error(`${label}: expected ${e}, got ${a}`);
}

function runSelfChecks(): void {
  // ── Level 1 ──
  const s1 = new KeyValueStore();
  s1.set("a", "apple");
  s1.set("b", "banana");
  s1.set("c", "apple");
  check("L1 get", s1.get("a"), "apple");
  check("L1 get missing", s1.get("z"), null);
  check("L1 count apple", s1.count("apple"), 2);
  check("L1 count banana", s1.count("banana"), 1);
  check("L1 count missing", s1.count("cherry"), 0);
  check("L1 delete", s1.delete("c"), true);
  check("L1 count after delete", s1.count("apple"), 1);
  check("L1 delete missing", s1.delete("z"), false);
  s1.set("a", "avocado");
  check("L1 overwrite", s1.get("a"), "avocado");
  check("L1 count old val", s1.count("apple"), 0);

  // ── Level 2 ──
  const s2 = new KeyValueStore();
  s2.set("app", "1");
  s2.set("api", "2");
  s2.set("beta", "3");
  check("L2 keys", s2.keys(), ["api", "app", "beta"]);
  check("L2 prefix ap", s2.prefix("ap"), ["api", "app"]);
  check("L2 prefix z", s2.prefix("z"), []);

  // ── Level 3 ──
  const s3 = new KeyValueStore();
  s3.set("x", "1");
  s3.begin();
  s3.set("x", "2");
  check("L3 read in txn", s3.get("x"), "2");
  check("L3 rollback", s3.rollback(), true);
  check("L3 after rollback", s3.get("x"), "1");

  s3.begin();
  s3.set("y", "10");
  check("L3 commit", s3.commit(), true);
  check("L3 after commit", s3.get("y"), "10");

  // nested
  s3.begin();
  s3.set("z", "outer");
  s3.begin();
  s3.set("z", "inner");
  check("L3 nested read", s3.get("z"), "inner");
  check("L3 inner rollback", s3.rollback(), true);
  check("L3 after inner rollback", s3.get("z"), "outer");
  check("L3 outer commit", s3.commit(), true);
  check("L3 after outer commit", s3.get("z"), "outer");

  check("L3 no txn rollback", s3.rollback(), false);
  check("L3 no txn commit", s3.commit(), false);

  // ── Level 4 ──
  const s4 = new KeyValueStore();
  s4.set("k", "first");
  s4.set("k", "second");
  s4.set("k", "third");
  check("L4 history", s4.getHistory("k"), ["first", "second", "third"]);
  check("L4 undo", s4.undoSet("k"), true);
  check("L4 after undo", s4.get("k"), "second");
  check("L4 history after undo", s4.getHistory("k"), ["first", "second"]);
  check("L4 undo again", s4.undoSet("k"), true);
  check("L4 after undo 2", s4.get("k"), "first");
  check("L4 undo last", s4.undoSet("k"), true);
  check("L4 after full undo", s4.get("k"), null);
  check("L4 no more undo", s4.undoSet("k"), false);
  check("L4 empty history", s4.getHistory("k"), []);
  check("L4 never set", s4.getHistory("unknown"), []);
}

function main(): void {
  try {
    runSelfChecks();
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    if (msg.startsWith("TODO:")) {
      console.log(msg);
      return;
    }
    console.log(`FAIL: ${msg}`);
    return;
  }
  console.log("All self-checks passed.");
}

main();
