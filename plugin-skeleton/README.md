# Python 插件化最小骨架（T214 验证件 · 独立于 `code/`）

借 Cordis 五概念的 Python 落地。**零业务依赖（仅 stdlib）**，可作为「可复用到其他项目」的种子。

## 结构
```
plugin-skeleton/
├── plugin/
│   ├── __init__.py     # 对外导出
│   ├── context.py      # Context/Fiber/Effect + 服务注入 + 类型化事件（可逆副作用核心）
│   ├── config.py       # 配置组合（layered patch / overlay）
│   └── manifest.py     # 插件清单 + 稳定指纹
├── tests/test_plugin_arch.py   # 11 条行为测试
└── conftest.py
```

## 五概念 → 落地映射
| Cordis 概念 | 本骨架 | 关键行为 |
|---|---|---|
| 可逆副作用 effect/dispose | `Context.effect(setup)` + `Fiber.dispose()` | 卸载时**逆序**撤销；卸载后再注册**立即撤销**（不泄漏） |
| 服务注入 inject | `Context.provide()/get()` + 函数插件 `.inject=[...]` | 依赖未满足则**等待**；服务消失→依赖方**自动卸载**；服务回来→**自愈重挂** |
| 类型化事件 emit/waterfall | `Context.on()/emit()/waterfall()` | waterfall = around-middleware，不调 `next()` 即**短路** |
| 配置组合 layered patch | `plugin.compose(base, *overlays)` | 按 id **整体替换** config / `insert` 追加；不改入参 |
| 插件清单/版本 | `plugin.describe()` + `fingerprint()` | 稳定 `sha256:` 指纹，供「证据绑版本」 |

## 运行验证
```sh
cd plugin-skeleton
python3 -m pytest tests -q        # 期望：11 passed
```

## 说明（与 T214 约束的关系）
- 本目录**不修改 `code/` 语义**，也**未改 `code/.importlinter`**（边界契约的落地以 `v2/refs/python-plugin-architecture.md` §建议 形式提出，待 Leader 排队后由单一修改者落地）。
- 直接 `git` 提交本目录不影响 `code/` 与现有门禁。
