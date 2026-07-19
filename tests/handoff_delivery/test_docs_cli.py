from __future__ import annotations

from pathlib import Path
import importlib.util
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

import handoff_delivery.builder as builder_module
from handoff_delivery.docs import (
    DocumentationError,
    load_docs_config,
    package_verifier_assets,
    package_verifier_script,
    render_documents,
)
from handoff_delivery.builder import (
    BaselineDifference,
    BaselineSnapshot,
    BuildPlan,
    BuildResult,
)
from handoff_delivery.source_specs import RequiredAssetInventory
from handoff_delivery.portable import PortableContract
from handoff_delivery.source_specs import ExactSourceSpec, TreeSourceSpec
from handoff_delivery.cli import main
from handoff_delivery.verifier import (
    VerificationResult,
    write_checksums,
    write_report,
)


TOPIC_SECTIONS = (
    "研究问题",
    "当前状态",
    "有效/无效结论",
    "数据与代码入口",
    "复现级别",
)


def _write_config(path: Path, *, source_path: str = "evidence/source.md") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'''version = 1

[[documents]]
document_id = "topic-stability"
document_type = "topic"
target_path = "01_stability/topic/README.md"
title = "稳定性主题"
reading_order = 10

[[claims]]
claim_id = "question"
document_id = "topic-stability"
section = "研究问题"
text = "这个 Hopfion 初态在目标参数下是否稳定？"
source_path = "{source_path}"
source_locator = "L1"
integrity_status = "source_backed"
warning = ""
reading_order = 10

[[claims]]
claim_id = "status"
document_id = "topic-stability"
section = "当前状态"
text = "本交付仅核对既有证据，不运行新仿真。"
source_path = "N/A"
source_locator = "N/A"
integrity_status = "inference"
warning = "推断：这是本次交付范围说明，不是仿真结论。"
reading_order = 20

[[claims]]
claim_id = "conclusion"
document_id = "topic-stability"
section = "有效/无效结论"
text = "有效结论以已登记证据为限。"
source_path = "{source_path}"
source_locator = "L2"
integrity_status = "source_backed"
warning = ""
reading_order = 30

[[claims]]
claim_id = "entry"
document_id = "topic-stability"
section = "数据与代码入口"
text = "见 [数据](data/table.csv)。"
source_path = "{source_path}"
source_locator = "L3"
integrity_status = "source_backed"
warning = ""
reading_order = 40

[[claims]]
claim_id = "reproduction"
document_id = "topic-stability"
section = "复现级别"
text = "documented_only。"
source_path = "{source_path}"
source_locator = "L4"
integrity_status = "source_backed"
warning = ""
reading_order = 50
''',
        encoding="utf-8",
        newline="\n",
    )
    return path


def test_topic_docs_render_exact_sections_relative_links_and_integrity_labels(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    evidence = project / "evidence/source.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("question\nconclusion\nentry\nreproduction\n", encoding="utf-8")
    config = load_docs_config(_write_config(tmp_path / "docs.toml"), project_root=project)

    rendered = render_documents(
        config,
        package_paths=frozenset(("01_stability/topic/data/table.csv",)),
    )

    payload = rendered["01_stability/topic/README.md"].decode("utf-8")
    assert tuple(
        line.removeprefix("## ")
        for line in payload.splitlines()
        if line.startswith("## ")
    ) == TOPIC_SECTIONS
    assert "[数据](data/table.csv)" in payload
    assert "来源：`evidence/source.md:L1`" in payload
    assert "⚠ 推断：这是本次交付范围说明，不是仿真结论。" in payload
    assert rendered == render_documents(
        config,
        package_paths=frozenset(("01_stability/topic/data/table.csv",)),
    )


def test_docs_schema_rejects_unresolved_source_backed_claim(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(DocumentationError, match="source path does not resolve"):
        load_docs_config(_write_config(tmp_path / "docs.toml"), project_root=project)


def test_docs_schema_requires_visible_warning_for_non_source_backed_claim(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    evidence = project / "evidence/source.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("evidence\n", encoding="utf-8")
    config_path = _write_config(tmp_path / "docs.toml")
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "warning = \"推断：这是本次交付范围说明，不是仿真结论。\"",
            "warning = \"\"",
        ),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(DocumentationError, match="visible warning"):
        load_docs_config(config_path, project_root=project)


def test_versioned_production_docs_cover_fixed_navigation_and_five_topics() -> None:
    project = Path(__file__).parents[2]
    config_path = (
        project / "95_shared_scripts/handoff_delivery/handoff_docs.toml"
    )

    config = load_docs_config(config_path, project_root=project)
    targets = {row.target_path for row in config.documents}
    assert {
        "README.md",
        "00_handoff/START_HERE.md",
        "shared/README.md",
        "01_stability/README.md",
        "02_spinwave_control/README.md",
        "03_mechanism_and_theory/README.md",
        "04_lif_device/README.md",
        "05_papers_and_talks/README.md",
    } <= targets
    assert sum(row.document_type == "topic" for row in config.documents) == 5
    rendered = render_documents(config)
    assert set(rendered) == targets


def test_cli_baseline_and_compare_old_round_trip_deterministically(
    tmp_path: Path,
) -> None:
    old = tmp_path / "old"
    old.mkdir()
    (old / "README.md").write_text("old\n", encoding="utf-8")
    baseline = tmp_path / "baseline.csv"

    assert main(["baseline", "--old", str(old), "--output", str(baseline)]) == 0
    first = baseline.read_bytes()
    assert main(["baseline", "--old", str(old), "--output", str(baseline)]) == 0
    assert baseline.read_bytes() == first
    assert main(["compare-old", "--old", str(old), "--baseline", str(baseline)]) == 0

    (old / "README.md").write_text("changed\n", encoding="utf-8")
    assert main(["compare-old", "--old", str(old), "--baseline", str(baseline)]) == 1


def test_cli_build_dry_run_is_only_a_thin_nonmutating_builder_adapter(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    old = tmp_path / "old"
    output = tmp_path / "delivery"
    project.mkdir()
    old.mkdir()
    result = BuildResult(
        exit_code=0,
        publishable=False,
        dry_run=True,
        reason="dry-run-complete",
        required_rows=(),
        source_rows=(),
        exclusion_rows=(),
        baseline_difference=BaselineDifference(),
    )

    with patch("handoff_delivery.cli.build_delivery", return_value=result) as build:
        assert main([
            "build",
            "--project-root", str(project),
            "--old", str(old),
            "--output", str(output),
            "--dry-run",
        ]) == 0

    assert build.call_count == 1
    assert build.call_args.kwargs == {
        "project_root": project,
        "old_delivery": old,
        "destination": output,
        "dry_run": True,
        "resume": False,
    }
    assert not output.exists()
    assert not tuple(tmp_path.glob(".delivery.staging-*"))


def test_cli_verify_delegates_to_the_packaged_full_verifier(tmp_path: Path) -> None:
    project = tmp_path / "project"
    delivery = tmp_path / "delivery"
    project.mkdir()
    verifier = delivery / "00_handoff/verify_delivery.py"
    verifier.parent.mkdir(parents=True)
    verifier.write_text(
        "import sys\n"
        "expected = ['--delivery', sys.argv[2], '--project-root', sys.argv[4]]\n"
        "raise SystemExit(0 if sys.argv[1:] == expected else 9)\n",
        encoding="utf-8",
    )

    assert main([
        "verify",
        "--project-root", str(project),
        "--delivery", str(delivery),
    ]) == 0


def test_cli_validate_recipes_checks_current_versioned_ledgers() -> None:
    project = Path(__file__).parents[2]

    assert main(["validate-recipes", "--project-root", str(project)]) == 0


def test_package_verifier_offline_mode_is_self_contained_read_only_and_fail_closed(
    tmp_path: Path,
) -> None:
    delivery = tmp_path / "delivery"
    handoff = delivery / "00_handoff"
    handoff.mkdir(parents=True)
    (delivery / "payload.txt").write_text("trusted\n", encoding="utf-8")
    verifier = handoff / "verify_delivery.py"
    verifier.write_bytes(package_verifier_script())
    results = tuple(
        VerificationResult(gate, True, (("checked", 1),), (), ("payload.txt",))
        for gate in ("G1", "G2", "G3", "G4", "G5")
    )
    write_report(delivery, results)
    write_checksums(delivery)
    before = {
        path.relative_to(delivery).as_posix(): path.stat().st_mtime_ns
        for path in delivery.rglob("*")
        if path.is_file()
    }
    outside = tmp_path / "outside"
    outside.mkdir()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = ""

    passed = subprocess.run(
        [
            sys.executable,
            str(verifier),
            "--delivery",
            str(delivery),
            "--offline",
        ],
        cwd=outside,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert passed.returncode == 0, passed.stderr
    assert "offline integrity-only" in passed.stdout
    assert "G3 was not independently rerun" in passed.stdout
    assert before == {
        path.relative_to(delivery).as_posix(): path.stat().st_mtime_ns
        for path in delivery.rglob("*")
        if path.is_file()
    }

    (delivery / "payload.txt").write_text("tampered\n", encoding="utf-8")
    failed = subprocess.run(
        [
            sys.executable,
            str(verifier),
            "--delivery",
            str(delivery),
            "--offline",
        ],
        cwd=outside,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert failed.returncode != 0


def test_builder_docs_pipeline_materializes_only_configured_docs_and_verifier(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    evidence = project / "evidence/source.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("question\nconclusion\nentry\nreproduction\n", encoding="utf-8")
    config = load_docs_config(_write_config(tmp_path / "docs.toml"), project_root=project)
    staging = tmp_path / "staging"
    data = staging / "01_stability/topic/data/table.csv"
    data.parent.mkdir(parents=True)
    data.write_text("x,y\n0,1\n", encoding="utf-8")
    old = tmp_path / "old"
    old.mkdir()
    portable_contract = PortableContract(
        runs=(),
        transforms=(),
        consumers=(),
        recipes=(),
        wrapper_contracts=(),
        config_toml=b'[paths]\nwork = "runtime"\n',
        runtime_entries=(),
    )
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=tmp_path / "delivery",
        required_assets=RequiredAssetInventory(()),
        old_baseline=BaselineSnapshot(()),
        portable_contract=portable_contract,
        tree_specs=(),
        exact_specs=(),
        include_thesis_assets=False,
        docs_config=config,
    )

    written = builder_module._materialize_docs_pipeline(plan, staging)

    assert written[0] == "01_stability/topic/README.md"
    assert set(written[1:]) == set(
        package_verifier_assets(
            portable_contract,
            tree_specs=(),
            exact_specs=(),
            include_thesis_assets=False,
        )
    )
    assert (staging / "01_stability/topic/README.md").read_bytes() == (
        render_documents(
            config,
            package_paths=frozenset(("01_stability/topic/data/table.csv",)),
        )["01_stability/topic/README.md"]
    )
    assert (staging / "00_handoff/verify_delivery.py").read_bytes() == (
        package_verifier_script()
    )
    assert not tuple(staging.glob("**/*.out/README.md"))


def test_builder_resolves_only_the_versioned_project_docs_source(tmp_path: Path) -> None:
    project = tmp_path / "project"
    evidence = project / "evidence/source.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("question\nconclusion\nentry\nreproduction\n", encoding="utf-8")
    config_path = project / "95_shared_scripts/handoff_delivery/handoff_docs.toml"
    _write_config(config_path)

    resolved = builder_module._resolve_docs_config(project, None)

    assert resolved == load_docs_config(config_path, project_root=project)


def test_full_package_verifier_assets_are_local_and_context_is_deterministic() -> None:
    contract = PortableContract(
        runs=(),
        transforms=(),
        consumers=(),
        recipes=(),
        wrapper_contracts=(),
        config_toml=b'[paths]\nwork = "runtime"\n',
        runtime_entries=(),
    )

    assets = package_verifier_assets(
        contract,
        tree_specs=(TreeSourceSpec("source", "01_stability/topic"),),
        exact_specs=(ExactSourceSpec("source.txt", "shared/source.txt"),),
        include_thesis_assets=False,
    )

    assert "00_handoff/verify_delivery.py" in assets
    assert "00_handoff/_verifier/context.json" in assets
    assert "00_handoff/_verifier/handoff_delivery/verifier.py" in assets
    assert assets == package_verifier_assets(
        contract,
        tree_specs=(TreeSourceSpec("source", "01_stability/topic"),),
        exact_specs=(ExactSourceSpec("source.txt", "shared/source.txt"),),
        include_thesis_assets=False,
    )
    compile(assets["00_handoff/verify_delivery.py"], "verify_delivery.py", "exec")
    context = assets["00_handoff/_verifier/context.json"].decode("utf-8")
    assert str(Path.cwd()) not in context


def test_full_package_verifier_runs_all_gates_outside_repository_without_bypass(
    tmp_path: Path,
) -> None:
    verifier_tests_path = Path(__file__).with_name("test_verifier.py")
    spec = importlib.util.spec_from_file_location(
        "handoff_test_verifier_fixture", verifier_tests_path
    )
    assert spec is not None and spec.loader is not None
    verifier_tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier_tests)

    project, delivery, contract, specs = verifier_tests._fixture(tmp_path)
    tree_specs, exact_specs = specs
    assets = package_verifier_assets(
        contract,
        tree_specs=tree_specs,
        exact_specs=exact_specs,
        include_thesis_assets=False,
    )
    for relative, payload in assets.items():
        target = delivery / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    before = {
        path.relative_to(delivery).as_posix(): path.stat().st_mtime_ns
        for path in delivery.rglob("*")
        if path.is_file()
    }
    outside = tmp_path / "outside-full"
    outside.mkdir()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = ""

    completed = subprocess.run(
        [
            sys.executable,
            str(delivery / "00_handoff/verify_delivery.py"),
            "--delivery",
            str(delivery),
            "--project-root",
            str(project),
        ],
        cwd=outside,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert all(f"{gate}:" in completed.stdout for gate in ("G1", "G2", "G3", "G4", "G5"))
    assert "G3: FAIL" in completed.stdout
    assert "bundled verification failed" not in completed.stderr
    assert before == {
        path.relative_to(delivery).as_posix(): path.stat().st_mtime_ns
        for path in delivery.rglob("*")
        if path.is_file()
    }
