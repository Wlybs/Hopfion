# thesis_v2 待执行修改清单

并行期内讨论确认但尚未执行的修改方案。terminal 1 完成图像任务（D+E+I+J）后，按本清单逐项执行。

每条格式：
- **状态**：讨论中 / 已确认 / 已执行
- **文件/位置**：涉及的具体文件和行号范围
- **改前 → 改后**：精确的 old_string → new_string
- **风险/验证**：需要注意的副作用和验证方式

---

## 全文级修改（并行安全）

### P1. 人名消除
**状态**：批 1（ch04/05/07）方案已确认（2026-04-21）；批 2（ch01 1.2 节）待写

**决策**：A 风格（简化中性）+ 全文范围 + \cite{} 保留，相邻 cite 合并

#### 批 1：ch04 + ch05 + ch07（共 ~9 处）

**改动 1.1：`chapters/ch04-stability.tex:9`**
```
old:
本文选取的竞争交换铁磁体系源于 Sallermann 等人的理论工作\cite{sallermann2023stability},Lobanov 与 Uzdin 随后在同一类体系中对 霍普夫子 的有限寿命、坍塌路径及逃逸机制开展了深入分析\cite{lobanov2023lifetime}。
new:
本文选取的竞争交换铁磁体系源于已有理论工作\cite{sallermann2023stability}，随后的研究在同一类体系中对 霍普夫子 的有限寿命、坍塌路径及逃逸机制开展了深入分析\cite{lobanov2023lifetime}。
```

**改动 1.2：`chapters/ch05-dynamics.tex:4`**
```
old:
斯格明子 的自旋波运动学已由 Ding 等\cite{ding2015motion}与 Huang 等\cite{huang2023transient}给予了较为系统的刻画，回旋矢量为零的 斯格明子环 也被证实可在自旋波作用下发生显著迁移\cite{shen2018skyrmionium}。相比之下，三维 霍普夫子 在自旋波激励下的动力学行为至今缺少系统性的微磁学研究。理论方面，磁振子霍尔效应已由 Saji 等人\cite{saji2023magnonic}在解析框架下作出预测；Zhang 等人\cite{zhang2023magnon}则在反铁磁背景中讨论了 霍普夫子 运动与自旋波散射间的耦合关系。
new:
斯格明子 的自旋波运动学已由已有研究\cite{ding2015motion,huang2023transient}给予了较为系统的刻画，回旋矢量为零的 斯格明子环 也被证实可在自旋波作用下发生显著迁移\cite{shen2018skyrmionium}。相比之下，三维 霍普夫子 在自旋波激励下的动力学行为至今缺少系统性的微磁学研究。理论方面，磁振子霍尔效应已在解析框架下作出预测\cite{saji2023magnonic}；另有研究在反铁磁背景中讨论了 霍普夫子 运动与自旋波散射间的耦合关系\cite{zhang2023magnon}。
```

**改动 1.3：`chapters/ch05-dynamics.tex:9`（在 P2 改动生效后执行）**
```
old:
STT 驱动下 霍普夫子 的动力学已由 Wang 等人\cite{wang2019current}和 Liu 等人\cite{liu2020three}分别在不同磁性体系中完成了较为详尽的数值与解析分析。
new:
STT 驱动下 霍普夫子 的动力学已在不同磁性体系中完成了较为详尽的数值与解析分析\cite{wang2019current,liu2020three}。
```
注意：P2 改动已删除后续方程段；本改动只动首句。

**改动 1.4：`chapters/ch05-dynamics.tex:314`（Shen 等）**
```
old:
Shen 等\cite{shen2018skyrmionium}研究的回旋矢量为零的 斯格明子环 则沿自旋波方向做无偏转的直线运动，这一行为特征与 霍普夫子 $\mathbf{G} = 0$ 属性之间的对应关系值得关注。
new:
此前工作所研究的回旋矢量为零的 斯格明子环 则沿自旋波方向做无偏转的直线运动\cite{shen2018skyrmionium}，这一行为特征与 霍普夫子 $\mathbf{G} = 0$ 属性之间的对应关系值得关注。
```

**改动 1.5：`chapters/ch05-dynamics.tex:316`（Saji 等人在二维对比段）**
```
old:
Saji 等人\cite{saji2023magnonic}曾在解析理论中预言类似的磁振子 Hall 效应，本章仿真从微磁学层面首次对该预言给出了定量支撑。
new:
已有解析理论曾预言类似的磁振子 Hall 效应\cite{saji2023magnonic}，本章仿真从微磁学层面首次对该预言给出了定量支撑。
```

**改动 1.6：`chapters/ch07-conclusion.tex` 总结第二大点末尾**
```
old:
从微磁学仿真层面为 Saji 等人此前的解析理论预言提供了独立的定量支撑。
new:
从微磁学仿真层面为此前的解析理论预言\cite{saji2023magnonic}提供了独立的定量支撑。
```

**执行顺序依赖**：
- P2 必须先于本批执行（改动 1.3 依赖 P2 已删除方程段）
- 其他 5 处独立可单独执行

**验证**：
- [ ] 活跃章节（排除 _rewritten/.v23bak）`grep -nE "[A-Z][a-z]+ 等人?|[A-Z][a-z]+ 与 [A-Z][a-z]+"` 只剩 ch01 1.2 节中的条目（ch04/05/07 归零）
- [ ] 编译 0 citation undefined
- [ ] 批 1 执行后 \cite{} 合并处 `\cite{a,b}` 语法正确

#### 批 2：ch01-intro.tex 1.2 节（~18 处，5 段整段替换）

全部在 `chapters/ch01-intro.tex` 文件内。按段落组织 old→new（每段一次 Edit 替换）。

**改动 2.1：line 16 段（理论预测与实验观测）**
```
old:
从理论渊源来看，霍普夫子 研究的学术根基可追溯至拓扑学中的 Hopf 映射。Tai 与 Smalyukh 较早地从理论层面论证了非中心对称磁性纳米结构中静态 Hopf 孤子的存在性\cite{tai2018static}，从而奠定了该拓扑构型在固态磁性材料中得以实现的理论基础。随后，磁性多层膜体系被 Kent 等人用于 霍普夫子 的构建与实验观测\cite{kent2021creation}。2023 年，Zheng 团队利用电子全息术在立方手性磁体中实现了稳定 霍普夫子 环的直接成像\cite{zheng2023hopfion}，该成果在实验层面具有里程碑式的意义。同年，Yu 等人在螺旋磁体 FeGe 中发现了分数 霍普夫子 及其集合体现象，并对电流驱动条件下的运动特性进行了讨论\cite{yu2023realization}。
new:
从理论渊源来看，霍普夫子 研究的学术根基可追溯至拓扑学中的 Hopf 映射。较早的理论工作论证了非中心对称磁性纳米结构中静态 Hopf 孤子的存在性\cite{tai2018static}，从而奠定了该拓扑构型在固态磁性材料中得以实现的理论基础。随后，磁性多层膜体系被用于 霍普夫子 的构建与实验观测\cite{kent2021creation}。2023 年，已有工作利用电子全息术在立方手性磁体中实现了稳定 霍普夫子 环的直接成像\cite{zheng2023hopfion}，该成果在实验层面具有里程碑式的意义。同年，已有研究在螺旋磁体 FeGe 中发现了分数 霍普夫子 及其集合体现象，并对电流驱动条件下的运动特性进行了讨论\cite{yu2023realization}。
```

**改动 2.2：line 19 段（稳定性研究开头）**
```
old:
稳定性是 霍普夫子 走向器件应用所面临的首要问题。Guslienko 在其综述中围绕圆柱形样品体系，对 霍普夫子 的稳定判据和边界效应做了全面梳理\cite{guslienko2024review}。
new:
稳定性是 霍普夫子 走向器件应用所面临的首要问题。已有综述围绕圆柱形样品体系，对 霍普夫子 的稳定判据和边界效应做了全面梳理\cite{guslienko2024review}。
```

**改动 2.3：line 21 段（DMI 体系）**
```
old:
含 Dzyaloshinskii-Moriya 相互作用（DMI）的手性磁体是 霍普夫子 稳定性研究起步最早、积累最深的体系。Sutcliffe 以解析方法推导了手性磁体中 霍普夫子 的理论构型\cite{sutcliffe2018hopfions}；手性磁体纳米盘对 霍普夫子 的束缚能力随后由 Liu 等人经微磁学仿真得到验证\cite{liu2018binding}；体块螺旋磁体中 霍普夫子 的椭圆稳定性条件则经 Metlov 进一步明确\cite{metlov2025elliptical}。在实验验证方面，立方手性磁体 MnGe 中 霍普夫子 环结构的首次观测归功于 Zheng 等人\cite{zheng2023hopfion}，而 FeGe 螺旋磁体中分数 霍普夫子 的实现及其电流驱动动力学的研究则由 Yu 等人完成\cite{yu2023realization}。这些研究成果表明，DMI 体系中 霍普夫子 稳态存在的参数空间已逐步明朗。
new:
含 Dzyaloshinskii-Moriya 相互作用（DMI）的手性磁体是 霍普夫子 稳定性研究起步最早、积累最深的体系。已有工作以解析方法推导了手性磁体中 霍普夫子 的理论构型\cite{sutcliffe2018hopfions}；手性磁体纳米盘对 霍普夫子 的束缚能力随后经微磁学仿真得到验证\cite{liu2018binding}；体块螺旋磁体中 霍普夫子 的椭圆稳定性条件进一步得到明确\cite{metlov2025elliptical}。在实验验证方面，立方手性磁体 MnGe 中 霍普夫子 环结构的首次观测已由实验完成\cite{zheng2023hopfion}，而 FeGe 螺旋磁体中分数 霍普夫子 的实现及其电流驱动动力学的研究则另有工作加以完成\cite{yu2023realization}。这些研究成果表明，DMI 体系中 霍普夫子 稳态存在的参数空间已逐步明朗。
```

**改动 2.4：line 23 段（竞争交换体系）**
```
old:
相比之下，竞争交换铁磁体系中 霍普夫子 稳定性的研究进展相对滞后。Sallermann 等人的理论计算工作揭示了体块磁体中竞争交换相互作用（frustrated exchange）为三维拓扑结构提供稳定化支撑的物理机制\cite{sallermann2023stability}；Lobanov 与 Uzdin 则对该体系下 霍普夫子 的有限寿命及坍塌路径做了深入剖析\cite{lobanov2023lifetime}。本文的稳定性研究正是在竞争交换铁磁体系的框架内展开。
new:
相比之下，竞争交换铁磁体系中 霍普夫子 稳定性的研究进展相对滞后。已有理论计算工作揭示了体块磁体中竞争交换相互作用（frustrated exchange）为三维拓扑结构提供稳定化支撑的物理机制\cite{sallermann2023stability}；后续研究对该体系下 霍普夫子 的有限寿命及坍塌路径做了深入剖析\cite{lobanov2023lifetime}。本文的稳定性研究正是在竞争交换铁磁体系的框架内展开。
```

**改动 2.5：line 25 段（几何限域）**
```
old:
几何限域效应与新型拓扑转变同样是当前活跃的研究前沿。环形纳米环曲率对 霍普夫子 的稳定化作用由 Corona 等人提出\cite{corona2023curvature}；霍普夫子 与 斯格明子 之间的拓扑相变过程\cite{gao2024topological,souza2025topological}以及时空编织机制\cite{knapman2024spacetime}亦受到研究者的持续关注。
new:
几何限域效应与新型拓扑转变同样是当前活跃的研究前沿。环形纳米环曲率对 霍普夫子 的稳定化作用已被提出\cite{corona2023curvature}；霍普夫子 与 斯格明子 之间的拓扑相变过程\cite{gao2024topological,souza2025topological}以及时空编织机制\cite{knapman2024spacetime}亦受到持续关注。
```

**改动 2.6：line 28 段（电流驱动）**
```
old:
精准操控 霍普夫子 的运动轨迹，构成其迈向实际器件的核心技术环节。电流驱动领域的研究中，Wang 等人率先对铁磁体内 Bloch 型与 N\'{e}el 型 霍普夫子 在 STT 作用下的动力学行为进行了系统性研究\cite{wang2019current}，并指出轴对称 霍普夫子 的回旋矢量满足 $\mathbf{G} = 0$，因而沿电流方向做无霍尔偏转的直线运动。Liu 等人在此基础上对 STT 驱动三维 霍普夫子 的完整动力学特征做了更为深入的分析，同时明确了回旋矢量与 Hopf 指数之间的定量关联\cite{liu2020three}。霍普夫子 涌现磁多极矩结构所引发的非线性响应特性，也在 Liu 等人的后续研究中得到揭示\cite{liu2022emergent}。
new:
精准操控 霍普夫子 的运动轨迹，构成其迈向实际器件的核心技术环节。电流驱动领域的研究中，已有工作率先对铁磁体内 Bloch 型与 N\'{e}el 型 霍普夫子 在 STT 作用下的动力学行为进行了系统性研究\cite{wang2019current}，并指出轴对称 霍普夫子 的回旋矢量满足 $\mathbf{G} = 0$，因而沿电流方向做无霍尔偏转的直线运动。后续工作在此基础上对 STT 驱动三维 霍普夫子 的完整动力学特征做了更为深入的分析，同时明确了回旋矢量与 Hopf 指数之间的定量关联\cite{liu2020three}。霍普夫子 涌现磁多极矩结构所引发的非线性响应特性，也在后续研究中得到揭示\cite{liu2022emergent}。
```

**改动 2.7：line 30 段（自旋波驱动）**
```
old:
与电流驱动相比较，自旋波（Magnon）驱动方案在热耗散指标上表现出显著优势。二维体系中，自旋波驱动 斯格明子 运动的行为已被较为充分地研究。传播自旋波对磁性 斯格明子 运动规律的影响由 Ding 等人加以阐明\cite{ding2015motion}；自旋波驱动 斯格明子 时出现的瞬态逆行运动现象由 Huang 等人首次报道\cite{huang2023transient}；Shen 等人则证实，回旋矢量为零的 斯格明子环 在自旋波作用下同样可实现有效驱动\cite{shen2018skyrmionium}。将视角拓展至三维 霍普夫子 体系，Saji 等人从理论上预测了 霍普夫子 所诱导的磁振子霍尔效应与磁振子聚焦现象\cite{saji2023magnonic}。Zhang 等人揭示了反铁磁体系内 霍普夫子 调节自旋波散射特性的物理机制，并初步探讨了其在元学习方向的应用前景\cite{zhang2023magnon}。电子在 霍普夫子 上的散射行为则经 Pershoguba 等人的数值计算予以量化\cite{pershoguba2021electronic}。Souza 等人的工作进一步表明，自旋波驱动 霍普夫子 运动的同时还可诱发拓扑转变\cite{souza2025topological}，从而为器件功能设计开辟了新的途径。
new:
与电流驱动相比较，自旋波（Magnon）驱动方案在热耗散指标上表现出显著优势。二维体系中，自旋波驱动 斯格明子 运动的行为已被较为充分地研究。传播自旋波对磁性 斯格明子 运动规律的影响已被阐明\cite{ding2015motion}；自旋波驱动 斯格明子 时出现的瞬态逆行运动现象已被首次报道\cite{huang2023transient}；已有研究证实，回旋矢量为零的 斯格明子环 在自旋波作用下同样可实现有效驱动\cite{shen2018skyrmionium}。将视角拓展至三维 霍普夫子 体系，已有理论预测了 霍普夫子 所诱导的磁振子霍尔效应与磁振子聚焦现象\cite{saji2023magnonic}。另有研究揭示了反铁磁体系内 霍普夫子 调节自旋波散射特性的物理机制，并初步探讨了其在元学习方向的应用前景\cite{zhang2023magnon}。电子在 霍普夫子 上的散射行为则经数值计算已予以量化\cite{pershoguba2021electronic}。近期工作进一步表明，自旋波驱动 霍普夫子 运动的同时还可诱发拓扑转变\cite{souza2025topological}，从而为器件功能设计开辟了新的途径。
```

**批 2 总结**：共 ~18 处人名前缀消除；改动 2.1~2.7 共 7 段整段替换。

**验证（批 1+2 全部完成后）**：
- [ ] `grep -nE "[A-Z][a-z]+ (等人?|与 [A-Z][a-z]+|团队)" chapters/ch0[1-7]*.tex` 应返回 0 行
- [ ] 编译 0 citation undefined / 0 reference undefined
- [ ] 渲染 ch01 1.2 节所在页 + ch05 5.1 节 + ch07 总结，目视文风通顺

---

### P2. ch02 Thiele 方程（2.4 节）去留
**状态**：✅ 方案已确认（2026-04-21），等 T1 完成后执行

**决策**：A 方案（整节删 + ch05 压缩为文献引用 + ch01 章节预告更新）

**使用情况分析**：
- Thiele 方程本身在论文中**无实际计算应用**
- 唯一后续使用：ch05:9 借 G=0 结论解释"放弃 STT 转自旋波"
- ch05 5.1 节按 P8（ch01 重写）计划终将整节迁往引言，现在先瘦身

**改动 1：`chapters/ch02-theory.tex` 删除整个 2.4 节（line 147-162）**

old_string（含前导空行）：
```
\section{Thiele 集体坐标方程}

对于以刚性模式运动的磁性拓扑结构，Thiele 方程提供了一种将 LLG 方程约化为质心运动方程的有效途径：
\begin{equation}
  \mathbf{G} \times \mathbf{v} + \mathcal{D} \cdot \mathbf{v} = \mathbf{F}
  \label{eq:thiele}
\end{equation}
其中 $\mathbf{v}$ 为 霍普夫子 质心速度，$\mathbf{F}$ 为外部驱动力，$\mathcal{D}$ 为耗散张量，$\mathbf{G}$ 为回旋矢量。

对于 霍普夫子，回旋矢量 $\mathbf{G}$ 与 Hopf 指数的关系为\cite{liu2020three}：
\begin{equation}
  G_i = \frac{\mu_0 M_s}{\gamma_0} \int \epsilon_{ijk} \, \mathbf{m} \cdot \left( \frac{\partial \mathbf{m}}{\partial x_j} \times \frac{\partial \mathbf{m}}{\partial x_k} \right) d^3r
  \label{eq:gyrovector}
\end{equation}

需要指出的是，Wang 等人\cite{wang2019current}与 Liu 等人\cite{liu2020three}分别独立推导得到轴对称 霍普夫子 的回旋矢量 $\mathbf{G} = 0$ 这一结论。其物理含义在于，STT 驱动下 霍普夫子 不产生霍尔偏转，沿驱动力方向做直线运动——此行为与二维 斯格明子 的动力学特征截然不同。
```

new_string：空字符串（完全删除整节）

**改动 2：`chapters/ch01-intro.tex:41` 去掉章节预告 Thiele**

old_string：
```
第二章建立理论框架，涵盖微磁学基本模型、霍普夫子 的拓扑性质、竞争交换相互作用机制以及 Thiele 集体坐标方程。
```

new_string：
```
第二章建立理论框架，涵盖微磁学基本模型、霍普夫子 的拓扑性质以及竞争交换相互作用机制。
```

**改动 3：`chapters/ch05-dynamics.tex:9-14` 删除 Thiele 推导段**

old_string（含方程）：
```
STT 驱动下 霍普夫子 的动力学已由 Wang 等人\cite{wang2019current}和 Liu 等人\cite{liu2020three}分别在不同磁性体系中完成了较为详尽的数值与解析分析。核心结论简明扼要：由于轴对称 霍普夫子 的回旋矢量恒为零（$\mathbf{G} = 0$），它在电流驱动下沿流向做纯粹的直线运动，霍尔偏转完全缺席——二维 斯格明子 中因非零拓扑荷而产生的显著横向偏移，在三维 霍普夫子 上并不复现。其运动速度可通过 Thiele 方程\cref{eq:thiele}导出：
\begin{equation}
  v = \frac{u}{\alpha - \beta} \cdot \frac{\mathcal{D}_{xz}}{\mathcal{D}_{xx}}
  \label{eq:hopfion-stt-velocity}
\end{equation}
其中 $u$ 为与电流密度成正比的速度参数，$\alpha$ 和 $\beta$ 分别为 Gilbert 阻尼和非绝热 STT 系数，$\mathcal{D}$ 为耗散张量。
```

new_string：
```
STT 驱动下 霍普夫子 的动力学已由 Wang 等人\cite{wang2019current}和 Liu 等人\cite{liu2020three}分别在不同磁性体系中完成了较为详尽的数值与解析分析。核心结论简明扼要：由于轴对称 霍普夫子 的回旋矢量恒为零（$\mathbf{G} = 0$），它在电流驱动下沿流向做纯粹的直线运动，霍尔偏转完全缺席——二维 斯格明子 中因非零拓扑荷而产生的显著横向偏移，在三维 霍普夫子 上并不复现。
```

**验证清单**：
- [ ] 编译后 `grep -cE "Citation.*undefined|Reference.*undefined"` = 0
- [ ] grep 整个工程无遗留 `\cref{eq:thiele}` / `\cref{eq:gyrovector}` / `\cref{eq:hopfion-stt-velocity}`（备份文件 .v23bak 不计）
- [ ] ch01:41 章节预告与 ch02 实际章节数匹配

---

### P3. 摘要定性化 + 幅度标度律软化（方案 B）
**状态**：✅ 方案已确认（2026-04-21）

**决策**：
- 中文摘要 5 处定量 → 定性
- 英文摘要同步 α
- **幅度标度律采用方案 B 软化**：删 $B_0^{1.99}$ 幂律和"与斯格明子一致"断言，保留"阈值 + 单调依赖"两个定性特征（数据支撑薄弱：仅 4 个有效点、范围 4×、1 个频率、1 种组合）

**牵动位置**（全部改动，T1 完成后执行）：

---

**改动 3.1：中文摘要 段 2（main.tex:55）**
```
old:
在拓扑稳定性方面，本文构建了一套融合局域旋转矩阵与环面坐标映射的解析初始化方案，使任意拓扑荷及反铁磁交替背景下的霍普夫子自旋构型均可程序化生成并实现三维可视化。竞争交换铁磁体系被选作弛豫分析的目标平台：以上述工具所构建的理想初始态为起点，弛豫过程收敛至固有尺寸吸引子，其大半径为 $R_{\text{eq}} = \SI{2.60}{nm}$。控制变量数值实验进一步证实，背景磁化取向不影响漂移行为。各向异性精细扫描则将临界失稳阈值锁定在 $K_{u1,c} \in (\num{52e3}, \num{55e3}) \, \si{J/m^3}$。
new:
在拓扑稳定性方面，本文构建了一套融合局域旋转矩阵与环面坐标映射的解析初始化方案，使任意拓扑荷及反铁磁交替背景下的霍普夫子自旋构型均可程序化生成并实现三维可视化。竞争交换铁磁体系被选作弛豫分析的目标平台：以上述工具所构建的理想初始态为起点，弛豫过程收敛至一固有尺寸吸引子。控制变量数值实验进一步证实，背景磁化取向不影响漂移行为。各向异性精细扫描则锁定了各向异性诱导失稳的参数窗口。
```

**改动 3.2：中文摘要 段 3（main.tex:57）**
```
old:
在此基础上，本文转向同一竞争交换体系中霍普夫子对自旋波激励的动态响应。数值结果揭示了一条选择性驱动法则：面内极化磁振子可有效激发霍普夫子平动，而面外极化分量的驱动效率趋近于零。轴向传播构型下频率扫描呈现多峰共振谱，本文仿真条件下 $\SI{1100}{GHz}$ 处响应最强，所致位移达 $\SI{18.1}{nm}$；驱动幅度与漂移速度之间满足 $v \propto B_0^{1.99}$ 幂律标度。当激励切换为面内传播时，霍普夫子沿近 $90°$ 拓扑霍尔角方向偏转，该角度对频率、强度及激励几何的变化表现出显著稳健性。以上数值证据从微磁学尺度为霍普夫子磁振子霍尔效应提供了定量佐证。本研究据此利用面内与轴向传播模式在方向响应上的互补关系，提出并经仿真验证了一种基于频率切换的霍普夫子轴向双向可逆调控方案。
new:
在此基础上，本文转向同一竞争交换体系中霍普夫子对自旋波激励的动态响应。数值结果揭示了一条选择性驱动法则：面内极化磁振子可有效激发霍普夫子平动，而面外极化分量的驱动效率趋近于零。轴向传播构型下频率扫描呈现多峰共振谱，其中某一特定频率处位移最为显著；驱动幅度达到阈值后霍普夫子出现稳定迁移。当激励切换为面内传播时，霍普夫子沿近乎垂直于驱动方向的拓扑霍尔角偏转，该角度对频率、强度及激励几何的变化表现出显著稳健性。以上数值证据从微磁学尺度为霍普夫子磁振子霍尔效应提供了仿真支撑。本研究据此利用面内与轴向传播模式在方向响应上的互补关系，提出并经仿真验证了一种基于频率切换的霍普夫子轴向双向可逆调控方案。
```

**改动 3.3：英文摘要 段 2（main.tex:70）**
```
old:
First, based on existing toroidal coordinate mapping theories, we developed a programmatic initialization script and 3D visualization tools for hopfions with arbitrary topological charges and antiferromagnetic backgrounds. In a frustrated ferromagnetic system, the ideal initial configurations were constructed using the above tools and subjected to relaxation analysis. Under the material parameters adopted in this study, we found an intrinsic size attractor ($R_{\text{eq}} = \SI{2.60}{nm}$). Background magnetization orientation showed no influence on hopfion drift. Under the same parameter set, the critical anisotropy threshold was determined as $K_{u1,c} \in (\num{52e3}, \num{55e3}) \, \si{J/m^3}$.
new:
First, based on existing toroidal coordinate mapping theories, we developed a programmatic initialization script and 3D visualization tools for hopfions with arbitrary topological charges and antiferromagnetic backgrounds. In a frustrated ferromagnetic system, the ideal initial configurations were constructed using the above tools and subjected to relaxation analysis. An intrinsic size attractor was identified under the material parameters adopted in this study. Background magnetization orientation showed no influence on hopfion drift. A critical anisotropy window for hopfion collapse was determined via fine-step parameter sweeps.
```

**改动 3.4：英文摘要 段 3（main.tex:72）**
```
old:
Second, we studied spin-wave-driven hopfion dynamics in the frustrated exchange system. Only in-plane oscillating spin waves effectively drive hopfions. Frequency sweeps revealed a multi-peak resonance spectrum; under the simulation conditions employed here, the strongest response occurs at $\SI{1100}{GHz}$ under axial propagation. The velocity scales as $v \propto B_0^{1.99}$ with driving amplitude. In-plane propagation produces a stable topological Hall angle of $\sim 90°$, providing quantitative numerical support for the magnonic Hall effect of hopfions at the micromagnetic level. Additionally, we proposed a bidirectional axial control scheme via spin-wave frequency switching.
new:
Second, we studied spin-wave-driven hopfion dynamics in the frustrated exchange system. Only in-plane oscillating spin waves effectively drive hopfions. Frequency sweeps revealed a multi-peak resonance spectrum; the strongest response was observed at a specific axial driving frequency. The hopfion begins to migrate stably once the driving amplitude exceeds a threshold. In-plane propagation produces a topological Hall angle close to perpendicular to the driving direction, robust against variations in frequency, amplitude, and excitation geometry. These numerical observations provide simulation-level support for the magnonic Hall effect of hopfions. Additionally, we proposed a bidirectional axial control scheme via spin-wave frequency switching.
```

---

**改动 3.5：ch05:203-243 幅度标度律子节软化**

子节标题改名 + 删除公式 eq:amplitude-scaling + 去掉 $B_0^{1.99}$ 断言 + 加诚实限制说明。

```
old:
\subsection{幅度标度律}
\label{subsec:amplitude-scaling}
在组合锁定为 srcX\_vibX、频率固定在 $f = \SI{440}{GHz}$ 的条件下，本文对 $B_0 = \SIrange{0.05}{2.0}{T}$ 范围内的 6 个幅度点逐一实施仿真，目标是量化 霍普夫子 运动速度随驱动幅度变化的标度关系。
new:
\subsection{幅度依赖性与阈值效应}
\label{subsec:amplitude-scaling}
在组合锁定为 srcX\_vibX、频率固定在 $f = \SI{440}{GHz}$ 的条件下，本文对 $B_0 = \SIrange{0.05}{2.0}{T}$ 范围内的 6 个幅度点逐一实施仿真，以研究 霍普夫子 运动速度随驱动幅度的依赖关系。
```

```
old (fig caption of fig:amplitude-scaling):
log-log 坐标下 霍普夫子 平均速度 $\bar{v}$ 对自旋波幅度 $B_0$ 的依赖关系。$B_0 \geq \SI{0.5}{T}$ 的数据段拟合给出 $\bar{v} \propto B_0^{1.99}$，$R^2 = 0.998$
new:
log-log 坐标下 霍普夫子 平均速度 $\bar{v}$ 对自旋波幅度 $B_0$ 的依赖关系。$B_0 \geq \SI{0.5}{T}$ 区段位移随幅度的增大呈增大趋势，$B_0 \leq \SI{0.1}{T}$ 时位移停留在噪声水平
```

```
old (公式段):
\cref{fig:amplitude-scaling}的结果清楚地显示，当幅度进入有效驱动窗口（$B_0 \geq \SI{0.5}{T}$）后，速度对幅度的依赖严格遵循幂律：
\begin{equation}
  \bar{v} = A \cdot B_0^n, \quad n = 1.99 \pm 0.01, \quad R^2 = 0.998
  \label{eq:amplitude-scaling}
\end{equation}
$n \approx 2$ 这一指数具有直观的物理解释：自旋波所携带的线性动量密度与其能量密度成正比，后者随 $B_0^2$ 增长；霍普夫子 达到稳态后，动量注入率恰好抵消耗散率，因而速度以 $v \propto B_0^2$ 的形式标度。该幂律关系与 斯格明子 在自旋波驱动下所遵循的 $v \propto B_0^2$ 标度完全一致\cite{ding2015motion}。

一旦幅度降至弱驱动区域（$B_0 \leq \SI{0.1}{T}$），霍普夫子 位移急剧衰减至噪声水平（$|\Delta r| < \SI{0.1}{nm}$），表征出明确的阈值效应。在 $B_0 = \SIrange{0.05}{0.1}{T}$ 条件下甚至观察到朝向激励源的微弱反向位移，该现象可能源于低幅度自旋波与 霍普夫子 势阱之间的弹性反弹效应。
new:
\cref{fig:amplitude-scaling}的结果揭示了两项定性特征。在有效驱动窗口（$B_0 \geq \SI{0.5}{T}$）内，霍普夫子 位移随自旋波幅度的增大呈增大趋势，趋势与自旋波通过动量转移驱动磁性拓扑结构的一般图像相符\cite{ding2015motion}。在弱驱动区域（$B_0 \leq \SI{0.1}{T}$），位移急剧衰减至噪声水平（$|\Delta r| < \SI{0.1}{nm}$），表征出明确的阈值效应；$B_0 = \SIrange{0.05}{0.1}{T}$ 条件下甚至观察到朝向激励源的微弱反向位移，该现象可能源于低幅度自旋波与 霍普夫子 势阱之间的弹性反弹效应。由于当前幅度扫描点数有限、所覆盖动态范围较窄，具体的标度律形式有待后续更细致的参数扫描加以确认。
```

---

**改动 3.6：ch05:316 二维 vs 三维对比（F 项散文版第一句）**
```
old:
具体而言，从幅度标度律来看，霍普夫子给出的 $v \propto B_0^{1.99}$ 幂律指数与斯格明子、斯格明子环体系中报道的 $v \propto B_0^2$ 高度吻合，说明自旋波通过动量转移驱动拓扑结构的基本物理机制在从二维推广至三维时并未发生本质变化。
new:
具体而言，从幅度依赖性来看，霍普夫子位移在有效驱动区段内随幅度的增大呈增大趋势，这一趋势与斯格明子、斯格明子环体系在自旋波驱动下的一般性响应相符，说明自旋波通过动量转移驱动拓扑结构的基本物理机制在从二维推广至三维时并未发生本质变化。
```

---

**改动 3.7：ch05:360 第 5 章本章小结 第 3 点（F 项散文版）**
```
old:
第三，幅度标度律：霍普夫子运动速度对自旋波幅度 $B_0$ 的依赖关系遵循 $v \propto B_0^{1.99}$（$R^2 = 0.998$）的幂律形式，与动量转移理论对二次标度律的预期一致。
new:
第三，幅度依赖性：霍普夫子位移在有效驱动区段（$B_0 \geq \SI{0.5}{T}$）内随自旋波幅度的增大呈增大趋势，弱驱动区段（$B_0 \leq \SI{0.1}{T}$）出现明确阈值效应；具体的标度律形式有待后续更细致的参数扫描加以确认。
```

---

**改动 3.8：ch06:23 概念器件模块 第 4 条（保留分点的那 4 项之一）**
```
old:
  \item 权重调节途径：将自旋波幅度 $B_0$ 映射为突触权重，$v \propto B_0^2$ 的标度律确保了从权重到输出之间存在唯一确定的函数关系。
new:
  \item 权重调节途径：将自旋波幅度 $B_0$ 映射为突触权重，位移随幅度增大而增大的特征确保了从权重到输出之间的稳定映射。
```

---

**改动 3.9：ch07 总结 第二大点（P2 之后的当前散文版）**
```
old:
速度对自旋波幅度呈 $v \propto B_0^{1.99}$ 的近似平方幂律关系（$R^2 = 0.998$），面内传播驱动下的拓扑 Hall 角 $\theta_{\text{H}} \approx \ang{87}$--$\ang{90}$ 在频率、幅度与激励几何三个维度上均稳健保持，从微磁学仿真层面为此前的解析理论预言\cite{saji2023magnonic}提供了独立的定量支撑。
new:
速度在有效驱动区段内随自旋波幅度的增大呈增大趋势，弱驱动段表现出明确阈值效应；面内传播驱动下的拓扑 Hall 角 $\theta_{\text{H}} \approx \ang{87}$--$\ang{90}$ 在频率、幅度与激励几何三个维度上均稳健保持，从微磁学仿真层面为此前的解析理论预言\cite{saji2023magnonic}提供了独立的支撑。
```

---

**依赖链**：
- 改动 3.6 / 3.7 / 3.9 依赖 F 项已执行（当前状态）→ 已满足
- 改动 3.9 还依赖 P1 改动 1.6（Saji 等人 → 此前的解析理论预言）——已包含在 P1 批 1 里

**验证**：
- [ ] 编译 0 undefined
- [ ] `grep "B_0\^\{?1\.99\|B_0\^\{?2\b"` 应无剩余（幂律平方表述全删）
- [ ] `grep "subsec:amplitude-scaling"` 标签在 ch06 里的引用仍有效
- [ ] `\cref{eq:amplitude-scaling}` 无残留引用

---

### P4. 致谢平衡（金老师减 / 其他人加）
**状态**：待讨论颗粒度

**待定**：
- 金老师部分减到几字
- "其他人"指谁（519 实验室 / 家人 / 同学）
- 各段落加多少字

---

### P5. 参考文献人名格式（不要全大写）
**状态**：待讨论颗粒度

**待定**：
- 诊断当前格式（是 ref.bib 里全大写还是 gbt7714 样式自动渲染大写）
- 决定改 bib 或改 bst

---

### P6. 引言用词（"理论渊源" 等）
**状态**：待讨论颗粒度

**待定**：
- 是否与 ch01 整章重写合并处理

---

## 冲突项（等 T1 完成后再做）

### P7. 冒号、破折号减少
**状态**：✅ 规则+示例已确认（2026-04-21），等 T1 完成后批量执行

**范围**：仅活跃章节正文 + 摘要段；**不动 \caption 内容**（T1 正在扩充 caption，待其完成）

**规模**：正文 ~131 处（冒号 79 + 破折号 52）+ 摘要冒号 4 处

**执行方式**：T1 完成后，逐章 grep 具体位置，按下方规则**逐处 Edit**（不使用 replace_all，避免误伤）。每章改完做一次 xelatex 快速编译，确认无断句异常。

---

#### 冒号替换规则

| # | 情形 | 替换 | 代表示例（file:line） |
|---|-----|------|----|
| **C1** | 说明引出（`名词：X 的说明`） | 改为句号拆句 | ch02:9 "包含若干独立的能量贡献项：" → "包含若干独立的能量贡献项。以下分别列出。" |
| **C2** | 判断动词后冒号（`X 表明：Y` / `X 显示：Y`） | 冒号改逗号 | ch05: "结果明确显示：面内振荡..." → "结果明确显示，面内振荡..." |
| **C3** | **方程/公式前冒号**（`X 如下：\begin{equation}`） | 改句号 `X 如下。\begin{equation}` | ch02:17 "交换能可写为：\begin{equation}" → "交换能可写作如下形式。\begin{equation}" |
| **C4** | 名词并列（`X：Y；Z：W` 定义式） | 改 `X，Y；Z，W` | ch06:23 器件模块 4 条（若保留分点）：`自旋波输入端：微波天线...` → `自旋波输入端即微波天线...` |
| **C5 保留** | LaTeX 语法（`\label{subsec:...}` / `\cite{a:b}`）；数学域内冒号；图 caption 内（T1 处理）；书名号/引号内 | 不动 | |

#### 破折号替换规则

| # | 情形 | 替换 | 代表示例 |
|---|-----|------|----|
| **D1** | 双端插入语 `X——Y——Z` | 改括号 `X（Y）Z` | ch05: "srcX 激活面内-轴向耦合通道、srcZ 直接作用于轴向通道——这两条独立路径使..." → "...轴向通道。这两条独立路径使..." |
| **D2** | 引出解释 `X——Y` | 改逗号或拆句 | ch04: "四组配置呈现高度一致的动力学特征：霍普夫子 质心均在前 $\sim\SI{1}{ns}$ 内沿环面轴向完成约 $\SI{4.75}{nm}$ 的一次性位移,随后被格点势能锁定——这一位移源于..." → "...锁定。这一位移源于..." |
| **D3** | 段末强调 `...X——Y 说明` | 改句号/分号 | ch05: "这是一个极端取值——它折射出..." → "这是一个极端取值，折射出..." |

---

#### 执行顺序建议（T1 完成后）

1. 先在 PENDING 写清每章预计改动数量，按 **ch01 → ch02 → ch03 → ch04 → ch05 → ch06 → ch07 → 摘要** 顺序
2. 每章用 Grep 列出全部 "：" 和 "——" 位置
3. 按规则判断每处属 C1/C2/C3/C4/D1/D2/D3 或 **保留**
4. 逐处 Edit；每章完成后编译一次，检查断句通顺
5. 摘要 4 处冒号最后处理

---

**验证**：
- [ ] 活跃章节 `grep -c "："` 和 `grep -c "——"` 数量相比执行前显著下降（目标：保留数 < 原数 30%，即 ~40 处以内）
- [ ] 编译 0 undefined / 0 overfull \vbox
- [ ] 多模态渲染抽 3-5 页目视确认断句通顺
- [ ] C5 豁免项（label/cite 等）语法未被破坏

### P8. ch01 整章重写（后摩尔/二维弊端/三维优势/对比图/高能初现/国内外动态/外场驱动/5.1 合并）
**状态**：大工程，单独立项

### P9. ch03 反铁磁/铁磁对比图插入
**状态**：等待

### P10. ch05 src/vib 中文化 + 表 5-1 概念写清
**状态**：等待

### P11. ch05 幅度标度律补数据或删
**状态**：等待

### P12. ch05 图 5-9 去留
**状态**：等待

### P13. ch06 神经形态示意图 + 补充内容
**状态**：等待

### P14. ch04 图 4-1 / 图 4-2（具体问题待用户说明）
**状态**：等待

---

## 执行日志

（T1 完成后按此文件逐项执行，记录时间与结果）
