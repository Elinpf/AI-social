# ⚠ 本目录作废（INVALID）：**100% 命中 freeze 缓存，是回放不是新跑**

- 起跑 23:28:54 → finished 23:30:25，**duration 91 秒**；`llm_calls 2878 / llm_cached 2878`（**100%**）；
  `by_purpose` 全 cached：dialogue 510/510、importance 1523/1523、judge 668/668、negotiation 49/49、plan 16/16、reflect 112/112
  ⇒ **网络调用 = 0**，不构成一次独立运行，不能用于两 seed 判定。
- 根因：启动器把 C:43 的 `--side-root` 固定为 `/tmp/d28_C_s43`，该目录**已被 20:29 那次作废的 C 跑用过**
  （其 `freeze_cache` 里已有同 keys 的响应）⇒ 本批全量命中缓存。
- 处置：目录改名 `_INVALID_allcached`；真 C:43 用**全新 side-root** 重跑，并在验收时强制要求
  **`network = calls − cached > 0` 且 `dialogue.cached` 远小于 `dialogue.calls`**（本次教训：不能只看 provider/结构）。
