# oaap.ai.assistants — Assistants: a View, a Prompt and a Model Name, Without Rights

- **ID:** `oaap.ai.assistants`
- **Version:** 0.5 (RFC-0101 stage 2: a person may rate an answer or a conversation with 0–5 stars; the rating names `assistant@rev` and is kept by the gateway that keeps the assistant, §2b. 0.4: RFC-0097 stage 1: assistants **live in the tenant's MCP gateway**, next to the views they name, with numbered revisions, a state `active | inactive` and the usage row's `assistant@rev`; the chat is the runtime; an assistant from the chat's configuration stays as "managed by configuration", §2a; additive for the format. 0.3: field `views`: the chat shows the views of MCP Apps,
  RFC-0075 D2). 0.2 (RFC-0074 stage 3: visibility and confirmation enforced by the
  chat app `apps/chat` 0.2.0, §2; the confirmation reaches the gateway as
  `X-OAAP-Confirmed`, §5). 0.1 (RFC-0074 stage 1: the format, the rule "no rights", the
  exchange file; how a chat acts as the person is procedure A,
  `oaap.core.identity` 2.13 and `oaap.ai.mcp-gateway` §3.9)
- **Status:** draft
- **RFC:** [RFC-0074](../rfcs/RFC-0074-assistants.md) (Accepted 2026-11-08, D1–D7; D2 superseded by [RFC-0097](../rfcs/RFC-0097-assistants-in-the-mcp-gateway.md))
- **Maturity:** stages 1–3 built and measured on `oaap-test` (2026-11-08): test
  page (24/24), chat app 0.1.0 with a real local model (23/23), chat app 0.2.0
  with assistants, visibility and confirmation at the gateway (26/26), tenant
  assistant and `/commands` end to end (18/18)

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
| `views` | `true` or `false` (0.3): the chat shows views of MCP Apps for this assistant's tools (RFC-0075 D2); default `false` |

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

## 2a. Where assistants live (0.4, RFC-0097 stage 1)

An assistant's definition lives in the tenant's **MCP gateway**
(`oaap.ai.mcp-gateway` §3.9b), not in a chat. The gateway keeps the record
of §2 and adds what only it assigns:

- `rev` — the revision, an integer the gateway assigns on every save
  (n+1), never the writer; every revision stays readable until it is
  compacted;
- `state` — `active` (offered), `inactive` (shown to whoever manages it,
  not offered in a chat), `deleted` (gone for everybody; the revisions
  stay under the retention rule);
- retention (D6): every revision a usage row still names, plus the last
  20; older ones are **compacted** — number, time and author stay, the
  text goes.

Visibility (§2, `private` / `context` / `tenant`) is enforced by the
gateway with the same rule the chat used, now in a shared reading
(`oaap-apps/lib/assistants`), and with the gateway's own declaration of
the authorization object `assistant` (RFC-0045). A chat:

- reads the assistants a person may use from the gateway, as that person;
- sends `X-OAAP-Assistant: <id>@<rev>` with every call, so the usage row
  names the revision that spoke;
- moves its old file into the gateway once, by a `tenant_admin`, owners
  kept, the file renamed, not deleted; until then nothing changes;
- never falls back to its file once its assistants live in the gateway;
- keeps an assistant from its configuration (`CHAT_ASSISTANT`) as
  "managed by configuration", without revisions (D7);
- may be limited by the tenant to a list of assistants (D9).

The exchange file (§3) stays the same; `rev`, `state` and `manage` are
never part of it.

## 2b. Ratings (0.5, RFC-0101 stage 2)

- A person may give **0–5 stars** to an answer (the model's final text of
  a round) and to a whole conversation; 0 means "useless", not "no
  rating". The last rating counts; it can be withdrawn.
- Only answers of an assistant **with a revision** can be rated (RFC-0101
  D8): a rating names `assistant@rev`. An assistant managed by
  configuration (§2a) has none, so it is not rated.
- The rating carries the circumstances of the answer as they were then
  (model alias, the conversation's light, view, per tool call name,
  effect class and outcome), **never** arguments, results or names.
  Question and answer travel only with the person's tick.
- It is kept where the assistant lives, by the MCP gateway
  (`oaap.ai.mcp-gateway` §3.9c). The chat keeps the stars in the person's
  own history, so that the person sees what they gave.

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

7. (0.4) A save in the gateway creates revision n+1 and revision n stays
   readable; `rev` sent by the writer is refused; a person without the
   grant neither sees nor saves (bait: a private assistant of a second
   person never appears, also not by id); a field like `token` is refused;
   a revision a usage row names survives compaction.

The reference reading is `oaap-apps/lib/assistants` (copies in `apps/chat`
and `apps/mcp-gateway`), tested in both apps.

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

## Deutsche Zusammenfassung (0.5, RFC-0101 Stufe 2)

Antworten und ganze Gespräche bekommen 0 bis 5 Sterne (0 heißt
„unbrauchbar“). Bewertbar ist nur, was ein Assistent mit Revision gesagt
hat; die Bewertung nennt `assistant@rev` und die Umstände von damals, nie
Argumente, Ergebnisse oder Namen. Frage und Antwort reisen nur mit Haken.
Gespeichert wird im MCP-Gateway, neben den Revisionen; der Chat behält die
Sterne im Verlauf der Person.

## Deutsche Zusammenfassung (0.4, RFC-0097 Stufe 1)

Ein Assistent liegt jetzt im **MCP-Gateway** des Mandanten, neben den
Sichten, die er nennt, nicht mehr in der Datei eines Chats. Jedes Speichern
ergibt eine neue Revision. Die Nummer vergibt das Gateway, alte Revisionen
bleiben lesbar. Verdichtet wird erst, was keine Messzeile mehr nennt und
nicht zu den letzten 20 gehört. Dann bleiben Nummer, Zeit und wer, der Text
geht. Zustände sind aktiv, inaktiv (nicht angeboten) und gelöscht. Die
Sichtbarkeit prüft das Gateway mit derselben Regel wie bisher der Chat
(gemeinsames Modul) und mit einem eigenen Rechteobjekt `assistant`. Der
Chat liest die Assistenten als die Person und meldet `id@rev` an jeder Tür.
Seine alte Datei übernimmt ein tenant_admin einmal; die Besitzer bleiben,
die Datei wird umbenannt. Danach fällt der Chat nie mehr still auf sie
zurück. `CHAT_ASSISTANT` bleibt als Rückfall erhalten, und ein Chat kann
auf eine Liste von Assistenten beschränkt werden.
