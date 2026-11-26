# Stage 4 AI prompt engineering record
- Original request: containerize Web/WAS/DB with network separation and auto deployment foundation.
- Added constraints: frontend bridge/overlay for web+was; internal backend only was+db; no WAS/DB published ports. Positive control and direct IP negative test avoid confusing missing utilities/DNS failure with isolation.
- Startup: Compose service_healthy; Swarm does not honor depends_on; bounded exponential retry and DB advisory lock in existing application; DB and WAS health checks.
- Secrets: existing env locally; external Swarm secrets mounted read-only, WAS entrypoint exports values to existing app config; non-root UID 10001. No secret values in image or repo. DB root only in DB service.
- Architecture: native local build; registry buildx for AMD64/ARM64, confirm actual server architecture. Slim base and pinned direct runtime dependencies; pytest excluded. Transitive dependencies and base digest not fully locked.
- Persistence: external local volume reuses prior data after stopping old DB; separate production volume pinned to labeled node. Local volume does not replicate.
- Verification: actual Docker build/test not available in generation environment. Record actual command output after local execution. No fabricated errors.
