# T74 · 「活起来的小镇」全周回放证据（B2 @ N=20）

> 只读日志 · 不改 engine/config · 确定性不受影响。

## 1. 数据源（权威 + 派生播放视图）

| 用途 | 文件 | 规格 |
|---|---|---|
| **权威日志（唯一事实源，不改）** | `social-experiment/v1.2/evidence/run_abl_B2_N20.jsonl` | seed=42 / N=20 / 84 回合 / 124,451 事件 / `state_hash=sha256:486d31fc43dc…` / SYSTEM_ERROR=0 |
| **派生播放视图**（浏览器用，剔噪） | `code/frontend/sample/run_b2_n20_week.play.jsonl` | **10.6 MB**（-80%），保留 26,559 / 剔除 97,892 事件 |
| **round→字节偏移索引** | `code/frontend/sample/run_b2_n20_week.play.index.json` | 84 回合偏移 + 源 sha256 + authority 指针 |
| 参考指标/普查 | 同目录 `census_abl_B2_N20.json`、`run_abl_B2_N20.summary.json` | — |

**播放视图**由 `frontend/tools/make_playview.py` 生成：仅剔除**渲染无关高体量事件**
（`MEMORY_WRITE/MEMORY_RETRIEVE/MEMORY_REFLECT/OBSERVATION/LLM_CALL`）。
**校验**：折叠后的渲染状态与 canonical **逐 agent 一致**（21/21；round76 累计死 20、round83 存活 10，完全一致）。

## 2. 关键事件（round / seq）

| 事件 | round | seq | 备注 |
|---|---|---|---|
| 开场：20 人出生 | 0 | 1 | AGENT_BORN |
| **首笔市集交易** | 6 | 5826 | MARKET_TRADE |
| 首个 `near_death` | 58 | 88110 | P001 |
| **首笔续命贷** | 59 | 90451 | LOAN_ISSUED（P001）|
| **首次死亡** | 60 | 92770 | AGENT_DIED（P001）|
| 错峰死亡密集（单帧 9 死） | 73 | 111167… | 10 人同回合 |
| 全员死亡（20/20） | 76 | 114234 | P018 为最后 |
| **复活 10 人** | 78 | 115664… | AGENT_REVIVED + NARRATIVE(114895) |
| 周结束 | 83 | — | 存活 10 / 死亡 10 |

> 20 人 AGENT_DIED 错峰于 round 60–76；10 人于 round 78 复活 → 周末存活 10。

## 3. 关键帧序列（10 帧，`code/frontend/sample/`）

| 帧 | round | 文件 |
|---|---|---|
| 开场 | 0 | `kf_r00_open.png` |
| 首笔交易 | 6 | `kf_r06_first_trade.png` |
| 常态日 | 30 | `kf_r30_normal_day.png` |
| 濒死 | 58 | `kf_r58_near_death.png` |
| 续命贷 | 59 | `kf_r59_first_loan.png` |
| 首次死亡（灰化） | 60 | `kf_r60_first_death.png` |
| 单帧 9 死 | 73 | `kf_r73_mass_death.png` |
| 全员死亡 | 76 | `kf_r76_all_dead.png` |
| 复活 + 叙事 | 78 | `kf_r78_revive.png` |
| 周结束 | 83 | `kf_r83_week_end.png` |

每帧顶部带**说明条**（`?caption=`，含 round + 事件 + seq）。

## 4. 整周动画（21 帧 GIF）

`code/frontend/sample/qingxi_week_b2n20.gif`（1000×625，21 帧，~5.5 MB，约 11s 循环）——
展示居民移动 / 活动气泡 / 消息气泡 / 死亡灰化 / 复活。

## 5. 回放 URL（`0.0.0.0:8848` 常驻）

- 浏览器播放（跟随 / 步进）：`http://<LAN-IP>:8848/?log=sample/run_b2_n20_week.play.jsonl&round=60`
- 关键帧直达（固定画面 + 说明条）：
  - 首死：`?log=sample/run_b2_n20_week.play.jsonl&round=60&caption=首次死亡`
  - 复活：`?log=sample/run_b2_n20_week.play.jsonl&round=78`
- 审计抽屉：追加 `&audit=1`；角色/场所详情：`&agent=P001` / `&place=market`。

## 6. 复现命令

```bash
cd code
# 1) 生成派生播放视图 + 索引
python frontend/tools/make_playview.py --in ../v1.2/evidence/run_abl_B2_N20.jsonl \
  --out frontend/sample/run_b2_n20_week.play.jsonl \
  --index frontend/sample/run_b2_n20_week.play.index.json \
  --authority v1.2/evidence/run_abl_B2_N20.jsonl
# 2) 关键帧（示例）
bash frontend/tools/screenshot.sh /root/kf_r60.png sample/run_b2_n20_week.play.jsonl 60 1600x1000 "&caption=第60回合·首次死亡"
# 3) 服务
python frontend/tools/serve.py --host 0.0.0.0 --port 8848
```

## 7. 遗留

- **C@N=20**（含真 LLM judge/叙事）就绪后可补一版（待 T73）。
- 54MB canonical 已**不直接给浏览器**（防 OOM）；权威仍以 canonical 为准。
