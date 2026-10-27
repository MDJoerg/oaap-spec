# RFC-0065: The MCP Gateway — Tools Behind One Keyed Endpoint, Bundled Into Views, With the User Carried Through to the Backend

- **Status:** **Accepted (2026-10-27)** — Jörg took D7–D13 as
  recommended, except D12, which becomes *measure first, then choose*
  (§12). Q1–Q4 answered the same day (§13): server-to-client requests
  configurable; the propagation of procedure P moves into the platform
  (**RFC-0066**), so that CAP apps and others use the same mechanism;
  the SAP user name comes from **one IdP attribute** used by n systems;
  a4h already runs several ABAP MCP servers. Nothing built.
- **Date:** 2026-10-27
- **Authors:** Claude (analysis & proposal), Jörg (requirement, decides)
- **Depends on:** `oaap.ai.gateway` 0.4 and RFC-0064 (the pattern this
  copies: keys, context, volume, report, vault), RFC-0041 (Keycloak as
  an app, the tenant as the place of sign-in), RFC-0042 (the tenant as
  a place), RFC-0027 (API keys for machine principals), RFC-0033
  (destinations and connector — the place where principal propagation
  was left open), RFC-0019 (token hygiene), RFC-0002 (default deny),
  RFC-0010 (public route brake)
- **Changes:** new capability `oaap.ai.mcp-gateway` 0.1; new app
  `mcp-gateway`; the parts of `ai-gateway` that both apps need (keys,
  context, vault, metering and report) move into one shared module

## Summary

The AI gateway puts models behind one keyed endpoint: a consumer asks
for a *purpose*, gets a key, and every call is metered with a copy of
the key's context. Jörg wants the same for **MCP servers** — the tool
servers that AI clients such as Claude Code, Copilot or a company's own
agent call directly — and three things more:

1. **Views and bundles.** Route only selected tools, and combine the
   tools of several servers into one endpoint that looks like a single
   server to the client.
2. **Protect the backends.** A backend MCP server — often an ABAP
   system — must not be flooded by an agent in a loop.
3. **Carry the user through.** When the backend is SAP, the person at
   the client must arrive there as **their own SAP user**, with their
   own authorizations, change documents and transport requests — not
   as a shared technical user. With Keycloak today, and Microsoft Entra
   soon.

This RFC proposes one app with one rule set. The decisive finding is
in §6: **neither Keycloak nor Entra can reliably hand over a SAP-ready
credential**, so the gateway itself becomes the issuer SAP trusts —
the same way the SAP Cloud Connector does it — and the identity
provider only answers *who is this*.

## 1. The requirement (Jörg, 2026-10-27)

- Like the AI gateway: the gateway knows the real MCP servers, **with
  different credential procedures** toward them. Toward the user it
  issues **API keys**, routes through, **meters** and makes volume
  available for **billing**.
- **Views:** route only selected tools.
- **Bundles:** unite the tools of several servers in one MCP endpoint.
  (Jörg: *bundles* — static composition, not an AI behind a tool.)
- **Backend protection** against too many requests.
- **SSO through to the backend.** Concrete case: an SAP ABAP backend;
  a SAP user must arrive via the MCP path. IdP: Keycloak, perspectively
  Entra.

Answers of 2026-10-27 that shape this RFC:

| Question | Jörg |
|---|---|
| Which backend MCP servers? | various; mostly **an MCP server inside the ABAP backend**, or an HTTP MCP server |
| Test system | **a4h** (ABAP Platform Trial), not yet set up |
| A signed-in user pays via an *access profile* with the same context as a key | **yes** |
| Where does the SAP user name come from? | **configurable; support all procedures** |
| "Agents on the MCP side" | **bundles** |
| Own app or one gateway with two faces? | **own app** |
| Tools only, or resources and prompts? | **all** |
| stdio servers | **no stdio support** |
| Entra | not yet, **very likely later** |

The ARC-1 training scenario (webtop) is explicitly **not** the use case.

## 2. The shape: same as the AI gateway

The MCP gateway is an ordinary OAAP app with a `public` route; the
platform authenticates nothing, strips client-sent identity headers and
brakes per client (RFC-0010). The app authorizes every request itself.

| AI gateway | MCP gateway |
|---|---|
| supplier = OpenAI endpoint + credential + light | **server** = MCP endpoint (Streamable HTTP) + **access procedure** + light + **protection limits** |
| alias = purpose → models | **view** = a named MCP endpoint → selected tools, resources and prompts of one or more servers |
| key: context, budget, rate, aliases | key: same context, budget, rate, restricted to **views** |
| usage row per completion | usage row per **`tools/call`, `resources/read`, `prompts/get`** |
| no prompt content in any log | **no tool arguments and no tool results in any log** |

Downstream, every view is one endpoint: `POST|GET|DELETE /mcp/<view>`
(Streamable HTTP). A client configured with that URL sees one MCP
server. Which servers stand behind it, and where, it never learns.

Taken over unchanged from `oaap.ai.gateway`: keys shown once and stored
hashed; the four context dimensions plus free labels; budget and rate
as hard limits; the identical 403; credentials write-only and encrypted
under a key outside the gateway's storage; *volume, never money*; the
snapshot rule; `/report/v1/usage` and the charts on **one query**;
`complete_until`. These are not re-specified here; they move into a
module both apps use, so that there is one vault and one query, not two
that disagree one day.

### 2.1 Protocol scope

- **Transport:** Streamable HTTP downstream and upstream. **No stdio**
  (D2). A server that only speaks stdio is not a supplier; whoever wants
  it wraps it as their own HTTP app.
- **Primitives:** **tools, resources (including templates and
  subscriptions) and prompts** (D3).
- **Notifications** pass through, filtered by the view:
  `notifications/tools/list_changed` and its siblings reach the client
  only if the change touches something the view exposes (and see §4.2 —
  a change does not expose anything by itself). Progress and
  cancellation pass through.
- **Server-to-client requests** (elicitation, sampling, roots) are
  **configurable per view** (Jörg, Q1), each one separately: `pass` or
  `refuse`. Default: elicitation and roots `pass`, sampling `refuse` —
  sampling lets a backend spend the client's model and send it data,
  the light question in reverse, so it is a deliberate switch.

### 2.2 Sessions

A downstream session holds **one upstream session per server** the view
touches, opened lazily on first use. Upstream sessions are never shared
between downstream sessions when the server's access procedure carries
the user (§5), because the identity differs per user. `initialize`
answers with the merged capabilities of the view, never with an
upstream's server name or version.

## 3. Views and bundles

A view is the operator's composition. It has three levels of power,
built in this order:

1. **Selection** — expose named tools, resources and prompts of one
   server; everything else stays invisible.
2. **Bundle** — expose items of several servers in one view. Every
   exposed tool carries a **name of the view** (default
   `<server>_<tool>`, operator may rename) and optionally a replaced
   description. Names are unique within a view; a collision is a
   configuration error, refused when saving, never resolved silently.
   Resources keep their URI; two servers offering the same URI in one
   view is a configuration error. Prompts are renamed like tools.
3. **Fixed arguments and bounds** — the view may pin an argument
   (`package = "ZDEMO"`) or restrict it to a list or a pattern. A pinned
   argument disappears from the schema the client sees; a call violating
   a bound is refused by the gateway before it reaches the server.

A view is **static**: it contains no model and makes no decisions. An
"agent tool" — one tool behind which an AI works — is a possible later
stage and not part of this RFC (§10).

## 4. The catalog: default deny, pinned, classified

### 4.1 Nothing appears on its own

The gateway reads each server's `tools/list`, `resources/list`,
`resources/templates/list` and `prompts/list` into a **catalog**. An
item a server offers is **not** exposed until the operator puts it into
a view. A server that adds a tool tomorrow adds nothing to any view.

### 4.2 Pinned descriptions

For every exposed item the gateway stores a **fingerprint** of its name,
description and schema at the moment the operator approved it. When a
server later reports a different fingerprint, the item is **suspended**
in every view until the operator confirms the change, and the operator
page shows old and new side by side.

Why this is a rule and not a convenience: a tool description is text
that goes straight into the model's context. A server that changes its
description after approval can instruct the model — that is the known
"rug pull" form of prompt injection, and the gateway is the one place
that sees every server's text before any client does.

### 4.3 Effect classes

The operator assigns every tool an **effect class**: `read`, `write`,
`execute` (irreversible or with side effects outside the system, such
as releasing a transport or sending mail). A view and a key each carry
the **highest class they may use**; default `read`.

MCP servers may annotate their own tools as read-only or destructive.
Those annotations are **shown to the operator as a hint and never
enforced** — the same principle as the light in `oaap.ai.gateway` §7:
we enforce what was declared by whoever is responsible, not what a
server says about itself.

## 5. Two identities: who pays, and who acts

The AI gateway has one identity: the key. The MCP gateway has two,
because they answer different questions:

- **Who pays, and for what?** — the **key** with its context, or, for a
  signed-in user, the **access profile** (§5.2).
- **Who acts in the backend?** — the **user**, where the backend needs
  one.

### 5.1 Two ways in

| Way in | Credential at the gateway | Typical client |
|---|---|---|
| **Key** | a gateway API key in the `Authorization` header | an agent, a pipeline, a server-side integration — no person |
| **Sign-in** | an OAuth access token from the tenant's identity provider | Claude Code, VS Code, any MCP client a person uses |

The sign-in follows the MCP authorization specification: the gateway is
an OAuth **protected resource**. It publishes its resource metadata
(RFC 9728), naming the tenant's identity provider as authorization
server. The client opens the browser, the person signs in at Keycloak
(the tenant's `auth`, RFC-0041) or at Entra, and the client presents
the resulting token. The gateway accepts a token **only if it is
addressed to this gateway** (audience, RFC 8707) — a token meant for
something else is refused even if it is valid.

A view declares which ways in it accepts: `key`, `signin`, or both. A
view whose servers carry the user (§6) accepts `signin` only — a key
has no person behind it.

### 5.2 The access profile (Jörg, Q3: yes)

A signed-in user is billed through an **access profile**: the same
context as a key (account, project, cost centre, application, labels,
responsible person), the same budget and rate, the same view
restriction — but bound to a **group or the tenant** instead of being a
secret string. The usage row records the profile's context *and* the
user's stable ID (RFC-0040 UUID), never the user's name or e-mail.

Which profile applies is decided by group membership in the identity
provider; a user matching none is refused with 403 — sign-in proves
who someone is, not that they may consume.

## 6. Toward the server: access procedures

Every server has exactly one **access procedure**. The operator
chooses it; the client cannot.

| Procedure | What the backend sees | For |
|---|---|---|
| **T — technical** | always the gateway's own principal: Basic, Bearer, a named header, or OAuth client credentials | catalogs, documentation servers, anything without per-user authorization |
| **X — token exchange** | the real user, with a token issued by the IdP **for this backend only** (RFC 8693; at Entra: *On-Behalf-Of*) | HTTP MCP servers that are OAuth resource servers of the same IdP |
| **P — propagation** | the real user, as a credential **the gateway issues** and the backend trusts | **SAP ABAP**, and any backend that trusts certificates or assertions but not our IdP |

**Never:** storing a user's own backend password in the gateway. That
would make the gateway a password vault for every user, which is the
opposite of single sign-on.

**Never:** passing the client's token on to the server. The MCP
specification forbids it, and for good reason: a token addressed to the
gateway would then work at every backend.

**No fallback.** A server with procedure X or P is **never** called
with the technical credential when the user cannot be carried through —
the call is refused and says why. A silent fallback would let a person
act with rights they do not have, and nobody would see it in SAP.

### 6.1 Why P exists: the IdP cannot speak SAP

SAP ABAP accepts a user, without a password, through:

1. an **X.509 client certificate** in the TLS handshake, mapped to a SAP
   user by a rule (transaction `CERTRULE`), the issuer trusted in
   `STRUST` — this is how the SAP Cloud Connector does principal
   propagation;
2. an **OAuth token from the SAP system's own OAuth server**, obtained
   with a **SAML bearer assertion** (grant type `saml2-bearer`);
3. Kerberos/SPNEGO (constrained delegation) — Windows domains only.

What the identity providers can deliver (checked 2026-10-27):

- **Keycloak** standard token exchange (v2, default since 26.2) issues
  **OAuth/OIDC tokens only**; exchanging for a SAML assertion is
  documented as **not supported**.
- **Entra** On-Behalf-Of requesting a SAML assertion is only documented
  on the **old v1 endpoint**, and practitioners report malformed
  assertions; Microsoft's own SAP guidance converts tokens in **Azure
  API Management**, i.e. outside Entra.

So neither IdP is a reliable source of a SAP-ready credential. The
conclusion is the design:

> **The IdP authenticates the person. The gateway issues the SAP
> credential.** SAP trusts the gateway's issuer, exactly as it would
> trust a Cloud Connector — and the path is the same whether the person
> signed in at Keycloak or at Entra.

**Placement (Jörg, Q2):** this is the same exchange the SAP Cloud
Connector performs, and the platform needs it beyond MCP — a CAP app on
OAAP calling ABAP OData *as the user* needs exactly the same. So the
issuer is **not** part of the MCP gateway. It is a platform function,
specified in **RFC-0066**: a destination with the authentication
`principal_propagation`. For the MCP gateway, procedure P simply means
*this server is reached through such a destination*; §6.2–§7 describe
what happens there and are normative in RFC-0066.

### 6.2 P in detail

For a call through a server with procedure P:

1. The gateway checks the user's token (§5.1) and determines the
   **backend user name** (§7).
2. It issues a **short-lived credential** for exactly that name:
   - **P-cert** (default): an X.509 client certificate, `CN=<SAP user>`,
     lifetime minutes, signed by an **issuing CA of this gateway and
     tenant**, used for the TLS connection to the backend;
   - **P-saml**: a SAML 2.0 assertion signed by the same issuer,
     exchanged at the SAP OAuth server (`saml2-bearer`) for a SAP access
     token, for systems where SAP OAuth is set up and certificates are
     not wanted.
3. The SAP system maps the credential to the user and runs the MCP
   request **as that user**. `SY-UNAME` is the person.

The issuing key never leaves the gateway, is stored like a supplier
credential (encrypted, write-only), and exists **once per tenant** — a
SAP system trusting tenant A's issuer can never be reached with tenant
B's users. The CA certificate (public part) is downloadable from the
operator page, because the SAP basis team must import it into `STRUST`.

Every issued credential is audited (time, server, backend user name,
serial), never the request itself.

### 6.3 The network path matters for P-cert

A client certificate only reaches SAP if **the TLS connection ends at
SAP** — at the ICM (with `VCLIENT` on the HTTPS port) or at a SAP Web
Dispatcher that forwards the certificate in a header the ICM is
configured to trust. Through a RFC-0033 destination this means `kind:
tcp` (the tunnel carries TLS unopened), not `kind: http` (the proxy
would terminate it). P-saml has no such constraint.

### 6.4 The MCP server inside ABAP is the simple case

Jörg's main case is an MCP server **implemented in the ABAP system
itself**, as an ICF service. Then the gateway's HTTP request *is* the
SAP logon: the user arrives at the ICM, the ICF handler runs as that
user, every tool the handler offers runs with that user's
authorizations. Nothing in between has to forward an identity.

An HTTP MCP server **outside** SAP that in turn calls SAP is the hard
case: the gateway can only hand the identity to that server (procedure
X, or a P-credential in a header the server agrees to use) — whether it
reaches SAP is the server's work, and this RFC says so instead of
promising it.

## 7. Who is the backend user: mapping (Jörg: configurable, all procedures)

**The normal case (Jörg, Q4):** one IdP attribute `sap_user`, used by
all n connected SAP systems. Maintaining names per system in the
gateway would be too much work and would need several people and roles
to act; the attribute is maintained once, where the person is
maintained. The rule list below stays configurable for the exceptions.
With procedure P the rules live on the destination (RFC-0066), not in
the gateway.

Per server with procedure X or P, the operator configures an **ordered
list of rules**; the first one that yields a name wins:

| Rule | Source | Example |
|---|---|---|
| **claim** | a named claim in the user's token | Keycloak user attribute `sap_user_a4h` mapped into the token; Entra extension attribute or `onPremisesSamAccountName` |
| **table** | a mapping table: user (RFC-0040 UUID) → backend name, per server — the exception, not the rule | maintained on the operator page, or imported as CSV |
| **derive** | a transformation of a standard claim | local part of `email`, upper case, truncated to 12 characters |

- No rule yields a name → **refused**, with the reason in the answer
  ("no SAP user known for you at system a4h"), never the technical user.
- The resulting name is checked against the backend's rules for user
  names (for SAP: 12 characters, upper case) before any credential is
  issued.
- With P-cert, the mapping may alternatively happen **in SAP**: the
  certificate then carries the IdP's stable ID or e-mail, and `CERTRULE`
  maps it. That is a fourth rule, **sap**, for systems whose basis team
  wants to keep the mapping themselves — the gateway then cannot check
  the name and says so on the operator page.
- Every change to the table or the rules is audited with old and new
  value.

## 8. Protecting the backends

Per server, enforced by the gateway, in this order:

1. **Concurrency:** at most *N* calls in flight; further calls wait in a
   short queue (bounded length and wait time).
2. **Rate:** per server, **per server and user**, and per key/profile.
3. **Timeout** per call.
4. **Breaker:** after *K* failures in a row the server is taken out for
   a cool-down; one probe call decides whether it comes back.

Answers: rate exceeded → `429` with `Retry-After`; queue full or breaker
open → `503` naming the server's label in the view, never its address;
budget exhausted → `429` without `Retry-After`. In MCP terms these are
transport errors before the session or JSON-RPC errors on an open
session; a tool that runs and fails is the server's `isError` result
and passes through unchanged.

The point is SAP dialog work processes: an agent that issues 200
`read_class` calls in a loop is realistic, and a SAP system that runs
out of dialog processes stops for its users too, not only for the
agent.

## 9. Volume, light, and what is never recorded

### 9.1 Usage row

One row per `tools/call`, `resources/read` and `prompts/get`: time,
key or profile (+ user UUID for sign-in), view, **item name in the view
and in the server**, server, access procedure, outcome (`ok`,
`tool_error`, `refused`, `limited`, `upstream_error`), latency, **bytes
up and down** at the client side, and the **context snapshot**.
`initialize`, `*/list`, pings and notifications are counted separately
as protocol traffic, not as consumption.

The report interface takes the dimensions of `oaap.ai.gateway` §5.1
plus `view`, `tool`, `server`, `user`. Because `tool` is a dimension,
an external billing system can price *per tool* — the gateway still
never knows a price.

### 9.2 Never recorded

**No tool argument, no tool result, no resource content and no prompt
text** in any log, any usage row, any audit entry — in any operating
mode. The SAP case makes this concrete: tool results are business data.

### 9.3 The light

Every server carries a light (`oaap.ai.gateway` §7), and the chain rule
holds: a view is never greener than its worst server. New for MCP is
the **other direction**: tool results flow into the model of the
*client*, which the gateway does not see. The gateway can therefore
only enforce the light of what it sends to servers (arguments); it
**documents** — and shows per view — that results leave toward the
client's model. A view may carry a note naming which models it is
approved for; enforcing that is out of reach and the RFC says so.

## 10. Not part of this RFC

- **Agent tools** (a tool behind which an AI loop runs via the AI
  gateway) — Jörg chose bundles; a later RFC if needed.
- **stdio** servers (D2).
- **Kerberos/SPNEGO** toward SAP.
- **Prices** — volume only, as in RFC-0064.
- **Rewriting tool results** (filtering fields out of answers) — the
  gateway does not read results (§9.2).

## 11. Stages

| Stage | Content | Measured on |
|---|---|---|
| **0** | shared module extracted from `ai-gateway` (keys, context, vault, metering, report), `ai-gateway` unchanged in behaviour | `ai-gateway` tests green, oaap-test unchanged |
| **1** | `mcp-gateway` app: one server, procedure T, keys, view as **selection**, catalog default deny, pinning, usage, report, protection limits | oaap-test against a reference HTTP MCP server |
| **2** | **bundles** across servers, renaming, fixed arguments and bounds, effect classes; resources and prompts | oaap-test, two servers in one view, collision refused |
| **3** | **sign-in** at the tenant's Keycloak (resource metadata, audience check, access profile); procedure **X** | oaap-test with `auth`; a client (Claude Code) signs in through the browser |
| **4** | procedure **P-cert** + mapping rules + issuer per tenant | **a4h**: a minimal ABAP MCP handler whose tool `whoami` returns `SY-UNAME` — the measurement is that two different people get two different answers |
| **5** | **P-saml**; Entra as IdP | a4h with SAP OAuth; an Entra test tenant |

Stage 4 needs on a4h (one-time, basis work — Jörg or with Jörg):
HTTPS port with client certificate request, gateway CA in `STRUST`,
a `CERTRULE` rule, an ICF node for the MCP handler, two test users.

## 12. Decisions

Already decided by Jörg (2026-10-27): D1 own app; D2 no stdio; D3 all
primitives; D4 bundles, no agent tools; D5 access profile for signed-in
users; D6 mapping configurable with all rule kinds.

To decide:

| # | Proposal | Recommendation |
|---|---|---|
| **D7** | The IdP authenticates, **the gateway issues the backend credential** (procedure P), one issuer per tenant | yes — it is the only path that works the same with Keycloak and Entra |
| **D8** | **No fallback** from X/P to the technical credential | yes |
| **D9** | Catalog **default deny** and **pinned descriptions** | yes |
| **D10** | Effect classes set by the operator; server annotations only shown | yes, default `read` |
| **D11** | Never record arguments, results, resource contents, prompt text | yes, as conformance requirement |
| **D12** | P-cert as default, P-saml second | yes — P-cert covers every ICF service; P-saml needs SAP OAuth configured per service |
| **D13** | Spec ID `oaap.ai.mcp-gateway`, app `mcp-gateway` | yes |

**Decided (Jörg, 2026-10-27, by form):** D7, D8, D9, D10, D11, D13 as
recommended; D7 is carried out by RFC-0066 D1/D2 (the platform issues,
in the destination). **D12 changed:** *measure first, then choose* —
a4h runs on the internet, and whether a client certificate reaches the
ICM there or TLS ends earlier (load balancer, Web Dispatcher) decides
whether x509 or SAML bearer comes first; the other follows as the next
stage (RFC-0066 §8 phase A0).

## 13. Questions to Jörg

Answers of 2026-10-27:

- **Q1:** configurable → §2.1.
- **Q2:** we build a **Keycloak–SAP SSO scenario together**, Claude
  guiding Jörg; a4h becomes the demo landscape. The exchange belongs
  into the platform, not into this app → **RFC-0066**.
- **Q3:** a4h **already runs several MCP server implementations** in
  ABAP; one offers tools about users and authorizations. No server of
  our own is needed for stage 4. That one is also the natural first
  measurement: under propagation, each person sees *their own* user
  and roles. Its tools get effect classes like any other (§4.3) —
  reading authorization data is still `read`, but a tool that changes
  a user is `execute`.
- **Q4:** configurable; the practical case is **one attribute
  `sap_user` for n systems**; the trust is set up per SAP system and per
  tenant → §7, RFC-0066.

The original questions:

- **Q1 — server-to-client requests.** MCP lets a server ask the client
  something back: **elicitation** (ask the person a question, e.g.
  "which transport request?"), **sampling** (let the *client's* model
  generate text for the server) and **roots**. Proposal: elicitation
  passes through from stage 2; **sampling is refused** until decided
  separately, because it lets a backend spend the client's model and
  send it data — the light question in reverse. Agreed?
- **Q2 — a4h.** Who sets up the basis part (§11 stage 4), and can the
  gateway reach a4h directly over TLS (P-cert needs the TLS connection
  to end at SAP)? Where does a4h run?
- **Q3 — the ABAP MCP server.** For the stage-4 measurement a
  ten-line ICF handler with `whoami` is enough. For real use: is there
  a specific ABAP MCP implementation you want to run on a4h, or should
  `oaap-lab` carry a minimal one?
- **Q4 — mapping in SAP.** Do you expect basis teams to want the
  mapping in `CERTRULE` themselves (rule **sap**), or is the gateway
  table the normal case?

## Deutsche Zusammenfassung

**Was gebaut werden soll:** Ein MCP-Gateway als eigene OAAP-App, nach
demselben Muster wie das KI-Gateway. Nach unten bietet es je **Sicht**
einen MCP-Endpunkt `/mcp/<sicht>` an. Der Client sieht einen einzigen
MCP-Server, aber nie, welche Server tatsächlich dahinterstehen.
Übernommen werden Schlüssel (einmal angezeigt, nur als Hash
gespeichert), Kontext, Budget, Rate, Tresor, „Volumen statt Geld", die
Kontext-Kopie je Messzeile und `/report/v1/usage` mit *einer* Abfrage.
Diese Teile wandern in ein gemeinsames Modul beider Apps (Stufe 0).

**Sichten und Bündel:** Eine Sicht wählt Tools, Resources und Prompts
aus, ein Bündel fasst die Angebote mehrerer Server in einer Sicht
zusammen. Tools bekommen Namen der Sicht; Namensgleichheit wird beim
Speichern abgelehnt. Argumente lassen sich festnageln oder begrenzen
(„Paket immer ZDEMO"). Keine KI im Bündel — das war deine Entscheidung.

**Katalog:** Was ein Server neu anbietet, erscheint nirgends von
selbst. Ändert ein Server die Beschreibung eines freigegebenen Tools,
wird das Tool gesperrt, bis der Betreiber die Änderung bestätigt. Das
schützt gegen Anweisungen, die über Tool-Texte ins Modell geschmuggelt
werden. Jedes Tool trägt eine **Wirkungsklasse** (lesen / schreiben /
ausführen); vergeben wird sie vom Betreiber, nicht vom Server.

**Zwei Identitäten:** *Wer zahlt* — der Schlüssel, oder bei einem
angemeldeten Menschen ein **Zugangsprofil** seiner Gruppe mit demselben
Kontext. *Wer handelt im Backend* — der Benutzer. Die Anmeldung läuft
so, wie MCP es vorsieht: Der Client öffnet den Browser, der Mensch
meldet sich am Keycloak des Mandanten an (später Entra), und das
Gateway nimmt nur Tokens an, die an *dieses* Gateway adressiert sind.

**Richtung Server, drei Verfahren:** **T** technischer Benutzer; **X**
Token-Tausch beim IdP (ein Token nur für dieses Backend, bei Entra
„On-Behalf-Of"); **P** Propagation. Nie: Benutzerpasswörter im Gateway
speichern, das Client-Token einfach weiterreichen, oder auf den
technischen Benutzer ausweichen, wenn der echte Benutzer nicht
durchkommt.

**Der Kernbefund für SAP:** Weder Keycloak noch Entra liefern
verlässlich einen Nachweis, mit dem SAP etwas anfangen kann. Keycloaks
Token-Tausch kann laut Doku keine SAML-Zusicherung erzeugen. Bei Entra
ist das nur auf dem alten v1-Endpunkt belegt, und auch dort mit Fehlern;
Microsofts eigene SAP-Anleitung wandelt deshalb in Azure API Management
um. Daraus folgt die Konstruktion: **Der IdP sagt, wer jemand ist. Den
SAP-Nachweis stellt das Gateway selbst aus**, genau wie der SAP Cloud
Connector. Standard ist ein **Zertifikat mit Minuten-Laufzeit** mit
`CN=<SAP-Benutzer>`, unterschrieben von einer Zertifizierungsstelle je
Mandant. SAP vertraut ihr in `STRUST` und ordnet das Zertifikat über
`CERTRULE` dem Benutzer zu. `SY-UNAME` ist dann der Mensch, mit seinen
Berechtigungen, Änderungsbelegen und Transportaufträgen. Als Alternative
gibt es eine selbst ausgestellte SAML-Zusicherung, die der OAuth-Server
von SAP in ein SAP-Token tauscht. Der Weg ist für Keycloak und Entra
derselbe.

**Dein Hauptfall ist der einfache:** Läuft der MCP-Server **im
ABAP-System** als ICF-Dienst, *ist* der Aufruf des Gateways die
SAP-Anmeldung — dazwischen muss niemand eine Identität weiterreichen.
Schwierig ist nur ein MCP-Server außerhalb von SAP, der seinerseits SAP
aufruft; das RFC sagt das offen. Damit das Zertifikat ankommt, muss die
TLS-Verbindung **bei SAP enden** (ICM oder Web Dispatcher); über
RFC-0033 heißt das `kind: tcp`.

**SAP-Benutzername (konfigurierbar, wie gewünscht):** eine Liste von
Regeln je Server; die erste, die einen Namen liefert, gilt. Möglich
sind ein Merkmal im Token, eine Tabelle im Gateway, eine Ableitung
(z. B. aus der E-Mail) oder die Zuordnung in SAP selbst über
`CERTRULE`. Findet keine Regel einen Namen, wird abgelehnt, mit klarem
Grund.

**Backend-Schutz:** je Server eine Obergrenze für gleichzeitige Aufrufe
mit kurzer Warteschlange, Raten je Server / Server+Benutzer /
Schlüssel, Zeitlimit und ein Sicherungsautomat. Das schützt die
SAP-Dialog-Workprozesse vor einem Agenten in einer Schleife.

**Nie protokolliert:** Tool-Argumente, Tool-Ergebnisse, Inhalte von
Resources, Prompt-Texte. Gemessen wird je Aufruf; die Dimension `tool`
erlaubt eine Abrechnung je Tool außerhalb des Gateways.

**Stufen:** 0 gemeinsames Modul · 1 ein Server, technischer Benutzer,
Auswahl, Messung, Schutz · 2 Bündel, Resources/Prompts ·
3 Anmeldung über Keycloak, Token-Tausch · 4 Zertifikat an **a4h**,
gemessen mit einem winzigen ABAP-Tool `whoami`, das `SY-UNAME` liefert ·
5 SAML-Variante und Entra.

**Nachtrag 27.10. (deine Antworten):** Rückfragen vom Server an den
Client sind je Sicht einstellbar (Sampling standardmäßig aus). Das
Ausstellen des SAP-Nachweises wandert aus dem Gateway in die Plattform
— **RFC-0066**, Destination mit `principal_propagation` —, damit auch
CAP-Apps es nutzen. Der SAP-Benutzer kommt normalerweise aus **einem**
IdP-Attribut `sap_user` für alle Systeme.

**Offen (§13):** Rückfragen vom Server an den Client (mein Vorschlag:
Rückfragen an den Menschen erlauben, Sampling vorerst sperren);
Einrichtung von a4h und der Netzweg dorthin; welcher ABAP-MCP-Server;
ob Basis-Teams die Zuordnung lieber selbst in `CERTRULE` pflegen.
