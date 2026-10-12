# 青溪镇社会实验 · 门禁入口（Makefile）
#
# 与 `pytest -q` / `lint-imports` / obs gate 并列的可跑门禁。
# 术语合规采用「基线/棘轮」模式：仅当出现基线之外的【新】违规才失败。

.PHONY: help lexicon-gate lexicon-report lexicon-baseline lexicon-dir-stats inert-gate pyclean code-test plugin-test stamp install-hooks gate

help:
	@echo "make lexicon-gate    # 术语合规 · 棘轮门禁（CI 推荐）"
	@echo "make lexicon-report  # 术语合规 · 完整报告（违规/提及/按目录）"
	@echo "make lexicon-baseline# 重冻术语基线（维护用）"
	@echo "make inert-gate      # 已登记/未接线核对 · 棘轮门禁（登记 != 生效，T226）"
	@echo "make code-test       # code/ 下 pytest"
	@echo "make gate            # 全部可用门禁（lexicon + inert + code-test + 可选 lint-imports）"
	@echo ""
	@echo "注：本 gate = 术语棘轮 + code 测试（非前端渲染门禁）；"
	@echo "    前端真渲染门禁见 code/Makefile 的 'make -C code front-gate'。"

# 术语合规 · 棘轮门禁：基线外新违规 -> 非 0
lexicon-gate:
	python3 glossary/tools/lint_terms.py --root . --baseline glossary/term_baseline.json

lexicon-report:
	python3 glossary/tools/lint_terms.py --root .

lexicon-dir-stats:
	python3 glossary/tools/lint_terms.py --root . --dir-stats

lexicon-baseline:
	python3 glossary/tools/lint_terms.py --root . --update-baseline glossary/term_baseline.json

# 已登记/未接线核对（T226）· 棘轮：未接线须显式声明；接线后须更新 expected_status。
# 性质：它造成的"红"不是 bug，而是"有人改了接线状态但没同步声明"。
# 盲区：静态扫描只保证有生产侧触发路径，不保证运行时真产生 → 重大条目叠加实跑日志核对。
inert-gate:
	python3 tools/check_inert_registry.py

# 假红防护（T220）：清陈旧字节码 + 禁写 .pyc，避免「回滚后仍红」的假红。
# 背景：RV6 实证——源码回滚后未清 __pycache__ 仍红，清后 4 passed。
pyclean:
	@find code -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@rm -rf code/.pytest_cache

# code-test 前置打戳（T220 追加）：pytest 结论须自带环境戳；
# 且戳里含「最近改动的模块」，把「红」与「谁在改什么」对上（避免"长期红来源不明"）。
code-test: pyclean stamp
	cd code && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider

# 插件骨架测试（独立于 code/，自成一体）；T220 四补齐覆盖，避免静默缺口。
plugin-test:
	cd plugin-skeleton && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider

# git 状态打戳（T220 三）：门禁结论必须说明「在哪个 git 状态上跑的」。
stamp:
	@bash tools/git_stamp.sh

# 安装本地 git 钩子（T237）：术语棘轮只扫**本次提交范围**（git diff --cached），
# 对共享索引 / 他人 WIP 免疫；全树检查保留给 CI（`make lexicon-gate`）。
# 钩子在 .git/hooks（不在版本库）→ 此目标把版本库内脚本装入，避免 clone 后丢失。
install-hooks:
	@cp tools/pre-commit-lexicon.sh .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "[install-hooks] 已安装 .git/hooks/pre-commit ← tools/pre-commit-lexicon.sh"

# 汇总门禁：先打戳（证据绑版本）；再术语棘轮 + inert 棘轮；再 code 测试；如装了 import-linter 则跑边界
gate: stamp lexicon-gate inert-gate code-test plugin-test
	@echo "[gate] 术语棘轮 + inert 棘轮 + code 测试 + 插件骨架测试 完成"
	@if command -v lint-imports >/dev/null 2>&1; then \
		echo "[gate] lint-imports 边界检查"; (cd code && lint-imports) ; \
	else \
		echo "[gate] 跳过 lint-imports（未安装）"; \
	fi
