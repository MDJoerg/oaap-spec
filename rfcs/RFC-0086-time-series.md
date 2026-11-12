# RFC-0086: Time Series — Values Over Time as a Platform Capability, Plain PostgreSQL by Default

- **Status:** **Accepted (2026-11-12)** — D2–D8 as recommended; D1 amended
  by Jörg: text values (status) get a history too, with a bounded length
  (§2.1, §4.4). **Stage 1 built and measured (reference 0.1.270,
  §10.1–10.2)**
- **Date:** 2026-11-12
- **Authors:** Jörg (the need: "we probably have to talk about time series
  as a data type and capability of the platform"; "solved as always: a
  simple default that is unobjectionable in licence terms, and other
  variants through abstraction"), Claude (facts read in reference 0.1.264,
  design)
- **Depends on:** RFC-0031 / `oaap.data.twin` (objects, tenant schema),
  `oaap.data.store` 0.2 (the node's Postgres), RFC-0051 (tiers, gaps, the
  sample format), RFC-0085 (the first writer: the fleet service),
  RFC-0081 (backup classes), RFC-0030 (rehearsal copy)
- **Not part of this RFC:** dashboards and charts (the fleet app draws its
  own, RFC-0085 stage 4–5); an external query protocol (Prometheus, Influx
  line protocol, Grafana data source); free text, messages and log lines
  (those are events); the node's own local history (RFC-0051 stays as it
  is).

## Summary

The platform has a twin that knows *what is* — objects, attributes,
relations, and for each group the snapshot at each change (`states`). It
has no place for *how a value moved*: CPU of a node every minute for a
year, the temperature of a machine, the number of open cases per day. Each
node keeps four hours to a month of its own metrics in files (RFC-0051),
and that is all.

This RFC adds **`oaap.data.timeseries`**: values over time, attached to a
twin object — **numbers**, kept in tiers that shrink with age, and short
**texts** such as a status (at most 64 characters), kept as their changes —
queried by range and step. The default runs **in the node's existing PostgreSQL with
nothing added** — no extension, no new service, PostgreSQL licence only.
Other stores (VictoriaMetrics, InfluxDB 3 Core, the Apache-licensed part of
TimescaleDB) can be put behind the same interface later; one test suite,
run against every driver, is what keeps the interface honest.

## 1. Facts (read 2026-11-12, reference 0.1.264)

1. **The store** is one PostgreSQL 16 per node (`pgvector/pgvector:pg16`),
   only on nodes with profile `store`, one schema per tenant and purpose
   (`twin_<tenant-id>`), each with its own role; no published port; apps
   never talk to it, they talk to the twin's API (`oaap.data.store` §1,
   §2.2). PostgreSQL 16 has declarative range partitioning in core.
2. **The twin keeps snapshots, not series.** `states` holds one row per
   group change with the group's attributes as JSON (RFC-0032 §1.4). A
   per-attribute history "reads `payload` apart" — no reader exists, and a
   group written every minute would make `states` the time series by
   accident, with JSON per point.
3. **RFC-0051's tiers work** and are the model: raw → 5 min → 30 min →
   2 h, each interval with **mean, minimum and maximum**, a gap stored as a
   gap, never filled. Sample format `{"v","node","t","m","x"}`.
4. **The first writer exists on paper:** RFC-0085's fleet service receives
   every metric of every node over the broker and has to keep it somewhere
   (RFC-0085 §5.5). Rough volume for the fleet today: five nodes, about ten
   series each, one point a minute — about 72 000 points a day.
5. **The hub has no store yet** (oaap-demo, RFC-0085 D11 gives it one).

## 2. The model

| Term | Meaning |
|---|---|
| **series** | one measured quantity of one twin object: `(object, measure, labels)` — e.g. node *oaapx01*, `cpu`, `{}`; or machine *M4*, `temperature`, `{"sensor":"spindle"}` |
| **kind** | `number` or `text`, fixed when the series is created (§2.1) |
| **point** | `(t, x)` — a time in UTC and a value of the series' kind |
| **policy** | which tiers a series keeps, and how long (§4) |
| **bucket** | one interval of a tier, holding mean, min, max and count |

- **A series belongs to a twin object** of the same tenant. No object, no
  series. That keeps the tenant boundary where it already is, gives every
  series a title, a type and an owner, and lets the picture of RFC-0085 find
  a node's series from the node.
- **`measure`** is a key (`[a-z][a-z0-9_.]{0,62}`); **`labels`** a small
  map of at most 8 string pairs; **`unit`** a free string set at creation
  (UCUM spelling recommended: `%`, `Cel`, `By`, `1/min`).
- The twin keeps the **latest** value as an ordinary attribute when a
  writer wants that (RFC-0085's `latest` group); the series keeps the
  history. Neither replaces the other.

### 2.1 Two kinds: numbers and short texts (D1, amended by Jörg)

- **`number`** — a double. Tiers with mean, min, max, count (§4.1–§4.3).
- **`text`** — a status-like word or short phrase: `healthy`,
  `degraded`, `in Wartung`, `running`. **At most 64 characters** (Unicode
  code points), no control characters, no line breaks; a longer value is
  refused with a reason, never cut. Text series are kept as **changes**
  (§4.4).
- **Not a log.** A text series answers "which state was it in, and when
  did it change". Messages, free text and log lines are events
  (RFC-0080, RFC-0032) — the length bound is what keeps the two apart.
- **Difference to the twin's `states`** (fact 2): `states` holds a
  snapshot of a whole group at each twin write, as a projection the relay
  makes. A text series is the deliberate history of **one** value,
  written by whoever measures it — the fleet service writes a node's
  liveness (`up`/`silent`/`unknown`) as one, every minute, without writing
  the twin every minute.
- An optional **expected interval** per series (e.g. 60 s) makes gaps
  visible for text as for numbers (§4.4).

## 3. The interface

Served **by the twin's service**, under its own path, with the twin's
keys and scopes — an app holding a twin key for a tenant may read (and, if
granted, write) that tenant's series and nothing else.

| Call | Does |
|---|---|
| `PUT /series` | create or find a series: object, measure, labels, kind, unit, policy, optional expected interval; answers its id |
| `POST /series/{id}/points` | append points (a batch, at most 10 000) |
| `POST /points` | append points for several series in one call (the fleet service's form) |
| `GET /series?object=…` | the series of an object |
| `GET /series/{id}/range?from&to&step` | numbers: buckets of mean/min/max/count, `step` picks the tier (§4.3); texts: the state intervals, or per bucket the value at its end, the number of changes and the longest-held value (§4.4) |
| `GET /series/{id}/latest` | the last point |
| `DELETE /series/{id}` | removes the series and all its points; confirmed, audited |

**Writing is idempotent.** A point with a time that already exists for the
series replaces nothing and is counted as a duplicate — an MQTT QoS 1
resend (RFC-0052) must not double a value. **Late points** inside the raw
retention are accepted, and the affected buckets are recomputed at the
next roll-up; older ones are refused with a reason and counted.

**Limits per tenant**, refused with a reason, never silently dropped:
series count (default 10 000), points per minute (default 20 000). They
protect the node, and a tenant that needs more says so.

## 4. Tiers and policies

### 4.1 Named policies, not free configuration

A series names one policy; policies are defined by the platform:

| Policy | raw | 5 min | 1 h | 1 day |
|---|---|---|---|---|
| `standard` | 7 days | 31 days | 400 days | 10 years |
| `short` | 2 days | 7 days | — | — |
| `long` | 31 days | 400 days | 10 years | 10 years |

`standard` keeps a node's year at hourly resolution and its decade by day,
and its minimum and maximum survive every step (RFC-0051's reason: a spike
must not vanish from the yearly chart). A new policy is a change of this
spec, not a setting — a hundred hand-made retention rules is how time
series stores fill disks unnoticed.

### 4.2 Rolling up

A bucket is computed once its interval has closed (plus a grace of two
intervals for late points) from the tier below it. A gap stays a gap: a
bucket with `count = 0` is not written, and a reader draws it as missing.

### 4.3 Reading

`range` chooses the **coarsest tier whose resolution is not coarser than
`step`** and that still covers `from`; if `from` lies beyond that tier's
retention, it falls back to the next coarser tier and says so in the
answer (`"tier": "1h"`). A chart never gets more than about 2 000 buckets;
a request that would yield more is answered with a coarser tier.

### 4.4 Text series: changes, not samples

A status written every minute is the same word 1 440 times a day. A text
series therefore keeps **one row per state interval**: `(from, value,
last_seen)`.

- A point with the **same** value as the open interval moves its
  `last_seen` forward; nothing else is written.
- A point with a **different** value closes the open interval and opens a
  new one.
- **Gaps:** if the series has an expected interval and a point arrives
  more than **three intervals** after `last_seen`, the old interval ends at
  `last_seen`, the time between is a gap (*unknown*), and a new interval
  opens — even with the same value. Without an expected interval a state
  holds until the next change.
- **Reading** returns the intervals clipped to `[from, to]`; with a
  `step`, one bucket per step with the value at its end, the number of
  changes inside it, and the value held longest in it.
- **Retention:** the intervals are kept as long as the **longest tier** of
  the series' policy (`standard`: 10 years). They are few: a node that
  changes state five times a day has about 18 000 rows in ten years.
- **Duplicates and late points:** a point at a time already covered by an
  interval with the same value is a duplicate and counted; a late point
  with a different value inside the raw retention splits the interval it
  falls into; older ones are refused and counted (as for numbers, §3).

## 5. The default driver: plain PostgreSQL

- **One schema per tenant**, `ts_<tenant-id>`, with its own role — beside
  the twin's schema, not inside it, so that its size, its backup and its
  copy for a rehearsal can be treated apart (§6).
- **Tables:** `series` (id, object id, measure, labels, kind, unit,
  policy, expected interval, created); `points` (series id, t, x double),
  **partitioned by day**; one table per rolled-up tier (series id, t,
  mean, min, max, count), **partitioned by month**; `text_states` (series
  id, from, value `varchar(64)`, last seen), **partitioned by year** — the
  length bound is also a column type, so the database refuses what the API
  might let through. Primary keys `(series_id, t)` make writing idempotent
  (`ON CONFLICT DO NOTHING`).
- **Retention is dropping partitions**, never `DELETE` — cheap, and it
  leaves no bloat behind.
- **One platform job** (the store node's minutely unit) creates the next
  partitions ahead of time, rolls up closed buckets and drops expired
  partitions; it never fails the unit (the rule of RFC-0051 and
  RFC-0052).
- **Licence:** PostgreSQL License only. No extension is loaded; the image
  stays the one `oaap.data.store` already uses.
- **Expected size for the fleet** (fact 4): about 72 000 raw points a day,
  about 500 000 kept raw under `standard` — tens of megabytes with indexes.
  Measured in stage 1, not trusted from this estimate.

## 6. The abstraction

- A **driver** implements one interface: `ensure_series`, `write`,
  `range`, `latest`, `list`, `drop_series`, `roll_up`, `expire`,
  `export`, `import`. The service calls only this interface.
- **The driver is chosen per node** (`oaap data timeseries driver …`),
  because a driver other than PostgreSQL is a service on that node; the
  default is `postgres`. Changing the driver of a node with data is an
  export into the new driver, measured, never in place.
- **One conformance suite** — idempotency, late points, gaps, tier choice,
  min/max surviving roll-up, text intervals (same value extends, change
  opens, gap after three intervals, 65 characters refused), limits, tenant
  boundary, export/import round trip — runs against every driver. A driver that fails it is not offered.
- **Named candidates, none built:** VictoriaMetrics (Apache-2.0),
  InfluxDB 3 Core (MIT/Apache-2.0), TimescaleDB **Apache-2.0 edition**
  (without the features under the Timescale License). Each would be its own
  small RFC with its measurement.
- **Backup and copy go through `export`/`import`** — the default driver's
  export is `pg_dump -n ts_<tenant-id>`, so the tenant's backup (and its
  class, RFC-0081) includes its series exactly as it includes its twin. A
  rehearsal (RFC-0030) copies series **only when asked**: history is
  rarely what a rehearsal tests, and it can be the largest part of a
  tenant.

## 7. Writers

1. **The fleet service** (RFC-0085): every `metrics` message of a node
   becomes a point of that node's series in `oaap-ops`, and its liveness
   (`up`/`silent`/`unknown`) and each instance's state from `status` become
   text series — and in each
   provider tenant whose profile includes `metrics` (RFC-0085 §7). A copy
   per receiver is accepted: it keeps every tenant's data in its own
   schema, revocable by dropping it.
2. **Apps**, through the API with a twin key.
3. **Later, a recorder:** a platform helper that subscribes to a tenant's
   topics on its broker and records numeric payloads as points — the piece
   RFC-0032 step 3's simulated machine and a real device need. Its own
   stage (§10), not required by the fleet.

## 8. Security

- Tenant boundary: own schema and role per tenant; the API resolves the
  tenant from the key, never from the request; a series of another
  tenant's object cannot be created (the object is resolved in the
  caller's twin).
- No port, no direct database access for apps or external tools (the
  store's rule). External dashboards read over the broker (RFC-0085 §7.2)
  or, later, over a read API of their own RFC.
- Deleting a series is confirmed and audited; dropping expired partitions
  is not a deletion by a person and is logged as a count per day.

## 9. Decisions asked of Jörg

1. **A capability of its own, `oaap.data.timeseries`** (§2)? Proposed:
   numbers only. **Decided (Jörg): numbers and short texts** — "we also
   need a history for texts like status; we can limit the permitted
   length" → kind `text`, at most 64 characters, kept as changes (§2.1,
   §4.4).
2. **Every series belongs to a twin object** (§2)? Recommended: yes.
   Alternative: free-standing series — simpler for a quick app, but outside
   the tenant's twin and without a title or owner.
3. **Served by the twin's service, with its keys** (§3)? Recommended: yes.
   Alternative: a service of its own (one more container per store node).
4. **Default driver: plain PostgreSQL in the existing store, schema
   `ts_<tenant-id>`, daily and monthly partitions, no extension** (§5)?
   Recommended: yes.
5. **Three named policies (`standard`, `short`, `long`); new ones only by
   spec change** (§4.1)? Recommended: yes.
6. **Driver per node, one conformance suite for all; alternatives named,
   none built** (§6)? Recommended: yes.
7. **Idempotent writes; late points accepted within the raw retention;
   limits per tenant refused with a reason** (§3)? Recommended: yes.
8. **Series are in the tenant backup; a rehearsal copies them only on
   request** (§6)? Recommended: yes.

## 10. Stages and what is measured

1. **The spec and the default driver.** `oaap.data.timeseries` 0.1, the
   PostgreSQL driver, the API in the twin service, the job, the CLI.
   **Measured on oaap-test** with a simulated clock (a year of points for
   fifty series in minutes, as RFC-0051 did): roll-up keeps min/max, a gap
   stays a gap, a text series written every minute for a year holds one
   row per change, partitions are dropped on time, a duplicate is counted, a
   late point recomputes its bucket, the conformance suite green, the size
   per million points written down.
2. **The fleet writes.** RFC-0085's fleet service writes into `oaap-ops`
   (RFC-0085 stage 5). Measured: a week of five real nodes, a hub restart
   with the broker's backlog arriving without duplicates.
3. **The charts** in the fleet app (`range` with step).
4. **The recorder** for tenant topics, with RFC-0032 step 3's simulated
   machine as its first user.
5. *Later, if wanted:* a second driver, as the proof that the abstraction
   holds.

### 10.1 Stage 1, first half — measured 2026-11-12 on oaap-test

The driver (`platform/services/twin/timeseries.py`) and the conformance
suite (`test/test_timeseries.py`) against a throwaway PostgreSQL 16 of
the store's image: **all green**; three deliberate faults (mean of means,
a duplicate overwriting, no text gap rule) each turned it red. The suite
found one real fault first: a refused call left its transaction open
and held its locks — every public call now rolls back on error.

**A simulated year** (`test/measure_timeseries.py`): 50 number series and
one status series, one point a minute, policy `standard`, job once per
simulated day.

| | |
|---|---|
| points written | 26.28 million in 25 minutes (≈ 19 000 per second); the job 107 s in total, ≈ 0.3 s per day |
| size after 7 days | 57 MB for 504 000 points — **≈ 113 MB per million raw points**, indexes and tiers included |
| size after a year | **186 MB**; raw stays at 576 000 rows (8 days: retention at day granularity), 5 min ≈ 0.6 million, 1 h 438 000 and growing to 400 days, 1 day 18 100 |
| spike | a value of 1000 on one day is the maximum of that day's 1-day bucket |
| status series | 4 changes a day for a year: **1 461 rows**, not 525 600 |
| a year in weekly steps | answered from tier `1d`, 52 buckets |

This is the fleet's size today (five nodes, about ten series each).
Departures recorded in the spec: tables per policy (retention by
partition needs it) and `text_states` not partitioned (an interval
belongs to its `last_seen`).

### 10.2 Stage 1, second half — built and measured 2026-11-12 on oaap-test

Reference 0.1.270: the interface in the twin's service (§3), `oaap data
timeseries enable|show|job`, the job as a step of the minutely unit, the
tenant archive. Rights come from the object's type (`contributes` writes,
any binding reads, a remote reader only reads), deletion needs
`?confirm=<id>` and is audited, the minute's allowance is counted in the
tenant's schema so both workers of the service share it.

**Tests.** The suite (now also: fresh points before roll-up, the
allowance across two connections, the audit) and a new interface test
(`test/test_timeseries_api.py`: Flask against a real PostgreSQL 16, 49
checks) — both green. Counter-checks: without the raw tail (below) four
checks turn red; with `CREATE SCHEMA IF NOT EXISTS` put back, the
interface test turns red with the error oaap-test showed.

**The real path on oaap-test** — `enable` for tenant `default`, then the
apps `projekt` (owns `Projekt`, only consumes `Firma`) and `raci`
(contributes to `Firma`) with their own twin keys through the gateway:

| | |
|---|---|
| create on an owned type / again / on a consumed type | 201 / 200, found / **403** with the binding named |
| 30 points / the same 30 again | 30 written / **30 duplicates, 0 written** |
| 5-minute range before any roll-up | 7 buckets, 30 points, min 0, max 13.5 |
| the same range after the minutely job | **identical**, 5 buckets now from tier `5m`, 2 still from raw |
| text: ok, ok, warning / 65 characters | 2 written, 1 extended, 2 states / 400 with the reason |
| delete without / with `confirm` | 409 / 200, in `audit` with the app's name |
| a contributor (not the owner) on `Firma` | 201 |
| the store | still closed; the role is in the platform group, may not create schemas |
| tenant archive (`zzz-probe`) | carries `tenant-timeseries-dump.sql`, all 40 tables |
| `oaap data store drop ts_…` | schema, role **and** credential gone |
| the unit | `Result=success` also while the job failed (before the fix below): one journal line per minute |

**What only the real path showed** (both tests had run as the superuser,
and the suite always ran the job before reading):

1. `CREATE SCHEMA IF NOT EXISTS` is refused to the tenant's role even when
   the schema exists — PostgreSQL checks the database privilege first.
   The driver now looks the schema up and creates it only when missing.
2. A 5-minute chart missed its last ten to fifteen minutes, and a new
   series all of it: a tier holds a bucket only two intervals after it
   closed. `range` now answers the part after a tier's mark from the raw
   points and merges the bucket that straddles it — the answer is the
   same before and after the roll-up.
3. A store error came back as a bare 500; now 503 with a reason.
4. `oaap data store drop` left the credential behind, so the job tried a
   role that no longer existed every minute — for `twin_` schemas too.

**Stage 1 is complete.** Next: stage 2, the fleet service writes
(RFC-0085 stage 5).

## 11. Out of scope

External query protocols and a Grafana data source; alerting on series
values (thresholds — a later step of RFC-0080 or of the fleet service);
forecasting; free text and log lines; changing RFC-0051's local store.

## Decision record (2026-11-12)

Jörg, in chat: D2–D8 "OK" — as recommended. **D1 amended:** "we also need
a history for texts like status; we can limit the permitted length."
Taken into the RFC as the kind `text` (§2.1): at most 64 characters, no
line breaks, kept as state intervals with gaps after three expected
intervals (§4.4), stored in `text_states` with the bound as column type
(§5), part of the conformance suite (§6). The limit of 64 is Claude's
proposal within Jörg's decision; changing it is a spec change.

## Deutsche Zusammenfassung

**Worum es geht.** Der Zwilling weiß, *was ist*: Objekte, Attribute,
Beziehungen, und je Datengruppe einen Schnappschuss bei jeder Änderung. Er
hat keinen Platz dafür, *wie sich ein Wert bewegt hat*, etwa CPU eines
Knotens jede Minute über ein Jahr. Bisher hält jeder Knoten nur seine
eigenen Messwerte für vier Stunden bis einen Monat in Dateien (RFC-0051).

**Der Vorschlag:** eine eigene Capability **`oaap.data.timeseries`** für
Werte über die Zeit — **Zahlen** und **kurze Texte** (Status).
- **Jede Zeitreihe hängt an einem Zwillingsobjekt** (z. B. Knoten oaapx01,
  Messgröße `cpu`). Ohne Objekt keine Reihe. Damit bleibt die
  Mandantengrenze, wo sie ist, und die Grafik aus RFC-0085 findet die
  Reihen eines Knotens am Knoten.
- **Zahlen und kurze Texte (Jörgs Ergänzung zu D1).** Texte wie
  `healthy`, `in Wartung`, höchstens **64 Zeichen**, ohne Zeilenumbruch —
  längere werden abgelehnt, nie abgeschnitten. Gespeichert werden nur
  **Wechsel**: Ein gleicher Wert verlängert „zuletzt gesehen“, ein neuer
  Wert beginnt einen neuen Abschnitt. Mit erwartetem Takt wird eine Lücke
  sichtbar („unbekannt“), wenn dreimal so lange nichts kam. Abfrage liefert
  Zustandsabschnitte bzw. je Zeitabschnitt den Wert am Ende, die Zahl der
  Wechsel und den am längsten gehaltenen Wert. Freitext und
  Protokollzeilen bleiben Ereignisse — die Längengrenze trennt beides.
- **Stufen, die mit dem Alter gröber werden**, immer mit Mittel, Minimum,
  Maximum und Anzahl, damit eine kurze Spitze im Jahresdiagramm nicht
  verschwindet. Drei feste Profile: `standard` (Minutenwerte 7 Tage,
  5-Minuten 31 Tage, Stunden 400 Tage, Tage 10 Jahre), `short`, `long`.
  Neue Profile nur über die Spezifikation, nicht als freie Einstellung.
- **Schnittstelle im Dienst des Zwillings**, mit dessen Schlüsseln:
  anlegen, Punkte schreiben, Bereich mit Schrittweite lesen, letzten Wert
  lesen. Doppelte Punkte (z. B. MQTT-Wiederholung) werden gezählt, nicht
  verdoppelt.

**Standardlösung:** reines PostgreSQL im vorhandenen Store, ohne
Erweiterung, also nur PostgreSQL-Lizenz. Ein eigenes Schema je Mandant
(`ts_<mandant>`), Tabellen nach Tag bzw. Monat aufgeteilt
(„Partitionierung“). Alte Daten löschen heißt dann einfach eine
Teiltabelle wegwerfen: schnell, ohne Datenbankmüll. Für die Flotte heute
etwa 72 000 Punkte am Tag, geschätzt einige zehn Megabyte; gemessen wird
das in Stufe 1.

**Abstraktion:** Ein Treiber je Knoten hinter einer festen Schnittstelle;
**ein gemeinsamer Prüfkatalog** läuft gegen jeden Treiber. Wer ihn nicht
besteht, wird nicht angeboten. Benannt, aber nicht gebaut: VictoriaMetrics
(Apache-2.0), InfluxDB 3 Core (MIT/Apache-2.0), TimescaleDB nur in der
Apache-Ausgabe.

**Sicherung:** Zeitreihen sind Teil der Mandantensicherung wie der
Zwilling; eine Generalprobe kopiert sie nur auf Wunsch.

**Acht Entscheidungen (§9), am 12.11. von Jörg angenommen:** D2–D8 wie
empfohlen, D1 erweitert um Text-Zeitreihen mit begrenzter Länge. **Stufen:** (1) Spec,
PostgreSQL-Treiber, Schnittstelle, auf oaap-test mit simulierter Uhr
gemessen (ein Jahr in Minuten); (2) die Flotte schreibt (RFC-0085 Stufe 5);
(3) Diagramme im Flottenmanagement; (4) ein „Rekorder“ für Mandanten-Topics,
erster Nutzer die simulierte Maschine aus RFC-0032; (5) später auf Wunsch
ein zweiter Treiber als Beweis für die Abstraktion.

**Stand 12.11. abends: Stufe 1 fertig (Referenz 0.1.270, §10.2).** Der
Zwillingsdienst hat die Schnittstelle, `oaap data timeseries enable`
richtet einen Mandanten ein, der Minutenjob verdichtet, die
Mandantensicherung nimmt die Reihen mit. Auf oaap-test mit echten
App-Schlüsseln über den Gateway gemessen: Rechte nach Bindung, Duplikate
gezählt, Diagramm vor und nach dem Verdichten gleich, Löschen nur mit
Bestätigung und protokolliert. Vier Fehler fand erst der echte Weg (die
Tests liefen als Datenbank-Verwalter): das Anlegen der Tabellen mit der
Mandantenrolle, die fehlenden letzten Minuten im 5-Minuten-Diagramm, ein
nacktes 500, ein liegengebliebenes Kennwort nach `drop`. Alle behoben und
durch Tests abgesichert.
