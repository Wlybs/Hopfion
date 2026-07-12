"""Fail-closed, content-level inventory checks for delivery candidates.

The inventory layer deliberately does not parse OVF payloads.  It identifies field
files by name, container membership, OOMMF markers, and measurable array/text
shapes.  The separate derived-data producer is the only component allowed to read
source OVF files.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import io
import math
import os
from pathlib import Path
import stat
import tarfile
from typing import BinaryIO, Literal, Mapping
import zipfile

import numpy as np


Decision = Literal["include", "exclude"]


@dataclass(frozen=True, slots=True)
class InspectionLimits:
    """Deterministic limits used while inspecting untrusted candidates."""

    max_archive_depth: int = 2
    max_archive_entries: int = 100_000
    max_archive_uncompressed_bytes: int = 5 * 1024**3
    max_nested_member_bytes: int = 512 * 1024**2
    max_numpy_uncompressed_bytes: int = 256 * 1024**2
    min_suspect_text_bytes: int = 10 * 1024**2
    min_suspect_text_rows: int = 100_000
    text_head_rows: int = 1_024
    text_even_rows: int = 4_096
    text_tail_rows: int = 1_024
    min_complete_field_points: int = 100_000

    def __post_init__(self) -> None:
        positive = (
            self.max_archive_depth,
            self.max_archive_entries,
            self.max_archive_uncompressed_bytes,
            self.max_nested_member_bytes,
            self.max_numpy_uncompressed_bytes,
            self.min_suspect_text_bytes,
            self.min_suspect_text_rows,
            self.text_head_rows,
            self.text_even_rows,
            self.text_tail_rows,
            self.min_complete_field_points,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("inspection limits must all be positive")


@dataclass(frozen=True, slots=True)
class InspectionResult:
    """Immutable disposition and evidence for one filesystem candidate."""

    decision: Decision
    reason: str
    sha256: str
    size: int
    file_type: str = "file"
    container_kind: str | None = None
    link_target: str | None = None
    evidence: tuple[str, ...] = ()
    array_shapes: tuple[str, ...] = ()


@dataclass(slots=True)
class _ArchiveBudget:
    entries: int = 0
    uncompressed_bytes: int = 0


@dataclass(frozen=True, slots=True)
class _Finding:
    reason: str
    evidence: tuple[str, ...] = ()


_FIELD_SUFFIXES = (".ovf", ".omf", ".ovf.gz", ".omf.gz")
_OOMMF_MARKERS = (
    b"# oommf:",
    b"begin: data text",
    b"begin: data binary",
)
_DERIVED_KINDS = frozenset(("figure_slice", "figure_line", "scalar_summary"))


class _NumpyResourceError(ValueError):
    """Raised before an NPZ member set can exceed the inspection memory budget."""


class _EncryptedNumpyError(ValueError):
    """Raised before attempting to read an encrypted NPZ member."""


def stream_sha256(path: Path | str, *, chunk_size: int = 1024 * 1024) -> str:
    """Hash a regular file without loading it into memory."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _field_name(name: str) -> bool:
    lowered = name.casefold()
    return lowered.endswith(_FIELD_SUFFIXES)


def _suffix_container_kind(name: str) -> str | None:
    lowered = name.casefold()
    if lowered.endswith((".7z",)):
        return "7z"
    if lowered.endswith((".rar",)):
        return "rar"
    if lowered.endswith((".tar.zst", ".tzst", ".zst")):
        return "zstd"
    if lowered.endswith((".tar.gz", ".tgz", ".gz")):
        return "gzip"
    if lowered.endswith(".zip"):
        return "zip"
    if lowered.endswith(".tar"):
        return "tar"
    return None


def _magic_container_kind(prefix: bytes) -> str | None:
    if prefix.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    if prefix.startswith(b"\x1f\x8b"):
        return "gzip"
    if prefix.startswith(b"\x28\xb5\x2f\xfd"):
        return "zstd"
    if prefix.startswith(b"7z\xbc\xaf\x27\x1c"):
        return "7z"
    if prefix.startswith((b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00")):
        return "rar"
    if len(prefix) >= 262 and prefix[257:262] == b"ustar":
        return "tar"
    return None


def _read_prefix(path: Path, length: int = 4096) -> bytes:
    with path.open("rb") as handle:
        return handle.read(length)


def _has_oommf_marker(payload: bytes) -> bool:
    lowered = payload.lower()
    return any(marker in lowered for marker in _OOMMF_MARKERS)


def _result(
    *,
    decision: Decision,
    reason: str,
    sha256: str,
    size: int,
    file_type: str = "file",
    container_kind: str | None = None,
    link_target: str | None = None,
    evidence: tuple[str, ...] = (),
    array_shapes: tuple[str, ...] = (),
) -> InspectionResult:
    return InspectionResult(
        decision=decision,
        reason=reason,
        sha256=sha256,
        size=size,
        file_type=file_type,
        container_kind=container_kind,
        link_target=link_target,
        evidence=evidence,
        array_shapes=array_shapes,
    )


def _unsafe_archive_member(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = tuple(part for part in normalized.split("/") if part not in ("", "."))
    return normalized.startswith("/") or ".." in parts or (len(normalized) > 1 and normalized[1] == ":")


def _charge_budget(
    budget: _ArchiveBudget,
    *,
    entries: int,
    uncompressed_bytes: int,
    limits: InspectionLimits,
) -> _Finding | None:
    budget.entries += entries
    budget.uncompressed_bytes += uncompressed_bytes
    if (
        budget.entries > limits.max_archive_entries
        or budget.uncompressed_bytes > limits.max_archive_uncompressed_bytes
    ):
        return _Finding(
            "archive-resource-limit",
            (
                f"entries={budget.entries}",
                f"declared_uncompressed_bytes={budget.uncompressed_bytes}",
            ),
        )
    return None


def _read_bounded(handle: BinaryIO, limit: int) -> bytes | None:
    payload = handle.read(limit + 1)
    if len(payload) > limit:
        return None
    return payload


def _read_member_for_inspection(
    handle: BinaryIO,
    *,
    declared_size: int,
    name: str,
    limits: InspectionLimits,
) -> bytes | None:
    """Read only a prefix unless nested structure requires bounded full content."""
    prefix = handle.read(4096)
    needs_full_content = (
        name.casefold().endswith(".npy")
        or prefix.startswith(b"\x93NUMPY")
        or _magic_container_kind(prefix) is not None
        or _suffix_container_kind(name) is not None
    )
    if not needs_full_content:
        return prefix
    if declared_size > limits.max_nested_member_bytes:
        return None
    remaining_limit = limits.max_nested_member_bytes - len(prefix)
    remainder = _read_bounded(handle, remaining_limit)
    if remainder is None:
        return None
    return prefix + remainder


def _array_shape_label(name: str, array: np.ndarray) -> str:
    shape = "x".join(str(value) for value in array.shape)
    return f"{name}:{shape}" if name else shape


def _shape_is_complete(shape: tuple[int, ...], threshold: int) -> bool:
    if len(shape) == 2 and shape[0] >= threshold and shape[1] in (3, 6):
        return True
    if len(shape) == 4 and 3 in shape:
        vector_axis = shape.index(3)
        spatial_points = math.prod(
            value for index, value in enumerate(shape) if index != vector_axis
        )
        if spatial_points >= threshold:
            return True
    if len(shape) == 3 and all(value > 4 for value in shape):
        return math.prod(shape) >= threshold
    return False


def _arrays_are_complete(arrays: Mapping[str, np.ndarray], threshold: int) -> bool:
    shapes = [tuple(int(value) for value in array.shape) for array in arrays.values()]
    if any(_shape_is_complete(shape, threshold) for shape in shapes):
        return True
    three_dimensional = [shape for shape in shapes if len(shape) == 3]
    counts = Counter(three_dimensional)
    return any(count >= 3 and math.prod(shape) >= threshold for shape, count in counts.items())


def _load_numpy_path(
    path: Path, *, max_uncompressed_bytes: int
) -> dict[str, np.ndarray]:
    is_npz = zipfile.is_zipfile(path)
    if is_npz:
        with zipfile.ZipFile(path) as archive:
            if any(info.flag_bits & 0x1 for info in archive.infolist()):
                raise _EncryptedNumpyError("encrypted NPZ member")
            declared_size = sum(
                info.file_size for info in archive.infolist() if not info.is_dir()
            )
        if declared_size > max_uncompressed_bytes:
            raise _NumpyResourceError(
                f"declared numpy bytes {declared_size} exceed {max_uncompressed_bytes}"
            )
    loaded = np.load(
        path,
        allow_pickle=False,
        mmap_mode=None if is_npz else "r",
    )
    if isinstance(loaded, np.ndarray):
        if loaded.dtype.hasobject:
            raise ValueError("object arrays are not allowed")
        return {"": loaded}
    try:
        arrays: dict[str, np.ndarray] = {}
        for name in loaded.files:
            array = loaded[name]
            if array.dtype.hasobject:
                raise ValueError("object arrays are not allowed")
            arrays[name] = array
        return arrays
    finally:
        loaded.close()


def _load_npy_bytes(payload: bytes) -> dict[str, np.ndarray]:
    array = np.load(io.BytesIO(payload), allow_pickle=False)
    if not isinstance(array, np.ndarray) or array.dtype.hasobject:
        raise ValueError("unsafe array")
    return {"": array}


def _actual_shape_value(arrays: Mapping[str, np.ndarray]) -> str:
    if len(arrays) == 1:
        return "x".join(str(value) for value in next(iter(arrays.values())).shape)
    return ";".join(
        f"{name}:{'x'.join(str(value) for value in arrays[name].shape)}"
        for name in sorted(arrays)
    )


def _valid_derived_declaration(
    declaration: Mapping[str, object] | None,
    arrays: Mapping[str, np.ndarray],
) -> bool:
    if not declaration or declaration.get("data_kind") not in _DERIVED_KINDS:
        return False
    required = (
        "shape",
        "units",
        "producer_script",
        "parent_source",
        "parent_sha256",
    )
    if any(not isinstance(declaration.get(key), str) or not declaration[key] for key in required):
        return False
    if declaration.get("is_complete_field") is not False:
        return False
    if declaration["shape"] != _actual_shape_value(arrays):
        return False
    parent_sha = str(declaration["parent_sha256"])
    return len(parent_sha) == 64 and all(character in "0123456789abcdefABCDEF" for character in parent_sha)


def _inspect_numpy(
    path: Path,
    *,
    declaration: Mapping[str, object] | None,
    limits: InspectionLimits,
) -> tuple[_Finding | None, tuple[str, ...], bool]:
    try:
        arrays = _load_numpy_path(
            path, max_uncompressed_bytes=limits.max_numpy_uncompressed_bytes
        )
    except _EncryptedNumpyError as error:
        return _Finding("encrypted-archive", (str(error),)), (), False
    except _NumpyResourceError as error:
        return _Finding("numpy-resource-limit", (str(error),)), (), False
    except (OSError, ValueError, TypeError, zipfile.BadZipFile):
        return _Finding("unsafe-or-corrupt-numpy"), (), False
    shapes = tuple(
        _array_shape_label(name, arrays[name]) for name in sorted(arrays)
    )
    if not arrays:
        return _Finding("unsafe-or-corrupt-numpy", ("empty array container",)), shapes, False
    if _arrays_are_complete(arrays, limits.min_complete_field_points):
        return _Finding("complete-field-array", shapes), shapes, False
    if not _valid_derived_declaration(declaration, arrays):
        return _Finding("undeclared-derived-array", shapes), shapes, False
    return None, shapes, True


def _zip_looks_like_npz(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [info.filename for info in archive.infolist() if not info.is_dir()]
    except (OSError, zipfile.BadZipFile):
        return False
    return bool(names) and all(name.casefold().endswith(".npy") for name in names)


def _inspect_npy_member(payload: bytes, label: str, limits: InspectionLimits) -> _Finding | None:
    try:
        arrays = _load_npy_bytes(payload)
    except (OSError, ValueError, TypeError):
        return _Finding("unsafe-or-corrupt-numpy", (label,))
    if _arrays_are_complete(arrays, limits.min_complete_field_points):
        shapes = tuple(_array_shape_label(label, value) for value in arrays.values())
        return _Finding("complete-field-array", shapes)
    return None


def _nested_member_finding(
    *,
    name: str,
    payload: bytes,
    depth: int,
    budget: _ArchiveBudget,
    limits: InspectionLimits,
) -> _Finding | None:
    if _has_oommf_marker(payload[:4096]):
        return _Finding("archive-contains-field", (name, "OOMMF marker"))
    if name.casefold().endswith(".npy") or payload.startswith(b"\x93NUMPY"):
        finding = _inspect_npy_member(payload, name, limits)
        if finding:
            return finding
    kind = _magic_container_kind(payload[:4096]) or _suffix_container_kind(name)
    if kind is None:
        return None
    if depth >= limits.max_archive_depth:
        return _Finding("archive-depth-limit", (name, f"depth>{limits.max_archive_depth}"))
    return _inspect_archive_bytes(
        payload,
        kind=kind,
        label=name,
        depth=depth + 1,
        budget=budget,
        limits=limits,
    )


def _inspect_zip_handle(
    archive: zipfile.ZipFile,
    *,
    label: str,
    depth: int,
    budget: _ArchiveBudget,
    limits: InspectionLimits,
) -> _Finding | None:
    infos = archive.infolist()
    finding = _charge_budget(
        budget,
        entries=len(infos),
        uncompressed_bytes=sum(info.file_size for info in infos),
        limits=limits,
    )
    if finding:
        return finding
    for info in infos:
        member_label = f"{label}!{info.filename}"
        if info.flag_bits & 0x1:
            return _Finding("encrypted-archive", (member_label,))
        if _unsafe_archive_member(info.filename):
            return _Finding("unsafe-archive-member", (member_label,))
        if info.is_dir():
            continue
        if _field_name(info.filename):
            return _Finding("archive-contains-field", (member_label,))
        with archive.open(info) as handle:
            payload = _read_member_for_inspection(
                handle,
                declared_size=info.file_size,
                name=member_label,
                limits=limits,
            )
        if payload is None:
            return _Finding("archive-resource-limit", (member_label, "member too large"))
        finding = _nested_member_finding(
            name=member_label,
            payload=payload,
            depth=depth,
            budget=budget,
            limits=limits,
        )
        if finding:
            return finding
    return None


def _inspect_tar_handle(
    archive: tarfile.TarFile,
    *,
    label: str,
    depth: int,
    budget: _ArchiveBudget,
    limits: InspectionLimits,
) -> _Finding | None:
    for member in archive:
        finding = _charge_budget(
            budget,
            entries=1,
            uncompressed_bytes=member.size if member.isfile() else 0,
            limits=limits,
        )
        if finding:
            return finding
        member_label = f"{label}!{member.name}"
        if _unsafe_archive_member(member.name) or member.issym() or member.islnk():
            return _Finding("unsafe-archive-member", (member_label,))
        if not member.isfile():
            continue
        if _field_name(member.name):
            return _Finding("archive-contains-field", (member_label,))
        extracted = archive.extractfile(member)
        if extracted is None:
            return _Finding("corrupt-archive", (member_label,))
        with extracted:
            payload = _read_member_for_inspection(
                extracted,
                declared_size=member.size,
                name=member_label,
                limits=limits,
            )
        if payload is None:
            return _Finding("archive-resource-limit", (member_label, "member too large"))
        finding = _nested_member_finding(
            name=member_label,
            payload=payload,
            depth=depth,
            budget=budget,
            limits=limits,
        )
        if finding:
            return finding
    return None


def _unsupported_container_finding(kind: str, label: str) -> _Finding | None:
    if kind == "gzip":
        return _Finding("unsupported-gzip-stream", (label,))
    if kind == "zstd":
        return _Finding("unsupported-zstd-container", (label,))
    if kind in ("7z", "rar"):
        return _Finding("unsupported-container", (label, kind))
    return None


def _inspect_archive_path(
    path: Path,
    *,
    kind: str,
    limits: InspectionLimits,
) -> _Finding | None:
    unsupported = _unsupported_container_finding(kind, path.name)
    if unsupported:
        return unsupported
    budget = _ArchiveBudget()
    try:
        if kind == "zip":
            with zipfile.ZipFile(path) as archive:
                return _inspect_zip_handle(
                    archive,
                    label=path.name,
                    depth=1,
                    budget=budget,
                    limits=limits,
                )
        if kind == "tar":
            with tarfile.open(path, mode="r:") as archive:
                return _inspect_tar_handle(
                    archive,
                    label=path.name,
                    depth=1,
                    budget=budget,
                    limits=limits,
                )
    except (OSError, EOFError, tarfile.TarError, zipfile.BadZipFile, RuntimeError):
        return _Finding("corrupt-archive", (path.name,))
    return _Finding("unsupported-container", (path.name, kind))


def _inspect_archive_bytes(
    payload: bytes,
    *,
    kind: str,
    label: str,
    depth: int,
    budget: _ArchiveBudget,
    limits: InspectionLimits,
) -> _Finding | None:
    unsupported = _unsupported_container_finding(kind, label)
    if unsupported:
        return unsupported
    try:
        if kind == "zip":
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                return _inspect_zip_handle(
                    archive,
                    label=label,
                    depth=depth,
                    budget=budget,
                    limits=limits,
                )
        if kind == "tar":
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
                return _inspect_tar_handle(
                    archive,
                    label=label,
                    depth=depth,
                    budget=budget,
                    limits=limits,
                )
    except (OSError, EOFError, tarfile.TarError, zipfile.BadZipFile, RuntimeError):
        return _Finding("corrupt-archive", (label,))
    return _Finding("unsupported-container", (label, kind))


def _iter_data_lines(path: Path):
    with path.open("r", encoding="utf-8", errors="strict", newline=None) as handle:
        for line in handle:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                yield stripped


def _sample_indices(total: int, limits: InspectionLimits) -> frozenset[int]:
    indices = set(range(min(total, limits.text_head_rows)))
    indices.update(range(max(0, total - limits.text_tail_rows), total))
    even_count = min(total, limits.text_even_rows)
    if even_count == 1:
        indices.add(0)
    elif even_count > 1:
        indices.update(
            round(position * (total - 1) / (even_count - 1))
            for position in range(even_count)
        )
    return frozenset(indices)


def _finite_numeric_width(line: str) -> int | None:
    fields = line.replace(",", " ").split()
    try:
        values = tuple(float(field) for field in fields)
    except ValueError:
        return None
    if not values or not all(math.isfinite(value) for value in values):
        return None
    return len(values)


def _ordinary_table_declaration(
    declaration: Mapping[str, object] | None, width: int
) -> bool:
    if not declaration or declaration.get("data_kind") in _DERIVED_KINDS:
        return False
    columns = declaration.get("columns")
    units = declaration.get("units")
    if not isinstance(columns, str) or not columns or not isinstance(units, str) or not units:
        return False
    return len(columns.split(";")) == width


def _inspect_large_text(
    path: Path,
    *,
    size: int,
    declaration: Mapping[str, object] | None,
    limits: InspectionLimits,
) -> _Finding | None:
    if size < limits.min_suspect_text_bytes:
        return None
    try:
        total = sum(1 for _ in _iter_data_lines(path))
    except (OSError, UnicodeError):
        return None
    if total < limits.min_suspect_text_rows:
        return None
    wanted = _sample_indices(total, limits)
    widths: list[int | None] = []
    try:
        for index, line in enumerate(_iter_data_lines(path)):
            if index in wanted:
                widths.append(_finite_numeric_width(line))
    except (OSError, UnicodeError):
        return None
    if not widths:
        return None
    for width in (3, 6):
        ratio = sum(value == width for value in widths) / len(widths)
        if ratio >= 0.99:
            if _ordinary_table_declaration(declaration, width):
                return _Finding("declared-tabular-data", (f"width={width}", f"sampled={len(widths)}"))
            return _Finding(
                "complete-field-text",
                (f"width={width}", f"sampled={len(widths)}", f"ratio={ratio:.6f}"),
            )
    return None


def inspect_candidate(
    path: Path | str,
    *,
    declaration: Mapping[str, object] | None = None,
    declared_kind: str | None = None,
    limits: InspectionLimits | None = None,
) -> InspectionResult:
    """Inspect one candidate without following symlinks or parsing OVF payloads."""
    candidate = Path(path)
    active_limits = limits or InspectionLimits()
    if declared_kind is not None:
        declaration = dict(declaration or {})
        declaration.setdefault("data_kind", declared_kind)

    metadata = candidate.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        link_target = os.readlink(candidate)
        digest = hashlib.sha256(b"symlink\0" + os.fsencode(link_target)).hexdigest()
        return _result(
            decision="exclude",
            reason="symlink",
            sha256=digest,
            size=metadata.st_size,
            file_type="symlink",
            link_target=link_target,
            evidence=(link_target,),
        )
    if not stat.S_ISREG(metadata.st_mode):
        digest = hashlib.sha256(f"mode:{metadata.st_mode}".encode()).hexdigest()
        return _result(
            decision="exclude",
            reason="not-regular-file",
            sha256=digest,
            size=metadata.st_size,
            file_type="other",
        )

    digest = stream_sha256(candidate)
    size = metadata.st_size
    if _field_name(candidate.name):
        return _result(
            decision="exclude",
            reason="field-filename",
            sha256=digest,
            size=size,
            evidence=(candidate.name,),
        )

    prefix = _read_prefix(candidate)
    if _has_oommf_marker(prefix):
        return _result(
            decision="exclude",
            reason="oommf-content",
            sha256=digest,
            size=size,
            evidence=("OOMMF/Data marker in first 4096 bytes",),
        )

    numpy_candidate = (
        candidate.suffix.casefold() in (".npy", ".npz")
        or prefix.startswith(b"\x93NUMPY")
    )
    magic_kind = _magic_container_kind(prefix)
    if magic_kind == "zip" and not numpy_candidate and _zip_looks_like_npz(candidate):
        numpy_candidate = True
    if numpy_candidate:
        finding, shapes, allowed = _inspect_numpy(
            candidate, declaration=declaration, limits=active_limits
        )
        if finding:
            return _result(
                decision="exclude",
                reason=finding.reason,
                sha256=digest,
                size=size,
                evidence=finding.evidence,
                array_shapes=shapes,
            )
        if allowed:
            return _result(
                decision="include",
                reason="declared-figure-slice",
                sha256=digest,
                size=size,
                evidence=(str(declaration.get("producer_script")),),
                array_shapes=shapes,
            )

    container_kind = magic_kind or _suffix_container_kind(candidate.name)
    if container_kind:
        finding = _inspect_archive_path(
            candidate, kind=container_kind, limits=active_limits
        )
        if finding:
            return _result(
                decision="exclude",
                reason=finding.reason,
                sha256=digest,
                size=size,
                container_kind=container_kind,
                evidence=finding.evidence,
            )
        return _result(
            decision="include",
            reason="approved-archive",
            sha256=digest,
            size=size,
            container_kind=container_kind,
            evidence=("member names and bounded content inspected",),
        )

    text_finding = _inspect_large_text(
        candidate,
        size=size,
        declaration=declaration,
        limits=active_limits,
    )
    if text_finding:
        if text_finding.reason == "declared-tabular-data":
            return _result(
                decision="include",
                reason=text_finding.reason,
                sha256=digest,
                size=size,
                evidence=text_finding.evidence,
            )
        return _result(
            decision="exclude",
            reason=text_finding.reason,
            sha256=digest,
            size=size,
            evidence=text_finding.evidence,
        )

    return _result(
        decision="include",
        reason="approved",
        sha256=digest,
        size=size,
    )
