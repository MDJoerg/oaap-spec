# oaap.core.tenant — Account and Tenant, the Boundary of Belonging

- **ID:** `oaap.core.tenant`
- **Version:** 0.9 (RFC-0041 K7 — **the switches inside that space, and the truth about them**; 0.8 — the platform may MAKE that provider, not only name it; 0.7 — a tenant may name who lets people
  in**: an OIDC provider object that is a URL and says nothing about
  where the server runs, plus a policy for what a first login through
  it BECOMES. The binding is a platform rule and is not configurable:
  `(provider, subject, tenant)` and nothing else, never an e-mail
  address and never a name. The consequence is the tenant's, because
  there are real cases for all three — but only the OPERATOR may move
  that switch, on a machine that carries other customers. The client
  secret is not in this record: this file is world-readable and travels
  in a tenant archive. See 2.8, conformance tests 20 and 21;
  RFC-0041 K1/K2/K4/K4b/K5/K7)
- **Previous version:** 0.6 (RFC-0042 T3 — **the tenant has a face**: a public
  title, two colours and a logo, and nothing else. Not a stylesheet: a
  tenant that can ship CSS can move, hide or fake any control on a page
  the platform answers for. The title is a SECOND name field on purpose
  — the `name` of 1.1 is the Klarname and stays in the house, while a
  login page needs no login. The logo is content in `oaap.data.files`,
  projected where the gateway can serve it without a session. Two rules
  it may not break: node-wide power keeps the platform's own chrome, and
  the tenant's ADDRESS stands beside its face on every page, because the
  address cannot be chosen freely and a title can. See 2.7, conformance
  tests 18 and 19;
  0.5 RFC-0042 T1/T2 — **the tenant is a place**: it
  answers at `<label>.<node>`, the slot the naming scheme described and
  never filled. The platform's own launchpad answers there, scoped to
  that tenant for everyone who arrives through that host, a
  `server_admin` included; a host naming a tenant this node does not
  have serves nothing, on every page. And the guard that had to come
  first: a tenant label and a default-tenant instance name are ONE
  namespace, refused in both directions, in the same words either kind
  of collision already produced. See 2.4, conformance tests 16 and 17;
  0.4.2 was four audit entries for instance diagnostics —
  `diagnose.opened`/`closed`/`expired` and `instance.restarted`, 1.7,
  RFC-0038 D2/D4: the first entries in this log for an act of READING,
  because a diagnosis window hands somebody the app's own output;
  0.4.1 the portal may create a tenant, `server_admin`
  only — the same act as `oaap tenant create` through a second door,
  with the one named exception to the invisibility rule that this
  requires, see 2.2 and conformance test 1a;
  0.4 was RFC-0026: an instance gets an identity, its data
  lives at `tenants/<tenant-id>/instances/<instance-id>/`, and both a
  tenant and an instance can be renamed with the addresses following.
  The frozen short name of 0.3 is withdrawn: identifiers follow the
  current label again, because the data no longer hangs off a name;
  0.3 was RFC-0025: an instance name belongs to a TENANT, not
  to the node. Everything node-scoped uses a key composed once from the
  tenant's frozen short name; the address keeps carrying the name the
  customer chose. The migration renames nothing, and a node with one
  tenant cannot tell that anything changed;
  0.2.2 added 1.4: data left behind by a removed instance
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
| `theme`         | the tenant's face (0.6): `title`, `color_primary`, `color_accent`, `logo`, `logo_type` — see 2.7. Absent means the platform's own look |
| `idp`           | who lets people in (0.7): `kind`, `issuer`, `client_id`, `version`, `label` — see 2.8. Absent means local accounts only. **Never the client secret**. Made by a connector (0.8): `connector`, `space`, and `version_how` — whether that version was read from the server or stated by a human |
| `idp_policy`    | what a first login through that provider becomes (0.7): `first_login`, `default_role`, `group_map`, `self_registration`, `reason`. Absent means `eingang`. Extended in 0.9 by `second_factor` (`off`/`required`) and by `realm` — what the provider's space last ANSWERED about those two switches, with the time it was read (§2.10) |


**Everything internal refers to `id`.** Not to the label, and never to
the name. This is what makes a label change a renaming instead of a
migration (RFC-0022 D4) — and label changes happen, because a label
ends up in hostnames and hostnames end up in public Certificate
Transparency logs.

Instance **data** refers to `id` too, and to the instance's own id
(`oaap.apps.runtime`): it lives at
`tenants/<tenant-id>/instances/<instance-id>/`. That is what makes a
rename a rename rather than a data migration, and it is why 0.3's
frozen short name could be withdrawn — it existed only to keep names
out of paths, and now identities do that job (RFC-0026 §3.2).

Readable **symlinks** lie beside the identities:
`tenants/by-label/<label>` and `tenants/<id>/by-name/<name>`. They are a
convenience for whoever has to read a path at two in the morning, never
something the platform depends on: a filesystem that refuses them
changes nothing about how the node runs.

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

**And one read (RFC-0038 D2), which is the exception that proves the
rule.** A diagnosis window hands somebody the app's own log — content
the platform neither wrote nor can filter. So the *act of reading* is
recorded, although nothing changed:

| `action`             | filed when                                        |
| -------------------- | ------------------------------------------------- |
| `diagnose.opened`    | a window is opened; `detail` carries its duration |
| `diagnose.closed`    | somebody closes it before its time                |
| `diagnose.expired`   | its time ran out and the platform closed it       |
| `instance.restarted` | an instance's containers were recreated (D4)      |

**And one entry that carries more than its verb (RFC-0037):**
`instance.sideload`, filed when an **uploaded** package is installed
into a production instance — from the portal or from the machine. Its
`detail` MUST name whether the instance was created or updated, the
version, the package's checksum, and **in full** the envelope widenings
that were confirmed. This is the one act where the platform cannot
vouch for the origin of the code (packages are unsigned, RFC-0019), so
the record of who accepted which bytes is what takes the place of that
proof — and it is the customer's record, in the customer's log.

**Never the contents.** The entry says who opened a window on which
instance for how long — it is not a copy of what they saw. The same
reasoning as `instance.export`: that the operator could also take the
log by ssh is a reason this record cannot be complete, not a reason to
leave out the line that can be written.

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

  **The portal may create a tenant too** (0.4.1), on the tenant page,
  for a `server_admin` and nobody else. It is the same act through a
  second door and MUST produce the same record, run the same label
  rules, say the same two sentences before the act, and file the same
  audit entry — a difference between the doors is a difference in what
  a tenant *is*.

  Why this one may leave the machine while a node profile (RFC-0011)
  may not: a new tenant is **empty**. No user, no instance, no permit,
  no address — a reserved word and a place to put things. What it is
  not is reversible (there is no removal, see below), which is why it
  stays `server_admin`'s alone. A `tenant_admin` who could create a
  tenant could create one and appoint themselves in it: a two-step
  path out of their own boundary (2.3 rule 1).
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
   past a tenant** — `server_admin` (the node) and `support` (the
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

**The tenant itself answers at `<label>.<node>`** (0.5, RFC-0042 T1/T2).
That slot was described by the scheme above and never filled: instances
have always been `<instance>.<label>.<node>`, so the level between them
and the node was empty. It is not an addition to the scheme; it is the
part of it that was missing. The default tenant contributes none — its
label is the absence of a label, so its place IS the node's own address.
Each unexpired former label answers too, for the reason 1.6 already
gives.

What answers there MUST be the platform's own launchpad, scoped to that
tenant — not a second application. A second one would have to re-acquire
the launchpad, the role filter, the visibility-group filter, the tenant
boundary and the session, and a rule that lives in two places eventually
disagrees with itself.

Two requirements come with it, and they are the substance:

- **The host scopes, and it scopes everyone.** A caller reached through
  `<label>.<node>` sees that tenant's apps and no others, a
  `server_admin` included. The node-wide view is one hostname away; a
  page that answers a wider question than the address asked is how an
  operator mistakes whose screen they are looking at.
- **A host naming a tenant this node does not have serves nothing.** Not
  the operator's view, not an empty page that looks like a working one.
  This is 2.5's second rule applied to an address, and it fails closed
  for the same reason.

**A tenant label and a default-tenant instance name are one namespace.**
Both occupy `<x>.<node>`. Creating or renaming either MUST be refused
when the other holds the name, in both directions, with unexpired
former labels and former instance names counting as held. The refusal
says that the name is taken, never by whom — and never which kind of
thing holds it, or the guard would leak what it exists to protect.

**An instance name belongs to a tenant** (RFC-0025). Two customers may
both call an instance `viewer`; what keeps their containers, networks,
directories, deploy tokens and hook addresses apart is a **key**,
composed once and never recomputed:

    key = <slug>-<name>      in a tenant
    key = <name>             in the default tenant

The **slug** is the tenant's **current** label. RFC-0025 froze it so a
rename would not have to move data; RFC-0026 moved the data under an
identity instead (1.1), and once it hangs off an id rather than a name,
freezing bought nothing but drift between what a container is called
and who owns it. So identifiers follow the label again — and a
tenant rename therefore **re-keys that tenant's instances and restarts
them**. That trade is named before it is made, in the rename dialog:
seconds of downtime for an act that is rare, deliberate and warned,
against no drift at all. Nothing moves on disk.

The default tenant's slug is the **empty string**, exactly as its label
is the absence of a label in a hostname (1.2). Everything on a
single-tenant node therefore keeps the key, address and deploy URL it
already had, with no compatibility layer to maintain.

Two things must be free before an instance is created, and checking
only the first is a bug: the **key** on the node, and the **name**
within the tenant. They are not the same question for an instance that
predates this rule, whose key carries no slug. A refusal says that the
name is taken and **not whose it is** — the collision is the fact, the
owner is not.

The address is built from the **name**, never from the key: an instance
keyed `cls-viewer` answers at `viewer.cls.<node>`. The key exists so
identifiers do not collide; the address does not need it, because the
label already says which tenant this is.

**Both names may change** (RFC-0026). A tenant label and an instance
name are renameable, and the addresses follow. What that costs is one
restart of the affected apps; what it does not cost is a data move.
Each rename keeps the previous spelling answering for a grace period
— the address **and** the deploy address — because a name that was
published is a name somebody wrote down. The deploy address also
accepts the instance's **identity**, which never changes at all: an
agent given that form need never be told about a rename.

### 2.7 The face of a tenant (0.6, RFC-0042 T3)

A tenant MAY choose how its place looks. What it may choose is a closed
set, and the closedness is the requirement:

| Field | Meaning |
| --- | --- |
| `title` | the tenant's **public** name, shown in the header and the tab |
| `color_primary` | the colour that carries the brand |
| `color_accent` | the second colour, for states and emphasis |
| `logo` | a picture, stored as content (`oaap.data.files`) |

**No stylesheet, no custom fonts, no per-tenant templates.** A tenant
that can ship CSS can move, hide or fake any control on a page the
platform is responsible for. Four values cannot. An implementation MUST
therefore turn these into *values* — a set of variable assignments and
nothing else — and MUST refuse a colour that is not a plain six-digit
hex value, because a value that can carry a semicolon is not a value.

**`title` is not `name`.** They are two fields on purpose. The `name` of
1.1 is the Klarname, asked for on a page that promises it stays inside
the house; the title appears on the login page, which by definition
requires no login. An implementation MUST NOT use `name` as a fallback
for a missing title. It falls back to the **label**, which is public by
construction — it is in the hostname and therefore in the certificate
transparency log (3.4).

**The logo is content, and it becomes public.** It MUST be stored
through `oaap.data.files`, addressed by its hash, under the tenant that
owns it — so it is in the node backup, in the tenant archive and in the
rehearsal, and so one tenant's picture is not addressable from
another's. Serving it is a different question: a login page has no
session, so the bytes MUST also be reachable on a route that needs
none. An implementation that copies them to such a place MUST treat
that copy as **derived** — rebuilt from the store after an update, a
rename and a restore, and never the thing an archive carries. Putting a
picture on a page anyone can open makes it public; a copy in a public
directory says so, rather than implying it.

**Removing a logo removes the reference, not the bytes.** The byte
layer has no delete in `oaap.data.files` 0.1, deliberately — content is
removed because a *document* may be removed, and that is
`oaap.data.documents`. So clearing a logo MUST drop the reference and
the served copy, and the content stays in the tenant's store until that
capability exists. An implementation MUST NOT pretend otherwise: a
tenant told their picture is gone, whose bytes are still on the node,
has been told something false.

**The type is decided by the content, never by the file name**, and an
implementation MUST refuse SVG. The picture is served from the
platform's own origin, and an image that can carry script sits there
beside every user's session. This is not a judgement about the operator
who uploads it; it is about what the file becomes once it is a URL
under the platform's own name.

Two rules a face may not break:

- **Node-wide power keeps the platform's own chrome.** A caller holding
  a node-wide role (2.3) sees the platform's colours on every address,
  including a customer's. An operator must be able to tell by looking
  that they are on a page where they can act on the whole node; a themed
  node administration is a page that can be mistaken for a customer's.
  They still see **whose** place they are on, and that they are looking
  at it as the operator.
- **A face may not claim to be another tenant or the platform.** The
  title and the picture are freely chosen; the **address** is not — it
  is built from the label, which is unique on the node. The address
  therefore stands beside the face on every page the face applies to,
  not as decoration but as an anchor, and the platform's own name does
  not leave the page.

**Legibility is the platform's, the hue is the tenant's.** Two colours
cannot break a layout, but they can make text vanish into its own
background. An implementation MUST derive the contrasting values itself
rather than serving a chosen colour into a role it cannot fill — a light
header gets dark writing on it, and a pale brand colour is deepened
where it has to be read as text on white.

Who may set it: a `tenant_admin` for **their own** tenant, and a
`server_admin` for any (2.3). A request naming a tenant MUST NOT be
believed on its own; the target is computed from the caller's role and
their own tenant, wherever the request arrives. The default tenant has
no face of its own: its place is the node's address, and a node that
could disguise its own address is the impersonation this section
forbids.

### 2.8 Who lets people in (0.7, RFC-0041)

A tenant MAY name an **external identity provider**. The provider
answers *who somebody is*; the platform keeps answering *what they may
do*. The first kind is OIDC.

**The provider object is a URL.** `kind`, `issuer`, `client_id`, the
provider `version` it was built against, and a `label` for the button.
Nothing in it says whether the server runs on this node, on another, or
at the customer — and an implementation MUST NOT introduce a field that
does. That one property is what makes a tenant's later move to its own
node an edit rather than a project.

**The client secret is NOT part of this record.** This file is
world-readable on the node and travels in a tenant archive, and a
secret in a backup is a secret in every copy of that backup. It MUST be
held separately, readable only by the component that performs the
login, and MUST NOT be reachable by an app or by any surface that
renders it.

**The channel is the authentication of the issuer.** An implementation
that obtains the identity token over the back channel MAY rely on
transport validation in place of verifying the token signature (OIDC
Core 3.1.3.7) — and then the transport is not a hardening option, it is
the only thing that proves who answered. An `http` issuer that is
reachable from the internet MUST therefore be refused. (A signature
check would not rescue such a setup: a key document fetched over the
same plain channel is as forgeable as the token it would verify.)

**The binding is a platform rule and is not configurable.** A login
coming in through a provider is matched to a local record on
`(provider, subject, tenant)` and on **nothing else**. Matching by
e-mail address is account takeover by collision; matching by username
is the same with extra steps. The tenant is part of the key, not a
consequence of it: the same human arriving in two tenants is two
principals (RFC-0022 D3), and two tenants naming one realm MUST produce
two records.

**A name a provider suggests is a suggestion.** If it is taken, the
implementation MUST create a distinct name rather than adopt the record
that holds it.

**Breaking a binding does not create a way back.** An implementation
MUST make the consequence explicit: after a binding is removed, the
same person signing in through the provider is a **new** record with
the tenant's first-login rights, because a binding is the only thing
that says who somebody is. A record left without a binding and without
a local credential is a record with rights and no way in; an
implementation SHOULD deactivate it and MUST NOT describe the removal
as something that can simply be re-established.

**No login through a provider ever falls back to a local password**,
and no record a provider created has one. An implementation MUST say
this in code rather than rely on what a hashing library does with an
empty value.

**What a first login BECOMES is the tenant's**, because a club that
administers its own realm needs something different from a customer
whose people the operator admits by hand:

| `first_login` | Meaning |
| --- | --- |
| `eingang` | an identity and no rights. **The default.** |
| `role` | the tenant's `default_role` is granted |
| `groups` | as `role`, plus realm groups mapped onto visibility groups by an explicit local mapping |

**No claim of a provider ever becomes a role.** A realm group MAY be
mapped onto a visibility group (RFC-0007) through a mapping the
operator wrote; an unmapped group grants nothing, so a tenant cannot
widen its own rights by inventing a group. The roles an
implementation may grant at a first login MUST be an **allow**-list,
not a deny-list, and it MUST NOT contain node-wide roles or
`tenant_admin`: a door that opens on somebody else's assertion must not
be able to open the node or the whole tenant.

**Only `server_admin` may move these switches** (`first_login`,
`default_role`, the mapping, self-registration). A `tenant_admin` SEES
them and cannot change them, and seeing is not a courtesy: it is what
makes "only the operator changes this" honest instead of merely quiet.
The reason is the shared node — a tenant that could open itself would
be opening a door on a machine carrying other customers, and the
operator would learn about it afterwards. Every change is an entry in
**that tenant's** log (1.7).

**`role`/`groups` together with self-registration MUST be refused**
unless it is set deliberately with a reason, and the reason goes into
the log. Separately each is defensible; together they hand rights to
anyone who can reach the registration page, and nothing else in the
system would notice.

**A second factor is recorded, never claimed.** The provider decides
whether a login needs one; the platform only learns that the login
succeeded. An implementation MUST record what was asserted (`amr`/
`acr`) so an audit entry can say it, and MUST NOT present that as
enforcement of its own.

### 2.9 Making that provider, not only naming it (0.8, RFC-0041 K3)

A node MAY hold **connectors**: a product, an address and a credential
with which the platform creates the space (a Keycloak realm) and the
client a tenant's provider object then names. This is a capability of
the **node**, not of a tenant — one identity server usually carries
every tenant on the machine, and a credential that can create spaces
belongs to the operator.

A connector is **four verbs and no more**: state the product's version,
make the space, make the client, and spell the issuer. An
implementation MUST declare what it cannot yet do rather than omit it,
so that a missing capability is visible before it is needed.

**Managing is not owning.** An implementation MUST NOT delete anything
at a provider — not a space, not a client, not a person. A space it
did not create MUST remain usable and MUST be taken as it is. A client
it finds MAY be extended by the addresses this node needs and MUST NOT
otherwise be changed. Removing a tenant, or forgetting a connector,
MUST NOT touch anything at the provider: the people in a club's space
are the club's, not the platform's. This rule SHOULD sit on the path
every call takes rather than in the absence of a call, because absence
is not enforceable.

**Nothing is half-made.** The version MUST be checked before anything
is created, and a refusal MUST name the call, both versions and the way
forward. An implementation that cannot complete an operation MUST stop
at the first answer it does not understand and MUST NOT leave a space
behind in a state nobody asked for.

**"Not ours" is not "not there."** An answer that refuses access to a
space MUST NOT be read as the space being absent. On a shared server
that space is another customer, and creating over it is the one outcome
this whole section exists to prevent. The sentence saying so MUST be
given at **every** call it can arrive at, not only at the first.

**The credential obeys the channel rule of 2.8**, and for a stronger
reason: it can create spaces. It MUST be held where only the component
that uses it can read it, and — unlike the client secret of 2.8 — that
is **not** the component that performs logins. A service that completes
logins has no business holding a credential that creates spaces.

**Where a pinned version cannot be read, it is stated and said to be
stated.** An implementation SHOULD read the product's version and
refuse one it was not built against. Where the product will not state
its version to a credential as narrow as this section requires, the
implementation MUST NOT proceed silently: a human states the version,
and every surface that prints the number MUST say that it was stated
and not read. A stated version MUST NEVER override one the server
actually gave.

> This last rule is not a relaxation but the residue of a measurement.
> At Keycloak 26.7.4 the version lives at an endpoint that returns a
> trimmed document to any credential that is not a full server
> administrator — which is exactly the credential this section asks
> for. "The version is checkable" and "the credential is narrow" cannot
> both be had there, and what is kept is the substance: nothing is
> created against a version nobody has checked.

### 2.10 The switches inside that space (0.9, RFC-0041 K7)

Two of a tenant's settings do not live in this record at all. Who may
**register themselves**, and whether a **second factor** is asked for,
are settings of the provider's space: the registration page is the
realm's page, and the second factor is checked by the realm. K7 puts
both in v1, and this section is about the one difficulty that follows.

**A switch that exists in two places has two truths.** An
implementation MAY move these switches through a connector (§2.9), and
if it does it MUST record **what the space answered afterwards**, never
what it asked for. The write is followed by a read, and the read is
what is written down. Where the space answers something other than
what it was told, the operation MUST fail loudly **and** the record
MUST be set to what the space actually says: a record that is more
wrong than before is the one outcome a failure must not produce.

**An instruction that did not take does not become an intention.** The
record keeps both halves — what somebody chose, and what the space
last said — and an implementation MUST show where they differ rather
than resolve the difference silently. A read alone MUST NOT change the
chosen half; a read that adopted the space's value would erase the
disagreement in the act of discovering it.

**The open half decides.** Every rule that exists because
self-registration is dangerous MUST be evaluated against whichever
half is open. In particular the refusal of §2.8 — `role`/`groups`
together with self-registration, unless set deliberately with a reason
— MUST apply when the SPACE has it switched on, whatever this record
says, and the refusal SHOULD name which half that was.

**OAAP does not enforce a second factor and MUST NOT appear to.** The
realm decides; a login that arrives has already been let through. What
an implementation MUST do is record what the provider **named** about
it, and, where the space is supposed to require one and none was
named, say so in that tenant's log. It MUST NOT refuse the login on
that ground: refusing an authentication it did not perform, on the
strength of a claim it cannot verify, is worse than recording the
fact.

> What counts as "named" is a reading of the assertion's **methods**,
> not of its assurance level. Measured at Keycloak 26.7.4 on
> 2026-09-23: an ordinary password login answers `acr=1`, so a
> provider is never silent and a rule waiting for silence never fires.
> An assurance level's meaning is set inside the realm, and a platform
> that read it as evidence would be judging somebody else's number.

**A switch whose reach is smaller than its name says so once, out
loud.** Where the product applies a setting only to people who arrive
after it, an implementation MUST say that when the switch is moved.
Measured at Keycloak 26.7.4: a newly registered member is asked to set
up a second factor and a member who was already there is not.

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
8. **A name belongs to its tenant** (2.4). Two tenants each create an
   instance called `viewer`; both succeed, and their containers,
   networks, data directories, deploy tokens and hook addresses differ.
   Each answers at `viewer.<its label>.<node>`. A second `viewer`
   inside one tenant is refused. Renaming a tenant changes its
   addresses and **no** identifier.
9. **A name may be reused; the data behind it may not** (1.4). Instance
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

1a. **The one named exception** (0.4.1). Since the portal may create a
   tenant, the rule and the act collide: the page carrying the button
   does not exist until the button has been pressed. The rule holds
   where it protects somebody and yields where it protects nobody —
   **nothing about tenants is ever OFFERED on a single-tenant node**
   (no menu entry, no mention, no column, for any role), and the tenant
   page answers a `server_admin` who asks for it **by address**. A
   `tenant_admin` cannot exist on such a node, and any other role is
   redirected as before. Test: on a single-tenant node the rendered
   navigation of every role is byte-identical to 0.4, and `GET /tenant`
   answers 303 for every caller except a `server_admin`.
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
   or `support`. They cannot create a user in another tenant even by
   naming one in the request. `partner` they may grant: since RFC-0039
   it carries no platform authority and reaches nowhere.
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

12. **Both names change, and the outside follows.** Rename an instance:
    its address and its deploy address move to the new name, the old
    spelling of both keeps working for the grace period, its identity
    is unchanged, and its data directory is not touched. Rename its
    tenant: the same, for every instance of that tenant at once. On a
    single-tenant node neither is observable from outside.

13. **Data lives under its tenant.** Every instance's storage,
    configured secrets and retained packages are under
    `tenants/<tenant-id>/instances/<instance-id>/`, and nothing of one
    tenant is under another's path. Removing an instance without
    deleting its data records what was left and under which identity;
    reinstalling the same name in the same tenant finds that data
    again; deleting it is an operator act in the tenant's audit log.

14. **Two tenants, one word.** Both create an instance named `viewer`.
    Both succeed; `docker ps` shows two different containers, the two
    data directories are different, each instance answers only at its
    own `viewer.<label>.<node>`, and each deploy hook reaches only its
    own. A second `viewer` in the same tenant is refused, naming the
    name and not its owner. Then rename one tenant: its addresses
    change, its identifiers do not, and its deploy address still works.

15. **No port past the gateway for a tenant.** On an `exposed` node, a
    `tenant_admin` asking for a declared non-HTTP endpoint of their own
    instance is refused with a message naming the reason, and the host
    refuses the same request when it arrives through the queue with the
    portal check bypassed. A `server_admin` gets it.

16. **The tenant has a place, and the place holds its boundary** (0.5).
    A tenant labelled `cls` answers at `cls.<node>`. A `server_admin`
    reaching it sees that tenant's apps and **no others** — the same
    account at the node's own address still sees everything. An
    unexpired former label reaches the same place. The default tenant
    has no such address: its place is the node's own. A host naming a
    tenant this node does not have answers nothing, **on every page of
    the portal and not only on the launchpad** — checking it at the
    launchpad alone would leave an address that does not exist
    answering everywhere nobody looked.

17. **One namespace, checked both ways** (0.5). With a default-tenant
    instance called `studio`, creating or renaming a tenant to the
    label `studio` is refused; with a tenant labelled `studio`,
    creating or renaming a default-tenant instance to `studio` is
    refused. Both refusals are **word for word** the refusal that name
    already gets from its own kind — a caller must not be able to tell
    from the sentence whether a tenant or an instance holds it.
    Unexpired former labels and former instance names are held in both
    directions; an instance of any other tenant holds nothing, because
    it answers one level deeper.

18. **The face is values, and the anchor is not chosen** (0.6). A
    tenant sets a title, two colours and a logo. Its place and its
    **login page** carry them; a caller with a node-wide role reaching
    the same address gets the platform's colours and no foreign logo,
    and still reads whose place it is. What the theme produces is a set
    of variable assignments and nothing else — a colour that is not six
    hex digits is refused, at every door. With no title set, the page
    shows the **label** and never the tenant's `name`. The tenant's
    address stands beside its face, and the platform's own name is still
    on the page. A pale brand colour produces readable text rather than
    white on white.

19. **The logo is content, and the copy that is served is derived**
    (0.6). An uploaded picture is stored under the owning tenant in
    `oaap.data.files` and is not findable from another tenant's store.
    An SVG is refused — also when it is called `logo.png`, because the
    content decides — with a reason naming what it would become. Delete
    the served copy: the next refresh writes it again from the store,
    and a second refresh changes nothing. Rename the tenant: the copy
    follows the new label and stays under the former one as long as that
    address answers. Remove the logo: the served copy goes with it.

20. **A foreign login binds to a subject, not to a name** (0.7).
    Configure a provider for one tenant. A first login creates a local
    record bound to `(provider, subject, tenant)` with exactly the
    rights the tenant's policy names and no others — in particular no
    role and no group the provider asserted, including a realm group
    called `server_admin`. Put a record in the store that matches the
    incoming person in everything a provider can assert (e-mail,
    display name, even the username) and lacks only a binding: it is
    **not** adopted, keeps its own rights, and the new record gets a
    distinct name. A second login through the same provider finds the
    first record and creates nothing. The record has no local password
    and the local login form refuses it. Break the binding: the next
    login is a **new** record, and the operator was told so.

21. **The switch belongs to the operator, the secret to the node**
    (0.7). A `tenant_admin` sees `first_login`, the default role and
    self-registration for their own tenant and cannot change any of
    them; a `server_admin` can, and each change is in that tenant's
    log. `first_login: role` with self-registration is refused unless a
    reason is given, and the reason is in the log. A role that is
    node-wide, or `tenant_admin`, is refused as a first-login role at
    every door. The client secret appears in no tenant record, in no
    tenant archive and on no surface; the component that performs the
    login is the only one that can read it. An `http` issuer on a host
    reachable from the internet is refused with a reason naming the
    channel.

22. **The platform makes a space and owns none of it** (0.8).
    Record a connector and provision a tenant through it: the space and
    the client exist at the provider, the client is confidential, it
    holds exactly this node's return addresses, and the tenant's
    provider object names the issuer with the version that was actually
    established. Run it again: nothing is created a second time, and a
    space that was already there is used unchanged. Point it at a space
    that exists and that this credential may not manage: the operation
    is refused with a sentence saying it is somebody else's, **nothing
    is created**, and the same sentence appears whichever call the
    refusal arrives at. Offer a version the implementation was not
    built against: it is refused before anything is created, and
    counting at the provider shows zero writes. Offer a server that
    states no version at all: it is refused likewise, and proceeds only
    once a human states the version — which then appears as *stated*
    wherever it is printed, and is overridden the moment the server
    does state one. No call an implementation makes to a provider uses
    a method that could delete. Forgetting a connector changes nothing
    at the provider, and the tenants provisioned through it keep
    signing in. The credential is readable by no container, including
    the one that performs logins.

23. **The switch and the record are one thing, or the difference is
    visible** (0.9). Move self-registration and the second factor
    through a connector: the space itself changes, and the tenant's
    record holds what the space answered, read back after the change.
    Make the space accept the change and report the old value: the
    operation fails with a sentence, the record is corrected to what
    the space says, and the instruction that did not take is still
    shown as an unfinished difference. Change a switch at the
    provider's own console and read again: the difference is named,
    and the chosen half is not quietly moved to match. With the space
    open and the record closed, ask for a first-login policy that
    grants a role: it is refused, and the refusal names the space.
    Require a second factor and let somebody in who was already in the
    space: the login is NOT refused, and that tenant's log says a
    second factor was expected and none was named — including where
    the provider stated an assurance level and no method. Ask for the
    switches with a dry run: nothing at the provider is called.

## 5. Dependencies

`oaap.core.identity` (user records, roles, the authorization call),
`oaap.apps.runtime` (instance registry, hostnames, deploy tokens,
creation permits), `oaap.core.portal` (surfaces), `oaap.data.backup`
(per-tenant backup, D7), `oaap.data.files` (0.6: where a tenant's logo lives).

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

## Nachtrag 0.3 — der Name gehört dem Mandanten

Bis 0.2 war ein Instanzname **knotenweit** eindeutig. Zwei Kunden auf
einem Knoten konkurrierten damit um gewöhnliche Wörter — `crm`, `wiki`,
`viewer` —, und der Zweite bekam eine Ablehnung, deren Grund er nicht
sehen konnte. Im Modell „wir betreiben, der Kunde verwaltet" ist das
besonders unangenehm: Dort sieht der Betreiber absichtlich nicht, was
die Mandantenverwalter tun, und ist an dem Gespräch, das die Ablehnung
erklären würde, gar nicht beteiligt.

Seit 0.3 gehört ein Instanzname dem **Mandanten**. Zwei Kunden dürfen
beide eine `viewer` haben. Was ihre Container, Netzwerke,
Datenverzeichnisse, Deploy-Token und Hook-Adressen auseinanderhält, ist
ein **Schlüssel**, der einmal zusammengesetzt und nie neu berechnet
wird: `<kurzname>-<name>`, im Standard-Mandanten schlicht `<name>`.

**Der Kurzname ist eingefroren.** Er entsteht beim Anlegen des
Mandanten aus dessen erstem Kürzel und wird danach nie wieder geändert
— auch nicht beim Umbenennen. Der Grund ist eine Zusage aus 1.6: Ein
Umbenennen soll eine *Umbenennung* sein und keine Migration. Würden
Containernamen und Verzeichnisse dem aktuellen Kürzel folgen, wäre
jedes Umbenennen ein Umbau mit Ausfallzeit — bezahlt für eine
kosmetische Änderung. Der Preis steht dafür ausdrücklich da: Nach einem
Umbenennen tragen die Kennungen noch den alten Kurznamen. Kosmetik an
Kennungen, nie an Adressen.

**Die Adresse trägt weiter den Namen, den der Kunde gewählt hat.** Eine
Instanz mit dem Schlüssel `cls-viewer` antwortet unter
`viewer.cls.<knoten>` — der Schlüssel existiert, damit Kennungen nicht
kollidieren, die Adresse braucht ihn nicht, weil das Kürzel den
Mandanten schon nennt.

**Für einen Knoten mit einem Mandanten ändert sich nichts.** Sein
Kurzname ist der leere String, genau wie sein Kürzel die Abwesenheit
eines Kürzels im Hostnamen ist. Jeder bestehende Schlüssel, jede
Adresse und jede ausgelieferte Deploy-URL gilt unverändert weiter —
ohne Übergangsschicht, die jemand pflegen müsste.

**Und die Umstellung benennt nichts um.** Bestehende Instanzen behalten
die Schlüssel, die sie haben; es kommen nur zwei Felder dazu. Kein
Container wird neu gebaut, kein Verzeichnis verschoben. Schlüssel
müssen eindeutig sein, nicht einheitlich.

**Zwei Prüfungen statt einer:** frei sein muss der **Schlüssel** auf
dem Knoten *und* der **Name** innerhalb des Mandanten. Für eine
Instanz, die älter ist als diese Regel und deshalb einen Schlüssel ohne
Kurznamen trägt, sind das zwei verschiedene Fragen — und nur die erste
zu stellen hieße, einem Mandanten zwei Instanzen namens `viewer` zu
erlauben.

## Nachtrag 0.4 — Namen sind änderbar, Identität nicht

0.3 hat den Namensraum je Mandant geschnitten. Die Frage danach war
Jörgs: *Kann man einen Mandanten und eine Instanz eigentlich umbenennen
und das Erscheinungsbild nach außen mitziehen?* Bis dahin: einen
Mandanten ja, eine Instanz gar nicht. Beides hing am selben Umstand —
ein Name war hier nicht nur ein Name, er war auch die Ablage.

**Die schmerzhafte Stelle war genau eine.** Von allem, was eine
Umbenennung anfasst, wird das meiste bei jedem Deployment ohnehin neu
geschrieben: Containernamen, Netzwerke, Gateway-Dateien,
Registry-Schlüssel, Token-Einträge. Teuer ist nur eines — die Daten zu
verschieben. Und es ist das Einzige, das halb fertig scheitern und
Kundendaten an zwei Orten hinterlassen kann.

**Also hängt die Ablage jetzt an Identitäten:**
`tenants/<mandant-id>/instances/<instanz-id>/`, mit lesbaren Symlinks
daneben. Drei Dinge fallen dabei ab. Alle Daten eines Mandanten sind
**ein Pfad** — das macht Sicherung je Mandant, Löschen mit Export und
den Umzug eines Mandanten auf einen anderen Knoten zu normalen
Vorgängen statt zu Projekten. Eine Umbenennung **verschiebt nichts**.
Und Daten können die Mandantengrenze **gar nicht mehr versehentlich
überqueren** — die Sicherung aus 0.2.2 wird zur Form des Baums, und die
Markierungsdatei darin überflüssig.

**Der eingefrorene Kurzname aus 0.3 ist zurückgenommen.** Er war die
richtige Antwort, solange die Ablage am Namen hing: Einfrieren hielt
eine Umbenennung davon ab, eine Migration zu werden. Hängt die Ablage
an einer Identität, kauft das Einfrieren nichts mehr außer Drift
zwischen dem, wie ein Container heißt, und dem, wem er gehört. Also
folgen Kennungen wieder dem aktuellen Kürzel — und eine Umbenennung des
Mandanten baut dessen Apps neu und startet sie neu. Der Dialog sagt das
vorher: Sekunden Ausfall für eine seltene, ausdrückliche Handlung,
dafür keine Drift.

**Was ein alter Name behält.** Beide Umbenennungen lassen die frühere
Schreibweise eine Schonfrist lang weiter antworten — die Adresse *und*
die Deploy-Adresse. Ein Name, der veröffentlicht war, ist ein Name, den
jemand aufgeschrieben hat. Zusätzlich nimmt die Deploy-Adresse die
**Kennung** der Instanz an, und die ändert sich nie: Wer einer KI diese
Form gibt, muss sie nach keiner Umbenennung informieren.

**Eine Zusage wäre dabei fast verloren gegangen.** „Daten behalten"
beim Entfernen verspricht, dass eine Neuinstallation gleichen Namens
sie wiederfindet. Mit id-basierten Pfaden gilt das nur noch, weil das
Entfernen sich die Identität als Merkposten notiert — und dieser
Merkposten macht zurückgelassene Kundendaten zum ersten Mal überhaupt
sichtbar, statt sie nach einer einmaligen Meldung verschwinden zu
lassen.

## Deutsche Zusammenfassung (1.7, v0.4.2 — vier Einträge für die Instanz-Diagnose)

Das Mandantenprotokoll hält bisher **Zustandsänderungen** fest, nie
Lesevorgänge. RFC-0038 D2 fügt die erste Ausnahme hinzu, und sie begründet
die Regel, statt sie zu verwässern: Ein Diagnose-Fenster gibt jemandem das
**Log der App** — Inhalte, die die Plattform weder geschrieben hat noch
zuverlässig filtern kann. Deshalb wird hier das *Lesen selbst*
aufgeschrieben, obwohl sich nichts geändert hat.

Neu im Vokabular: `diagnose.opened` (mit der Dauer im `detail`),
`diagnose.closed` (vorzeitig geschlossen), `diagnose.expired` (die Zeit
war um, die Plattform hat geschlossen) und `instance.restarted` (die
Container wurden neu erzeugt, D4).

**Die Inhalte stehen nie drin.** Der Eintrag sagt, wer wann für wie lange
ein Fenster auf welcher Instanz geöffnet hat — er ist keine Kopie des
Gelesenen. Dieselbe Begründung wie bei `instance.export`: Dass der
Betreiber sich das Log auch per ssh holen könnte, ist ein Grund, warum
dieses Protokoll nicht vollständig sein kann — kein Grund, die Zeile
weglassen, die man schreiben kann.

## Deutsche Zusammenfassung (1.7, RFC-0037 — der Eintrag, der mehr trägt als sein Verb)

`instance.sideload` wird geschrieben, wenn ein **hochgeladenes** Paket in
eine Produktiv-Instanz installiert wird — aus dem Portal wie von der
Maschine. Sein `detail` nennt: neu oder Aktualisierung, die Fassung, die
Prüfsumme des Pakets und **im Wortlaut** jede Rahmenerweiterung, die
dabei bestätigt wurde.

Warum dieser eine Eintrag mehr trägt als die anderen: Es ist der einzige
Akt, bei dem die Plattform für die **Herkunft** des Codes nicht
einstehen kann — OAAP-Pakete sind nicht signiert (RFC-0019). An die
Stelle des Beweises tritt die Aufzeichnung, wer welche Bytes angenommen
hat. Und sie gehört dem Kunden, in das Protokoll des Kunden.


## Deutsche Zusammenfassung (0.5 — der Mandant ist ein Ort)

**Die Adresse.** Ein Mandant antwortet jetzt unter
`<kürzel>.<knoten>` — also etwa `cls.oaap.joomp.de`. Das ist keine
Erweiterung des Namensschemas, sondern die Stelle darin, die nie
gefüllt wurde: Instanzen heißen längst `<instanz>.<kürzel>.<knoten>`,
die Ebene dazwischen war leer. Der Standard-Mandant bekommt keine —
sein Kürzel ist die Abwesenheit eines Kürzels, also *ist* sein Ort die
Wurzel des Knotens. Frühere Kürzel antworten mit, solange ihre
Schonfrist läuft; ein Verein, der gerade umbenannt wurde, findet seine
Seite weiter.

**Dort antwortet das Portal, nicht eine zweite Anwendung.** Eine eigene
App hätte fünf Dinge neu erwerben müssen, die das Portal hat und die
getestet sind: das Launchpad, den Rollenfilter, den Gruppenfilter, die
Mandantengrenze und die Sitzung. Genau so entstehen die teuersten
Fehler dieses Codes.

**Zwei Regeln sind der eigentliche Inhalt:**

- **Der Host verengt, und zwar für jeden.** Wer über `cls.<knoten>`
  kommt, sieht die Apps dieses Mandanten und keine anderen — auch ein
  `server_admin`. Die Knotensicht ist einen Hostnamen entfernt. Eine
  Seite, die mehr beantwortet als die Adresse gefragt hat, ist die
  Art, wie ein Betreiber verwechselt, auf wessen Bildschirm er
  gerade schaut.
- **Ein Host, der einen Mandanten nennt, den es hier nicht gibt,
  liefert nichts.** Nicht die Betreibersicht, und keine leere Seite,
  die wie eine funktionierende aussieht. Und das gilt für das **ganze**
  Portal, nicht nur für das Launchpad — sonst antwortet ein Ort, den es
  nicht gibt, überall außer dort, wo jemand hingeschaut hat.

**Und die Wache, die vorher kommen musste.** Ein Mandanten-Kürzel und
der Name einer Instanz des Standard-Mandanten teilen sich denselben
Adressraum: beide wollen `<x>.<knoten>`. Bisher hat das niemand
gegeneinander geprüft — folgenlos, solange dort nichts antwortete, und
ab dieser Fassung nicht mehr. Beide Richtungen werden jetzt abgelehnt,
frühere Kürzel und frühere Instanznamen zählen mit.

Die Ablehnung ist dabei **wortgleich** mit der, die derselbe Name schon
von seiner eigenen Art bekommen hätte. Das ist Absicht: Klänge sie
anders, verriete gerade die neue Wache, was sie schützen soll.

## Deutsche Zusammenfassung (0.6 — der Mandant bekommt ein Gesicht)

**Vier Werte, kein Stylesheet.** Ein Mandant darf über seinen Ort vier
Dinge bestimmen: einen öffentlichen Titel, zwei Farben und ein Bild.
Mehr nicht — und das *Mehr nicht* ist die Anforderung, nicht eine
Sparmaßnahme. Wer ein eigenes Stylesheet mitbringen darf, kann jedes
Bedienelement auf einer Seite verschieben, verstecken oder fälschen, für
die die Plattform geradesteht. Vier Werte können das nicht. Deshalb darf
aus einem Design auch nur eine Liste von Werten entstehen, und eine
Farbe, die kein sechsstelliger Hex-Wert ist, wird abgelehnt: Ein Wert,
der ein Semikolon tragen kann, ist kein Wert.

**Der Titel ist ein zweites Namensfeld, mit Absicht.** Der `name` aus
1.1 ist der Klarname, und die Seite, die nach ihm fragt, verspricht
schriftlich, dass er im Haus bleibt. Der Titel steht auf der
Anmeldeseite — und die verlangt definitionsgemäß keine Anmeldung. Ohne
gesetzten Titel steht deshalb das **Kürzel** da, nie der Klarname. Das
Kürzel ist ohnehin öffentlich: Es steht im Hostnamen und damit im
Certificate-Transparency-Log, das jeder lesen kann.

**Das Logo ist ein Inhalt.** Es liegt in `oaap.data.files`, über seinen
Hash adressiert und unter dem Mandanten, dem es gehört — also in der
Sicherung, im Mandantenarchiv und in der Generalprobe, und für andere
Mandanten nicht adressierbar. Ausgeliefert wird es aber von einer Route,
die keine Sitzung verlangt, denn die Anmeldeseite hat keine. Die Kopie
dort ist **abgeleitet**: Sie wird nach Umstieg, Umbenennen und
Rückspielung neu geschrieben, und kein Archiv trägt sie. Ein Bild auf
eine Seite zu stellen, die jeder öffnen kann, macht es öffentlich — ein
öffentliches Verzeichnis sagt das, statt es anzudeuten.

**Kein SVG**, und entschieden wird nach dem **Inhalt**, nie nach dem
Dateinamen. Das Bild wird unter der Adresse dieser Plattform
ausgeliefert, und ein Bild, das ein Skript tragen kann, sitzt dort neben
der Sitzung jedes Benutzers. Das ist kein Urteil über den Betreiber, der
es hochlädt — es geht darum, was die Datei wird, sobald sie eine Adresse
unter unserem eigenen Namen hat.

**Zwei Regeln, die ein Design nicht brechen darf:**

- **Wer knotenweite Macht hält, sieht die Farben der Plattform** — auch
  am Ort eines Kunden. Man muss einer Seite ansehen können, dass man auf
  ihr den ganzen Knoten bewegen kann; eine eingefärbte Knotenverwaltung
  ist eine Seite, die man für die eines Kunden halten kann. Wessen Ort
  es ist, sieht der Betreiber trotzdem — und dass er als Betreiber
  darauf schaut.
- **Ein Design darf nie einen anderen Mandanten oder die Plattform
  nachahmen.** Titel und Bild sind frei wählbar, die **Adresse** nicht:
  Sie entsteht aus dem Kürzel und ist auf diesem Knoten eindeutig. Also
  steht sie neben dem Gesicht, auf jeder Seite, die es trägt — nicht als
  Zierde, sondern als Anker. Und der Name der Plattform verlässt die
  Seite nicht.

**Die Farbe wählt der Mandant, die Lesbarkeit die Plattform.** Zwei
Farben können kein Layout zerstören, aber sie können Text in seinem
eigenen Hintergrund verschwinden lassen. Zu einer hellen Kopfzeile wird
die Schrift darauf dunkel, und eine blasse Markenfarbe wird dort
abgedunkelt, wo sie als Text auf Weiß gelesen werden muss.

**Wer es setzen darf:** ein `tenant_admin` für **seinen eigenen**
Mandanten, ein `server_admin` für jeden. Einer Anfrage, die einen
Mandanten nennt, wird dabei nicht geglaubt — das Ziel wird aus der Rolle
des Aufrufers und seinem eigenen Mandanten berechnet, an jeder Tür.
Der Standard-Mandant bekommt kein eigenes Gesicht: Sein Ort ist die
Adresse des Knotens, und ein Knoten, der seine eigene Adresse verkleiden
könnte, wäre genau die Nachahmung, die dieser Abschnitt verbietet.

## Deutsche Zusammenfassung (0.7 — der Mandant darf sagen, wer hereinlässt)

Ein Mandant darf einen **eigenen Anmeldedienst** benennen. Der Anbieter
beantwortet, **wer** jemand ist; OAAP beantwortet weiterhin, **was** er
darf. Die Apps merken davon nichts.

**Das Anbieter-Objekt ist eine URL.** Nirgends steht „das Keycloak
hier". Genau diese eine Eigenschaft macht den späteren Umzug eines
Vereins auf einen eigenen Knoten zu einer Änderung statt zu einem
Projekt — und deshalb darf keine Fassung dieser Spezifikation ein Feld
einführen, das sagt, wo der Server steht.

**Das Client-Geheimnis steht NICHT in diesem Satz.** Die Datei ist auf
dem Knoten für jeden lesbar und reist im Mandantenarchiv mit; ein
Geheimnis in einer Sicherung ist ein Geheimnis in jeder Kopie dieser
Sicherung. Es liegt getrennt, und nur der Dienst, der die Anmeldung
durchführt, kommt daran.

**Der Kanal ist die Beglaubigung des Ausstellers.** Wer das Token über
den Rückkanal holt, darf sich die Signaturprüfung sparen — das erlaubt
OIDC Core ausdrücklich, weil TLS zum Token-Endpunkt schon beweist, wer
geantwortet hat. Dann ist der Kanal aber keine Stellschraube mehr,
sondern die einzige Beglaubigung: Ein aus dem Internet erreichbarer
`http`-Aussteller muss abgelehnt werden. Eine Signaturprüfung rettete
so eine Lage übrigens nicht — ein über denselben offenen Kanal geholtes
Schlüsseldokument ist genauso fälschbar wie das Token, das es prüfen
sollte.

**Die Bindung ist Plattformregel und keine Einstellung.** Eine
eingehende Anmeldung wird an `(Anbieter, Kennung, Mandant)` zugeordnet
und an sonst nichts. Über die E-Mail-Adresse zuzuordnen ist
Kontoübernahme durch Namensgleichheit; über den Benutzernamen dasselbe
mit Zwischenschritt. Der Mandant gehört zum Schlüssel, weil derselbe
Mensch in zwei Mandanten **zwei** Prinzipale ist.

**Eine gelöste Bindung ist kein Rückweg.** Wer sich danach erneut
anmeldet, ist ein **neuer** Satz mit den Vorgaberechten — denn eine
Bindung ist das Einzige, was sagt, wer jemand ist. Das muss man den
Leuten sagen, statt es sie herausfinden zu lassen. Und ein Satz ohne
Bindung und ohne lokales Passwort ist ein Satz mit Rollen und ohne Weg
hinein; der gehört stillgelegt.

**Was ein erster Login BEDEUTET, trägt der Mandant:** `eingang`
(Vorgabe — eine Identität und keine Rechte), `role` oder `groups`.
**Umlegen darf den Schalter nur der Betreiber.** Der Mandant sieht ihn,
und das Sehen ist keine Höflichkeit: Es ist das, was „nur der Betreiber
ändert das" ehrlich macht statt bloß still. Der Grund ist die geteilte
Maschine — wer sich selbst eine Tür öffnen könnte, öffnete sie auf
einer Maschine, die ihm nicht allein gehört, und der Betreiber erführe
es hinterher.

**Keine Behauptung des Anbieters wird je zu einer Rolle.** Eine
Realm-Gruppe darf höchstens auf eine Sichtbarkeitsgruppe abgebildet
werden, durch eine Zuordnung, die der Betreiber selbst schreibt. Und
die Liste der überhaupt vergebbaren Rollen ist eine **Erlaubnis**-Liste,
keine Verbotsliste: Eine Rolle, die die Plattform später bekommt, ist
sonst versehentlich vergebbar.

**`role` zusammen mit Selbstregistrierung wird abgelehnt**, außer es
wird ausdrücklich mit Begründung gesetzt — und die Begründung steht
danach im Protokoll. Jedes für sich ist vertretbar; zusammen
verschenken sie Rechte an jeden, der die Seite erreicht, und nichts
sonst im System würde es merken.

**Ein zweiter Faktor wird notiert, nicht behauptet.** Keycloak
entscheidet, ob eine Anmeldung einen braucht; OAAP erfährt nur, dass sie
geklappt hat, und schreibt auf, was behauptet wurde.

## Deutsche Zusammenfassung (0.9 — die Schalter im Raum, und die Wahrheit darüber)

Zwei Einstellungen eines Mandanten liegen gar nicht in diesem Satz:
**wer sich selbst anmelden darf** und **ob ein zweiter Faktor verlangt
wird**. Beide gehören dem Anmeldedienst — die Registrierungsseite ist
seine Seite, und den zweiten Faktor prüft er. 0.9 sagt, wie OAAP damit
umgeht, dass derselbe Schalter dadurch an zwei Orten steht.

**Was in unserer Konfiguration steht, hat der Raum gesagt — nicht
wir.** Wer die Schalter über einen Konnektor bewegt, schreibt
*danach* auf, was der Raum antwortet. Sagt der Raum etwas anderes, als
er zugesagt hat, ist das ein lauter Fehlschlag **und** der Satz des
Mandanten wird auf die Wirklichkeit gesetzt. Ein Fehlschlag darf den
Satz nicht falscher zurücklassen, als er vorher war.

**Eine Anweisung, die nicht ankam, wird nicht zur Absicht.** Beide
Hälften bleiben stehen — was jemand gewählt hat und was der Raum
zuletzt sagte — und ein Unterschied wird *benannt*, nicht stillschweigend
aufgelöst. Ein bloßes Nachlesen darf die gewählte Hälfte nicht
überschreiben, sonst löscht es den Unterschied in dem Augenblick, in
dem es ihn findet.

**Die offene Hälfte entscheidet.** Die gefährliche Kombination aus 2.8
— eine Rolle beim ersten Login *und* Selbstregistrierung — wird auch
dann abgelehnt, wenn nur der Raum offen ist und unser Satz das
Gegenteil behauptet. Und die Ablehnung sagt, welche Hälfte es ist.

**OAAP erzwingt keinen zweiten Faktor und darf nicht so tun.** Der Raum
entscheidet. OAAP schreibt auf, was der Anbieter *genannt* hat, und
sagt es im Protokoll, wenn der Raum einen verlangen soll und keiner
genannt wurde. Abgelehnt wird die Anmeldung deswegen nicht — eine
fremde Anmeldung zu verweigern, die man selbst nicht geprüft hat, ist
schlechter, als sie festzuhalten. Gelesen werden dabei die *Methoden*
(`amr`), nicht die Vertrauensstufe (`acr`): Keycloak antwortet auf eine
gewöhnliche Passwort-Anmeldung mit `acr=1`, und was diese Zahl bedeutet,
wird im Realm festgelegt und nicht hier.

**Ein Schalter, der weniger erreicht als sein Name verspricht, sagt das
einmal laut.** Gemessen an Keycloak 26.7.4: Wer neu dazukommt, wird nach
einem zweiten Faktor gefragt; wer schon da war, nicht.

## Deutsche Zusammenfassung (0.8 — die Plattform legt die Tür selbst an)

Bis 0.7 durfte ein Mandant **sagen**, wer ihn hereinlässt. Seit 0.8
darf die Plattform diese Tür auch **bauen**: Ein Knoten hält
*Konnektoren* — ein Produkt, eine Adresse und eine Vollmacht —, und
damit legt OAAP den Realm und den Client an, die das Anbieter-Objekt
eines Mandanten danach nennt. Das ist eine Sache des **Knotens**, nicht
eines Mandanten: Ein Anmeldeserver trägt meist jeden Verein auf der
Maschine, und eine Vollmacht, die Realms anlegen kann, gehört dem
Betreiber.

Ein Konnektor ist **vier Verben und keines mehr** (Fassung nennen,
Raum anlegen, Client anlegen, Aussteller buchstabieren). Was er noch
nicht kann, muss er **benennen** statt weglassen — eine fehlende
Fähigkeit soll sichtbar sein, bevor jemand sie braucht.

Die Regeln, die keine Einstellungen sind:

- **Verwalten ist nicht besitzen.** Es wird nichts gelöscht. Nie. Kein
  Realm, kein Client, kein Mensch. Einen Mandanten zu entfernen oder
  einen Konnektor zu vergessen rührt beim Anbieter nichts an — die
  Menschen im Raum eines Vereins gehören dem Verein.
- **Es entsteht nichts halb.** Die Fassung wird geprüft, **bevor**
  etwas angelegt wird; bei einer Antwort, die OAAP nicht versteht, wird
  abgebrochen statt geraten.
- **„Gehört uns nicht" ist nicht „ist nicht da".** Eine Ablehnung darf
  nie als Abwesenheit gelesen werden — auf einer geteilten Maschine ist
  das der Verein von jemand anderem. Und der Satz, der das sagt, muss
  an **jeder** Tür stehen, durch die er kommen kann, nicht nur an der
  ersten.
- **Die Vollmacht liegt bei ihrem Leser und keinen Schritt weiter** —
  und das ist ausdrücklich **nicht** der Dienst, der die Anmeldungen
  abschließt.
- **Wo eine festgenagelte Fassung nicht gelesen werden kann, nennt sie
  ein Mensch — und überall steht dabei, dass sie genannt wurde.** Das
  ist keine Lockerung, sondern der Rest einer Messung: Bei Keycloak
  26.7.4 steht die Fassung an einer Stelle, die einer engen Vollmacht
  ein beschnittenes Dokument zurückgibt. „Prüfbar" und „eng" gibt es
  dort nicht zusammen. Was bleibt, ist der Kern: Es entsteht nichts
  gegen eine Fassung, die niemand geprüft hat. Eine Behauptung schlägt
  eine Messung dabei nie.
