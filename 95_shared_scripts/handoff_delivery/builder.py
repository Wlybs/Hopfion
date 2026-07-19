"""Non-destructive construction primitives for the Hopfion v2 handoff tree."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
import hashlib
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
import stat
import tempfile
from typing import Literal

from .docs import (
    DocsConfig,
    load_docs_config,
    package_verifier_assets,
    render_documents,
)
from .derived import (
    DerivedDataError,
    DerivedRecipe,
    produce_derived,
    produce_derived_in_environment,
    validate_derived_outputs,
    validate_derived_preflight,
    write_derived_evidence,
)
from .lineage import (
    FigureRecipe,
    ManifestKeys,
    route_figure,
    validate_figure_closure,
    validate_figure_coverage,
    validate_recipe_ledger,
)
from .models import IdList, ManifestError, require_relative_path
from .portable import (
    PORTABLE_OUTPUT_PATHS,
    _PinnedDeliveryScan,
    _PinnedPortableMaterialization,
    _PinnedTreeEntry,
    _snapshot_delivery_descriptor,
    PortableContract,
    PortableError,
    assemble_portable_contract,
    bind_initial_state_recipes_to_package,
    discover_full_field_consumers,
    load_field_consumer_registry,
    load_initial_state_recipes,
    materialize_portable_contract,
    scan_delivery_absolute_paths,
    validate_field_consumer_registry,
    validate_portable_contract,
)
from .redraw import (
    RedrawError,
    RedrawRecipe,
    execute_redraws,
    validate_redraw_plan,
)
from .source_specs import (
    AnchoredRoot,
    EXACT_SOURCE_SPECS,
    TREE_SOURCE_SPECS,
    ExactSourceSpec,
    RequiredAssetInventory,
    RequiredAssetRow,
    TreeSourceSpec,
    enumerate_required_assets,
)
from .verifier import (
    _checksum_payload,
    _report_payload,
    VerificationError,
    exit_code as verification_exit_code,
    package_figure_recipes,
    verify,
    write_checksums,
    write_report,
)


class BaselineError(RuntimeError):
    """Raised when the old delivery cannot be snapshotted safely."""


class BuildRefusedError(RuntimeError):
    """Raised before writing when a destination is unsafe or ambiguous."""


class _PublicationFailure(BuildRefusedError):
    """Carries recoverable state when a destination swap cannot complete."""

    def __init__(
        self,
        message: str,
        *,
        backup: Path | None,
        displaced_snapshot: DestinationSnapshot | None,
        recovery_status: str,
        recovery_paths: tuple[str, ...],
    ) -> None:
        super().__init__(message)
        self.backup = backup
        self.displaced_snapshot = displaced_snapshot
        self.recovery_status = recovery_status
        self.recovery_paths = recovery_paths


@dataclass(frozen=True, slots=True)
class BaselineEntry:
    relative_path: str
    path_type: Literal["file", "directory", "symlink", "other"]
    size: int
    sha256: str
    symlink_target: str


@dataclass(frozen=True, slots=True)
class BaselineSnapshot:
    entries: tuple[BaselineEntry, ...]


@dataclass(frozen=True, slots=True)
class DestinationSnapshot:
    existed: bool
    root_identity: tuple[int, int, int, int, int] | None
    entries: tuple[BaselineEntry, ...]


@dataclass(frozen=True, slots=True)
class BaselineDifference:
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    changed: tuple[str, ...] = ()
    type_changed: tuple[str, ...] = ()
    symlink_retargeted: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def is_clean(self) -> bool:
        return not any(
            (
                self.added,
                self.removed,
                self.changed,
                self.type_changed,
                self.symlink_retargeted,
                self.errors,
            )
        )


@dataclass(frozen=True, slots=True)
class BuildPlan:
    project_root: Path
    old_delivery: Path
    destination: Path
    required_assets: RequiredAssetInventory
    old_baseline: BaselineSnapshot
    figure_recipes: tuple[FigureRecipe, ...] = ()
    manifest_keys: ManifestKeys | None = None
    derived_recipes: tuple[DerivedRecipe, ...] = ()
    redraw_recipes: tuple[RedrawRecipe, ...] = ()
    portable_contract: PortableContract | None = None
    docs_config: DocsConfig | None = None
    tree_specs: tuple[TreeSourceSpec, ...] = TREE_SOURCE_SPECS
    exact_specs: tuple[ExactSourceSpec, ...] = EXACT_SOURCE_SPECS
    include_thesis_assets: bool = True


@dataclass(frozen=True, slots=True)
class BuildResult:
    exit_code: int
    publishable: bool
    dry_run: bool
    reason: str
    required_rows: tuple[RequiredAssetRow, ...]
    source_rows: tuple[RequiredAssetRow, ...]
    exclusion_rows: tuple[RequiredAssetRow, ...]
    baseline_difference: BaselineDifference
    written_paths: tuple[str, ...] = ()
    recovery_status: str = "not-needed"
    recovery_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _RecoveryOutcome:
    status: str
    paths: tuple[str, ...]


@dataclass(slots=True)
class _VerifiedStagingHandle:
    descriptor: int
    identity: tuple[int, int, int, int, int]
    snapshot: tuple[_PinnedTreeEntry, ...]

    def close(self) -> None:
        if self.descriptor >= 0:
            descriptor = self.descriptor
            self.descriptor = -1
            os.close(descriptor)


def _same_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
    )


def _hash_regular_no_follow(path: Path, metadata: os.stat_result) -> str:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if not no_follow:
        raise BaselineError("O_NOFOLLOW is required for an old-package baseline")
    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0),
        )
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or not _same_snapshot(metadata, opened):
            raise BaselineError(f"old-package path changed while opening: {path}")
        digest = hashlib.sha256()
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
            final_descriptor = os.fstat(handle.fileno())
        final_path = path.lstat()
        if not (
            _same_snapshot(metadata, opened)
            and _same_snapshot(opened, final_descriptor)
            and _same_snapshot(final_descriptor, final_path)
        ):
            raise BaselineError(f"old-package path changed while hashing: {path}")
        return digest.hexdigest()
    except OSError as error:
        raise BaselineError(f"cannot hash old-package path: {path}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _baseline_entry(path: Path, root: Path) -> BaselineEntry:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise BaselineError(f"cannot stat old-package path: {path}") from error
    relative = path.relative_to(root).as_posix()
    if stat.S_ISREG(metadata.st_mode):
        return BaselineEntry(
            relative_path=relative,
            path_type="file",
            size=metadata.st_size,
            sha256=_hash_regular_no_follow(path, metadata),
            symlink_target="",
        )
    if stat.S_ISDIR(metadata.st_mode):
        return BaselineEntry(relative, "directory", metadata.st_size, "", "")
    if stat.S_ISLNK(metadata.st_mode):
        try:
            target = os.readlink(path)
        except OSError as error:
            raise BaselineError(f"cannot read old-package symlink: {path}") from error
        digest = hashlib.sha256(b"symlink\0" + os.fsencode(target)).hexdigest()
        return BaselineEntry(relative, "symlink", metadata.st_size, digest, target)
    return BaselineEntry(relative, "other", metadata.st_size, "", "")


def _require_old_delivery_root(root: Path) -> None:
    try:
        metadata = root.lstat()
    except OSError as error:
        raise BaselineError(f"old delivery does not exist: {root}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise BaselineError(f"old delivery is not a real directory: {root}")


def _raise_baseline_walk_error(error: OSError) -> None:
    location = getattr(error, "filename", None) or "unknown path"
    raise BaselineError(
        f"cannot enumerate old delivery at {location}: {error}"
    ) from error


def capture_baseline(old_delivery: Path | str) -> BaselineSnapshot:
    """Capture every old-package path without following symbolic links."""
    root = Path(old_delivery)
    _require_old_delivery_root(root)
    entries: list[BaselineEntry] = []
    for current_raw, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
        onerror=_raise_baseline_walk_error,
    ):
        current = Path(current_raw)
        directory_names.sort()
        file_names.sort()
        traversable: list[str] = []
        for name in directory_names:
            path = current / name
            entry = _baseline_entry(path, root)
            entries.append(entry)
            if entry.path_type == "directory":
                traversable.append(name)
        directory_names[:] = traversable
        for name in file_names:
            entries.append(_baseline_entry(current / name, root))
    return BaselineSnapshot(tuple(sorted(entries, key=lambda item: item.relative_path)))


def compare_baseline(
    old_delivery: Path | str, baseline: BaselineSnapshot
) -> BaselineDifference:
    """Return all material differences from a previously captured baseline."""
    current = capture_baseline(old_delivery)
    expected_by_path = {entry.relative_path: entry for entry in baseline.entries}
    current_by_path = {entry.relative_path: entry for entry in current.entries}
    expected_paths = set(expected_by_path)
    current_paths = set(current_by_path)

    changed: list[str] = []
    type_changed: list[str] = []
    symlink_retargeted: list[str] = []
    for path in sorted(expected_paths & current_paths):
        expected = expected_by_path[path]
        actual = current_by_path[path]
        if expected.path_type != actual.path_type:
            type_changed.append(path)
        elif expected.path_type == "symlink" and (
            expected.symlink_target != actual.symlink_target
        ):
            symlink_retargeted.append(path)
        elif expected.size != actual.size or expected.sha256 != actual.sha256:
            changed.append(path)

    return BaselineDifference(
        added=tuple(sorted(current_paths - expected_paths)),
        removed=tuple(sorted(expected_paths - current_paths)),
        changed=tuple(changed),
        type_changed=tuple(type_changed),
        symlink_retargeted=tuple(symlink_retargeted),
    )


def _row_groups(
    inventory: RequiredAssetInventory,
) -> tuple[tuple[RequiredAssetRow, ...], tuple[RequiredAssetRow, ...]]:
    sources = tuple(
        row for row in inventory if row.disposition != "excluded_with_reason"
    )
    exclusions = tuple(
        row for row in inventory if row.disposition == "excluded_with_reason"
    )
    return sources, exclusions


def _load_project_figure_recipes(project_root: Path) -> tuple[FigureRecipe, ...]:
    """Load the canonical ledger when present; never infer a substitute ledger."""
    ledger = project_root / "95_shared_scripts/handoff_delivery/figure_recipes.csv"
    try:
        metadata = ledger.lstat()
    except FileNotFoundError:
        raise BuildRefusedError(
            f"required figure recipe ledger is missing: {ledger}"
        )
    except OSError as error:
        raise BuildRefusedError(f"cannot inspect figure recipe ledger: {ledger}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise BuildRefusedError(
            f"figure recipe ledger must be one real regular file: {ledger}"
        )
    try:
        return validate_recipe_ledger(project_root)
    except (ManifestError, OSError) as error:
        raise BuildRefusedError(f"figure recipe ledger failed: {error}") from error


def _is_independent_figure_path(
    raw: str,
    *,
    registered_paths: set[str] | frozenset[str],
) -> bool:
    path = PurePosixPath(raw)
    suffix = path.suffix.casefold()
    if suffix in {".png", ".svg"}:
        return True
    return suffix == ".pdf" and (
        "figures" in path.parts or raw in registered_paths
    )


def _route_figure_assets(
    inventory: RequiredAssetInventory,
    figure_rows: Sequence[FigureRecipe],
) -> RequiredAssetInventory:
    """Apply scientific-status routing to the already enumerated source assets."""
    if not figure_rows:
        return inventory
    if not inventory.source_paths_are_unique():
        raise BuildRefusedError("required-asset source paths must be unique")

    row_index = {row.source_path: index for index, row in enumerate(inventory.rows)}
    routed = list(inventory.rows)
    registered_paths = {figure.figure_path for figure in figure_rows}
    for index, asset in enumerate(routed):
        is_independent_figure = _is_independent_figure_path(
            asset.source_path,
            registered_paths=registered_paths,
        )
        if is_independent_figure and asset.source_path not in registered_paths:
            routed[index] = replace(
                asset,
                target_path=None,
                disposition="excluded_with_reason",
                expected_target_class="excluded",
                reason="unregistered-noncanonical-figure",
            )
    for figure in figure_rows:
        index = row_index.get(figure.figure_path)
        if index is None:
            raise BuildRefusedError(
                f"figure ledger asset is absent from required inventory: {figure.figure_path}"
            )
        asset = routed[index]
        destination_class = route_figure(figure)
        if destination_class == "active":
            if (
                asset.disposition != "copied_active"
                or asset.expected_target_class != "active"
                or asset.target_path is None
            ):
                raise BuildRefusedError(
                    f"active figure is not routed to an active target: {figure.figure_id}"
                )
            continue
        if asset.disposition == "excluded_with_reason":
            raise BuildRefusedError(
                f"non-active figure cannot be excluded from the handoff: {figure.figure_id}"
            )
        routed[index] = replace(
            asset,
            target_path=(
                f"{destination_class}/{figure.figure_id}/"
                f"{Path(figure.figure_path).name}"
            ),
            disposition="copied_archive",
            expected_target_class="archive",
            reason=f"figure-{figure.scientific_status}-archive",
        )

    result = RequiredAssetInventory(tuple(routed))
    if not result.source_paths_are_unique():
        raise BuildRefusedError("routed required-asset source paths must be unique")
    if not result.target_paths_are_unique():
        raise BuildRefusedError("figure routing creates duplicate package targets")
    packaged_figure_sources = {
        row.source_path
        for row in result
        if row.target_path is not None
        and _is_independent_figure_path(
            row.source_path,
            registered_paths=registered_paths,
        )
    }
    try:
        validate_figure_coverage(packaged_figure_sources, figure_rows)
    except ManifestError as error:
        raise BuildRefusedError(f"packaged figure coverage failed: {error}") from error
    return result


def _validate_canonical_figure_plan(plan: BuildPlan) -> None:
    """Bind every executable plan to the current canonical source ledger."""
    canonical = _load_project_figure_recipes(plan.project_root)
    if plan.figure_recipes != canonical:
        raise BuildRefusedError(
            "build plan figure recipes do not match the canonical source ledger"
        )


def _validate_lineage_preflight(plan: BuildPlan) -> None:
    """Resolve one immutable producer/redraw set before any destination write."""
    registered_paths = {figure.figure_path for figure in plan.figure_recipes}
    packaged_figure_sources = {
        row.source_path
        for row in plan.required_assets
        if row.target_path is not None
        and _is_independent_figure_path(
            row.source_path,
            registered_paths=registered_paths,
        )
    }
    try:
        validate_figure_coverage(packaged_figure_sources, plan.figure_recipes)
    except ManifestError as error:
        raise BuildRefusedError(f"packaged figure coverage failed: {error}") from error

    try:
        validate_derived_preflight(
            list(plan.derived_recipes), project_root=plan.project_root
        )
    except DerivedDataError as error:
        raise BuildRefusedError(f"derived preflight failed: {error}") from error

    if plan.figure_recipes:
        figures_by_id = {row.figure_id: row for row in plan.figure_recipes}
        expected_derived = {
            row.figure_id: (
                set()
                if row.derived_data_ids == "N/A"
                else set(IdList.parse(row.derived_data_ids).items)
            )
            for row in plan.figure_recipes
        }
        actual_derived = {figure_id: set() for figure_id in figures_by_id}
        try:
            for recipe in plan.derived_recipes:
                parent_figures = IdList.parse(recipe.parent_figure_ids).items
                parent_data = set(IdList.parse(recipe.parent_data_ids).items)
                for figure_id in parent_figures:
                    figure = figures_by_id.get(figure_id)
                    if figure is None:
                        raise BuildRefusedError(
                            "derived recipe coverage references an unknown figure: "
                            f"{figure_id}"
                        )
                    if recipe.output_data_id not in expected_derived[figure_id]:
                        raise BuildRefusedError(
                            f"derived recipe coverage has unrelated output_data_id "
                            f"{recipe.output_data_id!r} for {figure_id}"
                        )
                    figure_parent_data = (
                        set()
                        if figure.parent_data_ids == "N/A"
                        else set(IdList.parse(figure.parent_data_ids).items)
                    )
                    if not parent_data <= figure_parent_data:
                        raise BuildRefusedError(
                            f"derived recipe parent data do not match {figure_id}"
                        )
                    actual_derived[figure_id].add(recipe.output_data_id)
        except ManifestError as error:
            raise BuildRefusedError(
                f"derived recipe coverage failed: {error}"
            ) from error
        mismatches = {
            figure_id: {
                "missing": sorted(expected_derived[figure_id] - actual_derived[figure_id]),
                "extra": sorted(actual_derived[figure_id] - expected_derived[figure_id]),
            }
            for figure_id in figures_by_id
            if actual_derived[figure_id] != expected_derived[figure_id]
        }
        if mismatches:
            raise BuildRefusedError(
                f"derived recipe coverage is incomplete: {mismatches!r}"
            )
        targets_by_figure: dict[str, str] = {}
        for figure in plan.figure_recipes:
            targets = [
                row.target_path
                for row in plan.required_assets
                if row.source_path == figure.figure_path and row.target_path is not None
            ]
            if len(targets) != 1:
                raise BuildRefusedError(
                    f"figure has no unique packaged target: {figure.figure_id}"
                )
            targets_by_figure[figure.figure_id] = targets[0]
        data_paths = (
            None if plan.manifest_keys is None else dict(plan.manifest_keys.data_paths)
        )
        if data_paths is not None:
            for recipe in plan.derived_recipes:
                if data_paths.get(recipe.output_data_id) != recipe.output_path:
                    raise BuildRefusedError(
                        f"derived output path is not bound in data manifest: "
                        f"{recipe.output_data_id}"
                    )
        try:
            packaged_figures = package_figure_recipes(
                plan.figure_recipes,
                plan.required_assets,
                plan.redraw_recipes,
                {} if data_paths is None else data_paths,
            )
            validate_redraw_plan(
                packaged_figures,
                plan.redraw_recipes,
                figure_targets=targets_by_figure,
                data_paths=data_paths,
                executable_fields_prevalidated=True,
            )
        except (RedrawError, VerificationError) as error:
            raise BuildRefusedError(f"redraw plan failed: {error}") from error
        if plan.manifest_keys is None:
            raise BuildRefusedError(
                "figure closure manifest keys are required before publication"
            )
        try:
            for figure in plan.figure_recipes:
                validate_figure_closure(figure, plan.manifest_keys)
        except ManifestError as error:
            raise BuildRefusedError(f"figure closure failed: {error}") from error

    sources, _ = _row_groups(plan.required_assets)
    staged_paths = {
        row.target_path for row in sources if row.target_path is not None
    }
    reserved = {
        "00_handoff/DERIVED_DATA_EVIDENCE.csv",
        "00_handoff/FIGURE_REDRAW_EVIDENCE.csv",
        ".handoff-staging",
    }
    derived_paths = {recipe.output_path for recipe in plan.derived_recipes}
    collisions = (derived_paths | reserved) & staged_paths
    if collisions:
        raise BuildRefusedError(
            f"lineage output collides with copied target: {sorted(collisions)!r}"
        )
    if derived_paths & reserved:
        raise BuildRefusedError("derived output collides with reserved build evidence")
    available = staged_paths | derived_paths
    for recipe in plan.redraw_recipes:
        required = {recipe.script_path, *recipe.inputs}
        if not recipe.validation_only:
            required.add(recipe.reference_product_path)
        missing = sorted(required - available)
        if missing:
            raise BuildRefusedError(
                f"{recipe.redraw_id}: redraw inputs are not staged: {missing!r}"
            )
    redraw_ids = [recipe.redraw_id for recipe in plan.redraw_recipes]
    if len(redraw_ids) != len(set(redraw_ids)):
        raise BuildRefusedError("redraw IDs must be unique")


def _validate_portable_preflight(plan: BuildPlan) -> None:
    """Recompute every optional portable obligation before destination writes."""
    contract = plan.portable_contract
    _require_portable_contract(contract)
    assert contract is not None
    _validate_canonical_portable_ledgers(plan, contract)
    try:
        validate_portable_contract(contract, project_root=plan.project_root)
    except PortableError as error:
        raise BuildRefusedError(f"portable contract failed: {error}") from error

    if not plan.required_assets.source_paths_are_unique():
        raise BuildRefusedError(
            "portable preflight requires unique required-asset source paths"
        )
    if not plan.required_assets.target_paths_are_unique():
        raise BuildRefusedError(
            "portable preflight requires unique required-asset target paths"
        )
    copied = tuple(
        row
        for row in plan.required_assets
        if row.target_path is not None
        and row.disposition in {"copied_active", "copied_archive"}
    )
    disposition_by_source = {row.source_path: row.disposition for row in copied}
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
    discovery_paths = tuple(
        row.source_path
        for row in copied
        if (
            PurePosixPath(row.source_path).suffix.casefold() in discoverable_suffixes
            or not PurePosixPath(row.source_path).suffix
        )
    )
    try:
        discoveries = discover_full_field_consumers(
            plan.project_root, discovery_paths
        )
        validate_field_consumer_registry(
            discoveries,
            contract.consumers,
            disposition_by_source,
            publish=True,
            project_root=plan.project_root,
        )
    except PortableError as error:
        raise BuildRefusedError(
            f"full-field consumer registry failed: {error}"
        ) from error

    rows_by_target = {
        row.target_path: row for row in copied if row.target_path is not None
    }
    rows_by_source = {row.source_path: row for row in copied}
    staged_targets = set(rows_by_target)
    generated_targets = {
        transform.portable_path for transform in contract.transforms
    } | {
        runtime.launcher_path for runtime in contract.runtime_entries
    } | set(PORTABLE_OUTPUT_PATHS)
    collisions = staged_targets & generated_targets
    if collisions:
        raise BuildRefusedError(
            f"portable output collides with copied target: {sorted(collisions)!r}"
        )
    derived_collisions = {
        recipe.output_path for recipe in plan.derived_recipes
    } & generated_targets
    if derived_collisions:
        raise BuildRefusedError(
            "portable output collides with derived output: "
            f"{sorted(derived_collisions)!r}"
        )
    for transform in contract.transforms:
        source_row = rows_by_source.get(transform.source_path)
        if (
            source_row is None
            or source_row.disposition != "copied_active"
            or source_row.target_path != transform.original_path
        ):
            raise BuildRefusedError(
                "portable source-to-original binding mismatch: "
                f"{transform.source_path} -> {transform.original_path}"
            )
        if source_row.sha256 != transform.original_sha256:
            raise BuildRefusedError(
                "portable transform SHA256 differs from required inventory: "
                f"{transform.original_path}"
            )
    try:
        bind_initial_state_recipes_to_package(
            contract.recipes,
            required_assets=plan.required_assets,
            transforms=contract.transforms,
        )
    except PortableError as error:
        raise BuildRefusedError(
            f"initial-state package projection failed: {error}"
        ) from error


def _validate_canonical_portable_ledgers(
    plan: BuildPlan,
    contract: PortableContract,
) -> None:
    """Bind caller objects to the current versioned scientific ledgers."""
    _validate_canonical_portable_ledgers_at_root(plan.project_root, contract)


def _validate_canonical_portable_ledgers_at_root(
    project_root: Path,
    contract: PortableContract,
) -> None:
    """Load canonical portable ledgers without trusting an in-memory plan."""
    ledger_root = project_root / "95_shared_scripts/handoff_delivery"
    try:
        recipes = load_initial_state_recipes(
            ledger_root / "initial_state_recipes.csv",
            project_root=project_root,
        )
        consumers = load_field_consumer_registry(
            ledger_root / "full_field_consumers.csv",
            project_root=project_root,
        )
    except PortableError as error:
        raise BuildRefusedError(
            f"canonical portable ledger failed: {error}"
        ) from error
    if recipes != contract.recipes:
        raise BuildRefusedError(
            "build contract does not match canonical initial-state recipe ledger"
        )
    if consumers != contract.consumers:
        raise BuildRefusedError(
            "build contract does not match canonical full-field consumer ledger"
        )


def _route_portable_original_assets(
    inventory: RequiredAssetInventory,
    contract: PortableContract,
) -> RequiredAssetInventory:
    """Deterministically route each transform source to its archival original."""
    if not inventory.source_paths_are_unique():
        raise BuildRefusedError(
            "portable original routing requires unique source paths"
        )
    routed = list(inventory.rows)
    index_by_source = {row.source_path: index for index, row in enumerate(routed)}
    for transform in contract.transforms:
        index = index_by_source.get(transform.source_path)
        if index is None:
            raise BuildRefusedError(
                f"portable transform source is absent from required assets: {transform.source_path}"
            )
        row = routed[index]
        if row.disposition != "copied_active":
            raise BuildRefusedError(
                f"portable transform source is not copied_active: {transform.source_path}"
            )
        if row.sha256 != transform.original_sha256:
            raise BuildRefusedError(
                f"portable transform source SHA256 mismatch: {transform.source_path}"
            )
        routed[index] = replace(
            row,
            target_path=transform.original_path,
            disposition="copied_active",
            expected_target_class="active",
            reason=f"portable-original:{transform.transform_id}",
        )
    result = RequiredAssetInventory(tuple(routed))
    if not result.target_paths_are_unique():
        raise BuildRefusedError(
            "portable original routing creates duplicate delivery targets"
        )
    return result


def _require_portable_contract(contract: PortableContract | None) -> None:
    """Make portability a mandatory production gate, including dry-runs."""
    if contract is None:
        raise BuildRefusedError("portable contract is required for every build")


def _resolve_docs_config(
    project_root: Path,
    supplied: DocsConfig | None,
) -> DocsConfig | None:
    if supplied is not None:
        return supplied
    path = project_root / "95_shared_scripts/handoff_delivery/handoff_docs.toml"
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise BuildRefusedError("cannot inspect versioned handoff_docs.toml") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise BuildRefusedError("versioned handoff_docs.toml is not a regular file")
    try:
        return load_docs_config(path, project_root=project_root)
    except RuntimeError as error:
        raise BuildRefusedError(f"versioned documentation config failed: {error}") from error


def prepare_build(
    *,
    project_root: Path | str,
    old_delivery: Path | str,
    destination: Path | str,
    tree_specs: Sequence[TreeSourceSpec] = TREE_SOURCE_SPECS,
    exact_specs: Sequence[ExactSourceSpec] = EXACT_SOURCE_SPECS,
    include_thesis_assets: bool = True,
    manifest_keys: ManifestKeys | None = None,
    derived_recipes: Sequence[DerivedRecipe] = (),
    redraw_recipes: Sequence[RedrawRecipe] = (),
    portable_contract: PortableContract | None = None,
    docs_config: DocsConfig | None = None,
) -> BuildPlan:
    """Prepare an immutable build plan without writing the v2 destination."""
    _require_portable_contract(portable_contract)
    project = Path(project_root).absolute()
    resolved_docs_config = _resolve_docs_config(project, docs_config)
    assert portable_contract is not None
    _validate_canonical_portable_ledgers_at_root(project, portable_contract)
    old = Path(old_delivery).absolute()
    target = Path(destination).absolute()
    baseline = capture_baseline(old)
    inventory = enumerate_required_assets(
        project,
        tree_specs=tree_specs,
        exact_specs=exact_specs,
        include_thesis_assets=include_thesis_assets,
    )
    resolved_figure_recipes = _load_project_figure_recipes(project)
    inventory = _route_figure_assets(inventory, resolved_figure_recipes)
    inventory = _route_portable_original_assets(inventory, portable_contract)

    resolved_old = old.resolve()
    resolved_target = target.resolve(strict=False)
    if resolved_target == resolved_old or resolved_old in resolved_target.parents:
        raise BuildRefusedError("v2 destination must not be inside the old delivery")
    plan = BuildPlan(
        project_root=project,
        old_delivery=old,
        destination=target,
        required_assets=inventory,
        old_baseline=baseline,
        figure_recipes=resolved_figure_recipes,
        manifest_keys=manifest_keys,
        derived_recipes=tuple(derived_recipes),
        redraw_recipes=tuple(redraw_recipes),
        portable_contract=portable_contract,
        docs_config=resolved_docs_config,
        tree_specs=tuple(tree_specs),
        exact_specs=tuple(exact_specs),
        include_thesis_assets=include_thesis_assets,
    )
    _validate_lineage_preflight(plan)
    _validate_portable_preflight(plan)
    return plan


def _difference_or_error(plan: BuildPlan) -> BaselineDifference:
    try:
        return compare_baseline(plan.old_delivery, plan.old_baseline)
    except BaselineError as error:
        return BaselineDifference(errors=(str(error),))


def _build_result(
    plan: BuildPlan,
    *,
    exit_code: int,
    publishable: bool,
    dry_run: bool,
    reason: str,
    difference: BaselineDifference,
    written_paths: tuple[str, ...] = (),
    recovery_status: str = "not-needed",
    recovery_paths: tuple[str, ...] = (),
) -> BuildResult:
    sources, exclusions = _row_groups(plan.required_assets)
    return BuildResult(
        exit_code=exit_code,
        publishable=publishable,
        dry_run=dry_run,
        reason=reason,
        required_rows=plan.required_assets.rows,
        source_rows=sources,
        exclusion_rows=exclusions,
        baseline_difference=difference,
        written_paths=written_paths,
        recovery_status=recovery_status,
        recovery_paths=recovery_paths,
    )


def _raise_resume_walk_error(error: OSError) -> None:
    location = getattr(error, "filename", None) or "unknown path"
    raise BuildRefusedError(
        f"cannot enumerate resume destination at {location}: {error}"
    ) from error


def _reject_destination_symlinks(destination: Path) -> None:
    try:
        metadata = destination.lstat()
    except FileNotFoundError:
        return
    except OSError as error:
        raise BuildRefusedError(f"cannot inspect destination: {destination}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise BuildRefusedError("destination must be a real directory, not a symlink")

    for current_raw, directory_names, file_names in os.walk(
        destination,
        topdown=True,
        followlinks=False,
        onerror=_raise_resume_walk_error,
    ):
        current = Path(current_raw)
        for name in (*directory_names, *file_names):
            path = current / name
            try:
                if stat.S_ISLNK(path.lstat().st_mode):
                    raise BuildRefusedError(
                        f"resume destination contains a symlink: {path}"
                    )
            except OSError as error:
                raise BuildRefusedError(
                    f"cannot inspect resume destination path: {path}"
                ) from error


def _resume_allowlist(
    source_rows: Sequence[RequiredAssetRow],
    generated_paths: Sequence[str] = (),
) -> tuple[dict[str, RequiredAssetRow | None], frozenset[str]]:
    allowed_files: dict[str, RequiredAssetRow | None] = {}
    allowed_directories: set[str] = set()
    for row in source_rows:
        if row.target_path is None:
            raise BuildRefusedError(
                f"copied row has no mapped target: {row.source_path}"
            )
        relative = PurePosixPath(row.target_path)
        allowed_files[row.target_path] = row
    for raw in generated_paths:
        try:
            relative = require_relative_path(raw).as_posix()
        except ManifestError as error:
            raise BuildRefusedError(
                f"invalid declared generated resume path: {raw!r}"
            ) from error
        if relative in allowed_files:
            raise BuildRefusedError(
                f"generated resume path collides with a copied target: {relative}"
            )
        allowed_files[relative] = None
    for raw in allowed_files:
        relative = PurePosixPath(raw)
        for parent in relative.parents:
            if parent != PurePosixPath("."):
                if parent.as_posix() in allowed_files:
                    raise BuildRefusedError(
                        "resume allowlist has a file/directory collision: "
                        f"{parent.as_posix()}"
                    )
                allowed_directories.add(parent.as_posix())
    return allowed_files, frozenset(allowed_directories)


def _validate_resume_file(path: Path, row: RequiredAssetRow) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise BuildRefusedError(f"cannot inspect resume file: {path}") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise BuildRefusedError(f"resume mapped target is not a regular file: {path}")
    try:
        digest = _hash_regular_no_follow(path, metadata)
    except BaselineError as error:
        raise BuildRefusedError(f"resume mapped target is unstable: {path}") from error
    if metadata.st_size != row.size or digest != row.sha256:
        raise BuildRefusedError(
            f"resume mapped target has wrong size or SHA256: {path}"
        )


def _validate_resume_generated_file(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise BuildRefusedError(f"cannot inspect resume generated file: {path}") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise BuildRefusedError(
            f"resume generated target is not a regular file: {path}"
        )
    try:
        _hash_regular_no_follow(path, metadata)
    except BaselineError as error:
        raise BuildRefusedError(
            f"resume generated target is unstable: {path}"
        ) from error


def _validate_resume_contents(
    destination: Path,
    source_rows: Sequence[RequiredAssetRow],
    generated_paths: Sequence[str] = (),
) -> None:
    allowed_files, allowed_directories = _resume_allowlist(
        source_rows, generated_paths
    )
    for current_raw, directory_names, file_names in os.walk(
        destination,
        topdown=True,
        followlinks=False,
        onerror=_raise_resume_walk_error,
    ):
        current = Path(current_raw)
        directory_names.sort()
        file_names.sort()
        for name in directory_names:
            path = current / name
            relative = path.relative_to(destination).as_posix()
            if relative not in allowed_directories or relative in allowed_files:
                raise BuildRefusedError(
                    f"resume destination contains unknown directory: {relative}"
                )
        for name in file_names:
            path = current / name
            relative = path.relative_to(destination).as_posix()
            if relative not in allowed_files:
                raise BuildRefusedError(
                    f"resume destination contains unknown file: {relative}"
                )
            row = allowed_files[relative]
            if row is None:
                _validate_resume_generated_file(path)
            else:
                _validate_resume_file(path, row)


def _declared_generated_paths(plan: BuildPlan) -> tuple[str, ...]:
    paths = {
        "00_handoff/verification_report.json",
        "00_handoff/SHA256SUMS.txt",
        *(recipe.output_path for recipe in plan.derived_recipes),
    }
    if plan.derived_recipes:
        paths.add("00_handoff/DERIVED_DATA_EVIDENCE.csv")
    if plan.redraw_recipes:
        paths.add("00_handoff/FIGURE_REDRAW_EVIDENCE.csv")
        paths.update(
            recipe.output_path
            for recipe in plan.redraw_recipes
            if not recipe.validation_only
        )
    if plan.portable_contract is not None:
        paths.update(PORTABLE_OUTPUT_PATHS)
        paths.update(
            transform.portable_path
            for transform in plan.portable_contract.transforms
        )
        paths.update(
            runtime.launcher_path
            for runtime in plan.portable_contract.runtime_entries
        )
    if plan.docs_config is not None:
        paths.update(row.target_path for row in plan.docs_config.documents)
        if plan.portable_contract is not None:
            paths.update(
                package_verifier_assets(
                    plan.portable_contract,
                    tree_specs=plan.tree_specs,
                    exact_specs=plan.exact_specs,
                    include_thesis_assets=plan.include_thesis_assets,
                )
            )
    return tuple(sorted(paths))


def _destination_root_identity(
    metadata: os.stat_result,
) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def _capture_destination_snapshot(destination: Path) -> DestinationSnapshot:
    try:
        initial = destination.lstat()
    except FileNotFoundError:
        return DestinationSnapshot(False, None, ())
    except OSError as error:
        raise BuildRefusedError(
            f"cannot snapshot destination root: {destination}"
        ) from error
    if stat.S_ISLNK(initial.st_mode) or not stat.S_ISDIR(initial.st_mode):
        raise BuildRefusedError(
            f"destination snapshot root is not a real directory: {destination}"
        )

    _reject_destination_symlinks(destination)
    try:
        baseline = capture_baseline(destination)
    except BaselineError as error:
        raise BuildRefusedError(
            f"cannot snapshot destination contents: {destination}"
        ) from error
    if any(entry.path_type == "symlink" for entry in baseline.entries):
        raise BuildRefusedError(
            f"destination changed to contain a symlink: {destination}"
        )
    try:
        final = destination.lstat()
    except OSError as error:
        raise BuildRefusedError(
            f"destination changed while snapshotting: {destination}"
        ) from error
    if not _same_snapshot(initial, final):
        raise BuildRefusedError(
            f"destination root changed while snapshotting: {destination}"
        )
    return DestinationSnapshot(
        True,
        _destination_root_identity(final),
        baseline.entries,
    )


def _validate_destination(
    destination: Path,
    *,
    resume: bool,
    source_rows: Sequence[RequiredAssetRow],
    generated_paths: Sequence[str] = (),
) -> DestinationSnapshot:
    _reject_destination_symlinks(destination)
    if not destination.exists():
        return _capture_destination_snapshot(destination)
    try:
        nonempty = next(destination.iterdir(), None) is not None
    except OSError as error:
        raise BuildRefusedError(f"cannot list destination: {destination}") from error
    if nonempty and not resume:
        raise BuildRefusedError(
            "destination is non-empty; explicit resume=True is required"
        )
    if resume:
        _validate_resume_contents(destination, source_rows, generated_paths)
    return _capture_destination_snapshot(destination)


def _safe_target(staging: Path, target_path: str) -> Path:
    try:
        relative = require_relative_path(target_path)
    except ManifestError as error:
        raise BuildRefusedError(f"unsafe mapped target: {target_path!r}") from error
    current = staging
    for part in relative.parts[:-1]:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            current.mkdir()
            continue
        except OSError as error:
            raise BuildRefusedError(f"cannot inspect target ancestor: {current}") from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise BuildRefusedError(f"target ancestor is not a real directory: {current}")
    target = staging / relative.as_posix()
    try:
        metadata = target.lstat()
    except FileNotFoundError:
        return target
    except OSError as error:
        raise BuildRefusedError(f"cannot inspect target: {target}") from error
    if stat.S_ISLNK(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode):
        raise BuildRefusedError(f"mapped target is a symlink or directory: {target}")
    return target


def _copy_asset(
    plan: BuildPlan,
    row: RequiredAssetRow,
    staging: Path,
    source_anchor: AnchoredRoot,
) -> None:
    """Copy one mapped regular file through a stable, no-follow descriptor."""
    if row.target_path is None:
        raise BuildRefusedError(f"excluded row cannot be copied: {row.source_path}")
    source = plan.project_root / row.source_path
    initial = source_anchor.lstat(row.source_path)
    if not stat.S_ISREG(initial.st_mode):
        raise BuildRefusedError(f"mapped source is not a regular file: {source}")

    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor = source_anchor.open_regular(row.source_path)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or not _same_snapshot(initial, opened):
            raise BuildRefusedError(f"source changed while opening: {source}")
        target = _safe_target(staging, row.target_path)
        temporary_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".copying", dir=target.parent
        )
        temporary = Path(temporary_name)
        digest = hashlib.sha256()
        total = 0
        with os.fdopen(descriptor, "rb", closefd=True) as reader:
            descriptor = -1
            with os.fdopen(temporary_descriptor, "wb", closefd=True) as writer:
                while chunk := reader.read(1024 * 1024):
                    digest.update(chunk)
                    total += len(chunk)
                    writer.write(chunk)
                writer.flush()
                os.fsync(writer.fileno())
            final_descriptor = os.fstat(reader.fileno())
        final_path = source_anchor.lstat(row.source_path)
        if not (
            _same_snapshot(initial, opened)
            and _same_snapshot(opened, final_descriptor)
            and _same_snapshot(final_descriptor, final_path)
        ):
            raise BuildRefusedError(f"source changed during copy: {source}")
        if total != row.size or digest.hexdigest() != row.sha256:
            raise BuildRefusedError(f"source bytes no longer match inventory: {source}")
        os.replace(temporary, target)
        temporary = None
    except OSError as error:
        raise BuildRefusedError(f"cannot copy source asset: {source}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _copy_generated_file(
    source: Path,
    staging: Path,
    target_path: str,
    expected_sha256: str,
) -> None:
    """Copy a just-produced regular file without permitting target replacement."""
    try:
        initial = source.lstat()
    except OSError as error:
        raise BuildRefusedError(f"cannot inspect generated file: {source}") from error
    if stat.S_ISLNK(initial.st_mode) or not stat.S_ISREG(initial.st_mode):
        raise BuildRefusedError(f"generated output is not a regular file: {source}")
    target = _safe_target(staging, target_path)
    try:
        target.lstat()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise BuildRefusedError(f"cannot inspect generated target: {target}") from error
    else:
        raise BuildRefusedError(f"generated target already exists: {target_path}")

    source_descriptor = -1
    target_descriptor = -1
    try:
        source_descriptor = os.open(
            source,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
        )
        opened = os.fstat(source_descriptor)
        if not stat.S_ISREG(opened.st_mode) or not _same_snapshot(initial, opened):
            raise BuildRefusedError(f"generated output changed while opening: {source}")
        target_descriptor = os.open(
            target,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            0o644,
        )
        digest = hashlib.sha256()
        with os.fdopen(source_descriptor, "rb", closefd=True) as reader:
            source_descriptor = -1
            with os.fdopen(target_descriptor, "wb", closefd=True) as writer:
                target_descriptor = -1
                while chunk := reader.read(1024 * 1024):
                    digest.update(chunk)
                    writer.write(chunk)
                writer.flush()
                os.fsync(writer.fileno())
            final_descriptor = os.fstat(reader.fileno())
        final_source = source.lstat()
        if not (
            _same_snapshot(initial, opened)
            and _same_snapshot(opened, final_descriptor)
            and _same_snapshot(final_descriptor, final_source)
        ):
            raise BuildRefusedError(f"generated output changed during copy: {source}")
        if digest.hexdigest() != expected_sha256:
            raise BuildRefusedError(
                f"generated output SHA256 changed during copy: {target_path}"
            )
    except OSError as error:
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        raise BuildRefusedError(f"cannot copy generated output: {target_path}") from error
    finally:
        if source_descriptor >= 0:
            os.close(source_descriptor)
        if target_descriptor >= 0:
            os.close(target_descriptor)


def _materialize_lineage_pipeline(
    plan: BuildPlan,
    staging: Path,
) -> tuple[str, ...]:
    """Generate derived data and redraw evidence before publication."""
    written: list[str] = []
    derived_root: Path | None = None
    try:
        if plan.derived_recipes:
            derived_root = Path(
                tempfile.mkdtemp(
                    prefix=f".{plan.destination.name}.derived-",
                    dir=plan.destination.parent,
                )
            )
            evidence = tuple(
                produce_derived_in_environment(
                    recipe,
                    project_root=plan.project_root,
                    output_root=derived_root,
                )
                for recipe in plan.derived_recipes
            )
            validate_derived_outputs(
                list(plan.derived_recipes),
                list(evidence),
                output_root=derived_root,
            )
            evidence_by_id = {row.recipe_id: row for row in evidence}
            for recipe in plan.derived_recipes:
                row = evidence_by_id[recipe.recipe_id]
                _copy_generated_file(
                    derived_root / recipe.output_path,
                    staging,
                    recipe.output_path,
                    row.output_sha256,
                )
                written.append(recipe.output_path)
            derived_evidence_path = "00_handoff/DERIVED_DATA_EVIDENCE.csv"
            target = _safe_target(staging, derived_evidence_path)
            write_derived_evidence(target, list(evidence))
            written.append(derived_evidence_path)

        if plan.redraw_recipes:
            build_token = secrets.token_hex(32)
            marker = staging / ".handoff-staging"
            marker_created = False
            try:
                try:
                    with marker.open("x", encoding="utf-8", errors="strict") as handle:
                        handle.write(build_token + "\n")
                        handle.flush()
                        os.fsync(handle.fileno())
                    marker_created = True
                except OSError as error:
                    raise BuildRefusedError(
                        f"cannot create exclusive staging marker: {marker}"
                    ) from error
                redraw_evidence_path = "00_handoff/FIGURE_REDRAW_EVIDENCE.csv"
                execute_redraws(
                    plan.redraw_recipes,
                    staging_root=staging,
                    build_token=build_token,
                    evidence_path=staging / redraw_evidence_path,
                )
                written.append(redraw_evidence_path)
            finally:
                if marker_created:
                    try:
                        marker.unlink()
                    except FileNotFoundError:
                        pass
        return tuple(written)
    except (DerivedDataError, RedrawError) as error:
        raise BuildRefusedError(f"lineage pipeline failed: {error}") from error
    finally:
        if derived_root is not None and _path_exists_no_follow(derived_root):
            try:
                _remove_tree(derived_root)
            except (OSError, shutil.Error) as error:
                raise BuildRefusedError(
                    f"cannot clean isolated derived workspace: {derived_root}"
                ) from error


def _materialize_docs_pipeline(
    plan: BuildPlan,
    staging: Path,
) -> tuple[str, ...]:
    """Render configured docs and the package-local read-only verifier."""
    if plan.docs_config is None:
        return ()
    if plan.portable_contract is None:
        verifier_assets = {"00_handoff/verify_delivery.py": b""}
    else:
        verifier_assets = package_verifier_assets(
            plan.portable_contract,
            tree_specs=plan.tree_specs,
            exact_specs=plan.exact_specs,
            include_thesis_assets=plan.include_thesis_assets,
        )
    package_paths = frozenset(
        path.relative_to(staging).as_posix()
        for path in staging.rglob("*")
        if path.is_file()
    ) | frozenset(verifier_assets)
    try:
        rendered = render_documents(
            plan.docs_config,
            package_paths=package_paths,
        )
    except RuntimeError as error:
        raise BuildRefusedError(f"documentation rendering failed: {error}") from error
    written: list[str] = []
    for relative, payload in rendered.items():
        target = _safe_target(staging, relative)
        try:
            with target.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as error:
            raise BuildRefusedError(
                f"cannot exclusively materialize documentation: {relative}"
            ) from error
        written.append(relative)
    for relative, payload in verifier_assets.items():
        target = _safe_target(staging, relative)
        try:
            with target.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if relative == "00_handoff/verify_delivery.py":
                target.chmod(0o755)
        except OSError as error:
            raise BuildRefusedError(
                f"cannot exclusively materialize package verifier asset: {relative}"
            ) from error
        written.append(relative)
    return tuple(written)


def _materialize_portable_pipeline(
    plan: BuildPlan,
    staging: Path,
) -> _PinnedPortableMaterialization:
    """Create explicit portable outputs, if supplied, only inside staging."""
    if plan.portable_contract is None:
        return _pin_staging_pipeline_result(staging, ())
    try:
        package_initial_state_contract = bind_initial_state_recipes_to_package(
            plan.portable_contract.recipes,
            required_assets=plan.required_assets,
            transforms=plan.portable_contract.transforms,
        )
        materialized = materialize_portable_contract(
            plan.portable_contract,
            staging_root=staging,
            package_initial_state_contract=package_initial_state_contract,
            _retain_staging_descriptor=True,
        )
        if not isinstance(materialized, _PinnedPortableMaterialization):
            raise BuildRefusedError(
                "portable materialization did not retain its verified staging root"
            )
        return materialized
    except PortableError as error:
        raise BuildRefusedError(f"portable materialization failed: {error}") from error


def _finalize_verified_staging(
    plan: BuildPlan,
    staging: Path,
    materialized: _PinnedPortableMaterialization,
) -> _VerifiedStagingHandle:
    """Run mandatory gates, then append report/checksum through the same pinned fd."""
    contract = plan.portable_contract
    _require_portable_contract(contract)
    assert contract is not None
    descriptor = materialized.staging_descriptor
    try:
        metadata = os.fstat(descriptor)
    except OSError as error:
        raise BuildRefusedError("cannot inspect pinned staging before verification") from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or _destination_root_identity(metadata) != materialized.staging_identity
    ):
        raise BuildRefusedError("pinned staging identity changed before verification")

    try:
        results = verify(
            staging,
            project_root=plan.project_root,
            portable_contract=contract,
            tree_specs=plan.tree_specs,
            exact_specs=plan.exact_specs,
            include_thesis_assets=plan.include_thesis_assets,
            root_descriptor=descriptor,
            expected_snapshot=materialized.staging_snapshot,
            expected_figure_recipes=plan.figure_recipes,
            expected_redraw_recipes=plan.redraw_recipes,
            expected_derived_recipes=plan.derived_recipes,
            expected_required_assets=plan.required_assets,
            require_final_evidence=False,
        )
    except Exception as error:
        raise BuildRefusedError(
            f"delivery verification could not complete: {type(error).__name__}:{error}"
        ) from error
    if verification_exit_code(results) != 0:
        failed = tuple(row.gate for row in results if not row.passed)
        details = tuple(
            finding for row in results if not row.passed for finding in row.findings
        )
        raise BuildRefusedError(
            f"delivery verification failed gates {failed!r}: {details!r}"
        )

    try:
        write_report(staging, results, root_descriptor=descriptor)
        write_checksums(staging, root_descriptor=descriptor)
        final_scan = scan_delivery_absolute_paths(
            staging,
            root_descriptor=descriptor,
            _include_snapshot=True,
        )
        final_metadata = os.fstat(descriptor)
    except (OSError, PortableError, RuntimeError) as error:
        raise BuildRefusedError(
            f"cannot finalize verified staging: {type(error).__name__}:{error}"
        ) from error
    if (
        not isinstance(final_scan, _PinnedDeliveryScan)
        or final_scan.findings
        or _destination_root_identity(final_metadata) != materialized.staging_identity
    ):
        raise BuildRefusedError(
            "final report/checksum tree failed pinned G4 or root identity verification"
        )
    final_paths = {row.relative_path for row in final_scan.snapshot}
    required_final = {
        "00_handoff/verification_report.json",
        "00_handoff/SHA256SUMS.txt",
    }
    initial_by_path = {
        row.relative_path: row for row in materialized.staging_snapshot
    }
    final_by_path = {row.relative_path: row for row in final_scan.snapshot}
    expected_final_paths = set(initial_by_path) | required_final
    if final_paths != expected_final_paths:
        raise BuildRefusedError(
            "final pinned snapshot delta is not exactly report plus checksum"
        )
    changed_paths = sorted(
        relative
        for relative, initial in initial_by_path.items()
        if final_by_path.get(relative) != initial
    )
    if changed_paths:
        raise BuildRefusedError(
            f"final pinned snapshot changed verified paths: {changed_paths!r}"
        )
    report_relative = "00_handoff/verification_report.json"
    checksum_relative = "00_handoff/SHA256SUMS.txt"
    report_payload = _report_payload(results)
    report_row = final_by_path[report_relative]
    if (
        report_row.path_type != "file"
        or report_row.size != len(report_payload)
        or report_row.sha256 != hashlib.sha256(report_payload).hexdigest()
    ):
        raise BuildRefusedError(
            "final verification report bytes differ from deterministic payload"
        )
    expected_report_row = _PinnedTreeEntry(
        report_relative,
        "file",
        report_row.mode,
        len(report_payload),
        hashlib.sha256(report_payload).hexdigest(),
    )
    checksum_basis = tuple(
        expected_report_row if row.relative_path == report_relative else row
        for row in final_scan.snapshot
        if row.relative_path != checksum_relative
    )
    checksum_payload = _checksum_payload(checksum_basis)
    checksum_row = final_by_path[checksum_relative]
    if (
        checksum_row.path_type != "file"
        or checksum_row.size != len(checksum_payload)
        or checksum_row.sha256 != hashlib.sha256(checksum_payload).hexdigest()
    ):
        raise BuildRefusedError(
            "final checksum bytes differ from deterministic payload"
        )
    return _VerifiedStagingHandle(
        descriptor,
        materialized.staging_identity,
        final_scan.snapshot,
    )


def _pin_staging_pipeline_result(
    staging: Path,
    written_paths: tuple[str, ...],
) -> _PinnedPortableMaterialization:
    """Return a descriptor-owned pipeline result for a tree with no portable scan."""
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not no_follow or not directory_flag:
        raise BuildRefusedError(
            "verified staging requires O_NOFOLLOW and O_DIRECTORY"
        )
    descriptor = -1
    try:
        descriptor = os.open(
            staging,
            os.O_RDONLY
            | no_follow
            | directory_flag
            | getattr(os, "O_CLOEXEC", 0),
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise BuildRefusedError(
                "verified staging tree is not one real directory"
            )
        identity = _destination_root_identity(metadata)
        snapshot = _snapshot_delivery_descriptor(descriptor)
        retained = descriptor
        descriptor = -1
        return _PinnedPortableMaterialization(
            written_paths,
            retained,
            identity,
            snapshot,
        )
    except (OSError, PortableError) as error:
        raise BuildRefusedError("cannot pin verified staging tree") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _vacant_sibling(destination: Path, *, label: str) -> Path:
    created = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.{label}-",
            dir=destination.parent,
        )
    )
    created.rmdir()
    return created


def _path_exists_no_follow(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _raise_publication_failure(
    message: str,
    *,
    destination: Path,
    backup: Path | None,
    displaced_snapshot: DestinationSnapshot | None,
    restored_status: str,
    cause: Exception | None = None,
) -> None:
    recovery_status = restored_status
    recovery_paths: list[str] = []
    if backup is not None and _path_exists_no_follow(backup):
        if _path_exists_no_follow(destination):
            recovery_status = "manual-recovery-required"
            recovery_paths.extend((str(destination), str(backup)))
        else:
            try:
                os.replace(backup, destination)
            except (OSError, shutil.Error):
                recovery_status = "manual-recovery-required"
                recovery_paths.append(str(backup))
    elif restored_status != "empty-destination-restored":
        recovery_status = "manual-recovery-required"
        if _path_exists_no_follow(destination):
            recovery_paths.append(str(destination))

    failure = _PublicationFailure(
        message,
        backup=backup,
        displaced_snapshot=displaced_snapshot,
        recovery_status=recovery_status,
        recovery_paths=tuple(dict.fromkeys(recovery_paths)),
    )
    if cause is not None:
        raise failure from cause
    raise failure


def _publish_staging(
    staging: Path,
    destination: Path,
    expected_destination: DestinationSnapshot,
    *,
    verified_staging: _VerifiedStagingHandle,
) -> Path | None:
    """Publish only if the atomically displaced destination matches validation."""
    expected_staging_identity = verified_staging.identity
    try:
        verified_metadata = os.fstat(verified_staging.descriptor)
        staging_metadata = staging.lstat()
    except OSError as error:
        raise _PublicationFailure(
            "staging-changed-before-publish",
            backup=None,
            displaced_snapshot=None,
            recovery_status="not-needed",
            recovery_paths=(),
        ) from error
    if (
        not stat.S_ISDIR(verified_metadata.st_mode)
        or _destination_root_identity(verified_metadata) != expected_staging_identity
        or stat.S_ISLNK(staging_metadata.st_mode)
        or not stat.S_ISDIR(staging_metadata.st_mode)
        or _destination_root_identity(staging_metadata) != expected_staging_identity
    ):
        raise _PublicationFailure(
            "staging-changed-before-publish",
            backup=None,
            displaced_snapshot=None,
            recovery_status="not-needed",
            recovery_paths=(),
        )
    try:
        pre_publish_scan = scan_delivery_absolute_paths(
            staging,
            root_descriptor=verified_staging.descriptor,
            _include_snapshot=True,
        )
    except PortableError as error:
        raise _PublicationFailure(
            "staging-content-changed-before-publish",
            backup=None,
            displaced_snapshot=None,
            recovery_status="not-needed",
            recovery_paths=(),
        ) from error
    if (
        not isinstance(pre_publish_scan, _PinnedDeliveryScan)
        or pre_publish_scan.findings
        or pre_publish_scan.snapshot != verified_staging.snapshot
    ):
        raise _PublicationFailure(
            "staging-content-changed-before-publish",
            backup=None,
            displaced_snapshot=None,
            recovery_status="not-needed",
            recovery_paths=(),
        )
    backup: Path | None = None
    displaced_snapshot: DestinationSnapshot | None = None
    if _path_exists_no_follow(destination):
        backup = _vacant_sibling(destination, label="backup")
        os.replace(destination, backup)
        try:
            displaced_snapshot = _capture_destination_snapshot(backup)
        except BuildRefusedError as error:
            _raise_publication_failure(
                "destination-changed-during-publish:cannot-snapshot-displaced-tree",
                destination=destination,
                backup=backup,
                displaced_snapshot=None,
                restored_status="concurrent-destination-restored",
                cause=error,
            )

    if (
        backup is None and expected_destination.existed
    ) or (
        backup is not None
        and (
            not expected_destination.existed
            or displaced_snapshot != expected_destination
        )
    ):
        _raise_publication_failure(
            "destination-changed-during-publish",
            destination=destination,
            backup=backup,
            displaced_snapshot=displaced_snapshot,
            restored_status=(
                "concurrent-destination-restored"
                if backup is not None
                else "manual-recovery-required"
            ),
        )

    try:
        os.replace(staging, destination)
    except OSError as error:
        _raise_publication_failure(
            "publication-swap-failed",
            destination=destination,
            backup=backup,
            displaced_snapshot=displaced_snapshot,
            restored_status=(
                "previous-destination-restored"
                if expected_destination.existed
                else "empty-destination-restored"
            ),
            cause=error,
        )
    # DrvFS invalidates an open directory descriptor after its path is renamed.
    # The descriptor identity was checked immediately before the atomic rename;
    # release it so the destination becomes visible, then bind that path back to
    # the identity returned by the G4 materializer.
    verified_staging.close()
    try:
        published_metadata = destination.lstat()
    except OSError:
        published_metadata = None
    published_content_matches = False
    if (
        published_metadata is not None
        and not stat.S_ISLNK(published_metadata.st_mode)
        and stat.S_ISDIR(published_metadata.st_mode)
        and _destination_root_identity(published_metadata)
        == expected_staging_identity
    ):
        try:
            post_publish_scan = scan_delivery_absolute_paths(
                destination,
                _include_snapshot=True,
            )
        except PortableError:
            post_publish_scan = None
        published_content_matches = (
            isinstance(post_publish_scan, _PinnedDeliveryScan)
            and not post_publish_scan.findings
            and post_publish_scan.snapshot == verified_staging.snapshot
        )
    if not published_content_matches:
        recovery = _recover_failed_publication(
            destination,
            backup,
            expected_destination,
        )
        raise _PublicationFailure(
            "staging-changed-during-publish",
            backup=backup,
            displaced_snapshot=displaced_snapshot,
            recovery_status=recovery.status,
            recovery_paths=recovery.paths,
        )
    return backup


def _remove_tree(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
        shutil.rmtree(path)
    else:
        path.unlink()


def _rollback_publication(destination: Path, backup: Path | None) -> None:
    if _path_exists_no_follow(destination):
        raise OSError(
            f"formal destination must be vacant before rollback: {destination}"
        )
    if backup is not None:
        os.replace(backup, destination)


def _quarantine_publication(destination: Path) -> Path | None:
    if not _path_exists_no_follow(destination):
        return None
    quarantine = _vacant_sibling(destination, label="quarantine")
    os.replace(destination, quarantine)
    return quarantine


def _quarantine_unverified_recovery(destination: Path) -> Path | None:
    if not _path_exists_no_follow(destination):
        return None
    recovery = _vacant_sibling(destination, label="recovery")
    os.replace(destination, recovery)
    return recovery


def _recover_failed_publication(
    destination: Path,
    backup: Path | None,
    expected_destination: DestinationSnapshot,
) -> _RecoveryOutcome:
    retained: list[str] = []
    try:
        quarantine = _quarantine_publication(destination)
    except (OSError, shutil.Error):
        retained.append(str(destination))
        if backup is not None:
            retained.append(str(backup))
        return _RecoveryOutcome(
            "manual-recovery-required", tuple(dict.fromkeys(retained))
        )
    if quarantine is not None:
        retained.append(str(quarantine))

    rollback_error: Exception | None = None
    try:
        _rollback_publication(destination, backup)
    except Exception as error:  # recovery must survive a broken primary rollback hook
        rollback_error = error
        if backup is not None:
            try:
                os.replace(backup, destination)
            except (OSError, shutil.Error):
                retained.append(str(backup))
                return _RecoveryOutcome(
                    "manual-recovery-required", tuple(dict.fromkeys(retained))
                )

    try:
        recovered = _capture_destination_snapshot(destination)
    except BuildRefusedError:
        recovered = None
    if recovered != expected_destination:
        try:
            unverified = _quarantine_unverified_recovery(destination)
        except (OSError, shutil.Error):
            unverified = destination if _path_exists_no_follow(destination) else None
        if unverified is not None:
            retained.append(str(unverified))
        if backup is not None and _path_exists_no_follow(backup):
            retained.append(str(backup))
        return _RecoveryOutcome(
            "manual-recovery-required", tuple(dict.fromkeys(retained))
        )

    if expected_destination.existed:
        status = (
            "previous-destination-restored-after-rollback-error"
            if rollback_error is not None
            else "previous-destination-restored"
        )
    else:
        status = "empty-destination-restored"
    return _RecoveryOutcome(status, tuple(dict.fromkeys(retained)))


def execute_build(plan: BuildPlan, *, resume: bool = False) -> BuildResult:
    """Copy through an isolated staging tree and publish only after baseline checks."""
    try:
        _validate_portable_preflight(plan)
        _validate_canonical_figure_plan(plan)
        _validate_lineage_preflight(plan)
    except BuildRefusedError as error:
        return _build_result(
            plan,
            exit_code=1,
            publishable=False,
            dry_run=False,
            reason=f"build-failed:{type(error).__name__}:{error}",
            difference=_difference_or_error(plan),
        )

    before_write = _difference_or_error(plan)
    if not before_write.is_clean:
        return _build_result(
            plan,
            exit_code=1,
            publishable=False,
            dry_run=False,
            reason="old-package-baseline-changed-before-build",
            difference=before_write,
        )

    sources, _ = _row_groups(plan.required_assets)
    destination_snapshot = _validate_destination(
        plan.destination,
        resume=resume,
        source_rows=sources,
        generated_paths=_declared_generated_paths(plan),
    )
    plan.destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{plan.destination.name}.staging-",
            dir=plan.destination.parent,
        )
    )
    backup: Path | None = None
    written: list[str] = []
    published = False
    verified_staging: _VerifiedStagingHandle | None = None
    unfinalized_staging_descriptor = -1
    try:
        with AnchoredRoot(
            plan.project_root, error_type=BuildRefusedError
        ) as source_anchor:
            for row in sources:
                _copy_asset(plan, row, staging, source_anchor)
                if row.target_path is not None:
                    written.append(row.target_path)

        written.extend(_materialize_lineage_pipeline(plan, staging))
        written.extend(_materialize_docs_pipeline(plan, staging))
        portable_materialization = _materialize_portable_pipeline(plan, staging)
        if not isinstance(
            portable_materialization,
            _PinnedPortableMaterialization,
        ):
            raise BuildRefusedError(
                "portable pipeline did not return its verified staging identity"
            )
        written.extend(portable_materialization.written_paths)
        unfinalized_staging_descriptor = portable_materialization.staging_descriptor
        verified_staging = _finalize_verified_staging(
            plan,
            staging,
            portable_materialization,
        )
        unfinalized_staging_descriptor = -1
        written.extend(
            (
                "00_handoff/verification_report.json",
                "00_handoff/SHA256SUMS.txt",
            )
        )

        after_copy = _difference_or_error(plan)
        if not after_copy.is_clean:
            return _build_result(
                plan,
                exit_code=1,
                publishable=False,
                dry_run=False,
                reason="old-package-baseline-changed-after-copy",
                difference=after_copy,
                written_paths=tuple(written),
            )

        current_destination = _capture_destination_snapshot(plan.destination)
        if current_destination != destination_snapshot:
            return _build_result(
                plan,
                exit_code=1,
                publishable=False,
                dry_run=False,
                reason="destination-changed-before-publish",
                difference=after_copy,
                written_paths=tuple(written),
            )

        try:
            if verified_staging is None:
                raise BuildRefusedError("verified staging identity is unavailable")
            backup = _publish_staging(
                staging,
                plan.destination,
                destination_snapshot,
                verified_staging=verified_staging,
            )
        except _PublicationFailure as error:
            return _build_result(
                plan,
                exit_code=1,
                publishable=False,
                dry_run=False,
                reason=f"build-failed:{type(error).__name__}:{error}",
                difference=_difference_or_error(plan),
                written_paths=tuple(written),
                recovery_status=error.recovery_status,
                recovery_paths=error.recovery_paths,
            )
        published = True
        after_publish = _difference_or_error(plan)
        if not after_publish.is_clean:
            recovery = _recover_failed_publication(
                plan.destination,
                backup,
                destination_snapshot,
            )
            published = False
            return _build_result(
                plan,
                exit_code=1,
                publishable=False,
                dry_run=False,
                reason="old-package-baseline-changed-before-acceptance",
                difference=after_publish,
                written_paths=tuple(written),
                recovery_status=recovery.status,
                recovery_paths=recovery.paths,
            )

        if backup is not None:
            try:
                _remove_tree(backup)
            except (OSError, shutil.Error) as error:
                return _build_result(
                    plan,
                    exit_code=0,
                    publishable=True,
                    dry_run=False,
                    reason=(
                        "built-and-old-package-unchanged;"
                        f"backup-cleanup-failed:{type(error).__name__}:{error}"
                    ),
                    difference=after_publish,
                    written_paths=tuple(written),
                    recovery_status="published-backup-retained",
                    recovery_paths=(str(backup),),
                )
            backup = None
        return _build_result(
            plan,
            exit_code=0,
            publishable=True,
            dry_run=False,
            reason="built-and-old-package-unchanged",
            difference=after_publish,
            written_paths=tuple(written),
        )
    except (BuildRefusedError, OSError, shutil.Error) as error:
        recovery = _RecoveryOutcome("not-needed", ())
        if published:
            try:
                recovery = _recover_failed_publication(
                    plan.destination,
                    backup,
                    destination_snapshot,
                )
                published = False
            except Exception:
                retained = [str(plan.destination)]
                if backup is not None:
                    retained.append(str(backup))
                recovery = _RecoveryOutcome(
                    "manual-recovery-required", tuple(retained)
                )
        return _build_result(
            plan,
            exit_code=1,
            publishable=False,
            dry_run=False,
            reason=f"build-failed:{type(error).__name__}:{error}",
            difference=_difference_or_error(plan),
            written_paths=tuple(written),
            recovery_status=recovery.status,
            recovery_paths=recovery.paths,
        )
    finally:
        if verified_staging is not None:
            verified_staging.close()
        elif unfinalized_staging_descriptor >= 0:
            os.close(unfinalized_staging_descriptor)
        if _path_exists_no_follow(staging):
            try:
                _remove_tree(staging)
            except (OSError, shutil.Error):
                pass


def build_delivery(
    *,
    project_root: Path | str,
    old_delivery: Path | str,
    destination: Path | str,
    dry_run: bool = False,
    resume: bool = False,
    tree_specs: Sequence[TreeSourceSpec] = TREE_SOURCE_SPECS,
    exact_specs: Sequence[ExactSourceSpec] = EXACT_SOURCE_SPECS,
    include_thesis_assets: bool = True,
    manifest_keys: ManifestKeys | None = None,
    derived_recipes: Sequence[DerivedRecipe] = (),
    redraw_recipes: Sequence[RedrawRecipe] = (),
    portable_contract: PortableContract | None = None,
    docs_config: DocsConfig | None = None,
) -> BuildResult:
    """Prepare and either dry-run or execute one deterministic delivery build."""
    plan = prepare_build(
        project_root=project_root,
        old_delivery=old_delivery,
        destination=destination,
        tree_specs=tree_specs,
        exact_specs=exact_specs,
        include_thesis_assets=include_thesis_assets,
        manifest_keys=manifest_keys,
        derived_recipes=derived_recipes,
        redraw_recipes=redraw_recipes,
        portable_contract=portable_contract,
        docs_config=docs_config,
    )
    if dry_run:
        difference = _difference_or_error(plan)
        return _build_result(
            plan,
            exit_code=0 if difference.is_clean else 1,
            publishable=False,
            dry_run=True,
            reason=(
                "dry-run-complete"
                if difference.is_clean
                else "old-package-baseline-changed-during-dry-run"
            ),
            difference=difference,
        )
    return execute_build(plan, resume=resume)


def build_production_delivery(
    *,
    project_root: Path | str,
    old_delivery: Path | str,
    destination: Path | str,
    dry_run: bool = False,
    resume: bool = False,
) -> BuildResult:
    """Assemble canonical production inputs, then use the sole builder path."""
    project = Path(project_root).absolute()
    inventory = enumerate_required_assets(project)
    portable_contract = assemble_portable_contract(project, inventory)
    return build_delivery(
        project_root=project,
        old_delivery=old_delivery,
        destination=destination,
        dry_run=dry_run,
        resume=resume,
        portable_contract=portable_contract,
    )
