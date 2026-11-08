# oaap.ai.mcp-gateway — Tool Servers Behind One Keyed Endpoint per View

- **ID:** `oaap.ai.mcp-gateway`
- **Version:** 0.8.0 (RFC-0075 stage 1: views of MCP Apps are read, pinned by
  content and approved with their tool, §4.3). 0.7.3 (views, effect class and light of a key or profile can be
  changed without revoking it; a `403` names its reason; sources can be read in
  on demand, §2.3, §3.6). 0.7.2 (RFC-0074 stage 3: the usage row records `confirmed`,
  §9; the operator's page reads a platform source's catalog with the
  operator's own assertion, §3.7). 0.7.1 (RFC-0074 stage 2: `tools/list` names each tool's
  effect class in `_meta`, §5.2). 0.7 (RFC-0074 stage 1: **procedure A**, §3.9 — a chat of the
  platform carries the person here; a view's third way in, `platform`, and
  profiles naming `@<chat>`). 0.6 (RFC-0073 stage 3: **settings from the platform**, §3.8 — the
  sign-in settings fall back to what the platform hands over when a connector made
  the gateway's clients). 0.5 (RFC-0073 stage 2: **procedure I**, §3.7 — a signed-in
  person reaches an OAAP app as themselves, carried by the platform).
  0.4 (RFC-0073 stage 1: sources of the platform, §3.6 —
  OAAP apps declaring an MCP door are found and registered, nothing in a
  view without approval). 0.3 (RFC-0065 stage 3: sign-in of a person at the
  tenant's identity provider, access profiles, procedure X token
  exchange; one `401` for every failure; RFC-0065 D14–D16). 0.2 of
  2026-11-02 (stages 1 and 2: views that bundle tools,
  resources, resource templates and prompts of several servers under
  their own names, with fixed arguments and bounds; server-to-client
  requests configurable per view; technical access, keys, catalog with
  default deny and pinned descriptions, effect classes, protection
  limits, usage and report; §14 A1–A4; deliberate answer to MCP
  `2026-07-28` clients); 0.1 of 2026-11-02 was stage 1 alone.
- **Maturity:** draft
- **Based on:** RFC-0065 (the MCP gateway), RFC-0064 and
  `oaap.ai.gateway` 0.4 (keys, context, volume, report, vault — shared
  module), RFC-0033 and `oaap.net.destinations` (reaching outward),
  RFC-0068 (closed egress), RFC-0002 (default deny), RFC-0010 (public
  route brake), RFC-0019 (token hygiene); RFC 9728, RFC 8707, RFC 8693,
  the MCP authorization specification 2025-11-25
- **Implemented by:** `oaap-apps/apps/mcp-gateway`

## Purpose

AI clients — Claude Code, Copilot, a company's own agent — call **MCP
servers** directly: tool servers that read and change systems. The
gateway puts those servers behind **one endpoint per view**. A consumer
gets a key for named views; every tool call is checked, limited and
metered with a copy of the key's context. The client sees one MCP
server per view and never learns which server stands behind it, or
where.

Version 0.3 covers **views across several servers** (bundles) with
tools, resources and prompts; **two ways in** — a key, or a person
signed in at the tenant's identity provider and billed through an
access profile; and two procedures toward servers — **technical**
access (T) and **token exchange** (X), where the server sees the person.
Carrying the person into SAP by a certificate (procedure P) follows
(RFC-0065 §11, RFC-0066).

## 1. Routes

| Path | Role in the manifest | Who |
|---|---|---|
| `/mcp/<view>` | `public` | MCP clients, with a gateway key or a sign-in token (§2) |
| `/.well-known/oauth-protected-resource…` | `public` | MCP clients looking for where to sign in (§2.2) |
| `/report/v1/…` | `admin` | a billing system with a platform API key (RFC-0027) |
| `/` and everything else | `admin` | the operator |
| `/healthz` | — | the platform |

`/mcp/<view>` is `public`: the platform authenticates nothing there,
strips client-sent identity headers and brakes per client address
(RFC-0010); the `Authorization` header passes unchanged. The gateway
authorizes every request itself.

## 2. Two ways in: a key, or a person signed in

Every request to `/mcp/<view>` carries `Authorization: Bearer <value>`.
A value starting with `mcp-oaap-` is a **key** (§2.1); a value of three
dot-separated parts is a **sign-in token** (§2.2). A view states which
ways it accepts (§5): `key`, `signin` or both — and since 0.7 `platform`,
a person carried by a chat of the platform (§3.9), which comes without
`Authorization`.

- **One answer for every failure.** No credential, an unknown or revoked
  key, a token that fails any check of §2.2, and — for a key — a view
  that does not exist, does not accept keys, is not named by the key or
  is lit worse than the key allows (§3.3): all get
  **`401`** with the same body and the header

  `WWW-Authenticate: Bearer resource_metadata="<origin>/.well-known/oauth-protected-resource/mcp/<view>"`

  which depends on nothing but the requested path. Whoever probes learns
  nothing — not whether a key exists, not whether a view exists. (0.1
  and 0.2 answered `403`; the MCP authorization specification requires
  `401` for a missing or invalid credential, so all failures moved.)
- **`403`** is given only to a person with a **valid** token who may not
  use this view: no access profile for the view matches (§2.3), or the
  view does not exist, does not accept sign-in or is lit worse than the
  profile allows. Sign-in proves who someone is, not that they may
  consume. A `401` here would send the client into a new sign-in that
  changes nothing; and the person learns only about views of their own
  tenant's gateway.
- Five failed attempts from one address within five minutes are
  answered with `429` for the rest of the window.

### 2.1 Keys

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
  **rate** (requests per minute) and a **budget** in calls (0 = no
  limit).

### 2.2 Sign-in (RFC-0065 §5.1, §15)

The gateway is an OAuth **protected resource** (RFC 9728) of **one**
issuer — the tenant's identity provider — named in its configuration
(`MCPGW_ISSUER`, RFC-0065 D14). Without an issuer, sign-in is off and
the well-known path answers `404` for every view alike.

**Resource metadata.** `GET /.well-known/oauth-protected-resource/mcp/<view>`
(and `/.well-known/oauth-protected-resource` for the gateway as a whole)
returns `{"resource": "<origin>/mcp/<view>", "authorization_servers":
[issuer], "bearer_methods_supported": ["header"], "resource_name":
"<view>"}` — for **any** view name, existing or not. `<origin>` is the
scheme and host the request came in with (`X-Forwarded-Proto`, `Host`).

**The token check**, in this order; any failure is the `401` of §2:

1. a JWT with header `alg` = `RS256` and a `kid`; no other algorithm,
   in particular never `none` and never a symmetric one;
2. the signature verifies against the issuer's key with that `kid`; keys
   shorter than 2048 bits are not accepted;
3. `iss` equals `MCPGW_ISSUER` exactly;
4. `aud` (a string or a list) contains `MCPGW_AUDIENCE` (RFC 8707: the
   token was issued for this gateway — a valid token for anything else
   is refused);
5. `exp` is in the future and `nbf`/`iat` not in the future, each with
   30 seconds of leeway;
6. `sub` is present.

**The issuer's keys.** The gateway reads the issuer's OpenID discovery
document (`<issuer>/.well-known/openid-configuration`) and from it the
`jwks_uri` — which it uses **only if it has the same scheme, host and
port as the issuer**; otherwise sign-in fails and the operator page
says why (A4: never connect to an address only an answer names). Keys
are cached; an unknown `kid` causes at most one new fetch per minute.
Reaching the issuer is subject to the instance's egress (RFC-0068) like
any server.

**No token passthrough.** A sign-in token never leaves the gateway
toward a server (RFC-0065 §6); procedure X (§3.5) exchanges it for
another.

**The client registration** is not the gateway's: a client such as
Claude Code signs in through a **pre-registered public client** in the
tenant's realm whose tokens carry `MCPGW_AUDIENCE` in `aud` (RFC-0065
D15). The operator page names the client id to pass when adding the
server.

### 2.3 Access profiles (RFC-0065 §5.2)

A signed-in person consumes through an **access profile**: the same
context, effect class, light, rate and budget as a key, and the same
list of views — but instead of a secret it names **groups** of the
identity provider (the token's `groups` claim, full paths such as
`/sap-dev`), or `*` for every person of the issuer.

- The profile that applies is chosen **per view**, among the profiles
  that name the view: the first, by name, whose groups intersect the
  token's groups; only if none does, the first with `*`. A person
  matching no profile for the view gets `403`. (Chosen without regard to
  the view, a person with two profiles for two views could never reach
  the second — found in the conformance test.)
- The **rate** of a profile applies **per person**; its **budget** is
  shared by all persons of the profile.
- Profiles are revocable and audited like keys; changing a profile's
  groups is audited with old and new value.
- **Changing limits (0.7.3).** The views, the highest effect class and the
  light of a key or profile can be changed on the operator's page and on the
  command line (`key set`), with the same rules as when issuing; a key keeps
  its value. Audited with old and new value; effective at the next call.
- **The reason of a `403` (0.7.3).** When a profile names the person's
  group but does not open the view, the refusal says why: the view is not in
  the profile, the view lacks the way (`platform`, `signin`), or the view's
  light is above the profile's. The operator's page shows the same sentences
  next to each key and profile. Before 0.7.3 every case read "no access
  profile allows this view", which sent operators to create a profile that
  already existed.
- **The person** is identified by the token's `sub` together with the
  issuer (RFC-0065 D16) — never by name or e-mail. That pair is what
  the usage row records (§9).

## 3. Servers

A server is an MCP endpoint speaking **Streamable HTTP**. stdio is not
supported (RFC-0065 D2).

| Field | Meaning |
|---|---|
| name | `[a-z0-9-]`, unique; shown to the operator, never to a client |
| address | an `http(s)://` URL, or `destination:<need>` (§3.1) |
| access | procedure **T**: `none`, `bearer`, `basic` or `header:<Name>`; or procedure **X**: `exchange` (§3.5); a credential is stored only encrypted (§3.4) |
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

### 3.5 Procedure X: token exchange

A server with access `exchange` is called **as the signed-in person**,
with a token the identity provider issued for that server alone
(RFC 8693; Keycloak's standard token exchange):

| Field | Meaning |
|---|---|
| token endpoint | the issuer's token endpoint, as an `https://` URL or `destination:<need>` — the same rules as a server address (§3.1, A4) |
| client id | the gateway's **confidential** client in the realm; must equal `MCPGW_AUDIENCE`, because the exchange is only granted to a client the person's token is addressed to |
| client secret | stored only encrypted (§3.4) |
| audience | the client id of the backend the new token is for |

For a call, the gateway sends `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`
with the person's token as `subject_token`, `requested_token_type`
access token and the `audience`, authenticated as its client; the
answer's `access_token` goes to the server as `Authorization: Bearer`.
An exchanged token is kept per person and server until 30 seconds
before it expires, never written to storage, never shown.

- **No fallback** (RFC-0065 D8): when the exchange fails, or the call
  came with a key (no person), the call is refused with JSON-RPC error
  `-32003` and a sentence naming the view; the server is never called
  with any other credential.
- A view holding an entry of a server with access `exchange` accepts
  **sign-in only**; saving such a combination with `key` is refused.
- Reading the catalog of such a server needs a person too; the operator
  reads it with a token of their own (`server read --token-stdin`), or
  the catalog stays as last read.
- Upstream sessions are never shared between persons (RFC-0065 §2.2):
  a downstream session belongs to one person, and its upstream sessions
  with it.

### 3.6 Sources of the platform (0.4, RFC-0073 stage 1)

An instance whose manifest declares `mcp_sources: {read: true}` receives
`OAAP_MCP_SOURCES_URL` and `OAAP_MCP_SOURCES_KEY` from the platform
(`oaap.apps.runtime` 2.32): a list of the instances of **its tenant on its
node** that declare an MCP door.

- **When.** At start and every 5 minutes; after a failed read again after
  30 seconds (on a first install the platform writes the gateway's site
  after the container starts). By hand: `app.py source sync`;
  `app.py source list` shows the list as the platform sends it.
- **Registering.** A listed instance becomes a server named after the
  instance, light `red`, marked as a source: with access `platform`
  (procedure I, §3.7) at its `door` when the list names one, else access
  `none` at its `address`. A source registered before doors existed that
  never got an access (`none`, no credential) moves to `platform` once the
  list names a door. **Nothing appears in any view** until the operator
  approves entries (§4).
- **The operator keeps the say.** Access, credential and light set on such
  a server survive every later sync; only a changed address is followed —
  the door for `platform`, the address otherwise.
  In stage 1 the operator gives the server the key of an **agent
  principal** (RFC-0067 §4) limited to that instance, with access
  `bearer`: the app then sees the agent, never the gateway.
- **A name already taken** by a server made by hand is left untouched; the
  sync reports the conflict.
- **A source that disappears** keeps its server, marked with the moment it
  left the list; its entries stay in the views, shown, never removed in
  silence. It returns unmarked.
- Every movement is a line in the audit log (`server.source`). The key is
  never written, logged or shown.

### 3.7 Procedure I: a person to an OAAP app, through the platform (0.5, RFC-0073 stage 2)

A server with access **`platform`** is a source of the platform reached at
its door (`oaap.apps.runtime` 2.32.1). It exists only for sources; a server
made by hand cannot have it.

**Reading its catalog (0.7.2).** Listing a source needs a person. On the
operator's page, the gateway uses the assertion the platform gives the
signed-in operator for this page (aud = this gateway) as act credential, as
in procedure A — so a tenant without a sign-in service can put its own apps'
tools into a view. The command line still takes a provider token
(`--token-stdin`). Without either, the catalog stays as last read.

- **Configuration.** `MCPGW_CLIENT_SECRET` — the secret of the gateway's own
  confidential client (`MCPGW_AUDIENCE`) — and `MCPGW_PLATFORM_AUDIENCE`, the
  platform's client of the tenant's realm. The token endpoint is read from
  the issuer's discovery document (same origin). Missing any of these or the
  sources key: every call is refused with a sentence naming them.
- **Per call.** The person's token (§2.2) is exchanged (RFC 8693, as §3.5)
  **with the gateway's own client** for one addressed to
  `MCPGW_PLATFORM_AUDIENCE`, cached per person until 30 s before it expires.
  The gateway calls the door with `Authorization: Bearer <sources key>` and
  `X-OAAP-Act-Token: <exchanged token>`. The person's own token never leaves
  the gateway.
- **Without a person, no call:** a key, an expired session or a refused
  exchange is a refusal (`-32003`), never the sources key alone (D8). A view
  with such a server accepts sign-ins only; adding it to a key view, or
  switching such a view to keys, is refused. The catalog is read with a
  person's token (`server read <name> --token-stdin ja`).
- **A refusal of the platform is the person's, not the server's.** A `401`
  or `403` from the door is passed on as „Die Plattform lehnt ab (HTTP n):
  <sentence>“ (the platform's sentence, one printable line, at most 200
  characters), measured as `refused`/`platform`, and **does not count for
  the circuit breaker** — otherwise the attempts of one person without a
  right would close the source for everyone.
- **Measured as** procedure `I` with `user_sub` and `user_iss`, as X.
- **Agents** reach the same app with procedure T: the operator registers
  the instance a second time by hand, access `bearer`, with an agent
  principal's key limited to it (RFC-0073 §6).

### 3.8 Settings from the platform (0.6, RFC-0073 stage 3)

Each of the five settings of sign-in and procedure I falls back to the
platform's variable of `oaap.apps.runtime` 2.32.2 when it is empty:

| Setting | Falls back to |
|---|---|
| `MCPGW_ISSUER` | `OAAP_MCP_IDP_ISSUER` |
| `MCPGW_AUDIENCE` | `OAAP_MCP_IDP_AUDIENCE` |
| `MCPGW_SIGNIN_CLIENT` | `OAAP_MCP_IDP_SIGNIN` |
| `MCPGW_CLIENT_SECRET` | `OAAP_MCP_IDP_SECRET` |
| `MCPGW_PLATFORM_AUDIENCE` | `OAAP_MCP_IDP_PLATFORM_AUDIENCE` |

- A value set by hand wins, setting by setting; a gateway configured by
  hand before 0.6 behaves as before.
- The operator page says for each of the five where it came from („von
  der Plattform“, „von Hand“, „leer“). The secret is never shown.

### 3.9 Procedure A: a person carried by a chat of the platform (0.7, RFC-0074 stage 1)

A chat app of the tenant reaches the gateway through a **via door** on its own
site (`oaap.apps.runtime` 2.32.3). The platform has checked the chat's key and
the person's assertion (`oaap.core.identity` 2.13) and sends the request to
`/mcp/<view>` with the person's six headers — the assertion addressed to
**this gateway** — and `X-OAAP-MCP-Client: <chat>`, set by the door.

- **Recognised** when all three are present: `X-OAAP-MCP-Client`,
  `X-OAAP-User-Id`, `X-OAAP-User-Assertion`. The platform strips client-sent
  identity headers on `/mcp`, so the three arrive together only through a via
  door. The gateway does not check the assertion (it has no key); it passes it
  on, and the platform checks it again at the source's door.
- **The way in** `platform` must be among the view's ways; otherwise `403`.
- **The payer** is an access profile (§2.3) whose groups name `@<chat>` (the
  chat's instance name) or `@*` (every chat of the tenant): first a profile
  naming the chat, else one with `@*`. A profile with `*` does **not** apply —
  it was made for sign-ins at the identity provider, not for every chat.
  No profile: `403`. Group entries are `/path`, `*`, `@<instance>` or `@*`.
- **The person** is the user id with issuer `platform`; the downstream session
  belongs to that person and the profile (§3.5), and every request with a new
  assertion updates the one the session uses — the browser drives the loop,
  every round brings a fresh one (RFC-0074 D7).
- **To a source of the platform** (access `platform`, §3.7): the gateway calls
  the door with its sources key and the assertion as `X-OAAP-Act-Assertion`,
  instead of exchanging a token. No call to the identity provider.
- **To a server with procedure X** (§3.5) there is no provider token: the call
  is refused (`-32003`, a sentence naming procedure A), measured as
  `refused`, not counted for the circuit breaker.
- **`X-OAAP-Assistant`**, when the chat sends it and it matches
  `[a-z0-9][a-z0-9-]{0,47}`, is recorded; no decision depends on it.
- **Measured as** procedure `A` with `user_sub` = the person's id,
  `user_iss` = `platform`, `client` = the chat, `assistant`.
- A key at a view that accepts only `platform` is `401`, as any key at a view
  without `key`.

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

For reading, the gateway declares **all three** server-to-client
capabilities (`elicitation`, `roots`, `sampling`) at `initialize`:
some servers offer tools only to clients that can be asked back — the
official reference server shows 16 tools without and 20 with them
(measured 2026-11-02). The catalog session calls nothing, so nothing is
asked. For calls, §6.1 holds: an upstream session declares only what
the view passes and the client declared, so such a tool may be missing
at the server when it is called; that is the server's answer and
passes through unchanged.

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

### 4.3 Views of tools (0.8.0, MCP Apps, RFC-0075)

A tool may name an interactive view (`_meta.ui.resourceUri`, a `ui://` URI;
extension `io.modelcontextprotocol/ui`). The gateway:

- keeps `_meta.ui.resourceUri` and `_meta.ui.visibility` in the tool's pinned
  text (the flat legacy `_meta["ui/resourceUri"]` is read and translated);
  other `_meta` fields of the server are not part of the text;
- when reading the catalog, reads every view a tool names with
  `resources/read` and stores it as a resource of the catalog with the
  **SHA-256 of its content**, its MIME type (it must be
  `text/html;profile=mcp-app`) and `_meta.ui` (`csp`, `permissions`,
  `domain`, `prefersBorder`) — a server may leave views out of
  `resources/list`;
- approves the view **together with its tool**: approving the tool adds
  exactly that one resource to the view; a tool whose view could not be read
  is not approved;
- at `resources/read` of a view, compares the content with the pinned hash;
  a different content is answered with an error (`-32002`, usage reason
  `ui_changed`) and none of it reaches the client;
- treats a tool as **suspended** while its view in the same view is not
  active; confirming the tool confirms its current view;
- passes `_meta.ui` on in `tools/list` (beside `oaap/effect`) and on the
  view's resource entry. `visibility: ["app"]` is passed on; hiding such a
  tool from the model is the host's duty (the gateway cannot tell who calls).

## 5. Views

A view has a name (`[a-z0-9-]`, the path segment), the **ways in** it
accepts (a comma list of `key`, `signin`, `platform` in this order, §2,
§3.9; default `key`, and a view carried over from 0.2 keeps `key`), a
**highest effect class** (default `read`),
a setting for **server-to-client requests** (§6.1) and a list of
**entries**. An entry is one catalog entry of
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

**The class reaches the client (0.7.1).** To a client on protocol
`2025-06-18` or newer, `tools/list` adds to every tool
`"_meta": {"oaap/effect": "<class>"}` — the class the operator set in this
view, not the server's annotation, which is passed on unchanged beside
it. A chat asks the person before every tool whose class is not `read`
(RFC-0074 D6) and treats a tool without this field as `write`. Older
protocol versions have no `_meta` on a tool; they get none.

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
- **Sessions.** A downstream session belongs to the key — or the
  person (issuer and `sub`) and their profile — and the view that opened
  it; presented with another key or by another person it is unknown
  (`404`). A person's token may be renewed during a session; every
  request carries a valid one. A
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
reaches the gateway with a valid key or person and a session: time, key
or access profile, for a person their `sub` and issuer (RFC-0065 D16),
view,
**kind** (`tool`, `resource`, `template`, `prompt`), **name in the
view**, server, **name at the server**, access procedure (`T` or `X`), outcome,
duration, **bytes up** (the client's request body) and **bytes down**
(what the client received), and the **context snapshot** of the key
(`oaap.ai.gateway` §5). For procedure A also the chat, the assistant and
(0.7.2) **`confirmed`**: `yes` when the chat sent `X-OAAP-Confirmed: yes`
— the person confirmed this call in the chat (RFC-0074 §5.6). It is the
chat's statement, recorded for review, never a permission.

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
`project`, `cost_center`, `application`, `owner`, `key` (a key or an
access profile), `user` (the `sub`), `view`, `kind`, `tool` (the name in
the view), `server`, `outcome`, `day`, `month`; metrics `calls`,
`bytes_up`, `bytes_down`; `complete_until` in every answer. Volume,
never money. `GET /report/v1/keys` lists keys with their current
context and views, never a key value.

## 10. Never recorded

**No tool argument, no tool result, no resource content and no prompt
text** in any log, usage row, audit entry or error message — in any
operating mode (RFC-0065 D11). **No token** — neither a person's nor an
exchanged one — and no name or e-mail of a person. The usage table has no column a payload
would fit into. Access log lines carry method and path only.

## 11. Configuration

| Variable | Meaning |
|---|---|
| `MCPGW_MASTER_KEY` | key to the vault for server credentials (secret, `generate: token`) |
| `MCPGW_CATALOG_MINUTES` | catalog re-read interval, default 15, 0 = only on demand |
| `MCPGW_ISSUER` | the tenant's issuer, exactly as in `iss` (e.g. `https://auth.<node>/realms/<tenant>`); empty = sign-in off (§2.2, RFC-0065 D14) |
| `MCPGW_AUDIENCE` | the value a sign-in token must carry in `aud`: the client id of the gateway's confidential client (§2.2, §3.5) |
| `MCPGW_SIGNIN_CLIENT` | the id of the public client persons sign in with — only shown on the operator page and in the line for Claude Code (RFC-0065 D15) |

Servers, views and keys are maintained on the operator page and through
the command line inside the container (`app.py key|server|view …`).

## 12. Conformance tests (described)

1. A key without views reaches no view; no key, unknown, revoked and
   unentitled keys get byte-identical `401` answers (§2).
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
    allows only the better server gets the same `401` as everyone else.
18. A server that no longer declares a capability leaves its entries of
    that kind `missing`.
19. `server/discover` and a request with a version in `_meta` without a
    session get `400` with an error code outside `-32020`…`-32099`.
20. A database of 0.1 is carried over with every approval intact
    (same fingerprint, still `active`), and its views keep refusing
    server-to-client requests.
21. A read through a template records the template, never the filled-in
    URI; a refused unapproved URI is not recorded.
22. No credential, unknown and revoked keys, tokens that fail any check
    (wrong signature, `alg` other than RS256, wrong issuer, wrong
    audience, expired), a view that does not exist or does not accept the
    way in: byte-identical `401` with the same `WWW-Authenticate`.
23. The resource metadata names the configured issuer for every view
    name alike; without an issuer it is `404` for every view alike.
24. A `jwks_uri` on another origin than the issuer is not fetched.
25. A valid token whose groups match no profile for the view gets
    `403`; one that matches is billed to that profile with its `sub`; a
    person with two profiles for two views reaches both; a view limited
    to `key` answers a valid token with `403`, a view limited to
    `signin` answers a valid key with the `401` of §2; a person's
    session is unknown to another person of the same profile, and the
    profile's rate counts per person.
26. A server with procedure X receives a token whose audience is the
    configured backend, never the person's token and never a technical
    credential; when the exchange fails, or the call came with a key,
    the server is not called.
27. The usage row of a signed-in call carries profile, `sub` and issuer;
    no row, log line or page contains a token.

## 13. Dependencies

`oaap.core.gateway` (public route, identity headers), `oaap.apps.runtime`
(manifest, storage, configuration), `oaap.net.destinations` (§3.1),
`oaap.ai.gateway` (shared books), RFC-0068 (egress).

## 14. Not in 0.3

- **MCP `2026-07-28` itself** (stateless, without `initialize` and
  sessions, server-to-client requests as multi round-trip results,
  `subscriptions/listen` instead of `GET` and `resources/subscribe`).
  0.2 is recognizable as a session-based server (§6.2); speaking the new
  era is a redesign, not an addition.
- **Resource subscriptions and list-change notifications** toward the
  client: they need a server-initiated stream (`GET`), which 0.2 does
  not open; in the `2026-07-28` era they are replaced altogether.
- `completion/complete` and `logging/setLevel`.
- Procedure P (0.4, RFC-0066); P-saml and Entra (0.5); `pattern` and
  `format` enforcement in input schemas.
- Signature algorithms other than RS256; several issuers per gateway.
- Creating the clients in the realm: by hand in 0.3, a job of the IdP
  connector later (RFC-0065 D15).
- Scopes: the gateway names none and checks none; the access profile
  decides.

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

**Neu in 0.3 (RFC-0065 Stufe 3, deine Entscheidungen D14–D16):**

- **Zwei Wege hinein:** ein Schlüssel oder ein angemeldeter Mensch.
- **Anmeldung:** Der Mensch meldet sich am Keycloak des Mandanten an. Den
  Issuer trägt der Betreiber in die Konfiguration ein (D14). Claude Code
  nimmt dafür einen fest angelegten öffentlichen Client, dessen ID es
  mit `--client-id` bekommt (D15).
- **Tokenprüfung:** Das Gateway prüft das Token selbst: RS256, Signatur,
  Issuer, Audience, Ablauf. Die Schlüssel holt es nur von der Adresse
  des Issuers.
- **Zugangsprofile:** Wer zahlt, entscheidet ein Zugangsprofil, das über
  die Keycloak-Gruppen zugeordnet wird. Es trägt denselben Kontext wie
  ein Schlüssel. Die Rate gilt je Mensch, das Budget für das ganze
  Profil.
- **Messzeile:** Sie trägt den Menschen als `sub` mit Issuer, nie mit
  Namen oder E-Mail (D16).
- **Einheitliche 401:** Jede Ablehnung ist dieselbe `401`, auch für
  Schlüssel. Nur wer gültig angemeldet ist, die Sicht aber nicht
  benutzen darf, bekommt `403`. Eine 401 schickte den Client sonst in
  eine neue Anmeldung, die nichts ändert.
- **Profilwahl je Sicht:** Das Profil wird unter denen gewählt, die die
  Sicht nennen. Sonst käme jemand mit zwei Profilen für zwei Sichten nie
  in die zweite; das hat der Test gefunden.
- **Verfahren X:** Das Gateway tauscht das Token des Menschen bei
  Keycloak gegen eines nur für das Backend. Das Token des Menschen
  selbst gibt es nie weiter. Klappt der Tausch nicht, wird abgelehnt,
  nie auf den technischen Zugang ausgewichen. Eine Sicht mit so einem
  Server nimmt nur Anmeldungen an.

## Deutsche Zusammenfassung (0.4, RFC-0073 Stufe 1 — Quellen der Plattform)

Ein Gateway mit `mcp_sources: {read: true}` im Manifest liest beim Start und
alle 5 Minuten die Liste der MCP-Apps seines Mandanten auf diesem Knoten
(nach einem Fehlschlag nach 30 Sekunden wieder). Jede wird ein Server mit dem
Namen der Instanz, Zugang `none`, Ampel rot. In keiner Sicht erscheint etwas
ohne Freigabe. Was der Betreiber einstellt (Zugang, Schlüssel, Ampel), bleibt
bei jedem Abgleich stehen; in Stufe 1 ist das der Schlüssel eines Agenten, auf
die Instanz beschränkt. Ein von Hand vergebener Name wird nicht angefasst. Eine
verschwundene Quelle bleibt markiert stehen, ihre Einträge in den Sichten
werden nicht still entfernt.

## Deutsche Zusammenfassung (0.5, RFC-0073 Stufe 2 — Verfahren I)

Eine Quelle, für die die Liste eine Tür nennt, wird mit Zugang `platform`
eingetragen. Ruft ein angemeldeter Mensch über eine Sicht ein Tool dieser
Quelle, tauscht das Gateway sein Token mit dem **eigenen** Client gegen eines
für den Plattform-Client des Realms und ruft die Tür auf seiner eigenen Seite
mit dem Quellen-Schlüssel und diesem Act-Token. Die App sieht den Menschen,
das Gateway reicht sein eigenes Token nie weiter. Ohne Menschen kein Aufruf;
eine Sicht mit so einem Server nimmt nur Anmeldungen an. Lehnt die Plattform
die Person ab (Route, Bindung, Token), geht ihr Satz an den Client, gemessen
als `refused`, **ohne** den Sicherungsautomaten zu zählen. Neue Einstellungen:
`MCPGW_CLIENT_SECRET`, `MCPGW_PLATFORM_AUDIENCE`. Agenten bleiben bei Verfahren
T mit eigenem Schlüssel.

## Deutsche Zusammenfassung (0.6, RFC-0073 Stufe 3 — Einstellungen von der Plattform)

Die fünf Einstellungen für Anmeldung und Verfahren I (`MCPGW_ISSUER`,
`MCPGW_AUDIENCE`, `MCPGW_SIGNIN_CLIENT`, `MCPGW_CLIENT_SECRET`,
`MCPGW_PLATFORM_AUDIENCE`) nehmen, wenn sie leer sind, den Wert der Plattform
(`OAAP_MCP_IDP_*`). Ein von Hand gesetzter Wert gewinnt, einzeln je Einstellung.
Die Betreiberseite sagt für jede, woher sie kommt; das Geheimnis zeigt sie nie.

## Deutsche Zusammenfassung (0.7, RFC-0074 Stufe 1 — Verfahren A)

Ein Chat der Plattform trägt den Menschen her: Die via-Tür auf der Seite des
Chats setzt die sechs Kopfzeilen der Person (Zusicherung an dieses Gateway)
und `X-OAAP-MCP-Client`. Sind diese drei da, ist es Verfahren A. Die Sicht
braucht dafür den Zugang `platform` (Zugänge jetzt als Liste aus `key`,
`signin`, `platform`). Wer zahlt, sagt ein Zugangsprofil mit `@<chat>` oder
`@*`; ein `*`-Profil gilt hier ausdrücklich nicht. Gegenüber einer Quelle der
Plattform reicht das Gateway die Zusicherung als `X-OAAP-Act-Assertion`
weiter — kein Token-Tausch. Verfahren X geht so nicht und wird mit Satz
abgelehnt. Gemessen wird Verfahren `A` mit Kennung der Person, Issuer
`platform`, Chat und Assistent (nur zur Auskunft).

## Deutsche Zusammenfassung (0.7.1, RFC-0074 Stufe 2)

`tools/list` nennt jetzt je Werkzeug die Wirkungsklasse, die der Mandant in
der Sicht gesetzt hat: `_meta: {"oaap/effect": "read" | "write" |
"execute"}` (ab Protokoll 2025-06-18). Die Angaben des Herstellers
(`readOnlyHint` usw.) bleiben daneben unverändert. Der Chat fragt vor jedem
Werkzeug, das nicht `read` ist, und behandelt eines ohne diese Angabe wie
`write`.

## Deutsche Zusammenfassung (0.7.2, RFC-0074 Stufe 3)

Die Messzeile hat eine Spalte `confirmed`: `yes`, wenn der Chat meldet, die
Person habe diesen Aufruf bestätigt (`X-OAAP-Confirmed: yes`, nur bei
Verfahren A) — eine Angabe des Chats, keine Erlaubnis. Und: Auf der
Betreiberseite liest das Gateway den Katalog einer Quelle der Plattform jetzt
mit der Zusicherung der angemeldeten Betreiberin. Vorher ging das nur mit
einem Token des Anmeldediensts — ein Mandant ohne Keycloak konnte die
Werkzeuge seiner eigenen Apps nie in eine Sicht nehmen.

## Deutsche Zusammenfassung (0.7.3)

Sichten, Wirkungsklasse und Ampel eines Schlüssels oder Zugangsprofils lassen
sich jetzt ändern, ohne ihn zu widerrufen (Betreiberseite „Ändern“, Kommandozeile
`key set`); ein Schlüssel behält seinen Wert. Eine 403 nennt den echten Grund:
Sicht nicht im Profil, Zugang der Sicht fehlt, oder Ampel der Sicht über der des
Profils — dieselben Sätze stehen auf der Betreiberseite neben jedem Profil.
Vorher hieß jeder Fall „kein Zugangsprofil“. Dazu ein Knopf „Quellen jetzt
einlesen“ statt bis zu 15 Minuten Warten.

## Deutsche Zusammenfassung (0.8.0, RFC-0075 Stufe 1 — Ansichten)

Ein Tool kann eine Ansicht `ui://…` mitbringen (MCP Apps). Das Gateway liest sie
beim Katalog-Lesen und hält ihren Inhalt per SHA-256 fest. Wer das Tool
freigibt, gibt genau diese eine Ansicht mit frei; ohne lesbare Ansicht keine
Freigabe. Liefert der Server später etwas anderes, geht davon nichts an den
Client, und nach dem nächsten Katalog-Lesen sind Ansicht und Tool gesperrt, bis
jemand das Tool bestätigt. Im festgehaltenen Text des Tools steht nur `_meta.ui`.
