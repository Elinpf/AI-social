import sys, os, re
# 判定"该 sha 是否已被标注"。核心：**标注属于离它最近的 token**，不靠固定窗口。
line = sys.stdin.readline().rstrip("\n")
tok = os.environ.get("TOK", ""); ANN = os.environ.get("ANN", "")
if not tok: print(0); sys.exit(0)
i = line.find(tok)
if i < 0: print(0); sys.exit(0)
end = i + len(tok)

def spans():
    return [(m.start(), m.end()) for m in re.finditer(r"[0-9a-f]{7,}", line)]

def inside_any_bracket(pos):
    # 该位置是否落在某个（…）里
    for m in re.finditer(r"[（(][^）)]*[）)]", line):
        if m.start() < pos < m.end(): return True
    return False

def nearest_token(pos):
    best = None
    for s, e in spans():
        d = 0 if s <= pos <= e else min(abs(pos - s), abs(pos - e))
        if best is None or d < best[0]: best = (d, s, e)
    return best

# A) 紧跟 token 后 8 字内开始的括号：里面的标注算这个 token 的
after = line[end:]
if re.search(r"[（(]", after[:8]):
    m = re.search(r"[（(]([^）)]*)[）)]", after)
    if m and not re.search(r"[0-9a-f]{7,}", m.group(1)) and re.search(ANN, m.group(1)):
        print(1); sys.exit(0)

# B) token 之前的标注词：必须 ①不在任何括号里 ②离本 token 最近
for m in re.finditer(ANN, line[:i]):
    p = m.start()
    # 归属只由"最近 token"决定：邻接 sha 的括号（如 `bad（历史版）与 78ec…`）其最近 token 是邻接那个，
    # 因此不会辐射；而长句括号里的标注仍可归属本 token（不能用"是否在括号内"一刀切）。
    nt = nearest_token(p)
    if nt and nt[1] == i:            # 最近的 token 就是本 token
        print(1); sys.exit(0)
print(0)
