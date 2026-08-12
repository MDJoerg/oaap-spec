# RFC-0017: Real-Time Media as a Capability, LiveKit as the Reference

- **Status:** Draft (2026-08-12) — direction and four framing decisions
  taken by Jörg on 2026-08-12; this draft records them and surfaces the
  open questions for the build. **Prepared, not yet built.**
- **Date:** 2026-08-12
- **Authors:** Claude (proposal), Jörg (direction and decisions)
- **Depends on:** RFC-0002 (security-first, single entry), RFC-0004
  (packaging/manifest), RFC-0015 (declared endpoints — the raw UDP path),
  RFC-0016 (app isolation, multi-container apps, app-to-app links),
  §2.8 (secret config values)
- **Relates to:** the bdt-hub WebXR meeting tool (the first consumer);
  the "server services OAAP will co-manage" direction (MQTT next)

## Summary

OAAP can now carry a non-HTTP service (RFC-0015) built from several
containers on its own isolated network (RFC-0016). This RFC uses that to
make **real-time media** — audio and video over WebRTC — a thing OAAP
supports, and names **LiveKit** as the reference for how it is done.

The split matters and is deliberate. **Real-time media is the
capability; LiveKit is one implementation of it** — exactly as Caddy is
the reference for the gateway without "gateway = Caddy" appearing in any
spec. The normative specs stay LiveKit-free; `oaap-reference` and the app
package name LiveKit. A later swap to mediasoup, Janus or a hosted SFU
costs no spec change.

This closes the loop opened by the bdt-hub letter: the answer there was
"not a TURN relay, an SFU as an OAAP app." This RFC is that app.

## The four framing decisions (Jörg, 2026-08-12)

1. **Reference app now, growth-open — not a shared platform service
   yet.** LiveKit ships as a `wrapped` app a project installs for itself,
   using the capabilities that already exist (declared endpoint + secret
   config + isolation). It is built so the *shared, platform-managed*
   service can grow from it later (the "OAAP co-manages server services"
   direction, MQTT next) without a redesign — but that larger step is its
   own RFC. The capability today is the reference: it shows how real-time
   media runs on OAAP.
2. **Single-port UDP mode.** LiveKit runs with its embedded ICE over a
   single UDP port, not the usual wide media range. This fits the
   one-port-per-instance rule RFC-0015 deliberately chose, and proves
   that rule carries a real media server. RFC-0015 is not reopened for
   the common case (but see the open question in §5.1).
3. **Multi-container from the start (LiveKit + Redis).** Not the smallest
   possible cut — Jörg's choice — because it makes LiveKit the first real
   exercise of RFC-0016 multi-container apps under genuine load shape.
4. **Instance may carry more than one DNS name** — handled in a separate
   RFC-0009 follow-up, not here; noted because a media instance is a
   likely first user of it.

## Design

### Containers (RFC-0016 multi-container)

Two services in one app instance:

- `livekit` — the official `livekit/livekit-server` image (SFU +
  embedded ICE/TURN).
- `redis` — required by LiveKit for anything beyond a single trivial
  process; the store for room and participant state.

**Redis is a co-service, not a linked app.** Because both live in the
*same* instance, RFC-0016 already puts them on that instance's private
network and lets `livekit` resolve `redis` by service name. **No
app-to-app link is involved, and Redis gets no endpoint** — it is never
published, never reachable from outside or from another app. (This
corrects an earlier note that called it a link; a link is between two
*separate* instances.)

### Signaling — through the gateway, as HTTP/WSS

LiveKit's control plane is HTTP + WebSocket on `:7880`. This is an
ordinary OAAP route: `path: /`, served with TLS by the gateway under the
instance's external hostname, so clients connect to `wss://<host>/`. No
new mechanism. The route is **`public`** because LiveKit authenticates
every request itself by signed token (below) — the gateway login would be
the wrong gate. The RFC-0010 volume brake still applies, which is the
right kind of protection for a public control endpoint.

### Media — one UDP port, and a TCP fallback on the same number

LiveKit's media (RTP/RTCP over ICE) is the raw path. Configured in
single-port mode, all media multiplexes over one UDP port. Declared as an
RFC-0015 endpoint:

```yaml
endpoints:
  - name: media
    protocol: both        # see below
    container_port: <P>
    wish: <P>
    reason: "WebRTC media (audio/video); single-port ICE"
```

**Why `protocol: both`.** Some client networks block UDP. LiveKit offers
a TCP fallback for exactly those. RFC-0015's `both` publishes the *same
port number* for udp and tcp — so LiveKit binds UDP media and TCP
fallback on one number `P`, and we stay inside the one-port-per-instance
rule while still serving UDP-hostile networks. One grant, one router
forward (`P/udp` and `P/tcp`), one number.

### Tokens — key/secret, minted by the consuming app

LiveKit trusts a JWT signed with an API key/secret pair. The app that
runs meetings (bdt-hub) mints short-lived tokens for its clients. So:

- `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` are `secret: true` config on
  the LiveKit instance (§2.8 holds them; the app reinvents nothing).
- At the reference-app stage the **same operator** puts that secret into
  the consumer app's config by hand. It is not brokered. That is honest
  for stage 1 and is exactly the seam the *shared-service* RFC (growth
  path) would later automate — the platform minting or handing out
  short-lived credentials over an app-to-app link.

### Public IP for ICE

An SFU must tell clients the address to send media to. Behind a published
port LiveKit sees only its container IP, so `rtc.use_external_ip: true`
makes it learn its public IP at startup via STUN (one outbound request,
the same class of "ask the outside once" already accepted for the DNS and
reachability watchdogs). The reachability watchdog (RFC-0015, 0.1.33)
then confirms the media port from the node's side; a real client confirms
it end to end.

## 5. Open questions for the build

### 5.1 The advertised-port problem — the one that needs a decision

A media server advertises, in its ICE candidates, **the exact port the
world will send media to**. RFC-0015, by design, treats the port as a
*wish*: if the wished number is taken, the platform assigns another, and
the app learns it via `OAAP_ENDPOINT_PORT`. For an HTTP-ish raw service
that is fine. **For a media server it is not automatically fine:** if the
published host port differs from what LiveKit binds and advertises, ICE
points clients at the wrong port and media fails.

Two ways out:

- **(a) Make the wrapped entrypoint bind and advertise
  `OAAP_ENDPOINT_PORT`.** LiveKit is told at startup to use the
  platform-assigned number for both its bind and its advertised port.
  This keeps RFC-0015's wish semantics intact and needs no spec change —
  *if* LiveKit can be configured to bind an arbitrary port at runtime
  (it can, via config/env templating) **and** the publish maps that same
  number host↔container. That last part is the catch: RFC-0015 publishes
  `host_port:container_port` from the *static* manifest `container_port`.
  So the manifest's `container_port` would have to equal the assigned
  `host_port`, which is only known at grant time.
- **(b) A small RFC-0015 addendum: an opt-in "fixed port" endpoint.** An
  endpoint may declare that its port is a *requirement*, not a wish:
  `fixed: true`. Grant then publishes `host_port == container_port ==
  wish`, or **fails loudly** if the number is taken (rather than silently
  assigning another). Default stays "wish"; only servers that advertise
  their own port opt in.

**Recommendation: (b).** It is the honest shape — a media server's port
*is* a requirement, and saying so is better than a wish that silently
breaks media. It keeps the wish default for everything else and reopens
RFC-0015 only by addition, not by changing what is already decided. This
is the single decision this RFC most needs from Jörg before the build.

### 5.2 Growth path to a shared service

Decision 1 keeps this a reference app but asks it to be growth-open. The
seam is §Tokens: today the operator copies the secret by hand; the
shared-service RFC would have the platform broker short-lived credentials
over an RFC-0016 app-to-app link (bdt-hub links to the LiveKit instance,
asks for a room token, never holds the long-lived secret). Nothing in
this RFC should foreclose that — in particular the secret stays in
platform-held config, never baked into an image.

### 5.3 Smaller open items

- **Health path.** Which LiveKit endpoint the health check probes (its
  HTTP server answers; confirm a stable 200 path).
- **Turn/TCP specifics.** Whether LiveKit's embedded TURN is needed at
  all once single-port `both` is in place, or whether it adds a second
  port we do not want.
- **Recording / egress.** Out of scope for the reference; a later service
  container if a project needs server-side recording.

## Staged plan

- **A1 (this RFC).** Direction + the §5.1 decision.
- **A2.** Manifest `oaap-apps/apps/livekit`: two services (livekit,
  redis), the `both` media endpoint, secret key/secret config, public
  signaling route.
- **A3.** LiveKit single-port config and the entrypoint that wires
  `OAAP_ENDPOINT_PORT` per the §5.1 decision.
- **A4.** Deploy on oaap-demo (`exposed` profile + router forward → the
  reachability watchdog now shows real green), end-to-end test with a
  real client.
- **A5.** Tell bdt-hub: the SFU recommendation is now a concrete OAAP app,
  and how to point their client at it.

## Deutsche Zusammenfassung

**Worum es geht.** Seit 0.1.33 kann OAAP einen Nicht-HTTP-Dienst
(RFC-0015) aus mehreren Containern auf einem eigenen, abgeschotteten Netz
(RFC-0016) betreiben. Dieser RFC nutzt das, um **Echtzeit-Medien** (Audio
und Video über WebRTC) zu einer Fähigkeit von OAAP zu machen — mit
**LiveKit als Referenz**. Die Trennung ist Absicht: **Echtzeit-Medien ist
die Fähigkeit, LiveKit eine Umsetzung davon** — wie Caddy die Referenz
fürs Gateway ist, ohne dass „Gateway = Caddy" in einer Spec steht. Die
normativen Specs bleiben LiveKit-frei; nur Paket und `oaap-reference`
nennen LiveKit. Ein späterer Tausch kostet keine Spec-Änderung. Damit ist
auch die bdt-hub-Frage vom Anfang beantwortet: kein TURN-Relay, sondern
ein SFU als OAAP-App — und das ist diese App.

**Deine vier Entscheidungen** stehen im Kopf: Referenz-App (wachstumsoffen
zum späteren geteilten Plattform-Dienst), Ein-Port-UDP (passt zur
Ein-Port-Regel und beweist sie), gleich Mehr-Container (LiveKit + Redis —
erster echter Härtetest für RFC-0016), und mehrere DNS-Namen je Instanz
kommen separat.

**Aufbau in einem Satz.** Zwei Dienste in einer Instanz (livekit +
redis); Redis ist ein **Mitdienst, kein verlinkter App** — beide teilen
sich automatisch das Instanznetz, Redis wird nie veröffentlicht. Das
Signaling (Steuerkanal) läuft als normale HTTPS/WSS-Route übers Gateway;
der Medienpfad ist ein deklarierter UDP-Endpunkt, als `both` sogar mit
TCP-Rückfallebene **auf derselben Portnummer** — ein Grant, eine
Router-Freigabe. Zugangsdaten (API-Schlüssel/-Geheimnis) liegen als
`secret:true` in der Instanz-Konfiguration; die Meeting-App (bdt-hub)
erzeugt daraus kurzlebige Tokens.

**Die eine Frage, die ich Dir vorlegen muss (§5.1).** Ein Medienserver
bewirbt bei seinen Clients **genau den Port, an den sie senden sollen**.
RFC-0015 behandelt den Port aber absichtlich als **Wunsch**: Ist er
belegt, vergibt die Plattform still einen anderen. Für einen Medienserver
ist das gefährlich — bewirbt LiveKit einen anderen Port als den
veröffentlichten, schlägt die Medienverbindung fehl. Mein Vorschlag:
RFC-0015 um eine **Opt-in-Angabe `fixed: true`** ergänzen — der Port ist
dann Pflicht statt Wunsch, und die Freigabe **scheitert laut**, wenn die
Nummer belegt ist, statt still eine andere zu nehmen. Voreinstellung
bleibt „Wunsch"; nur Server, die ihren eigenen Port bewerben, schalten
das ein. Das ist die einzige Entscheidung, die ich vor dem Bauen von Dir
brauche.

**Nicht gebaut.** Dieser Entwurf ist Vorbereitung; A2–A5 baut die nächste
Session, nachdem Du §5.1 entschieden hast.
