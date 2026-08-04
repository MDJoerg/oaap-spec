# oaap.core.identity — Identity & Roles

- **ID:** `oaap.core.identity`
- **Version:** 0.2.0
- **Maturity:** draft
- **Based on:** RFC-0001, RFC-0002
- **Scope of this version:** built-in minimal identity provider with
  user management. External identity providers (Keycloak, LDAP, OIDC)
  are out of scope and must be able to replace this provider later
  without changing the gateway contract.

## 1. Purpose

Provides user accounts, authentication, and the standard role model for
the platform. The built-in minimal identity provider (local user store,
username + password, managed in the portal) is the default and requires
no additional components.

Identity is the platform's single source of truth for *who* a request
belongs to and *which platform roles* they hold. Apps never authenticate
users themselves (deployment contract); they receive the verified
identity as trusted headers from the gateway and map platform roles to
their own business roles.

## 2. Interface

### 2.1 Standard roles

The standard roles from RFC-0002 exist on every installation and are
not user-definable in this version:

`admin`, `keyuser`, `user`, `guest`, `partner`, `public`

`public` is a route marker (no authentication), never a role held by a
user account. A user account holds **one or more** of the other five.

### 2.2 User model

Each user account has at least:

| Field          | Rules                                                                           |
| -------------- | ------------------------------------------------------------------------------- |
| `username`     | unique, immutable after creation, `[a-z0-9][a-z0-9._-]*`, 2–40 chars, lowercase |
| `display_name` | optional free text; portal UX only — apps receive the `username`                |
| `roles`        | non-empty subset of {admin, keyuser, user, guest, partner}                      |
| `active`       | boolean; inactive users cannot sign in and existing sessions stop verifying     |
| password       | stored only as a salted hash; minimum length 8                                  |

### 2.3 Authentication contract with the gateway

- Identity issues a session on successful login; the gateway calls
  identity's verify endpoint on **every** request to a protected route
  (forward auth, RFC-0002 default deny).
- On success, verify returns the trusted headers `X-OAAP-User`
  (username) and `X-OAAP-Roles` (comma-separated roles); the gateway
  copies them onto the upstream request. On failure it returns a
  redirect to the login page (browser flows) or 401/403.
- Verify accepts an optional role restriction (`?roles=a,b`); the
  session must hold at least one of the listed roles (route-level
  authorization, spec `oaap.apps.runtime` 2.4).
- **Fresh state per request:** verify MUST evaluate the *current* user
  store on every call. Deactivating a user or changing their roles
  takes effect on their next request — waiting for re-login is not
  acceptable. (Sessions may cache the username, never the roles.)

### 2.4 User management

- Managing users is restricted to sessions holding the `admin` role.
  The portal provides the UI; identity provides the operations.
- Operations: **list** users (never exposing password hashes),
  **create** (username, initial password, roles, display name),
  **update** (roles, display name, active flag — not the username),
  **set password** (admin sets a new password for any user).
- **Last-admin protection:** an operation that would leave the
  platform without at least one *active* user holding `admin` MUST be
  rejected.
- **Self-service password change:** every signed-in user can change
  their own password by providing the current one. No other
  self-service exists in this version.
- Deleting users is not part of this version — deactivate instead
  (audit trails in apps may reference the username). Deletion semantics
  (including GDPR aspects) are an open point for a later version.

### 2.5 Bootstrap

The first admin is created via the portal's first-run wizard, protected
by the one-time setup token (see `oaap.core.host` 2.2). Until setup is
completed, no other request is served. The first admin receives the
roles `admin` and `keyuser`.

## 3. Configuration

- Session secret and setup token are generated at install time
  (`oaap.core.host`); the user store lives in the platform data
  directory and is included in platform backups (future
  `oaap.data.backup`).
- No configuration keys are exposed to apps.

## 4. Security requirements

1. Passwords are stored as salted hashes (state of the art; the
   reference uses werkzeug's scrypt-based default). Plaintext passwords
   never touch disk or logs.
2. Session cookies are HttpOnly and SameSite=Lax at minimum.
3. Management operations are only reachable through an
   admin-authenticated surface; the identity-internal API is never
   exposed through the gateway.
4. Failed logins return a generic error (no username enumeration).
5. Role changes and deactivation act on the next request (see 2.3).
6. Anti-spoofing is the gateway's duty (deployment contract guarantee
   1); identity supports it by being the only source of the trusted
   headers.

## 5. Conformance tests (described)

1. **Create and sign in** — admin creates user `verwaltung` with role
   `keyuser`; that user can sign in and reaches a `keyuser` route.
2. **Role enforcement** — a route restricted to `keyuser,admin` returns
   403 for a session holding only `user`.
3. **Fresh roles** — changing a signed-in user's roles is reflected in
   the trusted headers of their very next request (no re-login).
4. **Immediate deactivation** — deactivating a signed-in user causes
   their next request to be rejected/redirected to login.
5. **Last-admin protection** — removing `admin` from (or deactivating)
   the only active admin is rejected.
6. **Self-service password** — a user can change their own password
   with the correct current password; a wrong current password is
   rejected; the new password works, the old one no longer does.
7. **No hash exposure** — the user list operation never contains
   password hashes.

## 6. Dependencies

None (foundation; the gateway depends on identity, not vice versa).

## 7. Maturity

`draft` — v0.2.0 adds user management to the v0.1 outline. Open points
for later versions: external identity providers (Keycloak/LDAP/OIDC),
2FA (required by the internet hardening profile), forced password
change on first login, user deletion/GDPR semantics, per-app service
accounts.
