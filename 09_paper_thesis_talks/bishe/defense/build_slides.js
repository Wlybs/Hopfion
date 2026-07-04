// =============================================================
//  毕业答辩 PPT 生成脚本
//  题目：磁性拓扑结构的动力学调控及其在神经形态计算中的应用
//  作者：吴佳乐  指导教师：金蒙豪
//  生成：node build_slides.js -> defense_slides.pptx
// =============================================================
const pptxgen = require('pptxgenjs');
const path = require('path');

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';            // 13.333 x 7.5 inch
pres.title  = '磁性拓扑结构的动力学调控及其在神经形态计算中的应用';
pres.author = '吴佳乐';
pres.company = '杭州电子科技大学';

// -------- Color Palette: Ocean Gradient (deep blue / teal / midnight) --
const C = {
  midnight : '0D1B2A',    // 深夜蓝 (主深底)
  navy     : '1B2A4E',    // 海军蓝
  deep     : '065A82',    // 深海蓝 (强调)
  teal     : '1C7293',    // 青色
  seafoam  : '49A6B8',    // 浅青
  ice      : 'CADCFC',    // 冰蓝
  cream    : 'F5F8FB',    // 近白底
  white    : 'FFFFFF',
  charcoal : '2B3A55',    // 文字深
  muted    : '6B7E97',    // 次级文字
  amber    : 'F2A65A',    // 暖色强调 (用于数据高亮)
  coral    : 'E5736A'     // 错位互补
};

// -------- Font Pair --------------------------------------------------
const F = {
  head: 'Georgia',
  cn  : 'SimHei',         // 中文标题黑体
  body: 'Calibri',
  cnBody: 'SimSun'        // 中文正文宋体
};

// -------- Figure paths -----------------------------------------------
const FIG = path.resolve(__dirname, '../thesis_v2/figures');
const F_ = (name) => path.join(FIG, name);

// =============================================================
//  Helper: 通用元素
// =============================================================
function darkBackground(slide) {
  slide.background = { color: C.midnight };
  // 左上几何装饰
  slide.addShape(pres.ShapeType.rect, {
    x:0, y:0, w:13.333, h:0.04, fill:{ color:C.teal }, line:{ color:C.teal }
  });
  slide.addShape(pres.ShapeType.rect, {
    x:0, y:7.46, w:13.333, h:0.04, fill:{ color:C.teal }, line:{ color:C.teal }
  });
}

function lightBackground(slide) {
  slide.background = { color: C.cream };
  // 顶部 teal 标志条 (左侧短)
  slide.addShape(pres.ShapeType.rect, {
    x:0.5, y:0.55, w:0.12, h:0.7, fill:{ color:C.teal }, line:{ color:C.teal }
  });
}

// 浅色版幻灯片标题: 左侧细青色竖条 + 标题
function lightTitle(slide, title, subtitle) {
  slide.addText(title, {
    x:0.75, y:0.45, w:11.5, h:0.55,
    fontFace: F.cn, fontSize: 30, bold:true, color: C.charcoal,
    align:'left', valign:'middle', margin:0
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x:0.75, y:1.02, w:11.5, h:0.32,
      fontFace: F.body, fontSize: 13, italic:true, color: C.muted,
      align:'left', valign:'middle', margin:0
    });
  }
  // 标题下方点缀: 短 teal 横线
  slide.addShape(pres.ShapeType.rect, {
    x:0.75, y: subtitle?1.42:1.10, w:0.5, h:0.04,
    fill:{ color:C.teal }, line:{ color:C.teal }
  });
}

function pageNum(slide, n, total) {
  slide.addText(`${n} / ${total}`, {
    x:12.0, y:7.05, w:1.0, h:0.3,
    fontFace: F.body, fontSize: 9, color: C.muted, align:'right'
  });
  slide.addText('杭州电子科技大学  本科毕业答辩', {
    x:0.5, y:7.05, w:8, h:0.3,
    fontFace: F.cnBody, fontSize: 9, color: C.muted, align:'left'
  });
}

const TOTAL = 24;

// =============================================================
//  Helper: 章节封面卡（仿开题报告风格）
//  深底 + Garamond '0X.' 大字 + 章节名右下 + 三色弧线装饰
// =============================================================
function slideChapterCover(num, titleZh, accentColor) {
  const s = pres.addSlide();
  s.background = { color: C.cream };

  // 中央深底大卡
  const cx = 0.7, cy = 0.7, cw = 11.93, ch = 6.1;
  s.addShape(pres.ShapeType.rect, {
    x:cx, y:cy, w:cw, h:ch,
    fill:{ color: C.midnight }, line:{ type:'none' }
  });

  // "0X." 大字（白色 Garamond 衬线）
  s.addText(num + '.', {
    x:cx+0.45, y:cy+0.55, w:3.5, h:2.0,
    fontFace: 'Garamond', fontSize: 110, bold:true, color: C.white,
    align:'left', valign:'middle'
  });

  // 顶部白色细横线
  s.addShape(pres.ShapeType.rect, {
    x:cx+3.5, y:cy+1.5, w:cw-4.4, h:0.04,
    fill:{ color: C.white }, line:{ color: C.white }
  });

  // 右上三色圆点
  const dotX = cx+cw-1.05, dotY = cy+1.30;
  for (let i = 0; i < 3; i++) {
    s.addShape(pres.ShapeType.ellipse, {
      x:dotX+i*0.30, y:dotY, w:0.22, h:0.22,
      fill:{ color: accentColor }, line:{ color: accentColor }
    });
  }

  // 章节标题（右下，白色黑体）
  s.addText(titleZh, {
    x:cx+cw-7.5, y:cy+ch-1.5, w:7.0, h:1.0,
    fontFace: F.cn, fontSize: 36, bold:true, color: C.white,
    align:'right', valign:'middle'
  });

  // 装饰弧线：右上角三个同心圆环（部分露出卡外）
  for (let i = 0; i < 3; i++) {
    const r = 4.0 + i*0.6;
    s.addShape(pres.ShapeType.ellipse, {
      x:cx+cw-r/2, y:cy-r/2-1.0, w:r, h:r,
      fill:{ type:'none' }, line:{ color: accentColor, width:0.75 }
    });
  }
  // 左下角同心圆环
  for (let i = 0; i < 3; i++) {
    const r = 3.5 + i*0.5;
    s.addShape(pres.ShapeType.ellipse, {
      x:cx-r/2-1.0, y:cy+ch-r/2+0.5, w:r, h:r,
      fill:{ type:'none' }, line:{ color: accentColor, width:0.75 }
    });
  }
}

// =============================================================
//  Slide 1  封面
// =============================================================
function slideCover() {
  const s = pres.addSlide();
  darkBackground(s);

  // 上方副标题（学校）
  s.addText('杭州电子科技大学  本科毕业设计（论文）答辩', {
    x:0.5, y:0.7, w:12.3, h:0.4,
    fontFace: F.cnBody, fontSize: 14, color: C.ice,
    align:'center', valign:'middle'
  });

  // 装饰：中间 horizontal divider with diamond
  s.addShape(pres.ShapeType.line, {
    x:5.5, y:1.45, w:2.3, h:0,
    line:{ color: C.seafoam, width:1 }
  });

  // 主标题（中文）
  s.addText('磁性拓扑结构的动力学调控\n及其在神经形态计算中的应用', {
    x:0.5, y:1.85, w:12.3, h:1.8,
    fontFace: F.cn, fontSize: 44, bold:true, color: C.white,
    align:'center', valign:'middle', lineSpacingMultiple:1.15
  });

  // 副标题（英文）
  s.addText('Dynamical Control of Magnetic Topological Structures\nfor Neuromorphic Computing Applications', {
    x:0.5, y:3.85, w:12.3, h:0.8,
    fontFace: F.head, fontSize: 16, italic:true, color: C.ice,
    align:'center', valign:'middle', lineSpacingMultiple:1.2
  });

  // 中部装饰长条
  s.addShape(pres.ShapeType.rect, {
    x:5.0, y:4.95, w:3.3, h:0.04,
    fill:{ color: C.teal }, line:{ color:C.teal }
  });

  // 答辩信息卡 (居中)
  const infoY = 5.3;
  const cardX = 3.5, cardW = 6.3, cardH = 1.55;
  s.addShape(pres.ShapeType.roundRect, {
    x:cardX, y:infoY, w:cardW, h:cardH, rectRadius:0.08,
    fill:{ color: C.navy }, line:{ color: C.teal, width:1 }
  });
  // 信息行
  const info = [
    { l:'答辩人',    v:'吴佳乐'              },
    { l:'学　号',    v:'22040338'           },
    { l:'指导教师',  v:'金蒙豪  讲师'        },
    { l:'专　业',    v:'电子科学与技术'      }
  ];
  info.forEach((row, i) => {
    const yy = infoY + 0.12 + i*0.32;
    s.addText(row.l + '：', {
      x:cardX+0.6, y:yy, w:1.6, h:0.3,
      fontFace: F.cnBody, fontSize: 13, color: C.ice, align:'right'
    });
    s.addText(row.v, {
      x:cardX+2.2, y:yy, w:3.6, h:0.3,
      fontFace: F.cnBody, fontSize: 13, bold:true, color: C.white, align:'left'
    });
  });

  // 底部日期
  s.addText('2026 年 5 月', {
    x:0.5, y:6.95, w:12.3, h:0.4,
    fontFace: F.body, fontSize: 12, color: C.muted, align:'center'
  });
}

// =============================================================
//  Slide 2  目录 / 提纲
// =============================================================
function slideAgenda() {
  const s = pres.addSlide();
  darkBackground(s);

  s.addText('CONTENTS', {
    x:0.5, y:0.55, w:12.3, h:0.5,
    fontFace: F.head, fontSize: 18, color: C.seafoam, align:'center', characterSpacing:8
  });
  s.addText('答辩提纲', {
    x:0.5, y:1.05, w:12.3, h:0.7,
    fontFace: F.cn, fontSize: 36, bold:true, color: C.white, align:'center'
  });
  s.addShape(pres.ShapeType.rect, {
    x:6.16, y:1.85, w:1.0, h:0.04, fill:{ color:C.teal }, line:{ color:C.teal }
  });

  const items = [
    { n:'01', t:'研究背景与意义',         d:'拓扑磁结构 · Hopfion · 信息载体' },
    { n:'02', t:'理论基础与构造方法',     d:'LLG 方程 · Hopf 指数 · 解析初始态' },
    { n:'03', t:'拓扑稳定性研究',         d:'阻挫交换体系 · 稳态尺寸 · Ku_c' },
    { n:'04', t:'磁振子驱动动力学',       d:'方向选择 · 频率响应 · 双向输运' },
    { n:'05', t:'神经形态计算应用',       d:'LIF 类比 · 双向可逆输运' }
  ];

  // 五个卡片：上下两行 (3+2) 居中
  const cardW = 3.95, cardH = 2.0;
  const gap = 0.25;
  const layout = [
    {row:0, col:0}, {row:0, col:1}, {row:0, col:2},
    {row:1, col:0}, {row:1, col:1}
  ];
  const totalW3 = cardW*3 + gap*2;
  const startX3 = (13.333 - totalW3)/2;
  const totalW2 = cardW*2 + gap*1;
  const startX2 = (13.333 - totalW2)/2;
  const baseY = 2.55;

  items.forEach((it, i) => {
    const {row, col} = layout[i];
    const x = (row===0 ? startX3 : startX2) + col*(cardW+gap);
    const y = baseY + row*(cardH+0.25);

    s.addShape(pres.ShapeType.roundRect, {
      x, y, w:cardW, h:cardH, rectRadius:0.06,
      fill:{ color: C.navy }, line:{ color: C.deep, width:0.75 }
    });
    // 序号
    s.addText(it.n, {
      x:x+0.25, y:y+0.2, w:1.0, h:0.65,
      fontFace: F.head, fontSize: 36, bold:true, color: C.seafoam,
      align:'left', valign:'top'
    });
    // 标题
    s.addText(it.t, {
      x:x+0.25, y:y+0.85, w:cardW-0.5, h:0.5,
      fontFace: F.cn, fontSize: 17, bold:true, color: C.white,
      align:'left', valign:'middle'
    });
    // 简介
    s.addText(it.d, {
      x:x+0.25, y:y+1.35, w:cardW-0.5, h:0.55,
      fontFace: F.cnBody, fontSize: 11, color: C.ice,
      align:'left', valign:'top', lineSpacingMultiple:1.25
    });
  });

  pageNum(s, 2, TOTAL);
}

// =============================================================
//  Slide 3  研究背景
// =============================================================
function slideBackground() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '研究背景：拓扑磁结构与计算瓶颈', 'From Computing Bottleneck to Topological Solutions');

  // 4 要点 2x2 布局
  const items = [
    { n:'1', t:'后摩尔时代的计算瓶颈',
      d:'冯诺依曼架构存储/处理分离，数据搬运导致高延迟与能耗；晶体管尺寸逼近物理极限。',
      c:C.deep },
    { n:'2', t:'拓扑磁结构是新载体',
      d:'非易失 · 低驱动能耗 · 易与半导体集成；可作存算一体 / 神经形态计算的物理基础。',
      c:C.teal },
    { n:'3', t:'二维 Skyrmion 的局限',
      d:'面内几何限制信息密度；运动轨迹束缚于薄膜平面；对边界与各向异性敏感。',
      c:C.seafoam },
    { n:'4', t:'三维 Hopfion 的突破',
      d:'拓扑保护抗扰动 · 引入轴向自由度 · 三维动力学行为更丰富；高密度存储与类脑计算潜力。',
      c:C.amber }
  ];
  const cw = 6.0, ch = 2.45, gap = 0.3;
  const totalW = cw*2 + gap;
  const startX = (13.333 - totalW) / 2;
  const baseY = 1.85;
  items.forEach((it, i) => {
    const r = Math.floor(i/2), c = i%2;
    const x = startX + c*(cw+gap);
    const y = baseY + r*(ch+gap);
    s.addShape(pres.ShapeType.roundRect, {
      x, y, w:cw, h:ch, rectRadius:0.08,
      fill:{ color:C.white }, line:{ color: C.ice, width:0.5 }
    });
    s.addShape(pres.ShapeType.rect, {
      x, y, w:0.16, h:ch,
      fill:{ color: it.c }, line:{ color: it.c }
    });
    s.addText(it.n + '.', {
      x:x+0.3, y:y+0.2, w:0.85, h:0.7,
      fontFace: F.head, fontSize: 32, bold:true, color: it.c, align:'left', valign:'middle'
    });
    s.addText(it.t, {
      x:x+1.3, y:y+0.22, w:cw-1.4, h:0.5,
      fontFace: F.cn, fontSize: 18, bold:true, color: C.charcoal, align:'left', valign:'middle'
    });
    s.addText(it.d, {
      x:x+1.3, y:y+0.85, w:cw-1.4, h:1.45,
      fontFace: F.cnBody, fontSize: 13, color: C.muted, align:'left', valign:'top', lineSpacingMultiple:1.4
    });
  });

  pageNum(s, 5, TOTAL);
}

// =============================================================
//  Slide 4  Hopfion 是什么（基础概念）
// =============================================================
function slideHopfionIntro() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, 'Hopfion 是什么？', 'From 2D Skyrmion to 3D Knotted Texture');

  // 左：fig1-2 单图（Skyrmion 管 → Hopfion 几何过程，论文 §1.1 实际图）
  s.addShape(pres.ShapeType.roundRect, {
    x:0.5, y:1.85, w:5.5, h:5.0, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('fig1-2_skyrmion_to_hopfion.png'),
    x:0.75, y:2.0, w:5.0, h:3.54, sizing:{ type:'contain', w:5.0, h:3.54 } });
  s.addText('Skyrmion 管沿轴向扭转 360° 头尾相接 → Hopfion（论文 fig1-2）', {
    x:0.5, y:5.65, w:5.5, h:0.4,
    fontFace: F.cnBody, fontSize: 11, italic:true, color: C.muted, align:'center', lineSpacingMultiple:1.3
  });

  // 右：3 编号要点
  const items = [
    { n:'1', t:'三维拓扑磁结构',
      d:'由 Skyrmion 管沿轴向扭转 360° 头尾相接形成甜甜圈状磁纽结。',
      c:C.deep },
    { n:'2', t:'拓扑荷 Q_H',
      d:'由缠绕数 (p, q) 决定的整数拓扑荷：Q_H = p × q；本研究覆盖 Q_H = 1, 2, 4。',
      c:C.teal },
    { n:'3', t:'几何参数 (R, r)',
      d:'大半径 R 为环面中心轴到管心距离，管半径 r 为管截面半径。',
      c:C.seafoam }
  ];
  const rx = 6.2, rw = 6.63, rh = 1.65, rgap = 0.20;
  items.forEach((it, i) => {
    const yy = 1.85 + i*(rh+rgap);
    s.addShape(pres.ShapeType.roundRect, {
      x:rx, y:yy, w:rw, h:rh, rectRadius:0.06,
      fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
    });
    s.addShape(pres.ShapeType.rect, {
      x:rx, y:yy, w:0.16, h:rh,
      fill:{ color: it.c }, line:{ color: it.c }
    });
    s.addText(it.n + '.', {
      x:rx+0.3, y:yy+0.15, w:0.85, h:0.65,
      fontFace: F.head, fontSize: 28, bold:true, color: it.c, align:'left', valign:'middle'
    });
    s.addText(it.t, {
      x:rx+1.2, y:yy+0.18, w:rw-1.3, h:0.45,
      fontFace: F.cn, fontSize: 17, bold:true, color: C.charcoal, align:'left', valign:'middle'
    });
    s.addText(it.d, {
      x:rx+1.2, y:yy+0.65, w:rw-1.3, h:rh-0.75,
      fontFace: F.cnBody, fontSize: 13, color: C.muted, align:'left', valign:'top', lineSpacingMultiple:1.35
    });
  });

  pageNum(s, 4, TOTAL);
}

// =============================================================
//  Slide 5  研究意义
// =============================================================
function slideSignificance() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '研究意义：从拓扑物理到类脑计算', 'From Topological Physics to Brain-inspired Computing');

  // 左：应用拼图（神经形态硬件应用场景）
  s.addShape(pres.ShapeType.roundRect, {
    x:0.5, y:1.85, w:5.8, h:5.0, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('neuromorphic_app_collage.png'),
    x:0.7, y:2.0, w:5.4, h:4.66, sizing:{ type:'contain', w:5.4, h:4.66 } });
  s.addText('类脑计算应用场景：脑机接口 · 医疗 · 自动驾驶 · 决策（图源：综述文献）', {
    x:0.5, y:6.85, w:5.8, h:0.3,
    fontFace: F.cnBody, fontSize: 10, italic:true, color: C.muted, align:'center'
  });

  // 右：3 项纵排卡（科学价值 / 技术潜力 / 研究目标）
  const cols = [
    { t:'科学价值', i:'⊕', c:C.deep, items:[
      '揭示三维拓扑磁结构稳定性边界',
      '刻画磁振子-Hopfion 耦合机制'
    ]},
    { t:'技术潜力', i:'◎', c:C.teal, items:[
      '高密度三维磁存储 · 低功耗自旋波驱动',
      '非易失神经形态硬件载体'
    ]},
    { t:'研究目标', i:'◆', c:C.seafoam, items:[
      '建立 Hopfion 稳定性判据',
      '揭示自旋波驱动规律 · 探索类脑器件原型'
    ]}
  ];
  const rx = 6.5, rw = 6.33, rh = 1.55, rgap = 0.13;
  cols.forEach((cc, i) => {
    const yy = 1.85 + i*(rh+rgap);
    s.addShape(pres.ShapeType.roundRect, {
      x:rx, y:yy, w:rw, h:rh, rectRadius:0.08,
      fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
    });
    s.addShape(pres.ShapeType.rect, {
      x:rx, y:yy, w:0.18, h:rh,
      fill:{ color: cc.c }, line:{ color: cc.c }
    });
    // 图标
    s.addText(cc.i, {
      x:rx+0.4, y:yy+0.2, w:0.85, h:1.15,
      fontFace: F.head, fontSize: 38, bold:true, color: cc.c, align:'center', valign:'middle'
    });
    // 标题
    s.addText(cc.t, {
      x:rx+1.4, y:yy+0.18, w:rw-1.5, h:0.42,
      fontFace: F.cn, fontSize: 17, bold:true, color: C.charcoal, align:'left', valign:'middle'
    });
    // 列表
    cc.items.forEach((it, j) => {
      s.addText('• ' + it, {
        x:rx+1.4, y:yy+0.62+j*0.42, w:rw-1.55, h:0.40,
        fontFace: F.cnBody, fontSize: 12, color: C.muted, align:'left', valign:'top', lineSpacingMultiple:1.25
      });
    });
  });

  // 底部：链接箭头标语
  s.addText('稳定性 ⟶ 动力学', {
    x:6.5, y:6.55, w:6.33, h:0.4,
    fontFace: F.cn, fontSize: 16, bold:true, color: C.deep,
    align:'center', valign:'middle', characterSpacing:4
  });

  pageNum(s, 6, TOTAL);
}

// =============================================================
//  Slide 5  国内外研究现状
// =============================================================
function slideLiterature() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '国内外研究现状：发现 · 稳定 · 动力学', 'State-of-the-Art Review · Discovery → Stability → Dynamics');

  const EXTRACT = path.resolve(__dirname, 'extracted_figures');
  const cards = [
    {
      idx: '01', tag: '实验发现', tagEn: 'Experimental Discovery', col: C.deep,
      img: 'lit_overfocus.png',
      desc: '2023 年在立方手性磁体 (B20-FeGe) 中通过 Lorentz TEM 过焦像首次直接观测到 Hopfion 环嵌套结构，证实其在真实材料中的存在与稳定性。',
      ref: 'Zheng et al., Nature 623, 718 (2023)'
    },
    {
      idx: '02', tag: '拓扑稳定', tagEn: 'Topological Stability', col: C.teal,
      img: 'lit_3d_rainbow.png',
      desc: '解析推导与微磁仿真证实 Hopfion 在手性磁体 / 阻挫铁磁中均可形成拓扑保护稳态；不同方向 preimage 闭环相互缠绕成 Hopf-link。',
      ref: 'Sutcliffe 2018 · Sallermann 2023'
    },
    {
      idx: '03', tag: '动力学调控', tagEn: 'Dynamic Control', col: C.amber,
      img: 'lit_sphere_arrow.png',
      desc: 'STT 电流驱动 Bloch / Néel Hopfion 沿轴无 Hall 偏转直线运动；SOT 调控与拓扑变换近年取得突破；铁磁体系下自旋波驱动仍为开放问题。',
      ref: 'Wang 2019 · Yu 2023'
    }
  ];

  const cw = 3.85, ch = 4.55, gap = 0.30;
  const totalW = cw*3 + gap*2;
  const startX = (13.333 - totalW) / 2;
  const baseY = 1.55;

  cards.forEach((card, i) => {
    const x = startX + i*(cw+gap);

    // 卡片底
    s.addShape(pres.ShapeType.roundRect, {
      x, y:baseY, w:cw, h:ch, rectRadius:0.08,
      fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
    });

    // 顶部色条 (含 idx + 标签)
    s.addShape(pres.ShapeType.rect, {
      x, y:baseY, w:cw, h:0.5,
      fill:{ color: card.col }, line:{ type:'none' }
    });
    s.addText(card.idx, {
      x:x+0.18, y:baseY, w:0.6, h:0.5,
      fontFace: F.head, fontSize: 18, bold:true, color: C.white, align:'left', valign:'middle'
    });
    s.addText(card.tag, {
      x:x+0.78, y:baseY, w:cw-0.85, h:0.5,
      fontFace: F.cn, fontSize: 16, bold:true, color: C.white, align:'left', valign:'middle'
    });

    // 图片 (居中, 等比缩放)
    const imgW = cw - 0.5, imgH = 2.55;
    s.addImage({
      path: path.join(EXTRACT, card.img),
      x: x + (cw - imgW)/2, y: baseY + 0.62, w: imgW, h: imgH,
      sizing: { type: 'contain', w: imgW, h: imgH }
    });

    // 英文小标签
    s.addText(card.tagEn, {
      x, y: baseY + 3.20, w: cw, h: 0.26,
      fontFace: F.head, fontSize: 11, italic:true, color: card.col, align:'center'
    });

    // 描述
    s.addText(card.desc, {
      x:x+0.22, y: baseY + 3.48, w: cw-0.44, h: 0.72,
      fontFace: F.cnBody, fontSize: 12, color: C.charcoal,
      align:'left', valign:'top', lineSpacingMultiple:1.20
    });

    // 参考文献
    s.addText(card.ref, {
      x:x+0.22, y: baseY + 4.24, w: cw-0.44, h: 0.25,
      fontFace: F.body, fontSize: 10, italic:true, color: C.muted, align:'right'
    });
  });

  // 底部 takeaway 小卡
  const tkY = baseY + ch + 0.20;
  s.addShape(pres.ShapeType.roundRect, {
    x:0.8, y:tkY, w:11.7, h:0.65, rectRadius:0.08,
    fill:{ color: C.navy }, line:{ color: C.deep, width:0.75 }
  });
  s.addText('问题切入', {
    x:1.0, y:tkY, w:1.4, h:0.65,
    fontFace: F.cn, fontSize:13, bold:true, color: C.amber, align:'left', valign:'middle'
  });
  s.addText('阻挫铁磁体系下 3D Hopfion 的稳态边界 + 自旋波驱动响应规律 + 神经形态功能映射  →  本文系统化突破方向', {
    x:2.45, y:tkY, w:10.0, h:0.65,
    fontFace: F.cnBody, fontSize: 12, color: C.white,
    align:'left', valign:'middle'
  });

  pageNum(s, 8, TOTAL);
}

// =============================================================
//  Slide 6  研究内容与技术路线
// =============================================================
function slideRoadmap() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '研究内容与技术路线', 'Research Roadmap');

  // 三块流水线
  const stages = [
    { t:'01  构造', a:'解析初始态', b:'多拓扑荷可视化', c:'Mumax3 仿真平台', col:C.deep },
    { t:'02  稳定', a:'阻挫交换 (Frustrated FM)',  b:'稳态尺寸',     c:'Ku_c 临界扫描',   col:C.teal },
    { t:'03  驱动', a:'方向选择',    b:'频率响应',       c:'双向输运',        col:C.seafoam }
  ];
  const w = 3.6, h = 3.2;
  stages.forEach((st, i) => {
    const x = 0.6 + i*(w+0.55);
    // 卡片
    s.addShape(pres.ShapeType.roundRect, {
      x, y:1.85, w, h, rectRadius:0.1,
      fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
    });
    // 头部
    s.addShape(pres.ShapeType.rect, {
      x, y:1.85, w, h:0.55,
      fill:{ color: st.col }, line:{ type:'none' }
    });
    s.addText(st.t, {
      x, y:1.85, w, h:0.55,
      fontFace: F.cn, fontSize: 18, bold:true, color: C.white, align:'center', valign:'middle'
    });
    [st.a, st.b, st.c].forEach((it, j) => {
      s.addShape(pres.ShapeType.line, {
        x:x+0.4, y:2.7+j*0.7+0.32, w:0.18, h:0,
        line:{ color: st.col, width:2 }
      });
      s.addText(it, {
        x:x+0.65, y:2.7+j*0.7, w:w-0.85, h:0.55,
        fontFace: F.cnBody, fontSize: 14, color: C.charcoal,
        align:'left', valign:'middle'
      });
    });
    // 箭头
    if (i<2) {
      s.addText('▶', {
        x:x+w+0.05, y:3.15, w:0.5, h:0.6,
        fontFace: F.head, fontSize: 28, bold:true, color: C.teal,
        align:'center', valign:'middle'
      });
    }
  });

  // 第二排：04 应用 (单独一行宽卡)
  s.addShape(pres.ShapeType.roundRect, {
    x:0.6, y:5.4, w:12.15, h:1.4, rectRadius:0.1,
    fill:{ color: C.navy }, line:{ color: C.deep, width:0.75 }
  });
  s.addText('04  神经形态', {
    x:0.85, y:5.5, w:3.0, h:1.2,
    fontFace: F.cn, fontSize: 22, bold:true, color: C.amber, align:'left', valign:'middle'
  });
  s.addText('动力学特征  →  LIF 神经元功能映射  →  类脑器件概念架构', {
    x:3.9, y:5.5, w:8.5, h:1.2,
    fontFace: F.cn, fontSize:18, color: C.white, align:'left', valign:'middle', characterSpacing:2
  });

  pageNum(s, 9, TOTAL);
}

// =============================================================
//  Slide 7  理论基础: LLG + Hopf
// =============================================================
function slideTheory() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '理论基础：LLG 方程 与 Hopf 拓扑荷', 'LLG Dynamics · Hopf Topological Charge');

  // 3 概念卡 1×3 居中横排
  const concepts = [
    { n:'01', t:'磁化动力学',
      d:'LLG 方程（Landau-Lifshitz-Gilbert）描述磁矩在有效场中的进动 与 Gilbert 阻尼演化。',
      f:'∂ₜ m  =  −γ m × H_eff  +  α m × ∂ₜ m', c:C.deep },
    { n:'02', t:'拓扑保护',
      d:'Hopf 指数 Q_H 是 S³ → S² 映射的整数拓扑荷，连续形变下保持不变。',
      f:'Q_H ∈ ℤ ， Q_H = p × q', c:C.teal },
    { n:'03', t:'解析构造',
      d:'结合环面坐标 与 局域旋转矩阵，可生成任意 Q_H 与反铁磁 (AFM) 背景下的初始态。',
      f:'Mumax3 仿真平台 + Python 工具链', c:C.seafoam }
  ];
  const cw = 4.0, ch = 4.5, gap = 0.3;
  const totalW = cw*3 + gap*2;
  const startX = (13.333 - totalW) / 2;
  const baseY = 1.95;
  concepts.forEach((it, i) => {
    const x = startX + i*(cw+gap);
    s.addShape(pres.ShapeType.roundRect, {
      x, y:baseY, w:cw, h:ch, rectRadius:0.1,
      fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
    });
    // 顶部色条
    s.addShape(pres.ShapeType.rect, {
      x, y:baseY, w:cw, h:0.18,
      fill:{ color: it.c }, line:{ color: it.c }
    });
    // 大编号居中
    s.addText(it.n, {
      x, y:baseY+0.4, w:cw, h:1.0,
      fontFace: F.head, fontSize: 56, bold:true, color: it.c,
      align:'center', valign:'middle'
    });
    // 分隔短线
    s.addShape(pres.ShapeType.rect, {
      x:x+cw/2-0.4, y:baseY+1.55, w:0.8, h:0.03,
      fill:{ color: C.seafoam }, line:{ color: C.seafoam }
    });
    // 标题
    s.addText(it.t, {
      x:x+0.25, y:baseY+1.75, w:cw-0.5, h:0.55,
      fontFace: F.cn, fontSize: 20, bold:true, color: C.charcoal,
      align:'center', valign:'middle'
    });
    // 描述
    s.addText(it.d, {
      x:x+0.3, y:baseY+2.4, w:cw-0.6, h:1.4,
      fontFace: F.cnBody, fontSize: 13, color: C.muted,
      align:'center', valign:'top', lineSpacingMultiple:1.4
    });
    // 底部公式 / 关键短语
    s.addShape(pres.ShapeType.roundRect, {
      x:x+0.25, y:baseY+ch-0.65, w:cw-0.5, h:0.5, rectRadius:0.05,
      fill:{ color: C.cream }, line:{ color: it.c, width:0.75 }
    });
    s.addText(it.f, {
      x:x+0.25, y:baseY+ch-0.65, w:cw-0.5, h:0.5,
      fontFace: F.head, fontSize: 12, bold:true, italic:true, color: it.c,
      align:'center', valign:'middle'
    });
  });

  pageNum(s, 11, TOTAL);
}

// =============================================================
//  Slide 8  Hopfion 解析构造 (4 张图)
// =============================================================
function slideHopfionConstruct() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, 'Hopfion 解析构造：任意拓扑荷 Q_H 的初始态生成', 'Analytical Initialization · Q_H = 1, 2, 4');

  // 4 张图 横排
  const imgs = [
    { f:'hopfion_Qh1_p1q1_strategy1.png', label:'Q_H = 1', sub:'p=1, q=1' },
    { f:'hopfion_Qh2_p2q1_strategy1.png', label:'Q_H = 2', sub:'p=2, q=1' },
    { f:'hopfion_Qh2_p1q2_strategy1.png', label:'Q_H = 2', sub:'p=1, q=2' },
    { f:'hopfion_Qh4_p2q2_strategy1.png', label:'Q_H = 4', sub:'p=2, q=2' }
  ];
  const cw = 2.95, gap = 0.15;
  const totalW = cw*4 + gap*3;
  const sx = (13.333 - totalW)/2;
  const cy = 1.85;

  imgs.forEach((it, i) => {
    const x = sx + i*(cw+gap);
    s.addShape(pres.ShapeType.roundRect, {
      x, y:cy, w:cw, h:3.6, rectRadius:0.06,
      fill:{ color:C.white }, line:{ color:C.ice, width:0.5 }
    });
    s.addImage({ path: F_(it.f), x:x+0.15, y:cy+0.15, w:cw-0.3, h:(cw-0.3)/1.115, sizing:{ type:'contain', w:cw-0.3, h:(cw-0.3)/1.115 } });
    s.addText(it.label, {
      x, y:cy+2.85, w:cw, h:0.35,
      fontFace: F.head, fontSize: 16, bold:true, color: C.deep, align:'center'
    });
    s.addText(it.sub, {
      x, y:cy+3.2, w:cw, h:0.3,
      fontFace: F.head, fontSize: 12, italic:true, color: C.muted, align:'center'
    });
  });

  // 下半：方法说明
  const my = 5.65;
  s.addShape(pres.ShapeType.roundRect, {
    x:0.5, y:my, w:12.33, h:1.15, rectRadius:0.06,
    fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addShape(pres.ShapeType.rect, {
    x:0.5, y:my, w:0.18, h:1.15,
    fill:{ color: C.teal }, line:{ color: C.teal }
  });
  s.addText('方法', {
    x:0.85, y:my+0.05, w:1.2, h:0.4,
    fontFace: F.cn, fontSize:14, bold:true, color: C.deep, align:'left', valign:'middle'
  });
  s.addText('环面坐标映射  +  局域旋转矩阵  ⟶  生成任意 Q_H  及反铁磁交替背景下的解析自旋纹理；构建 Python 三维可视化工具链。', {
    x:0.85, y:my+0.45, w:11.8, h:0.65,
    fontFace: F.cnBody, fontSize: 13, color: C.charcoal, align:'left', valign:'middle', lineSpacingMultiple:1.3
  });

  pageNum(s, 12, TOTAL);
}

// =============================================================
//  Slide 9  阻挫交换稳态尺寸
// =============================================================
function slideSizeAttractor() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '阻挫交换体系：内秉稳态尺寸', 'Equilibrium Size in Frustrated Ferromagnets');

  // 左图：尺寸收敛
  s.addShape(pres.ShapeType.roundRect, {
    x:0.5, y:1.85, w:6.3, h:5.3, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('fig3-3_size_convergence.png'),
    x:0.65, y:2.0, w:5.95, h:4.93, sizing:{ type:'contain', w:5.95, h:4.93 } });
  s.addText('图：不同初始尺寸均收敛到统一稳态尺寸', {
    x:0.5, y:7.2, w:6.3, h:0.3,
    fontFace: F.cnBody, fontSize: 11, italic:true, color: C.muted, align:'center'
  });

  // 右：数据卡（重排：卡 h=1.65, gap 0.10）
  const rx = 8.3, rw = 4.55;
  // 卡 1: R_eq
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:1.85, w:rw, h:1.65, rectRadius:0.08,
    fill:{ color: C.deep }, line:{ color: C.deep }
  });
  s.addText('R_eq', {
    x:rx, y:1.92, w:rw, h:0.32,
    fontFace: F.head, fontSize: 13, italic:true, color: C.ice, align:'center', valign:'middle'
  });
  s.addText('2.60', {
    x:rx+0.3, y:2.3, w:rw-1.5, h:0.85,
    fontFace: F.head, fontSize: 52, bold:true, color: C.white, align:'right', valign:'middle'
  });
  s.addText('nm', {
    x:rx+rw-1.2, y:2.5, w:1.0, h:0.65,
    fontFace: F.head, fontSize: 20, color: C.ice, align:'left', valign:'middle'
  });
  s.addText('稳态大半径（Ku = 0）', {
    x:rx, y:3.18, w:rw, h:0.28,
    fontFace: F.cnBody, fontSize: 11, color: C.ice, align:'center', valign:'middle'
  });

  // 卡 2: r_eq
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:3.6, w:rw, h:1.65, rectRadius:0.08,
    fill:{ color: C.teal }, line:{ color: C.teal }
  });
  s.addText('r_eq', {
    x:rx, y:3.67, w:rw, h:0.32,
    fontFace: F.head, fontSize: 13, italic:true, color: C.cream, align:'center', valign:'middle'
  });
  s.addText('2.16', {
    x:rx+0.3, y:4.05, w:rw-1.5, h:0.85,
    fontFace: F.head, fontSize: 52, bold:true, color: C.white, align:'right', valign:'middle'
  });
  s.addText('nm', {
    x:rx+rw-1.2, y:4.25, w:1.0, h:0.65,
    fontFace: F.head, fontSize: 20, color: C.cream, align:'left', valign:'middle'
  });
  s.addText('稳态管半径（Ku = 10⁴ J/m³）', {
    x:rx, y:4.93, w:rw, h:0.28,
    fontFace: F.cnBody, fontSize: 11, color: C.cream, align:'center', valign:'middle'
  });

  // 卡 3: 取值无关结论
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:5.35, w:rw, h:1.45, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.amber, width:1.5 }
  });
  s.addText('关键发现', {
    x:rx, y:5.42, w:rw, h:0.3,
    fontFace: F.cn, fontSize: 12, bold:true, color: C.amber, align:'center'
  });
  s.addText('背景磁化方向\n对漂移行为无影响', {
    x:rx+0.15, y:5.78, w:rw-0.3, h:0.95,
    fontFace: F.cn, fontSize: 15, bold:true, color: C.charcoal,
    align:'center', valign:'middle', lineSpacingMultiple:1.25
  });

  pageNum(s, 13, TOTAL);
}

// =============================================================
//  Slide 11  漂移与居中验证
// =============================================================
function slideDrift() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '漂移行为与居中稳态验证', 'Drift Trajectory & Centered-Configuration Verification');

  // 左图：长时漂移轨迹（论文 fig3-4_drift_trajectory_10ns）
  s.addShape(pres.ShapeType.roundRect, {
    x:0.5, y:1.85, w:6.0, h:3.94, rectRadius:0.08,
    fill:{ color:C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('fig3-4_drift_trajectory_10ns.png'),
    x:0.65, y:2.0, w:3.7, h:3.69, sizing:{ type:'contain', w:3.7, h:3.69 } });
  s.addText('m_x=+1 背景下 10 ns 质心轨迹（前 1 ns 后零漂移）', {
    x:0.5, y:5.9, w:6.0, h:0.3,
    fontFace: F.cnBody, fontSize: 11, italic:true, color: C.muted, align:'center'
  });

  // 右图：居中验证
  s.addShape(pres.ShapeType.roundRect, {
    x:6.83, y:1.85, w:6.0, h:3.94, rectRadius:0.08,
    fill:{ color:C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('fig3-8_centered_z_drift.png'),
    x:6.98, y:2.0, w:5.7, h:3.64, sizing:{ type:'contain', w:5.7, h:3.64 } });
  s.addText('居中初始态：z 向漂移收敛于稳态', {
    x:6.83, y:5.9, w:6.0, h:0.3,
    fontFace: F.cnBody, fontSize: 11, italic:true, color: C.muted, align:'center'
  });

  pageNum(s, 14, TOTAL);
}

// =============================================================
//  Slide 12  Ku_c 临界各向异性
// =============================================================
function slideKuCritical() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '各向异性参数扫描：临界失稳阈值', 'Anisotropy Sweep · Critical Threshold');

  // 左图
  s.addShape(pres.ShapeType.roundRect, {
    x:0.5, y:1.85, w:4.4, h:4.85, rectRadius:0.08,
    fill:{ color:C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('fig3-7_anisotropy_summary.png'),
    x:0.7, y:2.0, w:4.0, h:4.45, sizing:{ type:'contain', w:4.0, h:4.45 } });
  s.addText('Ku 扫描：R / r 演化与 core 数', {
    x:0.5, y:6.75, w:4.4, h:0.3,
    fontFace: F.cnBody, fontSize:11, italic:true, color: C.muted, align:'center'
  });

  // 右：阈值卡
  const rx = 7.85, rw = 4.95;
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:1.85, w:rw, h:2.4, rectRadius:0.08,
    fill:{ color: C.midnight }, line:{ color: C.deep, width:0.5 }
  });
  s.addText('K_u1,c', {
    x:rx, y:1.95, w:rw, h:0.45,
    fontFace: F.head, fontSize: 16, italic:true, color: C.amber, align:'center'
  });
  s.addText('(52,  55) × 10³', {
    x:rx, y:2.45, w:rw, h:1.05,
    fontFace: F.head, fontSize: 32, bold:true, color: C.white, align:'center', valign:'middle'
  });
  s.addText('J / m³', {
    x:rx, y:3.55, w:rw, h:0.4,
    fontFace: F.head, fontSize: 16, color: C.ice, align:'center'
  });
  s.addText('临界各向异性区间', {
    x:rx, y:3.95, w:rw, h:0.3,
    fontFace: F.cnBody, fontSize: 11, color: C.ice, align:'center'
  });

  // 右下：解读
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:4.45, w:rw, h:2.35, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addText('解读', {
    x:rx+0.15, y:4.55, w:rw-0.3, h:0.35,
    fontFace: F.cn, fontSize: 14, bold:true, color: C.deep
  });
  const kuPts = [
    'Ku = 52 k：core ≈ 376，Hopfion 存活',
    'Ku = 55 k：core = 0，结构完全坍塌',
    'Ku 上行使势阱变浅，最终突破临界'
  ];
  kuPts.forEach((p, i) => {
    s.addText('• ' + p, {
      x:rx+0.2, y:4.95+i*0.55, w:rw-0.4, h:0.5,
      fontFace: F.cnBody, fontSize: 12, color: C.charcoal, valign:'middle', lineSpacingMultiple:1.25
    });
  });

  pageNum(s, 15, TOTAL);
}

// =============================================================
//  Slide 17  实验装置示意（自旋波驱动引入）
// =============================================================
function slideSWDeviceIntro() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '实验装置示意：自旋波激励 → Hopfion 驱动', 'Spin-Wave Excitation Setup');

  // 居中大图
  const cw = 7.5, ch = 4.85;
  const cx = (13.333 - cw) / 2;
  s.addShape(pres.ShapeType.roundRect, {
    x:cx, y:1.85, w:cw, h:ch, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('fig6-2_device_concept.png'),
    x:cx+0.25, y:2.0, w:7.0, h:3.82, sizing:{ type:'contain', w:7.0, h:3.82 } });
  s.addText('概念器件示意（论文 fig6-2）：磁轨道 + 内嵌 Hopfion + 自旋波激励 + 位置读取', {
    x:cx, y:6.50, w:cw, h:0.3,
    fontFace: F.cnBody, fontSize: 11, italic:true, color: C.muted, align:'center'
  });

  pageNum(s, 17, TOTAL);
}

// =============================================================
//  Slide 18  自旋波驱动 - 方向选择
// =============================================================
function slideDirectionSel() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '自旋波驱动：极化方向选择规律', 'Polarization Selectivity of Magnon Excitation');

  // 左图
  s.addShape(pres.ShapeType.roundRect, {
    x:0.5, y:1.85, w:3.7, h:4.85, rectRadius:0.08,
    fill:{ color:C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('fig4-1_direction_selectivity.png'),
    x:0.7, y:2.0, w:3.1, h:4.43, sizing:{ type:'contain', w:3.1, h:4.43 } });
  s.addText('面内 vs 面外极化，Hopfion 响应差异', {
    x:0.5, y:6.75, w:3.7, h:0.3,
    fontFace: F.cnBody, fontSize: 11, italic:true, color: C.muted, align:'center'
  });

  // 右：对比卡
  const rx = 8.35, rw = 4.45;
  // YES 卡
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:1.95, w:rw, h:2.3, rectRadius:0.08,
    fill:{ color: C.teal }, line:{ color: C.teal }
  });
  s.addText('✓', {
    x:rx, y:2.05, w:rw, h:0.7,
    fontFace: F.head, fontSize: 38, bold:true, color: C.white, align:'center'
  });
  s.addText('面内极化', {
    x:rx, y:2.75, w:rw, h:0.45,
    fontFace: F.cn, fontSize: 18, bold:true, color: C.white, align:'center'
  });
  s.addText('Hopfion 被有效驱动\n触发平动 / 漂移', {
    x:rx, y:3.25, w:rw, h:0.95,
    fontFace: F.cnBody, fontSize: 13, color: C.cream, align:'center', valign:'top', lineSpacingMultiple:1.3
  });

  // NO 卡
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:4.45, w:rw, h:2.3, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.coral, width:1.5 }
  });
  s.addText('✕', {
    x:rx, y:4.55, w:rw, h:0.7,
    fontFace: F.head, fontSize: 38, bold:true, color: C.coral, align:'center'
  });
  s.addText('面外极化', {
    x:rx, y:5.25, w:rw, h:0.45,
    fontFace: F.cn, fontSize: 18, bold:true, color: C.charcoal, align:'center'
  });
  s.addText('对平动几乎无贡献\n仅引起内部呼吸', {
    x:rx, y:5.75, w:rw, h:0.95,
    fontFace: F.cnBody, fontSize: 13, color: C.muted, align:'center', valign:'top', lineSpacingMultiple:1.3
  });

  pageNum(s, 18, TOTAL);
}

// =============================================================
//  Slide 14  srcZ 频率响应
// =============================================================
function slideFreqResponse() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, 'srcZ 轴向传播频响：多峰结构与方向反转', 'Axial Spectrum · Multi-peak Resonance · Direction Reversal');

  // 大图
  s.addShape(pres.ShapeType.roundRect, {
    x:0.5, y:1.85, w:4.0, h:5.3, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('fig4-5_srcZ_trajectory.png'),
    x:0.7, y:2.0, w:3.5, h:4.91, sizing:{ type:'contain', w:3.5, h:4.91 } });
  s.addText('图  srcZ 频率扫描下 Hopfion 的位移轨迹（论文 §5.2.3）', {
    x:0.5, y:7.05, w:4.0, h:0.3,
    fontFace: F.cnBody, fontSize: 11, italic:true, color: C.muted, align:'center'
  });

  // 右上：主峰卡
  const rx = 9.35, rw = 3.5;
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:1.85, w:rw, h:1.55, rectRadius:0.08,
    fill:{ color: C.midnight }, line:{ color: C.amber, width:1 }
  });
  s.addText('共振主峰', {
    x:rx, y:1.92, w:rw, h:0.3,
    fontFace: F.cn, fontSize: 12, color: C.amber, align:'center'
  });
  s.addText('1100', {
    x:rx, y:2.18, w:rw, h:0.85,
    fontFace: F.head, fontSize: 48, bold:true, color: C.white, align:'center', valign:'middle'
  });
  s.addText('GHz  ‧  −z 最强响应', {
    x:rx, y:3.05, w:rw, h:0.3,
    fontFace: F.cnBody, fontSize: 11, color: C.ice, align:'center'
  });

  // 右中：100 GHz 反向卡
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:3.55, w:rw, h:1.55, rectRadius:0.08,
    fill:{ color: C.deep }, line:{ color: C.deep }
  });
  s.addText('唯一反向频率', {
    x:rx, y:3.62, w:rw, h:0.3,
    fontFace: F.cn, fontSize: 12, color: C.cream, align:'center'
  });
  s.addText('100', {
    x:rx, y:3.88, w:rw, h:0.85,
    fontFace: F.head, fontSize: 48, bold:true, color: C.white, align:'center', valign:'middle'
  });
  s.addText('GHz  ‧  +z（朝向源）', {
    x:rx, y:4.75, w:rw, h:0.3,
    fontFace: F.cnBody, fontSize: 11, color: C.cream, align:'center'
  });

  // 右下：死区列表
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:5.25, w:rw, h:1.6, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.ice, width:1 }
  });
  s.addText('响应死区', {
    x:rx, y:5.32, w:rw, h:0.3,
    fontFace: F.cn, fontSize: 12, bold:true, color: C.charcoal, align:'center'
  });
  s.addText('75 / 150 / 600 / 1300 GHz', {
    x:rx, y:5.62, w:rw, h:0.45,
    fontFace: F.head, fontSize: 14, bold:true, color: C.deep, align:'center', valign:'middle'
  });
  s.addText('频率选择性  ‧  非线性响应', {
    x:rx, y:6.1, w:rw, h:0.3,
    fontFace: F.cnBody, fontSize: 10, italic:true, color: C.muted, align:'center'
  });
  s.addText('20 频点中  19 个 −z, 1 个 +z', {
    x:rx, y:6.42, w:rw, h:0.3,
    fontFace: F.cnBody, fontSize: 10, color: C.muted, align:'center'
  });

  pageNum(s, 19, TOTAL);
}

// =============================================================
//  Slide 14  双向可逆输运
// =============================================================
function slideBidirectional() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '频率切换实现轴向双向可逆输运', 'Bidirectional Transport via Frequency Switching');

  // 大图
  s.addShape(pres.ShapeType.roundRect, {
    x:0.5, y:1.85, w:5.0, h:4.7, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('fig4-11_freq_switch_z_control.png'),
    x:0.7, y:2.0, w:4.5, h:4.10, sizing:{ type:'contain', w:4.5, h:4.10 } });
  s.addText('图  频率切换下 Hopfion 的 z 向位移与速度（论文 §5.2.6）', {
    x:0.5, y:6.65, w:5.0, h:0.3,
    fontFace: F.cnBody, fontSize: 11, italic:true, color: C.muted, align:'center'
  });

  // 右：双步骤
  const rx = 9.35, rw = 3.5;
  // 步骤 1
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:1.95, w:rw, h:2.3, rectRadius:0.08,
    fill:{ color: C.teal }, line:{ color: C.teal }
  });
  s.addText('Phase 1', {
    x:rx, y:2.05, w:rw, h:0.4,
    fontFace: F.head, fontSize: 14, bold:true, color: C.cream, align:'center'
  });
  s.addText('+ 18.6 nm', {
    x:rx, y:2.5, w:rw, h:0.85,
    fontFace: F.head, fontSize: 26, bold:true, color: C.white, align:'center', valign:'middle'
  });
  s.addText('频率 f₁\n正向位移积累', {
    x:rx+0.1, y:3.4, w:rw-0.2, h:0.85,
    fontFace: F.cnBody, fontSize: 13, color: C.cream, align:'center', valign:'top', lineSpacingMultiple:1.3
  });

  // 箭头
  s.addText('↓', {
    x:rx, y:4.28, w:rw, h:0.55,
    fontFace: F.head, fontSize: 28, bold:true, color: C.amber, align:'center', valign:'middle'
  });

  // 步骤 2
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:4.7, w:rw, h:2.15, rectRadius:0.08,
    fill:{ color: C.deep }, line:{ color: C.deep }
  });
  s.addText('Phase 2', {
    x:rx, y:4.8, w:rw, h:0.4,
    fontFace: F.head, fontSize: 14, bold:true, color: C.amber, align:'center'
  });
  s.addText('反向位移', {
    x:rx, y:5.2, w:rw, h:0.85,
    fontFace: F.head, fontSize: 26, bold:true, color: C.white, align:'center', valign:'middle'
  });
  s.addText('频率 f₂\n位移逆转 / 释放', {
    x:rx+0.1, y:6.05, w:rw-0.2, h:0.75,
    fontFace: F.cnBody, fontSize: 13, color: C.ice, align:'center', valign:'top', lineSpacingMultiple:1.3
  });

  pageNum(s, 20, TOTAL);
}

// =============================================================
//  Slide 18  神经形态映射
// =============================================================
function slideNeuromorphic() {
  const s = pres.addSlide();
  lightBackground(s);
  lightTitle(s, '神经形态映射：Hopfion → LIF 神经元', 'Mapping Hopfion Dynamics to LIF Neuron Functions');

  // 左：fig6-2_lif_analogy 图（论文实际类比图）
  s.addShape(pres.ShapeType.roundRect, {
    x:0.5, y:1.85, w:5.0, h:4.85, rectRadius:0.08,
    fill:{ color: C.white }, line:{ color: C.ice, width:0.5 }
  });
  s.addImage({ path: F_('fig6-2_lif_analogy.png'),
    x:0.75, y:2.0, w:4.5, h:4.31, sizing:{ type:'contain', w:4.5, h:4.31 } });
  s.addText('图 6-2  Hopfion 位移曲线 (上) ↔ LIF 膜电位波形 (下)', {
    x:0.5, y:6.42, w:5.0, h:0.28,
    fontFace: F.cnBody, fontSize: 10, italic:true, color: C.muted, align:'center'
  });

  // 右上：4 个映射卡 纵排（动力学特征 ⟶ 神经元功能）
  const items = [
    { d:'激发阈值',  n:'临界激励强度',  c:C.deep },
    { d:'频率选择',  n:'共振响应',      c:C.teal },
    { d:'方向编码',  n:'双向输运',      c:C.seafoam },
    { d:'位移积累',  n:'膜电位充电',    c:C.amber }
  ];
  const rx = 5.7, rw = 7.13, rh = 1.0, rgap = 0.10;
  items.forEach((it, i) => {
    const yy = 1.85 + i*(rh+rgap);
    s.addShape(pres.ShapeType.roundRect, {
      x:rx, y:yy, w:rw, h:rh, rectRadius:0.06,
      fill:{ color:C.white }, line:{ color: C.ice, width:0.5 }
    });
    s.addShape(pres.ShapeType.rect, {
      x:rx, y:yy, w:0.16, h:rh,
      fill:{ color: it.c }, line:{ color: it.c }
    });
    // Hopfion 侧
    s.addText('Hopfion', {
      x:rx+0.45, y:yy+0.10, w:1.6, h:0.30,
      fontFace: F.head, fontSize: 11, italic:true, color: C.muted, align:'left', valign:'middle'
    });
    s.addText(it.d, {
      x:rx+0.45, y:yy+0.40, w:2.6, h:0.50,
      fontFace: F.cn, fontSize: 17, bold:true, color: C.charcoal, align:'left', valign:'middle'
    });
    // 中间箭头
    s.addText('⟶', {
      x:rx+3.0, y:yy+0.20, w:0.7, h:0.55,
      fontFace: F.head, fontSize: 26, bold:true, color: it.c, align:'center', valign:'middle'
    });
    // 神经元侧
    s.addText('神经元', {
      x:rx+3.8, y:yy+0.10, w:1.6, h:0.30,
      fontFace: F.head, fontSize: 11, italic:true, color: C.muted, align:'left', valign:'middle'
    });
    s.addText(it.n, {
      x:rx+3.8, y:yy+0.40, w:rw-3.95, h:0.50,
      fontFace: F.cn, fontSize: 16, bold:true, color: it.c, align:'left', valign:'middle'
    });
  });

  // 右下：流程整合宽卡
  s.addShape(pres.ShapeType.roundRect, {
    x:rx, y:6.30, w:rw, h:0.55, rectRadius:0.05,
    fill:{ color:C.midnight }, line:{ type:'none' }
  });
  s.addText('与 Leaky Integrate-and-Fire (LIF) 神经元模型功能等价', {
    x:rx, y:6.30, w:rw, h:0.55,
    fontFace: F.cn, fontSize: 13, bold:true, color: C.amber, align:'center', valign:'middle'
  });

  pageNum(s, 22, TOTAL);
}

// =============================================================
//  Slide 16  创新点
// =============================================================
function slideContributions() {
  const s = pres.addSlide();
  darkBackground(s);

  s.addText('CONTRIBUTIONS', {
    x:0.5, y:0.55, w:12.3, h:0.4,
    fontFace: F.head, fontSize: 16, color: C.seafoam, align:'center', characterSpacing:8
  });
  s.addText('主要创新点', {
    x:0.5, y:0.95, w:12.3, h:0.7,
    fontFace: F.cn, fontSize: 36, bold:true, color: C.white, align:'center'
  });
  s.addShape(pres.ShapeType.rect, {
    x:6.16, y:1.75, w:1.0, h:0.04, fill:{ color:C.amber }, line:{ color:C.amber }
  });

  const items = [
    {
      n:'01',
      t:'解析化拓扑构造工具链',
      d:'实现任意 Q_H 与反铁磁交替背景下 Hopfion 解析生成 + 三维可视化，覆盖 Q_H = 1, 2, 4。'
    },
    {
      n:'02',
      t:'稳定性参数判据',
      d:'阻挫交换体系定位 K_u1,c ∈ (52, 55) × 10³ J/m³，确认 R_eq = 2.60 nm 内秉稳态尺寸。'
    },
    {
      n:'03',
      t:'类脑功能映射',
      d:'凝练动力学特征与 LIF 神经元功能映射，提出自旋波驱动的三维类脑器件概念。'
    }
  ];
  // 1×3 居中对称
  const cw = 4.0, ch = 4.6, gap = 0.3;
  const totalW = cw*3 + gap*2;
  const startX = (13.333 - totalW) / 2;
  const baseY = 2.1;
  items.forEach((it, i) => {
    const x = startX + i*(cw+gap);
    const y = baseY;
    // 卡片底
    s.addShape(pres.ShapeType.roundRect, {
      x, y, w:cw, h:ch, rectRadius:0.1,
      fill:{ color: C.navy }, line:{ color: C.deep, width:0.75 }
    });
    // 顶部 amber 装饰条
    s.addShape(pres.ShapeType.rect, {
      x, y, w:cw, h:0.18,
      fill:{ color: C.amber }, line:{ color: C.amber }
    });
    // 序号（居中大字）
    s.addText(it.n, {
      x, y:y+0.45, w:cw, h:1.1,
      fontFace: F.head, fontSize: 64, bold:true, color: C.amber,
      align:'center', valign:'middle'
    });
    // 分隔短线
    s.addShape(pres.ShapeType.rect, {
      x:x+cw/2-0.4, y:y+1.75, w:0.8, h:0.03,
      fill:{ color: C.seafoam }, line:{ color: C.seafoam }
    });
    // 标题
    s.addText(it.t, {
      x:x+0.25, y:y+1.95, w:cw-0.5, h:0.85,
      fontFace: F.cn, fontSize: 18, bold:true, color: C.white,
      align:'center', valign:'middle', lineSpacingMultiple:1.2
    });
    // 描述
    s.addText(it.d, {
      x:x+0.3, y:y+2.95, w:cw-0.6, h:1.5,
      fontFace: F.cnBody, fontSize: 13, color: C.ice,
      align:'left', valign:'top', lineSpacingMultiple:1.5
    });
  });
}

// =============================================================
//  Slide 17  结论 / 致谢
// =============================================================
function slideThanks() {
  const s = pres.addSlide();
  darkBackground(s);

  // 顶部小字
  s.addText('THANKS  FOR  LISTENING', {
    x:0.5, y:1.5, w:12.3, h:0.5,
    fontFace: F.head, fontSize: 18, color: C.seafoam, align:'center', characterSpacing:10
  });

  // 主标题
  s.addText('感  谢  聆  听', {
    x:0.5, y:2.4, w:12.3, h:1.4,
    fontFace: F.cn, fontSize: 80, bold:true, color: C.white, align:'center', valign:'middle', characterSpacing:24
  });

  // 装饰
  s.addShape(pres.ShapeType.rect, {
    x:5.0, y:4.0, w:3.3, h:0.04,
    fill:{ color: C.amber }, line:{ color: C.amber }
  });

  // 邀请提问
  s.addText('恳请各位老师批评指正', {
    x:0.5, y:4.4, w:12.3, h:0.5,
    fontFace: F.cn, fontSize: 22, color: C.ice, align:'center', characterSpacing:6
  });

  // 致谢段落（极简）
  s.addShape(pres.ShapeType.roundRect, {
    x:2.5, y:5.4, w:8.3, h:1.45, rectRadius:0.1,
    fill:{ color: C.navy }, line:{ color: C.teal, width:0.75 }
  });
  s.addText('诚挚感谢导师 金蒙豪 老师的悉心指导\n感谢电子信息学院与课题组提供的科研支持', {
    x:2.5, y:5.4, w:8.3, h:1.45,
    fontFace: F.cnBody, fontSize: 16, color: C.white, align:'center', valign:'middle', lineSpacingMultiple:1.5
  });

  // 底部信息条
  s.addText('吴佳乐 · 22040338 · 电子科学与技术 · 2026.05', {
    x:0.5, y:7.05, w:12.3, h:0.3,
    fontFace: F.body, fontSize: 11, color: C.muted, align:'center'
  });
}

// =============================================================
//  生成
// =============================================================
slideCover();
slideAgenda();
slideChapterCover('01', '研究背景与意义', '8B5CF6');
slideHopfionIntro();
slideBackground();
slideSignificance();
slideChapterCover('02', '国内外研究现状', 'F2A65A');
slideLiterature();
slideRoadmap();
slideChapterCover('03', '拓扑稳定性研究', '1C7293');
slideTheory();
slideHopfionConstruct();
slideSizeAttractor();
slideDrift();
slideKuCritical();
slideChapterCover('04', '磁振子驱动动力学', '8B5CF6');
slideSWDeviceIntro();
slideDirectionSel();
slideFreqResponse();
slideBidirectional();
slideChapterCover('05', '神经形态映射与创新', 'F2A65A');
slideNeuromorphic();
slideContributions();
slideThanks();

pres.writeFile({ fileName: 'defense_slides.pptx' })
  .then(fname => console.log(`\n✅ 已生成: ${fname}`))
  .catch(err => { console.error('\n❌ 生成失败:', err); process.exit(1); });
