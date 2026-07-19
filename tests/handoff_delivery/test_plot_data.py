from pathlib import Path

from handoff_delivery.plot_data import generate_all


def test_real_plot_data_generation_closes_spatial_figure_inputs(tmp_path: Path) -> None:
    project = Path(__file__).parents[2]

    outputs = generate_all(project, tmp_path)

    assert len(outputs) == 13
    assert {path.suffix for path in outputs} == {".csv"}
    assert all(path.is_file() and path.stat().st_size > 0 for path in outputs)
    assert all(not path.read_bytes().startswith(b"# OOMMF") for path in outputs)
