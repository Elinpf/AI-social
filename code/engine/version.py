"""engine_version 指纹与复现输入常数（蓝图 §3.6）。

- 单一来源：`config/perception_scope.json`（权威）；缺失/非法/版本不匹配 → **硬报错**，不静默回退。
- 指纹：聚合 `default.json` 与复现输入常数（`perception_scope.json` / `topology.json` /
  `narrative_weights.json`）的规范哈希，写入 `WORLD_INIT`，重放前断言一致。
"""

from __future__ import annotations

import json
from pathlib import Path

from .canon import hash_obj

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

#: 纳入 engine_version 指纹的复现输入常数（缺失记为 null，不阻断，但重放会暴露不一致）
FINGERPRINT_FILES = (
    "default.json",
    "perception_scope.json",
    "topology.json",
    "narrative_weights.json",
    "llm.json",
    "engine_version.json",
    "policy.json",
    "activity_templates.json",
    "social.json",
    "life_v2.json",
)

REQUIRED_PERCEPTION_SCOPE_VERSION = "v1.2-r2"

VALID_VISIBILITY_CLASSES = frozenset({
    "global", "place_local", "members", "private", "participants_only", "subject_only",
})


class ConfigError(Exception):
    """复现输入配置错误（缺失/非法/版本不匹配）。"""


class PerceptionScopeError(ConfigError):
    """PERCEPTION_SCOPE 缺失/非法/版本不匹配（不得静默回退）。"""


def _read_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def component_digests(config_dir: str | Path | None = None) -> dict:
    d = Path(config_dir) if config_dir else CONFIG_DIR
    out = {}
    for name in FINGERPRINT_FILES:
        obj = _read_json(d / name)
        out[name] = hash_obj(obj) if obj is not None else None
    return out


def compute_fingerprint(config_dir: str | Path | None = None) -> str:
    return hash_obj(component_digests(config_dir))


def load_perception_scope(config_dir: str | Path | None = None) -> tuple[dict, str, str]:
    """严格加载 PERCEPTION_SCOPE（单一来源）。

    返回 (scope_table, default_visibility_class, version)。缺失/非法/版本不匹配 → 抛
    PerceptionScopeError（**不做默认回退**）。
    """
    d = Path(config_dir) if config_dir else CONFIG_DIR
    path = d / "perception_scope.json"
    obj = _read_json(path)
    if obj is None:
        raise PerceptionScopeError(f"缺少 PERCEPTION_SCOPE 配置文件：{path}")
    scope = obj.get("scope")
    if not isinstance(scope, dict) or not scope:
        raise PerceptionScopeError("perception_scope.json 缺少非空 `scope` 表")
    version = str(obj.get("version", ""))
    if version != REQUIRED_PERCEPTION_SCOPE_VERSION:
        raise PerceptionScopeError(
            f"PERCEPTION_SCOPE 版本不匹配：文件 {version!r} != 期望 {REQUIRED_PERCEPTION_SCOPE_VERSION!r}"
            "（不得静默回退；请对齐 config/perception_scope.json）")
    bad = sorted({v for v in scope.values() if v not in VALID_VISIBILITY_CLASSES})
    if bad:
        raise PerceptionScopeError(f"perception_scope.json 含非法 visibility_class：{bad}")
    default_cls = str(obj.get("default_visibility_class", "place_local"))
    if default_cls not in VALID_VISIBILITY_CLASSES:
        raise PerceptionScopeError(f"default_visibility_class 非法：{default_cls!r}")
    return dict(scope), default_cls, version


def assert_log_fingerprint(records: list, config_dir: str | Path | None = None,
                           expected: str | None = None) -> None:
    """重放前断言：日志 `WORLD_INIT.fingerprint` == 期望的 engine_version 指纹。

    `expected` 显式给出时用它（**避免运行期间配置被并发修改导致的假不匹配**——run 内
    应固定用启动时捕获的指纹）；否则从 `config_dir` 重新计算。

    不一致**通常是预期行为**（模型/thinking/政策/拓扑/可见性等复现输入被切换），
    而非数据损坏——故报错信息显式说明，避免使用者误判。
    """
    expected = expected if expected is not None else compute_fingerprint(config_dir)
    for rec in records:
        if rec.get("type") == "WORLD_INIT":
            got = rec.get("payload", {}).get("fingerprint")
            if got is None:
                return  # 旧日志无指纹：跳过（向后兼容）
            if got != expected:
                raise ConfigError(
                    "engine_version 指纹不一致，拒绝重放："
                    f"日志={got} 当前={expected}。"
                    "这通常表示**复现输入配置已变更**（如 config/llm.json 的模型/thinking 策略、"
                    "config/policy.json 政策档、topology.json、perception_scope.json 等），"
                    "并非数据损坏；请用与产出该日志相同的配置重放，或重新生成日志。")
            return


def load_engine_version(config_dir: str | Path | None = None) -> dict:
    """严格加载 `engine_version.json`（缺失/非法 → ConfigError）。"""
    d = Path(config_dir) if config_dir else CONFIG_DIR
    obj = _read_json(d / "engine_version.json")
    if obj is None:
        raise ConfigError(f"缺少 engine_version.json：{d / 'engine_version.json'}")
    if not isinstance(obj.get("components"), dict):
        raise ConfigError("engine_version.json 缺少 `components` 声明")
    return obj


def load_policy(config_dir: str | Path | None = None) -> dict:
    """严格加载 `policy.json`（B 线政策参数层；缺失/非法 → ConfigError）。"""
    d = Path(config_dir) if config_dir else CONFIG_DIR
    obj = _read_json(d / "policy.json")
    if obj is None:
        raise ConfigError(f"缺少 policy.json：{d / 'policy.json'}")
    return obj


def policy_defaults(config_dir: str | Path | None = None) -> dict:
    """把 policy.json 展开为 {name: default}（含 safety_valve 子项）。"""
    pol = load_policy(config_dir)
    out = {}
    for k, v in pol.items():
        if isinstance(v, dict) and "default" in v:
            out[k] = v["default"]
        elif isinstance(v, dict) and k == "safety_valve":
            for kk, vv in v.items():
                if isinstance(vv, dict) and "default" in vv:
                    out[f"safety_valve.{kk}"] = vv["default"]
    return out


def assert_version_consistency(config_dir: str | Path | None = None) -> None:
    """一致性断言：engine_version.json 声明的各组件版本 == 实际文件版本（不一致→ConfigError）。"""
    d = Path(config_dir) if config_dir else CONFIG_DIR
    ev = load_engine_version(d)
    for name, meta in ev.get("components", {}).items():
        fname = meta.get("file")
        declared = meta.get("version")
        if not fname or declared is None:
            continue
        obj = _read_json(d / fname)
        if obj is None:
            raise ConfigError(f"engine_version.json 声明的组件缺失：{fname}")
        actual = obj.get("version")
        if actual is not None and str(actual) != str(declared):
            raise ConfigError(
                f"组件版本不一致（{name}）：engine_version.json 声明 {declared!r} != "
                f"{fname} 实际 {actual!r}")
