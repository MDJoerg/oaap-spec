# RFC-0041: External Identity Providers — Keycloak, a Realm per Tenant, and the Way Out

- **Status:** Draft (2026-09-22) — seven decisions await Jörg
- **Date:** 2026-09-22
- **Authors:** Jörg (direction, the club scenario, the move requirement),
  Claude (design and write-up)
- **Depends on:** RFC-0022 (tenant as boundary, **D3**), RFC-0040 (the
  user record has an identity that is not its name — the hinge),
  RFC-0008 (`server_admin`), RFC-0016 (multi-container apps), RFC-0019
  (artifact deployment), RFC-0029 D5 (the tenant archive)
- **Extends:** `oaap.core.identity` (a second way to answer *who*),
  `oaap.core.tenant` (a tenant may name a provider)
- **Companion:** RFC-0042 (the tenant as a place) — the tenant address
  this RFC's §5 depends on is decided there, and that RFC needs nothing
  from this one

## Summary

A tenant may name an **external identity provider**. The provider
answers *who somebody is*; OAAP keeps answering *what they may do*. The
first provider kind is **OIDC**, and the first product behind it is
**Keycloak**, installed as an ordinary OAAP app, with **one realm per
tenant**.

The platform's link to a provider is a **configured object** — issuer
URL, realm, client id, client secret — and the platform does not know
or care whether the Keycloak behind that URL runs on this node, on
another node, or at the customer. That one property is what makes the
club's later move to its own node a configuration change instead of a
project.

## Motivation

### The scenario that asks for it

Jörg, 2026-09-22: `oaapx01` carries **one** Keycloak; at least two
clubs get a realm each; realms are bound to tenants. The node already
has four tenants (`default`, `cls`, `hbvp`, `pxx`) and seventeen app
instances, so this is not a thought experiment on an empty machine.

And the requirement that shapes everything: **the clubs will later want
their own node.** A tenant plus its realm must be movable.

### Why this RFC could not have come earlier

RFC-0040 (built 2026-09-22, reference 0.1.107) is its hinge, and §6
there said so in advance. Binding a foreign provider's subject to a
local user needs **a local identifier that is not a login name** — a
foreign `sub` is not a username, and the name a provider suggests may
collide with an existing one or change under the person's feet. That
identifier now exists. So does the file locking that becomes mandatory
the moment user records appear through *incoming traffic* rather than
through an administrator.

### What is already decided and is not re-opened here

- **RFC-0022 D3 — users are not shared, providers are.** The same human
  authenticating into two tenants is **two principals**. Roles, groups
  and sessions are per tenant and do not travel.
- **RFC-0040 §6 — the app never sees the provider.** Apps keep
  receiving `X-OAAP-*` and nothing else. The Deployment Contract's first
  guarantee — *an app never builds a login* — holds unchanged, or every
  app on the platform becomes an integration project.
- **Roles stay with OAAP.** A provider may assert group membership; it
  never asserts an OAAP role.

## 1. The shape

```
Browser ──► Gateway ──forward_auth──► Identity ──OIDC──► Keycloak realm
   │                     │                                  (hbvp)
   └────── app ◄─────────┘  X-OAAP-User, -User-Id, -Roles,
                            -Display-Name, -Email
```

Identity gains a **second way to answer "who is this"**, next to the
session cookie and the API key. `resolve_principal()` was written for
exactly this and says so in its own docstring: *"an ordered list of
methods, not a branch… so that a customer's own identity provider can
become a third method later instead of a rewrite."*

## 2. The decisions

### K1 — The relying party is **Identity**, not the gateway

> **Recommendation: Identity.** RFC-0040 §6 wrote "the gateway becomes
> the OIDC client". That sentence's *intent* — the app never sees the
> provider — is right and stays. Its *placement* is wrong for this
> codebase.

Identity already owns everything an OIDC relying party needs and the
gateway owns none of it: `/auth/*` on every entry point, the session
cookie and its `session_epoch`, the login throttle, the
return-to-where-you-were-going logic of RFC-0040 D5, and `/verify`
itself. Caddy would need a plugin and a second session notion; Identity
needs a library and one more method in `resolve_principal`.

The app-facing contract is **identical** either way, which is why this
is a correction of wording and not of direction.

### K2 — Keycloak is an app, and the platform must not know that it is local

> **Recommendation: keep Jörg's decision of 2026-09-21 — Keycloak is an
> OAAP app — and add the rule that makes it worth something.**

As an app it updates, backs up, rolls back and is audited like every
other app, and it brings its **own Postgres container** (RFC-0016
multi-container, the shape LiveKit + Redis already proved). That
matters concretely: `oaapx01` does **not** carry the `store` profile,
and this RFC must not make it.

The rule that has to come with it: **the platform's provider object is a
URL.** Nothing in the platform may say "the local Keycloak". An
instance may sit right next to it on the same node and the provider
object still names `https://auth.oaap.joomp.de/realms/hbvp` like any
other. Without this rule the move in K6 becomes a rewrite; with it, it
becomes an edit.

A consequence worth stating plainly: a node's own login then depends on
an app instance. If that app is down, holders of a realm-backed identity
cannot log in. **The built-in provider therefore never goes away** — the
operator's own `server_admin` keeps a local password, and a tenant may
keep local users alongside a realm. That is not a fallback bolted on; it
is RFC-0022 D3's "one or more providers" read literally.

### K3 — OAAP **consumes** a realm; it does not manage Keycloak (in v1)

> **Recommendation: consume, don't manage. A documented realm recipe,
> not an admin-API integration.**

The alternative — OAAP creates and maintains realms through Keycloak's
admin API — is an integration that ages against somebody else's product
across major versions, and it is the sort of work that is invisible
until it breaks. The board already sequenced it this way: *"Keycloak-RFC,
danach der Portal-Wizard."*

So v1: the operator creates the realm and an OIDC client by hand,
following a recipe this RFC ships, and enters four values in OAAP.
The wizard is named in §6 as the next step, with what it would do.

### K4 — First login creates a record, binds to `sub`, and grants nothing

> **Recommendation: create the local record, bind it one-to-one to the
> provider's `sub`, give it no role, and show it in an "Eingang".**

This is Jörg's own Strang B decision of 2026-09-14 (*"neue Benutzer per
Vorgabe gesperrt im Eingang"*) applied here.

Two rules are security-critical and are **not** negotiable knobs:

- **Never match an incoming login to an existing record by e-mail or by
  username.** Only `(provider, sub)` matches. E-mail matching is account
  takeover by collision; username matching is the same with extra steps.
- **A provider's claims never become OAAP roles.** A realm group MAY be
  mapped to an OAAP visibility group (RFC-0007) by an explicit, local
  mapping the operator writes; roles stay administered in OAAP.

### K5 — The entry point decides the tenant

> **Recommendation: the host somebody arrives at decides which realm
> they are sent to.**

A realm belongs to one tenant, so a login through `hbvp.<node>` goes to
the `hbvp` realm and produces a principal in the `hbvp` tenant. The same
human arriving through `cls.<node>` is a different principal in a
different tenant — RFC-0022 D3, made operational rather than
theoretical.

This is the one place where this RFC needs **RFC-0042** (the tenant
address). Without a tenant-scoped entry point, the login page would have
to ask *"which club are you?"*, which is both ugly and a way to
enumerate the node's customers.

### K6 — The move: export the realm, adopt the tenant, repoint the object

> **Recommendation: build the half that is tractable, and say plainly
> which half is not.**

A club moving to its **own new node** is the *easy* direction, and for a
reason this project has met before (RFC-0030): **the target is empty.**
Nothing to merge, no port already taken, no name another tenant has
claimed, no user who exists in both. That is precisely why
`oaap.data.backup` 2.1.1 (built 2026-09-22) produces a tenant archive
and refuses to promise a *restore into a running node*. The move Jörg
needs is not that refusal — it is its complement.

Three moving parts:

1. **The tenant** — `oaap backup create --tenant hbvp`, which exists.
   What is missing is the other end: adopting such an archive **into an
   empty node**. That is this RFC's build work, and it is bounded.
2. **The realm** — Keycloak's own realm export/import. **To be proven
   before the design leans on it:** whether a realm export preserves
   user ids (`sub`). If it does, every local binding from K4 survives
   the move untouched. If it does not, the move needs a re-binding step
   keyed on something else, and that changes K4. *This is measured on
   `oaap-test` before anything else is built.*
3. **The provider object** — one edit: the issuer URL now points at the
   club's own Keycloak.

What stays **unpromised**: merging a tenant back into a node that is
already running other tenants.

### K7 — Self-registration and 2FA are named, not built

> **Recommendation: out of scope for v1.**

Keycloak brings both. Whether a club may let members register
themselves is a **policy decision per tenant**, and 2FA belongs with the
internet-hardening profile that `oaap.core.identity` already lists as
open. Naming them here keeps the realm recipe from being written in a
way that would make them expensive later.

## 3. What an implementation must guarantee

- The **app-facing contract is unchanged**. An app cannot tell whether
  the person behind `X-OAAP-User-Id` authenticated locally or through a
  realm, and MUST NOT be able to.
- **Failure is closed and legible.** A provider that is unreachable
  refuses the login and says which provider and that it is unreachable —
  it never falls back to a local password for a realm-backed identity,
  and never creates a session on an unverified assertion.
- **The client secret is a secret of the node**, in a `0600` file like
  the backup targets and the external backings (RFC-0033 D1, RFC-0034
  §3.2) — never in an instance's environment, never in an archive, never
  visible to an app.
- **Every binding is visible and revocable.** A `server_admin` can see,
  for one user, which provider and which subject they are bound to, and
  can break that binding. A `tenant_admin` sees it for their own tenant.
- The act of attaching, changing or detaching a provider is a **tenant
  audit entry** (`oaap.core.tenant` 1.7). It changes who can get into the
  tenant, which is exactly what that log exists for.

## 4. Non-goals

- **No login built by an app.** Unchanged and load-bearing.
- **No role assertion from outside.** A provider says who; OAAP says what.
- **No user moved between tenants.** `oaap.core.identity` 2.2
  deliberately has no such operation, and two realms make two people.
- **No SAML, no LDAP in v1.** OIDC only; the provider object is shaped so
  a second kind costs a field, not a redesign.
- **No merge-restore of a tenant into a running node** (K6).

## 5. Build order

1. **Measure first:** does a Keycloak realm export preserve user ids?
   (K6.2). Everything else assumes it.
2. Keycloak as an OAAP app on `oaap-test` (multi-container, own
   Postgres), plus the realm recipe.
3. The provider object, the OIDC method in `resolve_principal`, first
   login → local record bound to `sub`, no role (K1, K4).
4. The entry point → realm mapping (K5). **Needs RFC-0042 §T1.**
5. Adopting a tenant archive into an empty node (K6.1).
6. Then, and only then, `oaapx01` — see §6.

## 6. Open for later

- **The portal wizard** the board has been holding: create a realm,
  create the client, write the mapping, all from the portal. Everything
  in v1 is shaped so this is additive.
- **Self-registration and the Eingang as a workflow** (K7, Strang B).
- **2FA**, with the internet-hardening profile.
- **A second provider kind** (SAML, LDAP).
- **Merge-restore of a tenant** into a running node.

## 7. A warning about the test bed

Jörg proposes `oaapx01`. That node carries **BDT test and production,
the paying customer's `cls-gliss-viewer`, the clubs' infoboard, LiveKit
and twelve more instances** — and it is the machine whose login path
this RFC changes. It also still carries the `dev` profile.

**Recommendation: build and prove on `oaap-test`, then move to
`oaapx01`** — and there, first with a realm for a tenant that has
nothing to lose (`pxx`), before `hbvp`. The second club is what makes
the scenario real; it does not have to be what makes the first attempt
real.

Also worth settling before any of this starts: the fleet runs **0.1.109**
while **0.1.110–0.1.113** are built, tested and pushed. Starting a large
build on a node that is four versions behind the source is how a
diagnosis becomes two diagnoses.

## Deutsche Zusammenfassung

**Die Frage war: sind wir bereit?** Ja — und der Grund ist RFC-0040 von
heute Morgen. Damit ein fremder Anbieter jemanden anmelden kann, braucht
die Plattform eine **lokale Kennung, die kein Anmeldename ist**: Die
Kennung eines fremden Anbieters ist kein Benutzername, und der Name, den
er vorschlägt, kann kollidieren oder sich ändern. Genau das wurde heute
gebaut. RFC-0040 §6 hatte das vorher angekündigt — es ist der Angelpunkt,
nicht eine Bequemlichkeit.

**Die Gestalt:** Der Anbieter beantwortet *wer*, OAAP beantwortet *was
jemand darf*. Die App sieht den Anbieter **nie** — sie bekommt weiter nur
die fünf `X-OAAP-*`-Kopfzeilen. Ohne diese Regel würde jede App auf der
Plattform zu einem Integrationsprojekt.

**Sieben Entscheidungen liegen bei Dir.** Die drei wichtigsten:

- **K1 — Der OIDC-Client wird *Identity*, nicht das Gateway.** RFC-0040
  §6 schrieb „das Gateway"; die Absicht dahinter stimmt, die Verortung
  nicht. Identity besitzt bereits alles, was ein OIDC-Client braucht:
  `/auth/*`, das Sitzungs-Cookie, die Drosselung, das Rücksprungziel und
  `/verify`. Caddy bräuchte ein Plugin und einen zweiten
  Sitzungsbegriff. Für die App ändert sich so oder so nichts.
- **K2 — Keycloak bleibt eine App, aber die Plattform darf nicht wissen,
  dass sie lokal ist.** Das Anbieter-Objekt ist eine **URL** — nirgends
  steht „das Keycloak hier". Genau das macht den Umzug später zu einer
  Änderung statt zu einem Projekt. Nebenbei: Keycloak bringt seine
  Datenbank als zweiten Container selbst mit; **oaapx01 trägt das Profil
  `store` nicht**, und dieses RFC verlangt es auch nicht.
- **K6 — Der Umzug ist die *lösbare* Hälfte.** Ein Verein, der auf einen
  **eigenen, neuen** Knoten zieht, ist der einfache Fall, weil das Ziel
  **leer** ist: nichts zu mischen, kein belegter Port, kein Name, den ein
  anderer Mandant inzwischen hat, kein Benutzer, den es zweimal gibt.
  Genau deshalb sagt das heute gebaute Mandantenarchiv von sich, dass es
  nicht in einen *laufenden* Knoten zurückgespielt werden kann — der
  Umzug, den Du brauchst, ist nicht diese Verweigerung, sondern ihr
  Gegenstück. Drei Teile: Mandantenarchiv (existiert), Realm-Export
  (**muss erst gemessen werden:** bleiben die Benutzer-Kennungen beim
  Export erhalten? Wenn ja, überleben alle Bindungen den Umzug
  unverändert), und eine Zeile Konfiguration.

**Zwei Sicherheitsregeln, die keine Stellschrauben sind:** Eine
eingehende Anmeldung wird **niemals** über E-Mail oder Benutzernamen
einem bestehenden Satz zugeordnet — nur über `(Anbieter, sub)`. Alles
andere ist Kontoübernahme durch Namensgleichheit. Und die Behauptungen
des Anbieters werden **nie** zu OAAP-Rollen; eine Realm-Gruppe darf
höchstens auf eine OAAP-Sichtbarkeitsgruppe abgebildet werden, und zwar
durch eine Zuordnung, die der Betreiber selbst schreibt.

**Und eine Warnung zur Testmaschine:** `oaapx01` trägt BDT (Test und
Produktiv), den zahlenden Großkunden, das Hallen-Infoboard, LiveKit und
zwölf weitere Instanzen — und es ist die Maschine, deren Anmeldeweg
dieses RFC verändert. Empfehlung: erst auf `oaap-test` beweisen, dann auf
`oaapx01`, und dort zuerst mit `pxx`, nicht mit `hbvp`. Der zweite Verein
macht das Szenario echt; er muss nicht auch den ersten Versuch echt
machen.
