# oaap.data.backup — Platform Backup & Restore

- **ID:** `oaap.data.backup`
- **Version:** 0.1.3
- **Maturity:** draft (0.1.2 extends "the address travels" to every name
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
- The app storage of every instance

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

### 2.2 Creating a backup

`oaap backup create [--to <path>]` — creates the archive and prints its
location. Requirements:

- **Consistency:** 0.1 is an *offline-consistent* backup: app
  containers are stopped for the copy and restarted afterwards. The
  command MUST announce this before stopping anything and SHOULD report
  the downtime afterwards. (Online/incremental backups are a later
  version.)
- The target MUST NOT lie inside the platform data directory (a backup
  that dies with the machine is not a backup). The command MUST refuse
  such a target and say why.
- The archive MUST be created with restrictive file permissions, and
  the command MUST state clearly that the file contains all platform
  secrets and user data (see section 4).

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

### 2.4 Relocation procedure

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
