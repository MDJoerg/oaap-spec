# oaap.core.portal — Web Portal

- **ID:** `oaap.core.portal`
- **Version:** 0.3.0
- **Maturity:** draft
- **Based on:** RFC-0001, RFC-0002, RFC-0003, RFC-0005, RFC-0007, RFC-0008

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

### 2.2 Launchpad

- Installed app instances appear as tiles with name, description,
  version, and channel badge; the tile links to the instance's
  platform-generated URL (RFC-0005 level 1: gateway listener port).
  Apps open through the gateway, never embedded.
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

### 2.5 Health

- Visible for roles `server_admin` and `partner` (service-partner
  scenario) — moved from `admin` in v0.3.0 (RFC-0008: this is
  server-internal information, not app-facing).
- **Node values**: platform version, uptime, CPU load, memory,
  free disk of the platform data filesystem (with a warning threshold
  matching the installer's minimum free space).
- **Core services**: liveness of identity and portal plus a
  **full-chain check** through the gateway (gateway → identity),
  so a broken proxy path is visible even when every container runs.
- **App instances**: per instance, the manifest's health endpoint is
  checked over the internal network (`oaap.apps.runtime` provides
  service port and health path in the registry). Instances registered
  before that data existed show "unknown" with a remediation hint.
- Whole-landscape health (controller + workers, RFC-0003) is a later
  stage of this section; node-local values come first.

### 2.6 Reserved navigation

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
2. Every management surface re-checks the required role server-side
   (`server_admin` for user management/store/instance visibility,
   `server_admin`/`partner` for health) — the navigation filter is UX
   only.
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
11. **Instance visibility authorization**: without `server_admin`,
    `/instances` routes return 403 and the navigation hides the entry.

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
