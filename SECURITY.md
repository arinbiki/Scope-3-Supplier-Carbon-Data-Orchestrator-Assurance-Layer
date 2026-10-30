# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

The Scope 3 Supplier Carbon Data Orchestrator & Assurance Layer processes confidential supplier emission factors, site locations, energy invoices, and spend ledgers. Security and data integrity are paramount.

If you discover a security vulnerability, please do NOT create a public issue on GitHub. Instead, report it responsibly:

* **Security Email**: `security@carbon-orchestrator.io`
* **Response Time**: Within 48 hours with an initial assessment and mitigation plan.

## Security Practices

* **Zero Plaintext Secrets**: API keys, database credentials, and partner tokens must reside in environment variables or HashiCorp Vault.
* **Evidence Integrity**: All uploaded evidence artifacts (PCFs, utility bills, ISO certificates) are content-addressed using SHA-256 cryptographic hashes.
* **Audit Trails**: Every state transition, tier downgrade, conflict resolution, and period lock is permanently recorded in the append-only `audit_event` log.
