/*
Drill 03 — Feature Flag Service

Implement a FeatureFlagService class with global toggles,
user overrides, group rules, and snapshots.

────────────────────────────────────────
Level 1 — Global Flags

  enable(flag: string): void
    Enable a flag globally.

  disable(flag: string): void
    Disable a flag globally.

  isEnabled(flag: string): boolean
    Returns whether the flag is enabled. Defaults to false.

────────────────────────────────────────
Level 2 — User Overrides

  enableForUser(flag: string, userId: string): void
    Enable a flag for a specific user.

  disableForUser(flag: string, userId: string): void
    Disable a flag for a specific user.

  isEnabledForUser(flag: string, userId: string): boolean
    If user has an override for this flag, return the override.
    Otherwise fall back to the global state.

────────────────────────────────────────
Level 3 — Groups

  addUserToGroup(userId: string, group: string): void
    Add a user to a group. A user can be in multiple groups.

  enableForGroup(flag: string, group: string): void
    Enable a flag for an entire group.

  disableForGroup(flag: string, group: string): void
    Disable a flag for an entire group.

  Resolution order for isEnabledForUser:
    1. User override (highest priority)
    2. Group — if the user belongs to ANY group that has
       this flag enabled, the flag is enabled at group level.
       If all of the user's groups with a setting have it
       disabled, the flag is disabled at group level.
       Only applies when at least one of the user's groups
       has a setting for this flag.
    3. Global state (lowest priority)

────────────────────────────────────────
Level 4 — Snapshots

  snapshot(name: string): void
    Save the entire current state under this name.
    Overwrites if the name already exists.

  restore(name: string): boolean
    Restore state from the named snapshot.
    Returns false if the name does not exist.

  listSnapshots(): string[]
    Returns all snapshot names, sorted alphabetically.
*/

export class FeatureFlagService {
  constructor() {
    // TODO: initialize your data structures
  }

  enable(flag: string): void {
    throw new Error("TODO: implement enable");
  }

  disable(flag: string): void {
    throw new Error("TODO: implement disable");
  }

  isEnabled(flag: string): boolean {
    throw new Error("TODO: implement isEnabled");
  }

  enableForUser(flag: string, userId: string): void {
    throw new Error("TODO: implement enableForUser");
  }

  disableForUser(flag: string, userId: string): void {
    throw new Error("TODO: implement disableForUser");
  }

  isEnabledForUser(flag: string, userId: string): boolean {
    throw new Error("TODO: implement isEnabledForUser");
  }

  addUserToGroup(userId: string, group: string): void {
    throw new Error("TODO: implement addUserToGroup");
  }

  enableForGroup(flag: string, group: string): void {
    throw new Error("TODO: implement enableForGroup");
  }

  disableForGroup(flag: string, group: string): void {
    throw new Error("TODO: implement disableForGroup");
  }

  snapshot(name: string): void {
    throw new Error("TODO: implement snapshot");
  }

  restore(name: string): boolean {
    throw new Error("TODO: implement restore");
  }

  listSnapshots(): string[] {
    throw new Error("TODO: implement listSnapshots");
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
  const f1 = new FeatureFlagService();
  check("L1 default off", f1.isEnabled("dark_mode"), false);
  f1.enable("dark_mode");
  check("L1 enabled", f1.isEnabled("dark_mode"), true);
  f1.disable("dark_mode");
  check("L1 disabled", f1.isEnabled("dark_mode"), false);

  // ── Level 2 ──
  const f2 = new FeatureFlagService();
  f2.enable("new_ui");
  f2.disableForUser("new_ui", "user1");
  check("L2 user override off", f2.isEnabledForUser("new_ui", "user1"), false);
  check("L2 fallback global", f2.isEnabledForUser("new_ui", "user2"), true);
  f2.enableForUser("new_ui", "user1");
  check("L2 user override on", f2.isEnabledForUser("new_ui", "user1"), true);

  // ── Level 3 ──
  const f3 = new FeatureFlagService();
  f3.addUserToGroup("alice", "beta");
  f3.addUserToGroup("alice", "staff");
  f3.enableForGroup("experiment", "beta");
  check("L3 group enabled", f3.isEnabledForUser("experiment", "alice"), true);
  check("L3 not in group", f3.isEnabledForUser("experiment", "bob"), false);
  f3.disableForUser("experiment", "alice");
  check("L3 user beats group", f3.isEnabledForUser("experiment", "alice"), false);

  const f3b = new FeatureFlagService();
  f3b.enable("feature_x");
  f3b.addUserToGroup("carol", "internal");
  f3b.disableForGroup("feature_x", "internal");
  check("L3 group off beats global", f3b.isEnabledForUser("feature_x", "carol"), false);
  check("L3 no group uses global", f3b.isEnabledForUser("feature_x", "dave"), true);

  // ── Level 4 ──
  const f4 = new FeatureFlagService();
  f4.enable("flag_a");
  f4.enable("flag_b");
  f4.snapshot("v1");
  f4.disable("flag_a");
  check("L4 after disable", f4.isEnabled("flag_a"), false);
  check("L4 restore", f4.restore("v1"), true);
  check("L4 restored", f4.isEnabled("flag_a"), true);
  check("L4 other flag", f4.isEnabled("flag_b"), true);
  check("L4 missing snapshot", f4.restore("nope"), false);
  check("L4 list", f4.listSnapshots(), ["v1"]);
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
