# Hopfion 人员交接交付包 v2 设计

日期：2026-07-12

任务：`Hopfion-ty3`

源项目：`/mnt/d/Research/Hopfion`

现有交付包：`/mnt/d/Research/Hopfion/hopfion_delivery_20260706`

实施输出：`/mnt/d/Research/Hopfion/hopfion_delivery_20260706_v2`

## 1. 目标

把 Hopfion 项目的主要研究成果、原始仿真代码、最终成图数据、分析脚本、理论说明和当前状态整理成一个可供下一位研究同事独立阅读和继续工作的交付包。

交付包必须同时满足：

1. 不交付任何具体 OVF/OMF 场文件，包括改后缀或藏在压缩包中的场文件。
2. 所有纳入的正式成图和当前主线结果图均按来源类型形成闭环：仿真图追溯到绘图输入、仿真脚本和初态配方；理论图追溯到理论代码与参数；示意图/外部图追溯到可编辑源或原始出处。
3. 不遗漏稳定性、自旋波控制、本征模/机理、Thiele 理论、LIF 器件、论文/汇报六条主线。
4. 原始仿真代码保持字节不变；主线另提供不依赖原电脑绝对路径的可移植运行入口。
5. 目录以研究故事线组织，README 只保留在真正需要导航和解释的位置；legacy、failed、interrupted、superseded 与 active 分离。

## 2. 安全策略

本次不在原目录上直接移动或删除文件。

- `hopfion_delivery_20260706/` 保持原样，作为回退基线。
- 所有新整理先写入同级目录 `hopfion_delivery_20260706_v2/`。
- 构建完成后比较文件清单、SHA256 和验收报告。
- 是否用 v2 替换旧目录，属于单独的破坏性操作，必须再次取得用户明确确认。
- 不修改研究源目录中的现有仿真数据、脚本或论文材料。

## 3. 权威信源

交付说明不得从旧 README 猜测当前状态。各类事实使用以下信源：

| 信息 | 权威来源 |
|---|---|
| 任务状态、优先级、依赖 | 项目根 `.beads/`；构建时导出只读快照 |
| 当前物理结论与诚信红线 | `/mnt/d/Obsidian/20-Research/Hopfion-Physics/progress.md` |
| 文件路径和代码版本 | 当前文件系统、Git HEAD 和 SHA256 |
| 项目目录迁移 | `00_project_index/path_migration.md` |
| 论文主线 | `00_project_index/hopfion_spinwave_paper_master_plan_20260703.md` |
| 最终论文/汇报实际用图 | `09_paper_thesis_talks/bishe/thesis_v2/chapters/*.tex` 与正式 PPTX/构建源 |

旧 `pending_issues_20260705.md`、旧 `figure-mapping.md`、历史 `AGENTS.md` 只能作为历史证据，不能作为 v2 当前指令。

## 4. 目标结构

```text
hopfion_delivery_20260706_v2/
├── README.md
├── 00_handoff/
│   ├── START_HERE.md
│   ├── PROJECT_STATUS.md
│   ├── SCIENTIFIC_INTEGRITY.md
│   ├── FIGURE_MANIFEST.csv
│   ├── DATA_MANIFEST.csv
│   ├── DOCUMENT_MANIFEST.csv
│   ├── RUN_MANIFEST.csv
│   ├── INITIAL_STATE_RECIPES.csv
│   ├── PORTABLE_TRANSFORMS.csv
│   ├── PORTABLE_CONFIG.toml
│   ├── TOPIC_INDEX.csv
│   ├── REQUIRED_ASSETS.csv
│   ├── SOURCE_MAP.csv
│   ├── BD_SNAPSHOT.json
│   ├── OLD_PACKAGE_BASELINE.csv
│   ├── EXCLUSIONS.md
│   ├── ENVIRONMENT.md
│   ├── requirements.txt
│   ├── SOURCE_SNAPSHOT.md
│   ├── SHA256SUMS.txt
│   ├── verification_report.json
│   └── verify_delivery.py
├── 01_stability/
│   ├── frustrated_fm/
│   ├── dmi_feasibility/
│   └── wang2019_reproduction/
├── 02_spinwave_control/
│   ├── drive_selection/
│   ├── frequency_sweeps/
│   ├── amplitude_sweeps/
│   ├── point_vs_plane/
│   ├── multisource/
│   └── reverse_propagation/
├── 03_mechanism_and_theory/
│   ├── energy_audit/
│   ├── ringdown/
│   ├── mode_maps/
│   ├── eigenmode_controls/
│   ├── thiele/
│   └── literature_claims/
├── 04_lif_device/
├── 05_papers_and_talks/
│   ├── thesis_final/
│   ├── paper_guidance/
│   └── presentations/
├── 90_archive/
│   ├── legacy_code/
│   ├── failed_explorations/
│   ├── interrupted_runs/
│   ├── superseded_figures/
│   └── project_history/
└── shared/
    ├── analysis/
    ├── plotting/
    ├── initial_state/
    └── references/
```

每个真实研究单元只在有内容时创建以下目录：

```text
<topic>/
├── README.md
├── simulation/
│   ├── original/
│   └── portable/
├── data/
├── analysis/
├── figures/
└── notes/
```

禁止为只含一个 `table.txt` 的运行目录生成独立 README。运行参数和状态统一写入 `RUN_MANIFEST.csv`。

## 5. 纳入范围

### 5.1 Active 主线

必须纳入：

- Frustrated-FM 稳定性、尺寸、各向异性、漂移修正和 Hopf 指数计算。
- 面源/点源自旋波的方向、频率、幅度、多源和反向传播控制。
- 能量趋势审计、ringdown、mode map、2026-06-12 至 2026-06-14 本征模控制链。
- `07_thiele_theory_model/` 的研究计划、代码、JSON 结果和日志。
- LIF 梯度 Ku 与周期演示的真实 PASS/FAILED 状态。
- 2026-07-05 更新的 B/D/E 理论文档与 2026-07-06 文献汇报。
- 正式毕设/论文/汇报中实际使用的研究图、对应绘图脚本和数据。
- 真正跨模块复用的初态、分析和绘图工具。

`REQUIRED_ASSETS.csv` 在复制前生成，至少逐文件列出以下确定集合及其目标路径：

- `00_project_index/hopfion_spinwave_paper_master_plan_20260703.md`。
- `07_thiele_theory_model/` 当前全部 7 个文件。
- `09_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608/B_point_vs_plane.md`。
- 同目录 `D_skyrmion_spinwave_theory_library_20260705.md` 与 `E_skyrmion_spinwave_source_geometry_claim_ledger_20260705.md`。
- `09_paper_thesis_talks/skyrmion_spinwave_dynamics_literature_report_20260705.pptx`。
- `09_paper_thesis_talks/bishe/thesis_v2/chapters/` 中正式章节引用的本地图文件，以及这些图在 `thesis_v2/figures/` 中的绘图脚本和 CSV。
- `04_frustrated_fm_foundation/20260105_frustrated_fm/compute_hopf_index.py`、漂移统一重跑 `.mx3`/运行脚本/配置/汇总数据。

正式论文图集合按确定算法得到：只解析 `thesis_v2/chapters/ch01-intro.tex` 至 `ch07-conclusion.tex`（排除 `_rewritten` 和备份），收集指向 `figures/` 的独立本地图引用；模板 logo、class 自带资源不计入研究图。

论文图依赖集合不靠文件名猜测：除上述被引用图外，`thesis_v2/figures/` 顶层的全部 `.py` 和 `.csv`（排除 `_unused/`、字体备份和缓存）都进入 `REQUIRED_ASSETS.csv`。每张被引用图再通过 `FIGURE_MANIFEST.csv` 的 ID 外键声明实际脚本和数据；G2 执行该行的 input-validation/重绘命令验证语义闭环。

其余 active 模块按以下源根生成 required-assets，不允许构建器自行缩小范围。候选全集是在应用任何排除规则之前递归枚举这些源根中的全部普通文件和符号链接；每个候选都必须恰好进入 `REQUIRED_ASSETS.csv` 一次，再标记为复制到 active、复制到 archive 或带理由排除。验证器独立重枚举源根并要求集合完全相等：

| 模块 | 确定源根 |
|---|---|
| 稳定性 | `04_frustrated_fm_foundation/20260105_frustrated_fm/{centered_stability_test,anisotropy_study,size_sweep,drift_experiments}` |
| 自旋波控制 | `04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/` |
| 机理控制 | `06_eigenmode_frequency_mechanism/` 与根目录 `hopfion_eigenmode_mechanism_20260612/` |
| LIF | `08_lif_neuron_device_application/lif_neuron_hopfion/` |
| 共享工具 | `95_shared_scripts/` 中除 OVF/缓存/测试产物外的全部源文件 |

源路径带 `failed/interrupted/incomplete/superseded` 或被 canonical 状态明确判为失败/推翻的文件仍进入 required-assets，但目标必须在 `90_archive/`，不能因此静默遗漏。

### 5.2 Archive

以下内容可保留，但必须退出 active：

- SRTP 与早期 legacy 代码。
- DMI/FM 失败探索、错误 ansatz、未完成或中断运行。
- `attempt1_incomplete`、`interrupted_runs`。
- 已被推翻、标记 `SUPERSEDED` 或仅用于调试的图。
- 旧路径迁移记录、旧任务快照和旧代理说明。

Archive 中每个直接分类目录允许且必须只保留一个 README，即 `90_archive/*/README.md`；README 说明年代、用途、失败原因或替代结果，不在更深叶目录重复生成。

### 5.3 排除

默认排除：

- `.ovf`、`.omf`、`.ovf.gz` 及任何等价场文件。
- 内含上述文件的 ZIP/TAR/TAR.ZST/7Z/RAR。
- OOMMF 文本头伪装成 `.txt` 的场文件。
- 可判定为完整三分量场网格、但没有交付必要性的百万行文本。
- Python venv、`node_modules`、缓存、预览目录、临时文件、锁和 PID。
- 下载网页、重复论文库、查重/AIGC 报告、学校模板副本。
- 过程 OVF 截图批次、重复旧版本图片和无解释的临时图。

所有排除类别、数量、体积和原因写入 `EXCLUSIONS.md`；不靠静默遗漏完成精简。

压缩包采用 fail-closed 策略：

- 先按 magic bytes 识别容器，不信任扩展名。
- ZIP/TAR 由 Python 标准库列目录；TAR.ZST 由系统 `tar` 列目录。
- 最多递归检查 2 层、100000 个条目和 5 GiB 声明解压体积；超过上限直接拒收。
- 加密、损坏、嵌套后无法识别或当前环境不支持的容器直接拒收，不允许“无法检查所以放行”。
- 当前环境没有可靠 7Z/RAR 读取器，因此 7Z/RAR 一律排除并记入 `EXCLUSIONS.md`。

## 6. 最终图与数据血缘

### 6.1 图的分类

图的“使用位置”“科学状态”和“来源类型”是三个独立维度，禁止混成单一 `status`。

- `usage_status`: `formal`、`current_only`、`archive_only`。
- `scientific_status`: `valid`、`superseded`、`failed`、`unverified`、`not_applicable`。
- `provenance_type`: `simulation`、`theory`、`schematic`、`external`。

分类优先规则：正式文档采用但结论已推翻的图应记录为 `usage_status=formal`、`scientific_status=superseded`，并只能在 `90_archive/superseded_figures/` 中保留，不能进入 active 结论入口。

### 6.2 Manifest 字段

至少包含：

```text
figure_id,usage_status,scientific_status,provenance_type,
claim_or_purpose,figure_path,figure_sha256,
plot_script_path,plot_command,input_data_ids,parent_data_ids,run_ids,
theory_asset_ids,initial_state_recipe_id,reproducibility,source_document_ids,
comparison_method,tolerance,notes
```

规则：

- 包内每个独立 PNG/SVG，以及位于 `figures/` 或在 manifest 明确标记为 figure 的 PDF，都必须登记。
- 论文、报告和幻灯片容器本身进入 `DOCUMENT_MANIFEST.csv`；只有从容器提取为独立交付资产的内嵌图才逐图登记。PPTX 内部 media 不重复当作独立文件交付。
- `usage_status=formal/current_only` 且 `scientific_status=valid` 的图必须满足与其 provenance 相匹配的完整闭环。
- `simulation`: 图 → 绘图命令 → 脚本 → 全部输入 → `.mx3` → 初态配方。
- `theory`: 图 → 绘图/计算命令 → 理论代码 → 参数/JSON/CSV；`.mx3` 和初态允许明确 `N/A`。
- `schematic`: 没有数值原始数据时不伪造数据；必须交付可编辑源或生成脚本。
- `external`: 必须记录论文/报告来源、原始图号和用途；不能冒充本项目结果。
- `archive_only/superseded/failed` 可以不保证完全重绘，但必须记录来源、状态和不能重绘的原因。

`current_only` 只允许来自本规范 5.1 的 active 模块，并且必须被 canonical `progress.md` 或 paper master plan 的当前结论/结果路径直接引用；仅因文件位于 `results/` 或名称含 `final` 不足以成为 current result。

Manifest 引用规则：所有 `*_ids` 字段都是分号分隔、无空格、保持顺序的 ID 列表；列表元素不得包含分号。`input_data_ids/parent_data_ids` 外键到 `DATA_MANIFEST.data_id`，`run_ids` 外键到 `RUN_MANIFEST.run_id`，`theory_asset_ids` 外键到 `REQUIRED_ASSETS.asset_id`，`initial_state_recipe_id` 外键到 `INITIAL_STATE_RECIPES.recipe_id`，`source_document_ids` 外键到 `DOCUMENT_MANIFEST.document_id`。`plot_script_path` 是单一相对 POSIX 路径。只有 provenance 矩阵明确允许时字段才可写字面量 `N/A`，不得用空字符串含混表达。

### 6.3 禁止 OVF 后的空间图处理

依赖 OVF 的空间构型图不能只留下 PNG。构建阶段使用受支持的场读取库读取源 OVF，并导出成图所需的最小派生数据：

- 明确坐标和单位的切片数组；或
- 网格、矢量分量和掩膜；或
- 论文实际使用的采样点和颜色量。

优先格式为压缩 NPZ；需要人工查看时同时导出 CSV。派生脚本、源 OVF 的原路径和源文件 SHA256 写入 manifest，但 OVF 本身不复制进交付包。

所有数值数据同时登记到 `DATA_MANIFEST.csv`：

```text
data_id,path,sha256,data_kind,format,shape,columns,units,producer_script,
parent_source,parent_sha256,is_complete_field,notes
```

任何 OOMMF header 命中都直接失败。无 header 的大文本只有同时满足“文件至少 10 MiB、非注释数据行至少 100000、确定性抽样中至少 99% 恰为三个有限浮点数、没有声明的普通表格 schema”时才标记为疑似完整场。确定性抽样固定取前 1024 行、全文件等间距 4096 行和末尾 1024 行非注释数据；少于 6144 行时检查全部，不使用随机数。

NPY/NPZ 必须以 `allow_pickle=False` 读取并检查 shape，而不能只信 manifest 自报。以下任一情况视为完整场并拒收：四维数组含长度为 3 的矢量轴且其余维度乘积至少 100000；三个同 shape 的三维数组（如 mx/my/mz）且体素数至少 100000；单个三维数组所有轴均大于 4 且元素数至少 100000。二维切片或带长度 3 矢量轴的二维空间切片只有登记为 `data_kind=figure_slice`、具有 shape/units/producer/parent 证据时才允许。

疑似文件默认拒收；只有在 `DATA_MANIFEST.csv` 中登记为成图所需的非完整派生切片、具有 shape/columns/units/producer/parent 证据且验证器实测 `is_complete_field=false` 时才能显式放行。完整三维场不因改成 CSV/NPY/NPZ 而获准交付。

## 7. 仿真代码与初态重建

### 7.1 原始代码

- 原始 `.mx3` 放入 `simulation/original/`，保持字节不变并登记 SHA256。
- 原始脚本中的绝对路径和历史错误不得偷偷改写；在 README 中明确其 archival/unmodified 身份。

### 7.2 可移植入口

Active 主线另提供 `simulation/portable/`：

- 不写死 `/mnt/d/...`、`D:/...`、`E:/...` 或 worktree 路径。
- 通过单一 `00_handoff/PORTABLE_CONFIG.toml` 和构建 wrapper 生成临时可运行副本。
- wrapper 只替换输入/输出路径，不修改物理参数。
- 每个 portable 入口在 `PORTABLE_TRANSFORMS.csv` 记录对应 original 路径、original SHA256、输出路径及逐项精确 `old_literal → new_literal` 替换。
- 验证器把 portable 中登记的新字面量逆向恢复为旧字面量后，必须与 original 逐字节相同；任何未登记差异一律失败。由此无需发明 Mumax3 参数解析器。

### 7.3 初态配方

`INITIAL_STATE_RECIPES.csv` 至少记录：

```text
recipe_id,logical_name,original_ovf_reference,generator_script,
generator_parameters,relaxation_mx3,expected_output,consumers,
verification_status,verification_evidence,notes
```

标准链路：

```text
解析初态生成器
  → Mumax3 弛豫脚本
  → 本地产生临时 OVF
  → 主线仿真
  → table/派生数组
  → 绘图
```

交付包不含链路中产生的 OVF。本任务不运行新的物理仿真，因此配方状态必须诚实区分：

- `documented_only`: 路径和参数已记录，未在本任务中运行。
- `generator_smoke_tested`: 解析生成器已临时运行并通过格式检查，未运行弛豫。
- `existing_full_chain_evidence`: 源项目已有完整链路日志/结果证据，本任务只核对证据。

不得把 `documented_only` 写成“已完整复跑验证”。Active 主线至少需要配方映射和现有结果证据；若没有任何初态来源证据，该算例只能转入 archive。

OVF 依赖门适用于所有 active 消费者，不只 `.mx3`。例如 Thiele 原始代码依赖 `ovf_archive.tar.zst` 时，原脚本可以按字节保留，但 portable 闭环必须改由 `INITIAL_STATE_RECIPES.csv` 重建临时纹理，或使用登记到 `DATA_MANIFEST.csv` 的非完整派生输入；含 OVF 的 archive 不进入交付包。

## 8. 文档策略

只保留三层说明：

1. 根 README：五分钟内理解项目、目录和阅读顺序。
2. `00_handoff/`：状态、诚信红线、环境、manifest、排除和验证。
3. 每个研究主题 README：研究问题、有效结论、失败结论、入口文件和复现命令。

README 必须使用相对 Markdown 链接。禁止：

- “保留的分类目录”一类占位描述。
- 机械重复列出每个相似 `.mx3` 的全部参数。
- 把历史任务或代理规则伪装成当前接手指令。
- 未标注地复述已推翻的 `v∝B^1.99`、已确认本征频率等陈旧说法。

允许存在 README 的位置由构建器显式列举：根、`00_handoff/`、每个一级模块和 `TOPIC_INDEX.csv` 登记的真实研究 topic；`.out`、单文件 data/figures 叶目录禁止 README。Topic README 必须包含“研究问题、当前状态、有效/无效结论、数据与代码入口、复现级别”五节。占位短语、旧代理命令、学校模板说明和未标记历史路径触发 G5 失败。

README allowlist 明确包含：`README.md`、`00_handoff/START_HERE.md`、固定一级模块 `0[1-5]_*/README.md`、`shared/README.md`、`TOPIC_INDEX.csv` 中逐项声明的 `readme_path`，以及且仅有 `90_archive/*/README.md` 这一级 archive 说明。构建器在 `verification_report.json` 中输出最终 allowlist；任何其他 README 失败。

## 8.1 Manifest schema

所有 CSV 使用 UTF-8、逗号分隔、LF 换行和 RFC 4180 引号规则；路径均为相对交付根的 POSIX 路径。ID 在各自文件内唯一且非空。

`DOCUMENT_MANIFEST.csv`：

```text
document_id,document_type,title,path,sha256,source_path,
scientific_status,purpose,notes
```

`RUN_MANIFEST.csv`：

```text
run_id,module,case_name,status,original_mx3,portable_entry,
table_data_ids,other_data_ids,initial_state_recipe_id,result_summary,notes
```

`status` 只能为 `active`、`archive` 或 `reference_only`。每个 `status=active` 且存在 `original_mx3` 的运行都必须有非空 `portable_entry`，并恰好对应 `PORTABLE_TRANSFORMS.csv` 一行；反向也不得存在没有 active run 的 portable transform。G4 要求 active portable 集合非空并做集合相等检查，禁止空清单真空通过。

`REQUIRED_ASSETS.csv`：

```text
asset_id,module,source_path,required_reason,expected_target_class,
target_path,source_sha256,status,notes
```

其中 `status` 只能为 `copied_active`、`copied_archive` 或 `excluded_with_reason`。对 `copied_*` 必须有 `target_path`，对 `excluded_with_reason` 必须有非空 `notes` 且 `target_path=N/A`；缺行、重复 `source_path`、空目标/排除理由均失败。`FIGURE_MANIFEST.csv`、`DATA_MANIFEST.csv`、`INITIAL_STATE_RECIPES.csv` 和 `PORTABLE_TRANSFORMS.csv` 使用前文定义字段，所有被引用 ID 必须通过外键检查。

`TOPIC_INDEX.csv`：

```text
topic_id,module,path,source_roots,current_status,readme_path,notes
```

`path` 必须位于 `01_` 至 `05_` 一级模块内且唯一；`readme_path` 必须等于 `<path>/README.md`。Archive 分类不作为 research topic，使用固定的 `90_archive/*/README.md` 规则。

## 9. 自动验收

`00_handoff/verify_delivery.py` 提供以下硬门，任一失败即非零退出。

### G1 — 场文件排除

- 文件名和 magic-byte 扫描：OVF/OMF 及压缩变体为零。
- 内容扫描：检测 OOMMF header、Data Text/Binary 标记，以及第 6.3 节定义的文本和 NPY/NPZ 完整场；只允许验证器实测且 manifest 支持的非完整派生数据豁免。
- 压缩包按第 5.3 节递归列目录；不得包含 OVF/OMF，任何不支持、加密、损坏或超资源上限的包 fail-closed。

### G2 — 图表闭环

- 包内所有独立图片均登记；文档容器进入 `DOCUMENT_MANIFEST.csv`。
- 所有 `formal/current_only` 图都接受检查，不允许用 `not_applicable/unverified` 绕过：`valid` 的 simulation/theory 图满足完整数值闭环；schematic/external 图无论 scientific status 为何均满足可编辑源/原始出处闭环；`superseded/failed/unverified` 图必须位于 archive、给出来源和醒目警告，且不得出现在 active README 的有效结论入口。
- SHA256 与 manifest 一致。
- 绘图命令至少通过 dry-run/input-validation；每个 active 一级模块至少选 1 张代表图实际重绘。比较方法和容差逐图写入 manifest，数值输出优先用 `numpy.testing.assert_allclose`，不得临时拍脑袋选择像素阈值。

### G3 — 项目主线覆盖

验证器独立按第 5.1 节的精确文件和源根算法重新枚举候选，再与 `REQUIRED_ASSETS.csv` 做集合相等比较；不能只相信 CSV 自报。随后检查每个精确源路径和目标路径，覆盖稳定性、自旋波、机理控制、Thiele、LIF、论文/汇报和共享工具。任何 required asset 缺失即失败。特别检查：

- Thiele 收敛代码与两组结果。
- B/D/E 理论文档。
- 正式论文研究图、绘图脚本和 CSV。
- `compute_hopf_index.py`、漂移统一重跑脚本和数据。

### G4 — 可移植性与初态

- 扫描 include globs 固定为 `0[1-5]_*/**/simulation/portable/**/*.{mx3,py,sh,ps1,json,yaml,yml,toml}`、`0[1-5]_*/**/analysis/**/*.{py,sh,ps1,m,json,yaml,yml,toml}`、`0[1-5]_*/**/*run*.{py,sh,ps1,json,yaml,yml,toml}`、`shared/{analysis,plotting,initial_state}/**/*.{py,sh,ps1,m,mx3,json,yaml,yml,toml}`、`00_handoff/PORTABLE_CONFIG.toml`，以及 `00_handoff/*MANIFEST.csv` 的命令/可执行路径字段；其中可执行依赖不得含原机器绝对路径。
- 排除 globs 仅限 `0[1-5]_*/**/simulation/original/**`、`90_archive/**`，以及 manifest 明确定义的 `source_path/original_ovf_reference/parent_source` provenance 字段；排除项中的历史路径必须明确标为非执行字符串。
- 每个 active OVF 消费者（`.mx3`、Python、Shell 和理论代码）的依赖均有初态配方或非完整派生数据映射。
- 原始脚本 SHA256 与源项目一致。
- 按 `PORTABLE_TRANSFORMS.csv` 逆向替换后，portable 与 original 逐字节相同。
- `RUN_MANIFEST` 中 active originals 与 `PORTABLE_TRANSFORMS` 的 original 集合完全相等且非空；每个 portable_entry 文件存在。

### G5 — 结构与可读性

- active 中不得出现 `failed`、`interrupted`、`incomplete`、`superseded`。
- 不为 `table.txt` 单独创建 README。
- README 必须有有效相对链接。
- legacy/failed 内容只能在 `90_archive/`。
- 根目录和一级研究模块数量固定，不生成新的平行分类体系。
- README 路径必须属于第 8 节显式 allowlist，`90_archive/*/README.md` 仅允许在直接分类目录，且 topic README 五个必需章节齐全。
- 对 active 来源建立 denylist：学校模板、代理说明、预览/缓存、legacy/failed/interrupted/superseded 源路径不得映射到 active。

## 10. 构建产物与审计记录

构建结束时必须产生：

- 源 Git branch、HEAD、dirty 状态和构建时间。
- bd 状态快照：`BD_SNAPSHOT.json` 保存当前 open/in_progress/closed 数量及完整 JSON。
- `SOURCE_MAP.csv` 保存每个源路径 → 交付路径、复制方式和源 SHA256。
- 构建前生成 `OLD_PACKAGE_BASELINE.csv`，逐项记录旧包相对路径、类型、大小、SHA256 和符号链接目标；构建结束后严格重算并比较，任一变化即失败。
- 先生成最终只读 `verification_report.json`，再生成 `SHA256SUMS.txt`。SHA256 清单覆盖包内其余全部普通文件但明确排除自身；最终验证不得改写报告。
- 若以后生成单一压缩交付包，其整体 SHA256 作为包外 sidecar，不写入归档自身。
- 排除清单及体积统计。
- 自动验收 JSON 和人类可读摘要。
- 原交付包与 v2 的文件数、目录数、体积和模块覆盖比较。

## 11. 非目标

- 不在本任务中开展新的物理仿真或补做研究结论。
- 不修改源项目中的物理参数和历史结果。
- 不声称仅凭哈希即可证明科学正确性；哈希只证明文件一致。
- 不把 `documented_only` 初态配方描述成已运行或已验证的完整重建。
- 不把所有下载论文、学校模板或历史工作环境一起打包。
- 不在用户再次确认前删除或替换旧交付目录。

## 12. 完成标准

只有同时满足以下条件，`Hopfion-ty3` 才可关闭：

1. `hopfion_delivery_20260706_v2/` 构建完成，旧目录未变。
2. G1–G5 全部通过，`verify_delivery.py` 返回 0。
3. 所有 `usage_status=formal/current_only` 且 `scientific_status=valid` 的图按 provenance 类型具有完整数据血缘；无法闭环的图不得伪装为有效主线结果。
4. Thiele、理论 guidance、论文最终研究图和最新汇报均已纳入。
5. 原始 `.mx3` 有 SHA256，可移植入口无物理参数改动。
6. 初态重建配方或登记的非完整派生输入覆盖所有 active OVF 消费者，并诚实记录验证级别。
7. 根 README 能让新同事按顺序完成“理解项目 → 找到结论 → 找到数据 → 重绘图 → 重跑仿真”。
8. `SOURCE_SNAPSHOT.md`、`EXCLUSIONS.md`、全部 manifest、旧包基线、SHA256 和验证报告齐全。
9. 用户验收 v2 后，才讨论是否替换原目录。
