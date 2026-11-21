# RFC-0117: Assistant Templates and a Wizard for the Tenant Admin

- **Status:** **Accepted (2026-11-21)** — D1–D10 as recommended (Jörg: "Wie empfohlen").
  **Stage 1 built and measured 2026-11-21 (§10):** reference 0.1.336, `oaap.core.tenant`
  1.20, templates `hilfe-assistent` 1.2.0, `recherche` 1.1.0, `assistent-leer` 1.0.0.
  **Stage 2 built and measured 2026-11-21 (§11):** reference 0.1.338, `oaap.core.tenant` 1.21,
  `oaap.ai.assistants` 0.8, mcp-gateway 0.37.0, chat 0.19.0.
  The facts in §1 were read the same day in `tenant_recipe.py`, `tenant_build.py`,
  `appctl.py`, the portal (`recipe_view.py`, `/einrichten`), `lib/assistants`,
  `mcp-gateway` (`books.py`, `app.py`) and `chat` (`app.py`, `page.html`).
- **Date:** 2026-11-21
- **Authors:** Jörg (the question, 2026-11-21: "a wizard for the tenant_admin to
  create assistants; the help assistant belongs there, the research agents too,
  later other templates; export/import may be used"), Claude (facts, design)
- **Depends on:** RFC-0074 / RFC-0097 / `oaap.ai.assistants` 0.7 (an assistant is a
  prompt, a model name and optionally a view, without rights; it lives in the MCP
  gateway), RFC-0109 (setup recipes for existing tenants, `oaap.tenant-recipe/1`),
  RFC-0113 D2 (a recipe never sets a light it cannot justify), RFC-0116 (the
  recipe `recherche`)
- **Changes (when accepted):** `oaap.core.tenant` (recipe key `offers`, param kind
  `prose`, releases for gateway-only templates); `oaap.ai.assistants` 0.8 (export
  carries `from`); the portal (page "Assistenten"); mcp-gateway and chat (a link,
  no own wizard)
- **Not part of this RFC:**
  - **A new engine.** The wizard runs recipes through the existing preview, run,
    confirm and rollback.
  - **Editing existing assistants.** That stays in the chat's drawer and the
    gateway's page `/assistenten` (revisions, compare).
  - **Views made by hand in the wizard.** A template brings its view or needs none.
  - **A marketplace for templates across tenants or nodes.** Later, with RFC-0077.

## Summary

Today a tenant admin gets the help assistant or the research assistant only
through a **recipe** — and only if the operator copied the recipe onto the node
and released it for the tenant. A person who just wants "an assistant like
Hilfe, but with our tone" has two bad roads: the recipe (no say in title, prompt,
greeting) or the chat's free form (no view, no profile, no model release behind
it).

This RFC proposes **one page in the portal, "Assistenten → Neu"**, a wizard in
four steps: *choose a template*, *check what is missing*, *adjust*, *preview and
create*. A template is a **recipe that offers an assistant** (`offers:
"assistant"`): the same file format, the same engine, plus a declaration which of
its params the person may shape (title, greeting, instructions, model,
visibility). The platform ships three templates — **Hilfe**, **Recherche**,
**Leer (ohne Werkzeuge)** — and more can follow as files. An exported assistant
can be **imported as a starting point**; the export names the template it came
from, so the import knows which view it needs.

## 1. Facts (read 2026-11-21)

### 1.1 Where the help assistant comes from

Not from configuration of an app: the recipe `hilfe-assistent`
(`oaap-docs/szenarien/rezepte/hilfe-assistent.json`, 1.1.0) fetches the docs into
`help`, releases a model name to the chat at the `ai-gateway`, and creates in the
`mcp-gateway` the view `hilfe`, the chat's access profile and the assistant
`hilfe` through the setup door (`POST /oaap/setup`, item kind `assistant`). Title,
greeting and instructions are fixed in the file. The older road is the chat's env
`CHAT_ASSISTANT` and a local `assistants.json`; `/api/assistants/migrate` moves
those into the gateway (tenant_admin only).

### 1.2 Recipes are already a wizard — with a gate

`tenant_recipe.py`: params of kind `text`, `word`, `bool`, `color`, `setup_item`,
`light`; preview, run, confirm, rollback through jobs; a tenant admin sees
recipes in the portal under `/einrichten`, may **request** one, and runs it only
after the operator released `recipe:<id>@<major>` in the tenant record. A `text`
param refuses control characters (`tenant_build.py:839`) — **instructions with line
breaks cannot be a param today.**

### 1.3 Recipes reach the node by hand

`RECIPE_DIR = /var/lib/oaap/recipes`; the operator copies files there. No upload,
no shipped set.

### 1.4 Export/import exists for assistants

`{"v": 1, "assistants": [...]}`, checked by `check_document`
(`lib/assistants`), written with `owner: "-"` by `books.assistant_export`,
downloadable at the gateway's `/assistenten/export`, importable through
`/mcp/_assistants/_import` (the importer becomes owner) and through the chat. The
file names a `view` but says nothing about **how that view comes about** — an
imported assistant in a tenant without the view is stored and then fails at the
first conversation.

### 1.5 The setup door protects human work

The `assistant` item never overwrites an assistant a person created or changed; a
difference comes back as `conflict`. That rule stays the backbone of §3.4.

## 2. The template

A template is an ordinary recipe with three additions:

```json
{
  "recipe": "oaap.tenant-recipe/1",
  "id": "hilfe-assistent",
  "version": "1.2.0",
  "offers": "assistant",
  "card": {"title": "Hilfe", "summary": "Beantwortet Fragen zur Plattform aus der Doku des Mandanten.",
           "light": "green", "icon": "help"},
  "params": {
    "title":    {"kind": "text",  "default": "Hilfe", "shape": true},
    "aid":      {"kind": "word",  "default": "hilfe", "from": "title"},
    "greeting": {"kind": "prose", "max": 600,  "default": "Ich beantworte …", "shape": true},
    "system":   {"kind": "prose", "max": 8000, "default": "Antworte aus der Doku …", "shape": true},
    "model":    {"kind": "setup_item", "need": "models", "item_kind": "alias", "default": "standard", "shape": true},
    "visibility": {"kind": "word", "default": "tenant", "choices": ["tenant", "private"], "shape": true},
    "ceiling":  {"kind": "light", "from": "model"}
  },
  "steps": [ "… as today, the assistant item uses {aid}, {title}, {greeting}, {system}, {visibility} …" ]
}
```

- **`offers: "assistant"`** — the portal lists it on the page "Assistenten", not
  (only) under "Einrichten". Exactly one `assistant` item in the steps; the check
  refuses a template without or with two.
- **`card`** — what the first wizard step shows: title, one sentence, the light the
  assistant will need (green, yellow, red — said before anything is chosen).
- **`shape: true`** — the params the wizard offers in the step "Anpassen". All
  others are set by the template or derived (`from`).
- **param kind `prose`** — multi-line text, line breaks and tabs allowed, other
  control characters refused, `max` up to 8000.

`id` of the assistant comes from the title (`aid`, lowercase word, unique in the
gateway; on collision the wizard suggests `hilfe-2` — D5).

## 3. The wizard (portal, tenant admin)

Page **"Assistenten"** in the tenant's place, next to "Einrichten". Visible to
`tenant_admin`; operators see it per tenant.

### 3.1 Step 1 — Vorlage wählen

Cards of all templates the tenant may use (D4), plus **"Aus Datei"** (import,
§4). Each card: title, sentence, light, and a mark *"braucht Freigabe"* where the
operator must release it first (then the button is "Anfragen", the existing
request road).

### 3.2 Step 2 — Was fehlt

The recipe's `needs` against the tenant: present apps in green; apps the template
installs (`install: true`) named with "wird installiert"; apps that are missing
and not installable as a sentence with the way out ("Ohne KI-Gateway kein Modell
— zuerst im Katalog installieren"). Params that are not `shape` but have no
default (e.g. the search service address of `recherche`) are asked here.

### 3.3 Step 3 — Anpassen

The `shape` params as a form: title, greeting, instructions (a large field with
the template's text, "Zurück zur Vorlage" button), model from the gateway's list
with its light, visibility. Nothing else — no view, no rights.

### 3.4 Step 4 — Vorschau und Anlegen

The existing recipe preview (rows per step: *neu*, *schon da*, *Konflikt*), then
run. Afterwards a link "Im Chat öffnen" (`?assistant=<aid>`). A conflict with a
human-made assistant of the same id is shown, never overwritten (§1.5).

### 3.5 Entry points elsewhere

The chat's "+ Neuer Assistent" and the gateway's `/assistenten` get a link
"Aus Vorlage …" to the portal page for tenant admins. The chat's free form stays
for private assistants without view.

## 4. Export and import

- **Export** (gateway, chat) adds per assistant **`from`**: `"recipe:<id>@<major>"`
  when the setup door created it, absent otherwise. `oaap.ai.assistants` 0.8;
  readers of `v: 1` ignore unknown keys already.
- **Import in the wizard ("Aus Datei")**: the file is checked (`check_document`).
  Per assistant:
  - with `from` and the template available → the wizard opens that template with
    the file's title, greeting, instructions, model and visibility pre-filled —
    steps 2–4 as usual, so the view, profile and model release come along;
  - without `from`, view present in the gateway (or no view) → import as today;
  - without `from`, view missing → a sentence: "Die Sicht `x` fehlt in diesem
    Mandanten; das Werkzeug dahinter muss zuerst eingerichtet werden." Not stored.
- **"Als Vorlage speichern"** (stage 3): a tenant admin turns an assistant into a
  tenant template — the recipe it came from with new defaults. Kept in the
  tenant, offered only there.

## 5. Shipped templates (stage 1)

| Template | View | Light | Release |
|---|---|---|---|
| **Hilfe** (`hilfe-assistent` 1.2.0) | `hilfe` | green / from model | free (D4) |
| **Recherche** (`recherche` 1.1.0) | `recherche` | red | operator (installs an app, sends queries out) |
| **Leer — ohne Werkzeuge** (`assistent-leer` 1.0.0) | none (RFC-0116 D9) | from model | free |

They ship with the platform under `platform/recipes/` and are copied to
`RECIPE_DIR` on install and update (D7); a file of the same id in `RECIPE_DIR`
placed by the operator wins.

## 6. Security requirements (proposed)

1. A template gives no rights: the assistant item stays bound by `RIGHTS`
   refusal in `lib/assistants`; the wizard can shape only `shape` params.
2. A template that installs an app, binds a destination to an outside host or
   creates a profile above `yellow` needs the operator's release, always.
3. `prose` params go into the assistant's text only; the recipe engine refuses a
   `prose` param in any other place (`target`, `id`, `name`, an app config key).
4. The light of the card is computed from the steps, not trusted from `card`; a
   difference refuses the template.
5. Import never stores an assistant whose view is missing.

## 7. Conformance (described; every line gets a bait)

1. A tenant admin creates "Hilfe" with own title and a three-line instruction →
   the assistant has both, view `hilfe`, conversation works. *Bait:* a `prose`
   value in `target` → refused.
2. The same template twice → second id `hilfe-2`, one view, one profile.
3. "Recherche" without release → card says "braucht Freigabe", run refused.
4. Card claims `green`, steps create a `red` profile → template refused.
5. Export of a template-made assistant carries `from`; import into a second
   tenant opens the template pre-filled and creates the view.
6. Import of an assistant without `from` whose view is missing → sentence, nothing
   stored.
7. A human-changed assistant `hilfe` → wizard shows *Konflikt*, nothing changed.

## 8. Stages

| Stage | What | Done when |
|---|---|---|
| **1** | `offers`, `card`, `shape`, `prose`; portal page with the four steps; templates Hilfe, Recherche, Leer shipped; free release for gateway-only templates | §7 lines 1–4, 7 on oaap-test |
| **2** | Export `from`, import in the wizard; links from chat and gateway | §7 lines 5–6 |
| **3** | "Als Vorlage speichern" (tenant templates); further templates (Vorgänge, SAP with RFC-0114 views) | a tenant template used twice |

## 9. Decisions

*Accepted 2026-11-21: D1–D10 as recommended.*

- **D1 — The wizard lives in the portal, not in the MCP gateway or the chat?**
  *Recommendation: portal.* A template touches several apps (help, ai-gateway,
  install, destinations); the recipe engine with preview and rollback is there; the
  gateway's page stays the place to look after assistants.
- **D2 — A template is a recipe with `offers: "assistant"`, no own format?**
  *Recommendation: yes* — one engine, one release road, existing recipes become
  templates with a few lines.
- **D3 — Shapeable: title, greeting, instructions, model, visibility — not view,
  not light?** *Recommendation: yes.*
- **D4 — Templates that only touch apps the tenant already has, create no profile
  above `yellow` and no outside destination, are free for every tenant admin
  without release?** *Recommendation: yes*; everything else keeps the operator's
  release (§6.2).
- **D5 — The same template may be used more than once (own id, shared view)?**
  *Recommendation: yes.*
- **D6 — The export names its template (`from`), the import reopens the
  template?** *Recommendation: yes.*
- **D7 — The platform ships templates and copies them to `RECIPE_DIR`; an
  operator's file of the same id wins?** *Recommendation: yes.*
- **D8 — A newer template never changes assistants made from an older one; the
  page only says "Vorlage neuer"?** *Recommendation: yes* (§1.5).
- **D9 — Tenant templates ("Als Vorlage speichern") in stage 3, kept per
  tenant?** *Recommendation: yes.*
- **D10 — The page also offers moving assistants still kept in a chat
  (`/api/assistants/migrate`)?** *Recommendation: yes*, one line "n Assistenten
  liegen noch im Chat — übernehmen", because otherwise they stay invisible to the
  gateway (seen on oaap-test, `vuebung-chat`).

## 10. Stage 1 — built and measured (2026-11-21)

**Built (reference 0.1.336, `oaap.core.tenant` 1.20 §2.13):**

- `tenant_recipe.py`: top keys `offers`, `card`; param kind `prose` (engine: `text` with
  `multiline`, line breaks and tabs only, `max` up to 8000); `shape`; `offer_problems`
  (exactly one assistant, card fields, card light at least the highest literal light of
  the steps, a `prose` value only in an assistant's `greeting`/`system` -- in every
  recipe); `free_problems` (D4).
- `appctl.py`: `SHIPPED_RECIPE_DIR` = `recipes/` beside appctl (copied by every update to
  `/var/lib/oaap/app/recipes`); `tenant_recipe_path` takes the operator's file at the same
  or a higher version, the shipped one at a higher version; the list joins both folders;
  the tenant_admin gate lets a free template pass without a release; `recipe-view.json`
  rows carry `offers`, `card`, `free`, `shipped`.
- Portal: page **Assistenten** (`/assistenten`, menu entry beside *Einrichten*, same
  people): cards, *Weiter* or *Freigabe anfragen*; `/assistenten/neu/<id>`: what is needed
  (instances, the template's description with its preconditions, values without a
  default), *Anpassen* (the `shape` params, instructions as a large field with "Zurück zur
  Vorlage"), preview, *Anlegen* -- the same `tenant-recipe` jobs as *Einrichten*. The form
  of *Einrichten* shows `prose` as a text area too.
- Templates in `platform/recipes/` (copies in `oaap-docs/szenarien/rezepte/`, test-checked
  equal): `hilfe-assistent` 1.2.0 (free; title, id, greeting, instructions, model shapeable;
  the defaults are what 1.1.0 created, so an unchanged tenant shows *vorhanden*),
  `recherche` 1.1.0 (operator's release), `assistent-leer` 1.0.0 (free, no view).

**Deviations from the text above:**

- **Visibility is not shapeable** (§2, D3): the MCP gateway's setup door creates only
  tenant-wide assistants; private ones stay the chat's drawer.
- **No automatic `-2`** (§2, D5): the id is a shapeable field; a taken id shows as
  *Konflikt* in the preview with the sentence "eine andere Kennung wählen".
- **Shipped templates are read in place**, not copied to `RECIPE_DIR` (D7): the same
  effect (an operator's file of the same id wins), without a copy that could go stale.
- **Free (D4)** is "shipped and unchanged, no install, nothing red, only `app.setup` and
  `destination.ensure` with a literal address": the help template's fixed docs source is
  the platform's own, a destination whose address comes from a value is not free.
- **D10** (move chat-local assistants) moves to stage 2 with the links from chat and
  gateway.

**Tests:** `test_assistant_templates.py` (engine, D4, D7, the gate, the view) and
`test_assistant_templates_page.py` (the page) new; the four RFC-0109 test files run
without the shipped folder (their semantics); 16 files in the Linux runner green.

**Measured on oaap-test** (0.1.336 staged, tenant `rzt`, as its tenant_admin through the
functions the portal's job calls and the portal pages with the gateway's headers; the
release `recipe:hilfe-assistent@1` taken for the measurement and given back), 13/13:

1. The page shows Hilfe and Leer with *Weiter*, Recherche with *Freigabe anfragen*; the
   wizard has the instructions as a text area; Recherche by address: back.
2. Without a release the tenant_admin previews the shipped Hilfe: all four steps
   *vorhanden* (1.2.0 meets what 1.1.0 made).
3. Own id `hilfe-m117`, own title, three-line instructions: only the assistant missing;
   run done; in the gateway's database title, view `hilfe` and the instructions with their
   lines.
4. *Bait:* id `hilfe` with other instructions → *Konflikt* "anders in", nothing
   overwritten. A control character in the instructions → refused with a sentence.
   Recherche without release → refused with the way to the operator.
5. Leer: an assistant without view with the template's multi-line instructions --
   **after** `rzt-werkzeuge` was raised from 0.32.0 to 0.35.0; with 0.32.0 the preview
   stopped before anything happened with the old gateway's "view: fehlt." (hence the
   template's description with its preconditions on the wizard page).
6. Both runs rolled back: both assistants deleted (revisions stay).

**Not measured:** a click in the browser by a person; a conversation with the new
assistants in the chat (rzt's chat is 0.17.0; an assistant without view needs 0.18.0).
**Found:** most tenants of the fleet run an MCP gateway before 0.35.0 -- *Leer* needs the
app updates first.

## 11. Stage 2 — built and measured (2026-11-21)

**Built.**

- **The run names its template** (`oaap.apps.runtime` 2.39, reference 0.1.338): every setup
  call of a recipe run carries `X-OAAP-Setup-Recipe: <id>@<major>` -- a header, not a field
  of the item: a gateway before 0.37 skips the header but would refuse an unknown field.
- **mcp-gateway 0.37.0** (`oaap.ai.mcp-gateway` 0.33): an assistant the call makes or finds
  present remembers the template (column `origin`, no revision). Export and the list for a
  chat name it as `from: recipe:<id>@<major>` (`oaap.ai.assistants` 0.8); `from` on import
  and save is stripped, never stored in the assistant. The page *Assistenten* links the
  portal's templates for a `tenant_admin`.
- **Portal** (`oaap.core.tenant` 1.21): card *Aus Datei* on the page *Assistenten*; a file
  (512 KB, 20 assistants) shows per assistant its way -- with `from` and a template the
  person may start at the same major, *Vorlage öffnen* posts the wizard pre-filled (only the
  `shape` parameters the template's assistant item takes `id`, `title`, `greeting`,
  `system`, `model` from; the host writes that map into `recipe-view.json`); otherwise a
  sentence. Nothing is stored before *Anlegen*.
- **chat 0.19.0**: *Aus Vorlage …* beside *+ Neuer Assistent* for a `tenant_admin`, to the
  portal's page (from `OAAP_PORTAL_URL`).

**Deviations from the text above:**

- **Import without `from` stays where it was** (§4): the portal does not store assistants;
  its sentence points to the chat or the MCP gateway, whose import already refuses an
  assistant whose view is missing (§6.5 held before this stage; measured again in the
  gateway's tests).
- **D10** needed nothing new: the chat has offered *Ins MCP-Gateway übernehmen* to the
  `tenant_admin` since chat 0.9.0; the portal page says where.

**Tests.** Reference `test_assistant_import` 33 new, `test_assistant_templates(_page)` green
(Linux runner); mcp-gateway `test_setup` 89 (6 new: header, `from` in export, present gets
the origin, `dry` remembers nothing, a broken header is ignored, `from` as an item field
refused), `test_gateway` 568 (6 new: import and save strip `from`, a broken `from`, the list
names it, `oaap.ai.assistants` 0.8); chat 238 (3 new).

**Measured on `oaap-test`** (0.1.338 staged, tenant `rzt`, `rzt-werkzeuge` 0.37.0, as its
tenant_admin through the job the portal calls and the portal's pages), 8/8:

1. Template *Leer* run with own id, title and three-line instructions: done.
2. The gateway remembered `assistent-leer@1` from the header, revision 1, no `from` in the
   assistant.
3. The export names `from: recipe:assistent-leer@1`.
4. *Aus Datei* with that export: *Vorlage öffnen* for Leer, the instructions with their lines.
5. The same entry without `from` and a missing view: the sentence naming the view, no template.
6. *Vorlage öffnen*: the wizard pre-filled with title, id and instructions.
7. The preview with the file's values: every step *present*.
8. Rolled back: the assistant deleted.

**Not measured:** a click in the browser by a person; the import into a **second** tenant
that then creates the view (the same template run as in stage 1, conformance 5 by
construction); the chat's link in a running chat (tested in `test_chat`, rzt's chat is
0.17.0).

## Deutsche Zusammenfassung

**Frage (Jörg, 21.11.):** Ein Assistent zum Anlegen von Assistenten für den
tenant_admin, mit Vorlagen wie Hilfe und Recherche, Export/Import nutzen.

**Befund:** Der Hilfe-Assistent kommt heute nicht aus einer App-Konfiguration,
sondern aus dem **Rezept** `hilfe-assistent` — fest verdrahtet (Titel, Text) und nur,
wenn der Betreiber das Rezept auf den Knoten kopiert und freigegeben hat. Textfelder
in Rezepten erlauben keine Zeilenumbrüche, Anweisungen sind also nicht anpassbar.
Der Export kennt die Sicht, aber nicht, wie sie entsteht.

**Vorschlag:** Eine Seite **„Assistenten → Neu“ im Portal**, vier Schritte: Vorlage
wählen → was fehlt → anpassen (Titel, Begrüßung, Anweisungen, Modell, Sichtbarkeit)
→ Vorschau und anlegen. Eine **Vorlage ist ein Rezept mit `offers: "assistant"`**,
dieselbe Maschine mit Vorschau und Rückbau. Mitgeliefert: Hilfe, Recherche, Leer
(ohne Werkzeuge). Vorlagen, die nur Vorhandenes im Mandanten anfassen, sind ohne
Freigabe nutzbar; Recherche (installiert, Suchwörter gehen hinaus) bleibt
freigabepflichtig. Der Export nennt künftig seine Vorlage (`from`), der Import öffnet
dann die Vorlage vorausgefüllt — so kommen Sicht, Profil und Modellfreigabe mit.

**Stufen:** 1 Seite + drei Vorlagen; 2 Export/Import; 3 eigene Vorlagen des
Mandanten („Als Vorlage speichern“).

**Entscheidungen D1–D10:** am 21.11. wie empfohlen angenommen (§9).

**Stufe 1 gebaut und gemessen (21.11., §10):** Referenz 0.1.336. Portal-Seite
„Assistenten“ mit Karten und Assistent; Vorlagen Hilfe 1.2.0 und Leer 1.0.0 frei,
Recherche 1.1.0 mit Freigabe; mehrzeilige Anweisungen (`prose`) nur im Text des
Assistenten. Auf oaap-test im Mandanten rzt als tenant_admin 13/13: eigener
Hilfe-Assistent mit dreizeiligen Anweisungen angelegt und zurückgenommen, Konflikt bei
vergebener Kennung, Recherche ohne Freigabe abgelehnt, Leer nach Update des MCP-Gateways
auf 0.35.0. Abweichungen: Sichtbarkeit nicht wählbar (nur „ganzer Mandant“), Kennung von
Hand statt automatisch „-2“, Übernahme der Chat-Assistenten (D10) in Stufe 2. Nicht
gemessen: Klick im Browser, Gespräch im Chat.

**Stufe 2 gebaut und gemessen (21.11., §11):** Ein Rezeptlauf nennt der Einrichtungstür
seine Vorlage (Kopfzeile `X-OAAP-Setup-Recipe`, Referenz 0.1.338). Das MCP-Gateway 0.37.0
merkt sich das am Assistenten; Export und Liste für den Chat nennen es als `from`. Im Portal
liest „Aus Datei“ eine exportierte Datei: Mit `from` öffnet „Vorlage öffnen“ den Assistenten
vorausgefüllt, sonst kommt ein Satz. Gespeichert wird erst mit „Anlegen“. Der Chat 0.19.0
und die Gateway-Seite haben für den tenant_admin den Link „Aus Vorlage …“. Auf oaap-test in
rzt 8/8: angelegt, Herkunft gemerkt, `from` im Export, Datei vorausgefüllt, Vorschau
„vorhanden“, zurückgenommen. Abweichungen: Ein Import ohne `from` läuft weiter über Chat
oder Gateway, die eine fehlende Sicht ablehnen. D10 gibt es im Chat schon seit 0.9.0. Nicht
gemessen: Klick im Browser, Import in einen zweiten Mandanten, der Link im laufenden Chat.
