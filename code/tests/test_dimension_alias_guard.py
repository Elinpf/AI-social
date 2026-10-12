"""Guard: `rel_respect` and `respect` are TWO DIFFERENT judgment dimensions.

Background (T213 / m2b-implementation-design §1.1, leader ruling 2026-10-12):
  * `rel_respect`  — one of the four **relation** dimensions, emitted by
    `agent._maybe_soft_judge` as `dimension=f"rel_{dim}"` for
    `dim ∈ {affinity, trust, respect, familiarity}`.
  * `respect`      — one of the three **T127 social-appraisal** dimensions,
    emitted bare by `agent._maybe_social_appraisal`.

A doc sentence saying "do not conflate them" drifts; this makes it **runnable**.
It fails loudly (never silently) if either namespace disappears/renames or if any
code starts normalising the `rel_` prefix away (which would collapse the two).

Placed under `code/tests/` on purpose: that is the suite the gate runs
(`make code-test` = `cd code && pytest -q`, testpaths=tests). Life-only test dirs
are not part of the default gate, so a guard there would not actually run.

Run:  cd code && python -m pytest tests/test_dimension_alias_guard.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _find_code_dir() -> Path:
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        if (p / "life" / "agent.py").exists():
            return p
    raise RuntimeError("cannot locate code/ dir containing life/agent.py")


CODE_DIR = _find_code_dir()
LIFE_DIR = CODE_DIR / "life"

RELATION_PREFIX = "rel_"
# relation 4-dim (agent._maybe_soft_judge) and appraisal 3-dim (agent._maybe_social_appraisal)
RELATION_BARE = ("affinity", "trust", "respect", "familiarity")
APPRAISAL_BARE = ("stance", "respect", "affection")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---- (A) both namespaces must still be declared, and stay distinct ------------
def _extract_relation_dims(agent_src: str) -> list[str]:
    """The `if dim not in (...)` filter that gates the relation judge path."""
    m = re.search(r"if\s+dim\s+not\s+in\s*\(([^)]*)\)\s*:", agent_src)
    assert m, ("relation-dim filter tuple not found in agent.py; the guard must be "
               "updated (do NOT delete it to make the suite green)")
    return re.findall(r'"([a-z_]+)"', m.group(1))


def _extract_appraisal_dims(agent_src: str) -> list[str]:
    """The `for dim, opts in (("stance", [...]), ...)` T127 appraisal dims."""
    return re.findall(r'\(\s*"(stance|respect|affection)"\s*,\s*\[', agent_src)


def test_both_namespaces_declared_and_disjoint():
    src = _read(LIFE_DIR / "agent.py")
    rel_bare = _extract_relation_dims(src)
    app_bare = _extract_appraisal_dims(src)

    # both are declared, and both include the overloaded bare token "respect"
    assert set(rel_bare) == set(RELATION_BARE), f"relation dims changed: {rel_bare}"
    assert set(app_bare) == set(APPRAISAL_BARE), f"appraisal dims changed: {app_bare}"
    assert "respect" in rel_bare and "respect" in app_bare

    # emitted strings are NOT the same dimension
    rel_emitted = {RELATION_PREFIX + d for d in rel_bare}          # {rel_respect, ...}
    app_emitted = set(app_bare)                                    # {respect, ...}

    assert "rel_respect" in rel_emitted
    assert "respect" in app_emitted
    assert "respect" not in rel_emitted, "relation path must never emit bare 'respect'"
    assert rel_emitted.isdisjoint(app_emitted), (
        "relation and appraisal dimension namespaces collided — 'respect' would be "
        "silently treated as 'rel_respect'")


# ---- (B) no code may normalise the `rel_` prefix away -------------------------
# Any of these would make a bare `respect` indistinguishable from `rel_respect`.
_FORBIDDEN = [
    r"""removeprefix\(\s*["']rel_["']\s*\)""",
    r"""replace\(\s*["']rel_["']\s*,""",
    r"""lstrip\(\s*["']rel_["']\s*\)""",
    r"""split\(\s*["']rel_["']\s*\)""",
    r"""\bsplit\(\s*["']_["']\s*\)\s*\[\s*-1\s*\]""",
    r"""rsplit\(\s*["']_["']\s*,\s*1\s*\)\s*\[\s*-1\s*\]""",
]
_FORBIDDEN_RE = [re.compile(p) for p in _FORBIDDEN]


def _iter_sources():
    for p in CODE_DIR.rglob("*.py"):
        parts = p.parts
        if "tests" in parts or p.name.startswith("test_") or "__pycache__" in parts:
            continue
        # frontend lives in its own world; the dimension namespace is life/engine/contracts.
        if "frontend" in parts:
            continue
        yield p


def test_no_prefix_alias_normalization_in_code():
    offenders: list[str] = []
    for p in _iter_sources():
        try:
            text = _read(p)
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for rx in _FORBIDDEN_RE:
                if rx.search(line):
                    offenders.append(f"{p.relative_to(CODE_DIR)}:{i}: {line.strip()}")
    assert not offenders, (
        "code normalises a dimension name in a way that could alias "
        "'respect' <-> 'rel_respect'; keep the namespaces distinct:\n"
        + "\n".join(offenders))


# ---- (C) the engine-side projection must name real life dimensions ------------
def _known_namespace(agent_src: str) -> set[str]:
    rel = {RELATION_PREFIX + d for d in _extract_relation_dims(agent_src)}
    app = set(_extract_appraisal_dims(agent_src))
    return rel | app | {"weekly_focus"}


def test_config_critical_dimensions_are_known_and_distinct():
    """`policy.llm_budget.critical_dimensions` is the published projection of
    `life/constants.CRITICAL_DIMENSIONS`; every entry must be a real life-side
    judge dimension (catches typos and bare/`rel_` confusion at the config level)."""
    cfg = json.loads(_read(CODE_DIR / "config" / "policy.json"))
    crit = (cfg.get("llm_budget") or {}).get("critical_dimensions")
    assert isinstance(crit, list), "policy.llm_budget.critical_dimensions must be a list"
    assert len(crit) == len(set(crit)), f"duplicate critical_dimensions: {crit}"

    known = _known_namespace(_read(LIFE_DIR / "agent.py"))
    unknown = [d for d in crit if d not in known]
    assert not unknown, (
        "critical_dimensions names outside the life-side judge namespace "
        "(typo, or bare/`rel_` confusion?): " + repr(unknown))

    # `importance` is a separate axis and must NOT be smuggled into this list.
    assert "importance" not in crit, (
        "importance belongs to the separate `critical_importance` key, not "
        "`critical_dimensions`")

