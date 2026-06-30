# Security Policy

## Supported Versions

Security fixes are provided for the latest released version of `repo-health`.

| Version | Supported |
| --- | --- |
| Latest `v*` release | Yes |
| Older releases | No |

## Reporting a Vulnerability

Please do not open a public issue for suspected vulnerabilities.

Report security concerns through GitHub private vulnerability reporting for this repository:

https://github.com/Aether-254/repo_health/security/advisories/new

If private vulnerability reporting is unavailable, contact the repository owner directly through GitHub.

## What to Include

Include enough detail to reproduce and assess the issue:

- affected version or commit
- operating system and Python version
- command used
- expected behavior
- actual behavior
- impact
- minimal reproduction steps

Do not include real GitHub tokens, private repository names, private issue contents, or other secrets in the report. Use redacted examples.

## Response Expectations

Maintainers will triage reports as soon as practical. Valid issues will be fixed in the default branch and released with a `v*` tag when appropriate.

## Scope

In scope:

- token handling
- accidental disclosure of private repository metadata
- unsafe network request behavior
- release artifact integrity problems
- CI/CD security issues

Out of scope:

- issues requiring compromised GitHub credentials
- GitHub API outages or rate limits
- findings that only affect unsupported old releases
