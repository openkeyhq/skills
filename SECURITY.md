# Security policy

## Reporting a vulnerability

Report security issues in this pack privately to **security@openkey.ai**. Include the affected skill or file, a description, and steps to reproduce where possible. Please do not open a public issue for security reports.

We aim to acknowledge reports within a few business days and ask for a reasonable disclosure window before details are published.

## What these skills can and cannot do

- They are instructions for a coding agent. The pack makes no calls with your key, runs no server, and requires no local binaries to use.
- API keys stay in the `OPENKEY_API_KEY` environment variable or a gitignored `.env`. No skill asks for, echoes, stores or commits a key, and none puts one in a tracked file or in browser code.
- The development scripts (`scripts/`) are for maintainers. The live check sends unauthenticated requests only and expects a 401 from routes that need a key.

## Supported versions

The latest release is supported. Security fixes are applied to that line; older tags are not maintained.
