"""叙事层权重与阈值的严格加载与校验（`config/narrative_weights.json`）。

对应设计：`v1.2/17-narrative-layer.md` §2.1（戏剧性九子维权重）/ §2.2–§2.3（阈值）
/ §4 / §7（渲染默认）。本模块是叙事层对配置的**唯一读取入口**，负责：

- **schema 校验**：九权重齐备、逐项 ∈ [0,1]、Σw == 1（容差 1e-9）；阈值七项齐备、
  非负，`k_top`/`delta_slots` 为正整数，`theta_feature > theta_drama`。
- **narrative_config_hash**：本文件规范哈希（`engine.canon.hash_obj`），与
  `engine/version.py` 纳入 `engine_version` 指纹的 `narrative_weights.json`
  分量**一致**；改权重/阈值 → 该哈希变化 → 重放前 `assert_log_fingerprint` 拒绝不一致日志。

纪律（对齐 17 §0.2 H-2 / §9.3 NT-C2，同 13 §2.3 WBI）：权重是**可声明的价值假设**，
仅决定叙事层「讲什么」；**不得**回写世界、不得作为激励/目标函数、不得进入评估指标、
验收门禁与 A 线训练信号。本模块**只读**配置，无副作用。
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.canon import hash_obj

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
NARRATIVE_WEIGHTS_FILE = "narrative_weights.json"

#: 戏剧性九子维权重键（17 §2.1）
WEIGHT_KEYS = (
    "c_conflict", "c_turn", "c_contrast", "c_plunge", "c_wbdiv",
    "c_ruin", "c_ally", "c_rarity", "c_impact",
)

#: 阈值键（17 §2.3 / §4.4）
THRESHOLD_KEYS = (
    "theta_turn", "theta_plunge", "theta_drama", "theta_feature",
    "k_top", "lambda", "delta_slots",
)

#: 必须为**正整数**的阈值键
INT_THRESHOLD_KEYS = ("k_top", "delta_slots")

#: 权重和容差
WEIGHT_SUM_TOL = 1e-9


class NarrativeWeightsError(Exception):
    """叙事权重/阈值配置缺失或非法（不得静默回退）。"""


def _read_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_number(v) -> bool:
    # 显式排除 bool（Python 中 bool 是 int 子类）
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def load_narrative_weights(config_dir: str | Path | None = None) -> dict:
    """严格加载并校验叙事权重配置，返回配置 dict（原样，不改写）。

    缺失 / 非法 / 不满足不变量 → 抛 :class:`NarrativeWeightsError`。
    """
    d = Path(config_dir) if config_dir else CONFIG_DIR
    path = d / NARRATIVE_WEIGHTS_FILE
    obj = _read_json(path)
    if obj is None:
        raise NarrativeWeightsError(f"缺少叙事权重配置：{path}")
    if not isinstance(obj, dict):
        raise NarrativeWeightsError(f"{NARRATIVE_WEIGHTS_FILE} 顶层必须是对象")

    # ---- 权重 ----
    weights = obj.get("weights")
    if not isinstance(weights, dict) or not weights:
        raise NarrativeWeightsError("缺少非空 `weights` 表")
    missing = [k for k in WEIGHT_KEYS if k not in weights]
    if missing:
        raise NarrativeWeightsError(f"weights 缺少键：{missing}")
    extra = [k for k in weights if k not in WEIGHT_KEYS]
    if extra:
        raise NarrativeWeightsError(f"weights 含未知键：{sorted(extra)}")
    for k in WEIGHT_KEYS:
        w = weights[k]
        if not _is_number(w):
            raise NarrativeWeightsError(f"weight {k!r} 非数值：{w!r}")
        if not (0.0 <= float(w) <= 1.0):
            raise NarrativeWeightsError(f"weight {k!r} 越界 [0,1]：{w!r}")
    total = sum(float(weights[k]) for k in WEIGHT_KEYS)
    if abs(total - 1.0) > WEIGHT_SUM_TOL:
        raise NarrativeWeightsError(f"权重和必须为 1，实际 {total!r}（容差 {WEIGHT_SUM_TOL}）")

    # ---- 阈值 ----
    thresholds = obj.get("thresholds")
    if not isinstance(thresholds, dict):
        raise NarrativeWeightsError("缺少 `thresholds` 表")
    missing_t = [k for k in THRESHOLD_KEYS if k not in thresholds]
    if missing_t:
        raise NarrativeWeightsError(f"thresholds 缺少键：{missing_t}")
    for k in THRESHOLD_KEYS:
        v = thresholds[k]
        if not _is_number(v):
            raise NarrativeWeightsError(f"threshold {k!r} 非数值：{v!r}")
        if float(v) < 0.0:
            raise NarrativeWeightsError(f"threshold {k!r} 不得为负：{v!r}")
    for k in INT_THRESHOLD_KEYS:
        v = float(thresholds[k])
        if v <= 0 or not v.is_integer():
            raise NarrativeWeightsError(f"threshold {k!r} 必须为正整数：{thresholds[k]!r}")
    if float(thresholds["theta_feature"]) <= float(thresholds["theta_drama"]):
        raise NarrativeWeightsError(
            "theta_feature 必须严格大于 theta_drama（特写阈值须高于周纪事入选阈值）")

    return obj


def narrative_config_hash(config_dir: str | Path | None = None) -> str:
    """叙事配置规范哈希（`sha256:...`）。

    与 `engine.version.component_digests()['narrative_weights.json']` 相同——因为二者
    都对同一份已解析 JSON 做规范化哈希。改权重/阈值即改变该哈希，须重算并记入
    `WORLD_INIT.config_components`，否则重放前的指纹断言会失败。
    """
    return hash_obj(load_narrative_weights(config_dir))
