# oaap.ai.gateway — AI Supply Behind One Keyed Endpoint

- **ID:** `oaap.ai.gateway`
- **Version:** 0.8.0 (**model properties and client templates**: four properties per alias -- `tools`, `vision`, `context`, `output` -- set or unknown, never guessed, the weakest of the alias's targets, each with its origin; in `/v1/models` as `oaap_*` and through the setup door; client files built from templates as data, the key only as a placeholder, and a self-service path `/v1/oaap/client-config`, §3.1, §3.2, §9 tests 15-17, RFC-0106; additive, reference ai-gateway 0.11.0). 0.7.0 (**built from a profile**: a setup door with the kinds `supplier`, `alias` and `client`, and a grant of kind `client` that authorises a chat of the platform through the via door without a key, the person never recorded; a grant may carry the context `tenant`, §7a, RFC-0104; additive, reference ai-gateway 0.10.1). 0.6.0 (a request may carry `X-OAAP-Light`, an additional ceiling for that request only that can tighten the key's ceiling and never loosen it -- the light a person chose for a chat conversation, RFC-0101; usage rows record it, §7, §9 test 12; additive. 0.5.3: a key that names aliases it can never reach under its ceiling is still issued, but the operator is told so, at issuing, at changing the aliases and in the key list, §7 (L14); a supplier that is always stripped of sampling parameters stores that, §4.2 (L15) -- reference app 0.8.1). 0.5.2 (the aliases of a valid key **may be changed** without a
  new secret, audited old → new, effective from the next request; light and
  release stay as issued, §2; additive. 0.5.1: a supplier may be marked to receive no sampling
  parameters, §4.2; additive. 0.5: keys may expire; keys issued for a cohort of a
  training in one step, shown once as the operator's own table; the
  operator may probe a supplier and take aliases from its model list,
  §2.1, §4.2; additive.
  0.4, RFC-0064 stage 3: one query behind the operator's
  charts and a report interface for external billing, `complete_until`
  in every answer, §5.1; additive.
  0.3.1, RFC-0064 stage 2: suppliers and aliases are
  maintained by the operator in the gateway itself, credentials at rest
  only encrypted with a key held outside the gateway's storage, §4.1.
  0.3: key context with four fixed dimensions, volume in bytes as well
  as tokens, a context snapshot on every usage record, no prices;
  additive except that the optional cost estimate of 0.2 §5 is struck)
- **Maturity:** draft
- **Based on:** RFC-0023 (supply, placement, entitlement); RFC-0022
  (account and tenant); RFC-0002 (default deny); RFC-0010 (public
  route brake); RFC-0019 (token hygiene: shown once, stored hashed,
  revocable); RFC-0021 (fleet key precedent for machine endpoints);
  RFC-0064 (volume and context)

## Purpose

A gateway offers **one OpenAI-compatible endpoint** downstream and
draws from one or more **suppliers** upstream: a local model runtime,
an external provider, or **another gateway**. It exists so that a
consumer — an app, a tenant, a laptop — asks for a *purpose*
(`chat-default`, `code`, `embedding-default`) and never for a vendor,
a model name or a URL.

Everything else in this document follows from that one property.
Rerouting, failover, data-protection routing and metering are all only
possible because the consumer does not name the model.

## 1. The route

An AI gateway is an ordinary OAAP app instance. Its API route is
declared `roles: [public]`, which means: the platform authenticates
nothing and strips client-sent identity headers; the app authorizes
every request itself (RFC-0002). The platform's per-client brake of
RFC-0010 applies and is charged **once per request**, so a streamed
answer is charged at setup, not per token.

| Method | Path                   | Purpose                                                       |
| ------ | ---------------------- | ------------------------------------------------------------- |
| `GET`  | `/v1/models`           | the **aliases** this key may use — never upstream model names |
| `POST` | `/v1/chat/completions` | completion, streaming and non-streaming                       |
| `POST` | `/v1/embeddings`       | embeddings                                                    |
| `GET`  | `/healthz`             | liveness, no key required, says nothing about suppliers       |

`GET /v1/models` returning aliases is what makes an off-the-shelf
client (LM Studio, an IDE plugin, a library) usable without adaptation:
the user picks `chat-default` from a list and never learns which
supplier served it.

A gateway **has no session, no cookie and no roles**, and it does not
consult the platform's identity service. It is a machine endpoint —
the third of the family named in RFC-0023 §3, alongside the deploy
hook (writes) and the fleet status (reads).

## 2. The API key is the identity

> For AI consumption, the identity is the **API key** — not the OAAP
> user, not the tenant.

- **Whoever operates a gateway issues its keys.** A right is given, not
  held (RFC-0019). A gateway that draws from an upstream holds exactly
  **one** key there, of its own; that key never reaches a consumer.
- The key value is shown **exactly once** at issue time; only its
  SHA-256 digest is stored. Listing shows labels and metadata, never
  key material.
- Every key carries a **context**: label, responsible person, and
  four fixed dimensions — **account, project, cost centre,
  application** — plus up to five free labels `name=value`. The context
  is free text to the operator, may be empty, and exists to make usage
  filterable and billable *outside* the gateway. The tenant assignment
  is not part of it: it is set by RFC-0022, `default` until then.
- The context **may be changed at any time**. Every change is audited
  with old and new value and takes effect from the next request.
- A key may be **restricted to a subset of aliases**. The subset **may be
  changed** while the key is valid (0.5.2) -- audited with old and new value,
  effective from the next request, the secret unchanged. Light and release
  for personal data are *not* changed with it: they bound where any alias of
  the key may lead. Keys of a cohort change together, not one by one.
- A key carries a **budget** and a **rate limit**. These are hard: they
  protect against a runaway bill, which an invoice afterwards does not.
- A key carries the **worst light it may use** and a **release for
  personal data** (§7). Both are decided when the key is issued.
- Issue and revoke are **audited**; requests are metered (§5) but their
  content is never recorded (§6).
- Every failure of authorization answers the **same 403 without
  detail**. Repeated failures are braked per client address.
- A key **may carry an end** (0.5). From then on it answers exactly like
  a revoked key — the same 403 — but a request with an expired key is
  **not counted as a guess**: it is a real key, and a classroom behind
  one address must not brake itself out after the course. An end may be
  moved (extended) until the key is revoked; revoking stays final.

### 2.1 Keys for a cohort (0.5)

A training needs one key per participant, all with the same end. A
gateway MAY issue them in one step:

- The operator pastes a table — one participant per line, cells
  separated by tab, semicolon or comma; the first cell is a name, an
  optional second cell a seat number (`07`) or a deviating seat
  (`07b`), further cells pass through. Without a number, seats are
  counted from a chosen first number.
- Every participant gets **an ordinary key** (§2): its own label, the
  name as the responsible person, the same end, the same aliases, light
  and budget, and the cohort's name in the context (project, unless
  given). The label follows the platform's cohorts (RFC-0046):
  `<cohort>-tn-<seat>`, so a participant's training server and key
  carry the same seat.
- The answer is **the same table with a column for the key** (and one
  for the seat, where the gateway chose or changed it), shown **once**,
  as a page and as a download, and never cached. Only the digests are
  stored, as for every key.
- A label is never issued twice, not even after a revoke. A participant
  who needs a new key gets a **deviating seat** (`07b`), given by the
  operator or taken as the next free one on request; a row whose seat is
  taken is answered with the reason, never silently skipped.
- A cohort can be **extended** (a new end for all its keys not revoked)
  and **revoked as a whole**, the latter only with an explicit "really".
  Both are audited.

## 3. Aliases, and failover inside a declared group

An **alias** names a purpose and maps to one or more suppliers. The
mapping is the operator's configuration, not the consumer's business.

- **Failover happens only inside an equivalence group declared by an
  administrator.** LLMs are not interchangeable the way web servers
  behind a load balancer are; silent substitution changes behaviour,
  sometimes subtly enough that nobody notices for weeks.
- A switch is **visible in the telemetry**: which supplier actually
  served a request is recorded per request and shown to the consumer
  who made it.
- A request naming something that is not an alias of this key is
  refused with the list of aliases it may use — a wrong model name is
  a configuration mistake, and configuration mistakes deserve an
  answer that fixes them.

### 3.1 Properties of an alias (0.8, RFC-0106)

A client needs facts about a model that the consumer rarely knows.
An alias carries four **properties**:

| Property | Meaning |
|---|---|
| `tools` | the model answers tool calls in the OpenAI form |
| `vision` | the model takes images in a request |
| `context` | the context window in tokens: input and output together |
| `output` | the most tokens the model produces in one answer |

- Each property is **set or unknown**. Unknown is a value of its own; a
  gateway MUST NOT fill it in by guess.
- Properties are kept per **target** (supplier and the supplier's model
  name). An alias has, per property, **the weakest value of its targets**:
  `false` if any target says `false`, otherwise unknown if any target is
  unknown; for numbers the smallest, but only when every target is known.
  A client must be able to rely on the value whichever target answers --
  the rule of the light (§7) applied to capability.
- Every value carries its **origin**: `supplier` (read from the
  supplier's model list, only fields the supplier really returned; a
  missing word in a capability list is not a `false`), `test` (a tool-call
  test, below) or `operator`. A local runtime that says nothing in its
  model list MAY be asked on its own description path (Ollama
  `/api/show`); a value the runtime does not serve -- a model's trained
  context length where the runtime serves a smaller window -- is not
  taken. A value from the operator is **never
  overwritten** by a later probe or test; what they report differently is
  shown beside it, to take or leave.
- The **tool-call test** runs only on the operator's click: per target
  one small request offering one harmless tool and asking to call it. A
  tool call in the answer is `true`, a plain answer `false`, a refusal
  naming the tools field `false`; any other failure sets nothing. It is
  not metered by this gateway; the supplier counts it.
- `GET /v1/models` adds, per alias and **only when set**, `oaap_tools`,
  `oaap_vision`, `oaap_context`, `oaap_output`. The setup door (§7a) takes
  them on an `alias` item as values of the operator; it does not
  overwrite a different value an operator set (`conflict`), and they do
  not count towards the item's digest.

### 3.2 Client files from templates (0.8, RFC-0106)

- A gateway MAY build the configuration file of a client tool (for
  example VS Code, opencode) for a set of aliases: picked by hand, or
  **derived from a key** -- then exactly the aliases `/v1/models` gives
  that key.
- A **template is data**, not code: the client's format version it was
  checked against and the date, the file name, where it goes, and the
  document with placeholders for the gateway's address, the alias and the
  four properties. An unknown property is left out with its field; the
  tool then uses its own default, and the gateway says which were
  unknown.
- **The key is never in the file**, on any path: the template carries the
  tool's own placeholder (an input variable, an environment variable)
  and a sentence where the key comes from.
- **Self-service:** `GET /v1/oaap/client-config?target=<tool>` with a key
  returns the file for that key's aliases. It reads nothing the key could
  not read through `/v1/models`; the key that asked is not copied into
  the answer. An unknown tool is `400` with the list of tools.

## 4. Suppliers, and chains

A supplier is **an OpenAI-compatible HTTP endpoint plus a
credential** — that is the entire model. A local runtime, an external
provider, a customer's own endpoint and another gateway are the same
kind of thing; they differ in address, credential and light (§7), not
in code. There is deliberately **no adapter framework** in this
version: a plugin architecture built before its second real case is a
guess wearing an interface.

A chain is therefore not a special construction either: **a gateway
has an upstream side and a downstream side, and an upstream may be
another gateway.**

A chain **proxies; it does not refer** (RFC-0023 A1). Traffic passes
through every layer, because every layer logs the access and meters
the consumption, and a layer that does not see the traffic can do
neither. Consequences, all accepted deliberately:

- latency adds up, and every layer is a point of failure for
  everything below it — therefore **chain length is the consumer's
  own trade-off**: keep it short, or host the supply yourself;
- **binding a gateway is never compulsory.** An external inferencing
  service is an equally legitimate supply for a tenant, and the
  platform is not on the path to it.

Upstream credentials **never leave the gateway** — not in an error
message, not in telemetry, not in a response header, not in the audit
log.

### 4.1 Maintenance (0.3.1, RFC-0064 stage 2)

- Suppliers and aliases are **maintained by the operator in the
  gateway** and take effect without a restart. There is **one** place
  that counts: a gateway that took them over from an earlier
  configuration MUST NOT keep reading that configuration.
- A credential is **write-only**: it can be set, replaced or removed,
  never read back. An empty input means *unchanged*, never *remove*.
- At rest, a credential is stored **only encrypted**, under a key that
  does not live in the gateway's own storage, so that a copy of that
  storage alone does not disclose it. Without such a key the gateway
  MUST refuse to store a credential and say why — and a takeover of
  credentials from an earlier configuration waits rather than store
  them in plain text or drop them.
- A credential that cannot be decrypted makes its supplier unusable,
  and the gateway names it. An alias that depends on it is unusable
  too — failing over around the gap would silently change the declared
  group (§3).
- A supplier still used by an alias cannot be removed.

### 4.2 Probing a supplier, and aliases from its model list (0.5)

- The operator MAY **probe** a supplier: `GET <supplier>/v1/models` with
  the supplier's credential. It lets no model compute and costs nothing,
  but shows whether the supplier is reached and accepts the credential.
  The answer is put in words: reached (with its models), credential
  refused (401/403), path unknown (404), the platform's tunnel not
  connected or the offer missing (`oaap.net.connector`), not reached
  (with the kind of error, never with the credential).
- An alias MAY be **tested** with a minimal request per target (one
  token at most). It is not metered by this gateway — there is no key it
  belongs to — and the supplier counts it.
- The operator MAY **create aliases from a supplier's model list**: pick
  models, accept or change the suggested names, create one alias per
  model with exactly that target. An existing alias is never
  overwritten by this.
- A supplier MAY be marked to **receive no sampling parameters**
  (`temperature`, `top_p`, `top_k`; 0.5.1): some suppliers refuse them
  (newer Claude models answer `400`), while many clients send them by
  default. The gateway removes exactly these fields on the way out and
  touches nothing else — it is a property of the supplier, not of the
  request, and it is not a look into the content (§6).
  (0.5.3, L15) For a supplier where the gateway always strips them
  (Anthropic), the setting is shown as fixed and **stored as on** -- a
  fixed form field is not submitted, and saving must not turn the stored
  value off.

## 5. Metering: each gateway keeps its own books

> Each gateway keeps the books for **the keys it issued**. An
> upstream's numbers are the upstream's truth and are not reconciled
> automatically.

Anything else invites silent double counting across three layers. A
tenant sees what its keys consumed; the node operator sees what the
tenant's gateway consumed from them; the two need not agree to the
token, and pretending they must would cost more than it is worth.

Recorded per request: time, key, alias, **supplier actually used**,
input and output token counts, **bytes up and down**, latency, the
outcome, and a **copy of the key's context**. Where a supplier reports
no token counts, the record says so rather than guessing.

- **Volume, never money.** A gateway counts calls, tokens and bytes. It
  does not price them; invoices and cost reports are produced outside
  from its numbers (RFC-0064).
- **Bytes are counted at the consumer side:** the request body the key
  holder sent and the response body they received — for a stream, the
  payload without transfer framing. Bytes are always known; tokens only
  when the supplier reports them. Both are kept so a gap in one stays
  visible next to the other.
- **The snapshot rule:** a usage record carries the key's context *as
  it was when the request began*. Changing a key's cost centre never
  moves past usage. Records that predate this rule may be filled once
  with the key's then-current context, and must say they were.

**Every consumer sees their own consumption, and only their own.** With
RFC-0022 in place, usage rolls up tenant → account, which is the view
RFC-0022 §7 measures.

### 5.1 Reporting (0.4, RFC-0064 stage 3)

- **One query.** Every view that shows volume — the operator's charts
  as much as the report interface — reads through the same query
  function. Two queries would disagree one day, and nobody could say
  which one is right.
- **Report interface:** `GET /report/v1/usage?from=…&to=…[&group_by=…]
  [&<dimension>=…][&format=csv]`. `from` inclusive, `to` exclusive, UTC.
  Dimensions: `account`, `project`, `cost_center`, `application`,
  `owner`, `key` (its label), `model` (the alias), `supplier`,
  `outcome`, `day`, `month`. Per group: `calls`, `in_tokens`,
  `out_tokens`, `calls_without_token_counts`, `bytes_up`, `bytes_down`,
  `calls_without_bytes`. Grouping and filtering use the context
  **copy** on the record (§5). An unknown parameter is refused, never
  ignored: a mistyped filter would otherwise bill everything.
- **`complete_until`** in every answer (a header for CSV): the time up to
  which the numbers are final. A record's time is the moment it is
  written, at the **end** of its request, so a period stops growing
  shortly after it ends; the margin covers the gap between stamping and
  storing.
- `GET /report/v1/keys`: the keys with their current context, never
  key material.
- **Access:** the route is the operator's (`admin`); an external system
  calls it with a platform API key of a machine principal (RFC-0027).
  A consumer key never opens it.

## 6. What a gateway must never record

**No prompt content, and no completion content, in any log — ever.**
Telemetry counts; the audit log records who routed where and when.
Prompts are the most sensitive payload this platform will ever carry,
and a log that holds them turns every backup and every support case
into a disclosure risk.

This is a conformance requirement, not a recommendation.

## 7. The traffic light: what a supplier does to your data

Every supplier carries a **light**. It does not describe quality,
speed or price — it describes **what can happen to the data you send**:

| light    | what it means                                                             | what may be sent                                                              |
| -------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `green`  | the data does not leave the organisation — the model runs on its own hardware | anything the consumer is otherwise allowed to hold; personal data **with an explicit release** |
| `yellow` | the data may leave the organisation, but to a provider under a binding commitment (contract, EU data centre, no training on the data) | company information; personal data **with an explicit release**                |
| `red`    | an external provider — the data can flow away                              | **no company information, no personal data** — public or synthetic input only  |

The light replaces a purely geographic classification on purpose:
where a machine stands is the *reason* for a light, never its
*meaning*. What an operator needs to decide is not "is this in the
EU?" but "what happens to my data here?"

### The light is enforced on declarations, never on content

The gateway **cannot see what a request contains** — §6 forbids it to
look, and that rule is not negotiable. Therefore the light can only be
enforced against **properties the consumer declared in advance**:

- every key carries the **worst light it may use** (default `yellow`,
  so `red` is a deliberate extra permission);
- every key carries a **release for personal data**, granted by
  whoever issued the key.

From those two the rule follows that the platform can actually keep:
**a key released for personal data may never use `red`.** Not because
red is forbidden in principle, but because we cannot tell one request
from another — and a rule that depends on the gateway recognising
personal data would be a promise it cannot keep.

Everything beyond that stays where it belongs: with the person who
sends the prompt. The platform is honest about the difference between
what it *enforces* and what it *documents*.

### A chain may only ever get more dangerous

> A declared light is a **ceiling, never a floor**. What a gateway
> offers downstream can never be greener than the worst link in the
> path it will actually use.

This is the rule that keeps a chain honest, and it is the reason the
light exists in both directions:

- **downstream**, `GET /v1/models` reports for every alias the light
  the *requesting key* would actually get — the worst light among the
  candidates that key may reach. An alias that can fail over from a
  green model to a red provider is **not green**;
- **upstream**, a gateway that draws from another gateway **reads that
  gateway's declared light and may not improve it**. Configuring
  `green` for a supplier that reports `red` does not make it green; the
  worse of the two wins.

Without this, a gateway becomes a laundry: put one in front of an
external provider, label it `green`, and every consumer downstream is
lied to by construction. The rule costs nothing and closes that.

### A key that can never reach an alias (0.5.3, L14)

When a key names aliases explicitly and every target of one of them lies
above the key's ceiling (or is `red` for a key cleared for personal
data), the key can never use that alias. The gateway still issues the
key -- the operator may raise a supplier's light later -- but it **says
so** when issuing, when the aliases are changed and in the key list,
naming the alias and the reason. `/v1/models` already leaves such an
alias out.

### A ceiling per request (0.6, RFC-0101)

A request may carry **`X-OAAP-Light: green | yellow | red`** — the light
the person behind a client chose for what they are about to send (in the
chat: the light of the conversation, default `green` for "sensitive and
personal data"). It is an **additional ceiling for this request only**:

- the ceiling of the request is the stricter of the key's ceiling and
  the header (`green` on a `yellow` key is `green`; `red` on a `yellow`
  key stays `yellow`) — the header can only refuse more, never allow
  more;
- a request whose alias has no target under the request's ceiling, while
  the key alone would have one, is refused with `503` and the code
  `conversation_light`, naming both lights; failover never crosses the
  request's ceiling, exactly as for the key's;
- `GET /v1/models` with the header lists only the aliases reachable
  under it, each with the light it would get;
- an unknown value is refused with `400` (`bad_light`), never ignored —
  whoever asks for a ceiling must not continue silently without it;
- the usage row records the requested light (`light`, empty without the
  header): a word from a fixed list, no content (§6).

The header is the client's statement, not an attestation. It protects
the person from a mistake; the key's ceiling remains the control.

### What the consumer must be able to see

The consumer must be able to see **the light of the alias it is using
and the supplier that actually served a request** (`GET /v1/usage`). A
policy the customer cannot verify is a promise, not a control.

Within an equivalence group a gateway prefers `green` before `yellow`
before `red`, and an operator who wants otherwise says so explicitly.
**Sovereignty is thus what happens when nobody configures anything** —
which is the only form of it that survives daily use.

## 7a. Built from a profile: the setup door and the grant for a chat (0.7, RFC-0104)

A tenant build (`oaap.core.tenant`, RFC-0055) may set a gateway up, and a
chat of the same tenant reaches it without an API key. Both are optional
for an implementation; a gateway that offers them declares them in its
manifest (`oaap.apps.runtime` 2.39).

### The setup door

- Declared as `setup: {path: <path>}`. The platform calls it with
  `Authorization: Bearer <OAAP_SETUP_KEY>` -- a value only the platform
  holds -- and `X-OAAP-Setup-Actor: <who started the build>`, which the
  gateway writes into its own audit as `setup:<who>`. Without the key the
  door is `403`, whatever identity headers come with the call; without
  `OAAP_SETUP_KEY` in its environment, every call is `403`.
- The calls, results and the "never overwrite what a human made" rule are
  those of RFC-0104 §3.1 (`present`, `made`, `would_make`, `conflict`,
  `refused`, `removed`, `gone`). A field named like a secret (`key`,
  `token`, `secret`, `password`, `credentials`, `credential`, `api_key`)
  is `refused`: credentials are typed by a human on the gateway's page.
- Kinds:

| Kind | Item | `ready` |
|---|---|---|
| `supplier` | `{"id", "url": "https://…/v1", "light"}`, **without** credentials | credentials stored **and** the supplier's test answers 2xx now |
| `alias` | `{"id": <model name>, "supplier", "model"}`, exactly one target | the name routes |
| `client` | `{"id": <chat instance key>, "aliases": [...], "ceiling", "personal_data", "tenant"?}`, the grant below | not revoked, not expired |

- `remove` takes back only what setup made and only while it is still
  as made (a digest of the item as the gateway read it after making it).
  A supplier for which a human has stored credentials stays (`conflict`:
  only a human deletes those); a model name still named by a key or grant
  that is not revoked stays; a grant that already has usage rows is
  revoked instead of deleted, so its usage keeps an owner.

### The grant for a chat

- A row of kind `client` in the key table, label = the chat instance's
  node key, **without** a usable digest: no bearer value matches it, and
  the key lookup never returns it.
- A request counts as one through the platform's via door only when all
  three are present: `X-OAAP-AI-Client` (set by the door), `X-OAAP-User-Id`
  and `X-OAAP-User-Assertion`. The platform strips the identity headers on
  the public `/v1`, so `X-OAAP-AI-Client` alone takes the ordinary path
  over the API key. A client without a usable grant gets the same `403` as
  an unknown key, and it is not counted as a failed attempt.
- The grant's model names, ceiling, personal-data release, budget and
  rate apply exactly as for a key (§2, §7). Its usage rows carry the
  grant's `key_id` and context like any key's (§5).
- **The person is never recorded** (§6): it is checked for presence only.
- **Context `tenant` (0.7).** An optional `tenant` on the `client` item is
  the grant's context "tenant" and so stands in every usage row of the
  chat; without it the context is `default`, as for a key issued without
  one. It is compared only when the item names it, so a grant made before
  is unchanged. Measured on kit1 (oaapx01, 2026-11-19): without it every
  row said `default`.

## 8. Errors

| Situation                          | Answer                                                            |
| ---------------------------------- | ----------------------------------------------------------------- |
| missing, unknown, revoked key      | `403`, no detail, braked                                          |
| alias not permitted for this key   | `400` with the permitted aliases                                  |
| rate limit hit                     | `429` with `Retry-After`                                          |
| budget exhausted                   | `429` **without** `Retry-After` — waiting does not help, only a new budget |
| no supplier in the group available | `503`, naming the alias, never the upstream credential            |
| upstream failed                    | `502`, with the supplier's own status where it is safe to pass on |

## 9. Conformance tests

1. A request without a key, with an unknown key and with a revoked key
   receive the identical 403.
2. A key restricted to `chat-default` is refused `code`, and the
   refusal lists what it may use.
3. `GET /v1/models` returns aliases only; no upstream model name and
   no supplier name appears in the response.
4. A streamed answer is charged once by the RFC-0010 brake.
5. Budget exhaustion answers 429 and does **not** reach the supplier.
6. A failover inside a declared group is recorded with the supplier
   actually used; a failover to a light the consumer forbids does not
   happen.
6a. `GET /v1/models` reports for each alias the worst light the
   requesting key would actually reach — an alias that may fail over
   to `red` is not reported as `green`.
6b. A key released for personal data is refused every `red` supplier,
   even when its own ceiling says `red`.
6c. A supplier configured `green` that reports `red` upstream is
   treated as `red`; the worse of the two wins.
7. No log file produced by the gateway contains prompt or completion
   text, in any operating mode.
8. An upstream credential appears in no response, no error and no
   telemetry record.
9. Key issue and revoke appear in the audit log; individual requests
   do not.
9a. A change of a key's context is audited with old and new value;
   usage recorded before the change keeps the old context, usage after
   it carries the new.
9b. `bytes_up` and `bytes_down` of a request equal the body sizes the
   consumer sent and received, streamed or not.
9c. A credential set through maintenance appears in no file of the
   gateway's storage in plain text, and in no page, response or audit
   entry.
9d. The numbers on the operator's charts and those of
   `/report/v1/usage` for the same period and filters are equal.
9e. A record stamped at the last second of a period belongs to it, one
   stamped at the first second of the next does not; an answer for a
   period that can still grow says so (`complete: false`).
10. A gateway drawing from another gateway holds exactly one key
    there; that key never appears downstream.
11. Changing the aliases of a valid key (0.5.2) takes effect on the next
    request with the same secret: `/v1/models` lists the new subset, a
    removed alias answers `400` with the permitted ones, the audit log
    names old and new; an unknown alias or a revoked key is refused and
    nothing changes.

12. With `X-OAAP-Light: green` a key with ceiling `yellow` gets `503`
    (`conversation_light`) for an alias that only reaches `yellow`, and the
    supplier is not called; the same request with `green` to a green alias
    succeeds and its usage row records `light = green`; **bait:** `red` on
    a key with ceiling `yellow` does not reach a red alias; an unknown
    value is `400` (0.6).

13. The setup door without `OAAP_SETUP_KEY` is `403`, also with identity
    headers of an administrator; with it, the same POST gives `made` then
    `present`; a `supplier` item with a field `key` is `refused`; a
    supplier for which a human stored credentials is a `conflict` on
    `remove` and stays (0.7).
14. A request through the via door with all three headers is authorised
    by the chat's grant and its usage row carries the grant's `key_id`
    and, if set, its `tenant`; **bait:** `X-OAAP-AI-Client` alone, or a
    grant's digest sent as bearer, gets `403`; the person's id is found
    nowhere on disk (0.7).
15. An alias over two targets reports the weakest value per property in
    `/v1/models`; an unknown property is absent; **bait:** a missing word
    in a supplier's capability list does not become `false` (0.8).
16. An operator value survives a probe that reports differently, and the
    report is shown beside it; the tool-call test sets `true` for a tool
    call, `false` for a plain answer, nothing for a failure, and creates
    no usage row (0.8).
17. A client file derived from a key lists exactly that key's aliases of
    `/v1/models`; **bait:** neither the key that asked, nor any other key,
    nor a supplier credential appears in any file or page built by §3.2
    (0.8).

## 10. Dependencies

- `oaap.apps.runtime` — the gateway is an app instance with a public
  route, declared configuration and declared mounts;
- `oaap.core.gateway` — default deny and the RFC-0010 brake;
- RFC-0022 stage 2 for account/tenant metadata on keys. Until then the
  assignment reads `default`, which is a real value, not a placeholder
  to be filled in later by hand.

## Non-goals (version 0.1)

- No training, no fine-tuning, no model management beyond aliases.
- No cost reconciliation across layers (§5).
- No prompt content anywhere (§6).
- No automatic failover outside a declared equivalence group (§3).
- No entitlement derived from an OAAP session — the key is the
  identity (§2).

## Zusammenfassung auf Deutsch

Ein KI-Gateway bietet **einen OpenAI-kompatiblen Endpunkt** an und
bedient sich bei einer oder mehreren **Bezugsquellen**: lokales
Modell, externer Anbieter oder **ein anderes Gateway**. Der Verbraucher
fragt nach einem **Zweck** (`chat-default`, `code`) und nie nach einem
Hersteller, Modellnamen oder einer URL. Alles Weitere folgt daraus:
Umleiten, Ausweichen, Datenschutz-Routing und Abrechnung sind nur
möglich, weil der Verbraucher das Modell nicht benennt.

**Technisch ist es eine gewöhnliche OAAP-App** mit einer `public`-Route
— die Plattform authentifiziert nichts, entfernt gefälschte
Identitäts-Kopfzeilen und bremst je Client (RFC-0010, einmal pro
Anfrage, Streaming also unbelastet). Die App prüft selbst: **Der
API-Key ist die Identität**, keine Sitzung, keine Rollen, kein Kontakt
zum Identitätsdienst. Damit ist das Gateway der dritte Vertreter der
Maschinen-Endpunkt-Familie neben Deploy-Hook und Flotten-Auskunft.

`GET /v1/models` liefert **die Aliasse**, nicht die Modellnamen der
Quelle — genau das macht LM Studio oder ein IDE-Plugin ohne Anpassung
benutzbar: Man wählt `chat-default` aus einer Liste und erfährt nie,
wer geantwortet hat.

**Schlüssel:** ausgestellt von dem, der das Gateway betreibt, einmal
angezeigt, nur als SHA-256 gespeichert, jederzeit widerrufbar; mit
einem **Kontext** (seit 0.3: Verantwortlicher, Account, Projekt,
Kostenstelle, Anwendung, bis zu fünf freie Etiketten — jederzeit
änderbar, jede Änderung in der Prüfspur), optional auf einzelne Aliasse
beschränkt, mit **Budget und Rate-Limit als harter Grenze**. Ein
Gateway, das sich bei einem anderen bedient, hält dort **genau einen
eigenen** Schlüssel, der nie nach unten durchgereicht wird.

**Auswertung (seit 0.4):** Grafiken auf der Betreiber-Seite und die
Schnittstelle `GET /report/v1/usage` für externe Rechnungen und
Kostenberichte lesen über **dieselbe Abfrage**. Gruppiert und gefiltert
wird nach der Kontext-Kopie in der Messzeile; jede Antwort sagt mit
`complete_until`, bis wann die Zahlen endgültig sind. Ein unbekannter
Parameter wird abgelehnt, nie übergangen. Abgefragt wird mit einem
Plattform-API-Schlüssel eines Maschinen-Benutzers (RFC-0027), nie mit
einem Gateway-Schlüssel. Volumen, keine Preise.

**Die Ampel (§7) sagt, was mit den Daten geschehen kann** — nicht, wo
ein Rechner steht: **grün** die Daten verlassen das Unternehmen nicht;
**gelb** sie verlassen es vielleicht, aber zu einem Anbieter unter
verbindlicher Zusage; **rot** externer Anbieter, Daten können
abfließen — keine Unternehmensinformationen, keine personenbezogenen
Daten. Der Standort ist der *Grund* für eine Farbe, nie ihre
*Bedeutung*.

**Durchgesetzt wird an Erklärungen, nie am Inhalt.** Das Gateway darf
nicht hineinsehen (§6), also kann es nur prüfen, was vorher erklärt
wurde: je Schlüssel die **schlechteste erlaubte Farbe** (voreingestellt
gelb, rot ist Zusatzerlaubnis) und eine **Freigabe für personenbezogene
Daten**. Daraus folgt die eine Regel, die die Plattform wirklich halten
kann: **Ein für personenbezogene Daten freigegebener Schlüssel darf
niemals rot benutzen.** Alles Weitere bleibt bei dem, der den Prompt
abschickt — und die Spec ist ehrlich über den Unterschied zwischen dem,
was sie *durchsetzt*, und dem, was sie *dokumentiert*.

**Eine Kette kann nur gefährlicher werden, nie ungefährlicher.** Eine
erklärte Farbe ist eine **Obergrenze, nie eine Untergrenze**: Was ein
Gateway nach unten anbietet, kann nie grüner sein als das schlechteste
Glied der Kette, die es tatsächlich benutzt. Deshalb wirkt die Ampel in
beide Richtungen — nach unten meldet `GET /v1/models` je Alias die
Farbe, die *dieser Schlüssel* wirklich bekäme (ein Alias, der von einem
grünen Modell auf einen roten Anbieter ausweichen kann, ist nicht
grün), und nach oben liest ein Gateway die Farbe seiner Bezugsquelle
und darf sie **nicht verbessern**. Ohne diese Regel wird ein Gateway
zur Wäscherei: eins davorstellen, `grün` dranschreiben, und alle
darunter sind von Bauart wegen belogen.

**Souveränität ist die Standard-Reihenfolge, kein bloßer Filter:**
Innerhalb einer Ausweich-Gruppe gilt grün vor gelb vor rot — wer es
anders will, sagt es ausdrücklich. Souveränität ist damit das, was
passiert, wenn niemand etwas einstellt; jede andere Form überlebt den
Alltag nicht. Eine Bezugsquelle ist dabei **immer dasselbe**: ein
OpenAI-kompatibler Endpunkt plus Zugangsdaten — lokal, extern, beim
Kunden oder ein anderes Gateway. Einen Adapter-Baukasten gibt es
bewusst nicht, solange wir den zweiten echten Fall nicht kennen.

**Ausweichen nur innerhalb einer erklärten Gruppe** — LLMs sind nicht
austauschbar wie Webserver hinter einem Lastverteiler; stilles
Ersetzen ändert das Verhalten, manchmal so leise, dass es wochenlang
niemand merkt. Welche Quelle tatsächlich geantwortet hat, steht in der
Telemetrie und ist für den Verbraucher sichtbar.

**Abrechnung:** Jedes Gateway führt Buch über die Schlüssel, die es
selbst ausgegeben hat; die Zahlen der Bezugsquelle sind deren Wahrheit
und werden nicht abgeglichen. Alles andere lädt zu stiller
Doppelzählung über drei Schichten ein.

**Und die härteste Regel:** In keinem Protokoll stehen jemals Prompts
oder Antworten. Gezählt wird, nicht mitgeschrieben — sonst wird jede
Sicherung und jeder Supportfall zum Datenleck. Das ist eine
Konformitätsbedingung, keine Empfehlung.

**Neu in 0.3 (RFC-0064):** Gezählt wird **Volumen, nie Geld** — Aufrufe,
Token (wenn die Quelle sie nennt) und **Bytes hoch/runter** am
Verbraucher. Jede Messzeile trägt eine **Kopie des Kontexts** zum
Zeitpunkt der Anfrage, wie ein Beleg seine Kontierung behält. Die
optionale Kostenschätzung aus 0.2 ist gestrichen; Rechnungen entstehen
außerhalb.

**Neu in 0.3.1 (RFC-0064 Stufe 2):** Bezugsquellen und Aliasse pflegt
der Betreiber **im Gateway selbst**, wirksam ohne Neustart; was aus
einer früheren Konfiguration übernommen wurde, wird dort nicht mehr
gelesen. Zugangsdaten sind nur schreibbar, nie lesbar, und liegen nur
**verschlüsselt** — mit einem Schlüssel, der nicht im Speicher des
Gateways liegt. Fehlt er, verweigert das Gateway das Speichern und
sagt warum.

### Nachtrag 0.5 (Deutsch)

**Ablauf und Kohorten:** Ein Schlüssel kann ein Ende haben. Danach
antwortet er genau wie ein widerrufener (dieselbe 403), zählt aber nicht
als Rateversuch. Für Schulungen stellt das Gateway in einem Schritt je
Teilnehmer einen gewöhnlichen Schlüssel aus: Der Betreiber fügt eine
Tabelle ein (Name, optional Nummer oder abweichende Kennung, weitere
Spalten werden durchgereicht) und bekommt dieselbe Tabelle mit einer
Schlüsselspalte zurück, einmal angezeigt und nie zwischengespeichert. Die
Etiketten folgen den Schulungsservern (`<kohorte>-tn-<nummer>`, RFC-0046).
Ein Etikett wird nie zweimal vergeben, auch nach einem Widerruf nicht.
Wer nachgeneriert, nimmt eine abweichende Kennung (`07b`). Eine Kohorte
lässt sich verlängern und als Ganzes widerrufen, Letzteres nur mit
„wirklich“.

**Bezugsquelle prüfen und Modellnamen übernehmen:** Der Betreiber kann
eine Quelle anpingen (`GET …/v1/models` mit ihren Zugangsdaten, nichts
wird gerechnet). Das Ergebnis steht in Worten da: erreichbar, Anmeldung
abgelehnt, Pfad unbekannt, Tunnel oder Angebot fehlt, nicht erreichbar.
Ein Modellname lässt sich mit einer Mini-Anfrage testen, die nicht in
den eigenen Verbrauch zählt. Aus der Modellliste einer Quelle legt der
Betreiber per Mehrfachauswahl Modellnamen an; vorhandene werden nie
überschrieben.

**0.5.1:** Eine Bezugsquelle kann so markiert werden, dass sie
`temperature`, `top_p` und `top_k` nicht bekommt. Neuere Claude-Modelle
lehnen diese Felder mit 400 ab, viele Werkzeuge schicken sie trotzdem.
Das Gateway entfernt genau diese Felder und sonst nichts.

**0.5.2:** Die Modellnamen eines gültigen Schlüssels lassen sich ändern,
ohne einen neuen Schlüssel auszustellen -- das Geheimnis beim Verbraucher
bleibt. Die Prüfspur nennt alt und neu, die Änderung gilt ab der nächsten
Anfrage. Ampel und Freigabe für personenbezogene Daten bleiben, wie beim
Ausstellen entschieden. Anlass: bec am 18.11., ein neuer Modellname war dem
Schlüssel des Chats nicht erlaubt (L26).

### Nachtrag 0.5.3 (Deutsch, L14/L15)

Nennt ein Schlüssel Modellnamen, die er wegen seiner Obergrenze nie
erreicht, wird er weiter ausgestellt, aber das Gateway sagt es: beim
Ausstellen, beim Ändern der Modellnamen und in der Schlüsselliste, mit Name
und Grund. Bei Anthropic ist „temperature/top_p nicht weitergeben“ fest an;
das wird jetzt auch so gespeichert -- vorher kippte das Speichern den Wert,
weil der Browser ein gesperrtes Feld nicht mitschickt.

### Nachtrag 0.6 (Deutsch, RFC-0101 Stufe 1)

Eine Anfrage darf `X-OAAP-Light: green|yellow|red` mitschicken. Das ist eine
**zusätzliche Decke nur für diese Anfrage**, die Ampel, die die Person im Chat
für ihr Gespräch gewählt hat. Es gilt die strengere aus Schlüssel und
Kopfzeile. Die Kopfzeile kann also nur mehr ablehnen, nie mehr erlauben.
Sperrt nur die Ampel des Gesprächs, antwortet das Gateway mit 503
`conversation_light` und nennt beide Farben. `/v1/models` zeigt dann nur die
erreichbaren Namen. Ein unbekannter Wert wird mit 400 abgelehnt. Die
Messzeile hält die verlangte Farbe fest (Spalte `light`, kein Inhalt).

### Nachtrag 0.7 (Deutsch, RFC-0104)

Neuer Abschnitt §7a: Ein Gateway lässt sich beim Aufbau eines Mandanten
aus einem Profil **einrichten**, und ein Chat desselben Mandanten erreicht
es **ohne API-Schlüssel**.

- **Einrichtungstür:** Die Plattform ruft sie mit einem Schlüssel, den nur
  sie hält (`OAAP_SETUP_KEY`). Ohne diesen Schlüssel ist die Tür zu, auch
  für eine Verwaltung. Sie kennt drei Arten: Bezugsquelle (ohne
  Zugangsdaten, die tippt ein Mensch), Modellname und Freigabe für einen
  Chat. Was ein Mensch geändert hat, wird nie überschrieben und beim
  Rückbau nicht entfernt.
- **Freigabe für einen Chat:** eine Zeile der Art `client` ohne
  benutzbaren Schlüsselwert. Ein Aufruf gilt nur dann als einer über die
  Tür der Plattform, wenn drei Kopfzeilen da sind: Chat, Kennung der
  Person und ihre Zusicherung. Modellnamen, Ampel, pbD-Freigabe, Budget
  und Rate wirken wie bei einem Schlüssel. Die Person wird nie
  gespeichert.
- **Mandant an der Freigabe:** Das optionale Feld `tenant` setzt den
  Kontext „Mandant“. Dann steht er in jeder Messzeile des Chats. Ohne das
  Feld steht dort `default`, so wie bei kit1 am 19.11. gemessen.

### Nachtrag 0.8 (Deutsch, RFC-0106)

- **Eigenschaften je Modellname:** Werkzeuge, Bilder, Kontextfenster (Ein-
  und Ausgabe zusammen) und größte Ausgabe. Gesetzt oder unbekannt, nie
  geraten; bei mehreren Zielen das schwächste. Herkunft je Wert: Quelle,
  Test oder Betreiber; ein Betreiberwert wird nie überschrieben. Der Test
  „Werkzeugaufruf probieren“ läuft nur auf Klick. `/v1/models` zeigt die
  gesetzten Werte als `oaap_*`, die Einrichtungstür nimmt sie an.
- **Vorlagen für Clients:** Die Konfigurationsdatei eines Werkzeugs (VS
  Code, opencode) aus einem Schlüssel oder von Hand gewählten Modellnamen;
  Vorlagen sind Daten mit geprüfter Formatfassung. Der Schlüssel steht nie
  in der Datei. Mit dem eigenen Schlüssel holt man sich die Datei selbst
  über `/v1/oaap/client-config`.

