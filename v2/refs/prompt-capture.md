# freeze：可选 prompt 正文落盘（T227）

> 作者：freeze-layer-dev ｜ 日期：2026-10-12 ｜ commit：见 `git log --grep T227`
> 目的：解锁用户目标 **#10**（拿数据训小模型）——补上 **input 侧**。

## 0. 背景

T225 核实：`LLM_CALL` 只有 `prompt_hash`、响应缓存只有输出 `text` → **「有 output 无 input」**，
**蒸馏/SFT 做不了**。本能力提供**可选**的 prompt 正文本地落盘。

## 1. 四控（硬要求）

| # | 控制 | 实现 |
|---|---|---|
| 1 | **默认关** | `CaptureConfig.enabled=False`；三态 `mode ∈ {off, sample, purpose}`；`fingerprint()` 折进 `engine_version`（`engine_version_with_policy()` → `…|capture=<digest16>`） |
| 2 | **不落全量** | `purpose` 模式默认只落 `{dialogue, reflect}`，**显式排除 `{judge, importance, describe, narrate}`**；`sample` 模式按 `crc32(cache_key)%10000 < rate*10000` **确定性抽样**（同 run 可复算） |
| 3 | **存储控住** | **单文件 append**（`<cache_dir>/prompts/prompts.jsonl`，规避 inode）+ 逐条 **zlib+base64 压缩** + **`max_bytes` 上限**（触顶**停写并显式落 `{"_marker":"capture_truncated"}`**，不静默）+ **TTL 到期清理** |
| 4 | **脱敏硬门** | 落盘前 redact（显式术语=env `LLM_API_KEY/…` + provider `base_url`；正则=`http(s)://…`/`sk-…`/`Bearer …`/`key=…`/32+hex）→ **只扫描自由文本字段**（`system/user/output`；自身 `cache_key/prompt_hash` 元数据不参与，避免 32+hex 误伤）→ **扫不到才写**，否则**拒写并计数 `refused`** |

**接入点**：`LLMClient.complete` 的**缓存命中**与**真实返回**两处（T0 兜底不落）。**默认关时零文件写入、行为逐项一致**。

## 2. 配置示例

```python
from freeze import FreezeConfig, LLMClient, MockProvider, EventLog
from freeze.capture import CaptureConfig

cfg = FreezeConfig(engine_version="v2+abc", cache_dir="./runs/r1")
cfg.capture = CaptureConfig(enabled=True, mode="purpose")   # 默认关；此开只落 dialogue/reflect
client = LLMClient(cfg, provider=MockProvider(), event_log=EventLog())
client.complete(purpose="dialogue", system="…", user="…")   # → 落盘（脱敏后）
client.capture.stats()   # {'written','refused','skipped','capped','truncated','bytes'}
```

## 3. 验收（tests，`tests/test_freeze.py`）

```
python3 -m pytest -q tests/test_freeze.py -k capture     # 9 passed
```
覆盖：默认关零写入 · `purpose` 排除 `judge` · 抽样确定性 · **反向验证（key 嵌进 prompt → 不得入盘；端点不得入盘）** · 拒写硬门（模拟 redact 失效→必须拦住并计数）· 容量上限 + `truncated` 显式标记 · TTL 清理 · 指纹随开关变化。

**实测（本地）**：`tests/test_freeze.py` → **57 passed**（含 9 项 T227）。

## 4. 与 side 存储 / #10 的关系（对齐 T228）

- 本能力解决 **prompt（input）侧** 落盘；**记忆/叙事正文**在 `side://`（`SideStore`），属**另一条**（T228 `.txt` 保留）。
- T225 实测：现有 canonical run **只剩事件 `.jsonl`**，盘上无 `side/` → **S2–S4（记忆/反思/叙事正文）导不出**；本能力上线后可补 **SFT/蒸馏的 input 侧**，但 **output 侧正文仍需 side `.txt` 保留（T228）**。

## 5. 未决 / 注意

- **默认关**：需显式开启（并进指纹，改变即视为复现输入变更）。
- **`refused`/`truncated` 是审计痕迹**：出现即为"采集被拦/被掐"，勿当成"样本少"。
- 【未验证】大样本下的压缩比与 `max_bytes` 标定（待长跑）。
