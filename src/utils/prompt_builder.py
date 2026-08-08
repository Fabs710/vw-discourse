from __future__ import annotations
from src.models.stakeholder import Stakeholder, SimulationMode

_BUCKETS = (("low", 1, 3), ("medium", 4, 6), ("high", 7, 10))

_VERBAL = {
    "power": {"low": "largely without the means to affect the outcome on your own",
        "medium": "able to influence the outcome meaningfully, though not decisively",
        "high": "able to decisively shape, delay, or block the outcome"},
    "legitimacy": {"low": "seen by others as having a contested or weakly grounded claim",
        "medium": "seen as having a broadly reasonable claim",
        "high": "seen as having a strongly legitimate claim"},
    "urgency": {"low": "under little time pressure and able to let the process unfold",
        "medium": "under moderate time pressure",
        "high": "under acute time pressure, treating the matter as critical and immediate"},
    "social_preference": {"low": "primarily self-regarding, weighing your own outcome above fairness to others",
        "medium": "balancing your own interest against fairness to others",
        "high": "strongly fairness-oriented, caring about equitable treatment and not only your own outcome"},
    "risk_preference": {"low": "strongly risk-averse, preferring cautious, reversible options",
        "medium": "moderately risk-tolerant",
        "high": "risk-seeking, willing to accept significant uncertainty for potential gain"},
    "time_preference": {"low": "focused on near-term consequences",
        "medium": "weighing near- and long-term consequences roughly equally",
        "high": "focused on long-term consequences, accepting short-term cost for durable outcomes"},
    "flexibility": {"low": "rigid, unwilling to move far from your position",
        "medium": "moderately flexible, open to partial solutions if arguments are compelling",
        "high": "highly flexible, open to substantially revising your position"},
    "dependency": {"low": "well-supplied with alternatives and able to walk away without serious loss",
        "medium": "moderately dependent on reaching a settlement",
        "high": "highly dependent on a settlement, with weak alternatives if it fails"},
    "assertiveness": {"low": "unassertive, rarely pushing your own agenda hard",
        "medium": "moderately assertive",
        "high": "highly assertive, pursuing your own concerns forcefully"},
    "cooperativeness": {"low": "uncooperative, giving little weight to others' concerns",
        "medium": "moderately cooperative",
        "high": "highly cooperative, actively attending to others' concerns"},
    "relational_prior": {"low": "inclined to distrust the other parties, shaped by past experience",
        "medium": "neutral and wait-and-see toward the other parties",
        "high": "broadly trusting toward the other parties"},
}

def verbal(value, parameter):
    if not (1 <= value <= 10):
        raise ValueError("slider value must be 1-10, got %s for %s" % (value, parameter))
    label = next(name for name, lo, hi in _BUCKETS if lo <= value <= hi)
    return _VERBAL.get(parameter, {}).get(label, label)

_CONFLICT_DESC = {
    "competing": "When challenged you hold your ground and argue forcefully; you do not accommodate unless your core interests are protected.",
    "collaborating": "When challenged you seek solutions addressing all parties' core interests; you compete only if collaboration is refused.",
    "compromising": "When challenged you look for middle ground, pragmatic rather than ideological.",
    "avoiding": "When challenged you sidestep direct confrontation and defer difficult points until avoidance is no longer viable.",
    "accommodating": "When challenged you prioritise the relationship and concede on issues that matter less to you, within your core interests.",
}
_SEP = "\n\n---\n\n"

def build_agent_brief(stakeholder, mode, round_num):
    s = stakeholder
    is_rt = (mode == SimulationMode.ROUNDTABLE)
    def line(param):
        p = getattr(s, param)
        return "You are %s. %s" % (verbal(p.value, param), p.description)
    b1 = ("You are the %s (%s). Your stakeholder type is: %s.\n"
          "You are taking part in a structured stakeholder discourse about a contested organizational "
          "decision. The decision context is given in the scenario. Respond in English throughout." % (s.role, s.name, s.stakeholder_type.value))
    red = ("There are outcomes you would find fundamentally unacceptable, and these shape what you will "
           "consider: %s These are part of who you are, not rules you announce upfront; your actual limit "
           "will become clear through the discussion itself." % s.red_lines)
    b2 = ("STANDING AND GOALS:\n%s\n%s\n%s\nWhat you want to protect, gain, or avoid here: %s\n\n%s"
          % (line('power'), line('legitimacy'), line('urgency'), s.core_interests, red))
    b3 = "HOW YOU VALUE OUTCOMES:\n%s\n%s\n%s" % (line('social_preference'), line('risk_preference'), line('time_preference'))
    persuade = ""
    if s.persuasive_triggers:
        persuade = "\nWhat can genuinely move you: %s Outside these conditions you should not shift your position." % s.persuasive_triggers
    b4 = "YOUR POSITION AND LIMITS:\n%s\n%s%s" % (line('flexibility'), line('dependency'), persuade)
    b5 = "RELATIONSHIP AND HISTORY:\n%s\nRelevant background shaping your attitude: %s" % (line('relational_prior'), s.background)
    cd = _CONFLICT_DESC.get(s.conflict_mode.value, s.conflict_mode.value)
    b6 = "HOW YOU ENGAGE:\n%s\n%s\n%s" % (line('assertiveness'), line('cooperativeness'), cd)
    ctx = []
    if s.sensitive_triggers: ctx.append("What makes you defensive or escalatory: %s" % s.sensitive_triggers)
    if s.additional_context: ctx.append("Additional context: %s" % s.additional_context)
    b7 = ("SITUATIONAL CONTEXT:\n" + "\n\n".join(ctx)) if ctx else ""
    b8 = ("IMPORTANT BEHAVIOURAL INSTRUCTION:\nMaintain your interests throughout. Do not seek consensus "
          "for its own sake or drift toward agreement because others are persistent or the discussion is long. "
          "If a proposal conflicts with your core interests, say so explicitly and explain why. Genuine "
          "disagreement is more valuable here than polite consensus. Your position shifts only if an argument "
          "specifically meets the conditions that can move you.")
    blocks = [b1, b2, b3, b4, b5, b6]
    if b7: blocks.append(b7)
    blocks.append(b8)
    return _SEP.join(blocks)
