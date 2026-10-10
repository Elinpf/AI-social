"""依赖边界测试（架构 §1.3 B3：观测层只读白名单）。

用 AST 扫描 `obs/*.py` 的 import，断言：
  - 允许：`engine.canon` / `engine.ledger` / `engine.events` / `engine.time`（纯函数、只读）；
  - 禁止：`engine.state` / `engine.replay` / `engine.arbiter` / `engine.hooks` /
    `engine.kernel` / `engine.runner` / `engine.rng`（写路径/实现）以及
    `life` / `freeze` / `narrative` / `orchestration` / `frontend` / `traj`；
  - 禁止包级 `import engine` / `from engine import ...`（易越界）。
"""

import ast
from pathlib import Path

_OBS_DIR = Path(__file__).resolve().parents[1] / "obs"

ALLOWED_ENGINE = {"engine.canon", "engine.ledger", "engine.events", "engine.time",
                  "engine.constants"}
FORBIDDEN_PREFIXES = (
    "engine.state", "engine.replay", "engine.arbiter", "engine.hooks",
    "engine.kernel", "engine.runner", "engine.rng",
    "life", "freeze", "narrative", "orchestration", "frontend", "traj",
)


def _iter_imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                yield ("import", n.name, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # 相对导入（obs 内部）
            yield ("from", node.module or "", node.lineno)


def test_obs_imports_respect_whitelist():
    violations = []
    for path in sorted(_OBS_DIR.glob("*.py")):
        for kind, mod, lineno in _iter_imports(path):
            if kind == "import":
                if mod == "engine" or mod.startswith("engine."):
                    if mod not in ALLOWED_ENGINE:
                        violations.append(f"{path.name}:{lineno} import {mod}")
                elif mod.split(".")[0] in {p.split(".")[0] for p in FORBIDDEN_PREFIXES}:
                    violations.append(f"{path.name}:{lineno} import {mod}")
            else:
                if mod == "engine":
                    violations.append(f"{path.name}:{lineno} from engine import ...")
                elif mod.startswith("engine."):
                    if mod not in ALLOWED_ENGINE:
                        violations.append(f"{path.name}:{lineno} from {mod} import ...")
                elif mod.split(".")[0] in {p.split(".")[0] for p in FORBIDDEN_PREFIXES}:
                    violations.append(f"{path.name}:{lineno} from {mod} import ...")
    assert violations == [], "观测层越界依赖：\n" + "\n".join(violations)


def test_obs_does_not_import_llm_clients():
    """用 AST 检测**实际 import**（不能只看子串：provider 名 'openai_compat' 不是 import）。"""
    forbidden_roots = {"openai", "anthropic", "litellm", "transformers",
                       "sentence_transformers", "freeze", "life"}
    bad = []
    for path in sorted(_OBS_DIR.glob("*.py")):
        for kind, mod, lineno in _iter_imports(path):
            root = (mod or "").split(".")[0]
            if root in forbidden_roots:
                bad.append(f"{path.name}:{lineno} {kind} {mod}")
    assert bad == [], "观测层 import 了 LLM 客户端/冻结/生活层：\n" + "\n".join(bad)


def test_obs_source_files_present():
    names = {p.name for p in _OBS_DIR.glob("*.py")}
    assert {"report.py", "emergence.py", "census.py", "antifraud.py",
            "wellbeing.py", "gate.py"} <= names
