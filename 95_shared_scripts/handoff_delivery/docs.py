"""Deterministic, source-aware Markdown rendering for the handoff package."""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import tomllib
from typing import Mapping, Sequence

from .models import ManifestError, require_relative_path
from .source_specs import AnchoredRoot, SourceSpecError


TOPIC_SECTIONS = (
    "研究问题",
    "当前状态",
    "有效/无效结论",
    "数据与代码入口",
    "复现级别",
)
DOCUMENT_TYPES = frozenset(("root", "module", "topic", "handoff", "archive"))
INTEGRITY_STATUSES = frozenset(
    ("source_backed", "inference", "unverified", "unsupported")
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class DocumentationError(RuntimeError):
    """Raised when documentation configuration or rendered links are unsafe."""


def _required_string(row: Mapping[str, object], field: str, *, context: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise DocumentationError(f"{context}.{field} must be a non-empty string")
    return value


def _required_order(row: Mapping[str, object], *, context: str) -> int:
    value = row.get("reading_order")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DocumentationError(f"{context}.reading_order must be non-negative integer")
    return value


def _relative(raw: str, *, context: str) -> str:
    try:
        return require_relative_path(raw).as_posix()
    except ManifestError as error:
        raise DocumentationError(f"invalid {context}: {raw!r}") from error


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    document_id: str
    document_type: str
    target_path: str
    title: str
    reading_order: int


@dataclass(frozen=True, slots=True)
class ClaimSpec:
    claim_id: str
    document_id: str
    section: str
    text: str
    source_path: str
    source_locator: str
    integrity_status: str
    warning: str
    reading_order: int


@dataclass(frozen=True, slots=True)
class DocsConfig:
    version: int
    documents: tuple[DocumentSpec, ...]
    claims: tuple[ClaimSpec, ...]


def _load_source_identity(project_root: Path, relative: str) -> None:
    descriptor = -1
    try:
        with AnchoredRoot(project_root, error_type=DocumentationError) as anchor:
            descriptor = anchor.open_regular(relative)
            os.fstat(descriptor)
    except (DocumentationError, SourceSpecError, OSError) as error:
        raise DocumentationError(
            f"source path does not resolve to a regular project file: {relative}"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def load_docs_config(path: Path | str, *, project_root: Path | str) -> DocsConfig:
    """Load and validate the sole hand-authored documentation source."""
    config_path = Path(path)
    try:
        payload = config_path.read_bytes()
        parsed = tomllib.loads(payload.decode("utf-8", errors="strict"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise DocumentationError(f"cannot load documentation config: {config_path}") from error
    if parsed.get("version") != 1:
        raise DocumentationError("documentation config version must be 1")
    raw_documents = parsed.get("documents")
    raw_claims = parsed.get("claims")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise DocumentationError("documentation config must declare documents")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise DocumentationError("documentation config must declare claims")

    documents: list[DocumentSpec] = []
    for index, raw in enumerate(raw_documents):
        context = f"documents[{index}]"
        if not isinstance(raw, dict):
            raise DocumentationError(f"{context} must be a table")
        document_type = _required_string(raw, "document_type", context=context)
        if document_type not in DOCUMENT_TYPES:
            raise DocumentationError(f"invalid {context}.document_type")
        target_path = _relative(
            _required_string(raw, "target_path", context=context),
            context=f"{context}.target_path",
        )
        if PurePosixPath(target_path).name != "README.md" and target_path != (
            "00_handoff/START_HERE.md"
        ):
            raise DocumentationError(f"unsupported documentation target: {target_path}")
        documents.append(
            DocumentSpec(
                document_id=_required_string(raw, "document_id", context=context),
                document_type=document_type,
                target_path=target_path,
                title=_required_string(raw, "title", context=context),
                reading_order=_required_order(raw, context=context),
            )
        )
    document_ids = tuple(row.document_id for row in documents)
    target_paths = tuple(row.target_path for row in documents)
    if len(document_ids) != len(set(document_ids)):
        raise DocumentationError("document IDs must be unique")
    if len(target_paths) != len(set(target_paths)):
        raise DocumentationError("document target paths must be unique")

    root = Path(project_root)
    claims: list[ClaimSpec] = []
    for index, raw in enumerate(raw_claims):
        context = f"claims[{index}]"
        if not isinstance(raw, dict):
            raise DocumentationError(f"{context} must be a table")
        integrity_status = _required_string(raw, "integrity_status", context=context)
        if integrity_status not in INTEGRITY_STATUSES:
            raise DocumentationError(f"invalid {context}.integrity_status")
        source_path = _required_string(raw, "source_path", context=context)
        source_locator = _required_string(raw, "source_locator", context=context)
        warning = raw.get("warning")
        if not isinstance(warning, str) or warning != warning.strip():
            raise DocumentationError(f"{context}.warning must be a string")
        if integrity_status == "source_backed":
            if source_path == "N/A" or source_locator == "N/A":
                raise DocumentationError(
                    f"{context} source-backed claim requires source path and locator"
                )
            source_path = _relative(source_path, context=f"{context}.source_path")
            _load_source_identity(root, source_path)
        else:
            if not warning:
                raise DocumentationError(
                    f"{context} non-source-backed claim requires visible warning"
                )
            if source_path != "N/A":
                source_path = _relative(source_path, context=f"{context}.source_path")
                _load_source_identity(root, source_path)
        claims.append(
            ClaimSpec(
                claim_id=_required_string(raw, "claim_id", context=context),
                document_id=_required_string(raw, "document_id", context=context),
                section=_required_string(raw, "section", context=context),
                text=_required_string(raw, "text", context=context),
                source_path=source_path,
                source_locator=source_locator,
                integrity_status=integrity_status,
                warning=warning,
                reading_order=_required_order(raw, context=context),
            )
        )
    claim_ids = tuple(row.claim_id for row in claims)
    if len(claim_ids) != len(set(claim_ids)):
        raise DocumentationError("claim IDs must be unique")
    unknown_documents = sorted(set(row.document_id for row in claims) - set(document_ids))
    if unknown_documents:
        raise DocumentationError(
            f"claims reference unknown documents: {unknown_documents!r}"
        )
    for document in documents:
        sections = tuple(
            dict.fromkeys(
                row.section
                for row in sorted(claims, key=lambda item: item.reading_order)
                if row.document_id == document.document_id
            )
        )
        if not sections:
            raise DocumentationError(f"document has no claims: {document.document_id}")
        if document.document_type == "topic" and sections != TOPIC_SECTIONS:
            raise DocumentationError(
                f"topic sections must be exactly {TOPIC_SECTIONS!r}: {document.document_id}"
            )
    return DocsConfig(1, tuple(documents), tuple(claims))


def _validate_links(
    target_path: str,
    payload: str,
    *,
    package_paths: frozenset[str],
) -> None:
    parent = PurePosixPath(target_path).parent
    for raw in MARKDOWN_LINK_RE.findall(payload):
        target = raw.split("#", 1)[0]
        if not target or target.startswith(("https://", "http://", "mailto:")):
            continue
        if target.startswith("/") or "\\" in target or re.match(r"[A-Za-z]:", target):
            raise DocumentationError(f"non-relative Markdown link: {target_path} -> {raw}")
        normalized = posixpath.normpath((parent / target).as_posix())
        if normalized == ".." or normalized.startswith("../"):
            raise DocumentationError(f"Markdown link escapes package: {target_path} -> {raw}")
        if normalized not in package_paths:
            raise DocumentationError(
                f"Markdown link does not resolve in package: {target_path} -> {raw}"
            )


def render_documents(
    config: DocsConfig,
    *,
    package_paths: frozenset[str] = frozenset(),
) -> dict[str, bytes]:
    """Render deterministic Markdown and require every local link to resolve."""
    rendered: dict[str, bytes] = {}
    all_paths = package_paths | frozenset(row.target_path for row in config.documents)
    claims_by_document: dict[str, list[ClaimSpec]] = {}
    for claim in config.claims:
        claims_by_document.setdefault(claim.document_id, []).append(claim)
    for document in sorted(
        config.documents, key=lambda row: (row.reading_order, row.document_id)
    ):
        claims = sorted(
            claims_by_document[document.document_id],
            key=lambda row: (row.reading_order, row.claim_id),
        )
        sections = tuple(dict.fromkeys(row.section for row in claims))
        lines = [f"# {document.title}", ""]
        for section in sections:
            lines.extend((f"## {section}", ""))
            for claim in (row for row in claims if row.section == section):
                lines.extend((claim.text, ""))
                if claim.integrity_status == "source_backed":
                    lines.extend(
                        (f"来源：`{claim.source_path}:{claim.source_locator}`", "")
                    )
                else:
                    lines.extend((f"⚠ {claim.warning}", ""))
        payload = "\n".join(lines).encode("utf-8")
        _validate_links(
            document.target_path,
            payload.decode("utf-8"),
            package_paths=all_paths,
        )
        rendered[document.target_path] = payload
    return rendered


def package_verifier_script() -> bytes:
    """Return the dependency-free package entry for read-only integrity checks."""
    return b'''#!/usr/bin/env python3
"""Read-only verifier entry shipped with the Hopfion handoff package."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys


sys.dont_write_bytecode = True


SHA256 = re.compile(r"[0-9a-f]{64}\\Z")
CHECKSUM = "00_handoff/SHA256SUMS.txt"
REPORT = "00_handoff/verification_report.json"


def regular_files(root: Path):
    rows = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories.sort()
        files.sort()
        current_path = Path(current)
        for name in tuple(directories):
            path = current_path / name
            if stat.S_ISLNK(path.lstat().st_mode):
                raise RuntimeError(f"symbolic link is forbidden: {path.relative_to(root)}")
        for name in files:
            path = current_path / name
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise RuntimeError(f"non-regular path is forbidden: {path.relative_to(root)}")
            rows.append(path.relative_to(root).as_posix())
    return tuple(sorted(rows))


def stable_sha256(path: Path):
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(descriptor)
        identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)
        if not stat.S_ISREG(after.st_mode) or identity(before) != identity(after):
            raise RuntimeError(f"file changed while hashing: {path}")
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def relative_path(raw: str):
    path = PurePosixPath(raw)
    if (
        not raw
        or "\\\\" in raw
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != raw
    ):
        raise RuntimeError(f"invalid checksum path: {raw!r}")
    return raw


def offline(root: Path):
    files = regular_files(root)
    expected_files = tuple(path for path in files if path != CHECKSUM)
    try:
        checksum_text = (root / CHECKSUM).read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as error:
        raise RuntimeError("cannot read SHA256SUMS.txt") from error
    rows = []
    for line in checksum_text.splitlines():
        digest, separator, raw_path = line.partition("  ")
        if not separator or not SHA256.fullmatch(digest):
            raise RuntimeError("invalid checksum row")
        rows.append((relative_path(raw_path), digest))
    paths = tuple(path for path, _ in rows)
    if paths != expected_files or len(paths) != len(set(paths)):
        raise RuntimeError("checksums do not exactly cover every other regular file")
    for relative, expected in rows:
        if stable_sha256(root / relative) != expected:
            raise RuntimeError(f"checksum mismatch: {relative}")
    try:
        report = json.loads((root / REPORT).read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("cannot parse verification report") from error
    gates = report.get("gates") if isinstance(report, dict) else None
    if (
        report.get("schema_version") != 1
        or report.get("passed") is not True
        or not isinstance(gates, list)
        or tuple(row.get("gate") for row in gates) != ("G1", "G2", "G3", "G4", "G5")
        or not all(row.get("passed") is True for row in gates)
    ):
        raise RuntimeError("verification report is not one complete passing G1-G5 run")
    print("PASS: offline integrity-only verification")
    print("NOTICE: G3 was not independently rerun; use full mode with --project-root")
    return 0


def full(root: Path, project_root: Path):
    bundle = root / "00_handoff/_verifier"
    sys.path.insert(0, str(bundle))
    try:
        from handoff_delivery.portable import (
            FieldConsumer,
            InitialStateRecipe,
            LiteralReplacement,
            PortableContract,
            PortableRuntimeEntry,
            PortableTransform,
            RunEntry,
            TemporaryDependencyContract,
        )
        from handoff_delivery.source_specs import ExactSourceSpec, TreeSourceSpec
        from handoff_delivery.verifier import exit_code, verify
        context = json.loads(
            (bundle / "context.json").read_text(encoding="utf-8", errors="strict")
        )
        if context.get("schema_version") != 1:
            raise RuntimeError("unsupported bundled verifier context")
        raw = context["portable_contract"]
        transforms = []
        for item in raw["transforms"]:
            row = dict(item)
            row["replacements"] = tuple(
                LiteralReplacement(
                    old=base64.b64decode(value["old_b64"], validate=True),
                    new=base64.b64decode(value["new_b64"], validate=True),
                    expected_count=value["expected_count"],
                )
                for value in row["replacements"]
            )
            transforms.append(PortableTransform(**row))
        consumers = []
        for item in raw["consumers"]:
            row = dict(item)
            row["roles"] = tuple(row["roles"])
            row["detection_evidence"] = tuple(row["detection_evidence"])
            consumers.append(FieldConsumer(**row))
        recipes = []
        for item in raw["recipes"]:
            row = dict(item)
            row["consumers"] = tuple(row["consumers"])
            recipes.append(InitialStateRecipe(**row))
        wrappers = []
        for item in raw["wrapper_contracts"]:
            row = dict(item)
            row["temporary_paths"] = tuple(row["temporary_paths"])
            wrappers.append(TemporaryDependencyContract(**row))
        runtimes = []
        for item in raw["runtime_entries"]:
            row = dict(item)
            row["runtime_tokens"] = tuple(row["runtime_tokens"])
            runtimes.append(PortableRuntimeEntry(**row))
        contract = PortableContract(
            runs=tuple(RunEntry(**row) for row in raw["runs"]),
            transforms=tuple(transforms),
            consumers=tuple(consumers),
            recipes=tuple(recipes),
            wrapper_contracts=tuple(wrappers),
            config_toml=base64.b64decode(raw["config_toml_b64"], validate=True),
            runtime_entries=tuple(runtimes),
        )
        results = verify(
            root,
            project_root=project_root,
            portable_contract=contract,
            tree_specs=tuple(TreeSourceSpec(**row) for row in context["tree_specs"]),
            exact_specs=tuple(ExactSourceSpec(**row) for row in context["exact_specs"]),
            include_thesis_assets=context["include_thesis_assets"],
            require_final_evidence=True,
        )
        for result in results:
            print(f"{result.gate}: {'PASS' if result.passed else 'FAIL'}")
            for finding in result.findings:
                print(f"  - {finding}")
        return exit_code(results)
    except (ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        raise RuntimeError(f"full bundled verification failed: {error}") from error


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--delivery", required=True, type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.offline:
            return offline(args.delivery)
        if args.project_root is None:
            raise RuntimeError("full G1-G5 mode requires --project-root")
        return full(args.delivery, args.project_root)
    except (OSError, RuntimeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


def package_verifier_assets(
    portable_contract: object,
    *,
    tree_specs: Sequence[object],
    exact_specs: Sequence[object],
    include_thesis_assets: bool,
) -> dict[str, bytes]:
    """Bundle verifier sources plus deterministic, JSON-only build context."""
    transforms = []
    for transform in portable_contract.transforms:
        row = asdict(transform)
        row["replacements"] = [
            {
                "old_b64": base64.b64encode(item.old).decode("ascii"),
                "new_b64": base64.b64encode(item.new).decode("ascii"),
                "expected_count": item.expected_count,
            }
            for item in transform.replacements
        ]
        transforms.append(row)
    context = {
        "schema_version": 1,
        "portable_contract": {
            "runs": [asdict(row) for row in portable_contract.runs],
            "transforms": transforms,
            "consumers": [asdict(row) for row in portable_contract.consumers],
            "recipes": [asdict(row) for row in portable_contract.recipes],
            "wrapper_contracts": [
                asdict(row) for row in portable_contract.wrapper_contracts
            ],
            "config_toml_b64": base64.b64encode(
                portable_contract.config_toml
            ).decode("ascii"),
            "runtime_entries": [
                asdict(row) for row in portable_contract.runtime_entries
            ],
        },
        "tree_specs": [asdict(row) for row in tree_specs],
        "exact_specs": [asdict(row) for row in exact_specs],
        "include_thesis_assets": bool(include_thesis_assets),
    }
    assets = {
        "00_handoff/verify_delivery.py": package_verifier_script(),
        "00_handoff/_verifier/context.json": (
            json.dumps(
                context,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        ),
    }
    source_root = Path(__file__).parent
    for name in (
        "__init__.py",
        "models.py",
        "inventory.py",
        "source_specs.py",
        "lineage.py",
        "derived.py",
        "redraw.py",
        "portable.py",
        "verifier.py",
    ):
        try:
            payload = (source_root / name).read_bytes()
        except OSError as error:
            raise DocumentationError(
                f"cannot bundle package verifier module: {name}"
            ) from error
        assets[f"00_handoff/_verifier/handoff_delivery/{name}"] = payload
    return dict(sorted(assets.items()))
