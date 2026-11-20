# RFC-0109: Setup Recipes — Small Wizards for a Tenant That Already Exists

- **Status:** Draft (2026-11-20). D1–D9 open.
- **Date:** 2026-11-20
- **Authors:**
  - Jörg, 2026-11-20, in the tenant `pxx` on oaapx01: help, MCP gateway,
    AI gateway and chat were installed by hand, not by a build, so their
    settings were missing. "Perspektivisch sollten wir solche Sachen im
    Aufbau des Tenants anbieten: kleine Wizards, womit ich bestimmte Dinge
    auch im Nachgang manuell machen kann."
  - Claude: did the missing settings for `pxx` the same day by calling the
    setup doors of RFC-0104 by hand (§1), and wrote this design from what
    that took.
- **Depends on:**
  - RFC-0055: tenant profiles and builds (check, do, undo; manual steps).
  - RFC-0079: profile versions.
  - RFC-0104: `destination.ensure`, the setup door, `app.setup`, the
    profile `ki-arbeitsplatz`.
  - RFC-0097: assistants in the MCP gateway.
- **Changes:** nothing in an existing profile. A build keeps refusing an
  existing tenant (§1.2); a recipe is a new, smaller thing beside it.

## Summary

A profile builds a **new** tenant. It cannot help a tenant that already
exists: its first step, `tenant.create`, stops with a conflict. And only a
server_admin may run it.

This RFC adds **setup recipes** (German in the portal: *Einrichten*). A
recipe is a short list of the same steps a profile uses, without
`tenant.create`, run against an existing tenant:

- it names the **apps** it needs; the person picks the **instances**
  (one per app, pre-selected when the tenant has just one);
- it may ask for **values that live in an app**, such as a model name of
  the AI gateway, and offers what the app has (§4);
- it always shows a **preview first** (every step's dry run), then does
  it; nothing a human made is overwritten — the setup doors already
  promise that;
- a **tenant_admin** may run it in their own tenant, as long as each step
  stays inside the tenant (§5);
- it can be **undone** like a build.

The first recipe is the one `pxx` needed: **"Hilfe-Assistent im Chat"**.

## 1. Facts (2026-11-20)

### 1.1 What `pxx` needed

`pxx` had `pxx-help` (help 0.7.0), `pxx-tools` (mcp-gateway 0.28.0),
`pxx-models` (ai-gateway 0.11.1) and `pxx-chat` (chat 0.16.0). Jörg had
already set up the AI gateway himself: supplier `openrouter` with the light
**red**, and model names such as `chat-default`. There was **no** model
name `standard`, which the profile `ki-arbeitsplatz` assumes.

What was missing, and what was done (as root, through
`appctl.setup_call`, dry run first):

| App | Missing | Done |
|---|---|---|
| help | destination `docs-origin`, documentation | destination added and bound (CLI), `fetch docs` (119 files) |
| ai-gateway | a client for the chat | `client pxx-chat`, aliases `[chat-default]`, ceiling red, tenant pxx |
| mcp-gateway | light of the help server, view, profile, assistant | `server_light pxx-help green`, view `hilfe`, profile `pxx-chat` (ceiling red), assistant `hilfe` (model `chat-default`, visibility tenant) |

These are exactly the items of the profile's steps `docs-origin`,
`hilfe-holen`, `modellname` and `werkzeuge-einrichten`, with two values
changed by hand: the model name and the ceiling. Without a person who
knows the setup doors, nobody could have done it.

### 1.2 Why a profile cannot do it

- `tenant.create` on an existing tenant: `CONFLICT` — "ein Mandant besteht
  schon und stammt nicht aus diesem Aufbau; er wird nicht angefasst".
  A build stops at a conflict.
- `tenant_build_start` refuses everyone but server_admin.
- A profile names instances by the names it installs (`{name_help}`). An
  existing tenant's instances have whatever names they were given.
- A profile's values are fixed or typed by the builder. It cannot ask the
  AI gateway which model names exist.

### 1.3 What already fits

- The step drivers (`_BuildDrivers`) check, do and undo each step type on
  the node, and find an instance by its local name in the tenant
  (`_instance_key`).
- The setup doors are idempotent: `present`, `made`, `conflict`; a dry run
  answers `would_make`. They never overwrite a human's change.
- The portal already shows a build as a list of steps with their state.

## 2. A recipe

A recipe is a JSON document like a profile, with its own kind:

```json
{
  "recipe": "oaap.tenant-recipe/1",
  "id": "hilfe-assistent",
  "version": "1.0.0",
  "title": "Hilfe-Assistent im Chat",
  "description": "Der Chat bekommt einen Assistenten, der in der Hilfe sucht.",
  "needs": {
    "help":  {"app": "help",        "label": "Hilfe"},
    "tools": {"app": "mcp-gateway", "label": "Werkzeuge"},
    "models":{"app": "ai-gateway",  "label": "Modelle"},
    "chat":  {"app": "chat",        "label": "Chat"}
  },
  "params": {
    "model": {"kind": "setup_item", "instance": "models", "item_kind": "alias",
              "default": "standard", "label": "Modellname für den Assistenten"},
    "ceiling": {"kind": "light", "default": "from:model",
                "label": "Höchste Ampel für den Chat"}
  },
  "steps": [
    {"id": "docs-origin", "type": "destination.ensure", "name": "docs-origin",
     "instance": "{help}", "target": "https://codeload.github.com/MDJoerg/oaap-docs",
     "auth": "none"},
    {"id": "hilfe-holen", "type": "app.setup", "name": "{help}",
     "items": [{"kind": "fetch", "id": "docs"}]},
    {"id": "freigabe", "type": "app.setup", "name": "{models}",
     "items": [{"kind": "client", "id": "{tenant}-{chat}", "aliases": ["{model}"],
                "ceiling": "{ceiling}", "personal_data": false, "tenant": "{tenant}"}]},
    {"id": "werkzeuge", "type": "app.setup", "name": "{tools}",
     "items": [{"kind": "refresh", "id": "{tenant}-{help}"},
               {"kind": "server_light", "id": "{tenant}-{help}", "light": "green"},
               {"kind": "view", "id": "hilfe", "accesses": ["platform"],
                "tools": {"server": "{tenant}-{help}", "effect": "read"}},
               {"kind": "profile", "id": "{tenant}-{chat}", "group": "@{tenant}-{chat}",
                "views": ["hilfe"], "ceiling": "{ceiling}"},
               {"kind": "assistant", "id": "hilfe", "title": "Hilfe", "view": "hilfe",
                "gateway": "{tenant}-{tools}", "model": "{model}",
                "visibility": "tenant"}]}
  ]
}
```

Rules:

- `needs` maps a placeholder to an app. Each becomes a parameter whose
  value is the **local name of an instance of that app in this tenant**.
  The placeholder `{tenant}` is the tenant's label and is always there.
- The **step vocabulary is the profile's**, minus everything that creates
  or shapes the tenant: no `tenant.create`, `tenant.face`, `tenant.policy`,
  `address.*`, `idp.*`. `app.install` is allowed (§3).
- The checks of RFC-0055 and RFC-0079 apply unchanged: known keys only,
  no secrets (`SECRET_WORDS`), versions, history per checksum.
- A recipe lives where the node's profiles live, in its own folder
  (`recipes/`); the portal page for profiles gets a second list.

## 3. A missing app

When the tenant has no instance of a needed app, the recipe either
stops before the first step ("dieser Mandant hat keine App *help*") or —
when the recipe says `"install": true` for that need — offers an
`app.install` from the catalogue with a proposed name. The person sees it
in the preview like every other step.

## 4. Values that live in an app

The model name `standard` was the wrong guess for `pxx`. The person
should **choose from what the AI gateway has**.

- New parameter kind `setup_item`: `instance` (a need), `item_kind`.
  The portal fills the choice from the instance's setup door.
- The setup door gets one read: `GET ?kind=<kind>` →
  `{"v": 1, "items": [{"id": "...", "title": "...", "light": "red"}]}` —
  ids, a short title, a light where the app knows one; **never a secret
  or a credential**. `GET` without `kind` stays as today (the list of
  kinds).
- `default` is used when it exists in the list; otherwise nothing is
  pre-selected and the person must choose.
- Parameter kind `light` with `"from:<param>"`: pre-selects the light of
  the chosen item (here: the supplier light behind the model name), so the
  ceiling matches what the model needs. The person can choose a better
  light; a worse one than the item needs is refused in the preview,
  because the chat could never use the model.

This read is the only app change: help, ai-gateway and mcp-gateway each
answer it for the kinds they offer.

## 5. Who may run a recipe

- **server_admin**: any recipe, any tenant.
- **tenant_admin**: any recipe, **own tenant only**, when every step passes
  the tenant-scope check:
  - `app.setup` on an instance of this tenant — the platform calls the
    door, the person never sees the setup key;
  - `app.config` with a non-secret key the manifest declares;
  - `destination.ensure` with `auth: none` (D5);
  - `app.install` from a catalogue this tenant may see.
  A step outside that scope makes the whole recipe refuse **before** the
  preview, with the step named.
- Every run is a line in the tenant's log with the person, the recipe,
  its version and checksum, and what was made.

## 6. Preview, run, undo

1. The person picks recipe, instances and values.
2. **Preview:** every step's check and the setup door's dry run, shown as
   a list: *vorhanden*, *wird angelegt*, *Konflikt* (with the app's
   note). A conflict stops the recipe; nothing has happened yet.
3. **Run:** the build engine drives the steps; a `manual` step waits as in
   a build.
4. **Undo:** removes what this run made (`made` items), in reverse, by the
   rules of RFC-0104 §3.1 — an item a human changed since stays.

A second run of the same recipe with the same values is a preview with
only *vorhanden* — that is how a person checks that everything is still in
place.

## 7. Where it shows

- Tenant context, page **Einrichten**: the recipes whose needs this tenant
  meets, each with "Was fehlt noch?" (its preview, read only) and
  "Einrichten".
- On an instance's page: "Einrichten…" lists the recipes that need this
  app.
- After a build, the build page links to *Einrichten* for later changes.

## 8. Security requirements

- S1: The setup key never leaves the platform; the person drives the
  door only through the platform, as in a build.
- S2: Instances are resolved **in the tenant of the run**; a placeholder
  can never name another tenant's instance (checked by key, not by name).
- S3: No secret in a recipe, a parameter, a preview or a log line. A
  credential is always a `manual` step in the app itself.
- S4: The setup-item read returns ids and titles only; tested with a
  supplier whose credential is set.
- S5: A tenant_admin cannot widen a recipe: the scope check runs on the
  filled steps, after the placeholders are replaced.

## 9. Decisions

- **D1 — A new kind beside profiles, not a flag on profiles.**
  Recommended: new kind `oaap.tenant-recipe/1`, same engine and step
  drivers. Alternative: profiles with `"existing_tenant": true`. A recipe
  is small and runs many times; a profile is large and runs once.
- **D2 — Instances as `needs`, chosen by the person.** Recommended:
  pre-selected when the tenant has exactly one instance of the app.
- **D3 — Missing app.** Recommended: stop by default; install only when
  the recipe says `"install": true` for that need.
- **D4 — Values from the app (`setup_item`) and the setup-door read
  `GET ?kind=`.** Recommended: yes, in stage 2; stage 1 takes typed values.
- **D5 — tenant_admin may run recipes.** Recommended: yes, own tenant,
  with the scope check of §5. Open fact to check in stage 1: whether a
  tenant_admin may create a destination today; if not,
  `destination.ensure` stays server_admin until a decision.
- **D6 — Preview is mandatory.** Recommended: yes; there is no "run"
  without a preview of the same values in the same minute.
- **D7 — Undo.** Recommended: yes, like a build, per run.
- **D8 — First recipes.** Recommended: `hilfe-assistent` (§2),
  `chat-am-ki-gateway` (only the client), `hilfe-doku` (only
  destination + fetch). They live in `oaap-docs/szenarien/rezepte/`.
- **D9 — Profiles use recipes.** Recommended: later (stage 3): a profile
  step `recipe.apply` so `ki-arbeitsplatz` is made of the same pieces a
  tenant_admin can repeat.

## 10. Stages and tests

- **Stage 1 — engine and CLI.** Kind, checks, `needs`, scope check;
  `oaap tenant recipe <label> <id> [--set k=v] [--dry-run]`; recipe
  `hilfe-assistent`. Test on oaap-test: a tenant with the four apps
  installed by hand → preview lists *wird angelegt*, run, second preview
  lists only *vorhanden*, undo, a human-changed item survives undo. Then
  on `pxx` (Jörg's word): preview must say *vorhanden* everywhere.
- **Stage 2 — portal and app read.** Page *Einrichten*, instance link,
  `setup_item` and `light` parameters, `GET ?kind=` in help, ai-gateway,
  mcp-gateway; tenant_admin runs. Test: a tenant_admin of tenant A cannot
  name an instance of tenant B (S2), cannot run a recipe with an
  out-of-scope step (S5); the model list shows no credential (S4).
- **Stage 3 — more recipes, `recipe.apply` in profiles.**

## 11. Out of scope

- Recipes that change the tenant itself (name, face, address, realm).
- Recipes across tenants or nodes.
- A recipe editor in the portal; recipes are files, like profiles.

## Deutsche Zusammenfassung

**Anlass:** In pxx auf oaapx01 standen Hilfe, MCP-Gateway, KI-Gateway und
Chat, aber ohne Aufbau — also ohne die Einstellungen, die das Profil
`ki-arbeitsplatz` sonst setzt. Ich habe sie heute von Hand über die
Einrichtungstüren nachgetragen. Das ging nur, weil ich weiß, welche Türen
es gibt und was das Profil hineinschreibt. Dabei passte der Modellname
`standard` nicht; du hattest `chat-default` angelegt.

**Warum ein Profil nicht hilft:** Ein Profil baut einen *neuen* Mandanten.
Auf einem bestehenden hält es beim ersten Schritt an („Mandant besteht
schon“), und nur server_admin darf es starten.

**Vorschlag: Rezepte („Einrichten“).** Ein Rezept ist eine kurze Liste
derselben Schritte wie im Profil, ohne „Mandant anlegen“, für einen
bestehenden Mandanten:

- Es nennt die **Apps**, die es braucht. Du wählst die **Instanzen**; hat
  der Mandant nur eine, ist sie vorgewählt.
- Es fragt **Werte aus der App** ab, z. B. die Modellnamen des
  KI-Gateways, statt `standard` zu raten. Die Ampel wird passend
  vorgeschlagen.
- Es zeigt **immer zuerst eine Vorschau**: vorhanden, wird angelegt,
  Konflikt. Bei einem Konflikt passiert nichts. Was ein Mensch angelegt
  hat, wird nie überschrieben.
- Ein **tenant_admin** darf es im eigenen Mandanten ausführen, solange
  jeder Schritt im Mandanten bleibt.
- Es lässt sich **rückgängig machen** wie ein Aufbau.
- Ein zweiter Lauf zeigt nur „vorhanden“ — so prüft man, ob noch alles
  steht.

Erstes Rezept: **„Hilfe-Assistent im Chat“**, genau das, was pxx gebraucht
hat. Später setzen sich Profile aus Rezepten zusammen.

**Offene Entscheidungen D1–D9**, je mit Empfehlung:

- D1: Rezept als eigene Art neben Profilen.
- D2: Instanzen wählbar, eine vorgewählt.
- D3: Fehlende App → Halt, Installieren nur, wenn das Rezept es anbietet.
- D4: Werte aus der App (neue Lesetür `GET ?kind=` an den
  Einrichtungstüren), in Stufe 2.
- D5: tenant_admin darf, mit Prüfung je Schritt. Offen: ob ein
  tenant_admin heute Destinations anlegen darf.
- D6: Vorschau ist Pflicht.
- D7: Rückgängig ja.
- D8: Drei erste Rezepte in `oaap-docs/szenarien/rezepte/`.
- D9: Profile aus Rezepten erst in Stufe 3.

**Stufen:**

1. Maschine und CLI, gemessen auf oaap-test, danach Vorschau auf pxx
   (muss überall „vorhanden“ sagen).
2. Portalseite „Einrichten“ und Lesetür in den drei Apps.
3. Weitere Rezepte, Profile nutzen Rezepte.
