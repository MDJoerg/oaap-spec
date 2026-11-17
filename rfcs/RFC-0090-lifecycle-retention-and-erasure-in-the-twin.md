# RFC-0090: Lifecycle, Retention and Erasure in the Twin — Measure the Growth, Keep the Hull, Archive the Details

- **Status:** **Draft (2026-11-17)** — D1–D10 open, each with a
  recommendation; nothing built (Jörg: "RFC schreiben, aber noch nicht
  umsetzen")
- **Date:** 2026-11-17
- **Authors:** Jörg (the need, capability idea I-54: "the real Industry 4.0
  twin is immortal and has a lifecycle; a dissolved node could be immortal
  or simply deleted. A figure for how much space the twin takes and how it
  grows, a small health page that shows the periodic growth, the total size
  and how the data spreads over objects no longer relevant to their
  lifecycle. Select twins that have not lived for X months, back up all
  their details, then delete them — the object itself stays, like an
  external end: key, title, lifecycle, relations. Restoring comes later.
  Several independent universes with wormholes, a research tool outside
  OAAP. Everything at one place for the owner of the fleet, but third
  parties — support partners, customers taking part of the support, the
  tenant admin with a right to their own health data including history —
  must fit too"), Claude (facts measured on the hub and on the outer node,
  design)
- **Depends on:** `oaap.data.twin` 0.7 (append-only tables, merge, the
  remote reader), `oaap.data.model` 0.2 (types, semantic IDs),
  RFC-0086 (time series with named retention policies — the model for this
  RFC), RFC-0087 (the external end, half-edges, disclosure levels),
  RFC-0088 (the tenant reader of the `assets` door, persons by UUID),
  RFC-0085 (hub, entry, service-provider profiles), RFC-0029/0081 (backup
  generations and classes), RFC-0053 (the vault)
- **Not part of this RFC:** the research tool across universes (outside
  OAAP by Jörg's own framing — this RFC only names what the platform owes
  it); restoring an archive (named, staged last, not designed in detail);
  the AAS repository API; a dataspace layer; restricted groups
  (`oaap.data.twin` D7, a separate question of *who reads*, not *how long*).

## Summary

The twin keeps everything forever. That was a deliberate choice
(RFC-0031 D5, "recorded time always") and it is the right default for an
asset's identity — but it is now the only store on the platform without
any notion of time. The time series beside it already drop what is past
its policy; the twin cannot even say how big it is.

This RFC adds four things, in this order:

1. **Measure** — size, growth and "objects no longer alive" per twin, as a
   page and as time series, so every later decision rests on numbers.
2. **A state door for ordinary apps** — today an app can report only
   `model` and `source` assets; an app like a hub with its clients has no
   way to say how its own parts are. One new asset kind fixes that.
3. **Retention classes per object type** — *immortal*, *lifecycle*,
   *transient* — and the condensing of superseded history.
4. **Hull, archive and erasure** — an object that has not lived for a
   while keeps its key, title, lifecycle and relations; its details go into
   an archive file and leave the database. A real erasure exists, is
   explicit, and leaves a trace without content.

Restoring an archive — into its own "old data" universe — is the fifth
stage and only sketched.

## 1. Facts (measured 2026-11-17)

**The tables.** Every tenant twin is a Postgres schema `twin_<tenant id>`
with `objects`, `source_keys`, `groups`, `attributes`, `relations`,
`activities`, `events`, `aliases`, plus `states` and `relay_watermark` for
the outbox relay. Attributes, relations and activities are append-only: a
change writes a new row and marks the old one `superseded_by`; nothing is
ever deleted (`oaap.data.twin` §2.3). There is no delete route, no
retention, no size report.

**The hub twin after four days of real fleet observation** (tenant
`oaap-ops` on the internal hub, six nodes, written by `platform:fleet`):

| | |
|---|---|
| objects | 167 (82 instances, 46 tenants, 20 assets, 6 nodes, 5 destinations, 3 brokers, 3 external ends, 2 tunnels) |
| attribute rows | 3 503, of which **2 289 (65 %) already superseded** |
| new attribute rows per day | ~1 000 (969 / 1 235 / 1 024 on 14.–16.11.) |
| events (outbox) per day | ~950, the same again in `states` |
| schema size | **5.0 MB** after four days → roughly 1.2 MB a day, ~450 MB a year at today's fleet |
| time series beside it | 27 MB (bounded by RFC-0086 policies) |
| whole store database | 43 MB |

So the twin is small today and grows linearly with how often states
change, not with how many objects exist. Two thirds of what it holds is
history of values that have since changed.

**What already has a lifecycle.** The fleet writer marks what disappeared
from a node's status document `removed` — "the record and its history
stay" (`fleet_sink`); a silent node becomes `silent`. A removed instance is
therefore kept forever with every value it ever had. RFC-0087 introduced
the **external end**: an object that stands for something outside the
fleet with nothing but a key, a title and a link — exactly the shape of a
hull this RFC asks for.

**What already has retention.** RFC-0086's time series: named policies
(`standard` raw 7 days, 5 min 31 days, 1 h 400 days, 1 day 10 years;
`short`; `long`), enforced by dropping partitions. The policy is named by
whoever writes the series, never configured freely.

**What already leaves the database.** A tenant archive (`oaap backup
create --tenant`) contains `pg_dump -n twin_<id>` of that tenant's twin
schema; node archives are kept in generations (RFC-0029), classed
(RFC-0081) and pulled by the vault (RFC-0053). An archive of single
objects does not exist.

**A promise without a mechanism.** RFC-0088 D3 says persons in the tenant
graph are "deleted with the user". With an append-only twin that has no
delete, this cannot be kept today; RFC-0088 stage 3 (persons) is not built,
so nothing is broken yet — but it must not be built before this RFC.

**The outer node since this morning.** `store` was switched on on the
outer node on 2026-11-17 (Jörg). Within a minute the RFC-0088 reader wrote
the assets of two tenants into their own twins (one with six assets, one
with a model name whose source is unknown). From now on data accumulates
there too.

**Ordinary apps cannot report their state.** The `assets` door
(`oaap.apps.runtime` 2.34) knows the kinds `model` and `source`, made for
gateways; "the list grows by this specification, never by an app". A
business app with a backend hub and clients — the case that started this
RFC — has no kind for "my connection to the hub", "my sync queue", "my
devices".

## 2. Three kinds of twin data — retention classes

Not everything in a twin has the same right to live. The class belongs to
the **object type**, declared by whoever ships the type, with a tenant
override *(D1, D2)*:

| Class | Meaning | Example | What happens with time |
|---|---|---|---|
| `immortal` | the asset itself; its identity never ends | a machine, a building, a customer company | nothing is ever condensed or archived automatically; erasure only explicitly |
| `lifecycle` *(default)* | lives, ends, is then of historical interest | a fleet node, an instance, a project, a contract | after it has **ended** and not lived for *N* months: hull + archive (§5) |
| `transient` | a state in passing | an asset's current state, a tunnel's half, a queue length | superseded values older than *M* days are condensed (§4); numeric values belong in a time series anyway |

- **When does an object "live"?** It lives while any origin writes to it.
  It has **ended** when its lifecycle attribute says so (`removed`,
  `retired`, `closed` — the type names its end words) or when nothing has
  written to it for *N* months. The type declares its end words; the
  platform does not guess them.
- **Declared in `data_model`** as `object_types[].retention: immortal |
  lifecycle | transient` and, for `lifecycle`, `ends_with: [...]` — an
  additive manifest field (0.16). The platform's own fleet and asset types
  get their class in their own model module.
- **A tenant may change the class of a type for its own twin** *(D2)* —
  a tenant that must keep project records for ten years makes `Projekt`
  immortal; one that wants no history of instances makes them transient.

## 3. Measure first — the twin's health page

Stage 1, and the precondition for everything else: nobody should archive
or delete before they can see what it would free.

- **Per twin** (per tenant schema): total size; rows per table; share of
  superseded rows; new rows per day over the last 7 and 31 days; objects
  per type with their class; objects **ended** or **not alive for 3/6/12
  months**, with the size their details take.
- **As time series** on the node object (RFC-0086, policy `standard`):
  `twin.bytes`, `twin.rows`, `twin.superseded_ratio` per tenant twin — so
  growth is a curve, not a guess, and FleetView can show it.
- **The page** "Zwilling" in the portal (*Katalog & Daten*): the
  `tenant_admin` sees their own twin; the `server_admin` sees all twins of
  the node; the hub shows the sum per node from the status document — sizes
  and counts only, never content *(D10)*.
- **The sentence that makes a deletion tempting**: "312 objects have not
  lived for 12 months; their details take 41 MB (63 % of this twin)."

## 4. Condensing superseded history (`transient`)

Two thirds of the hub twin are superseded values. For a `transient` type,
superseded **attribute** rows older than *M* days *(D4, recommended 31)*
are condensed to **one value per day** — the last one of that day — and
the rest deleted. A numeric attribute that changes often is a sign it
belongs in a time series; the page says so.

- Relations and activities are never condensed; they are structure, not
  measurement.
- Condensing writes one `events` row per run and type ("condensed 1 840
  rows of FleetInstance older than 31 days"), never per row.
- `?at=` keeps working: it answers with the day's last value, and says
  `condensed: true` for a point in time that falls into a condensed day.

## 5. Hull and archive (`lifecycle`)

An object of a `lifecycle` type that has **ended** and not lived for *N*
months *(D3, recommended 12; for the platform's fleet types 6)* becomes a
**hull**:

- **What stays in the database:** the object row (id, type, title), its
  source keys, its lifecycle attribute and the date it ended, its current
  **relations** in both directions, and `archived_at` plus an **archive
  reference**. That is the external end of RFC-0087 from the inside: the
  graph stays whole, a path through the object still exists, and a
  research tool still finds it by key.
- **What leaves:** every group with its full attribute, relation and
  activity history, the object's `events` and `states` rows. They go into
  an **archive file**: one JSON document per object (header, groups,
  complete history with `recorded_at`/`recorded_by`, relations,
  activities), collected per run into a file with a manifest and a SHA-256
  per object *(D5)*. The same format is the import format of stage 5 and
  the exchange format between universes (§8).
- **Where the file goes:** into the node's backup area as its own backup
  class `archive` (RFC-0081), pulled by the vault like every archive; the
  tenant's archive of the twin lies with that tenant. A run never deletes
  before the file is written, read back and its checksums match.
- **Reading a hull** answers the header, the relations and
  `archived: {at, ref}`; `?at=` before `archived_at` answers "archived —
  see ref" instead of a wrong empty object.
- **Writing to a hull** *(D7)*: an origin that writes to it again
  **revives** it — a new life with the same id and source keys; the archive
  stays where it is and is named on the object. A fleet node that comes
  back after a year is the same node, with a gap.
- **Selection is a human act in stage 4**, automatic only once the
  numbers of stage 1 have been watched for a while: the page proposes,
  the `tenant_admin` (own twin) or `server_admin` (platform types) starts
  the run, with a preview of objects, rows and megabytes.

## 6. Erasure — really gone, with a trace

Distinct from archiving: the details are not kept anywhere the platform
controls.

- **Who:** the `tenant_admin` for their own tenant's twin, the
  `server_admin` for types written by the platform; always explicit, with
  a preview and the object's title typed as confirmation *(D6)*.
- **What:** the object's groups, history, events, `states` rows, its
  retained MQTT messages on the twin's topic tree (the relay published
  them retained), and — on request — the hull itself. A merged-away id
  that pointed to it stops answering.
- **The trace:** one row in an `erasures` table — when, by whom, type,
  number of objects and rows, the reason given — **never** the title, the
  key or any value. "Something of type X was erased on day Y by Z" is the
  most the platform may still know.
- **Persons** (RFC-0088 D3): deleting a user erases their person objects
  in every tenant twin of the node by this path. RFC-0088 stage 3 waits for
  this.
- **What erasure cannot reach, said plainly:** backup generations made
  before the erasure keep the data until they expire (RFC-0029); an
  archive file already pulled by the vault is gone from the node's reach;
  a copy a person made is theirs. The page names the date until which
  backups may still hold it.
- **Up the chain** *(D9)*: if the erased object was disclosed to the hub
  (RFC-0087 levels *pseudonym* or *names*), the node's next status document
  carries an erasure note (type and pseudonymous key only) and the hub
  erases its copy by the same rule. Down the chain nothing is needed —
  the hub never writes into a node's twin.

## 7. A state door for ordinary apps

So that an app like a business hub with clients can deliver its own
health, as the gateways already do:

- **One new kind for the `assets` door** *(D8)*: `component` — a part of
  the app the operator should know about: its connection to a backend, a
  queue, a device class, a scheduled job. Fields as for the other kinds:
  `name`, `state` (`ok` / `down` / `idle`), `uses` (other components or
  sources of the same answer), `destination` (when the part reaches out
  through a bound destination). Optional `since` (ISO time of the last
  state change). Names and states only — no counts of persons, no
  addresses, no content.
- **Readers as today:** the fleet takes what `oaap.fleet.status` rule 5
  and the node's disclosure level allow; the tenant reader (RFC-0088)
  writes `component` assets into the tenant's twin as `transient` objects
  with a text series `state`, related to the instance — so a hub and its
  apps grow together through `uses` and `destination` exactly as the AI
  chain does.
- **Warnings** reuse RFC-0088 `asset.down` (10 minutes down), with the
  affected parties read backwards along `uses`.
- **Manifest:** nothing new — the door exists since 0.15; a node that does
  not know `component` ignores such entries (it already ignores unknown
  kinds).

## 8. Universes, wormholes and the chain

This RFC builds none of it but keeps every variant open. What the platform
owes them:

- **A universe is a twin store with its own owner** — a tenant twin on a
  node, the hub twin, an archive restored on its own, a twin outside OAAP
  entirely. They are independent; nothing is copied between them except by
  an explicit reader or an archive file.
- **Wormholes are shared keys.** Two universes meet where an object carries
  the same **semantic type** (`semantic_iri`, `oaap.data.model` 0.2 §2.9)
  and the same **source key**. The platform's duty is to keep both stable
  and exportable: source keys are never rewritten, semantic IDs survive
  hull and archive, and the archive format carries both.
- **Reading from outside** uses what exists: the remote reader
  (`oaap.data.twin` §2.14, a key scoped to `oaap.twin`) and the hub's read
  keys for service providers (RFC-0085 §7). An external research tool may
  read the fleet universe and a tenant's own universe side by side and join
  them by key — the joining is the tool's, not the platform's.
- **The chain.** A node's tenant twin keeps the detail (with its classes),
  the hub keeps what the node disclosed, for longer. A node twin is *not*
  merely a buffer: a `tenant_admin` needs their history when the hub or the
  bridge is away, and a customer who takes over part of the support reads
  their own node, not the operator's hub. What is only in transit (the
  three buffers of RFC-0085) stays a buffer.
- **Who sees what** stays as decided: the owner of the fleet sees
  everything their nodes disclose at level *names*; a service provider sees
  what a profile gives; a `tenant_admin` sees their tenant's twin on the
  node, with history; nobody sees across tenants.

## 9. Stages and what is measured

1. **Measure** (§3): size and growth per twin, the page, the time series,
   the sum at the hub. Measured on the test node with an artificial twin,
   then read on the hub and the outer node.
2. **Component kind** (§7): the door kind, the tenant reader, `asset.down`
   for components. Measured with a probe app; then offered to the external
   business app (BDT) in its briefing.
3. **Classes and condensing** (§2, §4): the manifest field, the defaults,
   the tenant override, condensing for `transient`, `?at=` with
   `condensed`. Measured against PostgreSQL with a copy of the hub twin
   (before/after size, `?at=` answers).
4. **Hull, archive, erasure** (§5, §6): runs started by a person, archive
   file with checksums read back before deleting, the `erasures` trace,
   erasure up the chain, persons on user deletion. Measured on the test
   node: archive → delete → read hull → revive → erase.
5. **Restore** (later): an archive file into a twin of its own ("old
   data" universe), read-only, reachable by the remote reader.

## 10. Decisions for Jörg

- **D1 — three classes** `immortal` / `lifecycle` / `transient`, per
  object type, default `lifecycle`. *Recommended.*
- **D2 — who sets the class.** The type's author declares it; the
  `tenant_admin` may change it for their own twin (both ways); the
  platform's own types by the `server_admin`. *Recommended.*
- **D3 — when a `lifecycle` object becomes a hull.** Ended and not lived
  for 12 months; the platform's fleet types 6 months; per tenant and type
  adjustable. Proposed by the page, started by a person until the numbers
  justify automatic runs. *Recommended.*
- **D4 — condensing `transient` history** after 31 days to one value per
  day; relations and activities never. *Recommended.*
- **D5 — archive format and place.** One JSON document per object with
  the full history, a manifest with SHA-256 per object; backup class
  `archive`, pulled by the vault; the same format later for import and for
  exchange between universes. *Recommended.*
- **D6 — erasure** by `tenant_admin` (own twin) or `server_admin`
  (platform types), with preview and typed confirmation, a content-free
  trace in `erasures`, retained MQTT messages cleared, the backup date
  named honestly. No four-eyes rule in this RFC (one owner today; the
  question returns with real customers). *Recommended.*
- **D7 — the hull keeps its relations, a write revives it.** Same id,
  same keys, a new life; the archive stays separate. *Recommended* —
  the alternative (refuse writes until restored) would make a returning
  node a second object.
- **D8 — the state door for apps** as a new `assets` kind `component`,
  not a new door. *Recommended* — one door, one reader, one warning path.
- **D9 — erasure travels up the chain** to the hub's copy through an
  erasure note in the status document. *Recommended.*
- **D10 — the page.** `tenant_admin` own twin, `server_admin` the node's
  twins, the hub the sums per node; sizes and counts only. *Recommended.*

## Deutsche Zusammenfassung

**Worum es geht.** Der Zwilling hält alles für immer. Für die Identität
eines Assets ist das richtig, aber er ist jetzt der einzige Speicher der
Plattform ohne Zeitbegriff. Die Zeitreihen daneben werfen weg, was über
ihre Frist hinaus ist. Der Zwilling kann nicht einmal sagen, wie groß er
ist.

**Gemessen (17.11.).** Der Flottenzwilling in der Zentrale hat nach vier
Tagen 167 Objekte und 3 503 Attributzeilen. **65 % davon sind schon
überholt**, also alte Werte, die sich inzwischen geändert haben. Pro Tag
kommen rund 1 000 Zeilen dazu. Das sind 5 MB, hochgerechnet etwa 450 MB im
Jahr bei der heutigen Flotte. Klein, aber linear wachsend mit jeder
Zustandsänderung. Auf dem äußeren Knoten läuft `store` seit heute früh;
dort schreibt der Knoten seitdem die Assets zweier Mandanten in deren
Zwillinge. RFC-0088 verspricht „Personen werden mit dem Benutzer
gelöscht“. Das ist heute nicht einlösbar, deshalb darf Stufe 3 von
RFC-0088 erst nach diesem RFC kommen.

**Drei Klassen je Objekttyp:**

- *unsterblich*: das Asset selbst;
- *Lebenszyklus*, der Standard: lebt, endet, ist dann Geschichte;
- *flüchtig*: Zustände im Vorbeigehen.

Wer den Typ liefert, legt die Klasse fest. Der tenant_admin darf sie für
seinen Zwilling ändern.

**Vier Stufen, eine fünfte später:**

1. **Messen:** Größe, Wachstum, „nicht mehr lebendig seit 3/6/12
   Monaten“ samt Platz. Als Seite „Zwilling“ im Portal und als
   Zeitreihe, damit FleetView das Wachstum als Kurve zeigt.
2. **Zustandstür für normale Apps:** neue Asset-Art `component`. Damit
   kann z. B. ein Hub mit seinen Clients melden, wie es seinen Teilen geht.
   Sie wächst über `uses` und Destinationen im Graphen zusammen wie die
   KI-Kette.
3. **Klassen und Verdichten:** Überholte Werte flüchtiger Typen werden
   nach 31 Tagen auf einen Wert pro Tag verdichtet.
4. **Hülle, Archiv, Löschen:**
   - Ein beendetes Objekt, das 12 Monate nicht gelebt hat (Flotte:
     6 Monate), behält Schlüssel, Titel, Lebenszyklus und Relationen.
     Seine Details gehen in eine Archivdatei mit Prüfsummen und erst
     danach aus der Datenbank.
   - Schreibt wieder jemand hinein, lebt es neu.
   - Echtes Löschen gibt es ausdrücklich. Es hinterlässt eine Spur ohne
     Inhalt, räumt auch die gespeicherten MQTT-Nachrichten weg und reicht
     bis zur Kopie in der Zentrale.
   - Der RFC sagt ehrlich, was Löschen nicht erreicht: ältere
     Sicherungen bis zu ihrem Ablauf.
5. **Einspielen** eines Archivs als eigenes „Altdaten-Universum“, später.

**Universen und Wurmlöcher.** Gebaut wird davon nichts, aber alles bleibt
offen. Die Pflicht der Plattform ist: Quellschlüssel und semantische IDs
bleiben stabil und überleben Hülle und Archiv; das Archivformat ist
zugleich Austauschformat; Lesen von außen geht über die vorhandenen
Leser. Das Recherchewerkzeug bleibt extern.

**Die Kette.** Der Knoten ist kein bloßer Puffer. Der tenant_admin
braucht seine Historie auch ohne Zentrale. Echter Puffer bleibt, was nur
durchläuft.

**Entscheidungen D1–D10**, alle mit Empfehlung:

- D1: drei Klassen.
- D2: Autor setzt, Mandant darf ändern.
- D3: 12/6 Monate, erst von Hand gestartet.
- D4: 31 Tage verdichten.
- D5: JSON je Objekt mit Prüfsumme, Sicherungsklasse `archive`.
- D6: Löschen mit Vorschau, Spur ohne Inhalt.
- D7: Hülle behält Relationen, Schreiben belebt neu.
- D8: `component` als neue Asset-Art.
- D9: Löschen wandert zur Zentrale.
- D10: Seite nach Rollen, nur Größen.
