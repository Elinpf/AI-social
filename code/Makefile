# 前端回归门禁 Makefile（T107/T108）
# 用法：make ci       —— 前端回归总门（★CI 用这个，退出码 0/1/3）
#       make gate-front—— 仅前端真渲染门禁（= front-gate = 旧名 gate）
#       make front-gate—— 同 gate-front
#       make gate      —— 同 front-gate（旧名，保留兼容）
#       make smoke     —— 仅无浏览器快速冒烟
#       make serve     —— 启动静态服务 0.0.0.0:8848
#
# ⚠️ 消歧（T280）：本 Makefile 的 `gate` = **前端真渲染门禁**；
#    仓根 `../Makefile` 的 `gate` = **术语棘轮 + pytest**（不含前端）。两者语义不同！
#    → 需要「一次跑全部」到仓根用 `make verify`（仓根门禁 + 本文件 make ci）。
#    → 消歧名：本文件用 `gate-front`；仓根用 `gate-repo`。旧名 `gate` 两处均保留兼容。
SHELL := /bin/bash
export PATH := /root/.local/share/pi-node/node-v22.23.1-linux-x64/bin:$(PATH)
CWD := $(dir $(realpath $(firstword $(MAKEFILE_LIST))))

.PHONY: help ci smoke front-gate gate gate-front serve art

help:
	@echo "== code/ Makefile（在 code/ 目录跑；或从仓根 make -C code <目标>）=="
	@echo "make ci         # ★前端回归总门：smoke + 真渲染门禁 + R9 四指标 + D 段（退出码 0/1/3，3=SKIP≠PASS）"
	@echo "make front-gate # 仅前端真渲染门禁（= 旧名 gate）"
	@echo "make gate       # 同 front-gate（旧名，保留兼容）"
	@echo "make smoke      # 仅无浏览器快速冒烟"
	@echo "make serve      # 起静态服务 0.0.0.0:8848（真渲染门禁需要）"
	@echo "make art        # 美术资源构建（含生成期守卫）"
	@echo ""
	@echo "⚠ 消歧（T280）：本文件的 gate = **前端真渲染门禁**；"
	@echo "   仓根 ../Makefile 的 gate = **术语棘轮 + pytest**（不含前端）。"
	@echo "   想一次跑全部 → 到仓根用 'make verify'（仓根门禁 + 本文件 make ci）。"

# 消歧别名（T280）：前端真渲染门禁；= front-gate = 旧名 gate。避免与仓根 gate 混淆。
gate-front: front-gate

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
