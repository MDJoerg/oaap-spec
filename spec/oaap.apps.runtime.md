# oaap.apps.runtime — App Runtime

- **ID:** `oaap.apps.runtime`
- **Version:** 0.2.4
- **Maturity:** draft (0.2 adds remote deployment via deploy tokens;
  0.2.1 adds the one-click store install in 2.6 with test 17; 0.2.2
  adds instance visibility in 2.7 and moves platform-level portal
  operations from `admin` to `server_admin`, per RFC-0007/RFC-0008;
  0.2.3 spells out instance **configuration** in 2.8 — promised since
  2.3/2.4.3 but never described in interface terms, and missing from
  the reference implementation until it blocked a real production
  rollout; 0.2.4 answers the open question in 2.6 — instances MAY be
  created from the portal, on a node whose profile says it is a
  workbench, per RFC-0011)
- **Based on:** RFC-0001 (capability model), RFC-0002 (roles/gateway),
  RFC-0003 (placement), RFC-0004 (manifest/app types), RFC-0005
  (addressing), RFC-0007 (visibility groups), RFC-0008 (server_admin),
  RFC-0011 (node profiles);
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

- The portal request names **only the app id** (and the store source
  it was seen in). It carries no package source, no manifest, no
  version — nothing installable.
- The privileged host side resolves the app id **against the
  platform's configured store sources** (the same list the store page
  reads) and installs from what *that* lookup returns. An app id that
  no configured source lists is refused. A compromised portal can
  therefore at worst install apps the server_admin already chose to
  trust by configuring their source.
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
