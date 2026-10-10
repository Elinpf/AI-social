"""规范 JSON 与哈希工具测试。"""

from engine.canon import canonical_json, hash_obj


def test_key_order_is_deterministic():
    a = {"b": 1, "a": {"y": 2, "x": 3}}
    b = {"a": {"x": 3, "y": 2}, "b": 1}
    assert canonical_json(a) == canonical_json(b) == '{"a":{"x":3,"y":2},"b":1}'


def test_float_rounded_to_6():
    assert canonical_json({"x": 1 / 3}) == '{"x":0.333333}'


def test_hash_obj_stable_and_prefixed():
    h = hash_obj({"k": [1, 2, 3]})
    assert h.startswith("sha256:") and len(h) == len("sha256:") + 64
    assert h == hash_obj({"k": [1, 2, 3]})


def test_equivalent_to_freeze_canonical():
    """与 freeze/canonical.py 同源等价，避免两套 canonical 导致哈希不一致。"""
    import pytest

    try:
        from freeze import canonical as fc
    except Exception:  # freeze 层可能尚未就绪 / 独立测试
        pytest.skip("freeze.canonical 不可用")
    from engine import canon as ec

    assert fc.GENESIS_HASH == ec.GENESIS_HASH
    assert fc.FLOAT_ROUND == ec.FLOAT_ROUND
    samples = [
        {"b": 1, "a": {"y": 2, "x": 3}},
        {"x": 1 / 3, "nested": [1, 2, {"z": True}]},
        {"s": "青溪镇", "list": [1, 2, 3]},
    ]
    for s in samples:
        assert fc.canonical_json(s) == ec.canonical_json(s)
        assert fc.hash_obj(s) == ec.hash_obj(s)

