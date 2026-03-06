"""
Drill 03 — Feature Flag Service

Implement a FeatureFlagService class with global toggles,
user overrides, group rules, and snapshots.

────────────────────────────────────────
Level 1 — Global Flags

  enable(flag) -> None
    Enable a flag globally.

  disable(flag) -> None
    Disable a flag globally.

  is_enabled(flag) -> bool
    Returns whether the flag is enabled. Defaults to False.

────────────────────────────────────────
Level 2 — User Overrides

  enable_for_user(flag, user_id) -> None
    Enable a flag for a specific user.

  disable_for_user(flag, user_id) -> None
    Disable a flag for a specific user.

  is_enabled_for_user(flag, user_id) -> bool
    If user has an override for this flag, return the override.
    Otherwise fall back to the global state.

────────────────────────────────────────
Level 3 — Groups

  add_user_to_group(user_id, group) -> None
    Add a user to a group. A user can be in multiple groups.

  enable_for_group(flag, group) -> None
    Enable a flag for an entire group.

  disable_for_group(flag, group) -> None
    Disable a flag for an entire group.

  Resolution order for is_enabled_for_user:
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

  snapshot(name) -> None
    Save the entire current state under this name.
    Overwrites if the name already exists.

  restore(name) -> bool
    Restore state from the named snapshot.
    Returns False if the name does not exist.

  list_snapshots() -> list[str]
    Returns all snapshot names, sorted alphabetically.
"""

from __future__ import annotations


class FeatureFlagService:
    def __init__(self) -> None:
        # TODO: initialize your data structures
        pass

    def enable(self, flag: str) -> None:
        raise NotImplementedError("TODO: implement enable")

    def disable(self, flag: str) -> None:
        raise NotImplementedError("TODO: implement disable")

    def is_enabled(self, flag: str) -> bool:
        raise NotImplementedError("TODO: implement is_enabled")

    def enable_for_user(self, flag: str, user_id: str) -> None:
        raise NotImplementedError("TODO: implement enable_for_user")

    def disable_for_user(self, flag: str, user_id: str) -> None:
        raise NotImplementedError("TODO: implement disable_for_user")

    def is_enabled_for_user(self, flag: str, user_id: str) -> bool:
        raise NotImplementedError("TODO: implement is_enabled_for_user")

    def add_user_to_group(self, user_id: str, group: str) -> None:
        raise NotImplementedError("TODO: implement add_user_to_group")

    def enable_for_group(self, flag: str, group: str) -> None:
        raise NotImplementedError("TODO: implement enable_for_group")

    def disable_for_group(self, flag: str, group: str) -> None:
        raise NotImplementedError("TODO: implement disable_for_group")

    def snapshot(self, name: str) -> None:
        raise NotImplementedError("TODO: implement snapshot")

    def restore(self, name: str) -> bool:
        raise NotImplementedError("TODO: implement restore")

    def list_snapshots(self) -> list[str]:
        raise NotImplementedError("TODO: implement list_snapshots")


# ─── Self-Checks (do not edit below this line) ──────────────────


def _check(label: str, actual: object, expected: object) -> None:
    if actual == expected:
        return
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def _run_self_checks() -> None:
    # ── Level 1 ──
    f1 = FeatureFlagService()
    _check("L1 default off", f1.is_enabled("dark_mode"), False)
    f1.enable("dark_mode")
    _check("L1 enabled", f1.is_enabled("dark_mode"), True)
    f1.disable("dark_mode")
    _check("L1 disabled", f1.is_enabled("dark_mode"), False)

    # ── Level 2 ──
    f2 = FeatureFlagService()
    f2.enable("new_ui")
    f2.disable_for_user("new_ui", "user1")
    _check("L2 user override off", f2.is_enabled_for_user("new_ui", "user1"), False)
    _check("L2 fallback global", f2.is_enabled_for_user("new_ui", "user2"), True)
    f2.enable_for_user("new_ui", "user1")
    _check("L2 user override on", f2.is_enabled_for_user("new_ui", "user1"), True)

    # ── Level 3 ──
    f3 = FeatureFlagService()
    f3.add_user_to_group("alice", "beta")
    f3.add_user_to_group("alice", "staff")
    f3.enable_for_group("experiment", "beta")
    _check("L3 group enabled", f3.is_enabled_for_user("experiment", "alice"), True)
    _check("L3 not in group", f3.is_enabled_for_user("experiment", "bob"), False)
    f3.disable_for_user("experiment", "alice")
    _check("L3 user beats group", f3.is_enabled_for_user("experiment", "alice"), False)

    f3b = FeatureFlagService()
    f3b.enable("feature_x")
    f3b.add_user_to_group("carol", "internal")
    f3b.disable_for_group("feature_x", "internal")
    _check("L3 group off beats global", f3b.is_enabled_for_user("feature_x", "carol"), False)
    _check("L3 no group uses global", f3b.is_enabled_for_user("feature_x", "dave"), True)

    # ── Level 4 ──
    f4 = FeatureFlagService()
    f4.enable("flag_a")
    f4.enable("flag_b")
    f4.snapshot("v1")
    f4.disable("flag_a")
    _check("L4 after disable", f4.is_enabled("flag_a"), False)
    _check("L4 restore", f4.restore("v1"), True)
    _check("L4 restored", f4.is_enabled("flag_a"), True)
    _check("L4 other flag", f4.is_enabled("flag_b"), True)
    _check("L4 missing snapshot", f4.restore("nope"), False)
    _check("L4 list", f4.list_snapshots(), ["v1"])


def main() -> None:
    try:
        _run_self_checks()
    except NotImplementedError as e:
        print(str(e))
        return
    except (AssertionError, AssertionError) as e:
        print(f"FAIL: {e}")
        return

    print("All self-checks passed.")


if __name__ == "__main__":
    main()
