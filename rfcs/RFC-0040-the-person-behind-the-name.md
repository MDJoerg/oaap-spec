# RFC-0040: The Person Behind the Name — A User Identity That Outlives Their Login Name

- **Status:** Accepted in direction (2026-09-21) — Jörg decided to pull
  this forward; six decisions below are open. Nothing built.
- **Date:** 2026-09-21
- **Authors:** Claude (finding & proposal), Jörg (direction)
- **Depends on:** RFC-0002 (the two headers), RFC-0022 (tenant as
  boundary; D3 — providers are shared, users are not), RFC-0026
  (Names Are Changeable, Identity Is Not — the principle this applies)
- **Extends:** RFC-0026 to the one record it did not cover
- **Precondition for:** a foreign identity provider (§6), and any
  notification service addressed by person rather than by address
- **Driver:** The `oaap-hbsha` project, letter of 2026-09-19, asking:
  *„eine stabile, nie wieder vergebene Kennung (falls `X-OAAP-User` ein
  änderbarer Anmeldename ist — ist er das?)"*. They are about to anchor
  a delegated-permission model for hundreds of people on the answer.

## Summary

RFC-0026 settled a principle for this platform: **identity is a UUID,
the filing system hangs off the UUID, and every name a human reads is
an alias that may change.** It applied that to instances and tenants.

**The user record is the one place the principle was never applied.**
`X-OAAP-User` carries the login name, and the login name is the primary
key: apps anchor on it, and it is the only thing they get.

Today this happens to be safe, for a reason nobody decided: there is no
way to rename a user, and — found while answering the letter — **no way
to delete one either**. A user is deactivated, never removed, so a name
is never reused. That is a gap, not a guarantee.

This RFC gives the user record an identity of its own, adds the two
attributes every app currently has to ask for twice (display name,
verified e-mail address), carries all three to apps as headers, and
fixes the one thing that stops a deep link from surviving a login.

## 1. Why now, when nothing is on fire

The requesting project said plainly that nothing is urgent. Six of
their seven wishes can wait. This one cannot, and the reason is
asymmetric cost rather than a deadline:

**Every permission they write before this exists is written against a
login name.** Their model is "person X holds role Y in context Z,
granted by W", for clubs, teams, venues and sponsors. The anchor is
whatever we tell them is stable. If we later give the platform a user
rename — and RFC-0026's own logic points straight there — every one of
those grants silently refers to nobody.

Silently is the operative word. This codebase has produced the same
failure four times: **a path was rebuilt and one reader stayed on the
old one.** Here the reader would be an entire external application's
authorization model, and the failure mode is a permission that no
longer matches a person rather than an error anyone sees.

Doing it now costs a field and a migration. Doing it after they ship
costs them a data migration across their whole domain model, and costs
us the conversation about whose mistake it was.

## 2. What exists today

Verified against reference 0.1.104:

| | Today |
| --- | --- |
| Identifier an app receives | `X-OAAP-User` — the login name |
| Renameable | No. No endpoint exists. |
| Deletable | **No.** `active: false` only; the record stays. |
| Display name | On the record; reachable via `/auth/whoami`, **not** in a header |
| E-mail address | **Does not exist as a field at all** |
| Deep link surviving login | **No** — neither path nor query (§5) |

Two consequences worth stating out loud:

- An app that wants to show a person's name or reach them by e-mail has
  to collect both itself, unverified, and keep them in step with the
  platform by hand.
- `X-OAAP-User` is *de facto* immutable and unique forever. Apps may be
  relying on that already. This RFC must therefore be **additive** —
  nothing that works today may stop working.

## 3. Proposal

### 3.1 A user gets an identity

Every user record gains an **`id`**: a UUID, assigned at creation,
**immutable and never reused**, including after deactivation.

UUID rather than the short hex RFC-0026 gave instances, for one
reason: this identifier will be mapped one-to-one onto a foreign
provider's subject claim (§6), and it leaves the node in headers and in
other systems' data. Tenants already use a UUID; users join them.

The login name stays exactly what it is and keeps its own uniqueness
rule. It simply stops being the identity.

### 3.2 A user gets an e-mail address, with a verification state

A new optional field, plus a flag recording whether the address was
proven. Setting the address clears the flag; only a verification step
sets it.

The platform does not gain e-mail *sending* in this RFC — there is no
verification mail here. The field and the flag are the place a verified
address will be written, by the verification flow a foreign provider
brings (§6) or by an administrator asserting it. Adding the field now
is what lets everything else be built against a stable shape.

### 3.3 Apps receive three more headers

Alongside the unchanged `X-OAAP-User` and `X-OAAP-Roles`:

| Header | Content |
| --- | --- |
| `X-OAAP-User-Id` | the UUID of §3.1 — **the thing to anchor on** |
| `X-OAAP-Display-Name` | the display name, may be empty |
| `X-OAAP-Email` | the e-mail address (see D2 on unverified ones) |

All are set by the same `copy_headers` list the gateway already writes,
from the same `/verify` answer, so there is one source and no second
truth. `/auth/whoami` returns the same three, for the same reason it
already mirrors roles.

**The rule apps must be told, in the Deployment Contract:** *anchor on
`X-OAAP-User-Id`, display `X-OAAP-User` and `X-OAAP-Display-Name`.*
That is RFC-0026's sentence, applied one level down.

### 3.4 `X-OAAP-User` does not change

It keeps its name, its spelling and its content. Existing apps are
untouched. It becomes, honestly, what it always was: a name.

### 3.5 Non-ASCII, said before it breaks

A display name is "Jörg Müller"; an e-mail local part can be worse. HTTP
header values are not a safe place for arbitrary Unicode, and the
failure is not a clean error — it is mojibake in one app and a dropped
header in another, discovered in production.

This must be decided in the RFC rather than in the code (D4).

## 4. The prerequisite that is not optional

`_save()` in the identity service rewrites the whole user file with no
lock — read, modify, write, `os.replace`. Two concurrent creations lose
one of them.

Today this is unreachable: users are created by an administrator, one
at a time, through the portal. It stops being unreachable the moment
user records are created by **incoming traffic** — which is exactly
what §6 brings, and what the requesting project's self-registration
wish needs.

The service already knows how to do this correctly: `_braked_note()`
takes an exclusive `flock` for precisely this reason. The knowledge is
present and was not applied to the file that matters most.

**This is fixed as part of this RFC**, not deferred to the one that
needs it, because by then the bug is live.

### 4.1 A limit to record, not to fix here

`/verify` parses the **entire** user file and scans it linearly **on
every request**. At a dozen users this is free. At a thousand it is a
few hundred kilobytes of JSON per request across two workers; at ten
thousand it does not hold. The portal's user list has no paging and no
search, and the file is per node rather than per tenant, so
backup-per-tenant (RFC-0022 D7) does not cover identities.

None of that is fixed here — this RFC does not change the store. It is
recorded because the direction in §6 is what makes those numbers
plausible, and because the answer given to an outside project should
match what is written down.

## 5. A deep link survives the login

Today it does not, and the loss is total:

- the refused session redirects to `/auth/login` with **no** return
  target;
- a successful login redirects to `/`, hard-coded.

Only the *instance* survives, because the browser stays on the same
hostname — the gateway generator says so in its own comment: *"login
redirects to `/` — back to this same instance."*

An invitation link is the ordinary case this breaks, and invitations
are how every delegated-administration model brings people in. So:
**the originally requested path and query are preserved across the
login.**

This is a small change with one sharp edge: a return target taken from
a URL is the classic open-redirect hole. Only a local path may be
accepted — no scheme, no host, no protocol-relative `//` — and that
rule belongs in the RFC (D5), not in a code review.

## 6. Why this is also the precondition for a foreign identity provider

Jörg decided on 2026-09-21 to **open the path to external identity
providers, with Keycloak installable as an OAAP app.** The design of
that belongs in its own RFC; what belongs *here* is why this one comes
first.

RFC-0022 **D3** already settled the shape: *"users are not shared,
identity providers are"* — a tenant attaches one or more providers, and
what is shared is the authentication source, never the authorization.
`resolve_principal()` was written for it, in its own words, as *"an
ordered list of methods, not a branch… so that a customer's own
identity provider can become a third method later instead of a
rewrite."*

Two constraints follow, and both land on this RFC:

**The app never sees the provider.** The gateway becomes the OIDC
client; the app keeps receiving `X-OAAP-*` headers and nothing else. The
first guarantee of the Deployment Contract — *an app never builds a
login* — holds unchanged, or every app on the platform becomes an
integration project.

**Roles stay with OAAP.** The provider answers *who*; OAAP answers *what
they may do*. That requires a local user record created on first login,
bound one-to-one to the provider's subject claim. **That binding needs
a local identifier that is not a login name** — a foreign provider's
subject is not a username, and the name it suggests may collide or
change.

So §3.1 is not merely convenient for that RFC; it is its hinge. And
§4's locking becomes mandatory on the same day, because records then
appear through incoming traffic.

## 7. Migration

- Existing users receive an `id` on first load after the update,
  written once. `e-mail` starts empty and unverified.
- The new headers appear on every authenticated route; the gateway
  sites are regenerated, which already happens on every deployment.
- Nothing is removed, nothing is renamed, no app changes.

## 8. Out of scope

- **A user rename.** This RFC makes one *possible* later without
  breaking anyone. It does not propose it.
- **Deleting a user.** Its absence was discovered here and is recorded,
  not fixed. It becomes a real requirement with self-registration
  (erasure obligations) and belongs with that work.
- **Sending e-mail.** No verification mail, no notifications. §3.2 adds
  the field, not the flow.
- **Lifecycle events to apps.** The requesting project's fourth wish.
  Worth recording that the raw material exists: the tenant audit log
  already writes user creation and change with a timestamp, so
  "changes since" is a read view rather than a new store.
- **The external identity provider itself.** Own RFC (§6).
- **The user store's scaling limits.** Recorded in §4.1, not addressed.

## 9. Decisions asked for

- **D1 — the identifier is a UUID**, immutable, never reused, assigned
  at creation and backfilled once for existing users. *Proposed: yes.*
- **D2 — an unverified e-mail address is not sent to apps.** An address
  an app receives in a platform header will be treated as proven,
  whatever a companion flag says, and the safe default is not to hand
  over a claim we have not checked. The alternative — send it with an
  explicit flag — is what the requesting project asked for.
  *Proposed: withhold until verified; revisit if a real case needs it.*
- **D3 — `X-OAAP-User` keeps its present meaning and spelling.**
  *Proposed: yes — anything else breaks running apps for cosmetics.*
- **D4 — header encoding for non-ASCII** display names and addresses.
  *Proposed: UTF-8 percent-encoded, documented in the Contract, with
  the plain form used whenever the value is already ASCII — so the
  common case stays readable in a log.*
- **D5 — the return target after login accepts local paths only:** must
  begin with a single `/`, must not begin with `//`, no scheme and no
  host; anything else falls back to `/`. *Proposed: yes.*
- **D6 — the write lock (§4) ships in this RFC**, not in the one that
  needs it. *Proposed: yes.*

## Deutsche Zusammenfassung

**Das Prinzip gilt schon — nur nicht für Benutzer.** RFC-0026 hat für
diese Plattform festgelegt: Die Identität ist eine UUID, jeder Name,
den ein Mensch liest, ist ein Alias und darf sich ändern. Für Instanzen
und Mandanten ist das umgesetzt. **Der Benutzersatz ist die einzige
Stelle, an der wir es nie angewendet haben:** `X-OAAP-User` trägt den
Anmeldenamen, und der Anmeldename *ist* der Schlüssel.

Heute geht das gut, aber aus einem Grund, den niemand entschieden hat:
Es gibt kein Umbenennen von Benutzern — und, beim Nachsehen für den
Handball-Brief gefunden, **auch kein Löschen**. Ein Benutzer wird
inaktiv gesetzt, nie entfernt; ein Name wird deshalb nie
wiederverwendet. Das ist eine Lücke, keine Zusage.

**Warum es jetzt sein muss, obwohl nichts brennt.** Das anfragende
Projekt schreibt selbst, es sei nichts eilig — und für sechs seiner
sieben Wünsche stimmt das. Für diesen nicht, aus einem Kostengrund:
Jede Freigabe, die sie vorher schreiben, ist gegen einen Anmeldenamen
geschrieben. Bekommt die Plattform später ein „Benutzer umbenennen" —
und die Logik von RFC-0026 führt geradewegs dorthin —, dann zeigen
diese Freigaben auf niemanden mehr. **Lautlos**, und das ist das
Entscheidende: genau das Muster, das uns schon viermal erwischt hat,
nur diesmal im Autorisierungsmodell einer fremden Anwendung.

**Was gebaut wird:** eine unveränderliche, nie wieder vergebene UUID auf
dem Benutzersatz; ein E-Mail-Feld mit Prüfmerkmal (bisher gibt es gar
keines); drei zusätzliche Kopfzeilen für Apps (Kennung, Anzeigename,
E-Mail) neben den unveränderten zweien; und ein **tiefer Link, der die
Anmeldung übersteht** — heute geht Pfad und Query verloren, erhalten
bleibt nur die Instanz. Die Regel für Apps lautet danach: **auf die
Kennung verankern, den Namen anzeigen.**

**Eine Vorbedingung ist nicht verhandelbar:** Die Benutzerdatei wird
heute ohne Sperre komplett neu geschrieben. Zwei gleichzeitige Anlagen
verlieren eine. Heute unerreichbar, weil nur ein Administrator Benutzer
anlegt — nicht mehr unerreichbar, sobald Sätze durch **eingehenden
Verkehr** entstehen. Derselbe Dienst macht es an anderer Stelle bereits
richtig (`flock`); es wurde nur auf die wichtigste Datei nicht
angewendet. Das wird hier mitrepariert, nicht später.

**Und warum das vor Keycloak kommt:** Jörg hat am 21.09. entschieden,
den Weg zu fremden Identitätsanbietern zu öffnen (Keycloak als
OAAP-App, eigenes RFC). Zwei Bedingungen daraus landen hier: Die App
sieht den Anbieter nie — unser Gateway wird OIDC-Client, die App bekommt
weiter nur `X-OAAP-*`. Und die Rollen bleiben bei OAAP, was einen
lokalen Benutzersatz verlangt, der bei der Erstanmeldung entsteht und
**eins zu eins an die Kennung des Anbieters gebunden** wird. Dafür
braucht es eine lokale Kennung, die kein Anmeldename ist. Dieses RFC ist
also nicht bloß praktisch für das nächste — es ist dessen Angelpunkt.

**Sechs Entscheidungen** stehen in §9 zur Abnahme; die interessanteste
ist D2: Eine ungeprüfte E-Mail-Adresse würde ich Apps **gar nicht**
geben, weil eine Adresse in einer Plattform-Kopfzeile als bewiesen
gelesen wird, egal welches Merkmal danebensteht — das anfragende
Projekt hat ausdrücklich beides gewünscht.
