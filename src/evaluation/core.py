"""
src/evaluation/core.py - adapted-DQI coding, outcome measures, floor metrics, and
a two-judge jury, applied to a completed run folder.

Design follows the supervisor-approved method note:
  * Quality: adapted DQI (0-2) on four judge-coded dimensions + individuation.
  * Outcome: agreement (binary), rounds, position movement per stakeholder.
  * Floor metrics: token share + speaking rank from logs (salience manip. check).
  * Two-judge jury; inter-judge agreement via quadratic weighted kappa.
Participation is measured from logs, not judge-coded (turn-taking is orchestrated).
"""
from __future__ import annotations
import json, re
from pathlib import Path

_ROUND = re.compile(r"^round(\d+)_(.+)$")

# --------------------------------------------------------------------------- #
# Codebook + judge prompts
# --------------------------------------------------------------------------- #
CODEBOOK = """You are coding a single contribution from one stakeholder in a simulated
organizational negotiation, using an adapted Discourse Quality Index. Score each
dimension on an ordinal 0-2 scale. Be strict and use the anchors.

justification_level  - how developed is the reasoning?
  0 = a bare assertion, no reason given
  1 = a reason is given but not fully developed or linked to the claim
  2 = a fully elaborated, logically linked justification

justification_content - what is the STRUCTURE of the appeal (not its sincerity)?
  0 = only the speaker's own outcomes are invoked
  1 = own interest is the primary justification, with INSTRUMENTAL reference to
      others or the whole ("securing our jobs secures the company's future" = 1,
      regardless of who says it)
  2 = the primary justification is a standard applied to ALL parties: explicit
      balancing of multiple parties' burdens and benefits, or appeal to a jointly
      held criterion (viability test, fairness rule) that could cut AGAINST the
      speaker. Tiebreaker: if the argument, as stated, could never require a
      sacrifice from the speaker, score at most 1.

respect - toward other parties and their arguments
  0 = dismissive, hostile, or ignores others' arguments
  1 = neutral or mixed
  2 = explicitly respectful and engages seriously with counter-arguments

constructive_politics - positional vs. solution-seeking
  0 = purely positional / entrenched
  1 = acknowledges the problem but offers no proposal
  2 = offers a mediating or consensual proposal

individuation - is this recognizably THIS stakeholder (anti-flattening check)?
  0 = generic; could be any stakeholder
  1 = somewhat role-specific
  2 = strongly distinctive to this stakeholder's role and interests

Return ONLY valid JSON, no markdown:
{"rationale":"one sentence","justification_level":0,"justification_content":0,"respect":0,"constructive_politics":0,"individuation":0}"""

def dqi_messages(role, contribution):
    sysp = "You are a careful, consistent discourse-quality coder. " + CODEBOOK
    user = ("STAKEHOLDER ROLE: %s\n\nCONTRIBUTION:\n%s\n\nWrite the one-sentence rationale first, "
            "then the scores, as JSON." % (role, contribution[:18000]))
    return [{"role": "system", "content": sysp}, {"role": "user", "content": user}]

def position_messages(role, first, last):
    sysp = ("You assess how far a stakeholder MOVED between its first and last contribution in a "
            "negotiation. Respond with ONLY JSON: "
            '{"rationale":"one sentence","position_move":0}. Scale: 0 = held firm / no real movement; '
            "1 = some movement or partial concession; 2 = substantial movement or concession.")
    user = ("STAKEHOLDER ROLE: %s\n\nFIRST CONTRIBUTION:\n%s\n\nLAST CONTRIBUTION:\n%s" %
            (role, first[:8000], last[:8000]))
    return [{"role": "system", "content": sysp}, {"role": "user", "content": user}]

def agreement_messages(synthesis):
    sysp = ("You judge the OUTCOME of a stakeholder negotiation from its final synthesis. Respond "
            "with ONLY JSON: "
            '{"rationale":"one sentence","agreement":true,'
            '"key_terms":[{"issue":"...","outcome":"one short sentence: where this issue ended"}]}. '
            "agreement is true only if the core contested issues were substantively resolved (not "
            "mere procedural politeness). key_terms lists the 3-5 most important contested issues "
            "and where each ended - agreed value, live proposal range, or unresolved standoff.")
    return [{"role": "system", "content": sysp},
            {"role": "user", "content": "FINAL SYNTHESIS / OUTCOME:\n%s" % synthesis[:16000]}]

def parse_json(text):
    clean = (text or "").strip().replace("```json", "").replace("```", "").strip()
    i, j = clean.find("{"), clean.rfind("}")
    if i != -1 and j != -1:
        clean = clean[i:j + 1]
    try:
        return json.loads(clean)
    except Exception:
        return {}

# --------------------------------------------------------------------------- #
# Stub judge (offline testing)
# --------------------------------------------------------------------------- #
class StubJudge:
    def __init__(self, name="stub", tilt=0):
        self.name = name; self.tilt = tilt
    def call(self, messages, label):
        from src.utils.llm import LLMResponse
        sysc = messages[0]["content"]
        if "agreement" in sysc.lower() and "position" not in sysc.lower():
            t = '{"rationale":"stub","agreement":false}'
        elif "MOVED" in sysc or "position_move" in sysc:
            t = '{"rationale":"stub","position_move":%d}' % (1 + self.tilt if self.tilt else 1)
        else:
            a = max(0, min(2, 1 + self.tilt))
            t = ('{"rationale":"stub","justification_level":%d,"justification_content":1,'
                 '"respect":1,"constructive_politics":0,"individuation":%d}' % (a, a))
        return LLMResponse(t, "stub", "stub", "stub-1", 10, "fp", 1, "stop", 0.0)

# --------------------------------------------------------------------------- #
# Weighted kappa (quadratic), categories 0..k-1
# --------------------------------------------------------------------------- #
def weighted_kappa(a, b, k=3):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    n = len(pairs)
    if n == 0:
        return None
    import itertools
    O = [[0] * k for _ in range(k)]
    for x, y in pairs:
        O[int(x)][int(y)] += 1
    ra = [sum(O[i]) for i in range(k)]
    ca = [sum(O[i][j] for i in range(k)) for j in range(k)]
    W = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]
    num = sum(W[i][j] * O[i][j] for i, j in itertools.product(range(k), range(k)))
    den = sum(W[i][j] * ra[i] * ca[j] / n for i, j in itertools.product(range(k), range(k)))
    if den == 0:
        return 1.0  # no expected disagreement (degenerate, e.g. identical constant scores)
    return round(1 - num / den, 3)

# --------------------------------------------------------------------------- #
# Read a completed run folder
# --------------------------------------------------------------------------- #
def _load_roles(run_folder):
    p = Path(run_folder) / "config_used.yaml"
    roles = {}
    if p.exists():
        import yaml
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        for s in d.get("stakeholders", []):
            roles[s["key"]] = "%s (%s)" % (s.get("name", s["key"]), s.get("role", ""))
    return roles

def segment_run(run_folder):
    rf = Path(run_folder)
    summ = json.loads((rf / "run_summary.json").read_text(encoding="utf-8"))
    keys = summ.get("speaking_order", [])
    outdir = rf / "outputs"
    contribs = {k: [] for k in keys}
    for f in sorted(outdir.glob("round*.txt")):
        m = _ROUND.match(f.stem)
        if not m:
            continue
        rnd, who = int(m.group(1)), m.group(2)
        if who in contribs:                       # excludes experts + moderator
            contribs[who].append((rnd, f.read_text(encoding="utf-8")))
    for k in contribs:
        contribs[k].sort()
    syn_f = outdir / "final_synthesis.txt"
    syn = syn_f.read_text(encoding="utf-8") if syn_f.exists() else ""
    return contribs, syn, summ

def floor_metrics(summ):
    keys = summ.get("speaking_order", [])
    tok = {k: 0 for k in keys}
    for c in summ.get("calls", []):
        m = _ROUND.match(c.get("label", ""))
        if m and m.group(2) in tok:
            tok[m.group(2)] += (c.get("output_tokens") or c.get("tokens") or 0)
    total = sum(tok.values()) or 1
    return {"token_share": {k: round(tok[k] / total, 3) for k in keys},
            "speaking_rank": {k: i + 1 for i, k in enumerate(keys)}}

# --------------------------------------------------------------------------- #
# Jury scoring
# --------------------------------------------------------------------------- #
_DIMS = ["justification_level", "justification_content", "respect", "constructive_politics", "individuation"]

class JudgeMeter:
    """Accumulates judge-side token usage so evaluation cost is logged, not guessed.

    The generation side has always priced itself (src/utils/pricing.estimate_cost);
    the judging side did not, which left roughly a third of the study's API spend
    without a receipt. This closes that gap: every jury call adds its token counts
    here, and the totals are written into evaluation.json and index.csv.
    """
    def __init__(self):
        self.per_judge = {}     # resolved model name -> {calls, input_tokens, output_tokens}
        self.calls = 0

    def record(self, response):
        model = getattr(response, "model_resolved", None) or getattr(response, "model_requested", "unknown")
        d = self.per_judge.setdefault(model, {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        d["calls"] += 1
        d["input_tokens"] += getattr(response, "input_tokens", 0) or 0
        d["output_tokens"] += getattr(response, "output_tokens", 0) or 0
        self.calls += 1

    def summary(self):
        from src.utils.pricing import estimate_cost
        per = {}
        total = 0.0
        unpriced = []
        for model, d in self.per_judge.items():
            c = estimate_cost(model, d["input_tokens"], d["output_tokens"])
            per[model] = dict(d, cost_usd=c)
            if c is None:
                unpriced.append(model)      # unknown model: report null rather than a wrong number
            else:
                total += c
        return {"per_judge": per,
                "total_calls": self.calls,
                "total_input_tokens": sum(d["input_tokens"] for d in self.per_judge.values()),
                "total_output_tokens": sum(d["output_tokens"] for d in self.per_judge.values()),
                "cost_usd": (None if unpriced else round(total, 4)),
                "unpriced_models": unpriced}


def _jury(judges, messages, label, meter=None):
    out = []
    for jd in judges:
        r = jd.call(messages, label)
        if meter is not None:
            meter.record(r)
        out.append(parse_json(r.text))
    return out

def evaluate_run(run_folder, judges, meter=None):
    meter = meter if meter is not None else JudgeMeter()
    contribs, syn, summ = segment_run(run_folder)
    roles = _load_roles(run_folder)
    per_judge_dim = {d: [[] for _ in judges] for d in _DIMS}   # for kappa
    dim_means = {d: [] for d in _DIMS}
    per_stakeholder = {}
    contribution_scores = []                                   # per-contribution record
    pos_moves = []

    for key, items in contribs.items():
        role = roles.get(key, key)
        s_dims = {d: [] for d in _DIMS}
        for rnd, text in items:
            scored = _jury(judges, dqi_messages(role, text), "dqi_%s_r%d" % (key, rnd), meter)
            rec = {"stakeholder": key, "round": rnd, "chars": len(text), "judges": []}
            for ji, sc in enumerate(scored):
                rec["judges"].append({d: sc.get(d) for d in _DIMS} |
                                     {"rationale": sc.get("rationale", "")})
            contribution_scores.append(rec)
            for d in _DIMS:
                vals = [s.get(d) for s in scored if isinstance(s.get(d), (int, float))]
                for ji, s in enumerate(scored):
                    per_judge_dim[d][ji].append(s.get(d))
                if vals:
                    m = sum(vals) / len(vals)
                    s_dims[d].append(m); dim_means[d].append(m)
        if len(items) >= 2:
            scored = _jury(judges, position_messages(role, items[0][1], items[-1][1]), "pos_%s" % key, meter)
            pv = [s.get("position_move") for s in scored if isinstance(s.get("position_move"), (int, float))]
            pm = sum(pv) / len(pv) if pv else None
        else:
            pm = None
        if pm is not None:
            pos_moves.append(pm)
        per_stakeholder[key] = {d: round(sum(s_dims[d]) / len(s_dims[d]), 3) if s_dims[d] else None for d in _DIMS}
        per_stakeholder[key]["position_move"] = round(pm, 3) if pm is not None else None

    ag = _jury(judges, agreement_messages(syn), "agreement", meter) if syn else []
    ag_bools = [bool(s.get("agreement")) for s in ag if "agreement" in s]
    agreement = (sum(ag_bools) / len(ag_bools) >= 0.5) if ag_bools else None
    key_terms = [{"judge": ji, "terms": s.get("key_terms", [])} for ji, s in enumerate(ag)]

    kappa = {}
    if len(judges) >= 2:
        for d in _DIMS:
            kappa[d] = weighted_kappa(per_judge_dim[d][0], per_judge_dim[d][1], k=3)
        kv = [v for v in kappa.values() if v is not None]
        kappa["mean"] = round(sum(kv) / len(kv), 3) if kv else None

    profile = {
        "run_folder": str(run_folder),
        "dqi": {d: (round(sum(dim_means[d]) / len(dim_means[d]), 3) if dim_means[d] else None) for d in _DIMS},
        "outcome": {
            "agreement": agreement,
            "rounds": summ.get("rounds_completed"),
            "convergence": summ.get("convergence_status"),
            "position_move_mean": round(sum(pos_moves) / len(pos_moves), 3) if pos_moves else None,
            "key_terms_per_judge": key_terms,
        },
        "floor": floor_metrics(summ),
        "per_stakeholder": per_stakeholder,
        "contribution_scores": contribution_scores,
        "inter_judge_kappa": kappa,
        "n_judges": len(judges),
        "judging_cost": meter.summary(),
    }
    return profile
