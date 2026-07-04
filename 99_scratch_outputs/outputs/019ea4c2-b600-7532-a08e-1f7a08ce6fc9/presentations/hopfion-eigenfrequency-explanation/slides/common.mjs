const C = {
  ink: "#172033",
  blue: "#246BCE",
  red: "#C43D3D",
  green: "#2F7D60",
  gray: "#667085",
  paleBlue: "#EAF2FF",
  paleRed: "#FCECEC",
  paleGreen: "#EAF6F1",
  paleGray: "#F4F6F8",
  line: "#D9DEE7",
  white: "#FFFFFF",
};

const FONT = "Microsoft YaHei";

function rect(ctx, slide, x, y, w, h, fill, line = "#00000000", radius = "rect") {
  return ctx.addShape(slide, { x, y, w, h, geometry: radius, fill, line: ctx.line(line, line === "#00000000" ? 0 : 1) });
}

function txt(ctx, slide, text, x, y, w, h, size = 24, color = C.ink, bold = false, align = "left", valign = "top", fill = "#00000000") {
  return ctx.addText(slide, { text, x, y, w, h, fontSize: size, color, bold, typeface: FONT, align, valign, fill,
    insets: { left: 2, right: 2, top: 2, bottom: 2 } });
}

function base(ctx, slide, kicker, title, n, subtitle = "") {
  rect(ctx, slide, 0, 0, 1280, 720, C.white);
  rect(ctx, slide, 56, 45, 9, 20, C.blue);
  txt(ctx, slide, kicker, 76, 42, 300, 28, 16, C.blue, true, "left", "middle");
  txt(ctx, slide, title, 56, 82, 1160, 64, 38, C.ink, true);
  if (subtitle) txt(ctx, slide, subtitle, 58, 152, 1120, 34, 18, C.gray);
  rect(ctx, slide, 56, 680, 1168, 1, C.line);
  txt(ctx, slide, String(n).padStart(2, "0"), 1168, 688, 56, 20, 13, C.gray, false, "right");
}

function footer(ctx, slide, text) {
  txt(ctx, slide, text, 58, 688, 1000, 18, 11, C.gray);
}

function bulletList(ctx, slide, items, x, y, w, size = 23, gap = 49, color = C.ink) {
  items.forEach((item, i) => {
    rect(ctx, slide, x, y + i * gap + 8, 8, 8, C.blue, "#00000000", "ellipse");
    txt(ctx, slide, item, x + 22, y + i * gap, w - 22, gap - 4, size, color);
  });
}

function labelBox(ctx, slide, text, x, y, w, h, fill = C.paleBlue, color = C.ink, size = 22, bold = false) {
  rect(ctx, slide, x, y, w, h, fill, C.line);
  txt(ctx, slide, text, x + 14, y + 12, w - 28, h - 24, size, color, bold, "center", "middle");
}

function arrow(ctx, slide, x, y, w = 70, text = "→") {
  txt(ctx, slide, text, x, y, w, 48, 35, C.blue, true, "center", "middle");
}

function bar(ctx, slide, { x, y, w, value, max, color, label, valueLabel }) {
  txt(ctx, slide, label, x, y - 30, w, 26, 17, C.ink, true, "center");
  rect(ctx, slide, x, y, w, 280, C.paleGray);
  const h = Math.max(4, 280 * value / max);
  rect(ctx, slide, x, y + 280 - h, w, h, color);
  txt(ctx, slide, valueLabel, x - 10, y + 290, w + 20, 28, 16, color, true, "center");
}

function sourceLine(ctx, slide, text) {
  footer(ctx, slide, text);
}

export async function makeSlide(presentation, ctx, n) {
  const slide = presentation.slides.add();

  if (n === 1) {
    rect(ctx, slide, 0, 0, 1280, 720, C.white);
    rect(ctx, slide, 70, 86, 14, 475, C.blue);
    txt(ctx, slide, "Hopfion 固有频率研究全过程", 118, 105, 1040, 95, 51, C.ink, true);
    txt(ctx, slide, "我们做了什么、为什么这样做，以及为什么现在不能给出固有频率", 120, 222, 980, 80, 28, C.gray);
    labelBox(ctx, slide, "核心结论", 120, 355, 175, 54, C.paleBlue, C.blue, 21, true);
    txt(ctx, slide, "不是 Hopfion 没有固有频率，而是现有测量方法没有把它从背景振动中可靠地分离出来。", 120, 425, 980, 125, 32, C.ink, true);
    txt(ctx, slide, "研究时间：2026-06-08 至 2026-06-14", 120, 605, 600, 30, 17, C.gray);
    txt(ctx, slide, "01", 1160, 680, 60, 20, 13, C.gray, false, "right");
  }

  if (n === 2) {
    base(ctx, slide, "先回答", "我们真正想知道的是什么？", n);
    labelBox(ctx, slide, "问题 A", 90, 215, 300, 72, C.paleBlue, C.blue, 24, true);
    txt(ctx, slide, "哪些自旋波频率最容易推动 Hopfion？", 90, 310, 300, 100, 27, C.ink, true, "center", "middle");
    arrow(ctx, slide, 420, 310, 80);
    labelBox(ctx, slide, "频率扫描能回答", 510, 215, 300, 72, C.paleGreen, C.green, 24, true);
    txt(ctx, slide, "得到的是“驱动响应窗口”", 510, 310, 300, 100, 27, C.ink, true, "center", "middle");
    arrow(ctx, slide, 840, 310, 80, "≠");
    labelBox(ctx, slide, "问题 B", 930, 215, 260, 72, C.paleRed, C.red, 24, true);
    txt(ctx, slide, "Hopfion 自己最自然的振动频率是什么？", 930, 310, 260, 120, 27, C.ink, true, "center", "middle");
    txt(ctx, slide, "研究后期的全部工作，就是尝试从 A 走到 B。", 190, 525, 900, 54, 30, C.blue, true, "center");
  }

  if (n === 3) {
    base(ctx, slide, "基本概念", "“推动最有效”不等于“固有频率”", n);
    rect(ctx, slide, 70, 205, 530, 390, C.paleBlue, C.line);
    txt(ctx, slide, "连续自旋波驱动", 105, 235, 460, 45, 29, C.blue, true, "center");
    bulletList(ctx, slide, ["一直有人在推", "结果受频率、波长、传播方向影响", "还受源几何、散射和驱动力大小影响", "回答：哪个条件下运动最强"], 115, 310, 430, 22, 61);
    rect(ctx, slide, 680, 205, 530, 390, C.paleGreen, C.line);
    txt(ctx, slide, "固有频率实验", 715, 235, 460, 45, 29, C.green, true, "center");
    bulletList(ctx, slide, ["只轻轻敲一下，然后停止", "观察系统自己自由振动", "要求弱激励、线性标度、空间局域", "回答：Hopfion 自己怎样振动"], 725, 310, 430, 22, 61);
    txt(ctx, slide, "类比：一直推秋千看它荡多高，与轻敲钟后听钟声，是两种不同测量。", 130, 625, 1020, 34, 22, C.ink, true, "center");
  }

  if (n === 4) {
    base(ctx, slide, "研究起点", "频率扫描首先证明了“频率选择性”", n, "这些结果真实，但它们描述的是被驱动后的运动，不是自由振动谱。 ");
    const rows = [
      ["平面源 srcX", "100–200 GHz、1000 GHz", "强响应窗口"],
      ["平面源 srcZ", "1100 GHz", "最强反向位移"],
      ["平面源 srcZ", "100 GHz", "异常 +z 运动"],
      ["点源", "约 700/800 GHz", "相对平面源峰位降低"],
    ];
    const xs = [80, 360, 760]; const ws = [260, 380, 420];
    ["驱动方式", "观察到的频率", "当时可以成立的结论"].forEach((h, i) => labelBox(ctx, slide, h, xs[i], 215, ws[i], 52, C.ink, C.white, 19, true));
    rows.forEach((r, ri) => r.forEach((v, i) => labelBox(ctx, slide, v, xs[i], 270 + ri * 72, ws[i], 64, ri % 2 ? C.white : C.paleGray, C.ink, 18, i === 1)));
    txt(ctx, slide, "关键限制：位移大，可能是传播效率高、散射推力强或非线性形变，并不自动等于共振。", 105, 595, 1070, 50, 23, C.red, true, "center");
  }

  if (n === 5) {
    base(ctx, slide, "为什么升级", "一个驱动响应峰同时混合了很多因素", n);
    labelBox(ctx, slide, "输入频率 f", 80, 290, 180, 72, C.paleBlue, C.blue, 23, true);
    arrow(ctx, slide, 270, 300);
    const factors = ["传播是否顺畅", "波矢 k 与波长", "偏振和入射方向", "反射与散射", "Hopfion 内部形变"];
    factors.forEach((v, i) => labelBox(ctx, slide, v, 350 + (i % 3) * 265, 215 + Math.floor(i / 3) * 125, 225, 74, i < 3 ? C.paleGray : C.paleRed, i < 3 ? C.ink : C.red, 20, true));
    arrow(ctx, slide, 650, 480, 80, "↓");
    labelBox(ctx, slide, "最终位移或速度", 500, 545, 390, 70, C.paleGreen, C.green, 26, true);
    txt(ctx, slide, "所以不能从最终运动反推：这个频率一定是 Hopfion 固有频率。", 90, 625, 1100, 36, 23, C.red, true, "center");
  }

  if (n === 6) {
    base(ctx, slide, "文献启发", "可靠的本征模结论需要一条完整证据链", n);
    const stages = ["弱宽带脉冲", "停止驱动", "自由振荡 FFT", "场强线性检验", "空间局域检验", "与连续驱动对照"];
    stages.forEach((s, i) => {
      labelBox(ctx, slide, s, 55 + i * 200, 285, 165, 88, i < 3 ? C.paleBlue : C.paleGreen, i < 3 ? C.blue : C.green, 19, true);
      if (i < stages.length - 1) arrow(ctx, slide, 220 + i * 200, 305, 35);
    });
    txt(ctx, slide, "只有峰位、线性、空间位置三者相互支持，才能逐步接近“Hopfion 本征模”的说法。", 130, 450, 1020, 68, 28, C.ink, true, "center");
    txt(ctx, slide, "我们借鉴的是 skyrmion 与 Hopfion 文献的分析方法，而不是照搬它们的 GHz 数值。", 130, 545, 1020, 50, 21, C.gray, false, "center");
    sourceLine(ctx, slide, "方法参照：Mochizuki 2012；Kravchuk et al. 2018；Raftrey & Fischer 2021");
  }

  if (n === 7) {
    base(ctx, slide, "第一次测量", "我们用弱 sinc 脉冲做了自由振荡谱", n);
    const params = [
      ["脉冲强度", "5 mT"], ["覆盖频率", "至 2000 GHz"], ["仿真时长", "0.5 ns"],
      ["采样间隔", "0.05 ps"], ["激励方向", "Bx 与 Bz"], ["保存内容", "mx、my、mz、E_total"],
    ];
    params.forEach((p, i) => {
      const x = 85 + (i % 3) * 390; const y = 220 + Math.floor(i / 3) * 145;
      rect(ctx, slide, x, y, 340, 105, i < 3 ? C.paleBlue : C.paleGray, C.line);
      txt(ctx, slide, p[0], x + 20, y + 16, 300, 27, 17, C.gray, true);
      txt(ctx, slide, p[1], x + 20, y + 49, 300, i === 5 ? 50 : 40, i === 5 ? 23 : 27, C.ink, true);
    });
    labelBox(ctx, slide, "轻敲一下", 175, 540, 200, 66, C.paleBlue, C.blue, 24, true);
    arrow(ctx, slide, 400, 550);
    labelBox(ctx, slide, "停止外力", 500, 540, 200, 66, C.paleGray, C.ink, 24, true);
    arrow(ctx, slide, 725, 550);
    labelBox(ctx, slide, "听自由振动", 825, 540, 245, 66, C.paleGreen, C.green, 24, true);
    sourceLine(ctx, slide, "参数：hopfion_eigenmode_ringdown_20260608/PARAMETER_CONFIRMATION.md");
  }

  if (n === 8) {
    base(ctx, slide, "第一次结果", "自由振荡谱出现了一个醒目的 173.66 GHz 峰", n);
    txt(ctx, slide, "173.66", 95, 225, 390, 120, 76, C.blue, true, "center", "middle");
    txt(ctx, slide, "GHz", 205, 355, 170, 45, 30, C.blue, true, "center");
    txt(ctx, slide, "在 Bx 和 Bz 数据的 m_z、E_total 中都出现", 90, 410, 400, 72, 23, C.ink, true, "center");
    rect(ctx, slide, 560, 215, 620, 330, C.paleGray, C.line);
    txt(ctx, slide, "同时观察到的弱峰", 600, 245, 540, 38, 24, C.ink, true, "center");
    ["10.22 GHz", "38.82 GHz", "77.64 GHz", "126.67 GHz"].forEach((v, i) => labelBox(ctx, slide, v, 610 + (i % 2) * 270, 310 + Math.floor(i / 2) * 95, 235, 64, C.white, C.gray, 22, true));
    txt(ctx, slide, "但原有连续驱动窗口都没有在 ±10 GHz 内与这些峰对齐。", 180, 590, 920, 42, 24, C.red, true, "center");
    sourceLine(ctx, slide, "机器结果：ringdown_peak_candidates.csv；drive_vs_ringdown_comparison.csv");
  }

  if (n === 9) {
    base(ctx, slide, "关键转折", "两个异常让我们不能直接相信 173.66 GHz", n);
    rect(ctx, slide, 80, 215, 520, 350, C.paleRed, C.line);
    txt(ctx, slide, "异常 1：敲得更重，声音却没变大", 115, 245, 450, 60, 27, C.red, true, "center");
    txt(ctx, slide, "1 mT 与 5 mT 的 173.66 GHz 振幅几乎相同", 115, 335, 450, 80, 25, C.ink, true, "center", "middle");
    labelBox(ctx, slide, "振幅比 ≈ 0.9923", 185, 450, 310, 64, C.white, C.red, 24, true);
    rect(ctx, slide, 680, 215, 520, 350, C.paleRed, C.line);
    txt(ctx, slide, "异常 2：从不同方向敲，主峰仍一样", 715, 245, 450, 60, 27, C.red, true, "center");
    txt(ctx, slide, "Bx 与 Bz 激励下的 m_z 主峰功率非常接近", 715, 335, 450, 80, 25, C.ink, true, "center", "middle");
    labelBox(ctx, slide, "1.803e-10 vs 1.884e-10", 765, 450, 350, 64, C.white, C.red, 22, true);
    txt(ctx, slide, "这说明主峰可能由一个所有算例共有的变化引起，而不是由脉冲方向和强度决定。", 125, 605, 1030, 42, 23, C.ink, true, "center");
  }

  if (n === 10) {
    base(ctx, slide, "找到原因", "原来的“钟”在测量前被突然换了支架", n);
    labelBox(ctx, slide, "原始平衡态", 80, 245, 280, 88, C.paleBlue, C.blue, 24, true);
    txt(ctx, slide, "周期边界 PBC\nα = 0.2", 80, 355, 280, 80, 23, C.ink, true, "center", "middle");
    txt(ctx, slide, "突然切换 →", 365, 295, 145, 48, 23, C.blue, true, "center", "middle");
    labelBox(ctx, slide, "ringdown 条件", 505, 245, 300, 88, C.paleRed, C.red, 24, true);
    txt(ctx, slide, "开放边界 + 吸收层\nbulk α = 0.001", 505, 355, 300, 80, 23, C.ink, true, "center", "middle");
    arrow(ctx, slide, 830, 295);
    labelBox(ctx, slide, "即使不施加脉冲\n也可能自己振动", 930, 250, 270, 160, C.paleGreen, C.green, 25, true);
    txt(ctx, slide, "这叫“边界淬火”：边界条件突然改变，把原状态投影到新系统的一组自由振动上。", 130, 515, 1020, 85, 27, C.ink, true, "center", "middle");
  }

  if (n === 11) {
    base(ctx, slide, "C0 控制", "完全不敲，173.66 GHz 仍然同样响", n, "我们保持边界切换不变，只把脉冲设为 0 mT。 ");
    const vals = [1.5673, 1.5602, 1.5481];
    bar(ctx, slide, { x: 210, y: 250, w: 150, value: vals[0], max: 1.65, color: C.gray, label: "0 mT", valueLabel: "1.5673e-7" });
    bar(ctx, slide, { x: 535, y: 250, w: 150, value: vals[1], max: 1.65, color: C.blue, label: "1 mT", valueLabel: "1.5602e-7" });
    bar(ctx, slide, { x: 860, y: 250, w: 150, value: vals[2], max: 1.65, color: C.red, label: "5 mT", valueLabel: "1.5481e-7" });
    txt(ctx, slide, "三根柱子几乎一样高：主峰不是随着敲击增强而增强。", 210, 610, 800, 42, 24, C.red, true, "center");
    sourceLine(ctx, slide, "C0：A(0 mT)/A(1 mT)=1.0046；机器判定 quench_dominated=true");
  }

  if (n === 12) {
    base(ctx, slide, "C1 修正", "先让 Hopfion 在新边界下真正安静下来", n);
    const stages = [
      ["载入原状态", "来自 PBC 平衡态"],
      ["开放边界 Relax", "不再突然开始测量"],
      ["检查拓扑保持", "确认没有在准备阶段损坏"],
    ];
    stages.forEach((s, i) => {
      labelBox(ctx, slide, s[0], 85 + i * 400, 245, 300, 72, i === 1 ? C.paleGreen : C.paleBlue, i === 1 ? C.green : C.blue, 24, true);
      txt(ctx, slide, s[1], 100 + i * 400, 340, 270, 70, 21, C.ink, false, "center", "middle");
      if (i < 2) arrow(ctx, slide, 390 + i * 400, 265, 80);
    });
    labelBox(ctx, slide, "数值 Hopf 指数相对变化 ≈ 2.51×10⁻⁹", 310, 480, 660, 80, C.paleGreen, C.green, 28, true);
    txt(ctx, slide, "含义：新的共同初态已经准备好，后面可以公平比较 0、1、2、5 mT。", 175, 590, 930, 42, 23, C.ink, true, "center");
  }

  if (n === 13) {
    base(ctx, slide, "C2 方法", "有脉冲结果必须先减去零场背景", n);
    labelBox(ctx, slide, "m(t, B)", 100, 250, 230, 88, C.paleBlue, C.blue, 30, true);
    txt(ctx, slide, "有脉冲轨迹", 100, 350, 230, 35, 20, C.gray, false, "center");
    txt(ctx, slide, "−", 365, 268, 80, 60, 45, C.red, true, "center", "middle");
    labelBox(ctx, slide, "m(t, 0)", 470, 250, 230, 88, C.paleGray, C.ink, 30, true);
    txt(ctx, slide, "没有脉冲的背景", 470, 350, 230, 35, 20, C.gray, false, "center");
    txt(ctx, slide, "=", 735, 268, 80, 60, 45, C.green, true, "center", "middle");
    labelBox(ctx, slide, "δm(t, B)", 840, 250, 280, 88, C.paleGreen, C.green, 30, true);
    txt(ctx, slide, "估计由脉冲引起的部分", 840, 350, 280, 35, 20, C.gray, false, "center");
    arrow(ctx, slide, 585, 430, 100, "↓ FFT");
    labelBox(ctx, slide, "再检查：峰位是否一致？功率是否随 B² 增长？信号是否明显高于背景？", 190, 510, 900, 92, C.white, C.ink, 24, true);
  }

  if (n === 14) {
    base(ctx, slide, "C2 结果", "79.14 GHz 有峰，但它没有随场强正常增强", n);
    bar(ctx, slide, { x: 120, y: 245, w: 145, value: 1.3448, max: 1.5, color: C.blue, label: "1 mT", valueLabel: "1.345e-9" });
    bar(ctx, slide, { x: 340, y: 245, w: 145, value: 1.1798, max: 1.5, color: C.green, label: "2 mT", valueLabel: "1.180e-9" });
    bar(ctx, slide, { x: 560, y: 245, w: 145, value: 1.2048, max: 1.5, color: C.red, label: "5 mT", valueLabel: "1.205e-9" });
    rect(ctx, slide, 790, 220, 405, 355, C.paleGray, C.line);
    txt(ctx, slide, "预先规定的判据", 825, 245, 335, 36, 24, C.ink, true, "center");
    txt(ctx, slide, "峰位一致：通过\n功率指数接近 2：失败（−0.0635）\n拟合 R² ≥ 0.9：失败（0.5323）\nSNR ≥ 3：失败（2.64）", 825, 305, 335, 210, 22, C.ink, false, "left", "top");
    labelBox(ctx, slide, "机器结论：passed = false", 825, 520, 335, 48, C.paleRed, C.red, 18, true);
    sourceLine(ctx, slide, "候选峰约 79.14 GHz；峰位离散 0.282 GHz，但线性标度和 SNR 不通过");
  }

  if (n === 15) {
    base(ctx, slide, "为什么不能定论", "现在缺少四块关键证据", n);
    const items = [
      ["1. 线性标度", "功率没有随 B² 增长", C.paleRed, C.red],
      ["2. 信噪比", "候选信号没有明显高出背景", C.paleRed, C.red],
      ["3. 空间归属", "不知道振动来自 Hopfion、边界还是体自旋波", C.paleGray, C.ink],
      ["4. 驱动对照", "连续驱动强峰与可信自由峰没有对齐", C.paleGray, C.ink],
    ];
    items.forEach((it, i) => {
      const x = 80 + (i % 2) * 580; const y = 210 + Math.floor(i / 2) * 190;
      rect(ctx, slide, x, y, 540, 150, it[2], C.line);
      txt(ctx, slide, it[0], x + 24, y + 22, 490, 34, 25, it[3], true);
      txt(ctx, slide, it[1], x + 24, y + 72, 490, 60, 21, C.ink);
    });
    txt(ctx, slide, "所以我们只能说“看到了候选峰”，不能说“确定了 Hopfion 固有频率”。", 125, 610, 1030, 42, 26, C.red, true, "center");
  }

  if (n === 16) {
    base(ctx, slide, "研究纪律", "为什么没有继续跑昂贵的空间模态图？", n);
    labelBox(ctx, slide, "基础线性门", 100, 260, 250, 82, C.paleBlue, C.blue, 25, true);
    arrow(ctx, slide, 380, 275);
    labelBox(ctx, slide, "通过？", 490, 260, 180, 82, C.paleGray, C.ink, 27, true);
    arrow(ctx, slide, 700, 275);
    labelBox(ctx, slide, "否", 805, 260, 120, 82, C.paleRed, C.red, 30, true);
    arrow(ctx, slide, 950, 275);
    rect(ctx, slide, 1040, 245, 180, 112, C.paleRed, C.line);
    txt(ctx, slide, "停止 C3 / stage2", 1054, 257, 152, 84, 22, C.red, true, "center", "middle");
    bulletList(ctx, slide, ["未运行 1 ns 线宽", "未运行逐胞空间 FFT", "未运行圆偏选择性", "未运行 CW 精扫与 k 谱"], 220, 430, 820, 22, 48);
    txt(ctx, slide, "原因：不能先看到漂亮图，再倒过来替一个基础检验失败的峰寻找解释。", 150, 620, 980, 38, 24, C.ink, true, "center");
  }

  if (n === 17) {
    base(ctx, slide, "最终认识", "这次研究得到了什么，而不是“什么都没得到”", n);
    rect(ctx, slide, 65, 200, 555, 390, C.paleGreen, C.line);
    txt(ctx, slide, "已经确认", 100, 225, 485, 42, 27, C.green, true, "center");
    bulletList(ctx, slide, ["自旋波驱动具有频率选择性", "173.66 GHz 主要受边界淬火激发", "79.14 GHz 未通过线性门", "原有 100/200/1000/1100 GHz 是响应窗口"], 115, 300, 450, 21, 59);
    rect(ctx, slide, 660, 200, 555, 390, C.paleBlue, C.line);
    txt(ctx, slide, "没有证明", 695, 225, 485, 42, 27, C.blue, true, "center");
    bulletList(ctx, slide, ["没有证明 Hopfion 不存在固有频率", "没有证明 173.66 GHz 是 Hopfion 本征模", "没有证明 79.14 GHz 是 Hopfion 本征模", "没有把强位移峰包装成共振峰"], 710, 300, 450, 21, 59);
    txt(ctx, slide, "下一步应转向可直接检验的理论：magnon 动量传递、广义 Thiele 张量、平移—形变耦合与坍塌阈值。", 95, 615, 1090, 60, 24, C.ink, true, "center", "middle");
  }

  return slide;
}
