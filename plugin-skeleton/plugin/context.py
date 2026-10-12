"""插件运行时核心：Context / Fiber / Effect / 类型化事件 / 声明式注入（零业务依赖）。"""
from __future__ import annotations

from typing import Any, Callable, Iterable

_MISSING = object()


class PluginError(Exception):
    """插件系统通用错误。"""


class ServiceNotFound(PluginError):
    """请求的服务未提供。"""


class Effect:
    """一次可逆副作用：持有 `undo` 回调，`dispose()` 幂等。"""

    __slots__ = ("_undo", "_disposed")

    def __init__(self, undo: Callable[[], None]):
        self._undo = undo or (lambda: None)
        self._disposed = False

    @property
    def disposed(self) -> bool:
        return self._disposed

    def dispose(self) -> None:
        if not self._disposed:
            self._disposed = True
            self._undo()


class Fiber:
    """一个插件实例的生命周期状态机（PENDING -> LOADING -> ACTIVE -> DISPOSED）。

    持该插件作用域内注册的**全部副作用**；`dispose()` **逆序**撤销，保证可逆注册。
    """

    PENDING = "PENDING"
    LOADING = "LOADING"
    ACTIVE = "ACTIVE"
    DISPOSED = "DISPOSED"

    def __init__(self, name: str):
        self.name = name
        self.state = self.PENDING
        self.effects: list[Effect] = []

    def add(self, eff: Effect) -> None:
        if self.state == self.DISPOSED:
            eff.dispose()          # 已卸载：新注册立即撤销（不泄漏）
        else:
            self.effects.append(eff)

    def dispose(self) -> None:
        self.state = self.DISPOSED
        for eff in reversed(self.effects):   # 逆序撤销
            eff.dispose()
        self.effects.clear()


class Context:
    """插件上下文 = 「副作用插座」。根 Context 持全局服务/监听器注册表。"""

    def __init__(self, parent: "Context | None" = None, *, name: str = "root"):
        self.parent = parent
        self.name = name
        self.root: Context = parent.root if parent is not None else self
        self._fiber: Fiber | None = None      # 非 None 表示这是一个插件作用域
        self._listeners: dict[str, list[list]] = {}   # event -> [[owner, handler]]
        if parent is None:
            self._services: dict[str, list] = {}       # name -> [value, owner_ctx]
            self._waiters: dict[str, list[Callable]] = {}   # service -> [apply callbacks]
            self._dependents: dict[str, list[dict]] = {}    # service -> [plugin records]
            self._plugins: list[dict] = []

    # ---------- 可逆副作用 ----------
    def _track(self, eff: Effect) -> Effect:
        if self._fiber is not None:
            self._fiber.add(eff)
        return eff

    def effect(self, setup: Callable[[], Callable[[], None] | None]) -> Effect:
        """注册一个可逆副作用：`setup()` 返回 `undo`；卸载时自动撤销。"""
        undo = setup()
        return self._track(Effect(undo))

    # ---------- 服务注入 ----------
    def provide(self, name: str, value: Any) -> Effect:
        """在本作用域提供一个命名服务；卸载时撤销。"""
        if name in self.root._services:
            raise PluginError(f"服务 {name!r} 已被提供，不能重复 provide")
        owner = self
        self.root._services[name] = [value, owner]
        eff = self._track(Effect(lambda: self._withdraw(name, value)))

        def wake():
            for cb in list(self.root._waiters.pop(name, [])):
                cb()
        eff2 = Effect(wake)
        if self._fiber is not None:
            self._fiber.add(eff2)
        wake()
        return eff

    def _withdraw(self, name: str, value: Any) -> None:
        cur = self.root._services.get(name)
        if cur is not None and cur[0] is value:
            del self.root._services[name]
        for rec in list(self.root._dependents.get(name, [])):
            rec["fiber"].dispose()              # 依赖方卸载（撤销其全部副作用）
            rec["fiber"].state = Fiber.PENDING  # 允许重新 apply
            rec["apply"]()                      # 重新进入等待（服务回来时再 apply）

    def get(self, name: str, default: Any = _MISSING) -> Any:
        cur = self.root._services.get(name)
        if cur is not None:
            return cur[0]
        if default is not _MISSING:
            return default
        raise ServiceNotFound(f"服务 {name!r} 未提供")

    # ---------- 类型化事件 ----------
    def on(self, event: str, handler: Callable) -> Effect:
        self.root._listeners.setdefault(event, []).append([self, handler])

        def undo():
            lst = self.root._listeners.get(event, [])
            lst[:] = [(o, h) for (o, h) in lst if not (o is self and h is handler)]
        return self._track(Effect(undo))

    def emit(self, event: str, *args: Any) -> list:
        out = []
        for _owner, handler in list(self.root._listeners.get(event, [])):
            out.append(handler(*args))
        return out

    def waterfall(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """around-middleware：handler(next, *args)；不调 next() 即短路。"""
        handlers = [h for _o, h in self.root._listeners.get(event, [])]

        def run(i: int):
            if i >= len(handlers):
                return kwargs.get("default")
            return handlers[i](lambda *a: run(i + 1), *args)
        return run(0)

    # ---------- 挂载插件 ----------
    def plugin(self, fn: Callable, config: Any = None, *, name: str | None = None) -> dict:
        pname = name or getattr(fn, "name", None) or getattr(fn, "__name__", "plugin")
        child = Context(self, name=pname)
        fiber = Fiber(pname)
        child._fiber = fiber
        rec = {"id": pname, "name": pname, "fn": fn, "config": config, "ctx": child, "fiber": fiber}
        self.root._plugins.append(rec)
        need = list(getattr(fn, "inject", []) or [])
        for s in need:
            self.root._dependents.setdefault(s, []).append(rec)

        def apply():
            if fiber.state == Fiber.ACTIVE:
                return
            missing = [s for s in need if s not in self.root._services]
            if missing:
                fiber.state = Fiber.PENDING
                for s in missing:
                    self.root._waiters.setdefault(s, []).append(apply)
                return
            fiber.state = Fiber.LOADING
            fn(child, config)
            fiber.state = Fiber.ACTIVE

        rec["apply"] = apply
        apply()
        return rec

    def dispose(self) -> None:
        """卸载本作用域挂载的所有插件（逆序）与其自身副作用。"""
        for rec in reversed(list(self.root._plugins)):
            if rec["ctx"] is self or rec["ctx"].parent is self:
                rec["fiber"].dispose()
        if self._fiber is not None:
            self._fiber.dispose()

    def plugins(self) -> list[dict]:
        return list(self.root._plugins)

    def services(self) -> dict:
        return {k: v[0] for k, v in self.root._services.items()}
