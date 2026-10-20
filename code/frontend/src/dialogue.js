/* dialogue.js — 青溪镇对话观看台（线程化聊天视图 + 按模拟时间回放）
 *
 * 铁律（与 frontend/README 的纪律一致）：
 *   1) 只读 threads.json（由 tools/gen_threads.py 从真源 run.jsonl 派生），不写世界、不参与判定；
 *   2) **不推断**任何线程结构/时间/人物：页面里出现的每个数字都带 seq 或来自数据文件的
 *      stats/source；日志里没有的键一律显示「日志未记录」；
 *   3) 旧格式（无 thread_id）走空态标记，不白屏、不报错。
 *
 * 页面数据契约见 tools/gen_threads.py 顶部注释（hitt.dialogue.threads/1）。
 */
(function () {
  "use strict";

  // ---------------- 常量 / 小工具 ----------------
  var SLOT_CN = { morning: "早晨", afternoon: "午后", evening: "傍晚", night: "夜里" };
  var CHANNEL_CN = { dm: "私聊", public: "公开说", group: "群聊" };
  var DIM_CN = { affinity: "亲近", trust: "信任", familiarity: "熟悉", respect: "敬重" };
  var NEED_CN = { energy: "体力", satiety: "饱腹", social: "社交", esteem: "尊重", mastery: "成就", leisure: "闲暇" };
  var SPRITES = ["red", "green", "blue", "yellow", "purple", "teal", "orange", "slate"];

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "text") n.textContent = attrs[k];
        else if (k === "html") n.innerHTML = attrs[k];
        else if (k === "class") n.className = attrs[k];
        else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), attrs[k]);
        else n.setAttribute(k, attrs[k]);
      });
    }
    (children || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }
  function text(s) { return document.createTextNode(s == null ? "" : String(s)); }
  function hash2(s) {                       // 只用于挑像素立绘（纯展示，不影响语义）
    var h = 2166136261;
    s = String(s || "");
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return (h >>> 0);
  }
  function spriteOf(agentId) { return SPRITES[hash2(agentId) % SPRITES.length]; }
  function wallClock(round) {               // 与 src/replay.js 同口径：1 tick = 2h，06:00 起
    if (round == null || isNaN(round)) return null;
    var hour = (6 + ((round % 12) * 2)) % 24;
    var mm = "00";
    return (hour < 10 ? "0" : "") + hour + ":" + mm;
  }
  function timeLabel(m) {
    var day = (m.day != null) ? m.day : (m.round != null ? Math.floor(m.round / 12) : null);
    var slot = m.slot ? (SLOT_CN[m.slot] || m.slot) : null;
    var hh = wallClock(m.round);
    var parts = [];
    parts.push(day != null ? ("第 " + (day + 1) + " 天") : "日期未记录");
    if (slot) parts.push(slot);
    if (hh) parts.push(hh);
    return parts.join(" · ");
  }
  function shortSha(s) { return s ? String(s).slice(0, 12) : "—"; }
  function fmtNum(v) { return (v == null || v === "") ? "—" : String(v); }

  var state = {
    data: null,
    threads: [],        // 原始线程（已按时间排序）
    flat: [],           // 扁平化消息（全序），元素 {t: threadIndex, m: msg}
    filters: { multiOnly: true, person: "", place: "", minTurns: 0, search: "" },
    speed: 1,
    playing: false,
    cursor: 0,
    timer: null,
    expanded: {},       // thread_id|legacy-seq -> bool
    ready: false
  };

  // ---------------- 数据加载 ----------------
  function candidateUrls() {
    var q = new URLSearchParams(location.search);
    var list = [];
    if (q.get("data")) list.push(q.get("data"));
    list.push("sample/dialogue_demo/threads.json");
    list.push("sample/dialogue_run1/threads.json");
    return list;
  }

  async function fetchJSON(url) {
    var res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }

  async function loadDefault() {
    var errs = [];
    var urls = candidateUrls();
    for (var i = 0; i < urls.length; i++) {
      try {
        var d = await fetchJSON(urls[i]);
        state.dataUrl = urls[i];
        return d;
      } catch (e) {
        errs.push(urls[i] + " → " + e.message);
      }
    }
    showEmpty(
      "没有找到对话数据。",
      [
        "生成命令（从真源 run.jsonl 派生，只读）：",
        "cd code && python frontend/tools/gen_threads.py \\",
        "    --log <run 目录>/run.jsonl --meta <run 目录>/meta.json \\",
        "    --out frontend/sample/dialogue_demo/threads.json",
        "",
        "或在页面右上「载入数据」直接选一个 threads.json。",
        "尝试过的路径：" 
      ].concat(errs.map(function (e) { return "  · " + e; }))
    );
    return null;
  }

  // ---------------- 数据装配 ----------------
  function prepare(data) {
    state.data = data;
    state.threads = (data.threads || []).slice();
    state.flat = [];
    state.threads.forEach(function (t, ti) {
      t.messages.forEach(function (m) { state.flat.push({ t: ti, m: m }); });
    });
    state.flat.sort(function (a, b) { return (a.m.seq || 0) - (b.m.seq || 0); });
    state.cursor = state.flat.length;

    var q = new URLSearchParams(location.search);
    if (q.get("person")) state.filters.person = q.get("person");
    if (q.get("place")) state.filters.place = q.get("place");
    if (q.get("min")) state.filters.minTurns = Number(q.get("min")) || 0;
    if (q.get("multi") === "1") state.filters.multiOnly = true;
    if (q.get("multi") === "0") state.filters.multiOnly = false;
    if (q.get("q")) state.filters.search = q.get("q");

    var st = data.stats || {};
    // 旧格式日志：默认关掉「只看多轮」，否则页面是空的（空态提示见 notice）
    if (!st.multi_turn_threads && st.legacy_messages) {
      state.filters.multiOnly = false;
      document.querySelectorAll("#quick .chip").forEach(function (c) {
        c.classList.toggle("on", c.getAttribute("data-multi") === "0");
      });
    }
    renderSource(data);
    renderFilters(data);
    syncFilterControls();
    renderStats();
    render();
    updatePlayUI();
    state.ready = true;
    focusThreadFromUrl();
    window.__RENDER_READY__ = true;
    document.documentElement.setAttribute("data-render-ready", "1");
  }

  function syncFilterControls() {
    var f = state.filters;
    document.getElementById("f-person").value = f.person || "";
    document.getElementById("f-place").value = f.place || "";
    document.getElementById("f-turns").value = String(f.minTurns || 0);
    document.getElementById("f-search").value = f.search || "";
    document.querySelectorAll("#quick .chip").forEach(function (c) {
      c.classList.toggle("on", (c.getAttribute("data-multi") === "1") === !!f.multiOnly);
    });
  }

  function focusThreadFromUrl() {
    var tid = new URLSearchParams(location.search).get("thread");
    if (!tid) return;
    var key = null;
    state.threads.some(function (t) {
      if (t.thread_id === tid) { key = threadKey(t); return true; }
      if (!t.thread_id && t.messages[0] && String(t.messages[0].seq) === tid) { key = threadKey(t); return true; }
      return false;
    });
    if (!key) { toast("URL 指定的线程不在当前数据里：" + tid); return; }
    state.expanded[key] = true;
    render();
    var card = document.querySelector('[data-thread="' + tid + '"]') ||
               document.querySelector('[data-key="' + key + '"]');
    if (card) {
      card.scrollIntoView({ block: "center" });
      card.classList.add("flash");
    }
  }

  function renderSource(data) {
    var s = data.source || {};
    var meta = s.meta_json || {};
    var q = function (id) { return document.getElementById(id); };
    q("src-run").textContent = s.run_jsonl || "未记录";
    q("src-run").title = s.run_jsonl || "";
    q("src-sha").textContent = shortSha(s.run_sha256);
    q("src-sha").title = s.run_sha256 || "";
    q("src-provider").textContent = meta.provider || s.llm_provider_in_log || "日志未记录";
    q("src-provider").title = meta.model || "";
    q("src-seed").textContent = fmtNum(meta.seed);
    q("src-events").textContent = fmtNum(s.events_total_in_log);
    q("src-msgs").textContent = fmtNum((data.stats || {}).messages);
    var note = q("src-note");
    if (meta.provider || s.llm_provider_in_log) {
      note.textContent = "· meta 已对齐";
      note.className = "ok";
    } else {
      note.textContent = "· 无 meta.json（provider 未声明）";
      note.className = "warn";
    }
    // 代码 sha 在 meta 里若存在则展示到 tooltip，不另造字段
    var codeSha = meta.code_sha || meta.sha || meta["sha"];
    if (codeSha) q("src-run").title = (s.run_jsonl || "") + "\ncode sha: " + codeSha;
  }

  function agentName(id) {
    var a = (state.data && state.data.agents) || {};
    var rec = a[id];
    if (!rec) return id || "（未记录）";
    return rec.name || id;
  }
  function agentShort(id) {
    var n = agentName(id);
    return n.replace(/^青溪镇[·・.]?/, "") || n;
  }
  function roleOf(id) {
    var a = (state.data && state.data.agents) || {};
    return (a[id] || {}).role || null;
  }
  var ROLE_CN = {
    farmer: "农户", craftsman: "工匠", cook: "厨子", healer: "医者", teacher: "教书先生",
    merchant: "商户", official: "差役", laborer: "帮工", scholar: "读书人", elder: "长者"
  };
  function placeName(id) {
    if (!id) return null;
    var p = (state.data && state.data.places) || {};
    return p[id] || id;
  }

  function avatarNode(id, small) {
    var d = el("div", { class: "avatar" + (small ? " sm" : ""), title: agentName(id) + (roleOf(id) ? "（" + (ROLE_CN[roleOf(id)] || roleOf(id)) + "）" : "") });
    d.style.backgroundImage = "url('assets/generated/characters/villager_" + spriteOf(id) + ".png')";
    return d;
  }

  // ---------------- 筛选 ----------------
  function renderFilters(data) {
    var persons = {};
    (data.agents ? Object.keys(data.agents) : []).forEach(function (p) { persons[p] = true; });
    (data.threads || []).forEach(function (t) { (t.participants || []).forEach(function (p) { persons[p] = true; }); });
    var ps = document.getElementById("f-person");
    ps.innerHTML = "";
    ps.appendChild(el("option", { value: "", text: "全部居民（" + Object.keys(persons).length + "）" }));
    Object.keys(persons).sort().forEach(function (p) {
      ps.appendChild(el("option", { value: p, text: agentShort(p) + "  " + p }));
    });

    var places = {};
    (data.threads || []).forEach(function (t) { (t.places || (t.place ? [t.place] : [])).forEach(function (p) { if (p) places[p] = true; }); });
    var pl = document.getElementById("f-place");
    pl.innerHTML = "";
    pl.appendChild(el("option", { value: "", text: "全部地点" }));
    Object.keys(places).sort().forEach(function (p) {
      pl.appendChild(el("option", { value: p, text: placeName(p) }));
    });
  }

  function threadPasses(t) {
    var f = state.filters;
    if (f.multiOnly && !(t.turns >= 2)) return false;
    if (f.minTurns && t.turns < f.minTurns) return false;
    if (f.person && (t.participants || []).indexOf(f.person) < 0) return false;
    if (f.place) {
      var places = t.places || (t.place ? [t.place] : []);
      if (places.indexOf(f.place) < 0) return false;
    }
    if (f.search) {
      var needle = f.search.toLowerCase();
      var hit = (t.messages || []).some(function (m) {
        return m.body && m.body.toLowerCase().indexOf(needle) >= 0;
      });
      if (!hit) return false;
    }
    return true;
  }

  function visibleCount(threadIndex) {
    // 该线程在回放游标之前已“发生”了几条消息
    var t = state.threads[threadIndex];
    var n = 0;
    for (var i = 0; i < state.flat.length && i < state.cursor; i++) {
      if (state.flat[i].t === threadIndex) n++;
    }
    // 线程内消息顺序可能不等于全局 seq 顺序（同线程跨 round 仍单调），用 seq 比较更稳
    var limit = state.cursor < state.flat.length ? (state.flat[Math.max(0, state.cursor - 1)] || {}).m : null;
    var cutoff = state.cursor >= state.flat.length ? Infinity : (limit ? limit.seq : Infinity);
    n = (t.messages || []).filter(function (m) { return (m.seq || 0) <= cutoff; }).length;
    return n;
  }

  function filteredThreads() {
    var out = [];
    state.threads.forEach(function (t, i) {
      if (!threadPasses(t)) return;
      if (state.cursor < state.flat.length && visibleCount(i) === 0) return;
      out.push(i);
    });
    return out;
  }

  // ---------------- 渲染对话流 ----------------
  function render() {
    var list = document.getElementById("thread-list");
    list.innerHTML = "";
    var notice = document.getElementById("stream-notice");
    notice.innerHTML = "";
    var st = state.data && state.data.stats || {};

    if (st.legacy_messages && !st.threaded_messages) {
      notice.appendChild(el("div", {
        class: "notice",
        text: "该日志为旧格式：MSG_* 里没有 thread_id/turn_index（D2 改造前）。"
            + "页面按「每条消息一条单发线程」显示，不做线程推断；「只看多轮」因此没有结果。"
            + "其余字段（人物/时间/地点/语境证据）照常呈现。"
      }));
    } else if (st.legacy_messages && st.threaded_messages) {
      notice.appendChild(el("div", {
        class: "notice",
        text: "该日志混合格式：" + st.threaded_messages + " 条带线程字段，" + st.legacy_messages
            + " 条为旧格式单发（已各自成条，标「旧格式」）。"
      }));
    }

    var idxs = filteredThreads();
    if (!state.data) return;
    if (!idxs.length) {
      showEmpty(
        state.threads.length ? "当前筛选下没有线程。" : "该日志里没有任何对话事件（MSG_DM / MSG_PUBLIC / MSG_GROUP）。",
        state.threads.length ? ["试着关掉「只看多轮」或清空人物/地点筛选。"]
                             : ["这可能是空世界日志（只有 AGENT_BORN / TURN_SEAL）。",
                                "换一份含对话的 run.jsonl 重新生成 threads.json 即可。"]
      );
      return;
    }
    document.getElementById("empty-box").hidden = true;

    idxs.forEach(function (ti) {
      list.appendChild(renderThread(ti));
    });

    // 未通过筛选的线程数提示
    var hidden = state.threads.length - idxs.length;
    if (hidden > 0) {
      list.appendChild(el("div", { class: "empty", text: "另有 " + hidden + " 条线程被当前筛选隐藏。" }));
    }
  }

  function renderThread(ti) {
    var t = state.threads[ti];
    var key = threadKey(t);
    var card = el("section", { class: "thread", "data-ti": String(ti), "data-key": key });

    // ---- head ----
    var avatars = el("div", { class: "avatars" });
    (t.participants || []).slice(0, 3).forEach(function (p) { avatars.appendChild(avatarNode(p)); });
    var names = el("div", { class: "names", text: (t.participants || []).map(agentShort).join("  ⇄  ") || "（参与者未记录）" });
    var metaBits = [];
    metaBits.push(CHANNEL_CN[t.channel] || t.channel || "渠道未记录");
    if (t.place) metaBits.push("📍 " + placeName(t.place));
    var first = t.messages[0] || {};
    var last = t.messages[t.messages.length - 1] || {};
    metaBits.push(timeLabel(first) + (t.messages.length > 1 && last.round !== first.round ? " → " + timeLabel(last) : ""));
    if (t.thread_id) metaBits.push(t.thread_id);
    var who = el("div", { class: "who" }, [names, el("div", { class: "meta", text: metaBits.join(" · ") })]);

    var tags = el("div", { class: "tags" });
    tags.appendChild(el("span", { class: "tag turns", text: t.turns + " 轮" }));
    if (t.multi_turn) tags.appendChild(el("span", { class: "tag multi", text: "多轮" }));
    if (t.legacy) tags.appendChild(el("span", { class: "tag legacy", text: "旧格式·单发" }));
    var shown = visibleCount(ti);
    if (shown < t.messages.length) tags.appendChild(el("span", { class: "tag live", text: "回放中 " + shown + "/" + t.messages.length }));
    var ctxBtn = el("button", {
      class: "ctxbtn", text: state.expanded[key] ? "收起语境 ▴" : "为什么这么聊 ▾",
      onclick: function () { state.expanded[key] = !state.expanded[key]; render(); }
    });
    tags.appendChild(ctxBtn);
    if (t.thread_id) {
      tags.appendChild(el("button", {
        class: "ctxbtn", text: "🔗 引用", title: "复制指向该线程的页面链接（可用于报告取证）",
        onclick: function (e) {
          e.stopPropagation();
          var u = new URL(location.href);
          u.searchParams.set("thread", t.thread_id);
          u.searchParams.set("still", "1");
          if (state.dataUrl) u.searchParams.set("data", state.dataUrl);
          try { navigator.clipboard.writeText(u.toString()); } catch (err) { /* ignore */ }
          toast("已复制线程链接：" + t.thread_id);
        }
      }));
    }

    card.appendChild(el("div", { class: "thread-head" }, [avatars, who, tags]));
    if (t.thread_id) card.setAttribute("data-thread", t.thread_id);

    // ---- messages ----
    var msgs = el("div", { class: "msgs" });
    var cutoff = cutoffSeq();
    var firstSpeaker = (t.messages[0] || {}).from || (t.participants || [])[0];
    t.messages.forEach(function (m, mi) {
      if ((m.seq || 0) > cutoff) return;
      var right = t.channel === "dm" && m.from && m.from !== firstSpeaker;
      var bubbleChildren = [];
      var speakerText = (m.turn_index != null ? "第 " + (m.turn_index + 1) + " 轮 · " : "")
        + (agentShort(m.from) || "（发送者未记录）");
      bubbleChildren.push(el("div", { class: "speaker", text: speakerText }));
      bubbleChildren.push(text(m.body != null ? m.body : "（正文未写入日志：body_ref=" + (m.body_ref || "null") + "）"));
      bubbleChildren.push(el("span", {
        class: "seq", text: "#" + (m.seq == null ? "?" : m.seq),
        title: "该条消息的事件 seq（可回指 run.jsonl）",
        onclick: function (e) {
          e.stopPropagation();
          var s = "#" + m.seq;
          try { navigator.clipboard.writeText(s); } catch (err) { /* 剪贴板不可用则忽略 */ }
          toast("已复制事件定位 " + s + "（msg_id=" + (m.msg_id || "未记录") + "）");
        }
      }));
      var bubble = el("div", { class: "bubble" }, bubbleChildren);
      var row = el("div", { class: "msg" + (right ? " right" : "") }, [
        avatarNode(m.from || "", true), bubble
      ]);
      msgs.appendChild(row);
    });
    var pending = t.messages.length - shown;
    if (pending > 0) {
      msgs.appendChild(el("div", { class: "msg pending" }, [
        el("div", { class: "bubble", text: "… 还有 " + pending + " 条未发生（回放中）" })
      ]));
    }
    card.appendChild(msgs);

    // ---- 语境面板 ----
    if (state.expanded[key]) card.appendChild(renderCtx(t, cutoff));

    if (shown < t.messages.length) card.classList.add("flash");
    return card;
  }

  function threadKey(t) { return t.thread_id || ("legacy:" + (t.messages[0] || {}).seq); }

  function cutoffSeq() {
    if (state.cursor >= state.flat.length) return Infinity;
    if (state.cursor <= 0) return -1;
    return state.flat[state.cursor - 1].m.seq;
  }

  function ctxRow(k, v) {
    return el("div", { class: "row" }, [el("span", { class: "k", text: k }), el("span", { class: "v", text: v })]);
  }

  function renderCtx(t, cutoff) {
    var panel = el("div", { class: "ctxpanel" });
    var shown = t.messages.filter(function (m) { return (m.seq || 0) <= cutoff; });
    var probe = shown[shown.length - 1] || t.messages[0] || {};
    var ctx = probe.context || {};

    // 1) 生成时快照（D2 payload.ctx）
    var snap = el("div", { class: "ctxcard" }, [el("h4", { text: "生成时语境快照（payload.ctx）" })]);
    var cs = ctx.ctx_snapshot;
    if (!cs) {
      snap.appendChild(el("div", { class: "none", text: "日志未记录（该条消息不含 payload.ctx）" }));
    } else {
      if (cs.relation != null) snap.appendChild(ctxRow("关系值", String(cs.relation)));
      if (cs.mood != null) snap.appendChild(ctxRow("情绪", String(cs.mood)));
      if (cs.topic) snap.appendChild(ctxRow("话题线", String(cs.topic)));
      if (cs.need && typeof cs.need === "object") {
        Object.keys(cs.need).forEach(function (k) {
          snap.appendChild(ctxRow("需求 · " + (NEED_CN[k] || k), String(cs.need[k])));
        });
      }
      if (!snap.querySelector(".row")) snap.appendChild(el("div", { class: "none", text: "快照里没有可显示键" }));
    }
    panel.appendChild(snap);

    // 2) 关系证据（真实 RELATION_CHANGE 事件）
    var rel = el("div", { class: "ctxcard" }, [el("h4", { text: "关系证据（RELATION_CHANGE，取本条之前最近一次）" })]);
    var rels = (ctx.relation || []);
    if (!rels.length) rel.appendChild(el("div", { class: "none", text: "日志未记录（本条之前没有该对人物的关系变更）" }));
    rels.slice(0, 6).forEach(function (r) {
      var pct = Math.max(0, Math.min(100, Number(r.after || 0)));
      rel.appendChild(ctxRow(
        agentShort(r.from) + "→" + agentShort(r.to) + " · " + (DIM_CN[r.dim] || r.dim),
        (r.before != null ? r.before + " → " : "") + (r.after != null ? r.after : "—") + "（" + (r.cause || "原因未记录") + "）"
      ));
      var bar = el("div", { class: "bar" }, [el("i", {})]);
      bar.firstChild.style.width = pct + "%";
      rel.appendChild(bar);
      rel.appendChild(el("div", { class: "src", text: "来源 seq #" + r.seq + " · round " + r.round }));
    });
    panel.appendChild(rel);

    // 3) 需求证据（真实 NEED_UPDATE）
    var need = el("div", { class: "ctxcard" }, [el("h4", { text: "当时需求（NEED_UPDATE，取本条之前最近一次）" })]);
    var needs = ctx.needs || {};
    var anyNeed = false;
    Object.keys(needs).forEach(function (aid) {
      var dims = needs[aid] || [];
      if (!dims.length) return;
      anyNeed = true;
      need.appendChild(el("div", { class: "src", text: agentShort(aid) }));
      dims.slice(0, 6).forEach(function (n) {
        need.appendChild(ctxRow(NEED_CN[n.dim] || n.dim,
          (n.before != null ? n.before + " → " : "") + (n.after != null ? n.after : "—")));
      });
    });
    if (!anyNeed) need.appendChild(el("div", { class: "none", text: "日志未记录（本条之前没有参与者的需求变更）" }));
    panel.appendChild(need);

    // 4) 共处 / 群组
    var occ = el("div", { class: "ctxcard" }, [el("h4", { text: "在场证据" })]);
    var e = ctx.encounter;
    if (e) {
      occ.appendChild(ctxRow("共处", agentShort(e.a) + " ⇄ " + agentShort(e.b)));
      if (e.place) occ.appendChild(ctxRow("地点", placeName(e.place)));
      if (e.duration_ticks != null) occ.appendChild(ctxRow("时长", e.duration_ticks + " tick"));
      occ.appendChild(el("div", { class: "src", text: "来源 seq #" + e.seq + " · round " + e.round }));
    } else {
      occ.appendChild(el("div", { class: "none", text: "日志未记录（本条之前没有 RELATION_ENCOUNTER）" }));
    }
    if (ctx.group) {
      occ.appendChild(ctxRow("群组", ctx.group.group_id));
      occ.appendChild(ctxRow("成员", (ctx.group.members || []).map(agentShort).join("、") || "未记录"));
      occ.appendChild(el("div", { class: "src", text: "来源 seq #" + ctx.group.seq }));
    }
    panel.appendChild(occ);

    // 5) 本条消息的溯源
    var prov = el("div", { class: "ctxcard" }, [el("h4", { text: "本条溯源" })]);
    prov.appendChild(ctxRow("事件 seq", "#" + (probe.seq == null ? "?" : probe.seq)));
    prov.appendChild(ctxRow("msg_id", probe.msg_id || "未记录"));
    prov.appendChild(ctxRow("round / day / slot",
      [probe.round, probe.day, probe.slot].map(function (x) { return x == null ? "—" : x; }).join(" / ")));
    prov.appendChild(ctxRow("reply_to", probe.reply_to || "未记录"));
    prov.appendChild(ctxRow("turn_index", probe.turn_index == null ? "未记录" : String(probe.turn_index)));
    if ((probe.refs || []).length) prov.appendChild(ctxRow("引用 refs", probe.refs.join(", ")));
    if ((probe.tag_hints || []).length) prov.appendChild(ctxRow("标签", probe.tag_hints.join(", ")));
    panel.appendChild(prov);
    return panel;
  }

  function showEmpty(title, lines) {
    var box = document.getElementById("empty-box");
    box.hidden = false;
    box.innerHTML = "";
    box.appendChild(el("div", { text: title, style: "color:#e7ecf3;font-weight:700;margin-bottom:8px" }));
    (lines || []).forEach(function (l) {
      box.appendChild(el("div", { class: "src", text: l }));
    });
  }

  // ---------------- 统计 / 回放 ----------------
  function renderStats() {
    var idxs = filteredThreads();
    var multi = idxs.filter(function (i) { return state.threads[i].turns >= 2; }).length;
    var msgs = 0, maxT = 0;
    idxs.forEach(function (i) {
      msgs += Math.min(visibleCount(i), state.threads[i].turns);
      maxT = Math.max(maxT, state.threads[i].turns);
    });
    document.getElementById("st-threads").textContent = idxs.length;
    document.getElementById("st-multi").textContent = multi;
    document.getElementById("st-msgs").textContent = msgs;
    document.getElementById("st-max").textContent = maxT;
    var st = (state.data && state.data.stats) || {};
    document.getElementById("st-format").textContent =
      st.legacy_messages && !st.threaded_messages ? "旧格式（无 thread_id）"
        : (st.threaded_messages ? "线程化" + (st.legacy_messages ? "（含旧格式 " + st.legacy_messages + "）" : "") : "—");
  }

  function updatePlayUI() {
    var total = state.flat.length;
    var cur = state.cursor;
    document.getElementById("scrub").max = String(total);
    document.getElementById("scrub").value = String(cur);
    document.getElementById("playcount").textContent = cur + " / " + total;
    var m = cur > 0 ? state.flat[cur - 1].m : null;
    document.getElementById("clock").textContent = m ? timeLabel(m) : "— 未开始 —";
    document.getElementById("btn-play").textContent = state.playing ? "⏸ 暂停" : "▶ 播放";
    document.getElementById("btn-play").classList.toggle("primary", !state.playing);
  }

  function setCursor(n, opts) {
    var total = state.flat.length;
    state.cursor = Math.max(0, Math.min(total, n));
    render();
    renderStats();
    updatePlayUI();
    if (!opts || opts.scroll !== false) scrollLatest();
  }

  function scrollLatest() {
    var stream = document.getElementById("stream");
    var cards = stream.querySelectorAll(".thread");
    if (!cards.length) return;
    // 找最后一个「本轮刚揭示」的线程卡片
    var last = cards[cards.length - 1];
    var top = last.offsetTop - stream.offsetTop;
    if (top < stream.scrollTop || top > stream.scrollTop + stream.clientHeight - 180) {
      last.scrollIntoView({ block: "nearest" });
    }
  }

  function tick() {
    if (!state.playing) return;
    if (state.cursor >= state.flat.length) { stopPlay(); return; }
    state.cursor += 1;
    var prev = state.cursor > 1 ? state.flat[state.cursor - 2] : null;
    var now = state.flat[state.cursor - 1];
    render();
    renderStats();
    updatePlayUI();
    scrollLatest();
    var sameThread = prev && now && prev.t === now.t;
    var delay = (sameThread ? 280 : 900) / state.speed;
    state.timer = setTimeout(tick, delay);
  }

  function startPlay() {
    if (state.cursor >= state.flat.length) state.cursor = 0;   // 已到末尾 → 从头回放
    state.playing = true;
    render(); renderStats(); updatePlayUI();
    clearTimeout(state.timer);
    state.timer = setTimeout(tick, 300);
  }
  function stopPlay() {
    state.playing = false;
    clearTimeout(state.timer);
    updatePlayUI();
  }

  var toastTimer = null;
  function toast(msg) {
    var t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove("show"); }, 2600);
  }

  // ---------------- 事件绑定 ----------------
  function bind() {
    document.querySelectorAll("#quick .chip").forEach(function (c) {
      c.addEventListener("click", function () {
        document.querySelectorAll("#quick .chip").forEach(function (x) { x.classList.remove("on"); });
        c.classList.add("on");
        state.filters.multiOnly = c.getAttribute("data-multi") === "1";
        if (state.filters.multiOnly) {
          state.filters.minTurns = Math.max(state.filters.minTurns, 2);
        } else if (state.filters.minTurns === 2) {
          // 关掉「只看多轮」时把自动抬到 2 的长度门槛放回去，否则切「全部」还是空的
          state.filters.minTurns = 0;
        }
        document.getElementById("f-turns").value = String(state.filters.minTurns);
        render(); renderStats();
      });
    });

    document.getElementById("f-person").addEventListener("change", function (e) {
      state.filters.person = e.target.value; render(); renderStats();
    });
    document.getElementById("f-place").addEventListener("change", function (e) {
      state.filters.place = e.target.value; render(); renderStats();
    });
    document.getElementById("f-turns").addEventListener("change", function (e) {
      state.filters.minTurns = Number(e.target.value) || 0; render(); renderStats();
    });
    document.getElementById("f-search").addEventListener("input", function (e) {
      state.filters.search = e.target.value.trim(); render(); renderStats();
    });

    document.querySelectorAll("#speed .chip").forEach(function (c) {
      c.addEventListener("click", function () {
        document.querySelectorAll("#speed .chip").forEach(function (x) { x.classList.remove("on"); });
        c.classList.add("on");
        state.speed = Number(c.getAttribute("data-speed")) || 1;
        if (state.playing) { clearTimeout(state.timer); state.timer = setTimeout(tick, 60); }
      });
    });

    document.getElementById("btn-play").addEventListener("click", function () {
      state.playing ? stopPlay() : startPlay();
    });
    document.getElementById("btn-prev").addEventListener("click", function () {
      stopPlay(); setCursor(state.cursor - 1);
    });
    document.getElementById("btn-next").addEventListener("click", function () {
      stopPlay(); setCursor(state.cursor + 1);
    });
    document.getElementById("btn-latest").addEventListener("click", function () {
      stopPlay(); setCursor(state.flat.length);
    });
    document.getElementById("scrub").addEventListener("input", function (e) {
      stopPlay(); setCursor(Number(e.target.value), { scroll: false });
    });

    document.addEventListener("keydown", function (e) {
      if (e.target && /input|select|textarea/i.test(e.target.tagName)) return;
      if (e.code === "Space") { e.preventDefault(); state.playing ? stopPlay() : startPlay(); }
      else if (e.code === "ArrowRight") { stopPlay(); setCursor(state.cursor + 1); }
      else if (e.code === "ArrowLeft") { stopPlay(); setCursor(state.cursor - 1); }
      else if (e.code === "End") { stopPlay(); setCursor(state.flat.length); }
      else if (e.code === "Home") { stopPlay(); setCursor(0); }
    });

    var fb = document.getElementById("btn-filters");
    if (fb) fb.addEventListener("click", function () {
      var sb = document.getElementById("sidebar");
      sb.classList.toggle("collapsed");
      fb.textContent = sb.classList.contains("collapsed") ? "筛选 ▾" : "筛选 ▴";
    });

    // 载入本地 threads.json（离线可用）
    document.getElementById("btn-load").addEventListener("click", function () {
      document.getElementById("file-input").click();
    });
    document.getElementById("file-input").addEventListener("change", function (e) {
      var f = e.target.files && e.target.files[0];
      if (!f) return;
      var r = new FileReader();
      r.onload = function () {
        try {
          var d = JSON.parse(String(r.result));
          if (!d.threads) throw new Error("缺少 threads 字段");
          stopPlay();
          state.dataUrl = null;      // 本地文件：链接里不写 data 参数
          prepare(d);
          document.getElementById("src-run").textContent = "本地文件: " + f.name;
          toast("已载入 " + f.name + "（" + d.threads.length + " 条线程）");
          startPlay();
        } catch (err) {
          toast("解析失败：" + err.message + "（需要 gen_threads.py 生成的 threads.json）");
        }
      };
      r.readAsText(f, "utf-8");
      e.target.value = "";
    });
  }

  // ---------------- 启动 ----------------
  async function main() {
    bind();
    // 窄屏默认收起筛选（内容优先），可用顶栏「筛选 ▾」展开
    if (window.matchMedia && window.matchMedia("(max-width: 760px)").matches) {
      document.getElementById("sidebar").classList.add("collapsed");
    }
    updatePlayUI();
    var d = await loadDefault();
    if (!d) return;
    // ?still=1 → 停在「全部已发生」的静态帧（供 shot.py 截图，避免截到回放中间态）
    var still = new URLSearchParams(location.search).get("still") === "1";
    if (still) document.body.classList.add("still");
    prepare(d);           // prepare 内置 cursor=全量，不会再触发第二次渲染（避免淡入动画截到半透明）
    if (still) return;
    // 默认：连续回放（沉浸看对话逐条浮现）；旧格式单发也能看
    startPlay();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", main);
  } else {
    main();
  }
})();
