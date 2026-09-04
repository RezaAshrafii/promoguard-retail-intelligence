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

The full publisher file is read in chunks. A deterministic arithmetic hash of the canonical row
position assigns each row to one of:

```text
train 70% | validation 15% | test 15%
```

The test set is untouched until scores and model choices are frozen. The resulting treatment/outcome
counts are reported so arm balance and class coverage can be checked explicitly. Because this split
is tied to the publisher file's canonical row order, the source SHA-256 is recorded alongside the
fixed seed; changing either invalidates exact reproduction.

To keep local execution reproducible, training uses a predeclared cap per arm/outcome stratum from
the real source. The cap is a computational constraint, not a claim that the data was synthesized.
The test metrics use the complete held-out real rows.

## Primary metric: Qini/AUUC

For a ranked test population, each prefix receives a policy value estimate using randomized assignment:

```text
Qini(prefix) = treated_successes
               - treated_count × control_successes / control_count
```

The cumulative Qini curve shows the incremental conversions/visits obtained by targeting the highest
scored prefixes relative to withholding treatment from those prefixes. `AUUC` is the trapezoidal area
under the cumulative Qini curve after normalizing x by the test population size. We report:

- model AUUC;
- random-ranking AUUC baseline;
- Qini at 10%, 20%, and 30% of the ranked population;
- arm counts and treatment fraction.

The random baseline is the mean of five deterministic seeded random permutations used as a reproducible
calibration reference, not a confidence interval. AUUC does not prove individual causal truth; it evaluates policy ranking under
the randomized benchmark's assumptions. A perfect oracle is not reported because each person has only
one observed outcome and the true counterfactual outcome is unavailable.

## Acceptance gate

The phase passes only when:

1. no post-treatment column enters training;
2. every split and cap is deterministic and recorded;
3. the complete real test set is evaluated exactly once after model selection;
4. both learners produce finite scores and preserve test-arm accounting;
5. Qini curves report every ranked prefix and use an explicit zero-treatment-control convention;
6. at least one learner beats the five-permutation random baseline AUUC in the locked test report;
   otherwise the result is retained as a negative benchmark and no model is promoted;
7. the report states that Criteo evidence does not identify retail or Iranian impact.

No threshold for automatic targeting is introduced. A future policy requires cost, capacity, treatment
harm, fairness, calibration, and a fresh holdout review.
