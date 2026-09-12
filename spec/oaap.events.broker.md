# oaap.events.broker — The MQTT Broker per Node

- **ID:** `oaap.events.broker`
- **Version:** 0.2
- **Maturity:** draft (0.2 adds the platform principal `oaap.relay`,
  §2.4, with which `oaap.data.twin` 0.3's outbox relay publishes — the
  first thing that actually arrives on the topic tree)
- **Based on:** RFC-0032 (events, states, and the unified namespace —
  this spec is build-order step 1: the broker; step 2, the relay and
  the `states` table, lives in `oaap.data.twin` 0.3 §2.13), RFC-0011
  (node profiles — this spec registers the profile `broker`, see
  `oaap.core.host` 2.5), RFC-0015 (non-HTTP endpoints — the transport
  this spec uses, referenced not redesigned), RFC-0027 (machine
  principals — how a client authenticates), RFC-0022 (tenant as
  boundary — the topic tree's own boundary-at-the-edge principle)

## 1. Purpose

One **MQTT broker per node**, offered as a platform service — gated by
its own node profile, `broker`, **independent of `store`**: a
back-office tenant has a digital twin but no reason to run real-time
messaging, exactly as a small node has no reason to run Postgres
(`oaap.data.store`).

This spec establishes the broker, its topic tree, and how a client
proves who it is. **Since 0.2 something publishes to it:** the outbox
relay of `oaap.data.twin` 0.3 (§2.13 there) reads every tenant's
`events` table and publishes each row on the tree of §2.2. That relay
is the twin's, not this spec's — this spec only adds the one principal
it logs in with (§2.4) and the service's place beside the broker
(§2.1).

Out of scope for 0.2: a simulated-machine reference app (build-order
step 3), RFC-0028's presence-event MQTT adapter (step 4), a real device
(step 5), guaranteed delivery/edge sync (a separate future capability,
tentatively `oaap.events.queue`, RFC-0032 §2).

## 2. Interface

### 2.1 The service

- A platform service `broker` (Mosquitto with the `mosquitto-go-auth`
  plugin — see §3), reachable on the platform network at all times.
- **Node profile `broker`** (new, registering with RFC-0011 /
  `oaap.core.host` 2.5): a node carries the service only when profiled
  for it, **independent of `store`**. A node without the profile MUST
  NOT run the service.
- **The relay rides on the same profile** (0.2): `oaap.data.twin` 0.3's
  `relay` service is started and stopped together with `broker` — no
  broker, no relay (decision of 2026-09-12). A node with `store` but
  without `broker` keeps recording events; they wait in the outbox and
  the portal says so (`oaap.core.portal` 2.5).
- Two listeners, two very different reachability rules:
  - **WebSocket (port 9001), for browsers.** Reached **only** through
    the gateway's `/broker/*` route, never published to the host
    directly — the same posture `oaap.data.twin`'s `/twin/*` already
    uses. The gateway's `forward_auth` gates *establishing the tunnel*
    to a session with role `user`; the MQTT `CONNECT` inside it still
    needs its own valid key (§2.4) — two gates for this transport only.
  - **Raw TCP (port 1883), for devices that cannot speak HTTP and carry
    no identity (RFC-0015 Stage 1).** Reachable on the platform network
    unconditionally (the relay above, and the simulated-machine
    reference app of build-order step 3, need no host port at all), but
    published to the **host** only when the node ALSO carries the node
    profile `exposed` (RFC-0015's existing purpose: an operator grants
    a non-HTTP port that bypasses the gateway). `broker` alone never
    opens a port on the host — this spec reuses `exposed` rather than
    inventing a second grant mechanism for one platform service.
- `install.sh`/`migrate.sh`: an existing node that gains the `broker`
  profile gets the service on its next update, matching `store`'s own
  pattern; a node without the profile is never touched. **Every**
  compose call that (re)creates the broker — the profile command, the
  update, the migration's safety net — MUST name the same file set,
  including the `exposed` overlay when both profiles are held; a call
  that names the base file alone recreates the broker without its raw
  port (found in the update path while building 0.2, before any node
  held both profiles).

### 2.2 The topic tree (RFC-0032 D1/§1.1)

```
oaap/<tenant-id>/<type-key>/<object-id>/<group-key>
```

The same identifiers `oaap.data.twin` already assigns and exposes —
nothing about the tree needs translating twice. Tenant first, not
last, so one ACL rule (§2.4) scopes a client to `oaap/<tenant-id>/#` —
the same boundary-at-the-edge principle RFC-0022 uses at the gateway.
Not modelled after i3x or RAMI 4.0's site/area/line/asset (RFC-0032
§1.1 — i3x turned out to be a query API, not a topic-naming standard).

An event that concerns a whole object rather than one of its groups
(a merge or unmerge) is published one level up, on
`oaap/<tenant-id>/<type-key>/<object-id>`.

### 2.3 The message on the wire (RFC-0032 §1.3, not this spec's decision)

Already decided by RFC-0031/RFC-0032: each publish is the twin's own
thin `events` row (`kind`, `object_id`, `group_key`, `origin` — no
payload fields; the relay adds the row's `id` and `recorded_at` so a
subscriber can order and de-duplicate), as JSON, **retained**, QoS 1.
A subscriber arriving after the fact still sees the last message on
each topic without a separate round trip. Published by
`oaap.data.twin` 0.3's relay (§2.13 there), not by anything in this
spec.

### 2.4 Authentication and authorization (RFC-0032 D2, RFC-0027 reused)

No local password file, no local ACL file — every `CONNECT` and every
topic action (publish AND subscribe, wildcards included) is checked
**live** against `oaap.core.identity`, the same "ask the one service
that knows" posture `/verify` already uses for every HTTP route.

**Clients — apps, devices, browsers — use an RFC-0027 key:**

- The MQTT **password** carries the full RFC-0027 key token
  (`oaapk_<id>_<secret>`); the MQTT **username** MUST be that same key's
  id, in the clear. A mismatch refuses — the check exists so a
  copy-paste or field-ordering mistake refuses loudly rather than
  silently authenticating as the wrong half of the pair.
- Only an **unscoped** machine key is accepted. A key issued with an
  `instance` scope (RFC-0027 D5 — the kind `oaap.data.twin`'s own
  internal key uses for `/twin/*`) MUST be refused here: that scoping
  is for one app's HTTP calls through a specific gateway route, not for
  a broker connection.
- Every topic a connected client touches MUST fall inside
  `oaap/<tenant>/` for **that key's own tenant** (§2.2) — a literal
  publish topic and a subscription filter are checked the same way; a
  filter like `oaap/<tenant>/#` is inside the boundary, a bare `#` or
  another tenant's prefix is not.

**The platform relay uses its own principal (0.2):**

- Username **`oaap.relay`**, password the node secret
  **`BROKER_RELAY_KEY`** (§3). Decision of 2026-09-12, chosen over one
  RFC-0027 key per tenant: a key is confined to its own tenant's tree,
  and the relay publishes for every tenant on the node; a per-tenant
  key would also expire (RFC-0027 caps validity) and silently stop the
  relay a year later. The relay container already holds every tenant
  schema's database credential, so a cross-tenant broker principal
  gives it nothing it could not already reach.
- The name contains a dot, which no RFC-0027 key id (hex digits) can
  ever contain — the two paths cannot be confused, by syntax rather
  than by a reservation someone has to remember.
- It may **publish only** — never subscribe, never read — and only to a
  literal topic of the shape of §2.2 (with or without the group level)
  whose `<tenant-id>` is a tenant this node knows.

Identity exposes two internal routes for this
(`/mqtt-auth/getuser`, `/mqtt-auth/aclcheck`, matching the
`mosquitto-go-auth` HTTP backend's own contract) — deliberately
**not** under `/internal/*`: that prefix's guard checks a request
header, and the broker's auth plugin has no configuration option to
set one. The same shared platform key instead travels in the query
string, which is safe here because the call never leaves the
platform network (`auth_opt_http_host` names the container, not a
public address).

A browser or a device that never obtained a key (no session, or a
session without a machine key of its own) simply cannot connect — this
spec does not build a way to mint one automatically from a logged-in
session; an operator issues a machine key today the same way for a
broker client as for any other (`oaap.core.identity`'s existing "Zugänge"
surface, RFC-0027).

## 3. Configuration

- Broker image: `iegomez/mosquitto-go-auth` (Mosquitto plus the
  `mosquitto-go-auth` plugin, so every CONNECT is a live decision
  rather than a static file) — provider-defined exact tag, pinned.
- The platform's existing `INTERNAL_API_KEY` is reused as the shared
  secret between the broker's auth plugin and identity's two routes
  (§2.4) — no new secret for that call.
- `BROKER_RELAY_KEY` (0.2): the relay principal's password, generated
  by the installer and — for a node that reaches 0.2 by updating — by
  the migration step, whether or not the node carries `broker`, so it
  is in place the day the profile is added. Held by `identity` (which
  checks it) and `relay` (which presents it) only — not by the broker,
  the twin, or the portal.
- Data path: under the platform data directory (MQTT persistence —
  retained messages, session state — never a tenant's own tree).
- Raw device port: 1883. WebSocket listener: 9001 (internal only, see
  §2.1).

## 4. Security requirements

- `allow_anonymous` MUST be `false`. No local password file, no local
  ACL file — the plugin has nothing to fall back to if identity is
  unreachable, and a `CONNECT` MUST be refused, not allowed, when the
  auth backend cannot be reached.
- The shared secret used for the auth-plugin callback MUST fail closed
  if unconfigured, exactly like `oaap.core.identity`'s existing
  `/internal/*` guard — a node whose key was never generated loses
  broker access loudly, not silently.
- A scoped (RFC-0027 D5) machine key MUST be refused for broker access
  (§2.4) — this spec's own boundary, distinct from and no looser than
  the boundary that scoping exists for elsewhere.
- The relay principal (§2.4) MUST fail closed as well: on a node without
  `BROKER_RELAY_KEY`, `oaap.relay` MUST NOT connect — not even with an
  empty password — and MUST NOT be granted any topic. When configured,
  it MUST be refused every subscribe and every read, every wildcard,
  every topic outside `oaap/<known tenant-id>/…`.
- The raw device port MUST NOT be published to the host unless the
  node carries `exposed`, and MUST stop being published the moment
  `exposed` is removed while `broker` is still held (no stale port
  surviving a profile change) — and MUST NOT be lost by an update of a
  node that holds both (§2.1).
- The WebSocket listener MUST NOT be published to the host directly —
  reachable only through the gateway's `forward_auth`-gated route.

## 5. Conformance tests (described)

1. **Profile gating:** a node without the `broker` profile runs no
   broker service and has nothing listening on 1883 or 9001. A node
   that gains the profile gets the service on its next update; one
   that never had it is never touched.
2. **Port gating, both directions:** with `broker` alone, port 1883 is
   NOT reachable from outside the platform network. Adding `exposed`
   makes it reachable within seconds, without a manual container
   restart; removing `exposed` again closes it the same way, while the
   broker itself keeps running.
3. **Authentication:** an unscoped, valid RFC-0027 machine key connects
   successfully (username = key id, password = full token); a
   malformed token, a username that does not match the key id, an
   unknown or revoked key, and an instance-SCOPED key are all refused.
   No anonymous connection succeeds.
4. **Authorization:** a connected client may publish and subscribe
   (including wildcard filters) anywhere under its own
   `oaap/<tenant>/...` tree and nowhere else — checked with a literal
   topic, a same-tenant wildcard filter, another tenant's tree, and a
   bare `#`.
5. **WebSocket path:** `/broker/*` refuses a request with no session
   (same as any other protected route) before ever reaching the
   broker; a logged-in session's WebSocket upgrade reaches the broker's
   9001 listener, where the same authentication/authorization rules
   (tests 3–4) still apply to the MQTT session inside it.
6. **The relay principal (0.2):** `oaap.relay` with the node's
   `BROKER_RELAY_KEY` connects; with a wrong or empty password it does
   not, and on a node without the secret it never does. Connected, it
   may publish to `oaap/<known tenant>/<type>/<object>[/<group>]`, and
   is refused a subscription, a read, a wildcard, an unknown tenant's
   tree and anything outside `oaap/`.

## 6. Dependencies

`oaap.core.host` (RFC-0011 node profiles, §2.5 — this spec registers
the name `broker` there), `oaap.core.identity` (the two routes that
decide every CONNECT and every topic action; the RFC-0027 key a client
authenticates with; the relay principal's check), `oaap.data.twin`
(the topic tree's vocabulary — tenant, type, object, group — the
`events` row shape of §2.3, and, since 0.3, the relay that publishes
it), `oaap.core.gateway` (the `/broker/*` route and its
`forward_auth`).

## 7. Maturity

`draft` — becomes `beta` once conformance tests 1–6 pass on the
reference platform (`oaap-test`), including the port-gating round trip
(test 2) verified with an actual external client, not only a container
on the platform network. Tests 1–5 passed there on 2026-09-11/12
(CURRENT_STATE 135 and 137, the WebSocket path of test 5 with a real
MQTT-over-WebSocket client through a logged-in session).

## Deutsche Zusammenfassung (v0.1)

**Ein MQTT-Broker je Knoten**, unabhängig vom Profil `store`: ein reiner
Backoffice-Mandant hat einen digitalen Zwilling, aber keinen Grund für
Echtzeit-Nachrichten. Diese Spec baut den Broker, den Themenbaum und die
Anmeldung.

**Zwei Wege, zwei sehr unterschiedliche Regeln.** Der WebSocket-Weg
(Port 9001) ist nie direkt erreichbar, nur durch die Gateway
(`/broker/*`), genau wie beim digitalen Zwilling — die Gateway sichert
den Tunnel mit einer angemeldeten Sitzung, der eigentliche MQTT-Connect
darin braucht trotzdem einen echten Schlüssel. Der rohe Geräte-Port
(1883) ist im Plattformnetz immer erreichbar, aber am Host nur, wenn
der Knoten **zusätzlich** das Profil `exposed` trägt — dieselbe
Freigabe, die RFC-0015 für genau diesen Zweck schon vorsieht, nicht neu
erfunden.

**Keine lokale Passwortdatei, keine lokale ACL-Datei.** Jeder Connect
und jede Themen-Aktion wird live gegen den Identity-Dienst geprüft: das
MQTT-Passwort trägt den vollen RFC-0027-Schlüssel, der Benutzername
muss dessen eigene ID sein. Nur ein **nicht** an eine Instanz gebundener
Schlüssel wird akzeptiert — ein instanzgebundener wie der des Zwillings
selbst wird hier abgelehnt. Jedes Thema muss innerhalb des eigenen
`oaap/<mandant>/...`-Baums liegen (RFC-0032 §1.1) — dieselbe
Randschärfe, die RFC-0022 an der Gateway schon verlangt.

## Deutsche Zusammenfassung (Nachtrag v0.2)

**Jetzt kommt etwas an.** Das Relais aus `oaap.data.twin` 0.3 liest die
`events` jedes Mandanten und veröffentlicht sie im Themenbaum —
„retained", damit ein später Abonnent die letzte Nachricht je Thema
trotzdem sieht. Das Relais selbst gehört zum Zwilling; diese Spec regelt
nur, **wie es sich am Broker anmeldet**, und dass es mit dem Profil
`broker` kommt und geht.

**Eigenes Plattform-Geheimnis statt Schlüssel je Mandant** (Jörgs
Entscheidung vom 12.09.): Benutzer `oaap.relay`, Passwort
`BROKER_RELAY_KEY`, beim Installieren oder beim Update automatisch
erzeugt. Ein RFC-0027-Schlüssel darf nur in den Baum seines eigenen
Mandanten; das Relais veröffentlicht aber für alle — und ein Schlüssel
liefe nach spätestens einem Jahr ab. Das Relais kennt ohnehin schon die
Datenbank-Zugänge aller Mandanten, bekommt also nichts dazu.

**Eng gefasst:** `oaap.relay` darf **nur veröffentlichen**, nie
abonnieren oder lesen, nur in wörtliche Themen der Form
`oaap/<bekannter Mandant>/<typ>/<objekt>[/<gruppe>]`. Fehlt das
Geheimnis auf dem Knoten, gibt es den Benutzer schlicht nicht — auch
nicht mit leerem Passwort.

**Ein Fund beim Bauen:** Das Update zog den Broker bisher immer nur mit
`docker-compose.yml` hoch, ohne die Zusatzdatei für den Geräte-Port. Auf
einem Knoten mit `broker` **und** `exposed` hätte jedes `oaap update`
Port 1883 geschlossen. Noch trägt kein Knoten beide Profile; behoben,
bevor es einen trifft.
