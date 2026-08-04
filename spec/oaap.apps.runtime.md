# oaap.apps.runtime — App Runtime

- **ID:** `oaap.apps.runtime`
- **Version:** 0.2.0
- **Maturity:** draft (0.2 adds remote deployment via deploy tokens)
- **Based on:** RFC-0001 (capability model), RFC-0002 (roles/gateway),
  RFC-0003 (placement), RFC-0004 (manifest/app types), RFC-0005
  (addressing); platform side of the App Deployment Contract
  (`docs/app-deployment-contract.md`)

## 1. Purpose

Installs and operates apps from their manifests: build or pull, wire
behind the gateway, provision storage/config/secrets, and run **multiple
instances of the same app** (e.g. production and test, possibly in
different versions) safely side by side. The user experience is
"pick an app, click install" in the portal; the runtime delivers every
guarantee the deployment contract promises to apps.

## 2. Interface

### 2.1 App sources

An app is installed from a **package**: a directory/archive containing
`oaap-app.yaml` and (for `native`) the build contexts. Sources in 0.1:
local upload and git URL. Store directories are a later capability;
the core never comes from a store (RFC-0001).

### 2.2 Manifest processing

- Validate `oaap-app.yaml` against the published JSON Schema (part of
  this capability; CI-usable). Invalid manifests are rejected with
  human-readable errors before anything is changed.
- `native`: build images **on the target node** (build on device).
  `image`/`wrapped`: pull the referenced images.
- The **compose converter** (RFC-0004) imports an existing
  docker-compose stack and generates a `wrapped` manifest for review —
  it is tooling on top of this interface, not a separate install path.

### 2.3 Instances

- Installing creates a named **instance** (e.g. `montage-doku` and
  `montage-doku-test`). Every instance has its own: version, config
  values, storage (strictly separate), `OAAP_APP_SECRET`, entry point
  (port/subpath/hostname per RFC-0005), and portal tile.
- **Channels**: an instance is marked `production` or `test`.
  Production accepts a new deployment only with a version bump; test
  instances may redeploy the same version in place.
- Instances can be stopped, started, reconfigured, and removed
  independently. Removing an instance offers keep-or-purge for its
  storage (mirroring `oaap uninstall` semantics).
- Placement (RFC-0003): an instance MAY be pinned to a node (e.g. a
  test worker); default is the controller.

### 2.4 Contract delivery (what the runtime MUST provide)

For every instance, the runtime delivers the contract guarantees:

1. Gateway routes from the manifest (prefix match, longest wins,
   undeclared paths rejected), role enforcement, identity headers set
   and spoofing-stripped on every listener.
2. Storage mounts per instance, writable for the container's runtime
   user; included in platform backup.
3. Config as env vars; `secret: true` entries stored protected and
   masked in the portal. `OAAP_APP_SECRET` generated per instance,
   stable across restarts, delivered only as env var, never written
   into app storage or backups.
4. Health supervision honoring `startup_grace_seconds`; restart policy
   for crashed services.
5. App containers attach only to internal networks — no container port
   is ever published directly; every entry point is a gateway listener.

### 2.5 Remote deployment (deploy tokens)

Purpose: close the development loop for a project's AI coding agent —
push to the project repository, trigger a deployment, test the running
result immediately, without a platform administrator in the loop. This
is the smallest working core of the Studio idea.

- Every instance installed from a remote source records its **package
  source** (e.g. git URL, path, ref). Remote deployment always means
  "fetch the recorded source again" — a deploy request can never
  supply a different source or upload a package.
- An administrator MAY create a **deploy token** for a **test-channel
  instance**: an opaque random secret bound to exactly one instance,
  shown once at creation, revocable at any time. The platform stores
  only a digest of the token. Tokens for production-channel instances
  MUST NOT exist; moving an instance to `production` invalidates its
  tokens.
- The platform exposes a **deploy hook**: an HTTP endpoint per
  instance, reachable through the gateway on the platform's entry
  points, authorized **solely** by the instance's deploy token (bearer
  credential — no session, no identity headers). On success the
  platform fetches the source fresh, redeploys the instance
  (same-version redeploy is test-channel semantics per 2.3), and
  responds with the outcome and the instance's entry URL.
- Every remote deployment MUST be **audited**: time, instance, source
  revision, outcome — visible to administrators in the portal.
- Failed token attempts MUST be throttled like login attempts, and
  responses MUST NOT reveal whether an instance name exists.

The production path is unchanged and deliberately excluded: promoting
to production remains a human action with a version bump.

### 2.6 Portal integration

Install/configure/instance management happens in the portal (`admin`;
app configuration also `keyuser` per RFC-0002). Each instance appears
as a role-filtered launchpad tile (portal spec). Deploy tokens are
created and revoked by administrators in the portal (instance object
page), and the deploy audit trail is visible there.

## 3. Configuration

- Level-1 port range (default 8100–8199, expert-configurable;
  assignments persisted per instance — RFC-0005).
- App data root on the node (default under the platform data dir).
- Per-app expert option: HTTP fallback instead of platform-CA TLS
  (RFC-0005 resolved question 2).

## 4. Security requirements

- Default deny end to end: no app reachable without gateway
  authentication unless a route is explicitly `public` in its manifest.
- Instance isolation: storage, secrets, and internal networks are per
  instance; a test instance can never read production data.
- `wrapped` apps with third-party images receive the same enforcement —
  platform security must not depend on app quality (RFC-0002).
- Manifest-declared roles are the only path to route authorization;
  apps cannot widen their own exposure at runtime.
- Deploy tokens are stored only as digests, are bound to exactly one
  test instance, and authorize exactly one action: redeploy that
  instance from its recorded source. They grant no login, no API
  access, and no influence on routes, roles, or configuration.

## 5. Conformance tests (described)

1. **Install happy path**: valid package → instance running, tile in
   portal, reachable through its entry point after login.
2. **Default deny**: unauthenticated request to the instance's entry
   point redirects to login; a user lacking the route's roles is
   rejected; the tile is hidden for them.
3. **Undeclared path**: request outside declared routes is rejected at
   the gateway and never reaches the app.
4. **Header guarantee**: client-sent `X-OAAP-*` headers never reach the
   app; verified identity headers always do (on every listener).
5. **Second instance**: installing a `test` instance yields separate
   storage, separate port, separate `OAAP_APP_SECRET`; writing in test
   never appears in production storage.
6. **Redeploy semantics**: same-version redeploy is rejected for
   production, accepted for test.
7. **Storage writability**: the container's non-root user can write its
   declared mounts immediately after install.
8. **Secret stability**: `OAAP_APP_SECRET` survives restart and
   platform reboot; it appears in no backup of the instance's storage.
9. **Startup grace**: an app whose health endpoint answers only after
   the declared grace period is not killed during it.
10. **Invalid manifest**: schema violations are rejected with a clear
    message; the system is unchanged.
11. **Removal**: removing an instance removes containers, routes, and
    tile; storage is kept or purged as chosen.
12. **Deploy hook happy path**: after a new commit in the recorded
    source, a POST with a valid deploy token redeploys the test
    instance; the new state is served through its entry point and an
    audit entry (time, revision, outcome) exists.
13. **Token required**: a missing or wrong token is rejected without
    any side effect; repeated failures are throttled; the response for
    a wrong token and a nonexistent instance is indistinguishable.
14. **Production protection**: creating a deploy token for a
    production instance is refused; moving a test instance with a
    token to production invalidates the token, and the hook refuses
    afterwards.
15. **Revocation**: a revoked token is refused immediately.
16. **Source pinning**: a deploy request cannot change the source —
    the redeploy uses the recorded package source even if the request
    carries a different one.

## 6. Dependencies

`oaap.core.host`, `oaap.core.gateway`, `oaap.core.identity`,
`oaap.core.portal`

## 7. Maturity

`draft` — first implementation target: run the two real pilot apps
(montage-doku as `native` production+test, BDT as `native` test) through
tests 1–11 on the reference platform. 0.2 target: tests 12–16 with the
pilot CRM's test instance and its AI coding agent as the first real
remote deployer.
