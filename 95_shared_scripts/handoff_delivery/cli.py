"""Thin command-line adapters over the tested handoff builder APIs."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Sequence

from .builder import (
    BaselineEntry,
    BaselineSnapshot,
    build_delivery,
    capture_baseline,
    compare_baseline,
)
from .lineage import validate_recipe_ledger
from .portable import load_field_consumer_registry, load_initial_state_recipes


BASELINE_COLUMNS = tuple(BaselineEntry.__dataclass_fields__)


def _write_baseline(path: Path, snapshot: BaselineSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=BASELINE_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(asdict(row) for row in snapshot.entries)


def _load_baseline(path: Path) -> BaselineSnapshot:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != BASELINE_COLUMNS:
                raise ValueError("baseline CSV header mismatch")
            rows = tuple(
                BaselineEntry(
                    relative_path=row["relative_path"],
                    path_type=row["path_type"],
                    size=int(row["size"]),
                    sha256=row["sha256"],
                    symlink_target=row["symlink_target"],
                )
                for row in reader
            )
    except (OSError, UnicodeError, ValueError, KeyError, csv.Error) as error:
        raise ValueError(f"cannot load baseline CSV: {path}") from error
    return BaselineSnapshot(rows)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m handoff_delivery")
    commands = parser.add_subparsers(dest="command", required=True)

    baseline = commands.add_parser("baseline")
    baseline.add_argument("--old", required=True, type=Path)
    baseline.add_argument("--output", required=True, type=Path)

    compare = commands.add_parser("compare-old")
    compare.add_argument("--old", required=True, type=Path)
    compare.add_argument("--baseline", required=True, type=Path)

    build = commands.add_parser("build")
    build.add_argument("--project-root", required=True, type=Path)
    build.add_argument("--old", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--dry-run", action="store_true")
    build.add_argument("--resume", action="store_true")

    verify = commands.add_parser("verify")
    verify.add_argument("--project-root", required=True, type=Path)
    verify.add_argument("--delivery", required=True, type=Path)

    recipes = commands.add_parser("validate-recipes")
    recipes.add_argument("--project-root", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one CLI command and return a process-style exit code."""
    args = _parser().parse_args(argv)
    try:
        if args.command == "baseline":
            _write_baseline(args.output, capture_baseline(args.old))
            return 0
        if args.command == "compare-old":
            difference = compare_baseline(args.old, _load_baseline(args.baseline))
            print(json.dumps(asdict(difference), sort_keys=True, ensure_ascii=False))
            return 0 if difference.is_clean else 1
        if args.command == "build":
            result = build_delivery(
                project_root=args.project_root,
                old_delivery=args.old,
                destination=args.output,
                dry_run=args.dry_run,
                resume=args.resume,
            )
            print(result.reason)
            return result.exit_code
        if args.command == "verify":
            verifier = args.delivery / "00_handoff/verify_delivery.py"
            metadata = verifier.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise ValueError(f"packaged verifier is not one regular file: {verifier}")
            environment = os.environ.copy()
            environment["PYTHONPATH"] = ""
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(verifier),
                    "--delivery",
                    str(args.delivery),
                    "--project-root",
                    str(args.project_root),
                ],
                env=environment,
                check=False,
            )
            return completed.returncode
        if args.command == "validate-recipes":
            ledger_root = args.project_root / "95_shared_scripts/handoff_delivery"
            figures = validate_recipe_ledger(args.project_root)
            recipes = load_initial_state_recipes(
                ledger_root / "initial_state_recipes.csv",
                project_root=args.project_root,
            )
            consumers = load_field_consumer_registry(
                ledger_root / "full_field_consumers.csv",
                project_root=args.project_root,
            )
            print(
                json.dumps(
                    {
                        "figures": len(figures),
                        "initial_state_recipes": len(recipes),
                        "full_field_consumers": len(consumers),
                    },
                    sort_keys=True,
                )
            )
            return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
