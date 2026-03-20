# API / View Guidelines

- Prefer specialized DRF views (`CreateAPIView`, `UpdateAPIView`, `DestroyAPIView`, etc.).
- Use `GenericAPIView` only when a specialized view does not fit.
- If `GenericAPIView` is used, include the proper mixins for intended methods.
- Do not rely on hooks like `perform_create` / `perform_update` unless explicitly required.
- Override method-specific handlers (`create`, `update`, `destroy`) instead of unrelated HTTP handlers.
- Keep standard CRUD response behavior:
  - Create: return created resource.
  - Update: return success + updated resource.
  - Delete: return success message.
- Use `get_queryset()` for collections and `get_object()` for single-resource operations.
