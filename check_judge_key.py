"""
check_judge_key.py - one API call, to prove a judge model is reachable before you
spend anything on a scoring pass.

Checks, in order, and stops at the first failure with a message that says what to fix:
  1. the key and base URL the client would use for this model
  2. that the endpoint answers at all
  3. that the model returns PARSEABLE JSON against the real DQI rubric shape - the
     failure mode that matters for an open-weight judge, because the evaluation path
     silently records an unparseable reply as a null score

Do not invent model ids. `--list` asks the endpoint for its own catalogue; that is the
only authoritative source. An id copied from a vendor pricing page or a blog post can
404 - which is exactly how this script came to exist, after `gemini-3.1-pro` was
guessed from a price table and turned out not to be servable.

Usage:
    python check_judge_key.py --list                 ask Google what it serves
    python check_judge_key.py --list qwen/qwen3.6-27b   ask OpenRouter what it serves
    python check_judge_key.py gemini-3.6-flash
    python check_judge_key.py qwen/qwen3.6-27b
    python check_judge_key.py qwen/qwen3.6-27b gemini-3.6-flash
"""
import sys, json

from src.evaluation.core import parse_json, dqi_messages
from src.utils.llm import LLMClient, detect_provider, _compatible_entry, MissingAPIKey
from src.utils.pricing import price_for

DIMS = ["justification_level", "justification_content", "respect",
        "constructive_politics", "individuation"]

# Probe with the REAL codebook prompt, not a short stand-in. A model can handle a
# two-line instruction and still fail on the full rubric, which is the prompt it will
# actually receive; a check that passes on an easier prompt than the job would be
# worse than no check.
PROBE = dqi_messages(
    "Works Council (employee representation)",
    "We cannot accept plant closures. But if management can show the capacity numbers, we are "
    "willing to discuss working-time reductions as an alternative, provided job security is "
    "guaranteed in writing for the affected sites.")


def check(model):
    print("\n=== %s ===" % model)
    provider = detect_provider(model)
    entry = _compatible_entry(model)
    print("  provider   : %s" % provider)
    print("  key from   : %s" % (entry[1] if entry else
                                 ("OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY")))
    print("  price/1M   : {}".format(price_for(model) or "UNKNOWN - cost will log as null"))
    if price_for(model) is None:
        print("  ! add this model to src/utils/pricing.py or its cost cannot be recorded")

    client = LLMClient(model, 0.0, 20260714, 1024)
    try:
        r = client.call(PROBE, "keycheck")
    except MissingAPIKey as e:
        print("  RESULT     : NOT CONFIGURED - %s" % e)
        return False
    except Exception as e:
        print("  RESULT     : CALL FAILED - %s: %s" % (type(e).__name__, e))
        print("               check the base URL, the model id spelling, and that the account has credit")
        return False

    print("  resolved   : %s" % r.model_resolved)
    print("  tokens     : %d in / %d out" % (r.input_tokens, r.output_tokens))
    p = price_for(model)
    if p:
        print("  this call  : ${:.6f}".format(r.input_tokens / 1e6 * p[0] + r.output_tokens / 1e6 * p[1]))

    parsed = parse_json(r.text)
    missing = [d for d in DIMS if not isinstance(parsed.get(d), (int, float))]
    if not parsed:
        print("  RESULT     : UNPARSEABLE - the reply was not JSON. Raw reply below.")
        print("               " + (r.text or "")[:300].replace("\n", "\n               "))
        return False
    if missing:
        print("  RESULT     : PARTIAL - JSON returned but missing/non-numeric: %s" % ", ".join(missing))
        print("               usable, but expect nulls; watch the usable-output rate in the audit scripts")
        return False
    print("  scores     : %s" % {d: parsed[d] for d in DIMS})
    print("  RESULT     : OK - reachable, priced, and returns a complete parseable score")
    return True


def list_models(probe_model="gemini-3.6-flash"):
    """Ask the endpoint what it actually serves. A 404 on a model id means the id is
    wrong, and guessing again is the wrong response - the catalogue is authoritative."""
    client = LLMClient(probe_model, 0.0, 20260714, 64)
    entry = _compatible_entry(probe_model)
    inner = client._compatible_client() if entry else client._openai_client()
    print("\nModels served by the endpoint for %r:" % probe_model)
    try:
        names = sorted(m.id for m in inner.models.list())
    except Exception as e:
        print("   could not list: %s: %s" % (type(e).__name__, e))
        return
    for n in names:
        print("   " + n)
    print("   (%d models)" % len(names))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--list"]:
        list_models(sys.argv[2] if len(sys.argv) > 2 else "gemini-3.6-flash")
        sys.exit(0)
    models = sys.argv[1:] or ["gemini-3.6-flash"]
    ok = [check(m) for m in models]
    print("\n%d of %d judge model(s) ready." % (sum(ok), len(ok)))
    sys.exit(0 if all(ok) else 1)
