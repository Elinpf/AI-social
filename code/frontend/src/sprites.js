/* sprites.js — 程序化 + AI Town 像素素材的渲染原语（art-director 视觉重构版）。
 *
 * 素材：AI Town（a16z-infra/ai-town, MIT）的 `gentle-obj.png` 地形/装饰 tileset 与
 * `peeps.png` 角色表，随附于 `frontend/assets/`，来源见 `frontend/NOTICE`。
 * 纪律：只读日志/config，绝不写世界；地形/装饰/建筑由 config 拓扑 + 固定哈希**确定性**生成。
 *
 * 重构要点（对齐 AI Town 观感）：
 *  - 无缝草地底 + 低频色斑（消除 checkerboard 接缝）；
 *  - 道路/广场/水面/农田用**程序化像素**绘制（柔和边缘 + 碎石/涟漪/田垄细节）；
 *  - 建筑按 place_id 分**原型**（村舍/工坊/谷仓/商铺/塔楼/会堂/城门/喷泉/凉亭），
 *    阶梯式屋顶 + 屋檐阴影 + 门牌/窗框，比例与投影统一；
 *  - 角色放大、正反朝向、头顶名牌与气泡；
 *  - 道具：路灯/长椅/围栏/招牌/花坛/水井/木箱/酒桶（确定性摆放）。
 */
(function (global) {
  "use strict";

  // ---- 场所类别配色（保留：图例/SVG 导出同口径；建筑原型在其上叠加造型差异）----
  const CATEGORY_STYLE = {
    living:          { name: "居住", wall: 0xb07a52, roof: 0x7a4a2b, win: 0xffe08a },
    work_production: { name: "生产", wall: 0x5f9e56, roof: 0x3f6f3a, win: 0xd8f0a0 },
    work_processing: { name: "加工", wall: 0x4fa39a, roof: 0x2f6f69, win: 0xcdeff0 },
    work_service:    { name: "服务", wall: 0x5b86c4, roof: 0x35578a, win: 0xd6e6ff },
    work_education:  { name: "教育", wall: 0x8a6fc0, roof: 0x5a468a, win: 0xeadfff },
    work_admin:      { name: "行政", wall: 0x7b8794, roof: 0x525c66, win: 0xe0e6ec },
    trade:           { name: "交易", wall: 0xc9a13f, roof: 0x8f6f1f, win: 0xfff2c0 },
    public:          { name: "公共", wall: 0x62a0a8, roof: 0x3d7078, win: 0xd8f2f5 },
    leisure:         { name: "娱乐", wall: 0xc86f9b, roof: 0x8f4569, win: 0xffdcec },
    edge:            { name: "边缘", wall: 0x6b6f76, roof: 0x44474c, win: 0xc7ccd2 },
  };
  function styleFor(category) { return CATEGORY_STYLE[category] || CATEGORY_STYLE.work_admin; }

  // ---- 调色工具 ----------------------------------------------------------
  function shade(hex, f) {
    const r = (hex >> 16) & 255, g = (hex >> 8) & 255, b = hex & 255;
    const cl = (v) => Math.max(0, Math.min(255, Math.round(v * f)));
    return (cl(r) << 16) | (cl(g) << 8) | cl(b);
  }
  function mix(hexA, hexB, t) {
    const ar = (hexA >> 16) & 255, ag = (hexA >> 8) & 255, ab = hexA & 255;
    const br = (hexB >> 16) & 255, bg = (hexB >> 8) & 255, bb = hexB & 255;
    const m = (a, b) => Math.round(a + (b - a) * t);
    return (m(ar, br) << 16) | (m(ag, bg) << 8) | m(ab, bb);
  }

  // ---- AI Town tileset（gentle-obj.png: 45 x 32 个 32px tile）----
  const TILE = 32;
  const TILESET_COLS = 45;
  // 索引由「像素方差 + 逐 tile 视觉核对」重定：只保留**可无缝平铺**的地面瓦
  const TILES = {
    grass: [271, 226, 962],        // 深绿草地（271 为主，无缝）
    grassLight: [745, 1015],       // 亮绿草地（点缀低频色斑）
    soil: [1024, 1016],            // 农田/裸土（棕 / 沙）
    water: [451, 452],             // 水面（涟漪可平铺）
  };
  // 装饰精灵：整株对象（[sx,sy,sw,sh] 源矩形；经连通域分析定位，非 32px 切片）
  const SPR = {
    treeCluster: [1153, 704, 127, 128],   // 5 株圆冠树丛（AI Town 招牌树）
    conifer:     [1248, 608, 32, 64],     // 针叶树
    bush:        [1280, 608, 32, 32],     // 灌木
    rock:        [1313, 609, 31, 30],     // 岩石
    flower:      [1185, 577, 30, 30],     // 花丛
    plant:       [1153, 577, 31, 31],     // 干枝植物
  };
  function spriteTex(base, r) {
    return new global.PIXI.Texture(base, new global.PIXI.Rectangle(r[0], r[1], r[2], r[3]));
  }
  const DECOR = SPR; // 向后兼容导出名
  // peeps.png 真实网格（经 alpha 空隙分析测得）：12 列 x 8 行，**每格 48x96**；
  // 每行 = 4 个角色，每个角色 3 帧行走（列 0-2 / 3-5 / 6-8 / 9-11）。
  // 行内容带（自 alpha 空隙测得，确定性常量）：
  const PEEPS = {
    CELLW: 48, CELLH: 96, ROWS: 8, GROUPS: 4, FRAMES: 3,
    BANDS: [[21, 92], [120, 188], [216, 284], [312, 380], [405, 476], [501, 572], [597, 668], [693, 764]],
  };
  // 兼容旧导出名（不再用于切图）
  const PEEPS_FRAMES = [];
  const PEEPS_COLS = 18;

  const PLACE_SIZE = 78;

  // ---- 纹理工具 ----------------------------------------------------------
  function slice(base, idx, cols) {
    cols = cols || TILESET_COLS;
    const c = idx % cols, r = Math.floor(idx / cols);
    return new global.PIXI.Texture(base, new global.PIXI.Rectangle(c * TILE, r * TILE, TILE, TILE));
  }
  // 按「角色(行,组) + 帧」切出 48x96 全身立绘
  function peepsTexture(base, i, frame) {
    const R = PEEPS.ROWS, G = PEEPS.GROUPS, F = PEEPS.FRAMES;
    const total = R * G;
    const idx = ((i % total) + total) % total;
    const row = Math.floor(idx / G), grp = idx % G;
    const b = PEEPS.BANDS[row] || PEEPS.BANDS[0];
    const fr = ((frame || 0) % F + F) % F;
    const x = (grp * F + fr) * PEEPS.CELLW;
    const y = b[0] - 1, h = (b[1] - b[0]) + 2;
    return new global.PIXI.Texture(base, new global.PIXI.Rectangle(x, y, PEEPS.CELLW, h));
  }

  // 确定性哈希（→ 0..1）：稳定摆放，可复现
  function hash2(x, y, salt) {
    let n = (x * 374761393 + y * 668265263 + (salt || 0) * 2246822519) | 0;
    n = ((n ^ (n >>> 13)) * 1274126177) | 0;
    return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
  }
  function pick(arr, r) { return arr[Math.floor(r * arr.length) % arr.length]; }

  // Graphics 便捷封装（保持 smoke_test 的 PIXI mock 兼容：只用 drawRect/RoundedRect/Circle/Ellipse）
  function fillRect(g, x, y, w, h, color, alpha) {
    g.beginFill(color, alpha == null ? 1 : alpha); g.drawRect(x, y, w, h); g.endFill();
  }
  function fillRound(g, x, y, w, h, r, color, alpha) {
    g.beginFill(color, alpha == null ? 1 : alpha); g.drawRoundedRect(x, y, w, h, r); g.endFill();
  }
  function strokeRound(g, x, y, w, h, r, color, width) {
    g.lineStyle(width, color, 1); g.drawRoundedRect(x, y, w, h, r); g.lineStyle(0, 0, 0);
  }
  function fillCircle(g, x, y, r, color, alpha) {
    g.beginFill(color, alpha == null ? 1 : alpha); g.drawCircle(x, y, r); g.endFill();
  }
  function fillEllipse(g, x, y, hw, hh, color, alpha) {
    g.beginFill(color, alpha == null ? 1 : alpha); g.drawEllipse(x, y, hw, hh); g.endFill();
  }
  // 阶梯式三角形（像素风屋顶）：从 baseline y 向上收缩；带 1px 暗描边（单一光源、立体感）
  function steppedGable(g, cx, baseY, halfW, height, steps, color) {
    const sh = height / steps;
    const ink = 0x241a12;
    for (let i = 0; i < steps; i++) {          // 描边（略大一圈）
      const w = Math.round((halfW + 1.2) * (1 - i / steps)) * 2 + 2;
      fillRect(g, cx - w / 2, baseY - (i + 1) * sh - 1.5, w, sh + 2, ink);
    }
    for (let i = 0; i < steps; i++) {          // 屋面
      const w = Math.round(halfW * (1 - i / steps)) * 2;
      fillRect(g, cx - w / 2, baseY - (i + 1) * sh, w, sh + 1, color);
    }
  }

  // ========================================================================
  //  建筑原型：按 place_id 映射到造型 + 类别配色
  // ========================================================================
  const BUILDING_SPEC = {
    residence:        { kind: "cottage", palette: "living" },
    farm:             { kind: "barn",    palette: "work_production" },
    workshop:         { kind: "workshop", palette: "work_production" },
    kitchen:          { kind: "cottage", palette: "work_processing", awning: true, chimney: true },
    clinic:           { kind: "tower",   palette: "work_service", emblem: "cross" },
    school:           { kind: "tower",   palette: "work_education", emblem: "bell" },
    office:           { kind: "hall",    palette: "work_admin", roof: "flat", storeys: 2 },
    market:           { kind: "stalls",  palette: "trade" },
    bank:             { kind: "hall",    palette: "trade", columns: true, emblem: "coin", storeys: 2 },
    plaza:            { kind: "fountain", palette: "public" },
    town_hall:        { kind: "tower",   palette: "public", emblem: "clock" },
    library:          { kind: "hall",    palette: "public", roof: "dome", emblem: "book" },
    community_center: { kind: "hall",    palette: "public", wide: true },
    cafe:             { kind: "cottage", palette: "leisure", awning: true, emblem: "cup" },
    park:             { kind: "gazebo",  palette: "leisure" },
    hall:             { kind: "hall",    palette: "leisure", wide: true, columns: true },
    gate:             { kind: "gate",    palette: "edge" },
  };

  function drawEmblem(g, kind, x, y, color) {
    if (kind === "cross") {                       // 诊所：红十字
      fillRect(g, x - 3, y - 10, 6, 20, color); fillRect(g, x - 10, y - 3, 20, 6, color);
    } else if (kind === "coin") {                 // 银行：金币
      fillCircle(g, x, y, 9, 0xf3d34a); fillCircle(g, x, y, 6, 0xd9ad25);
      fillRect(g, x - 1, y - 5, 2, 10, 0x8a6a12); fillRect(g, x - 4, y - 1, 8, 2, 0x8a6a12);
    } else if (kind === "clock") {                // 市政厅：钟面
      fillCircle(g, x, y, 9, 0xf6f2e6); fillCircle(g, x, y, 7, 0x2f3b46);
      fillRect(g, x - 1, y - 5, 2, 6, 0xf6f2e6); fillRect(g, x - 1, y - 1, 6, 2, 0xf6f2e6);
    } else if (kind === "bell") {                 // 学校：钟
      fillRect(g, x - 7, y - 2, 14, 6, 0xf0c14a);
      fillRect(g, x - 5, y - 7, 10, 5, 0xf0c14a); fillRect(g, x - 2, y - 10, 4, 3, 0xd9a52a);
      fillRect(g, x - 9, y + 4, 18, 2, 0x9a7420);
    } else if (kind === "book") {                 // 图书馆：书
      fillRect(g, x - 9, y - 6, 18, 12, 0xf3efe0);
      fillRect(g, x - 1, y - 6, 2, 12, 0x8a6f4a);
      fillRect(g, x - 9, y - 6, 18, 2, 0xc9b48a); fillRect(g, x - 9, y + 4, 18, 2, 0xc9b48a);
    } else if (kind === "cup") {                  // 咖啡馆：杯子
      fillRect(g, x - 7, y - 5, 12, 11, 0xf3efe0);
      fillRect(g, x + 5, y - 2, 5, 6, 0xf3efe0); fillRect(g, x + 6, y - 1, 3, 4, 0x6b4a2b);
      fillRect(g, x - 9, y + 6, 16, 3, 0xd9cdb2);
    }
  }

  // 建筑主体公共：投影 → 墙体 → 屋檐 → 门窗 → 招牌
  function placeLabel(PIXI, place, st, y) {
    const label = new PIXI.Text(place.name_cn || place.place_id, {
      fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif', fontSize: 14,
      fill: 0xffffff, stroke: 0x0b0e12, strokeThickness: 4,
    });
    label.anchor.set(0.5, 0); label.y = y; label.zIndex = 999;
    return label;
  }

  function makePlaceSprite(PIXI, place, node) {
    const spec = BUILDING_SPEC[place.place_id] || { kind: "cottage", palette: place.category };
    const st = styleFor(spec.palette);
    const c = new PIXI.Container();
    c.x = node.x; c.y = node.y;
    const g = new PIXI.Graphics();
    const wall = st.wall, roof = st.roof, win = st.win;
    const wallD = shade(wall, 0.72), wallL = shade(wall, 1.18);
    const roofD = shade(roof, 0.7), roofL = shade(roof, 1.2);
    const trim = 0xf2ead6, ink = 0x211a12;

    const k = spec.kind;

    // 贴地投影：与建筑底边相接、无缝隙；低对比冷灰、向右 1–2px（top-down 标准做法）
    const sw = ({ cottage: 30, tower: 40, hall: spec.wide ? 52 : 44, barn: 48,
      workshop: 38, stalls: 50, fountain: 34, gazebo: 36, gate: 34 }[k]) || 38;
    const sy = ({ fountain: 12, gazebo: 13 }[k]) || 0;
    fillRound(g, -sw - 4 + 2, -3 + sy, sw * 2 + 8, 8, 4, 0x2b3240, 0.30);
    fillRect(g, -sw + 2, -1 + sy, sw * 2 + 2, 3, 0x20262e, 0.32);

    if (k === "fountain") {
      // 中央广场：喷泉/水井 + 铺装环
      fillEllipse(g, 0, 6, 30, 12, 0x9a9a92);
      fillEllipse(g, 0, 4, 26, 10, 0xb7b7ad);
      fillEllipse(g, 0, 2, 16, 7, 0x3f6fa8);
      fillEllipse(g, 0, 1, 13, 5.5, 0x5b93cf);
      fillRect(g, -3, -22, 6, 22, 0xcfd6dd);
      fillRect(g, -3, -22, 6, 4, 0xeef4fa);
      fillEllipse(g, 0, -22, 9, 4, 0x8fb8e0, 0.9);
      fillRect(g, -1, -30, 2, 10, 0xbfe0f2, 0.8);
      fillCircle(g, 0, -32, 3, 0xdff0fb, 0.9);
    } else if (k === "gazebo") {
      // 公园：凉亭 + 长椅感
      fillRound(g, -26, -6, 52, 16, 4, shade(wall, 0.78));
      const pad = 6;
      [-26, 20].forEach((x) => fillRect(g, x, -40, pad, 36, trim));
      fillRect(g, -20, -40, 40, 5, trim);
      steppedGable(g, 0, -44, 34, 22, 6, roof);
      steppedGable(g, 0, -44, 34, 22, 6, roofL); // 二次叠画保持亮线（无害）
      fillCircle(g, 0, -58, 4, 0xf0c14a);
    } else if (k === "gate") {
      // 城门：石拱
      fillRound(g, -30, -46, 18, 58, 3, wall);
      fillRound(g, 12, -46, 18, 58, 3, wall);
      fillRound(g, -30, -52, 60, 16, 4, shade(wall, 0.82));
      for (let i = 0; i < 5; i++) fillRect(g, -26 + i * 12, -50, 7, 5, shade(wall, 1.15));
      fillRect(g, -30, -6, 60, 4, roofD);
      fillRect(g, -30, -46, 60, 4, roofD);
      fillRect(g, -22, -40, 6, 34, shade(wall, 0.85));
      fillRect(g, 16, -40, 6, 34, shade(wall, 0.85));
    } else if (k === "tower") {
      const bodyW = 56, bodyH = 34, top = -bodyH - 26;
      // 塔身
      fillRect(g, -18, top - 26, 36, 30, shade(wall, 0.9));
      fillRect(g, -18, top - 26, 36, 30, wallL); fillRect(g, -18, top - 26, 36, 30, wall);
      fillRect(g, -18, top - 30, 36, 6, roofD);
      steppedGable(g, 0, top - 30, 22, 18, 5, roof);
      // 主体
      fillRect(g, -bodyW / 2, top, bodyW, bodyH, wall);
      fillRect(g, -bodyW / 2, top, bodyW, 5, wallL);
      fillRect(g, -bodyW / 2, -6, bodyW, 6, wallD);
      fillRect(g, -bodyW / 2 - 4, top - 5, bodyW + 8, 7, roof);
      fillRect(g, -bodyW / 2 - 4, top - 5, bodyW + 8, 2, roofL);
      fillRect(g, -12, -18, 12, 18, shade(wall, 0.6));       // 门
      fillRect(g, -16, -21, 20, 3, roofD);
      fillRect(g, -22, top + 8, 12, 12, 0x2a2018); fillRect(g, -21, top + 9, 10, 10, win);
      fillRect(g, 10, top + 8, 12, 12, 0x2a2018); fillRect(g, 11, top + 9, 10, 10, win);
      drawEmblem(g, spec.emblem, 0, top + 14, spec.emblem === "clock" ? 0xffffff : shade(wall, 1.3));
      if (spec.emblem === "clock") { fillCircle(g, 0, top + 14, 10, 0x24303a); fillCircle(g, 0, top + 14, 8, 0xf6f2e6); fillRect(g, -1, top + 9, 2, 6, 0x24303a); fillRect(g, -1, top + 13, 6, 2, 0x24303a); }
    } else if (k === "barn") {
      const bw = 76, bh = 40, top = -bh - 28;
      fillRect(g, -bw / 2, top, bw, bh, wall);
      fillRect(g, -bw / 2, top, bw, 5, wallL);
      fillRect(g, -bw / 2 - 6, top - 6, bw + 12, 8, roof);
      fillRect(g, -bw / 2 - 6, top - 6, bw + 12, 2, roofL);
      steppedGable(g, 0, top - 6, bw / 2 + 6, 24, 6, roof);
      steppedGable(g, 0, top - 6, bw / 2 + 6, 24, 6, roofL);
      // 大门（双开红棕）
      fillRect(g, -16, -26, 32, 26, 0x7a3526);
      fillRect(g, -15, -25, 30, 24, 0x9a4632);
      fillRect(g, -1, -25, 2, 24, trim);
      fillRect(g, -15, -14, 30, 2, trim);
      fillRect(g, -16, -28, 32, 3, trim);
      // 筒仓
      fillRound(g, 34, top - 6, 26, bh + 6, 6, 0xb9b2a2);
      fillRound(g, 35, top - 5, 24, bh + 4, 6, 0xd8d2c4);
      fillEllipse(g, 47, top - 5, 12, 6, 0x9a9384);
      fillRect(g, 40, top + 8, 14, 3, 0xb0a898); fillRect(g, 40, top + 20, 14, 3, 0xb0a898);
    } else if (k === "hall") {
      const bw = spec.wide ? 92 : 70, bh = (spec.storeys === 2 ? 50 : 34), top = -bh - 20;
      fillRect(g, -bw / 2, top, bw, bh, wall);
      fillRect(g, -bw / 2, top, bw, 5, wallL);
      fillRect(g, -bw / 2, -7, bw, 7, wallD);
      if (spec.roof === "flat") {                       // 平顶（事务所）：现代感 + 天线
        fillRect(g, -bw / 2 - 5, top - 9, bw + 10, 11, roof);
        fillRect(g, -bw / 2 - 5, top - 9, bw + 10, 3, roofL);
        fillRect(g, -bw / 2 - 7, top - 2, bw + 14, 4, roofD);
        fillRect(g, -2, top - 24, 3, 16, shade(wall, 0.7));
        fillCircle(g, -0.5, top - 25, 3, 0xd94f4f);
      } else if (spec.roof === "dome") {                // 穹顶（图书馆）
        fillCircle(g, 0, top - 2, bw / 2 + 4, roof);
        fillCircle(g, 0, top - 7, bw / 2 - 2, roofL);
        fillRect(g, -bw / 2 - 6, top - 2, bw + 12, 7, roofD);
        fillRect(g, -3, top - 2 - bw / 2 - 10, 6, 10, trim);
        fillCircle(g, 0, top - 2 - bw / 2 - 12, 4, 0xf0c14a);
        fillRect(g, -bw / 2 - 8, top + 2, bw + 16, 3, shade(wall, 1.1));
      } else {                                          // 山墙 + 三角楣（默认）
        fillRect(g, -bw / 2 - 6, top - 7, bw + 12, 9, shade(wall, 1.1));
        steppedGable(g, 0, top - 7, bw / 2 + 6, 20, 5, roof);
        steppedGable(g, 0, top - 7, bw / 2 + 6, 20, 5, roofL);
        fillRect(g, -bw / 2 - 8, top - 3, bw + 16, 4, roofD);
      }
      if (spec.columns) {
        for (let i = 0; i < 4; i++) {
          const x = -bw / 2 + 8 + i * ((bw - 16) / 3) - 3;
          fillRect(g, x, top + 4, 6, bh - 8, trim);
          fillRect(g, x - 1, top + 3, 8, 3, shade(trim, 0.9));
        }
      } else {
        fillRect(g, -bw / 2 + 12, top + 9, 14, 13, win);
        fillRect(g, bw / 2 - 26, top + 9, 14, 13, win);
      }
      fillRect(g, -12, -18, 24, 18, shade(wall, 0.6));
      fillRect(g, -14, -20, 28, 3, roofD);
      drawEmblem(g, spec.emblem, 0, top + 2, 0xffffff);
      if (spec.storeys === 2) {
        fillRect(g, -bw / 2, top + bh - 16, bw, 3, shade(wall, 0.82));                 // 楼层分隔线
        fillRect(g, -bw / 2 + 12, top + 22, 14, 12, 0x2a2018); fillRect(g, -bw / 2 + 13, top + 23, 12, 10, win);
        fillRect(g, bw / 2 - 26, top + 22, 14, 12, 0x2a2018); fillRect(g, bw / 2 - 25, top + 23, 12, 10, win);
        fillRect(g, -16, top + 1, 32, 4, shade(wall, 1.12));                          // 檐口
      }
    } else if (k === "workshop") {
      const bw = 62, bh = 34, top = -bh - 22;
      fillRect(g, -bw / 2, top, bw, bh, wall);
      fillRect(g, -bw / 2, top, bw, 5, wallL);
      fillRect(g, -bw / 2 - 5, top - 6, bw + 10, 8, roof);
      steppedGable(g, 0, top - 6, bw / 2, 22, 6, roof);
      fillRect(g, -bw / 2 - 5, top - 2, bw + 10, 3, roofD);
      fillRect(g, -14, -20, 14, 20, shade(wall, 0.6));       // 门
      fillRect(g, 8, top + 8, 16, 12, win);                  // 大窗
      fillRect(g, 8, top + 8, 1, 12, 0x2a2018); fillRect(g, 15, top + 8, 1, 12, 0x2a2018);
      // 烟囱 + 烟
      fillRect(g, 16, top - 30, 9, 16, shade(wall, 0.7));
      fillEllipse(g, 21, top - 36, 5, 4, 0xdddddd, 0.55);
      fillEllipse(g, 26, top - 44, 6, 5, 0xdddddd, 0.4);
    } else if (k === "stalls") {
      // 市集：横跨大条纹遮阳棚 + 木摊架 + 果蔬货箱
      fillRect(g, -40, -8, 80, 10, 0x7a5630);                 // 摊架
      fillRect(g, -40, -8, 80, 3, 0x94693c);
      fillRect(g, -36, -8, 4, 10, 0x5f3d1f); fillRect(g, 32, -8, 4, 10, 0x5f3d1f);
      for (let i = 0; i < 8; i++) {                           // 条纹棚（亮色，夜间也醒目）
        fillRect(g, -44 + i * 11, -30, 11, 16, i % 2 ? 0xfbf6e8 : 0xf2d98a);
        fillRect(g, -44 + i * 11, -33, 11, 3, roof);
        fillRect(g, -44 + i * 11, -30, 11, 2, 0xffffff, 0.25);
      }
      fillRect(g, -42, -30, 3, 24, 0x6a4a26); fillRect(g, 39, -30, 3, 24, 0x6a4a26);
      fillRect(g, -30, -20, 12, 12, 0x9c6b34); fillRect(g, -30, -20, 12, 3, 0xba8348);   // 木箱
      fillRect(g, -12, -18, 10, 10, 0xd05a3a);               // 番茄
      fillRect(g, 4, -19, 11, 11, 0xd9a83c);                 // 南瓜
      fillRect(g, 22, -18, 10, 10, 0x8fbf4a);                // 青菜
    } else {
      // cottage（村舍 / 面包房 / 咖啡馆）
      const bw = 56, bh = 34, top = -bh - 24;
      fillRect(g, -bw / 2, top, bw, bh, wall);
      fillRect(g, -bw / 2, top, bw, 5, wallL);
      fillRect(g, -bw / 2, -6, bw, 6, wallD);
      fillRect(g, -bw / 2 - 5, top - 6, bw + 10, 8, roof);
      steppedGable(g, 0, top - 6, bw / 2 + 5, 24, 6, roof);
      steppedGable(g, 0, top - 6, bw / 2 + 5, 24, 6, roofL);
      fillRect(g, -bw / 2 - 5, top - 1, bw + 10, 3, roofD);
      fillRect(g, -20, top + 9, 12, 12, win); fillRect(g, 8, top + 9, 12, 12, win);
      fillRect(g, -20, top + 9, 1, 12, 0x2a2018); fillRect(g, 8, top + 9, 1, 12, 0x2a2018);
      fillRect(g, -11, -18, 22, 18, shade(wall, 0.6));
      fillRect(g, -13, -20, 26, 3, roofD);
      if (spec.chimney) {
        fillRect(g, 14, top - 26, 8, 14, shade(wall, 0.7));
        fillEllipse(g, 18, top - 33, 6, 5, 0xe8e8e8, 0.75);
        fillEllipse(g, 24, top - 41, 7, 6, 0xe8e8e8, 0.5);
        fillEllipse(g, 31, top - 50, 8, 7, 0xe8e8e8, 0.32);
      }
      if (spec.awning) {                                             // 门头雨棚
        for (let i = 0; i < 5; i++) { fillRect(g, -13 + i * 6, -20, 6, 9, i % 2 ? 0xf2ead6 : wall); }
        fillRect(g, -15, -22, 30, 2, roof);
      }
      drawEmblem(g, spec.emblem, 0, top + 3, 0xffffff);
    }

    c.addChild(g);

    // 名称牌（只留名称；容量等详情由 shell 侧栏承载）
    const label = placeLabel(PIXI, place, st, 22);
    c.addChild(label);
    // 供 town 做"标签避让"：建筑上方可用位置（按原型估算屋顶高度）
    const abY = ({ tower: -102, barn: -84, workshop: -72, cottage: -74, hall: -70,
      stalls: -54, gate: -68, gazebo: -74, fountain: -46 }[k]) || -74;
    c.__label = label; c.__labelAboveY = abY;

    // 悬挂招牌（牌面用类别色，招牌支架）
    if (k !== "fountain" && k !== "gazebo" && k !== "gate") {
      fillRect(g, 27, -34, 3, 15, 0x5a3f22);                 // 支架
      fillRound(g, 13, -50, 32, 17, 3, 0x3f2c18);            // 牌框
      fillRound(g, 14, -49, 30, 15, 3, win);                 // 牌面
      fillRect(g, 17, -44, 24, 2, shade(wall, 0.65));        // 牌面字（示意）
      fillRect(g, 17, -40, 17, 2, shade(wall, 0.8));
      fillCircle(g, 16, -46, 1.5, shade(wall, 0.6));
      fillCircle(g, 41, -46, 1.5, shade(wall, 0.6));
    }

    // 夜间发光点（窗光 / 门光），由 town 的 lightLayer 使用
    c.__smoke = [];
    if (k === "cottage" && spec.chimney) c.__smoke.push([20, -88]);
    if (k === "workshop") c.__smoke.push([22, -92]);
    const gl = [];
    if (k === "cottage") gl.push([-14, -42, 7], [14, -42, 7]);
    else if (k === "tower") gl.push([-16, -45, 7], [16, -45, 7]);
    else if (k === "hall") gl.push([-20, -42, 7], [20, -42, 7]);
    else if (k === "workshop") gl.push([16, -44, 8]);
    else if (k === "barn") gl.push([0, -16, 8]);
    else if (k === "stalls") gl.push([-22, -28, 6], [24, -28, 6]);
    c.__glows = gl;

    c.__placeId = place.place_id;
    return c;
  }

  // ========================================================================
  //  角色
  // ========================================================================
  function makeAgentSprite(PIXI, agentId, textureAlive, textureDead) {
    const c = new PIXI.Container();
    // 活跃高亮环（当前回合有动作/发言的角色）
    const ring = new PIXI.Graphics();
    ring.lineStyle(3, 0xffe08a, 0.95); ring.drawEllipse(0, 20, 13, 6); ring.lineStyle(0, 0, 0);
    ring.visible = false;
    c.addChild(ring);

    const shadow = new PIXI.Graphics();
    fillEllipse(shadow, 0, 20, 16, 6, 0x000000, 0.30);     // 接触影加重（T112：全景下"落地"更明确）
    fillEllipse(shadow, 0, 20, 11, 4, 0x000000, 0.26);
    c.addChild(shadow);

    // 夜间轮廓光（活跃角色：暖白光晕，避免贴在暗建筑上糊掉）
    const halo = new PIXI.Graphics();
    fillEllipse(halo, 0, 2, 14, 18, 0xffe9b0, 0.42);
    fillEllipse(halo, 0, 2, 9, 12, 0xfff8e0, 0.36);
    halo.visible = false;
    c.addChild(halo);

    const BASE = 0.58;                 // T112：放大（原 0.46）——全景下更可见
    // 描边：深色剪影垫在背后（略大 16%），使角色在任何底色/建筑旁都有清晰轮廓
    const outline = new PIXI.Sprite(textureAlive);
    outline.anchor.set(0.5, 1); outline.y = 20; outline.scale.set(BASE * 1.16);
    outline.tint = 0x141a24; outline.alpha = 0.9;
    c.addChild(outline);

    const sprite = new PIXI.Sprite(textureAlive);
    sprite.anchor.set(0.5, 1);
    sprite.y = 20;
    sprite.scale.set(BASE);            // 48x96 源 → 约 44px 全身
    c.addChild(sprite);

    // 自发光「提灯」（夜间对所有存活角色可见，成为暗处焦点）
    const lantern = new PIXI.Graphics();
    fillCircle(lantern, 10, -2, 6, 0xffcf6a, 0.26);
    fillCircle(lantern, 10, -2, 3.5, 0xffe6a0, 0.5);
    fillCircle(lantern, 10, -2, 1.6, 0xfff6d0, 0.9);
    lantern.visible = false;
    c.addChild(lantern);

    // 墓碑（死者改用墓碑，不再叠灰人）
    const tomb = new PIXI.Graphics();
    fillEllipse(tomb, 0, 20, 12, 5, 0x000000, 0.30);
    fillRound(tomb, -9, -16, 18, 24, 6, 0x8f949b);
    fillRound(tomb, -7, -13, 14, 20, 5, 0xa8adb4);
    fillRect(tomb, -2, -9, 4, 13, 0x6f747a); fillRect(tomb, -7, -4, 14, 4, 0x6f747a);
    tomb.visible = false;
    c.addChild(tomb);

    const label = new PIXI.Text(agentId, {
      fontFamily: "ui-monospace,monospace", fontSize: 11, fill: 0xffffff,
      stroke: 0x0b0e12, strokeThickness: 4,
    });
    label.anchor.set(0.5, 0); label.y = 22; c.addChild(label);

    let bubble = null;
    function setStatus(status) {
      if (status === "dead") {
        sprite.visible = false; tomb.visible = true; outline.visible = false;
        ring.visible = false; halo.visible = false; lantern.visible = false;
      } else {
        sprite.visible = true; tomb.visible = false; outline.visible = true;
        sprite.texture = textureAlive; sprite.tint = 0xffffff; outline.texture = textureAlive;
      }
    }
    function setBubble(text) {
      if (bubble) { c.removeChild(bubble); bubble.destroy(); bubble = null; }
      if (!text) return;
      text = String(text).replace(/\s+/g, " ").trim();
      if (text.length > 40) text = text.slice(0, 38) + "\u2026";
      if (!text) return;
      bubble = new PIXI.Text(text, {
        fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif', fontSize: 11,
        fill: 0x101418, backgroundColor: 0xf2f6fb, padding: 4,
        wordWrap: true, wordWrapWidth: 150, align: "center",
      });
      bubble.anchor.set(0.5, 1); bubble.y = -14; c.addChild(bubble);
    }
    function setHighlight(on) { ring.visible = !!on; halo.visible = !!on; }
    function setLabel(on) { label.visible = !!on; }
    return { container: c, setStatus, setBubble, setHighlight, setLabel, sprite, outline, shadow, ring, halo, lantern, tomb };
  }


  // ========================================================================
  //  事件视觉词汇（T77，按 T76 obs-console-ux-spec §7 回填；单一真源）
  //  用法：window.HITTSprites.FAMILY_COLOR / SEMANTIC_COLOR / EVENT_STYLE / EVENT_FAMILY / EVENT_ICONS
  //  图标 = pixel-asset-artist 的资产 key（缺图时前端退化为"族色圆点 + 首字母"）。
  // ========================================================================
  const FAMILY_COLOR = { ECON: "#E8B84B", LIFE: "#6FCF6B", SOCIAL: "#B07CE8", COGN: "#5CC8FF", SYS: "#8B98AB", WARN: "#E4572E" };
  const SEMANTIC_COLOR = { born: "#6FCF6B", died: "#D9534F", revived: "#7EC8FF", warn: "#E4572E" };
  const EVENT_STYLE = {
    MONEY_MINTED: { family: "ECON", icon: "mint", level: "audit", color: FAMILY_COLOR.ECON },
    INIT_ENDOW: { family: "ECON", icon: "coin-init", level: "detail", color: FAMILY_COLOR.ECON },
    TRANSFER: { family: "ECON", icon: "coin-arrow", level: "narrative", color: FAMILY_COLOR.ECON },
    MARKET_TRADE: { family: "ECON", icon: "shop", level: "narrative", color: FAMILY_COLOR.ECON },
    DEPOSIT: { family: "ECON", icon: "bank-in", level: "detail", color: FAMILY_COLOR.ECON },
    WITHDRAW: { family: "ECON", icon: "bank-out", level: "detail", color: FAMILY_COLOR.ECON },
    LOAN_ISSUED: { family: "ECON", icon: "loan", level: "narrative", color: FAMILY_COLOR.ECON },
    LOAN_REPAY: { family: "ECON", icon: "loan-repay", level: "detail", color: FAMILY_COLOR.ECON },
    INTEREST_CHARGED: { family: "ECON", icon: "percent", level: "detail", color: FAMILY_COLOR.ECON },
    LOAN_DEFAULT: { family: "ECON", icon: "loan-broken", level: "narrative", color: SEMANTIC_COLOR.warn },
    TAX_LEVIED: { family: "ECON", icon: "tax", level: "narrative", color: FAMILY_COLOR.ECON },
    UBI_PAID: { family: "ECON", icon: "gift-ubi", level: "narrative", color: FAMILY_COLOR.ECON },
    PENALTY_APPLIED: { family: "ECON", icon: "gavel", level: "narrative", color: FAMILY_COLOR.ECON },
    REVIVE_FEE_PAID: { family: "ECON", icon: "revive-fee", level: "narrative", color: FAMILY_COLOR.ECON },
    DROPPED: { family: "ECON", icon: "drop", level: "detail", color: FAMILY_COLOR.ECON },
    MONEY_BURNED: { family: "ECON", icon: "burn", level: "audit", color: FAMILY_COLOR.ECON },
    WORLD_INIT: { family: "LIFE", icon: "world", level: "audit", color: FAMILY_COLOR.LIFE },
    AGENT_BORN: { family: "LIFE", icon: "born", level: "narrative", color: SEMANTIC_COLOR.born },
    METABOLISM: { family: "LIFE", icon: "metabolism", level: "detail", color: FAMILY_COLOR.LIFE },
    STATE_CHANGE: { family: "LIFE", icon: "state", level: "narrative", color: FAMILY_COLOR.LIFE },
    AGENT_DIED: { family: "LIFE", icon: "skull", level: "narrative", color: SEMANTIC_COLOR.died },
    AGENT_REVIVED: { family: "LIFE", icon: "revive", level: "narrative", color: SEMANTIC_COLOR.revived },
    ECONOMY_INVARIANT_VIOLATION: { family: "LIFE", icon: "alert", level: "audit", color: SEMANTIC_COLOR.warn },
    MSG_PUBLIC: { family: "SOCIAL", icon: "speech-public", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    MSG_DM: { family: "SOCIAL", icon: "speech-dm", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    MSG_GROUP: { family: "SOCIAL", icon: "speech-group", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    RELATION_CHANGE: { family: "SOCIAL", icon: "relation", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    RELATION_ENCOUNTER: { family: "SOCIAL", icon: "meet", level: "detail", color: FAMILY_COLOR.SOCIAL },
    NORM_PROPOSED: { family: "SOCIAL", icon: "norm-new", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    NORM_ADOPTED: { family: "SOCIAL", icon: "norm-ok", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    NORM_VIOLATED: { family: "SOCIAL", icon: "norm-bad", level: "narrative", color: SEMANTIC_COLOR.warn },
    OFFER_CREATED: { family: "SOCIAL", icon: "offer", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    OFFER_ACCEPTED: { family: "SOCIAL", icon: "offer-ok", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    OFFER_REJECTED: { family: "SOCIAL", icon: "offer-no", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    OFFER_COUNTERED: { family: "SOCIAL", icon: "offer-alt", level: "detail", color: FAMILY_COLOR.SOCIAL },
    OFFER_EXPIRED: { family: "SOCIAL", icon: "offer-exp", level: "detail", color: FAMILY_COLOR.SOCIAL },
    CONFLICT_STARTED: { family: "SOCIAL", icon: "clash", level: "narrative", color: SEMANTIC_COLOR.warn },
    CONFLICT_RESOLVED: { family: "SOCIAL", icon: "clash-ok", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    GROUP_CREATED: { family: "SOCIAL", icon: "group", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    GROUP_JOINED: { family: "SOCIAL", icon: "group", level: "detail", color: FAMILY_COLOR.SOCIAL },
    GROUP_LEFT: { family: "SOCIAL", icon: "group", level: "detail", color: FAMILY_COLOR.SOCIAL },
    ROLE_CHANGE: { family: "SOCIAL", icon: "role", level: "narrative", color: FAMILY_COLOR.SOCIAL },
    TAG_EMITTED: { family: "SOCIAL", icon: "tag", level: "detail", color: FAMILY_COLOR.SOCIAL },
    PLACE_MOVE: { family: "COGN", icon: "walk", level: "narrative", color: FAMILY_COLOR.COGN },
    PLACE_ARRIVED: { family: "COGN", icon: "pin", level: "detail", color: FAMILY_COLOR.COGN },
    SCHEDULE_PLANNED: { family: "COGN", icon: "calendar", level: "detail", color: FAMILY_COLOR.COGN },
    SCHEDULE_REVISED: { family: "COGN", icon: "calendar-edit", level: "detail", color: FAMILY_COLOR.COGN },
    ACTIVITY_STARTED: { family: "COGN", icon: "act-play", level: "narrative", color: FAMILY_COLOR.COGN },
    ACTIVITY_COMPLETED: { family: "COGN", icon: "act-done", level: "detail", color: FAMILY_COLOR.COGN },
    ACTIVITY_INTERRUPTED: { family: "COGN", icon: "act-stop", level: "detail", color: FAMILY_COLOR.COGN },
    NEED_UPDATE: { family: "COGN", icon: "need", level: "detail", color: FAMILY_COLOR.COGN },
    GOAL_SET: { family: "COGN", icon: "goal", level: "narrative", color: FAMILY_COLOR.COGN },
    GOAL_PROGRESS: { family: "COGN", icon: "goal-bar", level: "detail", color: FAMILY_COLOR.COGN },
    GOAL_ACHIEVED: { family: "COGN", icon: "goal-ok", level: "narrative", color: FAMILY_COLOR.COGN },
    GOAL_ABANDON: { family: "COGN", icon: "goal-x", level: "detail", color: FAMILY_COLOR.COGN },
    MEMORY_WRITE: { family: "COGN", icon: "mem", level: "audit", color: FAMILY_COLOR.COGN },
    MEMORY_RETRIEVE: { family: "COGN", icon: "mem-search", level: "audit", color: FAMILY_COLOR.COGN },
    MEMORY_REFLECT: { family: "COGN", icon: "reflect", level: "narrative", color: FAMILY_COLOR.COGN },
    OBSERVATION: { family: "COGN", icon: "eye", level: "audit", color: FAMILY_COLOR.COGN },
    SEED_EVENT: { family: "COGN", icon: "seed", level: "narrative", color: FAMILY_COLOR.COGN },
    SKILL_PRACTICE: { family: "COGN", icon: "skill", level: "detail", color: FAMILY_COLOR.COGN },
    SKILL_LEVEL_UP: { family: "COGN", icon: "skill-up", level: "narrative", color: FAMILY_COLOR.COGN },
    SKILL_OUTPUT: { family: "COGN", icon: "craft", level: "detail", color: FAMILY_COLOR.COGN },
    SCORE_POSTED: { family: "COGN", icon: "trophy", level: "narrative", color: FAMILY_COLOR.COGN },
    RANKING_EMITTED: { family: "COGN", icon: "trophy", level: "narrative", color: FAMILY_COLOR.COGN },
    LLM_JUDGMENT: { family: "SYS", icon: "judge", level: "detail", color: FAMILY_COLOR.SYS },
    NARRATIVE: { family: "SYS", icon: "book", level: "narrative", color: FAMILY_COLOR.SYS },
    LLM_CALL: { family: "SYS", icon: "cpu", level: "audit", color: FAMILY_COLOR.SYS },
    TIME_MARK: { family: "SYS", icon: "clock", level: "audit", color: FAMILY_COLOR.SYS },
    TURN_SEAL: { family: "SYS", icon: "seal", level: "audit", color: FAMILY_COLOR.SYS },
    INTENT_REJECTED: { family: "SYS", icon: "reject", level: "detail", color: SEMANTIC_COLOR.warn },
    SYSTEM_ERROR: { family: "SYS", icon: "error", level: "narrative", color: SEMANTIC_COLOR.warn },
  };
  const EVENT_FAMILY = {};
  Object.keys(EVENT_STYLE).forEach((k) => { EVENT_FAMILY[k] = EVENT_STYLE[k].family; });
  // 供 pixel-asset-artist 出 24/32px 像素图标的 key 清单（唯一，来自 T76 §3+§7）
  const EVENT_ICONS = ["act-done", "act-play", "act-stop", "alert", "bank-in", "bank-out", "book", "born", "burn", "calendar", "calendar-edit", "clash", "clash-ok", "clock", "coin-arrow", "coin-init", "cpu", "craft", "drop", "error", "eye", "gavel", "gift-ubi", "goal", "goal-bar", "goal-ok", "goal-x", "group", "judge", "loan", "loan-broken", "loan-repay", "meet", "mem", "mem-search", "metabolism", "mint", "need", "norm-bad", "norm-new", "norm-ok", "offer", "offer-alt", "offer-exp", "offer-no", "offer-ok", "percent", "pin", "reflect", "reject", "relation", "revive", "revive-fee", "role", "seal", "seed", "shop", "skill", "skill-up", "skull", "speech-dm", "speech-group", "speech-public", "state", "tag", "tax", "trophy", "walk", "world"];

  // 事件图标图集（T72 资产库，pixel-asset-artist 生成）。
  // 结构与 audit.js `_iconHtml()` 期待的 `HITTSprites.ICON_ATLAS = {url,size,cols,index}` 完全一致；
  // index 键与 EVENT_STYLE[].icon 一一对齐（经核对 69/69，无缺口、无孤立）。缺图时前端退化为族色圆点。
  const ICON_ATLAS = {
    url: "assets/generated/icons_atlas.png",
    size: 32, cols: 12,
    index: {
      mint: 0, "coin-init": 1, "coin-arrow": 2, shop: 3, "bank-in": 4, "bank-out": 5, loan: 6, "loan-repay": 7,
      percent: 8, "loan-broken": 9, tax: 10, "gift-ubi": 11, gavel: 12, "revive-fee": 13, drop: 14, burn: 15,
      world: 16, born: 17, metabolism: 18, state: 19, skull: 20, revive: 21, alert: 22, "speech-public": 23,
      "speech-dm": 24, "speech-group": 25, relation: 26, meet: 27, "norm-new": 28, "norm-ok": 29, "norm-bad": 30,
      offer: 31, "offer-ok": 32, "offer-no": 33, "offer-alt": 34, "offer-exp": 35, clash: 36, "clash-ok": 37,
      group: 38, role: 39, tag: 40, walk: 41, pin: 42, calendar: 43, "calendar-edit": 44, "act-play": 45,
      "act-done": 46, "act-stop": 47, need: 48, goal: 49, "goal-bar": 50, "goal-ok": 51, "goal-x": 52, mem: 53,
      "mem-search": 54, reflect: 55, eye: 56, seed: 57, skill: 58, "skill-up": 59, craft: 60, trophy: 61,
      judge: 62, book: 63, cpu: 64, clock: 65, seal: 66, reject: 67, error: 68,
    },
  };

  // ========================================================================
  //  事件卡接线（T118 门控版）：**不再无条件 type→slug**。
  //  依据：v2/evidence/event_card_mapping_revised.json / _audit.md（obs-stats-dev）。
  //  原则：机械事件（RELATION_CHANGE/NEED_UPDATE/PLACE_MOVE/ACTIVITY_*/LLM_JUDGMENT）
  //        **默认不配卡**；卡片改由**活动 template / 语义条件**驱动；**宁可不显示，也不显示错的**。
  //  由 audit.js::_cardHtml 消费（同一门控）。
  // ========================================================================
  const EVENT_CARD_BASE = "assets/generated/event_cards_hand/";
  // (a) 无条件（语义明确）
  const EVENT_CARDS = {
    SKILL_PRACTICE: "skill-practice",     // E10
    OFFER_REJECTED: "polite-reject",      // E11
    ROLE_CHANGE: "passion-salary",        // E12（仅 ROLE_CHANGE；OFFER_CREATED 已移出）
    NORM_PROPOSED: "group-proposal",      // E13
    OFFER_COUNTERED: "counter-propose",   // E15
    CONFLICT_STARTED: "power-conflict",   // E17
    CONFLICT_RESOLVED: "power-conflict",
  };
  // (b) 活动/事件 payload.template → slug（ACTIVITY_* 等由此驱动）
  //   ★ 反造假：**不含 `rel_accept`**——rel-acceptance/diff-scoring 当前门控评估为 0
  //   （引擎缺 accept/reject 与 respect/affection 维度），**如实保留为 0，不设兜底**；life 补维度后自然点亮。
  const EVENT_CARDS_BY_TEMPLATE = {
    mentorship: "mentorship", creative_collab: "creative-collab", academic_collab: "academic-collab",
    combat_training: "combat-training", select_location: "select-location", gift: "gift-giving",
    savings: "saving-money", whisper: "whispered-comm",
    ice_break: "ice-breaking", rel_maintain: "rel-maintain",
  };
  // (c) 语义条件门控阈值/开关（audit.js::eventCardSlug 消费；**仅凭事件字段判定，无隐藏状态**）
  const EVENT_CARD_GATE = {
    SCARCITY_THETA: 0.5,
    // 是否把"裸语义事件"（TRANSFER{reason=gift} / DEPOSIT/WITHDRAW）也配卡（§2 字面"或"=true）。
    // 设为 false 则**仅 template 驱动**（gift/saving 只认 ACTIVITY_*{template=...}）。
    // 待 T123 收敛口径；默认按 §2 并集 = true。
    INCLUDE_RAW_SEMANTIC: true,
  };

  global.HITTSprites = {
    TILE, TILESET_COLS, TILES, DECOR, PEEPS_FRAMES, PEEPS_COLS, PLACE_SIZE,
    CATEGORY_STYLE, styleFor, slice, peepsTexture, hash2, pick, SPR, spriteTex, PEEPS, FAMILY_COLOR, SEMANTIC_COLOR, EVENT_STYLE, EVENT_FAMILY, EVENT_ICONS, ICON_ATLAS,
    EVENT_CARD_BASE, EVENT_CARDS, EVENT_CARDS_BY_TEMPLATE, EVENT_CARD_GATE,
    shade, mix, fillRect, fillRound, strokeRound, fillCircle, fillEllipse, steppedGable,
    BUILDING_SPEC, makePlaceSprite, makeAgentSprite,
  };
})(window);
