# Security Policy

## Supported Versions

`open-lead-agent` is currently pre-1.0. Security fixes are expected to target
the latest main branch until the project starts publishing versioned releases.

## Reporting a Vulnerability

Please do not open a public issue for a suspected security vulnerability.

Instead, report privately through GitHub Security Advisories if available, or
contact the maintainers through the repository owner profile.

Helpful details include:

- affected version or commit
- reproduction steps
- expected impact
- whether secrets, customer data, or model credentials may be exposed

## Sensitive Data

This project handles lead and contact information. Deployments should treat
profile fields, chat history, phone numbers, email addresses, WeChat IDs, and
LLM credentials as sensitive data.
