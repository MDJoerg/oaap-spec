# oaap.net.connector — The Inner Node Dials Out, the Outer Node Only Answers

- **ID:** `oaap.net.connector`
- **Version:** 0.2
- **Maturity:** draft (0.1 was RFC-0033 stage 2: connect keys on the
  outer node, the connector and its offer list on the inner node, the
  tunnel between them, `via` targets for HTTP destinations, pause and
  revocation, state on both sides, stream logs. **0.2 is stage 3:
  exposures** (§2.8) — a random public name for one target, from the
  inner node's command line or from a laptop client, login by default,
  a TTL, a sweep. A whole platform through the tunnel (stage 4) and
  rendezvous (stage 5) are the frontier, not specified)
- **Based on:** RFC-0033 (§2, §3, §6, §7, D2, D3, D4, D6, D7, D8, D9,
  D10), RFC-0009 (on-demand TLS under the node's own name), RFC-0010
  (the brake on a public route), RFC-0021 (the
  direction rule: the inner node connects outward), RFC-0027 (machine
  principals — the tunnel's key), RFC-0022 / `oaap.core.tenant` (a
  tunnel carries one tenant), `oaap.net.destinations` (the object a
  tunnel serves)

## 1. Purpose

A backend on a customer's site (an ERP, the tenant's twin) must be
reachable by an app that runs on a node in the internet — without a
port opened on the customer's firewall, and without the internet node
being able to reach anything the customer did not choose to show.

The **inner** node dials out to the **outer** node and holds a tunnel
open. The inner side keeps a list of **offers**: named addresses the
tunnel will carry. The outer side sees the names of the offers, never
their addresses, and a destination there can point at an offer:
`via <tunnel>/<offer>`. The app bound to that destination calls it
exactly as it would call a direct one (`oaap.net.destinations` 2.3) —
**an app cannot tell a tunnelled destination from a direct one.**

The same tunnel serves a second consumer since 0.2: **a browser or a
third party on the internet**. An **exposure** (2.8) is one target behind
one random public name, for a limited time — what many people use ngrok
for. It is opened from the inner node's command line or from a laptop,
and it is behind the outer platform's login unless someone says
`--public`.

In SAP terms: the connector is the SAP Cloud Connector, the offer list
is its access-control list of "virtual hosts", and a `via` destination
is a BTP destination with proxy type `OnPremise`.

## 2. Interface

### 2.1 Two roles, one service

Every node runs the same connector service. What it does depends on
what the operator configured on that node:

- **Outer role** — the node has issued at least one connect key. It
  accepts tunnels and carries destination calls into them.
- **Inner role** — the node has at least one connector. It dials out,
  keeps the tunnel up, and answers the calls that arrive through it
  from its offer list.

One node MAY hold both roles. Neither role opens a listener on the
host: the outer role is reached through the gateway, and the inner
role has no listener at all.

### 2.2 The connect key (outer side)

- `oaap connect key issue <label> --tenant <t>` creates a key and
  shows it **once**. The node stores only its SHA-256 hash, with the
  label, the tenant and who issued it when. The label names the
  tunnel on this node (`[a-z0-9][a-z0-9-]{0,38}[a-z0-9]`, unique per
  node).
- **A key belongs to exactly one tenant** (RFC-0033 §7). A destination
  of another tenant cannot select its tunnel — refused when the
  destination is created, and checked again on every call.
- `oaap connect key revoke <label>` removes the key. A tunnel that is
  connected with it MUST be closed within 5 seconds. Revocation MUST
  always succeed, also while destinations still point at the tunnel —
  it is the emergency action. The answer names those destinations:
  they now fail with 502.
- Issue and revoke are written to the tenant's audit log.

### 2.3 The connector and its offers (inner side)

- `oaap connector add <label> --endpoint <url>` reads the key from a
  hidden prompt or from stdin (`--key-stdin`), never from an argument.
  The endpoint is the outer node's address. It MUST be `https://`;
  `http://` is accepted only with `--plain` and is marked as such on
  every surface (a LAN rehearsal, never the internet).
- The key is kept in a directory no container but the connector
  service mounts, and it is not in the backup (the posture of
  `oaap.net.destinations` 2.5). The connector object itself (endpoint,
  offers, paused) is in the backup.
- `oaap connector offer add <label> <offer> --to <url> [--path <prefix>]
  [--methods <M,M>]` adds an offer. `--to` is an `http://` or
  `https://` URL with an optional base path, no user info, no query,
  no fragment. `--path` narrows the calls to paths below a prefix,
  `--methods` to a set of HTTP methods.
- **An offer MUST NOT name the node's own platform services** other
  than its public front door: container and service names of the
  platform (identity, portal, store, twin, broker, relay, the
  connector) and the loopback address are refused; the gateway is
  allowed only on its public ports (80, 443). Offering the front door
  is what makes the live twin read possible (RFC-0033 §6): the call
  still needs a key the inner tenant issued (D10).
- `oaap connector offer remove <label> <offer>` cuts every destination
  that used the offer, immediately, without asking the outer side.
- `oaap connector pause <label>` closes the tunnel within 5 seconds and
  refuses to reconnect until `oaap connector resume <label>`. The outer
  side **cannot** establish, resume or widen a tunnel (RFC-0033 §2.3).
- Adding, removing, pausing and resuming connectors and offers are
  written to the audit log.

### 2.4 The tunnel

- The inner side opens a WebSocket to `<endpoint>/connect/tunnel` with
  `Authorization: Bearer <key>` and the subprotocol `oaap-connect.1`.
  It passes any HTTP proxy and needs no UDP and no kernel rights.
- The gateway's route `/connect/tunnel` — exactly this path — is public
  on every site of the outer node (no session, identity headers
  stripped, like the deploy hook) and leads to the connector service
  only. It survives gateway reloads like every other held stream. The
  service's other door (`/via`, 2.5) is not routed from the outside.
- An unknown or revoked key gets one indistinguishable answer (401).
  Five failures from one address within five minutes slow that
  address down to one attempt per minute.
- **One tunnel per key.** A new connection with the same key replaces
  the old one, so a connector that lost its network is not locked out
  by its own ghost.
- On connecting, the inner side sends its offers as **names and kinds**
  (`hello`), and sends them again whenever the list changes. Addresses,
  prefixes and methods never cross the tunnel.
- Reconnect after a failure with backoff: 1 s doubling to 60 s.

**Wire format (version 1).** Text frames carry JSON control messages;
binary frames carry bodies as `[1 byte type][4 bytes stream id, big
endian][payload]`, type `1` = data, type `2` = end of body.

| message | direction | fields |
| --- | --- | --- |
| `hello` | inner → outer | `connector`, `offers: [{name, kind}]`, `version: 1` |
| `offers` | inner → outer | `offers: [{name, kind}]` |
| `open` | outer → inner | `id`, `offer`, `method`, `path` (raw, with query), `headers`, `body` (whether one follows), `caller`, `destination` |
| `head` | inner → outer | `id`, `status`, `headers` |
| `error` | inner → outer | `id`, `status`, `reason` |
| `cancel` | either | `id` |

Many calls share one tunnel; bodies flow in chunks of at most 64 KiB in
both directions. A WebSocket upgrade *through* the tunnel is not part
of 0.1 and is answered 501.

### 2.5 A `via` destination (outer side)

`oaap.net.destinations` 2.1 gains the target `{via: "<tunnel>/<offer>"}`
(CLI: `--target via:<tunnel>/<offer>`). In 0.1:

- only for `kind: http` — a TCP offer needs a listener per destination
  on the outer node and is left for later;
- the tunnel MUST exist on this node and belong to the destination's
  tenant;
- the offer need not be announced yet (the inner side may be offline
  when the destination is created); a call to an offer the inner side
  does not offer is answered 404 with a sentence.

The gateway handles the call as for a `direct` target
(`oaap.net.destinations` 2.3: caller by network, identity headers
stripped, credential added) and forwards it to the connector service
with three headers of its own: a key only the gateway holds, the
calling instance, and the destination (`<tenant>/<name>`). The
connector service MUST refuse a call without the gateway's key (403),
and MUST refuse it when the destination's tenant is not the tunnel's —
with **exactly the answer a revoked tunnel gets** (502, one sentence),
so the answer says nothing about another tenant's tunnels. It removes
the three headers before the call enters the tunnel, and with them
every hop-by-hop header, `Expect` included: the gateway has already
answered an expectation, and passed on it makes the inner side wait for
a `100 Continue` from a backend that is waiting for the body.

### 2.6 The check before a stream opens (inner side)

For every `open`, against the **current** configuration, in this order:

1. the connector is not paused — otherwise the tunnel would not be up;
2. the offer is in the list — otherwise 404, "not offered";
3. the method is allowed — otherwise 405;
4. the path, after percent-decoding, contains no `.` or `..` segment
   and no backslash, and lies below the offer's prefix — otherwise 403;
5. only then is the backend called: offer base path + requested path,
   `Host` set to the backend's, hop-by-hop headers and `X-Forwarded-*`
   removed.

Backend unreachable → 502 with a sentence; no answer within 120 seconds
→ 504.

### 2.7 State and logs

- **State.** The service writes its state where the portal and the CLI
  read it: per tunnel (outer) whether it is connected, since when, from
  which address, and the offers it announced; per connector (inner)
  whether it is connected, paused, the last error and the next attempt.
- **Portal.** The inner node shows its connectors with their offers and
  state; the outer node shows its tunnels with their announced offers,
  and a `via` destination shows its tunnel's state.
- **Fleet status** (`oaap.fleet.status`): `connector_down` (inner, not
  paused and not connected) and `tunnel_down` (outer, a tunnel that a
  bound destination uses is not connected) on the `attention` list.
- **Stream logs.** Both sides write one line per call against their
  own object — the offer inside, the tunnel outside: time, offer,
  calling instance, destination, method, path without query, status,
  bytes each way, duration. Never a header value, never a body. Each
  log is capped (5 MB, one predecessor kept) and read with
  `oaap connector log <label>` and `oaap connect log <label>`.

### 2.8 Exposures — a random public name for one target (0.2)

The ngrok case (RFC-0033 §3). An **exposure** is one target, one random
public name, a time limit. It is not a destination (an app's private
path to a backend) and not an offer (a name on the tunnel's list): its
consumer is a **browser or a third party on the internet**.

```
   https://k3f9x2mh4a.t.oaap.joomp.de  ──▶  outer node  ──tunnel──▶  inner side  ──▶  http://192.168.178.20:3000
   (a random name under the node's zone)     login by default        the target lives ONLY here
```

**Two ways to open one, one protocol.**

- **On the inner node**, by `server_admin` (RFC-0033 D9), through a
  connector: `oaap connector expose <label> <url> [--ttl 8h] [--public]`.
  The target is any `http(s)` address that node can reach — a LAN
  laptop, a container, a device — except what §2.3 forbids for an offer
  (the node's own platform services, loopback).
- **From a laptop**, by a person, through the **client** (§2.8.5), with
  the person's own API key (RFC-0027, RFC-0033 D7). The target is
  whatever the person typed; it never leaves the laptop.

**2.8.1 The name.** `<name>.t.<external host>` — `<name>` is 10 random
characters from `[a-z0-9]` chosen by the OUTER node, never by the inner
side (a name someone else picked could be guessed, squatted or made to
look like a real one). The zone `t.<external host>` exists on a node
that has an external hostname (`oaap external set`); without one, an
`expose` is refused with a sentence that says so. Behind an edge
(RFC-0006) the same names are served over plain `http` and only the edge
is accepted, exactly as for every other generated site.

**2.8.2 Protocol** (wire version 1, additive to 2.4). The inner side
asks; the outer side answers; the target address is never sent.

| message | direction | fields |
| --- | --- | --- |
| `expose` | inner → outer | `ref` (chosen by the inner side, unique per tunnel, ≤ 40 characters), `ttl` (seconds), `public` (bool), `resume` (a name this `ref` was given before, optional) |
| `exposed` | outer → inner | `ref`, `name`, `host`, `url`, `expires` (UTC), `public` |
| `expose-refused` | outer → inner | `ref`, `reason` (a sentence) |
| `unexpose` | inner → outer | `ref` |
| `expired` | outer → inner | `ref`, `reason` (`ttl` / `closed` / `revoked`) |
| `open` | outer → inner | as 2.4, with `exposure` (the `ref`) in place of `offer` and `caller` = the visitor's user name, or `public` |

`resume` makes the name survive a reconnect: the inner side sends every
live `expose` again after it dials in, and the outer side hands back the
same name if it is still live, held by no other tunnel and not closed by
the operator. Otherwise it answers as for a new one.

**2.8.3 Rules the outer node applies**, in this order, before it answers
`exposed`:

1. the node has an external hostname (2.8.1);
2. the tunnel is allowed to expose (a connector key: yes; a person's key:
   §2.8.5);
3. `public` is allowed for this tunnel (a connector key: yes; a person:
   only with the role `tenant_admin`, RFC-0033 D6);
4. `ttl` is at most **7 days**, and at least 1 s; missing means **8
   hours** (RFC-0033 §3.3). The requester sends the time that is LEFT, so
   the minimum of a *request* — one minute — is the requester's rule
   (`oaap connector expose`, the client), not the outer node's: a request
   for one minute that waited a second for the connector to dial in
   arrives as 59 seconds and is honoured (found live, 2026-09-26). A `resume` carries the time that is LEFT; only
   an end **later** than the one the node holds is an **extension** (logged
   as one, counted from now, never past 7 days from now) — a client that
   merely reconnects never lengthens or shortens anything;
5. at most 10 live exposures per tunnel and 100 per node.

**2.8.4 What a visitor meets.**

- **Login by default** (RFC-0033 D6). The gateway asks the connector
  service who may pass; for a login exposure the service asks identity
  (`/verify`) with the tunnel's tenant: any signed-in user of that
  tenant passes, and `server_admin` always does (RFC-0022 D5). A
  visitor without a session is sent to `/auth/login` on the same name,
  which every generated site serves. The verified identity headers are
  handed to the target like to any app; the target may trust them, and
  nothing a client sent under those names reaches it.
- **`--public`** is the explicit choice: no login, the identity headers
  overwritten with empty values, and a brake in the service (RFC-0010's
  shape): 120 requests per 60 s per client address per exposure, then
  429 with `Retry-After`.
- **What only the platform may see does not go to the target.** The
  target is not a platform app, and a `tenant_admin` who exposes a laptop
  is not the operator. The node removes, before the call enters the
  tunnel: the platform's **session cookie** (`oaap_session`) from the
  `Cookie` header (every other cookie passes) — it is valid on the whole
  node, so a target that kept it could act as the visitor, and a
  `server_admin` who followed a link would hand it over — and an
  `Authorization: Bearer oaapk_…` header (a platform API key). In the
  other direction a `Set-Cookie` that sets the session cookie is dropped
  from the target's answer: a target cannot set the node's session.
- A name that is not a live exposure answers 404 with one sentence; a
  request carrying `Upgrade` answers 501 (a WebSocket through the tunnel
  is not part of 0.2).
- The inner side dials the target with `Host` set to the target's,
  hop-by-hop headers and `X-Forwarded-*` removed, a path with a `.` or
  `..` segment or a backslash refused (2.6 step 4), and 502/504 with a
  sentence as for an offer.

**2.8.5 The laptop client.** One file, `oaap-expose.py`, offered by the
node at `<endpoint>/connect/client` (a public, exact route on every
generated site), for Linux, macOS and Windows wherever Python 3.9+ and
`aiohttp` are. It speaks the same tunnel (2.4) with the person's API
key: `Authorization: Bearer oaapk_…` and `X-OAAP-Tenant: <tenant>` on
the WebSocket handshake.

```
OAAP_KEY=oaapk_… python oaap-expose.py http://localhost:3000 \
       --server https://oaap.joomp.de --tenant cls --ttl 4h
```

- The outer node asks identity (`/verify?tenant=<tenant>`) with that
  key. An unknown, revoked or expired key → 401 (the one indistinguishable
  answer of 2.4); a key of another tenant, or a principal without the role
  `tenant_admin` → 403 with a sentence. `server_admin` cannot be carried
  by a key at all (RFC-0027), so an operator uses the node command.
- A refusal comes with the node's own sentence: a WebSocket handshake
  error carries no body, so the client asks the same door once more the
  plain way and prints what it says.
- The key is asked again about every 60 s while the tunnel stands
  (RFC-0027: a revocation counts on the very next request, and a tunnel
  has none). A key that no longer holds — revoked, expired, or without
  `tenant_admin` — ends the tunnel **and every exposure its owner opened**,
  and the client ends with a sentence about the key. The key is held in
  the service's memory for the life of the tunnel and nowhere else.
- A person's tunnel **may expose and nothing else** (RFC-0033 D7): it has
  no offers, cannot be the target of a `via` destination, and its
  `hello` offers are ignored. Its label is generated by the outer node
  and never selectable. A person may hold 5 tunnels at once.
- The client keeps the exposure alive: it re-sends `expose` with
  `resume` after a reconnect, prints the URL and the expiry, and on
  Ctrl-C sends `unexpose`. The key comes from `OAAP_KEY` or a hidden
  prompt, never from an argument, so it does not show in a process list.

**2.8.6 It expires, and it is swept.** A sweep runs at least every 10 s.
Expiry removes the exposure from routing at once (the next request is a
404), tells the inner side (`expired`), and is logged. An exposure also
ends when its tunnel's key is revoked. A tunnel that is merely
disconnected keeps its exposures until their TTL, so a reconnecting
client gets its name back. `oaap connect exposure close <name>` is the
outer operator's action: it ends the exposure and keeps the name from
being resumed.

**2.8.7 Certificates (RFC-0033 D8).** The names get their certificates
**on demand**, at the first handshake, approved per name: the gateway
asks the portal, which approves exactly a live exposure's name under the
zone (and nothing else under it). No wildcard certificate, so no DNS
credential on the node. The service counts the names it opened in the
last 7 days, and `oaap connect exposures` says so next to Let's Encrypt's
limit of 50 certificates per registered domain per week; from 40 it
warns. An expired exposure's certificate is left to lapse; nothing
approves a renewal for it.

**2.8.8 Audit and logs.**

- The **tenant audit log** (RFC-0022 §6) gets one line for each decision
  of a person: `exposure.open`, `exposure.extend`, `exposure.close`,
  `exposure.expire`, with who (the person, or the connector's label),
  the host, `public` or `login`, and the expiry. The target address is
  **not** in it — the outer node never had it. An exposure opened by a
  `server_admin` lands in the tenant's log, like every operator action.
- **Stream logs** (2.7) gain one line per call against the exposure:
  time, name, visitor (`public` for a public one), method, path without
  query, status, bytes, duration. Never a header value or a body.

**2.8.9 State.** The service reports per exposure: name, host, tenant,
tunnel, `public`, opened, expires, who opened it, and calls served —
never the target. Per connector (inner): each `expose` it holds, with the
name and URL the outer node gave. The portal shows both.

## 3. Configuration

- `oaap connect key issue|revoke|list`, `oaap connect offers <label>`,
  `oaap connect log <label>` — outer.
- `oaap connector add|remove|list|show|pause|resume|log`,
  `oaap connector offer add|remove` — inner.
- Exposures (2.8): `oaap connector expose <label> <url> [--ttl] [--public]`,
  `oaap connector unexpose <label> <ref>`, `oaap connector extend <label>
  <ref> --ttl` — inner; `oaap connect exposures`,
  `oaap connect exposure close <name>` — outer.
- All of it is `server_admin`'s (RFC-0033 D3, D9). The portal shows, and
  does not change. The laptop client (2.8.5) is the one path of a person
  who is not `server_admin`, and it can do nothing but `expose`.

## 4. Security requirements

- **The offer list is inner-only and is the boundary.** The check is on
  the inner side, before the stream opens, against the current list.
  The outer node never learns an address.
- **A tunnel carries one tenant.** Checked at creation of a `via`
  destination and again for every call.
- **The connector has no listener.** A compromised inner node gains
  nothing it did not have; a compromised outer node gains the offers of
  its tunnels for as long as the inner side keeps them, and can neither
  add an offer nor resume a paused connector.
- **The outer route is reached only through the gateway's key.** The
  connector service is on the platform network; a caller without the
  gateway's key is refused before anything is looked up.
- **No payload is logged.** Payload trace (RFC-0021's outlook) is not
  part of 0.1 or 0.2.
- **The outer node chooses every public name.** Random, 10 characters,
  never proposed by the inner side; the target address never crosses the
  tunnel (2.8.1, 2.8.2).
- **An exposure is login-protected unless it says `--public`**, and a
  person's key may open a public one only with the role `tenant_admin`
  (2.8.3). A public exposure is braked and always expires.
- **A person's tunnel exposes and nothing else.** No offers, no `via`
  target, no selectable label (2.8.5).
- **Only a live exposure gets a certificate.** The on-demand approval
  names exactly the live names under the zone (2.8.7); no wildcard
  certificate and no DNS credential exist on the node.
- **Nothing a visitor sends passes as identity.** Identity headers are
  overwritten on every exposure, public ones with empty values (2.8.4).
- **Everything `oaap.net.destinations` §4 says holds unchanged**:
  caller by network, no credential in the container, a rehearsal has no
  binding.

## 5. Conformance tests (described)

1. A tunnel with an unknown key → 401; with a revoked key → the same
   401, and a connected tunnel with that key closes within 5 s.
2. A bound app calls a `via` destination and the backend receives the
   destination's credential, its own `Host`, path and query intact, and
   none of the gateway's three headers.
3. A call to an offer not in the list → 404; with a method not allowed
   → 405; with `/../` or `%2e%2e` escaping the prefix → 403 — and the
   backend receives nothing.
4. Removing an offer on the inner side: the next call → 404 without any
   change on the outer side.
5. `pause`: the tunnel closes; calls → 502; the connector does not
   reconnect until `resume`.
6. A `via` destination in tenant B naming a tunnel of tenant A is
   refused at creation; a forged call carrying tenant B's destination
   into tenant A's tunnel is refused by the connector service with the
   same answer as a revoked tunnel.
7. A call to the connector service's `/via/*` without the gateway's key
   → 403.
8. A second connection with the same key replaces the first.
9. An offer naming `portal`, `identity`, `localhost` or the gateway on
   8098 is refused; the gateway on 80 is accepted.
10. The outer node's state names the offers, never their addresses.
11. A request body sent with `Expect: 100-continue` arrives whole, and
    the backend never sees the `Expect` header.
12. A gateway reload that changes the configuration does not close a
    connected tunnel.
13. (Exposures) An `expose` gets a 10-character name under `t.<host>`
    chosen by the outer node; the outer node's state never contains the
    target address; an `expose` on a node without an external hostname is
    refused with a sentence.
14. A login exposure: a visitor without a session is sent to
    `/auth/login`; a user of the tunnel's tenant passes and the target
    receives the five identity headers, none of them as the visitor sent
    them; a user of another tenant gets 403; `server_admin` passes.
15. A public exposure: no login, the identity headers arrive empty even
    if the client forged them, the 121st request within 60 s from one
    address gets 429.
16. TTL: past its expiry the next request is 404 within 10 s and the
    inner side is told (`expired`); `resume` after a reconnect returns the
    same name; an extension is one audit line and never runs past 7 days.
17. A laptop key without the role `tenant_admin` → 403; a key of another
    tenant → 403; an unknown key → 401; a person's tunnel cannot be named
    in a `via` destination and ignores offers; 5 tunnels per person.
18. The certificate approval says yes for a live exposure's name and no
    for any other name under the zone, for the zone itself, and for a
    name that just expired.
19. `oaap connect exposure close <name>` ends it at once and the name
    cannot be resumed; revoking the connect key ends the exposures its
    tunnel held.
20. A request with `Upgrade` → 501; a path with `%2e%2e` → 403 and the
    target receives nothing.
21. The target never receives the session cookie or a `Bearer oaapk_…`
    header, receives every other cookie, and cannot set the session
    cookie in its answer.
22. A reconnect returns the same name and does not move the end; a later
    end is one `exposure.extend` line; a pause and a resume of the
    connector keep the name.
23. Revoking a laptop's key ends its tunnel and the exposures it opened
    within 65 s, and the client ends with a sentence about the key.

## 6. Dependencies

`oaap.net.destinations` (the object and the listener), `oaap.core.gateway`
(the `/connect/tunnel` and `/connect/client` routes and the exposure
zone), `oaap.core.identity` (`/verify` for visitors and for a laptop's
key), `oaap.core.portal` (the certificate approval), `oaap.core.tenant`
(ownership, audit log), `oaap.fleet.status` (attention items).

## 7. Maturity

Draft. **0.2 (exposures) built in the reference 0.1.131 on 2026-09-26.**
Two test files hold the rules of 2.8: one for the node's files (the zone
site and its order, the limits, the audit lines, the certificate
approval) and one with real processes — an outer service, an inner
service, the real laptop client, a backend and a stand-in for identity.

**Measured on `oaap-test` on 2026-09-26** (the node stood behind a probe
name in edge mode, so no certificate was requested): the real client, run
on a Windows laptop, opened an exposure through the LAN and got
`http://<10 chars>.t.probe.oaap.invalid/`; a visitor without a session
was sent to `/auth/login` on that very name, and after signing in as a
member of the tenant reached the **laptop's** server. The target saw the
member's identity headers, its own `Host`, its own cookies — and **not**
the node's session cookie, an API key, a forged `X-OAAP-User`, or any
header of the gateway or the tunnel; a `Set-Cookie: oaap_session=…` in its
answer was dropped. A user of another tenant got 403, `server_admin` and
a tenant member's API key passed. 1 MiB up, `%2e%2e` 403, a WebSocket 501,
an unknown name 404. A public exposure needed no login, a forged identity
never reached the target, and the 121st request within a minute from one
address got 429 with `Retry-After: 60` (another address 200). One minute
after opening, its next request was a 404 and the log said *expired*.
`oaap connect exposure close` ended one in 5 s; the laptop client
redialled by itself through two restarts of the service and kept its
name; revoking the laptop's API key ended tunnel and exposures 37 s later
and the client said why. The portal's health page lists the exposures.

**Five findings changed the code** (each is a test now, and the tests
that catch them were checked to fail without the fix):

1. `--ttl 60s` arrived as 59 s (a second of waiting for the connector) and
   the outer node refused it: the minimum of a request is the requester's
   rule, the outer node takes what is left (2.8.3 rule 4).
2. **Every change to `connect.json` closed every laptop** with "key
   revoked": reconcile judged all tunnels by the file of connect keys, and
   a person's key is not in it (2.8.5).
3. **An exposure the outer operator closed came back under a new name**
   after a reconnect or a restart of the inner side, because the inner
   side asked again. An end decided by the other side is now remembered
   and final, and a `resume` of a closed name is refused (2.8.6).
4. The number of calls in the state stayed 0.
5. `oaap connect exposures` printed `https://` for a zone that is `http`.

**The certificate on demand, measured on `oaapx01` (direct mode, real
public name `t.oaap.joomp.de`) on 2026-09-26, with Jörg's release.** The
node dialled itself (`--plain`, endpoint `http://gateway:80`) and opened
two exposures to a throwaway echo server bound to the platform bridge
only, ten and five minutes, then everything was torn down.
- **Login exposure:** the first handshake for the fresh name
  `ri39javp94.t.oaap.joomp.de` took **6.0 s**, the certificate was
  issued by **Let's Encrypt** for exactly that name, verified by the
  client (`ssl_verify_result` 0); the gateway log shows the real
  on-demand order with the `tls-alpn-01` challenge served to Let's
  Encrypt's validators. The answer was 303 to `/auth/login` **on the same
  name**. A second request needed **0.09 s** (cached).
- **`--public` exposure:** a second fresh name, a second certificate
  (6.4 s), and the request came through the real gateway, the tunnel and
  the connector to the target: 200 with the target's own content.
- **A name that is not an exposure** (`zzunknown99.t.…`): the handshake
  fails and the gateway log holds **no certificate order** for it — the
  portal's approval refuses it, as 2.8.7 requires.
- **After the unexposing** (both ways: 5 s wait) the counter read "no live
  exposures, 2 names in 7 days", and both names answered 404. Nothing was
  left on the node: no key, no connector, no process, no file, no `app_*`
  artefact; `HEALTHY` 4/4 and 20/20 throughout.
- **Not measured:** the 50-per-week limit itself (two of 50 were used),
  and the behaviour when Let's Encrypt refuses (a rate-limit answer).
A name **one level too deep**
(`a.<name>.t.<host>`) is not part of the zone site; on a node it falls to
whatever else answers that host, exactly as any unknown name does.

**0.1 was** built in the reference 0.1.129 and measured on 2026-09-25 between
two nodes of our fleet over the LAN (`oaap-test` outer, `oaap-demo`
inner, `--plain`), then with the roles reversed:

- the inner node dialled out, the outer node listed the offer **name**;
  a bound app's call arrived at the backend with the destination's
  credential, the backend's own `Host`, path and query intact
  (`%2F` included), and none of the forged `X-OAAP-*`,
  `X-Forwarded-For` or `Authorization` headers the app had sent;
  5 MiB down and 2 MiB up arrived whole;
- method 405, outside the prefix 403, `%2e%2e` 403, another app's
  network 403, removed offer 404, pause 502 (tunnel down after 1.1 s),
  revoke: tunnel down after 4 s and the inner side saying "refused the
  key (401)"; two gateway reloads did not move the tunnel's `since`;
- an app network cannot resolve the connector service at all; from the
  platform network `/via` without the gateway's key is 403.

The same afternoon, as RFC-0033 D4 names it: `oaap-demo` inner,
`oaapx01` outer, **over the internet with TLS** (`https://oaap.joomp.de`,
no `--plain`). The inner node dialled out from the home network's
public address; a test app on `oaapx01` got the backend's answer in
30 ms with the destination's credential and none of its forged headers,
5 MiB down in 1.3 s, 2 MiB up whole and without `Expect`; outside the
prefix 403, another app's network 403, pause 502. Nothing on `oaapx01`
changed in public: all nine public names answered as before.

**Two findings changed the code** (both now conformance tests): an
`Expect: 100-continue` passed through the tunnel stalled every upload
over 1 MiB for 120 s; and a revoked tunnel answered 403 while the CLI
promised 502.

**One finding is open — the live twin read (RFC-0033 §6, D10).** The
pipe carries it: the call from `oaap-demo` reached `oaap-test`'s
gateway through the tunnel, and identity accepted the machine key the
inner node had issued. The twin then refused: `'via-demo' is not a
registered instance`. The twin takes tenant and origin from the LOCAL
instance registry, and a reader on another node is not in it. RFC-0033
§6 expected "no extra work"; one rule is missing in `oaap.data.twin` —
how a remote reader is named and which tenant it reads. Jörg decided
it the same day; `oaap.data.twin` 0.4 §2.14 (reference 0.1.130) adds a
read-only remote reader, and the live read through the tunnel was
measured there.

Deliberately left for later, each named in RFC-0033: TCP through the
tunnel, re-encryption with the platform CA inside the tunnel, payload
trace, maintenance in the portal — and, for exposures, a WebSocket
through the tunnel (development servers with hot reload need it) and a
button in the portal.

## Deutsche Zusammenfassung

**Was das ist.** Stufe 2 von RFC-0033, das Gegenstück zum SAP Cloud
Connector. Der **innere** Knoten (beim Kunden, bei uns `oaap-demo`)
baut von sich aus einen Tunnel zum **äußeren** Knoten (im Internet,
`oaapx01`) auf. Er hält eine **Angebotsliste**: benannte Adressen, die
der Tunnel tragen darf. Der äußere Knoten sieht nur die **Namen** der
Angebote, nie die Adressen. Eine Destination dort kann auf ein Angebot
zeigen (`via x01/erp`). Die gebundene App ruft sie genauso wie eine
direkte Destination auf und kann den Unterschied nicht erkennen.

**Warum das sicher ist.**
- Beim Kunden wird kein Port geöffnet. Der innere Knoten wählt nach
  außen, wie ein Browser.
- Die Liste liegt innen. Wer innen ein Angebot entfernt, schneidet
  sofort jede Destination ab, die es nutzt, ohne außen fragen zu
  müssen. `pause` legt den Tunnel still, und außen kann ihn niemand
  wieder aufmachen.
- Ein Schlüssel gehört genau einem Mandanten. Eine Destination eines
  anderen Mandanten kann den Tunnel nicht benutzen. Das wird beim
  Anlegen und bei jedem Aufruf geprüft.
- Der Verbindungsdienst lässt `via`-Aufrufe nur mit einem Schlüssel
  herein, den allein das Gateway kennt. Eine App kann ihn also nicht
  direkt ansprechen.

**Was protokolliert wird.** Beide Seiten schreiben je Aufruf eine
Zeile: wer, welches Angebot, welcher Pfad (ohne Query), Status,
Bytes und Dauer. Nie Kopfzeilen oder Inhalte.

**Gemessen am 25.09.** zwischen `oaap-test` und `oaap-demo`, in beiden
Richtungen. Zwei Befunde haben den Code geändert:
- Ein durchgereichtes `Expect: 100-continue` hielt jeden Upload über
  1 MiB 120 Sekunden fest.
- Ein widerrufener Tunnel antwortete 403, versprochen war 502. Jetzt
  bekommen „widerrufen“ und „fremder Mandant“ dieselbe Antwort.

**Der Zwilling live.** Zuerst lehnte der Zwilling ab, weil er den
Mandanten aus der **lokalen** Instanzliste las. Jörg hat am selben Tag
entschieden: `oaap.data.twin` 0.4 kennt den **entfernten Leser**, nur
lesend und nur für die gegebenen Typen. Gemessen durch den Tunnel.

**Die Abweichungen vom RFC**, jeweils mit Grund:
1. **Nur HTTP in 0.1.** TCP durch den Tunnel bräuchte außen je
   Destination einen eigenen Port, das kommt später.
2. **Die Aufrufe landen außen im Stream-Protokoll des Tunnels, nicht
   im Prüfprotokoll des Mandanten.** Das Prüfprotokoll hält
   Entscheidungen von Menschen fest (Schlüssel ausgestellt, Angebot
   entfernt). Eine Zeile je HTTP-Aufruf würde sie darin ertränken.
3. **Pflege nur über die Kommandozeile.** Das Portal zeigt Tunnel,
   Angebote und Zustand, ändert aber noch nichts.

## Deutsche Zusammenfassung (0.2 — Freigaben)

**Was neu ist.** Über denselben Tunnel läuft jetzt ein zweiter Verbraucher:
ein **Browser im Internet**. Eine **Freigabe** ist ein Ziel hinter einem
zufälligen öffentlichen Namen, für begrenzte Zeit — das, wofür viele ngrok
benutzen. Sie lässt sich auf zwei Wegen öffnen: am **inneren Knoten** per
`oaap connector expose <label> <url>` (nur `server_admin`) oder vom
**Laptop** mit dem kleinen Client `oaap-expose.py` und dem eigenen
API-Schlüssel (nur ein `tenant_admin` des Mandanten).

**Was dabei gilt.**
- Den Namen wählt der **äußere** Knoten: `<10 Zeichen>.t.<Name des Knotens>`.
  Die Adresse des Ziels erfährt er nie; sie steht weder in seinem Zustand
  noch im Prüfprotokoll.
- Vorgabe ist die **Anmeldung** der Plattform, geprüft für den Mandanten des
  Tunnels (ein `server_admin` kommt immer durch). Nur mit `--public` gibt es
  keine Anmeldung — dann sind die Identitäts-Kopfzeilen leer, und pro
  Adresse werden höchstens 120 Aufrufe in 60 Sekunden angenommen.
- Eine Freigabe **läuft ab** (Vorgabe 8 Stunden, höchstens 7 Tage). Wer nur
  neu verbindet, verlängert nichts; ein späteres Ende gilt als Verlängerung
  und steht im Prüfprotokoll. Der Betreiber kann jede Freigabe schließen:
  `oaap connect exposure close <name>`.
- **Was nur die Plattform sehen darf, bekommt das Ziel nicht:** das
  Sitzungs-Cookie (es gilt auf dem ganzen Knoten — wer es behielte, wäre der
  Besucher, auch ein `server_admin`) und einen API-Schlüssel. Ein Ziel kann
  außerdem die Sitzung des Knotens nicht setzen.
- Der Laptop-Client darf **nur freigeben**, hat keine Angebote und ist kein
  Ziel einer `via`-Destination. Der Knoten fragt den Schlüssel etwa jede
  Minute erneut: Ein widerrufener Schlüssel beendet Tunnel und Freigaben.
- Zertifikate kommen **bei Bedarf** und nur für den Namen einer lebenden
  Freigabe. Es gibt kein Platzhalter-Zertifikat und keinen DNS-Schlüssel auf
  dem Knoten. Gezählt wird gegen die Grenze von Let's Encrypt (50 je
  Domain und Woche); ab 40 gibt es eine Warnung.

**Noch nicht drin:** WebSocket durch die Freigabe (Dev-Server mit Hot Reload
brauchen es; Antwort heute 501), TCP, und ein Knopf im Portal.
