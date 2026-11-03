# Risk register

| Risk | Impact | Mitigation | Current state |
|---|---|---|---|
| NASA catalog omits downloadable resources | source ambiguity | pin candidate URL, hash, nested file hashes | mitigated for current archive |
| Small laboratory dataset generalizes poorly | misleading RUL | simple baselines, per-cell errors, explicit limitations | open |
| Historical leakage | inflated evaluation | cutoff-only inputs and chronological tests | controlled in API; full evaluation pending |
| Bedrock model/Region changes | unavailable explanations | runtime discovery, configured IDs, deterministic fallback | BLOCKED without credentials |
| RDS idle cost | unexpected spend | scheduled demos, priced review, teardown runbook | open |
| Public/private data mixing | privacy breach | static versioned export, no private API connection | controlled by design |
| Concurrent memory corrections | lost update | versions/idempotency plus PostgreSQL integration tests | implementation partial |
| Lab threshold misread as product advice | unsafe claim | label 1.4 Ah as experiment-specific throughout | controlled |

