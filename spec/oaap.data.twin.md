# oaap.data.twin — The Digital Twin

- **ID:** `oaap.data.twin`
- **Version:** 0.1
- **Maturity:** draft
- **Based on:** RFC-0031 (data model & digital twin — Twin is Schritt 3
  of the build order: Store, Model, Twin, reference apps, browser, then
  broker) §3, §6, §8, §9; `oaap.data.store` (every tenant's twin is a
  schema in it); `oaap.data.model` (the registry this service reads —
  it never holds a type definition of its own); RFC-0027 (machine
  principals — an instance authenticates as itself); RFC-0016 (app
  network isolation — why this service sits behind the gateway, not
  beside the app)

## 1. Purpose

The **only service an app talks to for shared tenant data** (RFC-0031
§2). It answers *which objects exist, who says what about them, and
what held when?* — the instance layer beneath `oaap.data.model`'s type
layer. An owner creates an object with its own core group; a
contributor writes into its own group on someone else's object; a
consumer reads. Origin and tenant come from the caller's own
credential, never from anything the request says (§4).

**0.1 builds RFC-0031 §9's own minimum**: steps 1–3 of the eight-step
conformance scenario — an owner creates an object with its core group;
a reader gets an object back with every group its type is bound to;
a contributor writes into its own group on a foreign object. Recorded
time is kept always (append, never overwrite, §2.3); validity
(`valid_from`/`valid_to`) is carried on attributes and relations and
returned with them, because RFC-0031 §9 step 1 already exercises it
("relates them with `isContactOf` valid from 2019") — but **nothing in
0.1 filters by it**. Concretely NOT built yet, named here rather than
silently missing (RFC-0031 §9 steps 4–8, and non-goals §10):

- **`?at=` and the tree** (§9 step 7) — reading what held at a past
  date, and the recursive-CTE object graph. 0.1's `GET .../objects/{id}`
  always answers with every current row.
- **`/twin/references`** (fuzzy search over titles/source keys, D6's
  reference tuple) — nothing to search yet without it.
- **Duplicate detection and merge** (§9 step 6, §3.6) — two origins
  creating the same real-world thing is not noticed in 0.1.
- **Restricted groups** (D7's second half) — 0.1's read rule is the
  simple half only: an instance may read every group of a type it
  contributes to or consumes; marking one group `restricted` to named
  readers is not implemented.
- **The rehearsal's own schema copy** (D8, §9 step 8) — RFC-0030 is not
  wired to this capability at all yet. Deliberately refused rather
  than half-built: §2.2 and §4 say exactly what a rehearsal instance
  gets instead (nothing that reaches this service).
- **The outbox reader** (RFC-0032) — every write appends one `events`
  row (§2.3); nothing reads that table yet. Free to build on top later
  without touching a write path.
- **The twin browser** (Schritt 5) and the AAS repository API (own,
  later RFC) both read this service's model; neither exists yet.

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
filtering (§1); no `?at=` (§1).

### 2.7 `PUT /twin/objects/{id}/groups/{group}`

Write into one group. Refused unless the caller `contributes` to the
object's type. If the group already exists under a **different**
origin, refused — RFC-0031 §3.3's "nobody else writes there," enforced
here, not trusted from the caller. Otherwise creates the group (first
writer becomes its origin) or appends to it: each attribute/relation
key is compared to its current row, and a value that has not actually
changed writes nothing — the history stays honest, not a row per
identical PUT. Records one `events` row. Returns `204`.

### 2.8 What §9's remaining steps need (deferred, not designed)

Steps 4 (a second object of the same type from a different origin —
already possible today, since ownership is per-type, not per-object;
worth a conformance test, not new code), 5 (a `data_models` group type
with no app, filled from the twin browser — needs Schritt 5), 6 (merge
— needs detection rules and an audit-logged human action, §3.6), 7
(`?at=` and the tree — needs validity-aware view queries and a
recursive CTE), 8 (rehearsal copy, D8 — needs `oaap.data.store`'s
schema-copy mechanism bound to a rehearsal's lifecycle, mirroring
RFC-0030 D6's general answer for shared data holdings).

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

## 4. Security requirements

- The caller's tenant and origin come from its resolved credential
  (`X-OAAP-User: instance:<name>` → the registry's own record of that
  instance), never from a request field. A body that named a tenant
  would be ignored even if sent — nothing in 0.1's request handling
  reads one.
- A human session reaching `/twin/*`, however it authenticated, is
  refused: `X-OAAP-User` must start with `instance:`.
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

Steps 4–8 of RFC-0031 §9 are out of scope for 0.1 (§1, §2.8) and are
not conformance tests here yet.

## 6. Dependencies

`oaap.data.store` (every tenant's twin is one of its schemas, provi-
sioned by the same host-side DDL pattern `oaap.data.model` already
uses); `oaap.data.model` (the registry read directly, `oaap_model.*`,
granted per tenant schema); `oaap.apps.runtime` (the install hook that
mints the E1 key and provisions the schema — one place, like the
`data_model` hook it sits beside); RFC-0027 (machine principals — the
credential mechanism, and specifically D5's `--instance` scoping,
which this capability relies on to keep the E1 key from reaching any
route beyond `/twin/*`, §2.2); RFC-0016 (app network isolation — the
reason this service is reached
through the gateway and not by a direct network link); RFC-0030 (the
rehearsal rule this capability currently satisfies by refusal, §2.2,
until D8 is built).

## 7. Maturity

`draft` — becomes `beta` once conformance tests 1–5 pass on the
reference platform (`oaap-test`), and steps 4–8 of RFC-0031 §9 each
have their own capability-spec addendum once built (§2.8 lists what
each needs).

## Deutsche Zusammenfassung (v0.1)

**Der einzige Dienst, mit dem eine App für gemeinsame Mandantendaten
spricht** (RFC-0031 Schritt 3). Objekte, Gruppen, Attribute, Relationen
und Aktivitäten je Mandantenschema (`twin_<mandant-id>` im `store`,
`oaap.data.store`), **append-only**: eine Änderung ist immer eine neue
Zeile, nie ein Überschreiben — `current_*`-Sichten sind die eigentliche
Schnittstelle. Herkunft und Mandant kommen ausschließlich aus dem
Berechtigungsnachweis des Aufrufers (Maschinen-Prinzipal `instance:
<name>`, RFC-0027), nie aus der Anfrage selbst.

**0.1 baut genau das Minimum, das RFC-0031 §9 selbst dafür nennt**:
Owner legt ein Objekt mit seiner Kern-Gruppe an, ein Leser bekommt es
mit allen gebundenen Gruppen zurück, ein Contributor schreibt in seine
eigene Gruppe auf einem fremden Objekt — „niemand sonst schreibt dort"
wird am Dienst selbst erzwungen, nicht dem Aufrufer vertraut. **Bewusst
noch nicht gebaut** (§1, §2.8): `?at=`/Baum, Referenzsuche, Dubletten-
Erkennung/Merge, `restricted`-Gruppen, der Outbox-Leser (RFC-0032), und
vor allem **die Generalprobe (D8)** — eine Generalprobe bekommt in 0.1
absichtlich **gar keinen** Zwilling-Schlüssel, weil ihre eigene Schema-
Kopie noch nicht existiert und das Mandantenschema sonst das
**produktive** wäre. Lieber ehrlich verweigert als halb gebaut.

**Nachtrag nach der ersten Live-Prüfung (2026-09-10):** der Maschinen-
Schlüssel wird jetzt mit RFC-0027s `--instance`-Bindung ausgestellt, auf
den reservierten Wert `oaap.twin` — nicht mehr ungebunden. Ein
ungebundener Schlüssel wird von `identity` nirgends außer nach Rolle
und Mandant abgewiesen; er hätte damit auch jede andere App im selben
Mandanten mit derselben Rolle geöffnet, nicht nur `/twin/*` — live auf
`oaap-test` nachgewiesen, siehe CURRENT_STATE 125.

Der Dienst läuft als eigener, kleiner Plattform-Container (`twin`),
am selben Knotenprofil `store` wie `oaap.data.store` selbst, erreichbar
ausschließlich über die Gateway-Route `/twin/*` — eine App-Instanz kann
ihn wegen der Netz-Isolation (RFC-0016) sonst gar nicht erreichen. Das
Schema-Passwort (RFC-0031 §7: „einmal gezeigt, nie einer App, nur
`oaap.data.twin`") liegt in einer Datei, die ausschließlich dieser
Container lesend mountet.
