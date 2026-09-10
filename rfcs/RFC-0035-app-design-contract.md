# RFC-0035: The App Design Contract — A Shared Theme, Not a Shared Codebase

- **Status:** Accepted (2026-09-10) — six decisions, all following the
  recommendation. See the decision record at the end.
- **Date:** 2026-09-10
- **Authors:** Jörg (direction, six decisions), Claude (analysis &
  proposal)
- **Depends on:** RFC-0004 (manifest — where a new field would live),
  RFC-0016 (app isolation — apps stay separate codebases; only the
  theme is shared), RFC-0022 (tenant as boundary — a future per-tenant
  theme follows the same boundary as the twin)
- **Followed by:** RFC-0036 (reserved) — the Launchpad/Shell: navigation
  structure, app visibility per user group, grouping, self-service
  (profile/password), a cross-app extension concept. This RFC is
  deliberately Part A of a two-part design round; Part B is its own
  decision, not yet drafted.
- **Driver:** Jörg, 2026-09-10, while `oaap-apps` was actively growing:
  *„Wir müssten eigentlich auch Tools und Regeln vorgeben, wenn wir
  erreichen wollen, dass zumindest Apps, die für OAAP gebaut werden,
  alle gleich aussehen."* — followed immediately by a second, larger
  idea (a tenant-level design editor and a configurable portal shell),
  which is why the round was split into two parts before either was
  decided.

## Summary

`oaap-apps` now holds eight apps (Studio, FleetView, Store Editor,
LiveKit, AI Gateway, Ollama Models, and — just built — Partnerverwaltung
and RACI), every one of them a standalone codebase rendering its own
HTML with no shared visual contract. The longer that continues, the
more apps there are to retrofit later. Rather than settle the whole
question — visual theme *and* navigation *and* a portal shell — at
once, the round was split. This RFC is **Part A**: the theme only.

| | Question | Decision |
| --- | --- | --- |
| **D1** | How wide is the contract? | **Narrow.** Colour palette, typography, spacing — as CSS variables. Layout structure (where navigation sits) is a Part-B question; deciding it here would mean building it twice. |
| **D2** | How does the theme reach an app? | **One platform-served stylesheet.** An app links to it (`<link rel="stylesheet">`) and uses its variables in its own CSS, with local fallback values in case the stylesheet fails to load. |
| **D3** | Who sets the values? | **A fixed platform default for now.** A tenant-level override (Jörg's design-editor idea) is a later phase; the variable names are chosen so that phase needs no breaking change. |
| **D4** | Is navigation placement decided here? | **No — only a minimal convention.** Every app carries a thin header bar: app name, a link back to the portal. Sidebar-vs-top, tiles, grouping are Part B, because they depend on whether apps stay standalone pages or get embedded in a shell. |
| **D5** | How binding is the contract? | **Mandatory for `oaap-apps`** (the dogfooding principle already in its `README.md`). **A recommendation, not enforced, for third-party apps** in this version — a manifest flag the store could check is a later stage, not now. |
| **D6** | What happens to the eight existing apps? | **No mass rewrite.** The contract is applied to the next new app built (the Step-5 twin browser, or whichever comes first); existing apps migrate opportunistically, when touched for another reason. |

Jörg decided all six on 2026-09-10, following every recommendation
(record at the end).

## Motivation

An app on OAAP is, by RFC-0016, its own isolated codebase — that is
correct for blast-radius and independence, and this RFC does not touch
it. But isolation at the code level does not require isolation at the
*look* level: a user moving from Partnerverwaltung to RACI to FleetView
should not have to re-learn what a button looks like each time, any
more than a SAP Fiori user re-learns UI5 theming when moving between
apps on the same launchpad. Today they would, because nothing defines
a shared vocabulary of colour, type or spacing — every app decided
those for itself, the way Partnerverwaltung and RACI just did with
plain inline styles.

The risk of waiting is not hypothetical: RFC-0031 Schritt 5 (the twin
browser, still open) is itself a new piece of portal-facing UI. Built
before this contract exists, it would need rebuilding after; built
after, it is the contract's first real user.

## 1. The contract

### 1.1 Variables (D1, D2)

A platform stylesheet defines a fixed set of CSS custom properties.
First cut, refined at build time, not frozen by this RFC:

```css
:root {
  --oaap-color-bg: #ffffff;
  --oaap-color-surface: #f4f5f7;
  --oaap-color-text: #1a1d21;
  --oaap-color-text-muted: #5b616b;
  --oaap-color-primary: #2f6fed;
  --oaap-color-primary-text: #ffffff;
  --oaap-color-border: #d8dbe0;
  --oaap-color-danger: #c4342f;
  --oaap-color-success: #1f8a4c;

  --oaap-font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  --oaap-font-size-base: 15px;

  --oaap-space-1: 4px;
  --oaap-space-2: 8px;
  --oaap-space-3: 16px;
  --oaap-space-4: 24px;

  --oaap-radius: 6px;
  --oaap-header-height: 48px;
}
```

An app's own CSS reads these (`color: var(--oaap-color-text)`) instead
of hard-coding a value, and keeps the same values as local fallbacks
(`var(--oaap-color-text, #1a1d21)`) so a missing stylesheet degrades,
rather than breaks, the page.

### 1.2 Delivery (D2, D3)

The platform serves the stylesheet from one well-known path
(`/platform/theme.css` behind the gateway, exact hosting service a
build decision for `oaap-reference`, not a spec decision here). Today
it is one static file with the values above — the same for every
tenant. A later, per-tenant version (D3) changes *where the values come
from*, not *how an app consumes them*: the app's `<link>` and its CSS
never change, only what the platform serves at that path.

### 1.3 The header convention (D4)

Until Part B settles navigation, every app carries one thing only: a
thin header bar (`--oaap-header-height` tall) with the app's own name
on the left and a link back to the portal on the right. Nothing about
sidebars, tiles or grouping is decided here.

### 1.4 Bindingness (D5)

For `oaap-apps`, using the platform stylesheet and the header
convention is mandatory going forward, per the dogfooding principle
already stated in `oaap-apps/README.md`. For apps built outside this
repository, it is a recommendation in this version — no manifest field
enforces it, and the store does not check for it.

## 2. Non-goals

Explicitly **not** decided here — reserved for RFC-0036 (Part B):

- Navigation structure (sidebar vs. top nav, and who chooses)
- A launchpad/shell service: app visibility per user group, custom
  grouping, tenant-chosen layout
- Self-service functions hosted by a shell (profile, password)
- Any cross-app extension concept

Also not decided: retrofitting the eight existing apps in one pass
(D6 — deliberately opportunistic instead), and a manifest-level
enforcement mechanism for third-party apps (D5 — deferred).

## 3. Build order

Not built yet. First real use: whichever app is built next under the
RFC-0031 bauplan (the Step-5 twin browser, or the second wave of Step 4
— Mitarbeiterverwaltung, Projekt-App). Existing apps are not touched by
this RFC on their own.

## Deutsche Zusammenfassung

`oaap-apps` hat acht Apps, jede ihr eigenes Aussehen — je mehr dazukommen, desto teurer wird ein Nachziehen später. Statt gleich alles zu entscheiden (Farben *und* Navigation *und* ein Portal-Shell), wurde die Runde geteilt. Dieses RFC ist **Teil A**: nur das Farb-/Typografie-Thema.

Sechs Entscheidungen, alle nach Empfehlung:

- **D1 — Umfang schmal:** Farbpalette, Typografie, Abstände als CSS-Variablen. Navigationsstruktur ist Teil B.
- **D2 — Ein zentrales Stylesheet:** die Plattform liefert es, Apps binden es per `<link>` ein und benutzen seine Variablen, mit eigenen Fallback-Werten.
- **D3 — Feste Werte heute, Mandant später:** ein Plattform-Standard jetzt; ein Tenant-Design-Editor ist eine spätere Ausbaustufe, ohne dass sich am App-seitigen Einbinden etwas ändert.
- **D4 — Navigation nicht jetzt entschieden:** nur eine Mini-Konvention — schmale Kopfzeile mit App-Name und Link zurück ins Portal. Alles Weitere ist Teil B (Launchpad).
- **D5 — Verbindlich für `oaap-apps`, Empfehlung für fremde Apps:** kein Manifest-Zwang in dieser Version.
- **D6 — Kein Nachbau aller acht Apps auf einmal:** Kontrakt gilt für die nächste neue App, Bestand zieht mit, wenn er ohnehin verändert wird.

**Teil B** (Launchpad/Shell — Navigation, Sichtbarkeit je Nutzergruppe, Self-Service, Erweiterungskonzept) ist als RFC-0036 reserviert, noch nicht entworfen.

## Decision record (2026-09-10)

Decided by Jörg in chat, the same session the design round was opened;
every recommendation followed.

- **D1 — narrow scope.** Colour, typography, spacing as CSS variables;
  navigation structure moved to Part B.
- **D2 — one platform stylesheet.** Linked by the app, variables
  consumed in its own CSS, local fallbacks kept.
- **D3 — fixed default now, tenant override later.** Variable names
  chosen so the later phase needs no breaking change.
- **D4 — no navigation decision yet, only a minimal header
  convention.** Thin bar, app name, link back to the portal.
- **D5 — mandatory for `oaap-apps`, a recommendation elsewhere.** No
  manifest enforcement in this version.
- **D6 — no mass retrofit.** Applied going forward; existing apps
  migrate opportunistically.

### What follows

No build yet. The contract is applied when the next app is built
under the RFC-0031 bauplan. Part B (RFC-0036, reserved) is its own,
separate design round — not opened by this RFC.
