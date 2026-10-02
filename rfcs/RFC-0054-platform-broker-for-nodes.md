# RFC-0054: The Platform Broker for Nodes and Operators — Extending `oaap.events.broker` Instead of Building a Second One

- **Status:** **Draft (2026-10-02)** — direction decided by Jörg
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
   keeps them under `data/gateway/caddy-data` on the host; the platform
   has its own CA (RFC-0005) for names no public authority serves. The
   broker mounts none of it and has **no TLS listener**.
7. **Not measured yet:** that Mosquitto can read Caddy's certificate
   files as stored, and whether it picks up a renewed certificate on
   `SIGHUP` or needs a restart; that a denied publish comes back to an
   MQTT 5 client as reason code `0x87` through the go-auth plugin. Stage
   1 and stage 3 measure these; nothing below is claimed before then.

## 2. The TLS listener

A third listener on **8883**, `tls_version tlsv1.2` or later, with the
certificate and key of the node's external host name, taken **read-only
from the gateway's certificate storage** (the one place certificates are
managed — RFC-0015's shape 1, built for this service first). The
published port is **8883**: a platform service is not bound to the
8200–8299 range that an app's fixed endpoint is.

- On a node **with** an external host name the certificate is the
  public one, and a client needs no extra file.
- On a node **without** one (the LAN nodes) the certificate comes from
  the platform CA, and a client is given the CA certificate once
  (`oaap metrics sender set --ca FILE`). The CA file is offered where the
  keys are managed.
- The renewal follows what stage 1 measures (§1.7): a reload if Mosquitto
  takes one, otherwise a restart of the broker after the gateway has
  renewed.
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
  explicitly. **Which nodes carry both profiles today is not yet
  looked at**; the stage reads it from `oaap node show` on each node
  before it changes anything.

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
2. **Certificate from the gateway's storage, read-only**, and the platform
   CA for LAN nodes (§2)? Recommended: yes.
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

1. **Measure the open facts** (§1.7) on `oaap-test`: Mosquitto reading
   the certificate as Caddy stores it and what it does on renewal; the
   reason code of a denied publish through the plugin. No code kept
   unless it is the TLS listener itself.
2. **Rights in the check** (§4–§6): grants on keys, the access type
   respected, the node and operator kinds, the metrics-branch rule.
   Tests of the tenant boundary first (an old key behaves as before; no
   tenant key matches the root), then the new rules; `oaap key issue
   --kind node|operator`.
3. **The listeners** (§2, §3): 8883 with the gateway's certificate; the
   profile `broker-plain` and the overlay on the private address; the
   check of which nodes change.
4. **Management** (§7.5): the new kinds and a grant editor in "Zugänge".
5. **The sender against this broker** — RFC-0052 stage 3: the
   conformance tests of its §6.4 (anonymous refused, wrong key refused,
   a node key under another name refused with the reason code and the
   queue **not** deleted, a reader that cannot write the branch, an
   operator granted a smart-home tree who can, a revoked key refused),
   an outage with a real backlog, a real reboot in the middle of a run.

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
  (eine Stelle für Zertifikate; LAN-Knoten: Plattform-CA, die der Client
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

**Was ich nicht gemessen habe (§1.7):** ob Mosquitto Caddys Zertifikatsdateien
so lesen kann und was bei einer Erneuerung passiert; ob eine verbotene
Veröffentlichung durch das Plugin als Code `0x87` beim Client ankommt. Das
messen Stufe 1 und Stufe 5.

**Zu entscheiden (§7):** das Profil `broker-plain`, Zertifikat aus dem
Gateway-Speicher, 8883 unter der bestehenden Regel (`broker` + `exposed`),
Schlüssel nur durch `server_admin`, Verwaltung in der vorhandenen
Schlüsselseite, die Wurzel als Einstellung des Broker-Knotens.

**Stand:** Entwurf, Richtung entschieden, nichts gebaut.
