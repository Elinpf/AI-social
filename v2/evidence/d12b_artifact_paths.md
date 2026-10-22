# D12-B 两臂留痕位置（§6-③，起跑前写死）

| 项 | 路径 |
|---|---|
| OFF 臂日志 | `v2/evidence/run_d12b_off_seed7_n16r24/run.jsonl` |
| OFF 臂 `switch_proof.txt` | `v2/evidence/run_d12b_off_seed7_n16r24/switch_proof.txt`（**`printenv HITT_D12_PREFWORD` 真值 = `<unset>`**） |
| OFF 臂 `arm_state_check.txt` | `v2/evidence/run_d12b_off_seed7_n16r24/arm_state_check.txt` |
| ON 臂日志 | `v2/evidence/run_d12b_on_seed7_n16r24/run.jsonl` |
| ON 臂 `switch_proof.txt` | `v2/evidence/run_d12b_on_seed7_n16r24/switch_proof.txt`（**真值 = `1`**） |
| ON 臂 `arm_state_check.txt` | `v2/evidence/run_d12b_on_seed7_n16r24/arm_state_check.txt` |
| 句首熵判定输出 | `v2/evidence/d12b_onset_entropy.txt`（`--compare` 的 stdout） |
| 具体性判定输出 | `v2/evidence/d12b_detail_proxy.txt`（两臂 `--run` 的 stdout） |

**`switch_proof.txt` 必含字段**（用 `printenv` 真值，不许写字面量）：
```
unit=<systemd unit>
code_sha=<git -C <worktree> rev-parse --short HEAD>
env_HITT_D12_PREFWORD=<printenv 真值 或 <unset>>
env_HITT_LLM_PROVIDER=<printenv 真值>
params seed=7 n=16 rounds=24
prompt_fn_sha256=<OFF/ON 各自的 dialogue_prompt_sha256>
```

**起跑 60 秒自检（两臂都要，FAIL 即停）**：
```bash
python3 tools/d9/arm_state_check.py --run <arm>/run.jsonl \
  --tree-expectation '{"paren_rate":0.78,"len_p50":47}' \
  --expect-struct '{"msgs":191,"threads":66,"ge3":28}' \
  --expect-provider openai_compat | tee <arm>/arm_state_check.txt
```
- **OFF 臂 `paren_rate` 若 ≈0（而非 ≈0.78）⇒ 跑错树 ⇒ 立即停跑**。
