# preflight-gate 交付记录：串行纪律代码闸

- 任务：#preflight-gate（life-engineer）
- 分支：`feat/scene-anchor`（已 push，新建 origin/feat/scene-anchor 跟踪）
- commit sha：`f8d95f07518ae7c2cf31e77b896ad9aed55543da`（父 3bb698a；fetch 后确认与 origin/master(3bb698a) 无冲突）
- 前置 sha 校验：`git rev-parse HEAD` = f8d95f07518ae7c2cf31e77b896ad9aed55543da

## 1. 改动文件（仅 tools/，未触碰 code/life|orchestration|config|engine，未改进指纹配置）

- 新增 `tools/d5/preflight.sh`（可执行）
- 修改 `tools/d2/run_batch.sh`：参数校验后插入
  `bash "$ROOT/tools/d5/preflight.sh" --tag run_batch || exit 9`
  原有退出码语义不变（2/3/4/6/7 保持，新增 9 仅代表 preflight 失败）

## 2. preflight.sh 行为

1) 三重 pgrep -f 并发检查：`orchestration[[:space:]]+run` / `run_batch` / `nightly\.py`，
   任一命中即失败。排除项：pgrep 自身、`$$`、**整条祖先链**、preflight 自己的 `$(...)` 子 shell
   （子 shell 继承父 cmdline 但 pid 不同，不排除会导致 run_batch 调用时把自己判成并发——实测踩到并修复）。
2) 调 `tools/d5/check_clean_tree.py`（rc1=FAIL、rc2=UNDECIDABLE 均按失败），终端只摘 BLOCKING 行。
3) 锚点留存：写 `v2/evidence/preflight/preflight_<UTC>_<sha8>[_tag].log`，
   含 ts_iso / branch / HEAD / self_pid / ancestors / 三项检查结果 / verdict。
4) 失败一律 `exit 9`，成功打印一行 PASS 摘要。

用法：`bash tools/d5/preflight.sh [--repo <path>] [--log-dir <dir>] [--tag <name>] [--quiet]`

## 3. 自证原文

正例（提交前 sha 3bb698a）：
```
$ bash tools/d5/preflight.sh --tag selfproof_pass
PASS preflight sha=3bb698a9(feat/scene-anchor) ts=2026-10-23T04:06:59+08:00 concurrency=0 frozen_tree=clean log=.../preflight_20261022T200659Z_3bb698a9_selfproof_pass.log
RC=0
```
正例（提交后 sha f8d95f07，终验）：
```
PASS preflight sha=f8d95f07(feat/scene-anchor) ts=2026-10-23T04:07:30+08:00 concurrency=0 frozen_tree=clean log=.../preflight_20261022T200730Z_f8d95f07_post_commit.log
RC=0
```

负例 A：并发（假 run_batch + 假 orchestration run，真实存活进程，/tmp 下，非仓库污染）
```
2597691 /bin/sh /tmp/pfself-11247/run_batch 60
2597692 /bin/sh /tmp/pfself-11247/orchestration run 60
[preflight] FAIL exit=9 reasons=concurrency:orchestration_run=1 concurrency:run_batch=1
RC=9     清理后残留 0 个
```
负例 B：nightly.py 并发
```
2597821 /bin/sh /tmp/pfself-11247/nightly.py 60
[preflight] FAIL exit=9 reasons=concurrency:nightly_py=1
RC=9     清理后残留 0 个
```
负例 C：冻结区脏（瞬时 .py 探针，即刻删除）
```
?? code/life/__preflight_dirt_probe.py
  BLOCKING ?? code/life/__preflight_dirt_probe.py
[preflight] FAIL exit=9 reasons=dirty_frozen_tree(rc=1)
RC=9
清理后 git status --porcelain -- code/life code/orchestration code/config code/engine → 空
```

## 4. 集成验证（接入 run_batch 无回归）

正常路径（mock 2 agents × 2 rounds，OUT=/tmp/pf_smoke_run，exit 0）：
```
PASS preflight sha=3bb698a9(...) concurrency=0 frozen_tree=clean
[d2] run: python3 -m orchestration run --life --seed 42 --agents 2 --rounds 2 --out /tmp/pf_smoke_run/run.jsonl --flush-every 2
[life] n_agents=2 rounds=2 events=63 ...
[meta] events=63 llm_calls=6 provider={'mock': 6} model={'mock-1': 6}
[d2] self-check wc -l=63 meta.events=63
[d2] OK
```
并发负例（已有 run_batch 在跑时再启动 run_batch.sh）：
```
[preflight] FAIL exit=9 reasons=concurrency:run_batch=1
RC=9   → 输出目录未创建（ls: cannot access ...: No such file or directory），即 mkdir 之前被拦
```

## 5. 取舍与局限

- 取舍：判定接入 run_batch 回归风险低（mock 全流程照旧 + 并发时精准拦截且在 mkdir 前），故完成接入，未退化为"仅独立脚本"。
- 局限：并发判定的口径是全机 pgrep（与其他 worktree/其他仓库的同名进程也会命中），这是有意的保守取向；
  若将来出现误伤，应加 `--repo` 范围收敛或改 cwd 过滤，而不是放宽检查。
- 证据文件位置：`v2/evidence/preflight/`（该目录被 check_clean_tree 归为非阻断；本轮未提交 log 文件，仅提交 tools/ 改动）。
- 自证脚本一次性，未入库；完整终端转录：`v2/evidence/preflight/preflight_selfproof_3bb698a9.txt`。
