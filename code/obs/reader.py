"""只读事件日志句柄（IF-4 输入侧）。

`ReadOnlyLog` 是观测层对 `EventLog` 的**只读视图**：不修改、不追加、不写世界。
依赖白名单（架构 §1.3）：仅 `engine.ledger`（`verify_chain`，只读校验）与
`engine.canon`（`canonical_json`/`hash_obj`，纯函数，避免复制序列化导致字节漂移）。
**禁止** import `engine.state` / `engine.replay` / `engine.arbiter` / `engine.hooks`
（写路径）以及 `life.*` / `freeze.*`。
"""

from __future__ import annotations

from engine.canon import hash_obj
from engine.ledger import verify_chain


class ReadOnlyLog:
    """事件记录的不可变只读包装。

    构造即做一次哈希链校验（可选）；非法日志拒绝观测（15 §5）。
    """

    def __init__(self, records, *, verify: bool = True):
        self._records = list(records)
        self._by_type: dict[str, list] | None = None
        self.chain_ok: bool = True
        self.chain_error: str | None = None
        if verify:
            ok, err = verify_chain(self._records)
            self.chain_ok, self.chain_error = ok, err

    # ---- 访问 ----
    @property
    def records(self) -> list:
        return self._records

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records)

    def index_by_type(self) -> dict[str, list]:
        if self._by_type is None:
            d: dict[str, list] = {}
            for r in self._records:
                d.setdefault(r["type"], []).append(r)
            self._by_type = d
        return self._by_type

    def of_type(self, type_: str) -> list:
        return self.index_by_type().get(type_, [])

    def type_counts(self) -> dict[str, int]:
        return {t: len(v) for t, v in self.index_by_type().items()}

    def distinct_types(self) -> list[str]:
        return sorted(self.index_by_type().keys())

    # ---- 锚点 ----
    def last_seq(self) -> int:
        return self._records[-1]["seq"] if self._records else -1

    def log_hash(self) -> str:
        """日志规范指纹（对全部记录求规范哈希，'sha256:…'）。"""
        return hash_obj(self._records)

    def seed(self) -> int | None:
        for r in self._records:
            if r["type"] == "WORLD_INIT":
                return int(r["payload"].get("seed"))
        return None

    def max_round(self) -> int:
        return max((int(r["round"]) for r in self._records), default=-1)

    def require_chain(self) -> None:
        if not self.chain_ok:
            raise ValueError(f"哈希链校验失败，拒绝观测：{self.chain_error}")


__all__ = ["ReadOnlyLog"]
