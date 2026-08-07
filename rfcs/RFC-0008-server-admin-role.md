# RFC-0008: `server_admin` — Separating Platform Administration from App-Facing `admin`

- **Status:** Draft (2026-08-07) — proposal, awaiting Jörg's decision on open questions
- **Date:** 2026-08-07
- **Authors:** Jörg (problem & proposal), Claude (write-up)
- **Depends on:** RFC-0002 (roles, gateway enforcement)
- **Motivates:** RFC-0007 (App Visibility Groups) — resolves its Open question 1

## Summary

RFC-0002 defined `admin` to mean two different things at once: "full
platform administration" *and* the role an app should treat as its own
administrator, because roles are forwarded to apps verbatim via
`X-OAAP-Roles` (App Deployment Contract). Anyone who needs full admin
functionality *inside one app* today must be given full control over
the OAAP server itself — there is no way to separate the two. This RFC
adds a new role, `server_admin`, that carries platform authority;
`admin` keeps its existing app-facing meaning, unchanged.

## Motivation

This gap has surfaced twice now:

1. **2026-08-04** (`program/capability-ideas.md`, "sechste Runde"): for
   Bernd's CRM 0.1 to make him "Geschäftsführer" in the app, he had to
   be OAAP `admin` — full control over Jörg's server. That specific
   case was resolved differently (Contract v0.3 stopped syncing the
   platform role into the app's own role on every request), but the
   underlying role-model gap was explicitly named and deliberately
   deferred: "Rollenmodell jetzt NICHT erweitern... kommt mit dem
   Tenant-RFC."
2. **2026-08-07** (RFC-0007 review): Jörg wants to hand a test user
   `admin` *inside an app* under evaluation, without granting them
   platform administration. RFC-0007's original proposal has `admin`
   unconditionally bypass visibility-group restrictions — which would
   make every app-admin test grant also a full server admin.

Jörg's proposal (verbatim reasoning, 2026-08-07): split into
`server_admin` (now) and `tenant_admin` (future, full multi-tenancy —
stays out of scope here). The initial installation user gets
`server_admin` and can designate further server admins themselves;
`server_admin` is the actual bypass authority; everything else (app
visibility, RFC-0007's group tags) works as already proposed.

## Proposal

### New role: `server_admin`

Added to RFC-0002's standard role table:

| Role           | Meaning                                                                    |
| -------------- | --------------------------------------------------------------------------- |
| `server_admin` | Full platform administration: users, roles/groups, apps, edge/external routing, backup, configuration. Never forwarded to apps as something app-specific to interpret — a platform/CLI/portal gate only. |

### `admin` keeps its existing, narrower, app-facing meaning

`admin` continues to be forwarded via `X-OAAP-Roles` exactly as today —
zero change for app developers, zero change to the App Deployment
Contract. Its meaning goes back to what it always meant *for apps*:
"show this user the app's own administrative functions." Holding
`admin` alone no longer implies anything about the OAAP server.

### Platform-administration surfaces move from `admin` to `server_admin`

Every CLI command and portal page that operates on the *server itself*
— not on one app's internal data — now requires `server_admin`:

- User, role and group management (incl. RFC-0007's `groups`/`visibility`)
- `oaap edge` (add/list/remove)
- `oaap external` (incl. `--behind-edge`)
- `oaap app install|visibility|...` (platform-level app lifecycle —
  distinct from using an app one is a member of)
- Backup/restore, node/host configuration

This is a mechanical inventory pass over `appctl.py` and the portal's
admin pages before implementation, not a design decision (Open
question 2).

### Bootstrap and migration

- **New installs:** the first user created during `oaap.core.host`
  bootstrap (RFC-0002 §Identity) receives **both** `server_admin` and
  `admin` — no behavior change for the common single-operator install.
- **Existing installs (upgrade):** every user currently holding `admin`
  receives `server_admin` once, as a one-time migration grant, so
  nobody presently trusted with the server loses access. `admin` stays
  as-is for them too. From that point on the two are granted
  independently — `admin` can be handed out freely (e.g. to a test
  user, per app) without server consequences.

### What stays out of scope

`tenant_admin` and multi-tenancy in general remain future work, per
the existing 2026-08-04 decision — this RFC only pulls the
`server_admin` half forward because RFC-0007 needs a real bypass
authority now.

## Consequences

- RFC-0002's role table gains a row (six standard roles instead of
  five); `oaap.core.identity` gains `server_admin` as a role a user
  record can carry.
- RFC-0007's Open question 1 resolves: the visibility-group bypass
  belongs to `server_admin`, not `admin` (RFC-0007 updated accordingly).
- `oaap.core.gateway`/portal: platform-admin-surface checks switch from
  `admin` to `server_admin`; app-facing `X-OAAP-Roles` forwarding is
  unchanged.
- One-time migration step required on update (grant `server_admin` to
  existing `admin` holders).
- App Deployment Contract: **unaffected** — apps still just see
  whatever roles (including `admin`) an operator assigned them.

## Out of scope

- `tenant_admin` / multi-tenancy (existing RFC candidate, unchanged).
- Any UI for delegating *which* server admin can grant `server_admin`
  to whom beyond "any `server_admin` can" (Open question 1).

## Open questions (for the decision)

1. **Who can grant `server_admin`?** Proposed: only an existing
   `server_admin` (self-governing, matches Jörg's framing "kann selbst
   weitere Personen bestimmen"). Alternative: `admin` could also grant
   it. Recommendation: restrict to `server_admin` — granting server
   control is itself a server-administration act.
2. **Exact inventory of CLI commands/portal pages to re-gate** — needs
   a pass over `appctl.py` and the portal before implementation.
   Mechanical, not a design question; done as part of implementation.

## Deutsche Zusammenfassung

**Das Problem:** `admin` bedeutete bisher zwei Dinge gleichzeitig —
„voller Server-Administrator" und „Admin innerhalb einer App" (weil
Rollen unverändert an Apps durchgereicht werden). Wer jemandem
App-Admin-Rechte geben will (z. B. einem Test-User), macht ihn damit
zugleich zum Herrscher über den ganzen Server. Genau dieser Fall kam
jetzt zweimal vor: beim CRM (schon anders gelöst, aber die Rollenlücke
blieb bewusst offen) und jetzt bei RFC-0007 (Gruppen-Bypass).

**Der Vorschlag (Jörgs Idee):** Eine neue Rolle `server_admin` für die
echte Server-Verwaltung (Benutzer, Gruppen, Edge/externe Routen,
Backup, Konfiguration) — nie an Apps weitergereicht. `admin` bleibt wie
gehabt die App-Rolle, ohne Server-Folgen. Der Ersteinrichtungs-Benutzer
bekommt beides und kann weitere Server-Admins bestimmen. Bestehende
Installationen: alle heutigen `admin`-Träger bekommen beim Update
einmalig zusätzlich `server_admin` — niemand verliert Zugriff.
`tenant_admin` bleibt wie besprochen Zukunftsmusik (eigenes
Multi-Tenancy-RFC).

**Für RFC-0007 heißt das:** Der Sichtbarkeits-Bypass gehört
`server_admin`, nicht `admin` — wird dort direkt übernommen.

**Zu entscheiden:** Darf nur `server_admin` weitere `server_admin`
vergeben (empfohlen), oder auch `admin`?
