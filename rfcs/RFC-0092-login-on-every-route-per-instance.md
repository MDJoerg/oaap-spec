# RFC-0092: Login on Every Route, per Instance — Tightening an App Without a New Package

- **Status:** **Accepted (2026-11-17)** — Jörg, on the BDT letter of
  2026-11-17: "OK, einverstanden" to the switch per instance; a
  server-side `optional` access mode is **not** part of it. Stage 1
  built in reference 0.1.298 (`oaap.core.gateway` 0.2.23)
- **Date:** 2026-11-18
- **Authors:** Jörg (decision), BDT (the request: access per route
  `public|optional|required`, and tightening an instance in the portal
  without a new package), Claude (design)
- **Depends on:** `oaap.core.gateway` 0.2.22 (default deny, `public`
  exceptions in the manifest, the one site body every entry point
  shares), RFC-0030 §2.15.2 (a rehearsal serves no public route — the
  same rule, already built), RFC-0059 (maintenance, the model for a
  per-instance mode), `oaap.core.identity` 2.3 (`/verify`)
- **Not part of this RFC:** a server-side `optional` mode (an app that
  wants "known if logged in" uses `/auth/whoami` and protected
  sub-paths); loosening — a switch that turns a protected route public
  does not exist and will not

## Summary

An app's manifest may declare routes `public`. The operator of an
instance sometimes wants less: a demo that must not be reachable
anonymously, an app whose public landing page leaks a customer's name.
Today the only way is a new package. This RFC adds one switch per
instance: **login on every route**. While it is on, every route of the
instance asks identity, including those the manifest declares `public`;
a route that already needed roles is unchanged. It is the rehearsal's
rule (RFC-0030 §2.15.2), given a switch.

## 1. The switch

- A field on the instance record, `login_required: {since, by, reason}`
  — absent means off. Never in the manifest: an app cannot loosen it,
  and a package update does not touch it.
- **Effect:** in the one site body every entry point shares (LAN port,
  automatic name, own names, aliases), a route the manifest declares
  `public` gets the forward-auth block of a non-public route with an
  empty role list: any logged-in person of the instance's tenant who may
  use this app, with the instance's visibility groups if it has them.
  The public-route brake (RFC-0010) does not apply to such a route any
  more — it is no longer public.
- **Unchanged:** routes with roles; `/auth/*`; the `/platform/*`
  blocks (the feedback form already asks for a login, the static theme
  and logos stay public); MCP doors that carry their own credential
  (RFC-0073, RFC-0074) — they were never public.
- **The CORS preflight carve-out** (`OPTIONS` without credentials on a
  role-gated route) stays as it is for role-gated routes and is not
  added for the formerly public ones: tightening must not open a method
  that was not open before.
- Enforced where the site is written, never by rewriting the stored
  routes: the stored manifest stays a true copy of what the package
  says.

## 2. Who moves it

- `server_admin` on the machine: `oaap app login-required <instance>
  on|off [--reason TEXT]`.
- In the portal, on the instance's Diagnosis tab next to maintenance:
  whoever may administer the instance (`require_instance_admin` — the
  tenant's `admin`/`tenant_admin` for an instance of their tenant).
  Tightening is always safe, and switching it off only returns to what
  the package itself declares.
- Every change is an entry `instance.login-required` in the tenant's
  log, with who and the reason.
- A rehearsal already behaves this way and does not need the switch;
  moving it on a rehearsal is refused with a sentence.

## 3. What it does not promise

- It is a gate in front of the app, not inside it: an app that serves
  the same content on a protected route to every logged-in member still
  does so.
- Machines that called a public route anonymously (webhooks, a status
  page, a display in a hall) are refused once the switch is on. The
  portal says so next to the button, and the instance's public routes
  are listed there so the operator sees what closes.

## 4. Stages

| Stage | Content |
|---|---|
| 1 | Record field, site body, CLI, portal button, log entry, tests; measured on oaap-test: a public route answers the app before, 303 to the login (browser) / 401 (API key missing) after, and the app again after off |

**Measured 2026-11-18 on oaap-test (0.1.298)** with `wegweiser`, whose
`/` the package declares public: before, the app answers itself (404 —
the short-link service has no front page); switched on, a browser gets
303 to `/auth/login` and a wrong API key 401; switched off, the app
answers again. Two entries `instance.login-required` in the tenant log,
naming the route that closed and the reason. Not measured: the portal
button in a browser (it runs the same host function through the worker).

## Deutsche Zusammenfassung

Je Instanz ein Schalter **„Anmeldung auf allen Routen“**. Ist er an,
fragt jede Route der Instanz die Anmeldung ab, auch die, die das Paket
als öffentlich erklärt; Routen mit Rollen bleiben, wie sie sind. Das ist
die Regel der Generalprobe, jetzt mit Schalter. Setzen dürfen ihn der
Server-Admin per `oaap app login-required <instanz> on|off` und im
Portal (Reiter Diagnose, neben dem Wartungsmodus) jeder, der die Instanz
verwalten darf. Jede Änderung steht im Mandantenlog. Das Paket ändert
sich nicht, ein Update lässt den Schalter stehen. Lockern geht nicht:
Aus heißt nur „wieder so, wie das Paket es sagt“. Maschinen, die eine
öffentliche Route ohne Anmeldung aufgerufen haben, werden danach
abgewiesen; das Portal sagt es neben dem Knopf. Ein serverseitiges
„optional“ gibt es nicht (Jörg, 17.11.).
