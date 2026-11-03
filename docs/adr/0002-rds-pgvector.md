# ADR 0002: RDS PostgreSQL with pgvector

Status: Accepted

Use standard RDS PostgreSQL for relational assessments, concurrency, and vector recall in one portable
store. Structured measurement tables remain authoritative; vectors are recall aids only. RDS cannot
scale to zero, so demo scheduling and teardown documentation must include idle database cost.

