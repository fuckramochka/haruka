# Security policy

## Supported versions

Only the latest minor release receives security fixes.

## Reporting

Do not open public issues for vulnerabilities involving session theft, remote
code execution, secret exposure or account takeover. Use GitHub's private
security advisory feature after the repository is published.

Never attach real `.env`, `*.session`, SQLite databases, private messages or API
responses containing credentials. Provide a minimal reproduction with fake data.

## Security model

Third-party engine modules are code and can be dangerous. Haruka provides
capability checks and source digests, but these are not an operating-system
sandbox. Review code and run untrusted extensions in a separate container or VM.
Dangerous capabilities require explicit trust. Initiative is disabled by default.
