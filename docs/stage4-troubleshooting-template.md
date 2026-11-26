# Troubleshooting record — append only verified outcomes
## Existing actual error (local MariaDB container creation)
- Command: docker run --name memo-dev-db ... (credential redacted)
- Actual error: Conflict. The container name "/memo-dev-db" is already in use by container "9e4c64b4e8da814097bab7fe107760d32c00b6bd093f19c5fc9d2e208826003a".
- Cause: repeated creation using same container name after initial wrong password entry.
- AI suggestion: remove old container and, only if no data to preserve, remove initial volume; recreate using matching password and .env.
- Follow-up: user screenshots show login and memo writing working locally; exact corrective commands and logs were not supplied, so do not claim those commands were verified.
## Additional actual errors
Record original command, redacted output, AI analysis, actual diagnosis, changed files, retest and result. Do not invent.
