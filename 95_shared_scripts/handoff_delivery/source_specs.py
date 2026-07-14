"""Authoritative source enumeration and deterministic v2 routing.

This module encodes design section 5.1 as data.  It enumerates every regular
file and symbolic link under the declared roots before applying content or
routing decisions, so exclusions remain auditable rather than silent.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Literal, overload

from .inventory import inspect_candidate
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


def _require_real_directory(path: Path, *, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise SourceSpecError(f"missing {label}: {path}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise SourceSpecError(f"{label} is not a real directory: {path}")


def _require_file_candidate(path: Path, *, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise SourceSpecError(f"missing {label}: {path}") from error
    if not (stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode)):
        raise SourceSpecError(f"{label} is not a file or symlink: {path}")


def _iter_tree_candidates(root: Path) -> Iterator[Path]:
    """Yield all files and links without following directory symlinks."""
    for current_raw, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        current = Path(current_raw)
        directory_names.sort()
        file_names.sort()

        traversable: list[str] = []
        for name in directory_names:
            candidate = current / name
            try:
                metadata = candidate.lstat()
            except OSError as error:
                raise SourceSpecError(
                    f"candidate disappeared during enumeration: {candidate}"
                ) from error
            if stat.S_ISLNK(metadata.st_mode):
                yield candidate
            elif stat.S_ISDIR(metadata.st_mode):
                traversable.append(name)
            else:
                yield candidate
        directory_names[:] = traversable

        for name in file_names:
            candidate = current / name
            try:
                metadata = candidate.lstat()
            except OSError as error:
                raise SourceSpecError(
                    f"candidate disappeared during enumeration: {candidate}"
                ) from error
            if stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                yield candidate
            else:
                yield candidate


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


def _resolve_graphics_reference(thesis_root: Path, reference: str) -> Path | None:
    normalized = reference.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    try:
        relative = require_relative_path(normalized)
    except ManifestError as error:
        raise SourceSpecError(f"unsafe thesis figure reference {reference!r}") from error
    if not relative.parts or relative.parts[0] != "figures":
        return None

    candidate = thesis_root / relative.as_posix()
    if candidate.suffix:
        _require_file_candidate(candidate, label="formal thesis figure")
        return candidate

    matches = tuple(
        path
        for suffix in (".png", ".pdf", ".jpg", ".jpeg", ".svg")
        if (path := candidate.with_suffix(suffix)).is_file()
    )
    if len(matches) != 1:
        raise SourceSpecError(
            f"formal thesis figure reference must resolve uniquely: {reference!r}"
        )
    return matches[0]


def _thesis_asset_targets(project_root: Path) -> dict[str, str]:
    thesis_root = project_root / _THESIS_ROOT.as_posix()
    chapters_root = thesis_root / "chapters"
    figures_root = thesis_root / "figures"
    _require_real_directory(chapters_root, label="formal thesis chapters root")
    _require_real_directory(figures_root, label="formal thesis figures root")

    candidates: set[Path] = set()
    for chapter_name in FORMAL_THESIS_CHAPTERS:
        chapter = chapters_root / chapter_name
        _require_file_candidate(chapter, label="formal thesis chapter")
        try:
            text = chapter.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise SourceSpecError(f"cannot parse formal thesis chapter: {chapter}") from error
        for match in _INCLUDE_GRAPHICS.finditer(_strip_tex_comments(text)):
            resolved = _resolve_graphics_reference(thesis_root, match.group(1))
            if resolved is not None:
                candidates.add(resolved)

    for candidate in sorted(figures_root.iterdir(), key=lambda path: path.name):
        if candidate.suffix.casefold() not in {".py", ".csv"}:
            continue
        _require_file_candidate(candidate, label="thesis figure dependency")
        candidates.add(candidate)

    result: dict[str, str] = {}
    for candidate in sorted(candidates, key=lambda path: path.as_posix()):
        source = candidate.relative_to(project_root).as_posix()
        target = PurePosixPath("05_papers_and_talks/thesis_final/figures") / candidate.name
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
    project_root: Path,
    *,
    tree_specs: Sequence[TreeSourceSpec],
    exact_specs: Sequence[ExactSourceSpec],
    include_thesis_assets: bool,
) -> dict[str, str]:
    candidates: dict[str, str] = {}
    targets: dict[str, str] = {}

    for spec in tree_specs:
        source_root = project_root / spec.source_root
        _require_real_directory(source_root, label=f"source root {spec.source_root}")
        for candidate in _iter_tree_candidates(source_root):
            relative = PurePosixPath(candidate.relative_to(source_root).as_posix())
            _add_candidate(
                candidates,
                targets,
                source=candidate.relative_to(project_root).as_posix(),
                target=_tree_target(spec, relative),
            )

    for spec in exact_specs:
        candidate = project_root / spec.source_path
        _require_file_candidate(candidate, label=f"required source {spec.source_path}")
        _add_candidate(
            candidates,
            targets,
            source=spec.source_path,
            target=spec.target_path,
        )

    if include_thesis_assets:
        for source, target in _thesis_asset_targets(project_root).items():
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


def _obvious_field_exclusion(path: Path) -> tuple[str, int, str] | None:
    """Skip multi-gigabyte hashing only when the field identity is explicit."""
    try:
        metadata = path.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        return None
    name = path.name.casefold()
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
    _require_real_directory(root, label="project root")
    candidate_targets = _collect_candidate_targets(
        root,
        tree_specs=tuple(tree_specs),
        exact_specs=tuple(exact_specs),
        include_thesis_assets=include_thesis_assets,
    )

    rows: list[RequiredAssetRow] = []
    copied_targets: dict[str, str] = {}
    for source, active_target in sorted(candidate_targets.items()):
        candidate = root / source
        obvious_field = _obvious_field_exclusion(candidate)
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

        inspection = inspect_candidate(candidate)
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
