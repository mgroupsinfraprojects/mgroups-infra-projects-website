# ADR 0004 — Security helpers are source foundations, not full enterprise deployment

## Decision

Security helpers for RBAC, hashing, encryption, and review hash-chain verification live in core/security and database code.

## Context

The source package can provide security primitives, but final enterprise deployment still requires organization-specific authentication,
key storage, installer signing, retention policy, and administrative configuration.

## Consequences

- Source-level security primitives are testable.
- Enterprise claims remain limited until installer, identity, and storage policies are implemented.
