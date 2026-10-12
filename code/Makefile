# 前端回归门禁 Makefile（T107/T108）
# 用法：make ci      —— 一键双门禁（★CI 用这个，退出码 0/1/3）
#       make smoke   —— 仅无浏览器快速门禁
#       make front-gate —— 仅真渲染门禁（需先 make serve）【与 gate 同义，见下】
#       make gate    —— 同 front-gate（保留旧名；勿与仓根 make gate 混淆）
#       make serve   —— 启动静态服务 0.0.0.0:8848
#
# ⚠️ 消歧：本 Makefile 的 `gate` = **前端真渲染门禁**；
#    仓根 `../Makefile` 的 `gate` = **术语棘轮 + code 测试**。两者语义不同！
#    新脚本请优先用 `front-gate`（T219 P1 第一步别名；真正改名待 release 收口后统一做）。
SHELL := /bin/bash
export PATH := /root/.local/share/pi-node/node-v22.23.1-linux-x64/bin:$(PATH)
CWD := $(dir $(realpath $(firstword $(MAKEFILE_LIST))))

.PHONY: ci smoke front-gate gate serve art
ci:
	@bash $(CWD)frontend/tools/ci_gate.sh
smoke:
	@node $(CWD)frontend/tools/smoke_test.js
front-gate:
	@python3 $(CWD)frontend/tools/gate_render.py
gate: front-gate
serve:
	@python3 $(CWD)frontend/tools/serve.py --host 0.0.0.0 --port 8848
art:
	@bash $(CWD)frontend/tools/art_build.sh
