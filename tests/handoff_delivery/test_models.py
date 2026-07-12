from dataclasses import FrozenInstanceError
from pathlib import PurePosixPath

import pytest

from handoff_delivery.models import (
    IdList,
    ManifestError,
    require_columns,
    require_foreign_keys,
    require_unique_key,
    require_relative_path,
)


def test_id_list_round_trip_is_ordered_and_immutable():
    ids = IdList.parse("data-1;data-2")

    assert ids.items == ("data-1", "data-2")
    assert isinstance(ids.items, tuple)
    assert ids.serialize() == "data-1;data-2"
    with pytest.raises(FrozenInstanceError):
        ids.items = ("changed",)


@pytest.mark.parametrize(
    "raw",
    (
        "",
        ";data-2",
        "data-1;",
        "data-1;;data-2",
        " data-1",
        "data-1 ",
        "data 1",
        "data-1;\tdata-2",
    ),
)
def test_id_list_rejects_empty_items_and_all_whitespace(raw):
    with pytest.raises(ManifestError):
        IdList.parse(raw)


def test_id_list_rejects_an_item_that_itself_contains_a_semicolon():
    with pytest.raises(ManifestError):
        IdList(("ambiguous;id",))


def test_manifest_paths_must_be_relative_posix_paths():
    raw = "01_stability/topic/data/table.txt"

    assert require_relative_path(raw) == PurePosixPath(raw)


@pytest.mark.parametrize(
    "raw",
    ("/mnt/d/file", "D:/file", "D:file", "../outside", "a/../../outside", "a\\b"),
)
def test_manifest_paths_reject_absolute_drive_traversal_and_backslashes(raw):
    with pytest.raises(ManifestError):
        require_relative_path(raw)


def test_required_columns_are_checked_without_reordering_the_header():
    columns = ("figure_id", "figure_path", "notes")

    assert require_columns(columns, ("figure_path", "figure_id")) == columns
    with pytest.raises(ManifestError, match="missing required columns.*sha256"):
        require_columns(columns, ("figure_id", "sha256"))


def test_unique_key_check_rejects_duplicate_values():
    rows = ({"figure_id": "fig-1"}, {"figure_id": "fig-2"})

    require_unique_key(rows, "figure_id")
    with pytest.raises(ManifestError, match="duplicate.*fig-1"):
        require_unique_key((*rows, {"figure_id": "fig-1"}), "figure_id")


def test_foreign_key_check_rejects_unknown_references():
    require_foreign_keys(("data-1", "data-2"), ("data-1", "data-2", "data-3"))

    with pytest.raises(ManifestError, match="unknown foreign key.*data-missing"):
        require_foreign_keys(("data-1", "data-missing"), ("data-1", "data-2"))


def test_manifest_error_is_a_value_error():
    error = ManifestError("invalid manifest")

    assert isinstance(error, ValueError)
    assert str(error) == "invalid manifest"
