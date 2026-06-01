# 00_shared_libs — 共享分析库

所有子目录的 Python 分析脚本依赖本目录的函数。使用前把本目录加到 PYTHONPATH：

```bash
export PYTHONPATH=/path/to/key_code/00_shared_libs:$PYTHONPATH
```

## 脚本清单

| 文件 | 功能 | 来源 |
|---|---|---|
| `hopfion_analysis.py` | Hopfion 质心、R、r 提取，OVF 批量加载，PBC 坐标展开 | `scripts/` |
| `compute_hopf_index.py` | Hopf 不变量数值计算 Q_H | `20260105_frustrated_fm/` |
| `paper_style.py` | 统一论文/PPT 图风格 | `scripts/` |
| `post_sim_analysis.py` | 仿真完成后自动分析（轨迹/速度/能量图） | `scripts/` |
| `audit_sweep_params.py` | sweep 实验参数一致性审计 | `20260105_frustrated_fm/templates/` |

## 依赖

Python 3 + numpy, scipy, matplotlib, discretisedfield。
使用 Hopfion 项目专用 venv：`/mnt/d/Research/Hopfion/hopfion/bin/activate`。
