# ADR 0007: License source code under Apache-2.0 and keep datasets separate

- Status: accepted under the Park release-readiness plan
- Date: 2026-08-31
- Owner: Reza

## Context

The public repository needs an explicit source-code license. The main external dataset is downloaded
from its publisher and is intentionally absent from Git. Applying one license label to both would
incorrectly imply that the repository can relicense third-party data.

## Decision

License PromoGuard source code and original documentation under Apache License 2.0. Keep external
datasets outside the repository and state that each retains its publisher terms. Apache-2.0 was
selected because it permits commercial and non-commercial reuse while preserving notices and an
explicit patent grant.

## Alternatives considered

- MIT: simpler, but without Apache-2.0's explicit patent-license language.
- GPLv3: strong copyleft may discourage some employer or design-partner integrations.
- no license: legally leaves reuse rights unclear and weakens public collaboration.

## Consequences

- reviewers can understand how the code may be reused;
- the license does not grant rights to dunnhumby, M5, Criteo, or other external data;
- raw and processed datasets stay ignored by Git;
- third-party dependency licenses remain their respective licenses.

## Reversal condition

Reconsider the license before accepting external contributors or commercial agreements whose legal
requirements conflict with Apache-2.0. A license change must receive explicit owner and, where
needed, legal review.
