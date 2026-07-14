from __future__ import annotations

import hashlib
from pathlib import Path
import zipfile

import pytest

import handoff_delivery.builder as builder_module
import handoff_delivery.source_specs as source_specs_module
from handoff_delivery.builder import (
    BaselineError,
    BuildPlan,
    BuildRefusedError,
    build_delivery,
    capture_baseline,
    compare_baseline,
    execute_build,
    prepare_build,
)
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
