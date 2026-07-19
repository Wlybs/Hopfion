"""Generate one unique, human-readable anchor for each excluded parent data ID."""

from __future__ import annotations

from pathlib import Path


PARENT_DATA_IDS = (
    "data-centered-background-table", "data-frequency-switch-v3-tables",
    "data-ku-critical-sweep-tables", "data-plane-frequency-sweep-tables",
    "data-point-source-sweep-tables", "data-ref-amplitude-sweep-field-series",
    "data-ref-direction-selectivity-field-series", "data-ref-ku-critical-field-series",
    "data-ref-mode-map-four-field-series", "data-ref-multisource-baseline-field-series",
    "data-ref-qh1-p1q1-field", "data-ref-qh2-p1q2-field",
    "data-ref-qh2-p2q1-field", "data-ref-qh4-p2q2-field",
    "data-ref-size-convergence-field-series", "data-ref-srcx-frequency-field-series",
    "data-ref-srcx1000-field-series", "data-ref-srcx200-field-series",
    "data-ref-srcz-frequency-field-series", "data-ref-srcz100-field-series",
    "data-ref-srcz1100-field-series", "data-ringdown-table-series",
)


def generate(root: Path) -> tuple[Path, ...]:
    root.mkdir(parents=True, exist_ok=True)
    outputs = []
    for data_id in PARENT_DATA_IDS:
        path = root / f"{data_id}.txt"
        path.write_text(
            f"data_id={data_id}\n"
            "status=provenance_anchor_only\n"
            "complete_field_in_delivery=false\n"
            "resolution=See FIGURE_MANIFEST.csv, RUN_MANIFEST.csv, "
            "FULL_FIELD_CONSUMERS.csv, and REQUIRED_ASSETS.csv for exact source paths "
            "and exclusion status. No OVF or complete vector field is embedded here.\n",
            encoding="utf-8",
        )
        outputs.append(path)
    return tuple(outputs)


if __name__ == "__main__":
    generate(Path(__file__).with_name("figure_data") / "provenance")
