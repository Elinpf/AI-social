# 无效跑取证：OFF 臂全量缓存回放（2026-10-31T12:03）

- run_batch rc=0，provider_guard.ok=true，但 `cached=calls=2252`，`tokens_in=tokens_out=0`。
- 原因：`--side-root /tmp/r38_f3_side_off` 为 10:21 旧尝试遗留目录，内含
  `freeze_cache` 1290 个文件；`orchestration/integration.py:1004` 把 freeze 缓存置于
  `<side_root>/freeze_cache`，同 prompt 命中即 `cached=True`、零真实调用（llm_client.py:306-345）。
- 结论：**未验真**（违反 llm-cost 缓存回放=0 要求）。该目录整体改名为
  `off_INVALID_cached_replay/` 保留为反例证据，不进入 F-3 读数。
- ON 臂 rc=9（preflight 并发闸）：因监控命令行含字面 `run_batch` 被 `pgrep -f` 自匹配，
  非真实并发；改监控写法后重跑。
## 批根 on.rc（失败态，非 on/ 的 rc）
```
2026-10-31 12:03:28.657967580 +0800 on.rc
content=9
```
