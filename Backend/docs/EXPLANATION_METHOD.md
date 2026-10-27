# DeepShield prediction explanations

The intended readers include adults aged 55+ and young people aged 11–18. The result screen therefore starts with a short explanation, an original/blurred image comparison, and practical verification steps in English and natural Bangladeshi Bengali. Technical attribution values are available in expandable sections. Usability with these age groups still needs to be evaluated; layout checks do not establish comprehension or improved awareness.

## What is computed

The original Swin-Small + DCT + Temporal Transformer checkpoint is loaded without retraining. Its SHA-256 is `be33edbb69a80072439b8ea361ee9b00f635a2604ea2a4b9c1bfabe731067b7e`. The classifier predicts Real or Fake, not named editing defects.

The existing gradient heatmap measures input sensitivity to the selected class logit. It is retained and labelled separately from SHAP. Display contrast enhancement is optional and initially off.

SHAP 0.48.0 estimates contributions to the selected-class logit minus the other-class logit, relative to the same aligned faces blurred with Gaussian radius 8:

- Branches: exact enumeration of eight RGB, DCT and temporal feature combinations, with fusion gates recomputed.
- Frames: approximate permutation SHAP over 16 sampled inputs, eight forward/reverse cycles with a fixed seed. Omitted for still images because their repeated inputs are not independent video moments.
- Regions: exact enumeration of 16 combinations of four nonoverlapping areas: eyes, nose, mouth/lower face, and the remainder of the aligned face crop. A region is changed consistently across all 16 inputs.

The main comparison also reports the actual selected-class score after blurring one region at a time. This score change is a separate measurement from a SHAP value. The displayed preview is one example; it is not a segmentation of an editing defect. Values must pass finite-value, class-matching and additivity checks before the frontend presents them.

## Interpretation limits

The blurred reference is input-specific, not a representative population background dataset. Blurring is an artificial intervention and may produce unfamiliar inputs. Branch feature mixtures can also be outside the training distribution. Exact enumeration makes the four-region game exact; it does not make an attribution a causal or forensic proof. Frame values are approximate. Scores are not calibrated probabilities of authenticity.

Neither heatmaps nor SHAP justify claims such as “a lip defect was found” or “the eyes were manipulated.” They explain measured model behaviour. A Real result does not verify a person's identity, a statement, or the truth of a news claim. General verification advice is presented separately from model evidence.

SHAP failures preserve the trained prediction and available gradient evidence. Older saved records without SHAP show an explicit unavailable state. They are not assigned invented explanations. Games that request prediction without explanations do not incur SHAP computation.

## Verification performed

The original checkpoint was tested on `real/00037.mp4` and `fake/id3_id16_0008.mp4`. Predictions remained Real 98.0981707572937 and Fake 99.90187883377075 respectively. The Real result's original frame details and gradient overlays matched the pre-SHAP baseline exactly. These are regression observations on two videos, not an accuracy evaluation.

All three attribution games completed on both videos. Maximum observed additivity error was below 0.000001. Warm local GPU explanation time for the tested Fake video was about 6.52 seconds; cold starts and hosted latency vary.

Run `pytest tests/test_shap_explanation.py` from Backend for analytical interaction, region partition, signed attribution, probability and failure-isolation checks. `scripts/verify_shap_actual.py` performs the original-checkpoint regression audit and writes private review artifacts. Frontend `scripts/test-explanation.cjs` checks both real audit results; generate those private fixtures first. No private face previews, checkpoint or secrets should be committed.
