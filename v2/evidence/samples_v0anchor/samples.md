# D6 原文样本候选（结构分档，非自然度）

- 日志 `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d2_before_n16_seed42/run.jsonl` (sha8 `c1f86bf6`)
- 消息 187 / 线程 172 / schema `legacy`
- 分档：good=0 mid=0 bad=172
- 规则：{"signals": ["has_pointer", "multi_turn(turns_A>=3)", "names_used(对端名出现)"], "good": "3 信号全中", "mid": "1–2 个", "bad": "0 个", "order_in_grade": "线程长度降序 → thread_key 升序（确定性）", "warning": "这是**结构分档**，不等于「读起来自然」；自然度由 judge/人评给，样本表只做候选池"}

## 最长线程

### `L:0|dm|P002-P004`（2 条 / turns_A=1 / 指针 0 / 点名 0）
```text
[seq 73 r0 morning library] 秀娘 → 老石: 秀娘笑眯眯地递过一块刚出炉的桂花糕：“来，尝尝这个，我新调的方子——你要是喜欢，回头我教你做，咱们街坊里就数你手巧。”
[seq 4662 r6 evening community_center] 秀娘 → 老石: 秀娘笑盈盈地把刚出炉的桂花糕塞到对方手里：“快尝尝，还热乎着呢，我特意少放了糖，就想着你爱吃这口。”
```

### `L:0|dm|P005-P016`（2 条 / turns_A=2 / 指针 0 / 点名 0）
```text
[seq 200 r0 morning park] 兰姐 → 陈医: （把秤砣往案板上一搁，抬眼打量你）哟，P005，你这身板练得倒结实，可光有力气不成——来，帮兰姐把这筐货搬上摊，我教你咋看秤星子，比划拳实在。
[seq 4688 r6 evening cafe] 陈医 → 兰姐: （压低声音）P016，你最近总说睡不着……我给你配的那副安神药，是不是没按时吃？
```

### `L:0|public|None-P005`（2 条 / turns_A=1 / 指针 0 / 点名 0）
```text
[seq 84 r0 morning None] 陈医 → None: （整理药柜时自言自语）这些药方子用了大半辈子，可每次看到病人痊愈，还是觉得值得。
[seq 1939 r3 afternoon None] 陈医 → None: （整理着药柜，自言自语）这药钱攒了三十年，够是够了……可人这一辈子，光攒钱又图个啥呢。
```

## 最短线程

### `L:0|dm|P001-P002`（1 条 / turns_A=1 / 指针 0 / 点名 0）
```text
[seq 1899 r3 afternoon market] 老周 → 老石: （摆摆手）不了，地里的活还等着我，改天再说吧。
```

### `L:0|dm|P001-P003`（1 条 / turns_A=1 / 指针 0 / 点名 0）
```text
[seq 4611 r6 evening market] 老周 → 阿禾: （把一袋新米往你手里塞）拿着，自家地里出的，不图啥。
```

### `L:0|dm|P002-P007`（1 条 / turns_A=1 / 指针 0 / 点名 0）
```text
[seq 4632 r6 evening community_center] 老石 → 阿林: 这木头我挑了三天，纹理顺，给你打个匣子。
```

## 指针链 vs 交替链 一致性（反例候选）

**不适用**：本批无任何 `reply_to`（legacy 单发），该检查对 v0-anchor 无意义。

## 档位 `good`

## 档位 `mid`

## 档位 `bad`

### `L:0|dm|P002-P004`（2 条 / turns_A=1）
```text
[seq 73 r0 morning library] 秀娘 → 老石: 秀娘笑眯眯地递过一块刚出炉的桂花糕：“来，尝尝这个，我新调的方子——你要是喜欢，回头我教你做，咱们街坊里就数你手巧。”
[seq 4662 r6 evening community_center] 秀娘 → 老石: 秀娘笑盈盈地把刚出炉的桂花糕塞到对方手里：“快尝尝，还热乎着呢，我特意少放了糖，就想着你爱吃这口。”
```

### `L:0|dm|P005-P016`（2 条 / turns_A=2）
```text
[seq 200 r0 morning park] 兰姐 → 陈医: （把秤砣往案板上一搁，抬眼打量你）哟，P005，你这身板练得倒结实，可光有力气不成——来，帮兰姐把这筐货搬上摊，我教你咋看秤星子，比划拳实在。
[seq 4688 r6 evening cafe] 陈医 → 兰姐: （压低声音）P016，你最近总说睡不着……我给你配的那副安神药，是不是没按时吃？
```

### `L:0|public|None-P005`（2 条 / turns_A=1）
```text
[seq 84 r0 morning None] 陈医 → None: （整理药柜时自言自语）这些药方子用了大半辈子，可每次看到病人痊愈，还是觉得值得。
[seq 1939 r3 afternoon None] 陈医 → None: （整理着药柜，自言自语）这药钱攒了三十年，够是够了……可人这一辈子，光攒钱又图个啥呢。
```

