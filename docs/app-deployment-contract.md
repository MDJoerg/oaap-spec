# OAAP App Deployment Contract (draft)

**Audience:** developers and AI coding agents (Codex, Claude Code, …)
building an app that will be deployed on an OAAP platform.
**Status:** draft, derived from RFC-0002/0003/0004 — will be superseded
by the `oaap.apps.runtime` capability spec. Expect small changes.

Give this document to your coding agent as a working instruction:
"Make the app deployable on OAAP according to this contract."

## What OAAP is, in one paragraph

OAAP runs apps as containers behind a central HTTP gateway that handles
**all authentication**. Your app never sees passwords and must not
implement login. The platform provides storage, configuration, backup,
and routing — if the app declares what it needs in a manifest.

## Deliverables

Your repository MUST contain:

1. `oaap-app.yaml` — the app manifest (see below)
2. A `Dockerfile` per service (for `native` apps; built on the target
   platform, so it must build on both amd64 and arm64 — avoid
   architecture-specific base images and binaries)

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
  - path: /                 # published through the gateway
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

health:
  path: /healthz            # GET returning 200 when healthy
```

## Rules (MUST)

1. **No own authentication.** Trust the gateway: every request carries
   the verified identity in the headers `X-OAAP-User` and
   `X-OAAP-Roles` (comma-separated; standard roles: `admin`, `keyuser`,
   `user`, `guest`, `partner`). Authorize inside the app based on these
   headers — never render a login form.
2. **HTTP only, one port per service.** No TLS in the app — the
   gateway terminates it. Listen on the port declared in the manifest,
   on `0.0.0.0`.
3. **Persist only under declared storage mounts.** Everything else in
   the container is throwaway. The platform backs up declared storage.
4. **Configuration only via environment variables** declared in the
   manifest. No config files the operator must edit.
5. **Log to stdout/stderr.** No log files.
6. **Health endpoint** as declared, returning 200 without side effects.
7. **Instance-safe:** the app may run as several instances (e.g. test
   and production, possibly different versions) on the same platform.
   Never hardcode hostnames, ports, absolute URLs, or shared paths;
   derive everything from environment and relative URLs.
8. **Offline-first:** the app must work without internet access at
   runtime. External services only if explicitly configured.

## Recommendations (SHOULD)

- Keep it to one service unless there is a real reason for more.
- Small images: slim base images, multi-stage builds.
- Migrations run automatically on startup (the platform just starts the
  new version).
- Mobile-friendly UI — field use on tablets is the norm, flaky
  connectivity included.

## German summary / Deutsche Zusammenfassung

Eine OAAP-App liefert ein Manifest (`oaap-app.yaml`) und pro Service ein
Dockerfile. Sie implementiert **keinen Login** (Identität kommt als
Header vom Gateway), lauscht auf einem HTTP-Port, schreibt persistente
Daten nur in deklarierte Mounts, wird nur über Umgebungsvariablen
konfiguriert, loggt nach stdout, bietet einen Health-Endpunkt und muss
mehrfach-instanzfähig sowie offline-fähig sein.
