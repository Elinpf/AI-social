#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""世界设定书一致性检查（worldbook v1 ↔ code/config/*）。

校验 `v2/refs/worldbook-v1.json` 与现有 config 是否**不矛盾、可机检**：
  1) 场所：worldbook.geography.places == config/places.json 的 place_id 集合
  2) 居民：worldbook.residents.roster 的 persona_id 集合 == config/personas.json
  3) 宏观机制：worldbook.macro_events.mechanisms.config_key == config/world_director.json 的 mechanisms 键，
     且每条 enabled 与 config 一致
  4) 机制表(WM)对齐：报告机制表独有 / 配置独有（不矛盾，仅"待对齐"提示）
  5) 社会层红线：worldbook 不得预设 price/wage/tax_rate/mint_rule 数值

用法：python v2/refs/tools/check_worldbook.py [--root <social-experiment>] [--json]
退出码：0=全部硬检查通过；1=有硬不一致（硬检查项 1/2/3/5）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    default_root = Path(__file__).resolve().parents[3]  # social-experiment/
    ap.add_argument("--root", default=str(default_root))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    wb = _load(root / "v2/refs/worldbook-v1.json")
    places = _load(root / "code/config/places.json")
    personas = _load(root / "code/config/personas.json")
    wd = _load(root / "code/config/world_director.json")

    hard: list[str] = []
    info: list[str] = []

    # 1) 场所
    wb_places = set(wb["geography"]["places"])
    cfg_places = {p["place_id"] for p in places["places"]}
    if wb_places != cfg_places:
        hard.append(f"[places] 不一致：worldbook-only={sorted(wb_places-cfg_places)} config-only={sorted(cfg_places-wb_places)}")
    else:
        info.append(f"[places] OK ({len(wb_places)} 场所一致)")

    # 2) 居民
    wb_ids = {r["persona_id"] for r in wb["residents"]["roster"]}
    cfg_ids = {p["persona_id"] for p in personas["personas"]}
    if wb_ids != cfg_ids:
        hard.append(f"[residents] 不一致：worldbook-only={sorted(wb_ids-cfg_ids)} config-only={sorted(cfg_ids-wb_ids)}")
    else:
        info.append(f"[residents] OK ({len(wb_ids)} 居民一致)")

    # 3) 宏观机制键 + enabled
    wb_mech = {m["config_key"]: m for m in wb["macro_events"]["mechanisms"]}
    cfg_mech = wd["mechanisms"]
    if set(wb_mech) != set(cfg_mech):
        hard.append(f"[mechanisms] 键不一致：worldbook-only={sorted(set(wb_mech)-set(cfg_mech))} config-only={sorted(set(cfg_mech)-set(wb_mech))}")
    else:
        info.append(f"[mechanisms] OK ({len(wb_mech)} 机制键一致)")
    for k, m in wb_mech.items():
        if k in cfg_mech and bool(m.get("enabled")) != bool(cfg_mech[k].get("enabled")):
            hard.append(f"[mechanisms] {k} enabled 不一致：worldbook={m.get('enabled')} config={cfg_mech[k].get('enabled')}")

    # 4) WM 表对齐（提示）
    wm_only = wb["macro_events"].get("wm_only_not_in_config", [])
    no_wm = [k for k, m in wb_mech.items() if not m.get("wm_id")]
    info.append(f"[WM 对齐] 机制表独有(未在 config): {wm_only}")
    info.append(f"[WM 对齐] config 独有(未并入 WM 表): {no_wm}  ← 待对齐，非矛盾")

    # 5) 社会层红线：不得预设数值
    forb = wb.get("social_layer_policy", {}).get("forbidden_presets", [])
    wb_str = json.dumps(wb, ensure_ascii=False)
    leaked = [f for f in forb if f in wb and isinstance(wb.get(f), (int, float))]
    if wb.get("social_layer_policy", {}).get("preset_values") is not False:
        hard.append("[social_layer] preset_values 必须为 false（红线：不预设社会层数值）")
    else:
        info.append(f"[social_layer] OK：不预设数值；红线清单={forb}")
    if leaked:
        hard.append(f"[social_layer] 发现疑似预设数值：{leaked}")

    ok = not hard
    if args.json:
        print(json.dumps({"ok": ok, "hard_issues": hard, "info": info}, ensure_ascii=False, indent=2))
    else:
        print("=" * 72)
        print("世界设定书一致性检查（worldbook-v1 ↔ code/config/*）")
        print("=" * 72)
        for line in info:
            print("  OK  " + line)
        for line in hard:
            print("  FAIL " + line)
        print("-" * 72)
        print(f"结果：{'PASS（全部硬检查通过）' if ok else 'FAIL（存在硬不一致，见上）'}")
        print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
