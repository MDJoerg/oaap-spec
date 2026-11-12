# RFC-0081: Backup Classes — How Much Backup a Node, a Tenant and a Test Instance Get

- **Status:** Draft (2026-11-12)
- **Date:** 2026-11-12
- **Authors:** Jörg (the need: "oaap-test is a test node and needs no real
  backup, at most a local one — maybe tenants should be able to configure
  something like that too"), Claude (facts measured on oaap-test and oaapx01
  on 2026-11-12, reference 0.1.257; design)
- **Depends on:** `oaap.data.backup` 0.4.2 (node archive, tenant archive
  2.1.1, exclusion 2.1.2, schedule 2.4), RFC-0029 (D1 schedule, D5 tenant
  archive, D5b exclusion), RFC-0053 (the vault: off-site copies, stage 3 the
  tenant door), RFC-0080 (`backup.failed`, `backup.missing`)
- **Not part of this RFC:** restoring a single tenant into a running node
  (still unbuilt and unpromised, `oaap.data.backup` 2.1.1); incremental
  backups; the vault itself (RFC-0053).

## Summary

Today a node either backs up **everything** every night or — schedule off —
**nothing**, and "nothing" raises a daily critical notification
(`backup.missing`, "Zeitplan aus"). Between the two there is only the
per-tenant exclusion of RFC-0029 D5b. That is too coarse in three places:

1. **A test node** (oaap-test) needs at most a local copy. Saying so should
   be a declaration with a reason, not an alarm every day.
2. **A tenant** may need more than the node gives (its own archive, its own
   hour, later an off-site copy through the vault) or less (a training or
   test tenant that needs nothing).
3. **Test instances** are copied and stopped every night like production.

This RFC introduces a **backup class** — declared for the node, for each
tenant and (as a switch) for test instances — and lets notifications, the
portal and the restore read it.

## 1. Facts (measured 2026-11-12)

- **oaap-test** backed up nightly to `/var/backups/oaap` (2 archives, 11 GB)
  **and** was pulled every night onto the Synology by oaap-demo (generations
  7/4/6, 33 GB) — full production treatment for a test node. Set to one local
  archive and the pull ended the same day (Jörg's word, CS 490).
- Each run stops the apps: oaap-test 80–100 s, oaapx01 45–51 s (its own
  measured figures, `apps/backup-last.json`).
- **Share of test instances** in the instance data (`du` of each instance
  directory, channel `test` or rehearsal):
  - oaap-test: 11 of 37 instances, **1.0 of 5.0 GB** (20 %)
  - oaapx01: 8 of 24 instances, **1.6 of 11.1 GB** (14 %)

  Leaving test instances out saves a fifth at most — worth a switch, not a
  redesign.
- Already there: **exclusion** of a tenant with a mandatory reason, filed in
  that tenant's log, recorded in the archive, named by the restore, its
  containers not stopped (`oaap.data.backup` 2.1.2, 0.4.1); a **tenant
  archive** that stops only that tenant's containers and says of itself
  "existence, not recovery" (2.1.1); `oaap tenant adopt` onto a node empty for
  that tenant. There is **no schedule** for a tenant archive, and nothing a
  `tenant_admin` can see about their backup besides their audit log.
- A node whose schedule is off gets `backup.missing` (critical, daily
  reminder) — correct for a forgotten backup, wrong for a declared one.

## 2. Proposal

### 2.1 The classes

| Class | Node | Tenant | Means |
|---|---|---|---|
| `offsite` | yes | — (via the vault, stage 3) | local archive + a copy that leaves the machine (pull or vault) |
| `local` | yes | yes | archives on this machine only — protects against mistakes, **not** against the disk or the machine dying |
| `node` | — | yes (default) | the tenant is part of the node's archive, whatever class the node has |
| `own` | — | yes | the tenant's **own archive** (2.1.1) on its own schedule, local; not in the node archive |
| `none` | yes | yes | no backup, **declared with a reason** |

- `none` for a tenant **is** today's exclusion (2.1.2) — same three
  conditions, same audit line; this RFC only names it.
- `own` takes the tenant out of the node archive (so it is not copied twice
  and its apps are not stopped twice) and gives it a schedule of its own.
- The node's class is a **declaration** the platform reads; the platform
  does not set up a pull or a vault from it (where archives go is decided at
  the machine, 2.4). `offsite` is declared by the operator who set up the
  pull; the health page can show the last pulled copy where the vault
  reports it (RFC-0053).

### 2.2 Test instances

A switch per node, overridable per tenant: **"Test-Instanzen nicht
sichern"**. Test instances (channel `test`, rehearsals) are then left out
of whichever archive would carry them, under the three conditions of 2.1.2:
recorded in the archive, named by the restore and left dormant, and visible
— the instance page says "nicht im Backup (Test-Instanz)". Their containers
are not stopped.

### 2.3 What reads the class

- **Notifications (RFC-0080):** `backup.missing` does not fire for a node
  declared `none`; it fires for `local`/`offsite` without a successful run in
  26 h, as today. A tenant with `own` gets `backup.failed` / `backup.missing`
  for **its** archive, in its own scope — the node hears it only through an
  explicit line.
- **Portal:** the node's health page shows the class and, for `local`, the
  sentence "liegt auf demselben Rechner — schützt vor Bedienfehlern, nicht
  vor einem Plattenausfall". Each tenant's start page (for its
  `tenant_admin`) shows the tenant's class, the last run that covered it and,
  for `none`, the operator's reason.
- **Restore:** unchanged rules, more inputs: what an archive left out by
  class is named before anything starts.

### 2.4 Who sets what

- The node's class, a tenant's class and the test switch: `server_admin`
  (they change what the operator promises and what the disk holds). Every
  change of a tenant's class is filed in that tenant's log.
- For a tenant with `own`, its `tenant_admin` may choose **the hour** and
  **how many archives stay**, up to a ceiling the `server_admin` sets — the
  run stops only that tenant's apps, so the hour is theirs.

### 2.5 Mechanics

- A tenant schedule is a systemd timer of its own
  (`oaap-tenant-backup@<label>.timer`), so systemd stays the truth (2.4).
- Node archive and tenant archives never run at the same time (one lock);
  a run that finds the lock taken waits, up to an hour, then records
  `failed` with the reason.
- The class lives with the existing records: the node's in the schedule
  record, a tenant's in its tenant record (`backup: {class, reason, at,
  keep}`), the exclusion file stays the source for `none` (one writer).

## 3. Decisions asked of Jörg

- **D1 — the classes as in 2.1** (`offsite`/`local`/`none` for the node;
  `node`/`own`/`local`/`none` for a tenant, `local` for a tenant being `own`
  without a later vault). *Recommendation: yes; `local` and `own` collapse
  for a tenant until the vault door exists — show one word, "eigenes Archiv".*
- **D2 — a declared `none` node raises no `backup.missing`.** The health page
  still says "kein Backup — Grund: …". *Recommendation: yes.*
- **D3 — test-instance switch default.** *Recommendation: off on existing
  nodes (nothing changes silently), on for a node whose class is `local` or
  `none` only when the operator ticks it.* The saving is 14–20 % (§1).
- **D4 — `tenant_admin` sets hour and count of an `own` archive** within the
  operator's ceiling. *Recommendation: yes.*
- **D5 — oaap-test** becomes the first node declared `local` with test
  instances left out. *Recommendation: yes — its own measurement first.*
- **D6 — order:** stage 1 node class + test switch + notifications; stage 2
  tenant `own` with schedules and the tenant page; stage 3 the vault door
  (RFC-0053) carries `own` archives off the machine. *Recommendation: as
  listed.*

## 4. Stages and what is measured

1. **Node class and test switch** — oaap-test declared `local`, test
   instances out: the archive's manifest lists them as left out, the
   completeness check passes narrowed, their containers keep running during
   the copy, `backup.missing` silent for a `none` declaration on a probe node.
2. **Tenant `own`** — a probe tenant on oaap-test with its own timer: only
   its containers stop, the node archive omits it, the lock makes a parallel
   start wait, a failure mails that tenant's list only.
3. **Vault door** — RFC-0053 stage 3 takes the `own` archive off the machine.

## 5. Out of scope

Restore of one tenant into a running node; incremental or deduplicated
archives; choosing a target path through the portal (stays at the machine).

## Zusammenfassung (deutsch)

Heute sichert ein Knoten **alles** jede Nacht oder — Zeitplan aus —
**nichts**, und „nichts“ löst täglich eine kritische Meldung aus. Dazwischen
gibt es nur das Ausnehmen eines Mandanten. Vorschlag: eine **Backup-Klasse**.

- **Knoten:** `offsite` (lokal + Kopie außer Haus), `local` (nur auf dem
  Rechner — schützt vor Bedienfehlern, nicht vor Plattentod), `none` (bewusst
  keins, mit Begründung, **ohne** tägliche Alarmmail).
- **Mandant:** `node` (im Knotenbackup, Standard), `own` (**eigenes Archiv**
  mit eigenem Zeitplan; stoppt nur seine Apps; später über den Tresor außer
  Haus), `none` (= das heutige Ausnehmen, mit Begründung in seinem Protokoll).
- **Schalter „Test-Instanzen nicht sichern“** je Knoten, je Mandant
  überschreibbar. Gemessen: Test-Instanzen sind auf oaap-test 20 %, auf
  oaapx01 14 % der Daten — lohnt sich als Schalter, mehr nicht.
- Der Mandanten-Admin sieht seine Klasse auf seiner Startseite und darf bei
  `own` Uhrzeit und Anzahl wählen (im Rahmen des Betreibers).
- Benachrichtigungen lesen die Klasse: `none` meldet nichts, `own` meldet
  Fehler nur dem Mandanten.

Entscheidungen D1–D6 in §3, je mit Empfehlung. Erster Knoten: oaap-test als
`local`, Test-Instanzen ausgelassen (heute schon auf 1 lokales Archiv
umgestellt, Abholung durch oaap-demo beendet).
