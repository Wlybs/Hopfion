from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import sys
import time

import numpy as np
import pytest

from handoff_delivery.lineage import FigureRecipe
from handoff_delivery.redraw import (
    ACTIVE_MODULES,
    RedrawError,
    RedrawRecipe,
    execute_redraws,
    validate_redraw_evidence,
    validate_redraw_plan,
)


def write_file(path: Path, payload: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    path.write_bytes(data)
    return path


def figure(
    figure_id: str,
    *,
    usage: str = "formal",
    story_module: str = "01_stability",
) -> FigureRecipe:
    python = str(Path(sys.executable).resolve())
    return FigureRecipe(
        figure_id=figure_id,
        usage_status=usage,
        scientific_status="valid",
        provenance_type="simulation",
        story_module=story_module,
        claim_or_purpose="fixture",
        figure_path=f"figures/{figure_id}.png",
        figure_sha256="a" * 64,
        plot_script_path="scripts/redraw.py",
        plot_command=f"{python} scripts/redraw.py data/input.npy redraw/output.npy",
        input_data_ids="data-a",
        parent_data_ids="data-parent",
        derived_data_ids="N/A",
        run_ids="run-a",
        theory_asset_ids="N/A",
        initial_state_recipe_id="init-a",
        reproducibility="full",
        source_document_ids="doc-a",
        comparison_reference_data_id="data-reference-a",
        comparison_method="numpy.testing.assert_allclose",
        tolerance="rtol=1e-12;atol=1e-12",
        notes="source_locator=fixture",
    )


def redraw(
    redraw_id: str,
    figure_id: str,
    module: str,
    *,
    representative: bool = True,
    command: str | None = None,
) -> RedrawRecipe:
    python = str(Path(sys.executable).resolve())
    return RedrawRecipe(
        redraw_id=redraw_id,
        figure_id=figure_id,
        module=module,
        script_path="scripts/redraw.py",
        command=command or f"{python} scripts/redraw.py data/input.npy redraw/output.npy",
        input_data_ids="data-a",
        input_paths="data/input.npy",
        output_path="redraw/output.npy",
        reference_product_path="reference/output.npy",
        comparison_method="numpy.testing.assert_allclose",
        tolerance="rtol=1e-12;atol=1e-12",
        environment_command=python,
        representative=representative,
        notes="isolated numeric fixture",
    )


def stage_numeric_fixture(root: Path, token: str) -> Path:
    root.mkdir(parents=True)
    write_file(root / ".handoff-staging", token + "\n")
    write_file(
        root / "scripts/redraw.py",
        "from pathlib import Path\n"
        "import numpy as np\n"
        "import sys\n"
        "source = np.load(sys.argv[1], allow_pickle=False)\n"
        "target = Path(sys.argv[2])\n"
        "target.parent.mkdir(parents=True, exist_ok=True)\n"
        "np.save(target, source * 2.0)\n",
    )
    (root / "data").mkdir()
    (root / "reference").mkdir()
    np.save(root / "data/input.npy", np.array([1.0, 2.0, 3.0]))
    np.save(root / "reference/output.npy", np.array([2.0, 4.0, 6.0]))
    return root


def test_active_modules_match_the_approved_story_tree() -> None:
    assert ACTIVE_MODULES == (
        "01_stability",
        "02_spinwave_control",
        "03_mechanism_and_theory",
        "04_lif_device",
        "05_papers_and_talks",
    )


def test_redraw_plan_covers_every_formal_current_figure_and_each_active_module() -> None:
    figures = tuple(
        figure(f"fig-{index}", story_module=module)
        for index, module in enumerate(ACTIVE_MODULES)
    )
    recipes = tuple(
        redraw(f"redraw-{index}", figures[index].figure_id, module)
        for index, module in enumerate(ACTIVE_MODULES)
    )
    data_paths = {
        "data-a": "data/input.npy",
        "data-reference-a": "reference/output.npy",
    }
    validate_redraw_plan(figures, recipes, data_paths=data_paths)

    with pytest.raises(RedrawError, match="figure coverage"):
        validate_redraw_plan(figures, recipes[:-1], data_paths=data_paths)
    with pytest.raises(RedrawError, match="representative redraw"):
        validate_redraw_plan(
            figures,
            tuple(
                replace(item, representative=False)
                if item.module == "03_mechanism_and_theory"
                else item
                for item in recipes
            ),
            data_paths=data_paths,
        )


def test_redraw_plan_binds_recipe_to_authoritative_figure_fields() -> None:
    row = figure("fig-a", story_module="02_spinwave_control")
    valid = redraw("redraw-a", "fig-a", "02_spinwave_control")
    validate_redraw_plan(
        (row,),
        (valid,),
        required_modules=("02_spinwave_control",),
        data_paths={
            "data-a": "data/input.npy",
            "data-reference-a": "reference/output.npy",
        },
    )

    for changed, pattern in (
        (replace(valid, module="01_stability"), "story module"),
        (replace(valid, input_data_ids="data-unrelated"), "input data IDs"),
        (
            replace(
                valid,
                command=(
                    f"{valid.environment_command} scripts/redraw.py data/input.npy "
                    "redraw/other.npy"
                ),
                output_path="redraw/other.npy",
            ),
            "plot command",
        ),
        (replace(valid, tolerance="rtol=1e-9;atol=1e-12"), "tolerance"),
    ):
        with pytest.raises(RedrawError, match=pattern):
            validate_redraw_plan(
                (row,),
                (changed,),
                required_modules=("02_spinwave_control",),
                data_paths={
                    "data-a": "data/input.npy",
                    "data-reference-a": "reference/output.npy",
                },
            )

    with pytest.raises(RedrawError, match="data manifest paths"):
        validate_redraw_plan(
            (row,),
            (valid,),
            required_modules=("02_spinwave_control",),
            data_paths={
                "data-a": "data/different.npy",
                "data-reference-a": "reference/output.npy",
            },
        )

    extra_command = (
        f"{valid.environment_command} scripts/redraw.py data/input.npy "
        "data/undeclared.npy redraw/output.npy"
    )
    figure_with_extra_command = replace(row, plot_command=extra_command)
    extra_input = replace(
        valid,
        command=extra_command,
        input_paths="data/input.npy;data/undeclared.npy",
    )
    with pytest.raises(RedrawError, match="exactly match data manifest paths"):
        validate_redraw_plan(
            (figure_with_extra_command,),
            (extra_input,),
            required_modules=("02_spinwave_control",),
            data_paths={
                "data-a": "data/input.npy",
                "data-reference-a": "reference/output.npy",
            },
        )

    unbound_reference = replace(
        valid,
        reference_product_path="reference/unbound.npy",
    )
    with pytest.raises(RedrawError, match="reference product"):
        validate_redraw_plan(
            (row,),
            (unbound_reference,),
            required_modules=("02_spinwave_control",),
            data_paths={
                "data-a": "data/input.npy",
                "data-reference-a": "reference/output.npy",
            },
        )


def test_validation_only_recipe_must_hash_the_routed_figure_asset() -> None:
    python = str(Path(sys.executable).resolve())
    row = replace(
        figure("fig-external", story_module="05_papers_and_talks"),
        scientific_status="unverified",
        provenance_type="external",
        plot_script_path="N/A",
        plot_command="N/A",
        input_data_ids="N/A",
        parent_data_ids="N/A",
        run_ids="N/A",
        initial_state_recipe_id="N/A",
        comparison_method="source_identity_review",
        tolerance="N/A",
        reproducibility="source_identity_reviewed",
        comparison_reference_data_id="N/A",
    )
    target = "90_archive/historical_figures/fig-external/fig-external.png"
    valid = RedrawRecipe(
        redraw_id="validate-external",
        figure_id=row.figure_id,
        module=row.story_module,
        script_path="shared/validate_hash.py",
        command=f"{python} shared/validate_hash.py {target}",
        input_data_ids="N/A",
        input_paths=target,
        output_path="N/A",
        reference_product_path="N/A",
        comparison_method="input_hash_validation",
        tolerance="exact",
        environment_command=python,
        representative=False,
        notes="validate routed external figure bytes",
    )
    validate_redraw_plan(
        (row,),
        (valid,),
        required_modules=(),
        figure_targets={row.figure_id: target},
    )

    other = "90_archive/historical_figures/other.png"
    unrelated = replace(
        valid,
        command=f"{python} shared/validate_hash.py {other}",
        input_paths=other,
    )
    with pytest.raises(RedrawError, match="figure asset"):
        validate_redraw_plan(
            (row,),
            (unrelated,),
            required_modules=(),
            figure_targets={row.figure_id: target},
        )


def test_validation_only_inputs_are_exact_data_paths_plus_routed_figure() -> None:
    python = str(Path(sys.executable).resolve())
    row = replace(
        figure("fig-superseded", story_module="02_spinwave_control"),
        scientific_status="superseded",
        reproducibility="historical_only",
    )
    target = (
        "90_archive/superseded_figures/fig-superseded/fig-superseded.png"
    )
    valid = RedrawRecipe(
        redraw_id="validate-superseded",
        figure_id=row.figure_id,
        module=row.story_module,
        script_path="shared/validate_hash.py",
        command=(
            f"{python} shared/validate_hash.py data/input.npy {target}"
        ),
        input_data_ids="data-a",
        input_paths=f"data/input.npy;{target}",
        output_path="N/A",
        reference_product_path="N/A",
        comparison_method="input_hash_validation",
        tolerance="exact",
        environment_command=python,
        representative=False,
        notes="validate historical inputs and routed figure bytes",
    )

    validate_redraw_plan(
        (row,),
        (valid,),
        required_modules=(),
        figure_targets={row.figure_id: target},
        data_paths={"data-a": "data/input.npy"},
    )

    extra = "data/undeclared.npy"
    with pytest.raises(RedrawError, match="exactly match"):
        validate_redraw_plan(
            (row,),
            (
                replace(
                    valid,
                    command=f"{valid.command} {extra}",
                    input_paths=f"{valid.input_paths};{extra}",
                ),
            ),
            required_modules=(),
            figure_targets={row.figure_id: target},
            data_paths={"data-a": "data/input.npy"},
        )


def test_numeric_recipe_requires_assert_allclose_and_predeclared_tolerance() -> None:
    valid = redraw("redraw-a", "fig-a", "01_stability")
    with pytest.raises(RedrawError, match="numpy.testing.assert_allclose"):
        replace(valid, comparison_method="image_hash")
    with pytest.raises(RedrawError, match="tolerance"):
        replace(valid, tolerance="N/A")
    with pytest.raises(RedrawError, match="reference product"):
        replace(valid, reference_product_path="data/input.npy")


def test_executor_runs_in_isolated_workspace_and_records_complete_evidence(
    tmp_path: Path,
) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-1", token)
    recipe = redraw("redraw-a", "fig-a", "01_stability")
    evidence_path = staging / "00_handoff/FIGURE_REDRAW_EVIDENCE.csv"

    rows = execute_redraws(
        (recipe,),
        staging_root=staging,
        build_token=token,
        evidence_path=evidence_path,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.result == "PASS"
    assert row.exit_code == 0
    assert row.command == recipe.command
    assert row.environment_command == recipe.environment_command
    assert row.comparison_method == "numpy.testing.assert_allclose"
    assert row.tolerance == "rtol=1e-12;atol=1e-12"
    assert row.input_sha256 == {
        "data/input.npy": hashlib.sha256(
            (staging / "data/input.npy").read_bytes()
        ).hexdigest()
    }
    assert row.output_sha256 == row.reference_sha256
    assert row.started_monotonic_ns <= row.finished_monotonic_ns
    assert row.raw_output_mtime_ns > 0
    assert not (staging / recipe.output_path).exists()
    assert evidence_path.is_file()
    validate_redraw_evidence((recipe,), rows, build_token=token)


def test_executor_rejects_reference_product_mutated_by_redraw_command(
    tmp_path: Path,
) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-reference", token)
    write_file(
        staging / "scripts/redraw.py",
        "from pathlib import Path\n"
        "import numpy as np\n"
        "import sys\n"
        "source = np.load(sys.argv[1], allow_pickle=False)\n"
        "target = Path(sys.argv[2])\n"
        "reference = Path(sys.argv[3])\n"
        "target.parent.mkdir(parents=True, exist_ok=True)\n"
        "np.save(reference, source * 3.0)\n"
        "np.save(target, source * 3.0)\n",
    )
    recipe = redraw("redraw-a", "fig-a", "01_stability")
    recipe = replace(
        recipe,
        command=(
            f"{recipe.environment_command} scripts/redraw.py data/input.npy "
            "redraw/output.npy reference/output.npy"
        ),
    )

    with pytest.raises(RedrawError, match="command failed"):
        execute_redraws((recipe,), staging_root=staging, build_token=token)


def test_redraw_cannot_read_the_hidden_reference_product(tmp_path: Path) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-hidden-ref", token)
    write_file(
        staging / "scripts/redraw.py",
        "from pathlib import Path\n"
        "import numpy as np\n"
        "import sys\n"
        "target = Path(sys.argv[2])\n"
        "target.parent.mkdir(parents=True, exist_ok=True)\n"
        "np.save(target, np.load('reference/output.npy', allow_pickle=False))\n",
    )
    recipe = redraw("redraw-a", "fig-a", "01_stability")

    with pytest.raises(RedrawError, match="command failed"):
        execute_redraws((recipe,), staging_root=staging, build_token=token)


def test_redraw_sandbox_cannot_read_external_absolute_paths(tmp_path: Path) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-external", token)
    secret = tmp_path / "external-secret.npy"
    np.save(secret, np.array([2.0, 4.0, 6.0]))
    write_file(
        staging / "scripts/redraw.py",
        "from pathlib import Path\n"
        "import numpy as np\n"
        "import sys\n"
        f"source = np.load({str(secret)!r}, allow_pickle=False)\n"
        "target = Path(sys.argv[2])\n"
        "target.parent.mkdir(parents=True, exist_ok=True)\n"
        "np.save(target, source)\n",
    )
    recipe = redraw("redraw-a", "fig-a", "01_stability")

    with pytest.raises(RedrawError, match="command failed"):
        execute_redraws((recipe,), staging_root=staging, build_token=token)


def test_redraw_sandbox_does_not_expose_undeclared_etc_files(tmp_path: Path) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-etc", token)
    write_file(
        staging / "scripts/redraw.py",
        "from pathlib import Path\n"
        "import numpy as np\n"
        "import sys\n"
        "payload = Path('/etc/passwd').read_text(encoding='utf-8')\n"
        "assert 'root:' in payload\n"
        "source = np.load(sys.argv[1], allow_pickle=False)\n"
        "target = Path(sys.argv[2])\n"
        "target.parent.mkdir(parents=True, exist_ok=True)\n"
        "np.save(target, source * 2.0)\n",
    )
    recipe = redraw("redraw-a", "fig-a", "01_stability")

    with pytest.raises(RedrawError, match="command failed"):
        execute_redraws((recipe,), staging_root=staging, build_token=token)


def test_redraw_cannot_mutate_or_add_files_to_staging(tmp_path: Path) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-injection", token)
    write_file(
        staging / "scripts/redraw.py",
        "from pathlib import Path\n"
        "import numpy as np\n"
        "import sys\n"
        "for sibling in Path('..').glob('.candidate.staging-*'):\n"
        "    (sibling / 'injected.ovf').write_bytes(b'# OOMMF: injected')\n"
        "source = np.load(sys.argv[1], allow_pickle=False)\n"
        "target = Path(sys.argv[2])\n"
        "target.parent.mkdir(parents=True, exist_ok=True)\n"
        "np.save(target, source * 2.0)\n",
    )
    recipe = redraw("redraw-a", "fig-a", "01_stability")

    execute_redraws((recipe,), staging_root=staging, build_token=token)
    assert not (staging / "injected.ovf").exists()


def test_executor_rejects_staged_input_mutated_by_redraw_command(
    tmp_path: Path,
) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-input", token)
    write_file(
        staging / "scripts/redraw.py",
        "from pathlib import Path\n"
        "import numpy as np\n"
        "import sys\n"
        "source_path = Path(sys.argv[1])\n"
        "source = np.load(source_path, allow_pickle=False)\n"
        "target = Path(sys.argv[2])\n"
        "target.parent.mkdir(parents=True, exist_ok=True)\n"
        "np.save(target, source * 2.0)\n"
        "np.save(source_path, source * 5.0)\n",
    )
    recipe = redraw("redraw-a", "fig-a", "01_stability")

    with pytest.raises(RedrawError, match="staged input changed"):
        execute_redraws((recipe,), staging_root=staging, build_token=token)


def test_executor_rejects_non_staging_tree_and_failed_command(tmp_path: Path) -> None:
    token = "build-token-123"
    ordinary = tmp_path / "delivery"
    ordinary.mkdir()
    recipe = redraw("redraw-a", "fig-a", "01_stability")
    with pytest.raises(RedrawError, match="staging marker"):
        execute_redraws((recipe,), staging_root=ordinary, build_token=token)

    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-2", token)
    with pytest.raises(RedrawError, match="declared input path"):
        replace(
            recipe,
            command=(
                f"{recipe.environment_command} scripts/redraw.py missing.npy "
                "redraw/output.npy"
            ),
            input_paths="data/input.npy",
        )


def test_executor_uses_monotonic_order_when_wall_clock_moves_backward(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-clock", token)
    recipe = redraw("redraw-a", "fig-a", "01_stability")
    real_now = time.time_ns()
    wall_values = iter(
        (
            real_now,
            real_now - 1_200_000_000,
            real_now - 1_100_000_000,
            real_now - 1_000_000_000,
            real_now - 900_000_000,
            real_now - 800_000_000,
        )
    )
    monkeypatch.setattr(time, "time_ns", lambda: next(wall_values))

    row = execute_redraws((recipe,), staging_root=staging, build_token=token)[0]
    assert row.started_monotonic_ns <= row.finished_monotonic_ns


def test_redraw_evidence_path_rejects_dotdot_escape(tmp_path: Path) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-dotdot", token)
    recipe = redraw("redraw-a", "fig-a", "01_stability")
    outside = staging / ".." / "outside-evidence.csv"

    with pytest.raises(RedrawError, match="inside staging"):
        execute_redraws(
            (recipe,),
            staging_root=staging,
            build_token=token,
            evidence_path=outside,
        )
    assert not outside.exists()


def test_redraw_evidence_path_rejects_symlinked_parent_escape(
    tmp_path: Path,
) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-symlink", token)
    recipe = redraw("redraw-a", "fig-a", "01_stability")
    outside = tmp_path / "outside-evidence"
    outside.mkdir()
    (staging / "escape").symlink_to(outside, target_is_directory=True)

    with pytest.raises(RedrawError, match="symlink"):
        execute_redraws(
            (recipe,),
            staging_root=staging,
            build_token=token,
            evidence_path=staging / "escape/evidence.csv",
        )
    assert not (outside / "evidence.csv").exists()


def test_missing_hand_authored_future_or_failed_evidence_is_rejected(
    tmp_path: Path,
) -> None:
    token = "build-token-123"
    staging = stage_numeric_fixture(tmp_path / ".candidate.staging-3", token)
    recipe = redraw("redraw-a", "fig-a", "01_stability")
    row = execute_redraws((recipe,), staging_root=staging, build_token=token)[0]

    with pytest.raises(RedrawError, match="evidence coverage"):
        validate_redraw_evidence((recipe,), (), build_token=token)
    with pytest.raises(RedrawError, match="build token"):
        validate_redraw_evidence(
            (recipe,), (replace(row, build_token="hand-authored"),), build_token=token
        )
    with pytest.raises(RedrawError, match="future"):
        validate_redraw_evidence(
            (recipe,),
            (replace(row, evidence_written_at_ns=time.time_ns() + 10_000_000_000),),
            build_token=token,
        )
    with pytest.raises(RedrawError, match="PASS"):
        validate_redraw_evidence(
            (recipe,), (replace(row, result="FAIL"),), build_token=token
        )
