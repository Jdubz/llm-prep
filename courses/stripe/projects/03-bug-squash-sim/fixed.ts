/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║                         DO NOT OPEN THIS FILE                           ║
 * ║                                                                         ║
 * ║  This is the answer key. Only read it after you've finished your        ║
 * ║  50-minute Bug Squash attempt. Compare your fixes to these.             ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 */

/**
 * EventBus — A publish/subscribe event system with middleware,
 * retry logic, and dead-letter queue support.
 *
 * @module eventbus
 */

// ─── Types ───────────────────────────────────────────────────────────────────

type EventHandler = (event: EventEnvelope) => void | Promise<void>;

interface EventEnvelope {
  /** The event name, e.g. "order.created" */
  event: string;
  /** Arbitrary event payload */
  data: any;
  /** ISO-8601 timestamp of when the event was published */
  timestamp: string;
  /** Monotonically increasing sequence number */
  sequence: number;
}

interface SubscribeOptions {
  /** Unique identifier for this subscription. Auto-generated if omitted. */
  id?: string;
  /**
   * Execution priority. Higher values run first.
   * @default 0
   */
  priority?: number;
  /**
   * Maximum number of times to retry on handler failure.
   * @default 0
   */
  maxRetries?: number;
  /**
   * Base delay in milliseconds for exponential backoff between retries.
   * @default 100
   */
  retryBaseDelay?: number;
}

interface Subscription {
  id: string;
  pattern: string;
  handler: EventHandler;
  priority: number;
  maxRetries: number;
  retryBaseDelay: number;
  regex: RegExp;
}

interface DeadLetterEntry {
  subscription: Subscription;
  envelope: EventEnvelope;
  error: Error;
  attempts: number;
  failedAt: string;
}

type Middleware = (
  envelope: EventEnvelope,
  next: () => EventEnvelope | null
) => EventEnvelope | null;

// ─── Helpers ─────────────────────────────────────────────────────────────────

let _idCounter = 0;

/** Generate a short unique id for subscriptions */
function generateId(): string {
  return `sub_${++_idCounter}_${Date.now().toString(36)}`;
}

/**
 * Convert a subscription pattern into a RegExp.
 * Supports wildcards:
 *   - "order.*"   matches "order.created", "order.updated"
 *   - "order"     matches only "order" (exact)
 *
 * A trailing `.*` matches exactly one additional segment.
 */
function patternToRegex(pattern: string): RegExp {
  // BUG FIX #2: Wildcard matching was too greedy.
  // The original used "\\..*" which translates to the regex \..*  — this matches
  // a dot followed by ANY characters (including more dots), so "order.*" would
  // match "order.item.created". The fix uses "\\.[^.]*" which translates to
  // \.[^.]* — matching a dot followed by only non-dot characters (one segment).
  const escaped = pattern
    .replace(/\./g, "\\.")
    .replace(/\\\.\*/, "\\.[^.]*");
  return new RegExp(`^${escaped}$`);
}

/**
 * Deep clone a value using structured clone semantics.
 * Falls back to JSON round-trip for environments without structuredClone.
 */
function deepClone<T>(value: T): T {
  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value));
}

/**
 * Sleep for a given number of milliseconds (used for retry backoff).
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ─── EventBus ────────────────────────────────────────────────────────────────

class EventBus {
  private subscriptions: Map<string, Subscription[]> = new Map();
  private middleware: Middleware[] = [];
  private deadLetterQueue: DeadLetterEntry[] = [];
  private eventHistory: EventEnvelope[] = [];
  private sequenceNumber = 0;
  private maxHistorySize: number;

  constructor(options?: { maxHistorySize?: number }) {
    this.maxHistorySize = options?.maxHistorySize ?? 1000;
  }

  // ── Subscribe ────────────────────────────────────────────────────────────

  /**
   * Register a handler for an event pattern.
   *
   * @param pattern - Event name or wildcard pattern (e.g. "order.*")
   * @param handler - Callback invoked when a matching event is published
   * @param options - Subscription options (priority, retry config, etc.)
   * @returns The subscription id
   */
  subscribe(
    pattern: string,
    handler: EventHandler,
    options: SubscribeOptions = {}
  ): string {
    const id = options.id ?? generateId();
    const subscription: Subscription = {
      id,
      pattern,
      handler,
      priority: options.priority ?? 0,
      maxRetries: options.maxRetries ?? 0,
      retryBaseDelay: options.retryBaseDelay ?? 100,
      regex: patternToRegex(pattern),
    };

    const existing = this.subscriptions.get(pattern) ?? [];
    existing.push(subscription);
    this.subscriptions.set(pattern, existing);

    return id;
  }

  // ── Unsubscribe ──────────────────────────────────────────────────────────

  /**
   * Remove a handler by its subscription id.
   *
   * @param pattern - The event pattern the handler was registered under
   * @param handlerId - The subscription id to remove
   * @returns true if the handler was found and removed
   */
  unsubscribe(pattern: string, handlerId: string): boolean {
    const handlers = this.subscriptions.get(pattern);
    if (!handlers) return false;

    // BUG FIX #5: Unsubscribe was using indexOf which searches for the string
    // value in an array of Subscription objects. Since the array contains objects
    // (not strings), indexOf always returns -1 and nothing is ever removed.
    // The fix uses findIndex with a predicate that matches on the id property.
    const index = handlers.findIndex((h) => h.id === handlerId);
    if (index === -1) return false;

    handlers.splice(index, 1);
    if (handlers.length === 0) {
      this.subscriptions.delete(pattern);
    }
    return true;
  }

  // ── Middleware ────────────────────────────────────────────────────────────

  /**
   * Add a middleware function. Middleware runs in order before handlers.
   * A middleware can transform the event envelope or return null to block it.
   */
  use(mw: Middleware): void {
    this.middleware.push(mw);
  }

  /**
   * Run the middleware chain on an envelope.
   * Returns the (possibly transformed) envelope, or null if blocked.
   */
  private applyMiddleware(envelope: EventEnvelope): EventEnvelope | null {
    let current: EventEnvelope | null = envelope;

    for (const mw of this.middleware) {
      if (current === null) break;
      current = mw(current, () => current);
    }

    return current;
  }

  // ── Publish ──────────────────────────────────────────────────────────────

  /**
   * Publish an event synchronously. All matching handlers are invoked
   * in priority order (highest first).
   *
   * @param event - The event name
   * @param data - Arbitrary payload
   * @returns The number of handlers invoked
   */
  publish(event: string, data: any): number {
    const envelope: EventEnvelope = {
      event,
      data,
      timestamp: new Date().toISOString(),
      sequence: ++this.sequenceNumber,
    };

    // Apply middleware
    const processed = this.applyMiddleware(envelope);
    if (processed === null) return 0;

    // Record in history
    this.recordEvent(processed);

    // Gather all matching handlers across all patterns
    const matching = this.getMatchingSubscriptions(event);

    // BUG FIX #1: Priority sort was inverted.
    // The original comparator was (a, b) => a.priority - b.priority which sorts
    // ascending (lowest first). Since higher priority should run first, the
    // comparator needs to be (a, b) => b.priority - a.priority (descending).
    matching.sort((a, b) => b.priority - a.priority);

    let invoked = 0;
    for (const sub of matching) {
      // BUG FIX #3: Event data was shared by reference between handlers.
      // The original code passed the same `processed` envelope object to every
      // handler. If one handler mutated env.data, all subsequent handlers (and
      // the caller's original object) saw the mutation. The fix deep-clones the
      // envelope for each handler so mutations are isolated.
      const handlerEnvelope = deepClone(processed);
      try {
        sub.handler(handlerEnvelope);
        invoked++;
      } catch (err) {
        // Synchronous publish doesn't retry; just count it as invoked
        invoked++;
      }
    }

    return invoked;
  }

  /**
   * Publish an event asynchronously. Returns a promise that resolves when
   * all handlers have completed. Supports retry logic for failed handlers.
   *
   * @param event - The event name
   * @param data - Arbitrary payload
   * @returns The number of handlers that completed successfully
   */
  async publishAsync(event: string, data: any): Promise<number> {
    const envelope: EventEnvelope = {
      event,
      data,
      timestamp: new Date().toISOString(),
      sequence: ++this.sequenceNumber,
    };

    const processed = this.applyMiddleware(envelope);
    if (processed === null) return 0;

    this.recordEvent(processed);

    const matching = this.getMatchingSubscriptions(event);
    matching.sort((a, b) => b.priority - a.priority);

    let succeeded = 0;

    for (const sub of matching) {
      const handlerEnvelope = deepClone(processed);
      let success = false;

      // BUG FIX #4: Retry loop had an off-by-one error.
      // The original loop condition was `attempt < sub.maxRetries` which means
      // with maxRetries=3 the loop runs for attempts 0,1,2 (only 2 retries after
      // the initial attempt, not 3). With maxRetries=0 the loop never runs at all,
      // so the handler is never even called once.
      // The fix uses `attempt <= sub.maxRetries` so attempt 0 is the initial call
      // and attempts 1..maxRetries are the retries, giving exactly maxRetries retries.
      for (let attempt = 0; attempt <= sub.maxRetries; attempt++) {
        try {
          if (attempt > 0) {
            const delay = Math.pow(2, attempt) * sub.retryBaseDelay;
            await sleep(delay);
          }
          await sub.handler(handlerEnvelope);
          success = true;
          break;
        } catch (err) {
          // Will retry if attempts remain
        }
      }

      if (success) {
        succeeded++;
      } else if (sub.maxRetries > 0) {
        this.deadLetterQueue.push({
          subscription: sub,
          envelope: processed,
          error: new Error("Handler failed after all retry attempts"),
          attempts: sub.maxRetries,
          failedAt: new Date().toISOString(),
        });
      }
    }

    return succeeded;
  }

  // ── Query Methods ────────────────────────────────────────────────────────

  /**
   * Get all entries in the dead letter queue.
   */
  getDeadLetterQueue(): DeadLetterEntry[] {
    return [...this.deadLetterQueue];
  }

  /**
   * Clear the dead letter queue and return all entries.
   */
  drainDeadLetterQueue(): DeadLetterEntry[] {
    const entries = this.deadLetterQueue;
    this.deadLetterQueue = [];
    return entries;
  }

  /**
   * Get recent event history.
   *
   * @param limit - Maximum number of events to return (most recent first)
   */
  getHistory(limit?: number): EventEnvelope[] {
    const history = [...this.eventHistory].reverse();
    return limit ? history.slice(0, limit) : history;
  }

  /**
   * Replay recent events to a specific handler. Useful for late subscribers
   * that need to catch up on events they missed.
   *
   * @param pattern - The event pattern to filter history by
   * @param handler - The handler to replay events to
   * @param limit - Maximum number of events to replay
   */
  replay(pattern: string, handler: EventHandler, limit?: number): number {
    const regex = patternToRegex(pattern);
    const matching = this.eventHistory
      .filter((e) => regex.test(e.event))
      .reverse()
      .slice(0, limit);

    let count = 0;
    for (const envelope of matching) {
      try {
        handler(deepClone(envelope));
        count++;
      } catch {
        // skip failed replays
      }
    }
    return count;
  }

  /**
   * Get the count of active subscriptions across all patterns.
   */
  get subscriberCount(): number {
    let count = 0;
    for (const handlers of this.subscriptions.values()) {
      count += handlers.length;
    }
    return count;
  }

  // ── Private Helpers ──────────────────────────────────────────────────────

  /**
   * Find all subscriptions whose pattern matches the given event name.
   */
  private getMatchingSubscriptions(event: string): Subscription[] {
    const result: Subscription[] = [];
    for (const handlers of this.subscriptions.values()) {
      for (const sub of handlers) {
        if (sub.regex.test(event)) {
          result.push(sub);
        }
      }
    }
    return result;
  }

  /**
   * Record an event in the history buffer, evicting old entries if needed.
   */
  private recordEvent(envelope: EventEnvelope): void {
    this.eventHistory.push(envelope);
    while (this.eventHistory.length > this.maxHistorySize) {
      this.eventHistory.shift();
    }
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// TESTS
// ═════════════════════════════════════════════════════════════════════════════

let _passed = 0;
let _failed = 0;

function check(label: string, actual: unknown, expected: unknown): void {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (Object.is(actual, expected) || a === e) {
    _passed++;
    console.log(`  \u2713 ${label}`);
  } else {
    _failed++;
    console.log(`  \u2717 ${label}\n    expected: ${e}\n         got: ${a}`);
  }
}

function section(name: string, fn: () => void | Promise<void>): void {
  console.log(`\n${name}`);
  const result = fn();
  if (result instanceof Promise) {
    result.catch((e: unknown) => {
      _failed++;
      console.log(`  \u2717 CRASH: ${e instanceof Error ? e.message : e}`);
    });
  }
}

// ─── Core Pub/Sub ────────────────────────────────────────────────────────────

section("Core Pub/Sub", () => {
  const bus = new EventBus();
  const received: string[] = [];

  bus.subscribe("user.created", (env) => {
    received.push(env.data.name);
  });

  bus.publish("user.created", { name: "Alice" });
  bus.publish("user.created", { name: "Bob" });

  check("receives published events", received, ["Alice", "Bob"]);
});

section("Core Pub/Sub — multiple subscribers", () => {
  const bus = new EventBus();
  let count = 0;

  bus.subscribe("ping", () => { count++; });
  bus.subscribe("ping", () => { count++; });
  bus.subscribe("ping", () => { count++; });

  const invoked = bus.publish("ping", {});
  check("all subscribers invoked", invoked, 3);
  check("count is correct", count, 3);
});

section("Core Pub/Sub — no cross-talk between events", () => {
  const bus = new EventBus();
  const aEvents: string[] = [];
  const bEvents: string[] = [];

  bus.subscribe("event.a", (env) => { aEvents.push(env.data.v); });
  bus.subscribe("event.b", (env) => { bEvents.push(env.data.v); });

  bus.publish("event.a", { v: "1" });
  bus.publish("event.b", { v: "2" });
  bus.publish("event.a", { v: "3" });

  check("event.a only gets its events", aEvents, ["1", "3"]);
  check("event.b only gets its events", bEvents, ["2"]);
});

section("Core Pub/Sub — returns 0 for no subscribers", () => {
  const bus = new EventBus();
  const invoked = bus.publish("nobody.listens", { x: 1 });
  check("returns 0", invoked, 0);
});

section("Core Pub/Sub — envelope has correct shape", () => {
  const bus = new EventBus();
  let captured: EventEnvelope | null = null;

  bus.subscribe("shape.test", (env) => { captured = env; });
  bus.publish("shape.test", { key: "value" });

  check("envelope has event name", captured!.event, "shape.test");
  check("envelope has data", captured!.data.key, "value");
  check("envelope has timestamp", typeof captured!.timestamp, "string");
  check("envelope has sequence number", typeof captured!.sequence, "number");
});

// ─── Priority ────────────────────────────────────────────────────────────────

section("Priority — handlers execute in priority order", () => {
  const bus = new EventBus();
  const order: number[] = [];

  bus.subscribe("priority.test", () => { order.push(1); }, { priority: 1 });
  bus.subscribe("priority.test", () => { order.push(10); }, { priority: 10 });
  bus.subscribe("priority.test", () => { order.push(5); }, { priority: 5 });

  bus.publish("priority.test", {});
  check("highest priority runs first", order, [10, 5, 1]);
});

section("Priority — equal priority preserves registration order", () => {
  const bus = new EventBus();
  const order: string[] = [];

  bus.subscribe("eq.priority", () => { order.push("first"); }, { priority: 5 });
  bus.subscribe("eq.priority", () => { order.push("second"); }, { priority: 5 });
  bus.subscribe("eq.priority", () => { order.push("third"); }, { priority: 5 });

  bus.publish("eq.priority", {});
  check("preserves insertion order for equal priority", order, ["first", "second", "third"]);
});

section("Priority — default priority is 0", () => {
  const bus = new EventBus();
  const order: string[] = [];

  bus.subscribe("default.pri", () => { order.push("high"); }, { priority: 1 });
  bus.subscribe("default.pri", () => { order.push("default"); });

  bus.publish("default.pri", {});
  check("priority-1 runs before default-0", order, ["high", "default"]);
});

// ─── Wildcards ───────────────────────────────────────────────────────────────

section("Wildcards — star matches one level", () => {
  const bus = new EventBus();
  const received: string[] = [];

  bus.subscribe("order.*", (env) => { received.push(env.event); });

  bus.publish("order.created", { id: 1 });
  bus.publish("order.updated", { id: 2 });
  bus.publish("order.item.added", { id: 3 });

  check("matches single-level events", received, ["order.created", "order.updated"]);
});

section("Wildcards — exact match still works", () => {
  const bus = new EventBus();
  const received: string[] = [];

  bus.subscribe("order.created", (env) => { received.push(env.event); });

  bus.publish("order.created", { id: 1 });
  bus.publish("order.updated", { id: 2 });

  check("only exact event matches", received, ["order.created"]);
});

section("Wildcards — wildcard and exact can coexist", () => {
  const bus = new EventBus();
  const wildcardHits: string[] = [];
  const exactHits: string[] = [];

  bus.subscribe("payment.*", (env) => { wildcardHits.push(env.event); });
  bus.subscribe("payment.completed", (env) => { exactHits.push(env.event); });

  bus.publish("payment.completed", { amount: 100 });
  bus.publish("payment.failed", { reason: "declined" });

  check("wildcard catches both", wildcardHits, ["payment.completed", "payment.failed"]);
  check("exact catches only its event", exactHits, ["payment.completed"]);
});

section("Wildcards — does not match parent event", () => {
  const bus = new EventBus();
  const received: string[] = [];

  bus.subscribe("order.*", (env) => { received.push(env.event); });
  bus.publish("order", { id: 1 });

  check("'order.*' does not match 'order'", received, []);
});

section("Wildcards — does not match deeply nested events", () => {
  const bus = new EventBus();
  const received: string[] = [];

  bus.subscribe("app.*", (env) => { received.push(env.event); });

  bus.publish("app.start", {});
  bus.publish("app.module.load", {});
  bus.publish("app.module.init.complete", {});

  check("only matches one level deep", received, ["app.start"]);
});

// ─── Data Isolation ──────────────────────────────────────────────────────────

section("Data Isolation — handlers get independent copies", () => {
  const bus = new EventBus();
  const snapshots: number[] = [];

  // Both handlers read, then one mutates — order shouldn't matter
  bus.subscribe("iso.test", (env) => {
    snapshots.push(env.data.value);
    env.data.value = 999;
  });

  bus.subscribe("iso.test", (env) => {
    snapshots.push(env.data.value);
    env.data.value = -1;
  });

  bus.publish("iso.test", { value: 42 });
  check("both handlers saw original value", snapshots, [42, 42]);
});

section("Data Isolation — original data is not modified", () => {
  const bus = new EventBus();
  const original = { items: [1, 2, 3] };

  bus.subscribe("no.mutate", (env) => {
    env.data.items.push(4);
  });

  bus.publish("no.mutate", original);
  check("original array unchanged", original.items, [1, 2, 3]);
});

section("Data Isolation — nested object mutations are isolated", () => {
  const bus = new EventBus();
  const results: string[] = [];

  bus.subscribe("nested.iso", (env) => {
    results.push(env.data.user.name);
    env.data.user.name = "CHANGED";
  });

  bus.subscribe("nested.iso", (env) => {
    results.push(env.data.user.name);
  });

  bus.publish("nested.iso", { user: { name: "Original" } });
  check("second handler sees original nested value", results, ["Original", "Original"]);
});

// ─── Middleware ───────────────────────────────────────────────────────────────

section("Middleware — can transform event data", () => {
  const bus = new EventBus();
  let received: any = null;

  bus.use((envelope, next) => {
    const result = next();
    if (result) {
      return { ...result, data: { ...result.data, enriched: true } };
    }
    return result;
  });

  bus.subscribe("mw.transform", (env) => { received = env.data; });
  bus.publish("mw.transform", { value: 42 });

  check("handler sees enriched data", received, { value: 42, enriched: true });
});

section("Middleware — can block events", () => {
  const bus = new EventBus();
  let called = false;

  bus.use((_envelope, _next) => {
    return null; // block everything
  });

  bus.subscribe("mw.block", () => { called = true; });
  const count = bus.publish("mw.block", {});

  check("handler was not called", called, false);
  check("publish returns 0", count, 0);
});

section("Middleware — runs in order", () => {
  const bus = new EventBus();
  const order: number[] = [];

  bus.use((envelope, next) => {
    order.push(1);
    return next();
  });
  bus.use((envelope, next) => {
    order.push(2);
    return next();
  });

  bus.subscribe("mw.order", () => {});
  bus.publish("mw.order", {});

  check("middleware runs in registration order", order, [1, 2]);
});

section("Middleware — passes through unmodified when no middleware", () => {
  const bus = new EventBus();
  let received: any = null;

  bus.subscribe("mw.none", (env) => { received = env.data; });
  bus.publish("mw.none", { raw: true });

  check("data passes through unchanged", received, { raw: true });
});

// ─── Retry & Dead Letter Queue ───────────────────────────────────────────────

section("Retry & DLQ — successful handler on first try", async () => {
  const bus = new EventBus();
  let callCount = 0;

  bus.subscribe("retry.ok", async () => {
    callCount++;
  }, { maxRetries: 3 });

  const succeeded = await bus.publishAsync("retry.ok", {});
  check("handler succeeded", succeeded, 1);
  check("called exactly once", callCount, 1);
  check("DLQ is empty", bus.getDeadLetterQueue().length, 0);
});

section("Retry & DLQ — retries on failure then succeeds", async () => {
  const bus = new EventBus();
  let attempts = 0;

  bus.subscribe("retry.eventual", async () => {
    attempts++;
    if (attempts < 3) {
      throw new Error("not yet");
    }
  }, { maxRetries: 3, retryBaseDelay: 1 });

  const succeeded = await bus.publishAsync("retry.eventual", {});
  check("handler eventually succeeded", succeeded, 1);
  check("took 3 attempts", attempts, 3);
  check("DLQ is empty", bus.getDeadLetterQueue().length, 0);
});

section("Retry & DLQ — exhausts retries and goes to DLQ", async () => {
  const bus = new EventBus();
  let totalAttempts = 0;

  bus.subscribe("retry.fail", async () => {
    totalAttempts++;
    throw new Error("always fails");
  }, { maxRetries: 2, retryBaseDelay: 1 });

  const succeeded = await bus.publishAsync("retry.fail", {});
  check("no handlers succeeded", succeeded, 0);
  check("attempted initial + 2 retries", totalAttempts, 3);
  check("one entry in DLQ", bus.getDeadLetterQueue().length, 1);
});

section("Retry & DLQ — no retries when maxRetries is 0", async () => {
  const bus = new EventBus();
  let attempts = 0;

  bus.subscribe("retry.none", async () => {
    attempts++;
    throw new Error("fail");
  }, { maxRetries: 0 });

  await bus.publishAsync("retry.none", {});
  check("called once with no retries", attempts, 1);
  check("DLQ is empty (no retry config)", bus.getDeadLetterQueue().length, 0);
});

section("Retry & DLQ — drain clears the queue", async () => {
  const bus = new EventBus();

  bus.subscribe("retry.drain", async () => {
    throw new Error("fail");
  }, { maxRetries: 1, retryBaseDelay: 1 });

  await bus.publishAsync("retry.drain", {});
  const drained = bus.drainDeadLetterQueue();
  check("drained 1 entry", drained.length, 1);
  check("DLQ is now empty", bus.getDeadLetterQueue().length, 0);
});

// ─── Unsubscribe ─────────────────────────────────────────────────────────────

section("Unsubscribe — removes a handler", () => {
  const bus = new EventBus();
  const received: string[] = [];

  const id = bus.subscribe("unsub.test", () => { received.push("a"); });
  bus.subscribe("unsub.test", () => { received.push("b"); });

  bus.publish("unsub.test", {});
  check("both handlers fire initially", received, ["a", "b"]);

  received.length = 0;
  const removed = bus.unsubscribe("unsub.test", id);
  check("unsubscribe returns true", removed, true);

  bus.publish("unsub.test", {});
  check("only second handler fires", received, ["b"]);
});

section("Unsubscribe — returns false for unknown id", () => {
  const bus = new EventBus();
  bus.subscribe("unsub.noop", () => {});

  const result = bus.unsubscribe("unsub.noop", "nonexistent_id");
  check("returns false", result, false);
});

section("Unsubscribe — subscriber count decreases", () => {
  const bus = new EventBus();

  const id1 = bus.subscribe("count.test", () => {});
  bus.subscribe("count.test", () => {});

  check("starts with 2 subscribers", bus.subscriberCount, 2);

  bus.unsubscribe("count.test", id1);
  check("down to 1 subscriber", bus.subscriberCount, 1);
});

// ─── Event History ───────────────────────────────────────────────────────────

section("Event History — records published events", () => {
  const bus = new EventBus();

  bus.publish("hist.a", { v: 1 });
  bus.publish("hist.b", { v: 2 });
  bus.publish("hist.c", { v: 3 });

  const history = bus.getHistory();
  check("3 events in history", history.length, 3);
  check("most recent first", history[0].event, "hist.c");
});

section("Event History — respects limit", () => {
  const bus = new EventBus();

  for (let i = 0; i < 10; i++) {
    bus.publish(`hist.${i}`, { i });
  }

  const recent = bus.getHistory(3);
  check("returns only 3", recent.length, 3);
  check("most recent first", recent[0].data.i, 9);
});

section("Event History — respects max history size", () => {
  const bus = new EventBus({ maxHistorySize: 5 });

  for (let i = 0; i < 10; i++) {
    bus.publish(`hist.${i}`, { i });
  }

  const history = bus.getHistory();
  check("capped at 5", history.length, 5);
  check("oldest retained is index 5", history[history.length - 1].data.i, 5);
});

// ─── Replay ──────────────────────────────────────────────────────────────────

section("Replay — replays matching events", () => {
  const bus = new EventBus();

  bus.publish("replay.a", { v: 1 });
  bus.publish("replay.b", { v: 2 });
  bus.publish("replay.a", { v: 3 });

  const replayed: any[] = [];
  const count = bus.replay("replay.a", (env) => { replayed.push(env.data); });

  check("replayed 2 events", count, 2);
  check("most recent first", replayed[0].v, 3);
});

// ─── Final Summary ───────────────────────────────────────────────────────────

// Allow async tests to complete before printing summary
setTimeout(() => {
  console.log("\n════════════════════════════════════");
  console.log(`  ${_passed} passed, ${_failed} failed`);
  console.log("════════════════════════════════════\n");
  if (_failed > 0) process.exit(1);
}, 500);
