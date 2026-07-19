"""Canonical production manifests and redraw recipes for the real Hopfion handoff."""

from __future__ import annotations

import csv
from dataclasses import asdict
from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from .lineage import FigureRecipe, ManifestKeys
from .models import IdList
from .portable import PortableContract
from .provenance_records import PARENT_DATA_IDS
from .redraw import RedrawRecipe
from .source_specs import RequiredAssetInventory, RequiredAssetRow
from .verifier import (
    DATA_COLUMNS, DOCUMENT_COLUMNS, REQUIRED_COLUMNS, RUN_COLUMNS, TOPIC_COLUMNS,
    package_figure_recipes,
)


REGISTRY_SOURCE = "95_shared_scripts/handoff_delivery/document_registry.md"
VALIDATOR_SOURCE = "95_shared_scripts/handoff_delivery/validate_plot_inputs.py"
REFERENCE_IDS = {
    "fig-formal-3-4-drift-10ns": "data-reference-module01-drift",
    "fig-formal-4-1-direction-selectivity": "data-reference-module02-direction",
    "fig-current-energy-audit-spectrum": "data-reference-module03-energy",
}

DATA_SOURCES: dict[str, str] = {
    "data-fig3-1-qh1-mesh": "95_shared_scripts/handoff_delivery/figure_data/fig3_1_qh1_mesh.csv",
    "data-fig3-1-qh2-p2q1-mesh": "95_shared_scripts/handoff_delivery/figure_data/fig3_1_qh2_p2q1_mesh.csv",
    "data-fig3-1-qh2-p1q2-mesh": "95_shared_scripts/handoff_delivery/figure_data/fig3_1_qh2_p1q2_mesh.csv",
    "data-fig3-1-qh4-mesh": "95_shared_scripts/handoff_delivery/figure_data/fig3_1_qh4_mesh.csv",
    "data-drift10ns-centroid-csv": "09_paper_thesis_talks/bishe/thesis_v2/figures/drift10ns_centroid_bg_mx_axis_x.csv",
    "data-centered-stability-ku0-csv": "09_paper_thesis_talks/bishe/thesis_v2/figures/centered_stability_Ku0.csv",
    "data-centered-stability-ku10k-csv": "09_paper_thesis_talks/bishe/thesis_v2/figures/centered_stability_Ku10k.csv",
    "data-centered-stability-ku50k-csv": "09_paper_thesis_talks/bishe/thesis_v2/figures/centered_stability_Ku50k.csv",
    "data-centered-qh-timeseries-npy": "95_shared_scripts/handoff_delivery/figure_data/centered_qh_timeseries.csv",
    "data-ku-survival-summary": "04_frustrated_fm_foundation/20260105_frustrated_fm/anisotropy_study/ku_critical_sweep/results/survival_table.txt",
    "data-anisotropy-rr-time-csv": "09_paper_thesis_talks/bishe/thesis_v2/figures/anisotropy_Rr_vs_time.csv",
    "data-size-convergence-cache-csv": "09_paper_thesis_talks/bishe/thesis_v2/figures/size_convergence_cache.csv",
    "data-point-source-frequency-summary": "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/point_source/results/point_source_summary.txt",
    "data-direction-srcx-vibx-centroid": "95_shared_scripts/handoff_delivery/figure_data/direction_srcX_vibX_centroid.csv",
    "data-direction-srcx-vibz-centroid": "95_shared_scripts/handoff_delivery/figure_data/direction_srcX_vibZ_centroid.csv",
    "data-direction-srcy-vibx-centroid": "95_shared_scripts/handoff_delivery/figure_data/direction_srcY_vibX_centroid.csv",
    "data-direction-srcz-vibx-centroid": "95_shared_scripts/handoff_delivery/figure_data/direction_srcZ_vibX_centroid.csv",
    "data-direction-srcz-vibz-centroid": "95_shared_scripts/handoff_delivery/figure_data/direction_srcZ_vibZ_centroid.csv",
    "data-srcx-displacement-cache-csv": "09_paper_thesis_talks/bishe/thesis_v2/figures/fig5-3_srcX_cache.csv",
    "data-srcz-trajectory-cache-csv": "09_paper_thesis_talks/bishe/thesis_v2/figures/fig5-3_srcZ_cache.csv",
    "data-amplitude-trajectory-cache-csv": "09_paper_thesis_talks/bishe/thesis_v2/figures/fig5-6_amplitude_cache.csv",
    "data-multisource-baseline-cache-csv": "09_paper_thesis_talks/bishe/thesis_v2/figures/fig5-7_baseline_cache.csv",
    "data-frequency-switch-v3-series": "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/multisource_control/bidirectional_z/freq_switch_bidirectional_v3.out/table.txt",
    "data-ringdown-power-spectra": "06_eigenmode_frequency_mechanism/hopfion_eigenmode_ringdown_20260608/results/ringdown_power_spectra.csv",
    "data-ringdown-drive-comparison": "06_eigenmode_frequency_mechanism/hopfion_eigenmode_ringdown_20260608/results/drive_vs_ringdown_comparison.csv",
    "data-energy-audit-records-csv": "06_eigenmode_frequency_mechanism/hopfion_energy_absorption_audit_20260608/results/energy_absorption_audit_records.csv",
    "data-energy-audit-window-sensitivity-csv": "06_eigenmode_frequency_mechanism/hopfion_energy_absorption_audit_20260608/results/energy_absorption_window_sensitivity.csv",
    "data-mode-map-deformation-timeseries-csv": "06_eigenmode_frequency_mechanism/hopfion_mode_map_20260608/results/deformation_timeseries.csv",
    "data-mode-map-summary-csv": "06_eigenmode_frequency_mechanism/hopfion_mode_map_20260608/results/mode_map_summary.csv",
    "data-mode-map-srcx1000-projections-npz": "95_shared_scripts/handoff_delivery/figure_data/mode_map_srcx1000_projections.csv",
    "data-mode-map-srcx200-projections-npz": "95_shared_scripts/handoff_delivery/figure_data/mode_map_srcx200_projections.csv",
    "data-mode-map-srcz100-projections-npz": "95_shared_scripts/handoff_delivery/figure_data/mode_map_srcz100_projections.csv",
    "data-mode-map-srcz1100-projections-npz": "95_shared_scripts/handoff_delivery/figure_data/mode_map_srcz1100_projections.csv",
    "data-legacy-energy-spectrum": "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/energy_absorption/energy_absorption_summary.txt",
    "data-srcx-frequency-displacement-summary": "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/srcX/results/motion_mode_summary.txt",
    "data-srcx-motion-classification-summary": "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/srcX/results/motion_mode_summary_05ns.txt",
    "data-srcz-direction-summary": "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/srcZ/results/motion_summary_srcZ.txt",
    "data-srcz-frequency-response-summary": "95_shared_scripts/handoff_delivery/figure_data/srcz_frequency_response_summary.txt",
    "data-reference-module01-drift": "95_shared_scripts/handoff_delivery/figure_data/reference_module01_drift.csv",
    "data-reference-module02-direction": "95_shared_scripts/handoff_delivery/figure_data/reference_module02_direction.csv",
    "data-reference-module03-energy": "95_shared_scripts/handoff_delivery/figure_data/reference_module03_energy.csv",
}
DATA_SOURCES.update({
    data_id: f"95_shared_scripts/handoff_delivery/figure_data/provenance/{data_id}.txt"
    for data_id in PARENT_DATA_IDS
})


def _csv_bytes(columns: Sequence[str], rows: Sequence[Mapping[str, object]]) -> bytes:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _copied(inventory: RequiredAssetInventory) -> dict[str, RequiredAssetRow]:
    return {row.source_path: row for row in inventory.rows if row.target_path is not None}


def data_paths(inventory: RequiredAssetInventory, figures: Sequence[FigureRecipe]) -> dict[str, str]:
    copied = _copied(inventory)
    ids = {
        item
        for figure in figures
        for raw in (figure.input_data_ids, figure.parent_data_ids)
        for item in (() if raw == "N/A" else IdList.parse(raw).items)
    } | set(REFERENCE_IDS.values())
    registry_target = copied[REGISTRY_SOURCE].target_path
    assert registry_target is not None
    result: dict[str, str] = {}
    for data_id in ids:
        source = DATA_SOURCES.get(data_id)
        if source is None:
            result[data_id] = registry_target
        else:
            row = copied.get(source)
            if row is None or row.target_path is None:
                raise RuntimeError(f"production data source is not copied: {data_id}:{source}")
            result[data_id] = row.target_path
    return result


def manifest_keys(
    inventory: RequiredAssetInventory,
    figures: Sequence[FigureRecipe],
    contract: PortableContract,
) -> ManifestKeys:
    paths = data_paths(inventory, figures)
    figure_runs = {
        item for figure in figures if figure.run_ids != "N/A"
        for item in IdList.parse(figure.run_ids).items
    }
    documents = {
        item for figure in figures if figure.source_document_ids != "N/A"
        for item in IdList.parse(figure.source_document_ids).items
    }
    return ManifestKeys(
        data_ids=frozenset(paths),
        run_ids=frozenset(figure_runs | {run.run_id for run in contract.runs}),
        theory_asset_ids=frozenset({"asset-hopfion-analytic-texture-generator"}),
        initial_state_recipe_ids=frozenset(recipe.recipe_id for recipe in contract.recipes),
        document_ids=frozenset(documents),
        data_paths=paths,
    )


def redraw_recipes(
    inventory: RequiredAssetInventory,
    figures: Sequence[FigureRecipe],
    keys: ManifestKeys,
) -> tuple[RedrawRecipe, ...]:
    copied = _copied(inventory)
    validator = copied[VALIDATOR_SOURCE].target_path
    assert validator is not None
    figure_targets = {source: row.target_path for source, row in copied.items()}
    recipes: list[RedrawRecipe] = []
    for figure in figures:
        if figure.usage_status not in {"formal", "current_only"}:
            continue
        input_ids = () if figure.input_data_ids == "N/A" else IdList.parse(figure.input_data_ids).items
        inputs = tuple(keys.data_paths[data_id] for data_id in input_ids)
        reference_id = REFERENCE_IDS.get(figure.figure_id)
        if reference_id is None:
            figure_target = figure_targets[figure.figure_path]
            assert figure_target is not None
            command_inputs = (*inputs, figure_target)
            recipes.append(RedrawRecipe(
                redraw_id=f"redraw-{figure.figure_id}", figure_id=figure.figure_id,
                module=figure.story_module, script_path=validator,
                command=" ".join(("/usr/bin/python3", validator, *command_inputs)),
                input_data_ids=figure.input_data_ids, input_paths=";".join(command_inputs),
                output_path="N/A", reference_product_path="N/A",
                comparison_method="input_hash_validation", tolerance="exact",
                environment_command="/usr/bin/python3", representative=False,
                notes="Read-only validation of every declared input and the accepted figure asset.",
            ))
            continue
        output = f"shared/redraw_products/{figure.story_module}.csv"
        reference = keys.data_paths[reference_id]
        recipes.append(RedrawRecipe(
            redraw_id=f"redraw-{figure.figure_id}", figure_id=figure.figure_id,
            module=figure.story_module, script_path=validator,
            command=" ".join(("/usr/bin/python3", validator, "--output", output, *inputs)),
            input_data_ids=figure.input_data_ids, input_paths=";".join(inputs),
            output_path=output, reference_product_path=reference,
            comparison_method="numpy.testing.assert_allclose",
            tolerance="rtol=0;atol=0", environment_command="/usr/bin/python3",
            representative=True,
            notes="Deterministic numeric-product reproduction from versioned plotting data; modules 04–05 have no honest numeric redraw candidate.",
        ))
    return tuple(recipes)


def manifest_payloads(
    inventory: RequiredAssetInventory,
    figures: Sequence[FigureRecipe],
    contract: PortableContract,
    redraws: Sequence[RedrawRecipe],
    keys: ManifestKeys,
    baseline_entries: Sequence[object] = (),
) -> dict[str, bytes]:
    copied = _copied(inventory)
    registry = copied[REGISTRY_SOURCE]
    required_rows = []
    for index, row in enumerate(inventory.rows):
        asset_id = (
            "asset-hopfion-analytic-texture-generator"
            if row.source_path == "95_shared_scripts/create_hopfion_AFM_v2.py"
            else f"asset-{index:04d}"
        )
        required_rows.append({
            "asset_id": asset_id, "module": (row.target_path or "excluded").split("/", 1)[0],
            "source_path": row.source_path, "required_reason": row.reason,
            "expected_target_class": row.expected_target_class,
            "target_path": row.target_path or "N/A", "source_sha256": row.sha256,
            "status": row.disposition, "notes": row.reason,
        })
    data_rows = []
    for data_id, path in sorted(keys.data_paths.items()):
        source = DATA_SOURCES.get(data_id)
        row = copied.get(source) if source is not None else registry
        assert row is not None
        suffix = PurePosixPath(path).suffix.casefold().lstrip(".") or "text"
        data_rows.append({
            "data_id": data_id, "path": path, "sha256": row.sha256,
            "data_kind": "provenance_record" if source is None else "plotting_input",
            "format": suffix, "shape": "source-defined", "columns": "source-defined",
            "units": "source-defined", "producer_script": VALIDATOR_SOURCE,
            "parent_source": source or "N/A", "parent_sha256": row.sha256 if source else "N/A",
            "is_complete_field": "false", "notes": "Versioned plotting input or excluded-field provenance anchor; never a complete OVF field.",
        })
    document_ids = sorted(keys.document_ids)
    document_rows = [{
        "document_id": document_id, "document_type": "source_registry",
        "title": document_id, "path": registry.target_path, "sha256": registry.sha256,
        "source_path": REGISTRY_SOURCE, "scientific_status": "indexed",
        "purpose": "Resolve figure source-document foreign keys without inventing missing metadata.",
        "notes": "Exact external locators remain in FIGURE_MANIFEST.csv.",
    } for document_id in document_ids]
    figure_run_ids = sorted(keys.run_ids - {run.run_id for run in contract.runs})
    run_rows = [{
        "run_id": run.run_id, "module": next((c.story_module for c in figures if run.run_id in (() if c.run_ids == "N/A" else IdList.parse(c.run_ids).items)), "shared"),
        "case_name": run.run_id, "status": run.status,
        "original_mx3": run.original_path, "portable_entry": run.portable_entry,
        "table_data_ids": "N/A", "other_data_ids": "N/A",
        "initial_state_recipe_id": next((c.initial_state_recipe_id for c in contract.consumers if c.run_id == run.run_id), "N/A"),
        "result_summary": "Portable active consumer registered by the canonical contract.",
        "notes": "Exact leaf run; see FULL_FIELD_CONSUMERS.csv.",
    } for run in contract.runs]
    run_rows.extend({
        "run_id": run_id, "module": next((f.story_module for f in figures if run_id in (() if f.run_ids == "N/A" else IdList.parse(f.run_ids).items)), "shared"),
        "case_name": run_id, "status": "reference_only", "original_mx3": "N/A",
        "portable_entry": "N/A", "table_data_ids": "N/A", "other_data_ids": "N/A",
        "initial_state_recipe_id": "N/A", "result_summary": "Figure-level run group; leaf consumers are registered separately.",
        "notes": "Reference grouping only; no fabricated aggregate executable.",
    } for run_id in figure_run_ids)
    topics = (
        ("topic-stability", "01_stability", "01_stability/centered_hopfion", "04_frustrated_fm_foundation"),
        ("topic-spinwave", "02_spinwave_control", "02_spinwave_control/plane_wave", "04_frustrated_fm_foundation"),
        ("topic-theory", "03_mechanism_and_theory", "03_mechanism_and_theory/thiele", "06_eigenmode_frequency_mechanism"),
        ("topic-lif", "04_lif_device", "04_lif_device/current_evidence", "08_lif_neuron_device_application"),
        ("topic-papers", "05_papers_and_talks", "05_papers_and_talks/thesis_and_talk", "09_paper_thesis_talks"),
    )
    topic_rows = [{
        "topic_id": topic_id, "module": module, "path": path,
        "source_roots": root, "current_status": "evidence_bounded",
        "readme_path": f"{path}/README.md", "notes": "Generated from handoff_docs.toml.",
    } for topic_id, module, path, root in topics]
    packaged_figures = package_figure_recipes(figures, inventory, redraws, keys.data_paths)
    payloads = {
        "00_handoff/REQUIRED_ASSETS.csv": _csv_bytes(REQUIRED_COLUMNS, required_rows),
        "00_handoff/DATA_MANIFEST.csv": _csv_bytes(DATA_COLUMNS, data_rows),
        "00_handoff/DOCUMENT_MANIFEST.csv": _csv_bytes(DOCUMENT_COLUMNS, document_rows),
        "00_handoff/RUN_MANIFEST.csv": _csv_bytes(RUN_COLUMNS, run_rows),
        "00_handoff/TOPIC_INDEX.csv": _csv_bytes(TOPIC_COLUMNS, topic_rows),
        "00_handoff/FIGURE_MANIFEST.csv": _csv_bytes(tuple(FigureRecipe.__dataclass_fields__), [asdict(row) for row in packaged_figures]),
    }
    if baseline_entries:
        payloads["00_handoff/OLD_PACKAGE_BASELINE.csv"] = _csv_bytes(
            ("relative_path", "path_type", "size", "sha256", "symlink_target"),
            [asdict(row) for row in baseline_entries],
        )
    archive_categories = sorted({
        PurePosixPath(row.target_path).parts[1]
        for row in inventory.rows
        if row.target_path is not None and row.target_path.startswith("90_archive/")
    })
    for category in archive_categories:
        payloads[f"90_archive/{category}/README.md"] = (
            f"# {category}\n\n"
            "此目录只保存历史、失败、中断、已取代或依赖本机绝对路径的源材料。"
            "它们便于追溯，但不构成 active 科学结论或可直接运行入口；"
            "准确状态以 00_handoff/REQUIRED_ASSETS.csv 和 FIGURE_MANIFEST.csv 为准。\n"
        ).encode("utf-8")
    return payloads
