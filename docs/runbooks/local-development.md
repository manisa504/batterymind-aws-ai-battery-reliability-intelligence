# Local development

Run ingestion first, then `docker compose up --build`. Send `X-BatteryMind-User` only in local mode.
The AWS configuration disables this development header and places authentication at Cognito and the
load balancer. Private-memory behavior must be validated against PostgreSQL before G4 can pass.

