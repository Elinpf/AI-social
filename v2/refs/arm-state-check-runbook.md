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

## 2. 起跑后 1 分钟内（秒级自检）

```bash
python3 tools/d9/arm_state_check.py \
  --run <RUN_DIR>/run.jsonl \
  --tree-expectation '{"paren_rate": 0.70, "len_p50": 39}' \
  --expect-struct '{"msgs": 686, "threads": 206, "ge3": 90}' \
  --expect-provider openai_compat \
  [--expect-env HITT_D12_DETAIL=1 --expect-behavior '{"paren_rate": {"min": 0.30}}'] \
  --tolerance 0.05
```

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

## 5. 纪律（事故教训，均实际发生过）

1. **监控/观察命令必须脱离跑批的进程组与会话**：`setsid`/`nohup` 解决"进程组连坐"；若还要求平台重启不杀，需按 T271 用 `systemd-run`（`setsid` **不换 cgroup**，见 hosting runbook §2）。
2. **同目录重跑前清空或改名残料**——只含初始化记录的 `run.jsonl` 极易被误当"在跑"。
3. **判据分级**：`FAIL-命名/口径`（数据可用，改标签）vs `FAIL-数据/证据`（结论不可用）；不写级别会把"命名错"误读成"数据废"。
