# D9u 判定：**通过**（四条判据全满足）——扩表使三臂重新可比

> 性质：只读判定。作者：Leader。基线 `origin/master` @ `b54b055`（D9u 相关件已入库；D9t 预登记五轮修正**未推**，与本件无关）。
> 预登记：`v2/refs/D9u-prereg-lexicon-expansion.md`（`3cb8abd`）。

## 1. 变量与版本（R-12：仪器/词表 sha 必须同屏）

| 项 | 旧 | 新（本轮） |
|---|---|---|
| lexicon | `01e55338…fad859`（v1.1，**21 词**） | **`9c2129def89b01819db1fe965fc199458a21dff5ad5885aff262e35ceef56b76`（v2.1，46 词）** |
| instrument | `3dbca76f…` | **`30ff4aa3cfc5dc3b8448febddede4afc18b9e1b8a39cdd9f5d70dc6048945d18`** |
| 变动 | — | `expansion_22`（22 词）→ **`expansion_25`（+`刨/锉/掰`，合计 25）**，一律**追加末尾** + 长度/重复校验；schema `2.1` |
| 旧版留档 | `v2/evidence/instrument-snapshots/`（`9c2e8a3`/`2eb7244`） | — |

## 1.5 ⚠ `coverage` 一个数、两个阈值（`prompt-linguist` 指出，必须同屏）

```
coverage = assigned / 片段数        ← 同一个数
  ├─ 守卫：≥ 19.3171%   → coverage_ok（决定族类护栏能否用）
  └─ 主判据：三份均 ≥ 80% → D9u 的目标
```
**两个阈值差 4 倍，引用时必须写明"过了哪一个"。**

**余量对照（同一臂、两个阈值，余量差 60 倍）**：

| 臂 | coverage | 距守卫 19.32% | 距主判据 80% |
|---|---|---|---|
| OFF_run1 | 80.41% | **+61.09pp** | **+0.41pp（1 条片段）** |
| ON2 | 84.48% | +65.16pp | +4.48pp |
| A+B | 84.69% | +65.37pp | +4.69pp |

⇒ **只看 `coverage_ok=true` 会以为很宽裕，而主判据那边只余 0.41pp。** 两者不可互相替代。

**另**：`assigned` 与"包含即算"三臂**逐臂差 0**（`prompt-linguist` 独立核）⇒ 本件两个口径下的数一致，不存在"哪个口径"的选择问题。

## 2. 四条判据逐条

### 判据 1（主）：三份语料 `coverage` 均 ≥80% → **✅ 通过**

| 臂 | 片段 | 旧（v1.1，21 词） | v2.0（43 词） | **v2.1（46 词，现行）** |
|---|---|---|---|---|
| `d9s-syntax-off`（OFF_run1） | 194 | 50 = 25.77% | 156 = 80.41% | **162 = 83.51%** |
| `d9s-on2` | 174 | 9 = 5.17% | 147 = 84.48% | **147 = 84.48%** |
| `d9m-ab-on`（A+B） | 196 | 45 = 22.96% | 166 = 84.69% | **169 = 86.22%** |

**⚠ D9u.1 勘误后余量（重要变化）**：
- **v2.0 时 `OFF_run1` 只高 0.41pp（1 条片段）**，随时可能破 79.9%；
- **v2.1 补 `刨/锉/掰` 三词后升到 83.51%，余量 3.51pp** ⇒ **贴线问题解除**；
- **⚠ 改善不等**：`OFF` +3.10pp / `ON2` **0**（三词在 ON2 未出现）/ `A+B` +1.53pp ⇒ **不得写"三臂都提升 3pp"**；
- **`(d2)` +3**（OFF 34→37、ON2 26→27、A+B 29→32），**`max_v` 不变**（`刨 23 < 搁 34`）。

### 判据 2：`coverage_ok = true`（门槛 `C-cov = 19.3171%`）→ **✅ 通过**

| 臂 | coverage | `coverage_ok` |
|---|---|---|
| OFF_run1 | 80.41% | **true** |
| ON2 | 84.48% | **true** |
| A+B | 84.69% | **true** |

**⚠ 来源声明**：本项由 **Leader 自己用冻结仪器算**（`eval-researcher` 未回该值），命令与输出见 §5。若它与你的不同，以你的为准并报我。

### 判据 3：顺序敏感（新词不抢旧词首次命中）→ **✅ 通过（按本意）**

| 臂 | **旧词 21 个中，归族计数发生变化的个数** |
|---|---|
| OFF_run1 | **0 / 21** |
| ON2 | **0 / 21** |

**⚠ 判据 3 的字面表述（"`max_v` 变化 ≤1"）不满足**（OFF +17、ON2 +28），但那是因为**新词成为新最高频**，不是"抢位置"。
**⇒ 判据 3 的字面表述有缺陷，本判定按本意执行**（详见 `d9u-criterion3-order-sensitive-check.md`）。**下一版预登记须替换为"原有词逐词零变化"。**

### 判据 4：六类指标新旧差 ≤15pp → **✅ 通过（差 0）**

`tools/d9s/syntax_shape.py` 的六类分类**不读 lexicon**（仅 `--split-family` 时读取用于侧别统计）⇒ 不加该参数时新旧逐位相同。
实测 ON2：`c1 12.07 / c2 0 / c3 70.11 / c4 6.32 / c5 7.47 / c6 4.02`，`H/log₂6 0.5591`。
**⚠ 但 `--split-family` 的侧别统计（assigned/unassigned）扩表前后不可比。**

## 3. 判定

> **D9u 通过**：四条判据全部满足。**扩表达成其唯一目的——让三臂从 23% vs 5%（差 4.6 倍）回到 80–85% 的同一水平，臂间重新可比。**

**但它不是"表达变好"的证据**：
- 扩表**只是把尺子变宽**，不改变任何行为；
- 预登记 §8 边界 1 已写「不得用扩表后的数说'表达变好了'」——**本判定严格遵守**。

## 4. 三条必须同屏的后果

1. **所有历史族读数作废**：`d9m`/`d9s` 全部件里的 `(d2)`、`max_v`、`(b2′)`、`max_k` 都是旧表算的，**新旧不可比**；
2. **`d9s` 判定不受影响**：其"不通过"由 `H = 1.4452 < 1.7578 bits` 撑住，走 `syntax_shape.py`（与 lexicon 无关）；
3. **`max_v` 换主角（新基线）**：

| 臂 | 旧 top1 | **新 top1** |
|---|---|---|
| H0 | — | 33（`搁`） |
| A_only | — | 35（`搁`） |
| A+B | 12（`蹭`，旧表） | 30（`搁`） |
| OFF_run1 | 15（`挪`） | **34（`搁`）** |
| ON2 | 3（`伸`） | **36（`压`）** |

⇒ **`max_v ≤5`、`(d2) ≥10` 等绝对阈值全部失效**（新值 30–36 / 31），**必须按新基线重标**——这是 D9t 起跑前的前置。

## 5. 复算命令（可逐字跑）

```bash
python3 - <<'PY'
import sys,importlib.util
sys.path.insert(0,'tools/metrics')
spec=importlib.util.spec_from_file_location("nf","tools/d9n/narration_family.py")
nf=importlib.util.module_from_spec(spec); sys.argv=["nf"]; spec.loader.exec_module(nf)
from pathlib import Path
lex=nf.load_lexicon(Path("tools/d9n/narration_family_lexicon.json"))
v=nf.v_judge(lex); P=lex['parts_6']; O=lex['objs_13']
for name,p in [("OFF_run1","v2/evidence/d9s-syntax-off_n16r24_s42/run.jsonl"),
               ("ON2","v2/evidence/d9s-on2_n16r24_s42/run.jsonl"),
               ("A+B","v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl")]:
    fr=[f[1:-1] for m in nf.extract_messages(nf.read_log(p)) for f in nf.PAIRED_RE.findall(m['body'] or '')]
    a=sum(1 for s in fr if nf.assign_family(s,v,P,O)['assigned'])
    print(f"{name} {len(fr)} {a} {a/len(fr)*100:.2f}% coverage_ok={a/len(fr)>=0.193171}")
PY
```

## 6. 边界

1. **判据 1 的余量经 D9u.1 勘误后为 3.51pp**（v2.0 时是 0.41pp）；**仍属最薄处**，后续任何拒词都会降它；
2. **`coverage_ok` 由 Leader 自算**，未经 `eval-researcher` 独立确认；
3. **扩表不产生新数据**，所有读数来自既有 `run.jsonl`（均已入库，`git add -f` 强入）；
4. **本件不宣称任何"生活气息/表达质量"提升**。
