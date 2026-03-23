/*
Drill 09 — String Parsing

String parsing patterns that appear constantly in Stripe interviews.
Accept-Language header parsing, invoice memo extraction, delimiter-based
parsing with edge cases. Focus on clean splitting, normalization, and
matching logic.

Target time: 30 minutes for all 4 levels.

────────────────────────────────────────
Level 1 — Accept-Language Basic Matching (8 min)

  parseAcceptLanguage(header: string, supported: string[]): string[]

    Parse an Accept-Language header like "en-US, fr-CA, fr-FR".
    Return the subset of supported languages that appear in the header,
    in preference order (left-to-right from the header).

    - Trim whitespace around each tag
    - Case-insensitive matching ("en-us" matches "en-US")
    - Only return exact tag matches at this level
    - If no supported languages match, return []

────────────────────────────────────────
Level 2 — Language Variants and Wildcards (8 min)

  parseAcceptLanguageWithVariants(header: string, supported: string[]): string[]

    Extends Level 1 with two new features:

    - Non-region tags: "en" matches any supported language starting with
      "en-" (e.g., "en-US", "en-GB"). Exact matches still take priority
      over prefix matches.
    - Wildcard: "*" matches all remaining supported languages not yet
      in the result.
    - Explicitly listed languages always take precedence over wildcard.
    - Return deduplicated results in preference order.

────────────────────────────────────────
Level 3 — Quality Factors (q-values) (8 min)

  parseAcceptLanguageQuality(header: string, supported: string[]): string[]

    Parse quality weights: "en-US;q=0.8, fr;q=0.9, *;q=0.1"

    - Default q=1.0 if no ;q= is specified
    - q=0 means "specifically not wanted" — exclude these tags entirely
    - Sort matched languages by q-value descending
    - For ties in q-value, preserve original header order
    - When a prefix tag matches multiple supported languages (e.g., "fr"
      matches "fr-CA" and "fr-FR"), they appear in the order they are
      listed in the supported array, all at the same q-value
    - Supports prefix matching ("en" → "en-US") and wildcard ("*")
    - Return sorted, deduplicated matching languages

────────────────────────────────────────
Level 4 — Invoice Memo Parser (8 min)

  reconcilePayments(payments: string[], invoices: string[]): Reconciliation[]

    Parse payment strings:  "PAY001,1500,Paying off: INV-2024-001"
      Format: paymentId,amount,memo
      The memo contains an invoice ID after "Paying off: " or
      "Payment for: " (case-insensitive).

    Parse invoice strings:  "INV-2024-001,2024-01-15,2000"
      Format: invoiceId,date,total

    Match payments to invoices by extracting the invoice ID from the memo.

    Return an array of Reconciliation objects:
      { paymentId, invoiceId, amount, invoiceDate, invoiceTotal, remaining }

    Where remaining = invoiceTotal - (sum of all payments to that invoice).

    Handle:
      - Partial payments (remaining > 0)
      - Multiple payments to the same invoice
      - Payments referencing non-existent invoices (invoiceDate = null,
        invoiceTotal = 0, remaining = -amount)
      - Return results in the order payments appear
*/

interface Reconciliation {
  paymentId: string;
  invoiceId: string;
  amount: number;
  invoiceDate: string | null;
  invoiceTotal: number;
  remaining: number;
}

// Level 1
function parseAcceptLanguage(header: string, supported: string[]): string[] {
  const headerLangs = header.split(',').map(lang => lang.trim());
  const supportedLookup = new Map(supported.map((s) => [s.toLowerCase(), s]));
  const accepted = headerLangs.filter((h => supportedLookup.has(h.toLowerCase())));
  return accepted.map(h => supportedLookup.get(h.toLowerCase())!);
}
// REVIEW: Correct. Clean use of the Map lookup pattern.
//
// Speed tip: you're lowercasing in filter() AND again in map(). You
// can do both in one pass — filter+map is what flatMap is for:
//
//   return headerLangs.flatMap(h => {
//     const match = supportedLookup.get(h.toLowerCase());
//     return match ? [match] : [];
//   });
//
// One iteration, one lowercase call per tag.

// Level 2
function parseAcceptLanguageWithVariants(header: string, supported: string[]): string[] {
  const headerTags = header.split(',').map(lang => lang.trim().toLowerCase());
  const supportedMap = new Map(supported.map((s) => [s.toLowerCase(), s]));
  const result: string[] = [];                                    
  const seen = new Set<string>();
                                                                                                          
  for (const tag of headerTags) {
    if (tag === "*") {                                                                                    
      // all remaining supported                                  
      for (const s of supported) {                                                                        
        if (!seen.has(s.toLowerCase())) { seen.add(s.toLowerCase()); result.push(s); }
      }                                                                                                   
    } else if (tag.includes("-")) {                               
      // exact match                                                                                      
      const original = supportedMap.get(tag);                                                             
      if (original && !seen.has(tag)) { seen.add(tag); result.push(original); }
    } else {                                                                                              
      // prefix match — scan supported for "tag-*"                                                        
      for (const s of supported) {                                                                        
        const sl = s.toLowerCase();                                                                       
        if (sl.startsWith(tag + "-") && !seen.has(sl)) { seen.add(sl); result.push(s); }                  
      }                                                                                                   
    }                                                             
  }     
  
  return result;
}
// REVIEW: Correct. This is well-structured — clean three-branch
// if/else, seen set handles dedup, supported order preserved for
// prefix matches. Nothing to fix.
//
// Speed tip for the interview: this exact for-loop body (the three
// branches: wildcard / exact / prefix) is going to repeat in Level 3.
// Extract it into a helper now:
//
//   function matchTag(tag: string, supported: string[], supportedMap, seen, result) { ... }
//
// Then Level 3 just parses q-values, sorts, filters q=0, and calls
// matchTag per entry. You'd finish Level 3 in ~3 minutes.

// Level 3
function parseAcceptLanguageQuality(header: string, supported: string[]): string[] {
  const headerTags = header.split(',').map(lang => {
    const tag = lang.trim().toLowerCase();
    const [l, q] = tag.split(';');
    let qVal = 1;
    if (q) {
      qVal = +(q.split('=')[1])
    }
    return { l, q: qVal };
  });
  headerTags.sort((a,b) => b.q - a.q);
  const supportedMap = new Map(supported.map((s) => [s.toLowerCase(), s]));
  const seen = new Set();
  const result = [];
  for (const tag of headerTags) {
    if (tag.q === 0) break;
    if (tag.l === "*") {                                                                                    
      // all remaining supported                                  
      for (const s of supported) {                                                                        
        if (!seen.has(s.toLowerCase())) { seen.add(s.toLowerCase()); result.push(s); }
      }                                                                                                   
    } else if (tag.l.includes("-")) {                               
      // exact match                                                                                      
      const original = supportedMap.get(tag.l);                                                             
      if (original && !seen.has(tag.l)) { seen.add(tag.l); result.push(original); }
    } else {                                                                                              
      // prefix match — scan supported for "tag-*"                                                        
      for (const s of supported) {                                                                        
        const sl = s.toLowerCase();                                                                       
        if (sl.startsWith(tag.l + "-") && !seen.has(sl)) { seen.add(sl); result.push(s); }                  
      }                                                                                                   
    }   
  }

  return result;
}
// REVIEW: Correct. Good job recognizing this is the same three-branch
// logic from Level 2. Two things that cost you time:
//
// 1. You copy-pasted the matching logic from Level 2 instead of
//    extracting it. This works but doubled your code and doubled
//    your debug surface. The spec told you Level 3 "supports prefix
//    matching and wildcard" — that's a signal to extract first.
//
// 2. The q-value parsing is clean. One subtlety: the spec says
//    "for ties in q-value, preserve original header order." Your
//    sort is stable in V8/Node (guaranteed since Node 12), so this
//    works. But worth knowing WHY it works — an interviewer might ask.
//
// 3. `break` on q=0 (line 147) only works because you sorted
//    descending — all q=0 entries are at the end. Correct, but if
//    you're unsure about sort stability under pressure, `continue`
//    is safer (skips the entry without relying on position).

// Level 4
function reconcilePayments(payments: string[], invoices: string[]): Reconciliation[] {
  // Handle:
  //     - Partial payments (remaining > 0)
  //     - Multiple payments to the same invoice
  //     - Payments referencing non-existent invoices (invoiceDate = null,
  //       invoiceTotal = 0, remaining = -amount)
  //     - Return results in the order payments appear
  const parseInvoice = ((i: string): any => {
    const invArr = i.split(',');
    return [invArr[0].toLowerCase(), invArr];
  });
  const invMap: Map<string, [string, string, string]> = new Map(invoices.map(parseInvoice));
  const result = payments.map((p) => {
    const payArr = p.split(',');
    const invId = payArr[2].split(':')[1].trim();
    let invoice: [string, string, string, number?] | undefined = invMap.get(invId.toLowerCase());
    if (!invoice) {
      invoice = [invId, "", "0"];
    }
    const remaining = (invoice[3] ?? +invoice[2]) - +payArr[1];
    const rec = {
      paymentId: payArr[0],
      invoiceId: invoice[0],
      amount: +payArr[1],
      invoiceDate: invoice[1] || null,
      invoiceTotal: +invoice[2],
      remaining,
    }
    invoice.push(remaining);
    return rec;
  });
  console.log(result);
  return result;
}
// REVIEW: Works but several things made this harder than it needs to be:
//
// 1. Tuple indexing (invoice[0], invoice[2], payArr[1]) is hard to
//    read and easy to get wrong. Parse into an object up front:
//      const [id, date, total] = line.split(",");
//      return { id, date, total: +total };
//    Then `invoice.date` instead of `invoice[1]`. Costs 1 extra line,
//    saves you from off-by-one index bugs under pressure.
//
// 2. Tracking remaining via invoice.push(remaining) (line 198) mutates
//    the tuple by appending a 4th element, then reads it back on the
//    next payment via invoice[3] (line 189). This is clever but fragile
//    — the type doesn't express it, and a second push would add a 5th
//    element. Cleaner: use a separate Map<string, number> for running
//    totals:
//      const paid = new Map<string, number>();
//      // in the loop:
//      const totalPaid = (paid.get(invId) ?? 0) + amount;
//      paid.set(invId, totalPaid);
//      const remaining = invoiceTotal - totalPaid;
//
// 3. The memo parsing on line 184 splits on ":" and takes [1], which
//    works for "Paying off: INV-2024-001" but would break if the memo
//    had additional colons. Safer: use indexOf + slice, or split with
//    a regex that captures the invoice ID directly:
//      const match = memo.match(/(?:paying off|payment for):\s*([\w-]+)/i);
//
// 4. Remove console.log before submitting (line 201) — interviewers
//    notice leftover debug output.

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
  level("Level 1 — Accept-Language Basic Matching", () => {
    const supported = ["en-US", "fr-CA", "fr-FR", "de-DE"];

    check("basic match",
      parseAcceptLanguage("en-US, fr-CA, fr-FR", supported),
      ["en-US", "fr-CA", "fr-FR"]);

    check("whitespace trimming",
      parseAcceptLanguage("  en-US ,  fr-CA  ", supported),
      ["en-US", "fr-CA"]);

    check("case insensitive",
      parseAcceptLanguage("EN-US, FR-ca", supported),
      ["en-US", "fr-CA"]);

    check("no matches",
      parseAcceptLanguage("ja-JP, ko-KR", supported),
      []);

    check("partial overlap preserves order",
      parseAcceptLanguage("fr-FR, ja-JP, en-US", supported),
      ["fr-FR", "en-US"]);
  });

  level("Level 2 — Language Variants and Wildcards", () => {
    const supported = ["en-US", "en-GB", "fr-CA", "fr-FR", "de-DE"];

    check("prefix match",
      parseAcceptLanguageWithVariants("en", supported),
      ["en-US", "en-GB"]);

    check("exact before prefix",
      parseAcceptLanguageWithVariants("en-GB, en", supported),
      ["en-GB", "en-US"]);

    check("wildcard fills remaining",
      parseAcceptLanguageWithVariants("fr-CA, *", supported),
      ["fr-CA", "en-US", "en-GB", "fr-FR", "de-DE"]);

    check("prefix + wildcard dedup",
      parseAcceptLanguageWithVariants("en, *", supported),
      ["en-US", "en-GB", "fr-CA", "fr-FR", "de-DE"]);
  });

  level("Level 3 — Quality Factors", () => {
    const supported = ["en-US", "en-GB", "fr-CA", "fr-FR", "de-DE"];

    check("q-value sorting",
      parseAcceptLanguageQuality("en-US;q=0.8, fr-CA;q=0.9", supported),
      ["fr-CA", "en-US"]);

    check("default q=1.0",
      parseAcceptLanguageQuality("de-DE, en-US;q=0.5", supported),
      ["de-DE", "en-US"]);

    check("q=0 excluded",
      parseAcceptLanguageQuality("en-US, fr-CA;q=0, de-DE", supported),
      ["en-US", "de-DE"]);

    check("wildcard with q + prefix",
      parseAcceptLanguageQuality("fr;q=0.9, *;q=0.1", supported),
      ["fr-CA", "fr-FR", "en-US", "en-GB", "de-DE"]);
  });

  level("Level 4 — Invoice Memo Parser", () => {
    const invoices = [
      "INV-2024-001,2024-01-15,2000",
      "INV-2024-002,2024-02-20,3000",
    ];

    check("single full payment",
      reconcilePayments(
        ["PAY001,2000,Paying off: INV-2024-001"],
        invoices
      ),
      [{
        paymentId: "PAY001", invoiceId: "INV-2024-001",
        amount: 2000, invoiceDate: "2024-01-15",
        invoiceTotal: 2000, remaining: 0
      }]);

    check("partial payment",
      reconcilePayments(
        ["PAY002,500,Payment for: INV-2024-002"],
        invoices
      ),
      [{
        paymentId: "PAY002", invoiceId: "INV-2024-002",
        amount: 500, invoiceDate: "2024-02-20",
        invoiceTotal: 3000, remaining: 2500
      }]);

    check("multiple payments to same invoice",
      reconcilePayments(
        [
          "PAY003,1000,Paying off: INV-2024-001",
          "PAY004,800,Payment for: INV-2024-001",
        ],
        invoices
      ),
      [
        {
          paymentId: "PAY003", invoiceId: "INV-2024-001",
          amount: 1000, invoiceDate: "2024-01-15",
          invoiceTotal: 2000, remaining: 1000
        },
        {
          paymentId: "PAY004", invoiceId: "INV-2024-001",
          amount: 800, invoiceDate: "2024-01-15",
          invoiceTotal: 2000, remaining: 200
        },
      ]);

    check("payment to non-existent invoice",
      reconcilePayments(
        ["PAY005,750,Paying off: INV-9999-999"],
        invoices
      ),
      [{
        paymentId: "PAY005", invoiceId: "INV-9999-999",
        amount: 750, invoiceDate: null,
        invoiceTotal: 0, remaining: -750
      }]);

    // Case-insensitive memo prefix
    check("case-insensitive memo",
      reconcilePayments(
        ["PAY006,500,paying off: INV-2024-002"],
        invoices
      ),
      [{
        paymentId: "PAY006", invoiceId: "INV-2024-002",
        amount: 500, invoiceDate: "2024-02-20",
        invoiceTotal: 3000, remaining: 2500
      }]);
  });
}

function main(): void {
  console.log("\nString Parsing\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
