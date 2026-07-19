from __future__ import annotations

from dataclasses import replace
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import numpy as np
import pytest

import handoff_delivery.builder as builder_module
import handoff_delivery.portable as portable_module
import handoff_delivery.source_specs as source_specs_module
from handoff_delivery.builder import (
    BaselineError,
    BuildPlan,
    BuildRefusedError,
    build_delivery as _production_build_delivery,
    capture_baseline,
    compare_baseline,
    execute_build as _production_execute_build,
    prepare_build as _production_prepare_build,
)
from handoff_delivery.derived import (
    HOPFION_ENVIRONMENT_COMMAND,
    DerivedRecipe,
)
from handoff_delivery.lineage import FigureRecipe, ManifestKeys
from handoff_delivery.portable import (
    FieldConsumer,
    InitialStateRecipe,
    LiteralReplacement,
    PortableContract,
    PortableRuntimeEntry,
    PortableTransform,
    RunEntry,
    field_consumers_csv,
    initial_state_recipes_csv,
)
from handoff_delivery.redraw import RedrawRecipe
from handoff_delivery.source_specs import (
    EXACT_SOURCE_SPECS,
    TREE_SOURCE_SPECS,
    ExactSourceSpec,
    RequiredAssetInventory,
    RequiredAssetRow,
    SourceSpecError,
    TreeSourceSpec,
    enumerate_required_assets,
)
from handoff_delivery.verifier import VerificationResult


THIELE_FILES = {
    "07_thiele_theory_model/hopfion_thiele_research_plan_20260615/RESEARCH_PLAN.md",
    "07_thiele_theory_model/hopfion_thiele_research_plan_20260615/codex_prompts.md",
    "07_thiele_theory_model/results_thiele_GD_translation_20260615/G_D_translation.json",
    "07_thiele_theory_model/results_thiele_GD_translation_20260615/G_D_translation_stdout.log",
    "07_thiele_theory_model/results_thiele_GD_convergence_20260703/G_D_translation_convergence.json",
    "07_thiele_theory_model/results_thiele_GD_convergence_20260703/G_D_translation_convergence_stdout.log",
    "07_thiele_theory_model/results_thiele_GD_convergence_20260703/compute_GD_convergence.py",
}

FORMAL_CHAPTERS = (
    "ch01-intro.tex",
    "ch02-theory.tex",
    "ch03-construction.tex",
    "ch04-stability.tex",
    "ch05-dynamics.tex",
    "ch06-neuromorphic.tex",
    "ch07-conclusion.tex",
)


def _test_only_finalize_without_task6_gates(
    _plan: BuildPlan,
    _staging: Path,
    materialized,
):
    """Keep pre-Task6 synthetic mechanics tests scoped to their original subject."""
    return builder_module._VerifiedStagingHandle(
        materialized.staging_descriptor,
        materialized.staging_identity,
        materialized.staging_snapshot,
    )


def build_delivery(**kwargs: object):
    """Exercise copy mechanics with lineage patched only inside synthetic tests."""
    kwargs.setdefault(
        "portable_contract", SimpleNamespace(transforms=(), runtime_entries=())
    )
    with (
        patch.object(builder_module, "_load_project_figure_recipes", return_value=()),
        patch.object(builder_module, "_validate_lineage_preflight", return_value=None),
        patch.object(builder_module, "_validate_portable_preflight", return_value=None),
        patch.object(builder_module, "_require_portable_contract", return_value=None),
        patch.object(
            builder_module,
            "_validate_canonical_portable_ledgers_at_root",
            return_value=None,
        ),
        patch.object(
            builder_module,
            "_materialize_portable_pipeline",
            side_effect=lambda _plan, staging: (
                builder_module._pin_staging_pipeline_result(staging, ())
            ),
        ),
        patch.object(
            builder_module,
            "_finalize_verified_staging",
            side_effect=_test_only_finalize_without_task6_gates,
        ),
    ):
        return _production_build_delivery(**kwargs)


def prepare_build(**kwargs: object):
    """Exercise source-plan mechanics with a test-local lineage patch."""
    kwargs.setdefault(
        "portable_contract", SimpleNamespace(transforms=(), runtime_entries=())
    )
    with (
        patch.object(builder_module, "_load_project_figure_recipes", return_value=()),
        patch.object(builder_module, "_validate_lineage_preflight", return_value=None),
        patch.object(builder_module, "_validate_portable_preflight", return_value=None),
        patch.object(builder_module, "_require_portable_contract", return_value=None),
        patch.object(
            builder_module,
            "_validate_canonical_portable_ledgers_at_root",
            return_value=None,
        ),
    ):
        return _production_prepare_build(**kwargs)


def execute_build(plan: BuildPlan, *, resume: bool = False):
    """Exercise publication mechanics with a test-local lineage patch."""
    with (
        patch.object(
            builder_module,
            "_validate_canonical_figure_plan",
            return_value=None,
        ),
        patch.object(
            builder_module,
            "_validate_lineage_preflight",
            return_value=None,
        ),
        patch.object(
            builder_module,
            "_validate_portable_preflight",
            return_value=None,
        ),
        patch.object(
            builder_module,
            "_require_portable_contract",
            return_value=None,
        ),
        patch.object(
            builder_module,
            "_materialize_portable_pipeline",
            side_effect=lambda _plan, staging: (
                builder_module._pin_staging_pipeline_result(staging, ())
            ),
        ),
        patch.object(
            builder_module,
            "_finalize_verified_staging",
            side_effect=_test_only_finalize_without_task6_gates,
        ),
    ):
        return _production_execute_build(plan, resume=resume)


def execute_portable_build(plan: BuildPlan, *, resume: bool = False):
    """Patch unrelated lineage only; exercise the production portable gates."""
    with (
        patch.object(
            builder_module,
            "_validate_canonical_figure_plan",
            return_value=None,
        ),
        patch.object(
            builder_module,
            "_validate_lineage_preflight",
            return_value=None,
        ),
        patch.object(
            builder_module,
            "_finalize_verified_staging",
            side_effect=_test_only_finalize_without_task6_gates,
        ),
    ):
        return _production_execute_build(plan, resume=resume)


def write_file(path: Path, payload: bytes | str = b"fixture\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    path.write_bytes(data)
    return path


def regular_tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def fixture_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    write_file(
        root / "00_project_index/hopfion_spinwave_paper_master_plan_20260703.md",
        "# plan\n",
    )
    for relative in THIELE_FILES:
        write_file(root / relative)

    theory = root / "09_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608"
    write_file(theory / "B_point_vs_plane.md")
    write_file(theory / "D_skyrmion_spinwave_theory_library_20260705.md")
    write_file(theory / "E_skyrmion_spinwave_source_geometry_claim_ledger_20260705.md")
    write_file(
        root
        / "09_paper_thesis_talks/skyrmion_spinwave_dynamics_literature_report_20260705.pptx",
        b"presentation",
    )

    thesis = root / "09_paper_thesis_talks/bishe/thesis_v2"
    for chapter in FORMAL_CHAPTERS:
        body = "chapter\n"
        if chapter == "ch01-intro.tex":
            body += "\\includegraphics[width=.8\\textwidth]{figures/formal-a.png}\n"
        if chapter == "ch05-dynamics.tex":
            body += "\\includegraphics{figures/formal-b.png}\n"
        write_file(thesis / "chapters" / chapter, body)
    write_file(
        thesis / "chapters/ch01-intro_rewritten.tex",
        "\\includegraphics{figures/not-formal.png}\n",
    )
    write_file(thesis / "figures/formal-a.png", b"A")
    write_file(thesis / "figures/formal-b.png", b"B")
    write_file(thesis / "figures/not-formal.png", b"not formal")
    write_file(thesis / "figures/hdu_logo.png", b"logo")
    write_file(thesis / "figures/redraw.py", "print('redraw')\n")
    write_file(thesis / "figures/figure_cache.csv", "x,y\n1,2\n")
    write_file(thesis / "figures/_unused/ignored.py", "raise SystemExit\n")

    fm = root / "04_frustrated_fm_foundation/20260105_frustrated_fm"
    write_file(fm / "compute_hopf_index.py", "print('QH')\n")
    for source_root in (
        "centered_stability_test",
        "anisotropy_study",
        "size_sweep",
    ):
        write_file(fm / source_root / "current.txt")
    write_file(fm / "centered_stability_test/README.md", "active context\n")
    drift = fm / "drift_experiments"
    write_file(drift / "unified_rerun/run.mx3", "SetGridSize(1, 1, 1)\n")
    write_file(drift / "unified_rerun/run.sh", "mumax3 run.mx3\n")
    write_file(drift / "unified_rerun/config.json", "{}\n")
    write_file(drift / "analysis/summary.txt", "PASS\n")

    spinwave = fm / "spin_wave_dynamics"
    write_file(spinwave / "freq_sweep/current.mx3")
    write_file(spinwave / "attempt_failed/result.txt")
    write_file(spinwave / "attempt_failed/README.md", "failed context\n")
    write_file(spinwave / "interrupted_runs/run.log")
    write_file(spinwave / "field.ovf", b"field")
    write_file(
        spinwave / "renamed_field.txt",
        "# OOMMF: rectangular mesh v1.0\n# Begin: Data Text\n0 0 1\n",
    )
    archive = spinwave / "results.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("hidden/magnetization.ovf", b"field")
    write_file(spinwave / "__pycache__/analysis.pyc", b"cache")
    write_file(spinwave / "templates/base.mx3.template", b"template")

    write_file(root / "06_eigenmode_frequency_mechanism/ringdown/run.mx3")
    write_file(root / "hopfion_eigenmode_mechanism_20260612/control.py")
    lif = root / "08_lif_neuron_device_application/lif_neuron_hopfion"
    write_file(lif / "gradient_ku_verification/pass.txt", "PASS\n")
    write_file(lif / "lif_cycle_demo/run.py", "print('first cycle')\n")
    write_file(lif / "lif.py")
    write_file(root / "95_shared_scripts/analysis_tool.py")
    write_file(root / "95_shared_scripts/draw_afm_new.py.bak", b"backup")
    write_file(root / "95_shared_scripts/_test_plot.png", b"test output")
    return root


def test_default_specs_name_the_authoritative_roots_and_exact_files() -> None:
    roots = {spec.source_root for spec in TREE_SOURCE_SPECS}
    assert roots == {
        "07_thiele_theory_model",
        "04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test",
        "04_frustrated_fm_foundation/20260105_frustrated_fm/anisotropy_study",
        "04_frustrated_fm_foundation/20260105_frustrated_fm/size_sweep",
        "04_frustrated_fm_foundation/20260105_frustrated_fm/drift_experiments",
        "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics",
        "06_eigenmode_frequency_mechanism",
        "hopfion_eigenmode_mechanism_20260612",
        "08_lif_neuron_device_application/lif_neuron_hopfion",
        "95_shared_scripts",
    }
    exact = {spec.source_path for spec in EXACT_SOURCE_SPECS}
    assert exact == {
        "00_project_index/hopfion_spinwave_paper_master_plan_20260703.md",
        "09_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608/B_point_vs_plane.md",
        "09_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608/D_skyrmion_spinwave_theory_library_20260705.md",
        "09_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608/E_skyrmion_spinwave_source_geometry_claim_ledger_20260705.md",
        "09_paper_thesis_talks/skyrmion_spinwave_dynamics_literature_report_20260705.pptx",
        "04_frustrated_fm_foundation/20260105_frustrated_fm/compute_hopf_index.py",
    }


def test_every_candidate_gets_one_deterministic_disposition(fixture_project: Path) -> None:
    first = enumerate_required_assets(fixture_project)
    second = enumerate_required_assets(fixture_project)
    assert first == second
    assert first.source_paths_are_unique()
    assert first.target_paths_are_unique()
    assert set(first.status) == {
        "copied_active",
        "copied_archive",
        "excluded_with_reason",
    }
    assert all(row.reason for row in first if row.disposition == "excluded_with_reason")


def test_thiele_and_formal_thesis_assets_are_complete(fixture_project: Path) -> None:
    rows = enumerate_required_assets(fixture_project)
    by_source = {row.source_path: row for row in rows}
    assert THIELE_FILES <= by_source.keys()

    thesis_prefix = "09_paper_thesis_talks/bishe/thesis_v2/figures/"
    thesis_sources = {
        source for source in by_source if source.startswith(thesis_prefix)
    }
    assert thesis_sources == {
        thesis_prefix + "formal-a.png",
        thesis_prefix + "formal-b.png",
        thesis_prefix + "redraw.py",
        thesis_prefix + "figure_cache.csv",
    }
    assert by_source[thesis_prefix + "figure_cache.csv"].disposition == "copied_active"


def test_all_tree_candidates_are_enumerated_before_routing_or_exclusion(
    fixture_project: Path,
) -> None:
    rows = enumerate_required_assets(fixture_project)
    sources = {row.source_path for row in rows}
    spinwave_prefix = (
        "04_frustrated_fm_foundation/20260105_frustrated_fm/"
        "spin_wave_dynamics/"
    )
    assert {
        spinwave_prefix + "freq_sweep/current.mx3",
        spinwave_prefix + "attempt_failed/result.txt",
        spinwave_prefix + "interrupted_runs/run.log",
        spinwave_prefix + "field.ovf",
        spinwave_prefix + "renamed_field.txt",
        spinwave_prefix + "results.zip",
        spinwave_prefix + "__pycache__/analysis.pyc",
        spinwave_prefix + "templates/base.mx3.template",
    } <= sources


def test_failed_interrupted_incomplete_and_superseded_route_only_to_archive(
    fixture_project: Path,
) -> None:
    spinwave = (
        fixture_project
        / "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics"
    )
    write_file(spinwave / "attempt_incomplete/state.txt")
    write_file(spinwave / "superseded_figures/old.png", b"old")

    for row in enumerate_required_assets(fixture_project):
        lowered = row.source_path.casefold()
        if any(word in lowered for word in ("failed", "interrupted", "incomplete", "superseded")):
            assert row.disposition == "copied_archive"
            assert row.expected_target_class == "archive"
            assert row.target_path is not None
            assert row.target_path.startswith("90_archive/")


@pytest.mark.parametrize(
    ("relative", "category"),
    [
        ("drive_selection/freq_probe.txt", "drive_selection"),
        ("freq_sweep/multisource_probe.txt", "frequency_sweeps"),
        ("amplitude_sweep/freq_probe.txt", "amplitude_sweeps"),
        (
            "multisource_control/bidirectional_z/freq_switch_v3.txt",
            "multisource",
        ),
        (
            "reverse_propagation_controls/freq_reverse_probe.txt",
            "reverse_propagation",
        ),
        ("vibY_plane_wave/freq_probe.txt", "point_vs_plane"),
        ("vibY_point_source/freq_probe.txt", "point_vs_plane"),
    ],
)
def test_spinwave_first_directory_has_routing_precedence(
    tmp_path: Path,
    relative: str,
    category: str,
) -> None:
    root = tmp_path / "project"
    source_root = root / "spin_wave_dynamics"
    write_file(source_root / relative)
    rows = enumerate_required_assets(
        root,
        tree_specs=(
            TreeSourceSpec(
                "spin_wave_dynamics",
                "02_spinwave_control",
                route="spinwave",
            ),
        ),
        exact_specs=(),
        include_thesis_assets=False,
    )
    assert len(rows) == 1
    assert rows[0].target_path is not None
    assert rows[0].target_path.startswith(f"02_spinwave_control/{category}/")


def test_canonical_failed_lif_cycle_routes_to_archive_but_gradient_stays_active(
    fixture_project: Path,
) -> None:
    prefix = "08_lif_neuron_device_application/lif_neuron_hopfion/"
    rows = enumerate_required_assets(fixture_project)
    cycle_rows = [
        row for row in rows if row.source_path.startswith(prefix + "lif_cycle_demo/")
    ]
    gradient_rows = [
        row
        for row in rows
        if row.source_path.startswith(prefix + "gradient_ku_verification/")
    ]
    assert cycle_rows
    assert all(row.disposition == "copied_archive" for row in cycle_rows)
    assert all(row.expected_target_class == "archive" for row in cycle_rows)
    assert all("canonical" in row.reason and "FAILED" in row.reason for row in cycle_rows)
    assert gradient_rows
    assert all(row.disposition == "copied_active" for row in gradient_rows)


def test_valid_python_source_with_oommf_literal_is_not_mistaken_for_field(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    source = root / "95_shared_scripts/scanner.py"
    write_file(
        source,
        'MARKERS = (b"# OOMMF:", b"Begin: Data Text")\n'
        'def detects(payload: bytes) -> bool:\n'
        '    return any(marker in payload for marker in MARKERS)\n',
    )
    rows = enumerate_required_assets(
        root,
        tree_specs=(TreeSourceSpec("95_shared_scripts", "shared", route="shared"),),
        exact_specs=(),
        include_thesis_assets=False,
    )
    assert len(rows) == 1
    assert rows[0].disposition == "copied_active"
    assert rows[0].sha256
    assert rows[0].reason == "authoritative-active-source"


def test_oommf_header_renamed_as_python_remains_excluded(tmp_path: Path) -> None:
    root = tmp_path / "project"
    write_file(
        root / "95_shared_scripts/fake.py",
        "# OOMMF: rectangular mesh v1.0\n# Begin: Data Text\n0 0 1\n",
    )
    rows = enumerate_required_assets(
        root,
        tree_specs=(TreeSourceSpec("95_shared_scripts", "shared", route="shared"),),
        exact_specs=(),
        include_thesis_assets=False,
    )
    assert rows[0].disposition == "excluded_with_reason"
    assert rows[0].reason == "oommf-content"


def test_fields_cache_templates_and_shared_test_outputs_are_explicitly_excluded(
    fixture_project: Path,
) -> None:
    rows = enumerate_required_assets(fixture_project)
    by_source = {row.source_path: row for row in rows}
    excluded_suffixes = {
        "spin_wave_dynamics/field.ovf",
        "spin_wave_dynamics/renamed_field.txt",
        "spin_wave_dynamics/results.zip",
        "spin_wave_dynamics/__pycache__/analysis.pyc",
        "spin_wave_dynamics/templates/base.mx3.template",
        "95_shared_scripts/_test_plot.png",
    }
    for suffix in excluded_suffixes:
        row = next(row for source, row in by_source.items() if source.endswith(suffix))
        assert row.disposition == "excluded_with_reason"
        assert row.target_path is None
        assert row.reason


@pytest.mark.parametrize("suffix", [".bak", ".backup", ".orig"])
def test_standard_backup_files_are_explicitly_excluded(
    tmp_path: Path,
    suffix: str,
) -> None:
    root = tmp_path / "project"
    source = f"95_shared_scripts/draw_afm_new.py{suffix}"
    write_file(root / source, b"backup")
    rows = enumerate_required_assets(
        root,
        tree_specs=(TreeSourceSpec("95_shared_scripts", "shared", route="shared"),),
        exact_specs=(),
        include_thesis_assets=False,
    )
    assert len(rows) == 1
    assert rows[0].source_path == source
    assert rows[0].disposition == "excluded_with_reason"
    assert rows[0].target_path is None
    assert rows[0].reason == "backup-file"


def test_content_inspector_handles_disguised_and_generic_archived_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    write_file(root / "literal.ovf", b"large-field-placeholder")
    write_file(root / "ovf_archive.tar.zst", b"large-archive-placeholder")
    write_file(
        root / "disguised.txt",
        "# OOMMF: rectangular mesh v1.0\n# Begin: Data Text\n0 0 1\n",
    )
    with zipfile.ZipFile(root / "generic.zip", "w") as bundle:
        bundle.writestr("hidden/m.ovf", b"field")

    inspected: list[str] = []
    real_inspector = source_specs_module.inspect_candidate

    def recording_inspector(path: Path) -> object:
        inspected.append(Path(path).name)
        return real_inspector(path)

    monkeypatch.setattr(source_specs_module, "inspect_candidate", recording_inspector)
    rows = enumerate_required_assets(
        root,
        tree_specs=(),
        exact_specs=tuple(
            ExactSourceSpec(name, f"01_stability/{name}")
            for name in (
                "literal.ovf",
                "ovf_archive.tar.zst",
                "disguised.txt",
                "generic.zip",
            )
        ),
        include_thesis_assets=False,
    )

    assert set(inspected) == {"disguised.txt", "generic.zip"}
    assert {row.disposition for row in rows} == {"excluded_with_reason"}
    by_source = {row.source_path: row for row in rows}
    assert by_source["literal.ovf"].sha256 == ""
    assert by_source["literal.ovf"].reason == "literal-field-name-unhashed"
    assert by_source["ovf_archive.tar.zst"].sha256 == ""
    assert (
        by_source["ovf_archive.tar.zst"].reason
        == "explicit-ovf-archive-name-unhashed"
    )


def test_generated_v1_readme_is_never_copied(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source = "hopfion_delivery_20260706/topic/README.md"
    write_file(root / source, "generated template\n")
    rows = enumerate_required_assets(
        root,
        tree_specs=(),
        exact_specs=(ExactSourceSpec(source, "01_stability/topic/README.md"),),
        include_thesis_assets=False,
    )
    assert len(rows) == 1
    assert rows[0].disposition == "excluded_with_reason"
    assert rows[0].reason == "generated-v1-readme"


def test_source_readmes_are_preserved_as_context_without_expanding_allowlist(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    rows = enumerate_required_assets(fixture_project)
    copied = [row for row in rows if row.target_path is not None]
    assert copied
    assert all(Path(row.target_path).name != "README.md" for row in copied)

    active_source = (
        "04_frustrated_fm_foundation/20260105_frustrated_fm/"
        "centered_stability_test/README.md"
    )
    archive_source = (
        "04_frustrated_fm_foundation/20260105_frustrated_fm/"
        "spin_wave_dynamics/attempt_failed/README.md"
    )
    by_source = {row.source_path: row for row in rows}
    assert by_source[active_source].target_path is not None
    assert by_source[active_source].target_path.endswith("/SOURCE_CONTEXT.md")
    assert by_source[archive_source].target_path is not None
    assert by_source[archive_source].target_path.endswith("/SOURCE_CONTEXT.md")

    old = tmp_path / "old"
    write_file(old / "README.md", "old package\n")
    destination = tmp_path / "delivery-v2"
    result = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    assert result.publishable
    for source in (active_source, archive_source):
        target = by_source[source].target_path
        assert target is not None
        assert (destination / target).read_bytes() == (fixture_project / source).read_bytes()


def test_source_context_rename_collision_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    write_file(root / "topic/README.md")
    write_file(root / "topic/SOURCE_CONTEXT.md")
    with pytest.raises(SourceSpecError, match="target collision"):
        enumerate_required_assets(
            root,
            tree_specs=(TreeSourceSpec("topic", "01_stability/topic"),),
            exact_specs=(),
            include_thesis_assets=False,
        )


def test_missing_required_source_root_fails_closed(fixture_project: Path) -> None:
    missing = fixture_project / "07_thiele_theory_model"
    for path in sorted(missing.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        else:
            path.rmdir()
    missing.rmdir()
    with pytest.raises(SourceSpecError, match="07_thiele_theory_model"):
        enumerate_required_assets(fixture_project)


@pytest.mark.parametrize(
    ("source", "target"),
    [("../escape", "01_stability/file"), ("safe", "../escape")],
)
def test_source_specs_reject_path_escape(source: str, target: str) -> None:
    with pytest.raises(SourceSpecError):
        ExactSourceSpec(source, target)


def test_target_collision_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    write_file(root / "a.txt", b"A")
    write_file(root / "b.txt", b"B")
    with pytest.raises(SourceSpecError, match="target collision"):
        enumerate_required_assets(
            root,
            tree_specs=(),
            exact_specs=(
                ExactSourceSpec("a.txt", "01_stability/same.txt"),
                ExactSourceSpec("b.txt", "01_stability/same.txt"),
            ),
            include_thesis_assets=False,
        )


def test_tree_source_root_must_be_a_real_directory(tmp_path: Path) -> None:
    root = tmp_path / "project"
    write_file(root / "not-a-directory")
    with pytest.raises(SourceSpecError, match="not-a-directory"):
        enumerate_required_assets(
            root,
            tree_specs=(
                TreeSourceSpec("not-a-directory", "01_stability", route="fixed"),
            ),
            exact_specs=(),
            include_thesis_assets=False,
        )


def test_exact_source_rejects_intermediate_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    write_file(outside / "secret.txt", b"outside")
    (root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(SourceSpecError, match="linked"):
        enumerate_required_assets(
            root,
            tree_specs=(),
            exact_specs=(
                ExactSourceSpec("linked/secret.txt", "01_stability/secret.txt"),
            ),
            include_thesis_assets=False,
        )


def test_tree_source_rejects_intermediate_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    write_file(outside / "tree/secret.txt", b"outside")
    (root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(SourceSpecError, match="linked"):
        enumerate_required_assets(
            root,
            tree_specs=(TreeSourceSpec("linked/tree", "01_stability/tree"),),
            exact_specs=(),
            include_thesis_assets=False,
        )


def test_source_scandir_permission_error_is_not_silently_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    write_file(root / "tree/asset.txt", b"asset")
    real_scandir = source_specs_module.os.scandir

    def denied_scandir(path: object):
        if isinstance(path, int):
            raise PermissionError("source tree denied")
        return real_scandir(path)

    monkeypatch.setattr(source_specs_module.os, "scandir", denied_scandir)
    with pytest.raises(SourceSpecError, match="cannot enumerate anchored directory"):
        enumerate_required_assets(
            root,
            tree_specs=(TreeSourceSpec("tree", "01_stability/tree"),),
            exact_specs=(),
            include_thesis_assets=False,
        )


def test_formal_chapter_file_symlink_is_not_followed(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    chapter = (
        fixture_project
        / "09_paper_thesis_talks/bishe/thesis_v2/chapters/ch01-intro.tex"
    )
    outside = write_file(
        tmp_path / "outside-chapter.tex",
        "\\includegraphics{figures/formal-a.png}\n",
    )
    chapter.unlink()
    chapter.symlink_to(outside)

    with pytest.raises(SourceSpecError, match="ch01-intro"):
        enumerate_required_assets(fixture_project)


def test_formal_figure_reference_rejects_intermediate_symlink_escape(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    thesis = fixture_project / "09_paper_thesis_talks/bishe/thesis_v2"
    write_file(
        thesis / "chapters/ch01-intro.tex",
        "\\includegraphics{figures/linked/secret.png}\n",
    )
    outside = tmp_path / "outside-figures"
    write_file(outside / "secret.png", b"outside")
    (thesis / "figures/linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(SourceSpecError, match="linked"):
        enumerate_required_assets(fixture_project)


def test_thesis_root_rejects_intermediate_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "project"
    outside_bishe = tmp_path / "outside-bishe"
    thesis = outside_bishe / "thesis_v2"
    for chapter in FORMAL_CHAPTERS:
        write_file(thesis / "chapters" / chapter, "chapter\n")
    write_file(thesis / "figures/data.csv", "x,y\n1,2\n")
    link_parent = root / "09_paper_thesis_talks"
    link_parent.mkdir(parents=True)
    (link_parent / "bishe").symlink_to(outside_bishe, target_is_directory=True)

    with pytest.raises(SourceSpecError, match="bishe"):
        enumerate_required_assets(
            root,
            tree_specs=(),
            exact_specs=(),
            include_thesis_assets=True,
        )


def test_manual_build_plan_cannot_copy_through_intermediate_symlink(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    payload = b"outside-secret"
    write_file(outside / "secret.txt", payload)
    (project / "linked").symlink_to(outside, target_is_directory=True)
    old = tmp_path / "old"
    write_file(old / "README.md")
    destination = tmp_path / "delivery-v2"
    row = RequiredAssetRow(
        source_path="linked/secret.txt",
        target_path="01_stability/secret.txt",
        disposition="copied_active",
        expected_target_class="active",
        reason="test-fixture",
        sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload),
        file_type="file",
    )
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=destination,
        required_assets=RequiredAssetInventory((row,)),
        old_baseline=capture_baseline(old),
    )

    result = execute_build(plan)
    assert result.exit_code != 0
    assert not result.publishable
    assert not destination.exists()
    assert (outside / "secret.txt").read_bytes() == payload


def test_production_execute_refuses_missing_portable_contract_before_destination(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=tmp_path / "delivery",
        required_assets=RequiredAssetInventory(()),
        old_baseline=capture_baseline(old),
    )

    result = _production_execute_build(plan)

    assert result.exit_code != 0
    assert "portable contract is required" in result.reason
    assert not plan.destination.exists()


def test_production_prepare_and_dry_run_cannot_bypass_missing_portable_contract(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    destination = tmp_path / "delivery"

    with pytest.raises(BuildRefusedError, match="portable contract is required"):
        _production_prepare_build(
            project_root=fixture_project,
            old_delivery=old,
            destination=destination,
            tree_specs=(),
            exact_specs=(),
            include_thesis_assets=False,
        )
    with pytest.raises(BuildRefusedError, match="portable contract is required"):
        _production_build_delivery(
            project_root=fixture_project,
            old_delivery=old,
            destination=destination,
            dry_run=True,
            tree_specs=(),
            exact_specs=(),
            include_thesis_assets=False,
        )
    assert not destination.exists()


def _portable_fixture_plan(tmp_path: Path) -> tuple[BuildPlan, bytes]:
    project = tmp_path / "portable-project"
    original = (
        b'// archival bytes remain unchanged\r\n'
        b'm.LoadFile("/mnt/d/Research/Hopfion/m000020.ovf")\r\n'
    )
    write_file(project / "src/run.mx3", original)
    write_file(project / "src/generate.py", "print('seed')\n")
    write_file(project / "src/relax.mx3", "relax()\n")
    write_file(project / "evidence/notes.txt", "Historical path notes only.\n")
    old = tmp_path / "portable-old"
    write_file(old / "README.md", "old package\n")
    original_target = "01_stability/topic/simulation/original/run.mx3"
    portable_target = "01_stability/topic/simulation/portable/run.mx3"
    launcher_target = "01_stability/topic/simulation/portable/launch_run.py"
    row = RequiredAssetRow(
        source_path="src/run.mx3",
        target_path=original_target,
        disposition="copied_active",
        expected_target_class="active",
        reason="portable integration fixture",
        sha256=hashlib.sha256(original).hexdigest(),
        size=len(original),
        file_type="file",
    )
    dependency_rows = tuple(
        RequiredAssetRow(
            source_path=source_path,
            target_path=target_path,
            disposition="copied_active",
            expected_target_class="active",
            reason="initial-state recipe fixture",
            sha256=hashlib.sha256(payload).hexdigest(),
            size=len(payload),
            file_type="file",
        )
        for source_path, target_path, payload in (
            (
                "src/generate.py",
                "shared/initial_state/generate.py",
                (project / "src/generate.py").read_bytes(),
            ),
            (
                "src/relax.mx3",
                "shared/initial_state/relax.mx3",
                (project / "src/relax.mx3").read_bytes(),
            ),
            (
                "evidence/notes.txt",
                "01_stability/topic/notes/initial-state-evidence.txt",
                (project / "evidence/notes.txt").read_bytes(),
            ),
        )
    )
    run = RunEntry("run-portable", "active", original_target, launcher_target)
    transform = PortableTransform(
        transform_id="transform-portable",
        run_id=run.run_id,
        source_path="src/run.mx3",
        original_path=original_target,
        original_sha256=row.sha256,
        portable_path=portable_target,
        replacements=(
            LiteralReplacement(
                old=b"/mnt/d/Research/Hopfion/m000020.ovf",
                new=b"${INIT_OVF}",
                expected_count=1,
            ),
        ),
    )
    consumer = FieldConsumer(
        source_path="src/run.mx3",
        roles=("direct_loader",),
        status="active",
        run_id=run.run_id,
        initial_state_recipe_id="recipe-portable",
        non_full_field_data_id="N/A",
        notes="content-discovered direct loader",
        portable_handling="literal_transform",
        detection_evidence=("mx3.m_loadfile@L2",),
        status_evidence="evidence/notes.txt:L1",
    )
    recipe = InitialStateRecipe(
        recipe_id="recipe-portable",
        logical_name="Documented fixture initial state",
        original_ovf_reference="/mnt/d/Research/Hopfion/m000020.ovf",
        generator_script="src/generate.py",
        generator_parameters='{"QH": 1}',
        relaxation_mx3="src/relax.mx3",
        expected_output="temporary/m000020.ovf",
        consumers=("src/run.mx3",),
        verification_status="documented_only",
        verification_evidence="evidence/notes.txt",
        notes="Documented only; no simulation was run for this delivery.",
        steps_json='["generate", "relax", "consume"]',
    )
    runtime = PortableRuntimeEntry(
        runtime_id="runtime-portable",
        source_path=transform.source_path,
        run_id=transform.run_id,
        transform_id=transform.transform_id,
        initial_state_recipe_id=recipe.recipe_id,
        runner_path="shared/runtime/portable_runner.py",
        launcher_path=launcher_target,
        mode="direct_loader",
        template_path=transform.portable_path,
        command_json='["mumax3","{runtime_entry}"]',
        runtime_tokens=("INIT_OVF",),
    )
    contract = PortableContract(
        runs=(run,),
        transforms=(transform,),
        consumers=(consumer,),
        recipes=(recipe,),
        wrapper_contracts=(),
        config_toml=(
            b'[paths]\ninitial_state = "shared/initial_state/m000020.ovf"\n'
        ),
        runtime_entries=(runtime,),
    )
    write_file(
        project / "95_shared_scripts/handoff_delivery/initial_state_recipes.csv",
        initial_state_recipes_csv(contract),
    )
    write_file(
        project / "95_shared_scripts/handoff_delivery/full_field_consumers.csv",
        field_consumers_csv(contract),
    )
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=tmp_path / "portable-delivery",
        required_assets=RequiredAssetInventory((row, *dependency_rows)),
        old_baseline=capture_baseline(old),
        portable_contract=contract,
    )
    return plan, original


def test_builder_materializes_portable_contract_in_staging_without_mutating_source(
    tmp_path: Path,
) -> None:
    plan, original = _portable_fixture_plan(tmp_path)
    source = plan.project_root / "src/run.mx3"

    result = execute_portable_build(plan)

    assert result.exit_code == 0, result.reason
    assert result.publishable
    destination = plan.destination
    original_target = destination / plan.portable_contract.runs[0].original_path  # type: ignore[union-attr]
    launcher_target = destination / plan.portable_contract.runs[0].portable_entry  # type: ignore[union-attr]
    portable_target = destination / plan.portable_contract.transforms[0].portable_path  # type: ignore[union-attr]
    assert source.read_bytes() == original
    assert original_target.read_bytes() == original
    assert b"${INIT_OVF}" in portable_target.read_bytes()
    assert b"/mnt/d/Research/Hopfion" not in portable_target.read_bytes()
    assert launcher_target.is_file()
    assert b"${INIT_OVF}" not in launcher_target.read_bytes()
    assert {
        "00_handoff/PORTABLE_TRANSFORMS.csv",
        "00_handoff/PORTABLE_WRAPPERS.csv",
        "00_handoff/INITIAL_STATE_RECIPES.csv",
        "00_handoff/FULL_FIELD_CONSUMERS.csv",
        "00_handoff/PORTABLE_CONFIG.toml",
        "01_stability/topic/simulation/portable/run.mx3",
        "01_stability/topic/simulation/portable/launch_run.py",
    } <= set(result.written_paths)


def test_builder_never_publishes_staging_replaced_at_portable_g4_scan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plan, _original = _portable_fixture_plan(tmp_path)
    original_scan = portable_module.scan_delivery_absolute_paths
    replaced = False

    def replace_at_scan(root: Path, **kwargs):
        nonlocal replaced
        if not replaced:
            replaced = True
            root.rename(root.with_name(root.name + ".verified"))
            root.mkdir()
            (root / "attacker.txt").write_text("attacker", encoding="utf-8")
        return original_scan(root, **kwargs)

    monkeypatch.setattr(
        portable_module,
        "scan_delivery_absolute_paths",
        replace_at_scan,
    )

    result = execute_portable_build(plan)

    assert result.exit_code == 1
    assert not result.publishable
    assert not plan.destination.exists()


def test_builder_never_publishes_staging_replaced_after_portable_materialization_returns(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plan, _original = _portable_fixture_plan(tmp_path)
    original_materialize = builder_module._materialize_portable_pipeline
    replaced = False

    def materialize_then_replace(build_plan: BuildPlan, staging: Path):
        nonlocal replaced
        written = original_materialize(build_plan, staging)
        if not replaced:
            replaced = True
            staging.rename(staging.with_name(staging.name + ".verified"))
            staging.mkdir()
            (staging / "attacker.txt").write_text("attacker", encoding="utf-8")
        return written

    monkeypatch.setattr(
        builder_module,
        "_materialize_portable_pipeline",
        materialize_then_replace,
    )

    result = execute_portable_build(plan)

    assert result.exit_code == 1
    assert not result.publishable
    assert not plan.destination.exists()


def test_builder_never_publishes_portable_child_mutated_after_g4_scan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plan, _original = _portable_fixture_plan(tmp_path)
    assert plan.portable_contract is not None
    portable_path = plan.portable_contract.transforms[0].portable_path
    original_materialize = builder_module._materialize_portable_pipeline
    mutated = False

    def materialize_then_mutate(build_plan: BuildPlan, staging: Path):
        nonlocal mutated
        materialized = original_materialize(build_plan, staging)
        target = staging / portable_path
        payload = target.read_bytes()
        changed = payload.replace(b"${INIT_OVF}", b"/tmp/evilxx")
        assert len(changed) == len(payload)
        assert changed != payload
        target.write_bytes(changed)
        mutated = True
        return materialized

    monkeypatch.setattr(
        builder_module,
        "_materialize_portable_pipeline",
        materialize_then_mutate,
    )

    result = execute_portable_build(plan)

    assert mutated
    assert result.exit_code == 1
    assert not result.publishable
    assert not plan.destination.exists()


def test_builder_never_publishes_staging_replaced_after_portable_scan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plan, _original = _portable_fixture_plan(tmp_path)
    original_capture = builder_module._capture_destination_snapshot
    replaced = False

    def replace_before_publish(path: Path):
        nonlocal replaced
        if path == plan.destination and not replaced:
            candidates = tuple(
                plan.destination.parent.glob(
                    f".{plan.destination.name}.staging-*"
                )
            )
            if candidates:
                replaced = True
                staging = candidates[0]
                staging.rename(staging.with_name(staging.name + ".verified"))
                staging.mkdir()
                (staging / "attacker.txt").write_text(
                    "attacker", encoding="utf-8"
                )
        return original_capture(path)

    monkeypatch.setattr(
        builder_module,
        "_capture_destination_snapshot",
        replace_before_publish,
    )

    result = execute_portable_build(plan)

    assert result.exit_code == 1
    assert not result.publishable
    assert not plan.destination.exists()


def test_verified_staging_handle_is_closed_after_successful_publication(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plan, _original = _portable_fixture_plan(tmp_path)
    original_publish = builder_module._publish_staging
    captured: list[builder_module._VerifiedStagingHandle] = []

    def capture_handle(*args, verified_staging, **kwargs):
        captured.append(verified_staging)
        return original_publish(
            *args,
            verified_staging=verified_staging,
            **kwargs,
        )

    monkeypatch.setattr(builder_module, "_publish_staging", capture_handle)

    result = execute_portable_build(plan)

    assert result.exit_code == 0, result.reason
    assert result.publishable
    assert len(captured) == 1
    assert captured[0].descriptor == -1


def test_verified_staging_handle_is_closed_after_publication_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plan, _original = _portable_fixture_plan(tmp_path)
    captured: list[builder_module._VerifiedStagingHandle] = []

    def fail_publication(*_args, verified_staging, **_kwargs):
        captured.append(verified_staging)
        raise builder_module._PublicationFailure(
            "synthetic publication refusal",
            backup=None,
            displaced_snapshot=None,
            recovery_status="not-needed",
            recovery_paths=(),
        )

    monkeypatch.setattr(builder_module, "_publish_staging", fail_publication)

    result = execute_portable_build(plan)

    assert result.exit_code == 1
    assert not result.publishable
    assert len(captured) == 1
    assert captured[0].descriptor == -1


def test_production_portable_and_lineage_build_resumes_byte_identically(
    tmp_path: Path,
) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    lineage_project, exact_specs, derived, redraw = task4_pipeline_fixture(
        tmp_path / "lineage"
    )
    lineage_inventory = enumerate_required_assets(
        lineage_project,
        tree_specs=(),
        exact_specs=exact_specs,
        include_thesis_assets=False,
    )
    for relative in (
        derived.source_path,
        derived.producer_script,
        *(row.source_path for row in lineage_inventory),
    ):
        write_file(
            plan.project_root / relative,
            (lineage_project / relative).read_bytes(),
        )
    plan = replace(
        plan,
        required_assets=RequiredAssetInventory(
            (*plan.required_assets.rows, *lineage_inventory.rows)
        ),
        derived_recipes=(derived,),
        redraw_recipes=(redraw,),
    )
    assert redraw.output_path in builder_module._declared_generated_paths(plan)

    first = execute_portable_build(plan)

    assert first.exit_code == 0, first.reason
    assert first.publishable
    before = regular_tree_bytes(plan.destination)
    assert {
        derived.output_path,
        "00_handoff/DERIVED_DATA_EVIDENCE.csv",
        "00_handoff/FIGURE_REDRAW_EVIDENCE.csv",
        "00_handoff/PORTABLE_TRANSFORMS.csv",
        plan.portable_contract.transforms[0].portable_path,  # type: ignore[union-attr]
        plan.portable_contract.runtime_entries[0].launcher_path,  # type: ignore[union-attr]
    } <= set(before)

    resumed = execute_portable_build(plan, resume=True)

    assert resumed.exit_code == 0, resumed.reason
    assert resumed.publishable
    after = regular_tree_bytes(plan.destination)
    execution_evidence = {
        "00_handoff/DERIVED_DATA_EVIDENCE.csv",
        "00_handoff/FIGURE_REDRAW_EVIDENCE.csv",
    }
    assert {
        path: payload
        for path, payload in after.items()
        if path not in execution_evidence
    } == {
        path: payload
        for path, payload in before.items()
        if path not in execution_evidence
    }
    assert execution_evidence <= set(after)


def test_builder_refuses_missing_recipe_before_publishing(tmp_path: Path) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    assert plan.portable_contract is not None
    broken = replace(
        plan,
        portable_contract=replace(plan.portable_contract, recipes=()),
    )

    result = execute_portable_build(broken)

    assert result.exit_code != 0
    assert not result.publishable
    assert "canonical initial-state recipe ledger" in result.reason
    assert not plan.destination.exists()


def test_builder_revalidates_manual_transform_sha_and_never_publishes(
    tmp_path: Path,
) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    assert plan.portable_contract is not None
    transform = plan.portable_contract.transforms[0]
    broken_transform = replace(transform, original_sha256="0" * 64)
    broken = replace(
        plan,
        portable_contract=replace(
            plan.portable_contract,
            transforms=(broken_transform,),
        ),
    )

    result = execute_portable_build(broken)

    assert result.exit_code != 0
    assert not result.publishable
    assert "SHA256" in result.reason
    assert not plan.destination.exists()


def test_builder_refuses_portable_output_collision_with_copied_target(
    tmp_path: Path,
) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    assert plan.portable_contract is not None
    portable = plan.portable_contract.transforms[0].portable_path
    payload = b"must not be overwritten\n"
    write_file(plan.project_root / "src/collision.txt", payload)
    collision = RequiredAssetRow(
        source_path="src/collision.txt",
        target_path=portable,
        disposition="copied_active",
        expected_target_class="active",
        reason="collision fixture",
        sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload),
        file_type="file",
    )
    broken = replace(
        plan,
        required_assets=RequiredAssetInventory(
            (*plan.required_assets.rows, collision)
        ),
    )

    result = execute_portable_build(broken)

    assert result.exit_code != 0
    assert not result.publishable
    assert "collid" in result.reason.casefold()
    assert not plan.destination.exists()


def test_builder_refuses_literal_count_mismatch_after_copy_without_publishing(
    tmp_path: Path,
) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    assert plan.portable_contract is not None
    transform = plan.portable_contract.transforms[0]
    broken_replacement = replace(
        transform.replacements[0],
        expected_count=2,
    )
    broken = replace(
        plan,
        portable_contract=replace(
            plan.portable_contract,
            transforms=(replace(transform, replacements=(broken_replacement,)),),
        ),
    )

    result = execute_portable_build(broken)

    assert result.exit_code != 0
    assert not result.publishable
    assert "occurrence" in result.reason
    assert not plan.destination.exists()


def test_builder_runs_g4_on_materialized_portable_before_publish(
    tmp_path: Path,
) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    assert plan.portable_contract is not None
    transform = plan.portable_contract.transforms[0]
    machine_specific = replace(
        transform.replacements[0],
        new=b"/home/another-user/generated-state.ovf",
    )
    broken = replace(
        plan,
        portable_contract=replace(
            plan.portable_contract,
            transforms=(replace(transform, replacements=(machine_specific,)),),
        ),
    )

    result = execute_portable_build(broken)

    assert result.exit_code != 0
    assert not result.publishable
    assert "G4 executable scan" in result.reason
    assert not plan.destination.exists()


def test_execute_reloads_canonical_portable_ledgers_and_rejects_forged_contract(
    tmp_path: Path,
) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    assert plan.portable_contract is not None
    forged_consumer = replace(
        plan.portable_contract.consumers[0],
        notes="caller-forged classification",
    )
    forged = replace(
        plan,
        portable_contract=replace(
            plan.portable_contract,
            consumers=(forged_consumer,),
        ),
    )

    result = execute_portable_build(forged)

    assert result.exit_code != 0
    assert "canonical full-field consumer ledger" in result.reason
    assert not plan.destination.exists()


def test_execute_refuses_canonical_ledger_changed_to_header_only_after_plan(
    tmp_path: Path,
) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    ledger = (
        plan.project_root
        / "95_shared_scripts/handoff_delivery/initial_state_recipes.csv"
    )
    ledger.write_text(
        "recipe_id,logical_name,original_ovf_reference,generator_script,"
        "generator_parameters,relaxation_mx3,expected_output,consumers,"
        "verification_status,verification_evidence,notes,steps_json\n",
        encoding="utf-8",
    )

    result = execute_portable_build(plan)

    assert result.exit_code != 0
    assert "canonical initial-state recipe ledger" in result.reason
    assert not plan.destination.exists()


def test_execute_refuses_missing_canonical_consumer_ledger(tmp_path: Path) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    ledger = (
        plan.project_root
        / "95_shared_scripts/handoff_delivery/full_field_consumers.csv"
    )
    ledger.unlink()

    result = execute_portable_build(plan)

    assert result.exit_code != 0
    assert "canonical portable ledger failed" in result.reason
    assert not plan.destination.exists()


def test_prepare_reloads_canonical_portable_ledgers_instead_of_trusting_argument(
    tmp_path: Path,
) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    assert plan.portable_contract is not None
    forged = replace(
        plan.portable_contract,
        recipes=(replace(plan.portable_contract.recipes[0], notes="forged"),),
    )

    with (
        patch.object(builder_module, "_load_project_figure_recipes", return_value=()),
        patch.object(builder_module, "_validate_lineage_preflight", return_value=None),
        pytest.raises(
            BuildRefusedError,
            match="canonical initial-state recipe ledger",
        ),
    ):
        _production_prepare_build(
            project_root=plan.project_root,
            old_delivery=plan.old_delivery,
            destination=plan.destination,
            tree_specs=(),
            exact_specs=(),
            include_thesis_assets=False,
            portable_contract=forged,
        )


def test_prepare_reroutes_enumerated_transform_source_to_original_tree(
    tmp_path: Path,
) -> None:
    fixture_plan, _ = _portable_fixture_plan(tmp_path)
    assert fixture_plan.portable_contract is not None

    with (
        patch.object(builder_module, "_load_project_figure_recipes", return_value=()),
        patch.object(builder_module, "_validate_lineage_preflight", return_value=None),
    ):
        prepared = _production_prepare_build(
            project_root=fixture_plan.project_root,
            old_delivery=fixture_plan.old_delivery,
            destination=fixture_plan.destination,
            tree_specs=(TreeSourceSpec("src", "01_stability/topic"),),
            exact_specs=(
                ExactSourceSpec(
                    "evidence/notes.txt",
                    "01_stability/topic/notes/initial-state-evidence.txt",
                ),
            ),
            include_thesis_assets=False,
            portable_contract=fixture_plan.portable_contract,
        )

    source_row = next(
        row for row in prepared.required_assets if row.source_path == "src/run.mx3"
    )
    assert source_row.target_path == (
        "01_stability/topic/simulation/original/run.mx3"
    )
    assert source_row.sha256 == hashlib.sha256(
        (fixture_plan.project_root / "src/run.mx3").read_bytes()
    ).hexdigest()


def test_execute_revalidates_source_to_original_target_binding(
    tmp_path: Path,
) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    row = plan.required_assets.rows[0]
    broken = replace(
        plan,
        required_assets=RequiredAssetInventory(
            (replace(row, target_path="01_stability/topic/run.mx3"),)
        ),
    )

    result = execute_portable_build(broken)

    assert result.exit_code != 0
    assert "source-to-original binding" in result.reason
    assert not plan.destination.exists()


def test_builder_discovery_candidates_include_structured_and_extensionless_shebang(
    tmp_path: Path,
) -> None:
    plan, _ = _portable_fixture_plan(tmp_path)
    additions: list[RequiredAssetRow] = []
    for source_path, target_path, payload in (
        (
            "configs/run.toml",
            "01_stability/topic/analysis/run.toml",
            b'initial_state = "temporary/state.ovf"\n',
        ),
        (
            "jobs/launch",
            "01_stability/topic/analysis/launch",
            b"#!/bin/sh\nmumax3 run.mx3\n",
        ),
    ):
        write_file(plan.project_root / source_path, payload)
        additions.append(
            RequiredAssetRow(
                source_path=source_path,
                target_path=target_path,
                disposition="copied_active",
                expected_target_class="active",
                reason="consumer discovery boundary fixture",
                sha256=hashlib.sha256(payload).hexdigest(),
                size=len(payload),
                file_type="file",
            )
        )
    broken = replace(
        plan,
        required_assets=RequiredAssetInventory(
            (*plan.required_assets.rows, *additions)
        ),
    )

    result = execute_portable_build(broken)

    assert result.exit_code != 0
    assert "discovery set" in result.reason
    assert "configs/run.toml" in result.reason
    assert "jobs/launch" in result.reason
    assert not plan.destination.exists()


def test_old_baseline_walk_error_is_not_silently_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", b"old")
    real_walk = builder_module.os.walk

    def denied_walk(top: object, *args: object, **kwargs: object):
        if Path(top) == old:
            onerror = kwargs.get("onerror")
            if onerror is not None:
                onerror(PermissionError("old baseline denied"))  # type: ignore[operator]
            return iter(())
        return real_walk(top, *args, **kwargs)

    monkeypatch.setattr(builder_module.os, "walk", denied_walk)
    with pytest.raises(BaselineError, match="cannot enumerate old delivery"):
        capture_baseline(old)


def test_resume_walk_error_cannot_hide_unknown_destination_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "delivery-v2"
    write_file(destination / "unknown/secret.txt", b"unknown")
    real_walk = builder_module.os.walk

    def denied_walk(top: object, *args: object, **kwargs: object):
        if Path(top) == destination:
            onerror = kwargs.get("onerror")
            if onerror is not None:
                onerror(PermissionError("resume destination denied"))  # type: ignore[operator]
            return iter(())
        return real_walk(top, *args, **kwargs)

    monkeypatch.setattr(builder_module.os, "walk", denied_walk)
    with pytest.raises(BuildRefusedError, match="cannot enumerate resume destination"):
        builder_module._validate_destination(
            destination,
            resume=True,
            source_rows=(),
        )
    assert (destination / "unknown/secret.txt").read_bytes() == b"unknown"


def test_dry_run_writes_nothing_and_returns_complete_rows(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md")
    destination = tmp_path / "delivery-v2"

    result = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
        dry_run=True,
    )
    assert result.exit_code == 0
    assert result.dry_run
    assert not result.publishable
    assert not destination.exists()
    assert len(result.required_rows) == len(enumerate_required_assets(fixture_project))
    assert set(result.source_rows) == {
        row for row in result.required_rows if row.disposition != "excluded_with_reason"
    }
    assert set(result.exclusion_rows) == {
        row for row in result.required_rows if row.disposition == "excluded_with_reason"
    }


def test_build_copies_only_mapped_assets_with_byte_identity(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "old package\n")
    destination = tmp_path / "delivery-v2"

    result = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    assert result.exit_code == 0
    assert result.publishable
    assert result.baseline_difference.is_clean
    for row in result.required_rows:
        source = fixture_project / row.source_path
        if row.disposition == "excluded_with_reason":
            assert row.target_path is None
            continue
        assert row.target_path is not None
        target = destination / row.target_path
        assert target.is_file()
        assert target.read_bytes() == source.read_bytes()


def test_nonempty_destination_rejects_unknown_file_even_with_resume(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md")
    destination = tmp_path / "delivery-v2"
    write_file(destination / "unrelated.txt", "keep\n")

    with pytest.raises(BuildRefusedError, match="non-empty"):
        build_delivery(
            project_root=fixture_project,
            old_delivery=old,
            destination=destination,
        )
    with pytest.raises(BuildRefusedError, match="unknown"):
        build_delivery(
            project_root=fixture_project,
            old_delivery=old,
            destination=destination,
            resume=True,
        )


def test_resume_accepts_only_matching_mapped_files_and_rebuilds_fresh(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md")
    destination = tmp_path / "delivery-v2"
    initial = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    assert initial.publishable

    resumed = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
        resume=True,
    )
    assert resumed.publishable
    assert {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    } == {row.target_path for row in resumed.source_rows}


def test_resume_rejects_mismatched_mapped_file(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md")
    destination = tmp_path / "delivery-v2"
    initial = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    row = next(row for row in initial.source_rows if row.target_path is not None)
    write_file(destination / row.target_path, b"corrupt")

    with pytest.raises(BuildRefusedError, match="size or SHA256"):
        build_delivery(
            project_root=fixture_project,
            old_delivery=old,
            destination=destination,
            resume=True,
        )
    assert (destination / row.target_path).read_bytes() == b"corrupt"


def test_resume_rejects_unknown_directory(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md")
    destination = tmp_path / "delivery-v2"
    (destination / "unknown-empty-directory").mkdir(parents=True)

    with pytest.raises(BuildRefusedError, match="unknown"):
        build_delivery(
            project_root=fixture_project,
            old_delivery=old,
            destination=destination,
            resume=True,
        )


def test_resume_rejects_symlinked_destination_ancestor(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md")
    destination = tmp_path / "delivery-v2"
    outside = tmp_path / "outside"
    outside.mkdir()
    destination.mkdir()
    (destination / "01_stability").symlink_to(outside, target_is_directory=True)

    with pytest.raises(BuildRefusedError, match="symlink"):
        build_delivery(
            project_root=fixture_project,
            old_delivery=old,
            destination=destination,
            resume=True,
        )
    assert not tuple(outside.iterdir())


def test_old_baseline_is_captured_before_any_v2_write(
    fixture_project: Path,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "delivery-v2"
    with pytest.raises(BaselineError):
        build_delivery(
            project_root=fixture_project,
            old_delivery=tmp_path / "missing-old",
            destination=destination,
        )
    assert not destination.exists()


def test_old_delivery_baseline_detects_content_change(tmp_path: Path) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "original")
    baseline = capture_baseline(old)
    write_file(old / "README.md", "changed")
    assert compare_baseline(old, baseline).changed == ("README.md",)


def test_baseline_records_file_directory_and_symlink_without_following(
    tmp_path: Path,
) -> None:
    old = tmp_path / "old"
    write_file(old / "nested/data.txt", b"payload")
    (old / "alias").symlink_to("nested/data.txt")

    baseline = capture_baseline(old)
    by_path = {entry.relative_path: entry for entry in baseline.entries}
    assert by_path["nested"].path_type == "directory"
    assert by_path["nested/data.txt"].path_type == "file"
    assert by_path["nested/data.txt"].sha256
    assert by_path["alias"].path_type == "symlink"
    assert by_path["alias"].symlink_target == "nested/data.txt"


def test_baseline_detects_added_and_removed_paths(tmp_path: Path) -> None:
    old = tmp_path / "old"
    write_file(old / "keep.txt")
    write_file(old / "remove.txt")
    baseline = capture_baseline(old)
    (old / "remove.txt").unlink()
    write_file(old / "added.txt")

    difference = compare_baseline(old, baseline)
    assert difference.added == ("added.txt",)
    assert difference.removed == ("remove.txt",)


@pytest.mark.parametrize("replacement", ["directory", "symlink"])
def test_baseline_detects_file_type_changes(tmp_path: Path, replacement: str) -> None:
    old = tmp_path / "old"
    write_file(old / "node", b"file")
    baseline = capture_baseline(old)
    (old / "node").unlink()
    if replacement == "directory":
        (old / "node").mkdir()
    else:
        (old / "node").symlink_to("missing-target")

    assert compare_baseline(old, baseline).type_changed == ("node",)


def test_baseline_detects_directory_to_file_type_change(tmp_path: Path) -> None:
    old = tmp_path / "old"
    (old / "node").mkdir(parents=True)
    baseline = capture_baseline(old)
    (old / "node").rmdir()
    write_file(old / "node", b"file")
    assert compare_baseline(old, baseline).type_changed == ("node",)


def test_baseline_detects_symlink_retarget_without_following(tmp_path: Path) -> None:
    old = tmp_path / "old"
    write_file(old / "targets/a")
    write_file(old / "targets/b")
    (old / "alias").symlink_to("targets/a")
    baseline = capture_baseline(old)
    (old / "alias").unlink()
    (old / "alias").symlink_to("targets/b")

    difference = compare_baseline(old, baseline)
    assert difference.symlink_retargeted == ("alias",)
    assert difference.changed == ()


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_old_delivery_must_exist_as_a_real_directory(tmp_path: Path, kind: str) -> None:
    old = tmp_path / "old"
    if kind == "file":
        write_file(old)
    with pytest.raises(BaselineError):
        capture_baseline(old)


def mutate_old_delivery(old: Path, difference_class: str) -> None:
    if difference_class == "added":
        write_file(old / "added.txt")
    elif difference_class == "removed":
        (old / "README.md").unlink()
    elif difference_class == "changed":
        write_file(old / "README.md", "changed")
    elif difference_class == "file-to-directory":
        (old / "README.md").unlink()
        (old / "README.md").mkdir()
    elif difference_class == "file-to-symlink":
        (old / "README.md").unlink()
        (old / "README.md").symlink_to("target-a")
    elif difference_class == "symlink-retargeted":
        (old / "alias").unlink()
        (old / "alias").symlink_to("target-b")
    else:  # pragma: no cover - the parameter list is the closed mutation set
        raise AssertionError(difference_class)


@pytest.mark.parametrize(
    "difference_class",
    [
        "added",
        "removed",
        "changed",
        "file-to-directory",
        "file-to-symlink",
        "symlink-retargeted",
    ],
)
def test_old_package_delta_fails_before_candidate_acceptance(
    fixture_project: Path,
    tmp_path: Path,
    difference_class: str,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "original")
    (old / "alias").symlink_to("target-a")
    destination = tmp_path / "delivery-v2"
    plan = prepare_build(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    mutate_old_delivery(old, difference_class)

    result = execute_build(plan)
    assert result.exit_code != 0
    assert not result.publishable
    assert not result.baseline_difference.is_clean
    assert not destination.exists()


def test_old_package_mutation_after_copy_fails_before_publish_and_cleans_candidate(
    fixture_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "original")
    destination = tmp_path / "delivery-v2"
    plan = prepare_build(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    original_copy = builder_module._copy_asset
    mutated = False

    def copy_then_mutate(*args: object, **kwargs: object) -> None:
        nonlocal mutated
        original_copy(*args, **kwargs)
        if not mutated:
            write_file(old / "README.md", "changed after copy")
            mutated = True

    monkeypatch.setattr(builder_module, "_copy_asset", copy_then_mutate)
    result = execute_build(plan)

    assert mutated
    assert result.exit_code != 0
    assert not result.publishable
    assert result.baseline_difference.changed == ("README.md",)
    assert not destination.exists()
    assert not any(tmp_path.glob(".delivery-v2.staging-*"))


def test_resume_destination_mutation_during_copy_blocks_publication_and_is_preserved(
    fixture_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "original")
    destination = tmp_path / "delivery-v2"
    initial = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    assert initial.publishable
    original_tree = regular_tree_bytes(destination)
    original_identity = (destination.stat().st_dev, destination.stat().st_ino)
    plan = prepare_build(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    original_copy = builder_module._copy_asset
    mutated = False

    def copy_then_mutate(*args: object, **kwargs: object) -> None:
        nonlocal mutated
        original_copy(*args, **kwargs)
        if not mutated:
            write_file(destination / "concurrent/keep-me.txt", b"concurrent")
            mutated = True

    monkeypatch.setattr(builder_module, "_copy_asset", copy_then_mutate)
    result = execute_build(plan, resume=True)

    assert mutated
    assert result.exit_code != 0
    assert not result.publishable
    assert "destination-changed-before-publish" in result.reason
    assert (destination.stat().st_dev, destination.stat().st_ino) == original_identity
    actual_tree = regular_tree_bytes(destination)
    assert actual_tree.pop("concurrent/keep-me.txt") == b"concurrent"
    assert actual_tree == original_tree
    assert not tuple(tmp_path.glob(".delivery-v2.backup-*"))
    assert not tuple(tmp_path.glob(".delivery-v2.quarantine-*"))


def test_destination_mutation_in_publish_window_is_restored_without_publication(
    fixture_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "original")
    destination = tmp_path / "delivery-v2"
    initial = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    assert initial.publishable
    original_tree = regular_tree_bytes(destination)
    plan = prepare_build(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    real_publish = builder_module._publish_staging

    def mutate_then_publish(*args: object, **kwargs: object) -> Path | None:
        write_file(destination / "late.txt", b"late concurrent write")
        return real_publish(*args, **kwargs)

    monkeypatch.setattr(builder_module, "_publish_staging", mutate_then_publish)
    result = execute_build(plan, resume=True)

    assert result.exit_code != 0
    assert not result.publishable
    assert "destination-changed-during-publish" in result.reason
    actual_tree = regular_tree_bytes(destination)
    assert actual_tree.pop("late.txt") == b"late concurrent write"
    assert actual_tree == original_tree
    assert not tuple(tmp_path.glob(".delivery-v2.backup-*"))


def test_publish_and_backup_restore_failure_reports_retained_old_tree(
    fixture_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "original")
    destination = tmp_path / "delivery-v2"
    initial = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    assert initial.publishable
    previous_tree = regular_tree_bytes(destination)
    plan = prepare_build(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    real_replace = builder_module.os.replace

    def fail_publish_and_restore(source: object, target: object) -> None:
        source_path = Path(source)
        target_path = Path(target)
        if target_path == destination and (
            source_path.name.startswith(".delivery-v2.staging-")
            or source_path.name.startswith(".delivery-v2.backup-")
        ):
            raise OSError("publish/restore unavailable")
        real_replace(source, target)

    monkeypatch.setattr(builder_module.os, "replace", fail_publish_and_restore)
    result = execute_build(plan, resume=True)

    assert result.exit_code != 0
    assert not result.publishable
    assert result.recovery_status == "manual-recovery-required"
    assert not destination.exists()
    backups = tuple(tmp_path.glob(".delivery-v2.backup-*"))
    assert len(backups) == 1
    assert regular_tree_bytes(backups[0]) == previous_tree
    assert str(backups[0]) in result.recovery_paths


@pytest.mark.parametrize("rollback_mode", ["once", "persistent"])
def test_post_publish_gate_failure_recovers_after_rollback_error(
    fixture_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rollback_mode: str,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "original")
    destination = tmp_path / "delivery-v2"
    initial = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    assert initial.publishable
    previous_tree = regular_tree_bytes(destination)
    plan = prepare_build(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    real_publish = builder_module._publish_staging
    real_rollback = builder_module._rollback_publication
    rollback_calls = 0

    def publish_then_mutate(*args: object, **kwargs: object) -> Path | None:
        backup = real_publish(*args, **kwargs)
        write_file(old / "README.md", "changed after publish")
        return backup

    def failing_rollback(formal: Path, backup: Path | None) -> None:
        nonlocal rollback_calls
        rollback_calls += 1
        if rollback_mode == "persistent" or rollback_calls == 1:
            raise OSError(f"rollback {rollback_mode} failure")
        real_rollback(formal, backup)

    monkeypatch.setattr(builder_module, "_publish_staging", publish_then_mutate)
    monkeypatch.setattr(builder_module, "_rollback_publication", failing_rollback)
    result = execute_build(plan, resume=True)

    assert rollback_calls >= 1
    assert result.exit_code != 0
    assert not result.publishable
    assert regular_tree_bytes(destination) == previous_tree
    quarantines = tuple(tmp_path.glob(".delivery-v2.quarantine-*"))
    assert len(quarantines) == 1
    assert regular_tree_bytes(quarantines[0])
    assert result.recovery_status == "previous-destination-restored-after-rollback-error"
    assert str(quarantines[0]) in result.recovery_paths
    assert not tuple(tmp_path.glob(".delivery-v2.backup-*"))


def test_failed_backup_restore_preserves_backup_and_quarantines_new_tree(
    fixture_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "original")
    destination = tmp_path / "delivery-v2"
    initial = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    assert initial.publishable
    previous_tree = regular_tree_bytes(destination)
    plan = prepare_build(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    real_publish = builder_module._publish_staging
    real_replace = builder_module.os.replace

    def publish_then_mutate(*args: object, **kwargs: object) -> Path | None:
        backup = real_publish(*args, **kwargs)
        write_file(old / "README.md", "changed after publish")
        return backup

    def always_fail_rollback(formal: Path, backup: Path | None) -> None:
        raise OSError("primary rollback unavailable")

    def fail_backup_restore(source: object, target: object) -> None:
        source_path = Path(source)
        target_path = Path(target)
        if (
            source_path.name.startswith(".delivery-v2.backup-")
            and target_path == destination
        ):
            raise OSError("backup restore unavailable")
        real_replace(source, target)

    monkeypatch.setattr(builder_module, "_publish_staging", publish_then_mutate)
    monkeypatch.setattr(builder_module, "_rollback_publication", always_fail_rollback)
    monkeypatch.setattr(builder_module.os, "replace", fail_backup_restore)
    result = execute_build(plan, resume=True)

    assert result.exit_code != 0
    assert not result.publishable
    assert result.recovery_status == "manual-recovery-required"
    assert not destination.exists()
    backups = tuple(tmp_path.glob(".delivery-v2.backup-*"))
    quarantines = tuple(tmp_path.glob(".delivery-v2.quarantine-*"))
    assert len(backups) == 1
    assert len(quarantines) == 1
    assert regular_tree_bytes(backups[0]) == previous_tree
    assert set(result.recovery_paths) == {str(backups[0]), str(quarantines[0])}


def test_post_publish_failure_without_prior_destination_leaves_formal_path_empty(
    fixture_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "original")
    destination = tmp_path / "delivery-v2"
    plan = prepare_build(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    real_publish = builder_module._publish_staging

    def publish_then_mutate(*args: object, **kwargs: object) -> Path | None:
        backup = real_publish(*args, **kwargs)
        write_file(old / "README.md", "changed after publish")
        return backup

    monkeypatch.setattr(builder_module, "_publish_staging", publish_then_mutate)
    result = execute_build(plan)

    assert result.exit_code != 0
    assert not result.publishable
    assert not destination.exists()
    quarantines = tuple(tmp_path.glob(".delivery-v2.quarantine-*"))
    assert len(quarantines) == 1
    assert result.recovery_status == "empty-destination-restored"
    assert result.recovery_paths == (str(quarantines[0]),)


def test_backup_cleanup_failure_keeps_valid_publication_and_retains_backup(
    fixture_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = tmp_path / "old"
    write_file(old / "README.md", "original")
    destination = tmp_path / "delivery-v2"
    initial = build_delivery(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    assert initial.publishable
    prior_tree = regular_tree_bytes(destination)
    plan = prepare_build(
        project_root=fixture_project,
        old_delivery=old,
        destination=destination,
    )
    real_remove_tree = builder_module._remove_tree

    def fail_backup_cleanup(path: Path) -> None:
        if path.name.startswith(".delivery-v2.backup-"):
            raise OSError("backup cleanup unavailable")
        real_remove_tree(path)

    monkeypatch.setattr(builder_module, "_remove_tree", fail_backup_cleanup)
    result = execute_build(plan, resume=True)

    assert result.exit_code == 0
    assert result.publishable
    assert result.recovery_status == "published-backup-retained"
    assert regular_tree_bytes(destination) == prior_tree
    backups = tuple(tmp_path.glob(".delivery-v2.backup-*"))
    assert len(backups) == 1
    assert result.recovery_paths == (str(backups[0]),)
    assert not tuple(tmp_path.glob(".delivery-v2.quarantine-*"))


def task4_pipeline_fixture(
    tmp_path: Path,
) -> tuple[Path, tuple[ExactSourceSpec, ...], DerivedRecipe, RedrawRecipe]:
    project = tmp_path / "project"
    producer_source = (
        Path(__file__).parents[2]
        / "95_shared_scripts/handoff_delivery/derived.py"
    )
    producer_target = project / "95_shared_scripts/handoff_delivery/derived.py"
    write_file(producer_target, producer_source.read_bytes())

    source = project / "source/field.npz"
    source.parent.mkdir(parents=True)
    np.savez(source, field=np.arange(24, dtype=np.float64).reshape(2, 2, 2, 3))
    expected = (
        b"x,y,mx,mz\n"
        b"11,22,3,5\n"
        b"11,26,9,11\n"
        b"13,22,15,17\n"
        b"13,26,21,23\n"
    )
    derived = DerivedRecipe(
        recipe_id="derive-fig-a-slice",
        output_data_id="data-fig-a-slice",
        source_path="source/field.npz",
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        producer_script="95_shared_scripts/handoff_delivery/derived.py",
        producer_sha256=hashlib.sha256(producer_target.read_bytes()).hexdigest(),
        selector_kind="slice",
        selector_json=json.dumps(
            {"array": "field", "axis": 2, "components": [0, 2], "index": 1},
            sort_keys=True,
            separators=(",", ":"),
        ),
        output_path="02_dynamics/data/fig-a-slice.csv",
        output_format="csv",
        output_sha256=hashlib.sha256(expected).hexdigest(),
        shape="2x2x2",
        columns="x;y;mx;mz",
        units="nm;nm;1;1",
        coordinate_origin="10;20;30",
        coordinate_spacing="2;4;6",
        coordinate_units="nm;nm;nm",
        parent_figure_ids="fig-a",
        parent_data_ids="source-field-a",
        environment_command=HOPFION_ENVIRONMENT_COMMAND,
        is_complete_field="false",
        notes="bounded slice used only by fig-a",
    )

    python = str(Path(sys.executable).resolve())
    write_file(
        project / "assets/redraw.py",
        "from pathlib import Path\n"
        "import numpy as np\n"
        "import sys\n"
        "source = np.genfromtxt(sys.argv[1], delimiter=',', names=True)\n"
        "target = Path(sys.argv[2])\n"
        "target.parent.mkdir(parents=True, exist_ok=True)\n"
        "np.savetxt(target, source['value'] * 2.0, delimiter=',', header='value', comments='')\n",
    )
    write_file(project / "assets/input.csv", "value\n1\n2\n3\n")
    write_file(project / "assets/reference.csv", "value\n2\n4\n6\n")
    exact_specs = (
        ExactSourceSpec("assets/redraw.py", "scripts/redraw.py"),
        ExactSourceSpec("assets/input.csv", "data/input.csv"),
        ExactSourceSpec("assets/reference.csv", "reference/output.csv"),
    )
    redraw_recipe = RedrawRecipe(
        redraw_id="redraw-fig-a",
        figure_id="fig-a",
        module="02_spinwave_control",
        script_path="scripts/redraw.py",
        command=f"{python} scripts/redraw.py data/input.csv redraw/output.csv",
        input_data_ids="data-fig-a-slice",
        input_paths="data/input.csv",
        output_path="redraw/output.csv",
        reference_product_path="reference/output.csv",
        comparison_method="numpy.testing.assert_allclose",
        tolerance="rtol=1e-12;atol=1e-12",
        environment_command=python,
        representative=True,
        notes="builder integration redraw",
    )
    return project, exact_specs, derived, redraw_recipe


def task4_figure_recipe(
    source_path: str,
    *,
    figure_id: str = "fig-formal-a",
    scientific_status: str = "unverified",
    reproducibility: str = "source_identity_reviewed",
) -> FigureRecipe:
    return FigureRecipe(
        figure_id=figure_id,
        usage_status="formal",
        scientific_status=scientific_status,
        provenance_type="external",
        story_module="05_papers_and_talks",
        claim_or_purpose="fixture figure",
        figure_path=source_path,
        figure_sha256="a" * 64,
        plot_script_path="N/A",
        plot_command="N/A",
        input_data_ids="N/A",
        parent_data_ids="N/A",
        derived_data_ids="N/A",
        run_ids="N/A",
        theory_asset_ids="N/A",
        initial_state_recipe_id="N/A",
        reproducibility=reproducibility,
        source_document_ids="doc-a",
        comparison_reference_data_id="N/A",
        comparison_method="source_identity_review",
        tolerance="N/A",
        notes="source_locator=doi:10.0000/fixture:Fig.1",
    )


def test_prepare_build_loads_real_ledger_hook_and_routes_nonactive_figure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    source_path = "figures/formal.png"
    write_file(project / source_path, b"figure")
    unregistered_path = "figures/old-result.png"
    write_file(project / unregistered_path, b"old figure")
    write_file(
        project / "95_shared_scripts/handoff_delivery/figure_recipes.csv",
        "fixture ledger marker\n",
    )
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    figure_row = task4_figure_recipe(source_path)
    monkeypatch.setattr(
        builder_module,
        "validate_recipe_ledger",
        lambda _project: (figure_row,),
    )
    monkeypatch.setattr(builder_module, "_validate_lineage_preflight", lambda _plan: None)

    with (
        patch.object(
            builder_module,
            "_validate_canonical_portable_ledgers_at_root",
            return_value=None,
        ),
        patch.object(builder_module, "_validate_portable_preflight", return_value=None),
    ):
        plan = builder_module.prepare_build(
            project_root=project,
            old_delivery=old,
            destination=tmp_path / "delivery-v2",
            tree_specs=(),
            exact_specs=(
                ExactSourceSpec(
                    source_path,
                    "05_papers_and_talks/thesis_final/figures/formal.png",
                ),
                ExactSourceSpec(
                    unregistered_path,
                    "05_papers_and_talks/thesis_final/figures/old-result.png",
                ),
            ),
            include_thesis_assets=False,
            portable_contract=SimpleNamespace(transforms=(), runtime_entries=()),
        )

    assert plan.figure_recipes == (figure_row,)
    routed = {row.source_path: row for row in plan.required_assets}[source_path]
    assert routed.disposition == "copied_archive"
    assert routed.expected_target_class == "archive"
    assert routed.target_path == (
        "90_archive/historical_figures/fig-formal-a/formal.png"
    )
    excluded = {row.source_path: row for row in plan.required_assets}[
        unregistered_path
    ]
    assert excluded.disposition == "excluded_with_reason"
    assert excluded.expected_target_class == "excluded"
    assert excluded.target_path is None
    assert excluded.reason == "unregistered-noncanonical-figure"


def test_manifest_registered_pdf_outside_figures_directory_is_a_figure() -> None:
    source_path = "reports/declared-plot.pdf"
    payload = b"declared figure PDF"
    asset = RequiredAssetRow(
        source_path=source_path,
        target_path="05_papers_and_talks/reports/declared-plot.pdf",
        disposition="copied_active",
        expected_target_class="active",
        reason="fixture",
        sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload),
        file_type="document",
    )
    figure_row = task4_figure_recipe(source_path)

    routed = builder_module._route_figure_assets(
        RequiredAssetInventory((asset,)),
        (figure_row,),
    )

    assert routed.rows[0].disposition == "copied_archive"
    assert routed.rows[0].target_path == (
        "90_archive/historical_figures/fig-formal-a/declared-plot.pdf"
    )


def test_prepare_build_requires_the_canonical_figure_ledger_by_default(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    write_file(project / "asset.txt")
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")

    with (
        patch.object(
            builder_module,
            "_validate_canonical_portable_ledgers_at_root",
            return_value=None,
        ),
        pytest.raises(BuildRefusedError, match="figure recipe ledger is missing"),
    ):
        builder_module.prepare_build(
            project_root=project,
            old_delivery=old,
            destination=tmp_path / "delivery-v2",
            tree_specs=(),
            exact_specs=(ExactSourceSpec("asset.txt", "shared/asset.txt"),),
            include_thesis_assets=False,
            portable_contract=SimpleNamespace(transforms=(), runtime_entries=()),
        )

    with pytest.raises(TypeError, match="figure_recipes"):
        builder_module.prepare_build(
            project_root=project,
            old_delivery=old,
            destination=tmp_path / "fixture-delivery",
            tree_specs=(),
            exact_specs=(ExactSourceSpec("asset.txt", "shared/asset.txt"),),
            include_thesis_assets=False,
            figure_recipes=(),
        )


def test_execute_build_revalidates_and_rejects_an_unregistered_figure_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    payload = b"unregistered figure"
    write_file(project / "figures/unregistered.png", payload)
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    destination = tmp_path / "delivery-v2"
    asset = RequiredAssetRow(
        source_path="figures/unregistered.png",
        target_path="01_stability/unregistered.png",
        disposition="copied_active",
        expected_target_class="active",
        reason="malformed-manual-plan",
        sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload),
        file_type="image",
    )
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=destination,
        required_assets=RequiredAssetInventory((asset,)),
        old_baseline=capture_baseline(old),
        figure_recipes=(),
    )
    monkeypatch.setattr(
        builder_module,
        "_load_project_figure_recipes",
        lambda _project_root: (),
    )
    monkeypatch.setattr(
        builder_module,
        "_validate_portable_preflight",
        lambda _plan: None,
    )

    with patch.object(
        builder_module, "_validate_portable_preflight", return_value=None
    ):
        result = builder_module.execute_build(plan)

    assert not result.publishable
    assert result.exit_code != 0
    assert "figure coverage" in result.reason
    assert not destination.exists()


def test_execute_build_reloads_canonical_ledger_for_a_manual_empty_plan(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    destination = tmp_path / "delivery-v2"
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=destination,
        required_assets=RequiredAssetInventory(()),
        old_baseline=capture_baseline(old),
        figure_recipes=(),
    )

    with patch.object(
        builder_module, "_validate_portable_preflight", return_value=None
    ):
        result = builder_module.execute_build(plan)

    assert not result.publishable
    assert result.exit_code != 0
    assert "figure recipe ledger is missing" in result.reason
    assert not destination.exists()


def test_lineage_preflight_rejects_empty_real_redraw_and_derived_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    asset = RequiredAssetRow(
        source_path="figures/formal.png",
        target_path="05_papers_and_talks/formal.png",
        disposition="copied_active",
        expected_target_class="active",
        reason="fixture",
        sha256="a" * 64,
        size=1,
        file_type="image",
    )
    ordinary = task4_figure_recipe(
        "figures/formal.png",
        scientific_status="not_applicable",
    )
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=tmp_path / "delivery-v2",
        required_assets=RequiredAssetInventory((asset,)),
        old_baseline=capture_baseline(old),
        figure_recipes=(ordinary,),
    )
    with pytest.raises(BuildRefusedError, match="redraw plan"):
        builder_module._validate_lineage_preflight(plan)

    pending = replace(
        ordinary,
        scientific_status="valid",
        provenance_type="theory",
        plot_script_path="scripts/plot.py",
        plot_command="python3 scripts/plot.py data/needed.csv redraw/check.csv",
        input_data_ids="data-needed",
        parent_data_ids="data-parent",
        derived_data_ids="data-needed",
        theory_asset_ids="asset-theory",
        reproducibility="minimal_projection_derivation_pending",
        comparison_method="numpy.testing.assert_allclose",
        tolerance="rtol=1e-7;atol=1e-10",
    )
    pending_plan = replace(plan, figure_recipes=(pending,))
    with pytest.raises(BuildRefusedError, match="derived recipe coverage"):
        builder_module._validate_lineage_preflight(pending_plan)

    monkeypatch.setattr(
        builder_module,
        "validate_derived_preflight",
        lambda _recipes, project_root: None,
    )
    unrelated = SimpleNamespace(
        recipe_id="derive-unrelated",
        source_path="source/field.npy",
        output_path="data/unrelated.csv",
        output_data_id="data-unrelated",
        parent_figure_ids=pending.figure_id,
        parent_data_ids="data-parent",
    )
    with pytest.raises(BuildRefusedError, match="unrelated output_data_id"):
        builder_module._validate_lineage_preflight(
            replace(pending_plan, derived_recipes=(unrelated,))
        )

    matched = SimpleNamespace(
        recipe_id="derive-needed",
        source_path="source/field.npy",
        output_path="data/needed.csv",
        output_data_id="data-needed",
        parent_figure_ids=pending.figure_id,
        parent_data_ids="data-parent",
    )
    with pytest.raises(BuildRefusedError, match="redraw plan"):
        builder_module._validate_lineage_preflight(
            replace(pending_plan, derived_recipes=(matched,))
        )


def test_lineage_preflight_rejects_a_figure_without_one_packaged_target(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    figure = task4_figure_recipe(
        "figures/formal.png",
        scientific_status="not_applicable",
    )
    excluded = RequiredAssetRow(
        source_path=figure.figure_path,
        target_path=None,
        disposition="excluded_with_reason",
        expected_target_class="excluded",
        reason="fixture",
        sha256="a" * 64,
        size=1,
        file_type="image",
    )
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=tmp_path / "delivery-v2",
        required_assets=RequiredAssetInventory((excluded,)),
        old_baseline=capture_baseline(old),
        figure_recipes=(figure,),
    )

    with pytest.raises(BuildRefusedError, match="figure rows without packaged assets"):
        builder_module._validate_lineage_preflight(plan)


def test_lineage_preflight_accepts_routed_script_and_absolute_python_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    figure = FigureRecipe(
        figure_id="fig-routed",
        usage_status="formal",
        scientific_status="valid",
        provenance_type="theory",
        story_module="02_spinwave_control",
        claim_or_purpose="Routed executable fixture.",
        figure_path="source/figure.png",
        figure_sha256="a" * 64,
        plot_script_path="source/plot.py",
        plot_command="python3 source/plot.py source/input.npy redraw/output.npy",
        input_data_ids="data-input",
        parent_data_ids="data-input",
        derived_data_ids="N/A",
        run_ids="N/A",
        theory_asset_ids="theory-a",
        initial_state_recipe_id="N/A",
        reproducibility="fully_reproducible",
        source_document_ids="N/A",
        comparison_reference_data_id="data-reference",
        comparison_method="numpy.testing.assert_allclose",
        tolerance="rtol=1e-12;atol=1e-12",
        notes="Builder normalization fixture.",
    )
    required = RequiredAssetInventory(
        tuple(
            RequiredAssetRow(
                source_path=source,
                target_path=target,
                disposition="copied_active",
                expected_target_class="active",
                reason="fixture",
                sha256=sha,
                size=1,
                file_type=file_type,
            )
            for source, target, sha, file_type in (
                ("source/figure.png", "02_spinwave_control/topic/figure.png", "a" * 64, "image"),
                ("source/plot.py", "shared/plotting/plot.py", "b" * 64, "code"),
                ("source/input.npy", "shared/data/input.npy", "c" * 64, "data"),
                ("source/reference.npy", "shared/data/reference.npy", "d" * 64, "data"),
            )
        )
    )
    python = str(Path(sys.executable).resolve())
    redraw = RedrawRecipe(
        redraw_id="redraw-routed",
        figure_id=figure.figure_id,
        module=figure.story_module,
        script_path="shared/plotting/plot.py",
        command=(
            f"{python} shared/plotting/plot.py shared/data/input.npy "
            "redraw/output.npy"
        ),
        input_data_ids="data-input",
        input_paths="shared/data/input.npy",
        output_path="redraw/output.npy",
        reference_product_path="shared/data/reference.npy",
        comparison_method="numpy.testing.assert_allclose",
        tolerance="rtol=1e-12;atol=1e-12",
        environment_command=python,
        representative=True,
        notes="Execute a routed script with the pinned absolute Python.",
    )
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=tmp_path / "delivery-v2",
        required_assets=required,
        old_baseline=capture_baseline(old),
        figure_recipes=(figure,),
        redraw_recipes=(redraw,),
        manifest_keys=ManifestKeys(
            data_ids=frozenset(("data-input", "data-reference")),
            theory_asset_ids=frozenset(("theory-a",)),
            data_paths={
                "data-input": "shared/data/input.npy",
                "data-reference": "shared/data/reference.npy",
            },
        ),
    )
    production_validate = builder_module.validate_redraw_plan

    def validate_one_module(figures, recipes, **kwargs):
        assert kwargs["executable_fields_prevalidated"] is True
        return production_validate(
            figures,
            recipes,
            required_modules=("02_spinwave_control",),
            **kwargs,
        )

    monkeypatch.setattr(builder_module, "validate_redraw_plan", validate_one_module)

    builder_module._validate_lineage_preflight(plan)


def test_builder_materializes_only_fresh_derived_outputs_and_redraw_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, exact_specs, derived, redraw_recipe = task4_pipeline_fixture(tmp_path)
    old = tmp_path / "old"
    write_file(old / "README.md", "old package\n")
    destination = tmp_path / "delivery-v2"

    def reject_in_process_production(*_args: object, **_kwargs: object):
        raise AssertionError("builder must execute the pinned producer environment")

    monkeypatch.setattr(
        builder_module,
        "produce_derived",
        reject_in_process_production,
    )

    result = build_delivery(
        project_root=project,
        old_delivery=old,
        destination=destination,
        tree_specs=(),
        exact_specs=exact_specs,
        include_thesis_assets=False,
        derived_recipes=(derived,),
        redraw_recipes=(redraw_recipe,),
    )

    assert result.exit_code == 0
    assert result.publishable
    assert (destination / derived.output_path).is_file()
    assert hashlib.sha256(
        (destination / derived.output_path).read_bytes()
    ).hexdigest() == derived.output_sha256
    assert not (destination / ".handoff-staging").exists()
    derived_evidence = destination / "00_handoff/DERIVED_DATA_EVIDENCE.csv"
    redraw_evidence = destination / "00_handoff/FIGURE_REDRAW_EVIDENCE.csv"
    assert derived_evidence.is_file()
    assert redraw_evidence.is_file()
    with derived_evidence.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["source_sha256"] == derived.source_sha256
    assert row["producer_sha256"] == derived.producer_sha256
    assert row["output_sha256"] == derived.output_sha256
    assert row["selector_json"] == derived.selector_json
    assert row["coordinate_origin"] == derived.coordinate_origin
    assert row["coordinate_spacing"] == derived.coordinate_spacing
    assert row["coordinate_units"] == derived.coordinate_units
    assert old.joinpath("README.md").read_text(encoding="utf-8") == "old package\n"
    assert not tuple(tmp_path.glob(".delivery-v2.staging-*"))
    assert not tuple(tmp_path.glob(".delivery-v2.derived-*"))


def test_builder_rejects_untracked_file_created_by_derived_producer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, exact_specs, derived, _ = task4_pipeline_fixture(tmp_path)
    old = tmp_path / "old"
    write_file(old / "README.md", "old package\n")
    destination = tmp_path / "delivery-v2"
    real_produce = builder_module.produce_derived_in_environment

    def produce_with_untracked(*args: object, **kwargs: object):
        evidence = real_produce(*args, **kwargs)
        output_root = Path(kwargs["output_root"])
        write_file(output_root / "untracked/hand-authored.csv", "bad\n")
        return evidence

    monkeypatch.setattr(
        builder_module,
        "produce_derived_in_environment",
        produce_with_untracked,
    )
    result = build_delivery(
        project_root=project,
        old_delivery=old,
        destination=destination,
        tree_specs=(),
        exact_specs=exact_specs,
        include_thesis_assets=False,
        derived_recipes=(derived,),
    )

    assert result.exit_code != 0
    assert not result.publishable
    assert "untracked derived outputs" in result.reason
    assert not destination.exists()
    assert not tuple(tmp_path.glob(".delivery-v2.staging-*"))
    assert not tuple(tmp_path.glob(".delivery-v2.derived-*"))


def test_task6_finalizer_refuses_failed_gate_before_report_checksum_or_promotion(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=tmp_path / "delivery",
        required_assets=RequiredAssetInventory(()),
        old_baseline=capture_baseline(old),
        portable_contract=SimpleNamespace(transforms=(), runtime_entries=()),
        tree_specs=(),
        exact_specs=(),
        include_thesis_assets=False,
    )
    staging = tmp_path / "staging"
    write_file(staging / "00_handoff/PORTABLE_CONFIG.toml", '[paths]\nwork="runtime"\n')
    materialized = builder_module._pin_staging_pipeline_result(staging, ())
    failed = (VerificationResult("G1", False, (("files", 1),), ("field found",), ()),)

    try:
        with patch.object(builder_module, "verify", return_value=failed):
            with pytest.raises(BuildRefusedError, match="G1"):
                builder_module._finalize_verified_staging(plan, staging, materialized)
    finally:
        os.close(materialized.staging_descriptor)
    assert not (staging / "00_handoff/verification_report.json").exists()
    assert not (staging / "00_handoff/SHA256SUMS.txt").exists()
    assert not plan.destination.exists()


def test_task6_finalizer_writes_report_then_checksum_and_rebuilds_same_fd_snapshot(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=tmp_path / "delivery",
        required_assets=RequiredAssetInventory(()),
        old_baseline=capture_baseline(old),
        portable_contract=SimpleNamespace(),
        tree_specs=(),
        exact_specs=(),
        include_thesis_assets=False,
    )
    staging = tmp_path / "staging"
    write_file(staging / "00_handoff/PORTABLE_CONFIG.toml", '[paths]\nwork="runtime"\n')
    materialized = builder_module._pin_staging_pipeline_result(staging, ())
    passed = tuple(
        VerificationResult(gate, True, (("checked", 1),), (), ("00_handoff",))
        for gate in ("G1", "G2", "G3", "G4", "G5")
    )
    events: list[str] = []
    real_report = builder_module.write_report
    real_checksums = builder_module.write_checksums

    def report(*args, **kwargs):
        events.append("report")
        return real_report(*args, **kwargs)

    def checksums(*args, **kwargs):
        events.append("checksum")
        return real_checksums(*args, **kwargs)

    with (
        patch.object(builder_module, "verify", return_value=passed) as verify_mock,
        patch.object(builder_module, "write_report", side_effect=report),
        patch.object(builder_module, "write_checksums", side_effect=checksums),
    ):
        finalized = builder_module._finalize_verified_staging(
            plan, staging, materialized
        )
    try:
        assert events == ["report", "checksum"]
        assert verify_mock.call_args.kwargs["expected_derived_recipes"] == ()
        assert finalized.descriptor == materialized.staging_descriptor
        final_paths = {row.relative_path for row in finalized.snapshot}
        assert "00_handoff/verification_report.json" in final_paths
        assert "00_handoff/SHA256SUMS.txt" in final_paths
        assert final_paths > {row.relative_path for row in materialized.staging_snapshot}
        listed = {
            line.split("  ", 1)[1]
            for line in (staging / "00_handoff/SHA256SUMS.txt")
            .read_text(encoding="utf-8")
            .splitlines()
        }
        assert "00_handoff/verification_report.json" in listed
        assert "00_handoff/SHA256SUMS.txt" not in listed
    finally:
        finalized.close()


def test_task6_finalizer_rejects_existing_file_rewrite_after_gate_pass(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=tmp_path / "delivery",
        required_assets=RequiredAssetInventory(()),
        old_baseline=capture_baseline(old),
        portable_contract=SimpleNamespace(),
        tree_specs=(),
        exact_specs=(),
        include_thesis_assets=False,
    )
    staging = tmp_path / "staging"
    config = staging / "00_handoff/PORTABLE_CONFIG.toml"
    write_file(config, '[paths]\nwork="runtime"\n')
    materialized = builder_module._pin_staging_pipeline_result(staging, ())
    passed = tuple(
        VerificationResult(gate, True, (("checked", 1),), (), ("00_handoff",))
        for gate in ("G1", "G2", "G3", "G4", "G5")
    )

    def mutate_then_pass(*_args, **_kwargs):
        original = config.read_bytes()
        config.write_bytes(original.replace(b"runtime", b"changed"))
        assert config.stat().st_size == len(original)
        return passed

    try:
        with patch.object(builder_module, "verify", side_effect=mutate_then_pass):
            with pytest.raises(BuildRefusedError, match="snapshot"):
                builder_module._finalize_verified_staging(plan, staging, materialized)
    finally:
        os.close(materialized.staging_descriptor)


@pytest.mark.parametrize("evidence_name", ["report", "checksum"])
def test_task6_finalizer_rejects_equal_length_evidence_tampering(
    tmp_path: Path, evidence_name: str,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=tmp_path / "delivery",
        required_assets=RequiredAssetInventory(()),
        old_baseline=capture_baseline(old),
        portable_contract=SimpleNamespace(),
        tree_specs=(),
        exact_specs=(),
        include_thesis_assets=False,
    )
    staging = tmp_path / "staging"
    write_file(staging / "00_handoff/PORTABLE_CONFIG.toml", '[paths]\nwork="runtime"\n')
    materialized = builder_module._pin_staging_pipeline_result(staging, ())
    passed = tuple(
        VerificationResult(gate, True, (("checked", 1),), (), ("00_handoff/README.md",))
        for gate in ("G1", "G2", "G3", "G4", "G5")
    )
    real_checksums = builder_module.write_checksums

    def checksums_then_tamper(*args, **kwargs):
        result = real_checksums(*args, **kwargs)
        target = (
            staging / "00_handoff/verification_report.json"
            if evidence_name == "report"
            else staging / "00_handoff/SHA256SUMS.txt"
        )
        payload = target.read_bytes()
        os.chmod(target, 0o644)
        target.write_bytes(bytes([payload[0] ^ 1]) + payload[1:])
        assert target.stat().st_size == len(payload)
        return result

    try:
        with (
            patch.object(builder_module, "verify", return_value=passed),
            patch.object(
                builder_module, "write_checksums", side_effect=checksums_then_tamper
            ),
        ):
            with pytest.raises(BuildRefusedError, match="deterministic payload"):
                builder_module._finalize_verified_staging(plan, staging, materialized)
    finally:
        os.close(materialized.staging_descriptor)


def test_execute_build_never_calls_publisher_when_task6_gate_fails_and_cleans_staging(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    old = tmp_path / "old"
    write_file(old / "README.md", "old\n")
    destination = tmp_path / "delivery"
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=destination,
        required_assets=RequiredAssetInventory(()),
        old_baseline=capture_baseline(old),
        portable_contract=SimpleNamespace(transforms=(), runtime_entries=()),
        tree_specs=(),
        exact_specs=(),
        include_thesis_assets=False,
    )
    failed = (VerificationResult("G3", False, (), ("missing source",), ()),)
    descriptors: list[int] = []
    published = False

    def materialize(_plan: BuildPlan, staging: Path):
        result = builder_module._pin_staging_pipeline_result(staging, ())
        descriptors.append(result.staging_descriptor)
        return result

    def publish(*_args, **_kwargs):
        nonlocal published
        published = True
        raise AssertionError("failed verification must never reach publication")

    with (
        patch.object(builder_module, "_validate_portable_preflight", return_value=None),
        patch.object(builder_module, "_validate_canonical_figure_plan", return_value=None),
        patch.object(builder_module, "_validate_lineage_preflight", return_value=None),
        patch.object(builder_module, "_materialize_portable_pipeline", side_effect=materialize),
        patch.object(builder_module, "verify", return_value=failed),
        patch.object(builder_module, "_publish_staging", side_effect=publish),
    ):
        result = _production_execute_build(plan)

    assert result.exit_code != 0
    assert not result.publishable
    assert "G3" in result.reason
    assert not published
    assert not destination.exists()
    assert not tuple(tmp_path.glob(".delivery.staging-*"))
    assert len(descriptors) == 1
    with pytest.raises(OSError):
        os.fstat(descriptors[0])
