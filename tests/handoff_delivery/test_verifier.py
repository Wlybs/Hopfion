from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, replace
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import zipfile

import numpy as np
import pytest

import handoff_delivery.verifier as verifier_module
from handoff_delivery.derived import DerivedRecipe
from handoff_delivery.lineage import FigureRecipe, load_figure_recipes
from handoff_delivery.portable import (
    FieldConsumer,
    InitialStateRecipe,
    PortableContract,
    PortableRuntimeEntry,
    PortableTransform,
    RunEntry,
    _snapshot_delivery_descriptor,
    apply_portable_transform,
    bind_initial_state_recipes_to_package,
    field_consumers_csv,
    initial_state_recipes_csv,
    packaged_initial_state_recipes_csv,
    portable_transforms_csv,
    portable_launcher_script,
    portable_runner_script,
    portable_wrappers_csv,
)
from handoff_delivery.redraw import RedrawRecipe, execute_redraws
from handoff_delivery.source_specs import (
    ExactSourceSpec,
    TreeSourceSpec,
    enumerate_required_assets,
)
from handoff_delivery.verifier import (
    VerificationError,
    VerificationResult,
    verify,
    write_checksums,
    write_report,
)


MODULES = (
    "01_stability",
    "02_spinwave_control",
    "03_mechanism_and_theory",
    "04_lif_device",
    "05_papers_and_talks",
)
ROOT_DIRECTORIES = (*MODULES, "00_handoff", "90_archive", "shared")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write(path: Path, payload: bytes | str = b"fixture\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload.encode() if isinstance(payload, str) else payload)
    return path


def _csv_bytes(columns: tuple[str, ...], rows: list[dict[str, object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or ()), list(reader)


def _rewrite_csv(path: Path, mutate) -> None:
    columns, rows = _read_csv(path)
    mutate(rows)
    path.write_bytes(_csv_bytes(tuple(columns), rows))


FIGURE_COLUMNS = tuple(FigureRecipe.__dataclass_fields__)
DATA_COLUMNS = (
    "data_id", "path", "sha256", "data_kind", "format", "shape", "columns",
    "units", "producer_script", "parent_source", "parent_sha256",
    "is_complete_field", "notes",
)
DOCUMENT_COLUMNS = (
    "document_id", "document_type", "title", "path", "sha256", "source_path",
    "scientific_status", "purpose", "notes",
)
RUN_COLUMNS = (
    "run_id", "module", "case_name", "status", "original_mx3", "portable_entry",
    "table_data_ids", "other_data_ids", "initial_state_recipe_id", "result_summary",
    "notes",
)
REQUIRED_COLUMNS = (
    "asset_id", "module", "source_path", "required_reason", "expected_target_class",
    "target_path", "source_sha256", "status", "notes",
)
TOPIC_COLUMNS = (
    "topic_id", "module", "path", "source_roots", "current_status", "readme_path",
    "notes",
)
REDRAW_COLUMNS = (
    "redraw_id", "figure_id", "module", "command", "environment_command",
    "input_data_ids", "environment", "input_sha256", "script_sha256",
    "output_sha256", "reference_sha256", "comparison_method", "tolerance", "result",
    "exit_code", "stdout_sha256", "stderr_sha256", "started_at_ns",
    "started_monotonic_ns", "raw_output_mtime_ns", "filesystem_clock_offset_ns",
    "filesystem_clock_uncertainty_ns", "output_mtime_ns", "finished_at_ns",
    "finished_monotonic_ns", "evidence_written_at_ns", "build_token",
)


@pytest.fixture(autouse=True)
def _load_synthetic_canonical_figure_ledger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use the strict CSV model for synthetic roots; production keeps full validation."""
    production = verifier_module.validate_recipe_ledger

    def load(project_root: Path):
        ledger = Path(project_root) / "95_shared_scripts/handoff_delivery/figure_recipes.csv"
        if ledger.is_file():
            return load_figure_recipes(ledger)
        return production(project_root)

    monkeypatch.setattr(verifier_module, "validate_recipe_ledger", load)


def _fixture(
    tmp_path: Path,
) -> tuple[
    Path,
    Path,
    PortableContract,
    tuple[tuple[TreeSourceSpec, ...], tuple[ExactSourceSpec, ...]],
]:
    project = tmp_path / "project"
    delivery = tmp_path / "delivery"
    for directory in ROOT_DIRECTORIES:
        (delivery / directory).mkdir(parents=True, exist_ok=True)

    original = b'm.LoadFile("input.ovf")\n'
    source_payloads = {
        "source/run.mx3": original,
        "source/generate.py": b"print('generate')\n",
        "source/relax.mx3": b"relax()\n",
        "source/evidence.txt": b"Documented source chain only.\n",
        "source/plot.py": b"print('validate inputs')\n",
        "source/data.csv": b"x,y\n0,1\n",
        "dynamic/base.txt": b"dynamic baseline\n",
    }
    for index in range(5):
        source_payloads[f"source/figure-{index}.png"] = f"PNG-{index}".encode()
    for relative, payload in source_payloads.items():
        _write(project / relative, payload)

    original_path = "01_stability/topic/simulation/original/run.mx3"
    portable_path = "01_stability/topic/simulation/portable/run.mx3"
    launcher_path = "01_stability/topic/simulation/portable/launch_run.py"
    transform = PortableTransform(
        transform_id="transform-1",
        run_id="run-1",
        source_path="source/run.mx3",
        original_path=original_path,
        original_sha256=_sha(original),
        portable_path=portable_path,
        replacements=(),
        strategy="identity",
    )
    run = RunEntry("run-1", "active", original_path, launcher_path)
    consumer = FieldConsumer(
        source_path="source/run.mx3",
        roles=("direct_loader",),
        status="active",
        run_id="run-1",
        initial_state_recipe_id="recipe-1",
        non_full_field_data_id="N/A",
        notes="Audited fixture loader.",
        portable_handling="identity",
        detection_evidence=("mx3.m_loadfile@L1",),
        status_evidence="source/evidence.txt:L1",
    )
    recipe = InitialStateRecipe(
        recipe_id="recipe-1",
        logical_name="Fixture initial state",
        original_ovf_reference="/historical/input.ovf",
        generator_script="source/generate.py",
        generator_parameters='{"QH":1}',
        relaxation_mx3="source/relax.mx3",
        expected_output="temporary/input.ovf",
        consumers=("source/run.mx3",),
        verification_status="documented_only",
        verification_evidence="source/evidence.txt",
        notes="Documented only; not rerun.",
        steps_json='["generate","relax","consume"]',
    )
    runtime = PortableRuntimeEntry(
        runtime_id="runtime-1",
        source_path="source/run.mx3",
        run_id="run-1",
        transform_id="transform-1",
        initial_state_recipe_id="recipe-1",
        runner_path="shared/runtime/portable_runner.py",
        launcher_path=launcher_path,
        mode="direct_loader",
        template_path=portable_path,
        command_json='["mumax3","{runtime_entry}"]',
        runtime_tokens=("INIT_OVF",),
    )
    contract = PortableContract(
        runs=(run,), transforms=(transform,), consumers=(consumer,), recipes=(recipe,),
        wrapper_contracts=(), config_toml=b'[paths]\nwork = "runtime"\n',
        runtime_entries=(runtime,),
    )

    targets = {
        "source/run.mx3": original_path,
        "source/generate.py": "shared/initial_state/generate.py",
        "source/relax.mx3": "shared/initial_state/relax.mx3",
        "source/evidence.txt": "01_stability/topic/notes/evidence.txt",
        "source/plot.py": "shared/plotting/plot.py",
        "source/data.csv": "shared/analysis/data.csv",
        "dynamic/base.txt": "01_stability/topic/dynamic/base.txt",
    }
    for index, module in enumerate(MODULES):
        targets[f"source/figure-{index}.png"] = f"{module}/topic/figures/figure-{index}.png"
    for source, target in targets.items():
        _write(delivery / target, source_payloads[source])
    _write(delivery / portable_path, apply_portable_transform(original, transform))
    _write(delivery / launcher_path, portable_launcher_script(runtime))
    _write(delivery / "shared/runtime/portable_runner.py", portable_runner_script())

    handoff = delivery / "00_handoff"
    _write(handoff / "PORTABLE_TRANSFORMS.csv", portable_transforms_csv(contract))
    _write(handoff / "PORTABLE_WRAPPERS.csv", portable_wrappers_csv(contract))
    _write(handoff / "INITIAL_STATE_RECIPES.csv", initial_state_recipes_csv(contract))
    _write(handoff / "FULL_FIELD_CONSUMERS.csv", field_consumers_csv(contract))
    _write(handoff / "PORTABLE_CONFIG.toml", contract.config_toml)

    data_path = "shared/analysis/data.csv"
    data_payload = (delivery / data_path).read_bytes()
    data_rows = [{
        "data_id": "data-1", "path": data_path, "sha256": _sha(data_payload),
        "data_kind": "scalar_summary", "format": "csv", "shape": "1x2",
        "columns": "x;y", "units": "1;1", "producer_script": "shared/plotting/plot.py",
        "parent_source": "source/data.csv", "parent_sha256": _sha(source_payloads["source/data.csv"]),
        "is_complete_field": "false", "notes": "Small plotting table.",
    }]
    for index, module in enumerate(MODULES):
        source = f"source/figure-{index}.png"
        figure_path = targets[source]
        data_rows.append({
            "data_id": f"reference-{index}", "path": figure_path,
            "sha256": _sha(source_payloads[source]), "data_kind": "figure_reference",
            "format": "png", "shape": "N/A", "columns": "N/A", "units": "N/A",
            "producer_script": "shared/plotting/plot.py", "parent_source": source,
            "parent_sha256": _sha(source_payloads[source]), "is_complete_field": "false",
            "notes": f"Exact redraw reference for {module}.",
        })
    _write(handoff / "DATA_MANIFEST.csv", _csv_bytes(DATA_COLUMNS, data_rows))
    _write(handoff / "DOCUMENT_MANIFEST.csv", _csv_bytes(DOCUMENT_COLUMNS, []))

    required_rows = []
    for index, source in enumerate(sorted(source_payloads)):
        target = targets[source]
        reason = (
            "portable-original:transform-1"
            if source == "source/run.mx3"
            else "authoritative-active-source"
        )
        required_rows.append({
            "asset_id": f"asset-{index}", "module": "fixture", "source_path": source,
            "required_reason": reason, "expected_target_class": "active",
            "target_path": target, "source_sha256": _sha(source_payloads[source]),
            "status": "copied_active", "notes": reason,
        })
    _write(handoff / "REQUIRED_ASSETS.csv", _csv_bytes(REQUIRED_COLUMNS, required_rows))
    _write(handoff / "RUN_MANIFEST.csv", _csv_bytes(RUN_COLUMNS, [{
        "run_id": "run-1", "module": "01_stability", "case_name": "fixture",
        "status": "active", "original_mx3": original_path, "portable_entry": launcher_path,
        "table_data_ids": "data-1", "other_data_ids": "N/A",
        "initial_state_recipe_id": "recipe-1", "result_summary": "Fixture only.",
        "notes": "Synthetic verifier fixture.",
    }]))

    figure_rows = []
    redraw_rows = []
    for index, module in enumerate(MODULES):
        figure_path = targets[f"source/figure-{index}.png"]
        figure_id = f"figure-{index}"
        figure_rows.append({
            "figure_id": figure_id, "usage_status": "formal" if index == 0 else "current_only",
            "scientific_status": "valid", "provenance_type": "simulation",
            "story_module": module, "claim_or_purpose": "Verifier fixture",
            "figure_path": figure_path, "figure_sha256": _sha(source_payloads[f"source/figure-{index}.png"]),
            "plot_script_path": "shared/plotting/plot.py",
            "plot_command": "python3 shared/plotting/plot.py shared/analysis/data.csv",
            "input_data_ids": "data-1", "parent_data_ids": "data-1",
            "derived_data_ids": "N/A", "run_ids": "run-1", "theory_asset_ids": "N/A",
            "initial_state_recipe_id": "recipe-1", "reproducibility": "input_validated",
            "source_document_ids": "N/A", "comparison_method": "sha256_exact",
            "tolerance": "exact", "notes": "Synthetic and fully registered.",
            "comparison_reference_data_id": f"reference-{index}",
        })
        redraw_rows.append({
            "redraw_id": f"redraw-{index}", "figure_id": figure_id, "module": module,
            "command": "python3 shared/plotting/plot.py shared/analysis/data.csv",
            "environment_command": "python3", "input_data_ids": "data-1",
            "environment": json.dumps({"python": "fixture"}),
            "input_sha256": json.dumps({data_path: _sha(data_payload)}),
            "script_sha256": _sha(source_payloads["source/plot.py"]),
            "output_sha256": _sha(source_payloads[f"source/figure-{index}.png"]),
            "reference_sha256": _sha(source_payloads[f"source/figure-{index}.png"]),
            "comparison_method": "sha256_exact", "tolerance": "exact", "result": "PASS",
            "exit_code": "0", "stdout_sha256": _sha(b""), "stderr_sha256": _sha(b""),
            "started_at_ns": "1", "started_monotonic_ns": "1", "raw_output_mtime_ns": "2",
            "filesystem_clock_offset_ns": "0", "filesystem_clock_uncertainty_ns": "1",
            "output_mtime_ns": "2", "finished_at_ns": "3", "finished_monotonic_ns": "3",
            "evidence_written_at_ns": "4", "build_token": "fixture-token",
        })
    _write(handoff / "FIGURE_MANIFEST.csv", _csv_bytes(FIGURE_COLUMNS, figure_rows))
    source_figure_rows = []
    for index, row in enumerate(figure_rows):
        source_row = dict(row)
        source_row["figure_path"] = f"source/figure-{index}.png"
        source_row["plot_script_path"] = "source/plot.py"
        source_row["plot_command"] = "python3 source/plot.py source/data.csv"
        source_figure_rows.append(source_row)
    _write(
        project / "95_shared_scripts/handoff_delivery/figure_recipes.csv",
        _csv_bytes(FIGURE_COLUMNS, source_figure_rows),
    )
    ledger_source = "95_shared_scripts/handoff_delivery/figure_recipes.csv"
    ledger_target = "shared/provenance/figure_recipes.csv"
    ledger_payload = (project / ledger_source).read_bytes()
    _write(delivery / ledger_target, ledger_payload)
    required_columns, required_manifest_rows = _read_csv(
        handoff / "REQUIRED_ASSETS.csv"
    )
    required_manifest_rows.append({
        "asset_id": "asset-canonical-figure-ledger", "module": "shared",
        "source_path": ledger_source,
        "required_reason": "authoritative-active-source",
        "expected_target_class": "active", "target_path": ledger_target,
        "source_sha256": _sha(ledger_payload), "status": "copied_active",
        "notes": "authoritative-active-source",
    })
    _write(
        handoff / "REQUIRED_ASSETS.csv",
        _csv_bytes(tuple(required_columns), required_manifest_rows),
    )
    _write(handoff / "FIGURE_REDRAW_EVIDENCE.csv", _csv_bytes(REDRAW_COLUMNS, redraw_rows))

    topics = []
    required_sections = (
        "## 研究问题\nFixture.\n\n## 当前状态\nValid.\n\n"
        "## 有效/无效结论\nFixture only.\n\n## 数据与代码入口\nSee manifests.\n\n"
        "## 复现级别\nInput validated.\n"
    )
    for index, module in enumerate(MODULES):
        path = f"{module}/topic"
        _write(delivery / module / "README.md", f"# {module}\n")
        _write(delivery / path / "README.md", f"# Topic {index}\n\n{required_sections}")
        topics.append({
            "topic_id": f"topic-{index}", "module": module, "path": path,
            "source_roots": "source", "current_status": "active",
            "readme_path": f"{path}/README.md", "notes": "Fixture topic.",
        })
    _write(handoff / "TOPIC_INDEX.csv", _csv_bytes(TOPIC_COLUMNS, topics))
    _write(delivery / "README.md", "# Handoff\n\n[Start](00_handoff/START_HERE.md)\n")
    _write(handoff / "START_HERE.md", "# Start here\n")
    _write(delivery / "shared/README.md", "# Shared\n")

    tree_specs = (TreeSourceSpec("dynamic", "01_stability/topic/dynamic"),)
    exact_specs = tuple(
        ExactSourceSpec(source, target)
        for source, target in sorted(targets.items())
        if source.startswith("source/")
    ) + (ExactSourceSpec(ledger_source, ledger_target),)
    required_assets = enumerate_required_assets(
        project,
        tree_specs=tree_specs,
        exact_specs=exact_specs,
        include_thesis_assets=False,
    )
    packaged_recipes = bind_initial_state_recipes_to_package(
        contract.recipes,
        required_assets=required_assets,
        transforms=contract.transforms,
    )
    _write(
        handoff / "INITIAL_STATE_RECIPES.csv",
        packaged_initial_state_recipes_csv(packaged_recipes),
    )
    specs = (tree_specs, exact_specs)
    return project, delivery, contract, specs


def _verify_fixture(
    project: Path,
    delivery: Path,
    contract: PortableContract,
    specs,
    *,
    require_final_evidence: bool = False,
    expected_derived_recipes=None,
):
    tree_specs, exact_specs = specs
    return verify(
        delivery,
        project_root=project,
        portable_contract=contract,
        tree_specs=tree_specs,
        exact_specs=exact_specs,
        include_thesis_assets=False,
        expected_derived_recipes=expected_derived_recipes,
        require_final_evidence=require_final_evidence,
    )


def _sync_canonical_ledger_asset(project: Path, delivery: Path) -> None:
    source = project / "95_shared_scripts/handoff_delivery/figure_recipes.csv"
    payload = source.read_bytes()
    _write(delivery / "shared/provenance/figure_recipes.csv", payload)

    def mutate(rows):
        row = next(
            item
            for item in rows
            if item["source_path"]
            == "95_shared_scripts/handoff_delivery/figure_recipes.csv"
        )
        row["source_sha256"] = _sha(payload)

    _rewrite_csv(delivery / "00_handoff/REQUIRED_ASSETS.csv", mutate)


def _gate(results: tuple[VerificationResult, ...], name: str) -> VerificationResult:
    return next(result for result in results if result.gate == name)


def test_positive_fixture_passes_all_five_gates_and_results_are_immutable(tmp_path: Path) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    results = _verify_fixture(project, delivery, contract, specs)
    assert tuple(row.gate for row in results) == ("G1", "G2", "G3", "G4", "G5")
    assert all(row.passed for row in results), results
    assert {
        "README.md",
        "shared/README.md",
        *(f"{module}/README.md" for module in MODULES),
        *(f"{module}/topic/README.md" for module in MODULES),
    } <= set(_gate(results, "G5").evidence_paths)
    with pytest.raises(FrozenInstanceError):
        results[0].passed = False  # type: ignore[misc]


def test_g2_requires_derived_evidence_when_the_build_plan_declares_a_recipe(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    recipe = DerivedRecipe(
        recipe_id="derived-fixture",
        output_data_id="derived-data",
        source_path="source/data.csv",
        source_sha256=_sha((project / "source/data.csv").read_bytes()),
        producer_script="95_shared_scripts/handoff_delivery/derived.py",
        producer_sha256="a" * 64,
        selector_kind="scalar",
        selector_json='{"array":"field","index":[0]}',
        output_path="01_stability/topic/data/derived.csv",
        output_format="csv",
        output_sha256="b" * 64,
        shape="1",
        columns="value",
        units="1",
        coordinate_origin="0",
        coordinate_spacing="1",
        coordinate_units="nm",
        parent_figure_ids="figure-0",
        parent_data_ids="data-1",
        environment_command="/mnt/d/Research/Hopfion/hopfion/bin/python",
        is_complete_field="false",
        notes="Missing-evidence fixture.",
    )

    result = _gate(
        _verify_fixture(
            project,
            delivery,
            contract,
            specs,
            expected_derived_recipes=(recipe,),
        ),
        "G2",
    )

    assert not result.passed
    assert any("DERIVED_DATA_EVIDENCE.csv is missing" in row for row in result.findings)


def test_g4_rejects_source_path_initial_state_recipe_manifest(tmp_path: Path) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _write(
        delivery / "00_handoff/INITIAL_STATE_RECIPES.csv",
        initial_state_recipes_csv(contract),
    )

    result = _gate(_verify_fixture(project, delivery, contract, specs), "G4")

    assert not result.passed
    assert any("package portable contract mismatch" in row for row in result.findings)


@pytest.mark.parametrize("variant", ["literal", "disguised", "archive", "npz"])
def test_g1_rejects_literal_disguised_archived_and_numpy_full_fields(
    tmp_path: Path, variant: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    target = delivery / "01_stability/topic/data/bad.bin"
    if variant == "literal":
        target = target.with_suffix(".ovf")
        _write(target, b"field")
    elif variant == "disguised":
        _write(target, b"# OOMMF: rectangular mesh v1.0\n# Begin: Data Text\n0 0 1\n")
    elif variant == "archive":
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w") as bundle:
            bundle.writestr("hidden/m.omf", b"field")
    else:
        target = target.with_suffix(".npz")
        target.parent.mkdir(parents=True, exist_ok=True)
        np.savez(target, mx=np.zeros((50, 50, 50)), my=np.zeros((50, 50, 50)), mz=np.zeros((50, 50, 50)))
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G1").passed


def test_g1_symlink_short_circuits_all_manifest_and_readme_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    external = _write(tmp_path / "external-sensitive.csv", "not,a,manifest\nsecret,value\n")
    manifest = delivery / "00_handoff/DATA_MANIFEST.csv"
    manifest.unlink()
    manifest.symlink_to(external)
    reads: list[str] = []
    production_read_csv = verifier_module._read_csv

    def track_read(root: Path, relative: str, columns: tuple[str, ...]):
        reads.append(relative)
        return production_read_csv(root, relative, columns)

    monkeypatch.setattr(verifier_module, "_read_csv", track_read)
    results = _verify_fixture(project, delivery, contract, specs)

    assert not _gate(results, "G1").passed
    assert all(not result.passed for result in results)
    assert reads == []
    assert all(
        any("not run because G1" in finding for finding in result.findings)
        for result in results[1:]
    )


@pytest.mark.parametrize("encoding", ["crlf", "bom"])
def test_g1_rejects_noncanonical_csv_encoding(tmp_path: Path, encoding: str) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    manifest = delivery / "00_handoff/DATA_MANIFEST.csv"
    payload = manifest.read_bytes()
    manifest.write_bytes(
        payload.replace(b"\n", b"\r\n") if encoding == "crlf" else b"\xef\xbb\xbf" + payload
    )
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G1").passed


def test_verify_binds_first_capture_to_materialized_expected_snapshot(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    descriptor = os.open(delivery, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        expected = _snapshot_delivery_descriptor(descriptor)
        target = delivery / "shared/analysis/data.csv"
        original = target.read_bytes()
        target.write_bytes(original.replace(b"0,1", b"9,9"))
        assert target.stat().st_size == len(original)
        tree_specs, exact_specs = specs
        results = verify(
            delivery,
            project_root=project,
            portable_contract=contract,
            tree_specs=tree_specs,
            exact_specs=exact_specs,
            include_thesis_assets=False,
            root_descriptor=descriptor,
            expected_snapshot=expected,
            require_final_evidence=False,
        )
    finally:
        os.close(descriptor)
    assert not _gate(results, "G1").passed
    assert all(not result.passed for result in results)
    assert any("materialized staging snapshot" in item for item in results[0].findings)


@pytest.mark.parametrize(
    "mutation",
    ["unregistered", "foreign-key", "status-evasion", "sha", "missing-evidence", "comparison"],
)
def test_g2_fails_closed_for_coverage_lineage_hash_evidence_and_comparison(
    tmp_path: Path, mutation: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    handoff = delivery / "00_handoff"
    if mutation == "unregistered":
        _write(delivery / "01_stability/topic/figures/unregistered.png", b"new")
    elif mutation == "foreign-key":
        _rewrite_csv(handoff / "FIGURE_MANIFEST.csv", lambda rows: rows[0].update(input_data_ids="missing"))
    elif mutation == "status-evasion":
        _rewrite_csv(handoff / "FIGURE_MANIFEST.csv", lambda rows: rows[0].update(usage_status="archive_only"))
    elif mutation == "sha":
        _write(delivery / "shared/analysis/data.csv", b"x,y\n0,999\n")
    elif mutation == "missing-evidence":
        _rewrite_csv(handoff / "FIGURE_REDRAW_EVIDENCE.csv", lambda rows: rows.pop(0))
    else:
        _rewrite_csv(handoff / "FIGURE_MANIFEST.csv", lambda rows: rows[0].update(comparison_method="N/A", tolerance="N/A"))
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G2").passed


@pytest.mark.parametrize("mutation", ["script", "input", "output-na", "reference"])
def test_g2_binds_each_numeric_figure_to_actual_redraw_hash_evidence(
    tmp_path: Path, mutation: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    path = delivery / "00_handoff/FIGURE_REDRAW_EVIDENCE.csv"

    def mutate(rows):
        if mutation == "script":
            rows[0]["script_sha256"] = "0" * 64
        elif mutation == "input":
            rows[0]["input_sha256"] = json.dumps({"shared/analysis/data.csv": "0" * 64})
        elif mutation == "output-na":
            rows[0]["output_sha256"] = "N/A"
        else:
            rows[0]["reference_sha256"] = "0" * 64

    _rewrite_csv(path, mutate)
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G2").passed


def test_g2_binds_sha256_exact_reference_to_declared_reference_data(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _rewrite_csv(
        delivery / "00_handoff/FIGURE_MANIFEST.csv",
        lambda rows: rows[0].update(comparison_reference_data_id="data-1"),
    )
    result = _gate(_verify_fixture(project, delivery, contract, specs), "G2")
    assert not result.passed
    assert any("reference data SHA" in finding for finding in result.findings)


@pytest.mark.parametrize(
    "mutation", ["orphan", "environment", "environment-command", "stdout-sha"]
)
def test_g2_rejects_fabricated_or_orphan_redraw_evidence(
    tmp_path: Path, mutation: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    path = delivery / "00_handoff/FIGURE_REDRAW_EVIDENCE.csv"

    def mutate(rows):
        if mutation == "orphan":
            orphan = dict(rows[0])
            orphan.update(redraw_id="orphan-redraw", figure_id="not-a-figure")
            rows.append(orphan)
        elif mutation == "environment":
            rows[0]["environment"] = "{}"
        elif mutation == "environment-command":
            rows[0]["environment_command"] = "bash"
        else:
            rows[0]["stdout_sha256"] = "not-a-sha"

    _rewrite_csv(path, mutate)
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G2").passed


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("table_data_ids", "missing-data"),
        ("other_data_ids", "missing-data"),
        ("initial_state_recipe_id", "missing-recipe"),
    ],
)
def test_g2_validates_run_manifest_dependency_foreign_keys(
    tmp_path: Path, field: str, value: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _rewrite_csv(
        delivery / "00_handoff/RUN_MANIFEST.csv",
        lambda rows: rows[0].update({field: value}),
    )

    result = _gate(_verify_fixture(project, delivery, contract, specs), "G2")
    assert not result.passed
    assert any("run dependency" in finding for finding in result.findings)


def test_g2_rejects_figure_reference_to_excluded_theory_asset(tmp_path: Path) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    required = delivery / "00_handoff/REQUIRED_ASSETS.csv"
    columns, rows = _read_csv(required)
    rows.append({
        "asset_id": "asset-excluded-theory", "module": "fixture",
        "source_path": "source/excluded-theory.txt", "required_reason": "excluded fixture",
        "expected_target_class": "excluded", "target_path": "N/A",
        "source_sha256": "", "status": "excluded_with_reason",
        "notes": "excluded fixture",
    })
    required.write_bytes(_csv_bytes(tuple(columns), rows))
    _rewrite_csv(
        delivery / "00_handoff/FIGURE_MANIFEST.csv",
        lambda figures: figures[0].update(theory_asset_ids="asset-excluded-theory"),
    )
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G2").passed


@pytest.mark.parametrize("mutation", ["missing-path", "wrong-hash"])
def test_g2_binds_document_manifest_rows_to_real_package_bytes(
    tmp_path: Path, mutation: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    payload = b"document evidence\n"
    document_path = "shared/documents/evidence.md"
    if mutation == "wrong-hash":
        _write(delivery / document_path, payload)
    row = {
        "document_id": "doc-evidence",
        "document_type": "note",
        "title": "Evidence",
        "path": document_path,
        "sha256": "0" * 64 if mutation == "wrong-hash" else _sha(payload),
        "source_path": "source/evidence.txt",
        "scientific_status": "valid",
        "purpose": "Verifier fixture.",
        "notes": "Synthetic document evidence.",
    }
    _write(
        delivery / "00_handoff/DOCUMENT_MANIFEST.csv",
        _csv_bytes(DOCUMENT_COLUMNS, [row]),
    )

    result = _gate(_verify_fixture(project, delivery, contract, specs), "G2")
    assert not result.passed
    assert any("document" in finding.casefold() for finding in result.findings)


def _archive_first_figure(delivery: Path, *, notes: str) -> str:
    manifest = delivery / "00_handoff/FIGURE_MANIFEST.csv"
    archive_path = "90_archive/superseded_figures/figure-0/figure-0.png"

    def mutate(rows):
        row = rows[0]
        source = delivery / row["figure_path"]
        _write(delivery / archive_path, source.read_bytes())
        source.unlink()
        row["scientific_status"] = "superseded"
        row["figure_path"] = archive_path
        row["notes"] = notes

    _rewrite_csv(manifest, mutate)
    _rewrite_csv(
        delivery / "00_handoff/DATA_MANIFEST.csv",
        lambda rows: next(
            row for row in rows if row["data_id"] == "reference-0"
        ).update(path=archive_path),
    )
    return archive_path


def _add_active_stability_representative(delivery: Path, archive_path: str) -> None:
    manifest = delivery / "00_handoff/FIGURE_MANIFEST.csv"
    columns, rows = _read_csv(manifest)
    replacement = dict(rows[0])
    replacement.update(
        figure_id="figure-0-current-representative",
        usage_status="current_only",
        scientific_status="valid",
        figure_path="01_stability/topic/figures/figure-0-current.png",
        notes="Current active representative for the fixture module.",
    )
    _write(delivery / replacement["figure_path"], (delivery / archive_path).read_bytes())
    rows.append(replacement)
    manifest.write_bytes(_csv_bytes(tuple(columns), rows))

    evidence = delivery / "00_handoff/FIGURE_REDRAW_EVIDENCE.csv"
    evidence_columns, evidence_rows = _read_csv(evidence)
    replacement_evidence = dict(evidence_rows[0])
    replacement_evidence.update(
        redraw_id="redraw-0-current-representative",
        figure_id=replacement["figure_id"],
    )
    evidence_rows.append(replacement_evidence)
    evidence.write_bytes(_csv_bytes(tuple(evidence_columns), evidence_rows))


def test_g2_requires_explicit_source_locator_and_warning_for_invalid_archive_figure(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _archive_first_figure(delivery, notes="Superseded fixture without evidence locator.")

    result = _gate(_verify_fixture(project, delivery, contract, specs), "G2")
    assert not result.passed
    assert any("source locator" in finding.casefold() for finding in result.findings)


def test_g2_rejects_active_readme_link_to_invalid_archive_figure(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    archive_path = _archive_first_figure(
        delivery,
        notes=(
            "source_locator=source/figure-0.png;"
            "must_route_to_superseded_archive;do_not_reuse"
        ),
    )
    readme = delivery / "01_stability/topic/README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + f"\n[Current valid result](../../{archive_path})\n",
        encoding="utf-8",
    )

    result = _gate(_verify_fixture(project, delivery, contract, specs), "G2")
    assert not result.passed
    assert any("active README" in finding for finding in result.findings)


def test_g2_allows_explicitly_warned_historical_link_from_active_readme(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    archive_path = _archive_first_figure(
        delivery,
        notes=(
            "source_locator=source/figure-0.png;"
            "must_route_to_superseded_archive;do_not_reuse"
        ),
    )
    _add_active_stability_representative(delivery, archive_path)
    readme = delivery / "01_stability/topic/README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + f"\n[WARNING: historical result; do not reuse](../../{archive_path})\n",
        encoding="utf-8",
    )

    assert _gate(_verify_fixture(project, delivery, contract, specs), "G2").passed


def test_g2_does_not_count_archived_invalid_redraw_as_module_representative(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _archive_first_figure(
        delivery,
        notes=(
            "source_locator=source/figure-0.png;"
            "must_route_to_superseded_archive;do_not_reuse"
        ),
    )
    result = _gate(_verify_fixture(project, delivery, contract, specs), "G2")
    assert not result.passed
    assert any("representative redraw modules" in finding for finding in result.findings)


def test_g2_accepts_execute_redraws_validation_only_evidence_for_superseded_simulation(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    archive_path = _archive_first_figure(
        delivery,
        notes=(
            "source_locator=source/figure-0.png;"
            "must_route_to_superseded_archive;do_not_reuse"
        ),
    )
    _add_active_stability_representative(delivery, archive_path)
    validator_path = "shared/validate_hash.py"
    _write(
        delivery / validator_path,
        "from pathlib import Path\n"
        "import hashlib\n"
        "import sys\n"
        "for raw in sys.argv[1:]:\n"
        "    hashlib.sha256(Path(raw).read_bytes()).hexdigest()\n",
    )
    python = str(Path(sys.executable).resolve())
    recipe = RedrawRecipe(
        redraw_id="redraw-0",
        figure_id="figure-0",
        module="01_stability",
        script_path=validator_path,
        command=(
            f"{python} {validator_path} shared/analysis/data.csv {archive_path}"
        ),
        input_data_ids="data-1",
        input_paths=f"shared/analysis/data.csv;{archive_path}",
        output_path="N/A",
        reference_product_path="N/A",
        comparison_method="input_hash_validation",
        tolerance="exact",
        environment_command=python,
        representative=False,
        notes="Validate the superseded simulation inputs and archived figure bytes.",
    )
    token = "fixture-token"
    _write(delivery / ".handoff-staging", token + "\n")
    try:
        generated = execute_redraws(
            (recipe,), staging_root=delivery, build_token=token
        )[0]
    finally:
        (delivery / ".handoff-staging").unlink()
    columns, evidence_rows = _read_csv(
        delivery / "00_handoff/FIGURE_REDRAW_EVIDENCE.csv"
    )
    generated_row = asdict(generated)
    generated_row["environment"] = json.dumps(
        generated.environment, sort_keys=True, separators=(",", ":")
    )
    generated_row["input_sha256"] = json.dumps(
        generated.input_sha256, sort_keys=True, separators=(",", ":")
    )
    evidence_rows[0] = generated_row
    _write(
        delivery / "00_handoff/FIGURE_REDRAW_EVIDENCE.csv",
        _csv_bytes(tuple(columns), evidence_rows),
    )

    assert _gate(_verify_fixture(project, delivery, contract, specs), "G2").passed


def test_g2_allows_scientifically_valid_archive_only_figure_in_archive(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    figure_manifest = delivery / "00_handoff/FIGURE_MANIFEST.csv"
    figure_columns, figures = _read_csv(figure_manifest)
    original = dict(figures[0])
    original_path = delivery / original["figure_path"]
    archive_path = "90_archive/historical_figures/figure-0/figure-0.png"
    _write(delivery / archive_path, original_path.read_bytes())
    original_path.unlink()
    figures[0].update(
        usage_status="archive_only",
        scientific_status="valid",
        figure_path=archive_path,
        notes="Historically useful and scientifically valid.",
    )
    _rewrite_csv(
        delivery / "00_handoff/DATA_MANIFEST.csv",
        lambda rows: next(
            row for row in rows if row["data_id"] == "reference-0"
        ).update(path=archive_path),
    )

    replacement = dict(original)
    replacement.update(
        figure_id="figure-0-current-representative",
        figure_path="01_stability/topic/figures/figure-0-current.png",
        notes="Current representative for the fixture module.",
    )
    _write(delivery / replacement["figure_path"], (delivery / archive_path).read_bytes())
    figures.append(replacement)
    figure_manifest.write_bytes(_csv_bytes(tuple(figure_columns), figures))

    redraw_path = delivery / "00_handoff/FIGURE_REDRAW_EVIDENCE.csv"
    redraw_columns, redraw_rows = _read_csv(redraw_path)
    replacement_evidence = dict(redraw_rows[0])
    replacement_evidence.update(
        redraw_id="redraw-0-current-representative",
        figure_id=replacement["figure_id"],
        output_sha256=replacement["figure_sha256"],
        reference_sha256=replacement["figure_sha256"],
    )
    redraw_rows[0] = replacement_evidence
    redraw_path.write_bytes(_csv_bytes(tuple(redraw_columns), redraw_rows))

    assert _gate(_verify_fixture(project, delivery, contract, specs), "G2").passed


def test_g2_rejects_an_extra_named_figure_manifest_column(tmp_path: Path) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    path = delivery / "00_handoff/FIGURE_MANIFEST.csv"
    columns, rows = _read_csv(path)
    for row in rows:
        row["undeclared_status_escape"] = "valid"
    path.write_bytes(_csv_bytes((*columns, "undeclared_status_escape"), rows))
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G2").passed


def test_g3_independently_enumerates_project_root_and_rejects_missing_source_row(tmp_path: Path) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _write(project / "dynamic/new-result.csv", "x\n1\n")
    result = _gate(_verify_fixture(project, delivery, contract, specs), "G3")
    assert not result.passed
    assert any("new-result.csv" in finding for finding in result.findings)


def test_g3_cannot_relabel_an_independently_active_source_as_archive(tmp_path: Path) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    path = delivery / "00_handoff/REQUIRED_ASSETS.csv"

    def mutate(rows):
        row = next(item for item in rows if item["source_path"] == "source/data.csv")
        old_target = delivery / row["target_path"]
        row["status"] = "copied_archive"
        row["expected_target_class"] = "archive"
        row["target_path"] = "90_archive/project_history/data.csv"
        _write(delivery / row["target_path"], old_target.read_bytes())

    _rewrite_csv(path, mutate)
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G3").passed


def test_g3_accepts_only_the_canonical_deterministic_figure_archive_reroute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _, packaged_figures = _read_csv(
        project / "95_shared_scripts/handoff_delivery/figure_recipes.csv"
    )
    source_figures = tuple(
        replace(
            FigureRecipe(**row),
            scientific_status="superseded" if index == 0 else row["scientific_status"],
            notes="WARNING: superseded fixture." if index == 0 else row["notes"],
        )
        for index, row in enumerate(packaged_figures)
    )
    source_figure = source_figures[0]
    ledger = project / "95_shared_scripts/handoff_delivery/figure_recipes.csv"
    _write(
        ledger,
        _csv_bytes(
            FIGURE_COLUMNS,
            [
                {key: str(value) for key, value in asdict(figure).items()}
                for figure in source_figures
            ],
        ),
    )
    _sync_canonical_ledger_asset(project, delivery)
    path = delivery / "00_handoff/REQUIRED_ASSETS.csv"

    def mutate(rows):
        for index, figure in enumerate(source_figures):
            row = next(item for item in rows if item["source_path"] == figure.figure_path)
            old_target = delivery / row["target_path"]
            if index == 0:
                row["status"] = "copied_archive"
                row["expected_target_class"] = "archive"
                row["target_path"] = "90_archive/superseded_figures/figure-0/figure-0.png"
                row["required_reason"] = "figure-superseded-archive"
                row["notes"] = "figure-superseded-archive"
            _write(delivery / row["target_path"], old_target.read_bytes())

    _rewrite_csv(path, mutate)
    packaged_path = delivery / "00_handoff/FIGURE_MANIFEST.csv"
    packaged_columns, packaged_rows = _read_csv(packaged_path)
    packaged_rows[0] = {
        key: str(value)
        for key, value in asdict(
            replace(
                source_figure,
                figure_path="90_archive/superseded_figures/figure-0/figure-0.png",
                plot_script_path=packaged_rows[0]["plot_script_path"],
                plot_command=packaged_rows[0]["plot_command"],
            )
        ).items()
    }
    packaged_path.write_bytes(_csv_bytes(tuple(packaged_columns), packaged_rows))
    assert _gate(_verify_fixture(project, delivery, contract, specs), "G3").passed


@pytest.mark.parametrize("mutation", ["ordinary-target", "missing-ledger", "portable-target"])
def test_g3_rebuilds_exact_targets_and_requires_canonical_figure_ledger(
    tmp_path: Path, mutation: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    required = delivery / "00_handoff/REQUIRED_ASSETS.csv"
    if mutation == "missing-ledger":
        (project / "95_shared_scripts/handoff_delivery/figure_recipes.csv").unlink()
    else:
        def mutate(rows):
            source = "source/data.csv" if mutation == "ordinary-target" else "source/run.mx3"
            row = next(item for item in rows if item["source_path"] == source)
            old_target = delivery / row["target_path"]
            row["target_path"] = (
                "01_stability/topic/data-renamed.csv"
                if mutation == "ordinary-target"
                else "01_stability/topic/simulation/original/substituted.mx3"
            )
            _write(delivery / row["target_path"], old_target.read_bytes())

        _rewrite_csv(required, mutate)
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G3").passed


def test_g3_binds_packaged_figure_rows_to_canonical_ledger_metadata(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)

    def relabel(rows):
        rows[0].update(
            provenance_type="schematic",
            scientific_status="not_applicable",
            input_data_ids="N/A",
            parent_data_ids="N/A",
            run_ids="N/A",
            initial_state_recipe_id="N/A",
            comparison_reference_data_id="N/A",
        )

    _rewrite_csv(delivery / "00_handoff/FIGURE_MANIFEST.csv", relabel)
    result = _gate(_verify_fixture(project, delivery, contract, specs), "G3")
    assert not result.passed
    assert any("canonical figure" in finding for finding in result.findings)


def test_g3_binds_required_reason_and_notes_to_independent_inventory(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _rewrite_csv(
        delivery / "00_handoff/REQUIRED_ASSETS.csv",
        lambda rows: rows[0].update(
            required_reason="invented reason", notes="invented notes"
        ),
    )
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G3").passed


def test_g3_rejects_empty_required_asset_module(tmp_path: Path) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _rewrite_csv(
        delivery / "00_handoff/REQUIRED_ASSETS.csv",
        lambda rows: rows[0].update(module=""),
    )
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G3").passed


def test_g3_treats_canonically_registered_pdf_outside_figures_as_a_figure(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    payload = b"registered PDF fixture\n"
    source = "source/registered-result.pdf"
    base_target = "03_mechanism_and_theory/topic/notes/registered-result.pdf"
    archive_target = "90_archive/superseded_figures/registered-pdf/registered-result.pdf"
    _write(project / source, payload)
    _write(delivery / archive_target, payload)
    ledger = project / "95_shared_scripts/handoff_delivery/figure_recipes.csv"
    columns, figure_rows = _read_csv(ledger)
    figure = replace(
        FigureRecipe(**figure_rows[0]),
        figure_id="registered-pdf",
        usage_status="archive_only",
        scientific_status="superseded",
        figure_path=source,
        figure_sha256=_sha(payload),
        notes="WARNING: superseded registered PDF.",
    )
    figure_rows.append({key: str(value) for key, value in asdict(figure).items()})
    ledger.write_bytes(_csv_bytes(tuple(columns), figure_rows))
    _sync_canonical_ledger_asset(project, delivery)
    required = delivery / "00_handoff/REQUIRED_ASSETS.csv"
    required_columns, required_rows = _read_csv(required)
    required_rows.append({
        "asset_id": "asset-registered-pdf", "module": "fixture", "source_path": source,
        "required_reason": "figure-superseded-archive", "expected_target_class": "archive",
        "target_path": archive_target, "source_sha256": _sha(payload),
        "status": "copied_archive", "notes": "figure-superseded-archive",
    })
    required.write_bytes(_csv_bytes(tuple(required_columns), required_rows))
    packaged = delivery / "00_handoff/FIGURE_MANIFEST.csv"
    packaged_columns, packaged_rows = _read_csv(packaged)
    packaged_rows.append({
        key: str(value)
        for key, value in asdict(
            replace(
                figure,
                figure_path=archive_target,
                plot_script_path=packaged_rows[0]["plot_script_path"],
                plot_command=packaged_rows[0]["plot_command"],
            )
        ).items()
    })
    packaged.write_bytes(_csv_bytes(tuple(packaged_columns), packaged_rows))
    tree_specs, exact_specs = specs
    expanded_specs = (tree_specs, (*exact_specs, ExactSourceSpec(source, base_target)))
    assert _gate(
        _verify_fixture(project, delivery, contract, expanded_specs), "G3"
    ).passed


def test_g3_never_resurrects_a_canonical_figure_excluded_by_base_inventory(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    payload = b"preview image fixture\n"
    source = "source/templates/generated_preview.png"
    target = "01_stability/topic/figures/generated_preview.png"
    _write(project / source, payload)
    _write(delivery / target, payload)
    ledger = project / "95_shared_scripts/handoff_delivery/figure_recipes.csv"
    columns, figure_rows = _read_csv(ledger)
    figure = replace(
        FigureRecipe(**figure_rows[0]),
        figure_id="excluded-preview",
        figure_path=source,
        figure_sha256=_sha(payload),
        notes="Canonical fixture that base policy excludes.",
    )
    figure_rows.append({key: str(value) for key, value in asdict(figure).items()})
    ledger.write_bytes(_csv_bytes(tuple(columns), figure_rows))
    _sync_canonical_ledger_asset(project, delivery)
    required = delivery / "00_handoff/REQUIRED_ASSETS.csv"
    required_columns, required_rows = _read_csv(required)
    required_rows.append({
        "asset_id": "asset-excluded-preview", "module": "fixture", "source_path": source,
        "required_reason": "malicious resurrection", "expected_target_class": "active",
        "target_path": target, "source_sha256": _sha(payload), "status": "copied_active",
        "notes": "Must be rejected because base enumeration excludes it.",
    })
    required.write_bytes(_csv_bytes(tuple(required_columns), required_rows))
    tree_specs, exact_specs = specs
    expanded_specs = (tree_specs, (*exact_specs, ExactSourceSpec(source, target)))
    result = _gate(
        _verify_fixture(project, delivery, contract, expanded_specs), "G3"
    )
    assert not result.passed
    assert any("base inventory excluded" in finding for finding in result.findings)


@pytest.mark.parametrize(
    "mutation",
    [
        "empty", "consumer", "original-sha", "missing-portable", "undeclared",
        "absolute", "runner", "independent-discovery",
    ],
)
def test_g4_rejects_incomplete_or_modified_portable_contract(
    tmp_path: Path, mutation: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    handoff = delivery / "00_handoff"
    candidate = contract
    if mutation == "empty":
        candidate = replace(contract, runs=(), transforms=(), runtime_entries=())
    elif mutation == "consumer":
        candidate = replace(contract, consumers=(replace(contract.consumers[0], initial_state_recipe_id="N/A"),))
    elif mutation == "original-sha":
        _write(delivery / contract.transforms[0].original_path, b"changed\n")
    elif mutation == "missing-portable":
        (delivery / contract.transforms[0].portable_path).unlink()
    elif mutation == "undeclared":
        _write(delivery / "01_stability/topic/simulation/portable/extra.mx3", b"Run(1e-9)\n")
    elif mutation == "absolute":
        _write(delivery / "01_stability/topic/analysis/run_bad.py", "open('D:/Research/Hopfion/input.ovf')\n")
    elif mutation == "runner":
        _write(delivery / "shared/runtime/portable_runner.py", "print('substituted runner')\n")
    else:
        _write(project / "source/plot.py", "open('new_field.ovf', 'rb')\n")
    assert not _gate(_verify_fixture(project, delivery, candidate, specs), "G4").passed


def test_g4_allows_active_non_simulation_run_without_original_but_rejects_bad_status(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    path = delivery / "00_handoff/RUN_MANIFEST.csv"
    columns, rows = _read_csv(path)
    rows.append({
        "run_id": "theory-only", "module": "03_mechanism_and_theory",
        "case_name": "analytical", "status": "active", "original_mx3": "N/A",
        "portable_entry": "N/A", "table_data_ids": "data-1", "other_data_ids": "N/A",
        "initial_state_recipe_id": "N/A", "result_summary": "Analytical row.",
        "notes": "No Mumax input exists.",
    })
    path.write_bytes(_csv_bytes(tuple(columns), rows))
    assert _gate(_verify_fixture(project, delivery, contract, specs), "G4").passed
    rows[-1]["status"] = "complete"
    path.write_bytes(_csv_bytes(tuple(columns), rows))
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G4").passed


def test_g4_binds_active_run_recipe_to_active_consumer_contract(tmp_path: Path) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _rewrite_csv(
        delivery / "00_handoff/RUN_MANIFEST.csv",
        lambda rows: rows[0].update(initial_state_recipe_id="N/A"),
    )
    result = _gate(_verify_fixture(project, delivery, contract, specs), "G4")
    assert not result.passed
    assert any("recipe" in finding.casefold() for finding in result.findings)


@pytest.mark.parametrize(
    "mutation",
    ["root", "template", "readme", "status", "denylist", "missing-topic", "missing-module"],
)
def test_g5_rejects_structure_templates_readme_scope_and_active_denylist(
    tmp_path: Path, mutation: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    if mutation == "root":
        (delivery / "06_parallel_taxonomy").mkdir()
    elif mutation == "template":
        _write(delivery / "01_stability/topic/README.md", "# Topic\n\n保留的分类目录\n")
    elif mutation == "readme":
        _write(delivery / "01_stability/topic/data/README.md", "# Leaf\n")
    elif mutation == "status":
        _write(delivery / "02_spinwave_control/topic/attempt_interrupted/result.txt", "partial\n")
    elif mutation == "denylist":
        _write(delivery / "03_mechanism_and_theory/topic/AGENTS.md", "old agent rules\n")
    elif mutation == "missing-topic":
        (delivery / "04_lif_device/topic/README.md").unlink()
    else:
        (delivery / "05_papers_and_talks/README.md").unlink()
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G5").passed


@pytest.mark.parametrize(
    "relative",
    [
        "01_stability/topic/AGENTS.local.md",
        "02_spinwave_control/topic/AGENTS_OLD.md",
        "03_mechanism_and_theory/topic/hdu-thesis.cls",
        "04_lif_device/topic/中文毕业论文模板说明.txt",
        "05_papers_and_talks/topic/latex-hdu-bachelor-thesis/hduthesis.cls",
    ],
)
def test_g5_rejects_agent_and_school_template_name_variants(
    tmp_path: Path, relative: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _write(delivery / relative, "forbidden active template\n")
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G5").passed


def test_g5_validates_start_here_links_and_template_text(tmp_path: Path) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    _write(
        delivery / "00_handoff/START_HERE.md",
        "# Start here\n\nplaceholder\n\n[Missing](../missing.md)\n",
    )
    assert not _gate(_verify_fixture(project, delivery, contract, specs), "G5").passed


def test_report_precedes_complete_checksum_and_later_verify_is_byte_and_mtime_immutable(
    tmp_path: Path,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    results = _verify_fixture(project, delivery, contract, specs)
    report = write_report(delivery, results)
    report_payload = json.loads(report.read_text(encoding="utf-8"))
    assert report_payload["readme_allowlist"] == sorted(
        path for path in _gate(results, "G5").evidence_paths if path.endswith(".md")
    )
    report_before_checksum = report.stat().st_mtime_ns
    checksum = write_checksums(delivery)
    assert checksum.stat().st_mtime_ns >= report_before_checksum

    lines = checksum.read_text(encoding="utf-8").splitlines()
    listed = {line.split("  ", 1)[1] for line in lines}
    regular = {
        path.relative_to(delivery).as_posix()
        for path in delivery.rglob("*")
        if path.is_file()
    }
    assert listed == regular - {"00_handoff/SHA256SUMS.txt"}
    before = {
        path.relative_to(delivery).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in delivery.rglob("*") if path.is_file()
    }
    second = _verify_fixture(project, delivery, contract, specs)
    after = {
        path.relative_to(delivery).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in delivery.rglob("*") if path.is_file()
    }
    assert all(row.passed for row in second)
    assert after == before


@pytest.mark.parametrize(
    "mutation",
    [
        "report", "listed-file", "missing-line", "duplicate-line",
        "missing-checksum", "delete-both",
    ],
)
def test_final_evidence_rejects_report_checksum_and_covered_file_tampering(
    tmp_path: Path, mutation: str,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    results = _verify_fixture(project, delivery, contract, specs)
    report = write_report(delivery, results)
    checksum = write_checksums(delivery)
    if mutation == "report":
        report.chmod(0o644)
        report.write_bytes(report.read_bytes().replace(b'"passed": true', b'"passed":false'))
    elif mutation == "listed-file":
        with (delivery / "README.md").open("ab") as handle:
            handle.write(b"\n")
    elif mutation == "missing-line":
        checksum.chmod(0o644)
        lines = checksum.read_bytes().splitlines(keepends=True)
        checksum.write_bytes(b"".join(lines[1:]))
    elif mutation == "duplicate-line":
        checksum.chmod(0o644)
        lines = checksum.read_bytes().splitlines(keepends=True)
        checksum.write_bytes(checksum.read_bytes() + lines[0])
    elif mutation == "missing-checksum":
        checksum.unlink()
    else:
        report.unlink()
        checksum.unlink()

    final = _verify_fixture(
        project,
        delivery,
        contract,
        specs,
        require_final_evidence=mutation == "delete-both",
    )
    assert not _gate(final, "G1").passed
    assert any(
        "final verification" in finding or "SHA256SUMS" in finding
        for finding in _gate(final, "G1").findings
    )


def test_exclusive_report_write_cleans_partial_file_after_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    results = _verify_fixture(project, delivery, contract, specs)
    report = delivery / "00_handoff/verification_report.json"
    production_fsync = verifier_module.os.fsync
    monkeypatch.setattr(
        verifier_module.os,
        "fsync",
        lambda _descriptor: (_ for _ in ()).throw(OSError("fixture fsync failure")),
    )
    with pytest.raises(VerificationError):
        write_report(delivery, results)
    assert not report.exists()
    monkeypatch.setattr(verifier_module.os, "fsync", production_fsync)
    assert write_report(delivery, results) == report


def test_path_mode_verify_report_and_checksum_reject_symlinked_ancestor(tmp_path: Path) -> None:
    project, delivery, contract, specs = _fixture(tmp_path)
    results = _verify_fixture(project, delivery, contract, specs)
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(delivery.parent, target_is_directory=True)
    linked_delivery = linked_parent / delivery.name
    with pytest.raises(VerificationError):
        tree_specs, exact_specs = specs
        verify(
            linked_delivery,
            project_root=project,
            portable_contract=contract,
            tree_specs=tree_specs,
            exact_specs=exact_specs,
            include_thesis_assets=False,
        )
    with pytest.raises(VerificationError):
        write_report(linked_delivery, results)
    assert not (delivery / "00_handoff/verification_report.json").exists()
