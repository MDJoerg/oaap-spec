# oaap.net.remote-access — A Person Inside One Instance Network, For a While

- **ID:** `oaap.net.remote-access`
- **Version:** 0.3
- **Maturity:** draft (0.1: the access object, its lifecycle, the
  tenant audit trail and the portal card — no traffic yet. 0.2: the
  port forward of §4 — a `forward` access carries real bytes. 0.3
  added the mechanics of §5's WireGuard peer, CLI-only, pending the
  real-node measurement D2's consequence requires. **That measurement
  happened on 2026-09-27, on oaap-test, and it found the fence as
  specified does not work against a current Docker daemon (29.7.1) —
  see §5.1a.** The object, the node profile, the key generation and
  the record-keeping all work exactly as built; what fails is the
  routing path a WireGuard peer would need to reach a container at
  all, for a reason that has nothing to do with this capability's own
  rules and everything to do with a Docker hardening feature §5.1a
  describes. Shape `wireguard` therefore remains CLI-only and is now
  additionally known not to carry traffic — a stronger statement than
  "not yet measured". §4's port forward is unaffected: it does not
  route into a bridge, it dials into one via `docker network connect`,
  which is not restricted this way.)
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

## 5. The WireGuard peer (RFC-0044 §5) — mechanics built, measured, blocked

Unlike a forward, a WireGuard peer puts a device **inside the instance
network**, not through one fixed door — so the fence has to be the
network path itself, not application code. That is exactly the shape
RFC-0044 §2.2 and D2's consequence are cautious about, and why this
section is explicit about what has been measured and what has not —
and, since 2026-09-27, about what the measurement found.

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

**Options, not yet decided (this needs Jörg, not a unilateral fix):**

- **Bridge the peer in, rather than routing to it.** Run WireGuard
  (or at least the per-access peer) inside a dedicated network
  namespace connected to the target bridge by a veth pair whose
  bridge-side end is an actual member of that bridge — so the
  packet's `iifname` at Docker's raw-table check genuinely is the
  bridge, because it entered fresh through a bridge port, not routed
  in. Works with Docker's protection instead of against it; costs
  real per-access (or per-instance) network plumbing, closer in shape
  to what §4's `connect_join_network()` already does, but for a whole
  subnet instead of one dial target.
- **Turn the protection off.** Docker's anti-spoofing rule is a
  daemon-wide hardening feature, not per-network; disabling it (if
  even possible without patching the daemon or its generated rules)
  would remove a real protection for every instance on the node, for
  every container, spoofing risk or not — a much bigger trade than
  this capability alone should decide.
- **Do not build shape (a) as routing at all — reconsider it as
  something else,** e.g. a case `oaap.net.remote-access` declines and
  points at the router's own WireGuard (RFC-0044 D9's Fritzbox case
  already does this for devices) rather than the platform's.
- **Leave §5 exactly as built (object, profile, keys, fence code,
  CLI) and stop here.** The object and its lifecycle are real and
  useful independent of whether shape `wireguard` ever carries
  traffic; nothing forces a decision today.

### 5.2 The node's own interface

- **Gated by node profile `remote-access`** (RFC-0011, D4): adding the
  profile (`oaap node add-profile remote-access`) generates the node's
  own key pair once (kept at rest under the platform's data
  directory, 0600, never shown again — the node's OWN identity, not a
  peer's), and brings up a `wg0` interface with that identity and a
  fixed listen port, if not already up. Removing the profile takes it
  down — refused while any `wireguard` access is still open, the same
  way `store`'s profile refuses removal while schemas exist.
- **One interface, one address range for the whole node** (not per
  instance): peers get individual `/32` tunnel addresses out of it;
  which INSTANCE a peer may reach is entirely the firewall fence's
  job, not the interface's.
- **No port forward needs this profile.** §4 rides the gateway; only
  §5 needs a UDP listener on the host, exactly as RFC-0044 §4 already
  says.

### 5.3 The peer

- **The node generates the key pair, not the laptop** (D10): a
  `wireguard-tools` `wg genkey`/`wg pubkey` pair per access. The
  private key is placed in the returned `.conf` text and printed
  **once**, at `oaap app access open --shape wireguard`, in the same
  breath as RFC-0027 shows a freshly issued API key's secret; the
  node keeps only the public key, inside the access record.
  **Not built: showing it from the portal.** The command line is the
  only door in 0.3, on purpose — a portal flow needs its own one-time
  display and is a separate, later piece of work, and D2's consequence
  means it should not exist before the fence itself has been measured
  live.
- **The `.conf` is a bearer credential** (RFC-0044 §5): whoever holds
  the file until it expires is inside; the node cannot tell who that
  is. Unlike a forward, there is no per-connection identity check.
- **The tunnel address** is the lowest free `/32` in the node's
  WireGuard subnet, tracked the same way the connect service's
  network membership is (§3/§4): by scanning the currently open
  `wireguard` accesses, no separate counter to drift.

### 5.4 What the laptop needs

An ordinary WireGuard client app and the printed `.conf` — no
`oaap-expose.py` involved, unlike §4. Its `AllowedIPs` names the
instance's subnet as a courtesy default (so the peer's own routing
sends the right traffic into the tunnel); the security boundary is
§5.1's fence, not this file.

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

## 9. What 0.3 explicitly does not do

- **No portal issuance of a WireGuard `.conf`.** The command line is
  the only door (§7) — a deliberate, not accidental, gap: D2's
  consequence puts the real-node fence measurement before offering
  this anywhere, and the portal is "anywhere".
- **The fence is untested on a real node.** §5.1's `iptables` rules
  are verified as text (the exact argument lists, in the right order)
  against a mocked binary — never against a real Docker network, a
  real gateway container, or a real peer sending real packets. This
  is the single most important line in this document: *do not treat
  §5 as safe to use until that measurement exists and is recorded.*
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
16. Opening a `wireguard` access allocates the lowest free tunnel
    address, adds the peer to `wg0`, and inserts the three firewall
    rules of §5.1 in the exact order specified, ahead of the chain's
    existing content.
17. Closing a `wireguard` access removes the peer from `wg0` and
    deletes all three firewall rules; a failed step during open leaves
    nothing partially applied.
18. Two simultaneous `wireguard` accesses receive two different
    tunnel addresses; closing one does not touch the other's peer or
    rules.
19. The `.conf` text is returned exactly once, from `access_open`, and
    is never written to `apps/remote-access.json` or any other file.
20. Removing node profile `remote-access` while a `wireguard` access
    is open is refused, mirroring `store`'s own refusal while schemas
    exist.

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

**Offene Wahl, noch nicht entschieden:** den Peer per Netzwerk-
Namensraum + veth ECHT als Bridge-Mitglied einbinden (aufwendiger,
funktioniert MIT Dockers Schutz statt gegen ihn); Dockers Schutz
knotenweit abschalten (schwächt ihn für JEDEN Container, nicht nur
diesen Zugang); WireGuard als Plattform-Fähigkeit ganz aufgeben und
stattdessen auf den Router verweisen (wie beim Gerätezugang, D9); oder
es einfach hier stehen lassen — das Objekt selbst bleibt nützlich,
auch wenn diese Form nie Verkehr trägt.

**Ausdrücklich nicht gebaut:** Portal-Ausgabe der `.conf`, QR-Code,
Namensauflösung für Peers (D6), Warnung vor Adressüberlappung mit
Heimnetzen. Gerätezugang (D9) bleibt ein eigenes Objekt.
