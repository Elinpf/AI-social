"""对话线程化（D2）：线程 id/回复指针/语境快照的**纯函数**helpers。

设计边界（对齐 Leader 裁决与 `v2/00-anchor.md`）：
  * 只产出**措辞与结构字段**，不产生任何世界态/数值后果（措辞不进判定，守 L-1）；
  * 全部函数**确定性**（无墙钟、无随机、无网络），只用入参；
  * 新增字段一律**只追加不改既有语义**，读侧 `.get()` 缺省 → 旧日志自然降级为「单发线程」。

字段契约（写入 `MSG_DM/MSG_PUBLIC/MSG_GROUP` 的 payload，由 `orchestration/integration.py::_do_social` 落盘）：
  thread_id      str            同一次「你来我往」共享；DM=`TH-<发起人>-<对端>-<发起round>`，
                                GROUP=`TH-<发起人>-G<group_id>-<round>`，
                                PUBLIC=`TH-<发起人>-PUB-<round>-<k>`（k 同 round 内自增，保证唯一）
  turn_index     int            线程内序号，0=发起，回复+1（连续无跳号）
  reply_to       str|None       被回复的 msg_id（发起为 None）；同线程内 seq 更早
  participants   list[str]      线程参与者（agent_id）
  ctx            dict           {relation:int, mood:str, need:{dim:int}, topic:str|None}

不进 state_hash（`engine/state.py::WorldState.to_dict()` 投影不含 event payload），只进事件哈希链。
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULTS = {
    "enabled": True,              # 线程化总开关（false = 回到「单发、无 thread 字段」旧行为）
    "max_turns": 6,               # 单线程最大轮数（含发起），到顶即封口
    "max_turns_per_round": 2,     # 单线程单回合最多推进轮数（K）
    "max_messages_per_slot": 2,   # 单 agent 单 slot 最多发出的 MSG 条数（发起+回复合计）
    "reply_window_rounds": 4,     # 入站消息在多少回合内仍可被回（超时即线程结束）[D9: 2→4 单变量]
    "history_turns": 3,           # 上下文装配只带最近 K 轮（控 token）
    "max_thread_chars": 240,      # 线程历史文本硬上限（控 token）
    "names_enabled": True,        # 邻居显示名注入（false = 回退到 persona_id 裸 ID）
}

OBSERVE_DEFAULTS = {
    "msg_enabled": True,          # MSG_* 是否进记忆（false = 断掉「措辞→记忆→检索」传导）
}

_MOOD_BY_NEED = {
    "energy": "疲惫",
    "satiety": "饥饿",
    "social": "孤单",
    "esteem": "低落",
    "mastery": "浮躁",
    "leisure": "紧绷",
}

# 角色称谓（用于同名消歧；只出现在提示词，不进事件/判定）
_ROLE_CN = {
    "farmer": "庄稼人", "craftsman": "手艺人", "cook": "厨子", "merchant": "买卖人",
    "healer": "郎中", "teacher": "教书先生", "public_servant": "当差的", "banker": "管账的",
    "artist": "画画的", "student": "读书人",
}


def _config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "life_v2.json"


def load_params(path: str | Path | None = None) -> dict:
    """读 `config/life_v2.json` 的 `dialogue` / `observe` 段（缺省值→默认开启）。"""
    p = Path(path) if path else _config_path()
    out = {"dialogue": dict(DEFAULTS), "observe": dict(OBSERVE_DEFAULTS)}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        if isinstance(data, dict):
            for sec in ("dialogue", "observe"):
                for k, v in (data.get(sec) or {}).items():
                    if k in out[sec]:
                        out[sec][k] = v
    # 运行时注入 hook（run_override.py --override life_v2.*=...；不落盘、不改指纹）
    try:
        from . import config as _lcfg
        ov = _lcfg.override_for("life_v2") or {}
        for sec in ("dialogue", "observe"):
            for k, v in (ov.get(sec) or {}).items():
                if k in out[sec]:
                    out[sec][k] = v
    except Exception:
        pass
    # env 一键回退（A/B 与回退用）
    import os
    if os.environ.get("HITT_DIALOGUE_THREADS") in ("0", "false", "off"):
        out["dialogue"]["enabled"] = False
    if os.environ.get("HITT_OBSERVE_MSG") in ("0", "false", "off"):
        out["observe"]["msg_enabled"] = False
    return out


def core_name(display_name: str) -> str:
    """「青溪镇·老周」→「老周」；无分隔符则原样返回。"""
    s = (display_name or "").strip()
    if not s:
        return ""
    return s.split("·")[-1].strip() or s


def build_display_map(personas: dict) -> dict:
    """{persona_id: 提示词用名字}（确定性；重名用角色称谓消歧）。"""
    cores = {pid: core_name(getattr(p, "display_name", "") or pid) for pid, p in personas.items()}
    counts: dict[str, int] = {}
    for name in cores.values():
        counts[name] = counts.get(name, 0) + 1
    out = {}
    for pid, p in personas.items():
        name = cores[pid]
        if counts.get(name, 0) > 1:
            role = getattr(p, "role_id", "") or ""
            out[pid] = f"{_ROLE_CN.get(role, role)}{name}"
        else:
            out[pid] = name
    return out


def mood_label(needs: dict) -> str:
    """确定性情绪词（字符串枚举）：取最匮乏的需求维度映射；全部 >=40 则「平和」。"""
    if not needs:
        return "平和"
    dim, val = min(needs.items(), key=lambda kv: (int(kv[1]), kv[0]))
    if int(val) >= 40:
        return "平和"
    return _MOOD_BY_NEED.get(dim, "平和")


def scarcest_need(needs: dict) -> dict:
    """{dim: value}（只带最匮乏的一维，控体积）。"""
    if not needs:
        return {}
    dim, val = min(needs.items(), key=lambda kv: (int(kv[1]), kv[0]))
    return {dim: int(val)}


def thread_id_dm(initiator: str, partner: str, round_no: int) -> str:
    return f"TH-{initiator}-{partner}-{int(round_no)}"


def thread_id_group(initiator: str, group_id: str, round_no: int) -> str:
    gid = (group_id or "").replace(":", "-")
    return f"TH-{initiator}-G{gid}-{int(round_no)}"


def thread_id_public(initiator: str, round_no: int, k: int) -> str:
    return f"TH-{initiator}-PUB-{int(round_no)}-{int(k)}"


def thread_initiator(thread_id: str | None) -> str | None:
    """从 thread_id 反解发起人（`TH-<发起人>-...`）；不合规格式返回 None。"""
    if not thread_id or not thread_id.startswith("TH-"):
        return None
    parts = thread_id.split("-")
    return parts[1] if len(parts) >= 2 and parts[1] else None


def is_replyable(ev_type: str, payload: dict, me: str) -> bool:
    """该条入站消息是否「对我说、且可被我回复」。只看可见性已由内核保证的 EventView。"""
    p = payload or {}
    if ev_type == "MSG_DM":
        return p.get("to") == me and (p.get("from") or "") != me
    if ev_type == "MSG_GROUP":
        parts = p.get("participants") or []
        return me in parts and (p.get("from") or "") != me
    return False
