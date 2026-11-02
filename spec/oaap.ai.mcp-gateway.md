# oaap.ai.mcp-gateway — Tool Servers Behind One Keyed Endpoint per View

- **ID:** `oaap.ai.mcp-gateway`
- **Version:** 0.2 (RFC-0065 stages 1 and 2: views that bundle tools,
  resources, resource templates and prompts of several servers under
  their own names, with fixed arguments and bounds; server-to-client
  requests configurable per view; technical access, keys, catalog with
  default deny and pinned descriptions, effect classes, protection
  limits, usage and report; §14 A1–A4; deliberate answer to MCP
  `2026-07-28` clients). 0.1 of 2026-11-02 was stage 1 alone.
- **Maturity:** draft
- **Based on:** RFC-0065 (the MCP gateway), RFC-0064 and
  `oaap.ai.gateway` 0.4 (keys, context, volume, report, vault — shared
  module), RFC-0033 and `oaap.net.destinations` (reaching outward),
  RFC-0068 (closed egress), RFC-0002 (default deny), RFC-0010 (public
  route brake), RFC-0019 (token hygiene)
- **Implemented by:** `oaap-apps/apps/mcp-gateway`

## Purpose

AI clients — Claude Code, Copilot, a company's own agent — call **MCP
servers** directly: tool servers that read and change systems. The
gateway puts those servers behind **one endpoint per view**. A consumer
gets a key for named views; every tool call is checked, limited and
metered with a copy of the key's context. The client sees one MCP
server per view and never learns which server stands behind it, or
where.

Version 0.2 covers **views across several servers** (bundles) with
tools, resources and prompts, and **technical access** (procedure T).
Sign-in of a person and carrying that person through to the backend
follow in later versions (RFC-0065 §11).

## 1. Routes

| Path | Role in the manifest | Who |
|---|---|---|
| `/mcp/<view>` | `public` | MCP clients, with a gateway key (§2) |
| `/report/v1/…` | `admin` | a billing system with a platform API key (RFC-0027) |
| `/` and everything else | `admin` | the operator |
| `/healthz` | — | the platform |

`/mcp/<view>` is `public`: the platform authenticates nothing there,
strips client-sent identity headers and brakes per client address
(RFC-0010). The gateway authorizes every request itself.

## 2. The key is the identity

- A key is shown **once**, stored only as SHA-256, revocable; its value
  starts with `mcp-oaap-`. Taken over from `oaap.ai.gateway` §2
  through the shared module: the same context (owner, account,
  project, cost centre, application, up to five labels), the same audit
  of every change with old and new value.
- A key names the **views** it may use. **No view named means no view**
  — unlike the AI gateway, where an empty list means all aliases. A
  tool server reaches into systems; nothing is reachable by default.
- A key carries the **highest effect class** it may use (§5.2, default
  `read`), the **worst light** it may use (§3.3, default `yellow`), a
  **rate** (requests per minute) and a **budget** in tool calls (0 = no
  limit).
- No key, an unknown key and a revoked key get **the identical answer**:
  `403` with the same body. A key that is valid but not entitled to the
  view gets the same `403`. Whoever probes learns nothing.
- Five failed attempts from one address within five minutes are
  answered with `429` for the rest of the window.

## 3. Servers

A server is an MCP endpoint speaking **Streamable HTTP**. stdio is not
supported (RFC-0065 D2).

| Field | Meaning |
|---|---|
| name | `[a-z0-9-]`, unique; shown to the operator, never to a client |
| address | an `http(s)://` URL, or `destination:<need>` (§3.1) |
| access | procedure **T**: `none`, `bearer`, `basic` or `header:<Name>`; the credential is stored only encrypted (§3.4) |
| light | `green`, `yellow`, `red` — what the server does with data sent to it (`oaap.ai.gateway` §7) |
| limits | §8 |

### 3.1 Addresses: only through the platform's egress (A4)

- **`destination:<need>`** resolves to the instance's
  `OAAP_DESTINATION_<NEED>_URL` (`oaap.net.destinations` §2.3). The
  platform then adds the destination's authentication; the gateway
  holds no secret, and a server with a destination address **must not**
  carry its own credential (one truth, not two). A destination that is
  not bound makes the server unavailable, with a sentence saying which
  need is missing.
- **A URL** is reached as the instance may reach it under RFC-0068. It
  must not contain user information (`user:pass@`).
- The gateway **never follows a redirect**; a `3xx` from a server is an
  upstream error. It **never connects to an address it reads from a
  server's answer**. In 0.2 there is no other address than the one
  configured; procedure X (0.3) will take its OAuth endpoints from
  destinations as well.
- Addresses that resolve to **loopback, link-local (169.254.0.0/16,
  fe80::/10) or unspecified** addresses are refused when saving and
  again when connecting. Private ranges are allowed: the operator named
  them (an app on the same node, a server in the LAN).

Reason: a gateway that follows addresses it is given is a tool for
reaching what the caller cannot reach (server-side request forgery).

### 3.2 Protocol versions, per direction (A3)

The gateway speaks a fixed list of **tested** MCP protocol versions:
`2025-03-26`, `2025-06-18`, `2025-11-25`.

- **Toward a server** it offers its newest tested version at
  `initialize`. A server that answers a version **outside** the list is
  not used: the call fails as an upstream error, and the operator page
  names the version the server offered — also when a server of the
  `2026-07-28` era rejects `initialize` and names its versions in the
  error. The negotiated version is shown
  per server and sent as `MCP-Protocol-Version` on every later request
  to that server.
- **Toward a client** it negotiates as the MCP specification
  prescribes: the client's version if tested, otherwise the newest
  tested version. A later request whose `MCP-Protocol-Version` header
  differs from the negotiated version is answered with `400`.
- The two are independent: a client on `2025-11-25` and a server on
  `2025-03-26` work together. What the gateway produces itself
  (`tools/list`, §6) is shaped for the client's version.

### 3.3 The light

The light of a view is the **worst light of the servers** it contains
(RFC-0065 §9.3: a view is never greener than its worst server). A key
may use a view
only if the view's light is not worse than the key's light
(`green` < `yellow` < `red`); otherwise the view answers like an
unknown one. The gateway enforces the light on what it **sends**
(arguments); results flow into the client's model, which the gateway
does not see (RFC-0065 §9.3) — the operator page says so.

### 3.4 Credentials

Stored only encrypted, under a key outside the gateway's storage
(`MCPGW_MASTER_KEY`, `oaap.ai.gateway` §4.1, shared module): set,
replace or remove; never shown again, never in an answer, an error, a
log line or a usage record. A server credential is sent only to that
server's address.

## 4. The catalog: default deny, pinned

### 4.1 Reading

The gateway reads what each server offers into a **catalog**, in four
kinds, each page by page and at most 1000 entries per kind:

| Kind | Read with | Identified by | Fingerprint covers |
|---|---|---|---|
| tool | `tools/list` | `name` | name, title, description, input schema, output schema, annotations |
| resource | `resources/list` | `uri` | uri, name, title, description, mime type, annotations |
| resource template | `resources/templates/list` | `uriTemplate` | uri template, name, title, description, mime type, annotations |
| prompt | `prompts/list` | `name` | name, title, description, arguments |

A kind is read only if the server names its capability at
`initialize` (`tools`, `resources`, `prompts`). A server that **no
longer** names a capability offers nothing of that kind: what of it
lies in a view becomes `missing` (§4.2), it does not stay listed with
an old text. The `size` of a resource is not part of the fingerprint:
it changes with the content, and the content is none of the gateway's
business.

The gateway reads on the operator's demand and on its own every
`MCPGW_CATALOG_MINUTES` (default 15).

An entry in the catalog is **not** exposed. Only a view exposes it
(§5). A server that adds an entry adds nothing to any view.

### 4.2 Fingerprint and suspension

The **fingerprint** of an entry is the SHA-256 of the canonical JSON
(sorted keys, no whitespace) of the fields in §4.1.

When the operator puts an entry into a view, the gateway stores the
**approved snapshot**: the fingerprint and the full text at that
moment. Then:

| Catalog says | State in every view | Effect |
|---|---|---|
| same fingerprint | `active` | listed and callable |
| different fingerprint | `suspended` | neither listed nor callable, until the operator confirms; the operator page shows old and new side by side |
| entry gone, or its kind no longer offered | `missing` | neither listed nor callable |

**Clients only ever see the approved snapshot**, never the server's
current text. A changed description reaches no model before the
operator confirmed it (RFC-0065 §4.2, "rug pull").

## 5. Views

A view has a name (`[a-z0-9-]`, the path segment), a **highest effect
class** (default `read`), a setting for **server-to-client requests**
(§6.1) and a list of **entries**. An entry is one catalog entry of
**any** server, under a **name of the view**. Entries of several
servers in one view form a **bundle** (RFC-0065 §3); the client sees
one MCP server and never learns which server answers which call.

### 5.1 Approval and names

Putting an entry into a view is an approval (§4.2).

- **Tools and prompts** get a name in the view: by default the
  server's name if it is free in the view, otherwise
  `<server>_<name>`; the operator may choose another. Names follow MCP's
  recommendation (`[A-Za-z0-9_.-]`, 1–128 characters) and are unique per
  kind within a view. A name that is taken is **refused when saving**,
  never resolved silently — not by numbering, not by overwriting.
- **Resources** keep their URI, **resource templates** their URI
  template. The same URI or template from two servers in one view is
  refused like a taken name.
- The operator may **replace the description** of an entry. The
  replacement is the operator's text, not the server's; the pinned
  snapshot and its fingerprint stay those of the server.
- A tool whose input schema refers to anything outside itself (a `$ref`
  not starting with `#`) is refused: it cannot be checked (§7). A
  resource template with operators other than `{x}` and `{+x}` (RFC 6570
  levels 1 and 2 without the other operators) is refused: whether a URI
  matches it cannot be decided unambiguously.

Changing the server of an entry is not possible; the operator removes
it and adds the other.

### 5.2 Effect classes

The operator assigns every tool in a view an **effect class**: `read`,
`write` or `execute` (irreversible, or with effects outside the system).
The server's own annotations (`readOnlyHint`, `destructiveHint`) are
**shown as a hint and never enforced**. Resources and prompts are
always `read`: reading them changes nothing.

An entry is listed and callable for a key only if its class is not
higher than **both** the view's highest class and the key's highest
class (`read` < `write` < `execute`).

### 5.3 Fixed arguments and bounds

For a tool in a view the operator may set:

- **Fixed arguments** — `{argument: value}`. A fixed argument
  **disappears** from the schema the client sees (from `properties`
  and `required`) and is set by the gateway when forwarding. A client
  that sends it anyway is refused (§7) — also with the same value: it
  did not read the schema the gateway shows.
- **Bounds** — per argument either a **list** of allowed values
  (`{"enum": [...]}`) or a **pattern** (`{"glob": "Z*"}`) in which `*`
  stands for any number of characters and `?` for exactly one, all
  other characters literal. The schema the client sees carries the list
  as `enum` and the pattern as an equivalent `pattern`, so that the
  model knows the bound; enforced is the gateway's own comparison, not a
  regular expression. A pattern is deliberately **not** a regular
  expression: an operator's expression on a client's input would be a
  way to stall the gateway, and a glob covers the case it is for
  ("only packages starting with Z").

Both are checked against the **approved** schema when saving: the
argument must be declared, a fixed value and every listed value must
satisfy the argument's schema, and an argument cannot be fixed and
bounded at once. When the operator confirms a changed text (§4.2), the
check is repeated against the new text; if a fixed argument or bound no
longer fits, the confirmation is refused until they are adjusted — the
entry stays suspended meanwhile.

Fixed values are the operator's configuration, not a client's argument;
they are stored and audited (§10 does not apply to them).

## 6. Protocol behaviour

Downstream: `POST`, `GET` and `DELETE` on `/mcp/<view>`, Streamable
HTTP. The gateway is the client's MCP server.

| Message from the client | Gateway |
|---|---|
| `initialize` | answers itself (§3.2); capabilities: `tools` always, `resources` (without `subscribe`, without `listChanged`) if the view holds resources or templates, `prompts` if it holds prompts; `serverInfo.name` is the view's name, never a server's; issues `Mcp-Session-Id`; remembers which server-to-client requests the client declared (§6.1) |
| `notifications/initialized`, other notifications | `202`; `notifications/cancelled` is forwarded to the server that runs the cancelled request, if one does |
| a response (no `method`) | `202`; forwarded to the server that asked, if it answers a request the gateway passed on (§6.1); otherwise dropped |
| `ping` | answers itself |
| `tools/list`, `resources/list`, `resources/templates/list`, `prompts/list` | answers itself, from the approved snapshots of the view's `active` entries of that kind the key may use (§5.2), under their names in the view, with fixed arguments removed and bounds shown (§5.3), shaped for the client's version; one page, no cursor |
| `tools/call`, `resources/read`, `prompts/get` | checks (§7, §8), forwards to the entry's server under the **server's** name, relays the answer; one usage record (§9) |
| `resources/subscribe`, `resources/unsubscribe`, anything else | JSON-RPC error `-32601` (method not found) |
| a JSON-RPC batch (array) | `400`; batching is not supported |
| `GET` | `405`: the gateway opens no server-initiated stream in 0.2 |
| `DELETE` | ends the session and the upstream sessions behind it |

- **Which entry.** `tools/call` and `prompts/get` name the entry in the
  view. `resources/read` names a URI: an approved resource with exactly
  that URI, otherwise an approved template it matches — `{x}` stands for
  one or more characters without `/`, `{+x}` for one or more of any. A
  URI that matches **several** templates of the view is refused (the
  operator has to make them unambiguous); one that matches none is
  refused like an unknown resource.
- **Sessions.** A downstream session belongs to the key and view that
  opened it; presented with another key it is unknown (`404`). A
  request other than `initialize` **without** a session gets `400`;
  with an unknown or expired one (idle 30 minutes) it gets `404` — the
  MCP signal for the client to initialize again.
- **Upstream sessions** are opened lazily, on the first call that needs
  a server, one per downstream session and server, and are never shared
  between downstream sessions.
- **Streams.** A server may answer a call with a single JSON response
  or an SSE stream. If the client accepts `text/event-stream`, the
  gateway relays the stream: progress and log notifications pass,
  passed-on requests (§6.1) pass, the final response passes. Otherwise
  it answers with the final response as JSON.
  `notifications/*/list_changed` from a server are not passed on: the
  view is static, and a catalog change goes through §4.2.

### 6.1 Requests from the server to the client

MCP lets a server ask the client during a call: **elicitation**
(`elicitation/create` — ask the person, e.g. "which transport
request?"), **roots** (`roots/list` — the client's working
directories) and **sampling** (`sampling/createMessage` — let the
*client's* model generate text for the server). Each view sets each of
the three to `pass` or `refuse` (RFC-0065 §2.1, Q1). Default for a new
view: elicitation and roots `pass`, sampling `refuse` — sampling lets a
backend spend the client's model and send it data. A view carried over
from 0.1 keeps refusing all three until the operator changes it: an
update does not silently widen what a view lets through.

A request is passed on only if **all** of these hold: the view passes
it, the client declared the capability at `initialize`, and the client
accepts a stream for this call. Otherwise the gateway answers the
server itself with JSON-RPC error `-32601`, and the client never sees
the request.

- **Toward the server**, the gateway declares at `initialize` exactly
  the capabilities it would pass — those the view passes *and* the
  client declared. A server that cannot ask, does not ask.
- **Toward the client**, a passed-on request carries an **identifier
  of the gateway**, not the server's: in a bundle, two servers may use
  the same identifier, and the client must not learn which server
  asked. The client's response is mapped back and forwarded to the
  server that asked, under that server's identifier.
- A passed-on request belongs to the call during which it was sent;
  once the call has ended, a late response is dropped.
- `ping` from a server is answered by the gateway.
- The content of a request and of the client's response (the person's
  answer) is never recorded (§10).

### 6.2 Clients of MCP `2026-07-28`

MCP `2026-07-28` has no `initialize` and no sessions: every request
carries its version in `_meta`, and `server/discover` reports a
server's versions. Its specification lets a client recognize a server
of the earlier, session-based era over HTTP by a **`4xx` whose body is
not one of its own errors** (codes `-32020` to `-32099`); the client
then falls back to `initialize`.

The gateway 0.2 is such an earlier server and answers deliberately so:
a request **without** a session that is `server/discover` or carries
`io.modelcontextprotocol/protocolVersion` in `_meta` gets `400` with
JSON-RPC error `-32600` and a sentence naming the versions it speaks.
It never answers with a code from `-32020` to `-32099`: that would
mark it as a server of the new era, and the client would not fall
back. Measured 2026-11-02 with the official Python SDK 2.3.0 (spec
0.1, §14 there).

## 7. Argument check (A1)

Every `tools/call` is checked before it is forwarded:

1. an argument the view **fixed** (§5.3) is refused if the client sent
   it;
2. the client's arguments, **with the fixed arguments set**, are checked
   against the **approved** input schema:
   - arguments the schema does not declare are refused, unless the
     schema explicitly allows additional properties;
   - missing required arguments and wrong types are refused;
   - `enum`, `const`, string and array lengths, numeric bounds,
     `items`, nested `properties`, `anyOf`, `oneOf`, `allOf` and local
     `$ref` are checked; other keywords (`format`, `pattern`, …) are not
     enforced and are named as such on the operator page;
3. every argument with a **bound** (§5.3) must be in its list or match
   its pattern.

Every `prompts/get` is checked against the approved prompt: arguments
are strings, undeclared ones are refused, required ones must be there.

A refusal is a JSON-RPC error `-32602` naming the **argument's path**,
never its value. It is counted (`refused`); the argument is not
recorded (§10).

## 8. Protecting the servers

Per server, in this order, after the key's own rate and budget. In a
bundle, every call is subject to the limits of **the server of its
entry**; a slow server in a view does not slow down the others.

1. **Breaker:** after *K* failures in a row (default 5) the server is
   out for a cool-down (default 30 s); then one call is let through,
   and its outcome decides.
2. **Rate** per server and per server-and-key (calls per minute,
   default 0 = none).
3. **Concurrency:** at most *N* calls in flight (default 4); further
   calls wait in a queue (default 16 places, 10 s).
4. **Timeout** per call (default 60 s).
5. **Answer size** (A2): at most *B* bytes per answer (default 1 MiB),
   counted while reading, without interpreting the content. An answer
   that exceeds it is dropped and replaced by an error naming the
   limit — never truncated, because a truncated result looks complete
   to the model.

| Situation | Answer |
|---|---|
| key rate exceeded | HTTP `429` with `Retry-After` |
| key budget exhausted | HTTP `429` without `Retry-After` |
| server rate, queue full, breaker open, size exceeded | JSON-RPC error `-32001`, `data.oaap.reason` = `rate`, `queue`, `breaker`, `size`, with `retry_after` where it applies; the message names the view, never the server's address |
| policy refusal: unknown tool or prompt, argument check | JSON-RPC error `-32602` with a sentence |
| policy refusal: suspended entry, effect class, unknown or unapproved resource, URI matching several templates | JSON-RPC error `-32002` (`-32602` for the several templates) with a sentence |
| server unreachable, timeout, HTTP error, protocol error | JSON-RPC error `-32003` |
| the server answers the call with a JSON-RPC error | that error, unchanged |
| the tool ran and failed | the server's result with `isError: true`, unchanged |

Only failures **on the way** to the server count toward the breaker
(unreachable, timeout, HTTP error, protocol error). A server that
answers — with a result, `isError` or a JSON-RPC error — is working.

## 9. Usage

One row per `tools/call`, `resources/read` and `prompts/get` that
reaches the gateway with a valid key and session: time, key, view,
**kind** (`tool`, `resource`, `template`, `prompt`), **name in the
view**, server, **name at the server**, access procedure, outcome,
duration, **bytes up** (the client's request body) and **bytes down**
(what the client received), and the **context snapshot** of the key
(`oaap.ai.gateway` §5).

- A read through a **template** records the template, never the URI the
  client filled in: values stand in it.
- A refused call to a resource nobody approved records **no** URI, for
  the same reason; a refused tool or prompt records the name the client
  sent, cut to 200 characters.

| Outcome | Meaning |
|---|---|
| `ok` | the server answered with a result |
| `tool_error` | the server answered with `isError: true` |
| `refused` | the gateway refused (unknown or suspended entry, effect class, argument check) |
| `limited` | a limit of §8 or the key's budget |
| `upstream_error` | unreachable, timeout, HTTP or protocol error, version outside the list, or a JSON-RPC error from the server |

`initialize`, the four lists, `ping`, notifications, responses to
passed-on requests, `DELETE` and requests of the `2026-07-28` era
(§6.2) are counted per day, key, view and method as **protocol
traffic**, not as consumption.

### 9.1 Report

`GET /report/v1/usage` and the operator's charts read **one query**
(`oaap.ai.gateway` §5.1): parameters `from`, `to` (required),
`group_by`, filters, `format=json|csv`; dimensions `account`,
`project`, `cost_center`, `application`, `owner`, `key`, `view`,
`kind`, `tool` (the name in the view), `server`, `outcome`, `day`,
`month`; metrics `calls`,
`bytes_up`, `bytes_down`; `complete_until` in every answer. Volume,
never money. `GET /report/v1/keys` lists keys with their current
context and views, never a key value.

## 10. Never recorded

**No tool argument, no tool result, no resource content and no prompt
text** in any log, usage row, audit entry or error message — in any
operating mode (RFC-0065 D11). The usage table has no column a payload
would fit into. Access log lines carry method and path only.

## 11. Configuration

| Variable | Meaning |
|---|---|
| `MCPGW_MASTER_KEY` | key to the vault for server credentials (secret, `generate: token`) |
| `MCPGW_CATALOG_MINUTES` | catalog re-read interval, default 15, 0 = only on demand |

Servers, views and keys are maintained on the operator page and through
the command line inside the container (`app.py key|server|view …`).

## 12. Conformance tests (described)

1. A key without views reaches no view; no key, unknown, revoked and
   unentitled keys get byte-identical `403` answers.
2. A tool the server offers but no view contains is neither listed nor
   callable.
3. After the server changes a listed tool's description, the next
   catalog read suspends it: not listed, call refused, operator page
   shows both texts; after confirming it is listed with the new text.
4. `tools/list` returns the approved text even while the server reports
   another.
5. A call with an undeclared argument, a missing required argument or a
   wrong type is refused with the argument's path and never reaches the
   server.
6. A `write` tool is not listed for a key or view limited to `read`.
7. A server answering `3xx` is not followed; an address resolving to
   loopback or link-local is refused.
8. A server offering a protocol version outside the list is refused;
   a client on another tested version than the server works.
9. Concurrency, queue, rates, timeout, answer size and breaker answer
   as in §8, and the server never sees more than *N* calls at once.
10. Every `tools/call` with a valid key and session yields exactly one
    usage row with the context snapshot; no row contains an argument
    or a result value.
11. A server-to-client request the view refuses, or the client did not
    declare, is answered by the gateway with an error and never reaches
    the client; the server is not even offered the capability.
12. The report and the charts give the same totals.
13. A view holds entries of two servers; each call reaches the right
    server under the server's name. Putting a second entry under a name
    already taken in the view is refused.
14. A fixed argument is absent from the listed schema, set when
    forwarding and refused when the client sends it; a value outside a
    bound is refused with the argument's path and never reaches the
    server; a fixed value or bound that does not fit the approved schema
    is refused when saving, and when confirming a changed text.
15. `resources/list`, `resources/templates/list` and `prompts/list` show
    only approved entries; reading an unapproved URI or a URI that does
    not match an approved template never reaches a server; a prompt
    with a missing or undeclared argument is refused.
16. A passed elicitation reaches the client under an identifier of the
    gateway, and the client's answer reaches the server that asked under
    the server's identifier; sampling is refused by default even if the
    client declared it.
17. A view is never greener than its worst server: a key whose light
    allows only the better server gets the same `403` as everyone else.
18. A server that no longer declares a capability leaves its entries of
    that kind `missing`.
19. `server/discover` and a request with a version in `_meta` without a
    session get `400` with an error code outside `-32020`…`-32099`.
20. A database of 0.1 is carried over with every approval intact
    (same fingerprint, still `active`), and its views keep refusing
    server-to-client requests.
21. A read through a template records the template, never the filled-in
    URI; a refused unapproved URI is not recorded.

## 13. Dependencies

`oaap.core.gateway` (public route, identity headers), `oaap.apps.runtime`
(manifest, storage, configuration), `oaap.net.destinations` (§3.1),
`oaap.ai.gateway` (shared books), RFC-0068 (egress).

## 14. Not in 0.2

- **MCP `2026-07-28` itself** (stateless, without `initialize` and
  sessions, server-to-client requests as multi round-trip results,
  `subscriptions/listen` instead of `GET` and `resources/subscribe`).
  0.2 is recognizable as a session-based server (§6.2); speaking the new
  era is a redesign, not an addition.
- **Resource subscriptions and list-change notifications** toward the
  client: they need a server-initiated stream (`GET`), which 0.2 does
  not open; in the `2026-07-28` era they are replaced altogether.
- `completion/complete` and `logging/setLevel`.
- Sign-in of a person, access profiles, procedure X (0.3); procedure P
  (0.4, RFC-0066); P-saml and Entra (0.5); `pattern` and `format`
  enforcement in input schemas.

## Deutsche Zusammenfassung

**Was das ist:** Ein MCP-Gateway als OAAP-App. Je **Sicht** gibt es
einen MCP-Endpunkt `/mcp/<sicht>`. Ein KI-Client (Claude Code, Copilot,
ein eigener Agent) sieht dort genau einen MCP-Server und erfährt nie,
welche Server dahinterstehen. Version 0.2 umfasst RFC-0065 Stufen 1
und 2. Eine Sicht bündelt Tools, Resources und Prompts mehrerer Server
(„Bündel“), der Zugang zu den Servern ist technisch (Verfahren T).

**Schlüssel:** Sie funktionieren wie beim KI-Gateway: einmal gezeigt,
nur als Hash gespeichert, mit Kontext für die Abrechnung. Anders als
dort gilt: **ohne genannte Sicht keine Sicht**, es ist also nichts von
selbst erreichbar. Je Schlüssel gibt es dazu die höchste Wirkungsklasse
(Standard `lesen`), die schlechteste erlaubte Ampel, eine Rate und ein
Budget in Aufrufen. Alle Ablehnungen sehen gleich aus.

**Server:** Die Adresse ist eine URL oder `destination:<name>`. Im
zweiten Fall setzt die Plattform die Zugangsdaten ein, und das Gateway
hält kein Geheimnis (A4). Das Gateway folgt keiner Weiterleitung und
fährt keine Adresse aus einer Antwort an; Loopback und Link-Local sind
verboten. Die Protokollversion handelt es getrennt mit Client und Server
aus, aus einer festen, getesteten Liste (A3).

**Katalog:** Das Gateway liest alle vier Arten, die ein Server anbietet:
Tools, Resources, Resource-Vorlagen und Prompts. Das geschieht alle
15 Minuten und auf Knopfdruck. Nichts davon ist sichtbar, bis der
Betreiber es in eine Sicht legt, und dabei wird der Text
**festgehalten**. Ändert der Server ihn, ist der Eintrag gesperrt, bis
der Betreiber bestätigt. Nennt ein Server eine Fähigkeit nicht mehr,
etwa Prompts, fehlen seine Einträge dieser Art. Sie bleiben dann nicht
mit dem alten Stand stehen.

**Sichten und Bündel (neu in 0.2):**

- Eine Sicht nimmt Einträge **beliebig vieler Server** auf.
- Ein Tool oder Prompt bekommt einen **Namen der Sicht**. Vorgeschlagen
  wird der Name beim Server, und wenn der schon belegt ist,
  `<server>_<name>`. Ein belegter Name wird beim Speichern
  **abgewiesen**, nie still aufgelöst. Resources behalten ihre URI.
- Die Beschreibung lässt sich durch einen eigenen Text ersetzen. Der
  Fingerabdruck bleibt der des Servers.
- **Feste Argumente** (`{"package": "ZDEMO"}`) verschwinden aus dem
  Schema, das der Client sieht, und das Gateway setzt sie ein. Schickt
  der Client sie trotzdem, wird abgewiesen.
- **Grenzen** erlauben je Argument eine Liste von Werten oder ein Muster
  mit `*` und `?`, etwa „nur Pakete mit Z“. Das ist bewusst kein
  regulärer Ausdruck, weil man mit einem solchen Ausdruck das Gateway
  lahmlegen könnte.
- Beim Speichern werden feste Werte und Grenzen gegen das freigegebene
  Schema geprüft. Beim Bestätigen eines geänderten Texts geschieht das
  erneut.
- Resources und Prompts gelten immer als `lesen`.
- Die Ampel einer Sicht ist die ihres **schlechtesten** Servers.

**Rückfragen vom Server an den Client:** Gemeint sind Elicitation
(Rückfrage an den Menschen), Roots (Arbeitsverzeichnisse) und Sampling
(das Modell des Clients benutzen). Jede Sicht stellt jede davon auf
durchreichen oder ablehnen. Für neue Sichten gilt: Elicitation und Roots
werden durchgereicht, Sampling wird abgelehnt. Sichten aus 0.1 lehnen
weiter alles ab, bis der Betreiber es ändert, denn ein Update soll
nichts still öffnen.

Durchgereicht wird nur, wenn die Sicht es erlaubt, der Client es kann
und gerade ein Strom offen ist. Dem Server sagt das Gateway nur zu, was
es auch durchreichen würde. Der Client sieht eine Kennung des Gateways,
nicht die des Servers. Die Antwort geht an genau den Server zurück, der
gefragt hat.

**MCP `2026-07-28`:** Diese neue Protokollversion kommt ohne
Anmeldung (`initialize`) und ohne Sitzungen aus. Ein Client dieser
Version erkennt einen älteren Server an einer `400` ohne „modernen“
Fehlercode und fällt dann zurück. Genau so antwortet das Gateway 0.2
jetzt bewusst; gemessen hatten wir das zuvor nur als zufälliges
Verhalten. Die neue Version selbst zu sprechen wäre ein Umbau, keine
Ergänzung.

**Prüfungen je Aufruf:**

- Der Eintrag liegt in der Sicht und ist aktiv.
- Seine Wirkungsklasse liegt nicht über der von Sicht und Schlüssel.
- Feste Argumente kommen nicht vom Client.
- Die Argumente passen zum freigegebenen Schema (A1).
- Grenzen sind eingehalten, und Prompt-Argumente sind geprüft.

Eine Meldung nennt den Pfad des Arguments, nie seinen Wert. Der Schutz
gilt je Server: Sicherungsautomat, Raten, Gleichzeitigkeit,
Zeitlimit und Antwortgröße.

**Gemessen** wird je `tools/call`, `resources/read` und `prompts/get`,
mit Art, Namen in der Sicht und beim Server und einer Kopie des
Kontexts. Bei einer Vorlage wird die Vorlage gemessen, nie die
eingesetzte URI. **Nie** gespeichert werden Argumente, Ergebnisse,
Inhalte, Prompt-Texte und die Antworten von Menschen auf Rückfragen.

**Nicht in 0.2:**

- MCP `2026-07-28` selbst
- Abonnements von Resources und Änderungsmeldungen, denn dafür fehlt der
  Strom vom Server zum Client
- Anmeldung eines Menschen (0.3) und der Benutzer bis ins SAP-System
  (0.4)
