# RFC-0083: The Weekly Report — What Happened, Summarized, Once a Week

- **Status:** Draft (2026-11-12)
- **Date:** 2026-11-12
- **Authors:** Jörg (the need: "not send certain things at once but as a
  kind of weekly report — summary and details; e.g. that a kernel upgrade
  was done, and every mail that raised an alert listed there too; maybe
  health data min/max/avg or growth per week/month/year; Markdown,
  rendered"), Claude (facts read in reference 0.1.260, design)
- **Depends on:** `oaap.core.notifications` 0.3 (lists, routing, outbox,
  log), RFC-0051 (node metrics), `oaap.core.updates` (care, reboot plan),
  `oaap.data.backup` 0.7, RFC-0010 (braked requests), RFC-0082 (alias in
  the subject)
- **Not part of this RFC:** intrusion detection (its own RFC; the report
  only counts what the brake already counts), a fleet-wide report across
  nodes (FleetView, later).

## Summary

Today every notification is a mail at the moment it happens, or nothing.
Much of what a node does is worth knowing but not worth an interruption: a
kernel was upgraded and the node rebooted at 04:15 as planned, a scanner
was braked 2 312 times, the disk grew by 3 GB, the backup ran seven times.
This RFC adds **one report per week per scope** (node and each tenant):
a summary on top, details below, written in Markdown, sent as mail
(plain text plus rendered HTML) and kept as a page in the portal. Each
routing line of a notification type gains a choice **sofort / im
Wochenbericht / beides**; critical types stay `sofort` and can only add
the report, never move into it.

## 1. Facts (read 2026-11-12, reference 0.1.260)

| Source | What it holds | How long |
|---|---|---|
| `apps/notify-log.jsonl` | every mail sent, per scope: type, op, counts — no addresses | 200 lines per scope |
| tenant log (`audit/tenant-log.jsonl`) | `reboot.planned/started/done` with the kernel, backup class changes, node identity, … | grows; read by tail |
| node metrics (RFC-0051) | cpu, mem, disk %, req, lat, tx, rx, conn — mean/min/max per interval | raw 4 h, 5 min 24 h, 30 min 7 d, **2 h 31 d — nothing older** |
| `throttle-braked.json` (identity) | braked requests per instance per hour | **24 h** |
| `apps/backup-last.json`, `backup-tenants/<id>.json` | the **last** run only | one record |
| host care (`host-care.json`) | kernel running/installed, auto-updates, advisories, images | the latest measurement |
| deploy log, fleet log | deploys, fleet polls | grows |

Consequences:

- Most sources keep **the latest state or a short window**. A weekly report
  cannot be assembled on day 7 from them — the braked counts of Monday are
  gone by Tuesday, the backup runs of the week are one record.
- Disk is a **percentage**; "growth per month/year" needs bytes, and the
  metrics store ends at 31 days.
- The example that started this: oaapx01's reboot on 2026-11-12 04:15 was
  planned on 2026-11-10 06:42 (kernel 6.12.116 installed by auto-updates),
  done in 80 s; the node's owners got **no** mail for it — the plan was made
  before notifications existed there and before the owners' address was
  set. A weekly report would have shown it; nobody had to be woken.
- The scanner on 2026-11-11 10:07 UTC (one address, `TLM-Audit-Scanner/2.0`,
  3 043 requests in one minute against `market.oaap-web…`, 2 312 braked,
  the rest 404 / login redirect / login page — nothing leaked) is visible
  today only for 24 h, as one number on the health page.

## 2. Proposal

### 2.1 A daily ledger

Once a day (the minute job, at the first run after 00:00 UTC) the node
appends **one line per scope** to `apps/report-ledger/<scope>.jsonl`:
the day's facts, already reduced — never raw records.

- **Events:** the tenant-log actions of that day that a report names
  (reboots with kernel, backup runs and their outcome, class/identity
  changes, deploys, instances created/removed, logins locked — counted).
- **Notifications:** every mail of the day from the notify log (type, op,
  when) — the report lists "all mails that raised an alert".
- **Measurements:** per series the day's min / mean / max (from the 30 min
  tier), plus **bytes**: disk used and free, the platform data directory,
  each tenant's storage (the backup's per-tenant sizes), archive size and
  duration.
- **Brake:** braked requests per instance with the number of distinct
  clients and the busiest minute (needs a small addition in identity, 2.5).

A line is a few hundred bytes; kept **3 years**, a node holds well under a
megabyte. This ledger is also what makes "growth per week / month / year"
possible: it is the only store that reaches back that far.

### 2.2 The report

Every week (default Monday 07:00 local, one setting per node) the node
writes one Markdown document per scope from the last 7 ledger lines, and
for the trend section the last 5 weeks, 12 months, 3 years where they exist.

```markdown
# Wochenbericht oaapx01 — KW 46 (09.–15.11.2026)

## Auf einen Blick
- 1 Neustart (geplant, Kernel 6.12.116), 80 s
- Backup: 7 von 7 gelungen, zuletzt 3,9 GB in 52 s
- 3 Meldungen verschickt (1 kritisch, behoben nach 2 min)
- Platte: 61 % (+2,1 GB diese Woche, +6 GB im Monat)
- 2 312 gebremste Anfragen, 1 Adresse, an einem Tag (Scanner)

## Ereignisse
| Wann | Was |
|---|---|
| Di 10.11. 06:42 | Kernel 6.12.116 installiert, Neustart geplant für Do 04:15 |
| Do 12.11. 04:15 | Neustart, zurück nach 80 s |

## Verschickte Meldungen
| Wann | Art | Verteiler | |
…

## Messwerte
| | min | Ø | max |
| CPU | 2 % | 9 % | 71 % |
…

## Wachstum
| | Woche | Monat | Jahr |
| Belegt | +2,1 GB | +6,0 GB | – (seit 3 Wochen gemessen) |
…
```

- **Summary first**, in sentences a non-technician reads; details as
  tables. A section without content is one line ("keine Ereignisse"), never
  left out silently.
- A **tenant's** report holds only that tenant: its instances, its backup,
  its mails, its storage growth, node events that touched it (a reboot), no
  other tenant's numbers and no node internals beyond that.
- Delivered as one mail (`multipart/alternative`: the Markdown as text, the
  same rendered to HTML), subject `[oaapx01] Wochenbericht KW 46`, to the
  lists routed for the new type `report.weekly`.
- Kept as a page: **Nachrichten → Berichte** lists the reports of the
  scope, newest first, rendered; kept 1 year.

### 2.3 Sofort, im Wochenbericht, beides

Each routing line (`oaap.core.notifications` 2.3) gains a delivery:
`now` (today's behaviour, default), `report` or `both`.

- `critical` types (`backup.failed`, `backup.missing`, `disk.full`,
  `instance.down`) **cannot** be set to `report` — only `now` or `both`.
  A failed backup that waits until Monday is the failure this platform
  exists to prevent.
- `report` lines put nothing in the outbox; the ledger already has the
  event.
- The report lists **every** mail that went out, whatever the delivery —
  the overview Jörg asked for ("auch alle Emails, die Alert gemeldet
  haben").
- New informational types that only make sense in the report, routed to
  it by default: `reboot.done` (with kernel), `backup.ok`, `brake.summary`.

### 2.4 What the report is not

No new alarm source: anything that needs a person **now** stays a
notification. No raw data: the ledger holds reductions. No addresses of
clients in the ledger or the report (distinct counts only; RFC-0010's
log scrubbing stands).

### 2.5 The brake, a little better (independent of the report)

From the scanner case: the health page says "2 312" and nothing else.
Identity counts per instance and hour; it would also keep, per bucket, the
number of **distinct clients** (a keyed hash, capped at 50 — "50+") and the
**busiest minute**. The health page then reads "2 312 · 1 Adresse · in einer
Minute", which says *scanner*, not *overload*. Bounded as today (instances
× 24 buckets × ≤ 50 short hashes).

Possible later (not in this RFC): answer well-known secret probes
(`/.env`, `/.git/`, `wp-config.php`, …) with 404 at the gateway without
reaching the app — needs care, because an app may legitimately serve a
path that looks like one.

## 3. Decisions asked of Jörg

- **D1 — a daily ledger kept 3 years** as the report's only source (2.1).
  *Recommendation: yes — the existing sources forget too fast.*
- **D2 — one report per scope per week**, Monday 07:00 by default, the
  day and hour a node setting. *Recommendation: yes.*
- **D3 — delivery per routing line `now` / `report` / `both`**, critical
  types never `report` only (2.3). *Recommendation: yes.*
- **D4 — tenants get their own report** with only their data.
  *Recommendation: yes, off by default per tenant until its admin routes
  `report.weekly` — a tenant who never asked must not start receiving
  mail.*
- **D5 — mail as text + HTML and a portal page "Berichte"**, kept a year.
  *Recommendation: yes.*
- **D6 — growth in bytes** (disk, data directory, per tenant) from the
  ledger; until a period is fully measured it says "seit N Tagen gemessen".
  *Recommendation: yes.*
- **D7 — the brake addition (2.5)** as a small separate step, before the
  report. *Recommendation: yes.*
- **D8 — order:** stage 1 brake addition (2.5); stage 2 ledger; stage 3
  node report (mail + page); stage 4 delivery choice and tenant reports.
  *Recommendation: as listed — the ledger must run a few weeks before a
  report can show trends, so it should start early.*

## 4. Stages and what is measured

1. **Brake** — a burst from one address shows "1 Adresse, 1 Minute" on the
   health page; a burst from 60 addresses "50+".
2. **Ledger** — after a day on oaap-test one line per scope with events,
   mails, min/mean/max and bytes; a reboot and a backup appear in it.
3. **Node report** — a forced run on oaap-test sends the report; it arrives
   (IMAP) as text and HTML, the portal page renders it; the reboot, the
   backups and every mail of the week are in it.
4. **Delivery and tenants** — `reboot.done` routed to `report` sends no
   mail but appears in the report; `backup.failed` cannot be set to
   `report`; a tenant's report holds no other tenant's data.

## 5. Out of scope

Intrusion detection; a fleet report across nodes; reports more often than
weekly (a daily report is the same machinery with another period — later,
if asked).

## Zusammenfassung (deutsch)

Heute ist jede Meldung entweder sofort eine Mail oder gar nichts. Vieles
ist wissenswert, aber keine Unterbrechung wert: Kernel aktualisiert und
planmäßig neu gestartet, ein Scanner 2 312-mal gebremst, Platte um 3 GB
gewachsen. Vorschlag: **ein Wochenbericht je Knoten und je Mandant**, oben
eine Zusammenfassung in Sätzen, darunter Tabellen (Ereignisse, alle
verschickten Meldungen, Messwerte min/Ø/max, Wachstum je Woche/Monat/Jahr),
als Markdown geschrieben, per Mail (Text + HTML) und als Portalseite
„Berichte“.

Weil die heutigen Quellen schnell vergessen (Metriken 31 Tage, Bremszähler
24 h, Backup nur der letzte Lauf), schreibt der Knoten **täglich eine Zeile
je Bereich** in ein Hauptbuch, 3 Jahre lang — nur daraus entsteht der
Bericht. Je Zuordnung im Verteiler wählt man **sofort / im Wochenbericht /
beides**; Kritisches (Backup, Platte voll, Instanz aus) bleibt immer sofort.
Nebenbei: die Bremse merkt sich künftig, wie viele Adressen es waren und in
welcher Minute — „1 Adresse, 1 Minute“ heißt Scanner, nicht Überlast.
Entscheidungen D1–D8 in §3.
