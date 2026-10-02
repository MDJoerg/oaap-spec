# RFC-0051: Node Metrics — a Local History for the Health Page, and a Queue Toward MQTT

- **Status:** **Accepted (2026-10-02)** — Jörg took the recommendations
  of §7 as proposed. Nothing built.
- **Date:** 2026-10-02
- **Authors:** Jörg (the need: watch the new node `oaapx02`, mini
  charts, four time windows, MQTT later), Claude (facts measured in the
  reference code, design)
- **Depends on:** RFC-0011 (node profiles), RFC-0021 (fleet status),
  RFC-0032 (events and the unified namespace — the topic tree this RFC
  deliberately stays *outside* of, §5)
- **Extends:** `oaap.core.portal` (the health page), `oaap.core.host`
  (a timer on the host)
- **Driver:** The health page shows how the node is *now*. Nobody can
  see how it behaved over the last night or last week, which is the
  question that matters when a node is new.

## Summary

A small **sampler on the host** reads CPU, memory and disk once a minute
and writes them into a **local, tiered store** that keeps full detail
for hours and coarse averages for a month. The **health page** draws it
as three small charts side by side (CPU, memory, disk) with four
windows: **4 h, 24 h, 1 week, 1 month**. Every sample also goes into a
**local outbound queue** with a fixed message format, so that a later
sender can forward it to an MQTT node without changing anything that
exists. The sender itself is **not** part of this RFC.

## 1. Facts (measured in the reference code, 2026-10-02)

- The health page (`/health`, `node_values()` in `portal/app.py`) reads
  load average (1/5/15 min), available memory and the free space of the
  platform data directory **at the moment of the request**. Nothing is
  stored; there is no history anywhere on the node.
- Those readings are made *inside the portal container*. `/proc` is not
  namespaced for load and memory, so they are host values; the disk
  figure is the registry mount's filesystem.
- The host already has a periodic timer (`oaap-instance-state.timer`,
  every 2 minutes, `install.sh`). A second timer follows an existing
  pattern; no new mechanism is needed.
- A single load-average figure is **not** CPU utilisation. It says how
  many tasks queue, not how busy the processors are, and it reads
  differently on a 4-core Raspberry Pi and on a 16-core server.

## 2. What is measured

Three series, one sample per minute, taken **on the host** (not in the
portal container, which may be restarted by the very update whose effect
one wants to watch):

| Series   | Value                                              | Source                |
|----------|----------------------------------------------------|-----------------------|
| `cpu`    | utilisation of all cores in percent (0–100)        | two reads of `/proc/stat`, one second apart, or the difference to the previous sample |
| `mem`    | memory in use in percent (`1 − MemAvailable/MemTotal`) | `/proc/meminfo`  |
| `disk`   | used space of the platform data filesystem in percent | `statvfs` on `DATA_DIR` |

Load average stays on the page as a number; it is not charted. Further
series (network, per-instance, temperature) are **out of scope** and
need no format change to add (§3).

## 3. The sample — one fixed format

One line of JSON per sample, the same everywhere it appears (store,
queue, later MQTT):

```json
{"v":1,"node":"<node-id>","t":"2026-10-02T14:03:00Z","m":"cpu","x":12.4}
```

`v` the format version, `node` the node's identity, `t` the minute in
UTC, `m` the series, `x` the value. One series per line, so a new series
is a new `m` and nothing else.

## 4. The local store

**Tiered, in plain files** under `DATA_DIR/data/metrics/` — no database,
no new service:

| Tier | Resolution | Kept for | Points per series |
|------|-----------|----------|-------------------|
| raw  | 1 minute  | 4 hours  | 240               |
| 5 m  | 5 minutes | 24 hours | 288               |
| 30 m | 30 minutes| 7 days   | 336               |
| 2 h  | 2 hours   | 31 days  | 372               |

Each tier stores **mean, minimum and maximum** per interval. The maximum
is the point of the exercise: a one-minute CPU spike must not vanish
from the monthly chart because it was averaged away. Older data of a
tier is dropped when it ages out; a lower tier is filled from the tier
above it as intervals close. At roughly 1,200 points per series and
three series, the whole store is a few hundred kilobytes and is
rewritten in place — the disk is not loaded by it.

A gap (the node was off) is stored as a gap and drawn as one; it is
never filled with the last value.

## 5. The outbound queue (prepared, not sent)

Every sample is also appended to `DATA_DIR/data/metrics/outbox.jsonl`
with a running sequence number. A future sender reads from its last
acknowledged number, publishes, and only then advances — the pattern the
twin's outbox relay (RFC-0032) already uses. The queue is **bounded**
(by age, default 7 days, and by size): a broker that is unreachable for
a month loses the oldest data and keeps the node healthy; the loss is
counted and shown, not hidden.

**Topic space.** Node metrics are not tenant data. They go on their own
branch, **outside** the tenant-first tree of `oaap.events.broker` §2.2:

```
oaap-node/<node-id>/metrics/<series>
```

so that no tenant ACL (`oaap/<tenant-id>/#`) can ever match them and no
tenant client can read the operator's node. Retained, QoS 1, same
message as §3. The sender, its credentials and the broker side are a
later RFC; this one only fixes the shape so that it need not change.

## 6. The page

On `/health` (roles `server_admin` and `support`, as now), a block
**"Verlauf"** above the existing node values:

- Three small charts side by side — CPU, memory, disk — each a line of
  the mean with a faint band between minimum and maximum, a percent
  scale 0–100 and the current value in the corner.
- Four buttons for the window: **4 h · 24 h · 1 Woche · 1 Monat**
  (default 24 h), applied to all three charts together. Choosing a
  window reloads the block, not the page.
- Drawn as plain **SVG, server-rendered**, with no chart library — the
  same choice as the QR codes of the Wegweiser app. Nothing is loaded
  from outside; the page works on a node with no internet.
- On a phone the charts stack.

A node that has just been updated has little history; the chart says
"seit <Zeitpunkt>" rather than pretending to a full window.

## 7. Decisions (Jörg, 2026-10-02: all recommendations taken)

1. **CPU as real utilisation** (recommended) or as load average? The
   first is comparable between nodes of different size; the second needs
   no extra read. **Decided: utilisation.**
2. **One disk or all?** Recommended: only the data directory's
   filesystem (what the page shows today). Docker's own volume may be a
   different filesystem on some nodes. **Decided: data
   directory now, a second series later if a node shows it matters.**
3. **Retention** as in §4 (4 h / 24 h / 7 d / 31 d) — enough for
   "one week" and "one month" as asked? **Decided: as in §4.**
4. **Fleet-wide?** Build once, roll out to all five nodes so that
   `oaapx02` can be compared with the others. **Decided: yes.**
5. **The topic branch** `oaap-node/<node-id>/…` outside the tenant tree
   (§5) — **decided: that is the shape.**

## 8. Stages

1. Sampler, tiered store and the format (§2–§4), with tests on a
   simulated clock (a month of samples in seconds).
2. The chart block on the health page (§6).
3. The outbound queue (§5, writing only) — **built** (reference 0.1.175): numbered lines in `outbox.jsonl`, bounded by age and size with the loss counted, `queue_ack` deletes what a sender has delivered, `oaap metrics queue` shows it, `oaap metrics queue-purge --yes` empties it (counted as `purged`, numbering goes on).
4. *Later, own RFC:* the sender to an MQTT node.

## 9. Out of scope

Alerts and thresholds; per-instance and per-container series; a
metrics database; long-term storage beyond a month; the MQTT sender and
its credentials.

---

## Deutsche Zusammenfassung

**Worum es geht:** Die Gesundheitsseite zeigt nur den Zustand *jetzt*.
Um einen neuen Knoten wie oaapx02 zu beobachten, braucht es einen
Verlauf.

**Was vorgeschlagen wird:**
- Ein kleiner **Messlauf auf dem Host** liest jede Minute CPU-Auslastung
  (in Prozent, nicht nur die Last), Arbeitsspeicher und Plattenbelegung.
- Eine **lokale, gestaffelte Ablage** in einfachen Dateien: 1-Minuten-Werte
  für 4 Stunden, 5-Minuten-Werte für 24 Stunden, 30-Minuten-Werte für
  7 Tage, 2-Stunden-Werte für 31 Tage — je Mittel, Minimum und Maximum,
  damit Spitzen im Monatsbild nicht verschwinden. Das sind wenige hundert
  Kilobyte.
- Auf der Gesundheitsseite ein Block **„Verlauf"**: drei kleine
  Diagramme nebeneinander, vier Knöpfe (4 h, 24 h, 1 Woche, 1 Monat),
  als einfaches SVG ohne Fremdbibliothek.
- Jeder Messwert geht zusätzlich in eine **lokale Warteschlange** mit
  festem Nachrichtenformat. Ein späterer Sender kann sie gepuffert an
  MQTT weiterreichen, ohne dass sich etwas ändert. Der Sender selbst
  gehört **nicht** zu diesem RFC. Die Themen liegen bewusst **außerhalb**
  des Mandantenbaums (`oaap-node/<knoten>/metrics/<reihe>`), damit kein
  Mandant sie je lesen kann.

**Entschieden (Jörg, 02.10.2026, alle Empfehlungen übernommen):** CPU als
echt Auslastung statt Last; nur die Platte des Datenverzeichnisses; die
Aufbewahrungszeiten wie in §4; auf allen fünf Knoten ausrollen; die
Themenform `oaap-node/…` außerhalb des Mandantenbaums.

**Stand:** angenommen, nichts gebaut.
