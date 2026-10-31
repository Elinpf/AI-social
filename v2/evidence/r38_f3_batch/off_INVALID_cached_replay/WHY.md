# 为何不采用本目录

- 本目录是 2026-10-31T12:03 的 OFF 臂产物，`run_batch` rc=0 但 **llm-cost 显示 cached=calls=2252、tokens_in=tokens_out=0**。
- 根因：使用了 `/tmp/r38_f3_side_off`（10:21 旧尝试遗留，`freeze_cache/responses` 内有 865 份响应），
  同 seed 同 spec ⇒ 提示词逐字节相同 ⇒ 全量命中；命中即零真实调用（`code/freeze/llm_client.py:306-345`）。
- 按团队纪律 4 与 CYCLE-37 §5.1 第⑥条，该臂**不构成真跑**，整目录作废留证，不进入 F-3 读数。
- 已用全新 `/tmp/r38_f3_side_off_fresh` 重跑，见 `../off/`。
