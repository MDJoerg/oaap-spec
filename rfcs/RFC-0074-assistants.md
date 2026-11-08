# RFC-0074: Assistants — A View, a Prompt and a Model Meaning, Running With the Rights of the Person Who Speaks

- **Status:** **Accepted (2026-11-08)** — Jörg: "D1-D7 wie empfohlen"; **stage 1
  built and measured on `oaap-test` (2026-11-08, 24/24, §9)**; **stage 2 built
  and measured (2026-11-08, 23/23, §10)**; **stage 3 built and measured
  (2026-11-08, 26/26, §11)**
- **Date:** 2026-11-08
- **Authors:** Jörg (direction: I-41 of 2026-11-05 — "a chat is an app",
  "an assistant carries no rights", the name "Assistent"), Claude (facts read
  in specs and reference code, design)
- **Depends on:** RFC-0065 (MCP gateway; views, procedures), RFC-0073 (apps as
  MCP sources, procedure I), RFC-0066 and `oaap.core.identity` §2.11 (the
  signed person), RFC-0067 (agents as principals), RFC-0045 (business
  authorization, contexts), RFC-0064 (AI gateway, model names), RFC-0068
  (closed egress), RFC-0057 (a database per app)
- **Changes (when accepted):** new spec `oaap.ai.assistants` 0.1;
  `oaap.core.identity` (procedure I accepts the platform's own assertion as
  act credential); `oaap.ai.mcp-gateway` (a person arriving through the
  platform); manifest (`mcp_client:`)
- **Driver:** I-41, step 3. Steps 1 (gateway against Keycloak) and 2 (apps as
  MCP sources, RFC-0073) are done. The chat app of step 4 needs two things
  that do not exist: a **definition** of what an assistant is, and a **way for
  the chat to act as the person** toward the MCP gateway. The second is the
  harder one: the portal session carries no token the gateway accepts.

## Summary

An **assistant** is four things and nothing else: a **view** of the MCP gateway
(which tools), a **system prompt** with a greeting, a **model meaning** (a
model name of the AI gateway, which the tenant maps), and a **visibility**
(private, a context, the tenant). It holds no key and no role. When someone
talks to it, every tool call runs **as that person**: the view limits which
tools, the app behind the tool limits which data, with `may()` as today.

The chat app already receives, on every request of a signed-in person, the
platform's **signed assertion** about that person (`X-OAAP-User-Assertion`,
5 minutes, addressed to the chat instance). This RFC proposes that the chat
**copies it** to a door on its own site, the platform checks it, and the MCP
gateway receives the person exactly as an app does. Downstream, procedure I
of RFC-0073 accepts the platform's own assertion where it accepts a Keycloak
token today. **No Keycloak is needed for the chat**, which matters because
most tenants have none.

## 1. Facts (read 2026-11-08; measured where noted)

| Claim | Where |
|---|---|
| Verify adds `X-OAAP-User-Assertion` for a person (`kind: human`) and a named instance: `sub`, `usr`, `ten`, `aud` = instance, 5 minutes, HMAC-SHA256 with the node's assertion key; apps copy it, never parse it | `oaap.core.identity` §2.11 |
| Only platform services hold the assertion key; without it the header is empty | same |
| The MCP gateway accepts a Keycloak token (issuer, audience, expiry, RS256) or a view key; **measured 14/14** against the real Keycloak on `oaap-test` | RFC-0065 §15, CURRENT_STATE 422 |
| Procedure I: the gateway exchanges the person's token at Keycloak for one addressed to the platform client; identity checks it and produces the six headers for the target app; **measured** | RFC-0073 §4, §13 |
| Procedure P (SAP) builds the credential from the person and `sap_user` at the platform, not from a provider token | RFC-0066 |
| A tenant's instances start no connection of their own; instance-to-instance traffic goes through doors of the platform | RFC-0068 |
| The AI gateway passes the request body unchanged except `model` (alias → model of the source), so `tools` reach the model as sent | `ai-gateway/app.py` (read 2026-11-08) |
| An app reaches the AI gateway through a **destination** (the key stays on the platform; under closed egress only a key with ceiling `green`) or, in an open tenant, an app link; **measured** with a local model on `oaap-test` | RFC-0068 stage 3, `oaap.apps.runtime` 0.2.48 |

## 2. The assistant (`oaap.ai.assistants` 0.1)

```yaml
id: reklamationen            # [a-z0-9-], unique per chat instance
title: Reklamationen
greeting: "Ich helfe bei Reklamationen. Frag nach einem Vorgang oder einem Kunden."
system: |
  Du bist der Assistent eines kleinen Handwerksbetriebs …
model: standard              # a model NAME of the AI gateway, never a model
view: reklamation            # a view of the tenant's MCP gateway
visibility: {scope: context, context: {team: service}}   # private | context | tenant
owner: <person id>
commands: true               # the view's MCP prompts appear as /commands
```

- **No rights.** No key, no role, no `on_behalf_of`. An assistant cannot do
  anything its speaker cannot, and cannot do anything outside its view.
  Effective = view ∩ the person's rights in the app.
- **Model as meaning (D3).** `model` is a name of the AI gateway (RFC-0064
  stage 2). The tenant decides what `standard` means. The default rule is
  **local first**: a new tenant's `standard` points to the node's Ollama. Whether
  that is good enough is what measurement §6 is for.
- **Visibility (D4)** via RFC-0045: *private* = only the owner; *context* =
  everyone with an assignment in that context, created by a key user of that
  context; *tenant* = everyone, created by a `tenant_admin`.
- **Where it lives (D2):** in the chat app's data, in the format of this spec,
  so a second chat app can import it. The platform stores no assistants.
- **Writing tools (D6):** a tool whose effect class writes is shown to the
  person and runs only after they confirm, in the chat, every time. A view may
  forbid writing tools for an assistant altogether.

## 3. The core question: how the chat acts as the person

### 3.1 Options

| | How | For | Against |
|---|---|---|---|
| **K — Keycloak client** | the chat is an OIDC client of the tenant's realm; the person signs in once more (silently under SSO), the chat holds an access and a refresh token for the gateway | standard OAuth; the same path as Claude Code; procedure X works | only tenants with a provider; the chat stores a **refresh token** (hours of power over the person); a second sign-in flow in every chat app |
| **A — the platform's assertion** (proposed) | the chat copies the assertion it already receives; the platform checks it at a door and carries the person to the gateway | every tenant, with or without Keycloak; nothing stored; 5 minutes; the platform checks its own signature | procedure X impossible on this path (no provider token); the 5 minutes bind the length of one step (§3.3) |
| **N — the chat names the person** | header with a user id | trivial | refused in RFC-0067 D3 and RFC-0073 §4.2: the app could name anybody |

### 3.2 Procedure A, the way

```text
browser ──session──▶ chat instance C        (verify: six headers, assertion aud=C)
chat C ──POST /platform/mcp/via/<view>/   (C's own site)
          Authorization: Bearer <C's client key>
          X-OAAP-Act-Assertion: <the assertion C received, copied>
     platform gateway → identity /verify
          key limited to oaap.mcp.client:<C>?  assertion signature, aud = C, not expired?
          person human, active, of C's tenant?  C declares mcp_client:?
          ◀── six headers of the PERSON, assertion aud = G
     platform gateway ──▶ MCP gateway G of the tenant, view <view>
G ── for an OAAP app source: procedure I with the assertion (aud = G) as act credential
G ── for SAP: procedure P as today (person and sap_user from the platform)
G ── for an external resource server: procedure X impossible → the tool is refused
```

- **The same rule as RFC-0073 §4.2:** a credential addressed to C is never
  used at G. C presents its assertion; the platform answers G with a new one
  addressed to G.
- **The MCP gateway trusts the six headers** on this door like every app
  trusts them; the gateway strips client-sent identity headers as always. G
  records procedure `A`, `user_sub`, and the assistant's id when C sends one
  (`X-OAAP-Assistant`, informational only, never a right).
- **Procedure I gains one input:** besides a Keycloak token exchanged for the
  platform client, identity accepts its own assertion with `aud` = the calling
  gateway. That is a token addressed to itself, checked with its own key — the
  same reasoning as RFC-0073 §4.2, without the round trip to Keycloak.

### 3.3 The five minutes (D5)

A person's message can need several model turns and tool calls. Measured on
`oaap-demo` (§6), one round of a local 7–8B model on a four-core CPU takes
5–30 s with thinking off and up to 12 minutes with thinking on. The proposal: **the browser drives the loop.** Each round
(model turn → tool call → result) is one request from the browser to the chat,
so every round carries a fresh assertion. The chat streams the round's state
back and the page asks for the next round. A round longer than five minutes
fails with a sentence, never with a silent retry under an old assertion. The
assertion is not lengthened for chats.

### 3.4 What this does and does not prove

As RFC-0073 §4.3: the platform proves that this person had a session at C
within the last five minutes. It does not prove that they wanted *this* tool
call. The counterweights are the view (default deny), the confirmation of
writing tools (D6), and the gateway's record.

## 4. Not part of this RFC

- The chat app itself (I-41 step 4), its history store (RFC-0057 stage 1 or a
  file in the app as interim), mobile view, forms, attachments, speech.
- Procedure X from the chat. A later RFC can add option K as a second way for
  tenants with a provider; the assistant format does not change.
- Agents. An agent has its own principal and key (RFC-0067 §4, RFC-0073 §6),
  not an assistant.
- OpenAPI as tools (I-39).

## 5. Security requirements (proposed)

1. The act assertion is accepted only at the door on C's own site, with C's
   client key, and only with `aud` = C.
2. No fallback: a missing, expired or foreign assertion is 401, never the
   chat's own principal.
3. C never stores an assertion beyond the request that brought it.
4. A person without `kind: human` (machine principal, API key) has no
   assertion and cannot use procedure A.
5. The assistant's id is information for logs; no decision depends on it.
6. Writing tools: confirmation per call in the chat (D6); the gateway records
   whether a call was confirmed.

## 6. Measurement: do local models call tools? (I-41 step 3a)

**Measured 2026-11-08.** Script:
`oaap-lab/ki-werkzeug-messung/messung_werkzeuge.py`. Node `oaap-demo`
(i5-6500T, 4 cores, 31 GB, no GPU), Ollama 0.32.6 of the OAAP instance, OpenAI
endpoint `/v1/chat/completions` (the one the AI gateway relays), five tools in
German, temperature 0.2. Eight cases, each twice (16 per model): simple call
(A1), choice among five tools (A2), enum value from "dringend" (A3), relative
date (A4), two messages that need no tool (B1 "Danke, schönen Sonntag", B2 a
knowledge question), a missing required argument that must be asked for (C1),
and a second turn that must use the tool result (D1).

| Model | Thinking | Correct | Seconds per round¹ | Fails |
|---|---|---|---|---|
| `qwen3:8b` | off² | 14/16 | 4–28 | C1: invents a time |
| `qwen2.5:7b` | — | 14/16 | 6–24 | C1: invents a time |
| `qwen3:4b-instruct` | — | 14/16 | 2–16 | C1: invents a time |
| `qwen3:8b` | on | **16/16** | 40–127 | — |
| `qwen3:4b` | on (cannot be switched off) | **16/16** | 27–**707** | — |
| `llama3.1:8b` | — | 10/16 | 5–23 | **B1: creates a ticket on "thank you"**, B2 searches documents, C1 |
| `llama3.2:3b` | — | 6/16 | 3–19 | B1, B2, A3 "dringend" outside the enum, A4 date format, C1 |

¹ After the first call of a model, which needs another 20–40 s to read the
prompt. ² `"reasoning": {"effort": "none"}`; see finding 5.

Findings:

1. **Local first holds for tool use.** Three models call the right tool with
   the right arguments, stay silent where no tool is needed and use the result,
   at 5–30 s per round on a four-core CPU without a GPU. Recommendation for
   `standard` on such a node: `qwen3:8b` with thinking off, `qwen2.5:7b` as
   the fallback.
2. **Without thinking, every model invents a missing argument** (C1: 09:00,
   10:00, 14:00). Only the thinking models ask back. This makes D6 a
   necessity, not a courtesy: the person sees the arguments of a writing tool
   before it runs.
3. **Thinking does not fit the five minutes on a CPU.** Up to 2,800 thinking
   tokens at about four tokens per second: one round took 12 minutes. D7 holds
   only with thinking off on such nodes; thinking belongs on a GPU.
4. **Small models are not a source of knowledge.** Asked what "z. Hd." means,
   only `qwen3:8b` without thinking was right ("zu Händen"); the others
   answered with confidence: "zur Hand", "zu hinterlegen", "zum Händler". The
   value comes from the tools; an assistant's system prompt should say so.
5. **The thinking switch is model-specific and the gateway cannot set it.**
   Ollama 0.32.6 on `/v1` ignores `reasoning_effort: "none"` silently and
   `think: false` as well; `reasoning: {effort: "none"}` works for `qwen3:8b`,
   while `qwen3:4b` (the newer thinking-only build) moves its thinking into the
   answer text instead. A model *meaning* therefore has to carry fields beyond
   the model name — today an AI-gateway alias maps only the name (open point
   for RFC-0064).
6. **The llama models are excluded.** Creating a ticket because someone said
   thank you is the one failure an assistant must not have.

**Through the AI gateway (measured 2026-11-08, `aigw-test` 0.5.0 on
`oaap-test`, key with ceiling `green`, alias `lokal` → `qwen2.5:0.5b`):** without
a key `/v1/models` answers 403; with it, one alias, green. All eight cases ran
through the gateway: `tools` reach the model, `tool_calls` come back
structured, and the second turn with a `role: tool` message passes (D1
correct). The model itself is far too small (2 of 8); `oaap-test` has 7 GB of
memory and cannot hold an 8B model, so the same-model comparison stays open and
is not needed for the claim: the gateway passes tool calls through.

## 7. Stages

1. `oaap.ai.assistants` 0.1 and procedure A in identity and the gateway;
   measured with a test page instead of a chat.
2. Chat app, first version (I-41 step 4): one assistant, one app's tools,
   local model, history in a file.
3. Visibility by context, `/commands`, confirmation of writing tools.

## 8. Decisions

| # | Proposal | Recommendation |
|---|---|---|
| **D1** | An assistant = view + system prompt/greeting + model name + visibility; **no rights** | yes |
| **D2** | Assistants live in the chat app's data, in the format of `oaap.ai.assistants`; the platform stores none | yes |
| **D3** | `model` is an AI-gateway name; the tenant maps it; default rule local first (§6: `qwen3:8b` without thinking on a CPU node) | yes |
| **D4** | Visibility private / context (key user) / tenant (`tenant_admin`) via RFC-0045 | yes |
| **D5** | The chat acts as the person by **procedure A** (copied platform assertion at a door on its own site); Keycloak option K later and optional | yes |
| **D6** | Writing tools only after confirmation in the chat, per call | yes |
| **D7** | The browser drives the tool loop; the assertion stays at five minutes (§6: holds with thinking off on a CPU node) | yes |

**Decided (Jörg, 2026-11-08):** D1–D7 as recommended.

## 9. Stage 1 as built (2026-11-08)

Built in reference 0.1.243, `mcp-gateway` 0.7.0 and the test page
`oaap-lab/assistent-probe` 0.1.0; specs `oaap.ai.assistants` 0.1,
`oaap.core.identity` 0.6.4 (2.12, 2.13), `oaap.apps.runtime` 0.2.56 (2.32.3,
manifest 0.12), `oaap.ai.mcp-gateway` 0.7 (§3.9).

**Settled while building** (left open by §3.2):

- **The door names the gateway:** `/platform/mcp/via/<gateway>/<view>` on the
  chat's own site, rewritten to `/mcp/<view>`. A tenant may have several
  gateways; the sketch `/platform/mcp/via/<view>/` could not say which.
- **The chat learns its gateways** from a list on its own site,
  `/platform/mcp/gateways`, written by the generator like the sources list
  of RFC-0073 — gateways are the instances of the tenant declaring
  `mcp_sources`.
- **The gateway learns the chat** from `X-OAAP-MCP-Client`, set by the door
  and never taken from the request. Procedure A at the gateway needs this
  header, the person's id and the assertion together; on the gateway's public
  `/mcp` the platform strips the identity headers, so the three can only
  arrive together through a via door.
- **Who pays at the gateway:** an access profile naming `@<chat>` or `@*`.
  A `*` profile (made for sign-ins) does not admit persons from a chat.
  A view needs the way `platform`; ways are now a list of `key`, `signin`,
  `platform`.
- **Procedure I's second credential** is `X-OAAP-Act-Assertion` (aud = the
  gateway); act token and act assertion together are refused.

**Measured on `oaap-test`** (`assistent-probe/messung_stufe1.py`, result in
`ergebnis-2026-11-08.txt`), over the public https names as a browser:

| | Result |
|---|---|
| anna signs in at the test page through the tenant's Keycloak; the page has her assertion, is an MCP client, the assistant is valid, the list names `vuebung-mcpgw` | pass |
| rounds through the via door, each its own request: `initialize`, `tools/list` (three tools of view `kp-i`), `list_projects` → only pA, `list_entries pB` → „Kein solches Projekt.“, `add_entry pA` written and read back | pass, 0.24–0.67 s per round (no model) |
| bert through the same page and view sees only pB; with anna's session id the gateway does not know the session | pass |
| gateway usage: procedure `A`, anna's id, issuer `platform`, chat `vuebung-aprobe`, assistant `reklamationen`, the profile's cost centre | pass |
| identity audit: `mcp.via` (gateway, chat, anna, `(A)`) and `mcp.act` to the source with `(A)`; no assertion in the log | pass |
| forged headers (chat, id, assertion) from outside at the gateway's `/mcp`: `401` | pass |
| via door with the page's key but no assertion, with a forged one, or an assertion without key: `401` | pass |
| the page's key at a **source's** door (procedure I): `403` | pass |
| without a session at the page: no round (redirect to sign-in) | pass |

24/24. Regression: RFC-0073's TLS measurement (procedure I with Claude Code's
sign-in at the same view `kp-i`) 15/15 after the change; unit tests
`test_mcp_via.py` 70 checks (with two counter-tests, red when a check or the
client header is removed), `test_gateway.py` 239.

**Not in stage 1:** a model, the chat app, visibility by context, `/commands`,
confirmation of writing tools (stage 2–3). The assistant's `gateway` field is
an addition to §2 (optional; required when a tenant has several gateways).

## 10. Stage 2 as built (2026-11-08)

The chat app `oaap-apps/apps/chat` 0.1.0 (standard library only): one
assistant from `CHAT_ASSISTANT`, the tools of one view, a model through a
destination `ki` on an AI gateway (the key stays on the platform), history as
one JSON file per conversation under `/data/people/<person id>/`, readable
only by that person. `mcp-gateway` 0.7.1 adds to every tool in `tools/list`
`"_meta": {"oaap/effect": "<class>"}` — the class the operator set in the
view (spec 0.7.1, §5.2).

**Settled while building:**

- **Order inside a round:** pending tool calls first, then the model turn.
  Tool calls need the person's assertion, which is freshest at the start of a
  request; the model turn needs none and may take long. A slow model never
  ages the assertion a tool is called with. The browser asks for the next
  round while the model wants tools (D7).
- **D6 moved into stage 2.** §6 finding 2 made confirmation a necessity, and
  view `kp-i` has a writing tool. Every tool whose class is not `read` is shown
  with its arguments and runs only after *Ausführen*; *Ablehnen* tells the
  model "Abgelehnt …" and changes nothing. Only the gateway makes a tool
  `read`; without its `_meta`, a tool counts as `write`, and the maker's
  `readOnlyHint` never counts. Recording the confirmation at the gateway
  (§5.6) stays in stage 3.
- At most six model turns per message; a tool the view does not have, or
  arguments that are not JSON, become an error result without a call.

**Measured on `oaap-test`** (`assistent-probe/messung_stufe2.py`, result
`ergebnis-stufe2-2026-11-08.txt`), over the public names as a browser, with a
real local model: AI gateway `aigw-test`, name `standard` →
`qwen3:4b-instruct` on the node's Ollama (4 vCPU, 7 GB, no GPU), key
`chat-vuebung` green, personal data allowed.

| | Result |
|---|---|
| anna signs in at the chat through Keycloak; assistant, view, model, MCP client, destination present | pass |
| "Welche Projekte habe ich?" → `list_projects` as anna without asking, answer names her project „Amsel“ (pA), not pB | pass |
| pB entries, fresh conversation → `list_entries pB` → the app: „Kein solches Projekt.“ | pass |
| write in pA → confirmation card `add_entry {project: pA, text: …}`, class `write`; refused: nothing written; second try confirmed: the entry is in pA **exactly once** | pass |
| "Lege einen Eintrag an." (no project, no text) → the model asks back: „Für welches Projekt …?“ | pass |
| bert in the same chat with the same assistant sees pB („Bussard“), not pA, and not anna's conversations (404) | pass |
| MCP gateway: procedure A, issuer `platform`, chat `vuebung-chat`, assistant `projekte`, cost centre `CHAT-1` | pass |
| AI gateway: every model turn at key `chat-vuebung`, model `qwen3:4b-instruct` | pass |
| history and log of the chat: no assertion, no key; a round without a session: none | pass |

23/23. Rounds 0.1–38 s, model turns 2.3–38 s, all far below five minutes.
Unit tests `test_chat.py` 37 (six deliberate faults each turned them red),
`test_gateway.py` 241.

**Findings:**

1. **The model answers from what it saw earlier.** Asked about pB right after
   listing anna's projects, `qwen3:4b-instruct` said "Projekt pB existiert
   nicht." without calling a tool — true for anna, nothing invented, but the
   app's check did not run. In a fresh conversation it called the tool. The
   rights still hold (the model only knows what anna's calls returned); what
   the history does is make answers *stale*, not wider.
2. **With a small instruct model, the asking back worked** (C1 of §6 failed
   for `qwen3:4b-instruct` with a different prompt). The system prompt says
   "frag nach, statt zu raten"; one run is no proof — the confirmation card
   remains the guarantee.
3. **The answer uses the app's titles** ("Projekt Amsel"), not ids; a check
   on ids alone would have failed a correct answer.

## 11. Stage 3 as built (2026-11-08)

Chat 0.2.0, `mcp-gateway` 0.7.2, `kontext-probe` 0.1.5 (one prompt);
specs `oaap.ai.assistants` 0.2, `oaap.ai.mcp-gateway` 0.7.2.

- **Assistants in the chat's data** (`/data/assistants.json`, the exchange
  format; D2), created, edited, deleted, exported and imported in the chat.
  Import is all or nothing. One assistant may come from configuration
  (`CHAT_ASSISTANT`); nobody changes that one in the chat.
- **Visibility (D4)** through the chat's authorization object `assistant`
  (`use`, `manage`, context field `team`) and `may()`; private = owner,
  tenant = everyone, created by `tenant_admin`. Checked at **every round**.
  Unreadable assignments: no team assistant (fail closed).
- **`/commands`:** the view's MCP prompts; `/name value` or
  `/name arg=value`; the prompt's text becomes the message.
- **§5.6:** a confirmed call carries `X-OAAP-Confirmed: yes`; the gateway's
  usage row has `confirmed`.

**Measured on `oaap-test`** (`assistent-probe/messung_stufe3.py`, result
`ergebnis-stufe3-2026-11-08.txt`), as a browser through Keycloak; anna holds
"assistant use+manage" in team service, bert "use" in team service, carl
nothing:

| | Result |
|---|---|
| anna creates a private assistant; only she sees it; bert can neither read it nor start a conversation with it (404) | pass |
| anna creates a team assistant for service: anna and bert see it, carl does not; anna not for team lager, bert not in service, anna not for the tenant (no `tenant_admin`), bert cannot change hers | pass |
| bert talks to the team assistant — as **bert** (pB, „Bussard“); the gateway records the assistant, procedure A, the chat | pass |
| anna writes after confirming: the gateway's usage row has `confirmed=yes`, read calls none — the header passes the platform's via door | pass |
| bert's assignment revoked: within 30 s the assistant is gone from his list, and his next round is refused (403); re-assigned afterwards | pass |
| export holds what anna manages (private and team, not the configured one); bert cannot import her file | pass |

26/26. Regression: stage 2 measurement 23/23 against chat 0.2.0. Unit tests:
`test_chat.py` 68 (twelve deliberate faults each turned them red — one,
"import all or nothing", only after a test with one allowed and one
forbidden assistant was added), `test_gateway.py` 245.

**Not measured on the node:** an assistant for the whole tenant created by
a `tenant_admin`, and `/commands` end to end. Both need a test person with a
platform role (`tenant_admin`, and `admin` for the gateway's page to put the
prompt into the view); the permission check of this session refused to grant
those roles. Both are covered by unit tests.

**Finding while building:** the gateway could read the catalog of a platform
source (procedure I) only with a token of a sign-in service — on the
operator's page not at all. A tenant without Keycloak, the case procedure A
is for, could never put its own apps' tools into a view. Fixed in 0.7.2:
the operator's page uses the operator's assertion, as procedure A does
(spec §3.7).

## Deutsche Zusammenfassung

**Worum es geht:** Schritt 3 der KI-Chat-Reihenfolge (I-41). Bevor die Chat-App
gebaut wird, braucht es zwei Dinge: eine **Festlegung, was ein Assistent ist**,
und einen **Weg, auf dem der Chat als die sprechende Person** beim MCP-Gateway
ankommt. Das Zweite ist die eigentliche Frage, denn die Portal-Sitzung trägt
kein Token, das das MCP-Gateway annimmt.

**Der Assistent (D1–D4, D6):** eine Sicht im MCP-Gateway (welche Werkzeuge),
ein Systemprompt mit Begrüßung, ein Modellname des KI-Gateways (der Mandant
legt fest, was „standard“ bedeutet, Standardregel: lokal zuerst) und eine
Sichtbarkeit (privat, Kontext, Mandant). **Er trägt keine Rechte.** Jeder
Werkzeugaufruf läuft als die Person, die gerade spricht: Die Sicht begrenzt die
Werkzeuge, die App dahinter begrenzt die Daten. Schreibende Werkzeuge laufen
nur nach Bestätigung im Chat. Gespeichert werden Assistenten in der Chat-App,
nicht in der Plattform.

**Die Token-Frage (D5, D7):** Jede App bekommt bei jeder Anfrage einer
angemeldeten Person schon heute eine **signierte Zusicherung der Plattform**
(`X-OAAP-User-Assertion`, fünf Minuten gültig, an genau diese Instanz
adressiert). Vorschlag **Verfahren A**: Der Chat reicht diese Zusicherung an
eine Tür auf seiner eigenen Seite weiter, die Plattform prüft ihre eigene
Unterschrift und gibt die Person ans MCP-Gateway weiter, wieder mit einer neuen
Zusicherung, diesmal ans Gateway adressiert. Von dort zu einer OAAP-App läuft
Verfahren I wie bisher, nur dass Identity statt eines Keycloak-Tokens auch die
eigene Zusicherung annimmt. **Keycloak wird für den Chat nicht gebraucht** —
wichtig, weil die meisten Mandanten keinen haben.

**Die Alternative** wäre, die Chat-App bei Keycloak als eigenen Client
anzumelden (wie Claude Code). Das geht nur bei Mandanten mit Keycloak, und der
Chat müsste ein Refresh-Token speichern, also stundenlang die Macht über die
Person halten. Bleibt als späterer, optionaler zweiter Weg (für Verfahren X).

**Die fünf Minuten:** Ein langsames lokales Modell braucht für eine Antwort mit
Werkzeugaufrufen womöglich länger. Darum treibt **der Browser die Schleife**:
Jede Runde (Modell → Werkzeug → Ergebnis) ist eine eigene Anfrage und bringt
eine frische Zusicherung mit. Die Zusicherung wird für Chats nicht verlängert.

**Das KI-Gateway** erreicht der Chat wie jede App über eine Destination (der
Schlüssel bleibt bei der Plattform, bei geschlossenem Abfluss nur Ampel
„grün“) — das ist seit RFC-0068 gemessen, hier kommt nichts Neues dazu.

**Die Modellmessung (§6, 08.11. auf oaap-demo, vier Kerne, keine GPU):**
„Lokal zuerst“ trägt. `qwen3:8b` (Denken aus), `qwen2.5:7b` und
`qwen3:4b-instruct` treffen 14 von 16 Fällen in 5–30 Sekunden pro Runde. Alle
drei **erfinden aber eine fehlende Angabe** (Uhrzeit), statt nachzufragen —
deshalb ist die Bestätigung schreibender Werkzeuge (D6) Pflicht. Die denkenden
Modelle fragen richtig nach, brauchen aber bis zu zwölf Minuten pro Runde; das
passt nicht in die fünf Minuten. Wissensfragen beantworten die kleinen Modelle
oft falsch und selbstsicher; der Wert kommt aus den Werkzeugen. Die
llama-Modelle fallen raus (eins legt auf „Danke“ einen Vorgang an). Neu offen:
Der Schalter fürs Denken ist je Modell verschieden, und ein Modellname im
KI-Gateway kann ihn heute nicht mitgeben. Durchs KI-Gateway auf oaap-test
gemessen: Werkzeugaufrufe gehen hin und zurück unverändert durch.

**Stufe 1 gebaut und gemessen (08.11., §9):** Referenz 0.1.243, MCP-Gateway
0.7.0, Testseite `assistent-probe` auf oaap-test. Die Tür heißt
`/platform/mcp/via/<gateway>/<sicht>` (mit Gateway im Pfad, weil ein Mandant
mehrere haben kann); die Seite des Chats nennt ihre Gateways unter
`/platform/mcp/gateways`. Im Gateway braucht die Sicht den Zugang `platform`,
und es zahlt ein Zugangsprofil mit `@<chat>` oder `@*` — ein `*`-Profil gilt
für Chats nicht. Gemessen 24/24 über die öffentlichen Namen wie ein Browser:
anna sieht durch die Testseite nur pA und schreibt dort, bert nur pB,
gefälschte Kopfzeilen von außen und die Tür ohne echte Zusicherung werden
abgelehnt, das Gateway zählt Verfahren A mit Chat und Assistent. Verfahren I
mit Claude Code bleibt 15/15.

**Stufe 2 gebaut und gemessen (08.11., §10):** Chat-App `apps/chat` 0.1.0 —
ein Assistent, die Werkzeuge einer Sicht, ein Modell über die Destination `ki`
(Schlüssel bleibt auf der Plattform), Verlauf als Datei je Person. In einer
Runde laufen erst die offenen Werkzeugaufrufe (frische Zusicherung), dann der
Modellzug. D6 ist vorgezogen: Was nicht `read` ist, läuft erst nach
„Ausführen“; ob ein Werkzeug liest, sagt nur das Gateway (0.7.1, `_meta`
`oaap/effect`). Gemessen 23/23 mit echtem lokalem Modell
(`qwen3:4b-instruct` auf oaap-test, Modellzüge 2–38 s): anna sieht pA, bert
pB, abgelehnt wird nichts geschrieben, zugestimmt genau einmal, fehlende
Angaben erfragt das Modell. Befund: Im selben Gespräch antwortet das Modell
aus früheren Ergebnissen, ohne erneut zu fragen — nicht weiter, aber womöglich
veraltet.

**Stufe 3 gebaut und gemessen (08.11., §11):** Chat 0.2.0 mit Assistenten in
den Daten des Chats (anlegen, ändern, löschen, Export/Import), Sichtbarkeit
privat / Team / Mandant über das Rechtemodell, geprüft bei jeder Runde,
`/Befehle` aus den Prompts der Sicht, Zustimmung ans Gateway gemeldet (Spalte
`confirmed`, Gateway 0.7.2). Gemessen 26/26 mit anna (pflegt Team service),
bert (benutzt) und carl (nichts): privat nur anna, Team anna und bert, carl
nicht; bert spricht als bert; entzogenes Recht: binnen 30 s weg, nächste
Runde abgelehnt. Nicht am Knoten gemessen: Mandanten-Assistent und
`/Befehle` — dafür bräuchte eine Testperson tenant_admin bzw. admin, und die
Rechteprüfung dieser Sitzung hat das Vergeben abgelehnt. Befund: Ohne Keycloak
konnte das Gateway den Katalog einer eigenen App nie lesen; behoben.
