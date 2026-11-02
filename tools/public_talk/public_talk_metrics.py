#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「公开场合接话」维度的确定性尺子出数器（纯只读、零跑批、零 LLM、确定性输出）。

定位：只做描述性测量，**不修改任何行为代码**；不引入新编号体系
（CYCLE-16 / R23 已裁定不发明 F-9 类编号；本文件的分组一律用自解释 snake_case 键名）。

版本：v2（在 v1 基础上升级，v1 备份与差异见文件末「变更记录」）

==========================================================================
一、统计单位（钉死；先写口径后出数，读数算出后不得回改口径）
==========================================================================
    M实例 = 一条 `type == "MSG_PUBLIC"` 的日志事件 = 1 行 jsonl = 1 次公开发言。
            分母即 M实例 总数；不使用「人」「slot」「对话轮」等其它单位。
    msg_adjacent_pair = **在 MSG_*(MSG_DM/MSG_PUBLIC/MSG_GROUP) 子序列上**相邻的两条 MSG_PUBLIC。
            （原始行序口径另出 `raw_row_definition` 副读数，两个口径差异极大，引用时必须写明用哪个。）

==========================================================================
二、四组尺子量：分子 / 分母 / 字段来源
==========================================================================
第 1 组  msg_public_total
    分子 = MSG_PUBLIC 事件条数；分母 = 无（本量自身即分母）；ratio = None
    字段 = 顶层 `type`（行级）。d27_C 批中首次出现于 run.jsonl 第 54 行。

第 2 组  participants_length_dist
    分子 = `payload.participants` 长度严格 > 1 的条数
    分母 = M实例 总数
    字段 = `payload.participants`（数组，取 len）
    **关键实现要求（v2 修 D4）**：histogram **只统计「键存在且为数组」的样本**；
        缺键 / 非数组的样本进 `records_missing_key` / `records_nonarray` 单列，
        **绝不并进 `"0"` 桶**，否则会被直读成「N 条空数组」。
    semantics_note：participants 是「**线程参与者集合**（同一 thread_id 内取值恒定）」，
        **不是收件人**（DM 的收件人是 `to`），也不是消息级可见性开关；
        长度 > 1 不代表多人群聊、也不代表多人接话。措辞不得再用「在场/可见」这种模糊词。
    纪律 = 分母 ≥ 30 可给占比；分母 < 68 一律 probe=true。

第 3 组  reply_to_forms
    分子 = 每种 reply_to 形态各自的条数；分母 = M实例 总数
    字段 = `payload.reply_to`
    形态判定（互斥；先判**键是否存在**，再判类型，最后判值）：
        missing_key / json_null / string_None / empty_string / real_message_id
        / real_message_id_legacy_msg_id / other
    注：CYCLE-22 §4.3 自述的「取值集合恒 ['None']」= Python repr(None) = 本表 json_null；
        字符串 'None' 一条都没有。四者不可合并。
    **F-2 修复（口径版本 `ruler-f2/1`）**：`reply_to` 实际装的是被引用消息的
        `msg_uid`（形如 `"42:189"`），不是 `msg_id`；旧实现拿 `payload.msg_id` 集合去比
        ⇒ `real_message_id` **恒 0**（恒假阴性，不是「真的没人接话」）。
        现口径：`real_message_id` = `reply_to` 命中**任一消息事件（MSG_DM / MSG_PUBLIC /
        MSG_GROUP）的 `payload.msg_uid`**。`msg_id` 降级为**兼容回退**，命中单记
        `real_message_id_legacy_msg_id`，**不并入** `real_message_id` 分子 —— 因为真实日志里
        `msg_id` 不唯一（r41v ON 臂 PUB 30 条只有 8 个不同值，`"P-0-0"` 占绝大多数），
        按它算会把不同消息认成同一条。

第 4 组  place_adjacency
    口径 = 相邻两条 MSG_PUBLIC 是否同一 place；分母 = 相邻对数（M实例-1）
    字段 = `payload.place`
    实测 = d27_C 批 place 键存在、值恒 null（55/55）⇒ UNVERIFIED，
           在 missing_field 里写 `payload.place` 并区分「缺键」与「值为 null」。
           **不自造近似口径**（不用 slot / topic / PLACE_ARRIVED / ACTIVITY_STARTED 顶替，不插补）。
    出数条件 = place 键在 100% 的 M实例 上存在且非 null。

==========================================================================
三、schema 兼容闸（跨批必需；v0-anchor 批没有 participants / reply_to 键）
==========================================================================
* 取键一律先 `"key" in payload`；缺失计入 `schema_gate.missing_key_events` 并置
  `schema_gate.schema_compatible = false`；**严禁静默按 0 处理，也严禁 KeyError 崩掉**。
* `schema_gate.key_presence`：每个消息事件类型 × 每个字段 → 该字段存在的条数。
* 理由：v0-anchor（run_d2_before_n16_seed42，log sha c1f86bf6…、code_sha dc93c9d9、n16 r84）
  MSG_DM=132 / MSG_GROUP=7 / MSG_PUBLIC=48 的 participants、reply_to 键存在数均为 0。
* meta.json 缺失时：`code_sha=null`、`schema_compatible=false`、`scale` 全部 UNKNOWN。

==========================================================================
四、跑批身份（v2 修 D1/D2）
==========================================================================
* `inputs.code_sha` **一律取 meta.json 的 code_sha**（跑批时点的代码身份）；
  `inputs.repo_head_declared` 是**使用者声明的仓库 HEAD**（来自 `--repo-head`，缺省 null），
  **不是运行时实测值**，也不参与任何计算；两者不得混用。
* `scale`（seed / agents_n / rounds / model / provider）**一律从 meta.json 读**；
  读不到的字段写 "UNKNOWN"，**不得硬编码**（v1 曾硬编码「单 seed 42、n16r60、C 臂」，
  在 seed43 批与 v0 r84 批上照样这么写，是假读数）。
* 附带完整性交叉校验：meta.run_sha256 与实测 log sha256 是否一致 → `meta_run_sha256_matches_log`。
* `invocation.argv` 记录本次调用原文，使读数自描述、可复算（v1 用法漏 --meta 会差 3 个 inputs 键）。
* **D8 禁令**：读数**不得**在运行时读取任何外部可变状态（git HEAD、文件 mtime、时钟、随机数、环境变量）
  并写进被哈希的字段——否则「换个 HEAD 就复算不出」的证据等于没有证据。
  `--repo-head` 只接受显式传入，脚本自身**不调用 git**。

==========================================================================
五、跨批不变性与消息图旁证（probe，非判据）
==========================================================================
* `thread_isolation`：PUB thread_id 集合 vs DM thread_id 集合的交集条数。
* `msg_graph_degree`：PUB 在消息图中的入度 / 出度（DM 的 reply_to 命中 PUB msg_uid 的条数、
  PUB 自身 reply_to 非空条数、PUB refs 非空条数）。
* `pub_next_to_dm`：PUB 之后紧邻的是什么（MSG 子序列口径为主、原始行序口径为副）。
* `author_topic_crosstab`：谁在自言自语什么话题（下一轮提示词设计的输入）。
* `invariance_note`：三项尺子量在当前样本上是结构不变量、无鉴别力；**含反向约束**：
  本不变量不得被用于论证改造无效或改造有效，只能证「公开面未接线」。

==========================================================================
六、纪律实现
==========================================================================
* 纯只读：只 open(log, "r")；不写 code/life、code/orchestration、code/config、code/engine。
* 确定性：无 random、无 datetime.now（`--timestamp` 才写时间）、无字典遍历序依赖；
  已验证 PYTHONHASHSEED 变化不影响输出。
* 输出：json.dumps(..., sort_keys=True, ensure_ascii=False, indent=2) + 结尾换行。
* 分母 < 30 只报事件数不报比率；分母 < 68 一律 probe=true。

用法（**必须带 --meta**，否则 code_sha / scale 全 UNKNOWN 且 schema_compatible=false）：
    python3 tools/public_talk/public_talk_metrics.py \
        --log v2/evidence/run_d27_C_n16r60_seed42/run.jsonl \
        --meta v2/evidence/run_d27_C_n16r60_seed42/meta.json \
        --extra-log v2/evidence/run_r10e2e_n16r60_seed42/run.jsonl \
        --extra-log v2/evidence/run_d28_C_s43_n16r60_seed43/run.jsonl \
        --extra-log v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
        --extra-log v2/evidence/run_d2_before_n16_seed42/run.jsonl \
        --repo-head 009e95310c5221aef47c9c36f41ddad4f11e627b \
        --out v2/evidence/public_talk_readings_d27_C_n16r60_seed42.json

    `--repo-head` 为**官方口径必带**项（显式钉住 40 位 sha）；省略时 inputs.repo_head_declared = null，
    读数其余部分完全一致，sha 也一致——因为脚本不读取 git，本参数只作人工声明对照。

退出码：0 正常 / 2 输入缺失或无法解析

变更记录（v1 → v2，全部由复核实测驱动）：
    D1 头部用法补 --meta；新增 invocation.argv 使读数自描述。
    D2 code_sha 改取 meta.json（v1 误用 git HEAD 009e9531，与本批跑批身份 f2bf606b 不符）；
       scale 改从 meta 读，不再硬编码。
    D3 `thread_id_reuse`（反义，true 表示「无复用」）更名为 `each_msg_owns_thread`，旧名删除。
    D4 v0-anchor 的「键整体不存在」不再并进长度 0 / 全 null 桶，改由 schema_gate 单列报出。
    D7 (v3) invocation 中 --out 归一化为 <OUT>：读数 sha256 不再依赖输出文件路径，
       验收标准改为「不同 --out 路径两跑 sha256 相同」；inputs.log_path / meta_path 保持绝对路径（数据源身份）。
       semantics_note 措辞改为「线程参与者集合（同线程内一致）」，不再用「在场/可见」模糊词。
    D8 (v4) `repo_head_at_run`（运行时 git rev-parse）改为 `repo_head_declared`（`--repo-head` 显式传入，
       缺省 null）；脚本不再调用 git，读数与当前 HEAD 解耦。官方口径 = 显式钉住 40 位 sha。
    新增 schema_gate / cross_batch_invariance / invariance_note / thread_isolation /
       msg_graph_degree / pub_next_to_dm / author_topic_crosstab。
    F-2 (v5，口径版本 `ruler-f2/1`) `real_message_id` 匹配键由 `payload.msg_id` 改为
       `payload.msg_uid`（任一消息事件 DM/PUB/GROUP）。原实现恒 0：`reply_to` 装的是
       `msg_uid`（形如 `"42:189"`），而集合里放的是 `msg_id`，且 `msg_id` 在真实日志里
       **不唯一**。`msg_id` 降级为 `real_message_id_legacy_msg_id` 单列（不并入分子）。
       附带修正 `msg_graph_degree.pub_out_degree_reply_nonnull` 把该回退项一并计入。
       **口径改动不等于改善**：旧读数（含 `v2/evidence/r41v_public_talk_readings/*`）
       系旧口径，不得与新读数直接比大小。
    R44 (v6，口径版本 `public-talk-deg/2`) **只追加**入度主口径：
       `pub_in_degree_total_any` = 任一消息事件（DM/PUB/GROUP）的 `reply_to` 命中某条
       MSG_PUBLIC 的 `msg_uid` 的边数；配套 `pub_in_degree_by_channel` /
       `pub_replied_uid_count` / `pub_in_degree_zero_any` / `isolated_nodes_any`。
       旧字段 `pub_in_degree_total`（= 只数 DM 边）语义不变、降级为兼容口径：
       在 `HITT_DIALOGUE_PUBLIC_REPLY=1` 的批里它会把「公开面被公开面接住」的边
       整体漏掉（d47 实测 旧 0 / 新 4）⇒ 引用入度请用 `*_any`。
       同时把 `note` 从写死文案改为按实测值拼接（CYCLE-47 §159 登记的文案硬化）。
       **旧读数不得与新读数直接比大小**。
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from pathlib import Path

MSG_PUBLIC = "MSG_PUBLIC"
MSG_TYPES = ("MSG_PUBLIC", "MSG_DM", "MSG_GROUP")
KEY_FIELDS = (
    "author",
    "body",
    "msg_id",
    "msg_uid",
    "thread_id",
    "participants",
    "reply_to",
    "place",
    "scope",
    "turn_index",
    "refs",
    "topic",
)

RATIO_MIN_DEN = 30   # 分母 < 30：只报事件数，不报比率
PROBE_DEN = 68       # 分母 < 68：probe=true

UNKNOWN = "UNKNOWN"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frac(num, den):
    if num is None or not den or den < RATIO_MIN_DEN:
        return None
    return round(num / den, 6)


def probe_flag(den: int) -> bool:
    return den < PROBE_DEN


def reply_to_form(payload: dict, msg_ids: set | None = None,
                  msg_uids: set | None = None) -> str:
    """`payload.reply_to` 的形态判定（互斥；F-2 修复后按 `msg_uid` 匹配）。

    * `msg_uids`（主键口径）：**任一消息事件**（MSG_DM / MSG_PUBLIC / MSG_GROUP）的
      `payload.msg_uid` 集合。`reply_to` 装的就是它（实测形如 `"42:189"`），命中记
      `real_message_id`。
    * `msg_ids`（兼容回退）：`payload.msg_id` 集合。真实日志里 `msg_id` **不唯一**
      （r41v ON 臂：PUB 30 条只有 8 个不同 msg_id，其中 `"P-0-0"` 承担绝大多数），
      因此命中只记 `real_message_id_legacy_msg_id`，**不并入** `real_message_id` 分子，
      仅用于「上游确实按 msg_id 写的日志」的可审计回退。
    * 两个集合都不命中 ⇒ `other`（**不得**因集合为空/键名写错而误判成 `real_message_id`）。
    """
    if "reply_to" not in payload:
        return "missing_key"
    v = payload["reply_to"]
    if v is None:
        return "json_null"
    if isinstance(v, str):
        if v == "None":
            return "string_None"
        if v == "":
            return "empty_string"
        if msg_uids and v in msg_uids:
            return "real_message_id"
        if msg_ids and v in msg_ids:
            return "real_message_id_legacy_msg_id"
        return "other"
    return "other"


def empty_forms() -> dict:
    return {
        "missing_key": 0,
        "json_null": 0,
        "string_None": 0,
        "empty_string": 0,
        "real_message_id": 0,
        "real_message_id_legacy_msg_id": 0,
        "other": 0,
    }


def load_meta(path):
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def scale_from_meta(meta):
    """scale 一律从 meta 读；读不到写 UNKNOWN，不硬编码、不猜。"""
    unknown = []

    def pick(*keys):
        if not meta:
            return UNKNOWN
        for k in keys:
            if k in meta and meta[k] is not None:
                return meta[k]
        return UNKNOWN

    out = {
        "seed": pick("seed_in_log", "seed", "seed_declared"),
        "agents_n": pick("n_in_log", "n", "n_declared"),
        "rounds": pick("rounds_effective", "rounds_seen_max", "rounds", "rounds_declared"),
        "model": pick("model", "model_reported", "model_requested"),
        "provider": pick("provider"),
        "source": "meta.json" if meta else "meta.json 缺失",
    }
    for k in ("seed", "agents_n", "rounds", "model", "provider"):
        if out[k] == UNKNOWN:
            unknown.append(k)
    out["unknown_fields"] = unknown
    out["complete"] = not unknown
    return out



def scan_extra_log(path: Path) -> dict:
    """额外批次：只算三项尺子量 + 键存在性，不保留全部 payload。"""
    forms = empty_forms()
    len_hist: dict[int, int] = {}
    len_missing = len_nonarray = 0
    place_null = place_nonnull = place_missing = 0
    n = 0
    key_presence = {
        t: {"events": 0, **{f: 0 for f in ("participants", "reply_to", "place")}} for t in MSG_TYPES
    }
    msg_ids: set = set()
    # F-2：`reply_to` 装的是 `msg_uid` ⇒ 候选集合取**任一消息事件**的 msg_uid（不限于 PUB）
    msg_uids: set = set()
    keep: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            ev = json.loads(raw)
            t = ev.get("type")
            if t not in MSG_TYPES:
                continue
            pl = ev.get("payload") or {}
            kp = key_presence[t]
            kp["events"] += 1
            for fld in ("participants", "reply_to", "place"):
                if fld in pl:
                    kp[fld] += 1
            uid = pl.get("msg_uid")
            if isinstance(uid, str) and uid:
                msg_uids.add(uid)
            if t != MSG_PUBLIC:
                continue
            n += 1
            mid = pl.get("msg_id")
            if isinstance(mid, str):
                msg_ids.add(mid)
            keep.append(pl)
    for pl in keep:
        if "participants" not in pl:
            len_missing += 1
        elif not isinstance(pl["participants"], (list, tuple)):
            len_nonarray += 1
        else:
            ln = len(pl["participants"])
            len_hist[ln] = len_hist.get(ln, 0) + 1
        if "place" not in pl:
            place_missing += 1
        elif pl["place"] is None:
            place_null += 1
        else:
            place_nonnull += 1
    # 统一累加 reply_to 形态（需要在拿到完整 msg_uids / msg_ids 集合后再判 real_message_id）
    forms = empty_forms()
    for pl in keep:
        forms[reply_to_form(pl, msg_ids, msg_uids)] += 1
    meta = load_meta(path.parent / "meta.json")
    return {
        "log_path": str(path.resolve()),
        "log_sha256": sha256_file(path),
        "meta_path": str((path.parent / "meta.json").resolve()) if meta is not None else None,
        "code_sha": (meta or {}).get("code_sha", None) if meta else None,
        # 部分批（如 d12c_on）的 meta 是简化 schema，只有 7 位 'sha'，没有 code_sha；
        # 如实单列，不冒充完整 code_sha。
        "code_sha_short": (
            (meta or {}).get("sha") if meta and not (meta or {}).get("code_sha") else None
        ),
        "meta_schema": "full" if (meta or {}).get("code_sha") else ("simplified" if meta else "missing"),
        "msg_public_total": n,
        "participants_length_histogram": {str(k): len_hist[k] for k in sorted(len_hist)},
        "participants_records_missing_key": len_missing,
        "participants_records_nonarray": len_nonarray,
        "reply_to_forms": forms,
        "place_null": place_null,
        "place_nonnull": place_nonnull,
        "place_missing_key": place_missing,
        "key_presence": key_presence,
        "schema_compatible": bool(
            n > 0 and key_presence[MSG_PUBLIC]["participants"] == n and key_presence[MSG_PUBLIC]["reply_to"] == n
        ),
        "is_official_ruler": False,
    }


def normalize_argv(argv: list) -> list:
    """D7：把 --out 的取值归一化为占位符，使读数 sha256 不依赖输出文件路径。

    保留其余参数原文（--log / --meta / 全部 --extra-log / --timestamp 等），
    因此 argv_joined 仍是可复制的命令，只是把 --out 换成本地路径即可。
    """
    out: list = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--out":
            out.extend(["--out", "<OUT>"])
            i += 2
            continue
        if a.startswith("--out="):
            out.append("--out=<OUT>")
            i += 1
            continue
        out.append(a)
        i += 1
    return out


def msg_graph_degree_note(*, n_dm_reply: int, dm_hit_dm: int, dm_hit_pub: int,
                          pub_in_total_any: int, in_by_channel: dict,
                          pub_out_reply: int, pub_out_refs: int) -> str:
    """`msg_graph_degree.note` 的**唯一**生成点：全部数字来自实测，绝不写死结论。

    看板 A-4（原 A-3 / CYCLE-47 N-1）：旧 note 是一段写死的人话——「公开消息在消息图里
    入度 0、**出边 0**，是孤立节点」，而同一批实测 `isolated_nodes=false`、
    `pub_out_degree_reply_nonnull=4` ⇒ **文案与数字自相矛盾**。现在把「是不是孤立节点」
    这件事交给实测值判定（口径与 `isolated_nodes_any` 完全一致），note 里只陈述计数。
    本函数是纯函数，便于单测（见 `tools/public_talk/test_msg_graph_degree_note.py`）。
    """
    out_edges = pub_out_reply + pub_out_refs
    isolated = (pub_in_total_any == 0 and pub_out_reply == 0 and pub_out_refs == 0)
    head = (f"DM 的 reply_to 非空 {n_dm_reply} 条中命中 DM msg_uid {dm_hit_dm} 条、"
            f"命中 PUB msg_uid {dm_hit_pub} 条（dm-only 兼容口径）；"
            f"任一消息事件命中 PUB msg_uid = {pub_in_total_any} 条"
            f"（按类型：{dict(sorted(in_by_channel.items())) or '{}'}）⇒ ")
    if isolated:
        tail = (f"公开消息在消息图里入度 0、出边 {out_edges}"
                f"（= 回复边 {pub_out_reply} + refs {pub_out_refs}），按 public-talk-deg/2 判为孤立节点")
    else:
        tail = (f"公开消息入度 {pub_in_total_any}（其中被公开面接住 "
                f"{in_by_channel.get('MSG_PUBLIC', 0)} 条）、出边 {out_edges}"
                f"（= 回复边 {pub_out_reply} + refs {pub_out_refs}），不是孤立节点")
    return head + tail


def main() -> int:
    ap = argparse.ArgumentParser(description="公开场合接话：确定性尺子（只读、零跑批、零 LLM）")
    ap.add_argument("--log", required=True, help="主数据源 run.jsonl（唯一尺子数据源）")
    ap.add_argument("--meta", default=None, help="meta.json（**必带**：code_sha 与 scale 的唯一来源）")
    ap.add_argument("--out", default=None, help="输出 json 路径；省略则写 stdout")
    ap.add_argument("--extra-log", action="append", default=[], help="额外批次 run.jsonl（跨批不变性自检，可重复）")
    ap.add_argument(
        "--repo-head",
        default=None,
        help="**使用者声明**的仓库 HEAD（40 位 sha，可缺省为 null）；脚本自身不调用 git，"
             "该值只写入 inputs.repo_head_declared 供人工对照，不参与任何计算（D8）",
    )
    ap.add_argument("--timestamp", action="store_true", help="追加生成时间戳（默认关闭以保证逐字节可复算）")
    args = ap.parse_args()

    repo_head_declared = args.repo_head
    repo_head_valid = bool(
        isinstance(repo_head_declared, str)
        and len(repo_head_declared) == 40
        and all(c in "0123456789abcdef" for c in repo_head_declared.lower())
    )
    if repo_head_declared is not None and not repo_head_valid:
        print(
            f"[public_talk] 警告: --repo-head 不是 40 位 hex（得到 {repo_head_declared!r}），"
            "仍按传入值原样记录并置 repo_head_declared_valid=false",
            file=sys.stderr,
        )

    log_path = Path(args.log)
    if not log_path.is_file():
        print(f"[public_talk] 输入缺失: {log_path}", file=sys.stderr)
        return 2

    # ---------------- 单遍读取主数据源 ----------------
    lines = 0
    rows_msg: list[tuple[int, str, dict]] = []   # (行号, 类型, payload) 仅 MSG_*，保持行序
    first_line = None
    last_line = None
    key_presence = {t: {"events": 0, **{f: 0 for f in KEY_FIELDS}} for t in MSG_TYPES}
    raw_next_after_pub: list[str | None] = []    # 原始行序：PUB 下一行的事件类型
    next_row_cache: list[tuple[int, str]] = []   # (行号, 类型) 全部行

    with log_path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            lines += 1
            ev = json.loads(raw)
            t = ev.get("type")
            next_row_cache.append((lineno, t))
            if t not in MSG_TYPES:
                continue
            pl = ev.get("payload") or {}
            kp = key_presence[t]
            kp["events"] += 1
            for fld in KEY_FIELDS:
                if fld in pl:
                    kp[fld] += 1
            rows_msg.append((lineno, t, pl))
            if t == MSG_PUBLIC:
                if first_line is None:
                    first_line = lineno
                last_line = lineno

    pub_lines = [ln for ln, t, _ in rows_msg if t == MSG_PUBLIC]
    pub_payloads = [pl for _, t, pl in rows_msg if t == MSG_PUBLIC]
    dm_payloads = [pl for _, t, pl in rows_msg if t == "MSG_DM"]
    n = len(pub_payloads)

    msg_ids = {pl["msg_id"] for pl in pub_payloads if isinstance(pl.get("msg_id"), str)}
    # F-2：`reply_to` 装的是 `msg_uid` ⇒ 候选集合取**任一消息事件**（DM/PUB/GROUP）的 msg_uid。
    # 只取 PUB 会漏掉「公开面接的是私聊消息」这一类边（本批为 0，但口径不得先天排他）。
    msg_uids = {pl["msg_uid"] for _, _, pl in rows_msg if isinstance(pl.get("msg_uid"), str) and pl["msg_uid"]}
    kp_pub = key_presence[MSG_PUBLIC]
    missing = {
        "participants": n - kp_pub["participants"],
        "reply_to": n - kp_pub["reply_to"],
        "place": n - kp_pub["place"],
    }
    missing_any = sum(
        1 for pl in pub_payloads if ("participants" not in pl) or ("reply_to" not in pl)
    )

    # ---------------- meta / 跑批身份 ----------------
    meta = load_meta(args.meta)
    meta_sha256 = None
    meta_bytes = None
    if args.meta and Path(args.meta).is_file():
        meta_sha256 = sha256_file(Path(args.meta))
        meta_bytes = Path(args.meta).stat().st_size
    log_sha256 = sha256_file(log_path)
    code_sha = (meta or {}).get("code_sha") if meta else None
    meta_run_sha = (meta or {}).get("run_sha256") if meta else None
    scale = scale_from_meta(meta)

    schema_compatible = bool(n > 0 and missing_any == 0 and meta is not None)
    schema_incompat_reasons = []
    if meta is None:
        schema_incompat_reasons.append("meta.json 缺失：code_sha / scale 无法绑定跑批身份")
    if n == 0:
        schema_incompat_reasons.append("无 MSG_PUBLIC 事件")
    if missing_any:
        schema_incompat_reasons.append(f"MSG_PUBLIC 缺 participants 或 reply_to 键：{missing_any} 条")

    # ---------------- 第 1 组：MSG_PUBLIC 总条数 ----------------
    g_total = {
        "stat_unit": "MSG_PUBLIC 事件条数（1 条 = 1 行 jsonl = 1 次公开发言）",
        "value": n,
        "numerator": n,
        "denominator": None,
        "ratio": None,
        "probe": True if not n else probe_flag(n),
        "probe_reason": f"本量自身即分母；以它为分母的比率，分母 {n} < {PROBE_DEN} ⇒ 一律 probe",
        "field_source": "顶层字段 type == 'MSG_PUBLIC'",
        "line_span_in_log": {"first": first_line, "last": last_line},
    }

    # ---------------- 第 2 组：participants 长度分布（缺键不并入 0 桶） ----------------
    len_hist: dict[int, int] = {}
    rec_missing = rec_nonarray = 0
    for pl in pub_payloads:
        if "participants" not in pl:
            rec_missing += 1
            continue
        pts = pl["participants"]
        if not isinstance(pts, (list, tuple)):
            rec_nonarray += 1
            continue
        ln = len(pts)
        len_hist[ln] = len_hist.get(ln, 0) + 1
    gt1 = sum(c for ln, c in len_hist.items() if ln > 1)
    hist_total = sum(len_hist.values())

    # participants 的语义证据：同一 thread_id 内取值是否恒定 / 发送方是否在集合内
    thread_pts: dict[tuple, set] = {}
    sender_in = sender_total = 0
    for typ, pl in ([(MSG_PUBLIC, p) for p in pub_payloads] + [("MSG_DM", p) for p in dm_payloads]):
        sender = pl.get("author") if typ == MSG_PUBLIC else pl.get("from")
        pts = pl.get("participants")
        if isinstance(pts, (list, tuple)):
            sender_total += 1
            if sender in pts:
                sender_in += 1
        tid = pl.get("thread_id")
        if isinstance(tid, str):
            thread_pts.setdefault((typ, tid), set()).add(
                tuple(pts) if isinstance(pts, (list, tuple)) else None
            )
    inconsistent_threads = sum(1 for v in thread_pts.values() if len(v) > 1)

    g_participants = {
        "stat_unit": "M实例（MSG_PUBLIC 条）",
        "field_source": "payload.participants（数组，取 len）",
        "semantics_note": (
            "participants 为**线程参与者集合**（同一 thread_id 内取值恒定，本批实测 "
            f"{len(thread_pts)} 个线程中不一致者 {inconsistent_threads} 个），"
            "**不是收件人**（DM 的收件人是 `to`），也不是消息级可见性开关；"
            "长度 > 1 不代表多人群聊、也不代表多人接话。"
        ),
        "thread_consistency": {
            "threads_checked": len(thread_pts),
            "threads_with_inconsistent_participants": inconsistent_threads,
            "definition": "按 (事件类型, thread_id) 分组，组内 participants 元组是否唯一",
        },
        "sender_in_participants": {
            "numerator": sender_in,
            "denominator": sender_total,
            "note": "发送方 = MSG_PUBLIC 的 author / MSG_DM 的 from；DM 无 author 字段，不可用 author 判定",
        },
        "length_histogram": {str(k): len_hist[k] for k in sorted(len_hist)},
        "length_values_set": sorted(len_hist),
        "histogram_sample_denominator": hist_total,
        "records_missing_key": rec_missing,
        "records_nonarray": rec_nonarray,
        "bucket_policy": "histogram 仅含「键存在且为数组」的样本；缺键/非数组单列，绝不并入 \"0\" 桶",
        "numerator_len_gt_1": gt1,
        "denominator": n,
        "ratio_len_gt_1": frac(gt1, n),
        "ratio_suppressed_because_den_lt_30": n < RATIO_MIN_DEN,
        "probe": probe_flag(n),
        "probe_reason": f"分母 {n} < {PROBE_DEN}：占比只作点估计，不可作判据，不得写「显著」",
    }

    # ---------------- 第 3 组：reply_to 形态 ----------------
    forms = empty_forms()
    other_examples: list[dict] = []
    for pl in pub_payloads:
        fname = reply_to_form(pl, msg_ids, msg_uids)
        forms[fname] += 1
        if fname == "other" and len(other_examples) < 5:
            other_examples.append({"repr": repr(pl.get("reply_to"))})
    n_nonnull = n - forms["json_null"] - forms["missing_key"]
    g_reply_to = {
        "stat_unit": "M实例（MSG_PUBLIC 条）",
        "field_source": "payload.reply_to（键可能缺失 / 值可能为 null / 字符串）",
        "forms": forms,
        "other_examples": other_examples,
        "numerator_nonnull_reply_to": n_nonnull,
        "denominator": n,
        "ratio_nonnull_reply_to": frac(n_nonnull, n),
        "probe": probe_flag(n),
        "match_key_policy": {
            "ruler_version": "ruler-f2/1",
            "primary_key": "payload.msg_uid（任一消息事件 DM/PUB/GROUP）",
            "legacy_fallback_key": "payload.msg_id（命中单记 real_message_id_legacy_msg_id，不并入分子）",
            "why": "reply_to 装 msg_uid；msg_id 在真实日志里不唯一（PUB 30 条仅 8 个不同值）",
            "candidate_uids_n": len(msg_uids),
            "candidate_msg_ids_n": len(msg_ids),
        },
        "note": (
            "CYCLE-22 §4.3 自述的「取值集合恒 ['None']」= Python repr(None) = 本表 json_null；"
            "本表把 缺键 / JSON null / 字符串 'None' / 空串 分开计数，四者不可合并。"
            "F-2：`real_message_id` 自 ruler-f2/1 起按 msg_uid 匹配（旧实现按 msg_id ⇒ 恒 0）"
        ),
    }

    # ---------------- 第 4 组：相邻对是否同 place ----------------
    place_hist: dict[str, int] = {}
    for pl in pub_payloads:
        if "place" not in pl:
            k = "missing_key"
        elif pl["place"] is None:
            k = "null"
        else:
            k = str(pl["place"])
        place_hist[k] = place_hist.get(k, 0) + 1
    nonnull_place = sum(c for k, c in place_hist.items() if k not in ("null", "missing_key"))
    pairs_total = max(n - 1, 0)
    if n > 0 and nonnull_place == n:
        same = sum(1 for a, b in zip(pub_payloads, pub_payloads[1:]) if a["place"] == b["place"])
        g_place = {
            "stat_unit": "msg_adjacent_pair（MSG 子序列上相邻两条 MSG_PUBLIC 构成 1 对）",
            "status": "MEASURED",
            "field_source": "payload.place",
            "numerator_same_place_pairs": same,
            "denominator_pairs": pairs_total,
            "ratio_same_place": frac(same, pairs_total),
            "probe": probe_flag(pairs_total),
        }
    else:
        missing_kind = []
        if place_hist.get("missing_key"):
            missing_kind.append(f"缺键 {place_hist['missing_key']} 条")
        if place_hist.get("null"):
            missing_kind.append(f"值为 null {place_hist['null']} 条")
        g_place = {
            "stat_unit": "msg_adjacent_pair（MSG 子序列上相邻两条 MSG_PUBLIC 构成 1 对）",
            "status": "UNVERIFIED",
            "field_source": "payload.place",
            "missing_field": "payload.place",
            "missing_kind": "；".join(missing_kind) if missing_kind else "未知",
            "why": (
                ("place 键存在但值恒为 null" if place_hist.get("null") else "place 键缺失")
                + f"：非 null 覆盖 {nonnull_place}/{n} 条（覆盖率 {round(nonnull_place / n, 6) if n else None}），"
                "不满足 100% 覆盖 ⇒ 相邻对「同 place」无从判定。按纪律写 UNVERIFIED，"
                "不自造近似口径（不用 slot / topic / PLACE_ARRIVED / ACTIVITY_STARTED 顶替，不插补）。"
            ),
            "place_value_histogram": place_hist,
            "nonnull_place_records": nonnull_place,
            "denominator_pairs": pairs_total,
            "numerator_same_place_pairs": None,
            "ratio_same_place": None,
            "probe": True,
            "grep_commands_used": [
                "grep -c '\"type\":\"MSG_PUBLIC\"' <RUN>/run.jsonl   # -> 55",
                "grep '\"type\":\"MSG_PUBLIC\"' <RUN>/run.jsonl | grep -c '\"place\":null'   # -> 55",
                "grep '\"type\":\"MSG_PUBLIC\"' <RUN>/run.jsonl | grep -c '\"place\":[^n]'   # -> 0（非 null place 条数）",
                "grep '\"type\":\"MSG_PUBLIC\"' <RUN>/run.jsonl | grep -c '\"reply_to\":null'   # -> 55",
            ],
            "judgeable_at_this_scale": False,
        }

    # ---------------- 诊断（非尺子） ----------------
    authors = sorted({pl.get("author") for pl in pub_payloads if pl.get("author") is not None})
    pub_threads = {pl.get("thread_id") for pl in pub_payloads if pl.get("thread_id") is not None}
    dm_threads = {pl.get("thread_id") for pl in dm_payloads if pl.get("thread_id") is not None}
    topics: dict[str, int] = {}
    refs_hist: dict[int, int] = {}
    turn_hist: dict[int, int] = {}
    scopes: dict[str, int] = {}
    for pl in pub_payloads:
        t = pl.get("topic")
        k = "null" if t is None else str(t)
        topics[k] = topics.get(k, 0) + 1
        r = pl.get("refs")
        ln = len(r) if isinstance(r, (list, tuple)) else 0
        refs_hist[ln] = refs_hist.get(ln, 0) + 1
        ti = pl.get("turn_index")
        ti_k = ti if isinstance(ti, int) else -1
        turn_hist[ti_k] = turn_hist.get(ti_k, 0) + 1
        sc = pl.get("scope")
        sc_k = "missing_key" if sc is None else str(sc)
        scopes[sc_k] = scopes.get(sc_k, 0) + 1

    diag = {
        "stat_unit": "M实例（MSG_PUBLIC 条）",
        "distinct_authors": len(authors),
        "author_list": authors,
        "distinct_thread_ids": len(pub_threads),
        "each_msg_owns_thread": bool(n > 0 and len(pub_threads) == n),
        "each_msg_owns_thread_note": (
            "true = 无任何 thread_id 被复用（每条消息独占一个线程）；"
            "旧字段 thread_id_reuse 语义相反、已删除"
        ),
        "topic_histogram": {k: topics[k] for k in sorted(topics)},
        "refs_length_histogram": {str(k): refs_hist[k] for k in sorted(refs_hist)},
        "turn_index_histogram": {str(k): turn_hist[k] for k in sorted(turn_hist)},
        "scope_histogram": {k: scopes[k] for k in sorted(scopes)},
        "note": "仅作旁证，不构成任何判据；分母 55 < 68，全部 probe",
    }

    # ---------------- author × topic 交叉（下一轮提示词设计输入，非判据） ----------------
    crosstab: dict[str, dict[str, int]] = {a: {} for a in authors}
    for pl in pub_payloads:
        a = pl.get("author")
        if a is None:
            continue
        t = pl.get("topic")
        k = "null" if t is None else str(t)
        crosstab.setdefault(a, {})
        crosstab[a][k] = crosstab[a].get(k, 0) + 1
    breadth = {a: len(crosstab.get(a, {})) for a in sorted(crosstab)}
    author_topic = {
        "stat_unit": "M实例（MSG_PUBLIC 条）",
        "topic_totals": {k: topics[k] for k in sorted(topics)},
        "by_author": {a: dict(sorted(crosstab[a].items())) for a in sorted(crosstab)},
        "per_author_topic_breadth": breadth,
        "authors_with_breadth_le_2": sum(1 for v in breadth.values() if v <= 2),
        "authors_total": len(breadth),
        "probe": True,
        "not_a_judgment": True,
        "usage_note": "作为下一轮「接话」提示词设计的输入（同场不同话题的人才有接话空间）；不进任何判据",
    }

    # ---------------- thread 隔离 ----------------
    thread_isolation = {
        "stat_unit": "thread_id 集合",
        "pub_thread_ids": len(pub_threads),
        "dm_thread_ids": len(dm_threads),
        "intersection_count": len(pub_threads & dm_threads),
        "isolated": len(pub_threads & dm_threads) == 0,
        "probe": True,
        "not_a_judgment": True,
        "note": "交集为 0 ⇒ 公开线程与私聊线程完全隔离，公开面自成一套线程，不流入对话线",
    }

    # ---------------- 消息图入度 / 出度 ----------------
    dm_uid = {pl["msg_uid"] for pl in dm_payloads if isinstance(pl.get("msg_uid"), str)}
    pub_uid = {pl["msg_uid"] for pl in pub_payloads if isinstance(pl.get("msg_uid"), str)}
    dm_reply = [pl.get("reply_to") for pl in dm_payloads if "reply_to" in pl and pl.get("reply_to") is not None]
    dm_hit_dm = sum(1 for v in dm_reply if v in dm_uid)
    dm_hit_pub = sum(1 for v in dm_reply if v in pub_uid)
    # F-2：旧口径用 `real_message_id + other` 近似「reply_to 非空条数」；新增
    # `real_message_id_legacy_msg_id` 后必须并入，否则 msg_id 回退命中的边会凭空消失（出度变小）。
    pub_out_reply = (forms["real_message_id"] + forms["real_message_id_legacy_msg_id"]
                     + forms["other"])
    pub_out_refs = sum(1 for pl in pub_payloads if isinstance(pl.get("refs"), (list, tuple)) and len(pl["refs"]) > 0)
    # R44（口径 `public-talk-deg/2`，**只追加**）：真入度 = **任一**消息事件
    # （DM / PUB / GROUP）的 `reply_to` 命中某条 PUB 的 `msg_uid` 的边数。
    # 旧字段 `pub_in_degree_total` 等价于「只数 DM 边」(`dm_hit_pub`)，在
    # `HITT_DIALOGUE_PUBLIC_REPLY=1` 的批里会**整体漏掉**「公开面被公开面接住」这一类边
    # （d47 实测：旧 0 / 新 4）。旧字段语义不变，降级为 dm-only 兼容口径。
    pub_in_edges: list[tuple[str, str]] = []   # (回复方类型, 被回复的 PUB msg_uid)
    for t, pl in ((t, pl) for _, t, pl in rows_msg):
        v = pl.get("reply_to")
        if isinstance(v, str) and v and v in pub_uid:
            pub_in_edges.append((t, v))
    in_by_channel: dict[str, int] = {}
    for t, _ in pub_in_edges:
        in_by_channel[t] = in_by_channel.get(t, 0) + 1
    pub_in_total_any = len(pub_in_edges)
    pub_replied_uid_count = len({u for _, u in pub_in_edges})
    msg_graph_degree = {
        "stat_unit": "边（reply_to 引用关系）",
        "ruler_version": "public-talk-deg/2",
        "dm_reply_to_nonnull": len(dm_reply),
        "dm_reply_to_hit_dm_msg_uid": dm_hit_dm,
        "dm_reply_to_hit_pub_msg_uid": dm_hit_pub,
        # R44 新增（主口径）：任一消息事件命中 PUB msg_uid 的入度
        "pub_in_degree_total_any": pub_in_total_any,
        "pub_in_degree_by_channel": dict(sorted(in_by_channel.items())),
        "pub_replied_uid_count": pub_replied_uid_count,
        "pub_in_degree_zero_any": pub_in_total_any == 0,
        "isolated_nodes_any": (pub_in_total_any == 0 and pub_out_reply == 0 and pub_out_refs == 0),
        # 兼容字段（语义不变）：只数 DM 边 ⇒ 在「公开面被公开面接住」的批里会低估，
        # 引用时请用 `pub_in_degree_total_any`（见 reports round-1-public-reply.md §R44-C0）
        "pub_in_degree_total": dm_hit_pub,
        "pub_out_degree_reply_nonnull": pub_out_reply,
        "pub_out_degree_refs_nonempty": pub_out_refs,
        "pub_in_degree_zero": dm_hit_pub == 0,
        "pub_out_degree_zero": pub_out_reply == 0 and pub_out_refs == 0,
        "isolated_nodes": (dm_hit_pub == 0 and pub_out_reply == 0 and pub_out_refs == 0),
        "denominator_dm_reply": len(dm_reply),
        "probe": True,
        "not_a_judgment": True,
        "note": msg_graph_degree_note(
            n_dm_reply=len(dm_reply), dm_hit_dm=dm_hit_dm, dm_hit_pub=dm_hit_pub,
            pub_in_total_any=pub_in_total_any, in_by_channel=in_by_channel,
            pub_out_reply=pub_out_reply, pub_out_refs=pub_out_refs),
        "note_consistency": {
            "rule": ("note 的「孤立节点 / 不是孤立节点」判定与 isolated_nodes_any 同口径："
                     "pub_in_degree_total_any==0 且 pub_out_degree_reply_nonnull==0 且 "
                     "pub_out_degree_refs_nonempty==0"),
            "note_says_isolated": (pub_in_total_any == 0 and pub_out_reply == 0
                                   and pub_out_refs == 0),
            "isolated_nodes_any": (pub_in_total_any == 0 and pub_out_reply == 0
                                   and pub_out_refs == 0),
            "consistent": True,  # 同一表达式生成的两处，结构上恒等；字段保留以便外部复算
        },
        "legacy_note": (
            "CYCLE-47 §159 登记过：旧 note 把 `出边 0` 写死，与实测 pub_out_degree_reply_nonnull>0 不一致；"
            "自 public-talk-deg/2 起 note 由实测值拼接（不再写死）"
        ),
    }

    # ---------------- PUB 之后紧邻是什么 ----------------
    # 主口径：MSG_* 子序列上的紧邻下一条；副口径：原始行序的下一行
    seq_types = [t for _, t, _ in rows_msg]
    seq_payloads = [pl for _, _, pl in rows_msg]
    next_msg_hist: dict[str, int] = {}
    within3_dm = 0
    same_author_adj = 0
    for k, (ln, t, pl) in enumerate(rows_msg):
        if t != MSG_PUBLIC:
            continue
        a = pl.get("author")
        if k + 1 < len(rows_msg):
            nxt = seq_types[k + 1]
            next_msg_hist[nxt] = next_msg_hist.get(nxt, 0) + 1
            if seq_payloads[k + 1].get("author") == a:
                same_author_adj += 1
        if "MSG_DM" in set(seq_types[k + 1: k + 4]):
            within3_dm += 1

    type_by_line = dict(next_row_cache)
    raw_next_hist: dict[str, int] = {}
    raw_within3_dm = 0
    for ln in pub_lines:
        nxt = type_by_line.get(ln + 1)
        key = nxt if nxt is not None else "EOF"
        raw_next_hist[key] = raw_next_hist.get(key, 0) + 1
        if any(type_by_line.get(ln + d) == "MSG_DM" for d in (1, 2, 3)):
            raw_within3_dm += 1

    pub_next_to_dm = {
        "stat_unit": "M实例（MSG_PUBLIC 条）",
        "definition_official": "在 MSG_DM/MSG_PUBLIC/MSG_GROUP 子序列上取紧邻下一条（跳过非消息事件）",
        "next_msg_type_histogram": {k: next_msg_hist[k] for k in sorted(next_msg_hist)},
        "numerator_next_is_dm": next_msg_hist.get("MSG_DM", 0),
        "denominator": n,
        "ratio_next_is_dm": frac(next_msg_hist.get("MSG_DM", 0), n),
        "within_next_3_msgs_contains_dm": within3_dm,
        "adjacent_next_msg_same_author": same_author_adj,
        "raw_row_definition": {
            "definition": "原始 jsonl 行序上的下一行事件类型（不跳过任何事件）",
            "next_raw_event_type_histogram": {k: raw_next_hist[k] for k in sorted(raw_next_hist)},
            "numerator_next_raw_is_dm": raw_next_hist.get("MSG_DM", 0),
            "within_next_3_raw_rows_contains_dm": raw_within3_dm,
            "note": "原始行序口径下紧邻的通常是 MEMORY_WRITE/OFFER_ACCEPTED 等事件，与子序列口径差异极大；引用必须写明口径",
        },
        "probe": True,
        "not_a_judgment": True,
    }

    # ---------------- schema 兼容闸 ----------------
    schema_gate = {
        "schema_compatible": schema_compatible,
        "schema_incompatible_reasons": schema_incompat_reasons,
        "required_keys": ["participants", "reply_to", "place"],
        "msg_public_events": n,
        "missing_key_events": {
            "participants": missing["participants"],
            "reply_to": missing["reply_to"],
            "place": missing["place"],
            "any_of_participants_or_reply_to": missing_any,
        },
        "key_presence": {t: key_presence[t] for t in MSG_TYPES},
        "policy": (
            "取键先判 `key in payload`：缺失显式计入 missing_key_events 并置 schema_compatible=false；"
            "绝不静默按 0 处理，也不 KeyError 崩溃；缺键样本不并入任何数值桶。"
            "v0-anchor 批（log sha c1f86bf6…、code_sha dc93c9d9、n16 r84）MSG_DM=132 / MSG_GROUP=7 / "
            "MSG_PUBLIC=48 的 participants、reply_to 键存在数均为 0，正是本闸要拦的形态。"
        ),
        "meta_required": True,
    }

    # ---------------- 跨批不变性自检 ----------------
    cross_batch = [scan_extra_log(Path(p)) for p in args.extra_log]

    def sig(total, hist, fms):
        return (total, tuple(sorted((int(k), v) for k, v in hist.items())), tuple(sorted(fms.items())))

    main_sig = sig(n, len_hist, forms)
    per_batch_identical = {}
    numeric_comparable = {}
    for b in cross_batch:
        identical = sig(
            b["msg_public_total"], b["participants_length_histogram"], b["reply_to_forms"]
        ) == main_sig
        # 与主批可比值：仅 D2 schema 及之后（键齐全且条数一致）才比数值
        b_hist = b["participants_length_histogram"]
        b_forms = b["reply_to_forms"]
        comp = bool(
            b["schema_compatible"]
            and b["msg_public_total"] == n
            and b_hist == {str(k): len_hist[k] for k in sorted(len_hist)}
            and b_forms["json_null"] == forms["json_null"]
            and b_forms.get("missing_key", 0) == 0
        )
        per_batch_identical[b["log_path"]] = identical
        numeric_comparable[b["log_path"]] = comp
    invariance_summary = {
        "main_batch_signature": {
            "msg_public_total": n,
            "participants_length_histogram": {str(k): len_hist[k] for k in sorted(len_hist)},
            "reply_to_forms": forms,
        },
        "per_batch_identical_to_main": per_batch_identical,
        "per_batch_numerically_comparable_to_main": numeric_comparable,
        "all_extra_batches_identical_to_main": (
            all(per_batch_identical.values()) if cross_batch else None
        ),
        "identical_among_schema_compatible_batches": (
            all(
                identical
                for b, identical in zip(cross_batch, per_batch_identical.values())
                if b["schema_compatible"]
            )
            if any(b["schema_compatible"] for b in cross_batch)
            else None
        ),
        "schema_incompatible_batches": [
            b["log_path"] for b in cross_batch if not b["schema_compatible"]
        ],
        "identical_scope_note": (
            "all_extra_batches_identical_to_main 会把 schema 断代批（v0-anchor）算成 false；"
            "判断「不变量成立范围」应看 identical_among_schema_compatible_batches"
        ),
        "numeric_comparison_scope": (
            "只有「schema_compatible=true 且条数一致」的批次可参与数值比较；"
            "v0-anchor 属 schema 断代批（48≠55、键存在数 0），只能比结构存在性"
        ),
    }
    invariance_note = {
        "claim": (
            "在 D2 schema 及之后的各批（d27_C / r10e2e / d28_C_s43 / d12c_on）上，"
            "「MSG_PUBLIC 条数 / participants 长度直方图 / reply_to 形态」三项量是**结构不变量**，"
            "对「生活气息」没有鉴别力：数值完全相同而对话内容完全不同。"
            "它们现在只能证明「公开面未接线（无接话通道、无在场多人）」；"
            "将来接线后才会从 0/55 变成非零。"
        ),
        "hard_constraint": (
            "本不变量不得被用于论证改造无效或改造有效，只能证「公开面未接线」；"
            "任何以「三项量没变」为由否定某次改造的写法都属误用。"
        ),
        "scope": "D2 schema 及之后、n16r60 的 4 批；v0-anchor（schema 断代，48 条且无键）不在数值比较范围内",
        "v0_anchor_note": (
            "v0-anchor 只比结构存在性（participants / reply_to 键存在数 = 0），不比数值 48 vs 55"
        ),
        "no_discrimination_before_wiring": True,
        "becomes_nonzero_after_wiring": True,
        "not_a_quality_metric": True,
    }

    # ---------------- 头信息 ----------------
    inputs = {
        "log_path": str(log_path.resolve()),
        "log_bytes": log_path.stat().st_size,
        "log_lines": lines,
        "log_sha256": log_sha256,
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "code_sha": code_sha,
        "code_sha_source": "meta.json:code_sha（跑批时点代码身份）" if meta else "meta.json 缺失 ⇒ null",
        "repo_head_declared": repo_head_declared,
        "repo_head_declared_valid": repo_head_valid,
        "repo_head_declared_note": (
            "**使用者声明的仓库 HEAD**（`--repo-head` 传入，缺省 null），**不是运行时实测值**、"
            "不参与任何计算；脚本内部不调用 git，故读数与当前 HEAD 无关（D8）。"
            "引用跑批身份请用 code_sha；本字段只用于人工声明对照。"
        ),
        "meta_path": str(Path(args.meta).resolve()) if args.meta else None,
        "meta_sha256": meta_sha256,
        "meta_bytes": meta_bytes,
        "meta_run_sha256": meta_run_sha,
        "meta_run_sha256_matches_log": (meta_run_sha == log_sha256) if meta_run_sha else None,
        "msg_public_type": MSG_PUBLIC,
        "extra_log_count": len(cross_batch),
    }

    invocation_argv = normalize_argv(list(sys.argv))
    readings = {
        "ruler": "public_talk/descriptive-4（描述性尺子；不发明编号，仅本文件内自解释命名）",
        "discipline": {
            "ratio_min_denominator": RATIO_MIN_DEN,
            "probe_threshold_denominator": PROBE_DEN,
            "rules": [
                f"分母 < {RATIO_MIN_DEN}：只报事件数，不报比率",
                f"分母 < {PROBE_DEN}：probe=true，占比只作点估计",
                "单 seed 点估计：不写显著、不给 CI、不跨批比较（跨批只做结构不变性自检）",
                "读数不回改口径；口径与实现同文件共存，改动须同步改头部注释与变更记录",
                "code_sha 一律取 meta.json；scale 一律从 meta 读；读不到写 UNKNOWN",
            ],
        },
        "invocation": {
            "argv": invocation_argv,
            "argv_joined": " ".join(invocation_argv),
            "normalization": (
                "D7：输出路径已归一化为占位符 <OUT>（`--out` 与 `--out=` 两种写法都处理），"
                "使读数 sha256 不依赖输出文件路径；其余参数（--log / --meta / 全部 --extra-log）原样保留，"
                "故 argv_joined 仍是可直接复制的命令，只是把 --out 换成你自己的路径即可。"
            ),
            "out_path_redacted": True,
            "note": "本读数由该命令行产生；复算必须使用同一条命令（尤其 --meta，否则 inputs 会缺 3 个键）",
        },
        "inputs": inputs,
        "scale": scale,
        "schema_gate": schema_gate,
        "msg_public_total": g_total,
        "participants_length_dist": g_participants,
        "reply_to_forms": g_reply_to,
        "place_adjacency": g_place,
        "diagnostics": diag,
        "author_topic_crosstab": author_topic,
        "thread_isolation": thread_isolation,
        "msg_graph_degree": msg_graph_degree,
        "pub_next_to_dm": pub_next_to_dm,
        "cross_batch_invariance": cross_batch,
        "invariance_summary": invariance_summary,
        "invariance_note": invariance_note,
        "judgeability": {
            "scale_desc": (
                f"seed={scale['seed']} agents_n={scale['agents_n']} rounds={scale['rounds']} "
                f"（来源 {scale['source']}）；M实例 n={n}；单批单次、无对照"
            ),
            "can_judge_as_descriptive": True,
            "cannot_judge": [
                "place_adjacency：payload.place 恒 null，本规模下无法判定",
                "任何跨批/跨臂的「变好/变差」比较：三项量本身是结构不变量，且本批单 seed 无对照",
                "任何「显著」「因果」结论：无重复、无 CI",
                "「公开渠道不存在多人对话」的普适结论：只能写「本批未观测到可见集合 >1 的公开消息」，"
                "且 participants 是可见集合而非收件人",
            ],
        },
    }
    if args.timestamp:
        import datetime

        readings["generated_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    text = json.dumps(readings, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"[public_talk] wrote {out_path}")
        print(f"[public_talk] sha256 {hashlib.sha256(text.encode('utf-8')).hexdigest()}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
