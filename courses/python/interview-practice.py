"""
Live Interview Practice (45 min): Data Workflow Fundamentals

Audience:
- Teams that use TypeScript, Python, and Go
- Interview focus: fundamentals, workflow, and communication (not language trivia)

Format simulation:
- You get a dataset and must explore, transform, and interpret it.
- Deliver a runnable solution in a time-boxed environment (CoderPad style).

How to use this file:
1) Start a 45-minute timer.
2) Implement TODOs only (no external dependencies; stdlib only).
3) Run: python interview-practice.py
4) Use printed output to explain your decisions and tradeoffs out loud.

Suggested pacing:
- 0-5 min: clarify assumptions and sketch approach
- 5-25 min: implement normalization + aggregation
- 25-35 min: implement interpretation/report
- 35-45 min: edge cases + polish + verbal walkthrough
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any
from collections import defaultdict

# ---------------------------------------------------------------------------
# DATASET (simulates what an interviewer might paste into CoderPad)
# ---------------------------------------------------------------------------

RAW_EVENTS: list[dict[str, Any]] = [
	{"event_id": "e1", "team": "search", "language": "python", "status": "ok", "duration_ms": "120", "items": "30", "timestamp_ms": "1710000001000"},
	{"event_id": "e2", "team": "search", "language": "go", "status": "ok", "duration_ms": "80", "items": "28", "timestamp_ms": "1710000002000"},
	{"event_id": "e3", "team": "search", "language": "typescript", "status": "error", "duration_ms": "350", "items": "0", "timestamp_ms": "1710000004000"},
	{"event_id": "e4", "team": "ads", "language": "python", "status": "ok", "duration_ms": "900", "items": "120", "timestamp_ms": "1710000005000"},
	{"event_id": "e5", "team": "ads", "language": "go", "status": "error", "duration_ms": "1100", "items": "0", "timestamp_ms": "1710000006000"},
	{"event_id": "e6", "team": "ads", "language": "go", "status": "ok", "duration_ms": "700", "items": "95", "timestamp_ms": "1710000008000"},
	{"event_id": "e7", "team": "infra", "language": "go", "status": "ok", "duration_ms": "60", "items": "10", "timestamp_ms": "1710000009000"},
	{"event_id": "e8", "team": "infra", "language": "python", "status": "ok", "duration_ms": "55", "items": "11", "timestamp_ms": "1710000010000"},
	{"event_id": "e9", "team": "infra", "language": "typescript", "status": "ok", "duration_ms": "70", "items": "9", "timestamp_ms": "1710000011000"},
	{"event_id": "e10", "team": "search", "language": "python", "status": "ok", "duration_ms": "100", "items": "31", "timestamp_ms": "1710000012000"},
	{"event_id": "e11", "team": "search", "language": "java", "status": "ok", "duration_ms": "95", "items": "27", "timestamp_ms": "1710000013000"},
	{"event_id": "e12", "team": "ads", "language": "typescript", "status": "ok", "duration_ms": "1300", "items": "140", "timestamp_ms": "1710000014000"},
	{"event_id": "e13", "team": "ads", "language": "python", "status": "error", "duration_ms": "1500", "items": "0", "timestamp_ms": "1710000015000"},
	# Intentionally noisy/bad rows to force data-quality handling:
	{"event_id": "e14", "team": "infra", "language": "go", "status": "ok", "duration_ms": "-1", "items": "7", "timestamp_ms": "1710000016000"},
	{"event_id": "e15", "team": "search", "language": "ruby", "status": "ok", "duration_ms": "88", "items": "25", "timestamp_ms": "1710000017000"},
	{"event_id": "e16", "team": "ads", "language": "go", "status": "unknown", "duration_ms": "500", "items": "60", "timestamp_ms": "1710000018000"},
	{"event_id": "e17", "team": "search", "language": "python", "status": "ok", "duration_ms": "not-a-number", "items": "20", "timestamp_ms": "1710000019000"},
	{"event_id": "e18", "team": "infra", "language": "python", "status": "ok", "duration_ms": "65", "items": "8", "timestamp_ms": None},
]


ALLOWED_LANGUAGES = {"python", "go", "typescript", "javascript", "java"}
ALLOWED_STATUS = {"ok", "error"}


@dataclass(frozen=True)
class Event:
	event_id: str
	team: str
	language: str
	status: str
	duration_ms: int
	items: int
	timestamp_ms: int


# ---------------------------------------------------------------------------
# INTERVIEW TASK
# ---------------------------------------------------------------------------
# Implement the functions below.
#
# Requirements:
# 1) normalize_events
#    - Convert valid RAW_EVENTS rows into Event objects.
#    - Skip invalid rows.
#    - A row is invalid if:
#      * missing required key
#      * language not in ALLOWED_LANGUAGES
#      * status not in ALLOWED_STATUS
#      * duration_ms/items/timestamp_ms are non-integer or negative
#
# 2) summarize_by_team
#    Return:
#      {
#        team_name: {
#          "total": int,
#          "ok": int,
#          "error": int,
#          "success_rate": float,      # ok / total
#          "p50_duration_ms": int,
#          "p95_duration_ms": int,
#          "throughput_items_per_s": float,  # total_items / total_duration_seconds
#        },
#        ...
#      }
#
#    Percentile rule for this exercise:
#      - sort durations ascending
#      - index = ceil(p * n) - 1
#      - clamp index to [0, n-1]
#
# 3) detect_anomalies
#    Return a list of human-readable strings.
#    Flag a team if:
#      - error rate > 0.20 OR
#      - p95_duration_ms >= 1200
#
# 4) build_report
#    Return a deterministic multi-line string sorted by team name, then anomalies.
#
# Notes for interview communication:
# - State assumptions explicitly.
# - Keep solution incremental and runnable.
# - Prefer readability over cleverness.


def normalize_events(rows: list[dict[str, Any]]) -> list[Event]:
  valid_events = []
  for row in rows:
    try:
      event_id = row["event_id"]
      team = row["team"]
      language = row["language"].lower()
      status = row["status"].lower()
      duration_ms = int(row["duration_ms"])
      items = int(row["items"])
      timestamp_ms = int(row["timestamp_ms"])

      if language not in ALLOWED_LANGUAGES:
        continue
      if status not in ALLOWED_STATUS:
        continue
      if duration_ms < 0 or items < 0 or timestamp_ms < 0:
        continue

      event = Event(
        event_id=event_id,
        team=team,
        language=language,
        status=status,
        duration_ms=duration_ms,
        items=items,
        timestamp_ms=timestamp_ms,
      )
      valid_events.append(event)
    except (KeyError, ValueError, TypeError):
      continue

  return valid_events


def percentile(values: list[int], p: float) -> int:
	"""Compute percentile using the exercise rule described above."""
	if not values:
		return 0

	ordered = sorted(values)
	idx = ceil(p * len(ordered)) - 1
	idx = max(0, min(idx, len(ordered) - 1))
	return ordered[idx]


def summarize_by_team(events: list[Event]) -> dict[str, dict[str, float | int]]:
  team_groups = defaultdict(list)
  for event in events:
    key = event.team
    team_groups[key].append(event)
	
  team_metrics = {}
  for team, events in team_groups.items():
    total = len(events)
    ok = sum(1 for e in events if e.status == "ok")
    error = sum(1 for e in events if e.status == "error")
    success_rate = ok / total if total > 0 else 0.0
    durations = [e.duration_ms for e in events]
    p50_duration_ms = percentile(durations, 0.5)
    p95_duration_ms = percentile(durations, 0.95)
    total_items = sum(e.items for e in events)
    total_duration_seconds = sum(e.duration_ms for e in events) / 1000
    throughput_items_per_s = total_items / total_duration_seconds if total_duration_seconds > 0 else 0.0

    team_metrics[team] = {
      "total": total,
      "ok": ok,
      "error": error,
      "success_rate": success_rate,
      "p50_duration_ms": p50_duration_ms,
      "p95_duration_ms": p95_duration_ms,
      "throughput_items_per_s": throughput_items_per_s,
    }

  return team_metrics

def detect_anomalies(summary: dict[str, dict[str, float | int]]) -> list[str]:
  anomalies = []
  for team, metrics in summary.items():
    if metrics["error"] / metrics["total"] > 0.20:
      anomalies.append(f"High error rate for team {team.upper()}")
    if metrics["p95_duration_ms"] >= 1200:
      anomalies.append(f"High p95 duration for team {team.upper()}")

  return anomalies


def build_report(summary: dict[str, dict[str, float | int]], anomalies: list[str]) -> str:
  lines = []
  for team in sorted(summary.keys()):
    metrics = summary[team]
    lines.append(f"TEAM {team.upper()}:")
    lines.append(f"  Total Events: {metrics['total']}")
    lines.append(f"  Success Rate: {metrics['success_rate']:.2%}")
    lines.append(f"  P50 Duration (ms): {metrics['p50_duration_ms']}")
    lines.append(f"  P95 Duration (ms): {metrics['p95_duration_ms']}")
    lines.append(f"  Throughput (items/s): {metrics['throughput_items_per_s']:.2f}")
    lines.append("")

  if anomalies:
    lines.append("ANOMALIES:")
    for anomaly in anomalies:
      lines.append(f"- {anomaly}")

  return "\n".join(lines)
  

# ---------------------------------------------------------------------------
# SELF-CHECK HARNESS
# ---------------------------------------------------------------------------
# These checks validate shape + core behavior while still leaving room for
# your implementation style.


def _run_self_checks() -> None:
	events = normalize_events(RAW_EVENTS)
	summary = summarize_by_team(events)
	anomalies = detect_anomalies(summary)
	report = build_report(summary, anomalies)

	assert isinstance(events, list)
	assert all(isinstance(e, Event) for e in events)
	assert len(events) == 13, "Expected 13 valid rows after filtering noisy data"

	assert set(summary.keys()) == {"ads", "infra", "search"}

	search = summary["search"]
	infra = summary["infra"]
	ads = summary["ads"]

	assert search["total"] == 5
	assert infra["total"] == 3
	assert ads["total"] == 5

	assert round(float(search["success_rate"]), 2) == 0.80
	assert round(float(infra["success_rate"]), 2) == 1.00
	assert round(float(ads["success_rate"]), 2) == 0.60

	assert int(search["p50_duration_ms"]) == 100
	assert int(infra["p95_duration_ms"]) == 70
	assert int(ads["p95_duration_ms"]) == 1500

	assert any("ads" in finding.lower() for finding in anomalies)

	assert isinstance(report, str)
	assert "TEAM ADS" in report
	assert "ANOMALIES" in report


def _print_prompt() -> None:
	print("=" * 70)
	print("MOCK LIVE INTERVIEW (45 min) — DATA WORKFLOW")
	print("=" * 70)
	print("Scenario:")
	print("A platform team (TypeScript/Python/Go) wants reliability insights")
	print("from mixed-language job events. Build a clean, runnable analysis.")
	print()
	print("Deliverables:")
	print("1) normalization with data-quality filtering")
	print("2) team-level metrics")
	print("3) anomaly detection")
	print("4) concise report output")
	print()
	print("Run after implementation: python interview-practice.py")
	print("=" * 70)


def main() -> None:
	_print_prompt()

	try:
		_run_self_checks()
	except NotImplementedError as error:
		print("\nTODOs remaining:")
		print(f"- {error}")
		print("\nTip: implement one function at a time and keep it runnable.")
		return
	except AssertionError as error:
		print("\nSelf-check failed:")
		print(f"- {error}")
		print("\nContinue iterating; this mirrors interview feedback loops.")
		return

	events = normalize_events(RAW_EVENTS)
	summary = summarize_by_team(events)
	anomalies = detect_anomalies(summary)
	report = build_report(summary, anomalies)

	print("\nAll self-checks passed. Final report:\n")
	print(report)


if __name__ == "__main__":
	main()
