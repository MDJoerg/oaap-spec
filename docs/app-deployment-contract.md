# OAAP App Deployment Contract (draft v0.3)

**Audience:** developers and AI coding agents (Codex, Claude Code, …)
building an app that will be deployed on an OAAP platform.
**Status:** draft, derived from RFC-0002/0003/0004 — will be superseded
by the `oaap.apps.runtime` capability spec. Expect small changes.
**Changelog:** v0.2 (2026-08-03) incorporates feedback from the first
real app integration (BDT): platform guarantees section, secrets,
startup grace, route semantics, redeploy and backup-scope rules.
v0.3 (2026-08-04) adds the recommended pattern for app-internal users
and roles, from the second real app integration (a CRM with its own
role/permission model).

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
   headers — never render a login form.
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
   runtime. External services only if explicitly configured.
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
   pinned in the spec): WebSocket and SSE pass through; no
   gateway-imposed request-body size limit by default (internet-hardened
   profiles may introduce limits); streaming responses are not subject
   to a gateway timeout.
8. **Redeploy semantics.** Production instances require a version bump;
   test instances may redeploy the same version in place.

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
App und wird nie wieder automatisch überschrieben.
