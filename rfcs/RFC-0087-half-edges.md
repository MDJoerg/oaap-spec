# RFC-0087: Half-Edges — Each Node Reports What It Knows of Its Links, the Hub Joins Them

- **Status:** Proposed (2026-11-14) — decisions D1–D5 asked of Jörg (§9)
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
| `oaap.fleet.external` | `<node>/<instance>/<target>` | `oaap.external`: kind (`vpn`, `offer`) |

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

## 6. Affected, not alarmed

Stage 2 adds one read to the twin service, **`affected(object)`**: from a
tunnel, an external end or an instance, follow `uses`, `bindsTo`,
`reaches` and `heldBy` backwards and list what depends on it — "VPN of
`ais-ovc` is down → destination `gamingpc` → `ais-mg` on oaapi01 → tunnel
`t-9f2c…` → destination `ais-oaapi01` → `ais-chat` on oaapx01, tenant
`ais`". FleetView draws it later; the fleet service puts the list into the
detail of the existing attention item (`tunnel_down`, `connector_down`)
when it opens a matter. No new alert kinds, no second mail.

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

## 9. Decisions asked of Jörg

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

**Fünf Entscheidungen (D1–D5)**, jeweils mit Empfehlung:

- D1: ID aus dem Hash ableiten.
- D2: drei Stufen, Vorgabe Pseudonym.
- D3: der Tunnel als eigenes Objekt.
- D4: externe Enden als Objekt, Namen nur auf Stufe „Namen“.
- D5: Hälften im Statusdokument statt in einer eigenen Klasse.
