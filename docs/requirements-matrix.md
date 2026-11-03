# Requirement-to-test traceability

| Requirement | Implementation | Verification | Gate |
|---|---|---|---|
| Authentic source and checksum | ingestion + source manifest | `nasa-ingestion.json` | G1 |
| Deterministic Parquet | sorted typed transformations | repeat ingestion/hash comparison | G1 |
| SOH and cutoff analysis | battery analytics package | unit + real API tests | G3 |
| RUL without future leakage | prediction package | chronological evaluator | G3 |
| Versioned policy | decision engine | boundary tests | G3 |
| User-owned persistent memory | SQLAlchemy + PostgreSQL RLS | memory integration suite | G4 |
| Structured facts before memory | API orchestration | context assembly tests | G4 |
| AWS security and cost controls | Python CDK | synth assertions + live tests | G2/G5 |
| Five engineering views | React application | build + browser tests | G5 |
| Independent public showcase | static validated export | build + value comparison | G6 |
| Editable architecture | draw.io + SVG/PNG | XML + visual review | G2 |
| Publishable documentation | `DOC/index.html` | static-link check | G7 |

