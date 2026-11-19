# RFC-0104: An AI Workplace From a Tenant Profile — Destinations, Setup Doors, and a Chat That Reaches Its Model Gateway Without a Key

- **Status:** **Accepted (2026-11-19)** — Jörg: "Alles wie empfohlen,
  Kürzel kit1, schreib das RFC", after going through the points in
  conversation. D1–D7 decided as recommended. **Stage 1 built**
  (reference 0.1.314, profile `ki-arbeitsplatz` 1.0.0, not pushed), §11.
- **Date:** 2026-11-19
- **Authors:**
  - Jörg: the wish to build a tenant with the AI apps from the portal,
    without SAP single sign-on for now, and first to make the normal
    tenant build able to do it.
  - Claude: reading of RFC-0055, the guide „Eine Mandantenlandschaft
    einrichten“ (oaap-docs), the manifests of `chat`, `mcp-gateway`,
    `ai-gateway`, `help`, `vorgaenge`; design.
- **Depends on:**
  - RFC-0055: tenant build from a profile, its step types and engine.
  - RFC-0074 and `oaap.apps.runtime` 2.32.3: procedure A, the chat at
    its tenant's MCP gateways through the platform's via door.
  - RFC-0097: assistants live in the MCP gateway.
  - RFC-0064 and `oaap.ai.gateway`: keys, model names, the light.
  - `oaap.net.destinations`: destinations and their assignment.
  - RFC-0087 §8.2: the node asks an instance on its internal endpoint.
- **Amends:** RFC-0055 §2 (three new step types, one new read for
  `manual.done_when`).
- **Not part of this RFC:**
  - SAP single sign-on and propagation to SAP (RFC-0091, RFC-0095).
  - A shared model gateway of the node for several tenants (RFC-0100).
  - Test instances next to the productive ones in this profile.
  - Volume per person in the model gateway (§9, O1).

## Summary

In `bec` the AI landscape (chat, MCP gateway, model gateway, help,
cases) was set up by hand: about fifteen steps in four apps, following
the guide. The tenant build of RFC-0055 can install those apps from the
store, but it cannot wire them. This RFC closes that gap so that a
server admin builds an **AI workplace** in the portal from one profile.

1. **A step type `destination.ensure`.** It creates a destination and
   assigns it to an instance, as the portal's „Zuordnen“ does. The help
   gets `docs-origin` this way.
2. **A setup door per app** (manifest field `setup`) and a step type
   **`app.setup`**. The build tells an app what it wants in place, for
   example „view `hilfe` with platform access, profile for `@<chat>`“.
   The app creates it by the same rules as its own pages and answers per
   item. The platform never writes an app's data itself.
3. **The chat reaches its model gateway without a key** (manifest fields
   `ai_client` and `ai_gateway`). Like the way to the MCP gateway today:
   a via door on the chat's own site, the chat's platform key plus the
   person's assertion, and in the model gateway a **client grant** for
   the instance instead of a bearer key. The secret that a human copied
   from the model gateway into the destination `ki` disappears. The
   destination `ki` stays for a gateway outside the tenant.
4. **A profile `ki-arbeitsplatz`** in oaap-docs: tenant, help, MCP
   gateway, model gateway, chat, cases, wired, with one assistant „Hilfe“
   for the whole tenant. It stops twice for a human: for the supplier's
   credentials (for example the Anthropic key) and for the first
   administrator.

The first tenant built from it is `kit1` on `oaapx01`.

## 1. Facts (read 2026-11-19)

- **The engine** (RFC-0055) knows the step types `tenant.create`,
  `tenant.face`, `address.ensure`, `address.wait`, `idp.provision`,
  `idp.admin_group`, `tenant.policy`, `app.install` (also from a store
  source by `app`), `app.config` (also `generate: true`), `authz.setup`,
  `manual`, `backup.check`. Profiles live in `/var/lib/oaap/profiles`;
  the portal page „Aufbau“ starts, continues and undoes a build.
- **`oaapx01` has no profile** (`/var/lib/oaap/profiles` does not exist).
  The two examples in `oaap-docs/szenarien/profile` (`kunde-standard`,
  `handballverein`) contain no AI app.
- **The hand steps** of the guide (steps 1–4), and whether a profile can
  do them today:

  | step | today |
  |---|---|
  | install help, mcp-gateway, ai-gateway, chat, vorgaenge | yes (`app.install`) |
  | generate `AIGW_MASTER_KEY` | yes (`app.config` with `generate`) |
  | roles from the chat's templates `assistant_user`, `assistant_keyuser` | yes (`authz.setup`) |
  | destination `docs-origin` for the help, `ki` for the chat | no |
  | MCP gateway: light of the help server, view `hilfe` with access „Plattform (Chat)“, access profile `@<chat>` | no (kept only in the app) |
  | MCP gateway: an assistant for the tenant | no (`CHAT_ASSISTANT` is the old place, RFC-0097 moved assistants into the gateway) |
  | model gateway: supplier, model names, a key for the chat | no |
  | the model gateway's key into the destination `ki` | no — and only a human could, by seeing it |
  | the supplier's credentials | stays a human's step |

- **Cases need no wiring.** The chat's feedback goes to
  `/platform/feedback` on its own origin; the platform delivers it to the
  tenant's `vorgaenge` instance. Installing it is enough.
- **The model gateway** authenticates every call with a bearer key
  (`keys` table: model names, ceiling, personal-data flag, budget, rate).
  Its `usage` rows name the key, never a person.
- **The chat reaches the MCP gateway** without a destination, through
  procedure A (`oaap.apps.runtime` 2.32.3): `OAAP_MCP_CLIENT_KEY`, the
  list `/platform/mcp/gateways` and a via door per gateway on the chat's
  own site.

## 2. `destination.ensure` (D1, stage 1)

A new step type of RFC-0055 §2:

| Type | Do | Check | Undo |
|---|---|---|---|
| `destination.ensure` | create the destination in the tenant (the function behind `oaap destination add`) and assign it to the instance (the function behind the portal's „Zuordnen“) | a destination of that name exists in the tenant with the wished target and auth kind, and is assigned to that instance | unassign; remove the destination only if this build made it |

- **Params:** `name`, `instance`, `target`, `auth` (`none`, `basic`,
  `bearer`, `header`), and for `basic`/`header` the fixed parts (`user`,
  `header`).
- **No secret in a profile.** A destination that needs a secret is made
  without it, and a `manual` step with the read `destination.secret`
  (§5) waits until a human has entered it on the instance page. A
  profile file never holds a secret, and neither does a build's state.
- **Conflict, not adoption.** A destination of that name that this build
  did not make and that differs from the wish is a conflict; the build
  stops and says what differs.

## 3. The setup door (D2, stage 2)

### 3.1 Manifest and call

```yaml
setup:
  path: /oaap/setup        # on the internal endpoint, like /oaap/assets
  items: [view, profile, assistant, server_light, refresh]   # what the app can set up
```

- **The node calls the instance** on its internal endpoint (RFC-0087
  §8.2), never through the public route:
  - `GET <path>` — what the app can set up and, per kind, what is
    present.
  - `POST <path>` with `{"v": 1, "items": [{"kind": …, "id": …, …}]}` —
    the wished state.
- **Who is asking.** The call carries an assertion of the platform
  (`oaap.core.identity`) for the build's actor, addressed to the
  instance, with the claim `oaap/setup: true`. An app accepts a setup
  call only with that claim and only for the actor's tenant. From
  outside, `/oaap/*` lies behind `admin` anyway; the claim is the second
  lock, because identity issues it only to the build engine.
- **The answer per item:** `present` (already as wished), `made`
  (created now), `conflict` (something of that id exists and differs;
  the sentence says what), `refused` (the app does not allow it; the
  sentence says why). The app never overwrites what a human made: a
  difference is a conflict, and the build stops there.
- **Idempotent.** The same POST twice gives `made` then `present`. This
  is what RFC-0055's check needs: `app.setup`'s check is the same POST
  with `"dry": true`, which changes nothing and answers what it would do.
- **Undo:** an item that answered `made` is recorded in the build's
  `made` list; `app.setup`'s undo sends `{"remove": [ids]}`, and the app
  removes only items it made for a setup call, never one a human changed
  since (it answers `conflict`).

### 3.2 The step type

| Type | Do | Check | Undo |
|---|---|---|---|
| `app.setup` | POST the step's `items` to the instance's setup door | the same POST with `dry: true` answers `present` for every item | `remove` for the items this build made (§3.1) |

### 3.3 What each app offers

- **`mcp-gateway`:**
  - `refresh` — read the platform sources now (what „Quellen jetzt
    einlesen“ does), then the catalog of a named server. The catalog of a
    platform source is read with the actor's assertion, as the operator
    page does (mcp-gateway 0.7.2).
  - `server_light` — the light of a server.
  - `view` — name, accesses (`platform`, `signin`, `key`), the tools:
    either a list or `{"server": …, "effect": "read"}` for all reading
    tools of a server.
  - `profile` — group (`@<chat>`), views, ceiling.
  - `assistant` — id, title, view, gateway, model name, greeting,
    visibility (`tenant`). A first revision `@1` (RFC-0097).
- **`ai-gateway`:**
  - `supplier` — name, address up to `/v1`, light. **Never the
    credentials:** those a human types on the gateway's own page (§5,
    read `setup.ready`).
  - `alias` — a model name, the supplier and the supplier's model id.
  - `client` — the grant of §4 for an instance: model names, ceiling,
    personal-data flag, budget, rate.
- **`help`:** `fetch` — fetch the documentation now (what „Jetzt holen“
  does) once `docs-origin` is assigned.
- **`chat`:** nothing in this RFC. Its roles come from `authz.setup`, its
  assistants from the MCP gateway, its model gateway from §4.

## 4. The chat at its model gateway without a key (D3, stage 2)

The same shape as procedure A for the MCP gateway (`oaap.apps.runtime`
2.32.3), for models.

- **Manifest:**
  - The chat declares `ai_client: {use: true}`. The instance gets
    `OAAP_AI_CLIENT_KEY` (an API key of `instance:<name>` limited to the
    pseudo-instance `oaap.ai.client:<name>`) and `OAAP_AI_CLIENT_URL`
    (`…/platform/ai/gateways` on its own site). Minted, renewed, reissued
    and retired like `OAAP_MCP_CLIENT_KEY`.
  - The model gateway declares `ai_gateway: {serve: true}`. That is what
    puts an instance into the list.
- **The list** `/platform/ai/gateways` on the chat's own site: the
  instances of the same tenant on this node that declare `ai_gateway`,
  not a rehearsal, sorted by name, each with its via door.
- **The via door** `/platform/ai/via/<gateway>/*` → `/v1/*` at the
  gateway, with `forward_auth` to identity
  (`via=oaap.ai.client:<chat>`). Two credentials, both required: the
  chat's client key and the person's act assertion. The door strips both
  and sets `X-OAAP-AI-Client: <chat>` itself.
- **The client grant in the model gateway.** A row of kind `client` in
  `keys`, label = the chat instance's name, without a digest. A call
  that arrives through the via door is authorised by that row: its model
  names, ceiling, personal-data flag, budget and rate apply exactly as
  for a key. A call with `X-OAAP-AI-Client` on the public route cannot
  happen (the platform strips it there, as for the MCP headers); a
  client without a grant gets the same `403` as an unknown key.
- **Which way the chat takes:**
  1. a destination `ki` assigned to the chat → that, as today (an
     explicit choice by a human wins, `bec` stays as it is);
  2. otherwise exactly one gateway in the list → its via door;
  3. several → the configuration value `CHAT_AI_GATEWAY` names one;
     without it, „Einrichtung prüfen“ says so.
- **What the model gateway records:** the client instance in its `usage`
  rows, as it records the key today. **Not the person**, although the
  door delivers one (§9, O1).

## 5. Reads for `manual.done_when`

RFC-0055's `manual` steps wait on a read. Two new reads:

- `destination.secret` (`name`, `instance`) — the destination has a
  secret. Never its value.
- `setup.ready` (`instance`, `kind`, `id`) — the instance's setup door
  says the item is ready. For an `ai-gateway` `supplier` that means:
  credentials stored and the supplier's test answered.

## 6. The profile `ki-arbeitsplatz` (D4–D6)

In `oaap-docs/szenarien/profile/ki-arbeitsplatz.json`, next to
`kunde-standard`.

- **Params:**
  - `label`, `title`, `color`, as in `kunde-standard`;
  - `supplier_url` (default `https://api.anthropic.com/v1`),
    `supplier_light` (default `yellow`), `model` (the supplier's model
    id behind the model name `standard`);
  - `with_realm` (default `false`; nothing in this profile needs a
    realm, §1 of the guide).
- **Steps, in this order:**
  1. `tenant.create`, `tenant.face`, `address.ensure`, `tenant.policy`
     (first login = role `user`).
  2. `app.install` from the store: `help` as `{label}-hilfe`,
     `mcp-gateway` as `{label}-werkzeuge`, `ai-gateway` as
     `{label}-modelle`, `chat` as `{label}-chat`, `vorgaenge` as
     `{label}-vorgaenge`. No test instances (D4).
  3. `app.config` `{label}-modelle` `AIGW_MASTER_KEY` `generate: true`.
  4. `destination.ensure` `docs-origin` → `{label}-hilfe`, target
     `https://codeload.github.com/MDJoerg/oaap-docs`, auth `none`;
     `app.setup` `{label}-hilfe` `fetch`.
  5. `app.setup` `{label}-modelle` `supplier`.
  6. `manual` „Zugangsdaten der Bezugsquelle eintragen“, `done_when`
     `setup.ready` (D5: an own model gateway per tenant; the key of the
     customer is typed by a human).
  7. `app.setup` `{label}-modelle`: `alias` `standard` → `{model}`;
     `client` for `{label}-chat` with `standard`, ceiling `yellow`.
  8. `app.setup` `{label}-werkzeuge`: `refresh` for `{label}-hilfe`;
     `server_light` `green` (the help serves public documentation);
     `view` `hilfe` (access `platform`, all reading tools of the help);
     `profile` for `@{label}-chat` with `hilfe`, ceiling `yellow`;
     `assistant` `hilfe` with model name `standard`, visibility `tenant`
     (D7).
  9. `authz.setup` for the chat (D6, §7).
  10. `manual` first administrator, `done_when` `role.tenant_admin`, as
      in `kunde-standard`.
  11. `backup.check`.

## 7. Who may use the assistants (D6)

Every person of the tenant gets `assistant_user`; the tenant's
administration gets `assistant_keyuser`; both from the chat's
templates through `authz.setup`. Whoever wants it narrower takes it away
in the portal afterwards.

- **To verify in stage 1:** how „every person of the tenant“ is
  expressed with today's `authz setup` (a mapping on the tenant's default
  role, or a group every person gets), and whether a tenant-visible
  assistant needs `use` with a context. If neither fits, stage 1 adds
  the smallest form of it to `authz setup` and says so in §11.

## 8. Security requirements

Each names the bait a test uses.

1. A profile and a build's state never hold a secret. Bait: a build of
   `ki-arbeitsplatz` with credentials entered; `grep` of the profile, the
   build state and the tenant's audit log for the supplier key finds
   nothing.
2. The setup door accepts only the platform's setup assertion for its own
   tenant. Bait: a POST with a person's assertion of the tenant
   (`tenant_admin`) → refused; with the setup claim for another tenant →
   refused.
3. The setup door never overwrites what a human made. Bait: a view
   `hilfe` changed by hand, then the build continued → `conflict`, the
   view unchanged.
4. A model call through the via door needs both credentials. Bait:
   the chat's client key without an act assertion → refused; a person's
   assertion without the client key → refused.
5. `X-OAAP-AI-Client` cannot be set from outside. Bait: a call on the
   gateway's public `/v1` with that header and no key → `403`.
6. A client without a grant gets nothing. Bait: a second chat in the
   tenant without a grant → `403`, same answer as an unknown key.
7. The grant's ceiling holds as a key's does. Bait: a request asking for
   `red` from a client with ceiling `yellow` → refused.
8. A via door exists only inside the tenant. Bait: a chat in another
   tenant on the same node does not list the gateway.

## 9. Decisions and open points

All decided by Jörg on 2026-11-19, as recommended.

- **D1 Destinations:** a step type `destination.ensure`; secrets never in
  a profile, a `manual` step waits for them.
- **D2 Setup doors:** each app offers a setup door; the platform never
  writes an app's data.
- **D3 Model gateway without a key:** the chat reaches the tenant's model
  gateway through a via door with a client grant; the destination `ki`
  stays for a gateway outside the tenant and wins when assigned.
- **D4 Contents:** help, MCP gateway, model gateway, chat, cases; no test
  instances in this profile.
- **D5 Models:** an own model gateway per tenant; the supplier's
  credentials are a human's step.
- **D6 Rights:** everyone `assistant_user`, the administration
  `assistant_keyuser`, from the templates.
- **D7 First assistant:** „Hilfe“ for the whole tenant, created in the
  MCP gateway.
- **Tenant:** the first build is `kit1` on `oaapx01` (a neutral label: it
  is in the host name and so in the public certificate log).

Open, not needed for the stages:

- **O1** Volume per person in the model gateway. The door delivers the
  person; recording it would be personal data and is not done.
- **O2** Test instances in the profile (each one wired twice).
- **O3** A profile with a realm and the person's sign-in at the MCP
  gateway (guide step 6).

## 10. Stages and tests

| stage | content | done when |
|---|---|---|
| 1 | D1, D4–D6: `destination.ensure`, the read `destination.secret`, profile `ki-arbeitsplatz` **version 1** with `manual` steps for everything inside the apps (text from the guide) and the destination `ki` made by the build, its secret entered by a human | on a test node, a build of version 1 reaches the end with its manual steps; the help has `docs-origin` without a human assigning it; §7's question answered |
| 2 | D2, D3, D7: setup doors in mcp-gateway, ai-gateway, help; `app.setup`, the read `setup.ready`; manifest `setup`, `ai_client`, `ai_gateway`; via door and client grant; chat takes the way of §4 | profile **version 2** without `ki` and with only the two human steps of §6; baits 1–8 hold; a chat built so answers a question with a page of the help as source |
| 3 | the profile on `oaapx01`, build of `kit1`, tried as a person | `kit1` built from the portal page „Aufbau“; a person who is not administration asks the assistant „Hilfe“ and gets an answer with a source; the MCP gateway's audit shows the call with the person and the chat; the model gateway's usage shows the client |

Stage 3 needs the platform version of stage 2 on `oaapx01` and the new
app versions in the store; rolling those out, like every push, waits for
Jörg's word.

Spec changes:

- `oaap.apps.runtime`: manifest 0.18 with `setup`, `ai_client`,
  `ai_gateway`; the list and via door for models next to 2.32.3.
- `oaap.core.identity`: `via=oaap.ai.client:<name>`; the setup assertion
  with `oaap/setup`.
- `oaap.ai.gateway`: client grants; what `usage` records for them.
- `oaap.ai.mcp-gateway`: the setup door's items.
- `oaap.ai.assistants`: an assistant created by setup.
- RFC-0055 §2 gets the three step types and two reads, with a pointer
  here. The guide „Eine Mandantenlandschaft einrichten“ gets „aus dem
  Profil“ as its first way.

## 11. Stage 1, built (2026-11-19)

Reference 0.1.314, profile `ki-arbeitsplatz` 1.0.0 in
`oaap-docs/szenarien/profile`.

- **Built:**
  - Step type `destination.ensure` as in §2: the destination through
    `destination_add` (new argument `secret_later`: a destination that
    needs a secret is made without one and listed as SECRET MISSING), the
    binding through `destination_bind`. Both write the tenant's audit log
    with the build's actor. The `made` items are `destination:<name>` and
    `binding:<instance>:<need>`; after an interruption the step claims
    only a destination created after the build started.
  - The read `destination.secret` for `manual` (§5).
  - The profile refuses a key `secret`, `password` or `token`, an `auth`
    outside `none`/`basic`/`bearer`/`header` (no principal propagation:
    its certificate pin cannot be known in advance), `basic` without
    `user`, `header` without `header`, and `destination`/`instance` on a
    `manual` step with another `done_when`.
  - The portal's build page names the step type.
  - Profile version 1: the five apps, `AIGW_MASTER_KEY` generated,
    `docs-origin` and `ki` made by the build, the first administrator,
    and four `manual` steps with the guide's text for what is set up
    inside the apps (help fetch, model gateway, MCP gateway, assistant).
    The address of the model gateway is a parameter `ki_url` in this
    version; version 2 drops it with `ki`.
- **§7 answered, by reading `oaap-apps/lib/assistants`:** an assistant
  with visibility `tenant` is seen by every person of the tenant
  (`can_see`) and kept only by `tenant_admin` (`can_manage`). That is D6
  already; `assistant_user` and `assistant_keyuser` are for team
  assistants with a team as context. So the profile has **no
  `authz.setup` step**: the assistant „Hilfe“ with visibility `tenant`
  gives everyone use and the administration care. A team assistant later
  still needs the templates in „Rollen & Rechte“.
- **Measured locally (no full reference suite; the Linux runner was not
  available, Docker was not running):**
  - `test_tenant_build_destination.py` 30/30 (new).
  - `test_tenant_build`, `test_tenant_build_apps`, `test_tenant_build_config`,
    `test_tenant_build_doors`, `test_tenant_build_page`,
    `test_build_administer`, `test_build_page_details`,
    `test_profile_versions`, `test_tenant_profile`,
    `test_tenant_profile_page`, `test_destinations`,
    `test_destinations_portal`, `test_destinations_admin_portal`,
    `test_destinations_through`, `test_authz_setup_step`: all pass.
  - The three profiles in `oaap-docs/szenarien/profile` pass the profile
    check; `ki-arbeitsplatz` also passes the upload check.
- **Not measured:** a build on a node. The done-when of stage 1 („a
  build of version 1 reaches the end on a test node“) is still open.

## Zusammenfassung auf Deutsch

**Worum es geht:** In `bec` wurde die KI-Landschaft von Hand eingerichtet:
rund fünfzehn Handgriffe in vier Apps. Der Mandantenaufbau aus einem
Profil (RFC-0055) kann die Apps installieren, aber nicht verdrahten.
Dieses RFC schließt die Lücke, damit ein Serververwalter einen
**KI-Arbeitsplatz** im Portal aus einem Profil aufbaut.

**Entschieden am 19.11. (alles wie empfohlen):**

1. **Destinations im Aufbau** (D1): eine Schrittart `destination.ensure`
   legt eine Destination an und ordnet sie zu. Geheimnisse stehen nie im
   Profil; ein Haltepunkt wartet, bis ein Mensch sie einträgt.
2. **Einrichtungstür je App** (D2): Der Aufbau sagt einer App, was er
   haben will („Sicht `hilfe`, Profil für `@chat`, Assistent `hilfe`“).
   Die App legt es nach ihren eigenen Regeln an und überschreibt nie, was
   ein Mensch angelegt hat. Die Plattform schreibt nie die Daten einer
   App selbst.
3. **Chat zum KI-Gateway ohne Schlüssel** (D3): wie heute zum
   MCP-Gateway, über eine Tür der Plattform mit Zusicherung. Im
   KI-Gateway steht statt eines Schlüssels ein Eintrag „Instanz `chat`
   darf diese Modellnamen bis gelb“. Das Geheimnis, das bisher jemand vom
   KI-Gateway in die Destination `ki` kopierte, entfällt. `ki` bleibt
   für ein Gateway außerhalb des Mandanten und gewinnt, wenn es
   zugeordnet ist.
4. **Inhalt** (D4): Hilfe, MCP-Gateway, KI-Gateway, Chat, Vorgänge;
   keine Test-Instanzen.
5. **Modelle** (D5): ein eigenes KI-Gateway je Mandant; den Schlüssel des
   Anbieters trägt ein Mensch ein.
6. **Rechte** (D6): alle Personen `assistant_user`, die Verwaltung
   `assistant_keyuser`, aus den Vorlagen. Wie „alle Personen“ heute
   ausgedrückt wird, prüft Stufe 1.
7. **Erster Assistent** (D7): „Hilfe“ für den ganzen Mandanten, angelegt
   im MCP-Gateway.
8. **Erster Mandant:** `kit1` auf `oaapx01`.

**Das Profil `ki-arbeitsplatz`** hält nur zweimal an: für die
Zugangsdaten des Anbieters und für die erste Verwaltung.

**Stufen:**

1. `destination.ensure` und Profil Version 1, noch mit Haltepunkten für
   alles in den Apps. **Gebaut am 19.11.** (Referenz 0.1.314, §11), lokal
   getestet, noch nicht an einem Knoten. §7 ist geklärt: Ein Assistent
   „für den Mandanten“ ist schon für alle sichtbar und nur von der
   Verwaltung pflegbar; das Profil braucht dafür keinen Rechte-Schritt.
2. Einrichtungstüren, Tür vom Chat zum KI-Gateway, Profil Version 2 mit
   nur noch zwei Haltepunkten; Köder 1–8 halten.
3. Profil auf `oaapx01`, `kit1` aus dem Portal aufbauen, als Person
   ausprobieren. Ausrollen und Pushen wie immer nur auf Jörgs Wort.

**Offen, für die Stufen nicht nötig:** Volumen je Person im KI-Gateway
(O1, wird bewusst nicht aufgezeichnet), Test-Instanzen im Profil (O2),
ein Profil mit Realm und Anmeldung der Person am MCP-Gateway (O3).
