# RFC-0002: Security-First Access Model (Identity, Gateway, Roles)

- **Status:** Draft
- **Date:** 2026-08-03
- **Authors:** Claude (proposal), Jörg (review & decision)
- **Depends on:** RFC-0001 (capability model)

## Summary

Every OAAP platform enforces authentication centrally, at a single HTTP
gateway in front of all apps. No app is reachable without passing the
gateway — even apps that implement no authentication themselves are
protected. The minimum viable setup is one admin user created during
installation. A small set of standard roles is predefined so that simple
scenarios need no custom role modeling.

## Motivation

OAAP targets small businesses without security expertise. "Secure by
Default" therefore cannot rely on every app doing security correctly —
the platform must guarantee a safe baseline regardless of app quality:

- **No loopholes**: there is no way to deploy an app that is accidentally
  open to the network.
- **Minimal burden**: creating one admin user during setup is acceptable
  for everyone; running a full identity server must not be required for
  small installations.
- **Growth path**: the same model must scale up to external identity
  providers and partner access later, without re-architecting.

## Proposal

### Gateway (`oaap.core.gateway`)

A reverse proxy that is the only network entry point to the platform.

- All HTTP(S) traffic to portal and apps passes through it.
- Default policy is **deny**: every route requires an authenticated
  session unless explicitly marked `public` in the app's configuration.
- The gateway enforces authentication and coarse-grained authorization
  (role checks per route) even for apps without built-in auth.
- Apps receive the verified identity and roles via trusted headers or
  tokens; they never see credentials.

### Identity (`oaap.core.identity`)

- Built-in minimal identity provider: local user store, username +
  password, managed in the portal. This is the default and requires no
  additional components.
- Pluggable backends (user choice): an external or co-installed identity
  provider (e.g. Keycloak, LDAP, cloud IdP) can replace or extend the
  built-in store without changing the gateway contract.
- Installation bootstrap: `oaap.core.host` MUST require creating the
  first admin user before the platform accepts any other request.

### Standard roles

Predefined platform roles, available on every OAAP installation:

| Role      | Meaning                                                                  |
| --------- | ------------------------------------------------------------------------ |
| `admin`   | Full platform administration: users, apps, configuration, backup         |
| `keyuser` | Manages configuration and data of assigned apps; first-level user support |
| `user`    | Regular internal user (employees); uses apps assigned to them            |
| `guest`   | Limited, typically temporary access to a specific app function (e.g. a customer signing off a completed installation) |
| `partner` | External partner organization participating in defined processes         |
| `public`  | Unauthenticated access; only valid for routes explicitly marked public — none by default |

- Apps declare in their manifest which roles they support and what each
  role may do inside the app.
- Custom roles remain possible for complex scenarios; the standard roles
  cover the simple ones without any modeling.

### Example mapping (pilot: installation business)

Owner: `admin` + `keyuser` · office staff: `user` · field teams: `user`
(via tablets over VPN) · customer sign-off on site: `guest` ·
partner companies (later): `partner`.

## Consequences

- `oaap.core.gateway` joins the initial capability set (RFC-0001) —
  it is foundational, like identity.
- Apps become simpler: they can rely on authenticated identity being
  present and delegate login entirely to the platform.
- The gateway is a single point of failure and MUST be covered by
  conformance tests early.

## Open questions

1. Token/session mechanism between gateway and apps (e.g. OIDC/JWT vs.
   trusted headers) — proposal to follow with the capability spec.
2. Does `guest` require named accounts, or are scoped invitation links
   (with expiry) sufficient?
3. How fine-grained is per-route role configuration in app manifests?
