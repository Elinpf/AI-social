# F-3 跑批代码树指纹 · 口径定义与可复算命令

> 目的：F-3 实现未提交（HEAD=`6b7ae8a`，工作树 dirty），`meta.code_sha` 不含 F-3，
> 因此「两臂跑的是同一份代码」不能靠 `code_sha` 证明，只能靠**跑前/跑中两次逐文件 sha256 聚合指纹完全相同**来证明。
> 本文件把口径、命令、以及它**能证明什么/不能证明什么**写死，供任何人自证复跑。

## 0. 一句话结论

- 首次引用的 `AGGREGATE=42c1bdd94e9c53499c2406e20c8c698f49763ab51fc68fbeed5f7c8a0b9c7e38` 是**口径 A**，
  覆盖 **105 个文件**，范围 = `code/{life,config,orchestration,engine}` 四子树里的 `.py`/`.json`（`maxdepth 2`）。
- 它是一个**四子树子集指纹**，**不是整棵 `code/` 树指纹**：`code/frontend`(666)、`code/freeze_cache`(1677)、
  `code/tests`(84)、`code/obs`(28) 等均**未纳入**。所以它只能证明「跑批相关四子树没漂」，
  **不能**宣称「两臂跑的是同一棵完整代码树」。

## 1. 口径 A（首次引用的 42c1bdd9…）

**选法**：只取 4 个目录（`code/life`、`code/config`、`code/orchestration`、`code/engine`）；
`-maxdepth 2`；只取 `.py` 与 `.json`；排除 `__pycache__`；按路径 `sort`；逐文件 `sha256sum`；
把 `sha256sum` 的逐行输出**整体再喂给一次 `sha256sum`** 得到聚合值（含文件内相对路径，不含时间/uid 等易变信息）。

```bash
find code/life code/config code/orchestration code/engine -maxdepth 2 -type f \
     \( -name '*.py' -o -name '*.json' \) ! -path '*__pycache__*' \
  | sort | xargs sha256sum | sha256sum
# → 42c1bdd94e9c53499c2406e20c8c698f49763ab51fc68fbeed5f7c8a0b9c7e38  -
```

**逐目录构成（105 个）**：`code/config` 16 / `code/engine` 34 / `code/life` 50 / `code/orchestration` 5。

**已知遗漏（口径 A 的 3 个盲点，口径 B 补上）**：
```
code/life/NOTICE                              （非 .py/.json）
code/life/tests/support/__init__.py           （深度 3）
code/life/tests/support/mini_kernel.py        （深度 3）
```

## 2. 口径 B（**R14 正式口径**：code 四子树聚合指纹）

> 命名写死：**`code 四子树聚合指纹（life/config/orchestration/engine，108 文件）`**。
> R14 及任何汇报里**不得简称「整树」**——它不覆盖 `code/` 全树，见 §2.1。

**选法**：同 4 个目录，**不限扩展名、不限深度**，排除 `__pycache__` 与 `*.pyc`；其余同上。

```bash
find code/life code/config code/orchestration code/engine -type f \
     ! -path '*__pycache__*' ! -name '*.pyc' \
  | sort | xargs sha256sum | sha256sum
# → 68683fe3caef04369bd262fc586522a93f5df8326fddd52400f50f57f4b780af  -   （108 个文件）
```

**为什么 B 更适合当正式口径**：A 的 `maxdepth 2` 与扩展名白名单都是人为裁剪（正是它漏了 `life/tests/support/*.py`），
B 对四子树无裁剪，口径更容易被复现方一次对上；B 的 108 = `life 53 + config 16 + orchestration 5 + engine 34`，
与 `find <dir> -type f` 的直接计数一致，可用一条独立命令校验。

## 2.1 未纳入范围（**没覆盖什么，和覆盖了什么一样重要**）

口径 B 只覆盖 4 个子树；`code/` 下其余内容**全部未纳入**。计数给两列：
「全部文件」与「排除 `__pycache__`/`*.pyc`」——后者才与口径 B 的排除规则同构，引用时请注明用的是哪一列。

| 路径（**必须写全路径**） | 全部文件 | 排除 `__pycache__`/`*.pyc` |
|---|---|---|
| `code/obs` | 44 | 28 |
| `code/frontend` | 667 | 666 |
| `code/tests` | 84 | 84 |
| `code/freeze_cache` | 1677 | 1677 |
| `code/contracts` | 13 | 7 |
| `code/scripts` | 11 | 11 |
| `code/logs` | 5 | 5 |
| `code/reports` | 6 | 6 |
| `code/devtools` | 5 | 5 |
| `code/narrative` | 2 | 2 |
| `code/licenses` | 2 | 2 |
| `freeze_cache`（**仓库根**，不是 `code/freeze_cache`） | 127 | 127 |

**同名路径必须写全，仅写目录名会导致读者取到另一处的计数**：`code/freeze_cache`(1677) 与仓库根 `freeze_cache`(127)
是两个不同的目录，两边数字都"看着像真的"；同理 `code/obs` 的全部计数(44) 与排除后计数(28) 也都能"看着像真的"，
不注明计数规则就会被引成互相矛盾的两个值。

## 3. 为什么不做「整棵 code/ 树」指纹

`code/` 下含**跑批自己生成/变化的产物与大体积缓存**：`code/freeze_cache`、`code/frontend`、
`code/OFF.jsonl`、`code/ON.jsonl`、`code/logs/`、`code/reports/` 等。

理由有两层，第二层更重要：

1. **产物漂移**：把这些纳入会让指纹**在两次计算之间因产物写入而漂移**，从而把「代码是否变化」和「产物是否写出」混为一谈。
2. **命题污染**：把产物写进代码指纹，会让「代码没变」与「产物没写」两个完全不同的命题被压缩成同一个数值。
   一旦指纹变了，读者无法判断是有人改了代码，还是系统正常写了个日志。**指纹必须只覆盖"输入"，绝不能包含"输出"。**

若确需整树口径，应当先显式定义排除集（产物/缓存/生成物），否则不可用。

## 4. 逐文件清单

`v2/evidence/f3_code_fingerprint_files_prerun.txt`：口径 A 与口径 B 的**逐文件 sha256 全量清单**（各 105 / 108 行）。
任何人对同一棵树复跑上面两条命令，必须逐字节得到与本文件相同的清单与聚合值。

## 5. 两次计算的用途（两臂同一性的硬证据）

| 时点 | 用途 | 期望 |
|---|---|---|
| OFF 臂起跑前（00:20:38，`f3_code_fingerprint_prerun.txt`） | 基线 | 基准值 |
| ON 臂起跑前（同命令复算） | 证明窗口内代码未动 ⇒ 两臂同一棵树 | 两次聚合值与逐文件清单**完全相同** |

两次不等 ⇒ 立即停跑、不上第二臂、报 Leader。
