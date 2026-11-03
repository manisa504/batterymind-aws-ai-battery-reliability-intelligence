# Aspect registry

| ID | Business purpose | Inputs → outputs | Dependencies | Principal failures | Security | Acceptance evidence |
|---|---|---|---|---|---|---|
| A01 | Establish trustworthy evidence | NASA archive → Parquet + manifest | None | hash/schema/unit failure | immutable raw source | G1 data report |
| A02 | Explain measured degradation | cycles/samples → SOH and trends | A01 | missing/invalid capacity | no user data | mathematical tests |
| A03 | Estimate experimental RUL | historical capacity → predictions + intervals | A01–02 | leakage, non-decreasing trend | bounded compute | chronological evaluation |
| A04 | Make repeatable classifications | valid metrics → versioned decision | A02 | boundary ambiguity | deterministic policy | boundary tests |
| A05 | Preserve active context | authenticated turns → bounded session | A09 | lost session | owner authorization | restart tests |
| A06 | Recall prior assessments | evidence-linked records → ranked memory | A05, A09 | stale/cross-user recall | RLS and ownership | isolation/correction tests |
| A07 | Fit relevant context | structured facts + memory → prompt context | A06 | token overflow | omit secret content | compression evaluation |
| A08 | Preserve temporal truth | cutoffs + versions → consistent history | A01, A06 | future evidence leakage | auditable timestamps | cutoff/concurrency tests |
| A09 | Operate securely on AWS | CDK → authenticated services | G0 | account/Region/SCP errors | least privilege/encryption | synth + live tests |
| A10 | Support engineering work | APIs → five dashboard views | A01–09 | loading/API errors | Cognito | build + browser tests |
| A11 | Demonstrate publicly | validated export → static showcase | A01–04 | stale/mismatched export | no private connections | build/value checks |
| A12 | Make design reviewable | architecture/evidence → static docs | G0–G6 | broken links/diagrams | no secrets | link/render checks |
| A13 | Measure quality and cost | traces/results → evaluation reports | A02–10 | absent telemetry | redaction/retention | reports + alarms |
| A14 | Prevent false release claims | gate evidence → release status | all | unverified success claim | signed CI/OIDC | G7 claim audit |

Each aspect uses the common contract: reject invalid identifiers; preserve units, cutoff, source hashes,
model and policy versions; return explicit unavailable states; and store no unsupported claim.

