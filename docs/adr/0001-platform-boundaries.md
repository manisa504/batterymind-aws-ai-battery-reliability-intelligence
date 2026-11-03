# ADR 0001: Production and public boundaries

Status: Accepted

The production system uses AWS with authenticated ECS services and private PostgreSQL. The Vercel
showcase consumes only a generated, versioned JSON export. GitHub Pages publishes documentation only.
This prevents public experiences from depending on AWS availability or private memory.

