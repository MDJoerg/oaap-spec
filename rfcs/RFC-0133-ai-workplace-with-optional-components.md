# RFC-0133: The AI Workplace with Optional Components

- **Status:** **Accepted (2026-11-25)** — D1–D7 decided by Jörg the same day,
  one at a time, all as recommended (§6). **Stage 1 built** (§6a), not rolled out.
- **Date:** 2026-11-25
- **Authors:** Jörg (the need: "Ich möchte danach einen Aufbau machen: KI-Arbeitsplatz
  mit optionalen Komponenten wie bookstack, forgejo, bdt-team" and "Richte die
  Recherche noch ein. Diese auch in den KI-Arbeitsplatz aufnehmen."), Claude (design)
- **Depends on:** RFC-0055 (tenant build from a profile), RFC-0104 (profile
  `ki-arbeitsplatz`), RFC-0121 (stores and workspaces), RFC-0116 (web research),
  RFC-0129 (connecting an app afterwards)
- **Changes (when accepted):** profile `ki-arbeitsplatz` 3.0.0 (oaap-docs);
  `oaap.ai.mcp-gateway` (setup kind `profile` takes `stores`); RFC-0055 §14
  (an app named only under a tick); nothing in the chat

## Summary

The profile `ki-arbeitsplatz` 2.3 builds a tenant with chat, help, tools,
models and cases, and — with a tick — a wiki. Tenant csa was set up by hand
on 2026-11-25 exactly like pxx: Forgejo ("projects"), BookStack ("wiki"),
BDT-TEAM, Research, the assistants BDT and Research, three store systems for
the chat's workspaces (CS 877, 878). That run is the recipe; this RFC turns it
into **four ticks** of the same profile — **Wiki**, **Projects (Forgejo)**,
**BDT-TEAM**, **Research** — each independent of the others, and closes the
three gaps the hand run showed.

## 1. What each tick builds

| Tick | Needs | Apps (instance name, editable) | Setup in the tools gateway |
|---|---|---|---|
| `with_wiki` (exists) | realm | bookstack `wiki`: 3 keys generated, admin group `/oaap-verwalter`, roles `/wiki-redaktion`, `/wiki-lesen`, realm sign-in | source yellow; store system `wiki` (bookstack) |
| `with_projects` | realm | forgejo `projects`: connector key generated, admin group `/oaap-verwalter`, realm sign-in | source yellow; store system `projects` (forgejo) |
| `with_bdt` | a source that lists `bdt-team` (D4) | bdt-team `bdt-team`: settings for the workplace (D5), two keys generated | source yellow; store system `bdt-team` (bdt); view `bdt` (the four `bdt_*`, a fixed list), profile `<chat>-bdt` (write), assistant **BDT** |
| `with_research` | — | recherche `recherche` with its own search service | view `recherche` (web_search, web_fetch), profile `<chat>-recherche` (read, ceiling red), assistant **Research**; the source stays red and "untrusted" |

Every assistant uses the model name `standard` the profile already makes. Every
access profile of the chat gets the store door (§3), so any assistant in a
workspace reaches every store system the tenant has.

## 2. What the hand run showed (csa, CS 877/878)

1. **The store door belongs to an access profile, not to a store system.**
   `stores` is a column of the profile; a store item only switches it on for the
   profiles it names, and only for profiles that exist. In csa the BDT and the
   Research profile came after the stores and had no door until the stores were
   applied a second time. In a profile with optional parts the list of doors
   cannot be written down: it depends on the ticks. → §3, D3.
2. **A view `{server, effect: read}` takes every reading tool** — on BDT-TEAM also
   the eight `stores_*`, which belong to the store door, not to the assistant.
   The setup door does not change an existing view (conflict). → the profile uses
   the fixed list (already possible).
3. **The defaults of the BDT package are not those of a workplace** (access
   optional, hub features, MCP gateway, help via MCP, new stores — all off). In
   csa 13 values were set by hand. → D5.
4. **BDT-TEAM is listed only in the operator catalog of oaapx01.** RFC-0055 §14
   refuses the upload of a profile whose `app` no configured source lists — the
   whole profile, even with the tick off. → §4, D4.
5. Forgejo had no administrator from the realm (only the connector account). The
   package has `OAAP_FORGEJO_ADMIN_GROUP`; the profile sets it like the wiki. → D6.
6. A spool request names the tenant by its id, the CLI by its label; and model
   names differ per tenant (`chat-default` in pxx, `standard` in csa). Neither
   matters inside a build (it names the tenant it creates, and makes `standard`).

## 3. The store door on the access profile (mcp-gateway)

The setup kind `profile` takes an optional `"stores": true`: the profile is made
(or found) with its store door on. A store item no longer needs to name doors;
`doors` stays for "Für den Chat freigeben" and older builds. A profile with
`stores: true` that already exists without the door gets it (an addition, never
a conflict — the same rule store items follow today). The door is still only a
door: what a person sees in a store is decided by the store system as that person
(RFC-0121).

## 4. An app named only under a tick (RFC-0055 §14)

An `app.install` whose step has a `when` is checked at upload only for its shape;
an `app` no configured source lists is **not** a refusal there. The build page
shows the tick greyed with the sentence "BDT-TEAM steht in keiner Paketquelle
dieses Knotens" and the preview refuses the tick if set. Without `when` nothing
changes: an unknown app still refuses the profile.

## 5. Stages

1. **Build:** mcp-gateway `profile.stores` (§3); reference: §4 at upload,
   preview and page; profile 3.0.0 with the four ticks and parameters
   `name_projects`, `name_bdt`, `name_research`. Tests: gateway (door on a
   profile made after the stores; existing profile gets the door), reference
   (upload with an unknown app under a tick; preview refuses the set tick).
2. **Measure on oaap-test:** a tenant from 3.0 with wiki, projects and research
   (BDT is not in a source there): every step DONE, three assistants, two store
   systems, every profile with the door; then removed.
3. **On oaapx01 (Jörg's word):** a tenant with all four ticks; a person signs in to
   Forgejo, wiki and BDT, opens a workspace with all three stores.

## 6a. As built (stage 1, 2026-11-25)

- **mcp-gateway 0.51.0:** `setup_item` takes `stores` off a `profile` item,
  runs the item as before, then switches the door on (`setup_profile_door`);
  `test_setup` 139 (+9: a profile made after the store systems gets the door,
  a present one gets it as `made`, `false`, baits: `"ja"`, a different profile
  stays a conflict, a key's label never gets the door), `test_gateway` 587.
- **Reference (0.1.380):** `upload_problems` lets an unknown app under `when`
  through; `tenant_build_apps_refusal` refuses a set tick with its label
  (`ticked_unknown_apps`); the start page greys the tick (`tick_apps`,
  `unavailable_ticks`). Found while writing the profile: an `app.setup` item
  could hold only lists of text -- a view's fixed tool list is a list of
  objects -- so a list may now also hold **flat objects of text** (no nesting,
  no secret names, parameters checked and filled). Linux runner: 12 files green.
- **Profile `ki-arbeitsplatz` 3.0.0:** ticks `with_projects`, `with_bdt`,
  `with_research` beside `with_wiki`, names `name_projects`, `name_bdt`,
  `name_research`; every access profile of the chat with `stores: true`.
  Needs mcp-gateway 0.51.0 in the store (an older gateway refuses `stores`).

## 6. Decisions (Jörg, 2026-11-25, all (a))

- **D1 One profile or several.** (a) `ki-arbeitsplatz` 3.0 with four ticks
  (recommended: one place, the base stays the same); (b) a separate profile per
  combination.
- **D2 Research in the profile.** (a) its three setup items written into the
  profile, the same text as recipe `recherche` 1.2.1 (recommended: no new step
  type); (b) a new step type `recipe.run`.
- **D3 Store door.** (a) `stores: true` on the access profile (§3, recommended);
  (b) order the steps and name the doors per tick — breaks as soon as two
  optional profiles meet.
- **D4 An app only some nodes have.** (a) tick greyed with a sentence, the profile
  uploads everywhere (§4, recommended); (b) BDT-TEAM stays out of the profile.
- **D5 BDT settings.** (a) the 13 values as `app.config` steps in the profile
  (recommended now; nothing to change elsewhere); (b) ask the BDT side for one
  switch "Arbeitsplatz" that sets them, and the profile sets only that.
- **D6 Administrators in Forgejo.** (a) the admin group `/oaap-verwalter`, like
  the wiki (recommended); (b) nobody from the realm, as in pxx and csa today.
- **D7 Ticks by default.** (a) all off — the person chooses (recommended);
  (b) Research on.

## Deutsche Zusammenfassung

Der Aufbau „KI-Arbeitsplatz“ (Profil `ki-arbeitsplatz`, heute 2.3 mit Haken
„Wiki“) bekommt vier unabhängige Haken: **Wiki**, **Projekte (Forgejo)**,
**BDT-TEAM** und **Recherche**. Jeder Haken installiert seine App, setzt ihre
Schlüssel und Einstellungen, meldet über den Realm an (Wiki, Projekte), legt im
MCP-Gateway die Ablage für die Arbeitsräume an und — bei BDT und Recherche —
Sicht, Zugangsprofil und Assistenten. Vorlage ist die Einrichtung von csa von
heute (CS 877/878). Drei Lücken schließt das RFC: (1) Die Ablagetür hängt am
Zugangsprofil; ein Profil mit `stores: true` bekommt sie, egal in welcher
Reihenfolge die Haken laufen. (2) Ein Haken, dessen App ein Knoten nicht kennt
(BDT-TEAM steht nur im Betreiber-Katalog von oaapx01), wird ausgegraut statt das
ganze Profil abzulehnen. (3) Die BDT-Einstellungen für den Arbeitsplatz setzt
das Profil selbst. Dazu bekommt Forgejo die Verwaltergruppe als Administratoren.
Stufe 1 ist gebaut (mcp-gateway 0.51.0, Referenz 0.1.380, Profil 3.0.0; §6a), nicht ausgerollt. Jörg hat D1–D7 am 25.11. einzeln entschieden, alle wie empfohlen: ein Profil mit vier Haken, Recherche direkt im Profil, `stores: true` am Zugangsprofil, BDT-Haken ausgrauen, 13 BDT-Werte im Profil, Verwaltergruppe als Forgejo-Admin, alle Haken aus.
