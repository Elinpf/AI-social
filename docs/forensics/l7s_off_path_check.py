"""R17 · L-7 结构臂「OFF 路径」离线自证（零跑批、零 LLM）。

用途：结构臂默认 ON 是本分支的处理臂，因此「不设 env」不能证明 OFF 路径可用。
本脚本显式对比 env=1 与 env=0 两态，输出可复算证据（供报告「可回滚」实证）。

可复算命令：
    cd social-experiment
    python3 docs/forensics/l7s_off_path_check.py

判据（全部为 True 才算 OFF 路径可用）：
  1. env=0 ⇒ `enabled()` False、`plan()` None、`render()` ""、模块无进程级状态（replay 安全）；
  2. env=0 ⇒ 两个提示词里没有结构段（`这一句换个说法：`）；
  3. env=0 ⇒ `ctx.l7struct` 不出现（payload 零扰动）；
  4. env=0 ⇒ `_dequp_body()` 退回原 DEQUP 路径（本臂 OFF 时 DEQUP 也 OFF ⇒ 原样返回）；
  5. env=1 ⇒ 上述四项反转（结构段存在、审计键存在）；
  6. 两态差异**只有一处插入**：`on.replace(seg, "", 1) == off`。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

CODE = Path(__file__).resolve().parents[2] / "code"
sys.path.insert(0, str(CODE))

from life import l7_structural as L7S          # noqa: E402
from life.agent import LifeLayerAgent          # noqa: E402
from life.memory import HashEmbeddingModel, SideStore  # noqa: E402
from life.persona import load_personas         # noqa: E402

SELF_ID, PARTNER_ID = "P003", "P002"


class _Kernel:
    def submit_intent(self, *a, **kw):
        pass


def _agent(tmp: Path) -> LifeLayerAgent:
    personas = load_personas(CODE / "config" / "personas.json")
    places = {p["place_id"]: p for p in
              json.loads((CODE / "config" / "places.json").read_text(encoding="utf-8"))["places"]}
    return LifeLayerAgent(SELF_ID, personas[SELF_ID], _Kernel(),
                          side_store=SideStore(tmp / "side"),
                          embedding=HashEmbeddingModel(), places=places,
                          peers=sorted(personas),
                          peer_names={k: v.display_name for k, v in personas.items()})


def _wv():
    """世界视图替身：带两条可见台词，使「禁忌开头」路径也被覆盖。"""
    ev = [SimpleNamespace(type="MSG_DM", payload={"body": "秀娘，你家的鸡又跑了。"}),
          SimpleNamespace(type="MSG_DM", payload={"body": "唉，这天气真闷。"})]
    return SimpleNamespace(day=3, round=17,
                           time=SimpleNamespace(day_of_week=2, slot="morning"),
                           visible_events=ev)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="l7s-off-"))
    wv = _wv()
    history = [("名2", "早上好。")]
    out: dict = {}

    # ---- env=0（显式关闭）------------------------------------------------
    os.environ[L7S.STRUCT_ENV] = "0"
    L7S.reset()
    agent = _agent(tmp)
    off_enabled = L7S.enabled()
    off_plan = L7S.plan(SELF_ID, [PARTNER_ID], 3, "2-morning", 17, 0, "initiate")
    off_render = L7S.render(off_plan)
    d_off = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID], wv=wv)
    r_off = agent._reply_prompt(PARTNER_ID, "tpl-1", history, wv=wv)
    ctx_off = agent._ctx_snapshot(PARTNER_ID, "tpl-1")
    body = "今天这锅汤我少放了半勺盐，多搁了一小把干贝"
    off_body = agent._dequp_body("BASE", body, {})

    # ---- env=1（显式开启，等价于默认态）---------------------------------
    os.environ[L7S.STRUCT_ENV] = "1"
    L7S.reset()
    agent2 = _agent(tmp)
    on_enabled = L7S.enabled()
    d_on = agent2._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID], wv=wv)
    seg_d = L7S.render(agent2._l7s)
    r_on = agent2._reply_prompt(PARTNER_ID, "tpl-1", history, wv=wv)
    seg_r = L7S.render(agent2._l7s)
    ctx_on = agent2._ctx_snapshot(PARTNER_ID, "tpl-1")

    out["env"] = L7S.STRUCT_ENV
    out["checks"] = {
        "1_off_enabled_false": off_enabled is False,
        "1_off_plan_none": off_plan is None,
        "1_off_render_empty": off_render == "",
        "1_off_no_process_state": ("recent" not in L7S._STATE) and ("stats" not in L7S._STATE),
        "2_off_prompt_has_no_struct_seg":
            ("这一句换个说法：" not in d_off) and ("这一句换个说法：" not in r_off),
        "3_off_ctx_has_no_l7struct": "l7struct" not in ctx_off,
        "4_off_dequp_body_passthrough": off_body == body,
        "5_on_enabled_true": on_enabled is True,
        "5_on_prompt_has_struct_seg":
            ("这一句换个说法：" in d_on) and ("这一句换个说法：" in r_on),
        "5_on_ctx_has_l7struct": ctx_on.get("l7struct", {}).get("v") == "l7-struct/1",
        "6_on_is_off_plus_one_insert":
            d_on.replace(seg_d, "", 1) == d_off and r_on.replace(seg_r, "", 1) == r_off,
    }
    out["diff_chars"] = {"dialogue": len(d_on) - len(d_off),
                         "reply": len(r_on) - len(r_off)}
    out["on_segment_dialogue"] = seg_d
    out["all_pass"] = all(out["checks"].values())
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
