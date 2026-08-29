# oaap.core.tenant — Account and Tenant, the Boundary of Belonging

- **ID:** `oaap.core.tenant`
- **Version:** 0.1 (RFC-0022 stage 2: the dimension exists everywhere,
  and is visible nowhere)
- **Maturity:** draft
- **Based on:** RFC-0022 (account and tenant), RFC-0002 (default deny),
  RFC-0007 (visibility groups), RFC-0008 (`server_admin`), RFC-0018
  (instance names), RFC-0019 (deploy tokens and creation permits),
  ADR-0006 (deployment scenarios)

## Purpose

A **tenant** is the boundary of belonging: inside it, things may find
each other — users, app instances, later messages and twin entities;
across it, nothing passes except by a declared route. An **account** is
the boundary of responsibility: a customer relationship that may hold
several tenants, possibly on several nodes.

This version implements exactly one thing, and it is deliberately
nothing anyone can see:

> **Every record that belongs to somebody carries a tenant. While a
> node has exactly one tenant, no surface mentions tenants at all.**

The reason for building it now, before it is needed, is stated in
RFC-0022: carrying an unused dimension costs a column, retrofitting one
costs a weekend — and that weekend would fall exactly when a second
customer is waiting to be onboarded.

## 1. The model on a node

```text
account   (reference only — see 1.3)
  +-- tenant  --  users, app instances, deploy tokens, creation permits
```

- A tenant lives on **exactly one node** (RFC-0022 D1). A node may
  carry many tenants.
- Every **user** is a member of exactly one tenant.
- Every **app instance** belongs to exactly one tenant.
- The **node itself belongs to no tenant.** Updates, ports,
  certificates, profiles, store sources and fleet keys are the
  operator's, never a tenant's — the `server_admin` line of RFC-0008.

### 1.1 The tenant record

| Field          | Rules                                                                       |
| -------------- | --------------------------------------------------------------------------- |
| `id`           | UUIDv4, assigned once, **immutable**, never displayed                       |
| `label`        | `[a-z0-9][a-z0-9-]{0,30}`, unique per node, editable (0.2); `default` on a single-tenant node |
| `name`         | free text for humans, e.g. "Kunde Meier GmbH"                               |
| `account`      | opaque account reference (UUID) — see 1.3                                   |
| `account_name` | cached display text for the account; never authoritative                    |
| `created`      | ISO-8601 timestamp                                                          |

**Everything internal refers to `id`.** Not to the label, and never to
the name. This is what makes a later label change a renaming instead of
a migration (RFC-0022 D4) — and a label change *is* coming, because a
label ends up in hostnames and hostnames end up in public Certificate
Transparency logs.

### 1.2 The default tenant

Every installation has one from the first minute: label `default`, name
empty, created by the installer or by the migration of 1.5. Its `id` is
a **freshly generated UUID per node**, not a well-known constant — two
nodes' default tenants are different tenants, and giving them the same
identifier would invite exactly the merge that RFC-0022 D1 forbids.

### 1.3 The account is a reference, not a registry

RFC-0022 Q1 places the account on the central management node. A node
therefore stores an account **UUID plus a cached name** and nothing
else: no members, no delegation, no cross-node write path. On a node
without a management node the account is honestly what it is — a label
on a tenant.

### 1.4 What carries a tenant, and what deliberately does not

Carries a tenant reference:

| Record                                  | Stored or derived | Why                                   |
| --------------------------------------- | ----------------- | ------------------------------------- |
| user account (`oaap.core.identity` 2.2) | stored            | membership is per tenant              |
| app instance (registry)                 | stored            | every instance belongs to exactly one |
| deploy token (RFC-0019)                 | **derived**       | a token is bound to exactly one instance, and the instance already says which tenant it is in |
| creation permit (RFC-0019)              | **stored**        | it is issued *before* the instance exists — there is nothing to derive from |
| backup manifest (`oaap.data.backup`)    | stored            | RFC-0022 D7: backup per tenant        |

The distinction is worth the extra column. A tenant reference stored in
two places is a tenant reference that can disagree with itself, and the
day it does, the wrong copy decides who may write into whose instance.
So: **derive wherever something already knows the answer, store only
where nothing does.** The creation permit is the one place where
nothing does — which also makes it the place where the tenant must be
chosen deliberately, by the human issuing it.

Does **not** carry a tenant, on purpose:

- **Node-level facts** — profiles, external hostname, edge routing,
  store sources, the update channel. They belong to the operator.
- **Fleet keys and the fleet status document** (`oaap.fleet.status`).
  A fleet key answers "what is the state of this *node*". Scoping it to
  a tenant would either shrink it into uselessness or pretend an
  isolation it does not have. When tenants become visible (0.2), the
  fleet document gains tenant *labels* as facts; the key stays the
  operator's.
- **App manifests.** RFC-0022 non-goal, and the load-bearing one: an
  app must never learn that it lives in a tenant. If it has to know,
  the boundary is in the wrong place — and every app on the platform
  becomes a multi-tenancy project.

### 1.5 Migration of an existing installation

On first run of a node that has no tenant store:

1. create the default account reference and the default tenant (1.2);
2. assign every existing user and every existing app instance to it;
3. assign every existing creation permit to it (deploy tokens need
   nothing — they follow their instance);
4. change nothing else, and say nothing about it.

The step is idempotent and silent when there is nothing to do, like
every other migration step on this platform.

## 2. Interface

### 2.1 Reading

- `oaap tenant list` — the tenants of this node. On a single-tenant
  node it prints the default tenant and one sentence saying that
  tenants are not in use here.
- `oaap tenant show [<label>]` — one tenant with its counts (users,
  instances). Counts, not names: this command is an inventory, not a
  data export.
- `oaap tenant check` — the integrity check of 3.2. Exit code 0 when
  every record resolves, 1 when any does not.

Creating, renaming and deleting tenants is **0.2** (RFC-0022 stage 3),
together with `tenant_admin`, the audit log and labels in hostnames.
This version has no way to create a second tenant, because a second
tenant that nobody can administer is worse than none.

### 2.2 Resolution rules

Two rules, and the difference between them is the whole safety
argument:

- **A missing tenant reference means the default tenant.** That is the
  migration of 1.5 and the reading rule for any record written before
  this version.
- **An unknown tenant reference never means the default tenant.** A
  record naming a UUID this node does not have is *not* healed, *not*
  reassigned, and *not* ignored. It is refused and reported (3.2).
  Silently mapping an unknown tenant onto `default` would move a
  customer's users or instances into the operator's own tenant — a data
  leak dressed as robustness.

### 2.3 Effect on other capabilities in this version

None that a user can observe. `oaap.core.identity`, `oaap.core.portal`,
`oaap.apps.runtime` and `oaap.data.backup` gain the field and the
migration; no screen, no command output, no hostname and no API
response changes while one tenant exists. That is the acceptance
criterion, not a side note.

## 3. Security requirements

1. **The boundary is enforced at the gateway and in the platform, never
   in apps** (RFC-0022). An app filtering by tenant itself is one bug
   away from a leak between customers.
2. **Fail closed on an unknown tenant** (2.2). The refusal is louder
   than the failure it prevents.
3. **A tenant reference is not a secret, a tenant's contents are.**
   `oaap tenant show` prints counts; nothing in this capability prints
   another tenant's usernames, instance names or configuration values.
4. **Labels are public** and will appear in hostnames from 0.2 onward,
   therefore in Certificate Transparency logs. An operator hosting a
   customer under confidentiality chooses an opaque label. The platform
   must say this at the moment a label is chosen, not in a document.
5. **No privilege is created by this version.** Nothing here grants or
   removes an authority; the role half is 0.2.

## 4. Conformance tests

1. **Invisible by construction.** On a node with exactly one tenant,
   the output of the portal pages, `oaap app list`, `oaap user list`
   and every other pre-0.1 command is byte-identical to the same node
   before the tenant store existed.
2. **Migration is complete.** After migrating a node that had users,
   instances, tokens and permits, `oaap tenant check` exits 0 and every
   record resolves to the default tenant.
3. **Migration is idempotent.** Running it twice creates one tenant,
   not two, and prints nothing the second time.
4. **Absent means default.** A record written without a tenant field
   resolves to the default tenant.
5. **Unknown never means default.** A record naming an unknown UUID is
   refused, is reported by `oaap tenant check` with a non-zero exit,
   and is not rewritten by the check.
6. **The default id is per node.** Two independently installed nodes
   have different default tenant UUIDs.
7. **The node is not in a tenant.** Node profiles, external hostname,
   edge configuration, store sources and fleet keys carry no tenant
   reference and are unaffected by the migration.

## 5. Dependencies

`oaap.core.identity` (user records), `oaap.apps.runtime` (instance
registry, deploy tokens, creation permits), `oaap.core.portal`
(surfaces), `oaap.data.backup` (per-tenant backup, D7).

## Zusammenfassung auf Deutsch

Ein **Mandant** ist die Grenze des Zusammengehörens, ein **Account** die
Grenze der Verantwortung. Diese Fassung setzt aus RFC-0022 genau
**Stufe 2** um — und die ist mit Absicht für niemanden sichtbar:

> **Jeder Datensatz, der jemandem gehört, trägt einen Mandanten.
> Solange ein Knoten genau einen Mandanten hat, erwähnt ihn keine
> Oberfläche.**

Warum jetzt, bevor es gebraucht wird: Eine ungenutzte Dimension
mitzuführen kostet eine Spalte, sie später nachzurüsten kostet ein
Wochenende — und dieses Wochenende fiele genau auf den Tag, an dem ein
zweiter Kunde wartet.

**Was einen Mandanten trägt:** Benutzer, App-Instanzen,
Anlege-Erlaubnisse, Sicherungen — und zwar **gespeichert**. Ein
**Deploy-Token** trägt keinen: Es hängt an genau einer Instanz, und die
weiß es schon. Ein zweimal gespeicherter Mandantenbezug ist einer, der
sich selbst widersprechen kann, und am Tag des Widerspruchs entscheidet
die falsche Kopie, wer in wessen Instanz schreiben darf. Also: **ableiten,
wo es schon jemand weiß; speichern nur dort, wo es niemand weiß.** Die
Anlege-Erlaubnis ist genau diese eine Stelle — sie wird ausgestellt,
bevor die Instanz existiert — und deshalb auch die Stelle, an der der
Mensch den Mandanten bewusst wählt. **Was bewusst keinen trägt:**
Knotendinge (Profile, externer Name, Edge, Store-Quellen, Updates) und
die Flotten-Auskunft samt Schlüssel — die beantwortet die Frage „wie
geht es diesem *Knoten*" und gehört dem Betreiber. Und vor allem: **das
App-Manifest**. Keine App erfährt je, dass sie in einem Mandanten
lebt; müsste sie es wissen, läge die Grenze falsch, und jede App würde
ein Multi-Tenancy-Projekt.

**Intern zählt nur die UUID**, nie das Kürzel und nie der Klarname.
Genau deshalb ist ein späterer Kürzelwechsel eine Umbenennung und keine
Migration. Der Standard-Mandant heißt `default` und bekommt **je Knoten
eine eigene UUID** — zwei Knoten haben zwei verschiedene
Standard-Mandanten, und eine gemeinsame Kennung lüde zu genau der
Verschmelzung ein, die RFC-0022 ausschließt. Der **Account ist auf dem
Knoten nur eine Referenz** (UUID plus zwischengespeicherter Name), kein
eigenes Verzeichnis — so entsteht kein Schreibweg zwischen Knoten
(RFC-0022 Q1).

**Die zwei Leseregeln, und ihr Unterschied ist das ganze
Sicherheitsargument:** Ein **fehlender** Mandantenbezug bedeutet
Standard-Mandant — das ist die Migration alter Datensätze. Ein
**unbekannter** Mandantenbezug bedeutet **niemals** Standard-Mandant,
sondern wird abgelehnt und gemeldet. Einen unbekannten Mandanten still
auf `default` abzubilden verschöbe Benutzer oder Instanzen eines Kunden
in den Mandanten des Betreibers — ein Datenleck im Gewand der
Robustheit.

**Anlegen, Umbenennen und Löschen von Mandanten kommt in 0.2**, zusammen
mit `tenant_admin`, dem Audit-Log und den Kürzeln in den Hostnamen. Ein
zweiter Mandant, den niemand verwalten kann, wäre schlechter als
keiner.

**Die Abnahmebedingung ist die Unsichtbarkeit selbst:** Auf einem
Knoten mit einem Mandanten muss jede Ausgabe zeichengleich zu der von
vorher sein.
