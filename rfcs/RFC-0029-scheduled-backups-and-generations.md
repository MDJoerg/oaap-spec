# RFC-0029: A Backup That Runs By Itself — Schedule, Generations, Visibility

- **Status:** Accepted (2026-09-05) — all seven decided
- **Date:** 2026-09-05
- **Authors:** Jörg (questions and direction), Claude (analysis & proposal)
- **Depends on:** `oaap.data.backup` 0.1.4, RFC-0022 (tenant as boundary),
  RFC-0024 (a deployment you can see — the visibility pattern this
  borrows), RFC-0011 (node profiles), ADR-0006 (deployment scenarios)
- **Driver:** `oaapx01` carries more every week — bdt-hub and bdt-app in
  test and production, the GLISS viewer of a paying customer in its own
  tenant, the AI gateway, LiveKit — and on 2026-09-05 it had **never been
  backed up once**. `/var/backups/oaap` did not exist. Jörg: *„Ich baue da
  gerade immer mehr auf und würde gern dieses Thema vielleicht auch
  pragmatisch lösen."*

## Summary

`oaap.data.backup` 0.1 can make one complete archive when a human asks.
Everything that turns that into an actual safety net was deferred: a
schedule, retention, an off-site copy, and any way to see whether last
night worked. This RFC decides that shape before it is built.

Five questions came from Jörg in one breath, and they are the right
five. Each is a decision below, with a recommendation:

| | Question | Decided |
| --- | --- | --- |
| **D1** | Is the schedule configured in the portal? | **Editable straight away**, `server_admin` only — Jörg chose the fuller variant over the recommended two-step |
| **D2** | Do both portals show done / planned / cancelled backups? | **Each truth once** — a node shows what it can verify, the puller shows what only it knows |
| **D3** | Incremental backups, weekly and monthly, with periodic fulls? | **No incremental** — and the outage drops: stop, copy uncompressed, start, compress afterwards |
| **D4** | Are archives deleted at the source right after transfer, or after a set time? | **Keep the 2 newest at the source**, regardless of whether they were fetched |
| **D5** | Separate backups per tenant, so one can be restored alone? | **Archive now, restore later** — the merge question gets its own round |
| **D5b** | Einzelne Mandanten vom Knoten-Backup ausnehmen? | **Ja, nach D5** — mit den drei Bedingungen |
| **D6** | Also a backup pushed by the node itself? | **Specified, built when the first unreachable node exists** |

## Motivation

### What happened on the day this was written

Two findings, both of the kind that only appear on a real machine.

**The first is why this RFC is urgent.** `oaap backup create` on a live
node produced an archive of **9 KB** for a node holding **899 MB**. It
reported success. The restore would have succeeded too — onto an empty
platform. Since the instance tree moved to `tenants/…` (RFC-0026, three
days earlier), the command still copied the list of paths it had always
copied: registry, users, store sources. No app data. No `instance.env`,
which means no app secrets either.

It is the same cut as the four findings of 2026-09-03: an identifier is
given a new, composed meaning, and **one reader goes on reading it in
the old one**. The backup was the fifth reader. Fixed the same day in
0.1.70, together with the rule that prevents the whole class:
`oaap.data.backup` 0.1.4 now requires completeness to be **measured
against the finished archive**, not asserted by the code that wrote it.
A path list can be spelled correctly and be empty.

On `oaapx01` the same command would have produced about **100 KB** for
9.1 GB. That is the backup that would otherwise have run tonight.

**The second is a number to design around.** A full archive of 899 MB
took **131 seconds — with the app containers stopped the whole time.**
Scaled to `oaapx01`'s 9.1 GB that is roughly twenty minutes of nightly
downtime for bdt-hub in production. That is no longer "a moment at
half past three"; it is an outage with a schedule. See D3.

### Why the pull direction, and why it is not the only one

The internal node fetches from the external one. The external node then
holds **no credential pointing inward**: taking over `oaapx01` does not
reach the backups. That is the whole security argument, and it is why
the first implementation is a pull.

It does not cover the case OAAP exists for. Bernd's workshop sits behind
someone else's firewall; nobody can reach in. There the node must push,
and the security argument inverts — see D6.

## Decisions

### D1 — The schedule belongs in the portal
> **Entschieden (2026-09-05): sofort auch änderbar** — `server_admin`
> stellt Uhrzeit und Aufbewahrung im Portal ein, ohne die
> Zwischenstufe. Jörg wählte damit die weitergehende Variante gegen die
> Empfehlung unten; die Begründung für die Zwischenstufe war nie ein
> Zweifel an der Sache, sondern die Sorge um einen Satz. Der Satz ist
> damit **Bedingung statt Vorbehalt**: Die Seite muss im selben
> Atemzug wie das Zeitfeld sagen, dass zur genannten Uhrzeit **jede App
> dieses Knotens für Minuten steht** — mit der zuletzt gemessenen Dauer
> dieses Knotens, nicht mit einer allgemeinen Zahl. Unverändert gilt:
> Ziel-Pfad und Abhol-Schlüssel kommen nicht ins Portal.


**Recommendation: yes, in two steps.** First the portal *shows* the
schedule and the state and says how to change it on the machine; then
it becomes editable for `server_admin`.

The reason for two steps is the same one that let a store source into
the portal while a node profile stayed on the machine (RFC-0012 §7): a
setting may move to the portal when it is *visible, reversible, and
grants nobody more reach than they already had*. A backup schedule is
all three. But the thing it schedules stops every app on the node for
minutes, so the page has to say that in the same breath as the time
field — and writing that sentence well is worth its own round.

Not in the portal, ever: the **target path** and the **pull key**. Those
name places and rights outside this node, and a portal that can redirect
where every secret on the machine is written is a portal that can
exfiltrate the machine.

### D2 — Visible in the portal, once per truth
> **Entschieden (2026-09-05): jede Wahrheit nur einmal.** Wie unten
> beschrieben.


**Recommendation: yes — the node's own backups on the node's own health
page, and the other node's through the fleet status (RFC-0021), never
as a second record.**

Concretely, borrowing RFC-0024's vocabulary because the shape is the
same:

- **done** — when, how long, how big, and whether the archive was read
  back successfully. Failures stay listed; a list that only shows
  successes cannot tell "it failed" from "nobody ever set this up".
- **planned** — the next run, from the timer itself rather than from a
  stored intention, so the page cannot claim a schedule that is not
  armed.
- **running** — with "seit N Minuten", because during those minutes the
  apps are down and somebody will be looking for the reason.
- **cancelled / skipped** — a node that was off at the appointed hour
  catches up; a run that could not start says why.

The pulling node knows things the source cannot: whether the copy
arrived, whether the checksum matched, how many generations exist. That
is *its* record and belongs on *its* page. The source's page must not
claim it — it would be repeating a fact it cannot verify, the exact
error the Studio card was corrected for on 2026-08-24.

**Machine-readable first.** Both sides already write a small
`status.json` (schema 0.1). The portal reads that file rather than
parsing a transcript, and the fleet status carries the same fields.

### D3 — No incremental backups. Generations of full archives instead
> **Entschieden (2026-09-05): keine inkrementellen Sicherungen — und
> die Ausfallzeit sinkt.** Stoppen, unkomprimiert kopieren, starten,
> danach komprimieren. Gemessen auf `oaapx01` am Tag der Entscheidung:
> 487 Sekunden Ausfall für 8,0 GB, davon fast alles Komprimierung.
> Erwartung danach: etwa eine Minute. Der Preis ist, die Daten
> vorübergehend doppelt zu halten — auf einer Platte mit 913 GB frei
> ist das umsonst. Damit wird dies **die erste Baustufe**, weil D1 ohne
> sie einen Zeitplan konfigurierbar macht, dessen Kosten unnötig hoch
> sind.


**Recommendation: no incremental, and this is a decision, not a
postponement.**

A full archive is restorable on its own. A chain is restorable only as
far as its weakest link, and a chain whose links are verified only when
they are needed is not a backup but a hope. Building that ourselves —
snapshot state, chain integrity, a restore that walks the chain —
would be a substantial amount of the most consequential code in the
platform, for a saving we do not need: 9 GB against 1.2 TB.

"Weekly" and "monthly" therefore become **kept generations of full
archives**, which is what the question actually asks for:

| Generation | From | Default |
| ---------- | ---- | ------- |
| daily | every run | 7 |
| weekly | the Sunday run | 4 |
| monthly | the run on the 1st | 6 |

Kept as hard links where the filesystem allows, so a generation costs no
second copy of the same bytes.

**If the size ever does become the problem**, the answer is not our own
incremental format but a tool that already has one — restic or borg, on
the *pulling* side, where a failure costs a copy and not the original.
That keeps the node's own act simple: make one complete archive.

**What should change instead is the downtime.** Today the containers
are stopped for the copy *and* for the compression, and compression is
almost all of it. Stopping, copying uncompressed to the same disk,
starting, and compressing afterwards would cut the outage from about
twenty minutes to about one on `oaapx01` — at the cost of temporarily
holding the data twice, which is free on a disk with 913 GB spare.
**This is the highest-value change in this RFC** and it is what makes a
nightly backup of a production node acceptable at all.

### D4 — Local archives expire by time, not by transfer
> **Entschieden (2026-09-05): die 2 neuesten bleiben am Ursprung
> liegen**, unabhängig vom Abholen. Wie unten beschrieben; so läuft es
> seit dem Tag der Entscheidung bereits auf `oaapx01` und `oaap-test`.


**Recommendation: keep the N newest at the source, default 2, never
zero — independent of whether they were fetched.**

Deleting on successful transfer sounds tidy and moves the whole safety
net onto one copy at one place: if the fetched copy is silently damaged,
nothing is left. Two generations on the source cost disk space that is
already there, and they are the cheapest possible way back — no network,
no second machine.

The source therefore knows nothing about the puller, which is also why
the same node can be fetched by two different places without either
being able to destroy the other's material.

### D5 — Per-tenant archives: yes. Per-tenant restore: not yet
> **Entschieden (2026-09-05): Archiv jetzt, Zurückspielen später.**
> `oaap backup create --tenant <label>` wird gebaut; das Verschmelzen
> eines Mandanten in einen laufenden Knoten bekommt eine eigene Runde
> und wird bis dahin **nicht versprochen**.


**Recommendation: split the question, because the two halves are not
equally hard.**

The **archive** is now genuinely possible, and it was not before
2026-09-02: since RFC-0026 everything one tenant owns lies under one
subtree (`tenants/<tenant-id>/`), and the platform can name it without
guessing. `oaap backup create --tenant <label>` would produce that
subtree plus the tenant's users and registry entries. This is a
reasonable next build.

The **restore** is the hard half, and it should not be promised with
the archive. A whole-node restore *replaces* a machine. Restoring one
tenant *merges* into a running node that has other customers on it, and
every question that makes hard is still open: what happens to an
instance that exists now and did not then, to a port already taken by
somebody else, to a name that a different tenant has since claimed, to
a user who exists in both. Answering those badly loses another
customer's data while restoring this one's.

Two things follow for the near term:

1. **Say what today's archive is.** A whole-node archive contains every
   tenant, and a customer's complete data set in one file — carried to
   wherever the backup target is. On a multi-tenant node that is a
   decision about somebody else's data, and it belongs in front of the
   operator when the target is chosen, not in a document (the same rule
   as the public tenant label, `oaap.core.tenant` 3.4).
2. **Do not build the per-tenant archive until the restore question has
   a shape**, or we ship the half that feels safe and leaves the actual
   need unmet.

### D5b — Excluding a tenant from the node backup
> **Entschieden (2026-09-05): ja, nach D5** — mit allen drei
> Bedingungen unten. Für `cls` ist es vorerst nicht dringend, was der
> beste Zeitpunkt für eine solche Entscheidung ist: ohne Druck.


Jörg, 2026-09-05: *„Wäre es eine Option bei der Konfiguration des
Backups nur bestimmte Mandanten einzuschließen und beispielsweise das
Backup aus dem Tenant heraus mit einem anderen Verfahren zu machen?"*

**Recommendation: yes — and it is the better default for a multi-tenant
operator, on three conditions that are not optional.**

It changes what the operator's archive *is*. Today it is "everything on
this machine", which on a node with customers means the operator holds
every customer's complete data set wherever the backup target happens to
be. With exclusion it becomes **"everything I am responsible for"** —
which is a more honest description of an operator's actual duty, and it
shrinks the blast radius of a stolen archive.

The three conditions:

1. **The archive must record what it deliberately left out.** A manifest
   that lists the tenants it contains and the tenants it omitted *by
   configuration*. Without this, a restore silently produces a node with
   a customer missing — the same class of failure as the 9 KB archive
   that started this RFC, and discovered on the same day: the day the
   original is gone.
2. **The restore must say it, not discover it.** An excluded tenant's
   instances are in the registry but have no data. The restore must
   name them and refuse to start them as if they were whole, rather than
   bringing up an app that looks wiped. (Which of the two — omit the
   registry entries, or restore them dormant with a warning — is the one
   sub-question worth deciding when this is built; the recommendation is
   **dormant plus a loud sentence**, because a customer's instance
   silently vanishing from the registry is worse than one that says
   "my data is elsewhere".)
3. **The tenant has to be able to see it.** Exclusion moves the risk
   onto the customer. That is a contract statement, not a checkbox, so
   the setting carries a reason and appears in **that tenant's own audit
   log** — the same counterweight that makes `server_admin` bearable
   (RFC-0022 §6). A customer who is not backed up by the operator must
   not learn it from the outage.

**On "another procedure from within the tenant":** today a
`tenant_admin` has no backup capability at all, so exclusion alone would
leave that tenant with nothing. Two forms are plausible — an app-level
export (which the App Deployment Contract could require of apps that
want it) or a tenant-scoped `oaap backup create --tenant <label>` that a
`tenant_admin` may run for their own tenant. The second is much the
smaller step: it is D5's archive with a different caller.

**Therefore the ordering: D5 before D5b.** Build the per-tenant archive
first; exclusion then reduces to *"this tenant is backed up separately,
and here is by whom"*, using the same mechanism from both ends.
Exclusion built first would mean a tenant with no platform-side backup
at all and a promise that somebody else is handling it — which is
exactly the arrangement that fails quietly.

For `cls` this is not urgent (Jörg, same day: *„Für cls ist das erst
einmal egal"*), so it is a decision to make deliberately rather than
under pressure — which is the best time to make it.

### D6 — The node pushing its own backup: a second mode, later
> **Entschieden (2026-09-05): Form steht, gebaut wird sie, wenn der
> erste Knoten hinter fremder Firewall wirklich steht.** Heute
> erreichen wir jeden Knoten der Flotte. Die Bedingung gilt ab dem
> ersten Tag und ist nicht verhandelbar: Das Zugangsrecht eines
> schiebenden Knotens darf **nur anlegen** — nie lesen, nie
> überschreiben, nie löschen.


**Recommendation: yes, as an explicitly second mode — and the security
argument has to be rebuilt for it, not carried over.**

Pull works while the internal node can reach the external one. It does
not work for the scenario OAAP is for: a node behind a customer's
firewall that nobody can reach. There the node must push.

The moment it does, it holds a credential to the target, and that
credential is on the machine whose compromise the backups exist to
survive. So it MUST be able to **create only** — never list, never read,
never overwrite, never delete. An append-only target (a write-only
object store bucket, or an SSH forced command that accepts a new file
and refuses everything else) is the requirement, not a nicety: with a
credential that can delete, an attacker who takes the node takes the
backups with it.

This mode is also what a **service partner** offering "we keep your
backups" needs, which connects it to `oaap.ops.monitoring` and to the
Care tier of the business model.

## What was already built (2026-09-05)

Deliberately *not* as a platform capability. `oaap-reference/ops/` holds
the trial run: a nightly full backup with local retention and a state
file, and a pull to a second node's off-site storage with checksum
verification and the generation scheme of D3. They are scripts an
operator installs, on our own fleet, so the shape can be judged from a
few weeks of real nights instead of from this document. What survives
that goes into `oaap.data.backup` 0.2; what does not, does not.

The one thing that did not wait is the completeness gap: that is fixed
in the platform, in 0.1.70, because a silent one is not a shape
question.

## Build order that follows

Decided 2026-09-05. Nothing here is urgent — the safety net exists and
is proven — so the order is by what makes the next step cheaper:

1. **D3, the copy-then-compress change.** First, because D1 otherwise
   makes a schedule configurable whose cost is needlessly high. Turns
   `oaapx01`'s nightly outage from eight minutes into about one.
2. **D2 read, then D1 write.** The state files exist on both sides
   already, so showing comes almost free and gives the write page
   somewhere to land. D1's warning sentence carries the number D3 just
   improved.
3. **D5, the per-tenant archive.** Buildable since RFC-0026.
4. **D5b, exclusion**, which reduces to a declaration once D5 exists.
5. **D6** when the first unreachable node exists — not before.

Deliberately not on this list: per-tenant *restore* (its own round, see
D5) and anything incremental (D3 decided against it).

## Deutsche Zusammenfassung

Ein Backup, das von allein läuft. Anlass: `oaapx01` trägt immer mehr —
bdt-hub, bdt-app, den Viewer eines zahlenden Kunden im eigenen Mandanten
— und war am 05.09.2026 **noch nie gesichert**.

Am selben Tag zwei Funde. Der erste ist der Grund für die Eile: Auf
einem echten Knoten erzeugte `oaap backup create` ein Archiv von **9 KB**
für **899 MB** Daten — und meldete Erfolg. Seit die Instanzdaten unter
`tenants/` liegen (RFC-0026, drei Tage zuvor), kopierte der Befehl noch
immer dieselbe Pfadliste wie eh und je: Registry und Benutzer, keine
Anwendungsdaten, keine `instance.env` und damit keine Geheimnisse. Auf
`oaapx01` wären es rund 100 KB für 9,1 GB gewesen — das Backup, das
sonst heute Nacht gelaufen wäre. Derselbe Schnitt wie bei den vier
Funden vom 03.09.: Ein Bezeichner bekommt eine neue Bedeutung, und eine
Stelle liest ihn weiter in der alten. Behoben in 0.1.70; die Spec
verlangt jetzt, dass Vollständigkeit **am fertigen Archiv gemessen**
wird und nicht behauptet.

Der zweite Fund ist eine Zahl: 899 MB brauchten **131 Sekunden mit
gestoppten Containern**. Auf `oaapx01` wären das rund zwanzig Minuten
Ausfall pro Nacht für bdt-hub.

**Am 05.09.2026 hat Jörg alle sieben entschieden:**

- **D1 — Zeitplan im Portal, sofort auch änderbar** (nur
  `server_admin`). Damit fällt die von mir vorgeschlagene Zwischenstufe
  weg; die Sorge dahinter galt nie der Sache, sondern einem Satz — und
  der ist jetzt Bedingung: Die Seite muss neben dem Zeitfeld sagen,
  dass zu dieser Uhrzeit **jede App dieses Knotens für Minuten steht**,
  mit der zuletzt gemessenen Dauer *dieses* Knotens. Ziel-Pfad und
  Abhol-Schlüssel bleiben draußen.
- **D2 — jede Wahrheit nur einmal.** Ein Knoten zeigt, was er belegen
  kann; was nur der abholende Knoten weiß, steht auf dessen Seite.
- **D3 — keine inkrementellen Sicherungen, und die Ausfallzeit sinkt.**
  Erst stoppen und unkomprimiert kopieren, dann starten, dann
  komprimieren. Gemessen: 487 Sekunden für 8,0 GB auf `oaapx01`, fast
  alles davon Komprimierung. Erwartung danach: etwa eine Minute.
- **D4 — die zwei neuesten Archive bleiben am Ursprung**, unabhängig
  vom Abholen. Läuft seit dem Entscheidungstag so.
- **D5 — Archiv je Mandant wird gebaut, Zurückspielen später** und bis
  dahin nicht versprochen.
- **D5b — Ausnehmen ja, aber nach D5**, mit allen drei Bedingungen.
- **D6 — Form steht, gebaut wenn der erste unerreichbare Knoten
  existiert.** Die Regel gilt ab Tag eins: nur anlegen dürfen.

**Reihenfolge:** D3 zuerst — sonst macht D1 einen Zeitplan einstellbar,
dessen Kosten unnötig hoch sind. Dann D2 (zeigen) und D1 (ändern), dann
D5, dann D5b. D6 erst, wenn Bernd es braucht.
