# env 开关优先级 · 跑批方独立复核（不看作者的结论，自己重跑）

- 复核时刻: 2026-10-20T20:18:32+08:00
- HEAD: fcf42bf931fb239867886674f68db822d1a162e2
- 复核人: batch-evidence-runner（跑批方，非机制作者）

## 复核对象（作者侧证据文件 sha256，与作者自报一致）
1324aac56f954fe48154a1748f84a5ac48417cac1c5bc40d819bbba0f362aa2c  v2/evidence/f4_env_priority_probe.py
bd1a57e170998fe02f827ac0025abafa10d46804bc5187e47aa3908e6bd94373  v2/evidence/f4_env_priority_probe_off.json
2b4109746d35ec957b0e45e357988567a6a391cfa40d2f70a633d1eb77a31eda  v2/evidence/f4_env_priority_probe_on.json

## 我自己重跑的两条命令与关键字段
```
$ python3 v2/evidence/f4_env_priority_probe.py off
{"arm": "off", "env_HITT_DIALOGUE_REPAIR": null, "effective_params": {"context_max_age_rounds": 24, "enabled": false, "gripe_context": true, "max_age_rounds": 84, "max_open": 3, "reply_priority": true, "window_msgs": 8}, "n_msgs": 106, "n_dialogue_rift_key": 0, "n_dialogue_rift_null": 0, "n_body_not_in_stub_set": 0, "body_contains_ablation_phrase": false}

$ HITT_DIALOGUE_REPAIR=1 python3 v2/evidence/f4_env_priority_probe.py on
{"arm": "on", "env_HITT_DIALOGUE_REPAIR": "1", "effective_params": {"context_max_age_rounds": 24, "enabled": true, "gripe_context": true, "max_age_rounds": 84, "max_open": 3, "reply_priority": true, "window_msgs": 8}, "n_msgs": 118, "n_dialogue_rift_key": 38, "n_dialogue_rift_null": 0, "n_body_not_in_stub_set": 0, "body_contains_ablation_phrase": false}
```

## 复核结论（跑批方口径）
- 未设 env ⇒ effective_params.enabled=false、dialogue_rift 键出现 0 次（且 null 计数也为 0 ⇒ 不是空键，是键不存在）⇒ 关闭态惰性成立。
- 设 env=1 且 config 仍为 false ⇒ effective_params.enabled=true、dialogue_rift 出现 ⇒ env 优先级成立。
- 两臂 body 均逐字来自 stub（n_body_not_in_stub_set=0）⇒ 机制未向 body 拼接文本，两臂可比性不受污染。
- 我独立重跑得到的字段值与作者自报一致（n_msgs 106 / on 臂 rift 键 >0），故接受该证据作为 Arm-T 可信开跑前提之一。
> 注意：本复核只证明**开关语义**；不证明机制有效，也不替代跑批在真 LLM 下的验真。
