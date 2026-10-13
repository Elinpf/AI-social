/* town.js — PixiJS 像素小镇渲染层（只读，art-director 视觉重构版）。
 * 素材来自 AI Town（a16z-infra/ai-town, MIT）的地形 tileset 与角色表（见 NOTICE）；
 * 地形/装饰/建筑按 config 拓扑 + 固定哈希**确定性**生成，可复现，不依赖运行时随机。
 * 仍严格「只读日志/config」，不写世界、不参与判定。
 *
 * 渲染分层（自下而上，保持 smoke_test 断言的 ground < place < agent）：
 *   1 foundation 纯色底
 *   2 grass      无缝草地（低频色斑，无 checkerboard）
 *   3 features   道路 / 广场 / 水面 / 农田（程序化像素）
 *   4 decor      树/灌木/石/花 + 道具（路灯/长椅/围栏/招牌/花坛）
 *   5 places     建筑（placeLayer）
 *   6 agents     角色（agentLayer）
 */
(function (global) {
  "use strict";

  const W = global.HITTSprites;
  const TILE = W.TILE;
  const fillRect = W.fillRect, fillEllipse = W.fillEllipse, fillCircle = W.fillCircle;
  const fillRound = W.fillRound;

  // 素材加载：优先显式 Image（返回 BaseTexture，避开 Assets.load 在部分无头 Chromium 下
  // 不 resolve / 返回 Texture 的问题）；无 Image（Node smoke_test）时回退 PIXI.Assets。
  function texFromURL(P, url) {
    if (typeof Image !== "undefined") {
      return new Promise((resolve, reject) => {
        const img = new Image();
        try { img.crossOrigin = "anonymous"; } catch (e) { /* ignore */ }
        img.onload = () => resolve(P.BaseTexture.from(img));
        img.onerror = () => reject(new Error("素材加载失败: " + url));
        img.src = url;
      });
    }
    if (P.Assets && P.Assets.load) return P.Assets.load(url);
    return Promise.reject(new Error("无可用图片加载器: " + url));
  }

  // 地面/道路配色（程序化）
  const C = {
    bg: 0x2b3d24,
    dirt: 0xa88f63, dirtD: 0x7e6a4a, dirtL: 0xc0ac86,   // 支路土路（压饱和）
    street: 0xa9a191, streetD: 0x7d766a, streetL: 0xc6bfae, // 主街压实土/浅石
    cobble: 0x9c948a, cobbleD: 0x6f6960, cobbleL: 0xc2b9aa,
    sand: 0xd9c48c, sandD: 0xb9a066,
    waterD: 0x2c5b86, soil: 0x8a5f34, soilD: 0x6a4626,
  };

  // ==========================================================================
  //  LAYOUT（T71）：仿 Stardew 的有机小镇布局 —— 纯前端展示层数据。
  //  * 只决定"画在哪、路怎么走、区怎么分"；**不触碰** engine 的 config/topology.json
  //    与其 travel_ticks（引擎已冻结，改它会变 engine_version 指纹）。
  //  * place 集合与 id 不变（仍 17 处），前端按 place_id 渲染、可渲染任意日志。
  //  坐标：世界像素（960x720）。
  // ==========================================================================
  const LAYOUT = {
    // 世界尺寸（前端展示层）：1440x1080（= T70 提案 960x720 的 1.5x，为留白放大）
    WORLD: { width: 1440, height: 1080 },
    // 街道（T70 方案 ×1.5）：唯一东西主街 + 南北仪式轴 + 错开的北/南巷
    MAINS: [
      { a: [120, 630], b: [1230, 630], w: 3 },  // 东西主街（西端跨石桥，东端出镇）
      { a: [705, 375], b: [705, 983], w: 2 },   // 南北仪式轴（市政厅→广场→城门）
      { a: [495, 375], b: [1170, 375], w: 1 },  // 北巷（礼堂↔市政厅↔工坊区）
      { a: [345, 840], b: [975, 840], w: 1 },   // 南巷（图书馆↔住宅↔社区↔学校）
    ],
    NODES: {
      residence:        [540, 795],   // 南巷·沿街
      farm:             [270, 255],   // 西北 河岸农田（郊野）
      workshop:         [1140, 450],  // 东缘 生产带
      kitchen:          [1043, 503],  // 东缘 生产带（与工坊相邻）
      clinic:           [1140, 780],  // 东缘 服务
      school:           [930, 885],   // 东南（邻住宅）
      office:           [1080, 585],  // 主街东段（近出镇口）
      market:           [840, 585],   // 主街北侧·广场东
      bank:             [945, 690],   // 主街南侧
      plaza:            [705, 630],   // 广场（主街×中轴交点·加宽）
      town_hall:        [705, 375],   // 中轴北端·对景焦点
      library:          [375, 780],   // 西南（邻公园/住宅）
      community_center: [770, 855],   // 南巷·中轴旁
      cafe:             [570, 690],   // 主街南侧·广场西
      park:             [450, 600],   // 主街北侧·临河口袋公园
      hall:             [540, 330],   // 北巷西侧
      gate:             [705, 983],   // 中轴南端·端景
    },
    RIVER: { pts: [[140, 60], [125, 330], [150, 570], [150, 645], [125, 900], [140, 1050]], half: 45 },
    POND: { x: 320, y: 700, rx: 90, ry: 55 },
    FARM_PLOTS: [{ x: 200, y: 300, w: 240, h: 150 }],
    // 斜向碎石小径（去网格感）
    DIAGS: [
      { a: [450, 600], b: [560, 690] },
      { a: [840, 585], b: [705, 630] },
      { a: [1140, 470], b: [1230, 630] },
      { a: [375, 780], b: [495, 630] },
    ],
  };

  class Town {
    constructor(hostEl, places, topology) {
      this.host = hostEl;
      this.places = places;
      this.topology = topology;
      this.layout = LAYOUT;
      // 位置改用前端 LAYOUT（保留 topology 的其它字段如 ring 作为回退）
      this.nodeById = {};
      topology.nodes.forEach((n) => {
        const p = LAYOUT.NODES[n.place_id];
        this.nodeById[n.place_id] = p ? Object.assign({}, n, { x: p[0], y: p[1] }) : n;
      });
      this.placeById = {};
      places.forEach((p) => { this.placeById[p.place_id] = p; });

      const PIXI = global.PIXI;
      this.world = LAYOUT.WORLD;
      this.app = new PIXI.Application({
        width: this.world.width,
        height: this.world.height,
        backgroundColor: C.bg,
        antialias: false,
      });
      this.host.appendChild(this.app.view);
      this._fit();

      this.worldLayer = new PIXI.Container();
      this.app.stage.addChild(this.worldLayer);

      this.groundLayer = new PIXI.Container();
      this.placeLayer = new PIXI.Container();
      this.landmarkLayer = new PIXI.Container();   // 地标（T124）：place 之上、agent 之下（保持 ground<place<agent 相对序）
      this.agentLayer = new PIXI.Container();
      this.worldLayer.addChild(this.groundLayer);
      this.worldLayer.addChild(this.placeLayer);
      this.worldLayer.addChild(this.landmarkLayer);
      this.fgLayer = new PIXI.Container();         // T357-A 前景（place/landmark 之上、agent 之下）：近景遮挡剪影+暗角
      this.worldLayer.addChild(this.fgLayer);
      this.worldLayer.addChild(this.agentLayer);
      try { this.agentLayer.sortableChildren = true; } catch (e) { /* mock */ }

      // 光照层（最上层）：色温覆盖 + 夜间灯火。由 shell 通过 setLighting('day'|'dusk'|'night') 切换。
      this.lightLayer = new PIXI.Container();
      this.worldLayer.addChild(this.lightLayer);
      this._overlay = new PIXI.Graphics();
      this._glowLayer = new PIXI.Container();
      this._smokeLayer = new PIXI.Container();
      this.lightLayer.addChild(this._overlay);      // 先暗色覆盖
      this.lightLayer.addChild(this._glowLayer);    // 灯火画在其上
      this.lightLayer.addChild(this._smokeLayer);   // 炊烟（昼夜都可见，画在最上）
      this._lightMode = "day";
      this._frame = 0;

      // 氛围层（浅蓝冷调 + 细雪光点；确定性、可静态）——加在最后，保持 ground 仍是 children[0]
      this._snowLayer = new PIXI.Container();
      this.worldLayer.addChild(this._snowLayer);

      // 只读调试钩子：仅把实例暴露到 window.__HITT_TOWN__，供无头回归/核验**读取** placeLayer/agentLayer 等；
      // 不改变任何行为（无副作用、不参与渲染与判定）。由 tools/gate_render.js 使用。
      try { global.__HITT_TOWN__ = this; } catch (e) { /* ignore */ }
      this.agents = {};
      this.agentOrder = [];
      this.placeRadius = 54;          // 建筑避让半径（装饰不与建筑重叠）
      // T116 信息分层：landscape | default | info；_showAgentLabels 控制 NPC P+ID 默认隐藏
      this._viewMode = "default";
      this._showAgentLabels = false;
      this._placeLabels = [];
      this._cols = Math.ceil(this.world.width / TILE);
      this._rows = Math.ceil(this.world.height / TILE);
    }

    _fit() {
      const view = this.app.view;
      view.style.width = "100%";
      view.style.height = "100%";
      view.style.objectFit = "contain";
      try { view.style.imageRendering = "pixelated"; } catch (e) { /* ignore */ }
    }

    async load(assetsBase) {
      const P = global.PIXI;
      assetsBase = assetsBase || "assets/";
      this.tilesetBase = await texFromURL(P, assetsBase + "tileset.png");
      this.peepsBase = await texFromURL(P, assetsBase + "peeps.png");
      try { if (P.SCALE_MODES) { this.tilesetBase.scaleMode = P.SCALE_MODES.NEAREST; this.peepsBase.scaleMode = P.SCALE_MODES.NEAREST; } } catch (e) { /* ignore */ }

      // 资产库（T72/T84，接口冻结 v1）：可选接入；不可用时回退旧程序化渲染。
      // 在 Node(smoke) 下无 global.HITTAssets / fetch 相对路径不可用 → 自动回退。
      this._useLib = false;
      try {
        const A = global.HITTAssets;
        if (A && typeof A.load === "function" && A.meta && A.meta("place.residence")) {
          this._useLib = true;                              // 已被 shell 预加载
        } else if (A && typeof A.load === "function" && typeof fetch === "function" && typeof document !== "undefined") {
          await A.load(assetsBase + "assets_manifest.json", P);
          if (A.meta && A.meta("place.residence")) this._useLib = true;
        }
      } catch (e) { this._useLib = false; }
      if (this._useLib) this.placeRadius = 72;

      // 视觉变体（T107）：同一 place 的多张图，按 place id 哈希选一张；不新增 place id。
      this._assetsBase = assetsBase;
      this._variantTex = {};
      if (this._useLib) {
        try {
          const vm = global.HITTAssets.manifest && global.HITTAssets.manifest.placeVariants;
          if (vm) {
            const keys = Object.keys(vm);
            for (let k = 0; k < keys.length; k++) {
              const pid = keys[k], vs = vm[pid];
              if (vs && vs.length) {
                const idx = Math.floor(W.hash2(pid.length, pid.charCodeAt(0) || 0, 11) * vs.length) % vs.length;
                const bt = await texFromURL(P, assetsBase + vs[idx]);      // → BaseTexture
                try { if (P.SCALE_MODES) bt.scaleMode = P.SCALE_MODES.NEAREST; } catch (e) { /* ignore */ }
                this._variantTex[pid] = new P.Texture(bt);                 // Sprite 需要 Texture（勿直接塞 BaseTexture）

              }
            }
          }
        } catch (e) { /* ignore */ }
      }

      this._buildTerrain();
      this._buildDecorations();
      this._buildPlaces();
      this._buildLandmarks();
      this._buildForeground();     // T357-A：局部高对比结构（前景遮挡剪影 + 近景暗角）
      this._buildAtmosphere();
      // T116：URL `?view=landscape|default|info` 直接进对应信息分层（供景观截图/欣赏）
      try {
        if (typeof location !== "undefined" && location.search) {
          const v = new URLSearchParams(location.search).get("view");
          if (v === "landscape" || v === "info" || v === "default") this._viewMode = v;
        }
      } catch (e) { /* ignore */ }
      this.setMode(this._viewMode);
      return this;
    }

    // 资产库取值助手（浏览器路径；Node 回退时不启用）
    _libTex(id) { const A = global.HITTAssets; return (this._useLib && A && A.texture) ? A.texture(id) : null; }
    _libMeta(id) { const A = global.HITTAssets; return (this._useLib && A && A.meta) ? A.meta(id) : null; }

    // T269「没层次」：按世界深度 y 给**精灵**做三层色阶 tint（远冷 / 中中性 / 近暖）
    // —— 这是顶视图里最可读的"远"信号：连最大的视觉体量（建筑/地标）也参与分层，而非只有地面 overlay。
    _mix(r1, g1, b1, r2, g2, b2, i) {
      i = Math.max(0, Math.min(1, i));
      const r = Math.round(r1 + (r2 - r1) * i), g = Math.round(g1 + (g2 - g1) * i), b = Math.round(b1 + (b2 - b1) * i);
      return (r << 16) | (g << 8) | b;
    }
    _depthTint(y) {
      const t = Math.max(0, Math.min(1, y / (this.world.height || 1)));
      if (t < 0.34) return this._mix(255, 255, 255, 198, 210, 236, 0.40 * (1 - t / 0.34));  // 远：冷、去饱和
      if (t > 0.66) return this._mix(255, 255, 255, 255, 240, 210, 0.28 * ((t - 0.66) / 0.34)); // 近：暖
      return 0xffffff;                                                                         // 中：中性
    }

    // 库版建筑：精灵 + 接地软影 + 名称牌 + 夜间窗光点（保持 placeLayer 每场所 1 子节点）
    _libPlace(P, place, node) {
      let tex = this._libTex("place." + place.place_id);
      if (this._variantTex && this._variantTex[place.place_id]) tex = this._variantTex[place.place_id];  // 视觉变体优先
      if (!tex) return null;
      const meta = this._libMeta("place." + place.place_id) || {};
      const sz = meta.size || [tex.width || 128, tex.height || 128];
      const anc = meta.anchor || [sz[0] / 2, sz[1] - 8];
      const c = new P.Container();
      c.x = node.x; c.y = node.y;
      // ① 接地软影 + 方向投影（提质量：光左上前 → 影投右下；资产不烘影，渲染层统一施加）
      const sh = new P.Graphics();
      const hw = sz[0] * 0.36, hh = sz[0] * 0.13;
      fillEllipse(sh, hw * 0.30, 2, hw * 1.05, hh * 1.15, 0x0e1a10, 0.18);  // 方向投影（底边之下、右偏）
      fillEllipse(sh, hw * 0.12, 1, hw * 0.62, hh * 0.85, 0x0e1a10, 0.26);  // 接地核心（可见、不被精灵覆盖）
      fillEllipse(sh, hw * 0.02, 0, hw * 0.30, hh * 0.50, 0x0e1a10, 0.34);  // 最实接触点（长在地上）
      c.addChild(sh);
      const sp = new P.Sprite(tex);
      sp.anchor.set(anc[0] / sz[0], anc[1] / sz[1]);
      sp.tint = this._depthTint(node.y);                                // T269：建筑也参与远/中/近三层色阶
      c.addChild(sp);
      const label = new P.Text(place.name_cn || place.place_id, {
        fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif', fontSize: 13,
        fill: 0xffffff, stroke: 0x0b0e12, strokeThickness: 4,
      });
      label.anchor.set(0.5, 0); label.y = 4; label.zIndex = 999;
      c.addChild(label);
      c.__label = label; c.__labelAboveY = -(sz[1] - anc[1]) - 20;
      c.__placeId = place.place_id; c.__place = place;
      c.__glows = [[-sz[0] * 0.18, -(sz[1] - anc[1]) * 0.55, 6], [sz[0] * 0.18, -(sz[1] - anc[1]) * 0.55, 6]];
      c.__smoke = [];
      return c;
    }

    // T357-A：局部高对比结构 —— 近景遮挡剪影（下缘大树冠，跨压建筑）+ 近景/四角暗角（统一调色板 + Bayer 抖动）
    _buildForeground() {
      const P = global.PIXI;
      const G = this.fgLayer; if (!G) return;
      const Wd = this.world.width, H = this.world.height;
      // ① 近景/四角暗角（Bayer 抖动，像素感；下缘强、左右下角更强）
      const BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
      const CELL = 3;
      const vg = new P.Graphics();
      for (let y = 0; y < H; y += CELL) {
        for (let x = 0; x < Wd; x += CELL) {
          const near = Math.max(0, (y / H - 0.50) / 0.50);                 // 只在下半
          const ex = Math.max(0, 1 - Math.min(x, Wd - x) / (Wd * 0.30));   // 越靠左右越强
          const a = near * (0.08 + 0.26 * ex);                             // 目标不透明度
          if (a <= 0.015) continue;
          const b = (BAYER[((y / CELL) | 0) & 3][((x / CELL) | 0) & 3] + 0.5) / 16;
          if (b > a) continue;                                             // 抖动阈值
          fillRect(vg, x, y, CELL, CELL, 0x0a1410, a);
        }
      }
      G.addChild(vg);
      // ② 近景遮挡剪影：下缘左右大"树冠"，深色、非直边、跨压紧邻建筑
      const DARK = 0x0c1712;
      const put = (cx, cy, rect, sc) => {
        const t = W.spriteTex(this.tilesetBase, rect); if (!t) return;
        const sp = new P.Sprite(t); sp.anchor.set(0.5, 1); sp.x = cx; sp.y = cy; sp.scale.set(sc); sp.tint = DARK;
        G.addChild(sp);
        // 接触影：让剪影"压"在地面上
        const sh = new P.Graphics(); fillEllipse(sh, cx + 4, cy - 3, 26 * sc, 8 * sc, 0x050b08, 0.30); G.addChild(sh);
      };
      put(70, H - 62, W.SPR.treeCluster, 4.2);
      put(190, H - 96, W.SPR.conifer, 3.4);
      put(Wd - 80, H - 58, W.SPR.treeCluster, 4.6);
      put(Wd - 210, H - 92, W.SPR.conifer, 3.2);
    }

    // 氛围层：浅蓝冷调 + 细雪光点（确定性摆放）
    _buildAtmosphere() {
      const P = global.PIXI; const G2 = this._snowLayer;
      const { width, height } = this.world;
      const sky = new P.Graphics();
      fillRect(sky, 0, 0, width, height, 0xbfe0ff, 0.10);          // 浅蓝冷调
      fillRect(sky, 0, 0, width, 90, 0xbfe0ff, 0.10);              // 顶部略强
      G2.addChild(sky);
      const snow = new P.Graphics();
      for (let i = 0; i < 520; i++) {
        const x = W.hash2(i, 1, 401) * width, y = W.hash2(i, 2, 403) * height;
        const big = W.hash2(i, 3, 407) > 0.82;
        const r = big ? 3 : (W.hash2(i, 5, 411) > 0.5 ? 2 : 1);
        fillRect(snow, x | 0, y | 0, r, r, 0xffffff, 0.65 + W.hash2(i, 4, 409) * 0.35);
        if (big) { fillRect(snow, (x - 1) | 0, (y + 1) | 0, 1, 1, 0xffffff, 0.5); fillRect(snow, (x + r) | 0, (y - 1) | 0, 1, 1, 0xffffff, 0.5); }
      }
      G2.addChild(snow);
      // T269「没层次」：纵向纵深色调带 —— 上（远/北）偏冷暗、下（近/南）偏暖亮（俯视读远近；不动拓扑）
      const depth = new P.Graphics();
      for (let i = 0; i < height; i += 2) {                                                // 2px 步进 → 带缘更细、少"横向硬带"
        const t = i / height;
        fillRect(depth, 0, i, width, 2, 0x0a1420, 0.28 * (1 - t));                        // 远端冷暗（T269 加强）
        fillRect(depth, 0, i, width, 2, 0x2a3550, 0.16 * (1 - t) * (1 - t));              // 空气透视：远端去饱和/偏冷
        if (t > 0.34) fillRect(depth, 0, i, width, 2, 0xffd9a0, 0.13 * (t - 0.34) / 0.66); // 近端暖亮（T269 加强）
      }
      G2.addChild(depth);
      // 轻微颗粒/抖动（避免"太干净"，贴近手绘像素）
      // T120：颗粒减弱（保留轻质颗粒、不再是"屏幕噪点"）
      const grain = new P.Graphics();
      for (let i = 0; i < 280; i++) {
        const x = W.hash2(i, 11, 501) * width, y = W.hash2(i, 12, 503) * height;
        const dark = W.hash2(i, 13, 507) > 0.5;
        fillRect(grain, x | 0, y | 0, 1, 1, dark ? 0x1a2030 : 0xffffff, dark ? 0.06 : 0.05);
      }
      G2.addChild(grain);
      this._grainGraphics = grain;      // T116：景观模式可隐藏颗粒
    }

    // T116 信息分层：mode = 'landscape' | 'default' | 'info'
    //  - landscape：隐藏全部标签 + 散点 + 颗粒（只留建筑/角色/地形，用于欣赏与截图）
    //  - default  ：只显建筑名；NPC ID 隐藏；散点降密度
    //  - info     ：建筑名 + NPC ID（近景/点击用）
    setMode(mode) {
      this._viewMode = (mode === "landscape" || mode === "info") ? mode : "default";
      const land = this._viewMode === "landscape";
      const info = this._viewMode === "info";
      (this._placeLabels || []).forEach((l) => { l.visible = !land; });
      if (this._scatterLayer) this._scatterLayer.visible = !land;
      if (this._grainGraphics) this._grainGraphics.visible = !land;
      this._showAgentLabels = info;
      Object.keys(this.agents).forEach((id) => {
        const r = this.agents[id];
        if (r.setLabel) r.setLabel(info && r.container.visible);
      });
    }
    applyZoomTier(scale) { this.setMode(scale >= 1.35 ? "info" : "default"); }   // 供 shell 在缩放变化时调用
    setAgentLabelById(id, on) { const r = this.agents[id]; if (r && r.setLabel) r.setLabel(!!on); }

    // T120/低照度：夜间给角色**夜光描边**（用同一贴图的亮色剪影垫底，像素、无平滑糊边）+ 更实接触影
    _agentLight(rec) {
      if (!rec) return;
      const night = this._lightMode === "night";
      const base = (rec.sprite && Math.abs(rec.sprite.scale.x)) || 0.58;
      if (rec.outline) {
        rec.outline.tint = night ? 0xe6f6ff : 0x141a24;      // 夜=冷白夜光描边（像素硬边，无糊）
        rec.outline.alpha = night ? 1.0 : 0.9;
        try { rec.outline.scale.set(base * (night ? 1.26 : 1.16)); } catch (e) { /* mock */ }
      }
      if (rec.shadow) { try { rec.shadow.scale.set(night ? 1.3 : 1); } catch (e) { /* mock */ } }
      if (rec.glow) { try { rec.glow.scale.set(night ? 1.4 : 1); } catch (e) { /* mock */ } }
    }

    // ================================================================= 地形
    _px2t(v) { return Math.floor(v / TILE); }

    // 草地三阶 tone ramp（T124）：优先用资产库 tile.grass_{dark,mid,light}（真 3 阶，32×32）；
    // 无库时回退 tileset 帧（中=271 / 暗=962 / 亮=745）。
    _grassTex(tier) {
      const IDS = ["tile.grass_dark", "tile.grass_mid", "tile.grass_light"];
      if (this._useLib) { const t = this._libTex(IDS[tier] || IDS[1]); if (t) return t; }
      const F = [W.TILES.grass[2], W.TILES.grass[0], W.TILES.grassLight[0]];
      return W.slice(this.tilesetBase, F[tier] || F[1]);
    }

    // 地面"有机斑块"（T124）：低频 value-noise(2 尺度) + Bayer 边界抖动 → 非矩形、过渡自然；
    // 替代原来 8×8 方块 hash（方块感来自"选格"而非 tile 资产）。返回 0/1/2 = 暗/中/亮。
    _grassTier(tx, ty) {
      const vn = (x, y, s, sc) => {
        const fx = x / sc, fy = y / sc;
        const x0 = Math.floor(fx), y0 = Math.floor(fy);
        const dx = fx - x0, dy = fy - y0;
        const c00 = W.hash2(x0, y0, s), c10 = W.hash2(x0 + 1, y0, s);
        const c01 = W.hash2(x0, y0 + 1, s), c11 = W.hash2(x0 + 1, y0 + 1, s);
        const sx = dx * dx * (3 - 2 * dx), sy = dy * dy * (3 - 2 * dy);
        const a = c00 + (c10 - c00) * sx, b = c01 + (c11 - c01) * sx;
        return a + (b - a) * sy;
      };
      const BAY = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
      const bay = (BAY[ty & 3][tx & 3] + 0.5) / 16 - 0.5;     // -0.5..0.5 边界抖动
      const n = 0.62 * vn(tx, ty, 9, 14) + 0.38 * vn(tx + 7, ty + 3, 4, 4) + 0.14 * bay;
      return n > 0.60 ? 2 : (n < 0.42 ? 0 : 1);
    }

    // 道路 / 广场 / 水面 / 农田 的 tile 掩码
    _makeMask() {
      const cols = this._cols, rows = this._rows;
      const road = [], water = [], soil = [], plaza = [], bridge = [], mainRoad = [];
      for (let y = 0; y < rows; y++) { road.push(new Array(cols).fill(false)); water.push(new Array(cols).fill(false)); soil.push(new Array(cols).fill(false)); plaza.push(new Array(cols).fill(false)); bridge.push(new Array(cols).fill(false)); mainRoad.push(new Array(cols).fill(false)); }
      const inB = (tx, ty) => tx >= 0 && ty >= 0 && tx < cols && ty < rows;
      const set = (g, tx, ty, v) => { if (inB(tx, ty)) g[ty][tx] = (v === undefined ? true : v); };
      const t = (v) => Math.floor(v / TILE);

      // 1) 街道网（LAYOUT.MAINS；轴对齐，w=占宽 tile）
      const markSeg = (a, b, W) => {
        if (a[1] === b[1]) { const ty = t(a[1]); for (let x = Math.min(a[0], b[0]); x <= Math.max(a[0], b[0]); x += TILE) for (let j = 0; j < (W || 1); j++) set(road, t(x), ty + j); }
        else if (a[0] === b[0]) { const tx = t(a[0]); for (let y = Math.min(a[1], b[1]); y <= Math.max(a[1], b[1]); y += TILE) for (let j = 0; j < (W || 1); j++) set(road, tx + j, t(y)); }
      };
      LAYOUT.MAINS.forEach((s) => markSeg(s.a, s.b, s.w));
      { const m = LAYOUT.MAINS[0]; const ty = t(m.a[1]); for (let x = Math.min(m.a[0], m.b[0]); x <= Math.max(m.a[0], m.b[0]); x += TILE) for (let j = 0; j < m.w; j++) set(mainRoad, t(x), ty + j); }

      // 2) 支路：每个 place 垂直连到最近街道（形成树状小路，而非同心环）
      Object.keys(LAYOUT.NODES).forEach((id) => {
        const nx = LAYOUT.NODES[id][0], ny = LAYOUT.NODES[id][1];
        let px = nx, py = ny, bestD = 1e9;
        LAYOUT.MAINS.forEach((s) => {
          const x1 = Math.min(s.a[0], s.b[0]), x2 = Math.max(s.a[0], s.b[0]);
          const y1 = Math.min(s.a[1], s.b[1]), y2 = Math.max(s.a[1], s.b[1]);
          let cx, cy, d;
          if (s.a[1] === s.b[1]) { cx = Math.max(x1, Math.min(x2, nx)); cy = s.a[1]; d = Math.abs(ny - cy) + 0.35 * Math.abs(nx - cx); }
          else { cy = Math.max(y1, Math.min(y2, ny)); cx = s.a[0]; d = Math.abs(nx - cx) + 0.35 * Math.abs(ny - cy); }
          if (d < bestD) { bestD = d; px = cx; py = cy; }
        });
        if (bestD > 1e8) return;
        // L 形支路：拐角朝向按确定性哈希择一 → 枝路蜿蜒、非网格
        if (W.hash2(t(nx), t(ny), 300) > 0.5) {
          for (let x = Math.min(t(nx), t(px)); x <= Math.max(t(nx), t(px)); x++) set(road, x, t(ny));
          for (let y = Math.min(t(ny), t(py)); y <= Math.max(t(ny), t(py)); y++) set(road, t(px), y);
        } else {
          for (let y = Math.min(t(ny), t(py)); y <= Math.max(t(ny), t(py)); y++) set(road, t(nx), y);
          for (let x = Math.min(t(nx), t(px)); x <= Math.max(t(nx), t(px)); x++) set(road, x, t(py));
        }
      });
      // 斜向碎石小径：沿直线栅格化（宽度 1 tile）
      (LAYOUT.DIAGS || []).forEach((dg) => {
        const n = Math.max(1, Math.ceil(Math.hypot(dg.b[0] - dg.a[0], dg.b[1] - dg.a[1]) / (TILE / 2)));
        for (let i = 0; i <= n; i++) set(road, t(dg.a[0] + (dg.b[0] - dg.a[0]) * i / n), t(dg.a[1] + (dg.b[1] - dg.a[1]) * i / n));
      });

      // 3) 河道（西侧蜿蜒；沿折线插值中心线）
      const R = LAYOUT.RIVER;
      for (let y = R.pts[0][1]; y <= R.pts[R.pts.length - 1][1]; y += 4) {
        let cx = R.pts[0][0];
        for (let k = 0; k < R.pts.length - 1; k++) {
          const p0 = R.pts[k], p1 = R.pts[k + 1];
          if (y >= p0[1] && y <= p1[1]) { const f = (y - p0[1]) / Math.max(1, p1[1] - p0[1]); cx = p0[0] + (p1[0] - p0[0]) * f; break; }
        }
        for (let x = cx - R.half; x <= cx + R.half; x += 4) set(water, t(x), t(y));
      }
      // 4) 公园池塘
      const PD = LAYOUT.POND;
      for (let y = PD.y - PD.ry - 4; y <= PD.y + PD.ry + 4; y += 4) for (let x = PD.x - PD.rx - 4; x <= PD.x + PD.rx + 4; x += 4) {
        if (((x - PD.x) / PD.rx) ** 2 + ((y - PD.y) / PD.ry) ** 2 <= 1) set(water, t(x), t(y));
      }
      // 5) 河岸农田
      LAYOUT.FARM_PLOTS.forEach((r) => {
        for (let y = r.y; y < r.y + r.h; y += TILE) for (let x = r.x; x < r.x + r.w; x += TILE) {
          const tx = t(x), ty = t(y);
          if (inB(tx, ty) && !road[ty][tx] && !water[ty][tx]) set(soil, tx, ty);
        }
      });
      // 6) 中央广场（主街×中轴交汇）
      const hub = this.nodeById["plaza"] || { x: this.world.width / 2, y: this.world.height / 2 };
      const hx = t(hub.x), hy = t(hub.y);
      for (let dy = -3; dy <= 3; dy++) for (let dx = -3; dx <= 3; dx++) {
        if (dx * dx + dy * dy <= 7) { set(plaza, hx + dx, hy + dy); set(road, hx + dx, hy + dy); }
      }
      // 7) 桥：道路与河道重叠处（主街跨河湾）
      for (let ty = 0; ty < rows; ty++) for (let tx = 0; tx < cols; tx++) {
        if (road[ty][tx] && water[ty][tx]) { set(bridge, tx, ty); set(water, tx, ty, false); }
      }
      this._roadMask = road; this._waterMask = water; this._soilMask = soil; this._plazaMask = plaza; this._bridgeMask = bridge; this._mainMask = mainRoad;
      return road;
    }

    _buildTerrain() {
      const P = global.PIXI;
      const { width, height } = this.world;

      // 1) 纯色底（防止未覆盖处漏黑）
      const bg = new P.Graphics(); fillRect(bg, 0, 0, width, height, C.bg, 1);
      this.groundLayer.addChild(bg);

      // 2) 无缝草地：主 271，低频大色斑（无 checkerboard）
      const road = this._makeMask();
      this._kindGrid = road;   // 向后兼容 smoke_test 的「地形网格已构建」断言
      const grass = new P.Container();
      const gset = W.TILES.grass, glight = W.TILES.grassLight;
      for (let ty = 0; ty < this._rows; ty++) {
        for (let tx = 0; tx < this._cols; tx++) {
          if (road[ty][tx]) continue;                       // 路面/广场由 features 层画
          const tier = this._grassTier(tx, ty);             // 有机斑块（value-noise + Bayer；非 8×8 方块）
          const sp = new P.Sprite(this._grassTex(tier));
          sp.x = tx * TILE; sp.y = ty * TILE;
          grass.addChild(sp);
        }
      }
      this.groundLayer.addChild(grass);

      // 3) 特征层：广场/道路/水面/农田
      const feat = new P.Graphics();
      this._drawPlaza(feat);
      this._drawRoads(feat);
      this._drawWater(feat);
      this._drawFarm(feat);
      this.groundLayer.addChild(feat);

      // 4) 装饰层（树/石/花 + 道具）
      this._decorLayer = new P.Container();
      this.groundLayer.addChild(this._decorLayer);
      this._scatterLayer = new P.Container();   // T116：草地散点（降密度 + 可一键隐藏）
      this.groundLayer.addChild(this._scatterLayer);

      // 外框暗角
      const vig = new P.Graphics();
      vig.lineStyle(8, 0x141f10, 0.85); vig.drawRect(4, 4, width - 8, height - 8);
      vig.lineStyle(3, 0x3f5a30, 0.5); vig.drawRect(9, 9, width - 18, height - 18);
      this.groundLayer.addChild(vig);
    }

    _drawRoads(g) {
      const road = this._roadMask, plaza = this._plazaMask;
      const isRoad = (tx, ty) => (tx >= 0 && ty >= 0 && tx < this._cols && ty < this._rows) && road[ty][tx];
      for (let ty = 0; ty < this._rows; ty++) {
        for (let tx = 0; tx < this._cols; tx++) {
          if (!road[ty][tx] || plaza[ty][tx]) continue;
          const x = tx * TILE, y = ty * TILE;
          if (this._bridgeMask && this._bridgeMask[ty][tx]) {          // 石/木桥（主街跨河）
            fillRect(g, x, y, TILE, TILE, 0x8a5a2f);
            for (let k = 0; k < 4; k++) fillRect(g, x, y + 2 + k * 8, TILE, 5, k % 2 ? 0x9c6a38 : 0x7a4a26);
            fillRect(g, x, y, 2, TILE, 0x5f3d1f); fillRect(g, x + TILE - 2, y, 2, TILE, 0x5f3d1f);
            continue;
          }
          const isMain = this._mainMask && this._mainMask[ty][tx];
          const base = isMain ? C.street : C.dirt, dk = isMain ? C.streetD : C.dirtD, lt = isMain ? C.streetL : C.dirtL;
          fillRect(g, x, y, TILE, TILE, base);
          // 碎石/光斑
          for (let s = 0; s < 5; s++) {
            const r1 = W.hash2(tx * 7 + s, ty * 13 + s, 41), r2 = W.hash2(tx * 3 + s, ty * 5 + s, 47);
            fillRect(g, (x + 3 + r1 * (TILE - 8)) | 0, (y + 3 + r2 * (TILE - 8)) | 0, 2, 2, s % 2 ? lt : dk, 0.7);
          }
          // 路面↔草地：**材质过渡带**（1px 深线 + 外侧 3px Bayer 抖动带，替代硬边）——T124 ①
          const trans = (side) => {
            for (let s = 0; s < TILE; s += 2) {
              const chk = ((s >> 1) & 1) === 0;               // 棋盘密度 50%/25%
              let bx, by;
              if (side === 0) { fillRect(g, x, y + s, 1, 2, dk); bx = x - (chk ? 2 : 1); by = y + s; }
              else if (side === 1) { fillRect(g, x + TILE - 1, y + s, 1, 2, dk); bx = x + TILE + (chk ? 0 : 1); by = y + s; }
              else if (side === 2) { fillRect(g, x + s, y, 2, 1, dk); bx = x + s; by = y - (chk ? 2 : 1); }
              else { fillRect(g, x + s, y + TILE - 1, 2, 1, dk); bx = x + s; by = y + TILE + (chk ? 0 : 1); }
              fillRect(g, bx, by, 2, 2, base, chk ? 0.55 : 0.30);   // 抖动的路面色渗入草地
            }
          };
          if (!isRoad(tx - 1, ty)) trans(0);
          if (!isRoad(tx + 1, ty)) trans(1);
          if (!isRoad(tx, ty - 1)) trans(2);
          if (!isRoad(tx, ty + 1)) trans(3);
        }
      }
      // 草地→路面 的碎屑过渡
      const nb = [[-1, 0], [1, 0], [0, -1], [0, 1]];
      for (let ty = 0; ty < this._rows; ty++) {
        for (let tx = 0; tx < this._cols; tx++) {
          if (!road[ty][tx] || plaza[ty][tx]) continue;
          for (let n = 0; n < nb.length; n++) {
            const nx = tx + nb[n][0], ny = ty + nb[n][1];
            if (nx < 0 || ny < 0 || nx >= this._cols || ny >= this._rows) continue;
            if (road[ny][nx]) continue;
            for (let s = 0; s < 3; s++) {
              const r1 = W.hash2(tx * 5 + s, ty * 9 + n * 17 + s, 53), r2 = W.hash2(tx * 11 + s, ty * 7 + s, 59);
              let fx, fy;
              if (nb[n][0] === -1) { fx = tx * TILE - 2; fy = ty * TILE + 2 + r1 * (TILE - 4); }
              else if (nb[n][0] === 1) { fx = tx * TILE + TILE; fy = ty * TILE + 2 + r1 * (TILE - 4); }
              else if (nb[n][1] === -1) { fx = tx * TILE + 2 + r2 * (TILE - 4); fy = ty * TILE - 2; }
              else { fx = tx * TILE + 2 + r2 * (TILE - 4); fy = ty * TILE + TILE; }
              fillRect(g, fx | 0, fy | 0, 2, 2, C.dirt, 0.85);
            }
          }
        }
      }
      // 草叶侵入路缘 → 柔化「路面↔草地」过渡
      for (let ty = 0; ty < this._rows; ty++) {
        for (let tx = 0; tx < this._cols; tx++) {
          if (!road[ty][tx] || plaza[ty][tx]) continue;
          const x = tx * TILE, y = ty * TILE;
          const tuft = (px, py) => { fillRect(g, px, py, 2, 3, 0x3f7a34, 0.9); fillRect(g, px + 3, py + 1, 2, 2, 0x356b2c, 0.85); };
          if (!isRoad(tx - 1, ty)) { tuft(x + 1, y + 3 + (W.hash2(tx, ty, 1) * 18 | 0)); tuft(x + 1, y + 18 + (W.hash2(tx, ty, 2) * 8 | 0)); }
          if (!isRoad(tx + 1, ty)) { tuft(x + TILE - 6, y + 5 + (W.hash2(tx, ty, 3) * 18 | 0)); }
          if (!isRoad(tx, ty - 1)) { tuft(x + 5 + (W.hash2(tx, ty, 4) * 18 | 0), y + 1); }
          if (!isRoad(tx, ty + 1)) { tuft(x + 8 + (W.hash2(tx, ty, 5) * 14 | 0), y + TILE - 5); }
        }
      }
    }

    _drawPlaza(g) {
      const hub = this.nodeById["plaza"]; if (!hub) return;
      const cx = hub.x, cy = hub.y, R = TILE * 2.6;
      fillEllipse(g, cx, cy + 7, R + 8, R * 0.74, 0x1c2a1a, 0.30);     // 投影
      fillCircle(g, cx, cy + 2, R + 5, C.cobbleD);
      // 铺装：小方砖（确定性交替色）
      const step = 9;
      for (let dy = -R; dy <= R; dy += step) {
        for (let dx = -R; dx <= R; dx += step) {
          if (dx * dx + dy * dy > R * R) continue;
          const rr = W.hash2((cx + dx) | 0, (cy + dy) | 0, 17);
          const col = rr > 0.62 ? C.cobbleL : (rr < 0.3 ? C.cobbleD : C.cobble);
          fillRect(g, cx + dx, cy + 2 + dy, step - 1, step - 1, col);
        }
      }
      g.lineStyle(2, C.cobbleD, 0.55); g.drawCircle(cx, cy + 2, R * 0.78); g.drawCircle(cx, cy + 2, R * 0.5); g.lineStyle(0, 0, 0);
    }

    _drawWater(g) {
      const water = this._waterMask; if (!water) return;
      const isW = (tx, ty) => (tx >= 0 && ty >= 0 && tx < this._cols && ty < this._rows) && water[ty][tx];
      const waterGroup = new global.PIXI.Container();
      const rim = new global.PIXI.Graphics();   // 深水岸线（纵深感）
      let bx0 = 1e9, by0 = 1e9, bx1 = -1e9, by1 = -1e9;
      for (let ty = 0; ty < this._rows; ty++) {
        for (let tx = 0; tx < this._cols; tx++) {
          if (!water[ty][tx]) continue;
          const sp = new global.PIXI.Sprite(W.slice(this.tilesetBase, W.pick(W.TILES.water, W.hash2(tx, ty, 31))));
          sp.x = tx * TILE; sp.y = ty * TILE;
          waterGroup.addChild(sp);
          bx0 = Math.min(bx0, tx * TILE); by0 = Math.min(by0, ty * TILE);
          bx1 = Math.max(bx1, tx * TILE + TILE); by1 = Math.max(by1, ty * TILE + TILE);
          const x = tx * TILE, y = ty * TILE;
          if (!isW(tx, ty - 1)) fillRect(rim, x, y, TILE, 3, C.waterD, 0.55);
          if (!isW(tx, ty + 1)) fillRect(rim, x, y + TILE - 3, TILE, 3, C.waterD, 0.65);
          if (!isW(tx - 1, ty)) fillRect(rim, x, y, 3, TILE, C.waterD, 0.55);
          if (!isW(tx + 1, ty)) fillRect(rim, x + TILE - 3, y, 3, TILE, C.waterD, 0.55);
        }
      }
      waterGroup.addChild(rim);
      // 浅色水面提亮 + 波光（避免死黑水塘）
      const shine = new global.PIXI.Graphics();
      const wcx = (bx0 + bx1) / 2, wcy = (by0 + by1) / 2, wrx = (bx1 - bx0) / 2, wry = (by1 - by0) / 2;
      fillEllipse(shine, wcx, wcy, wrx, wry, 0x6fb0dc, 0.16);
      for (let s = 0; s < 46; s++) {
        const r1 = W.hash2(s, 7, 101), r2 = W.hash2(s, 9, 103);
        fillRect(shine, (wcx - wrx + r1 * wrx * 2) | 0, (wcy - wry + r2 * wry * 2) | 0, 4, 2, 0xbfe6ff, 0.5);
      }
      // 睡莲（几片浮叶，增加生机与纵深）
      for (let s = 0; s < 5; s++) {
        const r1 = W.hash2(s, 3, 151), r2 = W.hash2(s, 5, 157);
        const lx = wcx - wrx * 0.7 + r1 * wrx * 1.4, ly = wcy - wry * 0.7 + r2 * wry * 1.4;
        fillCircle(shine, lx, ly, 5, 0x3f7a34, 0.9);
        fillCircle(shine, lx, ly, 5, 0x000000, 0.0);
        fillRect(shine, lx - 1, ly - 5, 2, 3, 0x2f5a2a, 0.9);
        if (W.hash2(s, 7, 163) > 0.5) fillCircle(shine, lx + 1, ly - 1, 2, 0xffdcea, 0.95);
      }
      waterGroup.addChild(shine);
      this._waterGroup = waterGroup;
      // 沙岸环
      for (let ty = 0; ty < this._rows; ty++) {
        for (let tx = 0; tx < this._cols; tx++) {
          if (water[ty][tx]) continue;
          let adj = false;
          if (isW(tx - 1, ty) || isW(tx + 1, ty) || isW(tx, ty - 1) || isW(tx, ty + 1)) adj = true;
          if (!adj) continue;
          const x = tx * TILE, y = ty * TILE;
          fillRect(g, x, y, TILE, TILE, C.sand, 0.92);
          for (let s = 0; s < 4; s++) {
            fillRect(g, (x + 2 + W.hash2(tx * 3 + s, ty * 5 + s, 83) * (TILE - 4)) | 0, (y + 2 + W.hash2(tx + s, ty, 89) * (TILE - 4)) | 0, 2, 2, C.sandD, 0.8);
          }
          // 水边芦苇（纵深/生机）
          if (W.hash2(tx, ty, 131) > 0.62) {
            const rx = x + 4 + W.hash2(tx, ty, 137) * (TILE - 10);
            const ry = y + 6 + W.hash2(tx + 1, ty, 139) * (TILE - 12);
            fillRect(g, rx, ry, 2, 9, 0x4f7a34); fillRect(g, rx + 4, ry - 3, 2, 12, 0x5f9a3f);
            fillRect(g, rx + 8, ry + 1, 2, 8, 0x4f7a34);
            fillRect(g, rx + 4, ry - 5, 3, 3, 0x8a6b3a);
          }
        }
      }
    }

    _drawFarm(g) {
      const soil = this._soilMask; if (!soil) return;
      for (let ty = 0; ty < this._rows; ty++) {
        for (let tx = 0; tx < this._cols; tx++) {
          if (!soil[ty][tx]) continue;
          const x = tx * TILE, y = ty * TILE;
          fillRect(g, x, y, TILE, TILE, C.soil);
          for (let f = 0; f < 4; f++) fillRect(g, x + 4, y + 4 + f * 8, TILE - 8, 2, C.soilD, 0.8);   // 田垄
          if (W.hash2(tx, ty, 97) > 0.35) {
            fillRect(g, x + 8, y + 6, 3, 5, 0x5f9e3a); fillRect(g, x + 18, y + 6, 3, 5, 0x74b04a);
            fillRect(g, x + 8, y + 15, 3, 5, 0x74b04a); fillRect(g, x + 18, y + 15, 3, 5, 0x5f9e3a);
          }
        }
      }
    }

    _buildDecorations() {
      const P = global.PIXI;
      const road = this._roadMask, water = this._waterMask, soil = this._soilMask, plaza = this._plazaMask;
      const deco = this._decorLayer;
      const nodes = Object.values(this.nodeById);
      // T269「没层次」主杠杆（顶视图）：细节密度随距离衰减 + 尺度衰减 + 远端空气透视 tint
      // t=0 最远(北/上)，t=1 最近(南/下)。位置 y 即"世界深度"。
      const DEPTH_H = this._rows * TILE;
      const depthAt = (y) => Math.max(0, Math.min(1, y / DEPTH_H));
      const depthScale = (t) => 0.88 + 0.14 * t;                 // 远端略小、近端略大
      const clearOf = (x, y, rad) => nodes.every((n) => {
        const dx = n.x - x, dy = n.y - y;
        return dx * dx + dy * dy > rad * rad;
      });
      // 水面瓦片（位于装饰之下）
      if (this._waterGroup) deco.addChild(this._waterGroup);

      for (let ty = 0; ty < this._rows; ty++) {
        for (let tx = 0; tx < this._cols; tx++) {
          if (road[ty][tx] || water[ty][tx] || soil[ty][tx] || plaza[ty][tx]) continue;
          const cx = tx * TILE + TILE / 2, cy = ty * TILE + TILE / 2;
          if (!clearOf(cx, cy, this.placeRadius)) continue;
          const edge = Math.min(tx, ty, this._cols - 1 - tx, this._rows - 1 - ty);
          // 步道/广场 1 格内留空 → 形成疏密对比（镇中心开阔）
          let nearRoad = false;
          for (let oy = -2; oy <= 2 && !nearRoad; oy++) {         // 2 格净空带（更明显留白）
            for (let ox = -2; ox <= 2; ox++) {
              const nx = tx + ox, ny = ty + oy;
              if (nx < 0 || ny < 0 || nx >= this._cols || ny >= this._rows) continue;
              if (road[ny][nx] || plaza[ny][nx]) { nearRoad = true; break; }
            }
          }
          if (nearRoad) continue;
          const r = W.hash2(tx, ty, 99);
          const grove = W.hash2(tx >> 2, ty >> 2, 5);              // 8x8 tile 的树丛簇
          let rect = null, scale = 1;
          if (edge <= 2) {                                          // 边缘：三面不同（防"同心环"）
            const side = (ty <= 2) ? "N" : (ty >= this._rows - 3) ? "S" : (tx <= 2) ? "W" : "E";
            const gapN = side === "N" && tx > 9 && tx < 18;         // 北面留缺口 → 露出农田远景
            const gapGate = side === "S" && Math.abs(tx - Math.floor(430 / TILE)) <= 2;
            if (gapN || gapGate) continue;
            const pTree = side === "N" ? 0.32 : side === "E" ? 0.24 : 0.5;
            if (r < pTree) { rect = W.SPR.treeCluster; scale = 0.85; }
            else if (r < pTree + 0.26) { rect = W.SPR.conifer; scale = 1.25; }
            else if (r < pTree + 0.36) { rect = W.SPR.bush; scale = 1.15; }
            else if (r < pTree + 0.41) { rect = W.SPR.rock; scale = 1.0; }
            else { rect = W.SPR.flower; scale = 1.05; }
          } else if (grove > 0.74 && r < 0.38) {                    // 簇状树丛（成片，不是碎点）
            if (r < 0.30) { rect = W.SPR.treeCluster; scale = 0.78; }
            else { rect = W.SPR.conifer; scale = 1.2; }
          } else if (r < 0.06) { rect = W.SPR.bush; scale = 1.1; }
          else if (r < 0.14) { rect = W.SPR.flower; scale = 1.05; }
          else if (r < 0.17) { rect = W.SPR.plant; scale = 1.05; }
          else if (r < 0.19) { rect = W.SPR.rock; scale = 0.95; }
          if (!rect) continue;
          // T269：远端去细节 —— 小件（花/草/石/灌木）在远带按确定哈希稀疏化；只留成片树丛的大件绿意
          const dt = depthAt(cy);
          const big = (rect === W.SPR.treeCluster || rect === W.SPR.conifer);
          if (dt < 0.34 && !big && W.hash2(tx, ty, 321) > 0.35) continue;
          const sp = new P.Sprite(W.spriteTex(this.tilesetBase, rect));
          sp.anchor.set(0.5, 1);
          sp.x = cx; sp.y = cy + TILE / 2;
          sp.scale.set(scale * depthScale(dt));                       // T269：尺度随距离衰减
          sp.tint = this._depthTint(cy);                              // T269：三层色阶 tint（同源：远冷/中/近暖）
          deco.addChild(sp);
          // T269「像贴图」：接地 AO/接触影（每株装饰都"踩"在地上，不飘）——统一光向左上前→影偏右下
          const ao = new P.Graphics();
          fillEllipse(ao, cx + 2, cy + TILE / 2 - 1, 8 * scale, 3 * scale, 0x0e1a10, 0.22);
          deco.addChild(ao);
        }
      }
      // 地表随机点缀：小石 / 枯枝 / 高草（弱化平铺重复感）
      for (let ty = 0; ty < this._rows; ty++) {
        for (let tx = 0; tx < this._cols; tx++) {
          if (road[ty][tx] || water[ty][tx] || soil[ty][tx] || plaza[ty][tx]) continue;
          const r = W.hash2(tx, ty, 211);
          if (r > 0.07) continue;                       // T116：降密度（0.16→0.07），保留质感、去"彩色噪点"
          const scx = tx * TILE + 4 + W.hash2(tx, ty, 213) * (TILE - 10);
          const scy = ty * TILE + 4 + W.hash2(tx, ty, 217) * (TILE - 10);
          // T269：远端地表碎点进一步稀疏（去细节），近端保留
          if (depthAt(scy) < 0.34 && W.hash2(tx, ty, 323) > 0.4) continue;
          const cx = scx, cy = scy;
          const t = W.hash2(tx, ty, 219);
          const g = new P.Graphics();
          if (t < 0.45) { fillRect(g, cx, cy, 4, 3, 0x7c8188); }                       // 小石（低饱和，非彩噪）
          else if (t < 0.75) { fillRect(g, cx, cy, 10, 2, 0x6a4a26); }                  // 枯枝
          else { for (let i = 0; i < 5; i++) fillRect(g, cx + i * 2, cy + (i % 2 ? 0 : 1), 2, 3, 0x4f7d38); }  // 高草（同色阶）
          this._scatterLayer.addChild(g);
        }
      }
      this._buildProps(deco);
    }

    // 道具：路灯 / 长椅 / 花坛 / 围栏 / 招牌（程序化像素）
    _buildProps(deco) {
      const P = global.PIXI;
      const road = this._roadMask;
      const isRoad = (tx, ty) => (tx >= 0 && ty >= 0 && tx < this._cols && ty < this._rows) && road[ty][tx];
      const lampAt = (x, y) => {
        const g = new P.Graphics();
        fillEllipse(g, x + 2, y + 1, 6, 3, 0x0e1a10, 0.28);   // T269像贴图：统一暖黑接地影+右下偏移
        fillRect(g, x - 1, y - 26, 3, 26, 0x4a4a52);
        fillRect(g, x - 4, y - 32, 9, 7, 0x2f2f36);
        fillCircle(g, x + 0.5, y - 29, 3, 0xffe08a);
        fillCircle(g, x + 0.5, y - 29, 1.5, 0xfff6d0);
        deco.addChild(g);
        (this._lampGlows = this._lampGlows || []).push([x + 0.5, y - 29]);
      };
      const benchAt = (x, y) => {
        const g = new P.Graphics();
        fillEllipse(g, x + 2, y + 1, 9, 3, 0x0e1a10, 0.26);   // T269像贴图：统一暖黑接地影+右下偏移
        fillRect(g, x - 9, y - 8, 18, 3, 0x8a5a2f);
        fillRect(g, x - 9, y - 13, 18, 3, 0x8a5a2f);
        fillRect(g, x - 8, y - 6, 2, 6, 0x5f3d1f); fillRect(g, x + 6, y - 6, 2, 6, 0x5f3d1f);
        deco.addChild(g);
      };
      const flowerBed = (x, y) => {
        const g = new P.Graphics();
        fillEllipse(g, x + 2, y - 1, 14, 4, 0x0e1a10, 0.22);   // T269 接地 AO
        fillRound(g, x - 12, y - 6, 24, 10, 3, 0x8a6636);
        fillRect(g, x - 12, y - 6, 24, 3, 0x9c7a44);
        const cols = [0xff7fb0, 0xffd45c, 0xff8f6b, 0xc08bff, 0xfff2c0];
        for (let i = 0; i < 8; i++) {
          const r1 = W.hash2(x | 0, y | 0, i * 3 + 1);
          fillCircle(g, x - 9 + i * 2.6, y - 8 - r1 * 3, 2, cols[i % cols.length]);
        }
        deco.addChild(g);
      };
      // 沿主干道两侧放路灯
      const hub = this.nodeById["plaza"];
      if (hub) {
        const htx = this._px2t(hub.x), hty = this._px2t(hub.y);
        for (let ty = 0; ty < this._rows; ty++) {
          for (let tx = 0; tx < this._cols; tx++) {
            if (!isRoad(tx, ty) || this._plazaMask[ty][tx]) continue;
            const onAxis = (tx === htx) || (ty === hty);
            if (!onAxis) continue;
            if ((tx + ty) % 5 !== 0) continue;
            if (W.hash2(tx, ty, 61) < 0.35) continue;
            if (!isRoad(tx, ty - 1)) lampAt(tx * TILE + TILE / 2, ty * TILE + 2);
            else if (!isRoad(tx + 1, ty)) lampAt(tx * TILE + TILE - 2, ty * TILE + TILE / 2);
          }
        }
        // 广场环：长椅 + 花坛
        const R = TILE * 3.4;
        for (let i = 0; i < 6; i++) {
          const a = (i / 6) * Math.PI * 2 + 0.3;
          const x = hub.x + Math.cos(a) * R, y = hub.y + Math.sin(a) * R * 0.72 + 10;
          if (i % 2 === 0) benchAt(x, y); else flowerBed(x, y);
        }
        // 广场四角路灯（夜间让广场有光，不做"黑盘"）
        for (let i = 0; i < 4; i++) {
          const a = (i / 4) * Math.PI * 2 + Math.PI / 4;
          lampAt(hub.x + Math.cos(a) * TILE * 2.6, hub.y + Math.sin(a) * TILE * 1.9 + 8);
        }
      }
      // 农田围栏
      const farm = this.nodeById["farm"]; if (farm) {
        const g = new P.Graphics();
        const fx = (this._px2t(farm.x) - 1) * TILE, fy = (this._px2t(farm.y) + 3) * TILE;
        const w = 5 * TILE, h = 3 * TILE;
        for (let x = fx; x <= fx + w; x += 8) fillRect(g, x, fy - 4, 2, 8, 0x8a6636);
        for (let y = fy; y <= fy + h; y += 8) fillRect(g, fx - 4, y, 2, 8, 0x8a6636);
        for (let x = fx; x <= fx + w; x += 8) fillRect(g, x, fy + h, 2, 8, 0x8a6636);
        deco.addChild(g);
      }
      // 生活小品散点：填空地、去挤（水井/长椅/栅栏，确定性摆放）
      const wellAt = (x, y) => {
        const g = new P.Graphics();
        fillEllipse(g, x + 2, y + 1, 11, 4, 0x0e1a10, 0.26);  // T269像贴图：统一暖黑接地影+右下偏移
        fillRound(g, x - 9, y - 15, 18, 15, 3, 0x8a8f96);
        fillRect(g, x - 9, y - 15, 18, 3, 0xb8bdb4);
        fillRect(g, x - 6, y - 22, 12, 8, 0x6f747a);
        fillRect(g, x - 8, y - 24, 16, 3, 0x8a6636);
        deco.addChild(g);
      };
      const fenceRun = (x1, y1, x2, y2) => {
        const g = new P.Graphics();
        const n = Math.max(1, Math.round(Math.hypot(x2 - x1, y2 - y1) / 16));
        for (let i = 0; i <= n; i++) {
          const x = x1 + (x2 - x1) * i / n, y = y1 + (y2 - y1) * i / n;
          fillRect(g, x - 1, y - 8, 2, 9, 0x8a6636); fillRect(g, x - 2, y - 4, 4, 2, 0x6f4f2a);
        }
        deco.addChild(g);
      };
      wellAt(890, 792); wellAt(1095, 560);
      benchAt(608, 748); benchAt(806, 748); benchAt(430, 690);
      fenceRun(360, 902, 760, 902);
      fenceRun(1010, 520, 1010, 668);
      { const g = new P.Graphics(); fillRect(g, 188, 700, 58, 16, 0x8a5a2f);
        for (let i = 0; i < 4; i++) fillRect(g, 192 + i * 15, 700, 3, 16, 0x6f4a26);
        fillRect(g, 188, 714, 58, 3, 0x5a3a1e); deco.addChild(g); }

      // ===== ② 密度与构图（T124）：把已有的"连成街"，不新增建筑 =====
      const crateAt = (x, y) => {
        const g = new P.Graphics();
        fillEllipse(g, x + 2, y + 1, 8, 3, 0x0e1a10, 0.24);   // T269像贴图：统一暖黑接地影+右下偏移
        fillRound(g, x - 7, y - 12, 14, 12, 2, 0x9c6b34);
        fillRect(g, x - 7, y - 12, 14, 3, 0xba8348);
        fillRect(g, x - 1, y - 12, 2, 12, 0x7a4f26);
        deco.addChild(g);
      };
      const signAt = (x, y) => {
        const g = new P.Graphics();
        fillEllipse(g, x + 2, y + 1, 6, 2, 0x0e1a10, 0.24);   // T269像贴图：统一暖黑接地影+右下偏移
        fillRect(g, x - 1, y - 16, 2, 16, 0x6a4a26);
        fillRound(g, x - 8, y - 24, 16, 9, 2, 0x8a6636);
        fillRect(g, x - 6, y - 21, 12, 2, 0xd8c48a);
        deco.addChild(g);
      };
      // 沿【所有】道路：每 4 tile 一处连接件（灯/花坛/木箱交替，放在非路侧）——制造"街"
      for (let ty = 1; ty < this._rows - 1; ty++) {
        for (let tx = 1; tx < this._cols - 1; tx++) {
          if (!isRoad(tx, ty) || this._plazaMask[ty][tx]) continue;
          if ((tx + ty) % 4 !== 0) continue;
          let px, py, ok = false;
          if (!isRoad(tx, ty - 1)) { px = tx * TILE + TILE / 2; py = ty * TILE + 2; ok = true; }
          else if (!isRoad(tx + 1, ty)) { px = tx * TILE + TILE - 2; py = ty * TILE + TILE / 2; ok = true; }
          else if (!isRoad(tx, ty + 1)) { px = tx * TILE + TILE / 2; py = ty * TILE + TILE - 2; ok = true; }
          if (!ok) continue;
          const k = (tx + ty) % 3;
          if (k === 0) lampAt(px, py); else if (k === 1) flowerBed(px, py); else crateAt(px, py);
        }
      }
      // 建筑门口"落点"：招牌 + 花坛（让每栋有门脸，而非草坪孤岛）
      this.places.forEach((p) => {
        const n = this.nodeById[p.place_id]; if (!n) return;
        signAt(n.x + 22, n.y + 28);
        flowerBed(n.x - 24, n.y + 30);
      });
    }

    _buildPlaces() {
      const P = global.PIXI;
      this.places.forEach((p) => {
        const node = this.nodeById[p.place_id];
        if (!node) return;
        let sp = this._useLib ? this._libPlace(P, p, node) : null;   // 资产库（T87）
        if (!sp) sp = W.makePlaceSprite(P, p, node);                 // 回退：旧程序化
        if (sp && typeof sp.tint !== "undefined") sp.tint = this._depthTint(node.y);  // T269：回退路径同源分层
        const py = Math.max(112, Math.min(this.world.height - 26, node.y));
        sp.y = py; sp.zIndex = py;
        // T269：建筑尺度随距离衰减（远端略小 → 顶视图"远"的信号之一）
        const t = Math.max(0, Math.min(1, py / this.world.height));
        const ds = 0.94 + 0.08 * t;
        if (sp.scale && sp.scale.set) sp.scale.set(ds);
        this.placeLayer.addChild(sp);
        if (sp.__label) this._placeLabels.push(sp.__label);   // T116：建筑名（景观模式可隐藏）
      });
      try { this.placeLayer.sortableChildren = true; } catch (e) { /* mock */ }
      // 标签避让：按 y 分带，带内按 x 排序后**上下交替**，减少重叠（相邻过近时错行）
      const items = this.placeLayer.children.slice();
      const bands = {};
      items.forEach((c) => { const b = Math.round(c.y / 48); (bands[b] = bands[b] || []).push(c); });
      Object.keys(bands).forEach((b) => {
        bands[b].sort((p, q) => p.x - q.x);
        bands[b].forEach((c, i) => {
          if (i === 0) return;
          const prev = bands[b][i - 1];
          if (Math.abs(c.x - prev.x) < 150) {                 // 水平过近 → 错行
            if (c.__label) c.__label.y = (i % 2 === 1) ? (c.__labelAboveY || -74) : 22;
          }
        });
      });
      this._buildGlows();
    }

    // 地标（T124）：构图焦点（钟塔/喷泉/拱桥/风车）。走 landmarkLayer，**不进 placeLayer**（保 placeLayer=17）。
    _buildLandmarks() {
      const P = global.PIXI;
      const LM = [
        ["landmark.clocktower", 650, 372],   // 中轴北端·对景焦点（town_hall 旁）
        ["landmark.fountain", 705, 636],     // 中央广场地标
        ["landmark.arch_bridge", 300, 636],  // 主街跨河石拱
        ["landmark.windmill", 250, 300],     // 西北郊·远景
      ];
      LM.forEach((it) => {
        const t = this._libTex(it[0]); if (!t) return;
        const c = new P.Container(); c.x = it[1]; c.y = it[2];
        const sh = new P.Graphics();
        fillEllipse(sh, 2, -1, 26, 8, 0x0e1a10, 0.16);   // T269像贴图：地标同向影（右下）
        fillEllipse(sh, 1, -2, 16, 5, 0x0e1a10, 0.18);
        c.addChild(sh);
        const sp = new P.Sprite(t); sp.anchor.set(0.5, 60 / 64);
        sp.tint = this._depthTint(it[2]);                               // T269：地标参与深度分色
        c.addChild(sp);
        this.landmarkLayer.addChild(c);
      });
    }

    // ================================================================= 角色
    _ensureAgent(agentId) {
      if (this.agents[agentId]) return this.agents[agentId];
      const P = global.PIXI;
      let idx = this.agentOrder.indexOf(agentId);
      if (idx < 0) { this.agentOrder.push(agentId); idx = this.agentOrder.length - 1; }
      let frames = null, tex;
      if (this._useLib) {
        // 资产库角色：char.<name> 144x96 = 3 帧 ×(48x96) → 与 peeps 同帧尺寸，复用 same 几何
        const CHARS = ["char.villager_red", "char.villager_green", "char.villager_blue", "char.villager_yellow",
          "char.villager_purple", "char.villager_teal", "char.villager_orange", "char.villager_slate"];
        const A = global.HITTAssets;
        const cid = CHARS[idx % CHARS.length];
        const base = A && A.bases ? A.bases[cid] : null;
        if (base) { frames = [0, 1, 2].map((f) => new P.Texture(base, new P.Rectangle(f * 48, 0, 48, 96))); tex = frames[0]; }
      }
      if (!frames && this.peepsBase) { frames = [0, 1, 2].map((f) => W.peepsTexture(this.peepsBase, idx, f)); tex = frames[0]; }
      const made = W.makeAgentSprite(P, agentId, tex, tex);
      const container = made.container;
      const statusRef = { v: "alive" };
      const node = this.nodeById["residence"] || { x: 480, y: 360 };
      container.x = node.x; container.y = node.y + 6;
      this.agentLayer.addChild(container);
      const rec = {
        container,
        setStatus: (s) => { statusRef.v = s || "alive"; made.setStatus(s); },
        setBubble: made.setBubble, setHighlight: made.setHighlight, setLabel: made.setLabel,
        sprite: made.sprite, outline: made.outline, shadow: made.shadow, lantern: made.lantern, _statusRef: statusRef,
        _ph: W.hash2(idx, 0, 5) * 6.28, _dir: 1, frames, _fr: 0,
        target: { x: node.x, y: node.y + 6 },
      };
      // 角色自发光：画在夜色 overlay 之上的 _glowLayer，夜间成为暗处焦点（跟角色移动）
      // T120：发光也走"有限色阶 + 有序抖动"（同光晕口径，避免平滑糊边）
      const glow = new P.Graphics();
      const BAY = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], TI = [0.30, 0.20, 0.12, 0.06], CL = 2;
      const dDisc = (R, color, mul) => {
        for (let yy = -R; yy < R; yy += CL)
          for (let xx = -R; xx < R; xx += CL) {
            const d = Math.sqrt(xx * xx + yy * yy) / R; if (d > 1) continue;
            const idx = d * TI.length, i2 = Math.min(3, Math.floor(idx)), f = idx - i2;
            const b = (BAY[(((yy / CL) | 0) & 3 + 4) % 4][(((xx / CL) | 0) & 3 + 4) % 4] + 0.5) / 16;
            fillRect(glow, xx, yy, CL, CL, color, (f > b ? TI[Math.min(3, i2 + 1)] : TI[i2]) * mul);
          }
      };
      dDisc(19, 0xffcf6a, 0.8);
      glow.x = container.x; glow.y = container.y; glow.visible = false;
      this._glowLayer.addChild(glow);
      rec.glow = glow;
      this.agents[agentId] = rec;
      return rec;
    }

    renderState(state) {
      const P2 = global.PIXI;
      const byPlace = {};
      Object.keys(state.agents).forEach((id) => {
        const a = state.agents[id];
        (byPlace[a.location || "residence"] = byPlace[a.location || "residence"] || []).push(id);
      });
      this._badges = this._badges || {}; this._graves = this._graves || {}; this._agg = this._agg || {};
      const ALIVE_MAX = 8;
      Object.keys(byPlace).forEach((loc) => {
        const ids = byPlace[loc].slice().sort();
        const node = this.nodeById[loc] || { x: this.world.width / 2, y: this.world.height / 2 };
        const alive = ids.filter((id) => (state.agents[id].status || "alive") !== "dead");
        const dead = ids.filter((id) => (state.agents[id].status || "alive") === "dead");
        const n = ids.length, aliveN = alive.length, deadN = dead.length;
        // 生者：网格化铺排（上限 ALIVE_MAX）
        const shownA = Math.min(aliveN, ALIVE_MAX);
        const cols = Math.ceil(Math.sqrt(Math.max(1, shownA)));
        const rows = Math.ceil(shownA / cols);
        const gapX = 44, gapY = 38;
        alive.forEach((id, i) => {
          const rec = this._ensureAgent(id);
          const a = state.agents[id];
          const vis = i < shownA;
          if (rec.container) { rec.container.visible = vis; rec.container.alpha = (aliveN > 8 ? 0.94 : 1); }
          if (vis) {
            const ox = (i % cols - (cols - 1) / 2) * gapX;
            const oy = (Math.floor(i / cols) - (rows - 1) / 2) * gapY + 14;
            rec.target = { x: node.x + ox, y: node.y + oy };
            rec.container.zIndex = node.y + oy;
          } else { rec.target = { x: node.x, y: node.y }; }
          rec.setStatus("alive");
          rec.setBubble(a.bubble || null);
          if (rec.setHighlight) rec.setHighlight(!!a.bubble);
          if (rec.setLabel) rec.setLabel(vis && n <= 6 && this._showAgentLabels);   // T116：NPC ID 默认隐藏（info 模式才显）
        this._agentLight(rec);   // T120：夜间夜光描边 + 接触影
          if (rec.lantern) rec.lantern.visible = false;
          if (rec.glow) { rec.glow.x = rec.container.x; rec.glow.y = rec.container.y; rec.glow.visible = vis && (this._lightMode === "night"); }
        });
        // 死者：隐藏其容器，**不逐个铺碑**
        dead.forEach((id) => {
          const rec = this._ensureAgent(id);
          if (rec.container) rec.container.visible = false;
          if (rec.glow) rec.glow.visible = false;
          if (rec.setLabel) rec.setLabel(false);
        });
        // 生者溢出 +N
        const extraA = aliveN - shownA;
        let badge = this._badges[loc];
        if (extraA > 0) {
          if (!badge) { badge = new P2.Text("", { fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif', fontSize: 14, fill: 0xffffff, stroke: 0x0b0e12, strokeThickness: 4 }); badge.anchor.set(0.5, 0.5); this.agentLayer.addChild(badge); this._badges[loc] = badge; }
          badge.text = "+" + extraA; badge.x = node.x; badge.y = node.y - 44; badge.visible = true;
        } else if (badge) badge.visible = false;
        // 死者聚合："墓园簇"图标 + 计数（⚰×N）
        let gc = this._graves[loc];
        if (deadN > 0) {
          if (!gc) {
            const c = new P2.Container(); const g = new P2.Graphics();
            const t = new P2.Text("", { fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif', fontSize: 12, fill: 0xffffff, stroke: 0x0b0e12, strokeThickness: 4 });
            t.anchor.set(0.5, 1); c.addChild(g); c.addChild(t);
            this.agentLayer.addChild(c); this._graves[loc] = gc = { c: c, g: g, t: t };
          }
          gc.c.visible = true; gc.c.x = node.x + 54; gc.c.y = node.y + 10;
          if (gc.g.clear) gc.g.clear();
          for (let k = 0; k < 3; k++) {
            const x = (k - 1) * 13;
            W.fillRound(gc.g, x - 5, -16, 10, 16, 3, 0x8f949b);
            W.fillRound(gc.g, x - 4, -14, 8, 13, 3, 0xa8adb4);
            W.fillRect(gc.g, x - 1, -10, 2, 7, 0x6f747a); W.fillRect(gc.g, x - 4, -6, 8, 2, 0x6f747a);
          }
          gc.t.text = "\u26b0\u00d7" + deadN; gc.t.y = -18;
        } else if (gc) gc.c.visible = false;
        // 大簇：场所聚合标签（生X 亡Y），替代个人名牌
        let al = this._agg[loc];
        if (n > 6) {
          if (!al) { al = new P2.Text("", { fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif', fontSize: 12, fill: 0xffffff, stroke: 0x0b0e12, strokeThickness: 4 }); al.anchor.set(0.5, 0); this.agentLayer.addChild(al); this._agg[loc] = al; }
          al.text = "\u751f" + aliveN + (deadN ? " \u4ea1" + deadN : ""); al.x = node.x; al.y = node.y + 34; al.visible = true;
        } else if (al) al.visible = false;
      });
      // 本回合不在状态里的 → 隐藏（不误标死亡）
      Object.keys(this.agents).forEach((id) => {
        if (!state.agents[id]) { const rec = this.agents[id]; if (rec.container) rec.container.visible = false; if (rec.glow) rec.glow.visible = false; }
      });
    }

    // T270「动得生硬」修复（**仅运动渲染逻辑；不动逻辑 tick / 世界时刻 / 拓扑**）：
    // ① dt 归一化（替固定 k=0.18，掉帧不再变慢）；② 速度上限 + 加速度上限 → 起步不再一帧突跳（实测原为单帧 37px）；
    // ③ 目标切换时给每角色一个 0..4 帧的**渲染起步延迟**（错峰，破"19 人同帧齐步"）；④ 步态推进率 ∝ 实际速度。
    tick() {
      const now = (typeof performance !== "undefined" ? performance.now() : Date.now());
      let dt = (now - (this._tprev || now)) / 1000;
      this._tprev = now;
      if (!(dt > 0) || dt > 0.1) dt = 1 / 60;      // 首帧 / 切后台长帧兜底
      this._frame++;
      const t = this._frame;
      const TAU = 0.10;      // 时间常数（≈原 k=0.18@60fps 的手感）
      const VMAX = 520;      // px/s 速度上限 → 消"起步突变"
      const AMAX = 2400;     // px/s² 加速度上限 → 起步有 ease-in
      Object.keys(this.agents).forEach((id) => {
        const rec = this.agents[id];
        const dxT = rec.target.x - rec.container.x, dyT = rec.target.y - rec.container.y;
        const moving = Math.abs(dxT) > 0.7 || Math.abs(dyT) > 0.7;
        // 目标切换 → 按角色相位给 0..4 帧起步延迟（错峰；**只错渲染相位**）
        if (rec._lx !== rec.target.x || rec._ly !== rec.target.y) {
          rec._lx = rec.target.x; rec._ly = rec.target.y;
          rec._delayFrames = Math.floor((rec._ph / 6.2831853) * 5);
        }
        if (rec._delayFrames > 0) { rec._delayFrames--; rec._vx = rec._vy = 0; }
        else if (moving) {
          let vx = dxT / TAU, vy = dyT / TAU;
          const sp = Math.hypot(vx, vy);
          if (sp > VMAX) { vx *= VMAX / sp; vy *= VMAX / sp; }
          rec._vx = rec._vx || 0; rec._vy = rec._vy || 0;
          const dvx = vx - rec._vx, dvy = vy - rec._vy, dv = Math.hypot(dvx, dvy), dmax = AMAX * dt;
          if (dv > dmax && dv > 1e-6) { rec._vx += dvx * dmax / dv; rec._vy += dvy * dmax / dv; }
          else { rec._vx = vx; rec._vy = vy; }
          rec.container.x += rec._vx * dt;
          rec.container.y += rec._vy * dt;
          if (Math.abs(rec.target.x - rec.container.x) < 0.5 && Math.abs(rec.target.y - rec.container.y) < 0.5) {
            rec.container.x = rec.target.x; rec.container.y = rec.target.y; rec._vx = rec._vy = 0;
          }
        } else { rec._vx = rec._vy = 0; }
        const speed = Math.hypot(rec._vx || 0, rec._vy || 0);
        const walking = speed > 6;
        if (rec.sprite) {
          const alive = !rec._statusRef || rec._statusRef.v !== "dead";
          if (alive && rec.frames) {                 // 行走动画（不镜像，避免朝向错乱）
            if (walking) {
              rec._fr = (rec._fr + (0.9 + speed / 120) * dt * 9) % rec.frames.length;   // 步频 ∝ 实际速度
              rec.sprite.texture = rec.frames[Math.floor(rec._fr) % rec.frames.length];
            } else if (rec._fr !== 0) { rec._fr = 0; rec.sprite.texture = rec.frames[0]; }
            if (rec.outline) rec.outline.texture = rec.sprite.texture;   // 描边跟随帧
          }
          rec.sprite.y = 20 - (walking ? Math.abs(Math.sin((t + rec._ph) * 0.22)) * 2.5 : 0);
        }
        if (rec.glow) { rec.glow.x = rec.container.x; rec.glow.y = rec.container.y; }
      });
    }

    // 夜间灯火 / 昼夜色温：mode = 'day' | 'dusk' | 'night'
    setLighting(mode) {
      this._lightMode = mode || "day";
      const { width, height } = this.world;
      if (this._overlay && typeof this._overlay.clear === "function") this._overlay.clear();
      const P = { day: [0xffd9a0, 0.09], dusk: [0xff9a4a, 0.18], night: [0x101d3c, 0.52] }[this._lightMode] || [0x000000, 0];
      fillRect(this._overlay, 0, 0, width, height, P[0], P[1]);
      const ga = this._lightMode === "night" ? 0.95 : (this._lightMode === "dusk" ? 0.45 : 0.0);
      this._glowLayer.alpha = ga;
      this._glowLayer.visible = ga > 0.01;
      // 夜间：所有存活角色点亮自发光（画在 overlay 之上的 _glowLayer，确保不被夜色压暗）
      const night = this._lightMode === "night";
      Object.keys(this.agents).forEach((id) => {
        const rec = this.agents[id];
        const alive = !rec._statusRef || rec._statusRef.v !== "dead";
        if (rec.lantern) rec.lantern.visible = false;   // 容器内灯会被 overlay 压暗，弃用
        if (rec.glow) rec.glow.visible = night && alive;
        this._agentLight(rec);   // T120：夜间给角色夜光描边 + 接触影加重
      });
    }

    _buildGlows() {
      const P = global.PIXI;
      const G = this._glowLayer;
      // T120：光晕 = **有限色阶 + 有序抖动（ordered dithering）**——像素画表达"光/雾/半透明"的标准手法。
      // 既不是平滑渐变（不符合像素），也不是硬环（丢光感）：4 档 alpha，档间用 Bayer 棋盘抖动过渡。
      const CELL = 2;
      const BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
      const TIER = [0.62, 0.36, 0.18, 0.09];
      const dth = (cx, cy, xx, yy) => {
        const bx = (((cx + xx) / CELL) | 0) & 3, by = (((cy + yy) / CELL) | 0) & 3;
        return (BAYER[by][bx] + 0.5) / 16;
      };
      const addAt = (x, y, r, color) => {
        const g = new P.Graphics();
        const band = (cx, cy, R, mul) => {
          for (let yy = -R; yy < R; yy += CELL)
            for (let xx = -R; xx < R; xx += CELL) {
              const d = Math.sqrt(xx * xx + yy * yy) / R; if (d > 1) continue;
              const idx = d * TIER.length, i = Math.min(TIER.length - 1, Math.floor(idx)), f = idx - i;
              const a = (f > dth(cx, cy, xx, yy)) ? TIER[Math.min(TIER.length - 1, i + 1)] : TIER[i];
              fillRect(g, cx + xx, cy + yy, CELL, CELL, color, a * mul);
            }
        };
        // 地面暖光池（T124③：夜光"铺地"；T269③：加低频噪声斑驳=漫反射，破"均匀贴片"）
        for (let yy = -r * 1.3; yy < r * 1.3; yy += CELL)
          for (let xx = -r * 3.0; xx < r * 3.0; xx += CELL) {
            const d = Math.sqrt((xx / (r * 3.0)) ** 2 + (yy / (r * 1.3)) ** 2); if (d > 1) continue;
            const idx = d * TIER.length, i = Math.min(3, Math.floor(idx)), f = idx - i;
            const a = (f > dth(x, y + r, xx, yy)) ? TIER[Math.min(3, i + 1)] : TIER[i];
            const nz = W.hash2((((x + xx) / 5) | 0) + 7, (((y + r + yy) / 5) | 0) + 13, 555);   // 低频斑驳（漫反射）
            fillRect(g, x + xx, y + r + yy, CELL, CELL, color, a * 0.95 * (0.55 + 0.7 * nz));
          }
        band(x, y, r * 2.4, 1);        // 光晕主体（dither 环带，放大）
        G.addChild(g);
      };
      this.placeLayer.children.forEach((c) => {
        const gl = c.__glows || [];
        gl.forEach((p) => addAt(c.x + p[0], c.y + p[1], p[2], 0xffcf6a));
        (c.__smoke || []).forEach((p) => {
          const sg = new P.Graphics(), sx = c.x + p[0], sy = c.y + p[1];
          fillCircle(sg, sx, sy, 5, 0xe8e8e8, 0.55);
          fillCircle(sg, sx + 5, sy - 9, 6, 0xe8e8e8, 0.42);
          fillCircle(sg, sx + 11, sy - 18, 7, 0xe8e8e8, 0.30);
          fillCircle(sg, sx + 16, sy - 29, 8, 0xe8e8e8, 0.18);
          this._smokeLayer.addChild(sg);
        });
      });
      // T269③：夜光主次焦点 —— 中央广场给一处更大更暖的核心光（避免夜景"均匀贴片"）
      const hub = this.nodeById["plaza"];
      if (hub) addAt(hub.x, hub.y - 4, 13, 0xffd08a);
      (this._lampGlows || []).forEach((p) => addAt(p[0], p[1], 6, 0xffd98a));
      this.setLighting(this._lightMode || "day");
    }

    // ④ 事件提示：顶部横幅（死亡/复活/大额交易/关系质变等，叙事强化）
    setBanner(text) {
      const P = global.PIXI;
      if (!this._banner) {
        this._bannerLayer = new P.Container();
        this._bannerBg = new P.Graphics();
        this._banner = new P.Text("", { fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif', fontSize: 16, fill: 0xffffff, stroke: 0x0b0e12, strokeThickness: 5 });
        this._banner.anchor.set(0.5, 0);
        this._bannerLayer.addChild(this._bannerBg); this._bannerLayer.addChild(this._banner);
        this.lightLayer.addChild(this._bannerLayer);
      }
      if (!text) { this._bannerLayer.visible = false; return; }
      this._banner.text = text;
      const w = Math.max(180, this._banner.width + 30), h = this._banner.height + 12;
      const cx = this.world.width / 2, y = 12;
      this._banner.x = cx; this._banner.y = y + 6;
      if (this._bannerBg.clear) this._bannerBg.clear();
      W.fillRound(this._bannerBg, cx - w / 2, y, w, h, 8, 0x101418, 0.74);
      W.strokeRound(this._bannerBg, cx - w / 2, y, w, h, 8, 0xffe08a, 2);
      this._bannerLayer.visible = true;
    }

    // 场所旁"事件气泡"：list=[{placeId,text}]（如 {placeId:'hall',text:'礼堂：3 人离世'}）
    setHappenings(list) {
      const P = global.PIXI;
      list = list || [];
      this._hap = this._hap || [];
      while (this._hap.length < list.length) {
        const c = new P.Container();
        const g = new P.Graphics();
        const t = new P.Text("", { fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif', fontSize: 12, fill: 0x101418, backgroundColor: 0xfff2c8, padding: 3 });
        t.anchor.set(0.5, 1);
        c.addChild(g); c.addChild(t);
        this.lightLayer.addChild(c);
        this._hap.push({ c: c, t: t, g: g });
      }
      this._hap.forEach((h, i) => {
        const e = list[i];
        if (!e) { h.c.visible = false; return; }
        const nd = this.nodeById[e.placeId] || { x: this.world.width / 2, y: this.world.height / 2 };
        h.t.text = e.text; h.c.visible = true; h.c.x = nd.x; h.c.y = nd.y - 74;
        try { h.c.zIndex = 99999; } catch (err) { /* mock */ }
      });
    }

  }

  global.HITTTown = { Town, texFromURL };
})(window);
