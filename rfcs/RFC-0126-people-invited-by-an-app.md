# RFC-0126: People Invited by an App — an App Asks, the Platform Creates the Login and Sends the Mail

- **Status:** **Accepted (2026-11-24)** — D1–D10 decided one by one the same
  day, each as recommended (§12). Nothing built. **Stage 0 measured on
  `oaap-test` the same day (§1.5).** The facts in §1 were read the same day in
  `oaap.core.identity`, RFC-0041, RFC-0055, RFC-0072, RFC-0091,
  `oaap.apps.runtime` (§2.24/§2.25 cases) and reference 0.1.359
  (`services/idp_admin.py`, `services/identity/app.py`); what was **not** read or
  measured is in §1.4, and stage 0 (§11) answers it first.
- **Date:** 2026-11-24
- **Authors:** Jörg (the need, RFC-0123 D8/D22: a customer's contact is a node,
  a login and responsibilities; "an app asks, the platform creates the user and
  sends a confirmation mail"), Claude (facts, design)
- **Follows:** RFC-0123 D22 (this RFC), RFC-0123 S7 (no app can create a user,
  no confirmation mail anywhere)
- **Depends on:** RFC-0040 (a user's UUID), RFC-0041 (a realm per tenant, K3
  "managing is not owning", K4 binding to `(provider, sub)`), RFC-0072 (mail
  from the node and per tenant, written into the realm), RFC-0091 (roles from
  realm groups, synced at every login)
- **Related:** RFC-0045 (business authorization — the app's own roles),
  RFC-0055 (the invitation link for a tenant build — a different thing, §1.1
  F7), RFC-0090 (erasure in the twin), RFC-0123 (the first consumer, `bestand`),
  I-69 (events — how the app learns that a person confirmed)
- **Changes (when accepted):** `oaap.core.identity` (invitations, a record made
  before the first login, the people an app invited), the Keycloak connector
  (`users` leaves `never` for a narrow, guarded verb — §3), `oaap.apps.runtime`
  (a manifest capability `people: {invite: true}`, a key and a URL like
  `cases`), `oaap.core.gateway` (the block `/platform/people/` per site),
  `oaap.core.tenant` (the switch per tenant)
- **Not part of this RFC:**
  - **Self-registration** (RFC-0041 K7, exists as a tenant switch). Here a
    person never registers themself; an app that knows them invites them.
  - **Staff and administrators.** An app invites only people with no platform
    authority (D3). The first administrator of a tenant (RFC-0072's open "b")
    may later use the same mechanism, by the operator, not by an app.
  - **Deleting a person.** An app can lock a login, never delete it (D6);
    erasure is the tenant admin's and RFC-0090's.
  - **Mail sent by apps in general** (RFC-0072 stage 3). Only the invitation
    and the realm's own mails are sent here, by Keycloak.

## Summary

RFC-0123's customer portal `bestand` needs what no app can do today: when an
account administrator orders the article "contact", a login must come into
being for a person outside the provider's company, the person must confirm
their address and set a password, and `bestand` must link that login to the
contact's node and responsibilities. Stage 0 of RFC-0123 found every piece
missing (S7), and found one decision standing against it: the Keycloak
connector names `users` under **`never`** — "OAAP does not create people in
somebody's realm and is not going to start" (RFC-0041 K3.3).

That rule was written for a realm that belongs to somebody else — the club's
member realm, a company's staff directory. It was right, and this RFC keeps it
for every realm that does not say otherwise. What it adds is narrow:

1. **An app declares** `people: {invite: true}` and gets a key and a URL, like
   `cases` (D1).
2. **The tenant decides** whether apps may invite at all; off by default, and a
   realm OAAP does not provision can never be opened (D2).
3. **An invited person gets no platform authority** — role `partner` at most,
   what they may do is the app's business (D3).
4. **The platform creates the user in the realm** with the required actions
   "verify address" and "set password", so nobody logs in before both are
   done, and has **Keycloak send the mail** (verify address, set
   password) through the tenant's mailbox (D4, D5).
5. **The platform record exists at once**, bound to `(provider, sub)` before
   the first login, so the app gets the person's UUID in the same answer (D7).
6. **An app touches only the people it invited** — resend, lock, unlock, read
   status; never delete, never change another's user (D6).
7. **Never matched by e-mail**: an address that already has a user is refused,
   not linked (D8).

## 1. Facts

### 1.1 Read 2026-11-24

| # | Fact | Where |
|---|---|---|
| F1 | The Keycloak connector's `never` is exactly `("users",)`: OAAP "does not create, change or remove people in somebody's realm" — "that is the club's, and K3.3 is the whole reason this file has no DELETE". The connector reads `users/{uuid}` and `users/count`, never writes a user. Methods GET, POST, PUT only. | reference `services/idp_admin.py:36-39`, `:259-291` |
| F2 | Identity keeps its own store; a login through a provider creates a local record **at the first login**, bound one-to-one to `(provider, sub)`; matching by e-mail or user name is forbidden. | RFC-0041 K4 (`:200-232`); `identity/app.py` `find_binding` |
| F3 | Per tenant, `first_login` is `eingang` (default: no right, shown in the inbox), `role` or `groups`; only `server_admin` moves it. | RFC-0041 K4/K4b |
| F4 | `POST /internal/users` exists and accepts only the portal (`X-OAAP-Internal-Key`); apps no longer reach identity over the network (RFC-0016). `oaap user add` writes identity's own store. | `identity/app.py:3136-3150`, `:3751`; `oaap.core.identity` §2 |
| F5 | Roles: `server_admin, tenant_admin, support, admin, keyuser, user, guest, partner`. **`partner` carries no platform authority at all** — the app-facing classification of RFC-0002. | `oaap.core.identity` §2.1 (`:80-90`) |
| F6 | Identity "adds no e-mail sending and no verification mail"; the built-in login has no password reset by mail. `VERIFY_EMAIL` / `execute-actions` appear nowhere in the code. | `oaap.core.identity:162`; grep 2026-11-24 |
| F7 | RFC-0055's invitation link invites a **prospect for a tenant build**, not a user; no mail is sent, the link is shown once. | RFC-0055 `:370-388` |
| F8 | Mail: one SMTP mailbox per node (stage 1) and one per tenant (stage 2, page "Nachrichten"), written into the realm as `smtpServer`; Keycloak's "update your account" mail was measured arriving. RFC-0072 left open "OAAP creating the first administrator and sending the set-password mail". | RFC-0072 `:12-14`, `:163-176`, `:290-304` |
| F9 | Realm groups map to `guest · partner · user` only, synced at **every** login (`role_source`). | RFC-0091 `:94-133` |
| F10 | The capability pattern: `cases: {submit: true}` gives the instance `OAAP_CASES_KEY` (principal `instance:<name>`, scoped to the pseudo-instance `oaap.cases.submit:<name>`) and `OAAP_CASES_URL`; the gateway lets that key through only in `/platform/cases/submit` of the instance's own site; made once, never for a probe install, follows the instance's lifecycle. A person cannot mint a key with such a dotted scope. | `oaap.apps.runtime` §2.24/§2.25; `oaap.core.gateway`; `oaap.core.identity` 0.6.11 |
| F11 | A new realm starts with `registrationAllowed: false`; the only required-action alias in the code is `CONFIGURE_TOTP`. | `idp_admin.py:212`, `:830-844` |

### 1.2 What follows

- The **mechanism exists in pieces**: a realm OAAP provisions (F1), its mail
  (F8), a binding at first login (F2), a key pattern for a platform door
  (F10). What is missing is the one verb and the order of steps.
- The **rule against it is a principle, not an accident** (F1). It cannot be
  dropped; it must be narrowed to "people OAAP created, in a realm OAAP
  provisions, for a tenant that allowed it".
- The **right role exists** (F5): `partner`, no platform authority. RFC-0123
  §9.1 says `user`; with D3 it becomes `partner`, and D21 of RFC-0123 (the
  twin's mark) stays as the second wall.

### 1.3 What the order of steps must solve

The first login creates the platform record (F2). An app that invites a person
needs the person's identity **before** that login — to link the contact node.
Since OAAP creates the realm user, it knows the `sub` (the Keycloak user id) at
once, and can make the platform record bound to `(provider, sub)` right then
(D7). The first login then finds the binding instead of creating one.

### 1.4 Not read, not measured

- Whether a `partner` reaches an app through the gateway and what it sees in
  the portal (the start page, the launchpad, the help) — stage 0.
- Keycloak's `execute-actions-email` with `VERIFY_EMAIL` + `UPDATE_PASSWORD` on
  the pinned version: the link's lifespan, the language, what the person sees.
- Whether the realm allows two users with one address
  (`duplicateEmailsAllowed` is set by RFC-0072; not read which way).
- Tenants without Keycloak (built-in login): there is no mail at all (F6). Not
  designed here beyond D9.

### 1.5 Measured 2026-11-24 on `oaap-test` (stage 0)

Reference 0.1.365, Keycloak 26.7.4 (the pinned version, connector `auth`).
The tenant realm `vuebung` was only **read**. Everything that writes ran in a
**throwaway realm** `rfc126probe`, made with the node's own connector
credential, whose SMTP server was a small sink container on the Keycloak
instance's network — **no mail left the node**. Afterwards the realm was
deleted and the sink stopped. The `partner` part ran in the throwaway tenant
`s0` with a throwaway person (built-in login, a generated password never
printed) and two throwaway apps, from outside through the edge — the way an
invited person comes; all removed afterwards.

| # | What | Result |
|---|---|---|
| K1 | `vuebung` (and a new realm's defaults) | `duplicateEmailsAllowed: false`, `loginWithEmailAllowed: true`, `actionTokenGeneratedByAdminLifespan` 43,200 s (12 h), languages `de`, `en`, default `de`; required actions `VERIFY_EMAIL`, `UPDATE_PASSWORD` enabled. **`resetPasswordAllowed: false`** — "forgot password" is **off** in a realm OAAP provisions |
| K2 | Create a user `enabled`, `emailVerified: false`, required actions `VERIFY_EMAIL` + `UPDATE_PASSWORD`, attribute `oaap_invited_by` | `201` — but **the attribute is dropped without a word**: Keycloak 26's declarative user profile keeps only declared attributes (`username`, `email`, `firstName`, `lastName`; `unmanagedAttributePolicy` unset). With the policy `ADMIN_EDIT` the attribute is kept; a group `oaap-invited/probe` works as a marker either way |
| K3 | `execute-actions-email` with both actions, `lifespan` 72 h | `204`; the mail (German, the user's `locale`): "Aktualisieren Sie Ihr Konto", from the realm's sender, naming the account, both actions and the validity; the link's token runs exactly 259,200 s |
| K4 | Following the link | "Führen Sie die folgende(n) Aktion(en) aus" (German) → "Passwort aktualisieren" → "Konto aktualisiert". Afterwards `emailVerified: true`, no required action left — opening the link **is** the address check |
| K5 | The same link again · a link with `lifespan` 30 s after 45 s | `400` "Die Aktion ist nicht mehr gültig." · `400` "Die Aktion ist nicht mehr gültig." — single use, and it expires |
| K6 | A second user with the same address · in other case (`Invited1@Example.TEST`) · another address | `409` "User exists with same email" · `409` · `201` |
| M1 | A person with role `partner` (built-in login) | logs in (the forced first password change works), sees the tenant's start page; the launchpad shows **only** the app whose route allows `partner`; that app answers `200` and gets `X-OAAP-User`, `X-OAAP-Roles: partner`, `X-OAAP-User-Id` (the UUID) and the signed assertion; an app allowing only `user` answers `403`; the portal's "Zugänge" and "Benutzer" `403` |

**What follows for stage 1.**

- **The marker needs the user profile.** The provisioning plan declares
  `oaap_invited_by` in the realm's user profile, viewable and editable by
  administrators only (not by the user), and adds the group
  `oaap-invited/<instance>`; the verb `invited_users` checks both. Without
  that, §3's marker silently does not exist (K2).
- **"Forgot password" is off** in the realms OAAP makes (K1). §6's last line
  ("works afterwards by the realm's own flow") is not true today. Stage 1
  switches `resetPasswordAllowed` on for a tenant whose switch
  `people.invite` is on — or says plainly that an invited person who forgets
  the password needs `resend`.
- **One link does both** (K4): the person never sees a separate "confirm
  address" step; the status `active` follows the first login, `emailVerified`
  already comes with the click.
- **Duplicates are refused by Keycloak itself** (K6), case-insensitively;
  D8's `409` can pass Keycloak's answer through. Unicode variants not measured.
- **`partner` works through the gateway as designed** (M1): only apps that
  name the role reach the person; the identity headers carry the UUID.

**Not measured:** the mail through the tenant's real mailbox (a sink stood
in; RFC-0072 measured that path for Keycloak's "update your account" mail);
the look of the mail (the realm's theme); a `partner` coming through a
Keycloak login and RFC-0091's group mapping (the built-in login stood in —
the gateway's part is the same); Unicode variants of an address.

## 2. The way, step by step

```
bestand ──POST /platform/people/invite──▶ gateway (key, own site) ──▶ identity
   {email, name, language, ref}                                      │
                                                                     │ 1 checks: capability, tenant switch, realm managed,
                                                                     │   address free, limits
                                                                     │ 2 Keycloak: create user (enabled, email_verified=false,
                                                                     │   required actions VERIFY_EMAIL, UPDATE_PASSWORD),
                                                                     │   attribute oaap_invited_by=instance:<name>,
                                                                     │   group oaap-invited/<instance>
                                                                     │ 3 platform record bound to (provider, sub),
                                                                     │   role partner, invited_by, ref
                                                                     │ 4 Keycloak: execute-actions-email (tenant mailbox)
   ◀──── 201 {user_id, status: "invited"} ───────────────────────────┘
person: mail → confirm address, set password → first login finds the binding
bestand: status "active" (read, or later an event, I-69)
```

## 3. Narrowing `never: users` (D2)

The connector gets **one** new verb, `invited_users`, and `users` stays in
`never` for everything else. The verb may:

- **create** a user — only in a realm OAAP provisioned for this tenant
  (RFC-0041 K3), only with the marker attribute `oaap_invited_by` and the group
  `oaap-invited/<instance>`;
- **send** the execute-actions mail for such a user;
- **enable / disable** such a user (lock and unlock);
- **read** such a user's state (required actions left, enabled, last login).

It may never touch a user without the marker, never change a user's name,
address or password, never delete (still no DELETE, F1). A realm OAAP does not
provision — a foreign IdP the tenant only connected — has no such verb at all.

**The switch is the tenant's** (`people.invite: off · on`), off by default.
Who flips it is D2: the recommendation is **`server_admin`**, like
`first_login` and self-registration (F3, RFC-0041 K7), because it changes who
can log in to the tenant at all.

## 4. The manifest and the door (D1)

```yaml
people:
  invite: true          # this app may invite people without platform authority
```

The instance gets `OAAP_PEOPLE_KEY` (principal `instance:<name>`, scoped to
`oaap.people.invite:<name>`) and `OAAP_PEOPLE_URL`
(`http://<gateway>:<port>/platform/people/`), exactly like `cases` (F10). The
gateway passes the key only under `/platform/people/` of the instance's own
site. Never for a probe install.

| Call | Does |
|---|---|
| `POST invite` `{email, name?, language?, ref?}` | §2; answers `{user_id, status}`; `ref` is the app's own key for the person (e.g. the contact node), stored, returned on reads |
| `POST {user_id}/resend` | sends the mail again (limited, D5) |
| `POST {user_id}/lock` · `unlock` | disables / enables the login |
| `GET {user_id}` · `GET ?ref=` · `GET` | status of the people **this instance** invited: `invited · active · locked · expired`, last login |

Every call is in the tenant's audit log with the instance, and visible to the
tenant admin on a portal page "Eingeladene Personen" per app (D10).

## 5. The person (D3, D7, D8)

- **Role `partner`, nothing else** (D3). The app decides inside itself what the
  person may do (its own roles, RFC-0045 role templates or its own model, like
  `bestand`'s responsibilities). An app can never ask for `user` or more; a
  tenant admin may raise a person later by hand, which ends the app's hold on
  them (the record loses `invited_by`).
- **The record exists from the invitation** (D7): UUID, `(provider, sub)`
  binding, `email_verified: false`, `invited_by`, `ref`. The first login does
  not create a second one; `first_login` (F3) does not apply to an invited
  person — the invitation already is the decision that `eingang` stands for.
- **The address is never a key** (D8, F2): an address that already belongs to a
  user in the realm, or to a platform record, is refused with `409 exists`. The
  app tells its user to ask the tenant admin; linking an existing person to an
  app is a tenant admin's act, later.
- **Role sync** (F9): an invited person sits in the group `oaap-invited/<instance>`;
  RFC-0091's mapping may map it to `partner`, never higher — the mapping's
  allowed set already says so.

## 6. The mail (D4, D5)

- **Keycloak sends it** (`execute-actions-email`, actions `VERIFY_EMAIL` and
  `UPDATE_PASSWORD`), through the **tenant's mailbox** (RFC-0072 stage 2), or
  the node's if the tenant has none. Identity sends nothing itself (F6 stays
  true).
- The link is valid for a lifespan the tenant sets (default 72 hours); after it
  the status is `expired`, and `resend` makes a new one.
- **Limits** (D5): per instance per hour and per day, per address per day; a
  limit reached answers `429` and shows on the portal page.
- Language from the call, else the tenant's. Text and look are the realm's
  theme (RFC-0042 colours where the theme takes them) — not designed here.
- Forgot password works afterwards by the realm's own flow (RFC-0072).

## 7. How the app learns that the person confirmed (D7)

The app reads the status (`GET ?ref=`) — allowed here, unlike cases (RFC-0123
S8), because the key may read **its own** invitations. When the events
capability (I-69) exists, identity publishes `person.invited`,
`person.activated`, `person.locked` in its envelope, and the app subscribes;
reading stays as the fallback.

## 8. Tenants without Keycloak (D9)

The built-in login has no mail (F6). Recommendation: **this RFC needs a realm**;
a tenant that wants apps to invite people gets one (RFC-0041 provisions it).
Not chosen for now: a set-password mail from identity itself through the
tenant's mailbox — a second mail path next to Keycloak's, to be its own
decision if a tenant without Keycloak ever needs it.

## 9. RFC-0123 afterwards

- §9.1: the contact's login gets role **`partner`**, not `user`.
- The article "Ansprechpartner" calls `invite` with the contact node's id as
  `ref`; the node stays `in_work` until the status is `active`, then
  `handed_over`; locking a contact calls `lock`.
- D21 (the twin's mark) stays: two walls, not one.

## 10. Security requirements (proposed)

1. A key of one instance reaches only `/platform/people/` of its own site and
   only the people that instance invited; tested with a second instance's key.
2. No call can create a user with any role but `partner`, in a realm OAAP does
   not provision, or in a tenant whose switch is off; each tested.
3. The connector cannot change, read or lock a realm user without
   `oaap_invited_by` of that instance; tested against a user made by hand.
4. An existing address is refused, never linked; tested with case and Unicode
   variants of the address.
5. Limits hold; a flood answers `429` without sending mail.
6. The invitation link is single-use and expires; tested after the lifespan.
7. Every call is in the audit log with instance, address (hashed in the log if
   the tenant's retention says so) and result.

## 11. Stages

| Stage | What | Measured by |
|---|---|---|
| **0** | Measure on `oaap-test`: a `partner` through the gateway into an app and in the portal; `execute-actions-email` with both actions on the pinned Keycloak (mail, link, lifespan, language); `duplicateEmailsAllowed`. — **measured 2026-11-24, §1.5** | §1.4 answered |
| **1** | Connector verb `invited_users` (§3), tenant switch, identity's invite with the record before the first login (§5), mail (§6), the door and the manifest capability (§4), audit. | security requirements 1–7; a person invited, mailed, confirmed, logged in, found by `ref` |
| **2** | Portal page "Eingeladene Personen" per app (lock, resend, raise to a platform role by hand); events once I-69 exists. | the tenant admin sees and acts on every invited person |
| **3** | `bestand` uses it (RFC-0123 stage 1). | a contact ordered, confirmed, logged in, sees only their nodes |

## 12. Decisions (Jörg, 2026-11-24, one by one, each as recommended)

| # | Question | Decision | Not chosen |
|---|---|---|---|
| **D1** | How does an app ask? | **A manifest capability `people: {invite: true}`** with key and URL like `cases` (§4). | The app as an OIDC client with admin rights in the realm (gives an app an admin credential, against RFC-0091); a portal form the app links to (no automation). |
| **D2** | How is K3.3 (`never: users`) narrowed, and who allows it? | **One new verb `invited_users`** only for users OAAP created with a marker, only in realms OAAP provisions; a tenant switch, off by default, flipped by **`server_admin`** (§3). | Dropping `never: users`; the switch with the `tenant_admin`; a separate realm for external people (a second login page, a second place to manage). |
| **D3** | Which platform role does an invited person get? | **`partner` only**; the app decides inside itself; raising is a tenant admin's act by hand (§5). | `user` (RFC-0123 §9.1 as written — reaches the twin and every app open to users); `guest`; a role the app chooses. |
| **D4** | Who sends the mail? | **Keycloak**, `execute-actions-email` with `VERIFY_EMAIL` + `UPDATE_PASSWORD`, through the tenant's mailbox (§6). | Identity sends its own mail; the app sends it (RFC-0072 stage 3 does not exist). |
| **D5** | Limits and lifespan? | **Per instance per hour/day and per address per day; link 72 h by default, set per tenant** (§6). | No limits; fixed values. |
| **D6** | What may the app do with its people later? | **Resend, lock, unlock, read status — only its own; never delete, never change name, address or password** (§4). | Delete (against F1 and RFC-0090); change the address. |
| **D7** | When does the platform record exist? | **At the invitation**, bound to `(provider, sub)`, so the app gets the UUID at once; status by reading, events later (§5, §7). | At the first login, the app waiting for it (no way to link before). |
| **D8** | An address that already has a user? | **Refused with `409`**, never linked; linking an existing person is a tenant admin's act, later (§5). | Linking by address (forbidden by RFC-0041 K4); creating a second user. |
| **D9** | Tenants without Keycloak? | **Need a realm** for this; no second mail path for now (§8). | A set-password mail from identity through the tenant's mailbox. |
| **D10** | What does the tenant admin see? | **A portal page per app with every invited person**, lock, resend, raise by hand; every call in the audit log (§4, stage 2). | Only the audit log. |

## Deutsche Zusammenfassung

**Worum es geht.** Das Kundenportal `bestand` aus RFC-0123 braucht etwas, das
keine App heute kann: Bestellt ein Account-Administrator einen
Ansprechpartner, muss für diese Person außerhalb des Dienstleisters eine
Anmeldung entstehen. Sie bestätigt ihre Adresse, setzt ein Passwort, und
`bestand` verknüpft die Anmeldung mit dem Knoten und den Zuständigkeiten.
Stufe 0 von RFC-0123 hat gezeigt: Es fehlt alles (S7), und eine Regel steht
dagegen. Der Keycloak-Konnektor führt `users` ausdrücklich unter `never`:
„OAAP legt keine Personen im Realm von jemand anderem an“ (RFC-0041 K3.3).

**Die Regel bleibt, aber eng geöffnet.** Sie war für fremde Realms gedacht
(der Verein, das Mitarbeiterverzeichnis). Neu ist ein einziges Verb
`invited_users`: Es gilt nur für Personen, die OAAP selbst mit einer Markierung
angelegt hat, und nur in Realms, die OAAP für den Mandanten bereitstellt. Löschen
geht weiterhin nicht. Ob Apps im Mandanten einladen dürfen, ist ein Schalter.
Er steht anfangs auf aus, und umlegen darf ihn nach Empfehlung nur der
`server_admin`.

**Der Weg.** Die App erklärt im Manifest `people: {invite: true}` und bekommt
wie bei den Vorgängen einen eigenen Schlüssel und eine eigene Adresse. Sie
schickt Adresse, Name und ihren eigenen Bezug. Die Plattform legt den Benutzer
im Realm an und erzeugt **sofort** den Plattform-Datensatz, gebunden an
`(provider, sub)`. So bekommt die App die UUID gleich in der Antwort. Dann lässt
die Plattform Keycloak die Mail schicken („Adresse bestätigen, Passwort
setzen“), über das Postfach des Mandanten.

**Die Person** bekommt höchstens die Rolle `partner`, also keine
Plattform-Befugnis. Was sie darf, entscheidet die App. RFC-0123 §9.1 wird
dadurch von `user` auf `partner` geändert. Die Marke im Zwilling (D21) bleibt
als zweite Mauer. Eine Adresse, zu der es schon einen Benutzer gibt, wird
abgewiesen und nie verknüpft. Die App darf mit ihren eigenen Eingeladenen
erneut senden, sperren, entsperren und den Status lesen; sonst nichts.

**Grenzen und Sicht.** Es gibt Mengengrenzen je App und je Adresse, und der
Link gilt standardmäßig 72 Stunden. Der Tenant-Admin sieht je App alle
eingeladenen Personen und kann sie sperren oder von Hand höherstufen. Jeder
Aufruf steht in der Prüfspur. Mandanten ohne Keycloak brauchen dafür einen
Realm.

**Entschieden (24.11.):** D1–D10 einzeln, jeweils wie empfohlen (§12).

**Stufe 0 gemessen am 24.11. (§1.5).** Die Einladungsmail funktioniert mit
dem gepinnten Keycloak wie gedacht. Ein Link führt auf Deutsch durch
„Adresse bestätigen“ und „Passwort setzen“; danach gilt die Adresse als
bestätigt. Der Link gilt nur einmal und läuft ab. Doppelte Adressen lehnt
Keycloak selbst ab, auch in anderer Groß-/Kleinschreibung. Eine Person mit der
Rolle `partner` kommt nur in Apps, die diese Rolle nennen, und die App bekommt
ihre UUID. Gemessen in einem Wegwerf-Realm mit einer Mail-Senke, so dass keine
Mail den Rechner verließ. **Zwei Befunde für Stufe 1:** Keycloak 26 verwirft
die Markierung `oaap_invited_by` stillschweigend, solange sie nicht im
Benutzerprofil erklärt ist (als Gruppe geht sie). Und „Passwort vergessen“ ist
in den Realms, die OAAP anlegt, ausgeschaltet.

**Stufen.** Stufe 0 misst, ob ein `partner` durchs Gateway in eine App kommt,
die Keycloak-Mail mit beiden Aktionen und die Duplikat-Einstellung. Stufe 1
baut Verb, Schalter, Einladung, Mail und Tür. Stufe 2 bringt die Portalseite,
Stufe 3 die Nutzung in `bestand`.

**Nicht gelesen, nicht gemessen:** RFC-0040 selbst (die UUID-Fakten stammen aus
der Identity-Spec), alles in §1.4.
