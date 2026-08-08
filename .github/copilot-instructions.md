# Copilot Working Instructions

1. Read context/README.md before making changes.
2. Read relevant context documents and ADRs before modifying code in that area.
3. Preserve domain, application, and infrastructure boundaries.
4. Update context documentation and ADRs whenever architectural decisions change.
5. Avoid premature infrastructure choices (microservices, distributed queues, cloud-only components).
6. Keep external boundaries asynchronous (database and HTTP clients).
7. Maintain strict type checking and avoid introducing untyped public interfaces.
8. Add or update tests for behavior changes.
9. Never silently change forecast semantics (target variable, horizon definition, evaluation rules).
10. Never fabricate or assume OSRS Wiki API fields that are not documented.
11. Preserve historical predictions and model-evaluation integrity when evolving storage and APIs.
12. Stop and document contradictions between implementation and context instead of improvising around them.
