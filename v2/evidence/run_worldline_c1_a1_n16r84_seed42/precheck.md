# C-1 前置核查（强制第 0 步）· 开关 LIFE_PROMPT_WORLD_C1 是否存在并接线

> 核查人：batch-runner（跑批托管与验真专家）
> 核查时刻：2026-10-22（本机时钟）
> 核查对象：**ctrl 臂实际跑的那份代码** —— worktree `.worktrees/worldline-c1-n16r84`，分支 `feat/world-line-c1`，code_sha `af1dffc61040adc97c828b4927ac3935dbef2d1b`（= ctrl `host.log` 里 `code_sha=` 的那一个）
> 性质：只读核查（grep/sed/pytest/import），未改动 `code/` 下任何文件。

## 0. 结论（先给判读）

**开关存在且已接线 ⇒ a1 臂成立，可以起跑。**

- 读取点：`code/life/agent.py:108`（`world_c1_enabled()` 读 `os.environ["LIFE_PROMPT_WORLD_C1"]`）。
- 唯一的**门控点**：`code/life/agent.py:1278` `if wv is None or not world_c1_enabled(): return ""` —— 关闭时返回空串 ⇒ 提示词拼接串与接入前逐字节一致。
- 插入点：`code/life/agent.py:1457`（`_dialogue_prompt`）与 `1475`（`_reply_prompt`）。
- ctrl `host.log` 里的 `LIFE_PROMPT_WORLD_C1=UNSET（变量不存在）` **指的是「环境变量没设」，不是「代码里没这个开关」** —— 这句容易误读成「开关不存在」，本次核查正是为消除这个歧义。
- 影响面：只改**提示词文本**（插入一行处境），不改 config、不写记忆、不发事件、不进 `state_hash`。

## 1. 命令与真实输出

### 1.1 读取点 / 常量定义（git grep，绑定 code_sha）

```bash
cd <REPO>/.worktrees/worldline-c1-n16r84 && git rev-parse HEAD
git grep -n "LIFE_PROMPT_WORLD_C1" -- code/
```

真实输出：

```
af1dffc61040adc97c828b4927ac3935dbef2d1b
code/life/agent.py:76:WORLD_C1_ENV = "LIFE_PROMPT_WORLD_C1"
code/life/agent.py:107:    """C-1 臂开关（env `LIFE_PROMPT_WORLD_C1` ∈ {1,true,yes,on}）；默认关。"""
```

`git grep` rc=0（0=命中=开关在树上可见）。注意 `code/life/agent.py:108` 是真正的 `os.environ.get(WORLD_C1_ENV, "")`，上一行 107 是 docstring，两者合起来才是「读取点」。

### 1.2 开关函数本体（`sed -n '106,108p' code/life/agent.py`）

```python
def world_c1_enabled() -> bool:
    """C-1 臂开关（env `LIFE_PROMPT_WORLD_C1` ∈ {1,true,yes,on}）；默认关。"""
    return os.environ.get(WORLD_C1_ENV, "").strip().lower() in {"1", "true", "yes", "on"}
```

### 1.3 门控点（`sed -n '1278p' code/life/agent.py`）

```python
        if wv is None or not world_c1_enabled():
            return ""
```

⇒ OFF（默认）= 返回空串；ON = 才可能拼出内容。**开关是这段逻辑的唯一闸门**。

### 1.4 插入点（`grep -n "_world_line" code/life/agent.py`）

真实输出：

```
1256:    def _world_line(self, wv) -> str:
1457:                + self._world_line(wv)       # C-1 臂：眼下场所+镇上的事（默认OFF ⇒ 空串）
1475:                + self._world_line(wv)       # C-1 臂：眼下场所+镇上的事（默认OFF ⇒ 空串）
```

`sed -n '1450,1480p'` 确认 1457 在 `_dialogue_prompt`（发起）里、1475 在 `_reply_prompt`（回复）里 —— **两个对话提示词都接上了**，不是死代码。

### 1.5 开了会改什么（`sed -n '1256,1322p' code/life/agent.py` 逻辑归纳）

`_world_line(wv)` 打开后返回 `"\n" + "；".join(bits) + "。（用自己的话顺口带一句，不要照抄这句的措辞。）"`，`bits` 只取三处**已有**字段：

| 来源 | 条件 | 例（`WORLD_C1_KIND_ZH` 映射） |
|---|---|---|
| `wv.location` + `config/places.json::name_cn` | 有地点 | `你眼下在集市` |
| `wv.visible_events` 中 `WORLD_GROUP_EVENT`/`WORLD_DIRECTIVE` | `payload.directed=True` 且 `[start_round,end_round)` 覆盖当前回合且 `now-start ≤ 24`（`WORLD_C1_WINDOW_ROUNDS`）；最多 2 种（`WORLD_C1_MAX_EVENTS`） | `镇上气氛有点紧`（kind=tension） |
| `_wp_last["market_scarcity_bp"]["global"]` | ≥ 1000 bp（`WORLD_C1_SCARCITY_MIN_BP`） | `集市上东西有点紧俏` |

- 不新增 config 键、不改 engine/orchestration、不写记忆、不发事件、不进 `state_hash`（文件头 70-75 行注释明写，代码一致）。

### 1.6 单变量行为已由仓内测试覆盖（在 af1dffc 上实跑）

```bash
cd <REPO>/.worktrees/worldline-c1-n16r84/code && \
  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_world_c1_prompt_single_variable.py
```

真实输出：

```
...........                                                              [100%]
11 passed in 0.24s
```

该测试文件自述的断言（`sed -n '1,40p' tests/test_world_c1_prompt_single_variable.py`）：A. OFF 时提示词空、B. ON 时插入、C. 只挑在期 directed 事件、D. 行情行有阈值门。⇒ 「OFF 逐字节不变 / ON 只多一行」这一单变量前提有可复跑的测试兜底。

### 1.7 ctrl 臂 world 事件确实会在跑批中出现（决定 ON 臂是否真有内容可插）

```bash
cd <REPO> && python3 - <<'PY'   # 统计 ctrl run.jsonl 里的世界事件
...
PY
```

真实输出（节选）：

```
lines: 194057
=== world events: 2
  WORLD_DIRECTIVE round=30 {'kind':'tension','directed':True,'effective_from_round':30,'expires_round':36}
  WORLD_GROUP_EVENT round=30 {'kind':'tension','directed':True,'start_round':30,'end_round':36}
```

⇒ 全 84 回合只有 round 30 起了 1 组 tension 世界事件（窗口 30–35）。所以 a1 臂的「镇上的事」一句**只在 rounds 30–35 有机会出现**；其余回合 ON 臂的差异主要体现在「你眼下在X」这一句。这是**预期内的剂量下限**，如实记录，后期报告不得夸大「世界事件进对话」的覆盖面。

### 1.8 前置环境（起跑可行性）

```bash
systemd-run --version                       # systemd 255 (255.4-1ubuntu8.18)，rc=0
ps -p 1 -o comm=                            # systemd
systemd-run --unit=probe-$$ --wait --pipe /bin/echo systemd-run-ok
pgrep -af "[o]rchestration run"             # 无命中，rc=1
```

真实输出：

```
systemd 255 (255.4-1ubuntu8.18) ... rc=0
systemd
Running as unit: probe-867395.service; invocation ID: 093e186355954f7fadace84a5eb3cb82
systemd-run-ok
Finished with result: success
rc=0
pgrep_rc=1
```

⇒ **交接手册 B1（systemd-run 未验证）本次已亲自验证通过**：transient unit 可建、可跑、可回收。串行闸门通过（无并发跑批）。

## 2. 判读与下一步

| 检查项 | 结果 |
|---|---|
| 开关名 | `LIFE_PROMPT_WORLD_C1`（`code/life/agent.py:76`） |
| 读取点 | `code/life/agent.py:108`（`world_c1_enabled()`） |
| 门控点 | `code/life/agent.py:1278` |
| 插入点 | `code/life/agent.py:1457` / `1475`（发起 + 回复两个提示词） |
| 行为差异 | 仅提示词插入一行处境（地点 / 在期世界事件 / 行情紧俏），零 config / 零事件 / 零 state_hash 影响 |
| 单变量测试 | 11 passed（`tests/test_world_c1_prompt_single_variable.py`） |
| systemd-run | 可用（已亲测） |
| 并发跑批 | 无（pgrep rc=1） |

**⇒ 走任务第 1 步（起跑 a1 臂）。** 代码完全复用 ctrl 臂同一 worktree / 同一 code_sha `af1dffc`，只把 `LIFE_PROMPT_WORLD_C1` 从「不存在」改成 `1`。
