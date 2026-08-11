# RFC-0015: Declared Endpoints — What the Gateway Cannot Carry

- **Status:** Accepted (2026-08-11) — all five questions decided on the
  day the RFC was written
- **Date:** 2026-08-11
- **Authors:** Claude (proposal), Jörg (direction: "a meeting tool with
  streaming, MQTT will come")
- **Depends on:** RFC-0002 (security-first access model), RFC-0004
  (manifest), RFC-0005 (addressing), RFC-0006 (edge node), RFC-0008
  (`server_admin`), RFC-0011 (node profiles)
- **Triggered by:** the bdt-hub letter of 2026-08-10 (TURN for WebRTC
  voice) and Jörg's follow-up the next day

## Summary

Everything an OAAP app can be reached by today is HTTP, because the
gateway is the only entry point and the gateway speaks HTTP. That was
the right constraint and it bought us the guarantee RFC-0002 exists
for. It also means the platform cannot host a media server, a native
MQTT broker, or anything else that does not speak HTTP — and two of
those are now on the roadmap rather than hypothetical.

This RFC proposes the smallest change that unblocks them: an app may
**declare** that it needs one non-HTTP port; the platform publishes it
only after a `server_admin` **grants** it per instance; and the grant
says plainly which guarantees stop at that port. Declaration is not
publication. The default stays deny.

## Motivation

Three unrelated needs turn out to be the same missing concept.

1. **Media.** Jörg is building a meeting tool with streaming, audio
   included. Real-time media does not travel over HTTP.
2. **Relay for peer-to-peer.** bdt-hub asked (2026-08-10) whether the
   platform could provide TURN for WebRTC voice. The answer today is
   no, and §"What is blocked" explains why that no is total rather
   than a matter of priority.
3. **Devices.** MQTT is named as coming. Sensors, PLCs and ESP32-class
   hardware speak MQTT over TCP 1883; they do not speak HTTP and
   cannot be taught to.

There is also a fourth motivation, which is that the platform already
admits this gap in writing. The compose converter refuses any service
whose port is not HTTP, with the words *"the gateway routes HTTP(S)
only; TCP passthrough is future work"* (`appctl.py`, `NON_HTTP_PORTS`
— and that set literally starts with MQTT's 1883). We have been
deferring this since RFC-0004.

## What is blocked today, precisely

Worth stating exactly, because the height of the wall determines the
shape of the door.

- **The gateway is the only published surface.** `oaap.core.gateway`
  0.2.3: *"Additional ports an app opens are never published."*
- **No app container publishes a host port at all.** Instances are
  started with `--network oaap_default` and no `-p` whatsoever
  (`appctl.py`, `start_instance_container`). The gateway alone
  publishes ports: 80, 443, and the range 8100–8199 it hands out as
  per-instance LAN listeners.
- **The manifest has no field for it.** The app schema knows `routes`,
  `storage`, `config`, `health`, `placement` — there is no place where
  an app could even *say* "I need a UDP port".
- **The edge cannot help.** RFC-0006 multiplexes several platforms
  behind one port forward by reading the **hostname**. A UDP packet
  carries none. The mechanism that solved "many services, one public
  address" for us is built on HTTP and does not extend.
- **The router is the hard floor.** One line, one forward of 80/443 to
  one node. Every additional published port is a manual act on
  hardware the platform does not control.

## Three findings that make the problem smaller than it looks

Before proposing anything, three things shrink the scope — and the
third one is the reason this RFC is worth writing now rather than
building a TURN service.

**1. WebSocket already covers more than we assumed.** Anything that
can ride an HTTP upgrade goes through the gateway today, *with*
identity attached: signalling, data channels, presence — and **MQTT
over WebSocket**, which Mosquitto speaks natively and which is the
normal case for browser and JavaScript clients. This only became
genuinely true on 2026-08-08, when the `forward_auth` upgrade-header
bug was fixed; before that, no authenticated WebSocket worked at all.
So the raw port is not "the MQTT solution" — it is the solution for
devices that cannot speak HTTP. Browser clients are better served by
the gateway, because the gateway brings the identity with them.

**2. An SFU makes the TURN question moot.** TURN is needed because two
browsers behind NAT cannot find each other. A media server has a
public address, so clients connect **to it** — an outbound connection,
which traverses every NAT by construction. An SFU is therefore the
media router *and* the NAT answer in one component, replacing both the
relay and the mesh. It also replaces quadratic scaling with linear:
mesh costs each participant N−1 connections, and a relayed mesh costs
the relay N·(N−1) streams.

**3. A modern SFU needs one port, not a range.** The classic objection
to hosting media is the RFC 5766 relay range, 49152–65535. Current
SFUs (LiveKit and comparable) multiplex all sessions over a **single**
UDP port, with a TCP fallback for restrictive networks. One declared
port is a proposal; sixteen thousand is not. This is what changes the
answer from "absurd" to "bounded".

Together: the thing Jörg needs (media) and the thing bdt-hub asked for
(TURN) collapse into **one** capability, and that capability needs
**one** port.

## Proposal

### The manifest may declare an endpoint

Alongside `routes`, an app may declare endpoints:

```yaml
endpoints:
  - name: media
    protocol: udp              # udp | tcp
    container_port: 7881
    reason: >
      WebRTC media. Participants authenticate against the app's own
      session tokens; the port carries SRTP only.
    fixed_port: false
```

`reason` is mandatory and is shown to the operator **verbatim** at
grant time. It is the app author's statement of who is let in and how
the app authenticates them — the same role the store's `publisher`
field plays, and for the same reason: the platform cannot verify it,
so it must at least name who is claiming it.

### Declaration is not publication

Nothing is published until a `server_admin` grants it **per instance**:

```text
oaap app endpoint list  <instance>
oaap app endpoint allow <instance> <name>
oaap app endpoint deny  <instance> <name>
```

plus a card on the instance object page, like configuration (2.8) and
throttling (RFC-0010) before it. Default is denied. This keeps
RFC-0002's promise intact word for word — *"there is no way to deploy
an app that is accidentally open to the network"* — because the act
that opens it is the operator's, not the app's.

The shape is deliberately the one we have used twice already: the app
declares, the operator decides, the default is off (visibility groups,
RFC-0007; expected node profiles, RFC-0011).

### What the platform stops guaranteeing — said out loud

On an HTTP route the gateway guarantees authentication, role checks,
identity headers apps can trust, throttling, and an access log. **On a
granted endpoint it guarantees none of these.** Traffic reaches the
container untouched.

The grant dialog must say exactly that, in the operator's language,
and require confirmation. This is not a new kind of compromise — it is
the `public` route (Forgejo's git paths, bdt-hub's API) one notch
further, and it should be named as such rather than dressed up. The
difference worth stating: a `public` route still passes through the
gateway, so it still gets throttling, logging, and header stripping. A
granted endpoint does not pass through the gateway at all.

### The platform assigns the port

The app says it needs a port; the platform picks it, from a second
reserved range beside 8100–8199, and tells the app through the
existing env mechanism. Apps do not choose their public port, exactly
as they do not choose their LAN listener today.

**Exception:** protocols whose port is part of the protocol — MQTT
1883, TURN 3478. Those must be requested as `fixed_port: true`, may
collide with another instance, and are refused with a clear message
when they do. The exception is narrow on purpose: a fixed port must be
unique across everything behind the same router, not just on the node.

### It is node-local, and that must be printed

A granted endpoint is reachable **only** on the node holding the port
forward. The edge cannot forward it. The grant output must say so:

```text
bdt-meet:media  ->  udp 8401 on oaap-demo (10.10.10.75)
This address is node-local. The edge cannot forward it, and a
restore on another machine will not bring it along.
```

Growth path, deliberately **not** part of this RFC: for TLS-wrapped
protocols (MQTTS, TURNS) the edge could route by **SNI**, which
restores name-based multiplexing without decrypting — but it needs a
layer-4 module our Caddy build does not have. Everything else would
have to be port-based, which makes the port part of the public address
(`meet.example.de:8401`) and demands fleet-wide unique allocation.
Both are real; neither is needed for one media service.

### The router stops being invisible

Two additions, because the failure mode here is silent — a forgotten
forward looks exactly like a broken app:

1. The platform generates the exact list of forwards the operator must
   create (`UDP 8401 → 10.10.10.75`), shown at grant time and on the
   health page.
2. The health page reports whether the port is actually reachable from
   outside — the same shape as the DNS watchdog decided in RFC-0009
   (the node asks about itself), with the same price: it requires
   asking something outside the house.

### Backup and restore

The line drawn in RFC-0011 applies unchanged. The **grant** belongs to
the service and moves with it. The **port assignment** and the router
forward belong to the machine and stay behind. A restore reports both:
"this instance has a granted endpoint; it has no port here yet and no
forward exists."

## Sizing: what a home connection actually carries

Relevant to Jörg's product decision, and cheap to compute.

An SFU receives one stream per participant and sends N−1 to each, so
server-side cost is N in, N·(N−1) out.

| Participants | Audio only (~40 kbit/s) | With video (~1 Mbit/s) |
| --- | --- | --- |
| 5 | 0.2 Mbit in / 0.8 Mbit out | 5 Mbit in / 20 Mbit out |
| 10 | 0.4 Mbit in / 3.6 Mbit out | 10 Mbit in / 90 Mbit out |

**Audio meetings on a domestic VDSL line are realistic** — 3.6 Mbit/s
upstream for ten people fits comfortably. **Video is not**: 90 Mbit/s
upstream does not exist on that line, and simulcast improves the
constant, not the order of magnitude.

The conclusion is about location, not software: the same app on a node
with real upstream carries video. This is precisely the "node at a
hoster" case from the fleet-type list of 2026-08-06.

## Staged plan

- **Stage 0 — today, no change.** Everything that fits in a WebSocket
  already works, with identity: signalling, data channels, presence,
  MQTT over WebSocket for browser clients.
- **Stage 1 — this RFC.** One declared, operator-granted endpoint per
  instance. Enough for an SFU, and enough for a native MQTT broker.
  This is where Jörg's meeting tool gets built, and it retires the
  TURN question rather than answering it.
- **Stage 2 — later, if it hurts.** Edge forwarding for endpoints (SNI
  for TLS protocols, port-based otherwise), reachability watchdog,
  generated router instructions.
- **Stage 3 — only on a second asker.** A media or relay service as a
  shared platform capability rather than an app. Same rule we applied
  to runtime secrets in RFC-0013: build the general thing when a
  second application asks for it, not in anticipation of one.

## What this deliberately does not do

- **No TCP/UDP proxying in the gateway.** The gateway stays an HTTP
  component. A granted endpoint bypasses it entirely — which is worse
  in guarantees and much better in honesty than a half-proxy that
  looks like the gateway and protects nothing.
- **No identity on raw ports.** There is no credible way to inject a
  verified identity into an SRTP or MQTT stream from outside the app.
  Pretending otherwise is how the `public` route would have been sold
  if we had been careless with it.
- **No second entry point for HTTP.** Anything that can speak HTTP
  must keep going through the gateway. The endpoint is for protocols
  that cannot, not for apps that would rather not.

## Open questions

1. **One endpoint per instance, or several?** Recommendation: exactly
   one, a visible limit rather than a hidden one — the same reasoning
   as the three secret slots in the store editor. A second asker is
   then the evidence, not a guess.
2. **May an app demand a fixed port (1883, 3478)?** Recommendation:
   yes, but only with explicit confirmation, because it can collide
   and must be unique behind the whole router.
3. **Does granting require a node profile as well as `server_admin`?**
   Recommendation: yes — a new profile (working name `exposed`), so a
   customer appliance in a workshop network does not carry the
   capability at all. Consistent with RFC-0011's own reasoning.
4. **Should the platform actively test outside reachability?** It is
   the only way a missing forward becomes visible, and the price is
   that the node regularly asks an outside service about itself —
   already accepted once for the DNS watchdog in RFC-0009.
5. **Meeting tool: audio-only, or video from the start?** Not a
   software question. It decides which machine the node must be, and
   therefore whether Stage 1 is sufficient on its own.

## Decided (Jörg, 2026-08-11)

All five questions were answered the day the RFC was written.

**1. One endpoint per instance.** Confirmed, with a reasoning I had
not offered: a service needing more than one port can be composed
from **several instances wired together**, and this will be the
exception rather than the rule.

*One refinement this forces, found while writing it up.* A media
server typically offers UDP as its primary path **and a TCP fallback
for restrictive networks** — and that fallback is exactly the case
that started this whole thread (bdt-hub's product owner wants
distributed participants). Two containers cannot be wired together
here, because it is one process listening twice. Proposal, which
keeps the limit intact: **"one endpoint" means one port *number*,
grantable for `udp`, `tcp`, or both.** The router then carries two
forwarding lines for the same number, the operator still grants
exactly one thing, and the fallback survives. Media servers commonly
use the same number for both anyway.

**2. No fixed ports — but an app may state a wish.** If the wished-for
port is free, it is granted; if not, the platform assigns another one
and the app lives with it. Jörg's reasoning: client-side
configuration for these protocols is nearly always flexible enough to
accept a non-standard port. That holds — MQTT client libraries and
WebRTC `iceServers` entries all carry an explicit port.

*Two consequences worth writing down.* First, **the app must always
read its actual port from the environment**, never assume its wish was
granted. That makes the env delivery mandatory rather than optional,
which is simpler than the alternative. Second, **once granted, the
port must be sticky** — a redeploy must not re-roll it. Otherwise
every published client configuration breaks silently, which is the
same lesson RFC-0009 drew for addresses: what a client has written
down belongs to the service.

**3. Yes to gating by node profile — and combining is already built.**
Verified in the implementation rather than assumed: `node.json` holds
a **set**, `add-profile`/`remove-profile` act on single entries, and
`load_profiles()` returns the sorted set. A node carrying `dev` and
`exposed` at once needs no change to storage, CLI, or portal display;
RFC-0011 designed for it and the code does it. What does not exist yet
is the profile `exposed` itself — today `PROFILES` has exactly one
entry, per RFC-0011 decision 2 ("only profiles that do something").
Adding it is one catalogue entry plus the behaviour it gates.

Temporary is equally fine: `remove-profile` takes it back, and the
already-granted endpoint keeps running while new grants are refused —
the same behaviour `dev` was proven to have on oaap-test on 2026-08-08.

*One sharp edge to document when this is built.* `load_profiles()`
deliberately **ignores profiles it does not know**, so that a
hand-edited or restored `node.json` can never grant a behaviour the
running version does not understand. Correct, but it means a node
downgraded to a version without `exposed` silently loses the profile —
and with it a published port. That belongs in the release note, not in
a surprise.

**4. Yes — the platform checks reachability itself.** The price is
accepted: the node regularly asks something outside the house whether
its published port is actually open. This is the second time we accept
it, after the DNS watchdog in RFC-0009, and for the same reason: the
failure it detects is otherwise **silent**. A forgotten router
forward is indistinguishable from a broken app, and nobody notices
until a meeting fails.

Note for implementation: the two watchdogs answer different questions
about the same house — RFC-0009 asks "does the published name still
point at me", this one asks "does the published port still reach me".
They should share a mechanism rather than grow separately.

**5. Audio only.** The product is a WebXR meeting; video streaming
services will live on the internet later, not on a domestic line. This
settles the sizing question: Stage 1 on oaap-demo is sufficient for
what is actually being built, and the table above is the reason the
video case moves elsewhere rather than being optimised.

### The window this decision was taken in

Jörg's framing, recorded because it will not stay true and because it
changes how much this RFC has to get right the first time:

> Bisher ist die Plattform nicht veröffentlicht und wir können
> Architekturentscheidungen verändern. Es sind nur einzelne
> Konsumenten, die ich alle kenne. Von denen lernen wir ja auch
> gerade. Wenn sich das ändern sollte — also Nutzer die wir nicht mehr
> kennen und die sich auf uns verlassen — sage ich Dir Bescheid.

So the shape proposed here may be revised once real use argues
against it. Two things follow, and they pull in opposite directions:

- **Build Stage 1 without a compatibility promise.** No migration
  path, no deprecation cycle, no "endpoints v1" that must survive.
  The declaration format may change if the first real media server
  teaches us something.
- **Do not let that excuse the security shape.** The parts of this RFC
  that are about *what the platform stops guaranteeing* — the grant,
  the profile gate, the printed warning — are exactly the parts that
  cost nothing to get right now and are painful to retrofit. A
  manifest field can be renamed later; a port that was published
  without anyone deciding to publish it cannot be un-published.

The trigger to revisit this note is Jörg's, not ours: unknown users
who depend on the platform. Until he says so, the format is soft and
the guarantees are not.

## Deutsche Zusammenfassung

**Worum es geht.** Alles, was eine OAAP-App heute erreichbar macht,
ist HTTP — weil das Gateway der einzige Eingang ist und das Gateway
HTTP spricht. Das war richtig und hat uns die Zusage aus RFC-0002
eingebracht. Es heißt aber auch: kein Medienserver, kein nativer
MQTT-Broker, kein TURN. Zwei davon stehen jetzt auf der Roadmap.

**Der Vorschlag ist der kleinstmögliche Schnitt.** Eine App darf
**erklären**, dass sie einen Nicht-HTTP-Port braucht. Veröffentlicht
wird er erst, wenn ein `server_admin` ihn **je Instanz freigibt** —
und die Freigabe sagt im Klartext, welche Zusagen an diesem Port
aufhören. Erklären ist nicht Veröffentlichen; die Voreinstellung
bleibt „zu". Dieselbe Bauform wie bei den Sichtbarkeitsgruppen und dem
`dev`-Profil: Die App bittet, der Betreiber entscheidet.

**Drei Befunde, die das Problem kleiner machen, als es aussieht.**
Erstens: Über WebSocket geht heute schon mehr, als wir dachten —
Signaling, Datenkanäle **und MQTT für Browser-Clients**, mit
Identität. Das ist erst seit dem WebSocket-Fix vom 8.8. wirklich wahr.
Der rohe Port ist deshalb nicht „die MQTT-Lösung", sondern die Lösung
für Geräte, die kein HTTP können. Zweitens: **Ein SFU erledigt die
TURN-Frage.** TURN braucht man, weil zwei Browser hinter NAT sich
nicht finden; ein Medienserver hat eine öffentliche Adresse, die
Clients verbinden sich zu ihm, und das geht durch jedes NAT. Ein
Dienst statt zwei — und linear statt quadratisch. Drittens: **Moderne
SFUs kommen mit einem einzigen UDP-Port aus** statt mit dem
16.000er-Bereich aus dem Lehrbuch. Genau das macht aus „undenkbar"
ein „ein Port".

**Was ehrlich benannt werden muss.** An einer HTTP-Route garantiert
das Gateway Anmeldung, Rollenprüfung, Drosselung und Protokoll. An
einem freigegebenen Port garantiert es **nichts davon** — der Verkehr
läuft am Gateway vorbei. Das ist die `public`-Route eine Stufe weiter,
und es gehört genau so hingeschrieben statt schöngeredet.

**Was das für Dein Meeting-Tool heißt, konkret.** Audio für zehn
Leute kostet den Server 3,6 Mbit/s ausgehend — auf einem
VDSL-Anschluss unproblematisch. Video für zehn Leute kostet 90 Mbit/s
ausgehend und ist auf einem Hausanschluss tot. Die Bauform trägt
also; es entscheidet der **Standort**, nicht die Software. Video
bedeutet einen Knoten mit echtem Upstream — genau der „Knoten beim
Hoster" aus Deiner eigenen Typenliste vom 6.8.

**Fünf Fragen an Dich** stehen oben unter „Open questions": ein Port
je Instanz oder mehrere; darf eine App einen festen Port verlangen;
braucht die Freigabe zusätzlich ein Knoten-Profil; soll die Plattform
selbst prüfen, ob die Portfreigabe im Router überhaupt existiert; und
die einzige, die kein Technikthema ist — Audio zuerst oder Video von
Anfang an.
