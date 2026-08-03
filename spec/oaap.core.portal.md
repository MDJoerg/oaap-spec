# oaap.core.portal — Web Portal (outline)

- **ID:** `oaap.core.portal`
- **Version:** 0.1.0
- **Maturity:** draft (outline — full specification to follow)
- **Based on:** RFC-0001, RFC-0002

## Purpose

The portal is the web UI where **everything** on the platform is
configured — there is no other administration surface for end users.
It serves the first-run wizard during bootstrap (see `oaap.core.host`)
and afterwards provides administration of users, apps, and platform
settings, scoped by the standard roles (RFC-0002).

## Interface (sketch)

- **First-run wizard**: reachable only with the one-time setup token;
  creates the first admin; disabled permanently afterwards.
- **Administration areas** (0.1 scope): user & role management, app
  overview, platform health of the whole landscape (RFC-0003), basic
  settings.
- **App integration**: installed apps appear in the portal as entry
  points; apps are opened through the gateway, not embedded.
- The portal itself is an app-like consumer of platform capabilities:
  it talks to `oaap.core.identity` for user management and is published
  through `oaap.core.gateway` like any app.

## Dependencies

`oaap.core.gateway`, `oaap.core.identity`

## Maturity

`draft`
