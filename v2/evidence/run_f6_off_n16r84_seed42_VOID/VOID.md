# ⛔ 本批作废（不作证据）

- 尺寸：n16×84 seed42，OFF 臂（`LIFE_PROMPT_MEMORY_F6` 未设）
- 起跑：2026-10-21T12:11:50+08:00（setsid，pid 1066344 / sid 1066333）
- 停止：2026-10-21T12:35:01+08:00，kill 进程组后 `pgrep -fa "orchestration[ ]run"` 空 + rc=1
- 停止时进度：last TURN_SEAL round = 9，`run.jsonl` 9679 行，
  sha256 = `4c8ef41ee398cb87040ddf4ffef13c70fd12f9257e418213588c99282c2a66e7`
- side-root：`/tmp/f6_off_side`（**保留不动、不再复用**，内含 788 个响应缓存；复用会污染新批的 provider/token 统计）
- 作废原因：**尺寸口径变更**（n16×84 → n16×60，Leader 裁决 B：实测 pace 2.5–4 倍于预估，6–7h 会挤掉报告收口）
- 处置：**保留不删**，仅标注；正式证据只用 n16×60 两臂批
- 结论：本批任何读数**不得**写入报告正文；如需说明，只写「曾有一批 n16×84 跑到 round 9 因尺寸变更作废」
