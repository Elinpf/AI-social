"""G-1 渲染期单变量取证探针（零网络 / 零计费 / 不产 run 目录）。

用法（在**被测树的 code/ 目录**为 cwd 运行，脚本本体放在主树 v2/evidence/）：
    cd <tree>/code && LIFE_PROMPT_GOSSIP_G1=<0|1|未设> \
        python3 <主树>/v2/evidence/g1_render_probe.py --out <json>

输出：两条提示词全文的 sha256、字符长度、render 环境指纹，供两树之间逐字节比对。
只用 life.llm.RuleBasedLLM 装配路径（不触发任何 LLM 请求），并先把 socket.socket
patch 成抛异常，任何网络尝试会直接失败。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
import tempfile
from pathlib import Path

_REAL_SOCKET = socket.socket


def _boom(*a, **k):
    raise RuntimeError("network blocked by probe (socket.socket patched)")


socket.socket = _boom  # 封死任何网络连接尝试

CONFIG = Path("config")
# 固定输入（两树必须逐字相同）：同 persona / 同 partners / 同 topic / 同 history
AGENT = "P003"
PARTNERS = ["P003", "P007"]
TOPIC = "今天的天气"
HISTORY = [("P007", "（叹气）唉，又闷又热。"), ("P003", "热啊。")]
# 默认探针 peers（可用 env G1_PROBE_PEERS 覆盖，用于复现真实跑批的 --agents N 规模：
# 真实跑批 peers=全体 agent id，--agents 4 ⇒ peers=4 ⇒ hint 至多 2 个名字）
PEERS = ["P001", "P003", "P005", "P007", "P009", "P011", "P013", "P015"]
# 反例自检钩子：G1_PROBE_INJECT_FAKE_NAME=<名字> 时，把该名字强行塞进某 peer 的显示名，
# 用来证明「名单越界断言」不是恒真（应触发 SystemExit(FAIL)）。
_FAKE = os.environ.get("G1_PROBE_INJECT_FAKE_NAME", "").strip()
_PEERS_ENV = os.environ.get("G1_PROBE_PEERS", "").strip()
if _PEERS_ENV:
    PEERS = [p for p in _PEERS_ENV.split(",") if p]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    sys.path.insert(0, str(Path.cwd()))
    from life.agent import LifeLayerAgent
    from life.memory import HashEmbeddingModel, SideStore
    from life.persona import load_personas
    from life.tests.support.mini_kernel import MiniKernel

    places = {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}
    personas = load_personas(CONFIG / "personas.json")
    persona = personas[AGENT]

    # 显示名词表：与运行期**完全同源**（orchestration/integration.py:1001 build_display_map）
    from life.dialogue_threads import build_display_map
    peer_names = {pid: name for pid, name in build_display_map(personas).items() if pid in PEERS}
    if _FAKE:
        # 反例自检：故意污染词表，断言必须炸
        peer_names["P001"] = _FAKE
        print(f"[negative-control] 已把 P001 显示名污染为 {_FAKE!r}")

    kernel = MiniKernel(seed=7, places=places)
    kernel._emit("AGENT_BORN", {"agent_id": AGENT, "home_place": persona.home_place,
                                "needs_init": persona.needs_init}, phase=0, actor="SYSTEM")
    tmp = Path(tempfile.mkdtemp(prefix="g1_render_probe_"))
    agent = LifeLayerAgent(AGENT, persona, kernel, side_store=SideStore(tmp / "side"),
                           embedding=HashEmbeddingModel(), places=places,
                           peers=PEERS, peer_names=peer_names)

    d = agent._dialogue_prompt("place_teahouse", PARTNERS)
    r = agent._reply_prompt("P007", TOPIC, HISTORY)

    # ---- 硬断言（fail-loud）：hint 名单必须 100% 来自 personas 词表，且不含自己/当前对话对象
    # 词表必须取自**未被污染的** personas 真源（不能用 peer_names，否则断言恒真）
    _true_map = build_display_map(personas)
    vocab = set(_true_map.values())
    self_name = _true_map.get(AGENT, AGENT)
    partner_names = {_true_map.get(p, p) for p in PARTNERS if p != AGENT}
    checks = {"hint_line_present": False, "hint_names": [], "names_all_in_personas": True,
              "names_exclude_self": True, "names_exclude_partners": True,
              "self_name": self_name, "partner_names": sorted(partner_names),
              "personas_vocab_size": len(vocab)}
    for txt in (d, r):
        for line in txt.splitlines():
            if line.startswith("镇上还住着："):
                checks["hint_line_present"] = True
                body = line[len("镇上还住着："):].split("。")[0]
                names = [n for n in body.split("、") if n]
                checks["hint_names"] = sorted(set(checks["hint_names"]) | set(names))
                checks["names_all_in_personas"] &= all(n in vocab for n in names)
                checks["names_exclude_self"] &= all(n != self_name for n in names)
                checks["names_exclude_partners"] &= all(n not in partner_names for n in names)
    missing = [n for n in checks["hint_names"] if n not in vocab]
    checks["names_not_in_personas"] = missing
    bad = (not checks["names_all_in_personas"] or not checks["names_exclude_self"]
           or not checks["names_exclude_partners"])
    if bad:
        raise SystemExit(f"[FAIL] hint 名单越界: {checks}")

    rec = {
        "tree_code_dir": str(Path.cwd()),
        "hint_checks": checks,
        "env_LIFE_PROMPT_GOSSIP_G1": os.environ.get("LIFE_PROMPT_GOSSIP_G1"),
        "gossip_enabled": bool(getattr(__import__("life.agent", fromlist=["x"]), "gossip_g1_enabled", lambda: None)()),
        "inputs": {"agent": AGENT, "partners": PARTNERS, "topic": TOPIC,
                   "history": HISTORY, "peers": PEERS, "tid": "place_teahouse"},
        "client_type": type(agent.llm).__module__ + "." + type(agent.llm).__name__,
        "provider": getattr(agent.llm, "provider", None),
        "socket_patched": socket.socket is _boom,
        "_dialogue_prompt": {
            "sha256": hashlib.sha256(d.encode("utf-8")).hexdigest(),
            "len_chars": len(d),
            "text": d,
        },
        "_reply_prompt": {
            "sha256": hashlib.sha256(r.encode("utf-8")).hexdigest(),
            "len_chars": len(r),
            "text": r,
        },
    }
    Path(args.out).write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print("dialogue sha256 =", rec["_dialogue_prompt"]["sha256"], "len =", rec["_dialogue_prompt"]["len_chars"])
    print("reply    sha256 =", rec["_reply_prompt"]["sha256"], "len =", rec["_reply_prompt"]["len_chars"])
    print("gossip_enabled =", rec["gossip_enabled"], "| provider =", rec["provider"],
          "| socket_patched =", rec["socket_patched"])
    print("out =", args.out)
    socket.socket = _REAL_SOCKET
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
