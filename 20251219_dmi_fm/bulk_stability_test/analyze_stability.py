"""
分析 4 个 bulk Hopfion 稳定性测试的结果。
追踪：mz 均值、总能量、各能量分量随时间的演化。
判据：若 mz_mean 从初始值 (~0.99) 快速趋向 1.0，则 Hopfion 已崩塌。
"""
import os
import glob
import numpy as np
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CASES = [
    ("run_pbc_demag",    "PBC+Demag (bulk)"),
    ("run_pbc_nodemag",  "PBC, no Demag"),
    ("run_nopbc_demag",  "no PBC+Demag (finite)"),
    ("run_nopbc_nodemag","no PBC, no Demag"),
]

def load_table(out_dir):
    table_path = os.path.join(out_dir, "table.txt")
    if not os.path.exists(table_path):
        return None, None
    data = np.loadtxt(table_path, comments="#")
    if data.ndim == 1:
        data = data[np.newaxis, :]
    # 读取列名
    with open(table_path) as f:
        header = f.readline().strip("# \n").split("\t")
    return header, data

def plot_stability():
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    summary = []

    for ax, (case_name, label) in zip(axes, CASES):
        out_dir = os.path.join(SCRIPT_DIR, f"{case_name}.out")
        header, data = load_table(out_dir)

        if data is None or len(data) < 2:
            ax.set_title(f"{label}\n[No data]")
            ax.text(0.5, 0.5, "Simulation not completed", ha='center', va='center',
                    transform=ax.transAxes, color='red')
            summary.append((label, "N/A", "N/A"))
            continue

        t_ns  = data[:, 0] * 1e9    # 转换为 ns
        mx    = data[:, 1]
        my    = data[:, 2]
        mz    = data[:, 3]

        # mz 均值从 ~0.99 → 1.0 意味着 Hopfion 崩塌
        mz_init  = mz[0]
        mz_final = mz[-1]
        collapsed = (mz_final - mz_init) > 0.005  # 超过 0.5% 视为崩塌
        status = "COLLAPSED" if collapsed else "STABLE"

        ax.plot(t_ns, mz, 'b-o', ms=4, label=r'$\langle m_z \rangle$')
        ax.axhline(1.0, color='r', ls='--', lw=0.8, label='Uniform FM (collapsed)')
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel(r"$\langle m_z \rangle$")
        ax.set_title(f"{label}\nStatus: {status}")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        # 能量面板（若有）
        if header and len(data[0]) > 4:
            e_total = data[:, 4]
            ax2 = ax.twinx()
            ax2.plot(t_ns, e_total * 1e18, 'g--', lw=1, alpha=0.6, label="E_total")
            ax2.set_ylabel("E_total (aJ)", color='g', fontsize=8)
            ax2.tick_params(axis='y', labelcolor='g', labelsize=7)

        summary.append((label, f"{mz_init:.4f}→{mz_final:.4f}", status))

    plt.suptitle("FM+Bulk-DMI Hopfion Stability: 2x2 (PBC × Demag) Comparison\n"
                 "FeGe params: Msat=860kA/m, Aex=13pJ/m, D=1.58mJ/m², R=40nm, r=20nm",
                 fontsize=11)
    plt.tight_layout(rect=[0, 0, 1, 0.93])

    out_path = os.path.join(SCRIPT_DIR, "stability_comparison.png")
    plt.savefig(out_path, dpi=150)
    print(f"Figure saved: {out_path}")

    print("\n" + "=" * 60)
    print(f"{'Case':<30} | {'mz (init→final)':<20} | {'Status'}")
    print("-" * 60)
    for label, mz_str, status in summary:
        print(f"{label:<30} | {mz_str:<20} | {status}")
    print("=" * 60)

if __name__ == "__main__":
    plot_stability()
