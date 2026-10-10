import pathlib
import sys

# 使 `import engine` 在从任意目录运行 pytest 时可用
_ROOT = pathlib.Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
