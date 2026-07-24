"""
src/models/stakeholder.py — VW Discourse Simulation

Stakeholder data model implementing the layered parameter framework
(a belief-desire-intention spine instantiated by four functional layers).

All sliders are integers 1-10 and are converted to verbal descriptors before
any API call (see prompt_builder.verbal) — raw numbers are NEVER sent to a model.
The scale poles below are the documented operationalisation of each parameter
(cf. Lutz et al., 2025): they are part of the method, not an implementation detail.

  Layer 1 - Salience            (Mitchell, Agle & Wood, 1997)
    power             1 = little capacity to affect the outcome   10 = decisive capacity
    legitimacy        1 = weak / contested claim                  10 = strongly recognised claim
    urgency           1 = no time pressure                        10 = acute / critical
  Layer 2 - Motivation          (behavioural economics)
    social_preference 1 = purely self-regarding                   10 = strongly fairness-oriented   (Fehr & Schmidt, 1999)
    risk_preference   1 = strongly risk-averse                    10 = strongly risk-seeking        (Kahneman & Tversky, 1979)
    time_preference   1 = short-term focused                      10 = long-term focused            (Frederick et al., 2002)
  Layer 3 - Position            (White & Neale, 1991)
    flexibility       1 = rigid / fixed position                  10 = highly flexible
    dependency        1 = strong alternatives (strong BATNA)      10 = captive (weak BATNA)
    red_lines         text; emergent — absorbed into the goal profile, never pre-declared
  Layer 4 - Interaction         (Thomas, 1992 / Thomas-Kilmann)
    assertiveness     1 = unassertive                             10 = pursues own concerns hard
    cooperativeness   1 = uncooperative                           10 = attends strongly to others
    -> conflict_mode is DERIVED from the two axes (a property, never set in config)
  Belief
    relational_prior  1 = deep distrust                           10 = high trust

Requires: pydantic v2  (pip install pydantic)
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ── Enumerations ─────────────────────────────────────────────────────────────

class StakeholderType(str, Enum):
    INTERNAL      = "internal"
    EXTERNAL      = "external"
    REGULATORY    = "regulatory"
    CIVIL_SOCIETY = "civil_society"
    CUSTOMER      = "customer"
    SHAREHOLDER   = "shareholder"
    OTHER         = "other"


class SimulationMode(str, Enum):
    ROUNDTABLE = "roundtable"
    BILATERAL  = "bilateral"
    BOTH       = "both"


class ConflictMode(str, Enum):
    """Thomas-Kilmann conflict-handling modes. DERIVED, never set directly."""
    COMPETING     = "competing"       # high assertiveness, low cooperativeness
    COLLABORATING = "collaborating"   # high assertiveness, high cooperativeness
    COMPROMISING  = "compromising"    # moderate on both (the centre)
    AVOIDING      = "avoiding"        # low assertiveness, low cooperativeness
    ACCOMMODATING = "accommodating"   # low assertiveness, high cooperativeness


def derive_conflict_mode(assertiveness: int, cooperativeness: int) -> ConflictMode:
    """
    Derive the Thomas-Kilmann conflict mode from its two underlying dimensions
    (Thomas, 1992). Modelling the axes and deriving the mode — rather than
    hand-assigning a category — removes researcher arbitrariness and anchors the
    parameter in the validated 2-D structure.

    Bands: HIGH >= 6, LOW <= 4, otherwise MID (5). MID on either axis, or a
    HIGH/LOW split that is not clear-cut, resolves to COMPROMISING (the centre).
    """
    HIGH, LOW = 6, 4
    a_high, a_low = assertiveness >= HIGH, assertiveness <= LOW
    c_high, c_low = cooperativeness >= HIGH, cooperativeness <= LOW
    if a_high and c_low:
        return ConflictMode.COMPETING
    if a_high and c_high:
        return ConflictMode.COLLABORATING
    if a_low and c_high:
        return ConflictMode.ACCOMMODATING
    if a_low and c_low:
        return ConflictMode.AVOIDING
    return ConflictMode.COMPROMISING


# ── Parameter and state models ───────────────────────────────────────────────

class SliderParam(BaseModel):
    """A 1-10 slider paired with a mandatory contextualising description.

    The description grounds the value in THIS stakeholder in THIS case; it is
    what turns an abstract number into a defensible, case-specific setting.
    """
    value: int = Field(ge=1, le=10, description="Slider value, 1-10 inclusive.")
    description: str = Field(min_length=5, description="What this value means for this stakeholder here.")


class RuntimeState(BaseModel):
    """Dynamic per-agent state — the only part that changes during a run.

    declared_red_line is null until the agent declares a non-concedable position
    during Round 2 discourse. It is NEVER pre-loaded from the red_lines text.
    """
    current_trust_level: float = Field(default=0.5, ge=0.0, le=1.0)
    current_frustration: float = Field(default=0.0, ge=0.0, le=1.0)
    current_openness:    float = Field(default=0.5, ge=0.0, le=1.0)
    declared_red_line:   Optional[str] = None


# ── Main model ────────────────────────────────────────────────────────────────

class Stakeholder(BaseModel):
    """A stakeholder agent under the layered parameter framework."""

    # Identity
    name: str
    role: str
    stakeholder_type: StakeholderType
    modes: list[SimulationMode] = Field(min_length=1)

    # Layer 1 — Salience
    power:      SliderParam
    legitimacy: SliderParam
    urgency:    SliderParam

    # Layer 2 — Motivation
    social_preference: SliderParam
    risk_preference:   SliderParam
    time_preference:   SliderParam

    # Layer 3 — Position
    flexibility: SliderParam
    dependency:  SliderParam

    # Layer 4 — Interaction (conflict mode is derived from these two)
    assertiveness:   SliderParam
    cooperativeness: SliderParam

    # Belief
    relational_prior: SliderParam

    # Text fields
    core_interests: str = Field(min_length=10, description="[MANDATORY] Concrete outcomes to protect, gain, or avoid.")
    background:     str = Field(min_length=10, description="[MANDATORY] History shaping the current attitude.")
    red_lines:      str = Field(
        min_length=10,
        description=(
            "[MANDATORY] Absorbed into the goal profile as background — NEVER inserted "
            "verbatim as a pre-declared constraint. The specific limit emerges in Round 2."
        ),
    )
    persuasive_triggers: Optional[str] = Field(default=None, description="[RECOMMENDED] What can genuinely move this stakeholder.")
    sensitive_triggers:  Optional[str] = Field(default=None, description="[RECOMMENDED] What makes them defensive or escalatory.")
    additional_context:  Optional[str] = Field(default=None, description="[OPTIONAL] Situational modifiers.")

    # Runtime state (system-managed; do not set in config)
    state: RuntimeState = Field(default_factory=RuntimeState)

    # ── Derived ───────────────────────────────────────────────────────────────
    @property
    def conflict_mode(self) -> ConflictMode:
        """Derived Thomas-Kilmann mode from assertiveness x cooperativeness."""
        return derive_conflict_mode(self.assertiveness.value, self.cooperativeness.value)

    # ── Validators ──────────────────────────────────────────────────────────────
    @field_validator("modes")
    @classmethod
    def _modes_unique(cls, v: list[SimulationMode]) -> list[SimulationMode]:
        if len(v) != len(set(v)):
            raise ValueError("modes must not contain duplicates.")
        return v

    # ── Convenience ───────────────────────────────────────────────────────────
    def participates_in(self, mode: SimulationMode) -> bool:
        return SimulationMode.BOTH in self.modes or mode in self.modes

    def reset_state(self) -> None:
        self.state = RuntimeState()

    def __repr__(self) -> str:
        return (f"Stakeholder(name={self.name!r}, role={self.role!r}, "
                f"type={self.stakeholder_type.value!r}, conflict_mode={self.conflict_mode.value!r})")


# ── Self-test: python src/models/stakeholder.py ──────────────────────────────
if __name__ == "__main__":
    def _p(v, d="contextual note for this stakeholder"):
        return SliderParam(value=v, description=d)

    # Two illustrative roles exercising the derivation.
    example = Stakeholder(
        name="Executive Management", role="Management board driving a restructuring",
        stakeholder_type=StakeholderType.SHAREHOLDER, modes=[SimulationMode.BOTH],
        power=_p(8), legitimacy=_p(5), urgency=_p(7),
        social_preference=_p(3), risk_preference=_p(7), time_preference=_p(7),
        flexibility=_p(5), dependency=_p(3),
        assertiveness=_p(9), cooperativeness=_p(3), relational_prior=_p(4),
        core_interests="Securing a controlling position to build a larger banking group.",
        background="Built a large stake via shares and derivatives; launched a tender offer.",
        red_lines="Will not settle for a position that denies a credible path to control.",
    )
    regulator = Stakeholder(
        name="Financial Supervisor", role="Prudential supervisor",
        stakeholder_type=StakeholderType.REGULATORY, modes=[SimulationMode.BOTH],
        power=_p(7), legitimacy=_p(9), urgency=_p(3),
        social_preference=_p(7), risk_preference=_p(2), time_preference=_p(7),
        flexibility=_p(5), dependency=_p(2),
        assertiveness=_p(5), cooperativeness=_p(6), relational_prior=_p(6),
        core_interests="Ensuring suitability, stability, and an orderly process.",
        background="Has not yet approved the crossing of key ownership thresholds.",
        red_lines="Block any threshold crossing that would threaten financial stability.",
    )

    assert example.conflict_mode is ConflictMode.COMPETING
    assert regulator.conflict_mode is ConflictMode.COMPROMISING

    print("Stakeholder model OK.")
    print(" ", repr(example))
    print(" ", repr(regulator))
    # Show the full derivation table
    print("\nderive_conflict_mode(assert, coop):")
    for a, c in [(9, 3), (8, 8), (2, 8), (2, 2), (5, 5), (7, 5), (6, 6)]:
        print(f"  a={a} c={c} -> {derive_conflict_mode(a, c).value}")
