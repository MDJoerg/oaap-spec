# oaap.data.backup — Platform Backup & Restore

- **ID:** `oaap.data.backup`
- **Version:** 0.1.0
- **Maturity:** draft
- **Based on:** RFC-0001 (capability model), RFC-0003 (node topology —
  0.1 covers a single-node platform), App Deployment Contract (storage
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

It MUST NOT contain container images (they are rebuilt or pulled from
the recorded package sources on restore) and SHOULD NOT contain caches,
logs, or ephemeral protection state (e.g. login-throttling counters —
a restored platform starts those fresh). TLS/ACME material MAY be
included; it is re-obtainable, and after a relocation the certificates
are re-issued anyway.

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

## 6. Dependencies

`oaap.core.host` (installer modes, prepare), `oaap.apps.runtime`
(registry, package sources, contract delivery). The core capabilities
are restored as part of the flow, not from the backup.

## 7. Maturity

`draft` — becomes `beta` once tests 1–4 pass on the reference platform
(VM-to-VM round trip); test 5 is proven by the first real relocation.
