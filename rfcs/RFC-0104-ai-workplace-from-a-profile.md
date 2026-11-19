# RFC-0104: An AI Workplace From a Tenant Profile — Destinations, Setup Doors, and a Chat That Reaches Its Model Gateway Without a Key

- **Status:** **Accepted (2026-11-19)** — Jörg: "Alles wie empfohlen,
  Kürzel kit1, schreib das RFC", after going through the points in
  conversation. D1–D7 decided as recommended. **Stage 1 built**
  (reference 0.1.314, profile `ki-arbeitsplatz` 1.0.0, not pushed), §11.
  **Stage 2 built** (reference 0.1.315, mcp-gateway 0.27.0, ai-gateway
  0.10.0, help 0.7.0, chat 0.16.0, profile 2.0.0, not pushed), §12.
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
  path: /oaap/setup        # a local path under one of the app's routes
```

- **What the instance gets:** `OAAP_SETUP_KEY`, a random value the
  platform makes at install and keeps in the instance's environment
  (like the other platform-owned variables, 2.8). It never leaves the
  platform: no page shows it, no profile names it.
- **The node calls the instance** through the gateway's internal
  listener (`gateway:8099/s/<instance>` → the declared path), which
  answers the platform network only, never through a public route. The
  call is made from inside the identity container, with the body on
  standard input, so the key appears in no process list.
- **Who is asking (changed while building stage 2):** the call carries
  `Authorization: Bearer <OAAP_SETUP_KEY>` and `X-OAAP-Setup-Actor:
  <who started the build>` (for the app's own audit). The first draft
  said: an assertion of the platform with a claim `oaap/setup`. But an
  app cannot check the platform's assertion — it is an HMAC with a key
  only platform services hold, and apps trust the headers the platform
  sets instead (that is how procedure A works). A per-instance key the
  platform alone holds gives the same two locks: from outside the path
  lies behind the app's route, and without the key nobody passes, a
  `tenant_admin` included. An app ignores every identity header on its
  setup path. Without `OAAP_SETUP_KEY` in its environment it refuses
  every call.
- **Calls:**
  - `GET <path>` → `{"v": 1, "kinds": [...]}`: what the app can set up.
  - `GET <path>?kind=<k>&id=<id>` → `{"v": 1, "kind", "id", "state":
    "present" | "absent", "ready": true | false, "note"}`. `ready` is
    what the read `setup.ready` (§5) asks.
  - `POST <path>` with `{"v": 1, "dry": false, "items": [{"kind": …,
    "id": …, …}]}` — the wished state, item after item.
  - `POST <path>` with `{"v": 1, "remove": [{"kind": …, "id": …}]}` —
    the undo.
  - The answer is `200` with `{"v": 1, "results": [{"kind", "id",
    "result", "note"}]}`, one per item, in order; `400` for a malformed
    body; `403` without the key.
- **The result per item:** `present` (already as wished), `made`
  (created now), `would_make` (with `dry`), `conflict` (something of that
  id exists and differs; the note says what), `refused` (the app does
  not allow it; the note says why), and for `remove`: `removed` or
  `gone`. The app never overwrites what a human made: a difference is a
  conflict, and the build stops there.
- **No secrets:** an item with a field `key`, `token`, `secret`,
  `password` or `credentials` is `refused`.
- **Idempotent.** The same POST twice gives `made` then `present`.
  `app.setup`'s check is the same POST with `"dry": true`.
- **What the app remembers:** for each item it made, who (the actor),
  when, and a digest of the wished item. `remove` removes an item only
  while it is still as setup made it; one a human changed since is a
  `conflict` and stays.

### 3.2 The step type

| Type | Do | Check | Undo |
|---|---|---|---|
| `app.setup` | POST the step's `items` to the instance's setup door | the same POST with `dry: true` answers `present` for every item | `remove` for the items this build made (§3.1) |

### 3.3 What each app offers

- **`mcp-gateway`:**
  - `{"kind": "refresh", "id": <server>}` — read the platform sources
    now (what „Quellen jetzt einlesen“ does), then the server's catalog
    through the discovery door (no person needed). `present` when the
    server exists and its catalog has tools; never a conflict; nothing
    to remove.
  - `{"kind": "server_light", "id": <server>, "light": "green" |
    "yellow" | "red"}` — a server's light. Setup may change it only from
    the `red` every new server starts with; another light set by a human
    is a conflict.
  - `{"kind": "view", "id": <name>, "accesses": ["platform", …],
    "tools": {"server": <s>, "effect": "read"}}` — a view; `tools` may
    instead be a list of `{"server", "tool"}`.
  - `{"kind": "profile", "id": <label>, "group": "@<chat>", "views":
    [...], "ceiling": "yellow"}` — an access profile.
  - `{"kind": "assistant", "id": <id>, "title", "view", "gateway",
    "model", "greeting", "visibility": "tenant"}` — an assistant, first
    revision `@1` (RFC-0097).
- **`ai-gateway`:**
  - `{"kind": "supplier", "id": <name>, "url": "https://…/v1", "light"}`
    — a supplier **without** credentials; a human types those on the
    gateway's page. `ready` is true when credentials are stored and the
    supplier's test answers.
  - `{"kind": "alias", "id": <model name>, "supplier": <name>, "model":
    <the supplier's model id>}` — a model name.
  - `{"kind": "client", "id": <chat instance>, "aliases": [...],
    "ceiling": "yellow", "personal_data": false}` — the grant of §4.
- **`help`:** `{"kind": "fetch", "id": "docs"}` — fetch the
  documentation now (what „Jetzt holen“ does). `present` when documents
  from `docs-origin` are there.
- **`chat`:** nothing in this RFC. Its assistants come from the MCP
  gateway, its model gateway from §4.

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
- **What the chat sends:** to `<via>/chat/completions` and
  `<via>/models`, `Authorization: Bearer <OAAP_AI_CLIENT_KEY>` and
  `X-OAAP-Act-Assertion: <the X-OAAP-User-Assertion it received for this
  person's request>` — exactly what it sends at an MCP via door.
- **What the model gateway gets:** `X-OAAP-AI-Client`, `X-OAAP-User-Id`
  and `X-OAAP-User-Assertion`, set by the platform; never the chat's key.
  Only all three together count as a call through the door (the
  platform strips the two identity headers on the gateway's public
  `/v1`), as for the MCP gateway's procedure A.
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

- `destination.secret` (`destination`, `instance`) — the destination has a
  secret. Never its value.
- `setup.ready` (`instance`, `kind`, `item`; `item` because `id` is the
  step's own id) — the instance's setup door
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
  2. `app.install` from the store: `help` as `hilfe`, `mcp-gateway` as
     `werkzeuge`, `ai-gateway` as `modelle`, `chat` as `chat`,
     `vorgaenge` as `vorgaenge`. No test instances (D4). Steps name an
     instance by its name inside the tenant; the platform makes the node
     key `{label}-hilfe` and so on. The apps know each other only by
     that key (source list, `X-OAAP-AI-Client`, `X-OAAP-MCP-Client`,
     gateway list), so the ids in setup items below are keys. Profile
     2.0.0 named the instances `{label}-hilfe` and got keys
     `{label}-{label}-hilfe`; `refresh` then found no server (measured
     with kit1 on oaapx01, 2026-11-19), fixed in 2.1.0.
  3. `app.config` `modelle` `AIGW_MASTER_KEY` `generate: true`.
  4. `destination.ensure` `docs-origin` → `hilfe`, target
     `https://codeload.github.com/MDJoerg/oaap-docs`, auth `none`;
     `app.setup` `hilfe` `fetch`.
  5. `app.setup` `modelle` `supplier`.
  6. `manual` „Zugangsdaten der Bezugsquelle eintragen“, `done_when`
     `setup.ready` (D5: an own model gateway per tenant; the key of the
     customer is typed by a human).
  7. `app.setup` `modelle`: `alias` `standard` → `{model}`;
     `client` for `{label}-chat` with `standard`, ceiling `yellow`.
  8. `app.setup` `werkzeuge`: `refresh` for `{label}-hilfe`;
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
2. The setup door accepts only its own instance's setup key (§3.1).
   Bait: a POST with a person's identity headers (`tenant_admin`) and no
   key → refused; with the setup key of another instance → refused.
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

## 12. Stage 2, built (2026-11-19)

Reference 0.1.315 (`oaap.apps.runtime` 0.2.72, `oaap.core.identity`
0.6.10), mcp-gateway 0.27.0, ai-gateway 0.10.0, help 0.7.0, chat 0.16.0,
profile `ki-arbeitsplatz` 2.0.0.

- **Built, platform:**
  - Manifest 0.18: `setup.path`, `ai_client.use`, `ai_gateway.serve`.
  - `OAAP_SETUP_KEY` per instance with `setup`; the internal listener's
    `handle /s/<name>`; `setup_call` from inside the identity container
    with key and body on standard input.
  - Step type `app.setup` (check = dry POST, do = POST, `made` items
    `setup:<instance>:<kind>:<id>`, undo = `remove`; an item a human
    changed since answers `conflict` and stays, the rollback goes on) and
    the read `setup.ready`. The profile refuses secret-named fields in
    items, unknown parameters and empty lists; parameters fill text,
    lists and objects inside items.
  - The via machinery of RFC-0074 is now one set of functions with two
    kinds (`mcp`, `ai`); identity's via check takes both prefixes, audit
    word `ai.via`. `OAAP_AI_CLIENT_KEY` follows the instance like the MCP
    client key.
- **Built, apps (by three helpers working in parallel on one contract,
  §3.1, then checked here):**
  - mcp-gateway: setup door with `refresh`, `server_light`, `view`,
    `profile`, `assistant`, all through the functions the operator pages
    use.
  - ai-gateway: setup door with `supplier`, `alias`, `client`; the client
    grant is a `keys` row of kind `client` that no bearer value can ever
    find; a call through the door counts only with all three headers;
    usage rows carry the grant, never the person (O1).
  - help: setup door with `fetch` (the same call as „Jetzt holen“); a new
    route `/oaap` with role `admin`.
  - chat: `ai_client`; the order of §4 (`ki` wins, else the one gateway,
    else `CHAT_AI_GATEWAY`); „Einrichtung prüfen“ names the way and says
    „im KI-Gateway fehlt die Freigabe für diesen Chat“ on a 403.
- **Profile version 2:** two human steps left (first administrator,
  supplier credentials, the latter with `setup.ready`); `ki_url` and the
  destination `ki` are gone. New: `CHAT_DEFAULT_LIGHT` is set to the
  supplier's light, because a green conversation could not use a yellow
  supplier such as Anthropic.
- **Changed while building:**
  - The setup call is authorised by `OAAP_SETUP_KEY`, not by an assertion
    with a claim (§3.1 says why: apps cannot check the platform's
    assertion).
  - `setup.ready` names the item `item`, not `id`.
- **Decided by the apps where §3 left room** (all within the contract):
  - mcp-gateway stops a real POST at the first conflict and answers the
    rest `refused` („nicht ausgeführt“); ai-gateway and help answer every
    item. The build stops either way.
  - An undone profile label or assistant cannot be made again under the
    same id (the gateway's ledger keeps revoked labels and revisions);
    a second build after a rollback needs other ids or a fresh instance.
  - An undone supplier with credentials a human entered stays.
  - A failed help fetch answers `refused` with the reason.
  - A grant that has usage is revoked, not deleted.
- **Measured locally (no full reference suite; Docker was not running,
  so no Linux runner):**
  - Reference: `test_ai_via_setup.py` 51/51 (new: manifest 0.18, the
    chat's site with list and door, bait 8, the internal listener,
    identity with both credentials (bait 4) and `ai.via`, `app.setup`
    and `setup.ready`, the key only on stdin, bait 1 in a profile);
    `test_mcp_via`, `test_instance_keys` (with the new key), and 24
    further tests of builds, destinations, profiles, doors and manifests
    pass. `test_mail_node` fails with or without this change (file mode
    0600 on Windows).
  - Apps: mcp-gateway `test_setup.py` 48/48 (baits 2, 3), test_gateway
    548/548 (one known race on the first run); ai-gateway `test_setup.py`
    97/97 (baits 2, 3, 5, 6, 7), its six other tests unchanged green;
    help `test_setup.py` 27/27 and its three other tests; chat
    `test_chat.py` 213/213, `test_markdown.js` 27/27; `check-store.py`
    and `check-shared.py` clean.
  - Profile version 2 passes the profile and the upload check.
- **Not measured:** anything on a node — no build of `kit1`, no real
  call through the internal listener or the new door, no supplier.
  That is stage 3.

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
   nur noch zwei Haltepunkten; Köder 1–8 halten. **Gebaut am 19.11.**
   (Referenz 0.1.315, mcp-gateway 0.27.0, ai-gateway 0.10.0, help 0.7.0,
   chat 0.16.0, §12), lokal getestet. Geändert beim Bauen: Der
   Einrichtungsaufruf weist sich mit einem Schlüssel je Instanz aus,
   den nur die Plattform kennt, statt mit einer Zusicherung — Apps
   können die Zusicherung der Plattform nicht prüfen.
3. Profil auf `oaapx01`, `kit1` aus dem Portal aufbauen, als Person
   ausprobieren. Ausrollen und Pushen wie immer nur auf Jörgs Wort.

**Offen, für die Stufen nicht nötig:** Volumen je Person im KI-Gateway
(O1, wird bewusst nicht aufgezeichnet), Test-Instanzen im Profil (O2),
ein Profil mit Realm und Anmeldung der Person am MCP-Gateway (O3).
