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
    filters: { multiOnly: true, person: "", place: "", minTurns: 0, search: "", sort: "time", leak: false, worldOnly: false },
    speed: 1,
    playing: false,
    cursor: 0,
    timer: null,
    expanded: {},       // thread_id|legacy-seq -> bool
    ready: false,
    view: "chat",
    cellFocus: null      // {day, slot} —— 时间轴点选的单元格
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
    var q = new URLSearchParams(location.search);
    var explicit = q.get("data");
    if (explicit) {
      // 显式指定数据源时**绝不回退**到内置样例（否则「假可用」：看着有数据，其实读的是别的文件）
      try {
        var d0 = await fetchJSON(explicit);
        state.dataUrl = explicit;
        return d0;
      } catch (e) {
        showEmpty("数据源加载失败：" + explicit, [
          "错误：" + e.message,
          "页面已停止加载，**不会**回退到内置样例（避免伪装成可用）。",
          "检查路径是否正确、是否由 gen_threads.py 生成；或改用 --log 重新生成。"
        ]);
        return null;
      }
    }
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
    if (q.get("sort") === "turns" || q.get("sort") === "time") state.filters.sort = q.get("sort");
    if (q.get("leak") === "1") state.filters.leak = true;
    if (q.get("world") === "1") state.filters.worldOnly = true;

    var st = data.stats || {};
    // 多轮线程很少时（<=24），默认「按轮次排序」：让人一眼看到最长的几条，而不是自己筛
    var multN = (data.stats || {}).multi_turn_threads || 0;
    if (!q.get("sort") && multN > 0 && multN <= 24) state.filters.sort = "turns";

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
    renderLifeline();
    renderRhythmPanel();
    renderSpreadPanel();
    renderView(state.view);
    render();
    updatePlayUI();
    state.ready = true;
    // ?view=rhythm|spread|chat（截图/引用时直接落到指定视图，避免只能靠点）
    var vq = q.get("view");
    if (vq && ["chat", "rhythm", "spread"].indexOf(vq) >= 0) setView(vq);
    focusThreadFromUrl();
    window.__RENDER_READY__ = true;
    document.documentElement.setAttribute("data-render-ready", "1");
  }

  // ---------------- 视图：对话流 / 节律·串门 / 闲话传播 ----------------
  var SLOT_ORDER = ["morning", "afternoon", "evening", "night"];

  function setView(v) {
    state.view = v;
    document.querySelectorAll(".vtab").forEach(function (b) {
      b.classList.toggle("on", b.getAttribute("data-view") === v);
    });
    renderView(v);
  }

  function renderView(v) {
    var hint = document.getElementById("viewhint");
    document.getElementById("chatview").hidden = v !== "chat";
    document.getElementById("panel-rhythm").hidden = v !== "rhythm";
    document.getElementById("panel-spread").hidden = v !== "spread";
    document.getElementById("lifeline").hidden = v === "spread";
    if (v === "chat") hint.textContent = "点时间轴任一格 = 跳到那个时段的消息";
    else if (v === "rhythm") hint.textContent = "每个数字都来自日志的 day/slot 与 PLACE_MOVE";
    else hint.textContent = "转述链来自 msg.refs；「同句复现」为脚本派生口径";
  }

  // ---- 一天的时间轴（每个格子 = 一天里的一个时段）----
  function renderLifeline() {
    var host = document.getElementById("lifeline");
    host.innerHTML = "";
    if (!state.data) return;
    var cells = state.data.rhythm || [];
    if (!cells.length) {
      host.appendChild(el("div", { class: "empty", text: "日志未记录 day/slot（无法画时间轴）。" }));
      return;
    }
    var byDay = {};
    cells.forEach(function (c) {
      var k = c.day == null ? "?" : String(c.day);
      (byDay[k] = byDay[k] || []).push(c);
    });
    var days = Object.keys(byDay).sort(function (a, b) {
      if (a === "?") return 1; if (b === "?") return -1; return Number(a) - Number(b);
    });
    var maxMsgs = 1;
    cells.forEach(function (c) { maxMsgs = Math.max(maxMsgs, c.messages || 0); });

    days.forEach(function (d) {
      var row = el("div", { class: "dayline" });
      row.appendChild(el("div", { class: "daylabel", text: d === "?" ? "日期未记录" : "第 " + (Number(d) + 1) + " 天" }));
      SLOT_ORDER.forEach(function (slot) {
        var c = (byDay[d] || []).filter(function (x) { return x.slot === slot; })[0];
        var cell = el("div", { class: "slotcell" });
        if (c) {
          var pct = Math.round(((c.messages || 0) / maxMsgs) * 100);
          cell.style.background = "linear-gradient(0deg, rgba(92,200,255," + (0.05 + pct / 400) + "), rgba(27,35,47,0.5))";
          cell.appendChild(el("div", { class: "sl", text: SLOT_CN[slot] || slot }));
          var sv = el("div", { class: "sv" });
          sv.appendChild(text("💬 " + (c.messages || 0)));
          if (c.moves) {
            sv.appendChild(text("  "));
            sv.appendChild(el("span", { class: "mv", text: "🚶 " + c.moves }));
          }
          cell.appendChild(sv);
          var bars = el("div", { class: "bars" });
          [["dm", "#5cc8ff"], ["public", "#7ee0a8"], ["group", "#ffcf5c"]].forEach(function (p) {
            var v = c[p[0]] || 0;
            if (!v) return;
            var i = el("i", {});
            i.style.width = Math.max(4, Math.round((v / Math.max(1, c.messages)) * 100)) + "%";
            i.style.background = p[1];
            bars.appendChild(i);
          });
          bars.title = "私聊 " + (c.dm || 0) + " · 公开 " + (c.public || 0) + " · 群聊 " + (c.group || 0);
          cell.appendChild(bars);
          cell.addEventListener("click", function () { focusCell(c.day, slot); });
        } else {
          cell.appendChild(el("div", { class: "sl", text: SLOT_CN[slot] || slot }));
          cell.appendChild(el("div", { class: "sv", text: "—" }));
          cell.style.opacity = "0.45";
        }
        if (state.cellFocus && String(state.cellFocus.day) === d && state.cellFocus.slot === slot) {
          cell.classList.add("active");
        }
        row.appendChild(cell);
      });
      host.appendChild(row);
    });
    host.appendChild(el("div", {
      class: "src", style: "font-size:11px;color:#66707d",
      text: "读完：每一格 = 日志里 day+slot 的对话条数与走动次数（PLACE_MOVE）；色条 = 私聊/公开/群聊占比。"
    }));
  }

  function focusCell(day, slot) {
    state.cellFocus = { day: day, slot: slot };
    setView("chat");
    renderLifeline();
    render();
    var cards = document.querySelectorAll("#thread-list .thread");
    var hit = null;
    for (var i = 0; i < cards.length; i++) {
      if (cards[i].getAttribute("data-day") === String(day) && cards[i].getAttribute("data-slot") === slot) {
        hit = cards[i]; break;
      }
    }
    if (hit) { hit.scrollIntoView({ block: "center" }); hit.classList.add("flash"); }
    else toast("该时段（第 " + (Number(day) + 1) + " 天 " + (SLOT_CN[slot] || slot) + "）当前筛选下没有对话");
  }

  // ---- 节律 · 串门面板 ----
  function renderRhythmPanel() {
    var host = document.getElementById("panel-rhythm");
    host.innerHTML = "";
    if (!state.data) return;
    var rhythm = state.data.rhythm || [];
    var travel = state.data.travel || [];
    var cards = el("div", { class: "pcards" });

    // 1) 一天里的说话节律（按时段汇总）
    var slotTotals = {};
    rhythm.forEach(function (c) {
      var k = c.slot || "?";
      slotTotals[k] = (slotTotals[k] || 0) + (c.messages || 0);
    });
    var total = Object.keys(slotTotals).reduce(function (a, k) { return a + slotTotals[k]; }, 0);
    var c1 = el("div", { class: "pcard" }, [el("h3", { text: "一天里什么时候在说话" })]);
    c1.appendChild(el("div", {
      class: "sub",
      text: "分子 = 该时段的 MSG_* 条数，分母 = 全部 " + total + " 条。按日志 day/slot 字段分组，不做时间外推。"
    }));
    var bars = el("div", { class: "hourbars" });
    var labels = el("div", { class: "hourlabels" });
    SLOT_ORDER.forEach(function (slot) {
      var v = slotTotals[slot] || 0;
      var hb = el("div", { class: "hb" });
      hb.style.height = Math.max(2, Math.round((v / Math.max(1, total)) * 100)) + "%";
      hb.title = (SLOT_CN[slot] || slot) + "：" + v + " 条（" +
        (total ? Math.round(v / total * 100) : 0) + "%）";
      bars.appendChild(hb);
      labels.appendChild(el("span", { text: (SLOT_CN[slot] || slot) + " " + v }));
    });
    c1.appendChild(bars);
    c1.appendChild(labels);
    cards.appendChild(c1);

    // 2) 谁在串门（PLACE_MOVE 轨迹，原样搬运）—— 宽卡最后渲染，先占位
    // placeholder-swap

    var c2 = el("div", { class: "pcard wide" }, [el("h3", { text: "谁在串门（当天场所轨迹）" })]);
    c2.appendChild(el("div", {
      class: "sub",
      text: "每个箭头 = 一条 PLACE_MOVE（from_place → to_place），悬停看 seq 与时段。按「人 · 天」分组，按走动次数排序，最多 10 条。"
    }));
    if (!travel.length) {
      c2.appendChild(el("div", { class: "none", text: "日志未记录 PLACE_MOVE（该日志没有走动，或派生时被 --no-keep-moves 关闭）。" }));
    } else {
      var sorted = travel.slice().sort(function (a, b) { return b.hops.length - a.hops.length; }).slice(0, 10);
      sorted.forEach(function (tr) {
        var row = el("div", { class: "trail" });
        row.appendChild(avatarNode(tr.agent, true));
        var who = el("span", { class: "tname" }, [
          text(agentShort(tr.agent)),
          el("b", { class: "hopn", text: " " + tr.hops.length + " 次" })
        ]);
        row.appendChild(who);
        row.appendChild(el("span", { class: "tday", text: "第 " + (Number(tr.day) + 1) + " 天" }));
        var flow = el("span", { class: "flow" });
        if (tr.hops[0] && tr.hops[0].from) {
          flow.appendChild(el("span", { class: "pl", text: placeName(tr.hops[0].from) }));
          flow.appendChild(el("span", { class: "arr", text: "→" }));
        }
        tr.hops.forEach(function (h, i) {
          if (i > 0) flow.appendChild(el("span", { class: "arr", text: "→" }));
          var chip = el("span", { class: "pl", text: placeName(h.to) });
          chip.title = "#" + h.seq + " · " + (SLOT_CN[h.slot] || h.slot || "");
          flow.appendChild(chip);
        });
        row.appendChild(flow);
        c2.appendChild(row);
      });
    }
    // 3) 对话发生地（place 字段）
    var placeCount = {};
    (state.data.threads || []).forEach(function (t) {
      t.messages.forEach(function (m) {
        if (!m.place) return;
        placeCount[m.place] = (placeCount[m.place] || 0) + 1;
      });
    });
    var pk = Object.keys(placeCount).sort(function (a, b) { return placeCount[b] - placeCount[a]; });
    var maxP = pk.length ? placeCount[pk[0]] : 1;
    var c3 = el("div", { class: "pcard" }, [el("h3", { text: "话都发生在哪儿" })]);
    c3.appendChild(el("div", { class: "sub", text: "分子 = 该地点发生对话条数；只统计日志里带 place 的消息（公开广播无地点）。" }));
    if (!pk.length) c3.appendChild(el("div", { class: "none", text: "日志未记录对话地点。" }));
    pk.slice(0, 8).forEach(function (p) {
      var line = el("div", { class: "row" }, [
        el("span", { class: "k", text: placeName(p) }),
        el("span", { class: "v", text: placeCount[p] + " 条" })
      ]);
      c3.appendChild(line);
      var b = el("div", { class: "bar" }, [el("i", {})]);
      b.firstChild.style.width = Math.round(placeCount[p] / maxP * 100) + "%";
      c3.appendChild(b);
    });
    cards.appendChild(c3);
    cards.appendChild(c2);
    host.appendChild(cards);
  }

  // ---- 闲话怎么传开 ----
  function renderSpreadPanel() {
    var host = document.getElementById("panel-spread");
    host.innerHTML = "";
    if (!state.data) return;
    var sp = state.data.spread || {};
    var cards = el("div", { class: "pcards" });

    // 1) 转述链（日志真源 refs）
    var c1 = el("div", { class: "pcard" }, [el("h3", { text: "转述链（msg.refs，日志真源）" })]);
    var edges = sp.ref_edges || [];
    c1.appendChild(el("div", {
      class: "sub",
      text: "口径：B 的 refs 指向 A 的 msg_id ⇒ A → B 一条转述边（分子 = 成功匹配到日志里消息的边，分母 = 全部 refs）。"
    }));
    if (!edges.length) {
      c1.appendChild(el("div", {
        class: "none",
        text: "本批日志里 refs 全为空（没有一条消息引用别的消息），所以「谁把话传给谁」在真源上没有记录 —— 这里显示空态，不用相似度硬凑。"
      }));
      c1.appendChild(el("div", {
        class: "src",
        text: "统计：" + (state.data.stats || {}).ref_edges + " 条可匹配转述边 / " + (state.data.stats || {}).messages + " 条消息"
      }));
    } else {
      edges.slice(0, 20).forEach(function (e) {
        c1.appendChild(el("div", {
          class: "echo",
          text: agentShort(e.orig_by) + " #" + e.from_seq + " → " + agentShort(e.by) + " #" + e.to_seq
        }));
      });
    }
    cards.appendChild(c1);

    // 2) 同句复现（脚本派生，显式标注）
    var c2 = el("div", { class: "pcard" }, [el("h3", { text: "同一句话被第二个人说出（派生口径）" })]);
    c2.appendChild(el("div", { class: "sub", text: sp.echo_note || "" }));
    var echoes = sp.echoes || [];
    if (!echoes.length) {
      c2.appendChild(el("div", { class: "none", text: "本批日志没有「去标点后逐字相同、且说话人不同」的消息对（说明没人原样复述别人的话）。" }));
    } else {
      echoes.slice(0, 10).forEach(function (g) {
        var box = el("div", { class: "echo" });
        box.appendChild(el("div", { class: "t", text: "「" + g.text + "」" }));
        box.appendChild(el("div", {
          class: "m",
          text: "说话人：" + g.by.map(agentShort).join(" / ") + " · seq #" + g.seqs.join(", #") +
                (g.places.length ? " · 地点 " + g.places.map(placeName).join("/") : "")
        }));
        c2.appendChild(box);
      });
    }
    cards.appendChild(c2);
    host.appendChild(cards);
  }

  function syncFilterControls() {
    var f = state.filters;
    document.getElementById("f-person").value = f.person || "";
    document.getElementById("f-place").value = f.place || "";
    document.getElementById("f-turns").value = String(f.minTurns || 0);
    document.getElementById("f-search").value = f.search || "";
    document.getElementById("f-sort").value = f.sort || "time";
    var cl = document.getElementById("chip-leak");
    if (cl) cl.classList.toggle("on", !!f.leak);
    var cw = document.getElementById("chip-world");
    if (cw) cw.classList.toggle("on", !!f.worldOnly);
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
    q("src-run").textContent = s.run_label || "未记录";
    q("src-run").title = (s.run_label || "") + "（完整的跑批目录路径留在跑批目录自身的 meta.json）";
    q("src-sha").textContent = shortSha(s.run_sha256);
    q("src-sha").title = s.run_sha256 || "";
    q("src-provider").textContent = meta.provider || s.llm_provider_in_log || "日志未记录";
    q("src-provider").title = meta.model || "";
    q("src-seed").textContent = fmtNum(meta.seed);
    q("src-events").textContent = fmtNum(s.events_total_in_log);
    q("src-msgs").textContent = fmtNum((data.stats || {}).messages);
    var sch = data.thread_schema || null;
    if (!sch) {
      var st0 = data.stats || {};
      sch = (st0.threaded_messages && st0.legacy_messages) ? "mixed"
          : st0.threaded_messages ? "explicit" : (st0.legacy_messages ? "legacy" : "none");
    }
    q("src-schema").textContent = ({ explicit: "explicit（多轮线程）", legacy: "legacy（旧格式单发）",
                                     mixed: "mixed（新旧混合）", none: "none（无对话）" })[sch] || sch;
    q("src-schema").title = "thread_schema：" + sch + "（决定『只看多轮』是否会有结果）";
    var note = q("src-note");
    if (meta.provider || s.llm_provider_in_log) {
      note.textContent = "· meta 已对齐";
      note.className = "ok";
    } else {
      note.textContent = "· 无 meta.json（provider 未声明）";
      note.className = "warn";
    }
    // 代码 sha 在 meta 里若存在则展示到 tooltip，不另造字段
    var codeSha = meta.code_sha || meta.sha || meta.commit;
    if (codeSha) q("src-run").title = (s.run_label || "") + "\ncode sha: " + codeSha;
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

    // D8：只有数据里真的出现 world_ctx 时才显示「只看世界事件」开关（旧数据集不受影响）
    var cw = document.getElementById("chip-world");
    if (cw) cw.hidden = !(data.threads || []).some(threadHasWorld);
  }

  // D8：payload.world_ctx（世界事件上下文）是否存在。只读字段，不改既有视图。
  function msgHasWorld(m) { return !!(m && m.world_ctx); }
  function threadHasWorld(t) { return (t.messages || []).some(msgHasWorld); }

  // 派生口径（不是日志字段）：该条消息 payload.ctx.topic 的原字符串出现在正文里 ⇒ 泄漏。
  function isLeak(m) {
    var topic = (m.ctx || {}).topic;
    return !!(topic && m.body && String(m.body).indexOf(String(topic)) >= 0);
  }
  function threadLeakCount(t) {
    var n = 0;
    (t.messages || []).forEach(function (m) { if (isLeak(m)) n++; });
    return n;
  }

  function threadPasses(t) {
    if (state.filters.leak && threadLeakCount(t) === 0) return false;
    if (state.filters.worldOnly && !threadHasWorld(t)) return false;
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
    if (state.filters.sort === "turns") {
      out.sort(function (x, y) {
        var a = state.threads[x], b = state.threads[y];
        if (b.turns !== a.turns) return b.turns - a.turns;              // 轮次多的在前
        var ar = a.start_round == null ? 1e9 : a.start_round;
        var br = b.start_round == null ? 1e9 : b.start_round;
        if (ar !== br) return ar - br;
        return ((a.messages[0] || {}).seq || 0) - ((b.messages[0] || {}).seq || 0);
      });
    }
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
    if (state.filters.leak) {
      var leakTotal = 0;
      state.threads.forEach(function (t) { leakTotal += threadLeakCount(t); });
      notice.appendChild(el("div", {
        class: "notice",
        text: "⚠ 已开启「只看 token 泄漏」（派生筛选）：判定 = 该条消息 ctx.topic 的原字符串出现在正文里。"
            + "本数据集共 " + leakTotal + " / " + ((state.data.stats || {}).messages || 0) + " 条命中。"
            + "这是脚本判定的措辞问题，不是日志里的标记位。"
      }));
    }
    if (state.filters.sort === "turns" && idxs.length > 1) {
      var top = state.threads[idxs[0]];
      notice.appendChild(el("div", {
        class: "notice", style: "border-color:rgba(92,200,255,0.4);background:rgba(92,200,255,0.08);color:#b9e6ff",
        text: "已按「轮次」排序：先看最长的线程（当前最长 " + top.turns + " 条"
            + (threadDistinctTurns(top) ? " / " + threadDistinctTurns(top) + " 轮" : "") + "，"
            + (top.participants || []).map(agentShort).join(" ⇄ ") + "）。想看时间顺序请在左侧「排序」切换。"
      }));
    }
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
    publishVerifiableCounts();
  }

  // 把「页面上真的渲染了多少条消息」暴露成机器可读的核验口：
  //   document.documentElement.dataset.msgCount   +  window.__DIALOGUE__
  // 核验方可以断言 rendered == data.stats.messages（在 ?still=1&multi=0 的全量状态下）。
  function publishVerifiableCounts() {
    var rows = document.querySelectorAll("#thread-list .msg[data-seq]");
    var rendered = [];
    for (var i = 0; i < rows.length; i++) {
      rendered.push({
        seq: Number(rows[i].getAttribute("data-seq")),
        msgId: rows[i].getAttribute("data-msg-id") || null,
        speaker: rows[i].getAttribute("data-speaker") || null,
        thread: rows[i].getAttribute("data-thread") || null
      });
    }
    document.documentElement.setAttribute("data-msg-count", String(rendered.length));
    document.documentElement.setAttribute("data-format", ((state.data && state.data.stats) || {}).legacy_messages
      && !((state.data && state.data.stats) || {}).threaded_messages ? "legacy" : "threaded");
    window.__DIALOGUE__ = {
      schema: (state.data && state.data.schema) || null,
      threadSchema: (state.data && state.data.thread_schema) || null,
      source: (state.data && state.data.source) || null,
      stats: (state.data && state.data.stats) || null,
      filters: JSON.parse(JSON.stringify(state.filters)),
      cursor: state.cursor,
      total: state.flat.length,
      rendered: rendered,
      view: state.view
    };
  }

  function renderThread(ti) {
    var t = state.threads[ti];
    var key = threadKey(t);
    var card = el("section", {
      class: "thread", "data-ti": String(ti), "data-key": key,
      "data-day": String((t.messages[0] || {}).day),
      "data-slot": (t.messages[0] || {}).slot || ""
    });

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
    var dt = threadDistinctTurns(t);
    tags.appendChild(el("span", {
      class: "tag turns",
      text: dt ? (t.turns + " 条 / " + dt + " 轮") : (t.turns + " 轮"),
      title: dt ? ("条 = 线程内消息数；轮 = turn_index 去重后的回合数（日志字段直接去重）")
                : "旧格式无 turn_index：只能按消息条数计"
    }));
    if (t.multi_turn) tags.appendChild(el("span", { class: "tag multi", text: "多轮" }));
    if (t.legacy) tags.appendChild(el("span", { class: "tag legacy", text: "旧格式·单发" }));
    if (state.filters.leak) {
      tags.appendChild(el("span", { class: "tag legacy", text: "泄漏 " + threadLeakCount(t) + " 条" }));
    }
    // turn_index 重复 = 同一轮有多人先后发言（日志事实，不是前端推断）：显式标出来
    var dupTurns = threadDupTurns(t);
    if (dupTurns.groups > 0) {
      tags.appendChild(el("span", {
        class: "tag",
        text: "turn_index 重复 " + dupTurns.groups + " 组 / " + dupTurns.extra + " 条",
        title: "同一 turn_index 下有多条消息（例如都回复同一条上轮消息）；页面按日志原样显示，不合并、不重排"
      }));
    }
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
      if (state.filters.leak && !isLeak(m)) return;
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
      if (msgHasWorld(m)) {
        var wc = m.world_ctx || {};
        bubbleChildren.push(el("span", {
          class: "tag", text: "世界事件",
          title: "world_ctx：v=" + (wc.v || "?") + " · refs=" + JSON.stringify(wc.refs || [])
               + " · kinds=" + JSON.stringify(wc.kinds || []) + " · prompted=" + (wc.prompted === true)
        }));
      }
      var bubble = el("div", {
        class: "bubble",
        title: "seq #" + m.seq + " · msg_id=" + (m.msg_id || "未记录")
             + " · turn_index=" + (m.turn_index == null ? "未记录" : m.turn_index)
             + " · reply_to=" + (m.reply_to || "null")
      }, bubbleChildren);
      var row = el("div", {
        class: "msg" + (right ? " right" : ""),
        "data-seq": String(m.seq == null ? "" : m.seq),
        "data-msg-id": m.msg_id || "",
        "data-speaker": m.from || "",
        "data-thread": t.thread_id || ("legacy:" + ((t.messages[0] || {}).seq))
      }, [avatarNode(m.from || "", true), bubble]);
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

  // 「轮」有两种口径，页面必须分开写，否则读者会把「18 条消息」误读成「18 个回合」：
  //   turns        = 线程内消息条数（统计单位）
  //   distinctTurns= turn_index 去重后的回合数（日志字段直接去重，不推断）
  function threadDistinctTurns(t) {
    var set = {};
    (t.messages || []).forEach(function (m) { if (m.turn_index != null) set[m.turn_index] = 1; });
    var k = Object.keys(set).length;
    return k || null;
  }

  function threadDupTurns(t) {
    var byTurn = {};
    (t.messages || []).forEach(function (m) {
      var k = m.turn_index;
      if (k == null) return;
      (byTurn[k] = byTurn[k] || []).push(m);
    });
    var groups = 0, extra = 0;
    Object.keys(byTurn).forEach(function (k) {
      if (byTurn[k].length > 1) { groups++; extra += byTurn[k].length - 1; }
    });
    return { groups: groups, extra: extra };
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
    var chipWorld = document.getElementById("chip-world");
    if (chipWorld) chipWorld.addEventListener("click", function () {
      state.filters.worldOnly = !state.filters.worldOnly;
      chipWorld.classList.toggle("on", state.filters.worldOnly);
      if (state.filters.worldOnly) { document.getElementById("empty-box").hidden = true; }
      render(); renderStats();
    });
    var chipLeak = document.getElementById("chip-leak");
    if (chipLeak) chipLeak.addEventListener("click", function () {
      state.filters.leak = !state.filters.leak;
      chipLeak.classList.toggle("on", state.filters.leak);
      if (state.filters.leak) { document.getElementById("empty-box").hidden = true; }
      render(); renderStats();
    });
    document.getElementById("f-sort").addEventListener("change", function (e) {
      state.filters.sort = e.target.value; render(); renderStats();
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

    document.querySelectorAll(".vtab").forEach(function (b) {
      b.addEventListener("click", function () { setView(b.getAttribute("data-view")); });
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
