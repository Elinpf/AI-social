import sys, os, re
line = sys.stdin.readline().rstrip("\n")
tok = os.environ.get("TOK", ""); ANN = os.environ.get("ANN", "")
i = line.find(tok)
if i < 0:
    print(0); sys.exit(0)
after = line[i+len(tok):]
pre = line[max(0, i-14):i]
def other_sha(s, exclude=tok):
    for m in re.finditer(r"[0-9a-f]{7,}", s):
        if m.group(0) != exclude:
            return True
    return False
# A. 紧跟在该 sha 后的括号里：合法（括号内不得含别的 sha ⇒ 防辐射）
if re.search(r"[（(]", after[:8]):
    m = re.search(r"[（(]([^）)]*)[）)]", after)
    if m and not other_sha(m.group(1)) and re.search(ANN, m.group(1)):
        print(1); sys.exit(0)
# B. 紧贴在该 sha 之前的名词性标注（前 14 字内，且中间没有别的 sha）
if not other_sha(pre) and re.search(ANN, pre):
    print(1); sys.exit(0)
print(0)
