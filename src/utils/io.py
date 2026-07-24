"""
src/utils/io.py — output and log helpers for a run.

A run writes plain-text agent outputs and JSON log records into a per-run folder
under data/. build_conversation_text renders the running transcript that is fed
back to agents each turn.
"""

from __future__ import annotations
import json
from pathlib import Path


def _safe(label: str) -> str:
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in label)[:80]


def save_output(text: str, label: str, run_folder: str | Path) -> str:
    folder = Path(run_folder) / "outputs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{_safe(label)}.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


def save_log(data: dict, label: str, run_folder: str | Path) -> str:
    folder = Path(run_folder) / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{_safe(label)}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def save_run_summary(summary: dict, run_folder: str | Path) -> str:
    path = Path(run_folder) / "run_summary.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def build_conversation_text(history: list[dict]) -> str:
    """Render a list of turn dicts ({agent_label, content, round}) as readable text."""
    parts = []
    for e in history:
        label = e.get("agent_label", e.get("agent", "?"))
        rnd = e.get("round")
        header = f"[{label}" + (f" — Round {rnd}]" if rnd is not None else "]")
        parts.append(f"{header}\n{e.get('content', '').strip()}")
    return "\n\n".join(parts)
