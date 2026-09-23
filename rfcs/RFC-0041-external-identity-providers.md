# RFC-0041: External Identity Providers — Keycloak, a Realm per Tenant, and the Way Out

- **Status:** **Accepted (2026-09-22); steps 2, 3, 4, 5 and 6 built
  (2026-09-23, reference 0.1.120–0.1.123, `oaap.core.identity` 0.5.0,
  `oaap.core.tenant` 0.9).** Keycloak is an OAAP app, a tenant carries
  a provider object and a first-login policy, a member of a club signs
  in through their own realm at their tenant's address, **OAAP creates
  that realm and that client itself** through a connector contract of
  which Keycloak is the first implementation — and **it now moves the
  two switches inside that realm**, recording what the realm answered
  rather than what it was told. Measured end to end on `oaap-test`,
  including a person registering themselves and arriving with no
  rights. **Open: step 7** (the move, K6) and **step 8** (`oaapx01`).
  All seven decided by Jörg in one sitting. Five as recommended; **K3 and K7 went the other way**,
  and **K4 came back refined**: the first-login rule is a per-tenant
  policy, not a platform rule. What that costs the build is written at
  each decision and folded into §5.
  **Both measurements are done** (2026-09-22, `oaap-test`, Keycloak
  26.7.4) — see §5.0. The answers are favourable, and they brought one
  finding nobody asked for: a realm export carries the client secret
  and the password hashes, so it is a **secret**, not a file.
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

### K3 — OAAP **manages** realms through Keycloak's admin API

> **Decided against the recommendation (Jörg, 2026-09-22): manage.**
> The recommendation below was *consume, don't manage*; it is kept
> verbatim because its objection does not disappear by being overruled
> — it becomes a build requirement.

**What the decision buys.** Creating a club stops being a two-system
chore: OAAP creates the realm and the client itself, and the operator
never types four values into two places. It also shortens **K6**, the
move — on the new, empty node OAAP can create the realm before
importing into it, instead of asking a human to prepare the target.

**What must come with it, or the objection comes true.** The
integration ages against somebody else's product across major versions,
and that kind of ageing is invisible until it breaks:

1. **A pinned Keycloak version**, recorded with the provider object —
   not "latest". The app is ours to update; the update is then a
   deliberate act with a test on `oaap-test` first.
2. **The admin path fails loudly, never silently.** If an admin call
   returns something this version does not understand, OAAP refuses the
   operation and says which call and which version — it does not guess
   and does not half-create a realm.
3. **Managing is not the same as owning.** A realm OAAP did not create
   is still usable by hand (the recipe stays in this RFC), and OAAP
   never deletes a realm it finds. Deleting a tenant does not delete
   the club's identities.
4. **The admin credential is an app secret**, scoped to realm
   administration, never to the master realm.

The portal wizard of §6 is now the *surface* of this, not a separate
capability.

> **Original recommendation (not taken): consume, don't manage. A
> documented realm recipe, not an admin-API integration.**

The alternative — OAAP creates and maintains realms through Keycloak's
admin API — is an integration that ages against somebody else's product
across major versions, and it is the sort of work that is invisible
until it breaks. The board already sequenced it this way: *"Keycloak-RFC,
danach der Portal-Wizard."*

So v1: the operator creates the realm and an OIDC client by hand,
following a recipe this RFC ships, and enters four values in OAAP.
The wizard is named in §6 as the next step, with what it would do.

### K4 — First login binds to `sub`; what happens next is a **tenant policy**

> **Decided with a refinement (Jörg, 2026-09-22):** *"Diese Optionen im
> Tenant anbieten bei der Konfiguration. Es gibt für alle Vorschläge
> usecases."* — The binding is a platform rule. The **consequence** of
> a first login is a setting the tenant carries, because a club that
> administers its own realm wants something different from a customer
> whose people the operator admits by hand.

**Always, in every tenant:** a local record is created and bound
one-to-one to `(provider, sub)`. That part is not configurable.

**Per tenant, one of three (`first_login`):**

- **`eingang`** — kein Recht, sichtbar im Eingang. **Die Vorgabe.**
- **`role`** — eine im Mandanten hinterlegte Standardrolle wird vergeben.
- **`groups`** — zusätzlich greift eine **ausdrücklich geschriebene**
  Abbildung von Realm-Gruppen auf OAAP-Sichtbarkeitsgruppen.

**K4b — the default and who may change it** (Jörg, as recommended):
a new tenant starts at `eingang`, and **only `server_admin` may move it**
off that value. A `tenant_admin` sees the setting and cannot change it.
The reason is the shared node: a tenant that could open itself would be
opening a door on a machine that carries other customers, and the
operator would learn about it afterwards. Every change is an entry in
**that tenant's** log (`oaap.core.tenant` 1.7), so the customer sees
what was done in their name.

Even at `groups`, the mapping is a local list the operator writes. A
realm group never becomes an OAAP **role**, and an unmapped group
grants nothing — a club cannot widen its own rights by inventing a
group.

This builds on Jörg's own Strang B decision of 2026-09-14 (*"neue
Benutzer per Vorgabe gesperrt im Eingang"*), which is now the default
rather than the only behaviour.

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
2. **The realm** — Keycloak's own realm export/import. This was the
   open question the design leaned on: does a realm export preserve
   the identity K4 binds to? **Measured 2026-09-22 on `oaap-test`
   against 26.7.4: yes** — the `sub` in a real token is the same UUID
   before the export and after the import into an empty instance
   (§5.0). So **every binding from K4 survives the move untouched**,
   and no re-binding step is needed. The measurement also showed that
   the members' passwords travel with the realm, so nobody has to
   reset anything — and that the export file is therefore a **secret**
   (§3).
3. **The provider object** — one edit: the issuer URL now points at the
   club's own Keycloak. The client secret travels in the export, so
   this really is one edit and not a re-registration.

What stays **unpromised**: merging a tenant back into a node that is
already running other tenants.

### K7 — Self-registration and 2FA are **in v1**

> **Decided against the recommendation (Jörg, 2026-09-22): both in v1.**
> The recommendation was *out of scope*. Keycloak brings both, so the
> cost is not in building them but in deciding who may switch them and
> what they mean on a shared node.

Both are **per-tenant settings**, and both follow K4b's authority rule:
the tenant sees them, only `server_admin` changes them, and every
change lands in that tenant's log.

**Self-registration** is coherent precisely *because* of K4b. Somebody
registering themselves in the club's realm arrives in a tenant whose
default is `eingang` — they get an identity and no rights, which is
what "Anmeldung möglich, Freischaltung nicht" has always meant here.
A tenant that has been moved to `role` **and** allows self-registration
is the combination that hands rights to anyone who can reach the page;
OAAP must therefore **refuse that pair** unless it is set deliberately,
and say why.

**2FA** is enforced in the realm, not by OAAP — Keycloak decides
whether a login needs a second factor, and OAAP only learns that the
login succeeded. Two things follow:

- OAAP MUST record **that** the provider asserted a second factor (the
  `amr`/`acr` claim) on the session, so an audit entry can say it.
- 2FA for the **built-in** provider stays out of v1 and stays with the
  internet-hardening profile. Otherwise a `server_admin` would believe
  the node is protected when only the realm-backed half is.

What remains in §6 is the **Eingang as a workflow** (Strang B): notify,
approve, reject with a reason.

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

Added by the decisions of 2026-09-22:

- **Every tenant switch from K4/K7 is `server_admin`-only and audited.**
  `first_login`, self-registration and 2FA are visible to a
  `tenant_admin` and changeable only by the operator, each change an
  entry in that tenant's log. A setting that decides who gets in must
  not be changeable by the party it lets in.
- **`first_login: role` together with self-registration is refused**
  unless it is set deliberately, with a reason that goes into the log.
  Separately each is defensible; together they grant rights to anyone
  who can reach the page, and nothing else in the system would notice.
- **The admin-API integration names its version and fails loudly** (K3).
  The provider object records the Keycloak version it was built
  against; an answer the implementation does not understand aborts the
  operation naming the call and the version, and never leaves a realm
  half-created.
- **OAAP never deletes a realm it did not create**, and deleting a
  tenant never deletes the club's identities. Managing is not owning.
- **The admin credential is scoped to realm administration**, never to
  the master realm, and is a secret of the node under the same rule as
  the client secret above.
- **A second factor asserted by the provider is recorded on the
  session** (`amr`/`acr`), so an audit entry can say that it happened.
  OAAP does not enforce it and must not claim to.

Added by the measurement of 2026-09-22 (§5.0):

- **A realm export is a secret.** Measured: it carries the OIDC client
  secret and the users' password hashes. It MUST be written and kept
  under the same rule as a node backup archive — `0600`, never inside
  an instance's storage, never readable by an app — and removed once
  the move it was made for is done. An implementation that offers a
  realm export through the portal MUST NOT serve it to a browser as an
  ordinary download.
- **The binding key is what the token says.** OAAP binds to the `sub`
  claim, not to whatever an admin API calls the user's id. On 26.7.4
  these are the same value and the measurement confirmed it end to
  end; they are the same by *default*, not by guarantee, so the code
  reads `sub` and nothing else.

## 4. Non-goals

- **No login built by an app.** Unchanged and load-bearing.
- **No role assertion from outside.** A provider says who; OAAP says what.
- **No user moved between tenants.** `oaap.core.identity` 2.2
  deliberately has no such operation, and two realms make two people.
- **No SAML, no LDAP in v1.** OIDC only; the provider object is shaped so
  a second kind costs a field, not a redesign.
- **No merge-restore of a tenant into a running node** (K6).

## 5. Build order

Updated after the decisions of 2026-09-22. K3 and K7 made it longer;
the order is chosen so that the two measurements come before anything
that assumes their answer.

### 5.0 The two measurements — done, 2026-09-22

Measured on `oaap-test` against **Keycloak 26.7.4** in throwaway
containers bound to `127.0.0.1`, removed afterwards. Not the admin
console's word for it: the full round trip, with a real token.

**M1 — does a realm export preserve the identity K4 binds to? Yes.**
The chain measured was `create user → obtain a real token → export →
import into an EMPTY instance → obtain a token again`, and all four
values are the same UUID:

- the internal user id before the export,
- the `sub` in a token issued before the export,
- the id in the export file,
- the `sub` in a token issued **after** the import.

Two things were deliberately separated here, because collapsing them
is how an assumption survives a measurement. The first run measured
only the **internal id**; K4 binds to **`sub`**. That `sub` is the
internal id is Keycloak's default, and "is the default" is not a
measurement — a mapper can change it. So a second run obtained an
actual token, before and after, and read `sub` out of it. Only then is
K6.2 answered: **every binding from K4 survives the move untouched**,
and no re-binding step is needed.

**M2 — can the admin API do what K3 now needs? Yes.** Against 26.7.4:
create a realm (`201`), create an OIDC client (`201`), read the client
back by `clientId`, and fetch its secret. That is the whole of what K3
asks for in v1. The server states its own version at
`/admin/serverinfo` → `systemInfo.version`, which is what makes the
pinned version checkable rather than merely written down.

**Pinned version: `quay.io/keycloak/keycloak:26.7.4`**, recorded with
the provider object per K3.

**The finding nobody asked for, and the more important one.** The
export file carries **the client secret** and **the users' password
hashes** — verified in the file, and proven by the fact that the user
could log in on instance B with the same password. That is good news
for the move (a club's members do not have to reset anything, and the
provider object keeps working) and it makes the export a **secret**:

> A realm export MUST be treated exactly like a node backup archive
> (`oaap.data.backup`): `0600`, never in an instance's storage, never
> in a place an app can read, and never left lying around after the
> move. It is not a configuration file that happens to contain
> accounts; it is every credential of that club in one file.

This was not in the design before the measurement. It is now §3 and
step 7 of the order below.

### 5.1 The order

Step 1 was the measuring, and it is done. Steps 2, 3 and 5 were built
on 2026-09-23 and are marked below.

1. ~~**RFC-0042 first**~~ — **done 2026-09-22/23** (reference
   0.1.115–0.1.119).
2. ~~Keycloak as an OAAP app~~ — **done** (`oaap-apps/apps/keycloak`
   0.1.1): two containers, its own Postgres, pinned to **26.7.4**, and
   the realm recipe in its README, which stays because K3 says
   *manage*, not *own*.
3. ~~The provider object, the OIDC login, the binding, the tenant
   policy~~ — **done** (0.1.120/0.1.121). One correction of wording:
   it is not a method in `resolve_principal` but a second way to
   *establish* the session that method reads — which is why nothing
   downstream changed at all.
4. ~~The admin-API path (K3)~~ — **done** (0.1.122,
   `oaap.core.tenant` 0.8). Built as a **connector contract** rather
   than as a Keycloak integration, on Jörg's direction of 2026-09-23:
   *Keycloak is the first connector with an API; when another SSO
   product arrives whose settings we also want to make and write back
   into our own configuration, it should be a file and a row in a
   table.* Four verbs, one table per product, two rules that run
   rather than being promised — nothing deletes, and nothing is
   created before the version has been checked. §5.3 has what the
   measuring changed.
5. ~~The entry point → realm mapping (K5)~~ — **done**, and it cost
   almost nothing once RFC-0042 existed: the same call that decides
   whose face a page wears decides whose realm a login goes to.
6. ~~The rest of K7: self-registration as a *realm* setting and the
   2FA switch~~ — **done** (0.1.123, `oaap.core.tenant` 0.9). The
   connector's fifth verb. What it added to the design is a rule about
   TRUTH rather than about switches: a setting that lives both in a
   realm and in OAAP's record is written down from what the realm
   answered, never from what OAAP asked for. §5.4 has what the
   measuring changed, including one rule that had to be rewritten
   after the machine showed it could never fire.
7. The move (K6): adopting a tenant archive into an empty node, the
   realm export — **handled as a secret, per §5.0** — and the one edit
   to the provider object. **Next.** The connector names this verb
   (`export`) and names it absent.
8. Then, and only then, `oaapx01` — see §7.

### 5.2 What the build added that the design did not have

Three rules came out of building and measuring rather than out of the
decisions, and they are now in `oaap.core.tenant` 2.8:

- **The channel is the authentication of the issuer.** The identity
  token is taken over the back channel and its signature is
  deliberately not verified — OIDC Core 3.1.3.7 allows exactly that,
  because TLS to the token endpoint already proves who answered. The
  consequence had to be said out loud: then the transport is not a
  hardening option, it is the only proof, and an `http` issuer
  reachable from the internet must be refused. A signature check would
  not rescue such a setup — a key document fetched over the same open
  channel is as forgeable as the token it would verify. The one
  exception is a statement of fact rather than a relaxation: an `http`
  issuer that cannot be reached from the internet at all.
- **A name a provider suggests is a suggestion.** A taken name gets a
  number. Adopting the record that holds it is the account takeover K4
  refuses one step earlier.
- **Breaking a binding is not something that can be re-established.**
  Measured on `oaap-test`: after `oaap user unbind`, the same person
  signing in again became a *new* record. That is not a defect — the
  alternative is to recognise somebody by their name — but the
  consequence had not been drawn: a record without a binding and
  without a local password is a record with rights and no way in. It is
  deactivated now, and the command says in three sentences what happens
  next.

And one thing the design expected to build did not have to be built:
the app-facing contract needed **no** change, in either direction. An
address the provider asserted as unverified was stored and kept out of
`X-OAAP-Email` by the rule RFC-0040 D2 already wrote, without a line
being added for foreign providers.

### 5.3 What step 4 measured, and what it cost the design

Two of K3's five requirements turned out to be in tension with each
other at the product they were written for. Both measurements are from
`oaap-test`, Keycloak **26.7.4**, 2026-09-23.

**K3.4's credential is possible, and it is narrower than expected.** A
service account in the server realm holding **`create-realm` and
nothing else** can create a realm, and can fully administer the realms
it created. Measured, with the answers:

| asked | answered |
| --- | --- |
| create a realm | **201** |
| administer the realm it created, and its clients | **200** |
| read the server realm's users | **403** |
| read the server realm's clients | **403** |
| read another realm's users | **403** |
| list every realm on the server | **403** |

K3.4 asked for a credential "scoped to realm administration, never to
the master realm". Half of that cannot be had: **creating** a realm is
an act in the server realm. What can be had is the narrowing above —
no human behind it, one grant, and no way to read anybody's people —
and where the intention cannot be kept it is now **named** rather than
quietly dropped: a credential that is a user's login says what it
costs, every time it is printed.

**K3.1 and K3.4 cannot both be satisfied.** The pinned version is
checkable only at `/admin/serverinfo`, and that endpoint answers a
narrow credential with a **trimmed** document — `profileInfo` and
nothing else, no version. Measured for `create-realm` alone, and for
`create-realm` + `view-realm`: the second buys no version and costs the
ability to enumerate every realm on the server, which on a shared node
is every club on it.

So K3.1 keeps its substance and loses its mechanism in one case:
nothing is created against a version nobody has checked, but where
OAAP cannot read it, **a human states it** — once, at the connector —
and every surface that prints the number says it was *stated* and not
read. A stated version never overrides one the server gives.

**And one sentence stood at the wrong door.** OAAP must not adopt
another customer's realm, and the careful refusal for that was written
at the realm lookup. That call answers **200**: a `create-realm`
credential may see that a realm exists. The refusal arrives one call
later, at the clients lookup, which had a bare status code and no
sentence. A rule worth saying is worth saying at every door it can
arrive at.

### 5.4 What step 6 measured

Keycloak **26.7.4** on `oaap-test`, 2026-09-23, with the same narrow
`create-realm` service account as §5.3.

**The credential is wide enough after all — inside its own realm.** The
open question from §5.3 was whether a credential narrow enough to
satisfy K3.4 could move anything *inside* a realm. It can, for realms
it created: the realm update (`registrationAllowed`) and the required
action (`CONFIGURE_TOTP`) both answered **204**. In a realm it did not
create, the same reads answered **403** — and the refusal arrives at
the *second* document, because the realm itself answers 200. That is
the same door §5.3 found for provisioning, and the sentence now stands
there too.

**K7 measured end to end.** Self-registration on → Keycloak's login
page really carries the registration link → a person registered
themselves → they arrived in OAAP as a record with **no roles and no
groups**, in the Eingang. That is the whole of what "Anmeldung möglich,
Freischaltung nicht" was supposed to mean, and it is now a measurement
rather than a claim.

**A switch's reach is smaller than its name.** With the second factor
required, a newly registered member is asked to set one up. A member
who was already in the realm is **not** — Keycloak applies a default
required action to people who arrive after it. Asking the others would
mean writing onto each person, which this design does not do (§2.9's
"managing is not owning"). So the reach is said out loud when the
switch is moved, rather than discovered by an audit.

**And one rule as first built could never have fired.** K7 asks the
platform to record what the provider asserted about a second factor;
step 6 added a note for the case where the realm requires one and the
login names none. It looked for the provider saying *nothing* — and
Keycloak answers `acr=1` to an ordinary password login, so it never
says nothing. Measured with exactly the case the rule was written for:
a member who was in the realm before the switch was turned on signed
in without a second factor, and the log said nothing about it.

What is read now is `amr`, which names **methods**. `acr` is still
recorded and deliberately not judged: an assurance level's meaning is
configured inside the realm, and a platform that read it as evidence
would be deciding what somebody else's number means.

## 6. Open for later

Shorter than it was: K3 pulled the wizard's substance into v1 and K7
pulled both feature switches in.

- **The portal wizard** the board has been holding — now only the
  *surface* of K3's admin path, since the capability itself is in v1.
- **The Eingang as a workflow** (Strang B): notify, approve, reject
  with a reason. K7 brought self-registration in; the queue behind it
  is still a list, not a process.
- **2FA for the built-in provider**, with the internet-hardening
  profile. K7's 2FA is the realm's, which is a different thing.
- **A second provider kind** (SAML, LDAP).
- **Merge-restore of a tenant** into a running node — the one thing
  K6 deliberately does not promise.

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

## Nachtrag: die Entscheidungen vom 22.09.2026

Jörg hat alle sieben in einem Durchgang entschieden. Fünf wie
vorgeschlagen (K1 Identity, K2 Anbieter-URL, K5 der Host entscheidet,
K6 nur die lösbare Hälfte, K4b Vorgabe Eingang und nur `server_admin`
stellt um). **Zwei anders, eine verfeinert** — und die drei sind der
interessante Teil:

**K3: OAAP verwaltet die Realms doch selbst, über Keycloaks
Verwaltungsschnittstelle.** Das nimmt Dir Handarbeit ab und verkürzt
sogar den Umzug, weil OAAP den Realm auf dem leeren Zielknoten selbst
anlegen kann. Mein Einwand bleibt trotzdem stehen, er wird nur zur
Bauauflage: So eine Anbindung altert gegen ein fremdes Produkt, und sie
altert **unsichtbar**. Deshalb gehören dazu eine **festgenagelte
Keycloak-Version** beim Anbieter-Objekt, ein Verhalten, das bei einer
unverstandenen Antwort **laut abbricht** statt zu raten, und die Regel,
dass Verwalten nicht Besitzen heißt: OAAP löscht nie einen Realm, den
es vorgefunden hat, und das Löschen eines Mandanten löscht nicht die
Identitäten des Vereins.

**K4: Der erste Login wird eine Sache des Mandanten.** Dein Einwand war
richtig — es gibt für alle drei Wege echte Fälle. Die **Bindung** an
`(Anbieter, Kennung)` bleibt Plattformregel und ist nicht einstellbar;
was danach passiert, trägt der Mandant: `eingang` (Vorgabe), `role`
oder `groups`. Und weil auf einem Knoten mehrere Kunden liegen, darf
diesen Schalter nur der Betreiber umlegen, nicht der Mandant selbst —
sonst öffnet jemand eine Tür auf einer Maschine, die ihm nicht allein
gehört, und Du erfährst es hinterher. Jede Änderung steht im Protokoll
**dieses** Mandanten.

**K7: Selbstregistrierung und Zwei-Faktor kommen in v1.** Keycloak
bringt beides mit, der Aufwand liegt nicht im Bauen, sondern im
Festlegen, wer sie umlegen darf. Beide werden Mandanten-Einstellungen
nach derselben Regel wie K4b. Selbstregistrierung ist überhaupt nur
deshalb unbedenklich, **weil** die Vorgabe `eingang` heißt: Wer sich
selbst registriert, bekommt eine Identität und keine Rechte. Die
Kombination `role` **plus** Selbstregistrierung verschenkt dagegen
Rechte an jeden, der die Adresse kennt — die muss OAAP ablehnen, außer
sie wird ausdrücklich so gesetzt, und dann mit Begründung. Der
Zwei-Faktor gilt zunächst nur für Realm-Anmeldungen; für die eingebaute
Anmeldung bleibt er offen, sonst hält ein `server_admin` den Knoten für
geschützt, obwohl nur die eine Hälfte es ist.

**Die zwei Messungen sind erledigt (22.09.2026, `oaap-test`, Keycloak
26.7.4)** — in Wegwerf-Containern, nur an `127.0.0.1` gebunden,
hinterher restlos entfernt.

**M1 — Bleibt die Kennung erhalten? JA.** Gemessen wurde die ganze
Kette: Benutzer anlegen → echtes Token holen → exportieren → in eine
**leere** Instanz importieren → wieder anmelden. Alle vier Werte sind
dieselbe UUID. **Damit überleben alle Bindungen aus K4 den Umzug
unverändert**, und es braucht keinen Neubindungs-Schritt.

Eine Feinheit, die den zweiten Lauf nötig machte: Der erste maß die
**interne Id**; K4 bindet aber an den **`sub`** aus dem Token. Dass
beide dasselbe sind, ist bei Keycloak die Vorgabe — aber „ist die
Vorgabe" ist keine Messung, und ein abweichender Mapper wäre genau die
Art Annahme, die erst beim ersten echten Umzug auffliegt. Also ein
zweiter Lauf mit einem echten Token, vor und nach dem Umzug.

**M2 — Kann die Verwaltungsschnittstelle, was K3 braucht? JA.** Realm
anlegen (201), Client anlegen (201), Client zurücklesen, Geheimnis
abholen. Und der Server nennt seine Version unter `/admin/serverinfo` —
das ist es, was die festgenagelte Version **prüfbar** macht statt nur
aufgeschrieben. **Festgenagelt: `quay.io/keycloak/keycloak:26.7.4`.**

**Und der Befund, nach dem niemand gefragt hat — der wichtigere.** Die
Exportdatei enthält **das Client-Geheimnis und die Passwort-Nachweise
der Mitglieder**. Nachgewiesen nicht nur in der Datei, sondern dadurch,
dass sich die Testbenutzerin nach dem Import mit demselben Passwort
anmelden konnte. Zwei Folgen, eine angenehme und eine unbequeme: Beim
Umzug muss **niemand** sein Passwort neu setzen und das Anbieter-Objekt
braucht wirklich nur eine Zeile — aber die Exportdatei ist damit **ein
Geheimnis wie ein Backup-Archiv**: `0600`, nie im Speicher einer
Instanz, nie für eine App lesbar, nie als gewöhnlicher Download aus dem
Portal, und nach dem Umzug gelöscht. Das stand vor der Messung nicht im
Entwurf.

**Und eine Warnung zur Testmaschine:** `oaapx01` trägt BDT (Test und
Produktiv), den zahlenden Großkunden, das Hallen-Infoboard, LiveKit und
zwölf weitere Instanzen — und es ist die Maschine, deren Anmeldeweg
dieses RFC verändert. Empfehlung: erst auf `oaap-test` beweisen, dann auf
`oaapx01`, und dort zuerst mit `pxx`, nicht mit `hbvp`. Der zweite Verein
macht das Szenario echt; er muss nicht auch den ersten Versuch echt
machen.

## Nachtrag: gebaut am 23.09.2026 (Schritte 2, 3 und 5)

**Was jetzt geht.** Ein Verein bekommt einen Realm in einem Keycloak,
das als gewöhnliche OAAP-App auf dem Knoten läuft. Ein Mitglied ruft
`<kürzel>.<knoten>` auf, sieht auf der Anmeldeseite einen Knopf mit dem
Text, den der Betreiber gewählt hat, meldet sich in seinem Verein an
und landet im Portal seines Mandanten. Auf `oaap-test` von Anfang bis
Ende gemessen: Anna kam herein und hatte **keine Rechte** — die
Vorgabe. Danach wurde der Schalter auf `role` gelegt, und Bernd kam mit
der Rolle `user` herein.

**Die Gestalt, in einem Satz:** Der OIDC-Client ist *Identity*, und es
ist keine dritte Methode — es ist ein zweiter Weg, die Sitzung
anzulegen, die Methode 1 ohnehin liest. Deshalb hat sich an `/verify`,
an den Kopfzeilen, an der Mandantengrenze und an jeder App **nichts**
geändert. Die Zusage aus RFC-0040 §6, dass eine App den Anbieter nie
sieht, ist damit strukturell wahr und nicht diszipliniert: Es gibt gar
nichts, woran eine App den Unterschied merken könnte.

**Ein Urteil in drei Programmen**, wieder: `services/idp.py`, die
Schwester von `place.py` aus RFC-0042. Identity meldet an, `appctl`
konfiguriert, das Portal zeigt. Und die beiden Regeln, die keine
Einstellungen sind, stehen dort als **Funktionen**, nicht als
Bedingungen an der Aufrufstelle — die Lehre vom Mutationstest des
Vortags: Eine Regel in einem Zweig kann man nur lesen, eine in einer
Funktion ausführen.

**K5 hat fast nichts gekostet.** Dieselbe Frage, die entscheidet,
wessen Gesicht eine Seite trägt, entscheidet, in wessen Realm eine
Anmeldung geht. Das war der ganze Grund, RFC-0042 vorzuziehen.

**Drei Befunde von der Maschine**, und der dritte ist der wichtigste:

1. *Kein Anbieter ist kein Anbieter namens "".* Die allererste
   Anbindung eines Mandanten meldete „ISSUER CHANGED, every binding it
   had is void" — ein beunruhigender Satz über einen Mandanten, der nie
   einen Anbieter hatte. Schlimmer als die Formulierung: Der leere
   Schlüssel `oidc|` ist ein Schlüssel, und ein Schlüssel trifft.
2. *Die Rückkehradresse muss auf das Zeichen stimmen*, und das Schema
   ist das des **Browsers**, nicht das im Container. Die CLI druckte
   nur die https-Form und schickte damit jeden Betreiber eines
   Klartext-Knotens in eine Ablehnung des Anbieters, die keine Ursache
   nennt.
3. *Eine gelöste Bindung ist kein Rückweg.* Nach `oaap user unbind`
   fand die erneute Anmeldung nicht zurück, sie legte einen neuen Satz
   an (`bernd` → `bernd-2`). Mein eigener Satz hatte „bindet frisch"
   gesagt. Das Verhalten ist richtig — die Alternative wäre, jemanden
   an seinem **Namen** wiederzuerkennen —, aber die Folge war nicht
   gezogen: Ein ungebundener Satz ohne lokales Passwort ist ein Satz
   mit Rollen und ohne Weg hinein. Der wird jetzt stillgelegt, und der
   Befehl sagt in drei Sätzen, was als Nächstes passiert.

**Und ein vierter, der gar nichts mit diesem RFC zu tun hat.** Der
Klicktest nahm zum Prüfen der Launchpad-Kachel einfach die **erste**
Instanz. Auf `oaap-test` war die erste seit diesem Tag ein
Hintergrunddienst, der überhaupt keine Kachel hat — drei Prüfungen
schlugen fehl, ohne dass irgendetwas kaputt war. Eine willkürliche
Auswahl ist keine Auswahl.

**Was Schritt 2/3/5 ausdrücklich nicht tun.** OAAP legt noch keine
Realms an (das ist Schritt 4, und das Rezept in der README des
Keycloak-Pakets ist genau deshalb ausführbar geblieben). OAAP schaltet
noch keine Selbstregistrierung und keinen Zwei-Faktor **im Realm** ein;
gebaut ist nur die Hälfte, die OAAP gehört — die Ablehnung der
gefährlichen Kombination und das Mitschreiben eines behaupteten
Faktors. Und der Umzug (K6) ist unangetastet.

## Nachtrag: gebaut am 23.09.2026 (Schritt 4)

**Was jetzt geht.** Zwei Handgriffe am Knoten, und ein Verein hat seine
Tür — ohne dass jemand vier Werte in zwei Systeme tippt:

```
sudo oaap idp add auth --url https://auth.<knoten> --admin-id oaap-admin ...
sudo oaap idp provision auth --tenant hbvp
```

Gemessen auf `oaap-test`, von Anfang bis Ende: OAAP legte den Realm
`probe4` und den Client an, holte das Geheimnis, schrieb das
Anbieter-Objekt — und Anna meldete sich in genau diesem Realm an und
kam **ohne Rechte** herein (`eingang`). Ihre Bindung nennt den `sub`,
den Keycloak vergeben hatte, und `password_hash` ist leer.

**Die Gestalt, und sie ist Jörgs.** Am 23.09. gab Jörg die Richtung
vor: *Keycloak als ersten Connector mit einer API verstehen; kommen
später weitere SSO-Lösungen, bei denen wir auch die für uns wichtigen
Einstellungen machen und in unsere Konfiguration schreiben wollen,
lässt sich das über Apps/Services/Plugins nachrüsten.* Gebaut ist
deshalb **kein** „Keycloak-Anschluss", sondern ein **Vertrag aus vier
Verben** mit einer Tabelle je Produkt: Adressen, Version-Stelle,
Aussteller-Schreibweise und Vollmachtsformen stehen in der Tabelle, die
zwei produkteigenen Anfragekörper in zwei Funktionen. Ein zweites
Produkt ist damit eine Datei und zwei Zeilen.

Und was der Konnektor **noch nicht** kann, nennt er: `settings` —
Selbstregistrierung und zweiter Faktor **im Realm**, Schritt 6. Ein
genanntes und nicht gebautes Verb ist die kleinere Lüge.

**Zwei Regeln stehen als Funktionen auf dem Weg, nicht als
Versprechen.** *Nichts löscht* — DELETE kommt gar nicht erst aus dem
Aufruf heraus, und ein Realm ist die Mitgliederliste eines Vereins.
*Nichts entsteht halb* — die Fassung wird geprüft, bevor etwas angelegt
wird, und ein Plan, der früher schreibt, wird abgelehnt. Beides wurde
sabotiert und beides fiel auf.

**Drei Befunde von der Maschine**, und die ersten beiden sind
Widersprüche im Entwurf selbst — sie stehen in §5.3:

1. Die enge Vollmacht, die K3.4 wollte, **gibt es** — und sie ist
   enger als erwartet. Aber „nie der master-Realm" ist nicht zu haben:
   Einen Realm **anzulegen** ist ein Akt im master-Realm.
2. **K3.1 und K3.4 gehen nicht zusammen.** Die Fassung steht nur an
   einer Stelle, und die antwortet einer engen Vollmacht beschnitten.
   Also: Wo OAAP sie nicht lesen kann, **nennt sie ein Mensch** — und
   überall steht dabei, dass sie genannt und nicht gelesen wurde.
3. **Der sorgfältige Satz stand an der falschen Tür.** Den fremden
   Realm eines anderen Vereins darf OAAP nicht übernehmen; die
   Ablehnung dafür stand am Realm-Aufruf, und der antwortet mit 200.
   Abgelehnt wird erst der Blick auf die Clients — und dort stand nur
   eine nackte Zahl.

**Was Schritt 4 ausdrücklich nicht tut.** Er legt keine Menschen an
(das bleibt beim Verein oder bei Schritt 6), er schaltet nichts im
Realm ein, und er löscht nichts. Ein von Hand gebauter Realm bleibt
benutzbar, und das Rezept dafür steht weiter in der README des
Keycloak-Pakets.

## Nachtrag: gebaut am 23.09.2026 (Schritt 6)

**Was jetzt geht.** Ein Handgriff, und die beiden Schalter im Realm
stehen dort, wo der Betreiber sie haben will — und der Satz des
Mandanten sagt dasselbe:

```
sudo oaap idp settings auth --tenant hbvp --self-registration on
sudo oaap idp settings auth --tenant hbvp --second-factor required
sudo oaap idp settings auth --tenant hbvp            # nur nachsehen
```

Gemessen auf `oaap-test`, von Anfang bis Ende: Selbstregistrierung an,
Registrieren-Knopf auf der Anmeldeseite des Realms, ein Mensch hat sich
selbst registriert — und kam bei OAAP **ohne Rollen und ohne Gruppen**
an, im Eingang. Zweiter Faktor an: Wer neu dazukommt, wird von Keycloak
zur Einrichtung geschickt.

**Die Regel dieses Schritts.** Ein Schalter, der an zwei Orten steht,
hat zwei Wahrheiten. Also: geschrieben, nachgelesen, und **die Antwort**
aufgeschrieben — nie die Anweisung. Sagt der Realm etwas anderes, als
er zugesagt hat, ist das ein lauter Fehlschlag *und* der Satz wird auf
die Wirklichkeit gesetzt. Und eine Anweisung, die nicht ankam, wird
nicht zur Absicht: das Unerledigte bleibt als Unterschied stehen,
statt vom eigenen Fehlschlag aufgeräumt zu werden.

**Eine Sicherheitsregel, die es vorher nicht geben konnte.** Die
Registrierungsseite gehört dem Realm. „Rolle beim ersten Login" plus
Selbstregistrierung wird deshalb auch dann abgelehnt, wenn nur der
Realm offen ist und unsere Notiz das Gegenteil behauptet — und die
Ablehnung sagt, welche Hälfte offen ist. Live geprüft.

**Drei Befunde von der Maschine** (§5.4):

1. Die enge Vollmacht aus §5.3 **kann** die Schalter bewegen — in
   ihren eigenen Realms. In einem fremden nicht, und abgelehnt wird
   wieder am *zweiten* Dokument, nicht am ersten.
2. Der zweite Faktor erreicht nur, wer ab jetzt dazukommt. Wer schon
   da war, wird nicht nachträglich gefragt — gemessen, und seitdem
   gesagt, bevor jemand es annimmt.
3. **Eine Regel, die nie hätte feuern können.** Der Hinweis auf einen
   fehlenden zweiten Faktor wartete auf das Schweigen des Anbieters.
   Keycloak schweigt nie: es antwortet mit `acr=1`. Gelesen wird jetzt
   `amr`, das Methoden nennt; `acr` wird weiter aufgeschrieben und
   nicht bewertet, weil seine Bedeutung im Realm festgelegt wird und
   nicht hier.

**Was Schritt 6 ausdrücklich nicht tut.** Er erzwingt keinen zweiten
Faktor — das tut der Realm, und eine Anmeldung, die hier ankommt, hat
er durchgelassen. Er fasst keine Menschen an: das Verb `users` steht im
Konnektor unter `never` und nicht unter „noch nicht". Und er löscht
weiterhin nichts.
