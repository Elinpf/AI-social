#!/usr/bin/env python3
"""check_tables.py —— 确定性检查 §11/§12 的两张必填表（查表，不查词）

由来：repro-verifier 2026-11-01 实测——关键词扫描无法区分"使用某词"与"讨论某词"
（反证：一句"判读改为实测倍率，不要外推"被判成"缺外推假定"），精确率仅 10–20%，
属结构性缺陷，调正则救不了。故改为**结构强制**：预登记必须含两张表，检查器只验
"表在不在 + 必填列是否为空"。这一步是确定性的，100% 精确。

用法：
  check_tables.py <file> [--strict]
  check_tables.py --selftest
"""
import re, sys, os, subprocess

REQ = {
    "率的定义": ["率名", "分子", "分母", "计算式", "纳入排除"],
    "外推与假定": ["外推式", "假定不变的量", "值来源"],
}

def find_table(lines, heading_kw):
    """找到含 heading_kw 的标题行，返回其后的 markdown 表格行"""
    for i, l in enumerate(lines):
        if l.strip().startswith("#") and heading_kw in l:
            j = i + 1
            tbl = []
            while j < len(lines):
                s = lines[j]
                if s.strip().startswith("#"):
                    break
                if s.strip().startswith("|"):
                    tbl.append((j + 1, s))
                j += 1
            return tbl
    return None

def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]

def check(path, strict=False):
    lines = open(path, encoding="utf-8").read().split("\n")
    bad = 0
    for name, cols in REQ.items():
        tbl = find_table(lines, name)
        if tbl is None:
            print(f"  MISS-TABLE  「## {name}」表不存在"); bad += 1; continue
        if len(tbl) < 2:
            print(f"  MISS-TABLE  「{name}」表只有 {len(tbl)} 行（需表头+至少 1 行）"); bad += 1; continue
        hdr_ln, hdr = tbl[0]
        hcells = cells(hdr)
        missing = [c for c in cols if not any(c in h for h in hcells)]
        if missing:
            print(f"  MISS-COL    「{name}」表头 L{hdr_ln} 缺列：{missing}"); bad += 1
        # 数据行（跳过 |---|）
        for ln, row in tbl[1:]:
            if set(row.strip()) <= set("|-: "):
                continue
            rc = cells(row)
            idx = [i for i, h in enumerate(hcells)]
            empties = []
            for c in cols:
                pos = next((i for i, h in enumerate(hcells) if c in h), None)
                if pos is None: continue
                if pos >= len(rc) or not rc[pos]:
                    empties.append(c)
            if empties:
                print(f"  EMPTY-CELL  「{name}」L{ln} 空列：{empties}"); bad += 1
    print(f"== 缺项合计 {bad} ==")
    if bad and strict:
        print("结论: HAS_MISSING(strict)"); return 1
    print("结论: " + ("ALL_TABLES_OK" if not bad else "MISSING(non-strict)"))
    return 0

def selftest():
    import tempfile
    rc = 0
    # 夹具1：两张表都缺
    t1 = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    t1.write("# 件\n\n没有任何表\n"); t1.close()
    out = subprocess.run([sys.executable, __file__, t1.name, "--strict"], capture_output=True, text=True)
    n = out.stdout.count("MISS-TABLE")
    print(f"selftest①  两张表缺 → 抓到 {n}（期望 2），rc={out.returncode}")
    rc |= 0 if (n == 2 and out.returncode == 1) else 1
    # 夹具2：表在但有空格
    t2 = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    t2.write("# 件\n\n## 率的定义\n| 率名 | 分子 | 分母 | 计算式 | 纳入排除 |\n|---|---|---|---|---|\n"
             "| gap率 | 48 | 125 | a/b | 排除 residence |\n"
             "| 空行示例 |  | 125 | a/b | 排除 residence |\n\n"
             "## 外推与假定\n| 外推式 | 假定不变的量 | 值来源 |\n|---|---|---|\n| ×4 | places | 配置 |\n")
    t2.close()
    out2 = subprocess.run([sys.executable, __file__, t2.name, "--strict"], capture_output=True, text=True)
    n2 = out2.stdout.count("EMPTY-CELL")
    print(f"selftest②  有空格 → 抓到 {n2}（期望 1），rc={out2.returncode}")
    rc |= 0 if (n2 == 1 and out2.returncode == 1) else 1
    os.unlink(t1.name); os.unlink(t2.name)
    print("selftest " + ("PASS" if rc == 0 else "FAIL"))
    return rc

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if len(sys.argv) < 2:
        print("用法: check_tables.py <file> [--strict] [--selftest]", file=sys.stderr); sys.exit(2)
    try:
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    except Exception:
        root = ""
    if not root:
        print("FATAL: 不在 git 仓库内", file=sys.stderr); sys.exit(4)
    print(f"== 执行上下文 repo={root} file={sys.argv[1]} ==")
    sys.exit(check(sys.argv[1], "--strict" in sys.argv))
