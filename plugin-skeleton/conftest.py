import pathlib
import sys

# 使 `import plugin` 在任意目录运行 pytest 时可用（骨架自成一体）
_ROOT = pathlib.Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
