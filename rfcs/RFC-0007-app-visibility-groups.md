# RFC-0007: App Visibility Groups

- **Status:** Draft (2026-08-07) — proposal, awaiting Jörg's decision
- **Date:** 2026-08-07
- **Authors:** Claude (proposal), Jörg (question & decision)
- **Depends on:** RFC-0002 (roles, gateway enforcement), RFC-0004 (manifest), RFC-0005 (addressing), RFC-0008 (`server_admin` — resolves Open question 1)

## Summary

RFC-0002's five standard roles (`admin`, `keyuser`, `user`, `guest`,
`partner`) answer *how trusted is this person on the platform* — a
coarse, fixed, security-relevant classification. They do not answer a
different, everyday operator question: *which of the installed apps
should this particular person or team actually see?* Today an app is
visible to a whole role or to nobody in that role; there is no way to
show one app to some `user`-role people and not others.

This RFC adds **visibility groups**: free-form tags an admin assigns to
users, and an optional group restriction an admin assigns to an
installed app *instance* (not the app's manifest — this is an operator
decision, made on the platform, not a developer decision shipped with
the app). Membership is checked **in addition to** the existing role
check, by the same gateway, with the same real enforcement — never a
UI-only filter.

## Motivation

Raised by Jörg (2026-08-07) after installing several apps on one
platform for different purposes: "eine sehr einfache Gruppen- oder
Kachelzuordnung würde mir reichen — an der App gepflegt: generell
verfügbar, oder verfügbar für user/Gruppe." Concretely: several `user`-
role people share a platform, but not every app is meant for everyone
in that role (e.g. a finance tool for two people, a workshop tool for
the shop floor, a customer-facing tool for the front desk).

The standard roles cannot express this without becoming custom roles
per scenario — which RFC-0002 explicitly leaves open ("custom roles
remain possible for complex scenarios") but never designed, and doing
so would multiply roles indefinitely and blur the security-relevant
role model with everyday app-assignment housekeeping. Those are
different concerns and should stay different concepts.

## Constraints

1. **No security theater.** RFC-0002's principle holds: the portal's
   launchpad filter is UX only; the gateway is the real enforcement.
   Anything this RFC adds must be enforced at the gateway, exactly like
   roles — never a tile that's merely hidden while the URL still works.
2. **Roles stay simple.** The five standard roles must not grow custom
   variants to express "which team" — that was RFC-0002's explicit
   design goal (no modeling required for simple scenarios).
3. **Operator concern, not developer concern.** Which people should see
   a given installed app is a decision for whoever runs the platform,
   made *after* installation, per instance — never baked into the
   app's distributed manifest (a wrapped app from the store does not
   know about a specific operator's teams).
4. **Stay simple.** Jörg's own framing: "sehr einfach." No group
   management UI, no nested groups, no per-route granularity beyond
   what roles already give — a flat tag, checked once per instance.

## Proposal

### Groups are free-form tags, not managed objects

A group is just a short string (e.g. `buero`, `baustelle-nord`,
`finanzen`). There is no group registry, no create/rename/delete
workflow — a group exists the moment any user carries the tag. This
avoids an entire admin surface for something meant to stay simple; if
real-world use later needs formal group objects (rename-safe, listable
independent of usage), that is future work (see Open question 3).

### User side: `groups` on the user record

Every user gains an optional `groups: [string]` field (default empty),
managed the same way `roles` is today — on the same object page
(design guidelines 6.2), a plain tag/checkbox-style input next to the
existing role checkboxes. Empty groups list = no group restriction can
exclude this user from anything (their roles alone decide, unchanged
behavior — this is the default and needs zero configuration).

### App instance side: `visibility` on the installed instance

Every installed app instance gains a `visibility` setting:

- **`all`** (default) — unchanged today's behavior: role check only.
- **`groups: [string]`** — an *additional* requirement, checked
  alongside the existing role check (both must pass): the caller needs
  at least one role the instance's routes declare **and** at least one
  group listed here. `server_admin` (RFC-0008) bypasses this
  unconditionally — the true platform-administration authority sees
  every instance regardless of visibility. `admin` alone does **not**
  bypass it: `admin` is an app-facing role (forwarded to apps as
  their own administrator) and, per RFC-0008, carries no platform
  authority by itself — a user can legitimately hold `admin` inside
  one app under test without seeing every group-restricted instance
  on the platform.

This lives in the **registry**, alongside the existing `roles` field
derived from the manifest — not in the manifest itself (constraint 3).
Set via:

```sh
sudo oaap app visibility <instance> all
sudo oaap app visibility <instance> groups buero,finanzen
```

Same mechanics as `oaap external set`/`oaap edge add`: updates the
registry, regenerates that instance's Caddy site (both the LAN
listener and, if registered, the external subdomain — `site_body()` is
shared), reloads the gateway. A portal admin page is Consequence work,
not required for this RFC's core (CLI is enough to ship a working
increment; the UI can follow the App-UI-Kit pattern already used for
Studio/Store).

### Enforcement

The generated Caddy `forward_auth` call gains an optional `groups`
query parameter, exactly parallel to the existing `roles` one:

```
uri /verify?roles=user,keyuser&groups=buero,finanzen
```

`/verify` (oaap.core.identity) checks it the same way it checks roles
today — fresh from the user store on every call, never trusted from
the session (spec 2.3's existing principle, unchanged): the caller
needs at least one of the listed groups, unless `server_admin` is
among their roles (RFC-0008). No `groups` parameter present (the
common case) = no change to existing behavior.

### Portal launchpad

`launchpad_tiles()` gets the mirrored, symmetric check (today it only
compares roles) so a hidden tile and a blocked gateway route always
agree — never one without the other.

### What is deliberately NOT in this RFC

- **No `X-OAAP-Groups` header to apps.** Groups are a platform-level
  visibility switch, not something the App Deployment Contract needs
  to teach apps about — keeping the contract's surface unchanged is
  worth more than a hypothetical future use. Add it later if a real
  need appears (an app wanting group-aware behavior can still read
  `X-OAAP-User` and ask the platform, once such an API exists).
- **No nested/hierarchical groups**, no group-of-groups.
- **No per-route granularity** — a manifest can already declare several
  routes with different `roles`; this RFC's `groups` restriction
  applies to the *instance* as a whole, matching how visibility is
  actually asked for ("hide this app"), not per sub-path.

## Consequences

- `oaap.core.identity` gains the `groups` field on user records and the
  `/verify` group check (spec bump).
- `oaap.core.gateway` gains the `groups` query parameter on `forward_auth`
  calls, generated alongside `roles` wherever `site_body()` is used
  (LAN and external sites both, RFC-0005 levels 1 and 3).
- `oaap.apps.runtime` gains the `visibility` field on registry entries
  and the `oaap app visibility` command.
- `oaap.core.portal` gains the mirrored tile filter and, as follow-up
  UI work, an object-page field for user groups and an admin control
  for instance visibility (candidate location: a small "Apps" admin
  page, since no page today lists installed instances for management
  — Store lists what's installable, `/health` lists status; neither is
  quite an app-management List Report today).
- The App Deployment Contract is **unaffected** — apps need no changes.

## Out of scope

- A dedicated group-management UI (rename, list all groups in use,
  delete a group from every user at once) — the tags stay ad hoc.
- Time-limited or approval-based group membership (relates to the
  existing ServiceAssignment idea in the capability backlog, a
  different, heavier mechanism for partner/support access).
- Per-user (not per-group) instance restriction — a group of one person
  already covers this without inventing a second mechanism.

## Open questions (for the decision)

1. **Admin bypass — RESOLVED (2026-08-07, Jörg) via RFC-0008.**
   `admin` alone does not bypass `visibility`: it stays an app-facing
   role, forwarded to apps as before, carrying no platform authority
   (Jörg's reasoning: handing someone `admin` to fully exercise an
   app under test must not also make them a platform administrator).
   The bypass belongs to the new `server_admin` role instead (RFC-0008)
   — the initial installation user holds both `server_admin` and
   `admin` and can designate further server admins. See RFC-0008 for
   the full role split and migration.
2. **Free-form tags vs. managed group objects** — proposed: free-form
   strings, no registry (constraint 4, simplicity). Revisit if this
   turns out to need renaming-safety or an overview of all groups in
   use once there are many.
3. **Portal UI now or CLI-only first increment** — the CLI alone
   delivers the real capability (gateway enforcement, tile filtering);
   the admin page is convenience on top. Recommendation: ship CLI +
   spec first, add the portal page as a fast follow once the shape is
   proven — same sequencing as `external`/`edge`.

## Deutsche Zusammenfassung

**Die Frage, die RFC-0002 nicht beantwortet:** Die fünf festen Rollen
sagen, *wie vertrauenswürdig* jemand auf der Plattform ist — nicht,
*welche der installierten Apps* eine bestimmte Person oder ein Team
tatsächlich sehen soll. Heute ist eine App für eine ganze Rolle
sichtbar oder für niemanden darin; es gibt keine Möglichkeit, sie nur
einem Teil der `user`-Rolle zu zeigen.

**Der Vorschlag:** **Sichtbarkeits-Gruppen** — frei vergebene Stichworte
(z. B. „Büro", „Baustelle-Nord"), die ein Administrator Benutzern
zuweist, plus eine optionale Gruppen-Einschränkung je **installierter
App-Instanz** (nicht im App-Manifest — das ist eine Entscheidung des
Betreibers, nicht des App-Entwicklers). Die Gruppenprüfung kommt
**zusätzlich** zur bestehenden Rollenprüfung dazu und wird — genau wie
Rollen heute — **vom Gateway wirklich durchgesetzt**, nicht nur im
Portal versteckt. Den Bypass hat **`server_admin`** (neue Rolle, siehe
RFC-0008) — `admin` allein bleibt eine reine App-Rolle ohne
Plattform-Wirkung, entschieden von Jörg am 7.8., weil App-Admin-Rechte
zum Testen sonst automatisch Serverherrschaft bedeutet hätten.

**Bewusst einfach gehalten:** Keine Gruppen-Verwaltung, kein
Umbenennen/Löschen — eine Gruppe existiert, sobald irgendein Benutzer
das Stichwort trägt. Kein neuer Header an die Apps (der Deployment
Contract bleibt unverändert) — Gruppen sind reine Plattform-Sache.

**Bedienung (CLI zuerst, Portal-Seite als Ausbaustufe):**

```sh
sudo oaap app visibility <instanz> groups buero,finanzen
sudo oaap app visibility <instanz> all       # zurück zum Normalzustand
```

**Zu entscheiden:** Freie Stichworte reichen erstmal, oder gleich eine
Gruppen-Verwaltung? Erst CLI+Spec, Portal-Seite als schneller
Nachzügler (empfohlen, wie bei `external`/`edge`)? (Die Bypass-Frage
ist entschieden — siehe RFC-0008.)
