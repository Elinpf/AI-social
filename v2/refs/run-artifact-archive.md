# 跑批产物归档口径 —— side `.txt` 正文必须随日志一起归档（T229）

> 作者：release-engineer ｜ 2026-10-12 ｜ 任务：T229-run-artifact-archive
> 状态：**方案 + 产物清单（未实现）**；含一条**实测（非"应该能"）**。未实测项标 **【未验证】**。
> 关联：#10 数据管线（`v2/refs/training-data-pipeline.md`）、T227（`v2/refs/prompt-capture.md`）、T228、T219（`v2/refs/build-and-release.md`）。
> 直连对齐：`obs-stats-dev` / `freeze-layer-dev` / `emergence-researcher`（不经 Leader）。

---

## 0. 结论速览（先说根因）

1. **根因**：我们把 **`.jsonl` 当成了产物**，但 `.jsonl` 里存的是 **`body_ref` 指针**（`side://mem/...txt`），**正文在 `side/` 目录**。
   → **跑批产物的定义不完整**：日志 ≠ 正文。
2. **正文为什么没了（两个坑）**：
   - **坑 1｜跑完即删**：`orchestration.run_e2e` 默认 `side_root = tempfile.mkdtemp(prefix="hitt_side_")`，结尾 `cleanup_side=True` 时对 **位于系统临时目录**（`str(side_root).startswith(tempfile.gettempdir())`，本机 `/tmp`）的 side 直接 `shutil.rmtree`。
     **实测**：即便显式 `--side-root /tmp/...`，仍会被删 → **"保留 side"在 `/tmp` 下不成立**（`code/orchestration/integration.py:681,744`）。
   - **坑 2｜指针无 writer（新发现）**：**代码里只有 `life/memory.py` 真正往 side 写正文**（记忆 `.txt`）。
     `NARRATIVE.body_ref = side://narrative/<agent>/<nid>.txt`（`life/agent.py:449`）与 `SKILL_OUTPUT.output_ref = side://skill/...`（`life/settlement.py:301`）
     **只是写了指针、没有任何写入方** → **即使保留了 side，S4 叙事/skill 正文也导不出**（悬空引用）。
3. **实测（可复算，见 §4）**：用**非临时路径**保留 side 跑 N=3×1周 → `mem .txt=1324`、`.vec=1324`；打包 `tar.gz=510KB`；**解包后导出 S2 = 21 条、missing_body = 0**。
4. **口径**：**证据级 run 必须留 side `.txt` 正文**（随日志一起归档）；探测级可只留日志；**大文件/散文件不得静默入库**，一律打 `tar` + 记 sha256，**入 `v2/evidence/` 的只有小 JSON，不含归档本体**。

---

## 1. 产物清单（一个 run 到底该归档什么）

> 命名：一次跑批一个目录 `<run_id>/`，`run_id = <task>_n<N>_<weeks>w_seed<S>_<sha7>[_<tag>]`（例：`t229_n3_1w_seed42_3bbe67e`）。
> 归档本体：`<run_id>.tar.gz`；**本体不入 git**，`v2/evidence/` 仅存其 sha256 与命令。

| # | 产物 | 路径 / 命名规则 | 证据级必须？ | 说明 |
|---|---|---|---|---|
| A1 | **事件日志（canonical）** | `<run_id>/run.jsonl` | ✅ | 哈希链、`turn_seal`、`body_ref` 指针源 |
| A2 | **side 记忆正文** | `<run_id>/side/mem/<agent>/<mem_id>.txt` | ✅ | **S2/S3 的正文**；**当前会丢，本任务的靶心** |
| A3 | side 嵌入向量 | `<run_id>/side/mem/<agent>/<mem_id>.vec` | ❌ **不归档** | 由 `.txt` 经 frozen 嵌入**确定性再生**（T228：`.txt` 留 / `.vec` 关） |
| A4 | side 叙事正文 | `<run_id>/side/narrative/<agent>/<nid>.txt` | ⚠️ **当前不存在** | 指针有、writer 无（§0 坑 2）→ 需生活层/narrative 补写 |
| A5 | side skill 正文 | `<run_id>/side/skill/<agent>/<skill_id>` | ⚠️ **当前不存在** | 同上（`life/settlement.py:301` 只写指针） |
| A6 | **配置快照** | `<run_id>/config/`（9 个指纹文件） | ✅ | 复现真源；与 `engine_version` 指纹同源 |
| A7 | **引擎版本声明** | `<run_id>/config/engine_version.json` | ✅ | 组件版本一致性 |
| A8 | **指纹** | 写进 `manifest.json`：`config.fingerprint` / `log_hash` | ✅ | 与 `WORLD_INIT.fingerprint` **同口径** |
| A9 | **命令 + git 状态** | `manifest.json`：`cmd` / `seed` / `n` / `rounds` / `git.sha` / `git.dirty` | ✅ | 取 `tools/git_stamp.sh` 三行，不另算 |
| A10 | **manifest** | `<run_id>/manifest.json` | ✅ | 见 T219 §2.3 扩展（本任务加 `artifacts.archive` + side 统计） |
| A11 | freeze 输出缓存 | `side/freeze_cache/`（responses/judgments/embeddings） | ⚠️ 默认不归档 | 可再生；**若某结论依赖它，该 cache 的 sha 必须进 evidence**（T219 §2.3） |
| A12 | prompt 正文（T227） | `.../prompts/prompts.jsonl`（**默认关**） | ⚠️ 按开关 | 开则归档（脱敏后）；解锁 input 侧 |
| A13 | **密钥零残留** | —— | ✅ | 归档前扫描：`.env*`/`*.key`/`secret*`/`sk-*`/`Bearer`/`http(s)://`（自由文本字段）；**命中即拒归档** |

**A13 关键**：`.txt` 正文是 LLM 生成文本，**天然可能含端点/密钥回声** → 归档前必须过一遍脱敏扫描（复用 T227 `capture` 的 redact 规则）。

---

## 2. 归档口径：证据级 vs 探测级

| 级别 | 定义 | 必须归档 | side 正文 | 例子 |
|---|---|---|---|---|
| **证据级 run** | **结论会引用它的数字/正文**；进 `v2/evidence/`；被文档/方案引为证据 | A1 + A2 + **A6–A10** 全量 | ✅ **必须**（`.txt`） | `run_t136_real_llm_canon_n20`、本任务 N=3×1w 复现 |
| **探测级 run** | 调参/冒烟/ablation 中间态，结论**不引用其正文**（只引用聚合指标，指标可从 A1 重算） | A1 + A9 + A10 | ❌ 可丢 | N=10 短跑、`--production-off` 消融 |

**判据（一句话）**：**结论是否会用到"正文"？会 → 证据级（留 side）；只会用到"从日志可重算的指标" → 探测级（可只留日志）。**
- **升级规则**：探测级 run 一旦被某结论引用其**正文样本**（S1–S4），就地升级为证据级，**必须重跑并保留 side**（当前 canonical run 已无法回补，见 §4 背景）。
- **降级禁止静默**：把证据级当探测级处理（丢正文）必须**显式打印**并写进 manifest 的 `notes`。

> 现状痛点（`training-data-pipeline.md` §8）：**现有 canonical run 只剩事件 `.jsonl`，盘上无 `side/`** → S2/S3/S4 永久缺正文。**这正是本 profile 要堵的口子。**

---

## 3. 容量 / 压缩 / 上限 / 到期（不得静默入库大文件）

**实测数字（N=3×1周，非 temp 路径）**：

| 项 | 值 |
|---|---|
| mem `.txt` | **1,324** 个 |
| mem `.vec` | 1,324 个 |
| freeze_cache 文件 | 167 个 |
| side **散文件总数** | **2,815** |
| side **真实字节** | **0.59 MB**（`du -sb`） |
| side **块占用** | **≈ 12 MB**（`du -sh`）→ **文件系统块膨胀 ≈ 20×** |
| 日志 `run.jsonl` | 2.35 MB |
| **归档 `tar.gz`** | **510 KB**（含 log+side；log 主导，side 重复短文本压缩增益有限） |

**结论（容量）**：
- **真正的风险是 inode 与块膨胀，不是绝对体积** —— 2,648 个小 `mem` 文件只占 0.59 MB 真实数据，却吃掉 2,648 inode + 12 MB 块。
- **外推 N=50×1周【未验证】**：`mem` 文件 ≈ 1,324×(50/3) ≈ **22,000 个（仅 .txt）** / **44,000 个（含 .vec）**；多 run 累积会快速推高 inode（本机 inode 曾在 89% 水位）。

**归档必须带（硬要求）**：
1. **打包存储**：散文件一律 `tar`（+可选 gzip/zstd）后再落盘，**禁止把 2 万+ 散文件直接堆进归档目录**（inode 杀手）。
2. **上限 `max_bytes`**：单 run 归档超限 → **显式截断并落 `{"_marker":"archive_truncated"}`**（沿用 T227 语义，**不静默**）。
3. **到期 TTL**：证据级 **永久**（随 evidence）；探测级 **N 天后清理**（阈值待定【未验证】）。
4. **不入 git**：归档本体进 `.gitignore`（`**/*.jsonl`、`**/*.gz` 已有；**补 `**/side_*/`、`**/runs/`**）；`v2/evidence/` 只放**小 JSON（sha256 + 命令 + 统计）**。
5. **`.vec` 不归档**（A3）：确定性可再生；若要省事也**不可**把 `.vec` 混进正文归档目录（会 2× inode）。

---

## 4. 可验证：从归档里导出 S2（实测，非"应该能"）

**复现步骤（全离线，无网络）**：

```bash
cd social-experiment/code
# ① 跑一个小 run，side 放到【非 /tmp】路径（否则被 cleanup 删；见 §0 坑 1）
rm -rf /root/t229 && mkdir -p /root/t229/side
python3 -m orchestration run --life --seed 42 --agents 3 --weeks 1 \
    --out /root/t229/run_n3_w1.jsonl --side-root /root/t229/side
# ② 归档：日志 + side 正文一起打包
cd /root/t229 && cp run_n3_w1.jsonl run.jsonl
tar czf run_n3_w1.archive.tar.gz run.jsonl side
# ③ 从【归档】解包，仅凭归档导出 S2（反思样本）
mkdir extracted && tar xzf run_n3_w1.archive.tar.gz -C extracted
python3 export_s2.py extracted     # 见下方脚本（只读：事件 → side 正文）
```

**实测结果（本机 `sha 3bbe67e`，provider=离线 mock）**：

| 项 | 值 |
|---|---|
| 归档 `run_n3_w1.archive.tar.gz` sha256 | `47f07bcf3cea52bacde2396802d1869a62fe9e97bb7a283c6be080b20ccf9324` |
| 归档大小 | 509,828 bytes |
| **解包后导出 S2** | **21 条**，`missing_body = 0` |
| 样例 `source_event_seq` | 821（`triggered_by_mem_ids` 79 条源记忆 → 正文齐全） |
| `n_source` min/median/max | 0 / 76 / 86 |

> **诚实边界**：本次用**离线 mock provider**，正文是 `mock::…` 占位 → **验证的是「归档 → 导出」链路成立**，**不是正文内容质量**；真实正文需 real-LLM run（并过 §3 脱敏门）。
> `n_source` 最小为 0：存在**源记忆为空的反思**（如周强制反思）—— 导出对空源也应保留并标注，**不得当异常丢弃**。

`export_s2.py`（最小参考实现，只读不写世界）：

```python
#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(sys.argv[1]); log = root / "run.jsonl"; side = root / "side"
recs = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
body = lambda a, m: (side / "mem" / a / f"{m}.txt").read_text(encoding="utf-8")
out, miss = [], 0
for r in recs:
    if r.get("type") != "MEMORY_REFLECT": continue
    p = r["payload"]; a = p["agent_id"]
    try:
        srcs = [body(a, m) for m in p["triggered_by_mem_ids"]]
        refl = body(a, p["produced_mem_id"])
    except FileNotFoundError:
        miss += 1; continue
    out.append({"kind": "S2_reflection", "source_event_seq": r["seq"], "agent_id": a,
                "input": {"source_memories": srcs}, "output": {"reflection_body": refl},
                "meta": {"produced_mem_id": p["produced_mem_id"], "n_source": len(srcs)}})
json.dump({"n": len(out), "miss": miss, "samples": out},
          open(root / "s2_export.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"S2 exported: {len(out)} samples, missing_body={miss}")
```

---

## 5. 与 T227 / T228 的接口 —— 三者合起来才是 #10 的完整原料链

| 侧 | 负责 | 状态 | 缺了会怎样 |
|---|---|---|---|
| **input 侧**（prompt 正文） | **T227**（`freeze-layer-dev`） | ✅ 已落地（默认关、`purpose/sample`、脱敏、压缩、上限、TTL） | 有 output 无 input → **蒸馏/SFT 做不了** |
| **正文侧**（side `.txt`） | **T228**（`.txt` 留 / `.vec` 关） | ⏳ 口径已定 | 有指针无正文 → **S2/S3/S4 导不出** |
| **归档侧**（正文随日志归档） | **T229（本文）** | ⏳ 本文给方案 | 有正文但 run 结束即删 → **正文永久丢**（本任务根因） |

**三者关系（一张图）**：
```
LLM 调用 ──T227──▶ prompt 正文(input) ┐
世界事件 ──T228──▶ side .txt 正文(output) ┤──T229──▶ 归档 run_<id>.tar.gz ──▶ S1–S4 数据集 ──▶ #10 训练
内存/叙事  ─(缺口)─▶ narrative/skill 正文 ✗（无 writer，见 §0 坑 2 / §1 A4-A5）
```
- **缺 T227** ⇒ 只有 output、没 input（current）。
- **缺 T228/T229** ⇒ 只有指针、没正文（current，S2–S4 断源）。
- **T227/T228/T229 全齐 + 补 narrative/skill writer** ⇒ #10 的 S1–S4 才**完整可导、可复算**。

> **额外待办（不属本文，需 `life-layer-dev`/`narrative-designer`）**：`NARRATIVE`/`SKILL_OUTPUT` **只有指针没有写入方** —— 这不是「留不留给 side」的问题，是**从未写过**。需补 writer，否则 S4 永远无源。

---

## 6. 与 T219（构建/发布）的衔接

- 本口径 = T219 **「跑批产物清单」的扩展**：T219 管 `dist/`（代码+配置资产），T229 管 **run 产物**（日志+正文）。
- `manifest.json` 增字段：`artifacts.archive = {path, sha256, bytes, n_files, has_side:true, side_txt:n, side_vec:0}`；`git.sha/dirty` 取 `tools/git_stamp.sh`。
- 发布/跑批入口首行调 `bash tools/git_stamp.sh`（T220 契约）；`[DIRTY]` 时归档结论**标"仅供参考"**。

---

## 7. 未验证 / 开放问题

- **【未验证】** N=50 单周真实文件数与压缩比（本文 N=3 外推，非实测）。
- **【未验证】** TTL 阈值、`max_bytes` 上限的标定（待长跑样本）。
- **【未验证】** `.txt` 正文的**脱敏扫描实现**（复用 T227 redact，需一次实测；Q-6）。
- **【待定】** `narrative`/`skill` writer 缺失的归属与排期（`life-layer-dev`/`narrative-designer`）。
- **【待定】** 探测级 run 的 TTL 时长、是否允许"只留日志"的 run 进入 evidence（建议：**进 evidence 即证据级**，由本文§2 判据约束）。
- **【事实】** 本次实测 provider=离线 mock → 只证链路，不证内容。
- 本文**只设计**，未改 `code/`，未把归档本体入库；`v2/evidence/t229_archive_roundtrip.json` 仅存 sha/命令/小统计。
