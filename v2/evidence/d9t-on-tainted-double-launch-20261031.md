# D9t ON 臂首次起跑作废：同命令被启动两次，写同一 out 与同一 side-root

> 作者：TeamLeader｜2026-10-31 16:1x｜**处置记录**（不是判定件）
> 发现者：`repro-verifier`（16:13 现场取证）｜Leader 独立复核并执行处置

## 1. 事实

| PID | 启动时刻 | 说明 |
|---|---|---|
| `2732286` | **15:47:00** | 第一次启动 |
| `2791286` | **16:12:34** | 第二次启动（**同一命令、同一 `--out`、同一 `--side-root`**） |

两者父进程均为 `bash /tmp/launch_d9t_on.sh` ⇒ **同一个启动脚本被跑了两次**。

`launch_cmd.txt` / `switch_proof.txt` 的 mtime 均为 16:12:3x ⇒ **被第二次启动覆盖**，第一次运行的执行层取证已丢失。

## 2. 处置（Leader 执行，16:1x）

```bash
kill 2732286 2791286                       # 两个都停；随后 pgrep -af "orchestration [r]un" 为空（已核）
mv .worktrees/d9t-openings-2/v2/evidence/d9t-on_n16r24_s42 /tmp/D9T_ON_TAINTED_1793434444
mkdir -p .worktrees/d9t-openings-2/v2/evidence/d9t-on_n16r24_s42   # 备用空目录
```
**留档不删**：污染批在 `/tmp/D9T_ON_TAINTED_1793434444`（含 `run.jsonl` 9688 行、被覆盖的 `launch_cmd.txt` / `switch_proof.txt`、0 字节 `run_batch.log`）。

## 3. 为什么这批不能用于判定（三条，同屏）

1. **两个进程写同一文件** ⇒ 行级来源不可辨。即使当时"无重复 seq"，也只说明**还没写到冲突区**，不是"没冲突"；
2. **`launch_cmd.txt`/`switch_proof.txt` 已被第二次启动覆盖** ⇒ 第一次运行的**执行层取证丢失**（与 D9s 那次 `switch_proof` 事故同型：**取证文件会被下一次启动改写**）；
3. `HEAD=cef1c58`、五开关真值现在只能证明**第二次启动的**，**不能证明"写 `run.jsonl` 那一次的"**。

## 4. 根因与修法

**根因**：`/tmp/launch_d9t_on.sh` **没有 `pgrep` 守门**（仓库里 `launch_arm.sh` 有：`pgrep -af "orchestration [r]un"` 非空即 `exit 21`）。
⇒ **守门脚本没被使用，等于没有守门。**

**修法**：①启动脚本前置 `pgrep` 非空即 `exit 21`；②启动前 `pgrep` 原始输出必须贴进 `launch_cmd.txt`（现在这份只记录了 env，没有记录"起跑时是否已有在跑"）；③`launch_cmd.txt`/`switch_proof.txt` **改为只写不复写**（带 run-id 后缀），否则取证永远会被下一次启动覆盖。

## 5. 状态

- 两个进程已停，`pgrep` 为空；
- 污染批留档于 `/tmp/D9T_ON_TAINTED_1793434444`；
- **ON 臂尚未取得可用于判定的数据**；起跑需重做（单进程、全新 `side-root`、`pgrep` 守门）。
