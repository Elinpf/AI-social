#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`render_shots.py` 的**零改动包装器**：仅补一个 `spread`（闲话怎么传开）视图。

为什么单独一个文件（不直接改 `render_shots.py`）：
- `render_shots.py` 的 `VIEWS` 只登记了 `chat` / `rhythm`；但 `code/frontend/dialogue.html`
  与 `src/dialogue.js:184` 早已支持第三个视图 `view=spread`（`state.data.spread`，由
  `code/frontend/tools/gen_threads.py:489` 生成）。
- 本任务要求「至少 3 张真实截图」，又不能动 `code/`、也不该改既有出图器的判据，
  故用**导入 + 补登记视图**的方式复用同一条渲染链（同一份 shot.py、同一份临时服务根、
  同一套像素自检与三件套记录），既有文件一字未改。

用法（与 render_shots.py 完全一致，多一个可用视图 spread）：
    python3 tools/metrics/render_shots_extra.py \
        --run-dir <RUN 目录> --batch-id D12-I --outdir <目录> \
        --views chat,rhythm,spread
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import render_shots as rs  # noqa: E402

# 与 chat/rhythm 同风格的尺寸；query 只多一个 view=spread（其余与既有视图一致）
rs.VIEWS = dict(rs.VIEWS)
rs.VIEWS["spread"] = (1400, 1000, "still=1&multi=1&min=0&view=spread")

# 单线程聚焦视图：dialogue.js:469/803 支持 `thread=<thread_id>`（点线程时自己也是这么跳的）。
# 线程 id 由环境变量给，缺省取本批最长线程（D12-I：TH-P004-P002-0，6 轮）——
# 该 id 必须存在于 threads_<batch>.json 的 threads[].thread_id 里，否则前端会退化为整页视图。
_THREAD_ID = os.environ.get("D12I_THREAD_ID", "TH-P004-P002-0")
rs.VIEWS["chat_thread"] = (1200, 1000, f"still=1&thread={_THREAD_ID}&sort=turns")

if __name__ == "__main__":
    sys.exit(rs.main(sys.argv[1:]))
