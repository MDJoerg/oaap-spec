# RFC-0120: The Twin as an Integration Hub

- **Status:** **Accepted (2026-11-22)** — D1–D12 as recommended (Jörg: "Alles wie empfohlen").
  Kept in mind (§4.10): webhooks in both directions.
  **Stage 0 built and measured 2026-11-22 (§9), with the portal page:** reference 0.1.346,
  `oaap.data.twin` 0.10, `oaap.core.identity` 0.6.11; §1.6 confirmed and closed.
  **Stage 1 built and measured 2026-11-22 (§10):** reference 0.1.347, `oaap.data.twin` 0.11
  §2.18 -- use case 1 done: a graph viewer loads the fleet twin of a tenant from outside.
  **Stage 2 built and measured 2026-11-22 (§11):** reference 0.1.348, `oaap.data.twin` 0.12
  §2.19-2.21, `oaap.data.model` 0.3 -- use case 3 done: KPIs with periods entered in the form and
  read per period.
  The facts in §1 were read the same day in `oaap.data.twin` 0.9, `oaap.data.model` 0.2,
  `oaap.data.timeseries` 0.1, `oaap.events.broker` 0.4, RFC-0027, RFC-0085/0087,
  `program/zielbild-datenplattform.md`, `program/capability-ideas.md` (I-51) and the reference
  0.1.345 (`platform/services/twin/`, `platform/services/identity/app.py`).
- **Date:** 2026-11-22
- **Authors:** Jörg (the idea, 2026-11-22: the twin's MCP door will also write — creating and
  changing types and instances from the chat, for authorized persons only; "one of my next
  requirements is a far-reaching REST API for our twin, to evaluate the data but also to model,
  create, change. That makes our twin concept even more valuable as an integrating part of a
  complex landscape, and the data grow together." And: "it gets exciting if through this API
  status changes are made, time series added and queried, research over relationships and so on
  is possible, so that we can become an important part of an integration platform and bring other
  features such as messaging and broker into play. We should think our RFC bigger right away."),
  Claude (facts, design)
- **Depends on:** RFC-0031 (the digital twin), RFC-0085/0087 (the fleet in the twin), RFC-0086
  (time series), RFC-0032 (events and relay), RFC-0027 (API keys), RFC-0045 (authorizations),
  RFC-0090 (lifecycle and erasure, Draft), RFC-0118 P6 / RFC-0119 D13/D16 (the twin as an MCP
  source; writing tools one tick each)
- **Changes (when accepted):** `oaap.data.twin` (1.0: an external door, query and graph reads,
  status, attribute periods, sync, change feed, writing MCP tools); `oaap.data.model` (status
  declared on a type; tenant object types); `oaap.data.timeseries` (series for persons and
  clients); `oaap.events.broker` (value events, webhooks); identity (the principal kind
  `client:`); the portal (keys for integration clients, a form for values with a period)
- **Not part of this RFC:**
  - **The AAS repository API** (`oaap.data.aas`, `zielbild-datenplattform.md`). It is the next
    door on top of this one, its own RFC; this RFC keeps its shapes AAS-friendly (§4.9).
  - **An OAuth issuer** for third-party clients (RFC-0027 non-goal stays).
  - **A general query language** (SPARQL, Cypher, GraphQL). §4.3 proposes a small, fixed set of
    reads that answer the three use cases; a language is a later question (D5).
  - **Lifecycle and erasure** of twin data (RFC-0090); this RFC only needs "retire" (§4.5).

## Summary

The twin is the platform's model of things — fleet nodes and instances, companies, persons,
projects, assets — with history, relations, groups owned by whoever wrote them, time series and
events. Today only the platform's own apps and the portal can reach it, mostly reading; a person
can change a group in the portal, nobody outside the platform can write, and the MCP door has three
reading tools.

This RFC proposes to make the twin **the integration hub of a tenant**: one documented, versioned
door (`/twin/v1`) for programs outside the platform, with the same rules that hold inside. It adds
what the three first use cases need:

1. **Evaluate and research** — filtered queries, graph reads (neighbourhood, paths, what depends on
   what), exports a graph viewer can load, a change feed (use case: an external graph viewer over
   the twin of our fleet).
2. **Model and sync** — object and group types per tenant, idempotent upserts by the source's own
   key, batches, retire, a change feed both ways and a clear rule for who owns what (use case: an
   enterprise modelling tool whose twins are kept in sync with the platform).
3. **Values in time** — attribute values with a period that coexist (KPI 2024 and KPI 2025), time
   series for persons and clients, a form to enter them (use case: a sustainability dashboard whose
   only data base is the twin).

Across all three: **status changes** as a declared, audited transition on an object; **events with
values** on the broker and **webhooks** for programs outside; **writing MCP tools** for persons, on
the road RFC-0119 D13 laid (one tick each, confirmation per call in the chat).

## 1. Facts (read 2026-11-22)

### 1.1 Doors today

- **Apps:** `/twin/*` on the node site, with an instance key scoped `oaap.twin`, minted at
  install (`appctl.py` `TWIN_KEY_SCOPE`). The caller is `instance:<name>`; what it may do comes
  only from its type **bindings** (`reads`, `contributes`, `owner`) in `oaap_model.bindings`; the
  tenant comes from the registry, never from the request. Routes: types, `POST /twin/objects`,
  read one, list by type (`q`, `offset`, at most 500, `truncated`), `PUT …/groups/{group}`
  (twin §2.4–2.7), and the time-series routes (`oaap.data.timeseries`).
- **Persons:** only through the portal's `/internal/twin/*` (shared internal key plus person
  headers): read the tenant's twin, tree (`depth` ≤ 5), `affected` (fleet objects only), merge and
  unmerge, write **tenant-origin** groups, create a **group** type (twin §2.9–2.12). A person cannot
  create an object; nothing deletes.
- **Remote reader:** `remote:<label>`, read-only, created by the operator's CLI for another OAAP
  node (twin §2.14).
- **MCP:** `twin_types`, `twin_search`, `twin_object`; a person is required, keys are refused;
  no writing tool (twin §2.16).
- **No door for a program outside the platform.** A key a tenant admin issues under *Zugänge*
  reaches app routes, the broker and `/authz/*`, not the twin (RFC-0027).

### 1.2 Model and time

- One schema per tenant in PostgreSQL; objects, source keys, groups, attributes (`value jsonb`,
  `valid_from`/`valid_to` as **dates**), relations, activities, events, aliases, states; everything
  append-only (`superseded_by`), read through `current_*` views. A group belongs to the origin that
  first wrote it (twin §2.3, §2.15).
- **One current value per (object, group, attribute)**: a new value supersedes the old one whatever
  its validity; validity is set once per PUT for all attributes in it. Two periods of one attribute
  (KPI 2024, KPI 2025) **cannot coexist** today. `?at=` is a day.
- **Activities** have a `status` that nothing updates after creation; there is **no object status**
  (twin §2.3). The table `states` holds group snapshots for the relay; nothing reads it.
- **Types** live in the node-wide registry `oaap_model` (kinds object, attribute, group, relation,
  activity; value types text, int, decimal, bool, date, datetime, enum, ref; origins `app:`,
  `model:`, `tenant:`; additive changes only; `semantic_id` → `semantic_iri`). A tenant may create
  only a **group** type on an existing object type (twin §2.11).
- The app PUT checks attribute keys against a pattern, **not** against the registry's value types
  (`twin_write.py`).
- **Time series exist** (`oaap.data.timeseries` 0.1, RFC-0086): series = (object, measure, labels),
  number or short text, tiers raw/5m/1h/1d with retention up to 10 years, rights from the object's
  binding, limits per tenant. Reachable for app keys only; no person route, no chart, no recorder,
  no external protocol (RFC-0086 §11).

### 1.3 Events

- Broker (Mosquitto, profile `broker`); topics `oaap/<tenant>/<type>/<object>/<group>`; the relay
  publishes thin events (id, kind, object, group, origin, time) — **no values**; a subscriber reads
  the value from the twin. Subscribers: an unscoped RFC-0027 key of the tenant, `oaap/<tenant>/#`;
  WebSocket through the gateway or TCP 1883 with profile `exposed` (`oaap.events.broker` 0.4).
- No webhooks, no server-sent events, no change feed, no value topics, no recorder.

### 1.4 The fleet in the twin

Types `FleetNode`, `FleetInstance`, `FleetTenant`, `FleetTunnel`, `FleetDestination`,
`FleetExternal`, `FleetAsset`, `FleetBroker` (origin `platform:fleet`), groups after AAS submodels
(`oaap.software`, `oaap.placement`, …), relations `isPartOf`, `heldBy`, `servedBy`, `dialedBy`,
`uses`, `reaches`, `bindsTo`, written every 30 s by the hub's `fleet_sink`; node metrics as series
(RFC-0085 A2, RFC-0087). This is the first graph worth looking at from outside (use case 1).

### 1.5 Ideas already written down

I-51 "self-growing CMDB" (AAS mapping, owner methods), the data-platform target picture (a
relationship graph next to the twin API, `oaap.data.aas`, `oaap.data.search`,
`oaap.events.queue`, the twin browser as modelling tool, Jörg's earlier "universes" REST service
with batch, export/import and feeds). No RFC for any of them; nothing on KPIs or on syncing a
modelling tool.

### 1.6 To check before anything is built

Identity's `POST /internal/keys` lets a tenant admin issue a key for a principal of their tenant
with any `instance` value and roles the principal holds. Whether an app's `instance:<name>`
principal is such a principal — and so whether a tenant admin could mint an `oaap.twin` key and act
as that app on the twin — was **not** read to the end. Stage 0 measures it (§6, line 1).

## 2. The three first use cases

| Use case | What it needs from the twin |
|---|---|
| **1. Graph viewer over the fleet twin** (external, read) | a key for a program; objects and relations of chosen types as nodes and edges in one export; neighbourhood and path reads; `?at=` for "how did it look then"; series of a node; a change feed to stay current |
| **2. Enterprise modelling tool, synced** (external, read + write) | create object and group types for the tenant; upsert objects by the tool's own ids; set groups and relations in batches; retire; read what others changed (change feed, webhooks); a rule that the tool never overwrites what the platform or a person owns |
| **3. Sustainability dashboard** (inside or outside, read + write) | KPIs as attribute values **with a period** (year, quarter, month) that coexist, with unit and source; a form to enter them on an asset; series for measured values; reads per period across many assets; the twin as the only data base |

## 3. The idea in one picture

```
                    ┌──────────────────────────── tenant's twin ────────────────────────────┐
 apps (instance:)───┤ /twin/*            (as today)                                          │
 portal (persons)───┤ /internal/twin/*   (as today, + status, periods, series, form)         │
 chat (persons) ────┤ MCP door           (+ writing tools, one tick each, confirm per call)  │
 programs ──────────┤ /twin/v1/*         NEW: query, graph, export, upsert, batch, status,   │
 (client:<label>)   │                    periods, series, change feed                        │
                    │        one write rule (twin §2.15) · bindings · origins · audit         │
                    └───────┬───────────────────────────────────────────────┬────────────────┘
                            │ events (+ values, opt-in)                     │ webhooks (signed)
                         broker (MQTT, WebSocket)                      programs outside
```

Every door goes through the **same write rule** and the **same bindings**. A program is a new
kind of principal, not a back door.

## 4. Proposal

### 4.1 Integration clients (the external door)

- A new principal kind **`client:<label>`** per tenant: a program outside the platform (a graph
  viewer, a modelling tool, a dashboard). The tenant admin creates it in the portal (*Zugänge →
  Integration*) with **bindings per type**, exactly like an app's (`reads`, `contributes`,
  `owner`), and a key scoped `oaap.twin` (RFC-0027: bearer, expires, at most 365 days). The origin
  of what it writes is `client:<label>`.
- The door is **`/twin/v1/*`** on the tenant's place (its domain, RFC-0115) and on the node's
  names, behind the gateway's key check. The tenant comes from the key, never from the request.
- An **OpenAPI 3.1** document at `/twin/v1/openapi.json`, generated from the types the client is
  bound to (a modelling tool can read what it may write).
- Limits per client (requests, writes, objects per batch) and an audit row per write, as for apps.
- The remote reader (twin §2.14) stays as it is; it becomes a special case of a reading client
  (D2).

### 4.2 Reads that answer questions

- **Filtered lists:** `GET /twin/v1/objects?type=&where=<group>.<attr><op><value>&at=&fields=`
  with a small, fixed set of operators (`=`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `has`), checked
  against the registry's value types; **cursor paging** instead of the cap at 500.
- **`?at=`** as a date-time (today a day); answers name the time they are valid for.
- **Exports:** `GET /twin/v1/export?types=&relations=&at=&format=json|jsonld|graphml` — nodes and
  edges in one document, what a graph viewer loads; JSON-LD uses `semantic_iri` where a type has one.

### 4.3 Graph reads (research over relationships)

- **Neighbourhood:** `GET /twin/v1/objects/{id}/graph?depth=&relations=&direction=&types=&at=`
  (depth at most 5, as the tree today; bounded in nodes).
- **Paths:** `GET /twin/v1/paths?from=&to=&relations=&max=` — the shortest paths between two
  objects (what connects this tunnel to that tenant?).
- **Dependents:** `affected` (twin §2.10a) for every type, not only fleet objects, with a declared
  set of relations that carry dependency.
- Computed in PostgreSQL (recursive queries over `current_relations`), no second store (D5).

### 4.4 Status as a declared transition

- A type may declare a **status** in the registry: its values and the allowed transitions
  (`planned → active → retired`, `open → in_work → done`), optionally who may make which
  (roles or bindings).
- `POST /twin/v1/objects/{id}/status {"to", "reason"}` (and the same in the portal and as an MCP
  tool): checked against the declaration, appended with who, when and why, published as an event.
  The current status and its history are read with the object.
- The table `states` keeps its relay meaning; the new thing is called **status** (D7).

### 4.5 Modelling and sync

- **Types per tenant:** a tenant admin (and a client with the right binding, D8) may create
  **object types**, attribute, relation and group types with origin `tenant:<id>`, additive only
  (`oaap.data.model` §2.5); keys are namespaced per tenant to end the node-wide flat namespace for
  tenant types (D9).
- **Upsert by the source's own key:** `PUT /twin/v1/objects/by-key/{source}/{key}` — creates or
  finds the object by `source_keys`, idempotent; the twin's id is returned and kept by the tool.
- **Batches:** `POST /twin/v1/batch` — up to N operations (objects, groups, relations, status) in
  one transaction, all or nothing, with a client-chosen id so a retry does nothing twice.
- **Retire** instead of delete: an object or a relation ends its validity (`valid_to`), stays in
  the history, disappears from `current_*`; erasure stays RFC-0090.
- **Ownership:** a client writes only groups of its own origin (the rule of twin §2.15); a group
  another origin owns is refused with a sentence that names the owner. Relations a client writes
  are its own. This is the sync rule: nobody overwrites anybody.
- **Values are checked** against the registry's value types on every door (today only the key
  pattern is checked).

### 4.6 Values in time

- **Attribute periods:** an attribute may carry several values that **coexist**, each with a
  period (`valid_from`, `valid_to` as date-times) and optionally `unit`, `source`, `quality`.
  The current row is the one whose period contains "now"; `?at=` picks another; a list of periods
  is read with `…/attributes/{attr}/periods`. A type declares which attributes are **periodic**
  (D4); the others keep today's rule.
- **Series for everybody:** the time-series routes for persons (portal, a chart on the object's
  page) and for clients (`/twin/v1/series`), same rights from the bindings.
- **Which to use:** a KPI reported per period (CO₂e 2025, energy per quarter) is an attribute
  period — few values, each with source and quality; a measured value (power every minute) is a
  series. The RFC writes that rule down so the dashboard and the modelling tool agree (D4).
- **Form mode:** the portal's object page gets *Werte mit Zeitraum*: choose attribute and period,
  enter value, unit and source — the first screen of use case 3, without a separate app.

### 4.7 Events, messaging and webhooks

- **Value events (opt-in per type):** the relay may publish the changed values with the event
  (`oaap/<tenant>/<type>/<object>/<group>`), for subscribers inside the platform that should not
  read back. Types with personal data stay thin (D10).
- **Status events:** `…/<object>/status` with from, to, who, why.
- **Webhooks for clients:** a client may register a URL per type and kind; the twin posts the event
  signed (HMAC with a secret only the client holds), retries with backoff, and stops after a limit,
  which the portal shows. A program outside needs no MQTT connection.
- **Change feed:** `GET /twin/v1/changes?since=<cursor>&types=` — every change in order, for a sync
  that missed webhooks; the cursor is the event id.
- The broker stays the bus inside the platform; queues (`oaap.events.queue`) are a later RFC.

### 4.8 Writing MCP tools

- New tools on the twin's MCP door: `twin_create_object`, `twin_set_group`, `twin_relate`,
  `twin_set_status`, `twin_add_period`, `twin_add_points` — each `readOnlyHint: false`.
- They act **as the person** with the person's rights in the portal (tenant-origin groups only,
  the same rule), never as an app or a client.
- They enter an assistant only by the road of RFC-0119 D13: each one ticked in the wizard, the
  chat confirms every call. A platform template "Zwilling" (RFC-0119 D16, stage 3c) starts reading.

### 4.10 Kept in mind: webhooks in both directions (Jörg, 2026-11-22)

Jörg: "Webhooks would have even more potential if we think of them in both directions." §4.7
proposes webhooks **out** of the twin. The other direction: a system that only speaks webhooks
(a modelling tool, a ticket system, an IoT or SaaS platform) **pushes** its changes **into** the
twin — `POST /twin/v1/hooks/<client>/<hook>`, the signature checked with a secret the client
holds, the payload turned into upserts, groups, status changes or series points by a **mapping
the tenant declares** (which field is the source key, which goes into which group, which event
means which status), and every result goes through the same write rule as any other write of that
client. Nothing is fetched by the twin. A receiver like that is what makes "the data grow
together" without writing an adapter per system; it is the inbound partner of sync (stage 3).
**Not decided** — to be designed with stage 3, with its own decision (mapping format, what a
mapping may write, replay and order, limits).

### 4.9 Friendly to AAS

Groups already follow AAS submodels in the fleet; types carry `semantic_id`. The new reads answer
`semantic_iri` wherever there is one, and the export in JSON-LD uses them — so the later
`oaap.data.aas` door is a mapping on top, not a rebuild.

## 5. Security requirements

1. The tenant of every call comes from the key's principal, never from the request.
2. A client's rights come only from its bindings; no role of a person carries over to a client.
3. One write rule for every door (twin §2.15); a client writes only its own origin's groups.
4. Every write is audited with principal, origin and (for persons through MCP) the assistant.
5. Webhook targets are outside hosts: the tenant's egress rule applies (RFC-0068); a closed tenant
   gets none, or only to destinations it has bound.
6. Value events and exports respect a type's marking for personal data (D10).
7. Limits per client and per tenant; a batch is bounded.
8. §1.6 is measured and closed before the external door opens.

## 6. Stages

| Stage | What | Done when |
|---|---|---|
| **0** | measure §1.6; OpenAPI skeleton; principal kind `client:` with bindings, key, portal *Integration* | the gap answered (and closed if open); a client reads `GET /twin/v1/types` with its key |
| **1** | reads: filtered lists, cursor, `?at=` date-time, neighbourhood, paths, export (JSON, GraphML); change feed | use case 1: a graph viewer loads the fleet twin of a tenant from outside, measured on oaap-test |
| **2** | values in time: periodic attributes, series for persons and clients, chart, form *Werte mit Zeitraum*; value checks on every door | use case 3: KPIs with periods entered in the form and read per period |
| **3** | modelling and sync: tenant object types, upsert by key, batch, retire, webhooks (out; inbound hooks with a mapping to be decided here, §4.10) | use case 2: a tool creates a type and objects, a person changes a group, the tool hears it by webhook and does not overwrite it |
| **4** | status: declared transitions, route, portal, events | a status change refused off the declaration and accepted on it, with its event |
| **5** | writing MCP tools on the twin, RFC-0119 3c template "Zwilling" with them as ticks | a person changes a group from the chat, confirmed, audited |
| later | value events, AAS repository API (`oaap.data.aas`), queues, a query language | own decisions |

## 7. Conformance (described; every line gets a bait)

1. A client's key of tenant A never reads tenant B, whatever the request says.
2. A client reads only types it is bound to; writes only with `contributes`; only its own groups.
3. A batch with one bad operation changes nothing; the same batch id twice writes once.
4. An upsert by key twice creates one object.
5. A value of the wrong type is refused on every door.
6. Two periods of one periodic attribute coexist; `?at=` picks the right one.
7. A status transition not declared is refused; a declared one is appended and published.
8. A webhook is signed; a wrong signature is the receiver's to see; a closed tenant posts none.
9. A writing MCP tool acts as the person and only where the portal would let the person write.

## 8. Decisions

*Accepted 2026-11-22: D1–D12 as recommended.*

- **D1 — An external door for programs at all (`/twin/v1`, principal `client:`), rather than
  only apps and persons?** *Recommendation: yes* — it is what makes the twin a hub; with the same
  bindings and write rule it adds a kind of caller, not a new rule.
- **D2 — Clients are created by the tenant admin (portal), not only by the operator?**
  *Recommendation: yes, tenant admin*; the operator can withdraw a tenant's right
  (`tenant_admin_may`). The remote reader becomes a reading client.
- **D3 — One versioned path `/twin/v1` with an OpenAPI document, the existing `/twin/*` for apps
  unchanged?** *Recommendation: yes.*
- **D4 — KPIs with a period as periodic attributes, measurements as series — and a type declares
  which attributes are periodic?** *Recommendation: yes.*
- **D5 — Graph reads in PostgreSQL (recursive queries), no graph database, no query language now?**
  *Recommendation: yes*; measure with the fleet twin; revisit if paths get slow.
- **D6 — Webhooks and a change feed for programs outside, the broker for inside?**
  *Recommendation: yes.*
- **D7 — Status declared on the type with allowed transitions, called "status" (the table
  `states` keeps its relay meaning)?** *Recommendation: yes.*
- **D8 — May a client create types, or only the tenant admin?** *Recommendation: a client with an
  explicit `models` binding may create types of its tenant's origin*, because syncing a modelling
  tool is exactly that; additive only.
- **D9 — Tenant type keys get a tenant namespace (e.g. `t.<label>.<Key>`)?** *Recommendation:
  yes*, before tenants create object types; app and model types keep their keys.
- **D10 — Value events and exports leave out attributes marked personal, unless the type says
  otherwise?** *Recommendation: yes.*
- **D11 — Writing MCP tools act as the person with the portal's rights only (no client or app
  rights through the chat)?** *Recommendation: yes.*
- **D12 — Order of stages: reads (use case 1) before values in time (use case 3) before sync (use
  case 2)?** *Recommendation: yes* — reads are the smallest risk and show the hub soonest; the
  dashboard needs periods, which sync also needs.

## 9. Stage 0 — built and measured (2026-11-22)

**§1.6 confirmed and closed.** Measured on `oaap-test` before the fix: a tenant admin of
`vuebung` got, through identity's people's key door (the one the portal's *Zugänge* uses, which
passes principal and scope through), keys for the app principal `instance:vuebung-vuebung-verein`
scoped `oaap.twin`, `oaap.authz.admin` and `oaap.cases.submit:x` -- 3 of 3 issued (each revoked
at once); the `oaap.twin` key reached the twin service (it answered 409, "no twin schema", i.e.
past the gateway's key check). Not only the twin: the same hole reached the authorization admin
door and the cases door. **Fix** (identity, `oaap.core.identity` 0.6.11): that door refuses keys
for `instance:`, `remote:`, `client:` principals and any scope with a dot, for every actor,
audited `key.refused`; the platform keeps minting them through `issue_key`. After the fix: 3 of 3
refused, no key made.

**Built.**

- Principal `client:<label>`, `oaap data twin clients | add-client <label> --tenant --reads
  [--days] | remove-client <label>` (reading only), record `twin-clients.json` without a secret,
  audit `twin.client.add/remove`.
- `GET /twin/v1/types` and `GET /twin/v1/openapi.json` (OpenAPI 3.1 of the door as the caller sees
  it) for every twin principal; clients refused on every write path (objects, groups, series).
- `oaap.data.twin` 0.10 §2.17.

**The tenant admin's page (D2), built the same day.** *Zugänge → Integration* lists the tenant's
clients with their types and keys, makes a client (name, types) and removes one through a host job
(`twin-client-add` / `twin-client-remove` in the recipe job: own tenant only, active types only,
a sentence that names the active ones otherwise) -- **without a key**: the job's result files never
hold a secret. The key is issued on the page straight from identity and shown once, like every
other key. For that identity's people's key door makes one exception to §1.6: the key of a
`client:` of the actor's own tenant, scoped exactly `oaap.twin`, role `user` only; `instance:`,
`remote:` and every other scope stay refused. Tests: `test_key_pages` +7 (the page names client,
types, keys and `/twin/v1`, shows a job's refusal, asks before removing, carries no secret; the key
comes from identity once, scoped to the twin with role user, only for a client of this tenant;
add and remove are jobs with an origin check and no secret); `test_api_keys` +6 (own client's
twin key issued; another tenant's client, other scopes, more roles refused). Measured on
`oaap-test` with a temporary tenant admin in `fleetprobe` (removed afterwards), 9/9: job as
tenant admin makes the client without a key and nothing secret in its result; for another tenant
and with an inactive type refused (naming the active types); the people's key door gives the
tenant admin the twin key of its own client; `/twin/v1/types` with it 200; the client without the
twin scope, with more roles, and an app principal refused; remove revokes (401). §1.6 again 3/3
closed. **Not measured:** the page clicked in the browser (served: the route is in the portal).

**Tests.** `test_twin_clients` (new, 11: only the bound types, tenant from the record, a tenant in
the request ignored, unknown client and a person refused, OpenAPI with only its types, three write
paths refused, an app reads /twin/v1 with its own bindings); `test_api_keys` +16 (both actors, five
scopes for an `instance:` principal, `remote:`, `oaap.twin` for an ordinary principal -- all 403,
no key made; an ordinary instance scope still issued; the platform's own `issue_key` still mints
the twin key); twin, key and identity suites green in the Linux runner. `test_tenant_boundary` has
5 red checks **before and after** this change (Caddy lines of public routes, not keys) -- a
pre-existing finding, not touched here.

**Measured on `oaap-test`** (0.1.346 staged after a backup), 3/3 + 8/8:

| Asked | Answer |
|---|---|
| tenant admin asks for `oaap.twin`, `oaap.authz.admin`, `oaap.cases.submit:x` keys of an app principal | 403 each, "stellt nur die Plattform aus", no key |
| `add-client messung-120` in tenant `fleetprobe`, reads `AssetApp` | key issued (not printed), expires |
| `GET /twin/v1/types` with it | 200, exactly `AssetApp`, access read, caller `client:messung-120` |
| `GET /twin/v1/openapi.json` | OpenAPI 3.1, bearer, `x-oaap-types` = its type |
| without a key / a wrong key | 303 to the sign-in / 401 |
| `POST /twin/objects` with the client's key | 403 "reads only" |
| after `remove-client` | the key 401 |

A first run said 200 for "without a key": the measurement followed the 303 to the sign-in page;
corrected (no redirects followed) and run again.

## 10. Stage 1 — built and measured (2026-11-22)

**Built** (`twin_read.py`, routes in the twin service, `oaap.data.twin` 0.11 §2.18): filtered lists
with a cursor (`where` checked against the registry's value types, `fields`), one object,
neighbourhood (`/objects/{id}/graph`), shortest paths (`/paths`), export JSON and GraphML
(`/export`, personal attributes left out -- D10, an attribute type may now say `"personal":
true`), change feed (`/changes`, cursor = event id, `since=now`, 5 s settling so a late commit is
not skipped); OpenAPI describes them.

**Decided while building (named here, not hidden):**

- `at` is a **date-time** and means both axes at once: what was recorded by then and not yet
  superseded (the recorded time the twin keeps anyway), and validity on that day. A date alone is
  the end of that day, UTC. Without `at` an ended relation (`valid_to` passed) is gone -- the fleet
  ends relations that way, and a viewer must not draw them.
- The `where` spelling: `<group>.<attr><op><value>` (`= != < <= > >=`), `<group>.<attr> in a,b`,
  `<group>.<attr> has` -- the group key has dots, so the attribute is the last part.
- Graph walks in Python over **one** load of the visible edges (D5: PostgreSQL, no second store;
  no recursive SQL yet). Measured below; revisit when a twin is much larger than the fleet's.
- An object of a type the caller may not read answers **404 like a missing one**, and is never an
  edge's end -- a client cannot probe ids across types.

**Tests.** `test_twin_v1_reads` (new, 38, against a real PostgreSQL in the Linux runner): a small
twin with history -- lists ordered and paged without gaps or doubles; filters as number, yes/no,
`in`, `has`; six baits answered 400 with a sentence; `at` 90 minutes back sees the old value,
misses an object recorded later and a merge done later; a merged id answers as its object with
its relations; neighbourhood and paths ignore an ended relation and never show the forbidden type;
export JSON = GraphML, personal attribute left out; feed paged in order, without the forbidden
type, `since=now`, a fresh event held back; a client of another tenant reads only that tenant; an
app reads `/twin/v1` with its own bindings; a person is refused. `test_twin_clients` adjusted
(OpenAPI paths); seven twin files green.

**Measured on `oaap-test`** (0.1.347 staged after a backup; `m121.py`, a temporary client in the
hub tenant reading the 8 fleet types, removed afterwards), 15/15:

| Asked | Answer |
|---|---|
| `/types` | 8 fleet types, 154 ms |
| `/export` (JSON) | 73 nodes (42 instances, 12 tenants, 7 nodes, 4 brokers, 4 assets, …), 116 edges of 17 relations, 54 KiB, 155 ms; every edge between nodes |
| `/export?format=graphml` | valid GraphML, 76 KiB, 181 ms, same nodes and edges |
| `/objects?type=FleetInstance&limit=10` | 5 pages, 42 objects, none twice, 713 ms in all |
| `where=oaap.liveness.fleetState=up` | 1 of 7 nodes, matching the values in the list |
| `/objects/{oaap-test}/graph?depth=2` | 64 nodes, 110 edges, 132 ms |
| `/paths` instance -> tenant | 1 shortest path over the node, 143 ms |
| `/export?at=` 6 hours back | 73 nodes, 116 edges, `at` named |
| `/changes` | 343 changes in one page, then none; `since=now` -> next 372 |
| baits: unknown attribute; type not bound; another tenant's object (and its graph); no key / wrong key | 400 / 400 / 404, 404 / 303, 401 |
| after removing the client | its key 401 |

**Not measured:** a real graph viewer program (the export is GraphML 1.0 and loads like any
other; no viewer was run); a twin much larger than the fleet's.

## 11. Stage 2 — built and measured (2026-11-22)

**Built** (`twin_values.py`, `twin_write.py`, `twin_read.py`, routes in the twin service, the
portal's object page and type form; `oaap.data.twin` 0.12 §2.19-2.21, `oaap.data.model` 0.3):

- **Values checked on every door** (§2.19 of the spec): app, person, platform writers, periods --
  one function, before anything is written; a bad value refuses the whole write with a sentence.
- **Periodic attributes** (D4): an attribute type says `"periodic": true` (and a `unit`); table
  `periods`, append-only; written by an app (`POST …/groups/{group}/periods`) or a person in the
  portal; read per period on every door and as the object's value.
- **Series for persons and clients:** `/twin/v1/series` (list, range, latest) for a client, the
  same through `/internal/twin/series` for the portal; the object page draws each number series.
- **The form *Werte mit Zeitraum*** on the object page: attribute, a year (whole, a quarter or a
  month) or two dates, value, unit, source, quality; a table per attribute with bars, a button
  to withdraw. The form *Typ anlegen* gets a column "Werte mit Zeitraum" and the unit.

**Decided while building (named here, not hidden):**

- **One bad value stops an app's or a person's write, not the fleet's.** The platform's own
  writers (origin `platform:`) lose only that value, logged -- one odd reading of one node must not
  stop the fleet twin. An **empty string** for any type but text is "no value" (stored `null`): the
  portal's empty field, and what the fleet writes for "none" (measured: the only 4 of 651 current
  values on oaap-test that did not fit were such empty strings). A string where a number is
  expected becomes the number (the portal sends text).
- **Periods of one attribute must not overlap; the same bounds again correct.** Otherwise "the value
  at a moment" would be ambiguous. Q1 and the year 2025 cannot both be one attribute -- a type that
  wants both declares two attributes. `null` withdraws (a row, not a delete).
- **A date as `valid_to` is the last day covered** (2025-01-01 .. 2025-12-31 = 2025), stored
  exclusive as the next day's 00:00 UTC -- what a form asks, what the API keeps.
- **The object's value of a periodic attribute** is the period containing the moment, else the
  **last one that ended before it**, with its bounds. A KPI for 2025 read in November 2026 is still
  the last known value; showing nothing would hide it, and the bounds keep anyone from taking it
  for today's.
- **`at` stays both axes** (stage 1). An object recorded today does not exist at `at=2024-07-01`,
  so a past period as known today is read with `from`/`to` on `/periods`; the portal's date picks
  the period of that day (it filters validity only, as before).
- **Turning `periodic` on or off is a destructive type change** (`type_change_kind`): the values
  live in another table then.
- **Clients still only read** -- writing periods is stage 3 (sync), with the rest of writing.

**Tests.** `test_twin_periods` (new, 44, against a real PostgreSQL in the Linux runner): value
checks per type with baits (int, date, enum), all-or-nothing, `"120"` -> 120, `""` -> null, a
`platform:` writer losing one value; periods coexisting, overlap 409, correction, unchanged 200,
withdrawal and second withdrawal 404, non-periodic 400, periodic in a group write 400; reads per
period, window, `at` before a correction, object value now (last ended) and on a day; the person
door (roles, tenant group created, an app's group refused, inactive group type); series for a
client (list, range, latest, a forbidden type 404) and a person; OpenAPI; the portal's form rules,
labels, bars and lines; the destructive type change. `test_fleet_twin` now registers the fleet's
attribute types and counts values left out: **none** -- the fleet's real values pass the check.
13 twin and portal files green.

**Measured on `oaap-test`** (0.1.348 staged after a backup; `m122.py`, a temporary tenant admin in
the hub tenant and a temporary client, removed afterwards with every row of the probe group),
20/20:

| Step | Result |
|---|---|
| *Typ anlegen* with two periodic KPIs (CO₂e t, energy MWh) and an int counter on `FleetNode` | registered: periodic with unit, the counter not |
| object page of the node oaap-test | the card *Werte mit Zeitraum* with its form, 228 ms |
| CO₂e 2024, 2025, Q1 2026, energy 2025 entered in the form | "Eingetragen: 2024." … each 45-56 ms |
| Q2 2025 (overlaps 2025); "viel" as a number | refused with a sentence |
| 2025 corrected, then the same again | "Eingetragen", then "Unverändert" |
| 2023 entered, then the button *Zurückziehen* | gone from every list |
| the page again (30 days) | 2024, 2025, Q1 2026, 2025 with bars; series drawn as lines |
| "viele" for the counter; "7" | refused; stored as the number 7 |
| client: CO₂e per period | 2024 1200.5, 2025 1050, Q1 2026 260 -- t CO₂e, with quality, 141 ms |
| client: window June 2025 | CO₂e 2025 and energy 2025 |
| client: the object now | CO₂e 260 (Q1 2026, the last ended) with its bounds, energy 830 |
| client: the node's series and the last day of one | 14 series; points read |
| every current value of the node's 4 twins through the new check | 652, none refused |

The fleet no longer writes this twin (oaap-test stopped being the hub on 2026-11-15); the fleet's
writing under the check is therefore covered by the runner test, not by a live hub. **Not
measured:** the pages in a browser (read as HTML), a twin of another tenant with real KPIs, a
dashboard program reading them.

## Deutsche Zusammenfassung

**Idee (Jörg, 22.11.):** Der Zwilling soll das Integrationsstück der Plattform werden. Dazu
gehört eine weitreichende REST-API zum Auswerten, Modellieren, Anlegen und Ändern, außerdem
Statusänderungen, Zeitreihen ergänzen und abfragen und Recherche über Beziehungen. Messaging und
Broker kommen zum Einsatz, und die MCP-Tür bekommt schreibende Werkzeuge für Berechtigte. „Gleich
größer denken.“ Drei erste Anwendungsfälle: ein externer Graph-Viewer über den Zwilling unserer
Flotte, ein Unternehmensmodellierungswerkzeug, dessen Zwillinge mit der Plattform synchronisiert
werden, und ein Nachhaltigkeits-Dashboard mit zeitabhängigen KPIs an Asset-Attributen, das den
Zwilling als einzige Datenbasis nutzt.

**Befund:**
- An den Zwilling kommen heute nur unsere Apps (Instanzschlüssel, Bindungen je Typ), das Portal
  für Personen (lesen, eigene Gruppen schreiben, Gruppentypen anlegen, zusammenführen) und lesende
  Zwillinge anderer Knoten.
- Die MCP-Tür hat drei lesende Werkzeuge.
- Für ein Programm außerhalb der Plattform gibt es keine Tür.
- Je Attribut gibt es genau einen aktuellen Wert. Zwei Zeiträume eines KPI (2024 und 2025) können
  heute nicht nebeneinander stehen.
- Einen Objekt-Status gibt es nicht.
- Zeitreihen gibt es schon, aber nur für Apps; für Personen gibt es keine Seite und kein Diagramm.
- Der Broker sendet nur dünne Ereignisse ohne Werte. Webhooks und einen Änderungs-Feed gibt es
  nicht.
- **Noch zu prüfen:** ob eine Mandanten-Verwaltung einen Zwillingsschlüssel für eine App-Instanz
  ausstellen könnte. Das misst Stufe 0, bevor eine Tür aufgeht.

**Vorschlag:**
- **Integrations-Clients:** eine neue Art Prinzipal `client:<name>` je Mandant. Die
  Mandanten-Verwaltung legt ihn im Portal an, mit Bindungen je Typ wie bei einer App und einem
  Schlüssel. Er erreicht eine versionierte Tür `/twin/v1` mit OpenAPI-Beschreibung. Es gelten
  dieselbe Schreibregel und dieselben Bindungen wie innen.
- **Lesen und Recherche:** Filter auf Werte, Blättern ohne 500er-Grenze, `?at=` mit Uhrzeit.
  Nachbarschaft, Pfade zwischen zwei Objekten, „was hängt davon ab“ für alle Typen. Export als
  JSON, JSON-LD oder GraphML für Graph-Viewer. Berechnet wird das in PostgreSQL, ohne eigene
  Graph-Datenbank.
- **Status:** am Typ erklärt, mit erlaubten Übergängen. Jeder Wechsel wird mit Grund
  festgehalten und als Ereignis gemeldet.
- **Modellieren und Synchronisieren:**
  - Objekttypen je Mandant, nur additiv.
  - Anlegen oder Finden über die eigene Kennung des Werkzeugs, ohne Doppelte.
  - Pakete, die ganz oder gar nicht geschrieben werden, und „ausmustern“ statt löschen.
  - Werte werden gegen ihre Typen geprüft.
  - Sync-Regel: Jeder schreibt nur seine eigenen Gruppen, niemand überschreibt einen anderen.
- **Werte in der Zeit:** Attribute, die ein Typ als periodisch erklärt, tragen mehrere Werte mit
  Zeitraum, Einheit und Quelle nebeneinander. Zeitreihen sind für Personen und Clients offen. Im
  Portal gibt es ein Formular „Werte mit Zeitraum“. Faustregel: Berichtszahlen sind Zeiträume,
  Messwerte sind Zeitreihen.
- **Ereignisse:** Ereignisse mit Werten für Typen, die das erlauben. Status-Ereignisse.
  Unterschriebene Webhooks für Programme draußen, mit Wiederholung. Ein Änderungs-Feed für den
  Abgleich.
- **Schreibende MCP-Werkzeuge:** als die Person, mit ihren Rechten aus dem Portal. In einen
  Assistenten kommen sie nur auf dem Weg von RFC-0119 D13: einzeln anhaken, und jeder Aufruf wird
  im Chat bestätigt.
- **AAS:** Die Formen bleiben AAS-freundlich, die AAS-Tür kommt später obendrauf.

**Stufen:**
- 0: Schlüssel-Prüfung, Client-Prinzipal, OpenAPI-Gerüst.
- 1: Lesen, Graph, Export, Feed, gemessen am Graph-Viewer über die Flotte.
- 2: Werte in der Zeit und Formular, gemessen an den Nachhaltigkeits-KPIs.
- 3: Modellieren und Synchronisieren mit Webhooks, gemessen am Modellierungswerkzeug.
- 4: Status.
- 5: Schreibende MCP-Werkzeuge und die Zwillings-Vorlage.

**Entscheidungen D1–D12 (§8)** sind offen, jede mit Empfehlung. Die wichtigsten:
- D1: überhaupt eine Tür nach außen
- D2: Clients legt die Mandanten-Verwaltung an
- D4: KPI als Zeitraum, Messwert als Zeitreihe
- D5: keine Graph-Datenbank und keine Abfragesprache jetzt
- D8: ein Modellierungswerkzeug darf Typen anlegen
- D12: Reihenfolge Lesen → Zeit → Sync

**Angenommen (22.11.):** Jörg: „Alles wie empfohlen“. D1–D12 gelten wie empfohlen. Vorgemerkt
(§4.10): Webhooks in beide Richtungen. Ein System, das nur Webhooks kennt (Modellierungswerkzeug,
Ticketsystem, IoT- oder SaaS-Plattform), schickt seine Änderungen in den Zwilling. Wie aus der
Nachricht Objekte, Gruppen, Status oder Messpunkte werden, legt der Mandant in einer Zuordnung
fest, ähnlich einem eingehenden IDoc mit Mapping. Alles läuft durch dieselbe Schreibregel. Das
wird mit Stufe 3 entworfen und eigens entschieden. Gebaut ist noch nichts.

**Stufe 0 gebaut und gemessen (22.11., §9), ohne die Portalseite:** Die Lücke aus §1.6 war echt.
Eine Mandanten-Verwaltung konnte über die Schlüsseltür für Personen Schlüssel für die Prinzipale
einer App mit Plattform-Begrenzungen ausstellen: Zwilling, Berechtigungstür und Vorgangstür.
Auf oaap-test wurden 3 von 3 ausgestellt (sofort widerrufen), und der Zwillingsschlüssel kam bis
zum Zwilling durch. Jetzt geschlossen (identity 0.6.11): 3 von 3 abgelehnt. Neu sind die
Integrations-Clients `client:<name>` (nur lesend) sowie `/twin/v1/types` und
`/twin/v1/openapi.json`. Auf oaap-test 8 von 8. Am selben Tag kam die Seite „Zugänge → Integration“
dazu (D2). Darauf legt die Mandanten-Verwaltung Clients ihres Mandanten an und entfernt sie über
einen Host-Auftrag, der nie einen Schlüssel trägt. Den Schlüssel stellt sie auf der Seite direkt bei
identity aus, und er wird einmal gezeigt. Dafür lässt identity genau eine Ausnahme zu: den
Zwillingsschlüssel eines Clients des eigenen Mandanten. Auf oaap-test 9 von 9; die Lücke bleibt
zu. Nicht geklickt: die Seite im Browser. Befund am Rande: `test_tenant_boundary`
hat 5 rote Prüfungen, schon vor dieser Änderung.

**Stufe 1 gebaut und gemessen (22.11., §10):** Die Lesewege der Tür `/twin/v1` sind da:

- Listen mit Filtern nach Werttyp und einer Blätter-Marke.
- Ein Objekt einzeln.
- Nachbarschaft und kürzeste Wege.
- Export als JSON und GraphML, ohne persönliche Attribute.
- Ein Änderungs-Feed.

Jede Antwort gilt für einen Zeitpunkt `at`, und zwar für beide Achsen: was bis dahin aufgezeichnet
war und was an dem Tag gültig war. Ein Objekt eines Typs, den der Aufrufer nicht lesen darf,
antwortet wie ein fehlendes und erscheint nie am Ende einer Kante.

Tests: 38 neue, gegen eine echte PostgreSQL. Auf oaap-test hat ein vorübergehender Client den
Flottenzwilling von außen gelesen, 15 von 15:

- 73 Knoten und 116 Kanten in 155 ms, als GraphML gleich viele.
- Die Nachbarschaft des Knotens oaap-test: 64 Knoten in 132 ms.
- Die Köder (fremder Mandant, fremder Typ, kein Schlüssel) wurden abgewiesen.

Damit ist Anwendungsfall 1 erfüllt. Nicht ausprobiert: ein echtes Graph-Viewer-Programm.

**Stufe 2 gebaut und gemessen (22.11., §11):** Werte in der Zeit.

- **Geprüfte Werte an jeder Tür:** Jeder Wert wird gegen seinen Typ geprüft, bevor etwas
  geschrieben wird. Ein falscher Wert lehnt den ganzen Schreibvorgang ab, mit einem Satz. Nur die
  Flotte verliert dabei nur den einen falschen Wert. Ein leeres Feld zählt als „kein Wert“.
- **Werte mit Zeitraum:** Ein Attributtyp kann periodisch sein, mit Einheit. Mehrere Werte stehen
  dann nebeneinander, jeder mit Zeitraum, Quelle und Güte. Überschneiden dürfen sie sich nicht;
  dieselben Grenzen korrigieren, Zurückziehen ist eine eigene Zeile, nichts wird gelöscht. Als Wert
  des Objekts gilt der Zeitraum, der jetzt läuft, sonst der zuletzt abgelaufene, mit seinen
  Grenzen.
- **Im Portal:** beim Anlegen eines Gruppentyps die Spalte „Werte mit Zeitraum“ und eine Einheit;
  auf der Objektseite das Formular „Werte mit Zeitraum“ (Jahr, Quartal, Monat oder Von–Bis), eine
  Tabelle mit Balken je Kennzahl und Messreihen als Verlaufslinien.
- **Für Clients:** Zeiträume je Objekt (mit Zeitfenster) und die Messreihen der Objekte, die sie
  lesen dürfen. Schreiben kommt mit Stufe 3.

Tests: 44 neue gegen eine echte PostgreSQL. Der Flottentest zeigt, dass alle echten Werte der
Flotte die Prüfung bestehen. Auf oaap-test 20 von 20:

- Eine Mandanten-Verwaltung hat im Portal zwei Kennzahlen mit Zeitraum angelegt.
- Am Knoten oaap-test hat sie CO₂e für 2024, 2025 und Q1 2026 eingetragen, einen Wert korrigiert
  und einen zurückgezogen. Überschneidung und Text statt Zahl wurden abgewiesen.
- Ein Client hat sie je Zeitraum gelesen.
- Alle 652 vorhandenen Werte bestehen die neue Prüfung.

Damit ist Anwendungsfall 3 erfüllt. Nicht angesehen: die Seiten im Browser. Die Flotte schreibt
auf oaap-test seit dem 15.11. nicht mehr; ihr Schreiben unter der Prüfung zeigt der Test im
Runner.
