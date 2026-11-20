# oaap.ai.mcp-gateway — Tool Servers Behind One Keyed Endpoint per View

- **ID:** `oaap.ai.mcp-gateway`
- **Version:** 0.31.0 (a person with a backend user of their own reads the **first** catalog of a procedure-P server from `/me`, as themselves, with the assertion the platform gives that page -- no operator role needed; never again once read, never without an assertion; nothing approved, §3.10; reference mcp-gateway 0.33.0). 0.30.0 (**target systems and multi-system views**: a system landscape of the gateway -- title, role, active, kind, non-secret facts, servers, a light from the role and never looser than a server -- and views shaped once on a reference system and served for further systems; each tool once with a required `system` argument the gateway routes by, per entry and system *gleich* / *freigegeben* / *abweichend* / *fehlt*; the gateway's tool `systeme`; usage rows record the system; setup kind `system`, §5.5, RFC-0114 stage 1; reference mcp-gateway 0.32.0). 0.29.0 (the setup door's kind **`server`**: a server behind a destination of the platform -- only `destination:<binding>[/path]`, auth `propagate` or `none`, a light; a human's change is a conflict, remove only while unchanged; ready once a person has read its catalog, §3.9e, RFC-0109 §12; reference mcp-gateway 0.31.0). 0.28.0 (the setup door **lists** its items: `GET ?kind=` without `id` for `refresh`/`server_light` (servers with light), `view`, `profile` (valid ones, ceiling as light), `assistant` (not deleted) -- never a key, digest, credential or a server's address, §3.9e, RFC-0109 §4; reference mcp-gateway 0.30.0). 0.27.0 (RFC-0109 D12: the setup door **brings back** a profile or an assistant that it removed itself -- proven by the gateway's own audit trail, never by a human's revoke or delete, never a key -- so a recipe can run again after an undo, §3.9e; reference mcp-gateway 0.29.0). 0.26.0 (RFC-0107: **client templates** -- the configuration file for a tool (Claude Code, VS Code, opencode) from a key's views or picked views, per way, the key only as the variable `OAAP_MCP_KEY`, never its value; self-service `GET /mcp/_client-config` with the key and `/me/client-config` for sign-in views, §2.4; additive, reference mcp-gateway 0.28.0). 0.25.0 (RFC-0104: **the setup door**, kinds `refresh`, `server_light`, `view`, `profile`, `assistant`; items name servers and chats by their node key, §3.9e; additive, reference mcp-gateway 0.27.0). 0.24.0 (RFC-0103 D10: `POST …/<id>/cases` may carry `outcome` -- `accepted`, `reopened` or `no_response`, the last one counts; the evaluation per revision counts `accepted` next to the cases, §3.9d; additive. 0.23.0: RFC-0097 stage 2 / RFC-0101 stage 4: **evaluation per assistant and revision** -- calls, refusals, errors and persons (counted) from the usage rows, stars and "not satisfied" cases per revision; a diff of two revisions; export of a chosen revision; the operator's page gets a tab `Assistenten`; a chat counts a case with `POST …/<id>/cases`, §3.9d; additive. 0.22.0: RFC-0101 stage 3: an assistant may carry `support_queue` (`oaap.ai.assistants` 0.6), checked by the shared rule and kept with its revision, §3.9b; additive. 0.21.0: RFC-0101 stage 2: **ratings** -- 0–5 stars per answer or conversation, stored next to the assistant's revisions with the circumstances, the person only as an HMAC with a key of this gateway, text only with the person's tick, read by whoever manages the assistant and the `tenant_admin`, §3.9c; revisions a rating names are not compacted; additive. 0.20.0: RFC-0097 stage 1: **assistants** live here with revisions, read and written by a person carried by a chat through the via door at `/mcp/_assistants`, visibility by the shared rule and the gateway's own authorization object `assistant`; the usage row records `assistant_rev`, §3.9b, §9; additive. 0.19.0: a request may carry `X-OAAP-Light`, an additional ceiling for that request that can tighten the key's or profile's ceiling and never loosen it; a view worse than it is refused with `403` and a sentence; checked on every request, also inside a session; usage rows record it, §3.3, §9, RFC-0101; additive. 0.18.0: the operator's page says what `*`/`/pfad` and `@<chat>`/`@*` stand for, and a profile whose groups do not fit the view's way is told which group to write instead of being told to switch on the other way, §2.3 (L12); the light warning names the server that sets the view's light, uses the colour words and both remedies, §2.3 (L13); the sign-in tab says the `tenant_admin` may set sign-in up, §2.2 (L4)). 0.17.0 (the **groups** of an access profile can be changed on the operator's page, checked before anything changes, §2.3 (L11); the sign-in tab links the instance's page in the portal from `OAAP_PORTAL_URL` (runtime 2.38) and says the `MCPGW_*` fields stay empty when the platform sets sign-in up, §2.2 (L1, L5)). 0.16.1 (L29: the catalog of a procedure-U server is read by the operator without an assertion, and a person with a stored credential may read the **first** list from `/me`, §3.12). 0.16.0 (procedure U also as **`basic`**: the person enters user (e.g. e-mail) and token separately, the gateway sends `Authorization: Basic base64(user:token)` -- what Atlassian Cloud's MCP server asks for, §3.12). 0.15.0 (RFC-0095 stage 3: **readiness** -- `GET /mcp/_readiness?view=` through the via door tells a chat per server whether the view is set up for the person (`ready`, `needs_credential`, `credential_rejected`, `not_for_you`), `/me/v1/readiness`; D2: `/me` and procedure U also for calls signed in at the realm, when the platform names the person's realm id and promises the header, §1b). 0.14.0 (RFC-0095 stage 2: **procedure U**, §3.12 -- a server where every person brings their own credential; entered on `/me`, write only, sealed in the vault bound to the person, sent only with that person's calls; refused before anything goes out when missing; the operator counts and deletes, never reads). 0.13.1 (an old row refused/destination without a door does not guess who refused, §1a). 0.13.0 (RFC-0095 stage 1: **`/me`**, the person's own page -- their usage rows of the last 30 days, a refusal in words with who refused, §1a; usage rows gain two structured columns **`status`** and **`door`**, §9. 0.12.0: servers can be **renamed**, §3.11 -- catalog and entries follow, a source server is found by its origin; `GET /mcp/_views` lists the views a person carried by a chat can open, all of them with reasons for the tenant's administration, §3.9a. 0.11.0: views can be **copied and renamed**, §5.4 -- a rename moves the keys and profiles that name the view; entries can be **assigned in bulk**: a set of catalog entries per view in one step, same approval per entry, §5.1. 0.10.0: RFC-0066 for the gateway: **procedure P**, §3.10 -- a person carried by a chat of the platform reaches a backend such as SAP as themselves, through a destination with principal propagation; `destination:<need>/<path>`, §3.1). 0.9.0 (RFC-0073 §16: the catalog of a platform source is read without a person at the platform's discovery door -- only the lists, as the gateway's machine principal; calls stay bound to a person, §3.7). 0.8.0 (RFC-0075 stage 1: views of MCP Apps are read, pinned by
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
Since 0.10 the gateway also carries a person from a chat of the platform
into SAP (procedure P, §3.10): through a destination with principal
propagation, whose certificate the platform issues -- the gateway holds
none (RFC-0065 §6, RFC-0066).

## 1. Routes

| Path | Role in the manifest | Who |
|---|---|---|
| `/mcp/<view>` | `public` | MCP clients, with a gateway key or a sign-in token (§2) |
| `/.well-known/oauth-protected-resource…` | `public` | MCP clients looking for where to sign in (§2.2) |
| `/report/v1/…` | `admin` | a billing system with a platform API key (RFC-0027) |
| `/me`, `/me/v1/…` | `user`, `keyuser`, `admin` | the person whose calls run through the gateway (0.13, §1a) |
| `/` and everything else | `admin` | the operator |
| `/healthz` | — | the platform |

`/mcp/<view>` is `public`: the platform authenticates nothing there,
strips client-sent identity headers and brakes per client address
(RFC-0010); the `Authorization` header passes unchanged. The gateway
authorizes every request itself.

### 1a. The person's page (0.13, RFC-0095 stage 1)

The platform authenticates `/me` like any `user` route and sets
`X-OAAP-User-Id`. The gateway shows **only usage rows with issuer
`platform` and exactly that `sub`** -- the calls the platform carried
(procedures A, P, I) -- of the last **30 days**. Key calls have no
person and never appear; calls of a client signed in at the realm
(§2.2) appear once the platform passes the person's realm `sub`
(RFC-0095 D2, not in 0.13). Without `X-OAAP-User-Id`: `403`, nothing
shown.

- `GET /me` -- a page: time, view, kind and name in the view, chat and
  assistant, procedure, outcome, duration; filters "only problems"
  (default when the last 7 days hold one), view, day.
- `GET /me/v1/calls?problems=0|1&view=&day=YYYY-MM-DD` -- the same as
  JSON: `{"v":1,"days":30,"filter":{…},"calls":[{time, view, kind,
  name, client, assistant, procedure, outcome, reason, status, door, ms,
  sentence, hint}],"note":…}`.

Every outcome other than `ok` gets a **sentence made from the row's
codes** (`outcome`, `reason`, `status`, `door`) and a hint what the
person can do -- never from recorded text; there is none (§10). A row
from before 0.13 (no `door`) gets the door its outcome implies -- except
`refused`/`destination`, which before 0.13 meant either that the gateway
could not carry the person or that the destination refused: its sentence
names both and no door (0.13.1).

### 1b. Readiness and the person's realm id (0.15, RFC-0095 stage 3, D2)

**Readiness.** `GET /mcp/_readiness?view=<view>` -- only through the
platform's via door, like `/mcp/_views` (§3.9a); otherwise the one
denial. For the carried person: when no access profile of the chat
opens the view (or its way or light does not fit), `state:
"not_for_you"` with the reason and **no servers** -- the same answer
for a view that does not exist. Otherwise per server of the view's
active entries: `state` `ready` (nothing needed from the person),
`needs_credential` (procedure U, no credential stored, with the
operator's hint and link) or `credential_rejected` (the last call of
this person to this server since the credential was stored was
`refused`/`credential`), the number of tools and entries; overall
`ready`, `missing_tools` and `me` -- the gateway's own `/me` address
from `OAAP_INSTANCE_NAMES`, or empty. The chat maps assistants to
views (RFC-0095 D9); the gateway knows no assistants.
`GET /me/v1/readiness` lists the person's procedure-U servers and their
state.

**The realm id (D2).** On `/me` the platform sends `X-OAAP-User-Idp:
<issuer> <sub>` (`oaap.core.identity` 2.14). The gateway believes it
only when `OAAP_IDENTITY_HEADERS` names it (runtime 2.37) and the
issuer is its own (`MCPGW_ISSUER`). Then `/me` also shows the rows of
that realm id, and the gateway remembers the link (realm id → platform
id; audit `person.link`, ids only). A call signed in at the realm to a
procedure-U server uses the credential of the linked platform id;
without a link it is refused with the hint to open `/me` once. The
link is set only on `/me`, never from an MCP request.

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

(0.17, L1/L5) Where the platform sets sign-in up (the portal's button
„Anmeldung einrichten“, `oaap.core.portal` 2.16), the `MCPGW_*` fields of
the instance's configuration stay **empty** -- the configuration's
labels and the sign-in tab say so, and the tab links the instance's
page in the portal (`OAAP_PORTAL_URL`, `oaap.apps.runtime` 2.38), card
MCP; without that variable it names the way in words.

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
  groups is audited with old and new value. (0.17) The operator's page
  changes them together with views and limits; the groups are checked
  first, so a wrong group changes nothing at all.
- (0.18, L12) The page says the two kinds of group plainly: `*` and full
  paths mean persons who sign in **at the gateway** (the view needs the
  way „Anmeldung“); `@<chat-instance>` and `@*` mean persons a chat of the
  platform carries (way „Plattform“), and `*` does **not** cover a chat.
  When a profile's groups are of the one kind and the view has only the
  other way, the warning says which groups to write, rather than telling
  the operator to switch on a way the case does not need.
- (0.18, L13) When a view's light is above a profile's ceiling, the
  sentence names the light in words (grün, gelb, rot), the server that
  sets it (the worst one, §9.3), and both remedies: raise the profile's
  ceiling, or -- if the server is less sensitive than rated -- rate it
  lower; new sources start red. "Lower the source's light" alone was
  read the wrong way round.
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

### 2.4 Client templates (0.26, RFC-0107)

The gateway writes the configuration file with which a tool uses its
views. **A template is data** shipped with the app (`templates/<tool>.json`),
never uploaded by an operator; each names the format it follows and the
date that format was checked against the tool's documentation. Shipped:
`claude-code`, `vscode` (Copilot's own format, key way only until a
sign-in from VS Code against a realm is measured) and `opencode`.

- **Per view a way:** `key` or `signin`. A view is offered for a way only
  if it has that way (§2) and the template offers it. A view with only
  `platform` cannot be put in a file. `signin` needs the issuer and the
  public client (`MCPGW_SIGNIN_CLIENT`); without them there is no file.
- **The key's value is never in a file**, on any path. A template has no
  placeholder for it and is refused at start if it contains `mcp-oaap-`;
  the key way writes the environment variable `OAAP_MCP_KEY` in the tool's
  own syntax. The value appears only once, when the key is issued (§2.1).
- **Operator's page** (role `admin`), tab "Vorlagen": the tool, then the
  views from a key or by hand; the file to copy or download (attachment,
  `Cache-Control: no-store`). From a key, a view the key could not open on a
  call (`why_not`, §2.3, e.g. its light above the key's ceiling) is left
  out and named with the reason.
- **`GET /mcp/_client-config?target=<tool>`** with the key: the file for
  that key's views on the way `key`. A missing, wrong or revoked key gets
  the same `401` as every request under `/mcp`; an unknown tool `400` with
  the list; no view a tool can reach `409` with the reasons. Recorded in
  the audit trail (`client.config`, the key's label and the tool), never as
  usage.
- **`GET /me/client-config?target=<tool>`** (route `/me`, §1a): the file on
  the way `signin` for the views that take sign-in and that some access
  profile opens. The person's groups at the realm are not known here (the
  platform gives apps no groups, `oaap.core.identity` §2), so the page says
  for a profile with groups other than `*` that the sign-in decides. A view
  with a procedure-U server whose credential the person has not stored is
  marked "erst Zugang hinterlegen".

## 3. Servers

A server is an MCP endpoint speaking **Streamable HTTP**. stdio is not
supported (RFC-0065 D2).

| Field | Meaning |
|---|---|
| name | `[a-z0-9-]`, unique; shown to the operator, never to a client |
| address | an `http(s)://` URL, or `destination:<need>[/<path>]` (§3.1) |
| access | procedure **T**: `none`, `bearer`, `basic` or `header:<Name>`; or procedure **X**: `exchange` (§3.5); or procedure **P**: `propagate` (§3.10); a credential is stored only encrypted (§3.4) |
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
- **`destination:<need>/<path>`** (0.10) appends the path to the
  destination's target: `destination:sap-a4h/zmcp2/bc/access-support` is
  `https://<target>/zmcp2/bc/access-support`. A path with a `..` segment,
  a query or a fragment is refused when saving and when connecting -- it
  must not lead out of the destination.
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

### 3.3a A ceiling per request (0.19, RFC-0101)

A request may carry **`X-OAAP-Light: green | yellow | red`** — the light
of the conversation the person chose in the chat (`oaap.ai.gateway` §7,
"A ceiling per request"). It tightens the ceiling of the key or profile
for this request and never loosens it. After the key or profile has been
checked (§2.3), a view whose light (§3.3) is worse than the requested
light is refused with **`403`** and a sentence naming both lights and the
server that sets the view's light — the requester may open the view, so
the sentence reveals nothing new. The check runs on **every** request,
also inside an open session: a person who switches the conversation to
`green` gets the very next call refused. An unknown value is refused with
`400`. The usage row records the requested light (§9).

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

**Reading its catalog without a person (0.9, RFC-0073 §16).** When the
sources list names a `discover` door for the source (`oaap.apps.runtime`
2.32.5), the gateway reads the catalog there whenever no person is at hand —
after a source appears, every `MCPGW_CATALOG_MINUTES`, and on the operator's
page without an assertion: `Authorization: Bearer <sources key>`, no act
credential, only `initialize`, `notifications/initialized`, the four lists,
reading the views (`ui://`) its tools name (§4.3) and closing the session.
The platform passes nothing else. The source sees
the gateway's machine principal and may list differently than for a person;
the sentence after reading says „Als Gateway gelesen“. With a person, the
gateway reads through the door of procedure I as before. Calls are never
made at the discovery door. Without a `discover` door (a platform before
reference 0.1.300) the sentence names the button and `--token-stdin`.

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

### 3.9a Views for a person carried by a chat (0.12)

`GET /mcp/_views` answers only a request through the platform's via door
(chat, person and assertion set, §3.9); anything else gets the one denial
of §2. It lists the views this person may open from this chat -- by the
same rule as a call: a profile naming `@<chat>` or `@*`, the way
`platform`, the light -- each with the number of active tools, prompts
and resources, its light and highest effect class. A person whose roles
include `tenant_admin`, `server_admin` or `admin` gets **all** views, the
others marked with the reason they are closed, so the administration sees
what is still to set up. Only names, counts and reasons, never an
entry's text. `_views` can never be a view's name (§5).

### 3.9b Assistants (0.20, RFC-0097 stage 1)

Assistants (`oaap.ai.assistants` §2a) live in this gateway, next to the
views they name. Every route below answers only a request through the
platform's via door (§3.9: chat, person, assertion); anything else gets
the one denial of §2. Who sees and who manages follows the assistant's
visibility: `private` its owner, `context` whoever holds `assistant.use`
or `assistant.manage` in that team (the gateway declares the object
`assistant` itself; without readable grants nobody sees a team
assistant), `tenant` everyone, managed by `tenant_admin`.

| route | answer |
|---|---|
| `GET /mcp/_assistants` | the assistants this person may use, current revision, with `rev`, `state`, `manage`; `inactive` only for whoever manages it |
| `GET /mcp/_assistants/<id>[?rev=n]` | the current or a given revision; `410` when compacted; `404` for one the person may not see — the same answer as for none |
| `GET /mcp/_assistants/<id>/revisions` | number, time, author, compacted — only for whoever manages it |
| `POST /mcp/_assistants` | save: checked by the shared rule, the view must exist here, `rev`/`state`/`manage` from the writer are refused; the owner of an existing assistant stays, a new one belongs to the writer; answers the new `rev` |
| `POST /mcp/_assistants/_import` | an exchange file, all or nothing; the importer becomes owner |
| `POST /mcp/_assistants/_migrate` | a chat's old file, all or nothing, owners kept, existing ids refused — only `tenant_admin` |
| `POST /mcp/_assistants/<id>/state` | `active`, `inactive`, `deleted` — whoever manages it |

Every save is an audit entry (`assistant.save`, `.import`, `.migrate`,
`.state`) with the new revision. Retention (D6): every revision a usage
row names, plus the last 20; older revisions are compacted — number,
time and author stay, the text goes. `_assistants` can never be a view's
name (§5).

### 3.9c Ratings (0.21, RFC-0101 stage 2)

A person rates an answer or a whole conversation with 0–5 stars
(`oaap.ai.assistants` §2b). The chat sends the rating through the via
door as that person; the same routes and the same visibility as §3.9b.

| route | answer |
|---|---|
| `POST /mcp/_assistants/<id>/ratings` | `{rev, scope: answer\|conversation, round, conversation, stars: 0–5\|null, model, model_light, light, view, gateway, tools: [{name, effect, outcome}], ms, text?: {question, answer}}`; `404` for an assistant the person may not see, as for none; `rev` must exist; the same person, conversation, scope and round replace; `stars: null` withdraws |
| `GET /mcp/_assistants/<id>/ratings` | per revision: count, distribution of 0–5, share of 0–2, number of persons; and the latest 500 ratings without the person — for whoever manages it and the `tenant_admin` (only among assistants they can see) |
| `GET /mcp/_assistants/_ratings` | the person's own ratings |

- **The person** is stored only as `who` = HMAC-SHA256 of the user id
  with a key of this gateway (`/data/ratings.key`, 32 bytes, 0600,
  created on first use). The conversation id is stored only inside a
  second HMAC (`slot`, with scope and round). Enough to replace one's own
  rating and to count persons, not enough to name them.
- **No content without the tick.** The gateway stores only the fields
  above; of `tools` only name, effect class and outcome. Arguments or
  results a chat sends anyway are dropped. `text` (at most 8,000
  characters each) only when the person ticked „Frage und Antwort
  mitgeben“; after 180 days the text goes and the rating stays.
- **Retention of revisions** (§3.9b, D6) also keeps every revision a
  rating names.
- Ratings are a record of their own; §10 stays true for usage rows.

### 3.9d Evaluation per revision (0.23, RFC-0097 stage 2, RFC-0101 stage 4)

| route | answer |
|---|---|
| `GET /mcp/_assistants/<id>/evaluation` | per revision: `changed_at`, `changed_by`, `compacted`; from the usage rows `calls`, `refused` (refused or limited), `errors` (tool or upstream error), `persons` (distinct, counted); `ratings` {count, stars[0..5], low, persons}; `cases`; plus `usage_since` (the oldest usage row) -- same readers as the ratings (§3.9c) |
| `GET /mcp/_assistants/<id>/diff?a=&b=` | the unified diff of two revisions (fields, then the system prompt); `404` with a sentence for a compacted one -- for whoever sees the assistant (who may read any revision anyway) |
| `POST /mcp/_assistants/<id>/cases` | `{rev, number, outcome?}`: a "not satisfied" case went to `vorgaenge` for this revision; counted once per person and case. Stored: assistant, rev, `who` (the HMAC of §3.9c), `slot` = HMAC of person and case number, time, and (0.24.0, RFC-0103 D10) `outcome` -- `accepted`, `reopened` or `no_response`, the last one sent counts. **Not** the number, no content |

- The **operator's page** (role `admin`) gets a tab **Assistenten**: per
  assistant the table above, a diff of two chosen revisions and an export
  link per revision. It applies the shared rule with the viewer's own
  person (`X-OAAP-User-Id`): another person's private assistant is not
  listed, not even counted; stars and cases show only to whoever manages
  the assistant and the `tenant_admin`.
- **Export** of a revision is an exchange file of `oaap.ai.assistants`
  with `owner: "-"` and no `rev` (the format requires `owner`; whoever
  imports becomes owner).
- Usage counts only reach back as far as the usage rows are kept; the
  page says since when.
- A revision a case names is not compacted (like ratings).

### 3.10 Procedure P: a person through a destination into the backend (0.10, RFC-0066)

A server with access **`propagate`** is reached through a destination with
the authentication `principal_propagation` (`oaap.net.destinations` 2.9,
RFC-0066 stage 1), bound to this gateway with the separate propagation grant.
The destination names the backend user (`sap_user`), issues a short-lived
client certificate for exactly that user from the tenant's CA and presents it
to the pinned target. The gateway only proves on whose behalf it calls.

- **Address:** `destination:<need>[/<path>]` only; a URL is refused. **No
  credential:** saving one with `propagate` is refused.
- **Per call:** the assertion the platform gave **this gateway** for the
  person -- from a chat through the via door (procedure A, §3.9) or on the
  operator's page (§3.7) -- is sent as `X-OAAP-User-Assertion`. The
  destination checks it against the instance the call comes from (RFC-0066
  §3.1); nothing else is sent: no `Authorization`, no cookie. The gateway
  keeps no cookie from an answer (the destination drops them as well).
- **Without an assertion, no call:** a key is refused (`-32003`), never a
  technical fallback (D8). A person signed in at the identity provider is
  refused with a sentence naming RFC-0066 Form B, which the destination does
  not take yet. A view with such a server takes no keys; adding it to a key
  view, or switching such a view to keys, is refused (as X and I).
- **Sessions per person** (RFC-0065 §6, decision P4): the downstream session
  belongs to the person and the profile (§3.9); the session toward the
  backend lives inside it. Another person never uses it -- a request with
  another person's session id is unknown (`404`) and nothing reaches the
  backend. A server without `Mcp-Session-Id` (stateless) works the same.
- **The catalog** is read by a person as themselves (decision P3): on the
  operator's page with the operator's assertion, who needs a backend user of
  their own. There is no technical catalog user; without a person the catalog
  stays as last read, and the sentence says so -- also at the periodic read.
- **The first catalog from `/me`** (0.31.0): while a procedure-P server's
  catalog has never been read, `/me` lists it, and any signed-in person may
  read it once, as themselves, with the assertion the platform gives that
  page -- the backend user, not an operator role, decides. Without an
  assertion nothing goes out; a refusal of the backend leaves it unread with
  the sentence. Once read, only the operator reads again, so a person with
  fewer rights never shortens the list for the others. Read is not approved:
  no view gains an entry; the audit trail records `catalog.first` with the
  person's id.
- **A refusal is the person's:** a `401` or `403` at the end of the
  destination -- the destination (no assertion, no `sap_user`) or the backend
  (no mapping of the certificate) -- is passed on as „Die Destination oder das
  Zielsystem lehnt ab (HTTP n): <sentence>“ (one printable line, at most 200
  characters), measured as `refused`/`destination`, and **does not count for
  the circuit breaker**.
- **Measured as** procedure `P` with `user_sub`, `user_iss`, `client` and
  `assistant` as in procedure A.
- **The light** is the operator's: a demo system with demo data `yellow`,
  customer systems `red` by default (decision P5).

### 3.11 Renaming a server (0.12)

A server may be renamed. Its catalog and its entries in every view follow;
approvals stay (same pinned snapshot and fingerprint); the names of the
entries **in the views** do not change, not even a proposed
`<server>_<name>`, so clients notice nothing. A server created from the
platform's source list (§3.6) keeps its origin (the instance name) and is
matched by it, not by its name, when the list is compared: renaming never
creates a second server, and "gone" and "back" keep working. Usage rows
keep the name they were recorded with. Refused: a name that is taken or
invalid.

### 3.12 Procedure U: the person's own credential (0.14, RFC-0095 stage 2)

Auth kind **`personal`**. The operator sets how the credential is sent
-- `bearer`, `header:<Name>` with an optional prefix (at most 40
characters), or (0.16) `basic` -- and a hint and link for the person (where to create it,
which scopes). The server record carries **no credential**: a
`personal` server has no shared fallback, ever (saving one is refused).
Like X, I and P it is a person kind: never in a view that accepts keys.

- **Entering** (`POST /me/credential`, `/me/credential-delete`, role
  `user`, for oneself only): one line, at most 4096 characters. For a
  `basic` server (0.16) the page asks for user and token separately;
  the user is one line without a colon, at most 256 characters, and
  `user:token` is sealed as one value. The gateway builds the Basic
  value only when sending; a value stored before the server was set to
  `basic` (no colon) is refused with a sentence to enter it anew, and
  nothing goes out. The page shows "stored on …, last used …", never the value, not even in
  part.
- **Keeping:** the vault (§3.4), its **own domain** -- a server
  credential and a personal one are never interchangeable -- one row
  per (issuer, sub, server), the sealed text bound to (issuer, sub): a
  row copied into another person's place does not open. A backup of
  `/data` alone reveals nothing. Renaming a server keeps the rows;
  deleting it deletes them.
- **The call:** the person's credential in the configured form,
  nothing else of the person. Without one: `refused`/`personal`, door
  `gateway`, **before** anything goes out, with a sentence pointing to
  `/me`. A `401`/`403` of the server: `refused`/`credential`, door
  `server`, with its status; it does not open the circuit breaker.
- **The catalog** (0.16.1, L29): read with the credential of the
  person who asks -- the operator on the server page with the user id
  the platform sets (no assertion needed, procedure U forwards none),
  or, while the list was **never** read, any person with a stored
  credential from `/me`. Reading is not approving; once read, only the
  operator reads again, so a credential with fewer scopes never
  shortens the list for the others.
  Procedure letter `U` in the usage row.
- **Catalog:** read with the credential of the operator who presses
  "read catalog" (their own row); without a person, not at all.
- **Operator** (server page): the number of persons and their platform
  ids, stored and last used, **delete** -- never read. Unused for 180
  days (`last_used`, else `stored`): marked; deleting stays a human
  decision.
- **Audit:** `personal.store`, `personal.delete` -- the person as
  `person:<sub>`, never a name (§10), never the value; an operator's
  delete names the operator and the person's id.
- In 0.14 the person is the platform's (`X-OAAP-User-Id`, issuer
  `platform`): a call signed in at the realm finds the credential once
  the platform passes the realm `sub` (RFC-0095 D2).

### 3.9e The setup door (0.25, RFC-0104)

A tenant build may set the gateway up through a door it declares as
`setup: {path: <path>}` (`oaap.apps.runtime` 2.39). Who may call it, the
calls, the results and the "never overwrite what a human made" rule are
those of `oaap.ai.gateway` §7a and RFC-0104 §3.1: the platform's
`OAAP_SETUP_KEY` as bearer, `X-OAAP-Setup-Actor` into the audit as
`setup:<who>`, identity headers ignored, fields named like a secret
refused. Items name servers and chats by their **node key**
(`<tenant>-<name>`): that is the name under which the platform's source
list (§3.8), `X-OAAP-MCP-Client` and the gateway list carry them.

**List (0.28.0, RFC-0109 §4).** `GET ?kind=<kind>` without `id` lists
what the gateway has of that kind, to choose from in a recipe:
servers `{"id", "title", "light"}` for `refresh` and `server_light`;
views `{"id", "title"}`; valid access profiles `{"id", "light":
<ceiling>, "title"}`; assistants that are not deleted `{"id", "title"}`.
Never a key, a digest, a credential or a server's address.

| Kind | Item | Notes |
|---|---|---|
| `refresh` | `{"id": <server>}` | reads the platform's sources now (§3.8), then the server's catalog through the discovery door, without a person (RFC-0073 §16); `present` when the server exists and its catalog has tools; never a conflict, nothing to remove; a later item that needs the server is not carried out while this one is refused |
| `server_light` | `{"id": <server>, "light"}` | a server's light; setup may change it only from the `red` every new server starts with -- another light a human set is a conflict |
| `view` | `{"id", "accesses": [...], "tools": {"server", "effect": "read"}}` or `"tools": [{"server", "tool"}, ...]` | a view (§5) with its tools approved as setup |
| `profile` | `{"id": <label>, "group": "@<chat key>", "views": [...], "ceiling"}` | an access profile (§3.9) |
| `assistant` | `{"id", "title", "view", "gateway": <gateway key>, "model", "greeting", "visibility": "tenant"}` | an assistant (§3.9b), first revision `@1` |
| `server` (0.29.0) | `{"id": <name>, "address": "destination:<binding>[/path]", "auth": "propagate"\|"none", "light"}` | a server behind a destination of the platform (§3.1, procedure P §3.10) -- never a free address, never a credential; another address, auth or light, or a server of a platform source under that name, is a conflict; `GET ?kind=server&id=` is ready once a person has read the catalog (procedure P reads as a person); remove deletes it while unchanged and in no view; listed with the servers |

- `remove` takes back only what setup made and only while it is still as
  made (a digest of what the gateway observed after making it): a view, a
  profile or an assistant a human changed since -- an assistant with a
  new revision included -- stays (`conflict`). A light goes back to
  `red`, a view is deleted, a profile revoked, an assistant set to
  `deleted`. A profile label or an assistant id stays with its entry for
  the audit trail; it is not made a second time.
- **Bringing back (0.27.0, RFC-0109 D12).** When an item names a profile
  that is revoked or an assistant that is deleted, and the gateway's audit
  trail shows that the **setup door itself** removed it (the last
  `key.revoke` of that label, or the assistant's last change, was by
  `setup:…`), the door brings it back as wished: the profile is valid
  again with the wished groups, views, ceiling and effect class
  (`profile.revive` in the audit trail); the assistant gets a new active
  revision, the earlier ones stay (`assistant.revive`). A dry run says
  `would_make`. What a human revoked or deleted stays a `conflict`; a
  **key** never comes back (its value is gone). So undo and run can follow
  each other any number of times.

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

**Assigning in bulk (0.11).** The operator may submit, for one view, the
set of catalog entries it should contain out of those shown to them
(e.g. a tree *server → kind → entry* with checkboxes). Each entry added
goes through the same approval as a single one (name proposed, effect
class chosen beside it, refusals per entry with their reason, the rest
applies); an entry shown and not selected is removed; an entry **not
shown** -- for instance one its server no longer offers -- is left as it
is. Nothing is removed by omission from a list the operator never saw.

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

### 5.4 Copy and rename (0.11)

A view may be **copied** under a new name: settings and entries with
their approvals (pinned snapshot, fingerprint, who, when) go along
unchanged -- the copy is the same approval, not a new one. A
**rename** is a copy that also moves every valid key and access profile
naming the view to the new name and then deletes the old view, audited
with the keys and profiles moved. Before it, the operator is shown who
names the view. Names outside the gateway -- a client's endpoint
`/mcp/<view>`, a chat assistant's view field -- are not changed and are
named as such; the old endpoint then answers like any unknown view
(§12.1). Usage rows keep the name they were recorded with.

### 5.5 Target systems and multi-system views (0.30, RFC-0114)

**Target systems.** The gateway keeps a list of target systems -- where a
tool call reaches through an MCP server: `id`, `title`, `role`
(`development`, `quality`, `production`, `sandbox`, `training`, `other`),
`active`, `kind`, `facts` (non-secret, e.g. `sid`, `client`; a name with a
secret word is refused), `light`, `description`, and its **servers** -- a
server belongs to at most one system. A system's light is the one set,
else the role's (`production` → `yellow`, else `green`), and never looser
than any of its servers. A system a view names cannot be removed. The list
never holds an address, a destination or a credential.

**Multi-system views.** A view becomes a multi-system view by naming a
**reference system**; its entries must then come from that system's
servers (an entry of another server is refused), and none may be named
`systeme`. Further systems are **added** to the view. For each tool entry
and system the gateway decides: *referenz*; *gleich* -- exactly one server
of the system offers the entry's server-side name with the reference's
approved fingerprint; *freigegeben* -- the fingerprint differs and the
operator approved this system's text (held like any approval, per view,
system and entry); *abweichend* -- differs, not approved; *fehlt*;
*mehrdeutig* -- several servers of the system offer it. Only *referenz*,
*gleich* and *freigegeben* are served. A suspended reference entry is
served nowhere. Resources, templates and prompts of a multi-system view
stay those of the reference system (stage 1).

**Protocol.** In a multi-system view `tools/list` shows each tool once,
with a **required** argument `system` added to its schema: an `enum` of
the active systems of the view whose light the key's or profile's ceiling
and the request's `X-OAAP-Light` allow and on which the entry is served,
and a description naming id, title, role and SID/client. A tool with no
such system is not listed. The gateway adds its own tool **`systeme`**:
the view's systems with id, title, role, kind, active, light, whether
usable now, the reference flag, facts, description and the tools served
there -- never an address, a server or a credential. On `tools/call` the
gateway takes `system` out of the arguments and forwards the call with the
held text of THAT system to its server; a missing, unknown or inactive
system, a light too strong for the ceiling, or an entry not served there
is refused (`-32602`) before anything goes out. Opening a multi-system view
uses the light of its most harmless active system; each call checks its
own system. The usage row records the system (column `system`).

**Setup door.** Kind `system`: `{"id", "title", "role", "type", "active",
"facts", "light", "description", "servers"}` (`type` is the system's kind);
the same rules; a human's change is a conflict; remove only while
unchanged and while no view names it.

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
duration, (0.13) **`status`** -- the HTTP status a refusal or a server error
carried, a number, `0` if none -- and **`door`** -- who refused or failed,
one of `gateway`, `platform`, `destination`, `server`, empty for `ok`;
**bytes up** (the client's request body) and **bytes down**
(what the client received), and the **context snapshot** of the key
(`oaap.ai.gateway` §5). For procedure A also the chat, the assistant and
(0.7.2) **`confirmed`**: `yes` when the chat sent `X-OAAP-Confirmed: yes`
— the person confirmed this call in the chat (RFC-0074 §5.6). It is the
chat's statement, recorded for review, never a permission. (0.20) **`assistant_rev`**: the revision of the
assistant when the chat sends `X-OAAP-Assistant: <id>@<rev>`, `0` without.
(0.19) **`light`**:
the light a request asked for with `X-OAAP-Light` (§3.3a), empty without —
a word from a fixed list, no content.

- A read through a **template** records the template, never the URI the
  client filled in: values stand in it.
- A refused call to a resource nobody approved records **no** URI, for
  the same reason; a refused tool or prompt records the name the client
  sent, cut to 200 characters.

| Outcome | Meaning |
|---|---|
| `ok` | the server answered with a result |
| `tool_error` | the server answered with `isError: true` |
| `refused` | the gateway refused (unknown or suspended entry, effect class, argument check; (0.14) `personal`: no stored credential), or the door/server refused the person (`platform`, `destination`, (0.14) `credential`: the server rejected the personal credential) |
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
28. A server with procedure P (§3.10) receives the person's assertion
    addressed to this gateway at the path behind the destination, no
    `Authorization` and never a cookie it set; a key, or no person, is
    refused without a call; a second person never gets the first one's
    session; a `403` of the destination reaches the person with its
    sentence, is measured `refused`/`destination` and does not open the
    circuit breaker.
29. (0.11) Bulk assignment: selected entries are approved with the
    chosen class, shown-and-unselected ones removed, unshown ones kept;
    one refused entry does not stop the others. Copy keeps both views
    with equal fingerprints; rename moves keys and profiles (a profile's
    other views untouched), the same key reaches the new endpoint, the
    old one answers like an unknown view, a taken or invalid name is
    refused and nothing changes.
30. (0.12) A renamed server keeps its entries active and reachable;
    a renamed source server is found by the next comparison of the
    source list, no second server. `/mcp/_views` without the via door is
    the one denial; through it a person sees only views a call would
    open, the administration all of them with reasons.
31. (0.13) `/me` shows a person exactly their own rows -- bait: a
    second person's row in a view named nowhere else never appears, nor
    a key call, nor a row of another issuer; a destination's `403` is
    recorded `status` 403, `door` `destination` and shown as "the
    destination or the target system refused (HTTP 403)" without any
    text of the server; an unknown tool is shown as refused by the
    gateway; without `X-OAAP-User-Id` `403`; `/` stays `admin`.
32. (0.14) Procedure U: the server receives exactly the calling person's
    credential in the configured form -- a second person's call never
    carries it; without one the call is refused before anything goes
    out; a `401` of the server is `refused`/`credential` and does not
    open the breaker; a sealed row moved to another person does not
    open; a shared server credential and a `personal` server in a key
    view are refused; the bait value appears in no file under `/data`,
    no page, row, audit entry or log.
33. (0.15) Readiness: without a credential `needs_credential` with hint
    and `me`; after storing `ready` (no reload of the chat); after a
    `401` of the server `credential_rejected`; a chat without a
    profile and an unknown view get the same `not_for_you` without
    servers; without the via door the one denial. D2: the realm header
    is ignored unless `OAAP_IDENTITY_HEADERS` names it, a foreign
    issuer is ignored; with both, `/me` shows the realm calls and a
    realm-signed call reaches the person's credential.
34. (0.16) Procedure U `basic`: without a user nothing is stored; a
    user with a colon is refused; with both, the catalog read and a
    call carry exactly `Basic base64(user:token)` of that person; the
    token is in no file under `/data` and no log in clear; a refusal of
    the server makes the view `credential_rejected`; an old value
    without a user goes nowhere.
35. (0.16.1) L29: the operator reads a procedure-U catalog with the
    platform's user id alone (no assertion), with their own credential;
    a person with a credential reads the first list from `/me` (audit
    `catalog.first`, nothing approved), never again once read, never
    without a credential, never for another kind of server.
36. (0.17) L11: changing a profile's groups on the operator's page
    (audit `profile.groups`); wrong groups change nothing, not even the
    views. L5: with `OAAP_PORTAL_URL` the sign-in tab links
    `<url>?tab=ueberblick#mcp`, without it the way in words; with
    sign-in off it says the `MCPGW_*` fields stay empty.
37. (0.18) L12: a profile with `*` on a view with only the way
    „Plattform“ is told to name `@<chat-instance>` or `@*`; the page
    explains both kinds and that `*` does not cover a chat. L13: the
    light warning names server, colours and both remedies and does not
    say "senken". L4: the sign-in tab names the `tenant_admin`.
38. (0.26) Client templates (§2.4): each shipped template loads; one with
    an unknown placeholder, a whole-value placeholder inside text, a way
    without its form or a key value is refused with the reason. From a key:
    the key's views with `OAAP_MCP_KEY` in the tool's syntax and no value;
    a view above the key's light is left out with the reason. By hand: the
    sign-in way carries the public client and port 33418 as a number; VS
    Code refuses the sign-in way; a view without the chosen way, a view
    twice, a `platform`-only view and sign-in without a public client give
    no file.
39. (0.26) `/mcp/_client-config`: 200 with the key's views as an
    attachment with `no-store` and an audit row, no usage row; wrong,
    missing or revoked key `401` with `WWW-Authenticate`; unknown tool
    `400`; only unreachable views `409`. `/me/client-config`: the sign-in
    views some profile opens, `400` for a tool without sign-in, `403`
    without the person's id. No output on any path contains an issued
    value or `mcp-oaap-`.
40. (0.31) The first catalog of a procedure-P server from `/me`: listed
    while never read, also for a person without the role `admin`; without
    an assertion refused with nothing sent; a backend refusal leaves it
    unread; read with the person's own assertion (audit `catalog.first`,
    no entry in any view); afterwards no person reads it again and `/me`
    no longer lists it.

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
- Procedure P with the person's IdP token (RFC-0066 Form B, for persons signed in
  at the identity provider); P-saml and Entra; `pattern` and
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

## Deutsche Zusammenfassung (0.9.0, RFC-0073 §16 — Erkunden ohne Person)

Den Katalog einer Quelle der Plattform liest das Gateway jetzt auch ohne
angemeldeten Menschen: über die Erkundungs-Tür der Plattform, die nur den
Verbindungsaufbau und die vier Listen durchlässt. Damit funktionieren das
Lesen gleich nach dem Erkennen einer Quelle und das regelmäßige Nachlesen
(`MCPGW_CATALOG_MINUTES`) wieder, und eine geänderte Beschreibung fällt von
selbst auf. Die App sieht dabei das Gateway als Maschinen-Benutzer und zeigt
ihm dessen Liste; nach dem Lesen steht „Als Gateway gelesen“. Aufrufe laufen
nie über diese Tür, sondern weiter als Person. Ohne Erkundungs-Tür (Plattform
vor 0.1.300) nennt der Satz den Knopf „Katalog lesen“ und `--token-stdin`.

## Deutsche Zusammenfassung (0.10.0, RFC-0066 — Verfahren P)

Das Gateway trägt eine Person aus dem Chat jetzt bis ins Zielsystem, etwa SAP:
Ein Server mit dem Zugang `propagate` liegt hinter einer Destination mit
Principal Propagation. Das Gateway gibt der Destination nur die Zusicherung, die
die Plattform ihm für diese Person ausgestellt hat. Die Destination nennt den
SAP-Benutzer (`sap_user`), stellt für genau ihn ein kurzlebiges Zertifikat aus
und meldet ihn damit am gepinnten Ziel an. Das Gateway hält keinen Schlüssel,
kein Zertifikat und keinen Cookie. Ohne Person gibt es keinen Aufruf, auch keinen
technischen Rückfall. Eine Anmeldung beim Anmeldedienst (Form B) nimmt die
Destination noch nicht an, das sagt ein Satz. Sitzungen bleiben je Person
getrennt (P4). Den Katalog liest eine Person als sie selbst, auf der
Betreiberseite (P3). Lehnt die Destination oder SAP eine Person ab, bekommt sie
den Satz zu sehen, und der Sicherungsautomat zählt das nicht. Neu ist außerdem
`destination:<name>/<pfad>` für den Pfad hinter der Destination.

## Deutsche Zusammenfassung (0.11)

Einträge lassen sich jetzt **gesammelt zuordnen**: Der Betreiber schickt für
eine Sicht die Menge der Einträge, die drin sein sollen, aus denen, die ihm
gezeigt wurden (in der App ein Baum Server → Art → Eintrag mit
Ankreuzfeldern). Jeder neue Eintrag geht durch dieselbe Freigabe wie einzeln;
was gezeigt und nicht angekreuzt war, geht heraus; was nicht gezeigt war,
bleibt. Sichten lassen sich **kopieren** (Freigaben gehen unverändert mit) und
**umbenennen**: Dann werden Schlüssel und Zugangsprofile umgestellt und die
alte Sicht gelöscht. MCP-Clients und Chat-Assistenten stellt das Gateway nicht
um -- die Seite sagt das vorher.

## Deutsche Zusammenfassung (0.12)

Server lassen sich **umbenennen**. Katalog und Einträge ziehen mit, die
Namen in den Sichten bleiben, Clients merken nichts. Ein Server aus der
Quellenliste der Plattform wird weiter über seine Herkunft gefunden. Neu ist
`GET /mcp/_views`, nur über die via-Tür eines Chats: Es nennt die Sichten,
die die Person aus diesem Chat öffnen kann, nach derselben Regel wie beim
Aufruf. Die Verwaltung des Mandanten bekommt alle Sichten, die übrigen mit
Grund. Der Chat baut daraus die Suchhilfe im Feld „Sicht“.

## Deutsche Zusammenfassung (0.13)

Das Gateway hat eine zweite Seite **`/me` für die Person** (RFC-0095 Stufe
1, Rolle `user`): Sie zeigt die eigenen Aufrufe der letzten 30 Tage, also
die, die die Plattform getragen hat (Verfahren A, P, I). Schlüsselaufrufe
erscheinen nie, Aufrufe mit Anmeldung am Anmeldedienst erst, wenn die
Plattform die Kennung aus dem Realm mitgibt. Jeder Fehler steht in Worten
da, mit dem, der abgelehnt hat, und einem Hinweis, was man tun kann. Der
Satz entsteht nur aus Codes. Dafür bekommt jede Messzeile zwei Spalten,
`status` (HTTP-Nummer) und `door` (Gateway, Plattform, Destination,
Server). Freier Text kommt nicht hinzu, §10 bleibt wörtlich wahr. Dasselbe
gibt es als JSON unter `/me/v1/calls`.

## Deutsche Zusammenfassung (0.14)

Neu ist **Verfahren U** (RFC-0095 Stufe 2): Bei einem Server mit Zugang
`personal` bringt jede Person ihren eigenen Zugang mit, etwa ein
persönliches Jira-Token. Der Betreiber stellt nur ein, wie er geschickt wird
(Bearer oder Kopfzeile mit Präfix), und gibt der Person einen Hinweis und
einen Link. Einen gemeinsamen Zugang gibt es nicht, auch nicht als
Rückfall. Die Person trägt ihren Zugang auf `/me` ein. Er liegt
verschlüsselt im Tresor, in einem eigenen Bereich und an die Person
gebunden, und wird nie wieder angezeigt. Er geht nur mit ihren Aufrufen
hinaus. Fehlt er, wird abgelehnt, bevor etwas hinausgeht. Lehnt der Server
ihn ab (401/403), zeigt `/me` „erneuern“, und der Sicherungsautomat bleibt
zu. Der Betreiber sieht je Server, wie viele Personen einen Zugang haben,
und kann einen löschen, aber keinen lesen. Nach 180 Tagen ohne Nutzung
wird ein Zugang markiert.

## Deutsche Zusammenfassung (0.15)

**Bereitschaft** (RFC-0095 Stufe 3): Über die via-Tür fragt ein Chat
`/mcp/_readiness?view=…` und erfährt je Server, ob die Sicht für die Person
eingerichtet ist: bereit, „eigener Zugang fehlt“ (mit Hinweis und Link)
oder „Zugang vom Server abgelehnt“. Dazu die Adresse von `/me`. Kann die
Person die Sicht nicht öffnen, nennt die Antwort keine Server, und eine
unbekannte Sicht sieht genauso aus. **D2:** Nennt die Plattform auf `/me`
die Kennung der Person im Realm (`X-OAAP-User-Idp`, ab 0.1.307) und sagt
sie in `OAAP_IDENTITY_HEADERS` zu, zeigt `/me` auch die Aufrufe mit
eigener Anmeldung (Claude Code). Ein solcher Aufruf findet dann auch den
persönlichen Zugang der Person.

## Deutsche Zusammenfassung (0.16)

Verfahren U kennt jetzt auch **`basic`**: Auf `/me` trägt die Person
Benutzer (etwa ihre E-Mail) und Token getrennt ein, das Gateway bildet
`Authorization: Basic base64(benutzer:token)` erst beim Senden. So
verlangt es der MCP-Server von Atlassian Cloud (Jira, Confluence) für
persönliche API-Token. Ein alter Wert ohne Benutzer geht nicht hinaus,
die Person wird gebeten, ihn neu einzutragen.

## Deutsche Zusammenfassung (0.16.1)

**L29:** Den Katalog eines Servers mit Verfahren U liest die Verwaltung
jetzt ohne Zusicherung der Plattform -- Verfahren U schickt nur den
eigenen Zugang, die Kennung der Person genügt. Und eine Person mit
hinterlegtem Zugang darf auf `/me` die **erste** Werkzeugliste lesen
(„Werkzeugliste für die Verwaltung lesen“), solange sie noch nie gelesen
wurde. Freigeben bleibt Sache der Verwaltung; danach liest nur noch die
Verwaltung neu, damit ein Zugang mit weniger Rechten die Liste der
anderen nie verkürzt.

## Deutsche Zusammenfassung (0.17)

**L11:** Die Gruppen eines Zugangsprofils lassen sich auf der
Betreiberseite ändern, zusammen mit Sichten und Grenzen. Falsche Gruppen
werden vorher abgewiesen, dann ändert sich gar nichts. **L1/L5:** Der
Reiter „Anmeldung“ verlinkt die Seite der Instanz im Portal (Karte MCP,
Knopf „Anmeldung einrichten“) und sagt, dass die Felder `MCPGW_*` dafür
leer bleiben. Die Adresse kommt von der Plattform (`OAAP_PORTAL_URL`, ab
0.1.308), sonst nennt das Gateway den Weg in Worten.

## Deutsche Zusammenfassung (0.18)

**L12:** Die Seite „Zugänge“ erklärt die zwei Arten von Gruppen: `*` und
`/pfad` sind Menschen, die sich **am Gateway** anmelden (Sicht braucht
„Anmeldung“); `@<chat>` und `@*` sind Menschen, die ein Chat herträgt (Sicht
braucht „Plattform“). Ein `*` gilt für einen Chat nicht. Passt ein Profil
nicht zur Sicht, sagt die Warnung, welche Gruppe gemeint ist, statt den
falschen Zugang zum Einschalten vorzuschlagen. **L13:** Die Ampel-Warnung
nennt die Farben auf Deutsch, den Server, der die Ampel der Sicht bestimmt,
und beide Wege (Profil höher stellen oder Server niedriger einstufen, wenn er
harmloser ist). **L4:** Der Reiter „Anmeldung“ sagt, dass ab Plattform
0.1.309 auch der `tenant_admin` die Anmeldung einrichtet.

## Deutsche Zusammenfassung (0.19, RFC-0101 Stufe 1)

Eine Anfrage darf `X-OAAP-Light: green|yellow|red` mitschicken, die Ampel,
die die Person im Chat für ihr Gespräch gewählt hat. Sie verschärft die
Decke von Schlüssel oder Profil für diese Anfrage und lockert sie nie. Ist
die Sicht röter (ihr schlechtester Server), kommt 403 mit einem Satz, der
beide Farben und den Server nennt. Geprüft wird bei jeder Anfrage, auch
innerhalb einer Sitzung. Ein unbekannter Wert wird mit 400 abgelehnt. Die
Messzeile hält die verlangte Farbe in der Spalte `light` fest (§10 bleibt
wahr).

## Deutsche Zusammenfassung (0.23, RFC-0097 Stufe 2 / RFC-0101 Stufe 4)

Je Assistent und Revision gibt es jetzt eine Auswertung (§3.9d):
- **Aus den Messzeilen:** Aufrufe, Ablehnungen, Fehler und Personen (nur
  gezählt).
- **Aus dem Chat:** Sterne und Vorgänge „Nicht zufrieden“.
- **Vergleich:** zwei Revisionen nebeneinander als Unterschied.
- **Export:** eine gewählte Revision als Austauschdatei.

Lesen dürfen dieselben wie bei den Sternen. Die Betreiberseite hat einen
Reiter „Assistenten“; ein fremder privater Assistent fehlt dort ganz. Ein
Vorgang wird nur gezählt: Die Nummer und die Person stehen im Gateway
nicht, nur HMACs.

## Deutsche Zusammenfassung (0.22, RFC-0101 Stufe 3)

Ein Assistent darf `support_queue` tragen (`oaap.ai.assistants` 0.6). Das
Gateway prüft das Feld mit derselben Regel wie der Chat und hält es mit
der Revision fest. Mehr ändert sich hier nicht: „Nicht zufrieden“ geht
nicht durch das Gateway, sondern als Vorgang über die Feedback-Route.

## Deutsche Zusammenfassung (0.21, RFC-0101 Stufe 2)

Sterne liegen jetzt im Gateway, neben den Revisionen der Assistenten
(§3.9c). Ein Chat schickt sie über die via-Tür als die Person: 0 bis 5
Sterne je Antwort oder Gespräch, mit den Umständen (Revision, Modell,
Ampel, Sicht, je Werkzeug Name, Wirkung, Ausgang, Dauer). Die Person steht
nur als HMAC mit einem Schlüssel des Gateways darin. Dieselbe Person an
derselben Stelle ersetzt ihre Bewertung, `null` zieht sie zurück. Text
gibt es nur mit Haken und nach 180 Tagen nicht mehr. Lesen dürfen, wer den
Assistenten pflegt, und der tenant_admin. Jede Person sieht ihre eigenen.
Eine Revision, die eine Bewertung nennt, wird nicht verdichtet.

## Deutsche Zusammenfassung (0.20, RFC-0097 Stufe 1)

Die Assistenten der Chats liegen jetzt im Gateway, mit Revisionen. Ein Chat
liest und schreibt sie über die via-Tür als die Person unter
`/mcp/_assistants`. Sichtbarkeit: privat der Besitzer, Team über das eigene
Rechteobjekt `assistant` des Gateways, Mandant alle (pflegen nur
tenant_admin). Ein fremder privater Assistent ist auch gezielt nicht zu
finden (404 wie unbekannt). Jedes Speichern ist eine neue Revision mit
Eintrag in der Prüfspur. Die Nummer vergibt das Gateway, die Sicht muss es
hier geben. Übernahme der alten Datei eines Chats nur durch tenant_admin,
mit den bisherigen Besitzern. Die Messzeile trägt die Revision in der
Spalte `assistant_rev`.

## Deutsche Zusammenfassung (0.25, RFC-0104 — Einrichtungstür)

Neuer Abschnitt §3.9e: Beim Aufbau eines Mandanten aus einem Profil richtet
die Plattform das MCP-Gateway über eine Einrichtungstür ein. Zugang wie beim
KI-Gateway: nur mit dem Schlüssel, den die Plattform hält. Arten:

- **`refresh`:** Quellen jetzt einlesen und den Katalog eines Servers ohne
  Person lesen.
- **`server_light`:** die Ampel eines Servers. Ändern darf die Einrichtung
  sie nur vom Startwert „rot“ aus.
- **`view`:** eine Sicht mit freigegebenen Werkzeugen.
- **`profile`:** ein Zugangsprofil für einen Chat (`@<chat>`).
- **`assistant`:** ein Assistent in Revision @1.

Server und Chats heißen in den Einträgen mit ihrem **Knotenschlüssel**
(`<kürzel>-<name>`), denn unter diesem Namen kennt das Gateway sie. Genau
das hatte der erste Aufbau von kit1 falsch: Das Profil nannte die Instanzen
mit vorangestelltem Kürzel, die Plattform setzte es noch einmal davor.
Rückgebaut wird nur, was die Einrichtung angelegt hat und was seitdem
unverändert ist.

## Deutsche Zusammenfassung (0.26, RFC-0107 — Vorlagen für Werkzeuge)

Das Gateway schreibt die Datei, mit der ein Werkzeug seine Sichten benutzt:
Claude Code, VS Code (Copilots eigenes Format, vorerst nur mit Schlüssel)
und opencode. Die Vorlagen sind Daten in der App, jede mit dem Datum, an dem
ihr Format geprüft wurde.

- **Reiter „Vorlagen“:** Werkzeug wählen, dann die Sichten aus einem
  Schlüssel oder von Hand, je Sicht der Zugang Schlüssel oder Anmeldung.
  Ergebnis zum Kopieren und Herunterladen.
- **Nie der Schlüsselwert:** In der Datei steht die Umgebungsvariable
  `OAAP_MCP_KEY`. Den Wert zeigt nur der Kasten direkt nach dem Ausstellen,
  einmal.
- **Selbstbedienung:** `GET /mcp/_client-config?target=` mit dem eigenen
  Schlüssel liefert die Datei für dessen Sichten. Auf `/me` bekommt eine
  Person die Datei für die Anmelde-Sichten, die ein Zugangsprofil öffnet.
  Ihre Gruppen im Realm kennt das Gateway dort nicht; bei Profilen für
  bestimmte Gruppen entscheidet die Anmeldung.

## Deutsche Zusammenfassung (0.27.0 — die Einrichtungstür holt zurück, was sie selbst entfernt hat)

Bisher war ein Rückgängig der Einrichtung endgültig: Ein widerrufenes
Zugangsprofil und ein gelöschter Assistent blieben unter ihrer Kennung
stehen, und ein neuer Lauf traf auf einen Konflikt (RFC-0109, Befund B).
Jetzt holt die Tür beides zurück, **wenn sie es selbst entfernt hat**. Der
Beweis ist die Prüfspur des Gateways: Der letzte Widerruf beziehungsweise
das Löschen kam von „setup:…“.

- Das Profil gilt wieder, so wie gewünscht.
- Der Assistent bekommt eine neue Revision; die früheren bleiben.

Was ein Mensch widerrufen oder gelöscht hat, bleibt ein Konflikt. Ein
Schlüssel kommt nie zurück. Rückgängig und Lauf gehen damit beliebig oft
hintereinander.

## Deutsche Zusammenfassung (0.28.0 — die Einrichtungstür nennt ihre Einträge)

`GET ?kind=…` ohne id nennt Server (mit Ampel), Sichten, gültige
Zugangsprofile (mit Obergrenze) und nicht gelöschte Assistenten -- nie
einen Schlüssel, Digest, Zugang oder eine Server-Adresse. Ein Rezept
wählt daraus (RFC-0109).

## Deutsche Zusammenfassung (0.29.0 — ein Server hinter einer Destination)

Die Einrichtungstür kennt die Art **`server`**: ein Server hinter einer
Destination der Plattform (`destination:<bindung>[/pfad]`, Verfahren P
oder ohne Zugang, Ampel) – nie eine freie Adresse, nie ein Zugang. Was ein
Mensch daran geändert hat, ist ein Konflikt; entfernt wird nur, was
unverändert ist. „Bereit“ ist der Server, sobald eine Person den Katalog
gelesen hat. Damit legt das Rezept „SAP SSO einrichten“ den Server an.

## Deutsche Zusammenfassung (0.30.0 — Systemlandschaft und Multi-System-Sichten)

Das Gateway führt eine **Systemlandschaft**: Zielsysteme mit Titel, Rolle
(Entwicklung, Qualität, Produktion …), aktiv, Art, Angaben wie SID und
Mandant (nie geheim), ihren Servern und einer Ampel (aus der Rolle,
Produktion gelb, nie lockerer als ein Server). Eine **Multi-System-Sicht**
wird am Referenzsystem ausgeprägt; weitere Systeme werden zugeordnet, und
je Werkzeug zeigt das Gateway *gleich*, *abweichend* (eigene Freigabe
nötig) oder *fehlt*. Im Chat steht jedes Werkzeug **einmal**, mit dem
Pflichtargument `system` (nur aktive, erlaubte Systeme); das Gateway
leitet an den Server dieses Systems weiter. Das Werkzeug `systeme` nennt
die Systeme der Sicht, nie Adresse oder Zugang. Die Messzeile nennt das
System.

## Deutsche Zusammenfassung (0.31.0 — erste Werkzeugliste eines P-Servers von /me)

Wer im Zielsystem (etwa SAP) einen eigenen Benutzer hat, aber im Gateway keine
Verwaltungsrolle, liest die **erste** Werkzeugliste eines Servers mit
Verfahren P jetzt selbst: im Portal unter „Meine Werkzeuge“, als sie selbst.
Nur solange die Liste noch nie gelesen wurde; danach liest nur die
Verwaltung neu. Gelesen ist nicht freigegeben. Die Prüfspur nennt die Person.
