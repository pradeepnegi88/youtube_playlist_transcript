# Contributing

## Before starting

Read:

- [README.md](README.md)
- [CLAUDE.md](CLAUDE.md)
- [AGENTS.md](AGENTS.md)

Check the current working tree and avoid overwriting changes you did not make.

## Making changes

1. Define the requested behavior and affected surfaces.
2. Find existing patterns before adding new code.
3. Keep changes focused and readable.
4. Update documentation for changed commands, configuration, APIs, or workflows.
5. Add or update tests for behavioral changes.

## Validation

Run the smallest relevant checks first, then broader checks when appropriate:

- Formatting and linting
- Type checking
- Unit and integration tests
- Build commands
- Manual browser or API checks

Record failures accurately. Do not hide errors or use success-shaped fallbacks.

## Pull requests

A pull request should explain:

- What changed
- Why it changed
- How it was tested
- Any migration, configuration, or deployment steps
- Known limitations

Keep unrelated refactors out of the pull request.
