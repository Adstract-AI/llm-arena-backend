# Error Handling Guidelines

- Use custom API exceptions for expected business failures; do not raise generic `Exception` or generic DRF exceptions for domain errors.
- Every custom API exception must have an appropriate HTTP status code, stable default detail, and stable error code.
- Preserve the most specific status code available; do not wrap auth, permission, validation, or other existing domain exceptions into broader generic errors.
- Raise business/domain exceptions from the service layer; keep views thin and focused on validation, calling services, and shaping the response.
- Keep logs in services, signals, and pipeline layers, not in views.
- Use `4xx` for expected client or business-rule failures and `5xx` only for true internal failures.
- If a failure is internal but persistence must still happen first, persist the state/error tracking first and then raise the custom `5xx` exception.
- If an operation has recoverable/non-fatal errors versus internal fatal errors, model those paths explicitly; do not return a normal success-style response for fatal internal errors.
- Do not swallow exceptions silently. Either handle them intentionally with persistence/logging, or re-raise the appropriate custom exception.
- When catching broad exceptions to translate them, preserve domain-specific exceptions with explicit `except SomeDomainException: raise` branches before the generic catch.
- Error responses should not expose internal implementation details unless explicitly required. Prefer safe, domain-level messages.
- Keep exception names and error messages specific to the bounded context and operation that failed.
