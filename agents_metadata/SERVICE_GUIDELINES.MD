# Service Guidelines

- Put business logic, orchestration, validation, and domain state transitions in services, not in views or serializers.
- Use `AbstractService` for cross-model logic, integrations, and orchestration that is not centered on one Django model.
- Use `AbstractModelService[Model]` for model-centered services so the model binding and common queryset/object helpers come from the base class.
- API views should use the service layer through the existing abstract service-view pattern and stay thin: request validation, service call, response shaping.
- Serializers should validate and represent data; they should not orchestrate domain workflows that belong in services.
- When one service needs another, prefer nested class level `*_service` field so user context is propagated consistently.
- Service methods should be typed. New non-trivial service methods should have clear docstrings describing purpose, inputs, outputs, and raised domain exceptions.
- Override `get_queryset()` in model services when the service needs default filtering, `select_related`, `prefetch_related`, or soft-delete/status exclusions.
- Keep service methods explicit about the boundary they own. If logic belongs to a more specific service, move it there instead of duplicating wrappers in a broader service.
- Raise domain-specific custom exceptions from services for expected business failures. Preserve more specific downstream exceptions instead of flattening them into generic service errors.
- Keep logs in services for business failures, state transitions, integrations, and recoverable/internal error paths. Do not move that logging into views.
- Services should use the actual model save path when downstream signals or invariants depend on it; avoid bulk updates when signal-driven behavior is required.
- Avoid hidden side effects in unrelated layers. If a service owns a workflow, it should be the clear entry point for that workflow.
- Reuse existing service methods when an appropriate one already exists. If the correct domain method does not exist, add it in the appropriate service instead of bypassing the service layer.
