# Serializer Guidelines

- Serializers should focus on validation and representation.
- Explicitly define serializer fields; do not use `__all__`.
- Avoid returning any internal data like IDs, timestamps etc. unless required by API contract.
- Keep business orchestration out of serializer `create()` / `update()` unless explicitly required.
