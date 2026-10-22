# R18 截图证据（修前可视化基线）

⚠️ **三重标注（必读，缺一条即为引用错误）**

1. **图源**：`v2/evidence/run_a5_real_n16r42_seed42`（**master `46e43808f28a891c26234703a48440bd0ceb9d4a` 时代**产出，17:44 收批；日志 sha256 前缀 `aa6edc35`，取 `threads.json.source.run_sha256`）。
2. **非本轮修后行为**：本轮**没有起新跑批**（纪律：串行 / 禁跑批），因此这些图**不能**代表 `feat/life-memory-fix-20261022` 的修后行为。
3. **仅作修前对照**：用途是让读者看到被修的那条链路所依附的世界长什么样（n16×42 的对话/节律/闲话视图），不是效果证据。

## 文件

| 文件 | 视图 | 尺寸 |
|---|---|---|
| `run_a5_real_n16r42_seed42-chat-aa6edc35.png` | 对话流（全量口径） | 1400×900 |
| `run_a5_real_n16r42_seed42-rhythm-aa6edc35.png` | 节律·串门 | 1300×1050 |
| `run_a5_real_n16r42_seed42-spread-aa6edc35.png` | 闲话怎么传开 | 1300×900 |
| `run_a5_real_n16r42_seed42-600-aa6edc35.png` | 600px 判读 | 600×900 |
| `render.log` | 渲染原始输出（4 次 `SHOT OK`，含亮度/彩色占比） | — |

**渲染时刻**：2026-10-22 18:10（文件 mtime 可核）；**数据产生时刻**：该批运行期（17:xx–17:44）。两个时刻不可混为一谈。

## 复现命令（仓库内可复算）

```bash
# 1) 从真源日志派生页面数据（只读，不写世界）
cd code
python3 frontend/tools/gen_threads.py \
  --log ../v2/evidence/run_a5_real_n16r42_seed42/run.jsonl \
  --out frontend/sample/dialogue_run_a5_real_n16r42_seed42/threads.json \
  --label run_a5_real_n16r42_seed42

# 2) 出四视图真截图（静态服务 8848 已常驻；shot.py → chromium-browser）
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
  sample/dialogue_run_a5_real_n16r42_seed42/threads.json "" "" \
  ../v2/evidence/fix-sleep-consolidation-20261022/shots
```
