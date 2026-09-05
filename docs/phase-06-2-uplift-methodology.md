# Phase 6.2 — Uplift/CATE methodology

## Decision

Phase 6.2 estimates heterogeneous treatment-effect scores on the real Criteo Uplift v2.1
randomized advertising benchmark. The output is a ranking signal for who may benefit from treatment;
it is not a retail promotion effect, Iranian market estimate, or automatic campaign policy.

The first implementation uses two transparent baselines for the `visit` outcome:

1. **S-Learner:** one outcome model with treatment as an input; predict the difference between the
   same user's treatment=1 and treatment=0 counterfactual predictions.
2. **T-Learner:** separate treated and control outcome models; predict the difference between their
   predictions for the same features.

Both are trained only on pre-treatment features `f0`–`f11`. `treatment`, `visit`, and `conversion`
are not features; `exposure` is post-treatment and is forbidden from the feature matrix.

## Data split

The full publisher file is read in chunks. A deterministic hash of pre-treatment features `f0`–`f11`
assigns each row to one of:

```text
train 70% | validation 15% | test 15%
```

The assignment is independent of outcome, treatment, chunk size, and source row order. Identical
feature vectors intentionally remain in the same split. Treatment/outcome counts are reported so arm
balance and class coverage can be checked explicitly. The source SHA-256 and fixed seed are recorded.

To keep local execution reproducible, training retains approximately one in twenty train rows using
a second deterministic pre-treatment-feature hash. Sampling never reads treatment or outcome and
therefore preserves source prevalence in expectation. Test metrics use every held-out row.

## Primary metric: Qini/AUUC

For a ranked test population, each prefix receives a policy value estimate using randomized assignment:

```text
Qini(prefix) = treated_successes
               - treated_count × control_successes / control_count
```

The cumulative Qini curve shows the incremental conversions/visits obtained by targeting the highest
scored prefixes relative to withholding treatment from those prefixes. `raw AUQC` is the trapezoidal
area under the cumulative Qini curve with population fraction on x. The reported `Qini coefficient`
is raw AUQC minus the triangular random-targeting line area; it is not normalized by a perfect curve.
We report:

- model raw AUQC and Qini coefficient;
- random-ranking Qini coefficient baseline;
- Qini at 10%, 20%, and 30% of the ranked population;
- arm counts and treatment fraction.

The random baseline is the mean of five deterministic seeded random permutations used as a reproducible
calibration reference, not a confidence interval. AUUC does not prove individual causal truth; it evaluates policy ranking under
the randomized benchmark's assumptions. A perfect oracle is not reported because each person has only
one observed outcome and the true counterfactual outcome is unavailable.

## Acceptance gate

The phase passes only when:

1. no post-treatment column enters training;
2. every split and train sample is deterministic, outcome-independent, and recorded;
3. the complete real test set is evaluated exactly once after model selection;
4. both learners produce finite scores and preserve test-arm accounting;
5. Qini curves report every ranked prefix and use an explicit zero-treatment-control convention;
6. the validation-selected learner beats the five-permutation random Qini-coefficient baseline in the
   test report; otherwise the result is retained as a negative benchmark and no model is promoted;
7. the report states that Criteo evidence does not identify retail or Iranian impact.

## Phase 6.3 extension

Model selection is now frozen on validation AUUC only. The selected learner is reported, but the
test set remains locked for the final comparison. The report also includes treatment/outcome stratum
coverage for train, validation, and test, plus an explicit machine-readable gate. Even when the gate
passes, `promotion_allowed` remains false until cost, capacity, harm, fairness, calibration, and a
fresh holdout review are completed.

## Phase 6.4 uncertainty and convergence repair

Every logistic model now runs after `StandardScaler`, and the report records solver iteration counts.
Reaching `max_iter` fails the convergence gate. For the validation-selected learner, the test ranking
is frozen and evaluated with 50 reproducible Poisson(1) multiplier-bootstrap replicates. The reported
95% percentile interval is conditional on that frozen ranking: it measures test-population evaluation
noise, not model-refit uncertainty, transportability, or business-policy uncertainty.

No threshold for automatic targeting is introduced. A future policy requires cost, capacity, treatment
harm, fairness, calibration, and a fresh holdout review.
