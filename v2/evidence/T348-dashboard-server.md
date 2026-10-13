# T348 · 看板服务存活 + 「无法报告」修复

**背景**：用户 11:57 报"打不开" ⇒ 实测 `serve.py` 已不在进程、`curl :8848` = **000**。最差失败形态不是"报错"，而是"**无法报告**"（什么都加载不出）。

## ① 不易死：systemd **transient** 托管（运行时创建、不安装 unit 文件；可 status/restart/log）
```
systemd-run --unit=hitt-dashboard --collect --property=Restart=always --property=RestartSec=2 \
  --property=WorkingDirectory=<code/frontend> --setenv=HITT_LIVE_ROOTS=/root/t271/runs \
  python3 tools/serve.py --host 0.0.0.0 --port 8848
```
- **端口** `8848`；**白名单根** `HITT_LIVE_ROOTS=/root/t271/runs`（realpath 规范化后判定）。
- **保活实测**：`kill <pid>` → **5s 内自动拉起**、`dashboard.html` 回到 **200**（先前 `Restart=on-failure` 无效：SIGTERM 被 systemd 判为 clean exit ⇒ 改 `Restart=always`）。
- **一键管理**（任何成员可照做）：`bash code/frontend/tools/serve_ctl.sh {start|restart|stop|status|log}`；无 systemd 用 `start-nohup` 兜底。
- ⚠️ **本地开发服务，不对外暴露**。

## ② 「无法报告」修复（服务重启/未就绪/批已结束 → 明确文案）
- **服务不可达**：浏览器本就无法加载页面 ⇒ 靠 **①** 让它几乎不死 + **一键重启命令**（任一成员可执行）。**如实说明这是本条的边界**：页面无法自我报告"宿主服务已死"。
- **文件未出现（批未起跑/未落盘）**：`/__tail` 返回 `waiting:true` ⇒ 页面显 **"等待新数据（文件未出现）"**（不是"读取失败/越权"）。
- ⭐ **批已结束**：新增只读端点 **`/__runinfo`**（读同目录 `meta.json`/`heartbeat.tsv`）⇒ 页面自动转 **"跟随已结束（批已完成，<ended_at>）· 可回放（尾部窗口 N 事件）"**，**停止轮询**（终态可达）。
- **追平(eof)≠结束**：`--flush-every 12` 使"活着的批看起来像死的" ⇒ 只显示"**已追平（等待新数据）**"，>5 分钟无增长才提示"可能已结束"，且不停轮询。

## 证据
- `T348-live-ended.png`：批结束后 `?z=live` 顶部 **批次 t300 · round 83 · 跟随已结束（2026-10-13 11:52:19）· 可回放**。
- `T348-dash-baseline-t300.png`：看板**基线区已更新**为 **v2-T300 · n_events 292,963 · 权威/现行**（消费 obs 清单 `5b0f761`）。
- **跨成员可复现**：`serve_ctl.sh status` → `active` + `200`。

## 变更文件
`code/frontend/tools/serve.py`（`/__runinfo`、waiting 语义、白名单 realpath 非 strict）、`src/main.js`（终态/等待/追平 状态机）、`tools/serve_ctl.sh`（新建）、`dashboard.html`（重生成）。
