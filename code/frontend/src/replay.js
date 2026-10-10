/* replay.js — 只读日志回放：把事件日志确定性折叠成「按回合的状态视图」。
 * 铁律：前端不写世界、不参与判定；所有展示数据均由日志/config 重算，可复现。
 */
(function (global) {
  "use strict";

  // 事件类型 → 展示元信息（图标/配色/是否进事件流）
  const EVENT_META = {
    WORLD_INIT:        { icon: "🌍", color: "#8b98ab", stream: true },
    AGENT_BORN:        { icon: "🐣", color: "#5ddc82", stream: true },
    INIT_ENDOW:        { icon: "💰", color: "#ffcf5c", stream: true },
    MONEY_MINTED:      { icon: "🪙", color: "#ffcf5c", stream: true },
    MONEY_BURNED:      { icon: "🔥", color: "#ff8f6b", stream: true },
    TRANSFER:          { icon: "↔️", color: "#ffcf5c", stream: true },
    MARKET_TRADE:      { icon: "🛒", color: "#ffcf5c", stream: true },
    TAX_LEVIED:        { icon: "🏛️", color: "#ffcf5c", stream: true },
    UBI_PAID:          { icon: "🎁", color: "#ffcf5c", stream: true },
    METABOLISM:        { icon: "🍚", color: "#ffcf5c", stream: true },
    PENALTY_APPLIED:   { icon: "⚖️", color: "#ff8f6b", stream: true },
    AGENT_DIED:        { icon: "💀", color: "#ff5c5c", stream: true },
    AGENT_REVIVED:     { icon: "✨", color: "#5ddc82", stream: true },
    STATE_CHANGE:      { icon: "🔁", color: "#8b98ab", stream: true },
    MSG_PUBLIC:        { icon: "📢", color: "#5cc8ff", stream: true },
    MSG_DM:            { icon: "✉️", color: "#5cc8ff", stream: true },
    MSG_GROUP:         { icon: "👥", color: "#5cc8ff", stream: true },
    LLM_CALL:          { icon: "🧠", color: "#c08bff", stream: false },
    LLM_JUDGMENT:      { icon: "🧠", color: "#c08bff", stream: false },
    TIME_MARK:         { icon: "🕒", color: "#8b98ab", stream: false },
    PLACE_MOVE:        { icon: "🚶", color: "#5cc8ff", stream: true },
    PLACE_ARRIVED:     { icon: "📍", color: "#5cc8ff", stream: false },
    SCHEDULE_PLANNED:  { icon: "🗒️", color: "#8b98ab", stream: false },
    SCHEDULE_REVISED:  { icon: "🗒️", color: "#8b98ab", stream: false },
    ACTIVITY_STARTED:  { icon: "▶️", color: "#5ddc82", stream: true },
    ACTIVITY_COMPLETED:{ icon: "✅", color: "#5ddc82", stream: false },
    ACTIVITY_INTERRUPTED:{ icon: "⏸️", color: "#ff8f6b", stream: true },
    NEED_UPDATE:       { icon: "❤️", color: "#8b98ab", stream: false },
    GOAL_SET:          { icon: "🎯", color: "#ffcf5c", stream: true },
    GOAL_PROGRESS:     { icon: "🎯", color: "#ffcf5c", stream: false },
    GOAL_ACHIEVED:     { icon: "🏆", color: "#ffcf5c", stream: true },
    GOAL_ABANDON:      { icon: "🚮", color: "#8b98ab", stream: false },
    RELATION_CHANGE:   { icon: "🤝", color: "#5ddc82", stream: true },
    RELATION_ENCOUNTER:{ icon: "👋", color: "#5ddc82", stream: false },
    MEMORY_WRITE:      { icon: "🧩", color: "#8b98ab", stream: false },
    MEMORY_RETRIEVE:   { icon: "🔍", color: "#8b98ab", stream: false },
    MEMORY_REFLECT:    { icon: "💭", color: "#c08bff", stream: true },
    OBSERVATION:       { icon: "👀", color: "#8b98ab", stream: false },
    SEED_EVENT:        { icon: "🌱", color: "#5ddc82", stream: true },
    TAG_EMITTED:       { icon: "🏷️", color: "#8b98ab", stream: false },
    ROLE_CHANGE:       { icon: "🔄", color: "#ffcf5c", stream: true },
    NORM_PROPOSED:     { icon: "📜", color: "#5cc8ff", stream: true },
    NORM_ADOPTED:      { icon: "📜", color: "#5ddc82", stream: true },
    NORM_VIOLATED:     { icon: "🚫", color: "#ff5c5c", stream: true },
    GROUP_CREATED:     { icon: "👥", color: "#5ddc82", stream: true },
    GROUP_JOINED:      { icon: "👥", color: "#5ddc82", stream: true },
    SKILL_LEVEL_UP:    { icon: "⭐", color: "#ffcf5c", stream: true },
    INTENT_REJECTED:   { icon: "⛔", color: "#ff8f6b", stream: true },
    ECONOMY_INVARIANT_VIOLATION: { icon: "🧨", color: "#ff5c5c", stream: true },
    SYSTEM_ERROR:      { icon: "🧨", color: "#ff5c5c", stream: true },
    TURN_SEAL:         { icon: "🔒", color: "#8b98ab", stream: false },
    NARRATIVE:         { icon: "📖", color: "#c08bff", stream: true },
  };
  function meta(type) { return EVENT_META[type] || { icon: "•", color: "#8b98ab", stream: true }; }

  const MONEY_RULES = {
    // type: [field(s) acting on actor / counterparty]
    INIT_ENDOW: { agent: "agent_id", amount: "amount", sign: +1 },
    MONEY_MINTED: { supply: "amount", sign: +1 },
    MONEY_BURNED: { supply: "amount", sign: -1 },
    TRANSFER: { from: "from", to: "to", amount: "amount" },
    MARKET_TRADE: { from: "buyer", to: "seller", amount: "price" },
    TAX_LEVIED: { agent: "agent_id", amount: "amount", sign: -1 },
    UBI_PAID: { agent: "agent_id", amount: "amount", sign: +1 },
    METABOLISM: { agent: "agent_id", amount: "amount", sign: -1 },
    PENALTY_APPLIED: { agent: "agent_id", amount: "amount", sign: -1 },
    REVIVE_FEE_PAID: { agent: "agent_id", amount: "amount", sign: -1 },
    LOAN_ISSUED: { agent: "borrower", amount: "amount", sign: +1 },
    LOAN_REPAY: { agent: "borrower", amount: "amount", sign: -1 },
    INTEREST_CHARGED: { agent: "borrower", amount: "amount", sign: -1 },
    DEPOSIT: { agent: "agent_id", amount: "amount", sign: -1 },
    WITHDRAW: { agent: "agent_id", amount: "amount", sign: +1 },
    INTEREST_PAID: { agent: "agent_id", amount: "amount", sign: +1 },
  };

  function num(v) { return (typeof v === "number" && isFinite(v)) ? v : 0; }

  class Replay {
    constructor(records) {
      this.records = records;
      this.meta = { seed: null, engineVersion: null };
      this.rounds = [];
      this.byRound = {};      // r -> [records]
      this.snapshots = {};    // r -> agents map (cumulative, end of round)
      this.facts = {};        // r -> facts
      this.totalEvents = records.length;
      this.eventTypeCount = {};
      this._fold();
    }

    _fold() {
      const recs = this.records;
      // 分组
      const roundSet = new Set();
      recs.forEach((r) => {
        const rd = (r.round == null) ? 0 : r.round;
        roundSet.add(rd);
        (this.byRound[rd] = this.byRound[rd] || []).push(r);
      });
      this.rounds = Array.from(roundSet).sort((a, b) => a - b);

      const agents = {};
      let supply = 0;
      const bump = (id) => {
        if (!agents[id]) agents[id] = { location: "residence", status: "alive", money: 0, role: null, needs: {}, activity: null };
        return agents[id];
      };

      for (const rd of this.rounds) {
        const evs = this.byRound[rd];
        for (const ev of evs) {
          this.eventTypeCount[ev.type] = (this.eventTypeCount[ev.type] || 0) + 1;
          const p = ev.payload || {};
          if (ev.type === "WORLD_INIT") { this.meta.seed = p.seed; this.meta.engineVersion = p.engine_version; }
          this._apply(ev, p, agents, bump, (d) => { supply += d; });
        }
        // 快照（深拷贝需要的字段）
        const snap = {};
        Object.keys(agents).forEach((id) => {
          const a = agents[id];
          snap[id] = { location: a.location, status: a.status, money: a.money, role: a.role, activity: a.activity, needs: Object.assign({}, a.needs) };
        });
        this.snapshots[rd] = snap;
        this.facts[rd] = this._computeFacts(rd, snap, supply, evs);
      }

      if (this.rounds.length && this.rounds[0] !== 0) this.rounds.unshift(0);
      this.maxRound = this.rounds.length ? this.rounds[this.rounds.length - 1] : 0;
    }

    _apply(ev, p, agents, bump, addSupply) {
      const t = ev.type;
      switch (t) {
        case "AGENT_BORN": {
          const a = bump(p.agent_id);
          a.location = p.home_place || "residence";
          a.status = "alive";
          if (p.needs_init) a.needs = Object.assign({}, p.needs_init);
          if (p.role_id) a.role = p.role_id;
          break;
        }
        case "PLACE_MOVE": bump(p.agent_id).location = p.to_place || p.place || bump(p.agent_id).location; break;
        case "PLACE_ARRIVED": bump(p.agent_id).location = p.place || bump(p.agent_id).location; break;
        case "ACTIVITY_STARTED":
          bump(p.agent_id).activity = { type: p.activity_type, place: p.place, slot_id: p.slot_id };
          break;
        case "ACTIVITY_COMPLETED":
        case "ACTIVITY_INTERRUPTED":
          bump(p.agent_id).activity = null; break;
        case "NEED_UPDATE": {
          const a = bump(p.agent_id); if (p.dim) a.needs[p.dim] = p.after; break;
        }
        case "ROLE_CHANGE": {
          const a = bump(p.agent_id || p.from);
          if (p.to_role) a.role = p.to_role; break;
        }
        case "AGENT_DIED": { bump(p.agent_id).status = "dead"; bump(p.agent_id).activity = null; break; }
        case "AGENT_REVIVED": bump(p.agent_id).status = "alive"; break;
        case "STATE_CHANGE": {
          const id = p.agent_id || ev.actor;
          const a = bump(id);
          if (p.to && typeof p.to === "string") a.status = p.to;
          if (p.status) a.status = p.status;
          break;
        }
        case "TURN_SEAL":
          if (typeof p.money_supply === "number") this._sealSupply = p.money_supply;
          break;
        default: break;
      }
      // 货币
      const rule = MONEY_RULES[t];
      if (rule) {
        if (rule.supply) { addSupply(rule.sign * num(p[rule.supply])); }
        else if (rule.from && rule.to) {
          bump(p[rule.from]).money -= num(p[rule.amount]);
          bump(p[rule.to]).money += num(p[rule.amount]);
        } else if (rule.agent) {
          bump(p[rule.agent]).money += rule.sign * num(p[rule.amount]);
        }
      }
    }

    _computeFacts(rd, snap, computedSupply, evs) {
      const ids = Object.keys(snap);
      const alive = ids.filter((id) => snap[id].status !== "dead");
      const occupancy = {};
      alive.forEach((id) => {
        const loc = snap[id].location || "residence";
        occupancy[loc] = (occupancy[loc] || 0) + 1;
      });
      const sumMoney = ids.reduce((s, id) => s + num(snap[id].money), 0);
      // 优先采用 TURN_SEAL 的权威 money_supply（若日志存在且为当前回合）
      let supply = (this._sealSupply != null) ? this._sealSupply : computedSupply;
      const roundEventCount = {};
      evs.forEach((e) => { roundEventCount[e.type] = (roundEventCount[e.type] || 0) + 1; });
      return {
        round: rd,
        total: ids.length,
        alive: alive.length,
        aliveRate: ids.length ? alive.length / ids.length : 0,
        moneySupply: supply,
        sumMoney: sumMoney,
        occupancy: occupancy,
        eventsThisRound: evs.length,
        eventTypeCount: roundEventCount,
      };
    }

    // 某回合用于渲染的状态（叠加该回合的瞬时气泡）
    displayState(rd) {
      const base = this.snapshots[rd] || {};
      const out = {};
      Object.keys(base).forEach((id) => { out[id] = Object.assign({}, base[id], { bubble: null }); });
      const evs = this.byRound[rd] || [];
      for (const ev of evs) {
        const p = ev.payload || {};
        if (ev.type === "MSG_PUBLIC" || ev.type === "MSG_DM" || ev.type === "MSG_GROUP") {
          const id = p.from || p.agent_id || ev.actor;
          const text = p.text || p.content || p.message || p.msg || "";
          if (out[id]) out[id].bubble = truncate(text, 60);
        } else if (ev.type === "ACTIVITY_STARTED") {
          const id = p.agent_id;
          if (out[id]) out[id].bubble = activityLabel(p.activity_type, p.place);
        }
      }
      return { agents: out, round: rd };
    }

    eventsInRound(rd) { return this.byRound[rd] || []; }
    timeOf(rd) {
      const evs = this.byRound[rd] || [];
      let t = null;
      for (const e of evs) if (e.type === "TIME_MARK") t = e.payload;
      return t;
    }
    hasAnyType(types) {
      return types.some((t) => (this.eventTypeCount[t] || 0) > 0);
    }
  }

  const ACTIVITY_LABEL = {
    work: "工作", socialize: "社交", rest: "休息", self_care: "自理",
    leisure: "休闲", learn: "学习", trade: "交易", civic: "公共事务",
  };
  function activityLabel(type, place) {
    const t = ACTIVITY_LABEL[type] || type || "活动";
    return place ? `${t}@${place}` : t;
  }

  // ---- 挂钟时间（纯展示口径；引擎内部仍是抽象 tick：12 tick/日、84 tick/周）----
  // 1 tick = 2h；day = round//12；slot = (round%12)//3；hour = (6 + (round%12)*2) % 24
  const SLOT_NAMES = ["早晨", "午后", "傍晚", "夜里"];
  const SLOT_RANGES = ["06:00–12:00", "12:00–18:00", "18:00–24:00", "00:00–06:00"];
  function wallClock(round) {
    const r = ((round % 12) + 12) % 12;
    const day = Math.floor(round / 12);
    const slotIdx = Math.floor(r / 3);
    const tickInSlot = r % 3;
    const hour = (6 + r * 2) % 24;
    return {
      day: day + 1,
      slotIdx,
      tickInSlot,
      hour,
      hhmm: String(hour).padStart(2, "0") + ":00",
      slotName: SLOT_NAMES[slotIdx],
      range: SLOT_RANGES[slotIdx],
    };
  }
  function wallClockText(round) {
    const w = wallClock(round);
    return `第 ${w.day} 日 ${w.hhmm}（${w.slotName}）`;
  }
  function truncate(s, n) {
    s = String(s == null ? "" : s);
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  }

  // 事件的可读描述（审计事件流）
  function describe(ev) {
    const p = ev.payload || {};
    const who = p.agent_id || p.from || ev.actor || "";
    switch (ev.type) {
      case "AGENT_BORN": return `${who} 出生于 ${p.home_place || "?"}`;
      case "INIT_ENDOW": return `${who} 初始注入 ${p.amount} mu`;
      case "MONEY_MINTED": return `铸币 +${p.amount} mu（${p.reason || ""}）`;
      case "PLACE_MOVE": return `${who}: ${p.from_place} → ${p.to_place}（${p.travel_ticks ?? "?"} ticks）`;
      case "PLACE_ARRIVED": return `${who} 抵达 ${p.place}`;
      case "ACTIVITY_STARTED": return `${who} 在 ${p.place} 开始「${ACTIVITY_LABEL[p.activity_type] || p.activity_type}」（${p.slot_id || ""}）`;
      case "MSG_PUBLIC": case "MSG_DM": case "MSG_GROUP": {
        const txt = truncate(p.text || p.content || p.message || p.msg || "", 80);
        return `${who}：${txt}`;
      }
      case "TIME_MARK": return `→ 第${p.day}日 ${p.slot}（week ${p.week}, ${p.day_type}）`;
      case "AGENT_DIED": return `${who} 死亡`;
      case "AGENT_REVIVED": return `${who} 复活`;
      case "TURN_SEAL": return `回合封条 round=${p.round} money=${p.money_supply ?? "?"}`;
      case "INTENT_REJECTED": return `${who} 意图被拒（${p.reason || p.intent_class || ""}）`;
      default: {
        const keys = Object.keys(p).slice(0, 4);
        return keys.length ? `${who} ${JSON.stringify(pick(p, keys))}` : `${ev.actor || ""}`;
      }
    }
  }
  function pick(o, ks) { const r = {}; ks.forEach((k) => { r[k] = o[k]; }); return r; }

  // ---------------- 人话化 + 因果（T77，按 T76 §3/§5 规格）----------------
  // 原因/理由码 → 中文（事实译述）。以 illiquid_no_credit_*/negative_net_worth 标记为「推断」。
  const REASON_CN = {
    market_fee: "市场手续费", scarce_buy: "物资稀缺，买入", gift: "赠予", ubi: "全民基本收入",
    tax: "税收", negative_net_worth: "净值转负", low_liquidity: "流动性偏低", copresence: "同处一地",
    revival_credit: "为复活借贷", illiquid_no_credit_N: "流动性枯竭且借不到贷", illiquid: "流动性枯竭",
    liquidity_restored: "流动性恢复", metabolism: "代谢消耗", overdue: "逾期",
    system_account: "系统账户", preference: "偏好变化", maintenance: "维护", rent: "租金", wage: "工资",
    chat: "交谈", trade_success: "交易顺利", transfer_rescue: "转账救助", ssl_flag: "被标记",
    encounter: "相遇", decay: "随时间淡化", soft_judgment: "软判定", formed: "建立关系", not_formed: "未建立",
    "activity:work": "共同劳作", "activity:socialize": "共同社交",
    too_expensive: "价格过高", no_need: "暂无需要", declined: "谢绝",
  };
  function reasonCn(code) { return REASON_CN[code] || String(code || "").replace(/^activity:/, "共同活动：") || ""; }
  function isInferredCause(code) { return /illiquid_no_credit|negative_net_worth/.test(String(code || "")); }

  // 关系维度 → 中文
  const RELDIM_CN = { affinity: "好感", trust: "信任", respect: "尊重", familiarity: "熟悉度" };
  const relDimCn = (d) => RELDIM_CN[d] || d || "关系";

  // 生命周期状态 → 中文（避免裸露英文状态）
  const STATE_CN = { alive: "存活", near_death: "濒危", dead: "已死亡", revived: "已复活",
    frozen: "冻结", terminated: "已终止", warning: "告警" };
  const stateCn = (s) => (s == null || s === "") ? "" : (STATE_CN[s] || s);
  // 可选片段：字段缺失时整段省略，杜绝 "undefined"
  function paren(parts) { const ps = parts.filter((x) => x != null && x !== "" && !/undefined/.test(String(x))); return ps.length ? `（${ps.join("，")}）` : ""; }
  function nz(v, unit) { return (v == null || v === "") ? null : `${v}${unit || ""}`; }
  function hasNum(v) { return v != null && v !== "" && !Number.isNaN(Number(v)); }
  const NEED_CN = { energy: "精力", satiety: "饱食", social: "社交", esteem: "自尊", mastery: "成就", leisure: "闲暇" };
  const needCn = (d) => NEED_CN[d] || d || "需求";

  const EVENT_STYLE = () => (window.HITTSprites && window.HITTSprites.EVENT_STYLE) || {};
  function styleOf(type) {
    const st = EVENT_STYLE()[type];
    return st || { family: "SYS", icon: "dot", level: "detail", color: "#8b98ab" };
  }

  // 从事件里提取「因果」信息：事实字段 reason/cause + 可跳 seq 链接
  function causalOf(ev) {
    const p = ev.payload || {};
    const t = ev.type;
    let code = null;
    if (p.reason) code = p.reason;
    if (t === "STATE_CHANGE" || t === "AGENT_DIED" || t === "AGENT_REVIVED") code = p.cause || p.via || code;
    if (t === "RELATION_CHANGE") code = p.cause || code;
    if (t === "ROLE_CHANGE" || t === "NEED_UPDATE") code = p.cause || code;
    if (t === "MARKET_TRADE" || t === "TRANSFER") code = p.reason || code;
    const inferred = isInferredCause(code);
    const causeText = code ? reasonCn(code) : "";
    const links = [];
    if (p.cause_event_seq != null) links.push({ label: "起因事件", seq: p.cause_event_seq });
    if (p.source_event_seq != null) links.push({ label: "来源记忆事件", seq: p.source_event_seq });
    if (p.target_event_seq != null) links.push({ label: "被观察事件", seq: p.target_event_seq });
    if (Array.isArray(p.fact_event_seqs)) p.fact_event_seqs.slice(0, 8).forEach((s) => links.push({ label: "依据事件", seq: s }));
    if (p.goal_id) links.push({ label: "目标", goalId: p.goal_id });
    return { code, causeText, inferred, links, evidenceSeq: ev.seq };
  }

  // 人话模板（ctx: {name(id), place(id)}）
  function humanize(ev, ctx) {
    ctx = ctx || {};
    const nm = ctx.name || ((x) => x);
    const pl = ctx.place || ((x) => x || "");
    const p = ev.payload || {};
    const T = ev.type;
    const who = nm(p.agent_id || p.from || ev.actor || "");
    const S = styleOf(T);
    let text;
    switch (T) {
      case "WORLD_INIT": text = `世界初始化（seed=${p.seed}）`; break;
      case "AGENT_BORN": text = `${who} 在「${pl(p.home_place)}」出生`; break;
      case "INIT_ENDOW": text = `${who} 出生获得初始资金 ${p.amount} mu`; break;
      case "MONEY_MINTED": text = `系统注入 ${p.amount} mu`; break;
      case "MONEY_BURNED": text = `系统销毁 ${p.amount} mu`; break;
      case "TRANSFER": text = `${nm(p.from)} 给 ${nm(p.to)} ${p.amount} mu`; break;
      case "MARKET_TRADE": text = `${nm(p.buyer)} 在市场买了 ${p.qty} 件（${p.unit_price}mu/件，共 ${p.amount}）`; break;
      case "TAX_LEVIED": text = `${who} 缴税 ${p.amount} mu`; break;
      case "UBI_PAID": text = `${who} 领到全民基本收入 ${p.amount} mu`; break;
      case "PENALTY_APPLIED": text = `${who} 被罚 ${p.amount} mu`; break;
      case "LOAN_ISSUED": text = `${nm(p.borrower)} 借到一笔贷款 ${p.principal} mu` + paren([nz(p.rate_bp, "") && `利率 ${(p.rate_bp / 100)}%`, nz(p.due_round, "") && `到期 round ${p.due_round}`]); break;
      case "LOAN_REPAY": text = `${nm(p.borrower)} 还了贷款` + (hasNum(p.amount) ? ` ${p.amount} mu` : ""); break;
      case "INTEREST_CHARGED": text = `${nm(p.borrower)} 被计息 ${p.amount} mu` + paren([nz(p.rate_bp, "") && `${(p.rate_bp / 100)}%`]); break;
      case "LOAN_DEFAULT": text = `${nm(p.borrower)} 违约，欠款 ${p.outstanding} mu`; break;
      case "REVIVE_FEE_PAID": text = `${who} 支付复活费 ${p.amount} mu`; break;
      case "DEPOSIT": text = `${who} 存入银行 ${p.amount} mu`; break;
      case "WITHDRAW": text = `${who} 从银行取出 ${p.amount} mu`; break;
      case "METABOLISM": text = `${who} 本回合代谢消耗 ${p.amount} mu` + paren([nz(p.liquid, "") && `流动性 ${p.liquid}`]); break;
      case "STATE_CHANGE": text = `${who} 状态：${stateCn(p.from) || "—"} → ${stateCn(p.to) || "—"}` + (p.cause ? `（${reasonCn(p.cause)}）` : ""); break;
      case "AGENT_DIED": {
        const cause = causalOf(ev);
        text = `${who} 去世了` + paren([cause.causeText && `原因：${cause.causeText}`, nz(p.liquid, "") && `流动性 ${p.liquid} mu`]);
        break;
      }
      case "AGENT_REVIVED": text = `${who} 复活了` + paren([p.via && reasonCn(p.via), nz(p.cost, " mu") && `代价 ${p.cost} mu`, nz(p.freeze_rounds, "") && `冻结 ${p.freeze_rounds} 回合`]); break;
      case "MSG_PUBLIC": text = `${nm(p.from)} 公开说：「${truncate(p.body || p.text || "", 80)}」`; break;
      case "MSG_DM": text = `${nm(p.from)} 私信 ${nm(p.to)}：「${truncate(p.body || p.text || "", 80)}」`; break;
      case "MSG_GROUP": text = `${nm(p.from)} 在群里说：「${truncate(p.body || p.text || "", 80)}」`; break;
      case "RELATION_CHANGE": text = `${nm(p.from)} 对 ${nm(p.to)} 的${relDimCn(p.dim)} ${p.before}→${p.after}` + (p.cause ? `（${reasonCn(p.cause)}）` : ""); break;
      case "RELATION_ENCOUNTER": text = `${nm(p.a || p.from)} 与 ${nm(p.b || p.to)} 在「${pl(p.place)}」相遇`; break;
      case "OFFER_CREATED": text = `${nm(p.from)} 向 ${nm(p.to)} 发起${p.kind ? "「" + p.kind + "」" : ""}协商` + (p.terms ? `（${typeof p.terms === "string" ? p.terms : JSON.stringify(p.terms)}）` : ""); break;
      case "OFFER_ACCEPTED": {
        const by = p.by || p.to, other = [p.from, p.to].find((x) => x && x !== by);
        text = `${nm(by)} 接受了 ${nm(other)} 的协商` + (p.offer_id ? `（${p.offer_id}）` : ""); break;
      }
      case "OFFER_REJECTED": {
        const by = p.by || p.to, other = [p.from, p.to].find((x) => x && x !== by);
        text = `${nm(by)} 拒绝了 ${nm(other)} 的协商` + (p.reason ? `（${reasonCn(p.reason)}）` : ""); break;
      }
      case "OFFER_COUNTERED": {
        const by = p.by || p.from, other = [p.from, p.to].find((x) => x && x !== by);
        text = `${nm(by)} 对 ${nm(other)} 还价` + (p.new_terms ? `（${typeof p.new_terms === "string" ? p.new_terms : JSON.stringify(p.new_terms)}）` : ""); break;
      }
      case "OFFER_EXPIRED": text = `协商 ${p.offer_id || ""} 过期`; break;
      case "NORM_PROPOSED": text = `${nm(p.proposer)} 提议新规范（${p.norm_id}），支持 ${p.support_count} 人`; break;
      case "NORM_ADOPTED": text = `规范 ${p.norm_id} 被采纳（${(p.adopters||[]).length} 人）`; break;
      case "NORM_VIOLATED": text = `有人违反了规范 ${p.norm_id}`; break;
      case "CONFLICT_STARTED": text = `${(p.parties||[]).map(nm).join("、")} 起冲突（${p.rule_ref}，赌注 ${p.stakes}）`; break;
      case "CONFLICT_RESOLVED": text = `冲突结束，${nm(p.winner)} 胜出（${p.rule_ref}）`; break;
      case "ROLE_CHANGE": text = `${who} 身份变化（${p.from_role || "—"} → ${p.to_role || "—"}）`; break;
      case "GROUP_CREATED": case "GROUP_JOINED": case "GROUP_LEFT":
        text = `${who} ${T==="GROUP_CREATED"?"创建":T==="GROUP_JOINED"?"加入":"离开"}了群体 ${p.group_id || ""}`; break;
      case "TAG_EMITTED": text = `${who} 被贴了标签「${p.tag}」`; break;
      case "PLACE_MOVE": text = `${who} ` + (p.from_place ? `从「${pl(p.from_place)}」` : "") + `前往「${pl(p.to_place || p.place)}」` + (hasNum(p.travel_ticks) ? `（${p.travel_ticks} tick）` : ""); break;
      case "PLACE_ARRIVED": text = `${who} 到达「${pl(p.place || p.to_place)}」`; break;
      case "SCHEDULE_PLANNED": text = `${who} 制定了本周计划`; break;
      case "ACTIVITY_STARTED": text = `${who} ` + (p.place ? `在「${pl(p.place)}」` : "") + `开始${ACTIVITY_LABEL[p.activity_type || p.activity] || p.activity_type || p.activity || "活动"}`; break;
      case "ACTIVITY_COMPLETED": text = `${who} 完成${ACTIVITY_LABEL[p.activity_type || p.activity] || p.activity_type || p.activity || "活动"}`; break;
      case "ACTIVITY_INTERRUPTED": text = `${who} 的${ACTIVITY_LABEL[p.activity_type || p.activity] || p.activity_type || p.activity || "活动"}被打断`; break;
      case "NEED_UPDATE": text = `${who} 的${needCn(p.dim)}：${p.before ?? "?"} → ${p.after ?? "?"}`; break;
      case "GOAL_SET": text = `${who} 立下目标：${p.description_ref || p.kind || "新目标"}` + paren([p.kind && `类型 ${p.kind}`, p.layer && `层级 ${p.layer}`]); break;
      case "GOAL_ACHIEVED": text = `${who} 达成了目标 ${p.goal_id}`; break;
      case "GOAL_ABANDON": text = `${who} 放弃了目标 ${p.goal_id}`; break;
      case "SKILL_LEVEL_UP": text = `${who} 的 ${p.skill_id} 升到 ${p.level_after} 级`; break;
      case "MEMORY_REFLECT": text = `${who} 陷入了反思`; break;
      case "SEED_EVENT": text = `种子事件：${p.description_ref || p.kind || ""}`; break;
      case "LLM_JUDGMENT": text = `裁决（${p.dimension || "?"}）：${p.decision || ""}`; break;
      case "NARRATIVE": text = `${p.pov ? nm(p.pov) + " 的" : ""}视角小记（见人物故事）`; break;
      case "INTENT_REJECTED": text = `${who} 的意图被拒（${p.intent_class || ""}：${reasonCn(p.reason)}）`; break;
      case "TIME_MARK": text = `时间：第 ${p.day} 日 ${p.slot}`; break;
      case "TURN_SEAL": text = `回合封条 #${p.round}（货币 ${p.money_supply ?? "?"}）`; break;
      case "SYSTEM_ERROR": text = `系统错误：${p.message || p.reason || ""}`; break;
      default: {
        const k = Object.keys(p).slice(0, 3);
        text = who + (k.length ? ` ${JSON.stringify(pick(p, k))}` : "");
      }
    }
    // 安全网：任何模板遗漏的 undefined / 空括号 / 多余空格都在此清理
    text = String(text == null ? "" : text)
      .replace(/\s*undefined\s*/g, " ")
      .replace(/「\s*」/g, "")
      .replace(/（\s*[，,、]\s*/g, "（").replace(/[，,、]\s*）/g, "）").replace(/（\s*）/g, "")
      .replace(/\s*（\s*）/g, "").replace(/[ \t]{2,}/g, " ").trim();
    if (!text) text = (who ? who + " " : "") + (T || "事件");
    return { text, style: S, level: S.level || "detail", family: S.family || "SYS", causal: causalOf(ev), seq: ev.seq, round: ev.round, actor: p.agent_id || p.from || ev.actor };
  }

  global.HITTReplay = { Replay, meta, describe, activityLabel, wallClock, wallClockText, EVENT_META, humanize, styleOf, causalOf, reasonCn };
})(window);
