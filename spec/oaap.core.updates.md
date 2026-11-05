# oaap.core.updates — Platform Updates

- **ID:** `oaap.core.updates`
- **Version:** 0.2
- **Maturity:** draft — accepted by Jörg 2026-08-06 (CLI trigger
  implemented and validated on real hardware); 0.1.1 (2026-08-07)
  updates the reserved portal-trigger role to `server_admin` per
  RFC-0008; 0.1.2 (2026-08-09) adds the reconcile step for shipped
  store sources, per RFC-0012 §4; 0.1.3 (2026-08-09) states where
  consistency steps must live and when they must run — the engine
  replaces itself while running, so a step written into it is skipped
  by the very update that introduces it (found on oaap-demo); **0.2
  (2026-11-05, Jörg's decision after CVE-2026-98432) adds §2.6 host
  care**: the operating system under the platform is measured and the
  node says what to do — reboot required, automatic updates, the
  gateway's listeners — in `oaap status`, the portal and the fleet
  document; and two node settings the platform writes itself
- **Based on:** RFC-0001 (capability model); program decision 2026-08-03
  ("one update engine per node, three triggers"); git-based delivery;
  RFC-0012 §4 (shipped sources survive a move)
  (program backlog); trust principle of `oaap.apps.runtime` 2.5
  ("a request can never supply a source")

## 1. Purpose

Keeps the platform core of a node up to date without manual file
surgery. With a growing fleet (four nodes as of 2026-08-06), manual
copy procedures drift installations apart and burn operator time; a
conformant node updates itself from its **recorded platform source**
with one action, shows what would change before it changes it, and
never touches app instances or user data in the process.

Out of scope for 0.1: updating apps (that is the store/deploy path of
`oaap.apps.runtime`), operating-system updates (recommendation:
`unattended-upgrades`), and multi-node orchestration (future fleet
capability; this spec is the per-node engine it will call). Since 0.2
the operating system is no longer a recommendation in a parenthesis:
§2.6 measures its care state and lets the platform write the two
settings that make the recommendation true.

## 2. Interface

### 2.1 One engine, three triggers

Every node runs ONE update engine. It can be invoked by three
triggers; 0.1 implements the CLI, the others are reserved:

1. **CLI** — `oaap update` (technicians, service partners, and the
   rescue path when the portal is broken). Implemented in 0.1.
2. **Portal** — a button for administrators (the everyday path).
   Reserved; will reuse the host-task channel (spool + worker).
3. **Schedule** — automatic updates, primarily security fixes.
   Reserved; requires update channels/severity metadata first.

### 2.2 Recorded platform source

- The platform records **where it came from** at install time (git
  repository URL, optionally branch/ref, and the local working copy
  path). An update always means: **fetch the recorded source again**.
  Neither the CLI nor any later trigger accepts a different source as
  a parameter — changing the source is a deliberate, separate
  administrative act (edit the recorded configuration).
- Installations without a git working copy (e.g. install-medium
  payloads) clone the recorded repository URL into a platform-owned
  location on first update and continue from there.

### 2.3 Behaviour

- `oaap update --check` (and as the first phase of every run): fetch,
  then report current version/revision, available version/revision,
  and a short change log. No changes to the system.
- `oaap update`: apply — update the working copy (fast-forward only),
  copy the platform files into the installation, rebuild the core
  service images, restart core services, then verify that the core
  services report healthy. The applied revision is recorded.
- **No-op guarantee:** when the node is already at the available
  revision, the engine installs no code, rebuilds no image and restarts
  no container, and says so. It does still run the consistency steps
  below — those are about the node, not about the code.
- **Consistency steps MUST come from the version being installed, and
  MUST run on every trigger.** An update engine is the one program that
  replaces itself while running: everything after the copy step is still
  the *old* engine. A migration or repair written into the engine is
  therefore skipped by exactly the update that introduces it — and,
  because the next run finds nothing to install, skipped forever after.
  Two rules follow, and both are load-bearing:
  1. The steps live **outside** the engine, in an artefact the engine
     invokes **from the installed location** after copying, so the new
     version's steps run.
  2. They run **also when nothing is installed** — that, and only that,
     heals a node that already missed one.
  Every step MUST be idempotent and silent when there is nothing to do,
  and a failing step MUST NOT abort the run: it is reported and the
  update stands. *(Found on oaap-demo, 2026-08-09, which jumped eight
  versions in one go and received neither the store-source migration nor
  a unit repair. Both had been written, tested and shipped; the node
  simply never ran them, and nothing said so — the worst shape a defect
  can take.)*
- **An update reconciles the node's shipped store sources**
  (`oaap.apps.runtime` 2.9, RFC-0012 §4) and reports what it did. This
  is the one piece of node *state* an update touches, and it exists for
  a specific failure: a source used to be written once, at installation,
  and never looked at again, so the day one of our lists moved, every
  node in the field stranded — visibly only as an empty store. What the
  operator changed is never overwritten; the difference is reported
  instead.
- **Failure behaviour:** if the image build fails, the previously
  running containers keep running (build before switch); the engine
  reports the failure and leaves the system on the old version.
  Rollback in 0.1 is documented-manual (check out the previous
  recorded revision and re-apply); automatic rollback / A/B is a
  later increment.
- Every run writes a transcript (`/var/log/oaap-update.log` in the
  reference) and is idempotent.

### 2.6 Host care: the operating system under the platform (0.2)

**Why this is here.** On 2026-11-05 a kernel fix for a remotely
exploitable fault (CVE-2026-98432, reachable through exactly the kind
of listener our gateway had become) was measured across the fleet. The
fix had been *installed* on the internet node for two days and was
*not running*, because nobody had rebooted it in ten weeks; four nodes
had no automatic updates at all; on one node the auto-update package
was installed by hand and did nothing, because the periodic switch the
package is supposed to set was missing. Every one of these was a fact
on the machine, and the platform said nothing. 0.1 wrote "recommendation:
unattended-upgrades" and left the rest to the operator; 0.2 makes the
node measure it and say what to do.

What 2.6 is **not** (later stages of the same programme idea, each
its own RFC): matching installed packages against security advisories,
a notification channel, a reboot *protection* per instance and urgency
levels that may override it (the Jörg decisions D1–D5 of 2026-11-05
describe them). 2.6 is the measurement they will all stand on.

#### 2.6.1 The measurement

Every node measures its own **care state** — on the machine, with
administrator rights, never from inside a container (the portal cannot
read the package database, and must not be able to). The measurement
is a small set of facts, each with the rule that produces it:

- **Running kernel** and **newest installed kernel of the same
  flavour**. The flavour is the suffix behind the version (`-amd64`,
  `+rpt-rpi-v8`); a machine may hold several, and a newer kernel of a
  *different* flavour is not an update for this one.
- **Reboot required** = the two differ. **By comparison, never by the
  distribution's marker file.** The marker (`/var/run/reboot-required`)
  is written by a hook that ships *with the auto-update package*; on a
  node without that package the marker never appears, and "no marker"
  then reads as "no reboot needed" while a newer kernel waits on disk
  (oaapx02, 2026-11-05). The marker MAY be shown as a hint; it MUST NOT
  be the verdict.
- **Automatic updates**, one verdict from **three** parts, each named
  in the detail when it fails: the distribution's auto-update program
  is installed; its periodic switch is set (the package does **not**
  guarantee this — it writes the switch only when a pre-seeded answer
  says so, see 2.6.3); its timer is active. `ok` needs all three,
  `warn` is installed-but-not-running, `error` is not installed.
  Plus the time of the last run, when there was one.
- **Reboot window** — `off`, or the local hour the node reboots itself
  after a kernel update (2.6.3).
- **Gateway listeners** — whether the gateway's public listeners
  negotiate Multipath TCP, read from the gateway's own network
  namespace (`oaap.core.gateway` 0.2.18 says they must not; on the day
  of the CVE they did, by a language default nobody had chosen).
- **The time of the measurement.** A fact without its time is a
  trap: a status read right after a reboot describes the old kernel.

The node keeps the latest measurement in one file beside the registry
(`host-care.json` in the reference). It is refreshed by the node's
minute job when older than ten minutes, by every update run (the file
must exist the moment a node can show it), and on demand. A fresh
measurement right after a reboot is what closes the loop: "running
6.12.115" is the proof the reboot was the right advice.

#### 2.6.2 Three places, one measurement

The same file feeds three readers; none measures on its own, so they
can never disagree:

1. **`oaap status`** prints the care state as its own block — one line
   each for the kernel, for automatic updates, for the gateway —
   **with the recommendation as text** on every line that is not fine:
   "reboot required — running 6.12.111, installed 6.12.115: `sudo
   systemctl reboot` in a quiet hour". A technician must not have to
   know the package manager to read the line. When the measurement is
   missing or older than a day, the block says so instead of guessing.
2. **The portal** shows a `server_admin` a band with the same lines on
   the app overview and on the health page, and the health page's node
   table carries the facts. Only `server_admin`: the machine is the
   operator's, and a tenant administrator can do nothing about a
   kernel (telling tenants about a planned reboot is D4 of the later
   RFC, not this).
3. **`/fleet/status`** carries the facts as the `host` block and the
   three attention kinds (`oaap.fleet.status` 0.5), so the operator's
   inner node sees "needs a reboot" across the whole fleet without a
   login — the view that was missing on 2026-11-05.

#### 2.6.3 Two settings the platform writes

Hand-editing the same two things on every node is how a fleet drifts;
the platform writes them, in **a file of its own** that the package
manager reads beside its defaults, never by editing the distribution's
files:

- **`oaap node care auto-updates on`** installs the distribution's
  auto-update program **and writes the periodic switch itself**
  (reference: `/etc/apt/apt.conf.d/52oaap-care`, with the pre-seeded
  answer set first so the package's own file appears too). It changes
  **no origins**: the distribution's security origin is what gets
  installed automatically, and nothing else — a vendor kernel origin
  (Raspberry Pi) stays out unless the operator adds it by hand, because
  it brings firmware jumps with it (Jörg's decision, 2026-11-05). The
  installer runs this on every new node; an updated node is *told* in
  the care state when it is missing and is not switched on behind the
  operator's back.
- **`oaap node care reboot-window HH:MM | off`** — with a window set,
  the node reboots itself at that local hour **when, and only when, a
  newer kernel is installed than the one running** (the distribution's
  own mechanism, `Automatic-Reboot` with `Automatic-Reboot-Time`; also
  with users logged in, since a node is headless and an operator's
  idle shell must not keep a security fix from running). **Off by
  default**: when a node reboots is the operator's decision per node
  (after the backup, D1), and the settings file says in a comment who
  wrote it and why. The window is shown in all three places of 2.6.2.
  One more thing the window needs, learned on oaapx02: the
  distribution's mechanism reboots only when its **marker file** exists,
  and the marker is written by a hook that runs when *the auto-update
  program* installs a kernel — a kernel installed before the switch was
  set never gets one. So with a window set, the measurement **writes
  the marker itself** whenever the comparison of 2.6.1 says the reboot
  is required. That is the only system file the measurement touches,
  and only with a window set.

Both commands require local administrator rights, are idempotent, and
re-measure when done, so the status answers the change at once.

## 3. Configuration

- Recorded source: repository URL, branch/ref, working-copy path
  (set at install; changeable only by an administrator on the node).
- Reserved: update channel (e.g. `stable`/`testing`), maintenance
  windows (for the schedule trigger).
- Host care (2.6): the auto-update switch and the reboot window, in
  one file of the platform's own under the package manager's
  configuration directory (`/etc/apt/apt.conf.d/52oaap-care` in the
  reference); the latest measurement in `host-care.json` beside the
  registry, world-readable, facts only.

## 4. Security requirements

- The update trigger is privileged: CLI requires root; the future
  portal trigger requires the `server_admin` role (RFC-0008 — updating
  the platform is server administration, not app-facing) and runs
  through the host-task channel, never as the web process.
- **Source pinning:** no trigger can inject a source, ref, or payload;
  the engine only ever pulls the recorded source (same principle as
  deploy tokens: requests carry intent, never content).
- Transport integrity: the source is fetched over authenticated
  channels (HTTPS/SSH git). Signed releases (tag signatures) are a
  planned hardening step, required before the schedule trigger ships.
- Updates must not weaken the platform: secrets, app data, and the
  instance registry are never rewritten by an update; gateway
  default-deny must hold before and after.
- Host care (2.6): the measurement runs with administrator rights but
  **writes only its own file** (and, with a reboot window set, the
  distribution's reboot marker — 2.6.3); the two settings touch only the
  platform's own configuration file; the portal reads and never writes;
  nothing but the kernel's name and the verdicts leaves the node (no
  package list — a package list is a map for an attacker).

## 5. Conformance tests (described)

1. **Update happy path:** a node behind the recorded source updates
   with one CLI action; afterwards the new version is visible
   (`oaap status`, login greeting) and all core services are healthy.
2. **No-op:** running the engine on an up-to-date node reports so and
   installs no code, rebuilds no image and restarts no container. The
   consistency steps of test 8 still run; on a node that is already
   consistent they change nothing and say so.
3. **Apps and data untouched:** app instances keep running through a
   core update; storage, secrets (`OAAP_APP_SECRET`), and the
   registry are byte-identical afterwards.
4. **Build failure is safe:** an update whose image build fails
   leaves the old containers running and the old version recorded.
5. **Source pinning:** the CLI offers no way to update from a
   different repository/ref; the engine uses the recorded source even
   if the environment suggests another.
6. **Check is read-only:** `--check` performs no system change.
7. **Medium-installed nodes:** a node installed without a git working
   copy acquires one from the recorded URL on first update and passes
   test 1.
8. **The engine cannot skip its own new steps:** a node several versions
   behind, whose target version adds a consistency step, has that step
   applied by the single update — not by a later one. Running the engine
   again immediately changes nothing further and reports nothing new
   (idempotence), and a node that missed a step under an older engine
   has it applied on the next run even though there is no code to
   install. A step that fails is reported and leaves the update
   standing.
9. **Reboot verdict by comparison (2.6.1):** a node whose newest
   installed kernel of the running flavour is newer than the running
   one reports `reboot_required` even when no marker file exists; a
   node whose newest installed kernel of *another* flavour is newer
   does not.
10. **Three parts, one verdict (2.6.1):** with the auto-update program
    installed but the periodic switch missing, the verdict is `warn`
    and the detail names the switch; with the switch present and the
    timer inactive, the detail names the timer.
11. **Three places, one measurement (2.6.2):** `oaap status`, the
    portal band and `/fleet/status` show the same kernel pair and the
    same verdicts, taken from one file; after a fresh measurement all
    three change together.
12. **The switch is written, not assumed (2.6.3):** `auto-updates on`
    on a node where the package is already installed without the
    switch leaves the node with the switch set; running it again
    changes nothing and says so.
13. **The window is a node setting (2.6.3):** `reboot-window 04:15`
    appears in the care state of all three places; `off` removes it;
    neither command touches the distribution's own files.

## 6. Dependencies

`oaap.core.host` (installation layout, recorded configuration).
The portal trigger will additionally depend on `oaap.core.portal`
and the host-task channel. Host care (2.6) is read by
`oaap.fleet.status` 0.5 (`host` block) and states a rule of
`oaap.core.gateway` 0.2.18 (plain TCP listeners).

## 7. Maturity

`draft` — 0.1 target: CLI trigger implemented in the reference and
proven on the real fleet (oaap-test first, then all four nodes);
tests 1–7 described above executed on real hardware. 0.2 candidates:
portal trigger via host-task channel, signed releases, update
channels, schedule trigger.

## German summary / Deutsche Zusammenfassung

Jeder Knoten hat EINE Update-Engine mit drei Auslösern: **CLI
(`oaap update`, in 0.1 umgesetzt)**, Portal-Button und Zeitplan (beide
reserviert). Die Plattform merkt sich bei der Installation ihre
**Quelle** (Git-Repo, Branch, Arbeitskopie); Update heißt immer „die
hinterlegte Quelle neu ziehen" — kein Auslöser kann eine andere Quelle
mitgeben (gleiches Prinzip wie beim Deploy-Hook). `oaap update --check`
zeigt nur, was sich ändern würde; `oaap update` wendet an: pull (nur
fast-forward), Plattformdateien kopieren, Core-Images neu bauen,
Services neu starten, Gesundheit prüfen, Revision festhalten.
Garantien: auf aktuellem Stand passiert nichts; schlägt der Build
fehl, laufen die alten Container weiter; App-Instanzen, Daten und
Secrets werden nie angefasst. Stick-Installationen (ohne Git-Kopie)
klonen beim ersten Update das hinterlegte Repo. Rollback ist in 0.1
dokumentiert-manuell; signierte Releases und automatische Updates
kommen, bevor der Zeitplan-Auslöser scharf wird.

## Deutsche Zusammenfassung (0.2 — Pflegestand des Knotens, §2.6)

**Anlass (05.11.2026, CVE-2026-98432):** Der Kernel-Fix lag auf dem
Internet-Knoten zwei Tage **installiert** und lief nicht, weil seit zehn
Wochen kein Neustart war; vier Knoten hatten gar keine automatischen
Updates; auf einem Knoten war das Auto-Update-Paket von Hand installiert
und tat nichts, weil der Schalter fehlte, den das Paket setzen soll.
Lauter Tatsachen auf der Maschine — und die Plattform hat keine davon
gesagt. Jörgs Entscheidung: „Eine Prüfung mit Empfehlung sollten wir in
oaap aufnehmen.“ Das ist §2.6.

**Die Messung (2.6.1)** macht jeder Knoten selbst, auf der Maschine, nie
aus einem Container: laufender Kernel und neuester installierter Kernel
**derselben Bauart**; daraus **Neustart nötig** — durch Vergleich, **nie
aus der Markierungsdatei** (die schreibt ein Hook, der nur mit dem
Auto-Update-Paket kommt; ohne das Paket heißt „keine Markierung“ gar
nichts — oaapx02). **Automatische Updates** als ein Urteil aus **drei**
Teilen (Programm da, Schalter gesetzt, Zeitgeber aktiv — das Paket allein
setzt den Schalter nicht), plus letzter Lauf. **Neustart-Fenster** (aus
oder Uhrzeit). **Gateway-Listener**: handeln sie Multipath TCP aus
(sollen sie nicht, `oaap.core.gateway` 0.2.18). Und der **Zeitpunkt** der
Messung — direkt nach einem Neustart beschreibt ein alter Wert den alten
Kernel.

**Drei Orte, eine Messung (2.6.2):** `oaap status` druckt den Pflegestand
als eigenen Block, je eine Zeile Kernel / Auto-Updates / Gateway, **mit
der Empfehlung als Text** („Neustart nötig — läuft 6.12.111, installiert
6.12.115: `sudo systemctl reboot` in einer ruhigen Stunde“). Das Portal
zeigt dem `server_admin` ein Band mit denselben Zeilen auf der
App-Übersicht und der Gesundheitsseite, nur ihm — ein Mandanten-Admin
kann an einem Kernel nichts tun (Mandanten über einen geplanten Neustart
informieren ist D4 des späteren RFC). Der Flottenstatus trägt die Fakten
als Block `host` (0.5). Alle drei lesen **dieselbe Datei**
(`host-care.json` neben der Registry), keiner misst selbst — also können
sie sich nicht widersprechen. Die Datei frischt der Minutenlauf auf, wenn
sie älter als zehn Minuten ist, jedes Update, und `oaap node care` auf
Zuruf.

**Zwei Einstellungen, die die Plattform schreibt (2.6.3)** — in einer
**eigenen Datei** (`/etc/apt/apt.conf.d/52oaap-care`), nie in denen der
Distribution: `sudo oaap node care auto-updates on` installiert das
Auto-Update-Programm **und schreibt den Schalter selbst**; es ändert
**keine Quellen** — nur die Sicherheitsquelle der Distribution wird
automatisch eingespielt, die Raspberry-Pi-Kernelquelle bleibt bewusst
draußen (Jörg, 05.11.). Der Installer macht das auf jedem neuen Knoten;
ein aktualisierter Knoten bekommt es nur **gesagt**, nicht heimlich
eingeschaltet. `sudo oaap node care reboot-window 04:15 | off`: Mit
Fenster startet der Knoten sich zu dieser Uhrzeit selbst neu — **nur
wenn** ein neuerer Kernel installiert ist als der laufende, auch mit
angemeldeten Benutzern (ein Knoten ist kopflos; eine vergessene Shell
darf keinen Sicherheitsfix aufhalten). **Ab Werk aus**: Wann ein Knoten
neu startet, entscheidet der Betreiber je Knoten (nach dem Backup, D1).
Und die Lehre von oaapx02: Der Mechanismus der Distribution startet nur
neu, wenn die **Markierungsdatei** da ist — und die schreibt ein Hook
nur, wenn das Auto-Update-Programm selbst einen Kernel einspielt. Mit
gesetztem Fenster schreibt darum die Messung die Markierung selbst,
sobald der Vergleich „Neustart nötig“ sagt.

**Nicht in 0.2** (spätere Stufen, je ein eigener RFC): Abgleich gegen
Sicherheitsmeldungen, ein Benachrichtigungsweg, Neustart-Schutz je
Instanz und Dringlichkeitsstufen (D2–D5 vom 05.11.). 2.6 ist die
Messung, auf der das alles stehen wird.

## Nachtrag 0.1.3 — das Programm, das sich selbst ersetzt

Ein Update-Programm ist der einzige Fall, in dem ein Programm sich
austauscht, während es läuft. `sudo oaap update` führt die Fassung aus,
die beim Tippen des Befehls auf der Platte lag — die **alte**. Alles
nach dem Kopieren der neuen Dateien ist immer noch der alte Ablauf.

Das hat eine Folge, die niemand von allein sieht: **Ein Reparatur- oder
Migrationsschritt, den eine neue Fassung ins Update-Programm schreibt,
wird von genau dem Update übersprungen, das ihn mitbringt.** Und danach
nie mehr — denn beim nächsten Lauf gibt es nichts zu installieren, und
das Programm steigt vorher aus.

Auf oaap-demo ist das am 09.08.2026 passiert: Der Knoten sprang von
0.1.18 auf 0.1.26 und bekam weder den Abgleich der Store-Quellen noch
die Reparatur der Deploy-Worker-Unit. Beides war geschrieben, geprüft
und ausgeliefert. Der Knoten hat es nur nie ausgeführt — und **nichts
hat das gemeldet**. Das ist die unangenehmste Form eines Fehlers: Die
Arbeit ist getan, der Nachweis sieht gut aus, und im Feld wirkt sie
trotzdem nicht.

Zwei Regeln, beide tragend:

1. Die Schritte liegen **außerhalb** des Update-Programms und werden
   **aus dem installierten Verzeichnis** aufgerufen — also aus dem
   neuen Stand.
2. Sie laufen **auch dann**, wenn es nichts zu installieren gibt. Nur
   das heilt einen Knoten, der einen Schritt bereits verpasst hat.

Dazu die Bedingungen, ohne die Regel 2 lästig würde: Jeder Schritt muss
wiederholbar sein und schweigen, wenn nichts zu tun ist. Und ein
Schritt, der scheitert, darf den Update-Lauf nicht abbrechen — er wird
gemeldet, das Update bleibt stehen.

Das „Nichts geändert"-Versprechen bleibt bestehen, aber es meint jetzt
präzise, was es meinen sollte: kein Code installiert, kein Image gebaut,
kein Container neu gestartet. Über den Zustand des **Knotens** hat es
nie eine Aussage gemacht.
