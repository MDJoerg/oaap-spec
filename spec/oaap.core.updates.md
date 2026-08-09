# oaap.core.updates — Platform Updates

- **ID:** `oaap.core.updates`
- **Version:** 0.1.3
- **Maturity:** draft — accepted by Jörg 2026-08-06 (CLI trigger
  implemented and validated on real hardware); 0.1.1 (2026-08-07)
  updates the reserved portal-trigger role to `server_admin` per
  RFC-0008; 0.1.2 (2026-08-09) adds the reconcile step for shipped
  store sources, per RFC-0012 §4; 0.1.3 (2026-08-09) states where
  consistency steps must live and when they must run — the engine
  replaces itself while running, so a step written into it is skipped
  by the very update that introduces it (found on oaap-demo)
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
capability; this spec is the per-node engine it will call).

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

## 3. Configuration

- Recorded source: repository URL, branch/ref, working-copy path
  (set at install; changeable only by an administrator on the node).
- Reserved: update channel (e.g. `stable`/`testing`), maintenance
  windows (for the schedule trigger).

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

## 6. Dependencies

`oaap.core.host` (installation layout, recorded configuration).
The portal trigger will additionally depend on `oaap.core.portal`
and the host-task channel.

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
