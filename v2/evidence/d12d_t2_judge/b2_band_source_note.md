# 旁证：B2 噪声带 `denom_510` 的 sha 溯源（真源 / 副本 / 默认输出位）

- 记录人：`metrics-judge`（判读与复算专家）
- 记录时刻：**2026-10-23 10:25 (+0800)**
- 记录性质：**溯源旁证**，不为任何结论提供新证据；本文件**不修改** `v2/evidence/d12d_t2_judge/b2_band.json`（那是 10:09 当刻的输出存档，保持原样）

---

## 1. 三份 sha 与两份取数时刻

| # | 对象 | 取数/核对时刻 (+0800) | 内容 sha256 | 顶层 `results` 键 | 状态 |
|---|---|---|---|---|---|
| ① | `v2/evidence/d3_noiseband_bootstrap.json`（**共享默认输出位**，10:11 时的工作区版） | **10:05 / 10:09** | `3e920dddd0be2b798da0ebf7279e9af0a992e8124fc6b853eb6d6b36656cbde0` | `denom_510` | **已被覆盖，现不存在** |
| ② | `v2/evidence/d12d_t2_judge/d3_noiseband_bootstrap_denom510.json`（**可复现副本**，本轮 `--out` 重建） | **10:22**（文件 mtime `10:22:24`） | `3e920dddd0be2b798da0ebf7279e9af0a992e8124fc6b853eb6d6b36656cbde0` | `denom_510` | **存在；与 ① 逐字节一致** |
| ③ | 同一路径的**当前工作区版** | 10:11:52 起（mtime） | `2313c001b65464df14f012f27b261b58cdf73bb4dfe1e3290bc11b4b22ba1f04` | `denom_341` | 存在（他人产物，与本报告无关，**未 add、未改动**） |
| ④ | `git show HEAD:` 版（HEAD=`4d8a583`） | 10:25 | `cf7a85754495cce2745a3dca706795df7cb892481c0fe5fab04129d4bda869ac` | `denom_480 / 623 / 686` | 自 `b21042b`（2026-10-21 00:11）起即为此内容，**从未含 `denom_510`** |

> 结论：**①② 同 sha**（真源＝副本），③④ 均不含 `denom_510`。

## 2. 覆盖事件的时间线（可核对）

| 时刻 | 事件 | 依据 |
|---|---|---|
| 10:05、10:09 | 本判读两次读取 ①，`sha256sum` 与 `json` 键均为 `denom_510` | 本判读执行记录；值等于 CYCLE-07 §S05 记录（`3e920ddd…cbde0`） |
| 10:09 | 本判读运行 `python3 v2/evidence/d3_noiseband_bootstrap.py --denom 510`，输出 L-7 `[-5.88, 5.88]` | `v2/evidence/d12d_t2_judge/b2_band_denom510.txt` |
| **10:11:52** | ① 被并发分析以 `--denom 341` **实跑覆盖** → `2313c001…`（键 `denom_341`） | 文件 mtime `10:11:52`；覆盖动机见 commit **`4d8a583`** 消息「refs(d12e): §6 更正——F-2 无现成噪声带实现…**实跑 denom341 已确认**」 |
| **10:22**（mtime `10:22:24`） | 本判读用 `--out` 把 `--denom 510` 重算到独立文件 ②，得 **同 sha** | `v2/evidence/d12d_t2_judge/d3_noiseband_bootstrap_denom510.json`（sha256 同上）、`b2_band_denom510_rerun.txt` |

**覆盖嫌疑人**：并发成员 `life-evidence-analyst`（依据：`4d8a583` 的 D12-E「实跑 denom341 已确认」；任务 t6 描述亦点名）。**这是流程性的共享写冲突，不是数据错误**。

## 3. 为什么这会影响「引用方式」而不影响「带值」

脚本 `v2/evidence/d3_noiseband_bootstrap.py`（sha256 `d878ac643716f437c57cc12753fd667bb49c2dd3d9dbda4bc72121a84d822986`）把 B=2000、`random.Random(42)`、语料 `v2/evidence/d3_annotated_corpus.jsonl`（sha256 `2d06c18490de8f067df33896e6e0de4776dc2ef38b4b617a413dbf652b644954`）**全部写死**，默认 `--out` 指向 ①。

- 因此带值 `[−5.88, +5.88]pp` **只依赖「脚本 + 语料 + `--denom 510`」三件**，与 ① 的内容无关（①只是默认落盘位置）；
- 用 `--out` 重算得到字节级相同的文件 ⇒ **带可离线重现，覆盖不构成证据缺失**；
- 但 **① 不可作为跨时点真源引用**（后跑者的 `--denom` 会覆盖它）。

## 4. 约定（本轮方法论产出，建议写进下一轮预登记）

1. **真源引用格式**：`脚本 sha256 + 语料 sha256 + 命令行 --denom N + 输出文件 sha256`；不写「某某 json 是 sha X」。
2. **每个 denom 落独立文件**（如 `d3_noiseband_bootstrap_denom510.json`），**共享 JSON 只当默认输出位**，不入任何判定引用。
3. 复算一律带 `--out` 指向自己的证据目录，**不要依赖脚本默认路径**——默认路径是多人共写位，会互相覆盖。

## 5. 复现命令

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
sha256sum v2/evidence/d3_noiseband_bootstrap.py          # 期望 d878ac64…2986
sha256sum v2/evidence/d3_annotated_corpus.jsonl          # 期望 2d06c184…4954
python3 v2/evidence/d3_noiseband_bootstrap.py --denom 510 \
  --out /tmp/d3_check_510.json
sha256sum /tmp/d3_check_510.json                         # 期望 3e920ddd…cbde0
python3 -c "import json;d=json.load(open('/tmp/d3_check_510.json'));print(d['results']['denom_510']['L-7 8gram_shared'])"
                                                          # 期望 {'abs_p95_pp': 5.88, 'band_pp': [-5.88, 5.88], 'width_pp': 11.76}
```
