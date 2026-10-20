# Arm-T 起跑记录（第二次，HEAD 6074502）

- 起跑时刻：**2026-10-20T20:38:36 (+08:00)**
- HEAD：`6074502f4062891d05e1057df08243d11c3cb79d`（两次 rev-parse：20:37:33 / 20:37:43 同值 ⇒ 安静窗口成立）
- 开关：`HITT_DIALOGUE_REPAIR=1`；config 保持提交态 `enabled=false`（sha `f04355716d494f7b1a7236865c1bc3c6d3e13c9b250143a066bc1dd5ea8e9eec`）
- 启动方式：`setsid --fork`（新建会话并 fork，父进程立即退出）——加固点：避免上一次被 SIGTERM 打断
- 第三方快照：`team-workspace/artifacts/reports/s0a-snapshot-T-2038.md`，sha256 `d8c7f20134c8345dbe9c3b647699f20a72c77bc9f33f9868f3e18c7027c2e8ab`
- 我的快照记录：`arm_T_open_record.json`（rc=0）

## 两臂代码身份承诺

**两臂均以 `6074502` 为代码身份**；Arm-C 起跑前必须复核 `tools_freeze_pin.json` 12 项 sha 与 HEAD 未变，任一不符 `rc=5` 拒开。

## 批窗内已发生的 `code/` 写入（如实记录）

- `git log --oneline e300c1f..6074502 -- code/` → `024c519`、`6074502`，命中文件全在 `code/frontend/`（README +9/-1、sample/.../threads.json +1、tools/d7_after_pipeline.sh +93）
- `git diff --stat e300c1f 6074502 -- code/{life,orchestration,config,engine}` → **空**（引擎侧零改动）
- 定性：按 `check_clean_tree` 前缀**不阻断**；按冻结令原文**属批窗内写入 `code/`，属流程违规**（Leader 20:37 裁定：不阻断、不作废，如实记录不掩盖）

## 度量脚本版本（重要）

- 本轮使用版 `tools/d5/dialogue_metrics.py` sha256 = `5fede53838b183eae48bd3c3f922c17499338d2ae74349f8e444119e5580c6fb`（工作区含他人未提交改动）
- 该改动**只涉及 L-12 拆分为 L-12a/L-12b**（`prompt-linguist` 口径定稿），F-4/F-4b 相关代码**逐字未变**（见下校验）
- 历史锁定版 sha `d7e2da17764eeec2f17b271b045bd8bc03153e79dd98f35ac171ec7ac3f97306`；中间版 `371c9fa18dd3022d8c442a742a0aa3468eb43dcdf0aa3760545cd13443de9751`
- **F 系列读数的跨版本可比性**：三版之间 F-4/F-4b 段落无差异；基线复算会用 `5fede538`（与两臂同版本）重跑并逐字段比对

## F-4/F-4b 段落未被本改动触碰的校验
```
$ git diff -- tools/d5/dialogue_metrics.py | grep -E "^[+-].*(F-4|tension|repair|closed_loop)"
(无输出 ⇒ F-4/F-4b 相关行未被改动)
```
