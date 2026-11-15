# RFC-0088: The Tenant's Own Asset Universe — Apps Fill the Tenant's Twin, the Tenant Admin Is Warned

- **Status:** Proposed (2026-11-15) — decisions D1–D5 open for Jörg
- **Date:** 2026-11-15
- **Authors:** Jörg (the need, capability idea I-53: "open our graph model
  and the twins to tenant admins too — AI gateway, MCP gateway: complex
  functions that usually run quietly but carry complexity and dependencies;
  warnings before outages: expiring API tokens, provider outages, the
  lifecycle of the models in use, usage and dependencies between users,
  agents, systems. Through loose coupling asset universes arise per role
  and wish; whoever wants to see everything gets a very strong knowledge
  base"), Claude (facts read in reference 0.1.289, ai-gateway 0.7.0,
  mcp-gateway 0.9.1; design)
- **Depends on:** RFC-0087 §8.2 (the `assets` door, its first reader: the
  fleet), `oaap.data.twin` 0.6 (a twin per tenant, objects, relations with
  validity, `affected`), `oaap.core.notifications` (RFC-0080: lists,
  matters, *Behoben*), RFC-0064 (gateway volume, keys, cohorts), RFC-0065/
  0066 (MCP gateway, propagation), RFC-0067 (agents acting for a person),
  RFC-0045 (business permissions), RFC-0085 §7 (profiles for providers)
- **Not part of this RFC:** the drawing (FleetView's graph with zoom,
  RFC-0085 stage 4–5 — this RFC ends at a list page); methods on assets
  (I-51 (b)); prices (RFC-0064 keeps volume, never money); any change to
  what the fleet sees (RFC-0087 §4 stays as it is).

## Summary

RFC-0087 gave the operator a graph of the fleet with state on its edges
and *affected parties instead of alarms*. The AI gateway now names its
model names and sources at a declared door (`assets`, manifest 0.15). The
fleet reads that door sparingly — pseudonyms, no persons, no keys.

The tenant who runs the gateway needs more and is entitled to more: it is
his contract with the provider, his keys that expire, his cohort whose
seats end on Friday, his agents that act for his people. Today he learns
of each of these when something stops working.

This RFC adds **a second reader of the same door**: the node writes what a
tenant's apps name of themselves into **that tenant's own twin**
(`oaap.data.twin`, already built, one schema per tenant), and judges it
with the machinery the fleet already has — a matter after a grace time,
mailed to the tenant's own list, closed with *Behoben* and its duration.
The answer of the door grows by **fields only the tenant reader takes**;
the fleet reader's whitelist does not change. One door, two readers, each
reading by whitelist — that is the loose coupling Jörg named: every role
gets its own cut of the same graph (§6).

## 1. Facts (read 2026-11-15)

1. **Every tenant already has a twin**: a schema `twin_<tenant>` in the
   store, objects with groups per origin, relations with validity,
   `?at=`, `tree`, `affected` (`oaap.data.twin` 0.6). The fleet writes its
   twin with the same write rules (`twin_write`, origin `platform:fleet`).
2. **What the AI gateway knows** (0.7.0): keys with an optional end
   (`expires`), cohorts with an end and seats, a budget per key and its
   use, project/cost centre/application per key, sources with a traffic
   light, the upstream model id behind each model name, the last attempt
   per source (`assets.Seen`), a connection test that lists the source's
   models (`GET …/models`).
3. **What the MCP gateway knows** (0.9.1): its sources (upstream MCP
   servers), sign-ins with an end (`expires_in` from OAuth), tools per
   source, and — through RFC-0067 — agents that act for a person.
4. **Nobody knows a model's lifecycle.** A provider's model list says
   what exists today, not what is deprecated. Comparing today's list with
   the ids in use shows *vanished*, never *to be withdrawn on …*.
5. **The node already asks the door** at each status document (RFC-0087
   §8.2, `_asset_reports`), every 5 minutes for the sender.
6. **Notifications are tenant-aware**: lists belong to a tenant or the
   node (RFC-0080); a matter type has a scope.

## 2. The answer grows — fields for the tenant reader only

The door stays `assets` (manifest 0.15). Its answer becomes `v: 1` plus
**optional fields** — a reader that does not know a field ignores it,
which is already how both readers work. The fleet reader keeps its
whitelist of RFC-0087 §8.2 unchanged.

| kind | new fields (tenant reader only) | meaning |
|---|---|---|
| `source` | `light`, `checked`, `models` | traffic light; last connection test (time, ok/down); the ids the source lists, at most 300 |
| `model` | `upstream` | `[{"source", "model"}]` — the upstream ids behind the name |
| `key` *(new kind)* | `expires`, `budget`, `used`, `models`, `owner` | a key's end, budget and use, the model names it may use, its responsible person |
| `cohort` *(new kind)* | `expires`, `seats` | a cohort's end and its live seats |
| `signin` *(new kind, MCP gateway)* | `expires`, `source` | an OAuth sign-in's end, the source it opens |
| `tool` *(new kind, MCP gateway)* | `source` | a tool and the source it belongs to |
| `agent` *(new kind, RFC-0067)* | `acts_for`, `uses` | an agent, the person it acts for, the model names and tools it uses |

Never in any field: a key's value or hash, a credential, a prompt, a
tool's arguments or results, an address with a credential in it. A key is
named by its **label**, as the gateway's own pages and audit name it.

`owner` and `acts_for` are persons (§5, D3).

## 3. The second reader: the tenant's twin

- **Who writes.** The node — the same job that builds the status document
  asks the door once and hands the answer to two readers. The fleet reader
  builds the `app` row; the **tenant reader** writes into the twin of the
  instance's tenant, origin `platform:assets`, one object per asset
  (source key `<instance>/<kind>/<name>`), relations `assetOf`,
  `assetUses`, `assetVia`, plus `keyMay` (key → model name), `toolOf`
  (tool → source), `actsFor` (agent → person object, D3). An asset no
  longer named is `removed`, its relations closed — history stays, as in
  the fleet. *(D1: the node writes; alternative: each app writes its own
  objects through `oaap.data.twin` as owner.)*
- **The tenant's twin gets the platform's types** once (a data model
  `oaap-assets` registered per tenant on first use, as `oaap fleet hub
  twin` does for the fleet).
- **State over time**: a source's and a model name's state as a text
  series (RFC-0086), so "when was the gaming PC unreachable last week"
  has an answer in the tenant's own world.
- **Only for tenants who want it** *(D2)*: a tenant setting `assets: on|off`
  on the portal page "Flotte" beside the disclosure level; default `on`
  for tenants with an app that has the door.

## 4. Warnings in the tenant

The fleet's machine, scoped to the tenant: a condition must hold for its
grace time, then **one matter** opens and goes to the tenant's list; when
it no longer holds, *Behoben* with the duration from the condition's
start. New matter types (`oaap.core.notifications`), scope `tenant`:

| type | condition | grace |
|---|---|---|
| `asset.expiring` | a key, cohort or sign-in ends within 14 days (7, 1 — the matter's text says which threshold) | none; reopened per threshold |
| `asset.down` | a source `down` (its last attempts failed) | 10 minutes |
| `asset.unserved` | a model name with no reachable source (all `down`) — names the keys and agents that use it | 5 minutes |
| `asset.budget` | a key at ≥ 90 % of its budget | none |
| `asset.vanished` | an upstream id in use is missing from its source's model list | two checks in a row |

Each matter names **what depends on it** by the twin's `affected`: the
source down → the model names → the keys and cohorts allowed to use them
→ the agents using those (and, with D3, the persons). One outage, one
mail — the rule of RFC-0087 §6, now in the tenant.

`asset.vanished` is the honest part of "lifecycle": it is seen the day a
provider removes a model, not before. An announced withdrawal date needs
a source of its own (a provider's deprecation list), **out of this RFC**
*(D4: later as an optional catalogue per provider)*.

## 5. Who sees what

- `tenant_admin`: the whole universe of the tenant, persons included.
- Other roles: nothing by default; later through business permissions
  (RFC-0045) — e.g. a cost-centre owner sees the keys of his cost centre.
- **Persons in the graph** *(D3)*: a key's responsible person and an
  agent's principal are personal data. Recommended: a person object per
  identity UUID (RFC-0040), title = display name, visible to
  `tenant_admin` only, removed with the user (RFC-0040 deletion) —
  alternative: keep only the label and never link a person.
- Every write by the tenant reader is ordinary twin history (who: the
  platform, origin `platform:assets`); reading it is a twin read with the
  usual audit.

## 6. Universes — one graph, a cut per role

| who | sees | from |
|---|---|---|
| tenant | its own assets, keys, agents, persons | this RFC, the tenant's twin |
| provider (support) | what profiles grant (RFC-0085 §7) | the fleet, pseudonyms |
| operator | nodes, tunnels, destinations, apps' assets as pseudonyms | RFC-0087 |

Nobody's cut is computed from somebody else's: each reader takes from the
door what its whitelist allows. Whoever wants to see everything — a
tenant that is also its own operator — gets both cuts and, through
`owner.link` and the twin's merge (RFC-0087 §5.1), can join them.

## 7. Stages and what is measured

| Stage | Content | Measured by |
|---|---|---|
| 1 | the tenant reader: asset objects and relations in the tenant's twin, state series; the portal page "Assets" (a list per kind with state, *affected* per row) | on oaap-test, tenant fleetprobe: the stand-in gaming PC off → the tenant's source `down`, the page names the model names; a model name deleted → `removed` |
| 2 | ai-gateway 0.8.0 fills `key`, `cohort`, `upstream`, `light`, `checked`; `asset.expiring`, `asset.down`, `asset.unserved`, `asset.budget` to the tenant's list | a key with an end tomorrow → `asset.expiring` at the tenant's test list; gaming PC off 10 min → `asset.down` naming `chat-gaming` and the keys allowed to use it; on → *Behoben* |
| 3 | `asset.vanished` (model list compared at the minute check); mcp-gateway fills `signin`, `tool`; agents (RFC-0067) with D3 | a source whose list drops an id in use → `asset.vanished` after two checks; a sign-in ending → `asset.expiring` |
| 4 | the graph view (with FleetView) | — |

## 8. Decisions for Jörg

- **D1 — who writes the tenant's twin.** The node, from the door it
  already asks — *recommended* (one door, apps stay simple, the whitelist
  per reader lives in one place). Alternative: each app writes its own
  objects through `oaap.data.twin` (richer, but every app needs a twin
  client and its own rules for removal).
- **D2 — on by default?** `on` for tenants with a door-app, switchable by
  the tenant_admin — *recommended*. Alternative: off until switched on.
- **D3 — persons in the graph.** Person objects by identity UUID, visible
  to tenant_admin only, deleted with the user — *recommended*.
  Alternative: labels only, no person ever linked.
- **D4 — lifecycle.** Stage 3 `asset.vanished` only — *recommended*; a
  provider deprecation catalogue later as its own piece.
- **D5 — thresholds.** 14/7/1 days, 10/5 minutes, 90 % — *recommended*,
  per tenant adjustable later.

## Deutsche Zusammenfassung

Jörgs Gedanke (I-53): Graph und Zwilling auch für Mandanten-Admins, mit
Warnungen vor Ausfällen beim KI- und MCP-Gateway.

**Der Kern:** Dieselbe Tür `assets`, die seit RFC-0087 §8.2 die Flotte
liest, bekommt einen **zweiten Leser**. Der Knoten schreibt, was die Apps
eines Mandanten über sich sagen, in den **Zwilling dieses Mandanten**.
Den gibt es schon, ein Schema je Mandant. Die Flotte sieht dabei nicht
mehr als heute.

**Die Antwort der Tür wächst** um Felder, die nur der Mandanten-Leser
nimmt:
- Schlüssel mit Ende, Budget und Verbrauch;
- Kohorten mit Ende;
- die Modellkennung beim Anbieter;
- die Ampel und der letzte Verbindungstest;
- beim MCP-Gateway Anmeldungen mit Ablauf und Werkzeuge;
- Agenten und für wen sie handeln.

Nie dabei: Schlüsselwerte, Zugangsdaten, Prompts, Werkzeug-Inhalte.

**Warnungen im Mandanten,** an seinen eigenen Verteiler, als Lage mit
Behoben (wie in der Flotte):
- Schlüssel, Kohorte oder Anmeldung läuft in 14/7/1 Tagen ab;
- Quelle 10 Minuten gestört;
- Modellname ohne erreichbare Quelle;
- Budget zu 90 % verbraucht;
- ein genutztes Modell ist aus der Liste des Anbieters verschwunden.

Jede Meldung nennt, was daran hängt: Modellnamen, Schlüssel, Kohorten,
Agenten.

**Lebenszyklus ehrlich:** Wir sehen, wenn ein Modell verschwunden ist,
nicht vorher. Eine Abkündigungsliste wäre eine eigene Quelle (später).

**Sichtbarkeit:** Der tenant_admin sieht alles, andere Rollen später
über fachliche Berechtigungen. Personen (Verantwortliche von Schlüsseln,
Auftraggeber von Agenten) nur für den tenant_admin, gelöscht mit dem
Benutzer.

**Universen:** ein Graph, ein Ausschnitt je Rolle. Der Mandant sieht
seine Welt, der Dienstleister, was Profile freigeben, der Betreiber die
Flotte mit Pseudonymen.

**Stufen:**
1. Leser und Seite „Assets“.
2. Schlüssel, Kohorten und die ersten Warnungen.
3. „Verschwunden“, MCP-Gateway, Agenten.
4. Graph-Ansicht.

**Entscheidungen D1–D5** (alle mit Empfehlung):
- D1: Der Knoten schreibt.
- D2: standardmäßig an.
- D3: Personen nur für den tenant_admin.
- D4: Lebenszyklus erst als „verschwunden“.
- D5: Schwellen wie oben.
