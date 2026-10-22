# l7v2_shots —— R16（L-7 v2 去重臂）真拍截图三件套

> 纪律：截图必须是真实渲染产物，**禁止拼图、禁止跨批混拼**。本目录四张 PNG 全部由
> `frontend/tools/shot.py`（Chrome headless）从**同一批** `run_l7v2_on_n16r60_seed42` 的
> `threads.json` 真拍，`blank_retries=0/2`（首帧即有内容）。

## 三件套（缺一不可）

| 项 | 内容 |
|---|---|
| **① 来源 run 目录** | `v2/evidence/run_l7v2_on_n16r60_seed42/`（`run.jsonl` sha256 `ee3d28bc9606f2c2ee6609af7c5272673e54db674d5268878aa5d99e477f11b8`，55,598,046 B，116,498 事件，510 消息） |
| **② 渲染命令** | 见下方 §命令（含 `gen_threads.py` → `serve.py` → `dialogue_shots.sh` 全链） |
| **③ 日志 sha256** | `render.log` = `8b56486dfeb51525299f1e836238e988578789e1ab0ab9f935003d923698f791` |

## 命令（在 `code/` 下执行，逐步可复现）

```bash
# 0) 该目录**无原始 meta.json**（meta_gate.txt 已记录缺失）⇒ 使用派生 meta，报告已显式标注
python3 frontend/tools/gen_threads.py \
  --log  ../v2/evidence/run_l7v2_on_n16r60_seed42/run.jsonl \
  --meta ../v2/evidence/run_l7v2_on_n16r60_seed42/meta.derived.json \
  --out  frontend/sample/dialogue_l7v2/threads.json --label l7v2

# 1) 静态服务必须走 http://（file:// 因同源策略失败）；setsid 起，拍完立即收
setsid python3 frontend/tools/serve.py --port 8948 > /tmp/serve_l7v2_8948.log 2>&1 < /dev/null &

# 2) 拍 4 视图（不靠 sleep，靠 shot.py 等 window.__RENDER_READY__）
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8948 \
     sample/dialogue_l7v2/threads.json "" "" ../v2/evidence/l7v2_shots

# 3) 立即收服务
pkill -f 'serve.p[y] --port 8948'
```

> 注：8848 端口当时已被另一进程占用（HTTP 200，也是本仓 frontend），为避免歧义本批改用 **8948** 独立实例，
> 拍完即 `pkill` 收回（见 `render.log` 与任务汇报）。

## 产物（4 张，文件名 `<batch>-<view>-<sha8>.png`，sha8 由 threads.json 自校验）

| # | 文件 | 视图 / 视口 | 字节 | sha256 |
|---|---|---|---|---|
| 1 | `l7v2-chat-ee3d28bc.png` | 对话流 chat 1400×900 | 261,270 | `6efdaabcf80ff53a3f1c4c4777fea4281c7937aece6c69b9eca1a6ce5cb8df52` |
| 2 | `l7v2-rhythm-ee3d28bc.png` | 节律·串门 rhythm 1300×1050 | 282,904 | `fee577e4d9995bf497399f02645135a76170fcbf6a2a97294e85936181f9f2ce` |
| 3 | `l7v2-spread-ee3d28bc.png` | 闲话传播 spread 1300×900 | 175,610 | `77ef11669c6ebc1b87047dcffafb7de49f229d447ddf8dec61a74518f36d76a1` |
| 4 | `l7v2-600-ee3d28bc.png` | 600px 判读 600×900 | 190,684 | `9c50e3266bedb63efda63c2e6c1586bc557456d231daa8698c4f8656563694b8` |
| — | `render.log` | 渲染日志 | 3,370 | `8b56486dfeb51525299f1e836238e988578789e1ab0ab9f935003d923698f791` |

## ⚠️ 必须与图同时读的一条边界

**spread（闲话传播）视图是「真实渲染 + 真空态」**：本批日志 `msg_refs` 全为空（`gen_threads` 报
`ref_edges=0`），页面在真源无记录时**照实显示空态**并写明「不用相似度硬凑」。这**不是渲染失败**，
也不是「传播为零」的结论——该口径需要日志本身记录消息引用关系才可测，本批不具备。

chat 图内自证标签：`数据源 l7v2`、`sha ee3d28bc`、`事件 116498`、`消息 510`、`线程 169`、
`线程格式 explicit`、`meta 已派生`（页面自己把派生 meta 标出来了，与本目录 §命令 0 一致）。
