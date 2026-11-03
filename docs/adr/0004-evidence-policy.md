# ADR 0004: Deterministic policy and LLM boundary

Status: Accepted

The decision engine owns classifications. Bedrock may explain the decision using supplied evidence and
valid prior memories; it cannot create measurements or override the policy. If inference is unavailable,
the API returns the deterministic result and an explicit unavailable explanation state.

