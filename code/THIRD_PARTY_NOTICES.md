# THIRD-PARTY NOTICES

本仓库包含/改编自以下第三方开源项目。分发本仓库或其衍生作品时，须遵守下列许可与声明义务。

---

## 1. Generative Agents (joonspk-research/generative_agents) — Apache-2.0

- 上游：`https://github.com/joonspk-research/generative_agents`（Stanford University）
- 许可：Apache License, Version 2.0
- 许可全文：`licenses/Apache-2.0.txt`
- 版权：归 Generative Agents 原作者所有。
- 本仓库改编位置：`code/life/`（人格生活层）。**逐文件"已修改"声明**见 `code/life/NOTICE`（依 Apache-2.0 §4(b) 要求，列出各改编文件与改动摘要）。
- 义务落实：
  - 保留版权/许可/归属声明（本文件 + `life/NOTICE`）；
  - **标明修改**：`life/agent.py`、`life/memory.py`、`life/persona.py` 等改编文件的文件头与 `life/NOTICE` 均声明 "adapted from / modified"；
  - 随分发提供许可证副本（`licenses/Apache-2.0.txt`）。

## 2. AI Town (a16z-infra/ai-town) — MIT

- 上游：`https://github.com/a16z-infra/ai-town`
- 许可：MIT License
- 许可全文：`licenses/MIT.txt`
- 版权：`Copyright (c) 2023 a16z-infra`（以**上游仓库 LICENSE 的版权行为准**；如上游版权行不同，请以其为准并更新本文件与 `licenses/MIT.txt`）。
- 本仓库改编位置：`code/frontend/`（前端/可视化）。**逐文件"已修改"声明**见 `code/frontend/NOTICE`。
- 义务落实：保留版权与许可声明，随分发提供 MIT 许可副本。

---

## 维护约定

- 新增任何第三方代码/资源前，必须：① 在本文件登记（上游 URL、许可、版权行、改编文件与改动摘要）；② 在 `licenses/` 放入许可全文；③ 对修改过的源文件在文件头标注 `modified from <上游文件> (<许可>)`。
- 本清单与 `licenses/` 属**对外发布阻断项**（不阻塞内部 P0 跑通）。
