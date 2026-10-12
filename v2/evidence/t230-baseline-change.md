# T230 · 基线变动声明 + 有/无还款对照

> 作者：econ-dev ｜ 2026-10-12 ｜ 相关提交 `84f0a69`（T230 接线 3 事件）
> **目的**：T230 引入三个**行为变更**，此后任何 run 的世界与 **T133 基线不同** —— 本文档显式声明并给出可比数字，避免后人拿两个不同世界的数做对比。

## 0. 基线已变动（⚠️ 必读）

T230 引入的**行为变更**（非调参）：
1. **新增按期还本**：econ 4.2 每回合按 `loan_repay_bp`（默认 **10%**）对在期/续期贷还本 → 发 `LOAN_REPAY`；
2. **新增销毁通道**：系统贷还款=销毁 → 发 `MONEY_BURNED`（与 `LOAN_REPAY` 配对）；**销毁总量因此增加**；
3. **新增要约超时终止**：`OFFER_*` 超窗口（默认 7 回合）未终态 → `OFFER_EXPIRED`。

→ **「关闭 = 现状」类证明（如 T222 的 `events = 36,763 = T133 基线`）在本提交后过期。**

## 1. 新基线（rule-based N=10×84 seed7，默认配置）

- **sha**：`84f0a69` ｜ **命令**：`build_world(seed=7, n=10)` 跑 84 回合（rule-based，无真 LLM provider）
- **事件总量**：**36,813**（T133 基线 36,763 → **+50**，含 `OFFER_EXPIRED=46` 等）
- 关键事件计数：

| 事件 | 计数 |
|---|---|
| `LOAN_REPAY` | 21 |
| `MONEY_BURNED` | 21 |
| `OFFER_EXPIRED` | 46 |
| `EXCHANGE_SETTLED` | 25 ｜ `TRANSFER` 14 ｜ `MARKET_TRADE` 14 |
| `LOAN_ISSUED` 10 ｜ `LOAN_DEFAULT` 4 ｜ `METABOLISM` 790 |
| `AGENT_DIED` 10 ｜ `PRODUCE` 155 |
| `M_final` | **18,292** |

## 2. 有/无还款对照（同 seed=7, N=10, 84 回合；只差 `loan_repay_bp`）

| 指标 | 默认 `loan_repay_bp=1000` | `loan_repay_bp=0`（关还款） | 差 |
|---|---|---|---|
| `LOAN_REPAY` | **21** | 0 | +21 |
| `MONEY_BURNED` | **21** | 0 | +21 |
| `LOAN_DEFAULT` | 4 | 5 | −1（还款减少坏账） |
| `OFFER_EXPIRED` | 46 | 46 | 0（不受还款影响） |
| `EXCHANGE_SETTLED` | 25 | 25 | 0 |
| 事件总量 | 36,813 | 36,809 | +4 |
| `M_final` | **18,292** | 18,908 | **−616**（还款销毁货币） |

> **读法**：还款机制使 `LOAN_REPAY`/`MONEY_BURNED` 从 0→21、`M_final` 降 616（销毁通道），并略减坏账；`OFFER_EXPIRED`/`EXCHANGE_SETTLED` 与还款无关（两态一致）。

## 3. 可比性声明

- **本次 run 含 T230 新机制（还本/销毁/要约超时），与 T133 基线不可直接对比。**
- 需要"逐变量隔离"时：用上表 `loan_repay_bp=0` 关掉还款；要约超时如需关闭，可加大 `exchange.offer_expire_rounds`（或后续加开关）。
- 口径纪律：本文件所有数字均标 **sha + 命令 + provider(rule-based)**；真 LLM run 不可与此直接互比。
