# 对照臂「期望值自检」Runbook（arm-state-check）

> 作者：repro-verifier ｜ 2026-10-22 ｜ 关联：四次事故（mock 静默回落 / 开关未接线 / mock 验不出提示词 / 树含旧变量）
> 脚本：`tools/d9/arm_state_check.py`（只读，秒级）
> 与 `v2/refs/batch-hosting-runbook.md`（T271，cgroup 逃逸/重启存活）互补：那份解决「进程活不活」，本文解决「**跑出来的东西是不是该树该有的样子**」。

**核心原则**：用「**行为是否符合该树期望**」替代「配置文件/环境变量写了什么」。声明一律不作数。

---

## 1. 起跑前（缺一不起跑）

```bash
git status --porcelain -- code/ ; git rev-parse --short HEAD          # 树干净 + landing 明确
pgrep -fa "orchestration run|judge_run" || echo "无并发，可起跑"        # 禁并发重负载
```

并把本批的「**树期望**」写成 JSON（例如 A0 树 `{"paren_rate":0.70,"len_p50":39}`；
A1 措辞树 `{"paren_rate":0.0,"len_p50":29}`；mock 树 `{"len_p50":14}` 之类）。

## 2. 起跑后 1 分钟内（**强制步骤 + 留痕**）

> **不做 pre-commit 钩子**（钩子在提交路径上，误判会阻断所有人的正常提交）；改为**强制步骤 + 留痕**：
> 起跑后 1 分钟内跑一次，把输出**贴进该批目录的 `arm_state_check.txt`**。留痕比拦截更合适。

```bash
python3 tools/d9/arm_state_check.py \
  --run <RUN_DIR>/run.jsonl \
  --tree-expectation '{"paren_rate": 0.70, "len_p50": 39}' \
  --expect-struct '{"msgs": 686, "threads": 206, "ge3": 90}' \
  --expect-provider openai_compat \
  [--expect-env HITT_D12_DETAIL=1 --expect-behavior '{"paren_rate": {"min": 0.30}}'] \
  --tolerance 0.05 | tee <RUN_DIR>/arm_state_check.txt
```

**口径提醒（否则两个数会对不上）**：C1 全部指标基于**前 `--first-n` 条（默认 20）**、`len_p50` 是**原始 body 长度（不去括号）**；C4 的 `msgs/threads/ge3` 是**全批**。
A0 参考值：前 20 条 raw p50 = **38.5**（去括号 33.0）；全批 raw p50 = **54.0**（去括号 41.0）；A0 前 34 回合子集 = **48.0**。看到 38.5/48/54 先问「哪个子集、是否去括号」。

| 判据 | 抓什么 | 规则 |
|---|---|---|
| **C0 provider** | mock 静默回落 | `LLM_CALL.payload.provider` 只含期望值 |
| **C1 首 N 条指标** | mock 验不出提示词 / 树含旧变量 | rate 用绝对差、长度计数用相对差，超 tolerance 即 FAIL |
| **C2 seals/初始化** | 续跑污染 / 断链 / 双初始化 | seal 单调不重复；`WORLD_INIT` 唯一 |
| **C3 开关↔行为** | 开关未接线 | 声明 `--expect-env` **必须**同时给 `--expect-behavior`，否则 FAIL（"只声明 env 不算"） |
| **C4 结构** | 批未跑完 / 规模不符 | `msgs/threads/ge3` 相对差 ≤ tolerance |

`CANNOT-VERIFY ≠ PASS`：未给期望的判据会明确标出，不默认放行。

## 3. 负例回归基线（2026-10-22 实测，工具应报红）

| 批次 | 现象 | 工具表现 |
|---|---|---|
| `run_d12a_base_seed7_n16r24_INVALID_confounded` | 树含禁旁白 ⇒ 旁白 0% | `C1 FAIL`：`paren_rate 实测=0.0000 期望=0.7` |
| `mock_trigA2_INVALID_switch_not_applied_n16r84_seed42` | 开关未生效 + mock 回落 | `C0 FAIL`（`provider={'mock':3383}`）+ `C3 FAIL`（`paren_rate=0.0 < min 0.3`） |
| `run_d12a_treat_seed7_n16r24_INVALID_incomplete` | 只 4 seal / 37 msg | `C4 FAIL`：`msgs 37 vs 600`、`threads 23 vs 200` |
| 只声明 env 不给行为 | — | `C3 FAIL`：「只声明 env 不算，必须验行为」 |
| **正例** `run_d2_after_n16_seed42`（A0） | — | C0–C4 全 PASS（`paren_rate=0.70`、`len_p50=38.5`、`msgs=686`、`threads=206`、`ge3=89`） |

## 4. 出批后固定动作

```bash
wc -l <RUN_DIR>/run.jsonl                      # 与 meta.events 对拍
cd code && python3 -m obs llm-cost --log <RUN_DIR>/run.jsonl --require-provider openai_compat ; echo rc=$?
#   ⚠ 别用管道接 tail/head——管道会吃掉退出码
python3 tools/d9/arm_state_check.py --run <RUN_DIR>/run.jsonl | grep -A1 C2   # 轮数以 TURN_SEAL 覆盖为准
```

## 4.5 托管方式（`setsid` 不够，需 `systemd-run`）

> **`setsid` 只脱离会话，不换 cgroup** ⇒ 平台重启 `jiuwenswarm.service` 时，同 cgroup 内的跑批进程**仍会被连坐回收**（今天三次"被杀"由此而来，不是玄学）。
> 因此"跑批期间别做长等待调用"只是缓解，**根治要换托管方式**：把跑批放进 **transient unit**（`system.slice` 下、与平台服务平级）。

```bash
# 长跑批托管模板（transient service，立即 detach、由 PID 1 托管、可查可停）
LOG=/tmp/batch-$(date +%Y%m%dT%H%M%S).log
systemd-run --unit=<batch>-<run_tag> --collect \
  --property=MemoryHigh=6G --property=MemoryMax=8G \
  bash -lc "cd <REPO>/code && python3 -m orchestration run --life --seed 42 --agents 16 \
            --rounds 84 --out <RUN_DIR>/run.jsonl --flush-every 2 --side-root <SIDE_DIR> \
            >> $LOG 2>&1"

# 自查三件
systemctl status <batch>-<run_tag>.service --no-pager | head -5
ls -la <RUN_DIR>/run.jsonl            # mtime 应 ≥ 起跑时刻
cat /proc/$(systemctl show -p MainPID --value <batch>-<run_tag>.service)/cgroup   # 应不在 jiuwenswarm.service 内
```

> 命名：`--unit=t271-<name>` 与既有托管 runbook（T271）保持一致，便于 `systemctl list-units 't271-*'` 统一查看。
> 日志落 `/tmp`（不进 git）；跑完把 `run.jsonl` + `meta.json` + `arm_state_check.txt` 归档进 `v2/evidence/<RUN_DIR>/`。

## 5. 纪律（事故教训，均实际发生过）

1. **监控/观察命令必须脱离跑批的进程组与会话**：`setsid`/`nohup` 解决"进程组连坐"；若还要求平台重启不杀，需按 T271 用 `systemd-run`（`setsid` **不换 cgroup**，见 hosting runbook §2）。
2. **同目录重跑前清空或改名残料**——只含初始化记录的 `run.jsonl` 极易被误当"在跑"。
3. **判据分级**：`FAIL-命名/口径`（数据可用，改标签）vs `FAIL-数据/证据`（结论不可用）；不写级别会把"命名错"误读成"数据废"。
