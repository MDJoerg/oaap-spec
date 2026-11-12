# oaap.core.notifications — Recipient Lists and Notifications

- **ID:** `oaap.core.notifications`
- **Version:** 0.6 (0.6: the **fleet** types `node.silent`, `bridge.down`,
`broker.queue`, `node.loss`, `hub.unreachable`, and a closing mail names how
long the matter lasted, RFC-0085 stage 2; 0.5: `exposure.found` -- an instance hands out a secret file, critical, tenant and node, RFC-0084; 0.4: the **weekly report** -- a daily ledger, one report per scope, delivery `now`/`report` per routing line -- 2.9, RFC-0083; 0.3: `{knoten}` is the node's alias once one is set, `{ort}` its place, the body names both names -- RFC-0082 stage 1)
- **Maturity:** draft. 0.1 was RFC-0080 stage 1: lists, the catalogue,
  routing, the outbox, sending by mail, the delivery log, the portal
  sections and `oaap notify`. 0.2 is stage 2: `instance.down` and
  `login.locked` (2.2.1), the portal page in tabs. Telegram as a second
  channel and intrusion detection come with their own RFCs.
- **Based on:** RFC-0080 (D1–D10, accepted 2026-11-11), RFC-0072 (the
  node's mailbox and a tenant's own, `oaap.net.destinations` 2.11),
  RFC-0069 (the minute job, the reboot plan's events), RFC-0070/0071
  (advisories), RFC-0051 (node metrics), `oaap.data.backup`,
  `oaap.core.tenant` 1.7 (the tenant log)

## 1. Purpose

The platform tells the right people when something needs them: a failed
backup, a full disk, open security fixes, a planned reboot, a halted run.
Who hears what is configured, not programmed: **recipient lists** and a
**routing** per scope. A scope is the node (its `server_admin`s) or one
tenant (its `tenant_admin`s, and the `server_admin` for it).

## 2. Interface

### 2.1 Recipient lists

- A list has a `name` (1–40 characters, unique in its scope), `entries`
  and an optional `subject_prefix` (≤ 40 characters).
- An entry is `{"channel": "mail", "to": "to"|"cc"|"bcc", "address": …}`
  or `{"channel": "mail", "to": …, "role": …}`. A node's list names the
  role `server_admin` only, a tenant's list `tenant_admin` only. A role
  resolves **at sending time** to the e-mail addresses of the active
  people who hold it then (a `tenant_admin` of exactly that tenant).
- `channel` is `mail` in 0.1; any other value is refused as "not built".
- A list is kept only with at least one **To** entry, at most 25
  addresses, and no address or role twice.
- **Mandatory lists**, present without being configured, editable, never
  removable: **Serverbesitzer** at the node (at first: role
  `server_admin`, To), **Mandantenverwaltung** in every tenant (at first:
  role `tenant_admin`, To).

### 2.2 Catalogue

The platform's, fixed in this spec; a tenant cannot add a type. Each type
has a category (`critical`, `health`, `security`, `operations`), a scope,
a default subject and a fixed German body (what, the tenant, the server,
the instance, the reason, a link to the portal page).

| Type | Category | Scope | Matter | Fires when |
|---|---|---|---|---|
| `backup.failed` | critical | both | yes | the last node backup ended with an error — for a tenant only if its data is in the node archive; a tenant with its own archive hears its own run (`oaap.data.backup` 2.7) |
| `backup.missing` | critical | both | yes | a backup schedule exists and is off, or no successful backup for 26 h — never on a node declared `none` (`oaap.data.backup` 2.6) |
| `exposure.found` | critical | both | yes | an instance hands out a secret file when asked directly (`oaap.core.gateway` 0.2.22, RFC-0084) — one matter per instance, to its tenant and to the node; never only in the report |
| `disk.full` | health | node | yes | the data disk ≥ warn threshold (default 90 %), closes below warn − 2 |
| `advisory.host` | security | node | yes | host packages have open security fixes |
| `advisory.image` | security | tenant | yes | images of the tenant's instances have open security fixes — **one matter per tenant**, the text names the instances |
| `reboot.planned` / `.started` / `.cancelled` | operations | both | no | the reboot plan files the event |
| `bulk.halted` | operations | tenant | no | a bulk run stopped at a failed step (not a manual stop) |
| `rebuild.failed` | operations | tenant | no | a rebuild was filed `failed` |
| `confirm.pending` | operations | tenant | no | a delivery through the deploy hook waits for a person's confirmation |
| `instance.down` | health | tenant | yes | a production instance unhealthy for 5 minutes — **one matter per instance** (2.2.1) |
| `login.locked` | security | tenant | no | identity locked a login after failed attempts — one mail per tenant and minute, naming every lock (2.2.1) |
| `node.silent` | health | node | yes | on a fleet hub: a node's last `alive` is older than 5 minutes, by the node's own time — one matter per node; a node behind an entry whose bridge is down is *unknown*, not silent; nothing new opens in the fleet service's first two minutes (RFC-0085 §6.1) |
| `bridge.down` | health | node | yes | on a fleet hub: one of its own bridges has notified `0` for 5 minutes — one matter per entry, naming the nodes behind it (§6.2) |
| `broker.queue` | health | node | yes | on a fleet hub: a broker reports more than half of its `max_queued_messages` waiting (an approximation: stored minus retained messages) (§6.2) |
| `node.loss` | health | node | no | on a fleet hub: a node's own outbox reports more lost samples than a minute ago; the first sighting only sets the baseline (§6.2) |
| `hub.unreachable` | critical | node | yes | on an entry: the hub's bridge into it has been away for 10 minutes — the outside watch of the hub (§6.3) |

**Closing a matter** (0.6) mails *Behoben* with a line `Dauer:` — how long
it lasted. For the fleet this closing mail is the "back" message of
RFC-0085 (`node.back`, `bridge.back`); no separate type exists. The fleet's
sources are trusted only while fresh: a fleet service whose state is older
than three minutes, or not connected, keeps its open matters open, as
`instance.down` does with a stale state view.

**A node's notifications are also published** (0.6) where a metrics sender
is configured: each one, as queued, under `<root>/<node>/events/<type>`,
not retained, so that the hub sees the fleet's alerts in one place. The
hub shows them; it does not mail them again.

*Scope:* `node` — only the node hears it. `tenant` — the tenant it is
about hears it, and the node only through an explicit line for that type.
`both` — the node and every tenant each hear it under their own routing.
A node with no backup schedule at all has no `backup.missing`; the portal
says so on its own page.

#### 2.2.1 The two stage-2 sources

- **`instance.down`.** The minute job reads the container state it writes
  anyway (`apps/instance-state.json`). An instance counts when it is a
  production instance (not `test`, not a rehearsal), runs in mode
  `running` and is not in maintenance; it is down when a service is not
  `running`, is absent, or its health check says `unhealthy`. The clock
  starts at the first minute seen down and restarts when the previous
  observation is older than three minutes (the minute job paused, e.g.
  for a backup). After five minutes the matter opens. **"Unknown" is not
  "fixed":** when the container runtime could not be asked or the state
  file is older than three minutes, the open matters stay open. An
  instance removed while down closes its matter without a mail. The
  tenant is the instance's; the mail links to `/instances/<name>`.
- **`login.locked`.** Identity locks a login after 5 failed attempts within
  5 minutes (`data/identity/login-throttle.json`, keys `client|name`,
  `key|<id>`, `keyclient|client`). The host **reads** that file each minute
  — identity stays its one writer — and reports a key that reached the
  threshold, once per hour per key. A name of a known user goes to that
  user's tenant; an unknown name and API-key attempts go to the node. The
  text names the name and the client address. A name is stripped of
  control characters and cut to 64 characters before it stands anywhere.
  Logins at a tenant's own realm (an external IdP) are not seen here —
  that IdP has its own lockout.

### 2.3 Routing

- Per scope a table of lines, each keyed by a category or a type:
  `{"lists": [names], "subject": template}`.
- The type's line wins over its category's (its lists; its subject, else
  the category's, else the catalogue's). A type with no lists in either
  line goes to the mandatory list.
- At the node, a `tenant`-scoped type is heard **only** through a line
  for that type — never through its category, never through the
  mandatory list.
- A subject template may contain `{knoten}`, `{mandant}`, `{instanz}`,
  `{typ}`, `{kurz}`, `{ort}`; any other placeholder or a lone brace is refused.
- `{knoten}` is the node's **alias once one is set** (`oaap.core.host` 2.6),
  before that the external host name, else the hostname -- setting an alias
  changes every subject of the node, nothing changes before. `{ort}` is the
  node's place (may be empty). The body then says `Server: oaapx01
  (oaap.joomp.de)` and, with a place, `Ort: de/strato`. (Measured on
  oaap-test 2026-11-12: a probe before and after -- `[oaap-test.oaap-demo.duckdns.org]`
  became `[oaap-test]`, both arrived.)
  The first named list's `subject_prefix` goes in front.

### 2.4 Sending

- Every source **queues** a notification in the outbox; nothing waits for
  a mail server. Events come from one table over the tenant log
  (`audit_tenant`: `reboot.*` ok, `instance.rebuild` failed) and from the
  places named in 2.2; matters from the minute job.
- **Matters:** the minute job compares the conditions true now with the
  open matters of each scope. A matter is mailed when it **opens**, once
  more when it **closes** ("Behoben: …", with the opening short word), and
  — category `critical` only — again every 24 h while it stays open
  ("Erinnerung: …").
- **The host sends** with the scope's mailbox: the node's for the node; a
  tenant's own for the tenant (the checks of `oaap.net.destinations`
  2.11 apply), else the node's with the tenant's name as sender name.
  To and Cc stand in the headers, Bcc never. The mail carries
  `Auto-Submitted: auto-generated`.
- **Every address once**, in its strongest field (To over Cc over Bcc),
  at most 25.
- **Nobody reachable** in a tenant's lists: the notification goes to the
  node's mandatory list, with a sentence saying so — except for a `both`
  type, which the node hears under its own routing anyway; a tenant's own
  archive (`oaap.data.backup` 2.7) is not heard by the node and does fall
  back.
- **A permanent refusal is final:** a 5xx answer of the mail server (all
  recipients refused, or the message) is logged `failed` at once; recipients
  refused singly are named in the log and the mail goes to the others.
- **Limits:** a tenant 20 sendings per hour, the node 60, probes 5 per
  hour per scope. Beyond the limit: not sent, logged `limited`.
- **Retry:** a notification the server did not take for a passing reason
  (connection, 4xx) stays in the outbox and is tried every minute for one
  hour — logged once as `retry`, then `failed`. A failed notification never
  causes a notification.
- **While a backup runs** (its record says `running`, started less than six
  hours ago) the minute part waits: no matter is opened or closed, nothing
  is sent, nothing is written into `apps/`. Events queue meanwhile and go
  afterwards.
- The mail links to the portal page of the matter: `/health` for the node,
  the tenant's start page or `/store` for a tenant, `/instances/<name>`
  for an instance, `/users` for a lock.
- **Delivery log:** one line per sending and scope — time, type, op,
  lists, counts of To/Cc/Bcc, result, the server's answer. No address,
  no body. The portal shows the last 30 of a scope.

### 2.5 Who keeps what

- Node lists, routing and the disk thresholds: `server_admin`.
- A tenant's lists and routing: its `tenant_admin`, and a `server_admin`
  acting for that tenant. Every change is filed in that tenant's log
  (`notify.list.set`, `notify.list.remove`, `notify.route`,
  `notify.test`, `notify.settings`).
- At the node's own page a `server_admin` sees a tenant's lists as names
  and entry counts only (D8); the addresses are on the tenant's page.
- The host judges every portal request again: role and tenant from the
  actor's own record (`acting_tenant`), only a `server_admin` names a
  tenant, a `tenant_admin` never writes the node's scope.

### 2.6 Command line

`oaap notify show | list-set <name> --to … [--cc …] [--bcc …] [--prefix …]
| list-remove <name> | route <category|type> --lists a,b [--subject …] |
test <name> | log [--all] | settings --disk-warn N --disk-crit N | run`,
each with `--tenant <label>` (default: the node). An item of `--to/--cc/
--bcc` is an address or `rolle:server_admin` / `rolle:tenant_admin`.
`run` evaluates the conditions and sends the outbox now (the minute job
does the same).

### 2.7 Files

| File | Mode | Holds |
|---|---|---|
| `apps/notifications.json` | 0644 | lists, routing, settings per scope — the portal reads it; written only on a change by a person |
| `apps/notify-log.jsonl` | 0644 | the delivery log |
| `apps/notify-view.json` | 0644 | how many addresses each list reaches now (the portal cannot read identity's store); written only when it changes |
| `data/notify/state.json` | 0600 | open matters, hourly stamps, the last failure, since when an instance is down, which locks were reported |
| `data/notify/outbox/` | 0700 | one file per queued notification |

What changes by itself every minute lives outside `apps/`: the backup tars
`apps/` and fails when a file appears there during the copy (measured,
RFC-0080 §6). `data/notify` is not in the backup; after a restore the open
matters are opened afresh.

The portal shows next to every list how many addresses it reaches now, and
says in red **above the tabs** when the mandatory list reaches nobody.

### 2.8 The portal page

`/nachrichten` has tabs, as the instance page does (`?tab=`): **Postausgang**
(the mailbox), **Verteiler**, **Benachrichtigungen** (routing),
**Protokoll** (the last 30 sendings) and, at the node only, **Mandanten**
(each tenant's mailbox and lists as names and counts). A form returns to
its own tab; an unknown tab word shows the first.

### 2.9 The weekly report (0.4, RFC-0083)

- **Ledger.** The first minute job after local midnight appends one line per
  scope (node, each tenant) for yesterday to `apps/report-ledger/<scope>.jsonl`
  (0600, kept 3 years): the report events of the tenant log (reboots, backup
  class, node identity, tenants, instance rebuild/sideload/purge, ...), every
  line of the delivery log, for the node min/mean/max of the metrics (30 min
  tier) and the backup run that finished that day; facts that exist only as
  the current state -- bytes used/free and per tenant (`du`, bounded to
  120 s), the care reading, the brake's counts per instance (with distinct
  clients and the busiest minute) -- only for yesterday. The first run on a
  node writes the six days before from what still exists; anything not
  measured is recorded as such, never invented. A tenant's line holds its
  own events, mails, own archive, storage and the brake of its instances.
- **Report.** On the set weekday and hour (default Monday 07:00 local,
  `apps/report.json`) the node writes last week's Markdown per scope to
  `apps/reports/<scope>/<YYYY-Www>.md` (0644, a year): summary in sentences,
  then events, every mail, backup, braked requests, measurements, and for the
  node growth per week/month/year ("seit N Tagen gemessen" until measured).
  It is queued as `report.weekly` (scope `both`, each scope its own) and
  mailed as `multipart/alternative`: the Markdown as text plus the same
  rendered to HTML (every text escaped first). Subject
  `[{knoten}] Wochenbericht 2026-W46`.
- **Tenants** get a report only when their `tenant_admin` routes
  `report.weekly` to a list -- a tenant who never asked starts receiving no
  mail. The node always gets one (no line = the mandatory list).
- **Delivery.** A routing line carries `delivery`: `now` (default) or
  `report` -- no mail, a log line `result: report`, so the type appears in
  the report. `backup.failed`, `backup.missing`, `disk.full`,
  `instance.down`, `report.weekly` and the category `critical` cannot be
  `report` (refused when set, and ignored when a category line would carry
  them). The RFC's third choice "both" is `now`: the report lists every mail.
- **Command line:** `oaap report show [--week W] [--tenant L]`, `oaap report
  run [--week-of DAY] [--send]`, `oaap report ledger [--day DAY]`, `oaap report
  settings [--day mon..sun] [--at HH:MM] [--on|--off]`; `oaap notify route
  <key> --delivery now|report`.
- **Portal:** tab **Berichte** on `/nachrichten` (the scope's reports, the
  chosen one rendered; at the node the day and hour, `server_admin`); a
  column **nur im Bericht** in the routing table ("immer sofort" where it
  cannot be).

## 3. Not in 0.2

Telegram and other channels; `intrusion.suspected`; apps sending
notifications of their own; HTML, attachments; a person opting out;
lockouts at a tenant's external IdP.

## Zusammenfassung (deutsch)

Die Plattform sagt den richtigen Leuten Bescheid. **Verteiler** (Adressen
oder Rollen, unter An/Cc/Bcc) gibt es je Knoten und je Mandant; die
Pflicht-Verteiler **Serverbesitzer** und **Mandantenverwaltung** sind von
Anfang an da. Ein fester **Katalog** von Meldungsarten in vier
Kategorien wird je Verteiler **zugeordnet**, mit Betreffvorlage. Jede
Quelle legt nur in den **Ausgangskorb**; die Minutenaufgabe verschickt.
Lagen werden bei Beginn und Behebung gemeldet, Kritisches zusätzlich
täglich. Grenzen gegen Missbrauch (20/h je Mandant), eine Stunde
Wiederholung, nie eine Mail über eine gescheiterte Mail. Das Protokoll
nennt keine Adressen.

**0.4 (RFC-0083) — Wochenbericht:** Täglich eine Zeile je Bereich in ein
Tagebuch (3 Jahre); montags 07:00 (einstellbar) ein Bericht je Bereich als
Markdown — Mail mit Text und HTML, Reiter „Berichte“. Mandanten nur, wenn sie
„Wochenbericht“ einem Verteiler zuordnen. Je Zuordnung „nur im Bericht“
(keine Mail); Kritisches, volle Platte, ausgefallene Instanz nie.

**0.3 (RFC-0082):** Ist ein Alias gesetzt, steht er im Betreff
(`[oaapx01] …`); der Text nennt beide Namen und den Ort. Neuer Platzhalter
`{ort}`. Ohne Alias bleibt alles wie bisher.

**0.2 (Stufe 2):** „Instanz ausgefallen“ — eine Produktiv-Instanz, die fünf
Minuten nicht gesund ist, öffnet eine Lage je Instanz; ist die
Container-Laufzeit nicht erreichbar, bleibt sie offen (unbekannt ist nicht
behoben). „Anmeldung gesperrt“ — der Host liest die Fehlversuchsdatei von
Identity (5 in 5 Minuten) und meldet je Name einmal pro Stunde, an den
Mandanten des Benutzers, Unbekanntes an den Knoten. Die Portalseite hat
jetzt Reiter.
