# AGENTS.md

Instructions for automated coding agents working in this repository.

## Operating rules

- Read `README.md`, `CLAUDE.md`, and relevant project documentation first.
- Inspect the working tree before making changes.
- Follow more specific instructions in nested directories.
- Make the smallest complete change that satisfies the request.
- Preserve unrelated user changes.
- Reuse existing patterns, helpers, and dependencies.
- Ask for clarification when an important product, security, data, or deployment decision
  cannot be inferred safely.

## Validation

- Run targeted tests and checks for changed behavior.
- Test both success and failure paths.
- Inspect frontend changes in a browser when applicable.
- Report commands run and their results.
- Do not claim success without verification.

## Safety

- Never expose or commit secrets.
- Treat external input as untrusted.
- Avoid destructive commands and broad file deletion.
- Use explicit targets for external services and repositories.
- Do not send source code or private data to third-party services without authorization.

## Completion report

Summarize the change, affected files, validation, and any remaining limitation.
