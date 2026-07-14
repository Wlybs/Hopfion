"""Deterministic producers for minimal, figure-specific derived data.

This module never copies an OVF into a delivery.  A source field may only be read
to emit a recipe-bounded slice, line, or scalar, with hashes checked before any
output is created.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any
import zipfile

import numpy as np

from .models import IdList, ManifestError, require_relative_path
from .source_specs import AnchoredRoot


HOPFION_ENVIRONMENT_COMMAND = "/mnt/d/Research/Hopfion/hopfion/bin/python"
DERIVED_PRODUCER_SCRIPT = "95_shared_scripts/handoff_delivery/derived.py"
ALLOWED_SELECTORS = frozenset({"slice", "line", "scalar"})
ALLOWED_OUTPUT_FORMATS = frozenset({"csv", "npz"})
SHA256_LENGTH = 64
SHAPE_PATTERN = re.compile(r"[1-9][0-9]*(?:x[1-9][0-9]*)*\Z")
MIN_COMPLETE_FIELD_POINTS = 100_000
OVF_MESHUNIT_PATTERN = re.compile(
    rb"(?im)^#\s*meshunit\s*:\s*([^\r\n#]+?)\s*$"
)
MAX_OVF_HEADER_BYTES = 1024 * 1024


class DerivedDataError(RuntimeError):
    """Raised when derived data cannot be proven recipe-generated and minimal."""


def _require_sha256(value: str, field_name: str) -> None:
    if len(value) != SHA256_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise DerivedDataError(f"{field_name} must be a lowercase SHA256 digest")


def _parse_json(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON token: {token}")
            ),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise DerivedDataError("selector_json must be valid canonical JSON") from error
    if not isinstance(value, dict):
        raise DerivedDataError("selector_json must contain one JSON object")
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    if canonical != raw:
        raise DerivedDataError("selector_json must use canonical JSON encoding")
    return value


def _require_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DerivedDataError(f"selector {field_name} must be an integer")
    return value


def _validate_selector(kind: str, selector: dict[str, Any]) -> None:
    if kind == "slice":
        expected = {"array", "axis", "components", "index"}
        if set(selector) != expected:
            raise DerivedDataError(f"slice selector keys must be {sorted(expected)!r}")
        _require_int(selector["axis"], "axis")
        _require_int(selector["index"], "index")
        components = selector["components"]
        if not isinstance(components, list) or not components:
            raise DerivedDataError("slice selector components must be a non-empty list")
        for component in components:
            _require_int(component, "component")
    elif kind == "line":
        expected = {"array", "axis", "components", "fixed"}
        if set(selector) != expected:
            raise DerivedDataError(f"line selector keys must be {sorted(expected)!r}")
        _require_int(selector["axis"], "axis")
        components = selector["components"]
        if not isinstance(components, list) or not components:
            raise DerivedDataError("line selector components must be a non-empty list")
        for component in components:
            _require_int(component, "component")
        fixed = selector["fixed"]
        if not isinstance(fixed, dict):
            raise DerivedDataError("line selector fixed must be an object")
        for raw_axis, index in fixed.items():
            if not raw_axis.isdecimal():
                raise DerivedDataError("line selector fixed axes must be decimal strings")
            _require_int(index, "fixed index")
    else:
        expected = {"array", "index"}
        if set(selector) != expected:
            raise DerivedDataError(f"scalar selector keys must be {sorted(expected)!r}")
        indexes = selector["index"]
        if not isinstance(indexes, list) or not indexes:
            raise DerivedDataError("scalar selector index must be a non-empty list")
        for index in indexes:
            _require_int(index, "index")
    if not isinstance(selector.get("array"), str) or not selector["array"]:
        raise DerivedDataError("selector array must be a non-empty string")


def _required_ids(raw: str, field_name: str) -> tuple[str, ...]:
    if raw == "N/A":
        raise DerivedDataError(f"{field_name} must name at least one parent")
    try:
        return IdList.parse(raw).items
    except ManifestError as error:
        raise DerivedDataError(f"{field_name}: {error}") from error


def _format_coordinate_number(value: float) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise DerivedDataError("coordinate values must be finite numbers")
    if number == 0:
        number = 0.0
    if number.is_integer():
        return str(int(number))
    return np.format_float_positional(number, unique=True, trim="-")


def _parse_coordinate_numbers(
    raw: str,
    field_name: str,
    *,
    positive: bool,
) -> tuple[float, ...]:
    if not isinstance(raw, str) or not raw:
        raise DerivedDataError(
            f"{field_name} must use canonical semicolon-separated numbers"
        )
    tokens = raw.split(";")
    values: list[float] = []
    for token in tokens:
        if not token or token != token.strip():
            raise DerivedDataError(
                f"{field_name} must use canonical semicolon-separated numbers"
            )
        try:
            value = float(token)
        except ValueError as error:
            raise DerivedDataError(f"{field_name} values must be finite numbers") from error
        if not math.isfinite(value):
            raise DerivedDataError(f"{field_name} values must be finite numbers")
        if token != _format_coordinate_number(value):
            raise DerivedDataError(
                f"{field_name} must use canonical semicolon-separated numbers"
            )
        if positive and value <= 0:
            raise DerivedDataError(f"{field_name} values must be positive")
        values.append(value)
    return tuple(values)


def _parse_coordinate_units(raw: str) -> tuple[str, ...]:
    if not isinstance(raw, str) or not raw:
        raise DerivedDataError(
            "coordinate_units must use canonical semicolon-separated unit tokens"
        )
    units = tuple(raw.split(";"))
    if any(
        not unit
        or unit == "N/A"
        or unit != unit.strip()
        or any(character.isspace() for character in unit)
        for unit in units
    ):
        raise DerivedDataError(
            "coordinate_units must use canonical semicolon-separated unit tokens"
        )
    return units


@dataclass(frozen=True, slots=True)
class DerivedRecipe:
    recipe_id: str
    output_data_id: str
    source_path: str
    source_sha256: str
    producer_script: str
    producer_sha256: str
    selector_kind: str
    selector_json: str
    output_path: str
    output_format: str
    output_sha256: str
    shape: str
    columns: str
    units: str
    coordinate_origin: str
    coordinate_spacing: str
    coordinate_units: str
    parent_figure_ids: str
    parent_data_ids: str
    environment_command: str
    is_complete_field: str
    notes: str

    def __post_init__(self) -> None:
        for field_name in ("recipe_id", "output_data_id"):
            value = getattr(self, field_name)
            if not value or ";" in value or any(character.isspace() for character in value):
                raise DerivedDataError(
                    f"{field_name} must be a non-empty ID without whitespace"
                )
        try:
            require_relative_path(self.source_path)
            require_relative_path(self.producer_script)
            require_relative_path(self.output_path)
        except ManifestError as error:
            raise DerivedDataError(str(error)) from error
        if self.producer_script != DERIVED_PRODUCER_SCRIPT:
            raise DerivedDataError(
                "producer_script must identify the canonical derived producer"
            )
        _require_sha256(self.source_sha256, "source_sha256")
        _require_sha256(self.producer_sha256, "producer_sha256")
        _require_sha256(self.output_sha256, "output_sha256")
        if self.selector_kind not in ALLOWED_SELECTORS:
            raise DerivedDataError(
                "selector_kind must be one of slice, line, or scalar; complete volumes are forbidden"
            )
        selector = _parse_json(self.selector_json)
        _validate_selector(self.selector_kind, selector)
        if self.output_format not in ALLOWED_OUTPUT_FORMATS:
            raise DerivedDataError("output_format must be csv or npz")
        if Path(self.output_path).suffix.casefold() != f".{self.output_format}":
            raise DerivedDataError("output_path suffix must match output_format")
        if not SHAPE_PATTERN.fullmatch(self.shape):
            raise DerivedDataError(
                "shape must declare exact positive dimensions such as 128x128x3"
            )
        if not self.columns or not self.units:
            raise DerivedDataError("shape, columns, and units must all be declared")
        coordinate_origin = _parse_coordinate_numbers(
            self.coordinate_origin,
            "coordinate_origin",
            positive=False,
        )
        coordinate_spacing = _parse_coordinate_numbers(
            self.coordinate_spacing,
            "coordinate_spacing",
            positive=True,
        )
        coordinate_units = _parse_coordinate_units(self.coordinate_units)
        coordinate_lengths = {
            len(coordinate_origin),
            len(coordinate_spacing),
            len(coordinate_units),
        }
        if len(coordinate_lengths) != 1:
            raise DerivedDataError(
                "coordinate_origin, coordinate_spacing, and coordinate_units must "
                "contain the same number of axis values"
            )
        _required_ids(self.parent_figure_ids, "parent_figure_ids")
        _required_ids(self.parent_data_ids, "parent_data_ids")
        if self.environment_command != HOPFION_ENVIRONMENT_COMMAND:
            raise DerivedDataError(
                "environment_command must identify the pinned hopfion Python environment"
            )
        if self.is_complete_field != "false":
            raise DerivedDataError("is_complete_field must be the literal false")
        if not self.notes:
            raise DerivedDataError("notes must explain why this bounded output is needed")


@dataclass(frozen=True, slots=True)
class _CoordinateSystem:
    """Spatial mesh metadata; origin is the pmin cell boundary, not a cell centre."""

    origin: tuple[float, ...]
    spacing: tuple[float, ...]
    units: tuple[str, ...]


def _declared_coordinate_system(recipe: DerivedRecipe) -> _CoordinateSystem:
    return _CoordinateSystem(
        origin=_parse_coordinate_numbers(
            recipe.coordinate_origin,
            "coordinate_origin",
            positive=False,
        ),
        spacing=_parse_coordinate_numbers(
            recipe.coordinate_spacing,
            "coordinate_spacing",
            positive=True,
        ),
        units=_parse_coordinate_units(recipe.coordinate_units),
    )


@dataclass(frozen=True, slots=True)
class DerivedEvidence:
    recipe_id: str
    output_data_id: str
    output_path: str
    source_path: str
    source_sha256: str
    producer_script: str
    producer_sha256: str
    selector_kind: str
    selector_json: str
    coordinate_origin: str
    coordinate_spacing: str
    coordinate_units: str
    output_sha256: str
    output_size: int
    output_mtime_ns: int
    parent_figure_ids: tuple[str, ...]
    parent_data_ids: tuple[str, ...]
    environment_command: str
    executed_python: str
    is_complete_field: bool
    generation_token: str
    generated_at_ns: int


@dataclass(frozen=True, slots=True)
class _Selection:
    values: np.ndarray
    coordinates: np.ndarray
    coordinate_axes: tuple[int, ...]
    output_shape: tuple[int, ...]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _running_implementation_sha256() -> str:
    implementation = Path(__file__).resolve()
    metadata = _assert_regular_source(implementation, "running derived implementation")
    if not stat.S_ISREG(metadata.st_mode):
        raise DerivedDataError("running derived implementation is not a regular file")
    return _sha256_file(implementation)


def _sha256_descriptor(descriptor: int) -> str:
    digest = hashlib.sha256()
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        os.lseek(descriptor, 0, os.SEEK_SET)
    except OSError as error:
        raise DerivedDataError("cannot hash anchored source descriptor") from error
    return digest.hexdigest()


def _same_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )


def _ovf_header_units(source: Path, spatial_dimensions: int) -> tuple[str, ...]:
    try:
        with source.open("rb") as handle:
            header = handle.read(MAX_OVF_HEADER_BYTES)
    except OSError as error:
        raise DerivedDataError("cannot read OVF header for mesh units") from error
    matches = OVF_MESHUNIT_PATTERN.findall(header)
    if len(matches) != 1:
        raise DerivedDataError(
            "OVF mesh units are unavailable or ambiguous in field metadata and header"
        )
    try:
        unit = matches[0].decode("ascii")
    except UnicodeDecodeError as error:
        raise DerivedDataError("OVF mesh units must be ASCII unit tokens") from error
    units = (unit,) * spatial_dimensions
    _parse_coordinate_units(";".join(units))
    return units


def _ovf_coordinate_system(
    field: Any,
    source: Path,
    *,
    spatial_dimensions: int,
) -> _CoordinateSystem:
    try:
        origin = tuple(float(value) for value in field.mesh.region.pmin)
        spacing = tuple(float(value) for value in field.mesh.cell)
    except (AttributeError, TypeError, ValueError) as error:
        raise DerivedDataError("OVF mesh pmin/cell metadata is unavailable") from error
    if not (
        len(origin) == len(spacing) == spatial_dimensions
        and all(math.isfinite(value) for value in origin)
        and all(math.isfinite(value) and value > 0 for value in spacing)
    ):
        raise DerivedDataError("OVF mesh pmin/cell metadata is invalid")
    try:
        raw_units = field.mesh.region.units
    except AttributeError:
        units = _ovf_header_units(source, spatial_dimensions)
    else:
        if isinstance(raw_units, str):
            units = (raw_units,) * spatial_dimensions
        else:
            try:
                units = tuple(str(unit) for unit in raw_units)
            except TypeError as error:
                raise DerivedDataError("OVF mesh units metadata is invalid") from error
        if len(units) != spatial_dimensions:
            raise DerivedDataError("OVF mesh units metadata is invalid")
        _parse_coordinate_units(";".join(units))
    return _CoordinateSystem(origin=origin, spacing=spacing, units=units)


def _require_exact_ovf_coordinates(
    actual: _CoordinateSystem,
    declared: _CoordinateSystem,
) -> None:
    for field_name, actual_values, declared_values in (
        ("coordinate_origin", actual.origin, declared.origin),
        ("coordinate_spacing", actual.spacing, declared.spacing),
    ):
        try:
            np.testing.assert_allclose(
                np.asarray(actual_values, dtype=np.float64),
                np.asarray(declared_values, dtype=np.float64),
                rtol=0,
                atol=0,
            )
        except AssertionError as error:
            raise DerivedDataError(
                f"OVF {field_name} does not exactly match the recipe declaration"
            ) from error
    if actual.units != declared.units:
        raise DerivedDataError(
            "OVF coordinate_units do not exactly match the recipe declaration"
        )


def _load_source(
    source: Path,
    array_name: str,
    *,
    source_name: str | None = None,
    declared_coordinates: _CoordinateSystem | None = None,
) -> np.ndarray:
    lowered = (source_name or source.name).casefold()
    if lowered.endswith((".ovf.gz", ".omf.gz")):
        raise DerivedDataError(
            "compressed OVF sources are unsupported by the pinned discretisedfield "
            "reader; point the recipe at an uncompressed anchored OVF/OMF source"
        )
    if lowered.endswith((".ovf", ".omf")):
        expected = Path(HOPFION_ENVIRONMENT_COMMAND).resolve()
        if Path(sys.executable).resolve() != expected:
            raise DerivedDataError(
                "OVF extraction requires /mnt/d/Research/Hopfion/hopfion/bin/python "
                "with discretisedfield"
            )
        try:
            import discretisedfield as df
        except ImportError as error:
            raise DerivedDataError("discretisedfield is unavailable in hopfion environment") from error
        suffix = Path(lowered).suffix
        try:
            with tempfile.TemporaryDirectory(
                prefix=".handoff-anchored-ovf-reader-",
                dir="/tmp",
            ) as temporary_directory:
                alias = Path(temporary_directory) / f"source{suffix}"
                alias.symlink_to(source)
                field = df.Field.from_file(str(alias))
        except Exception as error:
            raise DerivedDataError("cannot read anchored OVF/OMF source") from error
        array = np.asarray(field.array)
        if declared_coordinates is None:
            raise DerivedDataError(
                "OVF extraction requires declared coordinate metadata"
            )
        actual_coordinates = _ovf_coordinate_system(
            field,
            source,
            spatial_dimensions=array.ndim - 1,
        )
        _require_exact_ovf_coordinates(actual_coordinates, declared_coordinates)
    elif lowered.endswith(".npz"):
        try:
            with np.load(source, allow_pickle=False) as archive:
                if array_name not in archive.files:
                    raise DerivedDataError(
                        f"source NPZ has no declared array {array_name!r}"
                    )
                array = np.array(archive[array_name], copy=True)
        except (OSError, ValueError) as error:
            raise DerivedDataError(f"cannot read source NPZ: {source}") from error
    elif lowered.endswith(".npy"):
        try:
            array = np.load(source, allow_pickle=False)
        except (OSError, ValueError) as error:
            raise DerivedDataError(f"cannot read source NPY: {source}") from error
    else:
        raise DerivedDataError(
            "derived producer supports only NPY/NPZ fixtures or OVF through hopfion Python"
        )
    if array.dtype.hasobject:
        raise DerivedDataError("object arrays are forbidden")
    if not np.issubdtype(array.dtype, np.number):
        raise DerivedDataError("source array must be numeric")
    return np.asarray(array)


def _normalise_axis(axis: int, spatial_dimensions: int) -> int:
    if axis < 0:
        axis += spatial_dimensions
    if not 0 <= axis < spatial_dimensions:
        raise DerivedDataError("selector axis is outside the spatial dimensions")
    return axis


def _normalise_index(index: int, length: int, field_name: str) -> int:
    if index < 0:
        index += length
    if not 0 <= index < length:
        raise DerivedDataError(f"selector {field_name} is out of bounds")
    return index


def _normalise_components(components: list[int], count: int) -> tuple[int, ...]:
    result = tuple(_normalise_index(component, count, "component") for component in components)
    if len(set(result)) != len(result):
        raise DerivedDataError("selector components must be unique")
    return result


def _select(array: np.ndarray, kind: str, selector: dict[str, Any]) -> _Selection:
    if kind in {"slice", "line"}:
        if array.ndim < 2:
            raise DerivedDataError("slice/line input must have spatial and component axes")
        spatial_dimensions = array.ndim - 1
        if spatial_dimensions > 3:
            raise DerivedDataError(
                "slice/line selectors cannot reduce four or more spatial axes to a "
                "three-dimensional spatial volume"
            )
        axis = _normalise_axis(selector["axis"], spatial_dimensions)
        components = _normalise_components(selector["components"], array.shape[-1])

        if kind == "slice":
            index = _normalise_index(selector["index"], array.shape[axis], "index")
            selected = np.take(array, index, axis=axis)[..., list(components)]
            coordinates = np.array(
                list(np.ndindex(selected.shape[:-1])), dtype=np.int64
            )
            coordinate_axes = tuple(
                spatial_axis
                for spatial_axis in range(spatial_dimensions)
                if spatial_axis != axis
            )
            values = selected.reshape(-1, selected.shape[-1])
            output_shape = tuple(selected.shape)
        else:
            fixed = {int(raw_axis): index for raw_axis, index in selector["fixed"].items()}
            required_axes = set(range(spatial_dimensions)) - {axis}
            if set(fixed) != required_axes:
                raise DerivedDataError(
                    "line selector fixed axes must name every non-varying spatial axis"
                )
            indexes: list[int | slice] = []
            for spatial_axis in range(spatial_dimensions):
                if spatial_axis == axis:
                    indexes.append(slice(None))
                else:
                    indexes.append(
                        _normalise_index(
                            fixed[spatial_axis],
                            array.shape[spatial_axis],
                            f"fixed[{spatial_axis}]",
                        )
                    )
            selected = array[tuple(indexes) + (list(components),)]
            values = np.asarray(selected).reshape(array.shape[axis], len(components))
            coordinates = np.arange(array.shape[axis], dtype=np.int64).reshape(-1, 1)
            coordinate_axes = (axis,)
            output_shape = tuple(values.shape)
    else:
        indexes = selector["index"]
        if len(indexes) != array.ndim:
            raise DerivedDataError("scalar selector must index every source dimension")
        normalised = tuple(
            _normalise_index(index, array.shape[axis], f"index[{axis}]")
            for axis, index in enumerate(indexes)
        )
        values = np.asarray([[array[normalised]]])
        coordinates = np.asarray([normalised[:-1]], dtype=np.int64)
        coordinate_axes = tuple(range(array.ndim - 1))
        output_shape = (1,)

    if values.ndim != 2 or values.size == 0:
        raise DerivedDataError("selector produced an empty or non-tabular output")
    if values.size >= array.size:
        raise DerivedDataError("selector did not reduce the source array")
    if (
        len(output_shape) == 2
        and output_shape[0] >= MIN_COMPLETE_FIELD_POINTS
        and output_shape[1] in {3, 6}
    ) or (
        len(output_shape) == 4
        and 3 in output_shape
        and math.prod(
            length
            for index, length in enumerate(output_shape)
            if index != output_shape.index(3)
        )
        >= MIN_COMPLETE_FIELD_POINTS
    ) or (
        len(output_shape) == 3
        and all(length > 4 for length in output_shape)
        and math.prod(output_shape) >= MIN_COMPLETE_FIELD_POINTS
    ):
        raise DerivedDataError(
            "selector output still matches a complete-field array shape"
        )
    return _Selection(
        values=np.asarray(values),
        coordinates=coordinates,
        coordinate_axes=coordinate_axes,
        output_shape=output_shape,
    )


def _physicalise_coordinates(
    selection: _Selection,
    coordinate_system: _CoordinateSystem,
    *,
    spatial_dimensions: int,
) -> _Selection:
    """Convert integer mesh indices to cell centres: pmin + (index + 0.5) * cell."""

    if spatial_dimensions < 1 or not (
        len(coordinate_system.origin)
        == len(coordinate_system.spacing)
        == len(coordinate_system.units)
        == spatial_dimensions
    ):
        raise DerivedDataError(
            "declared coordinate axis count does not match source spatial dimensions"
        )
    axes = np.asarray(selection.coordinate_axes, dtype=np.int64)
    if selection.coordinates.shape[1] != axes.size:
        raise DerivedDataError("selected coordinate axes are internally inconsistent")
    origin = np.asarray(coordinate_system.origin, dtype=np.float64)[axes]
    spacing = np.asarray(coordinate_system.spacing, dtype=np.float64)[axes]
    coordinates = origin + (selection.coordinates.astype(np.float64) + 0.5) * spacing
    return _Selection(
        values=selection.values,
        coordinates=coordinates,
        coordinate_axes=selection.coordinate_axes,
        output_shape=selection.output_shape,
    )


def _format_number(value: Any) -> str:
    scalar = np.asarray(value).item()
    if isinstance(scalar, (int, np.integer)):
        return str(int(scalar))
    number = float(scalar)
    if not np.isfinite(number):
        raise DerivedDataError("derived output contains a non-finite value")
    if number.is_integer():
        return str(int(number))
    return np.format_float_positional(number, unique=True, trim="-")


def _render_csv(selection: _Selection, recipe: DerivedRecipe) -> bytes:
    columns = recipe.columns.split(";")
    units = recipe.units.split(";")
    expected_columns = selection.coordinates.shape[1] + selection.values.shape[1]
    if len(columns) != expected_columns or len(units) != expected_columns:
        raise DerivedDataError(
            "columns/units count does not match selected coordinates and values"
        )
    coordinate_units = _parse_coordinate_units(recipe.coordinate_units)
    expected_coordinate_units = tuple(
        coordinate_units[axis] for axis in selection.coordinate_axes
    )
    if tuple(units[: selection.coordinates.shape[1]]) != expected_coordinate_units:
        raise DerivedDataError(
            "coordinate units in units do not match declared coordinate_units"
        )
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(columns)
    for coordinates, values in zip(selection.coordinates, selection.values, strict=True):
        writer.writerow(
            [
                *(_format_number(value) for value in coordinates),
                *(_format_number(value) for value in values),
            ]
        )
    return output.getvalue().encode("utf-8")


def _npy_payload(array: np.ndarray) -> bytes:
    output = io.BytesIO()
    np.lib.format.write_array(output, np.asarray(array), version=(1, 0), allow_pickle=False)
    return output.getvalue()


def _render_npz(selection: _Selection, recipe: DerivedRecipe) -> bytes:
    columns = np.asarray(recipe.columns.split(";"), dtype="U")
    units = np.asarray(recipe.units.split(";"), dtype="U")
    expected_columns = selection.coordinates.shape[1] + selection.values.shape[1]
    if columns.size != expected_columns or units.size != expected_columns:
        raise DerivedDataError(
            "columns/units count does not match selected coordinates and values"
        )
    coordinate_units = _parse_coordinate_units(recipe.coordinate_units)
    expected_coordinate_units = tuple(
        coordinate_units[axis] for axis in selection.coordinate_axes
    )
    if tuple(units[: selection.coordinates.shape[1]]) != expected_coordinate_units:
        raise DerivedDataError(
            "coordinate units in units do not match declared coordinate_units"
        )
    output = io.BytesIO()
    arrays = {
        "columns": columns,
        "coordinates": selection.coordinates,
        "units": units,
        "values": selection.values,
    }
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for name in sorted(arrays):
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, _npy_payload(arrays[name]), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()


def _assert_regular_source(path: Path, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise DerivedDataError(f"cannot stat {label}: {path}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise DerivedDataError(f"{label} must be a regular non-symlink file: {path}")
    return metadata


def _require_output_root(path: Path | str) -> Path:
    raw = Path(path)
    if ".." in raw.parts:
        raise DerivedDataError("output_root must not contain dot-dot path components")
    return raw.absolute()


def _open_or_create_real_directory(path: Path) -> int:
    """Open an absolute directory path one no-follow component at a time."""
    absolute = path.absolute()
    if absolute.anchor != "/":
        raise DerivedDataError(f"output directory must be an absolute POSIX path: {path}")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open("/", flags)
        for part in absolute.parts[1:]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=descriptor)
            except FileExistsError:
                pass
            metadata = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode):
                raise DerivedDataError(
                    f"derived output path contains a symlink: {absolute}"
                )
            if not stat.S_ISDIR(metadata.st_mode):
                raise DerivedDataError(
                    f"derived output ancestor is not a directory: {absolute}"
                )
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        raise DerivedDataError(f"cannot anchor derived output directory: {absolute}") from error
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _write_exclusive(
    output_root: Path,
    relative_path: str,
    payload: bytes,
) -> os.stat_result:
    relative = require_relative_path(relative_path)
    parent_descriptor = _open_or_create_real_directory(output_root)
    descriptor = -1
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        for part in relative.parts[:-1]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=parent_descriptor)
            except FileExistsError:
                pass
            metadata = os.stat(
                part,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if stat.S_ISLNK(metadata.st_mode):
                raise DerivedDataError(
                    f"derived output path contains a symlink: {relative_path}"
                )
            if not stat.S_ISDIR(metadata.st_mode):
                raise DerivedDataError(
                    f"derived output ancestor is not a directory: {relative_path}"
                )
            child = os.open(part, flags, dir_fd=parent_descriptor)
            os.close(parent_descriptor)
            parent_descriptor = child
        try:
            descriptor = os.open(
                relative.parts[-1],
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0),
                0o644,
                dir_fd=parent_descriptor,
            )
        except FileExistsError as error:
            raise DerivedDataError(
                f"derived output already exists: {relative_path}"
            ) from error
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise DerivedDataError(
                f"derived output is not a regular file: {relative_path}"
            )
        return metadata
    except OSError as error:
        raise DerivedDataError(
            f"cannot create derived output: {relative_path}"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def produce_derived(
    recipe: DerivedRecipe,
    *,
    project_root: Path | str,
    output_root: Path | str,
) -> DerivedEvidence:
    """Generate exactly one declared minimal output and return immutable evidence."""
    project = Path(project_root).resolve()
    output = _require_output_root(output_root)
    declared_coordinates = _declared_coordinate_system(recipe)
    source_descriptor = -1
    producer_descriptor = -1
    with AnchoredRoot(project, error_type=DerivedDataError) as anchor:
        try:
            source_descriptor = anchor.open_regular(recipe.source_path)
            producer_descriptor = anchor.open_regular(recipe.producer_script)
            source_snapshot = os.fstat(source_descriptor)
            producer_snapshot = os.fstat(producer_descriptor)
            source_sha256 = _sha256_descriptor(source_descriptor)
            producer_sha256 = _sha256_descriptor(producer_descriptor)
            if source_sha256 != recipe.source_sha256:
                raise DerivedDataError("source_sha256 does not match the source bytes")
            if producer_sha256 != recipe.producer_sha256:
                raise DerivedDataError("producer_sha256 does not match the producer bytes")
            if producer_sha256 != _running_implementation_sha256():
                raise DerivedDataError(
                    "declared producer differs from the running derived implementation"
                )

            selector = _parse_json(recipe.selector_json)
            source_handle = Path(f"/proc/self/fd/{source_descriptor}")
            array = _load_source(
                source_handle,
                selector["array"],
                source_name=recipe.source_path,
                declared_coordinates=declared_coordinates,
            )
            if not _same_snapshot(source_snapshot, os.fstat(source_descriptor)):
                raise DerivedDataError("derived source changed during extraction")
            if not _same_snapshot(producer_snapshot, os.fstat(producer_descriptor)):
                raise DerivedDataError("derived producer changed during extraction")
        finally:
            if source_descriptor >= 0:
                os.close(source_descriptor)
            if producer_descriptor >= 0:
                os.close(producer_descriptor)
    selection = _physicalise_coordinates(
        _select(array, recipe.selector_kind, selector),
        declared_coordinates,
        spatial_dimensions=array.ndim - 1,
    )
    actual_shape = "x".join(str(length) for length in selection.output_shape)
    if recipe.shape != actual_shape:
        raise DerivedDataError(
            f"declared shape {recipe.shape!r} does not match generated shape {actual_shape!r}"
        )
    payload = (
        _render_csv(selection, recipe)
        if recipe.output_format == "csv"
        else _render_npz(selection, recipe)
    )
    output_sha256 = hashlib.sha256(payload).hexdigest()
    if output_sha256 != recipe.output_sha256:
        raise DerivedDataError("output_sha256 does not match generated bytes")

    metadata = _write_exclusive(output, recipe.output_path, payload)
    generated_at_ns = time.time_ns()
    return DerivedEvidence(
        recipe_id=recipe.recipe_id,
        output_data_id=recipe.output_data_id,
        output_path=recipe.output_path,
        source_path=recipe.source_path,
        source_sha256=source_sha256,
        producer_script=recipe.producer_script,
        producer_sha256=producer_sha256,
        selector_kind=recipe.selector_kind,
        selector_json=recipe.selector_json,
        coordinate_origin=recipe.coordinate_origin,
        coordinate_spacing=recipe.coordinate_spacing,
        coordinate_units=recipe.coordinate_units,
        output_sha256=output_sha256,
        output_size=metadata.st_size,
        output_mtime_ns=metadata.st_mtime_ns,
        parent_figure_ids=_required_ids(recipe.parent_figure_ids, "parent_figure_ids"),
        parent_data_ids=_required_ids(recipe.parent_data_ids, "parent_data_ids"),
        environment_command=recipe.environment_command,
        executed_python=str(Path(sys.executable).absolute()),
        is_complete_field=False,
        generation_token=secrets.token_hex(16),
        generated_at_ns=generated_at_ns,
    )


def _decode_derived_evidence(raw: str) -> DerivedEvidence:
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise DerivedDataError("pinned producer returned invalid JSON evidence") from error
    expected_fields = {field.name for field in fields(DerivedEvidence)}
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise DerivedDataError(
            "pinned producer returned an unexpected evidence schema"
        )
    for field_name in ("parent_figure_ids", "parent_data_ids"):
        values = payload[field_name]
        if not isinstance(values, list) or not all(
            isinstance(value, str) for value in values
        ):
            raise DerivedDataError(
                f"pinned producer returned invalid {field_name} evidence"
            )
        payload[field_name] = tuple(values)
    try:
        return DerivedEvidence(**payload)
    except (TypeError, ValueError) as error:
        raise DerivedDataError("pinned producer returned invalid evidence values") from error


def produce_derived_in_environment(
    recipe: DerivedRecipe,
    *,
    project_root: Path | str,
    output_root: Path | str,
) -> DerivedEvidence:
    """Run the canonical producer under the recipe-declared pinned Python."""
    executable = Path(recipe.environment_command)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise DerivedDataError(
            f"pinned derived-data environment is unavailable: {executable}"
        )
    project = Path(project_root).resolve()
    output = _require_output_root(output_root)
    request = json.dumps(
        {
            "output_root": str(output),
            "project_root": str(project),
            "recipe": asdict(recipe),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    package_root = Path(__file__).resolve().parents[1]
    environment = {
        "HOME": "/tmp",
        "OPENBLAS_NUM_THREADS": "1",
        "PATH": f"{executable.parent}:/usr/bin:/bin",
        "PYTHONHASHSEED": "0",
        "PYTHONPATH": str(package_root),
    }
    try:
        completed = subprocess.run(
            [str(executable), "-m", "handoff_delivery.derived", "--produce-json"],
            input=request,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            stdin=None,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise DerivedDataError(
            f"cannot execute pinned derived-data producer: {error}"
        ) from error
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-2000:]
        raise DerivedDataError(
            "pinned derived-data producer failed with exit "
            f"{completed.returncode}: {stderr}"
        )
    evidence = _decode_derived_evidence(
        completed.stdout.decode("utf-8", errors="strict")
    )
    if evidence.executed_python != recipe.environment_command:
        raise DerivedDataError(
            "pinned producer evidence does not match environment_command"
        )
    return evidence


def validate_derived_preflight(
    recipes: tuple[DerivedRecipe, ...] | list[DerivedRecipe],
    *,
    project_root: Path | str,
) -> None:
    """Validate producer/source identity and unique outputs without generating data."""
    recipe_ids = [recipe.recipe_id for recipe in recipes]
    data_ids = [recipe.output_data_id for recipe in recipes]
    output_paths = [recipe.output_path for recipe in recipes]
    source_paths = [recipe.source_path for recipe in recipes]
    source_sha256_values = [recipe.source_sha256 for recipe in recipes]
    for label, values in (
        ("recipe IDs", recipe_ids),
        ("output data IDs", data_ids),
        ("output paths", output_paths),
        ("source paths", source_paths),
        ("source SHA256 values", source_sha256_values),
    ):
        if len(values) != len(set(values)):
            raise DerivedDataError(f"derived {label} must be unique")
    running_sha256 = _running_implementation_sha256()
    for recipe in recipes:
        if recipe.producer_sha256 != running_sha256:
            raise DerivedDataError(
                f"{recipe.recipe_id}: producer differs from the running derived implementation"
            )
    project = Path(project_root).resolve()
    with AnchoredRoot(project, error_type=DerivedDataError) as anchor:
        for recipe in recipes:
            for label, relative, expected in (
                ("source_sha256", recipe.source_path, recipe.source_sha256),
                ("producer_sha256", recipe.producer_script, recipe.producer_sha256),
            ):
                descriptor = anchor.open_regular(relative)
                try:
                    actual = _sha256_descriptor(descriptor)
                finally:
                    os.close(descriptor)
                if actual != expected:
                    raise DerivedDataError(
                        f"{recipe.recipe_id}: {label} preflight mismatch"
                    )


def write_derived_evidence(
    path: Path | str,
    evidence_rows: tuple[DerivedEvidence, ...] | list[DerivedEvidence],
) -> None:
    """Write one exclusive, deterministic build-evidence CSV."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.lstat()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise DerivedDataError(f"cannot inspect derived evidence path: {target}") from error
    else:
        raise DerivedDataError(f"derived evidence already exists: {target}")
    temporary = target.with_name(f".{target.name}.writing")
    fieldnames = tuple(DerivedEvidence.__dataclass_fields__)
    try:
        with temporary.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for evidence in evidence_rows:
                row = asdict(evidence)
                row["parent_figure_ids"] = ";".join(evidence.parent_figure_ids)
                row["parent_data_ids"] = ";".join(evidence.parent_data_ids)
                row["is_complete_field"] = "false"
                writer.writerow(row)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except OSError as error:
        raise DerivedDataError(f"cannot write derived evidence: {target}") from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def validate_derived_outputs(
    recipes: tuple[DerivedRecipe, ...] | list[DerivedRecipe],
    evidence_rows: tuple[DerivedEvidence, ...] | list[DerivedEvidence],
    *,
    output_root: Path | str,
) -> None:
    """Reject missing, stale, hand-authored, or untracked derived artifacts."""
    recipe_by_id = {recipe.recipe_id: recipe for recipe in recipes}
    if len(recipe_by_id) != len(recipes):
        raise DerivedDataError("derived recipe IDs must be unique")
    evidence_by_id = {row.recipe_id: row for row in evidence_rows}
    if len(evidence_by_id) != len(evidence_rows):
        raise DerivedDataError("derived generation evidence IDs must be unique")
    if set(evidence_by_id) != set(recipe_by_id):
        missing = sorted(set(recipe_by_id) - set(evidence_by_id))
        extra = sorted(set(evidence_by_id) - set(recipe_by_id))
        raise DerivedDataError(
            f"generation evidence mismatch; missing={missing!r}; extra={extra!r}"
        )

    root = _require_output_root(output_root)
    discovered = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    expected = {recipe.output_path for recipe in recipes}
    if discovered != expected:
        raise DerivedDataError(
            "untracked derived outputs; "
            f"extra={sorted(discovered - expected)!r}; missing={sorted(expected - discovered)!r}"
        )

    for recipe_id, recipe in recipe_by_id.items():
        evidence = evidence_by_id[recipe_id]
        if not evidence.generation_token:
            raise DerivedDataError(f"{recipe_id}: generation evidence has no token")
        expected_fields = {
            "output_data_id": recipe.output_data_id,
            "output_path": recipe.output_path,
            "source_path": recipe.source_path,
            "source_sha256": recipe.source_sha256,
            "producer_script": recipe.producer_script,
            "producer_sha256": recipe.producer_sha256,
            "selector_kind": recipe.selector_kind,
            "selector_json": recipe.selector_json,
            "coordinate_origin": recipe.coordinate_origin,
            "coordinate_spacing": recipe.coordinate_spacing,
            "coordinate_units": recipe.coordinate_units,
            "output_sha256": recipe.output_sha256,
            "environment_command": recipe.environment_command,
            "executed_python": recipe.environment_command,
        }
        for field_name, expected_value in expected_fields.items():
            if getattr(evidence, field_name) != expected_value:
                raise DerivedDataError(
                    f"{recipe_id}: evidence {field_name} does not match recipe"
                )
        target = root / recipe.output_path
        metadata = _assert_regular_source(target, "derived output")
        if metadata.st_size != evidence.output_size:
            raise DerivedDataError(f"{recipe_id}: derived output size changed")
        if metadata.st_mtime_ns != evidence.output_mtime_ns:
            raise DerivedDataError(f"{recipe_id}: derived output mtime changed")
        if _sha256_file(target) != evidence.output_sha256:
            raise DerivedDataError(f"{recipe_id}: derived output SHA256 changed")


def _produce_json_main() -> int:
    try:
        request = json.loads(sys.stdin.buffer.read())
        if not isinstance(request, dict) or set(request) != {
            "output_root",
            "project_root",
            "recipe",
        }:
            raise DerivedDataError("invalid pinned-producer request schema")
        if not isinstance(request["recipe"], dict):
            raise DerivedDataError("invalid pinned-producer recipe")
        recipe = DerivedRecipe(**request["recipe"])
        evidence = produce_derived(
            recipe,
            project_root=request["project_root"],
            output_root=request["output_root"],
        )
        sys.stdout.write(
            json.dumps(asdict(evidence), sort_keys=True, separators=(",", ":"))
        )
        sys.stdout.write("\n")
        return 0
    except (DerivedDataError, TypeError, ValueError, OSError) as error:
        sys.stderr.write(f"derived producer refused request: {error}\n")
        return 1


if __name__ == "__main__":
    if sys.argv[1:] != ["--produce-json"]:
        sys.stderr.write("usage: python -m handoff_delivery.derived --produce-json\n")
        raise SystemExit(2)
    raise SystemExit(_produce_json_main())
