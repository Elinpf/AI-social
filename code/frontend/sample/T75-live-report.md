# T75 · 「实时跟随」模式：边跑边看小镇

> 只读 · 不改 engine/config · 确定性不受影响（live 日志仍可 `engine verify`）。

## 1. 现状澄清

前端本就**只读确定性日志**；点「播放」时已逐回合**平滑展开**（移动/活动/气泡都动），
但读的是**已存在的日志**。T75 增加 **live/跟随**：看**正在运行**的小镇。

## 2. 运行器（真内核、节流、离线）

`frontend/tools/live_run.py`：用 `orchestration.build_world`（真内核 + life 层，含 econ/lifecycle hook）
逐回合 `engine.run_round(r)` 推进，**每回合把新增事件追加**到 `sample/live/live.jsonl`，
并更新 `sample/live/latest_state.json`。**零网络**（默认离线 MockProvider）。

```bash
cd code
python frontend/tools/live_run.py --n 6 --rounds 300 --throttle 1.2
# 参数：--n/--rounds/--seed/--throttle(秒/回合)/--out-dir(默认 frontend/sample/live)
```

## 3. 前端跟随

`?live=sample/live/live.jsonl&follow=1`
- **~600ms 轮询**，发现新回合则重建 `Replay` 并**平滑推进到最新**；
- 顶栏 **● LIVE 徽标**（红、脉动）+ **round/事件计数** + **「⏸ 暂停跟随 / ▶ 跟随最新」**；
- 手动步进/拖滑杆自动**暂停跟随**（可回看历史）。

## 4. 实证（边跑边看）

同一会话内，运行器持续推进、页面跟随前进：

| 时点 | `latest_state.json` round | 事件数 |
|---|---|---|
| 开始后 ~3s | 2 | 318 |
| 截图 A 之后 | 28 | 4,649 |
| 截图 B 之后 | 54 | 8,988 |

- 跟随截图：`frontend/sample/live_follow_a.png`（此时页内 LIVE 显示 round 12 · 2,587 事件）、
  `frontend/sample/live_follow_b.png`（更靠后的回合）。
- **确定性**：`python -m engine verify --log frontend/sample/live/live.jsonl` → **PASS**（两次重放哈希相等）。

## 5. 回放 URL

- 实时跟随：`http://<LAN-IP>:8848/?live=sample/live/live.jsonl&follow=1`
  （先在本机跑 `live_run.py` 生成/续写 `sample/live/live.jsonl`）
- 暂停回看：点「⏸ 暂停跟随」或用播放条步进。

## 6. 约束与回归

- 只读、不改 `engine/config`、不引入 React/Convex；live 日志可 `verify`。
- `smoke_test.js` 全绿（`[D]` 段含 live_run/跟随断言）；`0.0.0.0:8848` 常驻。
