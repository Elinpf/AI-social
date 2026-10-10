"""T41：PERCEPTION_SCOPE 单一来源 + engine_version 指纹。"""

import copy
import json

import pytest

from engine import version
from engine.replay import replay_records
from engine.runner import run
from engine.state import state_hash


def test_perception_scope_missing_raises(tmp_path):
    with pytest.raises(version.PerceptionScopeError):
        version.load_perception_scope(tmp_path)


def test_perception_scope_version_mismatch_raises(tmp_path):
    (tmp_path / "perception_scope.json").write_text(json.dumps(
        {"version": "v0", "default_visibility_class": "place_local",
         "scope": {"MSG_PUBLIC": "global"}}), encoding="utf-8")
    with pytest.raises(version.PerceptionScopeError):
        version.load_perception_scope(tmp_path)


def test_perception_scope_bad_class_raises(tmp_path):
    (tmp_path / "perception_scope.json").write_text(json.dumps(
        {"version": version.REQUIRED_PERCEPTION_SCOPE_VERSION,
         "default_visibility_class": "place_local",
         "scope": {"MSG_PUBLIC": "nonsense"}}), encoding="utf-8")
    with pytest.raises(version.PerceptionScopeError):
        version.load_perception_scope(tmp_path)


def test_fingerprint_includes_repro_inputs():
    comps = version.component_digests()
    for name in ("default.json", "perception_scope.json", "topology.json"):
        assert comps[name] is not None, f"{name} 未纳入指纹"
    assert version.compute_fingerprint() == version.compute_fingerprint()
    # 单一来源：scope 恰来自引擎 config
    scope, default_cls, ver = version.load_perception_scope()
    assert ver == version.REQUIRED_PERCEPTION_SCOPE_VERSION
    assert "OBSERVATION" in scope and scope["OBSERVATION"] == "subject_only"


def test_world_init_commits_fingerprint():
    res = run(seed=1, rounds=3)
    wi = next(r for r in res["records"] if r["type"] == "WORLD_INIT")
    assert wi["payload"]["fingerprint"] == version.compute_fingerprint()
    assert wi["payload"]["config_components"]["perception_scope.json"] is not None


def test_assert_log_fingerprint_mismatch_raises():
    res = run(seed=1, rounds=2)
    recs = copy.deepcopy(res["records"])
    for r in recs:
        if r["type"] == "WORLD_INIT":
            r["payload"]["fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(version.ConfigError):
        version.assert_log_fingerprint(recs)


def test_replay_ok_when_fingerprint_matches():
    res = run(seed=1, rounds=3)
    s = replay_records(res["records"])  # 不应抛错
    assert state_hash(s) == res["final_state_hash"]


# ---- T44：engine_version.json + policy.json ----

def test_engine_version_and_policy_loaders():
    ev = version.load_engine_version()
    assert "components" in ev and ev["components"]["perception_scope"]["version"] == "v1.2-r2"
    pol = version.policy_defaults()
    assert pol["income_tax_bp"] == 1000
    assert "safety_valve.net_worth_floor_mu" in pol
    assert version.load_policy()["ubi_mu"]["min"] == 0


def test_engine_version_json_missing_raises(tmp_path):
    with pytest.raises(version.ConfigError):
        version.load_engine_version(tmp_path)


def test_policy_json_missing_raises(tmp_path):
    with pytest.raises(version.ConfigError):
        version.load_policy(tmp_path)


def test_fingerprint_includes_engine_version_and_policy():
    comps = version.component_digests()
    assert comps["engine_version.json"] is not None
    assert comps["policy.json"] is not None
    assert comps["llm.json"] is not None


def test_version_consistency_mismatch_raises(tmp_path):
    # 声明与实际 perception_scope 版本不一致 -> 报错
    (tmp_path / "perception_scope.json").write_text(json.dumps(
        {"version": "v0", "default_visibility_class": "place_local",
         "scope": {"MSG_PUBLIC": "global"}}), encoding="utf-8")
    (tmp_path / "engine_version.json").write_text(json.dumps(
        {"components": {"perception_scope": {"file": "perception_scope.json", "version": "v1.2-r2"}}}),
        encoding="utf-8")
    with pytest.raises(version.ConfigError):
        version.assert_version_consistency(tmp_path)


def test_real_config_is_consistent():
    version.assert_version_consistency()  # 不应抛错
