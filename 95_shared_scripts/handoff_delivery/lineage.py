"""Figure provenance contracts and canonical figure-set discovery.

The recipe ledger deliberately records source-project paths.  Package routing is a
separate decision, so a formally used but superseded figure cannot disappear by
being relabelled as an archive-only asset.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import csv
from dataclasses import dataclass, field, fields
import hashlib
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType

from .models import (
    IdList,
    ManifestError,
    require_columns,
    require_foreign_keys,
    require_relative_path,
    require_unique_key,
)
from .source_specs import AnchoredRoot


FORMAL_CHAPTERS = (
    "ch01-intro.tex",
    "ch02-theory.tex",
    "ch03-construction.tex",
    "ch04-stability.tex",
    "ch05-dynamics.tex",
    "ch06-neuromorphic.tex",
    "ch07-conclusion.tex",
)

USAGE_STATUSES = frozenset({"formal", "current_only", "archive_only"})
SCIENTIFIC_STATUSES = frozenset(
    {"valid", "superseded", "failed", "unverified", "not_applicable"}
)
PROVENANCE_TYPES = frozenset({"simulation", "theory", "schematic", "external"})
STORY_MODULES = (
    "01_stability",
    "02_spinwave_control",
    "03_mechanism_and_theory",
    "04_lif_device",
    "05_papers_and_talks",
)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
INCLUDEGRAPHICS_PATTERN = re.compile(
    r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}",
    re.MULTILINE,
)
MARKDOWN_CODE_SPAN_PATTERN = re.compile(r"`([^`\n]+)`")
SOURCE_LOCATOR_PLACEHOLDER_PATTERN = re.compile(
    r"(?:^|[^a-z0-9])(?:unresolved|unverified|unknown|tbd|n/?a)(?:$|[^a-z0-9])",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class CurrentResultReference:
    """One result directory directly named by a canonical status document."""

    result_root: str
    evidence_document: str
    evidence_literal: str

    def __post_init__(self) -> None:
        require_relative_path(self.result_root)
        if not self.evidence_document:
            raise ManifestError("current-result evidence_document must not be empty")
        if not self.evidence_literal:
            raise ManifestError("current-result evidence_literal must not be empty")


CURRENT_RESULT_REFERENCES = (
    CurrentResultReference(
        result_root=(
            "06_eigenmode_frequency_mechanism/"
            "skyrmion_hopfion_eigenfrequency_link_20260608"
        ),
        evidence_document=(
            "/mnt/d/Obsidian/20-Research/Hopfion-Physics/progress.md"
        ),
        evidence_literal=(
            "/mnt/d/Research/Hopfion/06_eigenmode_frequency_mechanism/"
            "skyrmion_hopfion_eigenfrequency_link_20260608/"
        ),
    ),
    CurrentResultReference(
        result_root=(
            "06_eigenmode_frequency_mechanism/"
            "hopfion_energy_absorption_audit_20260608"
        ),
        evidence_document=(
            "/mnt/d/Obsidian/20-Research/Hopfion-Physics/progress.md"
        ),
        evidence_literal=(
            "/mnt/d/Research/Hopfion/06_eigenmode_frequency_mechanism/"
            "hopfion_energy_absorption_audit_20260608/"
        ),
    ),
    CurrentResultReference(
        result_root=(
            "06_eigenmode_frequency_mechanism/hopfion_mode_map_20260608"
        ),
        evidence_document=(
            "/mnt/d/Obsidian/20-Research/Hopfion-Physics/progress.md"
        ),
        evidence_literal=(
            "/mnt/d/Research/Hopfion/06_eigenmode_frequency_mechanism/"
            "hopfion_mode_map_20260608/"
        ),
    ),
    CurrentResultReference(
        result_root=(
            "06_eigenmode_frequency_mechanism/"
            "hopfion_eigenmode_ringdown_20260608"
        ),
        evidence_document=(
            "/mnt/d/Obsidian/20-Research/Hopfion-Physics/progress.md"
        ),
        evidence_literal=(
            "/mnt/d/Research/Hopfion/06_eigenmode_frequency_mechanism/"
            "hopfion_eigenmode_ringdown_20260608/"
        ),
    ),
    CurrentResultReference(
        result_root="hopfion_eigenmode_mechanism_20260612",
        evidence_document=(
            "/mnt/d/Obsidian/20-Research/Hopfion-Physics/progress.md"
        ),
        evidence_literal=(
            "/mnt/d/Research/Hopfion/hopfion_eigenmode_mechanism_20260612/"
        ),
    ),
    CurrentResultReference(
        result_root=(
            "07_thiele_theory_model/results_thiele_GD_translation_20260615"
        ),
        evidence_document=(
            "00_project_index/hopfion_spinwave_paper_master_plan_20260703.md"
        ),
        evidence_literal=(
            "results_thiele_GD_translation_20260615/G_D_translation.json"
        ),
    ),
    CurrentResultReference(
        result_root=(
            "07_thiele_theory_model/results_thiele_GD_convergence_20260703"
        ),
        evidence_document=(
            "00_project_index/hopfion_spinwave_paper_master_plan_20260703.md"
        ),
        evidence_literal=(
            "07_thiele_theory_model/results_thiele_GD_convergence_20260703/"
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class FigureRecipe:
    figure_id: str
    usage_status: str
    scientific_status: str
    provenance_type: str
    story_module: str
    claim_or_purpose: str
    figure_path: str
    figure_sha256: str
    plot_script_path: str
    plot_command: str
    input_data_ids: str
    parent_data_ids: str
    derived_data_ids: str
    run_ids: str
    theory_asset_ids: str
    initial_state_recipe_id: str
    reproducibility: str
    source_document_ids: str
    comparison_method: str
    tolerance: str
    notes: str
    comparison_reference_data_id: str

    def __post_init__(self) -> None:
        if not self.figure_id or any(character.isspace() for character in self.figure_id):
            raise ManifestError("figure_id must be a non-empty ID without whitespace")
        if ";" in self.figure_id:
            raise ManifestError("figure_id must not contain semicolons")
        if self.usage_status not in USAGE_STATUSES:
            raise ManifestError(f"invalid usage_status: {self.usage_status!r}")
        if self.scientific_status not in SCIENTIFIC_STATUSES:
            raise ManifestError(
                f"invalid scientific_status: {self.scientific_status!r}"
            )
        if self.provenance_type not in PROVENANCE_TYPES:
            raise ManifestError(f"invalid provenance_type: {self.provenance_type!r}")
        if self.story_module not in STORY_MODULES:
            raise ManifestError(f"invalid story_module: {self.story_module!r}")
        if not self.claim_or_purpose:
            raise ManifestError("claim_or_purpose must not be empty")
        require_relative_path(self.figure_path)
        if not SHA256_PATTERN.fullmatch(self.figure_sha256):
            raise ManifestError("figure_sha256 must be a lowercase SHA256 digest")
        if self.plot_script_path != "N/A":
            require_relative_path(self.plot_script_path)
        input_ids = (
            frozenset()
            if self.input_data_ids == "N/A"
            else frozenset(IdList.parse(self.input_data_ids).items)
        )
        if self.derived_data_ids == "N/A":
            derived_ids = frozenset()
        else:
            derived_ids = frozenset(IdList.parse(self.derived_data_ids).items)
            if not derived_ids <= input_ids:
                raise ManifestError(
                    "derived_data_ids must be a subset of input_data_ids"
                )
        requires_derivation = (
            "deriv" in self.reproducibility and "pending" in self.reproducibility
        )
        if requires_derivation != bool(derived_ids):
            raise ManifestError(
                "pending derivation status and derived_data_ids must agree"
            )
        if not self.reproducibility:
            raise ManifestError("reproducibility must not be empty")
        if not self.notes:
            raise ManifestError("notes must not be empty")
        if self.comparison_reference_data_id != "N/A":
            reference_ids = IdList.parse(self.comparison_reference_data_id).items
            if len(reference_ids) != 1:
                raise ManifestError(
                    "comparison_reference_data_id must contain exactly one data ID"
                )
        if self.scientific_status == "not_applicable" and self.provenance_type not in {
            "schematic",
            "external",
        }:
            raise ManifestError(
                "scientific_status=not_applicable is limited to schematic/external figures"
            )


@dataclass(frozen=True, slots=True)
class ManifestKeys:
    """Known foreign-key targets used for figure-closure validation."""

    data_ids: frozenset[str] = frozenset()
    run_ids: frozenset[str] = frozenset()
    theory_asset_ids: frozenset[str] = frozenset()
    initial_state_recipe_ids: frozenset[str] = frozenset()
    document_ids: frozenset[str] = frozenset()
    data_paths: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        paths = dict(self.data_paths)
        if not set(paths) <= set(self.data_ids):
            raise ManifestError("data_paths keys must exist in data_ids")
        for path in paths.values():
            require_relative_path(path)
        if len(paths.values()) != len(set(paths.values())):
            raise ManifestError("data_paths values must be unique")
        object.__setattr__(self, "data_paths", MappingProxyType(paths))


def _strip_tex_comment(line: str) -> str:
    escaped = False
    for index, character in enumerate(line):
        if character == "%" and not escaped:
            return line[:index]
        if character == "\\":
            escaped = not escaped
        else:
            escaped = False
    return line


def discover_thesis_figures(chapters_dir: Path | str) -> tuple[str, ...]:
    """Discover figures from only the seven canonical thesis chapter files."""
    root = Path(chapters_dir)
    discovered: list[str] = []
    seen: set[str] = set()
    for chapter_name in FORMAL_CHAPTERS:
        chapter = root / chapter_name
        if not chapter.is_file():
            continue
        uncommented = "\n".join(
            _strip_tex_comment(line) for line in chapter.read_text(encoding="utf-8").splitlines()
        )
        for match in INCLUDEGRAPHICS_PATTERN.finditer(uncommented):
            raw = match.group(1).strip()
            path = require_relative_path(raw).as_posix()
            if path not in seen:
                seen.add(path)
                discovered.append(path)
    return tuple(discovered)


def _require_real_directory_beneath(root: Path, relative: str) -> Path:
    current = root
    for part in require_relative_path(relative).parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as error:
            raise ManifestError(f"missing canonical result root: {relative}") from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ManifestError(
                f"canonical result root is not a real directory: {relative}"
            )
    return current


def discover_current_mainline_figures(
    project_root: Path | str,
    *,
    references: Iterable[CurrentResultReference] = CURRENT_RESULT_REFERENCES,
) -> tuple[str, ...]:
    """Discover images only below result roots directly named in canonical docs."""
    project = Path(project_root).resolve()
    discovered: set[str] = set()
    for reference in references:
        evidence_path = Path(reference.evidence_document)
        if not evidence_path.is_absolute():
            evidence_path = project / evidence_path
        try:
            metadata = evidence_path.lstat()
            document = evidence_path.read_text(encoding="utf-8")
        except OSError as error:
            raise ManifestError(
                f"cannot read current-result evidence document: {evidence_path}"
            ) from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ManifestError(
                f"current-result evidence is not a regular file: {evidence_path}"
            )
        code_spans = {match.group(1) for match in MARKDOWN_CODE_SPAN_PATTERN.finditer(document)}
        if reference.evidence_literal not in code_spans:
            raise ManifestError(
                f"canonical result root is not directly named in {evidence_path}: "
                f"{reference.evidence_literal}"
            )
        result_root = _require_real_directory_beneath(
            project, reference.result_root
        )
        for path in result_root.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            suffix = path.suffix.casefold()
            if suffix in {".png", ".svg"} or (
                suffix == ".pdf" and "figures" in path.relative_to(result_root).parts
            ):
                discovered.add(path.relative_to(project).as_posix())
    return tuple(sorted(discovered))


def _parse_ids(raw: str, *, field_name: str, required: bool) -> tuple[str, ...]:
    if raw == "N/A":
        if required:
            raise ManifestError(f"{field_name} must not be N/A")
        return ()
    try:
        return IdList.parse(raw).items
    except ManifestError as error:
        raise ManifestError(f"{field_name}: {error}") from error


def _require_na(row: FigureRecipe, *field_names: str) -> None:
    for field_name in field_names:
        if getattr(row, field_name) != "N/A":
            raise ManifestError(
                f"{row.figure_id}: {field_name} must be N/A for {row.provenance_type}"
            )


def _require_text(row: FigureRecipe, *field_names: str) -> None:
    for field_name in field_names:
        if getattr(row, field_name) in {"", "N/A"}:
            raise ManifestError(f"{row.figure_id}: {field_name} must be declared")


def _validate_fk_field(
    row: FigureRecipe,
    field_name: str,
    valid: Iterable[str],
    *,
    required: bool,
) -> tuple[str, ...]:
    values = _parse_ids(getattr(row, field_name), field_name=field_name, required=required)
    try:
        require_foreign_keys(values, valid, context=f"{row.figure_id}:{field_name}")
    except ManifestError as error:
        raise ManifestError(f"{field_name}: {error}") from error
    return values


def _validate_external_source_locator(row: FigureRecipe) -> None:
    note_fields = {
        key.strip(): value.strip()
        for token in row.notes.split(";")
        if "=" in token
        for key, value in (token.split("=", 1),)
    }
    locator = note_fields.get("source_locator", "")
    candidate_values = [locator]
    if "original_external_source" in note_fields:
        candidate_values.append(note_fields["original_external_source"])
    if (
        not locator
        or "doc-thesis" in locator.casefold()
        or any(
            not value or SOURCE_LOCATOR_PLACEHOLDER_PATTERN.search(value)
            for value in candidate_values
        )
    ):
        raise ManifestError(
            f"{row.figure_id}: external figure requires an exact original source "
            "locator (source_locator)"
        )


def validate_figure_closure(row: FigureRecipe, manifests: ManifestKeys) -> None:
    """Validate one row using its provenance-specific closure matrix."""
    strict_numeric = (
        row.usage_status in {"formal", "current_only"}
        and row.scientific_status == "valid"
        and row.provenance_type in {"simulation", "theory"}
    )

    if row.provenance_type == "simulation":
        if strict_numeric:
            _require_text(
                row,
                "plot_script_path",
                "plot_command",
                "comparison_method",
                "tolerance",
            )
            _validate_fk_field(row, "input_data_ids", manifests.data_ids, required=True)
            _validate_fk_field(row, "parent_data_ids", manifests.data_ids, required=True)
            _validate_fk_field(row, "run_ids", manifests.run_ids, required=True)
            _validate_fk_field(
                row,
                "comparison_reference_data_id",
                manifests.data_ids,
                required=True,
            )
            _require_text(row, "initial_state_recipe_id")
            require_foreign_keys(
                (row.initial_state_recipe_id,),
                manifests.initial_state_recipe_ids,
                context=f"{row.figure_id}:initial_state_recipe_id",
            )
        else:
            _validate_fk_field(row, "input_data_ids", manifests.data_ids, required=False)
            _validate_fk_field(row, "parent_data_ids", manifests.data_ids, required=False)
            _validate_fk_field(row, "run_ids", manifests.run_ids, required=False)
            _validate_fk_field(
                row,
                "comparison_reference_data_id",
                manifests.data_ids,
                required=False,
            )
            if row.initial_state_recipe_id != "N/A":
                require_foreign_keys(
                    (row.initial_state_recipe_id,),
                    manifests.initial_state_recipe_ids,
                    context=f"{row.figure_id}:initial_state_recipe_id",
                )
        _validate_fk_field(
            row, "theory_asset_ids", manifests.theory_asset_ids, required=False
        )

    elif row.provenance_type == "theory":
        _require_na(row, "run_ids", "initial_state_recipe_id")
        if strict_numeric:
            _require_text(
                row,
                "plot_script_path",
                "plot_command",
                "comparison_method",
                "tolerance",
            )
            _validate_fk_field(row, "input_data_ids", manifests.data_ids, required=True)
            _validate_fk_field(row, "parent_data_ids", manifests.data_ids, required=True)
            _validate_fk_field(
                row, "theory_asset_ids", manifests.theory_asset_ids, required=True
            )
            _validate_fk_field(
                row,
                "comparison_reference_data_id",
                manifests.data_ids,
                required=True,
            )
        else:
            _validate_fk_field(row, "input_data_ids", manifests.data_ids, required=False)
            _validate_fk_field(row, "parent_data_ids", manifests.data_ids, required=False)
            _validate_fk_field(
                row, "theory_asset_ids", manifests.theory_asset_ids, required=False
            )
            _validate_fk_field(
                row,
                "comparison_reference_data_id",
                manifests.data_ids,
                required=False,
            )

    elif row.provenance_type == "schematic":
        _require_na(
            row,
            "input_data_ids",
            "parent_data_ids",
            "run_ids",
            "initial_state_recipe_id",
            "comparison_reference_data_id",
        )
        editable_ids = _validate_fk_field(
            row, "theory_asset_ids", manifests.theory_asset_ids, required=False
        )
        has_generator = row.plot_script_path != "N/A" and row.plot_command != "N/A"
        if not editable_ids and not has_generator:
            raise ManifestError(
                f"{row.figure_id}: schematic requires an editable source or generator"
            )

    else:  # external
        _require_na(
            row,
            "plot_script_path",
            "plot_command",
            "input_data_ids",
            "parent_data_ids",
            "run_ids",
            "theory_asset_ids",
            "initial_state_recipe_id",
            "comparison_reference_data_id",
        )
        _validate_fk_field(
            row, "source_document_ids", manifests.document_ids, required=True
        )
        _validate_external_source_locator(row)

    if row.provenance_type != "external":
        _validate_fk_field(
            row, "source_document_ids", manifests.document_ids, required=False
        )


def route_figure(row: FigureRecipe) -> str:
    """Return the package class without mutating canonical usage status."""
    if row.scientific_status in {"superseded", "failed"}:
        return "90_archive/superseded_figures"
    if row.usage_status == "archive_only" or row.scientific_status == "unverified":
        return "90_archive/historical_figures"
    return "active"


def validate_recipe_membership(
    rows: Iterable[FigureRecipe],
    *,
    formal_paths: Iterable[str],
    current_paths: Iterable[str],
) -> None:
    """Require exact canonical formal/current membership, independent of science status."""
    row_tuple = tuple(rows)
    formal_expected = frozenset(formal_paths)
    current_expected = frozenset(current_paths) - formal_expected
    formal_actual = frozenset(
        row.figure_path for row in row_tuple if row.usage_status == "formal"
    )
    current_actual = frozenset(
        row.figure_path for row in row_tuple if row.usage_status == "current_only"
    )
    if formal_actual != formal_expected:
        missing = sorted(formal_expected - formal_actual)
        extra = sorted(formal_actual - formal_expected)
        raise ManifestError(
            f"formal membership mismatch; missing={missing!r}; extra={extra!r}"
        )
    if current_actual != current_expected:
        missing = sorted(current_expected - current_actual)
        extra = sorted(current_actual - current_expected)
        raise ManifestError(
            f"current membership mismatch; missing={missing!r}; extra={extra!r}"
        )


def discover_independent_figures(
    delivery_root: Path | str,
    *,
    explicitly_marked_pdfs: Iterable[str] = (),
) -> tuple[str, ...]:
    """Discover independent image assets, excluding document containers."""
    root = Path(delivery_root)
    marked = frozenset(
        require_relative_path(path).as_posix() for path in explicitly_marked_pdfs
    )
    discovered: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        suffix = path.suffix.casefold()
        if suffix in {".png", ".svg"}:
            discovered.append(relative)
        elif suffix == ".pdf" and (
            relative in marked or "figures" in Path(relative).parts
        ):
            discovered.append(relative)
    return tuple(sorted(discovered))


def validate_figure_coverage(
    discovered_paths: Iterable[str], rows: Iterable[FigureRecipe]
) -> None:
    """Require one and only one ledger row per independently discovered figure."""
    row_tuple = tuple(rows)
    by_path: dict[str, list[str]] = {}
    for row in row_tuple:
        by_path.setdefault(row.figure_path, []).append(row.figure_id)
    duplicates = sorted(path for path, ids in by_path.items() if len(ids) != 1)
    if duplicates:
        raise ManifestError(f"duplicate figure_path rows: {duplicates!r}")
    discovered = frozenset(discovered_paths)
    registered = frozenset(by_path)
    missing = sorted(discovered - registered)
    extra = sorted(registered - discovered)
    if missing:
        raise ManifestError(f"missing figure rows: {missing!r}")
    if extra:
        raise ManifestError(f"figure rows without packaged assets: {extra!r}")


def load_figure_recipes(path: Path | str) -> tuple[FigureRecipe, ...]:
    """Load the versioned CSV ledger without normalising or guessing values."""
    ledger = Path(path)
    with ledger.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ManifestError("figure recipe ledger has no header")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            duplicates = sorted(
                name
                for name in set(reader.fieldnames)
                if reader.fieldnames.count(name) > 1
            )
            raise ManifestError(
                f"{ledger}: duplicate CSV header names: {duplicates!r}"
            )
        required = tuple(field.name for field in fields(FigureRecipe))
        require_columns(reader.fieldnames, required, context=str(ledger))
        parsed: list[FigureRecipe] = []
        for line_number, row in enumerate(reader, start=2):
            if row.get(None):
                raise ManifestError(
                    f"{ledger}:{line_number}: unexpected extra columns; "
                    "quote fields containing commas"
                )
            missing_values = tuple(name for name in required if row.get(name) is None)
            if missing_values:
                raise ManifestError(
                    f"{ledger}:{line_number}: missing CSV values for {missing_values!r}"
                )
            parsed.append(FigureRecipe(**{name: row[name] for name in required}))
        rows = tuple(parsed)
    require_unique_key(
        ({"figure_id": row.figure_id} for row in rows),
        "figure_id",
        context=str(ledger),
    )
    return rows


def _sha256_descriptor(descriptor: int) -> str:
    digest = hashlib.sha256()
    try:
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
    except OSError as error:
        raise ManifestError("cannot hash anchored figure source") from error
    return digest.hexdigest()


def validate_recipe_ledger(project_root: Path | str) -> tuple[FigureRecipe, ...]:
    """Statically validate source paths, hashes, axes and canonical formal rows.

    Full foreign-key closure is intentionally performed once the build has emitted
    DATA/RUN/DOCUMENT/INITIAL_STATE manifests.  This static pass never invents
    missing IDs merely to make a source ledger appear complete.
    """
    project = Path(project_root).resolve()
    ledger = project / "95_shared_scripts/handoff_delivery/figure_recipes.csv"
    rows = load_figure_recipes(ledger)
    with AnchoredRoot(project, error_type=ManifestError) as anchor:
        for row in rows:
            figure_descriptor = anchor.open_regular(row.figure_path)
            try:
                figure_sha256 = _sha256_descriptor(figure_descriptor)
            finally:
                os.close(figure_descriptor)
            if figure_sha256 != row.figure_sha256:
                raise ManifestError(
                    f"figure source SHA256 mismatch: {row.figure_path}"
                )
            if row.plot_script_path != "N/A":
                script_descriptor = anchor.open_regular(row.plot_script_path)
                os.close(script_descriptor)
            if (
                row.scientific_status in {"superseded", "failed"}
                and route_figure(row) == "active"
            ):
                raise ManifestError(f"unsafe active routing for {row.figure_id}")
            if row.provenance_type == "external":
                _validate_external_source_locator(row)

    chapters = project / "09_paper_thesis_talks/bishe/thesis_v2/chapters"
    thesis_root = "09_paper_thesis_talks/bishe/thesis_v2"
    formal = {
        f"{thesis_root}/{path}" for path in discover_thesis_figures(chapters)
    }
    current = set(discover_current_mainline_figures(project))
    validate_recipe_membership(
        rows,
        formal_paths=formal,
        current_paths=current,
    )
    return rows
