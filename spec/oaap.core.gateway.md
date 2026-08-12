# oaap.core.gateway — HTTP Gateway (outline)

- **ID:** `oaap.core.gateway`
- **Version:** 0.2.4
- **Maturity:** draft (outline — full specification to follow;
  §Edge routing added 2026-08-07 per RFC-0006; visibility groups
  parameter added 2026-08-07 per RFC-0007; per-instance public
  hostnames added 2026-08-08 per RFC-0009; public-route throttling and
  the WebSocket forward-auth fix added 2026-08-08 per RFC-0010;
  app-network membership added 2026-08-12 per RFC-0016)
- **Based on:** RFC-0001, RFC-0002, RFC-0003, RFC-0006, RFC-0007,
  RFC-0008, RFC-0009, RFC-0010, RFC-0016

## Purpose

The single HTTP(S) entry point of the platform. Every request to the
portal or any app passes through it; the default policy is **deny** —
a route is only reachable for an authenticated identity whose roles
permit it, unless the route is explicitly marked `public` in the app's
configuration (none by default). Apps can rely on authentication having
happened and never see credentials.

## Interface (sketch)

- **Route registration**: apps declare their routes, required roles, and
  any `public` exceptions in their manifest; the platform configures the
  gateway from that — apps never configure the gateway directly.
- **Identity propagation**: the gateway passes the verified identity and
  roles to apps via trusted headers or tokens (mechanism to be resolved
  with `oaap.core.identity`). **Anti-spoofing guarantee**: identity
  headers arriving from clients are stripped/overwritten on every
  route, including `public` ones — apps can trust their presence.
- **Visibility groups** (RFC-0007): an installed instance may carry an
  additional `visibility` restriction (`oaap.apps.runtime` 2.7,
  operator-set, never in the app manifest). When set, every non-public
  route's forward-auth call for that instance gains a `groups=`
  parameter alongside `roles=`, checked by `oaap.core.identity` 2.3/2.6
  — `server_admin` bypasses it unconditionally (RFC-0008). No new
  header is forwarded to apps; the App Deployment Contract is
  unaffected.
- **Route semantics**: declared paths are prefix matches, longest
  declared prefix wins; requests under no declared route are rejected
  at the gateway. The original `Host` header is preserved;
  `X-Forwarded-Proto`/`X-Forwarded-For` are set. Additional ports an
  app opens are never published.
- **Topology** (RFC-0003): the gateway runs on the controller and also
  publishes apps that run on worker nodes; a worker whose controller is
  down is not reachable through the gateway.
- **App network membership** (RFC-0016): each app instance runs on its
  own network (`oaap.apps.runtime` 2.11); the gateway is the only core
  service that joins those networks, which is how it proxies to apps
  that are otherwise isolated from identity, portal and each other. The
  membership is re-established whenever the gateway is recreated (every
  platform update), or apps become unreachable (502).
- **TLS termination** and port configuration (see `oaap.core.host`).

## Edge routing (RFC-0006)

A node whose gateway owns the shared public entry point can forward
requests for **other platforms' hostnames** to the platform that owns
the name. Only the entry is shared; the platforms stay autonomous.

### Edge side

- **Routing table**: administrator-maintained entries
  `hostname → target address[:port]`. Each entry covers the hostname
  **and** its wildcard subtree (`host` and `*.host`) — RFC-0005 level 3
  gives every app instance a subdomain, so a platform owns a subtree.
  CLI: `oaap edge add <hostname> <target>` / `list` / `remove`.
- The edge terminates TLS and obtains/renews certificates for all
  routed names (it is the only node that can answer ACME challenges).
  HTTP requests for routed names are redirected to HTTPS at the edge;
  ACME challenges are excepted.
- **Subdomain certificates are obtained on demand.** The edge cannot
  know the backend's app instance names, and wildcard certificates
  require a DNS challenge the platform does not assume. Certificates
  for names below a routed hostname are therefore obtained at
  handshake time, gated by a platform approval endpoint that permits
  only names equal to or below a configured edge route. *Known
  hardening gap:* any subdomain of a routed host is approvable, so a
  hostile client could drive certificate issuance into the CA's rate
  limit for that domain; a future increment lets the edge verify the
  concrete instance names against the backend.
- Forwarding preserves the original `Host` header unchanged and sets
  `X-Forwarded-Proto`/`X-Forwarded-For` (contract guarantee 2 holds
  through the chain).
- A routed hostname MUST NOT equal the edge's own external hostname.
  Names not in the table are never forwarded.
- The edge does not log request bodies (RFC-0006 trust section).

### Backend side (behind-edge mode)

A platform served through an edge is switched into behind-edge mode:
`oaap external set <hostname> --behind-edge <edge-address>`.

In this mode the gateway, for the external hostname and its subtree:

1. serves the full external site over **plain HTTP** (the edge already
   terminated TLS) and suppresses the usual HTTP→HTTPS redirect —
   otherwise the chain loops;
2. does not attempt ACME for these names (it cannot succeed — the
   ports live at the edge);
3. accepts requests for these hostnames **only from the configured
   edge address**; any other client gets `403` (this is also what makes
   trusting `X-Forwarded-*` acceptable: they can only come from the
   edge). Local entry points (LAN address, app listener ports) are
   unaffected;
4. keeps every RFC-0002 guarantee: identity headers are stripped and
   re-set by this gateway regardless of what the edge forwarded.

`oaap external show` reports the mode. Switching back to direct mode
(`oaap external set <hostname>` without the flag) restores TLS sites
and the redirect.

### Unavailability page (reserved)

When a routed backend does not answer, the edge serves a configurable
page; the same mechanism will serve deliberately-offline routes
(maintenance, incident response). Templates range from plain text to
an OAAP-branded page to custom content. Details are deferred to the
full specification; RFC-0006 resolved question 3 records the decision.

## Per-instance public hostnames (RFC-0009)

Besides the automatic `<instance>.<external hostname>` subdomains
above, a single app instance MAY register a public hostname **of its
own** — one that does not derive from the node's name and therefore
survives the app moving to another node. The gateway serves it as an
additional site for that instance:

1. built from the **same** route/role/group block as every other entry
   point of that instance — default deny, reserved `/auth/*`,
   anti-spoofing and visibility groups apply unchanged. Its own
   address grants an app nothing extra;
2. in **direct** mode: a TLS site with ACME plus an explicit
   HTTP→HTTPS redirect;
3. in **behind-edge** mode: plain HTTP, no ACME, no redirect, and only
   from the edge address — points 1–4 of the backend-side rules above
   apply verbatim, for the same reasons;
4. **additive** — the automatic node subdomain keeps working, so
   clients can migrate gradually;
5. **collision-refusing**: a name is rejected if it is or lies under
   the node's own external hostname, if an edge route on this node
   covers it, or if another instance already holds it; symmetrically,
   an edge route that would capture a local instance's hostname is
   rejected. The gateway never silently resolves such a conflict.

DNS and port forwarding for the name are the operator's responsibility
(RFC-0006's division of labour, unchanged).

## Public-route throttling (RFC-0010)

A `public` route receives no authentication — that is its definition.
The gateway therefore applies the one control it still can: a limit on
**requests per client address per instance**, checked before the app is
reached.

- On by default (reference default: 300 requests per 60 s), adjustable
  per instance and switchable off by `server_admin`.
- **One budget per instance**, shared by every entry point it has (LAN
  listener, node subdomain, own hostname) — a limit that can be
  bypassed by changing entry point is not a limit.
- The **gateway determines the client address**: the TCP peer in direct
  mode, the address vouched for by the edge in behind-edge mode. A
  client-supplied `X-Forwarded-For` is never used, and the edge
  overwrites that header with the peer it sees, so the chain cannot be
  seeded by the client.
- Checked **once per request**, so streaming responses and WebSocket
  connections pay it at setup only (guarantee 7 unaffected).
- Exceeding it yields `429` with `Retry-After`; the app is not reached.
- It is a **volume brake, not authentication**: per-address limits do
  not stop a distributed key-guessing attack, and the count is
  approximate (see RFC-0010 for the full list of what it does not
  promise). Apps on public routes remain responsible for their own
  credential lockout.

**Forward-auth and protocol upgrades.** The authentication subrequest
is a plain `GET`; the original request's hop-by-hop headers
(`Connection`, `Upgrade`) MUST NOT be forwarded to it. Passing them on
makes a WSGI auth service answer `400`, which forward-auth returns to
the client — breaking every WebSocket handshake before the app is
reached. This applies to every forward-auth call: platform apex, app
routes and the throttle check alike.

## Dependencies

`oaap.core.identity`

## Maturity

`draft`

## German summary / Deutsche Zusammenfassung (Edge-Abschnitt + Sichtbarkeitsgruppen)

**Sichtbarkeitsgruppen (RFC-0007):** Ist für eine Instanz eine
Gruppen-Einschränkung gesetzt, hängt das Gateway an jede
Rollenprüfung zusätzlich `groups=...` an — geprüft von Identity,
`server_admin` sieht immer alles. Kein neuer Header an Apps.

Ein Knoten mit dem öffentlichen Eingang (Portfreigabe) kann Anfragen
für die Hostnamen **anderer** Plattformen an deren Adresse
weiterreichen: Der Administrator pflegt eine Tabelle `Hostname → Ziel`
(`oaap edge add/list/remove`); jeder Eintrag gilt für den Namen samt
aller Subdomains. Der Edge holt die Zertifikate für alle Namen und
leitet HTTP auf HTTPS um. Die Zielplattform wird mit
`oaap external set <name> --behind-edge <edge-adresse>` in den Modus
„hinter Edge" geschaltet: Sie liefert ihre externe Site dann über
HTTP aus (kein Umleitungs-Loop), versucht keine eigenen Zertifikate
mehr und akzeptiert Anfragen für diese Namen **nur von der
Edge-Adresse** (sonst 403). Alle Sicherheitsgarantien bleiben: Auch
hinter dem Edge verwirft das eigene Gateway die Identitäts-Header und
setzt sie nach eigener Anmeldung neu. Die konfigurierbare
„Nicht erreichbar"-Seite (auch für bewusst offline genommene Routen)
ist reserviert und wird in der Vollspezifikation ausgearbeitet.

## Deutsche Zusammenfassung (eigene Adressen je Instanz, v0.2.2)

**Neu (RFC-0009):** Eine App-Instanz kann einen **eigenen öffentlichen
Namen** bekommen — zusätzlich zur automatischen Adresse
`<instanz>.<knotenname>`. Hintergrund ist bdt-hub: Dessen Adresse wird
in ausgelieferte Clients eingebaut, und die dürfen nicht am Namen der
Maschine hängen, auf der die App zufällig gestartet ist.

Wichtig: Es ist **dieselbe** Absicherung wie bei jeder anderen Adresse
derselben App — Rollen, Sichtbarkeitsgruppen, default deny und die
reservierte Anmelde-Route gelten unverändert. Direkt am Internet gibt
es ein normales Zertifikat plus HTTP→HTTPS-Umleitung; hinter einem Edge
Klartext-HTTP ohne Umleitung und nur vom Edge annehmbar (sonst
Endlosschleife — dieselbe Regel wie bei Knotennamen seit RFC-0006).
Die alte Adresse bleibt gültig, damit Clients in Ruhe umziehen können.
Namenskonflikte werden abgelehnt statt stillschweigend aufgelöst.
DNS-Eintrag und Portfreigabe bleiben Sache des Betreibers.

## Deutsche Zusammenfassung (Drosselung öffentlicher Routen, v0.2.3)

**Neu (RFC-0010):** Öffentliche Routen bekommen eine Bremse — Anfragen
pro Client-Adresse und Instanz, standardmäßig an, je Instanz
einstellbar. Ein Budget gilt für alle Zugänge einer Instanz zusammen,
sonst ließe es sich durch Wechseln des Zugangs umgehen. Wer der Client
ist, entscheidet das Gateway (direkter Peer bzw. die vom Edge
bezeugte Adresse), nie ein vom Client geschickter Header. Geprüft wird
einmal pro Anfrage, Streams und WebSockets zahlen also nur beim
Verbindungsaufbau. Wichtig und ausdrücklich festgehalten: Das ist eine
**Mengenbremse, keine Zugangskontrolle** — Details in RFC-0010.

**Behobener Fehler:** Die Anmeldeprüfung (`forward_auth`) darf die
Upgrade-Header einer Anfrage nicht mitbekommen. Tat sie es, antwortete
der Identity-Dienst mit 400 und **jeder WebSocket-Verbindungsaufbau
scheiterte** — auf allen authentifizierten Routen, seit es sie gibt.
