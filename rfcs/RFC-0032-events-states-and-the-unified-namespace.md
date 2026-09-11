# RFC-0032: Events, States, and the Unified Namespace

- **Status:** Accepted (2026-09-11) — four decisions, all following the
  recommendation. See the decision record at the end.
- **Date:** 2026-09-11
- **Authors:** Jörg (direction, four decisions), Claude (analysis &
  proposal)
- **Depends on:** RFC-0031 (the digital twin — this RFC's whole
  subject is "where the event RFC-0031 already emits goes"), RFC-0015
  (non-HTTP endpoints — the transport this RFC uses, unchanged),
  RFC-0027 (machine principals — how a broker client authenticates),
  RFC-0028 (terminals and presence — the first real-world event this
  RFC's transport carries), RFC-0011 (node profiles — the pattern this
  RFC's new `broker` profile follows), RFC-0021 (monitoring — how a
  stalled relay is reported)
- **Follows:** RFC-0031 Bauplan Schritt 6 (`program/studio/runbooks/
  rfc0031-zwilling-bauplan.md`), which left seven prepared questions
  for this RFC to answer.
- **Numbering note:** RFC-0033 and RFC-0034 were written before this
  one and skipped this number deliberately, both stating "RFC-0032
  stays reserved for events." This RFC fills it.

## Summary

RFC-0031 built the digital twin so that every write is recorded and
"produces an event" (§6, §10) — but left where that event *goes* to
this RFC, by design (§10: "Events and states — RFC-0032. This RFC only
says every write is recorded and emits one."). The recording exists
and is already live: every write to the twin appends one row to a
per-tenant `events` table (`oaap.data.twin` 0.2, oaap-reference
`platform/appctl.py`) that nothing has read since. This RFC decides
where those rows go, and answers the seven questions the RFC-0031
bauplan prepared for it.

| | Question | Decision |
| --- | --- | --- |
| **D1** | What shapes the topic tree — the twin's own vocabulary, or an external standard (RAMI 4.0 / i3x)? | **The twin's own vocabulary: `<tenant>/<type>/<object>/<group>`.** Checking i3x.dev against Jörg's own understanding (as the bauplan asked, before this RFC fixed the tree) found it is not a topic-hierarchy standard at all — see §1.1. Not i3x, not RAMI 4.0's site/area/line/asset. |
| **D2** | Does the broker need its own node profile (RFC-0011), or does it ride on `store`? | **Its own profile, `broker`.** A node can carry the twin (Postgres) without carrying real-time messaging (Mosquitto) — a pure back-office tenant has no reason to run a broker. |
| **D3** | Build the `states` (time-series) table now, or defer its shape until a real consumer needs it? | **Now, narrow.** One row per published change, group-grained (not per-attribute), append-only like every other twin table. |
| **D4** | How much of this gets built in this round? | **Nothing — decision only.** Mirrors RFC-0031's own rhythm: each bauplan step was its own session. The broker service, the outbox relay, the `states` table, and a simulated-machine reference app are the next step(s), not this one. |

Jörg decided all four on 2026-09-11, following every recommendation
(record at the end).

## Motivation

RFC-0031 deliberately built the cheapest possible preparation for this
RFC and stopped there: an `events` table that costs nothing to write
(one `INSERT` per twin write, already happening) and nothing to read
until something reads it (`program/studio/runbooks/
rfc0031-zwilling-bauplan.md:36-41`: "der Broker zuletzt, weil jeder
Schreibvorgang im Zwilling ein Ereignis erzeugt, aber niemand es heute
abholt — die Vorbereitung dafür … kostet nichts und macht RFC-0032 zu
einem Adapter statt zu einem Umbau"). This RFC is that adapter: it
decides the shape of the topic tree, how a client reaches it, what the
message on the wire looks like, and where a value's history lives —
without touching a single line of the twin service that already works.

## 1. The decisions

### 1.1 The topic tree comes from the twin, not from i3x (D1)

The bauplan named two candidate shapes for the topic tree: derive it
from the twin's own vocabulary (tenant/type/object/group), or adopt an
external hierarchy — RAMI 4.0's site/area/line/asset, or "i3x" — and
explicitly asked that i3x.dev be checked against Jörg's own
understanding before deciding (`rfc0031-zwilling-bauplan.md:298-300`,
`program/zielbild-datenplattform.md:387-390`).

That check happened as part of this RFC and the finding is recorded in
`program/capability-ideas.md` (2026-09-11 entry): **i3x (CESMII) is a
REST/HTTP query API over a manufacturing data platform — not a
topic-naming or MQTT standard.** It is broker-agnostic by design,
structures data as a graph of object types and instances rather than a
fixed site/area/line/asset string, and its own "historical values"
capability is an API operation, not a topic convention. It sits at the
same layer RFC-0031 §10 already deferred as "AAS repository API
conformity" — a possible future *query interface* onto
`oaap.data.twin`, unrelated to this RFC's topic tree. Jörg confirmed
this reading; the topic tree is therefore **not** modelled after i3x
or RAMI 4.0, and i3x is preserved as a separate, later idea rather than
folded into this decision.

The tree instead reuses vocabulary the twin already has, so nothing
about it needs translating twice:

```
oaap/<tenant-id>/<type-key>/<object-id>/<group-key>
```

`<tenant-id>`, `<type-key>`, `<object-id>` and `<group-key>` are
exactly the identifiers `oaap.data.twin` already assigns and exposes
(RFC-0031 §3–§4) — the same strings a reader already has from calling
the twin's own API. Putting the tenant first, not last, means an MQTT
ACL can scope a client to `oaap/<tenant-id>/#` with one rule, the same
boundary-at-the-edge principle RFC-0022 uses at the gateway.

### 1.2 The broker gets its own node profile (D2)

Mosquitto runs as a platform service, gated by a new RFC-0011 node
profile, **`broker`** — set independently of `store` (`sudo oaap node
add-profile broker`). The two capabilities answer different questions
(does this node hold twin data at all vs. does this node carry
real-time messaging) and a node can need one without the other: a
back-office tenant with no sensors or devices has a twin but no reason
to run a broker.

Transport is **already specified, not new work**: RFC-0015 Stage 1 (an
operator-granted, declared endpoint) covers exactly this — "enough for
a native MQTT broker" (`RFC-0015:257`) via **MQTT over WebSocket for
browser clients, through the gateway, with identity attached**
(`RFC-0015:423-428`), and the **raw TCP port for devices that cannot
speak HTTP** (`RFC-0015:41-42`, `274-276` — no identity on the raw
port, by design). A broker client authenticates with an RFC-0027
machine-principal key; a browser client rides the session the gateway
already verified, the same pattern every other WebSocket-through-
gateway use already follows.

### 1.3 The message on the wire stays thin (already built)

Not a fresh decision — RFC-0031 made this choice when it designed the
`events` table, and this RFC does not reopen it. Each row already
carries exactly `kind`, `object_id`, `group_key`, `origin` (no payload
fields, `oaap.data.twin.md:156-174`) — the bauplan's own "thin"
recommendation (`rfc0031-zwilling-bauplan.md:304-307`), already live.
The relay publishes that row, as JSON, **retained**, to the topic in
§1.1: a subscriber gets the *fact* that something changed and reaches
for the twin's own API if it wants the value. Retention means a
client arriving after the fact still sees the last message on each
topic without a separate "get current state" round-trip.

### 1.4 A narrow `states` table, now (D3)

A new, per-tenant-schema table, in the same append-only spirit as
`events`/`activities` (`oaap.data.twin.md:154-174`):

```sql
CREATE TABLE IF NOT EXISTS "{schema}".states (
    id bigserial PRIMARY KEY,
    object_id uuid NOT NULL,
    group_key text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL
)
```

Grain is the **group**, not the attribute — one row per published
change, `payload` holding that group's attribute snapshot at the
moment the relay read it. This is deliberately coarser than a
per-attribute time series: the relay already fetches the group's
attributes to build the retained MQTT message (§1.3), so writing the
same snapshot here costs nothing extra and needs no second read path.
A future reader wanting per-attribute history reads `payload` apart;
this RFC does not build that reader. Written **only** by the relay
(§1.5) — an app or device never writes `states` directly, the same way
it never writes `events` directly: both are projections of an ordinary
group write through the twin's existing API (RFC-0031 §4), never a
second way to produce data.

### 1.5 The relay, and what happens when the broker is unreachable

The relay is a reader of `events`, watermarked (it remembers the last
row id it published) and idempotent (re-publishing a row it already
sent is harmless — MQTT retained messages and the `states` table both
tolerate a duplicate write). When the broker is unreachable, the
answer the bauplan already gave stands: **the outbox grows, nothing is
lost, and the portal says so** (`rfc0031-zwilling-bauplan.md:310-312`)
— the same "report the symptom, never fail silently" pattern the
deploy-worker queue-depth alarm already uses (`oaap.core.portal` 0.3.8
Nachtrag). No cap, no dropped rows: a full disk is a node-capacity
problem to report, not a reason to lose history.

### 1.6 Presence (RFC-0028) is a separate publisher, not a twin event

Found while drafting this RFC, stated here so it is not assumed
otherwise later: RFC-0028's presence record — *"terminal T reports tag
X at time t"*, and the resulting `{device, operator, since, expires}`
state (`RFC-0028` §4.4) — lives in identity, not in the twin's
object/group model. It is **not** a twin write, carries no
`object_id`/`group_key`, and does not flow through the relay of §1.5.
When RFC-0028's own deferred MQTT adapter (§5: "MQTT, when it comes,
is a second adapter to the same event — not a second design") is
built, it publishes directly to the same broker this RFC establishes,
on its own topic (outside the `oaap/<tenant>/<type>/...` tree of
§1.1, since a terminal is not a twin object) — reusing the transport,
not the relay.

### 1.7 Nothing is built in this round (D4)

Matches RFC-0031's own build rhythm — Store, then Model, then Twin,
then the reference apps, then the browser, each its own session
(`RFC-0031` §11). This RFC decides; the broker service, the relay, the
`states` table, and a simulated-machine reference app (the bauplan's
seventh question) are a future step, opened when Jörg gives the
signal — not assumed here.

## 2. Non-goals

Explicitly **not** decided or built here, named so a later RFC does not
need to rediscover why:

- **Guaranteed delivery, edge nodes, twin sync to a plant node** —
  its own future RFC, tentatively `oaap.events.queue` (the name
  RFC-0031 §10 and `oaap.data.store.md:32` already used to mark the
  boundary), needs this RFC's transport first.
- **i3x as a query API onto `oaap.data.twin`** — a separate, later
  idea (`program/capability-ideas.md`, 2026-09-11 entry), unrelated to
  this RFC's topic tree; no RFC opened, no timeline.
- **OPC UA** — named in the Zielbild (`program/zielbild-
  datenplattform.md:208-211`) as "erst mit einer realen Maschine",
  i.e. not before a real device exists to justify it.
- **Per-attribute time series** — `states` (§1.4) is group-grained by
  design; a finer grain is a later, narrower table if a real reader
  ever needs one, not a redesign of this one.

## 3. Build order (for the next round)

1. `oaap.events.broker` capability spec (Purpose/Interface/
   Configuration/Security/Conformance, the RFC-0001 format every
   other capability spec already follows) — Mosquitto as the `broker`
   node profile, the topic tree of §1.1, the WebSocket/raw-port
   transports of §1.2 (already specified in RFC-0015, referenced not
   redesigned).
2. The relay (§1.5) and the `states` table (§1.4) in `oaap.data.twin`.
3. A simulated-machine reference app in `oaap-apps` (the bauplan's
   seventh question) — publishes fabricated telemetry as ordinary
   group writes on a Machine-type twin object, proving the whole path
   with no real device needed yet.
4. RFC-0028's deferred MQTT adapter for the presence event (§1.6),
   once the broker exists to adapt to.
5. A real device (ESP32-class, per the Zielbild) over the raw port.

## Deutsche Zusammenfassung

RFC-0031 hat vorbereitet, dass jeder Schreibvorgang im Zwilling ein
Ereignis erzeugt und in einer `events`-Tabelle landet — aber bewusst
offengelassen, wohin dieses Ereignis geht. Genau das entscheidet
RFC-0032, entlang der sieben Fragen, die der Bauplan zu Schritt 6
vorbereitet hatte.

Vier echte Entscheidungen, alle nach Empfehlung:

- **D1 — Themenbaum aus dem Zwilling, nicht aus i3x:** die vom Bauplan
  verlangte Prüfung von i3x.dev gegen Jörgs Verständnis ergab, dass
  i3x eine **Abfrage-API** ist, keine Themenbaum-Norm — weder i3x noch
  RAMI 4.0 prägen den Baum. Stattdessen `oaap/<mandant>/<typ>/<objekt>/<gruppe>`,
  dieselben Bezeichner, die der Zwilling schon vergibt.
- **D2 — eigenes Knotenprofil `broker`:** unabhängig von `store`, weil
  nicht jeder Zwillings-Knoten auch Echtzeit-Nachrichten braucht.
- **D3 — `states`-Tabelle jetzt, schmal:** eine Zeile je
  veröffentlichter Änderung, auf Gruppen-Ebene, nicht je Attribut.
- **D4 — nur entschieden, nicht gebaut:** wie bei RFC-0031 ist jeder
  Bauschritt seine eigene Runde.

Nebenbei geklärt, nicht neu entschieden: die dünne Nutzlast steht
schon (RFC-0031), die Übertragungswege stehen schon (RFC-0015), das
Anwesenheitsereignis aus RFC-0028 ist ein **eigener** Sender auf
demselben Broker, kein Zwillings-Ereignis.

## Decision record (2026-09-11)

Decided by Jörg in chat, the same session the RFC-0031 bauplan's
Schritt 6 was opened; every recommendation followed.

- **D1 — the twin's own vocabulary, not i3x/RAMI 4.0.** Jörg confirmed
  the i3x finding matches his own (corrected) understanding.
- **D2 — a new, independent node profile `broker`.** Confirmed as
  proposed.
- **D3 — the `states` table now, narrow (group-grained).** Confirmed
  as proposed.
- **D4 — decision only this round, build as its own next step.**
  Confirmed as proposed, matching RFC-0031's own rhythm.

### What follows

The build order of §3 is the next step, opened only on Jörg's signal —
not assumed here, the same discipline RFC-0031 itself used between its
own steps.
