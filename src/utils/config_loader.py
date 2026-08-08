"""
src/utils/config_loader.py — load and validate the simulation config.

Reads simulation_config.yaml into a validated SimulationConfig: model settings,
roundtable settings, and a {key: Stakeholder} map built through the Pydantic
model (so a malformed config fails fast with a clear error). Long text fields are
condensed to a few sentences before use to keep prompts bounded; the raw config
is retained for the run record.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

from src.models.stakeholder import Stakeholder

MAX_SENTENCES = 5
_TEXT_FIELDS = (
    "core_interests", "background", "red_lines",
    "persuasive_triggers", "sensitive_triggers", "additional_context",
)


def _condense(text: Optional[str], max_sentences: int = MAX_SENTENCES) -> Optional[str]:
    if not text:
        return text
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:max_sentences]).strip()


class ModelSettings(BaseModel):
    name: str = "gpt-4o"
    temperature: float = 0.7
    seed: int = 20260714
    max_tokens: int = 2048


class RoundtableSettings(BaseModel):
    max_rounds: int = 4
    max_summons: int = 2
    min_rounds_before_synthesis: int = 2
    salience_orchestration: bool = True   # light-touch: salience sets speaking order
    turn_order: list[str] = Field(min_length=1)


@dataclass
class SimulationConfig:
    model: ModelSettings
    roundtable: RoundtableSettings
    validation_mode: bool
    scenario_path_abs: Path
    stakeholders: dict[str, Stakeholder]
    raw: dict = field(default_factory=dict)

    def get_stakeholder(self, key: str) -> Optional[Stakeholder]:
        return self.stakeholders.get(key)

    def get_scenario_text(self) -> str:
        return self.scenario_path_abs.read_text(encoding="utf-8")


def load_config(path: str | Path) -> SimulationConfig:
    path = Path(path).resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    model = ModelSettings(**(raw.get("model") or {}))
    roundtable = RoundtableSettings(**(raw.get("roundtable") or {}))
    validation_mode = bool(raw.get("validation_mode", False))

    # Scenario path is relative to the project root (config file's parent-parent).
    project_root = path.parent.parent
    scenario_path_abs = (project_root / raw["scenario_path"]).resolve()

    # Build validated stakeholders keyed by their config key.
    stakeholders: dict[str, Stakeholder] = {}
    for entry in raw.get("stakeholders", []):
        data = dict(entry)
        key = data.pop("key", None)
        if not key:
            raise ValueError("Each stakeholder entry needs a unique 'key'.")
        for f in _TEXT_FIELDS:
            if f in data:
                data[f] = _condense(data[f])
        stakeholders[key] = Stakeholder(**data)   # Pydantic validates here

    # turn_order must reference known keys.
    unknown = [k for k in roundtable.turn_order if k not in stakeholders]
    if unknown:
        raise ValueError(f"turn_order references unknown stakeholder keys: {unknown}")

    return SimulationConfig(
        model=model,
        roundtable=roundtable,
        validation_mode=validation_mode,
        scenario_path_abs=scenario_path_abs,
        stakeholders=stakeholders,
        raw=raw,
    )
