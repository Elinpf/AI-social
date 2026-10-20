# D2 A0 臂 —— 「被杀 + 续跑尝试」中止记录（不作为任何读数，仅审计留痕）

时间线（+08:00）：
- 18:01 起跑 A0（n=16/rounds=84/seed=42/openai_compat，side_root=/tmp/d2_after16_side）
- 18:13 跑到 round 5 完成（flushed 4851 行，末条 TURN_SEAL(5)）后**进程被杀**
  根因：作者侧一次超长监控命令（sleep 600）超时被工具强杀，波及同进程组跑批进程（**非代码/端点故障，无 SYSTEM_ERROR**）
- 18:52 用 T276 `--resume-from` 续跑（至 round 9，9680 行）
- 18:53 **Leader 裁决：停掉续跑、从零重跑**（理由：A0 是对外对照臂，须与 v0-anchor 一样是一次性跑完；
  且 `restore()` 存在已知缺口 `_replied_msg_ids` 未重建，续跑等价性今晚无预算证明）

- **18:53 声明的「从零重跑」实际未生效**（静默失败：无进程、无日志；根因：命令里用了 `/bin/sh` 不存在的 `disown`，整条链提前失败，且未做「起跑后 1 分钟内三条自证」）
- **19:19 真正起跑成功**（`setsid` 脱离会话 + 全新 side_root `/tmp/d2_after16b_side`；landing commit `3ec85a0`），已用 `pgrep` / `ls -la` / `wc -l` 两次取样自证在写

处置：
- `run.partial.jsonl` = 被杀时的完整前缀 + 续跑段（**不完整**：缺 round 10..83），仅证明事件发生，**不参与任何读数**
- P2 缺口已修（`restore()` 重建 `_replied_msg_ids`），修复后从零重跑，落 `v2/evidence/run_d2_after_n16_seed42/`
