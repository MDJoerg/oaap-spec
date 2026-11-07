# RFC-0073: Apps as MCP Sources — The Manifest Declares a Door, the Gateway Finds It, the Platform Carries the Person

- **Status:** **Accepted (2026-11-07)** — Jörg: "Ich folge Deinen Empfehlungen.
  Akzeptiert und weiter" (D1–D8 as recommended); **stage 1 built and measured on `oaap-test`
  (reference 0.1.237, `mcp-gateway` 0.4.0, §12)**, rolled out to the four LAN nodes;
  **stage 2 built and measured on `oaap-test` (reference 0.1.238, `mcp-gateway` 0.5.0,
  §13)**, rolled out to all five nodes; **stage 3 built and measured on `oaap-test`
  (reference 0.1.239, `mcp-gateway` 0.6.0, D9–D13, §14)**, not rolled out
- **Date:** 2026-11-07
- **Authors:** Jörg (direction: I-41 of 2026-11-05, "the manifest declares
  doors, the platform interprets nothing"), Claude (facts read in specs and
  reference code, design)
- **Depends on:** RFC-0065 (MCP gateway; views, default-deny catalog, access
  procedures, sign-in), RFC-0067 (agents as principals, the signed person),
  RFC-0040 (the person's id), RFC-0041 (the tenant's provider, binding of a
  provider subject to a person), RFC-0027 (machine principals, keys limited to
  one instance), RFC-0068 (closed egress), RFC-0030 (rehearsal)
- **Changes (when accepted):** manifest 0.11 (`mcp:`, `mcp_sources:`),
  `oaap.apps.runtime`, `oaap.core.gateway`, `oaap.core.identity` (one more way
  `/verify` resolves a person, limited to one door), `oaap.ai.mcp-gateway` 0.4
  (procedure **I**, sources)
- **Driver:** I-41, step 2. A chat or an agent becomes useful through what it
  can reach: instances, cases (RFC-0061), events (RFC-0032), SAP behind a
  destination. Today an OAAP app that speaks MCP can be put behind the gateway
  only by hand, and only with a technical credential: the app then sees the
  gateway, not the person.

## Summary

An app that speaks MCP says so in its manifest: `mcp: {path: /mcp}`. The
platform interprets nothing beyond that. Every MCP gateway instance of the
same tenant on the same node **finds** such instances in a short list and
registers each as a server; nothing reaches a view until the operator approves
it (RFC-0065 D9 stands).

To call a source **as the signed-in person**, the gateway does not reach the
app directly. It sends the MCP request to a door on **its own site**,
`/platform/mcp/to/<instance>/`, together with the person's token, exchanged
for one addressed to the platform. Identity checks the token, finds the person
the tenant's provider bound to that subject, and `/verify` answers with the
same six headers a browser session would produce. The platform gateway
forwards to the app's declared path. **The app sees the person exactly as if
they had clicked**, so an app that anchors on `X-OAAP-User-Id` and asks
`may()` is right without a line of change. This was measured in the
end-to-end test of RFC-0067 (§10.5, `kontext-probe`) for the browser and for a
key; this RFC closes the person-through-the-gateway case.

Agents need nothing new: an agent is a machine principal (RFC-0067 §4), and
its key, limited to the source instance, is procedure T.

## 1. Facts (read 2026-11-07; measured where noted)

| Claim | Where |
|---|---|
| The MCP gateway checks a signed-in person's token itself (issuer, audience, expiry, RS256) and carries them to a backend by procedure X (token exchange) or P; **measured against the real Keycloak on `oaap-test` 2026-11-07, 14/14** | RFC-0065 §6, §15; CURRENT_STATE 422 |
| Apps are told nothing about the tenant's provider and receive only `X-OAAP-*` headers (no login built by an app) | RFC-0041 §4; RFC-0065 §15 point 1 |
| Procedure X therefore does not fit an OAAP app: the app would have to become an OAuth resource server of a provider it must not know | follows from the line above |
| Identity stores, per person who signed in through the tenant's provider, the binding `{provider, subject}` and finds the person by it | reference `services/identity/app.py`, `idp.find_binding`, record field `idp.subject` |
| `/verify` answers six headers, the sixth a signed assertion with `aud` = instance, 5 minutes, only for a person | `oaap.core.identity` §2.3, §2.11 |
| A key of a machine principal can be limited to one instance; at the app it yields that principal's headers | RFC-0027; RFC-0067 §4, measured §10.5 |
| A platform door on an instance's **own** site, opened by a platform-owned key limited to a pseudo-instance, exists already (`/platform/cases/submit`) | `oaap.apps.runtime` §2.24 |
| Instances start no connection of their own; destinations are the one way out | RFC-0068 |
| `kontext-probe` serves UI, REST and MCP on one route and is right at all three doors with `X-OAAP-User-Id` and `may()` alone | RFC-0067 §10.5 |
| Claude Code exchanges an authorization code only at an `https` token endpoint (localhost exempt); a browser sign-in through a client therefore needs TLS at the provider, independent of this RFC | CURRENT_STATE 422 |

## 2. The door in the manifest (D1)

```yaml
mcp:
  path: /mcp          # on the instance's own HTTP route; Streamable HTTP
```

- **Declaration only.** The platform records the path and lists the instance
  as a source (§3). It does not read tools, does not speak MCP and does not
  judge the app's descriptions; that is the gateway's catalog (RFC-0065 §4).
- `path` is a local path under one of the app's `routes`; anything else is
  refused where the manifest is validated. One door per app in this RFC.
- **`openapi:` is reserved**, refused with a sentence naming I-39, until its
  own RFC decides how operations become tools (I-39 has open questions about
  descriptions, effect classes and approval per operation).
- A rehearsal instance (RFC-0030) is never a source: it runs new code on a copy
  of production data, and a tool there would answer with production data under
  a test version.

## 3. Finding the sources (D2)

A gateway app declares that it consumes sources:

```yaml
mcp_sources:
  read: true
```

The instance receives, as for cases (`oaap.apps.runtime` §2.24),
platform-owned variables: `OAAP_MCP_SOURCES_URL` and `OAAP_MCP_SOURCES_KEY`
(a key of `instance:<name>`, limited to the pseudo-instance
`oaap.mcp.sources:<name>`, minted once, never for a rehearsal).

- `GET /platform/mcp/sources` on the gateway's own site lists the instances of
  **the same tenant on this node** that declare `mcp:` — name, app, version,
  path, and whether the instance is in standby or maintenance (RFC-0059). No
  other tenant, ever; a node-wide list does not exist.
- The gateway **registers** each listed instance as a server named after the
  instance, procedure **I** (§4), and reads its catalog with the first
  signed-in person who uses it, exactly as procedure X does today
  (`server read --token-stdin`). A name that already exists as a hand-made
  server is refused and shown, never overwritten.
- **Default deny stands:** a registered source shows nothing in any view until
  the operator approves its entries; descriptions are pinned; a changed
  description blocks the entry (RFC-0065 §4.2). The gateway's light default
  applies; the operator sets it.
- A source that disappears from the list (removed, renamed) keeps its entries
  in the views, marked as gone, until the operator removes them; a rename
  appears as a new source. Nothing vanishes silently from a view somebody
  relies on.

## 4. The person through the platform: procedure I (D3, D4)

### 4.1 The way

```text
client ──token(aud=gateway)──▶ MCP gateway
          gateway: token exchange at the provider → token(aud=platform client)
MCP gateway ──POST /platform/mcp/to/<instance>/  (own site)
              Authorization: Bearer <sources key>
              X-OAAP-Act-Token: <token for the platform>
          platform gateway → identity /verify (forward auth)
              key limited to oaap.mcp.sources:<gateway>?   provider token valid?
              person bound to that subject?  target in tenant, declares mcp:?
          ◀── six headers of the PERSON (assertion aud = <instance>)
platform gateway ──▶ <instance> at its declared path, headers set
```

- **One hop, inside the platform.** The gateway never opens a connection to
  another instance's port; RFC-0068 is untouched. The door exists only on the
  gateway's own site, one generated block per source of its tenant, written
  when a source or the gateway is installed, renamed or removed (the same
  regeneration that writes every site today).
- **What `/verify` checks, all of it, every call:**
  1. the bearer key is a sources key, limited to `oaap.mcp.sources:<g>`, of a
     live gateway instance `<g>` that declares `mcp_sources`;
  2. the act token: issuer = the provider of `<g>`'s tenant, audience
     contains **the platform's own client** of that realm, not expired, RS256
     with the provider's published keys (identity already holds them as the
     relying party, `oaap.core.identity` §2.8);
  3. a person exists whose binding is `{that provider, sub}`, is `kind:
     human`, active, of that tenant;
  4. the target instance is of the same tenant, declares `mcp:`, is not a
     rehearsal.
  Any failure: 401 (credential) or 403 (person known, target refused), with a
  sentence the gateway passes on; **no fallback** to the gateway's own
  principal (RFC-0065 D8).
- **What the app gets:** the six headers of §2.3, built by the same function
  as for a session; route role and group restrictions of the target apply to
  the person, fresh on every call. The client-sent `X-OAAP-Act-Token` is
  stripped before the request reaches the app, like every identity header.
- **What the gateway records:** procedure `I`, `user_sub` and `user_iss` as
  for X (RFC-0065 D16). Identity logs `mcp.act` per person, target and gateway
  in the tenant's log, without the token.

### 4.2 Why exchange first (D4)

The token a person's client presents is addressed to the gateway. RFC-0065 §6
forbids passing it on: a token for the gateway would then work wherever it is
accepted. The gateway therefore exchanges it — the same standard exchange as
procedure X, measured on 2026-11-07 — for a token addressed to the platform's
client of the realm. Identity then checks a token addressed to itself, which
is what a resource server does, and Keycloak's own log shows every exchange.
The realm has to allow it: the gateway's confidential client gets an audience
mapper onto the platform's client. By hand for the measurement; a job of the
IdP connector later (RFC-0065 D15).

Rejected alternatives:

- **The gateway names the person** (`on_behalf_of`, a header with a user id).
  RFC-0067 D3 refused exactly this at the delegation door: the app could name
  anybody. With a token, a compromised gateway can act only for people whose
  tokens it holds at that moment, for minutes.
- **Identity accepts the gateway's token directly.** Works, but breaks the rule
  of §6 and needs a second registry of which client belongs to which gateway.
- **An act credential first, then a direct call to the app.** A second
  credential to issue, store and expire, and a connection to another
  instance's port that RFC-0068 does not have.

### 4.3 What this does and does not prove

Like RFC-0067 §3.4: the platform proves that the provider recently
authenticated this person and that a gateway of the tenant holds their
token. It does not prove that the person wanted *this* call; the gateway's
confirmation on writing effect classes (I-41) and the view's approval are the
counterweights. A gateway instance is installed by an administrator, and the
`mcp_sources` line in its manifest is the statement that it may do this.
The portal shows it on the instance page.

## 5. A person the node does not know yet (D5)

Identity creates a person on the **first browser sign-in** through the
tenant's place (§2.8), following the tenant's first-login policy. Someone who
signs in at Keycloak but has never visited the tenant's place has no binding.
Proposal: **refuse** with the sentence "Diese Person hat sich an diesem Ort
noch nie angemeldet — einmal im Portal anmelden", and create nothing at this
door. Records created by incoming traffic stay on the one path built for them,
with its throttle and its write lock. Widening later is cheap; taking back an
account the gateway created is not.

## 6. Agents and the key way (D6)

A view reached with a gateway key has no person behind it. Toward an OAAP app
the right identity is the **agent's own principal** (RFC-0067 §4): the
operator stores the agent's platform key, limited to the source instance, as
the server's credential — **procedure T**, which exists. The app sees the
agent's name, `may()` answers with the agent's own assignments, and the
assertion is empty. A source registered automatically (§3) carries procedure
I; for a key view the operator registers the same instance a second time by
hand with T and the agent key. No new mechanism, and no way for a key to
borrow a person.

## 7. Not part of this RFC

- **Assistants** (`oaap.ai.assistants`) and the **chat app**: I-41 steps 3
  and 4, their own RFCs.
- **`openapi:` → tools** (I-39).
- **Sources on another node** of the same tenant. The door is one hop through
  one node's gateway; across nodes it needs a destination with procedure I and
  is a later amendment.
- **TLS for sign-in with Claude Code, Desktop and the phone.** A prerequisite
  measured on 2026-11-07 (CURRENT_STATE 422), independent of this RFC: the
  measurement here uses a script as the client.
- **The IdP connector creating the clients and mappers** (RFC-0065 D15).

## 8. Security requirements (proposed)

1. A source is listed only to gateway instances of its own tenant on its node;
   a rehearsal is neither source nor consumer.
2. `/platform/mcp/to/<i>/` exists only on a consuming gateway's own site and
   only for sources of its tenant; the sources key opens nothing else.
3. The act token is checked like any token addressed to the platform (issuer,
   audience = the platform's client, expiry, signature); a token addressed to
   the gateway is refused.
4. The person comes only from the provider's binding; nothing the gateway
   states can name a person.
5. No fallback: a failed act is a refusal, never a call as the gateway.
6. The app receives the same six headers as for a session, and never
   `X-OAAP-Act-Token`.
7. Every act is in the tenant's log, without the token.

## 9. Conformance (described; every line has a bait)

1. A manifest with `mcp.path` outside its routes, or with `openapi:` → refused
   at validation.
2. The sources list of gateway G in tenant A shows A's sources on this node,
   not B's, not a rehearsal; a key of another scope gets 401.
3. Through the door as anna → the app sees anna's `X-OAAP-User-Id`, roles and
   an assertion with `aud` = the source; `may()` gives anna's answer.
4. bert (known, but the route requires a role he lacks) → 403 from the route,
   not from the app.
5. Act token addressed to the gateway, expired, of another realm, tampered → 401;
   no request reaches the app (bait: the app counts calls).
6. Person with a valid token but no binding on this node → refused with the
   sentence of §5; no record created.
7. Target of another tenant, without `mcp:`, a rehearsal → 403.
8. Sources key used at another instance's site or at `/platform/cases/submit`
   → refused.
9. Client-sent `X-OAAP-User-Id` and `X-OAAP-Act-Token` do not arrive at the app.
10. A source removed → its view entries marked gone, not silently dropped.

## 10. Stages

| Stage | Content | Measured on |
|---|---|---|
| **1** | manifest 0.11 `mcp:` and `mcp_sources:`; sources list; `kontext-probe` declares `mcp:`; gateway registers sources (still with procedure T and an agent key, §6) | `oaap-test`, tenant `vuebung`: `kontext-probe` appears in `mcpgw-test`, approved into a view, called with an agent key; the app sees the agent |
| **2** | the door `/platform/mcp/to/<i>/`, `/verify` with act token, procedure **I** in the gateway | `oaap-test`, realm of `vuebung` with the exchange mapper: anna and bert by script through the gateway into `kontext-probe`; every line of §9 |
| **3** | the portal shows source and consumer on the instance page; the IdP connector creates the gateway's clients and mapper | `oaap-test` in a real browser |

The browser sign-in with Claude Code follows as soon as provider and gateway
have TLS.

## 11. Decisions

| # | Proposal | Recommendation |
|---|---|---|
| **D1** | The manifest declares one MCP door, `mcp: {path}`; `openapi:` reserved and refused until I-39 has its RFC | yes |
| **D2** | Sources are found by a list on the gateway's own site, same tenant and node only; registered automatically, **nothing in a view without approval** | yes |
| **D3** | The person reaches an OAAP app through **procedure I**: the platform carries the call and `/verify` produces the person's six headers; apps change nothing | yes |
| **D4** | Proof at the door: the person's token **exchanged for one addressed to the platform's client**; never the gateway's token, never a name | yes |
| **D5** | A person without a binding on the node is refused with a sentence; this door creates no accounts | yes |
| **D6** | Agents: procedure T with the agent principal's key limited to the source; nothing new | yes |
| **D7** | Sources on the same node only in this RFC | yes |
| **D8** | Rehearsal instances are neither sources nor consumers | yes |

**Decided (Jörg, 2026-11-07):** D1–D8 as recommended.

## 12. Stage 1 built and measured (2026-11-07, reference 0.1.237, `mcp-gateway` 0.4.0, `kontext-probe` 0.1.4)

**Built.** Manifest 0.11 (`mcp`, `mcp_sources`, `openapi` refused) in the
schema and in `appctl.py`; the key `oaap.mcp.sources:<name>`, minted, renewed,
reissued and retired like the other platform keys; the list written into the
consuming gateway's own site, its digest in the site marker (block format 6);
`oaap.apps.runtime` 0.2.53 §2.32, `oaap.ai.mcp-gateway` 0.4 §3.6. The gateway
syncs at start, every 5 minutes, after a failure after 30 s, and by
`source sync`.

**Tests.** Reference `test_mcp_sources.py` (manifest, site, list, marker,
keys; three mutations — tenant filter, rehearsal filter, key scope — each
turned it red); `test_platform_feedback`, `test_instance_keys`,
`test_rebuild_git` adjusted to format 6, five key kinds and manifest ≥ 0.10
(the one failure left in `test_rebuild_git`, item 4, was there before);
gateway `test_sources.py` (two mutations caught) and the existing 307 checks
of the gateway green; schema `validate.py` ten new cases.

**Measured on `oaap-test`** (staged 0.1.237, 28 sites rewritten, HEALTHY
before and after):

| Asked | Answer |
|---|---|
| `vuebung-mcpgw` (tenant `vuebung`) reads its list | `["vuebung-kp"]` |
| `mcpgw-test` (tenant `default`) reads its list | `[]` |
| A gateway's key at the other gateway's site | 403 |
| The key at its own app root, at a source's site | 403, 404 |
| No key | 303 to the login, no list |
| Sync registers `vuebung-kp` | server with access `none`, light `red`, marked as source, in no view |
| Operator sets the agent key (`mcp-agent`, collection "KP Lesen", `project = pA`, limited to `vuebung-kp`), approves three of four tools into view `kp` | catalog read, 4 tools |
| Through the gateway with a view key (`messung_rfc0073_stufe1.py`) | 8/8: 401 without key; `tools/list` the three approved; `list_projects` → only pA; pB invisible; `add_entry` refused **by the app** (the agent reads only); `search` refused by the gateway |
| A gateway removed with `--purge` | its sources key revoked, principal deleted |

**Deviations from §3, decided while building:**

- The list does **not** carry standby or maintenance state. The site is
  rewritten when the registry changes, and standby flips often without an
  install; a stale "awake" in a written list would be wrong. A source in
  standby answers the way the platform makes it answer (RFC-0059).
- The address in the list is the source's own LAN port behind its routes —
  the path procedure T with an agent key takes. Stage 2 adds the door on the
  gateway's site for procedure I.

**Findings:**

1. **On a first install the gateway's site is not yet rewritten when its
   container starts**: the first read got 404 on both gateways. Fixed in the
   app (retry after 30 s). The retry itself was not caught live a second time:
   the measuring install recreated the container after the site was written.
2. **`oaap authz agent-add` wants the full collection id**, while
   `oaap authz collections` prints eight characters. The id had to be read
   through the internal API. Small fix for the CLI, not done here.
3. A new gateway instance needs `MCPGW_MASTER_KEY` set by hand
   (`generate: token` fills nothing on the CLI, known since RFC-0041); without
   it the agent key was refused and lost — revoked and issued again.

**Not measured:** a source on another node (out of scope, D7), a source that
disappears live (unit test only), procedure I (stage 2).

## 13. Stage 2 built and measured (2026-11-07, reference 0.1.238, `mcp-gateway` 0.5.0)

**Built.** The door `/platform/mcp/to/<source>` on a consuming gateway's own
site, one block per source in its list (`oaap.apps.runtime` 0.2.54 §2.32.1);
`/verify?act=` in identity with its own module for the act token (`act.py`,
RS256 by hand as the gateway's `signin.py`; `oaap.core.identity` 0.6.3 §2.12);
the list carries `door`; the site digest covers the door's roles, groups and
target. In the gateway: access `platform`, the exchange with its own client
for `MCPGW_PLATFORM_AUDIENCE`, the call with sources key and act token,
procedure `I` in the measurement rows (`oaap.ai.mcp-gateway` 0.5 §3.7).

**Tests.** Reference `test_mcp_act.py` (act module: signature, issuer,
audience, expiry, `none`/HS256, short key, refetch brake; identity: both
credentials, an **unlimited key of the same principal `instance:gw`** refused,
another gateway's key, the cases key, other tenant, binding only in the
source's tenant, no binding → §5 sentence and nothing created, route roles,
audit lines without a token, an act token alone opens no ordinary route);
`test_mcp_sources.py` section 7 (door blocks, order, strips, no door to a
rehearsal or another tenant, digest follows route roles); `test_tenant.py`
holds the act branch to the same rule as `/verify` (no tenant in an app's
headers). Gateway `test_gateway.py` (+18: registration with door, exchange as
own client for the platform client, sources key and act token at the door,
never the person's token, cache, no fallback, `refused` not counted by the
breaker) and `test_sources.py` (+5: none → platform, operator's access kept).
Mutations caught: the exact-scope check (only after adding the bait of an
unlimited key of `instance:gw` — without it the mutation survived), the
assertion's audience, the binding check, the act header in upstream,
procedure `I` in the rows, the breaker exemption, the stale-identity
exception.

**Measured on `oaap-test`** (staged 0.1.238; `vuebung-mcpgw` 0.5.0; realm
`vuebung` of the `auth` Keycloak 26.7.4; `messung_rfc0073_stufe2.py`):

| Asked | Answer |
|---|---|
| anna (bound, KP Mitarbeit pA) through view `kp-i`, procedure I | `tools/list` the three approved; `list_projects` → only pA; `add_entry` pA **accepted by the app** and listed as hers |
| bert (bound, KP Lesen pB) | only pB; `add_entry` pB refused **by the app** |
| the door directly with sources key + exchanged token | 200, the app sees anna; client-sent `X-OAAP-User`, `-Id`, `-Roles` do not arrive |
| no act token / a token addressed to the gateway / tampered signature / no sources key | 401 / 401 („not addressed to the platform's client“) / 401 / 401 |
| carl, valid token, never signed in at the place | 403, „Diese Person hat sich an diesem Ort noch nie angemeldet — einmal im Portal anmelden.“ |
| a source without a door; the sources key at the source's own site; at `/platform/cases/submit` | 404; 403; 404 |
| `mcpgw-test` (tenant `default`) with its own sources key at this door | 403 |
| `vuebung-kp` limited to visibility group `kp-team`, only anna in it | gateway site rewritten by itself (`groups=kp-team` in the door); anna as before; bert: „Die Plattform lehnt ab (HTTP 403): Forbidden: not in a visibility group for this app“ |
| tenant log | one `mcp.act` per call: 61 accepted, refusals for token, binding and route, no token in any line |
| stage 1 again (view `kp` on a hand-made server `kp-agent` with a fresh agent key) | 8/8 |

Total: part A 21/21, part B 8/8.

**Deviations, decided while building:**

- §4.1 check 4 (target of the same tenant, declares `mcp:`, not a rehearsal)
  is enforced **where the door is written**: a door exists only for a source
  in the gateway's list. Identity compares the tenants once more; it does
  not read the registry.
- The door path has no sub-paths: `/platform/mcp/to/<source>` and the same
  with a trailing slash are rewritten to the declared `mcp.path` (Streamable
  HTTP has one endpoint).
- The gateway's two settings are explicit (`MCPGW_CLIENT_SECRET`,
  `MCPGW_PLATFORM_AUDIENCE`); the list does not carry the platform client.
  The IdP connector creating client and mapper is stage 3.

**Findings:**

1. **The tenant `vuebung` pointed at a client that no longer existed in its
   realm** (`oaap-vuebung-uebung`, made at the tenant build on 18.10.): every
   browser sign-in through the tenant's place would have failed. `oaap tenant
   check` said „All records resolve“. Repaired with the platform's own path,
   `oaap idp provision auth --tenant vuebung` (needs an external name; the
   client is now `oaap-probe.oaap.invalid`). A check that asks the realm
   whether the tenant's client exists is missing.
2. **The gateway treated a refusal of the door as a failure of the server**:
   the platform's sentence was lost („HTTP 403“) and every refusal counted
   for the circuit breaker — five attempts of one person without a right
   would have closed the source for everyone. Fixed in 0.5.0 before the
   rollout (`upstream.Refused`, measured).
3. **The first measuring script believed a JSON-RPC error was an accepted
   call** (no `result`, so no `isError`): „add_entry accepted“ passed while
   the profile's effect ceiling (`read`) had refused it. The checks now
   require a `result`. The profile needed `--max-effect write`.
4. **The act branch first stood between `verify()` and the next route** and
   tripped `test_tenant`'s static reading of `/verify`; moved before it, and
   the test now reads the act branch with the same rule.
5. `oaap authz assign` wants the full collection id, like `agent-add`
   (stage 1 finding 2), and a context, not a value, for `project`.
6. Every MCP call is one line in the tenant log. Right for now (§8.7); the
   volume for a chat is a question for stage 3 or the chat app.

**Not measured:** an expired act token live (unit test only), a token of
another realm at the door (unit test only), the browser sign-in with Claude
Code (needs TLS), a source in standby behind a door.

## 14. Stage 3 built and measured (2026-11-07, reference 0.1.239, `mcp-gateway` 0.6.0)

**Decided before building (Jörg, 2026-11-07: "ja weiter mit D9–D13 wie
vorgeschlagen"):**

| # | Proposal | Decided |
|---|---|---|
| **D9** | The connector's result reaches the gateway as **platform-owned variables** (`OAAP_MCP_IDP_*`) of an instance with `mcp_sources`; the app takes them as defaults, its own settings set by hand win | yes |
| **D10** | **On request only**: `oaap idp mcp <connector> --instance <gw>` with plan and `--dry-run`, and a portal button for `server_admin`; never at install | yes |
| **D11** | `oaap-mcp-<instance>` (confidential, exchange only) and `oaap-mcp-<instance>-login` (public, PKCE, redirect only `http://localhost:33418/callback`) | yes |
| **D12** | Switching off and removing the gateway **disable** both clients; nothing is deleted (RFC-0041 K3.3) | yes |
| **D13** | `oaap tenant check` asks the provider whether the tenant's client (and the gateways' clients) exist and are enabled | yes |

**Built.** The connector verb `mcp_clients` (`oaap.core.tenant` 1.5 §2.9.1):
plan with the version first, the tenant's space and client required and
never made here, both found clients judged **before** anything is written
(a wrong kind under the second name leaves the first one unmade), a found
client re-enabled and given the exchange switch, our redirect and the
audience mapper and nothing else, disabling by `PUT enabled: false`.
`oaap idp mcp` and the portal's worker call one function; it writes the five
variables (`oaap.apps.runtime` 2.32.2), recreates the container only when
they changed, records `mcp_idp` without the secret, writes one tenant-log
line. A redeploy keeps record and variables; without `mcp_sources` or as a
rehearsal the variables are dropped and the clients disabled. The gateway
falls back setting by setting and its operator page says where each came
from (`oaap.ai.mcp-gateway` 0.6 §3.8). The portal card **MCP** (`oaap.core.portal`
0.3.35 §2.16). `tenant check` asks every connector (D13).

**Tests.** Reference `test_mcp_idp.py` (60 checks against a paper Keycloak:
bodies, plan, creation, second run writes nothing, no space / no tenant client
refused, wrong kind refused without a half-made pair, a found disabled client
completed and nothing else touched, disabling without DELETE, `not ours`,
wrong version before any write; the platform's refusals before any call,
dry run, variables, record without secret, log line, recreate once, off,
removal disables or names both clients, `tenant check` findings and
unreachable provider, the worker's role check), `test_mcp_portal.py` (21:
the real worker refuses a `tenant_admin` and logs it, a `server_admin` calls
the same function; the card for source, gateway, set up, off, a provider by
hand, no provider, rehearsal; never the secret even if a record carried
it), `test_care_portal.py` (+1, where the card sits). Gateway
`test_platform_settings.py` (11, one process per case). Mutations caught: the
kind check, the pre-check order, the tenant's client in `tenant check`, a
secret in the record, enable instead of disable, the dry run returning,
PKCE, the password grant, the worker's role check.

**Measured on `oaap-test`** (staged 0.1.239; `vuebung-mcpgw` 0.6.0; `auth`
Keycloak 26.7.4 with its narrow `create-realm` service account;
`messung_rfc0073_stufe3.py`, 37/37 with the stage-2 clients still present,
36/36 after removing them):

| Asked | Answer |
|---|---|
| `oaap idp mcp auth --instance vuebung-mcpgw --dry-run` | the plan, nothing called |
| the same without `--dry-run` | `oaap-mcp-mcpgw` and `oaap-mcp-mcpgw-login` created; five variables in the instance; container recreated; record without secret |
| again | both "already there", nothing written, container not recreated |
| the two clients, read with the admin API | exactly the shapes of §2.9.1 (confidential/exchange/audience → `oaap-probe.oaap.invalid`; public/code/PKCE S256/redirect only `localhost:33418`/audience → gateway client) |
| anna and bert, **authorization code with PKCE** through Keycloak's login form, back to `http://localhost:33418/callback` | a code and a token addressed to the gateway client |
| the same with port 33419, or with `127.0.0.1` instead of `localhost` | Keycloak 400 „Ungültiger Parameter: redirect_uri“, no form — **the port is fixed, there is no loopback wildcard** |
| without PKCE; password grant at the sign-in client | `invalid_request`; `unauthorized_client` |
| anna and bert through view `kp-i` with these tokens, MCPGW_* empty | as stage 2: anna only pA and `add_entry` accepted by the app, bert only pB and refused by the app — the exchange runs with the client and secret the platform handed in |
| a token of the hand-made stage-2 client (audience `mcp-gw-vuebung`) | 401: the gateway takes the platform's values |
| the sign-in client disabled by hand at the console; `tenant check` | exit 1, the client named; enabled again → exit 0 |
| `--off` | both disabled, none deleted, the variables gone, record `off`; anna cannot sign in; `tenant check` 0 (an off sign-in is no finding) |
| on again | the same two clients enabled (no new ones); anna through again after ~2 s |
| portal as `server_admin`: gateway page, source page | card MCP: source `vuebung-kp` with a door for persons, issuer, both clients, button „Anmeldung abschalten“; on `vuebung-kp`: „Gelesen von: vuebung-mcpgw“; no secret |
| the button „abschalten“ and „einrichten“ through the node's worker | both clients disabled and enabled again; two `mcp.idp` lines naming the person from the portal |

Afterwards the hand-made clients of stage 2 (`mcp-gw-vuebung`, `mcp-claude`)
were deleted from the realm by hand — the platform never deletes — and the
stale secret taken out of `test/.env`. anna, bert and carl stay.

**Deviations, decided while building:**

- The clients are named after the instance's **local** name (`mcpgw`, not
  the registry key `vuebung-mcpgw`): the realm belongs to one tenant, and
  inside it the instance has that name.
- The portal button is `server_admin`'s alone, as `oaap.core.tenant` 2.9 has
  the connector's credential; a `tenant_admin` sees the state, not the button.

**Findings:**

1. **Keycloak takes the redirect URI literally**: another port on
   `localhost`, or `127.0.0.1`, is refused. Claude Code must be started with
   `--callback-port 33418`, as the gateway's line already says. Measured, not
   assumed (it was an open question of D11).
2. **„ready“ comes a moment too early**: `oaap idp mcp` reports when the
   container has been recreated, and the gateway answers about two seconds
   later. A client retries; the measuring script now does too.
3. The stage-2 measuring scripts (`messung_rfc0073_stufe2.py`,
   `tok_vuebung.py`) need the deleted hand-made clients; stage 3's script
   fetches tokens through the login form and replaces them.
4. Finding 6 of stage 2 (one tenant-log line per MCP call) stays open and
   moves to the chat app, where the number of calls per conversation is known.

**Not measured:** Claude Code itself signing in (needs TLS at provider and
gateway — unchanged since RFC-0065), the page in a real browser (Jörg), a
removal of a gateway with an active sign-in on the node (unit test only), a
redeploy without `mcp_sources` (unit test of the rule only).

## 15. TLS for the sign-in of Claude Code (2026-11-07, reference 0.1.240)

**Decided (Jörg, 2026-11-07: "Ok a freigegeben mit t1-t5"):** way A —
`oaap-test` gets a public name behind the existing edge `oaap-demo`
instead of a private CA. T1 the name `oaap-test.oaap-demo.duckdns.org`
(DuckDNS answers every depth under `oaap-demo.duckdns.org`; nothing to do
at DuckDNS or the router); T2 close the platform gap below; T3 move the
node, Keycloak and the tenant's binding; T4 check the test passwords
before going public; T5 measure.

**Two platform defects, both found on the way, both fixed in 0.1.240
(`oaap.core.gateway` 0.2.21):**

1. **An edge forwarded one level only.** Caddy's `*` is one label; an
   edge route was `host, *.host`, and a tenant's instance is
   `<instance>.<label>.<node>`. Measured on `oaap-demo` before the fix:
   `x.y.oaap-bernd.duckdns.org` answered 303 to the *edge's own* login.
   No edge has ever reached a tenant's instance — `oaap-bernd` has only
   the default tenant. Now `host, *.host, *.*.host`; existing edges are
   rewritten on update (measured: `oaap-bernd` unchanged, two levels now
   301 → https).
2. **Behind an edge every app believed it was served over http.** Caddy
   keeps `X-Forwarded-Proto` only from a trusted proxy and none was
   configured, though `_edge_guard` said the headers were trusted. The
   gateway announced `http://…/mcp/kp-i` as its resource — a client that
   checks the resource against the address it called (the MCP SDK does)
   stops there. Now the edge's address is the only trusted proxy
   (`edge-trust.servers`, imported in the global `servers` block).
   Measured: resource `https://…`; a LAN client with the external name
   still gets 403, a forged header at an instance port changes nothing.

**Measured** (`oaap-lab/mcp-gateway-messung/messung_rfc0073_tls.py`,
**15/15**, all through the public https names, as Claude Code sees them):

| Asked | Answer |
|---|---|
| protected-resource metadata of view `kp-i` | resource `https://mcpgw.vuebung.oaap-test.oaap-demo.duckdns.org/mcp/kp-i`, authorization server the https issuer |
| the realm's discovery document | issuer identical, token endpoint **https** (Claude Code's condition) |
| without a token | 401 |
| anna, bert: code + PKCE, back to `localhost:33418`, redeemed over https | tokens with the https issuer, addressed to `oaap-mcp-mcpgw` |
| procedure I through the gateway over https | anna only pA and writes; bert only pB and is refused by the app |
| the gateway client after `oaap idp mcp` at the new issuer | audience mapper onto the new platform client added; the old one stays (nothing else touched) |

**Findings:**

3. **A provider's new address voids every binding.** `oaap idp provision`
   at the new issuer said so ("bindings made under the old one no longer
   match anybody") and procedure I refused anna and bert ("never signed
   in here"); their first portal sign-in would have made *new* accounts
   without their roles. The platform re-points bindings only for a move
   between nodes. On `oaap-test` this was done once by hand, after the
   platform's own connector had found both bound subjects in the realm
   at the new address: two bindings, one `tenant.idp-repointed` line.
   **T6 (proposed):** `oaap idp provision` re-points when the issuer
   changed but connector and space are the same, and only the bindings
   whose subject the connector finds in that realm.
4. **The connector's address has no command.** The issuer is derived
   from it; it was changed by hand in the connector file (backup kept).
5. **DuckDNS's IPv6 record points at the router**, not at `oaap-demo`
   (`…62b5:8dff:fec8:e2f0`, belongs to none of the nodes; a self-signed
   certificate answers). Every IPv6 client of `oaap-demo`, `oaap-bernd`
   and now `oaap-test` lands there. Containers have no IPv6 and were
   unaffected; the node itself prefers IPv4 now (`/etc/gai.conf`). The
   record is in Jörg's DuckDNS account.
6. After the issuer change the gateway client carries two audience
   mappers; the old platform client was disabled by hand, not deleted.

**T4 done:** the Keycloak passwords are long and random; six active
portal test accounts with unknown passwords were deactivated, not
deleted; `oaap-admin` unchanged.

**Not measured:** Claude Code itself — the browser step happens at
Jörg's PC.

## Deutsche Zusammenfassung

**Worum es geht:** Schritt 2 der KI-Chat-Reihenfolge (I-41). Eine OAAP-App, die
MCP spricht, soll ohne Handarbeit als Werkzeugquelle im MCP-Gateway auftauchen,
und wer über das Gateway kommt, soll bei der App **als er selbst** ankommen,
nicht als das Gateway.

**Der Vorschlag in drei Teilen:**

1. **Die Tür im Manifest (D1).** Die App schreibt `mcp: {path: /mcp}`. Die
   Plattform merkt sich nur das und deutet nichts. `openapi:` ist reserviert,
   bis I-39 ein eigenes RFC hat.
2. **Das Gateway findet die Quellen (D2).** Ein Gateway, das im Manifest
   `mcp_sources: {read: true}` erklärt, bekommt eine Liste der MCP-Apps
   **seines Mandanten auf diesem Knoten** und trägt sie als Server ein. In
   einer Sicht erscheint aber nichts, bevor der Betreiber es freigibt. Das
   bleibt wie bisher (Standard: alles verboten, Texte festgehalten).
3. **Die Person über die Plattform, Verfahren I (D3, D4).** Das Gateway ruft
   die App nicht direkt, sondern schickt den Aufruf an eine Tür auf seiner
   **eigenen** Seite, `/platform/mcp/to/<instanz>/`. Dazu legt es das Token
   der Person, vorher bei Keycloak getauscht gegen eines **für die
   Plattform**. Identity prüft das Token, findet die Person über die
   Verknüpfung mit Keycloak und gibt die **gleichen sechs Kopfzeilen** wie bei
   einer Browser-Sitzung. **Die App merkt keinen Unterschied** und muss nichts
   ändern. Dass Apps mit `X-OAAP-User-Id` und `may()` dann richtig liegen,
   ist mit `kontext-probe` schon gemessen (RFC-0067).

**Warum nicht einfacher:** Würde das Gateway nur den Namen der Person
mitschicken, könnte ein kompromittiertes Gateway jeden nennen. Das haben wir
in RFC-0067 an der Weitergabe-Tür schon abgelehnt. Mit Token kann es nur für
Personen handeln, deren Token es gerade hat, und nur für Minuten. Das Token
der Person geht nie unverändert weiter (RFC-0065 §6).

**Weitere Vorschläge:**

- **D5:** Wer sich noch nie im Portal des Mandanten angemeldet hat, wird
  abgewiesen, mit einem Satz, der das sagt. Das Gateway legt keine Konten an.
- **D6:** Agenten brauchen nichts Neues. Ein Agent ist ein eigener
  Maschinen-Benutzer (RFC-0067). Sein Schlüssel, auf die App beschränkt, wird
  mit Verfahren T hinterlegt.
- **D7:** Nur auf demselben Knoten.
- **D8:** Generalproben-Instanzen sind weder Quelle noch Gateway.

**Stufen:** (1) Manifest und Quellenliste, gemessen mit `kontext-probe` und
einem Agentenschlüssel. (2) Die Tür und Verfahren I, gemessen mit anna und bert
per Skript. (3) Portal und automatische Keycloak-Clients. Der Login mit Claude
Code folgt, sobald `https` steht.

**Entschieden (Jörg, 07.11.):** D1–D8 wie empfohlen.

**Stufe 1 gebaut und gemessen (07.11., Referenz 0.1.237, mcp-gateway 0.4.0, §12):**
Das Gateway im Mandanten `vuebung` findet `kontext-probe` und trägt es ein. Der
Betreiber hinterlegt den Schlüssel eines Agenten (nur Lesen, Projekt pA) und
gibt drei von vier Tools frei. Durch das Gateway sieht die App den Agenten: nur
pA, Schreiben von der App abgelehnt, das nicht freigegebene Tool vom Gateway
abgewiesen. Das Gateway im Mandanten `default` sieht nichts davon, und fremde
Schlüssel kommen an keiner Tür durch. Befunde: Beim ersten Start fehlte die Tür
noch (404, jetzt mit Wiederholung nach 30 s); `agent-add` will die volle
Kennung der Sammlung; ein neues Gateway braucht `MCPGW_MASTER_KEY` von Hand.

**Stufe 2 gebaut und gemessen (07.11., Referenz 0.1.238, mcp-gateway 0.5.0, §13):**
Die Tür `/platform/mcp/to/<quelle>` steht auf der Seite des Gateways; identity
prüft Quellen-Schlüssel und getauschtes Token und gibt die Kopfzeilen der
Person. Gegen den echten Keycloak (Realm `vuebung`): anna sieht nur pA und darf
dort schreiben, bert sieht nur pB und darf nicht schreiben — entschieden von der
App, weil sie die Person sieht. Kaputte, falsch adressierte und fehlende
Nachweise: 401. carl, nie am Ort angemeldet: 403 mit dem Satz aus §5. Mit einer
Sichtbarkeitsgruppe nur für anna scheitert bert an der Route, und der Satz der
Plattform kommt bis zum Client. Jeder Akt steht im Mandantenprotokoll. 21/21
und 8/8. Befunde: Der Mandant `vuebung` zeigte auf einen Keycloak-Client, den
es nicht mehr gab (mit `oaap idp provision` repariert; eine Prüfung dafür
fehlt). Das Gateway wertete eine Ablehnung der Plattform als Serverfehler und
hätte so die Quelle für alle sperren können (vor dem Ausrollen behoben). Mein
erstes Messskript hielt eine Fehlerantwort für einen angenommenen Aufruf
(korrigiert).

**Stufe 3 gebaut und gemessen (07.11., Referenz 0.1.239, mcp-gateway 0.6.0, D9–D13, §14):**
Ein `server_admin` richtet die Anmeldung eines Gateways mit einem Befehl
(`oaap idp mcp auth --instance <gw>`) oder einem Knopf im Portal ein. Der
Konnektor, der den Realm des Mandanten angelegt hat, legt die beiden Clients an
(`oaap-mcp-<instanz>`, `oaap-mcp-<instanz>-login`). Die Plattform reicht die fünf
Werte als `OAAP_MCP_IDP_*` an das Gateway; von Hand Gesetztes gewinnt. Abschalten
und Entfernen deaktivieren beide Clients, gelöscht wird nichts. `oaap tenant
check` fragt jetzt beim Realm nach. Gemessen gegen den echten Keycloak: anna und
bert melden sich wie Claude Code an (Code mit PKCE über das Login-Formular,
Rücksprung `localhost:33418`) und kommen durch das Gateway in die App wie in
Stufe 2 — mit dem Client und Geheimnis von der Plattform. Ein anderer Port und
`127.0.0.1` werden von Keycloak abgewiesen: Der Port ist fest. Die Karte „MCP“
im Portal zeigt Quelle, Leser und den Stand der Anmeldung; der Knopf geht durch
den Worker und steht im Mandantenprotokoll. 37/37. Die handgemachten Clients von
Stufe 2 sind aus dem Realm entfernt. Offen: Claude Code selbst (braucht TLS) und
der Blick im echten Browser.

**TLS für Claude Code (07.11., Referenz 0.1.240, §15):** oaap-test heißt jetzt
`oaap-test.oaap-demo.duckdns.org` und steht hinter dem Edge oaap-demo. Dabei
zwei Plattformfehler gefunden und behoben: Ein Edge reichte nur eine
Namensebene weiter (Mandanten-Instanzen landeten im Portal des Edge), und
hinter einem Edge hielt jede App die Verbindung für http. Gemessen über die
öffentlichen https-Namen: Entdeckung, Anmeldung mit PKCE, Token über https,
durch das Gateway in die App — 15/15. Befunde: Eine neue Adresse des
Anmeldedienstes macht alle Bindungen ungültig (auf oaap-test geprüft und von
Hand umgehängt; Vorschlag T6), die Konnektor-Adresse hat keinen Befehl, und
der IPv6-Eintrag bei DuckDNS zeigt auf die Fritzbox. Offen: Claude Code selbst
an Jörgs Rechner.
