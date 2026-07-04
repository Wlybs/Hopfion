# Hopfion Research Workspace

This workspace is organized by research project, not by file type. The top
level answers "which project or research stage is this?", while each project
keeps its own scripts, simulation inputs, raw outputs, figures, notes, and
results together.

## Project Layout

| Directory | Purpose |
|---|---|
| `00_project_index/` | Workspace index, migration notes, task snapshots, figure maps. |
| `01_legacy_srtp_old/` | Legacy SRTP and old simulation results kept for provenance. |
| `02_early_dmi_fm_feasibility/` | Early DMI/FM Hopfion feasibility and stability exploration. |
| `03_wang2019_stt_reproduction/` | Wang 2019 Hopfion STT reproduction work. |
| `04_frustrated_fm_foundation/` | Main frustrated-FM Hopfion foundation: stability, size, anisotropy, and drift. |
| `05_spinwave_control_dynamics/` | Spin-wave-driven dynamics: frequency, amplitude, direction, point/plane source, and multisource control. |
| `06_eigenmode_frequency_mechanism/` | Ringdown, mode-map, energy-absorption, and eigenfrequency mechanism projects. |
| `07_thiele_theory_model/` | Thiele-equation theory plans and G/D translation results. |
| `08_lif_neuron_device_application/` | Hopfion LIF-neuron and device-behavior studies. |
| `09_paper_thesis_talks/` | Thesis, paper-writing, defense, and presentation materials. |
| `90_external_refs/` | External packages, patent materials, and reference code. |
| `95_shared_scripts/` | Shared scripts reused across projects. |
| `99_scratch_outputs/` | Temporary generated outputs and test artifacts. |

The numbered research directories follow the project story: legacy material,
early feasibility, literature reproduction, the frustrated-FM foundation,
spin-wave control, eigenmode/mechanism analysis, theory modeling, device
application, and finally writing/presentation outputs.

## Root-Level Rules

- Put new work under the owning project directory, not directly in the root.
- Create a new numbered project directory only when the work is a new research
  question or long-lived project.
- Keep raw simulation outputs inside the project that produced them.
- Use `95_shared_scripts/` only for scripts that are genuinely reused by more
  than one project.
- Treat `99_scratch_outputs/` as disposable; important results should move back
  into the project that owns them.

## Tooling Left At Root

The root still keeps agent/tooling files such as `AGENTS.md`, `CLAUDE.md`,
`.beads/`, `.agents/`, `.claude/`, `.git/`, `.gitignore`, and `docs/`.
The `hopfion/` Python virtual environment is also left in place for now because
moving a venv can break its absolute-path metadata.
