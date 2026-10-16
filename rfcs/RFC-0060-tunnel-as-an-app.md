# RFC-0060: A Tunnel as an App — Reaching a Foreign Network Through Its Own Door

- **Status:** **Accepted (2026-10-16)** — Jörg took D1–D8 as
  recommended. Nothing built. The Copilot measurement (§3.1) runs in
  parallel, by Jörg, against the existing gateway on `oaap-test`.
- **Date:** 2026-10-16
- **Authors:** Jörg (the case: a model endpoint on somebody else's
  machine behind somebody else's OpenVPN, to be offered to a customer
  through our AI gateway), Claude (analysis, write-up)
- **Depends on:** RFC-0033 (destinations, the connector, `via`),
  RFC-0023 / `oaap.ai.gateway` (chains, the traffic light), RFC-0016
  (one network per instance), RFC-0030 (a rehearsal reaches nothing
  outward), RFC-0044 (what a VPN for *people* is — and that this is not
  one), `oaap.apps.runtime` 2.20 (`shm`: a declared need applied by the
  one function that builds containers)
- **Changes:** `oaap.apps.runtime` (one declared service need: `tun`),
  `oaap.net.destinations` (one target kind: `through`), a store app
  `vpn-client` (OpenVPN first), later `oaap.ai.gateway` 0.3 (a
  destination as supplier — separate, RFC-0023 stage 3)
- **Language:** English per ADR-0003; German summary at the end.

## Summary

Everything OAAP can reach today it reaches either directly (a
`direct` destination), or through a tunnel **between two OAAP nodes**
(`via`, the connector), or by letting a **person** in (RFC-0044). What
it cannot do is reach a system that sits **behind a foreign VPN
server** — a door we do not own, with credentials somebody handed us.

The first real case: a retired gaming PC that is **not Jörg's and not an
OAAP node**, reachable only through its owner's OpenVPN, serving an
OpenAI-compatible model endpoint with an API key of its own. Jörg wants
to offer that model to a customer through our AI gateway, so that the
customer's Copilot talks to our key, our books and our traffic light —
and never to the gaming PC.

This RFC adds the missing piece in the form that keeps every existing
rule:

> **The tunnel is an app. What lies behind it is a destination.**

An ordinary store app holds the VPN client in **its own container
network**, for which the runtime grants exactly one new thing — a
`/dev/net/tun` device and the capability to configure it, declared in
the manifest and asked for once at install (D1). Nothing on the host
changes; no other container sees the tunnel. Addresses behind the
tunnel become **destinations** with a new target kind `through`
(D4): the operator binds a consumer app to such a destination as to any
other, the platform adds the credential (the foreign API key), and the
consumer app cannot tell a tunnelled target from a direct one — the
boundary RFC-0033 §8 demands.

One tunnel, any number of consumers, with binding, revocation, audit
and the rehearsal rule carried over unchanged. Not a platform feature
"OAAP can VPN"; one app and one target kind.

## 1. The case, and why the existing pieces do not cover it

### 1.1 What exists

| Way outward | Who owns the far door | Built |
| --- | --- | --- |
| `direct` destination | anybody; the target is public or on the LAN | 0.1.128 |
| `via` destination over the connector | **an OAAP node** on the inner side dials out | 0.1.129 |
| exposure | an OAAP node or a laptop client exposes *inward* | 0.1.130 |
| remote access (RFC-0044) | a **person** comes into an instance network | 0.1.137 |

A foreign system behind a foreign VPN server fits none: there is no
OAAP node on the far side to run a connector, the door is not ours to
replace, and nothing in the list lets a *node* become a VPN *client*.

### 1.2 The chain Jörg wants

```text
customer's cloud desktop (Copilot, key K1 issued by us)
   │  https://ai.oaap.joomp.de/v1 — alias `code`, light yellow
   ▼
AI gateway on oaapx01 — issues K1, keeps the books
   │  supplier = via-destination through the connector
   ▼
inner node at home (raspberrypi / oaap-test) — dials out to oaapx01
   AI gateway there: supplier = destination `gaming`, target `through`
   │  the platform adds K3 (the gaming PC's own key); the app never sees it
   ▼
vpn-client instance — holds the OpenVPN tunnel in its own network
   │  OpenVPN
   ▼
gaming PC of an acquaintance — OpenAI-compatible endpoint
```

Three organisations (customer, Jörg, the owner of the PC), three hops,
and every hop keeps its own books (RFC-0023 §5). The foreign VPN
credentials and K3 live on the inner node only; oaapx01 knows an offer
name (RFC-0033 D2) — which is exactly why the VPN client goes on the
inner node and not on the internet-facing one, even if the latter could
reach the VPN server directly.

### 1.3 Two ways that were considered and rejected

- **OpenVPN on the host of the inner node.** Works tonight. But it puts
  a route on the host, runs as root outside every record, is in no
  backup and no instance view, and the platform cannot say which app
  uses it. The first thing that goes wrong is invisible.
- **A VPN sidecar inside the AI gateway's instance.** Shorter, and the
  wrong boundary: a tunnel that exists only for one app is the second
  way to the same place that carries none of the destination rules
  (binding, revocation, audit, rehearsal). The next case — an app that
  needs a customer's ERP behind the customer's VPN — would be a new
  build instead of the same one.

## 2. Proposal

### 2.1 Runtime: one declared need, `tun` (D1, D2)

`oaap.apps.runtime`, manifest 0.8: a service MAY declare

```yaml
services:
  vpn:
    image: ...
    port: 8080
    tun: true
```

- **What it grants, exactly:** the device `/dev/net/tun` and the
  capability `NET_ADMIN` for **that container**. Nothing else: no
  `privileged`, no host network, no `SYS_ADMIN`, no sysctl on the host.
  The container stays on its instance network alone (RFC-0016).
- **Applied like `shm`** (runtime 2.20): recorded in the service's
  registry record at install, added by the one function that builds
  containers, at every (re)creation, through every door. A record that
  does not parse yields a container **without** the grant, never a
  failing `docker run`.
- **Asked for once at install**, the way a `public` route is: the
  install says what the app will be able to do (*"this service may
  create a network tunnel inside its own container"*) and a
  `server_admin` confirms. A `tenant_admin` cannot install an app that
  declares `tun` (D2) — a tunnel is a door the node's operator must
  know about, and today a tenant cannot author destination targets for
  the same reason (`oaap.net.destinations` 2.7).
- **What `NET_ADMIN` lets the app do, said plainly:** change routes,
  addresses and packet filters **inside its own network namespace**.
  It cannot touch the host's or another container's. That is the whole
  blast radius, and §4 names what the app must therefore promise.
- **Not in a rehearsal.** A rehearsal reaches nothing outward
  (RFC-0030, runtime 2.15). A service with `tun` in a rehearsal is
  created **without** the grant and the app must say so on its page
  rather than retry (D6).

### 2.2 The app: `vpn-client` (D3)

An ordinary store app, OpenVPN first, WireGuard as a second variant of
the same app later (stage 3). One service, `tun: true`, configuration
by declared variables:

```text
VPN_KIND        openvpn
VPN_CONFIG      the .ovpn file, secret           (multi-line, as RFC-0041 did for realm files)
VPN_AUTH        user:password or key material, secret, optional
VPN_TARGETS     one line per name reachable behind the tunnel
  gaming = http://10.8.0.5:11434
```

The app does three things and nothing else:

1. **Holds the tunnel up** and shows its state (connected since, last
   error, remote address) on its own page and in `/healthz`. Health is
   `ok` only while the tunnel is up — the platform's health view then
   says what a consumer will get.
2. **Trusts the far side for nothing.** It ignores every route, DNS
   server and option the VPN server pushes (OpenVPN: `route-nopull` and
   an explicit `route` per target network; `pull-filter ignore` for the
   rest). A foreign VPN server is a foreign authority; what it pushes is
   data. The container's default route and resolver stay Docker's.
3. **Serves named targets at a path:** `http://<service>:8080/t/<name>/…`
   is forwarded to the address `VPN_TARGETS` names, with the path
   appended and the target's own host as `Host`. Plain reverse proxy,
   streaming passed through untouched, no credential of its own — the
   credential is the destination's and arrives from the gateway.

The app **does not forward packets** between its interfaces
(`ip_forward` stays off, and the app's own filter drops anything
arriving from the tunnel that is not a reply to its own connections).
A VPN server that can see our container must see **one container with
one proxy port and nothing behind it** (§4).

### 2.3 Destinations: target kind `through` (D4)

`oaap.net.destinations` 2.1 gains a third target:

```text
target: {through: "<instance>/<name>"}
CLI:    --target through:<instance>/<name>
```

- `<instance>` MUST be an instance **of the destination's tenant** whose
  manifest declares a service with `tun: true`; `<name>` is a target
  name the app serves. Another tenant's instance is answered as one that
  does not exist (`oaap.core.tenant` 2.3).
- **The gateway handles the call exactly as for `direct`**
  (`oaap.net.destinations` 2.3: caller by network, identity headers
  stripped, the destination's credential added) and forwards to
  `http://<tunnel container>:<port>/t/<name>/…` on the tunnel instance's
  own network — which the gateway is a member of (runtime 2.11). No
  new listener, no new key: the one piece of the platform that may
  name a container is the gateway, and this is the gateway doing so by
  rule, not an operator typing a container name into `direct`.
- **The consumer app's variable and call do not change.** An app MUST
  NOT be able to tell a `through` target from a `direct` or `via` one
  (RFC-0033 §8).
- `through` is for `kind: http` only, like `via` in 0.2. A TCP target
  behind a tunnel waits for the same handover design `via` is waiting
  for.
- A tunnel instance that is **absent, asleep (RFC-0059 standby) or
  unhealthy** answers **502 with a sentence** naming the instance — the
  answer a disconnected connector tunnel gets. Removing a tunnel
  instance that still has `through` destinations is refused and names
  them, like removing a bound destination is.

**Why the address lives in the app and the credential in the
platform.** The app knows *where* (an address inside a network only it
can see; nothing secret about `10.8.0.5`). The platform knows *with
what* (the gaming PC's API key, stored root-only, never in a container,
`oaap.net.destinations` 2.5). Two owners, two facts, and the rule "the
app never holds the credential" (RFC-0033 D1) is kept by construction
for the consumer **and** for the tunnel app.

### 2.4 The AI gateway on top (RFC-0023 stage 3, separate build)

Not this RFC's change, but the reason it exists, so the fit is written
down:

- `oaap.ai.gateway` 0.3: a supplier MAY be **a bound destination**
  (`supplier=destination:gaming`) instead of a URL plus a key line. The
  gateway then calls `OAAP_DESTINATION_GAMING_URL` and holds no
  upstream key at all — better than 0.2, where the supplier key sits
  in the app's secret environment.
- **The light is declared by the operator**, because the gaming PC is
  no OAAP gateway and reports none: without a declaration the supplier
  is `red` (the README's rule), and Jörg sets `yellow` with the
  agreement as the reason. For the customer the hardware is a third
  party's; the request for permission says so in one sentence.
- Chaining across the connector (inner node → oaapx01) is the stage 3
  proof RFC-0023 has been waiting for since August: oaapx01's supplier
  is a `via` destination to the inner node's gateway, which in turn
  draws through the tunnel. Each layer issues its own keys and keeps
  its own books.

## 3. What to measure before anybody promises anything

1. **Copilot against the existing gateway on `oaap-test`** — VS Code
   and Eclipse: which endpoint type, does the key travel, do streaming
   and `tools`/`tool_calls` pass our relay untouched. No new code
   needed; decides whether an Ollama-shaped façade is ever required.
2. **A `tun` container on a real node:** the grant arrives through every
   door (install, config save, restart, update), and a container
   without `tun: true` has neither the device nor the capability.
3. **From the far side of the tunnel:** only the proxy port answers;
   nothing on the instance network and nothing on the host is reachable
   through the container. This is the measurement that justifies
   `NET_ADMIN` — a counter that stays at zero proves nothing
   (2026-09-27 lesson), so the probe must try and be refused.
4. **Pushed routes and DNS are ignored:** a VPN server configured to
   push a default route and a resolver changes neither inside the
   container.
5. **Streaming through three hops:** a completion through oaapx01 →
   connector → tunnel → gaming PC, token by token, with the latency
   written down. Chain length is the consumer's trade-off (RFC-0023
   A1) — but only if somebody measured it.

## 4. Security requirements

- **The grant is the manifest's and the operator's, never the
  tenant's.** `tun` is declared by the author, confirmed by a
  `server_admin` at install, recorded, and applied by one function.
- **Nothing on the host changes.** No route, no interface, no sysctl,
  no capability outside the one container.
- **The tunnel carries only what a destination asked for.** The app
  forwards no packets, accepts no pushed routes or resolvers, and
  serves no target `VPN_TARGETS` does not name. The connector's
  non-goal "never carries arbitrary traffic" (RFC-0033 §8) holds here
  too.
- **Whatever joins the tunnel instance's network acts as that
  instance** (`oaap.net.destinations` §4). The far side of the tunnel
  is *not* on that network — it is behind the container's own
  interface, and the container must keep it there (§2.2).
- **The foreign credential never reaches a container.** It is the
  destination's secret, added by the gateway. The tunnel app sees the
  request with the header already in it and forwards it; it stores
  nothing, logs no header, and — like the AI gateway — never a body.
- **A rehearsal gets no tunnel** (D6) and, as everywhere, no bindings.
- **Known limit:** `NET_ADMIN` inside the container is a promise the
  app keeps, not one the platform enforces. The platform enforces the
  namespace boundary; the app's image is ours and measured (§3.3).
  A third-party image declaring `tun` deserves the install question
  twice as much — which is why the question exists.

## 5. Non-goals (deliberate)

- **No VPN server.** OAAP does not become somebody's VPN endpoint;
  inbound for people is RFC-0044, inbound for nodes is the connector.
- **No tunnel for people, no tunnel for arbitrary apps' traffic.**
  Only named HTTP targets behind a bound destination.
- **No TCP through the tunnel in stage 1** — same reason and same wait
  as `via`.
- **No mesh, no discovery, no failover across tunnels.**
- **No change to consumer manifests** beyond a declared need.

## 6. Staging

0. **`tun` in the runtime** — manifest field, record, one function,
   install question, conformance test (§3.2). Small; the `shm` build is
   the template. **Built 2026-10-16** (`oaap.apps.runtime` 0.2.42 §2.23,
   test 59; reference 0.1.197, `test/test_service_tun.py`): the question
   is the CLI flag `--confirm-tun`; every other door is refused for a
   first grant until stage 4 brings it to the portal. §3.2 on a real
   node not yet measured.
1. **`vpn-client` (OpenVPN) + `through`** — the app, the target kind,
   the 502 rule, tests 1–4 of §7. Measured on `oaap-test` against the
   real gaming PC.
2. **The chain** — AI gateway supplier = destination (RFC-0023 stage 3,
   `oaap.ai.gateway` 0.3), connector inner node → oaapx01, §3.5
   measured. Then the request to the customer, with the numbers.
3. **WireGuard variant** of the same app — same `tun`, same proxy,
   different client.
4. **Portal:** tunnel state on the instance page; `through` offered in
   the destination form.

## Decisions (Jörg, 2026-10-16 — all eight as recommended)

- **D1 — one declared need `tun`, granting `/dev/net/tun` + `NET_ADMIN`
  to the one container; nothing else, nothing on the host.**
  Recommended. The alternative — a generic `capabilities:` list in the
  manifest — is a plugin architecture before its second case.
- **D2 — only a `server_admin` installs an app that declares `tun`;
  the install asks once.** Recommended. Same reasoning as destination
  targets (2.7): a door the node's operator must know about.
- **D3 — the tunnel is a store app, OpenVPN first; one container that
  holds the tunnel and serves named targets.** Recommended over a
  platform service: it is an ordinary instance with record, backup
  posture, health, standby and audit for free.
- **D4 — a third target kind `through: <instance>/<name>`; the gateway
  forwards to the tunnel container on that instance's network.**
  Recommended. The alternative (the app as a generic forward proxy,
  absolute-URI requests) keeps the address out of the app but needs a
  new gateway path and a second way to name targets.
- **D5 — the address behind the tunnel is the app's configuration; the
  credential is the destination's.** Recommended (§2.3, last
  paragraph).
- **D6 — a rehearsal gets no `tun`; the app says so instead of
  retrying.** Recommended; RFC-0030 D3 without exception here, because
  an exception would need the foreign credential in a rehearsal.
- **D7 — the VPN client lives on an inner node, not on oaapx01, for
  Jörg's case.** Recommended: the foreign credentials stay at home,
  oaapx01 sees an offer name. The third hop is the price and is
  measured (§3.5) before the customer hears a number.
- **D8 — the AI gateway learns "a destination as supplier" in 0.3,
  and the light of a non-OAAP supplier is declared by the operator,
  `red` by default.** Recommended; belongs to RFC-0023 stage 3 and is
  written here only so the two builds meet.

## Zusammenfassung auf Deutsch

**Der Fall.** Ein ausrangierter Gaming-PC — nicht Jörgs, kein
OAAP-Knoten — stellt hinter dem OpenVPN seines Besitzers einen
OpenAI-kompatiblen Modell-Endpunkt bereit; wir haben nur den
VPN-Zugang und einen API-Key. Jörg will dieses Modell einem Kunden
über unser KI-Gateway anbieten: Der Copilot des Kunden spricht mit
**unserem** Schlüssel, **unserer** Buchführung und **unserer** Ampel,
nie mit dem Gaming-PC.

**Was fehlt.** OAAP erreicht heute Ziele direkt, über den Konnektor
zwischen **zwei OAAP-Knoten** (`via`), oder es lässt einen **Menschen**
herein (RFC-0044). Ein System hinter einer **fremden VPN-Tür** erreicht
es nicht — nichts macht einen Knoten zum VPN-*Client*.

**Der Vorschlag in einem Satz:** **Der Tunnel ist eine App, und was
dahinter liegt, ist eine Destination.**

1. **Laufzeit, eine neue erklärte Anforderung `tun`** (D1): Der Dienst
   bekommt `/dev/net/tun` und `NET_ADMIN` — nur dieser eine Container,
   kein `privileged`, kein Host-Netz, keine Route auf dem Wirt. Gebaut
   wie `shm`: im Manifest erklärt, im Datensatz vermerkt, von der einen
   Funktion gesetzt, die Container baut. Beim Installieren fragt die
   Plattform einmal nach, und nur ein `server_admin` darf so eine App
   installieren (D2). In einer Generalprobe gibt es den Tunnel nicht
   (D6).
2. **Store-App `vpn-client`** (D3), erst OpenVPN, später WireGuard als
   Variante: hält den Tunnel in ihrem eigenen Container-Netz, zeigt den
   Zustand, **traut der Gegenseite nichts** (gepushte Routen und
   DNS-Server werden verworfen — ein fremder VPN-Server ist eine fremde
   Autorität), leitet keine Pakete weiter und bedient benannte Ziele
   unter `/t/<name>/…` als schlichter Reverse-Proxy.
3. **Destination mit Zielart `through: <instanz>/<name>`** (D4): Das
   Gateway behandelt den Aufruf genau wie bei `direct` — Aufrufer am
   Netz erkannt, Identitäts-Kopfzeilen entfernt, Zugangsdaten der
   Destination ergänzt — und reicht ihn an den Tunnel-Container weiter.
   Die Verbraucher-App merkt keinen Unterschied zu `direct` oder `via`
   (RFC-0033 §8). **Die Adresse hinter dem Tunnel steht in der App, der
   Schlüssel des Gaming-PCs in der Plattform** (D5) — die App hält nie
   die Zugangsdaten, auch die Tunnel-App nicht.

**Die Kette:** CloudPC des Kunden (K1) → Gateway auf oaapx01 (gibt K1
aus, führt Buch) → `via` über den Konnektor → innerer Knoten zu Hause
(Gateway dort: Bezugsquelle = Destination `gaming`, Plattform ergänzt
K3) → `vpn-client` → OpenVPN → Gaming-PC. Drei Organisationen, drei
Hops, jeder führt eigene Bücher. **Der VPN-Client gehört auf den
inneren Knoten** (D7): Die fremden Zugangsdaten bleiben zu Hause,
oaapx01 kennt nur einen Angebotsnamen. Der dritte Hop ist der Preis —
und er wird gemessen, bevor der Kunde eine Zahl hört.

**Ampel:** Der Gaming-PC meldet keine Farbe, also erklärt sie der
Betreiber — ohne Angabe rot, Jörg setzt gelb mit der Vereinbarung als
Grund. Für den Kunden ist es Hardware eines Dritten; der Antrag sagt
das in einem Satz.

**Zwei verworfene Wege:** OpenVPN auf dem Wirt (funktioniert heute
Abend, ist aber unsichtbar: Route auf dem Wirt, root, kein Datensatz,
keine Sicherung) und ein Sidecar im KI-Gateway (kürzer, aber die
falsche Grenze — der zweite Weg zum selben Ort, der die
Destination-Regeln nicht trägt; der nächste Fall „ERP des Kunden hinter
dessen VPN" wäre ein neuer Bau statt derselbe).

**Messen, bevor versprochen wird** (§3): Copilot gegen das bestehende
Gateway auf oaap-test (VS Code und Eclipse — welcher Endpunkt-Typ,
geht der Schlüssel mit, kommen Streaming und Tool-Aufrufe durch); der
`tun`-Container durch jede Tür; **von der Gegenseite des Tunnels aus**
antwortet nur der Proxy-Port und nichts dahinter (die Messung, die
`NET_ADMIN` rechtfertigt — ein Zähler auf null beweist nichts, die
Sonde muss es versuchen und abgewiesen werden); gepushte Routen
bleiben wirkungslos; Streaming über drei Hops mit Latenz.

**Stufen:** 0 `tun` in der Laufzeit → 1 `vpn-client` + `through`,
gemessen am echten Gaming-PC → 2 die Kette (KI-Gateway 0.3 mit
Destination als Bezugsquelle, RFC-0023 Stufe 3, Konnektor zu oaapx01),
dann der Antrag an den Kunden mit Zahlen → 3 WireGuard-Variante → 4
Portal.

**Acht Entscheidungen** (D1–D8) hat Jörg am 16.10. wie empfohlen
getroffen. Gebaut ist nichts; die Copilot-Messung (§3.1) macht Jörg
parallel gegen das bestehende Gateway auf oaap-test.
