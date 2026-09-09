# oaap.data.store — Managed Postgres per Node

- **ID:** `oaap.data.store`
- **Version:** 0.1
- **Maturity:** draft
- **Based on:** RFC-0031 (data model & digital twin — Store is Schritt 1
  of the build order: Store, Model, Twin, reference apps, browser,
  then broker), RFC-0011 (node profiles — this spec registers the
  profile `store`, see `oaap.core.host` 2.5), `oaap.data.backup` 0.3
  (dump becomes required backup content), RFC-0030 (rehearsal — the
  schema-copy mechanism this spec offers), `oaap.core.tenant`
  (tenant-id is the schema's stable namespace, never the Kürzel)

## 1. Purpose

One **managed Postgres instance per node**, offered as a platform
service — not an app, not addressable by anything outside the platform
network — carrying **one schema per tenant and purpose**
(`twin_<tenant-id>`, later `app_<instance-id>`). It is the foundation
`oaap.data.model` and `oaap.data.twin` store their data in; nothing
else in RFC-0031 can be built before it, which is why it is Schritt 1.

A node does not automatically carry it. Postgres wants memory a small
node does not have to spare, so whether a node offers `store` — and
therefore the twin — is a **profile decision** (RFC-0011), stated on
the machine, never assumed.

Out of scope for 0.1: per-app schemas (`app_<instance-id>` is named
above as the later case, not built here), a query interface for apps
(apps talk to `oaap.data.twin`/`oaap.data.model`, never to `store`
directly — RFC-0031 §6), replication across nodes (that is
`oaap.events.queue`/RFC-0032 territory).

## 2. Interface

### 2.1 The service

- A platform service `store` (e.g. `pgvector/pgvector:pg16`, see §3),
  healthcheck `pg_isready`, reachable **only from the platform
  network** — no published port, ever. Nothing outside the platform's
  own containers can reach it directly.
- **Node profile `store`** (new, registering with RFC-0011 /
  `oaap.core.host` 2.5): a node carries the service only when profiled
  for it. A node without the profile MUST report `store: not carried`
  from `oaap data store status` and MUST NOT attempt to start the service.
  The portal MUST state plainly that data-model/twin capabilities are
  unavailable on such a node, rather than failing opaquely the first
  time an instance tries to bind to them.
- `install.sh`/`migrate.sh`: an existing node that gains the `store`
  profile gets the service on its next update; a node without the
  profile is never touched, so a Raspberry Pi in the fleet never ends
  up carrying a Postgres nobody asked it to run.

### 2.2 Schemas

- `oaap data store schemas` — lists schemas on this node with purpose,
  tenant, size, and role name (never the password).
- `oaap data store create <purpose> <tenant-id>` — creates schema
  `<purpose>_<tenant-id>` plus a **dedicated role and password**,
  scoped to that one schema (`GRANT` only on it). The password is
  printed **once**, exactly like a machine-principal key (RFC-0027);
  it is not retrievable afterwards, and it is handed to the consuming
  platform service (`oaap.data.twin`), never to an app.
- `oaap data store drop <schema>` — refuses without `--yes`; drops
  schema and role together, so no orphaned role outlives its schema.
- **The tenant-id, never the Kürzel, in the schema name.** The
  tenant-id is stable (RFC-0026); the Kürzel is meant to be renamed
  freely. A schema name that outlives a rename would either freeze the
  Kürzel (defeating RFC-0025/0026) or quietly keep naming a tenant that
  no longer calls itself that.

### 2.3 Copy, for the rehearsal (RFC-0030 D6/D8)

Postgres has no "copy this schema" command. The implementation:

1. `pg_dump -n <schema>` the source schema.
2. Rewrite the schema name inside the dump to `<schema>_r_<instance-id>`.
3. Restore it under a **new role**, distinct from the source schema's
   role — a rehearsal's credentials are never the production ones
   (parity with RFC-0030 D3, which already says this for app secrets).
4. `oaap data store copy <schema> <new-name>` exposes this as one command,
   called by `oaap app rehearse`, never directly by an app or a
   tenant-facing surface.

The command MUST measure the source schema's size first
(`pg_total_relation_size` summed per table) and refuse with a clear
reason — no partial schema left behind — when the node does not have
room, using the same wording pattern as the rehearsal's disk-space
check in `oaap.apps.runtime`.

### 2.4 Backup

`store` has no command of its own for this — it extends
`oaap.data.backup`'s required content (its §2.1). A node profiled for
`store` MUST have its schemas included in every platform backup as a
**dump** (`pg_dump`/`pg_dumpall`), not a copy of the data directory
while stopped:

- A dump survives a Postgres major-version change across a relocation
  (RFC-0029 "Umzug"); a data-directory copy does not.
- The dump runs in the same window `oaap.data.backup` already stops
  apps for — it does not need its own downtime, but it does need its
  own completeness check: a backup taken from a node that carries
  `store` and does not include its dump MUST fail and leave no archive,
  exactly like the 2026-09-05 finding that produced a 9 KB "backup" of
  899 MB (`oaap.data.backup` 0.1.4).
- Restore recreates the schemas and roles from the dump before any app
  instance starts, so nothing depending on `oaap.data.twin` comes up
  against an empty store.

### 2.5 Restore and relocation — where this departs from the profile rule

`oaap.core.host` 2.5 says a profile is never restored from a backup
(RFC-0011 decision 4), because `dev`/`exposed` are *powers granted to
the operator's tooling*, and a workbench backup must not hand a
production box those powers by accident. `store` is not that kind of
profile: it says whether the machine has the infrastructure a tenant's
*data* depends on, and RFC-0029 §"Umzug" already treats relocation as
first-class. Silently dropping it would mean a relocated node comes up
with `oaap.data.twin` pointed at a store that was never recreated — the
exact shape of silent breakage this project has already paid for twice
([[leser-eines-bezeichners]], the 9 KB backup).

The resolution keeps both rules true without contradicting either:

- The profile itself still follows RFC-0011 D4 — restore MUST NOT set
  `store` on the new machine automatically. It stays a named, deliberate
  act, exactly like `dev`/`exposed`.
- The **data** MUST NOT be silently discarded because of that. A backup
  taken on a node profiled for `store` MUST carry the dump inside the
  archive as ordinary restorable content (it is not a profile, it is
  data), and restore MUST extract it and tell the operator plainly what
  it found and what to do: *"this backup carries a managed-Postgres
  dump for N schema(s) — add the profile and replay it:
  `sudo oaap node add-profile store && oaap data store restore <path>`"*.
- `oaap data store restore <dump-file>` (new) replays a previously
  extracted dump into a **running, freshly profiled** store service.
  It MUST refuse if any schema it would create already exists, so a
  restore never overwrites data a fresh install already produced.

## 3. Configuration

- Postgres image (provider-defined default `pgvector/pgvector:pg16` —
  brings `pgvector` along for later search, ships an arm64 build so the
  fleet's Raspberry Pi is not excluded a second time).
- Superuser password: a **platform** secret, generated at install time,
  stored in the platform `.env` alongside `OAAP_INTERNAL_KEY` and never
  logged or shown.
- Resource limits (`shared_buffers` etc.): provider-defined per node
  size; a 2 GB node is configured small or not profiled for `store` at
  all — a setting, not a hope.
- Data path: under the platform data directory, alongside the other
  platform-owned state (never under a tenant's own tree).

## 4. Security requirements

- The superuser role MUST never be reachable by, or its password known
  to, anything outside the `store` service's own operator tooling. It
  creates and drops schemas/roles; it never answers an app's query.
- A schema's role MUST be scoped to that schema alone (no cross-schema
  grants). `oaap.data.twin` holds these credentials as its own platform
  secret; an app never sees a database credential — it speaks to the
  twin service, which is the only thing with a `store` password
  (RFC-0031 §6, §8).
- No published port. The service MUST be reachable only from the
  platform's internal network, the same boundary `identity` and
  `portal` already sit behind.
- A rehearsal copy MUST use a role distinct from the schema it was
  copied from, and that role MUST be dropped together with the copy's
  schema on expiry (parity with the app-secret rule in RFC-0030 D3:
  a rehearsal never inherits production credentials).

## 5. Conformance tests (described)

1. **Schema lifecycle:** `oaap data store create twin <tenant-id>` on a node
   profiled for `store` produces a schema and a role whose password is
   shown exactly once; writing and reading rows through that role
   succeeds; a second tenant's schema is unreachable through the first
   tenant's role.
2. **Backup and restore round trip:** with rows in a schema, a platform
   backup includes a dump of it (checked by reading the archive, not
   the code); restore extracts the dump and names it and the exact
   replay command, **without** setting the `store` profile itself;
   after `add-profile store` and `oaap data store restore`, the schema
   reappears with identical rows and a working (new) role.
3. **Rehearsal copy:** a schema with 10 000 rows, copied via
   `oaap data store copy`, yields a new schema with the same row count under
   a **different** role; the source schema and role are unchanged;
   dropping the copy drops both schema and role.
4. **Refusal without room:** a copy attempted where the target has less
   free space than the measured source size is refused with a stated
   reason and leaves no partial schema.
5. **Profile gating:** a node without the `store` profile answers
   `oaap data store status` with `not carried`, never attempts to start the
   service, and the portal states that data-model/twin capabilities are
   unavailable there. A node that gains the profile gets the service on
   its next update; one that never had it is never touched.

## 6. Dependencies

`oaap.core.host` (RFC-0011 node profiles, §2.5 — this spec is the first
consumer of a profile beyond `dev`, and registers the name `store`
there), `oaap.data.backup` (dump becomes required content of every
backup taken on a node profiled for `store`), `oaap.core.tenant`
(tenant-id as the stable namespace a schema name is built from),
`oaap.apps.runtime` (the rehearsal mechanism `oaap data store copy` is
called from).

## 7. Maturity

`draft` — becomes `beta` once conformance tests 1–4 pass on the
reference platform (`oaap-test`); test 5 (profile gating) is proven
across at least two nodes, one profiled and one not.

## Deutsche Zusammenfassung (v0.1)

**Ein verwaltetes Postgres je Knoten**, mit **einem Schema je Mandant
und Zweck** — die Grundlage, auf der `oaap.data.model` und
`oaap.data.twin` (RFC-0031) ihre Daten ablegen. Kein Knoten trägt es
automatisch: Postgres will Arbeitsspeicher, den ein kleiner Knoten
nicht hat, deshalb entscheidet ein **Knotenprofil** (`store`,
RFC-0011), ob ein Knoten die Fähigkeit überhaupt anbietet — sichtbar im
Portal, nie stillschweigend fehlend.

**Ein Schema, eine Rolle, ein Passwort — einmal gezeigt.** Die
Mandanten-ID steht im Schemanamen, **nie das Kürzel**: die ID ist
stabil, das Kürzel ist zum Ändern gedacht (RFC-0025/0026). Eine App
sieht nie ein Datenbank-Passwort — sie spricht mit dem Zwillingsdienst,
und nur der hält ein `store`-Geheimnis.

**Kopieren für die Generalprobe** (RFC-0030): Postgres kann kein Schema
kopieren, also läuft es über `pg_dump` → Namen im Dump ersetzen →
Einspielen unter neuer Rolle. Die Kopie bekommt **immer** eine andere
Rolle als das Original — dieselbe Regel, die RFC-0030 D3 schon für
App-Geheimnisse verlangt.

**Sicherung als Dump, nicht als Verzeichniskopie**: ein Dump überlebt
einen Postgres-Versionswechsel beim Umzug, eine Verzeichniskopie nicht.
Ein Knoten mit `store`-Profil, dessen Sicherung den Dump vergisst, MUSS
scheitern und kein Archiv hinterlassen — dieselbe Lehre wie beim 9-KB-
„Backup" vom 05.09.

**Ausnahme von der Profil-Regel, bewusst begründet:** Profile werden
nach RFC-0011 D4 nie automatisch wiederhergestellt — richtig für `dev`
und `exposed`, die dem Portal Macht geben. `store` ist aber keine Macht,
sondern die Grundlage, auf der Mandantendaten stehen; beim Umzug (RFC-
0029) einfach wegzulassen wäre genau die stille Lücke, die dieses
Projekt zweimal Geld gekostet hat. Deshalb: **das Profil bleibt
Handarbeit** wie bisher, aber **der Dump geht nie verloren** — die
Wiederherstellung entpackt ihn und nennt den genauen Befehl
(`sudo oaap node add-profile store && oaap data store restore <Pfad>`),
statt ihn stillschweigend fallenzulassen.
