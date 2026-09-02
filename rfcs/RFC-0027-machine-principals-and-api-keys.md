# RFC-0027: Machine Principals — One Way to Prove You Are Not a Person

- **Status:** Accepted (2026-09-02) — D1 decided by Jörg; D2–D6
  taken as recommended, cheap to overturn. Implementation started.
- **Date:** 2026-09-02
- **Authors:** Claude (analysis & proposal), Jörg (direction)
- **Depends on:** RFC-0002 (security-first access model), RFC-0008
  (`server_admin`), RFC-0010 (public route throttling), RFC-0022
  (tenant as boundary)
- **Driver:** Jörg, 2026-09-02: *"Ich selbst denke auch über einen
  API-Key-Mechanismus nach. Also dass ich meine Authentifizierung über
  API-Keys bereitstelle und damit beispielsweise eine OpenAPI für
  Automatisierungen nutzen könnte."* — asked alongside a production
  terminal that must stay logged in, and an RFID reader that must
  report what it scanned.

## Summary

Three wishes arrived in one conversation and looked like three
features:

- a **production terminal** that stays usable across reboots without
  somebody typing an admin password into a kiosk,
- an **RFID reader** that reports "terminal 3 saw tag X",
- an **OpenAPI** an automation can drive.

They are one thing. Each is a principal that **is not a person and
cannot type a password**, and each needs a long-lived secret instead.

We have already built this twice by hand. The deploy hook carries a
bearer token the portal validates; the fleet status endpoint carries a
fleet key the same way. Both are carve-outs in the generated gateway
config, each with its own check. **A third carve-out is the signal
that this should be a mechanism.**

It is cheap because of where it goes. `/verify` is the single place
where the platform answers *who are you and what may you do*
(`platform/services/identity/app.py`). Role, visibility group and
tenant are all decided there, and the answer leaves as two headers. An
API key is **a second way to answer the same question**: a different
credential in front, identical headers behind. No app changes. No
gateway change beyond letting the header through.

And one framing decision, prompted by Jörg's question about SSO: this
RFC does **not** specify "session or key". It specifies
**authentication methods** as an open list at one point. When a
customer brings their own identity provider, that is a third method
answering the same question — not a rewrite. The sentence that carries
all three:

> **How you prove who you are is replaceable. What that grants is not.**

## 1. What exists today

**Two machine credentials, both hand-rolled.** The generated gateway
config gives `/deploy/*` and `/fleet/*` their own `handle` blocks with
no `forward_auth`; the identity headers are stripped and the portal
validates the credential itself (`platform/appctl.py`, the site
generator). Each works. Neither generalises: a deploy token deploys,
a fleet key reads status, and nothing else exists.

**Sessions are browser-lived.** `session.permanent` is never set, so
the session cookie dies with the browser process. This is correct for
people and fatal for a kiosk: a terminal is logged out by every
reboot. Measured, not assumed — see RFC-0028 §2.

**Everything else is default deny.** An app container publishes no
host port and sits alone on its own network; the only route to it runs
through the process that checks roles (RFC-0016, verified on `oaapx01`
2026-09-02). That property is what makes a new credential safe to add:
there is exactly one door to widen.

## 2. Why this is cheap: the choke point

```
browser ──cookie───┐
                   ├──▶ /verify ──▶ X-OAAP-User, X-OAAP-Roles ──▶ app
script ──Bearer────┘        │
                            └─ roles · visibility groups · tenant
```

`/verify` already resolves the tenant, applies RFC-0007 visibility
groups, honours RFC-0008's `server_admin` bypass and fails closed on
an unknown tenant. All of that is credential-independent. Adding a
method means adding **one branch at the front** and leaving the rest
untouched.

The alternative — letting each app accept API keys itself — is the
design we rejected for tenants and for the same reason: *"An app that
filtered by tenant itself would be one bug away from a leak between
customers"* (`oaap.core.tenant` 3.1). An app that authenticated
machines itself would be one bug away from the same.

## 3. Proposal

### 3.1 A principal may be a machine

Machine principals are **users with a kind**, not a parallel species:

```json
{ "username": "terminal-3", "kind": "machine", "tenant": "<uuid>",
  "roles": ["user"], "groups": ["packstation"], "active": true }
```

Everything already built then applies without a second implementation:
tenant membership (RFC-0022), roles, visibility groups (RFC-0007),
deactivation, the audit log, `session_epoch`-style revocation.

A machine principal **has no password** and cannot log in through the
form. It authenticates only by the methods below.

### 3.2 Authentication methods are a list, not a branch

`/verify` resolves the caller through an ordered list of methods.
Today two, later more:

| Method | Credential | Principal | Status |
| --- | --- | --- | --- |
| `session` | signed cookie | person | exists |
| `key` | `Authorization: Bearer …` | person or machine | this RFC |
| `federated` | assertion from a customer IdP | person | RFC-TBD (SSO) |

A method answers exactly one question: **which principal is this?**
Everything after that — roles, groups, tenant, the two headers — is
shared code, written once. This is the part Jörg's SSO question
bought: without it, adding a third method later means unpicking an
`if session else key`.

### 3.3 What a key is

```json
{ "id": "k7f3a91c",
  "principal": "terminal-3",
  "tenant": "<uuid>",
  "roles": ["user"],
  "instance": "cls-viewer",
  "label": "Terminal Packstation 3",
  "hash": "<argon2/scrypt of the secret>",
  "created": "...", "expires": "...", "last_used": "...",
  "created_by": "cls_admin", "revoked": false }
```

Presented as `Authorization: Bearer oaapk_k7f3a91c_<secret>`. The `id`
travels in clear so the audit log and the portal can name the key
without ever holding the secret.

Rules:

- **The secret is shown once, at creation, and never again.** Stored
  hashed. A platform that can show you a key again is a platform that
  can lose every key at once.
- **Roles are explicit and bounded.** A key carries the roles it was
  given, never more than the *issuer* holds, and never more than the
  principal holds. Two ceilings, both checked at issue time and again
  at use.
- **A key belongs to exactly one tenant** and is refused for any other
  (RFC-0022 3.1, unchanged — the check is already there).
- **Expiry is mandatory** (§6 D3). Keys that never expire outlive the
  people who made them and the reasons they existed.
- **`instance` is optional and narrows** the key to one app, mirroring
  what the deploy token already does.

### 3.4 Lifecycle

| Action | Who | Where |
| --- | --- | --- |
| issue | `tenant_admin` in own tenant, `server_admin` anywhere (§6 D4) | portal + CLI |
| list | issuer's tenant | portal + CLI |
| revoke | same as issue | portal + CLI, effective immediately |
| rotate | issue new, revoke old — deliberately two steps | — |

Revocation is immediate, by the same reasoning that produced
`session_epoch`: a credential you cannot withdraw within seconds is a
credential you do not really control.

There is no "renew in place". Rotation is issue-then-revoke so the
overlap is visible and the old key's `last_used` shows whether anything
still depends on it.

### 3.5 What a key may never do

- **Carry `server_admin`** (§6 D2). A leaked `server_admin` key is the
  whole node, and unlike a password it sits in a config file, a
  CI variable, a screenshot.
- **Travel in a query string.** Bearer header only (§6 D6). Query
  strings land in access logs, referrers and browser history — ours
  writes an access log per external site by design.
- **Grant more than its principal holds at the time of use.** Roles
  come from the live user store on every request, exactly as for
  sessions (`oaap.core.tenant` 2.3). Deactivating a principal kills
  its keys without touching them.

### 3.6 Brake and record

RFC-0010's throttle already exists for public routes. Key
authentication reuses it, keyed on the **key id** rather than the
client address: a machine behind NAT is not a person, and a shared
address must not become a shared limit.

Every issue, revoke and **first use** of a key is written to the
owning tenant's audit log. Not every request — that is the access
log's job — but `last_used` is kept so an operator can answer "is this
key still needed" without archaeology.

### 3.7 The two carve-outs we already have

The deploy token and the fleet key are the same idea, narrower. They
work, they are in the field, and they are documented in briefings
already sent to third parties.

**They are not migrated in this RFC.** They become a candidate for
folding in once keys have run for a while — and if that never happens
because the cost outweighs the tidiness, that is an acceptable
outcome. Naming them here is enough to stop a *fourth* carve-out.

### 3.8 The app sees the header — and why that argues for scoping

`forward_auth` consults identity and then proxies the **original
request** onward, headers included. So the app behind the route
receives the `Authorization` header, key and all.

This is not new — an app has always received the session cookie of the
person using it — but a key is worth saying out loud about, because a
key is *portable* in a way a cookie is not: it is meant to be pasted
into a config file, and a malicious or compromised app could paste it
somewhere else.

We do **not** strip it. Stripping the header would break every app that
uses `Authorization` for its own purposes, and it would only move the
problem: the app would still be serving a principal it could act as.

What actually bounds this is **scoping** (D5). A key limited to
`cls-viewer` reaches only `cls-viewer` — so an app that keeps it gains
nothing it did not already have. An unscoped key reaches everything its
roles allow, and hands that reach to every app it touches. That is why
`instance` is in v1 and not "later", and why the CLI says so at issue
time rather than in a document.

## 4. What this costs

- **A new class of exposure.** A long-lived secret lives in a file, an
  environment variable, a container image someone pushed by accident.
  Sessions expire on their own; keys do not. Expiry, narrow scope,
  immediate revocation and `last_used` are the countermeasures, and
  they are countermeasures, not a cure.
- **Something new to rotate.** Every credential is an operational
  obligation. We should ship the reminder with the mechanism, not
  after the first key silently expires in production at 03:00.
- **The key travels to the app** (§3.8). Bounded by scoping, not
  removed by it.
- **A second door into `/verify`.** One branch, but it is the branch
  that decides who someone is. It deserves its own conformance tests
  before anything else uses it.
- **Portal surface.** Issuing and revoking need a page, and the page
  must show a secret exactly once — a UI pattern we do not have yet.

## 5. What it buys

- The terminal from RFC-0028 becomes possible at all.
- The RFID reader gets an identity, which is what stops anyone on the
  shop-floor network from badging in as anyone.
- Automation against an app's OpenAPI, with the app unchanged — it
  receives the same two headers it always did.
- Automation against the **platform's** own functions, which is the
  first honest answer to "can I script my node".
- A named place for SSO to attach later instead of a rewrite.

## 6. Decisions

D1 was put to Jörg and decided. D2–D6 are taken as recommended
until he says otherwise — each is a single constant or a single check,
so overturning one costs a line, not a redesign.

**D1 — Machine principals as users with `kind`, or a separate store?**
**Decided (Jörg, 2026-09-02): users with a kind.**
*Recommendation was:* Everything else already works —
tenant, roles, groups, deactivation, audit. A parallel store would
duplicate the tenant check, which is the one check we have argued
hardest to keep in a single place.

**D2 — May a key carry `server_admin`?**
*Recommendation: no, with no override.* If a node genuinely needs
scripted administration, that is a separate RFC with a separate,
narrower mechanism — not the same key type that will end up in a CI
variable.

**D3 — Expiry: default, maximum, and is "never" allowed?**
*Recommendation: 90 days default, 365 maximum, no "never".* A terminal
that runs for years is exactly the case where a forgotten credential
hurts most; RFC-0028 should re-issue on enrolment rather than ask for
an eternal key.

**D4 — Who may issue?**
*Recommendation: `tenant_admin` within their own tenant, never above
their own roles; `server_admin` anywhere.* This mirrors the store
decision (RFC-0022 work, 0.1.55): the tenant admin runs their tenant,
and the point of delegating is that they do not have to ask.

**D5 — Is `instance` scoping in v1?**
*Recommendation: yes* — and §3.8, found while wiring the gateway,
strengthened it from convenience to containment: the app receives the
header, so an unscoped key hands its whole reach to every app it
touches. A key that can only reach one app is the difference between an
incident and a nuisance.

**D6 — Bearer header only, or also a query parameter?**
*Recommendation: header only.* Convenience here is paid for in access
logs that keep the secret forever.

## Non-goals

- **OAuth2 / OIDC as an issuer.** We are not building an authorisation
  server. If a customer brings one, that is the `federated` method and
  its own RFC.
- **Scopes beyond roles and instance.** We have roles and visibility
  groups already; a third permission dimension needs a driver we do
  not have yet.
- **Per-request signing (HMAC over the body).** The right answer for
  *inbound webhooks an app receives*, where the app verifies — see
  RFC-0028's ingress discussion and the note to the cls project. Not
  the right answer for a caller we can identify.
- **Migrating the deploy token and fleet key** (§3.7).

## Zusammenfassung auf Deutsch

Drei Wünsche kamen als drei Funktionen daher — ein Produktions-Terminal,
das angemeldet bleibt, ein RFID-Leser, der meldet was er gescannt hat,
und eine OpenAPI für Automatisierung. Es ist eine Sache: ein
**Prinzipal, der kein Mensch ist** und kein Passwort tippen kann, also
ein langlebiges Geheimnis braucht.

Zweimal haben wir das schon von Hand gebaut: das Deploy-Token und der
Fleet-Schlüssel. Ein drittes Mal wäre der Moment, daraus einen
Mechanismus zu machen.

Billig ist es wegen der Stelle: `/verify` beantwortet als **einzige**
Stelle „wer bist du und was darfst du" — Rolle, Sichtbarkeitsgruppe,
Mandant. Ein API-Schlüssel ist ein **zweiter Weg, dieselbe Frage zu
beantworten**: vorne ein anderer Nachweis, hinten dieselben zwei
Header. Keine App ändert sich.

Ein Schlüssel gehört einem Prinzipal in **einem** Mandanten, trägt
**ausdrücklich vergebene** Rollen (nie mehr als Aussteller und
Prinzipal selbst haben), ist **nur einmal sichtbar**, läuft **ab**,
lässt sich **sofort entziehen** und kann auf **eine Instanz** begrenzt
werden. `server_admin` per Schlüssel ist gesperrt.

Wichtig für später: Der RFC schreibt nicht „Sitzung **oder**
Schlüssel", sondern **Authentifizierungsverfahren als offene Liste**.
Bringt ein Kunde sein eigenes SSO mit, ist das ein drittes Verfahren an
derselben Stelle — kein Umbau. Der Satz dahinter: **Wie man beweist,
wer man ist, ist austauschbar. Was das gewährt, ist es nicht.**

**Entschieden (Jörg, 02.09.):** D1 — Maschinen-Prinzipale sind
**Benutzer mit Kennzeichen** (`kind: machine`), kein zweiter Speicher.
Damit gelten Mandant, Rollen, Sichtbarkeitsgruppen, Deaktivierung und
Audit unverändert, und die Mandantenprüfung bleibt an **einer** Stelle.
**Ein Punkt, der beim Bauen auffiel (§3.8):** Das Gateway befragt
identity und reicht die Anfrage danach **unverändert** an die App
weiter — samt `Authorization`-Kopfzeile. Die App sieht den Schlüssel
also. Neu ist das nicht (das Sitzungs-Cookie sieht sie seit jeher),
aber ein Schlüssel ist *tragbar*: er ist dafür gemacht, in eine
Konfigurationsdatei kopiert zu werden. Entfernen wollen wir ihn nicht —
das bräche jede App, die `Authorization` selbst benutzt, und verschöbe
das Problem nur. Was es wirklich begrenzt, ist die **Beschränkung auf
eine Instanz**: Ein Schlüssel für `cls-viewer` erreicht nur
`cls-viewer`, eine App gewinnt durch Aufheben also nichts. Deshalb ist
D5 in Version 1 und nicht „später", und deshalb sagt die CLI es beim
Ausstellen statt in einem Dokument.

Die übrigen fünf (`server_admin` gesperrt, Ablauf verpflichtend,
`tenant_admin` darf im eigenen Mandanten ausstellen, Begrenzung auf
eine Instanz in Version 1, nur der Bearer-Header) nehme ich wie
empfohlen — jede ist eine Konstante oder eine Prüfung, kein Umbau.
