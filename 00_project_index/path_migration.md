# Path Migration Map

This file records the first project-based reorganization pass on 2026-06-22.
The migration moved whole project directories where possible and did not delete
research data.

| Old root path | New path |
|---|---|
| `20251219_dmi_fm/` | `01_early_dmi_fm/20251219_dmi_fm/` |
| `20260105_frustrated_fm/` | `02_frustrated_fm_project/20260105_frustrated_fm/` |
| `20260614task/` | `03_spinwave_control/20260614task/` |
| `hopfion_eigenmode_ringdown_20260608/` | `04_eigenmodes_frequency/hopfion_eigenmode_ringdown_20260608/` |
| `hopfion_energy_absorption_audit_20260608/` | `04_eigenmodes_frequency/hopfion_energy_absorption_audit_20260608/` |
| `hopfion_mode_map_20260608/` | `04_eigenmodes_frequency/hopfion_mode_map_20260608/` |
| `hopfion_eigenfrequency_research_explanation_20260615/` | `04_eigenmodes_frequency/hopfion_eigenfrequency_research_explanation_20260615/` |
| `skyrmion_hopfion_eigenfrequency_link_20260608/` | `04_eigenmodes_frequency/skyrmion_hopfion_eigenfrequency_link_20260608/` |
| `hopfion_thiele_research_plan_20260615/` | `05_thiele_theory/hopfion_thiele_research_plan_20260615/` |
| `results_thiele_GD_translation_20260615/` | `05_thiele_theory/results_thiele_GD_translation_20260615/` |
| `lif_neuron_hopfion/` | `06_lif_neuron_device/lif_neuron_hopfion/` |
| `20260310_wang2019_hopfion_STT/` | `07_wang2019_stt_reproduction/20260310_wang2019_hopfion_STT/` |
| `bishe/` | `08_paper_thesis_talks/bishe/` |
| `presentation/` | `08_paper_thesis_talks/presentation/` |
| `hopfion_spinwave_paper_theory_guidance_20260608/` | `08_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608/` |
| `hopfion_spinwave_paper_theory_guidance_20260608.md` | `08_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608.md` |
| `hopfion_2025.pptx` | `08_paper_thesis_talks/hopfion_2025.pptx` |
| `deviceB_package/` | `09_external_refs/deviceB_package/` |
| `skyrmion_patent/` | `09_external_refs/skyrmion_patent/` |
| `srtp/` | `90_legacy_srtp_old/srtp/` |
| `old_results/` | `90_legacy_srtp_old/old_results/` |
| `scripts/` | `95_shared_scripts/` |
| `outputs/` | `99_scratch_outputs/outputs/` |
| `test/` | `99_scratch_outputs/test/` |
| `20260607task.md` | `00_project_index/20260607task.md` |
| `figure-mapping.md` | `00_project_index/figure-mapping.md` |

## 2026-06-24 Logical Reordering

The second pass renamed the top-level project buckets so the numbering follows
the research story: legacy material, feasibility, literature reproduction,
foundation, control dynamics, mechanisms, theory, device application, writing,
then external references. No files were deleted.

| Previous path | New path |
|---|---|
| `90_legacy_srtp_old/` | `01_legacy_srtp_old/` |
| `01_early_dmi_fm/` | `02_early_dmi_fm_feasibility/` |
| `07_wang2019_stt_reproduction/` | `03_wang2019_stt_reproduction/` |
| `02_frustrated_fm_project/` | `04_frustrated_fm_foundation/` |
| `03_spinwave_control/` | `05_spinwave_control_dynamics/` |
| `04_eigenmodes_frequency/` | `06_eigenmode_frequency_mechanism/` |
| `05_thiele_theory/` | `07_thiele_theory_model/` |
| `06_lif_neuron_device/` | `08_lif_neuron_device_application/` |
| `08_paper_thesis_talks/` | `09_paper_thesis_talks/` |
| `09_external_refs/` | `90_external_refs/` |
