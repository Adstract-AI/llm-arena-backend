# Serializer Guidelines

- Serializers should focus on validation and representation.
- Explicitly define serializer fields; do not use `__all__`.
- Serializers should never expose internal information unless explicitly required by the API contract or task.
- Avoid returning internal IDs, timestamps, foreign keys, internal statuses, error-tracking fields, implementation metadata, or backend-only computed control fields unless the response contract specifically requires them.
- Keep business orchestration out of serializer `create()` / `update()` unless explicitly required.
