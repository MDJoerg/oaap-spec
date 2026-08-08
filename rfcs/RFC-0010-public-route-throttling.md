# RFC-0010: A Brake on Public Routes

- **Status:** Accepted (2026-08-08)
- **Date:** 2026-08-08
- **Authors:** Claude (analysis & proposal), Jörg (decision on direction)
- **Depends on:** RFC-0002 (default deny, gateway enforcement)
- **Driver:** bdt-hub — the first OAAP app that is *entirely* public

## Summary

A route marked `public` gets no authentication from the platform: the
gateway strips spoofed identity headers and hands the request to the
app. Everything after that — credentials, authorization, abuse defence
— is the app's. That is by design and stays that way. What the platform
should not do is offer an **unlimited** pipe: this RFC adds a per-client
request brake on public routes, on by default, adjustable per instance.

## Motivation

Until now, `public` was a niche exception (Forgejo's Git routes, the
deploy hook, `/auth/*`). bdt-hub changes that: its manifest declares a
single route, `/`, with `roles: [public]`, and the instance is reachable
from the open internet. Everything it protects, it protects with its own
API keys.

That means the platform currently contributes nothing at all to the
security of its most exposed surface. An attacker can send requests as
fast as the network allows — guessing keys, hammering the signaling
endpoint, or simply flooding the node. The app runtime spec's security
section says "platform security must not depend on app quality"; on
public routes today it depends on it entirely.

Jörg's decision (2026-08-08), asked explicitly: the brake belongs in the
platform, not in each app — it should benefit BDT clients, Forgejo's Git
routes and whatever comes next, rather than being rebuilt every time.

## Proposal

Every `public` route of an instance passes a gateway-side check before
reaching the app: **requests per client address per instance**.

- **On by default** with a platform default (reference: 300 requests per
  60 seconds), because the safe state is the default state.
- **Adjustable per instance**, and switchable off, by `server_admin`:
  a real-time backend and a Git server have genuinely different traffic
  shapes, and an operator who cannot adjust a limit will simply be
  blocked by it (the mistake `oaap.apps.runtime` 2.8 just fixed for
  configuration). Switching it off warns.
- **One budget per instance**, shared across all its entry points (LAN
  port, node subdomain, own hostname per RFC-0009) — otherwise the limit
  is bypassed by rotating entry points.
- **The gateway decides who the client is**, not the app and not the
  header: in direct mode the TCP peer, behind an edge the address the
  edge vouches for. `X-Forwarded-For` is never trusted from a direct
  client, and the edge now *overwrites* rather than appends it, so a
  client cannot seed the chain with an address of its choosing.
- **Streaming is unaffected.** The check runs once per request, so a
  WebSocket connection or SSE stream is charged once at setup, not per
  message — contract guarantee 7 holds.
- **Over the limit answers `429` with `Retry-After`**, without reaching
  the app.
- Authenticated routes are **not** in scope here: they already have
  identity in front of them, and login itself is throttled separately.

## What this does and does not buy — read this part

This is a **volume brake, not an authentication mechanism**. Said
plainly, so nobody builds on a promise it does not make:

1. **It does not stop a determined key-guessing attack.** It limits
   requests per address; an attacker with a botnet or a rotating proxy
   pool has many addresses. Only the app knows its keys and can lock
   *a key* after N failures. bdt-hub should still do that.
2. **The ceiling is approximate.** Counting happens in the identity
   service's memory, and it runs several worker processes that each
   count on their own — so the effective ceiling is the configured
   limit times the worker count (measured: exactly 2× with the
   reference's two workers). Counters also reset when identity
   restarts. Both are acceptable for a flood brake and would not be for
   an authentication control — which is the point.
3. **Clients behind one NAT share a bucket.** A company office reaching
   the hub from one public address counts as one client. This is the
   normal trade-off of per-address limiting; the per-instance override
   exists for exactly these cases.
4. **It costs one internal request per public request.** The gateway
   asks identity before proxying. For a signaling backend, whose volume
   is messages inside long-lived connections rather than new requests,
   this is cheap. For an app doing thousands of small HTTP calls per
   second it is not, and the honest upgrade path is a rate-limiting
   module inside the gateway itself (a custom Caddy build) rather than
   an internal round trip.

## A bug this uncovered

Testing the brake surfaced a **pre-existing platform defect** on every
authenticated route: `forward_auth` handed the original request's
`Connection: Upgrade` / `Upgrade: websocket` headers to the identity
service, whose WSGI server answered `400`, and `forward_auth` returned
that to the client. **Every WebSocket handshake through the gateway
failed before reaching the app** — contradicting App Deployment
Contract guarantee 7, which the bdt-hub briefing explicitly relies on.
Stripping those hop-by-hop headers from the auth subrequest fixes it
(verified: `400` → `101` on a public route, `400` → `303` on
authenticated routes, where the redirect proves the check now runs).
Recorded here because this RFC's testing is what found it; the fix
belongs to `oaap.core.gateway` regardless of this proposal's fate.

## Decisions (Jörg, 2026-08-08)

1. **The default stays 300 requests per 60 seconds.** Generous on
   purpose: a default that locks out real users is worse than a loose
   one, and the limit is adjustable per instance at any time.
2. **Throttling becomes visible on the health page** — a per-instance
   count of requests braked in the recent past. Without it a `429`
   leaves only a line in an access log that nobody reads, and abuse
   stays invisible until somebody goes looking. A *warning* threshold
   on top was considered and deferred: it needs a threshold that does
   not cry wolf, and the counter can be watched first to find one.
3. **One number per instance now; per-route limits are a later
   stage** — noted, not built. A Git clone and an API call do cost very
   different amounts, so the need is real; it is deferred because more
   knobs mean more ways to set them wrong, and one number is the one
   people will actually get right.

## Deutsche Zusammenfassung

**Das Problem:** Eine als `public` gekennzeichnete Route bekommt von der
Plattform *keine* Anmeldung — das Gateway entfernt gefälschte
Identitäts-Header und reicht die Anfrage direkt an die App durch. Alles
Weitere macht die App selbst. Bei bdt-hub ist das **die ganze App**: eine
einzige öffentliche Route, geschützt allein durch App-eigene API-Keys,
erreichbar aus dem offenen Internet. Die Plattform trug damit zur
Sicherheit ihrer am stärksten exponierten Fläche bisher **nichts** bei —
Anfragen konnten so schnell kommen, wie das Netz sie liefert.

**Der Vorschlag (Deine Entscheidung vom 08.08.):** Eine Bremse im
Gateway statt in jeder App — Anfragen pro Client-Adresse und Instanz.
Standardmäßig an (300 Anfragen je 60 Sekunden), je Instanz einstellbar
und abschaltbar (mit Warnung), ein gemeinsames Budget über alle
Zugänge einer Instanz. Wer darüber liegt, bekommt `429` und erreicht
die App gar nicht erst. Wer der Client ist, entscheidet das Gateway —
nicht ein Header, den der Client selbst schicken kann.

```sh
sudo oaap app throttle show bdt-hub
sudo oaap app throttle set bdt-hub 600/60
sudo oaap app throttle off bdt-hub      # warnt bei öffentlichen Routen
```

**Was das ehrlicherweise NICHT leistet** — bitte lies diesen Teil, er
ist wichtiger als der Rest:

- Es **verhindert kein gezieltes Durchprobieren von API-Keys.** Begrenzt
  wird pro Adresse; wer viele Adressen hat, umgeht das. Nur bdt-hub
  selbst kann *einen Schlüssel* nach N Fehlversuchen sperren. Das sollte
  die App zusätzlich tun — ich würde es der BDT-KI als Anforderung in
  den Postkasten legen, wenn Du mich aktiv werden lässt.
- Die Grenze ist **ungefähr**: Der Zähler liegt im Arbeitsspeicher des
  Identity-Dienstes, der in mehreren Prozessen läuft, die getrennt
  zählen — real also etwa das Doppelte des eingestellten Werts (im Test
  exakt 2×). Für eine Flutbremse in Ordnung, für eine Zugangskontrolle
  nicht — und genau das ist es auch nicht.
- **Alle hinter einem Anschluss zählen als ein Client** (ein Büro mit
  einer öffentlichen IP). Dafür gibt es die Einstellbarkeit.

**Nebenbefund — und der ist ernst:** Beim Testen kam ein **bestehender
Fehler** ans Licht, der nichts mit dieser Bremse zu tun hat:
**WebSocket-Verbindungen scheiterten bisher auf JEDER authentifizierten
Route** mit „400 Bad Request", weil die Anmeldeprüfung die
Upgrade-Header der Anfrage mitgeschickt bekam und der Identity-Dienst
sie ablehnte — die Anfrage erreichte die App nie. Das widerspricht
Garantie 7 des App Deployment Contract, auf die sich bdt-hubs Signaling
ausdrücklich verlässt. Ist behoben und geprüft (aus 400 wurde 101 bzw.
303). Ohne diesen Fund wäre bdt-hub produktiv gegangen und hätte nicht
funktioniert.

**Entschieden (Jörg, 2026-08-08) — RFC-0010 abgenommen:**

1. **300 Anfragen pro Minute bleiben der Standard.** Bewusst großzügig:
   Ein zu enger Standardwert, der echte Nutzer aussperrt, ist schlimmer
   als ein lockerer — und je Instanz ist er jederzeit anpassbar.
2. **Die Gesundheitsseite zeigt künftig, wie oft gebremst wurde** (je
   Instanz). Sonst merkt niemand, dass jemand klopft. Eine zusätzliche
   Warnung bei anhaltender Drosselung ist vorgemerkt, aber
   zurückgestellt — dafür braucht es erst eine Schwelle, die nicht
   ständig fälschlich anschlägt; der Zähler liefert die Erfahrung dafür.
3. **Vorerst eine Zahl je Instanz**, Grenzen je Route sind als spätere
   Ausbaustufe **vorgemerkt** (Jörgs Entscheidung). Der Bedarf ist real
   — ein Git-Klon kostet etwas anderes als ein API-Aufruf —, aber mehr
   Stellschrauben heißt auch mehr Gelegenheiten, sie falsch zu setzen.
