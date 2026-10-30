# 「串臂 / 串口径 / 串表版本 / 服务端状态」四问自检（v2）

> 作者：dialogue-core-dev｜2026-10-31 更新（v1 由 Leader 入库于 `v2/refs/selfcheck-cross-arm-and-caliber-by-dig-core.md`，sha `2626c0f4…`）
> 性质：**只读检查清单 + 两条可跑锚点**。v2 新增 ④ 服务端状态 + "脚本与表版本绑定"案例 + 一处数据自纠。

## 0. 四问（引用任何两个数之前）
1. **同一个臂吗？**（H0 / A_only / A+B / OFF_run1 / ON2 …）
2. **同一套口径吗？**（字面可多计 / 归族单计 / 三臂合计 / 单臂）
3. **同一个表版本吗？**（lexicon v1.1 21 词 / v2.0 43 词 / 扩表 52 词；`normalized_entropy` vs `..._nonempty`；六类 vs 六格）
4. **同一个时间点的服务端状态吗？**（我以为"已推送/已入库"的东西，真的在吗？）

**四元组记法**：`max_v=36 / ON2 / 归族 / 扩表52词` —— 写全就不可能串。

## 1. 第 ④ 问怎么查（今晚 3 次踩到）
```bash
git cat-file -e <sha>                    # ① 这个 commit/对象在本机存在吗
git ls-remote origin refs/heads/master   # ② 远端 master 现在指向谁（不看本地缓存）
git fetch origin && git rev-parse origin/master   # ③ fetch 后再读远端 ref
git cat-file -e origin/master:<path>     # ④ 文件真的在那个提交里吗
```
**判据**：说"已入库/已推送"之前，①④ 必须都返回 0；只看到 `push rc=0` 或本地分支有该 sha **不算**（`34e862a` 就不在 master；`push` 成功也可能被 timeout 吃掉）。

## 2. 第 ③ 问的典型案例：**脚本与表版本绑定**（2026-10-31）
`d9u_order_sensitivity.py` v1 写死「旧表 21 词、追加到 `verbs_rotation_13` 尾」：
- 在 **v1.1 树**里跑：通过（改族 0 片）；
- 在 **v2.0 树**里跑：**断言必失败**（v2.0 已含 `verbs_expansion_22`，再往 `rotation_13` 追加会插在它之前 ⇒ 前 43 项立刻变）。

**v2 修法（已实现）**：
1. `--old-lexicon` 显式传旧表（默认 = 随脚本附的 **v1.1 逐字节快照** `tools/d9s/lexicon_v1.1_snapshot.json`，sha256 `01e55338…`，与 D9u 预登记记录的 v1.1 一致）；
2. **自动识别"最后一个动词表"**（v1.1=rotation_13，v2.0=expansion_22），新词只追加到它尾部；
3. **自动剔除旧表已有的新词**（v2.0 下 31 候选只剩 9 个新增）；
4. **版本一致性硬检查**：所传 lexicon 含 `verbs_expansion_22` 而当前 `v_judge` 只读 21 词时，**直接报错并给出怎么改**，不再抛裸断言；
5. import 优先用 **cwd 的 `tools/d9n`**（在该 lexicon 所属树里跑就对）。

**两种模式实跑（2026-10-31）**
| 模式 | 旧表 | 新增词 | 结果 |
|---|---|---|---|
| A（默认） | v1.1 21 词 | 31 | 新表 52 词；**改族 0 片 ⇒ 顺序不敏感通过** |
| B（`--old-lexicon current`，主树） | v2.0 43 词 | 9（31 中 22 个已在表内） | 新表 52 词；**改族 0 片 ⇒ 追加 9 词也通过** |

## 3. 基线速查（**含一处自纠**）

**单臂 · 归族 · `max_v`**
| 臂 | v1.1(21 词) | 扩表(52 词) |
|---|---|---|
| H0 | 31(蹭) | 33(搁) |
| A_only | 24(蹭) | 35(搁) |
| A+B | 12(蹭) | 30(搁) |
| OFF_run1 | 15(挪) | 34(搁) |
| ON2 | 3(伸) | 36(压) |

**`(b2′)` 违例族数**（自纠：我先前给的是"11–14"，实测为 **11–15**）
| 臂 | v1.1 | 扩表 52 词 | 主树 v2.0 |
|---|---|---|---|
| H0 | 7 | **14** | 14 |
| A_only | 7 | **14** | 14 |
| A+B | 4 | **14** | 14 |
| OFF_run1 | 5 | **15** | 15 |
| ON2 | 0 | **11** | 12 |

**三臂（OFF_run1+ON2+A+B）· 字面可多计**：搁 34+20+30=**84**、压 11+36+15=**62**
> 84 与 36 **永不并排**：一个三臂合计、字面可多计；另一个单臂、归族。

## 4. 判定用哪个
**单臂 + 归族 + 新表**的 `max_v`（33/35/30/34/36），阈值按**新基线重标**；不得用 84/62，不得用旧表 5，不得"放宽到 40"。

## 5. 两条可跑锚点
```bash
# ① 真调用率（判"同一个臂/能不能比"）
python3 - <<'PY'
import json,sys,collections
for p in sys.argv[1:]:
    per=collections.Counter(); real=collections.Counter()
    for line in open(p,encoding="utf-8"):
        if "LLM_CALL" not in line: continue
        e=json.loads(line)
        if e.get("type")!="LLM_CALL": continue
        d=e["payload"]; pu=d.get("purpose"); per[pu]+=1
        if (d.get("tokens_in") or 0)>0: real[pu]+=1
    print(p, f"dialogue真调用={real['dialogue']}/{per['dialogue']}")
PY

# ② 口径/表版本（旧表 vs 扩表、单臂归族；末行给"顺序不敏感/通过"）
cd <该表所属树>/code && python3 tools/d9s/d9u_order_sensitivity.py            # 对 v1.1 快照
cd <该表所属树>/code && python3 tools/d9s/d9u_order_sensitivity.py --old-lexicon current   # 对当前表
```
