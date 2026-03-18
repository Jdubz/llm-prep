/*
Drill 04 — Log Sanitizer

Build a log sanitizer that detects and redacts sensitive data.
Commonly reported Stripe Programming Exercise pattern.
Tests string manipulation speed and regex fluency.

Target time: 30 minutes for all 4 levels.

────────────────────────────────────────
Level 1 — Credit Card Redaction

  sanitize(log: string): string
    Replace credit card numbers with "[REDACTED]".
    A credit card number is 13-19 consecutive digits, optionally
    separated by spaces or dashes in groups of 4
    (e.g., "4242424242424242" or "4242-4242-4242-4242"
    or "4242 4242 4242 4242").

  getRedactionCount(): number
    Returns the total number of redactions performed across all calls.

────────────────────────────────────────
Level 2 — Multi-Pattern Redaction

  addPattern(name: string, regex: RegExp, replacement?: string): void
    Register a named pattern to redact. Default replacement is
    "[REDACTED:{name}]" (e.g., "[REDACTED:ssn]").

  sanitize() now also applies all registered patterns.
    Credit card redaction always runs first, then custom patterns
    in the order they were added.

  getStats(): Record<string, number>
    Returns count of redactions per pattern name.
    Credit card pattern is named "credit_card".

────────────────────────────────────────
Level 3 — Context-Aware Redaction

  sanitizeStructured(obj: Record<string, unknown>): Record<string, unknown>
    Deep-clone the object, then:
    - Any string value: apply all sanitize rules
    - Any key matching sensitive field names (case-insensitive):
      "password", "secret", "token", "api_key", "apikey",
      "authorization" → replace value with "[FILTERED]"
    - Recurse into nested objects and arrays.

────────────────────────────────────────
Level 4 — Streaming & Audit

  createStream(): {
    write(chunk: string): string;
    flush(): string;
    getAuditLog(): AuditEntry[];
  }
    Returns a streaming sanitizer. write() accepts partial log
    lines and returns sanitized output. A credit card number might
    span two chunks, so buffer incomplete patterns.

    flush() returns any buffered content (sanitized).

    AuditEntry = { pattern: string; original: string; line: number }
    getAuditLog() returns all redactions with the pattern name,
    the original matched text, and the 1-based line number.
    Line numbers are determined by newlines in the input.
*/

export type AuditEntry = {
  pattern: string;
  original: string;
  line: number;
};

export class LogSanitizer {
  constructor() {
    throw new Error("TODO: implement constructor");
  }

  // Level 1
  sanitize(log: string): string {
    throw new Error("TODO: implement sanitize");
  }

  getRedactionCount(): number {
    throw new Error("TODO: implement getRedactionCount");
  }

  // Level 2
  addPattern(name: string, regex: RegExp, replacement?: string): void {
    throw new Error("TODO: implement addPattern");
  }

  getStats(): Record<string, number> {
    throw new Error("TODO: implement getStats");
  }

  // Level 3
  sanitizeStructured(obj: Record<string, unknown>): Record<string, unknown> {
    throw new Error("TODO: implement sanitizeStructured");
  }

  // Level 4
  createStream(): {
    write(chunk: string): string;
    flush(): string;
    getAuditLog(): AuditEntry[];
  } {
    throw new Error("TODO: implement createStream");
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
  level("Level 1 — Credit Card Redaction", () => {
    const s = new LogSanitizer();
    check("plain cc", s.sanitize("card: 4242424242424242"), "card: [REDACTED]");
    check("dashed cc", s.sanitize("card: 4242-4242-4242-4242"), "card: [REDACTED]");
    check("spaced cc", s.sanitize("card: 4242 4242 4242 4242"), "card: [REDACTED]");
    check("multiple", s.sanitize("a 4111111111111111 b 5500000000000004 c"),
      "a [REDACTED] b [REDACTED] c");
    check("too short", s.sanitize("card: 123456"), "card: 123456");
    check("no cc", s.sanitize("just a normal log line"), "just a normal log line");
    check("redaction count", s.getRedactionCount(), 5);
    // 13-digit card
    check("13 digit", s.sanitize("card: 4222222222225"), "card: [REDACTED]");
  });

  level("Level 2 — Multi-Pattern", () => {
    const s = new LogSanitizer();
    s.addPattern("email", /[\w.+-]+@[\w-]+\.[\w.]+/g);
    s.addPattern("ssn", /\b\d{3}-\d{2}-\d{4}\b/g);
    check("email", s.sanitize("user: alice@example.com logged in"),
      "user: [REDACTED:email] logged in");
    check("ssn", s.sanitize("ssn: 123-45-6789"),
      "ssn: [REDACTED:ssn]");
    check("cc + custom", s.sanitize("card 4242424242424242 email test@test.com"),
      "card [REDACTED] email [REDACTED:email]");

    // Custom replacement text
    s.addPattern("ip", /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, "x.x.x.x");
    check("custom replacement", s.sanitize("from 192.168.1.1"), "from x.x.x.x");

    const stats = s.getStats();
    check("stats cc", stats["credit_card"], 1);
    check("stats email", stats["email"], 2);
    check("stats ssn", stats["ssn"], 1);
    check("stats ip", stats["ip"], 1);
  });

  level("Level 3 — Context-Aware", () => {
    const s = new LogSanitizer();
    s.addPattern("email", /[\w.+-]+@[\w-]+\.[\w.]+/g);

    const input = {
      user: "alice",
      email: "alice@example.com",
      password: "super-secret-123",
      api_key: "sk_test_abc123",
      nested: {
        token: "tok_xyz",
        data: "card 4242424242424242",
        Authorization: "Bearer tok_live",
      },
      list: ["normal", "secret-in-value 4111111111111111"],
    };

    const result = s.sanitizeStructured(input) as any;
    check("user unchanged", result.user, "alice");
    check("email sanitized", result.email, "[FILTERED]");
    check("password filtered", result.password, "[FILTERED]");
    check("api_key filtered", result.api_key, "[FILTERED]");
    check("nested token filtered", result.nested.token, "[FILTERED]");
    check("nested data cc redacted", result.nested.data, "card [REDACTED]");
    check("nested auth filtered", result.nested.Authorization, "[FILTERED]");
    check("array[0] unchanged", result.list[0], "normal");
    check("array[1] cc redacted", result.list[1], "secret-in-value [REDACTED]");
    // Original unchanged
    check("original preserved", (input as any).password, "super-secret-123");
  });

  level("Level 4 — Streaming & Audit", () => {
    const s = new LogSanitizer();
    const stream = s.createStream();

    // Normal line
    check("normal", stream.write("hello world\n"), "hello world\n");

    // CC split across chunks
    const out1 = stream.write("card: 42424242");
    check("partial buffered", out1, "card: ");
    const out2 = stream.write("42424242\n");
    check("completed cc", out2, "[REDACTED]\n");

    // Flush
    const out3 = stream.write("tail: 1234");
    const flushed = stream.flush();
    check("flushed", out3 + flushed, "tail: 1234");

    // Audit log
    const audit = stream.getAuditLog();
    check("audit length", audit.length, 1);
    check("audit pattern", audit[0].pattern, "credit_card");
    check("audit original", audit[0].original, "4242424242424242");
    check("audit line", audit[0].line, 2);
  });
}

function main(): void {
  console.log("\nLog Sanitizer\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
