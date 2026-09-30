# RFC-0047: One Account Everywhere — Shared Services for Members of Many Tenants

- **Status:** **Proposed (2026-09-30)** — placeholder, not yet designed.
  Jörg decided to hold this as its own RFC and to start shared services
  with their own logins meanwhile.
- **Date:** 2026-09-30
- **Authors:** Jörg (the wish), Claude (write-up)
- **Depends on:** RFC-0022 (D3: users are not shared, identity providers
  are), RFC-0040 (the person behind the name), RFC-0041 (external identity
  providers, one realm per tenant), RFC-0042 (the tenant as a place)
- **Driver:** A dedicated multi-tenant node hosts one *shared* tenant with
  services for everybody (a Git platform, for example). Members of many
  tenants should reach it with the account they already have.

## Summary

Start: shared services bring **their own logins**. That fits the
Deployment Contract and needs nothing new. The wish is "one account
everywhere". This RFC exists to keep that wish from being solved by
accident.

## Open questions

1. **Whose account?** A shared realm in which every customer's member is
   also a member, or a broker that maps each tenant's realm into the
   shared service?
2. **The contract.** An app never builds a login (RFC-0040 §6). A shared
   service such as a Git platform expects to be its own OIDC client. Does
   the gateway present the person via the five `X-OAAP-*` headers
   (reverse-proxy login) and the service trust them?
3. **Tenant boundary.** Which tenant does a request from the shared
   service count as? A person belonging to two tenants needs a rule.
4. **Roles stay with OAAP** (RFC-0041), including for the shared tenant.
5. **Leaving.** What happens to a shared-service account when the person's
   tenant membership ends, or the tenant moves to its own node?

## Options collected on 2026-09-30 (not decided)

Jörg's direction: pull the identity integration forward — a tenant that
says "we want Git" gets its realm registered in the shared Git platform;
and member care for tenant administrators and key users is optimised by an
app.

**A. One authentication source per tenant realm in the Git platform.**
Forgejo can hold several OIDC sources, each with auto-discovery URL, client
id and secret, and can map a group claim to organisation teams and to
"restricted". Simple, no extra Keycloak layer. Costs: the sign-in page
lists one button per source, so every customer sees the list of customers
(opaque source names soften it, they do not remove it); user names collide
across sources (same problem as I-9); the source has to be created with
the Git platform's own command line — OAAP has no hook for "run an
operation inside an instance"; and OAAP's IdP connector creates one client
per tenant for OAAP itself, not one per app.

**B. A broker realm for shared services.** One realm `shared`; each tenant
realm is registered in it as an identity provider (Keycloak identity
brokering; Keycloak 26 organisations can route by e-mail domain). The Git
platform knows exactly one source. No customer list on any page, one place
for name prefixing. Costs: the connector needs a second job (register a
tenant realm as provider in the broker realm), and the shared realm becomes
a place where identities of many customers meet — it must hold only
references, never passwords.

*Measured 2026-09-30 (Keycloak 26.7.4, throwaway realms, real logins,
script `program/messungen/keycloak-vermittler-messung.py`):*

- Brokering works: the hub realm issues its own token (`iss` = hub realm)
  for a person who authenticated in a tenant realm.
- **Without a hint the hub's login page lists every tenant provider** —
  the customer list is visible, as feared.
- **A username-template mapper gives collision-free names**: two people
  both called `alice` arrive as `tenant-a.alice` and `tenant-b.alice`.
- **The `sub` in the hub token is the hub's own shadow user**, different
  from the tenant realm's `sub`. So the hub holds a second identity record
  (name, e-mail) per brokered person; it belongs in the hub realm's backup
  and in the privacy statement. Bindings in OAAP tenants stay on the
  tenant realm and are unaffected.
- `email_verified` arrives `false` from a brokered login (RFC-0040 D2
  already keeps unverified addresses out of the headers).
- "Hide on login page" removes the list; a `kc_idp_hint` still routes.
  **A Git platform cannot send a hint per tenant** with one source, so
  hiding alone leaves a login form for hub-local accounts and no way in
  for tenants.
- **Keycloak organisations close that gap — for tenants whose members
  use the tenant's own e-mail domain.** With the providers hidden and an
  organisation per tenant linked to its provider by domain, the hub's
  login page asks for the e-mail only, and `alice@a.example` lands on
  tenant A's login page, `alice@b.example` on tenant B's; no provider
  list anywhere (step `org`, 26.7.4). The token leg after that is the one
  measured above.
- **The limit that matters for clubs:** routing is by the e-mail domain
  typed at the first login. A club whose members register with private
  addresses (`gmail`, `web`, ...) has no domain of its own to route by;
  routing by *membership* only works after a first, already routed
  login. So option B serves customers with their own domain, not
  associations of private persons.

**C. Reverse-proxy login through the gateway** (five `X-OAAP-*` headers,
the contract as written). Keeps "an app never builds a login". Fails for
`git clone` over HTTPS, which cannot pass a portal login; tokens would need
a bypass on the public route.

**Rule that any option keeps:** roles stay with OAAP and are never derived
from provider assertions (RFC-0041). Inside a *wrapped* third-party app the
platform cannot enforce that; the RFC must say what the app's own mapping
may and may not grant (for example: realm group → team, never → site
administrator).

**Member care app (related).** An app for `tenant_admin` and `keyuser` that
creates and disables people in *their own* realm through a realm-scoped
service account, and sets OAAP roles through a tenant-scoped API key
(RFC-0027). The platform still never creates people (`never: users`); the
app does, on the tenant's behalf, under credentials that reach one realm.
The alternative without any app is a realm user with `manage-users` in
Keycloak's own console: no build, but a heavier interface.

## Zusammenfassung (deutsch)

Gemeinsame Dienste (z. B. Forgejo im Shared-Mandanten) starten mit
**eigenen Konten**. Der Wunsch „ein Konto überall" bekommt dieses RFC als
Platzhalter, damit er nicht nebenbei und an der Sicherheitsgrenze vorbei
gelöst wird. Offene Fragen: wessen Konto (gemeinsamer Realm oder Vermittler),
wie das mit dem Vertrag „eine App baut nie eine Anmeldung" zusammengeht,
welchem Mandanten eine Anfrage zählt und was beim Austritt passiert.
Am 30.09. gesammelt: Optionen A (eine Quelle je Mandantenrealm), B (Vermittler-Realm `shared`, Keycloak-Brokering), C (Anmeldung über das Gateway) und eine Mitglieder-App für tenant_admin/keyuser. Nachtrag: gemessen — Vermittlung, Namenspräfix und Verbergen der Anbieterliste funktionieren; die Auswahl des Anbieters per E-Mail-Domäne (Keycloak-Organisationen) trägt nur bei Mandanten mit eigener Domäne, nicht bei Vereinen mit privaten Adressen. Nicht entschieden, nichts gebaut.
