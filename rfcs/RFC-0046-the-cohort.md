# RFC-0046: The Cohort — A Training Landscape From a Template, and Back Again

- **Status:** **Accepted (2026-09-30)** — the six decisions were put to
  Jörg before the draft and answered the same day (§12); the RFC records
  them and the design that follows from them. Nothing built.
- **Date:** 2026-09-30
- **Authors:** Jörg (the training case, the template idea, the
  lifetime rule), Claude (measurements and write-up)
- **Depends on:** RFC-0007 (visibility groups), RFC-0022 (tenant as
  boundary), RFC-0025 (instance namespace), RFC-0027 (machine
  principals and API keys), RFC-0030 (the rehearsal — its expiry rule
  is *kept*, not extended), RFC-0034 (documents and file storage),
  RFC-0040 (the person behind the name), RFC-0043 (instance names for
  apps)
- **Extends:** `oaap.core.identity` (create on the node, first-login
  password change, dated deactivation and deletion, deletion itself),
  `oaap.apps.runtime` (resource limits per instance, seeded storage)
- **Driver:** Jörg's company trains SAP developers. Participants from
  larger companies arrive with laptops on which nothing may be
  installed; the fallback is a workplace in the browser. The
  `code-server` app (oaap-apps, 0.1.0–0.1.2, 2026-09-30) proved the
  workplace; what is missing is the hand that sets up **twelve of them**
  and clears them away again.

## Summary

A **cohort** is *N* seats in one tenant, each seat a user and their own
instances, all made from one **template file** and all removable with
one command. The platform gains a command family `oaap cohort` in stage
1 and a tenant-scoped management API in stage 2, so that the same work
can be done from a trainer's laptop or from an app with a
`tenant_admin` key (RFC-0027).

The RFC is deliberately small where the platform already has the
answer, and precise where it does not:

- **Already there:** the tenant as the course's boundary (RFC-0022), the
  per-participant filter of the launchpad (visibility groups, RFC-0007),
  instance names and addresses (RFC-0025/0043), backup and removal per
  instance, the two storage mounts of the workplace app (home and
  material).
- **Missing and specified here:** a template that is a file (§2); the
  seat and its seeding (§3); commands that are idempotent and report
  (§4); a **lifetime** with dated deactivation and deletion of users but
  never a timer on an instance (§5); four small identity extensions
  (§6); resource limits per instance (§7); the stage-2 API (§8).

The measurements that shaped it are in §0.

## 0. What was measured before this was written (2026-09-30)

On `oaap-test` and `oaapx01`, with the `code-server` app:

- A participant workplace is one wrapped container; the gateway is its
  door (WebSocket upgrade through the forward-auth: `101` with a
  session, `303` without). Visibility groups do exactly what a cohort
  needs: a user without the seat's group got `403` at login, one with it
  reached the workplace, `server_admin`/`tenant_admin` see all.
- **Seeding is the real work.** A useful SAP seat needs, per
  participant: the extension list, `~/.adtls/destinations.json` (ADT's
  systems), `~/.adtls/SAPUILandscape.xml` (ADT's RFC systems; the
  language server reads the path from `SAPLOGON_LSXML_FILE`), a saved
  `.code-workspace` (an `abap:` folder survives only in a saved
  workspace), the course material, and an API key for the AI plugin as
  an instance secret. None of this is app code; all of it is *data per
  seat*.
- **Users cannot be created on the node by command.** `oaap app user`
  knows `list`, `password`, `unbind`; creation goes through the portal
  or identity's `/internal/users` with the platform key. Identity cannot
  delete a user, only deactivate (spec 2.4 left deletion open).
- **The reference sets no resource limits.** A container with ADT, CDS
  and the AI plugin sat at 1.9 GB; ADT's language server alone at
  230 MB RSS. Twelve of those on one node are a sizing question, and
  one participant's `npm install` is everyone's problem without limits.
- The portal's management endpoints (`/instances/new`, `/store/install`,
  `/instances/<n>/visibility`, users) are session-bound forms, not an
  API behind `/verify`. RFC-0027 named "an OpenAPI for automation" as
  its third driver and built none.

## 1. Vocabulary

| Word | Meaning |
| --- | --- |
| **Cohort** | One training run: *N* seats in one tenant, made from one template, with one lifetime. Has a name (`kurs-2026-10`), used as prefix. |
| **Seat** | One participant: a user, their group, their instances, their material. Numbered (`01`…`N`) or named. |
| **Template** | A file that says what a seat consists of and how the cohort lives. Import = copy in, export = copy out. |
| **Seed** | Files written into a fresh instance's storage before its first start: settings, ADT systems, workspace. Data, never code. |
| **Material** | The course directory, copied into each seat's `material` mount. Replaceable during the course without touching the seat's home. |
| **Handout** | The one-time file with usernames and initial passwords, produced at creation, never reproducible. |
| **Trainer** | The `tenant_admin` who runs the cohort. Sees every seat by role. |

## 2. The template is a file (D5)

A YAML file the trainer keeps in their own repository. The node stores a
copy with every cohort it created, so that `list` and `reset` know what
a seat was made from even if the trainer's file changed since.

```yaml
oaap_cohort: "0.1"
name: kurs-2026-10                 # cohort name; prefix of users and instances
tenant: schule                     # D1: one tenant, prefixes inside it
seats: 12                          # or a list of names under `participants:`
lifetime:                          # §5
  ends: 2026-10-24                 # course end: instances STOP, nothing is deleted
  deactivate_users_after: 30d      # dated: users cannot log in any more
  delete_users_after: 90d          # dated: users are deleted (§6.4)
resources:                         # §7, per instance, may be overridden per app
  memory: 3g
  cpus: 1.5
apps:
  - id: code-server                # store id or git source + path
    name: ide                      # -> instance kurs-2026-10-ide-07
    channel: test
    config:
      IDE_EXTENSIONS: |
        SAPSE.sap-ux-fiori-tools-extension-pack
        https://github.com/SAP/abap-cleaner/releases/latest/download/abapcleaner-vscode-linux.gtk.x86_64.vsix
      IDE_SUDO: ja
      ANTHROPIC_API_KEY: {secret: schule-anthropic}   # a NAMED secret of the tenant, never the value
    seed:                          # path inside the instance's home -> file next to the template
      .adtls/destinations.json: seeds/destinations.json
      .adtls/SAPUILandscape.xml:   seeds/SAPUILandscape.xml
      projects/kurs.code-workspace: seeds/kurs.code-workspace
    material: material/            # directory next to the template -> the `material` mount
    start: "?workspace=/home/coder/projects/kurs.code-workspace"   # appended to the seat's address on the tile
users:
  prefix: tn                       # -> kurs-2026-10-tn-07
  roles: [user]
  display_name: "Teilnehmer {nn}"
  first_login: change_password     # D2 (§6.2)
handout: handout.csv               # written once at create/add, then forgotten
```

Rules:

- **A template holds no secret.** `{secret: <name>}` refers to a named
  secret of the tenant that a `tenant_admin` stored once; the tool puts
  it into each instance's config as a `secret: true` value. A template
  that carries a literal key is refused at import, by field name.
- **Seeds are data per seat** and are written *before* the instance's
  first start, so the app finds them on its first run. A seed may use
  `{nn}`, `{name}`, `{user}` placeholders. Seeds never overwrite a file
  the participant has changed: `reset` does, `create`/`add` only fill.
- **Everything in the template has a default**, so the minimal template
  is `name`, `tenant`, `seats` and one app.
- Export is `oaap cohort export <name>` — the stored copy, plus the
  seat list and what was actually created, as one directory. A later
  `create` from that directory is the next run.

## 3. The seat

For seat `07` of cohort `kurs-2026-10` in tenant `schule`:

| What | Value | Existing rule |
| --- | --- | --- |
| user | `kurs-2026-10-tn-07`, roles from the template, **group `kurs-2026-10-07`** | identity 2.2/2.6 |
| instance per app | `kurs-2026-10-ide-07`, channel from the template, **visibility `groups: [kurs-2026-10-07]`** | runtime 2.3/2.7 |
| address | `kurs-2026-10-ide-07.schule.<node>` plus the tile's `start` suffix | RFC-0022 D4, RFC-0043 |
| home | seeded, then the participant's own | runtime storage |
| material | copied from the template's directory; `material update` replaces it for all seats | second storage mount |
| config | from the template; named secrets resolved | runtime 2.8 |
| resources | from the template | §7 |

**No new ownership relation.** The group *is* the seat's key: the
launchpad filters by it today, the trainer sees everything by role, and
RFC-0045's contexts can take it over later without a migration. A
cohort-wide group (`kurs-2026-10`) is set on every seat's user as well,
so that a shared instance (a Forgejo, a Jupyter for the whole course —
§9) can be shown to the cohort with one visibility setting.

**Prefixes, not tenants (D1).** All cohorts of the school live in one
tenant; the cohort name is the prefix of every object. A separate tenant
per course remains possible for the exception (a customer's in-house
course with their own identity provider) and changes nothing in the
template but the `tenant:` line.

## 4. The commands (stage 1)

```text
oaap cohort create  <template-dir>            # all seats; refuses if the name exists
oaap cohort add     <name> [--seat 13|--name x]  # a latecomer; same template copy
oaap cohort reset   <name> --seat 07 [--keep-home]   # remove + create the seat's instances; user and password stay
oaap cohort list    [<name>]                  # seats, states, addresses, lifetime dates
oaap cohort stop|start <name>                 # all instances of the cohort
oaap cohort material update <name> <dir>      # replace the material of every seat
oaap cohort handout <name>                    # ONLY at create/add; later calls say why not
oaap cohort export  <name> [<dir>]            # the stored template + what was created
oaap cohort remove  <name> [--seat 07] [--purge] [--users]   # §5
```

Four rules, all of them habits of this platform:

- **Idempotent and reporting.** `create` on a half-made cohort finishes
  the missing seats and says which existed. Every command ends with a
  table: seat, user, instances, state, address.
- **The tenant comes from the actor**, never from the template alone: a
  `tenant_admin` may create cohorts only in their own tenant
  (`oaap.core.tenant` 2.3). `server_admin` may anywhere.
- **Recorded.** Creation, reset, handout, lifetime changes and removal
  go into the tenant's audit log with the cohort name and the seat.
- **One implementation.** The CLI calls the same functions the stage-2
  API will expose; nothing is built twice.

`create` for twelve seats means twelve installs of the same app version:
the image is built once, then reused (measured: the second instance of
the same version skips the build).

## 5. The lifetime (D3) — dates for users, never a timer on an instance

Jörg's rule: *participants may keep their access for a while after the
course; there are dates on which users are really deactivated and,
after a further period, really deleted; manual by the creator always
works — above all deletion after the course.*

| Moment | What happens | By whom |
| --- | --- | --- |
| `ends` | instances are **stopped**, seats show a badge; nothing is deleted | the node, at the date |
| `ends` → `deactivate_users_after` | users can still log in, instances can be started by the trainer | — |
| `deactivate_users_after` | users are **deactivated** (identity `active: false`) | the node, at the date |
| `delete_users_after` | users are **deleted** (§6.4); their instances must be gone by then or the date does not fire and the trainer is told | the node, at the date |
| any time | `stop`, `start`, `remove --seat`, `remove --purge --users` | the trainer |

Three guards:

- **RFC-0030 D4 stands:** *an expiry may exist only on a rehearsal.* A
  cohort's dates act on **users** and on the *running state* of
  instances; no date deletes an instance or its storage. Removing
  instances is `oaap cohort remove`, a human with a confirmation that
  names what is deleted, like `oaap app purge`.
- **Dates are visible and movable** on the cohort and on every seat, in
  the portal and in `list`; every change is recorded.
- **Deletion needs an empty seat.** A user is deleted only when no
  instance of the seat exists; otherwise the date is skipped, recorded,
  and shown as "waiting for removal".

The dates are the first *scheduled* action on identity data. They run
in the same host-side worker that applies store installs and backups
(runtime 2.6, RFC-0029), once a day, and record every action they take.

## 6. Identity extensions (`oaap.core.identity` 0.6)

### 6.1 Create on the node

`oaap user add <username> --roles user --groups a,b --display-name … [--tenant …] [--password-file …|--generate]`,
and the same as a function the cohort uses. Same rules as the portal
(2.4): `tenant_admin` inside their tenant, never `server_admin` by this
door, address created unverified. `--generate` prints the password
**once** and writes it nowhere but the caller's handout.

### 6.2 First-login password change (D2)

A flag `must_change_password` on the user record, set by create and by
`set password`, cleared by the self-service change. A session created
while the flag is set reaches **only** the password page of the portal;
the gateway's `/verify` answers `403` with a hint for every other
route. Cleared, the session is ordinary. This is what makes an initial
password in a handout acceptable.

### 6.3 Dated deactivation and deletion

Two optional dates on the user record, `deactivate_at` and `delete_at`,
settable by whoever may edit the user, acted on by the daily worker
(§5), shown on the user page with the reason ("cohort kurs-2026-10").
A date in the past at save time is refused, not silently fired.

### 6.4 Deletion

The open point of identity 2.4 is decided for this case: **a user may
be deleted.** The record disappears; the audit log keeps the username
and the user `id` (RFC-0040) as text, because entries already written
must stay readable; apps that stored the username keep a string that no
longer resolves — which is exactly what "the person is gone" should look
like. Deletion is refused while the user holds `server_admin` or is the
last `tenant_admin` of their tenant, and while an API key of theirs is
still valid (revoke first). The GDPR reading is the intended one: after
`delete_users_after` nothing personal about a participant remains but
the audit trail the operator is obliged to keep.

## 7. Resource limits per instance (`oaap.apps.runtime` 0.2.32) (D4)

An instance carries an optional `resources: {memory, cpus, pids}`,
operator-owned like config, applied at container (re)creation
(`--memory`, `--cpus`, `--pids-limit`). Set by `oaap app resources
<instance> …`, by the portal's instance page, and by the cohort from
its template. No default: an instance without the block runs as today.
A node shows the **sum of limits against its RAM** on the health page,
so that a trainer creating twelve seats of 3 GB on an 8 GB node is told
before the twelfth container is OOM-killed.

## 8. Stage 2 — the management API and the key (D6)

Everything in §4 becomes a JSON API under the tenant's place
(`/api/v1/tenant/cohorts…`, `/api/v1/tenant/users…`,
`/api/v1/tenant/instances…`), behind `/verify`, accepting a session
**or an API key** (RFC-0027). A key issued by a `tenant_admin` with the
role `tenant_admin` reaches only that tenant's objects, expires, is
revocable, and cannot carry `server_admin` — RFC-0027's rules already
say so. The cohort tool then has three shapes with one implementation:
the node's CLI, a script on the trainer's laptop, an OAAP app with a key
in its config. The API is specified as its own document
(`oaap.core.management` 0.1) when stage 2 starts; this RFC only fixes
that the CLI's functions are its body.

## 9. Noted, not designed

- **Forgejo per course** (Jörg, 2026-09-30): a shared Git instance in
  the cohort's tenant, visible to the cohort group, so that participants
  can push their project folders; GitHub works as well, Forgejo keeps
  it on the node. A shared instance is one more line in the template
  (`shared: true`, one instance for all seats) — the template format
  above already allows it; the command family does not treat it
  specially.
- **Jupyter** as a second workplace app; **Eclipse** only as a desktop
  in the browser (noVNC); **extensions exported from VS Code desktop**
  as a source (universal ones only). All in the idea backlog.
- **A login-relay for loopback callbacks** (ADT's reentrance ticket
  returns to `localhost` inside the container): code-server's
  `/proxy/<port>/` is the bridge; a helper page or bookmarklet could
  hide the address edit. Not a platform matter.

## 10. Security requirements

- The template never contains a secret (§2); named secrets are resolved
  on the node and reach the instance as `secret: true` config.
- The handout exists once; the node stores only hashes. A second
  `handout` call refuses and offers `oaap user password` per seat.
- A `tenant_admin` cannot create a seat in another tenant, cannot grant
  node-wide roles, and their key (stage 2) inherits both limits.
- Seeds are written into the instance's storage with the image's uid,
  under the instance's own directory, never elsewhere; a seed path with
  `..` or an absolute path is refused.
- Resource limits are not a security boundary; the instance network
  (RFC-0016) and the missing Docker socket remain the boundary.
- Every command that deletes says what it deletes and needs a
  confirmation or `--yes`; nothing deletes on a date except users, and
  only when their seat is empty (§5).

## 11. Staging

1. **Identity 0.6** — `oaap user add`, `must_change_password`,
   `deactivate_at`/`delete_at`, deletion with its refusals (§6).
   **Built 2026-09-30** (reference 0.1.144, `oaap.core.identity` 0.6.0,
   spec 2.9). Refinements found while building: the login itself redirects
   to the password page and `/verify` redirects a *navigation* there (a
   bare 403 would be the first thing a participant sees), a script still
   gets the 403; the new password must differ from the old; dates are
   only *data* until the worker of stage 4; a stored date is not
   re-judged as "past" when a form sends it back.
2. **Runtime 0.2.32** — `resources` per instance, node-wide sum on the
   health page (§7). **Built 2026-09-30** (reference 0.1.145,
   `oaap.apps.runtime` 0.2.32, spec 2.18). Refinements found while
   building: the limit is read from the *registry* where containers are
   created, not from what the caller passes (a configuration save and a
   restart pass no record — a limit tied to the door would be lifted by
   the first save); it is set by the `server_admin` only (a limit the
   limited party can lift protects nobody); given fields merge, only
   `--clear` removes; a machine whose kernel lacks the memory cgroup
   accepts the flag and enforces nothing, so the command shows docker's
   warning; the sum counts per service container and names unlimited
   instances apart instead of counting them as zero.
3. **Cohort CLI** — template, seats, seeding, material, handout,
   reset, export, remove (§2–§4). **Built 2026-09-30** (reference 0.1.148,
   `oaap.apps.runtime` 0.2.33, spec 2.19) and tested against fakes; **not
   yet measured** with the `code-server` app on `oaap-test` (three seats),
   then on `oaapx01` with a real course template. Refinements found while
   building: the installer gets one hook between the environment file and
   the first container — seeds must exist for the *first* run, and the
   image's user has to own them, which is only known once the image is
   built; limits and the group restriction go into the *first* registry
   entry; the handout is opened exclusively **before** the first user and
   written row by row, and a seat whose install fails still gets its row;
   it may not lie inside the template directory (a repository); `create`
   on a half-made cohort finishes it from the copy it was *started* from;
   a named secret store per tenant (`oaap cohort secret`) is needed for
   `{secret: name}`, and lives beside the destination secrets where only
   the host reads; confirmation without a terminal refuses instead of
   waiting. Dates on users are set, nothing acts on them (stage 4).
   Not built in this stage: `lifetime.ends` stopping the instances (the
   daily worker), the portal's view of a cohort.
4. **The daily worker** for the lifetime dates (§5). **Built 2026-09-30**
   (reference 0.1.149, `oaap.apps.runtime` 0.2.34): `oaap cohort sweep`
   from its own systemd timer beside the rehearsal sweep (04:40,
   `Persistent=true`, on a fresh install and in `migrate.sh`). Refinements:
   the stop comes the day *after* `ends` (the last course day runs); it
   fires once and a manual `start` stands; the sweep acts on every person
   whose date has come, cohort or not (a date set in the portal must not
   silently never fire); a fired deactivation date is cleared; a refused
   deletion is logged once, not daily. `ends` itself moves
   by `oaap cohort extend` (built 2026-10-01, reference 0.1.151,
   `oaap.apps.runtime` 0.2.35): later only, computed dates follow, hand-set
   dates stay, nothing is started or reactivated.
5. **Stage 2** — `oaap.core.management` 0.1 and the key; the cohort as
   an app. **Built 2026-10-01** (reference 0.1.153): the API under
   `/api/v1/tenant/cohorts…` for a `tenant_admin` (session or key), jobs
   for what takes minutes, the template uploaded as ZIP, the handout as a
   one-time ZIP with a password the trainer chooses at download (Jörg,
   2026-10-01). A trainer may name only apps of trusted store sources.
   Not yet: a portal page for cohorts (the next stage on this API).
6. **Stage 3, first form: the portal page.** **Built 2026-10-01**
   (reference 0.1.155, `oaap.core.portal` 0.3.17): `/kohorten` and
   `/kohorten/<name>`, read-only, on the file the API's GET calls read. No
   change from the page yet; creating, extending and removing stay with
   the API and the CLI. **Second form, built 2026-10-01** (reference
   0.1.156, portal 0.3.18): *Stop/Start* and *Extend* as buttons on the
   cohort's page, through the same spool as the API, with the host's answer
   shown; removing stays with the API. **Third form, built 2026-10-01** (reference
   0.1.158, portal 0.3.19): *Create* from a template ZIP, the one-time
   handout (optional password) for the person who started the job, and
   *Reset a seat*, all through the API's own code. **Fourth form, built
   2026-10-01** (reference 0.1.160, portal 0.3.20): *Remove the cohort*
   with the name typed out. **Fifth form, built 2026-10-01** (reference
   0.1.161, portal 0.3.21): *Remove a seat* with `<cohort>-<seat>` typed
   out, and a refused user deletion no longer hides behind the closing
   line. Only *adding* seats stays with the API.

## 12. Decisions (Jörg, 2026-09-30)

- **D1 — One tenant, prefixes inside it; a separate tenant only as the
  exception.** The cohort name prefixes users, groups and instances;
  the template's `tenant:` line is all that changes for the exception.
- **D2 — First-login password change, as an identity extension.**
  §6.2.
- **D3 — Dates, not just a switch:** users may stay valid for a while
  after the course; a date deactivates them, a later date deletes them;
  manual by the creator always works, deletion after the course above
  all. §5 and §6.3/6.4. Instances keep RFC-0030 D4: no timer.
- **D4 — Resource limits in the MVP.** §7.
- **D5 — The template is a file** in the trainer's repository, with a
  stored copy per cohort on the node. §2.
- **D6 — Stage 2 as designed:** tenant-scoped management API with a
  `tenant_admin` key after RFC-0027, the CLI's functions as its body.
  §8.

## Deutsche Zusammenfassung

**Worum es geht.** Die code-server-App hat gezeigt, dass ein
Schulungsarbeitsplatz im Browser eine gewöhnliche OAAP-Instanz ist. Was
fehlt, ist die Hand, die zwölf davon aufstellt und wieder abräumt: die
**Kohorte**. Eine Kohorte ist ein Kurslauf — N Plätze in einem
Mandanten, jeder Platz ein Benutzer mit eigener Gruppe, eigenen
Instanzen und eigenem Material, alles aus **einer Vorlagendatei**, alles
mit einem Befehl entfernbar.

**Was schon da ist:** der Mandant als Grenze, die Sichtbarkeitsgruppen
(sie filtern das Startfeld je Teilnehmer — gemessen: ohne Gruppe 403,
mit Gruppe drin), Instanznamen und Adressen, Sicherung und Entfernen je
Instanz, die zwei Ablagen der App (Zuhause und Material).

**Was neu ist:**

- **Die Vorlage ist eine Datei** (D5): Name, Mandant, Plätze, Apps je
  Platz mit Konfiguration, Erweiterungen, **Saat** (destinations.json,
  SAPUILandscape.xml, Arbeitsbereich), Material, Ressourcen, Lebenszeit.
  Kein Geheimnis in der Datei — nur der *Name* eines im Mandanten
  hinterlegten Geheimnisses. Import und Export sind Kopieren.
- **Der Platz:** Benutzer `kurs-2026-10-tn-07` mit Gruppe
  `kurs-2026-10-07`, Instanz `kurs-2026-10-ide-07` nur für diese Gruppe
  sichtbar, Saat vor dem ersten Start, Material im zweiten Mount. Keine
  neue Besitz-Beziehung: die Gruppe ist der Schlüssel des Platzes.
  **Ein Mandant, Präfixe** (D1); eigener Mandant nur als Ausnahme.
- **Die Befehle** `oaap cohort create/add/reset/list/stop/start/material
  update/handout/export/remove` — idempotent, mit Bericht, im Mandanten
  des Handelnden, protokolliert. Erst CLI, dann API (D6).
- **Die Lebenszeit** (D3): Kursende **stoppt** Instanzen, löscht nichts.
  Benutzer bekommen zwei Termine: deaktivieren, später löschen. Manuell
  geht immer. Gelöscht wird ein Benutzer nur, wenn sein Platz leer ist.
  RFC-0030 D4 bleibt: kein Zeitschalter auf einer Instanz, Instanzen
  entfernt ein Mensch mit Bestätigung.
- **Identity 0.6:** Benutzer per Befehl anlegen (heute geht das nur im
  Portal), Passwortzwang beim ersten Login (D2), Termine für
  Deaktivierung und Löschung, und **Löschen** selbst — der offene Punkt
  aus identity 2.4 ist damit für diesen Fall entschieden, mit
  Verweigerungen für server_admin, letzten tenant_admin und gültige
  API-Schlüssel.
- **Ressourcengrenzen je Instanz** (D4): RAM, CPU, Prozesse; die
  Gesundheitsseite zeigt die Summe gegen den Knoten. Gemessen: ein
  Arbeitsplatz mit ADT, CDS und Claude lag bei 1,9 GB.
- **Stufe 2** (D6): dieselben Funktionen als JSON-API im
  Mandantenzuschnitt, hinter `/verify`, mit Sitzung *oder*
  `tenant_admin`-Schlüssel nach RFC-0027 — dann ist das Werkzeug auch
  ein Skript auf dem Laptop oder eine App.

**Vermerkt, nicht entworfen:** Forgejo je Kurs (Jörgs Anmerkung — eine
geteilte Instanz ist eine Zeile mehr in der Vorlage), Jupyter als
zweite Umgebung, Eclipse nur als Desktop im Browser, Export aus VS Code
Desktop, die Brücke für ADTs Anmelde-Rücksprung.

**Baureihenfolge:** Identity 0.6 → Ressourcengrenzen → Kohorten-CLI
(gemessen mit drei Plätzen auf oaap-test, dann ein echter Kurs auf
oaapx01) → täglicher Lauf für die Termine → Stufe 2.
