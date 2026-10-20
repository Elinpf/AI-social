# D8 M-1 双列对照（orig vs fixed）· armA/armB · n4r60/seed42

> 作者：metrics-dev｜2026-10-21｜任务：t7-m1fix（零 LLM，纯脚本）
> 脚本：`v2/evidence/d8_metrics.py`（**已有修改，见其头注释「修订 R9」**）
> 新读数：`v2/evidence/d8_metrics_armA_n4r60_seed42.json`、`..._armB_n4r60_seed42.json`
> 旧读数（脚本原样口径，保留对照）：同名 `.orig.json`

## 1. 一行复现（任何人跑同一条命令得同一结果）

```bash
python3 v2/evidence/d8_metrics.py --log v2/evidence/run_d8_armB_n4r60_seed42/run.jsonl \
  --label B --whitelist on --out-json /tmp/b.json >/dev/null && \
python3 -c "import json;d=json.load(open('/tmp/b.json'));o=d['layer4_M1_orig'];f=d['layer4_M1_fixed'];print('win_msgs=%d M1_orig=%d M1_fixed=%d seqs=%s'%(f['denom_msgs'],o['num_msgs'],f['num_msgs'],f['hit_seqs']))"
```

**期望输出（逐项一致，seq 顺序一致）**：

```
win_msgs=64 M1_orig=0 M1_fixed=3 seqs=[1974, 1988, 2118]
```

armA 同一条命令（把 `armB`→`armA`、`--label B --whitelist on`→`--label A --whitelist off`）期望：
`win_msgs=64 M1_orig=0 M1_fixed=0 seqs=[]`。

补充事实：同一输入两次运行输出 JSON **逐字节相同**（已 `cmp` 实测）；脚本无随机、无网络、不调 LLM。

## 2. 两列读数（两列都保留，不许合并、不许只报一列）

| 臂 | 列 | 分子（命中消息） | 分母（窗口内 MSG 去重） | 命中 seq | 命中实体 | 可作结论？ |
|---|---|---|---|---|---|---|
| A（开关关） | `M1_orig` | **0** | 64 | — | — | 否（口径缺陷） |
| A（开关关） | `M1_fixed` | **0** | 64 | — | — | 是（下界；本批 0 亦为真 0） |
| B（开关开） | `M1_orig` | **0** | 64 | — | — | 否（口径缺陷，见 §3） |
| B（开关开） | `M1_fixed` | **3** | 64 | `[1974, 1988, 2118]` | `D-14-wd.edict` ×3 | 是（**visitor 无词表 ⇒ 下界**） |

- 两臂分母相同（64），**per-message、去重**：分母 = 落在任一世界事件窗口 `[start,end)` 内的 `MSG_*` 去重条数。
- `M1_fixed` 的命中单位：一条消息只计 1 次（同一消息可同时属于多个窗口，但分子不按窗口重复计数）。
- armA 两列都为 0 且 `zero_nature=结构性(白名单未开…)`——**存在性方向不受本次修正影响**（B 非 0、A 为 0）。

## 3. 口径差异的因果（为什么 orig 是 0、fixed 是 3）——两个缺陷叠加，不是「修了个 bug」

**缺陷 D1：窗口归属错（只认第一个覆盖窗口即 `break`）**

本批 6 个世界事件实体里有 4 个窗口在时间上重叠：

| 实体 | 窗口 `[start,end)` | kind |
|---|---|---|
| `D-12-wd.visitor` | `[12, 18)` | visitor |
| `D-14-wd.edict` | `[14, 20)` | edict |
| `D-30-wd.tension` | `[30, 36)` | tension |
| `D-35-wd.visitor` | `[35, 41)` | visitor |
| `D-48-wd.visitor` | `[48, 54)` | visitor |
| `D-50-wd.tension` | `[50, 56)` | tension |

r15/r16 同时落在 `visitor[12,18)` 与 `edict[14,20)` 里。原脚本按 `issued_round` 升序取第一个命中的窗口便 `break`，
于是 r15/r16 的消息一律归给 **visitor**（issued=12），edict 窗口（issued=14）拿不到它们。
量化：`layer4_M1_win_pairs` 显示 fixed 口径下 (msg, entity) 对 = **78**，消息 = 64 ⇒ **14 对来自窗口重叠**（即 14 条消息被 orig 单归属强行分配）。

**缺陷 D2：`KIND_WORDS` 缺 `visitor` 词表**

冻结词表只有 `tension / edict / festival`，没有 `visitor`（D8 才首次启用 visitor 机制）。
⇒ 被 D1 错归到 visitor 的消息再查 visitor 词表必然是空列表 ⇒ **双重归零**（归错 + 查空）。

**修正后为什么是这 3 条**（三条措辞都命中的是 **edict** 词表中的「通告」，不是 visitor 词）：

| seq | round | 归属窗口 | 命中词 | 正文片段 |
|---|---|---|---|---|
| 1974 | 15 | visitor + **edict** | 通告（edict） | 新通告说，下月木料要统购，咱这手艺……怕是要难了。 |
| 1988 | 15 | visitor + **edict** | 通告（edict） | 谁知道呢。不过通告上说要登记外来人口，我寻思着，先别急着下结论。…… |
| 2118 | 16 | visitor + **edict** | 通告（edict） | 新通告说，下月起木料要凭票领了。 |

## 4. `M1_fixed` 为什么是「下界」而不是点估计

`layer4_M1_lexicon_coverage`（两臂相同结构，来自同一批世界事件）：

| 项 | 值 |
|---|---|
| 本批 kinds | `["edict", "tension", "visitor"]` |
| 有词表覆盖的 kind | `["edict", "tension"]` |
| **无词表覆盖的 kind** | `["visitor"]` |
| 窗口内消息总数 | 64 |
| 有词表 kind 可测的消息 | 38 |
| **只落在 visitor 窗口（结构性不可测）** | **26** |
| visitor 与其他 kind 重叠（靠重叠可被恢复） | 14 |

⇒ 那 **26 条**消息即使居民真的在用 visitor 类措辞谈论外来者，本列也一律记 0。
因此 `M1_fixed = 3/64` 的正确读法是「**至少 3 条**」，不是「恰好 3 条」。
本任务**不新造 visitor 词表**：`personas.json`/判据卡均无 visitor 的冻结词依据，事后新造词表等于改判据
（判据卡 §2 要求改词表必须换 `lexicon_sha8` 并重跑两臂），故按任务书选项二「显式声明 + 量化为下界」处理。

## 5. 脚本改动清单（可见、可审）

| 位置 | 改动 | 为什么 |
|---|---|---|
| `m1_scan(attribution)`（替代原 `window_hit_msgs()`） | 去掉首个命中即 `break`；`all` 归入全部覆盖窗口、`first` 保留原样 | 修 D1；保留 `first` 是为了让 orig 列仍然可复算、可对照 |
| `m1_columns()` | 同一逻辑产出完整列（分子/分母/seq/实体/raw hits） | 让第三方不必靠脚本内部变量去猜 |
| `--m1-attribution {first,all}`（默认 `all`） | 归属语义显式且可配置 | 任务要求「语义显式且可配置」 |
| 输出新增 `layer4_M1_orig` / `layer4_M1_fixed` / `layer4_M1_lexicon_coverage` / `layer4_M1_win_pairs` / `layer4_M1_flat_keys_note` | 两列并存 + 词表缺口显式声明 | 修 D2 的「不得默认忽略」要求 |
| 旧 4 个 flat 字段（`layer4_M1_num_msgs` 等） | **语义不变**，仍是 orig 值 | 不静默改既有字段语义（已新增 note 指明） |

> 已核对：新旧 JSON 之间**没有既有字段被改值**（`changed=[]`），只有新增键（6 个）。⇒ 下游引用旧字段不会静默漂移。

> **⚠ 读旧字段请按旧语义**：`layer4_M1_num_msgs`、`layer4_M1_num_entities`、`layer4_M1_dup_mentions_same_directive`
> 仍是 **orig（脚本原样口径，有缺陷）** 的值，不是修正后的值；JSON 内已用 `layer4_M1_flat_keys_note` 就地声明这一点。
> **任何结论请读 `layer4_M1_fixed`**；若下游把旧字段当新语义读，会得到「B 臂 M-1 = 0」的错误口径。

## 6. 给成稿环节的引用口径

1. 可写：「B 臂 M-1（修正口径）**3/64**，命中 seq `1974/1988/2118`，均为 edict 词「通告」；因 visitor 无词表覆盖，该列是**下界**」。
2. 可写：「A 臂两列均 0/64，且 `zero_nature=结构性(白名单未开)`」。
3. **禁止**写「B 臂 M-1 = 0/64」而不加限定（那是 orig 口径的缺陷值）。
4. **禁止**把 3/64 当点估计或换算成比率后与其他臂比较（分母 64 < 100，判据卡要求只报事件数）。
5. 两列不得合并成「0 或 3」之外的任何数；`M1_orig` 只能作「口径缺陷」的对照引用。
