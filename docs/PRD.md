# BatteryMind product requirements

Owner: Manisha  
Default AWS Region: `us-east-2`

## Problem and decision

Battery validation teams need a traceable view of degradation and a durable record of why an
engineering classification changed. BatteryMind combines authoritative NASA laboratory measurements,
transparent analytical baselines, deterministic policy decisions, and evidence-linked assessment
memory. It supports CONTINUE_MONITORING, INCREASE_TESTING, ENGINEERING_REVIEW, EOL_REVIEW, and
INSUFFICIENT_EVIDENCE. The classifications do not claim field safety or maintenance outcomes.

## Users and outcomes

- Reliability engineers inspect measured capacity, SOH, profiles, impedance, and RUL estimates at a
  historical cutoff without future leakage.
- Engineering reviewers inspect the exact measurements, model, policy version, and prior assessment
  behind a decision.
- Hiring managers explore a private-system-independent public export of verified measurements.

## Success criteria

The source archive and transformed rows are reproducible by checksum; analytics pass mathematical and
time-cutoff tests; memory passes persistence, correction, deletion, concurrency, and isolation tests;
the AWS template synthesizes with authentication and security controls; both UIs build; every public
claim points to executed evidence. Live AWS behavior requires live service tests.

## Constraints

Use real NASA experiments only. Keep raw data, predictions, and derived metrics separate. Keep private
memory and credentials out of public artifacts. Use AWS in production, Vercel for the independent
showcase, GitHub Pages for `DOC/`, and editable draw.io architecture. Paid provisioning and publication
require separate authorization.

