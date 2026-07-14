from __future__ import annotations

import hashlib
import io
import stat
import struct
import subprocess
import tarfile
import zipfile
import zlib
from pathlib import Path

import numpy as np
import pytest

from handoff_delivery import inventory as inventory_module
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


def _npy_bytes(array: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, array)
    return buffer.getvalue()


def _npy_header_bytes(shape: tuple[int, ...]) -> bytes:
    buffer = io.BytesIO()
    np.lib.format.write_array_header_1_0(
        buffer,
        {
            "descr": np.dtype(np.float64).str,
            "fortran_order": False,
            "shape": shape,
        },
    )
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


def _set_first_zip_compression_method(path: Path, method: int) -> None:
    payload = bytearray(path.read_bytes())
    local = payload.index(b"PK\x03\x04")
    central = payload.index(b"PK\x01\x02")
    struct.pack_into("<H", payload, local + 8, method)
    struct.pack_into("<H", payload, central + 10, method)
    path.write_bytes(payload)


def _corrupt_first_zip_member_compressed_data(path: Path) -> None:
    payload = bytearray(path.read_bytes())
    local = payload.index(b"PK\x03\x04")
    name_length, extra_length = struct.unpack_from("<HH", payload, local + 26)
    data_start = local + 30 + name_length + extra_length
    payload[data_start] ^= 0xFF
    path.write_bytes(payload)


def _corrupt_first_zip_member_compressed_middle(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        info = archive.infolist()[0]
    payload = bytearray(path.read_bytes())
    local = info.header_offset
    name_length, extra_length = struct.unpack_from("<HH", payload, local + 26)
    data_start = local + 30 + name_length + extra_length
    payload[data_start + info.compress_size // 2] ^= 0xFF
    path.write_bytes(payload)


def _set_first_zip_declared_output(path: Path, visible: bytes) -> None:
    payload = bytearray(path.read_bytes())
    local = payload.index(b"PK\x03\x04")
    central = payload.index(b"PK\x01\x02")
    crc = zlib.crc32(visible) & 0xFFFFFFFF
    struct.pack_into("<L", payload, local + 14, crc)
    struct.pack_into("<L", payload, local + 22, len(visible))
    struct.pack_into("<L", payload, central + 16, crc)
    struct.pack_into("<L", payload, central + 24, len(visible))
    path.write_bytes(payload)


def _shorten_first_zip_compressed_size(path: Path) -> None:
    payload = bytearray(path.read_bytes())
    local = payload.index(b"PK\x03\x04")
    central = payload.index(b"PK\x01\x02")
    compressed_size = struct.unpack_from("<L", payload, central + 20)[0]
    assert compressed_size > 1
    struct.pack_into("<L", payload, local + 18, compressed_size - 1)
    struct.pack_into("<L", payload, central + 20, compressed_size - 1)
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

    result = inspect_candidate(
        path,
        limits=InspectionLimits(
            min_suspect_text_bytes=1,
            min_suspect_text_rows=1,
        ),
    )

    assert result.decision == "exclude"
    assert result.reason == "oommf-content"


def test_real_inventory_source_with_quoted_oommf_markers_is_not_a_field():
    source = (
        Path(__file__).resolve().parents[2]
        / "95_shared_scripts"
        / "handoff_delivery"
        / "inventory.py"
    )

    result = inspect_candidate(source)

    assert result.decision == "include"
    assert result.reason == "approved"


@pytest.mark.parametrize(
    "payload",
    (
        b'marker = b"# OOMMF:"\n',
        b"print('# OOMMF: rectangular mesh v1.0')\n",
        b"The format documentation mentions # Begin: Data Text inline.\n",
        b"Use the quoted marker '# Begin: Data Binary' in this example.\n",
    ),
)
def test_quoted_or_inline_oommf_marker_mentions_are_not_fields(
    tmp_path: Path, payload: bytes
):
    path = tmp_path / "ordinary.txt"
    path.write_bytes(payload)

    result = inspect_candidate(path)

    assert result.decision == "include"
    assert result.reason == "approved"


@pytest.mark.parametrize(
    "header",
    (
        b"\xef\xbb\xbf# OOMMF: rectangular mesh v1.0\n",
        b"\xef\xbb\xbf\n\n  # oOmMf: rectangular mesh v1.0\n",
        b"\n\t# Begin: Data Text\n0 0 1\n",
        b"  # BEGIN: DATA BINARY 8\n",
    ),
)
def test_actual_oommf_header_lines_allow_bom_blanks_whitespace_and_case(
    tmp_path: Path, header: bytes
):
    path = tmp_path / "renamed.txt"
    path.write_bytes(header)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "oommf-content"


@pytest.mark.parametrize("container", ("zip", "tar"))
def test_actual_oommf_header_line_in_archive_member_is_rejected(
    tmp_path: Path, container: str
):
    payload = b"\xef\xbb\xbf\n  # Begin: Data Text\n0 0 1\n"
    members = {"padding.bin": b"x" * 8_192, "renamed.txt": payload}
    if container == "zip":
        path = _write_zip(tmp_path / "notes.zip", members)
    else:
        path = _write_tar(tmp_path / "notes.tar", members)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "archive-contains-field"


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


def test_tar_zstd_attempts_system_listing_and_detects_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "fields.tar.zst"
    path.write_bytes(b"\x28\xb5\x2f\xfdsynthetic")
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args, 0, stdout=b"notes.txt\ncase/M000001.OVF\n", stderr=b""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "archive-contains-field"
    assert calls
    args, kwargs = calls[0]
    assert args[:3] == ["tar", "--zstd", "--list"]
    assert "--file=-" in args
    assert str(path) not in args
    assert kwargs.get("stdin") is not None
    assert kwargs.get("shell", False) is False
    assert isinstance(kwargs.get("timeout"), (int, float))


def test_tar_zstd_benign_listing_is_attempted_but_not_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "notes.tar.zst"
    path.write_bytes(b"\x28\xb5\x2f\xfdsynthetic")
    calls = 0

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(args, 0, stdout=b"notes.txt\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = inspect_candidate(path)

    assert calls == 1
    assert result.decision == "exclude"
    assert result.reason == "unsupported-zstd-container"


@pytest.mark.parametrize("failure", ("missing", "timeout", "nonzero"))
def test_tar_zstd_listing_failures_are_attempted_and_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
):
    path = tmp_path / "broken.tar.zst"
    path.write_bytes(b"\x28\xb5\x2f\xfdsynthetic")
    calls = 0

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal calls
        calls += 1
        if failure == "missing":
            raise FileNotFoundError("tar")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 1)
        return subprocess.CompletedProcess(args, 2, stdout=b"", stderr=b"tar failed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = inspect_candidate(path)

    assert calls == 1
    assert result.decision == "exclude"
    assert result.reason == "unsupported-zstd-container"


@pytest.mark.parametrize("stdout", (b"../escape.txt\n", b"/absolute.txt\n", b"C:/drive.txt\n"))
def test_tar_zstd_listing_rejects_unsafe_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stdout: bytes
):
    path = tmp_path / "unsafe.tar.zst"
    path.write_bytes(b"\x28\xb5\x2f\xfdsynthetic")

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args, 0, stdout=stdout, stderr=b""
        ),
    )

    assert inspect_candidate(path).reason == "unsafe-archive-member"


def test_tar_zstd_listing_entry_and_output_limits_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "many.tar.zst"
    path.write_bytes(b"\x28\xb5\x2f\xfdsynthetic")

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args, 0, stdout=b"a\nb\n", stderr=b""
        ),
    )
    entries = inspect_candidate(path, limits=InspectionLimits(max_archive_entries=1))

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args, 0, stdout=b"a" * 5_000 + b"\n", stderr=b""
        ),
    )
    output = inspect_candidate(path, limits=InspectionLimits(max_archive_entries=1))

    assert entries.reason == "archive-resource-limit"
    assert output.reason == "archive-resource-limit"


def test_corrupt_archive_and_encrypted_zip_are_fail_closed(tmp_path: Path):
    corrupt = tmp_path / "broken.zip"
    corrupt.write_bytes(b"PK\x03\x04broken")
    encrypted = _write_zip(tmp_path / "encrypted.zip", {"notes.txt": b"secret"})
    _mark_first_zip_member_encrypted(encrypted)

    assert inspect_candidate(corrupt).reason == "corrupt-archive"
    assert inspect_candidate(encrypted).reason == "encrypted-archive"


@pytest.mark.parametrize(
    ("suffix", "expected_reason"),
    ((".zip", "corrupt-archive"), (".npz", "unsafe-or-corrupt-numpy")),
)
def test_deflated_zip_damage_never_leaks_zlib_error(
    tmp_path: Path, suffix: str, expected_reason: str
):
    if suffix == ".npz":
        members = {"m.npy": _npy_bytes(np.arange(1_024, dtype=np.int64))}
    else:
        members = {"notes.txt": bytes(range(256)) * 32}
    path = _write_zip(tmp_path / f"damaged{suffix}", members)
    _corrupt_first_zip_member_compressed_data(path)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == expected_reason


@pytest.mark.parametrize(
    ("suffix", "expected_reason"),
    ((".zip", "corrupt-archive"), (".npz", "unsafe-or-corrupt-numpy")),
)
def test_lzma_zip_damage_never_leaks_codec_error(
    tmp_path: Path, suffix: str, expected_reason: str
):
    if suffix == ".npz":
        members = {"m.npy": _npy_bytes(np.arange(1_024, dtype=np.int64))}
    else:
        members = {"notes.txt": bytes(range(256)) * 32}
    path = tmp_path / f"damaged{suffix}"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_LZMA) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    _corrupt_first_zip_member_compressed_middle(path)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == expected_reason


def test_zip_crc_is_verified_past_the_member_prefix(tmp_path: Path):
    path = tmp_path / "late-crc.zip"
    member_name = "notes.txt"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(member_name, b"a" * 8_192)
    payload = bytearray(path.read_bytes())
    local_header = payload.index(b"PK\x03\x04")
    name_length, extra_length = struct.unpack_from("<HH", payload, local_header + 26)
    member_start = local_header + 30 + name_length + extra_length
    payload[member_start + 5_000] ^= 0xFF
    path.write_bytes(payload)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "corrupt-archive"


@pytest.mark.parametrize("visible", (b"", b"ok"))
def test_zip_decoder_rejects_output_hidden_past_declared_size(
    tmp_path: Path, visible: bytes
):
    path = _write_zip(
        tmp_path / "hidden-output.zip",
        {"notes.txt": visible + b"# OOMMF: rectangular mesh\n"},
    )
    _set_first_zip_declared_output(path, visible)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "corrupt-archive"


def test_zip_decoder_requires_eof_at_declared_compressed_size(tmp_path: Path):
    path = _write_zip(
        tmp_path / "short-compressed-stream.zip",
        {"notes.txt": bytes(range(256)) * 16},
    )
    _shorten_first_zip_compressed_size(path)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "corrupt-archive"


def test_npz_member_cannot_hide_output_past_declared_npy(tmp_path: Path):
    visible = _npy_bytes(np.zeros((8, 8, 3)))
    path = _write_zip(
        tmp_path / "hidden-output.npz",
        {"m.npy": visible + b"hidden compressed output"},
    )
    _set_first_zip_declared_output(path, visible)

    result = inspect_candidate(path, declaration=_derived_declaration())

    assert result.decision == "exclude"
    assert result.reason == "unsafe-or-corrupt-numpy"


def test_zip_local_and_central_metadata_must_match(tmp_path: Path):
    path = _write_zip(tmp_path / "metadata-mismatch.zip", {"notes.txt": b"safe"})
    payload = bytearray(path.read_bytes())
    local = payload.index(b"PK\x03\x04")
    local_crc = struct.unpack_from("<L", payload, local + 14)[0]
    struct.pack_into("<L", payload, local + 14, local_crc ^ 1)
    path.write_bytes(payload)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "corrupt-archive"


@pytest.mark.parametrize(
    "compression",
    (
        zipfile.ZIP_STORED,
        zipfile.ZIP_DEFLATED,
        zipfile.ZIP_BZIP2,
        zipfile.ZIP_LZMA,
    ),
)
def test_zip_supported_codecs_pass_independent_stream_validation(
    tmp_path: Path, compression: int
):
    path = tmp_path / f"codec-{compression}.zip"
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        archive.writestr("notes.txt", bytes(range(256)) * 32)

    result = inspect_candidate(path)

    assert result.decision == "include"
    assert result.reason == "approved-archive"


@pytest.mark.parametrize("nested", (False, True))
def test_concatenated_zip_cannot_hide_an_earlier_archive(
    tmp_path: Path, nested: bool
):
    hidden = _zip_bytes({"hidden/state.ovf": b"field"})
    benign = _zip_bytes({"notes.txt": b"safe"})
    combined = hidden + benign
    if nested:
        path = _write_tar(tmp_path / "outer.tar", {"inner.zip": combined})
    else:
        path = tmp_path / "combined.zip"
        path.write_bytes(combined)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "corrupt-archive"


@pytest.mark.parametrize("nested", (False, True))
def test_zip_preamble_is_rejected_by_physical_layout(
    tmp_path: Path, nested: bool
):
    payload = b"MZ" + b"X" * 100 + _zip_bytes({"notes.txt": b"safe"})
    if nested:
        path = _write_tar(tmp_path / "outer.tar", {"inner.zip": payload})
    else:
        path = tmp_path / "self-extracting.zip"
        path.write_bytes(payload)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "corrupt-archive"


@pytest.mark.parametrize("nested", (False, True))
def test_zip_bytes_after_eocd_are_rejected(tmp_path: Path, nested: bool):
    payload = _zip_bytes({"notes.txt": b"safe"}) + b"unregistered tail"
    if nested:
        path = _write_tar(tmp_path / "outer.tar", {"inner.zip": payload})
    else:
        path = tmp_path / "trailing.zip"
        path.write_bytes(payload)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "corrupt-archive"


def test_zip_custom_comment_is_valid_layout(tmp_path: Path):
    path = tmp_path / "commented.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("notes.txt", b"safe")
        archive.comment = b"custom archive comment"

    result = inspect_candidate(path)

    assert result.decision == "include"
    assert result.reason == "approved-archive"


@pytest.mark.parametrize("nested", (False, True))
@pytest.mark.parametrize("damage", ("short-member", "missing-trailer"))
def test_tar_member_short_reads_and_missing_trailer_are_corrupt(
    tmp_path: Path, nested: bool, damage: str
):
    member = b"a" * 8_192
    valid = _write_tar(tmp_path / "valid.tar", {"notes.txt": member}).read_bytes()
    if damage == "short-member":
        damaged = valid[: 512 + 5_000]
    else:
        padded_member_size = ((len(member) + 511) // 512) * 512
        damaged = valid[: 512 + padded_member_size]
    if nested:
        path = _write_zip(tmp_path / "outer.zip", {"inner.tar": damaged})
    else:
        path = tmp_path / "damaged.tar"
        path.write_bytes(damaged)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "corrupt-archive"


@pytest.mark.parametrize("nested", (False, True))
def test_concatenated_tar_cannot_hide_field_after_first_end_marker(
    tmp_path: Path, nested: bool
):
    first = _write_tar(tmp_path / "first.tar", {"notes.txt": b"ok"}).read_bytes()
    second = _write_tar(
        tmp_path / "second.tar", {"hidden/state.ovf": b"synthetic"}
    ).read_bytes()
    concatenated = first + second
    if nested:
        path = _write_zip(tmp_path / "outer.zip", {"combined.tar": concatenated})
    else:
        path = tmp_path / "combined.tar"
        path.write_bytes(concatenated)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "archive-contains-field"
    assert any("state.ovf" in item for item in result.evidence)


def test_encrypted_npz_cannot_bypass_archive_encryption_check(tmp_path: Path):
    encrypted = _write_zip(tmp_path / "encrypted.npz", {"m.npy": b"not-an-array"})
    _mark_first_zip_member_encrypted(encrypted)

    result = inspect_candidate(encrypted)

    assert result.decision == "exclude"
    assert result.reason == "encrypted-archive"


def test_npz_rejects_non_npy_members_without_leaking_attribute_error(tmp_path: Path):
    path = _write_zip(
        tmp_path / "mixed.npz",
        {"m.npy": _npy_bytes(np.arange(3)), "README.txt": b"not an array"},
    )

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "unsafe-or-corrupt-numpy"


@pytest.mark.parametrize("member", ("../m.npy", "/m.npy", "C:/m.npy"))
def test_npz_rejects_unsafe_member_paths(tmp_path: Path, member: str):
    path = _write_zip(tmp_path / "unsafe.npz", {member: _npy_bytes(np.arange(3))})

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "unsafe-archive-member"


@pytest.mark.parametrize("duplicate_kind", ("raw", "logical"))
def test_npz_rejects_duplicate_members_and_logical_keys(
    tmp_path: Path, duplicate_kind: str
):
    path = tmp_path / "duplicate.npz"
    payload = _npy_bytes(np.arange(3))
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("m.npy", payload)
        if duplicate_kind == "raw":
            with pytest.warns(UserWarning, match="Duplicate name"):
                archive.writestr("m.npy", payload)
        else:
            archive.writestr("./m.npy", payload)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "unsafe-or-corrupt-numpy"


def test_npz_unsupported_compression_is_stably_fail_closed(tmp_path: Path):
    path = _write_zip(tmp_path / "unsupported.npz", {"m.npy": _npy_bytes(np.arange(3))})
    _set_first_zip_compression_method(path, 99)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "unsafe-or-corrupt-numpy"


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


def test_default_archive_limits_remain_at_specified_hard_caps():
    limits = InspectionLimits()

    assert limits.max_archive_depth == 2
    assert limits.max_archive_entries == 100_000
    assert limits.max_archive_uncompressed_bytes == 5 * 1024**3


@pytest.mark.parametrize("container", ("zip", "tar"))
def test_archive_member_path_traversal_is_rejected(tmp_path: Path, container: str):
    if container == "zip":
        path = _write_zip(tmp_path / "traversal.zip", {"../escape": b"bad"})
    else:
        path = _write_tar(tmp_path / "traversal.tar", {"../escape": b"bad"})

    assert inspect_candidate(path).reason == "unsafe-archive-member"


@pytest.mark.parametrize("link_type", (tarfile.SYMTYPE, tarfile.LNKTYPE))
def test_tar_symbolic_and_hard_links_are_rejected(
    tmp_path: Path, link_type: bytes
):
    path = tmp_path / "links.tar"
    with tarfile.open(path, "w") as archive:
        link = tarfile.TarInfo("link")
        link.type = link_type
        link.linkname = "../outside"
        archive.addfile(link)

    assert inspect_candidate(path).reason == "unsafe-archive-member"


def test_tar_non_regular_entry_with_payload_is_rejected(tmp_path: Path):
    path = tmp_path / "nonempty-directory.tar"
    payload = b"# OOMMF: rectangular mesh\n" + b"x" * 100_000
    with tarfile.open(path, "w") as archive:
        ordinary_directory = tarfile.TarInfo("ordinary/")
        ordinary_directory.type = tarfile.DIRTYPE
        archive.addfile(ordinary_directory)

        padding = tarfile.TarInfo("padding.bin")
        padding.size = 8_192
        archive.addfile(padding, io.BytesIO(b"x" * padding.size))

        disguised_payload = tarfile.TarInfo("state.ovf")
        disguised_payload.type = tarfile.DIRTYPE
        disguised_payload.size = len(payload)
        archive.addfile(disguised_payload, io.BytesIO(payload))

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "unsafe-archive-member"


def test_zip_unix_symlink_member_is_rejected(tmp_path: Path):
    path = tmp_path / "links.zip"
    link = zipfile.ZipInfo("link-to-outside")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(link, b"../outside")

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "unsafe-archive-member"


def test_zip_directory_entry_with_payload_is_rejected(tmp_path: Path):
    path = _write_zip(
        tmp_path / "nonempty-directory.zip",
        {
            "ordinary/": b"",
            "state.ovf/": b"# OOMMF: rectangular mesh\n" + b"x" * 100_000,
        },
    )

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "unsafe-archive-member"


def test_zip_empty_directory_stream_is_still_verified(tmp_path: Path):
    path = _write_zip(tmp_path / "damaged-empty-directory.zip", {"empty/": b""})
    _corrupt_first_zip_member_compressed_data(path)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "corrupt-archive"


@pytest.mark.parametrize("container", ("zip", "tar"))
def test_archive_members_reject_undeclared_non_field_numpy(
    tmp_path: Path, container: str
):
    payload = _npy_bytes(np.arange(8, dtype=np.float64))
    if container == "zip":
        path = _write_zip(tmp_path / "mixed.zip", {"notes.txt": b"ok", "data.npy": payload})
    else:
        path = _write_tar(tmp_path / "mixed.tar", {"notes.txt": b"ok", "data.npy": payload})

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "undeclared-derived-array"
    assert any("data.npy" in item for item in result.evidence)


def test_nested_numpy_uses_numpy_uncompressed_budget(tmp_path: Path):
    payload = _npy_bytes(np.arange(128, dtype=np.uint8))
    path = _write_zip(
        tmp_path / "mixed.zip", {"notes.txt": b"ok", "data.npy": payload}
    )

    result = inspect_candidate(
        path,
        limits=InspectionLimits(
            max_numpy_uncompressed_bytes=64,
            max_nested_member_bytes=1_024,
        ),
    )

    assert result.decision == "exclude"
    assert result.reason == "numpy-resource-limit"


def _small_text_limits() -> InspectionLimits:
    return InspectionLimits(
        min_suspect_text_bytes=1,
        min_suspect_text_rows=5,
        text_head_rows=2,
        text_even_rows=3,
        text_tail_rows=2,
    )


@pytest.mark.parametrize("container", ("zip", "tar"))
@pytest.mark.parametrize("row", (b"0.1 0.2 0.3\n", b"0 0 0 0.1 0.2 0.3\n"))
def test_archives_reject_headerless_complete_field_text(
    tmp_path: Path, container: str, row: bytes
):
    members = {"notes.txt": b"ok", "vectors.csv": row * 10}
    if container == "zip":
        path = _write_zip(tmp_path / "vectors.zip", members)
    else:
        path = _write_tar(tmp_path / "vectors.tar", members)

    result = inspect_candidate(path, limits=_small_text_limits())

    assert result.decision == "exclude"
    assert result.reason == "complete-field-text"
    assert any("vectors.csv" in item for item in result.evidence)


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


def test_text_sampling_checks_every_row_below_6144(tmp_path: Path):
    total = 5_000
    old_sample = set(range(1_024))
    old_sample.update(range(total - 1_024, total))
    old_sample.update(
        round(position * (total - 1) / (4_096 - 1))
        for position in range(4_096)
    )
    missed = [index for index in range(total) if index not in old_sample]
    assert len(missed) >= 60
    rows = ["1 2 3\n"] * total
    for index in missed[:60]:
        rows[index] = "1 2 3 4\n"
    path = tmp_path / "mixed-width.txt"
    path.write_text("".join(rows))

    result = inspect_candidate(
        path,
        limits=InspectionLimits(
            min_suspect_text_bytes=1,
            min_suspect_text_rows=1,
        ),
    )

    assert result.decision == "include"
    assert result.reason == "approved"


@pytest.mark.parametrize("container", ("plain", "zip"))
def test_text_line_length_is_bounded_and_fail_closed(
    tmp_path: Path, container: str
):
    payload = b"x" * (1024 * 1024 + 1)
    if container == "plain":
        path = tmp_path / "one-line.txt"
        path.write_bytes(payload)
    else:
        path = _write_zip(tmp_path / "one-line.zip", {"one-line.txt": payload})

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "text-resource-limit"


def test_suspect_three_column_text_with_invalid_utf8_is_fail_closed(tmp_path: Path):
    path = tmp_path / "malformed-vectors.txt"
    path.write_bytes(b"0.1 0.2 0.3\n" * 10 + b"\xff\n")

    result = inspect_candidate(path, limits=_small_text_limits())

    assert result.decision == "exclude"
    assert result.reason == "unreadable-suspect-text"
    assert "UnicodeDecodeError" in result.evidence


def test_small_binary_is_not_rejected_as_suspect_text(tmp_path: Path):
    path = tmp_path / "small-binary.dat"
    path.write_bytes(b"ordinary\xffbinary")

    result = inspect_candidate(path)

    assert result.decision == "include"
    assert result.reason == "approved"


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


@pytest.mark.parametrize("width", (3, 6))
@pytest.mark.parametrize(
    "schema_error",
    ("blank-column", "wrong-column-count", "blank-unit", "wrong-unit-count"),
)
def test_ordinary_three_and_six_column_tables_reject_invalid_schema(
    tmp_path: Path, width: int, schema_error: str
):
    path = tmp_path / f"table-{width}.csv"
    path.write_text((" ".join(str(index) for index in range(width)) + "\n") * 10)
    columns = [f"c{index}" for index in range(width)]
    units = ["1"] * width
    if schema_error == "blank-column":
        columns[1] = " "
    elif schema_error == "wrong-column-count":
        columns.pop()
    elif schema_error == "blank-unit":
        units[1] = " "
    else:
        units = ["1", "1"]
    declaration = {
        "data_kind": "timeseries",
        "columns": ";".join(columns),
        "units": ";".join(units),
    }

    result = inspect_candidate(
        path, declaration=declaration, limits=_small_text_limits()
    )

    assert result.decision == "exclude"
    assert result.reason == "complete-field-text"


@pytest.mark.parametrize("width", (3, 6))
@pytest.mark.parametrize("unit_count", (1, "width"))
def test_ordinary_table_units_may_be_scalar_or_per_column(
    tmp_path: Path, width: int, unit_count: int | str
):
    path = tmp_path / f"valid-table-{width}.csv"
    path.write_text((" ".join(str(index) for index in range(width)) + "\n") * 10)
    units = ["1"] * (width if unit_count == "width" else 1)
    declaration = {
        "data_kind": "timeseries",
        "columns": ";".join(f"c{index}" for index in range(width)),
        "units": ";".join(units),
    }

    result = inspect_candidate(
        path, declaration=declaration, limits=_small_text_limits()
    )

    assert result.decision == "include"
    assert result.reason == "declared-tabular-data"


@pytest.mark.parametrize(
    ("data_kind", "shape", "rows"),
    (
        ("figure_slice", "8x8x3", 64),
        ("figure_line", "8x3", 8),
        ("scalar_summary", "1x3", 1),
    ),
)
def test_declared_derived_text_is_measured_and_explicitly_allowed(
    tmp_path: Path, data_kind: str, shape: str, rows: int
):
    path = tmp_path / f"{data_kind}.csv"
    path.write_text("0.1,0.2,0.3\n" * rows)
    declaration = _derived_declaration(shape=shape)
    declaration["data_kind"] = data_kind

    result = inspect_candidate(
        path,
        declaration=declaration,
        limits=_small_text_limits(),
    )

    assert result.decision == "include"
    assert result.reason == "declared-derived-text"
    assert f"rows={rows}" in result.evidence
    assert "columns=3" in result.evidence


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("data_kind", "timeseries"),
        ("shape", "7x8x3"),
        ("columns", "mx;my"),
        ("units", "1;1"),
        ("producer_script", ""),
        ("parent_source", ""),
        ("parent_sha256", "not-a-sha256"),
        ("is_complete_field", True),
    ),
)
def test_derived_text_rejects_incomplete_or_false_manifest_evidence(
    tmp_path: Path, field: str, value: object
):
    path = tmp_path / "slice.csv"
    path.write_text("0.1,0.2,0.3\n" * 64)
    declaration = _derived_declaration()
    declaration[field] = value

    result = inspect_candidate(
        path,
        declaration=declaration,
        limits=_small_text_limits(),
    )

    assert result.decision == "exclude"
    assert result.reason == "invalid-derived-declaration"


def test_declared_derived_text_cannot_allow_a_complete_3d_field(tmp_path: Path):
    path = tmp_path / "volume.csv"
    path.write_text("0.1,0.2,0.3\n" * 125)
    declaration = _derived_declaration(shape="5x5x5x3")

    result = inspect_candidate(
        path,
        declaration=declaration,
        limits=InspectionLimits(
            min_suspect_text_bytes=1,
            min_suspect_text_rows=5,
            min_complete_field_points=100,
        ),
    )

    assert result.decision == "exclude"
    assert result.reason == "complete-field-text"


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


@pytest.mark.parametrize(
    ("data_kind", "shape"),
    (
        ("figure_slice", "mx:8x8;my:8x8;mz:8x8"),
        ("figure_line", "8x3"),
        ("scalar_summary", "1x3"),
    ),
)
@pytest.mark.parametrize("evidence_field", ("columns", "units"))
def test_numpy_derived_evidence_must_match_measured_logical_width(
    tmp_path: Path, data_kind: str, shape: str, evidence_field: str
):
    path = tmp_path / f"{data_kind}.npz"
    if data_kind == "figure_slice":
        np.savez(
            path,
            mx=np.zeros((8, 8)),
            my=np.zeros((8, 8)),
            mz=np.zeros((8, 8)),
        )
    elif data_kind == "figure_line":
        np.savez(path, values=np.zeros((8, 3)))
    else:
        np.savez(path, values=np.zeros((1, 3)))
    declaration = _derived_declaration(shape=shape)
    declaration["data_kind"] = data_kind
    declaration[evidence_field] = "first;second"

    result = inspect_candidate(path, declaration=declaration)

    assert result.decision == "exclude"
    assert result.reason == "undeclared-derived-array"


@pytest.mark.parametrize(
    ("data_kind", "shape"),
    (
        ("figure_slice", "mx:8x8;my:8x8;mz:8x8"),
        ("figure_line", "8x3"),
        ("scalar_summary", "1x3"),
    ),
)
def test_numpy_derived_evidence_accepts_measured_logical_width(
    tmp_path: Path, data_kind: str, shape: str
):
    path = tmp_path / f"valid-{data_kind}.npz"
    if data_kind == "figure_slice":
        np.savez(
            path,
            mx=np.zeros((8, 8)),
            my=np.zeros((8, 8)),
            mz=np.zeros((8, 8)),
        )
    elif data_kind == "figure_line":
        np.savez(path, values=np.zeros((8, 3)))
    else:
        np.savez(path, values=np.zeros((1, 3)))
    declaration = _derived_declaration(shape=shape)
    declaration["data_kind"] = data_kind

    result = inspect_candidate(path, declaration=declaration)

    assert result.decision == "include"


def test_numpy_derived_declaration_requires_nonempty_columns(tmp_path: Path):
    path = tmp_path / "slice.npz"
    np.savez(path, m=np.zeros((8, 8, 3)))
    declaration = _derived_declaration()
    declaration.pop("columns")

    result = inspect_candidate(
        path,
        declaration=declaration,
        limits=InspectionLimits(min_complete_field_points=10),
    )

    assert result.decision == "exclude"
    assert result.reason == "undeclared-derived-array"


@pytest.mark.parametrize(
    "field", ("columns", "units", "producer_script", "parent_source")
)
def test_numpy_derived_declaration_rejects_blank_string_evidence(
    tmp_path: Path, field: str
):
    path = tmp_path / "slice.npz"
    np.savez(path, m=np.zeros((8, 8, 3)))
    declaration = _derived_declaration()
    declaration[field] = "   "

    result = inspect_candidate(
        path,
        declaration=declaration,
        limits=InspectionLimits(min_complete_field_points=10),
    )

    assert result.decision == "exclude"
    assert result.reason == "undeclared-derived-array"


@pytest.mark.parametrize("data_format", ("npz", "csv"))
@pytest.mark.parametrize("field", ("columns", "units"))
def test_derived_declaration_rejects_blank_semicolon_tokens(
    tmp_path: Path, data_format: str, field: str
):
    declaration = _derived_declaration()
    declaration[field] = " ; ; "
    if data_format == "npz":
        path = tmp_path / "slice.npz"
        np.savez(path, m=np.zeros((8, 8, 3)))
        expected_reason = "undeclared-derived-array"
    else:
        path = tmp_path / "slice.csv"
        path.write_text("0.1,0.2,0.3\n" * 64)
        expected_reason = "invalid-derived-declaration"

    result = inspect_candidate(path, declaration=declaration)

    assert result.decision == "exclude"
    assert result.reason == expected_reason


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


def test_npz_entry_count_uses_archive_entry_budget(tmp_path: Path):
    path = tmp_path / "two-arrays.npz"
    np.savez(path, a=np.zeros((1,)), b=np.zeros((1,)))
    declaration = _derived_declaration(shape="a:1;b:1")
    declaration["columns"] = "a;b"

    result = inspect_candidate(
        path,
        declaration=declaration,
        limits=InspectionLimits(max_archive_entries=1),
    )

    assert result.decision == "exclude"
    assert result.reason == "archive-resource-limit"


@pytest.mark.parametrize("container", ("npy", "npz"))
def test_numpy_header_budget_is_checked_before_np_load_or_array_allocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    container: str,
):
    header = _npy_header_bytes((100_000_000,))
    if container == "npy":
        path = tmp_path / "huge.npy"
        path.write_bytes(header)
    else:
        path = _write_zip(tmp_path / "huge.npz", {"m.npy": header})

    def forbidden_np_load(*args: object, **kwargs: object) -> None:
        raise AssertionError("np.load must not run before the header budget check")

    monkeypatch.setattr(inventory_module.np, "load", forbidden_np_load)

    result = inspect_candidate(
        path,
        limits=InspectionLimits(max_numpy_uncompressed_bytes=1_024),
    )

    assert result.decision == "exclude"
    assert result.reason == "numpy-resource-limit"


def test_raw_npy_file_size_uses_numpy_budget(tmp_path: Path):
    path = tmp_path / "raw.npy"
    np.save(path, np.arange(128, dtype=np.uint8))

    result = inspect_candidate(
        path,
        limits=InspectionLimits(max_numpy_uncompressed_bytes=64),
    )

    assert result.decision == "exclude"
    assert result.reason == "numpy-resource-limit"


@pytest.mark.parametrize("container", ("npy", "npz"))
def test_numpy_negative_shape_dimensions_are_never_declared_safe(
    tmp_path: Path, container: str
):
    payload = _npy_header_bytes((-1, -1)) + b"\0" * 8
    if container == "npy":
        path = tmp_path / "negative.npy"
        path.write_bytes(payload)
    else:
        path = _write_zip(tmp_path / "negative.npz", {"m.npy": payload})

    result = inspect_candidate(
        path,
        declaration=_derived_declaration(shape="-1x-1"),
    )

    assert result.decision == "exclude"
    assert result.reason == "unsafe-or-corrupt-numpy"


@pytest.mark.parametrize("container", ("npy", "npz"))
def test_numpy_subarray_dtype_is_never_declared_safe(
    tmp_path: Path, container: str
):
    buffer = io.BytesIO()
    np.lib.format.write_array_header_1_0(
        buffer,
        {
            "descr": ("<f8", (3,)),
            "fortran_order": False,
            "shape": (100,),
        },
    )
    payload = buffer.getvalue() + b"\0" * 2_400
    if container == "npy":
        path = tmp_path / "subarray.npy"
        path.write_bytes(payload)
    else:
        path = _write_zip(tmp_path / "subarray.npz", {"m.npy": payload})

    result = inspect_candidate(
        path,
        declaration=_derived_declaration(shape="100"),
    )

    assert result.decision == "exclude"
    assert result.reason == "unsafe-or-corrupt-numpy"


@pytest.mark.parametrize("container", ("npy", "npz"))
def test_numpy_zero_width_dtype_and_unrepresentable_shape_are_rejected(
    tmp_path: Path, container: str
):
    buffer = io.BytesIO()
    np.lib.format.write_array_header_1_0(
        buffer,
        {
            "descr": "|V0",
            "fortran_order": False,
            "shape": (10**20,),
        },
    )
    payload = buffer.getvalue()
    if container == "npy":
        path = tmp_path / "zero-width.npy"
        path.write_bytes(payload)
    else:
        path = _write_zip(tmp_path / "zero-width.npz", {"m.npy": payload})

    result = inspect_candidate(
        path,
        declaration=_derived_declaration(shape=str(10**20)),
    )

    assert result.decision == "exclude"
    assert result.reason == "unsafe-or-corrupt-numpy"


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


@pytest.mark.parametrize("mutation", ("replace-with-symlink", "continue-writing"))
def test_candidate_mutation_during_inspection_is_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
):
    path = tmp_path / "candidate.txt"
    path.write_text("safe notes\n")
    replacement = tmp_path / "replacement.txt"
    replacement.write_text("different object\n")
    original_marker_check = inventory_module._has_oommf_marker
    mutated = False

    def mutate_after_prefix(prefix: bytes) -> bool:
        nonlocal mutated
        if not mutated:
            mutated = True
            if mutation == "replace-with-symlink":
                path.unlink()
                path.symlink_to(replacement.name)
            else:
                with path.open("ab") as handle:
                    handle.write(b"continued write\n")
        return original_marker_check(prefix)

    monkeypatch.setattr(inventory_module, "_has_oommf_marker", mutate_after_prefix)

    result = inspect_candidate(path)

    assert result.decision == "exclude"
    assert result.reason == "unstable-file-identity"
