/*
Drill 05 — API Client (Integration Exercise Prep)

Build a typed API client that interacts with a simulated REST API.
This drill practices the patterns needed for the Integration Exercise:
reading a spec, making HTTP-style requests, handling errors, testing.

Instead of real HTTP, we provide a FakeServer you interact with via
request(). The patterns are identical to real fetch() usage.

Target time: 35 minutes for all 4 levels.

────────────────────────────────────────
Level 1 — Basic CRUD Client

  The server exposes a /users resource:
    GET    /users          → { data: User[], has_more: boolean }
    GET    /users/:id      → User
    POST   /users          → User (body: { name, email })
    PUT    /users/:id      → User (body: partial User)
    DELETE /users/:id      → { deleted: true }

  User = { id: string; name: string; email: string; created_at: number }

  Implement:
    listUsers(): Promise<User[]>
    getUser(id: string): Promise<User | null>
      Returns null on 404.
    createUser(name: string, email: string): Promise<User>
    updateUser(id: string, updates: Partial<User>): Promise<User | null>
    deleteUser(id: string): Promise<boolean>

────────────────────────────────────────
Level 2 — Pagination & Search

  GET /users supports query params:
    ?limit=N         → max results per page (default 10)
    ?starting_after=ID → cursor-based pagination
    ?email=X         → exact email filter

  Implement:
    listAllUsers(): Promise<User[]>
      Paginate through ALL users (use limit=10 per page).

    findByEmail(email: string): Promise<User | null>
      Use the email filter. Return first match or null.

────────────────────────────────────────
Level 3 — Idempotency & Retry

  The server occasionally returns 500 errors (simulated).
  POST/PUT requests accept an Idempotency-Key header.

  Implement:
    createUserSafe(name: string, email: string,
                   idempotencyKey: string): Promise<User>
      Retry up to 3 times on 500 errors with the same
      idempotency key. Throw on other error codes.

    withRetry<T>(fn: () => Promise<T>, maxRetries: number): Promise<T>
      Generic retry wrapper. Retries on 500 errors only.
      Throws after maxRetries exhausted.

────────────────────────────────────────
Level 4 — Webhook Processing

  The server can emit events. You register a handler.

  Implement:
    onEvent(eventType: string,
            handler: (event: WebhookEvent) => Promise<void>): void
      Register a handler for an event type (e.g., "user.created").

    processWebhook(event: WebhookEvent): Promise<boolean>
      Process an incoming webhook event.
      - Verify event.signature matches sha256(event.id + ":" + secret)
        (use the verifySignature helper provided).
      - Deduplicate: skip events already processed (by event.id).
      - Call the registered handler for event.type.
      - Return true if processed, false if invalid/duplicate/no handler.

    getProcessedEvents(): string[]
      Returns ids of all successfully processed events, in order.
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
    // Seed data: 25 users
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

    // Route
    const userMatch = path.match(/^\/users\/(.+)$/);

    if (path === "/users" && method === "GET") {
      response = this.handleListUsers(path, body, headers);
    } else if (userMatch && method === "GET") {
      const user = this.users.get(userMatch[1]);
      response = user
        ? { status: 200, body: user }
        : { status: 404, body: { error: "Not found" } };
    } else if (path === "/users" && method === "POST") {
      const id = `usr_${String(this.nextId++).padStart(3, "0")}`;
      const user: User = {
        id,
        name: String(body?.name ?? ""),
        email: String(body?.email ?? ""),
        created_at: Date.now(),
      };
      this.users.set(id, user);
      response = { status: 201, body: user };
    } else if (userMatch && method === "PUT") {
      const user = this.users.get(userMatch[1]);
      if (!user) {
        response = { status: 404, body: { error: "Not found" } };
      } else {
        Object.assign(user, body);
        response = { status: 200, body: user };
      }
    } else if (userMatch && method === "DELETE") {
      if (!this.users.has(userMatch[1])) {
        response = { status: 404, body: { error: "Not found" } };
      } else {
        this.users.delete(userMatch[1]);
        response = { status: 200, body: { deleted: true } };
      }
    } else {
      response = { status: 404, body: { error: "Not found" } };
    }

    if (idemKey) this.idempotencyCache.set(idemKey, response);
    return response;
  }

  private handleListUsers(
    path: string,
    body?: Record<string, unknown>,
    headers?: Record<string, string>,
  ): ServerResponse {
    let users = [...this.users.values()].sort((a, b) => a.id.localeCompare(b.id));

    // Parse query params from path
    const url = new URL(`http://localhost${path}`);
    const limit = parseInt(url.searchParams.get("limit") ?? "10");
    const startingAfter = url.searchParams.get("starting_after");
    const emailFilter = url.searchParams.get("email");

    if (emailFilter) {
      users = users.filter((u) => u.email === emailFilter);
    }

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
  constructor(private server: FakeServer) {
    throw new Error("TODO: implement constructor");
  }

  // Level 1
  async listUsers(): Promise<User[]> {
    throw new Error("TODO: implement listUsers");
  }

  async getUser(id: string): Promise<User | null> {
    throw new Error("TODO: implement getUser");
  }

  async createUser(name: string, email: string): Promise<User> {
    throw new Error("TODO: implement createUser");
  }

  async updateUser(id: string, updates: Partial<User>): Promise<User | null> {
    throw new Error("TODO: implement updateUser");
  }

  async deleteUser(id: string): Promise<boolean> {
    throw new Error("TODO: implement deleteUser");
  }

  // Level 2
  async listAllUsers(): Promise<User[]> {
    throw new Error("TODO: implement listAllUsers");
  }

  async findByEmail(email: string): Promise<User | null> {
    throw new Error("TODO: implement findByEmail");
  }

  // Level 3
  async createUserSafe(name: string, email: string, idempotencyKey: string): Promise<User> {
    throw new Error("TODO: implement createUserSafe");
  }

  async withRetry<T>(fn: () => Promise<T>, maxRetries: number): Promise<T> {
    throw new Error("TODO: implement withRetry");
  }

  // Level 4
  onEvent(eventType: string, handler: (event: WebhookEvent) => Promise<void>): void {
    throw new Error("TODO: implement onEvent");
  }

  async processWebhook(event: WebhookEvent): Promise<boolean> {
    throw new Error("TODO: implement processWebhook");
  }

  getProcessedEvents(): string[] {
    throw new Error("TODO: implement getProcessedEvents");
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

function level(name: string, fn: () => Promise<void>): Promise<void> {
  return new Promise((resolve) => {
    console.log(name);
    fn()
      .then(resolve)
      .catch((e) => {
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.startsWith("TODO:")) {
          console.log(`  ○ ${msg}`);
        } else {
          _failed++;
          console.log(`  ✗ ${msg}`);
        }
        resolve();
      });
  });
}

async function runSelfChecks(): Promise<void> {
  await level("Level 1 — Basic CRUD", async () => {
    const server = new FakeServer();
    const client = new ApiClient(server);

    const users = await client.listUsers();
    check("list returns array", Array.isArray(users), true);
    check("list has users", users.length > 0, true);

    const user = await client.getUser("usr_001");
    check("get user", user?.name, "User 1");
    check("get missing", await client.getUser("usr_999"), null);

    const created = await client.createUser("New User", "new@test.com");
    check("create name", created.name, "New User");
    check("create email", created.email, "new@test.com");
    check("create has id", created.id.startsWith("usr_"), true);

    const updated = await client.updateUser(created.id, { name: "Updated" });
    check("update name", updated?.name, "Updated");
    check("update missing", await client.updateUser("usr_999", { name: "X" }), null);

    check("delete", await client.deleteUser(created.id), true);
    check("delete missing", await client.deleteUser("usr_999"), false);
    check("get after delete", await client.getUser(created.id), null);
  });

  await level("Level 2 — Pagination & Search", async () => {
    const server = new FakeServer();
    const client = new ApiClient(server);

    const allUsers = await client.listAllUsers();
    check("all users count", allUsers.length, 25);
    check("sorted by id", allUsers[0].id, "usr_001");
    check("last user", allUsers[24].id, "usr_025");

    const found = await client.findByEmail("user5@example.com");
    check("find by email", found?.name, "User 5");
    check("find missing email", await client.findByEmail("nope@nope.com"), null);
  });

  await level("Level 3 — Idempotency & Retry", async () => {
    const server = new FakeServer();
    const client = new ApiClient(server);

    // createUserSafe should retry on 500 and succeed
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

    // withRetry exhausted
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

  await level("Level 4 — Webhook Processing", async () => {
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
    check("bad sig", await client.processWebhook(badEvt), false);

    // No handler
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
