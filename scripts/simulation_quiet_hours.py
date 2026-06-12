#!/usr/bin/env python3
"""Singapore quiet-hour policy for long-running Mumax3 simulations."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


SINGAPORE = ZoneInfo("Asia/Singapore")
QUIET_START_HOUR = 23
QUIET_END_HOUR = 3
GRACE_END_MINUTE = 30


def _singapore(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=SINGAPORE)
    return value.astimezone(SINGAPORE)


def start_allowed(now: datetime) -> bool:
    """Return whether a new simulation may start at ``now``."""
    local = _singapore(now)
    return QUIET_END_HOUR <= local.hour < QUIET_START_HOUR


def running_action(
    now: datetime,
    started_at: datetime,
    estimated_finish: datetime | None,
) -> str:
    """Return ``continue`` or ``pause`` for an already-running case."""
    local_now = _singapore(now)
    local_started = _singapore(started_at)
    if start_allowed(local_now):
        return "continue"

    grace_start = local_now.replace(
        hour=QUIET_START_HOUR, minute=0, second=0, microsecond=0
    )
    grace_end = grace_start.replace(minute=GRACE_END_MINUTE)
    inside_grace = grace_start <= local_now < grace_end
    if not inside_grace or local_started >= grace_start or estimated_finish is None:
        return "pause"
    return "continue" if _singapore(estimated_finish) <= grace_end else "pause"


def estimate_finish(
    started_at: datetime,
    now: datetime,
    current_simulation_s: float,
    target_simulation_s: float,
) -> datetime | None:
    """Estimate completion from elapsed wall time and simulated-time progress."""
    if current_simulation_s <= 0 or target_simulation_s <= 0:
        return None
    if current_simulation_s >= target_simulation_s:
        return now
    elapsed = (_singapore(now) - _singapore(started_at)).total_seconds()
    if elapsed <= 0:
        return None
    remaining_wall_s = elapsed * (
        target_simulation_s - current_simulation_s
    ) / current_simulation_s
    return _singapore(now) + timedelta(seconds=remaining_wall_s)


def seconds_until_start_allowed(now: datetime) -> int:
    """Return seconds until the next 03:00 Singapore start boundary."""
    local = _singapore(now)
    if start_allowed(local):
        return 0
    if local.hour < QUIET_END_HOUR:
        boundary = local.replace(
            hour=QUIET_END_HOUR, minute=0, second=0, microsecond=0
        )
    else:
        boundary = (
            local + timedelta(days=1)
        ).replace(hour=QUIET_END_HOUR, minute=0, second=0, microsecond=0)
    return max(0, int((boundary - local).total_seconds()))


def target_seconds_from_mx3(path: Path) -> float | None:
    """Sum simple numeric ``run(...)`` durations; Relax-only files return None."""
    text = path.read_text(encoding="utf-8")
    values = re.findall(r"(?m)^\s*run\(\s*([0-9.eE+-]+)\s*\)", text)
    if not values:
        return None
    return sum(float(value) for value in values)


def table_last_time_s(path: Path) -> float | None:
    """Read the last numeric time from a Mumax table without loading the file."""
    if not path.is_file():
        return None
    with path.open("rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - 8192))
        lines = handle.read().decode("utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        if not line or line.startswith("#"):
            continue
        try:
            return float(line.split()[0])
        except (IndexError, ValueError):
            continue
    return None


def _parse_datetime(value: str) -> datetime:
    return _singapore(datetime.fromisoformat(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start-action")
    start_parser.add_argument("--now")

    running_parser = subparsers.add_parser("running-action")
    running_parser.add_argument("--started", required=True)
    running_parser.add_argument("--mx3", type=Path, required=True)
    running_parser.add_argument("--table", type=Path, required=True)
    running_parser.add_argument("--now")

    wait_parser = subparsers.add_parser("seconds-until-start")
    wait_parser.add_argument("--now")

    args = parser.parse_args()
    now = _parse_datetime(args.now) if args.now else datetime.now(SINGAPORE)
    if args.command == "start-action":
        print("start" if start_allowed(now) else "wait")
        return
    if args.command == "seconds-until-start":
        print(seconds_until_start_allowed(now))
        return

    started = _parse_datetime(args.started)
    target = target_seconds_from_mx3(args.mx3)
    current = table_last_time_s(args.table)
    finish = (
        estimate_finish(started, now, current, target)
        if current is not None and target is not None
        else None
    )
    print(running_action(now, started, finish))


if __name__ == "__main__":
    main()
