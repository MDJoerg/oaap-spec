# RFC-0137: Several Sign-ins in One Browser

- **Status:** **Accepted (2026-11-27)** — D1–D7 decided by Jörg, all as
  recommended (§8). **Stages 0 + 1 built 2026-11-27 (§9)**: reference
  0.1.390, oaap.core.identity 0.6.20.
- **Date:** 2026-11-27
- **Authors:** Jörg (the need: several AI chats of different tenants on
  oaapx01, used on a phone; switching between them ends in "falscher
  Mandant"), Claude (cause and design)
- **Depends on:** oaap.core.tenant 3.1 (the tenant boundary in `/verify`),
  RFC-0027 (principals, `resolve_principal`), RFC-0040 (identity headers),
  RFC-0041/RFC-0091 (realm and foreign IdP logins), RFC-0115 (a tenant's own
  domain and its own cookie)
- **Changes (when accepted):** identity (the session holds one sign-in per
  tenant; `/verify`, `/auth/whoami`, login and logout choose by tenant), the
  login page and the refusal page; no app changes

## Summary

A browser holds **one** platform session today: the cookie `oaap_session`,
widened to the node's name (`oaap.joomp.de`) so that every
`<instance>.<node>` sees it. Every tenant that lives under the node's names
shares this one cookie. Whoever signs in to tenant B's chat overwrites the
sign-in of tenant A; going back to A's chat, `/verify` sees a person of B and
answers **"Forbidden: this app belongs to another tenant"** (identity
`app.py`, the tenant boundary). The boundary is right; it simply sees the
wrong person.

This RFC lets one session hold **one sign-in per tenant**, the way a mail
service holds several accounts side by side. Each request still belongs to
exactly **one** person: the identity service picks the sign-in whose tenant is
the tenant of the instance being reached. Nothing an app sees changes. A
request for a tenant the browser has no sign-in for is sent to that tenant's
login, exactly like an anonymous visitor today, and the new sign-in is
**added** instead of replacing the others.

## 1. What happens today (read from the code, 0.1.389)

| Step | Where | What |
|---|---|---|
| Cookie scope | `DomainAwareSessionInterface`, `place.cookie_scope` | Every host at or below the node's name gets the cookie of the node's name; a tenant domain (RFC-0115) gets its own |
| Sign-in | `POST /auth/login`, OIDC callback | `session["user"]`, `session["epoch"]` (and `idp`, `idp_out` for realm logins) — one person |
| Check | `/verify` → `_by_session()` | the one person; then roles, groups, then `resolve_tenant(user.tenant) != resolve_tenant(instance tenant)` → 403 |
| Sign-out | `POST /auth/logout` | revokes all sessions of that person (`session_epoch`), clears the cookie |

So on oaapx01 the tenants pxx, csa, ais, oaap-web and the others share the
cookie; only bec (own domain `bec.brandeis.de`) has a cookie of its own. A
person with accounts in two of the shared tenants can use one of them per
browser. The workarounds — a second browser, a private window — do not exist
in a phone's home-screen app and lose the sign-in when closed.

## 2. The proposal

### 2.1 The session

The session carries a list instead of a single person:

```
session["accounts"] = {
  "<tenant id>": {"user": "<username>", "epoch": <n>,
                  "idp": {...}, "idp_out": {...}, "at": "<iso>"},
  ...
}
session["last"] = "<tenant id>"     # the sign-in used most recently
```

- **One sign-in per tenant** (D2). Signing in again to the same tenant
  replaces that tenant's entry and nothing else.
- **A limit of 8 entries** (D5) keeps the signed cookie under 4 KB; the
  oldest (`at`) drops out first. One entry without a provider hint is about
  150 bytes.
- **The provider's id token hint** (`idp_out.hint`, up to 1800 bytes,
  `IDP_HINT_MAX`) is kept **for the newest realm sign-in only**; older entries
  keep `idp_out.tenant` without it. The hint only spares the provider's
  „really sign out?" question, so an older entry signs out with one question
  more instead of risking the cookie — the rule the callback already follows
  for a single large token.
- The old form (`user`, `epoch` at the top level) is read as a list of one,
  so nobody is signed out by the update.

### 2.2 Choosing the sign-in

One function, `pick_account(instance_tenant, host)`, used by `/verify`,
`/auth/whoami` and every other session-shaped answer (the same place as
`_by_session` today, so no route can choose differently):

1. **The instance has a tenant** (the `tenant` parameter the generated gateway
   config writes): the entry of exactly that tenant. None → the answer an
   anonymous visitor gets today (a navigation goes to the login of that
   tenant's place, a script gets 401).
2. **A tenant's place** (`<label>.<node>`, its own domain): the entry of that
   tenant.
3. **The node's own place and node-level pages:** the entry of `last` (D3) —
   today's behaviour for a browser with one sign-in.

Each entry is checked exactly like today (active, epoch, terminal key,
must-change-password). A stale entry drops out of the list alone; the others
stay.

**server_admin** (D4): an entry with the role `server_admin` passes the
tenant boundary today. It is used for another tenant's instance **only when
the browser holds no sign-in of that tenant**. Whoever is signed in as a
member of the tenant is that member there, not the operator — otherwise an
operator who also has a personal account in a tenant could never see the
tenant as its member sees it.

### 2.3 Signing in

The login page and the OIDC callback **add** an entry (§2.1). The login page,
when the browser already holds sign-ins, says so in one line: „Angemeldet als
anna (pxx), jörg (csa) — hier meldest du dich zusätzlich für <Ort> an.“

The refusal "this app belongs to another tenant" stays as a last line of
defence (an entry whose person changed tenant since), but the ordinary case no
longer reaches it: a browser without a sign-in of the instance's tenant is
treated as not signed in **there** and goes to that tenant's login.

### 2.4 Signing out

`POST /auth/logout` signs out **the sign-in of the place it is called from**
(D6) and leaves the others; the menu offers „Überall abmelden" as a second
entry, which clears all. `_revoke_sessions` keeps working per person: revoking
anna's sessions removes anna's entry from every browser at its next request,
nothing else.

A realm login keeps its own provider sign-out (`idp_out`) per entry.

### 2.5 What the person sees

The user menu of the portal and the app frame lists the sign-ins of this
browser: the one in use first, the others with their place as a link, and
„Weiteres Konto anmelden“. That is the whole switcher — switching is opening
the other chat; the right person follows from the address.

## 3. Security

- **Exactly one person per request.** Selection is by the instance's tenant,
  which comes from the generated gateway config, never from the browser. The
  identity headers (RFC-0040) carry one person, as before; no header ever
  names a second.
- **No widening of the tenant boundary.** A sign-in of tenant B is never
  used for an instance of tenant A (except §2.2 server_admin, which passes
  today already).
- **A shared device** loses no more than today: whoever holds the browser
  holds its sign-ins — today one, then several. „Überall abmelden“ is one tap.
  Terminals (RFC-0028) keep exactly one entry and no switcher (D7).
- **Audit:** every sign-in and every sign-out of one entry is logged as
  today, with the tenant.
- **Own domains** (RFC-0115) keep their own cookie; the list lives per cookie.
  bec on `bec.brandeis.de` therefore stays separate, as decided in D4 of
  RFC-0115.

## 4. Quick relief before the build (stage 0)

Independent of the list: the 403 page for "another tenant" becomes a page
with one button, „Mit anderem Konto anmelden“, which signs out and goes to the
login of the instance's place with the instance as the return target. Two taps
instead of finding the sign-out yourself. It does not keep both sign-ins; it
only makes the switch bearable until stage 1.

## 5. Stages

| Stage | Content |
|---|---|
| 0 | Refusal page with „Mit anderem Konto anmelden" (§4) |
| 1 | Session list, `pick_account`, login adds, logout per place + „Überall abmelden", reading the old form (§2.1–2.4) |
| 2 | The list in the user menu of portal and app frame (§2.5) |

## 6. Tests and measurement

- Unit tests in identity: two sign-ins of different tenants; `/verify` for an
  instance of each gives its own person; an instance of a third tenant gives
  the login redirect; the old cookie form is read; revoke of one person removes
  only that entry; logout per place; the limit of 8; server_admin plus member
  (D4).
- Measured on oaap-test with two test tenants (vuebung and a second one) in
  one browser and on a phone: both chats open side by side, switching without
  a new login, both identity headers right in the app.

## 7. Non-goals

- Two persons of the **same** tenant in one browser at the same time (D2).
- Sharing one sign-in across nodes (that is the fleet, RFC-0085).
- A single person spanning tenants. Each sign-in stays an account of one
  tenant; this RFC only lets a browser hold several.

## 8. Decisions

Decided 2026-11-27 by Jörg: **all as recommended**.

- **D1 — Several sign-ins in one session at all?** Recommended: **yes**, as
  described. Alternative: one cookie per tenant (`oaap_session_<label>`) —
  the same effect, but more cookies on every request and the selection logic
  is needed anyway.
- **D2 — One sign-in per tenant?** Recommended: **yes**; a second sign-in of
  the same tenant replaces the first. Two persons of one tenant in one browser
  is a test situation, not daily work.
- **D3 — Which sign-in for node-level pages?** Recommended: **the most recent
  one** (`last`), today's behaviour.
- **D4 — server_admin and a member sign-in of the same tenant?** Recommended:
  **the member wins**; server_admin is used for another tenant only without a
  member sign-in of that tenant.
- **D5 — Limit?** Recommended: **8** sign-ins per browser.
- **D6 — What does „Abmelden" do?** Recommended: **the sign-in of this place**;
  „Überall abmelden" as a second entry.
- **D7 — Terminals?** Recommended: **exactly one sign-in**, no list, as today.

## 9. Stages 0 + 1 built (2026-11-27)

- identity: `_accounts`, `_pick`, `_add_account`, `_drop_account`; every
  session-shaped answer goes through `_pick`; logout per place and `all=1`;
  the old form read and rewritten; terminals untouched; the sign-in time to
  the microsecond (two sign-ins in one second must still sort for "newest"
  and the limit).
- The gateway: `X-OAAP-Site-Tenant` set in an instance site's `/auth/*`
  block and stripped at site level (it joined `NOT_PLATFORM_HEADERS`, so a
  site written before is stale and `migrate-identity-headers` rewrites it at
  the update). Found while building: identity pages on an instance's address
  carried no tenant, so a sign-out there could not know which sign-in it
  meant -- §2.2 named only `/verify` and the place.
- Stage 0: the refusal page with „Mit anderem Konto anmelden“; the login page
  names the persons already signed in.
- `test_several_sign_ins.py` (38 checks); `test_foreign_bearer` adjusted: a
  browser without a sign-in of the instance's tenant now gets the anonymous
  answer (401 for a script) instead of the boundary's 403 -- the person still
  never gets in.

### Measured on oaap-test (2026-11-27, through the edge)

Two test accounts, `r137a` (vuebung) and `r137b` (rzt), one cookie jar like
one browser, the two chats `chat.vuebung.<node>` and `chat.rzt.<node>`:

| Step | Result |
|---|---|
| sign in to vuebung's chat, open it | 303, then 200, whoami `r137a` |
| sign in to rzt's chat, open it | 303, then 200, whoami `r137b` |
| back to vuebung's chat | **200, whoami `r137a`** (until 0.1.389: 403 "another tenant") |
| a client-sent `X-OAAP-Site-Tenant` of rzt at vuebung's chat | whoami still `r137a` (the gateway overwrites it) |
| the login page names the sign-ins | „Angemeldet als r137b, r137a“ |
| cookie with two sign-ins | 242 characters |
| sign out at rzt's chat | rzt's chat 303 to the login, vuebung's chat 200, `r137a` |
| `all=1` at vuebung's chat | vuebung's chat 303 |

The update rewrote 50 instance sites and `external.caddy`
(`migrate-identity-headers`); every one of the 50 instance bodies carries the
strip and the set line. Test accounts deleted afterwards. **F1 (older, not
from this RFC):** `external.caddy` stays "stale" for
`_site_identity_stale` after the update -- it carries the strips
`X-OAAP-Client` and `X-OAAP-Couple-Tenant` and the gate's `copy_headers`
(RFC-0135/0136), which the check does not know, so every update rewrites the
file and reloads the gateway once more. Harmless, to be fixed in the check.
Not measured: a provider (realm) sign-in beside a local one; a phone.

## Deutsche Zusammenfassung

**Problem:** Alle Mandanten unter dem Knotennamen (auf oaapx01 also pxx, csa,
ais, oaap-web …) teilen sich ein Anmelde-Cookie. Wer sich im Chat von Mandant
B anmeldet, überschreibt die Anmeldung von Mandant A; zurück in A kommt
„this app belongs to another tenant“. Die Mandantengrenze arbeitet richtig,
sie sieht nur die falsche Person. Nur Mandanten mit eigener Domain (bec)
haben ein eigenes Cookie.

**Vorschlag:** Eine Sitzung hält **je Mandant eine Anmeldung**, wie mehrere
Konten bei einem Maildienst. Bei jedem Aufruf wählt der Identitätsdienst die
Anmeldung, deren Mandant zur aufgerufenen Instanz passt — jede Anfrage gehört
weiter genau einer Person, die Apps merken nichts. Fehlt eine Anmeldung für
den Mandanten, kommt dessen Anmeldeseite, und die neue Anmeldung wird
**dazugelegt**, statt die anderen zu ersetzen. „Abmelden“ gilt für den Ort, an
dem man ist, „Überall abmelden“ für alle. Im Benutzermenü stehen die
Anmeldungen des Browsers; wechseln heißt einfach den anderen Chat öffnen.

**Stufen:** 0 Ablehnungsseite mit Knopf „Mit anderem Konto anmelden“ (sofort
spürbar), 1 Liste in der Sitzung mit Auswahl je Mandant, 2 Liste im
Benutzermenü.

**Angenommen am 27.11.2026, D1–D7 alle wie empfohlen:** ja zur Liste (D1), eine Anmeldung je Mandant
(D2), für Knotenseiten die zuletzt benutzte (D3), Mitgliedskonto vor
server_admin (D4), höchstens 8 (D5), Abmelden je Ort plus „Überall abmelden“
(D6), Terminals bleiben bei einer Anmeldung (D7).
