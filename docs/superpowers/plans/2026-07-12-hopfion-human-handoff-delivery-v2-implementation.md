# Hopfion Human Handoff Delivery v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify `hopfion_delivery_20260706_v2/` as a non-destructive, story-structured Hopfion handoff package with content-level OVF exclusion, complete figure provenance, current theory/paper coverage, portable run entries, and concise documentation.

**Architecture:** A small stdlib-first Python package under `95_shared_scripts/handoff_delivery/` inventories authoritative source roots, classifies every candidate as active/archive/excluded, copies approved assets into the v2 story tree, writes normalized manifests and handoff documents, then runs independent G1–G5 verification. Generated delivery output is ignored by Git; source code, tests, design, and plan remain versioned. The old delivery is protected by a before/after SHA256 baseline.

**Tech Stack:** Python 3.12, pytest, Python stdlib (`csv`, `hashlib`, `pathlib`, `zipfile`, `tarfile`, `tomllib`, `subprocess`), NumPy for safe NPY/NPZ shape inspection, project `hopfion` environment only for `discretisedfield`-based figure extraction.

**Approved spec:** `docs/superpowers/specs/2026-07-12-hopfion-human-handoff-delivery-v2-design.md`

**Task tracker:** `Hopfion-ty3`

---

## File map

Create the implementation as focused modules:

- `95_shared_scripts/handoff_delivery/models.py` — normalized CSV schemas, ID-list parsing, relative-path and foreign-key validation.
- `95_shared_scripts/handoff_delivery/inventory.py` — deterministic source enumeration, hashes, old-package baseline, field/archive detection and exclusions.
- `95_shared_scripts/handoff_delivery/source_specs.py` — authoritative source-root and target-routing declarations from spec §5.1.
- `95_shared_scripts/handoff_delivery/lineage.py` — thesis TeX figure discovery and figure/data/document/run lineage validation.
- `95_shared_scripts/handoff_delivery/derived.py` — versioned, recipe-driven extraction of minimal figure slices/arrays from existing source fields; never copies complete fields.
- `95_shared_scripts/handoff_delivery/redraw.py` — manifest-driven input validation,
  representative redraw execution and deterministic comparison/evidence generation.
- `95_shared_scripts/handoff_delivery/portable.py` — exact literal transforms, reverse-byte verification, active-run coverage and absolute-path scanning.
- `95_shared_scripts/handoff_delivery/builder.py` — non-destructive v2 directory construction and source-map/required-assets generation.
- `95_shared_scripts/handoff_delivery/docs.py` — concise README, status, integrity, environment, exclusions and topic documentation.
- `95_shared_scripts/handoff_delivery/verifier.py` — independent G1–G5 checks and immutable JSON report.
- `95_shared_scripts/handoff_delivery/cli.py` / `__main__.py` — `baseline`, `build`, `verify`, and `compare-old` commands.
- `95_shared_scripts/handoff_delivery/figure_recipes.csv` — reviewed formal/current figure provenance ledger used by the builder.
- `95_shared_scripts/handoff_delivery/handoff_docs.toml` — versioned root/module/topic
  prose, reading order, scientific claims, source path/locator, integrity status and
  warnings consumed by the documentation renderer.
- `tests/handoff_delivery/` — isolated TDD fixtures and tests; no real OVF bytes are committed.

Do not modify research-source scripts or the old delivery directory.

Execution branch precondition: all implementation runs on `codex/hopfion-delivery-v2`; assert this before Task 1 and abort if the current branch differs. The current workspace is used instead of a separate worktree because required ignored/untracked research assets exist only here.

### Task 1: Package skeleton and manifest contracts

**Files:**
- Create: `95_shared_scripts/handoff_delivery/__init__.py`
- Create: `95_shared_scripts/handoff_delivery/models.py`
- Create: `tests/handoff_delivery/test_models.py`
- Modify: `.gitignore`

- [ ] **Step 0: Assert execution branch before creating tests or implementation**

Run: `test "$(git branch --show-current)" = "codex/hopfion-delivery-v2"`

Expected: exit 0 before any Task 1 file is created or modified.

- [ ] **Step 1: Write failing schema tests**

```python
from pathlib import PurePosixPath
import pytest

from handoff_delivery.models import IdList, ManifestError, require_relative_path


def test_id_list_round_trip_is_ordered_and_unambiguous():
    ids = IdList.parse("data-1;data-2")
    assert ids.items == ("data-1", "data-2")
    assert ids.serialize() == "data-1;data-2"


def test_id_list_rejects_spaces_empty_items_and_semicolons_in_ids():
    for raw in ("data-1;", "data-1; data-2", "data-1;;data-2"):
        with pytest.raises(ManifestError):
            IdList.parse(raw)


def test_manifest_paths_must_be_relative_posix_paths():
    assert require_relative_path("01_stability/topic/data/table.txt") == PurePosixPath(
        "01_stability/topic/data/table.txt"
    )
    for raw in ("/mnt/d/file", "D:/file", "../outside", "a\\b"):
        with pytest.raises(ManifestError):
            require_relative_path(raw)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_models.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'handoff_delivery'`.

- [ ] **Step 3: Implement minimal manifest primitives**

Implement `ManifestError`, immutable `IdList`, path normalization, required-column checking, unique-key checking, and foreign-key checking. Do not add delivery-specific business rules yet.

- [ ] **Step 4: Add generated output to Git ignore**

Append exactly `/hopfion_delivery_20260706_v2/` to `.gitignore`; do not ignore the old directory or unrelated user files.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_models.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add .gitignore 95_shared_scripts/handoff_delivery tests/handoff_delivery/test_models.py
git commit -m "test delivery manifest contracts"
```

### Task 2: Content-level field and archive exclusion engine

**Files:**
- Create: `95_shared_scripts/handoff_delivery/inventory.py`
- Create: `tests/handoff_delivery/test_inventory.py`

- [ ] **Step 1: Write failing tests for disguised fields and archives**

Use `tmp_path` to create small synthetic fixtures:

```python
def test_oommf_header_is_rejected_even_with_txt_suffix(tmp_path):
    path = tmp_path / "field.txt"
    path.write_text("# OOMMF: rectangular mesh v1.0\n# Begin: Data Text\n0 0 1\n")
    result = inspect_candidate(path)
    assert result.decision == "exclude"
    assert result.reason == "oommf-content"


def test_zip_with_nested_ovf_is_rejected(tmp_path):
    archive = make_zip(tmp_path / "bundle.zip", {"case/m000001.ovf": b"OVF"})
    result = inspect_candidate(archive)
    assert result.reason == "archive-contains-field"


def test_npz_vector_volume_is_rejected_but_figure_slice_is_allowed(tmp_path):
    volume = tmp_path / "volume.npz"
    np.savez_compressed(volume, m=np.zeros((50, 50, 50, 3)))
    assert inspect_candidate(volume).reason == "complete-field-array"

    slice_path = tmp_path / "slice.npz"
    np.savez_compressed(slice_path, m=np.zeros((100, 100, 3)))
    assert inspect_candidate(slice_path, declared_kind="figure_slice").decision == "include"
```

Also test magic-byte container detection, corrupt/encrypted/unsupported fail-closed behavior, deterministic text sampling, symlink inventory, and resource-limit rejection.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_inventory.py -q`

Expected: import or symbol failures for the missing inventory engine.

- [ ] **Step 3: Implement minimal inventory and exclusion logic**

Implement:

- streaming SHA256 and metadata inventory;
- magic-byte detection for ZIP/GZIP/ZSTD/7Z/RAR/TAR;
- recursive ZIP/TAR/TAR.ZST member-name inspection to depth 2 with declared limits;
- fail-closed unsupported/corrupt/encrypted behavior;
- OOMMF header detection in the first 4 KiB;
- deterministic large-text sampling from spec §6.3;
- `allow_pickle=False` NPY/NPZ shape inspection;
- explicit exclusion records rather than silent skips.

The inventory engine never opens real OVF payloads. Task 4's separate derived-data producer may read existing source OVFs only through the project `hopfion` environment and `discretisedfield`, and may emit only manifest-declared figure subsets.

- [ ] **Step 4: Run focused and combined tests**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_models.py tests/handoff_delivery/test_inventory.py -q`

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add 95_shared_scripts/handoff_delivery/inventory.py tests/handoff_delivery/test_inventory.py
git commit -m "add fail-closed delivery inventory"
```

### Task 3: Authoritative source enumeration, routing, and old-package protection

**Files:**
- Create: `95_shared_scripts/handoff_delivery/source_specs.py`
- Create: `95_shared_scripts/handoff_delivery/builder.py`
- Create: `tests/handoff_delivery/test_builder.py`

- [ ] **Step 1: Write failing source-set and safety tests**

```python
def test_every_source_candidate_gets_exactly_one_disposition(fixture_project):
    inventory = enumerate_required_assets(fixture_project.root)
    assert set(inventory.status) == {"copied_active", "copied_archive", "excluded_with_reason"}
    assert inventory.source_paths_are_unique()


def test_failed_and_interrupted_sources_route_only_to_archive(fixture_project):
    rows = enumerate_required_assets(fixture_project.root)
    for row in rows:
        if any(word in row.source_path.lower() for word in ("failed", "interrupted", "incomplete")):
            assert row.expected_target_class == "archive"


def test_old_delivery_baseline_detects_any_mutation(tmp_path):
    old = tmp_path / "old"
    write_fixture_file(old / "README.md", "original")
    baseline = capture_baseline(old)
    write_fixture_file(old / "README.md", "changed")
    assert compare_baseline(old, baseline).changed == ("README.md",)
```

Add separate regression cases proving the baseline also detects an added path, a
removed path, a regular-file/directory/symlink type change, and a symlink target
change even when the link name is unchanged. Parameterize the build safety test over
each difference class and assert a nonzero/failing build result is returned before
the candidate can be accepted or published.

- [ ] **Step 2: Run and verify RED**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_builder.py -q`

Expected: missing `source_specs`/`builder` symbols.

- [ ] **Step 3: Implement deterministic source specs and dry-run builder**

Encode the exact roots from spec §5.1, including thesis figure enumeration, the full seven-file Thiele directory, B/D/E theory documents, latest literature PPTX, drift/Hopf-index assets, LIF, and shared tools. Enumerate all candidates before exclusion. Route active/current content to modules 01–05, legacy/failed/interrupted/superseded content to `90_archive`, and unsupported/field/cache/template content to exclusions.

Builder requirements:

- `dry_run=True` writes nothing and returns complete required/source/exclusion rows;
- actual build refuses an existing non-empty v2 directory unless `--resume` is explicit;
- all copying uses source-to-target mapping and preserves source bytes;
- old delivery baseline records path type, size, SHA256 and symlink target, is
  captured before any v2 write and rechecked after build; any delta invalidates the
  candidate and prevents publication;
- generated README files are never copied from v1 templates.

- [ ] **Step 4: Verify GREEN**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_builder.py -q`

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add 95_shared_scripts/handoff_delivery/source_specs.py 95_shared_scripts/handoff_delivery/builder.py tests/handoff_delivery/test_builder.py
git commit -m "add deterministic handoff builder"
```

### Task 4: Figure, data, document, and run lineage

**Files:**
- Create: `95_shared_scripts/handoff_delivery/lineage.py`
- Create: `95_shared_scripts/handoff_delivery/derived.py`
- Create: `95_shared_scripts/handoff_delivery/redraw.py`
- Create: `95_shared_scripts/handoff_delivery/figure_recipes.csv`
- Modify: `95_shared_scripts/handoff_delivery/builder.py`
- Create: `tests/handoff_delivery/test_lineage.py`
- Create: `tests/handoff_delivery/test_derived.py`
- Create: `tests/handoff_delivery/test_redraw.py`
- Modify: `tests/handoff_delivery/test_builder.py`

- [ ] **Step 1: Write failing TeX discovery and provenance-matrix tests**

```python
def test_only_canonical_thesis_chapters_define_formal_figures(tmp_path):
    write_fixture_file(tmp_path / "ch01-intro.tex", r"\includegraphics{figures/a.png}")
    write_fixture_file(tmp_path / "ch01-intro_rewritten.tex", r"\includegraphics{figures/b.png}")
    assert discover_thesis_figures(tmp_path) == ("figures/a.png",)


def test_theory_figure_closure_does_not_require_mx3(valid_theory_row, manifests):
    validate_figure_closure(valid_theory_row, manifests)


def test_simulation_figure_requires_data_run_and_initial_recipe(invalid_simulation_row, manifests):
    with pytest.raises(ManifestError, match="run_ids"):
        validate_figure_closure(invalid_simulation_row, manifests)
```

Also test schematic/editable-source closure, external citation closure, formal
superseded routing, ID-list foreign keys, document-container separation, and every
packaged independent image having one manifest row. Add a set-equality test proving
that the independently discovered canonical thesis figures plus independently
discovered current mainline figures equal the `usage_status=formal|current_only`
recipe set: neither missing rows nor extra rows are allowed. A formal but
scientifically superseded figure remains `usage_status=formal`, receives
`scientific_status=superseded`, and routes to archive; changing it to
`archive_only` must fail the equality test.

For derived data, first write tests that:

- reject extraction recipes that select a complete vector volume;
- allow only an explicitly bounded slice/line/scalar reduction needed by one figure;
- require source SHA256, producer SHA256, exact selector/parameters, output SHA256,
  parent figure/data IDs, and the `hopfion` environment command;
- reproduce identical CSV/NPZ bytes from the same synthetic source fixture;
- reject hand-authored derived output or any output not generated from a versioned
  recipe.

Add a builder integration test proving preflight/build invokes the declared producer,
copies only its newly generated minimal output, rejects stale/untracked derived
files, and records producer/source/output SHA evidence in emitted manifests.

For redraws, first test that all formal/current input-validation commands run in an
isolated staging environment; every active module 01–05 has at least one actual
representative redraw; comparison method/tolerance is declared before execution;
numeric comparisons use `numpy.testing.assert_allclose`; and the evidence row records
command, environment, input/output SHA256, method, tolerance and result. Missing,
hand-authored, post-dated or failed evidence must be rejected.

- [ ] **Step 2: Run and verify RED**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_lineage.py tests/handoff_delivery/test_derived.py tests/handoff_delivery/test_redraw.py tests/handoff_delivery/test_builder.py -q`

Expected: missing lineage/derived implementation.

- [ ] **Step 3: Implement lineage rules and reviewed recipe ledger**

Implement the three independent axes (`usage_status`, `scientific_status`,
`provenance_type`) and provenance-specific closure matrix. Canonical formal/current
membership is derived independently from TeX and the canonical progress/master-plan
documents, then compared exactly with the recipe ledger. Scientific status may
change routing or add warnings but may never remove a canonical usage obligation.

Populate `figure_recipes.csv` for:

- every research figure referenced by canonical thesis chapters;
- every canonical current mainline figure directly named, or whose result directory
  is directly named, by canonical `progress.md`/paper master plan, regardless of
  scientific status;
- theory/Thiele result assets;
- schematics and external figures with generator/editable-source or citation evidence;
- formal-but-superseded figures routed to archive with a warning.

The ledger stores source paths and IDs, not copied output paths. Do not mark a row valid merely because its filename contains `final`.

Implement `derived.py` as a versioned producer invoked by builder preflight/build.
It may read an existing OVF only with
`/mnt/d/Research/Hopfion/hopfion/bin/python` and `discretisedfield`, and it may write
only the recipe-declared minimal CSV/NPZ subset. The ordinary inventory/verifier
must not parse OVF payloads. Generated derived files are build products, never
manually maintained package content.

Integrate this stage into `builder.py`: preflight and build resolve the same recipe
set; build materializes into an isolated staging directory and will not copy an
output unless the producer just generated it and all declared hashes match.

Implement `redraw.py` as the only executor/evidence writer for figure input checks
and redraws. It operates on a prepared staging tree, never on a promoted package;
the final builder pipeline will invoke it after all staged inputs/scripts/docs exist
and before G1–G5/report/checksum/promotion.

- [ ] **Step 4: Run tests and validate the real ledger statically**

Run:

```bash
PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_lineage.py tests/handoff_delivery/test_derived.py tests/handoff_delivery/test_redraw.py tests/handoff_delivery/test_builder.py -q
PYTHONPATH=95_shared_scripts python3 -c 'from pathlib import Path; from handoff_delivery.lineage import validate_recipe_ledger; validate_recipe_ledger(Path("."))'
```

Expected: tests pass; recipe validation reports zero missing source paths and zero invalid classifications.

- [ ] **Step 5: Commit**

```bash
git add 95_shared_scripts/handoff_delivery/lineage.py 95_shared_scripts/handoff_delivery/derived.py 95_shared_scripts/handoff_delivery/redraw.py 95_shared_scripts/handoff_delivery/figure_recipes.csv 95_shared_scripts/handoff_delivery/builder.py tests/handoff_delivery/test_lineage.py tests/handoff_delivery/test_derived.py tests/handoff_delivery/test_redraw.py tests/handoff_delivery/test_builder.py
git commit -m "map handoff figure provenance"
```

### Task 5: Portable transforms and initial-state recipes

**Files:**
- Create: `95_shared_scripts/handoff_delivery/portable.py`
- Create: `95_shared_scripts/handoff_delivery/initial_state_recipes.csv`
- Modify: `95_shared_scripts/handoff_delivery/builder.py`
- Create: `tests/handoff_delivery/test_portable.py`
- Modify: `tests/handoff_delivery/test_builder.py`

- [ ] **Step 1: Write failing exact-transform tests**

```python
def test_reverse_transform_recovers_original_bytes(tmp_path):
    original = b'm.LoadFile("/mnt/d/old/m000020.ovf")\nrun(0.2e-9)\n'
    portable, row = make_portable(original, old='/mnt/d/old/m000020.ovf', new='${INIT_OVF}')
    assert reverse_portable(portable, row) == original


def test_active_runs_and_portable_transforms_have_equal_nonempty_source_sets(active_runs, transforms):
    validate_portable_coverage(active_runs, transforms)


def test_executable_absolute_path_is_rejected_but_provenance_path_is_allowed():
    assert scan_executable_text('m.LoadFile("/mnt/d/old/a.ovf")')
    assert not scan_provenance_field('/mnt/d/old/a.ovf')
```

Add a builder integration test proving every active original produces exactly one
declared portable entry and transform row, the source original is never modified,
and a missing recipe/portable output makes the build fail before publication.

- [ ] **Step 2: Run and verify RED**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_portable.py tests/handoff_delivery/test_builder.py -q`

Expected: missing portable functions.

- [ ] **Step 3: Implement exact transforms and recipe coverage**

Generate portable scripts only through exact literal replacements recorded in `PORTABLE_TRANSFORMS.csv`; reverse replacements must recover original bytes. `PORTABLE_CONFIG.toml` supplies delivery-relative paths. Scan the exact include/exclude globs from spec G4, including JSON/YAML/TOML and manifest command fields.

Populate initial-state recipes with `documented_only`, `generator_smoke_tested`, or `existing_full_chain_evidence`; never claim a new relaxation was run. Include all active OVF consumers, including the Thiele script's excluded `ovf_archive.tar.zst` dependency.

Integrate portable generation into `builder.py` so transforms are applied only in an
isolated staging tree, originals are byte-copied under `simulation/original/`, and
the active run/original/portable/transform sets are checked for exact nonempty
equality before the staging tree can be promoted.

- [ ] **Step 4: Verify GREEN**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_portable.py tests/handoff_delivery/test_builder.py -q`

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add 95_shared_scripts/handoff_delivery/portable.py 95_shared_scripts/handoff_delivery/initial_state_recipes.csv 95_shared_scripts/handoff_delivery/builder.py tests/handoff_delivery/test_portable.py tests/handoff_delivery/test_builder.py
git commit -m "add portable simulation entries"
```

### Task 6: Independent G1–G5 verifier

**Files:**
- Create: `95_shared_scripts/handoff_delivery/verifier.py`
- Modify: `95_shared_scripts/handoff_delivery/builder.py`
- Create: `tests/handoff_delivery/test_verifier.py`
- Modify: `tests/handoff_delivery/test_builder.py`

- [ ] **Step 1: Write one failing test per hard gate**

Build tiny package fixtures and assert:

- G1 fails on literal/disguised/archive/NPZ full fields.
- G2 fails on an unregistered image, a broken provenance foreign key, a
  formal/current row whose status is changed to evade closure, a source/data SHA
  mismatch, a missing or unvalidated plotting input, missing redraw evidence for
  any required module, or absent numeric/image comparison and declared tolerance.
- G3 fails when independent source enumeration contains an asset missing from `REQUIRED_ASSETS.csv`.
- G4 fails on empty portable coverage, any active OVF consumer without an
  initial-state recipe, an original-script SHA mismatch, a declared portable file
  that does not exist, undeclared transforms, or absolute paths in executable text,
  manifest command fields, or portable configuration.
- G5 fails when the fixed root/module tree is changed, on template README, README
  outside the allowlist, or interrupted/incomplete/failed/superseded content outside
  archive. It also fails when school/thesis templates, `AGENTS*`, generated previews,
  caches, or temporary build artifacts appear in active modules.

Also add a positive fixture where all five gates pass.

Add a builder integration test proving it refuses to promote a staging tree with a
failed gate, and for a valid tree writes `verification_report.json` first and
`SHA256SUMS.txt` last. Assert the checksum covers every other regular file, excludes
itself, and a subsequent verification changes no byte or mtime in the package.

- [ ] **Step 2: Run and verify RED**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_verifier.py tests/handoff_delivery/test_builder.py -q`

Expected: missing verifier.

- [ ] **Step 3: Implement verifier with immutable result model**

Implement `VerificationResult` with gate name, passed flag, counts, findings, and evidence paths. `verify()` performs no writes. `write_report()` is a separate build-time action. Exit code is nonzero if any gate fails.

Checksums are generated only after the final report and exclude `SHA256SUMS.txt` itself. A later `verify` call reads but never rewrites the report.

Integrate verifier/report/checksum finalization into `builder.py`. Promotion from the
isolated staging tree to the requested output is permitted only after G1–G5 pass,
the immutable report is written, and the final checksum inventory is complete.

- [ ] **Step 4: Run all unit tests**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery -q`

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add 95_shared_scripts/handoff_delivery/verifier.py 95_shared_scripts/handoff_delivery/builder.py tests/handoff_delivery/test_verifier.py tests/handoff_delivery/test_builder.py
git commit -m "enforce handoff delivery gates"
```

### Task 7: Documentation renderer and CLI

**Files:**
- Create: `95_shared_scripts/handoff_delivery/docs.py`
- Create: `95_shared_scripts/handoff_delivery/handoff_docs.toml`
- Create: `95_shared_scripts/handoff_delivery/cli.py`
- Create: `95_shared_scripts/handoff_delivery/__main__.py`
- Modify: `95_shared_scripts/handoff_delivery/builder.py`
- Create: `tests/handoff_delivery/test_docs_cli.py`
- Modify: `tests/handoff_delivery/test_builder.py`
- Generate during build: `hopfion_delivery_20260706_v2/00_handoff/verify_delivery.py`

- [ ] **Step 1: Write failing documentation and command tests**

Test that generated topic README files contain exactly the five required sections,
all links are package-relative and resolve, no leaf `.out` README is generated,
status/integrity documents cite their source paths, and CLI dry-run emits no
filesystem mutations. Test the generated package-local
`00_handoff/verify_delivery.py` from outside the repository with a clean
`PYTHONPATH`: it must pass a valid package, return nonzero for a tampered package,
perform no writes, and require only Python plus dependencies explicitly shipped or
documented inside the package. Full G1–G5 mode receives an explicit fixture
`--project-root` so G3 can independently re-enumerate the source candidates. Also
test an explicitly labelled `--offline` integrity-only mode that validates the
packaged build evidence/checksums but does not claim to rerun G3.

Add an end-to-end builder fixture test that starts from a clean synthetic project,
builds the fixed delivery topology, renders every required manifest/document plus
portable entries and the packaged verifier, runs staged input-validation/redraws and
writes their evidence, passes G1–G5, writes report before checksum, then promotes
and runs the packaged verifier against the fixture source root. A second test proves
`--dry-run` creates neither output nor staging residue, while `--resume` is the only
flag that permits an explicitly supported interrupted build.

Test the `handoff_docs.toml` schema independently: every scientific claim must have
a resolvable source path and nonempty source locator, or be explicitly marked
`inference`, `unverified`, or `unsupported` with a visible warning. Generated
README/status prose must be a deterministic rendering of this file; prose present
only in generated output must fail regeneration/equality checks.

- [ ] **Step 2: Run and verify RED**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery/test_docs_cli.py tests/handoff_delivery/test_builder.py -q`

Expected: missing docs/CLI implementation.

- [ ] **Step 3: Implement renderer and CLI**

Commands:

```text
python3 -m handoff_delivery baseline --old <path> --output <csv>
python3 -m handoff_delivery build --project-root <path> --old <path> --output <path> [--dry-run] [--resume]
python3 -m handoff_delivery verify --project-root <path> --delivery <path>
python3 -m handoff_delivery compare-old --old <path> --baseline <csv>
python3 -m handoff_delivery validate-recipes --project-root <path>
```

Render concise root/module/topic docs from structured data, not copied template README files. Record Git HEAD/dirty state, full bd JSON export, environment and requirements, source map, exclusions, integrity warnings and reading order.

Use `handoff_docs.toml` as the sole versioned source for hand-authored root/module/topic
prose and claim metadata. It defines target document/section, claim text, source
path and locator, integrity status, warning, and reading order; generated documents
must never be edited directly.

Render a self-contained package-local verification entry at
`00_handoff/verify_delivery.py`. It must execute the same immutable G1–G5 logic as
the development CLI without importing verification code from the repository
checkout or an ambient `PYTHONPATH`; package any small verifier modules it imports under `00_handoff/` and
document the exact full invocation (`--delivery` plus `--project-root`) in the root
README. Without access to the original project root it may offer `--offline` to
verify embedded evidence and checksums, but must label G3 as not independently
rerun and must not present that mode as full G1–G5 acceptance.

Integrate docs, manifests and the package-local verifier into the same builder
staging pipeline. The complete order is inventory/copy → derived data → portable
entries → docs/manifests/package verifier → input-validation and actual redraw
evidence → G1–G5 → immutable report → checksum → promotion. The CLI is only an
adapter over these tested builder APIs and must not contain a second build path.

- [ ] **Step 4: Run the complete test suite**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery -q`

Expected: all pass with no warnings.

- [ ] **Step 5: Commit**

```bash
git add 95_shared_scripts/handoff_delivery/docs.py 95_shared_scripts/handoff_delivery/handoff_docs.toml 95_shared_scripts/handoff_delivery/cli.py 95_shared_scripts/handoff_delivery/__main__.py 95_shared_scripts/handoff_delivery/builder.py tests/handoff_delivery/test_docs_cli.py tests/handoff_delivery/test_builder.py
git commit -m "add handoff builder CLI and docs"
```

### Task 8: Build the real v2 package and close every gate

**Files:**
- Generate candidate: `/tmp/hopfion_delivery_v2_candidate/**`
- Generate a provisional named acceptance while bd is still open, then clean-rebuild
  after the closed-task publish HEAD is frozen (Git-ignored):
  `hopfion_delivery_20260706_v2/**`
- Modify as needed from verified findings: `95_shared_scripts/handoff_delivery/figure_recipes.csv`
- Modify as needed from verified findings: `95_shared_scripts/handoff_delivery/initial_state_recipes.csv`
- Modify as needed from integrity findings: `95_shared_scripts/handoff_delivery/handoff_docs.toml`

- [ ] **Step 1: Run source dry-run and review counts before writing**

Run:

```bash
PYTHONPATH=95_shared_scripts python3 -m handoff_delivery build \
  --project-root /mnt/d/Research/Hopfion \
  --old /mnt/d/Research/Hopfion/hopfion_delivery_20260706 \
  --output /tmp/hopfion_delivery_v2_candidate \
  --dry-run
```

Expected: reports all required roots, all 7 Thiele files, B/D/E docs, literature PPTX, canonical thesis figures, no unclassified source candidate, and no writes.

- [ ] **Step 2: Build a disposable candidate**

Run the same command without `--dry-run`.

Expected: creates only `/tmp/hopfion_delivery_v2_candidate`; old baseline comparison
still passes. Before promotion, builder invokes every required versioned
derived-data producer and all figure input-validation/representative-redraw commands,
writes generated redraw evidence, passes G1–G5, then writes report and checksum.

- [ ] **Step 3: Resolve manifest closure findings without weakening gates**

For each failed formal/current figure:

- locate the real plotting script and exact inputs;
- add or correct a versioned derived-data recipe/producer and a failing regression test;
- extract minimal figure slices with `hopfion/bin/python` + `discretisedfield` only when an existing source OVF is necessary;
- have the producer write NPZ/CSV plus producer, source, parent and output SHA evidence;
- classify scientific status honestly; a canonical formal/current usage may be
  archived with a warning when superseded but may not be relabelled `archive_only`
  or otherwise removed from the required set;
- never mark an unknown dependency `N/A` unless the provenance matrix permits it.

If implementation bugs appear, first add a failing regression test, then fix. Delete
and rebuild the entire disposable candidate after every source-ledger/producer fix.
Never hand-edit a generated delivery file and never weaken a gate to make a finding
disappear.

- [ ] **Step 4: Audit the build-time figure validation/redraw evidence read-only**

Confirm builder ran every formal/current figure's manifest-declared input-validation
command and, for every active first-level module `01_stability` through
`05_papers_and_talks`, at least one actual representative redraw from staged
packaged scripts and staged raw/minimal-derived data. Numeric products use the
predeclared `numpy.testing.assert_allclose` tolerances; image comparison is allowed
only where no numeric product exists and with a predeclared method/tolerance.
Read-only audit the generated command, environment, input/output SHA256, comparison
method, tolerance and result. Any failure is fixed in the versioned recipe/producer
with a regression test and clean candidate rebuild. Do not run an evidence writer
against or alter the promoted candidate.

- [ ] **Step 5: Run full verification**

Run:

```bash
PYTHONPATH=95_shared_scripts python3 -m handoff_delivery verify \
  --project-root /mnt/d/Research/Hopfion \
  --delivery /tmp/hopfion_delivery_v2_candidate
(cd /tmp && python3 /tmp/hopfion_delivery_v2_candidate/00_handoff/verify_delivery.py \
  --delivery /tmp/hopfion_delivery_v2_candidate \
  --project-root /mnt/d/Research/Hopfion)
```

Expected: G1–G5 all PASS; exit 0; immutable report and checksum order valid.

- [ ] **Step 6: Re-run old-package comparison**

Run:

```bash
PYTHONPATH=95_shared_scripts python3 -m handoff_delivery compare-old \
  --old /mnt/d/Research/Hopfion/hopfion_delivery_20260706 \
  --baseline /tmp/hopfion_delivery_v2_candidate/00_handoff/OLD_PACKAGE_BASELINE.csv
```

Expected: zero added, removed, changed, type-changed, or retargeted paths.

- [ ] **Step 7: Run integrity pass**

Review every independently discovered canonical `formal/current_only` figure and
every scientific claim in `PROJECT_STATUS.md`/module README files. Confirm the
discovered set exactly equals the recipe/manifest set, each source pointer resolves,
and every unsupported or stale claim is explicitly marked. Record unresolved issues
through the versioned documentation inputs and rebuild; do not edit the candidate or
invent replacements.

- [ ] **Step 8: Run all tests again**

Run: `PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery -q`

Expected: all pass.

- [ ] **Step 9: Commit final ledger changes**

```bash
git add 95_shared_scripts/handoff_delivery/figure_recipes.csv 95_shared_scripts/handoff_delivery/initial_state_recipes.csv 95_shared_scripts/handoff_delivery/handoff_docs.toml
git commit -m "finalize Hopfion handoff manifests"
```

Do not add the generated v2 directory to Git.

### Task 9: Final review, freeze HEAD, build final output, and publish branch

**Files:**
- Modify: `.beads/issues.jsonl`
- No generated delivery files are committed.

- [ ] **Step 1: Request full implementation review**

Provide the approved spec, this plan, base SHA `4c3ad1b`, current HEAD, test output,
candidate G1–G5 report and old-baseline comparison to an independent reviewer. Fix
all Critical/Important findings with regression tests and rebuild the disposable
candidate from an empty directory.

- [ ] **Step 2: Commit reviewed code and rebase before freezing the build provenance**

Commit all reviewed implementation/ledger changes. Then run:

```bash
git fetch origin
git rebase origin/master
```

If the rebase changes HEAD, discard and rebuild the candidate. Run the complete test
suite, candidate preflight, both verification entries, old-package comparison, and
`git diff --check` again. Do not build the final named directory yet.

- [ ] **Step 3: Build and verify the named acceptance package while bd is open**

Remove only a prior generated v2 after asserting its path is exactly
`/mnt/d/Research/Hopfion/hopfion_delivery_20260706_v2`; never touch the old delivery.
Run final-path preflight and a clean build from the reviewed/rebased HEAD. Execute the
complete test suite; confirm the build-time figure input-validation/representative-
redraw evidence read-only; then run the development verifier, the package-local full
verifier with `--project-root`, the old-package comparison, integrity pass, and
`git diff --check`. Do not rerun an evidence writer against the promoted package. At this point all
spec §12 completion criteria must be true for the actual named v2; the bd task is
still open/in-progress only so its closure precondition can be evaluated honestly.

- [ ] **Step 4: Close/export bd and freeze the publish commit**

Now close `Hopfion-ty3`, export current bd state with
`bd export -o .beads/issues.jsonl`, commit the task-state change, and confirm the
working tree has no tracked modifications. Do not rebase or amend after this point.
This commit is the frozen publish HEAD.

- [ ] **Step 5: Clean-rebuild the final package from the frozen closed-task HEAD**

Delete only the generated named v2 after the exact-path guard, then rebuild it from
an empty output directory. This second clean build is required so recorded Git HEAD,
`BD_SNAPSHOT.json`, immutable report and checksum all contain the closed task state
and match the commit that will be pushed. Do not hand-edit any file after promotion.

If this build or a later verification fails, reopen `Hopfion-ty3`, export/commit that
state, add a regression test and fix the versioned source/ledger, rebase before a new
acceptance build, and repeat Steps 3–5. Never leave a failed task recorded as closed.

- [ ] **Step 6: Fresh verification before push**

Run:

```bash
PYTHONPATH=95_shared_scripts python3 -m pytest tests/handoff_delivery -q
PYTHONPATH=95_shared_scripts python3 -m handoff_delivery verify --project-root . --delivery hopfion_delivery_20260706_v2
(cd /tmp && python3 /mnt/d/Research/Hopfion/hopfion_delivery_20260706_v2/00_handoff/verify_delivery.py --delivery /mnt/d/Research/Hopfion/hopfion_delivery_20260706_v2 --project-root /mnt/d/Research/Hopfion)
PYTHONPATH=95_shared_scripts python3 -m handoff_delivery compare-old --old hopfion_delivery_20260706 --baseline hopfion_delivery_20260706_v2/00_handoff/OLD_PACKAGE_BASELINE.csv
git diff --check
test -z "$(git status --porcelain --untracked-files=no)"
```

Expected: tests pass, both verifier entries report G1–G5 PASS, old package has zero
added/removed/changed/type-changed/retargeted paths, no whitespace errors, and no
tracked changes were made after the frozen commit.

- [ ] **Step 7: Push the already-verified frozen commit**

Run `git push -u origin codex/hopfion-delivery-v2`; do not rebase or amend after the
final build. Confirm `git rev-parse HEAD` equals
`git rev-parse origin/codex/hopfion-delivery-v2`, and run `git status` to confirm the
branch is up to date. The ignored final package remains local and corresponds to
that exact pushed HEAD.

If push is rejected because the remote branch advanced, never force-push. Fetch and
rebase onto the remote branch, then clean-rebuild the named v2 from the new HEAD and
repeat every final verification before retrying. Reopen the bd task first if a
conflict or changed implementation invalidates any completion criterion.

- [ ] **Step 8: Hand off the generated v2 path**

Report file/directory/size counts, module coverage, formal/current figure counts, exclusion totals, test counts, G1–G5 evidence, old-package baseline result and any explicitly unresolved scientific limitations. Do not replace the old directory without separate user approval.
