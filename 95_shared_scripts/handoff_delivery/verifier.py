"""Independent, fail-closed G1--G5 verification for a staged handoff tree.

``verify`` is deliberately read-only.  Build-time report and checksum writes are
separate, exclusive operations so a later verification cannot mutate delivery
evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import csv
from dataclasses import asdict, dataclass, replace
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shlex
import stat
from types import MappingProxyType
from typing import Any

from .derived import (
    DERIVED_EVIDENCE_COLUMNS,
    DERIVED_PRODUCER_SCRIPT,
    DerivedDataError,
    DerivedRecipe,
    parse_derived_evidence_rows,
    validate_derived_evidence_bindings,
)
from .inventory import InspectionLimits, _inspect_open_candidate
from .lineage import (
    FigureRecipe,
    STORY_MODULES,
    ManifestKeys,
    discover_independent_figures,
    load_figure_recipes,
    route_figure,
    validate_figure_closure,
    validate_figure_coverage,
    validate_recipe_ledger,
)
from .models import IdList, ManifestError, require_relative_path
from .portable import (
    FIELD_CONSUMER_COLUMNS,
    INITIAL_STATE_RECIPE_COLUMNS,
    PORTABLE_TRANSFORM_COLUMNS,
    PORTABLE_WRAPPER_COLUMNS,
    _PinnedDeliveryScan,
    _PinnedTreeEntry,
    _G4_SUFFIXES,
    _is_g4_executable_path,
    _load_structured_payload,
    _scan_manifest_csv_payload,
    _scan_python_executable,
    _snapshot_delivery_descriptor,
    PortableContract,
    PortableError,
    apply_portable_transform,
    bind_initial_state_recipes_to_package,
    discover_full_field_consumers,
    detect_field_consumer,
    field_consumers_csv,
    packaged_initial_state_recipes_csv,
    portable_transforms_csv,
    portable_launcher_script,
    portable_runner_script,
    portable_wrappers_csv,
    reverse_portable_transform,
    scan_delivery_absolute_paths,
    scan_executable_text,
    scan_structured_values,
    validate_field_consumer_registry,
    validate_packaged_initial_state_files,
    validate_portable_contract,
)
from .source_specs import (
    EXACT_SOURCE_SPECS,
    TREE_SOURCE_SPECS,
    ExactSourceSpec,
    AnchoredRoot,
    RequiredAssetInventory,
    RequiredAssetRow,
    SourceSpecError,
    TreeSourceSpec,
    enumerate_required_assets,
)
from .redraw import RedrawRecipe


class VerificationError(RuntimeError):
    """Raised when verifier inputs or immutable evidence cannot be trusted."""


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """One immutable gate result with deterministic, human-readable evidence."""

    gate: str
    passed: bool
    counts: tuple[tuple[str, int], ...]
    findings: tuple[str, ...]
    evidence_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.gate not in {"G1", "G2", "G3", "G4", "G5"}:
            raise VerificationError(f"unknown gate: {self.gate!r}")
        if not isinstance(self.passed, bool):
            raise VerificationError("passed must be a boolean")
        if not isinstance(self.counts, tuple) or not all(
            isinstance(row, tuple)
            and len(row) == 2
            and isinstance(row[0], str)
            and row[0]
            and isinstance(row[1], int)
            and row[1] >= 0
            for row in self.counts
        ):
            raise VerificationError("counts must be immutable name/nonnegative-int pairs")
        if len({name for name, _ in self.counts}) != len(self.counts):
            raise VerificationError("count names must be unique")
        if not isinstance(self.findings, tuple) or not all(
            isinstance(item, str) and item for item in self.findings
        ):
            raise VerificationError("findings must be an immutable string tuple")
        if not isinstance(self.evidence_paths, tuple) or not all(
            isinstance(item, str) and item for item in self.evidence_paths
        ):
            raise VerificationError("evidence_paths must be an immutable string tuple")


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
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MARKDOWN_LABELED_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
FIXED_ROOT_DIRECTORIES = frozenset((*STORY_MODULES, "00_handoff", "90_archive", "shared"))
ACTIVE_STATUS_TOKENS = frozenset(("failed", "interrupted", "incomplete", "superseded"))
README_PLACEHOLDERS = (
    "保留的分类目录",
    "placeholder",
    "claude code",
    "代理说明",
    "学校模板说明",
)
ACTIVE_DENY_TOKENS = (
    "agents.md", "claude.md", "gemini.md", "school_template", "thesis_template",
    "generated_preview", "preview", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".handoff-staging", ".copying", ".tmp", "temporary_build",
)
INVALID_FIGURE_STATUSES = frozenset(("superseded", "failed", "unverified"))
INVALID_WARNING_TOKENS = (
    "warning", "警告", "历史", "失效", "推翻", "勿复用", "do not reuse",
    "do_not_reuse", "superseded", "failed", "invalid",
)
FINAL_EVIDENCE_PATHS = frozenset(
    {
        "00_handoff/verification_report.json",
        "00_handoff/SHA256SUMS.txt",
    }
)


@dataclass(slots=True)
class _CapturedPackage:
    """One pinned no-follow snapshot with bounded, verified on-demand reads."""

    root_descriptor: int
    snapshot: tuple[_PinnedTreeEntry, ...]
    rows: Mapping[str, _PinnedTreeEntry]

    @property
    def files(self) -> tuple[str, ...]:
        return tuple(row.relative_path for row in self.snapshot if row.path_type == "file")

    @property
    def directories(self) -> frozenset[str]:
        return frozenset(
            row.relative_path for row in self.snapshot if row.path_type == "directory"
        )

    def read_bytes(self, relative: str) -> bytes:
        normalized = _relative(relative, context="captured package path")
        try:
            expected = self.rows[normalized]
        except KeyError as error:
            raise VerificationError(
                f"captured package has no regular file: {normalized}"
            ) from error
        if expected.path_type != "file":
            raise VerificationError(f"captured package path is not a file: {normalized}")
        parts = PurePosixPath(normalized).parts
        directory = os.dup(self.root_descriptor)
        descriptor = -1
        try:
            for part in parts[:-1]:
                next_directory = os.open(
                    part,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY
                    | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=directory,
                )
                os.close(directory)
                directory = next_directory
            descriptor = os.open(
                parts[-1],
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=directory,
            )
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != expected.mode
                or before.st_size != expected.size
            ):
                raise VerificationError(
                    f"captured package file metadata changed: {normalized}"
                )
            buffer = bytearray()
            while chunk := os.read(descriptor, 1024 * 1024):
                buffer.extend(chunk)
            after = os.fstat(descriptor)
            if _stat_identity(before) != _stat_identity(after):
                raise VerificationError(
                    f"captured package file changed while reading: {normalized}"
                )
            payload = bytes(buffer)
            if (
                len(payload) != expected.size
                or hashlib.sha256(payload).hexdigest() != expected.sha256
            ):
                raise VerificationError(
                    f"captured package bytes differ from pinned snapshot: {normalized}"
                )
            return payload
        except OSError as error:
            raise VerificationError(
                f"cannot read captured package file without symlink traversal: {normalized}"
            ) from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(directory)

    def read_text(self, relative: str) -> str:
        try:
            return self.read_bytes(relative).decode("utf-8", errors="strict")
        except UnicodeError as error:
            raise VerificationError(f"cannot decode captured package file: {relative}") from error

    def sha256(self, relative: str) -> str:
        return hashlib.sha256(self.read_bytes(relative)).hexdigest()

    def exists(self, relative: str) -> bool:
        normalized = _relative(relative, context="captured package path")
        return normalized in self.rows

    def close(self) -> None:
        if self.root_descriptor >= 0:
            descriptor = self.root_descriptor
            self.root_descriptor = -1
            os.close(descriptor)


def _stat_identity(row: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        row.st_dev,
        row.st_ino,
        stat.S_IFMT(row.st_mode),
        stat.S_IMODE(row.st_mode),
        row.st_size,
        row.st_mtime_ns,
        row.st_ctime_ns,
    )


def _capture_package(
    root_descriptor: int,
    *,
    expected_snapshot: Sequence[_PinnedTreeEntry] | None,
) -> _CapturedPackage:
    """Capture every package byte once through openat/O_NOFOLLOW descriptors."""

    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not no_follow or not directory_flag:
        raise VerificationError("captured verification requires O_NOFOLLOW/O_DIRECTORY")
    snapshot: list[_PinnedTreeEntry] = []

    def walk(descriptor: int, prefix: PurePosixPath) -> None:
        try:
            before_directory = os.fstat(descriptor)
            with os.scandir(descriptor) as iterator:
                entries = tuple(sorted(iterator, key=lambda item: item.name))
            for entry in entries:
                relative_path = prefix / entry.name
                relative = relative_path.as_posix()
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(metadata.st_mode):
                    raise VerificationError(f"captured package refuses symlink: {relative}")
                if stat.S_ISDIR(metadata.st_mode):
                    child = os.open(
                        entry.name,
                        os.O_RDONLY | no_follow | directory_flag | getattr(os, "O_CLOEXEC", 0),
                        dir_fd=descriptor,
                    )
                    try:
                        opened = os.fstat(child)
                        if _stat_identity(metadata) != _stat_identity(opened):
                            raise VerificationError(
                                f"captured directory changed while opening: {relative}"
                            )
                        snapshot.append(
                            _PinnedTreeEntry(
                                relative, "directory", stat.S_IMODE(opened.st_mode), 0, ""
                            )
                        )
                        walk(child, relative_path)
                    finally:
                        os.close(child)
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    raise VerificationError(
                        f"captured package refuses non-regular entry: {relative}"
                    )
                file_descriptor = os.open(
                    entry.name,
                    os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=descriptor,
                )
                try:
                    opened_before = os.fstat(file_descriptor)
                    if _stat_identity(metadata) != _stat_identity(opened_before):
                        raise VerificationError(
                            f"captured file changed while opening: {relative}"
                        )
                    digest = hashlib.sha256()
                    size = 0
                    while chunk := os.read(file_descriptor, 1024 * 1024):
                        digest.update(chunk)
                        size += len(chunk)
                    opened_after = os.fstat(file_descriptor)
                    if _stat_identity(opened_before) != _stat_identity(opened_after):
                        raise VerificationError(
                            f"captured file changed while reading: {relative}"
                        )
                    if size != opened_after.st_size:
                        raise VerificationError(
                            f"captured file size changed while reading: {relative}"
                        )
                    snapshot.append(
                        _PinnedTreeEntry(
                            relative,
                            "file",
                            stat.S_IMODE(opened_after.st_mode),
                            size,
                            digest.hexdigest(),
                        )
                    )
                finally:
                    os.close(file_descriptor)
            after_directory = os.fstat(descriptor)
            if _stat_identity(before_directory) != _stat_identity(after_directory):
                raise VerificationError(
                    f"captured directory changed while enumerating: {prefix.as_posix() or '.'}"
                )
        except OSError as error:
            raise VerificationError(
                f"cannot capture package directory: {prefix.as_posix() or '.'}"
            ) from error

    descriptor = os.dup(root_descriptor)
    try:
        walk(descriptor, PurePosixPath())
    finally:
        os.close(descriptor)
    captured_snapshot = tuple(snapshot)
    if expected_snapshot is not None and captured_snapshot != tuple(expected_snapshot):
        raise VerificationError(
            "captured package snapshot differs from materialized staging snapshot"
        )
    rows = MappingProxyType({row.relative_path: row for row in captured_snapshot})
    return _CapturedPackage(os.dup(root_descriptor), captured_snapshot, rows)


def _root_path(delivery_root: Path | str, root_descriptor: int | None) -> Path:
    root = Path(delivery_root)
    if root_descriptor is not None:
        try:
            metadata = os.fstat(root_descriptor)
        except OSError as error:
            raise VerificationError("cannot inspect pinned delivery descriptor") from error
        if not stat.S_ISDIR(metadata.st_mode):
            raise VerificationError("pinned delivery descriptor is not a directory")
        return Path(f"/proc/self/fd/{root_descriptor}")
    try:
        metadata = root.lstat()
    except OSError as error:
        raise VerificationError(f"cannot inspect delivery root: {root}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise VerificationError("delivery root must be one real directory")
    return root


def _relative(raw: str, *, context: str) -> str:
    try:
        return require_relative_path(raw).as_posix()
    except ManifestError as error:
        raise VerificationError(f"{context}: {error}") from error


def _parse_csv_payload(
    raw: bytes,
    relative: str,
    columns: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
    try:
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
            raise VerificationError(
                f"{relative}: CSV must be UTF-8 without BOM and use LF line endings"
            )
        payload = raw.decode("utf-8", errors="strict")
        with io.StringIO(payload, newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != columns:
                raise VerificationError(
                    f"{relative}: header must exactly match the versioned schema"
                )
            rows = tuple(reader)
    except (OSError, UnicodeError, csv.Error) as error:
        raise VerificationError(f"cannot read {relative}") from error
    for number, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise VerificationError(f"{relative}:{number}: extra or missing CSV cells")
    return rows


def _read_csv(
    package: _CapturedPackage,
    relative: str,
    columns: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
    return _parse_csv_payload(package.read_bytes(relative), relative, columns)


def _read_project_anchored(project_root: Path, relative: str) -> bytes:
    descriptor = -1
    try:
        with AnchoredRoot(project_root, error_type=VerificationError) as anchor:
            descriptor = anchor.open_regular(relative)
            before = os.fstat(descriptor)
            buffer = bytearray()
            while chunk := os.read(descriptor, 1024 * 1024):
                buffer.extend(chunk)
            after = os.fstat(descriptor)
            if _stat_identity(before) != _stat_identity(after):
                raise VerificationError(
                    f"project source changed while reading: {relative}"
                )
            return bytes(buffer)
    except SourceSpecError as error:
        raise VerificationError(f"cannot read anchored project source: {relative}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _unique(rows: Sequence[Mapping[str, str]], key: str, *, context: str) -> None:
    values = tuple(row[key] for row in rows)
    if any(not value for value in values) or len(values) != len(set(values)):
        raise VerificationError(f"{context}: {key} values must be non-empty and unique")


def _sha_file(path: Path) -> str:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise VerificationError(f"cannot inspect file: {path}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise VerificationError(f"not one real regular file: {path}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise VerificationError(f"cannot hash file: {path}") from error
    return digest.hexdigest()


def _ids(raw: str, *, allow_na: bool = True) -> tuple[str, ...]:
    if raw == "N/A" and allow_na:
        return ()
    try:
        return IdList.parse(raw).items
    except ManifestError as error:
        raise VerificationError(f"invalid manifest ID list: {raw!r}") from error


def _result(
    gate: str,
    findings: list[str],
    counts: Mapping[str, int],
    evidence: Sequence[str],
) -> VerificationResult:
    return VerificationResult(
        gate=gate,
        passed=not findings,
        counts=tuple(sorted(counts.items())),
        findings=tuple(sorted(dict.fromkeys(findings))),
        evidence_paths=tuple(sorted(dict.fromkeys(evidence))),
    )


def _gate_g1(package: _CapturedPackage) -> VerificationResult:
    findings: list[str] = []
    evidence = ["00_handoff/DATA_MANIFEST.csv"]
    declarations: dict[str, dict[str, object]] = {}
    try:
        data_rows = _read_csv(package, "00_handoff/DATA_MANIFEST.csv", DATA_COLUMNS)
        _unique(data_rows, "data_id", context="DATA_MANIFEST.csv")
        for row in data_rows:
            relative = _relative(row["path"], context="DATA_MANIFEST.path")
            if relative in declarations:
                raise VerificationError(f"duplicate DATA_MANIFEST path: {relative}")
            if row["is_complete_field"] not in {"true", "false"}:
                raise VerificationError(f"invalid is_complete_field for {row['data_id']}")
            declaration: dict[str, object] = dict(row)
            declaration["is_complete_field"] = row["is_complete_field"] == "true"
            if (
                row["data_kind"] in {"figure_slice", "figure_line", "scalar_summary"}
                or declaration["is_complete_field"]
            ):
                declarations[relative] = declaration
    except VerificationError as error:
        findings.append(str(error))

    checked = 0
    for entry in package.snapshot:
        if (
            entry.path_type != "file"
            or entry.relative_path in FINAL_EVIDENCE_PATHS
        ):
            continue
        relative = entry.relative_path
        checked += 1
        payload = package.read_bytes(relative)
        result = _inspect_open_candidate(
            Path(relative),
            io.BytesIO(payload),
            digest=entry.sha256,
            size=entry.size,
            declaration=declarations.get(relative),
            limits=InspectionLimits(),
        )
        if result.sha256 != entry.sha256 or result.size != entry.size:
            findings.append(f"{relative}: inspection bytes differ from captured snapshot")
            continue
        if result.decision != "include":
            findings.append(f"{relative}: {result.reason}")
    return _result("G1", findings, {"regular_files_checked": checked}, evidence)


def _validated_comparison(method: str, tolerance: str) -> bool:
    if method == "sha256_exact":
        return tolerance == "exact"
    if method == "input_hash_validation":
        return tolerance == "exact"
    if method != "numpy.testing.assert_allclose":
        return False
    parts = tolerance.split(";")
    if len(parts) != 2:
        return False
    values: dict[str, float] = {}
    try:
        for part in parts:
            key, separator, raw = part.partition("=")
            if not separator or key not in {"rtol", "atol"} or key in values:
                return False
            value = float(raw)
            if value < 0 or value != value or value in {float("inf"), float("-inf")}:
                return False
            values[key] = value
    except ValueError:
        return False
    return set(values) == {"rtol", "atol"}


def _load_captured_figures(
    package: _CapturedPackage, relative: str
) -> tuple[FigureRecipe, ...]:
    rows = _read_csv(package, relative, tuple(FigureRecipe.__dataclass_fields__))
    try:
        return tuple(FigureRecipe(**row) for row in rows)
    except (TypeError, ValueError, ManifestError) as error:
        raise VerificationError(f"cannot load captured figure manifest: {relative}") from error


def _discover_captured_figures(package: _CapturedPackage) -> tuple[str, ...]:
    discovered = []
    for relative in package.files:
        path = PurePosixPath(relative)
        suffix = path.suffix.casefold()
        if suffix in {".png", ".svg"} or (
            suffix == ".pdf" and "figures" in path.parts
        ):
            discovered.append(relative)
    return tuple(sorted(discovered))


def _validate_derived_evidence_gate(
    package: _CapturedPackage,
    project_root: Path,
    source_inventory: RequiredAssetInventory | None,
    data_rows: Sequence[Mapping[str, str]],
    figures: Sequence[FigureRecipe],
    expected_recipes: Sequence[DerivedRecipe] | None,
) -> int:
    """Bind minimal derived products to Task4 recipes and pinned source bytes."""
    evidence_path = "00_handoff/DERIVED_DATA_EVIDENCE.csv"
    source_by_path = {
        row.source_path: row for row in source_inventory.rows
    } if source_inventory is not None else {}
    producer_source = source_by_path.get(DERIVED_PRODUCER_SCRIPT)
    producer_target = None if producer_source is None else producer_source.target_path
    data_by_id = {row["data_id"]: row for row in data_rows}
    declared_derived = {
        row["data_id"]: row
        for row in data_rows
        if producer_target is not None and row["producer_script"] == producer_target
    }
    present = package.exists(evidence_path)
    if expected_recipes is not None and not expected_recipes:
        if present:
            raise VerificationError(
                "derived evidence exists although the build plan has no derived recipes"
            )
        if declared_derived:
            raise VerificationError(
                "DATA_MANIFEST declares derived products absent from the build plan"
            )
        return 0
    if not present:
        if expected_recipes or declared_derived:
            raise VerificationError("required DERIVED_DATA_EVIDENCE.csv is missing")
        return 0

    raw_rows = _read_csv(package, evidence_path, DERIVED_EVIDENCE_COLUMNS)
    try:
        typed = parse_derived_evidence_rows(raw_rows)
    except DerivedDataError as error:
        raise VerificationError(f"invalid derived evidence: {error}") from error
    evidence_by_data = {row.output_data_id: row for row in typed}
    if len(evidence_by_data) != len(typed):
        raise VerificationError("derived evidence output data IDs must be unique")

    if expected_recipes is None:
        reconstructed: list[DerivedRecipe] = []
        for row in typed:
            data = data_by_id.get(row.output_data_id)
            if data is None:
                raise VerificationError(
                    f"derived evidence references unknown data ID: {row.output_data_id}"
                )
            try:
                reconstructed.append(
                    DerivedRecipe(
                        recipe_id=row.recipe_id,
                        output_data_id=row.output_data_id,
                        source_path=row.source_path,
                        source_sha256=row.source_sha256,
                        producer_script=row.producer_script,
                        producer_sha256=row.producer_sha256,
                        selector_kind=row.selector_kind,
                        selector_json=row.selector_json,
                        output_path=row.output_path,
                        output_format=data["format"],
                        output_sha256=row.output_sha256,
                        shape=data["shape"],
                        columns=data["columns"],
                        units=data["units"],
                        coordinate_origin=row.coordinate_origin,
                        coordinate_spacing=row.coordinate_spacing,
                        coordinate_units=row.coordinate_units,
                        parent_figure_ids=";".join(row.parent_figure_ids),
                        parent_data_ids=";".join(row.parent_data_ids),
                        environment_command=row.environment_command,
                        is_complete_field="false",
                        notes=data["notes"],
                    )
                )
            except DerivedDataError as error:
                raise VerificationError(
                    f"cannot reconstruct derived recipe {row.recipe_id}: {error}"
                ) from error
        recipes = tuple(reconstructed)
    else:
        recipes = tuple(expected_recipes)
    try:
        validate_derived_evidence_bindings(recipes, typed)
    except DerivedDataError as error:
        raise VerificationError(f"derived evidence binding failed: {error}") from error

    recipe_data_ids = {row.output_data_id for row in recipes}
    if set(evidence_by_data) != recipe_data_ids:
        raise VerificationError("derived recipe/evidence data coverage mismatch")
    if declared_derived and set(declared_derived) != recipe_data_ids:
        raise VerificationError("derived DATA_MANIFEST coverage mismatch")

    figure_by_id = {row.figure_id: row for row in figures}
    selector_kind_to_data_kind = {
        "slice": "figure_slice",
        "line": "figure_line",
        "scalar": "scalar_summary",
    }
    actual_figure_outputs: dict[str, set[str]] = {
        figure_id: set() for figure_id in figure_by_id
    }
    for row in typed:
        data = data_by_id.get(row.output_data_id)
        if data is None:
            raise VerificationError(
                f"derived evidence references unknown data ID: {row.output_data_id}"
            )
        if (
            data["path"] != row.output_path
            or data["sha256"] != row.output_sha256
            or data["data_kind"] != selector_kind_to_data_kind[row.selector_kind]
            or data["is_complete_field"] != "false"
        ):
            raise VerificationError(
                f"derived DATA_MANIFEST binding mismatch: {row.output_data_id}"
            )
        package_row = package.rows.get(row.output_path)
        if (
            package_row is None
            or package_row.path_type != "file"
            or package_row.sha256 != row.output_sha256
            or package_row.size != row.output_size
        ):
            raise VerificationError(
                f"derived package output mismatch: {row.output_data_id}"
            )
        if (
            data["parent_source"] != row.source_path
            or data["parent_sha256"] != row.source_sha256
        ):
            raise VerificationError(
                f"derived parent source mismatch: {row.output_data_id}"
            )
        source_row = source_by_path.get(row.source_path)
        actual_source_sha = hashlib.sha256(
            _read_project_anchored(project_root, row.source_path)
        ).hexdigest()
        if (
            source_row is None
            or (source_row.sha256 and source_row.sha256 != row.source_sha256)
            or actual_source_sha != row.source_sha256
        ):
            raise VerificationError(
                f"derived source SHA256 mismatch: {row.output_data_id}"
            )
        producer_row = source_by_path.get(row.producer_script)
        actual_producer_sha = hashlib.sha256(
            _read_project_anchored(project_root, row.producer_script)
        ).hexdigest()
        if (
            producer_row is None
            or producer_row.target_path is None
            or producer_row.sha256 != row.producer_sha256
            or actual_producer_sha != row.producer_sha256
            or data["producer_script"] != producer_row.target_path
            or package.sha256(producer_row.target_path) != row.producer_sha256
        ):
            raise VerificationError(
                f"derived producer binding mismatch: {row.output_data_id}"
            )
        if any(parent not in data_by_id for parent in row.parent_data_ids):
            raise VerificationError(
                f"derived parent data FK mismatch: {row.output_data_id}"
            )
        for figure_id in row.parent_figure_ids:
            figure = figure_by_id.get(figure_id)
            if figure is None:
                raise VerificationError(
                    f"derived parent figure FK mismatch: {row.output_data_id}"
                )
            figure_parents = set(_ids(figure.parent_data_ids))
            if not set(row.parent_data_ids) <= figure_parents:
                raise VerificationError(
                    f"derived parent data do not match figure: {figure_id}"
                )
            actual_figure_outputs[figure_id].add(row.output_data_id)
    for figure in figures:
        declared = set(_ids(figure.derived_data_ids))
        if declared != actual_figure_outputs[figure.figure_id]:
            raise VerificationError(
                f"derived figure coverage mismatch: {figure.figure_id}"
            )
    return len(typed)


def _gate_g2(
    package: _CapturedPackage,
    project_root: Path,
    source_inventory: RequiredAssetInventory | None,
    source_error: str | None,
    expected_derived_recipes: Sequence[DerivedRecipe] | None,
) -> VerificationResult:
    findings: list[str] = [] if source_error is None else [source_error]
    source_by_path = {
        row.source_path: row for row in source_inventory.rows
    } if source_inventory is not None else {}
    evidence = [
        "00_handoff/FIGURE_MANIFEST.csv",
        "00_handoff/DATA_MANIFEST.csv",
        "00_handoff/DOCUMENT_MANIFEST.csv",
        "00_handoff/RUN_MANIFEST.csv",
        "00_handoff/REQUIRED_ASSETS.csv",
        "00_handoff/INITIAL_STATE_RECIPES.csv",
        "00_handoff/FIGURE_REDRAW_EVIDENCE.csv",
    ]
    figures = ()
    data_rows: tuple[dict[str, str], ...] = ()
    document_rows: tuple[dict[str, str], ...] = ()
    redraw_rows: tuple[dict[str, str], ...] = ()
    derived_rows = 0
    try:
        _read_csv(
            package,
            "00_handoff/FIGURE_MANIFEST.csv",
            tuple(FigureRecipe.__dataclass_fields__),
        )
        figures = _load_captured_figures(package, "00_handoff/FIGURE_MANIFEST.csv")
        data_rows = _read_csv(package, "00_handoff/DATA_MANIFEST.csv", DATA_COLUMNS)
        document_rows = _read_csv(
            package, "00_handoff/DOCUMENT_MANIFEST.csv", DOCUMENT_COLUMNS
        )
        runs = _read_csv(package, "00_handoff/RUN_MANIFEST.csv", RUN_COLUMNS)
        assets = _read_csv(package, "00_handoff/REQUIRED_ASSETS.csv", REQUIRED_COLUMNS)
        recipes = _read_csv(
            package, "00_handoff/INITIAL_STATE_RECIPES.csv", INITIAL_STATE_RECIPE_COLUMNS
        )
        redraw_rows = _read_csv(
            package, "00_handoff/FIGURE_REDRAW_EVIDENCE.csv", REDRAW_COLUMNS
        )
        for rows, key, context in (
            (data_rows, "data_id", "DATA_MANIFEST"),
            (document_rows, "document_id", "DOCUMENT_MANIFEST"),
            (runs, "run_id", "RUN_MANIFEST"),
            (assets, "asset_id", "REQUIRED_ASSETS"),
            (recipes, "recipe_id", "INITIAL_STATE_RECIPES"),
            (redraw_rows, "redraw_id", "FIGURE_REDRAW_EVIDENCE"),
        ):
            _unique(rows, key, context=context)
        data_paths = {row["data_id"]: _relative(row["path"], context="data path") for row in data_rows}
        keys = ManifestKeys(
            data_ids=frozenset(data_paths),
            run_ids=frozenset(row["run_id"] for row in runs),
            theory_asset_ids=frozenset(
                row["asset_id"]
                for row in assets
                if row["status"] in {"copied_active", "copied_archive"}
            ),
            initial_state_recipe_ids=frozenset(row["recipe_id"] for row in recipes),
            document_ids=frozenset(row["document_id"] for row in document_rows),
            data_paths=data_paths,
        )
        for run in runs:
            for field_name in ("table_data_ids", "other_data_ids"):
                dependencies = _ids(run[field_name])
                missing_dependencies = sorted(set(dependencies) - keys.data_ids)
                if missing_dependencies:
                    raise VerificationError(
                        f"run dependency FK mismatch: {run['run_id']}:{field_name}: "
                        f"{missing_dependencies!r}"
                    )
            recipe_id = run["initial_state_recipe_id"]
            if (
                recipe_id != "N/A"
                and recipe_id not in keys.initial_state_recipe_ids
            ):
                raise VerificationError(
                    "run dependency FK mismatch: "
                    f"{run['run_id']}:initial_state_recipe_id:{recipe_id!r}"
                )
        discovered = _discover_captured_figures(package)
        validate_figure_coverage(discovered, figures)
        for figure in figures:
            validate_figure_closure(figure, keys)
    except (VerificationError, ManifestError, OSError) as error:
        findings.append(str(error))
        data_paths = {}

    try:
        derived_rows = _validate_derived_evidence_gate(
            package,
            project_root,
            source_inventory,
            data_rows,
            figures,
            expected_derived_recipes,
        )
        if package.exists("00_handoff/DERIVED_DATA_EVIDENCE.csv"):
            evidence.append("00_handoff/DERIVED_DATA_EVIDENCE.csv")
    except (VerificationError, OSError) as error:
        findings.append(str(error))

    for row in data_rows:
        try:
            relative = _relative(row["path"], context="DATA_MANIFEST.path")
            if not SHA256_RE.fullmatch(row["sha256"]):
                raise VerificationError(f"invalid data SHA256: {row['data_id']}")
            if package.sha256(relative) != row["sha256"]:
                raise VerificationError(f"data SHA256 mismatch: {row['data_id']}")
            parent = row["parent_source"]
            if parent != "N/A":
                parent_relative = _relative(parent, context="DATA_MANIFEST.parent_source")
                if not SHA256_RE.fullmatch(row["parent_sha256"]):
                    raise VerificationError(f"invalid parent SHA256: {row['data_id']}")
                source_row = source_by_path.get(parent_relative)
                if source_row is None or (
                    source_row.sha256
                    and source_row.sha256 != row["parent_sha256"]
                ):
                    raise VerificationError(f"parent source inventory mismatch: {row['data_id']}")
                if hashlib.sha256(
                    _read_project_anchored(project_root, parent_relative)
                ).hexdigest() != row["parent_sha256"]:
                    raise VerificationError(f"parent source SHA256 mismatch: {row['data_id']}")
        except VerificationError as error:
            findings.append(str(error))

    for row in document_rows:
        try:
            relative = _relative(row["path"], context="DOCUMENT_MANIFEST.path")
            if not SHA256_RE.fullmatch(row["sha256"]):
                raise VerificationError(
                    f"invalid document SHA256: {row['document_id']}"
                )
            package_sha = package.sha256(relative)
            if package_sha != row["sha256"]:
                raise VerificationError(
                    f"document SHA256 mismatch: {row['document_id']}"
                )
            source = row["source_path"]
            if source != "N/A":
                source_relative = _relative(
                    source, context="DOCUMENT_MANIFEST.source_path"
                )
                source_row = source_by_path.get(source_relative)
                if source_row is None or source_row.sha256 != package_sha:
                    raise VerificationError(
                        f"document source inventory mismatch: {row['document_id']}"
                    )
                if hashlib.sha256(
                    _read_project_anchored(project_root, source_relative)
                ).hexdigest() != package_sha:
                    raise VerificationError(
                        f"document source SHA256 mismatch: {row['document_id']}"
                    )
        except VerificationError as error:
            findings.append(str(error))

    data_sha_by_id = {row["data_id"]: row["sha256"] for row in data_rows}

    redraw_by_figure: dict[str, dict[str, str]] = {}
    redraw_ids: set[str] = set()
    build_tokens: set[str] = set()
    for row in redraw_rows:
        figure_id = row["figure_id"]
        redraw_id = row["redraw_id"]
        if redraw_id in redraw_ids:
            findings.append(f"duplicate redraw evidence ID: {redraw_id}")
        redraw_ids.add(redraw_id)
        if figure_id in redraw_by_figure:
            findings.append(f"duplicate redraw evidence for figure: {figure_id}")
        redraw_by_figure[figure_id] = row
        try:
            command = shlex.split(row["command"], posix=True)
            if not command or command[0] != row["environment_command"]:
                raise VerificationError(
                    f"redraw environment command mismatch: {redraw_id}"
                )
            environment = json.loads(row["environment"])
            if (
                not isinstance(environment, dict)
                or not environment
                or any(
                    not isinstance(key, str)
                    or not key
                    or not isinstance(value, str)
                    or not value
                    for key, value in environment.items()
                )
            ):
                raise VerificationError(f"redraw environment is empty: {redraw_id}")
            if row["result"] != "PASS" or row["exit_code"] != "0":
                raise VerificationError(f"redraw result must be PASS/0: {redraw_id}")
            for field_name in ("stdout_sha256", "stderr_sha256"):
                if not SHA256_RE.fullmatch(row[field_name]):
                    raise VerificationError(
                        f"invalid redraw {field_name}: {redraw_id}"
                    )
            for field_name in ("script_sha256", "output_sha256", "reference_sha256"):
                if row[field_name] != "N/A" and not SHA256_RE.fullmatch(row[field_name]):
                    raise VerificationError(
                        f"invalid redraw {field_name}: {redraw_id}"
                    )
            numeric_fields = (
                "started_at_ns", "started_monotonic_ns", "raw_output_mtime_ns",
                "filesystem_clock_offset_ns", "filesystem_clock_uncertainty_ns",
                "output_mtime_ns", "finished_at_ns", "finished_monotonic_ns",
                "evidence_written_at_ns",
            )
            numeric = {field: int(row[field]) for field in numeric_fields}
            if any(
                numeric[field] < 0
                for field in numeric_fields
                if field != "filesystem_clock_offset_ns"
            ):
                raise VerificationError(f"negative redraw timestamp: {redraw_id}")
            if not (
                0 < numeric["started_monotonic_ns"]
                <= numeric["finished_monotonic_ns"]
                and numeric["started_at_ns"] <= numeric["finished_at_ns"]
                <= numeric["evidence_written_at_ns"]
            ):
                raise VerificationError(f"inconsistent redraw timestamps: {redraw_id}")
            if row["output_sha256"] != "N/A" and (
                numeric["raw_output_mtime_ns"] <= 0
                or numeric["output_mtime_ns"]
                != numeric["raw_output_mtime_ns"]
                - numeric["filesystem_clock_offset_ns"]
            ):
                raise VerificationError(
                    f"inconsistent calibrated redraw output timestamp: {redraw_id}"
                )
            token = row["build_token"].strip()
            if not token:
                raise VerificationError(f"empty redraw build token: {redraw_id}")
            build_tokens.add(token)
        except (VerificationError, ValueError, json.JSONDecodeError) as error:
            findings.append(str(error))
    expected_redraw_figures = {
        figure.figure_id
        for figure in figures
        if figure.usage_status in {"formal", "current_only"}
    }
    actual_redraw_figures = set(redraw_by_figure)
    if expected_redraw_figures != actual_redraw_figures:
        findings.append(
            "redraw figure coverage mismatch: "
            f"missing={sorted(expected_redraw_figures - actual_redraw_figures)!r}, "
            f"extra={sorted(actual_redraw_figures - expected_redraw_figures)!r}"
        )
    if len(build_tokens) != 1:
        findings.append("redraw evidence must share one non-empty build token")
    representative_modules: set[str] = set()
    invalid_figure_paths: set[str] = set()
    for figure in figures:
        try:
            if package.sha256(figure.figure_path) != figure.figure_sha256:
                raise VerificationError(f"figure SHA256 mismatch: {figure.figure_id}")
            active_path = not figure.figure_path.startswith("90_archive/")
            if active_path and (
                figure.usage_status == "archive_only"
                or figure.scientific_status in {"superseded", "failed", "unverified"}
            ):
                raise VerificationError(
                    f"active figure status evades closure: {figure.figure_id}"
                )
            if (
                not active_path
                and figure.scientific_status == "valid"
                and figure.usage_status in {"formal", "current_only"}
            ):
                raise VerificationError(f"valid figure routed to archive: {figure.figure_id}")
            if figure.scientific_status in INVALID_FIGURE_STATUSES:
                invalid_figure_paths.add(figure.figure_path)
                if active_path:
                    raise VerificationError(
                        f"invalid figure is not archived: {figure.figure_id}"
                    )
                notes = figure.notes.strip()
                fields = {
                    key.strip().casefold(): value.strip()
                    for token in notes.split(";")
                    if "=" in token
                    for key, value in (token.split("=", 1),)
                }
                if not fields.get("source_locator"):
                    raise VerificationError(
                        f"invalid archive figure lacks source locator: {figure.figure_id}"
                    )
                lowered_notes = notes.casefold()
                has_warning = any(
                    token in lowered_notes for token in INVALID_WARNING_TOKENS
                ) or (
                    "must_route_to_" in lowered_notes
                    and "_archive" in lowered_notes
                )
                if not has_warning:
                    raise VerificationError(
                        f"invalid archive figure lacks explicit warning: {figure.figure_id}"
                    )
            if figure.plot_script_path != "N/A":
                package.sha256(figure.plot_script_path)
                command = shlex.split(figure.plot_command, posix=True)
                if figure.plot_script_path not in command:
                    raise VerificationError(
                        f"plot command does not execute declared script: {figure.figure_id}"
                    )
                for data_id in _ids(figure.input_data_ids):
                    path = data_paths.get(data_id)
                    if path is None or path not in command:
                        raise VerificationError(
                            f"plot command misses declared input {data_id}: {figure.figure_id}"
                        )
            if figure.usage_status in {"formal", "current_only"}:
                row = redraw_by_figure.get(figure.figure_id)
                if row is None:
                    raise VerificationError(f"missing redraw evidence: {figure.figure_id}")
                if row["result"].casefold() not in {"pass", "passed"} or row["exit_code"] != "0":
                    raise VerificationError(f"redraw did not pass: {figure.figure_id}")
                if row["module"] != figure.story_module:
                    raise VerificationError(f"redraw module mismatch: {figure.figure_id}")
                if row["input_data_ids"] != figure.input_data_ids:
                    raise VerificationError(f"redraw input IDs mismatch: {figure.figure_id}")
                validation_only = row["comparison_method"] == "input_hash_validation"
                if validation_only:
                    if (
                        active_path
                        and figure.scientific_status == "valid"
                        and figure.provenance_type in {"simulation", "theory"}
                    ):
                        raise VerificationError(
                            f"active numeric figure cannot use validation-only evidence: {figure.figure_id}"
                        )
                    if row["tolerance"] != "exact":
                        raise VerificationError(
                            f"validation-only tolerance must be exact: {figure.figure_id}"
                        )
                    command_tokens = shlex.split(row["command"], posix=True)
                    script_candidates = [
                        token
                        for token in command_tokens[1:]
                        if PurePosixPath(token).suffix.casefold() == ".py"
                        and package.exists(token)
                    ]
                    if len(script_candidates) != 1 or row["script_sha256"] != package.sha256(
                        script_candidates[0]
                    ):
                        raise VerificationError(
                            f"validation-only script SHA mismatch: {figure.figure_id}"
                        )
                else:
                    if (
                        row["comparison_method"] != figure.comparison_method
                        or row["tolerance"] != figure.tolerance
                        or not _validated_comparison(
                            row["comparison_method"], row["tolerance"]
                        )
                    ):
                        raise VerificationError(
                            f"invalid comparison evidence: {figure.figure_id}"
                        )
                    normalized_evidence_command = _normalize_packaged_command(
                        row["command"],
                        source_to_target={},
                        figure_id=figure.figure_id,
                    )
                    if normalized_evidence_command != figure.plot_command:
                        raise VerificationError(
                            f"redraw command mismatch: {figure.figure_id}"
                        )
                    if figure.plot_script_path != "N/A" and row[
                        "script_sha256"
                    ] != package.sha256(figure.plot_script_path):
                        raise VerificationError(
                            f"redraw script SHA mismatch: {figure.figure_id}"
                        )
                try:
                    input_hashes = json.loads(row["input_sha256"])
                except json.JSONDecodeError as error:
                    raise VerificationError(
                        f"invalid redraw input hash JSON: {figure.figure_id}"
                    ) from error
                expected_input_hashes = {
                    data_paths[data_id]: data_sha_by_id[data_id]
                    for data_id in _ids(figure.input_data_ids)
                }
                if row["comparison_method"] == "input_hash_validation":
                    expected_input_hashes[figure.figure_path] = figure.figure_sha256
                if input_hashes != expected_input_hashes:
                    raise VerificationError(f"redraw input SHA mismatch: {figure.figure_id}")
                if row["comparison_method"] == "input_hash_validation" and (
                    row["output_sha256"] != "N/A"
                    or row["reference_sha256"] != "N/A"
                    or row["raw_output_mtime_ns"] != "0"
                    or row["output_mtime_ns"] != "0"
                ):
                    raise VerificationError(
                        f"validation-only redraw declares output: {figure.figure_id}"
                    )
                if (
                    not validation_only
                    and figure.provenance_type in {"simulation", "theory"}
                ):
                    if not SHA256_RE.fullmatch(row["output_sha256"]):
                        raise VerificationError(f"missing/invalid redraw output SHA: {figure.figure_id}")
                    if not SHA256_RE.fullmatch(row["reference_sha256"]):
                        raise VerificationError(f"missing/invalid redraw reference SHA: {figure.figure_id}")
                    if row["comparison_method"] == "sha256_exact":
                        reference_id = _ids(
                            figure.comparison_reference_data_id, allow_na=False
                        )[0]
                        if row["reference_sha256"] != data_sha_by_id[reference_id]:
                            raise VerificationError(
                                f"reference data SHA mismatch: {figure.figure_id}"
                            )
                        if (
                            row["reference_sha256"] != figure.figure_sha256
                            or row["output_sha256"] != row["reference_sha256"]
                        ):
                            raise VerificationError(
                                f"image redraw/reference SHA mismatch: {figure.figure_id}"
                            )
                    elif row["comparison_method"] == "numpy.testing.assert_allclose":
                        reference_id = _ids(
                            figure.comparison_reference_data_id, allow_na=False
                        )[0]
                        if row["reference_sha256"] != data_sha_by_id[reference_id]:
                            raise VerificationError(
                                f"numeric redraw reference SHA mismatch: {figure.figure_id}"
                            )
                if (
                    not validation_only
                    and
                    row["output_sha256"] != "N/A"
                    and row["comparison_method"] != "numpy.testing.assert_allclose"
                    and row["output_sha256"] != figure.figure_sha256
                ):
                    raise VerificationError(
                        f"redraw output does not bind actual figure: {figure.figure_id}"
                    )
                if (
                    not validation_only
                    and
                    active_path
                    and figure.scientific_status == "valid"
                    and SHA256_RE.fullmatch(row["output_sha256"])
                ):
                    representative_modules.add(figure.story_module)
        except (VerificationError, ValueError) as error:
            findings.append(str(error))
    for relative in sorted(
        path
        for path in package.files
        if PurePosixPath(path).name == "README.md"
        or path == "00_handoff/START_HERE.md"
    ):
        try:
            if relative.startswith("90_archive/"):
                continue
            text = package.read_text(relative)
            parent = PurePosixPath(relative).parent
            for line_number, line in enumerate(text.splitlines(), start=1):
                for match in MARKDOWN_LABELED_LINK_RE.finditer(line):
                    label, raw_target = match.groups()
                    target = raw_target.split("#", 1)[0]
                    if (
                        not target
                        or target.startswith(("http://", "https://", "mailto:"))
                        or target.startswith("/")
                        or "\\" in target
                        or re.match(r"[A-Za-z]:", target)
                    ):
                        continue
                    normalized = posixpath.normpath((parent / target).as_posix())
                    if normalized not in invalid_figure_paths:
                        continue
                    prose = MARKDOWN_LABELED_LINK_RE.sub(
                        lambda linked: linked.group(1), line
                    )
                    context = f"{label} {prose}".casefold()
                    if not any(token in context for token in INVALID_WARNING_TOKENS):
                        findings.append(
                            "active README/navigation presents invalid archive figure without "
                            f"warning: {relative}:{line_number} -> {normalized}"
                        )
        except (OSError, UnicodeError, ValueError, VerificationError) as error:
            findings.append(f"cannot inspect active README invalid-figure links: {relative}: {error}")
    missing_modules = set(STORY_MODULES) - representative_modules
    if missing_modules:
        findings.append(f"missing representative redraw modules: {sorted(missing_modules)!r}")
    return _result(
        "G2", findings,
        {
            "figures": len(figures), "data_rows": len(data_rows),
            "derived_rows": derived_rows, "document_rows": len(document_rows),
            "redraw_rows": len(redraw_rows),
        },
        evidence,
    )


def _normalize_packaged_command(
    command: str,
    *,
    source_to_target: Mapping[str, str],
    figure_id: str,
) -> str:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError as error:
        raise VerificationError(
            f"canonical plot command is malformed: {figure_id}"
        ) from error
    if not tokens:
        raise VerificationError(f"canonical plot command is empty: {figure_id}")
    executable = PurePosixPath(tokens[0]).name
    if not re.fullmatch(r"python(?:3(?:\.\d+)?)?", executable.casefold()):
        raise VerificationError(
            f"canonical plot command uses an unapproved interpreter: {figure_id}"
        )
    normalized = ["python3"]
    for token in tokens[1:]:
        mapped = source_to_target.get(token)
        if mapped is not None:
            normalized.append(mapped)
            continue
        token_path = PurePosixPath(token)
        if token_path.is_absolute():
            raise VerificationError(
                f"canonical plot command has unmapped absolute path: {figure_id}"
            )
        normalized.append(token)
    return shlex.join(normalized)


def _normalized_packaged_figure(
    figure: FigureRecipe,
    *,
    figure_target: str,
    source_to_target: Mapping[str, str],
) -> FigureRecipe:
    if figure.plot_script_path == "N/A":
        if figure.plot_command != "N/A":
            raise VerificationError(
                f"canonical figure has command without script: {figure.figure_id}"
            )
        return replace(figure, figure_path=figure_target)
    script_target = source_to_target.get(figure.plot_script_path)
    if script_target is None:
        raise VerificationError(
            f"canonical plot script has no deterministic package target: {figure.figure_id}"
        )
    return replace(
        figure,
        figure_path=figure_target,
        plot_script_path=script_target,
        plot_command=_normalize_packaged_command(
            figure.plot_command,
            source_to_target=source_to_target,
            figure_id=figure.figure_id,
        ),
    )


def package_figure_recipes(
    canonical: Sequence[FigureRecipe],
    required_assets: RequiredAssetInventory,
    redraw_recipes: Sequence[RedrawRecipe],
    data_paths: Mapping[str, str],
) -> tuple[FigureRecipe, ...]:
    """Map only executable/path fields into deterministic package space."""

    source_to_target = {
        row.source_path: row.target_path
        for row in required_assets.rows
        if row.target_path is not None
        and row.disposition in {"copied_active", "copied_archive"}
    }
    redraw_by_figure = {row.figure_id: row for row in redraw_recipes}
    if len(redraw_by_figure) != len(tuple(redraw_recipes)):
        raise VerificationError("redraw recipes must have unique figure IDs")
    packaged: list[FigureRecipe] = []
    for figure in canonical:
        figure_target = source_to_target.get(figure.figure_path)
        if figure_target is None:
            raise VerificationError(
                f"canonical figure has no deterministic package target: {figure.figure_id}"
            )
        row = _normalized_packaged_figure(
            figure,
            figure_target=figure_target,
            source_to_target=source_to_target,
        )
        redraw = redraw_by_figure.get(figure.figure_id)
        if redraw is not None:
            if redraw.comparison_method != "input_hash_validation":
                normalized_redraw_command = _normalize_packaged_command(
                    redraw.command,
                    source_to_target=source_to_target,
                    figure_id=figure.figure_id,
                )
                if (
                    redraw.script_path != row.plot_script_path
                    or normalized_redraw_command != row.plot_command
                ):
                    raise VerificationError(
                        f"redraw recipe is not bound to packaged figure command: {figure.figure_id}"
                    )
        command_tokens = set(shlex.split(row.plot_command, posix=True)) if row.plot_command != "N/A" else set()
        for data_id in _ids(row.input_data_ids):
            data_path = data_paths.get(data_id)
            if data_path is None or data_path not in command_tokens:
                raise VerificationError(
                    f"packaged figure command misses data path: {figure.figure_id}:{data_id}"
                )
        packaged.append(row)
    return tuple(packaged)


def _gate_g3(
    package: _CapturedPackage,
    project_root: Path,
    contract: PortableContract,
    tree_specs: Sequence[TreeSourceSpec],
    exact_specs: Sequence[ExactSourceSpec],
    include_thesis_assets: bool,
    expected_figure_recipes: Sequence[FigureRecipe] | None,
    expected_redraw_recipes: Sequence[RedrawRecipe] | None,
    source_inventory: RequiredAssetInventory | None,
    source_error: str | None,
) -> VerificationResult:
    findings: list[str] = [] if source_error is None else [source_error]
    evidence = ["00_handoff/REQUIRED_ASSETS.csv"]
    rows: tuple[dict[str, str], ...] = ()
    expected = ()
    try:
        rows = _read_csv(package, "00_handoff/REQUIRED_ASSETS.csv", REQUIRED_COLUMNS)
        _unique(rows, "asset_id", context="REQUIRED_ASSETS")
        _unique(rows, "source_path", context="REQUIRED_ASSETS")
        if source_inventory is None:
            raise VerificationError("independent source inventory is unavailable")
        expected = tuple(source_inventory.rows)
        expected_by_source = {row.source_path: row for row in expected}
        actual_by_source = {row["source_path"]: row for row in rows}
        missing = sorted(set(expected_by_source) - set(actual_by_source))
        extra = sorted(set(actual_by_source) - set(expected_by_source))
        if missing or extra:
            raise VerificationError(
                f"required source set mismatch: missing={missing!r}, extra={extra!r}"
            )
        ledger_source = "95_shared_scripts/handoff_delivery/figure_recipes.csv"
        ledger_expected = expected_by_source.get(ledger_source)
        if ledger_expected is None:
            raise VerificationError(
                "canonical figure recipe ledger is absent from independent enumeration"
            )
        ledger_payload = _read_project_anchored(project_root, ledger_source)
        if hashlib.sha256(ledger_payload).hexdigest() != ledger_expected.sha256:
            raise VerificationError(
                "canonical figure recipe ledger differs from enumerated source SHA"
            )
        ledger_rows = _parse_csv_payload(
            ledger_payload, ledger_source, tuple(FigureRecipe.__dataclass_fields__)
        )
        try:
            bound_figure_rows = tuple(FigureRecipe(**row) for row in ledger_rows)
        except (TypeError, ValueError, ManifestError) as error:
            raise VerificationError("canonical figure recipe ledger is invalid") from error
        validated_figure_rows = tuple(validate_recipe_ledger(project_root))
        if validated_figure_rows != bound_figure_rows:
            raise VerificationError(
                "full canonical validation differs from anchored ledger bytes"
            )
        if (
            expected_figure_recipes is not None
            and tuple(expected_figure_recipes) != bound_figure_rows
        ):
            raise VerificationError(
                "canonical figure ledger differs from build-plan recipes"
            )
        canonical_figures = {
            figure.figure_path: figure for figure in bound_figure_rows
        }
        missing_figure_sources = sorted(
            set(canonical_figures) - set(expected_by_source)
        )
        if missing_figure_sources:
            raise VerificationError(
                "canonical figure sources missing from enumeration: "
                f"{missing_figure_sources!r}"
            )
        transforms_by_source = {
            transform.source_path: transform for transform in contract.transforms
        }
        if len(transforms_by_source) != len(contract.transforms):
            raise VerificationError("portable transform source paths must be unique")
        missing_transform_sources = sorted(
            set(transforms_by_source) - set(expected_by_source)
        )
        if missing_transform_sources:
            raise VerificationError(
                f"portable transform sources missing from enumeration: {missing_transform_sources!r}"
            )
        targets: set[str] = set()
        source_to_target: dict[str, str] = {}
        routed_inventory_rows = []
        for source, expected_row in expected_by_source.items():
            row = actual_by_source[source]
            if row["source_sha256"] != expected_row.sha256:
                raise VerificationError(f"required source SHA256 mismatch: {source}")
            status = row["status"]
            if status not in {"copied_active", "copied_archive", "excluded_with_reason"}:
                raise VerificationError(f"invalid required status: {source}")
            expected_status = expected_row.disposition
            expected_target: str | None = expected_row.target_path
            expected_reason = expected_row.reason
            source_path = PurePosixPath(source)
            is_figure = source in canonical_figures or source_path.suffix.casefold() in {".png", ".svg"} or (
                source_path.suffix.casefold() == ".pdf"
                and "figures" in source_path.parts
            )
            if is_figure:
                figure = canonical_figures.get(source)
                if figure is None:
                    expected_status = "excluded_with_reason"
                    expected_target = None
                    expected_reason = "unregistered-noncanonical-figure"
                else:
                    if expected_row.disposition == "excluded_with_reason":
                        raise VerificationError(
                            f"canonical figure base inventory excluded: {source}"
                        )
                    route = route_figure(figure)
                    if route == "active":
                        expected_status = "copied_active"
                    else:
                        expected_status = "copied_archive"
                        expected_target = (
                            f"{route}/{figure.figure_id}/{source_path.name}"
                        )
                        expected_reason = (
                            f"figure-{figure.scientific_status}-archive"
                        )
            transform = transforms_by_source.get(source)
            if transform is not None:
                if expected_status != "copied_active":
                    raise VerificationError(
                        f"portable transform source is not active after figure routing: {source}"
                    )
                expected_target = transform.original_path
                expected_reason = f"portable-original:{transform.transform_id}"
            if not row["module"].strip():
                raise VerificationError(f"required asset module is empty: {source}")
            if row["required_reason"] != expected_reason:
                raise VerificationError(
                    f"required reason mismatch: {source}: expected {expected_reason!r}"
                )
            if not row["notes"].strip() or (
                expected_status == "excluded_with_reason"
                and expected_reason not in row["notes"]
            ):
                raise VerificationError(
                    f"required notes do not preserve routing reason: {source}"
                )
            if status != expected_status:
                raise VerificationError(
                    f"required disposition mismatch: {source}: "
                    f"expected {expected_status}, found {status}"
                )
            target = row["target_path"]
            expected_class = {
                "copied_active": "active",
                "copied_archive": "archive",
                "excluded_with_reason": "excluded",
            }[expected_status]
            if row["expected_target_class"] != expected_class:
                raise VerificationError(
                    f"expected_target_class mismatch: {source}: "
                    f"expected {expected_class}, found {row['expected_target_class']}"
                )
            if status == "excluded_with_reason":
                if expected_target is not None or target != "N/A" or not row["notes"].strip():
                    raise VerificationError(f"excluded row lacks reason/N/A target: {source}")
                routed_inventory_rows.append(
                    replace(
                        expected_row,
                        target_path=None,
                        disposition="excluded_with_reason",
                        expected_target_class="excluded",
                        reason=expected_reason,
                    )
                )
                continue
            target = _relative(target, context="REQUIRED_ASSETS.target_path")
            if target != expected_target:
                raise VerificationError(
                    f"deterministic target mismatch: {source}: "
                    f"expected {expected_target!r}, found {target!r}"
                )
            if target in targets:
                raise VerificationError(f"duplicate required target path: {target}")
            targets.add(target)
            if status == "copied_active" and target.startswith("90_archive/"):
                raise VerificationError(f"active source routed to archive: {source}")
            if status == "copied_archive" and not target.startswith("90_archive/"):
                raise VerificationError(f"archive source routed active: {source}")
            if package.sha256(target) != row["source_sha256"]:
                raise VerificationError(f"copied target SHA256 mismatch: {source}")
            source_to_target[source] = target
            routed_inventory_rows.append(
                replace(
                    expected_row,
                    target_path=target,
                    disposition=expected_status,
                    expected_target_class=expected_class,
                    reason=expected_reason,
                )
            )
        data_rows = _read_csv(package, "00_handoff/DATA_MANIFEST.csv", DATA_COLUMNS)
        expected_packaged_figures = {
            figure.figure_id: figure
            for figure in package_figure_recipes(
                bound_figure_rows,
                RequiredAssetInventory(tuple(routed_inventory_rows)),
                () if expected_redraw_recipes is None else expected_redraw_recipes,
                {row["data_id"]: row["path"] for row in data_rows},
            )
        }
        packaged_figures = _load_captured_figures(
            package, "00_handoff/FIGURE_MANIFEST.csv"
        )
        packaged_by_id = {figure.figure_id: figure for figure in packaged_figures}
        if len(packaged_by_id) != len(packaged_figures):
            raise VerificationError("packaged canonical figure IDs are not unique")
        if packaged_by_id != expected_packaged_figures:
            raise VerificationError(
                "packaged canonical figure metadata differs from source ledger/routing"
            )
    except (VerificationError, SourceSpecError, ManifestError, OSError) as error:
        findings.append(str(error))
    return _result(
        "G3", findings,
        {"manifest_rows": len(rows), "independent_candidates": len(expected)},
        evidence,
    )


def _captured_absolute_path_findings(package: _CapturedPackage) -> tuple[Any, ...]:
    findings: list[Any] = []
    for relative in package.files:
        relative_path = PurePosixPath(relative)
        payload = package.read_bytes(relative)
        if (
            relative == "00_handoff/PORTABLE_WRAPPERS.csv"
            or (
                len(relative_path.parts) == 2
                and relative_path.parts[0] == "00_handoff"
                and relative_path.name.endswith("MANIFEST.csv")
            )
        ):
            findings.extend(_scan_manifest_csv_payload(payload, relative))
            continue
        if (
            relative_path.suffix.casefold() not in _G4_SUFFIXES
            or not _is_g4_executable_path(relative_path)
        ):
            continue
        if relative_path.suffix.casefold() in {".json", ".yaml", ".yml", ".toml"}:
            value = _load_structured_payload(payload, relative)
            findings.extend(scan_structured_values(value, context=relative))
        elif relative_path.suffix.casefold() == ".py":
            findings.extend(_scan_python_executable(payload, context=relative))
        else:
            findings.extend(scan_executable_text(payload, context=relative))
    return tuple(findings)


def _routed_inventory_from_required_rows(
    rows: Sequence[Mapping[str, str]],
    source_inventory: RequiredAssetInventory,
) -> RequiredAssetInventory:
    """Join verified source identities to the package routing declared in G3."""
    source_by_path = {row.source_path: row for row in source_inventory.rows}
    projected: list[RequiredAssetRow] = []
    for row in rows:
        source = source_by_path.get(row["source_path"])
        if source is None:
            raise VerificationError(
                f"initial-state routing names unknown source: {row['source_path']}"
            )
        status = row["status"]
        if status not in {
            "copied_active", "copied_archive", "excluded_with_reason"
        }:
            raise VerificationError(
                f"invalid initial-state routing status: {row['source_path']}"
            )
        target = None if row["target_path"] == "N/A" else _relative(
            row["target_path"], context="REQUIRED_ASSETS.target_path"
        )
        projected.append(
            RequiredAssetRow(
                source_path=source.source_path,
                target_path=target,
                disposition=status,
                expected_target_class=row["expected_target_class"],
                reason=row["required_reason"],
                sha256=source.sha256,
                size=source.size,
                file_type=source.file_type,
            )
        )
    return RequiredAssetInventory(tuple(projected))


def _gate_g4(
    package: _CapturedPackage,
    project_root: Path,
    contract: PortableContract,
    *,
    scan_root: Path,
    root_descriptor: int,
    source_inventory: RequiredAssetInventory | None,
    source_error: str | None,
) -> VerificationResult:
    findings: list[str] = [] if source_error is None else [source_error]
    source_by_path = {
        row.source_path: row for row in source_inventory.rows
    } if source_inventory is not None else {}
    evidence = [
        "00_handoff/RUN_MANIFEST.csv",
        "00_handoff/PORTABLE_TRANSFORMS.csv",
        "00_handoff/PORTABLE_WRAPPERS.csv",
        "00_handoff/INITIAL_STATE_RECIPES.csv",
        "00_handoff/FULL_FIELD_CONSUMERS.csv",
        "00_handoff/PORTABLE_CONFIG.toml",
    ]
    runs: tuple[dict[str, str], ...] = ()
    try:
        validate_portable_contract(contract, project_root=project_root)
        if source_inventory is None:
            raise VerificationError(
                "independent source inventory is unavailable for initial-state projection"
            )
        required = _read_csv(
            package, "00_handoff/REQUIRED_ASSETS.csv", REQUIRED_COLUMNS
        )
        routed_inventory = _routed_inventory_from_required_rows(
            required, source_inventory
        )
        package_initial_state = bind_initial_state_recipes_to_package(
            contract.recipes,
            required_assets=routed_inventory,
            transforms=contract.transforms,
        )
        expected_payloads = {
            "00_handoff/PORTABLE_TRANSFORMS.csv": portable_transforms_csv(contract),
            "00_handoff/PORTABLE_WRAPPERS.csv": portable_wrappers_csv(contract),
            "00_handoff/INITIAL_STATE_RECIPES.csv": (
                packaged_initial_state_recipes_csv(package_initial_state)
            ),
            "00_handoff/FULL_FIELD_CONSUMERS.csv": field_consumers_csv(contract),
            "00_handoff/PORTABLE_CONFIG.toml": contract.config_toml,
        }
        for relative, expected in expected_payloads.items():
            if package.read_bytes(relative) != expected:
                raise VerificationError(f"package portable contract mismatch: {relative}")
        _read_csv(package, "00_handoff/PORTABLE_TRANSFORMS.csv", PORTABLE_TRANSFORM_COLUMNS)
        _read_csv(package, "00_handoff/PORTABLE_WRAPPERS.csv", PORTABLE_WRAPPER_COLUMNS)
        _read_csv(package, "00_handoff/FULL_FIELD_CONSUMERS.csv", FIELD_CONSUMER_COLUMNS)
        runs = _read_csv(package, "00_handoff/RUN_MANIFEST.csv", RUN_COLUMNS)
        validate_packaged_initial_state_files(
            package_initial_state,
            package_sha256={
                row.relative_path: row.sha256
                for row in package.snapshot
                if row.path_type == "file"
            },
        )
        disposition_by_source = {
            row["source_path"]: row["status"]
            for row in required
            if row["status"] in {"copied_active", "copied_archive"}
        }
        discoverable_suffixes = {
            ".mx3", ".py", ".sh", ".ps1", ".m", ".json", ".yaml", ".yml",
            ".toml", ".template",
        }
        discovery_paths = tuple(
            source
            for source in disposition_by_source
            if PurePosixPath(source).suffix.casefold() in discoverable_suffixes
            or not PurePosixPath(source).suffix
        )
        discoveries_list = []
        for source in discovery_paths:
            payload = _read_project_anchored(project_root, source)
            source_row = source_by_path.get(source)
            payload_sha = hashlib.sha256(payload).hexdigest()
            if source_row is None or (
                source_row.sha256 and source_row.sha256 != payload_sha
            ):
                raise VerificationError(
                    f"field-consumer source differs from source inventory: {source}"
                )
            discovery = detect_field_consumer(source, payload)
            if discovery is not None:
                discoveries_list.append(discovery)
        discoveries = tuple(discoveries_list)
        validate_field_consumer_registry(
            discoveries,
            contract.consumers,
            disposition_by_source,
            publish=True,
            project_root=project_root,
        )
        _unique(runs, "run_id", context="RUN_MANIFEST")
        allowed_run_statuses = {"active", "archive", "reference_only"}
        invalid_run_statuses = sorted(
            {row["status"] for row in runs} - allowed_run_statuses
        )
        if invalid_run_statuses:
            raise VerificationError(
                f"invalid RUN_MANIFEST statuses: {invalid_run_statuses!r}"
            )
        for row in runs:
            if row["status"] != "active" and row["portable_entry"] != "N/A":
                raise VerificationError(
                    f"non-active run declares portable entry: {row['run_id']}"
                )
            if row["status"] == "active" and row["original_mx3"] == "N/A" and row["portable_entry"] != "N/A":
                raise VerificationError(
                    f"active non-simulation run declares portable entry: {row['run_id']}"
                )
        active_rows = {
            (row["run_id"], row["original_mx3"], row["portable_entry"])
            for row in runs
            if row["status"] == "active" and row["original_mx3"] != "N/A"
        }
        active_contract = {
            (row.run_id, row.original_path, row.portable_entry)
            for row in contract.runs if row.status == "active"
        }
        if not active_rows or active_rows != active_contract:
            raise VerificationError("RUN_MANIFEST active portable coverage mismatch")
        active_consumer_recipes: dict[str, set[str]] = {}
        for consumer in contract.consumers:
            if consumer.status != "active":
                continue
            active_consumer_recipes.setdefault(consumer.run_id, set()).add(
                consumer.initial_state_recipe_id
            )
        for row in runs:
            if row["status"] != "active" or row["original_mx3"] == "N/A":
                continue
            expected_recipes = active_consumer_recipes.get(row["run_id"], set())
            if expected_recipes != {row["initial_state_recipe_id"]}:
                raise VerificationError(
                    "active run recipe differs from active consumer contract: "
                    f"{row['run_id']}"
                )
        declared_portables = {row.portable_path for row in contract.transforms}
        declared_launchers = {row.launcher_path for row in contract.runtime_entries}
        for transform in contract.transforms:
            source_row = source_by_path.get(transform.source_path)
            if source_row is None or source_row.sha256 != transform.original_sha256:
                raise VerificationError(
                    f"transform source inventory mismatch: {transform.source_path}"
                )
            source_sha = hashlib.sha256(
                _read_project_anchored(project_root, transform.source_path)
            ).hexdigest()
            original = package.read_bytes(transform.original_path)
            portable = package.read_bytes(transform.portable_path)
            if source_sha != transform.original_sha256 or _sha(original) != transform.original_sha256:
                raise VerificationError(f"original script SHA256 mismatch: {transform.original_path}")
            if apply_portable_transform(original, transform) != portable:
                raise VerificationError(f"portable bytes differ from transform: {transform.portable_path}")
            if reverse_portable_transform(portable, transform) != original:
                raise VerificationError(f"portable reverse mismatch: {transform.portable_path}")
        for launcher in declared_launchers:
            package.sha256(launcher)
        runner_paths = {row.runner_path for row in contract.runtime_entries}
        if runner_paths != {"shared/runtime/portable_runner.py"}:
            raise VerificationError("portable runtime runner coverage mismatch")
        if package.read_bytes("shared/runtime/portable_runner.py") != portable_runner_script():
            raise VerificationError("portable runner bytes differ from Task5 runtime")
        for runtime in contract.runtime_entries:
            if package.read_bytes(runtime.launcher_path) != portable_launcher_script(runtime):
                raise VerificationError(
                    f"portable launcher bytes differ from Task5 runtime: {runtime.launcher_path}"
                )
        for relative in package.files:
            if "/simulation/portable/" in f"/{relative}" and relative not in (
                declared_portables | declared_launchers
            ):
                raise VerificationError(f"undeclared portable file: {relative}")
        findings_absolute = _captured_absolute_path_findings(package)
        if findings_absolute:
            labels = [f"{row.relative_path}:{row.line_number}:{row.matched}" for row in findings_absolute]
            raise VerificationError(f"machine-specific executable paths: {labels!r}")
    except (VerificationError, PortableError, OSError) as error:
        findings.append(str(error))
    return _result(
        "G4", findings,
        {"active_runs": sum(
             row.get("status") == "active" and row.get("original_mx3") != "N/A"
             for row in runs
         ),
         "transforms": len(contract.transforms), "consumers": len(contract.consumers)},
        evidence,
    )


def _readme_links(package: _CapturedPackage, relative: str, text: str) -> tuple[str, ...]:
    findings: list[str] = []
    parent = PurePosixPath(relative).parent
    for raw in MARKDOWN_LINK_RE.findall(text):
        target = raw.split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if target.startswith("/") or "\\" in target or re.match(r"[A-Za-z]:", target):
            findings.append(f"README absolute/non-POSIX link: {relative} -> {raw}")
            continue
        combined = parent / target
        normalized = posixpath.normpath(combined.as_posix())
        if normalized == ".." or normalized.startswith("../"):
            findings.append(f"README link escapes package: {relative} -> {raw}")
            continue
        if not package.exists(normalized):
            findings.append(f"README link target missing: {relative} -> {raw}")
    return tuple(findings)


def _active_deny_path(relative: str) -> bool:
    lowered = relative.casefold()
    basename = PurePosixPath(lowered).name
    return (
        any(token in lowered for token in ACTIVE_DENY_TOKENS)
        or "latex-hdu-bachelor-thesis" in PurePosixPath(lowered).parts
        or re.fullmatch(r"agents(?:[._-].*)?", basename) is not None
        or basename == "hdu-thesis.cls"
        or (
            ("毕业论文" in relative or "毕业设计" in relative)
            and "模板" in relative
        )
    )


def _gate_g5(package: _CapturedPackage) -> VerificationResult:
    findings: list[str] = []
    evidence = [
        "00_handoff/TOPIC_INDEX.csv",
        "00_handoff/REQUIRED_ASSETS.csv",
        "00_handoff/START_HERE.md",
    ]
    topics: tuple[dict[str, str], ...] = ()
    required: tuple[dict[str, str], ...] = ()
    try:
        root_entries = {
            PurePosixPath(row.relative_path).parts[0]
            for row in package.snapshot
            if row.relative_path
        }
        root_directories = {
            row.relative_path
            for row in package.snapshot
            if row.path_type == "directory" and "/" not in row.relative_path
        }
        if root_directories != FIXED_ROOT_DIRECTORIES:
            findings.append(
                f"fixed root directories changed: {sorted(root_directories)!r}"
            )
        if root_entries - FIXED_ROOT_DIRECTORIES - {"README.md"}:
            findings.append(f"unexpected root entries: {sorted(root_entries - FIXED_ROOT_DIRECTORIES - {'README.md'})!r}")
        topics = _read_csv(package, "00_handoff/TOPIC_INDEX.csv", TOPIC_COLUMNS)
        required = _read_csv(package, "00_handoff/REQUIRED_ASSETS.csv", REQUIRED_COLUMNS)
        _unique(topics, "topic_id", context="TOPIC_INDEX")
        _unique(topics, "path", context="TOPIC_INDEX")
    except (OSError, VerificationError) as error:
        findings.append(str(error))

    allowed_readmes = {"README.md", "shared/README.md"}
    allowed_readmes.update(f"{module}/README.md" for module in STORY_MODULES)
    for row in topics:
        try:
            path = _relative(row["path"], context="TOPIC_INDEX.path")
            readme = _relative(row["readme_path"], context="TOPIC_INDEX.readme_path")
            if row["module"] not in STORY_MODULES or not path.startswith(f"{row['module']}/"):
                raise VerificationError(f"topic outside declared module: {row['topic_id']}")
            if readme != f"{path}/README.md":
                raise VerificationError(f"topic README mismatch: {row['topic_id']}")
            allowed_readmes.add(readme)
        except VerificationError as error:
            findings.append(str(error))
    for directory in package.directories:
        parts = PurePosixPath(directory).parts
        if len(parts) == 2 and parts[0] == "90_archive":
            allowed_readmes.add(f"{directory}/README.md")
    required_navigation = allowed_readmes | {"00_handoff/START_HERE.md"}
    for relative in sorted(required_navigation):
        if relative not in package.rows or package.rows[relative].path_type != "file":
            findings.append(f"required navigation document missing: {relative}")
    evidence.extend(sorted(allowed_readmes))

    readme_count = 0
    for row in package.snapshot:
        relative = row.relative_path
        lowered = relative.casefold()
        if not relative.startswith("90_archive/") and any(
            token in lowered for token in ACTIVE_STATUS_TOKENS
        ):
            findings.append(f"non-active status content outside archive: {relative}")
        if relative.startswith((*tuple(f"{module}/" for module in STORY_MODULES), "shared/")):
            if _active_deny_path(relative):
                findings.append(f"active denylist path: {relative}")
        if PurePosixPath(relative).name.casefold() != "readme.md" or row.path_type != "file":
            continue
        readme_count += 1
        if relative not in allowed_readmes:
            findings.append(f"README outside allowlist: {relative}")
        try:
            text = package.read_text(relative)
        except (OSError, UnicodeError, VerificationError) as error:
            findings.append(f"cannot read README {relative}: {error}")
            continue
        if any(phrase.casefold() in text.casefold() for phrase in README_PLACEHOLDERS):
            findings.append(f"template/legacy README language: {relative}")
        if relative in {row.get("readme_path") for row in topics}:
            for section in ("研究问题", "当前状态", "有效/无效结论", "数据与代码入口", "复现级别"):
                if not re.search(rf"^#+\s*{re.escape(section)}\s*$", text, re.MULTILINE):
                    findings.append(f"topic README missing section {section}: {relative}")
        findings.extend(_readme_links(package, relative, text))
    try:
        start_here = package.read_text("00_handoff/START_HERE.md")
        if any(
            phrase.casefold() in start_here.casefold()
            for phrase in README_PLACEHOLDERS
        ):
            findings.append("template/legacy README language: 00_handoff/START_HERE.md")
        findings.extend(
            _readme_links(
                package, "00_handoff/START_HERE.md", start_here
            )
        )
    except VerificationError as error:
        findings.append(str(error))
    for row in required:
        if row.get("status") != "copied_active":
            continue
        lowered = row.get("source_path", "").casefold()
        if _active_deny_path(row.get("source_path", "")) or any(
            token in lowered for token in ACTIVE_STATUS_TOKENS
        ):
            findings.append(f"active source denylist violation: {row.get('source_path')}")
    return _result("G5", findings, {"readmes": readme_count, "topics": len(topics)}, evidence)


def verify(
    delivery_root: Path | str,
    *,
    project_root: Path | str,
    portable_contract: PortableContract,
    tree_specs: Sequence[TreeSourceSpec] = TREE_SOURCE_SPECS,
    exact_specs: Sequence[ExactSourceSpec] = EXACT_SOURCE_SPECS,
    include_thesis_assets: bool = True,
    root_descriptor: int | None = None,
    expected_snapshot: Sequence[_PinnedTreeEntry] | None = None,
    expected_figure_recipes: Sequence[FigureRecipe] | None = None,
    expected_redraw_recipes: Sequence[RedrawRecipe] | None = None,
    expected_derived_recipes: Sequence[DerivedRecipe] | None = None,
    expected_required_assets: RequiredAssetInventory | None = None,
    require_final_evidence: bool = True,
) -> tuple[VerificationResult, ...]:
    """Read a delivery once per gate and return immutable results without writes."""
    owned = root_descriptor is None
    descriptor = _open_root_descriptor(Path(delivery_root)) if owned else root_descriptor
    assert descriptor is not None
    package: _CapturedPackage | None = None
    try:
        root = _root_path(delivery_root, descriptor)
        project = Path(project_root)
        try:
            package = _capture_package(
                descriptor, expected_snapshot=expected_snapshot
            )
        except VerificationError as error:
            g1 = _result(
                "G1", [str(error)], {"regular_files_checked": 0}, ()
            )
            skipped = tuple(
                _result(
                    gate,
                    ["not run because G1 structural/content safety failed"],
                    {"checks_run": 0},
                    (),
                )
                for gate in ("G2", "G3", "G4", "G5")
            )
            return (g1, *skipped)
        g1 = _gate_g1(package)
        if not g1.passed:
            skipped = tuple(
                _result(
                    gate,
                    ["not run because G1 structural/content safety failed"],
                    {"checks_run": 0},
                    (),
                )
                for gate in ("G2", "G3", "G4", "G5")
            )
            return (g1, *skipped)
        source_inventory: RequiredAssetInventory | None = None
        source_error: str | None = None
        try:
            source_inventory = enumerate_required_assets(
                project,
                tree_specs=tree_specs,
                exact_specs=exact_specs,
                include_thesis_assets=include_thesis_assets,
            )
            if (
                expected_required_assets is not None
                and tuple(
                    (row.source_path, row.sha256, row.size, row.file_type)
                    for row in source_inventory.rows
                )
                != tuple(
                    (row.source_path, row.sha256, row.size, row.file_type)
                    for row in expected_required_assets.rows
                )
            ):
                raise VerificationError(
                    "fresh source inventory differs from build-plan inventory"
                )
        except (VerificationError, SourceSpecError, OSError) as error:
            source_error = f"independent source inventory failed: {error}"
        base_results = (
            g1,
            _gate_g2(
                package,
                project,
                source_inventory,
                source_error,
                expected_derived_recipes,
            ),
            _gate_g3(
                package,
                project,
                portable_contract,
                tree_specs,
                exact_specs,
                include_thesis_assets,
                expected_figure_recipes,
                expected_redraw_recipes,
                source_inventory,
                source_error,
            ),
            _gate_g4(
                package,
                project,
                portable_contract,
                scan_root=Path(delivery_root),
                root_descriptor=descriptor,
                source_inventory=source_inventory,
                source_error=source_error,
            ),
            _gate_g5(package),
        )
        return _validate_final_evidence(
            package, base_results, required=require_final_evidence
        )
    finally:
        if package is not None:
            package.close()
        if owned:
            os.close(descriptor)


def exit_code(results: Sequence[VerificationResult]) -> int:
    """Return zero exactly when all five unique gates pass."""
    rows = tuple(results)
    return 0 if tuple(row.gate for row in rows) == ("G1", "G2", "G3", "G4", "G5") and all(row.passed for row in rows) else 1


def _open_root_descriptor(root: Path) -> int:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_DIRECTORY", 0)
    if not getattr(os, "O_NOFOLLOW", 0) or not getattr(os, "O_DIRECTORY", 0):
        raise VerificationError("exclusive evidence writes require O_NOFOLLOW/O_DIRECTORY")
    absolute = Path(os.path.abspath(root))
    descriptor = -1
    try:
        descriptor = os.open(
            "/", flags | getattr(os, "O_CLOEXEC", 0)
        )
        for part in absolute.parts[1:]:
            next_descriptor = os.open(
                part,
                flags | getattr(os, "O_CLOEXEC", 0),
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise OSError("delivery root descriptor is not a directory")
        return descriptor
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        raise VerificationError(
            f"cannot anchor delivery root without symlink ancestors: {root}"
        ) from error


def _parent_descriptor(root_descriptor: int, relative: str) -> tuple[int, str]:
    parts = _relative(relative, context="evidence path").split("/")
    descriptor = os.dup(root_descriptor)
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(
                part,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0),
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor, parts[-1]
    except Exception:
        os.close(descriptor)
        raise


def _exclusive_write(root_descriptor: int, relative: str, payload: bytes, mode: int) -> None:
    parent, leaf = _parent_descriptor(root_descriptor, relative)
    descriptor = -1
    created = False
    try:
        descriptor = os.open(
            leaf,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            mode,
            dir_fd=parent,
        )
        created = True
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        if created:
            try:
                os.unlink(leaf, dir_fd=parent)
            except OSError:
                pass
        raise VerificationError(f"cannot exclusively write {relative}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent)


def write_report(
    delivery_root: Path | str,
    results: Sequence[VerificationResult],
    *,
    root_descriptor: int | None = None,
) -> Path:
    """Exclusively write the final deterministic report after all gates pass."""
    rows = tuple(results)
    if exit_code(rows) != 0:
        raise VerificationError("refusing to write a passing report for failed/incomplete gates")
    owned = root_descriptor is None
    descriptor = _open_root_descriptor(Path(delivery_root)) if owned else root_descriptor
    assert descriptor is not None
    payload = _report_payload(rows)
    try:
        _exclusive_write(descriptor, "00_handoff/verification_report.json", payload, 0o444)
    finally:
        if owned:
            os.close(descriptor)
    return Path(delivery_root) / "00_handoff/verification_report.json"


def _report_payload(results: Sequence[VerificationResult]) -> bytes:
    rows = tuple(results)
    return json.dumps(
        {
            "schema_version": 1,
            "passed": True,
            "readme_allowlist": sorted(
                path
                for row in rows
                if row.gate == "G5"
                for path in row.evidence_paths
                if path.endswith(".md")
            ),
            "gates": [asdict(row) for row in rows],
        },
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ).encode("utf-8") + b"\n"


def _validate_final_evidence(
    package: _CapturedPackage,
    base_results: Sequence[VerificationResult],
    *,
    required: bool,
) -> tuple[VerificationResult, ...]:
    """Validate the optional final report/checksum pair against pinned package bytes."""

    rows = tuple(base_results)
    report_path = "00_handoff/verification_report.json"
    checksum_path = "00_handoff/SHA256SUMS.txt"
    present = {path for path in FINAL_EVIDENCE_PATHS if package.exists(path)}
    if not present and not required:
        return rows
    findings: list[str] = []
    if not present:
        findings.append("final verification report and checksum are required")
    elif present != FINAL_EVIDENCE_PATHS:
        findings.append(
            "final verification evidence must contain both report and checksum"
        )
    else:
        if package.read_bytes(report_path) != _report_payload(rows):
            findings.append(
                "final verification report differs from deterministic G1-G5 results"
            )
        expected_checksums = _checksum_payload(package.snapshot)
        actual_checksums = package.read_bytes(checksum_path)
        if actual_checksums != expected_checksums:
            findings.append(
                "SHA256SUMS must uniquely and exactly cover every other regular file"
            )
    if not findings:
        return rows
    first = rows[0]
    failed_g1 = replace(
        first,
        passed=False,
        findings=tuple(sorted((*first.findings, *findings))),
        evidence_paths=tuple(
            sorted((*first.evidence_paths, *FINAL_EVIDENCE_PATHS))
        ),
    )
    return (failed_g1, *rows[1:])


def _checksum_payload(snapshot: Sequence[_PinnedTreeEntry]) -> bytes:
    return "".join(
        f"{row.sha256}  {row.relative_path}\n"
        for row in snapshot
        if row.path_type == "file"
        and row.relative_path != "00_handoff/SHA256SUMS.txt"
    ).encode("utf-8")


def write_checksums(
    delivery_root: Path | str,
    *,
    root_descriptor: int | None = None,
) -> Path:
    """Write SHA256SUMS last, covering every other regular file and not itself."""
    owned = root_descriptor is None
    descriptor = _open_root_descriptor(Path(delivery_root)) if owned else root_descriptor
    assert descriptor is not None
    try:
        snapshot = _snapshot_delivery_descriptor(descriptor)
        report = next(
            (row for row in snapshot if row.relative_path == "00_handoff/verification_report.json"),
            None,
        )
        if report is None or report.path_type != "file":
            raise VerificationError("verification report must exist before checksums")
        if any(row.relative_path == "00_handoff/SHA256SUMS.txt" for row in snapshot):
            raise VerificationError("checksum file already exists")
        _exclusive_write(
            descriptor,
            "00_handoff/SHA256SUMS.txt",
            _checksum_payload(snapshot),
            0o444,
        )
    except PortableError as error:
        raise VerificationError("cannot snapshot delivery for checksums") from error
    finally:
        if owned:
            os.close(descriptor)
    return Path(delivery_root) / "00_handoff/SHA256SUMS.txt"


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
