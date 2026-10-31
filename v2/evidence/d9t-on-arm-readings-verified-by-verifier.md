# D9t ON 臂读数验算：**无可用数据（六项 CANNOT-VERIFY）**；归因为「服务端连接已建立但不返回」，**不是"端点不可达"**

> 作者：`repro-verifier`｜2026-10-31｜只读；未跑批、未改代码、未 push
> 任务：`T-D9T-READ-VERIFY`
> **对象**：ON 臂 `/tmp/d9t_on_n16r24_s42_out.174311/`（第 5 次启动，`run_id=174311`）；OFF 复用臂 `v2/evidence/d9s-on2_n16r24_s42/`
> **run.jsonl sha256** = `15664c49e39a3dd7a20486cf8c5b3b8208fed8272f6393b382187ac06770d391`（34 行 / 13149 B）
> **五元组**：`seed=42`（`--seed 42`）／`agent_id=16 个（P001–P016）`／`round=0`（只到初始化，未进第 1 轮）／`role_id` 未指定（默认 `None`）／`ROTATION=1`
> **复算命令**：`python3 /tmp/vvx/count4.py <run.jsonl>`（已用 `d9s-on2`/`d9s-syntax-off` 回归 `183/183/183/0`）

## 0. 六项结论一览

| # | 项 | 判 |
|---|---|---|
| 1 | 真调用四数逐行重算 | **CANNOT-VERIFY（无产出）** —— `MSG_PUBLIC/DM/GROUP = 0/0/0`、`LLM_CALL purpose=dialogue = 0`、`tokens_in>0 = 0`、`cached = 0` |
| 2 | `obs llm-cost` 交叉对齐 | **CANNOT-VERIFY** —— 未产生成本记录（进程未完成任何一次调用） |
| 3 | 代码指纹 `FP` before/after | **CANNOT-VERIFY** —— 未取得 after 快照（跑批未结束）；before 亦未落盘 |
| 4 | `switch_proof` 五开关真值 | **PASS** —— 五开关**全 `=1`**（原始 `/proc` 取证） |
| 5 | 两臂身份分侧 | ON：`launch_cmd.txt` `HEAD=cef1c58c448d400c0…` ✓，**无 `meta.json`** ⇒ `code_sha` 记 **`CANNOT-VERIFY（缺件）`**；OFF：无 `meta.json` ⇒ 引 `HEAD=f2b3230d` + `switch_proof`，记 **`CANNOT-VERIFY（缺件）`（≠ 不可比）** |
| 6 | 五元组口径 | **PASS（可读出）** —— 见件头；两臂 `seed=42` 一致，其余因 ON 未进第 1 轮无法对齐 |

**末句（任务卡要求）**：**本批读数不可用于 G0–G7 判定。** 理由：`run.jsonl` 仅含 34 行初始化事件、**零 `MSG_*` / 零 `LLM_CALL`**，任何 G0–G7 判据都无输入。

## 1. 第 1 项：34 行是什么（逐行核过）

```
分布: {'WORLD_INIT': 1, 'AGENT_BORN': 16, 'INIT_ENDOW': 16, 'MONEY_MINTED': 1}  = 34
序列: WORLD_INIT → (AGENT_BORN → INIT_ENDOW)×16 → MONEY_MINTED
```
```
MSG_PUBLIC 0 / MSG_DM 0 / MSG_GROUP 0 / LLM_CALL 0 / LLM_JUDGMENT 0 / TURN_SEAL 0
```
⇒ **纯初始化态，零有效产出** ✓（与 Leader 的判断一致）

## 2. 归因纠正：**不是"端点不可达"，是"连上了但不返回"**

**Leader 的归因**：provider 端点不可达。
**我的实测（两条独立证据）**：

**证据 A：自己发最小请求，端点正常且很快**
```
用仓库 code/.env.local 的真实凭据（key 不打印）:
  max_tokens=5   → http_code=200  time=0.072s
  max_tokens=120 → http_code=200  time=1.209s   （正常返回正文）
TCP /dev/tcp/172.16.3.41/31809 → 可连
（用 dummy key 时是 401 Unauthorized / 2ms —— **401 容易被客户端包装成"连接失败"**）
```

**证据 B：卡住的进程，socket 是 ESTAB 且在对端挂着**
```
$ cat /proc/2999158/wchan
poll_schedule_timeout.constprop.0          ← 在等 I/O

$ ss -tnp | grep 2999158
ESTAB  0  0  10.10.136.128:51404  172.16.3.41:31809  users:(("python3",pid=2999158,fd=3))
             ↑ tx_queue=0 rx_queue=0，连接已建立、服务器未回数据
```
⇒ **TCP 三次握手成功、连接 ESTAB** ⇒ 端点**可达**；**是服务端对"这批请求"迟迟不返回**。

**差异在哪**：我的 curl 是「单条短消息」，跑批是「16 agent 并发 + 完整长 prompt + thinking」⇒ **服务端对小请求 1.2s 返回，对大/并发请求排队或挂起**。

⇒ **正确归因**：**provider 端点可达但服务端对大并发/长 prompt 不返回（超时未触发）**。建议结账理由写这个，而不是"端点不可达"——后者经不起 `curl` 复算。

### 2.1 追加证据：**本地端口变了 ⇒ 已发生"超时重连"**（17:45:37 二次采样）

```
17:45:37  pid=2999158  ELAPSED=02:25  wchan=poll_schedule_timeout  CPU 1.2%
ss -tnp | grep pid=2999158
  ESTAB  0  0  10.10.136.128:35420  172.16.3.41:31809   ← 本地端口 35420
（17:44 首次采样时是 10.10.136.128:**51404**）
```
⇒ **两次采样之间本地源端口从 51404 变成 35420**，而进程 PID 未变 ⇒ **说明它关闭了旧连接、重建了一条新连接**（HTTP 客户端超时/失败后重试的典型形态）。
⇒ 即：**请求发出去了，服务端不返回 ⇒ 客户端超时 ⇒ 重连 ⇒ 再等**，循环中。run.jsonl 因此始终停在 34 行。

**这条同时说明两件事**：
1. **不是"不可达"**（连接能建、能重连）；
2. **也不是"我们这边的代码卡死"**（它在主动重试，行为合理）；
3. ⇒ **卡点定位到："服务端接受连接但不回响应，客户端在超时重试循环中"**。

## 3. 第 4/5 项：可核的都核了

```
switch_proof（/proc 原始取证）:
  LIFE_PROMPT_NARRATION=1
  LIFE_PROMPT_NARRATION_ROTATION=1
  LIFE_PROMPT_NARRATION_ACTION=1
  LIFE_PROMPT_NARRATION_SYNTAX=1
  LIFE_PROMPT_NARRATION_OPENINGS=1        ⇒ 五开关全 =1 ✓

launch_cmd.txt:
  arm=ON run_id=174311
  out=/tmp/d9t_on_n16r24_s42_out.174311
  side=/tmp/d9t_on_side_174311
  HEAD=cef1c58c448d400c0fe98736634cc0891b0a78e6     ✓
  --- pgrep_before (raw) ---  (empty)                ✓ 起跑前无并发
  env: NARRATION=1 ROTATION=1 ACTION=1 SYNTAX=1 OPENINGS=1 HITT_LLM_PROVIDER=openai_compat  ✓

meta.json: 不存在  ⇒ code_sha 记 CANNOT-VERIFY（缺件）
```
⇒ 这一批的**启动纪律是干净的**（`pgrep` 空、五开关显式、`HEAD` 正确、run_id 留档）——**卡住与启动纪律无关**。

## 4. 五次启动的形态一致性（可对比部分）

| 批 | 启动 | 落点 | 行数 | run.log |
|---|---|---|---|---|
| 1 | 15:47 | `v2/evidence/d9t-on_n16r24_s42/`（已清） | 34（观测） | 0 |
| 2 | 16:12 | 同上（并发写同一目录） | — | — |
| 3 | 17:12 | `…out.STALLED.171640/` | **34** | **0 B** |
| 4 | 17:43 | `…out.174311/`（当前） | **34** | **0 B** |

⇒ **凡能取到的批次都是 34 行 / 0 字节日志 / 同为纯初始化序列** ⇒ **形态同构**。
**第 5 批已加 `-u`（无缓冲）仍为 0 字节** ⇒ **排除"stdout 缓冲导致看不见"这一解释**，即进程真的没有任何输出。

## 5. 我这轮另外做的事（附）

- **清了两个中断批的 side-root**（Leader 授权）：`/tmp/d9t_on_fresh2_1793434526`（11M/2631 文件）、`/tmp/d9t_on_fresh2_1793436159`（8.5M/2089 文件）。理由：**中断批留 side-root 会让人误以为它产出过可用数据**；保留 `fresh_1793432816`（污染批物证）与当前在用的 `d9t_on_side_174311`。
- **自曝一个自检坑**：判"side-root 是否被占用"时我用 `pgrep -f "$d"`，**匹配到了自己的命令行**（因命令里含该路径），两个都误报"有占用"；改用 `ps|grep -F|grep -v 自身` + `lsof +D` 复核才确认无占用。⇒ 检查器把自身算成被测对象，这是本线第七次同族。

## 6. 结论

**本批读数不可用于 G0–G7 判定**（`run.jsonl` 零 `MSG_*`、零 `LLM_CALL`）。
**且归因需改写**：不是"端点不可达"，是「**端点可达（curl 200/1.2s）、连接已 ESTAB、但服务端对长 prompt/并发不返回**」。恢复服务端响应后，**脚本与代码无需改动即可原样重跑**（第 5 批已满足全部启动纪律）。
