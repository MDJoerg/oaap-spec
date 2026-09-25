# RFC-0044: Remote Access Into Instance Networks — A Person Inside, For a While, In One Place

- **Status:** Draft (2026-09-25) — nothing decided, nothing built. Build
  follows RFC-0033 stage 3 (it reuses its laptop client).
- **Date:** 2026-09-25
- **Authors:** Jörg (the wish), Claude (analysis & proposal)
- **Depends on:** RFC-0001 (capability #7 `oaap.net.remote-access`),
  RFC-0002 (gateway, default deny), RFC-0005 (WireGuard clients and DNS
  push), RFC-0008 (`server_admin`), RFC-0011 (node profiles, set at the
  machine), RFC-0015 (declared endpoints — the standing, public
  alternative this RFC is not), RFC-0016 (one network per instance, the
  gateway on every one of them), RFC-0022 (tenant as boundary, tenant
  audit log), RFC-0027 (API keys — the person's credential for the
  client), RFC-0030 (rehearsals — expiry and the sweep), RFC-0033
  (destinations; the laptop client of §3.5; D3 and §8, which reserve
  exactly this capability), RFC-0038 (the time-boxed diagnosis window —
  the closest precedent)
- **Driver:** Jörg, 2026-09-25: *„wir werden zukünftig mehr Services
  bekommen, die wir wrappen und die mehr als ein Container mitbringen.
  Beispielsweise Datenbanken, die nicht von außen erreichbar sind. Hier
  wäre es hilfreich, wenn man über eine Art VPN in die internen Netze
  dieser Service kommen kann und wenn wir das als Plattform Capability
  unterstützen. So eine Art Wireguard Service, startbar aus dem
  Portal."* — and, the same conversation: own RFC, not part of
  RFC-0033; draft now, build after RFC-0033 stage 3.

## Summary

A wrapped stack brings containers nobody outside is meant to reach: the
Postgres behind an app, a broker's admin port, a search index. RFC-0016
made that true structurally — they sit on the instance's own network
`oaap-inst-<instance>`, which only the instance's containers and the
gateway join. That is right for the app and inconvenient for the person
who has to look inside: today the only way to point DBeaver at that
Postgres is to sit at the machine with Docker rights.

This RFC introduces one object, an **access** (*Zugang*): a person,
one instance, a limited time. It is opened on the instance page
(„Zugang öffnen, 8 Stunden"), it expires by itself, it is swept, and it
is recorded in the tenant's audit log. It comes in two shapes:

- **port forward** — the laptop client of RFC-0033 §3.5 pulls **one
  port of one container** to the laptop's `localhost`, over HTTPS
  through the gateway. No UDP, no router change, passes corporate
  proxies. One door.
- **WireGuard peer** — a `.conf` file or QR code for the WireGuard app
  puts the laptop **into the instance network**. A network, not a
  door; needs a UDP listener on the node.

Two rules carry both shapes:

> **1. An access reaches one instance network — never the node, never
> the LAN, never another tenant — and the node enforces that, not the
> peer.**
> **2. An access is opened by a person with the right to administer the
> instance, lasts a chosen time, ends by itself, and leaves a record.**

The recommendation is to build the port forward first (it covers the
common case, "DBeaver on this one Postgres", more narrowly) and the
WireGuard peer second, on nodes that opt in.

## Motivation

### 1. Wrapped stacks have insides now

RFC-0016 lifted the one-service limit and gave every instance its own
network; non-web services "carry no route and are never published". The
first stacks that use it bring their own database, and RFC-0031 brings a
Postgres per tenant. What a developer or an administrator does with such
a database — inspect a table, run a migration by hand, export a
selection — needs a client on their own machine talking to the
database's port.

### 2. What exists does not fit

| Way in | Why it does not fit |
| --- | --- |
| `sudo docker exec …` at the machine | needs shell and Docker rights on the node — `server_admin` territory, and on `oaapx01` a production machine |
| RFC-0015 declared endpoint | **standing and public**: it publishes the port on the node for everyone who can reach it, must be declared in the manifest, and "a granted endpoint does not pass through the gateway at all". A database port on a public interface is the wrong answer to "I need to look for an hour" |
| RFC-0033 destination (`kind: tcp`) | the wrong direction: an **app** reaches a **backend**. A person is not an instance and has no binding |
| RFC-0038 diagnosis window | read-only views the portal renders; no client of the person's own |

### 3. Why this is not RFC-0033

RFC-0033 D3 decided it and §8 repeated it: *"No VPN for people.
`oaap.net.remote-access` (WireGuard) remains the way a person reaches a
network; the connector never carries arbitrary traffic."* The threat
models differ in every row:

| | RFC-0033 destination | this RFC |
| --- | --- | --- |
| who travels | an app's request | a person's packets |
| who holds the credential | the platform (§1.3: the app never sees it) | the person (their key, their `.conf`, and the inner service's own password) |
| what decides reachability | the inner side's offer list (§2.2) | the instance boundary, enforced on the node |
| gateway in the path | always, per request | shape (b): per connection; shape (a): **not at all** |
| lifetime | until revoked | a TTL, always |

Past the gateway there is no login, no default deny and no per-request
audit (RFC-0002 is a promise about HTTP routes). That is why this RFC
has its own rules instead of borrowing RFC-0033's.

What the two share: the **laptop client** of RFC-0033 §3.5 (same binary,
opposite direction — there a local port is exposed outward, here an
inner port is pulled to the laptop), and the **TTL-plus-sweep**
mechanism of exposures (RFC-0033 §3.3), rehearsals (RFC-0030 D4) and
diagnosis windows (RFC-0038).

### 4. The capability has been waiting

RFC-0001 lists `oaap.net.remote-access` as capability #7, "secure
external access (e.g. WireGuard) for field devices"; RFC-0005 says its
spec "should include DNS push in WireGuard profiles"; the spec ROADMAP
lists it as open. No spec text exists. This RFC is the first part of
that capability — note that it is **not** the part RFC-0001 had in mind
(field devices), see D9.

## 1. The object

```json
{ "id": "a4c1e7",
  "instance": "<instance uuid>",          // RFC-0026: identity, not name
  "tenant": "<uuid>",                     // the instance's tenant, always
  "shape": "forward",                     // forward | wireguard
  "target": { "service": "db", "port": 5432 },   // forward only
  "holder": "<user uuid>",                // RFC-0040: the person it is for
  "opened_by": "<user uuid>", "opened": "…", "expires": "…",
  "state": "open" }                       // open | closed | expired
```

An access belongs to exactly one instance and therefore exactly one
tenant (RFC-0022). It is held by **one named person**; the platform
never issues an access to nobody in particular. It is not an instance
property, is not in the manifest, and is not carried by backup, restore
or promotion — an access is an act, not configuration.

## 2. Rule 1 — one instance network, enforced on the node

### 2.1 What "inside" may mean

A person inside an access may reach **the containers of that instance
on `oaap-inst-<instance>`** — and in shape (b) only one port of one of
them. Not:

- **the node itself.** On a Docker bridge network the gateway address
  (`172.x.y.1`) *is* the host; a peer that can reach it can reach every
  service the host listens on, including those bound only to internal
  addresses;
- **the node's LAN** (at Bernd's: the NAS, the Fritzbox);
- **other instance networks, link networks** (`oaap-link-<A>-<B>`,
  RFC-0016 Q3) **or `oaap_platform`** (identity and portal);
- **the gateway's own address on the instance network.** RFC-0016 puts
  the gateway on every instance network, and RFC-0033 §1.3 identifies
  the calling instance *by the network the request arrived on — "there
  is nobody else on it"*. A person inside that network would break that
  premise: they could call `…/destinations/<name>/` and have the
  platform add the instance's backend credential for them. The
  gateway's address on the instance network is therefore excluded from
  every access, in both shapes.

### 2.2 Why the peer's configuration is not the fence

A WireGuard peer's `AllowedIPs` says which destinations the **peer**
routes into the tunnel. It lives in a file on the peer, and the peer
can edit it. On the server side, `AllowedIPs` only says which *source*
address a peer may use (WireGuard's cryptokey routing); it says nothing
about where that peer's packets may go once they are decrypted — the
host routes them like any other packet, and with IP forwarding on (as
Docker requires) that includes every bridge network and the LAN.
Docker's own isolation chains separate bridge networks from each other,
not an extra interface from all of them.

So the fence is a **host firewall rule**, written by the platform when
the access opens and removed when it closes: packets from this peer's
tunnel address to this instance's subnet, minus the gateway's address
there, are accepted; everything else from the tunnel interface —
forwarded or addressed to the host — is dropped. Docker reserves the
`DOCKER-USER` chain for exactly such rules and evaluates it before its
own; the reference may equally use a dedicated nftables table. The
spec requires the effect, not the tool.

Shape (b) needs no firewall rule for this: the gateway itself dials the
target, and it dials exactly one container address and port. The fence
there is code, and §4 states what it must check.

### 2.3 What rule 1 does not cover

The instance's own containers still have egress (RFC-0016 Q4: on by
default). A person inside can use a container as a stepping stone only
by logging into it — which the inner service's own authentication
decides (§7). The access does not make that worse, and it does not
prevent it either.

## 3. Rule 2 — opened, time-boxed, swept, recorded

- **Opened on the instance object page** (portal, tab next to
  *Diagnose*): shape, for (b) service and port, duration, holder. For
  (a) the result is a `.conf` download and a QR code; for (b) the
  command line for the client.
- **Time-boxed.** The duration is chosen from a short list (D3). The
  remaining time is visible on the page. Close early is one button.
- **Ends by itself.** Expiry removes the WireGuard peer and its
  firewall rule (a) or closes the stream and rejects new ones (b). The
  sweep is the one RFC-0038 already has for diagnosis windows, "the
  same shape as the rehearsal sweep"; the host re-checks the requester's
  right on every action, because the spool is data, not trust (RFC-0038, host
  spool worker).
- **Recorded** in the tenant audit log (RFC-0022 §6): opened (who, for
  whom, instance, shape, target, until when), closed early (who),
  expired; for (b) each connection with start, end and bytes. An access
  a `server_admin` opens appears in the **tenant's** log, because
  "access by the operator is itself an event" (RFC-0022 §6). Contents
  never (D7).
- RFC-0030 D4's rule "an expiry may exist only on a rehearsal" is about
  deleting instances; an access is not an instance and deletes nothing.
  The rule stands.

## 4. Shape (b) — port forward through the gateway

```
 laptop                              node (oaapx01)
 ┌───────────────────────┐          ┌────────────────────────────────────────┐
 │ DBeaver → localhost:5432         │ gateway  /connect/forward               │
 │ oaap client forward ──HTTPS/WS──▶│  1. who? person's API key (RFC-0027)    │
 │   crm db:5432         │          │  2. open access for this holder,        │
 └───────────────────────┘          │     instance, service, port? not expired│
                                    │  3. dial oaap-app-crm-db:5432           │
                                    │     on oaap-inst-crm — nothing else     │
                                    └────────────────────────────────────────┘
```

- The client authenticates with the **person's own API key** (RFC-0027
  `key` method, tenant-bound) — the same credential RFC-0033 §3.5 gives
  the laptop client for exposures. The portal hands out no new secret.
- The gateway checks, per connection: the key's principal is the
  access's holder; the access is open and unexpired; the target is the
  one recorded. It then dials the service's container on the instance
  network (RFC-0016 container naming) and never anything else — not
  another container, not the gateway itself, not an address the client
  supplies.
- It carries **TCP only**. UDP services are shape (a).
- The gateway stays in the path: authentication, a default of "no
  access", and a per-connection record survive. What does not survive
  is anything above TCP — the gateway does not understand the Postgres
  protocol and sees no query.
- It runs on every node the client can reach over HTTPS: `oaapx01`
  directly, a LAN node from the LAN, and Bernd's node through
  whatever already carries his portal. No port forward, no UDP.

This is `kubectl port-forward` and `ssh -L` in OAAP's shape, and it is
the recommendation for the first build (D2).

## 5. Shape (a) — WireGuard peer into the instance network

- **The listener.** One UDP port on the node, one WireGuard interface.
  Kernel WireGuard means root on the host — the installer is root
  anyway, but it is a new standing listener. Fine on a public server
  like `oaapx01`; at Bernd's behind a Fritzbox it needs a port forward
  on the router; many corporate networks block outbound UDP entirely,
  and then shape (a) simply does not connect. Only nodes that opt in
  carry the listener (D4).
- **The peer.** Opening an access creates a key pair and a tunnel
  address, adds the peer to the interface, and writes the firewall rule
  of §2.2. The `.conf` contains the private key; it is shown once, like
  an API key (RFC-0027), and not stored (D10). **The file is a bearer
  credential**: whoever holds it until expiry is inside, and the
  platform cannot tell who that is. Shape (b) does not have this
  weakness — its credential is the person's own key.
- **What it records.** WireGuard knows, per peer, the latest handshake
  and bytes transferred; that is the available metadata, and it is
  coarser than (b)'s per-connection record.
- **Names.** Docker's embedded DNS answers only inside containers, so
  `db` does not resolve on the laptop by itself. RFC-0005 already
  expects the WireGuard profile to push the platform as DNS server; here
  it would have to answer the instance's service names for that peer
  and no other (D6). Until then the page lists service names with their
  current addresses — which change on every recreate (RFC-0016: the
  network outlives the container, the address does not).
- **Address collisions.** Docker bridge subnets come from private
  ranges (`172.16.0.0/12`, `192.168.0.0/16`) that home and office
  networks also use. If the laptop's own network overlaps the instance
  subnet, the tunnel route and the local route fight. The page must
  warn when the instance subnet is one of the common home ranges.
- **When it earns its cost.** Several services of one stack at once
  (a database, its admin UI, a broker), UDP protocols, tools that
  discover peers on their network. That is the case for a network
  rather than a door.

## 6. The two shapes side by side

| | (b) port forward | (a) WireGuard peer |
| --- | --- | --- |
| reaches | one port of one container | the instance network (minus the gateway) |
| transport | HTTPS / WebSocket through the gateway | UDP to a listener on the node |
| node needs | nothing new beyond the connect endpoint | kernel WireGuard, a UDP port, a firewall rule per peer |
| Fritzbox / corporate network | works | port forward needed / often blocked |
| credential | the person's API key | a `.conf` — bearer, shown once |
| fence | gateway code dials one target | host firewall rule |
| record | per connection, bytes | handshake and byte counters |
| laptop needs | the OAAP client (RFC-0033 §3.5) | the WireGuard app |
| TCP / UDP | TCP | both |

## 7. Once inside — the inner service's password is the only gate

After either shape lets a person through, the Postgres checks its own
password and nothing else. OAAP's roles, groups and gateway rules do not
exist from the database's point of view. For a wrapped stack that
password usually lives in the instance configuration as a
`secret: true` value — in the clear in the instance's environment file,
as CURRENT_STATE 179 measured and RFC-0033 §Motivation 2 recalls.

Therefore two things must be said and one must be decided:

- **An access opens the door; it does not introduce the person to the
  database.** The portal page states which configuration value holds
  the credential; who may read that value is unchanged by the access.
- **The database user is the app's user**, with the app's rights.
  Everything the person does happens under the app's name, and the
  database's own log cannot tell them apart. That is acceptable for the
  person who administers the instance; it is the reason access is not a
  thing to hand to outsiders casually (D1).
- **Whether the platform should ever hand over or mint credentials**
  (a temporary database user per access, product by product, in the
  shape of the connector contract RFC-0041 built
  for identity products) is D8.

## 8. Rehearsals

A rehearsal (RFC-0030) reaches nothing outward (D3 there), which makes
an access into it harmless *outward*. It is not harmless *inward*: a
rehearsal holds a full copy of production data. An access into a
rehearsal is therefore allowed on the same terms as one into production
— same right, same record, marked as a rehearsal in the log — not on
easier ones (D5). It is also the best place to use one: inspecting the
migrated schema before promotion is what rehearsals are for.

## 9. Security requirements

- **Default: no access.** No instance, no tenant and no node has an
  open access unless a person opened it.
- **One instance network, enforced on the node** (§2): a host firewall
  rule for (a), a single fixed dial target for (b). Never the host,
  never the LAN, never another instance's, link or platform network,
  never the gateway's address on the instance network.
- **One tenant.** An access belongs to the instance's tenant; a key
  from another tenant cannot use it; RFC-0022's sentence holds.
- **Always a TTL.** No access without an expiry, no extension beyond
  the maximum (D3). Expiry removes the peer and its rule, or closes the
  streams — immediately, by the sweep.
- **A named holder.** (b) checks the holder's key per connection. (a)
  cannot, and says so on the page: the `.conf` is a bearer credential.
- **Metadata always, payload never.** The audit log records opening,
  closing, expiry and, for (b), each connection; never contents.
- **The operator's access is visible to the tenant** (RFC-0022 §6).
- **The WireGuard listener exists only where a `server_admin` put it**,
  on the machine (RFC-0011 implementation note).

## 10. Non-goals (deliberate)

- **Not a site-to-site VPN.** Two networks are not joined; one person's
  device enters one instance network.
- **Not LAN access.** Reaching the NAS behind the node is the router's
  VPN (Bernd's Fritzbox already has WireGuard) or RFC-0033's connector.
- **Not a replacement for destinations.** An app that needs a backend
  gets a destination (RFC-0033), never an access.
- **No standing access, and none for apps.** An access is held by a
  person and ends. A permanent path into an instance network is either
  an RFC-0015 endpoint or an RFC-0016 link, both of which already have
  owners.
- **No protocol awareness.** The platform does not parse SQL, and does
  not claim a per-query audit it cannot deliver.
- **No field devices.** Bernd's tablets reaching the platform are a
  different case (D9).

## 11. Staging

1. **Port forward.** The access object, the portal card, the audit
   entries, the sweep; the `forward` verb in the RFC-0033 laptop client
   and the gateway's connect endpoint for it. Built after RFC-0033
   stage 3, which ships the client and the endpoint.
2. **WireGuard peer.** The node profile and listener, per-peer keys and
   firewall rules, the `.conf`/QR, handshake metadata, the collision
   warning.
3. **Names for peers** (D6) — the RFC-0005 DNS push, scoped to the
   instance.

## Decisions (open)

Each with a recommendation; none decided.

- **D1 — Who may open an access?** Options: only `server_admin`; also
  the `tenant_admin` of the instance's tenant. **Recommendation: both**,
  the RFC-0038 D2 rule ("whoever may administer the instance"). It is
  the tenant's data and their app; RFC-0022's table already gives
  `tenant_admin` install and remove of their instances, which is more.
  The holder may be the opener or another user of the same tenant,
  never someone outside it. A `server_admin`'s access lands in the
  tenant's log.
- **D2 — Both shapes, or one first?** **Recommendation: port forward
  first** (stage 1), WireGuard second. (b) covers "DBeaver on this one
  Postgres" with one door instead of a network, works behind a Fritzbox
  and corporate proxies, keeps the gateway in the path, and costs no
  new listener. (a) follows for multi-service and UDP cases.
- **D3 — Duration.** **Recommendation: choices 1, 8 and 24 hours,
  default 8** (a working day), maximum 24; no extension — opening again
  is a new act with a new audit entry, as RFC-0038 D2 decided for the
  diagnosis window. RFC-0033's exposure maximum of 7 days is too long
  for a door into a database.
- **D4 — Must the node or the tenant opt in?** **Recommendation: the
  WireGuard listener only on nodes with a profile** (proposal:
  `remote-access`), set on the machine by `oaap node add-profile`
  (RFC-0011). That fits RFC-0011's line — a profile gates platform
  behaviour (whether a UDP listener exists), not a person's access,
  which stays with roles. The port forward needs no profile: it rides
  the gateway like the diagnosis window does. No tenant switch; D1's
  role check is the gate.
- **D5 — Access into a rehearsal?** **Recommendation: yes, on the same
  terms as production**, marked in the log (§8).
- **D6 — Names for WireGuard peers.** **Recommendation: build it in
  stage 3**, as a platform resolver pushed in the `.conf` (RFC-0005)
  that answers only the instance's service names for that peer; until
  then the page lists names and current addresses. Not needed for (b).
- **D7 — What the audit log records.** **Recommendation: metadata
  only** — opened (who, for whom, instance, shape, target, until),
  closed early, expired; for (b) each connection with start, end and
  bytes; for (a) the last handshake and byte counters at close. Never
  payload, and no "trace" option: unlike RFC-0033 §2.4 the platform
  cannot see inside the protocol, so it should not pretend to offer it.
- **D8 — Credentials for the inner service.** Options: the platform
  hands over nothing and names where the value lives; it shows the
  instance's configured secret on the access page; it mints a temporary
  database user per access. **Recommendation: hand over nothing now**,
  point to the configuration field (§7); name per-access database users
  as the right later answer, built product by product in the connector
  shape of RFC-0041, when a real case asks.
- **D9 — Field devices (Bernd's tablets): standing, non-expiring
  access?** **Recommendation: out of this RFC**, a separate decision.
  RFC-0001 #7 and RFC-0005 describe devices reaching the **platform**
  (the gateway, per-app hostnames), not an instance network — a
  different fence, a standing credential, and a different threat model.
  Bernd's Fritzbox already provides WireGuard to his LAN today.
- **D10 — Who generates the WireGuard key pair?** Options: the node,
  shown once in the `.conf`/QR; the laptop, uploading only its public
  key. **Recommendation: the node generates, shows once, stores only
  the public key.** It is the only way the portal flow Jörg asked for
  („startbar aus dem Portal", a QR code for the app) works without a
  second tool; the private key's brief presence on the node is the
  price, and it is the same one RFC-0027 pays for API keys.

## Deutsche Zusammenfassung

**Worum es geht.** Gewrappte Dienste bringen mehrere Container mit —
zum Beispiel eine Datenbank, die nur die App selbst erreichen soll.
RFC-0016 hat das technisch sauber gemacht: Jede Instanz hat ihr eigenes
Docker-Netz (`oaap-inst-<name>`), darin stehen nur ihre Container und
das Gateway. Für die App ist das richtig; für den Menschen, der mal mit
DBeaver in diese Postgres schauen muss, heißt es heute: an die Maschine
setzen und Docker-Rechte haben. Deine Idee: ein VPN-Zugang in genau
dieses innere Netz, als Plattform-Fähigkeit, aus dem Portal startbar.

**Warum ein eigenes RFC und nicht RFC-0033.** Bei den Destinations
erreicht eine **App** ein Backend, die Plattform hält das Geheimnis,
jede Anfrage läuft über das Gateway. Hier betritt ein **Mensch** ein
Netz, hält seinen Schlüssel selbst, und seine Pakete gehen direkt an
die Datenbank — am Gateway vorbei, also ohne Anmeldung, ohne „alles
verboten, was nicht erlaubt ist", ohne Protokoll je Anfrage. Anderes
Bedrohungsbild, also eigene Regeln. Gemeinsam ist beiden der
Laptop-Client aus RFC-0033 Stufe 3 (dasselbe Programm, andere
Richtung) und der Mechanismus „läuft ab und wird weggeräumt".

**Das neue Objekt: ein Zugang.** Eine Person, eine Instanz, eine
begrenzte Zeit. Zwei Regeln tragen alles:

1. **Ein Zugang erreicht genau ein Instanznetz** — nie den Knoten
   selbst, nie das LAN, nie einen anderen Mandanten, und auch nicht die
   Adresse des Gateways in diesem Netz. Letzteres ist wichtig, weil
   RFC-0033 die aufrufende Instanz am Netz erkennt, aus dem eine
   Anfrage kommt („da ist sonst niemand"); ein Mensch im Netz könnte
   sonst die Destinations der Instanz samt hinterlegtem Passwort
   benutzen. Durchgesetzt wird das **vom Knoten**, per Firewall-Regel
   — nicht durch die Einstellung `AllowedIPs` in der WireGuard-Datei
   des Laptops. Die liegt beim Nutzer, er kann sie ändern; sie sagt
   nur, was **sein** Rechner in den Tunnel schickt, nicht, was der
   Server durchlässt.
2. **Ein Zugang wird bewusst geöffnet, läuft ab, wird weggeräumt und
   protokolliert.** Auf der Instanzseite „Zugang öffnen, 8 Stunden";
   im Audit-Log des Mandanten steht wer, für wen, welche Instanz, bis
   wann. Vorbild ist das Diagnose-Fenster aus RFC-0038.

**Zwei Formen.**

- **(b) Portweiterleitung** — wie `ssh -L` oder `kubectl
  port-forward`: Der Laptop-Client holt **einen Port eines Containers**
  auf `localhost` des Laptops, über HTTPS durch das Gateway. Kein UDP,
  keine Portfreigabe an der Fritzbox, geht durch Firmen-Proxys. Das
  Gateway prüft bei jeder Verbindung den persönlichen API-Schlüssel und
  wählt selbst das Ziel. Eine Tür statt eines Netzes.
- **(a) WireGuard** — eine `.conf`-Datei oder ein QR-Code für die
  WireGuard-App bringt den Laptop **ins Instanznetz**. Braucht einen
  UDP-Port am Knoten (auf `oaapx01` kein Problem, bei Bernd eine
  Portfreigabe, in vielen Firmennetzen gesperrt). Die Datei ist ein
  Inhaber-Schlüssel: Wer sie hat, ist drin. Sinnvoll, wenn man mehrere
  Dienste eines Stacks gleichzeitig braucht oder UDP.

**Ehrlich gesagt:** Ist jemand drin, prüft nur noch die Datenbank
selbst ihr Passwort. OAAP-Rollen gibt es dort nicht, und alles läuft
unter dem Datenbank-Benutzer der App. Wer das Passwort bekommt, ist
eine eigene Frage (D8).

**Offene Entscheidungen mit Empfehlung:**

- **D1** Wer darf öffnen? `server_admin` und `tenant_admin` des
  Mandanten der Instanz (wie beim Diagnose-Fenster); öffnet der
  Betreiber, sieht der Mandant es im Log.
- **D2** Portweiterleitung zuerst, WireGuard danach.
- **D3** Dauer 1, 8 oder 24 Stunden, Vorgabe 8, keine Verlängerung —
  neu öffnen ist ein neuer Vorgang.
- **D4** Den WireGuard-Port bekommen nur Knoten mit einem Profil
  (Vorschlag `remote-access`), gesetzt an der Maschine; die
  Portweiterleitung braucht keines.
- **D5** Zugang in eine Generalprobe: ja, aber zu denselben
  Bedingungen wie in Produktion — sie enthält eine Kopie der
  Produktivdaten.
- **D6** Namensauflösung für WireGuard-Nutzer (damit `db` statt einer
  IP-Adresse funktioniert) in Stufe 3.
- **D7** Das Log hält nur Metadaten fest, nie Inhalte.
- **D8** Zunächst kein Passwort-Übergeben durch die Plattform; die
  Seite nennt nur, wo es steht. Später vielleicht ein befristeter
  Datenbank-Benutzer je Zugang.
- **D9** Bernds Tablets (dauerhafter Zugang) gehören nicht hierher:
  Die wollen auf die Plattform, nicht in ein Instanznetz, und seine
  Fritzbox kann WireGuard schon.
- **D10** Der Knoten erzeugt den WireGuard-Schlüssel, zeigt ihn einmal
  und speichert nur die öffentliche Hälfte.

**Reihenfolge:** Gebaut wird nach RFC-0033 Stufe 3, weil dort der
Laptop-Client und der Verbindungsendpunkt am Gateway entstehen.
