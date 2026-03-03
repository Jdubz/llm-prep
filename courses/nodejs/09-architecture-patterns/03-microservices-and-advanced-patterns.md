# 03 – Microservices and Advanced Patterns

## Microservices vs Monolith

### The Modular Monolith: The Sweet Spot

```
src/
├── modules/
│   ├── orders/
│   │   ├── domain/          # Entities, value objects, events
│   │   ├── application/     # Use cases, DTOs
│   │   ├── infrastructure/  # Repositories, external clients
│   │   ├── presentation/    # Routes, controllers
│   │   └── index.ts         # Public API
│   ├── inventory/
│   └── payments/
├── shared/                  # Shared kernel (events, base classes)
└── main.ts
```

Enforce boundaries with TypeScript project references or ESLint import rules. Modules communicate via events, not direct imports.

### Microservices vs Monolith Decision Tree

```
START: Do you have 2+ of these?
  ├── Need independent scaling for specific modules? ──→ YES
  ├── Module deploys 5x more frequently than the rest? ──→ YES
  ├── Module needs a different runtime/language? ──→ YES
  ├── Dedicated team (4+) owns the module? ──→ YES
  └── Module failure must not take down the system? ──→ YES

Count YES answers:
  0-1 ──→ MODULAR MONOLITH (enforce module boundaries, extract later)
  2+  ──→ EXTRACT THAT MODULE (keep the rest as monolith)
  All ──→ MICROSERVICES (but honestly, re-check your assumptions)
```

### Extraction Criteria

Extract a module into a separate service when at least two of these apply:

1. **Independent scaling**: Module needs 10x the compute of everything else
2. **Independent deployment**: Module changes 5x more frequently
3. **Technology divergence**: Module needs a different runtime
4. **Team autonomy**: Dedicated team, cross-team coordination is the bottleneck
5. **Fault isolation**: Module failure must not take down the system

### Inter-Service Communication

| Method | Use When | Coupling |
|--------|----------|----------|
| HTTP/REST | Sync request/response, CRUD | High |
| gRPC | High-throughput internal, streaming | High (schema) |
| Message Queue | Async processing, decoupled | Low |
| Event Bus | Broadcasting state changes | Very Low |

### API Gateway and Service Discovery

Gateway handles: routing, auth, rate limiting, response aggregation, circuit breaking. Use Kong, Envoy, or AWS API Gateway.

Service discovery in Kubernetes: built-in DNS. Without K8s: Consul, etcd, or cloud provider solutions.

---

## Vertical Slice Architecture

Rejects layers entirely. Each use case is self-contained from HTTP handler to database query.

```
src/features/
├── place-order/
│   ├── PlaceOrderHandler.ts   # HTTP handler
│   ├── PlaceOrderCommand.ts   # Input validation
│   ├── PlaceOrderLogic.ts     # Business logic
│   ├── PlaceOrderQuery.ts     # Direct DB query
│   └── PlaceOrder.test.ts
├── get-order-details/
└── cancel-order/
```

**Wins**: Features are independently modifiable, new engineers understand one slice without learning the full architecture, deletion is trivial (remove directory + route).

**Loses**: Shared domain logic requires careful management (duplication vs shared kernel), cross-cutting concerns need a separate solution.

**Practical hybrid**: Feature-based structure at top level, shared domain extracted only when genuinely reused across 3+ features.

---

## Modular Monolith with NestJS

NestJS modules map naturally to bounded contexts.

```typescript
@Module({
  imports: [TypeOrmModule.forFeature([OrderEntity]), BullModule.registerQueue({ name: 'orders' })],
  controllers: [OrderController],
  providers: [
    PlaceOrderUseCase,
    { provide: 'OrderRepository', useClass: TypeOrmOrderRepository },
    { provide: 'InventoryChecker', useClass: InventoryModuleClient },
    OrderSaga,
  ],
  exports: ['OrderRepository'], // Only what other modules need
})
export class OrdersModule {}

// Cross-module communication via events
@Injectable()
class OrderSaga {
  @OnEvent('inventory.reserved')
  async handleInventoryReserved(event: InventoryReservedEvent): Promise<void> {
    const order = await this.orderRepo.findById(event.orderId);
    order.confirmInventory();
    await this.orderRepo.save(order);
    this.eventBus.emit(new OrderConfirmedEvent(order.id));
  }
}
```

**Boundary enforcement**: Use `@Global()` sparingly. If you're making modules global so others can access them, your boundaries are leaking.

---

## Strangler Fig Pattern

Incrementally migrate from legacy to new architecture.

```typescript
// Proxy layer sits in front of both systems
const legacyProxy = httpProxy.createProxyMiddleware({ target: 'http://legacy:8080' });

// New service handles migrated routes
app.use('/api/v2/orders', orderRouter);
// Legacy handles everything else
app.use('/api', legacyProxy);
```

**Migration steps**:
1. Identify a bounded context with clear boundaries
2. Build in new architecture
3. Route traffic via proxy/gateway
4. Shadow traffic for parity verification
5. Cut over
6. Decommission legacy code
7. Repeat

**Pitfall**: Dual-write is dangerous during migration. Prefer event-based sync or database CDC (Debezium) to keep systems consistent.

---

## Multi-Repo vs Monorepo

### Turborepo

```
my-platform/
├── turbo.json
├── apps/
│   ├── api/         # Express/Fastify
│   ├── web/         # Next.js
│   └── worker/      # Background jobs
├── packages/
│   ├── domain/      # Shared domain
│   ├── database/    # Prisma schema
│   ├── config/      # Shared config
│   └── tsconfig/    # Shared TS configs
```

### Nx

More structure: generators, affected commands, dependency graph visualization, module boundary enforcement via ESLint rules and project tags.

### Decision Matrix

| Factor | Multi-Repo | Monorepo |
|--------|-----------|----------|
| Team size | 50+ engineers, autonomous teams | 2-30, shared ownership |
| Code sharing | Publish to registry | Direct imports |
| Consistency | Hard to enforce | Easy (shared configs) |
| CI complexity | Simple per-repo | Need affected builds |
| Onboarding | Smaller scope | Bigger picture |

**Pragmatic answer**: Monorepo with Turborepo for teams under 30. The instant feedback loop of changing a shared package and seeing effects in all consumers is worth the CI investment. Multi-repo when teams genuinely need full autonomy and will invest in internal package registry infrastructure.

---

## Staff-Level Discussion Topics

### Technical Strategy: Evaluating New Tools

Frame it as a decision matrix, not personal preference. Criteria:

1. **Problem severity**: How painful is the current solution? Quantify: developer hours lost, incidents caused, onboarding friction.
2. **Maturity**: GitHub stars mean nothing. Look at: release cadence, breaking change history, bus factor, corporate backing.
3. **Migration cost**: Not just rewriting code. Training, tooling changes, CI/CD updates, monitoring updates, documentation.
4. **Reversibility**: Can we adopt incrementally? Can we roll back? Strangler fig vs big-bang rewrite.
5. **Team alignment**: Does the team want this? Imposed tooling breeds resentment and poor adoption.

Write a one-page RFC. Include a "do nothing" option with concrete costs. Let the team comment async for a week, then decide.

### Platform Team Responsibilities

A platform team's mission is to make product engineers faster and safer. They own:

- **Shared libraries**: HTTP client with circuit breaking, structured logger, metrics SDK, auth middleware, error handling base classes
- **Service templates**: `create-service` CLI that scaffolds a new service with all the right defaults (linting, testing, CI, Dockerfile, observability)
- **Build system**: CI/CD pipeline templates, Docker base images, deployment automation
- **Observability stack**: Logging pipeline, metrics collection, distributed tracing, alerting rules
- **Developer environment**: Local development tooling, docker-compose setups, mock services
- **Standards and guardrails**: API design guidelines, code review checklists, security scanning, dependency update automation

What they do NOT own: business logic, feature decisions, or telling product teams how to structure their code. They provide paved roads, not mandates.

### Build vs Buy vs Open Source

| Factor | Build | Buy (SaaS) | Open Source |
|--------|-------|-------------|-------------|
| Core to business | Yes | No | Maybe |
| Competitive advantage | Yes | No | No |
| Maintenance budget | Have dedicated team | Want to minimize | Medium |
| Customization needs | High | Low | Medium-High |
| Time to market | Slow | Fast | Medium |
| Data sensitivity | Full control | Vendor risk | Full control |

**Framework**: If it's core to your business and a competitive advantage, build it. If it's table-stakes infrastructure (auth, email, payments), buy it. If it's technical infrastructure (database, message queue, monitoring), use open source.

### Rewrite Evaluation

Almost always push back. Rewrites fail more often than they succeed because:
- The old system encodes years of edge cases and bug fixes that aren't documented
- Rewriting takes 2-3x longer than estimated
- The business can't wait — you're maintaining two systems during the rewrite
- The new system will have its own bugs

**Instead**: Refactor incrementally. Strangler fig pattern. Extract one bounded context at a time. Keep the old system running until each piece is proven.

**Exception**: The rewrite is justified when the old system's technology is genuinely dead (no security patches, no maintainers, can't hire for it) AND the system is small enough to rewrite in under 3 months.

---

## Interview Questions

**Q: "Microservices vs monolith?"**

Start modular monolith. Extract when you can name at least two concrete criteria: independent scaling, independent deployment, tech divergence, team autonomy, fault isolation. If you're extracting because "microservices are best practice," you're optimizing for the wrong thing.

**Q: "How would you design an internal API platform for 20 product teams?"**

Layers: API Gateway (central entry point, handles auth, rate limiting, routing, observability), API standards (OpenAPI specs required, generated from code, automated breaking change detection in CI), SDK generation (generate TypeScript client SDKs from OpenAPI specs — teams consume services through typed SDKs, never raw HTTP), contract testing (Pact or similar, producer and consumer tests run in CI, breaking a contract blocks the PR).

**Q: "Our CI takes 45 minutes. How do you fix it?"**

Diagnose first. Parallelize lint, typecheck, and unit tests (they're independent). Cache `node_modules` (hash of `package-lock.json`), TypeScript incremental compilation (`.tsbuildinfo`), and Docker layers. Use Turborepo/Nx `affected` to only run tasks for changed packages. Shard test suites across multiple CI runners. Realistic target: 45 minutes down to 8-12 minutes with caching and parallelization.

**Q: "How would you migrate 15 repos into a monorepo?"**

This is a 3-6 month project. Phase 1: Foundation (choose Turborepo vs Nx, set up structure, configure CI, test with one service). Phase 2: Migrate repos one at a time starting with those that share the most code, use `git filter-repo` to preserve history. Phase 3: Extract shared code into packages. Phase 4: Remote caching, affected-only builds. Critical pitfall: CI/CD becomes the bottleneck — invest early in affected builds.

**Q: "A team wants to rewrite a service from scratch. How do you evaluate this?"**

Apply the strangler fig mindset. Ask: What edge cases are encoded in the existing system? How long will it realistically take? Can the business survive running two systems? Is the old technology actually dead (no security patches, can't hire)? Can we extract one bounded context at a time instead? The only valid case for a full rewrite is a system small enough to complete in under 3 months with genuinely dead technology.

## Related Reading

- **Modular monolith structure** uses the feature-based organization from [09 – Clean Architecture and DDD](./01-clean-architecture-and-ddd.md#project-structure-conventions) and the TypeScript project references described in [01 – Advanced Type Patterns](../01-typescript-advanced/02-advanced-type-patterns.md).
- **Microservices extraction criteria** require the independent scaling capabilities covered in [08 – Clustering and Scaling](../08-performance-scaling/02-clustering-and-scaling.md) and the stateless design principles in [08 – Caching and Redis](../08-performance-scaling/01-caching-and-redis.md#stateless-design-rule).
- **Inter-service communication (HTTP, gRPC, message queues)** builds on REST API design from [03 – HTTP Semantics and Status Codes](../03-rest-api-design/01-http-semantics-and-status-codes.md), the gRPC comparison in [08 – Clustering and Scaling](../08-performance-scaling/02-clustering-and-scaling.md#grpc-vs-rest-for-internal-services), and the event-driven patterns in [09 – Event-Driven and Async Patterns](./02-event-driven-and-async-patterns.md).
- **Vertical slice architecture** is an alternative to the layered approach in [09 – Clean Architecture and DDD](./01-clean-architecture-and-ddd.md#the-layers) — use it when feature independence matters more than shared domain logic.
- **Strangler fig pattern** uses the API versioning strategies from [03 – API Design Patterns and Versioning](../03-rest-api-design/03-api-design-patterns-and-versioning.md#api-versioning-strategies) to manage the migration surface.
- **Contract testing for inter-service APIs** is the quality gate described in [07 – Advanced Testing Patterns](../07-testing/03-advanced-testing-patterns.md#contract-testing-with-pact) — consumer-driven contracts prevent breaking changes across service boundaries.
- **Monorepo tooling (Turborepo, Nx)** manages the shared TypeScript code using the configuration patterns from [00 – TypeScript and Node.js Fundamentals](../00-ts-node-fundamentals.md) and the module resolution patterns from [02 – Threading and Process Management](../02-node-runtime/02-threading-and-process-management.md).
- **Platform team responsibilities** include maintaining the security middleware from [05 – Advanced Security and Secrets](../05-auth-security/03-advanced-security-and-secrets.md), the observability stack from [08 – Profiling and Advanced Performance](../08-performance-scaling/03-profiling-and-advanced-performance.md#opentelemetry-vendor-agnostic), and the database migration patterns from [06 – Advanced Patterns and Multi-Tenancy](../06-database-patterns/03-advanced-patterns-and-multi-tenancy.md).

## Practice Suggestions

1. **Build a modular monolith with enforced boundaries**: Create a Node.js application with 3 feature modules (e.g., orders, inventory, payments). Enforce boundaries using TypeScript project references so that modules can only communicate through explicitly exported interfaces. Verify that direct cross-module imports cause compilation errors.

2. **Implement an event-driven saga**: Build a 3-step order placement saga (reserve inventory, charge payment, create shipment) with compensating transactions. Implement both the orchestration pattern (central coordinator) and the choreography pattern (event-based). Intentionally fail the 2nd step and verify that the 1st step is compensated.

3. **Practice the strangler fig migration**: Take a simple Express CRUD API (the "legacy" system) and migrate one endpoint at a time to a new Fastify service. Use an HTTP proxy to route traffic between the two systems. Verify that the proxy transparently switches between old and new implementations.

4. **Extract a module into a separate service**: Starting from your modular monolith, identify one module to extract. Replace direct function calls with HTTP or message queue communication. Add contract tests (Pact) to verify the new service fulfills the same contract. Measure the latency impact of the extraction.

5. **Set up a monorepo with Turborepo**: Create a monorepo with an API app, a worker app, and shared packages (domain, database, config). Configure Turborepo for affected-only builds and remote caching. Verify that changing a shared package only rebuilds the consuming apps, and measure CI time savings versus a full rebuild.

6. **Design and write an RFC for a technical decision**: Pick a real decision (e.g., "should we adopt GraphQL for our new API?"). Write a one-page RFC with problem statement, options (including "do nothing"), trade-off analysis with concrete criteria (migration cost, team familiarity, performance implications), and a recommendation. Practice presenting it as you would in a staff-level architecture review.
