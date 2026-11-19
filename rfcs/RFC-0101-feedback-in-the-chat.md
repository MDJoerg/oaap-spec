# RFC-0101: Feedback in the Chat — the Conversation's Light, Stars per Answer, and "Not Satisfied" as a Case

- **Status:** **Accepted (2026-11-19)** — Jörg: "D1–D11 wie empfohlen".
  Wishes by Jörg from the first real chat test in tenant `bec` (I-62
  W1–W3, 2026-11-18); drafted the same day on his word, building on
  RFC-0097 and RFC-0098. **Stage 1 built** (2026-11-19, not pushed, not
  rolled out): chat 0.8.0, ai-gateway 0.9.0, mcp-gateway 0.21.0,
  `oaap.ai.gateway` 0.6.0, `oaap.ai.mcp-gateway` 0.19.0; §9 records what
  was measured and what was not.
- **Date:** 2026-11-19
- **Authors:** Jörg (the wishes: a light per conversation, defaulting to
  "sensitive data"; stars per answer and per conversation, always stored
  with assistant, revision, model, view, tool calls and time; "not
  satisfied" to the support, with an edited question and answer and the
  person's own expectation, explicitly to find gaps in the documentation),
  Claude (reading of chat, gateways and cases, design)
- **Depends on:** `oaap.ai.gateway` §7 (the light, a ceiling never a
  floor), `oaap.ai.mcp-gateway` §3.3 (the light of a view), §9/§10 (usage
  rows, no content), `oaap.ai.assistants` 0.3, RFC-0061 (cases, the
  feedback route, templates, the backend door), RFC-0097 (assistants with
  revisions in the MCP gateway, `assistant@rev`), RFC-0098 §4 (call ids,
  feedback with consent), RFC-0095 (`/me`)
- **Related:** I-62 W6/W7 (small chat versions, not here), I-63 (guided
  setups), RFC-0061 §5.4 (the AI key, not built)
- **Not part of this RFC:** the automatic processing of feedback by an AI
  (named in §5, its own RFC); roles of targets and tenants (RFC-0098 §3 —
  this RFC only shares the chat's header strip with them); W4–W8

## Summary

The chat answers, but nobody learns whether the answer helped, and the
person cannot say what they are about to put into it. Three pieces close
that, all in the chat, all handing their records to places that already
exist:

1. **The conversation's light (W1).** Every conversation carries a light
   the person chooses: `green` "sensitive and personal data", `yellow`
   "company information, nothing sensitive", `red` "only public input".
   The default is `green`. The light is a **ceiling the person sets for
   themselves** below the key's ceiling: the chat uses only models and
   views at most that light, and tells both gateways so they refuse too.
   Where no green path exists, the chat says so plainly and offers two
   requests to the tenant's administrators: "please provide a green
   option" and "may I do this scenario?" — both as cases (RFC-0061).
2. **Stars (W3).** 0–5 stars per answer and per conversation. Each rating
   is stored with its circumstances — `assistant@rev`, model alias and its
   light, view, the names and outcomes of the tool calls, duration, time —
   **next to the assistant's revisions in the MCP gateway** (RFC-0097), so
   one can see what a new model or a better prompt brought. Without
   content unless the person ticks "include question and answer".
3. **Not satisfied (W2).** A dialog in which the person edits the question
   and the answer that matter, writes what they expected, and may mark
   "the documentation is missing something". It becomes a case in the
   tenant's `vorgaenge` (RFC-0061) with the same circumstances, and — only
   with the person's consent — the call ids of the conversation
   (RFC-0098 §4.3), so the support finds exactly the usage rows of that
   conversation and nothing else.

## 1. Facts (read 2026-11-19)

- **chat 0.7.1** (`oaap-apps/apps/chat`): the browser drives the loop
  (RFC-0074 D7); history is one JSON file per conversation under
  `/data/people/<user id>/`, read only by that person. Settings live in
  the browser (`localStorage`). The model list (`api/models`) already
  carries each alias's light as the AI gateway reports it for the chat's
  key (`GET /v1/models`, worst light along the path); the view list
  (`api/views`) carries each view's light. The chat sends
  `X-OAAP-Assistant` to the MCP gateway. No ratings, no feedback, no
  notion of a conversation light.
- **AI gateway §7:** the light describes what can happen to the data, not
  quality. It is enforced on declarations, never on content: a key's
  worst light and its release for personal data. A declared light is a
  ceiling; a chain never gets greener.
- **MCP gateway §3.3:** a view's light is its worst server's; a key may use
  a view only up to its own light; otherwise the view answers like an
  unknown one. §10: no content in usage rows.
- **RFC-0061:** a case has `kind` (`bug`, `question`, `idea`, `change`,
  `internal`), `context`, attested `tech`, `queue`. Two ways in: the
  attested `/platform/feedback` route on the app's own origin (the
  gateway attests the person), and the backend door
  `/platform/cases/submit` with the app's instance key (the person is
  only app-asserted, `on_behalf_of`). Templates add subkinds and fields.
  Without a `vorgaenge` instance the route says so.
- **RFC-0097** (Draft): assistants with numbered revisions in the MCP
  gateway, usage rows record `assistant@rev`; an evaluation per assistant
  and revision is stage 2 there, and "ratings (I-62) attach to the same
  key". Until it is built, an assistant has no revision a rating could
  name.
- **RFC-0098 §4** (Draft): log levels `lean`/`support`/`full`; in
  `support` the chat keeps the call ids per conversation in the person's
  history and hands them over only with consent on feedback.

## 2. The conversation's light (W1)

### 2.1 What the person chooses

| light | the chat says | the chat uses |
|---|---|---|
| `green` (default) | „Sensible und personenbezogene Daten“ | only models and views whose light is `green` |
| `yellow` | „Firmeninformationen, nichts Sensibles“ | models and views up to `yellow` |
| `red` | „Nur Öffentliches“ | everything the key allows |

The words follow the table of `oaap.ai.gateway` §7, read from the
person's side: the light says what *I* am about to put in, so it may pick
only paths that may receive it. It can never be worse than the key's
ceiling — the chat offers only the lights the key reaches.

Changing to a worse light is a deliberate act: one sentence, one click
("Ich gebe in diesem Gespräch nichts Sensibles ein"). Changing to a
better one needs nothing. The light is stored in the conversation's
history file and shown in the header strip of the conversation, next to
the role of RFC-0098 §3 once that exists — two different things in one
place: the light says what the data may meet, the role says what the
target is.

### 2.2 Who enforces it

The light protects the person from a mistake; it is **not a control over
the person** — the key's ceiling remains the control (§7). Still, a
promise only the browser keeps is a weak one. Therefore:

- The chat lists and uses only models and views within the light; an
  assistant whose model or view is worse cannot be started in that
  conversation, and the chat says which part is too red.
- The chat sends the light with every request as **`X-OAAP-Light`**. Both
  gateways treat it as an **additional ceiling for this request only**:
  it can tighten the key's ceiling, never loosen it. The AI gateway
  refuses an alias whose path is worse (also after a failover: a
  failover to a worse light fails, as it does for the key today); the
  MCP gateway refuses a view that is worse with `403` and a sentence
  naming both lights (built so in stage 1: the requester may open the
  view, so the sentence reveals nothing, and the chat can show it). Both
  record the light the request carried in the usage row (a word from a
  fixed list, not content).

### 2.3 When there is no green path

In `bec` today no supplier is green. Then the chat says, before the first
message and without euphemism:

> „Für sensible Daten gibt es in diesem Mandanten keinen sicheren Weg:
> kein Modell und keine Sicht dieses Assistenten ist grün.“

and offers three things:

1. **„Ohne Sensibles weiter“** — the deliberate change of §2.1.
2. **„Grüne Option erbitten“** — a case of kind `idea` to the tenant's
   default queue: what the person wants to do (free text), which
   assistant, which part is too red. The chat fills the rest.
3. **„Vorab fragen, ob das erlaubt ist“** — a case of kind `question`
   with the scenario described by the person.

Both go the way of §4.3. Without a `vorgaenge` instance the two buttons
are not shown; a `tenant_admin` sees instead: „Rückmeldungen brauchen
die App Vorgänge in diesem Mandanten.“

## 3. Stars (W3)

### 3.1 What is rated

- **Per answer:** 0–5 stars under each assistant answer (an answer is the
  model's final text of a round, after its tool calls).
- **Per conversation:** 0–5 stars in the conversation's menu, any time.
- A rating can be changed or withdrawn by the person; the last one counts.
- 0–2 stars open the offer "Nicht zufrieden? An den Support geben" (§4);
  the button exists anyway, independent of stars.

### 3.2 The circumstances, stored with every rating

| field | content |
|---|---|
| `assistant`, `rev` | the assistant and the revision that spoke (RFC-0097) |
| `model`, `light` | the alias as the chat named it, its light as the AI gateway reported it, and the conversation's light (§2) |
| `view`, `gateway` | the view and the MCP gateway instance |
| `tools` | per tool call: name, effect class, outcome (`ok`, refused, error code) — **no arguments, no results** |
| `scope` | `answer` (with the round number) or `conversation` (with the number of rounds) |
| `ms` | duration of the round (or of the conversation) |
| `at` | time |
| `stars` | 0–5 |
| `who` | a key that lets the same person change their rating (D3), not a name |
| `text` | only if the person ticked „Frage und Antwort mitgeben“: the question and the answer as the person left them, at most 8,000 characters each (D4) |

Without `text` the record holds no content: names from the configuration,
words from fixed lists, numbers. §10 of the MCP gateway stays literally
true for usage rows; ratings are a separate record with their own reader.

### 3.3 Where ratings live

In the **MCP gateway, next to the assistant's revisions** (RFC-0097):
`POST /mcp/_assistants/<id>/ratings`, sent by the chat with the person's
assertion, refused for an assistant the person cannot see. The gateway
already keeps the usage rows that name `assistant@rev`; the evaluation
tab of RFC-0097 stage 2 shows, per assistant and revision: number of
ratings, distribution of stars, share of 0–2, number of support cases
(§4) and, from the usage rows, calls, refusals and errors. That is the
comparison Jörg asked for: what did the new model, the better prompt
bring.

Who reads ratings: whoever may manage the assistant, and the
`tenant_admin`; texts (`text`) the same readers. The person sees their
own ratings on `/me` (RFC-0095).

## 4. Not satisfied (W2)

### 4.1 The dialog

Opened from an answer („Nicht zufrieden“) or from the conversation menu:

- **Question and answer**, pre-filled from the conversation (the last
  question and the answer it is opened from), both editable — the person
  shortens, removes names, adds what is missing.
- **Tool calls** of that round as cards: name and outcome always;
  arguments and results only if the person ticks them (they are data the
  person may see, not necessarily the support).
- **„Was hätte ich erwartet?“** — free text, required.
- **„In der Dokumentation fehlt etwas“** — a tick; if the answer cited
  help pages (help 0.5 links), they are listed and travel along, so the
  documentation side sees which page was read and did not suffice.
- **Consent** (only where RFC-0098 level `support` or `full` applies):
  „Die Aufruf-Kennungen dieses Gesprächs mitgeben, damit der Support die
  Protokollzeilen findet.“ Without the tick, no ids travel.
- A line that tells the truth: „Der Vorgang trägt deinen Namen. Lesen
  kann ihn, wer im Mandanten Rückmeldungen bearbeitet.“

### 4.2 The case

| field (RFC-0061) | value |
|---|---|
| `kind` | `question`, subkind `chat-answer` (template shipped by the chat, §6 of RFC-0061) |
| `context` | node → tenant → the chat instance → object `{kind: "conversation", id}` (the conversation's own id; the support cannot open it, the person can) |
| `queue` | the assistant's `support_queue` if set, else the tenant's default queue (D6) |
| template fields | `assistant`, `rev`, `model`, `light`, `view`, `tools`, `expected`, `doc_gap`, `doc_pages`, `call_ids` (only with consent), and the circumstances of §3.2 |
| text | the edited question and answer |

The answer of the support comes back the way RFC-0061 returns answers to
the reporter; the chat shows a mark on the conversation when its case is
answered (it reads the case status with the person's session).

### 4.3 The way in

The chat page runs in the person's browser on the chat instance's own
origin. It posts the case to **`/platform/feedback`** on that origin, so
the gateway attests the person (RFC-0061 §3.1), and passes template and
fields. The backend door (§3.2 of RFC-0061, person only app-asserted) is
not used: it would make the chat able to file cases in anyone's name.
The same way carries the two requests of §2.3. Whether the route passes
a template and its fields today must be read when building; if it does
not, the route is extended, not bypassed.

## 5. Later, named

- **Automatic processing (W2's aim).** A support assistant reads cases of
  subkind `chat-answer`, groups them by assistant and revision, proposes
  a prompt change or a documentation change and files it as a case of
  kind `change`. It needs the AI key of RFC-0061 §5.4 and a decision on
  which light the support assistant itself may use. Its own RFC.
- **Ratings as a measure in the catalog** (RFC-0097 D5, assistant as a
  package): an exported assistant could carry its rating summary. Not
  before there is something to compare.

## 6. Security requirements

1. The conversation's light only tightens: neither the chat nor a
   forged `X-OAAP-Light` can make a gateway use a path worse than the
   key's ceiling. The ceiling of a request is the worse-for-the-request
   of the two: header `green` on a `yellow` key means `green`; header
   `red` on a `yellow` key means `yellow`.
2. A rating or a case for an assistant the person cannot see is refused
   like an unknown assistant (bait: a private assistant of a second
   person).
3. Without the tick, a rating holds no content and a case holds no tool
   arguments, results or call ids.
4. Readers of ratings are the assistant's managers and the
   `tenant_admin`; a manager of assistant A reads nothing of assistant B
   (bait).
5. Cases enter only through the attested route; the chat holds no key
   with `oaap.cases.submit`.
6. The person sees what they gave: own ratings on `/me`, own cases in
   `vorgaenge` as reporter.

## 7. Decisions

- **D1 Scale.** *Decided (Jörg, 2026-11-19, as recommended):* 0–5 stars per answer and per
  conversation, as Jörg wished; 0 means "useless", not "no rating".
- **D2 Where ratings live.** *Decided (Jörg, 2026-11-19, as recommended):* in the MCP gateway next to
  the revisions (§3.3). Alternatives: in the chat (lost when a second
  chat uses the same assistant, RFC-0097 D9) or as cases (a case is work
  to clear; a star is not).
- **D3 The person in a rating.** *Decided (Jörg, 2026-11-19, as recommended):* no name or user id;
  `who` is an HMAC of the user id with a per-gateway secret, enough to
  change one's own rating and to count persons, not enough to name them.
  `/me` finds one's own ratings by recomputing it.
- **D4 Text with a rating.** *Decided (Jörg, 2026-11-19, as recommended):* only with the tick;
  readable by the same readers; kept 180 days, then the text is removed
  and the rating stays.
- **D5 Default light.** *Decided (Jörg, 2026-11-19, as recommended):* `green` for every new
  conversation, as Jörg wished; a tenant setting may set `yellow` as the
  default (demo, training); `red` is never a default.
- **D6 Queue of a "not satisfied" case.** *Decided (Jörg, 2026-11-19, as recommended):* a new
  optional assistant field `support_queue` (in `oaap.ai.assistants`, with
  RFC-0097's revisions), else the tenant's default queue.
- **D7 `X-OAAP-Light` in both gateways.** *Decided (Jörg, 2026-11-19, as recommended):* yes, in stage
  1; a few lines each, and the light stops being a promise only the
  browser keeps.
- **D8 Ratings before RFC-0097.** *Decided (Jörg, 2026-11-19, as recommended):* no ratings until
  assistants have revisions; a star that names a prompt nobody can read
  again measures nothing. W1 (stage 1) does not wait.
- **D9 Call ids without RFC-0098 stage 3.** *Decided (Jörg, 2026-11-19, as recommended):* the case
  travels without ids; time and `assistant@rev` already narrow the rows,
  and the dialog says the ids are missing because the tenant logs `lean`.
- **D10 Tool arguments in a case.** *Decided (Jörg, 2026-11-19, as recommended):* off by default, per
  card a tick (§4.1).
- **D11 Mark for an answered case in the chat.** *Decided (Jörg, 2026-11-19, as recommended):* yes,
  read with the person's session from `vorgaenge`; no notification beyond
  what RFC-0061 already sends.

## 8. Stages and tests

| stage | content | done when |
|---|---|---|
| 1 | conversation light in the chat (§2.1–2.3), `X-OAAP-Light` in AI and MCP gateway, the two requests as cases | a green conversation with a yellow assistant model does not start and says why; a direct request with `X-OAAP-Light: green` to a yellow alias is refused by the AI gateway, and to a yellow view by the MCP gateway (bait: header `red` on a key with ceiling `yellow` does not reach a red alias); „Grüne Option erbitten“ creates a case of kind `idea` with the attested person; without `vorgaenge` the buttons are absent and the admin sentence shows |
| 2 | stars per answer and conversation, stored in the gateway with the circumstances (needs RFC-0097 stage 1) | a rating names `assistant@rev` and holds no content without the tick; changing it replaces it; a rating for another person's private assistant is refused; a manager of A reads no rating of B |
| 3 | "not satisfied" dialog, template `chat-answer`, doc gap, consent for call ids (ids need RFC-0098 stage 3) | the case carries the edited text, expected, doc pages; without consent no call ids, with consent exactly the conversation's ids; the answered mark appears |
| 4 | evaluation per assistant and revision (with RFC-0097 stage 2) | two revisions of one assistant show separate star distributions and case counts |

Spec changes: `oaap.ai.assistants` (field `support_queue`, ratings
record), `oaap.ai.mcp-gateway` (§3.3 request ceiling `X-OAAP-Light`,
§3.9b ratings with RFC-0097, §9 column `light`), `oaap.ai.gateway` (§7
request ceiling), chat README.

## 9. Stage 1, built (2026-11-19)

- **ai-gateway 0.9.0:** `X-OAAP-Light` as a ceiling per request on
  `/v1/chat/completions` (and every inference path) and `/v1/models`;
  `503 conversation_light` with both lights; `400 bad_light`; usage
  column `light`. 13 new checks in `test_gateway.py` (283/283), among them
  the bait: `red` on a `yellow` key does not reach a red alias.
- **mcp-gateway 0.21.0:** the same on every MCP request after the key or
  profile check; `403` with a sentence naming both lights and the server;
  checked inside an open session too; usage column `light`. 7 new checks
  in `test_gateway.py` (455/455), bait: `red` on a profile with ceiling
  `green` stays refused.
- **chat 0.8.0:** light per conversation (default `green`,
  `CHAT_DEFAULT_LIGHT` may say `yellow`, never `red`), sent with every
  model turn and every call at the door; worse only with `sure: true`
  and the sentence; the changes in the person's own history (`lights`);
  `GET api/light` with the lights of model and view as the gateways
  report them and the key's ceiling (`/v1/usage`); the warning without a
  path, sending blocked, the three ways of §2.3; the two requests posted
  from the browser to `/platform/feedback` (kind `idea`/`question`,
  object `{kind: assistant, id}`, the circumstances as text — the route
  takes no template fields, and stage 1 needs none). 19 new checks in
  `test_chat.py` (132/132). Looked at in a browser against the stand-in
  platform: the warning, the light dialog (red disabled above the key's
  ceiling, the sentence required), the request dialog and the case it
  posts, a yellow conversation that then runs, the narrow layout.
- **Not measured:** on a node, against the real `vorgaenge` route and
  real gateways; dark mode; the operator's pages do not show the new
  `light` column yet.

## Zusammenfassung auf Deutsch

Drei Wünsche aus dem ersten echten Chat-Test in bec (I-62), alle im Chat,
alle mit Ablage an Orten, die es schon gibt:

1. **Ampel je Gespräch (W1).** Die Person wählt, was sie eingeben wird:
   grün „sensible und personenbezogene Daten“ (Vorgabe), gelb
   „Firmeninformationen, nichts Sensibles“, rot „nur Öffentliches“. Der
   Chat nimmt dann nur Modelle und Sichten bis zu dieser Farbe. Er schickt
   die Farbe als `X-OAAP-Light` mit, und beide Gateways lehnen ebenfalls
   ab. Die Farbe kann die Decke des Schlüssels nur verschärfen, nie
   lockern. Sie schützt die Person vor einem Versehen und ist keine
   Kontrolle über sie. Gibt es keinen grünen Weg (in bec heute so), sagt
   der Chat das offen und bietet an: bewusst ohne Sensibles weiter,
   „grüne Option erbitten“ oder „vorab fragen, ob das erlaubt ist“. Die
   beiden Anfragen werden Vorgänge (RFC-0061).
2. **Sterne (W3).** 0–5 Sterne je Antwort und je Gespräch. Mit jeder
   Bewertung werden die Umstände gespeichert: `assistent@rev`, Modell und
   Farbe, Sicht, Werkzeugaufrufe nur mit Name und Ausgang, Dauer und Zeit.
   Inhalte kommen nur dazu, wenn die Person „Frage und Antwort mitgeben“
   ankreuzt. Die Bewertungen liegen **im MCP-Gateway neben den
   Revisionen** (RFC-0097). Dort zeigt die Auswertung je Revision, was ein
   neues Modell oder ein besserer Prompt gebracht hat. Deshalb gibt es
   Sterne erst, wenn Assistenten Revisionen haben.
3. **Nicht zufrieden (W2).** Ein Fenster, in dem die Person Frage und
   Antwort bearbeitet, ihre Erwartung aufschreibt und „in der Doku fehlt
   etwas“ ankreuzen kann. Die zitierten Hilfeseiten gehen mit. Daraus wird
   ein Vorgang im Mandanten, Unterart `chat-answer`, mit Namen der Person
   über die bezeugte Feedback-Route. Die Aufruf-Kennungen gehen nur mit
   Einwilligung mit (RFC-0098 §4.3). Dann findet der Support genau die
   Protokollzeilen dieses Gesprächs.

**Stufen:** 1 Ampel je Gespräch samt Gateway-Kopfzeile und den beiden
Anfragen. Das geht sofort, ohne andere RFCs. 2 Sterne (nach RFC-0097
Stufe 1). 3 „Nicht zufrieden“ (Kennungen nach RFC-0098 Stufe 3).
4 Auswertung je Revision (mit RFC-0097 Stufe 2). Die automatische
Bearbeitung durch eine KI ist benannt, kommt aber als eigenes RFC. D1–D11
hat Jörg am 19.11. wie empfohlen entschieden.
