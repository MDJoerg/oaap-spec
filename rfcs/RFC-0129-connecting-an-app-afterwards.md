# RFC-0129: Connecting an App Afterwards — a Checklist per Instance

- **Status:** **Accepted (2026-11-25)** — discussed with Jörg the same day
  (I-70); D1–D8 decided the same day, all as recommended (§9). Nothing built
  or measured.
- **Date:** 2026-11-25
- **Authors:** Jörg (the need, 2026-11-24: "Besser bzw. parallel wäre ein
  ‚Einrichten' für den Tenant-Admin … BDT-Team und pch-root als potenzielle
  Arbeitsräume … ein nachträglicher Einrichten-Workflow wäre für mich
  angenehmer"), Claude (facts, design)
- **Depends on:** RFC-0121 (stores and workspaces, the contract
  `oaap.work.stores/1`), RFC-0091 stage 3 (an app's own realm client,
  `identity.oidc_client`), RFC-0104 (tenant build from a profile), RFC-0109
  (setup recipes, the portal page *Einrichten*), manifest 0.23 (`mcp`,
  `mcp_store`), `oaap.core.portal` 2.20 (the cards *Anmeldung über den Realm*
  and *Für den Chat*)
- **Related:** RFC-0033 (destinations — the exception of §6), RFC-0110
  (BookStack), RFC-0111 (personal slots), idea I-70
- **Changes (when accepted):** `oaap.core.portal` (the checklist on the
  instance page), `oaap.core.tenant` (profile steps call the same functions),
  `oaap.work.stores` (`about.ready`, `about.missing`), the profile
  `ki-arbeitsplatz` (a tick "mit Git")
- **Not part of this RFC:** the chat's workspace dialog (RFC-0121 §5); the
  content of any connector; access across tenants beyond the direction of §6.

## Summary

An app that a tenant already runs (an existing Forgejo, a wiki, BDT-Team)
should become a store in the tenant's AI chat **without a new tenant build**.
The pieces exist one by one — the realm client button, generated secrets,
"Für den Chat freigeben" — but nobody sees which of them an instance still
lacks. This RFC puts a **checklist on the instance page**: the steps this
app's manifest calls for, each with its actual state read live and a button,
and one button "Alles anschließen". The profile `ki-arbeitsplatz` runs **the
same functions** at build time, so a tick "mit Git" beside "mit Wiki" costs
almost nothing. The last step is the app's own word: the store contract gets
`ready` and `missing` in `about`. Products we control (BDT-Team, PCH)
implement the contract themselves; foreign ones (Forgejo, BookStack) bring a
connector service in their package.

## 1. Facts (read 2026-11-25)

| # | Fact |
|---|---|
| F1 | The instance page has the card **Anmeldung über den Realm** for an app with `identity.oidc_client` (request `app_idp`) and, on the card MCP of a store connector (`mcp_store`), the section **Für den Chat** (request `chat_store`) — `oaap.core.portal` 2.20, reference 0.1.375. |
| F2 | `oaap app config set <instance> <KEY> --generate` fills an empty generatable key; install generates nothing and names such keys (runtime 2.8). The portal's configuration tab has "Erzeugen". |
| F3 | The profile steps `idp.app` and `app.setup` exist; the tick "mit Wiki" in `ki-arbeitsplatz` 2.3.0 uses them (`when` as a list). |
| F4 | Forgejo 15.0.11+oaap.1 brings its connector as service `oaap`; **without `OAAP_FORGEJO_CONNECTOR_SECRET` the connector is off** and Forgejo runs as before (RFC-0121 §10.3). After the update of an existing Forgejo (projects.joomp.de) someone must decide to switch it on. |
| F5 | A tenant build does not write `chat_store`: the card *Für den Chat* says "nicht freigegeben" until somebody presses (finding of 24.11.). |
| F6 | The measurement of 24.11. used platform accounts (`ws375-ta`) that were **not** persons of the realm; a probe "as me" by such an admin cannot reach the content of an app that signs in through the realm. |
| F7 | **The word *Einrichten* is taken:** the portal page *Einrichten* in a tenant's context runs setup recipes (RFC-0109), and the instance page has a button "Einrichten…" with the recipes that need its app. |
| F8 | PCH 0.8.0 has an OAAP package with MCP under `/mcp` and the person from the gateway's headers; BDT-Team is "prepared for OAAP" (Jörg). Neither was run against `oaap.work.stores/1`. |

## 2. The checklist

On the instance page, a card **Anschließen** (name: D2) for the
`tenant_admin` of the instance's tenant and the `server_admin`. It lists only
the steps the manifest calls for; a step that does not apply is absent, not
grey.

| # | Step | Shown when | State read from | Button |
|---|---|---|---|---|
| S1 | Anmeldung über den Realm | `identity.oidc_client` | the client exists and is enabled at the provider; `OAAP_OIDC_*` set in the instance | "Einrichten" = request `app_idp on` (F1) |
| S2 | Geheimnisse | a `config` key with `generate` | each such key filled (never its value) | "Erzeugen" per key, or all — runtime 2.8 |
| S3 | Konnektor antwortet | `mcp` | the MCP door answers `initialize` through the platform's internal listener | — (shows the last log lines if not) |
| S4 | Für den Chat | `mcp_store` | the tenant's MCP gateway lists the store system with this door | "Freigeben" = request `chat_store on` (F1) |
| S5 | Wer darf | `mcp_store` | the roles of the door's route against the realm's role map: which groups reach it | link to the realm's role map |
| S6 | Die App sagt | `mcp_store` | `stores_about` → `ready`, `missing` (§4), asked as the admin | — (lists `missing`) |
| S7 | Probe als ich | `mcp_store` | `stores_areas` / `stores_stores` as the admin's own person: green with a count | — |

- **Live, never a flag.** Each state is read when the card opens (and after a
  button), not taken from a record that says it was done once. What was done
  by hand, by a profile or by the command line shows as done.
- **Each button is the existing request** (`app_idp`, `chat_store`, config
  generate), judged again by the host. The checklist adds no new authority.
- **"Alles anschließen"** runs the open steps in order and stops at the first
  that fails (D6), saying which and why.
- **S7 without a person in the realm** (F6) is yellow, not red: "nicht
  prüfbar — du bist im Realm dieses Mandanten nicht als Person bekannt"
  (D7).
- **Order of reading:** S1 before S3 (an app that signs in through the realm
  may not start its connector before), S2 before S3 (F4).

## 3. One rule, two roads

The profile steps run the **same functions** as the buttons: `idp.app` = S1,
a new `app.secrets` = S2, a new `chat.store` = S4 (closes F5). A tenant build
with `ki-arbeitsplatz` therefore leaves an instance whose checklist is green,
and the checklist is the test of the profile.

`ki-arbeitsplatz` gets a tick **"mit Git"** (Forgejo from the store, S1–S4)
beside "mit Wiki". A new store app needs **no profile step of its own**: its
manifest is enough.

## 4. The app's own word: `about.ready`, `about.missing`

`stores_about` may additionally return:

```json
{"ready": false,
 "missing": [{"code": "account", "text": "Konto oaap-konnektor fehlt",
              "who": "tenant_admin"}]}
```

- `ready` absent = unknown (an older connector); the checklist then relies on
  S7.
- `who`: `tenant_admin`, `server_admin` or `person` (something each person
  sets up for themselves, e.g. a personal credential).
- `text` is German, short, for the admin; never a secret or an address.
- Additive: the contract stays `oaap.work.stores/1`.
- First candidates from BDT-Team (RFC-0121 §10.4, B13): `BDT_HUB_ALLOW_AGENTS`
  off, no key for the service identity issued in the project (by its owner),
  the person no member, no default store.

## 5. Who builds a connector

| Product | Who implements `oaap.work.stores/1` | Where |
|---|---|---|
| Forgejo, BookStack, other foreign products | we, translating their API | a service in the product's OAAP package (RFC-0121 §3.5) |
| BDT-Team, PCH — products Jörg controls | **the product itself** | its own OAAP package, MCP door with `mcp_store` |

For the gateway both look the same. A product that implements the contract
itself also says itself what it can (`about`) and what it lacks (`missing`).
Order (Jörg, 25.11.): **BDT-Team before PCH** (D4) — a letter to the BDT side
explains the workspace scenario and asks for its feature list
(`program/brief-bdt-team-arbeitsraum-2026-11-25.md`).

## 6. Outside the tenant (the exception)

The workspace scenario assumes every instance in the **same tenant**: the
person is known through the realm (`assertion`) and enters nothing. An app in
another tenant or outside OAAP is reached through a **destination**
(RFC-0033): address, trust and release with the admin. The rule "no
technical user for content" (RFC-0121 §8.2) stays: across the boundary the
foreign system does not know our person, so each person stores their own
credential once (`personal`, RFC-0111). The destination opens the road; each
person unlocks it for themselves. In the checklist this shows as S1 replaced
by "Destination gebunden" and S7 as "für dich eingerichtet / nicht
eingerichtet". A stage of its own (§8), not designed further here.

## 7. Security requirements

1. The checklist shows states, never a secret value, an address of a
   credential or a token.
2. Every button is an existing request, judged again by the host for the
   person pressing it; the checklist itself grants nothing.
3. S6 and S7 call the connector **as the admin's own person**, through the
   platform's gateway, like any person — never with a technical account.
4. A tenant's admin sees and acts only on instances of their tenant.
5. Every action is audited as its request is today; reading the checklist is
   not.

## 8. Stages

| Stage | What | Measured by |
|---|---|---|
| **1** | the card, read only: S1–S7 for Forgejo and BookStack | `oaap-test`, `ws375`: a fresh Forgejo (all open), after the buttons by hand (all green); bait: a `tenant_admin` of another tenant 403 |
| **2** | the buttons and "Alles anschließen"; `about.ready/missing` in the Forgejo connector | `oaap-test`: a fresh Forgejo connected only from the card; projects.joomp.de as the first real case, with Jörg |
| **3** | profile steps `app.secrets`, `chat.store`; tick "mit Git" in `ki-arbeitsplatz` | a tenant build with "mit Wiki" and "mit Git" → checklist green without a press |
| **4** | BDT-Team implements the contract itself | `oaap-test`: two persons through the realm, a foreign project refused, an old revision refused, forged headers refused |
| **5** | PCH the same way | as 4 |
| **6** | outside the tenant: destination and personal credential (§6) | to be designed |

## 9. Decisions

- **D1 — A checklist on the instance page, not a guided wizard?**
  **Decided (Jörg, 25.11.): try the checklist** — it is context-sensitive and
  shows the state later too, not only the first time.
- **D2 — Its name, since *Einrichten* is taken (F7)?** **Decided (25.11.): (a).**
  (a) **"Anschließen"** — a card on the instance page, *Einrichten* stays the
  recipes' page (recommended);
  (b) "Einrichten" anyway, and the recipes' button on the instance page is
  renamed "Rezepte…";
  (c) the checklist becomes part of RFC-0109's *Einrichten* page, per instance.
- **D3 — Where do the steps come from?** **Decided (25.11.): (a)** — after
  first being left open in the discussion ("kann ich noch nicht entscheiden").
  (a) Derived from the manifest (`identity.oidc_client`, `generate`, `mcp`,
  `mcp_store`) plus the app's own word in `about` (§4) — no new manifest field
  (recommended);
  (b) a manifest field `setup:` listing the steps an app wants;
  (c) only the app's own word: a generic setup door every app implements.
- **D4 — BDT-Team before PCH?** **Decided (Jörg, 25.11.): yes** — Jörg works
  on BDT now and can shape its API.
- **D5 — Products we control implement the contract themselves?** **Decided (25.11.): (a).**
  (a) Yes, in their own OAAP package; foreign products get a connector service
  (recommended);
  (b) always a connector service of ours, also for BDT and PCH.
- **D6 — "Alles anschließen" on a failing step?** **Decided (25.11.): (a).**
  (a) stop there and say why (recommended);
  (b) carry on with the steps that do not depend on it.
- **D7 — The probe for an admin who is no person in the realm (F6)?** **Decided (25.11.): (a).**
  (a) yellow "nicht prüfbar", the step does not block (recommended);
  (b) red, the checklist is not green until a person of the realm checks.
- **D8 — Outside the tenant through destinations and a personal credential
  (§6)?** **Decided (25.11.): yes, as a stage of its own, designed later**
  (Jörg: "vielleicht über Destinationen").

## Deutsche Zusammenfassung

**Worum es geht:** Eine App, die ein Mandant schon betreibt (ein bestehendes
Forgejo, das Wiki, später BDT-Team), soll ohne neuen Mandantenaufbau als
Ablage in den KI-Chat. Die Bausteine gibt es schon einzeln: die Knöpfe
„Anmeldung über den Realm“ und „Für den Chat freigeben“ sowie das Erzeugen
von Geheimnissen. Es sieht aber niemand, was einer Instanz noch fehlt.

**Vorschlag:** Auf der Instanzseite steht eine **Checkliste** (Arbeitsname
„Anschließen“, weil „Einrichten“ schon die Rezeptseite aus RFC-0109 ist). Sie
zeigt nur die Schritte, die das Manifest der App verlangt:
1. Anmeldung über den Realm
2. Geheimnisse
3. Konnektor antwortet
4. Für den Chat
5. Wer darf
6. Was die App selbst meldet
7. Probe als ich

Jeder Schritt hat eine Ampel, die live gelesen wird, und einen Knopf. Dazu
kommt „Alles anschließen“. Die Knöpfe sind die vorhandenen Anfragen, die
Checkliste gibt keine neuen Rechte.

**Zwei Wege, eine Regel:** Das Profil `ki-arbeitsplatz` ruft dieselben
Funktionen auf. Daher ist der Haken „mit Git“ neben „mit Wiki“ fast
geschenkt, und nach einem Aufbau ist die Checkliste grün.

**Die App sagt selbst, was fehlt:** `stores_about` liefert zusätzlich
`ready` und `missing`. Lösungen, die wir selbst in der Hand haben (BDT-Team,
PCH), setzen den Vertrag selbst um. Fremde Produkte (Forgejo, BookStack)
bekommen einen Konnektor-Dienst im Paket.

**Außerhalb des Mandanten (Ausnahme):** Der Zugang läuft über eine
Destination. Jede Person hinterlegt dort einmal ihren eigenen Zugang, denn
es gibt keinen technischen Benutzer für Inhalte. Das wird eine eigene, spätere
Stufe.

**Entschieden (25.11., D1–D8, alle wie empfohlen):**
- D1: Checkliste statt Assistent
- D2: Name „Anschließen“
- D3: Schritte aus dem Manifest plus Selbstauskunft der App, kein neues Feld
- D4: BDT-Team vor PCH
- D5: Eigene Produkte setzen den Vertrag selbst um
- D6: „Alles anschließen“ hält beim ersten Fehler an
- D7: Probe ohne Realm-Person nur gelb, blockiert nicht
- D8: Ausnahmen außerhalb des Mandanten über Destination plus persönlichen
  Zugang, als eigene spätere Stufe

Gebaut ist nichts.
