# D9k 配置同源守卫（`arm_config_guard.py`）· 交付与自检

> **件头两条**
> **① 任务载体**：本件依 **Leader 2026-10-30 06:12:05 消息**执行；所引卡号 `#T-D9K-REPORT` **在任务库中不存在**（`view_task get` → Task not found；`list(pending)` → No tasks found）；一页纸件亦按同一授权交付。**以消息为准**。
> **② 定位**：把 D9 线一页纸 §2 边界第 1 条（"两臂 `code_sha` 不同 ⇒ 差值只是观测"）从**口头纪律**变成**一条命令的判定**。

- 作者：`repro-verifier`｜2026-10-30｜**只落盘不提交**
- 工具：`tools/metrics/arm_config_guard.py`
- 输入：两臂**目录**（各含 `meta.json` + `run.jsonl`）；**只读**

---

## 0. 为什么必须做这个工具：`config_digest` **不能**判同源

实测 D9 线四臂的 `WORLD_INIT`，**`fingerprint` 与 `config_digest` 全部相同**：

| 臂 | code_sha | fingerprint | config_digest |
|---|---|---|---|
| `narr-off-20261030` | `47a7da9e…` | `sha256:a871e36c…` | `sha256:58485c06…` |
| `narr-on-20261030` | `47a7da9e…` | 同上 | 同上 |
| `run_d9_a1` | `05636bc…` | 同上 | 同上 |
| `run_d1_f6off` | `d7d1d93f…` | 同上 | 同上 |

⇒ **`config_digest` 不含 prompt 文本，也不含 env 级 override**。若拿它当"同源"证据，会把
**prompt 不同、env 不同**的两臂误判为可比（D9 线正因此作废过一条结论）。
**故本工具以 `meta.code_sha` 为主判据**，`fingerprint/digest` 仅作旁证并显式标注此局限。

## 1. 输出与判定（写死）

| 档 | 条件 | 退出码 |
|---|---|---|
| **`SAME_CONFIG`** | 两臂 `code_sha` 相同 **且** `provider`/`model` 相同 | **0** |
| **`DIFFERENT_CODE`** | `code_sha` 不同（并额外报 **prompt 收尾指令是否同源**） | **2** |
| **`CANNOT-VERIFY`** | `meta.json`/`run.jsonl` 缺失、`code_sha` 缺失、或 `code_sha` 不同但 git 对象不可得 | **3** |

同时报出：`code_sha / provider / model / seed / n / rounds / fingerprint / config_digest / engine_version`，
以及**一句"哪些结论因此不可用"**：

- `SAME_CONFIG` ⇒「两臂同源，可作对照；**是否单变量仍取决于 env / 运行时 override**」
- `DIFFERENT_CODE` ⇒「**任何跨臂差值只能作观测，不得归因于任一变量**；以该差值为主结论的件不可发布、不可作判据依据」
- `CANNOT-VERIFY` ⇒「**不得宣称两臂可比**，须先补齐 meta/WORLD_INIT 或提供可比 commit」

## 2. 三用例实测（含退出码）

**A. D9i 两臂（同 `code_sha`，只差 env）⇒ `SAME_CONFIG`，rc=0**
```
code_sha 相同: True ｜ provider/model 相同: True ｜ seed/n/rounds 相同: True
判定：SAME_CONFIG —— 两臂 code_sha 相同、provider/model 相同
影响：可作对照；但**是否单变量仍取决于 env / 运行时 override**（digest 相同不代表 env 相同）
```

**B. D9g 两臂（`05636bc` vs `d7d1d93f`）⇒ `DIFFERENT_CODE`，rc=2 —— 且工具自动指出 prompt 不同源**
```
code_sha 相同: False ｜ prompt 收尾指令同源: **False**
  A 有 2 条 / B 有 3 条；差异条目含 B 侧新增的两条「不要用括号…写动作、神态或心理旁白」与 A 侧「请用一句话自然地说点什么。」
判定：DIFFERENT_CODE —— code_sha 不同，prompt **不同源**
```
> 这正是 D9g 那条"两臂不可合并"的机械证据：**不是凭臂名，是比 prompt 行**。

**C. `mock_d9c_recent` / `mock_d9c_oldest`（无 `meta.json`）⇒ `CANNOT-VERIFY`，rc=3**
```
输入缺失: ['…/mock_d9c_recent_n16r84_seed42/meta.json 缺失或不可解析', '…/mock_d9c_oldest_n16r84_seed42/meta.json 缺失或不可解析']
判定：CANNOT-VERIFY —— 输入不全
```

## 3. 与 D9 线一页纸的挂接

本工具是 §2 边界第 1 条的**执行侧**：任何"两臂对照"的件，**引用前先跑一次**；`DIFFERENT_CODE` 者，
其差值只能写"观测"，**禁止**写"因为 X 导致 Y"。建议在跑批流水线里把它当**前置闸门**（rc=2/3 即拦下）。

## 4. 局限（随工具引用）

1. **prompt 比较依赖正则抽取**：只抓 `agent.py` 里 `+ "\n…"` 形态的收尾指令。若将来提示词改成
   常量表 / 多行拼接 / f-string，本工具会**漏抓**（此时"prompt 同源"结论应降级为不可判）。
2. **看不到 env**：env 不落 `meta.json`（D9i 两臂的差别就在 env），因此 `SAME_CONFIG` **只保证"代码同源"**，
   **不保证"单变量"**；需要 env 证据时须另取 `switch_proof` / `launch_cmd`（有则更好，无则记不可判）。
3. **git 对象缺失 ⇒ 降为 `CANNOT-VERIFY`**（不猜）。
4. **不比 `prompt_sha` 之类外部指纹**：若将来有独立 prompt 指纹字段，应优先用它（比正则更硬）。

## 5. 复算命令

```bash
# A：同代码（D9i）
python3 tools/metrics/arm_config_guard.py \
  --a v2/evidence/narr-off-20261030 --b v2/evidence/narr-on-20261030 ; echo "rc=$?"   # rc=0

# B：不同代码（D9g）
python3 tools/metrics/arm_config_guard.py \
  --a v2/evidence/run_d9_a1_n16r84_seed42 --b v2/evidence/run_d1_f6off_seed42_n16r84 ; echo "rc=$?"   # rc=2

# C：缺 meta（mock D9c）
python3 tools/metrics/arm_config_guard.py \
  --a v2/evidence/mock_d9c_recent_n16r84_seed42 --b v2/evidence/mock_d9c_oldest_n16r84_seed42 ; echo "rc=$?"   # rc=3

# 可选：结构化输出 / 跳过 git
python3 tools/metrics/arm_config_guard.py --a <A> --b <B> --json /tmp/guard.json
python3 tools/metrics/arm_config_guard.py --a <A> --b <B> --no-git
```

## 6. 不做

- 不改任何臂的 `meta.json` / `run.jsonl`；不改引擎；不跑批；不 commit；
- 不判"哪个臂更好"，只判"是否同源 / 能否比较"。
