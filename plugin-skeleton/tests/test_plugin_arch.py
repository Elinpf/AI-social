"""T214 · Python 插件运行时骨架测试（可逆副作用 / 服务注入 / 类型化事件 / 配置组合 / 清单）。"""
from __future__ import annotations

from plugin import Context, Fiber, compose, describe, fingerprint


# ---------- 1. 可逆副作用（effect/dispose） ----------
def test_effect_revoked_on_dispose():
    trace = []
    ctx = Context()

    def p(ctx_, cfg):
        ctx_.effect(lambda: (trace.append("acquired"), lambda: trace.append("disposed"))[1])
    ctx.plugin(p, name="p")
    assert trace == ["acquired"]
    ctx.dispose()
    assert trace == ["acquired", "disposed"]


def test_effects_revoked_in_reverse_order():
    order = []
    ctx = Context()

    def p(ctx_, cfg):
        ctx_.effect(lambda: (order.append("A"), lambda: order.append("~A"))[1])
        ctx_.effect(lambda: (order.append("B"), lambda: order.append("~B"))[1])
    ctx.plugin(p, name="p")
    ctx.dispose()
    assert order == ["A", "B", "~B", "~A"]      # 逆序撤销


def test_no_leak_when_registering_after_dispose():
    ctx = Context()

    def p(ctx_, cfg):
        ctx_.effect(lambda: lambda: None)
    rec = ctx.plugin(p, name="p")
    rec["fiber"].dispose()
    eff = rec["ctx"].effect(lambda: lambda: None)   # 已卸载后再注册
    assert eff.disposed is True                     # 立即撤销，不泄漏


# ---------- 2. 服务注入（声明式等待 + 消失自愈） ----------
def test_inject_waits_until_service_available():
    events = []
    ctx = Context()

    def consumer(ctx_, cfg):
        events.append("consumer:applied")
        ctx_.get("clock")            # 依赖可用
    consumer.inject = ["clock"]
    rec = ctx.plugin(consumer, name="consumer")
    assert rec["fiber"].state == Fiber.PENDING       # 服务未提供 -> 等待
    assert events == []
    ctx.provide("clock", {"now": 0})                 # 提供后自动 apply
    assert rec["fiber"].state == Fiber.ACTIVE
    assert events == ["consumer:applied"]


def test_dependent_disposed_then_heals_when_service_returns():
    events = []
    ctx = Context()
    served = ctx.provide("clock", {"now": 0})

    def consumer(ctx_, cfg):
        events.append("apply")
        ctx_.effect(lambda: (events.append("acquire"), lambda: events.append("dispose"))[1])
    consumer.inject = ["clock"]
    rec = ctx.plugin(consumer, name="consumer")
    assert events == ["apply", "acquire"]
    served.dispose()                                 # 服务消失
    assert events == ["apply", "acquire", "dispose"]  # 依赖方被卸载
    assert rec["fiber"].state == Fiber.PENDING
    ctx.provide("clock", {"now": 1})                 # 服务恢复 -> 自愈重新 apply
    assert events[-2:] == ["apply", "acquire"]
    assert rec["fiber"].state == Fiber.ACTIVE


def test_provide_conflict_raises():
    ctx = Context()
    ctx.provide("x", 1)
    try:
        ctx.provide("x", 2)
        assert False, "should raise"
    except Exception as e:
        assert "x" in str(e)


# ---------- 3. 类型化事件（emit / waterfall） ----------
def test_typed_event_emit_and_on():
    ctx = Context()
    seen = []
    ctx.plugin(lambda c, cfg: c.on("app/ready", lambda m: seen.append(m)), name="a")
    ctx.emit("app/ready", "hello")
    assert seen == ["hello"]


def test_waterfall_short_circuit():
    ctx = Context()
    ctx.plugin(lambda c, cfg: c.on("tools/pre-execute",
                                   lambda nxt, name: {"denied": True} if name == "rm" else nxt()),
               name="guard")
    ctx.plugin(lambda c, cfg: c.on("tools/pre-execute",
                                   lambda nxt, name: {"ok": name}), name="exec")
    assert ctx.waterfall("tools/pre-execute", "rm", default={"ok": None}) == {"denied": True}
    assert ctx.waterfall("tools/pre-execute", "ls", default={"ok": None}) == {"ok": "ls"}


# ---------- 4. 配置组合（layered patch） ----------
def test_config_compose_replace_and_insert():
    base = [{"id": "llm", "name": "dsh-llm", "config": {"temperature": 0.7}}]
    layer1 = [{"id": "llm", "config": {"temperature": 0.2}}]           # 整体替换
    layer2 = [{"insert": [{"id": "guard", "name": "dsh-guard"}]}]      # 追加
    out = compose(base, layer1, layer2)
    assert base[0]["config"] == {"temperature": 0.7}                   # 不改入参
    assert out[0]["config"] == {"temperature": 0.2}
    assert [e["id"] for e in out] == ["llm", "guard"]


def test_config_compose_missing_target_raises():
    try:
        compose([{"id": "a"}], [{"id": "zzz", "config": {}}])
        assert False, "should raise"
    except Exception as e:
        assert "zzz" in str(e)


# ---------- 5. 清单 / 指纹 ----------
def test_manifest_describe_and_fingerprint_stable():
    ctx = Context()

    def consumer(ctx_, cfg):
        pass
    consumer.inject = ["clock"]
    ctx.plugin(consumer, name="consumer")
    ctx.plugin(lambda c, cfg: None, name="producer")
    infos = describe(ctx)
    assert [i.id for i in infos] == ["consumer", "producer"]           # 按 id 升序
    fp1 = fingerprint(infos)
    fp2 = fingerprint(describe(ctx))
    assert fp1 == fp2 and fp1.startswith("sha256:")
