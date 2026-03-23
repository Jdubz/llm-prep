/*
Drill 05 — API Client (Integration Exercise Prep)

Build a typed API client that interacts with a simulated REST API.
Practices the patterns needed for the Integration Exercise:
pagination, retry with idempotency, webhook processing.

The FakeServer below simulates a REST API. Interact with it via
server.request(method, path, body?, headers?). Returns { status, body }.

Target time: 30 minutes for all 3 parts.

────────────────────────────────────
Part 1 — Requests & Pagination (10 min)

  The server has 25 seeded users and exposes:
    POST   /users          → User  (body: { name, email })
    GET    /users/:id      → User  (404 if not found)
    GET    /users          → { data: User[], has_more: boolean }
      ?limit=N             max per page (default 10)
      ?starting_after=ID   cursor for next page

  Implement:
    createUser(name, email): Promise<User>
    getUser(id): Promise<User | null>       ← return null on 404
    listAllUsers(): Promise<User[]>         ← paginate through ALL pages

  Example:
    await client.createUser("Alice", "a@test.com")
    // → { id: "usr_026", name: "Alice", email: "a@test.com", ... }

    await client.getUser("usr_999")  → null

    await client.listAllUsers()  → [usr_001, ..., usr_025] (3 pages)

────────────────────────────────────
Part 2 — Retry & Idempotency (10 min)

  The server returns 500 on every 5th POST/PUT request.
  POST/PUT accept an "Idempotency-Key" header — the server
  returns a cached response for duplicate keys.

  createUserSafe(name, email, idempotencyKey): Promise<User>
    Retry up to 3 times on 500 errors, passing the same
    idempotency key each time. Throw on non-500 errors.

  withRetry<T>(fn, maxRetries): Promise<T>
    Generic retry wrapper. Retries when the thrown error has
    a .status property === 500. Throws after maxRetries exhausted.

────────────────────────────────────
Part 3 — Webhook Processing (10 min)

  onEvent(eventType, handler): void
    Register a handler for an event type (e.g., "user.created").

  processWebhook(event: WebhookEvent): Promise<boolean>
    - Verify signature: verifySignature(event.id, event.signature, server.secret)
    - Deduplicate by event.id (skip already-processed events)
    - Call the registered handler for event.type
    - Return true if processed, false if invalid/duplicate/no handler

  getProcessedEvents(): string[]
    Return IDs of all successfully processed events, in order.
*/

// ─── Simulated Server (do not edit) ────────────────────────────

type User = { id: string; name: string; email: string; created_at: number };
type WebhookEvent = {
  id: string;
  type: string;
  data: Record<string, unknown>;
  signature: string;
};

type ServerResponse = {
  status: number;
  body: any;
};

class FakeServer {
  private users: Map<string, User> = new Map();
  private nextId = 1;
  private requestCount = 0;
  private idempotencyCache = new Map<string, ServerResponse>();
  readonly secret = "whsec_test123";

  constructor() {
    for (let i = 1; i <= 25; i++) {
      const id = `usr_${String(i).padStart(3, "0")}`;
      this.users.set(id, {
        id,
        name: `User ${i}`,
        email: `user${i}@example.com`,
        created_at: 1000 + i,
      });
    }
    this.nextId = 26;
  }

  async request(
    method: string,
    path: string,
    body?: Record<string, unknown>,
    headers?: Record<string, string>,
  ): Promise<ServerResponse> {
    this.requestCount++;
    const pathOnly = path.split("?")[0];

    // Simulate occasional 500s (every 5th POST/PUT)
    if ((method === "POST" || method === "PUT") && this.requestCount % 5 === 0) {
      const idemKey = headers?.["Idempotency-Key"];
      if (idemKey && this.idempotencyCache.has(idemKey)) {
        return this.idempotencyCache.get(idemKey)!;
      }
      return { status: 500, body: { error: "Internal Server Error" } };
    }

    // Idempotency
    const idemKey = headers?.["Idempotency-Key"];
    if (idemKey && this.idempotencyCache.has(idemKey)) {
      return this.idempotencyCache.get(idemKey)!;
    }

    let response: ServerResponse;
    const userMatch = pathOnly.match(/^\/users\/(.+)$/);

    if (pathOnly === "/users" && method === "GET") {
      response = this.handleListUsers(path);
    } else if (userMatch && method === "GET") {
      const user = this.users.get(userMatch[1]);
      response = user
        ? { status: 200, body: user }
        : { status: 404, body: { error: "Not found" } };
    } else if (pathOnly === "/users" && method === "POST") {
      const id = `usr_${String(this.nextId++).padStart(3, "0")}`;
      const user: User = {
        id,
        name: String(body?.name ?? ""),
        email: String(body?.email ?? ""),
        created_at: Date.now(),
      };
      this.users.set(id, user);
      response = { status: 201, body: user };
    } else {
      response = { status: 404, body: { error: "Not found" } };
    }

    if (idemKey) this.idempotencyCache.set(idemKey, response);
    return response;
  }

  private handleListUsers(path: string): ServerResponse {
    let users = [...this.users.values()].sort((a, b) => a.id.localeCompare(b.id));
    const url = new URL(`http://localhost${path}`);
    const limit = parseInt(url.searchParams.get("limit") ?? "10");
    const startingAfter = url.searchParams.get("starting_after");

    if (startingAfter) {
      const idx = users.findIndex((u) => u.id === startingAfter);
      if (idx >= 0) users = users.slice(idx + 1);
    }

    const page = users.slice(0, limit);
    return {
      status: 200,
      body: { data: page, has_more: users.length > limit },
    };
  }

  makeEvent(type: string, data: Record<string, unknown>): WebhookEvent {
    const id = `evt_${Math.random().toString(36).slice(2, 10)}`;
    return { id, type, data, signature: simpleHash(id + ":" + this.secret) };
  }

  makeBadEvent(type: string, data: Record<string, unknown>): WebhookEvent {
    const id = `evt_${Math.random().toString(36).slice(2, 10)}`;
    return { id, type, data, signature: "bad_signature" };
  }
}

function simpleHash(input: string): string {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    hash = ((hash << 5) - hash + input.charCodeAt(i)) | 0;
  }
  return "sig_" + Math.abs(hash).toString(36);
}

function verifySignature(eventId: string, signature: string, secret: string): boolean {
  return signature === simpleHash(eventId + ":" + secret);
}

// ─── Your Implementation ───────────────────────────────────────

export class ApiClient {
  eventHandlers: Map<string, (event: WebhookEvent) => Promise<void>>
  processedEvents: string[];
  constructor(private server: FakeServer) {
    this.eventHandlers = new Map();
    this.processedEvents = [];
  }

  // Part 1
  async createUser(name: string, email: string): Promise<User> {
    const { status, body } = await this.server.request('POST', '/users', { name, email });
    // console.log(status, body);
    return body;
  }
  // REVIEW: Works, but doesn't check status. If the server returns a
  // non-201 (e.g., 400 for missing fields), this silently returns the
  // error body as if it were a User. In a real integration you'd want:
  //   if (status !== 201) throw new Error(`Create failed: ${status}`);
  // Also: remove commented-out console.log before submitting.

  async getUser(id: string): Promise<User | null> {
    const { status, body } = await this.server.request('GET', `/users/${id}`);
    return status === 200 ? body : null;
  }
  // REVIEW: Clean. Good ternary on status.

  async listAllUsers(): Promise<User[]> {
    const users: User[] = [];
    
    let lastStatus = 200;
    let has_more = true;
    while (lastStatus === 200 && has_more) {
      const path = `/users${users.length ? '?starting_after=' + users.at(-1)!.id : ''}`;
      const { status, body } = await this.server.request('GET', path);
      lastStatus = status;
      has_more = body.has_more;
      users.push(...body.data);
    }
    return users;
  }
  // REVIEW: Correct. The pagination loop is solid — building the cursor
  // from users.at(-1)!.id is clean.
  //
  // Minor: `lastStatus` is tracked but the server always returns 200
  // for list endpoints (errors come as has_more:false + empty data).
  // Not wrong, just unused complexity. The simpler loop is:
  //
  //   let cursor: string | undefined;
  //   while (true) {
  //     const path = `/users?limit=10` + (cursor ? `&starting_after=${cursor}` : '');
  //     const { body } = await this.server.request('GET', path);
  //     users.push(...body.data);
  //     if (!body.has_more) break;
  //     cursor = body.data.at(-1)!.id;
  //   }
  //
  // Also: you don't pass ?limit=10 explicitly. It defaults to 10 in
  // THIS server, but in a real Stripe API call, always set it
  // explicitly — the interviewer may notice.

  // Part 2
  // createUserSafe(name, email, idempotencyKey): Promise<User>
  //   Retry up to 3 times on 500 errors, passing the same
  //   idempotency key each time. Throw on non-500 errors.

  // withRetry<T>(fn, maxRetries): Promise<T>
  //   Generic retry wrapper. Retries when the thrown error has
  //   a .status property === 500. Throws after maxRetries exhausted.
  async createUserSafe(name: string, email: string, idempotencyKey: string): Promise<User> {
    const result = await this.withRetry<ServerResponse>(() => this.server.request('POST', '/users', { name, email }, { 'Idempotency-Key': idempotencyKey }), 3);
    return result?.body;
  }
  // REVIEW: Works for the happy path, but createUserSafe doesn't
  // handle non-500 errors. The spec says "throw on non-500 errors."
  // Right now withRetry retries ALL errors (line 248 catches any
  // exception regardless of .status). A 400 bad request would be
  // retried instead of thrown immediately.
  //
  // Also: the server returns { status, body }. A 500 response doesn't
  // THROW — it returns { status: 500, body: {...} }. Your withRetry
  // expects fn() to throw, but server.request() resolves with the 500
  // response. You need to check the status and throw manually:
  //
  //   const res = await this.server.request(...);
  //   if (res.status === 500) throw Object.assign(new Error(), { status: 500 });
  //   return res.body;
  //
  // This is a common Stripe interview gotcha — fetch/request doesn't
  // reject on HTTP errors, you have to check res.ok / res.status.

  async withRetry<T>(fn: () => Promise<T>, maxRetries: number): Promise<T | null> {
    let retries = 0;
    let result: T | null = null;
    while (!result && retries <= maxRetries) {
      try {
        result = await fn();
      } catch (e: any) {
        retries++
      }
    }
    if (!result) throw new Error();
    return result;
  }
  // REVIEW: Three bugs:
  //
  // 1. Retries on ALL errors, not just status 500. The spec says
  //    "retries when the thrown error has .status === 500." Add:
  //      if ((e as any).status !== 500) throw e;
  //
  // 2. `while (!result && retries <= maxRetries)` — if fn() returns
  //    a falsy value (0, "", false, null), the loop keeps going even
  //    though the call succeeded. Use a success flag instead:
  //      let lastError; for (let i = 0; i <= maxRetries; i++) {
  //        try { return await fn(); } catch (e) { lastError = e; ... }
  //      } throw lastError;
  //
  // 3. Return type is `Promise<T | null>` but the spec says
  //    `Promise<T>`. It should never return null — it either succeeds
  //    or throws.
  //
  // The clearest pattern for retry:
  //   async withRetry<T>(fn, max): Promise<T> {
  //     for (let i = 0; i <= max; i++) {
  //       try { return await fn(); }
  //       catch (e: any) {
  //         if (e.status !== 500 || i === max) throw e;
  //       }
  //     }
  //     throw new Error("unreachable");
  //   }

  // Part 3
  //   onEvent(eventType, handler): void
  //   Register a handler for an event type (e.g., "user.created").

  // processWebhook(event: WebhookEvent): Promise<boolean>
  //   - Verify signature: verifySignature(event.id, event.signature, server.secret)
  //   - Deduplicate by event.id (skip already-processed events)
  //   - Call the registered handler for event.type
  //   - Return true if processed, false if invalid/duplicate/no handler

  // getProcessedEvents(): string[]
  //   Return IDs of all successfully processed events, in order.
  onEvent(eventType: string, handler: (event: WebhookEvent) => Promise<void>): void {
    this.eventHandlers.set(eventType, handler);
  }
  // REVIEW: Clean one-liner.

  async processWebhook(event: WebhookEvent): Promise<boolean> {
    const handler = this.eventHandlers.get(event.type)!;
    if (verifySignature(event.id, event.signature, this.server.secret) && handler && !this.processedEvents.includes(event.id)) {
      await handler(event);
      this.processedEvents.push(event.id);
      return true
    }
    return false
  }
  // REVIEW: Works but has a subtle ordering issue. Line 272 does
  // `this.eventHandlers.get(event.type)!` with a non-null assertion
  // BEFORE checking if the handler exists. The `!` would mask a
  // type error if handler were used before the `&& handler` check.
  // It works at runtime because `&&` short-circuits, but the `!`
  // is lying to TypeScript.
  //
  // The compound `if` on line 273 packs 3 checks into one line.
  // Under interview pressure, guard clauses are easier to read
  // and debug:
  //
  //   if (!verifySignature(event.id, event.signature, this.server.secret)) return false;
  //   if (this.processedEvents.includes(event.id)) return false;
  //   const handler = this.eventHandlers.get(event.type);
  //   if (!handler) return false;
  //   await handler(event);
  //   this.processedEvents.push(event.id);
  //   return true;
  //
  // Also: processedEvents.includes() is O(n) per call. Fine for this
  // drill, but in a real system you'd use a Set for O(1) dedup.
  // An interviewer might ask about scaling this.

  getProcessedEvents(): string[] {
    return this.processedEvents;
  }
  // REVIEW: Returns the internal array directly. A caller doing
  // getProcessedEvents().push("fake") would corrupt your state.
  // Return a copy: `return [...this.processedEvents]`.
  // Small thing but interviewers notice it — shows you think about
  // API boundaries.
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

function part(name: string, fn: () => Promise<void>): Promise<void> {
  return new Promise((resolve) => {
    console.log(name);
    fn()
      .then(resolve)
      .catch((e) => {
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.startsWith("TODO") || msg.includes("is not a function")) {
          console.log(`  ○ not yet implemented`);
        } else {
          _failed++;
          console.log(`  ✗ ${msg}`);
        }
        resolve();
      });
  });
}

async function runSelfChecks(): Promise<void> {
  await part("Part 1 — Requests & Pagination", async () => {
    const server = new FakeServer();
    const client = new ApiClient(server);

    // Paginate through all seeded users
    const allUsers = await client.listAllUsers();
    check("all users count", allUsers.length, 25);
    check("sorted by id", allUsers[0].id, "usr_001");
    check("last user", allUsers[24].id, "usr_025");

    // Get single user
    const user = await client.getUser("usr_001");
    check("get user", user?.name, "User 1");
    check("get missing", await client.getUser("usr_999"), null);

    // Create user
    const created = await client.createUser("New User", "new@test.com");
    check("create name", created.name, "New User");
    check("create has id", created.id.startsWith("usr_"), true);
  });

  await part("Part 2 — Retry & Idempotency", async () => {
    const server = new FakeServer();
    const client = new ApiClient(server);

    // createUserSafe should handle server 500s
    const user = await client.createUserSafe("Safe User", "safe@test.com", "idem_key_1");
    check("safe create", user.name, "Safe User");

    // withRetry generic
    let attempts = 0;
    const result = await client.withRetry(async () => {
      attempts++;
      if (attempts < 3) {
        throw Object.assign(new Error("500"), { status: 500 });
      }
      return "ok";
    }, 5);
    check("retry result", result, "ok");
    check("retry attempts", attempts, 3);

    // Exhausted retries should throw
    let threw = false;
    try {
      await client.withRetry(async () => {
        throw Object.assign(new Error("500"), { status: 500 });
      }, 2);
    } catch {
      threw = true;
    }
    check("retry exhausted throws", threw, true);
  });

  await part("Part 3 — Webhook Processing", async () => {
    const server = new FakeServer();
    const client = new ApiClient(server);

    const events: string[] = [];
    client.onEvent("user.created", async (event) => {
      events.push(event.data.name as string);
    });

    // Valid event
    const evt1 = server.makeEvent("user.created", { name: "Alice" });
    check("process valid", await client.processWebhook(evt1), true);
    check("handler called", events, ["Alice"]);

    // Duplicate
    check("process dup", await client.processWebhook(evt1), false);
    check("handler not called again", events, ["Alice"]);

    // Bad signature
    const badEvt = server.makeBadEvent("user.created", { name: "Evil" });
    check("bad sig rejected", await client.processWebhook(badEvt), false);

    // No handler registered
    const evt2 = server.makeEvent("user.deleted", { id: "usr_001" });
    check("no handler", await client.processWebhook(evt2), false);

    // Second valid event
    const evt3 = server.makeEvent("user.created", { name: "Bob" });
    check("process second", await client.processWebhook(evt3), true);
    check("processed list", client.getProcessedEvents(), [evt1.id, evt3.id]);
  });
}

async function main(): Promise<void> {
  console.log("\nAPI Client\n");
  await runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
