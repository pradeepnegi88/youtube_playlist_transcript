# Deployment Guide

## Before deployment

- Run the documented build, lint, type, and test commands.
- Check that required environment variables are configured.
- Confirm secrets are stored in the deployment platform, not in source control.
- Review database migrations and backward compatibility.
- Verify generated artifacts and static assets.
- Check logs and health checks.

## Environment separation

Use separate development, preview, and production environments where possible.

Production should have:

- HTTPS
- Restricted credentials
- Explicit allowed origins
- Resource and request limits
- Error monitoring
- Backups for persistent data

## Safe rollout

1. Deploy to a preview or staging environment.
2. Run smoke tests against the deployed service.
3. Verify the main user workflows.
4. Deploy to production.
5. Monitor logs, health checks, latency, errors, and resource usage.
6. Keep a rollback path.

## Persistence

Do not assume a deployed filesystem is persistent. Use a managed database, object storage,
or a persistent volume for data that must survive restarts and redeployments.

## Post-deployment checks

Verify:

- The application loads
- APIs return expected status codes
- Authentication works
- Background jobs complete
- Static assets load
- Logs contain no secrets
- Monitoring and alerts are receiving events

Document platform-specific commands and required environment variables in the project
README or an operations runbook.
