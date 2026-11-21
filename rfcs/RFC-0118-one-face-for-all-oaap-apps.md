# RFC-0118: One Face for All OAAP Apps — Names, Frame, Lists, Help, MCP, Twin

- **Status:** **Accepted (2026-11-21)** — D1–D9 as recommended (Jörg: "Wie empfohlen").
- **Date:** 2026-11-21
- **Authors:** Jörg (the question, 2026-11-21: "design rules for our OAAP apps — header,
  layout, navigation, tabs, tables and filters, embedded OAAP functions, AI; names alike,
  not once with OAAP and once without; every app offers help, is MCP-capable and offers and
  uses the twin; look at our apps, make a proposal, then check and adapt all of them"),
  Claude (inventory, proposal)
- **Depends on:** RFC-0035 (the app design contract: one platform stylesheet, a thin header),
  RFC-0036 (apps stay standalone pages), `oaap-design/docs/design-guidelines.md` v0.2
  (§5.1 the user menu in an app, §6 floorplans), RFC-0031 (data model and twin), RFC-0073
  (apps as MCP sources), RFC-0094 (help as the tenant's documentation, `docs:`), RFC-0061
  §3.1 (the feedback button), RFC-0042 T3 (the tenant's face)
- **Changes (when accepted):** RFC-0035 D2/D6 (amended: a platform-served frame script
  beside the stylesheet; retrofit all apps instead of opportunistically);
  design-guidelines v0.3 (a new chapter "Apps"); `oaap.core.identity` or the gateway (an
  instance-relative `/platform/context.json`); `oaap.data.twin` (search, an object's
  "open in app" address, the twin as an MCP source); the manifest schema
  (`data_model.object_types[].open`); `oaap-apps` (all 24 apps, a check `check-design.py`,
  a shared `lib/mcpdoor`)
- **Not part of this RFC:** a tenant design editor (RFC-0035 D3 stays: colours per tenant
  later); embedding apps in the portal (RFC-0036 non-goal stays); third-party apps (the
  rules are a recommendation for them, as in RFC-0035 D5).

## Summary

The 24 apps in `oaap-apps` were read on 2026-11-21, one by one (§1). They look like
24 projects, not like one platform: five header variants, three colour sets, seven
widths, five ways to switch a tab, search in two apps, paging in none, a user menu in
one, the feedback button in one, `docs:` in one, an MCP door in three, and app names
with and without "OAAP". Every app with a header copies 60–90 lines of style, and the
copies have drifted.

The proposal has three parts:

1. **Rules** (§3–§9): one naming rule; one frame (header, user menu, help, ask, feedback,
   footer); app types with their floorplans; one way to navigate; one list pattern
   (filter bar, sorting, paging, one row action); help, MCP and twin as duties, each
   with the exceptions written down.
2. **Platform pieces** that make the rules cheap (§10): the stylesheet grows into a
   small kit with dark mode; a frame script fills the header; a context document tells
   an app the tenant's title, the help address and the chat address; a shared MCP door;
   a twin picker and the twin as an MCP source; a check that reads every app.
3. **The retrofit** of all apps in six stages (§11), with a matrix per app (§2).

## 1. What was found (2026-11-21)

Read: every app's manifest, its page-rendering code, styles and scripts; the platform's
`theme.css`, `feedback.js`, `/auth/whoami`, `docs_publish.py`, the twin service, the
launchpad tile; RFC-0035/0036/0042/0061/0073/0094 and the design guidelines.

| Topic | Found |
| --- | --- |
| Names | With "OAAP": KI-Gateway, MCP-Gateway, Hilfe ("OAAP-Hilfe", hyphenated), Studio, FleetView, Store Editor, Ollama-Modelle, Partnerverwaltung, Mitarbeiterverwaltung, Projekt-App, RACI. Without: Chat, Vorgänge, Recherche, Spezialisten, Marketplace, Paketkatalog, Wegweiser, Rollen & Rechte, VPN-Client. Inside the product a third name: "OAAP IDE" (code-server), "OAAP Desktop" (webtop). Manifest name and page title differ (help: "OAAP-Hilfe" / "Hilfe"; projekt: "OAAP Projekt-App" / "Projekt-App"). No rule exists; the schema only limits the length. |
| Header | Five variants: gradient with three hexagons and the name in capitals plus a tagline (ai-gateway, mcp-gateway, studio, fleetview, store-editor, ollama-models; wegweiser with its own logo); "OAAP / Vorgänge" with a real user menu (vorgaenge); the platform's thin `oaap-header` with "← Portal" (partner-, mitarbeiterverwaltung, projekt, rollen-rechte); flat own blue (marketplace, package-catalog); none (recherche, spezialisten, vpn-client). |
| Colours | Only five apps load `/platform/theme.css`; six paste their own copy of `--oaap-*`; chat, help, marketplace, package-catalog, spezialisten, recherche, vpn-client have own palettes. `theme.css` itself uses primary `#2f6fed`, the guidelines `#2563eb`. |
| User | Only vorgaenge asks `/auth/whoami` and offers "Abmelden". Seven apps print the raw `X-OAAP-User` / `X-OAAP-Roles` headers (guideline §5.1 rule 2 says: never print roles). The rest show nobody. |
| Layout | Widths 52, 60, 62, 64, 68, 72, 74 rem, 820 and 860 px; breakpoints 640, 720, 760, 800 px. Dark mode in chat, help, marketplace, vpn-client only. |
| Navigation | Sub-path links (ai-gateway, vorgaenge), `?tab=` (mcp-gateway), links in the header (studio, store-editor, wegweiser, marketplace), pill tabs (rollen-rechte), JS buttons (chat), `#anchor` with `:target` (vorgaenge case page), none (seven apps). Tabs under the header in one app, under the title in another. |
| Lists | Bookmarkable filters and sortable columns: vorgaenge only (reference). Search: chat, help, marketplace. Chip filter: wegweiser. Paging: none. Inline forms in table rows (against guideline §6.1): package-catalog, spezialisten, rollen-rechte, marketplace admin. The twin apps fetch every row from the twin one by one and show raw URNs. |
| Platform functions | Feedback button (`feedback.js`): vorgaenge only. Help link: studio and store-editor, both to an own `/hilfe` page, not to the help app. Portal link: four apps, each built differently. |
| AI | Chat is the AI workplace; spezialisten and the marketplace review use AI in the background; no other app offers a way to ask about what is on screen. |
| Help (`docs:`) | studio only. RFC-0094 stage 6 (`OAAP_HELP_URL`, deep links) is specified, not built. |
| MCP (`mcp:`) | help, recherche, vorgaenge. Each has its own door code. |
| Twin | partner-, mitarbeiterverwaltung, projekt, raci (reference apps, own a few types), fleetview (consumes the node twin). Linking two objects means pasting a URN by hand; a list shows only the objects this app created. vorgaenge keeps its own "Partner" list beside the twin's Firma. `twin.py` is copied four times, and one copy has drifted. |
| Shared code | `lib/gwcore`, `lib/assistants`, `lib/mdview` copied and checked by `check-shared.py`. No shared frame; marketplace copies help's `render.py`. |
| Language | German everywhere; umlauts folded to ASCII in some apps ("gehoeren", "Gultig"); developer words reach users (RFC numbers, decision ids, "Herkunft: app:…", group keys, raw URNs). |

## 2. The apps and what each one gets

Types (§5): **A** workplace, **B** business app, **C** operations app, **D** service
without a page, **W** wrapped third-party product.

| id | Type | Name today → proposed | Frame | Help | MCP | Twin |
| --- | --- | --- | --- | --- | --- | --- |
| chat | A | Chat → **Chat** | own layout, user menu + help in the sidebar | yes | client (stays) | reads through MCP (§9) |
| vorgaenge | B | Vorgänge → **Vorgänge** | kit (has most of it) | yes | has; add search | — for now (correction 2026-11-21: its "Partner" are other tenants' inboxes, not companies; a case naming a Firma is a later feature) |
| spezialisten | B | Spezialisten → **Spezialisten** | kit | yes | read: list, runs | — |
| recherche | C | Recherche → **Recherche** | kit | yes | has | — |
| studio | B | OAAP Studio → **Studio** | kit | has (move `/hilfe` into it) | read: projects, briefing | — |
| wegweiser | B | Wegweiser → **Wegweiser** | kit | yes | read/search links | — |
| partnerverwaltung | B | OAAP Partnerverwaltung → **Partnerverwaltung** | kit | yes | read/search Firma, Kontaktperson | owner (has); picker, all owners' objects |
| mitarbeiterverwaltung | B | OAAP Mitarbeiterverwaltung → **Mitarbeiterverwaltung** | kit | yes | read/search | owner (has) |
| projekt | B | OAAP Projekt-App → **Projekte** | kit | yes | read/search | owner (has); picker for Kunde |
| raci | B | OAAP RACI → **Zuständigkeiten (RACI)** | kit (today off-system) | yes | read | contributor (has); picker |
| ai-gateway | C | OAAP KI-Gateway → **KI-Gateway** | kit | yes | read: usage, models | — |
| mcp-gateway | C | OAAP MCP-Gateway → **MCP-Gateway** | kit | yes | is the door; not a source | — |
| help | C | OAAP-Hilfe → **Hilfe** | kit | is the help | has | — |
| fleetview | C | OAAP FleetView → **Flotte** | kit | yes | read: nodes, instances | consumes (has) |
| store-editor | C | OAAP Store Editor → **Store-Editor** | kit | has a `/hilfe` → `docs:` | read: lists, findings | — |
| package-catalog | C | Paketkatalog → **Paketkatalog** | kit | yes | read: packages | — |
| marketplace | C | Marketplace → **Marktplatz** (`MARKET_NAME` stays) | kit on admin pages; public pages keep their own look | yes | read/search assets | — |
| ollama-models | C | OAAP Ollama-Modelle → **Ollama-Modelle** | kit | yes | read: models | — |
| rollen-rechte | C | Rollen & Rechte → **Rollen & Rechte** | kit | yes | read: roles, grants | — |
| vpn-client | C | VPN-Client → **VPN-Client** | kit | yes | read: state | — |
| keycloak | D | Keycloak (Anmeldedienst) → **Anmeldedienst (Keycloak)** | — | admin docs | — | — |
| livekit | D | LiveKit (Echtzeit-Medien) → **Echtzeit-Medien (LiveKit)** | — | admin docs | — | — |
| code-server | W | Code-Server (VS Code im Browser) → **Entwicklungsumgebung (VS Code)**; "OAAP IDE" → same | product's own | yes | — | — |
| webtop | W | Desktop im Browser (Webtop) → **Desktop im Browser (Webtop)**; "OAAP Desktop" → "Desktop" | product's own | yes (and the desktop info file points to it) | — | — |

## 3. Names

1. **No "OAAP" in an app's name.** OAAP is the frame, not part of each picture: a
   tenant like `bec` shows its own title and logo, and "OAAP Partnerverwaltung" under
   someone else's logo reads like an advertisement. OAAP appears once, in the footer
   ("läuft auf OAAP 0.1.x").
2. **The name says what the app does, in German**, as a noun, as short as the job allows
   (*Vorgänge*, *Hilfe*, *Flotte*). An established word stays (*Chat*, *Gateway*, *MCP*,
   *VPN*).
3. **A third-party product goes in brackets after the function**: *Anmeldedienst
   (Keycloak)*. The function is what the user looks for; the product is what the
   operator looks for.
4. **One name everywhere**: manifest `app.name`, store entry, launchpad tile, page title,
   header, `docs:` title, the product's own branding. An app whose name a tenant may
   change (chat `CHAT_TITLE`, help `HELP_TITLE`, marketplace `MARKET_NAME`) uses
   `app.name` as the default.
5. **The `id` never changes** (RFC-0026: names are changeable, identity is not). Renaming
   changes words, not addresses.

## 4. The frame

```text
┌──────────────────────────────────────────────────────────────────────┐
│ ⬡ bec · Vorgänge                           ? Hilfe   ✦ Fragen   Anna ▾ │  header
├──────────────────────────────────────────────────────────────────────┤
│ Übersicht   Neuer Vorgang   Bereiche   Partner                        │  one bar: tabs
├──────────────────────────────────────────────────────────────────────┤
│ page title                                       [global action]      │
│ …                                                                     │
├──────────────────────────────────────────────────────────────────────┤
│ Vorgänge 0.16.0 · läuft auf OAAP 0.1.339                     Feedback │  footer
└──────────────────────────────────────────────────────────────────────┘
```

- **Header** (dark blue, the kit's `.oaap-header`): left the tenant's logo, or the
  hexagon when there is none, linking to the portal; the tenant's title, small; the app's
  name. Right, in this order: **Hilfe** (the app's product page in the help app), **Fragen**
  (§8, only when the tenant has a chat), the **user menu** (display name; *Portal*,
  *Passwort ändern*, *Abmelden* as POST — guideline §5.1, its three rules unchanged).
  No tagline, no capitals, no roles, no version in the header.
- **Server-rendered first.** The app renders the header with its name and a portal link.
  The frame script (§10) adds what needs a request: who is logged in, the tenant's face,
  help, ask, feedback. Without the script the page keeps its name and the way back.
- **Footer**: app name and version, "läuft auf OAAP" and the platform version; the
  feedback button (`feedback.js`) on the right. Nothing else: no RFC numbers, no
  decision ids.
- **Dark mode** follows the system, from the kit; an app sets no colours of its own
  beyond the kit's variables.
- **Width**: work area up to 72 rem; running text about 75 characters per line.

## 5. App types and their layout

| Type | Apps | Layout |
| --- | --- | --- |
| **A** workplace | chat | Full screen, its own arrangement. The user menu, help and feedback still exist, in the place the layout gives them (chat: sidebar footer). |
| **B** business app | vorgaenge, spezialisten, studio, wegweiser, the four twin apps | The frame (§4) and the floorplans of guideline §6: list report, object page with object header and tabs, dialog page. |
| **C** operations app | gateways, help, fleetview, store-editor, package-catalog, marketplace (admin), ollama-models, rollen-rechte, vpn-client, recherche | As B. A status page with cards is a list report without a table. |
| **D** service | keycloak, livekit | No tile, no page; help for admins only. |
| **W** wrapped product | code-server, webtop | The product's own interface. OAAP adds the name, the help and, where the product allows, the way back to the portal. |

## 6. Navigation

1. **An app's areas are tabs in one bar under the header** — the only fixed bar
   (guideline §6.2.3). An app with one area has no bar.
2. **Tabs are links** (sub-path such as `/bereiche`, or `?tab=` on an object page), never
   buttons: bookmarkable, back-button-safe, no script needed. The server marks the active
   one.
3. **The first tab reads** (*Übersicht*); settings and administration come **last**;
   consequential actions in their own last tab (guideline §6.2.2).
4. **No sidebar in an app.** The portal has the sidebar; an app with so many areas that a
   bar overflows has too many areas. Exception: type A.
5. **An object page** carries "← back to the list" above its title; tabs within an object
   use `?tab=`.
6. Areas a role cannot use are not shown (the gateway enforces it anyway).

## 7. Lists, tables and filters

The list report of guideline §6.1, made concrete. The reference is the case list of
`vorgaenge`.

1. **Filter bar above the table**, a GET form: a search field first (`q`), then at most
   four choices, then *Zurücksetzen*. The URL carries the filter, so a filtered list can
   be bookmarked and sent. Filtering happens on the server.
2. **A count line**: "23 von 340".
3. **Sorting** by clicking a column header (`sort=col` / `sort=-col`), marked ▲/▼ and with
   `aria-sort`.
4. **Paging** from 50 rows: *Weitere 50* (`offset`), never a silent limit.
5. **One row action**: the row opens the object page. No forms, no button rows in a table
   row. Bulk actions, where needed, through checkboxes and one action above the table.
6. **Status as a badge** in the kit's five colours: ok, warning, error, neutral, test.
7. **An empty list says what to do** ("Noch keine Links. *Neuer Link* legt den ersten an.").
8. **Twin objects by their title**, never by URN; the URN appears once, in the object
   header, copyable.
9. **Narrow screens**: the table scrolls inside its container; columns marked as minor
   are hidden below 640 px.

## 8. AI

1. **No app builds its own chat.** AI reaches an app through two doors, both the
   platform's:
   - **The app is an MCP source** (§9 below, point MCP): the tenant's assistants can read
     what the app holds, and act where the app allows the same action in its page.
   - **Fragen** in the header opens the tenant's chat with the context of the page (the
     app, and the object when the page shows one) as a ready question. The chat chooses
     the assistant; the app passes only where the person is.
2. **AI working in the background says so**: what spezialisten or the marketplace review
   decided by AI is marked as such where it is shown.
3. An app never sends its data to a model itself; it goes through the AI gateway like
   everything else.

## 9. Help, MCP and twin as duties

**Help.** Every app of types A, B, C and W declares `docs:` (RFC-0094): at least an
overview (`index.md`), a how-to per main task and a FAQ, with `readers` and `audience`.
Type D declares admin documentation. The header's *Hilfe* goes to the app's product page
in the help app; the chat answers from it. Own help pages (`/hilfe` in studio and
store-editor) move into `docs:` — one source.

**MCP.** Every app of types B and C that holds data declares `mcp:` with **read** tools
for its main objects (list, search, read) and prompts for its main tasks. **Write** tools
only where the page offers the same action, with the same rights through the propagated
person (RFC-0073 procedure I). Tool names `<app>_<verb>` (`wegweiser_search`). An MCP Apps
view for the main object is welcome (vorgaenge `case.html` is the example), not required.
Exceptions: chat (a client), mcp-gateway (the door itself), D and W.

**Twin.** An app that keeps business objects which exist outside it — a company, a
person, a project, a machine — **puts them into the twin** (owner or contributor) or
**references the twin's** (consumes). It never keeps a private copy beside the twin. An
app without such objects declares nothing: an empty data model is not a duty fulfilled.
Every instance is already in the node twin (RFC-0085 A2) without doing anything.
Using the twin means: choose an object with the picker (§10), show it by its title, open
it in its owning app, and let assistants read it (§10).

## 10. Platform pieces

| # | Piece | What it does |
| --- | --- | --- |
| P1 | **`theme.css` becomes a kit** | The variables plus the classes the rules need: header, tab bar, cards, object header, filter bar, table (sortable header, count line, paging), badges, buttons, empty state, footer; dark mode; one palette (D9). Apps keep only what is their own. |
| P2 | **`/platform/app.js`** (the frame) | Fills the server-rendered header: user menu from `/auth/whoami`, the tenant's title and logo, *Hilfe*, *Fragen*, and loads `feedback.js`. Reads `data-oaap-*` attributes (product, object). Without it the page keeps name and portal link. |
| P3 | **`/platform/context.json`** on every instance entry | For display only: the tenant's title and logo address, the portal, help and chat addresses (each present only when it exists). Not a boundary: guideline §5.1 rule 3 stays — no tenant id, no groups, the gateway draws the line. |
| P4 | **Help deep link** | RFC-0094 stage 6: the help app answers `/p/<product>` and `/p/<product>/<doc>`. |
| P5 | **Chat deep link** | Chat accepts `?frage=…&kontext=app:<id>[/<object>]` and opens a new conversation with it. |
| P6 | **Twin: search, picker, open, MCP** | `GET /twin/objects?type=&q=` for apps; a picker (`<input data-oaap-twin="Firma">`, from P2) instead of pasting URNs; `data_model.object_types[].open` (manifest) so the portal and other apps can open an object in its owning app; the twin as an MCP source with read tools, so assistants see the tenant's objects. |
| P7 | **`lib/mcpdoor`** | The Streamable HTTP door from help/recherche/vorgaenge as one shared, copied module (like `gwcore`), so twenty apps do not write twenty doors. |
| P8 | **`check-design.py`** | Runs beside `check-store.py` and `check-shared.py` over every app: name rule, `docs:` present, `mcp:` present for B/C, kit and frame linked, no pasted palette, no raw role output, umlauts not folded. A check that runs before every push is what CI ("continuous integration": every change is checked automatically before it lands) means; here it runs by hand until there is a pipeline. |
| P9 | **Launchpad shows `app.icon`** | The schema has the field, the tile ignores it. |

## 11. Stages

Each stage ends with versions raised, the check green, measured on `oaap-test`; rollout
to the fleet on Jörg's word.

1. **Platform**: P1–P5, P9, P8 in its first form; design guidelines v0.3 chapter "Apps".
2. **Frame and names**: every app of A, B, C on the kit and the frame; names (§3); footer;
   feedback; dark mode; umlauts and no developer words. Mostly mechanical; it removes the
   pasted styles.
3. **Help**: `docs:` for every app — overview, how-tos, FAQ, written from what each app's
   description, briefing and `/hilfe` page already say.
4. **Lists and navigation**: tabs (§6) and lists (§7) per app; inline row forms go.
5. **MCP**: P7; read tools for every B/C app with data.
6. **Twin**: P6; the four twin apps on picker and search. (Struck 2026-11-21: "vorgaenge
   Partner on the twin's Firma" -- the Partner there are other tenants, see §2.)

## 12. Decisions for Jörg

| | Question | Recommendation |
| --- | --- | --- |
| **D1** | "OAAP" in app names? | **No.** The function in German; a third-party product in brackets; OAAP once, in the footer (§3). |
| **D2** | The renames in §2 (FleetView → Flotte, Marketplace → Marktplatz, Store Editor → Store-Editor, Projekt-App → Projekte, RACI → Zuständigkeiten (RACI), Keycloak/LiveKit/code-server function first)? | **As in §2.** |
| **D3** | The frame as a platform script (P2) instead of a copy in every app? | **Yes.** Amends RFC-0035 D2 ("theme, not code"): the script is served like `feedback.js`, not copied; apps stay separate codebases. |
| **D4** | The tenant's title and logo in every app (P3)? | **Yes**, title and logo now; colours stay with RFC-0035 D3 (later). |
| **D5** | Help mandatory for every app (§9)? | **Yes**, D admin-only. |
| **D6** | MCP mandatory for B/C apps with data, read first? | **Yes**, write only as a mirror of the page. |
| **D7** | Twin only where business objects exist, plus picker, open and the twin as MCP source? | **Yes** — no empty data models for the sake of a tick. |
| **D8** | All apps now, in stages 1–6, instead of "when touched" (RFC-0035 D6)? | **Yes**, the check (P8) keeps them there. |
| **D9** | Which blue: the guidelines' `#2563eb` family or `theme.css`'s `#2f6fed`? | **The guidelines'** — it is the brand; `theme.css` follows. |

## Deutsche Zusammenfassung

Am 21.11. habe ich alle 24 Apps gelesen. Sie sehen aus wie 24 Projekte, nicht wie eine
Plattform: fünf Kopfleisten, drei Farbsätze, sieben Breiten, fünf Arten von Reitern.
Suche gibt es in zwei Apps, Blättern in keiner. Ein Benutzermenü und den Feedback-Knopf
hat nur „Vorgänge“, eine Hilfe (`docs:`) nur „Studio“, eine MCP-Tür nur drei Apps. Mal
steht „OAAP“ im Namen, mal nicht. Jede App kopiert 60–90 Zeilen Stil, und die Kopien sind
auseinandergelaufen.

**Vorschlag:**

- **Namen:** kein „OAAP“ im App-Namen; deutsch, was die App tut; ein Fremdprodukt in
  Klammern („Anmeldedienst (Keycloak)“). OAAP steht einmal, in der Fußzeile. Überall
  derselbe Name; die Kennung bleibt.
- **Rahmen:** dunkelblaue Kopfleiste. Links Logo oder Titel des Mandanten und der
  App-Name, rechts Hilfe, Fragen (Chat mit dem Kontext der Seite) und das Benutzermenü.
  Darunter genau eine Leiste mit Reitern als Links. Fußzeile mit Version und
  Feedback. Dunkelmodus.
- **App-Typen:** Arbeitsplatz (Chat), Fachanwendung, Betriebs-App (mit den Floorplans
  der Guidelines), Dienst ohne Seite, eingepacktes Fremdprodukt.
- **Listen:** Filterleiste mit Suche (in der Adresse, also merkbar), „23 von 340“,
  sortierbare Spalten, Blättern ab 50, eine Zeilenaktion, Status als Badge, keine
  Formulare in Zeilen. Vorbild ist die Vorgangsliste.
- **KI:** keine App baut einen eigenen Chat. KI kommt über die MCP-Tür der App und über
  „Fragen“ in der Kopfleiste.
- **Pflichten:** Hilfe für jede App; MCP mit Lesewerkzeugen für jede Fach- und
  Betriebs-App mit Daten; Zwilling überall dort, wo Geschäftsobjekte vorkommen, und
  keine Privatkopie daneben. Wo es keine Geschäftsobjekte gibt, bleibt der Zwilling weg.
- **Bausteine der Plattform:** `theme.css` als kleines Kit, ein Rahmenskript, ein
  Kontextdokument (Titel und Logo des Mandanten, Adressen von Hilfe und Chat), Sprünge
  direkt in die Hilfe und in den Chat, Zwillings-Auswahl statt URN-Kopieren, der
  Zwilling als MCP-Quelle, eine gemeinsame MCP-Tür, eine Prüfung `check-design.py`.
- **Umbau** in sechs Stufen: Plattform, Rahmen und Namen, Hilfe, Listen und Navigation,
  MCP, Zwilling.

Offen sind D1–D9. Die Empfehlung steht jeweils in der Tabelle in §12.

## Decision record (2026-11-21)

Jörg decided D1–D9 on 2026-11-21 with "Wie empfohlen": no "OAAP" in app names (D1), the
renames of §2 (D2), the frame as a platform script (D3, amends RFC-0035 D2), the tenant's
title and logo in every app (D4), help mandatory (D5), MCP read tools mandatory for B/C
apps with data (D6), the twin only where business objects exist plus picker, open and MCP
(D7), all apps now in stages 1–6 instead of opportunistically (D8, amends RFC-0035 D6), the
guidelines' blue (D9).

**Entscheidung (21.11.):** Jörg hat D1–D9 „wie empfohlen“ entschieden.

## Built after the decision

- **2026-11-21, P6 part "the twin as an MCP source":** `oaap.data.twin` 0.9 §2.16,
  reference 0.1.341. Every MCP gateway of a tenant on a node with the profile `store`
  finds the source `twin` with three read tools (`twin_types`, `twin_search`,
  `twin_object`), carried as the signed-in person; red until approved. Measured on
  `oaap-test`: source list, discovery door (3 tools), refusals without a person, the
  three tools against the real twin (13/13). Not yet measured: one call of a person all
  the way through a gateway view into the twin. Still open from P6: the picker in
  `app.js` and `data_model.object_types[].open`.

**Nachtrag (21.11.):** Der Zwilling ist jetzt eine MCP-Quelle (oaap.data.twin 0.9,
Referenz 0.1.341), gemessen auf oaap-test. Noch nicht gemessen ist ein Aufruf einer Person
durch eine Gateway-Sicht. Aus P6 offen: Zwillings-Auswahl im Rahmenskript und `open`.
