# oaap.net.connector — The Inner Node Dials Out, the Outer Node Only Answers

- **ID:** `oaap.net.connector`
- **Version:** 0.1
- **Maturity:** draft (0.1 is RFC-0033 stage 2: connect keys on the
  outer node, the connector and its offer list on the inner node, the
  tunnel between them, `via` targets for HTTP destinations, pause and
  revocation, state on both sides, stream logs. Exposures (stage 3), a
  whole platform through the tunnel (stage 4) and rendezvous (stage 5)
  are the frontier, not specified)
- **Based on:** RFC-0033 (§2, §6, §7, D2, D3, D4, D10), RFC-0021 (the
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

## 3. Configuration

- `oaap connect key issue|revoke|list`, `oaap connect offers <label>`,
  `oaap connect log <label>` — outer.
- `oaap connector add|remove|list|show|pause|resume|log`,
  `oaap connector offer add|remove` — inner.
- All of it is `server_admin`'s (RFC-0033 D3). The portal shows, and
  does not change, in 0.1.

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
  part of 0.1.
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

## 6. Dependencies

`oaap.net.destinations` (the object and the listener), `oaap.core.gateway`
(the `/connect/tunnel` route), `oaap.core.tenant` (ownership, audit log),
`oaap.fleet.status` (attention items).

## 7. Maturity

Draft. Built in the reference 0.1.129 and measured on 2026-09-25 between
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
trace, maintenance in the portal.

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
