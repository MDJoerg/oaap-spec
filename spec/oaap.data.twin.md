# oaap.data.twin — The Digital Twin

- **ID:** `oaap.data.twin`
- **Version:** 0.13 (0.13: **modelling and sync** -- an integration client may write (`writes`) and model (`models`): types of its tenant with the object type in the tenant's namespace, upsert by its own key, its own groups and periods, batches under an id, retiring the objects it owns, renames by the owner; webhooks for the changes it may read, signed, in order, with retries; every current read leaves a retired object out (§2.22-2.25); RFC-0120 stage 3, reference 0.1.349; 0.12: **values in time** -- values checked against the registry's value types on every door (§2.19); **periodic attributes**: several values of one attribute coexist, each for a period with unit, source and quality, written as periods and read per period (§2.20); the time series readable by persons and integration clients (§2.21); RFC-0120 stage 2, reference 0.1.348; 0.11: **reads of the door `/twin/v1`** -- filtered lists with a cursor (`where` checked against the registry's value types), one object, neighbourhood, shortest paths, export (JSON, GraphML; personal attributes left out), change feed; every read answers as the twin looked at one moment `at` (date-time; recorded time and validity), only objects of the caller's types, an edge only between visible objects; §2.18, RFC-0120 stage 1, reference 0.1.347; 0.10: **integration clients and the door `/twin/v1`** -- `client:<label>`, a program outside the platform in one tenant, reading exactly the types the operator bound it to (`oaap data twin add-client --tenant --reads`, key scoped `oaap.twin`, shown once, at most 365 days); `GET /twin/v1/types` (the caller's bound types with access read/write and `semantic_iri`) and `GET /twin/v1/openapi.json` (OpenAPI 3.1 of the door as the caller sees it), for every twin principal; a client writes nothing yet, §2.17, RFC-0120 stage 0, reference 0.1.346; 0.9: 0.9: the twin as an MCP source -- every MCP gateway of the tenant finds the source `twin` with three read tools, carried as the signed-in person, §2.16, RFC-0118 P6, reference 0.1.341; 0.8: the list searches and pages -- `q` matches words in the title, `offset` skips rows; an app's list report no longer reads all and cuts at 500, §2.6a, RFC-0118 P6, reference 0.1.340; 0.7: `GET /twin/objects?type=` -- an app lists every object of a type it is bound to, §2.6a, RFC-0085 §10, reference 0.1.293; 0.6: the read `affected` -- what depends on a fleet object, §2.10a, RFC-0087 §6, reference 0.1.285; 0.5: the write rules in one module shared by the API and the platform's own writer; an unchanged **relation** writes nothing either, and a group PUT that changes nothing records no event -- §2.15; the person-facing type list answers `semantic_iri` -- `oaap.data.model` 0.2 §2.9; RFC-0085 amendment A2)
- **Maturity:** draft
- **Based on:** RFC-0033 §6 / D10 (0.4 adds the remote reader, §2.14:
  a reader on another node, reached through a tunnel,
  `oaap.net.connector`); RFC-0032 (events, states and the unified namespace — 0.3
  builds its build-order step 2: the outbox relay and the `states`
  table, §2.13; relay decisions of 2026-09-12 recorded there);
  RFC-0031 (data model & digital twin — Twin is Schritt 3
  of the build order: Store, Model, Twin, reference apps, browser, then
  broker) §3, §6, §8, §9; `oaap.data.store` (every tenant's twin is a
  schema in it); `oaap.data.model` (the registry this service reads —
  and, since 0.2, also writes one row into, §2.11); RFC-0027 (machine
  principals — an instance authenticates as itself); RFC-0016 (app
  network isolation — why this service sits behind the gateway, not
  beside the app); RFC-0015 addendum A4 (the `/internal/*` guard
  pattern 0.2 reuses for the portal, §2.12)

## 1. Purpose

The **only service an app talks to for shared tenant data** (RFC-0031
§2). It answers *which objects exist, who says what about them, and
what held when?* — the instance layer beneath `oaap.data.model`'s type
layer. An owner creates an object with its own core group; a
contributor writes into its own group on someone else's object; a
consumer reads. Origin and tenant come from the caller's own
credential, never from anything the request says (§4).

**0.1 built RFC-0031 §9's own minimum**: steps 1–3 of the eight-step
conformance scenario — an owner creates an object with its core group;
a reader gets an object back with every group its type is bound to;
a contributor writes into its own group on a foreign object. Recorded
time is kept always (append, never overwrite, §2.3).

**0.2 builds the Bauplan's Schritt 5 (the twin browser) on top,
additively — nothing 0.1 could already do is narrowed:**

- **`?at=`** (§9 step 7's first half) — validity filtering on every
  read, shared by the app-facing and the new person-facing routes
  alike (§2.8).
- **Merge and unmerge** (§9 step 6, §3.6) — an `aliases` table, human-
  triggered candidate detection, and transparent resolution on every
  read and write: an id that was merged away keeps answering, forever
  (D3), and groups of both objects are kept and shown together (§2.9).
- **A second authentication path**, `/internal/*`, for the portal
  only — never through the gateway, never with an RFC-0027 key. The
  portal already authenticates the actual person; this service only
  re-checks their ROLE per action (§2.12, §4).
- **Tenant type creation** (Bauplan Schritt 5: "Typen des Mandanten
  anlegen") — deliberately narrow: a tenant_admin may add a new GROUP
  type (plus the attribute types it needs) onto an object type that
  already exists, never a new object type, never a change to one that
  already exists (§2.11).
- **A tree** (§9 step 7's second half), built by repeated reads, not a
  recursive CTE — correct at this scale, revisited only if it becomes
  slow (§2.10).

**0.3 builds RFC-0032's build-order step 2 — the other end of the
outbox, additively again:**

- **The outbox relay** — a second process from the same image, its own
  compose service `relay`, carried by the node profile `broker` (not
  `store`): it publishes every `events` row to `oaap.events.broker`,
  retained, on the twin's topic tree (§2.13).
- **`states`** — one row per published group change, holding that
  group's attribute snapshot; written only by the relay (§2.13).
- **`GET /internal/twin/outbox`** — per tenant, how many events wait and
  when the relay last reported, for the portal's health page (§2.13,
  `oaap.core.portal` 2.5).

Concretely still NOT built, named here rather than silently missing:

- **`/twin/references`** (fuzzy search over titles/source keys, D6's
  reference tuple) — still nothing to search.
- **Restricted groups** (D7's second half) — the read rule is still the
  simple half only: an instance may read every group of a type it
  contributes to or consumes, and a person sees every group of their
  own tenant's object; marking one group `restricted` to named readers
  is still not implemented.
- **The rehearsal's own schema copy** (D8, §9 step 8) — unchanged from
  0.1: a rehearsal instance still gets no twin credential at all,
  deliberately (§2.2, §4).
- **The outbox reader** (RFC-0032) — every write still appends one
  `events` row (§2.3); nothing reads that table yet.
- **The AAS repository API** (own, later RFC) reads this service's
  model; it does not exist yet.

## 2. Interface

### 2.1 Where the twin lives

One schema per tenant in `oaap.data.store`'s Postgres, `twin_<tenant-
id>` — never the tenant's Kürzel (RFC-0025/0026, the same rule
`oaap.data.store` and `oaap.data.model` already apply). Its own
Postgres role, created and its password shown exactly once, exactly as
`oaap.data.store` 0.1 §2 already promises: "never for an app, only for
`oaap.data.twin`." In 0.1 that promise is kept literally — the
password is written straight into a root-only file
(`apps/twin-secrets.json`, `0600`) that only this service's own
container mounts, never printed to a terminal, never touched by
`appctl` again after it is written.

The service itself is a small platform container (`twin`, like
`identity`/`portal`), gated by the SAME node profile as `oaap.data.store`
(RFC-0011) — `docker-compose.yml`'s `profiles: ["store"]` on both, so
one `oaap node add-profile store` starts both halves of the capability
and one `remove-profile` stops both. It is reached **only** through the
gateway's `/twin/*` route (`Caddyfile`) — an app instance's own network
(RFC-0016) cannot see the `twin` container directly, so there is no
other path in.

### 2.2 Authentication (RFC-0031 §8, E1)

An instance that `contributes` or `consumes` a type (`oaap.data.model`
manifest sections) is issued a machine principal `instance:<name>`
(RFC-0027 3.1) and an API key for it, at install time, minted once and
never rotated by a later redeploy — the same stability rule
`OAAP_APP_SECRET` already follows. The key arrives in the container as
`OAAP_PLATFORM_KEY`; `OAAP_TWIN_URL` (`http://<gateway>/twin`) says
where to send it. Both are platform-owned and refused by `oaap app
config` like `OAAP_APP_SECRET` already is.

**`OAAP_TWIN_URL` already ends in `/twin`.** The Caddyfile's `handle
/twin/*` block forwards the path unchanged (no `strip_prefix`) because
this service's own Flask routes are registered with that prefix
(`/twin/objects`, not `/objects`) — so a caller appends only the
sub-path §2.4–§2.7 name (`{OAAP_TWIN_URL}/objects`, `{OAAP_TWIN_URL}
/objects/{id}`, …), never a second `/twin` segment. This section's own
route headers below name the path as reached from the gateway's root
for readability, which reads as "append the whole thing" if not read
this closely — exactly the mistake Partnerverwaltung's first build made
against the real service on `oaap-test` (RFC-0031 Schritt 4,
2026-09-10): a 404 from THIS service's own Flask app, not from the
gateway or `identity`, is the tell that the path was doubled, not the
auth.

The key **is** issued with RFC-0027's `--instance` scoping (D5) — to
`oaap.twin`, a reserved value, never the calling app's own name. This
was not the first version of this section: 0.1's first build left the
key unscoped, reasoning that "nothing else on the node was ever issued
`instance:<name>`'s key" is what limits it. That answers who can
*present* the key, not *where* `identity`'s `/verify` accepts it —
without a `--instance` value, a key is refused nowhere but by role and
tenant (D5 exists precisely because an app's own site always names
itself in its `forward_auth` call). An unscoped twin key therefore
authenticated against every *other* app's own route asking only role
`user` in the same tenant, not only `/twin/*` — found live on
`oaap-test` (RFC-0031 Schritt 3's own live verification, 2026-09-10) by
testing the very claim this paragraph used to make. `oaap.twin` closes
it the same way D5 closes it everywhere else, and can never collide
with a real app: `app.id` matches `[a-z0-9][a-z0-9-]{1,38}[a-z0-9]`,
which never contains a dot. `twin` additionally refuses any caller
whose verified principal does not start with `instance:` — a human
session reaching this route, however it got the header, is refused
outright; this is defense in depth, not a substitute for the scoping
above.

A **rehearsal instance gets neither.** D8 (a rehearsal's own copy of
the tenant's twin schema) is not built; the tenant's `twin_<id>` schema
is the production one, so a rehearsal that could reach it would read
and write live customer data — exactly what RFC-0030 exists to
prevent. `appctl` therefore does two things, not one: the copied
`instance.env` a rehearsal starts from has `OAAP_PLATFORM_KEY`/
`OAAP_TWIN_URL` scrubbed before anything is installed (same function
that already scrubs `OAAP_APP_SECRET` and manifest-declared secrets),
and the install that follows does not mint a replacement for a
rehearsal either. The app simply cannot reach `oaap.data.twin` from a
rehearsal in 0.1 — honestly, not silently.

**0.4: a second kind of caller, `remote:<label>`** — a reader on
another node (§2.14). Everything above holds for it: it presents an
RFC-0027 key scoped to `oaap.twin`, and the tenant comes from the
principal, never from the request. What changes is where the name is
looked up.

### 2.3 The model in 0.1

Per tenant schema: `objects`, `source_keys`, `groups`, `attributes`,
`relations`, `activities`, `events` — every one **append-only**
(RFC-0031 §3.4 D5, "recorded time always"): a write is a new row; an
old value is marked `superseded_by` the new row's id, never deleted,
never edited in place. `current_attributes`/`current_relations`/
`current_activities` are views (`WHERE superseded_by IS NULL`) — the
service reads only these, never the base tables, for exactly the
reason RFC-0031's bauplan names: "die Sichten sind kein Komfort,
sondern die API."

A **group** is the unit of ownership (§3.3): recorded once, with the
origin that first wrote it, and never reassigned. `attributes`/
`relations`/`activities` all carry `valid_from`/`valid_to` (nullable,
unfiltered in 0.1 — see §1) and `recorded_at`/`recorded_by` always.
`relations` point at a second object (`target_id`); `activities`
optionally name one as their target and carry a `status` plus the
planning fields RFC-0031 §3.4 reserves for them, though nothing in 0.1
updates a status after creation. `events` records `kind`/`object_id`/
`group_key`/`origin` on every write — the outbox (§1). Since 0.3 two
more tables sit beside them, `states` and `relay_watermark`, both
belonging to the outbox relay (§2.13).

`oaap.data.model`'s tables (`oaap_model.*`) are read directly, with a
`GRANT SELECT` given to every tenant's schema role at provisioning
time — "a registry the twin reads" (RFC-0031 §2), taken literally.

### 2.4 `GET /twin/types`

The types active for the caller's tenant, and the caller's own
bindings (`oaap_model.bindings WHERE instance = <caller>`) — what this
instance may create, read or write, in its own words, without it
having to keep its own copy of the manifest it was installed from.

### 2.5 `POST /twin/objects`

Create an object. Body: `{"type", "title", "source_key"?, "group":
{"key", "attributes"?, "relations"?, "activities"?}}`. Refused unless
the caller holds a `contributes` binding with `role: owner` for
`type` (RFC-0031 §3.3: "the owner is the origin that created it").
Writes the object row, an optional source key, the named group as the
owner's core group, its attribute/relation/activity rows, and one
`events` row. Returns `{"id": "urn:oaap:obj:<uuid>"}` — the exported
form RFC-0031 §3.2 recommends; the bare UUID is accepted back on every
read/write endpoint too.

### 2.6 `GET /twin/objects/{id}`

Refused unless the caller's bindings include `type_key` in **either**
direction (`contributes` or `consumes`) — RFC-0031 D7's simple half:
"an instance may read the types it consumes, all groups of them."
Returns the object's header and every group that exists on it, each
with its current attributes, relations and activities. No `restricted`
filtering still (§1). `?at=` is honoured since 0.2 (§2.8); if the
requested id was merged away, the object answers as its canonical
object instead, with a `merged_from` field naming the id it was asked
under (§2.9) — the request never fails just because the id it named no
longer stands alone.

### 2.6a `GET /twin/objects?type={key}` — every object of a type (0.7)

The list beside §2.6, for an app that holds no ids yet (RFC-0085 §10:
the fleet app reads the fleet from its tenant's twin). The same rule as
§2.6: refused (403) unless the caller's bindings name `type` in either
direction; a remote reader (§2.14) reads the types it was given. `?type=`
missing → 400. Answers `{"objects": [...], "truncated": bool}`, each
object exactly as §2.6 answers it (header and every group with its
current attributes, relations and activities), ordered by title; `?at=`
is honoured (§2.8). A merged-away alias is no row of its own (§2.9). At
most 500 objects; a longer list says `truncated: true` rather than
cutting silently. No filter on group or value in 0.7 -- the fleet of a
few nodes is small, and a query language is a later question.

**Search and pages (0.8, RFC-0118 P6).** `?q=` keeps the objects whose
title contains every word of it (case-insensitive, at most eight words,
`%` and `_` taken literally); `?offset=n` skips the first `n` rows of the
same order. The answer carries `offset`. A list report asks for one page
at a time and offers "Weitere" while `truncated` is true. Still no filter
on group or value.

The tenant is the caller's, as everywhere: an app of tenant B bound to
the same type lists tenant B's objects -- an empty list, never tenant
A's (measured on oaap-test, 2026-11-15: FleetView installed in a second
tenant of the same node read nothing).

### 2.7 `PUT /twin/objects/{id}/groups/{group}`

Write into one group. Refused unless the caller `contributes` to the
object's type. If the group already exists under a **different**
origin, refused — RFC-0031 §3.3's "nobody else writes there," enforced
here, not trusted from the caller. Otherwise creates the group (first
writer becomes its origin) or appends to it: each attribute/relation
key is compared to its current row, and a value that has not actually
changed writes nothing — the history stays honest, not a row per
identical PUT. Records one `events` row. Returns `204`. Since 0.2, the
object id (and a relation's own target id, §2.9) is resolved through a
merge first — a contributor holding an id from before a merge keeps
writing into the right place.

### 2.8 `?at=` — validity (§9 step 7's first half)

Every app-facing AND person-facing read accepts `?at=<YYYY-MM-DD>`. A
day, not a moment — the date slider Schritt 5 asks for offers exactly
that, and it is the only granularity RFC-0031 §3.4's validity axis
needs. An attribute or relation row is included only if `valid_from`
(when set) is on or before `at`, and `valid_to` (when set) is strictly
after it — the same half-open interval the earlier model used. An
unparsable `?at=` is treated as "now" (no filter), not as an error, the
same tolerant reading this platform already gives an unrecognised
store-list field.

### 2.9 Merge and unmerge (§9 step 6, §3.6)

An `aliases` table per tenant schema (`alias_id` primary key,
`canonical_id`, `merged_at`/`merged_by`, `unmerged_at`/`unmerged_by`
nullable): `alias_id` stops being its own object and answers as
`canonical_id` from then on, forever resolvable (D3). Unmerge sets
`unmerged_at` rather than deleting the row, so a merge's history
survives being undone.

Detection (`GET /internal/twin/candidates`, person-facing only) is a
platform hint, nothing more (§3.6): the SAME normalised title, created
by DIFFERENT origins, neither already merged away. Merge (`POST
/internal/twin/merge`, body `{"keep", "drop"}`) and unmerge (`POST
/internal/twin/unmerge`, body `{"drop"}`) are human acts, `tenant_admin`
only, each recording one `events` row with `origin:
"tenant:<username>"` so the audit trail names who acted, not only that
a write happened.

**Deliberately not restricted to one type**, on EITHER end (detection
or merge itself) — an earlier build did restrict both, on the reading
that a cross-type merge is "a mistake, not a duplicate." That reading
did not survive contact with the reference scenario this step exists
to resolve (RFC-0031 Bauplan Schritt 4, 2026-09-10): Mitarbeiterverwal-
tung creates "Anna" as a `Mitarbeiter` (owner `app:mitarbeiterverwal-
tung`), independently of Partnerverwaltung's existing "Anna" as a
`Kontaktperson` (owner `app:partnerverwaltung`) — the SAME real person,
TWO DIFFERENT types, because neither app knows the other's model. A
same-type restriction would have made this service unable to surface,
let alone resolve, the one duplicate it was named for — found live on
`oaap-test` while verifying this step, before the candidate list was
ever shown to a person. The canonical object's own type is what every
future read reports; the merged-away object's groups are kept and
shown alongside it regardless, since the loader below unions by object
id, never by type.

Every read (app- and person-facing) resolves a requested id to its
canonical id FIRST, then loads groups from the union of the canonical
id and every id merged into it: "groups of both objects are kept;
nothing is overwritten" (§3.6), literally. A group_key collision
between the two objects' own groups (only possible after a merge —
"nobody else writes there" only ever protected ONE live object) is
resolved by suffixing the second occurrence with a short form of its
own object id, so nothing is silently dropped; this never fires for an
object that was never merged.

### 2.10 `GET /internal/twin/objects/{id}/tree?at=&depth=` — the tree

Person-facing only (§2.12's authentication path applies). Follows
relations outward from one object, depth-limited (default 2, max 5),
`?at=` applied at every hop, built by repeated calls to the same
loader §2.9 uses — not a recursive CTE. Correct, not yet fast; revisit
only if it becomes slow at the size this platform actually runs at.

### 2.10a `GET /internal/twin/objects/{id}/affected` — what depends on it (0.6)

Person-facing only, like the tree. From one fleet object (RFC-0087), the
open relations read **backwards** — `usesTunnel`, `usesExternal`,
`behind`, `reaches`, `bindsTo` — breadth first, each object once, at most
200 rows (`truncated` says so). Every row carries kind, title, node, the
tenant (`heldBy`, `destOf`), its distance, the relation it was reached by
and the row it depends on; `tenants` sums them up, and a tunnel names its
two ends. A tunnel that *reaches* an affected instance is listed as a
whole: the twin does not know which of its offers a destination calls, so
such a row reads "possibly affected". Today's state only (no `?at=`). The
walk is one pure function the hub's fleet service also uses for its
`link.down` matter (`oaap.core.notifications` 0.8), so the page and the
mail never disagree. Not a fleet object: 404.

### 2.11 `POST /internal/twin/types` — tenant type creation

Bauplan Schritt 5: "Typen des Mandanten anlegen." Deliberately narrow,
to RFC-0031 §9 step 5's own example and nothing wider: `tenant_admin`
only, body `{"on", "group_key", "group_title"?, "attributes": [{"key",
"title"?, "value_type"?}]}` — a brand-new GROUP type (plus the
attribute types it needs), attached to an OBJECT type that already
exists and is already active for the tenant. Refuses outright if the
object type is not active, if the group key is not `namespace.name`
lowercase, or if ANY of the new keys already exist anywhere in the
registry — **create only**, never a version diff: `oaap.data.model`'s
own additive/destructive comparison (`type_change_kind`) stays
exclusively `appctl.py`'s code path, run by a human on the host, never
reachable from a tenant's own session. A person adding one group to an
existing object type — the ONE case RFC-0031 §9 actually names — is
enough for this step; a new OBJECT type, or a CHANGE to an existing
one, from the browser is explicitly deferred, not half-built.

The new rows are written with `origin: "tenant:<tenant-id>"` (never the
bare word `"tenant"` — see `oaap.data.model` 0.2's own Nachtrag for
why) through the SAME per-tenant Postgres role every other write in
this tenant's schema already uses, granted `INSERT` (never `UPDATE`/
`DELETE`) on `oaap_model.type_definitions`/`activations` for exactly
this purpose (§4).

### 2.12 The person-facing API (`/internal/*`)

Everything under `/internal/twin/*` (§2.8–§2.11, plus `GET
/internal/twin/types`, `GET /internal/twin/objects?type=`, `GET
/internal/twin/objects/{id}`, `GET /internal/twin/merges`, `PUT
/internal/twin/objects/{id}/groups/{group}`) is reached ONLY from the
portal, over the platform's internal network — never through the
gateway, never with an RFC-0027 key. Guarded exactly as `identity`'s
own `/internal/*` (RFC-0015 addendum A4): a shared `INTERNAL_API_KEY`,
checked by path PREFIX in a `before_request` hook so a future route
under it is covered the day it exists, not by a per-route decorator
someone can forget. `twin` is the THIRD holder of this key, after
`identity` and `portal`.

The portal relays who is asking as three trusted headers
(`X-OAAP-Person-User`, `X-OAAP-Person-Tenant`, `X-OAAP-Person-Roles`)
— it has already authenticated the actual person through its own
login and its own gateway forward-auth; this service only re-checks
their ROLE per action, the exact split identity's own `/internal/*`
comment already describes for itself: "this layer only establishes
that the caller IS the portal [...]; [the caller] is responsible for
admin authorization of its callers." RFC-0031 §6's own sentence, taken
literally: "the twin browser uses the same API with a person's session
instead of an instance credential" — except the session itself never
reaches this container.

Role gating, as Bauplan Schritt 5 names the roles: `user`/`keyuser`/
`admin`/`tenant_admin` may all READ (types, objects, the tree — no
binding filter, unlike an instance: RFC-0031 §3.3 treats the tenant as
an origin like any other, and every person of it may see its own
twin); `admin`/`keyuser`/`tenant_admin` may additionally WRITE into a
`tenant`-origin group (§2.7, origin literally `"tenant"` — schema-
scoped already, no cross-tenant namespace question the way §2.11's
type registry has); `tenant_admin` alone may view merge candidates,
merge, unmerge, and create a type.

### 2.13 The outbox relay and `states` (0.3, RFC-0032 §1.4/§1.5)

Two decisions RFC-0032 left open were taken by Jörg on 2026-09-12, both
following the recommendation: the relay runs as **its own service**
(not inside `twin`, whose two web workers would publish twice and whose
crash would restart nobody), and it authenticates at the broker with
**its own platform secret** (`oaap.events.broker` 0.2 §2.4), not with
one RFC-0027 key per tenant.

**Where it runs.** Compose service `relay`: the `twin` image, command
`relay.py`, node profile **`broker`** — no broker, no relay. It needs
no port and no gateway route; it only calls out, to `store` (as each
tenant's own schema role, from the same read-only `twin-secrets.json`
`twin` mounts) and to `broker` (platform network, port 1883). It does
not depend on `store` in compose — on a node with `broker` but without
`store` it finds no twin schema and idles.

**Two tables per tenant schema**, provisioned by the same host-side
`_twin_ensure_tables` as every other, and reaching an existing tenant
through `oaap data store migrate-twin` on update:

- `states (id, event_id UNIQUE, object_id, group_key, recorded_at,
  payload jsonb)` — RFC-0032 §1.4's table, plus `event_id`: it ties a
  snapshot to the event it answers, and its uniqueness is what makes a
  re-published row harmless. Append-only. Written ONLY by the relay.
- `relay_watermark (id = 1, last_event_id, updated_at, checked_at,
  last_error)` — exactly one row: the relay's bookkeeping, not twin
  data, and therefore the one table here that is updated in place.

**What it does, per tenant, in event-id order:**

1. Read the events past `last_event_id` (joined to `objects` for the
   type key).
2. Work out the topic (`oaap.events.broker` §2.2):
   `oaap/<tenant>/<type>/<object>/<group>` for a group event,
   `oaap/<tenant>/<type>/<object>` for an object-wide one (merge,
   unmerge). A row without an object (`type.created`) has no place in
   a tree of objects and is passed over — watermark advanced, nothing
   published.
3. For a group event, read that group's current attributes — the
   snapshot.
4. Publish the thin row (`id`, `kind`, `object_id`, `group_key`,
   `origin`, `recorded_at`), **retained, QoS 1, over MQTT v5**, and wait
   for the broker's acknowledgement. v5, not 3.1.1, is a requirement,
   not a preference: under 3.1.1 a broker acknowledges a publish it
   refused on ACL grounds exactly like one it accepted, so a
   misconfigured principal would advance the watermark over messages
   that went nowhere. Under v5 the refusal comes back as a reason code,
   and a refused publish stops this tenant at that row.
5. Only then, in **one** transaction: insert the `states` row (if any)
   and move `last_event_id` forward (never backward). A crash between
   4 and 5 re-publishes one row on restart — a retained message is
   simply replaced, and `event_id` refuses a second snapshot.

**When the broker is away** (or refuses, or the secret is missing),
nothing is skipped and nothing is lost: the tenant stops at the first
unpublished row and the reason goes into `last_error`. The relay also
writes `checked_at` at least once a minute while idle, so silence is
distinguishable from calm.

**A backlog** — events recorded before the relay first ran, or while
the broker was away — is published in order, but each `states` row
holds the group's snapshot at the moment the relay READ it (RFC-0032
§1.4's own wording), not the value at the time of the event. The
append-only tables above keep that history; `states` is not a second
copy of it.

**`GET /internal/twin/outbox`** — for each tenant: `pending` (events
past the watermark), `watermark`, `checked_age` (seconds since the
relay last reported, by Postgres's clock, so a clock difference between
containers cannot make a live relay look silent) and `last_error`; or
`error` when a schema lacks the relay tables. The one `/internal/twin/*`
route without person headers: it answers a node-wide operator question
and returns counts and ages only — never an object, a group or a
value. It still sits behind the prefix guard (§2.12).

### 2.14 The remote reader (0.4, RFC-0033 §6 / D10)

An app on **another node** reads this node's twin live, through a
tunnel (`oaap.net.connector`): the inner node offers its own front door
(`http://gateway:80/twin`), the outer node binds its app to a `via`
destination, and the destination carries the key this section
issues. The app on the outer node never sees the key
(`oaap.net.destinations` 2.3).

Measured before this section existed (2026-09-25, `oaap-test` ↔
`oaap-demo`): the call went through the tunnel and `identity` accepted
the key — and this service refused it, because 0.3 looked every caller
up in the LOCAL instance registry, where a reader on another node is
not. RFC-0033 §6 had expected "no extra work"; this section is the
extra work.

- **Created on the node that holds the data, by its operator:**
  `oaap data twin add-reader <label> --tenant <t> --reads <type>[,<type>…]`.
  It creates the machine principal `remote:<label>` in that tenant,
  records the reader, and issues one key scoped to `oaap.twin`
  (shown once, 90 days by default, at most 365 — RFC-0027 D3). The
  types named MUST be active for that tenant. There is no default:
  a reader reads exactly the types listed.
- **The record** lives next to the instance registry
  (`twin-readers.json` in the reference): label, tenant, types, who
  created it and when. It holds no secret. The service resolves
  `remote:<label>` there exactly as it resolves `instance:<name>` in
  the registry: the principal name comes from `identity`'s verification,
  everything else from a file only the operator writes.
- **Read-only, by construction and said out loud.** A remote reader
  gets one `consumes` binding per listed type and nothing else, so
  §2.6 and §2.4 answer it and §2.5 and §2.7 cannot. Both write routes
  refuse it with their own sentence before they look at bindings.
  Writing across nodes belongs to the owning side (RFC-0031 §3.3,
  RFC-0033 §6: a replica never becomes owner), and is not part of 0.4.
- **Its origin is `remote:<label>`**, wherever an origin is shown.
- `oaap data twin readers` lists them; `oaap data twin remove-reader
  <label>` revokes every key of the principal, deactivates it (principals
  are kept, like keys, for their history) and removes the record — the
  next call is refused by `identity`, and a key issued earlier that
  somehow was not revoked would still be refused here, because the
  record is gone.
- A rehearsal is not involved: the reader is not an instance.

**Measured** (reference 0.1.130, 2026-09-25): `oaap-test` holding the
data and offering `http://gateway:80/twin` through its connector,
`oaap-demo` outer with a `via` destination bound to an app. Through the
tunnel the app got `GET /types`, and a `Firma` object whole; an object
of another type → 403; `POST /objects` and `PUT …/groups/core` → 403
with the read-only sentence; after `remove-reader` the next call → 401
from `identity`.

**Why not a stand-in instance in the registry.** Registering the remote
app as a fake local instance would have worked without a line of code
here, and every other reader of the registry would then have had to
know that one entry does not run on this node. A second name space with
its own file keeps the registry true.

### 2.15 One write rule, two doors (0.5, RFC-0085 amendment A2)

The rules of §2.5/§2.7 -- a group belongs to the origin that created it,
a value repeated unchanged writes nothing, every write appends one
`events` row -- live in one module (`twin_write`) that two callers use:

- the API, for an app's instance credential; the binding check stays at
  this door;
- the **platform's own writer**, the hub's fleet service (RFC-0085 §9,
  amendment A2), with origin `platform:fleet` and the tenant's schema role
  (`/platform-apps/twin-secrets.json`, read-only, as the twin itself). It
  finds its objects by source key under its origin, and it can never write
  a group another origin created -- `owner.*` groups written by people
  stay theirs.

Two corrections came with it, both to match what §2.7 already said: an
**unchanged relation** (same target, same validity) writes nothing --
before, every PUT appended a new relation row; and a PUT that writes
nothing records **no** `events` row (the first PUT of a group still does,
as the group was created). Found 2026-11-14 while building the fleet's
writer, which repeats the same relations every half minute; the
counter-check without the correction is red (`test_fleet_twin.py`).

### 2.16 The twin as an MCP source (0.9, RFC-0118 P6 / D7)

An assistant should see the tenant's objects -- a customer, a project, a
machine -- the way a person in the portal's twin browser sees them, and
nothing more. The twin is not an app instance, so it does not declare
`mcp:` (RFC-0073); the platform names it instead.

**The source.** On a node with the profile `store`, the source list of
every consuming MCP gateway (`mcp_sources: {read: true}`, not a
rehearsal, RFC-0073 D2) names one more source, `twin`
(`app: "oaap.data.twin"`, `channel: "platform"`), with a door and a
discovery door on the gateway's own site like every other source
(RFC-0073 §4, §16). Its `address` is the door as well: the twin takes no
agent key (procedure T), so a call without a person is refused. If an
instance of the same tenant is itself called `twin` and declares a door,
that instance is the source of that name and the platform twin is not
listed -- one name, one source. The gateway treats the twin like any
other source: red until the operator approves tools into a view
(RFC-0065 D9).

**The door.** Exactly the blocks of RFC-0073 (`/verify?act=` resp.
`?discover=` with the gateway's sources key and, at the door, the
person's credential), with these values: roles `admin, keyuser,
tenant_admin, user` (the readers of §2.12), no visibility group, the
gateway's tenant, target `twin:8000`, path `/mcp`. After `forward_auth`
the block **sets** `X-OAAP-Twin-Tenant` to the gateway's tenant id --
overwriting whatever the client sent. That header is the tenant the twin
reads; it never comes from the body. `/mcp` is not under `/twin/*`, so the
public route never reaches it; only these blocks do.

**The service.** `POST /mcp` on `twin`: JSON-RPC over Streamable HTTP,
JSON answers only, no session (the shape of every OAAP app door). Without
`X-OAAP-Twin-Tenant` -- 403. `initialize`, `ping`, `tools/list`,
`prompts/list` and `resources/list` answer anyone the door let through
(the discovery door lets only these through, as the gateway's machine
principal). `tools/call` needs a **person**: `X-OAAP-User` set and not a
machine principal (`instance:`, `remote:`), and one of the reader roles;
otherwise the result is an error sentence (`isError: true`), never data.

| Tool | Arguments | Answer |
|---|---|---|
| `twin_types` | -- | the tenant's active types: `key`, `kind`, `title`, `semantic_iri` where defined |
| `twin_search` | `q` (words in the title), `type` (optional), `offset` | at most 50 objects `{id, type, title, owner}`, ordered by title, merged-away aliases excluded, `more: true` when there is a next page; `q` as §2.6a (every word, `%`/`_` literal) |
| `twin_object` | `id` (`urn:oaap:obj:<uuid>` or the bare uuid), `at` (optional date, §2.8) | as §2.12's object page: header, every group with attributes, relations (each target with its title) and activities, `merged_aliases` |

All three are read-only (`readOnlyHint: true`), and their descriptions
are fixed -- a changed description locks a tool in the gateway until it
is approved again. There is no writing tool: writing into the twin stays
with an app's own credential (§2.5/§2.7) and the portal (§2.12).

What a person may see through the twin is what §2.12 already grants:
every reader of the tenant sees its whole twin. An assistant adds no
reach of its own -- the call is the person's (RFC-0073 §4), and the
gateway's view decides which of the three tools the assistant has at all.

### 2.17 Integration clients and the door `/twin/v1` (0.10, RFC-0120 stage 0)

- **Principal `client:<label>`**: a program outside the platform (a graph viewer, a modelling
  tool, a dashboard), one tenant, made by the operator with
  `oaap data twin add-client <label> --tenant <t> --reads <types> [--days N]`, or by the
  tenant's administration on the portal page *Zugänge → Integration* (RFC-0120 D2): the page
  makes and removes the client through a host job (`twin-client-add` / `twin-client-remove`, own
  tenant only, active types only) and issues its key straight from identity, shown once -- the
  job never carries a key. Its key is scoped `oaap.twin` (§2.2), shown once, at most 365
  days; `remove-client` revokes every key and deactivates the principal. The record
  (`twin-clients.json`: tenant, types, key id, expiry -- no secret) is written by the host only;
  the twin reads it like the readers' file (§2.14). The tenant comes from that record, never from
  the request.
- **Rights:** one `consumes` binding per type it was given. In this version a client **writes
  nothing**: objects, groups and series points answer 403 with a sentence (RFC-0120 stage 3).
- **`GET /twin/v1/types`** -> `{"v": 1, "api": "v1", "caller", "types": [{"key", "kind",
  "title", "access": ["read"|"write"], "semantic_iri"?, "groups"?, "attributes"?,
  "relations"?}]}` -- only the types the caller is bound to; for any twin principal
  (`instance:`, `remote:`, `client:`).
- **`GET /twin/v1/openapi.json`**: OpenAPI 3.1 of the door as this caller sees it (bearer
  scheme, paths, `x-oaap-types`). The app routes `/twin/*` above are unchanged.
- **Keys of platform principals** (`instance:`, `remote:`, `client:`) and keys with a scope that
  names a platform capability (a dot: `oaap.twin`, `oaap.authz…`, `oaap.cases.submit:…`) are
  never issued through the people's key door; only the platform mints them
  (`oaap.core.identity`, RFC-0120 §1.6) -- with one exception: the key of a `client:` of the
  actor's own tenant, scoped exactly `oaap.twin`, role `user` only (D2).

### 2.18 Reads of the door `/twin/v1` (0.11, RFC-0120 stage 1)

For every twin principal (`instance:`, `remote:`, `client:`), with the caller's bindings (§2.17:
any binding of an object type, active for the tenant, lets it read). A request the caller can fix
answers 400 with a sentence (`{"error"}`); an object that does not exist **or** is of a type the
caller may not read answers 404 alike.

- **The moment `at`** (every read except the feed): a date-time (`2026-11-22T10:00:00Z`) or a date
  (= the end of that day, UTC); default now. A row counts that was **recorded** by then and not
  superseded by then (recorded time, §3.4) and whose **validity** contains that day; an object
  counts that was recorded by then; a merge counts that happened by then and was not undone.
  Every answer names its moment (`at`). Without `at` a relation whose `valid_to` has passed is
  gone (unlike the app routes' unfiltered `current_*` read, §2.6).
- **Visibility:** only objects of the caller's types; a relation appears only when both ends are
  visible (its target is never named otherwise); a merged-away id answers as its canonical
  object (`merged_from`), its groups and relations counted there.
- **`GET /twin/v1/objects?type=&where=&fields=&limit=&cursor=&at=`** -> `{"v", "at", "objects":
  [{"id", "type", "title", "owner", "groups": {g: {"origin", "attributes": {k: value},
  "relations": [{"key", "target"}]}}}], "next"}` ordered by (title, id). `where` (repeatable, at
  most 8, all must hold): `<group>.<attr><op><value>` with op `= != < <= > >=`,
  `<group>.<attr> in a,b` or `<group>.<attr> has`; the attribute must be registered, belong to
  the group where the group type lists its attributes, the value fit its `value_type` (numbers
  compare as numbers, `bool` only with `=`/`!=`/`in`). `fields` names the groups to answer
  (empty: none). `limit` 1..500 (default 100); `next` is an opaque cursor; one page looks at most
  20 000 objects and then answers with a `next` to go on.
- **`GET /twin/v1/objects/{id}?at=`** -- one object in the same shape.
- **`GET /twin/v1/objects/{id}/graph?depth=&relations=&direction=&types=&at=`** -> `{"nodes":
  [{"id", "type", "title", "depth"}], "edges": [{"source", "key", "target", "group"}],
  "truncated"}` -- depth 1..5 (default 2), direction `out|in|both` (default both), `types` the
  node types the walk enters, at most 2000 nodes.
- **`GET /twin/v1/paths?from=&to=&relations=&direction=&max=&length=&at=`** -> up to `max`
  (1..10, default 3) shortest paths of at most `length` hops (1..6), each `{"length", "nodes",
  "edges"}`, plus the nodes' titles.
- **`GET /twin/v1/export?types=&relations=&format=json|graphml&attributes=1|0&at=`** -- nodes and
  edges in one document; JSON with the types' `semantic_iri`, GraphML 1.0 with every attribute as
  `<group>.<attr>`. Attributes whose attribute type says `"personal": true` are left out (RFC-0120
  D10). At most 20 000 nodes (`truncated`).
- **`GET /twin/v1/changes?since=&types=&limit=`** -> `{"changes": [{"id", "at", "kind", "object",
  "type", "group", "origin", "merged_from"?}], "next", "more"}` -- the events (§2.3) of objects of
  the caller's types after the event id `since`, in order; `limit` 1..1000 (default 200);
  `since=now` answers no change and the newest `next`. An event joins the feed 5 seconds after it
  was recorded, so a transaction that took a lower id but committed later is not skipped.
- `GET /twin/v1/openapi.json` (§2.17) describes these paths.
- **Not in this version:** limits per client (requests), JSON-LD, value events, inbound webhooks
  (RFC-0120 D13, open). Writing: §2.22-2.25. Periods and series: §2.20, §2.21. Graph walks run over one load of the visible edges (no recursive SQL yet; measured
  with the fleet twin, revisited if they get slow).

### 2.19 Values checked on every door (0.12, RFC-0120 stage 2)

Every write of attributes -- an app's `POST /twin/objects` and `PUT …/groups/{group}`, a person's
group write through the portal, the platform's own writers (fleet, tenant assets) and every period
(§2.20) -- checks each value against its attribute type in `oaap.data.model` **before anything is
written**. One function decides (`twin_values.check` in the reference):

| value_type | accepted | stored |
|---|---|---|
| text | a string | as given |
| int | an integer, or a string of digits | an integer |
| decimal | a number, or a string that is one (`1.5`, `1,5`) | a number |
| bool | `true`/`false`, or those strings | `true`/`false` |
| date | `2026-11-22` | as given |
| datetime | `2026-11-22T10:00:00Z` | as given |
| enum | a string; one of the type's `values` when it lists them | as given |
| ref | `urn:oaap:obj:<uuid>` | as given |

`null` always fits (it clears), and so does an empty string for every type but text (a form's
empty field; the fleet's "none"), stored as `null`. An attribute that is not registered is not
checked. A value that does not fit refuses the **whole** write with 400 and a sentence naming the
attribute and its type -- the other values of that write are not written either. Only the
platform's own writers (origin `platform:…`) are not refused for one bad value: that value is left
out and logged, so one odd reading of one node never stops the fleet's twin. A periodic attribute
(§2.20) in a group write is refused with a sentence pointing to `…/periods`.

### 2.20 Periodic attributes (0.12, RFC-0120 stage 2, D4)

An attribute type may say **`"periodic": true`** (and a **`"unit"`**, `oaap.data.model` §2.2). Such
an attribute holds **several values side by side**, each for a **period**: a KPI per year or
quarter (CO₂e 2024, CO₂e 2025), not a measurement (that is a series, §2.21). Table `periods` in the
tenant's schema, append-only like every other: `value`, `valid_from` and `valid_to` as
date-times (`valid_to` exclusive), `unit`, `source`, `quality` (`measured`, `calculated`,
`estimated`, `reported`), who and when.

- **Write:** `POST /twin/objects/{id}/groups/{group}/periods` (an app, with `contributes` on the
  object's type, into its own group -- §2.15) and `POST /internal/twin/objects/{id}/groups/{group}/periods`
  (a person through the portal: roles admin, keyuser or tenant_admin, into a tenant group, which
  the first period creates). Body `{"attribute", "value", "valid_from", "valid_to", "unit"?,
  "source"?, "quality"?}`; a **date** as `valid_from` is that day's 00:00 UTC, a date as `valid_to`
  is the **last day the period covers** (2025-01-01 .. 2025-12-31 is the year 2025); without
  `unit` the attribute type's unit is kept. The value is checked (§2.19). Answers 201
  `{"written": true, "period"}`, or 200 with `written: false` when the same period with the same
  value, unit, source and quality is already there.
- **Rules:** periods of one attribute of one object **must not overlap** (409 naming the period
  in the way) -- except that **the same bounds again correct** the period (the old row is
  superseded, never deleted). **`"value": null` withdraws** a period (404 if there is none to
  withdraw). An attribute that is not periodic is refused as a period (400), and the attribute
  must belong to the group when the group type lists its attributes. One event `period.written`
  per write.
- **Read per period:** `GET /twin/v1/objects/{id}/periods?attribute=<group>.<attr>&from=&to=&at=`
  (a client, §2.18), `GET /twin/objects/{id}/periods` (an app with any binding on the type),
  `GET /internal/twin/objects/{id}/periods` (a person) -> `{"object", "periods": [{"group",
  "attribute", "value", "valid_from", "valid_to", "unit", "source", "quality", "recorded_at",
  "recorded_by"}]}`, oldest first, withdrawn ones left out. `from`/`to` keep the periods that
  overlap that window; `at` answers as recorded then (a correction made later is not yet there).
- **Read as the object's value:** in every object read (§2.18, `GET /twin/objects/{id}`, the
  portal, the MCP door) a periodic attribute's value is that of the period that **contains the
  moment** -- or, if none does, of the **latest period that ended before it** (the last known
  value), with its bounds: on `/twin/v1` under the group's `periods`, elsewhere next to the value
  (`"periodic": true`, `valid_from`, `valid_to`, `unit`, …). Filters (`where`, §2.18) compare
  that value. A period that begins later never counts.
- **`at` stays both axes** (§2.18): an object recorded today does not exist at `at=2024-07-01`.
  To read the value of a past period as it is known today, read the periods with `from`/`to`.
  The portal's date (a validity day, §2.12) picks the period of that day.

### 2.21 Series for persons and clients (0.12, RFC-0120 stage 2)

The time series of `oaap.data.timeseries` (until now reachable for app keys only) are read by:

- **integration clients** -- `GET /twin/v1/series?object=`, `GET /twin/v1/series/{id}/range?from=&to=&step=`,
  `GET /twin/v1/series/{id}/latest`; only series of objects of a type the client may read; any
  other answers 404 like a missing one;
- **persons** through the portal -- `GET /internal/twin/series?object=` and
  `GET /internal/twin/series/{id}/range`; a person reads the tenant's whole twin (§2.12). The
  object page draws each number series (at most eight) as a line with its min-max band over 24
  hours, 7 days, 30 days or a year.

A tenant without time series answers 409 (the client) or shows none (the portal). Writing series
stays with apps (RFC-0086).

### 2.22 Clients that write (0.13, RFC-0120 stage 3)

An integration client's record (`twin-clients.json`, written by the host only) carries, besides
`reads`, **`writes`** -- the object types it creates objects of (as owner) and writes its own
groups on -- and **`models: true`** -- it may create types of its tenant (§2.23, RFC-0120 D8). A
modelling client is owner of every object type it created itself, without the operator naming
it again. The tenant admin sets both on *Zugänge -> Integration* (fields *Schreibt*,
*Modelliert*); the operator with `oaap data twin add-client <label> --tenant <t> [--reads]
[--writes] [--models]`.

- The **origin** of everything a client writes is `client:<label>`. The twin's write rule holds
  unchanged (§2.15): a group belongs to the origin that created it; a group a person (`tenant`),
  an app or the platform created is refused with 403 and a sentence naming its owner. **This is
  the sync rule: nobody overwrites anybody.**
- A client writes **only through `/twin/v1`**; the app routes (`/twin/objects`, `/twin/series`,
  `/twin/points`) refuse it with a sentence pointing there. Writing series stays with apps.
- A client's group write is stricter than an app's: the group type must be registered, active
  for the tenant and attached to the object's type; attributes and relations only from the group
  type's lists; a relation's target is named by id or by the client's own key and must be an
  object the client may read. Every value is checked (§2.19).
- Every write answers JSON; a refusal is `{"error": "<sentence>"}` with 400, 403, 404 or 409, and
  nothing of the call is written.

### 2.23 Types of the tenant (0.13, RFC-0120 D8, D9)

`POST /twin/v1/types` (client with `models`) `{"object_type"?: {"key", "title", "title_plural"?,
"semantic_id"?}, "on"?: <object type>, "groups": [{"key", "title", "attributes": [{"key", "title",
"value_type", "values"?, "unit"?, "periodic"?, "personal"?}], "relations": [{"key", "title", "to",
"title_inverse"?}]}]}`:

- The object type is registered as **`t.<tenant label>.<key>`** (D9) with origin
  `tenant:<tenant-id>` and `created_by` = the client. Without `object_type`, the groups go `on` an
  object type the client may write.
- Attribute, relation and group keys stay node-wide (an attribute key has no dots, §2.5). A key
  already registered with the **same meaning** is **reused** (attribute: `value_type`, `values`,
  `unit`, `periodic`; relation: `from`, `to`); with another meaning it is refused (409). A
  relation's `to` may name a type of the same body by its short key.
- **Additive only** (`oaap.data.model` §2.5): a group type of this tenant that this client created
  may gain attributes and relations; nothing is removed or changed. A group type made by someone
  else is not changed (403).
- The same body again registers nothing: 200 `{"created": [], "unchanged": [...]}`; 201 when
  something was registered. One event `type.created`.

### 2.24 Upsert, batches, retire (0.13, RFC-0120 stage 3)

- **Upsert by the client's own key:** `PUT /twin/v1/objects/by-key/{key}` `{"type", "title",
  "groups": {<group>: {"attributes", "relations": [{"key", "target" | "target_key"}]}}}` finds the
  object the client knows as `{key}` (`source_keys`, origin `client:<label>`) or creates it (owner
  of the type needed; the first group is the owner's core group) -> `{"id", "created", "written",
  "renamed"}`, 201 when created, 200 otherwise. The same call twice makes one object; two calls
  at once with the same key too (a lock per key). `GET /twin/v1/objects/by-key/{key}` reads it.
  A key is the client's own: another client's key `APP-1` is another object.
- **Rename:** a new `title` from the owner renames; the old title is kept in `renames`, so a read
  with an earlier `at` answers the title of then. Another origin's title is refused.
- **Groups and periods:** `PUT /twin/v1/objects/{id}/groups/{group}`,
  `POST /twin/v1/objects/{id}/groups/{group}/periods` (§2.20) -- into the client's own groups.
- **Batch:** `POST /twin/v1/batch {"id", "operations": [...]}` -- up to 500 operations `upsert`
  (as above, with `key`), `group`, `period`, `retire` (each naming its object by `object` or by
  the client's `key`, so a later operation can use an object an earlier one created) in **one
  transaction, all or nothing**: one bad operation answers its number and sentence and nothing
  is written. The answer is kept under `(client, id)`; **the same id again answers it with
  `"replayed": true` and writes nothing**.
- **Retire:** `POST /twin/v1/objects/{id}/retire {"reason"?}` -- only the owner. The object stays
  in the history (a read with an earlier `at` sees it), leaves **every current read** (the door's
  lists, export, graph, paths; an app's and a person's reads; the MCP door) and is never written
  again (409). Retiring twice writes nothing. A relation ends as before, with `valid_to`. Erasure
  stays RFC-0090. Events `object.retired`, `object.renamed`.

### 2.25 Webhooks (0.13, RFC-0120 stage 3, D6)

A client registers a URL and gets every change it may read posted there -- the same entries the
change feed answers (§2.18: id, at, kind, object, type, group, origin; no values, so D10 holds):

- `POST /twin/v1/webhooks {"url", "types"?, "kinds"?, "own"?}` -> 201 with an id and the
  **secret, shown once**; `GET /twin/v1/webhooks` (state, delivered, failures, last answer; never
  the secret); `DELETE /twin/v1/webhooks/{id}`; `POST /twin/v1/webhooks/{id}/resume`. At most
  five per client. `types` narrows to some of its types, `kinds` to some of `object.created`,
  `group.written`, `period.written`, `object.retired`, `object.renamed`, `object.merged`,
  `object.unmerged`. The client's own writes are left out unless `own: true`.
- **Delivery** (the service `hooks`, the twin's image): `POST <url>` with `{"hook", "events": [...]
  (at most 50, oldest first), "next"}`, header **`X-OAAP-Signature: t=<unix seconds>,v1=<hex>`**,
  `<hex>` = HMAC-SHA256 with the secret over `<t>.<body>`; the receiver recomputes it and refuses
  an old `t`. The cursor moves only after a 2xx: **in order, at least once** -- a receiver
  deduplicates by event id; a sync that lost one reads the change feed from `next`. An event is
  posted once it is 5 seconds old (the feed's settling) -- measured 7 s from a person's save to
  the receiver.
- **Retries:** a failure waits 2^n seconds (at most an hour); after 10 failures in a row the
  webhook **stops** -- the client's list and the tenant admin's page *Integration* show it with
  the last answer; `resume` delivers everything from where it stopped.
- **Only to the internet:** `https`; no user or password in the URL; never a name of the
  platform's network or a private, loopback or link-local address -- checked at registration and
  again before every connection, which goes to the checked address (no second lookup), no
  redirect followed. The operator may name exceptions (`OAAP_TWIN_HOOK_ALLOW`, host names or
  addresses, e.g. a test receiver in the LAN; `http` allowed for them).
- **A closed tenant** (RFC-0068) registers none (409) and posts none -- its webhooks wait.
  "Only to destinations it has bound" is not built.
- The client's **current** rights decide at each delivery; a removed client's webhooks stop.

## 3. Configuration

- `apps/twin-secrets.json` (`0600`, root and the `twin` container's
  mount only): `{"twin_<tenant-id>": {"role", "password"}}`, written by
  `appctl._twin_ensure_schema`, read by nothing else.
- `OAAP_PLATFORM_KEY`, `OAAP_TWIN_URL` in an instance's `instance.env` —
  platform-owned (§2.2), present only when the manifest declares
  `contributes`/`consumes` and the instance is not a rehearsal.
- The node profile `store` (RFC-0011) — carries `twin` exactly as it
  carries `oaap.data.store` itself; neither runs without it.
- No manifest-level configuration of its own: `oaap.data.model`'s
  `data_model`/`contributes`/`consumes` sections are what an app
  declares; this capability only serves what they already said.
- `INTERNAL_API_KEY` (0.2) — the same platform secret `identity` and
  `portal` already hold, added to this container's environment so the
  portal may reach `/internal/*` (§2.12). Absent, that surface fails
  closed with `503`, exactly like identity's own.
- The compose service `relay` (0.3, §2.13) — node profile `broker`, the
  `twin` image with command `relay.py`, the same read-only
  `twin-secrets.json` mount, no port. `BROKER_RELAY_KEY` in its
  environment (and identity's), nowhere else — `twin` itself does not
  hold it. `RELAY_POLL_SECONDS` (default 2) sets how often it looks.

## 4. Security requirements

- The caller's tenant and origin come from its resolved credential
  (`X-OAAP-User: instance:<name>` → the registry's own record of that
  instance), never from a request field. A body that named a tenant
  would be ignored even if sent — nothing in 0.1's request handling
  reads one.
- A human session reaching `/twin/*`, however it authenticated, is
  refused: `X-OAAP-User` must start with `instance:`. A person reaches
  this service ONLY through `/internal/*` (§2.12), never `/twin/*`,
  and only via the portal — never directly, and never with an RFC-0027
  key of their own.
- `/internal/*` fails closed twice over (§2.12): no `INTERNAL_API_KEY`
  configured → `503`; present but wrong or absent on the request →
  `401`. Every route under the prefix is covered by ONE `before_request`
  hook, not a per-route decorator — the exact fix RFC-0015 addendum A4
  made for `identity`, reused here rather than re-derived.
- Every `/internal/*` route re-checks the caller's ROLE for its own
  action (§2.12) — the portal having verified the person is necessary,
  not sufficient; a `user` reaching a `tenant_admin`-only action (merge,
  type creation) is refused here, not only hidden in the portal's UI.
- A tenant-created type (§2.11) can only ever ADD a brand-new key — the
  connecting role's `GRANT INSERT` on `oaap_model.type_definitions`/
  `activations` carries no `UPDATE`/`DELETE`, and the service's own
  code refuses a key that already exists before any row is touched.
- The E1 key is **always** issued with RFC-0027 `--instance` scoping,
  to the reserved value `oaap.twin` — never left unscoped, and never
  scoped to the calling app's own name (§2.2: an unscoped key
  authenticates against every other app's own route asking the same
  role, in the same tenant — not only `/twin/*`). Both the Caddyfile's
  `/twin/*` block and `appctl.py`'s `_twin_issue_instance_key` name the
  exact same value (`TWIN_KEY_SCOPE`); the two drifting apart silently
  reopens the gap §2.2 describes, so a change to one without the other
  is a bug, not a variant.
- A write outside the caller's own group is refused with a plain
  reason, at the service, before any row is touched (§2.7).
- The schema-role credential lives in exactly one place a container
  mounts read-only; `appctl` never prints it, and the mount is `:ro`
  even for `twin` itself, since only `_twin_ensure_schema` (running on
  the host, as the Postgres superuser via `docker exec`) ever writes
  DDL or grants — the service only ever does DML.
- A rehearsal instance is refused this capability entirely (§2.2) —
  the one place 0.1 deliberately trades completeness for the guarantee
  RFC-0030 exists to make, rather than half-implementing D8 under time
  pressure.
- Every write is recorded, with `recorded_by`, and appends an `events`
  row — nothing is silently dropped, whether or not a relay is running
  to read it.
- The relay (§2.13) MUST NOT advance a tenant's watermark past a row the
  broker has not acknowledged as accepted — an unreachable broker, a
  timeout and a refusal all stop that tenant at that row. It MUST speak
  a protocol version in which a refused publish is reported (MQTT v5),
  since under 3.1.1 a refusal is acknowledged like a success.
- `states` is written by the relay only, never by an app, a person or
  `twin` itself — the same rule `events` already follows: both are
  projections of an ordinary write, never a second way to produce data.
- `GET /internal/twin/outbox` returns counts, ages and error texts
  only — never an object id, a group, or a value.

## 5. Conformance tests (described)

1. **Owner creates, with its core group** (§9 step 1): an instance
   bound as owner of `Customer` creates one with a `crm.core` group
   carrying attributes and a relation with `valid_from` set; `GET
   .../objects/{id}` returns them; a second instance NOT bound to
   `Customer` gets refused.
2. **Contributor writes into its own group** (§9 step 3, partial — full
   RACI needs Schritt 4's reference apps): an instance bound as
   `contributor` writes a new group on the owner's object; the SAME
   write attempted by a third instance with no binding to that type is
   refused; the owner's OWN core group cannot be touched by the
   contributor even by naming it explicitly.
3. **Nobody else writes there:** two different origins attempting to
   write the SAME `group_key` on one object — the second is refused,
   naming the group's actual owner.
4. **A rehearsal cannot reach the twin:** an app declaring `contributes`/
   `consumes`, rehearsed (RFC-0030), has neither `OAAP_PLATFORM_KEY` nor
   `OAAP_TWIN_URL` in its environment after install, even though its
   production sibling does.
5. **A node without a working store:** installing such an app anyway
   installs cleanly; the CLI states plainly that the twin schema was
   NOT provisioned, matching `oaap.data.model`'s own wording for the
   same situation.
6. **`?at=`** (§9 step 7, first half): a relation valid from 2024-06
   onward is absent from a read with `?at=2024-01-01` and present with
   `?at=2024-12-01` and with no `?at=` at all.
7. **The tree** (§9 step 7, second half): `GET .../tree?depth=2` from
   an object with one relation returns exactly one child, carrying the
   relation's own key as `via`; `?at=` narrows it the same way test 6
   does for a plain read.
8. **Merge and unmerge** (§9 step 6, §3.6): staff management creates
   "Anna Müller" independently of partner management's existing
   "Anna"; a `tenant_admin` merges the two; a read of EITHER id
   afterwards returns groups from BOTH; unmerge splits them back into
   two independently-readable objects, groups intact on each side.
9. **A person is not an instance, and vice versa:** `/twin/*` refuses
   `X-OAAP-Person-*` headers exactly as it always refused a bare human
   session (they are simply not `X-OAAP-User: instance:...`);
   `/internal/*` refuses a caller without `INTERNAL_API_KEY` even if
   it presents a perfectly valid RFC-0027 instance key.
10. **Tenant type creation stays additive:** a `tenant_admin` adds a
    `crm.satisfaction`-shaped group to `Firma`; a SECOND attempt using
    the identical `group_key` is refused, naming the key, not silently
    treated as "already done."

11. **An event reaches the broker, and its snapshot `states`** (0.3,
    §2.13): a group write on a node carrying `store` and `broker`
    appears as a retained message on
    `oaap/<tenant>/<type>/<object>/<group>` carrying the event's id and
    kind and no attribute value; the tenant's `states` gains exactly one
    row for that event id, holding the group's attributes;
    `relay_watermark.last_event_id` equals the event's id.
12. **Nothing is lost while the broker is away:** with the broker
    stopped, a group write leaves `pending` at 1 and the portal's health
    page says so; started again, the same event is published, `pending`
    returns to 0, and `states` still holds exactly one row for it.
13. **A refused publish stops the relay, loudly:** a publish the broker
    refuses is not counted as delivered — the watermark stays, and
    `last_error` names the refusal.

14. **A remote reader reads what it was given, and nothing else:** a
    key of `remote:<label>` with `--reads a` gets `GET /twin/types`
    (bindings: `a` as `consumes`) and `GET /twin/objects/{id}` for an
    object of type `a`; an object of type `b` → 403; `POST
    /twin/objects` and `PUT …/groups/…` → 403 with a sentence naming
    read-only; after `remove-reader` the same key → refused.
15. **A remote reader of tenant A never reads tenant B:** the tenant is
    the record's, and no request field changes it.
16. **The list (0.7, §2.6a):** an app bound to `a` gets every object of
    `a` in its tenant with its groups; `?type=b` (unbound) → 403;
    without `?type=` → 400; a wrong key → refused at the gateway; the
    same app in another tenant → an empty list.

17. **Values are checked on every door (0.12, §2.19):** a text for an `int` attribute, an
    invalid date, a value outside an `enum` -> 400 with the attribute's name, and the other
    values of the same write are not written; `"120"` for an `int` is stored as `120`; `""` for a
    date as `null`; a `platform:` writer loses only the bad value.
18. **Periods (0.12, §2.20):** CO₂e 2024 and 2025 coexist; Q1 2025 -> 409; 2025 again with
    other values supersedes, the same values again -> 200 `written: false`; `null` withdraws, a
    second withdrawal -> 404; a non-periodic attribute as a period -> 400; a periodic one in a
    group write -> 400; `at` before a correction reads the old value; the object read shows the
    period containing the moment or the last one ended, with its bounds.
19. **Series (0.12, §2.21):** a client reads the series of an object of its types and a range;
    a series of a type it may not read -> 404 (list and range); a person reads any series of the
    tenant.

20. **Clients that write (0.13, §2.22):** a client without `writes` creates nothing (403); a
    client writes a group a person created -> 403 naming `tenant`, the person's value stays; a
    client never writes through the app routes; a client of another tenant reads and writes
    nothing of this one (404).
21. **Types (0.13, §2.23):** without `models` -> 403; the object type is `t.<label>.<key>`; the
    same body again -> 200, nothing registered; an attribute added -> registered, the others
    unchanged; the same attribute key with another value type -> 409.
22. **Upsert, batch, retire (0.13, §2.24):** the same upsert twice -> one object; a wrong value ->
    400 and no object; a relation by the target's key; a rename read back with an earlier `at`;
    a batch with a bad second operation -> 400 naming it, the first not written; the same batch
    id twice -> `replayed`, no event; a retired object -> 404 now, 200 with an earlier `at`, 409
    on any write; another owner's object -> 403.
23. **Webhooks (0.13, §2.25):** a URL into the platform's network or a private address -> 400; a
    person's change reaches the receiver signed, the client's own does not; a forged body or an
    old `t` fails the check; a 500 -> waits, cursor unmoved; after the limit -> stopped and shown
    in the portal; resume -> the backlog; a closed tenant -> 409 and nothing posted; a removed
    client -> stopped.

Step 8 of RFC-0031 §9 (the rehearsal's own copy, D8) is the only one
still out of scope (§1) and not a conformance test here yet.

## 6. Dependencies

`oaap.data.store` (every tenant's twin is one of its schemas, provi-
sioned by the same host-side DDL pattern `oaap.data.model` already
uses); `oaap.data.model` (the registry read directly, `oaap_model.*`,
granted per tenant schema — and, since 0.2, also written to for a
tenant-created type, §2.11); `oaap.apps.runtime` (the install hook that
mints the E1 key and provisions the schema — one place, like the
`data_model` hook it sits beside); RFC-0027 (machine principals — the
credential mechanism, and specifically D5's `--instance` scoping,
which this capability relies on to keep the E1 key from reaching any
route beyond `/twin/*`, §2.2); RFC-0016 (app network isolation — the
reason this service is reached
through the gateway and not by a direct network link); RFC-0030 (the
rehearsal rule this capability currently satisfies by refusal, §2.2,
until D8 is built); RFC-0015 addendum A4 (the `/internal/*` guard
pattern, reused for the person-facing API, §2.12); `oaap.core.portal`
(the only caller of `/internal/*` — it authenticates the person and
relays who is asking, §2.12).

## 7. Maturity

`draft` — becomes `beta` once conformance tests 1–13 pass on the
reference platform (`oaap-test`), and step 8 of RFC-0031 §9 (the
rehearsal's own copy, D8) has its own capability-spec addendum once
built — the one piece 0.2 still satisfies by refusal alone (§1, §4).

## Deutsche Zusammenfassung (Nachtrag v0.7 — die Liste für Apps)

Neue Leseabfrage für Apps: `GET /twin/objects?type=<Typ>` liefert alle
Objekte eines Typs, jedes so vollständig wie die Einzelabfrage. Es gilt
dieselbe Regel: nur für einen Typ, den die App gebunden hat (`contributes`
oder `consumes`). Höchstens 500 Objekte; eine längere Liste sagt das
(`truncated`). Der Mandant ist immer der der App: Dieselbe App in einem
anderen Mandanten bekommt eine leere Liste. Anlass ist FleetView 1.0, das
die Flotte aus dem Zwilling der Zentrale liest (RFC-0085 §10).

## Deutsche Zusammenfassung (Nachtrag v0.6 — Betroffenheit)

Neue Leseabfrage `GET /internal/twin/objects/{id}/affected`: Von einem
Objekt der Flotte aus werden die Beziehungen rückwärts gelesen — wer nutzt
es, wer bindet das, wer erreicht das — mit Ort, Mandant und Entfernung je
Zeile. Ein Tunnel, der eine betroffene Instanz erreicht, steht als Ganzes
da („möglicherweise betroffen“), weil der Zwilling nicht weiß, welches
Angebot eine Destination nutzt. Dieselbe Funktion nutzt die Zentrale für
ihre Meldung `link.down`; Seite und Mail sagen also dasselbe.

## Deutsche Zusammenfassung (Nachtrag v0.5 — eine Schreibregel, zwei Türen)

Die Schreibregeln des Zwillings stehen jetzt in **einem** Modul. Die
Schnittstelle für Apps nutzt es, und ebenso der eigene Schreiber der
Plattform, der Flottendienst der Zentrale (Herkunft `platform:fleet`). Der
Flottendienst findet seine Objekte über den Quellschlüssel und kann eine
Gruppe, die ein anderer angelegt hat, nie beschreiben. Die Gruppen
`owner.*`, die Menschen pflegen, bleiben also deren Gruppen. Zwei
Korrekturen stellen nur her, was §2.7 schon versprach: Eine **unveränderte
Beziehung** schreibt keine Zeile mehr (vorher bei jedem Schreiben eine
neue), und ein Schreiben ohne Änderung erzeugt kein Ereignis. Die Typliste
nennt die semantische ID ausgeschrieben (`semantic_iri`).

## Deutsche Zusammenfassung (Nachtrag v0.4 — der entfernte Leser)

Eine App auf einem **anderen Knoten** kann den Zwilling dieses Knotens
live lesen, durch den Tunnel aus RFC-0033 Stufe 2. Bisher schlug der
Zwilling jeden Aufrufer in der Instanzliste des eigenen Knotens nach,
und ein Leser von anderswo stand dort nicht. Gemessen am 25.09.: Der
Tunnel trug den Aufruf, die Anmeldung nahm den Schlüssel an, und der
Zwilling lehnte ab.

Jetzt legt der Betreiber des Knotens, der die Daten hält, einen
**entfernten Leser** an:
`oaap data twin add-reader <label> --tenant <t> --reads <typ,typ>`.
Das erzeugt den Maschinen-Prinzipal `remote:<label>` im Mandanten und
eine Eintragung mit den erlaubten Typen, und es stellt einen Schlüssel
aus. Der Schlüssel wird einmal angezeigt und gehört in die Destination
auf dem äußeren Knoten, nicht in die App.

- **Nur lesen.** Der Leser bekommt je Typ eine Nutzungs-Bindung und
  sonst nichts. Beide Schreibwege lehnen ihn mit einem eigenen Satz ab.
  Schreiben über Knoten hinweg wäre eine eigene Entscheidung, denn die
  Daten gehören der Seite, die sie hält.
- **Nur die genannten Typen, nur der eigene Mandant.** Kein Typ ist
  voreingestellt, und der Mandant kommt aus der Eintragung, nie aus der
  Anfrage.
- **Warum keine Schein-Instanz** in der Instanzliste: Jeder andere Leser
  dieser Liste müsste dann wissen, dass ein Eintrag gar nicht auf diesem
  Knoten läuft.

## Deutsche Zusammenfassung (Nachtrag v0.3 — das Ereignis-Relais)

**Die `events`-Tabelle hat jetzt einen Leser.** Seit RFC-0031 legt jede
Schreibung im Zwilling eine Zeile in `events` ab; niemand holte sie ab.
Das **Relais** (RFC-0032 Bauplan Schritt 2) veröffentlicht sie am Broker
— `oaap/<mandant>/<typ>/<objekt>/<gruppe>`, bei einer Zusammenführung
eine Ebene höher —, „retained", damit ein später Abonnent die letzte
Nachricht je Thema trotzdem sieht. Die Nachricht bleibt dünn: *dass*
sich etwas geändert hat, nicht *was*; den Wert holt man beim Zwilling.

**Jörgs zwei Entscheidungen vom 12.09.:** Das Relais ist ein **eigener
Dienst** (`relay`, gleiches Image wie `twin`) am Profil **`broker`** —
ohne Broker kein Relais, die Ereignisse warten dann, und das Portal
sagt es. Und es meldet sich mit einem **eigenen Plattform-Geheimnis**
an (`oaap.events.broker` 0.2), nicht mit einem Schlüssel je Mandant.

**`states`**: je veröffentlichter Gruppenänderung eine Zeile mit dem
Stand der Gruppe in dem Moment, in dem das Relais sie liest. Schreibt
nur das Relais. Bei einem Rückstand (Broker war weg, oder das Relais
lief noch nie) ist das der *heutige* Stand, nicht der vom Zeitpunkt des
Ereignisses — die Geschichte steht weiter in den append-only-Tabellen,
`states` ist keine zweite Kopie davon.

**Verlustfreiheit, konkret:** Erst bestätigt der Broker die
Veröffentlichung, dann schreiben Schnappschuss und Wasserstand in
**einer** Transaktion. Absturz dazwischen → eine Nachricht geht beim
Neustart ein zweites Mal raus, was nichts schadet. Das Relais spricht
**MQTT v5**, weil unter 3.1.1 ein Broker auch eine *verweigerte*
Veröffentlichung wie eine angenommene bestätigt — dann liefe der
Wasserstand über Nachrichten hinweg, die nie ankamen.

**Fürs Portal** meldet `/internal/twin/outbox` je Mandant, wie viele
Ereignisse warten und wie lange sich das Relais nicht gemeldet hat —
Zählungen und Zeiten, nie Werte.

## Deutsche Zusammenfassung (v0.2)

**Der einzige Dienst, mit dem eine App für gemeinsame Mandantendaten
spricht** (RFC-0031 Schritt 3), jetzt ergänzt um Schritt 5: den
Zwillings-Browser im Portal. Objekte, Gruppen, Attribute, Relationen
und Aktivitäten je Mandantenschema (`twin_<mandant-id>` im `store`),
**append-only**. Herkunft und Mandant kommen für eine App weiterhin
ausschließlich aus ihrem Berechtigungsnachweis (Maschinen-Prinzipal
`instance:<name>`, RFC-0027) — für einen MENSCHEN neu seit 0.2 aus
einem zweiten, ausschließlich dem Portal vorbehaltenen Zugang (siehe
unten), nie aus der Anfrage selbst.

**0.2 baut Schritt 5, additiv — nichts, was 0.1 schon konnte, wird
enger:** `?at=` (der Datumsregler) auf jedem Lesen; der Baum, aus
wiederholten Lesevorgängen aufgebaut, nicht aus einer rekursiven
Datenbankabfrage; Zusammenführen und Auflösen von Dubletten (§3.6) —
menschliche Handlungen, protokolliert, jederzeit umkehrbar, weil
Gruppen nie verschmolzen, nur umgehängt werden; Anlegen eines
Mandanten-Typs — bewusst schmal: nur eine neue Gruppe an einem schon
vorhandenen Objekttyp, nie ein ganz neuer Objekttyp, nie eine Änderung
eines bestehenden. Ein zweiter Berechtigungsweg (`/internal/*`)
erschließt all das für einen Menschen, ohne den bestehenden,
maschinen-only Weg (`/twin/*`) im Geringsten zu verändern: das Portal
weist sich mit demselben geteilten Schlüssel aus, den `identity` schon
verlangt (RFC-0015 Nachtrag A4), und reicht die bereits geprüfte
Person als drei vertrauenswürdige Kopfzeilen weiter — die eigentliche
Anmeldung verlässt das Portal nie.

**Bewusst noch nicht gebaut**: Referenzsuche, `restricted`-Gruppen, der
Outbox-Leser (RFC-0032), und vor allem **die Generalprobe (D8)** —
unverändert seit 0.1: eine Generalprobe bekommt absichtlich **gar
keinen** Zwilling-Schlüssel, weil ihre eigene Schema-Kopie noch nicht
existiert. Lieber ehrlich verweigert als halb gebaut.

**Ein echter Fund beim Bau, nicht nur im Code:** die Herkunft eines
mandanteneigenen Typs hieß bislang das bloße Wort `tenant` — dieselbe
Zeichenkette für jeden Mandanten des Knotens. Zwei Mandanten, die
zufällig denselben Schlüssel wählen, hätten sich damit unbemerkt einen
Typ geteilt. Jetzt `tenant:<mandant-id>`, wie `app:<id>`/`model:<id>`
es schon vormachen — Einzelheiten in `oaap.data.model` 0.2s eigenem
Nachtrag.

**Nachtrag nach der ersten Live-Prüfung (2026-09-10):** der Maschinen-
Schlüssel wird jetzt mit RFC-0027s `--instance`-Bindung ausgestellt, auf
den reservierten Wert `oaap.twin` — nicht mehr ungebunden. Ein
ungebundener Schlüssel wird von `identity` nirgends außer nach Rolle
und Mandant abgewiesen; er hätte damit auch jede andere App im selben
Mandanten mit derselben Rolle geöffnet, nicht nur `/twin/*` — live auf
`oaap-test` nachgewiesen, siehe CURRENT_STATE 125.

**Nachtrag nach Schritt 4 (2026-09-10):** die Referenz-Apps
Partnerverwaltung (Owner) und RACI (Contributor) beweisen RFC-0031 §9
Schritt 1 und 3 jetzt live auf `oaap-test`, mit echtem Postgres —
Owner legt mit Kern-Gruppe an, Contributor schreibt seine eigene
Gruppe auf einem fremden Objekt, und ein Leser sieht beide Gruppen
zusammen. Dabei fiel eine zweite Stolperstelle auf: `OAAP_TWIN_URL`
endet bereits auf `/twin`, weil die Caddyfile-Route den Pfad
unverändert weiterleitet; ein Aufrufer hängt nur den Unterpfad an
(`{OAAP_TWIN_URL}/objects`), nie ein zweites `/twin` — §2.2 nennt das
jetzt ausdrücklich, nachdem Partnerverwaltungs erster Bau genau diesen
Fehler machte (404 vom Zwilling selbst, nicht vom Gateway — das
Erkennungszeichen).

Der Dienst läuft als eigener, kleiner Plattform-Container (`twin`),
am selben Knotenprofil `store` wie `oaap.data.store` selbst, erreichbar
ausschließlich über die Gateway-Route `/twin/*` — eine App-Instanz kann
ihn wegen der Netz-Isolation (RFC-0016) sonst gar nicht erreichen. Das
Schema-Passwort (RFC-0031 §7: „einmal gezeigt, nie einer App, nur
`oaap.data.twin`") liegt in einer Datei, die ausschließlich dieser
Container lesend mountet.

## Deutsche Zusammenfassung (0.9)

Der Zwilling wird eine MCP-Quelle. Auf einem Knoten mit dem Profil
`store` findet jedes MCP-Gateway eines Mandanten in seiner Quellenliste
zusätzlich die Quelle `twin`. Sie hat eine Tür auf der Seite des Gateways
wie jede App-Quelle, und die Tür trägt die angemeldete Person durch
identity. Der Mandant kommt aus einer Kopfzeile, die nur diese Tür setzt.

Drei Lesewerkzeuge:
- `twin_types`: die Objekttypen.
- `twin_search`: Suche im Titel, wahlweise je Typ, 50 je Seite.
- `twin_object`: ein Objekt mit Gruppen, Beziehungen (mit Titeln) und Aktivitäten.

Ohne Person gibt es nur den Katalog. Schreiben geht über MCP nicht.
Wie jede Quelle ist der Zwilling im Gateway rot, bis der Betreiber
Werkzeuge in eine Sicht freigibt.

## Deutsche Zusammenfassung (0.8)

Die Liste der Objekte eines Typs kann jetzt suchen (`q`: alle Wörter im
Titel) und blättern (`offset`). Damit liest eine App nicht mehr alles und
schneidet bei 500 ab (RFC-0118 P6).

## Deutsche Zusammenfassung (0.10 — Integrations-Clients und die Tür /twin/v1, RFC-0120 Stufe 0)

Ein Integrations-Client `client:<name>` ist ein Programm außerhalb der Plattform, etwa ein
Graph-Viewer, ein Modellierungswerkzeug oder ein Dashboard. Er gehört zu einem Mandanten und liest
genau die Typen, für die der Betreiber ihn bindet (`oaap data twin add-client`). Sein Schlüssel
gilt nur für den Zwilling, wird einmal gezeigt und läuft höchstens 365 Tage. Die neue Tür
`/twin/v1` nennt dem Aufrufer seine Typen (`/twin/v1/types`) und beschreibt sich selbst als
OpenAPI 3.1 (`/twin/v1/openapi.json`). Schreiben kann ein Client noch nicht; das kommt mit Stufe 3.
Schlüssel für Plattform-Prinzipale und mit Plattform-Begrenzungen stellt nur die Plattform aus.

## Deutsche Zusammenfassung (0.11 — die Lesewege der Tür /twin/v1, RFC-0120 Stufe 1)

Ein Programm außerhalb der Plattform kann den Zwilling seines Mandanten jetzt richtig lesen:

- **Listen** je Typ, nach Titel geordnet, seitenweise mit einer Blätter-Marke. Gefiltert wird
  nach Attributwerten, passend zum Werttyp des Attributs (Zahl, ja/nein, Datum, Text; dazu
  `in` und `has`). Ein falscher Filter wird mit einem Satz abgelehnt.
- **Ein Objekt** einzeln abrufen.
- **Nachbarschaft** eines Objekts bis Tiefe 5 sowie die **kürzesten Wege** zwischen zwei Objekten.
- **Export** aller Knoten und Kanten als JSON oder GraphML, also das, was ein Graph-Viewer lädt.
  Persönliche Attribute fehlen darin.
- **Änderungs-Feed** in Reihenfolge, für einen Abgleich, der nichts verpassen darf.

Jede Antwort gilt für einen Zeitpunkt `at` (ohne Angabe: jetzt) und gibt so wieder, wie der
Zwilling damals aussah. Gezeigt werden nur Objekte der Typen, für die der Aufrufer gebunden ist.
Eine Beziehung erscheint nur, wenn beide Enden sichtbar sind.

## Deutsche Zusammenfassung (0.12 — Werte mit Zeitraum, geprüfte Werte, Messreihen; RFC-0120 Stufe 2)

- **Werte werden geprüft, an jeder Tür:** App, Portal, Flotte und Zeiträume prüfen jeden Wert
  gegen den Werttyp seines Attributs, bevor etwas geschrieben wird. Ein falscher Wert lehnt den
  ganzen Schreibvorgang ab, mit einem Satz. „120“ für eine ganze Zahl wird zur Zahl 120; ein
  leeres Feld ist „kein Wert“. Nur die Plattform selbst (Flotte) verliert bei einem falschen Wert
  nur diesen einen, damit ein seltsamer Messwert nie den Flottenzwilling anhält.
- **Werte mit Zeitraum:** Ein Attributtyp kann sagen `"periodic": true` (mit Einheit). Dann
  stehen mehrere Werte nebeneinander, jeder für einen Zeitraum, mit Quelle und Güte – eine
  Kennzahl je Jahr oder Quartal. Zeiträume eines Attributs dürfen sich nicht überschneiden;
  dieselben Grenzen noch einmal korrigieren, `null` zieht zurück; nichts wird gelöscht.
  Eingetragen wird von einer App oder im Portal auf der Seite des Objekts (Formular „Werte mit
  Zeitraum“), gelesen je Zeitraum (Liste, Zeitfenster) und als Wert des Objekts: der Zeitraum,
  der jetzt gilt, sonst der zuletzt abgelaufene – mit seinen Grenzen, damit niemand 2025 für
  heute hält.
- **Messreihen für Personen und Clients:** Ein Integrations-Client liest die Reihen der Objekte,
  die er lesen darf; eine Person sieht sie auf der Objektseite als Verlaufslinie (24 Stunden bis
  ein Jahr). Gemessene Werte bleiben Reihen, gemeldete Kennzahlen sind Zeiträume (D4).

## Deutsche Zusammenfassung (0.13 — Modellieren und Abgleich; RFC-0120 Stufe 3)

- **Clients dürfen schreiben:** Ein Integrations-Client bekommt neben „liest“ jetzt „schreibt“
  (Typen, deren Objekte er anlegt und auf denen er seine eigenen Gruppen pflegt) und „modelliert“
  (er darf eigene Typen des Mandanten anlegen). Die Mandanten-Verwaltung setzt beides auf der
  Seite *Zugänge → Integration*. Alles, was ein Client schreibt, hat die Herkunft
  `client:<name>`. Die Schreibregel des Zwillings gilt unverändert: Eine Gruppe, die eine Person,
  eine App oder die Plattform angelegt hat, wird ihm mit dem Namen des Besitzers verweigert –
  niemand überschreibt jemanden.
- **Typen des Mandanten:** Ein modellierender Client legt Objekttypen an; sie heißen
  `t.<Mandantenkürzel>.<Name>`. Attribut-, Beziehungs- und Gruppenschlüssel werden
  wiederverwendet, wenn sie schon mit derselben Bedeutung existieren, und abgewiesen, wenn sie
  etwas anderes bedeuten. Nur hinzufügen, nie wegnehmen; derselbe Aufruf noch einmal ändert nichts.
- **Abgleich:** Upsert über den eigenen Schlüssel des Werkzeugs (zweimal = ein Objekt), Beziehungen
  über den Schlüssel des Ziels, Umbenennen nur durch den Besitzer (der alte Titel bleibt lesbar),
  Stapel bis 500 Schritte in einer Transaktion unter einer Kennung (dieselbe Kennung noch einmal
  schreibt nichts), Stilllegen statt Löschen: weg aus allem Lesen von heute, in der Geschichte
  noch da, nie wieder beschrieben.
- **Webhooks:** Ein Client meldet eine https-Adresse im Internet an; jede Änderung, die er lesen
  darf, geht signiert dorthin (HMAC mit einem Geheimnis, das er einmal sieht), in Reihenfolge,
  ohne seine eigenen. Fehler: wachsende Wartezeit, nach zehn Fehlversuchen angehalten, im Portal
  sichtbar, wieder aufnehmbar ohne Verlust. Nie ins Netz der Plattform; ein geschlossener Mandant
  verschickt keine. Eingehende Webhooks (§4.10 des RFC) sind noch nicht gebaut (D13 offen).
