# D10 C-A 汇总表（address_drift × 官方 F-1/L-7/L-12b）

- computed_at: 2026-10-30T18:06:49+0800
- lexicon_sha256: `dc4ce327ff8e0a77d34545903e8589ea97429a30c9b26bf0ed9d972eda122d95`
- summary_tool_sha256: `46f431f1eb54120e06ea6099184037f99605e4e85fa4bc68e94b8ffe4669abb4`

| key | arm | n_msg | cov% | mention% | vocabN | vocabMean | sw_n | sw/den_scored | sw%scored | sw%all | stageN | up | flat | down | err_n/den | err% | F1% | L7% | L12b% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| d9m-off | OFF | 191 | 31.9372 | 81.1518 | 19 | 1.5789473684210527 | 0 | 0/11 | 0.0 | 0.0 | 16 | 0 | 15 | 1 | 0+2/59 | 3.3898 | 77.4869 | 21.466 | 28.1437 |
| d9m-on | ON | 191 | 36.6492 | 85.3403 | 19 | 1.6842105263157894 | 3 | 3/17 | 17.6471 | 3.2258 | 18 | 1 | 16 | 1 | 0+0/67 | 0.0 | 74.8691 | 29.8429 | 34.1317 |
| d9s-off | OFF | 191 | 36.6492 | 86.3874 | 19 | 1.5263157894736843 | 0 | 0/15 | 0.0 | 0.0 | 20 | 0 | 20 | 0 | 2+0/68 | 2.9412 | 73.2984 | 30.3665 | 34.1317 |
| d9s-on | ON | 191 | 37.1728 | 86.3874 | 19 | 1.7894736842105263 | 4 | 4/19 | 21.0526 | 4.3011 | 18 | 0 | 17 | 1 | 5+1/70 | 8.5714 | 73.822 | 74.8691 | 35.9281 |
| round1 | ROUND1_NARR_ON | 191 | 39.267 | 91.0995 | 19 | 1.6842105263157894 | 0 | 0/22 | 0.0 | 0.0 | 20 | 1 | 18 | 1 | 1+0/74 | 1.3514 | 75.9162 | 20.9424 | 35.9281 |

## d9m-off (arm=OFF)
- log: `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl`
- log_sha256: `5f1dda97633ccf0b3f7d2b279c39a43752db7d945a2ca6f9133e0b2bc9106ed5`
- official_cmd: `/opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/tools/d5/dialogue_metrics.py --log /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl --out-json /tmp/tmpxqtgdqyq/dm.json`

## d9m-on (arm=ON)
- log: `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl`
- log_sha256: `2edc751c5a32d1328ed5834ab169d29c5c457cbe7b1d5abe3146d7840df6a795`
- official_cmd: `/opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/tools/d5/dialogue_metrics.py --log /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl --out-json /tmp/tmptb7_u6cx/dm.json`

## d9s-off (arm=OFF)
- log: `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d9s-off_n16r24_s42/run.jsonl`
- log_sha256: `bd6623c209641bbeff1f72df6e0e843d756ef395eb7898571acf3dae0ad4be4c`
- official_cmd: `/opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/tools/d5/dialogue_metrics.py --log /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d9s-off_n16r24_s42/run.jsonl --out-json /tmp/tmp29_4vyvh/dm.json`

## d9s-on (arm=ON)
- log: `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d9s-on_n16r24_s42/run.jsonl`
- log_sha256: `0a50484d0fce2933fbc87bd20bedae93d8f3d1d233310d2a8c005d1e0bdef4d9`
- official_cmd: `/opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/tools/d5/dialogue_metrics.py --log /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d9s-on_n16r24_s42/run.jsonl --out-json /tmp/tmppe4zvz9_/dm.json`

## round1 (arm=ROUND1_NARR_ON)
- log: `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/round1_narration_default_n16r24_s42/run.jsonl`
- log_sha256: `ca108da9f90031f7d8b9dbc346518898e48976c33ec0965737ca80255cb6e37b`
- official_cmd: `/opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/tools/d5/dialogue_metrics.py --log /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/round1_narration_default_n16r24_s42/run.jsonl --out-json /tmp/tmptzcioirh/dm.json`

## 与基线/另一臂的对比（仅描述，不可归因）

| baseline | treatment | switch(base) | switch(treat) | Δpp | Fisher 双侧 p | 说明 |
|---|---|---|---|---|---|---|
| d9m-off | d9m-on | 0/11 | 3/17 | 17.6471 | 0.257937 | 两臂差异**不是**称呼干预（各自只差旁白轮换 / 句式起首臂）⇒ 只作描述，不可归因 |
| d9m-off | d9s-on | 0/11 | 4/19 | 21.0526 | 0.267871 | 两臂差异**不是**称呼干预（各自只差旁白轮换 / 句式起首臂）⇒ 只作描述，不可归因 |
| d9m-off | round1 | 0/11 | 0/22 | 0.0 | 1.0 | 两臂差异**不是**称呼干预（各自只差旁白轮换 / 句式起首臂）⇒ 只作描述，不可归因 |
| d9m-on | d9s-off | 3/17 | 0/15 | -17.6471 | 0.228831 | 两臂差异**不是**称呼干预（各自只差旁白轮换 / 句式起首臂）⇒ 只作描述，不可归因 |
| d9m-on | round1 | 3/17 | 0/22 | -17.6471 | 0.074406 | 两臂差异**不是**称呼干预（各自只差旁白轮换 / 句式起首臂）⇒ 只作描述，不可归因 |
| d9s-off | d9s-on | 0/15 | 4/19 | 21.0526 | 0.113011 | 两臂差异**不是**称呼干预（各自只差旁白轮换 / 句式起首臂）⇒ 只作描述，不可归因 |
| d9s-off | round1 | 0/15 | 0/22 | 0.0 | 1.0 | 两臂差异**不是**称呼干预（各自只差旁白轮换 / 句式起首臂）⇒ 只作描述，不可归因 |
| d9s-on | round1 | 4/19 | 0/22 | -21.0526 | 0.038274 | 两臂差异**不是**称呼干预（各自只差旁白轮换 / 句式起首臂）⇒ 只作描述，不可归因 |
