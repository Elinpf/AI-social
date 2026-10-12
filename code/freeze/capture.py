"""可选 prompt 正文落盘（T227）——用户目标 #10 的解锁开关。

背景：`LLM_CALL` 只有 `prompt_hash`、响应缓存只有输出 `text` → **「有 output 无 input」**，
蒸馏/SFT 缺输入侧。本模块提供**可选**的 prompt 正文本地落盘。

**四控（硬要求）**：
1. **默认关**（`CaptureConfig.enabled=False`；配置指纹进 `engine_version`）。
2. **不落全量**：按 **purpose 选择**（默认只落有 input→output 价值的 `dialogue`/`reflect`；
   `judge`/`importance` 不落）或按**比例抽样**（确定性、可复现）。
3. **存储控住**：**压缩**（逐条 zlib+base64）+ **容量上限**（超限即停写）+ **到期清理**（TTL）。
4. **脱敏硬门**：落盘前**剔除**端点/密钥痕迹，并**扫描残留**——**扫不到才写**（否则拒写并计数）。

⚠️ 存储安全（inode）：**单文件 append**（1 个文件），避免逐条建文件。
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional

# 默认落盘 purpose（有明确 input→output 价值；judge/importance 输入巨大、输出是标签 → 不落）
DEFAULT_CAPTURE_PURPOSES: FrozenSet[str] = frozenset({"dialogue", "reflect"})
DEFAULT_EXCLUDE_PURPOSES: FrozenSet[str] = frozenset({"judge", "importance", "describe", "narrate"})

# 通用密钥/端点正则（兜底，不与显式 terms 冲突）
_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
_SK_RE = re.compile(r"sk-[A-Za-z0-9_\-]{6,}")
_BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{6,}")
_KV_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[\"']?[A-Za-z0-9._\-]{6,}")
_HEX32_RE = re.compile(r"\b[0-9a-fA-F]{32,}\b")

REDACTED = "[REDACTED]"


@dataclass
class CaptureConfig:
    """prompt 落盘配置（三态开关：off / sample / purpose）。"""

    enabled: bool = False
    mode: str = "purpose"          # "off" | "sample" | "purpose"
    sample_rate: float = 0.05      # mode="sample" 时的比例（0–1，确定性抽样）
    purposes: FrozenSet[str] = field(default_factory=lambda: DEFAULT_CAPTURE_PURPOSES)
    exclude_purposes: FrozenSet[str] = field(default_factory=lambda: DEFAULT_EXCLUDE_PURPOSES)
    compress: bool = True
    max_bytes: int = 64 * 1024 * 1024   # 容量上限（默认 64MB）；超限停写
    ttl_seconds: int = 7 * 24 * 3600    # 到期清理（默认 7 天）
    dir: Optional[str] = None           # 落盘目录；缺省 = <cache_dir>/prompts

    def fingerprint(self) -> Dict[str, object]:
        """进 engine_version 的配置指纹（默认关也应可复现）。"""
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "sample_rate": self.sample_rate,
            "purposes": sorted(self.purposes),
            "exclude_purposes": sorted(self.exclude_purposes),
            "compress": self.compress,
            "max_bytes": self.max_bytes,
            "ttl_seconds": self.ttl_seconds,
        }


class PromptCapture:
    """prompt 正文落盘器（四控）。"""

    def __init__(
        self,
        config: CaptureConfig,
        *,
        root: str,
        redact_terms: Optional[List[str]] = None,
    ) -> None:
        self.config = config
        self.root = Path(root)
        self.redact_terms = [t for t in (redact_terms or []) if t]
        self.path = self.root / "prompts.jsonl"
        self.written = 0
        self.refused = 0     # 脱敏扫描未过，拒写
        self.skipped = 0     # 未命中抽样/用途
        self.capped = 0      # 超容量上限
        self.truncated = False  # 显式截断标记（不得静默停写）
        self._bytes = 0

    # ---------------- 开关 & 抽样（确定性） ----------------
    def is_active(self) -> bool:
        return bool(self.config.enabled and self.config.mode != "off")

    def should_capture(self, purpose: str, sample_key: str = "") -> bool:
        if not self.is_active():
            return False
        if purpose in self.config.exclude_purposes:
            return False
        if self.config.mode == "purpose":
            return purpose in self.config.purposes
        if self.config.mode == "sample":
            # 确定性抽样：按 sample_key 的稳定哈希取模，保证可复现
            h = zlib.crc32(sample_key.encode("utf-8")) & 0xFFFFFFFF
            return (h % 10000) < int(self.config.sample_rate * 10000)
        return False

    # ---------------- 脱敏硬门 ----------------
    def redact(self, text: str) -> str:
        if not text:
            return text
        out = text
        for term in self.redact_terms:                 # 显式端点/密钥
            out = out.replace(term, REDACTED)
        out = _URL_RE.sub(REDACTED, out)
        out = _SK_RE.sub(REDACTED, out)
        out = _BEARER_RE.sub(REDACTED, out)
        out = _KV_RE.sub(REDACTED, out)
        out = _HEX32_RE.sub(REDACTED, out)
        return out

    def scan_clean(self, text: str) -> bool:
        """扫描是否仍有端点/密钥残留（**扫不到才写**）。"""
        if not text:
            return True
        for term in self.redact_terms:
            if term and term in text:
                return False
        if _URL_RE.search(text) or _SK_RE.search(text) or _BEARER_RE.search(text):
            return False
        if _KV_RE.search(text) or _HEX32_RE.search(text):
            return False
        return True

    # ---------------- 写入（压缩 + 容量上限 + 启动 TTL 清理） ----------------
    def _maybe_cleanup(self) -> None:
        if not self.path.exists():
            return
        age = time.time() - self.path.stat().st_mtime
        if self.config.ttl_seconds > 0 and age > self.config.ttl_seconds:
            try:
                self.path.unlink()
            except OSError:
                pass
            self._bytes = 0

    def write(self, record: Dict[str, object]) -> bool:
        if not self.is_active():
            return False
        self._maybe_cleanup()
        if self.path.exists() and self._bytes == 0:
            self._bytes = self.path.stat().st_size
        if self.config.max_bytes and self._bytes >= self.config.max_bytes:
            self.capped += 1
            if not self.truncated:
                # **显式标记**（非静默停写）：文件内留一条 marker，供日后辨别"数据少 = 被上限截断"
                self.truncated = True
                self._append_raw({"_marker": "capture_truncated",
                                  "max_bytes": self.config.max_bytes}, plain=True)
            return False

        redacted = dict(record)
        for k in ("system", "user", "output"):
            if k in redacted and isinstance(redacted[k], str):
                redacted[k] = self.redact(redacted[k])
        # 只扫描**自由文本字段**（system/user/output）；我们自己的 cache_key/prompt_hash 等
        # 元数据（sha256:…）不算泄漏，不参与扫描，否则会被 32+hex 正则误伤。
        scan_text = "\n".join(
            str(redacted[k]) for k in ("system", "user", "output") if isinstance(redacted.get(k), str)
        )
        if not self.scan_clean(scan_text):
            self.refused += 1          # 扫到残留 → 拒写（硬门）
            return False

        self._append_raw(redacted)
        self.written += 1
        return True

    def _append_raw(self, obj: Dict[str, object], *, plain: bool = False) -> None:
        """单文件 append；压缩时逐条 zlib+base64（避免逐条建文件 → inode）。"""
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        if self.config.compress and not plain:
            line = json.dumps({"z": base64.b64encode(zlib.compress(payload)).decode("ascii")})
        else:
            line = payload.decode("utf-8")
        data = (line + "\n").encode("utf-8")
        self.root.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as fh:
            fh.write(data)
        self._bytes += len(data)

    def stats(self) -> Dict[str, object]:
        return {"written": self.written, "refused": self.refused,
                "skipped": self.skipped, "capped": self.capped,
                "truncated": self.truncated, "bytes": self._bytes}
