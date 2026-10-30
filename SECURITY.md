# Security Policy

UPWIND has two security surfaces with different trust boundaries:

- the public National Explorer and its read-only API;
- the local engine, which reads user-owned files and writes local analysis
  artifacts.

Do not include private measurements, credentials, deployment tokens, or raw
upstream archives in a bug report. Public API reports should include the
endpoint, timestamp, response status, and a minimal reproducible request, with
personal or sensitive data removed.

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub's private
vulnerability reporting for [apandya55/Upwind](https://github.com/apandya55/Upwind/security/advisories/new).
Do not disclose an unpatched vulnerability in a public issue or pull request.

If private reporting is unavailable, contact the repository owner through the
GitHub profile and request a private channel. Reports should describe the
affected component, impact, reproduction steps, and any suggested mitigation.

The security policy does not imply that the local scientific engine is field
validated or that the hosted service provides a security, availability, or
operational guarantee.
