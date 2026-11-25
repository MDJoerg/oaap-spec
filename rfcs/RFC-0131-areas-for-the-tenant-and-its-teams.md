# RFC-0131: Areas for the Tenant and Its Teams

- **Status:** Draft — D1–D5 decided by Jörg (2026-11-25: the organisation
  manages its members itself; the page is in the portal; only the tenant admin
  creates areas; Forgejo through the administrator route for the owner; the
  name rule is enforced; private by default); D7–D8 open (§8).
  Nothing built.
- **Date:** 2026-11-25
- **Authors:** Jörg (the need, 2026-11-25: "wenn ich jetzt für das Unternehmen
  oder für einzelne Teams eine eigene Organisation anlegen würde … Das
  Unternehmen würde bei mir im Forgejo den Namen des Tenants bekommen. Alle
  weiteren Teams/Gruppen eine eigene Organisation mit einem Präfix des Tenants.
  Die Organisationen sollen sich selbst verwalten und haben einen eigenen
  Owner. Das könnten wir auch tief in unsere Tools integrieren."), Claude (design)
- **Depends on:** RFC-0121 (stores, `oaap.work.stores`: a store system already
  has **areas** — Forgejo: the person and their organisations), the Forgejo
  connector (`forgejo` 15.0.11+oaap.2, service `oaap`)
- **Related:** RFC-0045 (realm groups, `oaap authz setup`), RFC-0129
  (connecting an app afterwards), RFC-0118 (one face for all apps)
- **Changes (when accepted):** `oaap.work.stores` (a verb `stores_create_area`,
  declared in `about`), `oaap.core.portal` (a tenant page "Organisation"),
  `oaap.work.workspaces` (stage 2: "Neu…" chooses the area)
- **Not part of this RFC:** members of a team kept by the platform (D1: the
  organisation keeps them); a team as a realm group for rights in other apps
  (D8); renaming or deleting an organisation (done in the product).

## Summary

A tenant wants one organisation for the company and one per team in its
store systems — in Forgejo an *organisation*, named after the tenant
(`pxx`) or with its prefix (`pxx-vertrieb`), each with its own owner, and
from then on **managing itself**. Today this works by hand in Forgejo but
nothing keeps the names apart, the owner must exist first, and the chat's
"Neu…" always creates a repository under the person.

This RFC gives the store contract a verb **`stores_create_area`** (an area
is what `stores_areas` already lists), lets the tenant admin create such an
area on a portal page "Organisation" with a name the platform checks and an
owner, and — in stage 2 — lets "Neu…" in the chat put a new store into an
area. The platform creates the organisation and hands it over; it does not
keep its members.

## 1. Facts (2026-11-25)

- `oaap.work.stores` 0.2 has `stores_areas` (list) and `stores_create_store`
  with `area?`. The Forgejo connector lists the person and their
  organisations as areas (`/user/orgs`) and creates a repository in an
  organisation where the person may (`/orgs/{a}/repos`).
- The connector holds an administrator token and sends every content call
  with `Sudo: <login>`: Forgejo decides as the person.
- A person exists in Forgejo only after their first sign-in through the
  tenant's realm.
- The chat 0.24.1 sends no `area` with "Neu…": a new repository lands under
  the person.
- In `pxx` the Forgejo (`pxx-projects`) belongs to the tenant; one Forgejo can
  also serve several tenants (`projects.joomp.de`) — there the prefix is what
  keeps tenants apart.

## 2. The verb (stage 1)

| Verb | Arguments | Answer |
|---|---|---|
| `stores_create_area` | `name`, `title?`, `owner` (platform login), `visibility?` (`private` default) | `area` (id), `title`, `owner` — only if `create_area` is declared |

- `about` gains `create_area` (bool) and `area_word` (e.g. "Organisation",
  "Regal") so pages can say it in the product's word.
- The connector refuses with a sentence: a name that exists, a name the
  product does not allow, an owner who has never signed in ("… muss sich
  einmal angemeldet haben").
- **Forgejo:** an organisation whose only member is `owner` in the team
  *Owners* — created through the administrator route for that user
  (`POST /admin/users/{owner}/orgs`, to be measured on `ws375-git`, D4) so the
  platform's account does not stay in it. Visibility `private` unless asked.
  There is no commit to carry a trailer; the organisation's description says
  "Angelegt über OAAP von <admin> für <owner>", and the gateway's audit has it.
- From then on the owner manages members and teams in Forgejo (D1).

## 3. Names (D5)

- The company area is named exactly like the tenant (`pxx`).
- A team area is `<tenant>-<slug>`: lower-case letters, digits, hyphen,
  at most 40 characters together; the page proposes the slug from the title.
- The platform checks the name before the connector is called; a tenant can
  never create an area with another tenant's prefix on a shared product.

## 4. The page "Organisation" (stage 1, D2)

On the tenant's pages in the portal (tenant admin): the company and its teams
as rows — title, name, owner, and per store system that declares
`create_area` whether the area exists there (read through `stores_areas` as
the admin) with a button "In <system> anlegen". "Neues Team" asks title,
slug, owner (chosen from the tenant's persons). Every creation is written to
the audit. The page stores only what it needs to show the rows: title, name,
owner at creation, created where and when — no members.

## 5. "Neu…" into an area (stage 2)

The chat's "Neu…" offers the areas the person sees (`stores_areas`) — "unter
dir" or an organisation — and sends `area`; the product decides whether the
person may create a repository there.

## 6. Who may do what

| Who | May |
|---|---|
| tenant admin | create the company area and team areas, name the first owner (D3) |
| owner | everything in the product: members, teams, repositories, hand over |
| person | create stores in an area where the product lets them (stage 2) |

## 7. Security requirements

1. No area without a person behind the request; the admin's act is audited.
2. The name rule holds before any call (no foreign prefix).
3. The platform's account is not a member of the new organisation.
4. The owner must exist in the product; no account is created on their behalf.
5. Visibility is private unless chosen.

## 8. Decisions

- **D1 Who keeps the members?** (a) the organisation itself — the platform
  creates it and names the first owner. **Decided by Jörg 2026-11-25: (a).**
  (b) the platform, products follow at sign-in.
- **D2 Where?** (a) the portal, tenant page "Organisation" (recommended:
  several apps need the same teams); (b) the MCP-Gateway page "Ablagen".
  **Decided by Jörg 2026-11-25: (a).**
- **D3 Who may create?** (a) the tenant admin (recommended); (b) also a role
  the tenant grants. **Decided by Jörg 2026-11-25: (a).**
- **D4 How in Forgejo?** (a) the administrator route for the owner, the
  platform's account not in it (recommended, measured first); (b) as the owner
  with `Sudo` — needs "may create organisations" for every person.
  **Decided by Jörg 2026-11-25: (a).**
- **D5 Names enforced?** (a) tenant / `<tenant>-<slug>` enforced (recommended);
  (b) free names. **Decided by Jörg 2026-11-25: (a).**
- **D6 Visibility?** (a) private (recommended); (b) limited (all signed-in
  persons of the product). **Decided by Jörg 2026-11-25: (a).**
- **D7 Owner not yet in the product?** (a) refuse with a sentence (recommended);
  (b) create the account beforehand.
- **D8 Also a realm group per team?** (a) not now (recommended; RFC-0045 can
  add it); (b) yes, `/Teams/<slug>`.

## 9. Stages

0. Measure on `oaap-test` (`ws375-git`, Forgejo 15): the administrator route
   for another user, who ends up in *Owners*, refusals (name taken, unknown
   user), visibility.
1. Verb in the contract and the Forgejo connector; page "Organisation".
2. "Neu…" in the chat chooses the area.
3. Further products (BookStack shelves, BDT projects) as their connectors
   declare `create_area`.

## Deutsche Zusammenfassung

Ein Mandant soll in seinen Ablagesystemen eine **Organisation für das
Unternehmen** (Name = Mandant, z. B. `pxx`) und **je Team eine** (`pxx-vertrieb`)
bekommen, jede mit eigenem Owner, danach **selbstverwaltet** (D1, von Jörg
entschieden). Der Ablagen-Vertrag bekommt ein Verb `stores_create_area` (ein
Bereich ist, was `stores_areas` heute schon auflistet; bei Forgejo die
Organisationen), im `about` angekündigt. Der Mandanten-Admin legt Unternehmen
und Teams auf einer Portalseite „Organisation“ an; die Plattform prüft den
Namen (kein fremdes Präfix), der Konnektor legt in Forgejo die Organisation für
den Owner an (über den Admin-Weg, ohne dass das Plattformkonto Mitglied
bleibt), privat. Mitglieder führt danach der Owner in Forgejo; die Plattform
merkt sich nur Titel, Name, ersten Owner und wo angelegt. Stufe 2: „Neu…“ im
Chat wählt den Bereich (unter dir oder eine Organisation). D2 entschieden: im Portal. D3 entschieden: nur der Mandanten-Admin. D4 entschieden: Admin-Weg für den Owner. D5 entschieden: Namensregel erzwungen. D6 entschieden: privat. Offen: D4 Forgejo-Weg (erst messen), D5
Namensregel, D6 Sichtbarkeit, D7 Owner ohne Konto, D8 Realm-Gruppe je Team.
