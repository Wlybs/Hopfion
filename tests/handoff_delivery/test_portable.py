from __future__ import annotations

from dataclasses import replace
import csv
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

import pytest

import handoff_delivery.portable as portable_module

from handoff_delivery.portable import (
    FieldConsumer,
    InitialStatePackageContract,
    InitialStateRecipe,
    LiteralReplacement,
    PortableContract,
    PortableError,
    PortableRuntimeEntry,
    PortableTransform,
    RunEntry,
    TemporaryDependencyContract,
    apply_portable_transform,
    assemble_portable_contract,
    bind_initial_state_recipes_to_package,
    detect_field_consumer,
    discover_full_field_consumers,
    load_initial_state_recipes,
    load_field_consumer_registry,
    materialize_portable_contract,
    packaged_initial_state_recipes_csv,
    portable_launcher_script,
    portable_runner_script,
    reverse_portable_transform,
    scan_delivery_absolute_paths,
    scan_executable_text,
    scan_structured_values,
    temporary_dependency_workspace,
    validate_field_consumer_registry,
    validate_initial_state_coverage,
    validate_packaged_initial_state_files,
    validate_initial_state_recipes,
    validate_portable_coverage,
    validate_portable_contract,
)
from handoff_delivery.source_specs import (
    RequiredAssetInventory,
    RequiredAssetRow,
    enumerate_required_assets,
)


ORIGINAL_PATH = (
    "01_stability/case/simulation/original/run.mx3"
)
PORTABLE_PATH = (
    "01_stability/case/simulation/portable/run.mx3"
)
LAUNCHER_PATH = (
    "01_stability/case/simulation/portable/launch_run_1.py"
)
RUNNER_PATH = "shared/runtime/portable_runner.py"


def test_assemble_portable_contract_from_versioned_ledgers_is_exact_and_reversible(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    ledger_root = project / "95_shared_scripts/handoff_delivery"
    ledger_root.mkdir(parents=True)
    source_path = "src/run.mx3"
    original = b'm.LoadFile("historical_seed.ovf")\nrun(0.2e-9)\n'
    source = project / source_path
    source.parent.mkdir(parents=True)
    source.write_bytes(original)
    (project / "evidence.txt").write_text("documented source chain\n", encoding="utf-8")

    with (ledger_root / "initial_state_recipes.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(portable_module.INITIAL_STATE_RECIPE_COLUMNS),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "recipe_id": "recipe-seed",
                "logical_name": "Documented test seed",
                "original_ovf_reference": "historical_seed.ovf",
                "generator_script": "N/A",
                "generator_parameters": "{}",
                "relaxation_mx3": "N/A",
                "expected_output": "temporary/initial_states/seed.ovf",
                "consumers": source_path,
                "verification_status": "documented_only",
                "verification_evidence": "evidence.txt",
                "notes": "Documented only; no simulation was run.",
                "steps_json": '["provide the documented seed"]',
            }
        )
    with (ledger_root / "full_field_consumers.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(portable_module.FIELD_CONSUMER_COLUMNS),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "source_path": source_path,
                "roles": "direct_loader",
                "detection_evidence": "mx3.m_loadfile@L1",
                "status": "active",
                "status_evidence": "evidence.txt:L1",
                "run_id": "run-seed",
                "initial_state_recipe_id": "recipe-seed",
                "non_full_field_data_id": "N/A",
                "portable_handling": "literal_transform",
                "notes": "Active fixture leaf.",
            }
        )
    inventory = RequiredAssetInventory(
        (
            RequiredAssetRow(
                source_path=source_path,
                target_path="01_stability/topic/run.mx3",
                disposition="copied_active",
                expected_target_class="active",
                reason="fixture",
                sha256=hashlib.sha256(original).hexdigest(),
                size=len(original),
                file_type="code",
            ),
        )
    )

    contract = assemble_portable_contract(project, inventory)

    assert len(contract.runs) == len(contract.transforms) == len(contract.runtime_entries) == 1
    transform = contract.transforms[0]
    assert transform.original_path == "01_stability/topic/simulation/original/run.mx3"
    assert transform.portable_path == "01_stability/topic/simulation/portable/run.mx3"
    assert apply_portable_transform(original, transform) == (
        b'm.LoadFile("${INIT_OVF}")\nrun(0.2e-9)\n'
    )
    assert reverse_portable_transform(
        apply_portable_transform(original, transform), transform
    ) == original
    validate_portable_contract(contract, project_root=project)


def test_project_production_contract_closes_every_active_consumer() -> None:
    project = Path(__file__).parents[2]

    contract = assemble_portable_contract(
        project,
        enumerate_required_assets(project),
    )

    active = tuple(row for row in contract.consumers if row.status == "active")
    assert len(active) == 72
    assert len(contract.runs) == len(contract.transforms) == len(active)
    assert len(contract.runtime_entries) == len(active)
    assert sum(
        transform.strategy == "wrapper_plus_transform"
        for transform in contract.transforms
    ) == 1
    for transform in contract.transforms:
        original = (project / transform.source_path).read_bytes()
        portable = apply_portable_transform(original, transform)
        assert not scan_executable_text(portable, context=transform.portable_path)
        assert reverse_portable_transform(portable, transform) == original


def make_transform(
    original: bytes,
    *replacements: LiteralReplacement,
) -> PortableTransform:
    return PortableTransform(
        transform_id="transform-run-1",
        run_id="run-1",
        source_path="src/run.mx3",
        original_path=ORIGINAL_PATH,
        original_sha256=hashlib.sha256(original).hexdigest(),
        portable_path=PORTABLE_PATH,
        replacements=tuple(replacements),
    )


def test_exact_transform_preserves_bom_crlf_and_reverses_byte_for_byte() -> None:
    original = (
        b"\xef\xbb\xbf// keep CRLF\r\n"
        b'm.LoadFile("/mnt/d/Research/Hopfion/m000020.ovf")\r\n'
        b"run(0.2e-9)\r\n"
    )
    transform = make_transform(
        original,
        LiteralReplacement(
            old=b"/mnt/d/Research/Hopfion/m000020.ovf",
            new=b"${INIT_OVF}",
            expected_count=1,
        ),
    )

    portable = apply_portable_transform(original, transform)

    assert portable.startswith(b"\xef\xbb\xbf// keep CRLF\r\n")
    assert portable.endswith(b"run(0.2e-9)\r\n")
    assert reverse_portable_transform(portable, transform) == original


@pytest.mark.parametrize(
    ("payload", "expected_count"),
    [
        (b"prefix only", 1),
        (b"OLD OLD", 1),
    ],
)
def test_transform_rejects_missing_or_extra_literal_occurrences(
    payload: bytes,
    expected_count: int,
) -> None:
    transform = make_transform(
        payload,
        LiteralReplacement(
            old=b"OLD",
            new=b"NEW",
            expected_count=expected_count,
        ),
    )

    with pytest.raises(PortableError, match="occurrence"):
        apply_portable_transform(payload, transform)


def test_transform_rejects_overlapping_replacement_spans() -> None:
    original = b"ABC"
    transform = make_transform(
        original,
        LiteralReplacement(old=b"AB", new=b"X", expected_count=1),
        LiteralReplacement(old=b"BC", new=b"Y", expected_count=1),
    )

    with pytest.raises(PortableError, match="overlap"):
        apply_portable_transform(original, transform)


def test_transform_rejects_cascade_prone_new_literal_already_in_original() -> None:
    original = b"A B"
    transform = make_transform(
        original,
        LiteralReplacement(old=b"A", new=b"B", expected_count=1),
    )

    with pytest.raises(PortableError, match="already exists"):
        apply_portable_transform(original, transform)


def test_transform_rejects_new_literals_that_are_equal_or_substrings() -> None:
    original = b"LEFT RIGHT"
    transform = make_transform(
        original,
        LiteralReplacement(old=b"LEFT", new=b"TOKEN", expected_count=1),
        LiteralReplacement(old=b"RIGHT", new=b"TOKEN_LONG", expected_count=1),
    )

    with pytest.raises(PortableError, match="substring"):
        apply_portable_transform(original, transform)


def test_reverse_rejects_any_unregistered_portable_difference() -> None:
    original = b"path=OLD\r\nphysics=unchanged\r\n"
    transform = make_transform(
        original,
        LiteralReplacement(old=b"OLD", new=b"${PATH}", expected_count=1),
    )
    portable = apply_portable_transform(original, transform)

    with pytest.raises(PortableError, match="SHA256"):
        reverse_portable_transform(
            portable.replace(b"physics=unchanged", b"physics=CHANGED"),
            transform,
        )


def test_active_run_and_transform_sets_are_exact_equal_and_nonempty() -> None:
    original = b"OLD"
    run = RunEntry(
        run_id="run-1",
        status="active",
        original_path=ORIGINAL_PATH,
        portable_entry=LAUNCHER_PATH,
    )
    transform = make_transform(
        original,
        LiteralReplacement(old=b"OLD", new=b"NEW", expected_count=1),
    )

    validate_portable_coverage((run,), (transform,))

    with pytest.raises(PortableError, match="non-empty"):
        validate_portable_coverage((), ())
    with pytest.raises(PortableError, match="coverage"):
        validate_portable_coverage(
            (
                replace(
                    run,
                    original_path=ORIGINAL_PATH.replace("run.mx3", "other.mx3"),
                ),
            ),
            (transform,),
        )


def test_group_run_cannot_hide_multiple_originals_or_portables() -> None:
    original = b"OLD"
    run = RunEntry("run-1", "active", ORIGINAL_PATH, LAUNCHER_PATH)
    first = make_transform(
        original,
        LiteralReplacement(old=b"OLD", new=b"NEW", expected_count=1),
    )
    second = replace(
        first,
        transform_id="transform-run-1-second",
        original_path=ORIGINAL_PATH.replace("run.mx3", "second.mx3"),
        portable_path=PORTABLE_PATH.replace("run.mx3", "second.mx3"),
    )

    with pytest.raises(PortableError, match="run_id"):
        validate_portable_coverage((run,), (first, second))


def test_reference_and_archive_runs_create_no_portable_obligation() -> None:
    rows = (
        RunEntry("reference", "reference_only", "N/A", "N/A"),
        RunEntry("archive", "archive", "N/A", "N/A"),
        RunEntry("run-1", "active", ORIGINAL_PATH, LAUNCHER_PATH),
    )
    original = b"OLD"
    transform = make_transform(
        original,
        LiteralReplacement(old=b"OLD", new=b"NEW", expected_count=1),
    )

    validate_portable_coverage(rows, (transform,))

    reference_original = replace(
        rows[0],
        original_path=ORIGINAL_PATH,
    )
    validate_portable_coverage(
        (reference_original, rows[1], rows[2]),
        (transform,),
    )


@pytest.mark.parametrize(
    ("original", "portable"),
    [
        ("../original.mx3", PORTABLE_PATH),
        (ORIGINAL_PATH, r"01_stability\portable\run.mx3"),
        ("01_stability/case/run.mx3", PORTABLE_PATH),
        (ORIGINAL_PATH, "01_stability/case/run.mx3"),
        (
            "06_invalid/case/simulation/original/run.mx3",
            "06_invalid/case/simulation/portable/run.mx3",
        ),
    ],
)
def test_active_run_paths_must_be_delivery_relative_and_in_original_portable_trees(
    original: str,
    portable: str,
) -> None:
    with pytest.raises(PortableError):
        RunEntry("run-1", "active", original, portable)


def test_detector_distinguishes_direct_loader_from_python_template_generator() -> None:
    direct = detect_field_consumer(
        "sim/run.mx3",
        b'// m.LoadFile("commented.ovf")\nm.LoadFile("state.ovf")\n',
    )
    generator = detect_field_consumer(
        "tools/generate.py",
        b'template = \'m.LoadFile("{state}.ovf")\\n\'\n',
    )

    assert direct is not None and direct.roles == ("direct_loader",)
    assert generator is not None and generator.roles == ("generator",)


def test_detector_recognizes_python_reader_thiele_chain_and_shell_manager() -> None:
    reader = detect_field_consumer(
        "analysis/read.py",
        b"field = Field.from_file(input_path)\n",
    )
    thiele = detect_field_consumer(
        "analysis/thiele.py",
        (
            b'archive = "ovf_archive.tar.zst"\n'
            b'member = "m000020.ovf"\n'
            b"import tarfile, zstandard\n"
            b"def read_ovf(path):\n    return path.read_bytes()\n"
        ),
    )
    manager = detect_field_consumer(
        "jobs/run.sh",
        b"#!/bin/sh\n# mumax3 ignored.mx3\nmumax3 active.mx3\n",
    )

    assert reader is not None and reader.roles == ("known_ovf_reader",)
    assert thiele is not None and thiele.roles == (
        "known_ovf_reader",
        "archive_member_reader",
    )
    assert manager is not None and manager.roles == ("shell_manager",)


def test_python_detector_constant_folds_archive_and_generator_strings() -> None:
    thiele = detect_field_consumer(
        "analysis/thiele.py",
        (
            b'archive = "ovf_archive." + "tar.zst"\n'
            b'member = "m000020." + "ovf"\n'
            b"import tarfile\n"
            b"def read_ovf(path): return path.read_bytes()\n"
        ),
    )
    generator = detect_field_consumer(
        "tools/generate.py",
        b'template = "m.Load" + \'File("state.ovf")\\n\'\n',
    )

    assert thiele is not None and thiele.roles == (
        "known_ovf_reader",
        "archive_member_reader",
    )
    assert generator is not None and generator.roles == ("generator",)


def test_python_detector_fails_closed_on_parse_error() -> None:
    with pytest.raises(PortableError, match="parse Python"):
        detect_field_consumer(
            "analysis/broken.py",
            b'def broken(:\n    archive = "state.ovf"\n',
        )


def test_python_detector_uses_folded_constants_for_generic_field_touch_only() -> None:
    folded = detect_field_consumer(
        "analysis/folded_suffix.py",
        b'suffix = ".o" + "vf"\nopen(root / suffix, "rb")\n',
    )
    dynamic_fstring = detect_field_consumer(
        "analysis/dynamic_suffix.py",
        b'suffix = f".{extension}"\nopen(root / suffix, "rb")\n',
    )

    assert folded is not None
    assert folded.roles == ("unresolved_touch",)
    assert folded.detection_evidence == (
        "python.constant_field_reference@L1",
    )
    assert dynamic_fstring is None


def test_detector_marks_dynamic_ovf_touch_unresolved_instead_of_guessing() -> None:
    row = detect_field_consumer(
        "analysis/dynamic.py",
        b'suffix = ".ovf"\nwith open(root / (name + suffix), "rb") as handle:\n    pass\n',
    )

    assert row is not None and row.roles == ("unresolved_touch",)


def test_field_consumer_registry_requires_exact_discovery_set_roles_and_routes() -> None:
    discoveries = (
        detect_field_consumer("src/run.mx3", b'm.LoadFile("state.ovf")\n'),
        detect_field_consumer("src/thiele.py", b"def read_ovf(path): return path\n"),
        detect_field_consumer("src/archive.sh", b"mumax3 old.mx3\n"),
    )
    assert all(row is not None for row in discoveries)
    registry = (
        FieldConsumer(
            "src/run.mx3",
            ("direct_loader",),
            "active",
            "run-1",
            "recipe-1",
            "N/A",
            "registered from content scan",
            "literal_transform",
            ("mx3.m_loadfile@L1",),
            "src/run.mx3:L1",
        ),
        FieldConsumer(
            "src/thiele.py",
            ("known_ovf_reader",),
            "reference_only",
            "N/A",
            "N/A",
            "N/A",
            "reference code",
            "reference_only",
            ("python.known_ovf_reader@L1",),
            "src/thiele.py:L1",
        ),
        FieldConsumer(
            "src/archive.sh",
            ("shell_manager",),
            "archive",
            "N/A",
            "N/A",
            "N/A",
            "historical manager",
            "archive",
            ("shell.field_manager@L1",),
            "src/archive.sh:L1",
        ),
    )
    dispositions = {
        "src/run.mx3": "copied_active",
        "src/thiele.py": "copied_active",
        "src/archive.sh": "copied_archive",
    }

    validate_field_consumer_registry(
        tuple(row for row in discoveries if row is not None),
        registry,
        dispositions,
        publish=True,
    )

    with pytest.raises(PortableError, match="discovery set"):
        validate_field_consumer_registry(
            tuple(row for row in discoveries if row is not None),
            registry[:-1],
            dispositions,
            publish=True,
        )
    with pytest.raises(PortableError, match="roles"):
        validate_field_consumer_registry(
            tuple(row for row in discoveries if row is not None),
            (replace(registry[0], roles=("generator",)), *registry[1:]),
            dispositions,
            publish=True,
        )
    with pytest.raises(PortableError, match="copied_archive"):
        validate_field_consumer_registry(
            tuple(row for row in discoveries if row is not None),
            (replace(registry[0], status="archive"), *registry[1:]),
            dispositions,
            publish=True,
        )


def test_unresolved_consumer_is_forbidden_in_publish_mode() -> None:
    discovery = detect_field_consumer(
        "src/dynamic.py",
        b'suffix = ".ovf"\nopen(root / suffix, "rb")\n',
    )
    assert discovery is not None
    registry = (
        FieldConsumer(
            "src/dynamic.py",
            ("unresolved_touch",),
            "unresolved",
            "N/A",
            "N/A",
            "N/A",
            "requires human classification",
            "unresolved",
            ("code.dynamic_field_reference@L1",),
            "N/A",
        ),
    )

    validate_field_consumer_registry(
        (discovery,), registry, {"src/dynamic.py": "copied_active"}, publish=False
    )
    with pytest.raises(PortableError, match="unresolved"):
        validate_field_consumer_registry(
            (discovery,),
            registry,
            {"src/dynamic.py": "copied_active"},
            publish=True,
        )


def test_field_consumer_csv_loader_has_strict_versioned_header(tmp_path) -> None:
    ledger = tmp_path / "full_field_consumers.csv"
    ledger.write_text(
        "source_path,roles,detection_evidence,status,status_evidence,run_id,"
        "initial_state_recipe_id,non_full_field_data_id,portable_handling,notes\n"
        "src/run.mx3,direct_loader,mx3.m_loadfile@L1,active,src/run.mx3:L1,"
        "run-1,recipe-1,N/A,literal_transform,content scan\n",
        encoding="utf-8",
    )

    rows = load_field_consumer_registry(ledger)

    assert rows == (
        FieldConsumer(
            "src/run.mx3",
            ("direct_loader",),
            "active",
            "run-1",
            "recipe-1",
            "N/A",
            "content scan",
            "literal_transform",
            ("mx3.m_loadfile@L1",),
            "src/run.mx3:L1",
        ),
    )
    ledger.write_text("source_path,status\n", encoding="utf-8")
    with pytest.raises(PortableError, match="header"):
        load_field_consumer_registry(ledger)


def test_canonical_ledger_loaders_refuse_symlinked_parent_traversal(tmp_path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    consumer = outside / "full_field_consumers.csv"
    consumer.write_text(
        "source_path,roles,detection_evidence,status,status_evidence,run_id,"
        "initial_state_recipe_id,non_full_field_data_id,portable_handling,notes\n",
        encoding="utf-8",
    )
    recipes = outside / "initial_state_recipes.csv"
    recipes.write_text(
        "recipe_id,logical_name,original_ovf_reference,generator_script,"
        "generator_parameters,relaxation_mx3,expected_output,consumers,"
        "verification_status,verification_evidence,notes,steps_json\n",
        encoding="utf-8",
    )
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)

    with pytest.raises(PortableError, match="symlink"):
        load_field_consumer_registry(linked / consumer.name)
    with pytest.raises(PortableError, match="symlink"):
        load_initial_state_recipes(linked / recipes.name)


def test_consumer_discovery_cannot_be_redirected_after_leaf_validation(
    tmp_path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    source_directory = project / "src"
    source_directory.mkdir(parents=True)
    candidate = source_directory / "candidate.py"
    candidate.write_text("print('not a field consumer')\n", encoding="utf-8")
    outside = tmp_path / "outside-source"
    outside.mkdir()
    (outside / candidate.name).write_text(
        'm.LoadFile("outside.ovf")\n', encoding="utf-8"
    )
    original_read_bytes = Path.read_bytes
    swapped = False

    def redirect_after_validation(path: Path) -> bytes:
        nonlocal swapped
        if path == candidate and not swapped:
            swapped = True
            source_directory.rename(project / "src-original")
            source_directory.symlink_to(outside, target_is_directory=True)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", redirect_after_validation)

    discoveries = discover_full_field_consumers(project, ("src/candidate.py",))

    assert discoveries == ()


def test_anchored_regular_descriptor_closes_leaf_when_fstat_fails(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "evidence.txt").write_text("evidence", encoding="utf-8")
    real_open = portable_module.os.open
    real_close = portable_module.os.close
    opened: list[int] = []
    closed: list[int] = []

    def tracking_open(*args, **kwargs) -> int:
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def tracking_close(descriptor: int) -> None:
        closed.append(descriptor)
        real_close(descriptor)

    def failing_fstat(_descriptor: int):
        raise OSError("synthetic leaf fstat failure")

    monkeypatch.setattr(portable_module.os, "open", tracking_open)
    monkeypatch.setattr(portable_module.os, "close", tracking_close)
    monkeypatch.setattr(portable_module.os, "fstat", failing_fstat)

    with pytest.raises(PortableError, match="cannot open"):
        portable_module._anchored_regular_descriptor(
            root,
            portable_module.PurePosixPath("evidence.txt"),
            label="test evidence",
        )

    leaf_descriptor = opened[-1]
    leaf_handle = Path(f"/proc/self/fd/{leaf_descriptor}")
    try:
        assert not leaf_handle.exists()
    finally:
        if leaf_handle.exists():
            real_close(leaf_descriptor)


def test_consumer_ledger_read_is_anchored_before_parent_swap(
    tmp_path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    ledger_directory = project / "ledgers"
    ledger_directory.mkdir(parents=True)
    ledger = ledger_directory / "full_field_consumers.csv"
    header = (
        "source_path,roles,detection_evidence,status,status_evidence,run_id,"
        "initial_state_recipe_id,non_full_field_data_id,portable_handling,notes\n"
    )
    ledger.write_text(
        header
        + "src/run.mx3,direct_loader,mx3.m_loadfile@L1,active,src/run.mx3:L1,"
        "run-safe,recipe-1,N/A,literal_transform,safe\n",
        encoding="utf-8",
    )
    outside = tmp_path / "outside-ledger"
    outside.mkdir()
    (outside / ledger.name).write_text(
        header
        + "src/run.mx3,direct_loader,mx3.m_loadfile@L1,active,src/run.mx3:L1,"
        "run-outside,recipe-1,N/A,literal_transform,outside\n",
        encoding="utf-8",
    )
    original_check = portable_module._require_real_file_without_symlink_ancestors
    swapped = False

    def swap_after_check(path: Path, *, label: str) -> None:
        nonlocal swapped
        original_check(path, label=label)
        if path == ledger and not swapped:
            swapped = True
            ledger_directory.rename(project / "ledgers-original")
            ledger_directory.symlink_to(outside, target_is_directory=True)

    monkeypatch.setattr(
        portable_module,
        "_require_real_file_without_symlink_ancestors",
        swap_after_check,
    )

    rows = load_field_consumer_registry(ledger, project_root=project)

    assert rows[0].run_id == "run-safe"


def test_recipe_ledger_read_is_anchored_before_parent_swap(
    tmp_path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    ledger_directory = project / "ledgers"
    ledger_directory.mkdir(parents=True)
    ledger = ledger_directory / "initial_state_recipes.csv"
    header = (
        "recipe_id,logical_name,original_ovf_reference,generator_script,"
        "generator_parameters,relaxation_mx3,expected_output,consumers,"
        "verification_status,verification_evidence,notes,steps_json\n"
    )
    ledger.write_text(
        header
        + "recipe-safe,safe recipe,N/A,N/A,{},N/A,temporary/m000020.ovf,"
        "src/run.mx3,documented_only,evidence/safe.txt,safe notes,[]\n",
        encoding="utf-8",
    )
    outside = tmp_path / "outside-recipe-ledger"
    outside.mkdir()
    (outside / ledger.name).write_text(
        header
        + "recipe-outside,outside recipe,N/A,N/A,{},N/A,temporary/m000020.ovf,"
        "src/run.mx3,documented_only,evidence/outside.txt,outside notes,[]\n",
        encoding="utf-8",
    )
    original_check = portable_module._require_real_file_without_symlink_ancestors
    swapped = False

    def swap_after_check(path: Path, *, label: str) -> None:
        nonlocal swapped
        original_check(path, label=label)
        if path == ledger and not swapped:
            swapped = True
            ledger_directory.rename(project / "ledgers-original")
            ledger_directory.symlink_to(outside, target_is_directory=True)

    monkeypatch.setattr(
        portable_module,
        "_require_real_file_without_symlink_ancestors",
        swap_after_check,
    )

    rows = load_initial_state_recipes(ledger, project_root=project)

    assert rows[0].recipe_id == "recipe-safe"


def test_status_evidence_read_cannot_follow_parent_swapped_after_check(
    tmp_path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    evidence_directory = project / "evidence"
    evidence_directory.mkdir(parents=True)
    (evidence_directory / "review.txt").write_text("one line\n", encoding="utf-8")
    outside = tmp_path / "outside-evidence-source"
    outside.mkdir()
    (outside / "review.txt").write_text("one line\ntwo lines\n", encoding="utf-8")
    discovery = detect_field_consumer(
        "src/run.mx3", b'm.LoadFile("m000020.ovf")\n'
    )
    assert discovery is not None
    registry = (
        FieldConsumer(
            "src/run.mx3",
            discovery.roles,
            "active",
            "run-1",
            "recipe-1",
            "N/A",
            "specific evidence",
            "literal_transform",
            discovery.detection_evidence,
            "evidence/review.txt:L2",
        ),
    )
    original_check = portable_module._require_project_evidence_file
    swapped = False

    def swap_after_check(root: Path, relative: str, *, label: str) -> None:
        nonlocal swapped
        original_check(root, relative, label=label)
        if relative == "evidence/review.txt" and not swapped:
            swapped = True
            evidence_directory.rename(project / "evidence-original")
            evidence_directory.symlink_to(outside, target_is_directory=True)

    monkeypatch.setattr(
        portable_module,
        "_require_project_evidence_file",
        swap_after_check,
    )

    with pytest.raises(PortableError, match="status_evidence line is out of range"):
        validate_field_consumer_registry(
            (discovery,),
            registry,
            {"src/run.mx3": "copied_active"},
            publish=False,
            project_root=project,
        )


@pytest.mark.parametrize(
    "literal",
    [
        r"D:\\Research\\Hopfion\\state.ovf",
        r"\\\\server\\share\\state.ovf",
        "/mnt/d/Research/Hopfion/state.ovf",
        "/home/wujiale/project/state.ovf",
        "/tmp/project/.worktrees/feature/state.ovf",
    ],
)
def test_absolute_path_scanner_finds_fixed_forbidden_path_families(
    literal: str,
) -> None:
    findings = scan_executable_text(f'# even comments are executable-scan evidence: "{literal}"')
    assert findings and findings[0].matched


def test_arbitrary_structured_files_cannot_claim_manifest_provenance_exemption() -> None:
    document = {
        "source_path": "/mnt/d/Research/Hopfion/source/run.mx3",
        "original_ovf_reference": r"D:\Research\Hopfion\m000020.ovf",
        "parent_source": "/home/wujiale/source/table.txt",
        "allow_absolute_paths": True,
        "command": "python /mnt/d/Research/Hopfion/run.py",
        "nested": {"executable": r"D:\Research\Hopfion\mumax3.exe"},
    }

    findings = scan_structured_values(document, context="analysis/config.json")

    assert {finding.field_name for finding in findings} == {
        "source_path",
        "original_ovf_reference",
        "parent_source",
        "command",
        "nested.executable",
    }


def test_delivery_scan_uses_g4_includes_and_does_not_exempt_code_comments(
    tmp_path,
) -> None:
    delivery = tmp_path / "delivery"
    portable = delivery / "01_stability/topic/simulation/portable/run.mx3"
    original = delivery / "01_stability/topic/simulation/original/run.mx3"
    archive = delivery / "90_archive/failed/run.py"
    manifest = delivery / "00_handoff/RUN_MANIFEST.csv"
    for path, payload in (
        (portable, '// historical comment: D:/Research/Hopfion/state.ovf\n'),
        (original, 'm.LoadFile("D:/Research/Hopfion/state.ovf")\n'),
        (archive, 'run("/mnt/d/Research/Hopfion/old.py")\n'),
        (
            manifest,
            "run_id,source_path,command\n"
            "r1,/mnt/d/Research/Hopfion/source.mx3,python /home/user/run.py\n",
        ),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")

    findings = scan_delivery_absolute_paths(delivery)

    assert {finding.relative_path for finding in findings} == {
        "00_handoff/RUN_MANIFEST.csv",
        "01_stability/topic/simulation/portable/run.mx3",
    }
    manifest_findings = tuple(
        row for row in findings if row.relative_path == "00_handoff/RUN_MANIFEST.csv"
    )
    assert {row.field_name for row in manifest_findings} == {"command"}


def test_g4_original_exclusion_requires_exact_contiguous_tree_and_manifest_schema(
    tmp_path,
) -> None:
    delivery = tmp_path / "delivery"
    fixtures = {
        "01_stability/topic/simulation/portable/source_path/original/run.json": (
            '{"source_path":"/mnt/d/Research/Hopfion/not-provenance"}\n'
        ),
        "01_stability/topic/analysis/config.yaml": (
            'source_path: "/home/user/not-provenance"\n'
        ),
        "01_stability/topic/simulation/not_original/original/run.py": (
            '# misplaced components do not exclude /mnt/d/Research/Hopfion/run.py\n'
        ),
        "01_stability/topic/analysis/original/run.py": (
            '# analysis/original is executable /home/user/run.py\n'
        ),
        "01_stability/topic/simulation/original/run.py": (
            'run("/mnt/d/Research/Hopfion/archival.py")\n'
        ),
    }
    for relative, payload in fixtures.items():
        path = delivery / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")

    findings = scan_delivery_absolute_paths(delivery)

    assert {row.relative_path for row in findings} == {
        "01_stability/topic/analysis/config.yaml",
        "01_stability/topic/analysis/original/run.py",
        "01_stability/topic/simulation/not_original/original/run.py",
        "01_stability/topic/simulation/portable/source_path/original/run.json",
    }


def test_runtime_command_constructor_rejects_machine_absolute_executable() -> None:
    with pytest.raises(PortableError, match="machine-specific absolute"):
        PortableRuntimeEntry(
            runtime_id="runtime-evil",
            source_path="src/run.mx3",
            run_id="run-1",
            transform_id="transform-run-1",
            initial_state_recipe_id="recipe-1",
            runner_path=RUNNER_PATH,
            launcher_path=LAUNCHER_PATH,
            mode="direct_loader",
            template_path=PORTABLE_PATH,
            command_json='["/home/evil/mumax3","{runtime_entry}"]',
            runtime_tokens=("INIT_OVF",),
        )


def test_g4_scans_portable_wrappers_command_and_launcher_fields(tmp_path) -> None:
    delivery = tmp_path / "delivery"
    wrappers = delivery / "00_handoff/PORTABLE_WRAPPERS.csv"
    wrappers.parent.mkdir(parents=True)
    wrappers.write_text(
        "runtime_id,source_path,run_id,transform_id,initial_state_recipe_id,"
        "runner_path,launcher_path,mode,template_path,command_json,runtime_tokens\n"
        "runtime-evil,src/run.mx3,run-1,transform-run-1,recipe-1,"
        "/mnt/d/evil/portable_runner.py,"
        "/home/evil/launch.py,direct_loader,"
        "01_stability/case/simulation/portable/run.mx3,"
        '"[""/home/evil/mumax3"",""{runtime_entry}""]",INIT_OVF\n',
        encoding="utf-8",
    )

    findings = scan_delivery_absolute_paths(delivery)

    assert {(row.relative_path, row.field_name, row.matched) for row in findings} == {
        (
            "00_handoff/PORTABLE_WRAPPERS.csv",
            "command_json",
            "/home/evil/mumax3",
        ),
        (
            "00_handoff/PORTABLE_WRAPPERS.csv",
            "launcher_path",
            "/home/evil/launch.py",
        ),
        (
            "00_handoff/PORTABLE_WRAPPERS.csv",
            "runner_path",
            "/mnt/d/evil/portable_runner.py",
        ),
    }


def test_g4_constant_folds_python_strings_and_fails_closed_on_parse_error(
    tmp_path,
) -> None:
    delivery = tmp_path / "delivery"
    script = delivery / "shared/analysis/constant_path.py"
    script.parent.mkdir(parents=True)
    script.write_text(
        'ROOT = "/mnt/" + "d/Research/Hopfion/private"\n',
        encoding="utf-8",
    )

    findings = scan_delivery_absolute_paths(delivery)

    assert {(row.relative_path, row.matched) for row in findings} == {
        (
            "shared/analysis/constant_path.py",
            "/mnt/d/Research/Hopfion/private",
        )
    }

    script.write_text(
        'def broken(:\n    ROOT = "/mnt/d/Research/Hopfion/private"\n',
        encoding="utf-8",
    )
    with pytest.raises(PortableError, match="parse Python"):
        scan_delivery_absolute_paths(delivery)


def make_recipe(
    *,
    recipe_id: str = "recipe-1",
    consumers: tuple[str, ...] = ("src/run.mx3",),
    status: str = "documented_only",
) -> InitialStateRecipe:
    return InitialStateRecipe(
        recipe_id=recipe_id,
        logical_name="QH1 frustrated-FM initial state",
        original_ovf_reference="/mnt/d/Research/Hopfion/source/m000020.ovf",
        generator_script="src/generate.py",
        generator_parameters=json.dumps({"axis": "z", "QH": 1}, sort_keys=True),
        relaxation_mx3="src/relax.mx3",
        expected_output="temporary/m000020.ovf",
        consumers=consumers,
        verification_status=status,
        verification_evidence="evidence/generation_notes.txt",
        notes="Paths and parameters documented; no simulation was run for this delivery.",
        steps_json=json.dumps(
            ["generate analytic seed", "relax with Mumax3", "consume temporary OVF"]
        ),
    )


def make_recipe_source_tree(tmp_path):
    project = tmp_path / "project"
    for relative, payload in (
        ("src/generate.py", "print('generator')\n"),
        ("src/relax.mx3", "relax()\n"),
        ("evidence/generation_notes.txt", "Historical path notes only.\n"),
    ):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    return project


def make_required_asset(
    source_path: str,
    target_path: str | None,
    *,
    disposition: str = "copied_active",
    sha256: str | None = None,
) -> RequiredAssetRow:
    return RequiredAssetRow(
        source_path=source_path,
        target_path=target_path,
        disposition=disposition,
        expected_target_class=(
            "excluded"
            if disposition == "excluded_with_reason"
            else "archive"
            if disposition == "copied_archive"
            else "active"
        ),
        reason="test fixture",
        sha256=sha256 or hashlib.sha256(source_path.encode()).hexdigest(),
        size=1,
        file_type="file",
    )


def make_package_projection(
    recipe: InitialStateRecipe | None = None,
) -> InitialStatePackageContract:
    consumer_sha = hashlib.sha256(b"consumer source").hexdigest()
    if recipe is None:
        recipe = replace(
            make_recipe(),
            verification_evidence=(
                "evidence/generation_notes.txt;evidence/historical_run.txt"
            ),
        )
    inventory = RequiredAssetInventory(
        (
            make_required_asset(
                "src/generate.py", "shared/initial_state/generate.py"
            ),
            make_required_asset(
                "src/relax.mx3", "01_stability/initial_state/relax.mx3"
            ),
            make_required_asset(
                "src/run.mx3",
                ORIGINAL_PATH,
                sha256=consumer_sha,
            ),
            make_required_asset(
                "evidence/generation_notes.txt",
                "provenance/generation_notes.txt",
            ),
            make_required_asset(
                "evidence/historical_run.txt",
                "archive/evidence/historical_run.txt",
                disposition="copied_archive",
            ),
        )
    )
    transform = PortableTransform(
        transform_id="transform-package-projection",
        run_id="run-package-projection",
        source_path="src/run.mx3",
        original_path=ORIGINAL_PATH,
        original_sha256=consumer_sha,
        portable_path=PORTABLE_PATH,
        replacements=(
            LiteralReplacement(old=b"source", new=b"portable", expected_count=1),
        ),
    )
    return bind_initial_state_recipes_to_package(
        (recipe,), required_assets=inventory, transforms=(transform,)
    )


def test_initial_state_package_projection_maps_roles_without_mutating_source_recipe() -> None:
    source_recipe = replace(
        make_recipe(),
        verification_evidence=(
            "evidence/generation_notes.txt;evidence/historical_run.txt"
        ),
    )

    package = make_package_projection(source_recipe)
    projected = package.recipes[0]

    assert source_recipe.generator_script == "src/generate.py"
    assert projected.generator_script == "shared/initial_state/generate.py"
    assert projected.relaxation_mx3 == "01_stability/initial_state/relax.mx3"
    assert projected.consumers == (ORIGINAL_PATH,)
    assert projected.verification_evidence == (
        "provenance/generation_notes.txt;archive/evidence/historical_run.txt"
    )
    assert projected.original_ovf_reference == source_recipe.original_ovf_reference
    assert projected.expected_output == source_recipe.expected_output
    assert [
        (row.field_name, row.ordinal, row.source_path, row.package_path)
        for row in package.bindings
    ] == [
        (
            "generator_script",
            0,
            "src/generate.py",
            "shared/initial_state/generate.py",
        ),
        (
            "relaxation_mx3",
            0,
            "src/relax.mx3",
            "01_stability/initial_state/relax.mx3",
        ),
        ("consumers", 0, "src/run.mx3", ORIGINAL_PATH),
        (
            "verification_evidence",
            0,
            "evidence/generation_notes.txt",
            "provenance/generation_notes.txt",
        ),
        (
            "verification_evidence",
            1,
            "evidence/historical_run.txt",
            "archive/evidence/historical_run.txt",
        ),
    ]


def test_packaged_initial_state_recipe_csv_contains_only_projected_paths() -> None:
    package = make_package_projection()

    rows = tuple(
        csv.DictReader(packaged_initial_state_recipes_csv(package).decode().splitlines())
    )

    assert len(rows) == 1
    assert rows[0]["generator_script"] == "shared/initial_state/generate.py"
    assert rows[0]["consumers"] == ORIGINAL_PATH
    assert rows[0]["verification_evidence"] == (
        "provenance/generation_notes.txt;archive/evidence/historical_run.txt"
    )
    assert rows[0]["original_ovf_reference"].startswith("/mnt/d/")
    assert rows[0]["expected_output"] == "temporary/m000020.ovf"


@pytest.mark.parametrize(
    ("source_path", "disposition", "target_path"),
    [
        ("src/generate.py", "excluded_with_reason", None),
        ("src/relax.mx3", "copied_archive", "archive/relax.mx3"),
        ("src/run.mx3", "excluded_with_reason", None),
        ("evidence/generation_notes.txt", "excluded_with_reason", None),
    ],
)
def test_initial_state_package_projection_rejects_unavailable_role_assets(
    source_path: str,
    disposition: str,
    target_path: str | None,
) -> None:
    consumer_sha = hashlib.sha256(b"consumer source").hexdigest()
    rows = [
        make_required_asset("src/generate.py", "shared/generate.py"),
        make_required_asset("src/relax.mx3", "shared/relax.mx3"),
        make_required_asset(
            "src/run.mx3", ORIGINAL_PATH, sha256=consumer_sha
        ),
        make_required_asset(
            "evidence/generation_notes.txt", "provenance/evidence.txt"
        ),
    ]
    index = next(i for i, row in enumerate(rows) if row.source_path == source_path)
    rows[index] = make_required_asset(
        source_path,
        target_path,
        disposition=disposition,
        sha256=consumer_sha if source_path == "src/run.mx3" else None,
    )
    transform = PortableTransform(
        transform_id="transform-package-projection",
        run_id="run-package-projection",
        source_path="src/run.mx3",
        original_path=ORIGINAL_PATH,
        original_sha256=consumer_sha,
        portable_path=PORTABLE_PATH,
        replacements=(
            LiteralReplacement(old=b"source", new=b"portable", expected_count=1),
        ),
    )

    with pytest.raises(PortableError, match=source_path):
        bind_initial_state_recipes_to_package(
            (make_recipe(),),
            required_assets=RequiredAssetInventory(tuple(rows)),
            transforms=(transform,),
        )


def test_initial_state_package_projection_rejects_missing_asset() -> None:
    recipe = replace(make_recipe(), generator_script="src/missing.py")

    with pytest.raises(PortableError, match="src/missing.py"):
        bind_initial_state_recipes_to_package(
            (recipe,), required_assets=RequiredAssetInventory(()), transforms=()
        )


def test_initial_state_package_projection_rejects_transform_routing_bypass() -> None:
    consumer_sha = hashlib.sha256(b"consumer source").hexdigest()
    inventory = RequiredAssetInventory(
        (
            make_required_asset("src/generate.py", "shared/generate.py"),
            make_required_asset("src/relax.mx3", "shared/relax.mx3"),
            make_required_asset(
                "src/run.mx3", "01_stability/audited/run.mx3", sha256=consumer_sha
            ),
            make_required_asset(
                "evidence/generation_notes.txt", "provenance/evidence.txt"
            ),
        )
    )
    forged_transform = PortableTransform(
        transform_id="transform-forged-route",
        run_id="run-forged-route",
        source_path="src/run.mx3",
        original_path=ORIGINAL_PATH,
        original_sha256=consumer_sha,
        portable_path=PORTABLE_PATH,
        replacements=(
            LiteralReplacement(old=b"source", new=b"portable", expected_count=1),
        ),
    )

    with pytest.raises(PortableError, match="routing disagrees"):
        bind_initial_state_recipes_to_package(
            (make_recipe(),),
            required_assets=inventory,
            transforms=(forged_transform,),
        )


def test_validate_packaged_initial_state_files_is_fail_closed() -> None:
    package = make_package_projection()
    exact_sha_map = {
        row.package_path: row.source_sha256 for row in package.bindings
    }

    validate_packaged_initial_state_files(package, package_sha256=exact_sha_map)

    missing = dict(exact_sha_map)
    missing.pop("shared/initial_state/generate.py")
    with pytest.raises(PortableError, match="missing packaged initial-state file"):
        validate_packaged_initial_state_files(package, package_sha256=missing)

    mismatched = dict(exact_sha_map)
    mismatched[ORIGINAL_PATH] = hashlib.sha256(b"changed").hexdigest()
    with pytest.raises(PortableError, match="SHA256 mismatch"):
        validate_packaged_initial_state_files(package, package_sha256=mismatched)


def test_initial_state_recipe_status_and_source_evidence_are_fail_closed(
    tmp_path,
) -> None:
    project = make_recipe_source_tree(tmp_path)
    recipe = make_recipe()

    validate_initial_state_recipes((recipe,), project_root=project)

    with pytest.raises(PortableError, match="verification_status"):
        replace(recipe, verification_status="fully_rerun")
    with pytest.raises(PortableError, match="stale generator_script"):
        validate_initial_state_recipes(
            (replace(recipe, generator_script="src/missing.py"),),
            project_root=project,
        )
    with pytest.raises(PortableError, match="stale relaxation_mx3"):
        validate_initial_state_recipes(
            (replace(recipe, relaxation_mx3="src/missing.mx3"),),
            project_root=project,
        )
    with pytest.raises(PortableError, match="verification_evidence"):
        validate_initial_state_recipes(
            (replace(recipe, verification_evidence=""),),
            project_root=project,
        )


def test_documented_only_recipe_cannot_claim_an_unrun_full_chain(tmp_path) -> None:
    project = make_recipe_source_tree(tmp_path)
    recipe = replace(
        make_recipe(),
        notes="Full chain rerun and verified end-to-end for this delivery.",
    )

    with pytest.raises(PortableError, match="documented_only"):
        validate_initial_state_recipes((recipe,), project_root=project)


def test_initial_state_consumer_edges_are_bidirectionally_exact(tmp_path) -> None:
    project = make_recipe_source_tree(tmp_path)
    recipe = make_recipe()
    consumer = FieldConsumer(
        "src/run.mx3",
        ("direct_loader",),
        "active",
        "run-1",
        "recipe-1",
        "N/A",
        "active direct loader",
        "literal_transform",
        ("mx3.m_loadfile@L1",),
        "src/run.mx3:L1",
    )

    validate_initial_state_recipes((recipe,), project_root=project)
    validate_initial_state_coverage((consumer,), (recipe,))

    with pytest.raises(PortableError, match="consumer edges"):
        validate_initial_state_coverage(
            (replace(consumer, initial_state_recipe_id="recipe-2"),),
            (recipe,),
        )
    with pytest.raises(PortableError, match="exactly one"):
        validate_initial_state_coverage(
            (
                replace(
                    consumer,
                    non_full_field_data_id="data-derived-slice",
                ),
            ),
            (recipe,),
        )
    with pytest.raises(PortableError, match="active consumer"):
        validate_initial_state_coverage(
            (replace(consumer, initial_state_recipe_id="N/A"),),
            (),
        )


def test_initial_recipe_csv_loader_preserves_declared_status_without_upgrading(
    tmp_path,
) -> None:
    csv_path = tmp_path / "initial_state_recipes.csv"
    csv_path.write_text(
        "recipe_id,logical_name,original_ovf_reference,generator_script,"
        "generator_parameters,relaxation_mx3,expected_output,consumers,"
        "verification_status,verification_evidence,notes,steps_json\n"
        'recipe-1,QH1,D:/source/m000020.ovf,src/generate.py,"{""QH"":1}",'
        'src/relax.mx3,temporary/m000020.ovf,src/run.mx3,documented_only,'
        'evidence/generation_notes.txt,"Not run in this delivery.","[]"\n',
        encoding="utf-8",
    )

    rows = load_initial_state_recipes(csv_path)

    assert len(rows) == 1
    assert rows[0].verification_status == "documented_only"
    assert rows[0].consumers == ("src/run.mx3",)


def test_thiele_wrapper_dependencies_exist_only_in_isolated_temp_and_are_cleaned(
    tmp_path,
) -> None:
    staging = tmp_path / "delivery-staging"
    staging.mkdir()
    (staging / ".handoff-staging").write_text("test-token\n", encoding="utf-8")
    contract = TemporaryDependencyContract(
        wrapper_id="wrapper-thiele",
        run_id="run-thiele",
        transform_id="transform-thiele",
        temporary_paths=("input/m000020.ovf", "input/ovf_archive.tar.zst"),
    )
    payloads = {
        "input/m000020.ovf": b"synthetic-test-only",
        "input/ovf_archive.tar.zst": b"synthetic-archive-test-only",
    }

    with temporary_dependency_workspace(staging, contract, payloads) as workspace:
        assert workspace.parent == staging
        assert (workspace / "input/m000020.ovf").read_bytes() == payloads[
            "input/m000020.ovf"
        ]
        assert (workspace / "input/ovf_archive.tar.zst").is_file()

    assert not workspace.exists()
    assert not list(staging.rglob("*.ovf"))
    assert not list(staging.rglob("*.tar.zst"))


def test_wrapper_workspace_requires_exact_payload_set_and_staging_marker(
    tmp_path,
) -> None:
    staging = tmp_path / "not-staging"
    staging.mkdir()
    contract = TemporaryDependencyContract(
        "wrapper-thiele",
        "run-thiele",
        "transform-thiele",
        ("input/m000020.ovf",),
    )

    with pytest.raises(PortableError, match="staging marker"):
        with temporary_dependency_workspace(
            staging, contract, {"input/m000020.ovf": b"test"}
        ):
            pass

    (staging / ".handoff-staging").write_text("token\n", encoding="utf-8")
    with pytest.raises(PortableError, match="payload set"):
        with temporary_dependency_workspace(staging, contract, {}):
            pass


def test_staging_writer_cannot_be_redirected_after_ancestor_validation(
    tmp_path,
    monkeypatch,
) -> None:
    staging = tmp_path / "staging"
    target_parent = staging / "nested"
    target_parent.mkdir(parents=True)
    outside = tmp_path / "outside-write"
    outside.mkdir()
    original_target = portable_module._exclusive_staging_target
    swapped = False

    def swap_after_validation(root: Path, relative: str) -> Path:
        nonlocal swapped
        target = original_target(root, relative)
        if not swapped:
            swapped = True
            target_parent.rename(staging / "nested-original")
            target_parent.symlink_to(outside, target_is_directory=True)
        return target

    monkeypatch.setattr(
        portable_module,
        "_exclusive_staging_target",
        swap_after_validation,
    )

    portable_module._write_exclusive_staging_bytes(
        staging, "nested/output.txt", b"safe bytes"
    )

    assert not (outside / "output.txt").exists()
    assert (staging / "nested/output.txt").read_bytes() == b"safe bytes"


def test_staging_writer_cleanup_never_unlinks_external_collision(
    tmp_path,
    monkeypatch,
) -> None:
    staging = tmp_path / "staging"
    target_parent = staging / "nested"
    target_parent.mkdir(parents=True)
    outside = tmp_path / "outside-delete"
    outside.mkdir()
    sentinel = outside / "output.txt"
    sentinel.write_bytes(b"external sentinel")
    original_target = portable_module._exclusive_staging_target
    swapped = False

    def swap_after_validation(root: Path, relative: str) -> Path:
        nonlocal swapped
        target = original_target(root, relative)
        if not swapped:
            swapped = True
            target_parent.rename(staging / "nested-original")
            target_parent.symlink_to(outside, target_is_directory=True)
        return target

    def fail_fdopen(*_args, **_kwargs):
        raise OSError("synthetic write failure")

    monkeypatch.setattr(
        portable_module,
        "_exclusive_staging_target",
        swap_after_validation,
    )
    monkeypatch.setattr(portable_module.os, "fdopen", fail_fdopen)

    with pytest.raises(PortableError, match="cannot write portable output"):
        portable_module._write_exclusive_staging_bytes(
            staging, "nested/output.txt", b"safe bytes"
        )

    assert sentinel.read_bytes() == b"external sentinel"


def test_materializer_chmod_cannot_follow_swapped_launcher_parent(
    tmp_path,
    monkeypatch,
) -> None:
    original = b'm.LoadFile("D:/historical/m000020.ovf")\n'
    transform = make_transform(
        original,
        LiteralReplacement(
            b"D:/historical/m000020.ovf", b"${INIT_OVF}", 1
        ),
    )
    contract = PortableContract(
        (RunEntry("run-1", "active", ORIGINAL_PATH, LAUNCHER_PATH),),
        (transform,),
        (
            FieldConsumer(
                "src/run.mx3",
                ("direct_loader",),
                "active",
                "run-1",
                "recipe-1",
                "N/A",
                "specific evidence",
                "literal_transform",
                ("mx3.m_loadfile@L1",),
                "src/run.mx3:L1",
            ),
        ),
        (make_recipe(),),
        (),
        b'[runtime]\ntemp_prefix = "hopfion-portable-"\n',
        (
            PortableRuntimeEntry(
                "runtime-run-1",
                "src/run.mx3",
                "run-1",
                "transform-run-1",
                "recipe-1",
                RUNNER_PATH,
                LAUNCHER_PATH,
                "direct_loader",
                PORTABLE_PATH,
                '["python3","{runtime_entry}"]',
                ("INIT_OVF",),
            ),
        ),
    )
    staging = tmp_path / "staging"
    archived = staging / ORIGINAL_PATH
    archived.parent.mkdir(parents=True)
    archived.write_bytes(original)
    outside_parent = tmp_path / "outside-chmod"
    outside_parent.mkdir()
    outside_launcher = outside_parent / Path(LAUNCHER_PATH).name
    outside_launcher.write_bytes(b"external sentinel")
    outside_launcher.chmod(0o600)
    original_write = portable_module._write_exclusive_staging_bytes
    original_path_chmod = Path.chmod
    path_chmod_calls: list[Path] = []
    swapped = False

    def swap_after_launcher(root, relative: str, payload: bytes) -> None:
        nonlocal swapped
        original_write(root, relative, payload)
        if relative == LAUNCHER_PATH and not swapped:
            swapped = True
            launcher_parent = (staging / LAUNCHER_PATH).parent
            launcher_parent.rename(launcher_parent.with_name("portable-original"))
            launcher_parent.symlink_to(outside_parent, target_is_directory=True)

    monkeypatch.setattr(
        portable_module,
        "_write_exclusive_staging_bytes",
        swap_after_launcher,
    )

    def record_path_chmod(path: Path, mode: int, *args, **kwargs) -> None:
        path_chmod_calls.append(path)
        original_path_chmod(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "chmod", record_path_chmod)

    with pytest.raises(PortableError):
        materialize_portable_contract(contract, staging_root=staging)

    assert outside_launcher.read_bytes() == b"external sentinel"
    assert staging / LAUNCHER_PATH not in path_chmod_calls


def test_materializer_rejects_staging_root_replacement_at_g4_scan(
    tmp_path,
    monkeypatch,
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    contract = PortableContract(
        (),
        (),
        (),
        (),
        (),
        b'[runtime]\ntemp_prefix = "hopfion-portable-"\n',
        (),
    )
    original_scan = portable_module.scan_delivery_absolute_paths
    replaced = False

    def replace_at_scan(root: Path, **kwargs):
        nonlocal replaced
        if not replaced:
            replaced = True
            root.rename(tmp_path / "verified-staging")
            root.mkdir()
            (root / "attacker.txt").write_text("attacker", encoding="utf-8")
        return original_scan(root, **kwargs)

    monkeypatch.setattr(
        portable_module,
        "scan_delivery_absolute_paths",
        replace_at_scan,
    )

    with pytest.raises(PortableError, match="staging root changed"):
        materialize_portable_contract(contract, staging_root=staging)


def test_identity_transform_is_explicit_empty_and_still_sha_verified() -> None:
    original = b"relative_input = load_local_seed()\n"
    transform = PortableTransform(
        transform_id="identity-run",
        run_id="run-identity",
        source_path="src/relative_run.py",
        original_path="01_stability/topic/simulation/original/relative_run.py",
        original_sha256=hashlib.sha256(original).hexdigest(),
        portable_path="01_stability/topic/simulation/portable/relative_run.py",
        replacements=(),
        strategy="identity",
    )

    portable = apply_portable_transform(original, transform)

    assert portable == original
    assert reverse_portable_transform(portable, transform) == original
    with pytest.raises(PortableError, match="SHA256"):
        reverse_portable_transform(portable + b"# tampered\n", transform)


def test_identity_rejects_replacements_and_literal_transform_rejects_empty() -> None:
    original = b"OLD"
    fields = {
        "transform_id": "transform",
        "run_id": "run",
        "source_path": "src/run.mx3",
        "original_path": ORIGINAL_PATH,
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "portable_path": PORTABLE_PATH,
    }

    with pytest.raises(PortableError, match="identity"):
        PortableTransform(
            **fields,
            replacements=(LiteralReplacement(b"OLD", b"NEW", 1),),
            strategy="identity",
        )
    with pytest.raises(PortableError, match="replacement"):
        PortableTransform(**fields, replacements=(), strategy="literal_transform")


def test_transform_source_run_and_handling_bind_exactly_to_active_consumer(
    tmp_path,
) -> None:
    project = make_recipe_source_tree(tmp_path)
    original = b"OLD"
    transform = PortableTransform(
        transform_id="transform-run-1",
        run_id="run-1",
        source_path="src/run.mx3",
        original_path=ORIGINAL_PATH,
        original_sha256=hashlib.sha256(original).hexdigest(),
        portable_path=PORTABLE_PATH,
        replacements=(LiteralReplacement(b"OLD", b"NEW", 1),),
    )
    run = RunEntry("run-1", "active", ORIGINAL_PATH, LAUNCHER_PATH)
    consumer = FieldConsumer(
        source_path="src/run.mx3",
        roles=("direct_loader",),
        status="active",
        run_id="run-1",
        initial_state_recipe_id="recipe-1",
        non_full_field_data_id="N/A",
        notes="specific evidence",
        portable_handling="literal_transform",
        detection_evidence=("mx3.m_loadfile@L1",),
        status_evidence="src/run.mx3:L1",
    )
    recipe = make_recipe()
    runtime = PortableRuntimeEntry(
        runtime_id="runtime-run-1",
        source_path=transform.source_path,
        run_id=transform.run_id,
        transform_id=transform.transform_id,
        initial_state_recipe_id=recipe.recipe_id,
        runner_path=RUNNER_PATH,
        launcher_path=LAUNCHER_PATH,
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
        config_toml=b'[paths]\nseed = "shared/initial_state/seed.ovf"\n',
        runtime_entries=(runtime,),
    )

    validate_portable_contract(contract, project_root=project)

    with pytest.raises(PortableError, match="source/run/handling"):
        validate_portable_contract(
            replace(
                contract,
                consumers=(replace(consumer, source_path="src/other.mx3"),),
            ),
            project_root=project,
        )


def test_runtime_entries_bind_exactly_one_to_every_transform_and_recipe(
    tmp_path,
) -> None:
    project = make_recipe_source_tree(tmp_path)
    original = b'm.LoadFile("D:/historical/m000020.ovf")\n'
    transform = make_transform(
        original,
        LiteralReplacement(
            old=b"D:/historical/m000020.ovf",
            new=b"${INIT_OVF}",
            expected_count=1,
        ),
    )
    run = RunEntry("run-1", "active", ORIGINAL_PATH, LAUNCHER_PATH)
    consumer = FieldConsumer(
        source_path="src/run.mx3",
        roles=("direct_loader",),
        status="active",
        run_id="run-1",
        initial_state_recipe_id="recipe-1",
        non_full_field_data_id="N/A",
        notes="specific evidence",
        portable_handling="literal_transform",
        detection_evidence=("mx3.m_loadfile@L1",),
        status_evidence="src/run.mx3:L1",
    )
    recipe = make_recipe()
    runtime = PortableRuntimeEntry(
        runtime_id="runtime-run-1",
        source_path=transform.source_path,
        run_id=transform.run_id,
        transform_id=transform.transform_id,
        initial_state_recipe_id=recipe.recipe_id,
        runner_path=RUNNER_PATH,
        launcher_path=LAUNCHER_PATH,
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
        config_toml=b'[runtime]\ntemp_prefix = "hopfion-portable-"\n',
        runtime_entries=(runtime,),
    )

    validate_portable_contract(contract, project_root=project)

    with pytest.raises(PortableError, match="runtime.*coverage"):
        validate_portable_contract(
            replace(contract, runtime_entries=()), project_root=project
        )
    with pytest.raises(PortableError, match="runtime.*binding"):
        validate_portable_contract(
            replace(
                contract,
                runtime_entries=(
                    replace(runtime, initial_state_recipe_id="wrong-recipe"),
                ),
            ),
            project_root=project,
        )
    with pytest.raises(PortableError, match="runtime.*binding"):
        validate_portable_contract(
            replace(
                contract,
                runtime_entries=(
                    replace(
                        runtime,
                        launcher_path=LAUNCHER_PATH.replace(
                            "launch_run_1.py", "wrong_launcher.py"
                        ),
                    ),
                ),
            ),
            project_root=project,
        )


def test_materialized_runner_and_csv_execute_direct_mode_in_temp_and_clean(
    tmp_path,
) -> None:
    project = make_recipe_source_tree(tmp_path)
    original = b'm.LoadFile("D:/historical/m000020.ovf")\n'
    transform = make_transform(
        original,
        LiteralReplacement(
            old=b"D:/historical/m000020.ovf",
            new=b"${INIT_OVF}",
            expected_count=1,
        ),
    )
    run = RunEntry("run-1", "active", ORIGINAL_PATH, LAUNCHER_PATH)
    consumer = FieldConsumer(
        source_path="src/run.mx3",
        roles=("direct_loader",),
        status="active",
        run_id="run-1",
        initial_state_recipe_id="recipe-1",
        non_full_field_data_id="N/A",
        notes="specific evidence",
        portable_handling="literal_transform",
        detection_evidence=("mx3.m_loadfile@L1",),
        status_evidence="src/run.mx3:L1",
    )
    runtime = PortableRuntimeEntry(
        runtime_id="runtime-run-1",
        source_path=transform.source_path,
        run_id=transform.run_id,
        transform_id=transform.transform_id,
        initial_state_recipe_id="recipe-1",
        runner_path=RUNNER_PATH,
        launcher_path=LAUNCHER_PATH,
        mode="direct_loader",
        template_path=transform.portable_path,
        command_json=(
            '["python3","{delivery_root}/shared/runtime/fake_consumer.py",'
            '"{runtime_entry}","{dependency}","{workspace}"]'
        ),
        runtime_tokens=("INIT_OVF",),
    )
    contract = PortableContract(
        runs=(run,),
        transforms=(transform,),
        consumers=(consumer,),
        recipes=(make_recipe(),),
        wrapper_contracts=(),
        config_toml=b'[runtime]\ntemp_prefix = "hopfion-portable-"\n',
        runtime_entries=(runtime,),
    )
    validate_portable_contract(contract, project_root=project)

    delivery = tmp_path / "delivery"
    archived = delivery / ORIGINAL_PATH
    archived.parent.mkdir(parents=True)
    archived.write_bytes(original)
    fake = delivery / "shared/runtime/fake_consumer.py"
    fake.parent.mkdir(parents=True)
    fake.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "import sys\n"
        "marker = os.environ.get('PORTABLE_TEST_CHILD_MARKER')\n"
        "if marker:\n"
        "    Path(marker).write_text('started', encoding='utf-8')\n"
        "runtime, dependency, workspace = map(Path, sys.argv[1:4])\n"
        "payload = runtime.read_bytes()\n"
        "if not dependency.is_file() or str(dependency).encode() not in payload:\n"
        "    raise SystemExit(91)\n"
        "if b'${INIT_OVF}' in payload:\n"
        "    raise SystemExit(92)\n"
        "(workspace / 'consumer.ok').write_text('ok', encoding='utf-8')\n",
        encoding="utf-8",
    )

    written = materialize_portable_contract(contract, staging_root=delivery)

    assert "00_handoff/PORTABLE_WRAPPERS.csv" in written
    assert RUNNER_PATH in written
    with (delivery / "00_handoff/PORTABLE_WRAPPERS.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = tuple(csv.DictReader(handle))
    assert len(rows) == len(contract.transforms) == 1
    assert rows[0]["transform_id"] == transform.transform_id
    assert rows[0]["initial_state_recipe_id"] == "recipe-1"
    assert rows[0]["runner_path"] == RUNNER_PATH
    assert rows[0]["launcher_path"] == LAUNCHER_PATH
    assert LAUNCHER_PATH in written

    user_input = tmp_path / "user-seed.bin"
    user_input.write_bytes(b"synthetic bytes only")
    evidence = tmp_path / "execution-evidence.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(delivery / LAUNCHER_PATH),
            "--initial-state",
            str(user_input),
            "--evidence-out",
            str(evidence),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(evidence.read_text(encoding="utf-8"))
    assert result["dependency_provenance"] == "dependency_supplied_by_user"
    assert result["full_chain_reconstruction"] is False
    assert result["command_exit_code"] == 0
    assert result["workspace_cleaned"] is True
    assert not Path(result["workspace"]).exists()
    assert user_input.read_bytes() == b"synthetic bytes only"
    assert not list(delivery.rglob("*.ovf"))
    assert not list(delivery.rglob("*.tar.zst"))


    child_marker = tmp_path / "illegal-evidence-child-started.txt"
    attack_environment = os.environ.copy()
    attack_environment["PORTABLE_TEST_CHILD_MARKER"] = str(child_marker)
    outside = tmp_path / "outside-evidence"
    (outside / "nested").mkdir(parents=True)
    linked_parent = tmp_path / "evidence-parent"
    linked_parent.mkdir()
    (linked_parent / "linked").symlink_to(outside, target_is_directory=True)
    escaped_evidence = linked_parent / "linked/nested/escaped.json"
    escaped = subprocess.run(
        [
            sys.executable,
            str(delivery / LAUNCHER_PATH),
            "--initial-state",
            str(user_input),
            "--evidence-out",
            str(escaped_evidence),
        ],
        capture_output=True,
        text=True,
        env=attack_environment,
        timeout=10,
        check=False,
    )
    assert escaped.returncode != 0
    assert not child_marker.exists()
    assert not (outside / "nested/escaped.json").exists()

    config = delivery / "00_handoff/PORTABLE_CONFIG.toml"
    original_config = config.read_bytes()
    overwritten = subprocess.run(
        [
            sys.executable,
            str(delivery / LAUNCHER_PATH),
            "--initial-state",
            str(user_input),
            "--evidence-out",
            str(config),
        ],
        capture_output=True,
        text=True,
        env=attack_environment,
        timeout=10,
        check=False,
    )
    assert overwritten.returncode != 0
    assert not child_marker.exists()
    assert config.read_bytes() == original_config

    unwritable_evidence = Path(
        f"/proc/{os.getpid()}/hopfion-portable-evidence.json"
    )
    evidence_failed = subprocess.run(
        [
            sys.executable,
            str(delivery / LAUNCHER_PATH),
            "--initial-state",
            str(user_input),
            "--evidence-out",
            str(unwritable_evidence),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    stdout_evidence = json.loads(evidence_failed.stdout.splitlines()[-1])
    assert evidence_failed.returncode == 2
    assert stdout_evidence["exit_code"] == 2
    assert "evidence failure" in evidence_failed.stderr


def test_launcher_never_falls_back_from_nested_delivery_to_outer_delivery(
    tmp_path,
) -> None:
    outer = tmp_path / "outer-delivery"
    inner = outer / "nested" / "inner-delivery"
    launcher = inner / LAUNCHER_PATH
    launcher.parent.mkdir(parents=True)
    runtime = PortableRuntimeEntry(
        runtime_id="runtime-run-1",
        source_path="src/run.mx3",
        run_id="run-1",
        transform_id="transform-run-1",
        initial_state_recipe_id="recipe-1",
        runner_path=RUNNER_PATH,
        launcher_path=LAUNCHER_PATH,
        mode="direct_loader",
        template_path=PORTABLE_PATH,
        command_json='["python3","{runtime_entry}"]',
        runtime_tokens=("INIT_OVF",),
    )
    launcher.write_bytes(portable_launcher_script(runtime))
    outer_runner = outer / RUNNER_PATH
    outer_runner.parent.mkdir(parents=True)
    marker = tmp_path / "outer-runner-started"
    outer_runner.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('started', encoding='utf-8')\n",
        encoding="utf-8",
    )
    outer_registry = outer / "00_handoff/PORTABLE_WRAPPERS.csv"
    outer_registry.parent.mkdir(parents=True)
    outer_registry.write_text("outer registry only\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(launcher)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 2
    assert not marker.exists()
    assert "cannot identify its delivery runner" in completed.stderr


def test_direct_runner_nonzero_and_missing_input_fail_closed_and_clean(
    tmp_path,
) -> None:
    project = make_recipe_source_tree(tmp_path)
    original = b'm.LoadFile("D:/historical/m000020.ovf")\n'
    transform = make_transform(
        original,
        LiteralReplacement(
            old=b"D:/historical/m000020.ovf",
            new=b"${INIT_OVF}",
            expected_count=1,
        ),
    )
    run = RunEntry("run-1", "active", ORIGINAL_PATH, LAUNCHER_PATH)
    consumer = FieldConsumer(
        "src/run.mx3",
        ("direct_loader",),
        "active",
        "run-1",
        "recipe-1",
        "N/A",
        "specific evidence",
        "literal_transform",
        ("mx3.m_loadfile@L1",),
        "src/run.mx3:L1",
    )
    runtime = PortableRuntimeEntry(
        "runtime-run-1",
        transform.source_path,
        transform.run_id,
        transform.transform_id,
        "recipe-1",
        RUNNER_PATH,
        LAUNCHER_PATH,
        "direct_loader",
        transform.portable_path,
        '["python3","{delivery_root}/shared/runtime/fail_consumer.py",'
        '"{runtime_entry}"]',
        ("INIT_OVF",),
    )
    contract = PortableContract(
        (run,),
        (transform,),
        (consumer,),
        (make_recipe(),),
        (),
        b'[runtime]\ntemp_prefix = "hopfion-portable-"\n',
        (runtime,),
    )
    validate_portable_contract(contract, project_root=project)
    delivery = tmp_path / "delivery"
    archive = delivery / ORIGINAL_PATH
    archive.parent.mkdir(parents=True)
    archive.write_bytes(original)
    failure = delivery / "shared/runtime/fail_consumer.py"
    failure.parent.mkdir(parents=True)
    failure.write_text("raise SystemExit(23)\n", encoding="utf-8")
    materialize_portable_contract(contract, staging_root=delivery)
    user_input = tmp_path / "user-seed.bin"
    user_input.write_bytes(b"do not delete me")

    failure_evidence = tmp_path / "failure-evidence.json"
    failed = subprocess.run(
        [
            sys.executable,
            str(delivery / RUNNER_PATH),
            "--run-id",
            "run-1",
            "--initial-state",
            str(user_input),
            "--evidence-out",
            str(failure_evidence),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    failed_result = json.loads(failure_evidence.read_text(encoding="utf-8"))
    assert failed.returncode == 23
    assert failed_result["command_exit_code"] == 23
    assert failed_result["workspace_cleaned"] is True
    assert not Path(failed_result["workspace"]).exists()
    assert user_input.read_bytes() == b"do not delete me"

    missing_evidence = tmp_path / "missing-input-evidence.json"
    missing = subprocess.run(
        [
            sys.executable,
            str(delivery / RUNNER_PATH),
            "--run-id",
            "run-1",
            "--evidence-out",
            str(missing_evidence),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    missing_result = json.loads(missing_evidence.read_text(encoding="utf-8"))
    assert missing.returncode != 0
    assert "documented-only recipes are not auto-reconstructed" in missing.stderr
    assert missing_result["workspace"] == "N/A"
    assert missing_result["workspace_cleaned"] is True
    assert user_input.read_bytes() == b"do not delete me"

    parent_pid_file = tmp_path / "consumer-parent.pid"
    grandchild_pid_file = tmp_path / "consumer-grandchild.pid"
    interrupted_evidence = tmp_path / "interrupted-evidence.json"
    grandchild_code = (
        "from pathlib import Path\n"
        "import os\n"
        "import signal\n"
        "import time\n"
        "signal.signal(signal.SIGINT, signal.SIG_IGN)\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "Path(os.environ['PORTABLE_TEST_GRANDCHILD_PID']).write_text(str(os.getpid()), encoding='utf-8')\n"
        "while True: time.sleep(1)\n"
    )
    failure.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "import signal\n"
        "import subprocess\n"
        "import sys\n"
        "import time\n"
        "signal.signal(signal.SIGINT, signal.SIG_IGN)\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        f"grandchild_code = {grandchild_code!r}\n"
        "subprocess.Popen([sys.executable, '-c', grandchild_code])\n"
        "Path(os.environ['PORTABLE_TEST_PARENT_PID']).write_text(str(os.getpid()), encoding='utf-8')\n"
        "while True: time.sleep(1)\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PORTABLE_TEST_PARENT_PID"] = str(parent_pid_file)
    environment["PORTABLE_TEST_GRANDCHILD_PID"] = str(grandchild_pid_file)
    interrupted = subprocess.Popen(
        [
            sys.executable,
            str(delivery / RUNNER_PATH),
            "--run-id",
            "run-1",
            "--initial-state",
            str(user_input),
            "--evidence-out",
            str(interrupted_evidence),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    deadline = time.monotonic() + 5
    while (
        not (parent_pid_file.exists() and grandchild_pid_file.exists())
        and time.monotonic() < deadline
    ):
        if interrupted.poll() is not None:
            break
        time.sleep(0.02)
    assert parent_pid_file.exists() and grandchild_pid_file.exists()
    parent_pid = int(parent_pid_file.read_text(encoding="utf-8"))
    grandchild_pid = int(grandchild_pid_file.read_text(encoding="utf-8"))
    interrupted.terminate()
    try:
        _, interrupted_stderr = interrupted.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        for pid in (parent_pid, grandchild_pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        interrupted.kill()
        interrupted.wait(timeout=2)
        if interrupted.stdout is not None:
            interrupted.stdout.close()
        if interrupted.stderr is not None:
            interrupted.stderr.close()
        pytest.fail("runner did not terminate an ignoring process group within 8s")
    interrupted_result = json.loads(
        interrupted_evidence.read_text(encoding="utf-8")
    )
    assert interrupted.returncode == 143, interrupted_stderr
    assert interrupted_result["command_exit_code"] == 143
    assert interrupted_result["workspace_cleaned"] is True
    assert not Path(interrupted_result["workspace"]).exists()
    assert user_input.read_bytes() == b"do not delete me"
    process_deadline = time.monotonic() + 3
    while (
        any(Path(f"/proc/{pid}").exists() for pid in (parent_pid, grandchild_pid))
        and time.monotonic() < process_deadline
    ):
        time.sleep(0.02)
    assert not Path(f"/proc/{parent_pid}").exists()
    assert not Path(f"/proc/{grandchild_pid}").exists()


def test_runner_evidence_writer_rejects_ancestor_swap_after_validation(
    tmp_path,
) -> None:
    namespace = {"__name__": "portable_runner_test"}
    exec(portable_runner_script(), namespace)
    safe_evidence_output = namespace["_safe_evidence_output"]
    write_evidence = namespace["_write_evidence"]
    runner_error = namespace["RunnerError"]

    delivery = tmp_path / "delivery"
    delivery.mkdir()
    parent = tmp_path / "validated-parent"
    (parent / "nested").mkdir(parents=True)
    target = safe_evidence_output(
        str(parent / "nested/evidence.json"), delivery
    )
    original_parent = tmp_path / "original-parent"
    parent.rename(original_parent)
    outside = tmp_path / "outside"
    (outside / "nested").mkdir(parents=True)
    parent.symlink_to(outside, target_is_directory=True)

    with pytest.raises(runner_error, match="evidence"):
        write_evidence(target, {"ok": True})

    assert not (outside / "nested/evidence.json").exists()


def test_runner_output_export_rejects_post_validation_swap_and_target_symlink(
    tmp_path,
) -> None:
    namespace = {"__name__": "portable_runner_test"}
    exec(portable_runner_script(), namespace)
    export_outputs = namespace["_export_outputs"]
    safe_output_directory = namespace.get("_safe_output_directory")
    real_user_directory = namespace["_real_user_directory"]
    runner_error = namespace["RunnerError"]

    delivery = tmp_path / "delivery"
    handoff = delivery / "00_handoff"
    handoff.mkdir(parents=True)
    source = tmp_path / "runtime-output"
    (source / "figures").mkdir(parents=True)
    (source / "figures/result.json").write_text("safe", encoding="utf-8")

    destination = tmp_path / "validated-output"
    destination.mkdir()
    if safe_output_directory is None:
        destination_path = real_user_directory(
            str(destination), "output directory"
        )
        destination_descriptor = -1
    else:
        destination_path, destination_descriptor = safe_output_directory(
            str(destination), delivery
        )
    destination.rename(tmp_path / "validated-output-original")
    destination.symlink_to(delivery, target_is_directory=True)
    try:
        with pytest.raises(runner_error):
            if destination_descriptor < 0:
                export_outputs(source, destination_path)
            else:
                export_outputs(
                    source,
                    destination_path,
                    destination_descriptor,
                    delivery,
                )
    finally:
        if destination_descriptor >= 0:
            os.close(destination_descriptor)
    assert not (delivery / "figures/result.json").exists()

    destination.unlink()
    destination.mkdir()
    (destination / "figures").symlink_to(handoff, target_is_directory=True)
    if safe_output_directory is None:
        destination_path = real_user_directory(
            str(destination), "output directory"
        )
        destination_descriptor = -1
    else:
        destination_path, destination_descriptor = safe_output_directory(
            str(destination), delivery
        )
    try:
        with pytest.raises(runner_error):
            if destination_descriptor < 0:
                export_outputs(source, destination_path)
            else:
                export_outputs(
                    source,
                    destination_path,
                    destination_descriptor,
                    delivery,
                )
    finally:
        if destination_descriptor >= 0:
            os.close(destination_descriptor)
    assert not (handoff / "result.json").exists()


def test_runner_delivery_registry_read_cannot_follow_postcheck_parent_swap(
    tmp_path,
) -> None:
    original = b'm.LoadFile("D:/historical/m000020.ovf")\n'
    transform = make_transform(
        original,
        LiteralReplacement(
            b"D:/historical/m000020.ovf", b"${INIT_OVF}", 1
        ),
    )
    runtime = PortableRuntimeEntry(
        "runtime-run-1",
        "src/run.mx3",
        "run-1",
        "transform-run-1",
        "recipe-1",
        RUNNER_PATH,
        LAUNCHER_PATH,
        "direct_loader",
        PORTABLE_PATH,
        '["python3","{delivery_root}/shared/runtime/legitimate_failure.py",'
        '"{runtime_entry}"]',
        ("INIT_OVF",),
    )
    contract = PortableContract(
        (RunEntry("run-1", "active", ORIGINAL_PATH, LAUNCHER_PATH),),
        (transform,),
        (
            FieldConsumer(
                "src/run.mx3",
                ("direct_loader",),
                "active",
                "run-1",
                "recipe-1",
                "N/A",
                "specific evidence",
                "literal_transform",
                ("mx3.m_loadfile@L1",),
                "src/run.mx3:L1",
            ),
        ),
        (make_recipe(),),
        (),
        b'[runtime]\ntemp_prefix = "hopfion-portable-"\n',
        (runtime,),
    )
    delivery = tmp_path / "delivery"
    archived = delivery / ORIGINAL_PATH
    archived.parent.mkdir(parents=True)
    archived.write_bytes(original)
    legitimate = delivery / "shared/runtime/legitimate_failure.py"
    legitimate.parent.mkdir(parents=True)
    legitimate.write_text("raise SystemExit(37)\n", encoding="utf-8")
    materialize_portable_contract(contract, staging_root=delivery)

    marker = tmp_path / "evil-registry-command-started"
    evil_script = tmp_path / "evil_registry_command.py"
    evil_script.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('started', encoding='utf-8')\n",
        encoding="utf-8",
    )
    evil_handoff = tmp_path / "evil-handoff"
    evil_handoff.mkdir()
    registry = delivery / "00_handoff/PORTABLE_WRAPPERS.csv"
    with registry.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = tuple(rows[0])
    rows[0]["command_json"] = json.dumps(
        [sys.executable, str(evil_script), "{runtime_entry}"]
    )
    with (evil_handoff / registry.name).open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    namespace = {
        "__name__": "portable_runner_test",
        "__file__": str(delivery / RUNNER_PATH),
    }
    exec(portable_runner_script(), namespace)
    real_delivery_file = namespace["_real_delivery_file"]
    real_delivery_bytes = namespace.get("_read_delivery_bytes")
    handoff = delivery / "00_handoff"
    swapped = False

    def swap_after_registry_check(root: Path, relative: str, label: str) -> Path:
        nonlocal swapped
        path = real_delivery_file(root, relative, label)
        if relative == "00_handoff/PORTABLE_WRAPPERS.csv" and not swapped:
            swapped = True
            handoff.rename(delivery / "00_handoff-original")
            handoff.symlink_to(evil_handoff, target_is_directory=True)
        return path

    if real_delivery_bytes is None:
        namespace["_real_delivery_file"] = swap_after_registry_check
    else:
        def swap_before_anchored_registry_read(
            root_descriptor: int,
            relative: str,
            label: str,
        ) -> bytes:
            nonlocal swapped
            if relative == "00_handoff/PORTABLE_WRAPPERS.csv" and not swapped:
                swapped = True
                handoff.rename(delivery / "00_handoff-original")
                handoff.symlink_to(evil_handoff, target_is_directory=True)
            return real_delivery_bytes(root_descriptor, relative, label)

        namespace["_read_delivery_bytes"] = swap_before_anchored_registry_read
    user_input = tmp_path / "user-seed.bin"
    user_input.write_bytes(b"seed")
    namespace["_parse_args"] = lambda: namespace["argparse"].Namespace(
        run_id="run-1",
        initial_state=str(user_input),
        field_root=None,
        tar_executable=None,
        output_dir=None,
        evidence_out=None,
    )

    exit_code = namespace["main"]()

    assert exit_code != 0
    assert not marker.exists()


def test_thiele_runner_builds_archive_in_temp_executes_consumer_and_cleans(
    tmp_path,
) -> None:
    project = make_recipe_source_tree(tmp_path)
    original = (
        b'ARCHIVE_SOURCE = "D:/historical/ovf_archive.tar.zst"\n'
        b'OUT_DIR = "D:/historical/out"\n'
        b'TAR_EXE = "C:/historical/tar.exe"\n'
    )
    original_path = "03_mechanism/thiele/simulation/original/compute.py"
    portable_path = "03_mechanism/thiele/simulation/portable/compute.py"
    launcher_path = "03_mechanism/thiele/simulation/portable/launch_compute.py"
    transform = PortableTransform(
        transform_id="transform-thiele",
        run_id="run-thiele",
        source_path="src/thiele.py",
        original_path=original_path,
        original_sha256=hashlib.sha256(original).hexdigest(),
        portable_path=portable_path,
        replacements=(
            LiteralReplacement(
                b"D:/historical/ovf_archive.tar.zst", b"${ARCHIVE_SOURCE}", 1
            ),
            LiteralReplacement(b"D:/historical/out", b"${OUTPUT_ROOT}", 1),
            LiteralReplacement(b"C:/historical/tar.exe", b"${TAR_EXE}", 1),
        ),
        strategy="wrapper_plus_transform",
        wrapper_id="wrapper-thiele",
    )
    run = RunEntry("run-thiele", "active", original_path, launcher_path)
    consumer = FieldConsumer(
        "src/thiele.py",
        ("archive_member_reader",),
        "active",
        "run-thiele",
        "recipe-1",
        "N/A",
        "specific evidence",
        "wrapper_plus_transform",
        ("python.archive_member_reader@L1",),
        "src/thiele.py:L1",
    )
    runtime = PortableRuntimeEntry(
        "runtime-thiele",
        transform.source_path,
        transform.run_id,
        transform.transform_id,
        "recipe-1",
        RUNNER_PATH,
        launcher_path,
        "thiele_archive",
        transform.portable_path,
        '["python3","{delivery_root}/shared/runtime/fake_thiele_consumer.py",'
        '"{runtime_entry}","{archive_source}","{tar_executable}",'
        '"{workspace}"]',
        ("ARCHIVE_SOURCE", "OUTPUT_ROOT", "TAR_EXE"),
    )
    contract = PortableContract(
        (run,),
        (transform,),
        (consumer,),
        (make_recipe(consumers=("src/thiele.py",)),),
        (
            TemporaryDependencyContract(
                "wrapper-thiele",
                "run-thiele",
                "transform-thiele",
                ("input/m000020.ovf", "input/ovf_archive.tar.zst"),
            ),
        ),
        b'[runtime]\ntemp_prefix = "hopfion-portable-"\n',
        (runtime,),
    )
    with pytest.raises(
        PortableError,
        match="thiele_archive wrapper must declare the exact archive/member paths",
    ):
        validate_portable_contract(
            replace(
                contract,
                wrapper_contracts=(
                    replace(
                        contract.wrapper_contracts[0],
                        temporary_paths=(
                            "input/wrong.ovf",
                            "input/ovf_archive.tar.zst",
                        ),
                    ),
                ),
            ),
            project_root=project,
        )
    validate_portable_contract(contract, project_root=project)
    delivery = tmp_path / "delivery"
    archive = delivery / original_path
    archive.parent.mkdir(parents=True)
    archive.write_bytes(original)
    runtime_dir = delivery / "shared/runtime"
    runtime_dir.mkdir(parents=True)
    fake_tar = runtime_dir / "fake_tar.py"
    zstd_shim = runtime_dir / "zstd"
    zstd_shim.write_text(
        "#!/bin/sh\ncat\n",
        encoding="utf-8",
    )
    zstd_shim.chmod(0o755)
    real_tar = shutil.which("tar")
    assert real_tar is not None
    runtime_environment = os.environ.copy()
    runtime_environment["PATH"] = (
        str(runtime_dir) + os.pathsep + runtime_environment["PATH"]
    )
    fake_consumer = runtime_dir / "fake_thiele_consumer.py"
    fake_consumer.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "import subprocess\n"
        "import sys\n"
        "marker = os.environ.get('PORTABLE_TEST_CONSUMER_MARKER')\n"
        "if marker:\n"
        "    Path(marker).write_text('started', encoding='utf-8')\n"
        "runtime, archive, tar_exe, workspace = map(Path, sys.argv[1:5])\n"
        "payload = runtime.read_bytes()\n"
        "if not archive.is_file():\n"
        "    raise SystemExit(81)\n"
        "if str(archive).encode() not in payload or str(tar_exe).encode() not in payload:\n"
        "    raise SystemExit(82)\n"
        "if b'${' in payload:\n"
        "    raise SystemExit(83)\n"
        "listed = subprocess.run([str(tar_exe), '-tf', str(archive)], capture_output=True, check=False)\n"
        "if listed.returncode != 0 or listed.stdout.splitlines() != [b'm000020.ovf']:\n"
        "    raise SystemExit(84)\n"
        "(workspace / 'consumer.ok').write_text('ok', encoding='utf-8')\n",
        encoding="utf-8",
    )
    materialize_portable_contract(contract, staging_root=delivery)
    user_input = tmp_path / "user-static-field.bin"
    user_input.write_bytes(b"synthetic static field bytes")
    evidence = tmp_path / "thiele-evidence.json"
    valid_consumer_marker = tmp_path / "valid-thiele-consumer.started"
    runtime_environment["PORTABLE_TEST_CONSUMER_MARKER"] = str(
        valid_consumer_marker
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(delivery / RUNNER_PATH),
            "--run-id",
            "run-thiele",
            "--initial-state",
            str(user_input),
            "--tar-executable",
            real_tar,
            "--evidence-out",
            str(evidence),
        ],
        capture_output=True,
        text=True,
        env=runtime_environment,
        timeout=10,
        check=False,
    )

    result = json.loads(evidence.read_text(encoding="utf-8"))
    assert completed.returncode == 0, completed.stderr
    assert result["archive_producer_exit_code"] == 0
    assert result["command_exit_code"] == 0
    assert result["initial_state_sha256"] == hashlib.sha256(
        user_input.read_bytes()
    ).hexdigest()
    assert result["workspace_cleaned"] is True
    assert not Path(result["workspace"]).exists()
    assert valid_consumer_marker.read_text(encoding="utf-8") == "started"
    assert user_input.read_bytes() == b"synthetic static field bytes"
    assert not list(delivery.rglob("*.ovf"))
    assert not list(delivery.rglob("*.tar.zst"))

    fake_tar.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import io\n"
        "import os\n"
        "import shutil\n"
        "import sys\n"
        "import tarfile\n"
        "args = sys.argv[1:]\n"
        "case = os.environ['PORTABLE_TEST_ARCHIVE_CASE']\n"
        "if case == 'self_attesting_nonarchive':\n"
        "    if '--create' in args:\n"
        "        Path(args[args.index('--file') + 1]).write_bytes(b'NOT AN ARCHIVE')\n"
        "    elif '-tf' in args:\n"
        "        print('m000020.ovf')\n"
        "    elif '-tvf' in args:\n"
        "        print('-rw-r--r-- user/group 1 2026-01-01 00:00 m000020.ovf')\n"
        "    elif '-xf' in args:\n"
        "        destination = Path(args[args.index('-C') + 1])\n"
        "        destination.mkdir(parents=True, exist_ok=True)\n"
        "        shutil.copyfile(Path.cwd() / 'dependency/m000020.ovf', destination / 'm000020.ovf')\n"
        "    raise SystemExit(0)\n"
        "target = Path(args[args.index('--file') + 1])\n"
        "base = Path(args[args.index('-C') + 1])\n"
        "source = base / args[-1]\n"
        "if case == 'nonarchive':\n"
        "    target.write_bytes(b'not a tar archive')\n"
        "elif case == 'archive_symlink':\n"
        "    target.symlink_to(source.resolve())\n"
        "else:\n"
        "    with tarfile.open(target, 'w') as archive:\n"
        "        if case in {'extra_member', 'valid_member'}:\n"
        "            archive.add(source, arcname='m000020.ovf')\n"
        "        if case == 'extra_member':\n"
        "            archive.add(source, arcname='extra.ovf')\n"
        "        elif case == 'nonregular_member':\n"
        "            info = tarfile.TarInfo('m000020.ovf')\n"
        "            info.type = tarfile.SYMTYPE\n"
        "            info.linkname = 'elsewhere.ovf'\n"
        "            archive.addfile(info)\n"
        "        elif case == 'hardlink_member':\n"
        "            info = tarfile.TarInfo('m000020.ovf')\n"
        "            info.type = tarfile.LNKTYPE\n"
        "            info.linkname = 'elsewhere.ovf'\n"
        "            archive.addfile(info)\n"
        "        elif case == 'fifo_member':\n"
        "            info = tarfile.TarInfo('m000020.ovf')\n"
        "            info.type = tarfile.FIFOTYPE\n"
        "            archive.addfile(info)\n"
        "        elif case == 'character_device_member':\n"
        "            info = tarfile.TarInfo('m000020.ovf')\n"
        "            info.type = tarfile.CHRTYPE\n"
        "            info.devmajor = 1\n"
        "            info.devminor = 3\n"
        "            archive.addfile(info)\n"
        "        elif case == 'path_mismatch':\n"
        "            archive.add(source, arcname='nested/m000020.ovf')\n"
        "        elif case == 'byte_mismatch':\n"
        "            payload = b'altered field bytes'\n"
        "            info = tarfile.TarInfo('m000020.ovf')\n"
        "            info.size = len(payload)\n"
        "            archive.addfile(info, io.BytesIO(payload))\n",
        encoding="utf-8",
    )
    fake_tar.chmod(0o755)
    invalid_failures: list[str] = []
    for archive_case in (
        "nonarchive",
        "archive_symlink",
        "missing_member",
        "extra_member",
        "nonregular_member",
        "hardlink_member",
        "fifo_member",
        "character_device_member",
        "path_mismatch",
        "byte_mismatch",
    ):
        consumer_marker = tmp_path / f"{archive_case}.consumer-started"
        case_environment = runtime_environment.copy()
        case_environment["PORTABLE_TEST_ARCHIVE_CASE"] = archive_case
        case_environment["PORTABLE_TEST_CONSUMER_MARKER"] = str(
            consumer_marker
        )
        invalid_evidence = tmp_path / f"{archive_case}.evidence.json"
        invalid = subprocess.run(
            [
                sys.executable,
                str(delivery / RUNNER_PATH),
                "--run-id",
                "run-thiele",
                "--initial-state",
                str(user_input),
                "--tar-executable",
                str(fake_tar),
                "--evidence-out",
                str(invalid_evidence),
            ],
            capture_output=True,
            text=True,
            env=case_environment,
            timeout=10,
            check=False,
        )
        invalid_result = json.loads(
            invalid_evidence.read_text(encoding="utf-8")
        )
        if (
            invalid.returncode == 0
            or consumer_marker.exists()
            or invalid_result["command_exit_code"] is not None
        ):
            invalid_failures.append(
                f"{archive_case}:return={invalid.returncode},"
                f"consumer={consumer_marker.exists()},"
                f"command={invalid_result['command_exit_code']}"
            )
        assert invalid_result["workspace_cleaned"] is True
        assert not Path(invalid_result["workspace"]).exists()
    assert not invalid_failures, invalid_failures

    self_attesting_tar = runtime_dir / "tar.exe"
    os.link(fake_tar, self_attesting_tar)
    self_attesting_marker = tmp_path / "self-attesting.consumer-started"
    self_attesting_environment = runtime_environment.copy()
    self_attesting_environment["PORTABLE_TEST_ARCHIVE_CASE"] = (
        "self_attesting_nonarchive"
    )
    self_attesting_environment["PORTABLE_TEST_CONSUMER_MARKER"] = str(
        self_attesting_marker
    )
    self_attesting_evidence = tmp_path / "self-attesting.evidence.json"
    self_attesting = subprocess.run(
        [
            sys.executable,
            str(delivery / RUNNER_PATH),
            "--run-id",
            "run-thiele",
            "--initial-state",
            str(user_input),
            "--tar-executable",
            str(self_attesting_tar),
            "--evidence-out",
            str(self_attesting_evidence),
        ],
        capture_output=True,
        text=True,
        env=self_attesting_environment,
        timeout=10,
        check=False,
    )
    self_attesting_result = json.loads(
        self_attesting_evidence.read_text(encoding="utf-8")
    )
    assert self_attesting.returncode != 0
    assert not self_attesting_marker.exists()
    assert self_attesting_result["command_exit_code"] is None
    self_attesting_tar.unlink()

    fake_tar.write_text("#!/usr/bin/env python3\nraise SystemExit(17)\n", encoding="utf-8")
    fake_tar.chmod(0o755)
    producer_failure_evidence = tmp_path / "thiele-producer-failure.json"
    producer_failed = subprocess.run(
        [
            sys.executable,
            str(delivery / RUNNER_PATH),
            "--run-id",
            "run-thiele",
            "--initial-state",
            str(user_input),
            "--tar-executable",
            str(fake_tar),
            "--evidence-out",
            str(producer_failure_evidence),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    producer_result = json.loads(
        producer_failure_evidence.read_text(encoding="utf-8")
    )
    assert producer_failed.returncode == 17
    assert producer_result["archive_producer_exit_code"] == 17
    assert producer_result["command_exit_code"] is None
    assert producer_result["workspace_cleaned"] is True
    assert not Path(producer_result["workspace"]).exists()

    fake_consumer.write_text("raise SystemExit(29)\n", encoding="utf-8")
    consumer_failure_evidence = tmp_path / "thiele-consumer-failure.json"
    consumer_failed = subprocess.run(
        [
            sys.executable,
            str(delivery / RUNNER_PATH),
            "--run-id",
            "run-thiele",
            "--initial-state",
            str(user_input),
            "--tar-executable",
            real_tar,
            "--evidence-out",
            str(consumer_failure_evidence),
        ],
        capture_output=True,
        text=True,
        env=runtime_environment,
        timeout=10,
        check=False,
    )
    consumer_result = json.loads(
        consumer_failure_evidence.read_text(encoding="utf-8")
    )
    assert consumer_failed.returncode == 29
    assert consumer_result["archive_producer_exit_code"] == 0
    assert consumer_result["command_exit_code"] == 29
    assert consumer_result["workspace_cleaned"] is True
    assert not Path(consumer_result["workspace"]).exists()
    assert user_input.read_bytes() == b"synthetic static field bytes"


def test_field_root_runner_uses_user_tree_exports_only_non_full_outputs_and_cleans(
    tmp_path,
) -> None:
    project = make_recipe_source_tree(tmp_path)
    original = (
        b'ROOT = "D:/historical/mode-map"\n'
        b'OUT_ROOT = "D:/historical/results"\n'
    )
    original_path = "03_mechanism/mode_map/simulation/original/analyze.py"
    portable_path = "03_mechanism/mode_map/simulation/portable/analyze.py"
    launcher_path = "03_mechanism/mode_map/simulation/portable/launch_analyze.py"
    transform = PortableTransform(
        "transform-mode-map",
        "run-mode-map",
        "src/mode_map.py",
        original_path,
        hashlib.sha256(original).hexdigest(),
        portable_path,
        (
            LiteralReplacement(
                b"D:/historical/mode-map", b"${FIELD_ROOT}", 1
            ),
            LiteralReplacement(
                b"D:/historical/results", b"${OUTPUT_ROOT}", 1
            ),
        ),
        "wrapper_plus_transform",
        "wrapper-mode-map",
    )
    run = RunEntry("run-mode-map", "active", original_path, launcher_path)
    consumer = FieldConsumer(
        "src/mode_map.py",
        ("known_ovf_reader",),
        "active",
        "run-mode-map",
        "recipe-1",
        "N/A",
        "specific evidence",
        "wrapper_plus_transform",
        ("python.known_ovf_reader@L1",),
        "src/mode_map.py:L1",
    )
    runtime = PortableRuntimeEntry(
        "runtime-mode-map",
        transform.source_path,
        transform.run_id,
        transform.transform_id,
        "recipe-1",
        RUNNER_PATH,
        launcher_path,
        "field_root_analysis",
        portable_path,
        '["python3","{delivery_root}/shared/runtime/fake_mode_map.py",'
        '"{runtime_entry}","{field_root}","{output_root}"]',
        ("FIELD_ROOT", "OUTPUT_ROOT"),
    )
    contract = PortableContract(
        (run,),
        (transform,),
        (consumer,),
        (make_recipe(consumers=("src/mode_map.py",)),),
        (
            TemporaryDependencyContract(
                "wrapper-mode-map",
                "run-mode-map",
                "transform-mode-map",
                ("input/field-root.alias",),
            ),
        ),
        b'[runtime]\ntemp_prefix = "hopfion-portable-"\n',
        (runtime,),
    )
    with pytest.raises(
        PortableError,
        match="field_root_analysis requires an explicit non-full-field data dependency",
    ):
        validate_portable_contract(contract, project_root=project)

    consumer = replace(
        consumer,
        initial_state_recipe_id="N/A",
        non_full_field_data_id="data-synthetic-field-root",
    )
    runtime = replace(runtime, initial_state_recipe_id="N/A")
    contract = replace(
        contract,
        consumers=(consumer,),
        recipes=(),
        runtime_entries=(runtime,),
    )
    validate_portable_contract(contract, project_root=project)
    delivery = tmp_path / "delivery"
    archived = delivery / original_path
    archived.parent.mkdir(parents=True)
    archived.write_bytes(original)
    fake = delivery / "shared/runtime/fake_mode_map.py"
    fake.parent.mkdir(parents=True)
    fake.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "import sys\n"
        "marker = os.environ.get('PORTABLE_TEST_CHILD_MARKER')\n"
        "if marker:\n"
        "    Path(marker).write_text('started', encoding='utf-8')\n"
        "runtime, field_root, output_root = map(Path, sys.argv[1:4])\n"
        "payload = runtime.read_bytes()\n"
        "if str(field_root).encode() not in payload or str(output_root).encode() not in payload:\n"
        "    raise SystemExit(71)\n"
        "if not (field_root / 'field.bin').is_file() or b'${' in payload:\n"
        "    raise SystemExit(72)\n"
        "(output_root / 'figures').mkdir()\n"
        "(output_root / 'figures/result.json').write_text('{\"ok\": true}', encoding='utf-8')\n",
        encoding="utf-8",
    )
    materialize_portable_contract(contract, staging_root=delivery)
    field_root = tmp_path / "user-field-root"
    field_root.mkdir()
    (field_root / "field.bin").write_bytes(b"synthetic field-root bytes")
    exported = tmp_path / "exported"
    exported.mkdir()
    evidence = tmp_path / "mode-map-evidence.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(delivery / RUNNER_PATH),
            "--run-id",
            "run-mode-map",
            "--field-root",
            str(field_root),
            "--output-dir",
            str(exported),
            "--evidence-out",
            str(evidence),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    result = json.loads(evidence.read_text(encoding="utf-8"))
    assert completed.returncode == 0, completed.stderr
    assert result["command_exit_code"] == 0
    assert result["exported_outputs"] == ["figures/result.json"]
    assert json.loads(
        (exported / "figures/result.json").read_text(encoding="utf-8")
    ) == {"ok": True}
    assert result["workspace_cleaned"] is True
    assert not Path(result["workspace"]).exists()
    assert (field_root / "field.bin").read_bytes() == b"synthetic field-root bytes"

    child_marker = tmp_path / "overlap-child-started"
    overlap_environment = os.environ.copy()
    overlap_environment["PORTABLE_TEST_CHILD_MARKER"] = str(child_marker)
    overlap_evidence = tmp_path / "overlap-evidence.json"
    overlap = subprocess.run(
        [
            sys.executable,
            str(delivery / RUNNER_PATH),
            "--run-id",
            "run-mode-map",
            "--field-root",
            str(field_root),
            "--output-dir",
            str(tmp_path),
            "--evidence-out",
            str(overlap_evidence),
        ],
        capture_output=True,
        text=True,
        env=overlap_environment,
        timeout=10,
        check=False,
    )

    assert overlap.returncode != 0
    assert not child_marker.exists()
    assert not (tmp_path / "figures/result.json").exists()


def test_consumer_detection_evidence_is_deterministic_rule_at_line() -> None:
    discovery = detect_field_consumer(
        "src/run.mx3",
        b'// m.LoadFile("ignored.ovf")\nm.LoadFile("state.ovf")\n',
    )
    generator = detect_field_consumer(
        "src/generate.py",
        b"# first line\ntemplate = 'm.LoadFile(\"{seed}.ovf\")'\n",
    )

    assert discovery is not None
    assert discovery.detection_evidence == ("mx3.m_loadfile@L2",)
    assert generator is not None
    assert generator.detection_evidence == ("python.template_m_loadfile@L2",)


def test_detected_role_may_remain_unresolved_but_publish_fails() -> None:
    discovery = detect_field_consumer(
        "src/run.mx3",
        b'm.LoadFile("state.ovf")\n',
    )
    assert discovery is not None
    row = FieldConsumer(
        source_path="src/run.mx3",
        roles=discovery.roles,
        detection_evidence=discovery.detection_evidence,
        status="unresolved",
        status_evidence="N/A",
        run_id="N/A",
        initial_state_recipe_id="N/A",
        non_full_field_data_id="N/A",
        notes="Scientific status has not yet been reviewed.",
        portable_handling="unresolved",
    )

    validate_field_consumer_registry(
        (discovery,),
        (row,),
        {"src/run.mx3": "copied_active"},
        publish=False,
    )
    with pytest.raises(PortableError, match="unresolved"):
        validate_field_consumer_registry(
            (discovery,),
            (row,),
            {"src/run.mx3": "copied_active"},
            publish=True,
        )


def test_unresolved_touch_cannot_be_forced_active_and_generic_status_evidence_fails(
    tmp_path,
) -> None:
    project = tmp_path / "project"
    evidence = project / "evidence/review.txt"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("Reviewed active leaf.\n", encoding="utf-8")
    dynamic = detect_field_consumer(
        "src/dynamic.py",
        b'suffix = ".ovf"\nopen(root / suffix, "rb")\n',
    )
    assert dynamic is not None
    forced = FieldConsumer(
        source_path="src/dynamic.py",
        roles=dynamic.roles,
        detection_evidence=dynamic.detection_evidence,
        status="active",
        status_evidence="evidence/review.txt:L1",
        run_id="run-dynamic",
        initial_state_recipe_id="recipe-1",
        non_full_field_data_id="N/A",
        notes="Human review attempted.",
        portable_handling="literal_transform",
    )
    with pytest.raises(PortableError, match="unresolved_touch"):
        validate_field_consumer_registry(
            (dynamic,),
            (forced,),
            {"src/dynamic.py": "copied_active"},
            publish=False,
            project_root=project,
        )

    direct = detect_field_consumer(
        "src/run.mx3",
        b'm.LoadFile("state.ovf")\n',
    )
    assert direct is not None
    generic = replace(
        forced,
        source_path="src/run.mx3",
        roles=direct.roles,
        detection_evidence=direct.detection_evidence,
        status_evidence="authoritative-active-source",
    )
    with pytest.raises(PortableError, match="status_evidence"):
        validate_field_consumer_registry(
            (direct,),
            (generic,),
            {"src/run.mx3": "copied_active"},
            publish=False,
            project_root=project,
        )


@pytest.mark.parametrize("suffix", [".json", ".yaml", ".yml", ".toml"])
def test_structured_consumer_candidates_fail_to_unresolved_touch(suffix: str) -> None:
    discovery = detect_field_consumer(
        f"configs/run{suffix}",
        b'initial_state: "temporary/state.ovf"\n',
    )

    assert discovery is not None
    assert discovery.roles == ("unresolved_touch",)
    assert discovery.detection_evidence == (
        "structured.dynamic_field_reference@L1",
    )


def test_extensionless_shebang_manager_is_discovered() -> None:
    discovery = detect_field_consumer(
        "jobs/launch",
        b"#!/bin/sh\nmumax3 run.mx3\n",
    )

    assert discovery is not None
    assert discovery.roles == ("shell_manager",)
    assert discovery.detection_evidence == ("shell.field_manager@L2",)


def test_canonical_initial_state_ledger_has_seven_documented_evidence_rows() -> None:
    project = Path(__file__).resolve().parents[2]
    ledger = (
        project
        / "95_shared_scripts/handoff_delivery/initial_state_recipes.csv"
    )

    rows = load_initial_state_recipes(ledger)
    validate_initial_state_recipes(rows, project_root=project)

    assert {row.recipe_id for row in rows} == {
        "init-drift-axisx-bgmx-r3r2",
        "init-analytic-axisz-r8r4",
        "init-analytic-axisz-r12r5",
        "init-small-unknown",
        "init-centered-ku0",
        "init-centered-ku10k",
        "init-centered-ku50k",
    }
    assert {row.verification_status for row in rows} == {"documented_only"}
    by_id = {row.recipe_id: row for row in rows}
    assert by_id["init-drift-axisx-bgmx-r3r2"].generator_script == "N/A"
    assert by_id["init-small-unknown"].generator_script == "N/A"
    assert "UNKNOWN" in by_id["init-small-unknown"].generator_parameters
    for recipe_id in (
        "init-centered-ku0",
        "init-centered-ku10k",
        "init-centered-ku50k",
    ):
        assert "unverified" in by_id[recipe_id].notes.casefold()


def test_canonical_consumer_ledger_matches_current_discovery_and_only_audited_leaves() -> None:
    from handoff_delivery.builder import (
        _load_project_figure_recipes,
        _route_figure_assets,
    )
    from handoff_delivery.source_specs import enumerate_required_assets

    project = Path(__file__).resolve().parents[2]
    figure_recipes = _load_project_figure_recipes(project)
    inventory = enumerate_required_assets(project)
    inventory = _route_figure_assets(inventory, figure_recipes)
    copied = tuple(
        row
        for row in inventory
        if row.target_path is not None
        and row.disposition in {"copied_active", "copied_archive"}
    )
    discoverable_suffixes = {
        ".mx3",
        ".py",
        ".sh",
        ".ps1",
        ".m",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".template",
    }
    candidates = tuple(
        row.source_path
        for row in copied
        if Path(row.source_path).suffix.casefold() in discoverable_suffixes
        or not Path(row.source_path).suffix
    )
    discoveries = discover_full_field_consumers(project, candidates)
    registry = load_field_consumer_registry(
        project / "95_shared_scripts/handoff_delivery/full_field_consumers.csv"
    )
    dispositions = {row.source_path: row.disposition for row in copied}

    validate_field_consumer_registry(
        discoveries,
        registry,
        dispositions,
        publish=False,
        project_root=project,
    )

    fm = "04_frustrated_fm_foundation/20260105_frustrated_fm"
    spin = f"{fm}/spin_wave_dynamics"
    mode_map_path = (
        "06_eigenmode_frequency_mechanism/hopfion_mode_map_20260608/"
        "analysis/mode_map_analysis.py"
    )
    expected_active = {
        f"{fm}/drift_experiments/bg_mx_axis_x_stable/run.mx3",
        *(f"{fm}/centered_stability_test/stability_Ku{ku}.mx3" for ku in ("0", "10k", "50k")),
        *(
            f"{fm}/anisotropy_study/ku_critical_sweep/R8r4_Ku{ku}.mx3"
            for ku in ("0", "5k", "10k", "20k", "30k", "40k", "50k", "52k", "55k", "56k", "57k", "58k")
        ),
        f"{fm}/size_sweep/R8r4_Ku0.mx3",
        f"{fm}/size_sweep/R12r5_Ku0.mx3",
        f"{fm}/anisotropy_study/size_vs_ku/Ku1_0.0e+00_Ms_1.5000e+05.mx3",
        *(
            f"{spin}/drive_selection/plane_wave/{name}.mx3"
            for name in ("sw_srcX_vibX", "sw_srcX_vibZ", "sw_srcY_vibX", "sw_srcZ_vibX", "sw_srcZ_vibZ")
        ),
        *(
            f"{spin}/freq_sweep/plane_wave/srcX/02ns/sw_f{frequency}GHz.mx3"
            for frequency in range(100, 1100, 100)
        ),
        *(
            f"{spin}/freq_sweep/plane_wave/srcZ/{'sw_srcZ_fine_f' if frequency in {75, 1100, 1300, 1500} else 'sw_srcZ_f'}{frequency}GHz.mx3"
            for frequency in (75, 100, 500, 900, 1000, 1100, 1300, 1500)
        ),
        *(
            f"{spin}/amplitude_sweep/plane_wave/sw_B{label}T.mx3"
            for label in ("0p05", "0p1", "0p2", "0p5", "1p0", "2p0")
        ),
        *(
            f"{spin}/freq_sweep/point_source/src{axis}/ps_src{axis}_f{frequency}GHz.mx3"
            for axis in ("X", "Z")
            for frequency in range(100, 1100, 100)
        ),
        f"{spin}/multisource_control/baseline/sw_srcZ_neg_f200GHz.mx3",
        "08_lif_neuron_device_application/lif_neuron_hopfion/gradient_ku_verification/drive_release_test/uniform_control/uniform_ku_drive_release.mx3",
        "08_lif_neuron_device_application/lif_neuron_hopfion/gradient_ku_verification/drive_release_test/with_gradient/gradient_ku_drive_release.mx3",
        "07_thiele_theory_model/results_thiele_GD_convergence_20260703/compute_GD_convergence.py",
    }
    active = {row.source_path for row in registry if row.status == "active"}
    nonactive = {row.source_path for row in registry if row.status in {"reference_only", "archive"}}

    assert len(discoveries) == 326
    assert active == expected_active
    assert len(active) == 72
    assert nonactive == {row.source_path for row in discoveries} - expected_active
    assert len(nonactive) == 254

    mode_map = next(row for row in registry if row.source_path == mode_map_path)
    mode_map_discovery = next(
        row for row in discoveries if row.source_path == mode_map_path
    )
    assert mode_map.status == "reference_only"
    assert (
        mode_map.status_evidence,
        mode_map.run_id,
        mode_map.initial_state_recipe_id,
        mode_map.non_full_field_data_id,
        mode_map.portable_handling,
    ) == (
        "95_shared_scripts/handoff_delivery/document_registry.md:L15",
        "N/A", "N/A", "N/A", "reference_only",
    )
    for required_note in (
        "six current-valid figure recipes",
        "four complete-field roots",
        "excluded from the delivery",
        "ROOT mapping becomes invalid",
        "srcX-1000 GHz mx3 is missing",
        "Task8",
    ):
        assert required_note in mode_map.notes
    assert len(
        tuple(
            row
            for row in figure_recipes
            if row.plot_script_path == mode_map_path
        )
    ) == 6
    validate_field_consumer_registry(
        (mode_map_discovery,),
        (mode_map,),
        {mode_map_path: dispositions[mode_map_path]},
        publish=True,
        project_root=project,
    )
    validate_field_consumer_registry(
        discoveries,
        registry,
        dispositions,
        publish=True,
        project_root=project,
    )


def test_canonical_recipe_consumer_edges_equal_all_active_leaf_dependencies() -> None:
    project = Path(__file__).resolve().parents[2]
    ledger_root = project / "95_shared_scripts/handoff_delivery"
    consumers = load_field_consumer_registry(
        ledger_root / "full_field_consumers.csv"
    )
    recipes = load_initial_state_recipes(
        ledger_root / "initial_state_recipes.csv"
    )

    validate_initial_state_coverage(consumers, recipes)

    active = tuple(row for row in consumers if row.status == "active")
    assert len(active) == 72
    assert all(row.initial_state_recipe_id != "N/A" for row in active)
    assert sum(row.portable_handling == "literal_transform" for row in active) == 71
    wrappers = tuple(
        row for row in active if row.portable_handling == "wrapper_plus_transform"
    )
    assert len(wrappers) == 1
    assert wrappers[0].source_path == (
        "07_thiele_theory_model/results_thiele_GD_convergence_20260703/"
        "compute_GD_convergence.py"
    )
    assert sum(
        row.initial_state_recipe_id == "init-centered-ku10k" for row in active
    ) == 54
