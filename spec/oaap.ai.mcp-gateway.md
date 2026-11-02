# oaap.ai.mcp-gateway — Tool Servers Behind One Keyed Endpoint per View

- **ID:** `oaap.ai.mcp-gateway`
- **Version:** 0.1 (RFC-0065 stage 1: one server per view, technical
  access, keys, catalog with default deny and pinned descriptions,
  effect classes, protection limits, usage and report; §14 A1–A4)
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

Version 0.1 covers **one server per view** and **technical access**
(procedure T). Bundles across servers, resources and prompts, sign-in
of a person and carrying that person through to the backend follow in
later versions (RFC-0065 §11).

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
  server's answer**. In 0.1 there is no other address than the one
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
  names the version the server offered. The negotiated version is shown
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

The light of a view is the light of its server. A key may use a view
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

The gateway reads each server's tools (`tools/list`, all pages, at
most 1000 tools) into a **catalog**: name, title, description, input
schema, output schema, annotations. It reads on the operator's demand
and on its own every `MCPGW_CATALOG_MINUTES` (default 15).

A tool in the catalog is **not** exposed. Only a view exposes it (§5).
A server that adds a tool adds nothing to any view.

### 4.2 Fingerprint and suspension

The **fingerprint** of a tool is the SHA-256 of the canonical JSON
(sorted keys, no whitespace) of its name, title, description, input
schema, output schema and annotations.

When the operator puts a tool into a view, the gateway stores the
**approved snapshot**: the fingerprint and the full text at that
moment. Then:

| Catalog says | State in every view | Effect |
|---|---|---|
| same fingerprint | `active` | listed and callable |
| different fingerprint | `suspended` | neither listed nor callable, until the operator confirms; the operator page shows old and new side by side |
| tool gone | `missing` | neither listed nor callable |

**Clients only ever see the approved snapshot**, never the server's
current text. A changed description reaches no model before the
operator confirmed it (RFC-0065 §4.2, "rug pull").

## 5. Views

A view has a name (`[a-z0-9-]`, the path segment), **one server** in
0.1, a list of tools of that server, a **highest effect class**
(default `read`) and the server's light.

### 5.1 Approval

Adding a tool to a view is an approval (§4.2). It is refused when the
tool's input schema refers to anything outside itself (a `$ref` that
does not start with `#`): such a schema cannot be checked (§7).

### 5.2 Effect classes

The operator assigns every tool in a view an **effect class**: `read`,
`write` or `execute` (irreversible, or with effects outside the system).
The server's own annotations (`readOnlyHint`, `destructiveHint`) are
**shown as a hint and never enforced**.

A tool is listed and callable for a key only if its class is not
higher than **both** the view's highest class and the key's highest
class (`read` < `write` < `execute`).

## 6. Protocol behaviour

Downstream: `POST`, `GET` and `DELETE` on `/mcp/<view>`, Streamable
HTTP. The gateway is the client's MCP server.

| Message from the client | Gateway |
|---|---|
| `initialize` | answers itself (§3.2); capabilities: `tools` only; `serverInfo.name` is the view's name, never a server's; issues `Mcp-Session-Id` |
| `notifications/initialized`, other notifications | `202`; `notifications/cancelled` is forwarded to the upstream session if one is open |
| `ping` | answers itself |
| `tools/list` | answers itself, from the approved snapshots of the view's `active` tools the key may use (§5.2), shaped for the client's version |
| `tools/call` | checks (§7, §8), forwards, relays the answer; one usage record (§9) |
| anything else | JSON-RPC error `-32601` (method not found) in 0.1 |
| a JSON-RPC batch (array) | `400`; batching is not supported |
| `GET` | `405`: the gateway opens no server-initiated stream in 0.1 |
| `DELETE` | ends the session and the upstream sessions behind it |

- **Sessions.** A downstream session belongs to the key and view that
  opened it; presented with another key it is unknown (`404`). A
  request other than `initialize` **without** a session gets `400`;
  with an unknown or expired one (idle 30 minutes) it gets `404` — the
  MCP signal for the client to initialize again.
- **Upstream sessions** are opened lazily, on the first `tools/call`
  that needs the server, one per downstream session and server, and
  are never shared between downstream sessions.
- **Streams.** A server may answer a call with a single JSON response
  or an SSE stream. If the client accepts `text/event-stream`, the
  gateway relays the stream: progress and log notifications pass, the
  final response passes. Otherwise it answers with the final response
  as JSON. `notifications/*/list_changed` from a server are not passed
  on: the view is static, and a catalog change goes through §4.2.
- **Requests from the server to the client** (elicitation, sampling,
  roots) are **refused by the gateway** in 0.1 with JSON-RPC error
  `-32601`, sent back to the server; the client never sees them.
  Configurable per view from 0.2 (RFC-0065 §2.1).

## 7. Argument check (A1)

Every `tools/call` is checked against the **approved** input schema
before it is forwarded:

- arguments the schema does not declare are refused, unless the schema
  explicitly allows additional properties;
- missing required arguments and wrong types are refused;
- `enum`, `const`, string and array lengths, numeric bounds, `items`,
  nested `properties`, `anyOf`, `oneOf`, `allOf` and local `$ref` are
  checked; other keywords (`format`, `pattern`, …) are not enforced in
  0.1 and are named as such on the operator page.

A refusal is a JSON-RPC error `-32602` naming the **argument's path**,
never its value. It is counted (`refused`); the argument is not
recorded (§10).

## 8. Protecting the servers

Per server, in this order, after the key's own rate and budget:

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
| policy refusal (unknown tool, suspended, effect class, light) | JSON-RPC error `-32602` or `-32002` with a sentence |
| server unreachable, timeout, HTTP error, protocol error | JSON-RPC error `-32003` |
| the server answers the call with a JSON-RPC error | that error, unchanged |
| the tool ran and failed | the server's result with `isError: true`, unchanged |

Only failures **on the way** to the server count toward the breaker
(unreachable, timeout, HTTP error, protocol error). A server that
answers — with a result, `isError` or a JSON-RPC error — is working.

## 9. Usage

One row per `tools/call` that reaches the gateway with a valid key and
session: time, key, view, **tool name**, server, access procedure,
outcome, duration, **bytes up** (the client's request body) and
**bytes down** (what the client received), and the **context
snapshot** of the key (`oaap.ai.gateway` §5).

| Outcome | Meaning |
|---|---|
| `ok` | the server answered with a result |
| `tool_error` | the server answered with `isError: true` |
| `refused` | the gateway refused (unknown or suspended tool, effect class, light, argument check) |
| `limited` | a limit of §8 or the key's budget |
| `upstream_error` | unreachable, timeout, HTTP or protocol error, version outside the list, or a JSON-RPC error from the server |

`initialize`, `tools/list`, `ping`, notifications and `DELETE` are
counted per day, key, view and method as **protocol traffic**, not as
consumption.

### 9.1 Report

`GET /report/v1/usage` and the operator's charts read **one query**
(`oaap.ai.gateway` §5.1): parameters `from`, `to` (required),
`group_by`, filters, `format=json|csv`; dimensions `account`,
`project`, `cost_center`, `application`, `owner`, `key`, `view`,
`tool`, `server`, `outcome`, `day`, `month`; metrics `calls`,
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
11. A server-to-client request is answered by the gateway with an error
    and never reaches the client.
12. The report and the charts give the same totals.

## 13. Dependencies

`oaap.core.gateway` (public route, identity headers), `oaap.apps.runtime`
(manifest, storage, configuration), `oaap.net.destinations` (§3.1),
`oaap.ai.gateway` (shared books), RFC-0068 (egress).

## 14. Not in 0.1

**MCP `2026-07-28`** (measured 2026-11-02 with the official Python
SDK 2.3.0): a client of that era first probes with `server/discover`.
0.1 answers it like any request without a session (`400`); the SDK
then falls back to `initialize` and works on `2025-11-25`. That is
compatible, but by accident, not by design: adding `2026-07-28` to the
tested list and answering the probe deliberately is work for 0.2.

Bundles across servers, renaming, fixed arguments and bounds,
resources and prompts, server-to-client requests per view (0.2);
sign-in of a person, access profiles, procedure X (0.3); procedure P
(0.4, RFC-0066); P-saml and Entra (0.5); `pattern` and `format`
enforcement; GET streams for server-initiated messages.

## Deutsche Zusammenfassung

**Was das ist:** Ein MCP-Gateway als OAAP-App. Je **Sicht** gibt es
einen MCP-Endpunkt `/mcp/<sicht>`. Ein KI-Client (Claude Code, Copilot,
ein eigener Agent) sieht dort genau einen MCP-Server und erfährt nie,
welcher Server dahintersteht. Version 0.1 = RFC-0065 Stufe 1: ein
Server je Sicht, technischer Zugang (Verfahren T).

**Schlüssel:** wie beim KI-Gateway (einmal gezeigt, nur als Hash, mit
Kontext für die Abrechnung), aber **ohne genannte Sicht keine Sicht** —
nichts ist von selbst erreichbar. Dazu je Schlüssel die höchste
Wirkungsklasse (Standard `lesen`), die schlechteste erlaubte Ampel,
eine Rate und ein Budget in Tool-Aufrufen. Alle Ablehnungen sehen
gleich aus.

**Server:** Adresse als URL oder als `destination:<name>` — dann setzt
die Plattform die Zugangsdaten ein und das Gateway hält kein Geheimnis
(A4). Keine Weiterleitungen folgen, keine Adressen aus Antworten,
Loopback und Link-Local verboten. Protokollversion getrennt mit Client
und Server aushandeln, aus einer festen, getesteten Liste (A3).

**Katalog:** Das Gateway liest die Tools jedes Servers, alle 15 Minuten
und auf Knopfdruck. Nichts davon ist sichtbar, bis der Betreiber es in
eine Sicht legt. Dabei wird der Text **festgehalten**: Clients sehen nur
den freigegebenen Text. Ändert der Server Beschreibung oder Schema, wird
das Tool gesperrt, bis der Betreiber bestätigt — beide Fassungen stehen
nebeneinander.

**Prüfungen je Aufruf:** Tool in der Sicht und aktiv; Wirkungsklasse
(lesen/schreiben/ausführen) nicht über der von Sicht und Schlüssel;
Argumente gegen das freigegebene Schema (A1) — unbekannte, fehlende und
falsch getypte werden abgewiesen, die Meldung nennt den Pfad, nie den
Wert. Schutz je Server: Sicherungsautomat, Raten, höchstens N
gleichzeitige Aufrufe mit kurzer Warteschlange, Zeitlimit und
**Antwortgröße** (A2, Standard 1 MiB — zu groß ist ein Fehler, nie ein
stilles Abschneiden).

**Gemessen** wird je Tool-Aufruf mit Kontext-Kopie, Protokollverkehr
getrennt; Report und Grafiken über eine Abfrage. **Nie** gespeichert:
Argumente, Ergebnisse, Inhalte, Prompt-Texte.

**Rückfragen vom Server an den Client** (Elicitation, Sampling, Roots)
lehnt 0.1 ab; je Sicht einstellbar ab 0.2. Bündel, Resources/Prompts,
Anmeldung und Benutzer-Durchreichung folgen in 0.2 bis 0.5.
