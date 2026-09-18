# OAAP App Deployment Contract (draft v0.6)

**Audience:** developers and AI coding agents (Codex, Claude Code, …)
building an app that will be deployed on an OAAP platform.
**Status:** draft, derived from RFC-0002/0003/0004 — will be superseded
by the `oaap.apps.runtime` capability spec. Expect small changes.
**Changelog:** v0.2 (2026-08-03) incorporates feedback from the first
real app integration (BDT): platform guarantees section, secrets,
startup grace, route semantics, redeploy and backup-scope rules.
v0.3 (2026-08-04) adds the recommended pattern for app-internal users
and roles, from the second real app integration (a CRM with its own
role/permission model). v0.4 (2026-08-04) adds the project mailbox
(AI collaboration convention) and the deploy-hook workflow for test
deployments. v0.5 (2026-08-16) adds the **artifact path** — shipping the
package itself instead of a repository the platform fetches (RFC-0019) —
and states what needs a human: an envelope that widens, and every step
to production (RFC-0020). Both were already implemented and specified;
this document is where the app side reads them. v0.6 (2026-09-18)
catches up with what was built since and never reached this document,
from the fourth onboarding (the Handball-Infoboard): **tenants**,
**machine callers with API keys** (RFC-0027), what a **public route**
really gets (no identity, a rate brake, a filtered log), **outbound
network**, **build limits**, and **open streams across a gateway
reload**.

Give this document to your coding agent as a working instruction:
"Make the app deployable on OAAP according to this contract."

## What OAAP is, in one paragraph

OAAP runs apps as containers behind a central HTTP gateway that handles
**all authentication**. Your app never sees passwords and must not
implement login. The platform provides storage, configuration, secrets,
backup, and routing — if the app declares what it needs in a manifest.

## Deliverables

Your repository MUST contain:

1. `oaap-app.yaml` — the app manifest (see below)
2. A `Dockerfile` per service (for `native` apps; built on the target
   platform, so it must build on both amd64 and arm64 — avoid
   architecture-specific base images and binaries)

The manifest's JSON Schema is published at
[`schema/oaap-app.schema.json`](../schema/oaap-app.schema.json) —
validate `oaap-app.yaml` against it in CI before deploying.

**The schema is stricter than a node, on purpose** (RFC-0012 §8.2). It
rejects unknown fields, because in CI an unknown field is a typo and you
want to hear about it. A node in the field reads tolerantly instead: it
accepts any `oaap_manifest` whose MAJOR it implements, ignores what it
does not know, and refuses only a foreign MAJOR. So keep validating
against the newest schema — but do not expect a node to reject what the
schema rejects, and do not rely on that as a safety net.

## The manifest (`oaap-app.yaml`)

Example for a typical single-service web app:

```yaml
oaap_manifest: "0.1"

app:
  id: montage-doku          # stable, lowercase, [a-z0-9-]
  name: Montagedokumentation
  version: 0.1.0            # semver, bump on every release
  type: native              # native | image | wrapped

services:
  web:
    build: .                # native: path to Dockerfile context
    # image: ghcr.io/...   # image/wrapped: reference instead of build
    port: 8080              # the ONE http port the service listens on

routes:
  - path: /                 # prefix match, longest declared prefix wins
    roles: [user, keyuser, admin]
  - path: /signoff          # e.g. customer sign-off on site
    roles: [guest]
  # public routes are possible but discouraged: roles: [public]

storage:
  - name: data
    mount: /data            # write persistent files ONLY here

config:
  - key: COMPANY_NAME       # delivered to the app as env var
    label: "Firmenname"
    default: ""
  - key: EXTERNAL_API_KEY   # secrets: masked input, protected storage
    label: "API-Key Fremdsystem"
    secret: true

health:
  path: /healthz            # GET returning 200 when healthy
  startup_grace_seconds: 120  # e.g. time for migrations on startup
```

## Rules (MUST)

1. **No own authentication.** Trust the gateway: every request carries
   the verified identity in the headers `X-OAAP-User` and
   `X-OAAP-Roles` (comma-separated; standard roles: `admin`, `keyuser`,
   `user`, `guest`, `partner`). Authorize inside the app based on these
   headers — never render a login form. A caller's roles may also
   include `server_admin` (RFC-0008) if they hold it — it is forwarded
   like any other role, but it is a **platform-only** authority (server
   administration, not app administration) and apps MUST NOT treat it
   as implying anything about their own app-level permissions; a
   manifest's routes never declare it as a required role.
2. **HTTP only, one port per service.** No TLS in the app — the
   gateway terminates it. Listen on the port declared in the manifest,
   on `0.0.0.0`. Additional listeners the app opens are **never
   published** — only the declared port is reachable from outside.
3. **Persist only under declared storage mounts.** Everything else in
   the container is throwaway. The platform backs up declared storage.
4. **Configuration only via environment variables** declared in the
   manifest. Mark sensitive entries `secret: true`. No config files the
   operator must edit.
5. **Log to stdout/stderr.** No log files.
6. **Health endpoint** as declared, returning 200 without side effects.
7. **Instance-safe:** the app may run as several instances (e.g. test
   and production, possibly different versions) on the same platform.
   Never hardcode hostnames, ports, absolute URLs, or shared paths;
   derive everything from environment and relative URLs.
8. **Offline-first:** the app must work without internet access at
   runtime. External services only if explicitly configured — that
   means: the address of every outbound target is a **declared config
   variable** (with a default if you like), never a constant in the
   code. The platform does not restrict outbound traffic today (see
   "Network and build" below); your app must still degrade, not fail,
   when the target is unreachable.
9. **Accept the platform's Host.** Do not pin `Host` checks to
   `localhost` (common DNS-rebinding protection in local-server apps) —
   the app receives the platform's public hostname; see guarantee 2.

## What the platform guarantees

Apps may rely on the following; the reference implementation and every
conformant provider MUST deliver them (pinned formally in the
`oaap.apps.runtime` / `oaap.core.gateway` capability specs):

1. **Identity headers cannot be spoofed.** The gateway strips
   `X-OAAP-User` and `X-OAAP-Roles` from every incoming client request
   on **all** routes — including `public` ones — and sets them itself
   after authentication. If the header is present, it is authentic.
   On a `public` route the gateway does not authenticate at all, so the
   headers are **always absent there — even for a caller who is logged
   in**. A route cannot be "public and additionally roles": as soon as a
   real role is declared next to `public`, login is required.
2. **Host and forwarding headers.** The app receives the original
   `Host` header unchanged, plus `X-Forwarded-Proto` and
   `X-Forwarded-For` set by the gateway (needed for absolute URLs and
   redirects).
3. **Route semantics.** `path` is a prefix match; the longest declared
   prefix wins; requests under no declared route are rejected at the
   gateway and never reach the app.
4. **Per-instance storage.** Declared mounts are provisioned **per app
   instance** — a test instance and a production instance never share
   data. Mounts are writable for the container's runtime user (use a
   fixed numeric `USER` in the Dockerfile; running as non-root is
   expected).
5. **Instance secret.** Every app instance receives `OAAP_APP_SECRET`:
   a stable random value, delivered only as an environment variable and
   **never stored inside the app's mounts or backups**. Use it as a
   key-encryption-key when you encrypt data at rest — then backups
   contain ciphertext only.
6. **Startup grace.** During `startup_grace_seconds` after start, a
   failing health endpoint does not get the app killed (migrations may
   run); afterwards the endpoint is polled as liveness.
7. **Gateway properties** (reference values; minimum guarantees to be
   pinned in the spec): WebSocket and SSE pass through, on public and
   on authenticated routes; no gateway-imposed request-body size limit
   by default (internet-hardened profiles may introduce limits);
   streaming responses are not subject to a gateway timeout, and an
   idle WebSocket is not closed by the gateway. **A deployment of
   another app does not cut your open streams** (`oaap.core.gateway`
   0.2.8; before reference 0.1.102 it did). Your clients MUST still
   reconnect on their own: your **own** redeploy or restart ends your
   streams with your container, and the nightly backup stops it
   briefly. Reconnect with a little random delay, so that all devices
   behind one connection do not knock at the same second, and send a
   ping every 20–30 s for the routers in front of the gateway.
8. **Redeploy semantics.** Production instances require a version bump;
   test instances may redeploy the same version in place.

## Tenants

A node can host several **tenants** (customers, departments, clubs —
`oaap.core.tenant`). What that means for an app:

- Every app **instance** belongs to exactly **one** tenant, with its own
  mounts. The app sees nothing of it: there is no tenant header and no
  tenant environment variable, and none is needed.
- The **boundary is enforced at the gateway**: a user of another tenant
  is refused before the request reaches your app. Do not filter by
  tenant yourself. (The node operator with `server_admin` passes
  everywhere; that is deliberate and audited.)
- If your app has its own multi-client model (clubs, sites, branches
  inside one instance), keep it — do **not** try to map it onto OAAP
  tenants.
- An instance's internal key carries the tenant as a prefix, and its
  public addresses can change (further names, aliases, renaming). Build
  every link from `Host` + `X-Forwarded-Proto` of the current request,
  never from a name you assume.
- Everyone who passes the gateway on your routes is a member of the
  instance's tenant with one of the declared roles. If "whoever gets in
  may do everything" is your app's model, ask the operator to limit the
  instance to **visibility groups** (RFC-0007) rather than relying on a
  small tenant.

## Machine callers: API keys (RFC-0027)

A program that calls your app — a desktop client, a webhook, another
system, a script — does **not** need a `public` route or a key scheme of
your own:

1. The operator creates a **machine principal** (a user without a
   password) with a role, in the portal under "Zugänge" or with
   `oaap machine add <name> --tenant <tenant> --roles user`.
2. The operator issues a **key** for it, limited to **one instance** and
   with an expiry (1–365 days; "never" does not exist):
   `oaap key issue <name> --instance <key> --days 180`.
3. The program calls your **normal, protected** route with
   `Authorization: Bearer oaapk_…`.

The gateway checks the key, and your app receives `X-OAAP-User: <name>`
and `X-OAAP-Roles` **exactly as for a person** — the user-on-first-
contact pattern below applies unchanged. A key for another instance is
refused with `403`, an unknown or revoked one with `401`, immediately.

- The gateway forwards the request **unchanged**: your app sees the
  `Authorization` header. On protected routes, do not use that header
  for anything of your own and do not reject a value you do not know —
  the caller is already authenticated.
- A browser page on another origin calling your API with a key first
  sends an `OPTIONS` preflight. The gateway hands that preflight to
  **your app** without a login check; answer it with `200`/`204` and
  your CORS headers, or the browser stops before the real call.
- A browser **cannot** attach a key to a page navigation or to a
  WebSocket handshake. For devices without a user — a TV in a hall, a
  shared tablet, smart glasses — see the next section.
- The role `partner` is for **people** of external companies, not for
  machines.

## Public routes: what they really get

`public` is sometimes the only way — a display that nobody logs into, a
share link. It is allowed, it widens the envelope (a human confirms it,
see "Working with the platform side"), and it comes with these facts:

- **No identity.** See guarantee 1: the headers are always absent.
- **Protect it yourself.** A key, token or code is your app's business:
  make it long and random, revocable, and lock it out after repeated
  failures. The platform does not know which key is being guessed.
- **A rate brake in front of you** (RFC-0010): per client address and
  instance, default 300 requests per 60 s; above that the gateway
  answers `429` with `Retry-After` and your app never sees the request.
  A WebSocket counts **once**, at the handshake. All devices behind one
  internet connection count as **one** client — if a room full of
  devices reloads at once, tell the platform side a realistic number;
  the limit is adjustable per instance. Honour `Retry-After` instead of
  retrying blindly.
- **The access log keeps the path.** The gateway logs requests to every
  published name. Query strings and the values of `Authorization` and
  `Cookie` are **not** written (`oaap.core.gateway` 0.2.8), but the
  **path** is. A secret in the path therefore ends up in a file on the
  server. Carry device and share keys in the URL **fragment**
  (`https://host/display#k=…`): the browser never sends the part after
  `#` to any server, so it is in no log, no `Referer` and no proxy. Your
  page reads it from `location.hash`, sends it as the first WebSocket
  message or as a request header, and removes it from the address bar
  with `history.replaceState`.
- **A rehearsal serves none.** A rehearsal instance (RFC-0030 — test
  code on a copy of production data) requires login on **every** route,
  including those your manifest declares `public`. Devices that depend
  on a public route do not work there; that is intended.

## Network and build

- **Inbound:** your container publishes no port on the host and sits
  alone in its own network. Other apps on the node cannot reach it, and
  it cannot reach them. A connection between two apps is an explicit
  operator decision (`oaap app link`), never in the manifest.
- **Outbound:** open, today. HTTPS and outbound WebSockets to the
  internet work without any declaration. Per-app egress control may
  come later as a node profile; build for "configured target, graceful
  degradation" (rule 8) and you will not notice.
- **Build (`native`):** `docker build` of your `Dockerfile` runs on the
  **target node**, with internet access — the public npm, PyPI or Maven
  registries are reachable, and so are prebuilt native modules
  downloaded during install. There are **no build-time secrets**: if a
  private registry becomes necessary, write to the platform side before
  you build it in. Include a compiler toolchain in your build stage when
  a native module may have to compile (arm64 nodes are where prebuilds
  are missing).
- **Limits:** a package (ZIP) is at most **256 MB**; `node_modules`,
  build output and virtual environments do not belong in it. A whole
  deployment — build plus start until healthy — is aborted after
  **20 minutes**, cleaned up, and reported as failed.

## What OAAP does NOT back up

Only declared storage mounts are backed up. Data an app keeps on the
client (e.g. browser IndexedDB/localStorage) is outside the platform's
reach — apps holding primary data client-side SHOULD make that clear to
their users and offer their own export path.

## App-internal users and roles (recommended pattern)

Many business apps need their own user records and a finer role or
permission model than OAAP's five standard roles — that is expected and
welcome. The seam between both worlds follows one principle:

> **The platform decides who someone is and whether they may enter the
> app. The app decides who they are *inside* the app.**

Concretely (SHOULD):

1. **Admission is the manifest's job.** The route roles decide who
   reaches the app at all; the gateway enforces them. Inside the app,
   authorize against your own model.
2. **First contact creates an app user — the OAAP role is only a
   starting hint.** When a yet-unknown `X-OAAP-User` arrives, create
   your own user record for it. Either derive an initial business role
   from `X-OAAP-Roles`, or — for sensitive apps — create the account as
   **pending/unassigned** with minimal permissions and show a "please
   contact your administrator" page. Give app administrators an
   approval view where new logins are assigned a business role **or
   linked to an existing master-data record** (an employee usually
   exists in the app before their first login — link, don't duplicate).
3. **After the first assignment, the app owns the role.** Never
   re-derive the business role from `X-OAAP-Roles` on later requests —
   a continuous sync silently overwrites what app administrators
   configured. You don't need it for security either: a user
   deactivated on the platform is blocked at the gateway and never
   reaches the app again.

Additional guidance: `X-OAAP-User` (the username) is the stable join
key — store it on your user record; treat display names as changeable.
Do not seed real persons as hard-wired login users; seed them as
master data without a login and link on first contact. A platform
service for centrally managed app roles may come later as an opt-in
capability; this pattern works without any platform support.

## Working with the platform side

Two mechanisms connect your project to the platform team and its AI —
both live in or next to your repository, not in chat sessions:

1. **The project mailbox (`collab/`).** The repository carries the
   correspondence between the AIs (and humans) involved: letters in
   `collab/letters/`, reports (test results, review feedback) in
   `collab/reports/`. The rules — **pull first at every session start**,
   letters are immutable (answer with a new letter, `re:` header),
   commit and push a letter immediately, write so the humans can read
   along — are defined in [ai-collaboration.md](ai-collaboration.md).
   Your human will not remind you to check the mailbox; that is your
   job.
2. **The deploy hook (test channel).** Your briefing hands you a hook
   URL and a bearer token for your app's **test instance**. After
   pushing a deployable state: `POST <hook-url>` with
   `Authorization: Bearer <token>` — the platform pulls your
   repository fresh, redeploys the test instance, and answers with the
   outcome and the URL to test at (HTTP 202 means still building —
   poll `GET <hook-url>/status`). The token deploys **only** this test
   instance and nothing else; production deployments remain a human
   action with a version bump.
3. **Deploying a package instead of a repository** (RFC-0019). If the
   platform cannot reach your source — a private repository, an
   air-gapped node, a file on a stick — you ship the **package
   itself**, with the same token, in three steps:

   ```sh
   # 1. announce: the complete manifest, the checksum and the size
   curl -X POST <hook-url>/announce \
     -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
     -d '{"manifest": "<complete oaap-app.yaml>",
          "artifact_sha256": "<sha256 of the zip>",
          "artifact_bytes": <size in bytes>}'
   # answer: {"ok": true, "upload_token": "...", "upload_url": "..."}

   # 2. upload: only against that single-use token (valid 15 minutes)
   curl -X PUT "<upload_url>" \
     -H "Authorization: Bearer <upload_token>" \
     -H "Content-Type: application/zip" --data-binary @app.zip
   ```

   Rules that decide whether this succeeds:

   - The manifest **inside** the ZIP must be **byte-identical** to the
     announced one. Announce what you are shipping.
   - `app.version` must **change with every deployment**. Without a
     commit hash, the version is the only answer to "what is running?".
   - The archive holds your project directory: `oaap-app.yaml` in the
     root **or** in exactly one top-level folder. No absolute paths, no
     `..`, no symlinks — such an archive is refused unread.
   - Announcing costs nothing and refuses **before** the transfer, so
     announce first and read the answer rather than uploading blind.
   - A refusal always carries a machine-readable `refused` code **and**
     a sentence saying what to change. Read both; they are written for
     you, not for a log.
   - **No answer is not a refusal.** A small node may build longer than
     your client waits. Ask `GET <hook-url>/status` before you retry —
     a blind retry with the same version will be refused anyway.
4. **What needs a human, and why you should say so.** Your token
   redeploys **within the envelope the instance already has**. A
   deployment that would widen it — a route that becomes reachable
   without login, a new storage mount, a new gateway-bypassing port, a
   new link to another app — is held back until an administrator
   confirms *that* manifest. This is not an obstacle to route around:
   when you need one of these, say so in the mailbox with the reason,
   in the same deployment where it appears. Going to **production** is
   always a human decision (RFC-0020): the administrator promotes the
   artifact you tested, unchanged, so make sure the package you hand
   over is the one you mean.

## Recommendations (SHOULD)

- Keep it to one service unless there is a real reason for more.
- Small images: slim base images, multi-stage builds.
- Migrations run automatically on startup (covered by startup grace).
- Mobile-friendly UI — field use on tablets is the norm, flaky
  connectivity included.
- If your app uses secure-context browser APIs (`crypto.subtle`,
  clipboard, service workers, WebAuthn): degrade gracefully and say why
  when they are unavailable. During gateway-less test deployments, test
  via `http://localhost` (SSH port forward), never via `http://<ip>` —
  plain HTTP over an IP disables these APIs.

## German summary / Deutsche Zusammenfassung

Eine OAAP-App liefert ein Manifest (`oaap-app.yaml`) und pro Service ein
Dockerfile. Sie implementiert **keinen Login** (Identität kommt als
Header vom Gateway und ist garantiert nicht fälschbar), lauscht auf
einem HTTP-Port, akzeptiert den Plattform-Hostnamen, schreibt
persistente Daten nur in deklarierte, **je Instanz getrennte** Mounts,
wird über Umgebungsvariablen konfiguriert (Geheimnisse mit
`secret: true`; zusätzlich liefert die Plattform `OAAP_APP_SECRET` als
Schlüssel für eigene Verschlüsselung, das nie in Backups landet), loggt
nach stdout, bietet einen Health-Endpunkt mit Startup-Schonfrist und
muss mehrfach-instanzfähig sowie offline-fähig sein. Routen sind
Präfix-Matches (längster gewinnt), nicht deklarierte Pfade blockt das
Gateway, zusätzliche Ports werden nie veröffentlicht. Eigene
App-Benutzer und Fachrollen sind ausdrücklich vorgesehen: Die Plattform
entscheidet, *wer* jemand ist und ob er die App betreten darf; die App
entscheidet, wer er *in der App* ist. Die OAAP-Rolle dient nur als
Startvorschlag bei der Erstanlage (oder der Benutzer startet
„unzugeordnet" und wird von der App-Verwaltung freigegeben und mit
vorhandenen Stammdaten verknüpft) — danach gehört die Fachrolle der
App und wird nie wieder automatisch überschrieben. Die Zusammenarbeit
mit der Plattformseite läuft über das Projekt-Repo: der
**KI-Postkasten** (`collab/` — Briefe und Berichte, immer erst `pull`,
Briefe unveränderlich, sofort pushen) und der **Deploy-Hook** (nach dem
Push per Bearer-Token die eigene Test-Instanz ausrollen und sofort
unter Realbedingungen testen; Produktivsetzung bleibt Menschensache mit
Versions-Bump).

**Neu in v0.6 — nachgetragen, was gebaut war, aber hier fehlte:**

- **Mandanten:** Jede Instanz gehört genau einem Mandanten; die App sieht
  davon nichts (keine Kopfzeile, keine Variable) und filtert nicht
  selbst — die Grenze setzt das Gateway durch. Ein eigenes
  Mandantenmodell der App (Vereine, Standorte) bleibt, wie es ist. Links
  immer aus `Host` und `X-Forwarded-Proto` bauen. Wer durchs Gateway
  kommt, ist Mitglied des Mandanten — soll „wer reinkommt, darf alles"
  gelten, grenzt der Betreiber die Instanz auf Sichtbarkeitsgruppen ein.
- **Programme als Aufrufer:** Statt einer `public`-Route mit eigenem
  Schlüssel gibt es API-Schlüssel (RFC-0027): Maschinen-Prinzipal mit
  Rolle, Schlüssel auf eine Instanz begrenzt und mit Ablauf,
  `Authorization: Bearer oaapk_…` auf der normalen geschützten Route. Die
  App sieht `X-OAAP-User` wie bei einem Menschen. Den
  `Authorization`-Header auf geschützten Routen nicht für Eigenes
  benutzen; ein `OPTIONS`-Preflight erreicht die App ohne Anmeldung und
  muss dort beantwortet werden. `partner` ist eine Rolle für Menschen.
- **`public`-Routen:** keine Identität (die Kopfzeilen fehlen immer,
  auch für Angemeldete), eigener Schutz mit Sperre nach Fehlversuchen,
  eine Bremse im Gateway (Standard 300 Anfragen je 60 s und Adresse,
  ein WebSocket zählt einmal, alle Geräte hinter einem Anschluss zählen
  als einer), ein Zugriffsprotokoll **ohne** Query-Teil und ohne
  Schlüsselwerte, aber **mit** Pfad — Geräte- und Freigabeschlüssel
  deshalb ins Fragment der Adresse (`#…`). Eine Generalprobe bedient
  keine `public`-Route.
- **Netz und Bau:** nach innen abgeschottet, nach außen offen; Ziele
  über deklarierte Variablen, bei Ausfall weiterarbeiten. Gebaut wird
  auf dem Zielknoten mit Internetzugang, ohne Build-Geheimnisse; Paket
  höchstens 256 MB, ein Deployment höchstens 20 Minuten.
- **Offene Verbindungen:** Das Ausrollen einer **anderen** App trennt
  eure WebSockets nicht mehr (seit Referenz 0.1.102). Neu verbinden
  müssen Clients trotzdem können — beim eigenen Ausrollen und beim
  nächtlichen Backup.

**Neu in v0.5 — der Paket-Weg (RFC-0019):** Kommt die Plattform an die
Quelle nicht heran (privates Repository, Knoten ohne Internet, Datei
vom Stick), liefert die KI das **Paket selbst**, mit demselben Token
und in drei Schritten: **anmelden** (vollständiges Manifest, Prüfsumme,
Größe) → die Plattform prüft und gibt eine **Einmal-Erlaubnis** zurück
→ **hochladen**. Bedingungen: Das Manifest **in** der ZIP muss
zeichengleich zum angemeldeten sein, `app.version` muss sich bei jedem
Deployment ändern, und das Archiv enthält das Projektverzeichnis
(Manifest in der Wurzel oder in genau einem Oberordner, keine
absoluten Pfade, kein `..`, keine Symlinks). **Keine Antwort ist keine
Ablehnung** — dauert der Bau länger als die Geduld des Clients, fragt
man `GET <hook>/status`, statt blind zu wiederholen.

**Was einen Menschen braucht:** Ein Deploy-Token rollt **innerhalb des
bereits erteilten Rahmens** neu aus. Was den Rahmen erweitert (eine
Route ohne Anmeldung, ein neuer Speicher, ein Port am Gateway vorbei,
eine neue Verbindung zu einer anderen App), wird zurückgehalten, bis
ein Administrator **genau dieses** Manifest bestätigt — das ist kein
Hindernis zum Umgehen, sondern der Anlass, es im Postkasten zu
begründen. Und die **Produktivsetzung** ist immer eine menschliche
Entscheidung (RFC-0020): Übernommen wird das Paket, das getestet wurde,
unverändert.
