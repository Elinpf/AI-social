"""观测层参数（阈值 / 口径）与默认值。

口径来源（不自行发明）：
  - `v1.1/07-emergence-observation.md`（ε/ε_strong、S1–S4 显著性、D/F/K 分级）
  - `v1.1/13-wellbeing-metrics.md`（W1–W7、背离判据）
  - `v1.1/15-event-census-spec.md`（E1–E20 判定式阈值 ε=20 / ε_strong=50 / θ_dep=20 / N_round=3）
  - `v1/02-lifecycle-anticheat.md`（反作弊 W_wash=4 / ρ_wash=0.8 / L_cycle=5 / L_hop=3 /
    K_split=4 / T_large=30 / W_split=4；I_eff 口径）

说明：所有阈值均为**符号 + 默认建议值**；标【待标定】者由沙盒/T7 回填，
观测层不写死口径，允许通过 `params` 覆盖（保证同 `(log, params)` 可复现）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass(frozen=True)
class EmergenceParams:
    # --- 关系（07 §1.2 / 15 §2）---
    epsilon: float = 20.0            # ε，弱边阈值
    epsilon_strong: float = 50.0     # ε_strong，强边阈值
    epsilon_rec: float = 50.0        # ε_rec，互惠阈值，默认 = ε_strong
    w_min: float = 0.0               # W_MIN
    w_max: float = 100.0             # W_MAX（R = W_MAX − W_MIN）
    # --- 语义事件（15 §2）---
    skill_gap_mentor: int = 2         # E1：技能级差 ≥ 2
    theta_dep: float = 20.0           # θ_dep，需求匮乏阈值
    n_round: int = 3                  # N_round，协商轮次上限
    d_maint: int = 84                 # D_maint，关系维护间隔（默认 1 周）
    w_burn: int = 2                   # W_burn，倦怠连续时段数【待标定】
    theta_scarce: float = 50.0        # E9 稀缺指数阈值（0–100，同 MARKET_TRADE.scarcity_index 尺度；08 §1.2-N）【待标定】
    # --- 圈层（07 §1.4）---
    q_min: float = 0.30
    s_min: int = 3
    theta_stable: float = 0.60
    # --- 标签/观点（07 §1.3）---
    theta_adopt: float = 0.20
    # --- 规范（07 §1.5）---
    theta_cov: float = 0.30
    theta_sup: float = 0.50
    # --- 职业（07 §1.6）---
    n_switch: int = 2
    c_min: int = 2
    # --- 传播（07 §2.3）---
    theta_reach: float = 0.45         # N=20 目标
    w_seed: int = 84                  # 1 周
    # --- 时间窗（07 §3.2）---
    wb: int = 84                      # 基线窗
    wx: int = 84                      # 观测窗
    # --- 显著性（07 §3.3）---
    z_band: float = 3.0
    n_perm: int = 1000
    # --- PageRank（08 §4.3）---
    pagerank_d: float = 0.85
    pagerank_k: int = 30


@dataclass(frozen=True)
class WellbeingParams:
    theta_dep: float = 20.0
    wealth_high_pct: float = 0.75
    wealth_low_pct: float = 0.25


@dataclass(frozen=True)
class AntiFraudParams:
    # v1/02 §5.3
    w_wash: int = 4
    rho_wash: float = 0.8
    l_cycle: int = 5
    l_hop: int = 3
    k_split: int = 4
    t_large: int = 30
    w_split: int = 4
    w_refi: int = 3
    n_death: int = 3                  # 连续负数回合数阈值（判死基准，与 02 §2 对齐）
    floor: float = 0.0                # θ_floor


@dataclass(frozen=True)
class ObsParams:
    emergence: EmergenceParams = field(default_factory=EmergenceParams)
    wellbeing: WellbeingParams = field(default_factory=WellbeingParams)
    antifraud: AntiFraudParams = field(default_factory=AntiFraudParams)

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_PARAMS = ObsParams()

# 语义判定命中的 [F] 维度（只读冻结 LLM_JUDGMENT，不入判定/门禁）
SOFT_JUDGMENT_DIMENSIONS = (
    "mentor_relation", "creative_quality", "secret_trust", "job_preference",
    "academic_quality", "friendship_label", "first_impression",
    "respect_score", "affection_score", "satisfaction", "meaning",
)


__all__ = [
    "EmergenceParams", "WellbeingParams", "AntiFraudParams", "ObsParams",
    "DEFAULT_PARAMS", "SOFT_JUDGMENT_DIMENSIONS",
]
