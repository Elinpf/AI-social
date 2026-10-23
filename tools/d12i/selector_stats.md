# `tools/d12i/selector_stats.py` —— 选优机制统计（纯只读）

- 文件 sha256：`58c7f8e3dacc739f19fcb30551fc59ac610937d3e1d4abe7a755fe074fc1accf`
- 用途：一条命令出 **`argmin_unique`** 与 **`not_all_equal`**（并列，口径写死）+ `all_zero` + 三候选 shingle 层全同 + `picked` 分布 + `scores` 统计。
- 用法：
  ```bash
  python3 tools/d12i/selector_stats.py --log <run.jsonl> [--rounds N] [--key d12i|d12h]
  ```
- 退出码：0 正常；2 日志无该类消息。

## 为什么要两个数并列（"同名不同义"第 N 次预防）

| 名字 | 定义 | `scores=[1,1,2]` | 能不能当判据 |
|---|---|---|---|
| **`argmin_unique`** | **最小值的索引唯一** | **False** | ✅ 预登记的"argmin 唯一率"就是它 |
| `not_all_equal` | 分数不全同 | True | ❌ 只是"有区分度" |

D12-I 实测：`argmin_unique = 480/510 = 94.1%`、`not_all_equal = 503/510 = 98.6%`。
（Leader 核验件里曾用后者，已更正为前者。）
