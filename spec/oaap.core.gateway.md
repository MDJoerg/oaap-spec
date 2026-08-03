# oaap.core.gateway — HTTP Gateway (outline)

- **ID:** `oaap.core.gateway`
- **Version:** 0.1.0
- **Maturity:** draft (outline — full specification to follow)
- **Based on:** RFC-0001, RFC-0002, RFC-0003

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

## Dependencies

`oaap.core.identity`

## Maturity

`draft`
