# RFC-0080: Recipient Lists and Notifications — the Platform Tells the Right People

- **Status:** **Accepted (2026-11-11)** — Jörg: "wie empfohlen" (D1–D10). **Stage 1 built (reference 0.1.254, §6)**; `oaap.core.notifications` 0.1
- **Date:** 2026-11-11
- **Authors:** Jörg (the need: recipient lists with To/Cc/Bcc and a subject,
  different people for different kinds of message — critical errors to the
  server's owner, health to the service partner, security to a security team,
  a failed backup to a tenant's responsible people; Telegram as the next
  channel), Claude (facts read in the reference code 0.1.253, design)
- **Depends on:** RFC-0072 (the node's mailbox and a tenant's own mailbox, the
  portal page *Nachrichten*), RFC-0069 (node care: the minute job, the plan's
  events, the inbox and broker as readers of an event), RFC-0070 (advisories),
  RFC-0071 (rebuild), RFC-0051 (node metrics), `oaap.data.backup`
- **Order agreed with Jörg (2026-11-11):** (1) this RFC, (2) apps send mail
  through a tenant's mailbox (RFC-0072 stage 3), (3) incoming mail — mailboxes
  the platform reads — in its own RFC. Telegram is the next channel after mail.
- **Not part of this RFC:** detecting intrusions (§1: nothing detects them
  today — its own RFC); incoming mail; the Telegram channel itself (§2.1 only
  keeps the door open for it); apps sending notifications of their own.

## Summary

A **recipient list** has a name and one or more entries, each an e-mail
address **or a role** ("every `tenant_admin` of this tenant"), each marked
To, Cc or Bcc. The node has lists (kept by the `server_admin`), every tenant
has its own (kept by its `tenant_admin`).

The platform knows a **fixed catalogue of message types** — "backup failed",
"disk almost full", "security updates open", "reboot planned", … — each in
one of four **categories**: *critical*, *health*, *security*, *operations*.
A **routing** says which list(s) hear a category, optionally overridden per
type, each with a subject template. Whatever is routed nowhere goes to the
mandatory list **"Serverbesitzer"** (node) or **"Mandantenverwaltung"**
(tenant). Nothing is lost silently.

The **host** sends, with the mailbox of the scope (the tenant's own, else the
node's under the tenant's title). A condition is mailed **when it begins and
when it ends**, a critical one again once a day while it lasts — never every
minute. The portal page *Nachrichten* gets two sections, **Verteiler** and
**Benachrichtigungen**, with a test button and the log of what was sent.

## 1. Facts (read 2026-11-11, reference 0.1.253)

- **Mail out exists (RFC-0072):** the node's mailbox (`oaap mail set`) and a
  tenant's own mailbox (portal *Nachrichten* → *Postausgang*, spool action
  `mail`). The host already sends with `smtplib` (`mail_test`), with the
  password from the secret store no container mounts. Today only Keycloak and
  the test button send; **the platform sends no notification of its own.**
- **Every event already has one written form:** `audit_tenant(action, tenant,
  subject, result, …)` files it in a tenant's log (`oaap.core.tenant` 1.7).
  The reboot plan (RFC-0069 §2.7) passes its events to `_care_announce`, which
  files them in every tenant's log and hands them to **two readers** already:
  the operator's case inbox (`vorgaenge`, §2.7.6) and the broker (§2.7.8).
  Mail is a third reader of the same events, not a fourth way of finding them.
- **Sources that exist today:**
  - *Backup:* the nightly node backup records its last run with a failure
    sentence (`last_backup_run`, `backup_failure_reason`, 0.1.249). There is
    **no per-tenant backup** (`oaap.data.backup`: RFC-0022 D7 "not this
    version") — the node's backup holds every tenant's data.
  - *Disk, memory, CPU:* the minute sampler records percent values
    (`services/metrics.py`, series `disk`, `mem`, `cpu`). **No threshold and
    no alarm** exist.
  - *Security updates:* host packages (`services/advisories.py`, security
    candidates) and images (`_care_images`, RFC-0070/0071 "Abbild").
  - *Reboot:* `reboot.planned`, `reboot.started`, `reboot.cancelled`.
  - *Bulk runs* (portal 0.3.40): a run stops at the first failed step.
  - *Rebuild:* `instance.rebuild` with result `failed`.
  - *A widening waiting for confirmation* (I-43, RFC-0019 §3).
- **Sources that do not exist:**
  - *Intrusion:* nothing on the node recognises an attack (no log analysis, no
    fail2ban/CrowdSec-like component). A message type "intrusion suspected"
    has nothing to fire it.
  - *Login lockout:* identity blocks a name after 5 failed attempts
    (`services/identity`, `login-throttle.json`), but tells the host nothing.
  - *Instance down:* the portal's health page asks on demand; I found no
    minute job that notices a production instance staying unhealthy.
    (Read, not measured — to be verified when stage 2 is built.)

## 2. Proposal

### 2.1 Recipient lists

- Fields: `name` (unique in its scope), `entries`, optional `subject_prefix`.
- An entry: `{"channel": "mail", "to": "to"|"cc"|"bcc", "address": "…"}` or
  `{"channel": "mail", "to": …, "role": "tenant_admin"|"server_admin"}`.
  A role resolves **at sending time** to the e-mail addresses of the people
  who hold it then (from identity) — the list stays right when people change.
- `channel` is `mail` only in this version; the field exists so that a
  Telegram chat becomes an entry of the same list later without a new list
  form (Jörg, 2026-11-11: Telegram next).
- A list is valid when at least one **To** entry resolves to at least one
  address. Saving an invalid list is refused with the reason.
- **Mandatory lists**, made by the platform and not deletable, only editable:
  - node: **"Serverbesitzer"** — at first the role `server_admin`;
  - every tenant: **"Mandantenverwaltung"** — at first the role
    `tenant_admin` of that tenant.
  So a node and a tenant are notified from the first day without anybody
  configuring anything.

### 2.2 Message types and categories

The catalogue is the platform's, versioned in the spec; a tenant cannot add
types (the platform must fire them). Each type has an id, a scope, a
category, a default subject and a fixed German body with a link to the
portal page that shows the matter.

| Type | Scope | Category | Fires when | Source | Stage |
|---|---|---|---|---|---|
| `backup.failed` | node + every tenant (D5) | critical | the nightly backup ends with an error | exists | 1 |
| `backup.missing` | node | critical | no successful backup for 26 h, or the timer is off | derived | 1 |
| `disk.full` | node | health | disk ≥ 90 % (warn), ≥ 95 % (critical) | metrics + new threshold | 1 |
| `advisory.host` | node | security | security updates for host packages are open | exists | 1 |
| `advisory.image` | node + owning tenant | security | an instance's image has open security fixes | exists | 1 |
| `reboot.planned` / `.started` / `.cancelled` | node + every tenant | operations | the reboot plan changes | exists | 1 |
| `bulk.halted` | node or tenant of the run | operations | a bulk run stopped at a failed step | exists | 1 |
| `rebuild.failed` | owning tenant (+ node) | operations | a rebuild of an instance failed | exists | 1 |
| `confirm.pending` | owning tenant (+ node) | operations | a delivery waits for a widening to be confirmed | exists | 1 |
| `instance.down` | owning tenant (+ node) | health | a production instance unhealthy > 5 min | built (0.1.256) | 2 |
| `login.locked` | tenant of the user (+ node) | security | identity blocked a name | built (0.1.256) | 2 |
| `intrusion.suspected` | node | security | — nothing detects it yet | own RFC | — |

"(+ node)" means: the node's routing also sees the type, so the operator can
watch every tenant's failures if they want to; by default it is routed
nowhere at the node.

### 2.3 Routing

- Per scope a table: **category → lists**, and optionally **type → lists**
  (the type's line wins over its category's).
- Each line has a **subject template** (default from the catalogue) with
  the placeholders `{knoten}`, `{mandant}`, `{instanz}`, `{typ}`, `{kurz}`
  — nothing else is expanded, an unknown placeholder is refused at saving.
- A line can be switched **off** — except that what is switched off or
  routed nowhere falls back to the mandatory list (§2.1); the only way to
  hear nothing is to empty that list's entries down to its role, which
  always resolves.
- Default after an update: everything to the mandatory lists.

Jörg's examples, as routing at the node: *critical* → "Serverbesitzer";
*health* → "Servicepartner" (external address); *security* → "Security-Team".
At a tenant: `backup.failed` → "Backup-Verantwortliche" with To, Cc, Bcc and
the subject `[{mandant}] Backup fehlgeschlagen ({knoten})`.

### 2.4 Sending

- **The host sends**, never a container — the mailbox secret stays where it
  is. Node scope: the node's mailbox. Tenant scope: the tenant's own mailbox,
  else the node's with the tenant's title as sender name (RFC-0072 D3).
- **One function** builds and sends a notification; every source calls it
  (an event at the moment it happens, a condition from the minute job). The
  audit line and the notification come from the same call, so they cannot
  disagree about what happened.
- **Repetition:** a notification belongs to a *matter* (type + subject, e.g.
  `disk.full` on `/`). Mailed when the matter **opens**, once more when it
  **closes** ("behoben"), and — for *critical* only — again every 24 h while
  it stays open. Events without a duration (`reboot.started`) are mailed once.
- **Delivery log:** per scope the last 200 sendings (time, type, list,
  number of recipients, server answer — no addresses of Bcc entries, no
  body). A sending that fails is retried at the next minute up to one hour,
  then marked failed in the log and on the portal's start page for the
  `server_admin` — **a failed notification never triggers a notification**.
- **Limits (D9):** at most 25 resolved recipients per list, at most 20
  sendings per tenant per hour, test mails at most 5 per hour.

### 2.5 Where it is kept, who keeps it

- Node lists and routing: `server_admin`. Tenant lists and routing: its
  `tenant_admin` and the `server_admin` for it — the same rule as the
  tenant's mailbox (RFC-0072 D6).
- Stored by the host (like the mailbox: written through the spool, read by
  the portal), in the backup.
- A tenant never sees the node's lists; the node sees a tenant's lists only
  as names and counts, not addresses (D8).

### 2.6 Portal and CLI

- Page *Nachrichten* gets two sections after *Postausgang*:
  - **Verteiler:** the lists, a form (name, entries with To/Cc/Bcc, address
    or role, subject prefix), **Probe senden** (one test mail to the list,
    marked as a test), delete (not the mandatory list).
  - **Benachrichtigungen:** the routing table by category, expandable to the
    types, list choice and subject per line, and below it the delivery log.
- CLI for the node (`server_admin`): `oaap notify list|set|remove|test`,
  `oaap notify route <category|type> <list>…`, `oaap notify log`.

## 3. Decisions asked of Jörg

- **D1 — Entries may be roles as well as addresses** (agreed 2026-11-11).
- **D2 — Channel field now, only mail built; Telegram next** (agreed
  2026-11-11).
- **D3 — A fixed catalogue of types in four categories** (critical, health,
  security, operations); routing by category with an override per type.
  **Recommended:** the simple case is four lines, the special case possible.
- **D4 — Mandatory lists** "Serverbesitzer" and "Mandantenverwaltung" made by
  the platform, with the admin role in them from the start; everything routed
  nowhere goes there. **Recommended:** a node is never silent by accident.
- **D5 — A failed node backup notifies every tenant** too, because the
  tenant's data is in it and there is no per-tenant backup. **Recommended**;
  the tenant's mail says "die nächtliche Sicherung des Servers", not that
  something of theirs broke.
- **D6 — Open, closed, and daily for critical** (§2.4). **Recommended.**
  Alternative: only on opening.
- **D7 — Disk thresholds 90 % / 95 %** on the node's data disk, a node
  setting. **Recommended.**
- **D8 — Privacy between scopes** (§2.5): the node sees only names and counts
  of a tenant's lists; a node notification to an external partner names
  tenants only where the type is about one (`advisory.image`).
  **Recommended.**
- **D9 — Limits** 25 recipients per list, 20 sendings per tenant per hour, 5
  test mails per hour — a tenant admin must not turn the node's sender into a
  spam source (the reason of RFC-0072 D7). **Recommended.**
- **D10 — A new capability spec `oaap.core.notifications` 0.1** for lists,
  catalogue, routing and sending; the portal spec only describes the page.
  **Recommended:** Telegram and incoming mail will want the lists too.

## 4. Stages and what is measured

1. **Stage 1** — lists, routing, catalogue lines marked stage 1, the sending
   function, delivery log, portal sections, CLI. Measured on `oaap-test`
   against Jörg's mail server: a backup made to fail (unwritable target) →
   mail to "Serverbesitzer" and to a tenant's list with To/Cc/Bcc and its
   subject, arriving (read by IMAP); fixed → "behoben"; the disk threshold
   set low → `disk.full` opens and closes; a list without a To entry refused;
   a `tenant_admin` refused at the node's lists; the hourly limit refusing
   the 21st sending; a wrong mailbox password → logged failed, no loop.
2. **Stage 2** — `instance.down` (the minute job watches production
   instances) and `login.locked` (the host reads identity's failure table;
   identity stays its one writer — chosen over "identity tells the host",
   which would have added a second writer path), each measured by causing
   it. Built in 0.1.256, spec `oaap.core.notifications` 0.2.
3. **Telegram** as a channel of the same lists — its own RFC.
4. **Intrusion detection** — its own RFC; its type joins this catalogue
   when something can fire it.

## 5. Out of scope

- Incoming mail (the third step of the agreed order, own RFC).
- Apps sending mail (RFC-0072 stage 3, the second step).
- Apps defining notification types of their own.
- HTML mails, attachments, per-person opt-out.

## 6. Stage 1 built (2026-11-11, reference 0.1.254)

- `oaap.core.notifications` 0.1; `oaap.core.portal` 0.3.41 §2.15.
- `services/notify.py` holds the rules (catalogue, checks, routing, matters,
  limits, words) and is shared by host and portal. `appctl.py` keeps the
  files, the outbox directory, the sending, the conditions, the spool action
  `notify` and `oaap notify`.
- Sources wired: one table over `audit_tenant` (`reboot.*`, `instance.rebuild`
  failed), `bulk_run` (halted, not a manual stop), the deploy worker
  (`confirm.pending` when a delivery through the hook needs a person), and the
  minute job `oaap node care sample` (backup, disk, host and image advisories).
  `reboot.started` is sent before the machine reboots.
- Settled while building: the "Behoben" mail keeps the short word of the
  opening (not "Platte zu 89 %"); a disk matter closes only below warn − 2;
  `backup.missing` needs a schedule (a node never set up for backups is not
  alarmed daily); a tenant-scoped type reaches the node only through its own
  line; D8 is the node's overview, the tenant's own page shows its addresses
  to the `server_admin` acting for it.
- Tests: `test/test_notify.py` (rules, the way from audit line to mail, the
  fallback, limits, retry, the door, the findings below),
  `test/test_messages_portal.py` (the two sections).

### 6.1 Measured on oaap-test (2026-11-11, against Jörg's mail server, read back by IMAP)

- A real failed backup (target a 1 MB tmpfs) -> within the minute one mail to
  the node's "Serverbesitzer" and one to vuebung's "Backup-Verantwortliche":
  subject `[Backup] Verein Uebung: Backup fehlgeschlagen (<node>)`, sender name
  the tenant's, `To` and `Cc` in the headers, **no Bcc header**, the reason in
  the text, the link to the tenant's place. The two `.invalid` recipients were
  refused singly (521) and named in the log; the mail went to the third.
  Tenants with nobody reachable: logged `nobody`, no copies to the node.
- A real successful backup afterwards -> "Behoben: …" to both, one minute after
  the backup ended; nothing written or sent while it ran. A probe to a list
  through `oaap notify test` arrived marked as a probe. The real portal renders
  both sections at the node (tenants' lists as names and counts) and at
  vuebung (its addresses, its log).
- **Found by measuring, fixed before anything left oaap-test:**
  1. *The notifications broke the backup.* State and view were written into
     `apps/` every minute; the backup's `tar` failed with "apps: Datei hat sich
     beim Lesen geändert". -> state and outbox moved to `data/notify`, the view
     written only on change, the minute part waits while a backup runs.
  2. *A "Behoben" mid-backup:* a running backup is neither failed nor fixed. ->
     the same wait.
  3. *A 5xx was retried every minute* (`521 Domain does not exist`), with a log
     line each time. -> 5xx is final; a retry is logged once.
  4. *One matter per instance* opened one mail per instance with open image
     fixes at the first minute -> one matter per tenant, the text lists them.
  5. *"Serverbesitzer" reached nobody:* oaap-test's `server_admin` has no
     address — likely so on the other nodes. -> the reach view; the portal says
     it in red. **Before the rollout each node's owner list needs an address.**
  6. *A backup refused for lack of room left yesterday's "ok" standing* (the
     space check died before recording) -> it now records `failed` like every
     other outcome (`oaap.data.backup` behaviour, not only notifications).
  7. Links pointed to pages that do not exist (`/backup`, `/gesundheit`) ->
     `/health` for the node, the start page for a tenant; `[]` in a node subject
     -> the node's name.

## Zusammenfassung (deutsch)

**Worum es geht:** Die Plattform soll von sich aus Bescheid geben, und zwar
den richtigen Leuten. Bisher verschickt nur Keycloak Mails (Passwort
vergessen). Ein fehlgeschlagenes Backup sieht man heute nur, wenn man ins
Portal schaut.

**Verteiler:** Ein Verteiler hat einen Namen und Einträge. Jeder Eintrag ist
eine **E-Mail-Adresse oder eine Rolle** (etwa „alle Mandanten-Admins“) und
steht unter An, Cc oder Bcc. Eine Rolle wird erst beim Versand aufgelöst und
bleibt so aktuell, wenn Personen wechseln. Es gibt Verteiler des Knotens
(Server-Admin) und Verteiler je Mandant (Mandanten-Admin). Jeder Eintrag hat
schon ein Feld „Kanal“: heute nur Mail, als Nächstes Telegram.

**Meldungsarten:** Die Plattform gibt einen festen Katalog vor, in vier
Kategorien: *kritisch*, *Gesundheit*, *Sicherheit*, *Betrieb*. Eine Zuordnung
sagt, welcher Verteiler welche Kategorie bekommt. Einzelne Arten lassen sich
abweichend zuordnen, jeweils mit eigener Betreffvorlage (`{mandant}`,
`{knoten}`, `{instanz}` …). Was nirgends zugeordnet ist, landet im
Pflicht-Verteiler **„Serverbesitzer“** bzw. **„Mandantenverwaltung“**. Diese
beiden legt die Plattform selbst an, mit der Admin-Rolle darin. So
funktioniert es ab dem ersten Tag ohne Einrichtung.

**Was heute schon erkannt wird (im Code gelesen):** fehlgeschlagenes
Backup, offene Sicherheitsupdates (Rechner und Abbilder), Neustartplan,
angehaltener Lauf, fehlgeschlagener Neubau, wartende Bestätigung. Den
Plattenfüllstand misst die Plattform, eine Schwelle fehlt noch; die kommt
mit dazu (90 %/95 %).
**Was nicht erkannt wird:** **Einbrüche erkennt heute nichts.** Das braucht
ein eigenes RFC. Die Anmeldesperre nach 5 Fehlversuchen gibt es, sie meldet
aber nichts nach außen. Eine Prüfung „Instanz ausgefallen“ habe ich nicht
gefunden. Beides kommt in Stufe 2.

**Versand:** Der Server selbst verschickt, nie ein Container. Er nutzt das
Postfach des Mandanten, sonst das des Knotens mit dem Mandantennamen als
Absender. Eine Lage wird gemeldet, **wenn sie beginnt und wenn sie behoben
ist**. Nur Kritisches kommt zusätzlich einmal täglich, solange es andauert.
Es gibt ein Versandprotokoll. Schlägt der Versand selbst fehl, steht das im
Portal und löst keine weitere Mail aus.

**Im Portal:** Unter „Nachrichten“ kommen die Abschnitte **„Verteiler“** (mit
„Probe senden“) und **„Benachrichtigungen“** (Zuordnung und Protokoll) dazu.

**Entscheidungen (Empfehlung jeweils „ja“):** D1 Rollen und Adressen und D2
Kanalfeld/Telegram als Nächstes hast du schon entschieden. D3 fester Katalog
mit vier Kategorien. D4 Pflicht-Verteiler. D5 Ein fehlgeschlagenes
Server-Backup meldet sich auch bei jedem Mandanten, weil seine Daten darin
liegen und es kein eigenes Mandanten-Backup gibt. D6 Meldung bei Beginn und
Behebung, Kritisches täglich. D7 Plattenschwellen 90/95 %. D8 Der Knoten
sieht von den Mandanten-Verteilern nur Namen und Anzahl. D9 Grenzen gegen
Missbrauch des Absenders: 25 Empfänger je Verteiler, 20 Mails je Mandant und
Stunde. D10 eigene Spezifikation `oaap.core.notifications`.
