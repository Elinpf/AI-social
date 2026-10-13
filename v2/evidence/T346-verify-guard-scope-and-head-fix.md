# T346 · 修 `T340` 守卫两处设计缺陷：指纹去 HEAD 输入 + 分段指纹分级结论

- **作者**：sandbox-test-lead（**非作者核对象**：本任务为**修装置**，非"被验对象"；三向反向验证自办）
- **交付 sha**：**`4ee4eb0`**（`T346 … 修 T340 守卫两设计缺陷`）—— 本报告与两个守卫脚本同提交。
- **待补**：真 `make verify` 收尾确认（等跑批结束，免污染跑批耗时读数）；三向反向验证已在独立克隆（假门）完成。
- **改动文件**：`tools/tree_fingerprint.sh`（重写）、`tools/verify_tree_guard.sh`（重写）、新增 `tools/t346_verify_guard_bidirectional.sh`（验证脚本）
- **不改断言语义**；`Makefile` 契约不变（`verify`→守卫，内部真门仍 `verify-inner`）。

---

## 1. 被修的两个缺陷（`T340`）

| # | 缺陷 | 后果 |
|---|---|---|
| ① | 冻结区含 `code/frontend/**` | 按新规**前端本来自由改** ⇒ 前端一提交，**任何人的** `make verify` 都被判"不可信"（拒绝服务） |
| ② | 指纹把 **`HEAD` 当比较输入**（`git rev-parse HEAD` 进哈希） | **任何**提交（哪怕只改 `v2/evidence/**`、不碰冻结区）都改 HEAD ⇒ **误红** |

## 2. 修法

**① 指纹只算【内容】，`HEAD` 只记录**（`tools/tree_fingerprint.sh` 重写）
- 对冻结文件**工作树内容**逐个 `sha256sum`（含路径名）→ 排序 → 汇总 `sha256`。**不读 `HEAD`**。
- 文件集：tracked 走 `git ls-files`（仅借它**列文件名**，不读 index 内容）+ untracked `--others --exclude-standard`；gitignore 生成物不计入 ⇒ 免假红。
- ⇒ 无关提交（`v2/evidence/**` 等）**不改变**指纹；而**任何文件内容改变**（含"编辑后提交""新增未跟踪"）都会被捕获。

**② 分段指纹 + 分级结论**（`tools/verify_tree_guard.sh` 重写）
- `world` = `config/**` + 世界层 `code/**`（**排除** `code/frontend/**`）；`front` = `code/frontend/**`。两枚指纹分别起/收比对。
- **世界层跑中变** ⇒ `exit 2`（不可信，请重跑）；
- **仅前端跑中变** ⇒ **降级为告警，不阻断**，明写"**前端 CI 部分不可信；世界层结论仍可信**"，`exit` 随门原码；
- 两者皆未变 ⇒ 门结果可信。
- 保留 `T340` 可信度口径；`HEAD` 起/收**只打印记录**。

## 3. 三向反向验证（必做）—— 全 PASS

口径：**独立克隆**（`git clone --local`）+ **假内部门**（`VERIFY_INNER_CMD='touch … && sleep 4'`，不跑真 `make verify`、不碰实时树）。脚本 `tools/t346_verify_guard_bidirectional.sh`。

| 例 | 跑中动作 | 期望 | 实测 |
|---|---|---|---|
| C0 控制 | 不改 | 绿 | **rc=0**「门结果可信」 |
| C1 | 改**世界层** `code/engine/`（新增未跟踪） | **红** | **rc=2**「世界层跑中被改…不可信」 |
| C2 | **只**改 `code/frontend/`（新增未跟踪） | **告警不阻断** | **rc=0** +「前端 CI 部分不可信；世界层结论仍可信」，**无**不可信 |
| C3 | 跑中**只提交 `v2/evidence/**`**（HEAD 动、冻结区未动） | **绿** | **rc=0**「门结果可信」；HEAD `9374c3a → 081a99d`（**确实动了**） |

**旧 T340 对照（证明缺陷真实存在）**：同一 C3 场景下，**旧守卫 rc=2（误红）**（起/收指纹 `9856c8a6… → 0fc3bb59…`，因 HEAD 进哈希）。
⇒ **新守卫 C3=绿 / 旧=红**，双向成立；C1/C2 证明新守卫既不"什么都放过"也不"动不动就红"。

## 4. 口径与命令

- 指纹：`bash tools/tree_fingerprint.sh world` / `front`（HEAD 无关）。
- 守卫：`bash tools/verify_tree_guard.sh`（默认门 `make verify-inner`；测试钩子 `VERIFY_INNER_CMD`）。
- 三向验证：`bash tools/t346_verify_guard_bidirectional.sh`（**建议在克隆里跑**，用假门）。
- 原子写：两脚本均 `install -m0755`（临时文件→目标，避免半写态假红）。

## 5. 结论（一句话）

**两处缺陷已修**：指纹**只算冻结区内容**（`HEAD` 仅记录）；**分段指纹**给出**分级结论**（世界层变⇒不可信；仅前端变⇒告警不阻断）。**三向反向验证全过**（世界层红 / 仅前端告警 / 仅证据提交绿）+ 旧 T340 误红对照；断言语义未改，不再是"前端一动手就堵死所有人"。

*（T346 — sandbox-test-lead）*
