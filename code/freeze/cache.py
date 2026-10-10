"""冻结缓存存储（首跑落盘、重放读取）。

磁盘布局（``root`` = ``FreezeConfig.cache_dir``）::

    root/
      responses/<cache_key>.json     # LLM 补全结果（冻结）
      embeddings/<cache_key>.json    # 嵌入结果（冻结，含模型名/版本）
      judgments/<judgment_id>.json   # 冻结判定（IF-6 读回，绝不重调 LLM）

每个缓存文件都是规范 JSON，键已**包含 engine_version 与 prompt_hash**。
重放模式只读不写；文件不存在即缓存未命中（replay 下直接报错）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .canonical import digest

_CATEGORIES = ("responses", "embeddings", "judgments")


class FrozenStore:
    """基于文件系统的冻结缓存。"""

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        for cat in _CATEGORIES:
            (self.root / cat).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    def _path(self, category: str, key: str) -> Path:
        safe = key if key and all(c.isalnum() or c in "-_" for c in key) else digest(key)
        return self.root / category / f"{safe}.json"

    def _read(self, category: str, key: str) -> Optional[Dict[str, Any]]:
        p = self._path(category, key)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def _write(self, category: str, key: str, record: Dict[str, Any]) -> None:
        p = self._path(category, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    # -------------------------- 补全结果 ------------------------------ #
    def get_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        return self._read("responses", cache_key)

    def put_response(self, cache_key: str, record: Dict[str, Any]) -> None:
        self._write("responses", cache_key, record)

    def has_response(self, cache_key: str) -> bool:
        return self._path("responses", cache_key).exists()

    # -------------------------- 嵌入结果 ------------------------------ #
    def get_embedding(self, cache_key: str) -> Optional[Dict[str, Any]]:
        return self._read("embeddings", cache_key)

    def put_embedding(self, cache_key: str, record: Dict[str, Any]) -> None:
        self._write("embeddings", cache_key, record)

    def has_embedding(self, cache_key: str) -> bool:
        return self._path("embeddings", cache_key).exists()

    # -------------------------- 冻结判定 ------------------------------ #
    def get_judgment(self, judgment_id: str) -> Optional[Dict[str, Any]]:
        return self._read("judgments", judgment_id)

    def put_judgment(self, judgment_id: str, record: Dict[str, Any]) -> None:
        self._write("judgments", judgment_id, record)

    def has_judgment(self, judgment_id: str) -> bool:
        return self._path("judgments", judgment_id).exists()

    def judgment_ids(self) -> List[str]:
        return sorted(p.stem for p in (self.root / "judgments").glob("*.json"))

    def response_keys(self) -> List[str]:
        return sorted(p.stem for p in (self.root / "responses").glob("*.json"))
