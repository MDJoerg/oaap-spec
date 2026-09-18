# oaap.core.gateway — HTTP Gateway (outline)

- **ID:** `oaap.core.gateway`
- **Version:** 0.2.8
- **Maturity:** draft (outline — full specification to follow;
  open streams survive a gateway reload, and the permanent access log
  is filtered like the diagnosis log, 2026-09-18 (reference 0.1.102 /
  0.1.103, from the Handball-Infoboard's first letter);
  a refusal is readable across origins and a time-boxed per-instance
  access log added 2026-09-17 per RFC-0038;
  §Edge routing added 2026-08-07 per RFC-0006; visibility groups
  parameter added 2026-08-07 per RFC-0007; per-instance public
  hostnames added 2026-08-08 per RFC-0009; public-route throttling and
  the WebSocket forward-auth fix added 2026-08-08 per RFC-0010;
  app-network membership added 2026-08-12 per RFC-0016; per-instance
  hostnames extended to a canonical name plus aliases 2026-08-12 per
  RFC-0018; fleet status route added 2026-08-23 per RFC-0021)
- **Based on:** RFC-0001, RFC-0002, RFC-0003, RFC-0006, RFC-0007,
  RFC-0008, RFC-0009, RFC-0010, RFC-0016, RFC-0018, RFC-0027, RFC-0038

## Purpose

The single HTTP(S) entry point of the platform. Every request to the
portal or any app passes through it; the default policy is **deny** —
a route is only reachable for an authenticated identity whose roles
permit it, unless the route is explicitly marked `public` in the app's
configuration (none by default). Apps can rely on authentication having
happened and never see credentials.

## Interface (sketch)

- **Route registration**: apps declare their routes, required roles, and
  any `public` exceptions in their manifest; the platform configures the
  gateway from that — apps never configure the gateway directly.
- **Identity propagation**: the gateway passes the verified identity and
  roles to apps via trusted headers or tokens (mechanism to be resolved
  with `oaap.core.identity`). **Anti-spoofing guarantee**: identity
  headers arriving from clients are stripped/overwritten on every
  route, including `public` ones — apps can trust their presence.
- **Visibility groups** (RFC-0007): an installed instance may carry an
  additional `visibility` restriction (`oaap.apps.runtime` 2.7,
  operator-set, never in the app manifest). When set, every non-public
  route's forward-auth call for that instance gains a `groups=`
  parameter alongside `roles=`, checked by `oaap.core.identity` 2.3/2.6
  — `server_admin` bypasses it unconditionally (RFC-0008). No new
  header is forwarded to apps; the App Deployment Contract is
  unaffected.
- **Route semantics**: declared paths are prefix matches, longest
  declared prefix wins; requests under no declared route are rejected
  at the gateway. The original `Host` header is preserved;
  `X-Forwarded-Proto`/`X-Forwarded-For` are set. Additional ports an
  app opens are never published.
- **Fleet status route** (RFC-0021): `GET /fleet/status` is carried
  like the deploy hook — no forward auth, client-sent identity headers
  stripped, authorization by a fleet key that the portal validates
  (`oaap.fleet.status` 0.1). Served on the platform apex of every
  published name; never on app instance sites.
- **Topology** (RFC-0003): the gateway runs on the controller and also
  publishes apps that run on worker nodes; a worker whose controller is
  down is not reachable through the gateway.
- **App network membership** (RFC-0016): each app instance runs on its
  own network (`oaap.apps.runtime` 2.11); the gateway is the only core
  service that joins those networks, which is how it proxies to apps
  that are otherwise isolated from identity, portal and each other. The
  membership is re-established whenever the gateway is recreated (every
  platform update), or apps become unreachable (502).
- **TLS termination** and port configuration (see `oaap.core.host`).

## Edge routing (RFC-0006)

A node whose gateway owns the shared public entry point can forward
requests for **other platforms' hostnames** to the platform that owns
the name. Only the entry is shared; the platforms stay autonomous.

### Edge side

- **Routing table**: administrator-maintained entries
  `hostname → target address[:port]`. Each entry covers the hostname
  **and** its wildcard subtree (`host` and `*.host`) — RFC-0005 level 3
  gives every app instance a subdomain, so a platform owns a subtree.
  CLI: `oaap edge add <hostname> <target>` / `list` / `remove`.
- The edge terminates TLS and obtains/renews certificates for all
  routed names (it is the only node that can answer ACME challenges).
  HTTP requests for routed names are redirected to HTTPS at the edge;
  ACME challenges are excepted.
- **Subdomain certificates are obtained on demand.** The edge cannot
  know the backend's app instance names, and wildcard certificates
  require a DNS challenge the platform does not assume. Certificates
  for names below a routed hostname are therefore obtained at
  handshake time, gated by a platform approval endpoint that permits
  only names equal to or below a configured edge route. *Known
  hardening gap:* any subdomain of a routed host is approvable, so a
  hostile client could drive certificate issuance into the CA's rate
  limit for that domain; a future increment lets the edge verify the
  concrete instance names against the backend.
- Forwarding preserves the original `Host` header unchanged and sets
  `X-Forwarded-Proto`/`X-Forwarded-For` (contract guarantee 2 holds
  through the chain).
- A routed hostname MUST NOT equal the edge's own external hostname.
  Names not in the table are never forwarded.
- The edge does not log request bodies (RFC-0006 trust section).

### Backend side (behind-edge mode)

A platform served through an edge is switched into behind-edge mode:
`oaap external set <hostname> --behind-edge <edge-address>`.

In this mode the gateway, for the external hostname and its subtree:

1. serves the full external site over **plain HTTP** (the edge already
   terminated TLS) and suppresses the usual HTTP→HTTPS redirect —
   otherwise the chain loops;
2. does not attempt ACME for these names (it cannot succeed — the
   ports live at the edge);
3. accepts requests for these hostnames **only from the configured
   edge address**; any other client gets `403` (this is also what makes
   trusting `X-Forwarded-*` acceptable: they can only come from the
   edge). Local entry points (LAN address, app listener ports) are
   unaffected;
4. keeps every RFC-0002 guarantee: identity headers are stripped and
   re-set by this gateway regardless of what the edge forwarded.

`oaap external show` reports the mode. Switching back to direct mode
(`oaap external set <hostname>` without the flag) restores TLS sites
and the redirect.

### Unavailability page (reserved)

When a routed backend does not answer, the edge serves a configurable
page; the same mechanism will serve deliberately-offline routes
(maintenance, incident response). Templates range from plain text to
an OAAP-branded page to custom content. Details are deferred to the
full specification; RFC-0006 resolved question 3 records the decision.

## Per-instance public hostnames (RFC-0009, extended by RFC-0018)

Besides the automatic `<instance>.<external hostname>` subdomains
above, an app instance MAY register public hostnames **of its own** —
names that do not derive from the node's name and therefore survive the
app moving to another node. Since RFC-0018 that is **one canonical name
plus zero or more aliases**: the canonical name is the one the platform
reports and that is meant to be embedded in shipped clients; aliases are
additional names, fully reachable, under the same protection. The
gateway serves **one site per name** — canonical and each alias alike:

1. built from the **same** route/role/group block as every other entry
   point of that instance — default deny, reserved `/auth/*`,
   anti-spoofing and visibility groups apply unchanged. An own name (or
   an alias) grants an app nothing extra; a name is a front door, not a
   permission;
2. in **direct** mode: a TLS site with ACME plus an explicit
   HTTP→HTTPS redirect, per name;
3. in **behind-edge** mode: plain HTTP, no ACME, no redirect, and only
   from the edge address — points 1–4 of the backend-side rules above
   apply verbatim, for the same reasons; the edge needs one route per
   name;
4. **additive** — the automatic node subdomain keeps working, so
   clients can migrate gradually;
5. **collision-refusing**: a name is rejected if it is or lies under
   the node's own external hostname, if an edge route on this node
   covers it, or if any instance already holds it **as a canonical name
   or an alias**; symmetrically, an edge route that would capture a
   local instance's hostname is rejected. The gateway never silently
   resolves such a conflict. An alias may be registered only once the
   instance has a canonical name; removing the canonical name while
   aliases remain is refused.

DNS and port forwarding for **every** name are the operator's
responsibility (RFC-0006's division of labour, unchanged); on a restore
all names travel with the app and each must be repointed by hand.

## Public-route throttling (RFC-0010)

A `public` route receives no authentication — that is its definition.
The gateway therefore applies the one control it still can: a limit on
**requests per client address per instance**, checked before the app is
reached.

- On by default (reference default: 300 requests per 60 s), adjustable
  per instance and switchable off by `server_admin`.
- **One budget per instance**, shared by every entry point it has (LAN
  listener, node subdomain, canonical name and every alias) — a limit
  that can be bypassed by changing entry point is not a limit.
- The **gateway determines the client address**: the TCP peer in direct
  mode, the address vouched for by the edge in behind-edge mode. A
  client-supplied `X-Forwarded-For` is never used, and the edge
  overwrites that header with the peer it sees, so the chain cannot be
  seeded by the client.
- Checked **once per request**, so streaming responses and WebSocket
  connections pay it at setup only (guarantee 7 unaffected).
- Exceeding it yields `429` with `Retry-After`; the app is not reached.
- It is a **volume brake, not authentication**: per-address limits do
  not stop a distributed key-guessing attack, and the count is
  approximate (see RFC-0010 for the full list of what it does not
  promise). Apps on public routes remain responsible for their own
  credential lockout.

**Forward-auth and protocol upgrades.** The authentication subrequest
is a plain `GET`; the original request's hop-by-hop headers
(`Connection`, `Upgrade`) MUST NOT be forwarded to it. Passing them on
makes a WSGI auth service answer `400`, which forward-auth returns to
the client — breaking every WebSocket handshake before the app is
reached. This applies to every forward-auth call: platform apex, app
routes and the throttle check alike.

## A refusal must be readable across origins (RFC-0038 follow-up)

A page on another origin calls an app on this node and the gateway
refuses it — no session, no or a wrong API key, too many requests. Until
0.2.7 that refusal carried no CORS header, so the browser did not report
"not authenticated": it reported a **CORS error**, and the status the
caller actually received was invisible to the script and to the person
debugging it. (Found the hard way on 2026-09-15: hours spent on a CORS
question whose answer — *this one call carries no key* — was in the
gateway's access log the whole time.)

Therefore, when a refusal is produced for a request carrying an `Origin`
that is **not** the origin of the site itself:

- The refusal MUST carry `Access-Control-Allow-Origin` reflecting that
  origin, `Vary: Origin` **added** to whatever the response already
  varies on, and `Access-Control-Expose-Headers: WWW-Authenticate`.
- It MUST NOT carry `Access-Control-Allow-Credentials`. A cookie-bearing
  cross-origin call therefore still cannot read the refusal, so no
  foreign page can use one to probe whether its visitor has a session on
  this node. The case this serves is the one that is meant to work: an
  API key in `Authorization` (RFC-0027), which is not a credential in the
  CORS sense.
- A refusal that would be a **redirect to the login form** MUST instead
  be answered `401` with `WWW-Authenticate` and a message naming the way
  in, **unless the request is a browser navigation** (fetch metadata:
  `Sec-Fetch-Mode: navigate` or `Sec-Fetch-Dest: document`), where the
  login form is the right answer and the redirect stands. A 303 to an
  HTML page is useless to `fetch()`: the browser follows it, the login
  page answers `200` without CORS headers, and the script reports a CORS
  error on a URL it never called.
- A same-origin refusal is unchanged — no CORS header, and the login
  redirect stays.
- Every other status keeps its meaning: only a **redirect** is
  reinterpreted, never a `403`, a `429` or anything else.

This belongs to the **one** place that produces gateway refusals
(`oaap.core.identity`'s forward-auth endpoints — the role/tenant check
and the throttle check are the only forward-auth calls a generated site
makes). A rule written per site would be a rule forgotten at one site.

**Known remaining gap:** a `404` the gateway itself answers for a path an
instance declares no route for carries no CORS header either. It is the
same class of problem and deliberately not fixed here — it needs headers
on the gateway side rather than in identity.

## Open streams survive a gateway reload (0.2.8)

Every deployment of **any** app reloads the gateway configuration. A
WebSocket or SSE stream opened under the previous configuration MUST NOT
be closed by that reload. (Measured before the rule, on oaap-test with
Caddy 2.11.4: a held stream died in the same second as the reload, so a
deployment of one app cut the open connections of every other app on the
node.)

- Applies to every path from the gateway to an app: app routes on every
  entry point, edge forwarding (RFC-0006) and the broker's WebSocket
  listener (RFC-0032).
- The reference keeps such a stream for up to **12 hours** after the
  reload that retired its configuration (`stream_close_delay`). A stream
  is not guaranteed to live forever.
- Not covered, by design: a stream to an app that is **itself**
  redeployed or restarted ends with its container. The nightly backup
  also stops containers briefly (RFC-0029). Clients therefore MUST still
  reconnect; the guarantee is that a **neighbour's** deployment is not
  one of the reasons.
- A node updated from an earlier version rewrites its generated sites
  once, during the update.

## The permanent access log (0.2.8)

The gateway writes an access log for every **published** name (platform
apex, automatic instance names, an instance's own names and aliases, and
edge routes). The LAN entry points write none. The same field rules as
for the time-boxed diagnosis log (next section) apply to it, from **one**
definition shared by both:

- MUST NOT be written: the request's **query string**, the **value** of
  `Authorization`, `Proxy-Authorization` and `Cookie`, any `Set-Cookie`,
  the `X-OAAP-*` identity headers, the query string of a `Location`, and
  bodies.
- The **presence** of `Authorization` and `Cookie` is kept as a fixed
  placeholder.
- The **path** is written in full. A secret an app puts into the path
  therefore lands in this log. Apps are told to carry device or share
  keys in the URL **fragment** (`#…`), which a browser never sends to a
  server, and to exchange it for something short-lived after loading.
  The log belongs to the node operator and is not part of the backup.

(Until 0.2.7 this log kept full URIs. The operator of bdt-hub was told
on 2026-08-08 that this would be examined; it was fixed only when the
second app with keys in its links asked the same question.)

## A time-boxed per-instance access log (RFC-0038 D3)

An instance's gateway sites MAY be asked to write an access log of their
own — **only** while a diagnosis window is open for that instance
(`oaap.core.portal` 2.4). This specification does **not** introduce
permanent per-instance logging.

- Opening adds the log to **every** entry point of that instance (LAN
  listener, automatic name, canonical name and every alias) and reloads
  the gateway gracefully; closing or expiry removes it, reloads again and
  **deletes** the file and any rolled predecessors. An entry point left
  out would be a blind spot exactly where somebody is looking for one.
- Collection begins when the window opens. The portal says so, because
  the first question otherwise is why the list is empty.
- The file MUST be bounded in size, so an hour of a hammered route
  cannot turn a diagnosis into a disk problem.
- **These fields MUST NOT be written:** the request's **query string**,
  the **value** of `Authorization` or `Proxy-Authorization`, the value of
  `Cookie`, any `Set-Cookie`, the `X-OAAP-*` identity headers, the query
  string of a `Location`, and bodies. This is a MUST of this
  specification, not a property inherited from whatever the reference's
  log implementation happens to default to.
- The **presence** of `Authorization` or `Cookie` MUST be preserved
  (a fixed placeholder in place of the value). It is the one fact that
  tells *the caller sent no key* apart from *the key was wrong* — which
  is precisely the question this feature exists to answer — and a plain
  deletion would throw it away.
- A `Location` keeps its path, because it is what distinguishes "sent to
  the login form" from every other redirect.

## Dependencies

`oaap.core.identity`

## Maturity

`draft`

## German summary / Deutsche Zusammenfassung (Edge-Abschnitt + Sichtbarkeitsgruppen)

**Sichtbarkeitsgruppen (RFC-0007):** Ist für eine Instanz eine
Gruppen-Einschränkung gesetzt, hängt das Gateway an jede
Rollenprüfung zusätzlich `groups=...` an — geprüft von Identity,
`server_admin` sieht immer alles. Kein neuer Header an Apps.

Ein Knoten mit dem öffentlichen Eingang (Portfreigabe) kann Anfragen
für die Hostnamen **anderer** Plattformen an deren Adresse
weiterreichen: Der Administrator pflegt eine Tabelle `Hostname → Ziel`
(`oaap edge add/list/remove`); jeder Eintrag gilt für den Namen samt
aller Subdomains. Der Edge holt die Zertifikate für alle Namen und
leitet HTTP auf HTTPS um. Die Zielplattform wird mit
`oaap external set <name> --behind-edge <edge-adresse>` in den Modus
„hinter Edge" geschaltet: Sie liefert ihre externe Site dann über
HTTP aus (kein Umleitungs-Loop), versucht keine eigenen Zertifikate
mehr und akzeptiert Anfragen für diese Namen **nur von der
Edge-Adresse** (sonst 403). Alle Sicherheitsgarantien bleiben: Auch
hinter dem Edge verwirft das eigene Gateway die Identitäts-Header und
setzt sie nach eigener Anmeldung neu. Die konfigurierbare
„Nicht erreichbar"-Seite (auch für bewusst offline genommene Routen)
ist reserviert und wird in der Vollspezifikation ausgearbeitet.

## Deutsche Zusammenfassung (eigene Adressen je Instanz, v0.2.2)

**Neu (RFC-0009):** Eine App-Instanz kann einen **eigenen öffentlichen
Namen** bekommen — zusätzlich zur automatischen Adresse
`<instanz>.<knotenname>`. Hintergrund ist bdt-hub: Dessen Adresse wird
in ausgelieferte Clients eingebaut, und die dürfen nicht am Namen der
Maschine hängen, auf der die App zufällig gestartet ist.

Wichtig: Es ist **dieselbe** Absicherung wie bei jeder anderen Adresse
derselben App — Rollen, Sichtbarkeitsgruppen, default deny und die
reservierte Anmelde-Route gelten unverändert. Direkt am Internet gibt
es ein normales Zertifikat plus HTTP→HTTPS-Umleitung; hinter einem Edge
Klartext-HTTP ohne Umleitung und nur vom Edge annehmbar (sonst
Endlosschleife — dieselbe Regel wie bei Knotennamen seit RFC-0006).
Die alte Adresse bleibt gültig, damit Clients in Ruhe umziehen können.
Namenskonflikte werden abgelehnt statt stillschweigend aufgelöst.
DNS-Eintrag und Portfreigabe bleiben Sache des Betreibers.

**Erweiterung (RFC-0018, v0.2.5):** Aus dem einen eigenen Namen werden
**ein Hauptname plus beliebig viele Aliasse**. Der Hauptname ist DIE
Adresse (wird gemeldet, in Clients eingebaut); Aliasse sind gleichwertig
erreichbar, aber nicht „die" Adresse — und stehen unter genau demselben
Schutz (kein Schlupfloch). Das Gateway liefert **ein Site je Name**
(direkt je ein Zertifikat + Umleitung, hinter Edge je eine Edge-Route).
Kollisionen werden gegen **alle** Namen jeder Instanz geprüft. Ein Alias
geht erst mit vorhandenem Hauptnamen; den Hauptnamen zu entfernen,
solange Aliasse hängen, wird abgelehnt. Beim Umzug reisen **alle** Namen
mit und werden einzeln zum Umbiegen gemeldet.

## Deutsche Zusammenfassung (Drosselung öffentlicher Routen, v0.2.3)

**Neu (RFC-0010):** Öffentliche Routen bekommen eine Bremse — Anfragen
pro Client-Adresse und Instanz, standardmäßig an, je Instanz
einstellbar. Ein Budget gilt für alle Zugänge einer Instanz zusammen,
sonst ließe es sich durch Wechseln des Zugangs umgehen. Wer der Client
ist, entscheidet das Gateway (direkter Peer bzw. die vom Edge
bezeugte Adresse), nie ein vom Client geschickter Header. Geprüft wird
einmal pro Anfrage, Streams und WebSockets zahlen also nur beim
Verbindungsaufbau. Wichtig und ausdrücklich festgehalten: Das ist eine
**Mengenbremse, keine Zugangskontrolle** — Details in RFC-0010.

**Behobener Fehler:** Die Anmeldeprüfung (`forward_auth`) darf die
Upgrade-Header einer Anfrage nicht mitbekommen. Tat sie es, antwortete
der Identity-Dienst mit 400 und **jeder WebSocket-Verbindungsaufbau
scheiterte** — auf allen authentifizierten Routen, seit es sie gibt.

## Deutsche Zusammenfassung (v0.2.7 — eine Ablehnung muss lesbar sein, und ein befristetes Protokoll je Instanz)

**Erstens: „CORS-Fehler" war fast immer die falsche Auskunft.** Ruft eine
Seite von einer anderen Herkunft (Origin) eine App auf diesem Knoten und
das Gateway lehnt ab — keine Anmeldung, kein oder ein falscher
API-Schlüssel, zu viele Anfragen —, dann trug diese Ablehnung bisher
keine CORS-Kopfzeile. Der Browser meldete deshalb nicht „nicht
angemeldet", sondern „CORS-Fehler", und der wahre Status war für das
Skript und für den Menschen davor unsichtbar. Am 15.09. hat das Stunden
gekostet; die Antwort („dieser eine Aufruf trägt keinen Schlüssel") stand
die ganze Zeit im Zugriffsprotokoll des Gateways.

Jetzt verbindlich, für Ablehnungen an Aufrufe mit **fremder** Herkunft:

- Die Ablehnung spiegelt die Herkunft in `Access-Control-Allow-Origin`,
  ergänzt `Vary: Origin` und macht `WWW-Authenticate` lesbar.
- **Kein** `Access-Control-Allow-Credentials`. Ein Aufruf mit Cookie kann
  die Antwort also weiterhin nicht lesen — keine fremde Seite kann so
  ausmessen, ob ihr Besucher hier angemeldet ist. Bedient wird der Weg,
  der gedacht ist: ein API-Schlüssel in `Authorization` (RFC-0027).
- Eine Ablehnung, die eine **Umleitung zum Anmeldeformular** wäre, wird
  zu `401` mit einem Satz, der den Weg hinein nennt — **außer** bei einer
  echten Navigation im Browser, wo das Formular genau richtig ist. Für
  ein Skript ist eine Umleitung auf eine HTML-Seite nutzlos: Der Browser
  folgt ihr, die Anmeldeseite antwortet 200 ohne CORS-Kopfzeilen, und das
  Skript meldet einen CORS-Fehler zu einer Adresse, die es nie gerufen
  hat.
- Gleiche Herkunft bleibt unverändert, und nur eine **Umleitung** wird
  umgedeutet — ein 403 oder 429 behält seinen Status.

Die Regel gehört an die **eine** Stelle, die Gateway-Ablehnungen erzeugt
(die Forward-Auth-Endpunkte von `oaap.core.identity`). Eine Regel je Site
wäre eine Regel, die an einer Site vergessen wird.

**Offen geblieben:** Ein `404`, das das Gateway selbst für einen Pfad
ohne erklärte Route gibt, trägt weiterhin keine CORS-Kopfzeile. Gleiche
Klasse, bewusst nicht hier gelöst — das braucht Kopfzeilen im Gateway
statt in der Identität.

**Zweitens: das befristete Protokoll je Instanz (RFC-0038 D3).** Die
Sites einer Instanz dürfen ein eigenes Zugriffsprotokoll schreiben —
**nur** solange für diese Instanz ein Diagnose-Fenster offen ist. Ein
Dauerprotokoll je Instanz gibt es ausdrücklich nicht. Öffnen fügt es an
**jedem** Eingang der Instanz hinzu (LAN-Port, automatischer Name, eigene
Namen, Aliasse) und lädt das Gateway sanft neu; Schließen oder Ablauf
entfernt es und **löscht** die Datei. Aufgezeichnet wird ab dem Öffnen,
und die Datei ist in der Größe begrenzt.

**Was dabei nie geschrieben werden darf** — ein MUSS dieser Spezifikation
und keine Eigenschaft, die man von der Voreinstellung eines Log-Moduls
erbt: der Query-Teil der Anfrage, der **Wert** von `Authorization` und
`Cookie`, jedes `Set-Cookie`, die `X-OAAP-*`-Kopfzeilen, der Query-Teil
eines `Location` und Inhalte. Erhalten bleiben muss dagegen die
**Tatsache**, dass ein Nachweis dabei war (ein fester Platzhalter statt
des Werts): Genau sie unterscheidet „kein Schlüssel geschickt" von
„falscher Schlüssel" — die Frage, für die es dieses Fenster gibt.

## Deutsche Zusammenfassung (v0.2.8 — offene Verbindungen überstehen das Neuladen, und das Dauerprotokoll wird gefiltert)

**Erstens: Ein Ausrollen trennt keine fremden Verbindungen mehr.** Jedes
Ausrollen irgendeiner App lädt die Konfiguration des Gateways neu. Bis
0.2.7 wurden dabei **alle** offenen WebSocket- und SSE-Verbindungen
**aller** Apps des Knotens getrennt — auf oaap-test gemessen, in
derselben Sekunde. Jetzt verbindlich: Ein Neuladen trennt keine
bestehende Verbindung. Die Referenz hält sie bis zu 12 Stunden an der
alten Konfiguration fest. Gilt für App-Routen an jedem Eingang, für die
Edge-Weiterleitung und für den Broker. **Nicht** geschützt, und so
gewollt: eine Verbindung zu einer App, die **selbst** neu ausgerollt
wird — ihr Container stoppt. Auch das nächtliche Backup stoppt Container
kurz. Clients müssen also weiterhin neu verbinden können; nur das
Ausrollen des Nachbarn ist kein Grund mehr dafür.

**Zweitens: Das Dauerprotokoll schreibt keine Schlüssel mehr.** Das
Gateway protokolliert jeden Zugriff auf einen veröffentlichten Namen
(Portal, Instanz-Namen, eigene Adressen, Edge); die LAN-Eingänge nicht.
Bis 0.2.7 stand dort die vollständige Adresse samt Query-Teil. Jetzt
gelten dieselben Regeln wie für das Diagnose-Protokoll, aus **einer**
gemeinsamen Definition: kein Query-Teil, keine Werte von
`Authorization`/`Cookie` (nur die Tatsache, dass einer dabei war), kein
`Set-Cookie`, keine `X-OAAP-*`, kein Query-Teil in `Location`. **Der Pfad
bleibt vollständig** — ein Schlüssel, den eine App in den Pfad legt,
steht weiterhin im Protokoll. Empfehlung an Apps: Geräte- und
Freigabeschlüssel ins **Fragment** der Adresse (`#…`) legen, das der
Browser nie an einen Server schickt. Die Prüfung war bdt-hub am 08.08.
zugesagt und ist erst jetzt eingelöst, als die zweite App dieselbe
Frage stellte.
