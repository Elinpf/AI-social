# 边界件：`.gitignore:8 **/*.jsonl` 使「臂原始日志从未入 master」——「可复算」此前只是「本机可复算」

> 性质：只读核查 + 规则裁定。发现者：`repro-verifier`（问了一句"`A+B` 的原料在哪"，追下去才发现不是偶发）。作者：Leader。
> 影响面：**本线此前所有臂**，不止 D9m。

## 1. 事实（一次命令整块输出）

```bash
$ git check-ignore -v v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl
.gitignore:8:**/*.jsonl    v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl

$ git ls-tree origin/master --name-only v2/evidence/narr-on-20261030/
（空）

$ ls v2/evidence/narr-on-20261030/
dialogue_metrics.json  meta.json  run.jsonl  narration_stats.json  switch_proof.txt  ...
```

⇒ **本机有 `run.jsonl`，master 上没有**；同理 `d9n-rot-20261030/`、`run_d2_after_n16_seed42/` 等所有臂。
⇒ 因此历史上"复算一致"的表述，严格说都是**「本机复算一致」**，不是**「任何人可复算」**。

## 2. 机制（为什么会静默发生）

`git add <被 ignore 的文件>` **返回 `rc=0`、无 warning、无提示**，文件不进暂存区。
本轮我第一次 `git add` 两个 `run.jsonl` 时即如此：命令成功、`commit` 成功、`push` 成功，**但提交树里没有这两个文件**——直到 R-9 回读 `git cat-file -e origin/master:<path>/run.jsonl` 返回 `exists on disk, but not in 'origin/master'` 才暴露。

**这是第三种同族形态**（前两种：`git status` 假阳性、回读到别的版本）：
- 第一种：**看起来成功、实际没发生**（`git status` 干净但文件被改）
- 第二种：**看到数、但数与本地不同源**（回读到了别的 sha）
- 第三种：**命令成功、对象没进库**（`git add` 静默跳过）

⇒ 三者的共同点：**"操作返回成功"与"目标状态达成"是两件事，只有回读目标状态才能区分。**

## 3. 动作式规则（可复制执行，不是"注意"）

**R-10｜引用任何臂的原始数据前，先验它在不在库里**

```bash
# 通过 ⇒ 可写「已入库可复算」；失败 ⇒ 只能写「本机有、master 无」
git cat-file -e origin/master:<arm_dir>/run.jsonl && echo IN_REPO || echo NOT_IN_REPO
```

配套：
1. **入库原始日志必须 `git add -f`**（绕 `.gitignore:8`），且入库后**必须回读三值**（sha / 行 / 字节 + 与本地 `diff`）；
2. **存在性与同源性是两个问题，必须分开答**（`repro-verifier` 指出）：
   - `cat-file -e` **只答"在不在"**，答不了"是不是同一份"；
   - "是不是同一份"仍须 `sha256sum` + `wc -lc` + `diff`（R-9 四条）。
   ```bash
   arm=v2/evidence/<arm_dir>
   git cat-file -e origin/master:$arm/run.jsonl 2>/dev/null && echo "可复算：在库" || echo "仅本机：master 无"   # 在不在
   # ✗ 反例：git show origin/master:$arm/run.jsonl | wc -c   —— 路径不存在时得 0，与"空文件"同形，无法区分
   # 通过"在不在"之后，仍须：git show … > /tmp/rb && sha256sum /tmp/rb && wc -lc < /tmp/rb && diff -q /tmp/rb <本地>
   ```
3. **件内表述分档**（不得混写）：
   - `已入库可复算`：`cat-file -e` 通过 **且** 仪器 sha + 词表 sha + `--arm` 名三件齐；
   - `本机复算一致·入库不可复算`：`cat-file -e` 失败；
   - 两者**不得合并**为"已独立复算"。
4. **不修改 `.gitignore`**：全局忽略 `*.jsonl` 有其理由（防止跑批中间产物污染）。正确做法是**按件 `-f` 强制入库被引用的臂**，而不是放开规则。

## 4. 当前状态（截至 `446939e`）

| 臂 | `run.jsonl` 是否在 master | 可写表述 |
|---|---|---|
| `d9m-ab-on_n16r24_s42` | **在**（`3359526` 强制入库） | 已入库可复算 |
| `d9m-ab-off_n16r24_s42` | **在**（同上） | 已入库可复算 |
| `narr-on-20261030`（H0） | 不在 | 本机复算一致·入库不可复算 |
| `narr-off-20261030` | 不在 | 同上 |
| `d9n-rot-20261030`（A only） | 不在 | 同上 |
| `run_d2_after_n16_seed42`（A0） | 不在 | 同上 |

## 5. 以后怎么避免（三条，均应写进预登记模板）

1. **预登记阶段就写明**"本实验的原始日志是否入库"（默认否则须显式声明原因）；
2. **判定件的每张臂表加一列** `IN_REPO`（由 §3 命令生成，不手打）；
3. **只有 `IN_REPO=Y` 的行**才允许出现在「可复算」类断言里；`IN_REPO=N` 的行只能出现在「描述性读数」段落。

## 6. 边界

- 本件**不主张把历史所有臂补入库**：34MB/臂 × 数十臂 不划算，且历史臂已被派生 json 固定。**正解是"以后的新臂按 §5 走"，历史臂按 §4 如实标注。**
- 本件**不改变任何既有判定**：它只影响"可复算"这个词的使用范围，不影响任何数值与结论。
