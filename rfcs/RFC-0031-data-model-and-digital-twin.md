# RFC-0031: The Digital Twin — One Shared Data Layer Per Tenant

- **Status:** Accepted (2026-09-08) — the shape was decided in the
  interview (twenty answers in `program/zielbild-datenplattform.md`),
  the eight edge decisions D1–D8 the same evening, each following the
  recommendation. See the decision record at the end.
- **Date:** 2026-09-08
- **Authors:** Jörg (model, direction, twenty decisions), Claude
  (analysis & proposal)
- **Depends on:** RFC-0022 (tenant as boundary — one twin per tenant),
  RFC-0012 §8.3 (reserved names `consumes`/`contributes`/`data_models`),
  RFC-0004 (manifest), RFC-0027 (machine principals — an app writes as
  itself), RFC-0026 (identity is not changeable), RFC-0029 (backups),
  RFC-0030 D6 (shared data holding must be copyable), RFC-0023 (AI
  gateway — embeddings, later)
- **Followed by:** RFC-0032 (events, states and the unified namespace),
  a later RFC for the AAS repository API, and capability specs
  `oaap.data.model`, `oaap.data.store`, `oaap.data.twin`.
- **Driver:** Jörg, 2026-09-08: *„Eine App ‚Kundenmanagement' kann die
  Daten für Kunden und Ansprechpartner pflegen und diese für andere über
  einen Plattform-Layer bereitstellen. […] Andere Apps könnten im
  Manifest anzeigen, dass sie Daten für einen ‚Customer' konsumieren.
  […] Es muss also nicht für alle Objekte eine App geben, und es könnte
  durchaus Fälle geben, wo mehrere Apps ihre Daten in einen Zieltyp
  bereitstellen, wir also auch die Herkunft für eine Schlüsselbeziehung
  speichern müssten."* — and, on what the Asset Administration Shell
  cannot do: *„Was ich bis heute vermisse, sind meine Erweiterungen um
  zeitabhängige Beziehungen mit Properties und die Aktivitäten."*

## Summary

Every app on OAAP today owns its data completely and shares nothing.
That is correct for isolation (RFC-0016) and wrong for the thing a
small company actually needs: the customer that the CRM knows is the
same customer the project app, the complaint app and the RACI app
mean, and today each of them would type it in again.

This RFC proposes the **digital twin**: one shared data layer per
tenant into which apps deliver their objects and from which every app,
agent and person of that tenant reads. It is built from a model Jörg
built twice before (in ABAP and as a Python service) and then set
aside — and from the one thing that model has and the industry standard
lacks: **relations that are valid in time and carry their own
attributes, and activities as first-class entities.**

The shape was decided in the interview of 2026-09-08 and is not
re-opened here; it is restated in §3 so this document stands alone.
What remains are eight decisions about the edges:

| | Question | Recommendation |
| --- | --- | --- |
| **D1** | Where do types come from, and who may change one? | **Three origins, each with a namespace**: an app package, a `data_models` artefact, the tenant itself. Only the origin changes its types. |
| **D2** | Is a type definition per node or per tenant? | **Definition per package, activation per tenant.** Installing a package registers its types; a tenant's twin holds instances only for types activated there. |
| **D3** | What is an object's identity, and what happens on merge? | **An opaque platform ID plus any number of source keys.** A merge keeps both IDs resolvable forever; one becomes the canonical, the other an alias. |
| **D4** | How does an app's word ("Kunde") meet the platform's type ("Customer")? | **Binding at install time**: automatic when key or alias matches, otherwise the operator picks in the install dialog. Never silent, never blocking. |
| **D5** | Which time axes does a type carry? | **Recorded time always**, **validity** per attribute and relation type on opt-in, **planning** on activity types. |
| **D6** | What does a consumer get without a specification? | **A reference**: id, type, title, origin — and nothing else. More fields only through a consolidated model the tenant owns. |
| **D7** | Who may read which group? | **Reading is tenant-wide by declaration**: an app reads the types it `consumes`; a group may be marked `restricted` to its owner and named consumers. Shown before installation. |
| **D8** | How does a rehearsal (RFC-0030) copy a twin? | **By copying the tenant's twin schema** into a rehearsal schema bound to that one instance. If the copy is refused, so is the rehearsal. |

Jörg decided all eight on 2026-09-08, following every recommendation
(record at the end).

## Motivation

### The problem, in Jörg's example

A customer-management app keeps organisations and contacts in the
model that suits it best. A project app needs to pick a customer from
a list. A RACI app assigns employees to tasks for a customer. A
satisfaction score is maintained by nobody's app — it is the tenant's
own data about the same customer. Four things look at one object, and
each of them has a different opinion about what a customer is.

Without a shared layer, each app either re-implements the customer
list (four lists, four spellings) or talks to the CRM directly (four
integrations, and the CRM can never change). Both are what SAP
landscapes look like from the inside, and Jörg's stated purpose for
OAAP is to give a small company the enterprise architecture *without*
the enterprise.

### Why not the Asset Administration Shell alone

The AAS is a standard and it is specified; roughly half of Jörg's model
maps onto Shell + Submodel + Concept Description directly, and this RFC
borrows that vocabulary on purpose (§3.3). What the AAS does not have
is what turned out to be the most-used part of the earlier system:

- **relations that are valid for a period and carry attributes** —
  "Anna is the purchasing contact of Müller GmbH from 2019, at this
  e-mail address"; "this machine belonged to that customer until May";
- **activities** — a phone call, a task, a project, an inbound e-mail —
  as entities with their own time model, attached to objects.

Both can be forced into submodels, and the earlier chat that advised
against BaSyx as the persistence layer was right: from an app's
perspective it is clumsy and, for the tree navigation that is the
whole point, slow. So: **standard outside, own model inside.** The AAS
repository API is a projection of the twin (own RFC); the twin itself
is the model below.

### Why now

Three RFCs have been waiting for this one. RFC-0022 drew the tenant as
the boundary "within which twin entities are visible" without saying
what an entity is. RFC-0012 reserved `consumes`, `contributes` and
`data_models` without meaning. RFC-0030 wrote the rule that shared data
holding must be copyable, before any existed. And the reference apps
Jörg wants next — partner management, staff, RACI, projects — are all
consumers of a thing that does not exist yet.

## 1. What is decided (restated from the interview of 2026-09-08)

These are Jörg's answers, given in five rounds, and this RFC builds on
them without re-arguing:

1. **Mirror and truth.** Apps deliver their objects and own them. A
   tenant may also create types and objects directly, without any app.
2. **One twin per tenant.** The tenant is the boundary; "universe" is
   not a word outside this document.
3. **Platform ID plus source keys.** Duplicates are detected; only a
   person merges.
4. **App core plus extension groups**, modelled on AAS submodels. The
   owning app's core is untouchable; contributors and the tenant write
   into their own groups on the same object.
5. **Without a specification there is only id and text.** Cross-app
   search helps and views get more fields only from a consolidated
   model the tenant owns.
6. **Time is a property of the type** — validity, planning, recorded
   time as each type needs, not one model for everything.
7. **Activities are first-class**, with an owner each; inbound messages
   become activities on the platform side.
8. **Push.** The app writes on change, single or batch.
9. **Contributors may write** — into their own group on a foreign
   object.
10. **PostgreSQL as a platform service**, one per node, a schema per
    tenant, pgvector for embeddings, dumpable for the rehearsal.
11. **Adopt the model, rebuild the implementation.** The Python service
    is the blueprint, not the code.
12. **The data belongs to the tenant.** Platform sub-models stay stable
    as views over app models; the mapping is what changes.
13. **Tooling at the app/platform boundary** solves four cases in five
    without the user; the fifth gets a simple dialog.

Deferred to their own RFCs, also decided: MQTT broker as a platform
service with the twin's topic tree as the unified namespace (RFC-0032);
automatic embedding and fuzzy search over the twin; AAS **API
conformity** (not just an exchange format); guaranteed delivery between
nodes; a twin browser as a platform app; data spaces last.

## 2. Three capabilities, not one

The proposal cuts along "what can be built, tested and left out on its
own":

| Capability | Answers | Holds |
| --- | --- | --- |
| **`oaap.data.model`** | *What kinds of things exist, and what do they mean?* | type definitions: object, attribute, group, relation, activity types; value types; the time model per type; optional semantic IDs; type origin and binding |
| **`oaap.data.store`** | *Where does shared data live, and how is it copied?* | a managed PostgreSQL per node; a schema per tenant and purpose; backup scope; the isolated copy for a rehearsal; also usable by apps that need Postgres |
| **`oaap.data.twin`** | *Which objects exist, who says what about them, and what held when?* | instances: objects, attributes, relations, activities in provenance groups; identity and merge; the write and read API; declarations in the manifest; the twin browser |

`oaap.data.model` has no instance data and no service of its own; it is
a registry the twin reads. `oaap.data.store` knows nothing about twins;
it hands out schemas and copies them. `oaap.data.twin` is the only one
an app talks to.

## 3. The model

### 3.1 Vocabulary

Nine kinds of record, in two layers. The **type layer** is the model;
the **instance layer** is the twin.

| Type (model) | Instance (twin) | What it is |
| --- | --- | --- |
| object type | **object** | a thing with identity: Customer, Person, Machine, Project |
| attribute type | **attribute** | a typed value with meaning: E-Mail, Location, SerialNo, Satisfaction |
| group type | **group** | a named bundle of attributes, relations and activities on one object, with one origin — the AAS submodel |
| relation type | **relation** | a directed, typed link between two objects, valid in time, with attributes of its own |
| activity type | **activity** | something that happens or is to be done, attached to an object: PhoneCall, Task, Project, InboundMail |

Every type has a key, a title (singular and plural), a description,
tags, and an **origin** (§4). Every instance has a platform ID, a type,
a title, an origin, and the time fields its type asks for (§3.4).

This is Jörg's universe model, minus the word "universe" (it is the
tenant now), plus one change: the **group** is no longer an afterthought
but the unit of ownership (§3.3).

### 3.2 Objects and their identity

An object is created once and referenced everywhere. It has:

- a **platform ID**: opaque, stable, unique across the installation,
  never reused, never changed (RFC-0026 applied to data). Format is a
  spec question; the recommendation is a UUID rendered as
  `urn:oaap:obj:<uuid>` when it leaves the platform, so a foreign system
  can tell it from its own keys;
- exactly one **object type**;
- one or more **source keys**: `(origin, key)` pairs — "in the CRM this
  is `C-1000`", "in the staff app this is `E-17`". An origin may hold at
  most one key per object; an object may have keys from many origins.
  That is how "two apps deliver the same customer" is stored, and it is
  the only way the twin knows the CRM's `C-1000` and the staff app's
  `E-17` are the same person: because someone said so (§3.6).

A source key is how an app finds its own objects again; the platform ID
is how everyone else does. **Apps store references, not copies** — an
app that needs a customer's name shows it from the twin or from its own
cache, never from a second master.

### 3.3 Groups: the unit of ownership

Everything said *about* an object lives in a group, and every group has
exactly one origin — the app, artefact or tenant that wrote it:

```
Customer  urn:oaap:obj:5f0e…   title "Müller Metallbau GmbH"
 ├─ group  crm.core          origin app:crm      (owner)
 │    attributes: Location=Magdeburg, VatId=DE…
 │    relations : ← isContactOf Anna (2019-01-01 …)
 ├─ group  raci.assignments  origin app:raci     (contributor)
 │    relations : → responsible Peter (2026-09-01 …)
 └─ group  tenant.satisfaction origin tenant      (tenant's own)
      attributes: Score=4, LastSurvey=2026-06
```

Rules:

- The **owner** of an object is the origin that created it. Its core
  group is the object's identity in practice: title, primary keys,
  the fields the owning app maintains. **Nobody else writes there.**
- A **contributor** writes into its own groups on a foreign object.
  It can never modify, hide or delete another origin's group.
- A **consumer** reads.
- The **tenant** is an origin like any other, with the difference that
  its groups are edited by people in the twin browser rather than by
  code. This is where "a data model without an app" lives — the
  satisfaction score in Jörg's example is a group type shipped as a
  `data_models` artefact and filled in by hand.

A group type declares which attribute, relation and activity types it
holds, so a group is not a bag but a small schema — the direct
counterpart of an AAS submodel template, which is what will make the
AAS projection cheap later.

### 3.4 Time

The earlier model had `valid_from`/`valid_to` on every attribute and
relation, and used it constantly: the tree showed what held at the
chosen date. The interview answer is more precise — *per type, as
needed* — and the recommendation (D5) makes it concrete with three
axes:

| Axis | Fields | On | Purpose |
| --- | --- | --- | --- |
| **recorded** | `recorded_at`, `recorded_by`, superseded-by | everything, always | *what did we know on day X* — audit, undo, the rehearsal's honesty |
| **validity** | `valid_from`, `valid_to` | attribute and relation types that opt in | *what held at time T* — the tree with a date slider; a contact that changes companies; a location that moves |
| **planning** | `planned_start`, `planned_end`, `started_at`, `finished_at` | activity types | *what is scheduled, what happened* — tasks, appointments, projects |

Recorded time costs nothing to keep in Postgres (append, never update)
and is what makes "what did the twin say last Tuesday" answerable
without a design change later. Validity is opt-in because most
attributes are simply current, and a history that nobody asked for is
noise in every tree. Planning belongs to activities and to nothing
else.

Validity may lie in the future: "Lisa is the technical contact from
next month" is a relation with `valid_from` ahead of today, visible in
the tree once the slider passes it.

### 3.5 Relations and activities

A **relation** is directed (`from` → `to`), typed, and belongs to a
group on the `from` object. It has validity if its type asks for it,
and it may carry attributes of its own — the e-mail address of a person
*in the role of* purchasing contact is an attribute of the relation,
not of the person. Relation types name both directions
("is contact of" / "has contact") so the tree reads correctly from
either end.

An **activity** is attached to one object (its subject) and may name a
second (its target: the complaint the phone call was about). It has an
owner like every instance; a task app owns its tasks, the CRM owns its
phone calls, and an inbound e-mail delivered to the platform's message
endpoint is an activity owned by the platform itself, with the raw
message referenced, not copied. Activities carry the planning axis and
a status; an activity type says whether it is a task (`is_task`, may
be closed) or an event (happened, cannot be closed).

### 3.6 Duplicates and merge

Two origins may create what is one thing. The twin must notice and must
not decide:

- **Detection** is a platform service: same source key from two
  origins, same normalised title within a type, same value of an
  attribute marked *identifying* (e-mail, VAT id, serial number). A
  detection produces a **candidate pair**, visible in the twin browser
  and to the owning apps, nothing else.
- **Merge is a human act**, recorded in the tenant's audit log
  (RFC-0022 §6). It keeps *both* platform IDs resolvable forever: one
  becomes canonical, the other an alias that answers every request with
  the canonical object. Groups of both objects are kept; nothing is
  overwritten. An app that stored the alias never breaks.
- **Unmerge** is possible while both objects' groups are still
  distinguishable by origin — which is always, because groups are never
  merged, only re-parented.

### 3.7 Semantics

An attribute type has an OAAP meaning by key and title. It **may** carry
a semantic ID from ECLASS, IEC CDD or an AAS Concept Description; the
platform stores and exports it and never requires it. This is what keeps
the model usable for a five-person company on day one and
standard-conformant on the day a partner asks.

## 4. Where types come from (D1, D2)

Three origins, and the origin is part of the type's name:

| Origin | Namespace | Ships as | Changed by |
| --- | --- | --- | --- |
| an app | `app:<app-id>` | the app package's manifest section `data_model` | a new version of that app |
| a data-model artefact | `model:<artefact-id>` | a `data_models` entry in a store list (RFC-0012 §8.5), a package with types only, no service | a new version of the artefact |
| the tenant | `tenant` | created in the twin browser | the tenant's admin, in the browser |

**D1 recommendation:** only the origin changes its types, and only by
shipping a new version. An app cannot alter a type the tenant made; the
tenant cannot alter a type the CRM shipped — it can only add its own
group type to the CRM's object type. That is what makes the "app core
plus extension" rule enforceable instead of polite.

**D2 recommendation:** a type *definition* is registered on the node
when its package is installed, once, regardless of how many tenants
exist. A tenant's twin *activates* the types its installed instances
contribute or consume, and holds instances only for those. Two tenants
with the same CRM installed share the definition and nothing else. This
follows the RFC-0022 rule that no app learns of tenants: the CRM ships
one model, the platform keeps the tenants apart.

**When a package changes its model** (the migration question Jörg
raised): the new version ships the new definition; the platform
compares, applies additive changes silently (a new attribute type, a
new group type), and refuses destructive ones (a removed type with
instances, a changed value type) until the app declares a migration for
its own groups. This is the same shape as RFC-0030's reason for
existing, one level down — and the rehearsal is where such a change is
tried first (D8).

## 5. The boundary: what an app declares (D4, D6, D7)

Two manifest sections, using the names reserved in RFC-0012 §8.3:

```yaml
data_model:                 # types this app ships (origin app:crm)
  object_types:
    - key: Customer
      title: Kunde
      title_plural: Kunden
      identifying: [VatId, Email]
    - key: Person
      ...
  group_types:
    - key: crm.core
      on: Customer
      attributes: [Location, VatId, Phone]
      relations: [isContactOf]
      activities: [PhoneCall]
  attribute_types: ...
  relation_types: ...
  activity_types: ...

contributes:                # what this app writes
  - type: Customer          # owner: it creates Customers
    role: owner
  - type: Person
    role: owner

consumes:                   # what this app reads
  - type: Project
    as: Projekt             # the app's own word for it (D4)
    fields: [reference]     # D6: reference only
```

and, for the RACI app:

```yaml
contributes:
  - type: Customer
    role: contributor
    group: raci.assignments
consumes:
  - type: Customer
    as: Kunde
  - type: Person
    as: Mitarbeiter
    fields: [reference, Email]   # more than a reference: needs a consolidated model
```

**D4 — binding.** `as: Kunde` is the app's word; `type: Customer` is
the platform's. At install time the platform binds each `consumes` and
`contributes` entry to a type that exists on the node: automatically
when the key or an alias matches (case-insensitively, across the
registered aliases of the type), otherwise the install dialog asks the
operator to pick — the same place RFC-0012 puts a missing dependency:
declared, shown, offered, never silently resolved, never blocking. The
binding is configuration of the instance and is shown on its page.
Jörg's filters ("this app sees only customers of region North") are a
later refinement of the same binding record, not a new concept.

**D6 — what a consumer gets by default.** A **reference**: platform ID,
type, title, origin, and the source key *of the consumer's own origin*
if it has one. This is the list box and the search help. Any field
beyond that must come from a **consolidated model**: a group type the
tenant owns (`tenant` origin or a `data_models` artefact) that names
which attributes of which groups form the cross-app view of a type. The
consumer then reads the consolidated group, never another app's core.
This is Jörg's sentence made mechanical: *without a specification there
is only id and text.*

**D7 — who may read.** Within a tenant, reading is by declaration: an
instance may read the types it consumes, all groups of them, except
groups whose type is marked `restricted`, which only the owning origin
and origins it lists may read. Every declaration is shown **before
installation** in the words of the platform ("This app reads customer
and person master data and adds RACI assignments to customers") — the
phone-permissions pattern from the idea log. Writes are by declaration
too, and always into the writer's own groups.

## 6. Interface sketch

One internal service per node, reached over the platform network; the
caller is an **instance**, identified by its own credential (the machine
principal of RFC-0027, issued per instance at install). Tenant and
origin come from the credential, never from the request. The full
interface is the capability spec's job; the shape is:

| Verb | Path | What |
| --- | --- | --- |
| `GET` | `/twin/types` | the types active for this tenant, with the caller's bindings |
| `POST` | `/twin/objects` | create an object (caller becomes owner) with its core group |
| `GET` | `/twin/objects/{id}` | the object with the groups the caller may read; `?at=` for validity |
| `PUT` | `/twin/objects/{id}/groups/{group}` | replace the caller's own group on any object |
| `POST` | `/twin/objects/{id}/relations`, `/activities` | add into the caller's group |
| `GET` | `/twin/objects/{id}/tree?at=&depth=` | the navigation tree: relations valid at `at`, expanded to `depth` |
| `GET` | `/twin/references?type=&q=` | the search help: references matching `q` (id and text) |
| `POST` | `/twin/batch` | many of the above in one call — the sync case |
| `GET` | `/twin/candidates` | duplicate candidates the caller's objects are part of |

Every write is recorded (§3.4) and produces an event; RFC-0032 says
where the event goes. Reads are plain; the twin browser uses the same
API with a person's session instead of an instance credential.

## 7. The store and the copy (D8)

`oaap.data.store` is a managed PostgreSQL on the node: one server,
one database, a **schema per tenant and purpose** (`twin_<tenant>`,
later `app_<instance>` for apps that ask for Postgres). Its backup
scope is the whole server (RFC-0029 adds it to the required content);
its restore is a database restore.

**D8 — the rehearsal.** RFC-0030 D6 says shared data holding must be
able to make an isolated copy of itself or refuse. The store answers
with a schema copy: `twin_<tenant>` → `twin_<tenant>_r_<instance>`,
made at rehearsal creation, bound to that one rehearsal instance,
deleted with it. The rehearsal sees the whole tenant twin as of the
copy and writes only into its copy; nothing it does reaches production.
If the copy fails (space, a migration in flight), the rehearsal is
refused with the reason named — the RFC-0030 rule word for word.

This is honest but not small: a rehearsal of one app copies the whole
tenant twin, because the twin has no per-app slice — that is its point.
The size is shown before the copy, as RFC-0030 already does for the
directory.

## 8. Security requirements

- The caller's tenant and origin come from its credential; a request
  that names a tenant is rejected. No app learns of tenants (RFC-0022).
- A write outside the caller's own groups is rejected and logged as an
  event in the tenant's audit log.
- Merge, unmerge and type activation are person actions and land in
  the tenant's audit log with who, when, what.
- Restricted groups are enforced on read at the service, not by the
  client.
- Instances of one tenant never see objects of another; the schema per
  tenant makes this structural, not a filter.

## 9. Conformance, in one scenario

The reference apps Jörg named are the test:

1. **Partner management** (owner) creates Müller GmbH and Anna, relates
   them with `isContactOf` valid from 2019.
2. **Staff management** (owner) creates Lisa as an employee.
3. **RACI** (contributor) reads both as references, writes
   `responsible` relations into `raci.assignments` on Müller GmbH.
4. **Projects** (owner) creates a project; partner management creates
   another; both are objects of type Project with different origins.
5. **Satisfaction** (`data_models` artefact, tenant origin) adds a
   group type on Customer; a person fills it in the twin browser.
6. A duplicate candidate appears when staff management creates
   "Anna Müller" with Anna's e-mail; a person merges; the CRM's
   reference still resolves.
7. The tree of Müller GmbH at 2024-01-01 differs from today's.
8. A rehearsal of partner management sees the twin and changes nothing
   in production.

Each step is one conformance test; steps 1–3 are the minimum for the
first build.

## 10. Non-goals

- **Events and states** — RFC-0032. This RFC only says every write is
  recorded and emits one.
- **Search and embeddings** — own spec; depends on RFC-0023.
- **The AAS repository API** — own RFC, as a projection of §3.
- **Guaranteed delivery, edge nodes, twin sync to a plant node** —
  own RFC; needs RFC-0032 first.
- **Workflows and agents** — `kind: Agent`, idea log.
- **Data spaces** — last, with a real partner.
- **Connectors to foreign systems** (M365, DATEV, OPC UA) — idea log.

## 11. Build order

1. `oaap.data.store`: Postgres as a platform service, schema per tenant,
   in the backup, schema copy for the rehearsal. Testable alone.
2. `oaap.data.model`: type registry from packages and from the tenant,
   bindings at install, the install dialog.
3. `oaap.data.twin`: objects, groups, relations, activities, recorded
   time, validity, references, tree — behind the API of §6.
4. Partner management and RACI as the first owner/contributor pair;
   then staff, projects, satisfaction.
5. The twin browser in the portal — tree, date slider, timeline, and
   the tenant's own types.
6. Then RFC-0032.

---

## Deutsche Zusammenfassung

**Worum es geht.** Heute besitzt jede App ihre Daten vollständig und
teilt nichts. Für die Isolation ist das richtig; für das, was ein
kleines Unternehmen wirklich braucht, ist es falsch: Der Kunde, den das
CRM kennt, ist derselbe, den Projekt-App, Reklamations-App und RACI-App
meinen — und heute tippt ihn jede neu ein. Dieser RFC schlägt den
**digitalen Zwilling** vor: **eine gemeinsame Datenebene je Mandant**,
in die Apps ihre Objekte liefern und aus der jede App, jeder Agent und
jeder Mensch dieses Mandanten liest. Grundlage ist Jörgs
Universums-Modell — mit dem, was die Verwaltungsschale nicht kann:
**zeitgültige Beziehungen mit eigenen Attributen und Aktivitäten als
Bürger erster Klasse.** Außen der Standard (AAS-API, eigener RFC),
innen das eigene Modell.

**Was schon entschieden ist** (Interview vom 08.09., §1): Spiegel *und*
Wahrheit; ein Zwilling je Mandant; Plattform-ID plus Quellschlüssel,
Zusammenführen nur durch Menschen; App-Kern plus Herkunftsgruppen nach
AAS-Vorbild; ohne Spezifikation nur ID und Text; Zeit je Typ; Push;
Postgres als Plattformdienst; Modell übernehmen, neu bauen; die Daten
gehören dem Mandanten.

**Drei Capabilities** (§2): `oaap.data.model` (Typen und Bedeutung, kein
eigener Dienst), `oaap.data.store` (verwaltetes Postgres, Schema je
Mandant, kopierbar), `oaap.data.twin` (die Instanzen, die API, der
Zwillings-Browser). Nur mit dem Zwilling spricht eine App.

**Das Modell** (§3): Objekt-, Attribut-, Gruppen-, Relations- und
Aktivitätstypen; jede Aussage über ein Objekt liegt in einer **Gruppe
mit genau einer Herkunft** (App, Artefakt, Mandant) — das AAS-Submodell
als Einheit des Besitzes. Der Owner-Kern ist unantastbar, Contributor
und Mandant schreiben in eigene Gruppen. Drei Zeitachsen: **Erfassung
immer**, **Gültigkeit** je Attribut-/Relationstyp auf Wunsch,
**Planung** an Aktivitäten. Dubletten erkennt die Plattform, ein Mensch
führt zusammen; beide IDs bleiben für immer auflösbar.

**Die acht offenen Entscheidungen**, jede mit Empfehlung:

- **D1 — Woher kommen Typen, wer ändert sie?** Drei Herkünfte mit
  Namensraum (`app:`, `model:`, `tenant`); nur die Herkunft ändert ihre
  Typen, und nur über eine neue Version.
- **D2 — Definition je Knoten oder je Mandant?** Definition je Paket,
  Aktivierung je Mandant. Keine App erfährt von Mandanten.
- **D3 — Identität und Zusammenführen?** Opake Plattform-ID plus
  beliebig viele Quellschlüssel; nach dem Merge bleibt die zweite ID als
  Alias für immer auflösbar.
- **D4 — „Kunde" trifft „Customer"?** Bindung bei der Installation:
  automatisch bei passendem Key oder Alias, sonst fragt der
  Installationsdialog. Nie still, nie blockierend. Jörgs Filter als
  spätere Verfeinerung desselben Bindungssatzes.
- **D5 — Welche Zeitachsen?** Erfassung immer, Gültigkeit je Typ,
  Planung an Aktivitäten.
- **D6 — Was bekommt ein Verbraucher ohne Spezifikation?** Eine
  **Referenz**: ID, Typ, Titel, Herkunft. Mehr nur über ein
  konsolidiertes Modell des Mandanten.
- **D7 — Wer darf was lesen?** Lesen nach Erklärung im Manifest,
  mandantenweit; Gruppen können `restricted` sein. Alles vor der
  Installation in Klartext angezeigt.
- **D8 — Wie kopiert die Generalprobe den Zwilling?** Schema-Kopie des
  Mandanten-Zwillings, an die eine Probe-Instanz gebunden, mit ihr
  gelöscht. Scheitert die Kopie, scheitert die Probe — mit Grund.

**Reihenfolge** (§11): Store, Modell, Zwilling, Partnerverwaltung +
RACI, dann Mitarbeiter/Projekte/Zufriedenheit, dann der Browser, dann
RFC-0032. Die acht Schritte in §9 sind die Konformitätsprüfung; die
ersten drei das Minimum für den ersten Bau.

**Entschieden am 08.09.2026, alle acht nach Empfehlung** — siehe
Decision record.

## Decision record (2026-09-08)

Decided by Jörg in form mode, the same evening the draft was written;
every recommendation followed.

- **D1 — three origins, only the origin changes its types.** App
  package (`app:`), data-model artefact (`model:`), tenant (`tenant`),
  each a namespace; a type changes only by a new version of its origin;
  others attach their own group types.
- **D2 — definition per package, activation per tenant.** Installing
  registers types once on the node; a tenant's twin activates what its
  instances contribute or consume. No app learns of tenants.
- **D3 — opaque ID plus source keys; a merged ID stays resolvable.**
  UUID as platform ID, at most one source key per origin; a merge makes
  one ID canonical and keeps the other as an alias forever; groups are
  re-parented, never merged.
- **D4 — binding at install, dialog when in doubt.** Automatic on a
  matching key or alias, otherwise the install dialog asks — declared,
  shown, offered, never silent, never blocking. Filters are a later
  refinement of the same binding record.
- **D5 — recorded time always, validity per type, planning on
  activities.** Writes append, never overwrite; `valid_from`/`valid_to`
  only on attribute and relation types that opt in; planning fields on
  activities only.
- **D6 — the reference, and nothing else, without a specification.**
  Platform ID, type, title, origin, the consumer's own source key. More
  only through a consolidated model the tenant owns; a consumer never
  reads a foreign core group directly.
- **D7 — reading by declaration, with restricted groups.** An instance
  reads the types it consumes; a group type may be `restricted` to its
  origin and named readers; everything is shown in plain words before
  installation.
- **D8 — the rehearsal copies the tenant's twin schema.** Bound to the
  one rehearsal instance, deleted with it, size shown beforehand; a
  failed copy refuses the rehearsal with the reason named.

### What follows

The build order of §11 stands. First the capability spec
`oaap.data.store` (the only piece with no design risk left), then
`oaap.data.model` and `oaap.data.twin` as drafts, then RFC-0032 for the
events every write emits.
