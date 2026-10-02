# RFC-0054: The MQTT Broker App — a Mosquitto With Named Accounts and Topic Rights

- **Status:** **Draft (2026-10-02)** — for Jörg's decisions (§7). Nothing
  built.
- **Date:** 2026-10-02
- **Authors:** Jörg (the wish: a Mosquitto as an OAAP app, no anonymous
  access, machine and human accounts, topic rights, and usable for
  smart home, events and the twin as well), Claude (facts measured in
  the code, design)
- **Depends on:** RFC-0052 (the sender and the security requirements of
  its §6.4, which this app must meet), RFC-0015 (a declared endpoint,
  granted per instance), RFC-0016 (apps that hold their own state)
- **Related:** RFC-0032 / `oaap.events.broker` (the platform's own
  broker, deliberately **not** replaced, §1 fact 1)
- **Driver:** RFC-0052 stage 3 needs a real broker to be measured
  against, and the operator needs one that is his own.

## Summary

One OAAP app, **`mqtt-broker`**: Mosquitto in one container, together
with a small admin page for **named accounts** and their **rights per
topic tree**. **No anonymous access**, **TLS only**, passwords stored
hashed, the password and access-list files **generated** from the
account list and reloaded without a restart. It meets every requirement
of RFC-0052 §6.4 and is not limited to node metrics: a person or a
service account may be granted writing on a smart-home or events tree.
It is reached from outside through **one declared endpoint** that a
`server_admin` grants on an `exposed` node. Its certificate comes from a
**private CA the app creates itself**; the platform-issued certificate
of RFC-0015 (shape 1) is not built and is not waited for.

## 1. Facts (read in the code, 2026-10-02)

1. **A broker already exists** as a platform service
   (`oaap.events.broker`, node profile `broker`): Mosquitto with the
   `mosquitto-go-auth` plugin, every `CONNECT` and topic action decided
   live by identity from RFC-0027 keys, rights scoped to a tenant
   (`oaap/<tenant-id>/#`). It has `allow_anonymous false` already. What
   it does **not** have: **a TLS listener** (raw port 1883 is plain,
   published only on an `exposed` node; its WebSocket listener gets TLS
   only through the gateway) and **any principal that is not a
   tenant's** — no node account, no operator account for his own trees.
   The metrics sender speaks MQTT over TCP with TLS, so it cannot use
   it as it is.
2. **An app may declare one endpoint** (RFC-0015): protocol, container
   port, `reason`, optionally `fixed`. Nothing is published until a
   `server_admin` grants it, and only on a node with the profile
   `exposed`. A **fixed** port must lie in **8200–8299** (reference
   0.1.34): MQTT's own 8883 is not available as a published number.
   The sender takes any port in its URL, so this costs nothing.
3. **Certificates for non-HTTP endpoints are not built.** RFC-0015
   decided shape 1 (the platform obtains the certificate and mounts it
   into the app); the reference has nothing of it. The gateway's
   certificates cover HTTP routes only.
4. **An app can carry an admin page.** A route with `roles:
   [server_admin]` puts the gateway's login and role check in front of
   it, and the app receives the identity headers (RFC-0040). Apps with
   several containers and with `config` keys that the node generates
   (`generate: token`) exist (livekit, keycloak).
5. **Mosquitto does what is needed, by its own features:**
   `allow_anonymous false`; `password_file` with hashed entries
   (`mosquitto_passwd`); `acl_file` with one block per user and
   `topic read|write|readwrite <filter>` (an allow-list: what is not
   written is denied); a re-read of both files on `SIGHUP`; TLS
   listeners with a private certificate; MQTT 5 with a reason code on a
   denied publish or subscribe. **These are facts of the product, not
   yet measured here** — stage 1 measures them.

## 2. What the app is

One container (`build: .`, an image on `eclipse-mosquitto` plus Python
and OpenSSL) running **two processes**: Mosquitto in the foreground,
the admin page in the background. One container because the admin
process must send `SIGHUP` to Mosquitto after every change; two
containers would need a shared process namespace or a control channel
for nothing. State lives in the instance's data volume:
`accounts.json` (the list, with password **hashes**), the generated
`passwd` and `acl` files, the CA and the server certificate, and
Mosquitto's persistence file (retained messages survive a restart).

- **Listeners.** One: TLS, container port **8283** (a number in the
  fixed range, §1 fact 2). **No plain listener**, no WebSocket listener
  in this RFC.
- **The endpoint.** Declared as `endpoints: - name: mqtts, protocol:
  tcp, container_port: 8283, fixed: true`, with a `reason` that says who
  gets in: *named accounts with a password, over TLS; nothing is
  readable or writable without one.* The operator grants it (RFC-0015)
  and forwards the port on the router; until then the broker answers
  only on the node's own network.
- **The admin page.** Route `/`, role `server_admin` only. It lists the
  accounts and lets the operator create one (the password is generated
  and **shown once**), set an account's grants, rotate its password and
  delete it; and it offers the **CA certificate for download**, which
  every client that must verify this broker needs (`oaap metrics sender
  set --ca FILE`). Every change is one line in the app's log (who, what,
  which account; never a password).
- **Health.** The health check is the admin page; the broker's
  listener is checked by the app's own start script (it exits when the
  generated files are unreadable).

## 3. Accounts and rights

An account has a **name**, a **kind** and **grants**; its password is
hashed, never stored or shown again.

| Kind | Made for | Grants |
|------|----------|--------|
| `node` | one OAAP node (RFC-0052) | fixed: **write** `<root>/<node-id>/#`, nothing else. Cannot subscribe. Made from a node-id and the root (default `oaap-node`). |
| `person` | a human, a tool | free list: `read`, `write` or `readwrite` on a topic filter, as many as needed |
| `service` | smart home, the twin's relay, another app | the same free list |

- **Rights are per tree** (RFC-0052 §6.4 point 2). A person or a
  service may be granted **writing** on a smart-home tree, an events
  tree, the twin's tree: the broker is not a read-only mirror.
- **The metrics branch is protected from everyone but its node.** The
  root is a setting of the app (default `oaap-node`; it must equal the
  `--root` of the senders). The generator **refuses a write grant, for
  a `person` or `service`, whose filter could match anything under that
  root** — `#`, `oaap-node/#`, `+/oaapx02/#` — and says which one. A
  value on that branch is therefore always a value the node sent. Reading
  it is an ordinary grant.
- **Names are unique and cannot be reused silently.** A node account is
  bound to its node-id, so a second node with the same name is refused
  at publish, not by luck (RFC-0052 §4).
- **No wildcard account, no shared account, no anonymous.**

## 4. The files, and failing closed

`accounts.json` is the only source. After every change the app
**generates** `passwd` and `acl` from it into new files, **checks** them
(parses them; runs `mosquitto_passwd`'s own format check), replaces the
old ones atomically and sends `SIGHUP`. A generation that fails leaves
the old files and the old behaviour in place and shows the error. The
files are never edited by hand and are not mounted outside this
container. **A broker whose `passwd` or `acl` file is missing or
unreadable at start does not start** (the start script exits; the
instance shows as down) — it never falls back to open.

## 5. Certificates

On the first start the app creates **its own CA** (long-lived, the
private key stays in the data volume) and a **server certificate**
signed by it, naming the hostnames the operator sets in the app's
config (`BROKER_HOSTNAMES`, comma separated; the node's name and its
LAN address by default). The server certificate is renewed by the app
when less than 30 days remain; the CA certificate is what clients
trust. This is a **deliberate stand-in**: a client must be given the CA
file once, which suits the nodes (the sender has `--ca`) and not a
browser. When the platform-issued certificate (RFC-0015 shape 1)
exists, the app switches to it and the CA stays only for clients that
pinned it. Whether Mosquitto picks up a renewed certificate on
`SIGHUP` or needs a restart is **measured in stage 1**, and the renewal
does whichever is true.

## 6. Security, said in one place

- No anonymous access; no plain listener; named accounts only; hashed
  passwords; TLS 1.2 or later.
- Rights are enforced by the broker's access list, generated from one
  list; a stolen node account can publish only under its own name and
  can read nothing.
- The CA's private key and the hashes are in the instance's data and so
  in its **backup** (RFC-0029), which is written with mode 0600 like
  every backup; restoring a backup restores the accounts and the CA —
  the clients keep working.
- The platform stops guaranteeing at this port exactly what RFC-0015
  says it stops guaranteeing on any granted endpoint: no gateway login,
  no throttle, no access log. The broker's own login is the only gate,
  which is why §3 and §4 are requirements, not features. Mosquitto's own
  connection and message-size limits are set (`max_connections`,
  `message_size_limit`) so that one client cannot fill the node.
- The platform's own `broker` service stays as it is: separate failure
  domain, separate accounts (tenants' keys). **One set of accounts for
  both** — node and reader keys as principals of the platform broker
  (RFC-0052 §9 stage 5) — remains the later step.

## 7. Decisions for Jörg

1. **A new app, or the platform broker extended?** Recommended: **a new
   app** (§1 fact 1: the platform broker has no TLS listener and only
   tenant principals; the operator's own trees want their own domain).
2. **One container with two processes** (Mosquitto + admin page), as in
   §2? Recommended: yes. The alternative, two containers, needs a
   control channel for the `SIGHUP`.
3. **A private CA the app creates**, until the platform issues
   certificates (§5)? Recommended: yes — it unblocks the sender
   measurement today and costs one file handed to each client.
4. **Accounts managed on an admin page** for `server_admin` (§2)? Or the
   command line only? Recommended: the page, as the app's only route;
   a command-line twin can follow.
5. **Container port 8283**, the published number the operator's grant
   assigns? Recommended: yes; it is configuration of the app's
   endpoint, and the senders carry whatever port the URL names.
6. **The name `mqtt-broker`**, class `service`? Recommended: yes.

## 8. Stages

1. **The image, the generator, the files** — against a real Mosquitto
   in Docker on `oaap-test`, without the gateway or the page: account
   list in, `passwd`/`acl` out, SIGHUP reload, TLS with the private CA,
   fail-closed start. Measures §1 fact 5: the PUBACK reason code, the
   SUBACK refusal, the reload of files and of a renewed certificate.
   Tests of the generator itself (the overlap rule of §3, the format
   check) need no Docker.
2. **The admin page** (§2): accounts, grants, password shown once, the
   CA download, the log line.
3. **The endpoint and the sender** — grant the endpoint, forward the
   port, then **RFC-0052 stage 3**: `oaap metrics sender set` on another
   node against this broker with `--ca`, the conformance tests of
   RFC-0052 §6.4 (anonymous refused, wrong password refused, a node
   account publishing under another name refused with the reason code
   and the queue **not** deleted, a reader that cannot write the
   branch, a person granted a smart-home tree who can, a removed
   account refused), an outage of the broker and of the network with a
   real backlog, a real reboot in the middle of a run.
4. *Later:* the platform-issued certificate; a command-line twin of the
   page; a WebSocket listener; one set of accounts with the platform
   broker.

## 9. Out of scope

Bridging brokers; clustering; MQTT-specific monitoring beyond the app's
health; dashboards of the received data; per-message authorisation
beyond topic filters; client certificates (a later hardening);
alerts.

---

## Deutsche Zusammenfassung

**Worum es geht:** Für den Metrik-Sender (RFC-0052) und für deine eigenen
Zwecke (Smarthome, Ereignisse, Zwilling) soll ein **Mosquitto als
OAAP-App** laufen — ohne anonymen Zugang, mit Konten und Themenrechten.

**Was ich im Code gefunden habe:**
- Der **Plattform-`broker`** gibt es schon (Mosquitto mit Anmeldung über
  identity, Rechte je Mandant, kein anonymer Zugang). Er hat aber **kein
  TLS auf dem rohen Port** und **kennt nur Mandanten-Schlüssel** — kein
  Knotenkonto, kein Betreiberkonto. Der Sender kann ihn so nicht nutzen.
  Er bleibt unverändert.
- Eine App darf **einen Endpunkt** erklären; veröffentlicht wird er erst
  mit deiner Freigabe auf einem `exposed`-Knoten. Eine feste Portnummer
  muss in **8200–8299** liegen, also nicht 8883 — für den Sender egal.
- **Zertifikate für Nicht-HTTP-Endpunkte gibt es noch nicht** (RFC-0015
  Form 1 ist beschlossen, nicht gebaut).

**Was vorgeschlagen wird:**
- Eine App **`mqtt-broker`**: ein Container mit Mosquitto und einer
  kleinen **Verwaltungsseite** (nur `server_admin`). Konten mit Art
  (**Knoten**, **Person**, **Dienst**) und Rechten je Themenbaum; das
  Passwort wird erzeugt und **einmal angezeigt**, gespeichert nur als Hash.
- **Knotenkonten** dürfen nur unter `<Wurzel>/<Knoten>/#` schreiben und
  nichts lesen. **Personen- und Dienstkonten** bekommen frei Rechte —
  **auch Schreiben** auf Smarthome- oder Ereignisbäumen. Nur der
  Metrik-Zweig ist für alle außer dem Knoten selbst nicht beschreibbar:
  der Erzeuger **lehnt** ein Schreibrecht ab, dessen Filter dort treffen
  könnte (`#`, `oaap-node/#`, `+/knoten/#`).
- Passwort- und Zugriffsdatei werden aus **einer** Kontenliste
  **erzeugt**, geprüft, atomar ersetzt und mit `SIGHUP` neu eingelesen.
  Fehlt eine Datei beim Start, **startet der Broker nicht** — nie offen.
- **Nur TLS**, kein Klartext-Port. Das Zertifikat kommt vorerst von einer
  **eigenen CA, die die App selbst anlegt**; jeder Client bekommt die
  CA-Datei einmal (`--ca` im Sender). Das ist ein bewusster Notbehelf, bis
  die Plattform Zertifikate ausstellt.
- Erreichbar von außen über den **einen Endpunkt** (Container-Port 8283),
  den du freigibst und am Router weiterleitest.

**Zu entscheiden (§7):** neue App statt Plattform-Broker erweitern
(Empfehlung: neue App), ein Container mit zwei Prozessen, eigene CA vorerst,
Konten über die Seite statt nur per Kommandozeile, Port 8283, Name
`mqtt-broker`.

**Stufen (§8):** 1 Image + Erzeuger gegen einen echten Mosquitto (hier wird
auch gemessen, was ich bisher nur vom Produkt weiß: Ablehnungscode, Neuladen
der Dateien und des Zertifikats), 2 Verwaltungsseite, 3 Endpunkt + der
**Sender-Test gegen diesen Broker** (RFC-0052 Stufe 3), 4 später.

**Stand:** Entwurf, nichts gebaut.
