/* assets.js — 独立像素资产库的「按 id 引用」加载器（T72）。
 *
 * 读 assets/assets_manifest.json，把 generated/** 的 PNG 载入为 PIXI.BaseTexture，
 * 暴露 HITTAssets.texture(id) / anchor(id) / meta(id)。
 *
 * 纪律：
 *  - **纯加载器**，不改世界、不参与判定；不改变现有 assets/ 路径（AI Town 素材仍可回退）。
 *  - 可选接入：是否在 town.js/sprites.js 使用由 art-director 决定；本文件不进入 smoke_test 依赖。
 *
 * 用法：
 *   const A = await HITTAssets.load("assets/assets_manifest.json");
 *   const tex = A.texture("place.residence");   // → PIXI.Texture（NEAREST）
 *   const a = A.anchor("place.residence");      // → [64, 120]
 */
(function (global) {
  "use strict";

  function loadImage(P, url) {
    // Node（smoke_test 环境）：无 Image/无 DOM → 用 PIXI.BaseTexture.from 占位
    if (typeof document === "undefined" && !(P.Assets && P.Assets.load)) {
      return Promise.resolve(P.BaseTexture && P.BaseTexture.from ? P.BaseTexture.from(url) : null);
    }
    return new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => resolve(P.BaseTexture.from(img));
      img.onerror = () => resolve(null);           // 缺图不阻塞，运行时退化为无纹理
      img.src = url;
    });
  }

  const HITTAssets = {
    manifest: null,
    byId: {},
    bases: {},

    async load(manifestUrl, PIXI_IN) {
      const P = PIXI_IN || global.PIXI;
      const res = await fetch(manifestUrl, { cache: "no-cache" });
      const m = await res.json();
      this.manifest = m;
      this.byId = {};
      (m.assets || []).forEach((e) => { this.byId[e.id] = e; });
      const base = (manifestUrl || "").replace(/[^/]*$/, "");   // assets/
      for (const e of m.assets || []) {
        const bt = await loadImage(P, base + e.file);
        if (bt && P.SCALE_MODES) { try { bt.scaleMode = P.SCALE_MODES.NEAREST; } catch (x) { /* ignore */ } }
        this.bases[e.id] = bt;
      }
      return this;
    },

    meta(id) { return this.byId[id] || null; },
    anchor(id) { const e = this.byId[id]; return e ? (e.anchor || [0, 0]) : [0, 0]; },

    /** 返回 PIXI.Texture：整图；动帧可传 frame 索引用 frameSize 切分。 */
    texture(id, frame) {
      const e = this.byId[id], P = global.PIXI, base = this.bases[id];
      if (!e || !base) return null;
      if (frame != null && e.frameSize) {
        const [fw, fh] = e.frameSize;
        return new P.Texture(base, new P.Rectangle(frame * fw, 0, fw, fh));
      }
      return new P.Texture(base, new P.Rectangle(0, 0, e.size[0], e.size[1]));
    },

    /** 图标图集（供审计台 ICON_ATLAS 钩子）。 */
    iconAtlas() { return this.manifest && this.manifest.iconAtlas && this.manifest.iconAtlas.atlas; },
  };

  global.HITTAssets = HITTAssets;
})(typeof window !== "undefined" ? window : globalThis);
