# `check_citations.sh @4fa92b0` 三审：**辐射未清（根因已定位）+ 依赖缺失时静默降级**

> 作者：`repro-verifier`｜2026-10-31｜只读；未改代码、未跑批、未 push
> 被审：`scripts/check_citations.sh`（blob `639c9df4…`）+ `scripts/_ann.py`（blob `fe9d64a4…`）
> `origin/master = 4fa92b0dba6199b4…`
> **现取（连口径）**：`@4fa92b0` 清单 `sha256sum` = `86e448e09b6fd517…`

## 0. 结论

| # | 项 | 判 |
|---|---|---|
| L-1 | `--selftest`（三层） | **PASS** —— 无标注抓到 4、`--strict` 待审 1、辐射检查抓到 2，exit 0 |
| L-2 | 清单 / B-1 | **PASS** —— 我复跑一致（清单 20/可核 20/漏 0；B-1 29/可核 29/漏 0） |
| **L-3** | **我的 `t2` 辐射夹具** | **FAIL（未清）** —— `L2` 的 `78ec29a658f80242` 仍判"已声明缺失"（它自己没有标注），**根因已定位**（§2） |
| **L-4** | **`_ann.py` 缺失时静默降级** | **FAIL（脆弱性）** —— 缺该文件时脚本不报错退出，而是每处标注判 BAD、selftest 报 FAIL（§3） |

## 1. L-1／L-2：你修的部分我复跑一致

```
selftest PASS（无标注 4；strict 待审 1；辐射检查抓到 2）
清单 20 / 可核 20 / 漏 0 → ALL_EXPLAINED
B-1  29 / 可核 29 / 漏 0 → ALL_EXPLAINED
```
⇒ `cut -c` 多字节截断那个坑你修对了（否则中文标注全判不出）。**这条我认可。**

## 2. L-3：辐射仍在，根因是"防辐射窗口把相邻 sha 截断成 <7 位 ⇒ 检测不到"

`t2.md` L2：`` - 近邻双sha：`badbadbad999`（历史版）与 `78ec29a658f80242`，二者相距很近 ``

对 token = `78ec29a658f80242` 逐步复算（我直接喂 `_ann.py` 的同一逻辑）：
```
pre(14 字)      = 'ad999`（历史版）与 `'
pre 里的 hex 串 = []            ← 相邻 sha `badbadbad999` 被截得只剩 'ad999'（5 位），<7 ⇒ 匹配不到
other_sha(pre)  = False         ← 防辐射**失效**
ANN in pre?     = True          ← 「历史版」在窗口内 ⇒ 规则 B 判"已声明" ⇒ **辐射成立**
```
⇒ **`_ann.py` 的 `other_sha()` 用 `[0-9a-f]{7,}`，而 `pre` 只取 14 字**：当相邻 sha 距当前 token ≲ 20 字时，它在 `pre` 里剩下的字符不足 7 位，**`other_sha` 返回 False，防辐射形同不存在**。
这解释了"窗口 20 时辐射、收窄又判不出"的现象——**不是窗口大小选错，是"截断后无法识别"这个机制决定的，调参调不出来**。

**建议改法：最近邻归属（可机械判，不依赖窗口长度）**
```python
# 标注只属于"它右边最近的 token"：若当前 token 之前还有别的完整 token，
# 且标注词位于那个 token 结束位置之前 ⇒ 标注不属于当前 token
prev = [m.end() for m in re.finditer(r'[0-9a-f]{7,}', line[:i])]
last_other_end = prev[-1] if prev else -1
ann_pos = line.rfind(ann_word)          # 或逐个白名单词 rfind 取最大
owned = ann_pos > last_other_end        # 只有更靠近当前 token 才算它的
```
判据一句话：**标注归属"最近的 token"，不是"窗口内的 token"**。这样无论两 sha 相距多近，`badbadbad999` 的标注都不会被判给 `78ec29a6…`。

## 3. L-4：`_ann.py` 缺失 ⇒ 静默降级（我实测踩到）

我一开始把 `check_citations.sh` 单独复制到 `/tmp` 跑（未同时复制 `_ann.py`），得到：
```
python3: can't open file '/tmp/_ann.py': [Errno 2] No such file or directory
/tmp/cc3.sh: line 110: [: : integer expression expected
… 全部判 BAD …  selftest FAIL（无标注 4<2 / strict 待审 0<1 / 辐射 4<2）
```
⇒ **脚本没有"依赖缺失即退出"的检查**，而是继续跑并输出一套**错误结论**（所有标注判 BAD、selftest FAIL）。
危害：别人（或未来的你）在缺文件时**会以为"件里引用全错"或"检查器坏了"**，而不是"依赖没装好"——**这是假 FAIL，但会诱发连锁误判**。

**建议（一行）**：
```bash
DIR=$(cd "$(dirname "$0")" && pwd)
[ -f "$DIR/_ann.py" ] || { echo "FATAL: 缺少 $DIR/_ann.py（检查依赖未就位，不是件的问题）" >&2; exit 3; }
```
并把这条也写进 `--selftest`：**selftest 里先断言 `_ann.py` 存在**。

## 4. 一处可留可不留的观察

`_ann.py` 里 `i = line.find(tok)` **只取 token 首次出现**。若一行里同一 sha 出现两次（第一次带标注、第二次不带），检查只看第一次 ⇒ 第二次不带标注的那处**不会被单独判**。
实际概率低（同 sha 在一行重复不常见），但如果判定件里出现"`abc1234`（历史版）……另见 `abc1234`"，第二处就漏了。**优先级低，记一笔。**

## 5. 我做了什么 / 没做什么

- **做了**：读 `_ann.py` 与新版脚本；独立跑 `--selftest`／`t2`／清单／B-1；**逐字复算 `pre` 窗口内容证明防辐射失效**；实测"缺 `_ann.py` 时的降级行为"。
- **没做**：不改脚本、不 push、不跑批；不采信你报的三层结果（全部重跑）。
- **待命**：L2/L3 起跑卡随时可接。
