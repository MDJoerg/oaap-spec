# oaap.core.identity — Identity & Roles (outline)

- **ID:** `oaap.core.identity`
- **Version:** 0.1.0
- **Maturity:** draft (outline — full specification to follow)
- **Based on:** RFC-0001, RFC-0002

## Purpose

Provides user accounts, authentication, and the standard role model for
the platform. The built-in minimal identity provider (local user store,
username + password, managed in the portal) is the default and requires
no additional components; external identity providers (e.g. Keycloak,
LDAP) can replace or extend it later without changing the gateway
contract.

## Interface (sketch)

- **Standard roles** (RFC-0002): `admin`, `keyuser`, `user`, `guest`,
  `partner`, `public` — available on every installation.
- **Authentication contract with the gateway**: identity verifies
  credentials and issues the session/token the gateway checks on every
  request. The concrete mechanism (OIDC/JWT vs. trusted headers) is an
  open question from RFC-0002 and will be resolved in the full spec of
  this capability together with `oaap.core.gateway`.
- **User management API**: create/disable users, assign roles — consumed
  by the portal.
- **Bootstrap**: the first admin is created via the portal's first-run
  wizard (see `oaap.core.host`); until then no other request is served.

## Dependencies

None (foundation; the gateway depends on identity, not vice versa).

## Maturity

`draft`
