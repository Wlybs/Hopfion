"""Fail-closed, content-level inventory checks for delivery candidates.

The inventory layer deliberately does not parse OVF payloads.  It identifies field
files by name, container membership, OOMMF markers, and measurable array/text
shapes.  The separate derived-data producer is the only component allowed to read
source OVF files.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
import hashlib
import lzma
import math
import os
from pathlib import Path
import stat
import struct
import subprocess
import tarfile
import tempfile
from typing import BinaryIO, Literal, Mapping
import zipfile
import zlib

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
    max_text_line_bytes: int = 1024 * 1024
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
            self.max_text_line_bytes,
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
_MEMBER_SPOOL_MEMORY_BYTES = 1024 * 1024
_TAR_ZSTD_LIST_TIMEOUT_SECONDS = 30
_MAX_TAR_ZSTD_LISTING_BYTES = 16 * 1024 * 1024
_TAR_ZSTD_BYTES_PER_ENTRY = 4096


class _NumpyResourceError(ValueError):
    """Raised before an NPZ member set can exceed the inspection memory budget."""


class _NumpyArchiveResourceError(ValueError):
    """Raised before an NPZ can exceed the shared archive entry budget."""


class _EncryptedNumpyError(ValueError):
    """Raised before attempting to read an encrypted NPZ member."""


class _UnsafeNumpyMemberError(ValueError):
    """Raised when an NPZ member path or type is unsafe."""


class _UnsafeNumpyContainerError(ValueError):
    """Raised when an NPZ has ambiguous or unsupported structure."""


class _UnsafeNumpyPayloadError(ValueError):
    """Raised when an NPY payload is structurally unsafe or truncated."""


class _TextResourceError(ValueError):
    """Raised before an untrusted text line can consume unbounded memory."""


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


def _drain_archive_member(
    handle: BinaryIO,
    *,
    prefix: bytes,
    declared_size: int,
    spool: BinaryIO | None = None,
) -> None:
    """Consume one member to EOF, optionally spooling it without unbounded RAM."""
    actual_size = len(prefix)
    if spool is not None:
        spool.write(prefix)
    while chunk := handle.read(1024 * 1024):
        actual_size += len(chunk)
        if actual_size > declared_size:
            raise tarfile.ReadError(
                f"member size mismatch: declared {declared_size}, read more"
            )
        if spool is not None:
            spool.write(chunk)
    if actual_size != declared_size:
        raise tarfile.ReadError(
            f"member size mismatch: declared {declared_size}, read {actual_size}"
        )
    if spool is not None:
        spool.seek(0)


def _validate_empty_zip_directory_stream(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    label: str,
    limits: InspectionLimits,
) -> _Finding | None:
    """Validate compressed bytes that ``ZipExtFile`` skips for a zero-size entry."""
    if info.compress_size > limits.max_nested_member_bytes:
        return _Finding(
            "archive-resource-limit",
            (label, f"compressed_bytes={info.compress_size}"),
        )
    if info.compress_type == zipfile.ZIP_STORED:
        if info.compress_size != 0:
            raise zipfile.BadZipFile("stored empty directory has compressed bytes")
        return None
    if info.compress_type != zipfile.ZIP_DEFLATED:
        return _Finding("corrupt-archive", (label, "unverified directory codec"))

    source = archive.fp
    if source is None:
        raise zipfile.BadZipFile("closed ZIP while validating directory")
    original_position = source.tell()
    try:
        source.seek(info.header_offset)
        local_header = source.read(30)
        if len(local_header) != 30 or local_header[:4] != b"PK\x03\x04":
            raise zipfile.BadZipFile("invalid local ZIP header")
        local_flags, local_method = struct.unpack_from("<HH", local_header, 6)
        name_length, extra_length = struct.unpack_from("<HH", local_header, 26)
        if local_flags & 0x1 or local_method != info.compress_type:
            raise zipfile.BadZipFile("ZIP local header disagrees with directory")
        source.seek(name_length + extra_length, os.SEEK_CUR)

        decompressor = zlib.decompressobj(-15)
        remaining = info.compress_size
        while remaining:
            chunk = source.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise zipfile.BadZipFile("truncated directory compression stream")
            remaining -= len(chunk)
            if decompressor.decompress(chunk, 1):
                raise zipfile.BadZipFile("empty directory expands to data")
            if decompressor.unconsumed_tail:
                raise zipfile.BadZipFile("directory stream expands beyond zero bytes")
        if decompressor.flush():
            raise zipfile.BadZipFile("empty directory expands to data")
        if not decompressor.eof or decompressor.unused_data:
            raise zipfile.BadZipFile("invalid directory compression stream")
    finally:
        source.seek(original_position)
    return None


def _array_shape_label(name: str, shape: tuple[int, ...]) -> str:
    shape_value = "x".join(str(value) for value in shape)
    return f"{name}:{shape_value}" if name else shape_value


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


def _shapes_are_complete(
    shapes_by_name: Mapping[str, tuple[int, ...]], threshold: int
) -> bool:
    shapes = list(shapes_by_name.values())
    if any(_shape_is_complete(shape, threshold) for shape in shapes):
        return True
    three_dimensional = [shape for shape in shapes if len(shape) == 3]
    counts = Counter(three_dimensional)
    return any(count >= 3 and math.prod(shape) >= threshold for shape, count in counts.items())


def _canonical_archive_member(name: str) -> str:
    normalized = name.replace("\\", "/")
    return "/".join(
        part for part in normalized.split("/") if part not in ("", ".")
    )


def _validate_npz_infos(
    infos: list[zipfile.ZipInfo],
    *,
    max_archive_entries: int,
    max_uncompressed_bytes: int,
) -> None:
    if len(infos) > max_archive_entries:
        raise _NumpyArchiveResourceError(
            f"NPZ entries {len(infos)} exceed {max_archive_entries}"
        )
    if any(info.flag_bits & 0x1 for info in infos):
        raise _EncryptedNumpyError("encrypted NPZ member")
    for info in infos:
        mode = info.external_attr >> 16
        if _unsafe_archive_member(info.filename) or stat.S_ISLNK(mode):
            raise _UnsafeNumpyMemberError(info.filename)

    raw_names = [info.filename for info in infos]
    if len(raw_names) != len(set(raw_names)):
        raise _UnsafeNumpyContainerError("duplicate NPZ member name")
    if any(info.is_dir() or not info.filename.casefold().endswith(".npy") for info in infos):
        raise _UnsafeNumpyContainerError("NPZ contains a non-NPY member")

    logical_keys = [
        _canonical_archive_member(info.filename)[:-4].casefold() for info in infos
    ]
    if len(logical_keys) != len(set(logical_keys)):
        raise _UnsafeNumpyContainerError("duplicate NPZ logical key")
    declared_size = sum(info.file_size for info in infos)
    if declared_size > max_uncompressed_bytes:
        raise _NumpyResourceError(
            f"declared numpy bytes {declared_size} exceed {max_uncompressed_bytes}"
        )


def _read_npy_shape(
    handle: BinaryIO,
    *,
    declared_size: int,
    max_uncompressed_bytes: int,
) -> tuple[int, ...]:
    if declared_size > max_uncompressed_bytes:
        raise _NumpyResourceError(
            f"declared numpy bytes {declared_size} exceed {max_uncompressed_bytes}"
        )
    try:
        handle.seek(0)
        version = np.lib.format.read_magic(handle)
        shape, _fortran_order, dtype_value = np.lib.format._read_array_header(
            handle, version
        )
        dtype = np.dtype(dtype_value)
        normalized_shape = tuple(int(value) for value in shape)
        if any(value < 0 for value in normalized_shape):
            raise _UnsafeNumpyPayloadError("negative NPY shape dimension")
        if any(value > np.iinfo(np.intp).max for value in normalized_shape):
            raise _UnsafeNumpyPayloadError("NPY shape dimension exceeds np.intp")
        if dtype.subdtype is not None:
            raise _UnsafeNumpyPayloadError("subarray dtype")
        if dtype.itemsize <= 0:
            raise _UnsafeNumpyPayloadError("zero-width dtype")
        data_offset = handle.tell()
        data_size = math.prod(normalized_shape) * dtype.itemsize
    except MemoryError as error:
        raise _NumpyResourceError("NumPy header exhausted memory") from error
    except (
        EOFError,
        OSError,
        OverflowError,
        struct.error,
        SyntaxError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as error:
        raise _UnsafeNumpyPayloadError("invalid NPY header") from error
    if dtype.hasobject:
        raise _UnsafeNumpyPayloadError("object dtype")
    if data_size > max_uncompressed_bytes:
        raise _NumpyResourceError(
            f"array bytes {data_size} exceed {max_uncompressed_bytes}"
        )
    if data_offset + data_size != declared_size:
        raise _UnsafeNumpyPayloadError("NPY size mismatch")
    actual_size = data_offset
    while chunk := handle.read(1024 * 1024):
        actual_size += len(chunk)
        if actual_size > declared_size:
            raise _UnsafeNumpyPayloadError("NPY contains trailing data")
    if actual_size != declared_size:
        raise _UnsafeNumpyPayloadError("truncated NPY payload")
    return normalized_shape


def _load_numpy_shapes(
    path: Path,
    *,
    max_archive_entries: int,
    max_uncompressed_bytes: int,
) -> dict[str, tuple[int, ...]]:
    is_npz = zipfile.is_zipfile(path)
    if is_npz:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            _validate_npz_infos(
                infos,
                max_archive_entries=max_archive_entries,
                max_uncompressed_bytes=max_uncompressed_bytes,
            )
            shapes: dict[str, tuple[int, ...]] = {}
            for info in infos:
                logical_key = _canonical_archive_member(info.filename)[:-4]
                with archive.open(info) as member:
                    shapes[logical_key] = _read_npy_shape(
                        member,
                        declared_size=info.file_size,
                        max_uncompressed_bytes=max_uncompressed_bytes,
                    )
            return shapes
    declared_size = path.stat().st_size
    with path.open("rb") as handle:
        return {
            "": _read_npy_shape(
                handle,
                declared_size=declared_size,
                max_uncompressed_bytes=max_uncompressed_bytes,
            )
        }


def _actual_shape_value(shapes: Mapping[str, tuple[int, ...]]) -> str:
    if len(shapes) == 1:
        return "x".join(str(value) for value in next(iter(shapes.values())))
    return ";".join(
        f"{name}:{'x'.join(str(value) for value in shapes[name])}"
        for name in sorted(shapes)
    )


def _valid_derived_declaration(
    declaration: Mapping[str, object] | None,
    shapes: Mapping[str, tuple[int, ...]],
) -> bool:
    if not _valid_derived_metadata(declaration):
        return False
    assert declaration is not None
    if declaration["shape"] != _actual_shape_value(shapes):
        return False
    return True


def _valid_derived_metadata(
    declaration: Mapping[str, object] | None,
) -> bool:
    if not declaration or declaration.get("data_kind") not in _DERIVED_KINDS:
        return False
    required = (
        "shape",
        "columns",
        "units",
        "producer_script",
        "parent_source",
        "parent_sha256",
    )
    if any(
        not isinstance(declaration.get(key), str) or not declaration[key].strip()
        for key in required
    ):
        return False
    if any(
        not token.strip()
        for key in ("columns", "units")
        for token in str(declaration[key]).split(";")
    ):
        return False
    if declaration.get("is_complete_field") is not False:
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
        shapes_by_name = _load_numpy_shapes(
            path,
            max_archive_entries=limits.max_archive_entries,
            max_uncompressed_bytes=limits.max_numpy_uncompressed_bytes,
        )
    except _EncryptedNumpyError as error:
        return _Finding("encrypted-archive", (str(error),)), (), False
    except _UnsafeNumpyMemberError as error:
        return _Finding("unsafe-archive-member", (str(error),)), (), False
    except _UnsafeNumpyContainerError as error:
        return _Finding("unsafe-or-corrupt-numpy", (str(error),)), (), False
    except _UnsafeNumpyPayloadError as error:
        return _Finding("unsafe-or-corrupt-numpy", (str(error),)), (), False
    except _NumpyArchiveResourceError as error:
        return _Finding("archive-resource-limit", (str(error),)), (), False
    except _NumpyResourceError as error:
        return _Finding("numpy-resource-limit", (str(error),)), (), False
    except (
        AttributeError,
        EOFError,
        MemoryError,
        NotImplementedError,
        OSError,
        OverflowError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        lzma.LZMAError,
        zlib.error,
    ):
        return _Finding("unsafe-or-corrupt-numpy"), (), False
    shape_labels = tuple(
        _array_shape_label(name, shapes_by_name[name])
        for name in sorted(shapes_by_name)
    )
    if not shapes_by_name:
        return _Finding("unsafe-or-corrupt-numpy", ("empty array container",)), shape_labels, False
    if _shapes_are_complete(shapes_by_name, limits.min_complete_field_points):
        return _Finding("complete-field-array", shape_labels), shape_labels, False
    if not _valid_derived_declaration(declaration, shapes_by_name):
        return _Finding("undeclared-derived-array", shape_labels), shape_labels, False
    return None, shape_labels, True


def _zip_looks_like_npz(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [info.filename for info in archive.infolist() if not info.is_dir()]
    except (OSError, zipfile.BadZipFile):
        return False
    return bool(names) and all(name.casefold().endswith(".npy") for name in names)


def _inspect_npy_fileobj(
    handle: BinaryIO,
    *,
    declared_size: int,
    label: str,
    limits: InspectionLimits,
) -> _Finding:
    """Inspect NPY metadata without materializing the declared array."""
    try:
        normalized_shape = _read_npy_shape(
            handle,
            declared_size=declared_size,
            max_uncompressed_bytes=limits.max_numpy_uncompressed_bytes,
        )
    except _NumpyResourceError as error:
        return _Finding(
            "numpy-resource-limit",
            (label, str(error)),
        )
    except _UnsafeNumpyPayloadError as error:
        return _Finding("unsafe-or-corrupt-numpy", (label, str(error)))
    shape_label = f"{label}:{'x'.join(str(value) for value in normalized_shape)}"
    if _shape_is_complete(normalized_shape, limits.min_complete_field_points):
        return _Finding("complete-field-array", (shape_label,))
    return _Finding("undeclared-derived-array", (shape_label,))


def _inspect_archive_member_handle(
    *,
    name: str,
    handle: BinaryIO,
    declared_size: int,
    depth: int,
    budget: _ArchiveBudget,
    limits: InspectionLimits,
) -> _Finding | None:
    prefix = handle.read(4096)
    is_numpy = name.casefold().endswith(".npy") or prefix.startswith(b"\x93NUMPY")
    kind = _magic_container_kind(prefix) or _suffix_container_kind(name)
    if is_numpy and declared_size > limits.max_numpy_uncompressed_bytes:
        return _Finding(
            "numpy-resource-limit",
            (name, f"declared_numpy_bytes={declared_size}"),
        )
    if kind is not None and declared_size > limits.max_nested_member_bytes:
        return _Finding("archive-resource-limit", (name, "member too large"))

    needs_spool = (
        is_numpy
        or kind is not None
        or declared_size >= limits.min_suspect_text_bytes
        or declared_size > limits.max_text_line_bytes
    )
    if not needs_spool:
        _drain_archive_member(
            handle, prefix=prefix, declared_size=declared_size
        )
        if _has_oommf_marker(prefix):
            return _Finding("archive-contains-field", (name, "OOMMF marker"))
        return None

    with tempfile.SpooledTemporaryFile(
        max_size=_MEMBER_SPOOL_MEMORY_BYTES, mode="w+b"
    ) as spool:
        _drain_archive_member(
            handle,
            prefix=prefix,
            declared_size=declared_size,
            spool=spool,
        )
        if _has_oommf_marker(prefix):
            return _Finding("archive-contains-field", (name, "OOMMF marker"))
        if is_numpy:
            return _inspect_npy_fileobj(
                spool,
                declared_size=declared_size,
                label=name,
                limits=limits,
            )
        if kind is not None:
            if depth >= limits.max_archive_depth:
                return _Finding(
                    "archive-depth-limit",
                    (name, f"depth>{limits.max_archive_depth}"),
                )
            return _inspect_archive_fileobj(
                spool,
                kind=kind,
                label=name,
                depth=depth + 1,
                budget=budget,
                limits=limits,
            )
        finding = _inspect_large_text_fileobj(
            spool,
            size=declared_size,
            declaration=None,
            limits=limits,
        )
        if finding:
            return _Finding(finding.reason, (name, *finding.evidence))
    return None


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
        if stat.S_ISLNK(info.external_attr >> 16):
            return _Finding("unsafe-archive-member", (member_label, "symlink"))
        if info.is_dir():
            if info.file_size != 0:
                return _Finding(
                    "unsafe-archive-member", (member_label, "directory has payload")
                )
            with archive.open(info) as handle:
                handle.read(1)
            finding = _validate_empty_zip_directory_stream(
                archive,
                info,
                label=member_label,
                limits=limits,
            )
            if finding:
                return finding
            continue
        if _field_name(info.filename):
            return _Finding("archive-contains-field", (member_label,))
        with archive.open(info) as handle:
            finding = _inspect_archive_member_handle(
                name=member_label,
                handle=handle,
                declared_size=info.file_size,
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
            uncompressed_bytes=max(member.size, 0),
            limits=limits,
        )
        if finding:
            return finding
        member_label = f"{label}!{member.name}"
        if _unsafe_archive_member(member.name) or member.issym() or member.islnk():
            return _Finding("unsafe-archive-member", (member_label,))
        if not member.isfile():
            if member.size != 0:
                return _Finding(
                    "unsafe-archive-member", (member_label, "non-file has payload")
                )
            continue
        if _field_name(member.name):
            return _Finding("archive-contains-field", (member_label,))
        extracted = archive.extractfile(member)
        if extracted is None:
            return _Finding("corrupt-archive", (member_label,))
        with extracted:
            finding = _inspect_archive_member_handle(
                name=member_label,
                handle=extracted,
                declared_size=member.size,
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


def _tar_has_standard_trailer(handle: BinaryIO) -> bool:
    original_position = handle.tell()
    try:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        if size < 1024 or size % 512:
            return False
        handle.seek(-1024, os.SEEK_END)
        return handle.read(1024) == b"\0" * 1024
    finally:
        handle.seek(original_position)


def _inspect_tar_zstd_path(
    path: Path, *, limits: InspectionLimits
) -> _Finding:
    listing_limit = min(
        _MAX_TAR_ZSTD_LISTING_BYTES,
        limits.max_archive_entries * _TAR_ZSTD_BYTES_PER_ENTRY,
    )
    command = [
        "tar",
        "--zstd",
        "--list",
        "--quoting-style=escape",
        "--file",
        str(path),
    ]
    environment = dict(os.environ)
    environment["LC_ALL"] = "C"
    with tempfile.SpooledTemporaryFile(
        max_size=_MEMBER_SPOOL_MEMORY_BYTES, mode="w+b"
    ) as listing_output, tempfile.SpooledTemporaryFile(
        max_size=_MEMBER_SPOOL_MEMORY_BYTES, mode="w+b"
    ) as error_output:
        try:
            completed = subprocess.run(
                command,
                check=False,
                env=environment,
                shell=False,
                stderr=error_output,
                stdout=listing_output,
                timeout=_TAR_ZSTD_LIST_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return _Finding(
                "unsupported-zstd-container",
                (path.name, f"tar listing failed: {type(error).__name__}"),
            )
        returned_stdout = completed.stdout
        returned_stderr = completed.stderr
        if isinstance(returned_stdout, bytes):
            stdout = returned_stdout
        else:
            if listing_output.tell() > listing_limit:
                return _Finding(
                    "archive-resource-limit",
                    (path.name, f"listing_bytes>{listing_limit}"),
                )
            listing_output.seek(0)
            stdout = listing_output.read(listing_limit + 1)
        if isinstance(returned_stderr, bytes):
            stderr = returned_stderr
        else:
            if error_output.tell() > listing_limit:
                return _Finding(
                    "archive-resource-limit",
                    (path.name, f"listing_bytes>{listing_limit}"),
                )
            error_output.seek(0)
            stderr = error_output.read(listing_limit + 1)
    if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
        return _Finding(
            "unsupported-zstd-container", (path.name, "unparseable tar output")
        )
    if len(stdout) > listing_limit or len(stderr) > listing_limit:
        return _Finding(
            "archive-resource-limit",
            (path.name, f"listing_bytes>{listing_limit}"),
        )
    if completed.returncode != 0 or stderr:
        return _Finding(
            "unsupported-zstd-container",
            (path.name, f"tar returncode={completed.returncode}"),
        )
    try:
        listing = stdout.decode("utf-8", errors="strict")
    except UnicodeError:
        return _Finding(
            "unsupported-zstd-container", (path.name, "non-UTF-8 tar listing")
        )
    if listing and not listing.endswith("\n"):
        return _Finding(
            "unsupported-zstd-container", (path.name, "truncated tar listing")
        )
    names = listing.splitlines()
    if len(names) > limits.max_archive_entries:
        return _Finding(
            "archive-resource-limit",
            (path.name, f"entries={len(names)}"),
        )
    for name in names:
        if (
            not name
            or "\\" in name
            or any(ord(character) < 32 for character in name)
        ):
            return _Finding(
                "unsupported-zstd-container",
                (path.name, "ambiguous tar listing"),
            )
        if _unsafe_archive_member(name):
            return _Finding("unsafe-archive-member", (f"{path.name}!{name}",))
        if _field_name(name):
            return _Finding("archive-contains-field", (f"{path.name}!{name}",))
    return _Finding(
        "unsupported-zstd-container",
        (path.name, "listing cannot verify member content or nesting"),
    )


def _inspect_archive_path(
    path: Path,
    *,
    kind: str,
    limits: InspectionLimits,
) -> _Finding | None:
    if kind == "zstd":
        return _inspect_tar_zstd_path(path, limits=limits)
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
            with path.open("rb") as handle:
                if not _tar_has_standard_trailer(handle):
                    return _Finding("corrupt-archive", (path.name, "missing tar trailer"))
            with tarfile.open(path, mode="r:", ignore_zeros=True) as archive:
                return _inspect_tar_handle(
                    archive,
                    label=path.name,
                    depth=1,
                    budget=budget,
                    limits=limits,
                )
    except _NumpyResourceError as error:
        return _Finding("numpy-resource-limit", (str(error),))
    except (
        OSError,
        EOFError,
        tarfile.TarError,
        zipfile.BadZipFile,
        lzma.LZMAError,
        RuntimeError,
        zlib.error,
    ):
        return _Finding("corrupt-archive", (path.name,))
    return _Finding("unsupported-container", (path.name, kind))


def _inspect_archive_fileobj(
    handle: BinaryIO,
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
        handle.seek(0)
        if kind == "zip":
            with zipfile.ZipFile(handle) as archive:
                return _inspect_zip_handle(
                    archive,
                    label=label,
                    depth=depth,
                    budget=budget,
                    limits=limits,
                )
        if kind == "tar":
            if not _tar_has_standard_trailer(handle):
                return _Finding("corrupt-archive", (label, "missing tar trailer"))
            with tarfile.open(
                fileobj=handle, mode="r:", ignore_zeros=True
            ) as archive:
                return _inspect_tar_handle(
                    archive,
                    label=label,
                    depth=depth,
                    budget=budget,
                    limits=limits,
                )
    except _NumpyResourceError as error:
        return _Finding("numpy-resource-limit", (str(error),))
    except (
        OSError,
        EOFError,
        tarfile.TarError,
        zipfile.BadZipFile,
        lzma.LZMAError,
        RuntimeError,
        zlib.error,
    ):
        return _Finding("corrupt-archive", (label,))
    return _Finding("unsupported-container", (label, kind))


def _iter_data_lines_binary(
    handle: BinaryIO, *, max_line_bytes: int
) -> Iterator[str]:
    while raw_line := handle.readline(max_line_bytes + 1):
        if len(raw_line) > max_line_bytes:
            raise _TextResourceError(f"text line exceeds {max_line_bytes} bytes")
        line = raw_line.decode("utf-8", errors="strict")
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            yield stripped


def _iter_data_lines(path: Path, *, max_line_bytes: int) -> Iterator[str]:
    with path.open("rb") as handle:
        yield from _iter_data_lines_binary(
            handle, max_line_bytes=max_line_bytes
        )


def _iter_data_lines_fileobj(
    handle: BinaryIO, *, max_line_bytes: int
) -> Iterator[str]:
    handle.seek(0)
    yield from _iter_data_lines_binary(
        handle, max_line_bytes=max_line_bytes
    )


def _sample_indices(total: int, limits: InspectionLimits) -> frozenset[int]:
    if total < limits.text_head_rows + limits.text_even_rows + limits.text_tail_rows:
        return frozenset(range(total))
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


def _derived_declaration_attempt(
    declaration: Mapping[str, object] | None,
) -> bool:
    if not declaration:
        return False
    return declaration.get("data_kind") in _DERIVED_KINDS or any(
        key in declaration
        for key in (
            "shape",
            "producer_script",
            "parent_source",
            "parent_sha256",
            "is_complete_field",
        )
    )


def _parse_shape(shape: object) -> tuple[int, ...] | None:
    if not isinstance(shape, str) or not shape:
        return None
    parts = shape.split("x")
    if not parts or any(not part.isdecimal() for part in parts):
        return None
    dimensions = tuple(int(part) for part in parts)
    return dimensions if all(value > 0 for value in dimensions) else None


def _measure_derived_text(
    path: Path,
    declared_columns: tuple[str, ...],
    *,
    max_line_bytes: int,
) -> tuple[int, int] | None:
    rows = 0
    width: int | None = None
    saw_header = False
    try:
        for stripped in _iter_data_lines(
            path, max_line_bytes=max_line_bytes
        ):
            measured_width = _finite_numeric_width(stripped)
            if measured_width is None:
                header = tuple(stripped.replace(",", " ").split())
                if rows == 0 and not saw_header and header == declared_columns:
                    saw_header = True
                    continue
                return None
            if width is None:
                width = measured_width
            elif measured_width != width:
                return None
            rows += 1
    except (OSError, UnicodeError):
        return None
    if rows == 0 or width is None:
        return None
    return rows, width


def _text_shape_matches(
    shape: tuple[int, ...], *, rows: int, width: int
) -> bool:
    if width == 1 and math.prod(shape) == rows:
        return True
    return (
        len(shape) >= 2
        and shape[-1] == width
        and math.prod(shape[:-1]) == rows
    )


def _inspect_derived_text(
    path: Path,
    *,
    declaration: Mapping[str, object] | None,
    limits: InspectionLimits,
) -> _Finding:
    if not _valid_derived_metadata(declaration):
        return _Finding("invalid-derived-declaration")
    assert declaration is not None
    columns = tuple(
        value.strip() for value in str(declaration["columns"]).split(";")
    )
    units = tuple(
        value.strip() for value in str(declaration["units"]).split(";")
    )
    shape = _parse_shape(declaration["shape"])
    if (
        shape is None
        or not columns
        or any(not value for value in columns)
        or not units
        or any(not value for value in units)
    ):
        return _Finding("invalid-derived-declaration")
    try:
        measured = _measure_derived_text(
            path,
            columns,
            max_line_bytes=limits.max_text_line_bytes,
        )
    except _TextResourceError as error:
        return _Finding("text-resource-limit", (str(error),))
    if measured is None:
        return _Finding("invalid-derived-data")
    rows, width = measured
    if (
        len(columns) != width
        or len(units) not in (1, width)
        or not _text_shape_matches(shape, rows=rows, width=width)
    ):
        return _Finding("invalid-derived-declaration")
    evidence = (f"rows={rows}", f"columns={width}", f"shape={declaration['shape']}")
    if _shape_is_complete(shape, limits.min_complete_field_points) or _shape_is_complete(
        (rows, width), limits.min_complete_field_points
    ):
        return _Finding("complete-field-text", evidence)
    return _Finding("declared-derived-text", evidence)


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


def _inspect_large_text_rows(
    iter_lines: Callable[[], Iterator[str]],
    *,
    size: int,
    declaration: Mapping[str, object] | None,
    limits: InspectionLimits,
) -> _Finding | None:
    if (
        size < limits.min_suspect_text_bytes
        and size <= limits.max_text_line_bytes
    ):
        return None
    try:
        total = sum(1 for _ in iter_lines())
    except _TextResourceError as error:
        return _Finding("text-resource-limit", (str(error),))
    except (OSError, UnicodeError):
        return None
    if size < limits.min_suspect_text_bytes:
        return None
    if total < limits.min_suspect_text_rows:
        return None
    wanted = _sample_indices(total, limits)
    widths: list[int | None] = []
    try:
        for index, line in enumerate(iter_lines()):
            if index in wanted:
                widths.append(_finite_numeric_width(line))
    except _TextResourceError as error:
        return _Finding("text-resource-limit", (str(error),))
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


def _inspect_large_text(
    path: Path,
    *,
    size: int,
    declaration: Mapping[str, object] | None,
    limits: InspectionLimits,
) -> _Finding | None:
    return _inspect_large_text_rows(
        lambda: _iter_data_lines(
            path, max_line_bytes=limits.max_text_line_bytes
        ),
        size=size,
        declaration=declaration,
        limits=limits,
    )


def _inspect_large_text_fileobj(
    handle: BinaryIO,
    *,
    size: int,
    declaration: Mapping[str, object] | None,
    limits: InspectionLimits,
) -> _Finding | None:
    return _inspect_large_text_rows(
        lambda: _iter_data_lines_fileobj(
            handle, max_line_bytes=limits.max_text_line_bytes
        ),
        size=size,
        declaration=declaration,
        limits=limits,
    )


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

    if _derived_declaration_attempt(declaration):
        finding = _inspect_derived_text(
            candidate,
            declaration=declaration,
            limits=active_limits,
        )
        return _result(
            decision="include" if finding.reason == "declared-derived-text" else "exclude",
            reason=finding.reason,
            sha256=digest,
            size=size,
            evidence=finding.evidence,
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
