# RFC-0087: Half-Edges — Each Node Reports What It Knows of Its Links, the Hub Joins Them

- **Status:** **Accepted (2026-11-14)** — D1–D5 as recommended; D4
  amended by Jörg: an external end carries a link, so that data can grow
  together with partners (§5.1, decision record). **Stage 1 built
  (reference 0.1.281, §10): node side measured live on oaap-test, hub side
  against PostgreSQL; joined live at the hub 2026-11-14 (0.1.282, twin
  oaap-ops, the real tunnel oaapx01 ↔ oaap-demo). Portal page "Flotte" for the levels built 2026-11-15 (reference 0.1.284,
  measured live on oaap-test). **Stage 2 built 2026-11-15 (reference
  0.1.285, §6 amendment): `affected()`, the read, one hub matter
  `link.down` per tunnel; measured against PostgreSQL and read-only on the
  real hub twin; **the mail measured live 2026-11-15 on oaap-demo**
  (loop tunnel of oaap-test cut off its network: `link.down` after
  5 minutes with the affected destination, *Behoben* after reconnecting);
  **Stage 3a built 2026-11-15 (reference 0.1.288, vpn-client 0.2.0,
  §8.1): a tunnel app says how its tunnel and its targets are; measured
  live on oaap-test at the node, the hub side against PostgreSQL; the hub
  live waits for oaap-demo on 0.1.288.** Stage 3b (the AI gateway's
  relations) not built**
- **Date:** 2026-11-14
- **Authors:** Jörg (the need, I-51: "nodes share configuration, relations
  and events so that support can be automated in real time"; "the tunnel
  oaapi01 → oaapx01 is connected automatically and learns of failures";
  "tenants and instances too, if the tenant_admin allows it"), Claude
  (facts read in reference 0.1.280, design)
- **Depends on:** RFC-0085 (fleet transport, amendment A2: the twin per
  node), `oaap.fleet.status` 0.9 (the document that carries the halves),
  `oaap.net.connector` 0.4 (tunnels, connect keys), `oaap.net.destinations`
  0.12 (`via`, `through`), RFC-0060 (tunnel apps), `oaap.data.twin` 0.5
  (objects, relations with validity, one write rule), RFC-0086 (text
  series), `program/aas-zuordnung-knotendaten.md` (semantic IDs)
- **Not part of this RFC:** the drawing (FleetView, RFC-0085 stage 4–5);
  relations declared by apps (the AI gateway's model → source →
  destination; a later stage, §8); methods on assets (I-51 (b), its own
  RFC); OpenTelemetry (`traceparent`, an OTLP exit); new alerts (alerts
  stay RFC-0080).

## Summary

The fleet twin (RFC-0085 A2) knows nodes, their instances and the brokers
they report through. It does not know the links **between** nodes and
behind them: the AI gateway chain of 13.11. — an app on oaapx01 → a `via`
destination → the tunnel → the connector on oaapi01 → an offer → the
gateway there → a `through` destination → the VPN app → the gaming PC —
was understood only by looking at two consoles.

No node knows such a chain whole. **Each side knows its half**: the outer
node knows a tunnel, its tenant and the destinations that use it; the inner
node knows its connector and which of its instances an offer reaches. This
RFC lets every node report its halves in the status document it already
sends, and lets the hub join them in the twin. The join needs one shared,
non-secret identifier per tunnel. **Both sides can derive it from what they
already hold** — the outer node keeps the SHA-256 hash of the connect key,
the inner node the key — so nothing new crosses the tunnel and no key has
to be reissued.

What the hub then has is a graph with state on its edges: a tunnel whose
inner side is paused, a VPN app whose tunnel is down, and from there the
destinations and instances that depend on it — **affected parties instead
of a flood of alerts**.

## 1. Facts (read 2026-11-14, reference 0.1.280)

1. The outer node stores a connect key as `sha256(key)` in hex, with label
   and tenant (`appctl.py` key issue; `connect/app.py` compares the hash).
   The inner node keeps the key in a directory only the connector service
   mounts (`oaap.net.connector` 2.3).
2. The tunnel `hello` carries the connector label and offer names and
   kinds, never addresses (2.4). The outer side knows *a* connector label,
   but not which node it runs on.
3. A key belongs to exactly one tenant (2.2). A `via` destination names
   `<tunnel>/<offer>`; a `through` destination names `<instance>/<name>` of
   a tunnel app of its own tenant (`oaap.net.destinations` 2.8).
4. Both sides already write their state: per tunnel (outer) connected,
   since, offers; per connector (inner) connected, paused, last error
   (2.7). The status document carries `connector_down` and `tunnel_down`
   as attention kinds, nothing more.
5. Instance rows in the status document carry no tenant (`oaap.fleet.status`
   §3). The class `status` is marked "business data possible" (RFC-0085
   §3).
6. The fleet sink writes objects by source key, groups by origin, relations
   with dedup on validity (`twin_write.py`, `fleet_sink.py`); the status is
   published on change and at least hourly.

## 2. A half-edge

A half-edge is **one link as one side sees it**: what it is, which local
thing it starts at, a key by which the other half can be found, and the
state this side sees. (Names in the examples follow the chain of 13.11.;
`ais-chat`, the consuming app on oaapx01, stands for any app.)

```json
"links": [
  {"kind": "tunnel", "side": "outer", "id": "t-9f2c4e1a07b3d5e6c8a1f0b2",
   "label": "oaapi01", "tenant": "ais", "state": "ok", "since": "2026-11-14T18:02:11Z",
   "offers": ["mg"]},
  {"kind": "destination", "tenant": "ais", "name": "ais-oaapi01",
   "via": {"tunnel": "t-9f2c4e1a07b3d5e6c8a1f0b2", "offer": "mg"},
   "bound": ["ais-chat"]}
]
```

and on the inner node:

```json
"links": [
  {"kind": "tunnel", "side": "inner", "id": "t-9f2c4e1a07b3d5e6c8a1f0b2",
   "label": "oaapx01", "tenant": "ais", "state": "ok", "paused": false,
   "offers": [{"name": "mg", "reaches": "ais-mg"}]},
  {"kind": "destination", "tenant": "ais", "name": "gamingpc",
   "through": {"instance": "ais-ovc", "target": "gamingpc"},
   "bound": ["ais-mg"]}
]
```

Rules:

1. **Whitelist, facts only** (`oaap.fleet.status` rule 1). Never an
   endpoint URL, an offer's target address, a path prefix, a credential, a
   VPN server. `reaches` is the name of **an own instance** when the
   offer's target resolves to one; otherwise the word `external` — the
   address itself stays on the node.
2. **One row per link the node itself holds**: every connect key it issued
   (outer), every connector it runs (inner), every destination of kind
   `via` or `through`. `direct` destinations are left out in stage 1: their
   far end is outside the fleet and their address is configuration.
3. `state` uses the one vocabulary (`ok | warn | error | unknown`); `paused`
   (inner) is a separate fact, because a paused connector is *not running
   by choice* — like an instance in `standby`, never an alarm.
4. A tunnel app's own tunnel state ("the VPN is down") is known only to the
   app (2.8: "it knows; the platform does not"). Stage 1 reports
   `through` rows without it; stage 3 (§8) lets a tunnel app declare it.

## 3. The join key for a tunnel (D1)

```text
id = "t-" + hex( sha256( "oaap-tunnel-id/1\n" + sha256hex(key) ) )[0:24]
```

- The **outer** node holds `sha256hex(key)` and computes `id` from it; the
  **inner** node holds `key`, computes `sha256hex(key)` and then `id`.
  Nothing is exchanged, nothing is stored in addition, every key issued
  so far works.
- The id is **not secret** and is no verifier: it is a hash of the stored
  hash under a fixed prefix, so it neither lets anyone present a key nor
  equals what the outer node compares against. 96 bits are enough to make
  a collision between two tunnels of one fleet negligible.
- A reissued key is a new tunnel with a new id — which is what it is: the
  old one is revoked. Labels stay what they are on each side (the outer
  label names the tunnel on that node, the inner label the connector);
  the twin shows both.

`via` destinations name the tunnel by its outer label; the outer node
replaces it with the id in its row, so the destination half joins the
tunnel object without the hub knowing labels.

## 4. Tenants, and how much a node gives away (D2)

The links belong to tenants (a key has exactly one, fact 3). A tenant is
an asset of its node (I-51); the status document gains a `tenants` block
and the instance row a `tenant` field — **within what the node allows**:

| Level | What leaves the node | Example in the twin |
|---|---|---|
| `count` | the number of tenants only; links and instances carry no tenant | "oaapi01 has 4 tenants" |
| `pseudonym` | a stable pseudonym per tenant (`m-` + 10 hex of an HMAC with a secret of the node) | tenant `m-3be07c1d9a`, its tunnels and destinations |
| `names` | the tenant's name | tenant `ais`, its tunnels and destinations |

- The **server_admin** of the node sets the ceiling
  (`oaap fleet disclose <level>`, portal page "Flotte"). Default: `pseudonym`.
- The **tenant_admin** chooses for their own tenant at or below the
  ceiling (portal, tenant settings). Default: the ceiling. A tenant on
  `count` makes its links leave the node without tenant and without
  destination names (`name` becomes a pseudonym, `bound` a count).
- The **hub** decides who receives what (RFC-0085 §7 profiles); links are
  part of the class `status`, which is already marked business data.
  Nothing about a receiver is configured on the node (RFC-0085 §7.4).
- Instance **names** leave the node today and stay as they are; this RFC
  does not hide them (they often carry the tenant in their name — the
  portal page says so beside the level). Hiding instance names is a
  separate decision.

Every change of a level is written to the audit log of the node (server
level) and of the tenant (tenant level).

## 5. In the twin

New object types, relation types and groups in `fleet_model.py`, with the
naming of A2 (short names, `fleet` prefix, own semantic IDs under
`oaap-aas:`):

| Object | Source key | Groups (origin `platform:fleet`) |
|---|---|---|
| `oaap.fleet.tenant` | `<node>/<tenant or pseudonym>` | `oaap.tenant`: level, instance count |
| `oaap.fleet.tunnel` | `tunnel:<id>` | `oaap.tunnel.outer`: outer label, state, since, offers · `oaap.tunnel.inner`: connector label, state, paused, last error |
| `oaap.fleet.destination` | `<node>/<tenant>/<name>` | `oaap.destination`: kind, offer or target name, bound count |
| `oaap.fleet.external` | `<node>/<instance>/<target>` | `oaap.external`: kind (`vpn`, `offer`) · `owner.link` (people, §5.1) |

| Relation | From → to | Meaning |
|---|---|---|
| `isPartOf` (IDTA HierarchicalStructures) | tenant → node | the node holds the tenant |
| `heldBy` | instance → tenant | the instance belongs to the tenant (only at `pseudonym`/`names`) |
| `servedBy` | tunnel → node | the outer end |
| `dialedBy` | tunnel → node | the inner end |
| `uses` | destination → tunnel, destination → external | the way out |
| `reaches` | tunnel → instance | an offer ends at this instance |
| `bindsTo` | instance → destination | the instance calls through it |

- **The tunnel object is joined, not copied**: each half writes its own
  group to the same object (`tunnel:<id>`); whichever half arrives first
  creates it. Each group is written only from the status of the node that
  holds that half — the write rule of A2 holds unchanged.
- **A half without its partner stays visible**: a tunnel with only an outer
  group is "nobody dials" (or the inner node is outside the fleet); one
  with only an inner group dials a node outside the fleet. Both are facts,
  not errors.
- **Relations end with validity**, as in A2: a destination that disappears
  from a node's status closes its relations; history stays.
- A text series `state` (RFC-0086) on each tunnel object carries the joined
  state over time: `ok`, `paused`, `down-outer`, `down-inner`, `half`. "When
  was the tunnel down last week" is then a range query.

### 5.1 The edge of our universe, and a link across it (D4 as amended)

An external end is where what the fleet knows stops: a VPN server, a PC
behind it, an address an offer reaches outside the node. Jörg (2026-11-14):
*"External names are the end of our universe. But with a simple link the
data can grow together when the need is there, when we get more context,
or when we work with external data partners — the aim was to provide data
outward and to consume external data. A basic concept of the asset
administration shell and of data spaces."*

So every `oaap.fleet.external` object carries a place for that link, and
the twin already has the act that joins:

- **A group `owner.link`, written by people, never by the fleet service**
  (like `owner.contact`): `externalId` — the far end's identifier in
  someone else's world (an AAS `globalAssetId` or `specificAssetId`, an
  IRI, an IRDI; checked with the same rule as semantic IDs,
  `semantic.valid()`), `externalSource` — whose world (a partner, a data
  space, a tenant of another fleet), and `notes`. Empty by default; a
  half-edge never fills it, because a node does not know what the far end
  is called elsewhere.
- **Growing together is the twin's merge** (`oaap.data.twin` §2.9): when
  data about the same thing arrives from another origin — an import, a
  partner's shell, a second fleet — a `tenant_admin` merges the two
  objects; both ids keep answering, and unmerge splits them again. No
  new mechanism.
- **Candidates, not automation**: two objects of different origins with
  the same `externalId` are shown as a merge candidate; nothing is merged
  without a person (merge is a human act, `oaap.data.twin` §2.9).
- **Our own side of the link**: on export (a later stage), our objects get
  a `globalAssetId` formed like the semantic IDs — stored in a short form,
  expanded with a changeable base (`objid.info` today, RFC-0085 A2), so
  that a partner can link to us the same way.

## 6. Affected, not alarmed

Stage 2 adds one read to the twin service, **`affected(object)`**: from a
tunnel, an external end or an instance, follow `uses`, `bindsTo`,
`reaches` and `heldBy` backwards and list what depends on it — "VPN of
`ais-ovc` is down → destination `gamingpc` → `ais-mg` on oaapi01 → tunnel
`t-9f2c…` → destination `ais-oaapi01` → `ais-chat` on oaapx01, tenant
`ais`". FleetView draws it later; the fleet service puts the list into the
detail of the existing attention item (`tunnel_down`, `connector_down`)
when it opens a matter. No new alert kinds, no second mail.

**Amendment (2026-11-15, building stage 2 — for Jörg to confirm).** The
paragraph above assumed a matter is already opened for `tunnel_down` and
`connector_down`. None is: both are attention items in the status document
and FleetView shows them, but neither the node nor the hub mails them.
Stage 2 therefore opens the matter at the hub, which alone sees both
halves and the chain behind them: **one** matter type `link.down`
(`oaap.core.notifications` 0.8), one matter per tunnel object, opened when
its joined state has been `down-inner` or `down-outer` for five minutes,
whichever half reports it — the two attention kinds on the nodes stay as
they are and are not mailed one by one. So there is one new matter TYPE,
and still no second mail for one fault. Built (reference 0.1.285):

- `services/twin/fleet_affected.py` (pure walk + `load_graph`);
- the fleet service writes `/fleet/affected.json` on every flush (empty
  when nothing is down; the graph is read only when a tunnel is down);
- the host's minute job judges it (`fleet_watch.link_conditions`) — a
  report older than three minutes decides nothing, open matters stay;
- the read `GET /internal/twin/objects/{id}/affected` (`oaap.data.twin`
  0.6) for FleetView.

What stage 2 does NOT detect yet: "VPN off" as such. A VPN app whose own
tunnel is down but whose container stays healthy is invisible until
stage 3 (the app reports its tunnel state). With stage 2 the chain from
`ais-ovc` is already computed (measured read-only on the hub, below); it
becomes a mail once the instance or the tunnel is reported broken.

Measured: `test_fleet_affected.py` 29/29 (pure: the RFC's chain in order,
a cycle, limits, the matter's text); `test_fleet_twin.py` against
PostgreSQL on oaap-test (inner side broken → one entry with
`ais-oaapi01`, `ais-chat`, tenant `ais`; reconnected → gone; the RFC's
chain from `ais-ovc` out of the database). **Read-only on the real hub
twin `oaap-ops`** (oaap-demo, 74 relations, 102 objects): tunnel
`t-af21…` (outer oaapx01, inner oaap-demo) → destination on oaapx01 →
`ais-mg` on oaapx01; from `ais-ovc` on oaap-demo → its external end →
destination → `ais-mg` on oaap-demo → tunnel `t-af21…` → destination on
oaapx01 → `ais-mg` on oaapx01 — tenants as pseudonyms, because the
nodes give away `pseudonym` (§4).

**Live, 2026-11-15, hub oaap-demo on 0.1.285** (`link.down` routed to a
test list first): the connect service of oaap-test was taken off its
network at 09:05:20 while running — both halves of the loop tunnel
`t-1698…` lost their connection. The node's next status fetch (every
5 minutes) brought `down-inner` to the hub at 09:08:34; the matter opened
and the mail arrived at 09:14:15 naming the tunnel, both ends, the inner
side and the destination `d-d586…` with its tenant (pseudonyms). Network
back at 09:14:54, tunnel up at 09:15:24, *Behoben* at 09:20:16. Found on
the way: (a) the portal does not judge the age of the connect service's
state file, so a STOPPED connect service still reads as connected (the
measurement therefore cut the network instead); (b) the closing mail's
`Dauer` counts from the matter's opening while the quoted text says how
long the tunnel was down — both true, not yet in step. **(b) fixed,
reference 0.1.287 (`oaap.core.notifications` 0.9):** the fleet conditions
carry `began`, the matter keeps the earliest, and `Dauer` counts from it.

**(a) fixed, reference 0.1.286 (`oaap.net.connector` 0.6).** The connect
service rewrites its state at least every 30 s and names the beat; a
state older than four beats and two minutes is no state (nothing
connected) for portal, CLI and status document. The first live run of
this rule found its own gap: with no state the inner half lost its
`tunnel_id` — only state.json carries it — and dropped out of `links`;
the hub saw one half (`half`, no fault) and stayed silent. Now a stale
state keeps its names and loses only "connected". Measured on oaap-test,
hub oaap-demo, test list routed: connect **stopped** 09:29:27, status
document `connector_down` + `tunnel_down`, both halves `error` at 09:34;
hub `down-inner` since 09:34:31; mail 09:40:23; started 09:41:17,
*Behoben* 09:47:22. The page says "meldet seit … nichts mehr".

## 7. AAS

The relations become `RelationshipElement`s in a later export; the
semantic IDs are own ones (`oaap-aas:PeerRelations/0/2/…`,
`oaap-aas:FleetTenant/0/1`, …), `isPartOf` keeps the IDTA ID. The tenant
is the middle level of the hierarchy node → tenant → instance of
HierarchicalStructures 02011, as the mapping table says. The instance keeps
`isPartOf node` (where it runs); `heldBy tenant` is the ownership.

## 8. Stages and what is measured

| Stage | Content | Measured by |
|---|---|---|
| 1 | `links` and `tenants` in the status document (`oaap.fleet.status` 0.10), the derived tunnel id on both sides, the levels with their defaults and audit, the sink joins halves (§5) | oaap-test as outer **and** inner node (a test list routed first); then the real chain oaapx01 ↔ oaapi01 on Jörg's word: both halves on one tunnel object, connector paused → `paused` without an alert, a key revoked → relations closed, a tenant set to `count` → no name at the hub |
| 2 | `affected()` and the list in the attention detail; the text series per tunnel | the chain with the VPN switched off: the list names `gamingpc`, `ais-mg`, the tunnel, `ais-oaapi01`, `ais-chat` |
| 3 | a declared door for apps (I-41): a tunnel app reports its own tunnel state, the AI gateway reports model name → source → destination (names and kinds only) | the gaming PC unreachable → the external end turns red |

### 8.1 Stage 3a — a tunnel app says how its tunnel and its targets are (2026-11-15)

Stage 3 has two halves that share nothing but the idea of a declared
door. **3a**, built first, is the tunnel app's own state — the missing
piece for "VPN off". **3b**, the AI gateway's model → source →
destination, is a different shape (relations an app declares, not a
state) and follows with its own measurement.

Facts (read 2026-11-15, reference 0.1.287, vpn-client 0.1.5):

1. vpn-client's `/healthz` answers 200 only while its tunnel stands, so
   the node's probe already turns the *instance row* red when the VPN is
   down. But the row says "the app is unwell", not "the tunnel is down",
   and the hub opens no matter for an instance row; nothing reaches the
   external end.
2. A target behind a standing tunnel (the gaming PC switched off) is
   invisible: the tunnel is up, `/healthz` is 200.
3. The node reaches an app's health path through the gateway's internal
   endpoint `gateway:8099/h/<name>`, which answers the platform network
   only (RFC-0016).

The door (manifest 0.14, `oaap.apps.runtime` 2.33):

```yaml
link_state:
  path: /oaap/links
```

- A local path under one of the app's routes (the rule of `mcp:`). (Not
  `links:` — in the registry that word is already the list of partner
  instances, RFC-0016.) The
  platform records it and adds `gateway:8099/l/<name>` → that path to the
  internal endpoint, beside `/h/<name>`. Nothing else is opened.
- The answer, `{"v": 1, "tunnel": {"state": "ok"|"down"}, "targets":
  {"<name>": {"state": "ok"|"down"}}}`. The node reads exactly these
  fields; any other field, and any state outside the two words, is
  dropped (whitelist, rule 1). Names are the app's own target names —
  the ones a `through` destination names.
- **The node asks, the app does not push.** At each status document the
  portal asks every instance with the door (2 s), as it probes health.
  An instance in standby or maintenance is not asked: its targets are
  `paused` — someone's decision, never an alarm. No answer, a bad
  answer: `unknown`.

In the status document (`oaap.fleet.status` 0.11) a `through` row's
`through` gains `state`:

| state | meaning |
|---|---|
| `ok` | the app's tunnel stands and it reaches the target |
| `down-tunnel` | the app's own tunnel is down |
| `down-target` | the tunnel stands, the target does not answer |
| `paused` | the tunnel app sleeps or is in maintenance |
| `unknown` | the app did not answer its door |

A row without `state` (an app without the door, a node before 0.11)
stays as in stage 1: the external end is `present`.

At the hub:

- the external end's `extState` carries that word (`present` without
  it), and its text series `state` follows minute by minute like a
  tunnel's;
- `down-tunnel` and `down-target` are **down**: the report
  (`affected.json`) lists the external end with what depends on it, and
  after five minutes the same matter type `link.down` opens for it — one
  matter per external end, named `<node>/<instance>/<target>` (the
  target as the node gives it away, §4). `unknown` decides nothing and
  keeps an open matter open, as for tunnels;
- the matter's subject says *Verbindung* instead of *Tunnel*, since an
  unreachable PC behind a standing VPN is no tunnel.

The app (vpn-client 0.2.0): it checks each target with a TCP connect
every 30 s while its tunnel stands (5 s timeout) and answers the door;
the state page shows the same.

Measured by: the RFC's line for stage 3 — the gaming PC unreachable → the
external end turns red, and its matter names what depends on it; plus the
tunnel itself switched off (`down-tunnel`), and standby (`paused`, no
mail).

**Built (reference 0.1.288, vpn-client 0.2.0).** `appctl`:
`link_state_door_error`/`link_state_door`, manifest minor 14, the registry
record, `/l/<name>` in the internal endpoint. Portal: `_link_reports`
(asks, 2 s; standby/maintenance → `paused`; no answer → `unknown`),
`fleet_links.read_link_answer`/`through_state`, status document 0.11.
Hub: `fleet_twin.EXT_STATES` → `extState`; `fleet_sink.ext` (the state
per external end, its text series, removed with the end or when the app
loses its door); `fleet_affected.link_report` names an external end
`<node>/<instance>/<target>` with `kind` and `behind`;
`fleet_watch.link_text` writes its own head line; `notify` subject
*Verbindung getrennt*. No change to `fleet_model` (`extState` was text
already).

**Measured.**

- Locally: `test_fleet_links` 61/61, `test_fleet_affected` 49/49,
  `test_link_state_door` 21/21 (new: manifest rule, registry key, the
  `/l/` line only for a door), vpn-client `test_vpn_client` (+6: real TCP
  target ok, closed port down, `since` kept, no address in the answer,
  tunnel down clears the targets). In the portal's image on oaap-test:
  `test_link_reports_portal` 10/10 (new), `test_connect_fresh` 20/20.
  Against PostgreSQL 16 on oaap-test: `test_fleet_twin` 83/83, 11 of them
  new — `ok` → group and series; `down-target` → one report entry
  `ni/ais-ovc/gamingpc`, kind external, behind `ais-ovc`, affected from
  the database (destination, `ais-mg`, the tunnel, `ais-oaapi01`,
  `ais-chat`), the host's `link.down` after five minutes; `down-tunnel`
  starts a new `since`; `paused` and `unknown` no entry; the app without
  its door → `present`, no longer tracked; the destination deleted →
  `removed`.
- **Live on oaap-test (0.1.288 staged)** against a stand-in far end
  (`oaap-lab/vpn-gegenstelle`: OpenVPN server with throwaway certificates,
  a fake gaming PC at 10.8.0.1:11434), vpn-client 0.2.0 installed as
  `fleetprobe-fxvpn` with `--confirm-tun`, destination `gamingpc` →
  `through:fxvpn/gamingpc`. Read at the real `/fleet/status` (throwaway
  fleet key, revoked afterwards): schema 0.11, the row says
  `"through": {"instance": "fleetprobe-fxvpn", "target": "x-b5e2…",
  "state": "ok"}` — tenant, destination and target as pseudonyms, no
  address. Gaming PC switched off → `down-target` after 21 s (the app's
  page: "antwortet nicht (ConnectionRefusedError)"), the instance row
  stays `ok`; on again → `ok` after 21 s; the far end stopped (VPN off)
  → `down-tunnel` after 63 s (keepalive 10/60), the instance row `warn`
  (its `/healthz` 503); started → `ok` after 42 s; standby → `paused`
  at once, instance `standby`; woken → `ok` after 31 s; the app's
  container stopped by hand → `unknown`. The internal endpoint answered
  `/l/aigw-test` (no door) with 404.

**Not yet measured:** the hub live — oaap-demo runs 0.1.287, which
writes `present` for every external end; with 0.1.288 there (Jörg's
word, test list routed first) the fake gaming PC switched off must open
`link.down` for `oaap-test/fleetprobe-fxvpn/x-b5e2…`. The real `ais-ovc`
on oaap-demo runs vpn-client 0.1.5 (no door).

## 9. Decisions (asked of Jörg, answered 2026-11-14: as recommended)

- **D1 — the join key.** Derived from the key hash on both sides (§3,
  nothing reissued) — *recommended* — or a new id issued with each key
  and sent in `hello` (every existing key reissued).
- **D2 — levels and defaults.** Three levels `count | pseudonym | names`;
  ceiling by the server_admin, default `pseudonym`; the tenant_admin at
  or below it — *recommended*. Alternative: default `count` (sparser, but
  then the hub sees no links of a tenant until someone acts).
- **D3 — the tunnel as an object of its own** (a relation that is itself a
  twin, as Jörg put it) — *recommended* — or only a relation node → node
  (no place for two halves, no series).
- **D4 — external ends.** One `external` object per node, instance and
  target, named only at level `names` — *recommended* — or leave the far
  end out entirely.
- **D5 — where the halves travel.** Inside the status document (class
  `status`, already business data) — *recommended* — or a class of their
  own `links` (a profile could then give a provider the nodes' health
  without their links; costs a new topic and sender path).

## 10. Stage 1 — built and measured (2026-11-14, reference 0.1.281)

**Built.**

- Node: `portal/fleet_links.py` (pure: tunnel id, levels, pseudonyms, the
  rows), wired into `/fleet/status` (`oaap.fleet.status` 0.10); the connect
  service writes `tunnel_id` into its state (`oaap.net.connector` 0.5);
  `oaap fleet disclose count|pseudonym|names|default [--tenant <t>]` and
  `show`, the file `apps/fleet-disclose.json` made with its salt on first use
  (also by the minutely status job), audited.
- Hub: `fleet_model` 0.2.0 (4 object types, 13 relation types, 6 groups
  incl. the people's `owner.link`), `fleet_twin` (pure mapping),
  `fleet_sink._write_links` (join, close with `valid_to`, `removed`, the
  joined state series).
- Names as built, beside the words of §5: the tenant's `isPartOf` is the
  key `fleetTenantOn` (with the IDTA IsPartOf semantic ID — relation keys
  are unique per node, `fleetIsPartOf` is instance → node); `uses` is split
  into `usesTunnel` and `usesExternal` (one target type per relation type);
  the destination also gets `definedOn` (node) and `destOf` (tenant); the
  external end `behind` (the tunnel app instance). Source keys carry a
  prefix per kind (`tenant:`, `dest:`, `ext:`, `tunnel:`), so the instance
  sweep `<node>/%` can never take one of them for an instance.

**Measured.**

- `test/test_fleet_links.py` 34/34 locally (pure, and `fleet disclose`
  against a scratch data dir). Among them: the connect service's copy of
  the id rule equals the portal's (read from its source); an offer to an
  own instance's automatic address names the instance; a `last_error` that
  names the endpoint does not leave the node.
- `test/test_fleet_twin.py` 63/63 on oaap-test against a throwaway
  PostgreSQL 16 (`/tmp/tsrun.sh`): two nodes report the two halves of one
  tunnel → **one** tunnel object with both groups; the whole chain as
  relations (app → destination → tunnel → gateway → destination → VPN →
  external end, tenants, bindings); the same two documents again write no
  row; connector paused → joined state `paused`; key revoked → `servedBy`
  and `usesTunnel` closed with `valid_to`, outer half `removed`, joined
  state `half`; tenant lowered to `count` → `tenantOn` and `heldBy` closed;
  the same node back on 0.9 → its links untouched.
- **Live on oaap-test (0.1.281 staged):** a tunnel `h87` (tenant
  `fleetprobe`) from oaap-test to itself, offers `mg` →
  `https://aigw-test.<node>` and `nas` → a LAN address, a `via` destination.
  The status document carries both halves with **the same id**
  `t-169846ca2de0574b382f78fd` — the outer from the portal's hash, the
  inner from the connect service's key, two code paths; `mg` reaches
  `aigw-test`, `nas` is `external`; neither address, nor key, nor path in
  `links`. Default `pseudonym` active (12 tenants as `m-…`); ceiling
  `names` + `default` at `count` → names for `fleetprobe`, the 24 instance
  rows of `default` without tenant; every tenant change in that tenant's
  log. Reset to the default afterwards; the tunnel stays for the hub
  measurement.

**Open in stage 1.** ~~The portal pages for the levels~~ — built
2026-11-15 as one page "Flotte" (reference 0.1.284) for both roles, after
the page "Abfluss": the server_admin sets the ceiling and every tenant's
level, a tenant_admin sees and sets their own tenant only (no row, no count
of any other). It reads the settings file and writes through the spool;
the host derives role and tenant from the actor's record and calls the
same function as `oaap fleet disclose`, so a tenant above the ceiling is
refused there too. Every change is audited with person and role. Measured
live on oaap-test, 24 checks: both roles through the real gateway, the
settings file read after each act, a forged `tenant` field from a
tenant_admin hits their own tenant, a foreign origin is refused.
The live join at the hub: oaap-demo runs 0.1.279, which ignores `links`;
after its update the loop tunnel of oaap-test shows the join, the real
chain oaapx01 ↔ oaapi01 needs 0.1.281 on oaapx01 (Jörg's word).

**Live at the hub after the rollout (2026-11-14 evening, all five nodes on
0.1.281, oaapx01 on Jörg's word).** Within minutes, in `oaap-ops`: 2 tunnels,
each ONE object with both halves -- oaap-test's loop tunnel, and **the real
chain**: `t-af21…` served by oaapx01, dialed by oaap-demo, reaching `ais-mg`
there; a destination on oaapx01 uses it and `ais-mg` on oaapx01 is bound to
it; on oaap-demo `ais-mg` is bound to the `through` destination to the
external end. The joined state went `half` → `ok` as the second half
arrived. 30 tenants (pseudonyms), 3 destinations, 1 external end. **One
gap found:** the external end had no `behind` -- a `through` target names
the tunnel app by its name inside the tenant (`ovc`), every other row uses
the registry key (`ais-ovc`); fixed in 0.1.282 (the test had used one name
for both).

**Found on the way (not changed).** `fleet_view.auto_verdict` names an
instance's automatic address `<registry key>.<node>`; for an instance of a
non-default tenant the gateway's name is `<name>.<label>.<node>`
(`instance_view.auto_host`, `oaap.core.tenant` 2.4) — the document has
carried a name that answers nowhere for such instances since 0.3.

## Decision record (2026-11-14)

Jörg: "Alles wie empfohlen" — D1, D2, D3, D5 as recommended. **D4 as
recommended and amended:** external ends are the edge of our universe,
but they carry a simple link so that the data can grow together — with
more context, with external data partners, outward and inward, as in the
AAS and in data spaces. Written into §5.1: a people-written group
`owner.link` with an external identifier, merge candidates on equal
identifiers, joining by the twin's existing merge.

## Deutsche Zusammenfassung

**Worum es geht.** Die Kette vom 13.11. (App auf oaapx01 → Destination →
Tunnel → Connector auf oaapi01 → KI-Gateway → VPN-App → Gaming-PC) kennt
kein Knoten ganz. Jeder kennt seine Hälfte. Mit diesem RFC meldet jeder
Knoten seine Hälften im Statusdokument, das er ohnehin schickt, und die
Zentrale fügt sie im Zwilling zusammen. Dafür braucht es je Tunnel eine
gemeinsame, nicht geheime Kennung.

**Die Kennung ohne Austausch (D1).** Der äußere Knoten speichert vom
Schlüssel nur den SHA-256-Hash, der innere hat den Schlüssel selbst.
Beide rechnen daraus dieselbe Tunnel-ID aus: einen Hash des Hashes mit
festem Präfix, gekürzt auf 24 Zeichen. Dabei geht nichts durch den Tunnel,
und alle bisherigen Schlüssel funktionieren weiter. Die ID verrät nichts
und taugt nicht als Schlüssel.

**Was ein Knoten preisgibt (D2), drei Stufen:**

- *Anzahl*: „oaapi01 hat 4 Mandanten“.
- *Pseudonym*: stabile Kunstnamen je Mandant.
- *Namen*: die echten Mandantennamen.

Der Server-Admin setzt die Obergrenze (Vorschlag: Pseudonym). Der
Mandanten-Admin wählt für seinen Mandanten darunter oder gleich. Die
Zentrale verteilt weiter über die Profile aus RFC-0085 §7. Instanznamen
gehen schon heute hinaus; dieser RFC versteckt sie nicht, und das Portal
weist darauf hin.

**Im Zwilling:**

- Neue Objekte: Mandant, Tunnel, Destination und „externes Ende“.
- Der Tunnel ist ein eigenes Objekt (D3). Jede Seite schreibt ihre eigene
  Gruppe hinein, äußere und innere Hälfte.
- Eine Hälfte ohne Gegenstück bleibt sichtbar: „niemand wählt sich ein“
  oder „führt aus der Flotte hinaus“.
- Der Zustand des Tunnels läuft als Textreihe mit. So beantwortet eine
  Abfrage, wann der Tunnel letzte Woche weg war.

**Betroffenheit statt Alarmflut (Stufe 2).** Vom gestörten Glied aus
rückwärts lesen: Welche Destinationen, Instanzen und Mandanten hängen
daran? Diese Liste kommt in die bestehende Meldung (`tunnel_down`,
`connector_down`). Neue Alarmarten gibt es nicht.

**Stufen:**

1. Hälften und Mandanten im Statusdokument, Zusammenfügen in der Zentrale.
   Gemessen auf oaap-test mit Testverteiler, dann an der echten Kette auf
   Jörgs Wort.
2. Betroffenheit und die Zustandsreihe des Tunnels. Gemessen mit
   „VPN aus“.
3. Eine Tür für Apps nach I-41: Die VPN-App meldet ihren eigenen
   Tunnelzustand, das KI-Gateway meldet Modell → Bezugsquelle →
   Destination.

**Stufe 3a gebaut (15.11., Referenz 0.1.288, vpn-client 0.2.0, §8.1):**

- Eine Tunnel-App erklärt im Manifest (0.14) die Tür
  `link_state: {path: /oaap/links}`. Der Name ist nicht `links`, weil das
  Register dieses Wort schon für die Partnerliste nutzt.
- Der Knoten fragt die App bei jedem Statusdokument dort ab. Die Antwort
  enthält den eigenen Tunnel und jedes Ziel, jeweils als `ok` oder `down`,
  nur mit Namen.
- Im Statusdokument (0.11) trägt jede `through`-Zeile einen Zustand:
  - `ok`;
  - `down-tunnel`: VPN aus;
  - `down-target`: Ziel antwortet nicht;
  - `paused`: die App schläft;
  - `unknown`: keine Antwort.
- Die Zentrale färbt das externe Ende, führt eine Zustandsreihe und öffnet
  nach 5 Minuten `link.down` für das externe Ende. Das ist dieselbe
  Meldungsart; der Betreff heißt jetzt „Verbindung getrennt“.
- vpn-client 0.2.0 prüft dafür alle 30 s jedes Ziel per TCP.

Gemessen:

- **Live auf oaap-test** gegen eine Ersatz-Gegenstelle (in
  `oaap-lab/vpn-gegenstelle`), gelesen am echten Statusdokument:
  - Gaming-PC aus: `down-target` nach 21 s;
  - VPN aus: `down-tunnel` nach 63 s;
  - Standby: `paused` sofort;
  - App angehalten: `unknown`;
  - nach jedem Fall wieder `ok`.
- **Die Zentrale** gegen eine echte PostgreSQL, 83/83.

Noch offen:

- Die Zentrale live: oaap-demo auf 0.1.288, auf Jörgs Wort und mit
  Testverteiler.
- Das echte `ais-ovc` auf vpn-client 0.2.0.
- Stufe 3b: das KI-Gateway meldet Modell → Bezugsquelle → Destination.

**Stufe 1 gebaut (0.1.281):**
- Der Knoten meldet seine Hälften im Statusdokument 0.10.
- Der Connect-Dienst schreibt die Tunnel-ID in seinen Zustand.
- Neuer Befehl `oaap fleet disclose`.
- Die Zentrale fügt im Zwilling zusammen.

Gemessen:
- **Live auf oaap-test:** beide Hälften eines Tunnels mit derselben ID aus
  zwei verschiedenen Codewegen, das Angebot erkennt die Instanz
  `aigw-test`, keine Adresse und kein Schlüssel im Dokument, die Stufen
  wirken.
- **Zentrale gegen eine echte PostgreSQL:** ein Tunnelobjekt aus zwei
  Knoten, die ganze Kette als Beziehungen, Anhalten, Zurückziehen und
  Herabstufen.

Noch offen:
- ~~Befund: angehaltener Connect-Dienst liest sich als verbunden~~ —
  behoben 15.11. (Referenz 0.1.286): Herzschlag alle 30 s, eine
  liegengebliebene Zustandsdatei gilt als getrennt, behält aber die
  Tunnel-Kennung. Live gemessen mit echtem Anhalten: Mail nach 11 Minuten,
  Behoben 6 Minuten nach dem Neustart;
- ~~Befund „Dauer“~~ — behoben 15.11. (Referenz 0.1.287,
  oaap.core.notifications 0.9): Das Behoben zählt bei Flottenmeldungen ab
  dem Beginn der Störung;
- ~~Stufe 2, Betroffenheit~~ — gebaut 15.11. (Referenz 0.1.285). Befund
  beim Bauen: Für `tunnel_down`/`connector_down` öffnete bisher niemand
  eine Meldung. Deshalb öffnet jetzt die Zentrale **eine** Meldung je
  Tunnel (`link.down`), nach fünf Minuten, mit allem, was daran hängt.
  Das ist eine neue Meldungsart; Jörg bestätigt das noch. „VPN aus“ als
  solches erkennt erst Stufe 3. Die echte Kette ist aber schon lesend an
  der Zentrale gemessen;
- ~~die Portalseiten für die Stufen~~ — gebaut 15.11. als eine Seite
  „Flotte“ (Referenz 0.1.284): Der Server-Admin setzt Obergrenze und jede
  Mandantenstufe, ein tenant_admin sieht und setzt nur seinen Mandanten.
  Live auf oaap-test mit beiden Rollen gemessen;
- das Zusammenfügen live an der Zentrale, nach dem Update von oaap-demo.

Nebenbefund: Die automatische Adresse von Instanzen in Mandanten stand im
Statusdokument seit 0.3 falsch — behoben in 0.1.283 (15.11.).

**Entschieden am 14.11.: alles wie empfohlen**, D4 mit Jörgs Ergänzung:

- D1: ID aus dem Hash ableiten.
- D2: drei Stufen, Vorgabe Pseudonym.
- D3: der Tunnel als eigenes Objekt.
- D4: externe Enden als Objekt, Namen nur auf Stufe „Namen“. **Ergänzung
  Jörg:** Externe Namen sind das Ende unseres Universums, aber mit einer
  einfachen Verknüpfung wachsen die Daten zusammen (Partner, Datenräume,
  AAS). Dafür bekommt jedes externe Ende die Gruppe `owner.link`, die nur
  Menschen pflegen: eine externe Kennung (AAS-`globalAssetId`, IRI oder
  IRDI) und wessen Welt sie ist. Gleiche Kennungen werden als Kandidat
  angezeigt, das Zusammenführen bleibt das vorhandene Merge des Zwillings
  durch den Mandanten-Admin. Für einen späteren Export bekommen unsere
  eigenen Objekte eine `globalAssetId` über dieselbe änderbare Domain
  (objid.info).
- D5: Hälften im Statusdokument statt in einer eigenen Klasse.
