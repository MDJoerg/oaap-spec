# RFC-0054: The Platform Broker for Nodes and Operators — Extending `oaap.events.broker` Instead of Building a Second One

- **Status:** **Draft (2026-10-02)** — stages 1 and 2 done; direction decided by Jörg
  (extend the platform, no parallel path; the plain port only optional,
  for the intranet); §7 for the rest. Nothing built. **Replaces the
  first draft of this RFC** (an `mqtt-broker` app with its own accounts,
  its own CA and its own admin page; see the git history, `4ce3294`).
- **Date:** 2026-10-02
- **Authors:** Jörg (the wish: a broker with named accounts and topic
  rights, usable for node metrics and for smart home, events and the
  twin; and: no parallel path — extend the platform), Claude (facts read
  in the code, design)
- **Depends on:** RFC-0032 / `oaap.events.broker` (the broker this RFC
  extends), RFC-0027 (API keys — the credential), RFC-0052 (the sender
  and the security requirements of its §6.4, which this broker must
  meet), RFC-0011 (node profiles), RFC-0015 (`exposed`)
- **Extends:** `oaap.events.broker`, `oaap.core.identity` (the two
  `/mqtt-auth/*` routes and the key store), `oaap.core.gateway` (the
  certificates it already holds)
- **Driver:** RFC-0052 stage 3 needs a real broker to be measured
  against, and the operator wants one broker for everything his nodes
  speak MQTT about.

## Summary

The platform already has the broker and the accounts: Mosquitto whose
every connection and every topic action is decided live by identity,
from RFC-0027 keys. This RFC does not add a second broker. It gives that
one four things it lacks:

1. **A TLS listener** (8883) with the certificate the gateway already
   holds — one thing manages certificates.
2. **Rights as a list on a key** (a topic filter and *read* or *write*),
   instead of only "everything under my tenant". Today the access check
   ignores whether the client reads or writes.
3. **Two new key kinds:** a **node key**, bound to one node name, that
   may publish under `<root>/<node>/#` and nothing else; and an
   **operator key** with free rights per tree — including **writing**
   on smart-home, events and twin trees.
4. **The plain port as an option for the intranet only** (§3), off by
   default, switched on by a node profile, refused on a node with no
   private address.

The metrics branch is protected **in the access check itself**: nobody
but the matching node key may write on it. Management is the existing
key management (portal "Zugänge", `oaap key …`) with the new kinds.

## 1. Facts (read in the code, 2026-10-02)

1. **The broker** is Mosquitto with the `mosquitto-go-auth` plugin and
   the HTTP backend; `allow_anonymous false`; there is no local
   password file and no local ACL file. Two listeners: raw TCP **1883
   (plain)** and WebSocket 9001 (only through the gateway, which gives
   it TLS). It starts only on a node with the profile `broker`.
2. **`/mqtt-auth/getuser`** (identity) accepts a connection when the
   password is a valid, unscoped, unrevoked key token
   `oaapk_<id>_<secret>` and the user name is that same id; or when it is
   the relay's own login.
3. **`/mqtt-auth/aclcheck`** looks the key up by id and allows a topic
   when it lies under `oaap/<tenant-id>/…` — **the access type (read or
   write) that the plugin sends with every check is not used.** The relay
   is a second, non-tenant principal with its own rule: publish only,
   into a known tenant's tree. A principal that is not a tenant's
   already exists; this RFC makes it a pattern.
4. **Keys** are stored in identity's `api-keys.json` and managed in the
   portal ("Zugänge", RFC-0027) and with `oaap key issue|list|revoke`;
   revoking takes effect on the next check, because nothing is cached in
   a file.
5. **The raw port** is published to the host only when the node carries
   `broker` **and** `exposed`, by a compose overlay
   (`docker-compose.broker-exposed.yml`) that `_broker_compose_files()`
   adds. `exposed` is RFC-0015's profile for ports that bypass the
   gateway; the broker borrowed it instead of inventing a second grant.
6. **Certificates**: the gateway (Caddy) obtains and renews them and
   keeps them under `data/gateway/caddy-data` on the host. **The platform
   CA of RFC-0005 is accepted as an RFC but not built** (nothing in the
   code issues or serves it; the gateway only does on-demand ACME, and a
   LAN name gets no certificate). The broker mounts none of it and has
   **no TLS listener**. (An earlier draft of this RFC counted on that CA
   for LAN nodes; stage 3 corrected it, §2.)
7. **Measured on `oaap-test`, 2026-10-02 (stage 1)**, with Mosquitto
   2.0.18 and the plugin as the node runs them:
   - **A denied publish arrives as reason code `0x87`** in the `PUBACK`:
     a key published inside its own tenant tree and got a clean
     acknowledgement; the same key publishing on `oaap-node/…` and on
     another tenant's tree got `0x87` each time. The metrics sender's
     client (MQTT 5, written for RFC-0052) worked against the real
     broker on the first try (CONNECT, PUBLISH QoS 1, PUBACK).
   - **A wrong login arrives as `CONNACK` `0x87`** (not `0x86`): a wrong
     password, a wrong user name and a malformed password all gave it.
     The sender treats `0x86`, `0x87` and `0x8a` as a refusal.
   - **Caddy's storage cannot be mounted as it is.** Caddy keeps the
     certificate files with mode `0600`, owner root. Mosquitto drops to
     its own user (uid 1000) and **refuses to start**: `Unable to load
     server key file … Permission denied`. A copy is needed (§2).
   - **A renewed certificate is picked up on `SIGHUP`, without a
     restart.** With the key readable by uid 1000, a replaced
     certificate (serial 1001 → 2002) was served after `SIGHUP`; the
     process kept running (measured with the key at mode 640 group 1000
     and at 600 owner 1000).
   - **Not measured:** TLS with a certificate Caddy really obtained
     (`oaap-test` has none; `oaapx01` was not touched), the platform CA
     for a LAN name, the plain port from outside the platform network.

## 2. The TLS listener

A third listener on **8883**, `tls_version tlsv1.2` or later, with the
certificate and key of the node's external host name, **copied from the
gateway's certificate storage** (the one place certificates are obtained
and renewed — RFC-0015's shape 1, built for this service first). **A
copy, not a mount** (§1.7: Caddy's files are root-only and Mosquitto
runs as uid 1000): a step of the minutely host job compares the
modification time of Caddy's certificate with the copy's, and on a
change writes the pair into a directory only the broker's user reads
(mode 0600, owner uid 1000) and sends the broker `SIGHUP`, which
re-reads it without a restart (§1.7). The private key therefore exists
twice on the node, once in each owner's directory; that is the price of
not making Caddy's own storage readable to a broker. The
published port is **8883**: a platform service is not bound to the
8200–8299 range that an app's fixed endpoint is.

- On a node **with** an external host name the certificate is the
  public one, and a client needs no extra file.
- On a node **without** one (the LAN nodes) the gateway has nothing to
  give, so **the node issues its own**: a CA of its own, made once by
  `oaap broker sync` (its key in `data/broker-ca/`, mounted nowhere), and
  a server certificate signed by it, valid 397 days and renewed at 30
  left. It names `broker` (the platform-network name an in-platform client
  uses), the host name, the external name if any, and the LAN address; a
  change of the address issues a new one from the **same** CA, so no client
  must be given anything again. A client is given the CA certificate once:
  `oaap broker ca > ca.crt`, then `oaap metrics sender set --ca ca.crt`.
- **The source is chosen on every run**: if the gateway holds a
  certificate for the node's external name it is used (and a switch from
  the node's own to the gateway's needs only a `SIGHUP`); otherwise the
  node's own. The first certificate of all needs a **restart** of the
  broker (a listener cannot be added by a reload — Mosquitto's rule); every
  later change, a `SIGHUP`.
- The renewal is the copy step above plus `SIGHUP` (measured, §1.7); no
  restart.
- 8883 is published to the host on a node that carries `broker` **and**
  `exposed` — the existing rule (§1.5), unchanged: an operator decides
  that a port bypasses the gateway.

## 3. The plain port: only for the intranet, and only by choice

Port 1883 (no TLS) stays available for **devices that cannot speak TLS**
— the smart-home case — and is **off on the host by default**. Inside
the platform network it stays reachable as today (the relay and any
in-platform publisher need no host port).

- It is switched on by its **own node profile**, **`broker-plain`**,
  set with `oaap node add-profile broker-plain` — **CLI only**, like every
  profile (RFC-0011: the portal must not be able to grant itself a
  power). No new kind of setting: it is the mechanism the node already
  has.
- It is published **bound to the node's private LAN address**, not to
  all interfaces (`<lan-address>:1883:1883`, not `1883:1883`).
- **It is refused on a node that has no private address** (a server with
  only a public one): the profile cannot be added there, and the
  refusal says why. "Intranet only" is enforced by the node, not left to
  the operator's firewall.
- `oaap node show` and the health page print, in a line of their own,
  that this node accepts keys in the clear on its LAN. A key sent over
  1883 can be read by anyone on that network; the line says so.
- It **replaces** today's rule that `exposed` alone publishes 1883 on
  all interfaces. That is a behaviour change on every node that carries
  `broker` and `exposed` today; stage 3 lists them first and moves each
  explicitly. **Read on 2026-10-02 (`oaap node show`):**
  `raspberrypi` and `oaap-bernd` carry no profile; `oaap-demo` and
  `oaapx01` carry `dev` and `exposed` but not `broker`; `oaap-test`
  carries `broker`, `dev` and `store` but not `exposed`. **No node
  carries `broker` and `exposed` together, so port 1883 is published on
  no node today and the change touches none.** (`oaapx02` is the
  operator's own and was not read; stage 3 asks before it moves
  anything.)

## 4. Rights as a list

A key may carry **grants**: `{filter, read|write|readwrite}`. The access
check evaluates the topic against the grants and **respects the access
type** the plugin sends (publish = write, subscribe and receive = read;
a subscription filter is checked as the filter it is, wildcards
included, as today).

- **A tenant key is the special case** whose grant is
  `oaap/<tenant-id>/#`, read and write. Nothing changes for it, and an
  existing key without grants behaves exactly as before.
- Grants are set when the key is issued and changed afterwards by
  `server_admin` only. A change takes effect at the next check.

## 5. Two new key kinds

| Kind | Made for | Grants |
|------|----------|--------|
| `node` | one OAAP node (RFC-0052) | fixed: **write** `<root>/<node>/#`, nothing else; cannot subscribe. Made from a node name and the root (default `oaap-node`, the setting of RFC-0052 §2). |
| `operator` | a person, a tool, a device, another service of the operator | free list of grants on any tree *outside the tenant trees*; **writing allowed**. |

- Both are **issued by a `server_admin`** and are not tenant keys (they
  belong to the operator, not to a tenant; a tenant's `tenant_admin`
  cannot make one).
- The credential is the key token, exactly as for a tenant key (user
  name = id, password = token), so the sender and any smart-home client
  take it without a change.
- A node key is bound to its node name: a second node cannot publish
  under it, and **a node key used for another node's name is refused at
  publish** (RFC-0052 §4).
- Operator keys may be **named** and noted (who, what for) like any key.

## 6. The metrics branch, protected where the decision is made

The root of the metrics branch is a setting of the node that carries the
broker (default `oaap-node`; it must equal the senders' `--root`). In
`aclcheck`:

- **writing under the root is denied to every key except the node key
  bound to that very node name** — an operator key and a tenant key
  included, *whatever grants they carry*. A value on the branch is
  therefore always a value the node sent. This holds even if somebody
  issues an operator key with a grant that overlaps the root (`#`,
  `+/n1/#`): the check, not the issuing, is the gate.
- **reading** the root is an ordinary grant on an operator key.
- **a tenant key can never match** the root (it matches only
  `oaap/<tenant-id>/…`), as the platform broker's design already
  guarantees (RFC-0052 §6.3).

## 7. Decisions

Decided (Jörg, 2026-10-02): **extend the platform, no parallel broker**;
**the plain port only optional and only for the intranet.**

1. **The plain port is its own profile, `broker-plain`**, published on the
   private address, refused on a node without one (§3)? Recommended: yes.
   Alternatives: a setting beside the profiles (a new concept), or
   keeping `exposed` as the switch (then 1883 stays on all interfaces).
2. **Certificate from the gateway's storage, copied**, and a CA of the
   node's own for nodes the gateway gives nothing (§2)? Recommended: yes.
   **Decided in the build (stage 3)**, because the platform CA it first
   named does not exist (§1.6).
3. **8883 is published under the existing rule** (`broker` + `exposed`),
   not under a new one (§2)? Recommended: yes.
4. **Node and operator keys are issued by `server_admin` only** (§5)?
   Recommended: yes.
5. **Management in the existing key page and `oaap key`**, with the new
   kinds and a grant editor, not a page of its own? Recommended: yes.
6. **The metrics root is a setting of the broker's node**, enforced in
   `aclcheck` (§6)? Recommended: yes.

## 8. Meeting RFC-0052 §6.4

| §6.4 requirement | Met by |
|---|---|
| no anonymous access | `allow_anonymous false`, live check (§1.1) |
| node account bound to one node name, write only on its own branch, no read | node key (§5) |
| every other account: read the branch if granted, nobody writes it | §6, in the check |
| rights per tree; persons may write elsewhere | operator key (§5) |
| rights enforced by the broker from one list | the key store is the list; the check is live (§1.4) |
| TLS only | 8883 (§2); the plain port only on the intranet by choice (§3) |
| individually revocable | revoke the key; effective at the next check |
| fail closed | identity unreachable ⇒ nobody connects; the node's queue holds the data (RFC-0052) |
| passwords hashed, not in the clear | key tokens are stored as digests like every key (RFC-0027) — to be confirmed for the new kinds in stage 2 |
| the branch outside every tenant tree | §6 |

RFC-0052 still works against **any** MQTT 5 broker that meets §6.4,
including a plain Mosquitto; this RFC is how an OAAP node meets it.

## 9. Stages

1. **BUILT, as measurement (2026-10-02):** the open facts of §1.7 on
   `oaap-test`, with a throwaway key and throwaway containers (the key
   revoked afterwards). Two of three answers confirmed the design
   (`0x87`, reload on `SIGHUP`); one **changed** it (a copy instead of a
   mount, §2).
2. **BUILT (reference 0.1.178), measured on `oaap-test` (2026-10-02):** with a real node key and a real operator key against the real broker — a node key publishes only under its own name (another node's name and any other tree: `0x87`), its subscriptions, even to its own branch, are refused (`SUBACK 0x87`); an operator key publishes and subscribes on its granted tree (including a `+` filter inside the grant), is refused on the metrics branch for writing, on a tenant tree and on `#` and `$SYS/#` for subscribing, but may read the metrics branch; both keys are refused on an HTTP path with 403. Keys revoked afterwards. **Rights in the check** (§4–§6): grants on keys, the access type
   respected, the node and operator kinds, the metrics-branch rule.
   Tests of the tenant boundary first (an old key behaves as before; no
   tenant key matches the root), then the new rules; `oaap key issue
   --kind node|operator`.
3. **BUILT (reference 0.1.179), measured on `oaap-test` (2026-10-02):** the first `oaap broker sync` made the node's CA and a certificate (names `broker`, `oaap-test`, `10.10.10.96`) and restarted the broker, which then listened on 8883; the real sender (RFC-0052) published three queued samples over TLS verifying that CA, and an operator key read all three back as retained values; **without the CA the handshake failed (`SSLCertVerificationError`), nothing was sent and the sample stayed queued**; a certificate for a changed address was picked up on `SIGHUP` (serial and names changed, the broker's start time did not) and the real `broker sync` path did the same; `exposed` published 8883 on all interfaces and a client verified the certificate against the CA from outside the platform network; `broker-plain` published 1883 on `10.10.10.96` only (not `0.0.0.0`), `oaap node show` carried the warning line, removing both closed both ports and dropped the address from `.env`. Not measured: a certificate Caddy really obtained, the plain port with a real device, an update with `broker-plain` held. **BUILT (reference 0.1.179).** **The listeners** (§2, §3): 8883
   with the broker's certificate (the gateway's copied, or the node's own
   CA), the TLS listener only when a certificate is in place; the profile
   `broker-plain` and an overlay on the private address that makes Compose
   REFUSE without one (`${BROKER_PLAIN_BIND:?…}`) instead of publishing on
   every interface; `oaap broker sync|show|ca`, a step of the minutely job
   that also follows a changed LAN address. 8883 now replaces 1883 in the
   `exposed` overlay (no node was affected, §3).
4. **Management** (§7.5): the new kinds and a grant editor in "Zugänge".
5. **MEASURED (2026-10-02, reference 0.1.179 measured, 0.1.180 fixes).** **The sender against this broker** — RFC-0052 stage 3: the
   conformance tests of its §6.4 (anonymous refused, wrong key refused,
   a node key under another name refused with the reason code and the
   queue **not** deleted, a reader that cannot write the branch, an
   operator granted a smart-home tree who can, a revoked key refused),
   an outage with a real backlog, a real reboot in the middle of a run.

### 9.1 Stage 5 measurement (oaap-test broker, Raspberry Pi sender, over the LAN)

Setup: the broker on oaap-test with `exposed` (8883 published), a node key
for `raspberrypi`, the node's CA copied to the Pi, the real sender on the
Pi, unchanged from the fleet (0.1.179).

- **Normal run:** 300 values delivered over TLS with verification, queue 0.
- **Outage with a real backlog:** the broker container stopped for four
  minutes. The sender kept sampling, the queue grew to 4, the back-off ran
  60 s → 120 s (`ConnectionRefusedError`, never a crash, the unit never
  failed). After the broker came back the next try delivered everything:
  queue 0, numbers 302–307 acknowledged, nothing lost.
- **A node key under another name:** the sender configured as `otherbox`
  with the key of `raspberrypi`: the broker answered PUBACK `0x87`; the
  sender reported *the broker refused this publish … reason 0x87*, waited
  15 minutes, and the **queue was not deleted**.
- **A revoked key:** `sender test` → *the broker refused the login (0x87)*.
- **A real reboot of the Pi** (`systemctl reboot`): the queue (4 values),
  the numbering and the back-off wait survived it.

**Two faults found, both fixed in 0.1.180:**

1. `--ca /tmp/ca.crt` stored a **path**. `/tmp` is a tmpfs on the Pi; the
   reboot removed the file and the sender could never verify the broker
   again (data stayed queued, nothing leaked, but nothing flowed). The
   sender now **copies** the CA into its own directory
   (`data/metrics-sender/ca.crt`).
2. A **corrected** sender (right key after a wrong one) still waited out
   the old back-off. Setting a sender now **resets** its state: failures
   and wait of the old target say nothing about the new one.

Not measured: the reader that cannot write the branch and the human
account with a smart-home tree over the network (both measured against
the broker itself in stage 1), the Pi's sender after a reboot **with**
the fix (the Pi is on 0.1.179; the fix is covered by test only), an
outage longer than the 7-day bound.

## 10. Out of scope

Bridging brokers; clustering; client certificates (a later hardening);
alerts and dashboards of the received data; a WebSocket listener beyond
the gateway route that exists; a separate account store for MQTT.

---

## Deutsche Zusammenfassung

**Worum es geht:** Du willst keinen zweiten Weg, sondern die Plattform
erweitern. Deshalb ersetzt dieser RFC den ersten Entwurf (eine eigene
`mqtt-broker`-App mit eigener CA und eigener Verwaltungsseite; er steht in
der Git-Historie, `4ce3294`).

**Was schon da ist:** Der Plattform-Broker (Mosquitto) fragt bei **jeder**
Verbindung und **jeder** Themenaktion live bei identity nach, mit dem
RFC-0027-Schlüssel — kein anonymer Zugang, keine Passwortdatei, kein
Neuladen, Sperren wirkt sofort, die Schlüsselverwaltung gibt es im Portal.
Es gibt sogar schon ein Konto außerhalb der Mandanten (das Relais).

**Was ihm fehlt und gebaut wird:**
- **TLS auf 8883** mit dem Zertifikat, das der Gateway ohnehin verwaltet
  (eine Stelle für Zertifikate; LAN-Knoten: eine CA des Knotens selbst — die Plattform-CA aus RFC-0005 gibt es nicht —, die der Client
  einmal bekommt).
- **Rechte als Liste am Schlüssel** (Themenfilter + lesen/schreiben).
  Heute **ignoriert** die Prüfung, ob gelesen oder geschrieben wird.
- **Zwei neue Schlüsselarten:** **Knotenschlüssel** (darf nur unter
  `<Wurzel>/<Knoten>/#` schreiben, nichts lesen) und **Betreiberschlüssel**
  (freie Rechte je Baum, **auch Schreiben** für Smarthome, Ereignisse,
  Zwilling).
- **Schutz des Metrik-Zweigs in der Prüfung selbst:** Schreiben unter der
  Wurzel darf **nur** der passende Knotenschlüssel — egal welche Rechte ein
  anderer Schlüssel hat.

**Der Klartext-Port (deine Frage):** Ja, per Konfiguration. Er bekommt ein
**eigenes Knotenprofil `broker-plain`** (nur per Kommandozeile, wie alle
Profile — also kein neues Konzept), ist **aus**, solange es nicht gesetzt
ist, wird nur an die **private LAN-Adresse** gebunden und wird auf einem
Knoten ohne private Adresse **abgelehnt**. Die Seite „Knoten" und die
Gesundheitsseite sagen in einer eigenen Zeile, dass dieser Knoten Schlüssel
im Klartext im LAN annimmt. Das ändert die heutige Regel, nach der
`exposed` allein 1883 auf allen Schnittstellen veröffentlicht; die Stufe
prüft zuerst, welche Knoten betroffen sind.

**Gemessen (Stufe 1, 02.10., auf oaap-test):** Eine verbotene
Veröffentlichung kommt durch das Plugin als Code **`0x87`** beim Client an,
ein falsches Passwort als `CONNACK 0x87`; der Sender-Client funktionierte
gegen den echten Broker auf Anhieb. Ein erneuertes Zertifikat wird mit
**`SIGHUP` ohne Neustart** übernommen. **Aber:** Caddys Dateien (Modus 0600,
Eigentümer root) kann Mosquitto nicht lesen und startet dann nicht — es
braucht eine **Kopie** (ein Schritt im minütlichen Host-Lauf, der bei
Änderung kopiert und `SIGHUP` schickt), keinen Einhängepunkt. **Nicht
gemessen:** TLS mit einem echten Caddy-Zertifikat, die Plattform-CA für
einen LAN-Namen, der Klartext-Port von außen.

**Zu entscheiden (§7):** das Profil `broker-plain`, Zertifikat aus dem
Gateway-Speicher, 8883 unter der bestehenden Regel (`broker` + `exposed`),
Schlüssel nur durch `server_admin`, Verwaltung in der vorhandenen
Schlüsselseite, die Wurzel als Einstellung des Broker-Knotens.

**Stand:** Entwurf, Richtung entschieden; Stufe 1 (Messung) gemacht,
Stufe 3 (Listener, Zertifikat, Profil `broker-plain`) gebaut und getestet, noch auf
keinem Knoten; Stufe 2 (Rechte in der Prüfung, Knoten- und Betreiberschlüssel) gebaut und
getestet, noch auf keinem Knoten.
