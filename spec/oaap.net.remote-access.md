# oaap.net.remote-access — A Person Inside One Instance Network, For a While

- **ID:** `oaap.net.remote-access`
- **Version:** 0.4
- **Maturity:** draft (0.1: the access object, its lifecycle, the
  tenant audit trail and the portal card — no traffic yet. 0.2: the
  port forward of §4 — a `forward` access carries real bytes. 0.3
  added the mechanics of §5's WireGuard peer, CLI-only, and a
  real-node measurement on 2026-09-27 found the design as specified
  (one node-wide `wg0`, reached by routing) does not work against a
  current Docker daemon (29.7.1) — see §5.1a. **0.4 redesigns §5
  around that finding — each instance gets its own namespace, with
  the peer arriving as a genuine Docker bridge port instead of being
  routed in — and a SECOND real-node measurement on 2026-09-27
  confirms this design carries real traffic end to end AND correctly
  excludes the gateway, through the built code itself, not by hand.**
  Two more defects surfaced and were fixed by that same measurement
  before it passed — see §5.1b. Shape `wireguard` is still CLI-only
  (§9): a working fence is not, by itself, a decision to offer this
  from the portal. §4's port forward was unaffected throughout: it
  does not route into a bridge, it dials into one via `docker network
  connect`, which none of this restricts.)
- **Based on:** RFC-0044 (the object, D1–D10, §4 the port forward, §5
  the WireGuard peer), RFC-0038 (the diagnosis window and its sweep —
  the pattern this capability's lifecycle copies exactly, D2 there),
  RFC-0022 / `oaap.core.tenant` (the tenant audit log, an access
  belongs to exactly one tenant), RFC-0027 (API keys — the holder's
  own key is the forward's only credential), RFC-0016 (instance
  networks — what an access reaches, and how it is named), RFC-0011
  (node profiles — `remote-access`, D4), RFC-0033 §3.5 (the laptop
  client `oaap-expose.py`, which grew the `forward` verb §4 needed)

## 1. Purpose

RFC-0016 gave every instance its own Docker network, joined only by
its own containers and the gateway. Right for the app, inconvenient
for the person who has to look inside — a wrapped stack's own
Postgres, an admin port, a broker. This capability introduces the
object that makes looking inside a deliberate, time-boxed, recorded
act instead of a trip to the machine: an **access**.

0.1 delivered the object and its lifecycle. 0.2 delivered the first
shape carrying real traffic: a port forward. 0.3 delivers the second
shape's mechanics — a WireGuard peer into the whole instance network —
built and locally tested, but not yet measured on a real node, and
therefore not yet offered anywhere a person other than the machine's
own operator can reach.

## 2. The object

```json
{ "id": "a4c1e7",
  "instance": "<instance name/key>",
  "tenant": "<uuid>",
  "shape": "forward",                          // forward | wireguard
  "target": {"service": "db", "port": 5432,
            "container": "oaap-app-crm-db"},   // forward
  "holder": "<name the opener gave, default: themselves>",
  "opened_by": "<who queued the open>",
  "opened": "<ISO instant, UTC>",
  "expires": "<ISO instant, UTC>",
  "hours": 8,
  "state": "open" }
```

For a `wireguard` access, `target` instead holds
`{"peer_pubkey", "tunnel_ip", "instance_subnet", "gateway_ip"}` — never
the peer's private key, which is shown once and kept nowhere on the
node (D10, §5.3).

- An access belongs to **exactly one instance** and therefore exactly
  one tenant (RFC-0022). `tenant` is resolved from the instance at
  open time, the same way every other tenant-scoped record on this
  node resolves it.
- **Not instance configuration.** An access is not stored on the
  instance's registry entry, is not part of any manifest, and is not
  carried by backup, restore or promotion (RFC-0044 §1) — it is an act,
  not configuration. It is kept in its own file
  (`apps/remote-access.json`), the same way `connect.json` and
  `twin-readers.json` hold acts rather than configuration.
- **`target.container` is resolved once, at open time**, from the
  instance's own service list (RFC-0016): a single-service instance
  resolves any name (there is nothing to disambiguate); a
  multi-service instance requires an exact match on the service name,
  refused otherwise. This is the ONE container:port a forward may ever
  reach — fixed when the access opens, never re-resolved from a
  connection's own request, and never influenced by anything the
  laptop client sends.
- `holder` is free text, defaulting to the opener. For `forward` it is
  **not checked against the tenant's user list when the access
  opens** — but it IS the exact string every forward connection's
  identity check compares the caller's key to (§4): a holder that does
  not name a real, still-active user simply means nobody's key will
  ever match, which is refused the same way a wrong holder is. For
  `wireguard`, `holder` is a label only — the `.conf` file is a bearer
  credential (§5.3); nothing checks who is actually holding it.

## 3. Lifecycle

- **Open.** Checks, on the host, not only in a form: the instance
  exists; `shape` is one of `forward`/`wireguard`; `hours` is one of
  `1`/`8`/`24` (RFC-0044 D3, default `8`, no extension — opening again
  is a new act with a new audit entry); a `forward` access names a
  service that exists on the instance, and a port; a `wireguard`
  access requires the node to carry profile `remote-access` (D4) and
  `wireguard-tools` to be present. For `forward`, the connect service
  is joined to the instance's network here too (§4). For `wireguard`,
  a key pair is generated, a tunnel address is allocated, the peer is
  added to the node's `wg0` and the firewall fence is written (§5) —
  refused, with nothing written and nothing left half-applied, if any
  step fails. Writes the record and one tenant-audit line
  `access.opened` (who, for whom, instance, shape, target if any,
  hours).
- **List.** Open, unexpired accesses, optionally filtered by instance
  or tenant.
- **Close.** Removes the record early. For `forward`, the connect
  service leaves the instance's network too, but only once no other
  open `forward` access on that same instance still needs it. For
  `wireguard`, the peer is removed from `wg0` and its firewall fence
  rules are deleted. Writes `access.closed`.
- **Expire.** The same removal, run by the sweep, once `expires` has
  passed. Writes `access.expired` instead of `access.closed` — same
  shape as RFC-0038's `diagnose.expired` vs `diagnose.closed`.
- **Sweep.** `oaap app access sweep` closes every access whose time is
  up. It runs every minute from the same timer RFC-0038's diagnosis
  sweep already uses (`oaap-instance-watch.service`/`.timer`) — one
  more `ExecStart` line, not a new timer. Idempotent, like its
  neighbor: running it with nothing to close changes nothing.
- **No extension.** RFC-0044 D3: never extended in place. A longer
  look is a new access, with its own audit line — the same reasoning
  RFC-0038 D2 gives for its window.

## 4. The port forward (RFC-0044 §4)

```
laptop                                    node
┌──────────────────────┐                ┌───────────────────────────────┐
│ psql -h localhost      oaap-expose.py  │ gateway  /connect/forward     │
│      -p 5433  ──────▶  forward         │  1. who? holder's own key     │
│                      ──WebSocket──────▶│  2. this access: alive,       │
│                        (one per        │     'forward', not expired?   │
│                         TCP conn)       │  3. dial the ONE container:  │
└──────────────────────┘                │     port the access names     │
                                          └───────────────────────────────┘
```

- **A single hop, never inter-node.** Unlike `oaap.net.connector`'s
  tunnel (which crosses to another node), a forward is entirely local
  to the node the access was opened on: the gateway passes
  `/connect/forward` to the connect service, exactly as it already
  passes `/connect/tunnel` (same route shape, own handler).
- **One WebSocket per TCP connection**, raw bytes both ways, no
  framing of its own. The laptop client listens on a local port; every
  connection there opens its own WebSocket, relayed 1:1. There is
  nothing to multiplex, so nothing is.
- **Checked on every connection, not once.** The client's
  `Authorization: Bearer <API key>` is verified against identity
  (RFC-0027), and the resulting principal must equal the access's
  `holder` exactly — a key that opens fine but belongs to someone else
  is refused (403) without saying whose access it actually is. An
  unknown, non-`forward`, or expired access id answers 404/410, never
  401 — the request named the wrong access, not a bad key.
- **The connect service reaches the target because appctl put it
  there.** It carries no Docker socket and joins no network on its
  own initiative — the network join happens exactly once, when an
  access of shape `forward` opens on that instance, and is undone
  once no such access remains open on it (§3). The dial itself names
  only `target.container:target.port` — nothing a connection can
  redirect.
- **No new node capability.** No listener, no port published, no
  firewall rule: the fence here is code (the fixed dial target), not
  configuration — RFC-0044 §4 says so explicitly, which is why this
  shape did not have to wait for a firewall fence measured on a real
  node the way §5's WireGuard peer does.
- **The laptop client:** `oaap-expose.py forward --access <id>
  --server <node> --local-port <n>` (RFC-0033 §3.5's client, same
  binary, opposite verb from `expose`). Reads the key from `OAAP_KEY`
  or a hidden prompt, never an argument — same rule as `expose`.

## 5. The WireGuard peer (RFC-0044 §5) — built, measured, working (bridge-port design)

Unlike a forward, a WireGuard peer puts a device **inside the instance
network**, not through one fixed door — so the fence has to be the
network path itself, not application code. That is exactly the shape
RFC-0044 §2.2 and D2's consequence are cautious about, and why this
section is explicit about what has been measured and what has not.
0.3's design (one node-wide interface, reached by routing) turned out
not to work at all (§5.1a); 0.4's design (§5.1b onward) is a different
shape chosen specifically to work with the reason it failed, and has
been measured carrying traffic end to end.

### 5.1 The fence: a host firewall rule, not `AllowedIPs`

A WireGuard peer's own `AllowedIPs` (in its `.conf`) says which
destinations *that peer* routes into the tunnel — a client-side
courtesy, editable by whoever holds the file, and irrelevant to what
the *node* actually forwards once packets arrive decrypted. The
node-side fence is three `iptables` rules in the `DOCKER-USER` chain
(the chain Docker itself evaluates before its own per-network
isolation, and the same chain RFC-0044 §2.2 names), **inserted, in
this order, ahead of anything already in the chain** — Docker's own
default in that chain is a trailing `RETURN`, so a rule appended
instead of inserted would never be evaluated for this peer's packets:

```
iptables -I DOCKER-USER 1 -s <peer>/32 -d <gateway>/32 -j DROP
iptables -I DOCKER-USER 1 -s <peer>/32 -d <instance-subnet> -j ACCEPT
iptables -I DOCKER-USER 1 -s <peer>/32                     -j DROP
```

read top to bottom after insertion: the gateway's own address on the
instance network is excluded first (RFC-0044 §2.1 — the gateway
identifies the calling instance by which network a request arrived
on, "there is nobody else on it"; a peer that could reach it could use
the instance's own destinations with their stored credentials), the
rest of the instance's subnet is allowed, and everything else from
that peer is dropped. Removed with matching `-D` rules on close —
order does not matter for deletion.

**This is the rule D2's consequence asked to be measured on a real
node before any `.conf` is handed to anyone but the operator running
the CLI at the machine.** Built and unit-tested against the exact
`iptables` argument lists produced (mocking the binary — no container
runtime, no kernel WireGuard, needed to verify the *ordering*); on
2026-09-27 also measured for real, on oaap-test, with Jörg's explicit
permission to damage the node if it came to that ("es kann dort nichts
kaputt gehen … wir bauen dann gemeinsam wieder auf"). §5.1a is what
that measurement found.

### 5.1a What the real-node measurement found (2026-09-27, oaap-test)

**The three rules apply exactly as designed, in exactly the specified
order, and they are not the problem.** A simulated peer (a WireGuard
interface in its own network namespace, connected over a veth pair to
reach the real `wg0` on oaap-test) completed a real handshake, and
`iptables -S DOCKER-USER` afterwards showed the three rules in the
gateway-DROP / subnet-ACCEPT / catch-all-DROP order §5.1 specifies,
correctly removed again on close. The gateway's address was correctly
excluded (confirmed unreachable, by both HTTP and ICMP).

**What failed: the peer could not reach the instance's OWN container
either — the thing the fence is supposed to ALLOW.** The packet left
the peer, arrived on `wg0` (confirmed with `tcpdump`), and then simply
vanished — 0 packets, 0 bytes on every rule in `DOCKER-USER`, meaning
it never even reached the filter table's `FORWARD` chain where those
rules live. The actual cause, found with `nft list ruleset`: Docker
29.7.1 installs its own rules in `table ip raw`, chain `PREROUTING`,
one per container address, of the shape

```
ip daddr <container-ip> iifname != "<container's-own-bridge>" drop
```

for **every** container on the node, on every network — not only ones
with published ports. The `raw` table is evaluated before `conntrack`,
before `nat`, and before the `filter` table `DOCKER-USER` lives in
(netfilter hook order: raw → mangle → nat → filter). A WireGuard
peer's packet, routed in from `wg0`, arrives with `iifname = wg0`, not
the container's own bridge — so this rule drops it **before `DOCKER-
USER` is reached at all**, regardless of anything §5.1 does. Docker
added this specifically to stop exactly the technique this capability
relies on: a container reached by routing a packet in from some other
interface rather than through its own bridge, which Docker treats as
address-spoofing protection for its published-port feature, applied
unconditionally to every container's address, spoofing risk or not.

**This is not a bug in the three rules — it is the routing PATH they
sit on being closed one hook earlier, for every container on the
node, by Docker itself.** No ordering fix, no additional `DOCKER-USER`
rule and no `conntrack`-based return-path rule changes this: a fix
was tried live (an `ESTABLISHED,RELATED` return-path rule, in case the
gap was one-directional) and made no difference, because the drop
happens for the very first packet, before routing or filtering
decisions the fix could influence.

**What this means for §5 as specified:** a WireGuard peer cannot
reach a container on the instance network **at all**, on a node
running a Docker version with this protection, by the routing
mechanism §5.1/§5.2 describe. This is a materially different, and
more serious, finding than "the rule order needs checking" — it says
the mechanics built in 0.3 do not deliver §5's promise on a current
Docker install, independent of anything this capability's own code
does right or wrong. `oaap.net.remote-access`'s other shape is
unaffected: §4's port forward does not route into a bridge at all —
`connect_join_network()` uses `docker network connect`, the sanctioned
way for a process to join a bridge, which this Docker protection does
not restrict.

**Jörg's choice, 2026-09-27: "mit docker arbeiten"** — of the four
options this measurement raised (bridge the peer in; turn Docker's
protection off node-wide; drop shape (a) and point at the router
instead, per D9; or leave §5 exactly as built and stop), he picked
bridging the peer in: work WITH Docker's own protection, not against
or around it. §5.1b is the redesign that followed and the second
measurement that validated it.

### 5.1b The redesign, and the second measurement (2026-09-27, oaap-test)

**Each instance that has at least one open `wireguard` access gets its
own small apparatus, instead of the node carrying one shared `wg0`:**

```
                          root namespace                      oaap-wg-<instance> namespace
outside peer  ──UDP:ext──▶ PREROUTING DNAT           ┌───────────────────────────────────┐
(real client)              --dport <ext> -j DNAT     │ veth (WAN side) ──▶ wg0 (own key,  │
                            --to <wan-ns-ip>:51820 ──▶│   own listen port 51820 INSIDE)    │
                                                       │        │ decrypts                  │
                             veth (bridge side) ◀──────────────┘                            │
                             root end: real member    └───────────────────────────────────┘
                             of the instance's OWN
                             Docker bridge (`master br-...`)
                                     │
                                     ▼
                        the instance's containers, on their own bridge,
                        exactly as any other container reaches them
```

- **A WireGuard interface created DIRECTLY inside its target
  namespace** (`ip netns exec <ns> ip link add wg0 type wireguard`),
  **never moved there afterwards.** Tried the other way first and it
  does not work: `ip link set wg0 netns <ns>` moves the interface, but
  its UDP transport socket does not follow the move correctly — `wg
  show` inside the namespace claims a listening port, `ss -u -a -n`
  shows no socket at all, and the handshake never completes. Creating
  it in-namespace from the start does not have this problem.
- **The bridge-side veth's root end is a genuine port of the
  instance's own Docker bridge** (`ip link set <veth> master
  br-...`), not a routed hop — this is the whole point: traffic
  arriving this way is bridged, and Docker's raw-table rule (§5.1a)
  reports the bridge itself as the ingress interface for bridged
  traffic, which is exactly what the rule accepts. Measured: a
  simulated peer through this path reached the instance's real app
  container with 3/3 pings and a real HTTP 404 — the raw-table
  counters for both the app container's and the gateway's own rule
  stayed at `0 packets, 0 bytes` throughout, confirming this specific
  protection is no longer even in the path.
- **A second veth pair, plus one externally-DNAT'd UDP port per
  instance**, is how the outside world reaches this namespace's `wg0`
  at all: `iptables -t nat -A PREROUTING -p udp --dport <external>
  -j DNAT --to-destination <wan-ns-ip>:51820`. Different instances'
  peers must be told apart before decryption (the WireGuard packet
  itself carries nothing legible), so each instance's apparatus claims
  its own external port, allocated the same way a tunnel address is —
  by scanning what is already in use, no separate counter to drift.
- **Two `FORWARD` rules, not one — found missing by the second
  measurement, not designed in from the start.** The first live test
  after building this completed a full WireGuard handshake (the
  server side logged real bytes received) but the peer never received
  anything back: `FORWARD`'s default policy is `DROP`, and the first,
  obvious rule (`-d <wan-ns-ip> --dport 51820 -j ACCEPT`) only admits
  packets INTO the apparatus — the handshake reply and every packet
  after it, source `<wan-ns-ip>:51820`, matched nothing and was
  silently dropped. Fixed by adding the mirror rule (`-s <wan-ns-ip>
  --sport 51820 -j ACCEPT`); both are inserted and removed together.
- **`net.bridge.bridge-nf-call-iptables` must be `1`, and does not
  survive a reboot — found missing by the same measurement, the
  hard way.** With `br_netfilter` not loaded (the state of oaap-test
  before this was measured), a peer's traffic crosses from one bridge
  port to another WITHOUT ever reaching `iptables`' `FORWARD` chain at
  all — the three §5.1 rules exist, are correctly ordered, and simply
  never see the packet. A first pass of this measurement "succeeded"
  (the app container answered) for the wrong reason: with the fence
  chain unreachable, EVERYTHING was reachable, gateway included, and
  the gateway only happened to fail for an unrelated, unverified
  reason. Re-running with `net.bridge.bridge-nf-call-iptables=1`
  explicitly set changed the outcome measurably: the same `DOCKER-USER`
  rules' packet counters, all zero before, now moved — the ACCEPT rule
  counted exactly the app-container packets sent, the gateway-DROP
  rule counted exactly the gateway packets sent. **The build now
  re-asserts this itself, node-wide, on every apparatus bring-up**
  (`modprobe br_netfilter` + `sysctl -w
  net.bridge.bridge-nf-call-iptables=1`), refusing outright if it
  cannot, because nothing built after it would actually be fenced.
  This is a permanent, node-wide side effect of carrying this
  capability at all, not reverted when an apparatus tears down — and,
  incidentally, the same setting Docker's own documentation recommends
  for its OWN inter-container isolation features to work at all.

**The measurement that mattered, end to end, through the built code
itself** (`oaap node add-profile remote-access` →
`oaap app access open <instance> --shape wireguard --endpoint
<node's real LAN address> --holder <name>` → the printed `.conf`
loaded into a real WireGuard interface in a separate simulated-peer
namespace): a completed handshake, 3/3 pings and a real HTTP 404 from
the instance's own app container, and the gateway's address
confirmed unreachable — with `DOCKER-USER`'s own packet counters
showing exactly 3 accepted and exactly 3 dropped, matching the two
attempts made. Closing the access removed the peer, its fence rules,
and (once it was the last peer of that instance) the entire
apparatus — namespace, both veth pairs, the DNAT rule, both `FORWARD`
rules — leaving the node exactly as clean as it started.

### 5.2 The apparatus (per instance, not per node)

- **Gated by node profile `remote-access`** (RFC-0011, D4): adding the
  profile only checks the tooling is present (`wg`, `wg-quick`, `ip`).
  Unlike 0.3, nothing host-wide starts here any more — no apparatus
  exists until an instance's FIRST `wireguard` access opens. Removing
  the profile is refused while any `wireguard` access is still open,
  the same way `store`'s profile refuses removal while schemas exist.
- **One apparatus per instance, brought up on its first peer, torn
  down with its last.** Its own network namespace, its own WireGuard
  identity (generated once, kept at rest, 0600, never shown again —
  the INSTANCE's own identity, not a peer's), its own externally
  reachable UDP port, its own bridge-side veth into its own Docker
  network. A second peer of the SAME instance shares all of this —
  same namespace, same identity, same external port; a peer of a
  DIFFERENT instance gets an entirely separate one. Reboot-safe: the
  namespace and interfaces do not survive a reboot, the state that
  remembers them (and the instance's own key) does, and the next
  access open for that instance rebuilds the rest from it, unchanged
  from the peer's point of view (same identity, same `.conf`).
- **`net.bridge.bridge-nf-call-iptables=1`, re-asserted node-wide on
  every apparatus bring-up** (§5.1b) — the one genuinely node-wide
  side effect of this profile, and the reason the fence (§5.1) sees
  bridged traffic at all.
- **No port forward needs any of this.** §4 rides the gateway; only
  §5 needs a UDP listener reachable from outside the node at all.

### 5.3 The peer

- **The node generates the key pair, not the laptop** (D10): a
  `wireguard-tools` `wg genkey`/`wg pubkey` pair per access. The
  private key is placed in the returned `.conf` text and printed
  **once**, at `oaap app access open --shape wireguard`, in the same
  breath as RFC-0027 shows a freshly issued API key's secret; the
  node keeps only the public key, inside the access record.
  **Not built: showing it from the portal** (§9) — the command line
  is the only door, on purpose.
- **The `.conf`'s `Endpoint` names THIS instance's own externally-DNAT'd
  port** (§5.1b), not one fixed port for the whole node — a different
  instance's peer dials a different port on the same address.
- **The `.conf` is a bearer credential** (RFC-0044 §5): whoever holds
  the file until it expires is inside; the node cannot tell who that
  is. Unlike a forward, there is no per-connection identity check.
- **The tunnel address** is the lowest free `/32` in this INSTANCE's
  own WireGuard subnet (isolated per apparatus, so every instance
  reuses the same range without collision), tracked the same way the
  connect service's network membership is (§3/§4): by scanning the
  currently open `wireguard` accesses for this instance, no separate
  counter to drift.

### 5.4 What the laptop needs

An ordinary WireGuard client app and the printed `.conf` — no
`oaap-expose.py` involved, unlike §4. Its `AllowedIPs` names the
instance's subnet as a courtesy default (so the peer's own routing
sends the right traffic into the tunnel); the security boundary is
§5.1's fence, not this file. **This courtesy default is load-bearing
for anyone testing by hand rather than through `wg-quick` or a real
client app:** both install a kernel route for `AllowedIPs` toward the
interface automatically from the `.conf`; a bare `ip link add` +
`wg set` peer (as the second measurement's simulated client used)
does not, and traffic silently leaves by the wrong interface without
one — indistinguishable, from the outside, from the fence dropping
it.

## 6. Roles (D1)

Opening or closing an access requires `server_admin`, or the
`tenant_admin` of the **instance's own tenant** — never another
tenant's `tenant_admin`, refused by the same cross-tenant check every
other portal action already runs. An access a `server_admin` opens is
recorded in the **tenant's** log, not a separate operator log (RFC-0022
§6: "access by the operator is itself an event"). This governs who may
**open and close the record**; §4's per-connection check is a separate
question answered by the holder's own key, not by this role. §5 has no
equivalent per-connection check (§5.3).

## 7. Interface (CLI)

```
oaap app access open <instance> [--shape forward|wireguard]
    [--holder <name>] [--hours 1|8|24] [--service <name> --port <n>]
oaap app access list [<instance>]
oaap app access close <access-id>
oaap app access sweep
```

`oaap app access open` prints the record; for `forward`, the exact
client command the holder runs next; for `wireguard`, the `.conf`
text, once. The portal card offers `forward` and its lifecycle on the
instance page's "Fernzugang" tab; `wireguard` still shows there as
"not built" (§9) — the command line is the only door until the fence
is measured on a real node.

## 8. Security requirements

- **Default: no access.** No instance has an open access unless a
  person with the right role opened it.
- **A named holder for `forward`, checked at connection time.** §2/§4:
  not checked against the tenant's users when the record is created,
  but every forward connection's identity check must resolve to that
  exact name. `wireguard`'s holder is a label, not a check (§5.3).
- **Always a TTL**, one of three fixed durations, never extended.
- **One tenant.** An access belongs to the instance's tenant; the
  cross-tenant check that guards every other portal action guards this
  one too.
- **One fixed target, decided by the operator who opened it, never by
  the connection.** A forward's `target.container`/`target.port` are
  resolved once, at open time, from the instance's own declared
  services — nothing a laptop client sends can change or widen it. A
  WireGuard peer's reach is the firewall fence (§5.1), decided the
  same way, at open time, from the instance's own network.
- **The gateway's address on the instance network is excluded from
  every `wireguard` access** (§5.1) — RFC-0044 §2.1's reason: the
  gateway identifies the calling instance by which network a request
  came from, and a peer inside that network could otherwise reach the
  instance's own destinations and their stored credentials.
- **Metadata always, payload never** (D7). The audit log records
  opening, closing, expiry and a `access.forward.connected` line per
  connection (who, instance, target) — never the bytes exchanged; the
  connect service does not parse the protocol running over a forward
  and makes no claim to. A `wireguard` access is recorded the same way
  at open/close/expiry; there is no per-connection record for it (no
  identity check happens per packet — §5.3).
- **The spool is data, not trust.** Every open/close check above runs
  again on the host when the portal queues one, exactly as RFC-0038's
  diagnosis window does; every §4 check runs again on the connect
  service for every single connection, not only the first.
- **The WireGuard listener exists only where a `server_admin` put the
  profile** (D4, RFC-0011 implementation note) — never as a side
  effect of anything a tenant does.

## 9. What 0.4 explicitly does not do

- **No portal issuance of a WireGuard `.conf`.** The command line is
  the only door (§7) — a deliberate, not accidental, gap: a fence that
  is now measured working is not, by itself, a decision to offer this
  from the portal. That remains a separate, later question.
- **Not measured against a real client app or `wg-quick`** — the
  second measurement's peer was built by hand (`ip link add` + `wg
  set`, §5.4) to control exactly what was being tested; a peer set up
  the ordinary way (`wg-quick up`, a phone/desktop app) has not yet
  been tried against this apparatus.
- **Not measured across a reboot.** §5.2 states that the design
  should survive one (the persisted state and key rebuild everything
  else); this has not actually been rebooted and re-measured.
- **No names for peers** (RFC-0044 D6) — a WireGuard peer reaches
  containers by address; the page/command line list the addresses
  current at open time, which change on recreate (RFC-0016).
- **No QR code.** The `.conf` text alone; turning it into a scannable
  code is unbuilt.
- **No address-collision warning** (RFC-0044 §5, "Address
  collisions") — the node does not yet check whether its WireGuard or
  instance subnets overlap common home ranges.
- **No device access** (RFC-0044 D9) — a different object, a different
  fence, out of scope here.

## 10. Conformance tests

1. Opening an access on an unknown instance is refused.
2. Opening an access with a duration other than 1/8/24 hours is
   refused, with all three checked from a form value, not trusted.
3. Opening a `forward` access without a port is refused; naming a
   service the instance does not have is refused by name, not
   silently substituted.
4. An opened access appears in `oaap app access list` for its instance
   and disappears once closed.
5. Closing an unknown access id is refused.
6. `access sweep` closes an access whose `expires` has passed, and
   leaves an unexpired one alone.
7. Every open and close writes exactly one tenant-audit line, with the
   right actor and role; a denied attempt (wrong role) writes exactly
   one `access.opened`/`access.closed` line with `result: denied` and
   no record.
8. A `tenant_admin` may open and close an access on their own tenant's
   instance; the same request against another tenant's instance is
   refused before this capability's own role check runs (the shared
   cross-tenant guard).
9. The record written to `apps/remote-access.json` never appears in
   the instance's registry entry, a backup, or a promoted instance.
10. A `forward` connection with the holder's own key relays bytes
    exactly, both ways, over one WebSocket per TCP connection.
11. A `forward` connection with a key that verifies but is not the
    holder is refused (403), without revealing who the holder is.
12. A `forward` connection naming an unknown, non-`forward`, or
    expired access is refused (404/410), never mistaken for a bad key
    (401).
13. Two connections to the same `forward` access are independent —
    one ending does not affect the other.
14. Closing the last `forward` access of an instance makes the connect
    service leave that instance's network; closing one of several does
    not.
15. Opening a `wireguard` access without node profile `remote-access`
    is refused, and nothing is written (§5.2).
16. An instance's FIRST `wireguard` access allocates the lowest free
    tunnel address, brings up that instance's own namespace/interface/
    bridge-veth apparatus (§5.1b), and inserts the three firewall
    rules of §5.1 AND the two `FORWARD` rules of §5.1b, in the exact
    order specified, ahead of the chain's existing content.
17. A SECOND `wireguard` access on the SAME instance shares the first
    one's apparatus exactly (same namespace, same external port, no
    new veth pair) and gets its own tunnel address and firewall rules.
18. Closing a `wireguard` access removes its peer and its three
    firewall rules; a failed step during open leaves nothing partially
    applied, INCLUDING a just-created apparatus if this was the
    instance's first attempted peer.
19. Closing the LAST open `wireguard` access of an instance tears down
    its entire apparatus (namespace, both veth pairs, the DNAT rule,
    both `FORWARD` rules); closing one of several leaves the apparatus
    and the other peers untouched.
20. Two simultaneous `wireguard` accesses on the SAME instance receive
    two different tunnel addresses; on TWO DIFFERENT instances, two
    different external ports and two different namespaces.
21. The `.conf` text is returned exactly once, from `access_open`, and
    is never written to `apps/remote-access.json` or any other file;
    its `Endpoint` port is that instance's own external port.
22. Removing node profile `remote-access` while any `wireguard` access
    is open, on any instance, is refused, mirroring `store`'s own
    refusal while schemas exist.
23. Bringing up an apparatus asserts
    `net.bridge.bridge-nf-call-iptables=1` first and refuses outright,
    before creating anything, if that fails (§5.1b).

## 11. Dependencies

RFC-0044, RFC-0038 (window/sweep pattern), RFC-0022 (tenant, audit
log), RFC-0027 (the holder's own key, checked per forward connection),
RFC-0016 (instance networks, container naming), RFC-0011 (node
profiles, `remote-access`), RFC-0033 §3.5 (the laptop client §4
extended).

## Deutsche Zusammenfassung

**Worum es geht.** RFC-0044 will einen zeitlich begrenzten Zugang eines
Menschen in genau ein Instanznetz — als eigenes Objekt, „Zugang"
genannt. Stufe 1 (0.1) baute das Objekt selbst. Stufe 2 (0.2) ließ eine
Portweiterleitung wirklich Verkehr tragen — der Inhaber-Schlüssel wird
bei jeder Verbindung erneut geprüft, das Ziel steht fest seit dem
Öffnen, keine Firewall-Regel nötig.

**Stufe 3 (0.3, diese Fassung): die WireGuard-Mechanik ist gebaut, an
einem echten Knoten gemessen — und dabei blockiert vorgefunden. Nicht
durch einen Fehler in dieser Mechanik, sondern durch Docker selbst.**

- **Die Firewall-Regel, nicht die `AllowedIPs`-Zeile, ist der Zaun.**
  Drei `iptables`-Regeln in der `DOCKER-USER`-Kette, in genau dieser
  Reihenfolge VOR den bestehenden Inhalt der Kette eingefügt (nicht
  angehängt — Dockers eigene Vorgabe dort ist ein `RETURN`, ein
  angehängter Satz käme nie zum Zug): erst die Gateway-Adresse dieses
  Netzes ausschließen, dann den Rest des Instanznetzes erlauben, dann
  alles andere von diesem Peer verwerfen.
- **Neues Knotenprofil `remote-access`** (D4): legt den Schlüssel des
  KNOTENS selbst an (einmalig, nie wieder gezeigt) und bringt ein
  `wg0`-Interface hoch. **Der Knoten erzeugt den Schlüssel des PEERS**
  (D10), zeigt die `.conf`-Datei einmal an der Kommandozeile.

**Am 27.09. auf oaap-test gemessen, mit deiner ausdrücklichen
Freigabe, den Knoten dabei notfalls zu beschädigen.** Ein
nachgebildeter Peer (eigener Netzwerk-Namensraum, per veth an den
echten Knoten angebunden) baute einen echten WireGuard-Handschlag auf.
**Die drei Regeln wirken genau wie entworfen** — die Gateway-Adresse
war nachweislich unerreichbar (weder HTTP noch Ping kamen durch).
**Aber auch der App-Container der Instanz war unerreichbar — das,
was der Zaun eigentlich ERLAUBEN soll.** Der Grund, mit `tcpdump` und
`nft list ruleset` gefunden: Docker (Version 29.7.1) legt für JEDEN
Container-Namen, auf jedem Netz, eine eigene Regel in der
**`raw`-Tabelle** an — „kommt ein Paket für diese Container-Adresse
nicht von der eigenen Bridge, verwerfen" — und diese Tabelle wird VOR
`DOCKER-USER` ausgewertet. Ein über WireGuard hereingeroutetes Paket
trägt als Eingangsschnittstelle `wg0`, nie die Bridge — Docker verwirft
es deshalb, BEVOR meine drei Regeln überhaupt erreicht werden. Das ist
genau die Technik, gegen die Docker sich mit dieser Regel schützt: ein
Container über eine fremde Schnittstelle hereingeroutet erreichen,
statt über die eigene Bridge.

**Das ist kein Ordnungsfehler in den drei Regeln — der Weg, auf dem sie
sitzen, ist eine Stufe früher schon zu.** Eine Rückweg-Regel
(`conntrack ESTABLISHED,RELATED`) wurde live versucht und änderte
nichts, weil schon das allererste Paket verworfen wird, bevor Routing
oder Filterung überhaupt entscheiden. **Portweiterleitung (§4) ist
davon nicht betroffen** — sie routet nicht in eine Bridge hinein,
sondern tritt ihr regulär bei (`docker network connect`), genau der
Weg, den Docker vorsieht.

**Jörgs Entscheidung, 27.09.: „mit Docker arbeiten".** Von vier
Optionen (Bridge-Einbindung; Dockers Schutz knotenweit abschalten;
WireGuard ganz aufgeben und auf den Router verweisen wie beim
Gerätezugang D9; oder es einfach so stehen lassen) fiel die Wahl auf
die erste: mit Dockers eigenem Schutz arbeiten, nicht gegen ihn.

**Stufe 4 (0.4, diese Fassung): neu gebaut nach diesem Befund — und
ein ZWEITES Mal gemessen, diesmal erfolgreich, Ende zu Ende, durch den
gebauten Code selbst.** Jede Instanz mit mindestens einem offenen
Zugang bekommt jetzt ihre EIGENE kleine Apparatur statt eines
gemeinsamen knotenweiten `wg0`: ein eigener Netzwerk-Namensraum, ein
WireGuard-Interface DIREKT darin angelegt (niemals nachträglich
hineinverschoben — das zerstört die UDP-Anbindung des Interfaces,
gemessen), ein Veth-Paar, dessen Knoten-Ende ein ECHTES Mitglied der
Docker-Bridge dieser Instanz ist (`master br-...`) — genau deshalb
sieht Dockers `raw`-Tabellen-Regel jetzt die Bridge selbst als
Eingang, nicht `wg0`, und lässt den Verkehr durch. Ein zweites
Veth-Paar plus ein je-Instanz-eigener, von außen weitergeleiteter
UDP-Port sorgen dafür, dass ein echter Peer von außerhalb dieses
Interface überhaupt erreicht.

Die zweite Messung fand dabei selbst noch zwei echte Fehler im neuen
Bau, BEVOR sie bestand: erstens fehlte eine zweite `FORWARD`-Regel für
den RÜCKWEG (der Server empfing den Handschlag, die Antwort kam beim
Peer nie an — Dockers `FORWARD`-Kette hat als Grundregel `DROP`, und
nur die Hinrichtung war erlaubt); zweitens war `br_netfilter` auf
oaap-test gar nicht geladen — ohne dieses Modul sieht `DOCKER-USER`
gebrücktem Verkehr überhaupt nicht zu, und ein erster, scheinbar
erfolgreicher Testlauf hatte in Wahrheit GAR KEINEN Zaun geprüft (der
App-Container war nur erreichbar, weil NICHTS blockierte; dass das
Gateway trotzdem unerreichbar blieb, war Zufall, kein Zaun). Beide
Fehler sind jetzt im Code selbst behoben — `appctl.py` erzwingt
`net.bridge.bridge-nf-call-iptables=1` bei jeder Apparatur-Inbetriebnahme
selbst, weil dieser Schalter einen Neustart nicht überlebt.

**Der entscheidende Test, mit dem echten Code:** Profil setzen, Zugang
öffnen, die ausgegebene `.conf` in einen echten (simulierten) Peer
laden — vollständiger Handschlag, 3 von 3 Pings zum App-Container samt
echter HTTP-404-Antwort, das Gateway nachweislich weiter unerreichbar,
mit den `DOCKER-USER`-Zählern als Beleg (genau 3 erlaubt, genau 3
verworfen). Schließen des letzten Zugangs einer Instanz baut ihre
gesamte Apparatur wieder vollständig ab.

**Ausdrücklich nicht gebaut/gemessen:** Portal-Ausgabe der `.conf`,
QR-Code, Namensauflösung für Peers (D6), Warnung vor
Adressüberlappung mit Heimnetzen, ein echter WireGuard-Client
(`wg-quick`/App) statt des von Hand gebauten Test-Peers, ein Neustart
des Knotens mit anschließender erneuter Messung. Gerätezugang (D9)
bleibt ein eigenes Objekt.
