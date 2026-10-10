"""T91 内核侧配套：商品库存折叠/守恒 + 货币下限不变量。"""

from engine import conservation
from engine.constants import PHASE_ARBITRATE
from engine.events import spec
from engine.ledger import Ledger
from engine.replay import apply_event, replay_records
from engine.state import initial_state, state_hash


def _apply(state, led, ev):
    return apply_event(state, led.append_spec(ev))


def _seed(state, led):
    _apply(state, led, spec(0, 0, "SYSTEM", "WORLD_INIT", {"seed": 1}))
    _apply(state, led, spec(0, 0, "SYSTEM", "AGENT_BORN", {"agent_id": "A", "birth_round": 0}))


def test_production_events_registered():
    from engine.events import EVENT_TYPES
    for t in ("PRODUCE", "CONSUME", "DEPRECIATE", "PRODUCE_OVERFLOW", "VOTE_CAST"):
        assert t in EVENT_TYPES


def test_inventory_folds_and_goods_conservation():
    st = initial_state(1); led = Ledger(); _seed(st, led)
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "PRODUCE",
                         {"agent_id": "A", "good_id": "food", "qty": 5, "place": "farm",
                          "recipe": "", "skill_level": 1}))
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "CONSUME",
                         {"agent_id": "A", "good_id": "food", "qty": 2, "purpose": "eat"}))
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "DEPRECIATE",
                         {"agent_id": "A", "asset_id": "food", "delta_mu": 1}))
    assert st.inventory["A"]["food"] == 5 - 2 - 1
    assert conservation.check_goods_conservation(st) == []
    # inventory 入 state_hash：改库存应改变哈希
    h1 = state_hash(st)
    st.inventory["A"]["food"] += 1
    assert state_hash(st) != h1


def test_goods_conservation_detects_violation():
    st = initial_state(1); led = Ledger(); _seed(st, led)
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "PRODUCE",
                         {"agent_id": "A", "good_id": "food", "qty": 5}))
    st.inventory["A"]["food"] = 999  # 人为破坏
    v = conservation.check_goods_conservation(st)
    assert v and v[0]["invariant"] == "goods_conservation"


def test_money_floor_invariant():
    st = initial_state(1); led = Ledger(); _seed(st, led)
    # 无铸币、代谢 100 -> cash=-100, burned=100 -> M=-100 == minted-burned，但 < μ_floor(0)
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "METABOLISM", {"agent_id": "A", "amount": 100}))
    viols = conservation.check_all(st)
    kinds = {v["invariant"] for v in viols}
    assert "money_floor" in kinds
    assert "money_conservation" not in kinds  # 货币守恒式仍成立


def test_production_folds_replay_parity():
    st = initial_state(1); led = Ledger(); _seed(st, led)
    _apply(st, led, spec(0, PHASE_ARBITRATE, "A", "PRODUCE",
                         {"agent_id": "A", "good_id": "food", "qty": 5}))
    assert state_hash(replay_records(led.records)) == state_hash(st)
