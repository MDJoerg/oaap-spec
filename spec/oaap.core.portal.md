# oaap.core.portal — Web Portal

- **ID:** `oaap.core.portal`
- **Version:** 0.2.0
- **Maturity:** draft
- **Based on:** RFC-0001, RFC-0002, RFC-0003, RFC-0005

## 1. Purpose

The portal is the web UI where **everything** on the platform is
administered — there is no other administration surface for end users
(technicians and service partners additionally have the node CLI, see
`oaap.core.host` 2.3). It serves the first-run wizard during bootstrap
and afterwards provides the launchpad, user management, and platform
health, scoped by the standard roles (RFC-0002).

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
- Tiles are **role-filtered**: a user sees an instance only if their
  roles intersect the instance's route roles (admins see everything).
  The filter is UX — the gateway enforces authorization on every
  request regardless.
- Data source is the platform's instance registry, maintained by the
  app runtime (`oaap.apps.runtime`); the portal reads it, it never
  writes it.
- Later stages (backlog, RFC-0005/portal outline): tile images,
  grouping, operator-configurable appearance, multiple designs per
  user/group.

### 2.3 User management

Admin-only UI over the operations of `oaap.core.identity` 2.4 (list,
create, update, set password; deactivate instead of delete;
last-admin protection surfaces as an error message). Layout follows
the floorplans: a read-only list report navigating to one object page
per user; create is its own object page; saves use
Post/Redirect/Get.

### 2.4 Health

- Visible for roles `admin` and `partner` (service-partner scenario).
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

### 2.5 Reserved navigation

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
   (`admin` for user management, `admin`/`partner` for health) — the
   navigation filter is UX only.
3. The portal talks to identity's internal API only over the internal
   container network; that API is never exposed through the gateway.
4. Health checks run from the portal over the internal network and
   never expose internal addresses to the browser beyond status text.

## 5. Conformance tests (described)

1. **Wizard lifecycle**: wizard works exactly once (see
   `oaap.core.host` tests 2–4).
2. **Role-filtered launchpad**: a user whose roles do not intersect an
   instance's route roles does not see its tile; an admin sees all
   tiles; the gateway still blocks direct access regardless of tiles.
3. **Tile targets**: each tile links to the instance's generated URL
   and the app opens through the gateway (login enforced).
4. **User management floorplans**: the user list is read-only with
   navigation to an object page; create/update/set-password work and
   respond with Post/Redirect/Get; identity errors (e.g. last-admin
   protection) surface as messages.
5. **User management authorization**: without the `admin` role, the
   user-management routes return 403 and the navigation hides the
   entry.
6. **Health authorization**: health is reachable for `admin` and
   `partner`, 403 for everyone else.
7. **Health signal**: stopping an app container (or a core service)
   changes its health row on the next page load; the full-chain
   gateway check fails when the gateway cannot reach identity.
8. **Node values**: the health page shows version, uptime, load,
   memory, and disk of the platform data filesystem.
9. **Offline**: all portal pages render without any request leaving
   the platform (no external fonts, scripts, images).

## 6. Dependencies

`oaap.core.gateway`, `oaap.core.identity`; reads the instance registry
of `oaap.apps.runtime`.

## 7. Maturity

`draft` — v0.2 specifies launchpad, user management, and health as
implemented by the reference (2026-08-04). Open: appearance
configuration, landscape health, settings/store/studio areas.
