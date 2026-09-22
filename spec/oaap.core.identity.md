# oaap.core.identity — Identity & Roles

- **ID:** `oaap.core.identity`
- **Version:** 0.4.0 (a user has an identity of its own — an immutable
  UUID, an e-mail field with a verification state, three further
  trusted headers, a deep link that survives the login, and a write
  lock on the user store; RFC-0040)
- **Maturity:** draft
- **Based on:** RFC-0001, RFC-0002, RFC-0007, RFC-0008, RFC-0026,
  RFC-0036, RFC-0038, RFC-0040
- **Scope of this version:** built-in minimal identity provider with
  user management. External identity providers (Keycloak, LDAP, OIDC)
  are out of scope and must be able to replace this provider later
  without changing the gateway contract. 0.3.0 adds the `server_admin`
  role (RFC-0008) and free-form visibility groups (RFC-0007). 0.3.2
  adds the tenant membership of `oaap.core.tenant` 0.1 — a field and a
  migration, invisible while a node has one tenant. 0.3.3 makes that
  membership operative (`oaap.core.tenant` 0.2): the `tenant_admin`
  role, a tenant boundary the gateway enforces, and user management
  scoped to one tenant. Still invisible while a node has one tenant.
  0.3.4 names the self-service surface an app may use (2.7): the
  `/auth/*` guarantee on every entry point, and `GET /auth/whoami`.
  0.3.5 extends self-service (2.4) to a user's own `display_name`, per
  RFC-0036 D3 — the one field of their own record that carries no
  privilege. **0.4.0 applies RFC-0026's principle to the user record**
  (RFC-0040): the record gets an identity that is not its name, an
  e-mail field with a verification state, three further trusted
  headers, a login that returns the visitor to where they were going,
  and a lock on the file every change rewrites. Nothing is removed and
  nothing is renamed — the change is additive throughout, because
  `X-OAAP-User` is *de facto* immutable today and apps may already be
  relying on that.

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

`server_admin`, `tenant_admin`, `support`, `admin`, `keyuser`, `user`,
`guest`, `partner`, `public`

`public` is a route marker (no authentication), never a role held by a
user account. A user account holds **one or more** of the other eight.

`support` (RFC-0039) is the read-only counterpart to `server_admin`:
the service provider who looks after this node and reads its node-wide
status surfaces, changing nothing. `partner` carries no platform
authority at all — it is the app-facing classification RFC-0002
defined, and nothing more.

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

`tenant_admin` (0.3.3, RFC-0008's deferred half) is administration
authority **inside one tenant** — the tenant of the holder's own user
record, never one named in a request. It is a platform role like
`server_admin`, is likewise never forwarded to apps as something to
interpret, and is bounded by three rules that `oaap.core.tenant` 2.3
states in full: it may not grant `server_admin`, it may not touch a
user of another tenant, and the tenant it acts in comes from the actor.
Without those, the role is a two-step path to the whole node.

### 2.2 User model

Each user account has at least:

| Field            | Rules                                                                           |
| ---------------- | ------------------------------------------------------------------------------- |
| `id`             | **the identity** (0.4.0): a UUID, assigned at creation, immutable and never reused — see below |
| `username`       | unique, immutable in this version, `[a-z0-9][a-z0-9._-]*`, 2–40 chars, lowercase — **a name, not the key** |
| `display_name`   | optional free text, max 80 characters; carried to apps since 0.4.0              |
| `email`          | optional address (0.4.0), max 254 characters; see the verification rule below    |
| `email_verified` | boolean (0.4.0); false unless somebody proved the address                        |
| `roles`          | non-empty subset of {server_admin, tenant_admin, support, admin, keyuser, user, guest, partner} |
| `groups`         | free-form visibility tags (RFC-0007), default empty — see 2.6                   |
| `tenant`         | the tenant this user belongs to (`oaap.core.tenant` 1.1); absent means the default tenant |
| `active`         | boolean; inactive users cannot sign in and existing sessions stop verifying     |
| password         | stored only as a salted hash; minimum length 8                                  |

**The identity is not the name (0.4.0, RFC-0040 D1).** RFC-0026 settled
this principle for the platform — *identity is a UUID, and every name a
human reads is an alias that may change* — and applied it to instances
and tenants. The user record was the one place it was never applied.

- `id` MUST be a UUID, assigned when the record is created, **immutable
  and never reused**, including after deactivation. No operation
  changes it; a request that names one is ignored, not honoured.
- Existing records receive one on the first start after the update
  (2.5). An implementation MUST NOT leave a record without an `id`: the
  absence is not an error anybody sees, it is an app anchoring its
  permissions on an empty string.
- `username` keeps its present meaning, spelling and content
  (RFC-0040 D3). It is *de facto* immutable today only because no
  rename and no delete operation exists (2.4) — that is a gap, not a
  guarantee, and it is exactly why the identity is introduced before
  anybody writes a permission model against the name.
- **Renaming a user remains out of scope.** This version makes one
  possible later without breaking anyone; it does not offer one.

**The address, and whether anybody proved it (0.4.0, RFC-0040 §3.2).**
`email` and `email_verified` always travel together.

- Setting a **different** address MUST clear `email_verified`. An
  address that changed is an address nobody proved, and a flag left
  standing from the previous one is a lie the platform would then put
  in a header.
- The flag is set only by a deliberate assertion: in this version an
  administrator stating that the address belongs to the person, later
  the verification flow a foreign identity provider brings (RFC-0040
  §6). **This version adds no e-mail sending and no verification mail.**
- Validation is deliberately loose (one `@`, something either side of
  it, no spaces, at most 254 characters). The platform is not the
  arbiter of address syntax; the flag, not the pattern, is what says
  whether an address is real.

**Tenant membership (0.3.3).** A user belongs to exactly one tenant.
The field is written by the migration of `oaap.core.tenant` 1.5, and
from 0.3.3 it is **chosen when the account is created** and never
changed afterwards: moving a user between tenants is moving a person
between customers, and the honest form of that is a new account, not a
field edit. A tenant named in a create request MUST be one this node
has (`oaap.core.tenant` 2.5: unknown never means default), and a
`tenant_admin` may name only their own.

It still changes **nothing** on the app side: no new header, no change
to the login screen, and no way for an app to learn which tenant its
caller belongs to. The day an app needs to know, the boundary is in the
wrong place (RFC-0022 non-goals). What it does change is *where the
session may go* — see the tenant restriction in 2.3.

### 2.3 Authentication contract with the gateway

- Identity issues a session on successful login; the gateway calls
  identity's verify endpoint on **every** request to a protected route
  (forward auth, RFC-0002 default deny).
- On success, verify returns **five** trusted headers (0.4.0; the first
  two unchanged since RFC-0002), and the gateway copies them onto the
  upstream request. On failure it returns a redirect to the login page
  (browser flows) or 401/403.

  | Header | Content |
  | --- | --- |
  | `X-OAAP-User` | the username — a name, unchanged |
  | `X-OAAP-Roles` | comma-separated roles |
  | `X-OAAP-User-Id` | the `id` of 2.2 — **the thing an app anchors on** |
  | `X-OAAP-Display-Name` | the display name, may be empty |
  | `X-OAAP-Email` | a **verified** address, or empty — see below |

  - **All five MUST be returned on every success, empty where there is
    no value.** A header the answer leaves out is a header whose
    client-sent value has nothing to overwrite it, and the
    anti-spoofing guarantee (4.6) works by overwriting. Apps MUST read
    empty and absent as the same thing.
  - **They MUST come from the one verify answer**, written by the same
    copy list the gateway already uses — one source, no second truth.
  - **An unverified address is NOT sent** (RFC-0040 D2). An address
    arriving in a platform header is read as proven whatever flag
    stands beside it, and handing over an unchecked claim is the wrong
    default. `X-OAAP-Email` therefore carries a verified address or
    nothing at all. (The requesting project asked for the address plus
    a flag; this is the narrower answer and can be widened later
    without breaking anybody.)
  - **Header encoding (RFC-0040 D4).** `X-OAAP-Display-Name` and
    `X-OAAP-Email` MUST be **UTF-8 percent-encoded** unless the value
    is printable ASCII *and* contains no `%`, in which case it is sent
    plain so the common case stays readable. The percent sign is
    included so that the instruction to apps has no exception:
    **always percent-decode.** Arbitrary Unicode in an HTTP header does
    not fail cleanly — it is mojibake in one app and a dropped header
    in another, discovered in production.
  - **The rule apps are given** (App Deployment Contract): *anchor on
    `X-OAAP-User-Id`, display `X-OAAP-User` and `X-OAAP-Display-Name`.*
    That is RFC-0026's sentence, one level down.
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
- Verify accepts an optional **tenant restriction** (`?tenant=<id>`,
  `oaap.core.tenant` 3.1) — the boundary of belonging, enforced here
  and nowhere else. The session's user must belong to the named tenant,
  **unless** it holds `server_admin` (RFC-0022 D5: the operator may
  reach everything, and the audit log is the counterweight). A tenant
  parameter naming a tenant this node does not have is refused, never
  treated as the default one. Absent, this parameter changes nothing —
  which is why nothing changes on a single-tenant node.
- **A refusal must be readable across origins** (RFC-0038 follow-up).
  Every refusal a generated gateway site can produce comes from here —
  the verify endpoint and the throttle check are the only forward-auth
  calls such a site makes — so the rule belongs here and nowhere else. A
  refusal answering a request whose `Origin` is **not** the origin of the
  site it was aimed at MUST carry that origin in
  `Access-Control-Allow-Origin`, add `Vary: Origin`, and expose
  `WWW-Authenticate`; it MUST NOT carry
  `Access-Control-Allow-Credentials`. A refusal that would be a redirect
  to the login form MUST instead be `401` with `WWW-Authenticate`, unless
  the request is a browser navigation. The full rule and its reasons are
  in `oaap.core.gateway`.
  The site's own origin is determined from the forwarding headers the
  gateway sets, never from the host identity itself was reached at —
  which is always the internal service address and therefore useless
  here.
- **A refused request keeps its return target (0.4.0, RFC-0040 §5).**
  Until 0.3.6 the loss was total: the refusal redirected to the login
  form with no return target, and a successful login redirected to `/`.
  Only the *instance* survived, because the browser stays on the same
  hostname. An invitation link is the ordinary case this breaks, and
  invitations are how every delegated-administration model brings
  people in.
  - The refusal MUST carry the originally requested **path and query**
    to the login form, and a successful login MUST return the visitor
    there.
  - **Only a local path may be accepted** (RFC-0040 D5): it MUST begin
    with a single `/`, MUST NOT begin with `//` or `/\`, MUST carry no
    scheme and no host, and MUST contain no control characters;
    anything else falls back to `/`. A return target taken from a URL
    is the classic open-redirect hole — a link to our own login page
    that sends the visitor to somebody else's site *after* they signed
    in — so the rule belongs in the specification, not in a code
    review. The value MUST be validated again when it comes back from
    the form: it travelled through the visitor's browser.
  - **A deliberate sign-out carries no return target.** Somebody who
    signs out asked to leave the page they were on.
  - A **fragment** (`#…`) is never involved: browsers do not send it to
    a server. It survives a redirect on its own if the browser carries
    it, and the platform makes no promise about that.
- **Fresh state per request:** verify MUST evaluate the *current* user
  store on every call. Deactivating a user or changing their roles or
  groups takes effect on their next request — waiting for re-login is
  not acceptable. (Sessions may cache the username, never the roles or
  groups.)

### 2.4 User management

- Managing users is restricted to sessions holding `server_admin`
  (RFC-0008 — this operates on the server itself) or, **within their
  own tenant only**, `tenant_admin` (0.3.3). The portal provides the
  UI; identity provides the operations.
- **A `tenant_admin` sees and changes only their own tenant's users.**
  A request naming a user of another tenant is answered exactly as a
  request naming a user who does not exist: "not found". Answering
  "forbidden" would confirm that the username is taken on this node,
  which is already an answer across the boundary.
- **A `tenant_admin` may not grant a role whose authority reaches past
  a tenant** — `server_admin` and `support` — and may not grant
  `tenant_admin` outside their own tenant. All are refused, not
  silently dropped.
- Operations: **list** users (never exposing password hashes),
  **create** (username, initial password, roles, groups, display name,
  e-mail address), **update** (roles, groups, display name, e-mail
  address and its verification flag, active flag — not the username
  and **never** the `id`), **set password** (server_admin sets a new
  password for any user).
- **An address is created unverified (0.4.0).** Create accepts an
  address and stores it with `email_verified` false: an address an
  administrator types is not thereby proven. Asserting it is a
  separate, deliberate update. An assertion arriving together with a
  *changed* address MUST be refused (2.2) — and the refusal MUST be
  visible to whoever made it, not swallowed, or an administrator
  leaves the page believing an address was proven.
- **A user's `id` is visible to the administration surface**, so that
  the one field a support question is about can be looked up. An
  address is only ever shown together with its verification state.
- **Last-server_admin protection:** an operation that would leave the
  platform without at least one *active* user holding `server_admin`
  MUST be rejected (losing the last one would lock everyone out of
  user, edge, external-route and store management). There is no
  equivalent protection for `admin` any more — it is an ordinary
  app-facing role.
- **Self-service password change:** every signed-in user can change
  their own password by providing the current one.
- **Self-service display name (RFC-0036 D3, 0.3.5):** every signed-in
  user can change their own `display_name` — the one field of their
  own record that carries no privilege, so there is no security reason
  it stayed admin-only. Every other field of the user record (roles,
  groups, tenant, username, active flag) stays admin-only, unchanged
  — this route touches nothing but the display name.
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

**Identity backfill (0.4.0, RFC-0040 §7).** On every start, a record
without an `id` receives one, written once. This is deliberately
**not** guarded by a run-once flag, unlike the migrations below: those
change what a record *means* (a role granted, a tenant joined), so
repeating them would undo an operator's cleanup. Filling in a missing
identity changes no meaning and is idempotent — and without the flag it
also heals what a flag would miss: a user store restored from a backup
older than the update, a file edited on the machine, a creation path
nobody remembered. Together with the rule that every write assigns a
missing `id`, a record without an identity survives neither a write nor
a restart.

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

### 2.7 The self-service surface an app may use (0.3.4)

Apps render their own chrome. The platform owes them the *facts* about
the person in front of the screen and the *addresses* of the actions it
owns — never the widget.

- **`/auth/*` is reachable on every instance entry point**, not only on
  the portal, because the gateway reserves that prefix on every
  generated site (`oaap.core.gateway`). An app may therefore link to
  `/auth/password` and `/auth/logout` **relative to its own address**,
  with no platform change and no cross-origin request. This is a
  guarantee, not an accident of the current configuration.
- **`GET /auth/whoami`** answers the same question `/verify` answers,
  in a form a page can read: JSON describing **the caller and nobody
  else**. It authenticates exactly like every other route — a session
  cookie or an API key (RFC-0027), resolved by the one shared method
  list — and refuses an unauthenticated caller with 401 rather than a
  login redirect, because its caller is a script, not a browser
  following links.
- **Fields:** `username`, `id` (0.4.0 — the same value
  `X-OAAP-User-Id` carries), `display_name` (empty string when unset —
  never invented from the username), `email` (0.4.0 — a **verified**
  address or an empty string, exactly the rule the header follows;
  **not** percent-encoded, because JSON carries Unicode natively and
  D4's encoding exists only for HTTP headers), `roles` (exactly the
  list `X-OAAP-Roles` carries for this request), `kind` (`human` or
  `machine`), and `links`, an object holding the addresses the app may
  offer: `password` and `logout` for a human, `logout` only for a
  machine principal, which has no password to change. `logout` is a
  **POST**, not a link — a sign-out that any foreign page can trigger
  by embedding an image is a nuisance, not a feature. Identity accepts
  no GET there, so the rule enforces itself.
- **The roles field and the header MUST be the same list.** whoami is a
  second *reading* of one truth, never a second truth. An
  implementation that computes roles separately here is wrong even
  while the two agree.
- **No tenant is returned, and none will be.** The tenant boundary is
  enforced at the gateway before the app is reached (2.3,
  `oaap.core.tenant` 3.1). Handing an app its caller's tenant would
  invite the app to filter by it — a second, weaker enforcement one bug
  away from a leak between customers, and on a single-tenant node it
  would additionally make tenants visible where nothing may be
  (`oaap.core.tenant` 2.4).
- **No groups are returned**, for the reason 2.6 already gives for the
  absent header: visibility is a platform switch, not part of the App
  Deployment Contract.
- **The answer MUST NOT be cached** (`Cache-Control: no-store`): it
  describes the current session, and a shared cache holding it would
  hand one person's name to the next.
- Beyond this, no self-service exists in this version. A user can
  change their own display name (2.4, 0.3.5) and their own password;
  their roles, groups, tenant, active flag, `id` and **e-mail address**
  stay admin-only. The address is deliberately not self-service while
  the platform cannot send a verification mail: a self-set address
  could never be more than unverified, and would therefore reach no app
  anyway (2.3).

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
7. **Every change to the user store happens under an exclusive lock**
   (0.4.0, RFC-0040 D6). The store is rewritten whole on every change —
   read, modify, write — so two concurrent changes lose one of them,
   and lose it *silently*: the surviving file is complete and valid, it
   simply does not contain what the other writer did. **The lock MUST
   span the read**, not merely the write; a lock taken around the write
   alone protects a copy that was already stale.
   This is unreachable while an administrator creates accounts one at a
   time, and ordinary the moment records are created by **incoming
   traffic** — which is what a foreign identity provider and
   self-registration bring. It is required here rather than in the
   version that needs it, because by then the fault is live. Reads need
   no lock: the store is swapped in atomically, so a reader sees the
   old file or the new one, never half of either.
8. **A user record without an `id` MUST NOT be producible** (0.4.0).
   Every write assigns a missing one, and every start backfills
   (2.2, 2.5). This is belt and braces on purpose: an identifier whose
   absence is silent has caught this platform repeatedly, and here the
   damage would land in an outside application's authorization model.
9. `server_admin` is never forwarded to apps as anything they should
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
11. **The tenant boundary holds at the gateway** (0.3.3) — a session
    whose user belongs to tenant A receives 403 on a route verified
    with `?tenant=<B>`, and the upstream app is never reached; the same
    session with `server_admin` passes; without the parameter nothing
    changes.
12. **A `tenant_admin` is bounded** (0.3.3) — they can create, list and
    change users of their own tenant; a request naming a user of
    another tenant answers "not found", not "forbidden"; granting
    `server_admin` or `support`, or naming a foreign tenant on create,
    is refused. Granting `partner` is allowed (RFC-0039): it reaches
    nowhere past the tenant.
13. **whoami answers about the caller** (0.3.4, 2.7) — a signed-in user
    receives their own username, display name and roles; the `roles`
    field is byte-identical to the `X-OAAP-Roles` header the same
    session receives from `/verify`; an unauthenticated caller receives
    401 and no body describing anybody; an API key receives the key's
    effective (narrowed) roles, not the principal's full set.
14. **whoami leaks no boundary** (0.3.4, 2.7) — the answer contains no
    tenant and no groups, on a single-tenant node and on a multi-tenant
    one alike; it carries `Cache-Control: no-store`.
15. **The `/auth/*` guarantee** (0.3.4, 2.7) — on an instance's own
    entry point, `/auth/password`, `/auth/logout` and `/auth/whoami`
    reach identity and not the app, even when the app declares a route
    of the same path.
16. **Self-service display name touches nothing else** (0.3.5, RFC-0036
    D3) — a signed-in user changing their own `display_name` cannot,
    through the same request, change their roles, groups, tenant,
    username or active flag; a name over 80 characters is rejected with
    no change made; an unauthenticated request is redirected to login,
    never accepted.
17. **Every user has an identity, and it does not move** (0.4.0) — a
    user store written before the update has an `id` on every record
    after the first start, including inactive ones; a second start
    assigns none anew; changing a display name, a password, roles or
    the active flag leaves it untouched; an `id` named in a create or
    update request is ignored; a record appended without one is
    written with one.
18. **All five headers, every time** (0.4.0, 2.3) — a successful verify
    returns exactly the five headers, with an empty value where the
    record has none, never a shorter list; `X-OAAP-User-Id` is the
    stored `id`; `X-OAAP-User` is byte-identical to what the same
    session received before the update.
19. **An unverified address reaches nobody** (0.4.0, RFC-0040 D2) — an
    address stored without the flag appears neither in
    `X-OAAP-Email` nor in whoami; asserted, it appears in both;
    changing the address while asserting it clears the flag and empties
    the header again, and the refusal is reported to the caller.
20. **A non-ASCII display name survives** (0.4.0, RFC-0040 D4) — a
    display name containing umlauts arrives percent-encoded and decodes
    to the original; a pure-ASCII name without `%` arrives plain; an
    ASCII name containing `%` arrives encoded, so percent-decoding is
    correct for every value.
21. **The return target is local or nothing** (0.4.0, RFC-0040 D5) — a
    refused request to `/einladung?tok=x` sends the visitor to the
    login form and, after a successful login, back to
    `/einladung?tok=x`; each of `//host`, `/\host`, `https://host/`,
    `host`, a value with a control character and an over-long value
    lands on `/` instead, both when it arrives from the gateway and
    when it comes back from the form; the login form itself is not a
    return target; a comma in the path is not truncated.
22. **The user store is never written without the lock** (0.4.0,
    RFC-0040 D6) — every operation that changes a user holds it across
    read and write, including the ones on the machine (CLI) rather than
    through the portal; two concurrent creations of different users
    both survive.

## 6. Dependencies

None (foundation; the gateway depends on identity, not vice versa).

## 7. Maturity

**Recorded, not fixed here (0.4.0, RFC-0040 §4.1).** Verify parses the
*entire* user store and scans it linearly **on every request**. At a
dozen users that is free; at a thousand it is a few hundred kilobytes
of JSON per request across the workers; at ten thousand it does not
hold. The administration list has no paging and no search, and the
store is per node rather than per tenant, so backup-per-tenant
(`oaap.core.tenant` D7) does not cover identities. None of that is
addressed in this version — it is written down because the direction
towards a foreign identity provider is what makes those numbers
plausible, and because the answer given to an outside project should
match what is recorded.

`draft` — v0.2.0 added user management to the v0.1 outline; v0.3.0
adds the `server_admin` role (RFC-0008) and visibility groups
(RFC-0007); v0.3.3 adds `tenant_admin` and the tenant boundary
(`oaap.core.tenant` 0.2); v0.3.4 names the app-facing self-service
surface (2.7); v0.3.5 extends self-service to the user's own
`display_name` (RFC-0036 D3); v0.4.0 gives the user record an identity
of its own, an e-mail field with a verification state, three further
trusted headers, a login that returns the visitor to where they were
going, and a lock on the user store (RFC-0040). Open points for later versions: external identity
providers (Keycloak/LDAP/OIDC), 2FA (required by the internet
hardening profile), forced password change on first login, user
deletion/GDPR semantics, per-app service accounts, moving a user
between tenants (2.2 deliberately has no such operation), managed
group objects (RFC-0007 kept groups
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

## Deutsche Zusammenfassung (Self-Service Anzeigename, v0.3.5, RFC-0036 Teil B)

**Eine neue Seite, `/auth/profile`, analog zu `/auth/password`.** Jeder
angemeldete Nutzer kann seinen eigenen Anzeigenamen selbst ändern, ohne
einen Admin zu bitten — bisher ging das nur beim Passwort. Bewusst
klein geschnitten: Rollen, Gruppen, Mandant, Benutzername und
Aktiv-Status bleiben unverändert Admin-Sache, weil sie eine
sicherheitsrelevante Entscheidung tragen; der Anzeigename trägt keine.

## Deutsche Zusammenfassung (die Person hinter dem Namen, v0.4.0, RFC-0040)

**Das Prinzip galt schon — nur nicht für Benutzer.** RFC-0026 hat
festgelegt: Die Identität ist eine unveränderliche Kennung, jeder Name,
den ein Mensch liest, ist ein Alias. Für Instanzen und Mandanten war das
umgesetzt; der Benutzersatz war die einzige Stelle ohne dieses Prinzip.
`X-OAAP-User` trägt den Anmeldenamen, und der Anmeldename *war* der
Schlüssel — gutgegangen ist das nur, weil es weder Umbenennen noch
Löschen gibt. Das ist eine Lücke, keine Zusage.

**Was jetzt drin ist, und was sich für heute laufende Apps ändert:
nichts.** Alles ist *zusätzlich*. `X-OAAP-User` behält Namen,
Schreibweise und Inhalt.

1. **Eine Kennung je Benutzer** — eine UUID, beim Anlegen vergeben,
   unveränderlich, **nie wieder vergeben**, auch nach dem Deaktivieren
   nicht. Bestandsbenutzer bekommen sie beim ersten Start nach dem
   Update. Kein Auftrag kann sie ändern; steht eine im Auftrag, wird
   sie ignoriert. **Die Regel für Apps lautet ab jetzt: auf die
   Kennung verankern, den Namen anzeigen.**
2. **Ein E-Mail-Feld mit Prüfmerkmal** — vorher gab es gar keines. Eine
   Adresse, die ein Administrator eintippt, ist damit *nicht* bewiesen:
   das Häkchen „geprüft" ist ein zweiter, bewusster Schritt, und
   **ändert sich die Adresse, fällt das Häkchen**. Die Plattform
   verschickt in dieser Version keine Post; das Feld ist die Stelle, an
   die später ein Identitätsanbieter eine geprüfte Adresse schreibt.
3. **Drei weitere Kopfzeilen an Apps** — Kennung, Anzeigename, E-Mail,
   neben den zwei unveränderten. Immer alle fünf, leer wo es keinen Wert
   gibt: eine *fehlende* Kopfzeile hätte nichts, was einen vom Besucher
   mitgeschickten Wert überschreibt — und genau davon lebt die
   Fälschungssicherheit. **Eine ungeprüfte Adresse bekommt keine App zu
   sehen** (was in einer Plattform-Kopfzeile steht, gilt dort als
   bewiesen, egal welches Merkmal danebensteht). Umlaute werden
   prozentkodiert, weil beliebiges Unicode in HTTP-Kopfzeilen nicht
   sauber scheitert, sondern in einer App als Zeichensalat ankommt und
   in der nächsten ganz fehlt.
4. **Ein tiefer Link übersteht die Anmeldung** — bisher gingen Pfad und
   Query verloren, erhalten blieb nur die Instanz. Ein Einladungslink
   ist der Alltagsfall, den das kaputt machte. Angenommen wird
   **ausschließlich ein Pfad auf dieser Plattform**; alles andere landet
   auf `/`. Sonst wäre die eigene Anmeldeseite ein Sprungbrett auf eine
   fremde Seite — die klassische Form einer überzeugenden Phishing-Falle.
5. **Eine Sperre auf der Benutzerdatei** — sie wird bei jeder Änderung
   komplett neu geschrieben, und zwei gleichzeitige Änderungen verlieren
   eine davon **lautlos**: die überlebende Datei ist vollständig und
   gültig, sie enthält nur nicht, was der andere getan hat. Heute
   praktisch unerreichbar, weil ein Administrator Konten einzeln anlegt
   — nicht mehr unerreichbar, sobald Sätze durch **eingehenden Verkehr**
   entstehen (Selbstregistrierung, fremder Identitätsanbieter). Die
   Sperre umfasst das Lesen mit, nicht nur das Schreiben: eine Sperre um
   das Schreiben allein schützt eine Kopie, die schon veraltet war.

**Aufgeschrieben, aber nicht behoben:** Die Prüfung zerlegt bei *jeder*
Anfrage die ganze Benutzerdatei und sucht linear. Ab etwa tausend
Benutzern ist das spürbar, bei zehntausend trägt es nicht. Die
Benutzerliste im Portal hat kein Blättern und keine Suche, und die Datei
liegt je Knoten, nicht je Mandant — die Mandantensicherung erfasst
Identitäten deshalb nicht. Das gehört zu dem RFC, das den Speicher
ändert, nicht zu diesem.
