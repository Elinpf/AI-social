# 前端回归门禁 Makefile（T107/T108）
# 用法：make ci      —— 一键双门禁（★CI 用这个，退出码 0/1/3）
#       make smoke   —— 仅无浏览器快速门禁
#       make gate    —— 仅真渲染门禁（需先 make serve）
#       make serve   —— 启动静态服务 0.0.0.0:8848
SHELL := /bin/bash
export PATH := /root/.local/share/pi-node/node-v22.23.1-linux-x64/bin:$(PATH)
CWD := $(dir $(realpath $(firstword $(MAKEFILE_LIST))))

.PHONY: ci smoke gate serve art
ci:
	@bash $(CWD)frontend/tools/ci_gate.sh
smoke:
	@node $(CWD)frontend/tools/smoke_test.js
gate:
	@python3 $(CWD)frontend/tools/gate_render.py
serve:
	@python3 $(CWD)frontend/tools/serve.py --host 0.0.0.0 --port 8848
art:
	@bash $(CWD)frontend/tools/art_build.sh
