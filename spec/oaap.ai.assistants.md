# oaap.ai.assistants — Assistants: a View, a Prompt and a Model Name, Without Rights

- **ID:** `oaap.ai.assistants`
- **Version:** 0.2 (RFC-0074 stage 3: visibility and confirmation enforced by the
  chat app `apps/chat` 0.2.0, §2; the confirmation reaches the gateway as
  `X-OAAP-Confirmed`, §5). 0.1 (RFC-0074 stage 1: the format, the rule "no rights", the
  exchange file; how a chat acts as the person is procedure A,
  `oaap.core.identity` 2.13 and `oaap.ai.mcp-gateway` §3.9)
- **Status:** draft
- **RFC:** [RFC-0074](../rfcs/RFC-0074-assistants.md) (Accepted 2026-11-08, D1–D7)
- **Maturity:** stages 1–3 built and measured on `oaap-test` (2026-11-08): test
  page (24/24), chat app 0.1.0 with a real local model (23/23), chat app 0.2.0
  with assistants, visibility and confirmation at the gateway (26/26)

## 1. Purpose

A chat app on OAAP talks to a person with the help of a model and the tools
of an MCP gateway. An **assistant** says, for one purpose, which tools
(a view of the tenant's MCP gateway), which instructions (a system prompt and
a greeting) and which model (a name of the AI gateway) the chat uses.

An assistant **has no rights of its own** (RFC-0074 D1). It acts with the
rights of the person speaking to it, never more: what it may do is the
view ∩ that person's rights in the app behind each tool. The platform stores
no assistants (D2); a chat app keeps them in its own data, in this format, so
that a second chat app can import them.

## 2. The assistant

```yaml
id: reklamationen            # [a-z0-9][a-z0-9-]{0,47}, unique per chat instance
title: Reklamationen         # 1–80 characters
greeting: "Ich helfe bei Reklamationen."   # optional, 1–500 characters
system: |                    # 1–8000 characters
  Du bist der Assistent eines kleinen Handwerksbetriebs …
model: standard              # a model NAME of the AI gateway, never a model or an address
view: reklamation            # a view of the tenant's MCP gateway
gateway: vuebung-mcpgw       # optional: the gateway instance; required when the tenant has several
visibility: {scope: context, context: {team: service}}   # private | context | tenant
owner: <person id>           # 1–64 characters
commands: true               # optional, default false: the view's MCP prompts appear as /commands
```

As JSON the same object; YAML is shown for reading.

| Field | Rule |
|---|---|
| `id` | `^[a-z0-9][a-z0-9-]{0,47}$`, unique within one chat instance |
| `title`, `greeting`, `system`, `owner` | non-empty strings of at most 80 / 500 / 8000 / 64 characters; `greeting` optional |
| `model` | `^[a-z0-9][a-z0-9._:-]{0,63}$` — a name the tenant's AI gateway maps (`oaap.ai.gateway`, RFC-0064 stage 2). The tenant decides what `standard` means; the default rule is **local first** (D3) |
| `view` | `^[a-z0-9][a-z0-9-]{0,47}$`, the name of a view (`oaap.ai.mcp-gateway` §5) |
| `gateway` | optional, an instance name; without it the chat uses its tenant's only gateway and refuses when there are several |
| `visibility` | `{scope: private}`, `{scope: tenant}`, or `{scope: context, context: {<type>: <id>}}` with exactly one context (`<type>` `^[a-z][a-z0-9_]{0,31}$`, `<id>` 1–64 characters) |
| `commands` | `true` or `false` |

- **No rights (D1).** A field that looks like a right — `key`, `api_key`,
  `token`, `secret`, `password`, `roles`, `role`, `on_behalf_of`,
  `principal`, `scopes`, `scope`, `grants` — is **refused with a sentence**,
  not ignored: who writes it believes it works.
- **Unknown fields are refused** in 0.1.
- **Visibility (D4)** is read by the chat app against
  `oaap.core.authorization`: *private* — only the owner; *context* —
  everyone with an assignment in that context, created by a key user of it;
  *tenant* — everyone of the tenant, created by a `tenant_admin`. A chat app
  declares the authorization object (the reference chat: `assistant` with
  activities `use` and `manage` and the context field `team`, so a context
  is `{team: <id>}`) and checks visibility **at every round**, not only when
  a conversation starts: a revoked assignment stops the next round. When the
  person's assignments cannot be read, no context assistant is visible
  (fail closed). Visibility orders; it does not protect data — what an
  assistant can do stays bounded by view and the speaker's rights (D1).
- **Writing tools (D6)** run only after the person confirmed the call in the
  chat, every time, with tool and arguments shown. Only the gateway's effect
  class (`oaap.ai.mcp-gateway` §5.2, `_meta` `oaap/effect`) makes a tool
  `read`; a tool without it counts as writing.
- **Commands.** With `commands: true` the chat offers the view's MCP prompts
  as `/name …`; the prompt's text becomes the person's message. Prompts are
  read through the same door and the same person as tools.

## 3. The exchange file

```json
{"v": 1, "assistants": [ { … }, { … } ]}
```

Each entry must be valid by §2, and no `id` may occur twice. A chat app
imports such a file only as a whole: one invalid entry refuses the file,
with the sentences naming the entry by index.

## 4. How a chat acts as the person

Not part of the format, specified where it happens:

- the manifest field `mcp_client: {use: true}` and the doors on the chat's own
  site — `oaap.apps.runtime` 2.32.3;
- the check at the door, procedure A — `oaap.core.identity` 2.13;
- the gateway side, the way `platform` and profiles `@<chat>` —
  `oaap.ai.mcp-gateway` §3.9.

**The browser drives the loop (D7).** Every round — a model turn, a tool call,
its result — is one request from the browser to the chat, so every round
carries a fresh assertion of the person (five minutes). A round longer than
that fails with a sentence; the chat never retries under an old assertion and
never keeps one beyond the request that brought it.

## 5. Security requirements

1. An assistant carries no credential and no right; a chat app refuses one
   that tries (§2).
2. The assistant's id reaches the gateway only as information
   (`X-OAAP-Assistant`) and is recorded there; no decision depends on it.
3. A chat app keeps no assertion of a person beyond the request that brought
   it, and has no fallback to its own principal: without an assertion, no
   tool call.
4. A confirmed call carries `X-OAAP-Confirmed: yes` to the gateway, which
   records it (RFC-0074 §5.6). It is the chat's statement, recorded for
   review — never a permission.

## 6. Conformance tests

1. The example of §2 is valid; without `greeting`/`commands` too.
2. Each field of the "rights" list is refused with the sentence of D1; an
   unknown field is refused.
3. Each required field missing is refused.
4. `model` as an address (`http://…`), with a space, empty or capitalised is
   refused.
5. Every malformed `visibility` (unknown scope, context missing, empty, two
   contexts, extra fields on `tenant`) is refused; `private` and `tenant` pass.
6. An exchange file with a duplicate `id` or without `v` is refused.

The reference reading is `oaap-lab/assistent-probe/assistants.py` with
`test_assistants.py`.

## 7. Dependencies

`oaap.ai.mcp-gateway` (views), `oaap.ai.gateway` (model names),
`oaap.core.authorization` (visibility by context), `oaap.core.identity`
(the assertion, procedure A).

## Deutsche Zusammenfassung

Ein **Assistent** ist eine Sicht des MCP-Gateways, ein Systemprompt mit
Begrüßung, ein Modellname des KI-Gateways und eine Sichtbarkeit — **ohne
eigene Rechte**. Er handelt mit den Rechten der Person, die mit ihm spricht.
Felder, die nach einem Recht aussehen (`key`, `token`, `roles`,
`on_behalf_of` …), werden mit einem Satz abgelehnt, unbekannte Felder auch.
`model` ist ein Name (z. B. `standard`), den der Mandant im KI-Gateway
zuordnet, nie eine Adresse. Die Plattform speichert keine Assistenten; ein
Chat hält sie in seinen Daten und tauscht sie als Datei
`{"v": 1, "assistants": [...]}` aus. Wie der Chat als die Person handelt
(Verfahren A), steht in Identity 2.13, Runtime 2.32.3 und MCP-Gateway §3.9.
Der Browser treibt die Schleife: jede Runde eine Anfrage, also eine frische
Zusicherung. Sichtbarkeit durchsetzen und Bestätigung schreibender Tools
kommen in Stufe 3.

## Deutsche Zusammenfassung (0.2, RFC-0074 Stufe 3)

Der Chat setzt die Sichtbarkeit jetzt durch: privat nur die Eigentümerin, Team
alle mit `assistant.use` in diesem Team (pflegen mit `assistant.manage`),
Mandant alle (pflegen nur `tenant_admin`). Geprüft wird bei jeder Runde; ein
entzogenes Recht hält die nächste Runde an, und sind die Berechtigungen nicht
lesbar, sieht niemand einen Team-Assistenten. Schreibende Werkzeuge laufen nur
nach Zustimmung; der Chat meldet sie dem Gateway mit `X-OAAP-Confirmed: yes`,
das Gateway schreibt es in die Messzeile. Mit `commands: true` werden die
Prompts der Sicht zu `/Befehlen`.
