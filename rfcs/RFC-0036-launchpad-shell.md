# RFC-0036: The Launchpad Shell — Grouping, Self-Service, and What Stays Out

- **Status:** Accepted (2026-09-11) — four decisions, all following the
  recommendation. See the decision record at the end.
- **Date:** 2026-09-11
- **Authors:** Jörg (direction, four decisions), Claude (analysis &
  proposal)
- **Depends on:** RFC-0007 (app visibility groups — already answers
  most of what this RFC's own title once implied), RFC-0004 (manifest
  — where the new `launchpad` section lives), RFC-0016 (app isolation
  — the reason embedding stays a non-goal), RFC-0022 (tenant as
  boundary), RFC-0035 (Part A of the same design round — the theme)
- **Follows:** RFC-0035, reserved as its Part B: "navigation
  structure, app visibility per user group, grouping, self-service
  (profile/password), a cross-app extension concept."

## Summary

RFC-0035 (2026-09-10) deliberately split a larger design round in two:
Part A settled the visual theme; Part B — this RFC — was reserved for
"navigation, visibility per group, self-service, extensions" and left
undecided. Before drafting it, the same four topics were checked
against what already exists, and one of them turned out to be solved
already: **app visibility per user group is RFC-0007** (2026-08-07),
live since Identity 0.3.0 — the gateway enforces it, the portal filters
tiles by it. This RFC does not redecide that; it references it.

What was genuinely still open, from RFC-0035's own non-goals list:

| | Question | Decision |
| --- | --- | --- |
| **D1** | How do apps open from the launchpad? | **Standalone, unchanged — but the manifest gets a reserved field for a future embedded mode.** Every tile keeps opening its app as its own page in a new tab, per RFC-0016's network isolation. `launchpad.embeddable` is added now, doing nothing, so a later embedded shell needs no breaking manifest change. |
| **D2** | How far does tile grouping go now? | **A developer-suggested section label, nothing more.** `launchpad.group` in the manifest becomes a heading the portal renders over matching tiles. No tenant-side reordering, renaming or drag-and-drop — Jörg's larger tenant-design-editor idea stays deferred until a concrete need shows it, same reasoning RFC-0035 D3 used for a future per-tenant theme. |
| **D3** | What can a user change about themselves now (previously only their password)? | **Their own display name.** A new self-service page, `/auth/profile`, mirroring `/auth/password` exactly. Every other field of a user's record — roles, groups, tenant, username, active flag — stays admin-only; none of them is a display name's business. |
| **D4** | How far does the cross-app extension concept go now? | **Direction only, no build.** RFC-0036 names where a future contribution mechanism would live (e.g. a `contributes.portal_links` manifest section letting an app register a lightweight link without a full tile) so a later version needs no breaking change — the same reserve pattern as D1 and as RFC-0035 D3 — but builds nothing. No concrete need has asked for it yet. |

Jörg decided all four on 2026-09-11, following every recommendation
(record at the end).

## Motivation

RFC-0035's own non-goals section named four things Part B would have
to answer: navigation structure, visibility per group, self-service,
and cross-app extensions. Re-reading the codebase before drafting this
RFC found that the second of those questions is not actually open —
RFC-0007 answered it a month earlier, for a different, unrelated
reason (Jörg wanted to show one app to some `user`-role people and not
others, sharing one platform for different purposes). It is real,
enforced at the gateway, and the portal's launchpad already filters
tiles by it (`oaap.core.portal` 2.2). Nothing here changes that.

That leaves three real, still-open topics, plus a fourth this RFC adds
explicitly because Jörg raised it while answering the first: whether
today's decision to keep apps standalone needs groundwork laid now for
a possible embedded mode later, so that decision does not have to be
revisited from zero.

## 1. The decisions

### 1.1 Embedding stays a non-goal; the name for later is reserved (D1)

Every tile has always opened its app as a separate page
(`target="_blank"`, `oaap.core.portal` 2.2) — that was never written
down as a decision, only as behaviour. RFC-0016 gives the underlying
reason: each app instance runs on its own Docker network, and only the
gateway sits on every app's network at once. Identity and the portal
itself are deliberately **not** on any app's network (RFC-0016 §Motivation).
A shell that embeds an app's page inside the portal's own page
(an iframe, the SAP Fiori launchpad pattern Jörg's original idea named)
would need the portal to reach into that isolation — session handling
across an iframe boundary, a relaxed frame-ancestors policy, an app
built to expect reduced chrome instead of a full page. None of that is
free, and nothing today asks for it strongly enough to justify weakening
RFC-0016's isolation for it.

So: apps stay standalone. But Jörg's question in the decision round —
*"wir behalten uns aber auch den eingebetteten Modus vor... da das
sowieso nur mit OAAP-Apps funktionieren wird, ist das vielleicht etwas
für das Manifest?"* — is answered by reserving a name now rather than
later. `launchpad.embeddable` (boolean, default `false`) goes into the
manifest today; nothing reads it. An app that sets it `true` is stating
only that it does not depend on assumptions an embedded mode would
break — nothing enforces or checks the claim in this version. The exact
mechanism a future embedded shell would use (postMessage protocol,
session bridging, a stripped-chrome variant of the app) is not decided
here — that is precisely what a future RFC on the mode itself would
have to work out. This mirrors RFC-0035 D3's pattern exactly: a fixed
answer now, a name chosen so the later phase costs no breaking change.

### 1.2 A section label, not a layout editor (D2)

`launchpad.group` (string, optional, max 40 characters) goes into the
same new manifest section. When an installed instance's manifest
declares one, the portal renders it as a heading above every tile
sharing that label; an instance that declares none renders exactly as
every tile did before this field existed — in the pre-existing,
unlabelled section, with no heading. Order between sections is
alphabetical by label, with the unlabelled section always first, so an
app opting in cannot silently push everything else down.

This is a developer's suggestion about their own app, read from the
manifest at install time (never from a store list) exactly like
`app.class` (`oaap.apps.runtime` 2.10) — it describes what the app is
suggesting about itself, not an operator's or a tenant's decision about
their launchpad. Jörg's original, larger idea — a tenant-level editor
where a `tenant_admin` creates, renames and reorders sections, drags
tiles between them — is explicitly **not** built here. It would need
its own storage (per tenant), its own UI, and its own decisions about
what happens when an app's suggested group and a tenant's chosen
arrangement disagree; none of that is justified without more than one
manifest actually using the new field first.

### 1.3 Self-service grows by exactly one field (D3)

A new page, `/auth/profile`, added next to the existing
`/auth/password` (same identity service, same pattern: a `GET` shows a
form, a `POST` validates and saves, both require an active session).
It changes exactly one field of the caller's own user record —
`display_name` — and nothing else. Every other field a user might want
changed about themselves (roles, groups, tenant membership, username,
active status) stays behind admin/`tenant_admin` management
(`oaap.core.identity` 2.4), unchanged by this RFC: each of those carries
a security-relevant decision a display name does not.

### 1.4 The extension concept gets a direction, not a mechanism (D4)

RFC-0035's non-goals list named "a cross-app extension concept" as
part of Part B. No concrete use case has asked for one yet — this RFC
does not invent a use case to justify building one. What it does
instead is name, in prose, the shape a future mechanism would likely
take, so that if and when a real need appears, the manifest does not
need a breaking change to grow into it: a new, optional manifest
section (tentatively `contributes.portal_links`, unallocated and
unvalidated — the platform does not yet check that this key even holds
what it should) through which an app could register a lightweight link
or quick action the portal shows without giving the app a full
launchpad tile. Nothing is built, nothing is read, nothing is
validated. This is the same "name reserved now, no code" move as D1 —
here without even a concrete field going into the schema, because
unlike `embeddable` (which cleanly means "does nothing yet"),
speculatively shipping half of an extension mechanism risks locking in
the wrong shape before a real consumer exists to test it against.

## 2. Non-goals

Explicitly **not** decided or built here:

- App visibility per user group — already RFC-0007, unchanged.
- An embedded/iframe shell mode — D1 keeps this a non-goal; only a
  manifest field name is reserved.
- A tenant-level launchpad layout editor (custom sections, reordering,
  drag-and-drop) — D2 keeps this deferred.
- Any field beyond a user's own display name in self-service — D3.
- An actual cross-app extension mechanism (validation, portal
  rendering, any manifest schema for it) — D4 names a direction only.

## 3. Build order

Built together with this RFC, as one small step (Jörg's explicit
choice for the build timing, rather than waiting for the next app that
would need it — RFC-0035's pattern for D6 was the opposite, and both
are legitimate; this round's topics were small and isolated enough,
and the portal/identity context was already warm from RFC-0031
Schritt 5, to build immediately instead):

- Manifest 0.4 (`oaap.apps.runtime` 2.16): `launchpad.group` and
  `launchpad.embeddable`, validated but not `must_understand`.
- Portal (`oaap.core.portal` 0.3.13): tiles grouped by `launchpad.group`
  into headed sections; a `Profil` header link next to `Passwort`.
- Identity (`oaap.core.identity` 0.3.5): `GET`/`POST /auth/profile`,
  self-service `display_name` change.

No existing app in `oaap-apps` is required to adopt `launchpad.group`
or `launchpad.embeddable` — both are optional, additive fields, applied
opportunistically like RFC-0035 D6, not retrofitted in one pass.

## Deutsche Zusammenfassung

RFC-0035 (Teil A) hat eine größere Design-Runde bewusst geteilt: Teil A
war das Farb-/Typografie-Thema, Teil B (dieses RFC) sollte
„Navigation, Sichtbarkeit je Nutzergruppe, Self-Service,
Erweiterungskonzept" klären. Beim genaueren Hinsehen war einer dieser
vier Punkte längst gelöst: **Sichtbarkeit je Nutzergruppe ist RFC-0007**
(seit 08.08. live) — das Gateway erzwingt sie, das Portal filtert die
Kacheln danach. Dieses RFC entscheidet das nicht neu, es verweist nur
darauf.

Vier echte Entscheidungen, alle nach Empfehlung:

- **D1 — Einbetten bleibt Nicht-Ziel, der Name dafür ist reserviert:**
  Kacheln öffnen weiterhin als eigene Seite, wie es RFC-0016s
  Netz-Trennung nahelegt. Ein neues Manifest-Feld
  `launchpad.embeddable` tut heute nichts, reserviert aber den Namen,
  damit eine spätere eingebettete Shell keinen Bruch am Manifest
  braucht — Jörgs eigener Hinweis, dass das „sowieso nur mit OAAP-Apps
  funktionieren wird".
- **D2 — Gruppierung nur als Entwickler-Label:** `launchpad.group` im
  Manifest wird zur Abschnittsüberschrift im Launchpad. Kein
  Umsortieren, kein Mandanten-Editor in dieser Version — Jörgs größere
  Idee eines Tenant-Design-Editors bleibt zurückgestellt, bis ein
  konkreter Bedarf sie verlangt.
- **D3 — Self-Service um genau ein Feld:** der eigene Anzeigename ist
  jetzt selbst änderbar (`/auth/profile`), alles andere am eigenen
  Datensatz bleibt Admin-Sache.
- **D4 — Erweiterungskonzept nur als Richtung:** wie eine App dem
  Portal künftig etwas anbieten könnte, wird benannt, nicht gebaut —
  kein konkreter Bedarf verlangt es noch.

Gebaut wurde alles Vier gleich in diesem Schritt (Jörgs Entscheidung),
nicht erst beim nächsten Anlass.

## Decision record (2026-09-11)

Decided by Jörg in chat, the same session the design round was
reopened; every recommendation followed.

- **D1 — standalone stays, `embeddable` reserved.** Jörg's own
  follow-up question ("behalten uns den eingebetteten Modus vor... für
  das Manifest?") led directly to the reserved field; the concrete
  field shape (`launchpad.embeddable`) was proposed and confirmed
  separately in the same session.
- **D2 — developer label in the manifest, no tenant editor.**
  Confirmed as proposed.
- **D3 — own display name, nothing else.** Confirmed as proposed.
- **D4 — direction documented, nothing built.** Confirmed as proposed.
- **Build timing** — built immediately as one small step, rather than
  deferred to the next app that would need it.

### What follows

Nothing further reserved under this RFC. A tenant-level launchpad
editor, an embedded shell mode, or a real cross-app extension mechanism
would each be their own future RFC, opened only when a concrete need
asks for one — none is opened by this one.
