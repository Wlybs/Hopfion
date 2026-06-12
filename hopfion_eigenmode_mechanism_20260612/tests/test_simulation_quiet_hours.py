import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from simulation_quiet_hours import (  # noqa: E402
    estimate_finish,
    running_action,
    start_allowed,
    table_last_time_s,
    target_seconds_from_mx3,
)


SGT = ZoneInfo("Asia/Singapore")


def at(hour, minute):
    return datetime(2026, 6, 12, hour, minute, tzinfo=SGT)


def test_new_runs_are_blocked_from_2300_until_0300():
    assert start_allowed(at(22, 59)) is True
    assert start_allowed(at(23, 0)) is False
    assert start_allowed(datetime(2026, 6, 13, 2, 59, tzinfo=SGT)) is False
    assert start_allowed(datetime(2026, 6, 13, 3, 0, tzinfo=SGT)) is True


def test_running_case_may_finish_inside_2330_grace_window():
    started = at(22, 0)

    assert running_action(at(23, 0), started, at(23, 20)) == "continue"
    assert running_action(at(23, 0), started, at(23, 31)) == "pause"


def test_case_started_at_2300_is_paused_even_if_short():
    assert running_action(at(23, 0), at(23, 0), at(23, 5)) == "pause"


def test_running_case_is_paused_at_2330_if_still_alive():
    assert running_action(at(23, 30), at(22, 0), at(23, 29)) == "pause"


def test_unknown_finish_time_is_paused_at_2300():
    assert running_action(at(23, 0), at(22, 0), None) == "pause"


def test_finish_estimate_scales_elapsed_wall_time_by_simulation_progress():
    started = at(22, 0)
    now = at(23, 0)

    predicted = estimate_finish(
        started_at=started,
        now=now,
        current_simulation_s=0.4e-9,
        target_simulation_s=0.5e-9,
    )

    assert predicted == at(23, 15)


def test_mx3_target_and_table_progress_are_read_without_loading_ovf(tmp_path):
    mx3 = tmp_path / "case.mx3"
    table = tmp_path / "table.txt"
    mx3.write_text("run(0.3e-9)\nrun(20e-12)\n", encoding="utf-8")
    table.write_text(
        "# t (s)\tmz ()\n0\t1\n2.5e-10\t0.9\n",
        encoding="utf-8",
    )

    assert target_seconds_from_mx3(mx3) == 0.32e-9
    assert table_last_time_s(table) == 2.5e-10


def test_all_scheme_b_pipelines_use_the_shared_quiet_hours_runner():
    package = REPO / "hopfion_eigenmode_mechanism_20260612"
    for name in ("run_stage1.sh", "run_recovery_pipeline.sh", "run_stage2.sh"):
        text = (package / name).read_text(encoding="utf-8")
        assert "run_mumax_with_quiet_hours.sh" in text
        assert 'bash "$QUIET_RUNNER"' in text
