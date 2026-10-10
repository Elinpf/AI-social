"""M1 — persona / identity (06 §2).

Personas are static config loaded from `config/personas.json` (M1 is decoupled
from the engine: the engine only ever sees `persona_id` + the deterministic
derived scalars below). No online persona generation.

The `compressed_profile` builder follows the Generative Agents "identity stable
set" *structure* (scratch.py `get_str_iss`), reimplemented for our schema.
GA is Apache-2.0; this file is a modified/adapted reimplementation (see NOTICE).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import ROLE_WORKPLACE


@dataclass
class Persona:
    persona_id: str
    display_name: str
    age: int
    role_id: str
    home_place: str
    personality_big5: dict[str, int]
    values: dict[str, int]
    skills: list[dict[str, Any]]
    background: str
    goal_tendencies: list[dict[str, Any]]
    needs_init: dict[str, int]
    speech_style: dict[str, str]
    relations_init: list[dict[str, Any]] = field(default_factory=list)

    # ---- deterministic derived scalars (06 §2.4) --------------------------
    @property
    def work_ethic(self) -> float:
        return self.personality_big5.get("conscientiousness", 50) / 100.0

    @property
    def social_initiative(self) -> float:
        e = self.personality_big5.get("extraversion", 50)
        a = self.personality_big5.get("agreeableness", 50)
        return (e + a) / 200.0

    @property
    def risk_appetite(self) -> float:
        o = self.personality_big5.get("openness", 50)
        n = self.personality_big5.get("neuroticism", 50)
        return (o + (100 - n)) / 200.0

    @property
    def saving_propensity(self) -> float:
        sec = self.values.get("security", 60)
        n = self.personality_big5.get("neuroticism", 50)
        return (sec + n) / 200.0

    @property
    def work_place(self) -> str:
        return ROLE_WORKPLACE.get(self.role_id, "plaza")

    def compressed_profile(self, current_goal: str = "") -> str:
        """Stable identity text injected into prompts (<= ~200 tokens)."""
        b5 = self.personality_big5
        vals = self.values
        style = self.speech_style
        parts = [
            f"{self.display_name}（{self.persona_id}，{self.age}岁，{self.role_id}）。",
            f"背景：{self.background}",
            ("性格：开放{openness}/尽责{conscientiousness}/外向{extraversion}/"
             "宜人{agreeableness}/神经质{neuroticism}（0-100）。").format(**b5),
            ("价值：自主{self_direction}/仁爱{benevolence}/成就{achievement}/安全{security}。"
             ).format(**vals),
            f"语气：{style.get('tone','plain')}；长度：{style.get('verbosity','short')}。",
        ]
        if current_goal:
            parts.append(f"当前目标：{current_goal}")
        return "".join(parts)


def _as_int_map(d: dict) -> dict[str, int]:
    return {str(k): int(v) for k, v in (d or {}).items()}


def persona_from_dict(d: dict) -> Persona:
    return Persona(
        persona_id=str(d["persona_id"]),
        display_name=str(d.get("display_name", d["persona_id"])),
        age=int(d.get("age", 30)),
        role_id=str(d.get("role_id", "unemployed")),
        home_place=str(d.get("home_place", "residence")),
        personality_big5=_as_int_map(d.get("personality_big5", {})),
        values=_as_int_map(d.get("values", {})),
        skills=list(d.get("skills", [])),
        background=str(d.get("background", "")),
        goal_tendencies=list(d.get("goal_tendencies", [])),
        needs_init=_as_int_map(d.get("needs_init", {})),
        speech_style=dict(d.get("speech_style", {})),
        relations_init=list(d.get("relations_init", [])),
    )


def load_personas(path: str | Path) -> dict[str, Persona]:
    """Load personas.json -> {persona_id: Persona}. Deterministic, no engine dep."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items = raw["personas"] if isinstance(raw, dict) and "personas" in raw else raw
    out: dict[str, Persona] = {}
    for d in items:
        p = persona_from_dict(d)
        out[p.persona_id] = p
    return out
