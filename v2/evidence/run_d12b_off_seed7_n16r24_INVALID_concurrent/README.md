# 无效：起跑时**已有真 LLM 批在跑**（违反串行纪律），起跑后 20 秒内主动停止

- 起跑 2026-10-23T01:25:38（unit `t271-d12boff-012538`），发现 `run_d1_f6on_seed42_n16r84`（pid 2154350，00:59 起，真 LLM `openai_compat` 2500 次调用）正在跑
- 处置：立即 `systemctl stop`，**不参与任何对照**
- 教训：起跑前 `pgrep` 只查了字符串，未识别到他人 worktree/其它 out 路径上的真批 ⇒ 判"无批"必须**全局扫描 `orchestration run` + 检查各自 provider**，而不是只看自己常用目录
