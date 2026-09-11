# Security Guidelines

## Secrets

- Store secrets in environment variables or an approved secret manager.
- Never commit tokens, passwords, private keys, or production data.
- Rotate credentials if they are exposed.
- Use separate credentials for development, testing, and production.

## Input handling

Validate and normalize all user-controlled input before using it in:

- Shell commands
- File paths and filenames
- URLs
- Database queries
- HTML, templates, or logs
- Configuration and redirects

Use allowlists where possible. Reject invalid input clearly.

## Web applications

- Enforce authentication and authorization on every protected operation.
- Configure CORS for known origins instead of allowing every origin.
- Apply request size, timeout, rate, and concurrency limits.
- Use secure cookies and HTTPS in production.
- Avoid returning stack traces or sensitive implementation details.
- Escape output according to its rendering context.

## Files and data

- Prevent path traversal and unsafe archive extraction.
- Apply least-privilege permissions.
- Minimize collection of personal data.
- Define retention and deletion behavior.
- Encrypt sensitive data in transit and at rest where appropriate.

## Dependencies and operations

- Keep dependencies updated.
- Review new dependencies before adding them.
- Pin or lock versions where reproducibility matters.
- Review logs for secrets and personal data.
- Report suspected vulnerabilities privately rather than publishing exploit details.
