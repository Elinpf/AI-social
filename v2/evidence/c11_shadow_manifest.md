# C11 证据卫生 · `code/v2/` 影子目录移出仓库（只移不删）

> 作者：batch-operator｜2026-10-23 20:2x (+08:00)｜执行前提：D12-G（PID 1039299/1039307）**已自然退出**（`run_batch.rc=0`）
> 处置方式：**`mv` 到仓库外备份，绝不 `rm`**（可回滚）。本条不是"清理垃圾"，是**移除审计面污染源**。

## 1. 移动前后实测（可复算）

```
$ cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment      # 主仓（不是 worktree）
$ find code/v2 -type f | wc -l          →  12402
$ du -sh code/v2                        →  50M
$ find code/v2 -maxdepth 3 -type d | sort > /tmp/c11_shadow_backup/dirs.txt
$ find code/v2 -type f -printf '%s\t%p\n' | sort -k2 > /tmp/c11_shadow_backup/files_manifest.tsv   →  12402 行
$ mkdir -p /tmp/c11_shadow_backup && mv code/v2 /tmp/c11_shadow_backup/code_v2_shadow
$ find /tmp/c11_shadow_backup/code_v2_shadow -type f | wc -l   →  12402   （= 移动前，零丢失）
$ du -sh /tmp/c11_shadow_backup/code_v2_shadow                 →  50M     （= 移动前）
$ ls -d code/v2                                                →  NO       （仓库内已不存在）
```

| 项 | 移动前 | 移动后 |
|---|---|---|
| `code/v2` 文件数 | **12,402** | **0**（目录已不在仓库内） |
| 体积 | **50M** | — |
| 备份位置文件数 / 体积 | — | **12,402 / 50M**（`/tmp/c11_shadow_backup/code_v2_shadow`） |
| 主仓 `git status --short \| wc -l` | **51** | **50**（少的就是 `?? code/v2/`） |

清单文件（不随本次提交，体积原因，按需可再生成）：
`/tmp/c11_shadow_backup/files_manifest.tsv`（12402 行，每行 `字节数<TAB>相对路径`）、`/tmp/c11_shadow_backup/dirs.txt`（目录树）。

## 2. 为什么它在 `code/` 里是**红线**

1. **污染 `code_sha` 语义**：`meta.json.code_sha` 承诺"这批跑的是哪个 commit"。`code/` 目录下出现 12,402 个运行产物（`code/v2/evidence/run_*/…`，即早期未加 `--side-root` 时按相对路径写进去的影子），会让"代码树"与"产物树"混在一起；任何人 `git status`/`du` 看到的 `code/` 都不再是 commit 的内容。
2. **破坏"跑批期间不改 code/"的审计面**：纪律要求跑批期间 `code/life|orchestration|config|engine` 一字不动、且 `git_dirty_code_files` 为空才有意义。影子目录持续被写入，等于让 `code/` 在跑批期间一直被"改"（虽是产物不是源码），`git_dirty_code_files` 这类判据就失去分辨力——真有人动了源码，也容易被"code/ 本来就在变"糊过去。
3. **可复现性风险**：影子目录里的 `side/` 产物与主 `v2/evidence/` 同名/近似，容易在复算时被误当权威证据（同名不同批次），是最典型的"证据串味"入口。

⇒ 因此处置是**移出仓库**而不是加 `.gitignore` 忽略：忽略会把"影子又长出来"这件事藏起来，`mv` 才能让 `git status` 继续当哨兵（下次若有人再在 `code/` 下写产物，`?? code/v2/` 会立刻再出现）。

## 3. 未做/不做的部分（诚实登记）

- **没有**回写/清理 `/tmp/d12g_side`（本批 `--side-root` 指定的仓库外 side 目录，属本批产物，另案处理）；
- **没有**给 `code/v2/` 加忽略规则（理由见 §2 第 3 条）；
- 备份在 `/tmp` 下，**非持久**（重启即失）。若要长期留档，需由 Leader 决定迁到持久位置。
