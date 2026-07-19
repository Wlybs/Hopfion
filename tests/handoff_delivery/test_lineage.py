from __future__ import annotations

import csv
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from handoff_delivery.lineage import (
    CurrentResultReference,
    FigureRecipe,
    ManifestKeys,
    discover_independent_figures,
    discover_current_mainline_figures,
    discover_thesis_figures,
    load_figure_recipes,
    route_figure,
    validate_figure_closure,
    validate_figure_coverage,
    validate_recipe_membership,
    validate_recipe_ledger,
)
from handoff_delivery.models import ManifestError


def write_file(path: Path, payload: str | bytes = "fixture\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    path.write_bytes(data)
    return path


def recipe(**overrides: str) -> FigureRecipe:
    values = {
        "figure_id": "fig-sim",
        "usage_status": "formal",
        "scientific_status": "valid",
        "provenance_type": "simulation",
        "story_module": "01_stability",
        "claim_or_purpose": "fixture purpose",
        "figure_path": "figures/a.png",
        "figure_sha256": "a" * 64,
        "plot_script_path": "scripts/plot.py",
        "plot_command": "python3 scripts/plot.py",
        "input_data_ids": "data-a",
        "parent_data_ids": "data-parent",
        "derived_data_ids": "N/A",
        "run_ids": "run-a",
        "theory_asset_ids": "N/A",
        "initial_state_recipe_id": "init-a",
        "reproducibility": "full",
        "source_document_ids": "doc-a",
        "comparison_reference_data_id": "data-reference-a",
        "comparison_method": "numpy.testing.assert_allclose",
        "tolerance": "rtol=1e-7;atol=1e-10",
        "notes": "source_locator=fixture:1",
    }
    values.update(overrides)
    return FigureRecipe(**values)


@pytest.fixture
def manifests() -> ManifestKeys:
    return ManifestKeys(
        data_ids=frozenset(
            {"data-a", "data-parent", "parameters-a", "data-reference-a"}
        ),
        run_ids=frozenset({"run-a"}),
        theory_asset_ids=frozenset({"theory-code", "editable-source"}),
        initial_state_recipe_ids=frozenset({"init-a"}),
        document_ids=frozenset({"doc-a", "paper-a"}),
    )


def test_only_canonical_thesis_chapters_define_formal_figures(tmp_path: Path) -> None:
    write_file(
        tmp_path / "ch01-intro.tex",
        "\\includegraphics[width=.8\\textwidth]{figures/a.png}\n"
        "% \\includegraphics{figures/commented.png}\n",
    )
    write_file(tmp_path / "ch01-intro_rewritten.tex", "\\includegraphics{figures/b.png}\n")
    write_file(tmp_path / "ch05-dynamics.tex", "\\includegraphics{figures/c.pdf}\n")

    assert discover_thesis_figures(tmp_path) == (
        "figures/a.png",
        "figures/c.pdf",
    )


def test_unknown_axis_value_is_rejected() -> None:
    with pytest.raises(ManifestError, match="usage_status"):
        recipe(usage_status="final")
    with pytest.raises(ManifestError, match="scientific_status"):
        recipe(scientific_status="probably-valid")
    with pytest.raises(ManifestError, match="provenance_type"):
        recipe(provenance_type="mixed")
    with pytest.raises(ManifestError, match="story_module"):
        recipe(story_module="02_dynamics")


def test_pending_derivation_has_explicit_input_data_ids() -> None:
    with pytest.raises(ManifestError, match="derived_data_ids"):
        recipe(
            reproducibility="minimal_projection_derivation_pending",
            derived_data_ids="N/A",
        )
    with pytest.raises(ManifestError, match="subset"):
        recipe(
            reproducibility="minimal_projection_derivation_pending",
            derived_data_ids="data-unrelated",
        )

    row = recipe(
        reproducibility="minimal_projection_derivation_pending",
        derived_data_ids="data-a",
    )
    assert row.derived_data_ids == "data-a"


def test_figure_recipe_csv_rejects_unquoted_extra_columns(tmp_path: Path) -> None:
    ledger = tmp_path / "figure_recipes.csv"
    row = recipe()
    with ledger.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(asdict(row)))
        writer.writeheader()
        writer.writerow(asdict(row))

    lines = ledger.read_text(encoding="utf-8").splitlines()
    ledger.write_text(
        "\n".join((lines[0], f"{lines[1]},orphaned-column")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="unexpected extra columns"):
        load_figure_recipes(ledger)


def test_figure_recipe_csv_rejects_duplicate_header_names(tmp_path: Path) -> None:
    ledger = tmp_path / "figure_recipes.csv"
    row = recipe()
    with ledger.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(asdict(row)))
        writer.writeheader()
        writer.writerow(asdict(row))

    lines = ledger.read_text(encoding="utf-8").splitlines()
    ledger.write_text(
        "\n".join((f"{lines[0]},figure_id", f"{lines[1]},hidden-id")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="duplicate CSV header"):
        load_figure_recipes(ledger)


def test_theory_figure_closure_does_not_require_mx3(manifests: ManifestKeys) -> None:
    row = recipe(
        figure_id="fig-theory",
        provenance_type="theory",
        input_data_ids="parameters-a",
        parent_data_ids="parameters-a",
        run_ids="N/A",
        theory_asset_ids="theory-code",
        initial_state_recipe_id="N/A",
    )

    validate_figure_closure(row, manifests)


def test_simulation_figure_requires_data_run_and_initial_recipe(
    manifests: ManifestKeys,
) -> None:
    row = recipe(run_ids="N/A")

    with pytest.raises(ManifestError, match="run_ids"):
        validate_figure_closure(row, manifests)

    validate_figure_closure(
        recipe(comparison_reference_data_id="N/A"),
        manifests,
    )


def test_schematic_requires_generator_or_editable_source(
    manifests: ManifestKeys,
) -> None:
    valid = recipe(
        figure_id="fig-schematic",
        scientific_status="not_applicable",
        provenance_type="schematic",
        plot_script_path="N/A",
        plot_command="N/A",
        input_data_ids="N/A",
        parent_data_ids="N/A",
        run_ids="N/A",
        theory_asset_ids="editable-source",
        initial_state_recipe_id="N/A",
        comparison_reference_data_id="N/A",
        comparison_method="visual_source_review",
        tolerance="N/A",
    )
    validate_figure_closure(valid, manifests)

    invalid = replace(valid, theory_asset_ids="N/A")
    with pytest.raises(ManifestError, match="editable source or generator"):
        validate_figure_closure(invalid, manifests)


def test_external_figure_requires_document_and_original_locator(
    manifests: ManifestKeys,
) -> None:
    valid = recipe(
        figure_id="fig-external",
        provenance_type="external",
        plot_script_path="N/A",
        plot_command="N/A",
        input_data_ids="N/A",
        parent_data_ids="N/A",
        run_ids="N/A",
        theory_asset_ids="N/A",
        initial_state_recipe_id="N/A",
        comparison_reference_data_id="N/A",
        source_document_ids="paper-a",
        comparison_method="source_identity_review",
        tolerance="N/A",
        notes="source_locator=paper-a:Fig.2; purpose=background comparison",
    )
    validate_figure_closure(valid, manifests)

    with pytest.raises(ManifestError, match="source_locator"):
        validate_figure_closure(replace(valid, notes="purpose=background comparison"), manifests)


@pytest.mark.parametrize(
    "notes",
    (
        "source_locator=unresolved;purpose=background comparison",
        "source_locator=doc-paper:figure_number_unverified;purpose=background comparison",
        "source_locator=doc-thesis-ch01:Fig.1-1;original_external_source=unresolved",
        "source_locator=doc-thesis-ch01:Fig.1-1;purpose=background comparison",
    ),
)
def test_external_figure_rejects_placeholder_or_downstream_source_locators(
    manifests: ManifestKeys,
    notes: str,
) -> None:
    row = recipe(
        figure_id="fig-external",
        provenance_type="external",
        plot_script_path="N/A",
        plot_command="N/A",
        input_data_ids="N/A",
        parent_data_ids="N/A",
        run_ids="N/A",
        theory_asset_ids="N/A",
        initial_state_recipe_id="N/A",
        comparison_reference_data_id="N/A",
        source_document_ids="paper-a",
        comparison_method="source_identity_review",
        tolerance="N/A",
        notes=notes,
    )

    with pytest.raises(ManifestError, match="original source locator"):
        validate_figure_closure(row, manifests)


def test_foreign_key_lists_are_checked_without_treating_na_as_an_id(
    manifests: ManifestKeys,
) -> None:
    with pytest.raises(ManifestError, match="input_data_ids"):
        validate_figure_closure(recipe(input_data_ids="missing;data-a"), manifests)


def test_formal_superseded_figure_stays_formal_and_routes_to_archive() -> None:
    row = recipe(scientific_status="superseded", reproducibility="historical_only")
    assert row.usage_status == "formal"
    assert route_figure(row) == "90_archive/superseded_figures"


def test_canonical_membership_is_exact_and_status_cannot_hide_formal_figure() -> None:
    formal = {"figures/formal.png", "figures/superseded.png"}
    current = {"results/current.png"}
    rows = (
        recipe(figure_id="formal", figure_path="figures/formal.png"),
        recipe(
            figure_id="superseded",
            figure_path="figures/superseded.png",
            scientific_status="superseded",
        ),
        recipe(
            figure_id="current",
            usage_status="current_only",
            figure_path="results/current.png",
        ),
    )
    validate_recipe_membership(rows, formal_paths=formal, current_paths=current)

    evasion = tuple(
        replace(row, usage_status="archive_only") if row.figure_id == "superseded" else row
        for row in rows
    )
    with pytest.raises(ManifestError, match="formal membership"):
        validate_recipe_membership(evasion, formal_paths=formal, current_paths=current)


def test_packaged_independent_images_have_exactly_one_manifest_row(
    tmp_path: Path,
) -> None:
    write_file(tmp_path / "figures/a.png", b"png")
    write_file(tmp_path / "figures/b.svg", "<svg/>\n")
    write_file(tmp_path / "figures/c.pdf", b"pdf")
    write_file(tmp_path / "report.pdf", b"document container")
    write_file(tmp_path / "slides.pptx", b"document container")

    discovered = discover_independent_figures(
        tmp_path,
        explicitly_marked_pdfs={"figures/c.pdf"},
    )
    assert discovered == ("figures/a.png", "figures/b.svg", "figures/c.pdf")

    rows = (
        recipe(figure_id="a", figure_path="figures/a.png"),
        recipe(figure_id="b", figure_path="figures/b.svg"),
        recipe(figure_id="c", figure_path="figures/c.pdf"),
    )
    validate_figure_coverage(discovered, rows)

    with pytest.raises(ManifestError, match="missing figure rows"):
        validate_figure_coverage(discovered, rows[:-1])

    with pytest.raises(ManifestError, match="duplicate figure_path"):
        validate_figure_coverage(discovered, (*rows, replace(rows[0], figure_id="a2")))


def test_current_figures_require_direct_canonical_document_reference(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path / "docs/progress.md",
        "Current result: `results/current/`\n",
    )
    write_file(tmp_path / "results/current/figures/a.png", b"a")
    write_file(tmp_path / "results/current/figures/b.svg", "<svg/>\n")
    write_file(tmp_path / "results/unreferenced/figures/extra.png", b"extra")
    references = (
        CurrentResultReference(
            result_root="results/current",
            evidence_document="docs/progress.md",
            evidence_literal="results/current/",
        ),
    )

    assert discover_current_mainline_figures(
        tmp_path, references=references
    ) == (
        "results/current/figures/a.png",
        "results/current/figures/b.svg",
    )

    bad = (
        replace(references[0], evidence_literal="results/not-mentioned/"),
    )
    with pytest.raises(ManifestError, match="not directly named"):
        discover_current_mainline_figures(tmp_path, references=bad)


def test_reviewed_real_ledger_exactly_covers_formal_and_current_figures() -> None:
    project_root = Path(__file__).parents[2]

    rows = validate_recipe_ledger(project_root)

    assert len(rows) == 35
    assert sum(row.usage_status == "formal" for row in rows) == 19
    assert sum(row.usage_status == "current_only" for row in rows) == 16
    assert not any(row.usage_status == "archive_only" for row in rows)


def test_reviewed_external_formal_figures_preserve_source_and_integrity_status() -> None:
    project_root = Path(__file__).parents[2]
    rows = {row.figure_id: row for row in validate_recipe_ledger(project_root)}

    comparison = rows["fig-formal-1-1-skyrmion-vs-hopfion"]
    assert comparison.scientific_status == "unverified"
    assert comparison.provenance_type == "external"
    assert route_figure(comparison) == "90_archive/historical_figures"
    assert "10.1007/978-3-030-62844-4_7:Fig.1(b,c)" in comparison.notes
    assert "10.1016/j.physrep.2020.10.001:Fig.2(l)" in comparison.notes
    assert "thesis_caption_mislabels" in comparison.notes

    preimages = rows["fig-formal-2-1-hopfion-preimage-view"]
    assert preimages.scientific_status == "not_applicable"
    assert "10.1063/5.0099942:Fig.1(a-c)" in preimages.notes
    assert "arXiv:2511.23045v1:Fig.1(a)" in preimages.notes

    device = rows["fig-formal-6-2-device-concept"]
    assert device.scientific_status == "unverified"
    assert device.provenance_type == "external"
    assert route_figure(device) == "90_archive/historical_figures"
    assert "embedded_C2PA:urn:c2pa:" in device.notes
    assert "prompt_and_editable_source=unavailable" in device.notes
