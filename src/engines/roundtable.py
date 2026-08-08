"""
src/engines/roundtable.py — configurable roundtable discourse engine.

Carries over the proven design (multi-round turns, dynamic expert summoning, an
LLM convergence monitor, a neutral moderator, and a structured final synthesis)
and adds two things: light-touch salience orchestration (speaking order and
synthesis weighting follow salience) and reproducible logging (model snapshot,
fingerprint, and seed captured per call).

Behaviour is driven entirely by SimulationConfig — nothing is hardcoded.
"""

from __future__ import annotations
import json
import re
from src.models.stakeholder import SimulationMode
from src.utils.llm import LLMClient
from src.utils.config_loader import SimulationConfig
from src.utils.prompt_builder import build_agent_brief
from src.utils.state_manager import update_state, get_regrounding_reminder, get_state_snapshot
from src.utils.io import save_output, save_log, save_run_summary, build_conversation_text
from src.utils.pricing import estimate_cost

_SUMMON = re.compile(r"\[SUMMON:\s*(.+?)\]", re.IGNORECASE)
_SEP = "\n\n---\n\n"


def _salience(s) -> float:
    return (s.power.value + s.legitimacy.value + s.urgency.value) / 3.0


def _speaking_order(cfg: SimulationConfig) -> list[str]:
    keys = list(cfg.roundtable.turn_order)
    if cfg.roundtable.salience_orchestration:
        keys.sort(key=lambda k: _salience(cfg.get_stakeholder(k)), reverse=True)
    return keys


def _recent(history, round_num):
    if round_num <= 1:
        return history
    return [e for e in history if e.get("round", 0) >= round_num - 1 or e.get("agent") == "moderator"]


def _parse_json(text: str) -> dict:
    clean = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"status": "progressing", "recommendation": "continue", "rationale": "unparsed"}


def run_roundtable(config: SimulationConfig, timestamp: str, run_folder: str, client=None) -> dict:
    rt = config.roundtable
    m = config.model
    client = client or LLMClient(m.name, m.temperature, m.seed, m.max_tokens)
    scenario = config.get_scenario_text()

    base_keys = _speaking_order(config)
    for k in base_keys:
        config.get_stakeholder(k).reset_state()

    # provenance: freeze the exact scenario text and every generated brief with the run
    save_output(scenario, "scenario_used", run_folder)
    for k in base_keys:
        save_output(build_agent_brief(config.get_stakeholder(k), SimulationMode.ROUNDTABLE, 2), f"brief_{k}", run_folder)

    history: list[dict] = []
    experts: dict[str, dict] = {}
    summons_used = 0
    total_tokens = 0
    total_in = 0
    total_out = 0
    truncated = 0
    calls: list[dict] = []

    def call(messages, label) -> str:
        nonlocal total_tokens, total_in, total_out, truncated
        r = client.call(messages, label)
        print("  [%02d] %-28s %5.1fs  %6d tok" % (len(calls) + 1, label, r.latency_s, r.tokens), flush=True)
        total_tokens += r.tokens
        total_in += r.input_tokens
        total_out += r.output_tokens
        if r.finish_reason in ("length", "max_tokens"):
            truncated += 1
        calls.append({"label": label, **r.meta()})
        return r.text

    def agent_message(round_num, key):
        if not history:
            return (f"DECISION SCENARIO:\n{scenario}{_SEP}You are the first to speak. State your "
                    f"position on the decision clearly — your core concerns, priorities, and what you "
                    f"would argue for or against.")
        convo = build_conversation_text(_recent(history, round_num))
        tail = ("This is round %d. " % round_num) + ("It is now your turn. Engage directly with the other stakeholders' arguments — where "
                "you agree, where you disagree, and why. Do not seek compromise for its own sake.")
        if round_num >= 2:
            tail += " If a specialist is genuinely needed and none has been summoned, include [SUMMON: brief description]."
        return f"DECISION SCENARIO:\n{scenario}{_SEP}CONVERSATION SO FAR:\n\n{convo}{_SEP}{tail}"

    def expert_turn(persona, round_num, just_summoned):
        convo = build_conversation_text([e for e in history if e.get("round") == round_num or e.get("agent") == "moderator"])
        ask = ("You have just been summoned because your expertise is needed. Give your expert "
               "assessment on the specific question that prompted your invitation; speak authoritatively "
               "within your domain and decline to opine outside it."
               if just_summoned else
               "Respond to any questions directed at your area of expertise; stay within your mandate.")
        return call([{"role": "system", "content": persona},
                     {"role": "user", "content": f"DECISION SCENARIO:\n{scenario}{_SEP}CONVERSATION SO FAR:\n\n{convo}{_SEP}{ask}"}],
                    f"round{round_num}_expert")

    def make_expert_persona(desc, round_num):
        sysp = ("You are an expert prompt engineer. Write a concise system prompt (under 180 words) for a "
                "neutral domain expert summoned into a stakeholder discourse about a contested organizational decision. "
                "The expert is a knowledge holder, not an interest holder: define who they are, their specific "
                "domain, and instruct them to speak authoritatively within it and decline to opine outside it.")
        return call([{"role": "system", "content": sysp},
                     {"role": "user", "content": f"Expert needed: {desc}\n\nContext:\n{scenario[:500]}..."}],
                    f"round{round_num}_gen_persona")

    def convergence(round_num):
        sysc = ("You are an analytical observer of stakeholder discourse. Respond with ONLY valid JSON, "
                "no preamble and no markdown.")
        userc = (f"Assess this discourse after round {round_num}.{_SEP}TRANSCRIPT:\n"
                 f"{build_conversation_text(history)}{_SEP}"
                 'Return JSON with fields: {"status":"progressing|plateauing|converged",'
                 '"recommendation":"continue|intervene|synthesise","rationale":"1-2 sentences"}. '
                 "Agreement on process does NOT count as convergence; genuine convergence requires the "
                 "core contested issues between incompatible interests to be substantively resolved. "
                 "IMPORTANT - 'synthesise' means END THE SIMULATION: recommend it ONLY when further "
                 "rounds would clearly change nothing - either the core issues are substantively "
                 "resolved (converged), or positions have hardened into a stable impasse with no "
                 "movement across the last two rounds. If core issues remain unresolved and positions "
                 "are still moving or untested, recommend 'continue' (or 'intervene' if the discussion "
                 "is circling without progress). Do NOT recommend 'synthesise' merely because drafting "
                 "a combined term sheet would be a sensible next step in a real negotiation.")
        return _parse_json(call([{"role": "system", "content": sysc}, {"role": "user", "content": userc}],
                                f"convergence_round{round_num}"))

    def moderator(round_num, intervene):
        sysm = ("You are a neutral facilitator managing a structured stakeholder discourse. You hold no "
                "position and never argue for any side. Your role is purely procedural.")
        curr = build_conversation_text([e for e in history if e.get("round") == round_num])
        if intervene:
            userm = (f"The discourse has plateaued after round {round_num}.\n\n{curr}\n\nAs moderator, "
                     "identify where the core impasse lies, propose two or three concrete compromise "
                     "positions that might bridge the most conflicting stakeholders, and pose one pointed "
                     "question to each stakeholder. Frame these as facilitator proposals, not opinions.")
        else:
            userm = (f"Round {round_num} has completed.\n\n{curr}\n\nProduce a concise, strictly neutral "
                     "moderator summary: (1) what has been agreed, (2) where the core disagreements remain, "
                     "(3) what key trade-offs are still unaddressed, (4) a brief refocus for the next round.")
        return call([{"role": "system", "content": sysm}, {"role": "user", "content": userm}],
                    f"moderator_round{round_num}")

    def synthesis():
        weight = ("When weighing positions, give proportionally more weight to stakeholders with higher "
                  "standing (power and legitimacy), while still recording minority positions. "
                  if rt.salience_orchestration else "")
        max_round = max((e.get("round", 0) for e in history), default=1)
        convo = build_conversation_text([e for e in history if e.get("agent") == "moderator" or e.get("round") == max_round])
        syss = ("You are an expert facilitator producing a formal decision-support document. Follow the "
                "schema exactly; be analytical and concise; focus on what the multi-turn interaction "
                "revealed that a single prompt would miss.")
        users = (f"DECISION SCENARIO:\n{scenario}{_SEP}TRANSCRIPT:\n{convo}{_SEP}{weight}"
                 "Produce a synthesis with these sections: 1. Decision context. 2. Stakeholder assembly. "
                 "3. Final positions (each stakeholder, 2-3 sentences). 4. Genuine conflicts (structurally "
                 "incompatible positions). 5. Areas of convergence. 6. Key trade-offs for the decision-maker. "
                 "7. Integrative pathways. 8. Open questions. 9. Recommended next step. 10. Emergent insights "
                 "that only appeared through multi-turn interaction.")
        return call([{"role": "system", "content": syss}, {"role": "user", "content": users}], "final_synthesis")

    def label_of(key):
        if key in experts:
            return experts[key]["label"]
        s = config.get_stakeholder(key)
        return f"{s.name} ({s.role})"

    round_num = 1
    convergence_status = "progressing"
    for round_num in range(1, rt.max_rounds + 1):
        for key in base_keys + list(experts.keys()):
            if key in experts:
                text = expert_turn(experts[key]["persona"], round_num, False)
            else:
                sh = config.get_stakeholder(key)
                system = build_agent_brief(sh, SimulationMode.ROUNDTABLE, round_num)
                user = agent_message(round_num, key)
                reminder = get_regrounding_reminder(sh, round_num)
                if reminder:
                    user += _SEP + reminder
                text = call([{"role": "system", "content": system}, {"role": "user", "content": user}],
                            f"round{round_num}_{key}")
                update_state(sh, text, round_num, SimulationMode.ROUNDTABLE)
                if config.validation_mode:
                    save_log({"round": round_num, "agent": key, "salience": round(_salience(sh), 2),
                              "conflict_mode": sh.conflict_mode.value,
                              "params": {p: getattr(sh, p).value for p in
                                         ("power", "legitimacy", "urgency", "social_preference",
                                          "risk_preference", "time_preference", "flexibility",
                                          "dependency", "assertiveness", "cooperativeness", "relational_prior")},
                              "state": get_state_snapshot(sh)}, f"val_round{round_num}_{key}", run_folder)

            history.append({"round": round_num, "agent": key, "agent_label": label_of(key), "content": text})
            save_output(text, f"round{round_num}_{key}", run_folder)

            mt = _SUMMON.search(text)
            if mt and summons_used < rt.max_summons and key not in experts:
                desc = mt.group(1).strip()
                persona = make_expert_persona(desc, round_num)
                ekey = f"expert_{summons_used + 1}"
                experts[ekey] = {"persona": persona, "label": f"Expert: {desc[:40]}"}
                summons_used += 1
                etext = expert_turn(persona, round_num, True)
                history.append({"round": round_num, "agent": ekey, "agent_label": experts[ekey]["label"], "content": etext})
                save_output(etext, f"round{round_num}_{ekey}_first", run_folder)

        assess = convergence(round_num)
        save_log({"round": round_num, **assess}, f"convergence_round{round_num}", run_folder)
        convergence_status = assess.get("status", "progressing")
        rec = assess.get("recommendation", "continue")
        mod = moderator(round_num, rec == "intervene")
        history.append({"round": round_num, "agent": "moderator", "agent_label": f"Moderator (round {round_num})", "content": mod})
        save_output(mod, f"moderator_round{round_num}", run_folder)
        if rec == "synthesise" and round_num >= rt.min_rounds_before_synthesis:
            break

    final = synthesis()
    save_output(final, "final_synthesis", run_folder)
    save_output(build_conversation_text(history) + "\n\n=== SYNTHESIS ===\n\n" + final, "full_transcript", run_folder)

    summary = {
        "engine": "roundtable",
        "timestamp": timestamp,
        "run_folder": run_folder,
        "rounds_completed": round_num,
        "convergence_status": convergence_status,
        "experts_summoned": [e["label"] for e in experts.values()],
        "total_tokens": total_tokens,
        "input_tokens": total_in,
        "output_tokens": total_out,
        "truncated_calls": truncated,
        "estimated_cost_usd": estimate_cost(calls[0]["model_resolved"] if calls else m.name, total_in, total_out),
        "model": {
            "requested": m.name,
            "resolved": calls[0]["model_resolved"] if calls else None,
            "provider": calls[0]["provider"] if calls else None,
            "system_fingerprint": calls[0]["system_fingerprint"] if calls else None,
            "seed": m.seed,
        },
        "salience_orchestration": rt.salience_orchestration,
        "speaking_order": base_keys,
        "calls": calls,
    }
    save_run_summary(summary, run_folder)
    return summary
