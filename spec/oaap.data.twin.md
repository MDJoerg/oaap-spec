# oaap.data.twin — The Digital Twin

- **ID:** `oaap.data.twin`
- **Version:** 0.2
- **Maturity:** draft
- **Based on:** RFC-0031 (data model & digital twin — Twin is Schritt 3
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
`group_key`/`origin` on every write — the outbox (§1).

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
platform hint, nothing more (§3.6): two objects of the SAME type, the
SAME normalised title, created by DIFFERENT origins, neither already
merged away. Merge (`POST /internal/twin/merge`, body `{"keep",
"drop"}`) and unmerge (`POST /internal/twin/unmerge`, body `{"drop"}`)
are human acts, `tenant_admin` only, each recording one `events` row
with `origin: "tenant:<username>"` so the audit trail names who acted,
not only that a write happened. Merging objects of two different types
is refused outright — a mistake, not a duplicate.

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
  row — nothing is silently dropped, even if nothing reads that row
  yet.

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

`draft` — becomes `beta` once conformance tests 1–10 pass on the
reference platform (`oaap-test`), and step 8 of RFC-0031 §9 (the
rehearsal's own copy, D8) has its own capability-spec addendum once
built — the one piece 0.2 still satisfies by refusal alone (§1, §4).

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
