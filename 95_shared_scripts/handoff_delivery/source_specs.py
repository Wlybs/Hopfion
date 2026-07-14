"""Authoritative source enumeration and deterministic v2 routing.

This module encodes design section 5.1 as data.  It enumerates every regular
file and symbolic link under the declared roots before applying content or
routing decisions, so exclusions remain auditable rather than silent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Literal, overload

from .inventory import InspectionResult, inspect_candidate
from .models import ManifestError, require_relative_path


Disposition = Literal[
    "copied_active",
    "copied_archive",
    "excluded_with_reason",
]
TargetClass = Literal["active", "archive", "excluded"]
Route = Literal["fixed", "spinwave", "mechanism", "shared"]


class SourceSpecError(ValueError):
    """Raised when the authoritative source set cannot be enumerated safely."""


class AnchoredRoot:
    """No-follow, dirfd-anchored access beneath one trusted real directory."""

    def __init__(
        self,
        root: Path | str,
        *,
        error_type: type[Exception] = SourceSpecError,
    ) -> None:
        self.root = Path(root)
        self._error_type = error_type
        self._root_fd = -1

    def _error(self, message: str, cause: OSError | None = None) -> Exception:
        error = self._error_type(message)
        if cause is not None:
            error.__cause__ = cause
        return error

    def __enter__(self) -> AnchoredRoot:
        no_follow = getattr(os, "O_NOFOLLOW", 0)
        directory = getattr(os, "O_DIRECTORY", 0)
        if not no_follow or not directory:
            raise self._error("anchored traversal requires O_NOFOLLOW and O_DIRECTORY")
        try:
            self._root_fd = os.open(
                self.root,
                os.O_RDONLY | no_follow | directory | getattr(os, "O_CLOEXEC", 0),
            )
            metadata = os.fstat(self._root_fd)
        except OSError as error:
            if self._root_fd >= 0:
                os.close(self._root_fd)
                self._root_fd = -1
            raise self._error(f"cannot anchor real project root: {self.root}", error)
        if not stat.S_ISDIR(metadata.st_mode):
            os.close(self._root_fd)
            self._root_fd = -1
            raise self._error(f"anchored root is not a directory: {self.root}")
        proc_anchor = Path(f"/proc/self/fd/{self._root_fd}")
        try:
            if not self._same_identity(proc_anchor.stat(), metadata):
                raise OSError("/proc/self/fd identity mismatch")
        except OSError as error:
            os.close(self._root_fd)
            self._root_fd = -1
            raise self._error("/proc/self/fd is unavailable for anchored inspection", error)
        return self

    def __exit__(self, *_: object) -> None:
        if self._root_fd >= 0:
            os.close(self._root_fd)
            self._root_fd = -1

    @staticmethod
    def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
        return (
            left.st_dev == right.st_dev
            and left.st_ino == right.st_ino
            and stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
        )

    def _parts(self, relative: str) -> tuple[str, ...]:
        return tuple(_validated_relative(relative, context="anchored path").split("/"))

    def _open_directory_parts(self, parts: Sequence[str]) -> int:
        if self._root_fd < 0:
            raise self._error("anchored root is not open")
        descriptor = os.dup(self._root_fd)
        traversed: list[str] = []
        flags = (
            os.O_RDONLY
            | os.O_NOFOLLOW
            | os.O_DIRECTORY
            | getattr(os, "O_CLOEXEC", 0)
        )
        try:
            for part in parts:
                traversed.append(part)
                next_descriptor = -1
                try:
                    next_descriptor = os.open(part, flags, dir_fd=descriptor)
                    opened = os.fstat(next_descriptor)
                except OSError as error:
                    if next_descriptor >= 0:
                        os.close(next_descriptor)
                    raise self._error(
                        "anchored directory traversal failed at "
                        f"{'/'.join(traversed)}",
                        error,
                    )
                if not stat.S_ISDIR(opened.st_mode):
                    os.close(next_descriptor)
                    raise self._error(
                        "anchored path component is not a directory: "
                        f"{'/'.join(traversed)}"
                    )
                os.close(descriptor)
                descriptor = next_descriptor
            return descriptor
        except Exception:
            os.close(descriptor)
            raise

    def open_directory(self, relative: str) -> int:
        return self._open_directory_parts(self._parts(relative))

    def _open_parent(self, relative: str) -> tuple[int, str]:
        parts = self._parts(relative)
        return self._open_directory_parts(parts[:-1]), parts[-1]

    def lstat(self, relative: str) -> os.stat_result:
        parent_fd, leaf = self._open_parent(relative)
        try:
            try:
                return os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
            except OSError as error:
                raise self._error(f"cannot stat anchored path: {relative}", error)
        finally:
            os.close(parent_fd)

    def require_directory(self, relative: str, *, label: str) -> None:
        descriptor = self.open_directory(relative)
        try:
            if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise self._error(f"{label} is not a real directory: {relative}")
        finally:
            os.close(descriptor)

    def require_file_candidate(self, relative: str, *, label: str) -> None:
        metadata = self.lstat(relative)
        if not (stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode)):
            raise self._error(f"{label} is not a file or symlink: {relative}")

    def open_regular(self, relative: str) -> int:
        parent_fd, leaf = self._open_parent(relative)
        descriptor = -1
        try:
            try:
                descriptor = os.open(
                    leaf,
                    os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=parent_fd,
                )
                metadata = os.fstat(descriptor)
            except OSError as error:
                if descriptor >= 0:
                    os.close(descriptor)
                raise self._error(f"cannot open anchored regular file: {relative}", error)
            if not stat.S_ISREG(metadata.st_mode):
                os.close(descriptor)
                raise self._error(f"anchored path is not a regular file: {relative}")
            return descriptor
        finally:
            os.close(parent_fd)

    def read_text(self, relative: str, *, label: str) -> str:
        descriptor = self.open_regular(relative)
        try:
            with os.fdopen(descriptor, "rb", closefd=True) as handle:
                descriptor = -1
                payload = handle.read()
        except OSError as error:
            raise self._error(f"cannot read {label}: {relative}", error)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        try:
            return payload.decode("utf-8")
        except UnicodeError as error:
            raise self._error(f"cannot decode {label}: {relative}") from error

    def inspect(self, relative: str) -> InspectionResult:
        parent_fd, leaf = self._open_parent(relative)
        try:
            proc_path = Path(f"/proc/self/fd/{parent_fd}") / leaf
            return inspect_candidate(proc_path)
        finally:
            os.close(parent_fd)

    def _directory_entries(
        self, descriptor: int, *, label: str
    ) -> tuple[tuple[str, os.stat_result], ...]:
        try:
            with os.scandir(descriptor) as iterator:
                names = sorted(entry.name for entry in iterator)
            entries = tuple(
                (
                    name,
                    os.stat(name, dir_fd=descriptor, follow_symlinks=False),
                )
                for name in names
            )
        except OSError as error:
            raise self._error(f"cannot enumerate anchored directory: {label}", error)
        return entries

    def list_directory(self, relative: str) -> tuple[tuple[str, os.stat_result], ...]:
        descriptor = self.open_directory(relative)
        try:
            return self._directory_entries(descriptor, label=relative)
        finally:
            os.close(descriptor)

    def iter_tree(self, relative: str) -> tuple[str, ...]:
        root_parts = self._parts(relative)
        root_fd = self._open_directory_parts(root_parts)
        candidates: list[str] = []

        def recurse(descriptor: int, lexical_parts: tuple[str, ...]) -> None:
            label = "/".join(lexical_parts)
            for name, metadata in self._directory_entries(descriptor, label=label):
                child_parts = lexical_parts + (name,)
                child = "/".join(child_parts)
                if stat.S_ISDIR(metadata.st_mode):
                    child_fd = -1
                    try:
                        child_fd = os.open(
                            name,
                            os.O_RDONLY
                            | os.O_NOFOLLOW
                            | os.O_DIRECTORY
                            | getattr(os, "O_CLOEXEC", 0),
                            dir_fd=descriptor,
                        )
                        opened = os.fstat(child_fd)
                    except OSError as error:
                        if child_fd >= 0:
                            os.close(child_fd)
                        raise self._error(
                            f"anchored directory changed during traversal: {child}",
                            error,
                        )
                    if not self._same_identity(metadata, opened):
                        os.close(child_fd)
                        raise self._error(
                            f"anchored directory identity changed: {child}"
                        )
                    try:
                        recurse(child_fd, child_parts)
                    finally:
                        os.close(child_fd)
                else:
                    candidates.append(child)

        try:
            recurse(root_fd, root_parts)
        finally:
            os.close(root_fd)
        return tuple(candidates)


def _validated_relative(raw: str, *, context: str) -> str:
    try:
        return require_relative_path(raw).as_posix()
    except ManifestError as error:
        raise SourceSpecError(f"{context}: {error}") from error


@dataclass(frozen=True, slots=True)
class TreeSourceSpec:
    """One recursively enumerated source root and its active target route."""

    source_root: str
    target_prefix: str
    route: Route = "fixed"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_root",
            _validated_relative(self.source_root, context="source root"),
        )
        object.__setattr__(
            self,
            "target_prefix",
            _validated_relative(self.target_prefix, context="target prefix"),
        )
        if self.route not in {"fixed", "spinwave", "mechanism", "shared"}:
            raise SourceSpecError(f"unsupported route: {self.route!r}")


@dataclass(frozen=True, slots=True)
class ExactSourceSpec:
    """One exact required file and its complete active target path."""

    source_path: str
    target_path: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_path",
            _validated_relative(self.source_path, context="source path"),
        )
        object.__setattr__(
            self,
            "target_path",
            _validated_relative(self.target_path, context="target path"),
        )


@dataclass(frozen=True, slots=True)
class RequiredAssetRow:
    """The sole disposition assigned to one source candidate."""

    source_path: str
    target_path: str | None
    disposition: Disposition
    expected_target_class: TargetClass
    reason: str
    sha256: str
    size: int
    file_type: str


@dataclass(frozen=True, slots=True)
class RequiredAssetInventory(Sequence[RequiredAssetRow]):
    """An immutable, source-sorted required-assets inventory."""

    rows: tuple[RequiredAssetRow, ...]

    @overload
    def __getitem__(self, index: int) -> RequiredAssetRow: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[RequiredAssetRow, ...]: ...

    def __getitem__(
        self, index: int | slice
    ) -> RequiredAssetRow | tuple[RequiredAssetRow, ...]:
        return self.rows[index]

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def status(self) -> tuple[Disposition, ...]:
        return tuple(row.disposition for row in self.rows)

    def source_paths_are_unique(self) -> bool:
        paths = tuple(row.source_path for row in self.rows)
        return len(paths) == len(set(paths))

    def target_paths_are_unique(self) -> bool:
        paths = tuple(row.target_path for row in self.rows if row.target_path)
        return len(paths) == len(set(paths))


TREE_SOURCE_SPECS: tuple[TreeSourceSpec, ...] = (
    TreeSourceSpec("07_thiele_theory_model", "03_mechanism_and_theory/thiele"),
    TreeSourceSpec(
        "04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test",
        "01_stability/frustrated_fm/centered_stability_test",
    ),
    TreeSourceSpec(
        "04_frustrated_fm_foundation/20260105_frustrated_fm/anisotropy_study",
        "01_stability/frustrated_fm/anisotropy_study",
    ),
    TreeSourceSpec(
        "04_frustrated_fm_foundation/20260105_frustrated_fm/size_sweep",
        "01_stability/frustrated_fm/size_sweep",
    ),
    TreeSourceSpec(
        "04_frustrated_fm_foundation/20260105_frustrated_fm/drift_experiments",
        "01_stability/frustrated_fm/drift_experiments",
    ),
    TreeSourceSpec(
        "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics",
        "02_spinwave_control",
        route="spinwave",
    ),
    TreeSourceSpec(
        "06_eigenmode_frequency_mechanism",
        "03_mechanism_and_theory",
        route="mechanism",
    ),
    TreeSourceSpec(
        "hopfion_eigenmode_mechanism_20260612",
        "03_mechanism_and_theory/eigenmode_controls",
    ),
    TreeSourceSpec(
        "08_lif_neuron_device_application/lif_neuron_hopfion",
        "04_lif_device",
    ),
    TreeSourceSpec("95_shared_scripts", "shared", route="shared"),
)


EXACT_SOURCE_SPECS: tuple[ExactSourceSpec, ...] = (
    ExactSourceSpec(
        "00_project_index/hopfion_spinwave_paper_master_plan_20260703.md",
        "05_papers_and_talks/paper_guidance/"
        "hopfion_spinwave_paper_master_plan_20260703.md",
    ),
    ExactSourceSpec(
        "09_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608/"
        "B_point_vs_plane.md",
        "03_mechanism_and_theory/literature_claims/B_point_vs_plane.md",
    ),
    ExactSourceSpec(
        "09_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608/"
        "D_skyrmion_spinwave_theory_library_20260705.md",
        "03_mechanism_and_theory/literature_claims/"
        "D_skyrmion_spinwave_theory_library_20260705.md",
    ),
    ExactSourceSpec(
        "09_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608/"
        "E_skyrmion_spinwave_source_geometry_claim_ledger_20260705.md",
        "03_mechanism_and_theory/literature_claims/"
        "E_skyrmion_spinwave_source_geometry_claim_ledger_20260705.md",
    ),
    ExactSourceSpec(
        "09_paper_thesis_talks/"
        "skyrmion_spinwave_dynamics_literature_report_20260705.pptx",
        "05_papers_and_talks/presentations/"
        "skyrmion_spinwave_dynamics_literature_report_20260705.pptx",
    ),
    ExactSourceSpec(
        "04_frustrated_fm_foundation/20260105_frustrated_fm/compute_hopf_index.py",
        "01_stability/frustrated_fm/compute_hopf_index.py",
    ),
)


FORMAL_THESIS_CHAPTERS: tuple[str, ...] = (
    "ch01-intro.tex",
    "ch02-theory.tex",
    "ch03-construction.tex",
    "ch04-stability.tex",
    "ch05-dynamics.tex",
    "ch06-neuromorphic.tex",
    "ch07-conclusion.tex",
)

_THESIS_ROOT = PurePosixPath("09_paper_thesis_talks/bishe/thesis_v2")
_INCLUDE_GRAPHICS = re.compile(
    r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", re.MULTILINE
)


_SPINWAVE_FIRST_DIRECTORY_ROUTES = {
    "drive_selection": "drive_selection",
    "freq_sweep": "frequency_sweeps",
    "amplitude_sweep": "amplitude_sweeps",
    "multisource_control": "multisource",
    "reverse_propagation_controls": "reverse_propagation",
    "viby_plane_wave": "point_vs_plane",
    "viby_point_source": "point_vs_plane",
}


def _spinwave_category(relative: PurePosixPath) -> str:
    if relative.parts:
        first_directory = relative.parts[0].casefold()
        if category := _SPINWAVE_FIRST_DIRECTORY_ROUTES.get(first_directory):
            return category
    label = "/".join(relative.parts).casefold()
    if "freq" in label:
        return "frequency_sweeps"
    if "amplitude" in label:
        return "amplitude_sweeps"
    if "multi" in label:
        return "multisource"
    if "reverse" in label:
        return "reverse_propagation"
    if "point" in label or "plane" in label:
        return "point_vs_plane"
    return "drive_selection"


def _mechanism_category(relative: PurePosixPath) -> str:
    label = "/".join(relative.parts).casefold()
    if "energy" in label and "audit" in label:
        return "energy_audit"
    if "ringdown" in label:
        return "ringdown"
    if "mode_map" in label:
        return "mode_maps"
    if any(word in label for word in ("literature", "link", "explanation")):
        return "literature_claims"
    return "eigenmode_controls"


def _shared_category(relative: PurePosixPath) -> str:
    label = "/".join(relative.parts).casefold()
    if any(word in label for word in ("initial_state", "create_hopfion", "gen_hopfion")):
        return "initial_state"
    if any(word in label for word in ("plot", "draw", "figure", "paper_style")):
        return "plotting"
    return "analysis"


def _tree_target(spec: TreeSourceSpec, relative: PurePosixPath) -> str:
    prefix = PurePosixPath(spec.target_prefix)
    if spec.route == "spinwave":
        target = prefix / _spinwave_category(relative) / relative
    elif spec.route == "mechanism":
        target = prefix / _mechanism_category(relative) / relative
    elif spec.route == "shared":
        target = prefix / _shared_category(relative) / relative
    else:
        target = prefix / relative
    return _validated_relative(target.as_posix(), context="computed target")


def _strip_tex_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        comment_at: int | None = None
        for index, character in enumerate(line):
            if character != "%":
                continue
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                comment_at = index
                break
        lines.append(line if comment_at is None else line[:comment_at] + "\n")
    return "".join(lines)


def _resolve_graphics_reference(
    anchor: AnchoredRoot,
    thesis_root: PurePosixPath,
    reference: str,
) -> str | None:
    normalized = reference.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    try:
        relative = require_relative_path(normalized)
    except ManifestError as error:
        raise SourceSpecError(f"unsafe thesis figure reference {reference!r}") from error
    if not relative.parts or relative.parts[0] != "figures":
        return None

    candidate_path = thesis_root / relative
    candidate = candidate_path.as_posix()
    if candidate_path.suffix:
        anchor.require_file_candidate(candidate, label="formal thesis figure")
        return candidate

    matches: list[str] = []
    for suffix in (".png", ".pdf", ".jpg", ".jpeg", ".svg"):
        path = PurePosixPath(candidate).with_suffix(suffix).as_posix()
        try:
            metadata = anchor.lstat(path)
        except SourceSpecError as error:
            if isinstance(error.__cause__, FileNotFoundError):
                continue
            raise
        if stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            matches.append(path)
    if len(matches) != 1:
        raise SourceSpecError(
            f"formal thesis figure reference must resolve uniquely: {reference!r}"
        )
    return matches[0]


def _thesis_asset_targets(anchor: AnchoredRoot) -> dict[str, str]:
    chapters_root = _THESIS_ROOT / "chapters"
    figures_root = _THESIS_ROOT / "figures"
    anchor.require_directory(
        chapters_root.as_posix(), label="formal thesis chapters root"
    )
    anchor.require_directory(
        figures_root.as_posix(), label="formal thesis figures root"
    )

    candidates: set[str] = set()
    for chapter_name in FORMAL_THESIS_CHAPTERS:
        chapter = (chapters_root / chapter_name).as_posix()
        anchor.require_file_candidate(chapter, label="formal thesis chapter")
        text = anchor.read_text(chapter, label="formal thesis chapter")
        for match in _INCLUDE_GRAPHICS.finditer(_strip_tex_comments(text)):
            resolved = _resolve_graphics_reference(anchor, _THESIS_ROOT, match.group(1))
            if resolved is not None:
                candidates.add(resolved)

    for name, metadata in anchor.list_directory(figures_root.as_posix()):
        if PurePosixPath(name).suffix.casefold() not in {".py", ".csv"}:
            continue
        candidate = (figures_root / name).as_posix()
        if not (stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode)):
            raise SourceSpecError(
                f"thesis figure dependency is not a file or symlink: {candidate}"
            )
        candidates.add(candidate)

    result: dict[str, str] = {}
    for source in sorted(candidates):
        target = (
            PurePosixPath("05_papers_and_talks/thesis_final/figures")
            / PurePosixPath(source).name
        )
        result[source] = _validated_relative(target.as_posix(), context="thesis target")
    return result


def _add_candidate(
    candidates: dict[str, str],
    targets: dict[str, str],
    *,
    source: str,
    target: str,
) -> None:
    source = _validated_relative(source, context="candidate source")
    target = _validated_relative(target, context="candidate target")
    if PurePosixPath(source).name.casefold() == "readme.md":
        target = (
            PurePosixPath(target).with_name("SOURCE_CONTEXT.md").as_posix()
        )
    previous_target = candidates.get(source)
    if previous_target is not None and previous_target != target:
        raise SourceSpecError(
            f"source candidate has conflicting targets: {source!r} -> "
            f"{previous_target!r}, {target!r}"
        )
    previous_source = targets.get(target)
    if previous_source is not None and previous_source != source:
        raise SourceSpecError(
            f"target collision: {previous_source!r} and {source!r} -> {target!r}"
        )
    candidates[source] = target
    targets[target] = source


def _collect_candidate_targets(
    anchor: AnchoredRoot,
    *,
    tree_specs: Sequence[TreeSourceSpec],
    exact_specs: Sequence[ExactSourceSpec],
    include_thesis_assets: bool,
) -> dict[str, str]:
    candidates: dict[str, str] = {}
    targets: dict[str, str] = {}

    for spec in tree_specs:
        anchor.require_directory(
            spec.source_root, label=f"source root {spec.source_root}"
        )
        source_root = PurePosixPath(spec.source_root)
        for source in anchor.iter_tree(spec.source_root):
            relative = PurePosixPath(source).relative_to(source_root)
            _add_candidate(
                candidates,
                targets,
                source=source,
                target=_tree_target(spec, relative),
            )

    for spec in exact_specs:
        anchor.require_file_candidate(
            spec.source_path, label=f"required source {spec.source_path}"
        )
        _add_candidate(
            candidates,
            targets,
            source=spec.source_path,
            target=spec.target_path,
        )

    if include_thesis_assets:
        for source, target in _thesis_asset_targets(anchor).items():
            _add_candidate(
                candidates,
                targets,
                source=source,
                target=target,
            )
    return candidates


_CACHE_DIRECTORY_NAMES = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".cache",
        "node_modules",
        ".venv",
        "venv",
        "preview",
        "previews",
    }
)
_TEMPORARY_SUFFIXES = (".pyc", ".pyo", ".tmp", ".lock", ".pid", ".swp")
_BACKUP_SUFFIXES = (".bak", ".backup", ".orig")
_LITERAL_FIELD_SUFFIXES = (".ovf", ".omf", ".ovf.gz", ".omf.gz")
_ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tar.zst", ".tgz", ".tzst", ".7z", ".rar")
_CANONICAL_FAILED_LIF_PREFIX = (
    "08_lif_neuron_device_application/lif_neuron_hopfion/lif_cycle_demo/"
)


def _obvious_field_exclusion(
    source: str, metadata: os.stat_result
) -> tuple[str, int, str] | None:
    """Skip multi-gigabyte hashing only when the field identity is explicit."""
    if not stat.S_ISREG(metadata.st_mode):
        return None
    name = PurePosixPath(source).name.casefold()
    if name.endswith(_LITERAL_FIELD_SUFFIXES):
        return "literal-field-name-unhashed", metadata.st_size, "file"
    if "ovf_archive" in name and name.endswith(_ARCHIVE_SUFFIXES):
        return "explicit-ovf-archive-name-unhashed", metadata.st_size, "file"
    return None


def _preclassification_exclusion(source: str) -> str | None:
    path = PurePosixPath(source)
    parts = tuple(part.casefold() for part in path.parts)
    name = path.name.casefold()
    if (
        "hopfion_delivery_20260706" in parts
        and name == "readme.md"
    ):
        return "generated-v1-readme"
    if any(part in _CACHE_DIRECTORY_NAMES for part in parts[:-1]):
        return "cache-directory"
    if name.endswith(_BACKUP_SUFFIXES):
        return "backup-file"
    if name.endswith(_TEMPORARY_SUFFIXES) or name.endswith("~"):
        return "cache-or-temporary-file"
    if "templates" in parts or name.endswith((".template", ".tmpl")):
        return "template-file"
    if any("毕业设计模板" in part or "latex-hdu-bachelor-thesis" in part for part in parts):
        return "school-template"
    if source.startswith("95_shared_scripts/") and (
        name.startswith(("_test_", "test_"))
        or "test_outputs" in parts
        or "test-output" in parts
    ):
        return "shared-test-artifact"
    return None


def _archive_category(source: str) -> str | None:
    label = source.casefold()
    if "legacy" in label:
        return "legacy_code"
    if "superseded" in label:
        return "superseded_figures"
    if "interrupted" in label or "incomplete" in label:
        return "interrupted_runs"
    if "failed" in label:
        return "failed_explorations"
    return None


def _archive_decision(source: str) -> tuple[str, str] | None:
    if source.startswith(_CANONICAL_FAILED_LIF_PREFIX):
        return (
            "failed_explorations",
            "canonical-status:Hopfion-Physics/progress.md:L89:"
            "LIF-Phase-2-first-cycle=FAILED",
        )
    category = _archive_category(source)
    if category is None:
        return None
    return category, f"archive-status-marker:{category}"


def _archive_target(source: str, category: str) -> str:
    target = PurePosixPath("90_archive") / category / PurePosixPath(source)
    if PurePosixPath(source).name.casefold() == "readme.md":
        target = target.with_name("SOURCE_CONTEXT.md")
    return _validated_relative(target.as_posix(), context="archive target")


def _copied_reason(source: str, base: str) -> str:
    if PurePosixPath(source).name.casefold() == "readme.md":
        return f"{base}:source-README-renamed-to-SOURCE_CONTEXT.md"
    return base


def enumerate_required_assets(
    project_root: Path | str,
    *,
    tree_specs: Sequence[TreeSourceSpec] = TREE_SOURCE_SPECS,
    exact_specs: Sequence[ExactSourceSpec] = EXACT_SOURCE_SPECS,
    include_thesis_assets: bool = True,
) -> RequiredAssetInventory:
    """Enumerate the complete design-5.1 candidate set and route every row once."""
    root = Path(project_root)
    with AnchoredRoot(root) as anchor:
        candidate_targets = _collect_candidate_targets(
            anchor,
            tree_specs=tuple(tree_specs),
            exact_specs=tuple(exact_specs),
            include_thesis_assets=include_thesis_assets,
        )

        rows: list[RequiredAssetRow] = []
        copied_targets: dict[str, str] = {}
        for source, active_target in sorted(candidate_targets.items()):
            metadata = anchor.lstat(source)
            obvious_field = _obvious_field_exclusion(source, metadata)
            preliminary_reason = _preclassification_exclusion(source)
            if obvious_field is not None:
                reason, size, file_type = obvious_field
                row = RequiredAssetRow(
                    source_path=source,
                    target_path=None,
                    disposition="excluded_with_reason",
                    expected_target_class="excluded",
                    reason=reason,
                    sha256="",
                    size=size,
                    file_type=file_type,
                )
                rows.append(row)
                continue

            inspection = anchor.inspect(source)
            if inspection.decision == "exclude":
                row = RequiredAssetRow(
                    source_path=source,
                    target_path=None,
                    disposition="excluded_with_reason",
                    expected_target_class="excluded",
                    reason=inspection.reason,
                    sha256=inspection.sha256,
                    size=inspection.size,
                    file_type=inspection.file_type,
                )
            elif preliminary_reason is not None:
                row = RequiredAssetRow(
                    source_path=source,
                    target_path=None,
                    disposition="excluded_with_reason",
                    expected_target_class="excluded",
                    reason=preliminary_reason,
                    sha256=inspection.sha256,
                    size=inspection.size,
                    file_type=inspection.file_type,
                )
            elif (archive_decision := _archive_decision(source)) is not None:
                category, archive_reason = archive_decision
                target = _archive_target(source, category)
                row = RequiredAssetRow(
                    source_path=source,
                    target_path=target,
                    disposition="copied_archive",
                    expected_target_class="archive",
                    reason=_copied_reason(source, archive_reason),
                    sha256=inspection.sha256,
                    size=inspection.size,
                    file_type=inspection.file_type,
                )
            else:
                row = RequiredAssetRow(
                    source_path=source,
                    target_path=active_target,
                    disposition="copied_active",
                    expected_target_class="active",
                    reason=_copied_reason(source, "authoritative-active-source"),
                    sha256=inspection.sha256,
                    size=inspection.size,
                    file_type=inspection.file_type,
                )

            if row.target_path is not None:
                prior = copied_targets.get(row.target_path)
                if prior is not None and prior != row.source_path:
                    raise SourceSpecError(
                        f"target collision after routing: {prior!r} and "
                        f"{row.source_path!r} -> {row.target_path!r}"
                    )
                copied_targets[row.target_path] = row.source_path
            rows.append(row)

    result = RequiredAssetInventory(tuple(rows))
    if not result.source_paths_are_unique() or not result.target_paths_are_unique():
        raise SourceSpecError("required-assets inventory is not one-to-one")
    return result
