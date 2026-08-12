# oaap.apps.runtime — App Runtime

- **ID:** `oaap.apps.runtime`
- **Version:** 0.2.8
- **Maturity:** draft (0.2 adds remote deployment via deploy tokens;
  0.2.1 adds the one-click store install in 2.6 with test 17; 0.2.2
  adds instance visibility in 2.7 and moves platform-level portal
  operations from `admin` to `server_admin`, per RFC-0007/RFC-0008;
  0.2.3 spells out instance **configuration** in 2.8 — promised since
  2.3/2.4.3 but never described in interface terms, and missing from
  the reference implementation until it blocked a real production
  rollout; 0.2.4 answers the open question in 2.6 — instances MAY be
  created from the portal, on a node whose profile says it is a
  workbench, per RFC-0011; 0.2.5 works RFC-0012 in — manifest version
  handling in 2.2 (strict schema, tolerant node, `must_understand`),
  resolution by trust class in 2.6, and store sources as objects that
  survive a move in the new 2.9. Both old rules were traps: the
  manifest version was an equality check, so the first manifest 0.2
  would have been rejected by every node in the field, and an app id
  resolved to the first configured source, which made a foreign list a
  takeover path; 0.2.6 adds the **application class** in the new 2.10 —
  a manifest may say it is a `service`, and a service gets no launchpad
  tile, overridable per instance. Manifest 0.2 and the first field the
  version tolerance of 2.2 was built for; 0.2.7 spells out in 2.8 what
  `secret: true` promises and what it does not — exposure through the
  platform's surfaces, not encryption at rest, and therefore nothing
  about backups. Nothing changes; an unstated promise about credentials
  was the risk, per RFC-0013 §5)
- **Based on:** RFC-0001 (capability model), RFC-0002 (roles/gateway),
  RFC-0003 (placement), RFC-0004 (manifest/app types), RFC-0005
  (addressing), RFC-0007 (visibility groups), RFC-0008 (server_admin),
  RFC-0011 (node profiles), RFC-0012 (store sources and list format);
  platform side of the App Deployment Contract
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
- **Version handling is asymmetric on purpose** (RFC-0012 §8.2). The
  schema is an authoring tool and MUST stay strict — unknown fields are
  a typo where they are written. A **node** MUST read tolerantly:
  `oaap_manifest` is `MAJOR.MINOR`; a node accepts every manifest whose
  MAJOR it implements, ignores fields it does not know, and refuses only
  a foreign MAJOR. A higher MINOR is reported, not rejected. Without
  this rule, every extension of the manifest format would be a flag day
  for every node already in the field.
- **`must_understand`** is the exception that makes the rule above safe:
  a manifest MAY name features a reader has to understand to install the
  app correctly. A node that does not implement one of them MUST refuse
  **that app**, with a message naming the feature — rather than install
  something half-understood. Only features whose omission breaks the
  install belong here; optional additions do not.
- **Manifest 0.2** adds one field: `app.class` — see 2.10. It is the
  first use of the tolerance above, and deliberately a mild one, so
  that the mechanism is proven by something whose omission costs an
  untidy launchpad rather than a broken install.
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

### 2.11 Instance networks and isolation (RFC-0016)

Each app instance runs on **its own network**, isolated from every
other app and from the platform's own services.

- On install the platform creates a per-instance network
  (`oaap-inst-<instance>` in the reference); all container(s) of the
  instance join it and resolve each other by name.
- The **gateway** joins each instance network so it can proxy in. The
  identity and portal services do **not** — an app can reach the
  gateway and its own siblings, and nothing else. This is what makes
  the platform's internal APIs unreachable from an app (closing the
  escalation of RFC-0015 A4 structurally; the internal-API key of
  `oaap.core.identity` 4.3 remains as defence in depth).
- The gateway's membership MUST be restored whenever the gateway is
  recreated (a platform update does this): after recreating core
  services, the platform reconnects the gateway to every instance
  network. A node that skips this leaves apps unreachable (502).
- **App-to-app links** are the only way one app reaches another, and
  they are an explicit operator decision, never in the manifest:
  a link `A → B` is recorded in the registry (survives redeploy),
  realised as a **dedicated network** both instances' primary
  containers join (not by placing A on B's own network — B's private
  containers stay private), and revocable (revocation tears the
  dedicated network down). Removing an instance tears down its network
  and every link that referenced it.
- Outbound internet access is unchanged (on by default). Per-app egress
  control is a possible later, profile-gated capability, out of scope
  here.

The manifest is unaffected: an app declares routes and services as
before. Isolation, gateway bridging and links are the platform's and
the operator's concern, not the app author's.

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

Install/instance management and the store happen in the portal,
restricted to `server_admin` (RFC-0008 — this operates on the
platform itself, not on one app's own data); app **configuration**
(an installed instance's own settings) stays `admin`/`keyuser` per
RFC-0002, unchanged. Each instance appears as a role- and
group-filtered launchpad tile (portal spec, RFC-0007). Deploy tokens
are created and revoked by server_admins in the portal (instance
object page), and the deploy audit trail is visible there.

**One-click store install.** A server_admin MAY install an app
directly from the portal's store page. The trust model mirrors 2.5
("a request can never supply a source"):

- The portal request names **only the app id and the source it was
  seen in**. It carries no package source, no manifest, no version —
  nothing installable.
- The privileged host side resolves the app id **against the
  platform's configured store sources** (the same list the store page
  reads) and installs from what *that* lookup returns. An app id that
  no configured source lists is refused, and so is a source id that is
  not configured. A compromised portal can therefore at worst install
  apps the server_admin already chose to trust by configuring their
  source, and can only *choose among* those sources — never add one.
- **When several sources list the same app id, the highest trust class
  wins**; configured order decides only within one class (RFC-0012 §3).
  Resolving by order alone made a foreign list a takeover path: claim a
  known id, sit above the real list, collect the one-click install.
- **An installed instance records the source it came from**, and a
  later resolution for that instance prefers it as long as that source
  still lists the app. Changing an instance's source stays possible and
  becomes a deliberate, reported act instead of a silent one.
- **Installing from an `unverified` source MUST take an explicit
  confirmation**, and the confirmation MUST reach the deploy log: who
  accepted which source, when, for which app. This is a brake against
  inattention, not a security boundary — what protects against a
  compromised portal is the resolution rule above.
- One-click installs land on the **production channel** (installing
  from the store means using the app); test instances for development
  remain a deliberate choice (CLI, or the portal on a development
  node — see below). Re-clicking an installed app follows the redeploy
  semantics of 2.3 — same version on production is refused, a newer
  listed version updates.
- Every one-click install is **audited** like a remote deployment
  (time, app, source, outcome) and visible to server_admins.

**Creating instances from the portal — only on a `dev` node.** The rule
above ("a request can never supply a source") is what makes a
compromised portal survivable, and it is kept for every ordinary node.
On a node whose profile says it is a workbench (`oaap.core.host` 2.5,
RFC-0011), a server_admin MAY additionally create instances from the
portal:

- **Test channel only.** Portal-created instances land on the test
  channel; the production path stays the one-click store install. This
  is the same reasoning as 2.5: creating a test instance is a
  development act, and the profile is what says that development
  happens here.
- **The package source MAY be named by the request** — the case a
  brand-new app repository is always in, before any store list carries
  it. The host MUST still refuse anything that is not a remote Git
  source (no local paths — that would let the portal build an image
  from arbitrary files on the machine, a different power altogether).
- The host side MUST re-check the profile itself. The portal deciding
  it is allowed would make the profile a portal setting.
- **What is given up must be stated, not buried:** on a `dev` node, a
  compromised portal can install code the operator never chose to
  trust. That is a reasonable trade on a workbench and a bad one on a
  machine holding customer data — hence per node, not globally.
- Creating an instance is **audited** like every other deployment.

An implementation without node profiles behaves exactly as before: no
node has `dev`, so the portal creates nothing.

### 2.7 Visibility (RFC-0007)

Every registry instance carries an optional `visibility` setting,
alongside — never inside — the manifest-derived `roles`:

- **`{}` (default, "all")**: unchanged behavior — role check only.
- **`{"groups": [g1, g2, ...]}`**: an ADDITIONAL restriction, checked
  by the gateway/identity alongside the role check (both must pass;
  `oaap.core.identity` 2.6, `oaap.core.gateway` "Visibility groups").
  This is an **operator decision made after installation**, per
  instance — never in the app's distributed manifest (a store package
  does not know an operator's teams).
- Set via `sudo oaap app visibility <instance> all` /
  `sudo oaap app visibility <instance> groups g1,g2,...` — updates the
  registry, regenerates that instance's Caddy site(s) (LAN and, if
  registered, external subdomain — the same generator function serves
  both), and reloads the gateway. Same mechanics as `oaap external
  set`/`oaap edge add`.
- The portal offers the same control on `/instances` (list report +
  object page, server_admin only) — since its registry mount is
  read-only, the change is queued through the same host-side worker
  that already applies store installs (2.6), not written directly.
- Visibility **survives reinstall/redeploy** of the same named
  instance (like the port assignment in 2.3) — a redeploy must not
  silently reopen a group-restricted instance.
- `server_admin` bypasses every visibility restriction (RFC-0008).

### 2.8 Instance configuration

An instance's config values (2.3) are **operator-owned and editable for
the life of the instance** — install time is not the only chance to set
them. The deployment contract promises apps exactly this ("no config
files the operator must edit", rule 4), so the runtime must offer it:

- **Only declared keys.** The editable set is the manifest's `config`
  block of the installed version. Neither CLI nor portal can introduce
  an environment variable the app never declared, and `OAAP_APP_SECRET`
  is platform-owned — never listed, never settable.
- **Secrets are write-only.** A `secret: true` value is never rendered
  back into a page or printed by the CLI; the portal shows only whether
  it is set. Submitting an empty secret field means "keep the stored
  value" — clearing one is an explicit `unset`.
- **A change takes effect immediately.** Config reaches apps as
  environment variables, which container runtimes bake in at start —
  the runtime therefore **recreates the container** rather than
  restarting it. Storage, entry point, port, version, visibility and
  deploy token are untouched; the app is briefly unavailable.
- **No version bump, on either channel.** Configuring is not deploying:
  the production-channel rule "same version is refused" (2.3) governs
  *code*, not settings. An operator must be able to fix a wrong or
  missing value on a production instance without inventing a release.
- **Operator values outrank manifest defaults.** A redeploy — including
  one triggered by a deploy token — keeps what the operator set; a
  default only fills a key that has no value yet.
- **`server_admin` only**, in CLI and portal alike (RFC-0008): config
  values steer the platform's own instance and routinely contain
  credentials. This does not touch an app's *own* in-app settings,
  which stay `admin`/`keyuser` (2.6).
- **Auditable without leaking.** Every change is recorded with
  instance, key name, actor and time — values never appear in any log.

**What `secret: true` promises, and what it does not.** The promise is
about *exposure through the platform's own surfaces*, and it is worth
stating outright rather than leaving to inference — an unstated promise
about credentials is the kind somebody later relies on:

- **It does promise:** the value is never rendered into a page, never
  printed by the CLI, never written to a log or an audit record, and
  never returned by any API the portal offers. It reaches the app only
  as an environment variable. Submitting an empty field keeps the
  stored value, so a secret cannot be cleared by accident.
- **It does not promise encryption at rest.** The value is stored as
  plain text in the instance's own environment file, readable by root
  and by nothing else (mode 0600). Root already owns the platform, so
  this weakens nothing that was not already true — but it means
  "secret" is a UI property, not a cryptographic one.
- **It therefore does not promise anything about backups.** A platform
  backup contains every instance's configuration, and so contains every
  secret. The backup interface says so in as many words
  (`oaap.data.backup`); a backup file is a credential store and must be
  guarded like one.
- **There is no rotation, expiry, or record of last use**, and a value
  is available to the whole app process rather than to the one purpose
  it was issued for.

None of this is a defect for the case config was built for — an app's
own settings on a single-tenant node. It becomes one as soon as an app
needs credentials for *outbound* work against several targets, because
the declared-key model gives it a fixed set of keys and no way to add
one at runtime. RFC-0013 §5 is the first real case; it deliberately
defers the general answer until that case is built, rather than
guessing at the shape.

### 2.9 Store sources (RFC-0012 §2/§4)

A **store source** is a list of apps a node may install from. It is a
node-level fact, maintained by `server_admin`, and it is an **object**,
not a URL with a label:

- **`id`** — stable identity, never the URL. Everything else refers to
  it: the resolution rule of 2.6, the installed instance, the log
  record. Renaming or moving a list MUST NOT change its id.
- **`url`**, **`name`**, **`origin`** (who publishes it, shown to the
  user verbatim), **`enabled`**.
- **`trust`** — `platform` ("von uns", what the installation shipped) ·
  `verified` ("geprüft", curated by us or a selected partner) ·
  `unverified` ("muss bestätigt werden", anything else). An operator
  MAY set `verified` and `unverified`; `platform` is reserved for
  shipped sources, so that "von uns" means the same thing on every
  node. Finer distinctions belong in `origin` as text, not in more
  classes.
- Sources the installation ships additionally carry **`shipped`** and
  **`shipped_url`** — the URL as delivered.

**Shipped sources MUST survive a move.** An update reconciles them: for
each shipped id, if the node's stored URL still equals its
`shipped_url`, both follow the new URL; if they differ, the operator
edited it and the entry is left alone and the difference **reported**.
`enabled`, `name` and `trust` set by the operator are never
overwritten, and a removed shipped source stays removed — the removal
is remembered by id. Without this, the day one of our lists moves every
node in the field strands, visibly only as an empty store.

**Migration is a one-time act, not a rule.** A node upgrading from the
old `{url, name}` form derives id and trust class **once**, from the URL
prefix, and writes the result down. A trust class recomputed from the
URL on every lookup would silently change when a repository is renamed.

### 2.10 Application class and the launchpad tile (RFC-0012 §1.2)

A manifest MAY declare **`app.class`** — what the app *is*, as opposed
to `app.type` (2.2), which says how it is *packaged*:

| value      | meaning                                          |
|------------|--------------------------------------------------|
| `frontend` | has a user interface — the default when absent   |
| `service`  | used by other software, not by a person directly |

- **A `service` gets no launchpad tile by default.** Every instance got
  one until now, which put purely machine-facing apps on the launchpad
  as tiles leading to a page no human wants.
- **The node decides from the manifest it installed, never from a store
  list.** A list is a description; it must not be able to change what a
  stranger's launchpad shows, and the answer has to survive a source
  being disabled, removed or unreachable — and exist at all for an app
  installed straight from Git, which no list mentions. The runtime
  therefore records the class in the instance registry at install time.
  The store list carries `app_class` too, generated from the same
  manifest field (RFC-0012 §1.3), for filtering and labelling.
- **An unknown value counts as `frontend`.** Same rule as everywhere
  else in the format (RFC-0012 §8.1), and the safe direction: a tile
  too many is untidy, a missing tile hides a working app.
- **`app.class` is not a `must_understand` feature** (2.2). A node that
  ignores it shows one tile too many — untidy, not broken — and
  refusing the app instead would be the greater harm.
- **The operator overrides it per instance**, in the registry alongside
  — never inside — the manifest-derived class, exactly like visibility
  (2.7): `auto` (default, follow the class), `on` (always show),
  `off` (never show). Set via
  `sudo oaap app tile <instance> auto|on|off`; the portal offers the
  same control on the instance object page, queued through the
  host-side worker because its registry mount is read-only.
- The override **survives reinstall/redeploy** of the same named
  instance, like the port assignment (2.3) and visibility (2.7). The
  class itself does not: it is re-read from each installed manifest,
  because it describes the app and the app may have changed.
- **A hidden tile is not access control.** It is the same UX-only layer
  as the role and group filter (portal spec 2.2): the instance keeps
  its routes, its roles and its URL, and the gateway keeps enforcing
  them. Hiding an app from a user is what visibility groups (2.7) are
  for.

## 3. Configuration

- Level-1 port range (default 8100–8199, expert-configurable;
  assignments persisted per instance — RFC-0005).
- App data root on the node (default under the platform data dir).
- Per-app expert option: HTTP fallback instead of platform-CA TLS
  (RFC-0005 resolved question 2).

## 4. Security requirements

- Default deny end to end: no app reachable without gateway
  authentication unless a route is explicitly `public` in its manifest.
- Instance isolation: storage, secrets, and **networks** are per
  instance (RFC-0016); a test instance can never read production data,
  and no app can reach another app or the platform's own services
  except through the gateway or an explicitly declared link (2.11).
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
17. **Store-install resolution**: a one-click install for an app id
    that no configured store source lists is refused with no side
    effect; for a listed app, the installed source equals what the
    host-side lookup of the configured sources returned — a request
    carrying a divergent source has no influence (2.6).
18. **Visibility group restriction (2.7)**: an instance set to
    `groups: [finanzen]` is unreachable and its tile hidden for a user
    with the right role but not in `finanzen`; a `server_admin` reaches
    and sees it regardless. Setting visibility back to `all` restores
    the previous (role-only) behavior for everyone.
19. **Visibility survives redeploy**: an instance's visibility setting
    is unchanged after a redeploy that keeps the same instance name
    (2.3, 2.7) — a redeploy must not silently reopen it.
20. **Configure a production instance (2.8)**: a `secret: true` key
    left empty at install can be set afterwards on a **production**
    instance without a version bump; the running app receives the new
    value, and its storage and entry point are unchanged.
21. **Declared keys only**: setting an undeclared key or
    `OAAP_APP_SECRET` is refused with no side effect, through the CLI
    and through the portal.
22. **Secrets stay write-only, operator values stay put**: a secret
    value appears in no page, CLI output or log; an empty secret field
    leaves the stored value intact; and a redeploy of the same
    instance keeps every operator-set value instead of restoring the
    manifest default.

23. **Portal-created instance needs the profile (2.6, RFC-0011)**: on a
    node without `dev`, every portal request to create an instance is
    refused — including one that reaches the host side directly, not
    only the hidden button. After `oaap node add-profile dev`, the same
    request creates a **test**-channel instance; the created instance
    can receive a deploy token (2.5) and appears in the audit trail.
    Removing the profile makes the path refuse again, while instances
    already created keep running.
24. **Named sources stay Git and stay remote**: on a `dev` node, a
    create request naming a local directory or a non-Git source is
    refused with no side effect; a request naming a Git URL that no
    store source lists succeeds — the difference to test 17 is exactly
    the profile.

25. **Trust beats order (2.6)**: with an `unverified` source configured
    **first** and claiming an app id that a `platform` source also
    lists, the one-click install installs the platform source's package.
    Disabling the platform source makes the same click resolve to the
    other one — after a confirmation.
26. **A request cannot introduce a source (2.6)**: an install request
    naming a source id that is not configured is refused with no side
    effect, exactly like an app id no source lists.
27. **Confirmation is required and recorded (2.6)**: installing from an
    `unverified` source without a confirmation is refused; with it, the
    install succeeds and the deploy log names the source, its trust
    class, the app, and who confirmed.
28. **A shipped source survives a move (2.9)**: after the shipped URL
    of a source changes, an update carries the node's entry along and
    says so — unless the operator had edited that URL, in which case the
    entry is left alone and the difference is reported. A shipped source
    the operator removed is **not** re-added by the update.
29. **Manifest version tolerance (2.2)**: a manifest with a higher MINOR
    installs, with a note, and a field the node does not know is
    ignored; a foreign MAJOR is refused; a manifest declaring an
    unknown `must_understand` feature is refused with the feature named.

30. **A service gets no tile (2.10)**: an app whose manifest declares
    `class: service` installs, runs and is reachable at its URL, but
    appears on no launchpad — including the `server_admin`'s. An app
    that declares `frontend`, declares an unknown value, or declares
    nothing at all keeps its tile.
31. **The override outranks the class, and it survives (2.10)**:
    `tile on` gives a `service` instance a tile, `tile off` takes one
    away from a `frontend`, and both are still in force after a
    redeploy of the same instance name. Setting `auto` returns to
    whatever the installed manifest says.
32. **A list cannot move a tile (2.10)**: changing `app_class` in a
    store source, disabling that source, or removing it changes nothing
    about the tiles of instances already installed — the decision came
    from the manifest at install time.

33. **App isolation (2.11, RFC-0016)**: after install, an app container
    is on its own network only, not the platform network; it cannot
    resolve or reach the identity/portal services, while the gateway
    can; the app remains reachable through its entry point. A second
    app installed alongside cannot reach the first.
34. **Gateway link survives a recreate (2.11)**: after the gateway
    container is recreated (as every platform update does), the platform
    reconnects it to every instance network, and all apps are reachable
    again — a node that ran the update never stays in the 502 state.
35. **App-to-app link (2.11)**: a declared link `A → B` lets A reach B
    by name on a dedicated network and does not put A on B's own
    network (B's private siblings stay unreachable); the link survives a
    redeploy of either instance; revoking it, or removing either
    instance, tears the dedicated network down.

## 6. Dependencies

`oaap.core.host`, `oaap.core.gateway`, `oaap.core.identity`,
`oaap.core.portal`

## 7. Maturity

`draft` — first implementation target: run the two real pilot apps
(montage-doku as `native` production+test, BDT as `native` test) through
tests 1–11 on the reference platform. 0.2 target: tests 12–16 with the
pilot CRM's test instance and its AI coding agent as the first real
remote deployer.

## German summary / Deutsche Zusammenfassung (2.6/2.7, v0.2.2)

**Portal-Verwaltung jetzt server_admin:** Install-/Instanzverwaltung
und der Store erfordern jetzt `server_admin` statt `admin`
(RFC-0008) — die App-eigene Konfiguration bleibt `admin`/`keyuser`
wie bisher.

**Sichtbarkeit (2.7, RFC-0007):** Jede installierte Instanz kann eine
zusätzliche Gruppen-Einschränkung tragen (`sudo oaap app visibility
<instanz> groups buero,finanzen` bzw. `all` für zurücksetzen) —
neben, nicht anstelle der Rollen aus dem Manifest. Übersteht einen
Redeploy derselben Instanz. `server_admin` sieht immer alles. Im
Portal auf einer neuen Seite „Instanzen" ebenfalls einstellbar.

## Deutsche Zusammenfassung (2.8, v0.2.3)

**Konfigurationswerte lassen sich jetzt nachträglich setzen** — das
fehlte bisher komplett und ist bei der Produktivsetzung von bdt-hub
aufgefallen: Eine App deklariert einen Schlüssel als vertraulich ohne
Vorgabewert, die Instanz startet also mit leerem Wert, und danach gab
es keinen vorgesehenen Weg mehr, ihn zu füllen. Auf dem Produktiv-Kanal
war es sogar ausweglos, weil dort eine Neuinstallation derselben
Version bewusst abgelehnt wird.

Neu:

```sh
sudo oaap app config list <instanz>              # Schlüssel, Geheimnisse maskiert
sudo oaap app config set <instanz> <key> [wert]  # ohne Wert: versteckte Eingabe
sudo oaap app config unset <instanz> <key>       # zurück auf den Manifest-Vorgabewert
```

Im Portal steht dasselbe auf der Objektseite einer Instanz
(„Instanzen" → Instanz auswählen), nur für `server_admin`.

Die Regeln dahinter, in Kurzform:

- Nur **deklarierte** Schlüssel sind änderbar — was die App nicht in
  ihrem Manifest anmeldet, kann auch niemand in ihren Container
  schleusen. `OAAP_APP_SECRET` gehört der Plattform und bleibt außen vor.
- **Geheimnisse werden nie zurückgezeigt** — weder im Portal noch auf
  der Kommandozeile noch im Protokoll. Ein leer gelassenes Feld heißt
  „behalten", nicht „löschen".
- Nach dem Speichern wird der **Container neu erzeugt** (ein bloßer
  Neustart würde die alten Werte behalten — Umgebungsvariablen werden
  beim Start fest eingebrannt). Kurze Nichtverfügbarkeit, aber Daten,
  Adresse und Version bleiben unverändert.
- **Kein Versions-Bump nötig**, auch nicht auf Produktiv: Konfigurieren
  ist kein Deployment. Der Versionszwang schützt den *Code*, nicht die
  Einstellungen.
- Was der Betreiber gesetzt hat, **überlebt jeden Redeploy** —
  Vorgabewerte füllen nur noch leere Schlüssel.
- Protokolliert wird, *wer wann welchen Schlüssel* geändert hat —
  **nie der Wert**.

## Deutsche Zusammenfassung (2.6, v0.2.4)

**Die offene Frage aus 2.6 ist beantwortet.** Bisher galt überall:
Instanzen anlegen geht nur auf der Kommandozeile, weil eine
Test-Instanz eine Entwicklungshandlung ist. Die Begründung war richtig,
die Regel aber global — und auf einer Maschine, die *zum Entwickeln*
dasteht, damit falsch. Deine Idee mit den Knoten-Profilen (RFC-0011)
verortet sie statt sie zu lockern: Auf einem Knoten mit Profil `dev`
darf das Portal Instanzen anlegen, überall sonst bleibt alles wie
gehabt.

Zwei Grenzen bleiben auch dort:

- **Nur Test-Kanal.** Produktiv installiert weiterhin der Store mit
  einem Klick — dort nennt die Anfrage nur eine App-Kennung und der
  Server sucht die Quelle selbst.
- **Nur echte Git-Quellen.** Ein lokaler Pfad wird abgelehnt: „installiere
  aus dem Repository, das ich Dir nenne" ist etwas anderes als „baue
  mir ein Image aus irgendwelchen Dateien auf dieser Maschine".

**Was Du dafür aufgibst, offen gesagt:** Auf einem `dev`-Knoten kann
ein kompromittiertes Portal Code installieren, dem Du nie zugestimmt
hast. Auf der Werkbank ist das ein guter Tausch, auf einer Maschine mit
Kundendaten ein schlechter. Deshalb ist es eine Entscheidung je Knoten.

**Geprüft wird auf dem Server, nicht im Portal.** Der fehlende Knopf
ist nur die Oberfläche; die Entscheidung fällt dort, wo auch der
Installationsvorgang läuft. Sonst wäre das Profil eine Portal-Einstellung.

## Deutsche Zusammenfassung (2.2/2.6/2.9, v0.2.5)

Diese Fassung arbeitet RFC-0012 in die Spezifikation ein. Drei Dinge,
und alle drei waren vorher stillschweigende Fallen.

**Die Manifest-Version wird nicht mehr auf Gleichheit geprüft (2.2).**
Bisher musste im Manifest exakt `0.1` stehen. An dem Tag, an dem wir
`0.2` veröffentlichen, hätten alle Knoten im Feld solche Apps
abgelehnt — nicht „das neue Feld ignoriert", sondern „Manifest
ungültig". Jetzt gilt: Ein Knoten liest jede Version, deren **erste
Ziffer** er kennt, meldet eine neuere zweite Ziffer und ignoriert, was
er nicht kennt. Streng bleibt das **Schema** — dort soll ein Tippfehler
auffallen. Die Ausnahme heißt `must_understand`: Ein Manifest darf
sagen, welche Eigenschaften ein Leser verstanden haben muss; wer eine
davon nicht kennt, lehnt **diese App** mit klarer Meldung ab, statt
etwas halb Verstandenes zu installieren.

**Bei gleicher App-Kennung gewinnt jetzt das Vertrauen, nicht die
Reihenfolge (2.6).** Bisher gewann die zuerst eingetragene Quelle. Das
war ein Übernahmeweg: bekannte Kennung beanspruchen, weiter oben stehen,
Ein-Klick-Installation kassieren. Dazu zwei Ergänzungen: Das Portal
schickt künftig **Quelle und Kennung** — es darf unter den Quellen
wählen, die Du eingetragen hast, aber keine eigene mitbringen —, und
eine installierte Instanz **merkt sich ihre Quelle**, damit sie später
nicht stillschweigend aus einer anderen Liste bedient wird. Aus einer
ungeprüften Quelle zu installieren, kostet eine **Bestätigung**, und die
steht danach im Protokoll: wer hat wann welche Quelle für welche App
akzeptiert.

**Eine Quelle ist ein Objekt und übersteht einen Umzug (2.9).** Sie hat
eine feste Kennung (nie die URL), einen Namen, eine Herkunft im
Klartext, an/aus und eine Vertrauensklasse: „von uns" / „geprüft" /
„muss bestätigt werden". „Von uns" bleibt dem vorbehalten, was die
Installation mitbringt — sonst hieße es auf jedem Knoten etwas anderes.
Mitgelieferte Quellen tragen zusätzlich die ausgelieferte URL; beim
Update gleicht der Knoten ab: unangetastete URL zieht mit, geänderte
bleibt stehen und der Unterschied wird gemeldet, entfernt bleibt
entfernt. **Das musste vor dem Repo-Umzug existieren, nicht danach** —
sonst strandet jeder bestehende Knoten, sichtbar nur an einem leeren
Store. Bestehende Knoten bekommen Kennung und Klasse **einmalig** aus
dem URL-Präfix; eine bei jeder Auflösung neu berechnete Klasse würde
sich beim nächsten Repo-Namen still ändern.

## Deutsche Zusammenfassung (2.2/2.10, v0.2.6)

**Eine App darf jetzt sagen, dass sie keine Oberfläche hat (2.10).** Im
Manifest steht dafür `app.class`: `frontend` — hat eine Bedienoberfläche,
das ist der Normalfall und gilt auch, wenn nichts dasteht — oder
`service` — wird von anderer Software benutzt, nicht von einem Menschen.
Das ist etwas anderes als `app.type` (`native`/`image`/`wrapped`): der
Typ sagt, wie die App **verpackt** ist, die Klasse sagt, was sie **ist**.

**Ein `service` bekommt keine Kachel im Launchpad.** Bisher bekam jede
Instanz eine, auch eine reine Maschinenschnittstelle wie der bdt-hub —
die Kachel führte dann auf eine Seite, die kein Mensch sehen will.

**Die Entscheidung fällt am Manifest, nicht an einer Store-Liste.** Das
ist der wichtige Teil. Die Liste beschreibt eine App; sie darf nicht
bestimmen, was auf einem fremden Launchpad erscheint. Außerdem muss die
Antwort auch dann noch stimmen, wenn die Quelle abgeschaltet, entfernt
oder gerade nicht erreichbar ist — und es muss sie überhaupt geben für
eine App, die direkt aus Git installiert wurde und in keiner Liste
steht. Der Knoten merkt sich die Klasse deshalb bei der Installation.
Die Liste führt `app_class` weiterhin, erzeugt aus demselben
Manifest-Feld, zum Filtern und Beschriften.

**Du behältst das letzte Wort, je Instanz.** `sudo oaap app tile <name>
auto|on|off` — `auto` folgt der App, `on` zeigt die Kachel immer, `off`
nie. Im Portal steht dasselbe auf der Instanzseite. Diese Einstellung
übersteht ein erneutes Deployment, die Klasse selbst nicht: die wird bei
jeder Installation neu aus dem Manifest gelesen, denn sie beschreibt die
App, und die kann sich ändern.

**Eine versteckte Kachel ist keine Zugriffskontrolle.** Sie ist genauso
reine Anzeige wie der Rollen- und Gruppenfilter: Route, Rollen und URL
der Instanz bleiben unverändert, und das Gateway prüft weiter wie
bisher. Wer eine App wirklich vor jemandem verbergen will, nimmt
Sichtbarkeitsgruppen (2.7).

**Warum das kein `must_understand` ist:** Ein älterer Knoten, der das
Feld nicht kennt, zeigt eine Kachel zu viel. Das ist unschön, aber
nichts ist kaputt — die App abzulehnen wäre der größere Schaden. Genau
dafür ist die Versionstoleranz aus 2.2 gebaut, und `app.class` ist ihr
erster echter Anwendungsfall.

## Deutsche Zusammenfassung (2.8, v0.2.7)

**Was `secret: true` verspricht — und was nicht.** Bisher stand das
Versprechen nur zwischen den Zeilen. Jetzt steht es da, denn ein
unausgesprochenes Versprechen über Zugangsdaten ist genau die Sorte,
auf die sich später jemand verlässt.

**Zugesagt ist:** Der Wert erscheint auf keiner Seite, in keiner
CLI-Ausgabe, in keinem Protokoll und in keiner Schnittstelle, die das
Portal anbietet. Er erreicht die App ausschließlich als
Umgebungsvariable. Ein leer abgeschicktes Feld behält den gespeicherten
Wert — versehentlich löschen kann man ein Geheimnis also nicht.

**Nicht zugesagt ist Verschlüsselung.** Der Wert liegt im Klartext in
der Umgebungsdatei der Instanz, lesbar für `root` und sonst niemanden
(Rechte 0600). Root gehört die Plattform ohnehin, es wird also nichts
schwächer — aber „geheim" ist eine Eigenschaft der Oberfläche, keine
kryptografische.

**Und damit ist auch über Backups nichts zugesagt.** Ein Backup enthält
die Konfiguration aller Instanzen und damit alle Geheimnisse. Die
Backup-Schnittstelle sagt das ausdrücklich: Die Datei ist wie ein
Generalschlüssel zu behandeln.

**Es fehlen** Rotation, Ablauf und ein Nachweis der letzten Verwendung;
außerdem steht ein Wert dem ganzen App-Prozess offen, nicht nur dem
Zweck, für den er ausgestellt wurde.

Für den Fall, für den die Konfiguration gebaut wurde — die eigenen
Einstellungen einer App auf einem Einzelknoten —, ist davon nichts ein
Mangel. Zum Mangel wird es, sobald eine App Zugangsdaten für Arbeit
**nach außen** gegen mehrere Ziele braucht: Die Schlüssel sind im
Manifest festgelegt, es gibt also keinen Weg, zur Laufzeit einen
weiteren hinzuzufügen. Der Store Editor ist der erste echte Fall
(RFC-0013 §5) — und die allgemeine Antwort wird bewusst so lange
aufgeschoben, bis dieser Fall gebaut ist, statt sie zu erraten.

## Deutsche Zusammenfassung (App-Isolation und -Links, v0.2.8, RFC-0016)

Jede App-Instanz läuft ab jetzt in **ihrem eigenen Netz**, getrennt von
allen anderen Apps und von den Plattformdiensten (Abschnitt 2.11). Nur
das **Gateway** tritt jedem App-Netz bei — eine App erreicht das Gateway
und ihre eigenen Container, aber weder eine andere App noch Identity
oder Portal. Damit ist die interne API von Identity aus einer App
**strukturell** unerreichbar (die Eskalation aus RFC-0015 A4 ist nicht
mehr nur per Schlüssel abgewiesen, sondern gar nicht mehr erreichbar;
der Schlüssel aus `oaap.core.identity` 4.3 bleibt als zweite Schicht).

Weil ein Plattform-Update das Gateway neu erzeugt und dabei die
manuellen Netz-Verbindungen verliert, verbindet die Plattform das
Gateway nach dem Neustart der Kerndienste **wieder mit jedem App-Netz** —
sonst wären die Apps danach nicht erreichbar (502).

**App-zu-App-Verbindungen** sind der einzige Weg, auf dem eine App eine
andere erreicht, und sie sind eine ausdrückliche Betreiber-Entscheidung,
nie im Manifest: Ein Link `A → B` steht in der Registry (übersteht
Redeploy), wird als **eigenes Netz** umgesetzt, dem beide Primär-Container
beitreten (A wird **nicht** in Bs eigenes Netz gehängt — Bs interne
Container bleiben privat), und ist widerrufbar. Beim Entfernen einer
Instanz werden ihr Netz und alle Links, die sie betrafen, abgeräumt.
Bestehende Apps wandern beim `oaap update` automatisch auf eigene Netze.
