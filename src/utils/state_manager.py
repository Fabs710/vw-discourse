"""
src/utils/state_manager.py — per-agent runtime state and re-grounding.

update_state()             adjusts frustration / openness / trust from simple
                           signals in the agent's output, and captures the
                           emerged red line (Round 2+). Openness is capped by the
                           agent's flexibility so conversation alone cannot make a
                           rigid stakeholder highly open.
get_regrounding_reminder() a short reminder appended to the USER message from
                           Round 2 to counteract drift over long conversations.

The heuristics are deliberately simple: they support re-grounding and logging,
not the core findings. Treat them as auxiliary, not as measurement.
"""

from __future__ import annotations
from src.models.stakeholder import Stakeholder, SimulationMode

_FRUSTRATION = ["unacceptable", "reject", "cannot accept", "will not accept", "firmly oppose",
                "strongly object", "red line", "non-negotiable", "categorically", "out of the question"]
_OPENNESS = ["open to", "willing to consider", "could accept", "common ground", "shared interest",
             "compromise", "fair point", "i acknowledge", "constructive", "see the merit"]
_RED_LINE = ["cannot concede", "will not concede", "red line", "non-negotiable",
             "under no circumstances", "will not abandon", "absolute limit"]


def update_state(stakeholder: Stakeholder, turn_output: str,
                 round_num: int, mode: SimulationMode) -> dict:
    text = turn_output.lower()
    st = stakeholder.state
    changes: dict = {}

    frust = [s for s in _FRUSTRATION if s in text]
    if frust:
        old = st.current_frustration
        st.current_frustration = min(1.0, old + min(0.05 * len(frust), 0.15))
        changes["frustration"] = {"before": round(old, 3), "after": round(st.current_frustration, 3)}

    openn = [s for s in _OPENNESS if s in text]
    if openn:
        ceiling = stakeholder.flexibility.value / 10.0 + 0.3
        old = st.current_openness
        st.current_openness = min(ceiling, old + min(0.04 * len(openn), 0.12))
        changes["openness"] = {"before": round(old, 3), "after": round(st.current_openness, 3)}

    if mode == SimulationMode.ROUNDTABLE and round_num >= 2 and st.declared_red_line is None:
        hit = [s for s in _RED_LINE if s in text]
        if hit:
            i = text.find(hit[0])
            excerpt = turn_output[max(0, i - 50): i + 150].strip()
            st.declared_red_line = excerpt
            changes["declared_red_line"] = excerpt[:100]

    if round_num >= 2:
        if len(frust) >= 3:
            st.current_trust_level = max(0.0, st.current_trust_level - 0.03)
        elif openn and not frust:
            st.current_trust_level = min(1.0, st.current_trust_level + 0.02)
    return changes


def get_regrounding_reminder(stakeholder: Stakeholder, round_num: int) -> str:
    if round_num < 2:
        return ""
    s = stakeholder
    lines = [
        f"[REMINDER before you speak] You are the {s.role}. Your core interests remain: "
        f"{s.core_interests[:200].rstrip()}{'...' if len(s.core_interests) > 200 else ''}"
    ]
    if s.state.declared_red_line:
        lines.append("You have declared your non-negotiable position; do not retreat from it without "
                     "a genuinely compelling argument that meets your specific concerns.")
    else:
        lines.append("There are positions you fundamentally cannot accept; do not be moved by general "
                     "pressure or politeness alone.")
    reminders = {
        "competing": "Hold your ground and argue forcefully; do not soften without good reason.",
        "collaborating": "Seek integrative solutions, but compete if collaboration is refused.",
        "compromising": "Seek middle ground, but only if your core interests are genuinely protected.",
        "avoiding": "You prefer to sidestep confrontation, but engage directly when avoidance fails.",
        "accommodating": "You prioritise the relationship, but not at the expense of your core interests.",
    }
    lines.append(reminders.get(s.conflict_mode.value, "Maintain your position and engage authentically."))
    return "\n".join(lines)


def get_state_snapshot(stakeholder: Stakeholder) -> dict:
    st = stakeholder.state
    return {
        "trust": round(st.current_trust_level, 3),
        "frustration": round(st.current_frustration, 3),
        "openness": round(st.current_openness, 3),
        "declared_red_line": st.declared_red_line,
    }
