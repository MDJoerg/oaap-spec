# RFC-0073: Apps as MCP Sources — The Manifest Declares a Door, the Gateway Finds It, the Platform Carries the Person

- **Status:** **Accepted (2026-11-07)** — Jörg: "Ich folge Deinen Empfehlungen.
  Akzeptiert und weiter" (D1–D8 as recommended); stage 1 in progress
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
