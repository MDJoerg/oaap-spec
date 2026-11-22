# RFC-0119: Apps Bring Their Own Assistant Templates

- **Status:** **Accepted (2026-11-21)** — D1–D11 as recommended (Jörg: "Wie empfohlen").
  **Stage 1 built and measured 2026-11-22 (§11):** reference 0.1.342, `oaap.apps.runtime`
  0.2.79 (manifest 0.20), `oaap.core.tenant` 1.23, `vorgaenge` 0.18.0 with the template
  `vorgaenge-ueberblick` 1.0.0.
  **Stage 2 built and measured 2026-11-22 (§12):** reference 0.1.343, `oaap.core.tenant`
  1.24; ten more apps bring a template; `check-design.py` makes it a duty.
  **§6 closed 2026-11-22 (§13):** mcp-gateway 0.41.0 (`oaap.ai.mcp-gateway` 0.36), chat 0.21.0
  (`oaap.ai.assistants` 0.9).
  **Stage 3 decided 2026-11-22 (§10, D12–D16):** split into 3a–3d; Jörg: "E3: nein, aber
  vielleicht als Draft mit Freigabe? Sonst wie empfohlen."
  **Stage 3a built and measured 2026-11-22 (§14):** reference 0.1.344, `oaap.core.tenant` 1.25,
  mcp-gateway 0.42.0 (`oaap.ai.mcp-gateway` 0.37); ten templates name their app's prompts.
  **Stage 3b built and measured 2026-11-22 (§15):** reference 0.1.345, `oaap.core.tenant` 1.26,
  mcp-gateway 0.43.0 (`oaap.ai.mcp-gateway` 0.38), `vorgaenge` 0.19.0 (template 2.0.0); with it a
  correction to 3a (`commands: true`, §15).
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
| **3** | writing tools in app templates with RFC-0105 approvals; MCP prompts of the app's server in the view (D11); templates that span apps; a platform template for the twin | separate decisions when stage 2 stands — taken 2026-11-22 (D12–D16), stage 3 is split: |
| **3a** | MCP prompts of the app's own server in the template's view (D11); a need can ask for a minimum version of its app | the ten templates of apps with prompts name them; measured on oaap-test |
| **3b** | writing tools of the app's own server in an app template (D13): each one a separate tick in the wizard, none ticked beforehand; in the chat the existing confirmation per call | measured on oaap-test with `vorgaenge` (`create_case`, `comment_case`) |
| **3c** | templates that span apps — from the platform only (D15); a platform template for the twin (D16) | measured on oaap-test |
| **3d** | to be examined: an app template proposes a specialist (RFC-0105) only as a **draft** that a human releases (D14) | a design read against `spezialisten` first; separate go-ahead |

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

### Stage 3 (decided 2026-11-22)

Facts read for these decisions: writing tools in app MCP doors exist today only in
`vorgaenge` (`create_case`, `comment_case`; `help` writes through its separate maintenance
door, `recherche` reaches the open web). Prompts are served by 16 apps through `mcpdoor`
(`DOOR.prompt`) and by `help`; the chat offers a view's prompts as `/name …`. The twin is an
MCP source with three reading tools (`oaap.data.twin` 0.9 §2.16). The RFC-0105 approvals
(`required`, `signed`) are made for a **specialist** that writes without a person present;
in the chat a person confirms every writing call before it runs (`oaap.ai.assistants` §2).
*Corrected 2026-11-22 (stage 3b):* the **chat** enforces that confirmation; the gateway only
records `X-OAAP-Confirmed` in the usage row, "never a permission" (`oaap.ai.assistants` §5) --
the first version of this paragraph said the gateway checks it.

- **D12 — Split stage 3 into 3a (prompts), 3b (writing tools), 3c (templates that span
  apps, the twin), each measured and pushed on its own?** *Accepted.*
- **D13 — Writing tools in a chat assistant from an app template:** the template may name
  writing tools of the app's **own** server; step 2 of the wizard shows them in a box of
  their own, the tenant admin ticks each one, none is ticked beforehand; in the chat the
  existing confirmation per call applies; the template stays free (D6). D4 is replaced by
  this for stage 3b. *Accepted.*
- **D14 — May an app template create a specialist (RFC-0105, writing in the background)?**
  *No.* Jörg: "nein, aber vielleicht als Draft mit Freigabe?" — to be examined as stage 3d:
  a template proposes a specialist only as a draft that does nothing until a human releases
  it. The reference to RFC-0105 approvals leaves stages 3a–3c.
- **D15 — Templates that span several apps come from the platform only;** an app speaks
  for itself; the light of each source involved is asked separately, without default.
  *Accepted.*
- **D16 — A platform template for the twin, which does not set its own light** (the help
  template may, because it reads public documentation; the twin holds the tenant's data).
  *Accepted.* Jörg added (2026-11-22): the twin's MCP door will also get **writing**
  functions (creating and changing types and instances from the chat, for authorized
  persons only), and a broad **REST API** of the twin (evaluate, model, create, change) is
  one of his next requirements — the twin as an integrating part of a larger landscape where
  the data grow together. Both belong to `oaap.data.twin` and a separate RFC. For this RFC
  it means: the twin template of 3c reads; once the twin offers writing tools they enter the
  template by the D13 road (a separate tick each, confirmation per call), never silently.

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

## 12. Stage 2 — built and measured (2026-11-22)

**Built.**

- **Templates for the apps with data** (`oaap-apps`, manifest 0.20, each `assistants/` with one
  template 1.0.0, reading tools only, the light of the own source asked):
  `partnerverwaltung-auskunft` (0.3.0), `mitarbeiterverwaltung-auskunft` (0.3.0),
  `projekt-stand` (0.3.0), `raci-wer-ist-zustaendig` (0.3.0), `rollen-rechte-wer-darf-was`
  (0.4.0), `fleetview-lage` (1.2.0), `wegweiser-links` (0.6.0), `studio-vorhaben` (0.8.0),
  `marketplace-katalog` (0.5.0), `spezialisten-ueberblick` (0.6.0); with `vorgaenge-ueberblick`
  eleven. The card's light (the app's proposal) is yellow where the data names persons or
  customers, green for fleet, links, projects of the studio and the catalogue.
- **Duty (D10):** `check-design.py` rule `template`: an app with `mcp:` ships at least one
  template, or stands in `NO_TEMPLATE` with its reason. 24/24.
- **Block (§4.5, reference 0.1.343):** `oaap tenant templates <tenant>` lists what the apps
  brought and what was dropped; `--block <app_id>` / `--unblock` (server_admin only, audited,
  `app_templates_blocked` in the tenant record). Blocked: not free, the gate refuses even with
  a release, the card says "vom Betreiber gesperrt" without the request button; the operator
  can still run it.
- **Marks (§5, §6):** a run from an app's template records `app` (id, name, instance). The page
  *Assistenten* keeps listing such runs after the template is gone and marks a finished run
  "Vorlage neuer (x.y.z)" or "Vorlage nicht mehr da – die App wurde entfernt; ihre Werkzeuge
  gibt es nicht mehr"; a rolled-back run gets no mark.

**Deviations from the text above.**

- **The exceptions stand in `check-design.py` (`NO_TEMPLATE`), not as a manifest comment**
  (§7): an exception then changes no package. Seven: `ai-gateway`, `ollama-models`,
  `package-catalog`, `vpn-client`, `store-editor` (operator tools), and **`help` and
  `recherche`**, which the stage table listed or did not name: the platform already ships the
  templates `hilfe-assistent` and `recherche` for exactly these sources; a second template from
  the app would build a second view of the same tools.
- **"Vorlage neuer" holds for platform templates too:** an older finished run of
  `hilfe-assistent` 1.0.0/1.1.0 now says "Vorlage neuer (1.2.0)". That is the same rule
  (RFC-0117 D8: nothing changes by itself, the page says so); measured on oaap-test.

**§6 measured — what the gateway does when the app is removed:** nothing by itself. The
server row stays (with its light), the view keeps its four tool rows, the assistant stays
active. The page says "Vorlage nicht mehr da … ihre Werkzeuge gibt es nicht mehr"; what the
chat says when a person then calls the assistant was **not** measured. Making the gateway
notice a server whose instance is gone is work in `mcp-gateway`, not in this RFC's stage 2.

**Tests.** `test_app_templates.py` extended (Linux runner): every template in `oaap-apps`
against the rules with a valid manifest (11), the block (a tenant_admin may not block; card,
gate, a release does not beat it, the portal neither; the other tenant untouched; unblock),
the run records the app, "Vorlage neuer (1.1.0)" after an update, "Vorlage nicht mehr da"
after removal, no mark after a rollback. With the 28 neighbouring files 29 green. The ten apps'
own tests green (fleetview's version check adjusted; wegweiser once 205/206, then twice
206/206); `check-design.py` 24/24 with a bait (folder removed → `template` error);
`check-store.py` after `--fix`.

**Measured on `oaap-test`** (0.1.343 staged after a backup; tenant `rzt`; `vorgaenge` 0.18.0
and `wegweiser` 0.6.0 installed fresh; as its tenant_admin through the job the portal calls
and the portal's page), 16/17 — the one red line was the measurement's own too-wide check
(it found the correct "Vorlage neuer" of the older help runs above); the row of the new run
itself read "von der App Vorgänge" with no mark:

1. Both installs handed their template to the tenant.
2. `oaap tenant templates rzt` names both, nothing dropped.
3. Page *Assistenten*: both cards with *Weiter*.
4. `--block wegweiser`: the card says "vom Betreiber gesperrt", no *Weiter*, no request.
5. *Bait:* the tenant_admin calls the job anyway → refused.
6. *Bait:* with a release of the operator → still refused.
7. The operator sees the preview.
8. `--unblock`: *Weiter* again.
9. The tenant's log has block and unblock.
10. Run as tenant_admin: done; the run names the app.
11. (see above)
12. Update to a probe package 0.18.1 with template 1.1.0: "Vorlage neuer (1.1.0)", card 1.1.0.
13. The assistant in the gateway unchanged (origin `vorgaenge-ueberblick@1`, same instructions).
14. `oaap app remove rzt-vorgaenge`: card gone, the run listed with "Vorlage nicht mehr da".
15. §6 as above.
16. Rolled back: the assistant deleted (the light back to red, the view gone).
17. No mark on the rolled-back run.

Both instances removed afterwards; node HEALTHY 8/8, 43/43.

**Not measured:** a click in the browser by a person; a conversation with an app's assistant
in the chat, and what the chat says after the app is gone.

## 13. §6 closed — a removed app's tools (2026-11-22)

**The finding of §12, read again in the code:** the gateway already marked a source that left
the platform's list (`servers.gone`, RFC-0073 D2) -- but only at its next sync (every five
minutes; the measurement of §12 looked at once), and even then it kept listing the entries:
`item_state` read only the catalog, and the catalog still said "present", read while the app
existed. The assistant stayed active, so a chat would have sent the model tool names whose
calls go nowhere.

**Built.**

- **mcp-gateway 0.41.0** (`oaap.ai.mcp-gateway` 0.36, §3.6, §4.2): a new entry state **`gone`**
  -- the entry's server is a platform source no longer in the list. Neither listed nor
  callable; a call is refused with "… gibt es nicht mehr: die App dahinter wurde entfernt",
  never naming the server; one audit line `item.gone` per entry; the entries stay in the views
  (nothing removed in silence) and are active again when the source returns with the same
  text. The list of assistants for a chat names **`tools_gone`** (`all` / `some`); the operator's
  start page names the view ("Quelle entfernt"), its page *Assistenten* the assistant.
- **chat 0.21.0** (`oaap.ai.assistants` 0.9): with `tools_gone: all` no new conversation (409)
  and a running one answers "Die Werkzeuge dieses Assistenten gibt es nicht mehr – die App
  dahinter wurde entfernt. Wer ihn pflegt, kann ihn löschen oder ihm eine andere Sicht geben.";
  with `some` the conversation goes on; the card says it and disables *Neues Gespräch*.

**Not built, on purpose:** the platform does not poke the gateway at `oaap app remove`. The
gateway learns of the removal at its next sync (at most five minutes, or the operator's button
"Quellen jetzt einlesen"); until then a call fails at the removed container, as before. A poke
would be a new coupling from the platform into one app's command line for a window of five
minutes.

**Tests.** `test_sources.py` +11 (gone, not listed, refusal without the server, `item.gone`,
start page, `all`/`some`, bait: no view / no gone source, back → active); `test_gateway.py`
586/586 (one fixture's fake list lacked the source's address -- the real list always names it --
and so made the source "gone" mid-test; fixed in the fixture); all 13 gateway test files green;
`test_chat.py` 249/249 (+5, with the bait `some`); `check-store.py`, `check-design.py` 24/24.

**Measured on `oaap-test`** (backup first; tenant `rzt`; `rzt-werkzeuge` 0.41.0, `rzt-chat`
0.21.0; `vorgaenge` 0.18.0 installed fresh), 12/12: assistant from `vorgaenge-ueberblick`;
before: five entries active, four tools listed; right after the removal, before the sync,
still active (the five-minute window above); the sync says "verschwunden"; then all five entries
`gone`, nothing listed, the refusal sentence without the server, `tools_gone = all`, the
operator's page *Assistenten* and start page say it, five `item.gone` lines; reinstalled under
the same name: active again, `tools_gone` empty; rolled back, the instance removed; node
HEALTHY 8/8, 43/43.

**Not measured:** the chat's sentence in a browser (the chat's side is covered by its tests
against a fake gateway that answers `tools_gone`).

## 14. Stage 3a — prompts in app templates (2026-11-22)

**Built.**

- `mcp-gateway` 0.42.0 (`oaap.ai.mcp-gateway` 0.37): the setup door's `view` item may add
  `"prompts": {"server": <s>}` -- every prompt the server offers, approved as reading entries
  next to the view's tools. Another form, an unknown server or a server without prompts is
  refused and the view is not made half; a present view without those prompts is a conflict;
  remove works as for any view. An older gateway refuses the unknown field.
- Reference 0.1.344 (`oaap.core.tenant` 1.25): a need may say **`min_version`**; an instance of
  an older or unknown version does not meet it ("… läuft in Version 0.41.0; diese Vorlage braucht
  mindestens 0.42.0 -- erst die App aktualisieren"), nothing runs. The rules of an app's template
  allow `prompts` exactly as `{"server": "{source_key}"}` and require `min_version` 0.42.0 or newer
  on the MCP gateway's need -- so a template never meets a gateway that would refuse it halfway.
- `oaap-apps`: the ten templates of apps with prompts (fleetview, marketplace,
  mitarbeiterverwaltung, partnerverwaltung, projekt, raci, rollen-rechte, spezialisten, studio,
  wegweiser) name them, template version 1.1.0, each app one patch version up. `vorgaenge` has no
  prompts and stays as it is.

**Tests.** mcp-gateway `test_setup` 13 new (dry run, made with both prompts and reading tools only,
present on a second run, conflict on a view without prompts, three other forms, unknown server,
server without prompts -- nothing made, remove), all other gateway suites green. Reference
`test_app_templates` 10 new (a valid template with prompts; baits: another server, another form,
no or too low `min_version`, a `min_version` that is not x.y.z; the need judged with 0.41.0,
0.42.0, 0.100.0 and without a known version); the nine recipe and template suites in the Linux
runner green. All eleven templates pass the recipe check and the app-template rules;
`check-store` and `check-design` 24/24; the tests of the ten apps green.

**Measured on `oaap-test`** (0.1.344 staged after a backup; tenant `rzt`; `wegweiser` 0.6.1), 9/9:

| Asked | Answer |
|---|---|
| Install `wegweiser` 0.6.1 | template `wegweiser-links` 1.1.0 handed to the tenant |
| Preview with the tenant's gateway still 0.41.0 | refused: "… läuft in Version 0.41.0; diese Vorlage braucht mindestens 0.42.0 -- erst die App aktualisieren" |
| Gateway to 0.42.0, then the run | done; the view `wegweiser` holds `wegweiser_find` and `wegweiser_report` (prompt, read) next to three reading tools, all active, both prompts offered in the view |
| Preview afterwards | everything present, no conflict |
| Rollback | the assistant deleted; `wegweiser` removed again |

`rzt-werkzeuge` stays on 0.42.0.

**Not measured:** a prompt fetched with `/name` in the chat in the browser.

## 15. Stage 3b — writing tools, one tick each; correction to 3a (2026-11-22)

**Correction to 3a, found while reading the chat for 3b.** The chat offers a view's prompts as
`/name` only to an assistant with `commands: true` (`oaap.ai.assistants` §2), and §4.3 forbade
`commands` in an app's template. The measurement of §14 looked at the view only. Fixed: an
assistant of an app's template may carry `commands: true` exactly when its view names the app's
prompts; the ten templates carry it (template 1.2.0, each app one more patch version).

**Built (D13).**

- `mcp-gateway` 0.43.0 (`oaap.ai.mcp-gateway` 0.38): the setup door's `view` item with
  `tools: {"server", "effect": "read"}` may add `"writes": {"<tool>": true|false}` -- writing tools
  of the same server, approved as `write` when true, not at all when false. A reading or unknown
  tool, another value, or `writes` next to a tool list is refused; nothing is made half. The view's
  ceiling follows its entries.
- Reference 0.1.345 (`oaap.core.tenant` 1.26): in an app's template `writes` maps each tool to a
  parameter of kind `bool` that is not ticked beforehand and not `shape`; a literal `true`, a
  ticked default or one parameter for two tools drops the template; the gateway's need says
  `min_version: 0.43.0`; the chat's profile may say `max_effect: write` only when the view has
  `writes`. The wizard shows the ticks in step 2 in a box "Darf schreiben" (warning tone, tool
  name next to each label, a sentence that the person confirms every writing call in the chat).
- `vorgaenge` 0.19.0: template `vorgaenge-ueberblick` **2.0.0** (a new major, so an operator's
  release of `@1` does not cover writing) with `create_case` and `comment_case`, each its own
  tick; greeting and instructions say the assistant writes only with tools it is offered, says
  beforehand what it will write, and writes to the reporter only when asked.

**Tests.** mcp-gateway `test_setup` 10 new (false: reading only; the same view ticked later: a
conflict; true: `write`, ceiling write; again: present; baits reading tool, unknown tool, "ja",
a list, `writes` next to a tool list; remove), all gateway suites green. Reference
`test_app_templates` 14 new (the template's ticks; baits ticked default as bool and as text, a
literal true, `shape`, one parameter for two tools, a list, gateway 0.42.0, profile `execute`, a
profile that writes without `writes`, `commands` without prompts and not true; the wizard asks both
ticks unticked; an empty form sends false; the rendered item carries true/false); the nine recipe
and template suites in the Linux runner green; check-store and check-design 24/24; the tests of
`vorgaenge` and the ten apps green.

**Measured on `oaap-test`** (0.1.345 staged after a backup; tenant `rzt`; `rzt-werkzeuge` 0.43.0),
11/11:

| Asked | Answer |
|---|---|
| `wegweiser` 0.6.2, run of template 1.2.0 | the assistant has `commands: true`, the view offers both prompts |
| `vorgaenge` 0.19.0, only "Vorgänge melden" ticked | done; `create_case` as `write` in the view, `comment_case` absent, all else reads; view and the chat's profile up to `write` |
| nothing ticked | done; no writing tool, the view reads only (the profile's ceiling says `write`, the view caps it) |
| Rollback | all three assistants deleted; `vorgaenge` and `wegweiser` removed again |

`rzt-werkzeuge` stays on 0.43.0.

**Not measured:** the box "Darf schreiben" clicked in the browser; a writing call confirmed in the
chat and its usage row with `confirmed=yes`; `/name` in the chat.

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

**Stufe 2 gebaut und gemessen (22.11., §12):** Zehn weitere Apps bringen je eine Vorlage mit
(Partner, Mitarbeiter, Projekte, Zuständigkeiten, Rollen & Rechte, Flotte, Wegweiser, Studio,
Marktplatz, Spezialisten), nur lesend; mit Vorgänge elf. `check-design.py` macht eine Vorlage
zur Pflicht für jede App mit MCP-Tür, Ausnahmen mit Grund in der Prüfung selbst (sieben, darunter
Hilfe und Recherche, weil die Plattform deren Vorlagen schon mitbringt). Referenz 0.1.343: Der
Betreiber sperrt die Vorlagen einer App je Mandant (`oaap tenant templates <mandant> --block
<app>`), die Sperre schlägt auch eine Freigabe. Ein Lauf merkt sich seine App; die Seite
*Assistenten* sagt „Vorlage neuer“ nach einem Update und „Vorlage nicht mehr da“ nach dem
Entfernen. Auf oaap-test 16 von 17 (die rote Zeile war eine zu weit gefasste Prüfung der
Messung). Befund §6: Nach dem Entfernen einer App lässt das MCP-Gateway Quelle, Sicht und
Assistent stehen – das zu bemerken ist Arbeit im Gateway, offen. Nicht gemessen: Klick im
Browser, Gespräch im Chat.

**§6 geschlossen (22.11., §13):** Das Gateway kannte „Quelle verschwunden“ schon, merkte es aber
erst beim nächsten Abgleich (alle fünf Minuten) und bot die Werkzeuge danach trotzdem weiter
an. Neu (mcp-gateway 0.41.0): Einträge einer entfernten Quelle sind **`gone`** – sie bleiben
in der Sicht stehen, werden aber weder angeboten noch ausgeführt; ein Aufruf bekommt „… gibt es
nicht mehr: die App dahinter wurde entfernt“. Die Assistentenliste nennt `tools_gone`. Der Chat
0.21.0 beginnt dann kein Gespräch mehr und sagt in einem laufenden „Die Werkzeuge dieses
Assistenten gibt es nicht mehr“. Kommt die App wieder, ist alles wieder aktiv. Die Plattform
stößt den Abgleich bewusst nicht an (bis zu fünf Minuten Verzug). Auf oaap-test 12 von 12.
Nicht gemessen: der Satz des Chats im Browser.

**Stufe 3 entschieden (22.11., D12–D16):** Jörg: „E3: nein, aber vielleicht als Draft mit
Freigabe? Sonst wie empfohlen.“ Stufe 3 wird geteilt:
- **3a:** MCP-Prompts der eigenen App in der Sicht der Vorlage; ein Bedarf kann eine
  Mindestversion seiner App verlangen.
- **3b:** schreibende Werkzeuge der eigenen App. Im Wizard wird jedes einzeln angehakt, vorab
  keines. Im Chat bestätigt die Person jeden Aufruf wie heute. Die Vorlage bleibt frei.
- **3c:** Vorlagen über mehrere Apps liefert nur die Plattform. Dazu kommt eine Vorlage für den
  Zwilling, die ihre Ampel nicht selbst setzt.
- **3d (zu prüfen):** Eine App-Vorlage legt keinen Spezialisten an. Sie darf ihn höchstens als
  Entwurf vorschlagen, der erst nach Freigabe durch einen Menschen etwas tut.

Ergänzung zum Zwilling: Seine MCP-Tür bekommt später schreibende Funktionen (Typen und Instanzen
aus dem Chat anlegen und ändern, nur für Berechtigte). Eine breite REST-API zum Auswerten,
Modellieren, Anlegen und Ändern ist eine von Jörgs nächsten Anforderungen. Das gehört in ein
eigenes RFC zu `oaap.data.twin`. Die Zwillings-Vorlage aus 3c liest zunächst nur. Schreibende
Werkzeuge kommen später über den Weg von 3b hinzu.

**Stufe 3a gebaut und gemessen (22.11., §14):** Das MCP-Gateway 0.42.0 nimmt bei der Einrichtung
einer Sicht auch die Prompts eines Servers an, also fertige Fragen, die man im Chat mit `/name`
holt. Ein Bedarf im Rezept kann eine Mindestversion seiner App verlangen (Referenz 0.1.344).
Eine App-Vorlage darf die Prompts der eigenen App nennen, muss dann aber das Gateway ab 0.42.0
verlangen. So scheitert sie nie halb an einem älteren Gateway, sondern die Vorschau sagt vorher
„erst die App aktualisieren“. Die zehn Vorlagen der Apps mit Prompts nennen sie (Vorlage 1.1.0, je
App eine Patch-Version höher). Auf oaap-test 9 von 9: Mit Gateway 0.41.0 lehnt die Vorschau mit
diesem Satz ab; mit 0.42.0 entsteht die Sicht mit beiden Prompts von Wegweiser neben den lesenden
Werkzeugen. Danach wurde alles zurückgenommen. Nicht gemessen: ein Prompt per `/name` im Chat im
Browser.

**Stufe 3b gebaut und gemessen (22.11., §15):** Eine App-Vorlage darf schreibende Werkzeuge der
eigenen App nennen. Jedes bekommt im Assistenten ein eigenes Häkchen im Kasten „Darf schreiben“,
und keines ist vorab gesetzt. Was nicht angehakt ist, kommt gar nicht in die Sicht. MCP-Gateway
0.43.0, Referenz 0.1.345. Vorgänge 0.19.0 bringt die Vorlage 2.0.0 mit „Vorgänge melden“ und
„Kommentare schreiben“. Die neue Hauptversion sorgt dafür, dass eine Freigabe des Betreibers für
die nur lesende Version 1 das Schreiben nicht mit abdeckt. Auf oaap-test 11 von 11.
**Korrektur:** Die Bestätigung jedes schreibenden Aufrufs erzwingt der Chat; das Gateway hält sie
nur fest. In der ersten Fassung stand, das Gateway prüfe sie. **Nachtrag zu 3a:** Der Chat bietet
Prompts nur Assistenten mit `commands: true` an, und das hatte die Regel für App-Vorlagen
verboten. Behoben: Die zehn Vorlagen (1.2.0) tragen es. Nicht gemessen: Kasten und Bestätigung
im Browser, `/name` im Chat.

**Nachtrag 2026-11-22 -- 3c, die Vorlage für den Zwilling (D16):** gebaut mit RFC-0120 Stufe 5
(dort §15): `recipes/zwilling.json` liest über die Quelle `twin`; die drei schreibenden Werkzeuge
des Zwillings (`oaap.data.twin` 0.16 §2.28) kommen auf dem Weg von D13 -- je ein Häkchen, keins
vorab, im Chat jeder Aufruf bestätigt; keine eigene Ampel. Auf oaap-test gemessen. Vorlagen über
mehrere Apps (D15) und 3d bleiben offen.

*Deutsch:* Die Zwillings-Vorlage aus 3c ist gebaut und gemessen (siehe RFC-0120 §15). Offen
bleiben Vorlagen über mehrere Apps und 3d.
