# CLAUDE.md

Guidance for AI coding assistants working in this repository.

## Before changing code

1. Read the repository README and any contribution, architecture, or development
   documentation that applies to the requested work.
2. Inspect the existing code, tests, configuration, and working tree before making
   assumptions.
3. Identify the smallest set of files that needs to change.
4. Look for existing helpers, patterns, and tests before adding new abstractions.
5. Check for local instructions in nested `CLAUDE.md`, `AGENTS.md`, or equivalent
   files. More specific instructions override this file.

If the request has a significant product, API, data, security, or deployment
decision that is not specified, ask one focused question before implementing it.
For routine implementation details, use the repository's existing conventions.

## Implementation principles

- Make precise, complete changes. Do not modify unrelated code.
- Preserve existing behavior unless a behavior change is explicitly requested.
- Prefer the simplest design that solves the actual problem.
- Reuse existing utilities and abstractions.
- Keep public interfaces and stored data strongly typed where the language supports it.
- Validate external input at trust boundaries.
- Propagate or surface errors. Do not hide failures with broad catches or silent fallbacks.
- Do not add dependencies when the standard library or existing project dependencies are enough.
- Keep comments short and explain only non-obvious decisions.
- Do not commit credentials, tokens, private keys, personal data, or generated secrets.
- Treat user-controlled paths, URLs, filenames, commands, and markup as untrusted.
- Consider authentication, authorization, injection, path traversal, resource limits,
  privacy, and denial-of-service risks when changing networked or file-handling code.

## Testing and verification

- Read the project's documented test and validation commands before running them.
- Run the smallest targeted test or check that covers the change.
- Run type checks, linting, builds, and broader tests when the change warrants them.
- Add or update tests for behavioral changes. A test should fail if the behavior is removed.
- Derive expected values independently from the implementation under test.
- Make empty or zero-result checks distinguishable from successful checks that found no issues.
- Verify error paths, invalid input, boundary conditions, and relevant security cases.
- For frontend work, inspect the built page in a browser at the affected viewport sizes.
- For APIs, test both successful responses and representative failures.
- Do not claim a check passed unless it was actually run and its result is known.

## Documentation

Update documentation when the change affects:

- Installation or run commands
- Configuration or environment variables
- Public APIs or user workflows
- Deployment
- Data migrations
- Security or operational behavior

Keep documentation factual and aligned with the current implementation. Prefer
short, task-oriented instructions and working examples.

## Git and delivery

- Inspect `git status` before editing and before finishing.
- Never discard existing user changes.
- Do not use destructive commands such as `git reset --hard` or broad recursive deletion
  unless the user explicitly requests and scopes them.
- Do not amend commits unless explicitly asked.
- Follow the repository's branching, commit, review, and release conventions.
- Run the project's required local gate before pushing.
- If CI fails, identify the cause, fix it, and explain why local checks did not catch it.
- Keep commits focused and describe what changed, why it changed, and how it was verified.

## Tool and environment safety

- Use repository-local tools and package-manager commands where available.
- Do not install tools or packages unless required by the project or a failed validation.
- Avoid commands that expose secrets or send repository contents to third parties.
- Use explicit repository, organization, environment, and resource identifiers for external
  operations. Never rely on an ambiguous default when an operation could be destructive.
- Do not access external systems that the user or repository instructions place out of scope.
- Clean up temporary files, caches, generated databases, and build artifacts when they are
  not intended to be committed.

## Final response

Report briefly:

1. What changed.
2. Which files or surfaces were affected.
3. What validation was run and its result.
4. Any known limitation, follow-up, or required user action.

Link to workspace files when referring to them. Be concise and do not claim deployment,
publication, or persistence unless it was verified.
