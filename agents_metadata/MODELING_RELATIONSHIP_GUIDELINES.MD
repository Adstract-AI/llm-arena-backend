# Modeling & Relationship Guidelines

- Use signals only when necessary; otherwise prefer service-layer orchestration.
- Keep one-hop responsibility in cascades to avoid cross-layer coupling.
- For one-to-many relations, prefer dedicated child endpoints for child create/update.
- For one-to-one relations, share key only when entity semantics justify it.
- Prevent duplicate records and inconsistent relationship states.
