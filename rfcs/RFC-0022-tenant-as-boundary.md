# RFC-0022: The Tenant — OAAP's Boundary of Belonging

- **Status:** Draft — decisions open (2026-08-24)
- **Date:** 2026-08-24
- **Authors:** Claude (analysis & proposal), Jörg (decisions)
- **Depends on:** ADR-0006 (deployment scenarios), RFC-0002 (roles),
  RFC-0003 (platform topology), RFC-0007 (app visibility groups),
  RFC-0008 (`server_admin`), RFC-0009/RFC-0018 (instance names),
  RFC-0011 (node profiles)
- **Driver:** Phase 1 is now Jörg's own operation (ADR-0007). Three
  things that are next in line — messaging between apps, the digital
  twin, and single sign-on — all turn out to need the same missing
  concept first. The idea store has been collecting it since
  2026-08-03 under five different headings; this RFC pulls them
  together and asks the questions that only Jörg can answer.

## Summary

A **tenant** is OAAP's boundary of *belonging*: inside it, things may
find each other — users, apps, messages, twin entities, a single
login; across it, nothing passes except by a declared route. It is the
missing dimension that messaging, the digital twin and SSO are all
waiting for.

On the great majority of installations there is **exactly one tenant,
and it is invisible**: Bernd's workshop, a home lab, a hosted single-
customer VM (ADR-0006 scenarios 1 and 2) are one tenant by
construction. The concept must cost those installations *nothing* — no
extra screen, no extra decision, no extra path segment. It earns its
keep only in ADR-0006 scenario 3, where one operator serves several
customers from one platform.

The proposal is therefore deliberately asymmetric: **tenant-aware
everywhere in the data model, tenant-*visible* only where more than one
exists.** That was already the recommendation on 2026-08-03
("tenant-aware by design"); this RFC makes it concrete.

## Motivation

### 1. Three planned capabilities are blocked on the same question

- **Messaging between apps.** Which apps may send each other messages?
  "All apps on the node" is wrong the moment two customers share a
  node. Without a tenant there is no correct answer, only a risky one.
- **The digital twin.** Jörg's entry point (2026-08-24) is a CRM app
  that maintains customers and contacts and *offers those entities to
  other apps*. Offers them to whom? A twin without a boundary is a
  shared database with better manners.
- **SSO.** "One tenant = one Keycloak realm" (2026-08-23) presumes the
  tenant exists. Realms cannot be cut along a line that is not drawn.

### 2. The role split has been deferred twice, with a real case each time

On 2026-08-04 Bernd needed to be "Geschäftsführer" in his CRM and would
have had to become OAAP `admin` — full power over Jörg's server. The
decision then: do not widen the role model, this is the multi-tenancy
dimension, it comes with the tenant RFC. On 2026-08-07 the same need
returned through RFC-0007, and `server_admin` was pulled forward as
RFC-0008 — explicitly **only the server half**, with `tenant_admin`
left to this document. The debt is now two entries old and has a name.

### 3. The multi-tenant scenario stopped being hypothetical

ADR-0006 records it as one of three equal target scenarios, and the
conversation with the hosting acquaintance (2026-08-23) put a concrete
shape on it. The "external developers" test scenario in the idea store
— strangers logging in via SSO, using the Studio, owning repositories
on our Forgejo — is the first real multi-tenant case and is also the
first driver for tenant-bound identity.

## What a tenant is — and what it is not

A tenant is **a set of things that belong together and may therefore
find each other**. Concretely, one tenant owns:

- its **users** and their roles,
- its **app instances**,
- its **names** (see §4),
- its **messages** and **twin entities**,
- its **login** (which identity provider its people authenticate
  against).

A tenant is **not**:

- **not a node.** A node may carry several tenants; the node — its
  updates, ports, certificates, profiles — belongs to the operator,
  never to a tenant. This is exactly the `server_admin` line RFC-0008
  already drew.
- **not a visibility group.** RFC-0007 groups say *who among a
  tenant's users sees which app*. They live inside a tenant and stay
  as they are.
- **not an app.** The same app may run for many tenants; each
  instance belongs to exactly one.
- **not necessarily a legal entity.** "Demo", "Test", "Family" are
  legitimate tenants. The concept is technical, not commercial.

The single sentence to keep: **inside a tenant, things may find each
other; across tenants, only what someone declared.**

## Proposal

### 1. The default tenant is invisible

Every installation has a tenant from the first minute. On a single-
tenant node it is called `default`, it is created by the installer, and
**no screen ever mentions it**: no selector, no column, no path
segment, no additional click. Existing installations gain it in a
migration that changes no behaviour.

Rationale: the alternative — introducing tenants later as a "big
switch" — would mean a data migration on live systems at exactly the
moment someone is under pressure to onboard a second customer. Carrying
an unused dimension costs a column; retrofitting one costs a weekend.

### 2. Every instance belongs to exactly one tenant

The registry entry of an instance gains a tenant. Consequences:

- the launchpad shows a user the apps of **their** tenant,
- health and fleet views can group by tenant (the "Mandanten-Brille"
  for service providers, idea store 2026-08-21),
- backup and restore gain a natural unit: *this customer's data*,
- a tenant can be **moved** to another node — the scenario the idea
  store calls "Demo-Tenant bei Jörg → eigenes System".

### 3. `tenant_admin` — the half RFC-0008 left open

Two administrators, cleanly separated:

| | `server_admin` (RFC-0008) | `tenant_admin` (new) |
| --- | --- | --- |
| Node updates, profiles, ports, certificates | ✔ | ✘ |
| Create/remove tenants | ✔ | ✘ |
| Users and roles **of their tenant** | ✘ (may delegate) | ✔ |
| Install/remove app instances of their tenant | ✘ | ✔ (within quota) |
| Deploy tokens, creation permits of their tenant | ✘ | ✔ |
| See other tenants | ✘ | ✘ |

The Bernd case from 2026-08-04 resolves cleanly: Bernd becomes
`tenant_admin` of his own tenant and never touches Jörg's server.

### 4. Names: `<instance>.<tenant>.<node>` — and only when needed

Recommendation from 2026-08-23 confirmed: **subdomain, not path
prefix**. Wrapped apps expect to own `/` (the registry finding of
2026-08-21), and cookies separate per hostname instead of being shared
across a whole domain.

For the default tenant nothing changes: `<instance>.<node>` stays, as
RFC-0018 describes it. A named tenant inserts one label:
`<instance>.<tenant>.<node>`. Registered own names (RFC-0009) are
unaffected — they belong to the instance and say nothing about tenancy.

**Measured, not assumed (2026-08-24):** under `oaap.joomp.de` a
two-level name such as `app.kunde-a.oaap.joomp.de` resolves to the node
today — our DNS provider's wildcard covers the whole subtree. This is
*not* guaranteed by the DNS standard, which matches a wildcard against
exactly one label. An implementation must therefore treat two-level
resolution as **a property of the zone, not of DNS** — and a node whose
provider implements the strict rule needs either per-name records or a
wildcard per tenant. The node can check this itself (it already runs a
DNS watchdog) and say so before a tenant is created, rather than after
its apps are unreachable.

### 5. Identity: the platform keeps one contract, the tenant chooses its login

This is the most consequential proposal in this document.

The App Deployment Contract's first guarantee is that an app **never
builds a login** — a verified identity arrives as `X-OAAP-User` /
`X-OAAP-Roles` from the gateway. That guarantee must survive tenancy
untouched, or every app on the platform becomes a multi-tenancy
project.

Therefore: **the platform keeps exactly one identity contract**, and a
tenant may *federate* its login to an external provider — a Keycloak
realm, a customer's AD, Google. "One tenant = one realm" then describes
an implementation of a tenant's login, not a new platform dependency.
Single-tenant installations keep the built-in identity and never meet
Keycloak.

The alternative — making Keycloak the platform identity — was
considered and is not recommended: it would put a heavyweight
dependency in front of Bernd's workshop to serve a case Bernd will
never have, and it contradicts the spec's runtime-neutral stance
(ADR-0004's reasoning, applied to identity).

### 6. Messaging and twin: the boundary is the feature

Both are separate RFCs and are **not designed here**. What this RFC
fixes for them is the scope rule:

- an app may address only apps **of its own tenant**;
- twin entities are visible **within their tenant**;
- anything crossing a tenant border is not a message but an
  **integration** — declared, named, auditable (the idea store's
  "Destinations / Dataspace" direction).

That rule is worth writing down now even though nothing implements it
yet: it is much cheaper to state a boundary before two apps have
learned to ignore it.

## Decisions to make (Jörg)

Each with my recommendation. Nothing below is built before these are
answered.

**D1 — Does a tenant live on one node, or may it span nodes?**
*Recommendation: one node, for now.* A tenant spanning nodes needs a
write path between nodes, which RFC-0021 deliberately does not have
(stage 2, signed commands). Moving a tenant between nodes stays
possible; being in two places at once does not.

**D2 — Is the default tenant truly invisible, or shown as "Default"?**
*Recommendation: invisible.* Anything else taxes the 80 % for the
benefit of the 20 %.

**D3 — May one user belong to several tenants?**
*Recommendation: no, in stage 1.* One account, one tenant. A person who
needs two gets two accounts. Cross-tenant identity is where most
multi-tenancy accidents live, and the partner case (a service provider
looking after several customers) is better served by the management
node of RFC-0021 than by a double-tenant user.

**D4 — Names: `<instance>.<tenant>.<node>` — confirmed?**
*Recommendation: yes*, with the DNS caveat measured in §4 checked by
the node before a tenant is created.

**D5 — Is `tenant_admin` allowed to install apps from the store on
their own?** *Recommendation: yes, within a quota set by
`server_admin`* — otherwise the operator becomes a ticket queue and the
whole point of self-service is lost. What `tenant_admin` may never do
is anything that touches the node.

**D6 — Quotas: does stage 1 count anything (instances, storage, CPU)?**
*Recommendation: count instances only, and only as a soft limit with a
clear message.* Real resource isolation is a container-runtime topic
and would balloon this RFC.

**D7 — Does the tenant own its backup?**
*Recommendation: yes* — per-tenant backup and restore, because it is
the unit a customer actually asks about ("give me my data"), and
because tenant moves need it anyway.

**D8 — Where does the AI gateway sit?** The idea store's
`oaap.ai.gateway` candidate lets an admin route model traffic centrally
or per tenant. *Recommendation: tenant-scoped configuration with a
node-level default* — a customer's data-protection choice is a tenant
property, not a node property. Flagged here because Jörg named AI
hosting as increasingly interesting; the gateway gets its own RFC and
should not be pulled into this one.

## Staging

1. **Concept accepted** (this RFC, decisions above).
2. **Tenant-aware, tenant-invisible**: the dimension in identity,
   registry and portal; `default` everywhere; nothing changes for
   anyone. This is the step that must not be postponed — it is what
   makes step 3 cheap.
3. **`tenant_admin` and the second tenant**: roles, tenant
   administration, names, quota. Driven by a real case — the "external
   developers" scenario or the hosting acquaintance.
4. **Federated login per tenant** (Keycloak realm as the first
   implementation).
5. **Messaging / digital twin** on top of the finished boundary —
   separate RFCs. Jörg's CRM-as-twin-source is the intended first
   consumer.

## Non-goals (deliberate)

- No resource isolation beyond a counted quota (D6).
- No cross-tenant sharing mechanism — that is the integration topic and
  needs its own RFC.
- No tenant spanning nodes (D1).
- No change to app manifests. An app must not need to know it lives in
  a tenant; if it does, the boundary is in the wrong place.

## Security considerations

- **The boundary must be enforced at the gateway, not in apps.** An app
  that filters by tenant itself is one bug away from a data leak
  between customers. The identity headers an app receives must already
  be scoped.
- **Instance names are visible.** Certificates are public
  (CURRENT_STATE 84): if tenant names appear in hostnames, the tenant
  list is public. For a hosting operator that may be unacceptable —
  and it is the case where the deferred wildcard-certificate ADR
  becomes a real decision rather than a note.
- **A tenant move carries data.** Whatever step 3 builds must treat an
  export as what it is: a customer's complete data set in one file.

## Zusammenfassung auf Deutsch

Ein **Mandant** ist die Grenze des Zusammengehörens: Innerhalb dürfen
sich Dinge finden — Benutzer, Apps, Nachrichten, Zwillings-Entitäten,
eine gemeinsame Anmeldung; über die Grenze geht nichts außer auf einem
erklärten Weg. Genau dieses Konzept fehlt heute, und **Messaging,
digitaler Zwilling und SSO warten alle drei darauf**.

Auf den allermeisten Installationen gibt es **genau einen Mandanten,
und er ist unsichtbar** (Bernds Werkstatt, Home Lab, eine gehostete
Einzelkunden-VM). Der Vorschlag ist deshalb bewusst asymmetrisch:
**überall mandantenfähig im Datenmodell, sichtbar nur dort, wo es mehr
als einen gibt.** Eine ungenutzte Dimension mitzuführen kostet eine
Spalte; sie später nachzurüsten kostet ein Wochenende — und zwar genau
dann, wenn gerade ein zweiter Kunde drängt.

Kernpunkte: Jede Instanz gehört genau einem Mandanten. `tenant_admin`
ist die Hälfte, die RFC-0008 offengelassen hat — damit löst sich der
Bernd-Fall vom 04.08. sauber auf (Bernd wird Mandanten-Admin, ohne je
Jörgs Server anfassen zu können). Namen bekommen eine Ebene
(`app.kunde.knoten`) — nachgemessen: Unser DNS-Anbieter beantwortet
solche zweistufigen Namen bereits, was der DNS-Standard aber **nicht**
garantiert, der Knoten muss es also selbst prüfen. Und die wichtigste
Festlegung: **Die Plattform behält genau einen Identitäts-Vertrag** —
Apps bauen weiterhin nie einen Login —, ein Mandant darf seine
Anmeldung an einen externen Anbieter delegieren (Keycloak-Realm, AD,
Google). Keycloak wird damit die Umsetzung einer Mandanten-Anmeldung,
nicht eine neue Abhängigkeit der Plattform.

**Acht Entscheidungen liegen bei Jörg** (D1–D8, jeweils mit Empfehlung):
Mandant auf einem Knoten oder über Knoten hinweg; Default-Mandant
unsichtbar; ein Benutzer in mehreren Mandanten; Namensschema; darf ein
Mandanten-Admin selbst installieren; Kontingente; Backup je Mandant;
und wo das KI-Gateway sitzt. Gebaut wird nichts, bevor sie beantwortet
sind.
