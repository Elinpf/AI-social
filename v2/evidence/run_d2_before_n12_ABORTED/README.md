# D2 before 臂 n=12 —— 中止记录（不作为任何基线/对照，仅审计留痕）

- 参数：n=12 / rounds=84 / seed=42 / provider=openai_compat（真 LLM）/ 落盘 flush-every=2
- 起跑：2026-10-20T16:52:1x +08:00（`tools/d2/run_batch.sh`，日志 `/tmp/d2_before_run.log`）
- 中止：2026-10-20T16:55 +08:00，Leader 裁决（分母 <150 会让 D2 比率指标整段掉成 probe；改 n=16 重跑）
- 中止时进度：已落盘 **26 条事件，last_round=0**（round 0 尚未 seal），未产出 meta.json
- 处置：**不保留为基线，不参与任何读数**；`run.partial.jsonl` 仅证明「曾起跑并按要求中止」
- 备注：该批被 kill 后 `python -m orchestration run` 未写 END/ZIP 等标记，日志为**不完整前缀**，`obs` 读取器会因缺 TURN_SEAL 判为不完整，属预期
