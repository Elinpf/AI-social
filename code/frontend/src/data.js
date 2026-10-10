/* data.js — 只读数据加载：config（places/topology）与事件日志（JSONL）。
 * 纪律：只读；不写世界状态、不参与判定。所有数据来自 config/日志，保证可复现。
 */
(function (global) {
  "use strict";

  async function loadJSON(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`加载失败 ${url}: HTTP ${res.status}`);
    return res.json();
  }

  // 解析 JSONL 文本 → 记录数组（按 seq 稳定排序）。容忍尾部空行/空白。
  function parseJSONL(text) {
    const out = [];
    const lines = text.split(/\r?\n/);
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      let obj;
      try {
        obj = JSON.parse(line);
      } catch (e) {
        throw new Error(`第 ${i + 1} 行 JSON 解析失败: ${e.message}`);
      }
      if (obj && obj.type) out.push(obj);
    }
    // 事件日志以 seq 为全序；缺失时退化为稳定出现序
    out.sort((a, b) => {
      const sa = (a.seq == null) ? Infinity : a.seq;
      const sb = (b.seq == null) ? Infinity : b.seq;
      if (sa !== sb) return sa - sb;
      return (a.round || 0) - (b.round || 0);
    });
    return out;
  }

  async function loadText(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`加载失败 ${url}: HTTP ${res.status}`);
    return res.text();
  }

  global.HITTData = { loadJSON, parseJSONL, loadText };
})(window);
