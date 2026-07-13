# Security Policy

## Supported versions

| Version | Supported |
|---|---:|
| 2.2.x | yes |
| older | best effort |

## Reporting a vulnerability

Do not open a public issue for session theft, auth bypass, arbitrary code execution in a trusted path or secret disclosure. Use GitHub private vulnerability reporting in the repository Security tab. Include affected version, impact, reproduction and a minimal patch suggestion when possible.

## Threat model

Third-party modules are trusted in-process code. Loading an intentionally malicious module is not a sandbox escape because no sandbox is claimed. Vulnerabilities include bypassing documented permission gates without a malicious installed module, leaking secrets through built-in output, unsafe update/install behavior and remote compromise of default services.

## Operator checklist

- Keep `.env`, session, database and backups private.
- Run Haruka as an unprivileged OS user.
- Use a dedicated persistent directory with mode `0700`.
- Review module source and pin trusted URLs/commits.
- Avoid exposing a shell or debugger to untrusted roles.
- Back up before updates and revoke leaked bot tokens/sessions immediately.
