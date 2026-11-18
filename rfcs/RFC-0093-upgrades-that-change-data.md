# RFC-0093: Upgrades That Change Data — Notes in the Package, a Safety Net on the Node, a Warning in the Portal

- **Status:** **Draft (2026-11-18)** — D1–D6 open. Nothing built.
  Implementation waits until codeberg.org (Forgejo's release notes) is
  reachable again; the first case is the Forgejo upgrade 11 → 15 on
  oaap-demo, done by hand with Jörg along this RFC.
- **Date:** 2026-11-18
- **Authors:** Jörg (the question, 2026-11-18: "what if an external app
  migrates its data model and we break our instance — later the user must
  be able to do this in the portal without us, warned, and unable to break
  his instance carelessly; packaging for the store carries more
  responsibility"), Claude (reading of the reference, design)
- **Depends on:** `oaap.apps.runtime` 2.6 (store install/update), 2.14
  (the envelope rule, retained artifacts and rollback), 2.14.1 (promotion,
  "test first"), 2.15 (rehearsal, RFC-0030), 2.30 (the rebuild and its way
  back, RFC-0071), `oaap.data.backup` 0.7 (node and tenant archives),
  RFC-0083 (weekly report), RFC-0050 (package catalog)
- **Not part of this RFC:** migrations of the platform's own state
  (`oaap update` has its own migration steps); online backups
  (`oaap.data.backup` 2.2 "later version"); an app's own upgrade code —
  OAAP never runs a migration itself, the app does, OAAP decides whether
  and how safely the app gets to run it.

## Summary

On 2026-11-18 the store package Forgejo was raised from 11.0.0 to
15.0.11 — four major versions — and measured on fresh installs only. The
same day it turned out that a production instance of Forgejo 11 runs on
oaap-demo, that Forgejo 11 has been out of support since 16 July 2026,
and that the store would now offer "Aktualisieren auf 15.0.11" there with
one click: no backup, no notes, no warning, and a way back that restores
the old image onto a database the new one has already migrated — which
Forgejo refuses to start on.

Nothing in that chain is Forgejo's fault. Forgejo documents it
correctly: a full backup is a requirement, migrations run on start,
downgrades are refused, read the notes of every version you skip. The
gap is ours: **an update in OAAP knows what the app may do (the
envelope) but not what it does to its data.**

The proposal, in seven parts:

1. **Upgrade notes in the package** — manifest 0.17 `upgrade:` (is the
   change one-way, from which version a direct jump is supported, steps
   before and after) and an `UPGRADE.md` per package. Silence counts as
   one-way.
2. **A safety net on the node** — before a production instance is
   updated, its data is snapshotted; a failed update brings back image
   **and** data as one pair.
3. **A warning in the portal** — the update dialog names the jump, the
   notes, and that the way back is the snapshot; it asks for a tick.
4. **The rehearsal as the regular way** for a one-way update of
   production.
5. **Support end in the catalog** — an instance on a version without
   support is named in the weekly report.
6. **A packaging rule for the store** — a major upstream jump is
   released only with researched notes and an update measured on
   existing data.
7. **The check after the update comes from the package** — the app's
   own check (`forgejo doctor check`) decides, not "it answers HTTP".

## 1. Facts (read on 2026-11-18)

### 1.1 What OAAP does today

| What | Where | Today |
|---|---|---|
| Store update of an instance | runtime 2.6, `test_store_update_instance` | one button per instance; a production instance with a test sibling is not updated directly ("test first", then promotion 2.14.1); **without a test sibling production is updated directly** |
| Backup before an update | — | **none** |
| Backup granularity | `oaap.data.backup` 2.1–2.2 | the node, or one tenant's archive; offline-consistent, **all** app containers of the node stop for the copy |
| Restore | `oaap.data.backup` 2.3 | an **installer mode** for a whole node; restoring the data of ONE instance does not exist |
| The way back | runtime 2.14 (retained artifacts, ≥ 3 predecessors), 2.30 (`rebuild --back`, the predecessor image) | restores **code only**. On data a newer version migrated, the old code fails — Forgejo: "it will refuse to start" |
| The envelope rule | runtime 2.14, I-43 | compares what a package **may** do (routes, roles, ports, devices); says nothing about data |
| Rehearsal | runtime 2.15, RFC-0030 | new code on a copy of production's data from an archive — exactly the question "does 15 come up on THIS data?" — but nothing proposes or requires it. RFC-0030 itself: "migration completes on this data. Going back is still the backup." |
| Health after an update | runtime 2.6/2.11, `health.path` | "answers HTTP" within the startup grace; a migration that half ran and an app that serves errors on every second page both pass |
| Rebuild of a foreign image | runtime 2.30 step 2 | "its rebuild is a pull" — with a floating tag (`:11`, `:latest`; the store README: "teils noch gleitende Tags (`latest`)") **a rebuild can be a silent update with a migration**; the nightly rebuild (RFC-0071 stage 3) would do it unattended |
| Release notes | `oaap.dist.marketplace` §6a | the marketplace shows Markdown release notes; the node's store shows a version number |
| Support end of an upstream line | — | nowhere; Forgejo 11 ran four months past its end on a production instance unnoticed |

### 1.2 What Forgejo says about 11 → 15

From forgejo.org (docs v15.0 upgrade guide, release posts v12–v15);
the per-version breaking-change lists on codeberg.org could not be read
on 2026-11-18 (unreachable).

- Skipping majors is supported: "upgrade straight to the latest released
  Forgejo version … the upgrade procedure will take care of migrations";
  but "if you upgrade from v11.0, please remember to also check the
  release notes for v12.0, v13.0, and v14.0 for breaking changes".
- "make sure to perform a full backup before upgrading. It is a
  requirement when upgrading to a new stable release." For one filesystem
  and SQLite, `forgejo dump` or a point-in-time copy of all storage.
- Before: `forgejo manager flush-queues` — queue data "is not guaranteed
  to be backward compatible between versions".
- After: `forgejo doctor check --all` "and make sure it does not report
  any problem".
- Downgrade: the database version "is used to prevent an accidental
  downgrade … it will refuse to start". The documented way back is the
  backup.
- Breaking for us: v15 every user signs in again (cookie renamed); v12
  tokens in the URL (`?token=`, `?access_token=`) removed without a way
  back — any script of ours that clones that way breaks; v14 adds foreign
  keys and **deletes inconsistent rows** while doing so (logged).

Every one of these is a fact the package knew nothing about and the
portal could not have said.

## 2. Upgrade notes in the package (manifest 0.17 or the next free one)

*Note 2026-11-18: RFC-0094 (help) proposes to take 0.17 for `docs:`; then `upgrade:` becomes 0.18 (RFC-0094 D10).*

```yaml
oaap_manifest: "0.17"
upgrade:
  data: one-way            # one-way | compatible
  from: "11.0.0"           # oldest version this one migrates directly
  via: []                  # versions an older instance must pass first
  before:                  # run in the old container, before it stops
    - [forgejo, manager, flush-queues, --timeout, 5m]
  after:                   # run in the new container once it answers
    - [forgejo, doctor, check, --all]
  notes: UPGRADE.md        # in the package, see 2.1
```

- **`data`**: `one-way` — this version changes data so that an older
  version cannot read it; `compatible` — it does not (the author's
  promise, like `care.rebuild`, runtime 2.31). **Absent counts as
  `one-way`**: for a wrapped foreign image nobody at OAAP knows, and the
  safe assumption costs a snapshot, the unsafe one costs the data.
- **`from` / `via`**: an instance older than `from` is not updated
  directly; the portal names the versions in `via` and offers them in
  order (the catalog keeps those package versions, RFC-0050). No `from`:
  every older version counts as supported.
- **`before` / `after`**: argument lists (never a shell string), run as
  the service's user in its container, each with a timeout; `before` in
  the running old container, `after` in the new one once it answers.
  A non-zero exit of `after` counts as a failed update (§3). Output goes
  to the instance's log and the update record, not to the portal page.
- **`notes`**: a Markdown file in the package.
- A node before 0.17 ignores the section (RFC-0012 §8.2) — and then
  behaves like today. That is the reason §3's snapshot does not depend
  on the section: it is the node's rule, the section only refines it.

### 2.1 `UPGRADE.md`

One section per version that needs one, newest first, each with: what
changes for the data, what changes for users (a new sign-in, a removed
feature), what the operator must check, and **the sources read** (links
and the date they were read). The portal shows the sections between the
running version and the target — for 11 → 15 the sections of 12, 13, 14
and 15. A package whose `upgrade.data` is `one-way` and whose
`UPGRADE.md` has no section for its own version is refused by the store
check (§7).

## 3. A safety net on the node

An update (store, upload, Git, promotion, rebuild with a changed image)
of a **production** instance runs as one transaction:

1. **Refusals first** (nothing changed yet): the jump is not supported
   (`from`/`via`); not enough room for the snapshot (same check as
   `oaap.data.backup` 2.2); the instance is held, in standby or in a
   deployment.
2. `before` steps in the running container.
3. **Snapshot of this instance:** its containers stop (only these — not
   the node's, unlike today's backup), its storage directories are copied
   to `…/instances/<key>/pre-update/<stamp>/`, the running image is
   tagged as predecessor (the rebuild's tag, runtime 2.30 step 4), the
   instance's `instance.env` and record go with it. The downtime is
   measured and recorded (the backup rule, 2.2).
4. The update proper: new package, new image, containers recreated.
5. **The check:** the instance answers within its startup grace **and**
   every `after` step exits 0.
6. Passed: the record says `update: done` with versions, snapshot,
   downtime, check output; the tenant's log `instance.update`.
   Failed: containers stop, the snapshot's data is put back, the
   predecessor image runs, the record says `update: rolled-back` with the
   reason, the tenant's log too, and a notification goes to the tenant's
   administration list (RFC-0080).

**The way back after a passed update** ("Zurück auf die vorige
Version") restores image **and** snapshot as a pair, and says before it
runs: "Alles, was seit <time> in dieser Instanz geändert wurde, geht
verloren." A way back that restores only the image is refused for an
update the record marks one-way — that is the Forgejo case, and it must
not exist as a button.

The snapshot is **not** a backup in the sense of `oaap.data.backup`: it
lives on the same disk, for one purpose, and is removed by a later
passed update or after the retention of D5. The node's archive still
carries it while it exists (it is under the instance's directory).

Test instances get the same transaction without the duty to snapshot
(D4): their data is test data, and the snapshot costs disk.

## 4. A warning in the portal

The update button opens a dialog instead of starting:

- **"Von 11.0.0 auf 15.0.11 — vier Hauptversionen."** Major versions by
  semver; a version without semver is named as it is.
- **"Die Daten werden umgebaut. Zurück geht es nur über die Sicherung,
  die vorher angelegt wird."** for `one-way` (and for silence);
  "Die Daten bleiben lesbar für die alte Version." for `compatible`.
- The `UPGRADE.md` sections between the two versions, collapsed per
  version, the newest open.
- The measured downtime of the last snapshot of this instance, or an
  estimate from its data size, labelled as estimate.
- For production and `one-way`: **"Erst Generalprobe"** as the first
  button (§5), "Jetzt aktualisieren" as the second, behind a tick
  "Ich habe die Hinweise gelesen" — the tick carries the fingerprint of
  the notes shown, like the envelope tick of I-43.
- Unsupported jump: no update button, the way via the `via` versions
  instead.

The CLI says the same and wants `--confirm-upgrade` where the portal
wants the tick.

## 5. The rehearsal as the regular way

A rehearsal (RFC-0030) of the target version on a copy of production's
data answers the only question that matters before a one-way update.
Today it needs a test instance with the new code and a node archive. For
updates it becomes one action:

- **"Generalprobe für dieses Update"**: a rehearsal of the target
  package on a fresh **instance** snapshot (§3 step 3, not a node
  archive — the age is then minutes, not a night), with `before`/`after`
  run as in §3, its five refusals as always (no own address, no public
  route, no outgoing mail, …).
- Its result (`after` exit, the check output, the tester's "looks right")
  is stored with the update dialog: "Generalprobe am 18.11. bestanden".
- D2 decides whether a `tenant_admin` may run a one-way production
  update only after a passed rehearsal of that same target version.

## 6. Support end in the catalog

- A catalog entry (RFC-0050) MAY carry `supported_until` per package
  version line (`"11": "2026-07-16"`, `"15": "2027-07-15"`), taken from
  upstream's statement and dated in `UPGRADE.md`.
- The weekly report (RFC-0083) gets a section: instances running a line
  past its support end, with the newest supported version.
- The node's store marks such an instance on its card.

This is what would have said in July that oaap-demo's Forgejo had run out.

## 7. A packaging rule for the store

For `oaap-store` and `oaap-apps` (their AGENTS.md and `check-store.py`):

- A package version that raises the **upstream major** (or the
  upstream's own "breaking" marker) is released only with
  `upgrade.data`, `upgrade.from`, an `UPGRADE.md` section with the
  sources read **and the date**, and an update measured on existing data
  of the previous package version (not only a fresh install) — recorded
  in CURRENT_STATE.
- **Exact image tags.** A foreign image is pinned to a full version
  (`15.0.11`, not `15`, never `latest`); a patch update is a package
  version. Otherwise a rebuild (runtime 2.30) is an update nobody
  released. `check-store.py` refuses a floating tag on a new package
  version; existing ones are listed until they are pinned.
- The store check refuses a one-way package without its notes section.

The Forgejo package 15.0.11 of 2026-11-18 does not meet this rule: it
was measured on fresh installs only and its notes are not written. It is
the first package to be brought up to it, with the hand upgrade of
oaap-demo as its measurement.

## 8. Stages

| Stage | Content | Needs |
|---|---|---|
| 0 | By hand, with Jörg: Forgejo 11 → 15 on oaap-demo along §3/§5 — read the codeberg notes, check our own uses of `?token=`, flush-queues, snapshot, rehearsal on oaap-test with a copy, doctor check, then production; the protocol becomes Forgejo's `UPGRADE.md` | codeberg.org reachable |
| 1 | Packaging rule §7 and `check-store.py`; pin the floating tags of the store | D6 |
| 2 | Instance snapshot and the update transaction §3, CLI; the paired way back | D3–D5 |
| 3 | Manifest 0.17 `upgrade:` §2, `UPGRADE.md`, the portal dialog §4 | D1 |
| 4 | Rehearsal for an update §5 | D2 |
| 5 | `supported_until`, weekly report §6 | — |

Stage 2 is the one that protects data; it does not need the manifest
section, because silence counts as one-way.

## 9. Decisions for Jörg

- **D1 — Silence counts as one-way?** *Recommendation: yes.* A package
  that says nothing is treated as changing data irreversibly: snapshot,
  warning, paired way back. A package author who knows better writes
  `compatible`.
- **D2 — Who may run a one-way update of production?**
  *Recommendation:* the `server_admin` always (with the safety net); a
  `tenant_admin` only after a passed rehearsal of the same target
  version on that instance (§5). The test instance stays free for both.
- **D3 — Snapshot before every production update, or only one-way?**
  *Recommendation: every one.* `compatible` is a promise; the snapshot
  is what makes a wrong promise cheap.
- **D4 — Test instances?** *Recommendation:* the same transaction, the
  snapshot optional (off by default), because test data is test data and
  disk is not free.
- **D5 — How long does a snapshot stay?** *Recommendation:* until the
  next passed update of that instance, at least 7 days; the node's free
  space check warns, it never deletes a snapshot younger than 7 days on
  its own.
- **D6 — Exact image tags in the store from now on?**
  *Recommendation: yes*, and a patch update is a package version (the
  price: more package versions; the gain: no update nobody released).

## Deutsche Zusammenfassung

**Anlass:** Am 18.11.2026 wurde das Forgejo-Paket von 11 auf 15 gehoben,
gemessen nur an Neuinstallationen. Am selben Tag zeigte sich: Auf
oaap-demo läuft Forgejo 11 produktiv, seit 16.07.2026 ohne Support, und
der Store böte dort mit einem Klick das Update an. Vorher würde nichts
gesichert, es gäbe keine Hinweise und keine Warnung. Der Rückweg würde
nur das alte Abbild zurückbringen, und das startet auf einer schon
umgebauten Datenbank nicht. Forgejo dokumentiert das alles richtig; die
Lücke ist unsere. **Ein Update in OAAP weiß, was eine App darf, aber
nicht, was sie mit ihren Daten macht.**

**Was es heute gibt und warum es nicht reicht:** Sicherung nur für den
ganzen Knoten oder Mandanten, mit Stopp aller Apps; Zurückspielen nur
für den ganzen Knoten. Der Rückweg stellt nur Code zurück. Die
Generalprobe wäre das richtige Werkzeug, aber nichts schlägt sie vor.
Die Prüfung nach dem Update fragt nur „antwortet HTTP“. Gleitende Tags
(`:11`, `:latest`) machen sogar aus einem Neubau ein unbemerktes Update
mit Migration.

**Vorschlag in sieben Teilen:**

1. **Hinweise im Paket** (Manifest 0.17 `upgrade:`): Ist die Änderung
   ohne Rückweg (`one-way`)? Ab welcher Version geht der direkte Sprung,
   über welche Zwischenversionen sonst? Befehle vorher und nachher.
   Dazu eine `UPGRADE.md` mit Hinweisen und Quellen je Version.
   **Ohne Angabe gilt one-way.**
2. **Sicherheitsnetz auf dem Knoten:** Vor jedem Update einer
   Produktiv-Instanz wird nur diese Instanz angehalten und gesichert.
   Scheitert die Prüfung danach, kommen Abbild und Daten als Paar zurück.
   Ein Rückweg nur mit dem Abbild wird bei one-way abgelehnt.
3. **Warnung im Portal:** Größe des Sprungs, die Hinweise dazwischen,
   „Daten werden umgebaut, zurück nur über die Sicherung“, Haken zum
   Bestätigen, „Erst Generalprobe“ als erster Knopf.
4. **Generalprobe als Regelweg**, auf einer frischen Sicherung der
   Instanz statt eines nächtlichen Archivs.
5. **Support-Ende im Katalog**; der Wochenbericht nennt Instanzen auf
   Versionen ohne Support.
6. **Paketierregel für den Store:** Ein Hauptversionssprung nur mit
   recherchierten, datierten Hinweisen und einem gemessenen Update auf
   vorhandenen Daten; Images nur mit exakter Version.
7. **Die Prüfung nach dem Update kommt aus dem Paket** (bei Forgejo
   `doctor check`), nicht nur „antwortet HTTP“.

**Entscheidungen D1–D6:** Schweigen gilt als one-way (D1); wer darf
one-way auf Produktiv auslösen — server_admin immer, tenant_admin nur
nach bestandener Generalprobe (D2); Sicherung vor jedem Produktiv-Update
(D3); Test-Instanzen ohne Pflicht zur Sicherung (D4); Sicherung bleibt
bis zum nächsten erfolgreichen Update, mindestens 7 Tage (D5); exakte
Image-Tags im Store ab jetzt (D6).

**Stufen:** 0 Forgejo 11 → 15 auf oaap-demo von Hand mit Jörg, sobald
Codeberg erreichbar ist (das Protokoll wird die erste `UPGRADE.md`),
1 Paketierregel und exakte Tags, 2 Sicherung je Instanz und
Update-Transaktion (schützt die Daten, braucht das Manifest nicht),
3 Manifest 0.17 und Portal-Dialog, 4 Generalprobe fürs Update,
5 Support-Ende und Wochenbericht. Gebaut ist nichts.
