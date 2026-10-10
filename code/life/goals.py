"""M7 — goals (06 §7.1) + deterministic progress.

Four layers (survival / growth / social / meaning). Goals are seeded from persona
`goal_tendencies` at the weekly PLAN phase (GOAL_SET), then advanced by a
**deterministic** progress function driven by activities/skills (GOAL_PROGRESS),
and marked achieved at progress >= 1.0 (GOAL_ACHIEVED). No LLM in the numeric path.
"""
from __future__ import annotations

from dataclasses import dataclass

from .constants import GOAL_LAYERS, GOAL_PROGRESS_PER_ACTIVITY, KIND_TO_LAYER

# which activity types advance which goal kind
KIND_ACTIVITIES = {
    "security": ("work", "trade", "self_care"),
    "mastery": ("work", "learn"),
    "achievement": ("work", "learn", "civic"),
    "social": ("socialize", "leisure"),
    "meaning": ("civic", "socialize", "self_care"),
    "wealth": ("work", "trade"),
}


@dataclass
class Goal:
    goal_id: str
    agent_id: str
    kind: str
    layer: str
    priority: float = 0.5
    progress: float = 0.0
    status: str = "active"          # active | done | abandoned
    target_metric: str | None = None
    deadline_week: int | None = None
    description: str = ""

    def as_dict(self) -> dict:
        return {"goal_id": self.goal_id, "agent_id": self.agent_id, "kind": self.kind,
                "layer": self.layer, "priority": self.priority, "progress": round(self.progress, 6),
                "status": self.status, "target_metric": self.target_metric,
                "deadline_week": self.deadline_week, "description": self.description}


def layer_of(kind: str) -> str:
    return KIND_TO_LAYER.get(kind, "growth")


def initial_goals(agent_id: str, persona) -> list[Goal]:
    """Seed goals deterministically from persona goal_tendencies (06 §7.1)."""
    out: list[Goal] = []
    for i, t in enumerate(persona.goal_tendencies or []):
        kind = str(t.get("kind", "security"))
        out.append(Goal(goal_id=f"G-{agent_id}-{i:04d}", agent_id=agent_id, kind=kind,
                        layer=layer_of(kind), priority=float(t.get("weight", 0.5)),
                        description=f"{kind} 倾向"))
    if not out:
        out.append(Goal(goal_id=f"G-{agent_id}-0000", agent_id=agent_id, kind="security",
                        layer="survival", priority=0.5, description="security 倾向"))
    return out


def progress_delta(kind: str, activity_type: str) -> float:
    """Deterministic progress increment for performing `activity_type` toward `kind`."""
    if activity_type in KIND_ACTIVITIES.get(kind, ()):
        return GOAL_PROGRESS_PER_ACTIVITY
    return 0.0


def advance(goal: Goal, activity_type: str) -> float:
    """Return the new progress (clamped to [0,1]); does not mutate."""
    if goal.status != "active":
        return goal.progress
    return min(1.0, goal.progress + progress_delta(goal.kind, activity_type))


def is_achieved(progress: float) -> bool:
    return progress >= 1.0
