# oaap.core.tenant — Account and Tenant, the Boundary of Belonging

- **ID:** `oaap.core.tenant`
- **Version:** 0.2.2 (adds 1.4: data left behind by a removed instance
  belongs to the tenant it was written for, and no other tenant may take
  it over -- instance names are unique per node, so a name one customer
  gives up can be taken by the next, and until now the data would have
  travelled with the name;
  0.2.1 added rule 4 of 2.3: a `tenant_admin` may not grant
  an instance a port that bypasses the gateway, not even on their own
  instance -- found 2026-09-02, where the portal's own comment said
  "server_admin only" and the code admitted a tenant administrator;
  0.2 was RFC-0022 stage 3: the second tenant, `tenant_admin`,
  labels in names, and the audit log that makes the arrangement
  trustworthy)
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

Version 0.1 built the dimension and hid it. Version 0.2 makes it real:

> **A node may hold more than one tenant. A tenant administers itself,
> its instances answer under its own name, and every action that
> touches it is written down — including the operator's.**

The invisibility of 0.1 survives as a rule, not as an implementation:
**on a node with exactly one tenant, nothing in 0.2 is visible either.**
The second tenant is what switches the whole capability on.

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

| Field           | Rules                                                                       |
| --------------- | --------------------------------------------------------------------------- |
| `id`            | UUIDv4, assigned once, **immutable**, never displayed                       |
| `label`         | `[a-z0-9][a-z0-9-]{0,30}`, unique per node, editable (1.6); `default` on a single-tenant node |
| `name`          | free text for humans, e.g. "Kunde Meier GmbH"                               |
| `account`       | opaque account reference (UUID) — see 1.3                                   |
| `account_name`  | cached display text for the account; never authoritative                    |
| `created`       | ISO-8601 timestamp                                                          |
| `former_labels` | previous labels kept as aliases, each with an expiry — see 1.6              |

**Everything internal refers to `id`.** Not to the label, and never to
the name. This is what makes a label change a renaming instead of a
migration (RFC-0022 D4) — and label changes happen, because a label
ends up in hostnames and hostnames end up in public Certificate
Transparency logs.

### 1.2 The default tenant

Every installation has one from the first minute: label `default`, name
empty, created by the installer or by the migration of 1.5. Its `id` is
a **freshly generated UUID per node**, not a well-known constant — two
nodes' default tenants are different tenants, and giving them the same
identifier would invite exactly the merge that RFC-0022 D1 forbids.

The default tenant is **the operator's own**. It cannot be renamed and
cannot be deleted: its label is the absence of a label in every
hostname (2.4), so renaming it would move every existing address on the
node at once.

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
| audit entry (1.7)                       | stored            | an entry is filed in the tenant it concerns |
| an instance's data directory            | **stored**        | it outlives the instance, so there is nothing left to derive from |

The distinction is worth the extra column. A tenant reference stored in
two places is a tenant reference that can disagree with itself, and the
day it does, the wrong copy decides who may write into whose instance.
So: **derive wherever something already knows the answer, store only
where nothing does.** The creation permit is one of the two places
where nothing does — which also makes it the place where the tenant
must be chosen deliberately, by the human issuing it.

The other is an instance's **data directory**, and the reason is worth
stating because it is not obvious. Removing an instance keeps its
storage and its configured secrets unless deletion is asked for
explicitly: reinstalling under the same name is how an operator repairs
an app without losing its data, and losing it by default would be the
worse mistake. But instance names are unique per *node* (2.4), so a name
one tenant gives up can be taken by the next — and the data would
travel with the name. Therefore:

> **Data left behind belongs to the tenant it was written for, and no
> other tenant may take it over.** An install into a different tenant
> than the retained data belonged to is refused; the refusal names the
> way out and does *not* name the other tenant (2.4). Deleting the
> retained data is an operator act and is written to the audit log of
> the tenant it belonged to (1.7).

Retained data with **no** tenant recorded (written before this rule
existed) is treated as belonging to nobody: harmless on a node with one
tenant, where there is nothing to cross, and refused on a node with
several, where it is no longer decidable. Nodes stamp what they can on
update, so only directories whose instance was already gone stay
anonymous.

Does **not** carry a tenant, on purpose:

- **Node-level facts** — profiles, external hostname, edge routing,
  store sources, the update channel. They belong to the operator.
- **Fleet keys and the fleet status document** (`oaap.fleet.status`).
  A fleet key answers "what is the state of this *node*". Scoping it to
  a tenant would either shrink it into uselessness or pretend an
  isolation it does not have. The fleet document may name tenant
  *labels* as facts; the key stays the operator's.
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

### 1.6 A label may change, and it is an address change

RFC-0022 Q3: a changed label keeps working for a grace period. The old
label is recorded in `former_labels` with an expiry, and for as long as
it has not expired, every hostname derived from it is served exactly
like the new one — same instance, same protection. This reuses the
alias machinery RFC-0018 already gave instances rather than inventing a
second one.

A rename therefore has to say what it costs, in the same voice instance
address removal already uses: **every address of the tenant's instances
changes, certificates for the new names are issued on first contact,
and anything that hard-coded an old address keeps working only until
the grace period ends.** The platform has paid for a silent address
change once already (`hub.bdt.joomp.de`, 2026-08-23); it does not do
that twice.

Expired former labels are removed the next time labels are written out.
The default tenant's label never changes (1.2).

### 1.7 The audit log

RFC-0022 §6, and it is load-bearing, not an accessory: because
`server_admin` may do everything (D5), the record of what they did is
the only thing a customer's trust can rest on. Pretending there is a
technical barrier in front of the operator would be dishonest.

One entry per **state change**, never per read:

| Field     | Meaning                                                          |
| --------- | ---------------------------------------------------------------- |
| `when`    | ISO-8601 UTC                                                     |
| `who`     | the acting username, or `root` for an action taken at the machine |
| `role`    | the authority the action was taken under (`server_admin`, `tenant_admin`, `root`) |
| `action`  | short verb, e.g. `tenant.create`, `user.create`, `instance.install`, `permit.issue` |
| `tenant`  | the tenant `id` the entry is filed in                            |
| `subject` | what was acted on (a username, an instance name, a label)        |
| `result`  | `ok` or `denied`, plus a short reason when denied                |

Recorded at minimum: creating and renaming tenants; creating, changing
and deactivating users; appointing and removing administrators;
installing and removing instances; issuing and revoking deploy tokens
and creation permits.

**An action of a `server_admin` against a tenant is filed in that
tenant's log**, not in a separate operator log. The customer must be
able to see it. A `tenant_admin` reads their own tenant's entries; a
`server_admin` reads all of them.

The log is **append-only** and is never rewritten by the platform. It
is not a security boundary by itself — someone with root on the machine
can edit any file — it is a record, and its value is that it exists and
is shown.

## 2. Interface

### 2.1 Reading

- `oaap tenant list` — the tenants of this node. On a single-tenant
  node it prints the default tenant and one sentence saying that
  tenants are not in use here.
- `oaap tenant show [<label>]` — one tenant with its counts (users,
  instances). Counts, not names: this command is an inventory, not a
  data export.
- `oaap tenant check` — the integrity check of 3.2. Exit code 0 when
  every record resolves, 1 when any does not — and **1 also when a
  store it must check could not be read at all**. "Everything resolves"
  is a claim about records that were looked at; a check that silently
  counts an unreadable store as empty makes that claim about nothing.
- `oaap tenant log [<label>] [-n <count>]` — the audit log (1.7), newest
  last.

### 2.2 Writing

- `oaap tenant create <label> [--name <text>] [--account <uuid>]
  [--account-name <text>]` — creates a tenant. Before it does, it
  **checks the zone** (2.4) and **says that the label will be public**
  (3.4). Both at the moment of choosing, not in a document.
- `oaap tenant rename <label> <new-label> [--grace-days <n>]` — renames
  a tenant, keeps the old label as an alias for the grace period (1.6),
  and names the consequences before doing it.

Deleting a tenant is **not** in this version. A tenant holds users,
instances and their data; deleting it is an export-then-destroy
operation and gets its own round (RFC-0022 security note: a tenant
export is a customer's complete data set in one file).

Creating the first `tenant_admin` of a new tenant is user
administration, not tenant administration: the node operator does it
where users are made (2.3).

### 2.3 Roles

`tenant_admin` is the half RFC-0008 left open. It is an assignable role
like any other, and it means: **administer my own tenant, nothing
else.**

| | `server_admin` | `tenant_admin` |
| --- | --- | --- |
| Node updates, profiles, certificates, store sources | ✔ | ✘ |
| Grant an instance a port that bypasses the gateway (RFC-0015) | ✔ | ✘ |
| Create tenants, appoint the first tenant admin | ✔ | ✘ |
| Users and roles **of their own tenant** | ✔ | ✔ |
| Install and remove app instances **of their own tenant** | ✔ | ✔ |
| Deploy tokens and creation permits **of their own tenant** | ✔ | ✔ |
| Read the audit log **of their own tenant** | ✔ | ✔ |
| See another tenant at all | ✔ | ✘ |

Three rules make the second column safe:

1. **A `tenant_admin` may never grant a role whose authority reaches
   past a tenant** — `server_admin` (the node) and `partner` (the
   health surface, which names every instance on the machine) — and may
   never grant `tenant_admin` outside their own tenant. Otherwise the
   role is a two-step path out of its own boundary: create an account,
   give it more reach than you have, sign in as it.
2. **A `tenant_admin` never changes a user of another tenant** — not
   their roles, not their password, not their active flag. A request
   naming such a user answers exactly as it would for a user that does
   not exist (4.8): revealing that a name is taken elsewhere on the node
   is already a leak across the boundary.
3. **A `tenant_admin` acts only in their own tenant**, and the tenant
   is taken from *their own record*, never from the request. A tenant
   supplied by a caller is a tenant a caller has chosen.
4. **A `tenant_admin` may not reach past the gateway.** Granting an
   instance a non-HTTP port (RFC-0015) is refused for them even on
   their **own** instance: such a port is a resource of the host, and
   traffic through it never passes the gateway that enforces the
   boundary in the first place. It is the same line that kept the
   `exposed` node profile on the machine (RFC-0011). The refusal is
   re-checked on the host, not only in the portal.

`server_admin` may do everything (RFC-0022 D5). The counterweight is
1.7, not a restriction. The operating rule that follows — in a
multi-tenant environment `server_admin` is not a working account — is a
rule for humans, and the audit log is what makes it checkable.

### 2.4 Names

An instance of the default tenant keeps the address it has:
`<instance>.<node>` (RFC-0018). An instance of any other tenant answers
under `<instance>.<label>.<node>`, plus one such name per unexpired
former label (1.6).

A two-level name below the node's own name is **a property of the zone,
not of DNS** — a DNS wildcard matches exactly one label, so
`*.example.org` does not cover `a.b.example.org`. The node therefore
**measures** it (it already runs a DNS watchdog) and reports the result
*before* a tenant is created, not after its apps are unreachable. A
failed or impossible check is a warning, not a refusal: a node without
an external hostname has no zone to check, and an operator may be about
to fix their DNS.

Per-instance own hostnames (RFC-0009/RFC-0018) are unaffected: they are
chosen in full and carry no tenant label.

**Instance names stay unique per node**, not per tenant. That is one
fact the boundary cannot hide: a name already taken elsewhere has to be
refused, or the refusal arrives later and less comprehensibly. The
refusal therefore says that the name is taken and **not whose it is** —
the collision is the fact, the owner is not.

### 2.5 Resolution rules

Two rules, and the difference between them is the whole safety
argument:

- **A missing tenant reference means the default tenant.** That is the
  migration of 1.5 and the reading rule for any record written before
  0.1.
- **An unknown tenant reference never means the default tenant.** A
  record naming a UUID this node does not have is *not* healed, *not*
  reassigned, and *not* ignored. It is refused and reported (3.2).
  Silently mapping an unknown tenant onto `default` would move a
  customer's users or instances into the operator's own tenant — a data
  leak dressed as robustness.

### 2.6 Effect on other capabilities

On a node with one tenant: none that anyone can observe, exactly as in
0.1. From the second tenant onward:

- `oaap.core.identity` gains the `tenant_admin` role, a tenant on every
  user record, and the boundary check of 3.1.
- `oaap.core.portal` shows the caller their own tenant only, unless
  they hold `server_admin`.
- `oaap.apps.runtime` derives an instance's hostnames from its tenant's
  label (2.4) and scopes creation permits to a tenant.
- `oaap.fleet.status` may name tenant labels as facts; it stays the
  operator's document.

## 3. Security requirements

1. **The boundary is enforced at the gateway and in the platform, never
   in apps** (RFC-0022). Concretely: the gateway's authorization call
   for an instance carries that instance's tenant, and a session whose
   user belongs to a different tenant is refused there — before the app
   is reached. An app filtering by tenant itself is one bug away from a
   leak between customers.
2. **Fail closed on an unknown tenant** (2.5). The refusal is louder
   than the failure it prevents.
3. **A tenant reference is not a secret, a tenant's contents are.**
   Nothing in this capability shows one tenant another's usernames,
   instance names, audit entries or configuration values.
4. **Labels are public.** They appear in hostnames and therefore in
   Certificate Transparency logs. An operator hosting a customer under
   confidentiality chooses an opaque label. **The platform says this at
   the moment a label is chosen** (2.2), not in a document.
5. **A `tenant_admin` cannot escalate** (2.3 rules 1–3). This is the
   one new privilege in this version, and it is bounded by construction:
   the acting tenant comes from the actor's own record.
6. **Public routes stay public.** A route an app declares public
   (RFC-0002) is not tenant-scoped — there is no session to scope. The
   boundary applies to authenticated access, which is what it is for.
7. **The audit log records the operator too** (1.7). An action taken by
   a `server_admin` inside a tenant is filed in that tenant's log.
8. **A name may be reused; the data behind it may not** (1.4). Instance
   names become free again when an instance is removed, while its
   storage and configured secrets are deliberately kept. An install
   into a different tenant than the retained data belonged to is
   refused, and deleting that data is an operator act recorded in the
   audit log of the tenant it belonged to.

## 4. Conformance tests

1. **Invisible while single.** On a node with exactly one tenant, the
   output of the portal pages, `oaap app list`, `oaap user list` and
   every other command is byte-identical to the same node before the
   tenant store existed.
2. **Migration is complete and idempotent.** After migrating, `oaap
   tenant check` exits 0, every record resolves to the default tenant,
   and running the migration again creates nothing and prints nothing.
3. **Absent means default; unknown never does.** A record without a
   tenant field resolves to the default tenant; a record naming an
   unknown UUID is reported by `oaap tenant check` with a non-zero exit
   and is not rewritten by it.
3a. **An unreadable store fails the check.** With the user store present
    but unreadable, `oaap tenant check` exits non-zero and says so,
    rather than reporting that every record resolves. A store that is
    not there at all is an honest zero and passes.
4. **The default id is per node**, and the default tenant can be
   neither renamed nor deleted.
5. **The node is not in a tenant.** Node profiles, external hostname,
   edge configuration, store sources and fleet keys carry no tenant
   reference.
6. **The gateway refuses across the boundary.** A session belonging to
   tenant A receives 403 on an instance of tenant B, and the app is not
   reached. A `server_admin` is not refused (D5). A public route of the
   same instance is unaffected.
7. **Names follow the label.** An instance of a non-default tenant is
   served under `<instance>.<label>.<node>`; an instance of the default
   tenant is served under `<instance>.<node>` and nothing else. After a
   rename, both the new and the old label serve until the grace period
   ends.
8. **A `tenant_admin` is bounded.** They cannot list, read or change a
   user or an instance of another tenant; a request naming one is
   answered as if it did not exist. They cannot grant `server_admin`
   or `partner`. They cannot create a user in another tenant even by
   naming one in the request.
9. **The audit log records both sides.** A `server_admin` action inside
   a tenant appears in that tenant's log; a `tenant_admin` reading the
   log sees their own tenant's entries and no others.
10. **A rename warns before it acts**, names the address change, and
    keeps the old label serving for the grace period.

11. **Retained data does not change hands.** With two tenants: an
    instance of tenant A is removed without deleting its data; an
    install of the same name into tenant B is refused, and the refusal
    names neither A nor its label. The same install into A succeeds and
    keeps the data. After the operator deletes the retained data the
    name is free for B, and the deletion appears in **A's** audit log.
    On a node with one tenant, none of this is observable.

12. **No port past the gateway for a tenant.** On an `exposed` node, a
    `tenant_admin` asking for a declared non-HTTP endpoint of their own
    instance is refused with a message naming the reason, and the host
    refuses the same request when it arrives through the queue with the
    portal check bypassed. A `server_admin` gets it.

## 5. Dependencies

`oaap.core.identity` (user records, roles, the authorization call),
`oaap.apps.runtime` (instance registry, hostnames, deploy tokens,
creation permits), `oaap.core.portal` (surfaces), `oaap.data.backup`
(per-tenant backup, D7).

## Zusammenfassung auf Deutsch

Ein **Mandant** ist die Grenze des Zusammengehörens, ein **Account** die
Grenze der Verantwortung. Fassung 0.1 hat die Dimension gebaut und
versteckt. **Fassung 0.2 macht sie echt:**

> **Ein Knoten darf mehr als einen Mandanten halten. Ein Mandant
> verwaltet sich selbst, seine Instanzen antworten unter seinem eigenen
> Namen, und jede Handlung an ihm wird aufgeschrieben — auch die des
> Betreibers.**

Die Unsichtbarkeit von 0.1 bleibt als Regel: **Auf einem Knoten mit
genau einem Mandanten ist auch von 0.2 nichts zu sehen.** Erst der
zweite Mandant schaltet die Fähigkeit ein.

**Neu ist die Rolle `tenant_admin`** — die Hälfte, die RFC-0008 offen
gelassen hat. Sie bedeutet: *meinen* Mandanten verwalten, sonst nichts.
Benutzer, Instanzen, Token und Anlege-Erlaubnisse des eigenen
Mandanten, das eigene Audit-Log. Drei Regeln machen das sicher: Ein
`tenant_admin` darf **niemals `server_admin` vergeben** (sonst wäre die
Rolle ein Zweischritt zum ganzen Knoten), er **fasst keinen Benutzer
eines anderen Mandanten an** — eine Anfrage nach so einem Benutzer wird
beantwortet, als gäbe es ihn nicht, denn schon die Auskunft „diesen
Namen gibt es" wäre ein Leck über die Grenze — und **der Mandant, in
dem er handelt, kommt aus seinem eigenen Datensatz, nie aus der
Anfrage.** Ein vom Aufrufer mitgeschickter Mandant ist ein vom Aufrufer
gewählter Mandant.

**Die Grenze wird am Gateway durchgesetzt, nicht in der App.** Der
Autorisierungsaufruf trägt den Mandanten der Instanz; eine Sitzung aus
einem anderen Mandanten wird dort abgelehnt, bevor die App erreicht
ist. Eine App, die selbst nach Mandant filtert, ist einen Fehler weit
von einem Leck zwischen Kunden entfernt. Öffentliche Routen bleiben
öffentlich — dort gibt es keine Sitzung, die man einordnen könnte.

**Namen:** Instanzen des Standard-Mandanten behalten
`<instanz>.<knoten>`. Jeder andere Mandant bekommt
`<instanz>.<kürzel>.<knoten>`. Ob ein zweistufiger Name überhaupt
auflöst, ist **eine Eigenschaft der Zone, nicht von DNS** — ein
Platzhalter deckt genau eine Stufe ab. Der Knoten **misst** das und
sagt das Ergebnis, **bevor** ein Mandant angelegt wird, nicht wenn
dessen Apps unerreichbar sind. Und weil ein Kürzel im öffentlichen
Certificate-Transparency-Log landet, sagt die Plattform beim Anlegen,
dass es öffentlich wird — im Moment der Wahl, nicht in einem Dokument.
Ein **Kürzel darf sich später ändern**; das alte gilt eine Schonfrist
lang weiter (RFC-0018-Mechanik), und die Umbenennung nennt vorher, was
sie kostet: alle Adressen ändern sich. Diese Plattform hat eine
stillschweigende Adressänderung schon einmal bezahlt.

**Das Audit-Log ist tragend, kein Zubehör.** Weil `server_admin` alles
darf (RFC-0022 D5), ruht das Vertrauen des Kunden allein darauf, dass
sichtbar ist, was getan wurde. Eine Handlung des Betreibers **in** einem
Mandanten steht **in dessen Log**, nicht in einem separaten
Betreiber-Log — der Kunde muss sie sehen können. Aufgeschrieben wird der
Zustandswechsel, nie das Lesen: wer, wann, was, in welchem Mandanten,
mit welchem Ergebnis.

**Löschen eines Mandanten ist bewusst nicht dabei.** Ein Mandant hält
Benutzer, Instanzen und deren Daten; ihn zu löschen ist ein
Exportieren-dann-Vernichten und bekommt eine eigene Runde.
