#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verdict 分支自测（不跑真日志）：用 monkeypatch 替换 arm_stats，验证
  - (a)(b) 一致 ⇒ 主判定按 (a)、sampling_sensitivity=insensitive
  - (a)(b) 不一致 ⇒ 主判定=不可判、sensitive（不得择优取 a）
  - 守卫 on>off ⇒ 主判定降为不可判
  - N<30 ⇒ 不可判（样本不足）
产物：同目录 verdict_branch_selftest.txt（stdout 重定向）
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
spec = importlib.util.spec_from_file_location("m", os.path.join(os.path.dirname(HERE), "f2b_v2_summary.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fake_stats(landed=60, L6o=0.0, L6n=0.0, L7o=0.1, L7n=0.2, msgs=510):
    st = {"dir": "fake", "F1_chatter": 0.5, "F2_content_drift": 0.6, "F2_tag_switch": {},
          "F2_tag_change_split": {"tag_added": landed, "tag_replaced": 0}, "F2b_multi_topic": {},
          "L13": {"n": 0, "rate": 0.0}, "L5_template_hit": 0.0, "L6_dup_exact": L6o,
          "L7_dup_ngram8": L7o, "msgs": msgs, "D_dispatched": msgs, "through_landed": landed,
          "through_over_D": 0.2, "through_over_msgs": 0.2,
          "tag_appended_events_len2plus": landed, "landed_events": landed, "inherited_tag_msgs": 0}
    st2 = dict(st)
    st2.update({"L6_dup_exact": L6n, "L7_dup_ngram8": L7n})
    return st, st2


def run_case(name, landed, true_pred, guard_broken=False):
    off, on = fake_stats(landed=landed,
                         L6o=0.0, L6n=(0.05 if guard_broken else 0.0),
                         L7o=0.10, L7n=(0.30 if guard_broken else 0.05))
    appends = [{"seq": i, "round": i // 8, "agent": "a", "base": "b", "shift": "s",
                "tags": ["b", "s"], "body": f"body{i}", "thread": f"t{i%16}",
                "turn": 1, "landed": True, "prev_body": None} for i in range(landed)]
    m.arm_stats = lambda d: (off, appends, []) if d == "off" else (on, appends, [])
    d = tempfile.mkdtemp()
    jp, vp = os.path.join(d, "j.json"), os.path.join(d, "v.json")
    items = [{"seq": r["seq"], "judgement": ("true" if true_pred(i) else "false"), "reason": "-"}
             for i, r in enumerate(appends)]
    json.dump({"judger": "selftest", "blind": False, "items": items}, open(jp, "w"), ensure_ascii=False)
    sys.argv = ["x", "--off", "off", "--on", "on", "--judgements", jp, "--verdict", vp]
    m.main()
    v = json.load(open(vp, encoding="utf-8"))
    print(f"[{name}] A={v['precision_main_a']['verdict']}({v['precision_main_a']['n_true']}/30) "
          f"B={v['precision_control_b']['verdict']}({v['precision_control_b']['n_true']}/30) "
          f"-> main={v['main_verdict']} sensitivity={v['sampling_sensitivity']} guards_broken={v['guards_broken']}")
    return v


print("== 用例1：全真 ⇒ (a)(b) 同达标 ⇒ insensitive，主判定=达标")
v = run_case("all_true", 60, lambda i: True)
assert v["main_verdict"] == "达标" and v["sampling_sensitivity"] == "insensitive", v

print("== 用例2：真展开只在偶数 index（信用卡式交替）⇒ (b) step=2 起于 0 全真=30/30 达标；"
      "(a) 起点由 seed 决定，若落在奇数 ⇒ 全假=0/30 未达标 ⇒ sensitive ⇒ 主判定=不可判（不得择优取a）")
v = run_case("parity_offset", 60, lambda i: i % 2 == 0)
assert v["sampling_sensitivity"] == "sensitive" and v["main_verdict"] == "不可判", v
print("   注：30<=N<60 时 (a)(b) 取点恒同（step=1 都取前 30 条）⇒ 该档两方案必然一致，"
      "敏感只可能出现在 N>=60（step>=2，起点偏移）——这一性质写进判定备忘")

print("== 用例3：全假 ⇒ (a)(b) 同未达标 ⇒ insensitive，主判定=未达标")
v = run_case("all_false", 60, lambda i: False)
assert v["main_verdict"] == "未达标" and v["sampling_sensitivity"] == "insensitive", v

print("== 用例4：全真但 L-6/L-7 在 on 臂恶化（守卫 broken） ⇒ 主判定降为不可判")
v = run_case("guard_broken", 60, lambda i: True, guard_broken=True)
assert v["main_verdict"] == "不可判" and v["guards_broken"], v

print("== 用例5：landed=20 < 30 ⇒ 不可判（样本不足）")
v = run_case("insufficient", 20, lambda i: True)
assert v["main_verdict"].startswith("不可判"), v

print("\nALL VERDICT BRANCHES OK（本轮 5 例全部符合预登记/RULES 定义）")
