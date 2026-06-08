# Hopfion plane-wave energy-rate audit

Date: 2026-06-08

## Method

- Quantity: linear-fit energy rate `dE_total/dt` from Mumax3 `table.txt`.
- Reference fit window: 30%-100% of each simulation time span.
- Robustness check: six windows from full range to 50%-100%.
- Background correction: subtract same-window rate from the no-drive centered Ku10k stability run.
- Interpretation rule: positive corrected slope is treated as signed energy absorption; negative slope is reported as energy-rate response, not automatically called absorption.

## Data coverage

- Total table entries analyzed: 34
- Preferred spectrum entries: 30
- Background table: `/mnt/d/Research/Hopfion/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/table.txt`

## Peak summary

### srcX
- Strongest positive corrected energy absorption: 200 GHz (39.812 nJ/s, R2=0.986, stable_positive).
- Strongest absolute energy-rate response: 200 GHz (39.812 nJ/s signed, |rate|=39.812 nJ/s, R2=0.986, stable_positive).

### srcZ
- No robust positive corrected energy-absorption peak with R2 >= 0.5.
- Strongest absolute energy-rate response: 100 GHz (-4.677 nJ/s signed, |rate|=4.677 nJ/s, R2=0.851, mixed).

## Paper-facing interpretation

- `srcX` can support a low-frequency positive absorption channel if its signed positive peak remains aligned with displacement response.
- `srcZ` negative fitted rates should be described cautiously as driven energy-rate response or relaxation-assisted motion unless a proper drive-minus-no-drive power balance proves net positive absorption.
- Displacement peaks at high frequency should not be renamed eigenfrequencies from this analysis alone.

## Output files

- `results/energy_absorption_audit_records.csv`: one row per frequency table.
- `results/energy_absorption_window_sensitivity.csv`: one row per frequency and fit window.
- `figures/energy_absorption_audit_spectrum.png`: signed corrected spectrum.
- `figures/energy_trace_fit_examples.png`: representative energy traces and fit windows.
