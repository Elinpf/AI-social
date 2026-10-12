# T279 · 事件表现（治 #2 可感度）：最近事件走马条

## 一句话：治 #2 里的哪个缺口
**"运转的连续性看不出来"** —— 现有表现（toast / banner / 场所气泡 / worldFx）都只作用在**当前回合**且**转瞬即隐**；观者看到的是"某一刻闪了一下"，**看不到"一直在发生"**。
→ 本次加一条**最近事件走马条**：把**最近 5 轮**的 notable 事件（每轮取最高优先 1 条）**连续**呈现在左下角（末 4 条），**体积小、半透明、不遮场景** → 补上"持续在运转"的**可感度**，而非"顺手的样式优化"。

## 实现（只动 `frontend/`）
- `index.html` 加 `#evticker`；`styles/app.css` 加 `.evticker`（左下、12px、半透明、`opacity .92/.5` 分层）。
- `src/main.js`：`renderEvticker(rp, rd)` —— 取 `[rd-5, rd]` 每轮最高优先 notable 事件、末 4 条渲染；**随 `(log, round)` 确定性派生**（不依赖运行内存）。
- **可回退**：`?ticker=0`（body.no-ticker 隐藏）用于"改前"对照。
- 触碰面：仅展示层；未动 `?log=`/`?rounds=`/`/__gitstamp`（T275 盲测台语义不变）。

## 证据
- **改前/改后像素差异率**（round 59 · still · view=default · 1500×950 · `run_c_n20.play.jsonl`）：
  `T279-ticker-before.png`（`?ticker=0`）↔ `T279-ticker-after.png` → **差异 mean=0.514 / max=211 / 占比 2.03%**（小而克制，不喧宾夺主）。
- **时序片段**（走马条随回合更新）：`T279-ticker-clip.gif`（30 帧）。
- `make ci` → **PASS**（smoke + gate_render + R9 + D 段）。

## 附带
抓图时**非空白门禁真的拦下了一次白帧**（round 59 改后图，单色占比 56% → `SHOT FAIL`）——重拍后通过。→ 该门禁在真实取证中已起效。
