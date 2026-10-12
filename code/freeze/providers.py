"""可插拔 LLM / 嵌入 provider。

冻结层不硬编码任何单一厂商。约定 ``Provider`` 协议后，内置三种实现：

- :class:`MockProvider` —— 离线确定性（测试/骨架用，**无网络**）。
- :class:`OpenAICompatProvider` —— 任意 OpenAI 兼容端点（``/chat/completions``）。
- :class:`OllamaProvider` —— 本地 Ollama（``/api/chat``、``/api/embeddings``）。

参考 AI Town ``llm.ts`` 的可插拔思路：调用方（LLMClient）只依赖协议，
通过 ``model_by_tier`` 支持「T2 用强模型、T1 用便宜模型」的档位映射。
"""

from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

from .canonical import digest, sha256_hex

DEFAULT_TIMEOUT = 60


@dataclass
class ProviderResponse:
    """provider 返回的规范化结果。"""

    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)
    #: 可空：判别式路径的 `choices[0].logprobs`（含 content/top_logprobs），用于取候选分差 margin。
    logprobs: Optional[Dict[str, Any]] = None


class Provider(Protocol):
    """LLM provider 协议。"""

    name: str

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        tier: str = "T2",
        extra: Optional[Dict[str, Any]] = None,
    ) -> ProviderResponse:  # pragma: no cover - 协议声明
        ...

    def embed(self, text: str, *, model: Optional[str] = None) -> List[float]:
        ...  # pragma: no cover


# --------------------------------------------------------------------------- #
# Mock：离线确定性，不触网
# --------------------------------------------------------------------------- #

class MockProvider:
    """离线确定性 provider（测试 / 无网络骨架默认使用）。

    - 默认对同一 prompt 生成**确定性文本**（基于 prompt 哈希），便于复现。
    - 可注入 ``responder(system, user, extra) -> str`` 定制返回（如返回判定选项）。
    - ``embed_dim`` 维确定性向量。
    """

    name = "mock"

    def __init__(
        self,
        model: str = "mock-1",
        *,
        model_by_tier: Optional[Dict[str, str]] = None,
        responder: Optional[Callable[[str, str, Dict[str, Any]], str]] = None,
        embed_dim: int = 8,
        embed_model: str = "mock-embed-1",
        tokens: int = 8,
    ) -> None:
        self.model = model
        self.model_by_tier = model_by_tier or {}
        self.responder = responder
        self.embed_dim = embed_dim
        self.embed_model = embed_model
        self.tokens = tokens
        self.calls = 0
        self.embed_calls = 0
        self.last_prompts: List[str] = []

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        tier: str = "T2",
        extra: Optional[Dict[str, Any]] = None,
    ) -> ProviderResponse:
        self.calls += 1
        self.last_prompts.append(user)
        resolved = model or self.model_by_tier.get(tier) or self.model
        extra = extra or {}
        opts = extra.get("options")
        if self.responder is not None:
            text = self.responder(system, user, extra)
        elif opts:
            # 软判定：**确定性地**从 envelope.options 中选一个（保证 decision ∈ options、可复现）。
            h = int(sha256_hex(system + "\x00" + user)[:16], 16)
            text = str(opts[h % len(opts)])
        else:
            text = f"mock::{sha256_hex(system + '\x00' + user)[:16]}"

        logprobs = None
        if extra.get("logprobs"):
            # 合成确定性 logprobs：被选 label 高概率，其余选项按序递减，取 top-2 分差。
            cand = list(opts) if opts else [text]
            chosen = text if text in cand else cand[0]
            base = 0.90
            lps = []
            for i, o in enumerate(cand):
                lps.append({"token": str(o), "logprob": math.log(max(base - i * 0.2, 0.01))})
            # content：被选 token 带 top_logprobs
            top = [{"token": str(o), "logprob": math.log(max(base - i * 0.2, 0.01))}
                   for i, o in enumerate(cand)]
            logprobs = {"content": [{"token": chosen,
                                     "logprob": math.log(max(base - cand.index(chosen) * 0.2, 0.01)),
                                     "top_logprobs": top}]}
        return ProviderResponse(
            text=text,
            model=resolved,
            tokens_in=self.tokens,
            tokens_out=self.tokens,
            logprobs=logprobs,
        )

    def embed(self, text: str, *, model: Optional[str] = None) -> List[float]:
        self.embed_calls += 1
        seed = sha256_hex((model or self.embed_model) + "\x00" + text)
        # 由哈希确定性派生 [0,1) 浮点向量
        vec: List[float] = []
        for i in range(self.embed_dim):
            chunk = seed[i * 4 : i * 4 + 4] or "0000"
            vec.append(int(chunk, 16) / 0xFFFF)
        return vec


# --------------------------------------------------------------------------- #
# OpenAI 兼容端点
# --------------------------------------------------------------------------- #

class OpenAICompatProvider:
    """OpenAI 兼容 ``/chat/completions`` 端点（OpenAI/Azure/vLLM/本地网关等）。"""

    name = "openai_compat"

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        *,
        model_by_tier: Optional[Dict[str, str]] = None,
        embed_model: str = "text-embedding-3-small",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 2,
        retry_backoff: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.model_by_tier = model_by_tier or {}
        self.embed_model = embed_model
        self.timeout = timeout
        #: 瞬时错误（超时/连接失败/5xx/429）的重试次数（不含首次）。
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        #: 观测：累计 HTTP 尝试次数（含重试），用于审计/报告。
        self.http_attempts = 0
        #: 逻辑补全调用次数（用于冒烟/规模测试断言）。
        self.calls = 0

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            self.http_attempts += 1
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_err = RuntimeError(f"OpenAI 兼容端点 HTTP {exc.code}: {detail}")
                # 仅对瞬时错误（429/5xx）重试；4xx（鉴权/参数）不重试。
                if exc.code == 429 or 500 <= exc.code < 600:
                    if attempt < self.max_retries:
                        time.sleep(self.retry_backoff * (attempt + 1))
                        continue
                raise last_err from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_err = RuntimeError(f"OpenAI 兼容端点不可达/超时: {exc}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (attempt + 1))
                    continue
                raise last_err from exc
        raise last_err if last_err else RuntimeError("OpenAI 兼容端点调用失败")

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        tier: str = "T2",
        extra: Optional[Dict[str, Any]] = None,
    ) -> ProviderResponse:
        resolved = model or self.model_by_tier.get(tier) or self.model
        self.calls += 1
        body: Dict[str, Any] = {
            "model": resolved,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if extra:
            if extra.get("response_format"):
                body["response_format"] = extra["response_format"]
            # 用户要求：按 purpose/tier 控制 thinking（由冻结层 config 集中裁决后传入）。
            if extra.get("thinking") is not None:
                body["chat_template_kwargs"] = {"thinking": bool(extra["thinking"])}
            # 判别式路径：请求 per-token logprobs，用于候选分差 margin。
            if extra.get("logprobs"):
                body["logprobs"] = True
                if extra.get("top_logprobs"):
                    body["top_logprobs"] = int(extra["top_logprobs"])
        data = self._post("/chat/completions", body)
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content", "")
        usage = data.get("usage") or {}
        return ProviderResponse(
            text=text,
            model=data.get("model", resolved),
            tokens_in=int(usage.get("prompt_tokens", 0)),
            tokens_out=int(usage.get("completion_tokens", 0)),
            raw=data,
            logprobs=choice.get("logprobs"),
        )

    def embed(self, text: str, *, model: Optional[str] = None) -> List[float]:
        resolved = model or self.embed_model
        data = self._post("/embeddings", {"model": resolved, "input": text})
        return list((data.get("data") or [{}])[0].get("embedding", []))


# --------------------------------------------------------------------------- #
# 本地 Ollama
# --------------------------------------------------------------------------- #

class OllamaProvider:
    """本地 Ollama（``/api/chat`` + ``/api/embeddings``）。"""

    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        *,
        model_by_tier: Optional[Dict[str, str]] = None,
        embed_model: str = "nomic-embed-text",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.model_by_tier = model_by_tier or {}
        self.embed_model = embed_model
        self.timeout = timeout

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:  # pragma: no cover - 网络路径
            raise RuntimeError(f"Ollama 端点不可达: {exc}") from exc

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        tier: str = "T2",
        extra: Optional[Dict[str, Any]] = None,
    ) -> ProviderResponse:
        resolved = model or self.model_by_tier.get(tier) or self.model
        body = {
            "model": resolved,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        data = self._post("/api/chat", body)
        text = (data.get("message") or {}).get("content", "")
        return ProviderResponse(
            text=text,
            model=data.get("model", resolved),
            tokens_in=int(data.get("prompt_eval_count", 0)),
            tokens_out=int(data.get("eval_count", 0)),
            raw=data,
        )

    def embed(self, text: str, *, model: Optional[str] = None) -> List[float]:
        resolved = model or self.embed_model
        data = self._post("/api/embeddings", {"model": resolved, "prompt": text})
        return list(data.get("embedding", []))


# --------------------------------------------------------------------------- #
# 确定性词法相关度（token 级 feature hashing）——方案②（T48 采纳）
# --------------------------------------------------------------------------- #

class LexicalProvider:
    """**确定性词法相关度** provider（零依赖、可复现、可解释）。

    命名：`frozen://lexical-relevance-v1`。**不是语义嵌入**——它把文本映射为
    词面/词袋特征向量，向量余弦 ≈ **词面重叠**（token/标签/关键词）：

    - **可解释**：能说清「为什么想起这条记忆」= 词面/标签重叠；
    - **零依赖**：仅标准库；
    - **可复现**：同文本 → 同向量（逐位一致）。

    ⚠️ **保真度损失**：只保**词法**相似度，**丢失语义**——同义改写、跨表述的
    「相关往事」不会被检索到。**真语义相关性未验证**（方案① sentence-transformers
    为 P1 升级项）。
    """

    name = "lexical"

    def __init__(
        self,
        dim: int = 256,
        embed_model: str = "frozen://lexical-relevance-v1",
    ) -> None:
        self.dim = dim
        self.embed_model = embed_model
        self.embed_calls = 0

    # -- 分词：ASCII 词 + CJK 单字 + CJK 双字（bigram） -- #
    @staticmethod
    def _tokens(text: str) -> List[str]:
        toks: List[str] = []
        buf: List[str] = []
        prev_cjk: Optional[str] = None
        for ch in (text or "").lower():
            if ch.isascii() and (ch.isalnum() or ch == "_"):
                buf.append(ch)
                prev_cjk = None
                continue
            if buf:
                toks.append("w:" + "".join(buf))
                buf = []
            if "\u4e00" <= ch <= "\u9fff":  # CJK 统一表意文字
                toks.append("c:" + ch)
                if prev_cjk is not None:
                    toks.append("b:" + prev_cjk + ch)
                prev_cjk = ch
            else:
                prev_cjk = None
        if buf:
            toks.append("w:" + "".join(buf))
        return toks

    def embed(self, text: str, *, model: Optional[str] = None) -> List[float]:
        self.embed_calls += 1
        vec = [0.0] * self.dim
        for tok in self._tokens(text):
            h = int(sha256_hex(tok)[:16], 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 20) & 1 else -1.0
            vec[idx] += sign
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def complete(self, **kwargs) -> ProviderResponse:  # pragma: no cover - embed-only
        raise NotImplementedError("LexicalProvider 仅提供 embed（词法相关度）")


# --------------------------------------------------------------------------- #
# 环境驱动工厂（不硬编码单一厂商；从环境变量解析端点/密钥/模型）
# --------------------------------------------------------------------------- #

def provider_from_env(
    *,
    prefer: str = "auto",
    timeout: int = DEFAULT_TIMEOUT,
) -> Provider:
    """从环境变量构造 provider（**不硬编码厂商/密钥**）。

    解析优先级（按 ``prefer``）：

    1) ``prefer="auto"``：
       - 若设置了 ``FREEZE_LLM_BASE_URL``（或 ``OPENAI_API_BASE``）→ OpenAI 兼容。
       - 否则若设置了 ``OLLAMA_BASE_URL`` → Ollama。
       - 否则回退 :class:`MockProvider`（离线、无网络）。
    2) ``prefer="openai"`` 强制 OpenAI 兼容（从环境取端点/密钥，缺失即报错）。
    3) ``prefer="ollama"`` 强制 Ollama。
    4) ``prefer="mock"`` 强制 Mock。

    相关环境变量：
      - 端点：``FREEZE_LLM_BASE_URL`` / ``OPENAI_API_BASE``
      - 密钥：``FREEZE_LLM_API_KEY`` / ``OPENAI_API_KEY``
      - 模型：``FREEZE_LLM_MODEL`` / ``OPENAI_MODEL``（默认 ``gpt-4o-mini``）
      - Ollama：``OLLAMA_BASE_URL``、``OLLAMA_MODEL``
    """
    import os

    def _first(*names: str) -> Optional[str]:
        for n in names:
            v = os.environ.get(n)
            if v:
                return v
        return None

    if prefer == "mock":
        return MockProvider()

    if prefer == "lexical":
        return LexicalProvider()

    if prefer == "ollama":
        return OllamaProvider(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
            timeout=timeout,
        )

    oai_base = _first("FREEZE_LLM_BASE_URL", "OPENAI_API_BASE")
    oai_key = _first("FREEZE_LLM_API_KEY", "OPENAI_API_KEY")
    oai_model = _first("FREEZE_LLM_MODEL", "OPENAI_MODEL")
    ollama_base = os.environ.get("OLLAMA_BASE_URL")

    if prefer == "openai":
        if not oai_base:
            raise RuntimeError("prefer='openai' 但未设置 FREEZE_LLM_BASE_URL/OPENAI_API_BASE")
        return OpenAICompatProvider(
            base_url=oai_base,
            api_key=oai_key or "",
            model=oai_model or "gpt-4o-mini",
            timeout=timeout,
        )

    # auto
    if oai_base:
        return OpenAICompatProvider(
            base_url=oai_base,
            api_key=oai_key or "",
            model=oai_model or "gpt-4o-mini",
            timeout=timeout,
        )
    if ollama_base:
        return OllamaProvider(
            base_url=ollama_base,
            model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
            timeout=timeout,
        )
    return MockProvider()


__all__ = [
    "Provider",
    "ProviderResponse",
    "MockProvider",
    "OpenAICompatProvider",
    "OllamaProvider",
    "LexicalProvider",
    "provider_from_env",
]
