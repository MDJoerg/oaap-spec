# RFC-0108: A History per Instance

- **Status:** **Accepted (2026-11-20)** — Jörg: "Angenommen. Los" (D1–D8 as
  recommended). **All three stages built the same day**: reference 0.1.322,
  `oaap.core.portal` 0.3.56, `oaap.core.notifications` 0.12. See §9.
- **Date:** 2026-11-20
- **Authors:**
  - Jörg, 2026-11-20: in a tenant's context the health page should show
    only what concerns that tenant, and for that tenant "Aussagen zum
    aktuellen Datengrößen oder Ressourcenverbrauch und Trends".
  - Claude: built the tenant health page the same day (`oaap.core.portal`
    0.3.55 §2.5, reference 0.1.321) from what the node already measures.
    It found that the node keeps **no history per instance** and wrote
    this design.
- **Depends on:**
  - RFC-0051: node metrics, its tiered store, its traffic stage 5.
  - `oaap.core.portal` 0.3.55 §2.5: the tenant health page.
  - RFC-0083: the weekly report's ledger, which already holds one size per
    tenant and day.
  - RFC-0081: per-tenant backup.
- **Changes:** RFC-0051 §9 says "a series per container or per instance"
  is out of scope. This RFC takes that sentence back for **instances**.
  Containers stay out of scope; an instance is the sum of its containers.

## Summary

The tenant health page (0.3.55) can show, per instance, only:

- its state;
- its data size, refreshed after an action;
- its traffic over the **last 60 minutes**;
- its CPU and memory **now**, and only if it is among the node's six
  busiest containers.

It cannot answer "is this app growing", "since when is it slow" or "who
uses the memory at night". This RFC keeps a **history per instance**:

- CPU, memory, network, requests, errors and duration, every minute;
- the data size, every 15 minutes.

The series use RFC-0051's tiers (4 h raw, 24 h, 7 days, 31 days). The data
size is also kept per day for as long as the weekly report keeps its
ledger.

The series are **tenant data**: they are stored by tenant, shown only in
that tenant's context, and removed with the tenant. The node page gets one
new thing from the same data: a ranking of the instances that cost the
most.

## 1. What the node measures today

Measured 2026-11-20 in the reference 0.1.321 and on `oaapx01` (8 cores,
34 containers).

| Value | Per instance? | History? | Source |
|---|---|---|---|
| CPU, memory of the machine | no, node | 31 days | `metrics` raw/5m/30m/2h |
| CPU of the busiest container | one container | 31 days (`ctop`) | `traffic.docker_stats` |
| CPU, memory per container | top 6 only | **none**, overwritten every minute | `traffic.json` |
| Network per container | **not read** | — | — |
| Requests, bytes, duration, 5xx per host | yes, via host → instance | **60 minutes** | `traffic.json` `minutes` |
| Requests via the LAN address | **not logged** | — | the base `Caddyfile` has no `log` |
| Data size of an instance directory | production only | **none**; refreshed after actions | `rehearsal-options.json` |
| Data size of a tenant | per tenant | **per day, ~3 years** | report ledger, `bytes.tenant` |
| Restarts, out of memory | yes | none; current | `instance-state.json` |

**Cost**, measured on `oaapx01`:

- `docker stats --no-stream` for all 34 containers takes **2.1 s**. The
  sampler already runs it every minute and throws away everything but the
  top six.
- `du -sk` over all 31 instance directories takes **0.14 s** with a warm
  cache. The largest is 650 MB.

## 2. The series

One sample per instance per minute, the same minute as the node sample
(RFC-0051 §2):

| Series | Unit | How |
|---|---|---|
| `cpu` | % of one core | sum over the instance's containers, from the `docker stats` the sampler already runs |
| `mem` | MB | sum over its containers, same call |
| `rx`, `tx` | KB/s | `NetIO` of the same call (one more field), difference to the last minute |
| `req` | requests per minute | the gateway access log, per host, summed over the instance's hosts (RFC-0051 §10 already counts per host and minute) |
| `err` | 5xx per minute | same |
| `lat` | ms, mean | same |
| `disk` | MB | `du -sk` of the instance directory, **every 15 minutes**, held for the minutes in between |

Rules:

- **An instance is the sum of its containers.** The containers come from
  the registry (`instance_services`), the same list that
  `instance-state.json` uses. A container that belongs to no instance
  counts for the node only, as today.
- **A sleeping instance** (standby) writes `cpu = 0` and `mem = 0`. It is
  not a gap: it is asleep, and that is a fact. A gap means "not measured".
- **Test and rehearsal instances** are measured like production. The page
  marks them; the ranking can leave them out.
- **The LAN address** is still not logged (D5).

## 3. The store

The layout is RFC-0051's: the same JSONL files and the same tiers, written
by the same `metrics sample` step. The difference is one directory per
instance, under its tenant:

```
DATA_DIR/data/metrics/tenants/<tenant-id>/<instance-key>/raw.jsonl
                                                        /5m.jsonl
                                                        /30m.jsonl
                                                        /2h.jsonl
```

- **Size:** about 30 instances × 7 series × (240 + 288 + 336 + 372)
  points comes to roughly 5–10 MB on `oaapx01` (about 37,000 JSONL lines).
  That is negligible next to
  the instances' data.
- **Long trend of the data size:** the report ledger gets one more field
  per tenant and day, `bytes.instances = {key: bytes}`, next to
  `bytes.tenant`. It is kept as long as the ledger (D3).
- **An instance that is removed:** its directory goes with it. Its last
  ledger values stay in the tenant's ledger for as long as the ledger
  keeps them (D4).
- **A tenant that is removed:** `tenants/<tenant-id>/` goes with it.
- **The portal** already mounts `data/metrics` read-only. Nothing new is
  mounted.

## 4. Tenant boundary

These series say what a tenant's apps do and when. That is tenant data, so
the RFC-0051 sentence that node metrics are not tenant data does not apply
to them.

- **Who sees an instance's series:**
  - on the tenant's health page (0.3.55 §2.5): that tenant's
    `tenant_admin`, and the node's `server_admin` and `support`;
  - on the instance page: whoever administers the instance.
- **The node page** shows a ranking (§5) with instance and tenant names.
  It is for `server_admin` and `support` only, as the node page already
  is.
- **Nothing leaves the node** in this RFC. Neither the fleet twin
  (RFC-0086) nor the MQTT branch `oaap-node/…` (RFC-0051 §5) carries
  these series (D6).
- **No content.** The series hold numbers per minute. They hold no paths,
  no users, no query strings. The access log stays the operator's file,
  as before.

## 5. The pages

**Tenant health page** (0.3.55 §2.5):

- **Table:** each instance row gets a small curve (sparkline, 24 h) next
  to CPU, memory, requests and data size. The columns "CPU jetzt" and
  "Speicher jetzt" become real values for every instance, not only the
  top six.
- **Detail:** a click on a row opens the instance's block with the
  RFC-0051 charts. These are CPU, memory, requests, errors, duration,
  network and data size, with the same window buttons (4 h · 24 h ·
  1 Woche · 1 Monat).
- **Tenant total:** a chart for the whole tenant, the sum of its
  instances, for CPU, memory and requests.

**Instance page**, tab "Diagnose": the same block for the one instance.

**Node health page:** a card **"Was kostet am meisten"**, the top 10 over
the chosen window by mean CPU, by mean memory and by data growth, each
with its tenant. With it the operator can answer "who fills the disk"
without reading 30 rows.

All charts are drawn like RFC-0051's: server-side SVG, no library,
nothing loaded from outside.

## 6. Decisions (Jörg, 2026-11-20: all as recommended)

1. **Which series.** Recommended: all seven in §2. Alternative: only
   `cpu`, `mem` and `disk`, which leaves out traffic and network.
2. **How often the data size is measured.** Recommended: every 15 minutes
   (0.14 s on `oaapx01`). Alternative: once an hour. Once a minute is not
   recommended, because `du` on a large instance runs too long.
3. **Long trend of the data size per instance in the ledger.**
   Recommended: yes, as long as the ledger keeps the tenant's size.
4. **History of removed instances.** Recommended: the minute series go
   with the instance; the ledger days stay. Alternative: delete
   everything at once.
5. **The LAN address.** Recommended: do not log it in this RFC. A home
   node's traffic then stays partly invisible, and the page says so.
   Alternative: a `log` block in the base `Caddyfile`, which is a gateway
   change of its own with its own privacy question.
6. **Fleet.** Recommended: nothing leaves the node. FleetView keeps its
   node series. A later RFC can carry tenant totals to the hub.
7. **Thresholds and alerts** ("instance uses more than 2 GB"). Not
   recommended now. The node first learns what normal is, and RFC-0080
   (notifications) is the place for alerts later.
8. **Container series** (an instance with five containers broken down).
   Recommended: no, an instance is the sum. The instance page already
   shows the current state per container.

## 7. Stages

1. **Sampler and store** (§2, §3). One step in `metrics sample`, tests on
   a simulated clock as in RFC-0051. The ledger field
   `bytes.instances`.
2. **Tenant health page and instance page** (§5): sparklines, the block
   with windows, the tenant total.
3. **The node's ranking** (§5, "Was kostet am meisten").

Each stage is rolled out to the whole fleet.

## 8. Out of scope

- alerts and thresholds (D7);
- container series (D8);
- sending outside the node (D6);
- the LAN log (D5);
- billing. These numbers are volumes, not prices, the same line RFC-0064
  drew for the AI gateway.

## Deutsche Zusammenfassung

**Ausgangslage:** Die Gesundheitsseite eines Mandanten (seit 0.1.321)
zeigt je Instanz nur Zustand und Datengröße, den Verkehr der letzten
Stunde und CPU und Speicher als Augenblickswert, und auch das nur bei den
sechs stärksten Containern des Knotens. Einen Verlauf je Instanz hat
RFC-0051 bewusst ausgeschlossen.

**Vorschlag:**
- Je Instanz jede Minute CPU, Speicher, Netz, Anfragen, Fehler und Dauer,
  alle 15 Minuten die Datengröße.
- Aufbewahrung in denselben Stufen wie die Knotenwerte, also bis
  31 Tage. Die Datengröße zusätzlich je Tag im Berichtsbuch, so lange wie
  dort die Größe des Mandanten.
- **Kosten**, gemessen auf oaapx01: Die Abfrage aller 34 Container läuft
  ohnehin schon jede Minute. Die Größenmessung aller 31 Instanzen dauert
  0,14 s. Der Speicher liegt bei etwa 5–10 MB.

**Mandantengrenze:** Die Reihen sind Daten des Mandanten. Sie liegen je
Mandant, sind nur in seinem Kontext zu sehen und verschwinden mit ihm.
Vom Knoten geht nichts weg.

**Seiten:**
- Mandanten-Gesundheit: Minikurven je Instanz, ein Klick öffnet die
  Diagramme, dazu eine Summe für den Mandanten.
- Instanzseite: dieselben Diagramme für die eine Instanz.
- Knotenseite: eine Rangliste „Was kostet am meisten“ für den Betreiber.

**Zu entscheiden (D1–D8):**
- welche Reihen;
- wie oft die Datengröße gemessen wird;
- ob die Datengröße je Instanz langfristig im Berichtsbuch landet;
- was mit den Reihen einer entfernten Instanz geschieht;
- ob Anfragen über das LAN gezählt werden;
- ob etwas an die Flotte geht;
- ob es Schwellen und Alarme gibt;
- ob Container einzeln erfasst werden.

Die Empfehlungen stehen in §6.

**Stufen:**
1. Messen und Speichern.
2. Mandanten- und Instanzseite.
3. Rangliste für den Knoten.

## 9. Built (2026-11-20, reference 0.1.322)

- **Stage 1.** `services/instance_metrics.py`: one line per instance and
  minute from what `traffic.measure` already read (`keep`: the full
  `docker stats` list, now with `NetIO`, and the minute's tally per host);
  `du -sk` every 15 minutes, held in between; RFC-0051's tiers through
  `metrics.rollup/trim/window` (which now take the series as a parameter);
  `sweep` removes the directories of instances and tenants that are gone.
  `appctl.instance_metrics_targets()` gives each instance's tenant,
  containers, hosts, data directory and sleep state. The report ledger gets
  `bytes.instances` per tenant from the last `du`.
- **Stage 2.** The tenant health page: CPU, memory and data size from the
  history (no longer the top-6 snapshot), sparklines of 24 h per row, a
  link „Verlauf“ that opens the instance's charts with the window buttons,
  and the tenant's total (CPU, memory, requests) above. The instance page
  shows the same block on the tab „Diagnose“.
- **Stage 3.** The node health page: the card „Was kostet am meisten“,
  top 10 by mean CPU, mean memory and data growth over the chosen window.
- **Tests:** `test_instance_metrics` (a month on a simulated clock, the
  sums, network deltas and restarts, sleep = 0, gaps, `du` every 15
  minutes, removal, the ledger field, `NetIO`, `keep`),
  `test_portal_navigation` (sparklines, the instance's charts, the tenant
  total, no value of another tenant, the ranking); 91 test files that touch
  portal, metrics, traffic or the ledger green.

## Deutsche Zusammenfassung (gebaut)

Angenommen wie empfohlen und am selben Tag gebaut (0.1.322). Der Knoten
misst jetzt jede Minute je Instanz CPU, Speicher, Netz, Anfragen, Fehler
und Dauer, alle 15 Minuten die Datengröße. Die Messung nutzt, was der
Knoten ohnehin liest, nur `du` kommt dazu. Die Gesundheit des Mandanten
zeigt Minikurven je Instanz und auf Klick die Diagramme, dazu die Summe
des Mandanten. Die Instanzseite zeigt dieselben Diagramme im Reiter
„Diagnose“. Die Knotenseite zeigt dem Betreiber, welche Instanzen am
meisten kosten. Das Berichtsbuch führt die Größe je Instanz täglich.
