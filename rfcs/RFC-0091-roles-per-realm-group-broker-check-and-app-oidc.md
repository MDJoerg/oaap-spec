# RFC-0091: Roles per Realm Group, the Broker Check, and an App as OIDC Client — Partners and Customers with Their Own Identity Provider

- **Status:** **Accepted (2026-11-18)** — Jörg: D1–D7 as recommended.
  Stage 1 (broker check) built in reference 0.1.297, `oaap.core.tenant`
  1.8 §2.10.1, `oaap.core.notifications` 0.11 (`idp.door`), plus a
  daily reading of every tenant realm; stage 0 measurement on oaap-test
  pending; stages 2 and 3 not built
- **Date:** 2026-11-18
- **Authors:** Jörg (the scenario, 2026-11-17: a consulting tenant with
  employees, partners and premium partners/customers who bring their own
  identity provider — Entra, Google — in front of the tenant's Keycloak;
  Forgejo with single sign-on through that Keycloak; roles either
  "imposed" or mapped), Claude (reading of the reference, design)
- **Depends on:** RFC-0041 (external identity providers: a realm per
  tenant, K4 binding and first-login policy, K4b who may move it, K7
  self-registration), RFC-0045 (business authorization: realm group →
  collection, sync at every login, §5.2), RFC-0056 (the realm
  administrator group), RFC-0040 (the person behind the name),
  RFC-0039 (`partner`, `support`), `oaap.core.identity` 0.6.6,
  App Deployment Contract v0.9.1
- **Not part of this RFC:** one account across tenants (RFC-0047 stays
  the place for a shared Forgejo serving many tenants); OAAP *creating*
  identity brokers in a realm; a second factor for the built-in provider
  (internet hardening, RFC-0041 K7).

## Summary

Keycloak can already put several foreign identity providers in front of
one tenant's realm ("identity brokering"): employees through the
company's Entra, a partner through theirs, a customer through Google.
OAAP binds every login by `(provider, sub)` and never reads a role from
an assertion. Three things are missing for Jörg's scenario:

1. **A platform role per group.** Today a first login yields *one*
   default role for everybody (`first_login: role`), and a realm group
   can only become a visibility group or a business collection. A
   partner and an employee arriving through the same realm cannot get
   different platform roles without a human editing each person.
2. **The broker check.** The rule "a granting first-login policy
   together with self-registration needs a reason" (K7) looks at
   `registrationAllowed` only. A broker without a domain restriction
   (Google, Entra `common`) lets anybody with such an account create a
   realm user — self-registration by another name — and the rule does
   not see it.
3. **An app as its own OIDC client.** Forgejo must authenticate Git over
   HTTPS itself and therefore cannot sit behind the portal login. Its
   store package is old (manifest 0.1) and has no way to sign in through
   the tenant's realm.

The proposal: a **written mapping realm group → platform role**, limited
to `guest`, `partner` and `user`, set only by `server_admin` and applied
at every login like RFC-0045's sync; a **read-only broker check** that
treats every open broker as an open door; and a manifest declaration
with which an app **asks the platform for a client in the tenant's
realm**, first used by a renewed Forgejo package.

## 1. Facts (read in the reference on 2026-11-18)

| What | Where | Today |
|---|---|---|
| First-login policy | `services/idp.py` `policy_of`, `first_login_grant` | `eingang` (default) · `role` (ONE default role) · `groups` (one default role + realm group → visibility group) |
| Grantable at first login | `GRANTABLE_AT_FIRST_LOGIN` | `admin, keyuser, user, guest, partner`; never `server_admin, support, tenant_admin` |
| When the policy acts | `identity/app.py` provider login | only at the **first** login; later logins update name, e-mail, propagation — never roles |
| Realm group → business collection | `_authz_sync_login`, RFC-0045 §5.2 | at **every** login, adds and ends assignments, never a platform role |
| Who moves the policy | `policy_target` (K4b) | `server_admin` only; every move is an entry in that tenant's log |
| Self-registration rule | `policy_refusal`, `self_registration_open` | judged on `registrationAllowed` (record or realm reading) |
| Identity brokers | connector table `CONNECTOR_KINDS["keycloak"]["paths"]` | **no path**; nothing reads `identity-provider/instances` |
| Realm administrator group | RFC-0056, `admin_group` | `manage-users, view-users, query-users, query-groups` — can put people into groups, cannot add a broker |
| Groups in the token | client mapper `oaap-groups` | group **paths**, by the client OAAP made |
| Apps with their own OIDC client | manifest, connector | none; the connector makes exactly one client per tenant — the gateway's |
| Forgejo package | `oaap-store/apps/forgejo` | manifest 0.1, Forgejo 11, `/` public, registration off, SSH off, no OIDC source; an OIDC source only by hand (`forgejo admin auth add-oauth` in the container) |

Two consequences matter for the design:

- The realm administrator (RFC-0056) **can change group membership**.
  Any mapping from group to role therefore hands *the tenant's own
  administrator* the power to grant that role. That is acceptable for
  roles a tenant may grant anyway and not for more.
- RFC-0041 K4 contains the sentence *"A realm group never becomes an
  OAAP role."* Point 1 of this RFC reopens it; that is D1, and it is
  Jörg's.

## 2. Roles per realm group

### 2.1 The mapping

A fourth key in the tenant's identity policy, beside `group_map`
(visibility groups):

```yaml
idp_policy:
  first_login: groups
  default_role: guest
  role_map:                     # realm group path → platform role
    mitarbeitende: user
    partner: partner
    partner/premium: partner
    kunden/premium: guest
```

- Values are limited to **`guest`, `partner`, `user`** (D2). `keyuser`
  and `admin` stay assigned in OAAP by a person, because the realm
  administrator can move people between groups (§1).
- Written only by `server_admin` (K4b, unchanged), with a log entry in
  the tenant's log naming every line that changed.
- An unmapped group grants nothing; the mapping is by path, as the token
  carries paths (RFC-0045 stage 3 measurement).
- A provider's own role claims (`realm_access.roles`, `roles`) stay
  unread. The sentence "a provider's claims never become OAAP roles"
  holds: the *operator's* mapping becomes the role, not the claim.

### 2.2 When it acts

At **every** provider login (D3), in the same place and with the same
shape as `_authz_sync_login`:

- Roles that came from the mapping carry their origin
  (`role_source: {"partner": "group:partner"}`). Only those are added
  or ended by the sync; a role a person was given by hand is never
  touched.
- A person removed from the group loses the mapped role at their next
  login, and existing sessions keep it until then — the same latency
  RFC-0045 accepts for collections. Ending the session at once remains
  the job of deactivation.
- If no role is left, the person stays — bound, without rights, visible
  in the Eingang. Nothing is deleted.
- Every change is an `user.idp-role-sync` entry in the tenant's log
  ("gegeben: partner (Gruppe partner)", "beendet: …").

### 2.3 How groups get there per provider

Not OAAP's code, but the documented path the scenario needs: in the
realm, each broker gets a Keycloak **identity provider mapper** of type
"Hardcoded Group" (everybody arriving through *Partner-Entra* lands in
`partner`) or a claim-to-group mapper (Entra group → realm group). The
token then carries the group path, and §2.1 maps it. Business rights
follow the same group through RFC-0045 collections. One group, two
consequences — a platform role and business collections — both written
by OAAP's side, never asserted by the partner.

## 3. The broker check

### 3.1 What is read

A new **read-only** path in the connector table,
`identity_providers: /admin/realms/{space}/identity-provider/instances`,
read together with the K7 switches by `read_settings` and stored in the
realm reading (`realm.brokers`). Nothing is written; `never` stays as
it is for brokers (D5).

Per broker OAAP keeps: alias, product (`providerId`), enabled, and the
three fields that decide how open it is.

### 3.2 Open or closed

| Broker | Closed when | Otherwise |
|---|---|---|
| `google` | `hostedDomain` set | open — any Google account |
| `microsoft` / Entra via `oidc` | issuer or authorization URL names one directory id | open for `common`, `organizations`, `consumers` |
| `github`, `facebook`, … social | never | open |
| other `oidc` / `saml` | operator acknowledges it as closed, with a reason | open |

"Closed" means *the provider's own population is limited*, not that
everybody in it is welcome — a closed Entra broker still admits every
employee of that directory, which is why §2.3 routes them to a group
rather than to a role directly.

### 3.3 What follows

- `self_registration_open(policy)` becomes `open_doors(policy)` and
  returns a list: `registration` and one entry per open broker. The K7
  refusal in `policy_refusal` reads the list: a granting policy
  (`role`/`groups`, and now any `role_map` line) with **any** open door
  needs a reason, and the refusal names the door
  ("the broker 'google' admits any Google account").
- Two broker settings are reported as **warnings** in the portal and in
  `oaap idp settings`, because they undermine K4 inside the realm,
  before OAAP sees anything: `trustEmail: true` and a first-broker-login
  flow that links an existing realm user by e-mail without
  re-authentication. OAAP binds to the realm's `sub`; if the realm
  itself merges a foreign account into an existing user by e-mail, that
  is account takeover by collision one step earlier.
- A broker that appears or opens between two readings is a drift line
  (`drift_lines`) and lands in the weekly report (RFC-0083).
- The portal's Identity card for the tenant lists the brokers with
  "offen/geschlossen" — the tenant_admin sees it, only server_admin
  changes the policy (K4b).

## 4. An app as OIDC client of the tenant's realm

### 4.1 Why not the portal login

Forgejo answers `git clone`/`git push` over HTTPS with its own tokens; a
browser redirect to the portal cannot happen there. That is why its `/`
route is a reasoned `public` exception. Reverse-proxy authentication
(Forgejo trusting `X-OAAP-User`) would need protected routes for the web
UI and public ones for Git on the same paths — not separable. So
Forgejo signs in **itself**, against the tenant's realm.

### 4.2 The declaration

A manifest key (manifest version to be fixed when built):

```yaml
identity:
  oidc_client:
    redirect_paths: [/user/oauth2/oaap/callback]
    groups_claim: true          # add the oaap-groups mapper
```

On `app install`/`update` in a tenant whose provider is a managed realm,
the platform:

1. makes a confidential client `oaap-<instance>` in the tenant's realm
   with exactly those redirect URIs under the instance's names
   (RFC-0018) — the same connector verb that makes the gateway's client
   today, so no new class of write;
2. hands the app `OAAP_OIDC_ISSUER`, `OAAP_OIDC_CLIENT_ID` and the
   secret as a generated value (RFC-0079 `generate`), never in the
   catalogue or in Git;
3. disables the client on `app remove`/`purge` (the existing disable
   path for clients) and re-points the redirect URIs when names change.

A tenant without a managed realm gets no client, and the app falls back
to its own accounts. The app never receives an admin credential of the
realm.

### 4.3 Roles inside the app

Forgejo's own rights (site admin, restricted user) are the app's
business, not platform roles: Forgejo can read the `groups` claim
(`--group-claim-name groups --admin-group forgejo-admins
--restricted-group partner`). K4 is about OAAP's roles; an app reading a
group for its own purposes is RFC-0045's territory and stays allowed.

### 4.4 The Forgejo package

Renewed in `oaap-store` (D7): current Forgejo LTS at build time, current
manifest, `identity.oidc_client`, an entrypoint step that runs
`forgejo admin auth add-oauth`/`update-oauth` idempotently from the
three variables, registration closed except through the OIDC source
(`ALLOW_ONLY_EXTERNAL_REGISTRATION`), local accounts kept for the
initial admin. Without a realm everything stays as today.

## 5. Stages

| Stage | Content | Needs |
|---|---|---|
| 0 | Measure on oaap-test: a second realm as "foreign" OIDC broker in front of a tenant realm; does the connector credential read `identity-provider/instances` (made realm and adopted realm); which fields come back; does a Hardcoded-Group mapper reach the `groups` claim; what `trustEmail` and the default first-broker-login flow do with an existing e-mail | nothing decided |
| 1 | Broker check §3 — read, `open_doors`, refusal, warnings, portal, weekly report | D4, D5 |
| 2 | Role mapping §2 — policy key, CLI/portal for server_admin, sync at login, log | D1–D3 |
| 3 | App client §4.2 + Forgejo package §4.4, measured with a login through the foreign broker into Forgejo | D6, D7 |

Stage 1 closes a gap that exists today and can be built without stage 2.

**Measured 2026-11-18 on oaap-test (Keycloak 26.7.4), stage 0 part 1
and stage 1 end to end:**

- The fields are as assumed: `providerId`, `enabled`, `trustEmail`,
  `config.hostedDomain` (google), `config.tenant` (microsoft),
  `config.issuer`/`authorizationUrl`/`tokenUrl` (oidc, keycloak-oidc).
  The client secret comes back masked.
- A broker that follows the realm's default carries **no**
  `firstBrokerLoginFlowAlias`; the flow in force is the realm's
  `firstBrokerLoginFlow`. The reading uses the broker's value, else the
  realm's.
- The connector credential (service account with `create-realm`) reads
  the brokers of a realm **it made** (200) and gets **403** on a realm it
  did not make. That is recorded as *unknown*, never as *none*; an
  adopted realm needs `view-identity-providers` for the service account
  before its brokers can be judged.
- End to end with a Google broker without a domain added to the tenant
  realm `vuebung` (policy `role` → `user`, no reason): the reading files
  `tenant.idp-door` in the tenant's log and queues one `idp.door`; the
  policy view shows the broker OPEN and the disagreement; a new role
  without a reason is refused naming the broker; an acknowledgement
  without a reason is refused, with one it closes the door. Broker
  removed and acknowledgement withdrawn afterwards.
- Not yet measured (stages 2/3): a login through a foreign broker, the
  Hardcoded-Group mapper reaching the `groups` claim, and what
  `trustEmail` with the default first-broker-login flow does with an
  existing e-mail. The realms `rfc0091probe` and `rfc0091partner` stay
  on oaap-test for that.

## 6. Decisions for Jörg

- **D1 — Reopen K4's sentence?** A realm group may become a platform
  role through a mapping the operator writes. *Recommendation: yes* —
  the claim still never becomes a role, the operator's line does; that
  is the same trust as `group_map` and RFC-0045 collections.
- **D2 — Which roles?** *Recommendation: `guest`, `partner`, `user`.*
  The realm administrator can move people between groups, so a mapping
  to `keyuser`/`admin` would let the tenant's own administrator make
  OAAP admins. Those stay assigned by a person in OAAP.
- **D3 — First login only, or every login?** *Recommendation: every
  login*, only for roles the mapping gave (origin recorded), never
  touching hand-given roles. Otherwise a partner promoted or dropped in
  the realm keeps the wrong role forever.
- **D4 — Brokers count as doors?** *Recommendation: yes*, every open
  broker counts like self-registration for the K7 refusal; closed ones
  (domain or directory restricted, or acknowledged with a reason) do
  not.
- **D5 — Who sets up brokers?** *Recommendation: the operator in the
  Keycloak console*, as today; OAAP reads and judges, it does not write
  brokers. The realm administrator group (RFC-0056) gets no
  `manage-identity-providers` — adding a door to a tenant on a shared
  node is K4b's operator switch.
- **D6 — App as its own OIDC client of the tenant realm?**
  *Recommendation: yes*, via the manifest declaration §4.2, for apps
  that must authenticate non-browser clients themselves (Forgejo
  first). It is a reasoned exception to "apps never build a login"
  (RFC-0040 §6) in the same way the `public` route is a reasoned
  exception: the login page is the realm's, not the app's.
- **D7 — Renew the Forgejo package now?** *Recommendation: yes, in stage
  3*, together with the app client; the one-tenant case first, the
  shared Forgejo across tenants stays RFC-0047.

## Deutsche Zusammenfassung

**Worum es geht:** Jörgs Szenario vom 17.11. — ein Beratungs-Mandant mit
Mitarbeitenden, Partnern und Premium-Partnern/Kunden, die ihren eigenen
Anmeldedienst (Entra, Google) mitbringen. Keycloak kann das heute schon
(„Identity Brokering“ im Realm des Mandanten). OAAP fehlen drei Dinge:

1. **Rolle je Gruppe.** Heute bekommt jede Erstanmeldung *eine*
   Standardrolle. Partner und Mitarbeitende lassen sich nicht
   unterschiedlich einstufen, ohne jede Person einzeln anzufassen.
   Vorschlag: eine vom server_admin geschriebene Tabelle
   „Realm-Gruppe → Plattformrolle“, nur `guest`, `partner`, `user`,
   angewendet bei **jeder** Anmeldung (wie die fachlichen Rechte aus
   RFC-0045). Von Hand vergebene Rollen bleiben unberührt; was aus der
   Tabelle kam, endet, wenn die Gruppe wegfällt.
2. **Broker-Prüfung.** Die Regel „vergebende Erstanmeldung plus
   Selbstregistrierung nur mit Begründung“ sieht heute nur den
   Registrierungs-Schalter. Ein Google-Broker ohne Domänenbeschränkung
   ist aber faktisch Selbstregistrierung. Vorschlag: OAAP liest die
   Broker des Realms (nur lesen), stuft sie offen/geschlossen ein, zählt
   offene wie Selbstregistrierung und warnt bei `trustEmail` und
   Konto-Verknüpfung per E-Mail (Kontoübernahme im Realm, bevor OAAP
   etwas sieht). Neue oder geöffnete Broker landen im Wochenbericht.
3. **App als eigener OIDC-Client.** Forgejo muss Git über HTTPS selbst
   prüfen und kann nicht hinter dem Portal-Login sitzen. Vorschlag: Ein
   Manifest-Eintrag lässt die Plattform einen Client im Realm des
   Mandanten anlegen und der App Aussteller, Client-ID und Geheimnis
   geben. Das Forgejo-Paket wird erneuert und meldet sich darüber an;
   Forgejo-interne Rechte (Admin, eingeschränkt) liest Forgejo selbst
   aus der Gruppe.

**Entscheidungen D1–D7** (alle mit Empfehlung „ja“ bzw. wie oben):
K4-Satz „Realm-Gruppe wird nie Rolle“ öffnen (D1), nur
guest/partner/user (D2), bei jeder Anmeldung (D3), Broker zählen als Tür
(D4), Broker richtet der Betreiber in der Keycloak-Konsole ein, OAAP
liest nur (D5), App als OIDC-Client per Manifest (D6), Forgejo-Paket in
Stufe 3 erneuern (D7).

**Stufen:** 0 Messung auf oaap-test (zweiter Realm als „fremder“ IdP),
1 Broker-Prüfung (schließt eine heute bestehende Lücke, braucht nur
D4/D5), 2 Rollen je Gruppe, 3 App-Client + Forgejo. Gebaut ist nichts.
