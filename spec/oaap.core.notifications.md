# oaap.core.notifications — Recipient Lists and Notifications

- **ID:** `oaap.core.notifications`
- **Version:** 0.2
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
| `backup.failed` | critical | both | yes | the last node backup ended with an error |
| `backup.missing` | critical | node | yes | a backup schedule exists and is off, or no successful backup for 26 h — never on a node declared `none` (`oaap.data.backup` 2.6) |
| `disk.full` | health | node | yes | the data disk ≥ warn threshold (default 90 %), closes below warn − 2 |
| `advisory.host` | security | node | yes | host packages have open security fixes |
| `advisory.image` | security | tenant | yes | images of the tenant's instances have open security fixes — **one matter per tenant**, the text names the instances |
| `reboot.planned` / `.started` / `.cancelled` | operations | both | no | the reboot plan files the event |
| `bulk.halted` | operations | tenant | no | a bulk run stopped at a failed step (not a manual stop) |
| `rebuild.failed` | operations | tenant | no | a rebuild was filed `failed` |
| `confirm.pending` | operations | tenant | no | a delivery through the deploy hook waits for a person's confirmation |
| `instance.down` | health | tenant | yes | a production instance unhealthy for 5 minutes — **one matter per instance** (2.2.1) |
| `login.locked` | security | tenant | no | identity locked a login after failed attempts — one mail per tenant and minute, naming every lock (2.2.1) |

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
  `{typ}`, `{kurz}`; any other placeholder or a lone brace is refused.
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
  type, which the node hears under its own routing anyway.
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

**0.2 (Stufe 2):** „Instanz ausgefallen“ — eine Produktiv-Instanz, die fünf
Minuten nicht gesund ist, öffnet eine Lage je Instanz; ist die
Container-Laufzeit nicht erreichbar, bleibt sie offen (unbekannt ist nicht
behoben). „Anmeldung gesperrt“ — der Host liest die Fehlversuchsdatei von
Identity (5 in 5 Minuten) und meldet je Name einmal pro Stunde, an den
Mandanten des Benutzers, Unbekanntes an den Knoten. Die Portalseite hat
jetzt Reiter.
