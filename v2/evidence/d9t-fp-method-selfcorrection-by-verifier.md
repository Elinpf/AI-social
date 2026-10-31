# 自我更正：我提的 `FP` 指纹法有洞 —— **路径错/目录空也会给出"稳定指纹"，前后比对会假通过**

> 作者：`repro-verifier`｜2026-10-31｜只读；未改代码、未跑批、未 push
> `origin/master = 5159cf6d244dcaef…`（§9.8 已收我 `FP` 做法）
> **本件是自我更正：我上一件提供的方法本身有缺陷，跑批前必须补一道校验。**

## 0. 一句话

我的 `FP` 命令在**路径写错 / 目录为空**时**不报错**，而是输出一个**稳定但无意义**的指纹（`abcfa6a9…`，rc=0）⇒ 跑批前后两次都取这个值 ⇒ `diff` 相等 ⇒ 报 `CODE_UNCHANGED` **假通过**。
**这正是我们这轮消灭的第 5 个同族问题：结果看起来正常，但来源不是你以为的那个。**

## 1. 实测证据

```
# 正常工作区（master）文件数
$ find code/life code/orchestration code/config code/engine -type f \( -name '*.py' -o -name '*.json' \) | wc -l
121

# 在"没有 code/ 目录"的 /tmp/emptydir 里跑同一条命令
$ cd /tmp/emptydir && find code/life -type f -print0 2>/dev/null | sort -z | xargs -0 sha256sum 2>/dev/null | sha256sum
abcfa6a9d4df344d1781bc2560b5e4cdcae08b39ed303063535e7e1e926a304a  -     ← 稳定值，rc=0
# 再跑一次仍是 abcfa6a9…（确定性成立，但这正是危险处：它稳定 ⇒ 前后比对必"相等"）
```
⇒ **错路径也能给出"指纹"**，`find` 的报错被 `2>/dev/null` 吃掉，`xargs` 空输入不执行，末端 `sha256sum` 仍算出确定值、`rc=0`。

## 2. 修法：先数文件，低于阈值直接 FATAL

```bash
FP() {
  local dirs="code/life code/orchestration code/config code/engine" n
  n=$(find $dirs -type f \( -name '*.py' -o -name '*.json' \) 2>/dev/null | wc -l)
  [ "$n" -ge 100 ] || { echo "FATAL: FP 只找到 $n 个文件（期望 ≥100）——路径错或不在跑批那份代码上" >&2; return 3; }
  find $dirs -type f \( -name '*.py' -o -name '*.json' \) -print0 | sort -z | xargs -0 sha256sum | sha256sum
}
```
- **阈值依据（实测，非拍脑袋）**：当前 master 工作区 **121** 个；`cef1c58` 那份只多不少（多了 `test_life_narration_openings.py`）⇒ 取 **≥100** 有安全余量。
- **判据一句话**：**指纹之前先证明"我数到了东西"** —— 与 `check_citations.sh` 里"先断言 `_ann.py` 存在"、`push_and_verify.sh` 里"先验 `EXPECT`"是同一形态：**前置条件不满足时，后面的检查全部作废，不能静默给结论。**

## 3. 这条对应到 §9.8 的两条前提，要加第三条

§9.8 现有：
①必须在跑批实际使用的那份代码上取（ON=`cef1c58`）—— **与 B-1 同族：比较对象错**；
②指纹变了就报"代码被动过"，不得解释成"无害改动"。
**建议加第三条**：
> ③ **取指纹前必须先证明"数到了文件"**（文件数低于阈值 ⇒ FATAL，不得输出指纹）。
> 否则"在错目录取指纹"会得到稳定值，前后比对必相等 ⇒ **假通过**，而它长得和真通过一模一样。

**三条合起来才闭环**：①保证比的是对的对象 ②保证变了会报 ③保证"什么都没比到"不会被当成"没变"。

## 4. 我做了什么 / 没做什么

- **做了**：`FP` 命令确定性检验（三次同值 ✓）；**空/错路径下的行为实测**（得到稳定假指纹）；当前工作区文件数（121）作为阈值依据；给出补丁版 `FP`。
- **没做**：不改清单（`v2/refs/**` 归 Leader）、不 push、不跑批。
- **待命**：L2/L3 卡随时可接 —— **请用 §2 的补丁版 `FP`**，我核验时也会用它。
