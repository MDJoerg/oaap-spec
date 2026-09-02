# oaap.core.portal — Web Portal

- **ID:** `oaap.core.portal`
- **Version:** 0.3.12
- **Maturity:** draft (0.3.12 opens the store catalogue to a
  `tenant_admin` — RFC-0022 §4 gives them "install and remove app
  instances of their tenant", and a catalogue they cannot open makes
  that right unusable, while the SOURCE list stays the node operator's;
  and it requires the generated instance address to carry the tenant
  label, after a portal that left it out linked tiles to a host that
  answers nowhere;
  0.3.11 makes the published-names watchdog
  resolve dual-stack (IPv4 **and** IPv6): a name that resolves only over
  IPv6 — a Fritzbox rebind-protected CNAME seen from inside the LAN is
  the real case — no longer reads as a false "does not resolve" or
  "points elsewhere"; RFC-0009 follow-up;
  0.3.10 adds the direct-port reachability watchdog
  to the health page — the sibling of the published-names watchdog,
  RFC-0015 decision Q4: a self-test that confirms a granted port answers
  at the node's public address, TCP by connecting and UDP by STUN, and
  reports "not confirmed from here" rather than a false "broken";
  0.3.9 makes the launchpad follow the app class —
  a background service gets no tile, and a node where that hides
  something says so rather than showing an empty page; 0.3.8 adds the
  deploy worker to the health page,
  after a real node accepted portal actions and silently processed
  none of them; 0.3.7 specified the Store as a catalogue with an object
  page and added source management, per RFC-0012 §6/§7 — the last step
  of `portal-statt-cli.md`)
- **Based on:** RFC-0001, RFC-0002, RFC-0003, RFC-0005, RFC-0007,
  RFC-0008, RFC-0009, RFC-0010, RFC-0011, RFC-0012, RFC-0022

## 1. Purpose

The portal is the web UI where **everything** on the platform is
administered — there is no other administration surface for end users
(technicians and service partners additionally have the node CLI, see
`oaap.core.host` 2.3). It serves the first-run wizard during bootstrap
and afterwards provides the launchpad, user management, instance
visibility, and platform health, scoped by the standard roles
(RFC-0002) and, for the launchpad, visibility groups (RFC-0007).

The reference UI follows the OAAP design guidelines
(`oaap-design/docs/design-guidelines.md`): brand colors and hexagon
mark, German as the reference UI language, floorplans (list report /
object page / dialog page), no external resources at runtime
(offline-first).

## 2. Interface

### 2.1 First-run wizard

Reachable only while no user exists, protected by the one-time setup
token (`oaap.core.host` 2.2); creates the first admin via identity's
bootstrap operation and is permanently disabled afterwards.

The wizard MAY additionally ask **what the node is for** and record the
node's profiles (`oaap.core.host` 2.5, RFC-0011). This is the only
place where the portal writes a profile, and the write MUST be
authorised by the same setup token and refused once the first admin
exists — the privileged side, not the portal, checks both. A profile
the wizard cannot apply MUST NOT be silently dropped: the wizard says
so and does not create the admin, so the operator can simply send the
form again.

### 2.2 Launchpad

- Installed app instances appear as tiles with name, description,
  version, and channel badge; the tile links to the instance's
  platform-generated URL. Apps open through the gateway, never embedded.
- **Tile targets depend on where the caller is, not on which name they
  used.** LAN listener ports (RFC-0005 level 1) are reachable only from
  inside; from outside just the platform's HTTP(S) ports are forwarded.
  The portal therefore offers port URLs only when the request host is
  itself a LAN address (an IP literal or a single-label/`.local`-style
  name) and public URLs otherwise — an instance's own hostname
  (RFC-0009) when it has one, else its subdomain of the node. Deciding
  this by "does the host equal the node's external name" is wrong: a
  platform can be entered under any public name that resolves to it,
  and every such visitor would get LAN links that are dead from
  outside.
- Tiles are **role- and group-filtered** (RFC-0007): a user sees an
  instance only if (a) their roles intersect the instance's route
  roles, AND (b) — when the instance carries a visibility restriction
  (`oaap.apps.runtime` 2.7) — their groups intersect it, unless they
  hold `server_admin` (RFC-0008), which bypasses the group check only.
  There is **no role bypass** any more: the filter mirrors the
  gateway's `/verify` exactly (`oaap.core.identity` 2.3), which has
  never had one — a stray "admin sees every tile" UX-only exception
  predating RFC-0008 was removed as part of this version, since it
  could show a tile that then 403'd on click. The filter itself
  remains UX only — the gateway enforces both checks on every request
  regardless of what the portal shows.
- **Not every instance has a tile.** An app whose manifest declares
  itself a background `service` gets none by default, and an operator
  can force a tile on or off per instance
  (`oaap.apps.runtime` 2.10). Where this leads to instances the caller
  would otherwise see, a `server_admin` MUST be told that they exist
  and where to change it — an empty launchpad on a node full of
  running apps is otherwise indistinguishable from a broken one.
- The caller's groups are **not** a header (no `X-OAAP-Groups` exists,
  RFC-0007) — the portal looks them up from identity by the verified
  username, same trust boundary as roles.
- Data source is the platform's instance registry, maintained by the
  app runtime (`oaap.apps.runtime`); the portal reads it, it never
  writes it.
- Later stages (backlog, RFC-0005/portal outline): tile images,
  grouping, operator-configurable appearance, multiple designs per
  user/group.

### 2.3 User management

`server_admin`-only UI (RFC-0008 — this operates on the server itself)
over the operations of `oaap.core.identity` 2.4/2.6 (list, create,
update, set password; deactivate instead of delete; groups field
alongside roles; last-server_admin protection surfaces as an error
message). Layout follows the floorplans: a read-only list report
navigating to one object page per user; create is its own object
page; saves use Post/Redirect/Get. Granting `server_admin` to someone
is not separately gated — it is enforced structurally, since only an
existing `server_admin` can reach this UI at all (RFC-0008 decision:
only server_admin grants server_admin).

### 2.4 Instance visibility (RFC-0007)

`server_admin`-only UI over `oaap.apps.runtime` 2.7's `visibility`
field: a list report of installed instances (name, app, channel,
current visibility) navigating to an object page per instance (radio
"all" / "groups" + a free-text group field). Since the portal's
registry mount is read-only, saves are queued to the same host-side
worker that already applies one-click store installs (2.6) — the
portal never writes the registry or gateway config directly.

The same object page also carries the instance's **configuration**
(`oaap.apps.runtime` 2.8): one field per key the app's manifest
declares, `secret: true` entries masked — shown as "set" or "not set",
never prefilled with the stored value, and an empty submission keeps
what is stored. Saving goes through the same worker (it has to
recreate the container) and reports the outcome on the page. Also
`server_admin` only: these values steer the platform's own instance
and routinely contain credentials.

The object page carries the remaining per-instance operations as
further cards, so an operator never has to reach for the CLI to put an
app into service:

- **Own public hostname** (`oaap.apps.runtime` / RFC-0009), with the
  automatic node address shown alongside so the difference is visible.
  That automatic address is the name the **gateway** serves the
  instance under, tenant label included: `<instance>.<node>` in the
  default tenant, `<instance>.<label>.<node>` in every other one
  (`oaap.core.tenant` 2.4). The portal MUST compute it that way
  everywhere it prints or links it — the object page, the launchpad
  tile, the deploy log. A portal that leaves the label out names a host
  that resolves into the node's catch-all and answers for nothing,
  which is worse than naming no address at all. An instance whose
  tenant this node does not have therefore gets **no** automatic
  address, the same fail-closed answer the gateway gives.
- **Public-route throttling** (RFC-0010) — shown **only** when the app
  actually declares a `public` route, because on every other instance
  the setting would have no effect and would only mislead. The card
  states plainly that it is a volume brake and not a credential
  control.
- **Deploy token** (`oaap.apps.runtime` 2.5) — shown only for test
  instances, since production instances never carry one. The page
  reports whether a token exists and when it was issued, never its
  value.

Two rules for the token, both security-relevant:

1. The **portal generates** the token and hands the host side only its
   digest. The readable value therefore never reaches the filesystem —
   not the queue, not the token store. This grants the portal no new
   power: a deploy token authorizes exactly the redeploy the portal can
   already trigger.
2. The token is rendered **in the response to the creating request**,
   deliberately not via Post/Redirect/Get. A redirect would have to
   carry the value in a URL, and the gateway logs full request URIs
   including their query string.

**Creating an instance** appears in the list report **only on a node
whose profile allows it** (`oaap.core.host` 2.5, `oaap.apps.runtime`
2.6): a dialog page choosing either an app from the configured store
sources or a Git URL that no list carries yet, plus an optional
instance name. The page states why it exists — the node's profile — so
the difference between two nodes is never a mystery. A hidden button is
not the protection: the privileged side refuses the same request on a
node without the profile.

Finally, **removing an instance** — the only destructive control in the
portal. It therefore differs from every other card:

- the operator must **type the instance name** to confirm, so no single
  click can destroy anything;
- keeping the storage is the **preselected** option, deleting it is a
  separate, explicit choice;
- the host side re-checks the typed name against the instance it is
  about to remove, so a misdirected or replayed request cannot take
  down a different app than the one on screen;
- afterwards the caller lands on the list, since the page they came
  from no longer exists.

### 2.5 Health

- Visible for roles `server_admin` and `partner` (service-partner
  scenario) — moved from `admin` in v0.3.0 (RFC-0008: this is
  server-internal information, not app-facing).
- **Node values**: platform version, the node's **profiles**
  (`oaap.core.host` 2.5 — a node that behaves differently from its
  neighbour must say so, including where to change it), uptime, CPU
  load, memory, free disk of the platform data filesystem (with a
  warning threshold matching the installer's minimum free space).
- **Core services**: liveness of identity and portal plus a
  **full-chain check** through the gateway (gateway → identity),
  so a broken proxy path is visible even when every container runs.
- **Deploy worker**: whether anything is actually processing the write
  queue. Every change the portal makes to the node — install, remove,
  visibility, configuration, deploy tokens, store sources — is queued
  for a host-side worker, so a worker that has stopped turns the whole
  portal into a surface that accepts instructions and carries out none
  of them. The page MUST report this, and it MUST do so from the
  **symptom** (requests waiting far longer than any of them takes),
  not from the health of one particular mechanism: the implementation
  runs in a container and cannot ask the host's service manager, and a
  symptom-based check catches a stopped worker, a host without a
  service manager, and a worker that dies on every request alike. An
  alarm MUST name a way back.
- **App instances**: per instance, the manifest's health endpoint is
  checked over the internal network (`oaap.apps.runtime` provides
  service port and health path in the registry). Instances registered
  before that data existed show "unknown" with a remediation hint.
- **Published names** (RFC-0009 decision 2): for every name this node
  hands out — its external hostname and every instance's own hostname —
  whether that name still resolves to this node's public address. A
  name pointing elsewhere is the DuckDNS failure mode: the node is off
  the internet and nothing says so. Rules, because this is the one
  place the platform talks to a third party:
  - It runs **only when the node actually publishes a name**. A
    LAN-only platform makes no outside request at all, and the
    installer's offline promise stands.
  - The page MUST name **which** outside service was asked and what it
    answered. A silent call to a third party would be telemetry by
    another name.
  - The result MAY be cached; the page states when it was last checked.
  - **Behind an edge node** (RFC-0006) the published names resolve to
    the *edge's* public address, which this node cannot determine. The
    implementation MUST then report only whether the names resolve at
    all, and say why it can say no more — a guess would be worse than
    an honest "unknown".
  - **Dual-stack resolution.** A name is resolved over IPv4 **and**
    IPv6. It counts as "does not resolve" only when neither an A nor a
    AAAA record answers. A name that resolves only over IPv6 — a
    rebind-protected CNAME seen from inside the LAN is the real case —
    MUST NOT read as unresolved, and MUST NOT be flagged "points
    elsewhere" against the IPv4 public address; with nothing comparable
    it reads as an honest "not comparable". (The public address is
    discovered as IPv4 today; a v6-only name cannot be compared against
    it, and saying so beats a false alarm.)
- **Direct ports** (RFC-0015 decision Q4): for every granted direct
  endpoint (`oaap app endpoint allow`), whether the published port is
  actually reachable at this node's public address. A forgotten router
  forward is otherwise indistinguishable from a broken app. This is the
  sibling of *Published names* and shares its mechanism — one asks
  whether the name still points here, this whether the port still
  reaches here — and its third-party rules apply unchanged (runs only
  when a port is granted, names the outside service used for the public
  address, MAY be cached, states when last checked, reports "unknown"
  behind an edge). Two limits are stated on the page rather than hidden:
  - **Stage 1 is a self-test from the node.** A router that does not
    hairpin (loop a connection to its own public address back inside)
    makes a working forward look unreachable from here, so a failed
    probe MUST be reported as a grey "not confirmed from here", never a
    red "broken". Only a **success** is asserted, because a success
    cannot be faked. The stage-2 reflector (an outside vantage) removes
    this caveat and is a later stage.
  - **UDP** cannot be confirmed by a bare datagram. The check sends a
    STUN binding request (RFC 5389), which every WebRTC media server
    answers by standard — a real proof for the very endpoints UDP
    carries; its absence is the same grey "not confirmed".
- **Braked requests** (RFC-0010 decision 2): per instance with a
  `public` route, how often the volume brake rejected a request in the
  last 24 hours. Without this a `429` leaves nothing but a line in an
  access log nobody reads. The count MUST be complete across all worker
  processes of the throttling service — a number that silently omits
  what another worker holds is worse than none. The page repeats that
  this is a volume brake, not access control.
- Whole-landscape health (controller + workers, RFC-0003) is a later
  stage of this section; node-local values come first.

### 2.6 Store (RFC-0012 §6/§7)

Two rights, deliberately separated:

- the **catalogue and its object page, and installing from them**,
  are open to `server_admin` **and** `tenant_admin`. RFC-0022 §4
  gives a tenant administrator "install and remove app instances of
  their tenant"; a catalogue they may not open makes that right
  unusable. The install lands in **their** tenant, because the host
  derives the acting tenant from the caller's own record
  (`oaap.core.tenant` 2.3 rule 3) and never from the request.
- the **source list** stays with the node operator: `server_admin`
  only. Where packages may come from is a node decision, and a
  tenant that could add a source could install anything.

Everything a `tenant_admin` reads here is read through the boundary:
an app installed in another tenant MUST NOT read as "installed", and
a running install of another tenant's instance MUST NOT be reported.
A name already taken elsewhere on the node is still refused as
**taken** (`oaap.core.tenant` 2.4), not as "unknown" -- the collision
is the fact, the owner is not.

Three floorplans: the catalogue, an object page per app, and the
sources.

**Catalogue (list report).** All enabled sources are shown as **one**
catalogue, with the source and its trust class on **every** entry — not
one block per source. The reason is the resolution rule: when two lists
carry the same app id, only one of them can be installed
(`oaap.apps.runtime` 2.6), so showing both would offer a choice the host
would then overrule. The runners-up are named on the object page
instead.

- **Filters:** categories, application class, audience, maturity,
  status, trust class, source, licence, installed or not, and fit with
  the node's profiles. **Search** additionally covers tags, name,
  summary and description.
- **Three defaults, each reversible with one click.** Apps whose
  `profiles` do not match this node are **filtered, not hidden**; so are
  `archived` entries. `audience: expert` is **not** filtered — it is
  shown, marked, and costs a confirmation at install. Hiding it would
  turn a hint into a gate through the back door.
- **An unknown vocabulary value MUST NOT be dropped or refused.** It is
  shown verbatim and sorted under "Sonstiges", or every extension of the
  vocabulary would strand exactly the nodes that have not updated yet.
- **Icons and screenshots are loaded only from the list's own
  location.** An entry naming an absolute URL has that image dropped,
  not rendered: otherwise every node opening this page would contact
  hosts nobody chose and announce its existence and address for the sake
  of a thumbnail (RFC-0012 §1.1).

**Object page per app.** Icon, summary, long description, screenshots,
version with release date, links, licence, roles, categories, tags — and
the facts an operator needs before installing: which source it comes
from and in which class, which other lists also carry it, and whether
the package is pinned. The install button lives here; a `new` badge is
**computed** from the release date and never stored.

**Sources (list report).** `server_admin` only -- see above. They add,
rename, enable,
disables, removes a source and sets its trust class. Two rules:
`platform` is not settable by an operator, and raising a source to
`verified` MUST say what it costs — apps from it then install without a
confirmation and outrank unverified sources. Every change goes through
the privileged host side, which re-checks all of it: the portal's
registry mount is read-only, and the spool is data, not trust.

Managing sources MAY live in the portal — unlike setting a node profile,
which stayed on the machine (RFC-0011) — because adding a source is
visible, reversible, and by itself installs nothing. It grants the
portal no reach the `server_admin` did not grant.

### 2.7 Reserved navigation

`Einstellungen` (settings), `Store` (app store), `Studio` are reserved
navigation points (design guidelines section 5); implementations MUST
NOT use these routes for other purposes.

## 3. Configuration

None beyond the platform version passed at start. Appearance
configuration is a later stage (2.2).

## 4. Security requirements

1. The portal never authenticates users itself; it trusts the
   gateway's verified identity headers (RFC-0002, deployment-contract
   guarantee 1).
2. Every management surface re-checks the required role server-side —
   the navigation filter is UX only. `server_admin` for instance
   visibility and store **sources**; `server_admin` or `tenant_admin`
   for user management, the instance list and the store **catalogue**
   (2.6, RFC-0022 §4); `server_admin`/`partner` for health. A new
   route under an already-guarded area MUST call the same guard: the
   failure mode this is written against is a route added later and
   left open.
3. The portal talks to identity's internal API only over the internal
   container network; that API is never exposed through the gateway.
4. Health checks run from the portal over the internal network and
   never expose internal addresses to the browser beyond status text.
5. The portal's `/apps-registry` mount is **read-only** — instance
   visibility changes (2.4) and store installs (`oaap.apps.runtime`
   2.6) are only ever queued to the host-side worker, never applied
   in-process, so a compromised portal container cannot itself rewrite
   the registry or gateway configuration.

## 5. Conformance tests (described)

1. **Wizard lifecycle**: wizard works exactly once (see
   `oaap.core.host` tests 2–4).
2. **Role- and group-filtered launchpad**: a user whose roles do not
   intersect an instance's route roles does not see its tile; a user
   whose roles match but whose groups do not intersect a set
   visibility restriction also does not see it; a `server_admin` sees
   all tiles regardless of visibility (but still only tiles their role
   matches — RFC-0008 gives no role bypass); the gateway still blocks
   direct access regardless of tiles.
3. **Tile targets**: each tile links to the instance's generated URL
   and the app opens through the gateway (login enforced).
4. **User management floorplans**: the user list is read-only with
   navigation to an object page; create/update/set-password work and
   respond with Post/Redirect/Get; identity errors (e.g.
   last-server_admin protection) surface as messages.
5. **User management authorization**: without the `server_admin` role,
   the user-management routes return 403 and the navigation hides the
   entry — holding only `admin` is not sufficient.
6. **Health authorization**: health is reachable for `server_admin`
   and `partner`, 403 for everyone else (including a user holding only
   `admin`).
7. **Health signal**: stopping an app container (or a core service)
   changes its health row on the next page load; the full-chain
   gateway check fails when the gateway cannot reach identity.
8. **Node values**: the health page shows version, uptime, load,
   memory, and disk of the platform data filesystem.
9. **Offline**: all portal pages render without any request leaving
   the platform (no external fonts, scripts, images).
10. **Instance visibility floorplans**: the instances list is
    read-only with navigation to an object page; setting a group
    restriction and setting it back to "all" both take effect (tile
    and gateway) without requiring `oaap update`.
11. **Instance visibility authorization**: without `server_admin` or
    `tenant_admin`, `/instances` routes return 403 and the navigation
    hides the entry; a `tenant_admin` reaches the list and sees only
    their own tenant's instances, and an instance of another tenant
    answers 404 rather than 403 (`oaap.core.tenant` 2.3 rule 2).
12. **Create is profile-bound**: on a node without the `dev` profile,
    the create entry point is absent AND the route returns 403; after
    the profile is set on the machine, the page appears and creates a
    test instance; the health page shows the profile in both states.
13. **Wizard profile question**: ticking the node-profile box records
    the profile, and the same request without a valid setup token
    records nothing; after the first admin exists, a repeated request
    changes no profile.
14. **Published names**: a node with no published name shows no such
    section and makes **no outside request**; with a published name,
    a name resolving to this node's public address reads "points
    here", one resolving elsewhere is flagged, and one that does not
    resolve is flagged differently; behind an edge node the section
    reports resolution only and states why.
15. **Direct ports**: a node with no granted endpoint shows no such
    section and makes **no outside request**; with a granted endpoint,
    a forwarded and hairpinning port reads "reachable", while a port
    published on the host but not forwarded reads "not confirmed from
    here" — never "broken" (no false red, and above all no false green
    for a published-but-not-forwarded port); a granted UDP endpoint is
    probed by STUN; behind an edge node the section reports "not
    checkable" and states why.
16. **Braked requests**: after the brake has rejected N requests for an
    instance, the health page reports exactly N — including requests
    braked by a different worker process of the throttling service; an
    instance without a `public` route never appears.
17. **Deploy worker visible**: with the queue empty the health page
    reports the worker as healthy; with the worker stopped and a
    request queued long enough, the page reports an alarm that names a
    way back — and it does so **without** asking the host's service
    manager. Then: a burst of portal actions in immediate succession
    (as fast as a user can click) leaves every one of them applied and
    the worker still running.
18. **Tiles follow the app class**: an instance of a `service` app
    appears on no launchpad, including the `server_admin`'s, while the
    instance page still lists it and states why; switching that
    instance's tile to `on` makes it appear and back to `auto` makes it
    disappear again, without `oaap update`. On a node where this hides
    something, the launchpad tells a `server_admin` how many and where
    to look.
19. **The generated address carries the tenant label**: on a node with
    a second tenant, that tenant's instance is shown and linked as
    `<instance>.<label>.<node>` on the object page, on the launchpad
    tile and in the deploy log, and the name matches the site the
    gateway actually wrote — compare the two, do not assert a
    string. An instance of the default tenant keeps `<instance>.<node>`.
    An instance naming a tenant the node does not have gets no
    automatic address at all.
20. **Store authorization**: a `tenant_admin` reaches the catalogue and
    an app's object page and can install from them, and the new
    instance lands in their tenant; the sources page and every source
    change answers 403 for them and the button is not rendered; an app
    installed in another tenant does not read as "installed"; and
    installing under a name that tenant does not hold is refused as
    **taken**, without naming the tenant that holds it.

## 6. Dependencies

`oaap.core.gateway`, `oaap.core.identity`; reads the instance registry
of `oaap.apps.runtime`.

## 7. Maturity

`draft` — v0.2 specifies launchpad, user management, and health as
implemented by the reference (2026-08-04); v0.3.0 moves
platform-level management from `admin` to `server_admin` and adds
instance visibility (2.4), per RFC-0007/RFC-0008 (2026-08-07). Open:
appearance configuration, landscape health, settings/studio areas.

## German summary / Deutsche Zusammenfassung (v0.3.0)

**server_admin statt admin:** Benutzerverwaltung, Store und (neu)
Instanzen-Sichtbarkeit erfordern jetzt `server_admin` statt `admin`
(RFC-0008) — reine App-Rolle `admin` reicht dafür nicht mehr.
Gesundheit ebenso (`server_admin`/`partner`).

**Neue Seite „Instanzen" (2.4, RFC-0007):** Listenbericht aller
installierten Instanzen mit Objektseite je Instanz — „Alle sichtbar"
oder „Nur für Gruppen: ...". Da die Registry im Portal-Container
nur lesbar eingebunden ist, läuft das Speichern wie die
Ein-Klick-Installation über den Host-Worker, nie direkt.

**Launchpad:** zeigt Kacheln jetzt zusätzlich gruppengefiltert;
`server_admin` sieht immer alles, `admin` hat dabei **keinen**
Sonderstatus mehr (die alte, nur im Portal wirksame
„admin sieht alles"-Ausnahme entfiel — sie konnte eine Kachel zeigen,
die beim Klick trotzdem 403 lieferte).

## Deutsche Zusammenfassung (v0.3.1)

**Konfiguration auf der Instanz-Objektseite (2.4):** Dieselbe Seite
zeigt jetzt zusätzlich die Konfigurationswerte, die die App in ihrem
Manifest anmeldet. Vertrauliche Werte werden nie zurückgezeigt — das
Feld meldet nur „gesetzt" oder „noch nicht gesetzt", und wer es leer
lässt, behält den gespeicherten Wert. Gespeichert wird über denselben
Host-Worker wie die Sichtbarkeit, weil dafür der App-Container neu
erzeugt werden muss. Nur für `server_admin`.

**Kachel-Ziele (2.2), Fehlerbehebung:** Das Portal entschied bisher
anhand von „ist der aufgerufene Name genau der externe Knotenname?",
ob eine Kachel auf die öffentliche Adresse oder auf den LAN-Port
zeigt. Wer die Plattform unter irgendeinem anderen öffentlichen Namen
betrat (eigene Instanz-Adresse nach RFC-0009, ein CNAME des
Betreibers), bekam LAN-Port-Adressen — von außen tot, weil nur 80/443
weitergeleitet werden. Jetzt wird die umgekehrte Frage gestellt: Sieht
der Name nach einer LAN-Adresse aus (IP oder einteiliger Name)? Nur
dann Port-Adressen, sonst öffentliche — bevorzugt die eigene Adresse
der Instanz.

## Deutsche Zusammenfassung (v0.3.3)

**Die Instanz-Objektseite ist jetzt der Ort, an dem eine App in Betrieb
genommen und wieder abgeräumt wird** — ohne Kommandozeile: eigene öffentliche Adresse,
Drosselung öffentlicher Routen (nur sichtbar, wenn die App überhaupt
eine öffentliche Route hat) und **Deploy-Token** für Test-Instanzen.

Zwei Regeln beim Token sind wichtig: Das Portal **erzeugt** das Token
selbst und gibt der Serverseite nur dessen Prüfsumme — der lesbare Wert
landet damit nirgends auf der Platte. Und er wird **direkt in der
Antwort** angezeigt, bewusst nicht über eine Weiterleitung: Die müsste
den Wert in eine Adresse schreiben, und das Gateway protokolliert
Adressen vollständig.

**Entfernen** ist der einzige zerstörerische Handgriff und deshalb
anders gebaut: Der Instanzname muss **eingetippt** werden, „Daten
behalten" ist vorausgewählt, und die Serverseite prüft den eingetippten
Namen ein zweites Mal gegen die Instanz, die sie gerade abräumen soll.

## Deutsche Zusammenfassung (v0.3.5)

**Anlegen im Portal — aber nur dort, wo es hingehört.** Auf einem
Knoten mit Profil `dev` (RFC-0011) steht in der Instanzen-Liste jetzt
„Test-Instanz anlegen": entweder eine App aus den eingerichteten
Store-Quellen oder ein Git-Repository, das noch in keiner Liste steht.
Auf jedem anderen Knoten fehlt der Knopf — und die Adresse antwortet
dort auch dann mit einer Absage, wenn man sie direkt aufruft. Der
fehlende Knopf ist nie der Schutz, sondern nur die Höflichkeit.

**Die Gesundheitsseite nennt das Profil.** Damit erklärt sich ein
Knoten selbst, statt sich still anders zu verhalten als seine
Nachbarmaschine — inklusive Hinweis, wo man es ändert.

**Der Einrichtungsassistent fragt einmal, wofür der Knoten da ist.**
Das ist die einzige Stelle, an der das Portal ein Profil schreibt;
autorisiert durch das Setup-Token, und danach nie wieder. Kann der
Assistent das Profil nicht setzen, legt er auch keinen Administrator an
und sagt es — halb eingerichtet wäre schlimmer als noch einmal
abschicken.

## Deutsche Zusammenfassung (v0.3.6)

Zwei neue Abschnitte auf der Gesundheitsseite, beide aus Deinen
Abnahmen vom 8.8.

**„Veröffentlichte Namen" (RFC-0009).** Für jeden Namen, den dieser
Knoten nach außen gibt — seinen eigenen und den jeder Instanz mit
eigener Adresse — steht dort, ob er noch hierher zeigt. Das ist der
DuckDNS-Fall: Der Knoten war tagelang nicht erreichbar und nichts hat
es gesagt.

Der Preis ist benannt statt versteckt: Um zu vergleichen, muss der
Knoten **eine fremde Stelle nach seiner eigenen öffentlichen Adresse
fragen**. Deshalb drei Regeln — es passiert **nur, wenn der Knoten
überhaupt einen Namen veröffentlicht** (ein reiner LAN-Knoten fragt
niemanden), die Seite **nennt den Dienst**, den sie gefragt hat, und
sie sagt, wann zuletzt geprüft wurde. Hinter einem Edge-Knoten zeigen
die Namen auf dessen öffentliche Adresse, die von hier aus nicht
feststellbar ist; dann steht dort nur, ob die Namen auflösen — und
warum nicht mehr gesagt werden kann.

*Nachtrag 0.3.11:* Der Wächter fragt jetzt **IPv4 und IPv6**. „Löst
nicht auf" gilt nur noch, wenn weder ein A- noch ein AAAA-Eintrag
antwortet. Ein Name, der von innen nur IPv6 liefert — genau Dein
`bdt-hub-test.joomp.de` hinter dem Fritzbox-Rebind-Schutz — wird nicht
länger fälschlich als „löst nicht auf" oder gar „zeigt woanders hin"
angezeigt, sondern ehrlich als „Nur IPv6 (nicht vergleichbar)", weil
die öffentliche Adresse heute als IPv4 ermittelt wird.

**„Direkte Ports" (RFC-0015).** Der Zwilling der „Veröffentlichten
Namen" und teilt sich mit ihnen die Mechanik: Der Namens-Wächter fragt
„zeigt der Name noch hierher?", dieser fragt „erreicht der Port noch
hierher?". Für jede freigegebene Direkt-Port-Freigabe steht dort, ob
der Port an der öffentlichen Adresse dieses Knotens tatsächlich
antwortet — sonst ist eine vergessene Router-Freigabe von einer kaputten
App nicht zu unterscheiden. Dieselben Fremdstellen-Regeln gelten (nur
bei freigegebenem Port, nennt den Dienst für die öffentliche Adresse,
darf gecacht werden, hinter einem Edge „nicht prüfbar"). Zwei Grenzen
stehen offen auf der Seite: **Stufe 1 ist ein Selbsttest vom Knoten** —
ein Router ohne Hairpin lässt eine funktionierende Freigabe von hier aus
stumm erscheinen, deshalb ist ein Fehlschlag nie ein rotes „kaputt",
sondern ein graues „von hier nicht bestätigt"; nur ein **Erfolg** wird
behauptet, weil er nicht zu fälschen ist. Der Reflektor von außen
(Stufe 2) nimmt diese Grenze weg. **UDP** lässt sich mit einem bloßen
Paket nicht bestätigen; geprüft wird per STUN-Anfrage, die jeder
WebRTC-Medienserver beantwortet — echter Beweis für genau die Endpunkte,
die UDP trägt.

**„Gebremste Anfragen" (RFC-0010).** Je Instanz mit öffentlicher Route:
wie oft die Mengenbremse in den letzten 24 Stunden abgewiesen hat.
Sonst hinterlässt ein 429 nur eine Zeile in einem Log, das niemand
liest. Die Zahl **muss über alle Worker-Prozesse vollständig sein** —
eine, die stillschweigend unterschlägt, was ein anderer Worker gezählt
hat, ist schlimmer als gar keine. Die Warnschwelle bleibt wie
entschieden zurückgestellt, bis der Zähler Erfahrungswerte liefert.

## Deutsche Zusammenfassung (2.6 Store, v0.3.7)

Der Store ist jetzt ein **Katalog über alle Quellen** statt einer
Aneinanderreihung von Listen — mit Quelle und Vertrauensklasse an
**jedem** Eintrag. Der Grund ist nicht Geschmack: Führen zwei Listen
dieselbe App-Kennung, kann ohnehin nur eine installiert werden. Beide
nebeneinander zu zeigen, böte eine Wahl an, die der Server hinterher
überstimmt. Stattdessen steht auf der Objektseite, welche anderen Listen
dieselbe App führen.

**Gefiltert wird** nach Kategorie, Art, Zielgruppe, Reifegrad, Status,
Vertrauen, Quelle, Lizenz, installiert und Knoten-Profil; **gesucht**
zusätzlich über Hashtags und Texte. Drei Voreinstellungen, jede mit
einem Klick umkehrbar: Apps, die ein Profil erwarten, das dieser Knoten
nicht hat, sind **ausgefiltert, nicht versteckt**; archivierte ebenso;
**„nur für Experten" wird NICHT ausgefiltert** — es wird gekennzeichnet
und kostet eine Bestätigung. Es zu verstecken hieße, aus einem Hinweis
durch die Hintertür eine Sperre zu machen.

Zwei Dinge, die leicht übersehen werden und deshalb normativ sind: Ein
**unbekannter Vokabular-Wert** darf nicht verschwinden und erst recht
nicht zur Ablehnung führen — er wird unverändert gezeigt und unter
„Sonstiges" einsortiert, sonst strandet jede Erweiterung genau die
Knoten, die noch nicht aktualisiert sind. Und **Bilder werden nur aus
der Liste selbst geladen**: Ein Eintrag mit fremder Bild-URL verliert
das Bild, statt dass jeder Knoten beim Öffnen der Store-Seite Server
kontaktiert, die niemand ausgewählt hat.

Die **Objektseite** ist der Grund, warum das Listenformat überhaupt
Darstellungsfelder trägt — ohne sie wären sie Dekoration. Sie zeigt
Symbol, Kurz- und Langtext, Bilder, Version mit Release-Datum, Links,
Lizenz, Rollen, Kategorien, Hashtags und die Fakten vor der
Installation: aus welcher Quelle, in welcher Klasse, welche anderen
Listen dieselbe App führen, und ob das Paket festgelegt ist. Das
„neu"-Abzeichen wird aus dem Release-Datum **berechnet**, nie
gespeichert.

**Quellenverwaltung im Portal** (damit ist Schritt 4 aus
`portal-statt-cli.md` erledigt): hinzufügen, umbenennen, an- und
ausschalten, entfernen, Vertrauensklasse setzen. „Von uns" bleibt dem
vorbehalten, was die Installation mitbringt; eine Quelle auf „geprüft"
zu heben, sagt ausdrücklich, was das kostet — von dort wird künftig
**ohne Bestätigung** installiert. Jede Änderung geht über die
privilegierte Server-Seite, die alles noch einmal prüft: Das Portal hat
die Registry nur lesend eingehängt, und der Spool ist Daten, kein
Vertrauen. Dass die Quellenverwaltung überhaupt ins Portal darf —
anders als das Knoten-Profil, das auf der Maschine blieb — liegt daran,
dass eine Quelle hinzuzufügen sichtbar und umkehrbar ist und für sich
genommen nichts installiert.

**Nachtrag 0.3.8 — der Deploy-Worker gehört auf die Gesundheitsseite.**
Bei der Abnahme auf `oaap-test` (2026-08-09) hat eine schnelle Folge von
Portal-Aktionen den Warteschlangen-Wächter des Wirts stillgelegt. Der
Knoten sah danach in jeder Ansicht gesund aus, nahm weiter Anweisungen
entgegen — und führte keine davon aus. Genau das darf nicht unsichtbar
sein: Jede Änderung, die das Portal am Knoten vornimmt, läuft über diese
Warteschlange. Die Seite meldet den Zustand deshalb **am Symptom**
(Anfragen, die länger warten, als irgendeine von ihnen dauert) statt am
Zustand eines bestimmten Mechanismus — der Portal-Container kann den
Dienstverwalter des Wirts ohnehin nicht fragen, und die Symptom-Prüfung
erwischt auch einen Wirt ohne Dienstverwalter oder einen Worker, der bei
jeder Anfrage abstürzt. Eine Meldung nennt immer einen Weg zurück.

## Nachtrag 0.3.9 — nicht jede Instanz gehört aufs Launchpad

Bisher bekam jede installierte Instanz eine Kachel. Bei einer App ohne
Bedienoberfläche — einer reinen Maschinenschnittstelle wie dem bdt-hub
oder Ollama — führt diese Kachel auf eine Seite, die kein Mensch sehen
will. Künftig entscheidet die **Anwendungsklasse** aus dem App-Manifest
(`oaap.apps.runtime` 2.10): `service` heißt keine Kachel, `frontend`
oder gar keine Angabe heißt Kachel wie bisher. Wer es anders will,
stellt es je Instanz um.

**Der Teil, der leicht übersehen wird:** Ein Launchpad, das nichts
zeigt, sieht aus wie ein kaputtes Launchpad. Auf einem Knoten, der nur
Hintergrunddienste betreibt, wäre die Seite künftig leer, und niemand
könnte sehen, ob die Apps fehlen oder nur die Kacheln. Deshalb sagt das
Portal einem `server_admin` an dieser Stelle, wie viele Instanzen keine
Kachel haben und wo er das ändert. Für alle anderen bleibt die Seite
still — sie sollen nichts vermissen, was sie ohnehin nicht bedienen.

**Verstecken ist keine Zugriffskontrolle**, hier so wenig wie beim
Rollen- und Gruppenfilter: Die Instanz behält Route, Rollen und URL,
und das Gateway prüft weiter. Wer eine App wirklich vor jemandem
verbergen will, nimmt Sichtbarkeitsgruppen (RFC-0007).

## Nachtrag 0.3.12 — der Store für den Mandanten, und der Name, der wirklich antwortet

Zwei Dinge, die beide erst mit dem zweiten Mandanten sichtbar wurden.

**Der Store war für den Kunden zu.** RFC-0022 §4 gibt einem
`tenant_admin` ausdrücklich das Recht, Instanzen seines Mandanten zu
installieren und zu entfernen. Der Katalog verlangte aber `server_admin`
— der Kunde bekam 403 und sah keine einzige App, die er hätte
installieren können. Das Recht stand auf dem Papier und war nicht
ausübbar. Katalog, App-Seite und Installieren sind jetzt für beide
offen; installiert wird immer im **eigenen** Mandanten, weil der Knoten
den handelnden Mandanten aus dem Benutzerdatensatz ableitet und nie aus
der Anfrage.

**Die Quellenliste bleibt beim Betreiber.** Woher Pakete kommen dürfen,
ist eine Entscheidung über den Knoten, nicht über einen Mandanten. Wer
eine Quelle eintragen könnte, könnte alles installieren. Zwei Rechte,
zwei Wächter — und die Prüfung achtet darauf, dass keine neu ergänzte
Route zwischen ihnen durchfällt.

**Der zweite Punkt ist eine falsche Adresse gewesen.** Das Gateway
veröffentlicht die Instanz eines Mandanten unter
`<instanz>.<kürzel>.<knoten>`. Das Portal rechnete an drei Stellen
weiter `<instanz>.<knoten>` — die Launchpad-Kachel verlinkte damit auf
einen Namen, der auf den Auffang-Eintrag des Knotens zeigt, und die
Objektseite zeigte eine Adresse zum Abschreiben, die nirgends antwortet.
Auffällig ist daran nicht die Formel, sondern dass es **drei Kopien**
davon gab: Die Regel liegt jetzt an einer Stelle, und die Prüfung
vergleicht sie mit dem Namen, den `appctl` tatsächlich in die
Gateway-Datei schreibt. Zwei Rechenwege, eine Antwort — weichen sie
voneinander ab, ist genau dieser Fehler wieder da.

**Eine Instanz, deren Mandant auf diesem Knoten unbekannt ist, bekommt
gar keine automatische Adresse.** Das ist dieselbe Richtung, in die das
Gateway ausfällt: lieber kein Name als die App eines Kunden unter dem
Namen des Betreibers.
