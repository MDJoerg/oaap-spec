# RFC-0097: Assistants in the MCP Gateway — Revisions, Exchange, and the Assistant Channel

- **Status:** Draft (2026-11-19). Direction decided by Jörg in conversation
  on 2026-11-19: "the assistant goes into the gateway as proposed" and
  "an external AI may couple to an assistant over MCP, with permission and
  only where released". **D6, D7, D9 decided** (Jörg, 2026-11-19: "Alle
  wie empfohlen") — the decisions stage 1 needs are complete. Open: D3,
  D4, D5, D8 (stages 2 and 3), each with a recommendation. Nothing built.
- **Date:** 2026-11-19
- **Authors:** Jörg (the questions: where are assistants stored; revisions,
  upload/download, evaluation, support; an external AI coupled to the
  chat's assistants over MCP), Claude (reading of chat and gateway, design)
- **Depends on:** `oaap.ai.assistants` 0.3, `oaap.ai.mcp-gateway` 0.18.0
  (views, procedures A/P/U, usage rows with `client`/`assistant`, §10),
  RFC-0074 (assistants; **D2 is superseded** by this RFC), RFC-0075 (views
  of MCP Apps), RFC-0095 (`/me`, readiness), RFC-0068 (closed egress),
  RFC-0045 (contexts and grants)
- **Related:** RFC-0098 (targets, roles, log levels), RFC-0099 (result
  views), I-62 W3 (ratings per answer, stored with assistant and revision)
- **Not part of this RFC:** the chat loop itself (unchanged); an assistant
  calling another assistant (agent-to-agent, later); ratings and feedback
  (I-62, its own RFC — this RFC only provides the revision they refer to)

## Summary

An assistant is a view, a prompt and a model name (RFC-0074 §2). Today the
view lives in the MCP gateway, the model name in the AI gateway — and the
prompt, the part one wants to revise, evaluate and support, lives in one
file per chat instance (`/data/assistants.json`), overwritten on every save,
invisible to every other client.

This RFC moves the **definition** of assistants into the MCP gateway, next
to the views they name. The chat stays the runtime: it loads assistants
from the gateway, runs the conversation, keeps the history. In return:

1. **Revisions.** Every save creates a numbered revision; usage rows record
   `assistant@rev`. Support can say which prompt spoke on a given day.
2. **Exchange.** Export and import as a file in `oaap.ai.assistants`
   format; optionally a package kind in the catalog.
3. **Evaluation.** Usage per assistant and revision on the operator's page;
   ratings (I-62) attach to the same key.
4. **The assistant channel.** An external MCP client (Claude Desktop, an
   IDE) can connect to `/mcp/a/<assistant>` and receive what the chat
   receives: the view's tools, the assistant's prompt as server
   `instructions`, its commands as MCP `prompts`, and the target context of
   RFC-0098 — only where the tenant and the assistant release it.

## 1. Facts (read 2026-11-19)

- `apps/chat/store.py`: one JSON file per chat instance, written whole via
  a temp file and `os.replace`; one more assistant can come from the
  configuration (`CHAT_ASSISTANT`). No history.
- `apps/chat/assistants.py`: the check of `oaap.ai.assistants` 0.1/0.3 is a
  pure function, already meant to be applied on import of a file.
- RFC-0074 D2: "in the chat app's data … The platform stores no
  assistants." The gateway is not the platform; it is an app of the tenant.
  Moving the definition there keeps that sentence true for the platform.
- The gateway already records `client` and `assistant` per usage row
  (0.7, only for information, §5.5 of RFC-0074) and receives the assistant
  as `X-OAAP-Assistant` from the chat.
- MCP `initialize` returns an optional `instructions` string; `prompts/list`
  returns named prompts. Both exist in the protocol versions the gateway
  speaks (§3.2/§6).

## 2. Proposal

### 2.1 The assistant record in the gateway

Same fields as `oaap.ai.assistants` 0.3, plus:

- `rev` — integer, assigned by the gateway, never by the writer;
- `state` — `active` | `inactive` (an inactive assistant is shown to its
  owner and the administration, not offered in a chat);
- `channel` — `off` | `on` (§2.4), default `off`;
- `changed_by`, `changed_at` per revision.

Rules unchanged: **no rights** (RFC-0074 D1); a field that looks like a
right is refused with a sentence; `model` is a name of the AI gateway;
`view` must be a view of this gateway. Visibility (`private`, `context`,
`tenant`) is enforced by the gateway with the same grants the chat uses
today (RFC-0045).

Storage: the gateway's database, a table `assistants` (current) and
`assistant_revisions` (all revisions, append only). Retention of old
revisions: D6.

### 2.2 How the chat uses it

- `GET /mcp/_assistants` through the via door (like `/mcp/_views`, §3.9a):
  the assistants this person may use, current revision, readiness of the
  view (RFC-0095 stage 3).
- Create, change, deactivate: `PUT/POST /mcp/_assistants/<id>` through the
  same door, the person's grants decide; every write is a new revision.
- The chat sends `X-OAAP-Assistant: <id>@<rev>` with every call; the usage
  row stores both parts.
- Migration: on first start against a gateway that knows assistants, the
  chat offers to move its `assistants.json` there (one revision 1 per
  assistant, owner kept); afterwards the file is renamed, not deleted.
- An assistant from `CHAT_ASSISTANT` stays possible (D7) and is marked
  "managed by configuration".

### 2.3 Export, import, evaluation, support

- **Export:** one assistant (current or a chosen revision) as a YAML/JSON
  file in `oaap.ai.assistants` format, without `owner` and `rev`.
- **Import:** checked by the same function; the importer becomes owner;
  the view must exist in this gateway, otherwise refused with the name of
  the missing view. Import never brings rights, only text.
- **Catalog:** optionally a package kind `assistant` (D5).
- **Evaluation:** the operator's page gets a tab per assistant: calls,
  refusals, persons (count only), per revision. Ratings (I-62 W3) are
  stored with `assistant@rev`.
- **Support:** a usage row with `assistant@rev` leads to the exact prompt
  that spoke. Diff between two revisions on the page.

### 2.4 The assistant channel

An external MCP client connects to

```
https://<gateway>/mcp/a/<assistant>
```

signed in at the tenant's identity provider (§2.2 of the gateway spec) —
never with a key: a channel always carries a person.

What it receives:

- `tools/list`: the tools of the assistant's view, filtered as for this
  person, with the target parameter of RFC-0098 where the view has
  targets;
- `initialize.instructions`: the assistant's `system` text;
- `prompts/list`: the assistant's greeting and, if `commands: true`, the
  view's prompts;
- usage rows with `client = channel:<client name>` and `assistant@rev`.

What stays different from the chat:

- **The model is not ours.** The external client sends results of tools to
  its own model. This is data leaving the tenant (RFC-0068). The channel is
  therefore off unless **both** switches are on: the tenant's
  `assistant_channel` setting and the assistant's `channel: on` (D3).
  A closed tenant (RFC-0068) never opens a channel.
- **Confirmation:** the chat's confirmation card does not exist in an
  external client. Writing tools in a channel follow the view's effect
  class; D4 decides whether a channel may write at all.
- The assistant's prompt becomes visible to the external client. It must
  not hold secrets (it never should; the check refuses nothing here, the
  page says it).

## 3. Security requirements

1. An assistant record carries no right; the channel adds none (effective =
   view ∩ the person's rights ∩ target rights of RFC-0098).
2. Usage rows record `assistant@rev`, never the prompt text (§10 unchanged).
3. The channel requires a signed-in person; key calls to `/mcp/a/…` are
   refused.
4. Channel switches are audited (who, when, which assistant).
5. Import is checked like a save; a file cannot set `rev`, `owner`,
   `state` or `channel`.

## 4. Decisions

- **D1 Where assistants live.** *Decided (Jörg, 2026-11-19):* in the MCP
  gateway; the chat is the runtime. Supersedes RFC-0074 D2.
- **D2 External coupling.** *Decided (Jörg, 2026-11-19):* yes, as an MCP
  channel per assistant, only with permission and release.
- **D3 Who releases the channel.** *Recommendation:* tenant setting by
  `tenant_admin`, plus `channel: on` per assistant by whoever may manage
  that assistant; both required.
- **D4 Writing in a channel.** *Recommendation:* stage 1 read only (tools
  with effect class `read`); writing later, with MCP elicitation as the
  confirmation where the client supports it.
- **D5 Package kind `assistant` in the catalog.** *Recommendation:* yes,
  in stage 3; the view it names travels as a dependency by name, never as
  content.
- **D6 Revisions kept.** *Decided (Jörg, 2026-11-19, as recommended):* all revisions that a usage row
  of the retention window names, plus the last 20; older ones compacted.
- **D7 `CHAT_ASSISTANT`.** *Decided (Jörg, 2026-11-19, as recommended):* stays as a fallback for a chat
  without a gateway, shown as "managed by configuration".
- **D8 Path of the channel.** *Recommendation:* `/mcp/a/<assistant>`; a
  rename of the assistant keeps the old path as an alias for 30 days.
- **D9 Several chats, one gateway.** *Decided (Jörg, 2026-11-19, as recommended):* assistants belong to
  the gateway, not to a chat; a chat may be limited to a list of
  assistants by the tenant (field on the chat instance).

## 5. Stages and tests

| stage | content | done when |
|---|---|---|
| 1 | assistant records with revisions in the gateway, `/mcp/_assistants`, chat loads from there, migration of `assistants.json`, `assistant@rev` in usage rows | a save creates rev n+1, rev n stays readable; a person without the grant neither sees nor saves (bait: a private assistant of a second person never appears); a field like `token` is refused |
| 2 | export/import, evaluation tab, revision diff | an exported file imports into a second gateway with the same view name; a missing view is refused with its name |
| 3 | assistant channel (read only), tenant + assistant switch, catalog kind | Claude Desktop connected to `/mcp/a/x` lists exactly the view's read tools and receives the prompt as instructions; with either switch off: 403 with a sentence; closed tenant: refused |

Spec changes: `oaap.ai.assistants` 0.4 (fields `rev`, `state`, `channel`;
"lives in the MCP gateway"), `oaap.ai.mcp-gateway` (§3.9b assistants, §2.4
channel route, §9 column `assistant_rev`).

## Zusammenfassung auf Deutsch

Heute liegt ein Assistent als Datei in der Chat-Instanz und wird beim
Speichern überschrieben. Die Sicht des Assistenten liegt aber im
MCP-Gateway und der Modellname im KI-Gateway, also liegt nur der Prompt im
Chat. Das RFC verlegt die **Beschreibung des Assistenten ins MCP-Gateway**
(von Jörg am 19.11. entschieden). Der Chat bleibt die Laufzeit und behält
die Verläufe.

Das bringt:

- **Revisionen:** Jede Änderung bekommt eine neue Nummer. In der
  Nutzungszeile steht `assistent@rev`, so findet der Support den Prompt,
  der an einem bestimmten Tag gesprochen hat.
- **Export und Import** als Datei, später als Pakettyp im Katalog.
- **Auswertung** je Assistent und Revision. Bewertungen aus I-62 hängen
  daran.
- **Assistenten-Kanal:** Eine externe KI (Claude Desktop, IDE) verbindet
  sich mit `/mcp/a/<assistent>` und bekommt dasselbe wie der Chat: die
  Tools der Sicht, den Prompt als `instructions`, die Befehle als
  `prompts` und den Ziel-Kontext aus RFC-0098. Das geht nur mit einer
  angemeldeten Person. Es müssen zwei Schalter an sein (am Mandanten und
  am Assistenten), denn die Daten gehen an ein fremdes Modell. Ein
  geschlossener Mandant öffnet nie einen Kanal. Stufe 1 ist nur lesend.

RFC-0074 D2 („Assistenten liegen im Chat“) wird damit abgelöst. Am 19.11.
hat Jörg D6, D7 und D9 wie empfohlen entschieden, damit steht alles, was
Stufe 1 braucht. Revisionen bleiben, solange eine Nutzungszeile auf sie
zeigt, dazu immer die letzten 20 (D6). `CHAT_ASSISTANT` bleibt als Rückfall,
gekennzeichnet als „verwaltet über die Konfiguration“ (D7). Assistenten
gehören dem Gateway, der Mandant kann einen Chat auf eine Liste beschränken
(D9). Offen sind noch D3, D4, D5 und D8 für die Stufen 2 und 3.
