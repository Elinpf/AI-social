"""CLI 入口与 run() API。

run(seed, config, rounds) 跑空世界（只有出生/初始注入）N 回合，返回日志与最终状态。
"""

from __future__ import annotations

import json
from pathlib import Path

from .kernel import Engine
from .state import state_hash

_CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def load_config(path: str | Path | None = None) -> dict:
    """加载实验配置，并把**政策参数层** `config/policy.json` 合并进 `config["policy"]`。

    hook 不能做 I/O，故政策档（含 `lifecycle` 等）在运行时经 `ctx.config["policy"]` 只读访问；
    policy.json 已纳入 engine_version 指纹（`engine.version.FINGERPRINT_FILES`），口径受指纹保护。
    缺失/非法 → `ConfigError`（硬报错，不回退）。
    """
    p = Path(path) if path else (_CONFIG_DIR / "default.json")
    with open(p, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    from .version import load_policy
    cfg["policy"] = load_policy()  # 合并政策档（缺失→ConfigError）
    return cfg


def default_config() -> dict:
    return load_config()


def run(seed: int, config: dict | None = None, rounds: int = 20) -> dict:
    """运行空世界 N 回合。

    返回 {records, final_state, final_state_hash, seed, engine_version, chain_ok}。
    """
    if config is None:
        config = default_config()
    eng = Engine(seed, config)
    state = eng.run(rounds)
    chain_ok, chain_err = eng.ledger.verify_chain()
    return {
        "records": eng.ledger.records,
        "final_state": state,
        "final_state_hash": state_hash(state),
        "seed": int(seed),
        "engine_version": eng.engine_version,
        "rounds": int(rounds),
        "chain_ok": chain_ok,
        "chain_error": chain_err,
    }


def write_log(records: list, path: str | Path) -> None:
    """落盘 JSONL（每行一条记录，规范键排序）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            f.write("\n")


def read_log(path: str | Path) -> list:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
