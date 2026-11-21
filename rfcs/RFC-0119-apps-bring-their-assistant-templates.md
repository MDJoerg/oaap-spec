# RFC-0119: Apps Bring Their Own Assistant Templates

- **Status:** **Accepted (2026-11-21)** — D1–D11 as recommended (Jörg: "Wie empfohlen").
  **Stage 1 built and measured 2026-11-22 (§11):** reference 0.1.342, `oaap.apps.runtime`
  0.2.79 (manifest 0.20), `oaap.core.tenant` 1.23, `vorgaenge` 0.18.0 with the template
  `vorgaenge-ueberblick` 1.0.0.
  The facts in §1 were read the same day in `platform/recipes/hilfe-assistent.json`,
  `appctl.py` (`docs_publish_instance`, `SHIPPED_RECIPE_DIR`, `tenant_recipe_path`), the
  manifests of `oaap-apps/apps/*/oaap-app.yaml`, `oaap.ai.mcp-gateway` 0.35 §3.9e and
  RFC-0117.
- **Date:** 2026-11-21
- **Authors:** Jörg (the idea, 2026-11-21: "now that every app offers an MCP door, a
  simple way to create assistants: the wizard gets its templates from the apps. The apps
  know best what they can do and what a good prompt looks like. Installing an app alone
  brings new templates."), Claude (facts, design)
- **Depends on:** RFC-0117 (assistant templates and the wizard; a template is a recipe
  with `offers: "assistant"`), RFC-0073 (apps as MCP sources; `mcp:` in the manifest),
  RFC-0094 (an app brings its documentation; the node copies declared folders out of the
  package per tenant), RFC-0113 D2 (no default for a light), RFC-0118 (MCP read tools are
  a duty for apps with data; `check-design.py`)
- **Changes (when accepted):** `oaap.apps.runtime` (manifest 0.20: `assistant_templates`);
  `oaap.core.tenant` (templates from apps: where they are read, the narrower rules of §4,
  the server light asked in the wizard); the portal page *Assistenten* (origin on the card,
  "Vorlage nicht mehr da"); `check-design.py` (a duty with written exceptions); first
  templates in `oaap-apps`
- **Not part of this RFC:**
  - **A new wizard or a new format.** App templates are RFC-0117 templates; the wizard, the
    preview, the run and the rollback stay as they are.
  - **Templates that span several apps** (e.g. cases together with the twin). Stage 3 at
    the earliest (§8).
  - **Writing tools in app templates.** Reading only until RFC-0105 approvals are part of
    the template road (§4.3, D4).
  - **A marketplace for templates.** RFC-0117 put that off; this RFC does not change it.

## Summary

Since RFC-0118, 18 of the 24 apps in `oaap-apps` have an MCP door. Each knows best which of
its tools answer which question and how an assistant should use them — yet today a tenant
admin gets an assistant only from the three templates the platform ships (Hilfe, Recherche,
Leer). For "an assistant that keeps track of our open cases" someone has to write a recipe.

This RFC proposes that **an app ships assistant templates in its package**, declared in the
manifest (`assistant_templates:`), the same way it ships its documentation (`docs:`). The
node copies them per tenant at install, update and removal. In the portal's page
*Assistenten* they appear as cards next to the platform's own, marked *"von App X"*. The
person runs them through the RFC-0117 wizard unchanged.

An app's template is **narrower than a platform template**: it may only build a view of its
own app's reading tools, a profile for the chat and the assistant, and release a model name.
It cannot install anything, bind a destination, touch another app or set its own server's
light — if that light is still red, the wizard asks the human (§4).

## 1. Facts (read 2026-11-21)

### 1.1 Templates today

Three shipped templates in `platform/recipes/` (`hilfe-assistent` 1.2.0, `recherche`
1.1.0, `assistent-leer` 1.0.0), read in place from `SHIPPED_RECIPE_DIR`; an operator's file
of the same id in `/var/lib/oaap/recipes` wins at the same or a higher version
(`tenant_recipe_path`). Both folders are node-wide: every tenant sees the same templates.

### 1.2 The help template sets a light itself

`hilfe-assistent` runs `refresh` and `server_light: green` for the help server, then the
view `hilfe` with `tools: {server, effect: "read"}`, the chat's profile and the assistant.
The light is justified because the server is the platform's own help over the platform's
own docs. The setup door changes a server's light only from the `red` every new server
starts with; another light a human set is a conflict (`oaap.ai.mcp-gateway` §3.9e).

### 1.3 Apps already bring files per tenant

`docs:` (manifest 0.17, RFC-0094): `docs_publish_instance` copies exactly the declared
folders out of the unpacked package into `<tenant>/docs/<instance id>/<version>/` at every
install, update and promotion, drops them at removal, and writes an index. Nothing is
fetched at runtime; what is copied is what was tested in the package.

### 1.4 MCP doors in the apps

`mcp:` in 18 manifests: ai-gateway, fleetview, help, marketplace, mitarbeiterverwaltung,
ollama-models, package-catalog, partnerverwaltung, projekt, raci, recherche, rollen-rechte,
spezialisten, store-editor, studio, vorgaenge, vpn-client, wegweiser. A gateway of the same
tenant finds each in its source list; the catalog is read without a person, calls carry the
person (RFC-0073 §16). The twin is a platform service with its own door (`oaap.data.twin`
0.9 §2.16), not an app.

### 1.5 MCP prompts are not assistants

The gateway serves an MCP server's `prompts` in a view like tools. A prompt is a text
with arguments a client fills; it has no view, greeting, model or light. It can be part of
what an assistant uses, not a replacement for one.

## 2. The idea in one picture

```
App package (tested)                      Node                         Portal
  oaap-app.yaml                            install / update             Assistenten
    assistant_templates:                   ─────────────────►           ┌──────────────────────┐
      path: assistants/                    <tenant>/assistant-          │ Hilfe     (Plattform)│
  assistants/                              templates/<instance>/        │ Leer      (Plattform)│
    vorgaenge-ueberblick.json              <version>/*.json             │ Offene Vorgänge      │
                                                                         │      (von Vorgänge) │
                                           removal: folder gone         └──────────────────────┘
                                                                          → RFC-0117 wizard
```

## 3. What an app ships

### 3.1 Manifest (0.20)

```yaml
assistant_templates:
  path: assistants/        # folder in the package, one JSON file per template
```

Its own top-level key (not under `mcp:`), because nodes before manifest 0.20 refuse unknown
keys inside a block — the same reason `mcp_content` is its own block (runtime 2.32.6). A
manifest with `assistant_templates` but without `mcp:` is refused at install.

### 3.2 A template file

An ordinary RFC-0117 template, for example in `vorgaenge`:

```json
{
  "recipe": "oaap.tenant-recipe/1",
  "id": "vorgaenge-ueberblick",
  "version": "1.0.0",
  "offers": "assistant",
  "card": {"title": "Offene Vorgänge",
           "summary": "Sagt, was in den Bereichen offen ist, sucht Vorgänge und fasst einen zusammen.",
           "light": "yellow", "icon": "inbox"},
  "needs": {
    "app":    {"app": "vorgaenge",   "label": "Vorgänge"},
    "tools":  {"app": "mcp-gateway", "label": "Werkzeuge (MCP-Gateway)"},
    "models": {"app": "ai-gateway",  "label": "Modelle (KI-Gateway)"},
    "chat":   {"app": "chat",        "label": "Chat"}
  },
  "params": {
    "title":    {"kind": "text",  "max": 60, "default": "Vorgänge", "shape": true},
    "aid":      {"kind": "word",  "default": "vorgaenge", "shape": true},
    "greeting": {"kind": "prose", "max": 600, "shape": true,
                 "default": "Ich sage dir, was in deinen Bereichen offen ist, und fasse Vorgänge zusammen."},
    "system":   {"kind": "prose", "max": 8000, "shape": true,
                 "default": "Du bist der Assistent „Vorgänge“. Bereiche mit list_queues, suche mit search_cases, lies mit get_case …"},
    "model":    {"kind": "setup_item", "need": "models", "item_kind": "alias", "default": "standard", "shape": true},
    "server_light": {"kind": "light", "label": "Ampel der Vorgänge-Quelle im MCP-Gateway"},
    "ceiling":  {"kind": "light", "from": "model", "default": "yellow"}
  },
  "steps": [
    {"id": "freigabe", "type": "app.setup", "name": "{models}",
     "items": [{"kind": "client", "id": "{chat_key}", "aliases": ["{model}"],
                "ceiling": "{ceiling}", "personal_data": true, "tenant": "{tenant}"}]},
    {"id": "werkzeuge", "type": "app.setup", "name": "{tools}",
     "items": [{"kind": "refresh", "id": "{app_key}"},
               {"kind": "server_light", "id": "{app_key}", "light": "{server_light}"},
               {"kind": "view", "id": "{aid}", "accesses": ["platform"],
                "tools": {"server": "{app_key}", "effect": "read"}},
               {"kind": "profile", "id": "{chat_key}", "group": "@{chat_key}",
                "views": ["{aid}"], "ceiling": "{ceiling}"},
               {"kind": "assistant", "id": "{aid}", "title": "{title}", "view": "{aid}",
                "gateway": "{tools_key}", "model": "{model}",
                "greeting": "{greeting}", "system": "{system}", "visibility": "tenant"}]}
  ]
}
```

The need that names the shipping app is called **`app`** by convention; §4 checks that it
names the app whose package the file came from.

## 4. Rules for a template from an app

### 4.1 What the node does

1. At install, update and promotion the node copies the declared folder out of the
   unpacked package to `<tenant>/assistant-templates/<instance id>/<version>/`, like
   `docs_publish_instance`; at removal it deletes it (D2). A rehearsal instance (RFC-0030)
   copies nothing.
2. Each file is checked at copy time with the recipe check plus §4.2–4.4; a file that fails
   is not copied, and install says so (`WARNING: assistant template '<id>' not handed over:
   <sentence>`), like a dropped documentation product. The install itself does not fail.
3. The audit trail of the tenant gets one row `instance.assistant_templates` with the ids
   and versions.

### 4.2 Names

- The template's `id` starts with the shipping app's `app_id` and a dash
  (`vorgaenge-ueberblick`) (D7). So two apps cannot collide, the operator's release key
  stays `recipe:<id>@<major>`, and the gateway's `X-OAAP-Setup-Recipe` keeps its form.
- An operator's file or a platform template of the same id wins (RFC-0117 D7 keeps
  holding).

### 4.3 Allowed steps (D3, D4)

| Step | Allowed | Why |
|---|---|---|
| `app.setup` at the need `models` (ai-gateway) | `client` with the chat's key | the assistant needs a model name |
| `app.setup` at the need `tools` (mcp-gateway) | `refresh` and `server_light` of **the app's own server** (`{app_key}`); `view` whose tools all come from that server with `effect: "read"`; `profile` for the chat naming only that view; exactly one `assistant` naming that view | everything an assistant on the app's tools needs |
| `app.install`, `destination.ensure`, `app.setup` at any other need, a `server` or `system` item, a view with resources from another server | **refused** | an app speaks for itself, never for the tenant's other apps or outside hosts |

### 4.4 The light of the app's own server (D5)

Every new server starts `red`. A platform template may set its own help server green
(§1.2); an app's template may **not choose** the light of its own server — the app would be
judging itself. Instead:

- `server_light` must be a param of kind `light` **without default** (RFC-0113 D2).
- If the server already has a light, the wizard shows it and the step is *vorhanden*.
- If the server is still `red`, step 2 (*Was fehlt*) asks the tenant admin: "Die Quelle
  *Vorgänge* steht im MCP-Gateway auf Rot. Welche Ampel soll sie bekommen?", with the card's
  light shown as **the app's proposal**, not pre-selected. Red stays a valid answer; then
  the assistant exists but the chat's profile ceiling decides whether it can use the view.
- The light of the card is still computed from the steps (RFC-0117 §6.4); for an app
  template the card's light is the app's proposal for its server.

### 4.5 Release (D6)

An app template that passes §4.3 is **free** for the tenant admin in the sense of RFC-0117
D4: it installs nothing, reaches no outside host, and the person sees every word of the
instructions in step 3 before anything is created. The operator can withdraw templates of
an app per tenant (`oaap tenant templates <tenant> --block <app_id>`), then the card says
"vom Betreiber gesperrt".

## 5. The wizard (changes to RFC-0117 §3)

- **Step 1:** cards of app templates under a heading per app ("Aus deinen Apps"), with the
  app's name and icon; platform templates first.
- **Step 2:** if the tenant has several instances of the app, the person picks one (the
  need `app` like any other need). The template of the **newest** installed version is
  used. The server light of §4.4 is asked here.
- **Steps 3 and 4:** unchanged.
- **The page *Assistenten*** marks an assistant whose template has gone ("Vorlage nicht
  mehr da — die App wurde entfernt") and one whose template is newer ("Vorlage neuer")
  (RFC-0117 D8 holds: nothing changes by itself).

## 6. When an app is updated or removed (D9)

- **Update:** new template files replace the old ones in the tenant. Assistants made from
  them stay as they are; the page says "Vorlage neuer".
- **Removal:** the folder is gone, the card disappears. Assistants made from it stay; their
  view now names a server the gateway no longer finds. What the gateway does with such
  entries today was not read for this draft; stage 2 measures it and, if needed, makes the
  chat say "Die Werkzeuge dieses Assistenten gibt es nicht mehr". The page says so.

## 7. Duty in the design rules (D10)

`check-design.py` gains one rule: an app with `mcp:` ships at least one assistant template,
or names its exception in the manifest comment `# design: no-assistant-template <reason>`
(as for `docs:` today). Expected exceptions: `ollama-models`, `vpn-client`,
`package-catalog` (operator tools without a question a tenant's person would ask).

## 8. Stages

| Stage | What | Done when |
|---|---|---|
| **1** | manifest 0.20 `assistant_templates`; node copies per tenant, checks §4.2–4.3 at copy time; portal lists them with origin; server light asked in step 2; first template `vorgaenge-ueberblick` | §9 lines 1–6 on oaap-test |
| **2** | templates for the apps with data (vorgaenge, partnerverwaltung, projekt, mitarbeiterverwaltung, rollen-rechte, raci, fleetview, wegweiser, studio, marketplace, spezialisten, help); `check-design.py` duty; "Vorlage nicht mehr da / neuer"; the operator's block per app | check-design 24/24 with the new rule; §9 lines 7–8 |
| **3** | writing tools in app templates with RFC-0105 approvals; MCP prompts of the app's server in the view (D11); templates that span apps; a platform template for the twin | separate decisions when stage 2 stands |

## 9. Conformance (described; every line gets a bait)

1. Install `vorgaenge` with a template in a tenant → the card *Offene Vorgänge (von
   Vorgänge)* appears only in that tenant. *Bait:* a second tenant on the node → no card.
2. Run it with own title → view of the app's reading tools, chat profile, assistant;
   conversation lists open cases. *Bait:* the view would hold a writing tool → refused at
   copy time.
3. A template whose `id` does not start with the app's id → not copied, install warns.
4. A template with `destination.ensure` or `app.install` → not copied, install warns.
5. The source is still red → step 2 asks the light, nothing pre-selected; the person picks
   yellow → the setup door sets it. *Bait:* a template giving `server_light` a default →
   not copied.
6. The source has a light a human set → step shows *vorhanden*, nothing changed.
7. App update with template 1.1.0 → card shows 1.1.0, the assistant made from 1.0.0 is
   unchanged, the page says "Vorlage neuer".
8. App removed → card gone, assistant still listed with "Vorlage nicht mehr da".

## 10. Decisions

*Accepted 2026-11-21: D1–D11 as recommended.*

- **D1 — An app ships templates in its package, declared in the manifest — not served at
  runtime by its MCP door?** *Recommendation: package.* What is copied is what was tested
  with the app, the node can check it once at install, and it works without a running
  instance. Same road as `docs:`.
- **D2 — App templates are visible only in the tenant where the app is installed, copied
  per instance?** *Recommendation: yes.* The platform's and the operator's templates stay
  node-wide.
- **D3 — An app template may only build what an assistant on the app's own tools needs
  (§4.3)?** *Recommendation: yes.* No install, no destination, no other app.
- **D4 — Reading tools only, until RFC-0105 approvals are part of the template road?**
  *Recommendation: yes* (stage 3).
- **D5 — An app never chooses its own server's light; a red source is asked of the tenant
  admin with the app's proposal shown, not pre-selected?** *Recommendation: yes*
  (RFC-0113 D2).
- **D6 — App templates that pass §4.3 are free for the tenant admin; the operator can block
  an app's templates per tenant?** *Recommendation: yes.* The alternative — every app
  template needs the operator's release — would make "installing an app brings templates"
  a request form.
- **D7 — The template's id starts with `<app_id>-`?** *Recommendation: yes*; no new id form,
  release key and header stay as they are.
- **D8 — Several instances of one app: one card, the instance chosen in step 2, the newest
  version's file used?** *Recommendation: yes.*
- **D9 — Update replaces the templates, removal deletes them; assistants made from them
  never change by themselves?** *Recommendation: yes* (RFC-0117 D8).
- **D10 — `check-design.py` makes one template a duty for apps with `mcp:`, with written
  exceptions?** *Recommendation: yes, in stage 2* — so that "every app with data has an
  assistant" holds the way "every app has help" holds.
- **D11 — MCP prompts of the app's server may be named in the template's view, as an
  addition, never instead of a template?** *Recommendation: yes, stage 3.*

## 11. Stage 1 — built and measured (2026-11-22)

**Built.**

- **Node (reference 0.1.342, `oaap.apps.runtime` 2.41):** manifest 0.20
  `assistant_templates: {path}` (refused without `mcp.path`, with another field, with a path
  leaving the package). New module `app_templates.py` (pure rules: declaration, §4.2–4.4,
  extract, listing). At every install the node copies the valid templates to
  `tenants/<tenant>/assistant-templates/<instance id>/` with `templates.json`, says what it
  dropped and why, never fails the install; removal deletes the folder; a rehearsal copies
  nothing; audit `instance.assistant_templates`.
- **Recipes (`oaap.core.tenant` 1.23):** `tenant_recipe_path(rid, tid)` finds an app's
  template of that tenant when neither the operator nor the platform has the id; preview,
  run, continue, rollback and requests use it. `recipe_is_free(doc, tid)`: free when the doc
  equals the file the app brought and §4.3 still holds. For an app's template the preview
  reads the app server's light from the gateway's setup door (`GET ?kind=server_light`): not
  red → that light is taken; red or unknown → the parameter stays open, the card's light as
  `suggested` with `proposal: "app"`.
- **Portal:** rows of app templates carry `tenant` (shown only there) and `app`; the page
  *Assistenten* shows platform cards first, then "von der App …"; the wizard asks a light
  without default and without `from` under *Was gebraucht wird*, with "– bitte wählen –" and
  nothing selected, and says whether the source is red (the app's proposal named) or already
  set by a human.
- **`vorgaenge` 0.18.0** (manifest 0.20) brings `assistants/vorgaenge-ueberblick.json` 1.0.0:
  view `vorgaenge` of the app's reading tools, profile `<chat>-vorgaenge` (reading only), the
  assistant with instructions naming `list_queues`, `list_cases`, `search_cases`, `get_case`.

**Deviations from the text above.**

- **The need naming the app is `source`, not `app`** (§3.2, §4.3): `app` is a reserved word
  of the recipe engine (the selection reference). The placeholder is `{source_key}`.
- **The template releases no model** (§3.2): it names the model gateway only to offer its
  list of model names; the chat must already be released for the chosen name (the help
  template does that). A model release would conflict with the chat's existing one and is the
  model gateway's decision, not an app's — and it would carry `personal_data`, which an app
  must not decide either.
- **The operator's block per app** (§4.5) and the marks "Vorlage nicht mehr da / neuer" (§5,
  §6) are stage 2, as the stage table says.

**Tests.** Reference `test_app_templates.py` new (Linux runner): manifest 0.20, the
template of `vorgaenge` against the rules, 13 baits (§4.2–4.4), copy per tenant with a dropped
file and a link not followed, which file wins, the gate (free in its tenant, not changed, not
in another tenant), the view and cards, the light question (red → asked, chosen → set, human's
green → taken), removal and rehearsal. With 28 neighbouring files (recipes, templates, portal,
manifest doors) 29 files green. `vorgaenge` `test_app`, `test_mcp` green; `check-design.py`
24/24; `check-store.py` after `--fix` of the README table.

**Measured on `oaap-test`** (0.1.342 staged after a backup; `vorgaenge` 0.18.0 installed
fresh into tenant `rzt` as `rzt-vorgaenge`; as its tenant_admin through the job the portal
calls and the portal's pages), 13/13:

1. The install said "Assistant template 'vorgaenge-ueberblick' 1.0.0 handed to the tenant's
   wizard"; `templates.json` names it, nothing dropped.
2. Tenant `vuebung`: no template of the app.
3. The view for the portal: tenant `rzt`, app *Vorgänge*, free.
4. Page *Assistenten* in `rzt`: card *Offene Vorgänge*, "von der App Vorgänge", *Weiter*.
5. The wizard asks the source's light: "– bitte wählen –", nothing selected.
6. Preview without a light: the question stays open, the app's proposal yellow, nothing chosen.
7. Preview with yellow: no conflict.
8. Run as tenant_admin without a release: done.
9. The gateway: the assistant on view `vorgaenge`, origin `vorgaenge-ueberblick@1`.
10. The view holds only reading tools — no `create_case`, no `comment_case`.
11. The source now has the chosen light yellow.
12. *Bait:* the same template in `vuebung` (no app there), even as the operator → refused.
13. Rolled back: the assistant deleted.

Then `oaap app remove rzt-vorgaenge`: the tenant's template folder and the portal row gone;
node HEALTHY 8/8, 43/43.

**Not measured:** a click in the browser by a person; a conversation with the new assistant in
the chat (a person's call through a gateway view, still open since RFC-0118 P6).

## Deutsche Zusammenfassung

**Idee (Jörg, 21.11.):** Seit RFC-0118 hat jede App mit Daten eine MCP-Tür. Die App weiß
selbst am besten, was sie kann und wie ein guter Prompt aussieht. Also soll sie ihre
Assistenten-Vorlagen mitbringen: Wer eine App installiert, bekommt im Assistenten-Wizard
neue Vorlagen dazu.

**Befund:** Der Wizard (RFC-0117) kennt heute nur drei Vorlagen der Plattform (Hilfe,
Recherche, Leer). Sie gelten knotenweit für alle Mandanten. 18 der 24 Apps haben eine
MCP-Tür. Für ihre Hilfe-Seiten gibt es schon den Weg, den wir brauchen: Das Manifest nennt
einen Ordner (`docs:`), und der Knoten kopiert ihn bei Installation und Update je Mandant
aus dem geprüften Paket.

**Vorschlag:**
- Eine App nennt im Manifest `assistant_templates: {path: assistants/}`. Der Knoten kopiert
  die Vorlagen je Mandant, genau wie die Doku, und prüft sie dabei. Eine Vorlage, die gegen
  die Regeln verstößt, wird nicht übernommen und die Installation warnt.
- Auf der Portal-Seite *Assistenten* erscheinen die Vorlagen als Karten „von App X“, nur im
  Mandanten, in dem die App installiert ist. Der Wizard läuft wie bisher.
- Eine App-Vorlage darf **weniger** als eine Vorlage der Plattform: nur eine Sicht auf die
  **lesenden** Werkzeuge der eigenen App, das Profil des Chats, den Assistenten und die
  Freigabe eines Modellnamens. Sie installiert nichts, legt keine Ziele nach außen an und
  fasst keine andere App an.
- Die **Ampel der eigenen Quelle** setzt die App nicht selbst. Steht die Quelle noch auf
  Rot, fragt der Wizard den tenant_admin. Der Vorschlag der App ist dabei zu sehen, aber
  nicht vorausgewählt.
- Solche Vorlagen sind ohne Freigabe des Betreibers nutzbar. Der Betreiber kann die
  Vorlagen einer App je Mandant sperren.
- Ein App-Update bringt neue Vorlagen, bestehende Assistenten bleiben unverändert („Vorlage
  neuer“). Wird die App entfernt, verschwindet die Karte, und die Seite vermerkt am
  Assistenten „Vorlage nicht mehr da“.
- `check-design.py` verlangt ab Stufe 2 von jeder App mit MCP-Tür mindestens eine Vorlage
  oder eine schriftliche Ausnahme.

**Stufen:**
1. Manifest, Kopie je Mandant, Prüfung, Karten mit Herkunft, Ampelfrage, erste Vorlage in
   *Vorgänge*.
2. Vorlagen für die Apps mit Daten, Pflicht in check-design, Hinweise bei Update und
   Entfernen, Sperre durch den Betreiber.
3. Schreibende Werkzeuge mit Freigabe nach RFC-0105, MCP-Prompts, Vorlagen über mehrere
   Apps, eine Vorlage für den Zwilling.

**Entscheidungen D1–D11 (§10):** am 21.11. wie empfohlen angenommen. Die wichtigsten:
- D1: aus dem Paket, nicht zur Laufzeit von der MCP-Tür
- D3/D4: eng, nur lesend
- D5: keine Ampel durch die App selbst
- D6: frei, aber vom Betreiber sperrbar

**Stufe 1 gebaut und gemessen (22.11., §11):** Referenz 0.1.342, Manifest 0.20. Der Knoten
kopiert die Vorlagen einer App bei der Installation in den Ordner des Mandanten, prüft sie und
nennt, was er fallen lässt; beim Entfernen verschwinden sie. Im Portal erscheinen sie nur in
diesem Mandanten als Karte „von der App …“; die Ampel der eigenen Quelle fragt der Assistent
(nichts vorausgewählt, Vorschlag der App daneben), hat ein Mensch sie schon gesetzt, gilt seine.
Erste Vorlage: `vorgaenge-ueberblick` in Vorgänge 0.18.0. Auf oaap-test in rzt 13/13: Karte da,
Ampelfrage, angelegt ohne Freigabe, Sicht nur mit lesenden Werkzeugen, Quelle auf Gelb, im
Mandanten vuebung abgelehnt, zurückgenommen; nach dem Entfernen der App ist die Karte weg.
Abweichungen: Der Bedarf heißt `source` (`app` ist in der Rezept-Maschine reserviert); die
Vorlage gibt kein Modell frei (das bleibt Sache des KI-Gateways). Sperre durch den Betreiber und
die Hinweise „Vorlage neuer / nicht mehr da“ kommen in Stufe 2. Nicht gemessen: Klick im
Browser, Gespräch im Chat.
