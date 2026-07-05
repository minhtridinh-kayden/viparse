# Security Policy

## Supported versions

viparse is pre-1.0; security fixes land on the latest `main` / most recent release.

| Version         | Supported |
|-----------------|-----------|
| latest (`main`) | ✅        |
| older           | ❌        |

## Reporting a vulnerability

Please report vulnerabilities **privately** — do not open a public issue:

- **GitHub** — open a private advisory via the repository's *Security → Report a
  vulnerability* form, or
- **Email** — kayden.trizenx@gmail.com.

We aim to acknowledge a report within a few business days and to ship a fix or mitigation
promptly, crediting reporters who wish to be named.

## Threat model & mitigations

viparse parses **untrusted documents**, so it is built to fail fast rather than hang or
exhaust memory on hostile input:

- **Oversized files** are rejected before parsing (`max_bytes`, default 100 MiB).
- **Zip decompression bombs** are caught by bounded streaming decompression of OOXML parts.
- **Runaway external processes** (LibreOffice, Tesseract) run under timeouts.
- viparse **never** executes file content and never extracts zip members by path.

Heavy/CVE-prone parsers live behind extras and are wrapped in thin adapters, so a
vulnerable engine can be swapped without touching the rest of the pipeline. `pip-audit`
runs in CI on every change, and a CycloneDX SBOM is produced by a dedicated CI job.
