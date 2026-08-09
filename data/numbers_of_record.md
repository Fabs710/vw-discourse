# Numbers of record - generated 2026-08-09

Rule: **fix the text, never the table.** Regenerate with `python make_numbers_of_record.py`.

## corpus

```json
{
 "main_batch_runs": 129,
 "cross_model_runs": 9,
 "round_cap_runs": 3,
 "controlled_runs": 141,
 "validation_case_runs": 3,
 "programme_runs_generated": 177,
 "baseline_n": 10,
 "conditions_main_batch": 30
}
```

## baseline

```json
{
 "respect": {
  "mean": 1.575,
  "sd": 0.0779,
  "n": 10,
  "2sd": 0.1558
 },
 "justification_content": {
  "mean": 1.5081,
  "sd": 0.0644,
  "n": 10,
  "2sd": 0.1289
 },
 "position_movement": {
  "mean": 0.225,
  "sd": 0.0881,
  "n": 10,
  "2sd": 0.1762
 },
 "justification_level": {
  "mean": 1.9604,
  "sd": 0.0247,
  "n": 10,
  "2sd": 0.0495
 },
 "constructive_politics": {
  "mean": 1.9562,
  "sd": 0.0331,
  "n": 10,
  "2sd": 0.0662
 },
 "transcript_chars": {
  "mean": 144010.2,
  "sd": 17073.1752,
  "n": 10,
  "2sd": 34146.3504
 }
}
```

## screen_thresholds

```json
{
 "justification_content": {
  "order_band": 0.0429,
  "pooled_sd": 0.091,
  "se_3run": 0.0525,
  "band_over_se": 0.82
 },
 "respect": {
  "order_band": 0.0362,
  "pooled_sd": 0.0624,
  "se_3run": 0.036,
  "band_over_se": 1.0
 },
 "position_movement": {
  "order_band": 0.15,
  "pooled_sd": 0.1461,
  "se_3run": 0.0843,
  "band_over_se": 1.78
 },
 "red_line": {
  "order_band": 5.5333,
  "pooled_sd": 3.5934,
  "se_3run": 2.0747,
  "band_over_se": 2.67
 },
 "transcript_chars": {
  "order_band": 10627.6333,
  "pooled_sd": 16317.6519,
  "se_3run": 9421.0007,
  "band_over_se": 1.13
 }
}
```

## screen_effect_position_movement

```json
{
 "baseline": 0.225,
 "high": 0.4443,
 "effect": 0.2193,
 "exact_p_vs_baseline_posthoc": 0.014,
 "floor": 0.0035,
 "note": "screen verdict rests on the two pre-stated criteria; the p is a post-hoc robustness figure"
}
```

## session_test_respect

```json
{
 "original_mean": 1.5292,
 "confirmatory_mean": 1.6375,
 "delta": 0.1083,
 "p": 0.018,
 "control_delta": 0.0334,
 "control_p": 0.5159
}
```

## baseline_displacement_respect

```json
{
 "calibrated_mean": 1.5919,
 "n_calibrated": 27,
 "vs_layer_poles_series": {
  "perturbed_mean": 1.632,
  "n_perturbed": 24,
  "delta": 0.0401,
  "welch_t": 1.92,
  "history": "+0.102 (11 cal runs, Jul) -> +0.063 (16) -> this value (27); fixed comparison set = the eight layer-pole conditions"
 },
 "vs_all_perturbed": {
  "perturbed_mean": 1.6637,
  "n_perturbed": 102,
  "delta": 0.0718,
  "welch_t": 4.19,
  "note": "drill sweeps included; moderate-magnitude conditions also sit above the calibrated point"
 }
}
```

## round_cap

```json
{
 "respect": {
  "r4": 1.575,
  "r6": 1.713,
  "delta": 0.138,
  "p": 0.0175
 },
 "position_movement": {
  "r4": 0.225,
  "r6": 0.4167,
  "delta": 0.1917,
  "p": 0.014
 },
 "transcript_chars": {
  "r4": 144010.2,
  "r6": 236838.0,
  "delta": 92827.8,
  "p": 0.0035
 }
}
```

## cross_model

```json
{
 "floor": 0.0035,
 "respect": {
  "mini": 1.575,
  "sonnet": 1.7847,
  "delta": 0.2097,
  "p": 0.0035
 },
 "position_movement": {
  "mini": 0.225,
  "sonnet": 0.8887,
  "delta": 0.6637,
  "p": 0.0035
 },
 "experts": {
  "mini": 1.8,
  "sonnet": 0.0,
  "delta": -1.8,
  "p": 0.014
 },
 "red_line": {
  "mini": 11.2,
  "sonnet": 6.6667,
  "delta": -4.5333,
  "p": 0.049
 },
 "justification_content": {
  "mini": 1.5081,
  "sonnet": 1.5763,
  "delta": 0.0682,
  "p": 0.0944
 },
 "justification_level": {
  "mini": 1.9604,
  "sonnet": 2.0,
  "delta": 0.0396,
  "p": 0.0385
 },
 "constructive_politics": {
  "mini": 1.9562,
  "sonnet": 1.993,
  "delta": 0.0368,
  "p": 0.0944
 },
 "individuation": {
  "mini": 2.0,
  "sonnet": 2.0,
  "delta": 0.0,
  "p": 1.0
 },
 "transcript_chars": {
  "mini": 144010.2,
  "sonnet": 150405.0,
  "delta": 6394.8,
  "p": 0.5455
 },
 "tokens": {
  "mini": 438431.7,
  "sonnet": 685540.3333,
  "delta": 247108.6333,
  "p": 0.0035
 },
 "gen_cost": {
  "mini": 0.4593,
  "sonnet": 1.935,
  "delta": 1.4757,
  "p": 0.0035
 },
 "position_sweep_contrast": {
  "mini": 0.2777,
  "sonnet": 0.139
 }
}
```

## jury

```json
{
 "kappa_median": 0.477,
 "kappa_mean": 0.455,
 "n": 129,
 "at_or_below_fair_041": 55,
 "substantial_061_plus": 23
}
```

## variance_census

```json
{
 "respect": {
  "sd": 0.0747,
  "distinct": 19,
  "min": 1.438,
  "max": 1.812,
  "at_2.0": 0
 },
 "justification_content": {
  "sd": 0.0868,
  "distinct": 21,
  "min": 1.292,
  "max": 1.729,
  "at_2.0": 0
 },
 "constructive_politics": {
  "sd": 0.0366,
  "distinct": 10,
  "min": 1.812,
  "max": 2.0,
  "at_2.0": 34
 },
 "justification_level": {
  "sd": 0.0177,
  "distinct": 5,
  "min": 1.917,
  "max": 2.0,
  "at_2.0": 17
 },
 "individuation": {
  "sd": 0.0048,
  "distinct": 2,
  "min": 1.979,
  "max": 2.0,
  "at_2.0": 122
 },
 "red_line": {
  "sd": 3.9147,
  "distinct": 18,
  "min": 1.0,
  "max": 19.0,
  "at_2.0": 1
 }
}
```

## verbosity_rho

```json
{
 "respect": 0.226,
 "justification_content": 0.206
}
```

## audit_scope_A

```json
{
 "n_items": 28,
 "cost_usd": 0.2607,
 "pairs": {
  "gemini-3.6-flash vs qwen/qwen3.6-27b": {
   "justification_level": {
    "kappa": 0.0,
    "exact": 0.964
   },
   "justification_content": {
    "kappa": 0.286,
    "exact": 0.643
   },
   "respect": {
    "kappa": 0.462,
    "exact": 0.857
   },
   "constructive_politics": {
    "kappa": null,
    "exact": 1.0
   },
   "individuation": {
    "kappa": null,
    "exact": 1.0
   },
   "mean_kappa": 0.249
  },
  "gemini-3.6-flash vs HUMAN": {
   "justification_level": {
    "kappa": null,
    "exact": 1.0
   },
   "justification_content": {
    "kappa": 0.071,
    "exact": 0.536
   },
   "respect": {
    "kappa": 0.5,
    "exact": 0.821
   },
   "constructive_politics": {
    "kappa": 0.0,
    "exact": 0.786
   },
   "individuation": {
    "kappa": 0.0,
    "exact": 0.964
   },
   "mean_kappa": 0.143
  },
  "qwen/qwen3.6-27b vs HUMAN": {
   "justification_level": {
    "kappa": 0.0,
    "exact": 0.964
   },
   "justification_content": {
    "kappa": 0.172,
    "exact": 0.607
   },
   "respect": {
    "kappa": 0.462,
    "exact": 0.75
   },
   "constructive_politics": {
    "kappa": 0.0,
    "exact": 0.786
   },
   "individuation": {
    "kappa": 0.0,
    "exact": 0.964
   },
   "mean_kappa": 0.127
  }
 },
 "usable": {
  "gemini-3.6-flash": 1.0,
  "qwen/qwen3.6-27b": 1.0
 }
}
```

## costs

```json
{
 "generation_controlled_batches": 79.69,
 "judging_logged_controlled": 13.23,
 "audit_scopes_BC": 5.39
}
```

## hand_entered

```json
{
 "_rule": "each value names its source; change it only by changing the source",
 "gm_fidelity": {
  "value": "1.62 of 2 across ten pre-specified claims",
  "source": "doc 14, Sec 9.7"
 },
 "legibility": {
  "value": "independent model recovers the intended band",
  "source": "doc 12, Sec 5.6"
 },
 "human_check_v2": {
  "kappa_content_v2": ".88 (Claude) / .56 (GPT)",
  "kappa_respect": ".50 (GPT) / .31 (Claude)",
  "source": "doc 14, Sec 8.5; data/human_codes.json + evaluation.json (judge order: GPT first). Attribution swap corrected 2 Aug - respect/constructive columns carried each other's values in the pre-correction table; content v2 was always right because the rejudge script ran Claude-first."
 },
 "generation_total_appH": {
  "value": "$88.69 across 177 generated runs",
  "source": "Appendix H (doc 17)"
 },
 "judging_logged_appH": {
  "value": "$15.71 across 62 instrumented runs",
  "source": "Appendix H"
 },
 "pre_instrumentation_estimate": {
  "value": "~$22 (estimate on known call volume)",
  "source": "Appendix H"
 },
 "audit_total": {
  "value": "$5.65 ($0.26 sample + $5.39 scopes B/C)",
  "source": "Appendix H + audit log"
 },
 "project_total": {
  "value": "~$132",
  "source": "Appendix H"
 },
 "confirmed_drill_effects": {
  "value": "4 of 20 contrasts at p<=0.05 (three substantive respect effects + one transcript-length contrast); no chance benchmark attached - the sweeps were selected on exploratory extremes (Sec 9.5.2); strongest belief/respect +0.073 p=.0087",
  "source": "doc 16, Sec 9.5"
 }
}
```

## judge_offsets

```json
{
 "main_batch": {
  "justification_level": {
   "mean_offset_openai_minus_anthropic": 0.0194,
   "n_records": 3094
  },
  "justification_content": {
   "mean_offset_openai_minus_anthropic": 0.2847,
   "n_records": 3094
  },
  "respect": {
   "mean_offset_openai_minus_anthropic": 0.148,
   "n_records": 3094
  },
  "constructive_politics": {
   "mean_offset_openai_minus_anthropic": 0.0304,
   "n_records": 3094
  },
  "individuation": {
   "mean_offset_openai_minus_anthropic": -0.0016,
   "n_records": 3094
  }
 },
 "cross_model_batch": {
  "justification_level": {
   "mean_offset_openai_minus_anthropic": -0.0046,
   "n_records": 216
  },
  "justification_content": {
   "mean_offset_openai_minus_anthropic": 0.3472,
   "n_records": 216
  },
  "respect": {
   "mean_offset_openai_minus_anthropic": 0.1111,
   "n_records": 216
  },
  "constructive_politics": {
   "mean_offset_openai_minus_anthropic": 0.0046,
   "n_records": 216
  },
  "individuation": {
   "mean_offset_openai_minus_anthropic": 0,
   "n_records": 216
  }
 },
 "note": "judges[0]=OpenAI, judges[1]=Anthropic (build order, core.py); positive = OpenAI more lenient. Sign error corrected 29 Jul."
}
```
