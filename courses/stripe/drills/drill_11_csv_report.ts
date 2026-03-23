/*
Drill 11 — CSV Transaction Report

Parse CSV transaction records, process them with balance validation,
and generate summary reports. This is the most commonly reported
Stripe programming exercise pattern alongside tiered pricing.

Target time: 30 minutes for all 3 parts.

────────────────────────────────────
Part 1 — Parse CSV (8 min)

  parseTransactions(csv: string): Transaction[]

  CSV format (first line is header):
    id,from,to,amount,status
    tx_001,alice,bob,500,completed
    tx_002,bob,carol,200,pending

  Parse into Transaction objects. amount should be a number.
  Skip blank lines.

  Example:
    parseTransactions("id,from,to,amount,status\ntx_001,alice,bob,500,completed")
    → [{ id: "tx_001", from: "alice", to: "bob", amount: 500, status: "completed" }]

────────────────────────────────────
Part 2 — Process with Overdraft Check (12 min)

  processTransactions(
    transactions: Transaction[],
    initialBalances: Map<string, number>
  ): { processed: Transaction[]; rejected: Transaction[]; balances: Map<string, number> }

  Process transactions in order. Rules:
    - Only process transactions with status "completed" (skip others silently)
    - Reject if sender's balance would go negative
    - Update balances for accepted transactions
    - Return the processed list, rejected list, and final balances

  Example (initial: alice=1000, bob=500):
    tx_001: alice→bob 500    → OK (alice=500, bob=1000)
    tx_002: alice→bob 600    → REJECTED (alice only has 500)
    tx_003: bob→alice 200    → OK (bob=800, alice=700)

────────────────────────────────────
Part 3 — Settlement Report (10 min)

  generateReport(transactions: Transaction[]): Report[]

  From processed transactions, compute per-user summaries:
    { user, sent, received, net, txCount }
    - sent: total amount sent by this user
    - received: total amount received by this user
    - net: received - sent
    - txCount: number of transactions involving this user (as sender OR receiver)

  Sort by net descending, then user ascending for ties.
*/

type Transaction = {
  id: string;
  from: string;
  to: string;
  amount: number;
  status: string;
};

type Report = {
  user: string;
  sent: number;
  received: number;
  net: number;
  txCount: number;
};

// Part 1
function parseTransactions(csv: string): Transaction[] { throw new Error("TODO"); }

// Part 2
function processTransactions(
  transactions: Transaction[],
  initialBalances: Map<string, number>,
): { processed: Transaction[]; rejected: Transaction[]; balances: Map<string, number> } {
  throw new Error("TODO");
}

// Part 3
function generateReport(transactions: Transaction[]): Report[] { throw new Error("TODO"); }

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

function part(name: string, fn: () => void): void {
  console.log(name);
  try {
    fn();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("TODO") || msg.includes("is not a function")) {
      console.log(`  ○ not yet implemented`);
    } else {
      _failed++;
      console.log(`  ✗ ${msg}`);
    }
  }
}

function runSelfChecks(): void {
  const csv = `id,from,to,amount,status
tx_001,alice,bob,500,completed
tx_002,bob,carol,200,completed
tx_003,alice,carol,300,pending
tx_004,carol,alice,100,completed
tx_005,alice,bob,1000,completed`;

  part("Part 1 — Parse CSV", () => {
    const txs = parseTransactions(csv);
    check("count", txs.length, 5);
    check("first id", txs[0].id, "tx_001");
    check("first from", txs[0].from, "alice");
    check("first amount is number", typeof txs[0].amount, "number");
    check("first amount", txs[0].amount, 500);
    check("last status", txs[4].status, "completed");

    // Blank lines
    const csvWithBlanks = "id,from,to,amount,status\n\ntx_001,alice,bob,100,completed\n\n";
    check("skips blank lines", parseTransactions(csvWithBlanks).length, 1);
  });

  part("Part 2 — Process with Overdraft Check", () => {
    const txs = parseTransactions(csv);
    const balances = new Map([["alice", 1000], ["bob", 500], ["carol", 200]]);
    const result = processTransactions(txs, balances);

    // tx_001: alice→bob 500 → alice=500, bob=1000 ✓
    // tx_002: bob→carol 200 → bob=800, carol=400 ✓
    // tx_003: pending → skipped
    // tx_004: carol→alice 100 → carol=300, alice=600 ✓
    // tx_005: alice→bob 1000 → alice would be -400 → REJECTED
    check("processed count", result.processed.length, 3);
    check("rejected count", result.rejected.length, 1);
    check("rejected id", result.rejected[0].id, "tx_005");
    check("alice balance", result.balances.get("alice"), 600);
    check("bob balance", result.balances.get("bob"), 800);
    check("carol balance", result.balances.get("carol"), 300);
  });

  part("Part 3 — Settlement Report", () => {
    // Use the processed transactions from Part 2: tx_001, tx_002, tx_004
    const processed: Transaction[] = [
      { id: "tx_001", from: "alice", to: "bob", amount: 500, status: "completed" },
      { id: "tx_002", from: "bob", to: "carol", amount: 200, status: "completed" },
      { id: "tx_004", from: "carol", to: "alice", amount: 100, status: "completed" },
    ];
    const report = generateReport(processed);

    check("report length", report.length, 3);
    // Sorted by net desc: bob(+300), carol(+100), alice(-400)
    check("first user", report[0].user, "bob");
    check("bob sent", report[0].sent, 200);
    check("bob received", report[0].received, 500);
    check("bob net", report[0].net, 300);
    check("bob txCount", report[0].txCount, 2);

    check("second user", report[1].user, "carol");
    check("carol net", report[1].net, 100);
    check("carol txCount", report[1].txCount, 2);

    check("third user", report[2].user, "alice");
    check("alice net", report[2].net, -400);
    check("alice txCount", report[2].txCount, 2);
  });
}

function main(): void {
  console.log("\nCSV Transaction Report\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
