# Parameter drill-down analysis (Section 9.5)

Batch `sensitivity_20260726_172041` - 9 runs across 3 conditions.

## 1. Are the screening thresholds usable?

| metric | pooled within-condition SD | SE of a 3-run mean | order-noise band | band / SE |
|---|---|---|---|---|

A usable screening band sits well above the standard error of a condition mean. Where it does not, the screen will over-fire on that metric.

## 2. Within-sweep contrasts (high minus low, same batch, baseline offset cancels)

- **5 contrasts at 3 vs 3 runs.** Exact floor p = 0.1, so conventional significance is UNREACHABLE at this arm size. 1 reach the floor (chance would give about 0.5).

| family | sweep | layer | metric | high | low | contrast | p (exact) |
|---|---|---|---|---|---|---|---|
| layer | Position layer (all stakeholders) | position | respect | 1.8123 | 1.736 | +0.0763 ** | 0.1 |
| layer | Position layer (all stakeholders) | position | transcript length | 148423.3333 | 132915.3333 | +15508.0 | 0.3 |
| layer | Position layer (all stakeholders) | position | position movement | 0.861 | 0.722 | +0.139 | 0.6 |
| layer | Position layer (all stakeholders) | position | red-line declarations | 3.3333 | 3.6667 | -0.3333 | 1.0 |
| layer | Position layer (all stakeholders) | position | justification content | 1.5067 | 1.5347 | -0.028 | 1.0 |

## 3. Baseline displacement

Clean comparison - calibrated configuration vs layer-perturbed, both from the screen batch:

| metric | calibrated | perturbed | delta | Welch t |
|---|---|---|---|---|
| justification content | 1.5763 | 1.5207 | -0.0557 | -1.48 |
| respect | 1.7847 | 1.7742 | -0.0105 | -0.38 |
| position movement | 0.8887 | 0.7915 | -0.0972 | -0.42 |
| red-line declarations | 6.6667 | 3.5 | -3.1667 | -2.94 |
| transcript length | 150405.0 | 140669.3333 | -9735.6667 | -1.77 |

Pole symmetry (does the direction of the perturbation matter?):

| metric | calibrated | all high poles | all low poles |
|---|---|---|---|
| justification content | 1.5763 | 1.5067 | 1.5347 |
| respect | 1.7847 | 1.8123 | 1.736 |
| position movement | 0.8887 | 0.861 | 0.722 |
| red-line declarations | 6.6667 | 3.3333 | 3.6667 |
| transcript length | 150405.0 | 148423.3333 | 132915.3333 |

## 4. Variance census - which dependent variables carry information

| variable | min | max | SD | distinct values |
|---|---|---|---|---|
| dqi_justif_content | 1.458 | 1.667 | 0.0711 | 7 |
| dqi_respect | 1.708 | 1.833 | 0.0429 | 6 |
| position_move | 0.5 | 1.25 | 0.2988 | 5 |
| red_line_declarations | 1.0 | 8.0 | 2.3511 | 5 |
| transcript_chars | 124183.0 | 160658.0 | 11191.2543 | 9 |
| dqi_justif_level | 1.979 | 2.0 | 0.007 | 2 |
| dqi_constructive | 1.938 | 2.0 | 0.0208 | 4 |
| dqi_individuation | 2.0 | 2.0 | 0.0 | 1 |
| rounds | 4.0 | 4.0 | 0.0 | 1 |
| experts | 0.0 | 1.0 | 0.3333 | 2 |
| agreement | - | - | - | 0/9 True |