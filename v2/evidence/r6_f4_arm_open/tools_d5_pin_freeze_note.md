# tools/d5/dialogue_metrics.py 在 pin 时点的字节物证（防止工作区改动消失后成悬案）

- 记录时刻：2026-10-20T20:39:47+08:00｜HEAD：6074502f4062891d05e1057df08243d11c3cb79d
- 工作区版本 sha256：`5fede53838b183eae48bd3c3f922c17499338d2ae74349f8e444119e5580c6fb`
- 改动来源：**prompt-linguist**（非本团队成员），内容为 **L-12 拆分为 L-12a「对端提及」/ L-12b「对端称呼」**
- patch 文件：`tools_d5_diff_at_pin_5fede538.patch`，sha256 = `43821eb1feb38e48d0fe6f8758b9311730cd627ea2768d95abf38b35dd1a7e53`
- 三 sha 并列：历史锁定版 `d7e2da17…f97306` / 中间版 `371c9fa1…43de9751` / **本轮使用版 `5fede538…5580c6fb`**

## 字段级核查：F-4 / F-4b 相关行是否被该改动触碰

```bash
$ git diff -- tools/d5/dialogue_metrics.py | grep -E "^[+-].*(F-4|tension|repair|closed_loop)"
```

```
(无输出)
```

**结论：无 F-4 相关行变动** ⇒ 该改动不触及 F-4/F-4b 逻辑；F 系列读数在 `5fede538` 与历史版之间口径一致。

## 该改动的功能范围（供审计，不掩饰）

- 触及：`L-12_peer_name_address_rate` 被拆成 `L-12_peer_mention_rate`(L-12a) 与 `L-12b_peer_address_rate`(L-12b)，并新增 `L-12_definitions`；markdown 输出表相应改为两行。
- **旧键 `L-12_peer_name_address_rate` 在新版中不再存在** ⇒ 仍在读该键的下游脚本会拿到 None，**这是潜在的兼容性破坏点**，已如实记录（与本轮 F-4 无关，但 T5 入库时须一并说明）。

## 处置（Leader 裁决）

1. 两臂一律用 `5fede538`；Arm-C 起跑前 `rc=5` 会抓 `tools/d5/` 任何变化，抓到即**拒开并报 Leader**，不许换个版本重跑。
2. T5 时该改动**单独入库**，commit message 写明来源 `prompt-linguist` 的 L-12a/L-12b 拆分、并注明不触及 F-4/F-4b 逻辑；不隐藏、不冒领。
