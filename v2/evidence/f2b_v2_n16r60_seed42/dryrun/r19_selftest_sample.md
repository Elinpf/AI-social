# F-2b 话题展开 · B.4-v2 precision 判定抽样（n16r60 / seed=42，双取样并集）

> 臂：`on（LIFE_PROMPT_TOPIC_BREADTH=1）`；判定对象：`ctx.topic_breadth.landed = true` 的消息。
> (a) N=10 < 30 ⇒ **样本不足**（不得用更小分母凑判定）
> (b) N=10 < 30 ⇒ 不产出对照样本
> 下列为 **(a)∪(b) 并集**：标题里的 `[A]`/`[B]`/`[AB]` 标明该条属于哪个样本（A=主判、B=对照、AB=两者）。
> 判定标准（预登记 §2）：① 接着同线程上一句在说事；② 原话题之外**自然**带出第二个话题线索
> （shift 话题以动作/对象出现在语义主位，不是修饰语、不与动作矛盾）。
> 真展开=true / 假展开=false / 存疑=undecidable（存疑计入分母、不计入真）。
> 判定者：life-spearman（**未参与** code/life/topic_breadth.py 与 agent.py 的话题展开实现），**非盲**（判定时已见臂名与 D/T/landed 读数）。

