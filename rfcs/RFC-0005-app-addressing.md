# RFC-0005: App Addressing and Entry Points

- **Status:** Draft
- **Date:** 2026-08-03
- **Authors:** Claude (proposal), Jörg (review & decision)
- **Depends on:** RFC-0002 (gateway), RFC-0004 (app manifest)

## Summary

How does a user's browser reach a specific app on the platform? Most
web apps assume they run at the root path (absolute asset URLs) — the
first real integration (BDT) confirmed this. At the same time, LAN
environments (the primary Phase-1 target) offer no reliable way to
create per-app hostnames. This RFC defines a **layered addressing
model**: port-based addressing as the universal baseline, path prefixes
as an opt-in for subpath-tolerant apps, and per-app hostnames wherever
real name resolution exists. Addressing is entirely a platform concern;
apps never depend on how they are addressed. Response-body URL
rewriting is explicitly rejected.

## Constraints (why the obvious answers fail)

1. **Root-path assumption**: typical web apps use absolute URLs
   (`/css/…`, `/api/…`). Mounting them under `/appname/` breaks them.
   We cannot force the entire self-hosting ecosystem to become
   subpath-tolerant — especially not `wrapped` apps.
2. **URL rewriting is a dead end**: rewriting URLs inside HTML/JS/JSON
   responses at the gateway fails for runtime-generated URLs, JSON
   payloads, and service workers. It produces per-app special cases —
   the opposite of a contract. Rejected.
3. **LAN name resolution is unreliable**: mDNS (`*.local`) does not
   resolve dependably in Android browsers (field tablets!). Consumer
   routers (e.g. Fritzbox) offer `device.fritz.box` but no custom
   aliases or wildcards. Requiring users to run or reconfigure DNS
   violates the NAS-simple principle.
4. **TLS follows naming**: public hostnames get ACME certificates;
   port-based and LAN addressing need a separate TLS story (future
   work, see open questions).

## Proposal

### Principles

- **Addressing is platform business.** Apps declare routes and roles
  (RFC-0004); the platform decides how instances are exposed. Apps MUST
  work regardless of the addressing level (they already MUST accept any
  `Host`, deployment contract rule 9).
- **The portal is the launchpad.** Users open apps by clicking tiles in
  the portal; the platform generates the URLs. URL aesthetics are
  therefore secondary to reachability.
- Every entry point, on every level, passes through the gateway with
  identical authentication (RFC-0002 — default deny on all listeners).
  Concretely: additional ports (level 1) are **listeners of the gateway
  itself**, not of app containers — apps remain attached only to the
  internal network and are never directly reachable. Session check,
  role check against the manifest's routes, header stripping, and all
  contract guarantees apply identically on every listener.

### Level 1 — Port per app instance (universal baseline)

- Each app instance gets a dedicated gateway listener port
  (e.g. `http://<platform-host>:8101/`), serving the app at the root
  path — no app cooperation needed.
- Works in every environment (LAN, Fritzbox, offline) with zero DNS
  requirements. This is the **default** in the LAN profile.
- The platform manages a port range and shows the resulting URLs in the
  portal; users normally never type them.

### Level 2 — Path prefix (opt-in per app)

- Apps that tolerate running under a subpath declare it in the manifest
  (`subpath: true` plus the env var the platform sets, e.g.
  `OAAP_BASE_PATH`). Only then may the platform mount them under
  `/<app-id>/` on the main port.
- Recommended for `native` apps we influence (the deployment contract
  will recommend subpath tolerance); never assumed for `wrapped` apps.

### Level 3 — Hostname per app (where names exist)

- **Internet profile**: real DNS + wildcard or per-app records; ACME
  TLS; `https://bdt.example.com`. The natural mode for internet
  deployments (shared services, partner portal).
- **LAN with platform DNS**: the platform can serve DNS for a private
  zone (e.g. `*.oaap.intern`). Two delivery paths:
  - **WireGuard clients** (field tablets): the WireGuard profile pushes
    the platform as DNS server — per-app hostnames work automatically
    for exactly the user group that needs remote access. No router
    changes.
  - **LAN devices**: optional — operators who can point their router's
    DHCP/DNS at the platform get hostnames LAN-wide; nobody is required
    to.
- mDNS (`oaap.local`) MAY be published as a convenience for reaching
  the **platform itself** on Apple/Windows clients, but no per-app
  reliance on mDNS.

### Manifest impact (RFC-0004 amendment)

- New optional service field: `subpath: true` (+ documented
  `OAAP_BASE_PATH` env contract).
- No other manifest changes: levels 1 and 3 are transparent to apps.

## Consequences

- `oaap.core.gateway` spec must cover multiple authenticated listeners
  and platform-generated routing config per instance and level.
- The portal spec gains the launchpad duty: tiles with
  platform-generated app URLs.
- `oaap.net.remote-access` spec should include DNS push in WireGuard
  profiles.
- The deployment contract recommends subpath tolerance for new apps
  (SHOULD, not MUST).

## Out of scope

- TLS mechanics per level (belongs to the gateway spec / internet
  profile; LAN TLS story is an open question below).
- Inter-app communication (server-side; not user-facing addressing).

## Open questions

1. Default port range for level 1 (proposal: 8100–8199) and whether
   ports stay stable across reinstalls of the same instance.
2. LAN TLS: self-signed platform CA with device enrollment vs. plain
   HTTP in trusted LAN vs. ACME via public name even for LAN hosts —
   decide with the gateway spec. Weighty data point from the first
   probe deployment: browsers restrict secure-context APIs
   (`crypto.subtle`, clipboard, service workers, WebAuthn) to
   HTTPS/localhost — plain-HTTP LAN operation silently breaks apps
   using them. This pushes strongly toward TLS even in the LAN profile.
3. Name of the private zone (`*.oaap.intern`? configurable?).
