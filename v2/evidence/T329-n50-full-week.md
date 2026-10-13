# T329 · N=50×84 mock 【实跑】—— 把"外推"换成"实测"

**日期** 2026-10-13 · **作者** kernel-dev · **sha `a05d042`**（运行树）· **性质** 只读实测（未改 `code/`）
**口径**：**mock（非真 LLM）· 非证据级（参考值）**；`N50_VEC=0`；`ulimit -v 16G`；独立进程；`/usr/bin/time -v` 采 peak RSS；显式 `side_root=/tmp/t329_side`（便于计 inode/文件数）。

## 0. 结论（先给）

- ⭐ **跑完了，未碎**：**N=50×84 单核 mock 实跑 21.5 分钟（run=1289.4s；wall=25:20.9），84 回合跑满**，events **1,941,003**，`unknown_event_types=[]`。
- **实测 ≈ 外推**：T324 外推 **≈21.5min/周** ⇒ **实测 run 1289.4s = 21.5min** ✓（外推成立）。
- **内存**：peak RSS **2,851,832 KB ≈ 2.72 GiB**（< 16G 上限，未触；但**随回合增长**，24 回合看不到）。
- **side inode**：文件 **13,600**（55 MB），`df -i` free 起点 5,369,011 → 终点 5,355,218（**−13,793**）。
- ⇒ **R1（N=50 CPU 墙）当前答案**：**单核 ~21.5min/周可完成**；瓶颈仍是 **计算**（非内存/inode）。

## 1. 实测数（命令见 §3）

| 量 | 实测 |
|---|---|
| run 秒 | **1289.37** |
| wall（含启动/收尾） | 25:20.93 |
| **peak RSS** | **2,851,832 KB ≈ 2.72 GiB** |
| events | 1,941,003 |
| 回合 | **84（跑满）** |
| `unknown_event_types` | `[]` |
| side 文件数（终） | **13,600**（55 MB） |
| `df -i /tmp` free | before 5,369,011 → after 5,355,218（**−13,793**）|
| `available`（跑中） | ≥6G（未触 16G cap）|

## 2. 与 T324【外推】/ T223·T254【旧读数】对照

| 维度 | T324 外推（未实测） | **T329 实测** | 判定 |
|---|---|---|---|
| N=50×84 时间 | ≈21.5 min（外推） | **21.5 min（1289s）** | **外推≈实测** ✓ |
| peak RSS | 未覆盖 | **2.72 GiB** | 随回合增长（24 回合时 824MB）|
| side inode/文件 | 未覆盖 | **13,600**（inode −13,793） | 见下对比 |

| 维度 | T223/T254（去全扫前） | **T329（now）** | 变化来源 |
|---|---|---|---|
| N=50×84 可完成性 | **否（>66min 未完成）** | **是（21.5min）** | 去全扫（T264/T295/T312/T330/T328③）|
| **side 文件数（N=50×84）** | **298,725** | **13,600** | ⭐ **T268 内容寻址去重**（`side://src/<sha>` 同内容合一）+ vec=0 ⇒ 文件数大降（**≈22×**）|
| `MEMORY_WRITE` 超线性 | ≈O(N²)（pairwise） | 事件 1.94M（≈O(N²)，未变） | **未变**（life 语义老账）|

> ⭐ **两点新事实**：① **内存随回合显著增长**（824MB@24r → 2.72GiB@84r，**24 回合看不到**，印证"外推最易在内存失效"）；② **side 文件数因 T268 内容寻址已大幅下降**（旧 298,725 → 13,600），**当初 T223 的 inode 焦虑显著缓解**。

## 3. 复现

```bash
cd social-experiment/code && export N50_VEC=0 && ulimit -v 16777216
SD=/tmp/t329_side; rm -rf "$SD"; mkdir -p "$SD"
/usr/bin/time -v python -c "from orchestration.integration import run_e2e; r=run_e2e(seed=42,rounds=84,n=50,side_root='$SD',cleanup_side=False); print(r['events'], r['seconds'], r['unknown_event_types'])"
find "$SD" -type f | wc -l ; df -i /tmp | tail -1
```
起始 `df -i` free 5,369,011；`/tmp/t329.log` 有 START/END。

## 4. 边界（诚实）

- **mock、非证据级**；**单核串行**（未接 M4 并发）；**未测真 LLM**。
- 时间读数**受宿主并发**影响（本次开跑前后已确认无批/无重活；`available` 22G）。
- `side` 文件数受 `N50_VEC=0`（不落 `.vec`）影响 ⇒ **进制不同时不可直接比**；与 T223 比时**同为 vec=0**。
