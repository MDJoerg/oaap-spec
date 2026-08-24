# RFC-0022: Account and Tenant — OAAP's Boundary of Belonging

- **Status:** Accepted (2026-08-24)
- **Date:** 2026-08-24
- **Authors:** Claude (analysis & proposal), Jörg (decisions)
- **Depends on:** ADR-0006 (deployment scenarios), ADR-0007 (phases),
  RFC-0002 (roles), RFC-0003 (platform topology), RFC-0007 (app
  visibility groups), RFC-0008 (`server_admin`), RFC-0009/RFC-0018
  (instance names), RFC-0011 (node profiles), RFC-0021 (fleet status)
- **Driver:** Phase 1 is Jörg's own operation (ADR-0007). Three things
  next in line — messaging between apps, the digital twin, and single
  sign-on — all need the same missing concept first. The idea store has
  been collecting it since 2026-08-03 under five different headings.

## Summary

A **tenant** is OAAP's boundary of *belonging*: inside it, things may
find each other — users, apps, messages, twin entities; across it,
nothing passes except by a declared route.

An **account** is the boundary of *responsibility*: a customer
relationship that may hold several tenants, possibly on several nodes,
and that carries the things which outlive a single tenant — who
delegates what to whom, which identity providers are known, who
consumes how much.

On the great majority of installations there is exactly one account
with exactly one tenant, and **both are invisible**: Bernd's workshop,
a home lab, a hosted single-customer VM (ADR-0006 scenarios 1 and 2)
are one tenant by construction. The concept must cost those
installations *nothing*. It earns its keep in scenario 3, where one
operator serves several customers from one platform.

The proposal is therefore deliberately asymmetric: **tenant-aware
everywhere in the data model, tenant-*visible* only where more than one
exists.**

## Motivation

### 1. Three planned capabilities are blocked on the same question

- **Messaging between apps.** Which apps may send each other messages?
  "All apps on the node" is wrong the moment two customers share a
  node. Without a tenant there is no correct answer, only a risky one.
- **The digital twin.** Jörg's entry point (2026-08-24) is a CRM app
  that maintains customers and contacts and *offers those entities to
  other apps*. Offers them to whom? A twin without a boundary is a
  shared database with better manners.
- **SSO.** "One tenant, one or more identity providers" presumes the
  tenant exists. Realms cannot be cut along a line that is not drawn.

### 2. The role split has been deferred twice, with a real case each time

On 2026-08-04 Bernd needed to be "Geschäftsführer" in his CRM and would
have had to become OAAP `admin` — full power over Jörg's server. The
decision then: this is the multi-tenancy dimension, it comes with the
tenant RFC. On 2026-08-07 the same need returned through RFC-0007, and
`server_admin` was pulled forward as RFC-0008 — explicitly **only the
server half**, with `tenant_admin` left to this document.

### 3. The multi-tenant scenario stopped being hypothetical

ADR-0006 records it as one of three equal target scenarios, and the
conversation with the hosting acquaintance (2026-08-23) gave it shape.
Jörg's requirement (2026-08-24) sharpens it further: there are **two
managed models**, and they differ in who does the work, not in who owns
the machine — *we own all tenants* versus *we operate tenants but
delegate the usual administration to the customer*.

## The model

```text
Account            "Kunde Meier GmbH"   — responsibility, delegation, usage
  ├── Tenant       "meier-prod"  on node A   — belonging: users, apps, twin
  ├── Tenant       "meier-test"  on node A
  └── Tenant       "meier-lab"   on node B
```

- An **account** holds one or more tenants. It may span nodes.
- A **tenant** lives on exactly one node (decision D1).
- Every **instance** belongs to exactly one tenant.
- Every **user** is a member of exactly one tenant; the **identity
  provider** they authenticate against may serve many tenants (D3).

### What a tenant is not

- **not a node.** A node may carry tenants of several accounts; the
  node — updates, ports, certificates, profiles — belongs to the
  operator, never to a tenant. That is the `server_admin` line RFC-0008
  already drew.
- **not a visibility group.** RFC-0007 groups say *who among a tenant's
  users sees which app*. They live inside a tenant and stay as they are.
- **not an app.** The same app may run for many tenants; each instance
  belongs to exactly one.
- **not a billing construct.** Usage is *measured* per tenant and per
  account (§7); whether anyone invoices it is outside this RFC.

The sentence to keep: **inside a tenant, things may find each other;
across tenants, only what someone declared.**

## Proposal

### 1. Default account and default tenant are invisible

Every installation has both from the first minute. On a single-tenant
node they are `default`, created by the installer, and **no screen ever
mentions them**: no selector, no column, no extra path segment.
Existing installations gain them in a migration that changes no
behaviour.

Rationale: introducing tenancy later as a "big switch" would mean a
data migration on live systems at exactly the moment someone is under
pressure to onboard a second customer. Carrying an unused dimension
costs a column; retrofitting one costs a weekend.

### 2. Identity: one platform contract, many providers per tenant

The App Deployment Contract's first guarantee is that an app **never
builds a login** — a verified identity arrives as `X-OAAP-User` /
`X-OAAP-Roles` from the gateway. That guarantee survives tenancy
untouched, or every app on the platform becomes a multi-tenancy
project.

So: **the platform keeps exactly one identity contract**, and a tenant
attaches **one or more identity providers** (D3):

- the platform's own built-in identity (the default, and all a
  single-tenant installation ever sees),
- the **customer's** provider — in the SAP world the normal case, the
  customer brings the SSO,
- the **service provider's own** provider, attached to customer tenants
  for maintenance access.

An identity provider is a **reusable object**: the same one may be
attached to several tenants, including tenants on different nodes. What
is shared is the *authentication source*, never the authorization:

> **The same human authenticating into two tenants is two principals.**
> Roles, groups and sessions are per tenant and do not travel. A
> maintenance engineer who can log into twelve customer tenants holds
> twelve separate memberships, each one visible and revocable on its
> own.

This is what makes D3 a *"jein"* rather than a "yes": users are not
shared, providers are.

### 3. Names: label, and internally a UUID

A tenant carries three names, deliberately separated (D4):

| | | |
| --- | --- | --- |
| **`id`** | UUID, immutable, never displayed | everything internal refers to this |
| **`label`** | short, unique per node, **editable** | appears in hostnames: `<instance>.<label>.<node>` |
| **`name`** | free text, e.g. "Kunde Meier GmbH" | what humans read in the portal |

The label is maintained in tenant administration, may be changed later,
and is checked for duplicates on change. It is usually a short code or
even a UUID, because a hostname is public and an operator may not want
to reveal who their customers are — a concern the certificate finding
(CURRENT_STATE 84) makes concrete: instance hostnames end up in public
Certificate Transparency logs.

Because everything internal refers to the UUID, a label change is a
**renaming, not a migration**. But it *is* an address change, and this
platform has already paid for one: `hub.bdt.joomp.de` disappeared from
a live client on 2026-08-23 (CURRENT_STATE 76/77). Therefore:

- changing a label warns with named consequences, as instance address
  removal now does;
- the previous label keeps working as an alias for a grace period —
  RFC-0018 already gives instances several names, and this reuses that
  machinery rather than inventing a second one.

For the default tenant nothing changes: `<instance>.<node>` stays, as
RFC-0018 describes it.

**Measured, not assumed (2026-08-24):** under `oaap.joomp.de` a
two-level name such as `app.kunde-a.oaap.joomp.de` resolves to the node
today — our DNS provider's wildcard covers the whole subtree. The DNS
standard does *not* guarantee this: a wildcard matches exactly one
label. An implementation must therefore treat two-level resolution as
**a property of the zone, not of DNS**. The node checks it (it already
runs a DNS watchdog) and says so *before* a tenant is created, not
after its apps are unreachable.

### 4. Roles: who may do what

`server_admin` (RFC-0008) **may do everything** — that is Jörg's
decision (D5) and it is the only honest model for someone who has root
on the machine anyway. The counterweight is not a restriction but
**transparency**: see §6.

From that follows an operating rule, not a technical one (Jörg, Q2):
**in a multi-tenant environment `server_admin` is not a working
account.** It is the firefighter — used for emergencies, held by
dedicated, *named* people, and never the account someone does their
daily job with. Every `server_admin` action that touches a tenant
belongs in the tenant's audit log (§6).

The mechanism that makes this practicable — full server access granted
to service staff for a bounded time, possibly through temporary users —
is a concept of its own ("fire fighter" access) and gets its own RFC.
It is named here because this decision creates the need for it.

`tenant_admin` is the half RFC-0008 left open. The node operator
creates a tenant and its first `tenant_admin` in the node's user
administration; from there the tenant administers itself:

| | `server_admin` | `tenant_admin` |
| --- | --- | --- |
| Node updates, profiles, ports, certificates | ✔ | ✘ |
| Create accounts and tenants, appoint the first tenant admin | ✔ | ✘ |
| Users and roles **of their tenant** | ✔ | ✔ |
| Attach/detach identity providers of their tenant | ✔ | ✔ |
| Install and remove app instances of their tenant | ✔ | ✔ |
| Deploy tokens and creation permits of their tenant | ✔ | ✔ |
| See other tenants | ✔ | ✘ |

A portal user therefore carries a role **plus** two assignments:
account and tenant. The Bernd case from 2026-08-04 resolves cleanly:
Bernd becomes `tenant_admin` of his own tenant and never touches Jörg's
server.

The two managed models (Jörg, D5) are then just two configurations of
the same mechanism, not two products:

- **we own all tenants** — the operator holds `tenant_admin` for every
  tenant; no customer accounts exist.
- **we operate, the customer administers** — the customer's people hold
  `tenant_admin`, the operator keeps `server_admin` and stays out of
  daily work.

### 5. Messaging and twin: the boundary is the feature

Both get their own RFCs and are **not designed here**. What this RFC
fixes for them is the scope rule:

- an app may address only apps **of its own tenant**;
- twin entities are visible **within their tenant**;
- anything crossing a tenant border is not a message but an
  **integration** — declared, named, auditable.

Worth stating now even though nothing implements it: it is far cheaper
to draw a boundary before two apps have learned to ignore it.

### 6. Audit: tenant actions are visible, and so is looking

Jörg's requirement (D5): an audit log for tenant actions, visible in
the administrator's view. Proposed shape, following the precedent
already set by the fleet key log and the deploy log:

- **What is recorded:** who, when, which action, which tenant, result.
  Creating and deleting tenants and accounts; appointing and removing
  administrators; attaching and detaching identity providers;
  installing and removing instances; issuing and revoking tokens.
- **Who sees it:** a `tenant_admin` sees their own tenant's entries; a
  `server_admin` sees all of them.
- **Access by the operator is itself an event.** Because
  `server_admin` may do everything, the record of *what they did* is
  what makes the arrangement trustworthy. Actions of a `server_admin`
  against a tenant are logged in that tenant's log, not in a separate
  operator log — the customer must be able to see them. This is the
  same principle the idea store already fixed for partner delegation
  (2026-08-23): metadata always, payload only deliberately and
  announced.
- **The audit log is load-bearing, not an accessory.** In this model
  the customer's trust rests on it alone: there is no technical barrier
  in front of a `server_admin`, and pretending otherwise would be
  dishonest. It therefore ranks with `tenant_admin` in stage 3, not
  after it.

### 7. Usage is measured, not capped (revision of D6)

Jörg's question — *what would a quota actually limit?* — is the right
one, and it changes my earlier recommendation.

On a single OAAP node the scarce goods are RAM, disk and CPU of one
machine. A number in a database limits none of them: unless the
container runtime enforces it, a quota is theatre — and the moment it
*is* enforced, it becomes an outage during someone's business hours.

Proposal: **stage 1 counts and shows, it does not stop.** Per tenant
and per account: number of instances, storage used, and (from §8) AI
consumption. A `server_admin` sees who uses what; a `tenant_admin` sees
their own. Real limits get added when a real case appears — and then as
runtime limits per instance (which Docker can actually enforce), not as
a number in a table.

This also serves the accounting Jörg wants in D8: the same measurement
feeds both.

### 8. AI gateway: chained, keyed, metered (hooks only)

The `oaap.ai.gateway` capability gets **its own RFC**. What this one
reserves is where it hangs (D8):

- an AI gateway usually sits **on the node**, and the operator "rents"
  capacity to tenants;
- a gateway may also be configured **within a tenant**, or **account-
  wide across the account's tenants**;
- a gateway may draw from the node's gateway, from an account gateway,
  or from an external node — the layers chain.

Two properties belong in this RFC because they are account/tenant
properties, not model properties:

- **whoever operates a gateway issues the API keys** that permit
  consumption — the same "a right is given, not held" pattern as the
  deploy token (RFC-0019);
- **usage is booked per consumer, and every consumer sees their own** —
  a tenant sees its own consumption, an account sees its tenants'.
  Whether it is invoiced onward is outside our scope.

## Decisions (Jörg, 2026-08-24)

- **D1 — a tenant does not span nodes.** Accepted as recommended.
- **D2 — the default tenant is invisible.** Accepted as recommended.
- **D3 — users are not shared, identity providers are.** A tenant has
  one or more IdPs; an IdP may serve several tenants, including on
  different nodes (SAP pattern: the customer brings the SSO; the
  service provider attaches its own for maintenance). Authorization
  stays per tenant.
- **D4 — `<instance>.<label>.<node>`,** with the label an editable,
  duplicate-checked field of tenant administration, usually a code or
  UUID; internally everything refers to a UUID.
- **D5 — `tenant_admin` administers their tenant**, including app
  installation and IdP assignment; the node operator creates tenant and
  first admin. **`server_admin` may do everything.** New: the
  **account** above the tenant, and portal users carrying account and
  tenant assignments alongside their role. Audit log for tenant
  actions, visible to administrators.
- **D6 — revised** (§7): no quota in stage 1; measure and show instead.
- **D7 — backup per tenant**, and per account as the sum of its
  tenants.
- **D8 — AI gateway chained** across node, account and tenant, with
  API keys issued by whoever operates a gateway and per-consumer usage
  visible to that consumer. Own RFC.

## Decisions, second round (Jörg, 2026-08-24)

- **Q1 — the account lives on the central management node.** Nodes know
  only their own tenants plus an opaque account reference; no cross-node
  write path is created, and RFC-0021 stage 2 is not pre-empted. The
  price is accepted knowingly: without the management node an account is
  only a label on a tenant, and cross-node views — account-wide usage,
  an identity-provider registry one does not retype per node — exist
  only where that node exists.
- **Q2 — the customer may detach the maintenance provider**, everything
  is logged, and they carry the consequences. `server_admin` remains the
  way back in — as **firefighter, not as a working account** (see §4),
  held by named people, with every tenant-facing action in the tenant's
  audit log. A bounded "fire fighter" access for service staff becomes
  its own RFC.
- **Q3 — a changed label keeps working for a grace period** as an alias.
- **Q4 — stage 2 is pulled forward regardless** (tenant- and
  account-aware, invisible to everyone). Everything above it waits for a
  real case; Jörg is weighing two — making the BDT scenario
  multi-tenant, or the AI gateway.

## Staging

1. **Concept accepted** (this RFC, Q1–Q4 answered).
2. **Account- and tenant-aware, both invisible:** the dimension in
   identity, registry, portal and backup; UUIDs internally; `default`
   everywhere; nothing changes for anyone.
3. **`tenant_admin`, the second tenant, the audit log:** roles,
   assignments, tenant administration, labels in names, usage figures.
4. **Federated login per tenant** — one or more IdPs, the maintenance
   pattern of §2.
5. **AI gateway** (own RFC) and **messaging / digital twin** (own
   RFCs) on top of the finished boundary. Jörg's CRM-as-twin-source is
   the intended first consumer.

## Non-goals (deliberate)

- No resource isolation and no enforced quota (§7).
- No cross-tenant sharing mechanism — that is the integration topic.
- No tenant spanning nodes (D1).
- No change to app manifests. An app must not need to know it lives in
  a tenant; if it does, the boundary is in the wrong place.

## Security considerations

- **The boundary is enforced at the gateway, not in apps.** An app that
  filters by tenant itself is one bug away from a leak between
  customers. The identity headers an app receives are already scoped.
- **Tenant labels are public.** They appear in hostnames and therefore
  in Certificate Transparency logs (CURRENT_STATE 84). This is the
  reason labels are opaque by default — and the case in which the
  deferred wildcard-certificate ADR becomes a real decision.
- **`server_admin` may do everything.** The protection is not a
  restriction but a record: §6 makes every tenant action visible,
  including the operator's own.
- **A tenant export is a customer's complete data set in one file.**
  Whatever stage 3 builds must treat it that way.

## Zusammenfassung auf Deutsch

Ein **Mandant** ist die Grenze des Zusammengehörens: Innerhalb dürfen
sich Dinge finden — Benutzer, Apps, Nachrichten, Zwillings-Entitäten;
darüber hinaus geht nichts außer auf einem erklärten Weg. Neu in dieser
Runde (Jörg, 24.08.): darüber der **Account** als Grenze der
Verantwortung — ein Kundenverhältnis, das mehrere Mandanten halten
kann, auch auf mehreren Knoten. Ein Mandant selbst bleibt auf **einem**
Knoten.

Auf den allermeisten Installationen gibt es genau einen Account mit
genau einem Mandanten, und **beide sind unsichtbar**. Der Vorschlag ist
deshalb bewusst asymmetrisch: überall mandantenfähig im Datenmodell,
sichtbar nur dort, wo es mehr als einen gibt.

**Identität:** Die Plattform behält genau **einen** Identitäts-Vertrag
— Apps bauen nie einen Login. Ein Mandant hängt **einen oder mehrere
Identity-Provider** an: den eingebauten, den des Kunden (im
SAP-Umfeld der Normalfall) und den des Dienstleisters für
Wartungszugänge. Geteilt wird die **Anmeldequelle**, nie die
Berechtigung: Derselbe Mensch in zwei Mandanten ist zweimal
Mitglied — Rollen, Gruppen und Sitzungen wandern nicht mit, und jede
Mitgliedschaft ist einzeln sichtbar und einzeln entziehbar.

**Namen:** Ein Mandant trägt eine unveränderliche **UUID** (intern),
ein **Kürzel** (im Hostnamen `app.kuerzel.knoten`, pflegbar,
Dublettenprüfung beim Ändern) und einen **Klarnamen** (fürs Portal).
Das Kürzel ist meist bewusst nichtssagend, weil Hostnamen öffentlich
sind. Ein Kürzelwechsel ist dank UUID eine Umbenennung, aber eben auch
ein Adresswechsel — deshalb mit Warnung und Übergangsfrist, wir haben
gelernt, was ein harter Schnitt kostet.

**Rollen:** `server_admin` darf alles; das Gegengewicht ist kein
Verbot, sondern **Sichtbarkeit** — ein Audit-Log über Mandanten-
Aktionen, in dem auch das Handeln des Betreibers steht.
`tenant_admin` verwaltet seinen Mandanten selbst, inklusive
App-Installation und IdP-Zuordnung. Die zwei Managed-Modelle
(„uns gehören alle Mandanten" vs. „wir betreiben, der Kunde
verwaltet") sind damit zwei Konfigurationen desselben Mechanismus,
kein zweites Produkt.

**Kontingente entfallen in Stufe 1** (Antwort auf Jörgs Rückfrage):
Eine Zahl in der Datenbank begrenzt kein RAM. Stufe 1 **misst und
zeigt** — Instanzen, Speicher, KI-Verbrauch, je Mandant und je Account;
echte Grenzen kommen als Laufzeit-Limits, wenn ein realer Fall da ist.
Dieselbe Messung trägt die Abrechnung des KI-Gateways.

**Die vier offenen Fragen sind entschieden** (Jörg, 24.08.): Der
**Account liegt auf dem zentralen Management-Knoten** — damit entsteht
kein Schreibweg zwischen Knoten, und der Preis ist wissentlich in Kauf
genommen: Ohne diesen Knoten ist ein Account nur ein Etikett. Der
**Kunde darf den Wartungs-IdP abhängen**, alles wird protokolliert, und
er trägt die Folgen; `server_admin` bleibt der Weg zurück — aber
ausdrücklich als **Feuerwehr und nicht als Arbeitskonto**, geführt von
namentlich bekannten Personen, mit jeder mandantenbezogenen Handlung im
Audit-Log des Mandanten. Ein zeitlich begrenzter Notfallzugang für
Service-Mitarbeiter („Fire Fighter") bekommt ein eigenes RFC. Ein
**altes Kürzel überlebt eine Übergangsfrist** als Alias. Und **Stufe 2
wird in jedem Fall vorgezogen**, weil sie unsichtbar, jetzt billig und
später teuer ist; alles darüber wartet auf einen echten Fall.

Damit ist das Konzept **angenommen**. Was daraus folgt, verteilt sich
auf eigene RFCs: Fire-Fighter-Zugang, KI-Gateway, Messaging und
digitaler Zwilling.
