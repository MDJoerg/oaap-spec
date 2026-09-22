# oaap.data.backup — Platform Backup & Restore

- **ID:** `oaap.data.backup`
- **Version:** 0.4
- **Maturity:** draft (0.4 implements RFC-0029 D5 and D5b: an archive of
  ONE tenant, which says of itself that it cannot be restored; and a
  tenant may be left out of the node archive, on three conditions that
  are not optional -- the archive records what it omitted, the restore
  says it instead of letting it be discovered, and the tenant reads it
  in their own audit log; 0.2.1 implements RFC-0029 D2: the state of a
  backup is readable -- running, done, failed, never set up -- and each
  fact appears on the side that can verify it; 0.2 implements RFC-0029 D3: the apps stop for the
  COPY only, compression runs afterwards with them back up -- measured
  cost before the change was 487 s of downtime for 8.0 GB, of which
  almost all was gzip; 0.1.5 adds the tenant audit log to the required
  content -- the first real restore drill produced a node that came back
  complete and said "No entries yet", 2026-09-05; 0.1.4 names the instance tree under `tenants/` as
  required content and makes completeness a check against the finished
  archive — written after a live node produced a 9 KB "backup" of 899 MB
  and said nothing, 2026-09-05; 0.1.2 extends "the address travels" to every name
  an instance owns — canonical plus aliases, RFC-0018; 0.1.1 draws the
  line between what belongs to the **service** and travels — an
  instance's own address, RFC-0009 — and what belongs to the **machine**
  and stays behind: node profiles, RFC-0011)
- **Based on:** RFC-0001 (capability model), RFC-0003 (node topology —
  0.1 covers a single-node platform), RFC-0009 (instance address),
  RFC-0018 (canonical name plus aliases),
  RFC-0011 (node profiles), App Deployment Contract (storage
  guarantee "included in platform backup"), `oaap.core.host` (installer
  `restore` mode), `oaap.apps.runtime` (instance registry and package
  sources)

## 1. Purpose

One command produces a **self-contained backup** of everything the
platform cannot recreate on its own; the installer's `restore` mode
turns a prepared machine plus that backup back into the same platform.
Two scenarios drive 0.1:

1. **Disaster recovery** — the machine dies; a replacement is running
   again from the last backup.
2. **Relocation** ("Umzug") — the platform moves to different hardware,
   e.g. from a hosted test machine to the customer's own server. This
   is a first-class scenario, not an afterthought: the Bernd pilot ends
   with exactly this move, and it serves as the conformance proof.

Scheduled backups, retention, off-site targets, and backup verification
by a service partner are later versions (they connect to
`oaap.ops.monitoring`). 0.1 is the manual, complete, restorable backup.

## 2. Interface

### 2.1 Backup content

A backup is a **single archive** with a **backup manifest** (format
version, platform version, creation time, source hostname, list of
contained instances). It MUST contain:

- Platform configuration (data-directory layout, registered external
  hostnames, level-1 port assignments)
- Identity data: the user store with password hashes and roles
- The app-instance registry, including each instance's configuration,
  package source, channel, and secrets (`instance.env`,
  `OAAP_APP_SECRET`) — without these a restore cannot deliver the
  contract guarantees
- The app storage of every instance **and its `instance.env`**, wherever
  the platform currently keeps them. Since RFC-0026 that is the tenant
  tree (`tenants/<tenant-id>/instances/<instance-id>/`); records written
  before it still lie flat under `apps/<key>/`, and an archive taken on
  a node holding both MUST carry both (0.1.4)

- The **tenant audit log** (`oaap.core.tenant` 1.7). It is the
  counterweight to "a `server_admin` may do everything on this node"
  (RFC-0022 D5): the customer's own record of what the operator did
  inside their tenant. A restore that drops it hands the operator a
  clean slate, which is the one thing the log exists to prevent -- and
  it does so invisibly, because everything else comes back (0.1.5)

- The **tenant store** (`oaap.core.tenant` 1.1). Without it the
  restored users and instances name tenants the node does not have,
  and the resolution rule of `oaap.core.tenant` 2.2 refuses them —
  correctly, and unhelpfully. A whole-node backup therefore always
  carries the whole tenant store, even when only one tenant exists.

It MUST NOT contain container images (they are rebuilt or pulled from
the recorded package sources on restore) and SHOULD NOT contain caches,
logs, or ephemeral protection state (e.g. login-throttling counters —
a restored platform starts those fresh). It MUST NOT contain the
node's **profiles** (`oaap.core.host` 2.5) as restorable state; the
manifest SHOULD record them as information (see 2.3). TLS/ACME material MAY be
included; it is re-obtainable, and after a relocation the certificates
are re-issued anyway.

**Per-tenant backup (RFC-0022 D7) is not this version.** A backup here
is a whole node. Cutting one tenant out of it is a different operation
with a different failure mode — a tenant export is a customer's
complete data set in one file — and it arrives with `oaap.core.tenant`
0.2, together with the roles that decide who may ask for it.

#### 2.1.1 The archive of one tenant (0.4, RFC-0029 D5)

An implementation MAY offer an archive of a **single tenant**: that
tenant's instance data, its registry entries, its users, its audit log
and, where the node carries a data store, its own schema — and nothing
belonging to anybody else.

- It MUST be **distinguishable from a node archive by its manifest**,
  not merely by its file name. An archive that must not be handed to
  the installer must not look like one that may, and a restore tool
  that encounters it MUST say what it is rather than "this is not a
  backup".
- It MUST state **in the archive itself** whether it can be restored.
  Where per-tenant restore is not implemented, that statement is
  `false` and the reason belongs with it: a whole-node restore
  *replaces* a machine, restoring one tenant *merges* into a running
  node that has other customers on it, and the questions that makes
  hard — an instance that exists now and did not then, a port somebody
  else has taken, a name another tenant has claimed since, a user who
  is in both — are unanswered. Answering them badly loses another
  customer's data while restoring this one's.
- **What it guarantees is existence, not recovery**, and it MUST say so
  in those terms. That is worth having on its own: the data is outside
  the machine.
- It SHOULD stop only the containers of that tenant, and only for the
  copy. The other customers on the node have no part in this.
- The completeness check of 2.2 applies to it unchanged, against that
  tenant's instances.

#### 2.1.2 Leaving a tenant out of the node archive (0.4, RFC-0029 D5b)

An implementation MAY let the operator **exclude** a tenant from the
node archive. This changes what the operator's archive *is*: from
"everything on this machine" to "everything I am responsible for" —
more honest about the duty, and a smaller blast radius for a stolen
archive. It is permitted only with all three of the following.

1. **The archive MUST record what it deliberately left out** — the
   tenants it contains and the tenants it omits *by configuration*,
   with the reason. Without this, a restore silently produces a node
   with a customer missing, discovered on the day the original is gone.
2. **The restore MUST say it, not discover it.** An excluded tenant's
   instances come back in the registry with no data behind them. The
   implementation MUST name them and MUST NOT start them as if they
   were whole: an app that comes up on an empty disk looks wiped, and
   somebody will believe it. The record stays — an instance silently
   vanishing from the registry is worse than one that says where its
   data is.
3. **The tenant MUST be able to see it.** Exclusion moves the risk onto
   the customer, which is a contract statement and not a checkbox. The
   setting MUST carry a reason in the operator's own words and MUST
   appear in **that tenant's own audit log** (`oaap.core.tenant` 1.7).
   A customer the operator does not back up must not learn it from the
   outage. An implementation MUST refuse an exclusion with no reason.

The completeness check of 2.2 MUST be **narrowed, never weakened**: the
excluded tenant's instances are absent on purpose, every other instance
still has to be in the archive.

### 2.2 Creating a backup

`oaap backup create [--to <path>]` — creates the archive and prints its
location. Requirements:

- **Consistency:** this is an *offline-consistent* backup: app
  containers are stopped for the copy and restarted afterwards. The
  command MUST announce this before stopping anything and MUST report
  the downtime afterwards. (Online backups are a later version;
  incremental ones are **decided against** — RFC-0029 D3.)
- **The apps stop for the copy, not for the compression** (0.2,
  RFC-0029 D3). The archive is written uncompressed while the
  containers are down, the containers are started again, and only then
  is it compressed. Measured before the change: 487 seconds of downtime
  for 8.0 GB, of which almost all was gzip. The implementation MUST
  restart the containers even when the copy failed — a backup that
  leaves the node stopped has done more damage than the one it
  prevented — and MUST NOT leave a partial file behind that could be
  mistaken for an archive.

  The price is holding the data twice for a few minutes. The command
  MUST therefore check beforehand that the target has room for it and
  refuse with a clear message, rather than discovering a full disk in
  the middle of the night.
- **The measured downtime MUST be recorded** where the platform can
  read it back (0.2). Not for a report: RFC-0029 D1 puts the schedule
  in the portal, and the page owes its operator the sentence "your apps
  will stop for about this long" — with **this node's** last measured
  figure. A number from a manual is always somebody else's machine.
- **The state MUST be recorded on every outcome** (0.2.1, RFC-0029 D2),
  and `running` MUST be written *before* the containers are stopped.
  Four states have to stay distinguishable — running, done, failed,
  and never set up — because they need four different answers, and the
  last two are the two where somebody has to act. An implementation
  that records only successes cannot tell them apart.

  A record MUST NOT be presented as a failure merely because it is
  older than the field that would prove it succeeded. (Found the day
  this was written: a health page called a run "failed — no reason
  recorded" that had in fact written a 1.6 GB archive, because the
  record predated the state field.)
- **Each fact is shown by the side that can verify it.** Whether a copy
  arrived somewhere else, and whether its checksum matched, is known
  only to the receiving side. The node that produced the archive MUST
  NOT claim it; where it has no such knowledge, saying so is the
  correct output.
- The target MUST NOT lie inside the platform data directory (a backup
  that dies with the machine is not a backup). The command MUST refuse
  such a target and say why.
- The archive MUST be created with restrictive file permissions, and
  the command MUST state clearly that the file contains all platform
  secrets and user data (see section 4).
- **Completeness MUST be measured against the finished archive** (0.1.4)
  and not asserted by the implementation. Before an archive is put in
  place, the command MUST check, for every instance in the registry
  that has a data directory, that the archive holds that directory. If
  any is missing, the command MUST fail and MUST NOT leave an archive
  behind — an incomplete backup that calls itself complete is worse
  than none, because it is discovered on the day the original is gone.

  This rule exists because it was broken. On 2026-09-05 a backup on a
  live node was 9 KB where the node held 899 MB: since the instance
  tree moved to `tenants/…` (RFC-0026), the implementation still copied
  the list of paths it had always copied — registry and users, no app
  data, no `instance.env`. Nothing failed. The archive restored, onto
  an empty platform. A path list can be spelled correctly and be
  empty; only the archive knows what is in it.

### 2.3 Restore

Restore is an **installer mode** (`restore`, see the mode table in
`oaap.core.host` §2.1): it behaves like `bootstrap`, except that all
state comes from the backup instead of an empty initialization:

1. Preflight as in bootstrap (the machine is prepared the same way).
2. Install and start the core, then seed platform state from the
   backup: configuration, identity data, registry, instance secrets,
   app storage.
3. Re-create every app instance from the restored registry: build or
   pull from the recorded package source, regenerate gateway
   configuration, start.
4. **No setup wizard, no setup token** — the admin users come from the
   backup. The installer prints the login URL instead.
5. **Tenants the archive left out are named before anything starts**
   (0.4, 2.1.2 condition 2), and their instances are left **dormant**
   with the reason the archive recorded.

Rules:

- Restore MUST refuse to run on a machine that already hosts a
  platform (same protection as `bootstrap`).
- The restored platform MUST come up on the **new machine's** address.
  Registered external hostnames are kept; if DNS still points at the
  old machine, the installer says so and continues — switching DNS is
  the operator's next step, not a restore failure.
- `OAAP_APP_SECRET` values MUST survive restore unchanged, so app data
  that depends on them (sessions, signed values) keeps working. The
  contract guarantee that this secret never appears in *app storage*
  is unaffected — the platform backup carries it in the registry part.

**What belongs to the service travels; what belongs to the machine does
not.** The line is drawn once, and both sides are stated out loud
rather than left to be discovered:

- An instance's **own public hostnames** (RFC-0009, and its aliases per
  RFC-0018) are part of the instance and MUST be restored with it —
  clients address the app, not the box it happens to run on. Since those
  names still resolve to the old machine right after a relocation, the
  restore MUST say so **per name** (canonical and every alias) on each
  affected instance; pointing DNS at the new machine is the operator's
  next step, exactly as for the node's external hostname above.
- The node's **profiles** (RFC-0011) describe the machine and MUST NOT
  be restored: a workbench backup restored onto a production box must
  not bring developer powers along. The restore MUST NOT do this
  silently — it names the profiles the backup came with and how to set
  them again, so an operator restoring a workbench is not left
  wondering why the portal refuses to create instances.

### 2.4 The schedule (0.3, RFC-0029 D1)

A node MAY run its backup on a schedule. Where a schedule exists, the
platform owns **when** it runs and **how many archives stay**; it does
not own **whether** the node has one at all, nor **where** the archives
go.

- **systemd (or the node's equivalent) is the truth; the recorded
  schedule is a view.** The platform writes down what the timer
  *actually reports* — the armed state and the next run asked of the
  timer itself, never derived from what was last set. A page must not
  claim a schedule that is not armed, and a hand edit made on the
  machine must appear rather than be papered over.
- **Exactly one writer.** The recorded view is written by the platform
  alone. An installer that also wrote it would be a second answer to
  one question.
- **`server_admin` only.** Changing the hour stops **every** app on the
  node, including the apps of tenants who did not choose it. Re-checked
  where the change is applied, never only at the button.
- **The page MUST state the cost next to the time field**, using **this
  node's** last measured downtime (2.2). A node that has never backed
  up MUST say so rather than borrow a number — a figure from a manual
  is always somebody else's machine.
- **The target path is NOT settable through the platform's remote
  surfaces.** An archive holds every secret on the machine; where it is
  written is decided at the machine. The path MAY be displayed.
- **Retention at the source has a floor of one.** An archive deleted
  the moment it was copied away leaves nothing when the copy turns out
  to be silently damaged.
- **Setting a schedule up in the first place MAY stay outside the
  platform** while the form is still being proven, because that step is
  what chooses the target. A node without a timer MUST be told so
  plainly — "never set up" is a different answer from "switched off",
  and both differ from "it failed".

### 2.5 Relocation procedure

The documented Umzug flow, built from the two operations above:

1. Prepare the new machine (`prepare` mode covers server readiness).
2. `oaap backup create` on the old machine, transfer the archive.
3. `restore` on the new machine; verify via LAN that login and all
   instances work.
4. Switch external access (DNS/DynDNS, port forwarding) to the new
   machine. The old platform MUST be stopped or its external access
   removed **before** the new one takes over the hostname — two live
   platforms answering for one name means certificate conflicts and
   split data.
5. Decommission the old platform (`oaap uninstall`) or keep it,
   demoted, as a test system.

## 3. Configuration

- Backup target path (provider-defined default outside the data
  directory)
- Optional content switches (include TLS material, include logs) —
  provider-defined; the defaults follow §2.1

## 4. Security requirements

- A backup archive is equivalent to full administrative access: it
  holds every platform secret, all password hashes, and all app data.
  Tooling MUST create it with owner-only permissions and MUST say what
  the file contains. Guarding the file at rest and in transit is the
  operator's responsibility in 0.1; archive encryption is a planned
  later version and providers MAY offer it already.
- Restore MUST NOT weaken a running platform: refusing to restore over
  an existing installation is a security rule, not only a safety rule.
- A restored platform MUST NOT carry over ephemeral protection state
  in a weakened form — throttling counters start fresh, the setup
  wizard stays disabled (admins exist), and no secret is regenerated
  silently.

## 5. Conformance tests (described)

1. **Create happy path:** on a platform with at least one app instance,
   `oaap backup create` produces an archive with restrictive
   permissions whose manifest lists platform version and all
   instances; afterwards the platform is fully running again.
1a. **The archive holds the data, not just the list** (0.1.4). On a node
   with instances in **two** tenants, the archive contains each
   instance's storage *with its contents* and each `instance.env`.
   Tested by reading the archive, never by reading the code — and on
   two tenants, because a node with one is the case in which the old
   flat path and the new one look alike. The same is asked of the
   **tenant audit log**: a node that has one and an archive that does
   not is not a backup of that node. Counter-test: an implementation
   that omits either MUST fail and leave no archive.

3b. **The log survives the round trip** (0.1.5). After conformance test
   3, `oaap tenant log` on the restored node shows the entries it
   showed before. Found by the first real restore drill, 2026-09-05:
   everything else came back and the log said "No entries yet" — which
   is exactly how the operator's record of their own actions would
   disappear without anyone noticing.
2. **Target safety:** a target inside the platform data directory is
   refused with a clear message; nothing is stopped or changed.
3. **Round-trip restore:** on a fresh machine, `restore` from the
   backup succeeds without a setup wizard; existing users log in with
   their old passwords and roles; every app instance runs with its
   storage contents present; `OAAP_APP_SECRET` values are unchanged.
4. **Existing platform protection:** `restore` on a machine with a
   platform refuses and changes nothing.
5. **Relocation:** after the documented Umzug flow, the registered
   external hostname serves the new machine with valid TLS and the
   old machine no longer answers. (Pilot proof: Bernd's real move to
   his own hardware.)

6. **Service travels, machine stays:** a backup taken from a node with
   a profile and an instance carrying its own public hostname, restored
   elsewhere, yields an instance that still has its hostname (with the
   restore saying that DNS still points at the old machine) and a node
   with **no** profile (with the restore naming what it dropped and how
   to set it again).
7. **Schedule in the portal** (2.4, 0.3): a `server_admin` changes the
    hour and the retention and the timer reports the new next run; the
    page shows this node's own last measured downtime beside the time
    field, and a node that never backed up says so instead of showing a
    number. A `support` sees the state but is offered no form, and the
    same request presented directly to the node is refused. There is no
    field for the target path. A node without a timer is told that
    plainly and offered no form. Switching the schedule off is
    distinguishable from never having set one up.

## 6. Dependencies

`oaap.core.host` (installer modes, prepare), `oaap.apps.runtime`
(registry, package sources, contract delivery). The core capabilities
are restored as part of the flow, not from the backup.

## 7. Maturity

`draft` — becomes `beta` once tests 1–4 pass on the reference platform
(VM-to-VM round trip); test 5 is proven by the first real relocation.

## Deutsche Zusammenfassung (v0.1.1)

**Eine Linie, zweimal angewandt:** Was zum *Dienst* gehört, zieht mit
um. Was zur *Maschine* gehört, bleibt zurück.

- Die **eigenen Adressen einer Instanz** (RFC-0009, samt Aliassen nach
  RFC-0018) gehören zur App und wandern deshalb mit — Kunden sprechen die
  Anwendung an, nicht den Kasten, auf dem sie zufällig läuft. Direkt nach
  einem Umzug zeigen diese Namen aber noch auf die alte Maschine; die
  Wiederherstellung sagt das jetzt für **jeden Namen** (Haupt- und
  Aliasname) jeder betroffenen Instanz ausdrücklich, statt es einen
  später beim Aufrufen entdecken zu lassen.
- Das **Knoten-Profil** (RFC-0011) beschreibt die Maschine und wandert
  deshalb **nicht** mit: Ein Werkbank-Backup, eingespielt auf einer
  Produktivmaschine, darf dort keine Entwicklerrechte mitbringen. Auch
  das passiert nicht stillschweigend — die Wiederherstellung nennt das
  Profil, das im Backup stand, und den Befehl, es bewusst wieder zu
  setzen.

## Deutsche Zusammenfassung (2.1.1/2.1.2, v0.4 — wessen Daten ein Archiv trägt)

**Das Archiv eines einzelnen Mandanten** (`oaap backup create --tenant
<kürzel>`): seine Instanzdaten, seine Registrierungseinträge, seine
Benutzer, sein Protokoll und, wo der Knoten einen Datenspeicher trägt,
sein eigenes Schema — und nichts, was jemand anderem gehört. Es stoppt
nur die Apps dieses Mandanten, und nur für das Kopieren; der Rest des
Knotens merkt nichts davon.

**Und es sagt von sich selbst, dass es nicht zurückgespielt werden
kann.** Das ist kein Mangel, den wir verschweigen, sondern der Grund,
warum es das Archiv überhaupt schon gibt: Eine Wiederherstellung des
ganzen Knotens **ersetzt** eine Maschine. Einen einzelnen Mandanten
zurückzuspielen heißt, ihn in einen **laufenden** Knoten
**hineinzumischen**, auf dem andere Kunden sitzen — und jede Frage, die
das schwer macht, ist offen: eine Instanz, die es jetzt gibt und damals
nicht; ein Port, den inzwischen jemand anders hat; ein Name, den sich ein
anderer Mandant genommen hat; ein Benutzer, den es in beiden gibt. Diese
Fragen falsch zu beantworten verliert die Daten eines anderen Kunden,
während man die dieses einen wiederherstellt. Was das Archiv also
zusichert, ist **Existenz, nicht Wiederherstellung** — die Daten liegen
außerhalb der Maschine. Das ist für sich genommen etwas wert.

**Einen Mandanten aus der Knotensicherung ausnehmen** ändert, was das
Betreiberarchiv *ist*: aus „alles auf dieser Maschine" wird „alles,
wofür ich geradestehe". Auf einem Knoten mit Kunden hält der Betreiber
heute jeden vollständigen Datenbestand jedes Kunden — dort, wo das
Sicherungsziel zufällig steht. Erlaubt ist das Ausnehmen nur mit **allen
drei** Bedingungen:

1. **Das Archiv schreibt auf, was es weglässt** — welche Mandanten drin
   sind und welche absichtlich nicht, mit Begründung. Ohne das erzeugt
   eine Wiederherstellung lautlos einen Knoten, dem ein Kunde fehlt;
   bemerkt an dem Tag, an dem das Original weg ist.
2. **Die Wiederherstellung sagt es, statt es entdecken zu lassen.** Die
   Instanzen des ausgenommenen Mandanten kommen zurück, ihre Daten
   nicht. Sie werden **benannt und nicht gestartet**: Eine App, die auf
   einer leeren Platte hochkommt, sieht aus wie gelöscht, und jemand
   wird das glauben. Der Eintrag bleibt aber stehen — eine Instanz, die
   lautlos aus der Registrierung verschwindet, ist schlimmer als eine,
   die sagt, wo ihre Daten sind.
3. **Der Mandant kann es sehen.** Das Ausnehmen verschiebt das Risiko
   auf den Kunden, und das ist eine Vertragsaussage, kein Häkchen. Also
   trägt die Einstellung eine Begründung in den Worten des Betreibers
   und steht im **Protokoll dieses Mandanten**. Ein Kunde, den der
   Betreiber nicht sichert, darf das nicht aus dem Ausfall erfahren.
   Ohne Begründung wird das Ausnehmen verweigert.

Die Vollständigkeitsprüfung wird dabei **enger gefasst, nicht
aufgeweicht**: Die Daten des ausgenommenen Mandanten fehlen absichtlich,
jede andere Instanz muss weiterhin im Archiv liegen.

