"""Read-only input validator and deterministic numeric comparison producer."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("inputs", nargs="+")
    args = parser.parse_args()
    paths = tuple(Path(raw) for raw in args.inputs)
    for path in paths:
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"missing or empty plotting input: {path}")
    if args.output is not None:
        source = next(
            (path for path in paths if path.suffix.casefold() in {".csv", ".npy", ".npz"}),
            None,
        )
        if source is None:
            raise SystemExit("numeric redraw requires a CSV/NPY/NPZ input")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
