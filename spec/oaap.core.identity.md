# oaap.core.identity — Identity & Roles

- **ID:** `oaap.core.identity`
- **Version:** 0.3.2
- **Maturity:** draft
- **Based on:** RFC-0001, RFC-0002, RFC-0007, RFC-0008
- **Scope of this version:** built-in minimal identity provider with
  user management. External identity providers (Keycloak, LDAP, OIDC)
  are out of scope and must be able to replace this provider later
  without changing the gateway contract. 0.3.0 adds the `server_admin`
  role (RFC-0008) and free-form visibility groups (RFC-0007). 0.3.2
  adds the tenant membership of `oaap.core.tenant` 0.1 — a field and a
  migration, invisible while a node has one tenant.

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

The standard roles from RFC-0002 and RFC-0008 exist on every
installation and are not user-definable in this version:

`server_admin`, `admin`, `keyuser`, `user`, `guest`, `partner`, `public`

`public` is a route marker (no authentication), never a role held by a
user account. A user account holds **one or more** of the other six.

`server_admin` (RFC-0008) is full platform administration authority —
users, groups, edge/external routing, backup, store, and the
visibility-group bypass (2.6). It is **never** forwarded to apps as
something app-specific to interpret; it exists only for platform/
CLI/portal gates. `admin` keeps its pre-0.3.0 meaning unchanged: an
app-facing role, forwarded to apps via `X-OAAP-Roles` exactly as
before, carrying no platform authority by itself. The two are granted
independently — a user can hold `admin` (full administrative function
inside one app) without holding `server_admin` (control of the OAAP
server itself), and vice versa.

### 2.2 User model

Each user account has at least:

| Field          | Rules                                                                           |
| -------------- | ------------------------------------------------------------------------------- |
| `username`     | unique, immutable after creation, `[a-z0-9][a-z0-9._-]*`, 2–40 chars, lowercase |
| `display_name` | optional free text; portal UX only — apps receive the `username`                |
| `roles`        | non-empty subset of {server_admin, admin, keyuser, user, guest, partner}        |
| `groups`       | free-form visibility tags (RFC-0007), default empty — see 2.6                   |
| `tenant`       | the tenant this user belongs to (`oaap.core.tenant` 1.1); absent means the default tenant |
| `active`       | boolean; inactive users cannot sign in and existing sessions stop verifying     |
| password       | stored only as a salted hash; minimum length 8                                  |

**Tenant membership (0.3.2).** A user belongs to exactly one tenant.
The field is written by the migration of `oaap.core.tenant` 1.5 and is
otherwise not settable in this version — there is only one tenant to
belong to. It changes **nothing** about authentication: no new header,
no new parameter, no change to the login screen. An app must never
learn which tenant its caller belongs to; the day it needs to know, the
boundary is in the wrong place (RFC-0022 non-goals).

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
  authorization, spec `oaap.apps.runtime` 2.4). No bypass exists for
  this check — `server_admin` does not automatically satisfy a role
  restriction it is not itself listed in (RFC-0008: it carries no
  implied app-facing role).
- Verify accepts an optional group restriction (`?groups=a,b`,
  RFC-0007) — an ADDITIONAL check alongside roles: the session must
  hold at least one of the listed groups, **unless** it holds
  `server_admin`, which bypasses the group check unconditionally
  (2.6). Absent, this parameter changes nothing (today's behavior).
- **Fresh state per request:** verify MUST evaluate the *current* user
  store on every call. Deactivating a user or changing their roles or
  groups takes effect on their next request — waiting for re-login is
  not acceptable. (Sessions may cache the username, never the roles or
  groups.)

### 2.4 User management

- Managing users is restricted to sessions holding the `server_admin`
  role (RFC-0008 — this operates on the server itself). The portal
  provides the UI; identity provides the operations.
- Operations: **list** users (never exposing password hashes),
  **create** (username, initial password, roles, groups, display
  name), **update** (roles, groups, display name, active flag — not
  the username), **set password** (server_admin sets a new password
  for any user).
- **Last-server_admin protection:** an operation that would leave the
  platform without at least one *active* user holding `server_admin`
  MUST be rejected (losing the last one would lock everyone out of
  user, edge, external-route and store management). There is no
  equivalent protection for `admin` any more — it is an ordinary
  app-facing role.
- **Self-service password change:** every signed-in user can change
  their own password by providing the current one. No other
  self-service exists in this version.
- Deleting users is not part of this version — deactivate instead
  (audit trails in apps may reference the username). Deletion semantics
  (including GDPR aspects) are an open point for a later version.

### 2.5 Bootstrap

The first user is created via the portal's first-run wizard, protected
by the one-time setup token (see `oaap.core.host` 2.2). Until setup is
completed, no other request is served. The first user receives the
roles `server_admin`, `admin` and `keyuser` (RFC-0008: the common
single-operator install needs no further role setup — this user can
both administer the platform and use every app's own admin functions,
and can designate further server admins).

**Upgrade migration (RFC-0008, one-time):** on the first start after
adding `server_admin`, every existing user holding `admin` also
receives `server_admin`, so nobody presently trusted with the server
loses access when the two roles split apart. Recorded by a flag so it
runs exactly once; after this point the two roles are granted
independently.

### 2.6 Visibility groups (RFC-0007)

- `groups` is a free-form list of short tags on a user record — no
  group registry, no rename/delete workflow; a group exists the moment
  any user carries the tag (deliberately simple, matching the
  `oaap.apps.runtime` `visibility` field on app instances, spec 2.7).
- Validation mirrors usernames: lowercase `[a-z0-9][a-z0-9._-]*`, max
  40 characters, deduplicated.
- Checked by `/verify`'s optional `?groups=` parameter (2.3) —
  identity does not know about app instances or their visibility
  setting; the gateway config generator supplies the group list to
  check per route, exactly as it already does for roles.
- `server_admin` bypasses every group restriction unconditionally
  (2.1) — the platform administrator sees and reaches every instance
  regardless of visibility.
- No `X-OAAP-Groups` header exists or is planned — groups are a
  platform-level visibility switch, not part of the App Deployment
  Contract. An app that wants group-aware behavior has no API for that
  in this version.

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
3. Management operations are only reachable through a
   server_admin-authenticated surface; the identity-internal API is
   never exposed through the gateway. **The internal API additionally
   requires a shared platform key** (RFC-0015 addendum A4): being on the
   internal container network is not proof of anything, because every
   app instance runs on that same network. The key is held only by the
   platform services that legitimately call the internal API (the
   portal) and is delivered to them at install time; identity **fails
   closed** — a missing key disables the internal API rather than
   opening it. Login, `/verify` and app traffic do not use the internal
   API and are unaffected. Without this, code inside any installed app
   container could create itself a `server_admin` account. Superseded
   in full once each app runs on its own network (RFC-0015 A4 step 2),
   which removes the reachability rather than guarding it.
4. Failed logins return a generic error (no username enumeration).
5. Role, group and deactivation changes act on the next request (see 2.3).
6. Anti-spoofing is the gateway's duty (deployment contract guarantee
   1); identity supports it by being the only source of the trusted
   headers.
7. `server_admin` is never forwarded to apps as anything they should
   treat specially — it is a platform gate only (2.1). Granting it only
   to another `server_admin` (never to a user holding merely `admin`)
   is enforced structurally: the management surface itself requires
   `server_admin` to reach at all (requirement 3).

## 5. Conformance tests (described)

1. **Create and sign in** — server_admin creates user `verwaltung` with
   role `keyuser`; that user can sign in and reaches a `keyuser` route.
2. **Role enforcement** — a route restricted to `keyuser,admin` returns
   403 for a session holding only `user`.
3. **Fresh roles** — changing a signed-in user's roles is reflected in
   the trusted headers of their very next request (no re-login).
4. **Immediate deactivation** — deactivating a signed-in user causes
   their next request to be rejected/redirected to login.
5. **Last-server_admin protection** — removing `server_admin` from (or
   deactivating) the only active server_admin is rejected; removing
   plain `admin` from the last admin is NOT rejected (it carries no
   platform protection).
6. **Self-service password** — a user can change their own password
   with the correct current password; a wrong current password is
   rejected; the new password works, the old one no longer does.
7. **No hash exposure** — the user list operation never contains
   password hashes.
8. **Group bypass** — a route restricted to `?groups=finanzen` returns
   403 for a session with neither `finanzen` in its groups nor
   `server_admin` in its roles; a session with `server_admin` (but not
   `finanzen`) still passes.
9. **admin/server_admin independence** — a user holding only `admin`
   cannot reach `/users`, `/store`, `/instances` or `/health`; a user
   holding only `server_admin` (not `admin`) can manage users but does
   not automatically gain any app's own admin-level function.
10. **Internal API requires the platform key** (RFC-0015 A4) — a request
    to any `/internal/*` route without the shared key is rejected (401);
    the same request with the key succeeds. With no key configured on
    the node, every `/internal/*` route is disabled (503), never open.
    The guard is by path prefix, so a newly added internal route is
    covered without a per-route change.

## 6. Dependencies

None (foundation; the gateway depends on identity, not vice versa).

## 7. Maturity

`draft` — v0.2.0 added user management to the v0.1 outline; v0.3.0
adds the `server_admin` role (RFC-0008) and visibility groups
(RFC-0007). Open points for later versions: external identity
providers (Keycloak/LDAP/OIDC), 2FA (required by the internet
hardening profile), forced password change on first login, user
deletion/GDPR semantics, per-app service accounts, `tenant_admin`
(future — explicitly out of scope for RFC-0008, see multi-tenancy in
the capability backlog), managed group objects (RFC-0007 kept groups
free-form deliberately; revisit if renaming-safety or a full overview
of groups in use becomes a real need).

## German summary / Deutsche Zusammenfassung (server_admin & Sichtbarkeitsgruppen, v0.3.0)

**server_admin (RFC-0008):** Neue Rolle für die echte
Server-Verwaltung (Benutzer, Gruppen, Edge/externe Routen, Backup,
Store) — nie an Apps weitergereicht. `admin` bleibt unverändert die
App-Rolle ohne Server-Wirkung; beide werden unabhängig vergeben. Der
Ersteinrichtungs-Benutzer bekommt beide Rollen. Bestehende
Installationen: alle heutigen `admin`-Träger bekommen beim Update
einmalig zusätzlich `server_admin` — niemand verliert Zugriff. Nur
`server_admin` darf weitere `server_admin` vergeben (strukturell
erzwungen, da die Benutzerverwaltung selbst `server_admin` erfordert).
Der Schutz „mindestens ein aktiver Administrator bleibt" gilt jetzt
für `server_admin`, nicht mehr für `admin`.

**Sichtbarkeitsgruppen (RFC-0007):** Freie Stichworte je Benutzer
(`groups`), keine Gruppen-Verwaltung — eine Gruppe existiert, sobald
irgendein Benutzer sie trägt. `/verify` prüft optional `?groups=...`
zusätzlich zu den Rollen; `server_admin` sieht immer alles. Kein neuer
Header an Apps — der Deployment Contract bleibt unverändert.

## Deutsche Zusammenfassung (interne API mit Plattform-Schlüssel, v0.3.1)

Ein bei der Beantwortung von RFC-0015 gefundener Sicherheitsfehler ist
geschlossen. Die interne API von Identity (`/internal/*`, u. a.
Benutzer anlegen samt Rollen) war allein dadurch geschützt, „im
Container-Netz erreichbar" zu sein — **jede installierte App läuft aber
in genau diesem Netz.** Damit konnte Code in jedem App-Container sich
selbst ein `server_admin`-Konto anlegen und die ganze Plattform
übernehmen (von außen nicht erreichbar, aber jede installierte App,
auch fremde Images, hätte es gekonnt). Neu: Jeder Aufruf von
`/internal/*` braucht einen **gemeinsamen Plattform-Schlüssel**, den
nur die berechtigten Plattformdienste (das Portal) besitzen und der bei
der Installation erzeugt wird. Identity **verweigert im Zweifel** —
fehlt der Schlüssel, ist die interne API abgeschaltet, nicht offen.
Anmeldung, `/verify` und App-Verkehr laufen nicht über die interne API
und sind unberührt. Der Schutz per Pfad-Präfix deckt auch künftige
`/internal/*`-Routen automatisch ab. Bestehende Knoten bekommen den
Schlüssel bei `sudo oaap update` erzeugt und die beiden Dienste einmal
neu erzeugt. **Die eigentliche Lösung** ist ein eigenes Netz je App
(RFC-0015 A4, Schritt 2) — dieser Schlüssel schließt die Lücke sofort,
bis die Netz-Trennung die Erreichbarkeit ganz beseitigt.
