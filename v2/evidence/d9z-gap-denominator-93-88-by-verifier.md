# D9z v3 复核：`93` vs `88` 的差异来源已定位；`ed56acf`/`2744dbc` 性质更正

> 作者：`repro-verifier`｜2026-11-01｜**只读**；未跑批、未改代码、未 push
> 对象：`v2/refs/D9z-prereg-intra-round-visibility.md`（复核时 `master=2744dbc`；所引 sha256 `a0c2927063fb96c9…`（**v3 时点值·非当前版**），`master` 现值该件为 `c43692a658c7a107…`（v3.2）；103 行 / 7,751 B 亦为 v3 时点快照）
> 数据：`v2/evidence/d9t-on_n16r24_s42/run.jsonl`（sha256 `af4c44d11dd22eb8…`，MSG 去重后 **191** 条）

---

## 1. `93` vs `88`：**口径差异，不是算错。差在"排不排父"**

`93 / 34 / 0.3656` **精确复现**，条件是：**只排除「本条 `place=residence`」，不看父的 `place`**。

| 变体 | `n` | gap 分布 | `gap≥2` | 占比 |
|---|---|---|---|---|
| ① 无排除 | **125** | `{1:77, 2:48}` | 48 | **0.3840** |
| **② 本条或父 residence（leader 的 88）** | **88** | `{1:58, 2:30}` | 30 | **0.3409** |
| **②′ 仅本条 residence（复核方的 93）** | **93** | `{1:59, 2:34}` | 34 | **0.3656** |
| ②″ 仅父 residence | **105** | `{1:61, 2:44}` | 44 | **0.4190** |
| ③ thread 总条数 ≥2 | 125 | `{1:77, 2:48}` | 48 | 0.3840 |
| 排 `round 0`（本条） | 125 | `{1:77, 2:48}` | 48 | 0.3840 |
| ④ ②+③ ／ ⑤ 排 round0+② ／ ⑥ 三者全 | 88 | `{1:58, 2:30}` | 30 | 0.3409 |

**结论**：`93` 与 `88` **不是谁算错，是 v2 那句「排除 `residence`」没写清排哪一端**。复核方按「本条」、leader 按「本条或父」，于是 `125 → 93 → 88`。

**判断**：「本条或父」更贴合排除目的 —— `residence` 要排是因为全员在住所 = 初始/睡眠态，`C(16,2)=120` 占 33%，不是可对话配对；**只要对话任一端在住所，这段就不可信**。但 v3 已删三条排除，该值不进判据，**不阻塞冻结**。

**建议补写**：敏感性行须写「排 `residence`（**本条或父，任一端即排**）」，并把 `93（仅本条）/ 105（仅父）/ 88（两端）` **三值同屏**。**尤其必须列出 `105 / 0.4190`** —— 它的 `gap≥2` 占比**比基线 0.3840 还高**，只挑这一个数会得出"排除后更糟"的反向结论。三值不并排，此行即为可随手挑数的坑。

复算命令：
```python
msgs={}
for l in open("v2/evidence/d9t-on_n16r24_s42/run.jsonl",encoding="utf-8"):
    if not l.strip(): continue
    e=json.loads(l)
    if not e.get("type","").startswith("MSG"): continue
    pl=e["payload"]; msgs[pl["msg_uid"]]=(int(e["round"]),pl.get("place"),pl.get("thread_id"),pl.get("reply_to"))
p=[(msgs[u][0]-msgs[r][0],msgs[u][1],msgs[r][1]) for u,(a,b,c,r) in msgs.items() if r and r in msgs]
print(len(p))                                                            # 125
print(len([x for x in p if x[1]!="residence" and x[2]!="residence"]))    #  88
print(len([x for x in p if x[1]!="residence"]))                          #  93
print(len([x for x in p if x[2]!="residence"]))                          # 105
```

---

## 2. `ed56acf` vs `2744dbc`：**不是"两个提交各推一次"，是父子提交、内容零差异**

```
2744dbc 05:13:27  删三条排除、两臂同尺；并把 93 与 88 的差同屏（未复现 93）
ed56acf 04:47:00  修致命项「分母/基线两把尺」：删三条排除，两臂同尺 125/0.3840
0345742 04:17:37  v2
```

- `git merge-base --is-ancestor ed56acf 2744dbc` → **YES**（`ed56acf` 在 `2744dbc` 历史里）
- `git diff --stat ed56acf 2744dbc` → **空**
- tree 相同（**历史版 git 对象 id，非文件指纹，不得作 sha256 用**）：`a621aa36191f` / `a621aa36191f`；blob 均 `7eb4406…`（同为**历史版 git 内部对象**）

⇒ **不是两个成员撞车各推一次，是同一份内容被提交了两次**（第二次只改 commit message：把「修致命项…」改成「…并把 93 与 88 的差同屏」）。**无第三方插入，不需要追责谁。**

---

## 3. 「谁推的」：**commit 元数据查不出来，属结构性问题**

两次提交 author / committer 均为 `life-evidence-analyst <life-evidence-analyst@jiuwenswarm.local>`，而该身份是**团队共享 git 配置**：

```
843 life-evidence-analyst
638 TeamLeader
 85 dialogue-core-dev
 28 frontend-demo-dev
 21 prompt-linguist
 20 life-engineer
```

⇒ `life-evidence-analyst` 是团队 843 次提交的共用身份，非某成员专属（本机 `git config user.name` 亦为它）。**"是不是你推的"用 git 元数据无法回答** —— 任何成员在此仓提交都显示此名。

**本件作者陈述**：`ed56acf` / `2744dbc` **不是我推的**（全程只读复核，脚本在 `/tmp/vvx/`，未 `git add/commit/push`）。**说明**：此"不是我"无法用元数据佐证，仅为本人陈述。要真正区分须靠 `git reflog`（各人本地、不中心化）或提交时间窗与各人活动日志对时 ⇒ **建议立规矩：提交 message 里带 `member_name`**，否则「谁推的」永久无法查证。

---

## 4. 顺带闭合的两条口径事实（供 v3 引用）

- **`round 0` 不计 = 无影响**：排除后相邻对仍 125、分布不变 ⇒ 证实「`round 0` 是纯预热轮、0 相邻对」，此排除项对 `gap` 口径**无约束力**。
- **`thread 总条数 ≥2` = 非约束条件**：过滤后仍 125、逐条相同 ⇒ v3 把它标为「非约束条件」**成立**（66 线程中 34 个仅 1 条，但那些线程里的 MSG 不构成带 `reply_to` 的相邻对）。

---

## 5. 声明

- 本件只核数值与提交关系，**不改任何判定口径、不改阈值、不动 `v2/refs/` 内容**。
- `125 / 0.3840` 作为判据口径（§1.1 ①）**已独立复现，与 v3 一致**。
- 三值（`93` / `88` / `105`）均已同屏，**本件不采纳任何一个**，仅定位差异来源。
