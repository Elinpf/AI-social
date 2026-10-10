"""确定性随机源（P4 / §1.4 / D-8）。

- 层级化：每个逻辑子系统分配独立 stream_id；
- 抽样序列由 (global_seed, stream_id, round, seq) 唯一确定；
- PRNG = SplitMix64，纯整数运算，禁浮点、禁墙钟/环境依赖；
- 子种子 = SHA-256(canonical_json([seed, stream_id, round, seq])) 前 8 字节 big-endian。
"""

from __future__ import annotations

from .canon import canonical_bytes, sha256_hex

MASK64 = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15
_MIX1 = 0xBF58476D1CE4E5B9
_MIX2 = 0x94D049BB133111EB


def splitmix64_next(state: int) -> tuple[int, int]:
    """SplitMix64 单步：返回 (new_state, output_u64)。"""
    x = (state + _GOLDEN) & MASK64
    z = x
    z = ((z ^ (z >> 30)) * _MIX1) & MASK64
    z = ((z ^ (z >> 27)) * _MIX2) & MASK64
    z = (z ^ (z >> 31)) & MASK64
    return x, z


def derive_subseed(global_seed: int, stream_id: str, round_no: int, seq: int) -> int:
    """子种子：SHA-256(canonical_json([seed, stream_id, round, seq])) 前 8 字节。"""
    h = sha256_hex(canonical_bytes([int(global_seed), str(stream_id), int(round_no), int(seq)]))
    return int(h[:16], 16)  # 前 8 字节 -> uint64（hex 前 16 字符）


def draw_u64(global_seed: int, stream_id: str, round_no: int, seq: int, n: int) -> list[int]:
    """确定性抽 n 个 uint64。同一 (seed, stream_id, round, seq, n) 恒等。"""
    if n < 0:
        raise ValueError("n 必须 >= 0")
    state = derive_subseed(global_seed, stream_id, round_no, seq)
    out: list[int] = []
    for _ in range(n):
        state, val = splitmix64_next(state)
        out.append(val)
    return out


class RngStream:
    """单个 stream_id 下的确定性随机流。

    同一 stream 内以 (round, seq) 定位抽样点；不跨点复用状态，
    避免「一处抽样改变另一处序列」（§1.4）。
    """

    def __init__(self, global_seed: int, stream_id: str):
        self.global_seed = int(global_seed)
        self.stream_id = str(stream_id)

    def draw(self, round_no: int, seq: int, n: int) -> list[int]:
        return draw_u64(self.global_seed, self.stream_id, round_no, seq, n)

    def draw_int(self, round_no: int, seq: int, lo: int, hi: int) -> int:
        """在 [lo, hi] 上无偏抽整数（拒绝采样，纯整数）。"""
        if hi < lo:
            raise ValueError("hi 必须 >= lo")
        span = hi - lo + 1
        if span == 1:
            return lo
        # 拒绝采样上界：取 2^64 内 span 的最大整数倍
        limit = (1 << 64) - ((1 << 64) % span)
        cursor = 0
        while True:
            for v in draw_u64(self.global_seed, self.stream_id, round_no, seq * 1000 + cursor, 1):
                if v < limit:
                    return lo + (v % span)
            cursor += 1


class Ctx:
    """hook 上下文：只提供确定性随机与只读 config，禁止 I/O / 墙钟。"""

    def __init__(self, global_seed: int, config: dict, round_no: int = 0, phase: int = 0):
        self.global_seed = int(global_seed)
        self.config = config
        self.round_no = int(round_no)
        self.phase = int(phase)

    def rng(self, stream_id: str, seq: int, n: int) -> list[int]:
        return draw_u64(self.global_seed, stream_id, self.round_no, seq, n)

    def derive_time(self, round_no: int) -> dict:
        """life 层 Ctx 协议：round -> 时间坐标（纯函数）。"""
        from .time import derive_time as _derive
        tcfg = self.config.get("time_config") if isinstance(self.config, dict) else None
        return _derive(round_no, tcfg)

    def stream(self, stream_id: str) -> RngStream:
        return RngStream(self.global_seed, stream_id)

    def at(self, round_no: int, phase: int) -> "Ctx":
        return Ctx(self.global_seed, self.config, round_no, phase)
