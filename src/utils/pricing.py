"""
src/utils/pricing.py - rough USD cost estimation for a run.

Prices are USD per 1M tokens (input, output), July 2026. Update as prices change;
matching is by loose substring on the resolved model name. Returns None for an
unknown model so cost is reported as null rather than wrong.
"""
PRICES = {
    "o4-mini":           (0.55, 2.20),
    "gpt-5.4-mini":      (0.75, 4.50),
    "gpt-5.4-nano":      (0.20, 1.25),
    "gpt-5.4":           (2.50, 15.0),
    "gpt-5.5":           (5.0, 30.0),
    "claude-haiku-4.5":  (1.0, 5.0),
    "claude-sonnet-4.6": (3.0, 15.0),
    "claude-sonnet-5":   (2.0, 10.0),
    "claude-opus-4.8":   (5.0, 25.0),
    # Audit judges (Section 8.4). Not part of the frozen jury; used only for the
    # post-hoc third/fourth-rater checks, which write to a separate scores file.
    # A price here does NOT mean the id is servable - this table is consulted only after
    # a call succeeds. `gemini-3.1-pro` sat here priced at (2.0, 12.0) and was not a real
    # model id at all: it was copied off a vendor price table, 404'd on first contact, and
    # is removed. Confirm an id with `check_judge_key.py --list`, which asks the endpoint
    # for its own catalogue, before adding a row. Avoid "-preview" and "-latest": a preview
    # model can change or vanish and an alias silently repoints, either of which breaks the
    # snapshot-pinning discipline of Section 6.4.
    "gemini-3.6-flash":  (1.50, 7.50),   # CONFIRMED - reachable, and billed in the Sec 8.4 audit
    "gemini-2.5-pro":    (1.25, 10.0),   # rate from the price list; id NOT yet confirmed on this key
    # Qwen3.6-27B is the OPEN-WEIGHT dense release. Alibaba's "Plus" and "Max" tiers are
    # proprietary hosted models, not open weights, and would defeat the purpose of the
    # fourth rater. Rate below is OpenRouter, July 2026; verify against your invoice.
    "qwen3.6-27b":       (0.289, 2.40),    # CONFIRMED - reachable, and billed in the Sec 8.4 audit
    "qwen3.6-35b-a3b":   (0.140, 0.900),  # MoE, ~3B active - cheaper, weaker at careful rubric work
    "stub":              (0.0, 0.0),
}

def price_for(model):
    """Return (input_price, output_price) per 1M tokens for a resolved model name.

    Matching is by LONGEST substring, not first hit. Two bugs are avoided by this:

      * order dependence - the previous version returned the first key contained in
        the model name, so 'gpt-5.4-mini-2026-03-17' priced correctly only because
        'gpt-5.4-mini' happened to sit above 'gpt-5.4' in the dict. Reordering the
        table, or inserting a new key, would silently mis-price by 3.3x.
      * reverse containment - the previous version also matched when the model name
        was contained in the KEY, so a bare 'gpt-5.4' matched 'gpt-5.4-mini' and was
        billed at mini rates, and a bare 'claude' matched whichever Claude came first.

    An unknown model still returns None, so cost is reported as null rather than wrong.
    """
    if not model:
        return None
    m = model.lower()
    best_key = None
    for key in PRICES:
        if key in m and (best_key is None or len(key) > len(best_key)):
            best_key = key
    return PRICES[best_key] if best_key else None

def estimate_cost(model, input_tokens, output_tokens):
    p = price_for(model)
    if not p:
        return None
    return round(input_tokens / 1e6 * p[0] + output_tokens / 1e6 * p[1], 4)


if __name__ == "__main__":
    # offline self-test: python src/utils/pricing.py
    CASES = [
        ("gpt-5.4-mini-2026-03-17", (0.75, 4.50)),   # the pinned generation/judge model
        ("gpt-5.4-mini",            (0.75, 4.50)),
        ("gpt-5.4",                 (2.50, 15.0)),   # must NOT fall through to mini
        ("gpt-5.4-2026-01-09",      (2.50, 15.0)),
        ("gpt-5.4-nano",            (0.20, 1.25)),
        ("claude-sonnet-5-20260420",(2.00, 10.0)),
        ("claude-sonnet-4.6",       (3.00, 15.0)),
        ("stub-1",                  (0.00, 0.00)),
        ("o4-mini-2025-04-16",      (0.55, 2.20)),
        ("claude",                  None),           # too vague to price: must be None
        ("gpt-6-mini",              None),           # unknown: must be None
    ]
    bad = [(m, price_for(m), exp) for m, exp in CASES if price_for(m) != exp]
    for m, got, exp in bad:
        print("FAIL %-26s got %s expected %s" % (m, got, exp))
    print("pricing self-test: %d/%d passed" % (len(CASES) - len(bad), len(CASES)))
    assert not bad
