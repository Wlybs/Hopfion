from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

import handoff_delivery.derived as derived_module
from handoff_delivery.derived import (
    HOPFION_ENVIRONMENT_COMMAND,
    DerivedDataError,
    DerivedRecipe,
    produce_derived,
    produce_derived_in_environment,
    validate_derived_preflight,
    validate_derived_outputs,
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_source(path: Path) -> tuple[Path, np.ndarray]:
    path.parent.mkdir(parents=True, exist_ok=True)
    array = np.arange(24, dtype=np.float64).reshape(2, 2, 2, 3)
    np.savez(path, field=array)
    return path, array


def make_recipe(project: Path, *, output_sha256: str) -> DerivedRecipe:
    source, _ = write_source(project / "source/field.npz")
    producer = Path(__file__).parents[2] / "95_shared_scripts/handoff_delivery/derived.py"
    fixture_producer = project / "95_shared_scripts/handoff_delivery/derived.py"
    fixture_producer.parent.mkdir(parents=True, exist_ok=True)
    fixture_producer.write_bytes(producer.read_bytes())
    return DerivedRecipe(
        recipe_id="derive-fig-a-slice",
        output_data_id="data-fig-a-slice",
        source_path="source/field.npz",
        source_sha256=sha256_bytes(source.read_bytes()),
        producer_script="95_shared_scripts/handoff_delivery/derived.py",
        producer_sha256=sha256_bytes(fixture_producer.read_bytes()),
        selector_kind="slice",
        selector_json=json.dumps(
            {"array": "field", "axis": 2, "components": [0, 2], "index": 1},
            sort_keys=True,
            separators=(",", ":"),
        ),
        output_path="02_dynamics/data/fig-a-slice.csv",
        output_format="csv",
        output_sha256=output_sha256,
        shape="2x2x2",
        columns="x;y;mx;mz",
        units="nm;nm;1;1",
        coordinate_origin="10;20;30",
        coordinate_spacing="2;4;6",
        coordinate_units="nm;nm;nm",
        parent_figure_ids="fig-a",
        parent_data_ids="source-field-a",
        environment_command=HOPFION_ENVIRONMENT_COMMAND,
        is_complete_field="false",
        notes="bounded z-index slice for fig-a only",
    )


def test_complete_vector_volume_selector_is_rejected() -> None:
    with pytest.raises(DerivedDataError, match="selector_kind"):
        DerivedRecipe(
            recipe_id="bad-volume",
            output_data_id="bad-volume-data",
            source_path="source/field.npz",
            source_sha256="a" * 64,
            producer_script="95_shared_scripts/handoff_delivery/derived.py",
            producer_sha256="b" * 64,
            selector_kind="volume",
            selector_json='{"array":"field"}',
            output_path="data/full.npz",
            output_format="npz",
            output_sha256="c" * 64,
            shape="2x2x2x3",
            columns="mx;my;mz",
            units="1;1;1",
            coordinate_origin="10;20;30",
            coordinate_spacing="2;4;6",
            coordinate_units="nm;nm;nm",
            parent_figure_ids="fig-a",
            parent_data_ids="source-a",
            environment_command=HOPFION_ENVIRONMENT_COMMAND,
            is_complete_field="false",
            notes="not allowed",
        )


def test_slice_selector_cannot_reduce_four_spatial_axes_to_a_full_3d_volume() -> None:
    source = np.zeros((2, 50, 50, 50, 3), dtype=np.float32)
    selector = {"array": "field", "axis": 0, "components": [0, 1, 2], "index": 0}

    with pytest.raises(DerivedDataError, match="three-dimensional spatial volume"):
        derived_module._select(source, "slice", selector)


@pytest.mark.parametrize(
    ("source_shape", "components"),
    (
        ((2, 50, 50, 50), tuple(range(50))),
        ((2, 100_000, 3), (0, 1, 2)),
    ),
)
def test_slice_selector_rejects_output_that_still_matches_a_complete_field(
    source_shape: tuple[int, ...],
    components: tuple[int, ...],
) -> None:
    source = np.zeros(source_shape, dtype=np.uint8)
    selector = {
        "array": "field",
        "axis": 0,
        "components": list(components),
        "index": 0,
    }

    with pytest.raises(DerivedDataError, match="complete-field array shape"):
        derived_module._select(source, "slice", selector)


@pytest.mark.parametrize(
    ("selector_kind", "selector", "expected_axes", "expected_coordinates"),
    (
        (
            "slice",
            {"array": "field", "axis": 2, "components": [0], "index": 1},
            (0, 1),
            np.array([[11.0, 22.0], [11.0, 26.0], [13.0, 22.0], [13.0, 26.0]]),
        ),
        (
            "line",
            {
                "array": "field",
                "axis": 0,
                "components": [0],
                "fixed": {"1": 1, "2": 0},
            },
            (0,),
            np.array([[11.0], [13.0]]),
        ),
        (
            "scalar",
            {"array": "field", "index": [1, 0, 1, 2]},
            (0, 1, 2),
            np.array([[13.0, 22.0, 39.0]]),
        ),
    ),
)
def test_selectors_use_declared_cell_center_coordinates(
    selector_kind: str,
    selector: dict[str, object],
    expected_axes: tuple[int, ...],
    expected_coordinates: np.ndarray,
) -> None:
    source = np.arange(24, dtype=np.float64).reshape(2, 2, 2, 3)
    selected = derived_module._select(source, selector_kind, selector)
    physical = derived_module._physicalise_coordinates(
        selected,
        derived_module._CoordinateSystem(
            origin=(10.0, 20.0, 30.0),
            spacing=(2.0, 4.0, 6.0),
            units=("nm", "nm", "nm"),
        ),
        spatial_dimensions=3,
    )

    assert physical.coordinate_axes == expected_axes
    np.testing.assert_array_equal(physical.coordinates, expected_coordinates)


@pytest.mark.parametrize("selector_kind", ["slice", "line", "scalar"])
def test_only_explicit_bounded_reductions_are_allowed(selector_kind: str) -> None:
    selector_by_kind = {
        "slice": '{"array":"field","axis":2,"components":[0],"index":1}',
        "line": '{"array":"field","axis":0,"components":[0],"fixed":{"1":0,"2":1}}',
        "scalar": '{"array":"field","index":[0,1,1,2]}',
    }
    shape_by_kind = {"slice": "1x1x1", "line": "1x1", "scalar": "1"}
    columns_by_kind = {
        "slice": "x;y;value",
        "line": "x;value",
        "scalar": "x;y;z;value",
    }
    units_by_kind = {
        "slice": "nm;nm;1",
        "line": "nm;1",
        "scalar": "nm;nm;nm;1",
    }
    recipe = DerivedRecipe(
        recipe_id=f"bounded-{selector_kind}",
        output_data_id=f"data-{selector_kind}",
        source_path="source/field.npz",
        source_sha256="a" * 64,
        producer_script="95_shared_scripts/handoff_delivery/derived.py",
        producer_sha256="b" * 64,
        selector_kind=selector_kind,
        selector_json=selector_by_kind[selector_kind],
        output_path=f"data/{selector_kind}.npz",
        output_format="npz",
        output_sha256="c" * 64,
        shape=shape_by_kind[selector_kind],
        columns=columns_by_kind[selector_kind],
        units=units_by_kind[selector_kind],
        coordinate_origin="10;20;30",
        coordinate_spacing="2;4;6",
        coordinate_units="nm;nm;nm",
        parent_figure_ids="fig-a",
        parent_data_ids="source-a",
        environment_command=HOPFION_ENVIRONMENT_COMMAND,
        is_complete_field="false",
        notes="bounded fixture",
    )
    assert recipe.selector_kind == selector_kind


def test_recipe_requires_all_hashes_exact_selector_parent_ids_and_environment(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    valid = make_recipe(project, output_sha256="c" * 64)

    for field_name in ("source_sha256", "producer_sha256", "output_sha256"):
        with pytest.raises(DerivedDataError, match=field_name):
            replace(valid, **{field_name: "missing"})
    with pytest.raises(DerivedDataError, match="canonical JSON"):
        replace(valid, selector_json='{ "array": "field", "axis": 2 }')
    with pytest.raises(DerivedDataError, match="parent_figure_ids"):
        replace(valid, parent_figure_ids="N/A")
    with pytest.raises(DerivedDataError, match="environment_command"):
        replace(valid, environment_command="python3 derived.py")
    with pytest.raises(DerivedDataError, match="shape"):
        replace(valid, shape="bounded")
    with pytest.raises(DerivedDataError, match="canonical derived producer"):
        replace(valid, producer_script="fake.py")


def test_preflight_rejects_a_canonical_producer_that_differs_from_running_code(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    valid = make_recipe(project, output_sha256="c" * 64)
    declared = project / valid.producer_script
    declared.write_text("# not the executing producer\n", encoding="utf-8")
    forged = replace(
        valid,
        producer_sha256=sha256_bytes(declared.read_bytes()),
    )

    with pytest.raises(DerivedDataError, match="running derived implementation"):
        validate_derived_preflight((forged,), project_root=project)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        ("coordinate_origin", "10.0;20;30", "canonical"),
        ("coordinate_origin", "10;nan;30", "finite"),
        ("coordinate_spacing", "2;0;6", "positive"),
        ("coordinate_spacing", "2;4", "same number"),
        ("coordinate_units", "nm; nm;nm", "canonical"),
    ),
)
def test_recipe_requires_canonical_coordinate_metadata(
    tmp_path: Path,
    field_name: str,
    value: str,
    message: str,
) -> None:
    valid = make_recipe(tmp_path / "project", output_sha256="c" * 64)

    with pytest.raises(DerivedDataError, match=message):
        replace(valid, **{field_name: value})


def test_preflight_rejects_source_beneath_symlinked_ancestor(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    recipe = make_recipe(project, output_sha256="c" * 64)
    (project / "source").rename(project / "real-source")
    (project / "source").symlink_to("real-source", target_is_directory=True)

    with pytest.raises(DerivedDataError, match="anchored directory traversal"):
        validate_derived_preflight((recipe,), project_root=project)


def test_preflight_rejects_multiple_recipes_for_the_same_source_path(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    first = make_recipe(project, output_sha256="c" * 64)
    second = replace(
        first,
        recipe_id="derive-fig-b-line",
        output_data_id="data-fig-b-line",
        output_path="02_dynamics/data/fig-b-line.csv",
    )

    with pytest.raises(DerivedDataError, match="source paths must be unique"):
        validate_derived_preflight((first, second), project_root=project)


def test_preflight_rejects_multiple_paths_with_the_same_source_bytes(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    first = make_recipe(project, output_sha256="c" * 64)
    alias = project / "source/field-alias.npz"
    alias.write_bytes((project / first.source_path).read_bytes())
    second = replace(
        first,
        recipe_id="derive-fig-b-line",
        output_data_id="data-fig-b-line",
        source_path="source/field-alias.npz",
        output_path="02_dynamics/data/fig-b-line.csv",
    )

    with pytest.raises(DerivedDataError, match="source SHA256 values must be unique"):
        validate_derived_preflight((first, second), project_root=project)


def test_ovf_reader_preserves_required_extension_for_discretisedfield(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[Path] = []

    class FakeField:
        @classmethod
        def from_file(cls, filename: str):
            path = Path(filename)
            opened.append(path)
            if path.suffix != ".ovf":
                raise ValueError("discretisedfield dispatch requires an OVF suffix")
            return SimpleNamespace(
                array=np.arange(6, dtype=np.float64).reshape(1, 2, 3),
                mesh=SimpleNamespace(
                    cell=np.array([2.0, 4.0]),
                    region=SimpleNamespace(
                        pmin=np.array([10.0, 20.0]),
                        units=("nm", "nm"),
                    ),
                ),
            )

    monkeypatch.setattr(
        derived_module.sys,
        "executable",
        HOPFION_ENVIRONMENT_COMMAND,
    )
    monkeypatch.setitem(
        sys.modules,
        "discretisedfield",
        SimpleNamespace(Field=FakeField),
    )
    requested_temp_roots: list[str | None] = []
    real_temporary_directory = derived_module.tempfile.TemporaryDirectory

    def tracked_temporary_directory(*args: object, **kwargs: object):
        requested_temp_roots.append(kwargs.get("dir"))
        return real_temporary_directory(*args, **kwargs)

    monkeypatch.setattr(
        derived_module.tempfile,
        "TemporaryDirectory",
        tracked_temporary_directory,
    )

    source = tmp_path / "descriptor-without-suffix"
    source.write_bytes(b"# OOMMF OVF 2.0\n# meshunit: nm\n")
    result = derived_module._load_source(
        source,
        "m",
        source_name="results/m000001.ovf",
        declared_coordinates=derived_module._CoordinateSystem(
            origin=(10.0, 20.0),
            spacing=(2.0, 4.0),
            units=("nm", "nm"),
        ),
    )

    assert opened and opened[0].suffix == ".ovf"
    assert requested_temp_roots == ["/tmp"]
    np.testing.assert_array_equal(
        result,
        np.arange(6, dtype=np.float64).reshape(1, 2, 3),
    )


def test_ovf_reader_falls_back_to_verified_meshunit_header(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeField:
        @classmethod
        def from_file(cls, _filename: str):
            return SimpleNamespace(
                array=np.arange(6, dtype=np.float64).reshape(1, 2, 3),
                mesh=SimpleNamespace(
                    cell=np.array([2.0, 4.0]),
                    region=SimpleNamespace(pmin=np.array([10.0, 20.0])),
                ),
            )

    monkeypatch.setattr(derived_module.sys, "executable", HOPFION_ENVIRONMENT_COMMAND)
    monkeypatch.setitem(sys.modules, "discretisedfield", SimpleNamespace(Field=FakeField))
    source = tmp_path / "field-with-meshunit-header"
    source.write_bytes(b"# OOMMF OVF 2.0\n# meshunit: nm\n# Begin: Data Binary 4\n")

    result = derived_module._load_source(
        source,
        "m",
        source_name="results/m000001.ovf",
        declared_coordinates=derived_module._CoordinateSystem(
            origin=(10.0, 20.0),
            spacing=(2.0, 4.0),
            units=("nm", "nm"),
        ),
    )

    np.testing.assert_array_equal(
        result,
        np.arange(6, dtype=np.float64).reshape(1, 2, 3),
    )


@pytest.mark.parametrize(
    ("declared_coordinates", "message"),
    (
        (
            derived_module._CoordinateSystem(
                origin=(11.0, 20.0),
                spacing=(2.0, 4.0),
                units=("nm", "nm"),
            ),
            "coordinate_origin",
        ),
        (
            derived_module._CoordinateSystem(
                origin=(10.0, 20.0),
                spacing=(2.0, 4.000000000000001),
                units=("nm", "nm"),
            ),
            "coordinate_spacing",
        ),
        (
            derived_module._CoordinateSystem(
                origin=(10.0, 20.0),
                spacing=(2.0, 4.0),
                units=("m", "m"),
            ),
            "coordinate_units",
        ),
    ),
)
def test_ovf_reader_requires_exact_declared_mesh_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declared_coordinates: object,
    message: str,
) -> None:
    class FakeField:
        @classmethod
        def from_file(cls, _filename: str):
            return SimpleNamespace(
                array=np.arange(6, dtype=np.float64).reshape(1, 2, 3),
                mesh=SimpleNamespace(
                    cell=np.array([2.0, 4.0]),
                    region=SimpleNamespace(
                        pmin=np.array([10.0, 20.0]),
                        units=("nm", "nm"),
                    ),
                ),
            )

    monkeypatch.setattr(derived_module.sys, "executable", HOPFION_ENVIRONMENT_COMMAND)
    monkeypatch.setitem(sys.modules, "discretisedfield", SimpleNamespace(Field=FakeField))
    source = tmp_path / "field"
    source.write_bytes(b"# OOMMF OVF 2.0\n# meshunit: nm\n")

    with pytest.raises(DerivedDataError, match=message):
        derived_module._load_source(
            source,
            "m",
            source_name="results/m000001.ovf",
            declared_coordinates=declared_coordinates,
        )


def test_ovf_reader_rejects_missing_mesh_units(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeField:
        @classmethod
        def from_file(cls, _filename: str):
            return SimpleNamespace(
                array=np.arange(6, dtype=np.float64).reshape(1, 2, 3),
                mesh=SimpleNamespace(
                    cell=np.array([2.0, 4.0]),
                    region=SimpleNamespace(pmin=np.array([10.0, 20.0])),
                ),
            )

    monkeypatch.setattr(derived_module.sys, "executable", HOPFION_ENVIRONMENT_COMMAND)
    monkeypatch.setitem(sys.modules, "discretisedfield", SimpleNamespace(Field=FakeField))
    source = tmp_path / "field-without-meshunit"
    source.write_bytes(b"# OOMMF OVF 2.0\n# Begin: Data Binary 4\n")

    with pytest.raises(DerivedDataError, match="mesh units"):
        derived_module._load_source(
            source,
            "m",
            source_name="results/m000001.ovf",
            declared_coordinates=derived_module._CoordinateSystem(
                origin=(10.0, 20.0),
                spacing=(2.0, 4.0),
                units=("nm", "nm"),
            ),
        )


def test_compressed_ovf_source_is_rejected_before_reader_dispatch(
    tmp_path: Path,
) -> None:
    with pytest.raises(DerivedDataError, match="compressed OVF sources"):
        derived_module._load_source(
            tmp_path / "descriptor-without-suffix",
            "m",
            source_name="results/m000001.ovf.gz",
        )


def test_csv_producer_is_byte_deterministic_and_records_all_hashes(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    expected = (
        b"x,y,mx,mz\n"
        b"11,22,3,5\n"
        b"11,26,9,11\n"
        b"13,22,15,17\n"
        b"13,26,21,23\n"
    )
    recipe = make_recipe(project, output_sha256=sha256_bytes(expected))

    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = produce_derived(recipe, project_root=project, output_root=first_root)
    second = produce_derived(recipe, project_root=project, output_root=second_root)

    assert (first_root / recipe.output_path).read_bytes() == expected
    assert (second_root / recipe.output_path).read_bytes() == expected
    assert first.output_sha256 == second.output_sha256 == recipe.output_sha256
    assert first.source_sha256 == recipe.source_sha256
    assert first.producer_sha256 == recipe.producer_sha256
    assert first.selector_json == recipe.selector_json
    assert first.coordinate_origin == recipe.coordinate_origin
    assert first.coordinate_spacing == recipe.coordinate_spacing
    assert first.coordinate_units == recipe.coordinate_units
    assert first.parent_figure_ids == ("fig-a",)
    assert first.parent_data_ids == ("source-field-a",)
    assert first.is_complete_field is False


def test_environment_runner_uses_the_declared_pinned_python(tmp_path: Path) -> None:
    project = tmp_path / "project"
    expected = (
        b"x,y,mx,mz\n"
        b"11,22,3,5\n"
        b"11,26,9,11\n"
        b"13,22,15,17\n"
        b"13,26,21,23\n"
    )
    recipe = make_recipe(project, output_sha256=sha256_bytes(expected))
    output_root = tmp_path / "isolated-output"

    evidence = produce_derived_in_environment(
        recipe,
        project_root=project,
        output_root=output_root,
    )

    assert evidence.executed_python == HOPFION_ENVIRONMENT_COMMAND
    assert (output_root / recipe.output_path).read_bytes() == expected


def test_npy_source_uses_declared_cell_center_coordinates(tmp_path: Path) -> None:
    project = tmp_path / "project"
    expected = (
        b"x,y,mx,mz\n"
        b"11,22,3,5\n"
        b"11,26,9,11\n"
        b"13,22,15,17\n"
        b"13,26,21,23\n"
    )
    recipe = make_recipe(project, output_sha256=sha256_bytes(expected))
    source = project / "source/field.npy"
    np.save(source, np.arange(24, dtype=np.float64).reshape(2, 2, 2, 3))
    recipe = replace(
        recipe,
        source_path="source/field.npy",
        source_sha256=sha256_bytes(source.read_bytes()),
    )
    output_root = tmp_path / "output"

    produce_derived(recipe, project_root=project, output_root=output_root)

    assert (output_root / recipe.output_path).read_bytes() == expected


def test_npz_producer_is_byte_deterministic_and_pickle_free(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    recipe = replace(
        make_recipe(project, output_sha256="0" * 64),
        output_path="02_dynamics/data/fig-a-slice.npz",
        output_format="npz",
        output_sha256=(
            "49e06ea5b11092178a4a237bea2540c06bdbb09431fa3b1999bca7411bcba638"
        ),
    )
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first = produce_derived(recipe, project_root=project, output_root=first_root)
    second = produce_derived(recipe, project_root=project, output_root=second_root)
    first_bytes = (first_root / recipe.output_path).read_bytes()
    second_bytes = (second_root / recipe.output_path).read_bytes()

    assert first_bytes == second_bytes
    assert first.output_sha256 == second.output_sha256 == recipe.output_sha256
    with np.load(first_root / recipe.output_path, allow_pickle=False) as archive:
        assert archive.files == ["columns", "coordinates", "units", "values"]
        np.testing.assert_array_equal(
            archive["values"],
            np.array([[3.0, 5.0], [9.0, 11.0], [15.0, 17.0], [21.0, 23.0]]),
        )
        np.testing.assert_array_equal(
            archive["coordinates"],
            np.array([[11.0, 22.0], [11.0, 26.0], [13.0, 22.0], [13.0, 26.0]]),
        )
        np.testing.assert_array_equal(
            archive["units"],
            np.array(["nm", "nm", "1", "1"]),
        )


def test_wrong_declared_output_hash_writes_nothing(tmp_path: Path) -> None:
    project = tmp_path / "project"
    recipe = make_recipe(project, output_sha256="0" * 64)
    output_root = tmp_path / "output"

    with pytest.raises(DerivedDataError, match="output_sha256"):
        produce_derived(recipe, project_root=project, output_root=output_root)
    assert not (output_root / recipe.output_path).exists()


def test_stale_or_hand_authored_output_is_rejected(tmp_path: Path) -> None:
    project = tmp_path / "project"
    expected = (
        b"x,y,mx,mz\n11,22,3,5\n11,26,9,11\n13,22,15,17\n13,26,21,23\n"
    )
    recipe = make_recipe(project, output_sha256=sha256_bytes(expected))
    output = tmp_path / "output" / recipe.output_path
    output.parent.mkdir(parents=True)
    output.write_bytes(expected)

    with pytest.raises(DerivedDataError, match="already exists"):
        produce_derived(recipe, project_root=project, output_root=tmp_path / "output")


def test_derived_output_rejects_symlinked_parent_escape(tmp_path: Path) -> None:
    project = tmp_path / "project"
    expected = (
        b"x,y,mx,mz\n11,22,3,5\n11,26,9,11\n13,22,15,17\n13,26,21,23\n"
    )
    recipe = make_recipe(project, output_sha256=sha256_bytes(expected))
    output_root = tmp_path / "output"
    output_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (output_root / "02_dynamics").symlink_to(
        outside,
        target_is_directory=True,
    )

    with pytest.raises(DerivedDataError, match="symlink"):
        produce_derived(recipe, project_root=project, output_root=output_root)
    assert not (outside / "data/fig-a-slice.csv").exists()


def test_derived_output_rejects_output_root_with_dotdot(tmp_path: Path) -> None:
    project = tmp_path / "project"
    expected = (
        b"x,y,mx,mz\n11,22,3,5\n11,26,9,11\n13,22,15,17\n13,26,21,23\n"
    )
    recipe = make_recipe(project, output_sha256=sha256_bytes(expected))
    escaped_root = tmp_path / "declared-root" / ".." / "escaped-root"

    with pytest.raises(DerivedDataError, match="output_root.*dot-dot"):
        produce_derived(
            recipe,
            project_root=project,
            output_root=escaped_root,
        )
    assert not (tmp_path / "escaped-root" / recipe.output_path).exists()


def test_untracked_derived_file_or_missing_generation_evidence_is_rejected(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    expected = (
        b"x,y,mx,mz\n11,22,3,5\n11,26,9,11\n13,22,15,17\n13,26,21,23\n"
    )
    recipe = make_recipe(project, output_sha256=sha256_bytes(expected))
    output_root = tmp_path / "output"
    evidence = produce_derived(recipe, project_root=project, output_root=output_root)
    extra = output_root / "02_dynamics/data/untracked.csv"
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("hand authored\n", encoding="utf-8")

    with pytest.raises(DerivedDataError, match="untracked derived outputs"):
        validate_derived_outputs((recipe,), (evidence,), output_root=output_root)
    with pytest.raises(DerivedDataError, match="generation evidence"):
        validate_derived_outputs((recipe,), (), output_root=output_root)


def test_output_validation_rejects_output_root_with_dotdot(tmp_path: Path) -> None:
    project = tmp_path / "project"
    expected = (
        b"x,y,mx,mz\n11,22,3,5\n11,26,9,11\n13,22,15,17\n13,26,21,23\n"
    )
    recipe = make_recipe(project, output_sha256=sha256_bytes(expected))
    output_root = tmp_path / "output"
    evidence = produce_derived(recipe, project_root=project, output_root=output_root)
    unsafe_alias = output_root / ".." / output_root.name

    with pytest.raises(DerivedDataError, match="output_root.*dot-dot"):
        validate_derived_outputs(
            (recipe,),
            (evidence,),
            output_root=unsafe_alias,
        )
