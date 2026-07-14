"""Non-destructive construction primitives for the Hopfion v2 handoff tree."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
from typing import Literal

from .models import ManifestError, require_relative_path
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


def prepare_build(
    *,
    project_root: Path | str,
    old_delivery: Path | str,
    destination: Path | str,
    tree_specs: Sequence[TreeSourceSpec] = TREE_SOURCE_SPECS,
    exact_specs: Sequence[ExactSourceSpec] = EXACT_SOURCE_SPECS,
    include_thesis_assets: bool = True,
) -> BuildPlan:
    """Prepare an immutable build plan without writing the v2 destination."""
    project = Path(project_root).absolute()
    old = Path(old_delivery).absolute()
    target = Path(destination).absolute()
    baseline = capture_baseline(old)
    inventory = enumerate_required_assets(
        project,
        tree_specs=tree_specs,
        exact_specs=exact_specs,
        include_thesis_assets=include_thesis_assets,
    )

    resolved_old = old.resolve()
    resolved_target = target.resolve(strict=False)
    if resolved_target == resolved_old or resolved_old in resolved_target.parents:
        raise BuildRefusedError("v2 destination must not be inside the old delivery")
    return BuildPlan(project, old, target, inventory, baseline)


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
) -> tuple[dict[str, RequiredAssetRow], frozenset[str]]:
    allowed_files: dict[str, RequiredAssetRow] = {}
    allowed_directories: set[str] = set()
    for row in source_rows:
        if row.target_path is None:
            raise BuildRefusedError(
                f"copied row has no mapped target: {row.source_path}"
            )
        relative = PurePosixPath(row.target_path)
        allowed_files[row.target_path] = row
        for parent in relative.parents:
            if parent != PurePosixPath("."):
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


def _validate_resume_contents(
    destination: Path,
    source_rows: Sequence[RequiredAssetRow],
) -> None:
    allowed_files, allowed_directories = _resume_allowlist(source_rows)
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
            row = allowed_files.get(relative)
            if row is None:
                raise BuildRefusedError(
                    f"resume destination contains unknown file: {relative}"
                )
            _validate_resume_file(path, row)


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
        _validate_resume_contents(destination, source_rows)
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
) -> Path | None:
    """Publish only if the atomically displaced destination matches validation."""
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
    try:
        with AnchoredRoot(
            plan.project_root, error_type=BuildRefusedError
        ) as source_anchor:
            for row in sources:
                _copy_asset(plan, row, staging, source_anchor)
                if row.target_path is not None:
                    written.append(row.target_path)

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
            backup = _publish_staging(
                staging,
                plan.destination,
                destination_snapshot,
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
) -> BuildResult:
    """Prepare and either dry-run or execute one deterministic delivery build."""
    plan = prepare_build(
        project_root=project_root,
        old_delivery=old_delivery,
        destination=destination,
        tree_specs=tree_specs,
        exact_specs=exact_specs,
        include_thesis_assets=include_thesis_assets,
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
