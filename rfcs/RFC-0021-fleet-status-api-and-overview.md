# RFC-0021: Fleet Status API and Fleet Overview App

- **Status:** Accepted (2026-08-23)
- **Date:** 2026-08-23
- **Authors:** Claude (analysis & proposal), Jörg (decisions)
- **Depends on:** RFC-0003 (platform topology), RFC-0006 (edge node),
  RFC-0008 (`server_admin`), RFC-0010 (public route throttling),
  RFC-0011 (node profiles)
- **Driver:** the fleet is now five nodes (oaap-test, oaap-demo,
  oaap-bernd, raspi400, oaapx01), one of them a headless production
  node on the public internet, managed remotely. Today the only
  cross-node view is Uptime Kuma's "answers / does not answer".
  The health page knows much more — but only per node, only as HTML,
  only behind an interactive `server_admin` login.

## Summary

Every node gains one **read-only, machine-readable status document**:
`GET /fleet/status`, guarded by a dedicated, revocable **fleet key**
(no session, no cookie). A new platform app, the **Fleet Overview**
("FleetView", built in `oaap-apps` like the Studio), is the first
consumer: the operator configures the list of nodes and one key per
node, the app polls them and shows the landscape — traffic lights,
versions, instances, pending confirmations — with links into each
node's portal. Stage 1 is **strictly read-only**: this RFC creates no
remote-control channel of any kind. Management actions across nodes
(rollout waves, remote deploy, self-healing) remain a separate, later
RFC that will need signed commands; nothing here pre-empts it.

## Motivation

1. **The headless scenario needs eyes.** oaapx01 is exactly the node
   ADR-0006 scenario 2 describes: production services, no one sitting
   in front of it. "Remote managed" without a landscape view means
   logging into five portals in five tabs.
2. **The data already exists — the interface does not.** The portal's
   health page (`oaap.core.portal`) gathers core-service states,
   per-instance health/version/channel, external names, DNS drift and
   recent deployments. None of it is reachable by a program: it is
   rendered HTML behind an interactive login.
3. **Uptime Kuma cannot say *what* is wrong.** It probes URLs. It
   cannot tell "platform 0.1.38, three instances, one of them
   unhealthy, one promotion awaiting confirmation" from "answers 200".
4. **The direction of connection is already decided in spirit.** The
   idea store records the rule for external nodes: *the internal
   server connects outward; the external node needs no access inward.*
   A pull-based status API honours that literally — the watching node
   polls, the watched node never connects anywhere.

## Proposal

### 1. The status document — `GET /fleet/status`

One new route on the gateway, answered by the portal, returning JSON:

```json
{
  "schema": "oaap.fleet.status/0.1",
  "node": "oaapx01",
  "platform_version": "0.1.40",
  "profiles": [],
  "time": "2026-08-23T10:15:00Z",
  "core": [
    {"name": "identity", "state": "ok"},
    {"name": "gateway",  "state": "ok"},
    {"name": "portal",   "state": "ok"},
    {"name": "deploy-worker", "state": "ok"}
  ],
  "instances": [
    {"instance": "bdt-hub", "app": "bdt-hub", "version": "0.1.0",
     "channel": "production", "state": "ok",
     "origin": "promoted", "address": "hub.bdt.joomp.de"}
  ],
  "attention": [
    {"kind": "dns_drift", "detail": "public name points at old IP"},
    {"kind": "confirmation_pending", "instance": "bdt-hub-test"}
  ]
}
```

Rules:

- **Facts only, never secrets.** No tokens, no key hashes, no config
  values, no source URLs (a source URL has already leaked a PAT once —
  CURRENT_STATE 63). Contents are the same facts the health page shows
  a `server_admin`, minus anything that is a credential or contains
  one.
- **`attention` is the machine-readable version of "something needs a
  human"**: DNS drift (the check the platform already runs), a pending
  promotion/deployment confirmation, a core service down. The list of
  kinds is open; consumers must tolerate unknown kinds.
- **The document is versioned** (`schema`), so the overview app can
  talk to nodes of mixed platform versions during a rollout — which is
  the normal state of a fleet, not the exception.
- The endpoint answers on every published name of the node, like any
  other route, and is throttled by RFC-0010's mechanism.

### 2. The fleet key

- Issued and revoked by `server_admin` on the node being watched:
  `oaap fleet key issue <label>` / `list` / `revoke <label>`, plus the
  same on the portal's instances page later. The label says *who*
  watches ("fleetview@oaap-demo"), so revocation is meaningful.
- Presented as a bearer header. Stored **hashed** on the node, same
  pattern as deploy tokens (the readable value never touches the
  disk); shown exactly once at issue time.
- Grants **exactly one thing**: `GET /fleet/status`. It is not a
  session, carries no roles, opens no other route. A leaked fleet key
  leaks the landscape's facts — unpleasant, but it moves nothing,
  deletes nothing, deploys nothing.
- Without a valid key the route answers 403 with no body detail
  (same "no chatter" rule as the deploy hook).

### 3. The Fleet Overview app (stage 1)

- A **normal platform app** from `oaap-apps` (dogfooding, like the
  Studio): installed from the store, runs on the operator's inner
  node (oaap-demo today), visible per RFC-0007 groups, admin pages
  gated on `server_admin` role headers.
- Configuration is operator data: the node list (name, base URL) as a
  config value, one fleet key per node as a **secret** config value
  (`oaap app config` / portal card — write-only, never echoed).
- Polls each node on a modest interval and renders the landscape:
  one row/tile per node — reachable, platform version (and whether
  versions diverge across the fleet), core lights, instance list with
  channel and state, and the `attention` items on top. Every node
  links to its own portal — FleetView **shows**, the node's portal
  **acts**.
- Unreachable is a state, not an error page: a node that does not
  answer is shown exactly like Uptime Kuma would show it — plus
  everything known from the last successful poll, marked stale.
- The whiteboard/layer view from the idea store (nodes by layer,
  tenant lens for service partners) is the app's growth direction;
  stage 1 is an honest list/tile report following the design
  guidelines' floorplans.

### 4. Non-goals (deliberate)

- **No write path, no commands, no self-healing.** Any cross-node
  action (rollout waves as the continuation of RFC-0020, remote
  deploy, restart buttons) is a separate RFC and will need more than
  a bearer key — signed, auditable commands. This RFC keeps the
  watched node's autonomy intact (RFC-0006: "the platform stays
  yours"; RFC-0011 kept `headless` out for the same reason).
- **No push telemetry, no metrics history.** The status document is
  "now". Real-time dashboards, cost/usage series and their storage are
  the telemetry capability that the AI gateway idea (`oaap.ai.gateway`,
  idea store 2026-08-23) will need too — one concept for both, later.
- **No tenant lens yet.** The document deliberately has room for a
  `tenant` field on instances once the tenant RFC exists; nothing in
  stage 1 depends on it.
- **No auto-discovery.** The node list is operator configuration.
  A node never announces itself anywhere.

## Security considerations

- The status route is a new unauthenticated-by-session surface; its
  guard is the key check plus RFC-0010 throttling. The document must
  therefore never contain anything whose exposure is worse than
  "facts about the landscape": no secrets, no internal addresses
  beyond what the node publishes anyway, no user data, no logs.
- Key hygiene follows the deploy-token precedent: hash at rest, show
  once, revoke by label, audit issue/revoke/use (state changes to the
  log, not every poll).
- FleetView holds fleet keys as app secrets — the first app that
  holds credentials *to other nodes*. That is exactly the posture the
  platform already accepts for operator-entered app secrets, and the
  keys' blast radius is read-only by construction. The app must never
  render a key back, not even masked.

## Outlook: partner-managed fleets (stage-2 direction, not built here)

Jörg's requirements for the later management stage (2026-08-23) are
recorded so stage 1 does not paint itself into a corner:

1. **Trust is created by the owner.** Whoever set the nodes up (and
   holds all rights) creates the trust relationships. A **partner**
   who later cares for nodes gets rights **on the central management
   node** — never directly on the managed nodes.
2. **Node credentials never leave the management node.** The partner
   always acts *through* the central instance, which checks his
   permissions and logs every action. This is what makes the next
   requirement constructive rather than organisational:
3. **Revocation is immediate and complete.** Removing a partner's
   rights on the management node cuts his access to *all* connected
   nodes in the same moment — there is nothing to collect back,
   because the partner never held node keys.
4. **Granular permissions, several partners in parallel.** What a
   partner may do (read / deploy / configure, per node or group) is
   controlled on the management node; several partner relationships
   may coexist (different services, and explicitly the transition
   period when switching from one partner to another).
5. **The owner sees who did what.** Metadata audit always (who, when,
   which action, which node, result). **Payload trace is an option
   the owner can switch on** (fault isolation, building trust) — known
   to all parties, its activation itself audited and visible; that
   transparency is part of the deterrent. Payloads can carry personal
   data, so a trace is announced and time-boxed; metadata remains the
   default.

Stage 1 already conforms: fleet keys are held by the central node's
FleetView app and are never rendered back; the `partner` role reads
through the platform's own role gate, not with a key of its own.

## Decisions (Jörg, 2026-08-23)

1. **Scope of the document: full.** Stage 1 ships the complete status
   document as proposed — platform version, core-service lights,
   instance list (version, channel, state, address) and the
   `attention` list. The health page gathers these facts already; the
   marginal cost is small and the value for the upcoming headless
   walkthrough is large. Node resource figures (disk/RAM/CPU) stay
   out — they lean into the telemetry capability.
2. **Poll interval: minutes, configurable.** Default in the order of
   60 seconds per node. Outage *alerting* remains Uptime Kuma's job;
   FleetView shows state and attention, it does not race to be a
   live dashboard. Seconds-level freshness is telemetry territory,
   deferred with it.
3. **Visibility: `server_admin` and `partner`.** Consistent with the
   partner model in the outlook (partners work read-only through the
   management instance) and with the health page, which already
   admits `partner`. Granular per-partner scoping (which partner sees
   which nodes) arrives with stage 2.
4. **The word is `fleet`.** CLI `oaap fleet …`, route `/fleet/status`,
   spec `oaap.fleet.status`. The program level keeps speaking of the
   "Flotte"; the technical level is English per ADR-0003.

## Zusammenfassung auf Deutsch

Jeder Knoten bekommt **eine lesende, maschinenlesbare Status-Auskunft**
(`GET /fleet/status`): Plattformversion, Kerndienst-Ampeln, Instanzen
mit Version/Kanal/Zustand und eine `attention`-Liste („hier braucht es
einen Menschen": DNS-Drift, wartende Bestätigung, Dienst ausgefallen).
Geschützt wird sie nicht per Login, sondern per **Flotten-Schlüssel**:
von `server_admin` ausgestellt und widerrufbar, gehasht gespeichert wie
Deploy-Token, kann **ausschließlich diese eine Auskunft lesen** — ein
geleakter Schlüssel kann nichts bewegen. Niemals enthalten: Geheimnisse,
Quell-URLs, Konfigurationswerte.

Die **Flotten-Übersichts-App** („FleetView") ist eine normale
Plattform-App aus `oaap-apps` (wie das Studio) und läuft auf dem
inneren Knoten: Knotenliste und je ein Schlüssel als Betreiber-Config,
die App **pollt** die Knoten (der interne Server verbindet sich nach
außen — der externe braucht keinerlei Zugang nach innen) und zeigt die
Landschaft mit Ampeln, Versionsständen und Auffälligkeiten; jede Zeile
verlinkt ins Portal des Knotens. **Stufe 1 ist strikt lesend** — keine
Fernsteuerung, keine Selbstheilung, kein Rollout; das kommt später als
eigenes RFC mit signierten Aufträgen. Für diese spätere Stufe hält der
Ausblick Jörgs Anforderungen fest (2026-08-23): Partner bekommen ihre
Rechte **nur auf dem Management-Knoten** (Knoten-Schlüssel verlassen
ihn nie — dadurch wirkt ein Entzug sofort auf alle verbundenen Knoten),
granulare Steuerung je Partner, mehrere parallele Partnerbeziehungen
(auch für den Partnerwechsel), Metadaten-Audit immer und ein vom
Besitzer zuschaltbarer, selbst auditierter Payload-Trace. Die vier
Entscheidungen (Jörg, 2026-08-23): volle Status-Auskunft schon in
Stufe 1; Poll-Intervall im Minutenbereich (Alarmierung bleibt bei
Uptime Kuma); sichtbar für `server_admin` und `partner`; der Begriff
ist `fleet`.
