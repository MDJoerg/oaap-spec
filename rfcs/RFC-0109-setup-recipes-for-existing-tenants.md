# RFC-0109: Setup Recipes — Small Wizards for a Tenant That Already Exists

- **Status:** **Accepted (2026-11-20)** — after a first discussion the
  same day (D4 stage 2, D5 changed: the operator releases, §5; D8
  extended: SAP SSO, §12; new D10 requests as cases, §13; new D11 where it
  shows, §7), Jörg: "Ja, wie empfohlen" for D1–D3, D6, D7, D9–D11.
  **Stage 1 built the same day** (reference 0.1.323, `oaap.core.tenant`
  1.12, recipe `hilfe-assistent` 1.0.0), measured on oaap-test and as a
  preview on `pxx`; see §14. **D12 decided and built** (Jörg: "Gateway
  holt zurück"): mcp-gateway 0.29.0, `oaap.ai.mcp-gateway` 0.27.0; §15.
  **Stage 2 built** (Jörg: "Ja, Stufe 2 bauen"): reference 0.1.324,
  help 0.8.0, ai-gateway 0.12.0, mcp-gateway 0.30.0, recipe
  `hilfe-assistent` 1.1.0; measured on oaap-test with a `tenant_admin`
  through the real portal page; §16.
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
  `address.*`, `idp.provision`. `app.install` is allowed (§3). Steps that
  work *inside* a realm the tenant already has (such as an attribute or a
  client scope, §12) are new step types of stage 3.
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

Jörg, 2026-11-20: "das sollte der server_admin/Betreiber erlauben.
Danach soll der tenant_admin sowas selbst hinbekommen."

- **server_admin**: any recipe, any tenant.
- **The operator releases** a recipe for tenants, the way a catalogue
  entry is released ("Sichtbar für: alle | pxx, bec"). A recipe nobody
  released is visible only to the server_admin. A release names the
  recipe's id and a version range; a new major version needs a new
  release.
- **tenant_admin**: a **released** recipe, **own tenant only**, without
  asking anyone, when every step passes the tenant-scope check:
  - `app.setup` on an instance of this tenant — the platform calls the
    door, the person never sees the setup key;
  - `app.config` with a non-secret key the manifest declares;
  - `destination.ensure` with `auth: none` (D5);
  - `app.install` from a catalogue this tenant may see.
  A step outside that scope makes the whole recipe refuse **before** the
  preview, with the step named.
- A tenant_admin who needs a recipe that is not released, or a step
  outside the scope, **asks the operator** (§13).
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

## 7. Where it shows (D11)

Jörg asked: under "Aufbau" in the tenant view? Today "Aufbau" (`/aufbau`)
is a **node** page in the side-bar group "Betrieb", shown only to whoever
may build (`can_build`, server_admin). A tenant_admin never sees it, and
it is about making tenants, not about living in one. So:

- **Tenant view, new side-bar entry "Einrichten"** (`/einrichten`), group
  "Betrieb", right after "Instanzen", shown to tenant_admin and
  server_admin in a tenant's context. It lists:
  - the recipes released for this tenant whose needs it meets, each with
    "Was fehlt noch?" (its preview, read only) and "Einrichten";
  - the runs of this tenant (state, who, when, "Rückgängig");
  - the open requests to the operator and their state (§13), with a
    button "Beim Betreiber anfragen".
- **Node view, page "Aufbau"** (server_admin): a second list beside the
  profiles — the recipes of the node, their versions, **"Freigeben für"**
  per recipe, and the incoming requests of all tenants.
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

## 9. Decisions (Jörg, 2026-11-20: D4, D5, D8 as discussed, all others as recommended)

- **D1 — A new kind beside profiles, not a flag on profiles.**
  Recommended: new kind `oaap.tenant-recipe/1`, same engine and step
  drivers. Alternative: profiles with `"existing_tenant": true`. A recipe
  is small and runs many times; a profile is large and runs once.
- **D2 — Instances as `needs`, chosen by the person.** Recommended:
  pre-selected when the tenant has exactly one instance of the app.
- **D3 — Missing app.** Recommended: stop by default; install only when
  the recipe says `"install": true` for that need.
- **D4 — Values from the app (`setup_item`) and the setup-door read
  `GET ?kind=`.** **Decided (Jörg, 2026-11-20): stage 2**; stage 1 takes
  typed values.
- **D5 — tenant_admin may run recipes.** **Changed by Jörg
  (2026-11-20):** the operator releases a recipe for tenants; after that
  the tenant_admin runs it alone, own tenant, with the scope check of §5.
  Open fact for stage 1: a tenant_admin may already make a destination
  with principal propagation in the portal (L22, reference 0.1.311); to
  check whether the same holds for `auth: none` and from the CLI path a
  recipe uses.
- **D6 — Preview is mandatory.** Recommended: yes; there is no "run"
  without a preview of the same values in the same minute.
- **D7 — Undo.** Recommended: yes, like a build, per run.
- **D8 — First recipes.** Recommended: `hilfe-assistent` (§2),
  `chat-am-ki-gateway` (only the client), `hilfe-doku` (only
  destination + fetch). They live in `oaap-docs/szenarien/rezepte/`.
  **Jörg, 2026-11-20: also "SAP SSO einrichten"** — §12, stage 3.
- **D9 — Profiles use recipes.** Recommended: later (stage 3): a profile
  step `recipe.apply` so `ki-arbeitsplatz` is made of the same pieces a
  tenant_admin can repeat.
- **D10 — Requests to the operator as cases (§13).** Recommended: the
  platform writes the request as a case into a cases instance the
  operator names in the default tenant; the tenant needs no connection of
  its own; without such an instance, a message to the node owner.
- **D11 — Where it shows (§7).** Recommended: "Einrichten" in the tenant
  view for tenant_admin, recipes and releases on "Aufbau" for the
  operator — not recipes under "Aufbau".

## 10. Stages and tests

- **Stage 1 — engine and CLI.** Kind, checks, `needs`, scope check;
  `oaap tenant recipe <label> <id> [--set k=v] [--dry-run]`; recipe
  `hilfe-assistent`. Test on oaap-test: a tenant with the four apps
  installed by hand → preview lists *wird angelegt*, run, second preview
  lists only *vorhanden*, undo, a human-changed item survives undo. Then
  on `pxx` (Jörg's word): preview must say *vorhanden* everywhere.
- **Stage 2 — portal, releases and app read.** Page *Einrichten*,
  recipes and "Freigeben für" on *Aufbau*, instance link, `setup_item`
  and `light` parameters, `GET ?kind=` in help, ai-gateway, mcp-gateway;
  tenant_admin runs released recipes. Test: a tenant_admin of tenant A
  cannot name an instance of tenant B (S2), cannot run an unreleased
  recipe or one with an out-of-scope step (S5); the model list shows no
  credential (S4).
- **Stage 3 — requests and SAP SSO.** Requests to the operator (§13);
  recipe `sap-sso` with its new step types (§12); `recipe.apply` in
  profiles.

## 11. Out of scope

- Recipes that change the tenant itself (name, face, address, realm).
- Recipes across tenants or nodes.
- A recipe editor in the portal; recipes are files, like profiles.

## 12. Recipe "SAP SSO einrichten" (D8, stage 3)

The chain the tenant `bec` runs today (person in the chat → MCP gateway
→ SAP system as that person, RFC-0065/0066, measured with the chain test
of RFC-0096) was made by hand in about fifteen steps, half of them in the
SAP system. A recipe cannot do the SAP half, but it can **lead through
it** and check each link:

| # | Step | Kind |
|---|---|---|
| 1 | Realm of the tenant: attribute `sap_user` (editable by admins only), client scope `sap` on the platform client | new step type `idp.claim` (inside an existing realm) |
| 2 | Destination with principal propagation to the SAP system: target, user claim, name check `sap` | `destination.ensure` with `auth: principal_propagation` — today excluded from profiles because the server certificate must be pinned |
| 3 | Pin the SAP server certificate: the platform reads the fingerprint, a human compares and confirms | `manual`, done_when `destination.pinned` (new read) |
| 4 | SAP side: import the platform's issuing certificate (STRUST), rule-based mapping (CERTRULE, RZ10 `login/certificate_mapping_rulebased=1`), check user `OAAP_CHECK` without roles | `manual` steps with the text of the SAP-Basis checklist (oaap-docs, L23), done_when `destination.check` (new read: the chain test passes) |
| 5 | Bind the destination to the MCP gateway with `--propagate`; server, view, profile | `destination.bind` (new) and `app.setup` |
| 6 | Assistant in the chat for the SAP view | `app.setup` (assistant) |

Parameters: the SAP system's address, its SAP client, the view's name.
Values that are secrets (none here; the platform's issuing key never
leaves the node) stay out, as everywhere.

Because steps 1–3 reach outside the apps, this recipe is
**server_admin-only until released** like every other, and its release
is the moment the operator says "this tenant may connect its own SAP
system".

## 13. Requests to the operator (D10, stage 3)

Jörg, 2026-11-20: in a multi-tenant landscape not every tenant_admin is
known; a tenant_admin should be able to **request services from the
operator** — "eine Art Ticket-Prozess" — through the node's cases,
perhaps in the default tenant, or connected from the tenant.

Design:

- The operator names **one cases instance** (app `vorgaenge`) in the
  default tenant as the node's **request inbox** (node setting, portal
  page "Aufbau").
- On *Einrichten*, a tenant_admin presses **"Beim Betreiber anfragen"**:
  for an unreleased recipe, a refused step, or free text ("wir brauchen
  SAP SSO für unser System X").
- **The platform** writes the case, not the tenant: through the cases
  app's own door, as the platform, with the tenant, the person's display
  name, the recipe, the values and the preview attached. The tenant needs
  no destination, no key and no account in the default tenant; the
  request carries nothing the tenant did not type or the preview did not
  show.
- The operator works the case as any other: asks back in the case,
  **releases** the recipe for that tenant (§5) or runs it himself, and
  closes it. The release links to the case.
- The tenant_admin sees the state and the operator's replies **on
  *Einrichten*** (the platform reads them back), not in the default
  tenant.
- Without a request inbox: the request goes as a message to the node
  owner (RFC-0080 lists), and the state on *Einrichten* says so.

Alternative (not recommended now): the tenant's own cases instance
connected to the operator's. That needs a connection between two
tenants' instances, which the platform does not have today; the platform
as the writer keeps the tenant boundary simple.

Open fact for stage 3: whether `vorgaenge` can take a case from the
platform (door, identity of the writer) or needs a small addition.

## Deutsche Zusammenfassung

**Angenommen am 20.11.** („Ja, wie empfohlen“ nach der ersten
Besprechung). Gebaut ist noch nichts.

**Stand nach der ersten Besprechung (20.11.):**

- D4: Werte aus der App kommen in Stufe 2 (entschieden).
- D5, geändert: Der **Betreiber gibt ein Rezept frei** („Freigeben für:
  alle | pxx, bec“). Danach führt der tenant_admin es selbst aus.
- D8: Dazu kommt das Rezept **„SAP SSO einrichten“** (§12, Stufe 3). Es
  führt durch die SAP-Seite (STRUST, CERTRULE, RZ10, OAAP_CHECK) und
  prüft jedes Glied mit dem Kettentest.
- Neu D10: **Anfragen an den Betreiber als Vorgang** (§13). Die
  Plattform schreibt die Anfrage in eine Vorgangs-Instanz des
  Betreibers im Mandanten default. Der Mandant braucht dafür keine
  eigene Verbindung. Antworten und Stand sieht der tenant_admin unter
  „Einrichten“.
- Neu D11: **Wo im Portal** (§7). „Aufbau“ ist eine Knotenseite für den
  Betreiber, die ein tenant_admin nicht sieht. Deshalb bekommt die
  Mandantensicht einen eigenen Eintrag „Einrichten“, unter „Betrieb“
  nach „Instanzen“. Unter „Aufbau“ verwaltet der Betreiber die Rezepte,
  Freigaben und eingehenden Anfragen.

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

**Entscheidungen D1–D9 im ersten Entwurf**, je mit Empfehlung (Stand
nach der Besprechung: siehe oben):

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

## 14. Stage 1, built (2026-11-20, reference 0.1.323)

**What is there:**

- `platform/services/tenant_recipe.py` (pure): judging a recipe
  (`recipe_problems`), its profile shape for the engine (`as_profile`:
  needs and `tenant` become parameters, `install: true` becomes an
  `app.install` in front), choosing the instances (`resolve_needs`,
  S2), the preview (`preview`, `preview_blockers`), the tenant_admin
  scope (`tenant_admin_scope_problems`, on the filled steps, S5 — used
  from stage 2).
- `tenant_build`: run ids `r-…` beside `b-…`, log events
  `tenant.recipe.*` for a run.
- `appctl`: recipes in `/var/lib/oaap/recipes/`, runs in
  `data/tenant-recipe-runs/`, history per digest as for profiles;
  `oaap tenant recipe list | preview <id> --tenant <label> [--param
  need=<instance>] [--param key=value] | run … | runs | show <run> |
  continue | confirm | rollback [--yes]`. Root / server_admin only.
- Need values: `{n}` = the instance's name in the tenant, `{n_key}` = its
  key on the node (a key is not always `<label>-<name>`, the default
  tenant has none), `{tenant}` = the label.
- Recipe `oaap-docs/szenarien/rezepte/hilfe-assistent.json` 1.0.0,
  parameters `model` (default `standard`) and `ceiling` (default
  `yellow`).
- `oaap.core.tenant` 1.12, §2.13, conformance test 32.
- Tests: `test/test_tenant_recipe.py` 52/52; the build tests unchanged
  green (test_tenant_build 86, test_profile_versions 32,
  test_tenant_build_destination 30, _config 12, _apps 50,
  test_build_rollback_accounts 33, test_tenant_build_doors 41,
  test_tenant_build_page 71). No full suite.

**Measured on oaap-test** (0.1.323 staged): tenant `rzt` with help,
mcp-gateway, ai-gateway and chat installed by hand, master keys by hand,
supplier `openrouter` (red) and model name `chat-default` by hand — the
state of `pxx` this morning.

| Check | Result |
|---|---|
| preview | four steps "wird angelegt", the same notes as the hand-made setup of `pxx` |
| run | done; destination added and bound, client `rzt-chat`, light, view, profile, assistant made |
| second preview | all four "vorhanden" |
| second run | done, nothing made |
| rollback of the first run | exactly its seven items, in reverse; log `tenant.recipe.rollback` per item |
| another tenant's instance (`--param chat=vuebung-chat`) | refused, names the tenant's own |
| unknown tenant / tenant without the apps / two chats | refused, each with its sentence |
| run after rollback | refused by the preview, no run recorded (finding B) |

**Findings:**

- **A — two runs in one second shared an id** (found by the test): the
  second state overwrote the first, and with it the first run's undo.
  Fixed: a taken id gets `-2`, `-3`.
- **B — undo, then run again, conflicts.** The MCP gateway keeps a
  revoked access profile and a removed assistant under their id for ever
  (known since RFC-0104 stage 2); the preview says so and the run does
  not start. So "Rückgängig" is final for those items today. A fix
  belongs to the app: its setup door could bring back an entry that the
  door itself removed (it records its items in `setup_items`). **Open
  decision for Jörg (D12):** build that in mcp-gateway, or keep undo
  final and say so on the page.
- **C — the operator's release already has a home.** The tenant record
  carries `tenant_admin_may` (`oaap.core.tenant` 1.7, `oaap tenant allow
  <label> destinations`): rights a server_admin hands to one tenant's
  tenant_admin. Stage 2 can record a recipe's release there
  (`recipe:<id>`) instead of a new store. It also answers the open fact
  of D5: a tenant_admin makes destinations only where the operator
  allowed `destinations`.
- **D — the help fetched on its own.** After the destination was bound,
  the help instance restarted and fetched the documentation itself; the
  step `hilfe-holen` found it present. Undo leaves the documentation
  there (the run did not make it).

**Measured on oaapx01, tenant `pxx`** (2026-11-20, after push and
`oaap update` 0.1.322 → 0.1.323, Jörg: "Ja, pushen und messen"; recipe
copied to `/var/lib/oaap/recipes/`): the preview with `model=chat-default`,
`ceiling=red` picked help, tools, models, chat on its own and said
"vorhanden" for all four steps — the hand-made setup of the morning is
exactly what the recipe describes. No run was started.

**Not measured:** an item a human changed surviving undo on the node
(the app's rule, tested with RFC-0104).

**Left on oaap-test:** tenant `rzt` with its four instances and two runs
(one rolled back), the recipe in `/var/lib/oaap/recipes/`, the tree
`~/ref-0.1.323`.

## Deutsche Zusammenfassung (Stufe 1 gebaut)

**Gebaut (Referenz 0.1.323):** Rezepte laufen über die Kommandozeile
(`oaap tenant recipe preview | run | rollback …`), nur für den Betreiber.
Sie nutzen dieselbe Aufbau-Maschine und dieselben Schritte wie Profile.
Das erste Rezept ist „Hilfe-Assistent im Chat“; es liegt in oaap-docs.

**Gemessen auf oaap-test** mit einem Mandanten im Zustand von pxx heute
Morgen:

- Vorschau: vier Schritte „wird angelegt“.
- Lauf: fertig.
- Zweite Vorschau: alles „vorhanden“; ein zweiter Lauf legt nichts an.
- Rückgängig nimmt genau die sieben Dinge des Laufs zurück.
- Fremde Instanzen, fehlende Apps und mehrere Chats werden abgelehnt.

**Befunde:**

- A: Zwei Läufe in derselben Sekunde hatten dieselbe Kennung. Behoben.
- B: Nach dem Rückgängigmachen geht ein neuer Lauf nicht, weil das
  MCP-Gateway widerrufene Profile und Assistenten für immer unter ihrer
  Kennung behält. Die Vorschau fängt das ab. **Entscheidung D12:** Das
  Gateway reaktiviert, was seine Einrichtungstür selbst entfernt hat, oder
  „Rückgängig“ bleibt für diese Teile endgültig.
- C: Für die Freigabe durch den Betreiber gibt es schon einen Ort:
  `tenant_admin_may` am Mandanten (wie `oaap tenant allow … destinations`).
  Stufe 2 kann Rezept-Freigaben dort eintragen.
- D: Die Hilfe holt ihre Doku nach dem Zuordnen selbst.

**Auf pxx gemessen** (nach Push und Update von oaapx01 auf 0.1.323): Die
Vorschau wählt die vier Instanzen selbst und zeigt überall „vorhanden“.
Die Handarbeit vom Morgen entspricht also genau dem Rezept. Gestartet
wurde kein Lauf.

## 15. D12, built (2026-11-20, mcp-gateway 0.29.0)

Jörg, 2026-11-20: "Gateway holt zurück".

- The setup door of the MCP gateway brings back an access profile that is
  revoked or an assistant that is deleted **when it removed them itself**.
  The proof is the gateway's audit trail, not the door's memory: the last
  `key.revoke` of that label, or the assistant's last change, was by
  `setup:…`. That also covers what mcp-gateway 0.28.0 removed before this
  version existed.
- The profile is valid again with the wished groups, views, ceiling and
  effect class (`profile.revive`); the assistant gets a new active revision,
  the earlier ones stay (`assistant.revive`). A dry run says `would_make`
  with "Holt zurück, was die Einrichtung selbst entfernt hat."
- What a human revoked or deleted stays a `conflict`, now with "nicht von
  der Einrichtung" in its note; a **key** never comes back.
- `oaap.ai.mcp-gateway` 0.27.0, §3.9e. Tests: `test_setup.py` 61/61 (new:
  dry, bring back, present afterwards, remove and bring back again, a
  human's revoke and delete stay, a key never), `test_gateway` 548,
  `test_sources` 30, `test_templates` 54, `test_signin` 28,
  `check-store.py` and `check-shared.py` clean.
- **Measured on oaap-test**, tenant `rzt` (where the run after the undo had
  stopped, finding B): `rzt-werkzeuge` updated from the local tree to 0.29.0;
  the preview says "wird angelegt" for all four steps, profile and assistant
  with "Holt zurück"; the run is done; the next preview says "vorhanden"
  everywhere. The audit trail shows `key.revoke` by `setup:oaap-admin` (by
  0.28.0 in the morning), then `profile.revive` and `assistant.revive`.
- The AI gateway needed nothing: its client `rzt-chat`, removed by the same
  undo, was made again without a conflict.

**Not done:** push, the catalogue's 0.29.0 on other nodes (pxx-tools stays
0.28.0 until Jörg says so); `rzt-werkzeuge` on oaap-test now has the local
folder `~/mcpgw-0.29.0` as its source.

## Deutsche Zusammenfassung (D12 gebaut)

Entschieden: **Das Gateway holt zurück** (mcp-gateway 0.29.0). Die
Einrichtungstür holt ein Zugangsprofil oder einen Assistenten zurück, wenn
sie es selbst entfernt hat. Den Beweis liefert die Prüfspur des Gateways;
das gilt auch für das, was 0.28.0 heute Morgen entfernt hat.

- Was ein Mensch widerrufen oder gelöscht hat, bleibt ein Konflikt.
- Ein Schlüssel kommt nie zurück.

Gemessen auf oaap-test im Mandanten rzt, wo der Lauf nach dem Rückgängig
angehalten hatte: Die Vorschau sagt „Holt zurück“, der Lauf ist fertig, und
danach steht überall „vorhanden“. Tests: 61/61 in der Einrichtungstür, die
übrigen Gateway-Tests grün.

Noch nicht geschehen: Push, und das Update von pxx-tools (bleibt auf 0.28.0
bis zu deinem Wort).

## 16. Stage 2, built (2026-11-20, reference 0.1.324)

**What is there:**

- **The list read** (§4) in three apps: `GET ?kind=<kind>` without `id`
  → `{"v": 1, "kind", "items": [{"id", "title", "light"?,
  "light_min"?}]}`. help 0.8.0 (`fetch`), ai-gateway 0.12.0 (`supplier`
  without URL and credential, `alias` with the worst and the best light
  of its targets, `client` with its ceiling), mcp-gateway 0.30.0
  (servers with light, views, valid profiles, assistants not deleted).
  `oaap.apps.runtime` 0.2.74, `oaap.ai.gateway` 0.9.0,
  `oaap.ai.mcp-gateway` 0.28.0.
- **Parameter kinds** `setup_item` (`need`, `item_kind`) and `light`
  (`from`) in `tenant_recipe` (`judge_choices`): a given id must be in
  the list; nothing given takes the default when listed, else the only
  item, else "bitte wählen"; an app without the read leaves the typed
  value standing, with a note. The light follows the item's `light` (the
  worst it can reach); stricter than `light_min` is refused. For the
  light the RFC text of §4 said "a worse one than the item needs"; built
  is the meaning: a ceiling under which the chat could never use the
  model.
- **Releases** (§5, finding C): `recipe:<id>@<major>` in
  `tenant_admin_may`; `oaap tenant allow|disallow <label>
  recipe:<id>[@<major>]` and the card "Rezepte" on *Aufbau*; log
  `tenant.recipe.release|unrelease`.
- **The tenant_admin** runs a released recipe in their own tenant
  (tenant id from their record), the filled steps inside the scope;
  continue/confirm need release and scope again, undo only the own
  tenant and never removes instances. The release is the operator's
  permission for exactly that recipe's steps -- this answers the open
  fact of D5: a `destination.ensure` with `auth: none` in a released
  recipe needs no `destinations` right.
- **Portal** (`oaap.core.portal` 0.3.57): page *Einrichten*
  (`/einrichten`, recipe form with "Was fehlt noch?" and "Einrichten",
  run page with "Rückgängig"), card "Rezepte" with "Freigegeben für" on
  *Aufbau*; every button a spool request `tenant-recipe`, the host's
  view `recipe-view.json`.
- `oaap.core.tenant` 1.13 (2.13, conformance test 33).
- Recipe `hilfe-assistent` 1.1.0: `model` is a `setup_item` (models /
  alias, default `standard`), `ceiling` a `light` from `model`.
- Tests: `test_tenant_recipe.py` 92 (52 of stage 1 + 40), new
  `test_tenant_recipe_page.py` 35; app tests `help/test_setup.py`,
  `ai-gateway/test_setup.py` 113, `mcp-gateway/test_setup.py` 67, all
  green; unchanged green: the build tests of §14, `test_portal_navigation`,
  `test_nav_view`, `test_destinations_admin_portal`, `test_cli_reference`,
  app tests (ai-gateway gateway/supply/props/catalog, mcp-gateway
  gateway/templates, help). In the Linux runner: `test_chain_check`,
  `test_tenant_recipe`, `test_tenant_recipe_page`,
  `test_tenant_build_page`. No full suite.

**Measured on oaap-test** (0.1.324 staged; tenant `rzt` with help 0.8.0,
ai-gateway 0.12.0, mcp-gateway 0.30.0 installed from the working tree; a
machine principal `rzt-probe-admin` with role `tenant_admin` in `rzt`,
no password; the portal's own code driven inside the portal container
with the gateway's headers, the real view file, the real spool and the
host's worker):

| Check | Result |
|---|---|
| CLI preview without a model name | the list from the AI gateway (`chat-default`), chosen as the only one; ceiling red from the model |
| `--param ceiling=yellow` / `model=gibts-nicht` | refused with the sentence (stricter than the model reaches) / with the list |
| `oaap tenant allow rzt recipe:hilfe-assistent` | `recipe:hilfe-assistent@1` in the record; view `released_for: [rzt]` |
| page `/einrichten` as tenant_admin | 200, side-bar entry, the released recipe, the tenant's three runs |
| "Rückgängig" of the last run | rolled back, log in the name of `rzt-probe-admin (tenant_admin)` |
| "Was fehlt noch?" | choices `model=chat-default`, `ceiling=red`; three steps *wird angelegt*, the button "Einrichten" with exactly those values |
| "Einrichten" | run done (the MCP gateway brought its items back, D12) |
| second "Was fehlt noch?" | all four *vorhanden*, no button |
| spool request past the portal: tenant_admin of `rzt` names `vuebung` | refused: own tenant only (S2) |
| spool request: tenant_admin releases | refused: only the server_admin |
| release taken back | the page says nothing is released; a preview is refused with the way to the operator; released again afterwards |
| S4: all eight lists of the three apps in `rzt` | only `id`, `title`, `light`, `light_min`; no secret of the instance's environment in the text; the supplier `openrouter` has its credential set |

**Not built in stage 2:** the link "Einrichten…" on an instance's page
and the link from a finished build to *Einrichten* (§7) -- small, left
for stage 3 together with the requests; a release for a version range
other than a major.

**Left on oaap-test:** `rzt` with the three app versions from the
working tree (sources `~/apps-s2`), the release `recipe:hilfe-assistent@1`,
the machine principal `rzt-probe-admin` (no key), the run
`r-20261120t100304-rzt`; `~/ref-0.1.324`, `~/probe_portal.py`,
`~/probe_s4.py`.

## Deutsche Zusammenfassung (Stufe 2 gebaut)

**Gebaut (Referenz 0.1.324):**

- **Werte aus der App:** Die Einrichtungstüren von Hilfe 0.8.0,
  KI-Gateway 0.12.0 und MCP-Gateway 0.30.0 nennen ihre Einträge
  (`GET ?kind=…`): Kennung, Titel, Ampel, nie einen Zugang. Im Rezept
  `hilfe-assistent` 1.1.0 wählt man den Modellnamen aus dieser Liste, und
  die Ampel folgt ihm.
- **Freigabe:** Der Betreiber gibt ein Rezept je Mandant frei
  (`oaap tenant allow <kürzel> recipe:<id>` oder auf „Aufbau“).
- **tenant_admin:** führt ein freigegebenes Rezept im eigenen Mandanten
  aus, auf der neuen Seite **Einrichten** im Portal.

**Gemessen auf oaap-test** mit einem tenant_admin über die echte
Portalseite: Rückgängig, Vorschau, Einrichten, zweite Vorschau alles
vorhanden. Abgelehnt wurden ein fremder Mandant, eine Freigabe durch den
tenant_admin und ein Lauf ohne Freigabe. In den Listen steht kein
Geheimnis.

**Offen:** der Link „Einrichten…“ auf der Instanzseite und nach einem
Aufbau, dazu Stufe 3 (Anfragen an den Betreiber als Vorgang, Rezept „SAP
SSO einrichten“, `recipe.apply` in Profilen).
