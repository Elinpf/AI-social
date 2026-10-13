# 青溪镇社会实验 · 门禁入口（Makefile）
#
# 与 `pytest -q` / `lint-imports` / obs gate 并列的可跑门禁。
# 术语合规采用「基线/棘轮」模式：仅当出现基线之外的【新】违规才失败。

.PHONY: help lexicon-gate lexicon-report lexicon-baseline lexicon-dir-stats inert-gate pyclean code-test plugin-test stamp install-hooks gate gate-repo verify verify-inner resume-fixture-check resume-guard

help:
	@echo "== 仓根 Makefile（在仓库根目录跑）=="
	@echo "make verify          # ★唯一总门（受守卫）：起/收比冻结区指纹，跑中被改即判'结果不可信'"
	@echo "make verify-inner    # verify 的内部真门（仓根门禁 + 前端 CI）；直接用则无首尾自检"
	@echo "make gate-repo       # 消歧名 = 下面的 gate（仓根级门禁）"
	@echo "make gate            # 仓根级门禁：术语棘轮 + inert + code-test + plugin-test（+可选 lint-imports）"
	@echo "make lexicon-gate    # 术语合规 · 棘轮门禁"
	@echo "make lexicon-report  # 术语合规 · 完整报告（违规/提及/按目录）"
	@echo "make lexicon-baseline# 重冻术语基线（维护用）"
	@echo "make inert-gate      # 已登记/未接线核对 · 棘轮门禁（登记 != 生效，T226）"
	@echo "make code-test       # 在 code/ 下跑 pytest"
	@echo "make plugin-test     # 在 plugin-skeleton/ 下跑 pytest"
	@echo "make stamp           # 记录本次门禁结论所绑定的 git 状态"
	@echo "make resume-fixture-check # 快 · must-be-red 夹具检查（pre-fix 分歧对语义投影必须【不等】）"
	@echo "make resume-guard    # 慢 · current HEAD 上 cut=75/89 续跑一致性回归守护（独立、不挂 verify）"
	@echo ""
	@echo "⚠ 消歧（T280）：本文件的 gate = 仓根级门禁，**不含前端渲染**。"
	@echo "   前端渲染门禁在 code/ 下（make -C code ci 或 make -C code front-gate）。"
	@echo "   想一次跑全部 → 用 'make verify'（唯一不会说错的总门）。"

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

# 消歧别名（T280）：仓根级门禁 = 本文件 `gate`（术语 + inert + pytest + plugin + 可选 lint-imports）。
# 与 `code/Makefile` 的 `gate`（前端真渲染）**语义不同** —— 需要「跑全部」用 `make verify`。
gate-repo: gate

# ★唯一总门（T280）：仓根门禁 + code/ 前端 CI 全跑。
#   「make verify 全绿」= 仓根门禁 与 前端 CI 都通过（唯一不会说错的目标）。
#   T340：`verify` 现为**受守卫**版本 —— 起/收记冻结区(code+config)指纹，**跑中被改即判"结果不可信"**（exit 2）。
#        内部真门 = `verify-inner`（等价旧 verify）。
verify:
	@bash tools/verify_tree_guard.sh

verify-inner: gate
	@echo "[verify] 仓根门禁通过 → 继续前端 CI（在 code/ 跑 make ci）"
	@$(MAKE) -C code ci
	@echo "[verify] OK · 仓根门禁 + 前端 CI 均通过（全绿）"

# ===== T311 · resume 回归守护（重口径门；**不挂 gate/verify**，避免与前端 CI/夜跑叠加）=====
# resume-fixture-check：快 —— must-be-red 夹具（pre-fix 分歧对）语义投影必须【不等】。
# resume-guard：慢 —— current HEAD 上 cut=75/89 续跑必须 == oneshot（每 cut ≈4×150r run）。
#   ⚠ 一人一次；与 `make verify`、obs 跑批错开。详见 tools/t271/resume_regression_guard.sh 头部装置前提。
resume-fixture-check:
	@bash tools/t271/negative_fixture_check.sh

resume-guard:
	@bash tools/t271/resume_regression_guard.sh
