# RFC-0113: Proposals for Found MCP Sources — the Gateway Proposes, the Operator Accepts

- **Status:** **Draft (2026-11-20)** — D1–D9 open. Nothing built, nothing
  measured for this RFC. The facts in §1 were read the same day in the
  specs and in `mcp-gateway` 0.31.0.
- **Date:** 2026-11-20
- **Authors:** Jörg (the question, 2026-11-20: "should we build a kind of
  autodiscovery for MCP servers of the apps installed in the tenant; the
  MCP gateway could recommend them and make configuration easier"),
  Claude (facts, design)
- **Depends on:** RFC-0073 (apps as MCP sources; §3 the list, §16
  discovery without a person), RFC-0065 (views, default deny, pinned
  descriptions, effect classes, lights), RFC-0094 (D6: the one automatic
  approval, for a help), RFC-0104 (the setup door and its view recipe),
  RFC-0074 (procedure A, views with access `platform`)
- **Changes (when accepted):** `oaap.ai.mcp-gateway` (proposals);
  in stage 2 the manifest (`mcp.title`, `mcp.summary`),
  `oaap.apps.runtime` (the source list carries both) and
  `oaap.core.portal` (the MCP card)
- **Not part of this RFC:**
  - **Finding by probing.** No port scan, no guessing of `/mcp` or
    `/.well-known/…` on instances. The manifest declares the door
    (RFC-0073 D1); what is not declared is not found.
  - **Automatic approval.** Nothing reaches a view without an operator's
    click. The one exception that exists (a help of the own tenant,
    RFC-0094 D6) stays as it is and gets no siblings here.
  - **MCP servers inside foreign products** (a Forgejo, an n8n). Their
    package can declare `mcp:` and is then found like any source, but
    procedure I hands them `X-OAAP-*` headers they do not understand.
    They need credentials per person (RFC-0111) and get an RFC of their
    own after it.
  - **stdio servers:** RFC-0112. An `mcp-stdio` instance is an ordinary
    source and gets proposals like any other.

## Summary

Finding is built. Since RFC-0073 a gateway lists the instances of its
tenant that declare `mcp:`, enters each as a server and — since the
amendment of 2026-11-18 — reads its catalog without a person.

What is missing is the step after that. A found source is a server with a
red light whose tools are in no view. The operator has to know that they
must set the light, open a view, unfold the tree, tick every tool and
pick an effect class for each, and that a profile must point at that
view. Nothing on the gateway's pages says "this source was found and
nobody uses it yet".

This RFC adds a **proposal** per found source: a card that names the
source, says what its catalog holds, pre-ticks the reading tools and the
prompts, and asks for the two things only the operator can decide — the
light and the view. One click accepts it, through the same approval
function the tree uses. A proposal changes nothing until it is accepted,
and it can be dismissed.

## 1. Facts (read 2026-11-20)

| Claim | Where |
|---|---|
| An app declares `mcp: {path}`; a gateway with `mcp_sources: {read: true}` gets the list of such instances of its tenant on its node | RFC-0073 §2, §3 |
| A new source becomes a server named after the instance, light `red`, procedure I; no view shows anything of it | `books.sync_sources`; RFC-0073 §3 |
| The gateway reads a source's catalog without a person, at start and periodically | RFC-0073 §16.3; `read_catalog` |
| The list is synchronised every 5 minutes (`SOURCES_EVERY = 300`); the card on the page says "alle 15 Minuten" | `app.py`; a wrong sentence, to be fixed with stage 1 |
| The start page's "Zu tun" names a source only when its catalog was never read, failed, or the source is gone — not when it is read and unused | `start_tab` |
| Approval is per entry in the view's tree; the effect class is pre-selected from the tool's annotations (`readOnlyHint` → read, `destructiveHint` → execute, else write) | `app.py`, the tree of a view |
| For a help of the own tenant the gateway approves the reading tools and prompts once into every view with access `platform` | RFC-0094 D6; `auto_approve_help` |
| The setup door can make a view from `{"server", "effect": "read"}`; a profile's author has to write that step | RFC-0104 §3.3 |
| A light states the class of data behind a server (demo data `yellow`, customer systems `red`); a profile's ceiling refuses servers above it | `mcp-gateway` README, P5 |
| Packages in the store that declare `mcp:` today: `help`, `vorgaenge` | `oaap-apps/apps/*/oaap-app.yaml` |

## 2. The proposal

### 2.1 When there is one (D1)

A proposal exists for a server that

- came from the source list and is not gone,
- has a catalog that was read, and
- has **offered entries that are in no view**,

unless the operator dismissed it (§2.4). It is computed from the books
when the page is drawn; the gateway stores nothing but dismissals.

Two cases follow from the one rule:

- **A new source:** nothing of it is in any view. The proposal offers the
  whole catalog.
- **A source that grew:** an update of the app added tools. The proposal
  offers only the entries that are new since the last acceptance or
  dismissal, and only for views that already hold entries of this server.
  A *changed* description is not a proposal; it blocks the entry as
  before (RFC-0065 §4.2).

### 2.2 What it shows

On the start page, above "Zu tun", one card per proposal:

- the source's name, app and version as the list gives them; in stage 2
  the title and summary from the manifest (§4);
- the catalog in numbers: reading tools, other tools, prompts, resources;
- the entries as a list with their descriptions, **pre-ticked:** tools
  with `readOnlyHint: true`, and prompts. **Not ticked:** every other
  tool (shown with the effect class the tree would pre-select), and
  resources. An entry that cannot be approved (a schema that points
  outside, a template that cannot be checked) is shown with the sentence
  the tree gives today;
- two fields the operator must fill: the **light** and the **view**.

### 2.3 What the operator decides (D2, D3)

- **The light has no default.** The card cannot know what data the app
  holds; a light chosen by the gateway would be a guess with the weight
  of a classification. The field starts empty and the button stays
  inactive until it is set. For a source that grew, the light is already
  set and is not asked again.
- **The view.** The card offers the existing views that could carry the
  source, and "new view, named after the source". If exactly one view
  with access `platform` exists, it is pre-selected, because that is the
  chat's view in a tenant set up from a profile (RFC-0104). One proposal
  goes into one view; a second view is the tree's job.
- **Accepting** runs the function the tree runs (`view-items`): the same
  checks, the same pinning of the description, the same audit lines, with
  the operator as actor. There is no second approval path.
- **What accepting does not do:** it creates no profile, no key and no
  assistant. If the chosen view has no access that somebody holds, the
  card says so in a sentence and links to "Zugänge". Who may talk to a
  source stays a separate decision.

### 2.4 Dismissing (D4)

"Nicht einbinden" hides the proposal. The server stays, its catalog is
still read, the tree still offers everything. The dismissal is one audit
line with the actor and the list of entries it covered; entries that
appear later raise a new proposal (§2.1). The server's page shows
"Vorschlag ausgeblendet" with a button to bring it back.

## 3. Outside the gateway's page (D5, D6)

- **"Zu tun"** gets one line per open proposal, with a link to the card.
- **The setup door** (RFC-0104 §3.1) gets no new kind. A profile that
  wants a source in a view already says `{"kind": "view", "tools":
  {"server", "effect": "read"}}`. What the door gains is a read: `GET
  <path>?kind=proposals` answers the open proposals by name and count, so
  that a recipe (RFC-0109) or `tenant check` can say "two sources found,
  not in use" without a browser.
- **A tenant with sources and no gateway** (stage 2): the platform knows
  the instances that declare `mcp:` whether or not a gateway reads the
  list. The portal's MCP card says "n Apps mit MCP-Tür, kein MCP-Gateway
  im Mandanten" with a link to the store. This is the only place where
  the proposal has to come from the platform; everything else is the
  gateway's.

## 4. Two words in the manifest (D7, stage 2)

```yaml
mcp:
  path: /mcp
  title: Vorgänge                      # optional, at most 60 characters
  summary: Vorgänge lesen, anlegen und kommentieren.   # optional, at most 200
```

- **For the operator, not for a model.** The gateway shows both on the
  card and on the server's page, escaped, and passes them to no client:
  not in `tools/list`, not in `serverInfo`, not in an assistant. What a
  model reads stays the pinned description of an approved entry.
- **Declaration only**, as RFC-0073 D1: the platform checks type and
  length where the manifest is validated and copies both into the source
  list.
- **No tool names in the manifest.** A list of "recommended tools" there
  would be the catalog maintained twice, and it would go stale with the
  first update (the argument against A3 in RFC-0073 §16.7). What an app
  wants to recommend it already says in the catalog: `readOnlyHint` and
  a good description.

## 5. Security requirements (proposed)

1. A proposal changes nothing. Before acceptance no view, light, profile
   or key differs from the state without this RFC.
2. Acceptance runs through the same function as the manual approval, with
   the signed-in operator as actor and the same roles required.
3. A tool without `readOnlyHint: true` is never pre-ticked. A resource is
   never pre-ticked.
4. The gateway never sets a light for a proposal.
5. `mcp.title` and `mcp.summary` reach no MCP client and no model; they
   are shown escaped and cut to their length.
6. Acceptance and dismissal are audit lines with actor, server, view and
   entries.
7. A source the gateway's principal may not read (RFC-0073 D15) has no
   catalog and therefore no proposal; its line in "Zu tun" stays the one
   of today.

## 6. Conformance (described; every line gets a bait)

1. A source appears, its catalog is read → a proposal is shown;
   `tools/list` of every view answers exactly as before (bait: a view
   with access `platform` exists and stays empty).
2. A catalog with three tools, one with `readOnlyHint: true`, one with
   `readOnlyHint: false`, one without annotations → exactly one is
   pre-ticked.
3. Accept without a light → refused with a sentence; nothing approved.
4. Accept → the entries are in the chosen view with the effect classes of
   the form; the audit shows the operator, not "plattform"; the same
   request by a signed-in person without the operator role → refused.
5. Dismiss → no card; the tree still offers the entries. A catalog read
   that adds a tool → a proposal with that one tool only.
6. An entry with a schema that points outside → shown, not tickable; a
   forged form field for it → refused by the approval function (the bait
   is the direct POST).
7. A manifest with `summary` of 201 characters or with a line break →
   refused at validation. A `summary` holding `<script>` and a sentence
   addressed to a model → shown as text on the card, absent from
   `initialize` and `tools/list` of every view.
8. A help of the own tenant → approved once as before (RFC-0094 D6), no
   proposal for the entries that approval covered.

## 7. Stages

| Stage | What | Proof |
|---|---|---|
| **1** | Gateway only: proposal card for new and grown sources, accept, dismiss, the line in "Zu tun", the read at the setup door; the sentence about 15 minutes corrected. No platform change, no manifest change | on oaap-test: install `vorgaenge` in a tenant with a chat; one click later the chat lists cases; conformance 1–6 and 8 |
| **2** | `mcp.title` and `mcp.summary` in the manifest and in the source list; the portal's MCP card names sources without a gateway | conformance 7; a tenant without a gateway shows the hint |

## 8. Decisions

- **D1 — A proposal for every found source with unused entries, computed
  from the books, nothing stored but dismissals?** *Recommendation: yes.*
- **D2 — No default for the light?** *Recommendation: yes.* The
  alternative, `green` for apps of the own tenant, would classify data
  the gateway has not seen.
- **D3 — Pre-ticked are reading tools and prompts; one proposal goes into
  one view; acceptance creates no profile and no assistant?**
  *Recommendation: yes.*
- **D4 — Dismissing hides the proposal until the catalog grows?**
  *Recommendation: yes.*
- **D5 — The setup door gets a read (`kind=proposals`) and no new kind to
  make?** *Recommendation: yes;* the view recipe of RFC-0104 already
  covers building from a profile.
- **D6 — The portal hints at sources without a gateway (stage 2)?**
  *Recommendation: yes*, as a sentence on the existing card, no new
  page.
- **D7 — `mcp.title` and `mcp.summary`, for the operator only, and no
  tool names in the manifest?** *Recommendation: yes.*
- **D8 — No further automatic approvals beside the help of RFC-0094 D6?**
  *Recommendation: yes.* The help is read-only documentation of the
  tenant itself; no other app has that property by its kind.
- **D9 — Foreign products with their own MCP server wait for RFC-0111 and
  an RFC of their own?** *Recommendation: yes.*

## Deutsche Zusammenfassung

**Worum es geht:** Jörgs Frage vom 20.11. war, ob wir eine Autodiscovery
für die MCP-Server der installierten Apps bauen sollten, damit das
MCP-Gateway sie empfehlen kann. Der erste Teil ist schon gebaut: Seit
RFC-0073 findet ein Gateway alle Apps seines Mandanten, die im Manifest
`mcp:` erklären, trägt sie als Server ein und liest (seit dem 18.11.)
ihren Katalog ohne Person.

**Was fehlt:** Eine gefundene Quelle ist ein Server mit Ampel rot, dessen
Werkzeuge in keiner Sicht stehen. Der Betreiber muss selbst wissen, dass
er die Ampel setzen, eine Sicht öffnen, den Baum aufklappen und jedes
Werkzeug einzeln ankreuzen muss. Nirgends steht „diese Quelle wurde
gefunden und wird noch nicht benutzt“.

**Der Vorschlag:** Das Gateway zeigt je gefundener Quelle eine Karte auf
der Startseite. Sie nennt die Quelle, zählt den Katalog auf und kreuzt die
lesenden Werkzeuge und die Prompts vor. Schreibende Werkzeuge und
Resources sind sichtbar, aber nicht angekreuzt. Der Betreiber entscheidet
zwei Dinge selbst: die Ampel (ohne Vorbelegung, weil das Gateway die Daten
der App nicht kennt) und die Sicht. Ein Klick übernimmt den Vorschlag über
dieselbe Freigabe-Funktion wie der Baum. „Nicht einbinden“ blendet ihn
aus, bis der Katalog wächst. Bringt ein App-Update neue Werkzeuge, gibt es
einen Vorschlag nur für diese.

**Was es bewusst nicht gibt:**

- **Kein Suchen im Netz.** Gefunden wird nur, was das Manifest erklärt.
- **Keine automatische Freigabe.** Die eine Ausnahme (die Hilfe des
  eigenen Mandanten, RFC-0094) bleibt, weitere kommen nicht dazu.
- **Keine Werkzeugnamen im Manifest.** Das wäre der Katalog doppelt
  gepflegt und nach dem ersten Update veraltet.
- **Kein Profil, kein Assistent** beim Übernehmen. Wer mit der Quelle
  sprechen darf, bleibt eine eigene Entscheidung; die Karte verweist
  darauf.

**Stufe 2:** Das Manifest bekommt zwei freiwillige Angaben, `mcp.title`
und `mcp.summary`. Sie sind für den Betreiber gedacht und gehen nie an ein
Modell. Außerdem sagt die MCP-Karte im Portal, wenn ein Mandant Apps mit
MCP-Tür hat, aber kein Gateway.

**Nicht Teil:** MCP-Server in Fremdprodukten wie Forgejo oder n8n. Sie
verstehen die Kopfzeilen der Plattform nicht und brauchen Zugangsdaten je
Person (RFC-0111), also einen eigenen RFC danach.

**Nebenbei gefunden:** Die Karte „Quellen der Plattform“ sagt „alle 15
Minuten“, der Code gleicht alle 5 Minuten ab. Der Satz wird mit Stufe 1
berichtigt.

**Entscheidungen D1–D9** sind offen, Empfehlungen in §8. Gebaut und
gemessen ist nichts.
