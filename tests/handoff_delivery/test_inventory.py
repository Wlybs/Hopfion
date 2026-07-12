from __future__ import annotations

import hashlib
import io
import struct
import tarfile
import zipfile
from pathlib import Path

import numpy as np
import pytest

from handoff_delivery.inventory import InspectionLimits, inspect_candidate, stream_sha256


def _write_zip(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return path


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def _mark_first_zip_member_encrypted(path: Path) -> None:
    payload = bytearray(path.read_bytes())
    local = payload.index(b"PK\x03\x04")
    central = payload.index(b"PK\x01\x02")
    local_flags = struct.unpack_from("<H", payload, local + 6)[0] | 0x1
    central_flags = struct.unpack_from("<H", payload, central + 8)[0] | 0x1
    struct.pack_into("<H", payload, local + 6, local_flags)
    struct.pack_into("<H", payload, central + 8, central_flags)
    path.write_bytes(payload)


def _write_tar(path: Path, members: dict[str, bytes]) -> Path:
    with tarfile.open(path, "w") as archive:
        for name, payload in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return path


def _derived_declaration(*, shape: str = "8x8x3") -> dict[str, object]:
    return {
        "data_kind": "figure_slice",
        "shape": shape,
        "columns": "mx;my;mz",
        "units": "dimensionless",
        "producer_script": "shared/initial_state/extract_slice.py",
        "parent_source": "source/m000001.ovf",
        "parent_sha256": "a" * 64,
        "is_complete_field": False,
    }


@pytest.mark.parametrize(
    "header",
    (
        "# OOMMF: rectangular mesh v1.0\n0 0 1\n",
        "# Begin: Data Text\n0 0 1\n",
        "# Begin: Data Binary 4\n",
    ),
)
def test_oommf_markers_are_rejected_even_with_txt_suffix(tmp_path: Path, header: str):
    path = tmp_path / "innocent.txt"
    path.write_text(header)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "oommf-content"


@pytest.mark.parametrize("name", ("field.ovf", "field.omf", "field.OVF.GZ"))
def test_literal_field_names_are_rejected_without_opening_payload(tmp_path: Path, name: str):
    path = tmp_path / name
    path.write_bytes(b"not parsed as a field")

    assert inspect_candidate(path).reason == "field-filename"


def test_zip_magic_and_nested_member_names_cannot_be_hidden_by_suffix(tmp_path: Path):
    nested = _zip_bytes({"deep/m000001.ovf": b"field"})
    path = _write_zip(tmp_path / "renamed.bin", {"inner.dat": nested})

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "archive-contains-field"
    assert any("m000001.ovf" in item for item in result.evidence)


def test_tar_magic_cannot_be_hidden_and_field_member_is_rejected(tmp_path: Path):
    path = _write_tar(tmp_path / "renamed.data", {"case/state.omf": b"field"})

    result = inspect_candidate(path)

    assert result.reason == "archive-contains-field"


def test_benign_zip_is_inspected_and_allowed(tmp_path: Path):
    path = _write_zip(tmp_path / "notes.bin", {"README.md": b"handoff notes"})

    result = inspect_candidate(path)

    assert result.decision == "include"
    assert result.reason == "approved-archive"
    assert result.container_kind == "zip"


@pytest.mark.parametrize(
    ("magic", "reason"),
    (
        (b"\x1f\x8b\x08\x00", "unsupported-gzip-stream"),
        (b"\x28\xb5\x2f\xfd", "unsupported-zstd-container"),
        (b"7z\xbc\xaf\x27\x1c", "unsupported-container"),
        (b"Rar!\x1a\x07\x00", "unsupported-container"),
    ),
)
def test_unsupported_compression_is_fail_closed_by_magic(
    tmp_path: Path, magic: bytes, reason: str
):
    path = tmp_path / "renamed.txt"
    path.write_bytes(magic + b"payload")

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == reason


def test_corrupt_archive_and_encrypted_zip_are_fail_closed(tmp_path: Path):
    corrupt = tmp_path / "broken.zip"
    corrupt.write_bytes(b"PK\x03\x04broken")
    encrypted = _write_zip(tmp_path / "encrypted.zip", {"notes.txt": b"secret"})
    _mark_first_zip_member_encrypted(encrypted)

    assert inspect_candidate(corrupt).reason == "corrupt-archive"
    assert inspect_candidate(encrypted).reason == "encrypted-archive"


def test_encrypted_npz_cannot_bypass_archive_encryption_check(tmp_path: Path):
    encrypted = _write_zip(tmp_path / "encrypted.npz", {"m.npy": b"not-an-array"})
    _mark_first_zip_member_encrypted(encrypted)

    result = inspect_candidate(encrypted)

    assert result.decision == "exclude"
    assert result.reason in {"encrypted-archive", "unsafe-or-corrupt-numpy"}


def test_archive_depth_entry_and_declared_size_limits_fail_closed(tmp_path: Path):
    third = _zip_bytes({"notes.txt": b"ok"})
    second = _zip_bytes({"third.zip": third})
    deep = _write_zip(tmp_path / "deep.zip", {"second.zip": second})
    many = _write_zip(tmp_path / "many.zip", {"a": b"1", "b": b"2"})
    large = _write_zip(tmp_path / "large.zip", {"a": b"12345"})

    assert inspect_candidate(deep).reason == "archive-depth-limit"
    assert (
        inspect_candidate(many, limits=InspectionLimits(max_archive_entries=1)).reason
        == "archive-resource-limit"
    )
    assert (
        inspect_candidate(
            large, limits=InspectionLimits(max_archive_uncompressed_bytes=4)
        ).reason
        == "archive-resource-limit"
    )


def _small_text_limits() -> InspectionLimits:
    return InspectionLimits(
        min_suspect_text_bytes=1,
        min_suspect_text_rows=5,
        text_head_rows=2,
        text_even_rows=3,
        text_tail_rows=2,
    )


@pytest.mark.parametrize(
    "row",
    (
        "0.1 0.2 0.3\n",
        "0 0 0 0.1 0.2 0.3\n",
    ),
)
def test_deterministic_large_text_detection_rejects_vector_field_layouts(
    tmp_path: Path, row: str
):
    path = tmp_path / "field.csv"
    path.write_text("# comment\n" + row * 10)

    first = inspect_candidate(path, limits=_small_text_limits())
    second = inspect_candidate(path, limits=_small_text_limits())

    assert first == second
    assert first.reason == "complete-field-text"


def test_declared_ordinary_table_schema_is_not_misclassified_as_field(tmp_path: Path):
    path = tmp_path / "table.csv"
    path.write_text("0 0 0 0.1 0.2 0.3\n" * 10)
    declaration = {
        "data_kind": "timeseries",
        "columns": "t;x;y;mx;my;mz",
        "units": "s;m;m;1;1;1",
    }

    result = inspect_candidate(
        path, declaration=declaration, limits=_small_text_limits()
    )

    assert result.decision == "include"
    assert result.reason == "declared-tabular-data"


def test_non_field_large_text_is_allowed(tmp_path: Path):
    path = tmp_path / "four-columns.txt"
    path.write_text("1 2 3 4\n" * 10)

    assert inspect_candidate(path, limits=_small_text_limits()).decision == "include"


def test_numpy_complete_field_shapes_are_measured_not_trusted(tmp_path: Path):
    vector_volume = tmp_path / "vector_volume.npy"
    flat_vectors = tmp_path / "flat_vectors.npy"
    components = tmp_path / "components.npz"
    np.save(vector_volume, np.zeros((5, 5, 5, 3)))
    np.save(flat_vectors, np.zeros((100, 3)))
    np.savez(
        components,
        mx=np.zeros((5, 5, 5)),
        my=np.zeros((5, 5, 5)),
        mz=np.zeros((5, 5, 5)),
    )
    limits = InspectionLimits(min_complete_field_points=100)

    assert inspect_candidate(vector_volume, limits=limits).reason == "complete-field-array"
    assert inspect_candidate(flat_vectors, limits=limits).reason == "complete-field-array"
    assert inspect_candidate(components, limits=limits).reason == "complete-field-array"


def test_numpy_slice_needs_complete_manifest_evidence_and_actual_safe_shape(tmp_path: Path):
    path = tmp_path / "slice.npz"
    np.savez(path, m=np.zeros((8, 8, 3)))

    undeclared = inspect_candidate(path, limits=InspectionLimits(min_complete_field_points=10))
    declared = inspect_candidate(
        path,
        declaration=_derived_declaration(),
        limits=InspectionLimits(min_complete_field_points=10),
    )

    assert undeclared.reason == "undeclared-derived-array"
    assert declared.decision == "include"
    assert declared.reason == "declared-figure-slice"


def test_false_manifest_claim_cannot_allow_complete_numpy_field(tmp_path: Path):
    path = tmp_path / "volume.npz"
    np.savez(path, m=np.zeros((5, 5, 5, 3)))

    result = inspect_candidate(
        path,
        declaration=_derived_declaration(shape="5x5x5x3"),
        limits=InspectionLimits(min_complete_field_points=100),
    )

    assert result.reason == "complete-field-array"


def test_pickle_dependent_numpy_payload_is_fail_closed(tmp_path: Path):
    path = tmp_path / "objects.npy"
    np.save(path, np.array([{"unsafe": True}], dtype=object), allow_pickle=True)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "unsafe-or-corrupt-numpy"


def test_numpy_declared_expansion_limit_is_fail_closed_before_array_load(tmp_path: Path):
    path = tmp_path / "large.npz"
    np.savez(path, m=np.zeros((8, 8, 3)))

    result = inspect_candidate(
        path, limits=InspectionLimits(max_numpy_uncompressed_bytes=16)
    )

    assert result.decision == "exclude"
    assert result.reason == "numpy-resource-limit"


def test_streaming_sha_metadata_and_symlink_inventory_do_not_follow_target(tmp_path: Path):
    target = tmp_path / "target.txt"
    target.write_text("# OOMMF: rectangular mesh v1.0\n")
    link = tmp_path / "link.txt"
    link.symlink_to(target.name)

    target_result = inspect_candidate(target)
    link_result = inspect_candidate(link)

    assert stream_sha256(target) == hashlib.sha256(target.read_bytes()).hexdigest()
    assert target_result.reason == "oommf-content"
    assert link_result.reason == "symlink"
    assert link_result.link_target == target.name
    assert link_result.sha256 != target_result.sha256
