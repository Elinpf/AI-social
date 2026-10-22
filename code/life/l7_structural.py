"""L-7 结构臂（L7S）：把「去重」从**生成后撞车重试**前移到**生成前的结构性约束**。

## 为什么要前移（问题定性，见 `docs/forensics/2026-10-22-repo-state.md` §6.3）

R12/R14/R15 三轮连续击穿 L-7（8-gram 近重复率 +9.72pp / +11.18pp），而 R12 的 DEQUP
臂（`life/anti_repeat.py`）已经证明**事后重试式去重**收不干净：
`collide()` 是「第一次生成已经套路了」才补救，`retry_suffix()` 再花一次 LLM 调用
（R12 实测 `retries=88=collisions=88`，重试率 17.25%），且重试**本身又是一次抽样**——
可能再次撞车、也可能把台词改坏。也就是说，「同 slot 内的台词不重复」这件事被交给了
**运气**（重试命中率），而不是被交给**结构**。

本模块的取舍：**不动配额、不动 config、不加重试**，只改「这一句该怎么组织」这一层——
在**调用模型之前**就把「开口方式 / 收束方式 / 具体落点」三件事用确定性的方式定下来，
并把「镇上刚刚已经用过的开头」作为显式禁忌清单提前摆给模型。

## 三条结构约束（全部生成前生效，零额外 LLM 调用）

  ① **开口方式轮转**（`OPEN_FORMS`）：6 选 1，由 `sha256(agent|day|slot|round|turn|mode|对象)`
     确定性指派。中文对话的 8-gram 撞车**绝大多数撞在同一批开场套路上**（先叫人名再客套、
     清一色「我……」起头），轮转直接把这些共享前缀拆开。
  ② **收束方式轮转**（`END_FORMS`）：4 选 1，与 ① 同源但取不同位，避免所有句子都以问号
     或同一语气词收尾（「……吧。」这类重复尾串同样是 8-gram 撞车的常见来源）。
  ③ **禁忌开头清单**（`_banned_openers`）：取最近说出口的若干句的**归一化前 4 字**，
     去重后作为「这几个开头镇上已经用过了，别再用」的显式禁令提前下发。
     ——这是 R12 `retry_suffix()` 那段信息（「你刚想说的那句撞了」）的**前移版本**：
     内容几乎相同，但**发生在生成前**，因此不需要第二次调用，也不再靠碰运气。

## 纪律（对齐项目既有旁路先例 F-4/F-6/G-1，但方向相反）

  * 开关：env `LIFE_PROMPT_L7_STRUCT`，**默认 ON**（本分支即处理臂）；设为
    `0/false/no/off` 时完全关闭，`plan()` 返回 None、`render()` 返回空串、
    `_dequp_body()` 退回原有 DEQUP 逻辑 ⇒ 提示词与接入前**逐字节一致**。
  * 不读不写 `code/config/*.json`，不进 `state_hash`、不改 `engine_version` 指纹；
  * 只在开启时向 `ctx.l7struct` 追加一个审计键（additive，与 `ctx.dequp` / `ctx.echo` 同一先例）；
  * 8-gram 口径**镜像** `tools/d5/dialogue_metrics.py::normalize_body`（不发明新口径），
    由 `code/tests/test_l7_structural.py` 守住不漂移；
  * 进程内状态（`_RECENT`）与 `anti_repeat` 同构：单进程跑批，`reset()` 供测试/重放使用。

**统计口径**：本模块只影响「台词怎么组织」，不改变任何指标定义；L-7 仍由官方脚本复算。
"""
from __future__ import annotations

import hashlib
import os
import re

#: 结构臂开关（**默认 ON**，`0/false/no/off` 关闭）
STRUCT_ENV = "LIFE_PROMPT_L7_STRUCT"
#: env 中表示「关闭」的取值
_OFF = {"0", "false", "no", "off"}

#: 与官方 L-7 一致的 shingle 长度（`dialogue_metrics.py:479` 用 8）
NGRAM = 8
#: 最近窗口：参与「禁忌开头」统计的台词条数
RECENT_MAX = 16
#: 禁忌清单里最多列几个开头（控 token）
BAN_SAMPLES = 4
#: 判断「一个开头」用的归一化前缀长度
OPENER_CHARS = 4
#: 单条禁忌开头的展示截断
LINE_CHARS = 8

#: ① 开口方式：6 种互不相同的**结构**（不是措辞模板，模型仍自由造句）
OPEN_FORMS = (
    ("先叫对方一声再开口", "开口先叫一声对方的名字/称呼，再直接说事"),
    ("先说自己在做什么", "开口先讲你眼下自己正在做的事或碰到的事，再说对方"),
    ("先问对方一句", "开口先问对方一句关于他眼下处境的话，不要先叫名字"),
    ("用语气词起头", "开口用一个语气词起头（唉／哎／哦／哟 之类，只用一个），再说事"),
    ("接住上一句里的词", "开口先接住对方（或刚才话题里）的一个词，顺着那个词往下说"),
    ("先一句感慨再落到具体事", "开口先说一句短的感慨，随即落到一件具体的事上"),
)

#: ② 收束方式：4 种结构
END_FORMS = (
    ("以问句收", "最后用一个问句收住，把话头递回给对方"),
    ("用很短的一句收", "最后一句要短（不超过六个字），干脆收住"),
    ("用语气词收", "最后用「吧／呢／啊／呀／嘛」这类语气词收住，不要用问号"),
    ("落在具体小事上收", "最后落在一件具体的小事上收住（不总结、不感叹、不问问题）"),
)

#: 进程内状态：**只用于测试/重放清零**，不参与任何输出。
#: （R17 教训：`test_periodic_flush` / `test_resume_from_flush` 要求「同 seed 两次跑逐字节一致」，
#:  任何跨 run 残留的进程级状态都会破坏这一性质 ⇒ 禁忌开头的取材改为**从该 agent 的可见事件
#:  `wv.visible_events` 里现取**，天然与 replay 一致，不存在跨 run 污染。）
_STATE: dict = {"calls": 0}


def enabled() -> bool:
    """结构臂开关：默认 ON；`LIFE_PROMPT_L7_STRUCT ∈ {0,false,no,off}` 时关闭。"""
    return os.environ.get(STRUCT_ENV, "").strip().lower() not in _OFF


def reset() -> None:
    _STATE["calls"] = 0


# ---- 口径镜像 ---------------------------------------------------------------
def normalize(body: str) -> str:
    """**镜像** `tools/d5/dialogue_metrics.py::normalize_body`（改这里必须同步改那边）。"""
    s = (body or "").strip().lower()
    s = s.replace("（", "(").replace("）", ")")
    return re.sub(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)\[\]【】]", "", s)


def shingles(body: str) -> set[str]:
    t = normalize(body)
    return {t[i:i + NGRAM] for i in range(max(0, len(t) - NGRAM + 1))}


# ---- 确定性指派 -------------------------------------------------------------
def _h(*parts) -> int:
    """稳定哈希（不用内置 hash，避免 PYTHONHASHSEED 影响可复现性）。"""
    key = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:12], 16)


def assign(speaker: str, partners, day: int, slot: str, round_no: int,
           turn: int, mode: str) -> tuple[int, int]:
    """确定性指派 (开口方式序号, 收束方式序号)；同一组入参恒等，跨 agent 近似均匀。"""
    n = _h(speaker, ",".join(sorted(partners or ())), day, slot, round_no, turn, mode)
    return n % len(OPEN_FORMS), (n // len(OPEN_FORMS)) % len(END_FORMS)


# ---- ③ 禁忌开头 -------------------------------------------------------------
def recent_bodies(wv, agent_id: str | None = None) -> list[str]:
    """从**可见事件**里取最近说出口的台词正文本（新→旧），最多 `RECENT_MAX` 条。

    只读 `wv.visible_events`（内核已做可见性过滤），**不读进程级状态** ⇒ 与
    replay/续跑逐字节一致（`test_periodic_flush` / `test_resume_from_flush` 硬约束）。
    """
    out: list[str] = []
    for ev in reversed(list(getattr(wv, "visible_events", []) or [])):
        if getattr(ev, "type", "") not in ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC"):
            continue
        body = ((getattr(ev, "payload", None) or {}).get("body") or "").strip()
        if not body:
            continue
        out.append(body)
        if len(out) >= RECENT_MAX:
            break
    return out


def _banned_openers(bodies) -> list[str]:
    """给定台词序列（新→旧）⇒ 归一化前 4 字（去重、保序、最多 `BAN_SAMPLES` 个）。"""
    out: list[str] = []
    for body in bodies or ():
        t = normalize(body)
        if len(t) < OPENER_CHARS:
            continue
        head = t[:OPENER_CHARS]
        if head in out:
            continue
        out.append(head)
        if len(out) >= BAN_SAMPLES:
            break
    return out


# ---- 生成前的约束计划 -------------------------------------------------------
def plan(speaker: str, partners, day: int, slot: str, round_no: int,
         turn: int, mode: str, recent=()) -> dict | None:
    """生成前算出「这一句该怎么组织」；关闭时返回 None（⇒ 提示词零扰动）。

    `recent`：该 agent **可见**的最近台词（新→旧，来自 `recent_bodies(wv)`），
    用于生成禁忌开头清单。**不读进程状态** ⇒ 续跑/replay 逐字节可复现。
    """
    if not enabled():
        return None
    oi, ei = assign(speaker, partners, day, slot, round_no, turn, mode)
    _STATE["calls"] += 1
    return {
        "v": "l7-struct/1",
        "open": oi, "open_name": OPEN_FORMS[oi][0],
        "end": ei, "end_name": END_FORMS[ei][0],
        "banned": _banned_openers(recent),
        "mode": mode,
    }


def render(pl: dict | None) -> str:
    """把计划渲染成提示词里**一段**插入（关闭/None ⇒ 空串）。"""
    if not pl or not enabled():
        return ""
    seg = (f"\n这一句换个说法：{OPEN_FORMS[pl['open']][1]}；{END_FORMS[pl['end']][1]}。"
           "\n（句子里要有一件具体的东西——你正做着的活、手里的东西、谁家的谁——"
           "不要只讲空泛的感受。）")
    banned = pl.get("banned") or []
    if banned:
        seg += ("\n这几个开头镇上最近已经有人用过了，别再用："
                + "、".join(f"「{b[:LINE_CHARS]}」" for b in banned) + "。")
    return seg


def remember(body: str) -> None:
    """R17 起**无状态**：最近台词的取材已改为 `recent_bodies(wv)`（replay 安全）。

    保留本函数只为兼容接线点与单测；它不做任何事，也不产生任何输出差异。
    """
    return None


def audit(pl: dict | None) -> dict | None:
    """开启时追加进 `ctx.l7struct` 的审计字段（关闭/未计划 ⇒ None ⇒ 不多键）。"""
    if not pl or not enabled():
        return None
    return {
        "v": "l7-struct/1",
        "open": int(pl["open"]), "open_name": pl["open_name"],
        "end": int(pl["end"]), "end_name": pl["end_name"],
        "n_banned": len(pl.get("banned") or []),
        "mode": pl.get("mode"),
    }
