"""
run.py — entry point for a single roundtable simulation.

Usage:
    python run.py                         # uses config/simulation_config.yaml
    python run.py path/to/config.yaml
"""

from __future__ import annotations
import sys
import datetime
from pathlib import Path

from src.utils.config_loader import load_config
from src.engines.roundtable import run_roundtable


def main(config_path: str = "config/simulation_config.yaml") -> None:
    cfg = load_config(config_path)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = str(Path("data") / f"run_{timestamp}")
    print(f"Running roundtable — model={cfg.model.name}, run_folder={run_folder}")
    summary = run_roundtable(cfg, timestamp, run_folder)
    print(f"Done. Rounds: {summary['rounds_completed']} | in/out tokens: {summary['input_tokens']}/{summary['output_tokens']} "
          f"| est. cost: ${summary['estimated_cost_usd']} | truncated calls: {summary['truncated_calls']} "
          f"| convergence: {summary['convergence_status']}")
    print(f"Outputs in: {run_folder}")


if __name__ == "__main__":
    main(*sys.argv[1:])
