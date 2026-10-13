/* main.js — 启动 / 游戏化 shell（只读）。
 * 数据流：config(places/topology) + 事件日志(JSONL) → Replay 折叠 → Pixi 渲染 + 审计台。
 * shell 职责：近全屏地图、可折叠抽屉、悬浮控制、昼夜光照、镜头缩放平移、关键事件高亮、点击详情。
 * 纪律：只读日志/config，不写世界、不参与判定。
 */
(function () {
  "use strict";

  const D = window.HITTData;
  const R = window.HITTReplay;

  const el = (id) => document.getElementById(id);
  const state = { places: [], topology: null, replay: null, round: 0, timer: null, playing: false, source: "", sel: null, still: false, snapAgents: false, personas: {}, seqRound: null, auditTab: "chronicle", view: "default", explicitView: false, fx: true, fxHold: false };
  const cam = { scale: 1, x: 0, y: 0 };

  const town = { inst: null };
  let audit = null;
  let fxLayer = null;

  function showError(msg) { const b = el("error-box"); b.hidden = false; b.textContent = "⚠ " + msg; }
  function clearError() { el("error-box").hidden = true; }

  async function boot() {
    try {
      const qs = new URLSearchParams(location.search);
      state.still = qs.get("still") === "1";       // 单帧模式：只渲一帧后停 ticker/rAF
      state.snapAgents = state.still;
      state.live = qs.get("live") || null;         // LIVE 跟随模式：轮询增量日志
      state.liveTail = qs.get("tail") === "1";     // T343：走 /__tail 增量尾读（跟随正在增长的日志）
      state.liveTailMb = parseInt(qs.get("tailmb"), 10) || 4;   // 首轮尾部窗口大小（MB）
      state.following = qs.get("follow") !== "0";   // 默认跟随最新
      state.explicitView = !!qs.get("view");        // URL 显式指定分层时，缩放不自动覆盖
      // 像素锐利：全局最近邻缩放
      if (window.PIXI && PIXI.SCALE_MODES && PIXI.BaseTexture && PIXI.BaseTexture.defaultOptions) {
        PIXI.BaseTexture.defaultOptions.scaleMode = PIXI.SCALE_MODES.NEAREST;
      }
      const [placesDoc, topology] = await Promise.all([
        D.loadJSON("data/places.json"),
        D.loadJSON("data/topology.json"),
      ]);
      state.places = placesDoc.places || placesDoc;
      state.topology = topology;

      // 人格（角色卡用）
      try {
        const pd = await D.loadJSON("data/personas.json");
        (pd.personas || pd).forEach((x) => { state.personas[x.persona_id] = x; });
      } catch (e) { console.warn("personas 载入失败", e); }

      // 图标图集单一真源：由 art-director 的 src/sprites.js 静态常量 HITTSprites.ICON_ATLAS 提供，
      // audit.js 只消费、不在此重设（避免两份口径）。清单 HITTAssets 供 town/sprites 按需消费。

      town.inst = new window.HITTTown.Town(el("pixi-host"), state.places, state.topology);
      town.inst.app.ticker.add(() => town.inst.tick());
      fxLayer = new PIXI.Container();
      town.inst.app.stage.addChild(fxLayer);
      audit = new window.HITTAudit.Audit(el("kfacts"), el("event-stream"), el("ev-count"));
      audit.ctx = { name: nameOf, place: placeNameOf };
      audit.onOpenAgent = (id) => selectAgent(id);
      audit.onJumpRound = (r) => { stopPlay(); pauseFollow(); jumpTo(r); };
      audit._expandSeq = qs.get("expand");   // 证据用：自动展开某行详情（剧情卡因果链）
      renderLegend();

      const loadP = town.inst.load("assets/").catch((e) => {
        console.warn("素材加载失败，退回纯日志回放:", e);
        showError("美术素材加载失败：" + e.message);
      });
      // still 模式：等素材完整加载（首帧即完整视觉）；常规模式：超时兜底不阻塞回放
      if (state.still) { await loadP; }
      else { await Promise.race([loadP, new Promise((r) => setTimeout(r, 4000))]); }

      wireControls();
      wireCamera();
      applyCam();
      setView(qs.get("view") || "default");   // 默认 default：建筑名可见、NPC ID 隐藏

      // T343：tail 模式的 live 路径是**外部绝对路径**（经 /__tail 读），不能当普通日志 URL 加载（会 404 中断 boot）；
      // 故首屏先用一个内置样例把 boot 走完，随后 startLiveTail 会立即用尾读结果替换 replay。
      const logUrl = state.liveTail ? "sample/demo_run.jsonl" : (state.live || qs.get("log") || "sample/demo_run.jsonl");
      const sampleSel = el("sample-select");
      Array.from(sampleSel.options).forEach((o) => { if (o.value === logUrl) sampleSel.value = logUrl; });
      await loadLogFromURL(logUrl);

      const rq = qs.get("round");
      if (rq != null && state.replay) { stopPlay(); jumpTo(parseInt(rq, 10) || 0); }
      // T259-B 播放件：?speed=<ms> 定速；?autoplay=1 载入即自动播放（供真人盲测片段）
      // T259 修观感：首屏默认拉近 + 聚焦活动最密处（"离远看哪哪都一样"→"看成一个地方"）。
      // ?cam=fit 保留旧的全景行为（可回退对照）；?camscale=<name> 调焦聚倍率。仅在未显式定位时生效。
      if (qs.get("cam") !== "fit") {
        const cs = parseFloat(qs.get("camscale")) || 1.6;
        focusCamera(cs);
      }
      const sp = qs.get("speed");
      if (sp) el("speed-select").value = String(sp);
      if (qs.get("autoplay") === "1" && state.replay) play();

      // 证据截图用：?card=<slug> 直接放大某张事件卡（如 card=scarcity-buy）
      const cardSlug = qs.get("card");
      if (cardSlug && audit && audit.openCardArt) {
        const base = (window.HITTSprites && window.HITTSprites.EVENT_CARD_BASE) || "";
        audit.openCardArt(base + cardSlug + ".png");
      }

      // LIVE 跟随模式（T75）：轮询增量日志、平滑推进到最新
      if (state.live) {
        el("live-box").hidden = false;
        el("btn-follow").textContent = state.following ? "⏸ 暂停跟随" : "▶ 跟随最新";
        el("btn-follow").onclick = () => {
          state.following = !state.following;
          el("btn-follow").textContent = state.following ? "⏸ 暂停跟随" : "▶ 跟随最新";
          if (state.following && state.replay) jumpTo(state.replay.maxRound);
        };
        startLive();
      }

      // 便于截图/演示：?audit=1 打开审计抽屉；?agent=<id> 或 ?place=<id> 打开详情
      if (qs.get("audit") === "1") openDrawer("audit");
      if (qs.get("debug") === "1") document.body.classList.add("show-debug");   // 证据截图用：展开调试/回放控件
      // T259 层次层对照：?grade=0 关闭天空/暗角/地面渐隐（"改前"截图用）
      if (qs.get("grade") === "0") document.body.classList.add("no-grade");
      // T279 事件表现对照：?ticker=0 关闭最近事件走马条（"改前"截图用）
      if (qs.get("ticker") === "0") document.body.classList.add("no-ticker");
      if (["social","weekly","chronicle","econ"].includes(qs.get("tab"))) { openDrawer("audit"); switchAuditTab(qs.get("tab")); }
      if (qs.get("settings") === "1") el("settings-pop").hidden = false;
      if (qs.get("agent")) selectAgent(qs.get("agent"));
      else if (qs.get("place")) selectPlace(qs.get("place"));
      // 关键帧说明条（?caption=文字）
      const cap = qs.get("caption");
      if (cap) { const c = el("caption"); c.textContent = cap; c.hidden = false; }

      // G-13：?fx=0 关闭世界内反馈（"改前"对照）；?fxhold=1 保持峰值（still 取证）；?fxg=<trade|conflict|norm> 触发一次演示
      if (qs.get("fx") === "0") state.fx = false;
      if (qs.get("fxhold") === "1") state.fxHold = true;
      const fxg = qs.get("fxg");
      if (fxg) {
        state.fxHold = true;
        const ids = Object.keys(town.inst.agents);
        if (fxg === "dm") { const a = agentXY(ids[0]), b = agentXY(ids[1] || ids[0]); if (a && b) worldFx("dm", a.x, a.y, b.x, b.y); }
        else {
          const pos = (fxg === "trade") ? placeXY("market")
            : (fxg === "norm" || fxg === "seed") ? placeXY("plaza")
            : (agentXY(ids[0]) || placeXY("plaza"));
          if (pos) worldFx(fxg, pos.x, pos.y);
        }
      }

      // 单帧模式：快照后停掉持续渲染，置就绪标志供截图脚本等待
      if (state.still) finalizeStill();
    } catch (e) {
      showError(e.message + "（请用 tools/serve.py 启动本地服务，而非 file:// 直接打开）");
      console.error(e);
    }
  }

  function renderLegend() {
    const styles = window.HITTSprites.CATEGORY_STYLE;
    el("hud-legend").innerHTML = Object.keys(styles).map((k) => {
      const hex = "#" + styles[k].wall.toString(16).padStart(6, "0");
      return `<span><i style="background:${hex}"></i>${styles[k].name}</span>`;
    }).join("");
  }

  // 名字/场所解析（用 display_name / name_cn，退回 id）
  let __placeById = null;
  function nameOf(id) { if (!id) return ""; const p = state.personas[id]; return p ? p.display_name : id; }
  function placeNameOf(id) {
    if (!id) return "";
    if (!__placeById) { __placeById = {}; state.places.forEach((p) => { __placeById[p.place_id] = p; }); }
    const p = __placeById[id]; return p ? p.name_cn : id;
  }

  // ---------------- 日志 ----------------
  async function loadLogFromURL(url) {
    clearError(); setSource("载入中… " + url);
    const text = await D.loadText(url);
    applyLogText(text, url);
  }
  function applyLogText(text, label) {
    const records = D.parseJSONL(text);
    if (!records.length) throw new Error("日志为空或不含事件");
    state.replay = new R.Replay(records);
    state.round = state.replay.rounds[0] || 0;
    // seq → round 索引（因果链接跳转用）；seq → record（剧情卡因果链用）
    state.seqRound = {};
    const bySeq = {};
    for (const rec of records) { if (rec.seq != null) { state.seqRound[rec.seq] = rec.round; bySeq[rec.seq] = rec; } }
    state.eventsBySeq = bySeq;
    if (audit) { audit._seqIndex = state.seqRound; audit._eventsBySeq = bySeq; }
    const slider = el("round-slider");
    slider.min = String(state.replay.rounds[0] || 0);
    slider.max = String(state.replay.maxRound);
    slider.value = String(state.round);
    setSource(label);
    closeInspector();
    renderRound(false);
    stopPlay();
  }
  function setSource(s) { state.source = s; el("source-badge").textContent = s; el("source-badge").title = s; }

  // ---------------- LIVE 跟随（T75）----------------
  // 轮询增量日志：发现新回合则重建 Replay；跟随开启时平滑推进到最新。
  let liveTimer = null;
  function startLive() {
    // T343：`?live=<abs>&tail=1` → 走只读增量端点 /__tail（跟随正在增长的日志，**不整文件重下**）。
    if (state.liveTail) { startLiveTail(); return; }
    const path = state.live;
    const poll = async () => {
      try {
        const text = await D.loadText(path + (path.includes("?") ? "&" : "?") + "_=" + Date.now());
        const recs = D.parseJSONL(text);
        if (recs.length && (!state.replay || recs.length !== state.replay.totalEvents)) {
          const prev = state.replay ? state.replay.totalEvents : -1;
          state.replay = new R.Replay(recs);
          const maxR = state.replay.maxRound;
          el("live-round").textContent = `round ${maxR} · ${recs.length} 事件`;
          el("round-slider").max = String(maxR);
          if (state.following) { state.round = maxR; renderRound(false); }
          else if (prev < 0) { renderRound(false); }
        }
      } catch (e) { /* 文件可能尚未生成/更新中 */ }
      liveTimer = setTimeout(poll, 600);
    };
    poll();
  }

  // ---- T343 实时跟随（增量尾读）----
  // 只随增长取字节（/__tail）；**节流**重建 Replay；**显式状态**（跟随中/无增长/已结束/读取失败）；
  // 首轮为**尾部窗口**（末尾 N MB，行对齐）——界面标注，别误读成"从头回放"。
  function setLiveStatus(s) { const e = el("live-status"); if (e) e.textContent = s; }
  function inferBatch(path) {
    const s = String(path);
    const m = s.match(/nightly\/([A-Za-z0-9]+)\//) || s.match(/\/runs\/([A-Za-z0-9_-]+)\//);
    return m ? m[1] : "—";
  }
  function startLiveTail() {
    const path = state.live;
    const POLL = 1500, MIN_BUILD = 3000;   // 轮询间隔 / 重建节流（首次有数据立即重建）
    let off = null, all = [], lastSize = -1, idle = 0, built = false, lastBuild = 0;
    if (el("live-batch")) el("live-batch").textContent = "批次 " + inferBatch(path);
    setLiveStatus("连接中…");
    const poll = async () => {
      let j = null;
      try {
        const u = `/__tail?path=${encodeURIComponent(path)}&tailmb=${state.liveTailMb}` + (off == null ? "" : `&off=${off}`);
        j = await (await fetch(u, { cache: "no-store" })).json();
      } catch (e) { setLiveStatus("读取失败：" + (e && e.message)); liveTimer = setTimeout(poll, POLL); return; }
      if (j.error) { setLiveStatus("读取失败：" + j.error); liveTimer = setTimeout(poll, POLL); return; }
      if (j.waiting) { setLiveStatus("等待新数据（文件未出现）"); liveTimer = setTimeout(poll, POLL); return; }
      const grew = j.size !== lastSize;
      const recs = j.text ? D.parseJSONL(j.text) : [];
      if (recs.length) all = all.concat(recs);
      off = j.off;
      const now = performance.now();
      if (recs.length && (!built || now - lastBuild >= MIN_BUILD)) {   // 首次立即重建；其后节流
        state.replay = new R.Replay(all);
        built = true; lastBuild = now;
        el("round-slider").max = String(state.replay.maxRound);
        if (state.following) { state.round = state.replay.maxRound; renderRound(false); }
      }
      const maxR = state.replay ? state.replay.maxRound : "—";
      el("live-round").textContent = `round ${maxR} · ${all.length} 事件`;
      idle = (recs.length || grew) ? 0 : idle + 1;
      lastSize = j.size;
      const idleSec = Math.round(idle * POLL / 1000);
      const win = j.truncated ? "尾部窗口·" : "";
      // ⚠️ 跑批在两次 flush 之间"已追平(eof)"是**正常**，不能当"已结束"；只在**长时间**无增长才提示可能结束（且不停轮询）。
      let st;
      if (recs.length || grew) st = "跟随中";
      else if (idleSec < 300) st = "已追平（等待新数据）";
      else st = "长时间无增长（可能已结束）";
      setLiveStatus(win + st);
      // T348/T375：批状态三态（还在跑 / 完成rc=0 / 挂了rc≠0）——一眼可判，且"挂了"必须显眼。
      let info = null;
      try { info = await (await fetch(`/__runinfo?path=${encodeURIComponent(path)}`, { cache: "no-store" })).json(); } catch (e) { }
      if (info && !info.error) {
        const LBL = { running: "运行中", done: "完成（rc=0）", failed: "失败（rc≠0）" };
        const lbl = LBL[info.state] || info.state || "";
        if (el("live-batch")) el("live-batch").textContent = `批次 ${info.batch || inferBatch(path)} · ${lbl}`;
        if (info.state === "failed") {
          setLiveStatus(`⚠ 批失败（rc=${info.rc}）· 见 host.log · 已停止跟随`);
          liveTimer = null; return;
        }
        if (info.state === "done") {
          setLiveStatus("跟随已结束（批已完成" + (info.ended_at ? "，" + info.ended_at : "") + "）· 可回放（尾部窗口 " + all.length + " 事件）");
          liveTimer = null; return;
        }
      } else if (info && info.ended) {   // 兜底：无 state 但有 ended
        setLiveStatus("跟随已结束（批已结束）· 可回放");
        liveTimer = null; return;
      }
      liveTimer = setTimeout(poll, POLL);
    };
    poll();
  }
  function pauseFollow() {
    if (state.live && state.following) {
      state.following = false;
      const b = el("btn-follow");
      if (b) b.textContent = "▶ 跟随最新";
    }
  }

  // ---------------- 回合渲染 ----------------
  function renderRound(animateFx = true) {
    const rp = state.replay;
    if (!rp) return;
    const rd = state.round;
    town.inst.renderState(rp.displayState(rd));
    // T116：角色可能在渲染中新建 → 每回合重申当前信息分层（info 才显 NPC ID）
    if (typeof town.inst.setMode === "function") town.inst.setMode(state.view);
    if (state.snapAgents) snapAgents();
    audit.renderFacts(rp, rd);
    audit._seqIndex = state.seqRound;
    audit.renderStream(rp, rd);
    el("round-slider").value = String(rd);
    el("round-label").textContent = `round ${rd} / ${rp.maxRound}`;
    renderClock(rp, rd);
    renderTimebar(rp, rd);
    renderLighting(rp, rd);
    renderEvticker(rp, rd);   // 事件表现：最近事件走马条（纯展示，随回合确定性派生）
    if (animateFx && !state.still) handleKeyEvents(rp, rd);
    if (state.auditTab === "social" && audit && audit.renderSocial) audit.renderSocial(rp, rd);
    else if (state.auditTab === "weekly" && audit && audit.renderWeekly) audit.renderWeekly(rp, rd);
    else if (state.auditTab === "econ" && audit && audit.renderEcon) audit.renderEcon(rp, rd);
    if (state.sel) refreshInspector();   // 详情面板跟随当前回合
  }

  // 仅重绘事件流（筛选/搜索/审计模式切换时）
  function rerenderStream() {
    if (!state.replay || !audit) return;
    audit._seqIndex = state.seqRound;
    audit.renderStream(state.replay, state.round);
  }

  // 单帧模式：把角色直接放到目标位置（跳过逐帧平滑）
  function snapAgents() {
    Object.keys(town.inst.agents).forEach((id) => {
      const rec = town.inst.agents[id];
      if (rec && rec.target) { rec.container.x = rec.target.x; rec.container.y = rec.target.y; }
    });
  }

  // 单帧模式收尾：停 ticker / rAF，渲染最后一帧，置 __RENDER_READY__
  function finalizeStill() {
    const app = town.inst.app;
    try { app.ticker.stop(); } catch (e) { /* noop */ }
    if ("autoStart" in app.ticker) app.ticker.autoStart = false;
    const paint = () => { try { app.renderer.render(app.stage); } catch (e) {} };
    paint();
    requestAnimationFrame(() => {
      paint();
      requestAnimationFrame(() => {
        paint();
        window.__RENDER_READY__ = true;
        try { document.documentElement.setAttribute("data-render-ready", "1"); } catch (e) {}
      });
    });
  }

  function renderClock(rp, rd) {
    const w = R.wallClock(rd);
    let t = null;
    for (let r = rd; r >= 0; r--) { const tt = rp.timeOf(r); if (tt) { t = tt; break; } }
    const week = t ? ` · week ${t.week} ${t.day_type}` : "";
    // 周/日型属"调试信息"，默认折叠；时钟只留"第X日 HH:MM（时段）"
    el("hud-clock").innerHTML = `第 ${w.day} 日 ${w.hhmm}（${w.slotName}）` +
      (week ? `<span class="debug-only">${escapeHtml(week)}</span>` : "");
  }

  // ---- 昼夜光照（纯氛围；按 TIME_MARK 的 slot，缺省用挂钟槽位）----
  const LIGHT = [
    "linear-gradient(rgba(255,190,110,0.16), rgba(255,190,110,0.07))", // morning 晨暖
    "linear-gradient(rgba(255,255,255,0.0), rgba(255,255,255,0.0))",   // afternoon 午亮
    "linear-gradient(rgba(255,130,45,0.24), rgba(255,80,25,0.14))",    // evening 晚橙
    "linear-gradient(rgba(20,36,92,0.52), rgba(10,18,54,0.62))",       // night 夜深蓝（明显）
  ];
  function renderLighting(rp, rd) {
    // slot 由 round 确定性派生（slot_idx = (round%12)//3），与引擎口径一致。
    // 注意：TIME_MARK 只在每天起始（morning）触发，不能用来判断当日其它时段。
    const slotIdx = R.wallClock(rd).slotIdx;
    const key = ["day", "day", "dusk", "night"][slotIdx];   // ← 交给 art-director 的 town.setLighting
    if (town.inst && typeof town.inst.setLighting === "function") {
      town.inst.setLighting(key);
      el("lighting").style.background = "none";             // 由 town 的 glow/光照层负责
    } else {
      el("lighting").style.background = LIGHT[slotIdx] || "none";  // 回退：CSS 覆盖层
    }
  }

  function renderTimebar(rp, rd) {
    const bar = el("timebar");
    if (!bar) return;
    if (bar.__max === rp.maxRound && bar.__n === rp.rounds.length) { updateTimebarCurrent(bar, rd); return; }
    bar.__max = rp.maxRound; bar.__n = rp.rounds.length;
    const cells = rp.rounds.map((r) => {
      const w = R.wallClock(r);
      const cls = ["cell", ["morning", "afternoon", "evening", "night"][w.slotIdx]];
      if (r % 3 === 0) cls.push("slot-start");
      if (r % 12 === 0) cls.push("day-start");
      return `<div class="${cls.join(" ")}" data-round="${r}" title="round ${r} · 第${w.day}日 ${w.hhmm} ${w.slotName}"></div>`;
    });
    bar.innerHTML = cells.join("");
    updateTimebarCurrent(bar, rd);
  }
  function updateTimebarCurrent(bar, rd) {
    bar.querySelectorAll(".cell").forEach((c) => c.classList.toggle("current", Number(c.dataset.round) === rd));
  }

  // ---------------- 关键事件高亮 + 提示条 ----------------
  const KEY_EVENTS = {
    AGENT_DIED: { icon: "💀", pri: 5 },
    AGENT_REVIVED: { icon: "✨", pri: 5 },
    MARKET_TRADE: { icon: "🛒", pri: 3 },
    RELATION_CHANGE: { icon: "🤝", pri: 2 },
    NORM_ADOPTED: { icon: "📜", pri: 4 },
    NORM_VIOLATED: { icon: "🚫", pri: 4 },
    ROLE_CHANGE: { icon: "🔄", pri: 3 },
    GROUP_CREATED: { icon: "👥", pri: 3 },
    SEED_EVENT: { icon: "🌱", pri: 4 },
    CONFLICT_STARTED: { icon: "⚔️", pri: 4 },
    GOAL_ACHIEVED: { icon: "🏆", pri: 4 },
    SKILL_LEVEL_UP: { icon: "⭐", pri: 3 },
    MSG_DM: { icon: "💬", pri: 2 },
  };
  let toastTimer = null;
  function handleKeyEvents(rp, rd) {
    const evs = rp.eventsInRound(rd).filter((e) => KEY_EVENTS[e.type]);
    const ctx = (audit && audit.ctx) || { name: nameOf, place: placeNameOf };
    if (!evs.length) {
      if (town.inst && town.inst.setBanner) town.inst.setBanner("");
      if (town.inst && town.inst.setHappenings) town.inst.setHappenings([]);
      return;
    }
    evs.sort((a, b) => (KEY_EVENTS[b.type].pri - KEY_EVENTS[a.type].pri));
    const top = evs[0];
    const meta = KEY_EVENTS[top.type];
    const topH = R.humanize(top, ctx);
    showToast(meta.icon, topH.text);
    // 顶部横幅（art-director 的 setBanner；叙事强化）
    if (town.inst && town.inst.setBanner) town.inst.setBanner(`${meta.icon} ${topH.text}`);
    // 场所旁事件气泡（setHappenings）：按地点归并，最多 4 处
    const disp = (rp.displayState(rd) || {}).agents || {};
    const hap = [], seen = {};
    for (const e of evs) {
      const p = e.payload || {};
      let placeId = null;
      if (e.type === "MARKET_TRADE") placeId = "market";
      else { const aid = p.agent_id || p.from || p.buyer; if (aid && disp[aid]) placeId = disp[aid].location; }
      if (!placeId || seen[placeId]) continue;
      seen[placeId] = 1;
      const t = R.humanize(e, ctx).text;
      hap.push({ placeId, text: t.length > 20 ? t.slice(0, 19) + "…" : t });
      if (hap.length >= 4) break;
    }
    if (town.inst && town.inst.setHappenings) town.inst.setHappenings(hap);
    // 高亮 + G-13 世界内反馈：交易→市场(金)；冲突→当事人(红叹号)；规范采纳→广场(金环)；其余→相关角色
    evs.slice(0, 4).forEach((e) => {
      const p = e.payload || {};
      const aid = p.agent_id || p.from || p.buyer || p.winner || (p.parties && p.parties[0]);
      if (e.type === "MARKET_TRADE") { highlightPlace("market"); const m = placeXY("market"); if (m) worldFx("trade", m.x, m.y); }
      else if (e.type === "CONFLICT_STARTED" || e.type === "CONFLICT_RESOLVED") { const a = agentXY(aid); if (a) worldFx("conflict", a.x, a.y); else { highlightAgent(aid); } }
      else if (e.type === "NORM_ADOPTED" || e.type === "NORM_PROPOSED") { const pl = placeXY("plaza"); if (pl) worldFx("norm", pl.x, pl.y); highlightPlace("town_hall"); }
      else if (e.type === "SEED_EVENT") { const pl = placeXY("plaza"); if (pl) worldFx("seed", pl.x, pl.y); }
      else if (e.type === "GOAL_ACHIEVED") { const a = agentXY(aid); if (a) worldFx("celebrate", a.x, a.y); }
      else if (e.type === "GROUP_CREATED") { const a = agentXY(aid); if (a) worldFx("group", a.x, a.y); }
      else if (e.type === "SKILL_LEVEL_UP") { const a = agentXY(aid); if (a) worldFx("skill", a.x, a.y); }
      else if (e.type === "MSG_DM") { const f = agentXY(p.from); const t = agentXY(p.to); if (f && t) worldFx("dm", f.x, f.y, t.x, t.y); }
      else if (aid) highlightAgent(aid);
    });
  }
  function showToast(icon, text) {
    el("toast-icon").textContent = icon;
    el("toast-text").textContent = text;
    const t = el("toast");
    t.hidden = false;
    requestAnimationFrame(() => t.classList.add("show"));
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.classList.remove("show"); setTimeout(() => { t.hidden = true; }, 300); }, 2600);
  }

  function pulse(obj, base, peak, dur) {
    if (!obj || !window.PIXI) return;
    const start = performance.now();
    const tick = () => {
      const k = Math.min(1, (performance.now() - start) / dur);
      const s = base + (peak - base) * Math.sin(k * Math.PI);
      obj.scale.set(s);
      if (k < 1) requestAnimationFrame(tick);
      else obj.scale.set(base);
    };
    requestAnimationFrame(tick);
  }
  function highlightAgent(id) {
    const rec = town.inst.agents[id];
    if (!rec) return;
    pulse(rec.container, 1, 1.6, 900);
    ringFx(rec.container.x, rec.container.y, 0x5cc8ff);
  }
  function highlightPlace(pid) {
    const child = town.inst.placeLayer.children.find((c) => c.__placeId === pid);
    if (!child) return;
    pulse(child, 1, 1.12, 800);
    ringFx(child.x, child.y, 0xffcf5c);
  }
  function ringFx(x, y, color) {
    if (!fxLayer || !window.PIXI) return;
    const g = new PIXI.Graphics();
    g.lineStyle(3, color, 1); g.drawCircle(0, 0, 14);
    g.x = x; g.y = y;
    fxLayer.addChild(g);
    const start = performance.now(), dur = 1000;
    const tick = () => {
      const k = Math.min(1, (performance.now() - start) / dur);
      g.scale.set(0.6 + k * 1.8);
      g.alpha = 1 - k;
      if (k < 1) requestAnimationFrame(tick);
      else { fxLayer.removeChild(g); g.destroy(); }
    };
    requestAnimationFrame(tick);
  }

  // ---- G-13 世界内反馈短动效（只读；复用 fxLayer；`?fx=0` 关闭用于"改前"对照）----
  function placeXY(pid) { const n = town.inst && town.inst.nodeById && town.inst.nodeById[pid]; return n ? { x: n.x, y: n.y } : null; }
  function agentXY(id) { const r = town.inst && town.inst.agents && town.inst.agents[id]; return r ? { x: r.container.x, y: r.container.y } : null; }
  // 峰值图形（still/`?fxhold=1` 下保持不动，便于可复现取证；否则短促放大淡出）
  function worldFx(kind, x, y, x2, y2) {
    if (!state.fx || !fxLayer || !window.PIXI || x == null) return;
    const g = new PIXI.Graphics();
    let label = "";
    if (kind === "trade") {                                   // 成交：金环 + 上浮金币
      g.lineStyle(4, 0xffcf5c, 1); g.drawCircle(0, 0, 26);
      g.beginFill(0xffd76a, 1); [-16, 0, 16].forEach((dx, i) => g.drawCircle(dx, -34 - i * 5, 6)); g.endFill();
      label = "🪙 成交";
    } else if (kind === "conflict") {                         // 冲突：红色叹号 + 红环
      g.lineStyle(4, 0xe4572e, 1); g.drawCircle(0, 0, 24);
      g.beginFill(0xe4572e, 1); g.drawRect(-3, -44, 6, 20); g.drawRect(-3, -20, 6, 6); g.endFill();
      label = "⚔ 冲突";
    } else if (kind === "norm") {                             // 规范采纳：金色双环
      g.lineStyle(4, 0xf0c14a, 1); g.drawCircle(0, 0, 28);
      g.lineStyle(2, 0xf0c14a, 0.7); g.drawCircle(0, 0, 42);
      label = "📜 采纳";
    } else if (kind === "seed") {                             // 种子事件：绿环 + 芽
      g.lineStyle(4, 0x6fcf6b, 1); g.drawCircle(0, 0, 26);
      g.beginFill(0x6fcf6b, 1); g.drawEllipse(0, -30, 8, 5); g.endFill();
      label = "🌱 种子";
    } else if (kind === "celebrate") {                        // 目标达成：金环 + 星
      g.lineStyle(4, 0xffd76a, 1); g.drawCircle(0, 0, 28);
      g.beginFill(0xfff2a0, 1); g.drawPolygon([0, -46, 5, -38, 14, -38, 7, -32, 10, -23, 0, -28, -10, -23, -7, -32, -14, -38, -5, -38]); g.endFill();
      label = "🏆 达成";
    } else if (kind === "group") {                            // 组队：青绿环 + 两点
      g.lineStyle(4, 0x66e0c0, 1); g.drawCircle(0, 0, 26);
      g.beginFill(0x66e0c0, 1); g.drawCircle(-9, -30, 5); g.drawCircle(9, -30, 5); g.endFill();
      label = "👥 组队";
    } else if (kind === "skill") {                            // 技能升级：蓝环 + 星
      g.lineStyle(4, 0x5cc8ff, 1); g.drawCircle(0, 0, 24);
      g.beginFill(0xbfe6ff, 1); g.drawCircle(0, -30, 5); g.endFill();
      label = "⭐ 升级";
    } else if (kind === "dm") {                               // 私聊：两点连线 + 气泡
      if (x2 != null) {
        g.lineStyle(3, 0x5cc8ff, 0.9); g.moveTo(0, 0); g.lineTo(x2 - x, y2 - y);
        g.beginFill(0x5cc8ff, 1); g.drawCircle(0, 0, 4); g.drawCircle(x2 - x, y2 - y, 4); g.endFill();
      } else { g.lineStyle(3, 0x5cc8ff, 1); g.drawCircle(0, 0, 18); }
      label = "💬 私聊";
    } else { g.lineStyle(4, 0x5cc8ff, 1); g.drawCircle(0, 0, 24); }
    g.x = x; g.y = y; fxLayer.addChild(g);
    let tx = null;
    if (label) {
      tx = new PIXI.Text(label, { fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif', fontSize: 15,
        fill: 0xffffff, stroke: 0x0b0e12, strokeThickness: 5 });
      tx.anchor.set(0.5, 1); tx.x = x; tx.y = y - 46; fxLayer.addChild(tx);
    }
    if (state.fxHold) { g.alpha = 1; g.scale.set(1.15); if (tx) tx.alpha = 1; return; }   // 证据：保持峰值
    const start = performance.now(), dur = 1200;
    const tick = () => {
      const k = Math.min(1, (performance.now() - start) / dur);
      g.scale.set(0.7 + k * 1.5); g.alpha = 1 - k;
      if (tx) { tx.alpha = 1 - k; tx.y = y - 46 - k * 14; }
      if (k < 1) requestAnimationFrame(tick);
      else { fxLayer.removeChild(g); g.destroy(); if (tx) { fxLayer.removeChild(tx); tx.destroy(); } }
    };
    requestAnimationFrame(tick);
  }

  // ---------------- 镜头：滚轮缩放 + 拖拽平移 ----------------
  function applyCam() {
    if (!town.inst) return;
    town.inst.worldLayer.scale.set(cam.scale);
    town.inst.worldLayer.position.set(cam.x, cam.y);
    // T116：随缩放自动分层（近景 info / 全景 default）。带滞回，避免拖动边界抖动；
    // 用户显式选择「景观」时不自动覆盖。
    if (state.view !== "landscape" && !state.explicitView && !cam._focusLock && typeof town.inst.setMode === "function") {
      const tier = cam.scale >= 1.45 ? "info" : (cam.scale <= 1.15 ? "default" : state.view);
      if (tier !== state.view) setView(tier);
    }
  }

  // T259 修观感：把首屏镜头拉近并居中到"当前活动最密处"（全体角色质心），
  // 让开场读成一个"地方"而非一张"地图"。只在未显式定位时调用；可回退（?cam=fit）。
  function focusCamera(scale) {
    if (!town.inst) return;
    const ids = Object.keys(town.inst.agents || {});
    let sx = 0, sy = 0, n = 0;
    ids.forEach((id) => {
      const rec = town.inst.agents[id];
      const t = rec && (rec.target || rec.container);
      if (t && isFinite(t.x) && isFinite(t.y)) { sx += t.x; sy += t.y; n++; }
    });
    const v = town.inst.app.view;
    cam.scale = Math.max(1, Math.min(4, scale));
    const cx = n ? sx / n : v.width / 2;
    const cy = n ? sy / n : v.height / 2;
    cam.x = v.width / 2 - cx * cam.scale;
    cam.y = v.height / 2 - cy * cam.scale;
    cam._focusLock = true;   // 首屏聚焦时抑制"近景自动切 info(显 NPC ID)"的档位跳变，保持建筑名分层
    clampCam(); applyCam();
    cam._focusLock = false;
  }

  // T116 信息分层：landscape | default | info（默认 default：建筑名可见、NPC ID 隐藏）
  function setView(mode) {
    state.view = (mode === "landscape" || mode === "info") ? mode : "default";
    if (town.inst && typeof town.inst.setMode === "function") town.inst.setMode(state.view);
    const b = el("btn-view");
    if (b) {
      b.textContent = state.view === "landscape" ? "🏞 景观：开" : "🏞 景观";
      b.classList.toggle("active", state.view === "landscape");
    }
  }
  function clampCam() {
    cam.scale = Math.max(0.5, Math.min(4, cam.scale));
    // 世界尺寸以前端渲染为准（T71：Town 用 LAYOUT.WORLD，非 topology.world）
    const W = (town.inst && town.inst.app.view.width) || state.topology.world.width;
    const H = (town.inst && town.inst.app.view.height) || state.topology.world.height;
    const minX = W - W * cam.scale, minY = H - H * cam.scale;
    cam.x = Math.min(0, Math.max(minX, cam.x));
    cam.y = Math.min(0, Math.max(minY, cam.y));
  }
  function canvasPoint(e) {
    const view = town.inst.app.view;
    const r = view.getBoundingClientRect();
    return { x: (e.clientX - r.left) * (view.width / r.width), y: (e.clientY - r.top) * (view.height / r.height) };
  }
  function zoomAt(px, py, factor) {
    state.explicitView = false;   // 任意缩放（滚轮/按钮）→ 交回自动分层
    const before = { x: (px - cam.x) / cam.scale, y: (py - cam.y) / cam.scale };
    cam.scale *= factor; clampCam();
    cam.x = px - before.x * cam.scale;
    cam.y = py - before.y * cam.scale;
    clampCam(); applyCam();
  }
  function wireCamera() {
    const wrap = el("stage-wrap");
    wrap.addEventListener("wheel", (e) => {
      if (!town.inst) return;
      e.preventDefault();
      state.explicitView = false;   // 用户手动缩放 → 退出 URL 显式分层，交回自动分层
      const p = canvasPoint(e);
      zoomAt(p.x, p.y, e.deltaY < 0 ? 1.15 : 1 / 1.15);
    }, { passive: false });

    let dragging = false, moved = false, last = null;
    wrap.addEventListener("pointerdown", (e) => {
      if (e.target.closest("#controls, .drawer, .zoom-ctl, #topbar")) return;
      state.explicitView = false;
      dragging = true; moved = false; last = { x: e.clientX, y: e.clientY };
      wrap.setPointerCapture && wrap.setPointerCapture(e.pointerId);
    });
    wrap.addEventListener("pointermove", (e) => {
      if (!dragging || !town.inst) return;
      const dx = e.clientX - last.x, dy = e.clientY - last.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
      const view = town.inst.app.view, r = view.getBoundingClientRect();
      cam.x += dx * (view.width / r.width);
      cam.y += dy * (view.height / r.height);
      last = { x: e.clientX, y: e.clientY };
      clampCam(); applyCam();
    });
    wrap.addEventListener("pointerup", (e) => {
      if (!dragging) return; dragging = false;
      if (!moved) handleClick(e);
    });
    wrap.addEventListener("pointercancel", () => { dragging = false; });

    el("btn-zoom-in").onclick = () => { const v = town.inst.app.view; zoomAt(v.width / 2, v.height / 2, 1.2); };
    el("btn-zoom-out").onclick = () => { const v = town.inst.app.view; zoomAt(v.width / 2, v.height / 2, 1 / 1.2); };
    el("btn-zoom-reset").onclick = () => { cam.scale = 1; cam.x = 0; cam.y = 0; applyCam(); };
  }

  // ---------------- 点击交互（角色 / 场所） ----------------
  function handleClick(e) {
    if (!town.inst || !state.replay) return;
    const p = canvasPoint(e);
    const wx = (p.x - cam.x) / cam.scale, wy = (p.y - cam.y) / cam.scale;
    // 先找角色（近者优先）
    const recs = Object.keys(town.inst.agents);
    let best = null, bestD = 26 * 26;
    recs.forEach((id) => {
      const c = town.inst.agents[id].container;
      const d = (c.x - wx) ** 2 + (c.y - 20 - wy) ** 2;
      if (d < bestD) { bestD = d; best = id; }
    });
    if (best) { selectAgent(best); return; }
    // 再找场所
    let place = null, pd = 46 * 46;
    Object.values(town.inst.nodeById).forEach((n) => {
      const d = (n.x - wx) ** 2 + (n.y - wy) ** 2;
      if (d < pd) { pd = d; place = n.place_id; }
    });
    if (place) selectPlace(place);
  }

  function openDrawer(id) {
    // 角色卡与观测台同处右抽屉位置 → 互斥切换，避免小屏重叠
    const other = id === "audit" ? "inspector" : "audit";
    const oe = el(other); if (oe) oe.classList.remove("open");
    el(id).classList.add("open");
  }
  function closeDrawer(id) { el(id).classList.remove("open"); }
  function closeInspector() { state.sel = null; closeDrawer("inspector"); }

  function selectAgent(id) { state.sel = { kind: "agent", id }; refreshInspector(); openDrawer("inspector"); }
  function selectPlace(pid) { state.sel = { kind: "place", id: pid }; refreshInspector(); openDrawer("inspector"); }

  function refreshInspector() {
    if (!state.sel || !state.replay) return;
    if (state.sel.kind === "agent") renderAgentInspector(state.sel.id);
    else renderPlaceInspector(state.sel.id);
  }

  function agentColor(id) {
    const idx = Object.keys(town.inst.agents).indexOf(id);
    return "#" + [0x5cc8ff, 0xffcf5c, 0x5ddc82, 0xff8f6b, 0xc08bff, 0x66e0c0, 0xff7fb0, 0x9ad0ff]
      .concat()[((idx < 0 ? 0 : idx)) % 8].toString(16).padStart(6, "0");
  }

  // G-14：角色卡内迷你关系图（只读；节点=有关系的他人，边粗=好感强度，绿正/红负；点节点切换角色卡）
  function relGraphSVG(selfId, rels, nameOf, colorOf) {
    const ids = Object.keys(rels || {});
    const title = `<h4>关系图 ${help("边越粗=好感/信任越高；绿=正面、红=负面。点节点切换角色卡。")}</h4>`;
    if (!ids.length) return `<div class="insp-sec">${title}<div class='muted'>暂无关系边</div></div>`;
    const W = 240, H = 240, cx = 120, cy = 120, R = 92, n = ids.length;
    const edges = [], nodes = [];
    ids.forEach((to, i) => {
      const a = Math.PI * 2 * i / n - Math.PI / 2;
      const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a);
      const aff = (rels[to].affinity != null) ? rels[to].affinity : ((rels[to].trust != null) ? rels[to].trust : 0);
      const w = (1 + Math.min(5, Math.abs(aff) / 12)).toFixed(1);
      const col = aff >= 0 ? "#5ddc82" : "#e4572e";
      edges.push(`<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${col}" stroke-width="${w}" opacity="0.7"/>`);
      nodes.push(`<g class="rg-node" data-agent="${escapeHtml(to)}" style="cursor:pointer"><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="12" fill="${colorOf(to)}" stroke="#0b0e12" stroke-width="2"/><text x="${x.toFixed(1)}" y="${(y + 24).toFixed(1)}" text-anchor="middle" font-size="9" fill="#e6ebf2">${escapeHtml(String(nameOf(to)).slice(-4))}</text></g>`);
    });
    nodes.push(`<circle cx="${cx}" cy="${cy}" r="14" fill="${colorOf(selfId)}" stroke="#ffffff" stroke-width="2"/><text x="${cx}" y="${cy + 28}" text-anchor="middle" font-size="9" fill="#e6ebf2">我</text>`);
    return `<div class="insp-sec">${title}<svg class="relgraph" viewBox="0 0 ${W} ${H}" width="100%" height="230">${edges.join("")}${nodes.join("")}</svg></div>`;
  }

  function gatherAgent(rp, id, rd) {
    const persona = state.personas[id] || null;
    let cash = 0, debt = 0, deposits = 0;
    let status = "alive";
    const rels = {}, msgs = [], behaviors = [], goals = [], timeline = [], loans = [];
    const push = (a, v, cap) => { a.push(v); if (a.length > (cap || 14)) a.shift(); };
    for (const e of rp.records) {
      if ((e.round || 0) > rd) continue;
      const p = e.payload || {}, t = e.type;
      switch (t) {
        case "INIT_ENDOW": if (p.agent_id === id) cash += p.amount || 0; break;
        case "TRANSFER": if (p.from === id) cash -= p.amount || 0; if (p.to === id) cash += p.amount || 0; break;
        case "MARKET_TRADE": if (p.buyer === id) cash -= p.amount || 0; if (p.seller === id) cash += p.amount || 0; break;
        case "TAX_LEVIED": case "METABOLISM": case "PENALTY_APPLIED": case "REVIVE_FEE_PAID":
          if (p.agent_id === id) cash -= p.amount || 0; break;
        case "UBI_PAID": case "INTEREST_PAID": if (p.agent_id === id) cash += p.amount || 0; break;
        case "INTEREST_CHARGED": if (p.borrower === id) cash -= p.amount || 0; break;
        case "LOAN_ISSUED":
          if (p.borrower === id) { cash += p.principal || 0; debt += p.outstanding || p.principal || 0; loans.push({ amount: p.principal, due: p.due_round }); }
          break;
        case "LOAN_REPAY": if (p.borrower === id) { cash -= p.amount || 0; debt = Math.max(0, debt - (p.amount || 0)); } break;
        case "LOAN_DEFAULT": if (p.borrower === id) debt = Math.max(debt, p.outstanding || 0); break;
        case "DEPOSIT": if (p.agent_id === id) { cash -= p.amount || 0; deposits += p.amount || 0; } break;
        case "WITHDRAW": if (p.agent_id === id) { cash += p.amount || 0; deposits = Math.max(0, deposits - (p.amount || 0)); } break;
        default: break;
      }
      if (t === "AGENT_DIED" && p.agent_id === id) { status = "dead"; push(timeline, { round: e.round, seq: e.seq, text: `去世了（${R.reasonCn(p.cause)}，流动性 ${p.liquid} mu）`, inferred: /illiquid_no_credit/.test(p.cause || "") }); }
      if (t === "AGENT_REVIVED" && p.agent_id === id) { status = "alive"; push(timeline, { round: e.round, seq: e.seq, text: `复活了（${R.reasonCn(p.via)}，代价 ${p.cost} mu）` }); }
      if (t === "STATE_CHANGE" && p.agent_id === id) {
        const to = p.to || "";
        if (p.to === "dead" || p.to === "terminated") status = "dead";
        else if (p.to === "alive" || p.to === "revived") status = "alive";
        else if (to) status = to;
        if (["warning", "near_death", "dead"].includes(to)) push(timeline, { round: e.round, seq: e.seq, text: `状态 ${p.from}→${p.to}（${R.reasonCn(p.reason || p.cause)}）`, inferred: /low_liquidity|illiquid/.test(p.reason || p.cause || "") });
      }
      if (t === "RELATION_CHANGE" && p.from === id) { const k = p.to || "?"; rels[k] = rels[k] || {}; rels[k][p.dim] = p.after; }
      if ((t === "MSG_PUBLIC" || t === "MSG_DM" || t === "MSG_GROUP") && p.from === id) push(msgs, { round: e.round, to: p.to || "", body: p.body || p.text || "" });
      if (t === "PLACE_MOVE" && p.agent_id === id) push(behaviors, { round: e.round, text: `前往「${placeNameOf(p.to_place)}」` });
      if (t === "ACTIVITY_STARTED" && p.agent_id === id) push(behaviors, { round: e.round, text: `在「${placeNameOf(p.place)}」${R.activityLabel(p.activity_type)}` });
      if (t === "GOAL_SET" && p.agent_id === id) push(goals, { round: e.round, text: `${p.description_ref || p.kind}（${p.kind}/${p.layer}）` });
      if (t === "GOAL_ACHIEVED" && p.agent_id === id) push(goals, { round: e.round, text: `达成 ${p.goal_id}` });
    }
    return { persona, cash, debt, deposits, status, rels, msgs, behaviors, goals, timeline };
  }

  // ---- 面向用户的中文化字典（中文为主，括号内保留英文键对照）----
  const BIG5_CN = { openness: ["开放性", "openness"], conscientiousness: ["尽责性", "conscientiousness"],
    extraversion: ["外向性", "extraversion"], agreeableness: ["宜人性", "agreeableness"], neuroticism: ["情绪稳定性", "neuroticism"] };
  const VALUES_CN = { self_direction: ["自主", "self_direction"], benevolence: ["仁爱", "benevolence"],
    achievement: ["成就", "achievement"], security: ["安全", "security"], universalism: ["博爱", "universalism"], power: ["影响力", "power"] };
  const GOAL_CN = { security: "生存安全", wealth: "财富", mastery: "精进", achievement: "成就", social: "社交", meaning: "意义", status: "地位" };
  const GOAL_LAYER = { survival: "生存", growth: "成长", social: "社交", meaning: "意义" };
  const SPEECH_TONE = { plain: "平实", warm: "温和", calm: "沉静", playful: "俏皮", blunt: "直率", casual: "随性", expressive: "外放", formal: "正式" };
  const SPEECH_LEN = { short: "简短", medium: "适中", long: "健谈" };
  const NEED_CN = { energy: "精力", satiety: "饱食", social: "社交", esteem: "自尊", mastery: "成就", leisure: "闲暇" };
  // 关系维度（来源：glossary-ui-terms.md）：affinity/trust −100~100；respect/familiarity 0~100
  const REL_CN = { affinity: ["好感", -100, 100], trust: ["信任", -100, 100], respect: ["尊重", 0, 100], familiarity: ["熟悉度", 0, 100] };
  const ROLE_CN = { farmer: "农民", craftsman: "工匠", cook: "厨师", merchant: "商人", healer: "医护",
    teacher: "教师", public_servant: "公职人员", banker: "银行职员", artist: "艺术家", student: "学生", unemployed: "待业" };
  const SKILL_CN = { farming: "务农", cooking: "烹饪", bargaining: "议价", study: "学习", crafting: "手工",
    healing: "医护", teaching: "教学", banking: "金融", trading: "经商", artistry: "才艺" };
  function needCnK(k) { return NEED_CN[k] || k; }
  function roleCn(r) { return ROLE_CN[r] || r || "居民"; }
  function skillCn(s) { return SKILL_CN[s] || s; }
  // 数值档位（0–100，基于 glossary：低≤33 / 中34–66 / 高≥67；此处细分到形容词）
  function tier(v) {
    v = Number(v);
    if (Number.isNaN(v)) return "";
    if (v >= 80) return "很高"; if (v >= 67) return "较高"; if (v >= 34) return "中等";
    if (v >= 20) return "偏低"; return "很低";
  }
  // 有向关系：正=好、负=差
  function relTier(v, lo) {
    v = Number(v);
    if (lo < 0) { if (v >= 50) return "很好"; if (v >= 20) return "偏好"; if (v > -20) return "中性"; if (v > -50) return "偏差"; return "很差"; }
    return tier(v);
  }
  function help(tip) { return `<span class="help" title="${escapeHtml(tip)}">?</span>`; }
  // 带中文 + 数值 + 档位 + 英文对照的 chip
  function statChip(cn, en, val, tip) {
    return `<span class="chip" title="${escapeHtml(tip || (cn + "：" + val + "/100，" + tier(val)))}">` +
      `${cn} <b>${val}</b><span class="muted">（${tier(val)}）</span>` +
      (en ? ` <span class="muted">${escapeHtml(en)}</span>` : "") + `</span>`;
  }

  function renderAgentInspector(id) {
    const rp = state.replay, rd = state.round;
    const d = gatherAgent(rp, id, rd);
    const snap = (rp.snapshots[rd] || {})[id] || {};
    const persona = d.persona;
    const nm = persona ? persona.display_name : id;
    const label = { alive: "存活", dead: "已死亡", warning: "濒危", near_death: "濒危", terminated: "已终止" }[d.status] || d.status;
    const badgeColor = d.status === "dead" || d.status === "terminated" ? "#D9534F"
      : (d.status === "near_death" || d.status === "warning") ? "#E4572E" : "#6FCF6B";
    const needs = snap.needs || {};
    const needBars = Object.keys(needs).length ? Object.keys(needs).map((k) =>
      `<div class="bar"><span class="lbl" title="${escapeHtml(needCnK(k) + " " + k)}">${escapeHtml(needCnK(k))}</span>` +
      `<span class="track"><span class="fill" style="width:${Math.max(0, Math.min(100, needs[k]))}%"></span></span>` +
      `<span>${Math.round(needs[k])}<span class="muted">（${tier(needs[k])}）</span></span></div>`
    ).join("") : "<div class='muted'>（无需求快照）</div>";
    const relRows = Object.keys(d.rels).map((to) =>
      `<div class="rel"><a class="relname" data-agent="${escapeHtml(to)}">${escapeHtml(nameOf(to))}</a>` +
      Object.keys(d.rels[to]).map((k) => {
        const cn = REL_CN[k];
        const name = cn ? cn[0] : k, lo = cn ? cn[1] : 0, hi = cn ? cn[2] : 100;
        const tip = cn ? `${name}：${lo}~${hi}，${lo < 0 ? "正=好、负=差" : "越高越强"}` : k;
        return `<span class="chip" title="${escapeHtml(tip)}">${name} ${d.rels[to][k]}${cn ? `<span class="muted">（${relTier(d.rels[to][k], lo)}）</span>` : ""}</span>`;
      }).join("") + `</div>`
    ).join("") || "<div class='muted'>暂无关系记录</div>";
    const msgRows = d.msgs.slice(-6).reverse().map((m) => `<div class="quote">「${escapeHtml(m.body)}」<span class="muted">· r${m.round}${m.to ? " → " + escapeHtml(nameOf(m.to)) : ""}</span></div>`).join("") || "<div class='muted'>暂无发言</div>";
    const behavRows = d.behaviors.slice(-8).reverse().map((b) => `<div class="kv"><span class="k">r${b.round}</span><span>${escapeHtml(b.text)}</span></div>`).join("") || "<div class='muted'>暂无行为记录</div>";
    const tlRows = d.timeline.slice(-8).map((t) => `<div class="tl ${t.inferred ? "infer" : "fact"}"><span class="muted">r${t.round || "?"}</span> ${t.inferred ? "推测：" : ""}${escapeHtml(t.text)}${t.seq != null ? ` <a class="wl" data-seq="${t.seq}">#${t.seq}</a>` : ""}</div>`).join("") || "<div class='muted'>暂无关键节点</div>";
    const goalRows = d.goals.slice(-4).reverse().map((g) => `<div class="kv"><span class="k">r${g.round}</span><span>${escapeHtml(g.text)}</span></div>`).join("") || "<div class='muted'>暂无</div>";
    const p = persona || {};
    const big5 = p.personality_big5 ? Object.keys(p.personality_big5).map((k) => {
      const cn = BIG5_CN[k] || [k, k];
      if (k === "neuroticism") {
        // 方向：展示「情绪稳定性 = 100 − neuroticism」，越高越稳（避免与原始分方向混用）
        const stab = Math.max(0, Math.min(100, 100 - Number(p.personality_big5[k])));
        return `<span class="chip" title="情绪稳定性 = 100 − 神经质原始分(${p.personality_big5[k]})；越高情绪越稳定（0–100）">` +
          `情绪稳定性 <b>${stab}</b><span class="muted">（${tier(stab)}，越高越稳）</span> <span class="muted">neuroticism</span></span>`;
      }
      return statChip(cn[0], cn[1], p.personality_big5[k], cn[0] + "：0–100，越高越明显");
    }).join("") : "";
    const values = p.values ? Object.keys(p.values).map((k) => {
      const cn = VALUES_CN[k] || [k, k];
      return statChip(cn[0], cn[1], p.values[k], "价值取向：" + cn[0] + " 0–100");
    }).join("") : "";
    const skills = (p.skills || []).map((s) => `<span class="chip" title="${escapeHtml(skillCn(s.skill_id) + " " + s.skill_id)}">${escapeHtml(skillCn(s.skill_id))} L${s.level}<span class="muted"> ${escapeHtml(s.skill_id)}</span></span>`).join("");
    const wtier = (w) => (w > 0.7 ? "强" : w >= 0.4 ? "中" : "弱");
    const gt = (p.goal_tendencies || []).map((g) => {
      const nm = GOAL_CN[g.kind] || g.kind;
      const w = g.weight || 0;
      return `<span class="chip" title="目标倾向：${escapeHtml(nm)}（${escapeHtml(g.kind)}）权重 ${w}（弱<0.4 / 中0.4–0.7 / 强>0.7）">` +
        `${escapeHtml(nm)}<span class="muted">（${wtier(w)} ${Math.round(w * 100)}%）</span>${g.layer ? `<span class="muted"> ${escapeHtml(GOAL_LAYER[g.layer] || g.layer)}</span>` : ""}</span>`;
    }).join("");
    const ss = p.speech_style || {};
    const speech = (ss.tone || ss.verbosity) ? `<span class="chip">说话风格：${escapeHtml(SPEECH_TONE[ss.tone] || ss.tone || "—")}${ss.verbosity ? " · " + escapeHtml(SPEECH_LEN[ss.verbosity] || ss.verbosity) : ""}<span class="muted"> ${escapeHtml([ss.tone, ss.verbosity].filter(Boolean).join("/"))}</span></span>` : "";
    const net = d.cash + d.deposits - d.debt;

    el("insp-title").textContent = "角色卡";
    el("insp-body").innerHTML = `
      <div class="cc-head">
        <div class="cc-avatar" style="background:${agentColor(id)}">${escapeHtml(nm.slice(-1))}</div>
        <div class="cc-id">
          <div class="nm">${escapeHtml(nm)}</div>
          <div class="sub">${p.age ? p.age + " 岁 · " : ""}${escapeHtml(roleCn(p.role_id))}${p.role_id ? ` <span class="muted">${escapeHtml(p.role_id)}</span>` : ""} · 家「${escapeHtml(placeNameOf(p.home_place || "residence"))}」</div>
          <div><span class="badge-status" style="background:${badgeColor}">${label}</span>
            <span class="muted">位于「${escapeHtml(placeNameOf(snap.location || "residence"))}」· ${snap.activity ? escapeHtml(R.activityLabel(snap.activity.type, snap.activity.place)) : "—"}</span></div>
        </div>
      </div>
      <div class="insp-sec"><h4>金钱 / 负债 ${help("现金=手上可用；存款=存在银行；负债=未还贷款；净值=现金+存款−负债。单位 mu。")}</h4>
        <div class="kv"><span class="k">现金</span><span>${Math.round(d.cash)} mu</span></div>
        <div class="kv"><span class="k">存款</span><span>${Math.round(d.deposits)} mu</span></div>
        <div class="kv"><span class="k">负债</span><span>${Math.round(d.debt)} mu</span></div>
        <div class="kv"><span class="k">净值</span><span>${Math.round(net)} mu</span></div>
      </div>
      <div class="insp-sec"><h4>需求 ${help("六项需求 0–100，越低越紧迫；由睡眠/进食/社交/活动等变化。")}</h4>${needBars}</div>
      <div class="insp-sec"><h4>关系（可点切换）${help("对他人四个维度：好感/信任/敬重/熟悉度，均 0–100，越高越强。")}</h4>${relRows}</div>
      ${relGraphSVG(id, d.rels, nameOf, agentColor)}
      <div class="insp-sec"><h4>人格背景 ${help("他的性格底色：五大人格与价值取向均为 0–100，越高代表该特质越明显；括号内为英文键对照。")}</h4>
        <div class="cc-bg">${escapeHtml(p.background || "—")}</div>
        <div class="sec-sub">五大人格 ${help("开放性=乐于尝试新事物；尽责性=自律有条理；外向性=爱社交；宜人性=体贴他人；情绪稳定性=情绪是否平稳（neuroticism 原始分越高=越易波动）。")}</div>
        <div class="chips">${big5}</div>
        <div class="sec-sub">价值取向 ${help("他看重的方向：自主=独立自主；仁善=关心他人；成就=追求成绩；安稳=重视安全稳定。")}</div>
        <div class="chips">${values}</div>
        <div class="sec-sub">技能 · 目标倾向 · 说话风格 ${help("技能等级 L1–L5；目标倾向=他更可能追求的方向与权重；说话风格影响对话语气与篇幅。")}</div>
        <div class="chips">${skills}${gt}${speech}</div>
      </div>
      <div class="insp-sec"><h4>目标</h4>${goalRows}</div>
      <div class="insp-sec"><h4>最近行为</h4>${behavRows}</div>
      <div class="insp-sec"><h4>发表的（MSG 原文）</h4>${msgRows}</div>
      <div class="insp-sec"><h4>因果时间线（事实/推测）</h4>${tlRows}</div>`;
    // 关系人名可点切换；因果 seq 可跳
    el("insp-body").querySelectorAll(".relname").forEach((a) => { a.onclick = () => selectAgent(a.dataset.agent); });
    el("insp-body").querySelectorAll(".rg-node").forEach((g) => { g.onclick = () => selectAgent(g.dataset.agent); });
    el("insp-body").querySelectorAll(".wl").forEach((a) => {
      a.onclick = () => { const s = Number(a.dataset.seq); const r = state.seqRound && state.seqRound[s]; if (r != null) { stopPlay(); pauseFollow(); jumpTo(r); } };
    });
  }
  function renderPlaceInspector(pid) {
    const rp = state.replay, rd = state.round;
    const place = state.places.find((p) => p.place_id === pid) || { place_id: pid, name_cn: pid, category: "?" };
    // 坐标/环层优先取渲染模块的 nodeById（art-director 的新布局），回退到 topology
    const node = (town.inst.nodeById && town.inst.nodeById[pid]) ||
      (state.topology.nodes || []).find((n) => n.place_id === pid) || {};
    const disp = rp.displayState(rd).agents;
    const occ = Object.keys(disp).filter((id) => (disp[id].location || "residence") === pid).sort();
    const occRows = occ.map((id) => {
      const a = disp[id];
      const act = a.bubble ? escapeHtml(a.bubble) : (a.activity ? escapeHtml(R.activityLabel(a.activity.type, a.activity.place)) : "—");
      return `<div class="occ-row" data-agent="${escapeHtml(id)}"><span class="dot" style="background:${agentColor(id)}"></span><span class="nm">${escapeHtml(id)}</span><span class="muted">${act}</span></div>`;
    }).join("") || "<div class='muted'>当前无人</div>";
    el("insp-title").textContent = "场所详情";
    el("insp-body").innerHTML = `
      <div class="insp-hero">
        <span class="dot" style="background:#7b8794"></span>
        <div><div class="nm">${escapeHtml(place.name_cn || pid)}</div><div class="sub">${escapeHtml(place.category || "")} · 容量 ${place.capacity ?? "?"} · 环层 ${node.ring ?? "?"}</div></div>
      </div>
      ${travelSection("plaza", pid, "中央广场", place.name_cn || pid)}
      <div class="insp-sec"><h4>场内人员（${occ.length}）</h4>${occRows}</div>`;
    el("insp-body").querySelectorAll(".occ-row").forEach((row) => {
      row.onclick = () => selectAgent(row.dataset.agent);
    });
  }

  // 语义通行成本（只读引用 config/topology.json 的 travel_ticks；引擎冻结不改）
  function travelSection(fromId, toId, fromName, toName) {
    const tt = state.topology && state.topology.travel_ticks;
    if (!tt || !tt[fromId] || tt[fromId][toId] == null) return "";
    const n = tt[fromId][toId];
    const note = (fromId === toId)
      ? "（参照点本身）"
      : "展示距离≠通行成本：cost 由拓扑 travel_ticks 决定（引擎冻结），故会出现「看着近、语义成本高」的点（如 城门↔广场=3）。";
    return `<div class="insp-sec"><h4>语义通行成本</h4>
      <div class="kv"><span class="k">从${escapeHtml(fromName)}到${escapeHtml(toName)}</span><span>${n} tick</span></div>
      <div class="muted" style="font-size:11px;margin-top:4px">${note}</div></div>`;
  }
  // ---- 事件表现：最近事件走马条（"世界在运转"要看得见，但不喧宾夺主）----
  // 取最近 SPAN 轮、每轮最高优先 notable 事件各 1 条，末 N 条紧凑显示；**随 (log, round) 确定性派生**。
  function renderEvticker(rp, rd) {
    const box = el("evticker");
    if (!box) return;
    const SPAN = 5, N = 4;
    const ctx = (audit && audit.ctx) || { name: nameOf, place: placeNameOf };
    const picked = [];
    for (let r = Math.max(0, rd - SPAN); r <= rd; r++) {
      const evs = rp.eventsInRound(r).filter((e) => KEY_EVENTS[e.type]);
      if (!evs.length) continue;
      evs.sort((a, b) => KEY_EVENTS[b.type].pri - KEY_EVENTS[a.type].pri);
      picked.push(evs[0]);            // 每轮 1 条 → 连续感
    }
    const last = picked.slice(-N);
    box.innerHTML = last.map((e, i) => {
      const ic = KEY_EVENTS[e.type].icon;
      const t = R.humanize(e, ctx).text;
      const cls = i === last.length - 1 ? "row show" : "row show old";
      return `<div class="${cls}"><span class="ic">${ic}</span>${escapeHtml(t)}</div>`;
    }).join("");
  }

  function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

  // ---------------- 播放控制 ----------------
  function jumpTo(rd) {
    const rp = state.replay; if (!rp) return;
    rd = Math.max(rp.rounds[0] || 0, Math.min(rp.maxRound, rd));
    state.round = rd; renderRound(true);
  }
  function step(d) {
    const rp = state.replay; if (!rp) return;
    const idx = rp.rounds.indexOf(state.round);
    const ni = Math.max(0, Math.min(rp.rounds.length - 1, idx + d));
    jumpTo(rp.rounds[ni]);
  }
  function play() {
    if (!state.replay) return;
    if (state.round >= state.replay.maxRound) jumpTo(state.replay.rounds[0] || 0);
    state.playing = true; el("btn-play").textContent = "⏸ 暂停"; scheduleTick();
  }
  function stopPlay() {
    state.playing = false; el("btn-play").textContent = "▶ 播放";
    if (state.timer) { clearTimeout(state.timer); state.timer = null; }
  }
  function scheduleTick() {
    const speed = parseInt(el("speed-select").value, 10) || 800;
    state.timer = setTimeout(() => {
      if (!state.playing) return;
      if (state.round >= state.replay.maxRound) { stopPlay(); return; }
      step(1); scheduleTick();
    }, speed);
  }

  function switchAuditTab(tab) {
    state.auditTab = (tab === "social" || tab === "weekly" || tab === "econ") ? tab : "chronicle";
    document.querySelectorAll("#audit .tab").forEach((x) => x.classList.toggle("active", x.dataset.tab === state.auditTab));
    const c = el("pane-chronicle"), s = el("pane-social"), w = el("pane-weekly"), e = el("pane-econ");
    if (c) c.hidden = state.auditTab !== "chronicle";
    if (s) s.hidden = state.auditTab !== "social";
    if (w) w.hidden = state.auditTab !== "weekly";
    if (e) e.hidden = state.auditTab !== "econ";
    if (state.replay && audit) {
      if (state.auditTab === "social" && audit.renderSocial) audit.renderSocial(state.replay, state.round);
      else if (state.auditTab === "weekly" && audit.renderWeekly) audit.renderWeekly(state.replay, state.round);
      else if (state.auditTab === "econ" && audit.renderEcon) audit.renderEcon(state.replay, state.round);
    }
  }

  function wireControls() {
    el("btn-first").onclick = () => { stopPlay(); pauseFollow(); jumpTo(state.replay.rounds[0] || 0); };
    el("btn-last").onclick = () => { stopPlay(); jumpTo(state.replay.maxRound); };
    el("btn-prev").onclick = () => { stopPlay(); pauseFollow(); step(-1); };
    el("btn-next").onclick = () => { stopPlay(); pauseFollow(); step(1); };
    el("btn-play").onclick = () => { state.playing ? stopPlay() : play(); };
    el("round-slider").oninput = (e) => { stopPlay(); pauseFollow(); jumpTo(parseInt(e.target.value, 10)); };
    el("speed-select").onchange = () => { if (state.playing) { if (state.timer) clearTimeout(state.timer); scheduleTick(); } };

    el("btn-toggle-audit").onclick = () => el("audit").classList.toggle("open");
    { const bd = el("btn-debug"); if (bd) bd.onclick = () => document.body.classList.toggle("show-debug"); }
    { const bv = el("btn-view"); if (bv) bv.onclick = () => { state.explicitView = false; setView(state.view === "landscape" ? "default" : "landscape"); }; }
    // 观测台分页：编年史 / 社交
    document.querySelectorAll("#audit .tab").forEach((b) => {
      b.onclick = () => switchAuditTab(b.dataset.tab);
    });
    // 事件流筛选/搜索/审计模式
    if (el("ev-level")) el("ev-level").onchange = (e) => { audit.opts.level = e.target.value; rerenderStream(); };
    if (el("ev-search")) el("ev-search").oninput = (e) => { audit.opts.q = e.target.value; rerenderStream(); };
    if (el("ev-audit")) el("ev-audit").onchange = (e) => { audit.opts.auditMode = e.target.checked; rerenderStream(); };
    document.querySelectorAll(".drawer-close").forEach((b) => { b.onclick = () => closeDrawer(b.dataset.close); });

    // 设置浮层（载入日志 / 样例 / 数据源），默认隐藏
    const pop = el("settings-pop");
    el("btn-settings").onclick = (e) => { e.stopPropagation(); pop.hidden = !pop.hidden; };
    pop.onclick = (e) => e.stopPropagation();
    document.addEventListener("click", () => { if (!pop.hidden) pop.hidden = true; });

    el("sample-select").onchange = async (e) => {
      const v = e.target.value; if (!v) return; stopPlay();
      try { await loadLogFromURL(v); } catch (err) { showError(err.message); }
    };
    el("file-input").onchange = async (e) => {
      const f = e.target.files && e.target.files[0]; if (!f) return; stopPlay();
      try { applyLogText(await f.text(), f.name); } catch (err) { showError(err.message); }
    };
    document.addEventListener("dragover", (e) => e.preventDefault());
    document.addEventListener("drop", async (e) => {
      e.preventDefault();
      const f = e.dataTransfer.files && e.dataTransfer.files[0]; if (!f) return; stopPlay();
      try { applyLogText(await f.text(), f.name); } catch (err) { showError(err.message); }
    });
    document.addEventListener("keydown", (e) => {
      if (e.target && /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
      if (e.code === "Space") { e.preventDefault(); state.playing ? stopPlay() : play(); }
      else if (e.code === "ArrowRight") { stopPlay(); step(1); }
      else if (e.code === "ArrowLeft") { stopPlay(); step(-1); }
      else if (e.code === "Escape") { closeDrawer("inspector"); closeDrawer("audit"); }
    });

    // 后台标签页 / 暂停时停 rAF，降低闲置 CPU（播放与截图观感不变）
    document.addEventListener("visibilitychange", () => {
      if (!town.inst) return;
      if (document.hidden) {
        stopPlay();
        try { town.inst.app.ticker.stop(); } catch (e) { /* noop */ }
      } else if (!state.still) {
        try { town.inst.app.ticker.start(); } catch (e) { /* noop */ }
      }
    });
  }

  window.addEventListener("DOMContentLoaded", boot);
})();
