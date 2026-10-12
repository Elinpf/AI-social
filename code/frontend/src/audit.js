/* audit.js — 观测台（T77 重做）：K 类事实 + 「小镇编年史」人话事件流 + 因果 + 审计模式。
 * 只读：所有文案/数字均由日志+人格+族色常量重算；原始事件仍可展开查看（审计不丢）。
 */
(function (global) {
  "use strict";

  const R = global.HITTReplay;

  class Audit {
    constructor(kfactsEl, streamEl, countEl) {
      this.kfactsEl = kfactsEl;
      this.streamEl = streamEl;
      this.countEl = countEl;
      this.ctx = { name: (x) => x, place: (x) => x || "" };   // 由 main 注入（personas/places）
      this.onOpenAgent = null;      // (id)=>void  点名字→角色卡
      this.onJumpRound = null;      // (round)=>void 点因果→跳回合
      this.opts = { level: "narrative", q: "", auditMode: false, range: 0 };
      this._seqIndex = null;        // seq→round（由 main 注入，因果跳转用）
      this._eventsBySeq = null;     // seq→record（由 main 注入，剧情卡因果链用）
      this.weeklyWeek = null;       // 周报指定周（null=当前回合所在周）
      this._expandSeq = null;       // ?expand=<seq> 自动展开某行详情（证据用）
    }

    renderFacts(replay, rd) {
      const f = replay.facts[rd] || { total: 0, alive: 0, aliveRate: 0, moneySupply: 0, occupancy: {}, eventsThisRound: 0 };
      const occ = f.occupancy || {};
      let busiest = { loc: "—", n: 0 };
      Object.keys(occ).forEach((k) => { if (occ[k] > busiest.n) busiest = { loc: k, n: occ[k] }; });
      const cum = Object.values(replay.eventTypeCount).reduce((a, b) => a + b, 0);
      const cards = [
        ["存活 / 总数", `${f.alive} / ${f.total}`],
        ["存活率", (f.aliveRate * 100).toFixed(1) + "%"],
        ["货币总量 (mu)", formatMoney(f.moneySupply)],
        ["本回合事件", String(f.eventsThisRound)],
        ["最热场所", `${this.ctx.place(busiest.loc)} (${busiest.n})`],
        ["累计事件", String(cum)],
      ];
      this.kfactsEl.innerHTML = cards.map(([k, v]) =>
        `<div class="kfact"><div class="k">${escapeHtml(k)}</div><div class="v">${escapeHtml(v)}</div></div>`
      ).join("");
    }

    _levelOk(level) {
      const o = this.opts.level;
      if (o === "all") return true;
      if (o === "detail") return level === "narrative" || level === "detail";
      return level === "narrative";   // 默认：只显示叙事级
    }

    renderStream(replay, rd) {
      const o = this.opts;
      const lo = Math.max(replay.rounds[0] || 0, rd - (o.range || 0));
      const groups = [];
      let shown = 0, total = 0;
      const q = (o.q || "").trim().toLowerCase();
      for (let r = lo; r <= rd; r++) {
        const evs = replay.eventsInRound(r);
        const rows = [];
        for (const ev of evs) {
          total++;
          const h = R.humanize(ev, this.ctx);
          if (!this._levelOk(h.level)) continue;
          const text = h.text || "";
          if (q && !(text.toLowerCase().includes(q) || String(ev.type).toLowerCase().includes(q) || String(ev.seq).includes(q))) continue;
          rows.push(this._row(ev, h));
          shown++;
        }
        if (rows.length) groups.push(this._groupHead(r, replay) + rows.join(""));
      }
      this.streamEl.innerHTML = shown
        ? groups.join("")
        : `<div class="muted" style="padding:10px 2px">本回合无「${o.level === "narrative" ? "叙事级" : o.level}」事件${q ? "（搜索：" + escapeHtml(o.q) + "）" : ""}</div>`;
      this.streamEl.scrollTop = 0;
      if (this.countEl) this.countEl.textContent = `(${shown}/${total} 条${o.level === "narrative" ? "·叙事级" : ""})`;
      this._wire();
      // 因果跳转后：定位并高亮源事件行
      if (this._focusSeq != null) {
        const row = this.streamEl.querySelector(`.ev-card[data-seq="${this._focusSeq}"]`);
        if (row) {
          row.classList.add("focus");
          if (row.scrollIntoView) row.scrollIntoView({ block: "center" });
          setTimeout(() => row.classList.remove("focus"), 2200);
        }
        this._focusSeq = null;
      }
      // 证据/检索用：?expand=<seq> 自动展开某一行的详情（含剧情卡因果链）
      if (this._expandSeq != null) {
        const row = this.streamEl.querySelector(`.ev-card[data-seq="${this._expandSeq}"]`);
        if (row) { const d = row.querySelector(".ev-detail"); if (d) d.hidden = false; if (row.scrollIntoView) row.scrollIntoView({ block: "center" }); }
      }
    }

    _groupHead(r, replay) {
      const w = R.wallClock(r);
      return `<div class="ev-group"><span class="g-round">round ${r}</span><span class="g-time">第${w.day}日 ${w.hhmm} ${w.slotName}</span></div>`;
    }

    // ---------------- 社交 / 对话视图（T77）----------------
    renderSocial(replay, rd) {
      const doc = global.document;
      if (!doc) return;
      const body = doc.getElementById("social-body");
      if (!body) return;
      const nm = this.ctx.name, pl = this.ctx.place;
      const RELTYPES = { MSG_DM: 1, MSG_PUBLIC: 1, MSG_GROUP: 1, OFFER_CREATED: 1, OFFER_ACCEPTED: 1,
        OFFER_REJECTED: 1, OFFER_COUNTERED: 1, OFFER_EXPIRED: 1, RELATION_ENCOUNTER: 1, RELATION_CHANGE: 1,
        CONFLICT_STARTED: 1, NORM_PROPOSED: 1 };
      const evs = [], counts = {};
      for (let r = (replay.rounds[0] || 0); r <= rd; r++) {
        for (const e of replay.eventsInRound(r)) {
          if (RELTYPES[e.type]) { evs.push(e); counts[e.type] = (counts[e.type] || 0) + 1; }
        }
      }
      const dm = evs.filter((e) => e.type === "MSG_DM");
      const offers = evs.filter((e) => String(e.type).startsWith("OFFER_"));
      // 人物对聚合
      const pairs = {};
      const addPair = (a, b, inc) => {
        if (!a || !b) return;
        const s = [a, b].sort(); const k = s.join("|");
        pairs[k] = pairs[k] || { a: s[0], b: s[1], msg: 0, offer: 0 };
        pairs[k][inc]++;
      };
      dm.forEach((e) => addPair(e.payload.from, e.payload.to, "msg"));
      offers.forEach((e) => addPair(e.payload.from, e.payload.to, "offer"));
      const pairList = Object.values(pairs).sort((x, y) => (y.msg + y.offer) - (x.msg + x.offer));
      const sel = this.socialPair || null;
      const pairKeyOf = (e) => { const s = [e.payload.from, e.payload.to].sort(); return s.join("|"); };
      // 对话线程（私聊 + 协商），按 seq 排序
      const thread = evs.filter((e) => e.type === "MSG_DM" || String(e.type).startsWith("OFFER_"))
        .sort((a, b) => a.seq - b.seq).filter((e) => !sel || pairKeyOf(e) === sel);
      // 共处 / 关系变化聚合
      const enc = {}, rel = {};
      evs.forEach((e) => {
        const p = e.payload || {};
        if (e.type === "RELATION_ENCOUNTER") {
          const k = [p.a || p.from, p.b || p.to].sort().join("|") + "@" + (p.place || "");
          enc[k] = enc[k] || { a: p.a || p.from, b: p.b || p.to, place: p.place, n: 0 }; enc[k].n++;
        } else if (e.type === "RELATION_CHANGE") {
          const k = [p.from, p.to].sort().join("|") + "|" + p.dim;
          rel[k] = rel[k] || { from: p.from, to: p.to, dim: p.dim, delta: 0, n: 0, cause: p.cause };
          rel[k].n++; rel[k].delta += (Number(p.after) - Number(p.before)) || 0; rel[k].cause = p.cause || rel[k].cause;
        }
      });
      const groupUnimplemented = (counts.MSG_PUBLIC || 0) === 0 && (counts.MSG_GROUP || 0) === 0;
      // 对话是否像"模板措辞"（如「（寒暄）你好呀。」）——据实标注，不臆断
      const bodies = dm.map((e) => String((e.payload || {}).body || (e.payload || {}).text || ""));
      const tmpl = bodies.filter((b) => /^（[^）]*）/.test(b) || /寒暄|你好呀/.test(b)).length;
      const templatedLikely = bodies.length > 0 && tmpl >= Math.max(2, Math.ceil(bodies.length * 0.5));
      const chip = (label, n, color) => `<span class="chip" title="${escapeHtml(label)}">${escapeHtml(label)} <b>${n}</b></span>`;
      const relDimCn = (d) => ({ affinity: "好感", trust: "信任", respect: "尊重", familiarity: "熟悉度" }[d] || d);

      const threadRows = thread.slice(-80).map((e) => {
        const h = R.humanize(e, this.ctx);
        const p = e.payload || {};
        const isDm = e.type === "MSG_DM";
        const color = (h.style && h.style.color) || "#8b98ab";
        // 正文不要重复人名：DM 只显示「原话」；协商去掉开头的人名前缀
        let body;
        if (isDm) {
          body = `「${String(p.body || p.text || "").slice(0, 100)}」`;
        } else {
          body = h.text || "";
          const f = nm(p.from || "");
          if (f && body.startsWith(f)) body = body.slice(f.length).replace(/^\s+/, "");
          if (p.by) { const b = nm(p.by); if (b && body.startsWith(b)) body = body.slice(b.length).replace(/^\s+/, ""); }
        }
        const arrow = isDm ? "→" : "⇄";
        return `<div class="soc-item ${isDm ? "dm" : "offer"}" style="border-left-color:${color}">` +
          `<span class="soc-r muted">r${e.round}</span>` +
          `<span class="soc-actors"><a class="ev-actor" data-agent="${escapeHtml(p.from || "")}">${escapeHtml(nm(p.from || ""))}</a>` +
          (p.to ? ` <span class="muted">${arrow}</span> <a class="ev-actor" data-agent="${escapeHtml(p.to)}">${escapeHtml(nm(p.to))}</a>` : "") + `</span>` +
          `<span class="soc-text">${escapeHtml(body)}</span></div>`;
      }).join("") || `<div class="muted" style="padding:6px 0">${sel ? "这对人物暂无对话" : "暂无对话/协商记录"}</div>`;

      const pairRows = pairList.slice(0, 40).map((pr) => {
        const k = [pr.a, pr.b].sort().join("|");
        return `<div class="soc-pair ${sel === k ? "sel" : ""}" data-pair="${escapeHtml(k)}">` +
          `<span class="sp-names">${escapeHtml(nm(pr.a))} ↔ ${escapeHtml(nm(pr.b))}</span>` +
          `<span class="muted">${pr.msg} 私聊 · ${pr.offer} 协商</span></div>`;
      }).join("") || "<div class='muted'>暂无人物往来</div>";

      const encRows = Object.values(enc).sort((x, y) => y.n - x.n).slice(0, 12).map((e) =>
        `<div class="kv"><span class="k">${escapeHtml(nm(e.a))} ↔ ${escapeHtml(nm(e.b))}</span><span>在「${escapeHtml(pl(e.place))}」共处 ${e.n} 次</span></div>`
      ).join("") || "<div class='muted'>暂无共处记录</div>";
      const relRows = Object.values(rel).sort((x, y) => y.n - x.n).slice(0, 12).map((r) =>
        `<div class="kv"><span class="k">${escapeHtml(nm(r.from))} → ${escapeHtml(nm(r.to))}</span><span>${relDimCn(r.dim)} ${r.delta >= 0 ? "+" + r.delta : r.delta}（${r.n} 次${r.cause ? "，" + escapeHtml(R.reasonCn(r.cause)) : ""}）</span></div>`
      ).join("") || "<div class='muted'>暂无关系变化</div>";

      body.innerHTML = `
        <div class="insp-sec"><h4>社交概览 ${helpTip("当前日志中各类社交事件的计数；公开/群聊若为 0，说明引擎当前只实现了一对一私聊。")}</h4>
          <div class="chips">
            ${chip("私聊 MSG_DM", counts.MSG_DM || 0)} ${chip("公开 MSG_PUBLIC", counts.MSG_PUBLIC || 0)}
            ${chip("群聊 MSG_GROUP", counts.MSG_GROUP || 0)} ${chip("协商发起", counts.OFFER_CREATED || 0)}
            ${chip("协商接受", counts.OFFER_ACCEPTED || 0)} ${chip("协商拒绝", counts.OFFER_REJECTED || 0)}
            ${chip("协商还价", counts.OFFER_COUNTERED || 0)} ${chip("共处", counts.RELATION_ENCOUNTER || 0)}
            ${chip("关系变化", counts.RELATION_CHANGE || 0)} ${chip("冲突", counts.CONFLICT_STARTED || 0)}
          </div>
          <div class="soc-note">一对一私聊：<b>有</b>（MSG_DM）。一对多/多对多（MSG_PUBLIC / MSG_GROUP）：<b>${groupUnimplemented ? "当前日志中为 0 —— 引擎侧尚未发生/未实现" : "有"}</b>。${groupUnimplemented ? "这里如实呈现，不假装有群聊。" : ""}</div>
          <div class="soc-note muted">注：${templatedLikely
            ? "本日志的私聊措辞疑似<b>模板</b>（非 LLM 生成）；正式措辞以真实 LLM 对话日志为准。"
            : "对话措辞取自日志原文（「」内为未被改写的引用）。"}</div>
        </div>
        <div class="insp-sec"><h4>谁在和谁来往（按人物对）</h4><div class="soc-pairs">${pairRows}</div>
          ${sel ? `<div class="muted" style="margin-top:4px"><a class="wl" id="soc-clear">显示全部</a></div>` : ""}</div>
        <div class="insp-sec"><h4>对话 / 协商线程 <span class="muted">${sel ? "（已按人物对筛选）" : ""}</span></h4><div class="soc-thread">${threadRows}</div></div>
        <div class="insp-sec"><h4>一起待过（共处）</h4>${encRows}</div>
        <div class="insp-sec"><h4>关系如何变化</h4>${relRows}</div>`;

      body.querySelectorAll(".soc-pair").forEach((el) => {
        el.onclick = () => { this.socialPair = (this.socialPair === el.dataset.pair) ? null : el.dataset.pair; this.renderSocial(replay, rd); };
      });
      const clr = body.querySelector("#soc-clear");
      if (clr) clr.onclick = () => { this.socialPair = null; this.renderSocial(replay, rd); };
      body.querySelectorAll(".ev-actor").forEach((el) => {
        el.onclick = (e) => { e.stopPropagation(); const id = el.dataset.agent; if (id && this.onOpenAgent) this.onOpenAgent(id); };
      });
    }

    // ---------------- 小镇周报（T240/G-9）：全部取自日志，逐条可溯源，不编造 ----------------
    renderWeekly(replay, rd) {
      const doc = global.document; if (!doc) return;
      const body = doc.getElementById("weekly-body"); if (!body) return;
      const RPW = 84;                                   // 1 周 = 7 日 × 12 回合
      const wk = (this.weeklyWeek != null) ? this.weeklyWeek : Math.floor(rd / RPW);
      const start = wk * RPW, end = Math.min(rd, start + RPW - 1);
      const evs = [];
      for (let r = start; r <= end; r++) for (const e of replay.eventsInRound(r)) evs.push(e);
      const cnt = {};
      evs.forEach((e) => { cnt[e.type] = (cnt[e.type] || 0) + 1; });
      const f = replay.facts[end] || {};
      const facts = [
        ["存活 / 总数", `${f.alive} / ${f.total}`],
        ["货币总量 (mu)", String(f.moneySupply)],
        ["本周事件", String(evs.length)],
        ["死亡 / 复活", `${cnt.AGENT_DIED || 0} / ${cnt.AGENT_REVIVED || 0}`],
      ];
      const HL = { AGENT_BORN: 1, AGENT_DIED: 1, AGENT_REVIVED: 1, MARKET_TRADE: 1, CONFLICT_STARTED: 1,
        CONFLICT_RESOLVED: 1, NORM_ADOPTED: 1, ROLE_CHANGE: 1, GOAL_ACHIEVED: 1, OFFER_ACCEPTED: 1,
        OFFER_REJECTED: 1, SEED_EVENT: 1 };
      const hl = evs.filter((e) => HL[e.type]).sort((a, b) => a.seq - b.seq).slice(0, 14);
      const msgs = evs.filter((e) => /^MSG_/.test(e.type)).slice(-6);
      const narr = evs.filter((e) => e.type === "NARRATIVE").slice(0, 4);
      const hlRows = hl.map((e) => `<div class="wk-row"><a class="wl" data-seq="${e.seq}">r${e.round}</a> ${escapeHtml(R.humanize(e, this.ctx).text)}</div>`).join("") || "<div class='muted'>本周无关键事件</div>";
      const msgRows = msgs.map((e) => `<div class="wk-quote">${escapeHtml(R.humanize(e, this.ctx).text)} <a class="wl" data-seq="${e.seq}">#${e.seq}</a></div>`).join("") || "<div class='muted'>本周无发言</div>";
      const narrRows = narr.map((e) => `<div class="wk-narr">${escapeHtml(R.humanize(e, this.ctx).text)} <a class="wl" data-seq="${e.seq}">#${e.seq}</a></div>`).join("");
      body.innerHTML = `
        <div class="insp-sec"><h4>第 ${wk + 1} 周 · 小镇周报 ${helpTip('"本周" = 7日 × 12回合；数字与句子全部取自日志，逐条可点回溯（不编造）。')}</h4>
          <div class="kfacts">${facts.map(([k, v]) => `<div class="kfact"><div class="k">${escapeHtml(k)}</div><div class="v">${escapeHtml(v)}</div></div>`).join("")}</div>
        </div>
        ${narrRows ? `<div class="insp-sec"><h4>周报正文（日志叙事 · 可溯源）</h4>${narrRows}</div>` : ""}
        <div class="insp-sec"><h4>本周纪事（编年史高光）</h4>${hlRows}</div>
        <div class="insp-sec"><h4>镇民之言（原话引用，未改写）</h4>${msgRows}</div>`;
      body.querySelectorAll(".wl").forEach((el) => {
        el.onclick = (e) => { e.stopPropagation(); const s = Number(el.dataset.seq); const r = (this._seqIndex || {})[s]; if (r != null && this.onJumpRound) { this._focusSeq = s; this.onJumpRound(r); } };
      });
    }

    // ---------------- 经济 / 制度 因果面板（G-12；依 obs 面板契约 v2 P3/T101）----------------
    // 只读：全部由当前日志**确定性重算**（同日志逐字节可复现）；诚实标注已知缺口。
    renderEcon(replay, rd) {
      const doc = global.document;
      if (!doc) return;
      const body = doc.getElementById("econ-body");
      if (!body) return;
      const nm = this.ctx.name;
      // 逐回合货币总量（TURN_SEAL.money_supply 优先，缺则取 facts）
      const series = [];
      let minted = 0, burned = 0, taxIn = 0, ubiOut = 0, volume = 0, nTrade = 0, nProduce = 0;
      const cnt = (t) => (replay.eventTypeCount[t] || 0);
      for (let r = (replay.rounds[0] || 0); r <= rd; r++) {
        const f = replay.facts[r] || {};
        series.push(f.moneySupply || 0);
        for (const e of replay.eventsInRound(r)) {
          const p = e.payload || {};
          if (e.type === "MONEY_MINTED") minted += num(p.amount);
          else if (e.type === "MONEY_BURNED") burned += num(p.amount);
          else if (e.type === "TAX_LEVIED") taxIn += num(p.amount);
          else if (e.type === "UBI_PAID") ubiOut += num(p.amount);
          else if (e.type === "TRANSFER" || e.type === "MARKET_TRADE") { volume += num(p.amount != null ? p.amount : p.price); nTrade++; }
          else if (e.type === "ACTIVITY_COMPLETED") nProduce++;
        }
      }
      const supply = (replay.facts[rd] || {}).moneySupply || 0;
      const balances = Object.keys(replay.snapshots[rd] || {}).map((id) => Math.max(0, (replay.snapshots[rd][id].money) || 0));
      const gini = giniOf(balances);
      const V = supply ? volume / supply : 0;
      const taxPool = taxIn - ubiOut;
      // 制度
      const nProp = cnt("NORM_PROPOSED"), nAdopt = cnt("NORM_ADOPTED"), nGroup = cnt("GROUP_CREATED");
      const nContract = cnt("CONTRACT_CREATED") + cnt("CONTRACT_SIGNED");   // 当前事件表无契约事件 → 0
      const admitRate = nProp ? nAdopt / nProp : 0;
      // 通道
      const cDM = cnt("MSG_DM"), cPUB = cnt("MSG_PUBLIC"), cGRP = cnt("MSG_GROUP");
      const chTot = Math.max(1, cDM + cPUB + cGRP);
      // 已知缺口（诚实）
      const gapP1 = (nTrade === 0) || (volume === 0);
      const spark = sparkline(series);
      const money = (v) => (v >= 1000 ? v.toLocaleString("en-US") : String(Math.round(v * 100) / 100));
      const card = (k, v, sub) => `<div class="kfact"><div class="k">${escapeHtml(k)}</div><div class="v">${v}</div>${sub ? `<div class="k" style="margin-top:2px">${sub}</div>` : ""}</div>`;
      const bar = (label, n, total, color) => `<div class="bar"><span class="lbl">${escapeHtml(label)}</span><span class="track"><span class="fill" style="width:${total ? Math.round(100 * n / total) : 0}%;background:${color}"></span></span><span>${n}</span></div>`;
      body.innerHTML = `
        <div class="insp-sec"><h4>经济循环 ${helpTip("只读日志确定性重算；货币总量优先取每回合 TURN_SEAL.money_supply。")}</h4>
          <div class="kfacts">
            ${card("货币总量 M(t)", money(supply) + " mu", "round ≤ " + rd)}
            ${card("铸 / 销毁（累计）", money(minted) + " / " + money(burned), "net " + money(minted - burned))}
            ${card("税池", money(taxPool) + " mu", "税入 " + money(taxIn) + " − UBI " + money(ubiOut))}
            ${card("交易额 / 笔数", money(volume) + " mu", nTrade + " 笔")}
            ${card("货币流速 V", V.toFixed(4), "交易额 / 货币总量")}
            ${card("净值 Gini", gini.toFixed(3), balances.length + " 人")}
          </div>
          <div class="sec-sub">M(t) 走势（逐回合）</div>
          <div class="econspark">${spark}</div>
          ${gapP1 ? `<div class="soc-note">已知缺口 <b>G-P1-1</b>：本 run Agent 间<span>零交易/无工资</span>——"商品→货币转换通道"缺失；V 偏低属预期，非异常。</div>` : ""}
        </div>
        <div class="insp-sec"><h4>制度涌现 ${helpTip("规范采纳漏斗；契约/投票当前事件表未产出则标『未产出』。")}</h4>
          <div class="sec-sub">规范：提议 ${nProp} → 采纳 ${nAdopt}（采纳率 ${(admitRate * 100).toFixed(0)}%）</div>
          <div class="track" style="height:10px"><div class="fill" style="width:${nProp ? Math.round(100 * nAdopt / nProp) : 0}%"></div></div>
          <div class="kv"><span class="k">群组（GROUP_CREATED）</span><span>${nGroup}</span></div>
          <div class="kv"><span class="k">契约 / 投票</span><span>${nContract}（未产出）</span></div>
        </div>
        <div class="insp-sec"><h4>沟通通道</h4>
          ${bar("私聊 DM", cDM, chTot, "#5cc8ff")}
          ${bar("公开 PUBLIC", cPUB, chTot, "#ffcf5c")}
          ${bar("群聊 GROUP", cGRP, chTot, "#c08bff")}
          <div class="muted" style="font-size:11px;margin-top:4px">数据源：只读日志重算（同日志逐字节可复现）</div>
          <div class="muted" style="font-size:11px">口径：M(t) 取 TURN_SEAL.money_supply；『铸/销毁』仅按 MONEY_MINTED/BURNED 事件累计，二者口径不同（play 视图剔噪/其它沉淀），**数值不吻合非异常**。</div>
        </div>`;
    }

    _row(ev, h) {
      const st = h.style || {};
      const actor = h.actor && /^[PA]\d+/.test(h.actor) ? h.actor : "";
      const chipColor = st.color || "#8b98ab";
      // 名字只出现一次：人话句若以该名字开头，则把开头名字做成可点 chip、正文去掉重复
      let text = h.text || "";
      let lead = "";
      const dn = actor ? this.ctx.name(actor) : "";
      if (actor && dn) {
        lead = `<span class="ev-actor" data-agent="${escapeHtml(actor)}" style="border-color:${chipColor}">${escapeHtml(dn)}</span>`;
        if (text.startsWith(dn)) text = text.slice(dn.length).replace(/^\s+/, "");
      }
      const cause = h.causal;
      const hasWhy = cause && (cause.code || (cause.links && cause.links.length));
      const why = hasWhy ? `<span class="ev-why">⌄ 为什么</span>` : "";
      return `<div class="ev-card" data-seq="${ev.seq}" style="border-left-color:${chipColor}">` +
        `<div class="ev-head">` +
        this._iconHtml(st) +
        lead +
        `<span class="ev-text">${escapeHtml(text)}</span>` +
        `<span class="ev-seq muted">#${ev.seq}</span>` +
        why +
        `<span class="ev-raw-toggle" title="查看原始事件">▤</span>` +
        `</div>` +
        this._cardHtml(ev) +
        `<div class="ev-detail" hidden>${this._detail(ev, h)}</div>` +
        `</div>`;
    }

    // 事件卡（T111）：命中 `HITTSprites.EVENT_CARDS` 映射的事件类型 → 显示手绘像素卡缩略图
    // （四区规格见 assets/event-card-spec.md；单一在用集 = event_cards_hand）。缺图/未映射则留空。
    _cardHtml(ev) {
      const Sp = global.HITTSprites;
      if (!Sp || !ev || !ev.type) return "";
      const slug = eventCardSlug(ev, Sp);       // T118：门控判定（机械事件默认不配卡）
      if (!slug) return "";
      const url = (Sp.EVENT_CARD_BASE || "") + slug + ".png";
      // 结构归 art-director；样式（尺寸/圆角/悬停/点击放大）由 shell 侧 app.css + _wireCardArt 负责
      return `<div class="ev-cardart">` +
        `<img class="ev-cardart-img" src="${url}" alt="${escapeHtml(slug)}" loading="lazy" data-full="${url}"></div>`;
    }

    // 图标：若 art-director × pixel-asset-artist 的图标图集就绪（单一真源 EVENT_STYLE.icon ↔ 图集键），
    // 则用 16×16 像素图标；否则退化为「族色圆点 + 单字符」（禁用 emoji）。
    _iconHtml(st) {
      const color = (st && st.color) || "#8b98ab";
      const key = (st && st.icon) || "dot";
      const atlas = global.HITTSprites && global.HITTSprites.ICON_ATLAS;
      if (atlas && atlas.url && atlas.index && atlas.index[key] != null) {
        const s = atlas.size || 16, cols = atlas.cols || 1, i = atlas.index[key];
        const maxI = Math.max.apply(null, Object.keys(atlas.index).map((k) => atlas.index[k]));
        const rows = Math.max(1, Math.ceil((maxI + 1) / cols));
        const disp = 16;                          // 列表行图标 16px（大展示用 32px 源）
        const k = disp / s;
        const col = i % cols, row = Math.floor(i / cols);
        return `<span class="ev-ico px" style="width:${disp}px;height:${disp}px;` +
          `background-image:url('${atlas.url}');` +
          `background-size:${cols * s * k}px ${rows * s * k}px;` +
          `background-position:${-(col * s * k)}px ${-(row * s * k)}px;"></span>`;
      }
      return `<span class="ev-ico dot" style="color:${color};border-color:${color}">${escapeHtml(this._icon(key))}</span>`;
    }

    _icon(key) {
      const glyph = { skull: "†", revive: "✦", born: "✚", loan: "§", shop: "■", tax: "%", "gift-ubi": "✚",
        "coin-arrow": "»", "coin-init": "◈", walk: "▶", pin: "▾", relation: "⇄", "speech-dm": "✉",
        "speech-public": "¶", "speech-group": "∷", goal: "◎", "goal-ok": "★", "goal-x": "✕", clash: "⚡",
        "clash-ok": "✓", book: "≡", judge: "◐", need: "◔", state: "◉", "loan-broken": "✖", metabolism: "◆",
        drop: "▽", gavel: "§", "revive-fee": "✚", mint: "◇", burn: "▲", "bank-in": "▼", "bank-out": "▲",
        percent: "‰", "norm-new": "§", "norm-ok": "✓", "norm-bad": "✗", offer: "⇢", "offer-ok": "✓",
        "offer-no": "✗", meet: "◵", role: "◆", tag: "▣", seed: "❖", reflect: "◇", skill: "◈", "skill-up": "★",
        trophy: "♛", group: "∷", calendar: "▤", "calendar-edit": "▥", "act-play": "▶", "act-done": "✓",
        "act-stop": "⏸", reject: "⛒", alert: "⚠", error: "✖", world: "◍" };
      return glyph[key] || "◆";
    }

    _detail(ev, h) {
      const c = h.causal || {};
      const parts = [];
      if (c.causeText) {
        parts.push(`<div class="why-line ${c.inferred ? "infer" : "fact"}">` +
          `${c.inferred ? "推测：" : "因为："}${escapeHtml(c.causeText)}` +
          `${c.inferred ? "" : `（来源 #${ev.seq}）`}</div>`);
      }
      if (c.links && c.links.length) {
        const seqLinks = c.links.filter((l) => l.seq != null);
        // G-8 剧情卡：有 seq→record 映射时，渲染「因果链」（上游事件 → 本条），事实分色、链节可点溯源
        if (seqLinks.length && this._eventsBySeq) {
          const nodes = seqLinks.map((l) => {
            const rec = this._eventsBySeq[l.seq];
            const txt = rec ? R.humanize(rec, this.ctx).text : `（事件 #${l.seq}）`;
            return `<div class="cc-node fact"><a class="wl" data-seq="${l.seq}">#${l.seq} ${escapeHtml(l.label || "起因")}</a><span class="cc-txt">${escapeHtml(txt)}</span></div>`;
          });
          parts.push(`<div class="causal-chain"><div class="cc-title">剧情卡 · 因果链（事实，可点溯源）</div>` +
            nodes.join(`<div class="cc-arrow">↓</div>`) +
            `<div class="cc-arrow">↓</div><div class="cc-node effect">本条：${escapeHtml(h.text || "")}</div></div>`);
        } else {
          parts.push(`<div class="why-links">` + c.links.map((l) =>
            l.seq != null ? `<a class="wl" data-seq="${l.seq}">${escapeHtml(l.label)} #${l.seq}</a>`
                          : `<span class="wl">${escapeHtml(l.label)} ${escapeHtml(l.goalId || "")}</span>`
          ).join("") + `</div>`);
        }
      }
      if (this.opts.auditMode) {
        parts.push(`<pre class="raw">${escapeHtml(JSON.stringify(ev, null, 1))}</pre>`);
      }
      return parts.length ? parts.join("") : `<div class="muted" style="font-size:11px">无附加信息</div>`;
    }

    _wire() {
      const self = this;
      this.streamEl.querySelectorAll(".ev-head").forEach((head) => {
        head.onclick = (e) => {
          if (e.target.classList.contains("ev-actor")) { return; }
          const card = head.parentElement;
          if (e.target.classList.contains("ev-raw-toggle")) {
            const d = card.querySelector(".ev-detail"); d.hidden = !d.hidden; return;
          }
          const why = card.querySelector(".ev-why");
          if (why) { const d = card.querySelector(".ev-detail"); d.hidden = !d.hidden; }
        };
      });
      this.streamEl.querySelectorAll(".ev-actor").forEach((el) => {
        el.onclick = (e) => { e.stopPropagation(); if (self.onOpenAgent) self.onOpenAgent(el.dataset.agent); };
      });
      this.streamEl.querySelectorAll(".wl").forEach((el) => {
        el.onclick = (e) => {
          e.stopPropagation();
          const seq = Number(el.dataset.seq);
          if (!isNaN(seq) && self.onJumpRound) {
            const rec = (self._seqIndex || {})[seq];
            if (rec != null) { self._focusSeq = seq; self.onJumpRound(rec); }
          }
        };
      });
      this._wireCardArt();
    }

    // 事件卡缩略图：点击/键盘 → 放大查看（lightbox）。结构由 art-director 提供，样式/交互归 shell。
    _wireCardArt() {
      const doc = global.document;
      if (!doc) return;
      const imgs = this.streamEl.querySelectorAll(".ev-cardart-img");
      if (!imgs.length) return;
      this._ensureLightbox();
      imgs.forEach((im) => {
        if (im.getAttribute) im.setAttribute("tabindex", "0");
        if (im.setAttribute) im.setAttribute("role", "button");
        if (im.setAttribute) im.setAttribute("aria-label", "查看事件卡详情（回车放大）");
        const open = (e) => { if (e && e.stopPropagation) e.stopPropagation(); this.openCardArt(im.dataset.full || im.src); };
        im.onclick = open;
        im.onkeydown = (e) => { if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") { e.preventDefault(); open(e); } };
      });
    }

    // 公开方法：打开事件卡放大层（供 main.js 的 ?card=<slug> 证据截图复用）
    openCardArt(src) {
      const doc = global.document;
      if (!doc || !src) return;
      const lb = this._ensureLightbox();
      lb.querySelector("img").src = src;
      lb.classList.add("open");
      const im = lb.querySelector("img");
      if (im && im.focus) { try { im.focus(); } catch (e) { /* ignore */ } }
    }

    _ensureLightbox() {
      const doc = global.document;
      let lb = doc.getElementById("ev-lightbox");
      if (lb) return lb;
      lb = doc.createElement("div");
      lb.id = "ev-lightbox";
      lb.className = "ev-lightbox";
      lb.setAttribute("role", "dialog");
      lb.setAttribute("aria-label", "事件卡放大查看（Esc 关闭）");
      lb.innerHTML = `<figure class="ev-lightbox-fig"><img class="ev-lightbox-img" alt="事件卡" tabindex="0">` +
        `<figcaption class="ev-lightbox-cap">点击空白处或按 Esc 关闭</figcaption></figure>`;
      // 仅点遮罩空白处关闭（点图片本身不关）
      lb.onclick = (e) => { if (e.target === lb) lb.classList.remove("open"); };
      doc.addEventListener("keydown", (e) => { if (e.key === "Escape") lb.classList.remove("open"); });
      doc.body.appendChild(lb);
      return lb;
    }
  }

  // 让人名在文本中可点（把 display_name 包成 chip）
  function hlNames(text, ctx) {
    return text; // 名字可点已通过 actor chip 提供；正文保持原样避免误伤
  }
  // T118 事件卡门控：机械事件（RELATION_CHANGE/NEED_UPDATE/PLACE_MOVE/ACTIVITY_*/LLM_JUDGMENT）
  // 默认不配卡；卡片由**活动 template** 或**语义条件**驱动。依据 v2/evidence/event_card_mapping_revised.json。
  // 原则：宁可不显示，也不显示错的。
  function eventCardSlug(ev, Sp) {
    const p = (ev && ev.payload) || {};
    const byTpl = Sp.EVENT_CARDS_BY_TEMPLATE || {};
    if (p.template && byTpl[p.template]) return byTpl[p.template];
    const byType = Sp.EVENT_CARDS || {};
    if (byType[ev.type]) return byType[ev.type];
    const th = (Sp.EVENT_CARD_GATE && Sp.EVENT_CARD_GATE.SCARCITY_THETA != null) ? Sp.EVENT_CARD_GATE.SCARCITY_THETA : 0.5;
    const rawSem = !(Sp.EVENT_CARD_GATE && Sp.EVENT_CARD_GATE.INCLUDE_RAW_SEMANTIC === false);
    switch (ev.type) {
      case "TRANSFER": return (rawSem && p.reason === "gift") ? "gift-giving" : "";
      case "DEPOSIT": case "WITHDRAW": return rawSem ? "saving-money" : "";
      case "STATE_CHANGE": return p.to === "exhausted" ? "emotion-burnout" : "";
      case "MARKET_TRADE": return (p.reason === "scarce_buy" || (typeof p.scarcity_index === "number" && p.scarcity_index >= th)) ? "scarcity-buy" : "";
      case "MSG_DM": return p.visibility === "private" ? "whispered-comm" : "";
      default: return "";
    }
  }

  function helpTip(tip) { return `<span class="help" title="${escapeHtml(tip)}">?</span>`; }
  function num(v) { return (typeof v === "number" && isFinite(v)) ? v : 0; }
  // Gini（非负数组）
  function giniOf(a) {
    if (!a || !a.length) return 0;
    const s = a.slice().sort((x, y) => x - y), n = s.length, sum = s.reduce((p, c) => p + c, 0);
    if (sum <= 0) return 0;
    let cum = 0; for (let i = 0; i < n; i++) cum += (i + 1) * s[i];
    return (2 * cum) / (n * sum) - (n + 1) / n;
  }
  // 迷你折线（自包含 SVG）
  function sparkline(vals) {
    if (!vals || vals.length < 2) return `<div class="muted" style="font-size:11px">（回合不足，无走势）</div>`;
    const w = 100, h = 30, mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals), rng = (mx - mn) || 1;
    const pts = vals.map((v, i) => `${(i / (vals.length - 1) * w).toFixed(1)},${(h - (v - mn) / rng * h).toFixed(1)}`).join(" ");
    return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" width="100%" height="40" class="spark">` +
      `<polyline points="${pts}" fill="none" stroke="#5cc8ff" stroke-width="2"/></svg>`;
  }

  function formatMoney(v) {
    if (v == null) return "—";
    if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(2) + "M";
    if (Math.abs(v) >= 1e3) return v.toLocaleString("en-US");
    return String(Math.round(v * 100) / 100);
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  global.HITTAudit = { Audit, formatMoney, eventCardSlug };
})(window);
