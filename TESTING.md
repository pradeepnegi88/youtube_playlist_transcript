# Testing Guide

## Test the behavior, not the implementation

Tests should verify observable behavior through stable public interfaces. Expected values
must be defined independently from the implementation under test.

Every behavioral claim should have a check that fails when the behavior is removed.

## Minimum coverage

For each changed feature, consider:

- Normal input
- Invalid input
- Empty input
- Boundary values
- Permission or authentication failures
- Network and dependency failures
- Persistence and restart behavior
- User-visible error messages

## Test layers

### Unit tests

Use for pure functions, validation, transformations, and isolated business rules.

### Integration tests

Use for database access, file handling, API routes, queues, and external service adapters.
Use fakes or controlled fixtures instead of real production services.

### End-to-end tests

Use for critical user workflows that cross frontend, backend, storage, or authentication
boundaries.

## Test hygiene

- Keep tests deterministic and isolated.
- Do not depend on developer-specific paths or credentials.
- Clean up temporary files and records.
- Make expected counts explicit.
- Preserve useful failure output.
- Run the repository's documented test command before delivery.
