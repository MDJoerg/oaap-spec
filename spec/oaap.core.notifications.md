# oaap.core.notifications — Recipient Lists and Notifications

- **ID:** `oaap.core.notifications`
- **Version:** 0.18 (the matter **`site.check`** -- the site check found a red point that was not red in its previous run; operations, tenant, one per instance, only where both the switch *Seiten-Check* and *Hinweise zur Webseite* are on, closed by the first run without red, 2.2.2, RFC-0141 stage 2). 0.17 (the matters **`site.google`** -- Google has not fetched a watched web site for 14 days -- and **`site.notfound`** -- its people's 404 rose; operations, tenant, one per instance, only where the instance's switch *Hinweise zur Webseite* is on, 2.2.2, I-81 idea 5). 0.16 (the event **`host.upgraded`** -- a run of `oaap node care upgrade` finished, with its result; operations, node, RFC-0139 stage 2). 0.15 (the matter **`host.updates`** -- packages wait for an update on the node; operations, node, reminded every 24 h, RFC-0139 stage 1). 0.14 (the fleet's matters `node.silent`, `bridge.down`, `broker.queue`, `link.down` are **reminded daily** like critical ones -- a catalogue entry may say `remind: <hours>`; `node.silent` may now also come from an **entry** for the nodes paired through it while their hub is away, RFC-0085 A4 §18.2/§18.3; the disk forecast `disk.trend` (health, under 48 h) and `disk.soon` (critical, under 12 h), computed on the node from its own metrics, §18.7; a symbol before the subject (🔴 critical begins, 🟠 a health matter begins, 🔁 reminder, ✅ Behoben) and `Importance: high` / `X-Priority: 1` only for critical mails, §18.8; 0.13: `recipe.request`: a tenant asks the operator and the node has no request inbox, or it did not answer -- operations, node, event, RFC-0109 §13; 0.12: the report ledger keeps per tenant and day also `bytes.instances` -- the size of each instance from the history's last `du`, RFC-0108 D3; 0.11: 0.11: `idp.door` -- a broker in front of a tenant's realm is open and was not at the last reading, security, tenant and node, RFC-0091 stage 1, reference 0.1.297; 0.10: `link.down` also for an **external end** whose tunnel app says its tunnel or the target is down -- one matter per end, named `<node>/<instance>/<target>`; its subject says *Verbindung getrennt* instead of *Tunnel getrennt*, RFC-0087 §8.1, reference 0.1.288; 0.9: `Dauer` counts from when the fault began where the condition knows it -- the fleet types -- not from the matter's opening, reference 0.1.287, RFC-0087 finding b; 0.8: the fleet type `link.down` -- a broken tunnel at the hub, one matter per tunnel naming what depends on it, RFC-0087 §6, reference 0.1.285; 0.7: a lock on a name **nobody has** -- an empty one included -- is no longer mailed; it is counted and appears in the node's weekly report as *Fremde Anmeldeversuche*, 2.2.1/2.9; 0.6: the **fleet** types `node.silent`, `bridge.down`,
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
| `disk.trend` | health | node | yes | 0.14: the node's forecast says the data disk is full in under 48 hours (linear over 24 h, exponential only when the growth accelerates, the earlier counts); closes above 60 h (RFC-0085 §18.7) |
| `disk.soon` | critical | node | yes | 0.14: the same forecast under 12 hours, closes above 18 h; never report only |
| `advisory.host` | security | node | yes | host packages have open security fixes |
| `host.upgraded` | operations | node | no | a run of `oaap node care upgrade` finished: packages, Docker, seconds, containers not back, waiting reboot; or why nothing was installed -- RFC-0139 |
| `host.updates` | operations | node | yes, reminded every 24 h | packages wait for an update (counts: waiting, security, Docker; whether a reboot waits) -- RFC-0139 |
| `advisory.image` | security | tenant | yes | images of the tenant's instances have open security fixes — **one matter per tenant**, the text names the instances |
| `reboot.planned` / `.started` / `.cancelled` | operations | both | no | the reboot plan files the event |
| `bulk.halted` | operations | tenant | no | a bulk run stopped at a failed step (not a manual stop) |
| `rebuild.failed` | operations | tenant | no | a rebuild was filed `failed` |
| `confirm.pending` | operations | tenant | no | a delivery through the deploy hook waits for a person's confirmation |
| `instance.down` | health | tenant | yes | a production instance unhealthy for 5 minutes — **one matter per instance** (2.2.1) |
| `idp.door` | security | both | no | a reading of the tenant's realm (by hand or the daily one) finds a broker open that was not open at the last reading — one message per broker, naming it and the tenant's first-login policy (`oaap.core.tenant` 2.10.1, RFC-0091 §3.3) |
| `login.locked` | security | tenant | no | identity locked a login after failed attempts — one mail per tenant and minute, naming every lock (2.2.1) |
| `node.silent` | health | node | yes | on a fleet hub: a node's last `alive` is older than 5 minutes, by the node's own time — one matter per node; a node behind an entry whose bridge is down is *unknown*, not silent; nothing new opens in the fleet service's first two minutes (RFC-0085 §6.1) |
| `bridge.down` | health | node | yes | on a fleet hub: one of its own bridges has notified `0` for 5 minutes — one matter per entry, naming the nodes behind it (§6.2) |
| `broker.queue` | health | node | yes | on a fleet hub: a broker reports more than half of its `max_queued_messages` waiting (an approximation: stored minus retained messages) (§6.2) |
| `node.loss` | health | node | no | on a fleet hub: a node's own outbox reports more lost samples than a minute ago; the first sighting only sets the baseline (§6.2) |
| `hub.unreachable` | critical | node | yes | on an entry: the hub's bridge into it has been away for 10 minutes — the outside watch of the hub (§6.3) |
| `recipe.request` | operations | node | no | (0.13) a tenant's request to the operator (`oaap.core.tenant` 2.13, RFC-0109 §13) when the node names no request inbox or the inbox did not answer; `kurz` = the tenant's label, the text the request as the case would carry it (recipe, values, text, what the preview said) |
| `link.down` | health | node | yes | on a fleet hub (0.8): a tunnel whose joined state (both halves, as the twin holds them) has been `down-inner` or `down-outer` for 5 minutes — **one matter per tunnel**, however many halves report it; the text names its two ends and what depends on it, nearest first, with tenants (RFC-0087 §6). `paused` and `half` are no fault. Without a fresh report from the fleet service (3 minutes) an open matter stays open. **0.10:** also an external end whose tunnel app reports `down-tunnel` or `down-target` (`oaap.fleet.status` 0.11) for 5 minutes, one matter per end, `kurz` = `<node>/<instance>/<target>`; `paused` and `unknown` are no fault; subject *Verbindung getrennt: {kurz}* |
| `site.google` | operations | tenant | yes | (0.17) an instance whose switch *Hinweise zur Webseite* is on (`oaap.core.portal` 2.25), a production instance: Googlebot has not fetched for 14 days -- counted from its last visit or from when the switch was turned on, whichever is later; a visit closes it. **One matter per instance**, `kurz` = the days, no reminder (2.2.2) |
| `site.check` | operations | tenant | yes | (0.18) a production instance whose switches *Seiten-Check* (`oaap.core.portal` 2.27) and *Hinweise zur Webseite* are both on: the last run that judged something found a red point that was not red in the judged run before it (RFC-0141 §6). Stays open while a run finds red, closes with the first run without red; a run that could not reach the site changes nothing. One matter per instance, `kurz` = the number of red points, the text names them; no reminder, yellow never mails (2.2.2) |
| `site.notfound` | operations | tenant | yes | (0.17) the same instances: people's 404 (not known automata) of the last 7 full UTC days are at least 20 and at least twice the weekly mean of up to 28 days before them; stays open while at least 10 and 1.5 times the mean. One matter per instance, `kurz` = the count, the text names the five paths most asked for (2.2.2) |

**Closing a matter** (0.6) mails *Behoben* with a line `Dauer:` — how long
it lasted. From 0.9 that is how long the **fault** lasted where the
condition knows its start (`began`: `node.silent` from the last sign of
life, `bridge.down`, `hub.unreachable` and `link.down` from their
`since`) — so the closing mail agrees with the text of the opening one;
the earliest `began` of a matter stays. Other types count from the
matter's opening, as before. For the fleet this closing mail is the "back" message of
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
  user's tenant; API-key attempts go to the node. The text names the name
  and the client address. A name **nobody has** (an empty one included) is
  a stranger guessing, not an account at risk (0.7): it is not mailed but
  counted per local day in the notify state (`foreign_logins`: locks,
  failures, client addresses as keyed 8-digit hashes -- at most 50 --, the
  names tried -- at most 20 --, ten days kept) and reported weekly (2.9). A name is stripped of
  control characters and cut to 64 characters before it stands anywhere.
  Logins at a tenant's own realm (an external IdP) are not seen here —
  that IdP has its own lockout.

#### 2.2.2 The web site's matters (0.17, I-81 idea 5)

The minute job reads, for every production instance (not `test`, not a
rehearsal) whose record carries `site_watch: {on: true, since, by}`, its page
statistics (`site.json`, `oaap.core.portal` 2.23) -- nothing new is measured.

- **`site.google`.** Absent days = now minus the later of Googlebot's last
  visit (`bot_last`) and the switch's `since`; the matter opens at 14. A new
  site was never visited -- that is no absence on the first minute. The text
  names the last visit, if any, and three usual reasons (new and not linked,
  `noindex`, robots.txt) and points to Google's own Search Console. Only
  Googlebot counts, not Bing or another engine.
- **`site.notfound`.** The page statistics count per day `nfp`, the 404 of
  requests that are not a known automaton (a scanner probing `/wp-login.php`
  is no reason to mail), from `nfp_from` on. Compared are the last 7 full UTC
  days (today does not count: a half day would make the matter flicker) with
  the weekly mean of the up to 28 days before them that were counted; at
  least 7 such days are needed, so the first judgment comes after two weeks.
  Opens at >= 20 and >= 2 x mean, stays open at >= 10 and >= 1.5 x mean.
- Turning the switch off, or removing the instance, closes its open matters
  **without** a mail -- nobody asked to hear *Behoben* then.
- **`site.check`** (0.18). The site check (RFC-0141) keeps the last 12 runs per instance; the minute's conditions read them. A run that could not reach the site (grey) is skipped, so it neither opens nor closes. The matter opens only for a red point that is **new** -- a red that was already red in the run before does not open one when it is not open (who switches the notices on later hears the next new red, not the old one). Switching off either switch, or removing the instance, closes it without a mail.
- All link to `/instances/<name>?tab=statistik`. All may be routed to the
  weekly report only.

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
  120 s; per instance in the tenant's line as `bytes.instances`, from the
  history's last `du`, 0.12, RFC-0108), the care reading, the brake's counts per instance (with distinct
  clients and the busiest minute) -- only for yesterday. The first run on a
  node writes the six days before from what still exists; anything not
  measured is recorded as such, never invented. A tenant's line holds its
  own events, mails, own archive, storage and the brake of its instances.
  The node's line also holds that day's locks on names nobody has
  (`foreign`, 2.2.1; kept ten days, so a backfilled day has them too).
- **Report.** On the set weekday and hour (default Monday 07:00 local,
  `apps/report.json`) the node writes last week's Markdown per scope to
  `apps/reports/<scope>/<YYYY-Www>.md` (0644, a year): summary in sentences,
  then events, every mail, backup, braked requests, *Fremde Anmeldeversuche*
  (locks, failures, distinct addresses, the names tried -- an empty one as
  "(leer)"), measurements, and for the
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

**0.9 — Dauer ab der Störung:** Im Behoben steht bei den Flottenmeldungen
jetzt, wie lange die Störung selbst dauerte, nicht wie lange die Meldung
offen war. Bisher stand im Text der ersten Mail „seit 5 Minuten“, das
Behoben zählte aber erst ab dem Öffnen. Beides stimmte, passte aber nicht
zusammen. Andere Meldungen zählen weiter ab dem Öffnen.

**0.8 — Tunnel getrennt:** Die Zentrale meldet einen gestörten Tunnel
einmal (`link.down`), gleich ob außen, innen oder beide Seiten es melden,
und erst nach fünf Minuten. Die Mail nennt beide Enden und alles, was
daran hängt, von nah nach fern, mit Mandanten — Betroffenheit statt
Alarmflut. Angehalten oder halb bekannt ist keine Störung.

**0.7 — Fremde Anmeldeversuche:** Eine Sperre auf einen Namen, den es nicht
gibt (auch einen leeren), ist ein Fremder, der rät — kein Konto in Gefahr.
Dafür kommt keine Mail mehr; sie wird gezählt und steht im Wochenbericht des
Knotens (Sperren, Fehlversuche, Adressen nur als Prüfsumme, versuchte Namen).
Sperren auf echte Namen melden weiter sofort.

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

## Deutsche Zusammenfassung (0.11 — eine neue offene Tür am Anmeldedienst)

Neue Meldungsart `idp.door` (Sicherheit, Mandant und Knoten): Liest OAAP
den Realm eines Mandanten – von Hand mit `oaap idp settings` oder bei der
täglichen Lesung – und findet dort einen Broker (Google, Entra, fremder
Anmeldedienst), der offen ist und bei der letzten Lesung nicht offen war,
geht eine Meldung je Broker hinaus. Sie nennt den Broker und was eine
erste Anmeldung im Mandanten bedeutet (RFC-0091 Stufe 1).

## Deutsche Zusammenfassung (0.13 — Anfrage eines Mandanten als Nachricht)

Neue Benachrichtigung `recipe.request` (Betrieb, nur der Knoten): Ein
Mandant fragt beim Betreiber an, und der Knoten hat keinen Posteingang
für Anfragen benannt oder der Posteingang antwortet nicht. Der Text ist
derselbe, den der Vorgang trüge.

## Deutsche Zusammenfassung (0.14 — Erinnerung für die Lagen der Flotte)

Bisher kam nur eine kritische Lage täglich wieder (RFC-0080 D6). Die Lagen
der Flotte sind „Gesundheit“ und kamen deshalb nur einmal: `bridge.down`
zu oaapx01 wurde am 20.11. gemailt und dann vier Tage nicht mehr. Ein
Eintrag im Katalog darf jetzt `remind: <Stunden>` sagen; `node.silent`,
`bridge.down`, `broker.queue` und `link.down` sagen 24. Die Erinnerung ist
die bekannte („Erinnerung: …“, „Besteht weiterhin: …“) mit dem aktuellen
Text der Lage. Andere Gesundheitslagen wie `disk.full` bleiben, wie D6
entschieden hat. Neu ist auch: `node.silent` kann von einem **Eingang**
kommen, für die Knoten, die über ihn gekoppelt sind, solange ihre Zentrale
fehlt (RFC-0085 §18.3).

Dazu (0.14): Die neue Lage `disk.trend` warnt, wenn die Datenplatte nach
der Schätzung des Knotens in weniger als 48 Stunden voll ist, `disk.soon`
ist kritisch unter 12 Stunden (RFC-0085 §18.7). Im Betreff steht vorn ein
Symbol: 🔴 Kritisches beginnt, 🟠 eine Gesundheitslage beginnt, 🔁
Erinnerung, ✅ Behoben; alles andere bleibt ohne. Nur kritische Mails
tragen die Kopfzeilen `Importance: high` und `X-Priority: 1` (§18.8).

## Deutsche Zusammenfassung (0.15 — wartende Updates des Servers)

Neue Lage `host.updates` (Betrieb, nur der Knoten): offen, solange auf dem
Server Pakete auf ein Update warten, mit Erinnerung alle 24 Stunden. Die Mail
nennt die Zahl, davon Sicherheitsupdates und Docker, ob ein Neustart wartet,
und wie man nachsieht (RFC-0139 Stufe 1).

## Deutsche Zusammenfassung (0.16 — Updates eingespielt)

Neue einmalige Meldung `host.upgraded` (Betrieb, nur der Knoten): ein Lauf von
`oaap node care upgrade` ist fertig — wie viele Pakete, davon Docker, wie
lange, ob alle Container wieder laufen, ob ein Neustart wartet; oder warum
nichts eingespielt wurde (Sicherung oder apt fehlgeschlagen).

## Deutsche Zusammenfassung (0.17 — Hinweise zur Webseite)

Zwei neue Lagen (Betrieb, Mandant, je Instanz, keine Erinnerung), nur für
Produktivinstanzen, deren Schalter „Hinweise zur Webseite“ an ist:
`site.google` — Google (Googlebot) war seit 14 Tagen nicht da, gezählt ab dem
letzten Besuch, frühestens ab dem Einschalten; `site.notfound` — die 404 von
Besuchern (ohne Automaten) der letzten 7 vollen Tage sind mindestens 20 und
doppelt so viele wie im Wochenmittel davor (bis zu vier Wochen; geurteilt wird
erst nach zwei Wochen Zählung). Ausschalten schließt offene Lagen ohne Mail.
Beide dürfen nur in den Wochenbericht gehen (I-81 Idee 5).

## Deutsche Zusammenfassung (0.18 — Seiten-Check rot)

Eine neue Lage **`site.check`** (Betrieb, Mandant, je Instanz, keine
Erinnerung): Der Seiten-Check (RFC-0141) fand einen roten Punkt, der im
Lauf davor nicht rot war. Nur wenn an der Instanz **beide** Schalter an sind,
„Seiten-Check“ und „Hinweise zur Webseite“. Sie bleibt offen, solange ein
Lauf Rot findet, und schließt mit dem ersten Lauf ohne Rot. Ein Lauf, der die
Seite nicht erreicht (grau), ändert nichts. Gelb mailt nie. Ausschalten eines
der beiden Schalter schließt ohne Mail.
