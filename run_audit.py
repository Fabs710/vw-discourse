"""
run_audit.py - run the whole independent-judge audit unattended.

Why a driver rather than a chain of shell commands
--------------------------------------------------
Overnight means nobody is watching. Three things follow. A failed step must STOP the
sequence rather than let later steps run on missing input; every step's output has to
land in a log that can be read in the morning; and steps that have already succeeded
must be skipped, so re-running after a failure costs nothing and repeats nothing.
`cmd1; cmd2` in PowerShell gives none of that - it runs everything regardless of
failure. `cmd1 && cmd2` gives the first but not the other two, and only on
PowerShell 7+.

The expensive steps run first. Scoring costs money; the four analyses are free and
idempotent, so a failure there loses nothing.

Usage
-----
    python run_audit.py --dry      rehearse with stub judges, no API calls, no cost
    python run_audit.py            the real thing
    python run_audit.py            (again, after a failure - completed steps are skipped)

Everything is written to audit_log_<timestamp>.txt beside this file.
"""
import argparse, json, subprocess, sys, time
from datetime import datetime
from pathlib import Path

CROSS = "data/sensitivity_20260726_172041"      # scope B: the cross-model batch
MAIN  = "data/sensitivity_20260723_000046"      # scope C: the stratified ten
TEN = ("main,main_recheck_r1,order_reversed,order_random,layer_salience_low,"
       "layer_motivation_high,layer_position_high,layer_interaction_low,"
       "igmetall_flexibility_high_r1,mgmt_relational_prior_high_r1")

JUDGES = [("gemini-3.6-flash", "_audit_gemini", "Gemini"),
          ("qwen/qwen3.6-27b", "_audit_qwen",   "Qwen")]


def steps(dry):
    """(label, argv, batch, suffix, costs_money). Scoring first, analysis after.

    A dry run writes to its OWN suffix. The first version of this driver did not, and a
    rehearsal overwrote real scored files with stub scores in the live batch folders -
    destroying paid-for data and, worse, leaving files that the resume check would then
    read as 'already scored', so the live run would have skipped the work entirely. A
    rehearsal must never be able to touch what the real run produces.
    """
    out = []
    for model, suffix, label in JUDGES:
        eff = suffix + ("_DRY" if dry else "")
        for batch, only, scope in ((CROSS, None, "B"), (MAIN, TEN, "C")):
            cmd = [sys.executable, "evaluate.py", batch, "--judges", model, "--suffix", eff]
            if only:
                cmd += ["--only", only]
            if dry:
                cmd += ["--dry"]
            out.append(("score  scope %s  %-16s" % (scope, label), cmd, batch, eff, not dry))
    for model, suffix, label in JUDGES:
        eff = suffix + ("_DRY" if dry else "")
        for batch, scope in ((CROSS, "B"), (MAIN, "C")):
            out.append(("analyse scope %s  %-16s" % (scope, label),
                        [sys.executable, "analyze_audit_judge.py", batch,
                         "--suffix", eff, "--label", label],
                        batch, eff, False))
    return out


def clean_dry_artifacts():
    """Remove everything a previous --dry left behind, so a rehearsal leaves no trace."""
    n = 0
    for batch in (CROSS, MAIN):
        for pat in ("*/evaluation_audit_*_DRY.json", "audit_judge_analysis_*_DRY.json"):
            for f in Path(batch).glob(pat):
                f.unlink(); n += 1
    return n


def outstanding(batch, suffix, only):
    """Which runs this step targets that do NOT yet carry their audit file.

    Resume is per-RUN, not per-step. An all-or-nothing check would re-score all nine
    runs of a batch because one was missing, which costs money and rewrites results
    that were already paid for. It also means a run interrupted halfway resumes from
    where it stopped rather than from the beginning.
    """
    root = Path(batch)
    if not root.exists():
        return []
    if only:
        names = [s.strip() for s in only.split(",") if s.strip()]
    else:
        names = sorted(p.name for p in root.iterdir()
                       if p.is_dir() and (p / "run_summary.json").exists())
    return [n for n in names if not (root / n / ("evaluation%s.json" % suffix)).exists()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="stub judges, no API calls, no cost")
    ap.add_argument("--force", action="store_true", help="re-score even where audit files exist")
    a = ap.parse_args()

    log = Path("audit_log_%s.txt" % datetime.now().strftime("%Y%m%d_%H%M%S"))
    plan = steps(a.dry)

    def say(msg=""):
        print(msg, flush=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")

    say("Independent judge audit - %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    say("%d steps. Scoring runs first; the four analyses are free and idempotent." % len(plan))
    say("Log: %s" % log.name)
    say("DRY RUN - stub judges, no API calls" if a.dry else "LIVE - this spends money")
    say("=" * 78)

    t0 = time.time()
    done = skipped = 0
    for i, (label, cmd, batch, suffix, costs) in enumerate(plan, 1):
        is_score = "score" in label
        if is_score and not a.force:
            only = cmd[cmd.index("--only") + 1] if "--only" in cmd else None
            todo = outstanding(batch, suffix, only)
            total_targets = len([s for s in (only or "").split(",") if s.strip()]) or \
                            len([p for p in Path(batch).iterdir()
                                 if p.is_dir() and (p / "run_summary.json").exists()])
            if not todo:
                say("\n[%d/%d] %s  SKIPPED - all %d run(s) already scored"
                    % (i, len(plan), label, total_targets))
                skipped += 1
                continue
            if len(todo) < total_targets:
                say("\n[%d/%d] %s  RESUMING - %d of %d run(s) still to score"
                    % (i, len(plan), label, len(todo), total_targets))
                # narrow the command to exactly what is missing
                if "--only" in cmd:
                    cmd[cmd.index("--only") + 1] = ",".join(todo)
                else:
                    cmd += ["--only", ",".join(todo)]
        say("\n[%d/%d] %s  %s" % (i, len(plan), label, datetime.now().strftime("%H:%M:%S")))
        say("        " + " ".join(cmd[1:]))
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        for line in (r.stdout or "").splitlines():
            say("        " + line)
        if r.returncode != 0:
            say("\n!! STEP FAILED with exit code %d. Stopping - later steps would run on" % r.returncode)
            say("!! missing input. Nothing after this point has been attempted.")
            for line in (r.stderr or "").splitlines()[-15:]:
                say("        " + line)
            say("\nFix the cause and re-run: completed steps are detected and skipped.")
            say("Log: %s" % log.name)
            sys.exit(1)
        done += 1

    # ---- cost summary, read back from what was actually written ----
    say("\n" + "=" * 78)
    total = 0.0
    for model, suffix, label in JUDGES:
        sub = 0.0
        for batch in (CROSS, MAIN):
            for f in Path(batch).glob("*/evaluation%s.json" % suffix):
                try:
                    sub += (json.loads(f.read_text(encoding="utf-8"))
                            .get("judging_cost", {}).get("cost_usd", 0) or 0)
                except Exception:
                    pass
        say("  %-18s $%.4f" % (label, sub))
        total += sub
    say("  %-18s $%.4f" % ("TOTAL", total))
    if a.dry:
        n = clean_dry_artifacts()
        say("\n  rehearsal cleaned up: %d _DRY file(s) removed, live data untouched" % n)
    say("\n%d step(s) run, %d skipped, %.1f minutes." % (done, skipped, (time.time() - t0) / 60))
    say("index.csv and every reported score are untouched - all writes went to")
    say("evaluation_audit_*.json and audit_judge_analysis_*.json.")
    say("\nSend the four 'analyse' blocks in %s for the write-up." % log.name)


if __name__ == "__main__":
    main()
