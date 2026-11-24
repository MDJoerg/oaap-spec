# RFC-0127: Events as a Platform Capability — Apps Publish What They Declare, Subscribe to What They Are Granted, in the CloudEvents Envelope

- **Status:** **Accepted (2026-11-24)** — D1–D12 decided one by one the same
  day, each as recommended (§13).
  **Stage 0 measured** on `oaap-test` the same day: F3 (§1.5) and the
  relay's throughput (§1.6). **Stage 1, step 1 (D11) built** the same day,
  reference 0.1.360, measured on `oaap-test` (§1.7). **Step 1.2 (the bus:
  envelope, manifest block, door, store, grants, feed) built** the same day,
  reference 0.1.361, `oaap.events.bus` 0.1, measured (§1.8). **Step 1.3
  (addressed events, the case door's record) built**, reference 0.1.362,
  `oaap.events.bus` 0.2, measured (§1.9). The facts in §1 were read the same day in
  `oaap.events.broker` 0.4, RFC-0032, RFC-0120 §4.7/§13, `oaap.data.twin`,
  `oaap.core.notifications` 0.13, `oaap.apps.runtime` (§2.24/§2.25), reference
  0.1.359 (`services/twin/relay.py`, `twin/hooks.py`, `twin_inbound.py`,
  `mqtt_acl.py`), `oaap-apps/apps/vorgaenge`, and in the CloudEvents, xRegistry,
  AsyncAPI and SAP publications listed in §1.2. What was **not** read or
  measured is in §1.4; stage 0 (§12) answers it first.
- **Date:** 2026-11-24
- **Authors:** Jörg (the direction, 2026-11-24, as an addendum to RFC-0123 D15:
  "wenn wir jetzt das Konzept der Events immer mehr verwenden, sollten wir
  daraus eine Plattform-Fähigkeit ableiten. Dann sollten wir uns auch an
  Standards wie cloudevents.io orientieren. Damit koppelt SAP beispielsweise in
  der Cloud ihre SaaS-Lösungen … wenn wir Apps ihre Ereignisse publizieren und
  auch Ereignisse subscribieren können. Auch ein Integration Layer über Broker,
  Webhooks oder Messaging ist interessant"), Claude (facts, design)
- **Follows:** I-69 (`program/capability-ideas.md`), RFC-0123 D15 and its
  addendum (cases report back by event), RFC-0125 §11 (a twin event names the
  meaning of what changed), RFC-0126 §7 (identity reports invited people)
- **Depends on:** RFC-0032 (broker, relay, topic tree), RFC-0027 (machine
  keys), RFC-0120 (twin webhooks out and in, change feed), RFC-0125 (concepts:
  an event type and its fields carry meaning)
- **Related:** RFC-0080 (notifications to people — a different thing, §10),
  RFC-0085 (fleet tree, bridging), RFC-0086 (a later recorder of numbers),
  RFC-0061 (`vorgaenge` and its handover outbox), RFC-0033 (destinations — the
  way out to a partner's event broker)
- **Changes (when accepted):** a new capability `oaap.events.bus` (catalogue,
  publish, subscribe, delivery, feed); `oaap.events.broker` (the events branch,
  the ACL fix of §9); `oaap.apps.runtime` (manifest `events:`, key and URL like
  `cases`); `oaap.core.gateway` (`/platform/events/` per site);
  `oaap.data.twin` (twin events in the envelope, webhooks in the CloudEvents
  form); `vorgaenge` (the first publisher)
- **Not part of this RFC:**
  - **Queues and guaranteed delivery between nodes** (`oaap.events.queue`,
    store-and-forward) — named in five RFCs, still later; §11 keeps the door
    open.
  - **Kafka, AMQP, NATS bridges and a partner's broker** (SAP Event Mesh,
    Solace) — later, over a destination (RFC-0033).
  - **Notifications to people** (RFC-0080): mail to a person stays its own
    thing; a rule "event → notification" may come later (§10).
  - **AAS events** (`BasicEventElement`): experimental in the metamodel;
    mapped when `oaap.data.aas` exists.

## Summary

Events already run through the platform in four shapes that do not know each
other: the twin's **relay** to the MQTT broker (RFC-0032), the twin's
**webhooks out** with HMAC and the **change feed** (RFC-0120), the twin's
**webhooks in** with a mapping (RFC-0120 D13), and `vorgaenge`' own
**handover outbox** to partners. Three new needs have just been decided that
each want one more: cases reporting back to the app that opened them
(RFC-0123 D15), the twin naming the meaning of a change (RFC-0125 §11),
identity reporting an invited person's confirmation (RFC-0126 §7). And **no app
can publish or subscribe** at all: the manifest has no field for it, an app's
platform keys are scoped and the broker refuses scoped keys, and the only way
in is an unscoped tenant key an operator hands out by hand — which, as read
today, may also publish onto the twin's own topics.

This RFC makes events **one capability** with **one envelope**, after
**CloudEvents 1.0** — the CNCF format SAP uses to couple its cloud
applications (every event through SAP's Cloud Application Event Hub must be
CloudEvents-conformant):

1. **One envelope** (D1): CloudEvents 1.0 in its JSON form; `source` and `id`
   set by the platform, never by the publisher; three extensions of ours
   (tenant, origin, meaning).
2. **A catalogue per app in the manifest** (D2): what an app publishes (type,
   schema, meaning, audience) and what it wants to subscribe to; readable as
   **AsyncAPI 3.1** (D9).
3. **Publishing through a platform door** (D3): `POST /platform/events/` with a
   key like `cases`; the platform checks the type against the catalogue and
   stamps the envelope.
4. **Subscriptions granted, not taken** (D4): the tenant admin grants a declared
   subscription; a publisher may also **address** an event to one instance (a
   case to the app that opened it) (D5).
5. **Delivery pushed into the app, with a feed behind it** (D6): the platform
   POSTs the event to the instance in the CloudEvents HTTP binding,
   at-least-once, in order per subject; a pull feed for catching up.
6. **The integration layer out and in** (D7, D8): the twin's webhooks become
   the general way out (CloudEvents webhook form, HMAC kept); the twin's
   receivers the general way in; the broker stays the bus inside.
7. **The twin speaks the envelope too** (D10), and **the ACL hole is closed**
   (D11): only the platform publishes on the twin's topics.

## 1. Facts

### 1.1 Read 2026-11-24 (the platform)

| # | Fact | Where |
|---|---|---|
| F1 | Mosquitto per node (profile `broker`), WebSocket only through the gateway, TCP 1883 in the platform network; every CONNECT and topic action is checked live at identity. Topic tree `oaap/<tenant-id>/<type-key>/<object-id>/<group-key>`; QoS 1, retained; persistent sessions expire after 7 days. Tenant trees are **not** bridged between nodes (only the fleet tree is). | `oaap.events.broker` §2 (`:60-121`, `:202-248`); RFC-0085 §5.3 |
| F2 | A client authenticates with an RFC-0027 key; **only an unscoped key** is accepted, an `instance`-scoped one is refused; every topic must lie inside `oaap/<own tenant>/`. A key for a broker client is issued **by hand** by an operator ("Zugänge"). | `oaap.events.broker:142-158`, `:212-217`; `identity/app.py:3243-3266` |
| F3 | Inside `oaap/<tenant>/` a tenant key may read **and write** (`mqtt_acl.py` kind `tenant`) — so it can publish onto the twin's topics, where only the relay should write. **Measured 2026-11-24 (§1.5):** a twin-shaped event can be forged that way, retained included. | `services/mqtt_acl.py:8-33`; `oaap.events.broker:154-181` |
| F4 | The relay reads the twin's `events` table from a watermark every 2 s (200 rows), publishes MQTT v5 QoS 1 retained; payload `{id, kind, object_id: "urn:oaap:obj:<uuid>", group_key, origin, recorded_at}`, a status change adds `status: {from, to, reason}` on `…/<object>/status`. | `twin/relay.py:36-37`, `:66-67`, `:129-150`, `:204`, `:281-282` |
| F5 | Twin webhooks out (built, `oaap.data.twin` 0.13): body `{hook, events[≤50], next}`, `X-OAAP-Signature: t=…,v1=HMAC-SHA256(<t>.<body>)`, at-least-once in order, backoff to 1 h, stop after 10 failures, `resume`, ≤5 per client, internet targets only, no values. Change feed `GET /twin/v1/changes?since=` (cursor = event id). Value events: not built. | `oaap.data.twin:695-701`, `:854-882`; `twin/hooks.py:178-184` |
| F6 | Twin webhooks in (built, 0.14 §2.26): signature `oaap` · `hmac-sha256` · `token`; a JSON mapping with ≤20 rules `when` → `upsert`/`retire`/`status`; a delivery is one batch, idempotent by delivery id. | `oaap.data.twin:884-954`; `twin_inbound.py` |
| F7 | Notifications: a fixed platform catalogue, channel `mail` only, an outbox directory; **apps may not send** their own. | `oaap.core.notifications:37-50`, `:148-160`, `:288` |
| F8 | `vorgaenge` publishes no events; it has its own outbox for handovers to partners (`POST <partner>/handover`, Bearer, at-least-once, idempotent by `handover_id`). No app in `oaap-apps` uses MQTT. | `oaap-apps/apps/vorgaenge/app.py:123-164`, `store.py:306-310`; grep |
| F9 | The runtime manifest has **no field** for events, broker, publish or subscribe. The capability pattern is `cases: {submit: true}` → `OAAP_CASES_KEY` (principal `instance:<name>`, scoped `oaap.cases.submit:<name>`) and `OAAP_CASES_URL`, passed by the gateway only in that block of the instance's own site, never for a probe install. | `oaap.apps.runtime` §2.24/§2.25 (`:2010-2068`) |
| F10 | "Outbox" names three different things today: the twin's `events` table, the notification outbox, `vorgaenge`' handover outbox. `oaap.events.queue` is named in RFC-0032, -0033, -0120, `oaap.data.store`, the broker spec and the data-platform target picture, with no spec. | grep 2026-11-24 |

### 1.2 Read 2026-11-24 (the standards)

| # | Fact | Source |
|---|---|---|
| S1 | **CloudEvents v1.0.2** (released; `specversion` stays `"1.0"`). Required: `id`, `source`, `specversion`, `type`; optional: `datacontenttype`, `dataschema`, `subject`, `time`. Attribute and extension names: `a–z0–9`, should start with a letter, ≤20 characters recommended. `source` + `id` identify an event. | github.com/cloudevents/spec `cloudevents/spec.md` |
| S2 | Bindings released at v1.0.2: **HTTP** (binary: `ce-*` headers; structured: `application/cloudevents+json`; batched only when the receiver asks), **MQTT** (3.1.1 structured JSON only; 5.0 binary or structured), Kafka, AMQP, NATS. WebSockets: work in progress. Formats JSON, Avro, Protobuf released. | `bindings/*`, `formats/json-format.md` |
| S3 | **HTTP webhooks** for event delivery (v1.0.2): HTTPS POST; 429 throttles, 410 retires the target; abuse protection by an **OPTIONS handshake** (`WebHook-Request-Origin` → `WebHook-Allowed-Origin`, optional rate); authorization by Bearer token. | `cloudevents/http-webhook.md` |
| S4 | **Subscriptions API**: 0.1-wip, not released (subscription with `types`, `filters`, `sink`, `protocol`; filter dialects `exact · prefix · suffix · all · any · not`, optional `sql`). **CESQL** v1.0.0 released. **xRegistry** (event-type and schema registry, split out of CloudEvents in 2023): v1.0-rc4. | `subscriptions/spec.md`; github.com/xregistry/spec |
| S5 | **SAP**: every event through SAP Cloud Application Event Hub must be CloudEvents-conformant (`source` + `id` unique); S/4HANA example `type: sap.s4.beh.businesspartner.v1.BusinessPartner.Changed.v1`, `source: /default/sap.s4.beh/<id>`, `data: {"BusinessPartner": "1000667"}` (thin); extension `sappassport` for tracing; event catalogue on the SAP Business Accelerator Hub, some in AsyncAPI; CAP: messaging `format: cloudevents`. | developers.sap.com tutorials `eh-basic-concepts`, `codejam-events-process-1-bah`; cap.cloud.sap/docs/guides/events/s4 |
| S6 | **AsyncAPI 3.1.0** describes an application's channels and messages (schemas in JSON Schema, Avro, Protobuf …); CloudEvents is the envelope inside; both together is common practice, not a norm. | asyncapi.com/docs/reference/specification/latest |

### 1.3 What follows

- **The pieces exist; the shape does not.** Relay, webhooks out with HMAC,
  receivers in, feed — all built, all twin-only, each with its own payload. One
  envelope and one catalogue turn them into one capability without new
  transport.
- **CloudEvents fits what we have**: thin events (SAP's are thin too, S5),
  `subject` = our object URN, MQTT binding for the broker, HTTP binding for
  webhooks. The parts that are not released (subscriptions, xRegistry) we do
  not adopt as wire formats; we keep our own catalogue and subscriptions in
  their spirit and export to AsyncAPI.
- **An app must never hold a broker key** that reaches the twin's topics (F2,
  F3). Publishing goes through a door, as `cases` does (F9).
- **F3 is a hole today** (measured, §1.5), independent of this RFC. D11 closes
  it in stage 1.

### 1.4 Not read, not measured

- ~~Whether an instance network reaches the broker at all~~ — read 2026-11-24,
  §1.5 (M6).
- ~~F3 measured~~ — measured 2026-11-24, §1.5.
- ~~The relay's throughput beyond 200 rows per 2 s, and what a second event
  source does to it~~ — measured 2026-11-24, §1.6.
- SAP's AsyncAPI version and `x-sap-*` fields on the Accelerator Hub
  (help.sap.com not reachable for the reader); the AsyncAPI text itself.

### 1.5 Measured 2026-11-24 on `oaap-test` (stage 0, part one)

Reference 0.1.359. A throwaway machine principal `ev-probe` (role `user`) in the
test tenant `t9k2`, an **unscoped** RFC-0027 key for it (`oaap key issue
ev-probe --days 1`), an MQTT v5 client (paho 2.1) inside the relay container,
which sits in the broker's network, against `broker:1883`. A made-up type
`evprobe` and a made-up object id, so that no real twin object was touched.
Afterwards the retained message was cleared (empty payload, retain), the key
revoked, the principal removed.

| # | What | Result |
|---|---|---|
| M1 | Subscribe `oaap/<t9k2>/#` | granted |
| M2 | Publish, QoS 1, **retained**, onto `oaap/<t9k2>/evprobe/<uuid>/state` with exactly the relay's payload (`kind: status.changed`, `origin: twin`, an `object_id` URN) | **`Success`** — the broker took it |
| M3 | A second connection subscribes **afterwards** to that topic | it receives the forged message as **retained**, indistinguishable from one the relay wrote |
| M4 | Publish into another tenant's tree, onto the metrics branch `oaap-node/…`, onto the bridged branch `oaap-via/…`; subscribe to another tenant's tree | all four `Not authorized` |
| M5 | Clear the retained message, subscribe again | nothing retained — cleanup confirmed |
| M6 | Who sits in the broker's network `oaap_default` | only platform containers (gateway, identity, portal, twin, relay, hooks, connect, store); **no app container**. Apps reach the broker only through the gateway's `/broker/*` (WebSocket, logged-in session **and** a key inside the MQTT CONNECT) or, on a node with the raw port exposed, from outside. |

**What follows.** F3 is real, for the lowest role (`user`): the tenant
boundary holds (M4), but inside its own tenant a key holder can write onto
the twin's topics and leave a **retained** forgery there that every later
subscriber receives as the current state (M3). The relay overwrites it only
when that object's next real event arrives. The payload carries no mark of who
wrote it — which is exactly what the CloudEvents envelope with a
platform-set `source` (D2) and D11 change. Today no app holds such a key and
no app speaks MQTT (F8, M6); the hole is open to whoever an operator issues an
unscoped key to by hand. Not measured: overwriting the retained topic of a
**real** twin object (the ACL does not look at the type, so it is expected to
behave the same), and whether `/broker/*` accepts a key as `Authorization`
instead of a session.

### 1.6 Measured 2026-11-24 on `oaap-test`: the relay's throughput (stage 0, part two)

Reference 0.1.359 on `oaap-test` (a VM on a PC, not a Raspberry Pi). Two
throwaway integration clients (RFC-0120, `--models`, a key for one day) in the
throwaway tenants `s0` and `zzz-probe`, each registering a type `EvLoad` and
then writing 3,000 objects through the door `/twin/v1/batch`, 500 per batch.
Each object makes two events (`object.created`, `group.written`), both naming
a group, so the relay writes a `states` row for each, stamped with the moment
it handled the row. Producer times are `events.recorded_at`, relay times
`states.recorded_at`. RFC-0123's load S5 in `s0` (§1.4 there, the same
morning) was read afterwards from the same two columns.

| Run | Sources | Events | Producer | Relay done after | Relay rate | Lag p50 / p90 / max |
|---|---|---|---|---|---|---|
| R1 (RFC-0123 S5) | 1 | 22,222 | 117 s (190/s) | 386 s | 57.6/s | 160 / 274 / 290 s |
| R2 | 1 | 6,000 | 14 s (429/s) | 93 s | 64.4/s | 44 / 73 / 83 s |
| R3 (R2 again) | 1 | 6,000 | 18 s (327/s) | 95 s | 63.3/s | 41 / 72 / 81 s |
| R4 | **2 at once** | 2 × 6,000 | 26 s and 20 s | 146 s, both | **41.2/s each**, 82.4/s together | 71 / 114 / 126 s and 71 / 118 / 131 s |

**What follows.**

- **The relay is the narrow part, not the twin.** The door writes 190–430
  events a second; the relay publishes about 60 a second for one tenant. A burst
  (an import, a big batch) arrives at subscribers minutes late — 290 s for the
  last of R1's events.
- **The shape comes from the loop** (`relay.py`): per tenant at most 200 rows
  per pass, one publish per row whose PUBACK it waits for, one commit per row,
  and a fixed 2 s sleep after every pass over all tenants. One busy tenant:
  about 3.1 s per 200 rows, i.e. about 1.1 s of work (≈5.5 ms a row) plus the
  2 s sleep. Two busy tenants: one pass takes about 4.85 s (2 × ≈1.4 s + 2 s),
  and each tenant still gets only 200 rows per pass.
- **A second source slows every other one** — here by a third (64 → 41 a
  second each), while the sum grows by only a quarter (64 → 82). The tenants
  share one loop; a busy tenant lengthens everybody's pass.
- **Ceilings at this cost:** one tenant stays below 100 a second even with no
  work at all (200 rows per 2 s); all tenants together reach about 140–180 a
  second (1 / 5.5–7 ms per row) once there are enough busy ones for the sleep
  not to matter.
- **For this RFC.** App events do not go through the relay (the door, §6), so
  they do not take from it. But D10 makes the relay write every twin event a
  second time, into the store — a second write per row, which lowers these
  numbers further. Stage 1 therefore does **not** hang the delivery of app
  events on this loop, and it gives the relay what `relay.py` itself names as
  the later step ("revisited only if it becomes a cost"): no sleep while a
  backlog remains, or LISTEN/NOTIFY, and publishing a batch without waiting for
  each PUBACK before the next. At today's load (a few events a minute across
  the fleet) none of this is a cost; under a burst it is.

Not measured: how long a **quiet** tenant's single event waits while others
have a backlog (by the loop at most one pass, about 5 s in R4); more than two
sources; a Raspberry Pi. The runs leave about 12,000 retained topics on the
broker (one per object) in the two probe tenants; they go with the tenants. The
clients were removed afterwards (keys revoked, principals deactivated); the
relay logged no error.

### 1.7 Built and measured 2026-11-24: D11 (stage 1, step 1)

Reference 0.1.360 (`mqtt_acl.decide`): a tenant key inside its own tree
`oaap/<tenant>/` reads and subscribes; a publish is refused with "only the
platform publishes in a tenant's tree (RFC-0127 D11)". `oaap.events.broker`
0.5 says so (§2.4, §4, test 4). Before the change it was read who else writes
there: the relay and the node's care event use the platform principal
`oaap.relay` (identity's own check, untouched), node keys write outside
`oaap/`, and no app speaks MQTT (F8) — so no legitimate writer loses anything.
Staged on `oaap-test`; §1.5's probe repeated with a throwaway principal
(`user`, tenant `t9k2`, unscoped key for one day), then key revoked and
principal deleted.

| # | What | 0.1.359 (§1.5) | 0.1.360 |
|---|---|---|---|
| M2 | Publish, QoS 1, retained, twin-shaped, own tenant | `Success` | **`Not authorized`** |
| M3 | A later subscriber to that topic | receives the forgery as retained | **receives nothing** |
| M4 | Other tenant, `oaap-node/…`, `oaap-via/…`; subscribe another tenant | `Not authorized` | `Not authorized` |
| M1 | Subscribe own tree | granted | granted |
| M7 | Reading still works: a key of `s0` subscribes `oaap/<s0>/#` | — | `Granted`; 1,040 retained twin states received (`origin` set by the relay), the rest dropped by the broker's queue limit |

The relay logged no refusal after the change. Unit tests: `test_mqtt_acl`,
`test_broker_profile`, `test_event_relay` changed to the new rule, with
`test_fleet_watch` and `test_fleet_pair` all green.

**Found on the way (not D11's doing, but this RFC's business).** M7's
SUBACK came only after **38.7 s**. The broker asks identity once per
retained message before it delivers it (go-auth, a read check per topic, no
cache hit for 12,000 different topics): about 370 checks a second, logged as
up to 11,600 checks a minute; after the key was revoked mid-delivery each
check answered "unknown key". So a subscriber to a tenant tree with many
retained topics waits half a minute or more and receives only up to the
queue limit. That is the twin's retained state topics at scale (RFC-0123's
pilot will have tens of thousands of nodes), not app events — §9's events
branch is **not retained** and is therefore not affected. Not measured:
whether other clients of the broker wait meanwhile (Mosquitto is single
threaded, so it is expected). Belongs to the twin's topics, a later step
(an ACL cache keyed by tenant prefix, or no per-message read check for a
subscription already granted on the whole tree); recorded here, not
decided.

### 1.8 Built and measured 2026-11-24: the bus, step 1.2

Reference 0.1.361, `oaap.events.bus` 0.1, runtime 0.2.83 (manifest 0.21).
Staged on `oaap-test`; the schema step brought the five twin schemas there
up to `bus_events` and `bus_grants` on its own. A throwaway probe app
(`evprobe`, one package, publishing and wanting `app.evprobe.probe.ping.v1`)
installed twice in the throwaway tenant `s0` (`s0-evp-a`, `s0-evp-b`) and
once in `zzz-probe` (`zzz-probe-evp-c`); all three removed afterwards (keys
revoked, principals deleted, the catalogue empty again).

| # | What | Result |
|---|---|---|
| B1 | Install | key and URL in the environment, both instances in the catalogue |
| B2 | Publish with forged `source`, `id`, `time`, `oaaptenant`, `oaaporigin` | `202`; stored and delivered with the platform's values (`source` `urn:oaap:tenant:<s0>:instance:s0-evp-a`, a ULID, the door's time, `oaapsemantic` from the catalogue) |
| B3 | Undeclared type · `n: -1` · an extra field · 70 KB · `oaapto` | `403` · `422 data.n: at least 0` · `422 data.x: not allowed here` · `413` · `400` |
| B4 | Binary mode (`ce-type`, `ce-subject`, body = data) | `202` |
| B5 | `s0-evp-b`'s feed before the grant · after `oaap events grant` · `?since=` · after `revoke` | empty · both events · exactly the later ones · empty, although a new one was published |
| B6 | The publisher's own feed | empty: it does not get its own events back |
| B7 | 125 publishes within a minute | 115 × `202` + 10 × `429` (120 a minute, counting the five before) |
| B8 | `s0-evp-b`'s key at `s0-evp-a`'s door · no key · a forged `X-OAAP-User` · a made-up key | `403` from identity ("limited to … s0-evp-b") · `303` to the login · `303` (the header is stripped) · `401` — none reaches the twin service |
| B9 | The instance in `zzz-probe`, granted the same type | its feed stays empty while `s0` holds 125 events: no event crosses tenants |
| B10 | Audit | `events.grant` and `events.revoke` in the tenant audit log with who, instance and type |

Found and fixed during the measurement: `oaap events list --tenant <label>`
did not resolve a label (fixed before the commit). Not measured: a person's
session at the door (the `303` without a key is the same path), retention
(the 30-day deletion runs with 1 % of publishes), a tenant without a twin
through the real path (unit-tested: `409`).

### 1.9 Built and measured 2026-11-24: addressed events, step 1.3

Jörg, 2026-11-24: the platform's record comes from the case door (option A
of three: the door records the pair; not "the subscriber declares it", not a
record per case). Reference 0.1.362, `oaap.events.bus` 0.2, runtime 0.2.84.
Staged on `oaap-test`. The probe (`evprobe` 0.2.0: an addressed type, a
subscription to it with `addressed_only`, `cases: {submit: true}`) installed
three times in the tenant `default`, which has a `vorgaenge` inbox and a
twin, and once in `s0`; all four removed afterwards.

| # | What | Result |
|---|---|---|
| A1 | `evp-a` addresses `evp-b`, no record | `403` "'evp-b' gave 'evp-a' nothing to address" |
| A2 | `evp-b` opens a case through its case door | `201` from `vorgaenge` (V-2026-0026); the record holds (`vorgaenge`, `evp-b`, `cases`, 1); a second case counts 2 |
| A3 | `oaapto` on a type that is not addressed · an addressed type without `oaapto` · an instance of `s0` · an instance that does not declare the type (`vorgaenge`) | `400` · `400` · `403` "no instance of this tenant" · `403` "does not declare" |
| A4 | A record (`evp-a`, `evp-b`) **written by hand** — `vorgaenge` publishes nothing before step 1.5 — then `evp-a` addresses `evp-b` | `202`; in `evp-b`'s feed **without a grant**, with `oaapto: instance:evp-b`; `evp-c`'s and `evp-a`'s feeds empty |
| A5 | A grant on the addressed type for `evp-c` · a grant on the other type | refused ("reaches only the instance it names") · granted, and `evp-c` still sees nothing addressed to `evp-b` |
| A6 | `/platform/events/relate…` and `/platform/events/x` from an app | `404`, `404` — the record cannot be written through the events door |

No error in the twin service's log. The hand-written record and the probes'
rows were deleted; the two probe cases stay in `default`'s inbox (V-2026-0026,
-0027). Not measured: the record when the twin service is down (the case
door's second `forward_auth` then fails, and with it the case — a coupling
this option brings; the twin service is a core service of the same node).

## 2. Words

| Word | Meaning |
|---|---|
| **event** | something that happened, told once, in the envelope (§3); never a command |
| **event type** | a catalogue entry: name, schema of `data`, meaning, audience (§4) |
| **publisher** | an app instance, the twin, identity, or an external system through a receiver |
| **subscription** | a granted right of one instance (or one integration client) to receive one event type, with an optional filter (§6) |
| **addressed event** | an event the publisher sends to one named instance only (§6.2) |
| **delivery** | getting one event to one subscriber: push into the app, webhook out, or feed (§7) |

## 3. The envelope (D1)

CloudEvents 1.0, JSON form (`application/cloudevents+json`), on every path:

| Attribute | Set by | Value |
|---|---|---|
| `specversion` | platform | `"1.0"` |
| `id` | platform | the event's id in the tenant's event store (a ULID, sortable) |
| `source` | **platform** | `urn:oaap:tenant:<tenant-id>:<publisher>` — `instance:<name>`, `twin`, `identity`, `receiver:<client>/<hook>`; the publisher cannot choose it |
| `type` | publisher, checked | `<namespace>.<entity>.<what>.v<major>` — `oaap.twin.object.changed.v1`, `app.vorgaenge.case.statuschanged.v1`, `oaap.identity.person.activated.v1` |
| `subject` | publisher | what it is about: `urn:oaap:obj:<uuid>` for a twin object, else the publisher's own key |
| `time` | platform | when the platform accepted it |
| `datacontenttype` | platform | `application/json` |
| `dataschema` | platform | the URL of the type's schema in the catalogue |
| `data` | publisher | checked against the schema; **thin by default** (keys, from/to), full only when the type says so (§8) |
| `oaaptenant` | platform | the tenant id (also inside `source`, here for filters) |
| `oaaporigin` | platform | the origin as the twin names it (`app:<id>`, `model:<id>`, `tenant`) |
| `oaapsemantic` | publisher via catalogue | the semantic ID of the type (RFC-0125: a platform concept or a standard) |
| `oaapto` | publisher | only for an addressed event: `instance:<name>` (§6.2) |

On MQTT the structured JSON form is used (works for 3.1.1 and 5.0, S2); on
HTTP the structured form, the binary form accepted on input.

## 4. The catalogue (D2, D9)

An app declares in its manifest what it publishes and what it wants:

```yaml
events:
  publishes:
    - type: app.vorgaenge.case.statuschanged.v1
      title: "Vorgang hat den Status gewechselt"
      subject: case                     # what `subject` holds
      schema: events/case-statuschanged.json   # JSON Schema, in the package
      semantic_id: oaap-aas:Cases/1/0/StatusChanged
      audience: addressed               # addressed · tenant · listed
      personal: false
  subscribes:
    - type: oaap.identity.person.activated.v1
      why: "Ansprechpartner freischalten"
    - type: app.vorgaenge.case.statuschanged.v1
      addressed_only: true              # only events addressed to me
```

- **Types are versioned in the name** (`.v1`); a breaking schema change is a new
  type, the old one kept until no subscriber is left — the additive rule of
  `oaap.data.model` §2.5 applied to events.
- **Audience**: `addressed` — delivered only to the instance named in `oaapto`;
  `tenant` — any instance of the tenant may be granted it; `listed` — only the
  apps the publisher names.
- **Platform types** (twin, identity, later others) are in the platform's own
  catalogue, same form.
- The tenant's catalogue — every installed app's types plus the platform's — is
  readable through the portal ("Ereignisse"), the API and MCP, and **exported as
  AsyncAPI 3.1** per app and per tenant, the way SAP's Accelerator Hub does it
  (S5, S6). An xRegistry export waits for its release (S4).

## 5. Publishing (D3)

The instance gets `OAAP_EVENTS_KEY` (principal `instance:<name>`, scoped
`oaap.events:<name>`) and `OAAP_EVENTS_URL`, like `cases` (F9). It publishes:

```
POST /platform/events/          (structured CloudEvents, or binary with ce-* headers)
{ "type": "app.vorgaenge.case.statuschanged.v1", "subject": "V-2026-0042",
  "oaapto": "instance:bestand-cds",
  "data": {"case": "V-2026-0042", "from": "open", "to": "in_progress",
           "object": {"kind": "bundle", "id": "B-17"}} }
→ 202 {"id": "01J…"}
```

The platform: checks the type is in this app's `publishes`; checks `data`
against the schema; for `addressed`, checks `oaapto` names an instance of the
same tenant; **sets `source`, `id`, `time`, `oaaptenant`, `oaaporigin`,
`oaapsemantic`, `dataschema`** (whatever the app sent there is replaced); writes
the event into the tenant's **event store** (one table, like the twin's
`events`, §7); answers `202`. Limits per instance (events per minute, size of
`data` ≤ 64 KB) answer `429` / `413`.

No app publishes on the broker directly (D3, F2/F3).

## 6. Subscribing (D4, D5)

### 6.1 Granted, not taken

A subscription the manifest declares **does not deliver yet**. The tenant admin
sees on the portal page "Ereignisse" which app wants which type and why, and
grants or refuses — once per instance and type, recorded in the audit log.
Two cases need no grant: an **addressed** event to the instance it names (the
publisher chose the receiver; the subscriber declared `addressed_only`), and a
platform event about something the instance itself caused (identity telling
`bestand` about a person `bestand` invited, RFC-0126). Filters: by `subject`
prefix and by `data` fields with `exact · prefix` (the released core of S4's
dialects); CESQL later.

### 6.2 Addressed events

RFC-0123 D15 is the case: `vorgaenge` must tell **the app that opened a case**
that it moved — not every app of the tenant. An addressed event carries
`oaapto: instance:<name>` and is delivered **only** there; nobody else can be
granted it, and it never goes onto a broadcast topic. The publisher may address
only an instance that gave it something to address (for `vorgaenge`: the
instance that submitted the case through `/platform/cases/submit`); the platform
checks that from its own records, so an app cannot spray events at strangers.

## 7. Delivery (D6)

- **One event store per tenant** (a table next to the twin's, `bus_events`),
  append-only, with the delivery state per subscription. Retention per tenant
  (default 30 days); the twin's own `events` table stays as it is and feeds the
  store through the relay (D10).
- **Push into the app**: the platform POSTs each event to the path the instance
  declares (`events.endpoint: /oaap/events`, inside its own network, never
  through the internet), in the CloudEvents HTTP structured binding, signed like
  the twin's webhooks (`X-OAAP-Signature`, HMAC with a secret the platform gives
  the instance at install). At-least-once, **in order per `subject`**, backoff
  to 1 h, stop after 10 failures (shown on the portal page), `resume`. The app
  is idempotent by `id`.
- **Feed behind it**: `GET /platform/events/feed?since=<id>` with the same key
  returns the instance's granted and addressed events in order — for catching
  up after a stop, and for an app that prefers to pull.
- **MQTT for apps**: not in the first stages. If an app ever needs it, it gets a
  read-only scoped broker identity limited to the topics of its grants — after
  §1.4's check that instance networks reach the broker.

## 8. Personal data and size

- **Thin by default** (S5, RFC-0120 D10): keys, from/to, the subject — the
  subscriber reads details where it may. A type may declare `full: true`; then
  the tenant admin sees "carries data" when granting.
- A type with `personal: true` is never delivered out of the tenant (§9 webhooks)
  unless the tenant admin allows that type for that target.
- Erasure (RFC-0090): the event store is not a second master; an erased object's
  events keep their ids and lose `data` after the retention or on erasure.

## 9. The integration layer: out, in, and the bus inside (D7, D8, D11)

- **Out — webhooks** (D7). The twin's webhooks for integration clients (F5)
  become the general way out: a client may register a URL for **any granted
  event type** of its tenant, not only twin types. The body becomes CloudEvents
  (batched `application/cloudevents-batch+json`, ≤50 per POST); the HMAC
  signature stays (it is stronger than S3's Bearer and already built), and the
  target is checked once by S3's **OPTIONS handshake** before the first POST.
  The old body stays for existing hooks until they are moved (a field
  `format: oaap-v1 · cloudevents`).
- **In — receivers** (D8). The twin's receivers (F6) accept, besides their
  mapping to twin writes, a **CloudEvents mapping**: an external system's call
  becomes an event of a type the tenant declares for that receiver
  (`ext.<client>.<entity>.<what>.v1`), then delivered like any other. A sender
  that already speaks CloudEvents (SAP, S5) is accepted as is; its `source` is
  kept as `oaapextsource`, ours is the receiver.
- **The bus inside — the broker** (D11). The broker stays the internal bus and
  gets a branch `oaap/<tenant>/events/<type>` where the platform publishes every
  non-addressed event of the store (structured JSON, QoS 1, not retained).
  **Only platform principals publish anywhere under `oaap/<tenant>/`**: a tenant
  key becomes read-only there (closes F3). Fleet and care topics keep their own
  rules.
- **Messaging beyond the broker** — queues, Kafka/AMQP bridges, a partner's
  event mesh — is a later RFC (`oaap.events.queue`), on this envelope and this
  store; nothing here needs to change for it.

## 10. What stays separate

- **Notifications** (RFC-0080) go to **people** by mail from a fixed catalogue.
  Events go to **programs**. A later rule "this event → this notification" may
  join them; apps still do not send mail (F7).
- **`vorgaenge`' handover outbox** (F8) is a contract with a partner system
  (a command with an answer, not an event); it stays. A case's status change
  is the event (§6.2).
- **The twin's `events` table** stays the twin's journal; the relay copies from
  it into the store (D10).

## 11. The twin and the first pairs (D10, D12)

- **D10 — the twin in the envelope.** The relay writes each twin event into the
  store as `oaap.twin.object.created|changed|retired.v1` and
  `oaap.twin.object.statuschanged.v1`, `subject` = the object URN, `data` =
  `{type, group, instance, origin}` (RFC-0125 D4's instance key) and
  `oaapsemantic` = the group type's semantic ID (RFC-0125 §11). The **current
  MQTT payload on the existing twin topics stays** for its readers (the fleet
  views); new readers use the events branch.
- **D12 — the first pairs**, in this order: (1) `vorgaenge` →
  `bestand`, addressed status events (RFC-0123 stage 2); (2) identity →
  the inviting app, `oaap.identity.person.activated|locked.v1` (RFC-0126
  stage 2); (3) twin events in the envelope with webhooks in CloudEvents form.

## 12. Stages

| Stage | What | Measured by |
|---|---|---|
| **0** | Measure on `oaap-test`: F3 (a tenant key publishing on a twin topic) — **done 2026-11-24, §1.5**; the relay's throughput with a second source — **measured 2026-11-24, §1.6**; whether an instance network reaches the broker — **read 2026-11-24, §1.5 M6**. | §1.4 answered |
| **1** | **The ACL fix** (only platform principals publish under `oaap/<tenant>/`) — **built 2026-11-24, 0.1.360, §1.7**. Envelope, store, catalogue in the manifest, publish door, grants, addressed events, push into the app, feed. First pair `vorgaenge` → `bestand`. | security requirements; a case moved in `vorgaenge` arrives once in `bestand`, after a stop of `bestand` through the feed |
| **2** | Platform types (identity, twin in the envelope, D10); the portal page "Ereignisse" with the tenant's catalogue and grants; AsyncAPI export. | RFC-0126's activation arrives in the inviting app; AsyncAPI opens in an AsyncAPI viewer |
| **3** | Webhooks out for any granted type in CloudEvents form with the OPTIONS handshake (D7); receivers in with a CloudEvents mapping (D8). | a CloudEvents sender (a test sender in SAP's format) arrives as an event and is delivered |
| later | `oaap.events.queue`; Kafka/AMQP; a partner's event mesh over a destination; MQTT for apps; CESQL filters; xRegistry once released; bridging tenant events between nodes. | own RFCs |

### 12.1 Stage 1 in steps (2026-11-24)

`bestand` does not exist yet (RFC-0123 stage 1 is not built, and D21 comes
before it). Jörg, 2026-11-24: stage 1 is built with a **stand-in
receiver** — a small probe app on `oaap-test` takes `bestand`'s place;
`bestand` later uses the same door. The steps, each built, measured and
committed on its own:

| Step | What | Spec |
|---|---|---|
| 1.1 | D11, the ACL fix — **built, 0.1.360, §1.7** | `oaap.events.broker` 0.5 |
| 1.2 | Envelope, manifest block `events` (manifest 0.21), catalogue on the node, the key and the door, the store, grants on the command line, the feed — **built, 0.1.361, §1.8** | `oaap.events.bus` 0.1 |
| 1.3 | Addressed events (`oaapto`) with the platform's own record of who may address whom — **built, 0.1.362, §1.9** (the case door records the pair) | `oaap.events.bus` 0.2 |
| 1.4 | The push into the app (CloudEvents HTTP, HMAC, in order per subject, backoff, stop, resume) | `oaap.events.bus` 0.3 |
| 1.5 | `vorgaenge` publishes the status of cases opened from a backend; the probe app as the opener receives it once, and after a stop through the feed | `vorgaenge` |
| 1.6 | The relay without the sleep while a backlog remains (§1.6) | `oaap.data.twin` |

### Security requirements (proposed)

1. A publisher cannot set `source`, `id`, `time` or the `oaap*` extensions
   except `oaapto`; tested by sending them.
2. An app publishes only the types it declares; an undeclared type answers 403.
3. An addressed event reaches only the instance it names, and only an instance
   the publisher has a record of; tested with a stranger's name.
4. A subscription delivers only after the tenant admin's grant (except §6.1's two
   cases); a refused or revoked grant stops delivery at once.
5. No event crosses tenants; tested with two tenants on one node.
6. After stage 1 no tenant key can publish under `oaap/<tenant>/`; tested.
7. A `personal` type never leaves the tenant without the admin's permission for
   that target.

## 13. Decisions (Jörg, 2026-11-24, one by one, each as recommended)

| # | Question | Decision | Not chosen |
|---|---|---|---|
| **D1** | Which envelope? | **CloudEvents 1.0, JSON form, everywhere**; `source`/`id`/`time` set by the platform; extensions `oaaptenant`, `oaaporigin`, `oaapsemantic`, `oaapto` (§3). | Our own envelope; the AAS `EventPayload` form (experimental); CloudEvents only at the edge. |
| **D2** | How does an app say what it publishes and wants? | **`events.publishes` / `events.subscribes` in the manifest**, types versioned in the name, JSON Schema in the package, meaning after RFC-0125, audience `addressed · tenant · listed` (§4). | Types registered at runtime; no catalogue (anything goes). |
| **D3** | How does an app publish? | **Through a platform door** `POST /platform/events/` with a key like `cases`; never directly on the broker (§5). | A broker key per app (would need the ACL to know every type); both. |
| **D4** | How does a subscription come about? | **Declared in the manifest, granted by the tenant admin**, per instance and type, audited; filters `exact · prefix` first (§6.1). | Automatic for every declared subscription; a node-wide grant by the operator. |
| **D5** | How does an event reach only the app that caused it (cases → opener)? | **Addressed events** (`oaapto`), checked against the platform's own records, no grant needed, never broadcast (§6.2). | A broadcast with a filter on `context.object` (every app would see every case); a webhook per case template. |
| **D6** | How does an event get to the app? | **Pushed into the instance** (CloudEvents HTTP, HMAC, at-least-once, in order per subject) **with a pull feed behind it**; MQTT for apps later (§7). | MQTT for apps first; pull only. |
| **D7** | The way out? | **The twin's webhooks generalized** to any granted type, CloudEvents body, HMAC kept, OPTIONS handshake added; old body kept for existing hooks (§9). | A new webhook system beside the twin's; Bearer instead of HMAC. |
| **D8** | The way in? | **The twin's receivers get a CloudEvents mapping**: external calls become events of a declared type; a CloudEvents sender accepted as is (§9). | A separate inbound endpoint; only twin writes as today. |
| **D9** | How is the catalogue shown outward? | **AsyncAPI 3.1 export** per app and per tenant; xRegistry once released (§4). | xRegistry now (rc); no export. |
| **D10** | The twin's events? | **Into the store in the envelope** as `oaap.twin.object.*.v1` with group, instance and semantic ID; **the existing MQTT payload stays** for its readers (§11). | Replace the old payload at once; leave the twin outside. |
| **D11** | The broker's ACL (F3)? | **Only platform principals publish under `oaap/<tenant>/`**, tenant keys read-only there — in stage 1, independent of the rest. | Leave it until apps use the broker. |
| **D12** | Which first? | **`vorgaenge` → `bestand`** (addressed status), then identity → inviting app, then the twin with webhooks (§11). | The twin first; all at once. |

## Deutsche Zusammenfassung

**Worum es geht.** Jörg will Ereignisse als eigene Plattformfähigkeit, nach
**CloudEvents** (dem Format, mit dem SAP seine Cloud-Anwendungen koppelt):
Apps veröffentlichen ihre Ereignisse und abonnieren fremde, mit einer
Integrationsschicht über Broker, Webhooks oder Messaging.

**Was es schon gibt (am 24.11. gelesen).** Es gibt vier Ereigniswege, die
nichts voneinander wissen:
- das Relais des Zwillings zum MQTT-Broker;
- Webhooks nach außen mit HMAC und den Änderungsfeed;
- Webhooks nach innen mit Zuordnung;
- die eigene Übergabe-Outbox von `vorgaenge`.

Alle sind nur für den Zwilling gebaut, jeder mit eigenem Format. **Keine App
kann heute veröffentlichen oder abonnieren.** Es gibt kein Manifestfeld dafür,
der Broker nimmt nur ungescopte Schlüssel, und die stellt ein Operator von Hand
aus. **Eine Lücke:** Ein solcher Mandantenschlüssel darf auch auf die Themen des
Zwillings schreiben und so Zwilling-Ereignisse fälschen. **Am 24.11. auf
oaap-test gemessen (§1.5):** Ein Schlüssel mit der Rolle `user` hat eine
gefälschte Nachricht im Format des Relais als gehaltene Nachricht (retained)
abgelegt, und ein späterer Abonnent bekam sie wie eine echte. Fremde Mandanten,
den Metrikzweig und den Brückenzweig verweigert der Broker. Apps sitzen nicht
im Netz des Brokers; heute trifft die Lücke nur, wem ein Operator von Hand
einen ungescopten Schlüssel gibt.

**Durchsatz des Relais, gemessen am 24.11. (§1.6):** Das Relais schafft
für einen Mandanten etwa 60 Ereignisse pro Sekunde, der Zwilling erzeugt
bis zu 430. Bei einer großen Ladung kommt das letzte Ereignis erst nach
Minuten an (bei 22 222 Ereignissen nach 290 Sekunden). Schreiben zwei
Mandanten gleichzeitig, bekommt jeder nur noch 41 pro Sekunde, zusammen 82.
Das liegt an der Schleife: höchstens 200 Zeilen je Mandant und Durchgang,
nach jedem Durchgang 2 Sekunden Pause, und jede Nachricht wird einzeln
bestätigt abgewartet. App-Ereignisse laufen nicht über das Relais. Stufe 1
hängt ihre Zustellung deshalb nicht an diese Schleife und baut die Pause
bei Rückstau und das Einzelabwarten aus. Heute, bei wenigen Ereignissen pro
Minute, kostet das nichts; bei einem Import schon.

**CloudEvents** (v1.0.2, im Original geprüft) legt nur den Umschlag fest:
- Pflicht sind `id`, `source`, `specversion` und `type`.
- Bindungen gibt es für HTTP, MQTT, Kafka, AMQP und NATS, dazu einen
  Webhook-Teil mit Handshake.
- Subscriptions-API und xRegistry sind noch nicht veröffentlicht.
- SAP verlangt CloudEvents für jedes Ereignis über seinen Event Hub und
  beschreibt seinen Katalog teils in AsyncAPI.

**Lücke geschlossen am 24.11. (§1.7, Stufe 1, erster Schritt):** Ein
Mandantenschlüssel darf im Baum seines Mandanten nur noch lesen. Die Messung
aus §1.5 wurde wiederholt: Die Fälschung wird jetzt abgelehnt, und ein
späterer Abonnent bekommt nichts. Lesen geht weiter. Dabei aufgefallen: Wer
einen Mandantenbaum mit vielen gehaltenen Themen abonniert (s0 hat etwa
12 000), wartet fast 40 Sekunden auf die Bestätigung, weil der Broker für
jede gehaltene Nachricht einzeln bei identity nachfragt. Er bekommt außerdem
nur so viele Nachrichten, wie in die Warteschlange passen. Das betrifft die
Zustandsthemen des Zwillings, nicht die neuen Ereignisse, denn die werden
nicht gehalten. Festgehalten, nicht entschieden.

**Ereignisbus gebaut am 24.11. (§1.8, Schritt 1.2):** Eine App erklärt im
Manifest (0.21, Block `events`), was sie veröffentlicht und was sie empfangen
möchte. Sie bekommt einen eigenen Schlüssel und eine Tür auf ihrer Seite
(`/platform/events`). Die Plattform setzt Absender, Kennung und Zeit selbst,
prüft gegen das Schema und legt das Ereignis in der Ablage des Mandanten ab.
Empfangen wird erst nach einer Freigabe (`oaap events grant`), abgeholt wird
über den Feed. Auf oaap-test mit einer Probe-App gemessen: Gefälschte
Absenderangaben werden ersetzt. Nicht erklärte Typen, Schemafehler, zu große
Ereignisse und mehr als 120 pro Minute werden abgelehnt. Vor der Freigabe und
nach dem Widerruf kommt nichts an. Ein fremder Schlüssel kommt nicht durch die
Tür, und ein anderer Mandant sieht nichts. Als Nächstes kommen adressierte
Ereignisse (1.3) und der Push in die App (1.4).

**Adressierte Ereignisse gebaut am 24.11. (§1.9, Schritt 1.3):** Wie du
entschieden hast, merkt sich die Vorgangstür, welche Instanz bei welchem
Posteingang einreicht. Nur an so eine Instanz darf der Posteingang später
adressieren. Gemessen: Ohne Eintrag wird abgelehnt. Eine Einreichung legt
den Eintrag an, eine zweite zählt ihn hoch. Ein adressiertes Ereignis kommt
ohne Freigabe beim Empfänger an und nirgends sonst. Weil `vorgaenge` erst in
Schritt 1.5 veröffentlicht, wurde für diesen Teil ein Eintrag von Hand
gesetzt. Der Preis dieser Variante: Ist der Zwilling-Dienst ausgefallen,
scheitert auch die Einreichung eines Vorgangs.

**Entschieden (24.11., D1–D12 einzeln, jeweils wie empfohlen):**
- **Ein Umschlag:** CloudEvents 1.0 als JSON. `source`, `id` und Zeit setzt
  immer die Plattform, nie die App. Dazu kommen vier eigene Erweiterungen:
  Mandant, Herkunft, Bedeutung nach RFC-0125, Empfänger.
- **Ein Katalog je App im Manifest:** was sie veröffentlicht (Typ mit Version
  im Namen, JSON-Schema, Bedeutung, Zielgruppe) und was sie abonnieren will.
  Nach außen als AsyncAPI 3.1.
- **Veröffentlichen über eine Plattformtür**, mit einem eigenen Schlüssel wie
  bei den Vorgängen, nie direkt auf dem Broker.
- **Abonnements werden erteilt, nicht genommen:** Der Tenant-Admin gibt sie
  frei.
- **Adressierte Ereignisse** gehen nur an eine bestimmte Instanz, z. B. ein
  Vorgang an die App, die ihn geöffnet hat (RFC-0123 D15). Sie brauchen keine
  Freigabe und laufen nie über einen allgemeinen Kanal.
- **Zustellung:** Die Plattform schiebt jedes Ereignis in die App, signiert,
  mindestens einmal und je Gegenstand in Reihenfolge. Dahinter steht ein Feed
  zum Nachholen.
- **Nach außen** werden die Zwilling-Webhooks für jeden freigegebenen Typ
  verallgemeinert, im CloudEvents-Format mit Handshake. **Nach innen** bekommen
  die Empfänger eine CloudEvents-Zuordnung.
- **Der Broker** bleibt der Bus innen. Nur die Plattform schreibt dort unter
  `oaap/<tenant>/`; das schließt die Lücke.
- **Der Zwilling** schreibt seine Ereignisse ebenfalls in den Umschlag. Das
  alte MQTT-Format bleibt für seine bisherigen Leser.
- **Reihenfolge der ersten Paare:** `vorgaenge` → `bestand`, dann Identity →
  einladende App (RFC-0126), dann der Zwilling mit Webhooks.

**Nicht hier:** Queues und gesicherte Zustellung zwischen Knoten, Kafka/AMQP,
die Kopplung an einen fremden Event Mesh (etwa SAP), Benachrichtigungen an
Menschen und AAS-Ereignisse. Alles das kommt später auf diesem Umschlag.

**Stufen.** Stufe 0 misst die Lücke, den Durchsatz des Relais und ob
Instanznetze den Broker erreichen — am 24.11. erledigt (§1.5, §1.6). Stufe 1 bringt die Lückenschließung
(am 24.11. gebaut, 0.1.360, §1.7),
Umschlag, Ablage, Katalog, Tür, Freigaben, adressierte Ereignisse und
Zustellung, mit `vorgaenge` → `bestand` als erstem Paar. Stufe 2 bringt die
Plattformtypen, die Portalseite und den AsyncAPI-Export. Stufe 3 bringt
Webhooks und Empfänger im CloudEvents-Format.

**Nicht gelesen, nicht gemessen:** alles in §1.4, dazu der AsyncAPI-Text und die
AsyncAPI-Fassung bei SAP.
