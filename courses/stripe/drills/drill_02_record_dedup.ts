/*
Drill 02 — Record Deduplication

Given user records from multiple data sources, identify which records
represent the same person. Commonly reported Stripe Programming
Exercise pattern.

Target time: 35 minutes for all 4 levels.

────────────────────────────────────────
Level 1 — Exact Match Dedup

  type Record = { id: string; email: string; name: string; company: string }

  addRecords(records: Record[]): void
    Ingest a batch of records.

  findExactDupes(): string[][]
    Find groups of records with identical email (case-insensitive).
    Return groups sorted: ids within each group sorted ascending,
    groups sorted by first id ascending.
    Only include groups with 2+ records.

  getUniqueCount(): number
    Returns count of unique entities (by email).

────────────────────────────────────────
Level 2 — Fuzzy Match

  findFuzzyMatches(threshold: number): Array<[string, string, number]>
    Compare all pairs of records. Return pairs where similarity
    score >= threshold.

    Similarity score (0-100) is the average of:
      - email: 100 if equal (case-insensitive), else 0
      - name:  100 if equal (case-insensitive),
               50 if one contains the other, else 0
      - company: 100 if equal (case-insensitive),
                 50 if one contains the other, else 0

    Return as [id1, id2, score] where id1 < id2.
    Sort by score descending, then id1 ascending, then id2 ascending.

────────────────────────────────────────
Level 3 — Transitive Merge

  mergeTransitive(threshold: number): string[][]
    Using fuzzy matches at the given threshold, group records
    transitively: if A matches B and B matches C, then {A, B, C}
    are one group even if A doesn't directly match C.

    Return groups of 2+ records. Ids sorted ascending within group,
    groups sorted by first id ascending.

  getCanonical(recordId: string, threshold: number): Record | null
    For a record, find its merged group (at the given threshold).
    Return a "canonical" record:
      - id: smallest id in the group
      - email: from the record with the smallest id
      - name: longest name in the group
      - company: longest company in the group
    Returns null if recordId not found.

────────────────────────────────────────
Level 4 — Conflict Resolution

  addMergeRule(field: "email" | "name" | "company",
               id1: string, id2: string, action: "match" | "distinct"): void
    Manual override: force two records to be considered matching
    or distinct on a specific field, regardless of the fuzzy score.

  mergeWithRules(threshold: number): string[][]
    Like mergeTransitive, but apply manual rules:
    - "match" rules on any field add 100 to that field's score
      (capped at 100) before averaging.
    - "distinct" rules force the pair to never merge, regardless
      of score.

    Same output format as mergeTransitive.
*/

export type UserRecord = {
  id: string;
  email: string;
  name: string;
  company: string;
};

export class RecordDedup {
  constructor() {
    throw new Error("TODO: implement constructor");
  }

  // Level 1
  addRecords(records: UserRecord[]): void {
    throw new Error("TODO: implement addRecords");
  }

  findExactDupes(): string[][] {
    throw new Error("TODO: implement findExactDupes");
  }

  getUniqueCount(): number {
    throw new Error("TODO: implement getUniqueCount");
  }

  // Level 2
  findFuzzyMatches(threshold: number): Array<[string, string, number]> {
    throw new Error("TODO: implement findFuzzyMatches");
  }

  // Level 3
  mergeTransitive(threshold: number): string[][] {
    throw new Error("TODO: implement mergeTransitive");
  }

  getCanonical(recordId: string, threshold: number): UserRecord | null {
    throw new Error("TODO: implement getCanonical");
  }

  // Level 4
  addMergeRule(field: "email" | "name" | "company", id1: string, id2: string, action: "match" | "distinct"): void {
    throw new Error("TODO: implement addMergeRule");
  }

  mergeWithRules(threshold: number): string[][] {
    throw new Error("TODO: implement mergeWithRules");
  }
}

// ─── Self-Checks (do not edit below this line) ──────────────────

let _passed = 0;
let _failed = 0;

function check(label: string, actual: unknown, expected: unknown): void {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (Object.is(actual, expected) || a === e) {
    _passed++;
    console.log(`  ✓ ${label}`);
  } else {
    _failed++;
    console.log(`  ✗ ${label}`);
    console.log(`    expected: ${e}`);
    console.log(`         got: ${a}`);
  }
}

function level(name: string, fn: () => void): void {
  console.log(name);
  try {
    fn();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("TODO:")) {
      console.log(`  ○ ${msg}`);
    } else {
      _failed++;
      console.log(`  ✗ ${msg}`);
    }
  }
}

function runSelfChecks(): void {
  level("Level 1 — Exact Match Dedup", () => {
    const d = new RecordDedup();
    d.addRecords([
      { id: "r1", email: "alice@example.com", name: "Alice Smith", company: "Acme" },
      { id: "r2", email: "bob@example.com", name: "Bob Jones", company: "Globex" },
      { id: "r3", email: "Alice@Example.com", name: "A. Smith", company: "Acme Inc" },
      { id: "r4", email: "carol@example.com", name: "Carol White", company: "Initech" },
      { id: "r5", email: "BOB@example.com", name: "Robert Jones", company: "Globex Corp" },
    ]);
    check("exact dupes", d.findExactDupes(), [["r1", "r3"], ["r2", "r5"]]);
    check("unique count", d.getUniqueCount(), 3);

    // Additional records
    d.addRecords([
      { id: "r6", email: "alice@example.com", name: "Alice", company: "Acme" },
    ]);
    check("3-way dupe", d.findExactDupes(), [["r1", "r3", "r6"], ["r2", "r5"]]);
    check("unique after add", d.getUniqueCount(), 3);
  });

  level("Level 2 — Fuzzy Match", () => {
    const d = new RecordDedup();
    d.addRecords([
      { id: "r1", email: "alice@example.com", name: "Alice Smith", company: "Acme" },
      { id: "r2", email: "alice@example.com", name: "Alice", company: "Acme Inc" },
      { id: "r3", email: "bob@example.com", name: "Bob Jones", company: "Globex" },
    ]);
    // r1 vs r2: email=100, name=50 (Alice contained in Alice Smith), company=50 (Acme contained in Acme Inc) → avg=66
    // r1 vs r3: email=0, name=0, company=0 → avg=0
    // r2 vs r3: email=0, name=0, company=0 → avg=0
    const matches = d.findFuzzyMatches(50);
    check("fuzzy count", matches.length, 1);
    check("fuzzy match", matches[0], ["r1", "r2", 66]);

    // Lower threshold
    const allPairs = d.findFuzzyMatches(0);
    check("all pairs", allPairs.length, 3);
    check("all pairs sorted by score desc", allPairs[0][2] >= allPairs[1][2], true);
  });

  level("Level 3 — Transitive Merge", () => {
    const d = new RecordDedup();
    d.addRecords([
      { id: "r1", email: "alice@example.com", name: "Alice Smith", company: "Acme" },
      { id: "r2", email: "alice@example.com", name: "Alice", company: "Widgets Co" },
      { id: "r3", email: "asmith@widgets.co", name: "Alice Smith", company: "Widgets Co" },
      { id: "r4", email: "bob@example.com", name: "Bob", company: "Other" },
    ]);
    // r1-r2: email=100, name=50, company=0 → 50
    // r2-r3: email=0, name=50, company=100 → 50
    // r1-r3: email=0, name=100, company=0 → 33
    // At threshold 50: r1-r2 match, r2-r3 match → transitive: {r1, r2, r3}
    check("transitive merge", d.mergeTransitive(50), [["r1", "r2", "r3"]]);

    // Canonical: smallest id = r1
    const canon = d.getCanonical("r3", 50);
    check("canonical id", canon?.id, "r1");
    check("canonical email", canon?.email, "alice@example.com");
    check("canonical name", canon?.name, "Alice Smith"); // longest
    check("canonical company", canon?.company, "Widgets Co"); // longest

    check("canonical not found", d.getCanonical("nope", 50), null);

    // r4 not in any group
    check("singleton canonical", d.getCanonical("r4", 50)?.id, "r4");
  });

  level("Level 4 — Conflict Resolution", () => {
    const d = new RecordDedup();
    d.addRecords([
      { id: "r1", email: "alice@example.com", name: "Alice Smith", company: "Acme" },
      { id: "r2", email: "alice@example.com", name: "Alice Johnson", company: "Acme" },
      { id: "r3", email: "bob@example.com", name: "Bob", company: "Globex" },
      { id: "r4", email: "carol@example.com", name: "Bob", company: "Globex" },
    ]);
    // r1-r2 without rules: email=100, name=0, company=100 → 66 (would merge at threshold 50)
    // Force distinct
    d.addMergeRule("email", "r1", "r2", "distinct");
    check("distinct blocks merge", d.mergeWithRules(50), []);

    // r3-r4: email=0, name=100, company=100 → 66 normally
    // Force match on email → email becomes 100, name=100, company=100 → 100
    d.addMergeRule("email", "r3", "r4", "match");
    check("match forces merge", d.mergeWithRules(50), [["r3", "r4"]]);
  });
}

function main(): void {
  console.log("\nRecord Deduplication\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
