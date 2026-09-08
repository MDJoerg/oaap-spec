# RFC-0033: Destinations and the Connector — Reaching Inward Without Opening a Door

- **Status:** Accepted (2026-09-08) — D1, D2, D3 and D5 decided by Jörg
  in the design round; D4, D6, D8, D9 and D10 the same evening, each
  following the recommendation; **D7 decided differently**: node
  command and laptop client both ship in stage 3. Nothing is built.
- **Date:** 2026-09-08
- **Authors:** Jörg (the pattern, the direction, the ngrok wish), Claude
  (analysis & proposal)
- **Depends on:** RFC-0002 (gateway, default deny), RFC-0005 (platform
  CA), RFC-0006 (edge node — the inbound counterpart), RFC-0009
  (on-demand TLS under the node's own name), RFC-0011 (node profiles),
  RFC-0015 (declaration is not publication), RFC-0016 (app networks and
  app-to-app links — the shape a destination copies), RFC-0021 (the
  direction rule: the inner node connects outward), RFC-0022 (tenant as
  boundary — crossing it is an integration), RFC-0023 §2 (a data path
  through the fleet is not a control path), RFC-0027 (machine
  principals — the tunnel's credential), RFC-0029 (pull direction and
  its limit, D6), RFC-0030 D3 (a rehearsal reaches nothing outward),
  RFC-0031 (groups as the unit of ownership; the store and the copy)
- **Numbering note:** RFC-0032 is reserved for events, states and the
  unified namespace (RFC-0031 "followed by"). This document is
  therefore RFC-0033 although it was written first.
- **Driver:** Jörg, 2026-09-08: *„Ich würde gern so ein Konzept in die
  Plattform bringen, wie es SAP mit dem SAP Cloud Connector, den
  Connectivity Service und Destinations bietet. Dass wir von ‚innen'
  einen Tunnel zu einer Cloud- oder Edge-Komponente aufbauen und dort
  virtuelle Destinationen anbieten. Apps aus den äußeren Knoten
  bekommen so eine sichere Verbindung nach innen."* — and, the same
  afternoon: *„Ich benutze sehr oft die freie ngrok-Version für
  Testzwecke, um im Internet temporär einen Tunnel auf eine interne
  Ressource zu erstellen. […] Wenn wir das hier sicher mit einbauen
  können, wäre das super."*

## Summary

An app on a node with a public address needs to reach something that
has none: a customer's stock system behind their firewall, the twin on
the operator's inner node, a developer's laptop. Today the only way is
to open a door inward — a port forward, a VPN, a credential that points
at the inner network — and every one of those is exactly what the
fleet's direction rule forbids.

This RFC introduces three objects that together are the SAP Cloud
Connector pattern, cut to OAAP's shape:

- a **destination** — a named target an app is *bound to* by the
  operator, in the same form as an app-to-app link (RFC-0016): default
  none, declared per instance, recorded, revocable, never in the
  manifest as a grant. The app calls a local address; the platform adds
  authentication, TLS and transport. **The app never holds the
  credential** (D1);
- a **connector** — a service on an inner node that opens an
  **outbound** tunnel to an outer node and keeps the **offer list** of
  what the tunnel may reach. The offer list lives inside and only
  inside (D2). The outer node sees names, never addresses;
- an **exposure** — the ngrok case: a temporary, randomly named public
  route through the same tunnel, created from the inner side's command
  line, expiring by itself.

The rule that carries all three, in one sentence:

> **The inner side decides what is reachable; the outer side decides
> who may use it. Neither can widen the other's decision.**

## Motivation

### 1. The direction rule exists and has no data path for apps

RFC-0021 wrote it down for management, RFC-0029 for backups: *the
internal server connects outward; the external node needs no access
inward.* Both are pull or observe. RFC-0023 §2 then added the first
**data path** through the fleet — inference requests relayed from an AI
node — and drew the line that makes it safe: a data path changes
nothing on the receiving node, spends no right, installs nothing. The
prohibition is on **control** from outside, not on bytes.

An app on `oaapx01` that needs the inner twin, or a customer's app on a
hosted tenant that needs the customer's own ERP, is the same data path
with the direction reversed at the network level and unchanged at the
trust level: the inner side initiates, the outer side consumes.

### 2. Apps hold outbound credentials in plaintext, and the store said wait

CURRENT_STATE 179 measured it: `secret: true` config values are written
to the instance's environment file in the clear and travel with every
backup. The decision then was not to build a credential store until a
real case demanded one, because "the actual hurdle is that the keys are
fixed in the manifest" and no case had shown the shape. A destination
is that case and gives the shape: one target, maintained once, bound to
many instances, and for HTTP the app does not see the secret at all.

### 3. The rehearsal cut secrets because it could not cut destinations

RFC-0030 D3 says in so many words: *in SAP terms this is exactly why a
QAS system gets its RFC destinations cut* — and then had to approximate
it by not copying `secret: true` values. With destinations the
approximation becomes the thing itself: **a rehearsal has no
destination bindings.** A copy of production that cannot reach
production's targets cannot act on anyone.

### 4. Two scenarios are now real, not hypothetical

- **The customer brings their backend.** ADR-0006 scenario 3, the SAP
  case word for word: a customer's tenant on `oaapx01`, a small OAAP
  node with a connector installed at the customer's site, and their
  apps on the hosted tenant reach their warehouse system or file server
  through it. Jörg (2026-09-08): realistic.
- **The twin wanders.** The CRM and its twin (RFC-0031) live on the
  inner node; an app on the outer node reads the same objects. Jörg:
  realistic and interesting — with the open thought whether this is a
  tunnel, a replica, or both. §6 answers that.

### 5. The ngrok habit

Jörg opens ngrok tunnels several times a week: a random public hostname
with a real certificate, from the command line, onto a port that exists
only on his LAN, gone when he closes the terminal. Every piece of that
is either already in the platform (a public node with a wildcard zone,
on-demand TLS, throttled public routes, expiring instances with a sweep)
or is the tunnel this RFC introduces anyway. It costs one command.

## Vocabulary — SAP to OAAP

| SAP | OAAP | Already exists as |
| --- | --- | --- |
| Cloud Connector | **connector**, a service on an inner node | node type 5 in the idea store (2026-08-05) |
| Connectivity Service | **connect endpoint** on the outer node's gateway | machine credentials on a gateway route (RFC-0027) |
| Destination | **destination**, a named target per tenant | app-to-app links (RFC-0016), across nodes |
| Access Control (virtual host → internal host, paths) | **offer list**, maintained on the inner side only | "the platform stays yours" (RFC-0006) |
| Subaccount ↔ Location ID | a tunnel belongs to exactly one tenant or account on the outer node | RFC-0022 |
| Destination Service lookup API | *not built* (D1) — see §1.4 | — |
| — (ngrok) | **exposure**, an expiring public route through the tunnel | RFC-0009 on-demand TLS, RFC-0010 throttling, RFC-0030 sweep |

Two words are deliberately not "tunnel": the tunnel is transport, the
objects people configure are destinations, offers and exposures. Nobody
binds an app to a tunnel.

## 1. Destinations

### 1.1 The object

A destination lives on the node whose apps use it — the **outer** node
in the connector case, but a destination needs no connector at all
(stage 1). It belongs to exactly one tenant (RFC-0022) and is
maintained by that tenant's `tenant_admin` or a `server_admin`.

```json
{ "name": "erp",                       // unique per tenant
  "kind": "http",                      // http | tcp
  "target": { "direct": "https://erp.example.com/api/" },
  "auth":   { "type": "basic", "user": "oaap", "secret_ref": "…" },
  "tenant": "<uuid>",
  "created_by": "meier_admin", "created": "…",
  "bindings": ["orders", "raci"] }     // instances, maintained by grants
```

`target` is either `direct` (an address the node can reach on its own —
the internet, or the node's LAN) or `via` (an offer of a connector,
§2). `auth` is what the platform adds on the app's behalf: none, basic,
bearer, a named header; OAuth client credentials later, when a target
demands it. Secrets are stored the way deploy tokens are (hashed where
possible; where the secret must be presented in the clear, encrypted at
rest with the node key — this is the credential store CURRENT_STATE 179
deferred, and it is small because the platform is the only reader).

### 1.2 Binding is a grant, declaring is a need

Copied from RFC-0016 links and RFC-0015 endpoints:

- **Default: no destination.** Isolation is the resting state.
- A `tenant_admin` binds an instance to a destination in the portal or
  with `oaap app destination bind <instance> <destination> [--as NAME]`.
  The binding is recorded in the registry, survives redeploy like
  visibility and address do, is shown on both object pages, and is
  revocable.
- The **manifest may declare a need**: `destinations: [{name: erp,
  kind: http, purpose: "order lookup"}]`. Declaration is not binding —
  the install dialog shows the need and the operator chooses which
  destination satisfies it, or leaves it unbound and the app must cope.
  The app's word (`erp`) and the tenant's object (`meier-erp-prod`) are
  mapped by `--as`, the same move RFC-0031 makes for type names.

### 1.3 How the app reaches it — HTTP: proxy, never the credential (D1)

For `kind: http` the platform sets, per binding, one environment
variable:

```
OAAP_DESTINATION_ERP_URL=http://oaap-gateway.<instance-net>/destinations/erp/
```

The address is the gateway's listener on the instance's own private
network (RFC-0016 gives every instance one, and the gateway is a
member). The gateway knows which instance is calling from the network
the request arrived on — there is nobody else on it — looks up that
instance's bindings, rejects anything unbound, adds the destination's
authentication, and forwards: for `direct` to the target, for `via`
into the tunnel. The app sees a plain HTTP endpoint and no secret.

This is the platform's first contract guarantee, mirrored: *an app
never builds a login* on the way in, and **an app never holds a
credential** on the way out.

### 1.4 Non-HTTP: handover, said out loud

Postgres (RFC-0031), MQTT, SMB (`oaap.data.files`), SMTP: none of them
pass through an HTTP proxy. For `kind: tcp` the platform **hands the
values over** through the mechanism that already exists — instance
configuration. The manifest names the fields the app reads:

```yaml
destinations:
  - name: mail
    kind: tcp
    env: { host: SMTP_HOST, port: SMTP_PORT, user: SMTP_USER, password: SMTP_PASSWORD }
```

and the binding fills them from the destination. For `via` targets the
gateway additionally opens a local TCP listener on the instance network
that forwards through the tunnel, so `host`/`port` still point at the
platform; only the credential travels into the container. The
destination's object page states that it runs in **handover mode**, so
nobody believes the proxy guarantee where it does not hold.

Not built: a REST lookup API in the SAP sense. Its uses — protocol
libraries that cannot proxy, and **principal propagation** (the logged-
in person arriving at the backend as themselves) — are named as the
retrofit case. Jörg (2026-09-08): *„Da warten wir aber auf echte
Usecases."* Nothing here forecloses it; a lookup API would be a third
delivery mode next to proxy and handover, not a redesign.

### 1.5 The rehearsal has none

RFC-0030 D3, extended by one line: **destination bindings are not
carried into a rehearsal.** The environment variables come up unset,
the proxy path answers 403 with the reason. An operator may bind a
destination to a rehearsal by hand; that action is logged in the
tenant's audit log like every other rehearsal exception. This replaces
nothing in RFC-0030 — secrets are still not copied — it just makes the
QAS sentence there literal.

## 2. The connector and the tunnel

### 2.1 Two sides, two keys' worth of trust

```
   inner node (oaap-demo, customer site)          outer node (oaapx01)
   ┌──────────────────────────────┐              ┌──────────────────────────┐
   │ connector "x01"              │  outbound    │ gateway  /connect/…      │
   │   offers:                    │ ───TLS────▶  │   tunnels: x01 (tenant A)│
   │     erp  → 10.10.10.5:8080   │   (WS, mux)  │   offers seen: erp, twin │
   │     twin → twin.oaap.internal│              │ destinations (tenant A): │
   │   key: <issued by oaapx01>   │              │   erp  = via x01/erp     │
   │   state: connected 3d 2h     │              │   apps bound: orders     │
   └──────────────────────────────┘              └──────────────────────────┘
```

- The **outer** node issues the tunnel's credential:
  `oaap connect key issue <label> --tenant <t>` — a machine principal
  (RFC-0027, `kind: connector`), hashed at rest, shown once, revocable
  by label. **The key is bound to one tenant** (or, on a management
  node, one account). That is the Location-ID line: one connector may
  serve several outer tenants, but each tunnel serves exactly one.
- The **inner** node holds the key: `oaap connector add <label>
  --endpoint https://oaapx01.example --key …`. The connector is a
  **node service**, maintained by `server_admin` (D3), not a tenant
  object — it belongs to the machine it runs on and its offers point
  into that machine's network.
- The tunnel is **outbound TLS from the inner node to a gateway route
  on the outer node**, WebSocket-carried and multiplexed, so it passes
  any corporate proxy, needs no UDP and no kernel rights, and is
  terminated by the same Caddy that terminates everything else.
  Re-encryption with the platform CA (RFC-0005) inside the tunnel is an
  option for later, as RFC-0006 said for the edge hop. WireGuard stays
  what it is: `oaap.net.remote-access`, **people into a network**; the
  connector is **apps to backends**. The two are not merged (D3).
- Reconnect with backoff; the state is on both portals (connector card
  inside, tunnel row on the destinations page outside) and in the fleet
  status document as an `attention` item when a tunnel is down.

### 2.2 The offer list lives inside (D2)

```
oaap connector offer add x01 erp  --to http://10.10.10.5:8080 --path /api/ --methods GET,POST
oaap connector offer add x01 twin --to https://twin.oaap.internal/ --tenant meier
oaap connector offer remove x01 erp
```

An offer names an inner address, optionally narrowed by path prefix
and method, and is the **only** thing the tunnel will carry. The outer
node learns offer **names and kinds** when the tunnel connects
(`oaap connect offers <tunnel>`), never addresses. A destination
`via x01/erp` on the outer node can therefore point only at what the
inner side has chosen to show, and an inner operator who removes an
offer has cut every destination that used it, immediately, without
asking anyone.

This is the SAP Cloud Connector's central property and the reason the
pattern is trusted by security teams: the machine that would be
damaged holds the list.

### 2.3 The off switch is inside

RFC-0006 Q3 recorded "pulling the virtual cable" as a capability the
platform wants. The connector is its second use: `oaap connector pause
<label>` drops the tunnel and refuses to reconnect until resumed. The
outer node can revoke the key, which achieves the same from its side —
but it **cannot** establish, resume or widen a tunnel. A compromised
outer node holds, at most, the destinations its tenants were granted.

### 2.4 What the connector records

Metadata always: every stream opened, with offer, calling instance (as
reported by the outer gateway), time, bytes, result — in the connector's
log on the inner node, where the owner of the backend can read it.
Payload trace is the option RFC-0021's outlook already defined:
switchable by the owner, announced, time-boxed, itself audited. The
outer node logs the same stream against the destination in the
tenant's audit log, so both parties can answer "who reached what"
without trusting the other's log.

## 3. Exposures — the ngrok case

### 3.1 One command

```
oaap connector expose x01 http://192.168.178.20:3000 --ttl 8h
→ https://k3f9x2.t.oaap.joomp.de   (expires 2026-09-09 02:14, login required)
```

The inner node asks the outer node, over the existing tunnel, for a
public name; the outer node assigns a random label under its exposure
zone (`<random>.t.<node zone>`), obtains the certificate on demand — the
policy RFC-0009 already has for anything under the node's own name —
and serves the route through the tunnel to the target the inner node
named. The target is any address the inner node can reach: a LAN
laptop, a container, a device. The name is printed once and listed on
both portals under the connector until it expires.

### 3.2 Safe by default, public by choice (D6)

An exposure is a route on the outer gateway, so RFC-0002 applies to it
like to any other route: **by default it sits behind the outer
platform's login**, and the tenant the tunnel belongs to decides who
may open it — which for Jörg's own case means "me, logged in". The
ngrok use that needs no login (a webhook from a third party, a customer
looking at a prototype) is `--public`: an unauthenticated route,
throttled by RFC-0010, and still expiring. The default is the safe one
because the command will be typed quickly and often.

### 3.3 It expires, and it is swept

`--ttl` is mandatory with a default (proposal: 8 hours, maximum 7
days); extension is a command and is logged; the same sweep RFC-0030
built for rehearsals removes the route, the name and the certificate
registration. An exposure that outlives the work it was made for is the
failure mode ngrok's free tier avoids by killing the process, and we do
not have a process to kill.

### 3.4 Difference to a destination

| | destination | exposure |
| --- | --- | --- |
| who consumes | an app on the outer node | a browser or a third party on the internet |
| who configures | outer `tenant_admin` binds; inner `server_admin` offers | inner `server_admin`, one command |
| name | tenant-private, never public | public, random, expiring |
| lifetime | until revoked | TTL |
| authentication | added by the platform toward the target | required by the outer gateway from the visitor, unless `--public` |

Same tunnel, opposite consumer. Exposures are stage 3 because they are
the cheapest complete slice through the tunnel after destinations
themselves — one target, one name, no behind-edge mode.

### 3.5 Where the command runs (D7)

ngrok runs on the laptop. `expose` exists in **two places, both in
stage 3** (Jörg's decision):

- **on the inner node**, targeting any address that node can reach — a
  LAN laptop at home, an engineer's machine at the customer's site —
  through the node's connector and its connect key;
- **on a laptop**, as a small client speaking the same tunnel protocol
  to the same connect endpoint, authenticated with a **person's API key**
  (RFC-0027 `key` method, tenant-bound) instead of a connector key.

The outer node treats both alike: a tunnel bound to a tenant, an
exposure with a TTL under it. What the laptop client does not get is an
offer list or destinations — it may expose, nothing else; the
connector's wider powers stay on a node an operator administers. The
client is a second build artefact (Linux, macOS, Windows), and that
cost is taken knowingly for the case the node command cannot cover:
Jörg working outside his own LAN.

### 3.6 Certificates for random names (D8)

On-demand TLS works today and needs no new right on the machine. Two
limits are known and are stated rather than discovered: Let's Encrypt
issues at most 50 certificates per registered domain per week, and each
name lands in Certificate Transparency — harmless for a random label,
but the count is real. When exposures become frequent, the answer is a
wildcard `*.t.<zone>`, and that reopens the ADR CURRENT_STATE 84
deferred (DNS-01 needs a standing API right on the DNS zone). The
platform counts issued exposure certificates and says so on the
destinations page before the limit says it.

## 4. A whole platform through the tunnel (stage 4)

RFC-0006 solved "two platforms, one port pair" with an edge node in the
same LAN and a port forward on the router. With a connector the edge
can sit on the outer node and the inner platform needs **no port
forward and no DynDNS at all**: the offer is a hostname subtree
(`*.oaap-bernd.example`), the outer gateway terminates TLS for it as
RFC-0006 defines, and the inner platform runs in behind-edge mode
exactly as there. Everything RFC-0006 said about plaintext at the edge
and the agreement between owners applies unchanged. This is the
Cloudflare-Tunnel pattern, and it removes the failure that started
RFC-0006 — a public name silently pointing at a stale address.

## 5. Rendezvous between two inner sites (stage 5)

Two inner nodes behind two firewalls each hold a tunnel to the same
outer node and the same account. A destination on inner A `via` an
offer of inner B is routed **through** the outer node; the outer node
is relay and trust anchor, and sees the traffic unless the platform CA
re-encrypts inside the tunnel (the option from §2.1 becomes the
requirement here). This is the case RFC-0029 D6 could only name: the
push from Bernd's workshop to a backup target that cannot reach in.

## 6. The twin across the tunnel — how the thoughts merge

Jörg's question (2026-09-08): an app on the outer node uses central
twins — through the tunnel, or through synchronisation and a cache, or
must these ideas merge? They merge at one point and stay apart
everywhere else:

**The destination is the pipe. What flows through it, and how a copy
is marked, belongs to RFC-0031 and RFC-0032.**

- **Live read (stage 2, no extra work).** The inner connector offers
  the tenant's twin API (`oaap.data.twin`, RFC-0031 §6); the outer
  tenant binds its app to `via x01/twin`. The app speaks the twin API
  as it would locally. One thing must be said: RFC-0031 §8 takes the
  caller's tenant and origin **from its credential**, and over a
  destination the caller is the outer instance. The destination
  therefore carries a key the inner tenant issued to that outer
  instance as a machine principal (RFC-0027) — the same "a right is
  given, not held" pattern — so the inner twin sees a named origin,
  not "the tunnel". This is also the exact spot where principal
  propagation would later attach.
- **Replica (with `oaap.events.queue`).** The seven-capability cut of
  2026-09-08 already contains the piece: guaranteed delivery between
  physical nodes. A queue offer through the same tunnel ships group
  changes into a **read-only replica** schema on the outer node. The
  replica's groups keep their origin; RFC-0031's provenance makes the
  copy honest by construction — the outer store never becomes owner of
  anything it did not create, and a merge stays a person's action on
  the owning side. Apps on the outer node keep reading the replica
  when the tunnel is down, which is RFC-0003's degraded operation
  applied to data.
- **Not a cache.** A cache has no owner and no time; the twin has
  both. Whatever the outer node holds is a replica with a recorded
  "as of", visible in the twin browser as such.

So: live read is what this RFC delivers; replication is a queue feature
that uses this RFC's pipe; nothing else is merged.

## 7. Security requirements

- **The offer list is inner-only and is the boundary.** The outer node
  can never address anything not offered; the check is on the inner
  side, before the stream opens, against the current list.
- **A tunnel carries one tenant.** Its key is bound to that tenant on
  the outer node; a destination in another tenant cannot select it.
  RFC-0022's sentence holds across nodes: inside a tenant things may
  find each other, across tenants only what someone declared.
- **No credential leaves the platform for HTTP.** The app never sees a
  destination secret; the proxy is the only reader. Handover mode is
  visible on the object page, per destination.
- **A compromised outer node** gains: the destinations of its tenants,
  for as long as the inner side keeps the offers up. It cannot add
  offers, resume a paused tunnel, or read the inner offer list beyond
  names. Revocation and pause are both single actions.
- **A compromised inner node** gains what it had anyway — it is the
  machine the backends live on. The connector adds no inbound door: it
  has no listener, it dials out.
- **Exposures are login-protected by default** and expire. A `--public`
  exposure is throttled and appears on the outer portal with its
  remaining time, in the list an operator looks at.
- **Both sides log every stream** against their own object (offer
  inside, destination outside), metadata always; payload trace is
  explicit, announced and time-boxed.
- **The rehearsal has no bindings.** Stated in §1.5, repeated here
  because it is the reason the rest is safe to build.

## 8. Non-goals (deliberate)

- **No VPN for people.** `oaap.net.remote-access` (WireGuard) remains
  the way a person reaches a network; the connector never carries
  arbitrary traffic.
- **No mesh, no discovery.** A connector dials the endpoints it is
  told; nothing announces itself.
- **No load balancing, no failover across tunnels.**
- **No lookup API, no principal propagation** (D1) — named as the
  retrofit case, waiting for a real use.
- **No offers or destinations from a laptop client** — it exposes,
  nothing more (D7).
- **No change to app manifests beyond a declared need.** An app must
  not know whether a destination is direct or tunnelled; if it does,
  the boundary is in the wrong place.

## 9. Staging

1. **Destinations without a tunnel.** The object, tenant-scoped; `direct`
   targets; bindings as grants; the HTTP proxy path and the TCP
   handover; no bindings in a rehearsal. Testable on one node.
2. **Connector and tunnel.** Connect keys on the outer node, the
   connector service and offer list on the inner node, `via` targets,
   state on both portals and in the fleet document, pause/resume,
   stream logs. Live twin read falls out of this stage.
3. **Exposures.** `expose` from the inner node **and** from the laptop
   client (D7), random names, on-demand TLS, login by default, TTL and
   sweep.
4. **A whole platform through the tunnel** (edge over connector,
   RFC-0006 behind-edge mode).
5. **Rendezvous** between inner sites, with re-encryption inside the
   tunnel.

Stage 1 is small enough to sit between RFC-0031's build steps; Jörg
(D5) agreed. Stage 2 is built against the twin case on our own fleet
(D4); stage 3 follows it.

## Decisions

Decided by Jörg on 2026-09-08 in the design round:

- **D1 — HTTP: proxy only; non-HTTP: handover through instance
  configuration; no lookup API.** Accepted as recommended, with the
  note that the mechanism may be retrofitted — principal propagation
  named as the case — *"da warten wir aber auf echte Usecases."*
- **D2 — The offer list lives only on the inner side; the outer node
  sees offer names and kinds.** Accepted as recommended.
- **D3 — The connector is a `server_admin` node service holding several
  tunnels to several outer nodes; each tunnel belongs to exactly one
  tenant there. WireGuard stays separate.** Accepted as recommended.
- **D5 — Stage 1 may run between RFC-0031's steps.** Accepted.

Decided by Jörg the same evening, second round:

- **D4 — The first real case is *the twin wanders*.** GPU node and
  internal Forgejo are out; *the customer brings their backend* stays
  the product goal and gets the same code plus an installer path. Stage
  2 is built and rehearsed on our own fleet: `oaap-demo` inner,
  `oaapx01` outer, no customer involved. Accepted as recommended.
- **D6 — Exposures are login-protected by default; `--public` is the
  explicit choice.** Accepted as recommended.
- **D7 — Both: the node command and a laptop client ship together in
  stage 3.** Decided *against* the recommendation (node first, laptop
  later). Jörg works outside his LAN often enough that the node command
  alone would not replace ngrok for him. Consequence in §3.5: a second
  build artefact, and the laptop client may expose but holds no offers
  and no destinations.
- **D8 — On-demand certificates first, counted; the wildcard ADR
  reopens when the count says so.** Accepted as recommended, after the
  price of the alternative was spelled out: a wildcard needs a standing
  DNS-API token on `oaapx01`, which at most providers covers the whole
  zone — whoever takes the node could then redirect everything under
  `joomp.de`. If the ADR returns, the mitigation to design is a
  delegated throw-away zone (`t.oaap.joomp.de`) at a provider with
  per-zone tokens.
- **D9 — The right to `expose` on a node is `server_admin` of that
  node.** Accepted as recommended; a narrower right is cut when someone
  other than the operator needs one. (The laptop client's right is the
  person's own API key, D7.)
- **D10 — The live twin read authenticates with a machine key the
  inner tenant issues to the outer instance (RFC-0027), carried by the
  destination.** Accepted as recommended: RFC-0031 §8 stays literally
  true, and this is where principal propagation would attach.

## Deutsche Zusammenfassung

**Worum es geht.** Eine App auf einem Knoten mit öffentlicher Adresse
muss etwas erreichen, das keine hat: die Warenwirtschaft eines Kunden
hinter dessen Firewall, den Zwilling auf unserem inneren Knoten, den
Laptop eines Entwicklers. Heute ginge das nur mit einer Tür nach innen
— Portfreigabe, VPN, ein Zugangsdatum, das ins innere Netz zeigt —,
und genau das verbietet die Richtungsregel der Flotte (RFC-0021,
RFC-0029: innen verbindet nach außen, außen hat keinen Zugang nach
innen).

**Drei Objekte, nach dem Vorbild SAP Cloud Connector:**

- **Destination** — ein benanntes Ziel, an das der Betreiber eine App
  *bindet*, in derselben Form wie eine App-Verknüpfung (RFC-0016):
  standardmäßig keine, je Instanz erklärt, gespeichert, widerrufbar,
  nie im Manifest als Recht. Die App ruft eine lokale Adresse, die
  Plattform ergänzt Anmeldung, TLS und Transport. **Die App hält nie
  das Geheimnis** (D1). Für Nicht-HTTP (Postgres, MQTT, SMB, SMTP) wird
  der Wert über die vorhandene Instanzkonfiguration **übergeben**, und
  die Objektseite sagt das. Keine Lookup-API — Principal Propagation
  ist der benannte Nachrüstfall, wir warten auf echte Anwendungen.
- **Connector** — ein Dienst auf einem inneren Knoten, der einen
  **ausgehenden** Tunnel zu einem äußeren Knoten aufbaut und die
  **Angebotsliste** führt: was der Tunnel erreichen darf. Die Liste
  lebt nur innen (D2); außen sieht man Namen, keine Adressen. Der
  Connector ist Knotendienst des `server_admin`, hält mehrere Tunnel zu
  mehreren äußeren Knoten, jeder Tunnel gehört dort genau einem
  Mandanten (D3). WireGuard bleibt getrennt: Menschen ins Netz, der
  Connector bringt Apps zu Backends. Der Aus-Schalter liegt innen
  („virtuelles Kabel ziehen", RFC-0006).
- **Exposure** — der ngrok-Fall: ein Kommando auf dem inneren Knoten,
  ein zufälliger öffentlicher Name mit echtem Zertifikat durch
  denselben Tunnel, **standardmäßig hinter der Anmeldung** des äußeren
  Knotens, `--public` als ausdrückliche Wahl, mit Ablaufzeit und
  Aufräumen wie bei der Generalprobe. Erste Fassung läuft auf dem
  inneren Knoten und erreicht jede LAN-Adresse; ein Laptop-Client kommt
  später.

**Der Satz, der alles trägt:** Die innere Seite entscheidet, was
erreichbar ist; die äußere Seite entscheidet, wer es nutzen darf.
Keine kann die Entscheidung der anderen ausweiten.

**Was es mit Bestehendem macht.** Die Generalprobe (RFC-0030) bekommt
ihre Destinationen wörtlich gekappt statt behelfsmäßig über fehlende
Geheimnisse. Die Zugangsdaten-Frage aus Stand 179 hat ihren echten
Fall. Der Edge-Knoten (RFC-0006) kann in Stufe 4 außen stehen, ohne
Portfreigabe und ohne DynDNS bei Bernd. Das Backup-Push aus RFC-0029 D6
wird in Stufe 5 zum Rendezvous zweier innerer Standorte.

**Zwilling durch den Tunnel.** Die Destination ist das Rohr; was
hindurchfließt und wie eine Kopie gekennzeichnet ist, gehört zu
RFC-0031/0032. **Lesen live** fällt aus Stufe 2 heraus: Der Connector
bietet die Zwillings-API an, die äußere App spricht sie wie lokal, und
authentifiziert sich mit einem Schlüssel, den der innere Mandant ihr
ausgestellt hat (D10). **Replik** kommt mit `oaap.events.queue`: eine
Warteschlange durch dasselbe Rohr füllt ein nur lesbares Schema außen;
die Herkunft der Gruppen bleibt, der äußere Knoten wird nie Besitzer,
und die Apps lesen weiter, wenn der Tunnel weg ist. Kein Cache: ein
Cache hat keinen Besitzer und keine Zeit, der Zwilling beides.

**Staffelung:** (1) Destinationen ohne Tunnel — klein, passt zwischen
die Bauschritte von RFC-0031 (D5: ja); (2) Connector und Tunnel, damit
Zwilling-Lesen live; (3) Exposures; (4) ganze Plattform durch den
Tunnel; (5) Rendezvous.

**Alle zehn Entscheidungen stehen (Jörg, 08.09. Abend).** Der erste
Fall ist *der Zwilling wandert* (D4), geprobt auf der eigenen Flotte:
`oaap-demo` innen, `oaapx01` außen; der Kundenfall bleibt Produktziel.
Exposures liegen als Vorgabe hinter der Anmeldung, `--public` ist die
Wahl (D6). **Abweichend von der Empfehlung (D7):** Knoten-Kommando
**und** Laptop-Client kommen zusammen in Stufe 3, weil Jörg oft außerhalb
seines LAN arbeitet; der Laptop-Client darf nur veröffentlichen, keine
Angebote, keine Destinationen. Zertifikate zunächst on demand mit Zähler
(D8) — der Preis der Wildcard-Alternative ist benannt: ein dauerhaftes
DNS-API-Token auf `oaapx01`, das bei den meisten Anbietern die ganze
Zone `joomp.de` beschreiben kann; falls das ADR wiederkommt, ist die
delegierte Wegwerf-Zone die zu entwerfende Milderung. `expose`-Recht
beim `server_admin` des Knotens (D9). Zwillings-Lesen live mit einem
Maschinenschlüssel, den der innere Mandant der äußeren Instanz ausstellt
(D10).

**Nummerierung:** RFC-0032 ist für Ereignisse und Unified Namespace
reserviert; dieses Dokument ist deshalb RFC-0033, obwohl es zuerst
geschrieben wurde.
