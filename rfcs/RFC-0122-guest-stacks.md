# RFC-0122: Guest Stacks — Compose Stacks the Admin Keeps, Portainer as the First Adapter

- **Status:** **Accepted (2026-11-23)** — D1–D4 decided in conversation
  (§13.1), D5–D16 as recommended (Jörg: "Wie empfohlen", §13.2). Nothing built.
  **Stage 0 measured on oaap-test the same day** (§1.5): what was open in §1.4
  is answered there, except Nginx Proxy Manager (stage 4) and a restore onto a
  machine that never had the stack. The OAAP facts in §1.1
  were read the same day in the specs; the Portainer facts in §1.2 come from a
  web search the same day, partly from third-party guides, and from memory —
  each line says which. What was **not** read or measured is listed in §1.4.
- **Date:** 2026-11-23
- **Authors:** Jörg (the idea, 2026-11-23: "lieber eine besondere Unterstützung
  für Portainer Stacks bauen anstatt alles selbst zu machen … die Rolle des
  NGINX Proxy Managers übernehmen … ein Auge haben auf die Stacks … die Volumes
  mit in unsere Sicherung nehmen"), Claude (facts, design)
- **Depends on:** RFC-0008 (`server_admin`), RFC-0011 (node profiles), RFC-0026
  (the tenant tree), `oaap.core.gateway` (routes, the gate), `oaap.data.backup`
  (the archive), RFC-0084 (secret files)
- **Related:** RFC-0037 (sideloading — a different thing, §2.2), idea I-66
  (build service — a different thing, §2.2), RFC-0031 / idea I-51 (the twin, a
  CMDB that grows by itself), RFC-0044 (access into instance networks),
  RFC-0080 / RFC-0083 (notifications, weekly report), RFC-0093 (upgrades that
  change data), RFC-0115 (a tenant's own domain)
- **Changes (when accepted):** a new specification `oaap.apps.stacks`;
  `oaap.core.host` (a profile); `oaap.core.gateway` (routes to a guest stack);
  `oaap.data.backup` (the backup set of a stack); `oaap.data.twin` (object types
  for stacks, containers, images, volumes); an app package `portainer`
- **Not part of this RFC:**
  - **Portainer inside a tenant.** Decided (D1): guest stacks exist only on a
    node whose admin runs it for themselves; they are managed centrally by the
    `server_admin`. A tenant uses a stack, it never administers one.
  - **OAAP deploying, updating or repairing a guest stack.** The admin does
    that, in Portainer. OAAP reads; the one exception is the stop and start
    around a backup (§6.3).
  - **Single sign-on into the software of a guest stack.** The gate in front
    is OAAP's; the login inside stays the product's own.
  - **Kubernetes and Swarm.** Docker standalone only.
  - **The watcher for our own catalog.** The same eye (§7) should watch the
    images of OAAP apps too; that is the missing half of I-66 and is written
    there, not here.

## Summary

OAAP apps are packages the platform promises to keep: tested, updated, backed
up, with login and health. That promise costs work per app, and we do not
always keep up (Forgejo). At the same time many admins already run their
software as Compose stacks under Portainer and are not going to repackage it.

This RFC adds a **second class** next to apps: the **guest stack**. It is a
Compose stack that the admin keeps — deployed and updated by them, in
Portainer — and that OAAP **surrounds**:

1. **The way in.** OAAP takes the role of a reverse proxy manager: a name, a
   certificate and the tenant's login in front of a port of the stack. The
   stack publishes no port of its own.
2. **The backup.** The stack's volumes are listed, the admin ticks which ones
   belong to the backup (data yes, logs no), and they go into the platform's
   archive together with the stack's definition.
3. **The eye.** Stacks, containers, images and volumes appear in the twin;
   OAAP reports what is down, what is old and what carries known
   vulnerabilities.

A guest stack belongs to **exactly one tenant** (D4). It is **not** kept by the
platform, and every place that shows it says so.

Portainer is the **first adapter**, not the contract. What OAAP relies on is
what Docker itself tells (Compose project labels, volumes, networks);
Portainer adds the stack's definition and is the admin's tool. OAAP can bring
Portainer along as an app, or work with one that is already there (D2).

## 1. Facts

### 1.1 OAAP (read 2026-11-23)

| # | Fact |
|---|---|
| F1 | A node carries **profiles** that gate platform behaviour; they are set only on the machine, an unknown name is rejected, the status page states them (`oaap.core.host` 2.5, RFC-0011). `sideload` is the precedent for "off until the owner of the machine switches it on" (RFC-0037). |
| F2 | A backup is **one archive** with a manifest. It carries the app storage of every instance in the tenant tree `tenants/<tenant-id>/instances/<instance-id>/`, never container images, and should not carry logs or caches (`oaap.data.backup` 2.1). |
| F3 | An implementation may offer the archive of a **single tenant**, distinguishable by its manifest (`oaap.data.backup` 2.1.1). |
| F4 | Containers started beside `oaap` are a known trouble: a bare `docker compose up` leaves strays the platform does not account for (our own experience, 2026-11). |
| F5 | Idea I-66 (build service) names the other answer to "we do not keep up": recipes that turn upstream Compose into OAAP packages — and says that building alone does not help without a watcher for new upstream versions. |

### 1.2 Portainer (web search 2026-11-23, and memory)

| # | Fact | Source |
|---|---|---|
| P1 | The API takes an access token in the header `X-API-Key`; a user creates it for themselves; `GET /api/stacks` lists stacks, `GET /api/endpoints` the environments. | docs.portainer.io (API access) |
| P2 | A custom OAuth provider (client id, secret, authorization, token and resource URL) can be set under Settings → Authentication; guides for Authelia, authentik and Keycloak-like providers exist. Whether everything needed is in the Community Edition today is **not confirmed** from the official page. | third-party guides |
| P3 | Portainer keeps each stack under `/data/compose/<stack-id>/` in its own data volume: the Compose file and, if variables were set, `stack.env`. | third-party guide |
| P4 | Relative bind mounts (`./data`) do not work for stacks in the Community Edition — the path would lie inside Portainer's volume. Stacks therefore use **named volumes** or **absolute host paths**. | GitHub discussion portainer/9795 |
| P5 | Docker Compose marks containers, volumes and networks with `com.docker.compose.project` (and `…service`, `…volume`). | memory, not read today |
| P6 | Portainer shows app templates from a JSON list whose URL the admin sets. | memory, not read today |
| P7 | Portainer needs the Docker socket. Whoever is admin in Portainer is root on the host. | memory; follows from the Docker API |

### 1.3 What follows

- Portainer does **not** keep a stack up to date. Moving software from "OAAP
  app" to "Portainer stack" moves the duty from us to the admin; it does not
  remove it. The honest product is a clear line of responsibility plus an eye
  that tells the admin what they owe (§7).
- P7 is why D1 is the only safe scope: on a node shared by tenants that do not
  trust each other's admin, a Portainer login is a door to all of them.
- P5 means discovery and the list of volumes do not depend on Portainer. A
  plain Compose project started from a shell is found the same way.
- P4 makes the backup simpler than feared: volumes and absolute paths, both
  readable from Docker.

### 1.4 Not read, not measured

- Whether OAuth in Portainer CE works against our Keycloak, and whether it can
  be limited to one group (P2).
- What the API returns for a stack's file and variables, and for stacks that
  come from Git.
- How the reference gateway reaches a container in a stack's private network
  without the stack publishing a port, and whether that survives a redeploy of
  the stack in Portainer.
- How OAAP's own containers are told from foreign ones today (labels, project
  names), so that a guest stack is never mistaken for a stray and the other
  way round.
- Stop, copy, start around a database volume, and a restore onto an empty
  node.
- Nginx Proxy Manager: where its proxy hosts lie and how they can be read
  (stage 4).

Stage 0 (§11) answers these before anything is built on them. Answered in
§1.5, except Nginx Proxy Manager.

### 1.5 Measured in stage 0 (2026-11-23, oaap-test)

Portainer CE **2.45.4** (tag `lts`, image of 2026-11-18) as a container bound
to `127.0.0.1` only, its own data volume, the Docker socket. Three stacks
through the API: `a` (Postgres 16 with a named volume, nginx with an absolute
bind mount, no published port), `b` (nginx, a service of the same name `web`),
and one from Git (`docker/awesome-compose`, `gitea-postgres`). A stand-in for
the gateway (`caddy:2`, the image of the reference gateway) instead of the
platform's own gateway, which was not touched. Keycloak: the instance on
oaap-test, a realm of its own. Everything was removed afterwards.

| # | Measured | Follows |
|---|---|---|
| M1 | The first admin needs a **setup token** that Portainer prints into its start log (`X-Setup-Token`, or start with `--no-setup-token`). Without it `POST /api/users/admin/init` is 403. A fresh Portainer has **no environment**; the local Docker one is made through the API (`EndpointCreationType=1`). | The package `portainer` reads the token from the log once, or starts with an admin password file from the instance's secrets (not measured), and creates the local environment itself. |
| M2 | An access token (`X-API-Key`) reads `/api/endpoints`, `/api/stacks`, `/api/stacks/<id>/file`; a wrong key gets 401 (P1 confirmed). | The adapter needs nothing else for reading. |
| M3 | `GET /api/stacks` returns the stack variables **with their values** — a database password included. | A "reading" token reads secrets. It is stored as a secret file (RFC-0084), and what the adapter reads is treated as secret (§6.2, §10.7) — also in the twin, which gets variable **names** only. |
| M4 | A Portainer stack lives under `/data/compose/<id>/` **inside Portainer's volume** (P3 confirmed); Docker's label `com.docker.compose.project.working_dir` names that path, which does not exist on the host. A Git stack carries URL, reference, file path and the commit it was deployed from; its file is readable like any other. | The definition of a Portainer stack comes from the Portainer adapter only. The `docker` adapter alone finds and backs up its volumes, but not its file. |
| M5 | Portainer's containers, volumes and networks carry `com.docker.compose.project`, `…service`, `…volume`, `…network` (P5 confirmed; `com.docker.compose.version` is empty). OAAP's core services carry the project `oaap`. **OAAP's app containers carry no label at all** — only the name prefix `oaap-app-`. On oaap-test the measurement found three foreign Compose projects and five single containers left from earlier measurements (F4). | Telling OAAP's own from foreign must not rest on a name prefix anyone can choose: stage 1 gives OAAP's app containers a label of their own (an instance key), and discovery reads it. |
| M6 | A container joined to a stack's network (`docker network connect`) reaches a service there **without a published port**. But a **service name is ambiguous** across the networks a container is in: with stacks `a` and `b` both having `web`, the name answered from `a`, and after `a` was stopped and started, **from `b`**. The container name (`<project>-<service>-<n>`) answered right every time, also across a recreate. | §5.2 rule 1 holds, with a new rule: an exposure is routed to the **container name** in the stack's own network, never to a bare service name. Otherwise a name of tenant A can serve a stack of tenant B (§10.9). |
| M7 | A redeploy through the API (`PUT /api/stacks/<id>`) answers 200 **before** the containers are recreated (seconds later). The recreated container keeps its name; the stand-in kept working. | §5.2 rule 2 holds by container name. Nobody reads "redeployed" from the API's answer. |
| M8 | Portainer's **stop** removes the stack's containers and its network — except while another container is joined to the network: then the network stays, and Portainer says nothing. **Start** made the containers again in the kept network; the stand-in worked without being joined again. When the network was removed, start made a **new** one (new id). | The gateway joins again whenever a stack's network is new — the same healing the platform already does for instance networks (RFC-0016) — and an exposure answers 503 meanwhile. |
| M9 | Portainer's **delete** of a stack answers 204; the named volume stays; the network stays silently while the stand-in is joined to it. | When a stack is **gone** (§4), OAAP leaves the network with its gateway and removes nothing else. |
| M10 | Mode **`stop`** done with Docker, not Portainer: containers stopped in reverse dependency order, the volume copied through a helper container (5,000 rows, 7 MB), the bind path copied, started in order — **6.3 s** down, all rows there. Portainer kept showing the stack as active throughout. **Restore** after stack, volume and bind path were removed: volume made and filled first, path back, then the stack deployed again from the saved definition through the API — 5,000 of 5,000 rows, the page served; Compose took the pre-made volume without a label and without complaint. | §6.3 and §6.4 hold. The order of a restore is: volumes and paths first, then the admin deploys. The restore onto a machine that never had the stack is still to measure before stage 2 is done. |
| M11 | **OAuth in CE works** against our Keycloak: authorization code, user info, `preferred_username` as identifier. CE has **no group or team mapping** (no such field in its settings). With automatic user provisioning **on**, every user of the realm gets in (as a standard user); with it **off**, only users made beforehand in Portainer — and under OAuth those must be made **without a password** (with one: refused). Portainer's local admin keeps working with OAuth on. The client secret is not returned by the settings. | P2 confirmed for CE. "Limited to one group" (§5.3) is: provisioning off, persons made beforehand by the admin; a group check on the Keycloak side was not measured. The local admin stays the way in when the provider is down. |
| M12 | The Git stack, a popular example, uses `postgres:alpine` without a version — today **Postgres 19**, whose data layout no longer fits the example's volume path: the database restarted in a loop (nine times in a few minutes), and the stack also published port 3000 on all interfaces. | Exactly the cases of §3 ("offen am Gateway vorbei") and §7 ("restarting in a loop", "image age") — met in the first stack taken from the internet. |

## 2. Words

### 2.1 The objects

| Word (German in the UI) | Meaning |
|---|---|
| **guest stack** (Gast-Stack) | a Compose project on the node that OAAP did not create and does not keep, adopted by the `server_admin` |
| **found stack** (gefundener Stack) | a Compose project OAAP sees but nobody adopted. Nothing happens to it. |
| **adoption** (Übernahme) | the `server_admin` gives a found stack a title and **one tenant** |
| **exposure** (Freigabe) | a name at the gateway that leads to one service and port of the stack |
| **backup set** (Sicherungsumfang) | the ticked volumes and paths of a stack, plus its definition |
| **adapter** | what tells OAAP about stacks: `docker` (always), `portainer` (adds definition, variables, the stack's id) |

### 2.2 Three things that are not the same

| | Sideloading (RFC-0037) | Build service (I-66) | Guest stack (this RFC) |
|---|---|---|---|
| Input | an OAAP package | upstream Compose plus an OAAP overlay | a running Compose stack |
| Becomes an OAAP app | yes | yes | **no** |
| Who updates it | the platform's update path | the recipe and its watcher | the admin, in Portainer |
| Login, health, contract | the app contract | the app contract | only the gate in front |
| Promise | kept by the platform | kept by the platform | **surrounded, not kept** |

A guest stack that proves itself can later become a recipe (I-66). The
direction is one way: nothing here turns an OAAP app into a guest stack.

## 3. The profile and discovery

- A node shows guest stacks only with the profile **`stacks`** (name: D6), set
  on the machine (F1). Without it OAAP behaves as today: it reads nothing from
  Docker about foreign containers and offers no page.
- With the profile, OAAP lists every Compose project on the node that is not
  its own as a **found stack**: name, services, state, volumes, published
  ports. Reading is all it does.
- A found stack that publishes a port on all interfaces is marked: "offen am
  Gateway vorbei". OAAP does not close it; it says so.
- A container without a Compose project is listed under "einzelne Container"
  and cannot be adopted in stage 1.

## 4. Adoption: one stack, one tenant

The `server_admin` adopts a found stack: a title, a short description, and
**exactly one tenant** (D4). From then on

- the tenant's place shows a tile for each exposure of the stack, marked
  **"Gast-Stack — gepflegt vom Betreiber dieses Knotens, nicht von der
  Plattform"**;
- the stack's backup set lies in that tenant's tree and is part of that
  tenant's archive (F3);
- the stack's objects in the twin belong to that tenant (§7).

A stack that should serve several tenants is given to a tenant made for shared
things; OAAP does not split one stack. Moving a stack to another tenant is a
deliberate act with an entry in both tenants' audit logs; its earlier backups
stay where they were written.

Adoption is recorded by OAAP, keyed by adapter, environment and Compose
project name. Nothing is written into the stack: no label, no network, no
file. A stack that disappears stays in the list as **gone**, with its
exposures answering 503 and its backups kept; the `server_admin` retires it.

## 5. The way in

### 5.1 An exposure

An exposure names a **service** of the stack, a **port** inside it, and a
**name**. The name follows the tenant's rules: `<name>.<tenant place>`, or
below the tenant's own domain (RFC-0115). The certificate comes as for an
instance.

| Access | Meaning |
|---|---|
| `tenant` (default) | any signed-in person of the owning tenant |
| `roles` | signed-in persons holding one of the named roles |
| `public` | no login. Needs a second confirmation and is shown in red in the list. |

The gateway passes the platform's identity headers (RFC-0040) only if the
exposure says so; software that does not expect them should not get them.

### 5.2 Rules

1. A guest stack needs **no published host port** for an exposure. The gateway
   reaches the service inside the stack's network; how, is stage 0 (§1.4).
2. An exposure survives a redeploy of the stack in Portainer. If the service
   is away, the name answers 503 with the platform's page, not a timeout.
3. Names of guest stacks and of instances share one namespace per tenant; a
   collision is refused when the exposure is made.
4. An exposure never points at Portainer itself, the Docker socket, or a
   container outside the adopted stack.

### 5.3 Portainer's own door

Portainer is reached under a name of the node, behind the platform's gate,
for the role `server_admin` only. Behind the gate Portainer still asks for
its own login; where the node has a provider it is wired by OAuth (P2,
stage 0), otherwise Portainer's local admin remains and its password lies in
the instance's secrets. The local admin is kept in every case as the way in
when the provider is down.

## 6. The backup

### 6.1 The backup set

For an adopted stack OAAP lists what Docker reports for its containers:

- every **named volume**, with its size and the services that mount it;
- every **bind mount** with an absolute host path (P4), with the same;
- the **definition**: Compose file and variables, from the Portainer adapter,
  or from the Compose project's working directory where Docker names one.

The `server_admin` ticks volumes and paths. The definition is always in. New
volumes that appear after a redeploy are **not** ticked by themselves; the
stack shows "neues Volume, nicht in der Sicherung" until someone decides.
Paths outside a short list of refused places (`/`, `/etc`, `/var/lib/docker`,
the socket, OAAP's own data directory) can be ticked; those cannot.

### 6.2 Where it lies

The backup set goes into the platform's archive under
`tenants/<tenant-id>/stacks/<stack-key>/` (F2), listed in the manifest beside
the instances. The variables of a stack are treated as secrets: same
protection as `instance.env`. Images are not in the archive (F2); the
manifest records image name and digest per service so a restore knows what
ran.

### 6.3 When: the mode per stack

Ticking a volume says *what*. Whether the copy is usable is a second question;
a database copied while it writes may not start again.

| Mode | What happens | For |
|---|---|---|
| `stop` (default) | stop the stack's containers, copy, start them in the recorded order | everything with a database |
| `live` | copy while running | files that are written rarely; chosen knowingly |
| `hook` (later) | run a declared command in a container first (a dump), copy its output | stacks that must not stop |

In mode `stop` OAAP starts exactly the containers it stopped, also when the
copy fails, and reports a stack that does not come back. This stop and start
is the only change OAAP ever makes to a guest stack.

### 6.4 Restore

A restore brings back the ticked volumes and paths and puts the definition
beside them as files. **Deploying the stack again is the admin's act**, in
Portainer, from that definition. OAAP says so on the restore page and does
not claim a guest stack is restored the way an instance is. Stage 2 is not
done before one restore onto an empty node has been measured.

## 7. The eye

- **Twin.** Object types *Stack*, *Container*, *Image*, *Volume* with their
  relations (stack has containers, container runs image, container mounts
  volume, stack belongs to tenant). They are written from what Docker reports,
  like the node data of I-51; nobody maintains them by hand.
- **State.** Not running, restarting in a loop, unhealthy by the container's
  own health check: shown on the tile, sent through the tenant's notifications
  (RFC-0080) to the `server_admin`.
- **Age.** Per image: the digest that runs, and whether the same tag upstream
  has a newer one. No update is made; the page says "neuer Stand verfügbar"
  and the weekly report (RFC-0083) lists it.
- **Vulnerabilities.** Images are scanned on the node with an open scanner
  (which: D12); the result is a count by severity per image and the names of
  the critical ones. Nothing leaves the node except the scanner's fetch of its
  database.
- **Who is told.** The `server_admin`, because they keep the stack. The
  tenant's admin sees state and the mark "not kept by the platform", not the
  list of vulnerabilities (D13).

## 8. Portainer: brought along, or already there

**Brought along.** An app package `portainer` (Community Edition, a pinned
version) that only installs on a node with the profile `stacks`, into the
operator's tenant. Its envelope shows the one thing no other app gets: the
Docker socket. This is one piece of software we keep instead of many — and it
is kept like any app, including the watcher.

**Already there.** The `server_admin` registers an existing Portainer: its
address and an access token they created (P1). OAAP checks the token, reads
the version and the environment that is this node's Docker, and stores the
token as a secret file (RFC-0084). OAAP never asks for a Portainer password.
A token is used for reading only until stage 5.

**Without Portainer.** The profile works with the `docker` adapter alone:
discovery, adoption, exposure, volumes and the eye. Only the definition of a
stack then comes from the Compose project's directory, if Docker names one.

**An existing reverse proxy** (Nginx Proxy Manager) holds ports 80 and 443,
which the gateway needs. Taking over is a stage of its own (4): OAAP reads the
proxy hosts, proposes an exposure for each, and the admin switches the ports
over in one planned step with a way back.

## 9. Later: templates, private networks, AI

- **Templates.** OAAP serves a template list in Portainer's format (P6) from a
  set of Compose files we publish: shapes that fit §5 and §6 out of the box
  (no published ports, named volumes, a health check). A stack deployed from
  one is still a guest stack.
- **Private networks.** A stack's network reached through the platform's
  remote access (RFC-0044) instead of a public name: for databases and admin
  interfaces that should never have an exposure.
- **AI.** Reading tools over the eye ("which stacks are down", "what is old")
  as an MCP source for the operator's assistant. No tool that changes a stack.

## 10. Security requirements (proposed)

1. Without the profile `stacks` the platform reads nothing about foreign
   containers and no package may ask for the Docker socket.
2. Everything in this RFC needs the role `server_admin`. A tenant admin sees
   the tiles and the state of their tenant's stacks, nothing more.
3. Portainer's door is behind the gate for `server_admin` only (§5.3). It is
   never an exposure and never `public`.
4. A found stack is default deny: no route, no backup, no twin object beyond
   the list, until adopted.
5. An exposure points only into the adopted stack (§5.2, rule 4). `public`
   needs the second confirmation and is written to the audit log of the
   owning tenant.
6. OAAP writes nothing into a guest stack and changes nothing in Portainer.
   The stop and start of §6.3 is the exception, logged with times.
7. A stack's variables and Portainer's access token are secrets: never shown
   again, never in a log, protected in the archive.
8. Names, labels, image names and log lines of a guest stack are foreign
   content. They are shown as text and never interpreted — also not by an
   assistant (§9).
9. A stack belongs to one tenant in every store: route, backup, twin. No
   answer about tenant A contains a stack of tenant B.
10. Every page and tile of a guest stack carries the mark of §4. The platform
    never shows a green "aktuell" for software it does not keep.

## 11. Stages

| Stage | Content |
|---|---|
| **0 — measure** (done 2026-11-23, §1.5; open: a restore onto a machine that never had the stack, Nginx Proxy Manager) | On `oaap-test`: Portainer CE as a container behind the gateway; OAuth against Keycloak, limited to one group; the API with a token (stacks, file, variables, a stack from Git); a stack with Postgres in a private network reached by the gateway without a published port, across a redeploy; telling OAAP's containers from foreign ones; `stop` — copy — start, and a restore on an empty node; an absolute bind mount. |
| **1 — adopt and expose** | profile, discovery, found stacks, adoption with one tenant, exposures with `tenant` / `roles` / `public`, tiles with the mark; the package `portainer`; adapter `docker` and `portainer` (reading). |
| **2 — backup** | the backup set, modes `stop` and `live`, the archive and the tenant archive, restore as in §6.4. |
| **3 — the eye** | twin objects, state and notifications, image age, vulnerability scan, the weekly report. |
| **4 — what is already there** | registering an existing Portainer; reading Nginx Proxy Manager and taking over its ports. |
| **5 — later** | templates in Portainer's format, private networks (RFC-0044), mode `hook`, reading MCP tools. |

## 12. Conformance (described; every line gets a bait)

1. A node without the profile lists no foreign container and refuses the
   package `portainer`.
2. A found stack that is not adopted has no route, no backup set and no twin
   object.
3. A tenant admin of tenant B gets no trace of a stack adopted for tenant A —
   list, tile, twin, archive.
4. An exposure to a container outside the stack, to Portainer or to the
   socket cannot be saved.
5. A person without the role is refused at the gate of a `roles` exposure and
   of Portainer's door; the software behind is never reached.
6. An exposure answers again after the stack was redeployed, without anyone
   touching OAAP.
7. A volume that is not ticked is not in the archive; a new volume is not
   ticked by itself and is reported.
8. In mode `stop` a failed copy leaves the stack running as before.
9. The archive holds a stack's variables protected and the manifest names
   image and digest per service.
10. A restore on an empty node brings volumes and definition back; a database
    stack deployed from it starts with its data.
11. `/`, the Docker data directory and the socket cannot be ticked.
12. A stack name or label containing markup or instructions is shown as text.
13. Every tile and page of a guest stack carries the mark.

## 13. Decisions

### 13.1 Decided 2026-11-23 (Jörg, in conversation)

- **D1 — Only for admins with their own nodes; managed centrally by the
  `server_admin`, used by tenants, never offered inside a tenant.** Yes.
- **D2 — Both directions: OAAP can bring Portainer along, and it recognises
  and integrates an installation that is already there.** Yes.
- **D3 — The backup takes the volumes of a stack, selectable one by one, so
  that data and logs can be separated.** Yes.
- **D4 — A stack belongs to exactly one tenant.** Yes.

### 13.2 Decided 2026-11-23: D5–D16 as recommended

D12 is thereby decided as "after stage 0": the scanner is the one choice
still to be made.

- **D5 — The word: "guest stack" / "Gast-Stack"?** *Recommendation: yes.* It
  says in one word that the stack is welcome and not ours.
- **D6 — The profile is called `stacks`?** *Recommendation: yes*, set on the
  machine like `sideload`.
- **D7 — The contract is Docker's own report; Portainer is an adapter?**
  *Recommendation: yes.* Otherwise the feature depends on one vendor's
  editions and licence, and a plain Compose project stays a stray.
- **D8 — OAAP writes nothing into a stack; choices (exposure, backup set) are
  kept in OAAP, labels in the Compose file are at most a later default?**
  *Recommendation: yes.* An existing stack must be adoptable untouched.
- **D9 — Default access of an exposure is `tenant`; `public` needs a second
  confirmation?** *Recommendation: yes.*
- **D10 — Default backup mode is `stop`?** *Recommendation: yes.* A short
  pause at night is a smaller harm than a backup that does not start.
- **D11 — A new volume is not ticked by itself, but reported?**
  *Recommendation: yes.* Ticking by itself would pull a cache of unknown size
  into the archive; saying nothing would lose data silently.
- **D12 — Which scanner (candidate: Trivy), and does it run as part of the
  platform or as a package?** *Recommendation: decide after stage 0;* licence
  and size on a small node are not read.
- **D13 — The tenant admin sees state and the mark, not the vulnerability
  list?** *Recommendation: yes.* The list is a to-do list for the person who
  can act on it.
- **D14 — Restore brings data and definition back; deploying stays the
  admin's act?** *Recommendation: yes for stages 1–4.* Deploying through
  Portainer's API is possible later, with a token that may write.
- **D15 — Taking over Nginx Proxy Manager is stage 4, after backup and the
  eye?** *Recommendation: yes.* It is the widest door to the ecosystem and the
  step with the most ways to lock an admin out of their own server.
- **D16 — The package `portainer` carries the Community Edition only?**
  *Recommendation: yes.* An admin with a Business licence registers their own
  installation (§8).

## Deutsche Zusammenfassung

**Worum es geht.** OAAP-Apps sind Pakete, deren Pflege die Plattform
verspricht. Das kostet je App Arbeit, und wir kommen nicht immer hinterher.
Viele Admins betreiben ihre Software ohnehin als Compose-Stacks unter
Portainer. Dieser RFC führt deshalb eine **zweite Klasse** ein: den
**Gast-Stack**. Der Admin pflegt ihn weiter selbst in Portainer; OAAP legt
sich darum: **Zugang** (Name, Zertifikat, Anmeldung des Mandanten — die Rolle
des Nginx Proxy Managers), **Sicherung** (ausgewählte Volumes im
Plattform-Archiv) und **Beobachtung** (Zustand, Alter der Images,
Sicherheitslücken, im Zwilling).

**Ehrliche Grenze.** Portainer pflegt keinen Stack. Die Pflicht wandert von
uns zum Admin, sie verschwindet nicht. Deshalb trägt jede Kachel und jede
Seite den Hinweis „Gast-Stack — gepflegt vom Betreiber dieses Knotens, nicht
von der Plattform“, und OAAP zeigt dem Admin, was er schuldet.

**Abgrenzung (§2.2).** Sideloading (RFC-0037) und der Build-Dienst (I-66)
machen aus etwas eine OAAP-App. Ein Gast-Stack wird **keine** App: kein
App-Vertrag, kein Update durch die Plattform, nur die Tür davor.

**Wie es läuft.**
- Ein Knoten zeigt Gast-Stacks nur mit dem Profil `stacks`, gesetzt an der
  Maschine (§3). Dann listet OAAP alle fremden Compose-Projekte als
  *gefunden*; es passiert nichts mit ihnen.
- Der server_admin **übernimmt** einen Stack: Titel und **genau ein Mandant**
  (§4). Soll ein Stack mehreren dienen, bekommt er einen Mandanten für
  Gemeinsames.
- **Freigabe (§5):** Dienst, Port, Name. Zugriff `tenant` (Standard), `roles`
  oder `public` (mit zweiter Bestätigung). Der Stack braucht keinen
  veröffentlichten Port. Ein Stack, der trotzdem einen Port nach außen
  öffnet, wird markiert.
- **Portainer selbst** liegt hinter der OAAP-Anmeldung, nur für server_admin.
  Wer in Portainer Admin ist, ist Root auf dem Knoten.
- **Sicherung (§6):** OAAP zeigt benannte Volumes und Host-Verzeichnisse des
  Stacks, du kreuzt an. Compose-Datei und Variablen sind immer dabei. Neue
  Volumes werden gemeldet, nicht still mitgesichert. Je Stack ein Modus:
  `stop` (Standard: anhalten, kopieren, starten), `live` (im Lauf kopieren),
  später `hook` (Dump-Befehl). Der Restore bringt Daten und Definition
  zurück; das erneute Ausrollen macht der Admin in Portainer.
- **Beobachtung (§7):** Stack, Container, Image, Volume als Objekte im
  Zwilling; Meldung bei Ausfall; Hinweis auf neuere Images; Scan auf
  Sicherheitslücken auf dem Knoten. OAAP aktualisiert nichts selbst.
- **Portainer (§8):** entweder als Paket `portainer` mitgebracht (Community
  Edition) oder eine vorhandene Installation mit einem API-Token angemeldet.
  Es geht auch ganz ohne Portainer, weil Docker selbst alles Nötige meldet.
  Ein vorhandener Nginx Proxy Manager belegt die Ports 80/443; die Übernahme
  ist eine eigene Stufe.
- **Später (§9):** unsere Compose-Vorlagen im Portainer-Format, private Netze
  über den Fernzugang (RFC-0044), lesende KI-Werkzeuge.

**Stufe 0 gemessen (23.11., oaap-test, §1.5).** Portainer CE 2.45.4, drei
Stacks über die API, ein Stellvertreter fürs Gateway, Keycloak in einem
eigenen Realm; danach alles entfernt. Die wichtigsten Befunde:
- **Ein Lese-Token liest Geheimnisse:** `GET /api/stacks` liefert die
  Variablen eines Stacks mit Werten (auch ein DB-Passwort). Token und
  Gelesenes werden wie Geheimnisse behandelt; in den Zwilling nur Namen.
- **Dienstnamen sind mehrdeutig:** Hängt das Gateway in zwei Stack-Netzen mit
  je einem Dienst `web`, antwortete nach Stop/Start der *andere* Stack. Eine
  Freigabe zielt darum immer auf den Containernamen
  (`<projekt>-<dienst>-<n>`), nie auf den Dienstnamen — sonst bedient ein Name
  von Mandant A einen Stack von Mandant B.
- **Eigene Container erkennen:** Die App-Container von OAAP tragen heute gar
  kein Label, nur das Namenspräfix `oaap-app-`. Stufe 1 gibt ihnen ein eigenes
  Label. Auf oaap-test fanden sich drei fremde Compose-Projekte und fünf
  einzelne Reste früherer Messungen.
- **Netz:** Stop in Portainer entfernt Container und Netz (außer das Gateway
  hängt noch drin, dann bleibt es still stehen); ein neues Netz muss das
  Gateway neu betreten. Löschen in Portainer lässt Volumes stehen.
  Redeploy über die API antwortet, bevor die Container neu sind.
- **Sicherung `stop` und Restore gehen:** 6,3 s Ausfall, 5000 von 5000
  Zeilen nach Löschen von Stack, Volume und Pfad und neuem Ausrollen aus der
  gesicherten Definition. Portainer merkt das Anhalten durch Docker nicht.
- **OAuth in CE geht** gegen unser Keycloak, aber **ohne Gruppen**: Mit
  automatischem Anlegen kommt jeder des Realms hinein; ohne nur Personen, die
  der Admin vorher in Portainer angelegt hat (ohne Passwort). Der lokale
  Admin bleibt als Notzugang.
- **Erster Admin braucht ein Einrichtungs-Token** aus dem Startprotokoll —
  wie bei OAAP selbst; das Paket muss das übernehmen.
- Das erste Beispiel aus dem Netz (gitea-postgres) lief mit
  `postgres:alpine` = Postgres 19 in eine Neustartschleife und öffnete Port
  3000 nach außen — genau die Fälle, die das Auge melden soll.

**Noch offen aus Stufe 0:** Restore auf einer Maschine, die den Stack nie
hatte; Nginx Proxy Manager (Stufe 4); eine Gruppenprüfung auf der
Keycloak-Seite.

**Stufen (§11).** 0 Messen auf oaap-test · 1 Übernehmen und Freigeben, Paket
`portainer` · 2 Sicherung · 3 Beobachtung · 4 vorhandene Installation und
Nginx Proxy Manager · 5 Vorlagen, private Netze, `hook`, KI.

**Entschieden (23.11.):** D1 nur eigene Knoten, zentral durch server_admin ·
D2 mitbringen und vorhandene erkennen · D3 Volumes einzeln wählbar · D4 ein
Stack, ein Mandant.

**Ebenfalls entschieden (23.11., „Wie empfohlen“):** D5 Wort „Gast-Stack“ · D6 Profil `stacks` · D7
Vertrag ist Docker, Portainer ein Adapter · D8 OAAP schreibt nichts in den
Stack, Auswahl liegt in OAAP · D9 Freigabe standardmäßig `tenant` · D10
Sicherung standardmäßig `stop` · D11 neues Volume melden, nicht ankreuzen ·
D12 Scanner nach Stufe 0 wählen · D13 Lückenliste nur für server_admin · D14
Restore ohne Ausrollen · D15 Nginx Proxy Manager erst Stufe 4 · D16 Paket nur
Community Edition.
