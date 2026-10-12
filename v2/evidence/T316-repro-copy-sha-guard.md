# T316 反向验证：`repro_resume_cut.sh` 副本根 sha 标记（不再静默复用陈旧副本）

> 作者：release-engineer ｜ 2026-10-13 ｜ 任务：T316（脚枪修，在验证链上）
> 背景：`T315` 只让副本根可覆盖；`[ -d "$CO/code" ] || build` 仍会**无声复用旧 sha 副本** ⇒ 实测造出假 `resume1≠resume2`（`4425cb8d`，清 CO 后复测三文件全等 `8820493f`）。

## 实现（`tools/t271/repro_resume_cut.sh`）
副本根 `CO` 内放 **sha 标记 `$CO/.src_sha`**：
- `CO/code` 不存在 / 无标记 / 标记 `!= 期望 SHORT` ⇒ **WARN + 重建**（`make_batch_copy` 后写标记），**不静默复用**；
- 标记 == 期望 ⇒ 复用（默认行为对同一 sha 不变）。

## 反向验证（分进程；命令见下）
```
T271_REPRO_COPY=/tmp/t271-rc-shatest T271_REPRO_SHA=<SHA> T271_REPRO_ROOT=/root/t271/runs/repro_shatest \
  bash tools/t271/repro_resume_cut.sh 89
```
| 步 | 动作 | 期望 | 实测 |
|---|---|---|---|
| A | 用**旧 sha** `9af5259` 建 CO | marker=旧 | `marker=9af5259` ✓ |
| B | 改用**新 sha** `5b939d8` 跑同一 CO | **WARN + 重建** | `WARN: 标记=9af5259 != 期望 5b939d8 -> 重建`；`marker=5b939d8` ✓ |
| C | **同 sha** 再跑 | 不 WARN（复用） | `WARN 行数=0` ✓ |

⇒ **错 sha 的 CO 必重建/告警（不静默复用）**；同 sha 不变。步骤 A/B/C 的三次 `resume1==resume2==oneshot` 均 yes。

## 依赖方通知
- `kernel-dev`（T314 复验）、`sandbox-test-lead`（T311 守护）—— 已通知：接口未变；指纹在 CO 内，CLI 不变。
