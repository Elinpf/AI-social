# D12-D 三态接线证明（T0/T1/T2）

> 作者：`prompt-linguist` ｜ 2026-10-23 08:28 ｜ 分支 **`feat/d12c-dedup` @ `5ca515d`**（parent `feat/d12c-specific@a977cb0`）
> 渲染脚本：`tools/d12d/render_d12d_prompt.py`（固定输入：`build_world(seed=42,n=2)` 的 P001、`template=gift`、单条 reply history）

## 1. 三态 `prompt_fn_sha256`

| 态 | env | `prompt_fn_sha256` | 期望 |
|---|---|---|---|
| **T0** | 无 | `5cf08593d562dc09fdd42ab289319a819481c4882701407b039fa514ff8293f7` | **与 D12-C 的 T0 逐字相等 ✅** |
| **T1** | `LIFE_PROMPT_D12C_SPECIFIC=1` | `effc14dbffdb6865aa52d9d8adab9db269ab3b92ae9a1a230a22cab6c0ed73f5` | **与 D12-C 的 T1 逐字相等 ✅** |
| **T2** | `=1` + `LIFE_PROMPT_D12C_DEDUP=1` | `ca61423cb60c3be5a500df7f1de0aeb691f65e68a4b417be0817f726315e51cf` | **新值，且 ≠ T1 ✅** |

⇒ **前两态逐字复现** ⇒ 接线未污染；T2 为新增两行的净效果。

## 2. 渲染文本 sha 与 diff

| 文件 | sha256 |
|---|---|
| `v2/evidence/d12d_prompt_render_T0.txt` | `d2dbd57cf99a23da91464e077b5d559cd14f8e8d461bebf043fe43ceddb94e32` |
| `v2/evidence/d12d_prompt_render_T1.txt` | `14065646acdc52b2c83dac5ad4915194bb452454849ba18e9ecdc12d7f28dc2d` |
| `v2/evidence/d12d_prompt_render_T2.txt` | `b0b33befc8fab320153ef17be8aa99eeda8c0d7fce51312d5d24bd65bb9b55df` |

- **T0→T1 diff**：`v2/evidence/d12d_prompt_render_T0_T1.diff` —— 只多 D12-C 两行 × 两处；
- **T1→T2 diff**：`v2/evidence/d12d_prompt_render_T1_T2.diff` —— 只多 D12-D 两行 × 两处：
```
+这回换个新的：要是你们刚提过某件器物或某个数，就换一件别的（刚说秤砣，就改说药碾子）。
+开口别用你上一句或对方上一句的前四个字，换个起法。
```

## 3. 代码改动范围（单变量）

`git diff --numstat a977cb0 feat/d12c-dedup`：
- `code/life/agent.py`：**只新增** `_D12D_ENV = "LIFE_PROMPT_D12C_DEDUP"`、`_d12d_on()`、`_d12d_lines()`，并在两个 prompt 末尾各**追加** `+ self._d12d_lines()`（无既有行被改）
- `tools/d12d/render_d12d_prompt.py`：**新增**渲染脚本

## 4. 复现命令

```bash
git archive feat/d12c-dedup | tar -x -C /tmp/t271-d12d-br
cd /tmp/t271-d12d-br/code && export PYTHONPATH=$PWD
env -u LIFE_PROMPT_D12C_SPECIFIC -u LIFE_PROMPT_D12C_DEDUP python3 ../tools/d12d/render_d12d_prompt.py   # T0
env -u LIFE_PROMPT_D12C_DEDUP LIFE_PROMPT_D12C_SPECIFIC=1 python3 ../tools/d12d/render_d12d_prompt.py    # T1
env LIFE_PROMPT_D12C_SPECIFIC=1 LIFE_PROMPT_D12C_DEDUP=1 python3 ../tools/d12d/render_d12d_prompt.py     # T2
```
