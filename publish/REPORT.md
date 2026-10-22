# 报告族指针（R1–R5 + R3b）

> 本文件只做导航，不复制正文。正文与证据索引在 `../reports/`；每份报告自带「证据索引表」（结论 ↔ 文件 ↔ sha ↔ 复算命令）。

| 编号 | 报告 | 一句话 | 适合谁 |
|---|---|---|---|
| **R1** | [`R1-method-and-reproducibility.md`](../reports/R1-method-and-reproducibility.md) | 这套实验凭什么可信、哪些话不能信到哪一步（可信边界 8 条、真跑判据四层、B2 单阈值纪律、受控解冻） | 想复核方法的人 |
| **R2** | [`R2-dialogue-structure.md`](../reports/R2-dialogue-structure.md) | 对话的「形状」：线程分布、交替轮次、指针完整率；含 `max_turns` 2/4/6 三档对照 | 看结构改造的人 |
| **R3** | [`R3-dialogue-quality.md`](../reports/R3-dialogue-quality.md) | 台词本身：旁白/套路/长度/具体性/承接，附同窗口判定表与「不得称措辞改善」的理由 | 判断"说得像不像人"的人 |
| **R3b** | [`R3b-D6-同窗口评测.md`](../reports/R3b-D6-同窗口评测.md) | D6 v1.0 的发布副本：同窗口 34 回合的完整读数与 judge 交叉检查 | 要最细读数的人 |
| **R4** | [`R4-life-texture.md`](../reports/R4-life-texture.md) | 生活气息：闲聊/漂移/情绪呼应/修复闭环/习惯/跨天记忆，附"为何多数只能报事件数" | 关心"有没有过日子感"的人 |
| **R5** | [`R5-datasets-and-demo.md`](../reports/R5-datasets-and-demo.md) | 数据集索引、字段字典、页面入口、16 张真实截图（三件套：run 目录 + 渲染命令 + 日志 sha） | 想拿数据/看页面的人 |

## 演示入口（亲眼看对话）

```bash
cd code && python frontend/tools/serve.py          # 静态服务，端口 8848
# 浏览器：http://127.0.0.1:8848/dialogue.html?data=<threads.json 相对路径>&sort=turns
```

三个入口（同一页面、同视图、只换 `data`）：

| 阶段 | `data` | 日志 sha256 |
|---|---|---|
| 改造前 v0-anchor | `sample/dialogue_v0anchor_n16_seed42/threads.json` | `c1f86bf61f62b3a0ce8e17e0c2312791cf0262381cd2120c2a63c9b6258963cf` |
| 改造后 A0 | `sample/dialogue_run_d2_after_n16_seed42/threads.json` | `643f13a528c288d3e9677cb8ac100139224afbd0b46c0f7da0c3a5ed85b13141` |
| 措辞臂 A1（**probe**） | `sample/dialogue_a1_wording_n4r60_seed42/threads.json` | `ae969198feaefd1f69147001e027394d55527bd1a0e460ff654697bdc3b1559b` |

> ⚠️ 页面上的 `D9-reply-window-2to4` 是**回复窗口臂**（阴性结果），**不是**措辞臂；两者不可并列比较。

## 阅读顺序建议

1. 只想判断能不能信 → **R1** §3 可信边界（8 条）
2. 想看结论 → **R2** §5（结构）+ **R3** §4.1c-2（措辞同窗口表）
3. 想复核 → 各报告 §证据索引 + 本发布包 `RELEASE-NOTES.md` §复现三步
