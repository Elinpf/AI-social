# ABORTED — Arm-T 第一次起跑（2036）

> **本目录不得用于任何读数、演示或结论。** 只作失败留痕。

## 事实

- 起跑：2026-10-20T20:24:43 (+08:00)，HEAD `e300c1f`，`HITT_DIALOGUE_REPAIR=1`
- 命令：`bash tools/d2/run_batch.sh --out-dir v2/evidence/run_r6_treat_n16_seed42 --seed 42 --agents 16 --rounds 84 --side-root /tmp/r6_treat_side --flush-every 2`
- 终止：`/tmp/r6_treat_console.log` 末行为 **`Terminated`**（SIGTERM，非异常栈、非代码错误、非端点错误）
- 规模：`run.jsonl` 仅 **34 行**，最后一条 `MONEY_MINTED round=0 seq=33`；**无 `meta.json`**
- 时间：20:36:29 复查时进程已不存在（起跑后约 11 分钟内死亡，具体时刻未捕获）

## 归因（已排除 / 未排除，如实写）

- 已排除：代码错误（无 traceback）、LLM 端点不可用（起跑前 `/v1/models` 200、obs 验真 rc=0）、磁盘/权限（文件正常写入）、OOM（无 dmesg OOM 记录）
- 最可能：**启动方式未能与工具会话的进程组彻底脱离**，会话/调用结束时进程组收到 SIGTERM（与 A0 的 `run_d2_after_resume_ABORTED` 18:13 被杀同族：都是"批进程被外部信号打断"，不是代码问题）
- 本次加固：改用 `setsid --fork`（新建会话并 fork，父进程立即退出、子进程 reparent 到 init），并在起跑后**校验进程 SID 与调用方 shell 的 SID 不同**

## 处置

- 目录保留为 ABORTED，**不续跑、不补 meta、不裁成"看起来完整"**
- Arm-T 从零重跑（同 HEAD、同开关、同规格），重跑目录 `v2/evidence/run_r6_treat_n16_seed42`
- 本次 ABORTED 消耗约 34 条事件，成本可忽略；不计入任何统计
