# Parameter drill-down analysis (Section 9.5)

Batch `sensitivity_20260723_000046` - 129 runs across 30 conditions.

## 1. Are the screening thresholds usable?

| metric | pooled within-condition SD | SE of a 3-run mean | order-noise band | band / SE |
|---|---|---|---|---|
| justification content | 0.091 | 0.0525 | 0.0429 | 0.82  **<- band is BELOW run-to-run noise** |
| respect | 0.0624 | 0.036 | 0.0362 | 1.0 |
| position movement | 0.1461 | 0.0843 | 0.15 | 1.78 |
| red-line declarations | 3.5934 | 2.0747 | 5.5333 | 2.67 |
| transcript length | 16317.6519 | 9421.0007 | 10627.6333 | 1.13 |

A usable screening band sits well above the standard error of a condition mean. Where it does not, the screen will over-fire on that metric.

## 2. Within-sweep contrasts (high minus low, same batch, baseline offset cancels)

- **45 contrasts at 3 vs 3 runs.** Exact floor p = 0.1, so conventional significance is UNREACHABLE at this arm size. 4 reach the floor (chance would give about 4.5).
- **20 contrasts at 6 vs 6 runs.** Exact floor p = 0.00216; significance at 0.05 IS attainable. 4 contrasts reach p <= 0.05 (chance would give about 1.0).

| family | sweep | layer | metric | high | low | contrast | p (exact) |
|---|---|---|---|---|---|---|---|
| drill | Management relational prior | belief | respect | 1.7085 | 1.6355 | +0.073 | 0.0087 |
| drill | Works council cooperativeness | interaction | transcript length | 166970.5 | 147172.8333 | +19797.6667 | 0.013 |
| drill | Works council cooperativeness | interaction | respect | 1.7222 | 1.6458 | +0.0763 | 0.0455 |
| drill | IG Metall flexibility | position | respect | 1.7327 | 1.6492 | +0.0835 | 0.0498 |
| layer | Interaction layer (all stakeholders) | interaction | transcript length | 155454.0 | 129818.3333 | +25635.6667 | 0.1 |
| layer | Position layer (all stakeholders) | position | position movement | 0.4443 | 0.1667 | +0.2777 | 0.1 |
| layer | Salience layer (all stakeholders) | salience | respect | 1.625 | 1.7157 | -0.0907 | 0.1 |
| drill | Management dependency | position | justification content | 1.5347 | 1.618 | -0.0833 | 0.1 |
| drill | Management relational prior | belief | position movement | 0.264 | 0.4445 | -0.1805 | 0.132 |
| drill | Works council dependency | position | justification content | 1.5208 | 1.5902 | -0.0693 | 0.1385 |
| drill | Management relational prior | belief | transcript length | 155546.3333 | 146458.0 | +9088.3333 | 0.1948 |
| drill | Management flexibility | position | transcript length | 142420.6667 | 170954.0 | -28533.3333 | 0.2 |
| layer | Motivation layer (all stakeholders) | motivation | red-line declarations | 10.6667 | 15.6667 | -5.0 | 0.2 |
| layer | Position layer (all stakeholders) | position | red-line declarations | 13.6667 | 10.3333 | +3.3333 | 0.2 |
| drill | Works council dependency | position | respect | 1.6493 | 1.7013 | -0.052 | 0.2489 |
| drill | Management relational prior | belief | justification content | 1.5032 | 1.5312 | -0.028 | 0.2489 |
| drill | Management relational prior | belief | red-line declarations | 13.6667 | 11.1667 | +2.5 | 0.2684 |
| drill | Works council dependency | position | red-line declarations | 14.5 | 12.0 | +2.5 | 0.2727 |
| drill | Saxony assertiveness | interaction | transcript length | 149559.3333 | 164687.6667 | -15128.3333 | 0.3 |
| drill | Management dependency | position | red-line declarations | 11.3333 | 14.6667 | -3.3333 | 0.3 |
| drill | IG Metall flexibility | position | position movement | 0.3195 | 0.4028 | -0.0833 | 0.3009 |
| drill | IG Metall flexibility | position | justification content | 1.5902 | 1.5487 | +0.0415 | 0.3247 |
| drill | Works council cooperativeness | interaction | justification content | 1.5765 | 1.5348 | +0.0417 | 0.329 |
| drill | IG Metall flexibility | position | red-line declarations | 10.1667 | 12.8333 | -2.6667 | 0.3961 |
| drill | Investors power | salience | red-line declarations | 15.0 | 12.3333 | +2.6667 | 0.4 |
| drill | Investors power | salience | transcript length | 151852.6667 | 138899.6667 | +12953.0 | 0.5 |
| layer | Motivation layer (all stakeholders) | motivation | justification content | 1.5557 | 1.4377 | +0.118 | 0.5 |
| drill | Management flexibility | position | position movement | 0.3333 | 0.222 | +0.1113 | 0.5 |
| drill | Saxony assertiveness | interaction | position movement | 0.3333 | 0.4443 | -0.111 | 0.5 |
| drill | Owners social preference | motivation | justification content | 1.5623 | 1.493 | +0.0693 | 0.5 |
| drill | Management dependency | position | respect | 1.625 | 1.667 | -0.042 | 0.5 |
| drill | Owners social preference | motivation | transcript length | 152130.6667 | 159464.0 | -7333.3333 | 0.6 |
| drill | Saxony assertiveness | interaction | red-line declarations | 10.6667 | 12.0 | -1.3333 | 0.6 |
| drill | Owners social preference | motivation | red-line declarations | 11.0 | 9.6667 | +1.3333 | 0.6 |
| layer | Position layer (all stakeholders) | position | justification content | 1.507 | 1.4443 | +0.0627 | 0.6 |
| layer | Motivation layer (all stakeholders) | motivation | position movement | 0.2223 | 0.1667 | +0.0557 | 0.6 |
| layer | Interaction layer (all stakeholders) | interaction | respect | 1.6803 | 1.646 | +0.0343 | 0.6 |
| drill | Works council dependency | position | transcript length | 146282.5 | 141680.8333 | +4601.6667 | 0.6299 |
| layer | Position layer (all stakeholders) | position | transcript length | 163392.3333 | 154957.3333 | +8435.0 | 0.7 |
| drill | Owners social preference | motivation | position movement | 0.389 | 0.5 | -0.111 | 0.7 |
| drill | Saxony assertiveness | interaction | respect | 1.7153 | 1.6877 | +0.0277 | 0.7 |
| layer | Motivation layer (all stakeholders) | motivation | respect | 1.625 | 1.5973 | +0.0277 | 0.7 |
| drill | Management flexibility | position | respect | 1.6527 | 1.6387 | +0.014 | 0.7 |
| drill | Works council dependency | position | position movement | 0.3472 | 0.3888 | -0.0417 | 0.7251 |
| drill | Works council cooperativeness | interaction | red-line declarations | 9.3333 | 10.1667 | -0.8333 | 0.7424 |
| layer | Salience layer (all stakeholders) | salience | red-line declarations | 13.6667 | 12.3333 | +1.3333 | 0.8 |
| drill | Owners social preference | motivation | respect | 1.6393 | 1.6737 | -0.0343 | 0.8 |
| drill | Works council cooperativeness | interaction | position movement | 0.347 | 0.3748 | -0.0278 | 0.842 |
| drill | IG Metall flexibility | position | transcript length | 155260.0 | 153244.1667 | +2015.8333 | 0.868 |
| layer | Motivation layer (all stakeholders) | motivation | transcript length | 147776.3333 | 145860.3333 | +1916.0 | 0.9 |
| layer | Salience layer (all stakeholders) | salience | transcript length | 160394.0 | 162040.3333 | -1646.3333 | 0.9 |
| layer | Interaction layer (all stakeholders) | interaction | red-line declarations | 13.0 | 11.3333 | +1.6667 | 0.9 |
| drill | Management flexibility | position | red-line declarations | 10.0 | 11.0 | -1.0 | 0.9 |
| layer | Interaction layer (all stakeholders) | interaction | justification content | 1.4443 | 1.403 | +0.0413 | 0.9 |
| drill | Investors power | salience | justification content | 1.5417 | 1.5627 | -0.021 | 0.9 |
| drill | Investors power | salience | respect | 1.667 | 1.653 | +0.014 | 0.9 |
| layer | Position layer (all stakeholders) | position | respect | 1.5903 | 1.5763 | +0.014 | 0.9 |
| layer | Salience layer (all stakeholders) | salience | justification content | 1.4723 | 1.4863 | -0.014 | 0.9 |
| drill | Management dependency | position | transcript length | 152049.0 | 152097.6667 | -48.6667 | 1.0 |
| drill | Management dependency | position | position movement | 0.389 | 0.333 | +0.056 | 1.0 |
| layer | Interaction layer (all stakeholders) | interaction | position movement | 0.167 | 0.139 | +0.028 | 1.0 |
| drill | Investors power | salience | position movement | 0.361 | 0.3333 | +0.0277 | 1.0 |
| drill | Management flexibility | position | justification content | 1.5487 | 1.5557 | -0.007 | 1.0 |
| drill | Saxony assertiveness | interaction | justification content | 1.5553 | 1.5487 | +0.0067 | 1.0 |
| layer | Salience layer (all stakeholders) | salience | position movement | 0.139 | 0.139 | +0.0 | 1.0 |

## 3. Baseline displacement

Clean comparison - calibrated configuration vs layer-perturbed, both from the screen batch:

| metric | calibrated | perturbed | delta | Welch t |
|---|---|---|---|---|
| justification content | 1.4983 | 1.4688 | -0.0295 | -1.1 |
| respect | 1.5919 | 1.632 | +0.0401 | +1.92 |
| position movement | 0.2777 | 0.198 | -0.0797 | -2.04 |
| red-line declarations | 9.4815 | 12.5833 | +3.1019 | +2.83 |
| transcript length | 142611.5185 | 152461.625 | +9850.1065 | +2.09 |

Pole symmetry (does the direction of the perturbation matter?):

| metric | calibrated | all high poles | all low poles |
|---|---|---|---|
| justification content | 1.4983 | 1.5355 | 1.527 |
| respect | 1.5919 | 1.6733 | 1.6541 |
| position movement | 0.2777 | 0.3137 | 0.3333 |
| red-line declarations | 9.4815 | 12.0196 | 11.8627 |
| transcript length | 142611.5185 | 154302.8039 | 150346.5294 |

## 3b. Session test on the calibrated configuration

Split by RUN ID, not by condition: the confirmatory top-up added runs to 'main'
itself, so condition 'main' now spans both sessions and cannot serve as the
original-session arm. Membership is the commissioning record (doc 18).

**Session test** - original draw vs every calibrated run made in the confirmatory
session (top-up and replicate pooled):

| metric | original (n=5) | confirmatory (n=10) | delta | Welch t | p (exact) | floor |
|---|---|---|---|---|---|---|
| justification content | 1.4998 | 1.5186 | +0.0188 | +0.4 | 0.6953 | 0.0003 |
| respect | 1.5292 | 1.6375 | +0.1083 | +2.8 | 0.018 | 0.0003 |
| position movement | 0.1668 | 0.275 | +0.1082 | +2.46 | 0.0916 | 0.0003 |
| red-line declarations | 12.0 | 10.0 | -2.0 | -1.07 | 0.375 | 0.0003 |
| transcript length | 150437.2 | 130576.7 | -19860.5 | -2.36 | 0.0609 | 0.0003 |

**Internal control** - the two confirmatory groups against each other. A session
effect predicts this is null; a non-null result would mean the contrast above is
not measuring session.

| metric | top-up | replicate | delta | Welch t | p (exact) |
|---|---|---|---|---|---|
| justification content | 1.5164 | 1.5208 | +0.0044 | +0.08 | 0.9365 |
| respect | 1.6208 | 1.6542 | +0.0334 | +0.71 | 0.5159 |
| position movement | 0.2832 | 0.2668 | -0.0164 | -0.22 | 1.0 |
| red-line declarations | 10.4 | 9.6 | -0.8 | -0.28 | 0.8492 |
| transcript length | 137583.2 | 123570.2 | -14013.0 | -1.16 | 0.3016 |

## 4. Variance census - which dependent variables carry information

| variable | min | max | SD | distinct values |
|---|---|---|---|---|
| dqi_justif_content | 1.292 | 1.729 | 0.0868 | 21 |
| dqi_respect | 1.438 | 1.812 | 0.0747 | 19 |
| position_move | 0.0 | 0.917 | 0.1582 | 10 |
| red_line_declarations | 1.0 | 19.0 | 3.9147 | 18 |
| transcript_chars | 92581.0 | 189791.0 | 17243.3469 | 129 |
| dqi_justif_level | 1.917 | 2.0 | 0.0177 | 5 |
| dqi_constructive | 1.812 | 2.0 | 0.0366 | 10 |
| dqi_individuation | 1.979 | 2.0 | 0.0048 | 2 |
| rounds | 4.0 | 4.0 | 0.0 | 1 |
| experts | 0.0 | 2.0 | 0.4913 | 3 |
| agreement | - | - | - | 4/129 True |