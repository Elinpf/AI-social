# `v2/evidence/form_metrics/shots/` —— 真实截图证据（`Q-20` 整改）

> 出数脚本：`tools/metrics/render_shots.py`（主树新增，**只读既有日志、零跑批、零 LLM**）
> 生成时间：2026-10-24 02:29–02:30（**全部早于该时刻的旧图一律未被使用**）

## 0. 这份证据要解决的问题

`Q-20`：D12-H 渲染链断裂——**没有 `threads.json` ⇒ 没有 PNG**，`v2/evidence/d12h_shots/` 只有渲染脚本、0 张 PNG，
CYCLE-12 因此把本周期截图判为 `失败（缺证据）`。

本目录给出：**2 批 × 2 视图 = 4 张真实 PNG**，每张都能溯源到「来源 run 目录 + 渲染命令 + 日志 sha256」，
并附派生出的 `threads.json` 及其 sha256。文件时间戳（02:29–02:30）晚于本轮任务开始时间（02:10）。

## 1. 渲染链（一段话，可照抄复现）

```
源 run.jsonl
  └─(1) code/frontend/tools/gen_threads.py ─▶ threads_<批>.json（本目录，不落 code/）
       └─(2) tools/metrics/render_shots.py 起临时静态服务（symlink code/frontend，sample/ 只放本批 threads.json）
            └─(3) code/frontend/tools/shot.py（Playwright + Chromium 现场截图）──▶ <批>-<视图>-<sha8>.png
```

一条命令跑完一整批（在仓库根执行）：

```bash
python3 tools/metrics/render_shots.py \
  --run-dir .worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42 \
  --batch-id D12-H --outdir v2/evidence/form_metrics/shots --timeout 120

python3 tools/metrics/render_shots.py \
  --run-dir .worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42 \
  --batch-id T5 --outdir v2/evidence/form_metrics/shots --timeout 120
```

## 2. 四张图的「三件套」+ 指纹（逐张写死）

### 2.1 D12-H — 来源 run 目录 `.worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42`
日志 `run.jsonl` sha256 = **`122b36e988267a396cfdd95b167bad92bf69beabc249c253b46555f2679c3207`**（119519 行 / 510 条 MSG）
`threads_D12-H.json` sha256 = **`49266e735379d073af66c6dd9f9c5be925df8c420daf29f843f6481239eb22c0`**（8494324 字节 / 169 线程）

| PNG | sha256 | 字节 | mtime | 非空白自检 |
|---|---|---|---|---|
| `D12-H-chat-122b36e9.png` | `b199cb4d4dc7580d1a7c97f2fbfb7006e9be14827da171d18937761519d97a61` | 292143 | 2026-10-24T02:29:09+08:00 | OK：24394 色 / 最大单色 14.17% / 非背景 58.20% |
| `D12-H-rhythm-122b36e9.png` | `f0fcf9e3d643ba8acc6295a95e5b449a1755957799b6c74ed1777dbbe16d30bd` | 282266 | 2026-10-24T02:29:12+08:00 | OK：22372 色 / 最大单色 26.20% / 非背景 47.43% |

渲染命令（原样，来自 `render_report_D12-H.json` 的 `triplet.render_cmd`；端口为当次临时服务端口，端口号不固定，其余逐字相同）：

```
python3 code/frontend/tools/shot.py --url http://127.0.0.1:<port>/dialogue.html?still=1&multi=1&min=0&sort=turns&data=sample/dialogue_D12-H/threads.json --out v2/evidence/form_metrics/shots/D12-H-chat-122b36e9.png --width 1400 --height 900 --timeout 120.0 --retry-blank 2 --no-blank-check
python3 code/frontend/tools/shot.py --url http://127.0.0.1:<port>/dialogue.html?still=1&multi=1&min=0&view=rhythm&data=sample/dialogue_D12-H/threads.json --out v2/evidence/form_metrics/shots/D12-H-rhythm-122b36e9.png --width 1300 --height 1050 --timeout 120.0 --retry-blank 2 --no-blank-check
```

### 2.2 T5 — 来源 run 目录 `.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42`
日志 `run.jsonl` sha256 = **`dd4ad73d5a21c7485c2afbfc9701e267c25da3150b10adade3b3819a3996ff36`**（117393 行 / 510 条 MSG）
`threads_T5.json` sha256 = **`d643268a2ac728f7beb202167f784b261967844aed2f5deb60f3e3fab2385c01`**（2382007 字节，线程字段为显式 `thread_id`）

| PNG | sha256 | 字节 | mtime | 非空白自检 |
|---|---|---|---|---|
| `T5-chat-dd4ad73d.png` | `bf56c38bb078a7a3f87cdb379d87e339852c94f3679116752341b1030efb34ca` | 287640 | 2026-10-24T02:30:06+08:00 | OK：24224 色 / 最大单色 14.17% / 非背景 58.18% |
| `T5-rhythm-dd4ad73d.png` | `a8e9fe77bec0f7f12a8259fbf15c41d1872c44f177c63296c1f48d51251f19a2` | 282034 | 2026-10-24T02:30:08+08:00 | OK：22340 色 / 最大单色 26.20% / 非背景 47.40% |

渲染命令同 2.1 形式，`data=sample/dialogue_T5/threads.json`、`--out .../T5-chat-dd4ad73d.png`、`--out .../T5-rhythm-dd4ad73d.png`。

脚本本体 `tools/metrics/render_shots.py` sha256 = `a85f2711a46bfe150d0d162361cfa7584d8d7aea9ec2fb01b344d3ec879e0b34`。

完整全量数据（含每张图的 `png_sha256` 全值、`png_mtime_ns`、`pixel_selfcheck` 全部字段、逐字命令）见：
`render_report_D12-H.json`（sha256 `5edafaa9761e1de0c9ca981737574c52868cb6bd9e982dc9f8896a5a35eb7f4b`）、
`render_report_T5.json`（sha256 `e2a0f19ddf76a5eeea863571a17c7a8388557bba054dfa84f76ee45763576733`）。

## 3. 图上**能看见什么**（描述性，不做效果判读）

- `D12-H-chat`：源贴条显示 `D12-H / sha 122b36e9886 / openai_compat / seed 42 / 事件 119519 / 消息 510 / 线程格式 explicit（多轮线程）/ meta 已对齐`；
  顶部「第1天…第5天 × 早晨/上午/傍晚/夜间」5×4 节律格全部有内容；下方对话卡逐条可见，**正文几乎全是台词、括号旁白极少**。
- `T5-chat`：同结构；`sha dd4ad73d / 事件 117393 / 消息 510`；对话卡里**能看到成串的括号旁白**（如「（用袖子擦了半指宽的木头）」），
  与 D12-H 的形态差异**肉眼可见** —— 这与 `form_metrics` 里 `L-3` 0.1961% vs 57.8431% 一致（**此处只描述所见，不判优劣**）。
- `D12-H-rhythm` / `T5-rhythm`：两图的面板文本**逐字相同**（OCR 实测）——「话都发生在哪儿」为 `住宅 101 条 / 咖啡馆 103 条 / 公园 54 条 / 市集 53 条 / 中央广场 38 条 / 工坊 20 条 / 社区中心 18 条 / 农场 16 条`；「谁在串门」为 `老周 4次 / 老石 4次 / 秀娘 4次 / 陈医 4次`。
  像素级复核：两图差 **10,459 px，其中 10,407 px 落在 `y=60..79` 的元信息条**（`D12-H` vs `T5` 批标识），其余 52 px 属抗锯齿级差异、**无内容差异**。
  ⇒ **该视图对 D12-H / T5 这两批不具区分力**，只能作为「**渲染链可用性**」的证据（四张图能出、能打开、有内容），**不能**用作「两批确有差异」的证据；两批的差异证据是 chat 视图的旁白形态与 `form_metrics` 的 `L-3` 读数（`1/510 = 0.1961%` vs `295/510 = 57.8431%`）。
  ⚠ 更正留痕（2026-10-24，V1 反验后）：本段此前有三处**与图上实测不符**的表述——①把排行第一的场所写成非实际地点；②把串门人名写成非 20 persona 之一；③据两图差异推断两批互不相同（该推断不成立）。三者均被 OCR 与像素复核证伪（场所实为 `咖啡馆 103 条`、人名实为 `老周 / 老石 / 秀娘 / 陈医` 各 4 次；两图面板逐字相同），故整段重写。

## 4. 本次实测暴露的三处断点 / 缺陷（如实登记，不静默绕过）

| 编号 | 断在哪 | 现象 | 定位 | 处置 |
|---|---|---|---|---|
| `R-1` | 链路第 1 步之前 | `Q-20` 原断点：`v2/evidence/d12h_shots/` 无 `threads.json` ⇒ 无图 | 缺的是「派生 + 起服务 + 落三件套」这一段，**不是** `gen_threads.py` 或 `shot.py` 的缺陷 | ✅ 已由 `tools/metrics/render_shots.py` 补齐；`code/frontend/` 一字未改 |
| `R-2` | 链路第 2 步（我自己的脚本） | 首轮实测两视图全部 `SHOT FAIL: 等待 __RENDER_READY__ 超时` | **本脚本自身缺陷**：临时服务根里的 `threads.json` 用了**相对路径**建软链（链接目标被解析为「相对链接所在目录」）⇒ 软链断裂 ⇒ 前端 `GET /sample/.../threads.json` 404 ⇒ 页面永不 ready。诊断证据：独立探针直连时 `loaded at 1.2s`、`READY at 6.4s`、`cards=88`，证明页面与数据都没问题 | ✅ 已修：改用 `threads_json.resolve()` 绝对路径建链（脚本内注释留痕）；修后 4 张图 rc=0 |
| `R-3` | 链路第 3 步（`shot.py` 的判据，属 `code/frontend`） | `shot.py` 的「非空白」判据（最大单色占比 ≥50% 判空白）对 `dialogue.html` **假红**：实测正常渲染的深色页面被判「最大单色占比 80.09%」⇒ rc=1、拒绝出图（重试 3 次仍 FAIL） | `code/frontend/tools/shot.py::_largest_color_frac` + 阈值 `_BLANK_FRAC`；`shot.py` 自身 docstring 已写「`--no-blank-check` 用于非小镇画布的普通页面：深色/大色块页面会被误判为空白」 | ⚠ **未改 code/**（冻结期）。按 docstring 的既定用法传 `--no-blank-check`，改用本脚本自算的像素自检（`distinct_colors ≥ 200` 且 `top_color_frac ≤ 99%`，逐张落盘）。**建议修法（交 Leader/下一周期）**：给 `shot.py` 加页面类型档（如 `--blank-profile=canvas|ui`），UI 档用「色数 + 非背景占比」判据，而不是单色占比 |

另：`GET /favicon.ico 404` 属无害噪声，不影响出图。

### 4.1 像素自检的**可复算命令**（验收员可直接照抄复跑，结果应与上表逐位相同）

```bash
python3 - <<'PY'
from PIL import Image
from collections import Counter
from pathlib import Path
for p in sorted(Path('v2/evidence/form_metrics/shots').glob('*.png')):
    im = Image.open(p).convert('RGB'); px = list(im.getdata())
    c = Counter(px); mc, top = c.most_common(1)[0]
    nb = sum(1 for q in px if abs(q[0]-mc[0])+abs(q[1]-mc[1])+abs(q[2]-mc[2]) > 24)
    print(p.name, len(c), round(top/len(px), 4), round(nb/len(px), 4))
PY
```

实测输出（2026-10-24 02:3x 复跑，与 §2 表内数值一致）：

```
D12-H-chat-122b36e9.png   24394  0.1417  0.582
D12-H-rhythm-122b36e9.png 22372  0.262   0.4743
T5-chat-dd4ad73d.png      24224  0.1417  0.5818
T5-rhythm-dd4ad73d.png    22340  0.262   0.474
```

判据（写死）：`distinct_colors >= 200` 且 `top_color_frac <= 0.99` ⇒ OK。
四张图分别超出阈值两个数量级 ⇒ **不是空白帧/单色帧**，与 `shot.py` 的「单色占比 >=50% 判空白」结论相反（该判据对深色 UI 假红，见 R-3）。

## 5. 纪律自述（可核查）

- **无拼图、无跨批混拼**：每张图由一次独立 `shot.py` 调用产出，文件名带 `batch_id` + 日志 sha8；两批 PNG 的 sha256、字节数、像素自检值互不相同。
- **无旧图冒充**：`render_shots.py` 在截每张图前若发现同名文件**先删除**，只认本次现截（见 `render_report*.json.policy.no_reuse`）。
- **`code/` 零写入**：服务根是 `/tmp/hitt_render_*` 临时目录 + 指向 `code/frontend/*` 的符号链接，`sample/` 只放本批 `threads.json` 的链接；
  全流程 `sys.dont_write_bytecode`，`git status code/` 无本任务新增（仅工作前既有的 `?? code/frontend/sample/dialogue_*`）。
- 零跑批、零 LLM 调用、未 commit / push、未 kill 任何进程（静态服务是本进程内的 daemon 线程，进程退出即回收）。
- 未使用正在跑的 D12-I 日志：两批均为**已收批**（存在 `run_batch.end`）。
