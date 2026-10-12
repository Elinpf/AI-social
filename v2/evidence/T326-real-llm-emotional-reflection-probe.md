# T326 真 LLM 小样本探针：反思节点是否含「情感词」

> 作者：release-engineer ｜ 2026-10-13 ｜ sha **`352e9a4`** ｜ provider **`openai_compat`（154 LLM_CALL，无 mock）**
> 一页证据：口径可复核 + 真/mock 对照 + 原文样本 + 结论。

## 1. 「情感词」判定依据（可复核，**必须**）
`code/life/agent.py:861-864`（`_DRIFT_POS`/`_DRIFT_NEG`，**硬编码 13+13=26 个子串**）：
- POS：`帮助 成长 喜悦 连接 感谢 陪伴 温暖 成功 support growth joy connect thanks`
- NEG：`冲突 失败 孤独 失去 争吵 痛苦 挫折 焦虑 conflict loss lonely fail struggle`
- 判定：`(text).lower()` **含任一子串** ⇒ 「含情感词」。
- 对象：`MEMORY_WRITE` 事件中 **`kind=="reflection"`** 的节点；正文经 `body_ref` → `side/src/<digest>.txt`（T268 内容寻址）。

## 2. 命令（可复算）
```bash
# 真 LLM（内网端点，无 mock）：托管逃逸 + MemoryMax
R=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
bash tools/t271/make_batch_copy.sh t326real "$(git -C "$R" rev-parse HEAD)"
bash tools/t271/host_batch.sh --name t326real --out /root/t271/runs/t326_real/run.jsonl \
  --workdir /tmp/t271-t326real/code --env-file "$R/code/.env.local" --mem-high 4G --mem-max 6G \
  -- /opt/openjiuwen/workswarm-venv/bin/python -m orchestration run --life --seed 42 --agents 3 \
     --rounds 84 --out /root/t271/runs/t326_real/run.jsonl --side-root /root/t271/runs/t326_real/side --flush-every 21
# mock 对照：env -u HITT_LLM_PROVIDER 同参
# 分析：
python3 tools/t271/emotion_probe.py /root/t271/runs/t326_real
python3 tools/t271/emotion_probe.py /root/t271/runs/t326_mock
```

## 3. 结果
| run | provider | reflection 节点 | **命中 26 词表** | `importance≥7` 子集命中 |
|---|---|---:|---:|---:|
| **真 LLM** `352e9a4` | `openai_compat`(154) | 63 | **0/63 = 0.0%** | 0/42 |
| mock | `mock`(153) | 63 | 0/63 = 0.0% | 0/42 |

## 4. 原文样本（真 LLM，**供人眼判『有没有情绪』**，原样）
- P001：`（蹲在田埂上，捏了把土搓了搓）嗯。`
- P003：`（直起腰，用袖子擦了擦汗，朝P001离开的方向望了一眼）……走了啊。也是，各家有各家的活。`
- P002：`（低头挑着木料，没抬眼）嗯。`
- P001：`（蹲在田埂上，捏着烟没点）市场那边又闹腾了。关系变来变去，跟我没关系。地还在，种子还在，就行。`
- （mock 对照）`mock::9f86784e01f0db08（insight 1）` —— 纯占位符。

## 5. 结论：**主 (b)「文本有情绪但没命中词表」＋ mock 属 (c)**
- **真 LLM 下 26 词表命中仍 = 0**，但**原文并非"平"** —— 含**隐性情绪/叙事口吻**（怅然"……走了啊。也是，各家有各家的活"；疏离"跟我没关系…就行"）⇒ **落在 (b)：有情绪、但用的是隐含表达、没命中 26 个显式子串 ⇒ 词表太窄/太死**。
- **mock 属 (c)**：正文是 `mock::<hash>（insight N）` 占位符，**零情绪**（T323 的"含情感词=0"很大程度源于此）。
- **含义（对 T325 方向）**：**`PERSONA_DRIFT` 在真跑里候选恒空的根因 = 26 词表门控太窄**（真文本用隐性情感）⇒ **T325 应改为"词表扩 / 可配置"**，而非只"改 mock 文本"。
- **诚实边界**：**"有没有情绪"是主观判断**；本文**给原样样本供人眼**，结论是**校准读数、非断言**。

## 6. 与 T323 的关系
T323「465 反思含情感词=0」为 **mock** 结果；本探针证实：**真 LLM 下 26 词表命中亦=0**，**但真文本有情绪** ⇒ **不是"世界太干"，而是"情感词表口径太窄"**（世界质量结论须改写）。
