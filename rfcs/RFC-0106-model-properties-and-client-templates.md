# RFC-0106: Model Properties and Client Templates in the AI Gateway

- **Status:** Draft (2026-11-20). From idea I-56 (Jörg, 2026-11-17). Open
  decisions D1–D12 below, each with a recommendation. Nothing built.
- **Date:** 2026-11-20
- **Authors:** Jörg (the requirement: whoever wants to use the gateway's
  models in VS Code maintains `chatLanguageModels.json` by hand; a tab
  "Vorlagen" in the gateway should produce that file — choose the target,
  choose the model names or derive them from a key, copy or download; the
  real value is in the extra facts a user rarely knows: tool calling,
  images, context and output size), Claude (reading of `oaap.ai.gateway`
  0.7 and the reference app 0.10.1, design)
- **Depends on:** `oaap.ai.gateway` 0.7.0 (§2 keys, §3 aliases, §4.2
  probing and aliases from a model list, §7 the light, §7a the setup
  door), RFC-0064 (catalogue in the app), RFC-0104 (setup door, profile
  `ki-arbeitsplatz`), RFC-0088 (assets: the gateway names its models)
- **Not part of this RFC:** exporting MCP gateway views for clients (I-57,
  same pattern, own RFC); a provider's model life cycle (deprecation lists);
  prices of any kind (RFC-0064: volume only)

## Summary

Today the gateway knows, for each alias, only its **targets** (supplier
and the supplier's model name) and the **light**. A client that wants to
use an alias needs more: does the model call tools, does it take images,
how many tokens go in and come out. Users guess these numbers, and a wrong
guess is not a harmless detail: a client that thinks a model has no tool
calling hides it from agent mode, and a client that thinks the context is
larger than it is sends requests the supplier refuses.

This RFC adds two things, in two stages:

1. **Properties on the alias** (stage 1). Four facts — `tools`, `vision`,
   `context`, `output` — kept by the operator on the alias, proposed from
   the supplier's model list where the supplier tells, proposed from an
   optional tool-call test, and never guessed. They appear in
   `GET /v1/models` as `oaap_*` fields next to the light, so the platform's
   own chat and every other client can read them. The setup door takes
   them, so a profile can set them.
2. **Client templates** (stage 2). A tab "Vorlagen": choose a target (VS
   Code first, opencode second), choose the aliases or derive them from a
   key, get a file to copy or download. Each target is **a small template
   as data**, not code. The key is never in the file — a placeholder and a
   sentence where it comes from. A consumer that holds a key can fetch its
   own file through `/v1` without asking the operator.

## 1. Facts (read 2026-11-20)

- **Reference app 0.10.1.** Tables `suppliers` (name, url, light, sealed
  credential) and `aliases` (name, targets, order). No property of a model
  is stored anywhere. `GET /v1/models` answers per key the reachable
  aliases with `oaap_light`, `oaap_light_meaning`, `oaap_data_rule`.
- **The probe** (§4.2) calls `GET <supplier>/v1/models` and keeps only the
  `id`s. "Aliases from a model list" builds one alias per picked id.
- **The platform's chat** reads `/v1/models` of its gateway and uses `id`
  and `oaap_light` (chat `app.py`). It knows nothing about context size or
  tool calling either.
- **The asset door** (RFC-0088) names each alias as `kind: model` with the
  suppliers it uses.
- **What suppliers report in their model list differs.** Some OpenAI-
  compatible suppliers add a context size or capability list to each
  entry, others return only ids; local runtimes often say more on a
  runtime-specific path than on `/v1/models`. Which supplier says what is
  **to be measured in stage 1** against the suppliers the fleet really
  uses, not assumed here.
- **Client formats move.** VS Code's custom-endpoint file
  (`chatLanguageModels.json`: per model `id`, `name`, `url`, `toolCalling`,
  `vision`, `maxInputTokens`, `maxOutputTokens`) changed behaviour between
  releases (reported: a model with `toolCalling: false` missing from the
  picker; models not shown without an extra setting in one release).
  opencode has an older `provider` form (`options.baseURL`, per model
  `limit.context`, `limit.output`, `tool_call`) and a newer `providers`
  form. goose has JSON "custom providers" whose `context_limit` was
  reported as not applied. **A template therefore carries the format
  version it was checked against and the date** (§3.2).

## 2. Stage 1 — properties on the alias

### 2.1 The four properties

| Property | Meaning | Example |
|---|---|---|
| `tools` | the model answers tool calls in the OpenAI form | `true` |
| `vision` | the model takes images in a request | `false` |
| `context` | tokens the model accepts as input | `128000` |
| `output` | tokens the model produces at most per answer | `8192` |

Each property is **set or unknown**. Unknown is a value of its own: it is
shown as "unbekannt", left out of `/v1/models`, and a template uses the
target's own default for it and says so. Nothing is filled in by guess.

### 2.2 On the alias, the weakest of its targets

Properties belong to the **alias**, because the alias is what a client
sees. An alias with several targets (a failover group, §3) gets per
property **the weakest value of its targets**: the smallest `context` and
`output`, `tools`/`vision` only if every target has it. The rule is the
light's rule (§7, "a chain may only ever get more dangerous") applied to
capability: a client must be able to rely on the value whichever target
answers. The operator sees the per-target values that produced it.

### 2.3 Where a value comes from

Every value carries its **origin**:

- `supplier` — read from the supplier's model list at a probe or at
  "aliases from a model list" (only the fields the supplier really
  returned);
- `test` — from the tool-call test (2.4);
- `operator` — typed by the operator.

A value from the operator is **never overwritten** by a later probe; a
probe that reports something different shows it as a difference to take
or leave. A value from `supplier` or `test` is refreshed by the next probe
or test.

### 2.4 The tool-call test

An optional button "Werkzeugaufruf probieren" on an alias: per target one
minimal request offering one harmless tool (`now`, no arguments) and
asking to call it, `max_tokens` small. A tool call in the answer → `tools:
true (test)`; a plain answer or a refusal of the `tools` field → `false
(test)`. Like the alias test (§4.2) it is not metered by this gateway and
the supplier counts it; it runs only on the operator's click, never on its
own, because it costs at the supplier.

### 2.5 Read by clients

`GET /v1/models` adds, per alias and only when set: `oaap_tools`,
`oaap_vision`, `oaap_context`, `oaap_output`. Clients that do not know the
fields ignore them (they are extensions in the same style as `oaap_light`).
The platform's chat can use `oaap_context` to cut a long conversation
before the supplier refuses it, and `oaap_tools` to offer the MCP tools
only where they can be called — both are chat changes outside this RFC.

The asset door adds the same four values to `kind: model` (RFC-0088 §8.2
whitelist, additive).

### 2.6 The setup door

The setup item `alias` accepts the four properties. The profile
`ki-arbeitsplatz` can then set them for its standard alias; an item from
the door has origin `operator` (it is a declaration by whoever wrote the
profile).

## 3. Stage 2 — client templates

### 3.1 The tab "Vorlagen"

1. **Target**: VS Code, opencode (more as templates arrive, §3.2).
2. **Models**: either **from a key** (the operator picks a key by its
   label; offered are the aliases that key may use and can reach under its
   ceiling — exactly the list `/v1/models` gives that key), or **picked by
   hand** from all aliases.
3. **Result**: the file, shown for copying and offered as a download, with
   a short text: where the file goes for this target, where the key
   comes from, which properties were unknown and what the target does
   then.

### 3.2 A template is data

A template is a JSON document in the app (`templates/<target>.json`):

- `target`, `title`, `format` (the client's format version it was checked
  against), `checked` (date);
- `file` (suggested file name and where it goes);
- `key_placeholder` (for VS Code an input variable, for opencode an
  environment variable reference);
- `skeleton` with one repeated block per model, using only the names
  `{id}`, `{name}`, `{url}`, `{tools}`, `{vision}`, `{context}`, `{output}`;
- `unknown` — per property, what the template writes when it is unknown
  (leave out, or the target's default with a comment).

A new client is a new file in a release of the app, not code. Templates
are not uploaded by operators in this RFC (D6).

### 3.3 The key is never in the file

The file holds a **placeholder** and the text says where the key comes
from (the key list, or whoever issued it). This holds on every path,
including the self-service path (3.4): the key the consumer sent is not
copied into the answer. A file that contains a secret ends up in a
repository sooner or later.

### 3.4 Self-service with a key

`GET /v1/oaap/client-config?target=<target>` with the key as usual
(`Authorization: Bearer …`) returns the file for **that** key's reachable
aliases. A person who received a key can then build their own file without
the operator's page. It reads nothing the key could not already read
through `/v1/models`.

### 3.5 The address

`{url}` is the gateway's public address with `/v1`, taken from the
instance's own address on the platform, falling back to the request's
host. A gateway reached through a chain gives its own address — the
consumer talks to the gateway it holds a key for.

## 4. Security and data

- No secret in any template output (3.3).
- The tool-call test sends a fixed text and a fixed tool, no content from
  any person.
- Properties are facts about models, not about persons; nothing new is
  recorded about consumers (§6 of the spec stays as it is).
- The self-service path is metered like `/v1/models` is today (not at
  all: no model computes).

## 5. Decisions

- **D1 Properties on the alias, weakest of its targets.** *Recommendation:*
  yes (§2.2). Alternative: on each supplier model — more exact, but a
  client never sees a supplier model, only an alias.
- **D2 The four fields** `tools`, `vision`, `context`, `output`.
  *Recommendation:* exactly these four now; others (reasoning, prompt
  caching, structured output) only when a template or the chat needs one.
- **D3 Unknown is a value; nothing guessed.** *Recommendation:* yes.
- **D4 Origin per value; an operator value is never overwritten.**
  *Recommendation:* yes (§2.3).
- **D5 Tool-call test on a click only.** *Recommendation:* yes, not
  metered by the gateway, never automatic (it costs at the supplier).
- **D6 Templates as data shipped with the app; no upload by operators.**
  *Recommendation:* yes for now; an upload would make a template a way to
  put arbitrary text into files people paste into their tools.
- **D7 First targets: VS Code, then opencode.** *Recommendation:* yes;
  goose only after its `context_limit` is measured to take effect.
- **D8 Models from a key or by hand.** *Recommendation:* both (§3.1);
  "from a key" uses the exact rule of `/v1/models`.
- **D9 Key placeholder, never the value.** *Recommendation:* yes, on every
  path (§3.3).
- **D10 Self-service path `/v1/oaap/client-config`.** *Recommendation:*
  yes in stage 2 (§3.4).
- **D11 Properties through the setup door; profile sets its standard
  alias.** *Recommendation:* yes (§2.6); the profile values come from a
  measurement of the supplier the profile names.
- **D12 Properties in `/v1/models` and the asset door.** *Recommendation:*
  yes, additive `oaap_*` fields (§2.5).

## 6. Stages and tests

- **Stage 1** — ai-gateway 0.11.0, `oaap.ai.gateway` 0.8: table of
  properties per alias (and per target, with origin), the page "Modelle"
  shows and edits them, probe proposes from the supplier list, tool-call
  test, `/v1/models` and asset door fields, setup door `alias` with
  properties. Measured first: what the suppliers on oaap-test and oaapx01
  actually return in their model lists (§1).
  Tests: weakest-of-targets per property; unknown stays unknown and is
  absent in `/v1/models`; an operator value survives a probe that reports
  differently and the difference is shown; the tool-call test with a stub
  supplier that calls the tool, one that answers plainly, one that refuses
  `tools`; setup door round trip with properties; old aliases without
  properties behave as before.
- **Stage 2** — ai-gateway 0.12.0, `oaap.ai.gateway` 0.9: tab "Vorlagen",
  templates VS Code and opencode, self-service path.
  Tests: a file from a key lists exactly the aliases `/v1/models` gives
  that key; no output on any path contains the key or any credential
  (searched for the key's text and for `sk-`); unknown properties follow
  the template's `unknown` rule; the generated VS Code and opencode files
  are valid JSON and are **loaded by the real client** once, by Jörg, on
  his machine (the client's own check is the measurement, not ours).

## Zusammenfassung auf Deutsch

**Worum es geht:** Wer die Modelle des KI-Gateways in VS Code oder
opencode nutzen will, schreibt die Konfiguration heute von Hand und muss
Dinge wissen, die er selten weiß: Kann das Modell Werkzeuge aufrufen?
Nimmt es Bilder? Wie viel passt hinein, wie viel kommt heraus? Das Gateway
weiß es auch nicht — es kennt je Modellname nur die Ziele und die Ampel.

**Stufe 1 — Eigenschaften am Modellnamen:** vier Angaben `tools`,
`vision`, `context`, `output`. Jede ist gesetzt oder „unbekannt“; geraten
wird nichts. Bei mehreren Zielen (Ausweichgruppe) gilt je Angabe das
schwächste Ziel — wie bei der Ampel, damit man sich darauf verlassen kann,
egal wer antwortet. Woher ein Wert kommt, steht dabei: vom Anbieter (aus
seiner Modellliste, wo er es sagt), aus dem Test „Werkzeugaufruf
probieren“ (nur auf Klick, kostet beim Anbieter ein paar Token) oder vom
Betreiber — ein Wert vom Betreiber wird nie überschrieben. Die Werte
stehen in `/v1/models` neben der Ampel (`oaap_tools` usw.), damit auch
unser Chat sie lesen kann, und die Einrichtungstür nimmt sie, damit ein
Profil sie setzen kann.

**Stufe 2 — Reiter „Vorlagen“:** Ziel wählen (zuerst VS Code, dann
opencode), Modellnamen wählen oder aus einem Schlüssel ableiten, Datei
kopieren oder herunterladen. Je Ziel eine kleine Schablone als Daten —
neue Werkzeuge ohne Code. Der Schlüssel steht nie in der Datei, nur ein
Platzhalter und ein Satz, woher er kommt. Wer einen Schlüssel hat, kann
sich seine Datei auch selbst holen (`/v1/oaap/client-config`), ohne die
Betreiberseite.

**Wichtig:** Die Formate der Werkzeuge ändern sich (bei VS Code und goose
gibt es gemeldete Fehler genau bei diesen Feldern). Jede Schablone sagt
deshalb, gegen welche Fassung und an welchem Tag sie geprüft wurde, und
die eigentliche Abnahme ist: du lädst die Datei einmal im echten Werkzeug.

**Zu entscheiden:** D1–D12, je mit Empfehlung (oben in §5). Die wichtigsten:
D1 Eigenschaften am Modellnamen mit „schwächstes Ziel“, D5 Werkzeugtest
nur auf Klick, D6 Schablonen nur mit der App ausgeliefert, D10
Selbstbedienung mit dem eigenen Schlüssel.
