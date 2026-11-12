# RFC-0085: Pairing and Fleet Observation — Every Node Reports to One Hub, Service Providers Receive Profiles

- **Status:** **Accepted (2026-11-12, D1–D11 as recommended)** — nothing
  built; roll-out of anything on oaap-demo and oaapx01 waits for Jörg's word
- **Date:** 2026-11-12
- **Authors:** Jörg (the need: "monitor my nodes and get fleet management
  going; collect health data through a broker on oaapx01 and route it to
  oaap-demo; everything fail-safe through queuing; internal nodes send to
  oaap-demo directly, external ones through oaapx01; statistics and
  monitoring; watch the other brokers and the expected signs of life;
  build an infrastructure picture from the topic prefixes; feed external
  dashboards over MQTT; a twin per node; FleetView was not trivial — it
  must become simpler and operable from the portal, a pairing by key
  exchange; several service providers — hardware, security, AMS — as
  receivers with data profiles, each with its own twin; our twins live on
  oaap-demo"), Claude (facts read in reference 0.1.264 and on oaap-demo,
  design)
- **Depends on:** RFC-0021 (fleet status, and its outlook on
  partner-managed fleets), RFC-0031 (twin), RFC-0032 / `oaap.events.broker`
  (broker, topic tree), RFC-0051 (node metrics, queue), RFC-0052 (sender),
  RFC-0054 (node and operator keys, TLS), RFC-0080 /
  `oaap.core.notifications` (alerts), RFC-0082 (alias, place, tags),
  RFC-0039 (`support` vs. `partner`)
- **Not part of this RFC:** time series as a platform capability (RFC-0086,
  next — this RFC only says where its data comes from); acting on nodes
  from the hub (RFC-0021 stage 2); collecting new hardware or security
  measurements (this RFC reserves their branches, §3); payload traces.

## Summary

The pieces of a fleet observation exist, and both ends are measured: every
node samples, stores and queues its metrics (RFC-0051); a sender delivers
the queue to an MQTT broker and deletes nothing the broker has not
acknowledged (RFC-0052); the broker binds node keys to one node name and
protects the metrics branch (RFC-0054). FleetView shows the fleet by
polling. **What is missing is the middle** — nobody receives, nobody
watches, nothing is set up — and the setup that exists asks for
hand-copied keys in environment variables.

This RFC makes the middle one shape:

1. **One hub.** Every node pairs **once**, with the hub (oaap-demo, tenant
   `oaap-ops`). Nodes that cannot reach the hub send to an **entry**
   (oaapx01), and the hub opens a bridge **outward** to the entry, so the
   home network opens no port.
2. **Pairing by code, in the portal.** The hub shows a one-time code; the
   node's portal takes it, shows what will leave the node, and asks for
   confirmation. Keys are exchanged by the platforms and never shown.
3. **The node decides what leaves; the hub decides who sees it.** Neither
   can widen the other's decision.
4. **Liveness by expectation.** A node that has not reported within its
   interval is silent; the hub alerts through RFC-0080. Hub and entry
   watch each other, so the loss of the hub is reported too.
5. **Service providers receive profiles, never node access.** A profile is
   a set of topic classes and a node selection; the broker enforces it. A
   provider receives into its own tenant on the hub (with its own twin) or
   with a read key into its own tools.
6. **Every node gets a twin** in `oaap-ops`; the topic tree creates the
   objects, the twin holds the relations, and the infrastructure picture
   is drawn from the twin.

## 1. Facts (read 2026-11-12, reference 0.1.264)

1. **The sender holds no connection.** Once a minute it opens one
   connection, publishes the pending queue (QoS 1, retained) to
   `oaap-node/<node-id>/metrics/<series>`, and disconnects (RFC-0052 §2).
   Its `CONNECT` sets user, password and clean start and **no will**
   (`metrics_sender.connect_packet`, flags `0xc2`). **An MQTT Last Will
   therefore cannot tell a dead node from a finished run**, and this RFC
   does not use one (§6). The node keeps up to 7 days in its queue.
2. **The broker** is `oaap.events.broker`: Mosquitto with mosquitto-go-auth,
   checked live against identity on the broker's own node; `persistence
   true`; **no `max_queued_messages` set** (the Mosquitto default applies).
   Node keys write only `<root>/<own name>/#` and cannot subscribe;
   operator keys carry grants on trees outside the tenant trees; writing
   under the metrics root is refused to every key but the node's own
   (RFC-0054 §5–§6). **Grants cannot be changed after issue** (RFC-0054
   §9.2, stage 4). TLS on 8883 is published only with `exposed`.
3. **Where it runs:** the profile `broker` is on oaap-test and oaap-demo;
   **not on oaapx01**. **No sender is configured on any node** — the
   Raspberry Pi's was removed after the measurement of 2026-10-02.
4. **FleetView 0.3.5** runs on oaap-demo (production). It polls
   `GET /fleet/status` per node with a fleet key; nodes and keys are typed
   into `FLEETVIEW_NODES` / `FLEETVIEW_KEYS`. Strictly read-only. Jörg:
   "not trivial" — the reason for §4.
5. **oaap-demo** carries the profiles `broker`, `dev`, `exposed` — **not
   `store`**, so it holds no twin today. The tenant **`oaap-ops`** was
   created on 2026-11-12 (no users, no instances). Disk: 229 GB free.
6. **Alerts are per node.** RFC-0080 sends mail from the node that sees
   the problem (types today: `instance.down`, `instance.rebuild`,
   `login.locked`, `backup.failed`, `backup.missing`, `disk.full`,
   `exposure.found`, `reboot.planned`). Nothing notices a node that has
   stopped, because that node is the one that would send.
7. **Care events already use a broker:** where `broker` runs, the reboot
   plan publishes retained messages under `oaap/<default>/node/#` — on the
   node's own broker, in a tenant tree.
8. **`/fleet/status` 0.9** carries `node`, `alias`, `place`, `tags`
   (RFC-0082), versions, instances and `attention` markers.
9. **The twin has relations** with validity (`valid_from`/`valid_to`) and
   a query that walks relations outward from one object, depth 2 by
   default, at most 5 (`oaap.data.twin`).
10. **RFC-0021's outlook fixes the trust model for providers:** trust is
    created by the owner; a provider gets rights on the central node, never
    on the managed nodes; revocation is immediate and complete because the
    provider never held a node key; several providers in parallel; the
    owner sees who did what.

**Open facts, measured in stage 1 before anything depends on them:**

- **F1.** A message that arrives over a bridge **the local broker opened**:
  does mosquitto-go-auth check it with `aclcheck`, and under which user? If
  yes, the hub's rule "only the node writes its branch" refuses every
  bridged value, and §5.4 needs its alternative.
- **F2.** The entry's queue for a bridge that is away: what Mosquitto keeps
  by default, what it drops first, and how it can be counted.
- **F3.** The size of a real `/fleet/status` document on oaapx01 (the
  largest node) as one MQTT message.

## 2. The picture

```text
 internal node ──────────────── TLS ─────────────┐
 internal node ──────────────── TLS ─────────────┤
                                                  ▼
 external node ── TLS ──► ENTRY broker      HUB broker (oaap-demo)
 external node ── TLS ──►  (oaapx01)  ◄──── bridge, opened by the hub
                              │               │
                              │               ├─ fleet service (§6, §8)
                              │               │    └─► twin of oaap-ops
                              │               ├─► provider tenant A (own twin)
                              │               ├─► provider tenant B (own twin)
                              │               └─► read key → external dashboard
                              └─ watches the hub (§6.3)
```

Words used in this RFC:

| Word | Meaning |
|---|---|
| **node** | an OAAP node that reports |
| **hub** | the node whose broker collects everything and whose platform watches (oaap-demo) |
| **entry** | a broker node that takes reports from nodes that cannot reach the hub (oaapx01); every entry is bridged to exactly one hub |
| **observation tenant** | a tenant on the hub that receives data into its twin: `oaap-ops` for the owner, one per provider |
| **service provider** | a company that receives a profile (hardware, security, AMS). Not the role `partner` and not the role `support` (RFC-0039): a provider receives data and acts on nothing |
| **profile** | which classes (§3) of which nodes a receiver gets |

The hub is also an entry for the nodes that reach it directly.

## 3. The topic tree of the fleet

The root stays **`oaap-node`** (configurable, RFC-0052 §2). It has readers
already — the sender's default, the broker's protection rule, RFC-0054's
key kinds — and a renamed root would have to be carried through all of
them. Below the node name, the first level is a **class**: one class per
kind of data, so that a profile is a list of topic filters and the broker
enforces it without logic of its own.

| Class | Topic | Content | Retained | Personal data possible |
|---|---|---|---|---|
| `alive` | `oaap-node/<n>/alive` | every run: time, sequence number, platform version, the interval the node promises | yes | no |
| `metrics` | `oaap-node/<n>/metrics/<series>` | as today (RFC-0051) | yes | no |
| `status` | `oaap-node/<n>/status` | the `/fleet/status` document, on change and at least hourly | yes | **business data** (tenant labels, instance names) |
| `events` | `oaap-node/<n>/events/<type>` | the node's RFC-0080 messages (§6.4), with the same type names | no | **yes** (`login.locked` names an account) |
| `security` | `oaap-node/<n>/security/…` | reserved: open CVEs, waiting updates, image findings | — | no |
| `hw` | `oaap-node/<n>/hw/…` | reserved: SMART, temperatures, hardware inventory | — | no |
| `backup` | `oaap-node/<n>/backup/…` | reserved: generations, vault state | — | no |

Infrastructure topics, written by the platform of the broker node, never
by a node key:

| Topic | Written by | Content |
|---|---|---|
| `oaap-node/<hub>/bridge/<entry>` | the hub's broker (Mosquitto bridge notification) | `1` connected, `0` not; retained |
| `oaap-node/<b>/broker` | the broker node's minutely job | clients connected, messages queued and dropped, uptime |
| `oaap-fleet/control/<entry>/…` | the hub | commands to the entry (§4.5) — the only tree the bridge carries outward |

The "infrastructure picture from the prefixes" (Jörg) reads this tree:
node names, which broker a node reports to, which entry is bridged to which
hub. **The tree gives groups, not relations**; §9 turns it into objects and
relations in the twin.

## 4. Pairing

### 4.1 What the operator does

1. **At the hub:** the server_admin opens *Flotte → Knoten koppeln* in the
   portal, chooses the way in (direct, or an entry by name) and gets a code:
   valid 15 minutes, usable once, shown as a text block and a QR code.
2. **At the node:** the server_admin opens *Flotte → Kopplung*, pastes the
   code. The node shows **who** receives (the hub's alias), **through
   which** broker, and **which classes** it will send, as checkboxes
   (default: `alive`, `metrics`, `status`, `events`), with the
   personal-data marker of §3 next to `events`. Confirm.
3. **Done.** The node sends its first `alive` and `status`; the hub's
   portal shows the node as *gekoppelt* within a minute. No key, address or
   environment variable is typed anywhere.

The same steps exist as commands (`oaap fleet pair-code`, `oaap fleet pair
<code>`, `oaap fleet unpair`), calling the same functions as the portal.

### 4.2 What the platforms do

The code carries: the hub's name, the entry's HTTPS address and broker
address, the fingerprint of the certificate the node must see there, a
one-time secret, the expiry, and a MAC over all of it (§4.3).

1. The node calls `POST /fleet/pair` **at the entry** (for direct pairing:
   at the hub) over HTTPS, verifying the fingerprint, with the code, its
   node name and the classes it offers.
2. The entry checks the MAC, the expiry and that the secret is unused,
   issues a **node key** on its broker bound to the node name (RFC-0054),
   and answers with user, secret, broker address and CA.
3. The node configures its sender exactly as `oaap metrics sender set`
   does, stores which classes it offers, and records the pairing (hub,
   entry, time) in a file the portal reads.
4. The entry announces nothing separately: the hub learns of the node
   from the node's own first `alive` and `status`, which reach it over the
   bridge like every later message. No second channel.

**Name conflicts:** a node name for which the entry holds an active node
key is refused ("already paired"), unless the code was made as a
replacement for that node (a reinstalled node).

### 4.3 The trust between hub and entry

An entry must accept the hub's codes, and the hub must reach the entry's
broker. That is a pairing one level up, made once per entry with the same
steps: the hub shows an *entry code*, the entry's server_admin pastes it
in *Flotte → Eingang für Zentrale*. The entry then

- issues an **operator key** for the bridge with two grants: read
  `oaap-node/#` (what flows to the hub) and write
  `oaap-fleet/control/<entry>/#` (the hub's commands, §4.5);
- stores a **pairing secret** shared with the hub, with which the hub signs
  node codes (HMAC-SHA256 — the standard library has it, no new
  dependency);
- watches the bridge client (§6.3).

The hub configures its side of the bridge (§5.3) from the answer.

### 4.4 The rule

> **The node decides what leaves it. The hub decides who sees it.
> Neither can widen the other's decision.**

The hub cannot ask a node for a class the node does not offer; a node can
withdraw a class at any time in *Flotte → Kopplung*, and the hub shows the
class as *nicht angeboten*, not as missing data. (Same sentence, same
direction as RFC-0033: the inner side decides what is reachable.)

### 4.5 Unpairing

- **From the node:** *Kopplung lösen* removes the sender, its secret and
  the offered classes, and tells the entry (best effort). The queue stays
  (RFC-0052).
- **From the hub:** *Knoten entfernen* publishes a revoke command on
  `oaap-fleet/control/<entry>/revoke/<n>`; the entry revokes the node key.
  The node's next run is refused, it stops sending (RFC-0052 waits the long
  backoff after an authorization refusal) and its portal says *Kopplung vom
  Empfänger aufgehoben*. **Revocation never depends on the node.**
- The hub keeps the node's twin object and history; the object is marked
  *entkoppelt* with the time (§9).

### 4.6 What becomes of fleet keys

The hub no longer needs to reach a node: the status document arrives as
the `status` class. `GET /fleet/status` and fleet keys stay as they are
(other readers, Uptime Kuma, scripts), but the hub does not use them, and
FleetView's environment variables are retired with stage 4 (§10).

## 5. Delivery and queuing

### 5.1 Three buffers, none of them silent

| Where | Holds | Bound | Counted |
|---|---|---|---|
| node outbox (RFC-0051) | everything not acknowledged by the entry or hub | 7 days, size | yes, today |
| entry, bridge session | everything for the hub while the bridge is away | **24 hours** (to configure, F2) | yes, `oaap-node/<entry>/broker` |
| hub, fleet service session | everything for the receiver while it is down | persistent session, QoS 1 | yes |

A loss is always counted where it happens and shown in the hub's portal;
nothing is dropped without a number.

### 5.2 The ways in

- **Internal node → hub:** TLS on the hub's 8883, the node's CA of the hub
  (RFC-0054 §2). The plain port (`broker-plain`) is not used for the fleet.
- **External node → entry:** TLS on the entry's public 8883 with the
  certificate the gateway already holds. oaapx01 needs `broker` (and has
  `exposed` to confirm in stage 1).

### 5.3 The bridge

Opened **by the hub**, outbound — the home network publishes no port for
the fleet. Mosquitto bridge settings in short: `topic oaap-node/# in 1`,
`topic oaap-fleet/control/<entry>/# out 1`, a persistent session (clean
start off), the operator key of §4.3, TLS verifying the entry's
certificate, and a notification topic `oaap-node/<hub>/bridge/<entry>`.

*For Jörg:* a bridge is a broker that logs into another broker as a
client and forwards selected topics. In SAP terms it resembles a qRFC
queue between two systems: what cannot be delivered waits, in order, and
is delivered when the connection is back.

### 5.4 Trust on the bridged branch

The hub's rule (RFC-0054 §6): *writing under the root is refused to every
key except the node's own.* A bridged value was written by the node — on
the entry, where the entry's broker enforced the same rule. If F1 shows
that the hub checks bridged messages too, the rule is extended, in the
check, to: **the bridge of an entry may carry `oaap-node/<n>/…` for the
nodes paired through that entry, and for nothing else.** The hub knows
which nodes those are from the pairing (§4.2). If F1 shows that bridged
messages are not checked, the hub still drops, in the fleet service, any
bridged value for a node not paired through that entry, and counts it.

### 5.5 History is the receiver's job

Retained messages keep the last value of each topic, not the history
(RFC-0052 §2). The fleet service (§8) reads with a persistent session and
writes each value on arrival; where the values are kept is RFC-0086.

## 6. Liveness, brokers, alerts

### 6.1 A node that falls silent

Each `alive` carries the interval the node promises (default 60 s). The
hub's fleet service raises **`node.silent`** when no `alive` has arrived
for **5 minutes** (the threshold of `instance.down`), and **`node.back`**
when one arrives again, with the silent span. A node whose status is
*unknown* — never seen since pairing, or after a hub restart before the
first full interval — is **unknown**, not fine and not silent (the rule of
`instance.down`).

A silent node behind an entry whose bridge is down is **not** reported as
silent: the hub cannot know. It is shown as *unbekannt, Eingang getrennt*,
and the bridge alert (§6.2) carries the list of nodes behind it.

### 6.2 Brokers and bridges

- **`bridge.down`**: the notification topic of an entry's bridge has been
  `0` for 5 minutes. **`bridge.back`** with the span and how many messages
  the entry kept and dropped in between.
- **`broker.queue`**: an entry's bridge queue above 50 % of its bound
  (§5.1) — warn before it starts dropping.
- **`node.loss`**: a node reports (in `alive`) that its own outbox dropped
  data (RFC-0051 counts it today).

### 6.3 Who watches the hub

The hub cannot report its own death. **Each entry watches its hub:** if the
hub's bridge client has not been connected to the entry for 10 minutes,
the entry raises **`hub.unreachable`** through its *own* RFC-0080 lists
(the entry's server owner). oaapx01 is on the internet, so it can still
mail when the house is dark. With one entry this is a mutual watch
(hub ↔ oaapx01); a fleet without any entry has no outside watcher, and the
hub's portal says so.

### 6.4 Alerts stay RFC-0080

All new types (`node.silent`, `node.back`, `node.loss`, `bridge.down`,
`bridge.back`, `broker.queue`, `hub.unreachable`) are types of
`oaap.core.notifications`, routed through lists, sent by the platform of
the hub (or the entry), with the weekly report (RFC-0083) as an option.
Each node keeps sending its own alerts by mail as today; it **also**
publishes them as class `events`, so the hub sees the whole fleet's alerts
in one place. A node's alert is never sent twice by mail: the hub shows
node events, it does not re-mail them unless a list at the hub says so.

## 7. Service providers and profiles

### 7.1 A profile

| Field | Example |
|---|---|
| name | `hardware` |
| classes | `alive`, `metrics`, `hw` |
| nodes | all / by tag (`tag:werk`) / a list |

Suggested starting set: `hardware` (alive, metrics, hw), `security`
(alive, security, events), `betrieb` (alive, metrics, status, events,
backup), `voll` (all). Profiles live at the hub, edited by its
server_admin.

MQTT filters cannot express tags. A profile is therefore **expanded** into
one filter per node and class (`oaap-node/n1/metrics/#`, …), and expanded
again when a node is paired, unpaired or its tags change. That requires
**changing a key's grants after issue** — today not possible (fact 2). This
RFC asks for that change to RFC-0054, for the keys that belong to a
provider subscription only, made by the hub's platform, audited (D8).

### 7.2 A subscription

The owner (the hub's server_admin) gives a provider a **subscription**:
one profile, one way of delivery, a start and optionally an end.

- **Into a provider tenant on the hub.** The provider gets a tenant on the
  hub (`ops-<provider>`); the fleet service writes the profile's data into
  that tenant's twin (§9). The provider's people log into their tenant
  with ordinary tenant roles; they see their twin and their fleet app,
  nothing of `oaap-ops`.
- **Into the provider's own tools.** The hub issues an operator key with
  the profile's read grants. The provider connects a dashboard, Grafana,
  or a bridge from their own broker (outbound from them). This is also the
  way for **any external dashboard** of the owner's.

### 7.3 Ending, auditing, personal data

- Ending a subscription revokes its key or stops writing into the tenant,
  **at once** (RFC-0021 outlook, point 3). The provider tenant keeps what
  it received; deleting it is a separate, confirmed step.
- The hub keeps a ledger per subscription: profile, nodes, delivery, who
  started, changed and ended it, when. The owner sees it in the portal
  (RFC-0021 outlook, point 5).
- A profile containing a class marked "personal data possible" (§3) shows
  that in the portal when it is given to a provider, with the sentence that
  passing personal data to a service provider needs a data-processing
  agreement. The platform does not check agreements; it says when one is
  needed.

### 7.4 Several providers

Several subscriptions coexist, also two providers with the same profile
during a change of provider (RFC-0021 outlook, point 4). Nothing about a
provider is ever configured on a node.

## 8. Where the logic runs

The receiving, the watching, the alerts and the provider deliveries need
platform rights — issuing keys, RFC-0080, writing into several tenants'
twins. They run in a **platform service on the hub**, `fleet`, started by
a new node profile **`fleet-hub`** (requires `broker` and `store`). The
fleet app in a tenant is the **face**: it reads its tenant's twin (and
later its time series) and shows lists, the picture, alerts and statistics.
It holds no key and talks to no broker. Pairing pages are portal pages of
the platform, not of the app, because they issue keys (§4).

## 9. A twin per node

In the twin of `oaap-ops`, the fleet service maintains:

| Type | Object | Created when |
|---|---|---|
| `oaap.fleet.node` | one per paired node | first `alive` or `status` |
| `oaap.fleet.broker` | the hub and each entry | pairing of the entry |
| `oaap.fleet.instance` | one per instance in a node's `status` | appears in `status` |

Groups, by origin (RFC-0031: each statement in the group of its source):

- `status` — from the status document (version, alias, place, tags,
  attention markers), written by the fleet service;
- `liveness` — last seen, interval, silent spans, pairing state;
- `latest` — the last value of each metric series;
- `owner` — **written by people, never by the fleet service**: location,
  hardware, purchase date, warranty, notes.

Relations (with validity, fact 9): node *reports through* broker; entry
*is bridged to* hub; instance *runs on* node; node *is in place* — from
`place` (RFC-0082). The **infrastructure picture** is the twin's relation
query from the hub object, drawn by the fleet app: tags and places become
groups, brokers and bridges become edges, a silent node or a broken bridge
gets its colour from `liveness`.

**Provider twins** carry the same types, but only the groups and objects
their profile covers; a provider may add its own groups (origin =
provider), for example a maintenance contract. The owner's groups never
appear there.

## 10. FleetView

FleetView becomes the fleet app of §8: same name, new major version,
installed in `oaap-ops` (and in each provider tenant). It reads the twin;
it has no environment variables for nodes or keys. The present 0.3.5 stays
until the new one shows all five nodes; then it is removed from
oaap-demo's `default` tenant.

## 11. Decisions asked of Jörg

1. **One hub; nodes pair once with it; providers only through the hub**
   (§2, §7)? Recommended: yes. Alternative: providers pair with nodes
   directly — contradicts RFC-0021's outlook (node keys spread, revocation
   per node).
2. **Keep the root `oaap-node`, classes as the first level below the node**
   (§3)? Recommended: yes.
3. **The status document travels as class `status`; the hub stops polling**
   (§4.6)? Recommended: yes — external nodes need no inbound reachability.
4. **Pairing by a one-time code (15 min) signed with a secret shared
   between hub and entry, entries paired once with the same steps** (§4)?
   Recommended: yes. Alternative: public-key signatures (needs a library on
   every node).
5. **Default classes `alive`, `metrics`, `status`, `events`;** `security`,
   `hw`, `backup` reserved now and filled by later RFCs (§3)? Recommended:
   yes.
6. **The bridge is opened by the hub; the entry keeps 24 hours** (§5)?
   Recommended: yes.
7. **Liveness by expectation, no Last Will; alert after 5 minutes; each
   entry watches its hub** (§6)? Recommended: yes.
8. **Profiles expanded into per-node grants, and provider keys whose grants
   the hub's platform may change** — an amendment to RFC-0054 (§7.1)?
   Recommended: yes.
9. **Providers receive into a tenant on the hub or with a read key; never a
   role on a node** (§7.2)? Recommended: yes.
10. **A platform service `fleet` on a profile `fleet-hub`; the app is the
    face** (§8)? Recommended: yes. Alternative: everything inside the app —
    an app would then issue keys and send platform alerts.
11. **oaap-demo gets `store` and becomes the hub; oaapx01 gets `broker`
    and becomes the first entry** (stage 1)? Recommended: yes.

## 12. Stages and what is measured

Each stage is built and measured on oaap-test first (as hub stand-in or as
entry, together with oaap-demo), then rolled out on Jörg's word.

1. **The chain by hand, with what exists.** `store` on oaap-demo, `broker`
   on oaapx01; the bridge configured by hand; node keys issued with
   `oaap key issue --kind node`; senders on all five nodes (internal to
   oaap-demo, external to oaapx01). **Measured:** F1–F3; metrics of all
   five arriving at oaap-demo; the bridge cut for an hour with the backlog
   caught up and counted; oaap-demo rebooted with nothing lost.
2. **The new classes and the watch.** `alive`, `status`, `events` from the
   node; the `fleet` service with `node.silent`/`back`, `bridge.down`/
   `back`, `broker.queue`, `hub.unreachable` at the entry. **Measured:** a
   node switched off is reported after 5 minutes and back after power-on;
   the bridge cut is one alert, not five; oaap-demo stopped → mail from
   oaapx01.
3. **Pairing in the portal.** Hub, entry, node; unpairing from both sides;
   the five nodes of stage 1 re-paired by code. **Measured:** a pairing
   without typing a key; an expired, a reused and a forged code refused; a
   node removed at the hub refused at its next run.
4. **Twins and the face.** Types, groups and relations in `oaap-ops`;
   FleetView's new version; the picture. **Measured:** five node objects
   with relations; a silent node coloured in the picture; FleetView 0.3.5
   removed.
5. **Statistics** on RFC-0086's default store.
6. **Providers.** Profiles, subscriptions, the RFC-0054 amendment, a test
   provider tenant on the hub and a read key into an external dashboard.
   **Measured:** a provider sees exactly its profile; a tag change widens
   and narrows its grants; ending a subscription cuts it at once.

## 13. Out of scope

Acting on nodes from the hub or by a provider (RFC-0021 stage 2); the
content of `security`, `hw` and `backup` (own RFCs); time series storage
(RFC-0086); payload traces; more than one hub; checking data-processing
agreements.

## Decision record (2026-11-12)

Jörg, in chat: "wie empfohlen, rollout später". All eleven decisions of
§11 follow the recommendation:

- **D1** one hub, nodes pair once, providers only through the hub;
- **D2** root `oaap-node`, classes as the first level;
- **D3** status as class `status`, the hub stops polling;
- **D4** one-time code, 15 minutes, HMAC with a secret per entry; entries
  paired with the same steps;
- **D5** default classes `alive`, `metrics`, `status`, `events`;
  `security`, `hw`, `backup` reserved;
- **D6** bridge opened by the hub, the entry keeps 24 hours;
- **D7** liveness by expectation, alert after 5 minutes, each entry
  watches its hub;
- **D8** profiles expanded into per-node grants; provider keys whose
  grants the hub's platform may change (amendment to RFC-0054);
- **D9** providers receive into a tenant on the hub or by read key, never
  a role on a node;
- **D10** platform service `fleet` on profile `fleet-hub`, the app is the
  face;
- **D11** oaap-demo gets `store` and becomes the hub, oaapx01 gets
  `broker` and becomes the first entry.

"Rollout später": stages are built and measured on oaap-test; changes on
oaap-demo and oaapx01 (profiles, bridge, senders) and the fleet roll-out
of reference 0.1.265 wait for Jörg's word.

## Deutsche Zusammenfassung

**Worum es geht.** Die Bausteine für die Flottenüberwachung liegen fast
alle schon da und sind gemessen: Jeder Knoten misst, speichert und reiht
seine Messwerte in eine Warteschlange (RFC-0051); der Sender schickt sie
per MQTT an einen Broker und löscht nur, was der Broker bestätigt hat
(RFC-0052); der Broker bindet Knotenschlüssel an einen Knotennamen
(RFC-0054). **Es fehlt die Mitte**: Niemand empfängt, niemand wacht,
nichts ist eingerichtet — und das Einrichten von FleetView verlangt
abgetippte Schlüssel in Umgebungsvariablen.

**Der Vorschlag in sechs Sätzen.**
1. **Eine Zentrale:** Jeder Knoten koppelt sich *einmal* mit oaap-demo
   (Mandant `oaap-ops`). Externe Knoten senden an einen **Eingang**
   (oaapx01); oaap-demo baut die Brücke dorthin *von innen nach außen* auf,
   das Heimnetz öffnet keinen Port.
2. **Koppeln per Code im Portal:** Die Zentrale zeigt einen Einmal-Code
   (15 Minuten), das Portal des Knotens nimmt ihn, zeigt *was* den Knoten
   verlässt, und fragt nach Bestätigung. Schlüssel tauschen die Plattformen
   untereinander, niemand sieht sie.
3. **Der Knoten entscheidet, was er hergibt; die Zentrale entscheidet, wer
   es sieht.** Keiner kann die Entscheidung des anderen erweitern.
4. **Lebenszeichen als Erwartung:** Meldet sich ein Knoten 5 Minuten nicht,
   alarmiert die Zentrale über den Verteiler (RFC-0080). Zentrale und
   Eingang bewachen sich gegenseitig — fällt oaap-demo aus, mailt oaapx01.
5. **Dienstleister bekommen Datenprofile, nie Zugriff auf Knoten:** Ein
   Profil ist eine Auswahl von Datenklassen und Knoten (z. B. per Tag); der
   Broker setzt es durch. Ein Dienstleister bekommt einen eigenen Mandanten
   auf oaap-demo mit eigenem Zwilling — oder einen Leseschlüssel für seine
   eigenen Werkzeuge (das ist auch der Weg für externe Dashboards).
6. **Jeder Knoten bekommt einen Zwilling** in `oaap-ops`; die Topics legen
   die Objekte an, der Zwilling hält die Beziehungen, daraus wird die
   Infrastruktur-Grafik gezeichnet.

**Ein Befund, der meinen Chat-Vorschlag korrigiert:** Der Sender hält keine
Verbindung, er verbindet sich jede Minute neu und trennt wieder, ohne
„Last Will". Ein Last Will kann einen toten Knoten also nicht von einem
fertigen Lauf unterscheiden. Darum: Lebenszeichen als Erwartung („alle 60 s
ein `alive`"), nicht über MQTT-Mechanik.

**Datenklassen** unter `oaap-node/<knoten>/`: `alive`, `metrics` (gibt es
schon), `status` (das bisherige `/fleet/status`-Dokument, jetzt per Broker —
die Zentrale muss die Knoten nicht mehr abfragen), `events` (die Meldungen
des Knotens; **kann personenbezogen sein**), reserviert `security`, `hw`,
`backup`. Ein Profil ist schlicht eine Liste solcher Klassen.

**Ausfallsicherheit:** drei Puffer hintereinander — Knoten (7 Tage),
Eingang (24 Stunden), Empfangsdienst der Zentrale (dauerhafte Sitzung).
Jeder Verlust wird dort gezählt, wo er passiert. Eine Brücke ist ein
Broker, der sich bei einem anderen Broker als Client anmeldet und
ausgewählte Topics weiterreicht — vergleichbar mit einer qRFC-Queue
zwischen zwei SAP-Systemen.

**Wo die Logik läuft:** Empfang, Wache, Alarme und Belieferung der
Dienstleister brauchen Plattformrechte und laufen darum als
Plattformdienst `fleet` auf einem neuen Knotenprofil `fleet-hub`. FleetView
wird das Gesicht davon: liest nur den Zwilling, keine Schlüssel, keine
Umgebungsvariablen.

**Drei offene Fakten werden in Stufe 1 zuerst gemessen:** (F1) ob der
Broker der Zentrale über die Brücke ankommende Werte mit seiner Rechteprüfung
abweist, (F2) wie der Eingang die Warteschlange einer abwesenden Brücke hält
und zählt, (F3) wie groß ein echtes Statusdokument ist.

**Elf Entscheidungen (§11), am 12.11. von Jörg alle wie empfohlen angenommen** ("wie empfohlen, rollout später"); die wichtigsten: eine
Zentrale statt direkter Dienstleister-Kopplung (D1), Status per Broker
statt Abfrage (D3), Koppeln per signiertem Einmal-Code (D4), Lebenszeichen
als Erwartung (D7), Profilschlüssel mit änderbaren Rechten als Nachtrag zu
RFC-0054 (D8), Plattformdienst statt Logik in der App (D10), oaap-demo
bekommt `store`, oaapx01 bekommt `broker` (D11).

**Stufen:** (1) die Kette von Hand mit dem, was es gibt, gemessen inkl.
Brückenausfall und Neustart; (2) neue Klassen und Wache mit Alarmen;
(3) Koppeln im Portal; (4) Zwillinge und neues FleetView mit Grafik;
(5) Statistik auf Basis von RFC-0086; (6) Dienstleister und Profile.

**Schon erledigt (12.11.):** Mandant `oaap-ops` auf oaap-demo angelegt
(leer). Dabei gefunden: `oaap tenant create` übergeht `--dry-run`
stillschweigend und legt wirklich an — Fehler im CLI, wird behoben.
