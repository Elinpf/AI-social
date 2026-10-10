# 青溪镇社会实验 · 门禁入口（Makefile）
#
# 与 `pytest -q` / `lint-imports` / obs gate 并列的可跑门禁。
# 术语合规采用「基线/棘轮」模式：仅当出现基线之外的【新】违规才失败。

.PHONY: help lexicon-gate lexicon-report lexicon-baseline lexicon-dir-stats code-test gate

help:
	@echo "make lexicon-gate    # 术语合规 · 棘轮门禁（CI 推荐）"
	@echo "make lexicon-report  # 术语合规 · 完整报告（违规/提及/按目录）"
	@echo "make lexicon-baseline# 重冻术语基线（维护用）"
	@echo "make code-test       # code/ 下 pytest"
	@echo "make gate            # 全部可用门禁（lexicon + code-test + 可选 lint-imports）"

# 术语合规 · 棘轮门禁：基线外新违规 -> 非 0
lexicon-gate:
	python3 glossary/tools/lint_terms.py --root . --baseline glossary/term_baseline.json

lexicon-report:
	python3 glossary/tools/lint_terms.py --root .

lexicon-dir-stats:
	python3 glossary/tools/lint_terms.py --root . --dir-stats

lexicon-baseline:
	python3 glossary/tools/lint_terms.py --root . --update-baseline glossary/term_baseline.json

code-test:
	cd code && python3 -m pytest -q

# 汇总门禁：先术语棘轮；再 code 测试；如装了 import-linter 则跑边界
gate: lexicon-gate code-test
	@echo "[gate] 术语棘轮 + code 测试 完成"
	@if command -v lint-imports >/dev/null 2>&1; then \
		echo "[gate] lint-imports 边界检查"; (cd code && lint-imports) ; \
	else \
		echo "[gate] 跳过 lint-imports（未安装）"; \
	fi
