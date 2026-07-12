"""Generic, delivery-independent manifest validation primitives."""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any


class ManifestError(ValueError):
    """Raised when manifest data violates a structural contract."""


def _require_unambiguous_id(item: str) -> None:
    if not isinstance(item, str) or not item:
        raise ManifestError("manifest IDs must be non-empty strings")
    if ";" in item:
        raise ManifestError("manifest IDs must not contain semicolons")
    if any(character.isspace() for character in item):
        raise ManifestError("manifest IDs must not contain whitespace")


@dataclass(frozen=True, slots=True)
class IdList:
    """An immutable, ordered list of semicolon-delimited manifest IDs."""

    items: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.items, tuple) or not self.items:
            raise ManifestError("an ID list must contain at least one item in a tuple")
        for item in self.items:
            _require_unambiguous_id(item)

    @classmethod
    def parse(cls, raw: str) -> IdList:
        """Parse a serialized ID list without changing item order."""
        if not isinstance(raw, str):
            raise ManifestError("a serialized ID list must be a string")
        return cls(tuple(raw.split(";")))

    def serialize(self) -> str:
        """Serialize this ID list using its canonical delimiter."""
        return ";".join(self.items)


def require_relative_path(raw: str) -> PurePosixPath:
    """Return *raw* as a relative POSIX path or raise ``ManifestError``."""
    if not isinstance(raw, str) or not raw:
        raise ManifestError("manifest paths must be non-empty strings")
    if "\\" in raw:
        raise ManifestError("manifest paths must use POSIX separators")
    if PureWindowsPath(raw).drive:
        raise ManifestError("manifest paths must not contain a Windows drive")

    path = PurePosixPath(raw)
    if path.is_absolute():
        raise ManifestError("manifest paths must be relative")
    if path == PurePosixPath("."):
        raise ManifestError("manifest paths must identify a relative path")
    if ".." in path.parts:
        raise ManifestError("manifest paths must not traverse to a parent")
    return path


def require_columns(
    columns: Iterable[str],
    required: Iterable[str],
    *,
    context: str = "manifest",
) -> tuple[str, ...]:
    """Check a manifest header and return its original immutable ordering."""
    column_tuple = tuple(columns)
    required_tuple = tuple(required)
    missing = tuple(column for column in required_tuple if column not in column_tuple)
    if missing:
        raise ManifestError(
            f"{context}: missing required columns: {', '.join(missing)}"
        )
    return column_tuple


def require_unique_key(
    rows: Iterable[Mapping[str, Any]],
    key: str,
    *,
    context: str = "manifest",
) -> None:
    """Require *key* to exist and have a unique value in every row."""
    seen: dict[Hashable, int] = {}
    for row_number, row in enumerate(rows, start=2):
        if key not in row:
            raise ManifestError(f"{context}: row {row_number} has no {key!r} key")
        value = row[key]
        if not isinstance(value, Hashable):
            raise ManifestError(
                f"{context}: row {row_number} has an unhashable {key!r} value"
            )
        if value in seen:
            raise ManifestError(
                f"{context}: duplicate {key} value {value!r} "
                f"in rows {seen[value]} and {row_number}"
            )
        seen[value] = row_number


def require_foreign_keys(
    references: Iterable[Hashable],
    valid_keys: Iterable[Hashable],
    *,
    context: str = "manifest",
) -> None:
    """Require every reference to exist in the supplied target-key set."""
    try:
        valid = frozenset(valid_keys)
    except TypeError as error:
        raise ManifestError(f"{context}: foreign-key targets must be hashable") from error

    unknown: list[Hashable] = []
    for reference in references:
        try:
            is_known = reference in valid
        except TypeError as error:
            raise ManifestError(
                f"{context}: foreign-key references must be hashable"
            ) from error
        if not is_known and reference not in unknown:
            unknown.append(reference)
    if unknown:
        formatted = ", ".join(repr(reference) for reference in unknown)
        raise ManifestError(f"{context}: unknown foreign key values: {formatted}")
