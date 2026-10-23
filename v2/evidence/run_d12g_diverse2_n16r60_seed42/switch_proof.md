# D12-G 单臂 switch_proof（取自已执行进程环境）

- unit: `d12g-diverse2-n16r60.service`（`systemd-run --collect`）
- 起跑时刻: 2026-10-23T19:27:14 (+08:00)
- MainPID: 1039299（存活期取值）
- **cgroup**: `0::/system.slice/d12g-diverse2-n16r60.service`（真脱离证据）
- launch_cmd（原文）:
  `systemd-run --collect --unit=d12g-diverse2-n16r60 --property=EnvironmentFile=<wt>/code/.env.local --property=EnvironmentFile=/tmp/d12g_switches.env --working-directory=<wt> -- bash tools/d2/run_batch.sh --out-dir v2/evidence/run_d12g_diverse2_n16r60_seed42 --seed 42 --agents 16 --rounds 60 --side-root /tmp/d12g_side`
- `/proc/1039299/environ`（直接读进程，非父 shell）——**三条 env 齐**:
  ```
  HITT_LLM_PROVIDER=openai_compat
  LIFE_PROMPT_D12C_SPECIFIC=1
  LIFE_PROMPT_D12E_BESTOF=3
  LIFE_PROMPT_D12G_DIVERSE=3
  ```
- 代码树: `feat/d12g-diverse2` @ `344d3da`（引擎代码与 `feat/d12f-diverse@1a8a3b4` 相同），`code/` clean
- 运行期不可替换证据: `code/life/agent.py`
  - 跑前: `dc2a8012420bc342b58f2c1890ded06bb8baeb8b88631dd5d212478c81fafdf7`
  - 跑后: `dc2a8012420bc342b58f2c1890ded06bb8baeb8b88631dd5d212478c81fafdf7`（= 跑前值，逐字相同 ⇒ 跑批期间引擎未被替换/改动；收批时 `sha256sum code/life/agent.py` 实测，2026-10-23 20:17）
- 起跑前无批证据（**用 ps 而非 pgrep**）: `ps -eo pid,lstart,cmd | grep "[o]rchestration run"` → 仅命中检查命令自身；`systemctl --state=running | grep -iE "t271|d12|r10e2e|f2b"` → 空
- 本批 `run_batch.sh` 已含 `${OUT_ABS:-…}` 修复 ⇒ `run_batch.rc` / `run_batch.end` 应落**本目录**
