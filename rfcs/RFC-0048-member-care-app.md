# RFC-0048: Member Care — A Tenant's Own App for the People in Its Realm

- **Status:** **Proposed (2026-09-30)** — D1–D5 decided by Jörg the same
  day (each as recommended, D1 as "an app in the tenant", D5 as D5-b:
  no role setting by the app in version 1); the measurements in §6 are
  open. Nothing built.
- **Date:** 2026-09-30
- **Authors:** Jörg (the need and the four decisions), Claude (design)
- **Depends on:** RFC-0022 (tenant as boundary), RFC-0027 (API keys and
  machine principals), RFC-0039 (roles, `tenant_admin` grants), RFC-0040
  (the person behind the name), RFC-0041 (external identity providers,
  the connector contract with `never: users`), RFC-0042 (the tenant as a
  place), RFC-0047 (one account everywhere, open)
- **Driver:** On a dedicated multi-tenant node every customer tenant has
  its own realm. Its `tenant_admin` must be able to create, block and
  reset the people of that realm without the operator, and without being
  handed the Keycloak console (heavy, shows more than needed).

## Summary

An app that runs **inside the customer tenant** and lets `tenant_admin`
and `keyuser` care for the members of *that tenant's realm*. The platform
still never creates people; the app does, on the tenant's behalf, under a
service account that reaches exactly one realm and only the user
endpoints.

## 1. Decisions

| | Question | Decided |
|---|---|---|
| **D1** | Where does it run? | **As an app inside the tenant** — one instance per tenant (`mitglieder.<label>.<node>`), isolated from other customers. Not one instance for all tenants. |
| **D2** | How does it reach the realm? | **A service account per tenant realm** with `manage-users` and `view-users` of that realm and nothing else; its secret is the instance's configuration, never a platform-wide credential. |
| **D3** | What does it do in version 1? | List members; create one (a one-time start password, change forced at first login); block and unblock; reset a password; give the OAAP role `user` or `keyuser`. **Not:** groups, self-registration, `tenant_admin`. |
| **D4** | Who may use it? | `tenant_admin` and `keyuser` of the tenant; the gateway enforces the roles at the route, the app checks again. |

## 2. Shape

- Manifest type `wrapped`-independent: a small own service (Python, like
  the other platform apps) with the usual five headers as identity
  (`X-OAAP-User`, `-Roles`, `-Tenant`, ...). It never builds a login
  (Deployment Contract).
- Config keys: `KC_URL` (the realm's provider URL, from the tenant's
  provider object), `KC_REALM`, `KC_CLIENT_ID`, `KC_CLIENT_SECRET`
  (secret). Nothing else about Keycloak is known to the app.
- Every action is written to the tenant's audit log (who, whom, what),
  and the app **never shows or stores** a password after the first display
  of a start password.
- The app cannot see any other realm, other tenants' instances, or the
  master realm. A leaked secret costs one club's member list, not the
  node.

## 3. Rules that are not settings

1. **Realm scope.** The service account's roles are checked at creation;
   the app refuses to start if the account can reach anything outside its
   realm (a self-test against the `master` realm must answer 403).
2. **No deleting people** in version 1: block only. Deleting a person
   removes what the audit trail refers to.
3. **A blocked person is blocked at both ends:** disabled in the realm and,
   through the tenant's user record, unable to sign in to OAAP (RFC-0040
   has no delete; deactivation exists).
4. **Roles come from OAAP, never from the realm.** The app sets roles in
   OAAP only up to `keyuser`; `tenant_admin` and node-wide roles are out
   of reach (RFC-0039).

## 4. What the platform has to provide

- **The service account.** Creating a client in the tenant's realm with
  `realm-management` roles is a new connector job ("member-care
  account"): dry run first, named refusal, never overwrite, version
  pinned as in RFC-0041 §5.3. The connector still has no verb for people.
- **A way for the app to set OAAP roles.** See D5.

## 5. Open decision D5 — how does the app set an OAAP role?

The identity service's internal user API is for the platform, not for
apps. Two ways, to be chosen:

- **D5-a — a machine key of the tenant (RFC-0027)** with the narrow right
  to set `user`/`keyuser` on users of its own tenant. Needs a check that
  a machine principal can carry that right at all.
- **D5-b — no role setting by the app in v1.** The tenant's first-login
  policy gives newcomers `user` (operator sets `role` for tenants whose
  self-registration is off); the app only shows a link to the portal user
  page where `tenant_admin` gives `keyuser`. Smaller, safer, one click
  more for the administrator.

**Decided (2026-09-30): D5-b first**; D5-a when the machine-principal
check succeeds. Consequence for D3: version 1 gives `user` through the
tenant's first-login policy and does not set roles itself.

## 6. Measurements before building

1. Which roles a service account needs to create/enable/disable/reset
   users **only** in a realm the OAAP connector created, and that a
   request to `master` and to another realm answers 403 (same table as
   RFC-0041 §5.3).
2. Whether "reset password" can be done without the administrator ever
   seeing the new password (one-time start password shown once, change at
   first login).
3. Whether the connector's own service account (`create-realm` only) may
   assign the `realm-management` roles to a new client in a realm it
   created. If not, the member-care account is a manual step per tenant
   until the connector gets a wider, named credential.

## 7. Measured 2026-09-30 (Keycloak 26.7.4, throwaway realms)

Script `program/messungen/keycloak-mitglieder-messung.py`, connector
account `oaap-admin` with `create-realm` only:

| Question | Answer |
|---|---|
| Can the connector's account give a new client's service account `manage-users` + `view-users` in a realm it created? | **Yes (204).** No wider credential is needed; the member-care account is one more connector job. |
| The member-care account: list, create, read, set a temporary start password, disable | all work (200/201/200/204/204) |
| User record carries no credentials; credentials list empty | yes |
| Blocked person can no longer sign in | yes (the login page says the account is disabled) |
| Master realm users, other realm's users, own realm's clients, roles, identity providers, creating a client | **403 each** |
| Give a user `realm-admin` (escalation) | **403, refused** |
| Read the own realm's settings | **200 — reachable, but no field with `secret`, `password` or `smtp` in its name; no SMTP block in a fresh realm.** What Keycloak returns once a club has configured SMTP is not measured (Keycloak masks it in general; unverified here). |
| Login with the start password demands a change | **Yes** — the login lands on the change-password step (`password-new`), no token issued. (The first run stopped one redirect short; re-measured.) |

Consequence: the design stands. The realm-scope self-test of §3.1 is
pinned to the measured 403 set above. Still to measure once, at the first
club that configures SMTP: that the settings read shows the SMTP password
masked; until then the app never displays the settings response.

## Zusammenfassung (deutsch)

Eine kleine App **im Kundenmandanten** (eine Instanz je Mandant), mit der
`tenant_admin` und `keyuser` die Menschen im Realm ihres Mandanten pflegen:
auflisten, anlegen (Startpasswort einmalig, Änderung beim ersten Login),
sperren, Passwort zurücksetzen, Rolle `user`/`keyuser` vergeben. Sie
erreicht den Realm über ein Dienstkonto, das nur `manage-users` und
`view-users` dieses einen Realms hat. Die Plattform legt weiterhin nie
selbst Menschen an. Entschieden (30.09.): D1–D4 wie empfohlen. D5 entschieden: D5-b — in Version 1 setzt die App keine OAAP-Rollen
(`user` kommt über die Richtlinie des Mandanten, `keyuser` im Portal).
Offen: drei Messungen am Keycloak vor dem Bau. Nichts gebaut.


