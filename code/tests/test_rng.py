"""确定性随机源测试（SplitMix64，整数、禁浮点）。"""

from engine.rng import draw_u64, derive_subseed, splitmix64_next, RngStream


def test_draw_is_deterministic():
    a = draw_u64(12345, "market", 3, 0, 8)
    b = draw_u64(12345, "market", 3, 0, 8)
    assert a == b
    assert len(a) == 8


def test_streams_are_isolated():
    a = draw_u64(12345, "market", 3, 0, 4)
    b = draw_u64(12345, "comms", 3, 0, 4)
    assert a != b


def test_seq_and_round_change_sequence():
    assert draw_u64(1, "s", 0, 0, 4) != draw_u64(1, "s", 0, 1, 4)
    assert draw_u64(1, "s", 0, 0, 4) != draw_u64(1, "s", 1, 0, 4)


def test_outputs_are_u64_ints():
    for v in draw_u64(7, "init", 0, 0, 16):
        assert isinstance(v, int)
        assert 0 <= v < (1 << 64)


def test_splitmix_reference_vector():
    # SplitMix64 首输出（seed=0）标准测试向量
    _, out = splitmix64_next(0)
    assert out == 0xE220A8397B1DCDAF


def test_rejection_sampling_range():
    st = RngStream(999, "lifecycle")
    for seq in range(50):
        v = st.draw_int(0, seq, 3, 7)
        assert 3 <= v <= 7
