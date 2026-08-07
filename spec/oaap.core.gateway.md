# oaap.core.gateway — HTTP Gateway (outline)

- **ID:** `oaap.core.gateway`
- **Version:** 0.2.0
- **Maturity:** draft (outline — full specification to follow;
  §Edge routing added 2026-08-07 per RFC-0006)
- **Based on:** RFC-0001, RFC-0002, RFC-0003, RFC-0006

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
- **Route semantics**: declared paths are prefix matches, longest
  declared prefix wins; requests under no declared route are rejected
  at the gateway. The original `Host` header is preserved;
  `X-Forwarded-Proto`/`X-Forwarded-For` are set. Additional ports an
  app opens are never published.
- **Topology** (RFC-0003): the gateway runs on the controller and also
  publishes apps that run on worker nodes; a worker whose controller is
  down is not reachable through the gateway.
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

## Dependencies

`oaap.core.identity`

## Maturity

`draft`

## German summary / Deutsche Zusammenfassung (Edge-Abschnitt)

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
