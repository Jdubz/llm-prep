# Module 07: Feature Flags and Database Migrations

## Feature Flags

### Platforms

| Platform | Type | Strengths |
|----------|------|-----------|
| LaunchDarkly | SaaS | Enterprise, SDKs for every language, strong targeting |
| Unleash | Open source / SaaS | Self-hostable, simple, good for startups |
| Flagsmith | Open source / SaaS | Feature flags + remote config, self-hostable |
| Split.io | SaaS | Strong experimentation/analytics integration |
| Flipt | Open source | GitOps-native, lightweight |

### Flag Types

**Release flags**: Gate new features behind a flag. Enable incrementally. Remove after full rollout.
```javascript
if (featureFlags.isEnabled('new-checkout-flow', user)) {
  return <NewCheckoutFlow />;
}
return <LegacyCheckoutFlow />;
```

**Operational flags**: Circuit breakers, graceful degradation. Long-lived.

**Experiment flags**: A/B tests. Route cohorts to different experiences for measurement.

**Permission flags**: Entitlement-based access. "Premium users get feature X."

### Flag Lifecycle and Technical Debt

```
Create -> Develop -> Test -> Roll Out (%) -> Fully On -> Remove Flag
                                                          ^
                                                    CRITICAL STEP
```

Stale flags cause dead code paths, testing combinatorial explosion (N flags = 2^N states), cognitive overhead, and risk of accidentally toggling forgotten flags. Mitigate with: expiration dates at creation, automated alerts when 100% on for >30 days, linting rules, quarterly cleanup sprints, mandatory ownership.

### Feature Flag Checklist

**Creating:** Descriptive name, documented purpose, assigned owner, expiration date, safe default (off = old behavior), fallback for flag service unavailability.

**Removing:** Flag 100% on/off >30 days, dead code paths deleted, tests updated, flag deleted from platform, PR approved.

---

## Database Migrations in CI/CD

### The Expand/Contract Pattern

**Phase 1 -- Expand** (backward-compatible changes only):
```sql
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
CREATE TABLE user_preferences (...);
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

**Phase 2 -- Migrate** (application uses both old and new schema):
```sql
UPDATE users SET email_verified = TRUE WHERE verified_at IS NOT NULL;
```

**Phase 3 -- Contract** (remove old schema in a subsequent deploy):
```sql
ALTER TABLE users DROP COLUMN verified_at;
```

**Order:** (1) Deploy expand migration, (2) Deploy new app code, (3) Verify stability, (4) Deploy contract migration.

### Backward Compatibility

Every migration must be compatible with both current and previous application versions.

**Safe operations (no expand/contract):** Adding nullable columns, adding tables, adding indexes (CONCURRENTLY), widening types (int -> bigint, varchar(50) -> varchar(100)).

**Dangerous operations (require expand/contract):** Renaming columns, removing columns, changing types, adding NOT NULL without defaults, splitting/merging tables.

### Migration Testing

- Run migrations against production-sized data (sanitized) in CI
- Test both up and down migrations
- Measure migration duration on production-sized data
- Use advisory locks to prevent concurrent migration execution
- Tools: Flyway, Liquibase, golang-migrate, Alembic, Prisma Migrate

---

## Secrets Management

### Never in Git

Non-negotiable. Secrets in git are compromised secrets, even if removed from HEAD (they remain in history). This includes: API keys, tokens, passwords, database connection strings, TLS private keys, OAuth secrets, encryption keys.

### Tools

**HashiCorp Vault:** Dynamic secrets (short-lived DB credentials on demand), encryption as a service, identity-based access (K8s service account, AWS IAM), audit logging.

**AWS Secrets Manager / Parameter Store:** Native AWS integration, automatic rotation for RDS credentials, cross-account sharing. Parameter Store is cheaper for simpler use cases.

**External Secrets Operator (Kubernetes):**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  data:
  - secretKey: password
    remoteRef:
      key: prod/database
      property: password
```

### Rotation Strategies

- **Automated rotation**: Secrets Manager rotates credentials on a schedule via Lambda
- **Dual credentials**: Application supports two simultaneously; rotate one while the other remains active
- **Short-lived tokens**: Prefer tokens that expire (JWT, STS) over long-lived credentials
- **Vault dynamic secrets**: Unique, short-lived credentials per consumer, automatically revoked

---

## Testing in Production

### Dark Launching

Deploy new code to production but do not expose it to users. Mirror real requests to the new code path and compare results -- the new system's responses are logged but never returned to users.

```python
async def get_recommendations(user_id: str):
    result = await legacy_recommendation_service.get(user_id)

    if feature_flags.is_enabled('dark-launch-new-recs'):
        asyncio.create_task(
            dark_launch_new_recommendations(user_id, expected=result)
        )

    return result  # always returns legacy result

async def dark_launch_new_recommendations(user_id, expected):
    try:
        actual = await new_recommendation_service.get(user_id)
        metrics.record_comparison(expected, actual)
    except Exception as e:
        logger.warning(f"Dark launch error: {e}")
        # Never affects the user
```

### Shadow Traffic

Route a copy of production traffic to a shadow service via Istio traffic mirroring. Shadow responses are discarded. Caution: doubles your load (account in capacity planning), ensure shadow does not write to production databases or send real notifications.

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
spec:
  http:
  - route:
    - destination:
        host: my-service-v1
    mirror:
      host: my-service-v2
    mirrorPercentage:
      value: 100.0
```

### Chaos Engineering Integration

Integrate chaos experiments into CI/CD for continuous resilience verification. Progressive approach:

1. **Game days**: Scheduled, manual chaos experiments with the team watching
2. **Automated experiments**: Run in staging as part of CI/CD, verify SLOs held during chaos
3. **Continuous chaos in production**: Netflix-style random failures, with kill switches

---

## Interview Questions

**Q: How do you handle database migrations during a canary deployment?**

A: All schema changes must be backward-compatible (expand/contract). Run migrations before deploying the canary -- the stable version must tolerate the new schema. Never drop columns while both versions run. The contract phase happens only after 100% rollout and stabilization.

**Q: Your codebase has 200 feature flags, many stale. How do you address this?**

A: Audit for flags 100% on/off for >30 days. Assign owners. Enforce expiration dates with platform alerts. Lint rules for stale references. Quarterly cleanup sprints. Cap active flags per team to force cleanup before creating new ones.

**Q: How would you design secrets management for a Kubernetes-based platform?**

A: Central store (Vault or AWS Secrets Manager) as source of truth. External Secrets Operator syncs into K8s Secrets. Per-service access control via Vault policies or IAM. Automated rotation with credential refresh. Audit logging. Developers never see production secrets. ExternalSecret manifests reference secrets by path, not value.

### Related Reading

- [Module 07: Pipeline Design and Deployment Strategies](01-pipeline-design-and-deployment-strategies.md) -- feature flags work alongside deployment strategies (canary, blue-green) to control risk during rollouts
- [Module 07: Infrastructure and GitOps](03-infrastructure-and-gitops.md) -- secrets management with Vault and External Secrets Operator, and GitOps workflows for managing configuration changes
- [Module 02: Database Platforms and Scaling](../02-databases-at-scale/03-database-platforms-and-scaling.md) -- PostgreSQL migration tooling, advisory locks for preventing concurrent migrations, and database-specific schema change considerations
- [Module 06: Kubernetes Core and Operations](../06-containers-orchestration/02-kubernetes-core-and-operations.md) -- running database migrations as Kubernetes Jobs or init containers before deployment rollout
- [Module 08: SLOs, Alerting, and Incident Response](../08-observability/02-slos-alerting-and-incident-response.md) -- feature flag rollouts should be monitored against SLOs; error budget consumption during a rollout signals when to halt
- [Module 09: Authentication and Authorization](../09-security/01-authentication-and-authorization.md) -- secrets management (Vault, AWS Secrets Manager) and rotation strategies for database credentials and API keys

### Key Takeaways

1. **Database migrations require discipline**: Expand/contract is the only way to achieve zero-downtime schema changes.
2. **Feature flags are powerful but require hygiene**: Every flag needs an owner and an expiration date.
3. **Secrets management is a system, not a tool**: Rotation, access control, auditing, and developer experience all matter.
4. **Testing in production is not reckless when done right**: Dark launching and shadow traffic validate with real workloads while keeping users safe.
