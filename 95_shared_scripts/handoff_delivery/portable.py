"""Fail-closed portable-entry contracts for the Hopfion handoff package.

The module deliberately treats simulation programs as opaque bytes.  A portable
entry may differ from its archival original only at explicitly registered
literal spans, and reversing those spans must recover the original SHA256.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
from string import Formatter
import tempfile
import tokenize
import tomllib
from typing import Any, Iterator, Literal

from .models import ManifestError, require_relative_path


class PortableError(ValueError):
    """Raised when a portability contract is ambiguous or cannot be verified."""


RunStatus = Literal["active", "archive", "reference_only"]
ConsumerStatus = Literal["active", "reference_only", "archive", "unresolved"]
RecipeVerificationStatus = Literal[
    "documented_only",
    "generator_smoke_tested",
    "existing_full_chain_evidence",
]

FIELD_CONSUMER_ROLES = (
    "direct_loader",
    "generator",
    "known_ovf_reader",
    "archive_member_reader",
    "shell_manager",
    "unresolved_touch",
)

PORTABLE_RUNNER_PATH = "shared/runtime/portable_runner.py"
RuntimeMode = Literal["direct_loader", "field_root_analysis", "thiele_archive"]
_RUNTIME_MODE_TOKENS: Mapping[str, tuple[str, ...]] = {
    "direct_loader": ("INIT_OVF",),
    "field_root_analysis": ("FIELD_ROOT", "OUTPUT_ROOT"),
    "thiele_archive": ("ARCHIVE_SOURCE", "OUTPUT_ROOT", "TAR_EXE"),
}
_RUNTIME_COMMAND_FIELDS = frozenset(
    {
        "delivery_root",
        "runtime_entry",
        "dependency",
        "workspace",
        "output_root",
        "archive_source",
        "tar_executable",
        "field_root",
    }
)


def _require_id(raw: str, *, label: str) -> str:
    if not isinstance(raw, str) or not raw or ";" in raw:
        raise PortableError(f"{label} must be one non-empty unambiguous ID")
    if any(character.isspace() for character in raw):
        raise PortableError(f"{label} must not contain whitespace")
    return raw


def _require_real_file_without_symlink_ancestors(path: Path, *, label: str) -> None:
    """Refuse both a symlink leaf and traversal through any symlinked parent."""
    for candidate in (path, *path.parents):
        try:
            metadata = candidate.lstat()
        except OSError as error:
            raise PortableError(f"cannot inspect {label}: {path}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise PortableError(f"{label} path traverses a symlink: {candidate}")
        if candidate == path:
            if not stat.S_ISREG(metadata.st_mode):
                raise PortableError(f"{label} must be one real file")
        elif not stat.S_ISDIR(metadata.st_mode):
            raise PortableError(f"{label} parent is not a real directory: {candidate}")


def _anchored_regular_descriptor(
    root: Path,
    relative: PurePosixPath,
    *,
    label: str,
) -> int:
    """Open one root-relative regular file without ever following a symlink."""
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not no_follow or not directory_flag:
        raise PortableError(f"{label} requires O_NOFOLLOW and O_DIRECTORY")
    absolute_root = root.absolute()
    if not absolute_root.is_absolute() or relative.is_absolute() or not relative.parts:
        raise PortableError(f"invalid anchored {label} path")
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise PortableError(f"invalid anchored {label} path")
    directory_descriptor = -1
    descriptor = -1
    try:
        directory_descriptor = os.open(
            "/",
            os.O_RDONLY | directory_flag | no_follow | getattr(os, "O_CLOEXEC", 0),
        )
        for part in absolute_root.parts[1:]:
            next_descriptor = os.open(
                part,
                os.O_RDONLY
                | directory_flag
                | no_follow
                | getattr(os, "O_CLOEXEC", 0),
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        for part in relative.parts[:-1]:
            next_descriptor = os.open(
                part,
                os.O_RDONLY
                | directory_flag
                | no_follow
                | getattr(os, "O_CLOEXEC", 0),
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        descriptor = os.open(
            relative.name,
            os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_descriptor,
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            os.close(descriptor)
            descriptor = -1
            raise PortableError(f"{label} must be one real file")
        return descriptor
    except PortableError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        raise PortableError(
            f"cannot open {label} without symlink traversal: {relative.as_posix()}"
        ) from error
    finally:
        if directory_descriptor >= 0:
            os.close(directory_descriptor)


def _read_anchored_regular(
    root: Path,
    relative: PurePosixPath,
    *,
    label: str,
) -> bytes:
    descriptor = _anchored_regular_descriptor(root, relative, label=label)
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as error:
        raise PortableError(f"cannot read anchored {label}") from error
    finally:
        os.close(descriptor)

    def identity(row: os.stat_result) -> tuple[int, int, int, int, int]:
        return (
            row.st_dev,
            row.st_ino,
            stat.S_IFMT(row.st_mode),
            row.st_size,
            row.st_mtime_ns,
        )

    if identity(before) != identity(after):
        raise PortableError(f"{label} changed while it was read")
    return b"".join(chunks)


def _read_path_anchored(
    path: Path,
    *,
    label: str,
    project_root: Path | None = None,
) -> bytes:
    absolute = path.absolute()
    if project_root is None:
        root = Path("/")
        relative = PurePosixPath(*absolute.parts[1:])
    else:
        root = project_root.absolute()
        try:
            relative = PurePosixPath(*absolute.relative_to(root).parts)
        except ValueError as error:
            raise PortableError(f"{label} must remain inside the project root") from error
    return _read_anchored_regular(root, relative, label=label)


def _require_delivery_path(raw: str, *, tree: str) -> str:
    try:
        path = require_relative_path(raw)
    except ManifestError as error:
        raise PortableError(f"invalid delivery-relative {tree} path: {raw!r}") from error
    if not path.parts or not re.fullmatch(r"0[1-5]_[^/]+", path.parts[0]):
        raise PortableError(f"{tree} path must be under a 01-05 delivery module")
    required = ("simulation", tree)
    pairs = tuple(zip(path.parts, path.parts[1:]))
    positions = tuple(index for index, pair in enumerate(pairs) if pair == required)
    if len(positions) != 1:
        raise PortableError(
            f"{tree} path must be below exactly one simulation/{tree}/: {raw!r}"
        )
    other_tree = "portable" if tree == "original" else "original"
    if ("simulation", other_tree) in pairs:
        raise PortableError(f"{tree} path must not traverse the opposite simulation tree")
    tree_index = positions[0]
    if tree_index + 2 >= len(path.parts):
        raise PortableError(f"{tree} path must identify a file below simulation/{tree}")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class LiteralReplacement:
    """One exact byte literal substitution and its required source count."""

    old: bytes
    new: bytes
    expected_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.old, bytes) or not self.old:
            raise PortableError("replacement old literal must be non-empty bytes")
        if not isinstance(self.new, bytes) or not self.new:
            raise PortableError("replacement new literal must be non-empty bytes")
        if self.old == self.new:
            raise PortableError("replacement old and new literals must differ")
        if not isinstance(self.expected_count, int) or isinstance(
            self.expected_count, bool
        ) or self.expected_count < 1:
            raise PortableError("replacement expected_count must be a positive integer")


@dataclass(frozen=True, slots=True)
class PortableTransform:
    """The complete, reversible byte-difference contract for one active run."""

    transform_id: str
    run_id: str
    source_path: str
    original_path: str
    original_sha256: str
    portable_path: str
    replacements: tuple[LiteralReplacement, ...]
    strategy: Literal["literal_transform", "identity", "wrapper_plus_transform"] = (
        "literal_transform"
    )
    wrapper_id: str = "N/A"

    def __post_init__(self) -> None:
        _require_id(self.transform_id, label="transform_id")
        _require_id(self.run_id, label="run_id")
        try:
            source = require_relative_path(self.source_path).as_posix()
        except ManifestError as error:
            raise PortableError(
                f"invalid transform source_path: {self.source_path!r}"
            ) from error
        object.__setattr__(self, "source_path", source)
        object.__setattr__(
            self,
            "original_path",
            _require_delivery_path(self.original_path, tree="original"),
        )
        object.__setattr__(
            self,
            "portable_path",
            _require_delivery_path(self.portable_path, tree="portable"),
        )
        if not re.fullmatch(r"[0-9a-f]{64}", self.original_sha256):
            raise PortableError("original_sha256 must be lowercase SHA256 hex")
        if not isinstance(self.replacements, tuple):
            raise PortableError("portable transform replacements must be a tuple")
        if not all(isinstance(row, LiteralReplacement) for row in self.replacements):
            raise PortableError("transform replacements must be LiteralReplacement rows")
        if self.strategy not in {
            "literal_transform",
            "identity",
            "wrapper_plus_transform",
        }:
            raise PortableError(f"invalid portable transform strategy: {self.strategy!r}")
        if self.strategy == "identity":
            if self.replacements:
                raise PortableError("identity transform must have empty replacements")
            if self.wrapper_id != "N/A":
                raise PortableError("identity transform must not declare a wrapper_id")
        elif not self.replacements:
            raise PortableError(
                f"{self.strategy} needs at least one registered replacement"
            )
        if self.strategy == "literal_transform" and self.wrapper_id != "N/A":
            raise PortableError("literal_transform must not declare a wrapper_id")
        if self.strategy == "wrapper_plus_transform":
            _require_id(self.wrapper_id, label="wrapper_id")


@dataclass(frozen=True, slots=True)
class RunEntry:
    """Minimal run row needed to prove exact active portable coverage."""

    run_id: str
    status: RunStatus
    original_path: str
    portable_entry: str

    def __post_init__(self) -> None:
        _require_id(self.run_id, label="run_id")
        if self.status not in {"active", "archive", "reference_only"}:
            raise PortableError(f"invalid run status: {self.status!r}")
        if self.status == "active":
            object.__setattr__(
                self,
                "original_path",
                _require_delivery_path(self.original_path, tree="original"),
            )
            object.__setattr__(
                self,
                "portable_entry",
                _require_delivery_path(self.portable_entry, tree="portable"),
            )
        else:
            if self.portable_entry != "N/A":
                raise PortableError(
                    "archive/reference_only rows must not declare a portable obligation"
                )
            if self.original_path != "N/A":
                object.__setattr__(
                    self,
                    "original_path",
                    _require_delivery_path(self.original_path, tree="original"),
                )


@dataclass(frozen=True, slots=True)
class FieldConsumerDiscovery:
    """Content-derived field-touch roles for exactly one source file."""

    source_path: str
    roles: tuple[str, ...]
    detection_evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            source = require_relative_path(self.source_path).as_posix()
        except ManifestError as error:
            raise PortableError(
                f"invalid field-consumer source path: {self.source_path!r}"
            ) from error
        object.__setattr__(self, "source_path", source)
        _require_canonical_roles(self.roles)
        _require_detection_evidence(self.detection_evidence)


@dataclass(frozen=True, slots=True)
class FieldConsumer:
    """Human classification for one independently discovered field touch."""

    source_path: str
    roles: tuple[str, ...]
    status: ConsumerStatus
    run_id: str
    initial_state_recipe_id: str
    non_full_field_data_id: str
    notes: str
    portable_handling: str
    detection_evidence: tuple[str, ...]
    status_evidence: str

    def __post_init__(self) -> None:
        try:
            source = require_relative_path(self.source_path).as_posix()
        except ManifestError as error:
            raise PortableError(
                f"invalid field-consumer source path: {self.source_path!r}"
            ) from error
        object.__setattr__(self, "source_path", source)
        _require_canonical_roles(self.roles)
        _require_detection_evidence(self.detection_evidence)
        if self.status not in {
            "active",
            "reference_only",
            "archive",
            "unresolved",
        }:
            raise PortableError(f"invalid field-consumer status: {self.status!r}")
        if not isinstance(self.notes, str) or not self.notes.strip():
            raise PortableError("field-consumer classification needs non-empty notes")
        if not isinstance(self.status_evidence, str) or not self.status_evidence.strip():
            raise PortableError("field-consumer status_evidence must be non-empty")
        if self.portable_handling not in {
            "literal_transform",
            "identity",
            "wrapper_plus_transform",
            "non_full_derived_data",
            "reference_only",
            "archive",
            "unresolved",
        }:
            raise PortableError(
                f"invalid field-consumer portable_handling: {self.portable_handling!r}"
            )
        for label, value in (
            ("run_id", self.run_id),
            ("initial_state_recipe_id", self.initial_state_recipe_id),
            ("non_full_field_data_id", self.non_full_field_data_id),
        ):
            if value != "N/A":
                _require_id(value, label=label)


@dataclass(frozen=True, slots=True)
class AbsolutePathFinding:
    """One forbidden machine-specific literal in an executable field."""

    relative_path: str
    line_number: int
    field_name: str
    matched: str


@dataclass(frozen=True, slots=True)
class InitialStateRecipe:
    """Evidence-labelled reconstruction chain; it never contains field bytes."""

    recipe_id: str
    logical_name: str
    original_ovf_reference: str
    generator_script: str
    generator_parameters: str
    relaxation_mx3: str
    expected_output: str
    consumers: tuple[str, ...]
    verification_status: RecipeVerificationStatus
    verification_evidence: str
    notes: str
    steps_json: str = "[]"

    def __post_init__(self) -> None:
        _require_id(self.recipe_id, label="recipe_id")
        if not isinstance(self.logical_name, str) or not self.logical_name.strip():
            raise PortableError("initial-state logical_name must be non-empty")
        if (
            not isinstance(self.original_ovf_reference, str)
            or not self.original_ovf_reference.strip()
        ):
            raise PortableError("original_ovf_reference must be non-empty provenance")
        if self.verification_status not in {
            "documented_only",
            "generator_smoke_tested",
            "existing_full_chain_evidence",
        }:
            raise PortableError(
                f"invalid initial-state verification_status: {self.verification_status!r}"
            )
        if not isinstance(self.verification_evidence, str) or not self.verification_evidence.strip():
            raise PortableError("verification_evidence must be non-empty")
        if not isinstance(self.notes, str) or not self.notes.strip():
            raise PortableError("initial-state recipe notes must be non-empty")
        for label, raw in (
            ("generator_script", self.generator_script),
            ("relaxation_mx3", self.relaxation_mx3),
        ):
            if raw != "N/A":
                try:
                    normalized = require_relative_path(raw).as_posix()
                except ManifestError as error:
                    raise PortableError(f"invalid {label}: {raw!r}") from error
                object.__setattr__(self, label, normalized)
        try:
            expected = require_relative_path(self.expected_output).as_posix()
        except ManifestError as error:
            raise PortableError(
                f"invalid expected_output: {self.expected_output!r}"
            ) from error
        object.__setattr__(self, "expected_output", expected)
        if not isinstance(self.consumers, tuple) or not self.consumers:
            raise PortableError("initial-state recipe consumers must be non-empty")
        normalized_consumers: list[str] = []
        for raw in self.consumers:
            try:
                normalized_consumers.append(require_relative_path(raw).as_posix())
            except ManifestError as error:
                raise PortableError(f"invalid recipe consumer path: {raw!r}") from error
        if len(normalized_consumers) != len(set(normalized_consumers)):
            raise PortableError("initial-state recipe consumers must be unique")
        object.__setattr__(self, "consumers", tuple(normalized_consumers))
        try:
            parameters = json.loads(self.generator_parameters)
        except (TypeError, json.JSONDecodeError) as error:
            raise PortableError("generator_parameters must be valid JSON") from error
        if not isinstance(parameters, Mapping):
            raise PortableError("generator_parameters must be one JSON object")
        try:
            steps = json.loads(self.steps_json)
        except (TypeError, json.JSONDecodeError) as error:
            raise PortableError("steps_json must be valid JSON") from error
        if not isinstance(steps, list) or not all(
            isinstance(step, str) and step.strip() for step in steps
        ):
            raise PortableError("steps_json must be a JSON list of non-empty strings")


@dataclass(frozen=True, slots=True)
class TemporaryDependencyContract:
    """A wrapper-owned set of field/archive paths that may exist only in temp."""

    wrapper_id: str
    run_id: str
    transform_id: str
    temporary_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_id(self.wrapper_id, label="wrapper_id")
        _require_id(self.run_id, label="run_id")
        _require_id(self.transform_id, label="transform_id")
        if not isinstance(self.temporary_paths, tuple) or not self.temporary_paths:
            raise PortableError("wrapper temporary_paths must be non-empty")
        normalized: list[str] = []
        for raw in self.temporary_paths:
            try:
                normalized.append(require_relative_path(raw).as_posix())
            except ManifestError as error:
                raise PortableError(f"unsafe wrapper temporary path: {raw!r}") from error
        if len(normalized) != len(set(normalized)):
            raise PortableError("wrapper temporary paths must be unique")
        object.__setattr__(self, "temporary_paths", tuple(normalized))


@dataclass(frozen=True, slots=True)
class PortableRuntimeEntry:
    """One executable runner row bound exactly to one portable transform."""

    runtime_id: str
    source_path: str
    run_id: str
    transform_id: str
    initial_state_recipe_id: str
    runner_path: str
    launcher_path: str
    mode: RuntimeMode
    template_path: str
    command_json: str
    runtime_tokens: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_id(self.runtime_id, label="runtime_id")
        _require_id(self.run_id, label="run_id")
        _require_id(self.transform_id, label="transform_id")
        _require_id(
            self.initial_state_recipe_id, label="initial_state_recipe_id"
        )
        try:
            source = require_relative_path(self.source_path).as_posix()
            runner = require_relative_path(self.runner_path).as_posix()
        except ManifestError as error:
            raise PortableError("runtime source/runner paths must be delivery-relative") from error
        object.__setattr__(self, "source_path", source)
        object.__setattr__(self, "runner_path", runner)
        if runner != PORTABLE_RUNNER_PATH:
            raise PortableError(
                f"runtime rows must use the unified runner: {PORTABLE_RUNNER_PATH}"
            )
        object.__setattr__(
            self,
            "launcher_path",
            _require_delivery_path(self.launcher_path, tree="portable"),
        )
        object.__setattr__(
            self,
            "template_path",
            _require_delivery_path(self.template_path, tree="portable"),
        )
        if self.launcher_path == self.template_path:
            raise PortableError(
                "runtime launcher_path must be distinct from its portable template"
            )
        if self.mode not in _RUNTIME_MODE_TOKENS:
            raise PortableError(f"invalid portable runtime mode: {self.mode!r}")
        if not isinstance(self.runtime_tokens, tuple):
            raise PortableError("runtime_tokens must be an immutable tuple")
        expected_tokens = _RUNTIME_MODE_TOKENS[self.mode]
        if self.runtime_tokens != expected_tokens:
            raise PortableError(
                f"{self.mode} runtime_tokens must exactly equal {expected_tokens!r}"
            )
        try:
            command = json.loads(self.command_json)
        except (TypeError, json.JSONDecodeError) as error:
            raise PortableError("runtime command_json must be valid JSON") from error
        if not isinstance(command, list) or not command or not all(
            isinstance(item, str) and item for item in command
        ):
            raise PortableError(
                "runtime command_json must be a non-empty JSON string list"
            )
        command_findings = tuple(
            finding
            for argument in command
            for finding in scan_executable_text(
                argument,
                context="PORTABLE_WRAPPERS.csv",
                field_name="command_json",
            )
        )
        if command_findings:
            raise PortableError(
                "runtime command_json contains machine-specific absolute paths: "
                f"{[row.matched for row in command_findings]!r}"
            )
        fields: set[str] = set()
        try:
            for argument in command:
                for _, field, _, _ in Formatter().parse(argument):
                    if field is not None:
                        fields.add(field)
        except ValueError as error:
            raise PortableError("runtime command_json has malformed placeholders") from error
        unknown = fields - _RUNTIME_COMMAND_FIELDS
        if unknown:
            raise PortableError(
                f"runtime command_json has unknown placeholders: {sorted(unknown)!r}"
            )
        if "runtime_entry" not in fields:
            raise PortableError("runtime command_json must execute {runtime_entry}")


@dataclass(frozen=True, slots=True)
class PortableContract:
    """Immutable package-wide portability input supplied explicitly to a build."""

    runs: tuple[RunEntry, ...]
    transforms: tuple[PortableTransform, ...]
    consumers: tuple[FieldConsumer, ...]
    recipes: tuple[InitialStateRecipe, ...]
    wrapper_contracts: tuple[TemporaryDependencyContract, ...]
    config_toml: bytes
    runtime_entries: tuple[PortableRuntimeEntry, ...] = ()

    def __post_init__(self) -> None:
        for label, rows, row_type in (
            ("runs", self.runs, RunEntry),
            ("transforms", self.transforms, PortableTransform),
            ("consumers", self.consumers, FieldConsumer),
            ("recipes", self.recipes, InitialStateRecipe),
            ("wrapper_contracts", self.wrapper_contracts, TemporaryDependencyContract),
            ("runtime_entries", self.runtime_entries, PortableRuntimeEntry),
        ):
            if not isinstance(rows, tuple) or not all(
                isinstance(row, row_type) for row in rows
            ):
                raise PortableError(f"portable contract {label} must be a typed tuple")
        if not isinstance(self.config_toml, bytes) or not self.config_toml:
            raise PortableError("portable config_toml must be non-empty bytes")


@dataclass(frozen=True, slots=True)
class _PinnedTreeEntry:
    """Stable content identity for one path below a pinned delivery root."""

    relative_path: str
    path_type: Literal["file", "directory"]
    mode: int
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class _PinnedDeliveryScan:
    """G4 findings and the exact tree bytes from the same pinned traversal."""

    findings: tuple[AbsolutePathFinding, ...]
    snapshot: tuple[_PinnedTreeEntry, ...]


@dataclass(frozen=True, slots=True)
class _PinnedPortableMaterialization:
    """Builder-only ownership transfer for the exact G4-scanned staging root."""

    written_paths: tuple[str, ...]
    staging_descriptor: int
    staging_identity: tuple[int, int, int, int, int]
    staging_snapshot: tuple[_PinnedTreeEntry, ...]


def _require_canonical_roles(roles: tuple[str, ...]) -> None:
    if not isinstance(roles, tuple) or not roles:
        raise PortableError("field-consumer roles must be a non-empty tuple")
    if len(roles) != len(set(roles)):
        raise PortableError("field-consumer roles must be unique")
    unknown = [role for role in roles if role not in FIELD_CONSUMER_ROLES]
    if unknown:
        raise PortableError(f"unknown field-consumer roles: {unknown!r}")
    expected = tuple(role for role in FIELD_CONSUMER_ROLES if role in roles)
    if roles != expected:
        raise PortableError(
            f"field-consumer roles must use canonical order: {expected!r}"
        )


def _require_detection_evidence(evidence: tuple[str, ...]) -> None:
    if not isinstance(evidence, tuple) or not evidence:
        raise PortableError("detection_evidence must be a non-empty tuple")
    if len(evidence) != len(set(evidence)):
        raise PortableError("detection_evidence entries must be unique")
    for item in evidence:
        if not isinstance(item, str) or not re.fullmatch(
            r"[a-z0-9_.-]+@L[1-9][0-9]*", item
        ):
            raise PortableError(
                f"detection_evidence must use deterministic rule@Lline form: {item!r}"
            )


def _strip_mx3_comments(text: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return "".join("\n" if char == "\n" else "\r" if char == "\r" else " " for char in match.group(0))

    without_blocks = re.sub(r"/\*.*?\*/", blank, text, flags=re.DOTALL)
    return re.sub(r"//[^\r\n]*", blank, without_blocks)


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _matching_lines(text: str, pattern: str, *, flags: int = 0) -> tuple[int, ...]:
    return tuple(
        sorted({_line_number(text, match.start()) for match in re.finditer(pattern, text, flags)})
    )


def _decode_python_source(payload: bytes, *, context: str) -> str:
    try:
        encoding, _lines = tokenize.detect_encoding(io.BytesIO(payload).readline)
        return payload.decode(encoding, errors="strict")
    except (LookupError, SyntaxError, UnicodeError) as error:
        raise PortableError(f"cannot parse Python source: {context}") from error


def _parse_python_source(text: str, *, context: str) -> ast.AST:
    try:
        return ast.parse(text, filename=context, mode="exec")
    except (SyntaxError, ValueError, TypeError) as error:
        raise PortableError(f"cannot parse Python source: {context}") from error


def _constant_python_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _constant_python_string(node.left)
        right = _constant_python_string(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                return None
            parts.append(value.value)
        return "".join(parts)
    return None


def _folded_python_strings(tree: ast.AST) -> tuple[tuple[str, int], ...]:
    parents = {
        id(child): parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    folded = {
        id(node): value
        for node in ast.walk(tree)
        if (value := _constant_python_string(node)) is not None
    }
    rows: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        value = folded.get(id(node))
        if value is None:
            continue
        parent = parents.get(id(node))
        if isinstance(parent, (ast.BinOp, ast.JoinedStr)):
            continue
        rows.append((value, getattr(node, "lineno", 1)))
    return tuple(rows)


def detect_field_consumer(
    source_path: str,
    payload: bytes,
) -> FieldConsumerDiscovery | None:
    """Classify field-touch mechanics from content, never scientific status."""
    try:
        source = require_relative_path(source_path).as_posix()
    except ManifestError as error:
        raise PortableError(f"invalid discovery source path: {source_path!r}") from error
    if not isinstance(payload, bytes):
        raise PortableError("field-consumer discovery accepts bytes only")
    suffix = PurePosixPath(source).suffix.casefold()
    text = (
        _decode_python_source(payload, context=source)
        if suffix == ".py"
        else payload.decode("utf-8-sig", errors="replace")
    )
    roles: set[str] = set()
    evidence: set[str] = set()
    folded_field_references: tuple[tuple[str, int], ...] = ()

    def add(role: str, rule: str, line: int) -> None:
        roles.add(role)
        evidence.add(f"{rule}@L{line}")

    if suffix == ".mx3":
        code = _strip_mx3_comments(text)
        for line in _matching_lines(code, r"\bm\s*\.\s*LoadFile\s*\("):
            add("direct_loader", "mx3.m_loadfile", line)
        touch_text = code
    elif suffix == ".py":
        tree = _parse_python_source(text, context=source)
        folded_strings = _folded_python_strings(tree)
        folded_field_references = tuple(
            (value, line)
            for value, line in folded_strings
            if re.search(
                r"(?:\.ovf\b|\.omf\b|\.tar\.zst\b|LoadFile\s*\()",
                value,
                re.IGNORECASE,
            )
        )
        try:
            token_rows = tuple(tokenize.generate_tokens(io.StringIO(text).readline))
        except (IndentationError, tokenize.TokenError) as error:
            raise PortableError(f"cannot parse Python source: {source}") from error
        usable = tuple(row for row in token_rows if row.type != tokenize.COMMENT)
        code_rows = tuple(row for row in usable if row.type != tokenize.STRING)
        for value, line in folded_strings:
            if re.search(r"\bm\s*\.\s*LoadFile\s*\(", value):
                add("generator", "python.template_m_loadfile", line)
        for row in code_rows:
            if row.type == tokenize.NAME and (
                row.string == "from_file"
                or re.fullmatch(
                    r"(?:read|load|parse)_?ovf", row.string, flags=re.IGNORECASE
                )
            ):
                add("known_ovf_reader", "python.known_ovf_reader", row.start[0])
        commentless = " ".join(row.string for row in usable)
        lower_commentless = (
            commentless + " " + " ".join(value for value, _line in folded_strings)
        ).casefold()
        if (
            ".tar.zst" in lower_commentless
            and ".ovf" in lower_commentless
            and any(
                token in lower_commentless
                for token in ("tarfile", "zstandard", "unzstd", "zstd")
            )
        ):
            archive_line = next(
                (
                    row.start[0]
                    for row in usable
                    if ".tar.zst" in row.string.casefold()
                ),
                next(
                    (
                        line
                        for value, line in folded_strings
                        if ".tar.zst" in value.casefold()
                    ),
                    1,
                ),
            )
            add(
                "archive_member_reader",
                "python.archive_member_chain",
                archive_line,
            )
        touch_text = commentless
    elif suffix in {".sh", ".ps1"} or (not suffix and text.startswith("#!")):
        lines = tuple(text.splitlines())
        uncommented_lines = tuple(
            "" if line.lstrip().startswith("#") and not line.startswith("#!") else line
            for line in lines
        )
        uncommented = "\n".join(uncommented_lines)
        lower = uncommented.casefold()
        if (
            "mumax3" in lower
            or (
                any(token in lower for token in ("tar ", "tar.exe", "unzstd", "zstd"))
                and (".ovf" in lower or ".tar.zst" in lower)
            )
        ):
            line = next(
                (
                    index
                    for index, value in enumerate(uncommented_lines, start=1)
                    if "mumax3" in value.casefold()
                    or any(
                        token in value.casefold()
                        for token in ("tar ", "tar.exe", "unzstd", "zstd")
                    )
                ),
                1,
            )
            add("shell_manager", "shell.field_manager", line)
        touch_text = uncommented
    elif suffix == ".m":
        uncommented = "\n".join(
            line.split("%", 1)[0] for line in text.splitlines()
        )
        if ".ovf" in uncommented.casefold() and re.search(
            r"\b(?:fopen|read|load).*", uncommented, flags=re.IGNORECASE
        ):
            line = next(
                (
                    index
                    for index, value in enumerate(uncommented.splitlines(), start=1)
                    if ".ovf" in value.casefold()
                    or re.search(r"\b(?:fopen|read|load)", value, re.IGNORECASE)
                ),
                1,
            )
            add("known_ovf_reader", "matlab.known_ovf_reader", line)
        touch_text = uncommented
    else:
        touch_text = text

    if not roles:
        dynamic = re.search(
            r"(?:\.ovf\b|\.omf\b|\.tar\.zst\b|LoadFile\s*\()",
            touch_text,
            re.IGNORECASE,
        )
        if dynamic is not None:
            add(
                "unresolved_touch",
                (
                    "structured.dynamic_field_reference"
                    if suffix in {".json", ".yaml", ".yml", ".toml"}
                    else "code.dynamic_field_reference"
                ),
                _line_number(touch_text, dynamic.start()),
            )
    if not roles and folded_field_references:
        for _value, line in folded_field_references:
            add(
                "unresolved_touch",
                "python.constant_field_reference",
                line,
            )
    if not roles:
        return None
    ordered = tuple(role for role in FIELD_CONSUMER_ROLES if role in roles)
    ordered_evidence = tuple(
        sorted(
            evidence,
            key=lambda item: (int(item.rsplit("@L", 1)[1]), item.rsplit("@L", 1)[0]),
        )
    )
    return FieldConsumerDiscovery(source, ordered, ordered_evidence)


def discover_full_field_consumers(
    project_root: Path,
    source_paths: Sequence[str],
) -> tuple[FieldConsumerDiscovery, ...]:
    """Read a fixed source set deterministically and return every content hit."""
    rows: list[FieldConsumerDiscovery] = []
    normalized: list[str] = []
    for raw in source_paths:
        try:
            normalized.append(require_relative_path(raw).as_posix())
        except ManifestError as error:
            raise PortableError(f"invalid discovery source path: {raw!r}") from error
    if len(normalized) != len(set(normalized)):
        raise PortableError("field-consumer discovery source paths must be unique")
    for source in sorted(normalized):
        try:
            payload = _read_anchored_regular(
                project_root,
                PurePosixPath(source),
                label="field-consumer candidate",
            )
        except PortableError as error:
            raise PortableError(f"cannot read field-consumer candidate: {source}") from error
        discovered = detect_field_consumer(source, payload)
        if discovered is not None:
            rows.append(discovered)
    return tuple(rows)


def validate_field_consumer_registry(
    discoveries: Sequence[FieldConsumerDiscovery],
    registry: Sequence[FieldConsumer],
    dispositions: Mapping[str, str],
    *,
    publish: bool,
    project_root: Path | None = None,
) -> None:
    """Bind independent content discovery to explicit, routed classifications."""
    discovery_paths = tuple(row.source_path for row in discoveries)
    registry_paths = tuple(row.source_path for row in registry)
    if len(discovery_paths) != len(set(discovery_paths)):
        raise PortableError("field-consumer discoveries contain duplicate paths")
    if len(registry_paths) != len(set(registry_paths)):
        raise PortableError("field-consumer registry contains duplicate paths")
    if set(discovery_paths) != set(registry_paths):
        raise PortableError(
            "field-consumer discovery set does not equal registry paths: "
            f"missing={sorted(set(discovery_paths) - set(registry_paths))!r}, "
            f"extra={sorted(set(registry_paths) - set(discovery_paths))!r}"
        )
    discovered_by_path = {row.source_path: row for row in discoveries}
    for row in registry:
        discovered = discovered_by_path[row.source_path]
        if row.roles != discovered.roles:
            raise PortableError(
                f"field-consumer roles differ from content discovery: {row.source_path}"
            )
        if row.detection_evidence != discovered.detection_evidence:
            raise PortableError(
                "field-consumer detection_evidence differs from content discovery: "
                f"{row.source_path}"
            )
        disposition = dispositions.get(row.source_path)
        if row.status in {"active", "reference_only"}:
            expected = "copied_active"
        elif row.status == "archive":
            expected = "copied_archive"
        else:
            expected = disposition
        if disposition != expected:
            raise PortableError(
                f"{row.source_path}: status {row.status!r} requires {expected}, "
                f"found {disposition!r}"
            )
        if "unresolved_touch" in row.roles and row.status != "unresolved":
            raise PortableError(
                f"{row.source_path}: unresolved_touch cannot receive a guessed status"
            )
        expected_handling = {
            "reference_only": "reference_only",
            "archive": "archive",
            "unresolved": "unresolved",
        }.get(row.status)
        if expected_handling is not None and row.portable_handling != expected_handling:
            raise PortableError(
                f"{row.source_path}: status/portable_handling mismatch"
            )
        if row.status == "active" and row.portable_handling not in {
            "literal_transform",
            "identity",
            "wrapper_plus_transform",
            "non_full_derived_data",
        }:
            raise PortableError(
                f"{row.source_path}: active status needs executable portable handling"
            )
        if row.status == "unresolved":
            if row.status_evidence != "N/A":
                raise PortableError(
                    f"{row.source_path}: unresolved status_evidence must be N/A"
                )
        else:
            generic = row.status_evidence.casefold().replace("_", "-")
            if any(
                phrase in generic
                for phrase in (
                    "copied-active",
                    "authoritative-active-source",
                    "directory-name",
                    "dirname",
                    "path-classification",
                )
            ):
                raise PortableError(
                    f"{row.source_path}: generic status_evidence is forbidden"
                )
            locator = re.fullmatch(r"(.+):L([1-9][0-9]*)", row.status_evidence)
            if locator is None:
                raise PortableError(
                    f"{row.source_path}: status_evidence must be a file:Lline locator"
                )
            try:
                evidence_path = require_relative_path(locator.group(1)).as_posix()
            except ManifestError as error:
                raise PortableError(
                    f"{row.source_path}: invalid status_evidence path"
                ) from error
            if project_root is not None:
                try:
                    lines = _read_anchored_regular(
                        project_root,
                        PurePosixPath(evidence_path),
                        label="status_evidence",
                    ).decode("utf-8-sig", errors="strict").splitlines()
                except (PortableError, UnicodeError) as error:
                    raise PortableError(
                        f"{row.source_path}: cannot read status_evidence"
                    ) from error
                if int(locator.group(2)) > len(lines):
                    raise PortableError(
                        f"{row.source_path}: status_evidence line is out of range"
                    )
    if publish:
        unresolved = sorted(row.source_path for row in registry if row.status == "unresolved")
        if unresolved:
            raise PortableError(
                f"publish mode forbids unresolved field consumers: {unresolved!r}"
            )


INITIAL_STATE_RECIPE_COLUMNS = (
    "recipe_id",
    "logical_name",
    "original_ovf_reference",
    "generator_script",
    "generator_parameters",
    "relaxation_mx3",
    "expected_output",
    "consumers",
    "verification_status",
    "verification_evidence",
    "notes",
    "steps_json",
)


def load_initial_state_recipes(
    path: Path,
    *,
    project_root: Path | None = None,
) -> tuple[InitialStateRecipe, ...]:
    """Load a versioned recipe ledger without inferring or upgrading status."""
    try:
        payload = _read_path_anchored(
            path,
            label="initial-state recipe ledger",
            project_root=project_root,
        ).decode("utf-8-sig", errors="strict")
        with io.StringIO(payload, newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != INITIAL_STATE_RECIPE_COLUMNS:
                raise PortableError(
                    "initial-state recipe header must exactly match the versioned schema"
                )
            raw_rows = tuple(reader)
    except (UnicodeError, csv.Error) as error:
        raise PortableError(f"cannot parse initial-state recipe ledger: {path}") from error
    rows: list[InitialStateRecipe] = []
    for number, raw in enumerate(raw_rows, start=2):
        if None in raw or any(value is None for value in raw.values()):
            raise PortableError(f"initial-state recipe row {number} has extra/missing cells")
        try:
            rows.append(
                InitialStateRecipe(
                    recipe_id=raw["recipe_id"],
                    logical_name=raw["logical_name"],
                    original_ovf_reference=raw["original_ovf_reference"],
                    generator_script=raw["generator_script"],
                    generator_parameters=raw["generator_parameters"],
                    relaxation_mx3=raw["relaxation_mx3"],
                    expected_output=raw["expected_output"],
                    consumers=tuple(raw["consumers"].split(";")),
                    verification_status=raw["verification_status"],  # type: ignore[arg-type]
                    verification_evidence=raw["verification_evidence"],
                    notes=raw["notes"],
                    steps_json=raw["steps_json"],
                )
            )
        except PortableError as error:
            raise PortableError(f"initial-state recipe row {number}: {error}") from error
    identifiers = tuple(row.recipe_id for row in rows)
    if len(identifiers) != len(set(identifiers)):
        raise PortableError("initial-state recipe IDs must be unique")
    return tuple(rows)


def _require_project_evidence_file(
    project_root: Path,
    relative: str,
    *,
    label: str,
) -> None:
    try:
        descriptor = _anchored_regular_descriptor(
            project_root,
            PurePosixPath(relative),
            label=label,
        )
    except PortableError as error:
        raise PortableError(f"stale {label}: {relative}") from error
    os.close(descriptor)


def validate_initial_state_recipes(
    recipes: Sequence[InitialStateRecipe],
    *,
    project_root: Path,
) -> None:
    """Validate declared paths/evidence without running a physical simulation."""
    identifiers = tuple(row.recipe_id for row in recipes)
    if len(identifiers) != len(set(identifiers)):
        raise PortableError("initial-state recipe IDs must be unique")
    try:
        root_metadata = project_root.lstat()
    except OSError as error:
        raise PortableError(f"cannot inspect recipe project root: {project_root}") from error
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        raise PortableError("recipe project root must be one real directory")

    documented_claims = re.compile(
        r"(?:full[ _-]?chain|end[ _-]?to[ _-]?end|fully).{0,24}"
        r"(?:rerun|reproduced|verified|validated)|"
        r"(?:rerun|reproduced|verified|validated).{0,24}"
        r"(?:full[ _-]?chain|end[ _-]?to[ _-]?end)",
        flags=re.IGNORECASE,
    )
    relaxation_claims = re.compile(
        r"relax(?:ation|ed)?.{0,24}(?:rerun|verified|validated|passed)",
        flags=re.IGNORECASE,
    )
    for row in recipes:
        if row.generator_script != "N/A":
            _require_project_evidence_file(
                project_root, row.generator_script, label="generator_script"
            )
        if row.relaxation_mx3 != "N/A":
            _require_project_evidence_file(
                project_root, row.relaxation_mx3, label="relaxation_mx3"
            )
        evidence_paths = tuple(row.verification_evidence.split(";"))
        if not evidence_paths or any(not item for item in evidence_paths):
            raise PortableError("verification_evidence must name non-empty paths")
        for evidence in evidence_paths:
            try:
                normalized = require_relative_path(evidence).as_posix()
            except ManifestError as error:
                raise PortableError(
                    f"verification_evidence must be source-relative: {evidence!r}"
                ) from error
            _require_project_evidence_file(
                project_root, normalized, label="verification_evidence"
            )
        claim_text = f"{row.verification_evidence}\n{row.notes}"
        if row.verification_status == "documented_only" and documented_claims.search(
            claim_text
        ):
            raise PortableError(
                f"{row.recipe_id}: documented_only may not claim a rerun full chain"
            )
        if row.verification_status == "generator_smoke_tested" and (
            documented_claims.search(claim_text) or relaxation_claims.search(claim_text)
        ):
            raise PortableError(
                f"{row.recipe_id}: generator_smoke_tested may not claim relaxation/full-chain evidence"
            )


def validate_initial_state_coverage(
    consumers: Sequence[FieldConsumer],
    recipes: Sequence[InitialStateRecipe],
) -> None:
    """Require an exact two-way active-consumer to recipe/data dependency map."""
    active = tuple(row for row in consumers if row.status == "active")
    expected_edges: set[tuple[str, str]] = set()
    for row in active:
        if row.run_id == "N/A":
            raise PortableError(f"active consumer has no run_id: {row.source_path}")
        has_recipe = row.initial_state_recipe_id != "N/A"
        has_data = row.non_full_field_data_id != "N/A"
        if not has_recipe and not has_data:
            raise PortableError(
                f"active consumer lacks a recipe or non-full derived data: {row.source_path}"
            )
        if has_recipe and has_data:
            raise PortableError(
                f"active consumer must select exactly one recipe/data dependency: {row.source_path}"
            )
        if has_recipe:
            expected_edges.add((row.initial_state_recipe_id, row.source_path))

    declared_edges = {
        (recipe.recipe_id, consumer)
        for recipe in recipes
        for consumer in recipe.consumers
    }
    if expected_edges != declared_edges:
        raise PortableError(
            "initial-state consumer edges are not bidirectionally exact: "
            f"missing={sorted(expected_edges - declared_edges)!r}, "
            f"extra={sorted(declared_edges - expected_edges)!r}"
        )


PORTABLE_TRANSFORM_COLUMNS = (
    "transform_id",
    "run_id",
    "source_path",
    "original_path",
    "original_sha256",
    "portable_path",
    "strategy",
    "wrapper_id",
    "replacements_json",
)

PORTABLE_WRAPPER_COLUMNS = (
    "runtime_id",
    "source_path",
    "run_id",
    "transform_id",
    "initial_state_recipe_id",
    "runner_path",
    "launcher_path",
    "mode",
    "template_path",
    "command_json",
    "runtime_tokens",
)

FIELD_CONSUMER_COLUMNS = (
    "source_path",
    "roles",
    "detection_evidence",
    "status",
    "status_evidence",
    "run_id",
    "initial_state_recipe_id",
    "non_full_field_data_id",
    "portable_handling",
    "notes",
)


def load_field_consumer_registry(
    path: Path,
    *,
    project_root: Path | None = None,
) -> tuple[FieldConsumer, ...]:
    """Load the strict, versioned content-discovery classification ledger."""
    try:
        payload = _read_path_anchored(
            path,
            label="field-consumer registry",
            project_root=project_root,
        ).decode("utf-8-sig", errors="strict")
        with io.StringIO(payload, newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != FIELD_CONSUMER_COLUMNS:
                raise PortableError(
                    "field-consumer registry header must exactly match the versioned schema"
                )
            raw_rows = tuple(reader)
    except (UnicodeError, csv.Error) as error:
        raise PortableError(f"cannot parse field-consumer registry: {path}") from error
    rows: list[FieldConsumer] = []
    for number, raw in enumerate(raw_rows, start=2):
        if None in raw or any(value is None for value in raw.values()):
            raise PortableError(f"field-consumer row {number} has extra/missing cells")
        try:
            rows.append(
                FieldConsumer(
                    source_path=raw["source_path"],
                    roles=tuple(raw["roles"].split(";")),
                    detection_evidence=tuple(raw["detection_evidence"].split(";")),
                    status=raw["status"],  # type: ignore[arg-type]
                    status_evidence=raw["status_evidence"],
                    run_id=raw["run_id"],
                    initial_state_recipe_id=raw["initial_state_recipe_id"],
                    non_full_field_data_id=raw["non_full_field_data_id"],
                    portable_handling=raw["portable_handling"],
                    notes=raw["notes"],
                )
            )
        except PortableError as error:
            raise PortableError(f"field-consumer row {number}: {error}") from error
    paths = tuple(row.source_path for row in rows)
    if len(paths) != len(set(paths)):
        raise PortableError("field-consumer registry source paths must be unique")
    return tuple(rows)

PORTABLE_OUTPUT_PATHS = (
    "00_handoff/PORTABLE_TRANSFORMS.csv",
    "00_handoff/PORTABLE_WRAPPERS.csv",
    "00_handoff/INITIAL_STATE_RECIPES.csv",
    "00_handoff/FULL_FIELD_CONSUMERS.csv",
    "00_handoff/PORTABLE_CONFIG.toml",
    PORTABLE_RUNNER_PATH,
)


def validate_portable_contract(
    contract: PortableContract,
    *,
    project_root: Path,
) -> None:
    """Validate all package-level relations without materializing any output."""
    validate_portable_coverage(contract.runs, contract.transforms)
    validate_initial_state_recipes(contract.recipes, project_root=project_root)

    transform_bindings = {
        (row.source_path, row.run_id, row.strategy) for row in contract.transforms
    }
    if len(transform_bindings) != len(contract.transforms):
        raise PortableError("portable transform source/run/handling bindings must be unique")
    consumer_bindings = {
        (row.source_path, row.run_id, row.portable_handling)
        for row in contract.consumers
        if row.status == "active"
        and row.portable_handling
        in {"literal_transform", "identity", "wrapper_plus_transform"}
    }
    if transform_bindings != consumer_bindings:
        raise PortableError(
            "portable transform source/run/handling coverage mismatch: "
            f"missing={sorted(transform_bindings - consumer_bindings)!r}, "
            f"extra={sorted(consumer_bindings - transform_bindings)!r}"
        )
    validate_initial_state_coverage(contract.consumers, contract.recipes)

    active_run_ids = {row.run_id for row in contract.runs if row.status == "active"}
    consumer_run_ids = {
        row.run_id for row in contract.consumers if row.status == "active"
    }
    if active_run_ids != consumer_run_ids:
        raise PortableError(
            "active run/field-consumer run coverage mismatch: "
            f"missing={sorted(active_run_ids - consumer_run_ids)!r}, "
            f"extra={sorted(consumer_run_ids - active_run_ids)!r}"
        )

    runtime_ids = tuple(row.runtime_id for row in contract.runtime_entries)
    if len(runtime_ids) != len(set(runtime_ids)):
        raise PortableError("portable runtime IDs must be unique")
    runtime_transform_ids = tuple(
        row.transform_id for row in contract.runtime_entries
    )
    if len(runtime_transform_ids) != len(set(runtime_transform_ids)):
        raise PortableError(
            "portable runtime coverage must contain exactly one row per transform"
        )
    launcher_paths = tuple(row.launcher_path for row in contract.runtime_entries)
    if len(launcher_paths) != len(set(launcher_paths)):
        raise PortableError("portable runtime launcher paths must be unique")
    consumers_by_binding = {
        (row.source_path, row.run_id): row
        for row in contract.consumers
        if row.status == "active"
    }
    expected_runtime_bindings = {
        (
            transform.source_path,
            transform.run_id,
            transform.transform_id,
            consumers_by_binding[(transform.source_path, transform.run_id)].initial_state_recipe_id,
            transform.portable_path,
            next(
                run.portable_entry
                for run in contract.runs
                if run.status == "active" and run.run_id == transform.run_id
            ),
        )
        for transform in contract.transforms
    }
    actual_runtime_bindings = {
        (
            row.source_path,
            row.run_id,
            row.transform_id,
            row.initial_state_recipe_id,
            row.template_path,
            row.launcher_path,
        )
        for row in contract.runtime_entries
    }
    if not contract.runtime_entries or (
        expected_runtime_bindings != actual_runtime_bindings
    ):
        missing = expected_runtime_bindings - actual_runtime_bindings
        extra = actual_runtime_bindings - expected_runtime_bindings
        label = "binding" if contract.runtime_entries else "coverage"
        raise PortableError(
            f"portable runtime {label} mismatch: "
            f"missing={sorted(missing)!r}, extra={sorted(extra)!r}"
        )
    for runtime in contract.runtime_entries:
        consumer = consumers_by_binding[(runtime.source_path, runtime.run_id)]
        if "archive_member_reader" in consumer.roles:
            expected_mode = "thiele_archive"
        elif "known_ovf_reader" in consumer.roles:
            expected_mode = "field_root_analysis"
        else:
            expected_mode = "direct_loader"
        if runtime.mode != expected_mode:
            raise PortableError(
                f"portable runtime mode mismatch for {runtime.transform_id}: "
                f"expected {expected_mode}, found {runtime.mode}"
            )
        if runtime.mode == "field_root_analysis" and (
            consumer.initial_state_recipe_id != "N/A"
            or consumer.non_full_field_data_id == "N/A"
        ):
            raise PortableError(
                "field_root_analysis requires an explicit non-full-field data "
                "dependency; one initial-state recipe cannot close a complete-field reader"
            )

    wrapper_ids = tuple(row.wrapper_id for row in contract.wrapper_contracts)
    if len(wrapper_ids) != len(set(wrapper_ids)):
        raise PortableError("wrapper contract IDs must be unique")
    wrappers_by_id = {row.wrapper_id: row for row in contract.wrapper_contracts}
    expected_wrapper_ids: set[str] = set()
    for transform in contract.transforms:
        if transform.strategy == "wrapper_plus_transform":
            expected_wrapper_ids.add(transform.wrapper_id)
            wrapper = wrappers_by_id.get(transform.wrapper_id)
            if wrapper is None:
                raise PortableError(
                    f"missing wrapper contract for transform: {transform.transform_id}"
                )
            if (
                wrapper.run_id != transform.run_id
                or wrapper.transform_id != transform.transform_id
            ):
                raise PortableError(
                    f"wrapper/transform linkage mismatch: {transform.transform_id}"
                )
            runtime = next(
                row
                for row in contract.runtime_entries
                if row.transform_id == transform.transform_id
            )
            if runtime.mode == "thiele_archive" and wrapper.temporary_paths != (
                "input/m000020.ovf",
                "input/ovf_archive.tar.zst",
            ):
                raise PortableError(
                    "thiele_archive wrapper must declare the exact archive/member paths"
                )
    if expected_wrapper_ids != set(wrappers_by_id):
        raise PortableError("orphan wrapper contract is not bound to one transform")

    try:
        config_text = contract.config_toml.decode("utf-8-sig", errors="strict")
        config = tomllib.loads(config_text)
    except (UnicodeError, tomllib.TOMLDecodeError) as error:
        raise PortableError("PORTABLE_CONFIG.toml must be valid UTF-8 TOML") from error
    if not isinstance(config, Mapping) or not config:
        raise PortableError("PORTABLE_CONFIG.toml must contain a non-empty table")
    findings = scan_structured_values(config, context="00_handoff/PORTABLE_CONFIG.toml")
    if findings:
        raise PortableError(
            "PORTABLE_CONFIG.toml contains machine-specific absolute paths: "
            f"{[(row.field_name, row.matched) for row in findings]!r}"
        )


def _csv_payload(
    columns: tuple[str, ...],
    rows: Sequence[Mapping[str, str]],
) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=list(columns),
        extrasaction="raise",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    return stream.getvalue().encode("utf-8")


def portable_transforms_csv(contract: PortableContract) -> bytes:
    rows: list[dict[str, str]] = []
    for transform in sorted(contract.transforms, key=lambda row: row.transform_id):
        replacements = [
            {
                "old_b64": base64.b64encode(row.old).decode("ascii"),
                "new_b64": base64.b64encode(row.new).decode("ascii"),
                "expected_count": row.expected_count,
            }
            for row in transform.replacements
        ]
        rows.append(
            {
                "transform_id": transform.transform_id,
                "run_id": transform.run_id,
                "source_path": transform.source_path,
                "original_path": transform.original_path,
                "original_sha256": transform.original_sha256,
                "portable_path": transform.portable_path,
                "strategy": transform.strategy,
                "wrapper_id": transform.wrapper_id,
                "replacements_json": json.dumps(
                    replacements, ensure_ascii=True, separators=(",", ":")
                ),
            }
        )
    return _csv_payload(PORTABLE_TRANSFORM_COLUMNS, rows)


def portable_wrappers_csv(contract: PortableContract) -> bytes:
    """Serialize the exact transform-to-unified-runner execution relation."""
    rows = [
        {
            "runtime_id": row.runtime_id,
            "source_path": row.source_path,
            "run_id": row.run_id,
            "transform_id": row.transform_id,
            "initial_state_recipe_id": row.initial_state_recipe_id,
            "runner_path": row.runner_path,
            "launcher_path": row.launcher_path,
            "mode": row.mode,
            "template_path": row.template_path,
            "command_json": row.command_json,
            "runtime_tokens": ";".join(row.runtime_tokens),
        }
        for row in sorted(contract.runtime_entries, key=lambda item: item.transform_id)
    ]
    return _csv_payload(PORTABLE_WRAPPER_COLUMNS, rows)


def initial_state_recipes_csv(contract: PortableContract) -> bytes:
    rows = [
        {
            "recipe_id": row.recipe_id,
            "logical_name": row.logical_name,
            "original_ovf_reference": row.original_ovf_reference,
            "generator_script": row.generator_script,
            "generator_parameters": row.generator_parameters,
            "relaxation_mx3": row.relaxation_mx3,
            "expected_output": row.expected_output,
            "consumers": ";".join(row.consumers),
            "verification_status": row.verification_status,
            "verification_evidence": row.verification_evidence,
            "notes": row.notes,
            "steps_json": row.steps_json,
        }
        for row in sorted(contract.recipes, key=lambda item: item.recipe_id)
    ]
    return _csv_payload(INITIAL_STATE_RECIPE_COLUMNS, rows)


def field_consumers_csv(contract: PortableContract) -> bytes:
    rows = [
        {
            "source_path": row.source_path,
            "roles": ";".join(row.roles),
            "detection_evidence": ";".join(row.detection_evidence),
            "status": row.status,
            "status_evidence": row.status_evidence,
            "run_id": row.run_id,
            "initial_state_recipe_id": row.initial_state_recipe_id,
            "non_full_field_data_id": row.non_full_field_data_id,
            "portable_handling": row.portable_handling,
            "notes": row.notes,
        }
        for row in sorted(contract.consumers, key=lambda item: item.source_path)
    ]
    return _csv_payload(FIELD_CONSUMER_COLUMNS, rows)


def _exclusive_staging_target(staging_root: Path, relative: str) -> Path:
    try:
        path = require_relative_path(relative)
    except ManifestError as error:
        raise PortableError(f"unsafe portable output path: {relative!r}") from error
    current = staging_root
    for part in path.parts[:-1]:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            try:
                current.mkdir()
            except OSError as error:
                raise PortableError(
                    f"cannot create portable output directory: {current}"
                ) from error
            continue
        except OSError as error:
            raise PortableError(f"cannot inspect portable output ancestor: {current}") from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise PortableError(f"portable output ancestor is not a real directory: {current}")
    target = staging_root / path.as_posix()
    try:
        target.lstat()
    except FileNotFoundError:
        return target
    except OSError as error:
        raise PortableError(f"cannot inspect portable output target: {relative}") from error
    raise PortableError(f"portable output collides with an existing target: {relative}")


def _directory_descriptor_without_symlink_ancestors(path: Path, *, label: str) -> int:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not no_follow or not directory_flag:
        raise PortableError(f"{label} requires O_NOFOLLOW and O_DIRECTORY")
    descriptor = -1
    try:
        descriptor = os.open(
            "/",
            os.O_RDONLY | directory_flag | no_follow | getattr(os, "O_CLOEXEC", 0),
        )
        for part in path.absolute().parts[1:]:
            next_descriptor = os.open(
                part,
                os.O_RDONLY
                | directory_flag
                | no_follow
                | getattr(os, "O_CLOEXEC", 0),
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        raise PortableError(f"cannot anchor {label} without symlink traversal") from error


def _staging_parent_descriptor(
    staging_root: Path | int,
    relative: str,
    *,
    create: bool,
) -> tuple[int, str]:
    try:
        path = require_relative_path(relative)
    except ManifestError as error:
        raise PortableError(f"unsafe portable output path: {relative!r}") from error
    if isinstance(staging_root, int):
        try:
            descriptor = os.dup(staging_root)
        except OSError as error:
            raise PortableError("cannot duplicate anchored staging root") from error
    else:
        descriptor = _directory_descriptor_without_symlink_ancestors(
            staging_root, label="staging root"
        )
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    try:
        for part in path.parts[:-1]:
            try:
                next_descriptor = os.open(
                    part,
                    os.O_RDONLY
                    | directory_flag
                    | no_follow
                    | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, 0o755, dir_fd=descriptor)
                next_descriptor = os.open(
                    part,
                    os.O_RDONLY
                    | directory_flag
                    | no_follow
                    | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=descriptor,
                )
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor, path.name
    except OSError as error:
        os.close(descriptor)
        raise PortableError(
            f"cannot traverse portable output ancestors: {relative}"
        ) from error


def _write_exclusive_staging_bytes(
    staging_root: Path | int,
    relative: str,
    payload: bytes,
) -> None:
    parent_descriptor, name = _staging_parent_descriptor(
        staging_root, relative, create=True
    )
    descriptor = -1
    created = False
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            0o644,
            dir_fd=parent_descriptor,
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
                os.unlink(name, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                raise PortableError(
                    f"cannot clean failed portable output: {relative}"
                ) from cleanup_error
        raise PortableError(f"cannot write portable output: {relative}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def _stable_staging_bytes(staging_root: Path | int, *, relative: str) -> bytes:
    parent_descriptor, name = _staging_parent_descriptor(
        staging_root, relative, create=False
    )
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            dir_fd=parent_descriptor,
        )
        before = os.fstat(descriptor)
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise PortableError(f"staged original is not one real file: {relative}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as error:
        raise PortableError(f"cannot read staged original: {relative}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)
    identity = lambda row: (  # noqa: E731 - compact immutable snapshot
        row.st_dev,
        row.st_ino,
        stat.S_IFMT(row.st_mode),
        row.st_size,
        row.st_mtime_ns,
    )
    if identity(before) != identity(after):
        raise PortableError(f"staged original changed while reading: {relative}")
    return b"".join(chunks)


def _chmod_staging_file(
    staging_root: Path | int,
    relative: str,
    mode: int,
) -> None:
    parent_descriptor, name = _staging_parent_descriptor(
        staging_root, relative, create=False
    )
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            dir_fd=parent_descriptor,
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise PortableError(f"portable executable is not one real file: {relative}")
        os.fchmod(descriptor, mode)
    except OSError as error:
        raise PortableError(f"cannot chmod anchored portable output: {relative}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def portable_runner_script() -> bytes:
    """Return the self-contained standard-library runtime entry artifact."""
    return b'''#!/usr/bin/env python3
"""Execute one registered portable transform in an external temp workspace."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import tomllib


COLUMNS = (
    "runtime_id",
    "source_path",
    "run_id",
    "transform_id",
    "initial_state_recipe_id",
    "runner_path",
    "launcher_path",
    "mode",
    "template_path",
    "command_json",
    "runtime_tokens",
)


class RunnerError(RuntimeError):
    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _relative(raw: str, label: str) -> str:
    path = PurePosixPath(raw)
    if (
        not raw
        or "\\\\" in raw
        or path.is_absolute()
        or raw != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise RunnerError(f"unsafe {label}: {raw!r}")
    return raw


def _real_delivery_file(root: Path, relative: str, label: str) -> Path:
    relative = _relative(relative, label)
    path = root / relative
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as error:
            raise RunnerError(f"missing {label}: {relative}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise RunnerError(f"{label} traverses a symlink: {relative}")
    if not stat.S_ISREG(path.lstat().st_mode):
        raise RunnerError(f"{label} is not a real file: {relative}")
    return path


def _read_delivery_bytes(
    root_descriptor: int,
    relative: str,
    label: str,
) -> bytes:
    relative = _relative(relative, label)
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not no_follow or not directory_flag:
        raise RunnerError(f"{label} requires O_NOFOLLOW and O_DIRECTORY")
    directory_descriptor = -1
    descriptor = -1
    try:
        directory_descriptor = os.dup(root_descriptor)
        parts = PurePosixPath(relative).parts
        for part in parts[:-1]:
            next_descriptor = os.open(
                part,
                os.O_RDONLY
                | directory_flag
                | no_follow
                | getattr(os, "O_CLOEXEC", 0),
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_descriptor,
        )
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RunnerError(f"{label} is not a real file: {relative}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if not _same_identity(before, after):
            raise RunnerError(f"{label} changed while it was read: {relative}")
        return b"".join(chunks)
    except RunnerError:
        raise
    except OSError as error:
        raise RunnerError(
            f"cannot read {label} without symlink traversal: {relative}"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if directory_descriptor >= 0:
            os.close(directory_descriptor)


def _real_user_file(raw: str, label: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.absolute()
    for current in (path, *path.parents):
        try:
            metadata = current.lstat()
        except OSError as error:
            raise RunnerError(f"cannot inspect {label}: {path}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise RunnerError(f"{label} traverses a symlink: {current}")
        if current == path and not stat.S_ISREG(metadata.st_mode):
            raise RunnerError(f"{label} must be one real file")
        if current != path and not stat.S_ISDIR(metadata.st_mode):
            raise RunnerError(f"{label} parent is not a real directory")
    return path


def _real_user_directory(raw: str, label: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.absolute()
    for current in (path, *path.parents):
        try:
            metadata = current.lstat()
        except OSError as error:
            raise RunnerError(f"cannot inspect {label}: {path}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise RunnerError(f"{label} traverses a symlink: {current}")
        if not stat.S_ISDIR(metadata.st_mode):
            raise RunnerError(f"{label} must be a real directory")
    return path


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        stat.S_IFMT(left.st_mode),
        left.st_size,
        left.st_mtime_ns,
    ) == (
        right.st_dev,
        right.st_ino,
        stat.S_IFMT(right.st_mode),
        right.st_size,
        right.st_mtime_ns,
    )


def _stable_sha256(path: Path, label: str) -> str:
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise RunnerError(f"{label} must be one real file")
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise RunnerError(f"cannot open {label} safely: {path}") from error
    digest = hashlib.sha256()
    try:
        opened = os.fstat(descriptor)
        if not _same_identity(before, opened):
            raise RunnerError(f"{label} changed while it was opened")
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after_descriptor = os.fstat(descriptor)
    except OSError as error:
        raise RunnerError(f"cannot hash {label}: {path}") from error
    finally:
        os.close(descriptor)
    try:
        after_path = path.lstat()
    except OSError as error:
        raise RunnerError(f"cannot re-inspect {label}: {path}") from error
    if not (
        _same_identity(before, after_descriptor)
        and _same_identity(after_descriptor, after_path)
    ):
        raise RunnerError(f"{label} changed while it was hashed")
    return digest.hexdigest()


def _real_workspace_file(root: Path, path: Path, label: str) -> Path:
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise RunnerError(f"{label} must remain inside the runtime workspace") from error
    current = root
    for part in relative.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as error:
            raise RunnerError(f"cannot inspect {label}: {path}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise RunnerError(f"{label} traverses a symlink")
        if current == path:
            if not stat.S_ISREG(metadata.st_mode):
                raise RunnerError(f"{label} must be one real file")
        elif not stat.S_ISDIR(metadata.st_mode):
            raise RunnerError(f"{label} parent is not a real directory")
    return path


def _is_within(path: Path, root: Path) -> bool:
    try:
        return Path(os.path.commonpath((str(path), str(root)))) == root
    except ValueError:
        return False


def _directory_identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
    )


def _open_anchored_directory(path: Path, label: str) -> int:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not no_follow or not directory_flag:
        raise RunnerError(f"{label} requires O_NOFOLLOW and O_DIRECTORY")
    descriptor = -1
    try:
        descriptor = os.open(
            "/",
            os.O_RDONLY | directory_flag | no_follow | getattr(os, "O_CLOEXEC", 0),
        )
        for part in path.parts[1:]:
            next_descriptor = os.open(
                part,
                os.O_RDONLY
                | directory_flag
                | no_follow
                | getattr(os, "O_CLOEXEC", 0),
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        raise RunnerError(f"cannot anchor {label} without symlink traversal") from error


def _verify_output_directory(
    path: Path,
    descriptor: int,
    delivery_root: Path,
) -> None:
    if _is_within(path, delivery_root) or _is_within(delivery_root, path):
        raise RunnerError("output directory must not overlap the delivery")
    for current in (path, *path.parents):
        try:
            metadata = current.lstat()
        except OSError as error:
            raise RunnerError("cannot re-inspect output directory") from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RunnerError("output directory traverses a symlink/non-directory ancestor")
    try:
        descriptor_metadata = os.fstat(descriptor)
        path_metadata = path.lstat()
    except OSError as error:
        raise RunnerError("cannot verify output directory identity") from error
    if _directory_identity(descriptor_metadata) != _directory_identity(path_metadata):
        raise RunnerError("output directory changed after validation")


def _safe_output_directory(raw: str, delivery_root: Path) -> tuple[Path, int]:
    path = _real_user_directory(raw, "output directory")
    if _is_within(path, delivery_root) or _is_within(delivery_root, path):
        raise RunnerError("output directory must not overlap the delivery")
    descriptor = _open_anchored_directory(path, "output directory")
    try:
        _verify_output_directory(path, descriptor, delivery_root)
    except BaseException:
        os.close(descriptor)
        raise
    return path, descriptor


def _output_parent_descriptor(
    destination_descriptor: int,
    relative: Path,
) -> tuple[int, str]:
    descriptor = os.dup(destination_descriptor)
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    try:
        for part in relative.parts[:-1]:
            try:
                next_descriptor = os.open(
                    part,
                    os.O_RDONLY
                    | directory_flag
                    | no_follow
                    | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                os.mkdir(part, 0o755, dir_fd=descriptor)
                next_descriptor = os.open(
                    part,
                    os.O_RDONLY
                    | directory_flag
                    | no_follow
                    | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=descriptor,
                )
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor, relative.name
    except OSError as error:
        os.close(descriptor)
        raise RunnerError(
            f"runtime output target traverses a symlink/non-directory: {relative}"
        ) from error


def _export_outputs(
    source: Path,
    destination: Path,
    destination_descriptor: int,
    delivery_root: Path,
) -> list[str]:
    _verify_output_directory(destination, destination_descriptor, delivery_root)
    forbidden_suffixes = {
        ".ovf", ".omf", ".tar", ".zst", ".zip", ".gz", ".bz2", ".xz", ".7z"
    }
    files: list[tuple[Path, Path]] = []
    for path in sorted(source.rglob("*")):
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise RunnerError("runtime output export refuses symlinks")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise RunnerError("runtime output export accepts regular files only")
        if any(suffix.casefold() in forbidden_suffixes for suffix in path.suffixes):
            raise RunnerError(f"runtime output export refuses full-field/archive file: {path.name}")
        relative = path.relative_to(source)
        target = destination / relative
        if _is_within(target, delivery_root) or _is_within(delivery_root, target):
            raise RunnerError(f"runtime output target overlaps the delivery: {relative}")
        files.append((path, target))
    opened: list[tuple[Path, int, str, int, str]] = []
    success = False
    try:
        for source_path, target in files:
            relative = target.relative_to(destination)
            parent_descriptor, name = _output_parent_descriptor(
                destination_descriptor, relative
            )
            try:
                os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                pass
            except OSError as error:
                os.close(parent_descriptor)
                raise RunnerError(
                    f"cannot inspect runtime output target: {relative}"
                ) from error
            else:
                os.close(parent_descriptor)
                raise RunnerError(f"runtime output export would overwrite: {relative}")
            try:
                target_descriptor = os.open(
                    name,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0),
                    0o644,
                    dir_fd=parent_descriptor,
                )
            except OSError as error:
                os.close(parent_descriptor)
                raise RunnerError(
                    f"cannot reserve runtime output target: {relative}"
                ) from error
            opened.append(
                (
                    source_path,
                    parent_descriptor,
                    name,
                    target_descriptor,
                    relative.as_posix(),
                )
            )
        for source_path, _parent, _name, target_descriptor, relative in opened:
            try:
                source_descriptor = os.open(
                    source_path,
                    os.O_RDONLY
                    | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0),
                )
                before = os.fstat(source_descriptor)
                if not stat.S_ISREG(before.st_mode):
                    raise RunnerError(f"runtime output is not one real file: {relative}")
                while True:
                    chunk = os.read(source_descriptor, 1024 * 1024)
                    if not chunk:
                        break
                    view = memoryview(chunk)
                    while view:
                        written = os.write(target_descriptor, view)
                        view = view[written:]
                after = os.fstat(source_descriptor)
                if (
                    before.st_dev,
                    before.st_ino,
                    before.st_size,
                    before.st_mtime_ns,
                ) != (
                    after.st_dev,
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                ):
                    raise RunnerError(f"runtime output changed while exporting: {relative}")
                os.fsync(target_descriptor)
            except OSError as error:
                raise RunnerError(f"cannot export runtime output: {relative}") from error
            finally:
                if "source_descriptor" in locals():
                    os.close(source_descriptor)
                    del source_descriptor
        success = True
        return [relative for *_rest, relative in opened]
    finally:
        for _source, parent_descriptor, name, target_descriptor, _relative in opened:
            os.close(target_descriptor)
            if not success:
                try:
                    os.unlink(name, dir_fd=parent_descriptor)
                except FileNotFoundError:
                    pass
            os.close(parent_descriptor)


def _load_rows(payload: bytes) -> tuple[dict[str, str], ...]:
    try:
        text = payload.decode("utf-8-sig", errors="strict")
        reader = csv.DictReader(text.splitlines())
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise RunnerError("PORTABLE_WRAPPERS.csv header mismatch")
        rows = tuple(reader)
    except (UnicodeError, csv.Error) as error:
        raise RunnerError("cannot parse PORTABLE_WRAPPERS.csv") from error
    if not rows:
        raise RunnerError("PORTABLE_WRAPPERS.csv has no runtime rows")
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise RunnerError("PORTABLE_WRAPPERS.csv has extra or missing cells")
    run_ids = tuple(row["run_id"] for row in rows)
    if len(run_ids) != len(set(run_ids)):
        raise RunnerError("PORTABLE_WRAPPERS.csv run_id values are not unique")
    return rows


def _command(row: dict[str, str], values: dict[str, str]) -> list[str]:
    try:
        raw = json.loads(row["command_json"])
    except (TypeError, json.JSONDecodeError) as error:
        raise RunnerError("registered command_json is invalid") from error
    if not isinstance(raw, list) or not raw or not all(
        isinstance(item, str) and item for item in raw
    ):
        raise RunnerError("registered command_json is not a string list")
    try:
        command = [item.format_map(values) for item in raw]
    except (KeyError, ValueError) as error:
        raise RunnerError("registered command has an invalid placeholder") from error
    return command


def _replace_runtime_tokens(
    template: bytes, tokens: tuple[str, ...], values: dict[str, str]
) -> bytes:
    payload = template
    for token in tokens:
        marker = ("${" + token + "}").encode("ascii")
        count = payload.count(marker)
        if count < 1:
            raise RunnerError(f"portable template is missing runtime token {token}")
        payload = payload.replace(marker, os.fsencode(values[token]))
    leftovers = tuple(
        sorted(set(match.decode("ascii") for match in re.findall(rb"\\$\\{[A-Z0-9_]+\\}", payload)))
    )
    if leftovers:
        raise RunnerError(f"portable template has unresolved runtime tokens: {leftovers!r}")
    return payload


def _outside_delivery_workspace(delivery_root: Path, prefix: str) -> Path:
    workspace = Path(tempfile.mkdtemp(prefix=prefix)).absolute()
    try:
        common = Path(os.path.commonpath((str(delivery_root), str(workspace))))
    except ValueError:
        common = Path()
    if common == delivery_root:
        shutil.rmtree(workspace, ignore_errors=True)
        raise RunnerError("runtime temp workspace must be outside the delivery")
    return workspace


def _signal_group(process_group: int, signum: int) -> None:
    try:
        os.killpg(process_group, signum)
    except ProcessLookupError:
        pass


def _group_exists(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_for_group(
    child: subprocess.Popen[bytes], process_group: int, timeout: float
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        child.poll()
        if not _group_exists(process_group):
            return True
        time.sleep(0.02)
    child.poll()
    return not _group_exists(process_group)


def _stop_process_group(
    child: subprocess.Popen[bytes], process_group: int
) -> None:
    if _group_exists(process_group):
        _signal_group(process_group, signal.SIGTERM)
        if not _wait_for_group(child, process_group, 0.5):
            _signal_group(process_group, signal.SIGKILL)
            _wait_for_group(child, process_group, 1.0)
    if child.poll() is None:
        try:
            child.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            _signal_group(process_group, signal.SIGKILL)
            try:
                child.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass


def _run_child(
    command: list[str],
    workspace: Path,
    *,
    stdout: object = None,
    stderr: object = None,
) -> int:
    try:
        child = subprocess.Popen(
            command,
            cwd=workspace,
            start_new_session=True,
            stdout=stdout,
            stderr=stderr,
        )
    except OSError as error:
        raise RunnerError(f"cannot start registered command: {command[0]!r}") from error
    process_group = child.pid
    interrupted = {"signal": 0}
    previous: dict[int, object] = {}

    def forward(signum: int, _frame: object) -> None:
        if not interrupted["signal"]:
            interrupted["signal"] = signum
        _signal_group(process_group, signum)

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, forward)
        while True:
            code = child.poll()
            if interrupted["signal"]:
                _wait_for_group(child, process_group, 0.5)
                _stop_process_group(child, process_group)
                return 128 + interrupted["signal"]
            if code is not None:
                return code
            time.sleep(0.02)
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        _stop_process_group(child, process_group)


def _stable_executable_identity(
    raw: str,
    label: str,
) -> tuple[Path, tuple[int, int, int, str]]:
    candidate = _real_user_file(raw, label)
    if not os.access(candidate, os.X_OK):
        raise RunnerError(f"{label} is not executable")
    try:
        before = candidate.lstat()
    except OSError as error:
        raise RunnerError(f"cannot inspect {label}: {candidate}") from error
    digest = _stable_sha256(candidate, label)
    try:
        after = candidate.lstat()
    except OSError as error:
        raise RunnerError(f"cannot re-inspect {label}: {candidate}") from error
    if not _same_identity(before, after):
        raise RunnerError(f"{label} changed while its identity was recorded")
    return candidate, (
        before.st_dev,
        before.st_ino,
        stat.S_IFMT(before.st_mode),
        digest,
    )


def _same_executable_file(
    left: tuple[int, int, int, str],
    right: tuple[int, int, int, str],
) -> bool:
    return left[:3] == right[:3]


def _archive_validator(
    producer_identity: tuple[int, int, int, str],
) -> str:
    for name in ("tar.exe", "bsdtar", "tar"):
        resolved = shutil.which(name)
        if resolved is None:
            continue
        try:
            candidate, candidate_identity = _stable_executable_identity(
                resolved,
                "archive validation executable",
            )
        except RunnerError:
            continue
        if _same_executable_file(candidate_identity, producer_identity):
            continue
        return str(candidate)
    raise RunnerError("an independent tar executable is required to validate the archive")


def _verify_thiele_archive(
    archive: Path,
    dependency: Path,
    workspace: Path,
    expected_sha256: str,
    producer_identity: tuple[int, int, int, str],
) -> None:
    _real_workspace_file(workspace, archive, "temporary archive")
    if _stable_sha256(dependency, "temporary OVF member") != expected_sha256:
        raise RunnerError("temporary OVF member differs from the supplied initial state")
    validation_root = workspace / "archive-validation"
    extraction_root = validation_root / "extracted"
    try:
        validation_root.mkdir()
        extraction_root.mkdir()
    except OSError as error:
        raise RunnerError("cannot create isolated archive validation workspace") from error
    validator = _archive_validator(producer_identity)
    archive_relative = archive.relative_to(workspace).as_posix()
    listing = validation_root / "members.txt"
    try:
        with listing.open("xb") as handle:
            list_code = _run_child(
                [validator, "-tf", archive_relative],
                workspace,
                stdout=handle,
                stderr=subprocess.DEVNULL,
            )
    except OSError as error:
        raise RunnerError("cannot record the temporary archive member listing") from error
    if list_code != 0:
        raise RunnerError("temporary archive failed independent validation")
    try:
        members = listing.read_bytes().splitlines()
    except OSError as error:
        raise RunnerError("cannot read the temporary archive member listing") from error
    if members != [dependency.name.encode("utf-8")]:
        raise RunnerError(
            "temporary archive must contain exactly the m000020.ovf member"
        )
    member_types = validation_root / "member-types.txt"
    try:
        with member_types.open("xb") as handle:
            type_code = _run_child(
                [validator, "-tvf", archive_relative],
                workspace,
                stdout=handle,
                stderr=subprocess.DEVNULL,
            )
    except OSError as error:
        raise RunnerError("cannot record the temporary archive member types") from error
    if type_code != 0:
        raise RunnerError("temporary archive member types failed independent validation")
    try:
        type_rows = member_types.read_bytes().splitlines()
    except OSError as error:
        raise RunnerError("cannot read the temporary archive member types") from error
    if len(type_rows) != 1 or type_rows[0][:1] != b"-":
        raise RunnerError("temporary archive member must be a regular file entry")
    extraction_relative = extraction_root.relative_to(workspace).as_posix()
    extract_code = _run_child(
        [
            validator,
            "-xf",
            archive_relative,
            "-C",
            extraction_relative,
            dependency.name,
        ],
        workspace,
        stderr=subprocess.DEVNULL,
    )
    if extract_code != 0:
        raise RunnerError("temporary archive member could not be extracted safely")
    extracted = _real_workspace_file(
        extraction_root,
        extraction_root / dependency.name,
        "extracted temporary OVF member",
    )
    if _stable_sha256(extracted, "extracted temporary OVF member") != expected_sha256:
        raise RunnerError("temporary archive member bytes differ from the supplied initial state")


def _safe_evidence_output(raw: str, delivery_root: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.absolute()
    if _is_within(path, delivery_root):
        raise RunnerError("evidence output must be outside the delivery")
    try:
        leaf = path.lstat()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise RunnerError(f"cannot inspect evidence output: {path}") from error
    else:
        if stat.S_ISLNK(leaf.st_mode) or not stat.S_ISREG(leaf.st_mode):
            raise RunnerError("evidence output must be a real file or a new path")
    for parent in path.parents:
        try:
            metadata = parent.lstat()
        except OSError as error:
            raise RunnerError(f"cannot inspect evidence parent: {parent}") from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RunnerError("evidence output traverses a symlink/non-directory ancestor")
    return path


def _write_evidence(path: Path, evidence: dict[str, object]) -> None:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not no_follow or not directory_flag:
        raise RunnerError("evidence output requires O_NOFOLLOW and O_DIRECTORY")
    directory_descriptor = -1
    descriptor = -1
    temporary = ""
    try:
        directory_descriptor = os.open(
            "/",
            os.O_RDONLY | directory_flag | no_follow | getattr(os, "O_CLOEXEC", 0),
        )
        for part in path.parent.parts[1:]:
            next_descriptor = os.open(
                part,
                os.O_RDONLY
                | directory_flag
                | no_follow
                | getattr(os, "O_CLOEXEC", 0),
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        try:
            target_metadata = os.stat(
                path.name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISLNK(target_metadata.st_mode) or not stat.S_ISREG(
                target_metadata.st_mode
            ):
                raise RunnerError(
                    "evidence output must be a real file or a new path"
                )
        for _attempt in range(128):
            temporary = ".portable-evidence-" + os.urandom(16).hex()
            try:
                descriptor = os.open(
                    temporary,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | no_follow
                    | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                    dir_fd=directory_descriptor,
                )
            except FileExistsError:
                continue
            break
        else:
            raise RunnerError("cannot allocate exclusive evidence temporary file")
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\\n") as handle:
            descriptor = -1
            json.dump(evidence, handle, indent=2, sort_keys=True)
            handle.write("\\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(
            temporary,
            path.name,
            src_dir_fd=directory_descriptor,
            dst_dir_fd=directory_descriptor,
        )
        temporary = ""
        os.fsync(directory_descriptor)
    except OSError as error:
        raise RunnerError(f"cannot write evidence output: {path}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary and directory_descriptor >= 0:
            try:
                os.unlink(temporary, dir_fd=directory_descriptor)
            except FileNotFoundError:
                pass
        if directory_descriptor >= 0:
            os.close(directory_descriptor)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one Hopfion portable entry in an external temp workspace."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--initial-state")
    parser.add_argument("--field-root")
    parser.add_argument("--tar-executable")
    parser.add_argument("--output-dir")
    parser.add_argument("--evidence-out")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    delivery_root = Path(__file__).absolute().parents[2]
    evidence: dict[str, object] = {
        "run_id": args.run_id,
        "dependency_provenance": "dependency_supplied_by_user",
        "initial_state_sha256": "N/A",
        "full_chain_reconstruction": False,
        "archive_producer_exit_code": None,
        "command_exit_code": None,
        "exported_outputs": [],
        "workspace": "N/A",
        "workspace_cleaned": True,
    }
    workspace: Path | None = None
    evidence_path: Path | None = None
    output_directory: Path | None = None
    output_directory_descriptor = -1
    delivery_descriptor = -1
    exit_code = 2
    error_text = ""
    try:
        delivery_descriptor = _open_anchored_directory(
            delivery_root, "delivery root"
        )
        if args.evidence_out:
            evidence_path = _safe_evidence_output(
                args.evidence_out, delivery_root
            )
        if args.output_dir:
            output_directory, output_directory_descriptor = _safe_output_directory(
                args.output_dir, delivery_root
            )
        config_payload = _read_delivery_bytes(
            delivery_descriptor,
            "00_handoff/PORTABLE_CONFIG.toml",
            "PORTABLE_CONFIG.toml",
        )
        try:
            config = tomllib.loads(
                config_payload.decode("utf-8-sig", errors="strict")
            )
        except (UnicodeError, tomllib.TOMLDecodeError) as error:
            raise RunnerError("cannot parse relative PORTABLE_CONFIG.toml") from error
        if not isinstance(config, dict) or not config:
            raise RunnerError("PORTABLE_CONFIG.toml must contain a table")
        registry_payload = _read_delivery_bytes(
            delivery_descriptor,
            "00_handoff/PORTABLE_WRAPPERS.csv",
            "PORTABLE_WRAPPERS.csv",
        )
        matches = [
            row
            for row in _load_rows(registry_payload)
            if row["run_id"] == args.run_id
        ]
        if len(matches) != 1:
            raise RunnerError(f"run_id is not registered exactly once: {args.run_id}")
        row = matches[0]
        mode = row["mode"]
        if mode not in {
            "direct_loader",
            "field_root_analysis",
            "thiele_archive",
        }:
            raise RunnerError(f"runtime mode is not implemented: {mode}")
        if mode in {"direct_loader", "thiele_archive"} and not args.initial_state:
            raise RunnerError(
                f"{mode} requires explicit --initial-state; documented-only recipes are not auto-reconstructed"
            )
        user_input = None
        user_input_sha256 = ""
        field_root = None
        if mode in {"direct_loader", "thiele_archive"}:
            user_input = _real_user_file(args.initial_state, "initial state")
            user_input_sha256 = _stable_sha256(user_input, "initial state")
            evidence["initial_state_sha256"] = user_input_sha256
        else:
            if not args.field_root:
                raise RunnerError(
                    "field_root_analysis requires explicit --field-root; no historical full fields are packaged"
                )
            field_root = _real_user_directory(args.field_root, "field root")
        runtime_config = config.get("runtime", {})
        prefix = "hopfion-portable-"
        if isinstance(runtime_config, dict):
            configured = runtime_config.get("temp_prefix", prefix)
            if isinstance(configured, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,48}", configured):
                prefix = configured
        workspace = _outside_delivery_workspace(delivery_root, prefix)
        evidence["workspace"] = str(workspace)
        dependency_dir = workspace / "dependency"
        runtime_dir = workspace / "run"
        output_root = workspace / "output"
        dependency_dir.mkdir()
        runtime_dir.mkdir()
        output_root.mkdir()
        dependency: Path | None = None
        if user_input is not None:
            dependency = dependency_dir / (
                "m000020.ovf" if mode == "thiele_archive" else "input.bin"
            )
            shutil.copyfile(user_input, dependency)
            if _stable_sha256(dependency, "temporary initial-state copy") != user_input_sha256:
                raise RunnerError("temporary initial-state copy differs from the supplied file")
        else:
            (dependency_dir / "field-root.alias").write_text(
                str(field_root), encoding="utf-8"
            )
        template_payload = _read_delivery_bytes(
            delivery_descriptor,
            row["template_path"],
            "portable template",
        )
        template_name = PurePosixPath(row["template_path"]).name
        tokens = tuple(filter(None, row["runtime_tokens"].split(";")))
        archive_source = ""
        tar_executable = "tar"
        if mode == "direct_loader":
            expected_tokens = ("INIT_OVF",)
            assert dependency is not None
            token_values = {"INIT_OVF": str(dependency)}
        elif mode == "thiele_archive":
            expected_tokens = ("ARCHIVE_SOURCE", "OUTPUT_ROOT", "TAR_EXE")
            assert dependency is not None
            selected_tar = args.tar_executable
            if not selected_tar and isinstance(runtime_config, dict):
                configured_tar = runtime_config.get("tar_executable")
                if isinstance(configured_tar, str) and configured_tar:
                    selected_tar = configured_tar
            selected_tar = selected_tar or "tar"
            if "/" in selected_tar or "\\\\" in selected_tar:
                tar_path, producer_identity = _stable_executable_identity(
                    selected_tar,
                    "tar executable",
                )
                tar_executable = str(tar_path)
            else:
                resolved_tar = shutil.which(selected_tar)
                if resolved_tar is None:
                    raise RunnerError(f"tar executable is unavailable: {selected_tar}")
                tar_path, producer_identity = _stable_executable_identity(
                    resolved_tar,
                    "tar executable",
                )
                tar_executable = str(tar_path)
            archive = dependency_dir / "ovf_archive.tar.zst"
            producer_command = [
                tar_executable,
                "--create",
                "--zstd",
                "--file",
                str(archive),
                "-C",
                str(dependency_dir),
                dependency.name,
            ]
            producer_code = _run_child(producer_command, workspace)
            evidence["archive_producer_exit_code"] = producer_code
            if producer_code != 0:
                normalized = producer_code if 1 <= producer_code <= 255 else 2
                raise RunnerError(
                    f"temporary archive producer failed with exit code {producer_code}",
                    normalized,
                )
            _verify_thiele_archive(
                archive,
                dependency,
                workspace,
                user_input_sha256,
                producer_identity,
            )
            archive_source = str(archive)
            token_values = {
                "ARCHIVE_SOURCE": archive_source,
                "OUTPUT_ROOT": str(output_root),
                "TAR_EXE": tar_executable,
            }
        else:
            expected_tokens = ("FIELD_ROOT", "OUTPUT_ROOT")
            assert field_root is not None
            token_values = {
                "FIELD_ROOT": str(field_root),
                "OUTPUT_ROOT": str(output_root),
            }
        if tokens != expected_tokens:
            raise RunnerError(f"{mode} runtime token contract mismatch")
        runtime_entry = runtime_dir / template_name
        runtime_entry.write_bytes(
            _replace_runtime_tokens(template_payload, tokens, token_values)
        )
        values = {
            "delivery_root": str(delivery_root),
            "runtime_entry": str(runtime_entry),
            "dependency": str(dependency) if dependency is not None else "",
            "workspace": str(workspace),
            "output_root": str(output_root),
            "archive_source": archive_source,
            "tar_executable": tar_executable,
            "field_root": str(field_root) if field_root is not None else "",
        }
        command = _command(row, values)
        command_code = _run_child(command, workspace)
        evidence["command_exit_code"] = command_code
        if command_code != 0:
            normalized = command_code if 1 <= command_code <= 255 else 2
            raise RunnerError(
                f"registered command failed with exit code {command_code}", normalized
            )
        if output_directory is not None:
            evidence["exported_outputs"] = _export_outputs(
                output_root,
                output_directory,
                output_directory_descriptor,
                delivery_root,
            )
        exit_code = 0
    except RunnerError as error:
        error_text = str(error)
        exit_code = error.exit_code
    except BaseException as error:
        error_text = f"unexpected runner failure: {type(error).__name__}: {error}"
        exit_code = 2
    finally:
        if delivery_descriptor >= 0:
            os.close(delivery_descriptor)
        if output_directory_descriptor >= 0:
            os.close(output_directory_descriptor)
        if workspace is not None:
            try:
                shutil.rmtree(workspace)
            except OSError as error:
                evidence["workspace_cleaned"] = False
                error_text = f"runtime cleanup failed: {error}"
                exit_code = 2
            else:
                evidence["workspace_cleaned"] = not workspace.exists()
        evidence["exit_code"] = exit_code
        evidence["error"] = error_text
        if evidence_path is not None:
            try:
                _write_evidence(evidence_path, evidence)
            except (OSError, RunnerError) as error:
                print(f"portable runner evidence failure: {error}", file=sys.stderr)
                exit_code = 2
                evidence["exit_code"] = exit_code
                evidence_failure = f"evidence write failed: {error}"
                error_text = (
                    f"{error_text}; {evidence_failure}"
                    if error_text
                    else evidence_failure
                )
                evidence["error"] = error_text
        print(json.dumps(evidence, sort_keys=True))
        if error_text:
            print(f"portable runner: {error_text}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
'''


def portable_launcher_script(runtime: PortableRuntimeEntry) -> bytes:
    """Return a per-run executable that locates and delegates to the runner."""
    run_id = json.dumps(runtime.run_id, ensure_ascii=True)
    launcher_parts = repr(PurePosixPath(runtime.launcher_path).parts)
    runner_path = json.dumps(runtime.runner_path, ensure_ascii=True)
    source = f'''#!/usr/bin/env python3
"""Portable launcher for one registered Hopfion run."""

from __future__ import annotations

import os
from pathlib import Path
import sys


RUN_ID = {run_id}
LAUNCHER_PATH_PARTS = {launcher_parts}
RUNNER_PATH = {runner_path}


def main() -> int:
    launcher = Path(__file__).absolute()
    root = launcher
    for _part in LAUNCHER_PATH_PARTS:
        root = root.parent
    if root.joinpath(*LAUNCHER_PATH_PARTS) != launcher:
        print("portable launcher is not at its registered relative path", file=sys.stderr)
        return 2
    runner = root / RUNNER_PATH
    registry = root / "00_handoff/PORTABLE_WRAPPERS.csv"
    if not runner.is_file() or not registry.is_file():
        print("portable launcher cannot identify its delivery runner", file=sys.stderr)
        return 2
    os.execv(
        sys.executable,
        [sys.executable, str(runner), "--run-id", RUN_ID, *sys.argv[1:]],
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''
    return source.encode("utf-8")


def materialize_portable_contract(
    contract: PortableContract,
    *,
    staging_root: Path,
    _retain_staging_descriptor: bool = False,
) -> tuple[str, ...] | _PinnedPortableMaterialization:
    """Create portable entries and ledgers exclusively inside isolated staging."""
    written: list[str] = []
    staging_descriptor = _directory_descriptor_without_symlink_ancestors(
        staging_root, label="staging root"
    )
    try:
        for transform in sorted(contract.transforms, key=lambda row: row.transform_id):
            original = _stable_staging_bytes(
                staging_descriptor, relative=transform.original_path
            )
            portable = apply_portable_transform(original, transform)
            _write_exclusive_staging_bytes(
                staging_descriptor, transform.portable_path, portable
            )
            staged_portable = _stable_staging_bytes(
                staging_descriptor,
                relative=transform.portable_path,
            )
            if reverse_portable_transform(staged_portable, transform) != original:
                raise PortableError(
                    f"portable reverse verification failed: {transform.transform_id}"
                )
            if _stable_staging_bytes(
                staging_descriptor, relative=transform.original_path
            ) != original:
                raise PortableError(
                    "portable generation modified the archival original: "
                    f"{transform.original_path}"
                )
            written.append(transform.portable_path)

        for runtime in sorted(contract.runtime_entries, key=lambda row: row.transform_id):
            _write_exclusive_staging_bytes(
                staging_descriptor,
                runtime.launcher_path,
                portable_launcher_script(runtime),
            )
            try:
                _chmod_staging_file(staging_descriptor, runtime.launcher_path, 0o755)
            except PortableError as error:
                raise PortableError("cannot make portable launcher executable") from error
            written.append(runtime.launcher_path)

        evidence_payloads = {
            "00_handoff/PORTABLE_TRANSFORMS.csv": portable_transforms_csv(contract),
            "00_handoff/PORTABLE_WRAPPERS.csv": portable_wrappers_csv(contract),
            "00_handoff/INITIAL_STATE_RECIPES.csv": initial_state_recipes_csv(contract),
            "00_handoff/FULL_FIELD_CONSUMERS.csv": field_consumers_csv(contract),
            "00_handoff/PORTABLE_CONFIG.toml": contract.config_toml,
            PORTABLE_RUNNER_PATH: portable_runner_script(),
        }
        for relative in PORTABLE_OUTPUT_PATHS:
            _write_exclusive_staging_bytes(
                staging_descriptor, relative, evidence_payloads[relative]
            )
            if relative == PORTABLE_RUNNER_PATH:
                try:
                    _chmod_staging_file(staging_descriptor, relative, 0o755)
                except PortableError as error:
                    raise PortableError("cannot make portable runner executable") from error
            written.append(relative)

        descriptor_metadata = os.fstat(staging_descriptor)
        try:
            path_metadata = staging_root.lstat()
        except OSError as error:
            raise PortableError("staging root changed during materialization") from error
        identity = lambda row: (  # noqa: E731 - immutable filesystem identity
            row.st_dev,
            row.st_ino,
            stat.S_IFMT(row.st_mode),
        )
        if (
            stat.S_ISLNK(path_metadata.st_mode)
            or identity(descriptor_metadata) != identity(path_metadata)
        ):
            raise PortableError("staging root changed during materialization")
        try:
            scan_result = scan_delivery_absolute_paths(
                staging_root,
                root_descriptor=staging_descriptor,
                _include_snapshot=True,
            )
        except PortableError as error:
            try:
                failed_path_metadata = staging_root.lstat()
            except OSError:
                failed_path_metadata = None
            if (
                failed_path_metadata is None
                or stat.S_ISLNK(failed_path_metadata.st_mode)
                or identity(descriptor_metadata) != identity(failed_path_metadata)
            ):
                raise PortableError(
                    "staging root changed during materialization"
                ) from error
            raise
        try:
            final_path_metadata = staging_root.lstat()
        except OSError as error:
            raise PortableError("staging root changed during materialization") from error
        if (
            stat.S_ISLNK(final_path_metadata.st_mode)
            or identity(descriptor_metadata) != identity(final_path_metadata)
        ):
            raise PortableError("staging root changed during materialization")
        if not isinstance(scan_result, _PinnedDeliveryScan):
            raise PortableError("pinned G4 scan did not return a tree snapshot")
        if scan_result.findings:
            raise PortableError(
                "G4 executable scan found machine-specific absolute paths: "
                f"{[(row.relative_path, row.line_number, row.field_name, row.matched) for row in scan_result.findings]!r}"
            )
        written_paths = tuple(written)
        if not _retain_staging_descriptor:
            return written_paths
        retained_metadata = os.fstat(staging_descriptor)
        try:
            retained_path_metadata = staging_root.lstat()
        except OSError as error:
            raise PortableError("staging root changed after G4 verification") from error
        retained_identity = (
            retained_metadata.st_dev,
            retained_metadata.st_ino,
            stat.S_IFMT(retained_metadata.st_mode),
            retained_metadata.st_size,
            retained_metadata.st_mtime_ns,
        )
        retained_path_identity = (
            retained_path_metadata.st_dev,
            retained_path_metadata.st_ino,
            stat.S_IFMT(retained_path_metadata.st_mode),
            retained_path_metadata.st_size,
            retained_path_metadata.st_mtime_ns,
        )
        if (
            not stat.S_ISDIR(retained_metadata.st_mode)
            or stat.S_ISLNK(retained_path_metadata.st_mode)
            or retained_identity != retained_path_identity
        ):
            raise PortableError("staging root changed after G4 verification")
        retained_descriptor = staging_descriptor
        staging_descriptor = -1
        return _PinnedPortableMaterialization(
            written_paths,
            retained_descriptor,
            retained_identity,
            scan_result.snapshot,
        )
    finally:
        if staging_descriptor >= 0:
            os.close(staging_descriptor)


@contextmanager
def temporary_dependency_workspace(
    staging_root: Path,
    contract: TemporaryDependencyContract,
    payloads: Mapping[str, bytes],
) -> Iterator[Path]:
    """Materialize wrapper inputs under staging temp and remove them on exit."""
    try:
        root_metadata = staging_root.lstat()
        marker_metadata = (staging_root / ".handoff-staging").lstat()
    except OSError as error:
        raise PortableError("wrapper requires a real staging marker") from error
    if (
        stat.S_ISLNK(root_metadata.st_mode)
        or not stat.S_ISDIR(root_metadata.st_mode)
        or stat.S_ISLNK(marker_metadata.st_mode)
        or not stat.S_ISREG(marker_metadata.st_mode)
    ):
        raise PortableError("wrapper requires a real staging marker")
    try:
        marker = (staging_root / ".handoff-staging").read_text(
            encoding="utf-8", errors="strict"
        ).strip()
    except (OSError, UnicodeError) as error:
        raise PortableError("wrapper staging marker cannot be read") from error
    if not marker:
        raise PortableError("wrapper staging marker must be non-empty")

    normalized_payloads: dict[str, bytes] = {}
    for raw, payload in payloads.items():
        try:
            normalized = require_relative_path(raw).as_posix()
        except ManifestError as error:
            raise PortableError(f"unsafe wrapper payload path: {raw!r}") from error
        if not isinstance(payload, bytes):
            raise PortableError("wrapper payload values must be bytes")
        normalized_payloads[normalized] = payload
    if set(normalized_payloads) != set(contract.temporary_paths):
        raise PortableError(
            "wrapper payload set does not exactly match temporary_paths"
        )

    workspace = Path(
        tempfile.mkdtemp(prefix=".portable-temp-", dir=staging_root)
    )
    try:
        for relative in contract.temporary_paths:
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with target.open("xb") as handle:
                    handle.write(normalized_payloads[relative])
                    handle.flush()
            except OSError as error:
                raise PortableError(
                    f"cannot materialize wrapper temporary dependency: {relative}"
                ) from error
        yield workspace
    finally:
        try:
            shutil.rmtree(workspace)
        except FileNotFoundError:
            pass
        except (OSError, shutil.Error) as error:
            raise PortableError(
                f"cannot clean wrapper temporary workspace: {workspace}"
            ) from error


_ABSOLUTE_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/][^\s\"'`,;)\]}]*)"),
    re.compile(
        r"(?:\\{2,}|(?<!:)/{2})[A-Za-z0-9._$-]+[\\/]+"
        r"[A-Za-z0-9._$-]+[^\s\"'`,;)\]}]*"
    ),
    re.compile(r"/mnt/[A-Za-z](?:/[^\s\"'`,;)\]}]*)?"),
    re.compile(r"/home/[^/\s\"'`,;)\]}]+(?:/[^\s\"'`,;)\]}]*)?"),
    re.compile(r"/(?:[^\s\"'`,;)\]}]+/)*(?:\.worktrees|worktrees)(?:/[^\s\"'`,;)\]}]*)?"),
)


def scan_executable_text(
    text: str | bytes,
    *,
    context: str = "<memory>",
    field_name: str = "text",
) -> tuple[AbsolutePathFinding, ...]:
    """Return every fixed-family machine-specific absolute path literal."""
    if isinstance(text, bytes):
        decoded = text.decode("utf-8-sig", errors="replace")
    elif isinstance(text, str):
        decoded = text
    else:
        raise PortableError("absolute-path scanning accepts only str or bytes")
    findings: list[AbsolutePathFinding] = []
    seen: set[tuple[int, int, str]] = set()
    for pattern in _ABSOLUTE_PATTERNS:
        for match in pattern.finditer(decoded):
            key = (match.start(), match.end(), match.group(0))
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                AbsolutePathFinding(
                    relative_path=context,
                    line_number=decoded.count("\n", 0, match.start()) + 1,
                    field_name=field_name,
                    matched=match.group(0),
                )
            )
    return tuple(
        sorted(
            findings,
            key=lambda row: (row.line_number, row.field_name, row.matched),
        )
    )


def _scan_python_executable(
    payload: bytes,
    *,
    context: str,
) -> tuple[AbsolutePathFinding, ...]:
    text = _decode_python_source(payload, context=context)
    tree = _parse_python_source(text, context=context)
    findings = list(scan_executable_text(text, context=context))
    seen = {(row.line_number, row.matched) for row in findings}
    for value, line in _folded_python_strings(tree):
        for finding in scan_executable_text(
            value,
            context=context,
            field_name="python.constant",
        ):
            adjusted_line = line + finding.line_number - 1
            key = (adjusted_line, finding.matched)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                AbsolutePathFinding(
                    relative_path=context,
                    line_number=adjusted_line,
                    field_name="python.constant",
                    matched=finding.matched,
                )
            )
    return tuple(
        sorted(
            findings,
            key=lambda row: (row.line_number, row.field_name, row.matched),
        )
    )


PROVENANCE_ABSOLUTE_PATH_FIELDS = frozenset(
    {"source_path", "original_ovf_reference", "parent_source"}
)


def scan_structured_values(
    value: Any,
    *,
    context: str,
    _field_path: tuple[str, ...] = (),
    _allowed_provenance_fields: frozenset[str] = frozenset(),
) -> tuple[AbsolutePathFinding, ...]:
    """Scan structured executable values with only three provenance exemptions."""
    if _field_path and _field_path[-1] in _allowed_provenance_fields:
        return ()
    findings: list[AbsolutePathFinding] = []
    if isinstance(value, Mapping):
        for key in sorted(value, key=lambda item: str(item)):
            findings.extend(
                scan_structured_values(
                    value[key],
                    context=context,
                    _field_path=(*_field_path, str(key)),
                    _allowed_provenance_fields=_allowed_provenance_fields,
                )
            )
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(
                scan_structured_values(
                    item,
                    context=context,
                    _field_path=(*_field_path, str(index)),
                    _allowed_provenance_fields=_allowed_provenance_fields,
                )
            )
    elif isinstance(value, str):
        field = ".".join(_field_path) if _field_path else "value"
        findings.extend(
            scan_executable_text(value, context=context, field_name=field)
        )
    return tuple(findings)


_G4_SUFFIXES = frozenset(
    {".mx3", ".py", ".sh", ".ps1", ".m", ".json", ".yaml", ".yml", ".toml"}
)


def _is_g4_executable_path(relative: PurePosixPath) -> bool:
    if not relative.parts:
        return False
    if relative.parts[0] == "90_archive":
        return False
    pairs = set(zip(relative.parts, relative.parts[1:]))
    if ("simulation", "original") in pairs:
        return False
    raw = relative.as_posix()
    if raw == "00_handoff/PORTABLE_CONFIG.toml":
        return True
    if len(relative.parts) >= 2 and relative.parts[0] == "shared":
        return relative.parts[1] in {
            "analysis",
            "plotting",
            "initial_state",
            "runtime",
        }
    if not re.fullmatch(r"0[1-5]_[^/]+", relative.parts[0]):
        return False
    return (
        ("simulation", "portable") in pairs
        or "analysis" in relative.parts
        or "run" in relative.name.casefold()
    )


def _load_structured_payload(payload: bytes, relative: str) -> Any:
    suffix = PurePosixPath(relative).suffix.casefold()
    try:
        text = payload.decode("utf-8-sig", errors="strict")
        if suffix == ".json":
            return json.loads(text)
        if suffix == ".toml":
            return tomllib.loads(text)
        if suffix in {".yaml", ".yml"}:
            try:
                import yaml  # type: ignore[import-not-found]
            except ImportError as error:
                raise PortableError(
                    f"YAML scanner dependency is unavailable for {relative}"
                ) from error
            return yaml.safe_load(text)
    except (UnicodeError, ValueError) as error:
        raise PortableError(f"cannot parse structured executable file: {relative}") from error
    raise PortableError(f"unsupported structured executable file: {relative}")


def _load_structured_file(path: Path, relative: str) -> Any:
    try:
        return _load_structured_payload(path.read_bytes(), relative)
    except OSError as error:
        raise PortableError(f"cannot read structured executable file: {relative}") from error


def _scan_manifest_csv_payload(
    payload: bytes,
    relative: str,
) -> tuple[AbsolutePathFinding, ...]:
    try:
        text = payload.decode("utf-8-sig", errors="strict")
        with io.StringIO(text, newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise PortableError(f"manifest has no header: {relative}")
            rows = tuple(reader)
    except (UnicodeError, csv.Error) as error:
        raise PortableError(f"cannot parse executable manifest: {relative}") from error
    findings: list[AbsolutePathFinding] = []
    executable_markers = (
        "command",
        "executable",
        "script_path",
        "portable_entry",
        "runner_path",
        "launcher_path",
        "template_path",
        "generator_script",
        "relaxation_mx3",
    )
    for row_number, row in enumerate(rows, start=2):
        selected = {
            key: value
            for key, value in row.items()
            if key in PROVENANCE_ABSOLUTE_PATH_FIELDS
            or any(marker in key.casefold() for marker in executable_markers)
        }
        for finding in scan_structured_values(
            selected,
            context=relative,
            _allowed_provenance_fields=PROVENANCE_ABSOLUTE_PATH_FIELDS,
        ):
            findings.append(
                AbsolutePathFinding(
                    relative_path=finding.relative_path,
                    line_number=row_number,
                    field_name=finding.field_name,
                    matched=finding.matched,
                )
            )
    return tuple(findings)


def _scan_manifest_csv(path: Path, relative: str) -> tuple[AbsolutePathFinding, ...]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise PortableError(f"cannot read executable manifest: {relative}") from error
    return _scan_manifest_csv_payload(payload, relative)


def _descriptor_snapshot(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def _read_delivery_descriptor(descriptor: int, relative: str) -> bytes:
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise PortableError(f"delivery scan entry is not a regular file: {relative}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as error:
        raise PortableError(f"cannot read delivery executable: {relative}") from error
    if _descriptor_snapshot(before) != _descriptor_snapshot(after):
        raise PortableError(f"delivery executable changed during scan: {relative}")
    return b"".join(chunks)


def _walk_delivery_descriptor(
    descriptor: int,
    prefix: PurePosixPath = PurePosixPath(),
) -> tuple[
    tuple[tuple[PurePosixPath, bytes], ...],
    tuple[_PinnedTreeEntry, ...],
]:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    try:
        before = os.fstat(descriptor)
        with os.scandir(descriptor) as iterator:
            entries = tuple(sorted(iterator, key=lambda row: row.name))
        rows: list[tuple[PurePosixPath, bytes]] = []
        snapshot: list[_PinnedTreeEntry] = []
        for entry in entries:
            relative = prefix / entry.name
            metadata = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode):
                raise PortableError(
                    f"delivery executable scan refuses symlinks: {relative.as_posix()}"
                )
            if stat.S_ISDIR(metadata.st_mode):
                snapshot.append(
                    _PinnedTreeEntry(
                        relative.as_posix(),
                        "directory",
                        stat.S_IMODE(metadata.st_mode),
                        0,
                        "",
                    )
                )
                child = os.open(
                    entry.name,
                    os.O_RDONLY
                    | directory_flag
                    | no_follow
                    | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=descriptor,
                )
                try:
                    child_rows, child_snapshot = _walk_delivery_descriptor(
                        child, relative
                    )
                    rows.extend(child_rows)
                    snapshot.extend(child_snapshot)
                finally:
                    os.close(child)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise PortableError(
                    "delivery scan accepts regular files and directories only: "
                    f"{relative.as_posix()}"
                )
            file_descriptor = os.open(
                entry.name,
                os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0),
                dir_fd=descriptor,
            )
            try:
                payload = _read_delivery_descriptor(
                    file_descriptor, relative.as_posix()
                )
                rows.append((relative, payload))
                snapshot.append(
                    _PinnedTreeEntry(
                        relative.as_posix(),
                        "file",
                        stat.S_IMODE(metadata.st_mode),
                        len(payload),
                        hashlib.sha256(payload).hexdigest(),
                    )
                )
            finally:
                os.close(file_descriptor)
        after = os.fstat(descriptor)
    except OSError as error:
        raise PortableError(
            f"cannot enumerate pinned delivery scan tree: {prefix.as_posix()}"
        ) from error
    if _descriptor_snapshot(before) != _descriptor_snapshot(after):
        raise PortableError(
            f"delivery directory changed during scan: {prefix.as_posix()}"
        )
    return tuple(rows), tuple(snapshot)


def _snapshot_delivery_descriptor(
    descriptor: int,
) -> tuple[_PinnedTreeEntry, ...]:
    """Recompute the complete regular-file/directory snapshot for one root fd."""
    _rows, snapshot = _walk_delivery_descriptor(descriptor)
    return snapshot


def scan_delivery_absolute_paths(
    root: Path,
    *,
    root_descriptor: int | None = None,
    _include_snapshot: bool = False,
) -> tuple[AbsolutePathFinding, ...] | _PinnedDeliveryScan:
    """Apply the exact G4 executable/provenance boundary to a staged delivery."""
    try:
        root_metadata = root.lstat()
    except OSError as error:
        raise PortableError(f"cannot inspect delivery root: {root}") from error
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        raise PortableError("delivery scan root must be one real directory")
    owned_descriptor = root_descriptor is None
    descriptor = (
        _directory_descriptor_without_symlink_ancestors(root, label="delivery scan root")
        if root_descriptor is None
        else os.dup(root_descriptor)
    )
    try:
        descriptor_metadata = os.fstat(descriptor)
        rows, snapshot = _walk_delivery_descriptor(descriptor)
        findings: list[AbsolutePathFinding] = []
        for relative_path, payload in rows:
            relative = relative_path.as_posix()
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
            if relative_path.suffix.casefold() not in _G4_SUFFIXES or not _is_g4_executable_path(
                relative_path
            ):
                continue
            if relative_path.suffix.casefold() in {".json", ".yaml", ".yml", ".toml"}:
                value = _load_structured_payload(payload, relative)
                findings.extend(scan_structured_values(value, context=relative))
            elif relative_path.suffix.casefold() == ".py":
                findings.extend(_scan_python_executable(payload, context=relative))
            else:
                findings.extend(scan_executable_text(payload, context=relative))
        try:
            final_path_metadata = root.lstat()
        except OSError as error:
            raise PortableError("delivery scan root changed during scan") from error
        if (
            stat.S_ISLNK(final_path_metadata.st_mode)
            or _descriptor_snapshot(descriptor_metadata)
            != _descriptor_snapshot(final_path_metadata)
        ):
            raise PortableError("delivery scan root changed during scan")
    finally:
        os.close(descriptor)
    ordered_findings = tuple(
        sorted(
            findings,
            key=lambda row: (
                row.relative_path,
                row.line_number,
                row.field_name,
                row.matched,
            ),
        )
    )
    if _include_snapshot:
        return _PinnedDeliveryScan(ordered_findings, snapshot)
    return ordered_findings


def _all_occurrences(payload: bytes, literal: bytes) -> tuple[int, ...]:
    starts: list[int] = []
    offset = 0
    while True:
        found = payload.find(literal, offset)
        if found < 0:
            return tuple(starts)
        starts.append(found)
        offset = found + 1


def _validated_spans(
    payload: bytes,
    replacements: tuple[LiteralReplacement, ...],
    *,
    reverse: bool,
) -> tuple[tuple[int, int, bytes], ...]:
    new_literals = tuple(row.new for row in replacements)
    if len(new_literals) != len(set(new_literals)):
        raise PortableError("replacement new literals must be unique")
    for index, left in enumerate(new_literals):
        for right in new_literals[index + 1 :]:
            if left in right or right in left:
                raise PortableError(
                    "replacement new literals must not be equal or substrings"
                )

    spans: list[tuple[int, int, bytes]] = []
    for row in replacements:
        source = row.new if reverse else row.old
        target = row.old if reverse else row.new
        if not reverse and row.new in payload:
            raise PortableError(
                f"replacement new literal already exists in original bytes: {row.new!r}"
            )
        starts = _all_occurrences(payload, source)
        if len(starts) != row.expected_count:
            raise PortableError(
                "literal occurrence count mismatch: "
                f"expected {row.expected_count}, found {len(starts)} for {source!r}"
            )
        spans.extend((start, start + len(source), target) for start in starts)

    spans.sort(key=lambda item: (item[0], item[1]))
    for left, right in zip(spans, spans[1:]):
        if right[0] < left[1]:
            raise PortableError(
                "literal replacement spans overlap and are therefore ambiguous"
            )
    return tuple(spans)


def _replace_original_spans(
    payload: bytes,
    spans: tuple[tuple[int, int, bytes], ...],
) -> bytes:
    pieces: list[bytes] = []
    cursor = 0
    for start, end, replacement in spans:
        pieces.append(payload[cursor:start])
        pieces.append(replacement)
        cursor = end
    pieces.append(payload[cursor:])
    return b"".join(pieces)


def apply_portable_transform(original: bytes, transform: PortableTransform) -> bytes:
    """Apply every registered replacement once by source-byte offsets."""
    if not isinstance(original, bytes):
        raise PortableError("portable transforms operate on bytes only")
    digest = hashlib.sha256(original).hexdigest()
    if digest != transform.original_sha256:
        raise PortableError(
            "original SHA256 does not match the portable transform contract"
        )
    if transform.strategy == "identity":
        return original
    spans = _validated_spans(original, transform.replacements, reverse=False)
    portable = _replace_original_spans(original, spans)
    # This also catches an implementation error that generated an irreversible
    # byte stream before a caller can stage it.
    reverse_portable_transform(portable, transform)
    return portable


def reverse_portable_transform(portable: bytes, transform: PortableTransform) -> bytes:
    """Reverse only registered new literals and verify the archival SHA256."""
    if not isinstance(portable, bytes):
        raise PortableError("portable transforms operate on bytes only")
    if transform.strategy == "identity":
        if hashlib.sha256(portable).hexdigest() != transform.original_sha256:
            raise PortableError(
                "identity reverse did not recover the registered original SHA256"
            )
        return portable
    spans = _validated_spans(portable, transform.replacements, reverse=True)
    original = _replace_original_spans(portable, spans)
    if hashlib.sha256(original).hexdigest() != transform.original_sha256:
        raise PortableError(
            "reverse transform did not recover the registered original SHA256"
        )
    return original


def validate_portable_coverage(
    runs: tuple[RunEntry, ...],
    transforms: tuple[PortableTransform, ...],
) -> None:
    """Require a one-to-one, exact, non-empty active-run transform mapping."""
    if not isinstance(runs, tuple) or not isinstance(transforms, tuple):
        raise PortableError("run and transform collections must be immutable tuples")
    run_ids = tuple(row.run_id for row in runs)
    if len(run_ids) != len(set(run_ids)):
        raise PortableError("run_id values must be unique")
    transform_ids = tuple(row.transform_id for row in transforms)
    if len(transform_ids) != len(set(transform_ids)):
        raise PortableError("transform_id values must be unique")
    transform_run_ids = tuple(row.run_id for row in transforms)
    if len(transform_run_ids) != len(set(transform_run_ids)):
        raise PortableError(
            "each active run_id must map to exactly one portable transform"
        )
    originals = tuple(row.original_path for row in transforms)
    portables = tuple(row.portable_path for row in transforms)
    if len(originals) != len(set(originals)):
        raise PortableError("each original must map to exactly one transform")
    if len(portables) != len(set(portables)):
        raise PortableError("each portable output must map to exactly one transform")

    active = tuple(row for row in runs if row.status == "active")
    if not active or not transforms:
        raise PortableError("active portable coverage must be non-empty")
    launchers = tuple(row.portable_entry for row in active)
    if len(launchers) != len(set(launchers)):
        raise PortableError("each active run must have one unique portable launcher")
    expected = {
        (row.run_id, row.original_path)
        for row in active
    }
    actual = {
        (row.run_id, row.original_path)
        for row in transforms
    }
    if expected != actual:
        raise PortableError(
            "active run/transform coverage mismatch: "
            f"missing={sorted(expected - actual)!r}, extra={sorted(actual - expected)!r}"
        )
