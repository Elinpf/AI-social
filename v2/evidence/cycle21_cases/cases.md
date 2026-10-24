# CYCLE-21 §4 可展示案例：逐字对话素材（带 seq 与溯源）

> **生成者**：`case-curator`｜**生成方式**：`v2/evidence/cycle21_cases/extract_cases.py` 只读两臂 `run.jsonl`（**零跑批、零 LLM 调用**），本文件可由该脚本原样重生成。
> **用途**：供《CYCLE-21 周期实验报告》第四节「可展示案例」引用。
> **纪律**：正文逐字原文，不删改、不截断、不跨线程拼接；每线程单独成段；每条消息带 `seq`（run.jsonl 顶层字段）；每段注明来源文件 + sha256 前 8 位 + thread_id + 参与人 + day/slot/place。
> **本文件不计算任何指标、不下任何臂级结论**（旁白率等读数归 `metric-recomputer`；本文件只提供可被复核引用的原文素材）。

## 0. 段清单

| 段 | 臂 | batch | thread_id | 条数 | 用途 |
|---|---|---|---|---|---|
| 1 | C 基线 | `CYCLE-21C` | `TH-P004-P002-0` | 6 | C 臂无旁白形态（主样本） |
| 2 | C 基线 | `CYCLE-21C` | `TH-P010-P009-0` | 6 | C 臂无旁白形态（副样本） |
| 3 | B 实验 | `CYCLE-21B` | `TH-P004-P002-0` | 6 | B 臂旁白形态（与段 1 同 thread_id） |
| 4 | B 实验 | `CYCLE-21B` | `TH-P010-P009-0` | 6 | B 臂旁白形态（与段 2 同 thread_id） |

> 段 1↔段 3、段 2↔段 4 是**同 thread_id、跨两个独立 run** 的对照，**不是同一局模拟的同一轨迹**（`code_sha` 不同，见各臂元信息）。引用时只能用于说明「两臂消息形态的差异」，不得当作配对样本或同轨迹前后对照。

---

## 1. 逐字段素材

### CYCLE-21C / C 基线臂
| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/run_d27_C_n16r60_seed42/run.jsonl` |
| 日志 sha256（全长） | `1fbb9ef5161fd07aa68fcc9fc4038f104ff18b56383a2fc6b31bb3cb5486a188`（sha8 = `1fbb9ef5`）|
| 日志规模 | 116308 events / 56,531,099 B |
| 跑批身份（`meta.json`） | `code_sha = code_sha_end = f2bf606bf5f6c362a7d4d34b9177f3210d43aabf`；`seed 42`；`rounds 60`；`n 16`；`provider openai_compat`；`model DeepSeek-Flash`；`llm_calls 2878`；`degraded_calls 0`；`finished_at 2026-10-24T14:59:23+08:00` |
| 本臂线程总数（MSG_DM+MSG_PUBLIC 重建） | 169 |

> ⚠ 本批日志位于 `v2/evidence/` 下，受 `.gitignore`（`**/*.jsonl`）排除 ⇒ **不在 git 对象里**：可原地复算 sha、可重渲染，但不可从零重建。

#### 段 1｜`TH-P004-P002-0`（CYCLE-21C，6 条，DM）

| 项 | 值 |
|---|---|
| segment_id | `CYCLE-21C-TH-P004-P002-0` |
| 来源文件 | `v2/evidence/run_d27_C_n16r60_seed42/run.jsonl` |
| 来源 sha256 前 8 位 | `1fbb9ef5` |
| thread_id | `TH-P004-P002-0` |
| 参与人 | `P002`, `P004` |
| seq 序列 | `73`, `549`, `2090`, `2914`, `4920`, `5556` |
| day / slot | day [0]；slot morning → afternoon → evening |
| 地点（逐条可变的 payload.place） | library → market → community_center |
| 段内以全角括号开头的消息数（描述性计数，非臂级结论） | 0/6 |

逐字原文（左侧 `#seq` 为 run.jsonl 顶层 `seq` 字段；`day/slot/place` 逐条取 `payload` 原值）：

- **#73** `P004` → `P002`｜day 0 · morning · place `library`｜topic `mentorship`｜turn_index 0｜type `MSG_DM`
  > 这炉桃酥我总烤不出你家的脆劲儿，你最近忙得过来不？教教我。
- **#549** `P002` → `P004`｜day 0 · morning · place `library`｜topic `mentorship`｜turn_index 1｜type `MSG_DM`
  > 哎，我正刨着刘家那根榆木梁，手头活儿紧，你明儿带块面来我这儿，我边做边教你，行不？
- **#2090** `P004` → `P002`｜day 0 · afternoon · place `market`｜topic `mentorship`｜turn_index 2｜type `MSG_DM`
  > 你那根榆木梁刨到哪一步了，我明儿带块发好的面过去，你腾得出手教我和面不？
- **#2914** `P002` → `P004`｜day 0 · afternoon · place `market`｜topic `mentorship`｜turn_index 3｜type `MSG_DM`
  > 哎，刨到卯口了，你带面来我教你揉，顺手把窗台上那把旧刨刀递我。
- **#4920** `P004` → `P002`｜day 0 · evening · place `community_center`｜topic `mentorship`｜turn_index 4｜type `MSG_DM`
  > 老石，你这话说得我心里痒，我正给王家小孙子捏那屉小兔子馒头呢，面还软着。刨刀给你，我这就去拿面。
- **#5556** `P002` → `P004`｜day 0 · evening · place `community_center`｜topic `mentorship`｜turn_index 5｜type `MSG_DM`
  > 面软着就先别急着捏，王家小孙子那屉兔子馒头等得起。我这刨刀刚啃上榆木，纹路正顺，换手反倒要起毛。你揉面时手腕使几分劲，是凭手感还是看面醒到啥程度？

#### 段 2｜`TH-P010-P009-0`（CYCLE-21C，6 条，DM）

| 项 | 值 |
|---|---|
| segment_id | `CYCLE-21C-TH-P010-P009-0` |
| 来源文件 | `v2/evidence/run_d27_C_n16r60_seed42/run.jsonl` |
| 来源 sha256 前 8 位 | `1fbb9ef5` |
| thread_id | `TH-P010-P009-0` |
| 参与人 | `P009`, `P010` |
| seq 序列 | `135`, `954`, `2162`, `3760`, `5018`, `6266` |
| day / slot | day [0]；slot morning → afternoon → evening |
| 地点（逐条可变的 payload.place） | park → farm → market → cafe |
| 段内以全角括号开头的消息数（描述性计数，非臂级结论） | 0/6 |

逐字原文（左侧 `#seq` 为 run.jsonl 顶层 `seq` 字段；`day/slot/place` 逐条取 `payload` 原值）：

- **#135** `P010` → `P009`｜day 0 · morning · place `park`｜topic `combat_training`｜turn_index 0｜type `MSG_DM`
  > 金先生，我把这段副歌的鼓点改到第三小节了，你听听看。就这儿。
- **#954** `P009` → `P010`｜day 0 · morning · place `park`｜topic `combat_training`｜turn_index 1｜type `MSG_DM`
  > 鼓点挪到第三小节，我算了下，跟前面两拍正好凑成四四拍，账要平。你敲一遍。
- **#2162** `P010` → `P009`｜day 0 · afternoon · place `farm`｜topic `combat_training`｜turn_index 2｜type `MSG_DM`
  > 哎，我手里这杯凉透的咖啡还没喝完呢，先把鼓槌搁下——你说的第三小节我试了，跟前面两拍确实能凑上，可敲出来像赶集似的，你听听是不是我手腕太僵了？
- **#3760** `P009` → `P010`｜day 0 · afternoon · place `market`｜topic `combat_training`｜turn_index 3｜type `MSG_DM`
  > 你那鼓槌还搁在账本边上呢，第三小节先别赶，手腕松了再敲。账要平。
- **#5018** `P010` → `P009`｜day 0 · evening · place `cafe`｜topic `combat_training`｜turn_index 4｜type `MSG_DM`
  > 账本我拿橡皮擦蹭掉两行重写，鼓槌就搁在砚台边上沾了点墨，第三小节我改成先落半拍再补，手腕松着来才不僵嘛。
- **#6266** `P009` → `P010`｜day 0 · evening · place `cafe`｜topic `combat_training`｜turn_index 5｜type `MSG_DM`
  > 算盘珠子卡在第三档，我拿指甲抠了半天才拨正。你那鼓槌沾了墨，敲下去账上怕是要多一笔。

### CYCLE-21B / B 实验臂（旁白放开）
| 项 | 值 |
|---|---|
| 来源文件 | `.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl` |
| 日志 sha256（全长） | `87e233c421aebeb5ecf3d4f37c74ba721cd6829f3d7e55ec75042e76d350f2f4`（sha8 = `87e233c4`）|
| 日志规模 | 115545 events / 56,148,529 B |
| 跑批身份（`meta.json`） | `code_sha = code_sha_end = c74985050b86f31c21f4ab90da8d9244b3410251`；`seed 42`；`rounds 60`；`n 16`；`provider openai_compat`；`model DeepSeek-Flash`；`llm_calls 2869`；`degraded_calls 0`；`finished_at 2026-10-24T16:23:24+08:00` |
| 本臂线程总数（MSG_DM+MSG_PUBLIC 重建） | 170 |

> ⚠ 本批日志位于 `v2/evidence/` 下，受 `.gitignore`（`**/*.jsonl`）排除 ⇒ **不在 git 对象里**：可原地复算 sha、可重渲染，但不可从零重建。

#### 段 3｜`TH-P004-P002-0`（CYCLE-21B，6 条，DM）

| 项 | 值 |
|---|---|
| segment_id | `CYCLE-21B-TH-P004-P002-0` |
| 来源文件 | `.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl` |
| 来源 sha256 前 8 位 | `87e233c4` |
| thread_id | `TH-P004-P002-0` |
| 参与人 | `P002`, `P004` |
| seq 序列 | `73`, `549`, `2090`, `2914`, `4920`, `5556` |
| day / slot | day [0]；slot morning → afternoon → evening |
| 地点（逐条可变的 payload.place） | library → market → community_center |
| 段内以全角括号开头的消息数（描述性计数，非臂级结论） | 6/6 |

逐字原文（左侧 `#seq` 为 run.jsonl 顶层 `seq` 字段；`day/slot/place` 逐条取 `payload` 原值）：

- **#73** `P004` → `P002`｜day 0 · morning · place `library`｜topic `mentorship`｜turn_index 0｜type `MSG_DM`
  > （把沾着面粉的擀面杖搁下）听说你这两天在给东头老周家修灶台，忙得开不了火？我这炉新试的枣泥酥总差点意思，想请你尝尝，顺嘴给句实话。你尝一口。
- **#549** `P002` → `P004`｜day 0 · morning · place `library`｜topic `mentorship`｜turn_index 1｜type `MSG_DM`
  > （在围裙上蹭了蹭手）哎，老周家灶膛我拿墨斗弹了线，你这酥皮起得匀不匀？
- **#2090** `P004` → `P002`｜day 0 · afternoon · place `market`｜topic `mentorship`｜turn_index 2｜type `MSG_DM`
  > （捏着刚出炉的桃酥）老周家那灶膛你弹了线，我这炉桃酥边角还带点焦，你尝尝火候够不够？
- **#2914** `P002` → `P004`｜day 0 · afternoon · place `market`｜topic `mentorship`｜turn_index 3｜type `MSG_DM`
  > （用刨子推着木料）哎，火候正好，我那块榆木案板还差你灶上一道烟熏色。
- **#4920** `P004` → `P002`｜day 0 · evening · place `community_center`｜topic `mentorship`｜turn_index 4｜type `MSG_DM`
  > （拿筷子搅着盆里的枣泥）你这手艺我惦记好久了，明儿蒸锅枣糕，你过来尝尝。
- **#5556** `P002` → `P004`｜day 0 · evening · place `community_center`｜topic `mentorship`｜turn_index 5｜type `MSG_DM`
  > （刨子搁在凳上）枣糕不急，你那窗棂子还歪着，先说说这阵子咋样？

#### 段 4｜`TH-P010-P009-0`（CYCLE-21B，6 条，DM）

| 项 | 值 |
|---|---|
| segment_id | `CYCLE-21B-TH-P010-P009-0` |
| 来源文件 | `.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl` |
| 来源 sha256 前 8 位 | `87e233c4` |
| thread_id | `TH-P010-P009-0` |
| 参与人 | `P009`, `P010` |
| seq 序列 | `135`, `954`, `2162`, `3760`, `5018`, `6266` |
| day / slot | day [0]；slot morning → afternoon → evening |
| 地点（逐条可变的 payload.place） | park → farm → market → cafe |
| 段内以全角括号开头的消息数（描述性计数，非臂级结论） | 6/6 |

逐字原文（左侧 `#seq` 为 run.jsonl 顶层 `seq` 字段；`day/slot/place` 逐条取 `payload` 原值）：

- **#135** `P010` → `P009`｜day 0 · morning · place `park`｜topic `combat_training`｜turn_index 0｜type `MSG_DM`
  > （压着腿）金先生，这段鼓点我总踩不稳。您听听。
- **#954** `P009` → `P010`｜day 0 · morning · place `park`｜topic `combat_training`｜turn_index 1｜type `MSG_DM`
  > （翻着账本）鼓点像利息，差一厘都不行。
- **#2162** `P010` → `P009`｜day 0 · afternoon · place `farm`｜topic `combat_training`｜turn_index 2｜type `MSG_DM`
  > （把鼓槌在指间转了半圈）哎，金先生，我这鼓点要是真按利息算，昨儿后半夜在礼堂敲的那段早该倒贴钱了——您说这练功的账，到底该记在哪本上呢？
- **#3760** `P009` → `P010`｜day 0 · afternoon · place `market`｜topic `combat_training`｜turn_index 3｜type `MSG_DM`
  > （把算盘往柜台上一推）你那鼓点记谁家账上？
- **#5018** `P010` → `P009`｜day 0 · evening · place `cafe`｜topic `combat_training`｜turn_index 4｜type `MSG_DM`
  > （把鼓槌搁在凳上）这鼓点记我自个儿账上吧
- **#6266** `P009` → `P010`｜day 0 · evening · place `cafe`｜topic `combat_training`｜turn_index 5｜type `MSG_DM`
  > （拨着算盘珠子）我这月流水还差三块二。你那鼓点先记着，回头我拿铜板跟你平。

---

## 2. 自检：body 在 run.jsonl 中逐字命中（含 seq 对位）

方法：对每条引用的 `payload.body` 原文执行 `grep -n -F -- <body> <run.jsonl>`（`-F` 固定串匹配，避免正则元字符干扰），要求**命中行数 = 1**，并回读该行的 `seq` 字段，要求**与正文标注的 seq 相等**（`seq 对位` 列）。

| 臂 | thread_id | seq | 命中行号 | 命中数 | seq 对位 | 命令 |
|---|---|---|---|---|---|---|
| `CYCLE-21C` | `TH-P004-P002-0` | `73` | 74 | 1 | ✅ | `grep -n -F -- '这炉桃酥我总烤不出你家的脆劲儿，你最近忙得过来不？教教我。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P004-P002-0` | `549` | 550 | 1 | ✅ | `grep -n -F -- '哎，我正刨着刘家那根榆木梁，手头活儿紧，你明儿带块面来我这儿，我边做边教你，行不？' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P004-P002-0` | `2090` | 2091 | 1 | ✅ | `grep -n -F -- '你那根榆木梁刨到哪一步了，我明儿带块发好的面过去，你腾得出手教我和面不？' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P004-P002-0` | `2914` | 2915 | 1 | ✅ | `grep -n -F -- '哎，刨到卯口了，你带面来我教你揉，顺手把窗台上那把旧刨刀递我。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P004-P002-0` | `4920` | 4921 | 1 | ✅ | `grep -n -F -- '老石，你这话说得我心里痒，我正给王家小孙子捏那屉小兔子馒头呢，面还软着。刨刀给你，我这就去拿面。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P004-P002-0` | `5556` | 5557 | 1 | ✅ | `grep -n -F -- '面软着就先别急着捏，王家小孙子那屉兔子馒头等得起。我这刨刀刚啃上榆木，纹路正顺，换手反倒要起毛。你揉面时手腕使几分劲，是凭手感还是看面醒到啥程度？' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P010-P009-0` | `135` | 136 | 1 | ✅ | `grep -n -F -- '金先生，我把这段副歌的鼓点改到第三小节了，你听听看。就这儿。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P010-P009-0` | `954` | 955 | 1 | ✅ | `grep -n -F -- '鼓点挪到第三小节，我算了下，跟前面两拍正好凑成四四拍，账要平。你敲一遍。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P010-P009-0` | `2162` | 2163 | 1 | ✅ | `grep -n -F -- '哎，我手里这杯凉透的咖啡还没喝完呢，先把鼓槌搁下——你说的第三小节我试了，跟前面两拍确实能凑上，可敲出来像赶集似的，你听听是不是我手腕太僵了？' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P010-P009-0` | `3760` | 3761 | 1 | ✅ | `grep -n -F -- '你那鼓槌还搁在账本边上呢，第三小节先别赶，手腕松了再敲。账要平。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P010-P009-0` | `5018` | 5019 | 1 | ✅ | `grep -n -F -- '账本我拿橡皮擦蹭掉两行重写，鼓槌就搁在砚台边上沾了点墨，第三小节我改成先落半拍再补，手腕松着来才不僵嘛。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21C` | `TH-P010-P009-0` | `6266` | 6267 | 1 | ✅ | `grep -n -F -- '算盘珠子卡在第三档，我拿指甲抠了半天才拨正。你那鼓槌沾了墨，敲下去账上怕是要多一笔。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P004-P002-0` | `73` | 74 | 1 | ✅ | `grep -n -F -- '（把沾着面粉的擀面杖搁下）听说你这两天在给东头老周家修灶台，忙得开不了火？我这炉新试的枣泥酥总差点意思，想请你尝尝，顺嘴给句实话。你尝一口。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P004-P002-0` | `549` | 550 | 1 | ✅ | `grep -n -F -- '（在围裙上蹭了蹭手）哎，老周家灶膛我拿墨斗弹了线，你这酥皮起得匀不匀？' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P004-P002-0` | `2090` | 2091 | 1 | ✅ | `grep -n -F -- '（捏着刚出炉的桃酥）老周家那灶膛你弹了线，我这炉桃酥边角还带点焦，你尝尝火候够不够？' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P004-P002-0` | `2914` | 2915 | 1 | ✅ | `grep -n -F -- '（用刨子推着木料）哎，火候正好，我那块榆木案板还差你灶上一道烟熏色。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P004-P002-0` | `4920` | 4921 | 1 | ✅ | `grep -n -F -- '（拿筷子搅着盆里的枣泥）你这手艺我惦记好久了，明儿蒸锅枣糕，你过来尝尝。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P004-P002-0` | `5556` | 5557 | 1 | ✅ | `grep -n -F -- '（刨子搁在凳上）枣糕不急，你那窗棂子还歪着，先说说这阵子咋样？' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P010-P009-0` | `135` | 136 | 1 | ✅ | `grep -n -F -- '（压着腿）金先生，这段鼓点我总踩不稳。您听听。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P010-P009-0` | `954` | 955 | 1 | ✅ | `grep -n -F -- '（翻着账本）鼓点像利息，差一厘都不行。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P010-P009-0` | `2162` | 2163 | 1 | ✅ | `grep -n -F -- '（把鼓槌在指间转了半圈）哎，金先生，我这鼓点要是真按利息算，昨儿后半夜在礼堂敲的那段早该倒贴钱了——您说这练功的账，到底该记在哪本上呢？' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P010-P009-0` | `3760` | 3761 | 1 | ✅ | `grep -n -F -- '（把算盘往柜台上一推）你那鼓点记谁家账上？' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P010-P009-0` | `5018` | 5019 | 1 | ✅ | `grep -n -F -- '（把鼓槌搁在凳上）这鼓点记我自个儿账上吧' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |
| `CYCLE-21B` | `TH-P010-P009-0` | `6266` | 6267 | 1 | ✅ | `grep -n -F -- '（拨着算盘珠子）我这月流水还差三块二。你那鼓点先记着，回头我拿铜板跟你平。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl'` |

**自检结论**：共 24 条引用消息，逐字命中 24 条、异常 0 条；其中命中唯一且 seq 对位一致 24/24 条。要求：每条命中行数 = 1 且 seq 对位一致。

大批量复核方式：逐条重放第 2 节表格里的命令即可。示例（取表中第一条）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
grep -n -F -- '这炉桃酥我总烤不出你家的脆劲儿，你最近忙得过来不？教教我。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
```

---

## 3. 能与不能

### 能证明
1. 上述每一条消息的 `seq`、发言人、`thread_id`、`day/slot/place`、正文，都能在对应 `run.jsonl` 中逐字命中（第 2 节已逐条落盘命中数）；
2. C 臂所选两段消息正文**无**全角括号动作旁白，B 臂所选两段消息正文**以**全角括号动作旁白开头（形态差异在两个臂内部一致，可直接肉眼核对本文件原文）；
3. 两臂各自 `meta.degraded_calls = 0`、`provider openai_compat` ⇒ 文本由真 LLM 生成，非兜底模板。

### 不能证明
1. **不能**给任何旁白率/一致率数字下结论 —— 本文件是**样本摘录**（4 线程 × 6 条 = 24 条），不是分层随机抽样，不能外推到臂级比例；读数以 `metric-recomputer` 的复算件为准；
2. **不能**当作同一局模拟的同轨迹对照 —— 段 1/3、段 2/4 只是 thread_id 相同，来自两个独立 run（`code_sha` 不同、`run_sha256` 不同），World 演化路径不同；
3. **不能**证明任何「更生活 / 更真实」的效果判断 —— 本周期无判据编号、无闸线；
4. `place` 字段在线程内逐条变化（同一线程跨 morning/afternoon/evening、跨地点），不能据此推断「这些人在同一地点连续对话」；`MSG_PUBLIC` 的 `place` 为 `null` 属原值，本次所引 4 段均为 `MSG_DM`。
