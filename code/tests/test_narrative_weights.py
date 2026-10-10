"""T46：叙事权重配置 `config/narrative_weights.json` 的加载、校验与指纹。

对齐 `v1.2/17-narrative-layer.md` §2.1/§2.3/§9.2 与 T41 指纹口径。
"""

import copy
import json

import pytest

from engine import version
from narrative import weights as nw


def _valid_config() -> dict:
    return {
        "version": "vX",
        "weights": {k: (1.0 / len(nw.WEIGHT_KEYS)) for k in nw.WEIGHT_KEYS},
        "thresholds": {
            "theta_turn": 0.2, "theta_plunge": 0.25, "theta_drama": 0.35,
            "theta_feature": 0.6, "k_top": 5, "lambda": 0.3, "delta_slots": 6,
        },
    }


def _write(tmp_path, obj) -> None:
    (tmp_path / nw.NARRATIVE_WEIGHTS_FILE).write_text(
        json.dumps(obj, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- 真源配置 ----

def test_load_shipped_config_ok():
    cfg = nw.load_narrative_weights()
    assert set(cfg["weights"]) == set(nw.WEIGHT_KEYS)
    assert abs(sum(cfg["weights"].values()) - 1.0) <= nw.WEIGHT_SUM_TOL


def test_shipped_weights_sum_to_one_exact():
    cfg = nw.load_narrative_weights()
    assert sum(float(cfg["weights"][k]) for k in nw.WEIGHT_KEYS) == pytest.approx(1.0, abs=1e-9)


def test_shipped_thresholds_have_defaults():
    th = nw.load_narrative_weights()["thresholds"]
    for k in nw.THRESHOLD_KEYS:
        assert k in th, f"阈值 {k} 缺默认值"
        assert isinstance(th[k], (int, float)) and not isinstance(th[k], bool)
    assert float(th["k_top"]).is_integer() and th["k_top"] > 0
    assert float(th["delta_slots"]).is_integer() and th["delta_slots"] > 0
    assert th["theta_feature"] > th["theta_drama"]


def test_narrative_config_hash_deterministic():
    assert nw.narrative_config_hash() == nw.narrative_config_hash()


def test_narrative_config_hash_matches_engine_fingerprint_component():
    # narrative_config_hash 与 engine_version 指纹分量一致
    comps = version.component_digests()
    assert comps[nw.NARRATIVE_WEIGHTS_FILE] is not None, "narrative_weights.json 未纳入指纹"
    assert nw.narrative_config_hash() == comps[nw.NARRATIVE_WEIGHTS_FILE]


# ---------------------------------------------------------------- 非法输入 ----

def test_missing_file_raises(tmp_path):
    with pytest.raises(nw.NarrativeWeightsError):
        nw.load_narrative_weights(tmp_path)


def test_bad_weight_sum_raises(tmp_path):
    obj = _valid_config()
    obj["weights"]["c_impact"] += 0.05  # 和 != 1
    _write(tmp_path, obj)
    with pytest.raises(nw.NarrativeWeightsError):
        nw.load_narrative_weights(tmp_path)


def test_weight_out_of_range_raises(tmp_path):
    obj = _valid_config()
    obj["weights"]["c_conflict"] = 1.5
    _write(tmp_path, obj)
    with pytest.raises(nw.NarrativeWeightsError):
        nw.load_narrative_weights(tmp_path)


def test_unknown_weight_key_raises(tmp_path):
    obj = _valid_config()
    obj["weights"]["c_bogus"] = 0.0
    _write(tmp_path, obj)
    with pytest.raises(nw.NarrativeWeightsError):
        nw.load_narrative_weights(tmp_path)


def test_missing_threshold_raises(tmp_path):
    obj = _valid_config()
    del obj["thresholds"]["delta_slots"]
    _write(tmp_path, obj)
    with pytest.raises(nw.NarrativeWeightsError):
        nw.load_narrative_weights(tmp_path)


def test_non_positive_k_top_raises(tmp_path):
    obj = _valid_config()
    obj["thresholds"]["k_top"] = 0
    _write(tmp_path, obj)
    with pytest.raises(nw.NarrativeWeightsError):
        nw.load_narrative_weights(tmp_path)


def test_feature_not_above_drama_raises(tmp_path):
    obj = _valid_config()
    obj["thresholds"]["theta_feature"] = 0.2  # <= theta_drama
    _write(tmp_path, obj)
    with pytest.raises(nw.NarrativeWeightsError):
        nw.load_narrative_weights(tmp_path)


def test_bool_weight_rejected(tmp_path):
    obj = _valid_config()
    obj["weights"]["c_turn"] = True
    _write(tmp_path, obj)
    with pytest.raises(nw.NarrativeWeightsError):
        nw.load_narrative_weights(tmp_path)


def test_config_hash_changes_with_content(tmp_path):
    _write(tmp_path, _valid_config())
    h1 = nw.narrative_config_hash(tmp_path)
    obj = copy.deepcopy(_valid_config())
    obj["thresholds"]["theta_drama"] = 0.4
    _write(tmp_path, obj)
    h2 = nw.narrative_config_hash(tmp_path)
    assert h1 != h2
