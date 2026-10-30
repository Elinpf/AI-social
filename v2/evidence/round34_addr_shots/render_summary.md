# Round 34 现场渲染截图取证（chat / rhythm）

- 属性：**本轮现场渲染**，非历史旧图复用（`render_shots.py` 对同名 PNG 先 `unlink` 再截）
- 工具：`tools/metrics/render_shots.py`，sha256 = `a85f2711a46bfe150d0d162361cfa7584d8d7aea9ec2fb01b344d3ec879e0b34`
- 空白自检：`--blank-check off`（默认）⇒ 不给 `shot.py` 传单色判据，改用脚本自算像素自检
  `distinct_colors ≥ 200 且 top_color_frac ≤ 0.99 ⇒ OK`；4 张全部 **OK**（详见 `render_report.json` 每张 `pixel_selfcheck`）
- 退出码：两个批次 `ok_count=2 / fail_count=0`；无渲染失败目录需要替换

## 证据源（均为真 LLM 跑批，`fallback_detected=false`、`degraded_calls=0`）

| 批次标签 | run 目录 | run.jsonl sha256(前16) | code_sha | 规模 | llm_calls / 真调用 |
|---|---|---|---|---|---|
| `R34-n16r84-f3on` | `v2/evidence/cycle34_f3_on_n16r84_seed42` | `b6cacdaf975a178c` | `80009f4f…` | n16 r84 seed42 | 3403 / **1737**（非缓存） |
| `R34-D10-addr` | `v2/evidence/d9m-ab-on_n16r24_s42`（D10 称呼线引用批） | `2edc751c5a32d132` | `3176048a…` | n16 r24 seed42 | 2252 / **43**（非缓存） |

## 产物清单（4 张 PNG，全部 > 0 字节）

| 图 | 字节 | png sha256 |
|---|---|---|
| `R34-n16r84-f3on-chat-b6cacdaf.png` | 296057 | `1afa2d515019fc1e1d3344a21c36e9e1cd84c83c6f52ab902dfa165f955c5542` |
| `R34-n16r84-f3on-rhythm-b6cacdaf.png` | 285197 | `6a15be1b1c2fe59d7bbc9d1801194f97b78e408d6a5a1c465ed9a40bfaca61e3` |
| `R34-D10-addr-chat-2edc751c.png` | 294563 | `167fd1267004a20c003489a7b3c989f2c6e32b27395bc1e1e4c3fb494c9b280c` |
| `R34-D10-addr-rhythm-2edc751c.png` | 279783 | `803e412d7c694a2ca521b6f8bf358a063786f135cbc80ca34fe02579bee5534b` |

均已在渲染后肉眼核对：n16r84 chat 首屏为「石记」线程（林阿公/石艮等居民对话与地址），rhythm 视图为「一天里什么时候在说话」「都发生在哪儿」等节奏分布；D10 批 chat 首屏为老王/石记对话线。

## 可重放命令（逐条独立，输出目录同一处）

```bash
cd <repo>/social-experiment

python3 tools/metrics/render_shots.py \
  --run-dir v2/evidence/cycle34_f3_on_n16r84_seed42 \
  --batch-id R34-n16r84-f3on \
  --outdir v2/evidence/round34_addr_shots \
  --views chat,rhythm --timeout 180 --retry-blank 2

python3 tools/metrics/render_shots.py \
  --run-dir v2/evidence/d9m-ab-on_n16r24_s42 \
  --batch-id R34-D10-addr \
  --outdir v2/evidence/round34_addr_shots \
  --views chat,rhythm --timeout 180 --retry-blank 2
```

## 附带件

- `render_report.json`：两批合并汇总（run 元信息、log/threads sha256、逐张 png sha256 与像素自检、完整命令）
- `render_report_<batch>.json`：`render_shots.py` 原生逐批报告（三件套纪律字段原样保留）
- `render.log`：两批渲染全过程日志合并；分卷见 `render_n16r84_f3on.log`、`render_d10_addr.log`
- `threads_<batch>.json`：由 run.jsonl 现场派生（未写入 `code/`）

## 纪律自证

- 未跑批、未调 LLM；`pgrep` 确认无并发跑批后才起渲染
- 未修改 `code/`：`find code/ -newermt "2026-10-30 22:00"` 空输出（服务根为临时目录 + 符号链接）
- 写盘范围仅 `v2/evidence/round34_addr_shots/`；未 commit/push
