"""Isolated figure input-validation and representative-redraw executor."""

from __future__ import annotations

from collections.abc import Iterable
import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
from typing import Any

import numpy as np

from .lineage import FigureRecipe, STORY_MODULES, route_figure
from .models import IdList, ManifestError, require_relative_path


ACTIVE_MODULES = STORY_MODULES
NUMERIC_SUFFIXES = frozenset({".npy", ".npz", ".csv"})
IMAGE_SUFFIXES = frozenset({".png", ".svg", ".pdf"})


class RedrawError(RuntimeError):
    """Raised when redraw execution or its evidence cannot be trusted."""


def _relative(raw: str, field_name: str) -> str:
    try:
        return require_relative_path(raw).as_posix()
    except ManifestError as error:
        raise RedrawError(f"{field_name}: {error}") from error


def _input_paths(raw: str) -> tuple[str, ...]:
    if not raw or raw == "N/A":
        raise RedrawError("input_paths must declare at least one staged input")
    paths = tuple(_relative(item, "input_paths") for item in raw.split(";"))
    if len(set(paths)) != len(paths):
        raise RedrawError("input_paths must not contain duplicates")
    return paths


def _parse_tolerance(raw: str) -> tuple[float, float]:
    parts = raw.split(";")
    if len(parts) != 2:
        raise RedrawError("numeric tolerance must declare rtol and atol")
    parsed: dict[str, float] = {}
    for part in parts:
        key, separator, value = part.partition("=")
        if not separator or key not in {"rtol", "atol"} or key in parsed:
            raise RedrawError("numeric tolerance must declare unique rtol and atol")
        try:
            number = float(value)
        except ValueError as error:
            raise RedrawError("numeric tolerance values must be finite numbers") from error
        if not math.isfinite(number) or number < 0:
            raise RedrawError("numeric tolerance values must be finite and nonnegative")
        parsed[key] = number
    if set(parsed) != {"rtol", "atol"}:
        raise RedrawError("numeric tolerance must declare rtol and atol")
    return parsed["rtol"], parsed["atol"]


@dataclass(frozen=True, slots=True)
class RedrawRecipe:
    redraw_id: str
    figure_id: str
    module: str
    script_path: str
    command: str
    input_data_ids: str
    input_paths: str
    output_path: str
    reference_product_path: str
    comparison_method: str
    tolerance: str
    environment_command: str
    representative: bool
    notes: str

    def __post_init__(self) -> None:
        for field_name in ("redraw_id", "figure_id"):
            value = getattr(self, field_name)
            if not value or ";" in value or any(character.isspace() for character in value):
                raise RedrawError(
                    f"{field_name} must be a non-empty ID without whitespace"
                )
        if self.module not in ACTIVE_MODULES:
            raise RedrawError(f"unknown active module: {self.module!r}")
        script = _relative(self.script_path, "script_path")
        inputs = _input_paths(self.input_paths)
        if self.input_data_ids != "N/A":
            try:
                IdList.parse(self.input_data_ids)
            except ManifestError as error:
                raise RedrawError(f"input_data_ids: {error}") from error
        if not self.environment_command or any(
            character.isspace() for character in self.environment_command
        ):
            raise RedrawError("environment_command must be one executable token")
        try:
            command = tuple(shlex.split(self.command, posix=True))
        except ValueError as error:
            raise RedrawError("command is not valid shell-style token text") from error
        if not command or command[0] != self.environment_command:
            raise RedrawError("command must start with environment_command")
        if len(command) < 2 or command[1] != script:
            raise RedrawError(
                "command argv[1] must be the declared script_path"
            )
        missing_input_arguments = sorted(set(inputs) - set(command[2:]))
        if missing_input_arguments:
            raise RedrawError(
                "command must pass every declared input path; "
                f"missing={missing_input_arguments!r}"
            )

        validation_only = self.output_path == "N/A" and self.reference_product_path == "N/A"
        if (self.output_path == "N/A") != (self.reference_product_path == "N/A"):
            raise RedrawError(
                "output_path and reference_product_path must both be N/A or both be paths"
            )
        if validation_only:
            if self.representative:
                raise RedrawError("representative redraw must produce a comparison product")
            if self.comparison_method != "input_hash_validation" or self.tolerance != "exact":
                raise RedrawError(
                    "validation-only command requires input_hash_validation and exact tolerance"
                )
        else:
            output = _relative(self.output_path, "output_path")
            reference = _relative(
                self.reference_product_path, "reference_product_path"
            )
            if output in {*inputs, script, reference}:
                raise RedrawError("redraw output must be newly created in isolation")
            if output not in command[2:]:
                raise RedrawError("command must pass the declared output_path")
            if reference in {*inputs, script}:
                raise RedrawError(
                    "reference product must be distinct from script and staged inputs"
                )
            suffix = Path(reference).suffix.casefold()
            if suffix in NUMERIC_SUFFIXES:
                if self.comparison_method != "numpy.testing.assert_allclose":
                    raise RedrawError(
                        "numeric products require numpy.testing.assert_allclose"
                    )
                _parse_tolerance(self.tolerance)
            elif suffix in IMAGE_SUFFIXES:
                if self.comparison_method != "sha256_exact" or self.tolerance != "exact":
                    raise RedrawError(
                        "image products require a predeclared sha256_exact/exact comparison"
                    )
            else:
                raise RedrawError("unsupported redraw comparison-product format")
        if not isinstance(self.representative, bool):
            raise RedrawError("representative must be a boolean")
        if not self.notes:
            raise RedrawError("notes must describe the validation/redraw purpose")

    @property
    def inputs(self) -> tuple[str, ...]:
        return _input_paths(self.input_paths)

    @property
    def validation_only(self) -> bool:
        return self.output_path == "N/A"


@dataclass(frozen=True, slots=True)
class RedrawEvidence:
    redraw_id: str
    figure_id: str
    module: str
    command: str
    environment_command: str
    input_data_ids: str
    environment: dict[str, str]
    input_sha256: dict[str, str]
    script_sha256: str
    output_sha256: str
    reference_sha256: str
    comparison_method: str
    tolerance: str
    result: str
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str
    started_at_ns: int
    started_monotonic_ns: int
    raw_output_mtime_ns: int
    filesystem_clock_offset_ns: int
    filesystem_clock_uncertainty_ns: int
    output_mtime_ns: int
    finished_at_ns: int
    finished_monotonic_ns: int
    evidence_written_at_ns: int
    build_token: str


def validate_redraw_plan(
    figure_rows: Iterable[FigureRecipe],
    recipes: Iterable[RedrawRecipe],
    *,
    required_modules: Iterable[str] = ACTIVE_MODULES,
    figure_targets: dict[str, str] | None = None,
    data_paths: dict[str, str] | None = None,
    executable_fields_prevalidated: bool = False,
) -> None:
    """Require one validation command per canonical figure and module redraw coverage."""
    figures = tuple(figure_rows)
    redraws = tuple(recipes)
    expected = {
        row.figure_id for row in figures if row.usage_status in {"formal", "current_only"}
    }
    actual_list = [row.figure_id for row in redraws]
    actual = set(actual_list)
    if len(actual) != len(actual_list) or actual != expected:
        raise RedrawError(
            "figure coverage mismatch; "
            f"missing={sorted(expected - actual)!r}; extra={sorted(actual - expected)!r}"
        )
    redraw_ids = [row.redraw_id for row in redraws]
    if len(set(redraw_ids)) != len(redraw_ids):
        raise RedrawError("redraw IDs must be unique")

    by_figure = {row.figure_id: row for row in figures}
    representative_modules: set[str] = set()
    for recipe in redraws:
        figure = by_figure[recipe.figure_id]
        if recipe.module != figure.story_module:
            raise RedrawError(
                f"{recipe.redraw_id}: story module does not match figure ledger"
            )
        if recipe.input_data_ids != figure.input_data_ids:
            raise RedrawError(
                f"{recipe.redraw_id}: input data IDs do not match figure ledger"
            )
        input_ids = (
            ()
            if figure.input_data_ids == "N/A"
            else IdList.parse(figure.input_data_ids).items
        )
        if input_ids and data_paths is None:
            raise RedrawError(
                f"{recipe.redraw_id}: declared input data require data manifest paths"
            )
        expected_input_paths: set[str] = set()
        if input_ids:
            if data_paths is None:
                raise RedrawError(
                    f"{recipe.redraw_id}: declared input data require data manifest paths"
                )
            missing_ids = sorted(set(input_ids) - set(data_paths))
            if missing_ids:
                raise RedrawError(
                    f"{recipe.redraw_id}: data manifest has no paths for {missing_ids!r}"
                )
            expected_input_paths.update(data_paths[data_id] for data_id in input_ids)
        if recipe.validation_only:
            expected_figure_path = (
                figure.figure_path
                if figure_targets is None
                else figure_targets[figure.figure_id]
            )
            if expected_figure_path not in recipe.inputs:
                raise RedrawError(
                    f"{recipe.redraw_id}: validation-only recipe must hash its figure asset"
                )
            expected_input_paths.add(expected_figure_path)
        if expected_input_paths != set(recipe.inputs):
            raise RedrawError(
                f"{recipe.redraw_id}: redraw inputs must exactly match "
                "data manifest paths and routed figure requirements"
            )
        is_active_numeric = (
            figure.scientific_status == "valid"
            and route_figure(figure) == "active"
            and figure.provenance_type in {"simulation", "theory"}
        )
        if is_active_numeric:
            if recipe.validation_only:
                raise RedrawError(
                    f"{recipe.redraw_id}: active numeric figure requires an actual redraw"
                )
            if data_paths is None:
                raise RedrawError(
                    f"{recipe.redraw_id}: active numeric redraw requires data manifest paths"
                )
            reference_data_id = figure.comparison_reference_data_id
            if reference_data_id == "N/A" or reference_data_id not in data_paths:
                raise RedrawError(
                    f"{recipe.redraw_id}: reference product has no declared data manifest ID"
                )
            if recipe.reference_product_path != data_paths[reference_data_id]:
                raise RedrawError(
                    f"{recipe.redraw_id}: reference product does not match its data manifest path"
                )
            expected_fields = {
                "comparison_method": figure.comparison_method,
                "tolerance": figure.tolerance,
            }
            if not executable_fields_prevalidated:
                expected_fields["script_path"] = figure.plot_script_path
            labels = {
                "script_path": "plot script",
                "comparison_method": "comparison method",
                "tolerance": "tolerance",
            }
            for field_name, expected_value in expected_fields.items():
                if getattr(recipe, field_name) != expected_value:
                    raise RedrawError(
                        f"{recipe.redraw_id}: {labels[field_name]} does not match figure ledger"
                    )
            if (
                not executable_fields_prevalidated
                and recipe.command != figure.plot_command
            ):
                raise RedrawError(
                    f"{recipe.redraw_id}: plot command does not match figure ledger"
                )
        if not recipe.representative:
            continue
        if figure.scientific_status != "valid" or route_figure(figure) != "active":
            raise RedrawError(
                f"{recipe.redraw_id}: representative redraw uses a non-active figure"
            )
        representative_modules.add(recipe.module)
    required_module_set = set(required_modules)
    unknown_required = required_module_set - set(ACTIVE_MODULES)
    if unknown_required:
        raise RedrawError(
            f"unknown required redraw modules: {sorted(unknown_required)!r}"
        )
    missing_modules = required_module_set - representative_modules
    if missing_modules:
        raise RedrawError(
            f"missing representative redraw for modules: {sorted(missing_modules)!r}"
        )


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_snapshot(root: Path) -> tuple[tuple[str, str, int, str], ...]:
    """Hash one real tree without accepting symlinks or special files."""
    rows: list[tuple[str, str, int, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        try:
            metadata = path.lstat()
        except OSError as error:
            raise RedrawError(f"cannot snapshot redraw tree: {relative}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise RedrawError(f"redraw tree contains a symlink: {relative}")
        if stat.S_ISDIR(metadata.st_mode):
            rows.append((relative, "directory", 0, ""))
        elif stat.S_ISREG(metadata.st_mode):
            rows.append((relative, "file", metadata.st_size, _hash_file(path)))
        else:
            raise RedrawError(f"redraw tree contains a special file: {relative}")
    return tuple(rows)


def _staged_regular(root: Path, raw: str) -> Path:
    relative = require_relative_path(raw)
    current = root
    for index, part in enumerate(relative.parts):
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as error:
            raise RedrawError(f"missing staged path: {raw}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise RedrawError(f"staged path contains a symlink: {raw}")
        if index < len(relative.parts) - 1:
            if not stat.S_ISDIR(metadata.st_mode):
                raise RedrawError(f"staged path ancestor is not a directory: {raw}")
        elif not stat.S_ISREG(metadata.st_mode):
            raise RedrawError(f"staged input is not a regular file: {raw}")
    return current


def _safe_staging_output(root: Path, raw: str) -> Path:
    """Create real parent directories without following staging-tree symlinks."""
    relative = require_relative_path(raw)
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            try:
                current.mkdir()
                metadata = current.lstat()
            except OSError as error:
                raise RedrawError(
                    f"cannot create redraw evidence directory: {raw}"
                ) from error
        except OSError as error:
            raise RedrawError(f"cannot inspect redraw evidence path: {raw}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise RedrawError(f"redraw evidence path contains a symlink: {raw}")
        if not stat.S_ISDIR(metadata.st_mode):
            raise RedrawError(
                f"redraw evidence ancestor is not a directory: {raw}"
            )
    target = current / relative.parts[-1]
    try:
        target.lstat()
    except FileNotFoundError:
        return target
    except OSError as error:
        raise RedrawError(f"cannot inspect redraw evidence target: {raw}") from error
    raise RedrawError(f"redraw evidence already exists: {target}")


def _copy_staged(root: Path, workspace: Path, raw: str) -> str:
    source = _staged_regular(root, raw)
    digest = _hash_file(source)
    target = workspace / raw
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target, follow_symlinks=False)
    if _hash_file(target) != digest:
        raise RedrawError(f"isolated copy changed bytes: {raw}")
    return digest


def _require_unchanged_workspace_file(
    workspace: Path,
    raw: str,
    expected_sha256: str,
    *,
    label: str,
) -> None:
    path = _staged_regular(workspace, raw)
    if _hash_file(path) != expected_sha256:
        raise RedrawError(f"{label} changed during redraw execution: {raw}")


def _load_numeric(path: Path) -> Any:
    suffix = path.suffix.casefold()
    if suffix == ".npy":
        return np.load(path, allow_pickle=False)
    if suffix == ".npz":
        with np.load(path, allow_pickle=False) as archive:
            return {name: np.array(archive[name], copy=True) for name in archive.files}
    if suffix == ".csv":
        array = np.genfromtxt(path, delimiter=",", names=True)
        if array.dtype.names:
            return np.column_stack([array[name] for name in array.dtype.names])
        return np.asarray(array)
    raise RedrawError(f"unsupported numeric product: {path}")


def _assert_numeric_close(output: Path, reference: Path, tolerance: str) -> None:
    rtol, atol = _parse_tolerance(tolerance)
    actual = _load_numeric(output)
    expected = _load_numeric(reference)
    try:
        if isinstance(actual, dict) or isinstance(expected, dict):
            if not isinstance(actual, dict) or not isinstance(expected, dict):
                raise AssertionError("numeric container types differ")
            if set(actual) != set(expected):
                raise AssertionError("NPZ array keys differ")
            for key in sorted(actual):
                np.testing.assert_allclose(
                    actual[key], expected[key], rtol=rtol, atol=atol
                )
        else:
            np.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol)
    except (AssertionError, TypeError, ValueError) as error:
        raise RedrawError(f"numeric redraw comparison failed: {error}") from error


def _validate_staging_marker(staging: Path, build_token: str) -> None:
    if not build_token:
        raise RedrawError("build token must not be empty")
    try:
        metadata = staging.lstat()
    except OSError as error:
        raise RedrawError(f"cannot inspect staging root: {staging}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RedrawError("staging root must be a real directory")
    marker = staging / ".handoff-staging"
    try:
        marker_metadata = marker.lstat()
        payload = marker.read_text(encoding="utf-8")
    except OSError as error:
        raise RedrawError("missing or unreadable staging marker") from error
    if (
        stat.S_ISLNK(marker_metadata.st_mode)
        or not stat.S_ISREG(marker_metadata.st_mode)
        or payload != build_token + "\n"
    ):
        raise RedrawError("staging marker does not match the current build token")


def _calibrate_filesystem_clock(workspace: Path) -> tuple[int, int]:
    """Estimate mounted-filesystem clock offset without hiding its uncertainty."""
    probe = workspace / ".filesystem-clock-probe"
    before_wall = time.time_ns()
    before_monotonic = time.monotonic_ns()
    descriptor = -1
    try:
        descriptor = os.open(
            probe,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(b"clock probe\n")
            handle.flush()
            os.fsync(handle.fileno())
        probe_mtime_ns = probe.stat().st_mtime_ns
    except OSError as error:
        raise RedrawError("cannot calibrate staging filesystem clock") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    after_wall = time.time_ns()
    after_monotonic = time.monotonic_ns()
    probe.unlink()
    elapsed = max(0, after_monotonic - before_monotonic)
    midpoint = before_wall + elapsed // 2
    wall_discontinuity = abs((after_wall - before_wall) - elapsed)
    uncertainty = max(1, elapsed // 2 + wall_discontinuity)
    return probe_mtime_ns - midpoint, uncertainty


def _sandbox_command(
    recipe: RedrawRecipe,
    workspace: Path,
    command: list[str],
) -> tuple[list[str], dict[str, str]]:
    """Expose only the isolated workspace and exact read-only runtimes."""
    bwrap = Path("/usr/bin/bwrap")
    if not bwrap.is_file():
        raise RedrawError("bubblewrap is required for isolated redraw execution")
    executable = Path(recipe.environment_command)
    if not executable.is_absolute():
        raise RedrawError("environment_command must be an absolute executable path")

    sandbox_executable = recipe.environment_command
    runtime_arguments: list[str] = []
    candidate_runtime = executable.parent.parent
    if (candidate_runtime / "pyvenv.cfg").is_file():
        runtime_arguments = ["--ro-bind", str(candidate_runtime), "/runtime"]
        sandbox_executable = f"/runtime/{executable.relative_to(candidate_runtime)}"
    elif not (
        executable.is_relative_to("/usr") or executable.is_relative_to("/bin")
    ):
        raise RedrawError(
            "redraw executable must be under /usr, /bin, or a declared Python venv"
        )

    isolated_command = [sandbox_executable, *command[1:]]
    arguments = [
        str(bwrap),
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind",
        "/lib64",
        "/lib64",
        "--dir",
        "/etc",
        "--ro-bind",
        "/etc/alternatives",
        "/etc/alternatives",
        *runtime_arguments,
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/tmp/home",
        "--dir",
        "/tmp/mpl",
        "--bind",
        str(workspace),
        "/work",
        "--chdir",
        "/work",
        "--setenv",
        "HOME",
        "/tmp/home",
        "--setenv",
        "MPLCONFIGDIR",
        "/tmp/mpl",
        "--setenv",
        "MPLBACKEND",
        "Agg",
        "--setenv",
        "PYTHONHASHSEED",
        "0",
        "--setenv",
        "PATH",
        "/runtime/bin:/usr/bin:/bin",
        "--",
        *isolated_command,
    ]
    return arguments, {"PATH": "/usr/bin:/bin"}


def _execute_one(
    recipe: RedrawRecipe,
    *,
    staging: Path,
    build_token: str,
) -> RedrawEvidence:
    workspace = Path(
        tempfile.mkdtemp(prefix=f".redraw-{recipe.redraw_id}-", dir=staging.parent)
    )
    reference_workspace = Path(
        tempfile.mkdtemp(
            prefix=f".redraw-reference-{recipe.redraw_id}-",
            dir=staging.parent,
        )
    )
    try:
        script_sha256 = _copy_staged(staging, workspace, recipe.script_path)
        input_sha256 = {
            path: _copy_staged(staging, workspace, path) for path in recipe.inputs
        }
        reference_sha256 = "N/A"
        if not recipe.validation_only:
            reference_sha256 = _copy_staged(
                staging, reference_workspace, recipe.reference_product_path
            )

        output = None if recipe.validation_only else workspace / recipe.output_path
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                raise RedrawError("isolated redraw output existed before execution")

        environment_evidence = {
            "executable": recipe.environment_command,
            "sandbox": "/usr/bin/bwrap --unshare-all",
            "MPLBACKEND": "Agg",
            "PYTHONHASHSEED": "0",
        }
        command = shlex.split(recipe.command, posix=True)
        filesystem_clock_offset_ns, filesystem_clock_uncertainty_ns = (
            _calibrate_filesystem_clock(workspace)
        )
        workspace_before = _tree_snapshot(workspace)
        started_at_ns = time.time_ns()
        started_monotonic_ns = time.monotonic_ns()
        sandbox_command, sandbox_environment = _sandbox_command(
            recipe, workspace, command
        )
        try:
            completed = subprocess.run(
                sandbox_command,
                cwd="/",
                env=sandbox_environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise RedrawError(f"cannot execute redraw command: {error}") from error
        finished_at_ns = time.time_ns()
        finished_monotonic_ns = time.monotonic_ns()
        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace")[-500:]
            raise RedrawError(
                f"redraw command failed with exit {completed.returncode}: {stderr}"
            )

        _require_unchanged_workspace_file(
            workspace,
            recipe.script_path,
            script_sha256,
            label="redraw script",
        )
        for input_path, input_digest in input_sha256.items():
            _require_unchanged_workspace_file(
                workspace,
                input_path,
                input_digest,
                label="staged input",
            )
        if not recipe.validation_only:
            _require_unchanged_workspace_file(
                reference_workspace,
                recipe.reference_product_path,
                reference_sha256,
                label="reference product",
            )

        output_sha256 = "N/A"
        raw_output_mtime_ns = 0
        output_mtime_ns = 0
        if output is not None:
            try:
                output_metadata = output.lstat()
            except OSError as error:
                raise RedrawError("redraw command produced no declared output") from error
            if stat.S_ISLNK(output_metadata.st_mode) or not stat.S_ISREG(
                output_metadata.st_mode
            ):
                raise RedrawError("redraw output is not a regular file")
            raw_output_mtime_ns = output_metadata.st_mtime_ns
            normalised_mtime_ns = (
                raw_output_mtime_ns - filesystem_clock_offset_ns
            )
            output_mtime_ns = normalised_mtime_ns
            reference = reference_workspace / recipe.reference_product_path
            output_sha256 = _hash_file(output)
            if recipe.comparison_method == "numpy.testing.assert_allclose":
                _assert_numeric_close(output, reference, recipe.tolerance)
            elif output_sha256 != reference_sha256:
                raise RedrawError("image redraw SHA256 comparison failed")

        expected_workspace = set(workspace_before)
        if output is not None:
            expected_workspace.add(
                (
                    recipe.output_path,
                    "file",
                    output.stat().st_size,
                    output_sha256,
                )
            )
        if set(_tree_snapshot(workspace)) != expected_workspace:
            raise RedrawError("redraw command created undeclared workspace artifacts")

        evidence_written_at_ns = time.time_ns()
        return RedrawEvidence(
            redraw_id=recipe.redraw_id,
            figure_id=recipe.figure_id,
            module=recipe.module,
            command=recipe.command,
            environment_command=recipe.environment_command,
            input_data_ids=recipe.input_data_ids,
            environment=environment_evidence,
            input_sha256=input_sha256,
            script_sha256=script_sha256,
            output_sha256=output_sha256,
            reference_sha256=reference_sha256,
            comparison_method=recipe.comparison_method,
            tolerance=recipe.tolerance,
            result="PASS",
            exit_code=completed.returncode,
            stdout_sha256=_hash_bytes(completed.stdout),
            stderr_sha256=_hash_bytes(completed.stderr),
            started_at_ns=started_at_ns,
            started_monotonic_ns=started_monotonic_ns,
            raw_output_mtime_ns=raw_output_mtime_ns,
            filesystem_clock_offset_ns=filesystem_clock_offset_ns,
            filesystem_clock_uncertainty_ns=filesystem_clock_uncertainty_ns,
            output_mtime_ns=output_mtime_ns,
            finished_at_ns=finished_at_ns,
            finished_monotonic_ns=finished_monotonic_ns,
            evidence_written_at_ns=evidence_written_at_ns,
            build_token=build_token,
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=False)
        shutil.rmtree(reference_workspace, ignore_errors=False)


def _write_evidence(path: Path, rows: tuple[RedrawEvidence, ...]) -> None:
    fieldnames = tuple(RedrawEvidence.__dataclass_fields__)
    temporary = path.with_name(f".{path.name}.writing")
    try:
        temporary.lstat()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise RedrawError(
            f"cannot inspect redraw evidence temporary: {temporary}"
        ) from error
    else:
        raise RedrawError(f"stale redraw evidence temporary exists: {temporary}")
    try:
        with temporary.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                serialized = asdict(row)
                serialized["environment"] = json.dumps(
                    row.environment, sort_keys=True, separators=(",", ":")
                )
                serialized["input_sha256"] = json.dumps(
                    row.input_sha256, sort_keys=True, separators=(",", ":")
                )
                writer.writerow(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def execute_redraws(
    recipes: Iterable[RedrawRecipe],
    *,
    staging_root: Path | str,
    build_token: str,
    evidence_path: Path | str | None = None,
) -> tuple[RedrawEvidence, ...]:
    """Run all commands in disposable workspaces and optionally write one ledger."""
    staging = Path(staging_root)
    _validate_staging_marker(staging, build_token)
    staging_before = _tree_snapshot(staging)
    recipe_rows = tuple(recipes)
    ids = [recipe.redraw_id for recipe in recipe_rows]
    if len(ids) != len(set(ids)):
        raise RedrawError("redraw IDs must be unique")
    evidence = tuple(
        _execute_one(recipe, staging=staging, build_token=build_token)
        for recipe in recipe_rows
    )
    validate_redraw_evidence(recipe_rows, evidence, build_token=build_token)
    if _tree_snapshot(staging) != staging_before:
        raise RedrawError("staging tree changed during redraw execution")
    if evidence_path is not None:
        staging_absolute = staging.absolute()
        target_absolute = Path(evidence_path).absolute()
        try:
            relative = target_absolute.relative_to(staging_absolute).as_posix()
            require_relative_path(relative)
        except (ManifestError, ValueError) as error:
            raise RedrawError("redraw evidence path must be inside staging") from error
        target = _safe_staging_output(staging, relative)
        _write_evidence(target, evidence)
    return evidence


def validate_redraw_evidence(
    recipes: Iterable[RedrawRecipe],
    evidence_rows: Iterable[RedrawEvidence],
    *,
    build_token: str,
) -> None:
    """Validate executor-created evidence against the predeclared recipe set."""
    recipe_tuple = tuple(recipes)
    evidence_tuple = tuple(evidence_rows)
    recipe_by_id = {row.redraw_id: row for row in recipe_tuple}
    evidence_by_id = {row.redraw_id: row for row in evidence_tuple}
    if len(recipe_by_id) != len(recipe_tuple) or len(evidence_by_id) != len(
        evidence_tuple
    ):
        raise RedrawError("redraw/evidence IDs must be unique")
    if set(recipe_by_id) != set(evidence_by_id):
        raise RedrawError(
            "evidence coverage mismatch; "
            f"missing={sorted(set(recipe_by_id) - set(evidence_by_id))!r}; "
            f"extra={sorted(set(evidence_by_id) - set(recipe_by_id))!r}"
        )
    now = time.time_ns()
    for redraw_id, recipe in recipe_by_id.items():
        evidence = evidence_by_id[redraw_id]
        if evidence.build_token != build_token:
            raise RedrawError(f"{redraw_id}: evidence build token mismatch")
        expected = {
            "figure_id": recipe.figure_id,
            "module": recipe.module,
            "command": recipe.command,
            "environment_command": recipe.environment_command,
            "input_data_ids": recipe.input_data_ids,
            "comparison_method": recipe.comparison_method,
            "tolerance": recipe.tolerance,
        }
        for field_name, value in expected.items():
            if getattr(evidence, field_name) != value:
                raise RedrawError(f"{redraw_id}: evidence {field_name} mismatch")
        if set(evidence.input_sha256) != set(recipe.inputs):
            raise RedrawError(f"{redraw_id}: evidence input set mismatch")
        if evidence.result != "PASS" or evidence.exit_code != 0:
            raise RedrawError(f"{redraw_id}: evidence result must be PASS with exit 0")
        if not evidence.environment:
            raise RedrawError(f"{redraw_id}: environment evidence is empty")
        if not (
            0
            < evidence.started_monotonic_ns
            <= evidence.finished_monotonic_ns
        ):
            raise RedrawError(
                f"{redraw_id}: monotonic evidence timestamps are inconsistent"
            )
        if evidence.evidence_written_at_ns > now + 5_000_000_000:
            raise RedrawError(f"{redraw_id}: evidence timestamp is in the future")
        if recipe.validation_only:
            if (
                evidence.raw_output_mtime_ns != 0
                or evidence.output_mtime_ns != 0
                or evidence.output_sha256 != "N/A"
            ):
                raise RedrawError(f"{redraw_id}: validation-only evidence has output")
        else:
            if (
                evidence.raw_output_mtime_ns <= 0
                or evidence.output_mtime_ns
                != evidence.raw_output_mtime_ns
                - evidence.filesystem_clock_offset_ns
            ):
                raise RedrawError(
                    f"{redraw_id}: calibrated output timestamp is inconsistent"
                )
