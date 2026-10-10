# 事件卡机制区 空槽位 自检清单（T117）

> 判据（**三条件**）：① 机制槽色 `(225,228,235)` 的实心块 ② 块内**无深色墨迹** ③ 尺寸落在**槽位阈值**(30–64 × 18–34)；三者同时满足 → 判**空槽**。每卡判定依据见 JSON `candidates`。

| # | 卡 | 中文 | 标注类型 | 像素空槽 | 规格问题 | 状态 |
|---|---|---|---|---|---|---|
| 1 | mentorship | 导师指导 | rel-bars | 无 | 无 | **无需修** |
| 2 | gift-giving | 赠礼 | equation | 无 | 无 | **已修** |
| 3 | combat-training | 冲突演练 | status | 无 | 无 | **无需修** |
| 4 | creative-collab | 创意协作 | rel-bars | 无 | 无 | **无需修** |
| 5 | saving-money | 储蓄 | equation | 无 | 无 | **已修** |
| 6 | whispered-comm | 私语 | ab-choice | 无 | 无 | **无需修** |
| 7 | emotion-burnout | 情绪耗竭 | status | 无 | 无 | **无需修** |
| 8 | diff-scoring | 评分分歧 | rel-bars | 无 | 无 | **无需修** |
| 9 | scarcity-buy | 稀缺抢购 | equation | 无 | 无 | **已修** |
| 10 | skill-practice | 技能练习 | status | 无 | 无 | **无需修** |
| 11 | polite-reject | 礼貌拒绝 | ab-choice | 无 | 无 | **无需修** |
| 12 | passion-salary | 热爱与薪资 | ab-choice | 无 | 无 | **无需修** |
| 13 | group-proposal | 小组提案 | timeline | 无 | 无 | **无需修** |
| 14 | academic-collab | 学术协作 | rel-bars | 无 | 无 | **无需修** |
| 15 | counter-propose | 反提案 | timeline | 无 | 无 | **无需修** |
| 16 | select-location | 选择地点 | ab-choice | 无 | 无 | **无需修** |
| 17 | power-conflict | 权力冲突 | rel-bars | 无 | 无 | **无需修** |
| 18 | rel-acceptance | 关系接纳 | rel-bars | 无 | 无 | **无需修** |
| 19 | ice-breaking | 破冰 | ab-choice | 无 | 无 | **无需修** |
| 20 | rel-maintain | 关系维护 | timeline | 无 | 无 | **无需修** |

**结论**：20/20 张**像素级无空槽**；`equation` 类 3 张（scarcity-buy / gift-giving / saving-money）此前操作符项多画空槽，**已随 `else:`→`elif v:` 一行修法修复并重生成**。