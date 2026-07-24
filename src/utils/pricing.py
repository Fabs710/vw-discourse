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
    "stub":              (0.0, 0.0),
}

def price_for(model):
    if not model:
        return None
    m = model.lower()
    for key, val in PRICES.items():
        if key in m or m in key:
            return val
    return None

def estimate_cost(model, input_tokens, output_tokens):
    p = price_for(model)
    if not p:
        return None
    return round(input_tokens / 1e6 * p[0] + output_tokens / 1e6 * p[1], 4)
