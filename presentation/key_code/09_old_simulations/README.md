# 09_old_simulations — 旧版本对标

## 教训

旧 `My_old_simulation/` 系列（共 20 runs，srcX/srcZ point source freq sweep）**含 J2/J4 系数符号错误**。与当前正确版本对比，拓扑荷差异约 2-3%。

**陷阱**：J2 / J4 在 frustrated FM 模型里有正负号约定，不同文献存在差异。
**经验**：复用别人代码时必须验证符号；直接从已验证的 `R8r4_Ku0.mx3` 拷参数，不要从公式重推。

## 脚本清单

| 文件 | 功能 |
|---|---|
| `My_old_simulation_srcZ_410GHz.mx3` | 旧版本代表（**系数错误**，原文件名 `z_f_sw_410000000000.0_505050.mx3`）|
| `deviceB_srcZ_1000GHz.mx3` | Device B（用户次要机器）独立验证版本 |
| `srtp_hopfion_spinwave.mx3` | srtp 早期：自旋波 + 磁场驱动 3D 运动 |

## 原始数据位置

- `old_results/My_old_simulation/A材料尺寸对hopfion的影响/`（中文目录名）
- `deviceB_package/deviceB_package/`（套娃）
- `srtp/{experiments, hopfion_mumax3, magnon-hopfion-main}/` 早期学生项目
