# VW Discourse Simulation

LLM-based multi-agent simulation of a contested corporate decision — Volkswagen's
2024 "Zukunft Volkswagen" restructuring confrontation — for the master's thesis
*Parameterizing the Stakeholder: A Theory-Grounded Framework for Simulating Organizational
Deliberation with Large Language Models* (WU Vienna, 2026).

The engine implements the thesis's layered parameter framework (BDI spine + four
functional layers: salience, motivation, position, interaction) with rounds, expert
summoning, a convergence monitor, a neutral moderator and a structured synthesis.
Every number reported in the thesis regenerates from this repository: see
`make_numbers_of_record.py` (the reconciliation table), the `analyze_*.py` scripts,
and the `make_fig*.py` figure generators. Licensed under the MIT License (see LICENSE);
the run data in `data/` is included for verification.

## Key decisions (this build)
- **Case:** Volkswagen "Zukunft Volkswagen" 2024 restructuring / collective-bargaining confrontation (core sensitivity case). A separate, smaller case is used for validation.
- **Scenario framing:** *leaner*, presented as a live decision — the real outcome is withheld, to avoid steering the agents toward the documented result.
- **Models:** OpenAI primary now, behind a provider abstraction so Claude (Anthropic) slots in for the cross-model comparison.
- **Salience in orchestration:** light architectural weighting of turn priority and synthesis by salience, so `power` is not merely a prompt attribute.
- **Evaluation:** LLM-as-judge with an LLM-coded Discourse Quality Index (DQI); two judge models (Claude + GPT) whose judgments are compared (inter-judge agreement).
- **Reproducibility:** fixed seed, logged `system_fingerprint`, pinned model snapshot per run.

## Layout
```
src/models/stakeholder.py    parameter model (layered framework; conflict mode derived)
src/utils/llm.py             provider abstraction (OpenAI/Anthropic) + reproducibility
src/utils/config_loader.py   YAML -> validated Stakeholders
src/utils/prompt_builder.py  documented slider->verbal operationalisation + agent brief
src/utils/state_manager.py   runtime state + re-grounding
src/utils/io.py              logging / output
src/engines/roundtable.py    rounds, summoning, convergence, moderator, synthesis
config/simulation_config.yaml
prompts/scenario.txt
run.py                       entry point
run_sensitivity.py           sensitivity analysis + order-robustness harness
```

## Privacy
Keep this repository **private until after grading** (per supervisor). Secrets live in
`.env` (gitignored); copy `.env.example` to `.env` and fill in your keys.

## Run
```
python -m venv venv && venv\Scripts\activate      # (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env                            # then add OPENAI_API_KEY (+ ANTHROPIC_API_KEY)
python run.py
```
