# RFC-0052: The Metrics Sender — Forwarding the Node Queue to an MQTT Broker

- **Status:** **Accepted (2026-10-02)** — Jörg took all recommendations
  of §8 as proposed and added the security requirements of §6.4 for the
  receiving broker. Nothing built.
- **Date:** 2026-10-02
- **Authors:** Jörg (the wish: send the real-time data buffered, through
  a queue, to an MQTT node), Claude (facts measured in the reference
  code, design)
- **Depends on:** RFC-0051 (the queue, the message, the topic branch —
  all fixed there and **not reopened here**), RFC-0032 /
  `oaap.events.broker` (the topic tree this branch stays outside of,
  the key-as-credential pattern)
- **Related:** RFC-0033 / `oaap.net.destinations` (why this is *not* a
  destination, §3), RFC-0021 (fleet keys — the same idea of a key that
  grants one thing)
- **Extends:** `oaap.core.host` (the minutely host job)
- **Driver:** RFC-0051 stage 3 writes every sample into a numbered,
  bounded local queue. Nothing reads it. Until something does, the
  queue only fills to its limits and the data never leaves the node.

## Summary

A small **sender on the host** reads the queue from the first
unacknowledged number, publishes each sample to an MQTT broker the
operator names, and **deletes a sample from the queue only after the
broker has acknowledged it** (`queue_ack`, already built). It runs in
the same minutely job as the sampler, keeps no process of its own, and
**never makes that job fail**: a broker that is down costs a counted,
shown delay and, after the queue's limits, counted loss — never the
health of the node. Delivery is **at least once**; the receiver may see
a sample twice, never a gap that the node could have avoided.

## 1. Facts (measured in the reference code, 2026-10-02)

1. **The queue is there and numbered** (reference 0.1.175):
   `metrics.queue_pending(dir, limit)` returns unacknowledged entries
   oldest first, `queue_ack(dir, upto)` advances the mark and deletes,
   `queue_status` reports pending, `lost`, `purged`. The sender needs
   nothing more from the queue.
2. **The message is fixed** (RFC-0051 §3): `metrics.sample_lines(node,
   entry)` turns one queue entry into up to three messages
   `{"v":1,"node","t","m","x"}`. Nothing calls it yet.
3. **The host has Python 3 and no MQTT library.** The installer does not
   install one, and the host job runs as the node's own `appctl.py`.
   A sender that needs `pip install` is a new thing every node must
   have before it can update.
4. **A node has no identity of its own.** The only name it carries is
   the host name (`socket.gethostname()`, used in backup file names).
   `node.json` holds profiles (RFC-0011), not an identity. RFC-0051 wrote
   `<node-id>` in the topic and left its meaning open. This RFC must
   close it (§4).
5. **The job the sender would share is already crowded.** The minutely
   `oaap-instance-watch` unit runs the state index, then the sampler
   (`ExecStart=-…`, a failing step does not fail the unit). A sender
   that blocks on a dead network would delay the container-state view
   behind it.
6. **A destination is the wrong object.** `oaap.net.destinations` is a
   tenant's object, made for an *instance* that calls out through the
   gateway and must never hold the key. The metrics sender is the
   operator's own host process, belongs to no tenant, and reaches
   nothing through the gateway. Using a destination would put the
   operator's node credential into a tenant's namespace and its audit
   log.

## 2. What the sender does

Once per minute, after the sampler, in the same unit:

1. If a **backoff** is running (§5) and has not expired, stop. Cost: one
   file read.
2. If the queue has nothing pending, stop.
3. Open one connection to the broker, with the credential, over TLS
   (§6). Connect timeout 5 s; the whole run has a budget of 20 s.
4. Publish pending entries **oldest first**, in batches, each message
   with QoS 1 and the retain flag (RFC-0051 §5), to
   `oaap-node/<node-id>/metrics/<series>`.
5. After the broker's acknowledgement (`PUBACK`) of **every message of
   an entry**, call `queue_ack(entry number)`. An entry with three
   messages is acknowledged only when all three were.
6. Disconnect. Record the outcome (§7).

One connection per run, no daemon: nothing to supervise, nothing to
restart, nothing that survives a reboot in a bad state. The cost is a
TLS handshake a minute. If that proves too much, the sender may wait
and send every 5 minutes instead; that changes a constant, not the
design.

**Order and the retained message.** A backlog is sent oldest first, so
the last message of a series on the broker is the newest. A late
subscriber reads the current value from the retained message and the
history from nothing — history is the node's own store, not the
broker's.

**Catch-up.** After an outage the queue may hold up to its bound (7
days, about 30,000 messages). A run publishes as many as its 20 s
budget allows and stops cleanly between entries; the next run
continues. Catching up a week takes about an hour. No run is allowed to
publish *faster* than the broker can acknowledge: one batch in flight,
acknowledged before the next.

## 3. Delivery guarantees (and what is not promised)

- **At least once.** If the node dies after the broker's `PUBACK` and
  before `queue_ack`, the entry is sent again at the next run. A
  receiver that must not count a sample twice de-duplicates on
  `(node, m, t)`: `t` is a minute, so the triple identifies a sample.
  The message does not need a sequence number for that, and the format
  of RFC-0051 §3 stays as it is.
- **In order within a run, not across a gap.** Older data lost to the
  queue's bounds is gone; the loss is in `lost`, shown by
  `oaap metrics queue`, and the receiver sees a gap in `t`.
- **Not promised:** that the broker stores anything (that is the
  broker's retention), that a retained message is the newest after a
  resend (a resend can briefly put an older value back on top until the
  next entry arrives — one minute at most).

## 4. The node's identity on the wire

`<node-id>` is a **name the operator gives**, defaulting to the host
name, normalised to `[a-z0-9][a-z0-9-]{0,38}[a-z0-9]` (the rule
destinations and instances already use). It is stored with the
sender's configuration (§5), not derived from anything that can change
under it.

- It is a name, not a UUID, because the people reading these topics
  read them in a broker tool: `oaap-node/oaapx02/metrics/cpu`.
- **Uniqueness is the broker's job, not the node's.** Two nodes with
  the same name would write on the same topics. The receiving side
  prevents it by binding a credential to **one** node-id (§6.3): the
  second node's publish is refused, and the sender reports it as an
  error, not as a retry.

## 5. Configuration, credential, state

Three things, kept apart because they have different owners and
different secrecy:

| What | Where | Mounted into a container? |
|------|-------|----------------------------|
| Target and node-id: `mqtts://host:port`, user, node-id, optional CA file | `DATA_DIR/data/metrics/sender.json` | no |
| The secret (password) | `DATA_DIR/data/metrics/sender.secret`, mode 0600, root only | **never** |
| Run state: last success, last error, backoff | `DATA_DIR/data/metrics/sender-state.json` | read-only into the portal (§7) |

Commands (root, like every command that changes the node):

```text
oaap metrics sender set --url mqtts://host:8883 --user NAME [--node ID] [--ca FILE]
                        (the secret is read from standard input, not from the line)
oaap metrics sender show      target, node-id, whether a secret is set, the state
oaap metrics sender test      connect, publish nothing, say why or why not
oaap metrics sender remove    deletes configuration, secret and state; the queue stays
```

- **The secret is never printed**, not by `show`, not by an error, not
  in the portal, not in any log. `show` says "secret: set".
- **No sender configured is a normal state.** The queue keeps filling to
  its bounds, as today. `oaap metrics queue` says "no sender
  configured".
- **The secret file is excluded from `oaap backup` by default.** It is
  node-specific and cheap to enter again; a backup that carries a
  node's login to the operator's broker is a second place that must be
  guarded.
- **Backoff.** After a failed run the next attempt waits 1, 2, 4, …
  minutes, up to 15. Any success resets it. While it runs, the minutely
  job pays one file read. An **authentication or authorization refusal**
  does not back off in steps: it waits the full 15 minutes at once —
  hammering a broker with a wrong password is what gets a node banned.
- **The unit never fails because of the sender.** Like the sampler
  (RFC-0051), it catches everything, writes one line to standard error
  and exits 0.

## 6. The wire, and the receiving side

### 6.1 Protocol

MQTT **3.1.1**, written in the reference **without a library**: the
sender needs `CONNECT` (with user and password), `PUBLISH` at QoS 1,
`PUBACK`, `DISCONNECT`, nothing else — a few hundred lines on the
standard library's `socket` and `ssl`, tested against an in-process fake
broker. Reason: fact 3. A library would be one more thing every node
must carry; a protocol this small does not earn it. A node that gets a
library later can switch without changing a byte on the wire.

### 6.2 TLS

**Required.** The default is `mqtts://` with the system's trusted
certificate authorities and host-name verification; `--ca FILE` names a
private CA (the LAN broker case). A plain `mqtt://` target is accepted
only with `--allow-plain` and only for a target address in a private
range, and `show` says so in a line of its own. A certificate the
sender cannot verify **stops the run**; it never sends "just this once".

### 6.3 The receiving broker

The sender does not care what is behind the address, but the topic
branch of RFC-0051 §5 only works if the broker enforces three things:

1. **A credential per node**, and the credential may publish **only**
   under `oaap-node/<its own node-id>/#`. No subscribe right.
2. **No tenant principal can match the branch.** True on an OAAP broker
   already (`oaap.events.broker` §2.4 scopes tenant clients to
   `oaap/<tenant-id>/#`), and it stays true by construction.
3. **Retained messages are kept** (a default broker does).

For a **plain Mosquitto** with a password file and an ACL file, that is
two lines per node. For an **OAAP broker** as the receiver, the
authorization hook (`/mqtt-auth/…` in identity) needs a second kind of
principal, a **node key** that grants exactly one thing, as the fleet key
(RFC-0021) grants reading the status. That is a change to
`oaap.events.broker`, **not part of this RFC's first stage** (§9).

### 6.4 Security requirements for the receiving broker (Jörg, 2026-10-02)

The receiving Mosquitto holds the operator's view of every node. These
are **requirements**, not options, whatever way it is run (a plain
installation, an OAAP app, or an OAAP service):

1. **No anonymous access.** `allow_anonymous false`. A connection
   without a credential is refused at `CONNECT`, before any topic is
   looked at.
2. **Only named accounts, of two kinds.**
   - a **machine account per node**, bound to **one** node-id. It may
     **publish** under `oaap-node/<its node-id>/#` and nothing else. It
     may **not subscribe** to anything — a stolen node credential must
     not read other nodes — and may not publish under another node's
     name (§4);
   - a **human (or reader) account per person or tool**, bound to a set
     of node-ids or to all. It may **subscribe** to
     `oaap-node/<id>/#`, and may **not publish** anywhere.
   No account can do both. There is no shared account.
3. **Topic permissions are enforced by the broker**, in its ACL, not by
   the good behaviour of the client. With Mosquitto that is an ACL file
   with one `user` block per account, so that a node block reads
   `topic write oaap-node/<node-id>/#`; the file is *generated* from the
   account list, never hand-edited on the host, so the list is the one
   source.
4. **TLS only.** The plain port is not published; the TLS listener
   presents the broker's own certificate chain, and a client certificate
   is optional (a later hardening, not required).
5. **Credentials are individually revocable** without touching the
   others: removing an account removes its line and reloads the broker.
6. **Fail closed.** A broker that cannot read its password or ACL file
   does not start; it never falls back to "open".
7. **Passwords are stored hashed** in the password file (Mosquitto's
   `mosquitto_passwd` format), never in the clear, and the file is not
   mounted into any container but the broker's.
8. **The topic branch stays outside every tenant tree.** On a broker
   that also serves tenants (`oaap.events.broker`), no tenant rule may
   match `oaap-node/#` (§6.3 point 2).

**Conformance tests (described).** Against a real broker with these
settings: an anonymous connection is refused; a wrong password is
refused; a node account publishing under another node's name is
refused (and the sender classes it as an authorization refusal, §5); a
node account that subscribes receives nothing and is refused; a reader
account subscribes and receives retained values, and a publish by it is
refused; a removed account is refused on the next connect; a broker
started with a missing ACL file does not start; the plain port does not
answer from outside.

**How it is run — a shape this RFC leaves to stage 4.** Two shapes,
both able to meet the list above:
- **an OAAP app** (Mosquitto in a container with the generated
  password and ACL files, its TLS listener on the gateway's certificate
  or its own). Simple, self-contained, reuses the app machinery; the
  account list is the app's own;
- **the existing `broker` platform service**
  (`oaap.events.broker`, live authentication against identity, no local
  files), with a **node key** and a **reader key** as new principal kinds
  of the keys of RFC-0027. Its design (§2.4: no local password file, no
  local ACL file) already meets most of the list, and accounts would be
  revoked in the portal like any key. More to build.

Recommended: **the app first** — a Mosquitto app with the generated
files, built as stage 4 below — and the node/reader key principals as
the later step, because only that step lets one set of accounts serve
people and tenants alike.

## 7. Showing it

- `oaap metrics queue` gains the sender's lines: target (no secret),
  last success ("vor 3 Min."), last error as text, the running backoff,
  and the number waiting.
- The **health page** gets one line under the charts, for the same
  roles as the charts: "Senden an *host*: ok, zuletzt vor 1 Min.
  · 0 wartend", or "nicht erreichbar seit 14:03 · 212 wartend · 0
  verloren". It reads `sender-state.json` and the queue's counters
  through the directory the portal already mounts read-only. No button
  yet: configuring is the operator's command, not a web form.
- A queue that has **lost** samples says so on that line, in words, not
  just a number.

## 8. Decisions (Jörg, 2026-10-02: all recommendations taken)

**Decided: 1–7 as recommended.** The questions stay as asked:

1. **Where does the sender run?** Recommended: a **step of the minutely
   host job**, no process of its own (§2). Alternatives: a container with
   a library (more to ship, a second thing to supervise), or a bridge
   from a local Mosquitto (not every node has a broker).
2. **No library, a minimal MQTT client of our own?** Recommended: yes
   (§6.1) — three packet types, tested against a fake broker.
3. **The node-id is a name the operator chooses**, default host name
   (§4)? Recommended: yes. The alternative, a generated UUID, is safer
   against name clashes and unreadable in a broker tool.
4. **TLS mandatory**, plain only with `--allow-plain` on private
   addresses (§6.2)? Recommended: yes.
5. **The secret file excluded from the backup** (§5)? Recommended: yes.
6. **The first receiver.** What is it? A plain Mosquitto you run (the
   RFC works with it today), or an OAAP node's own broker (needs the
   node-key principal first, §6.3)? Recommended: **start against a plain
   Mosquitto**, and add the node key to `oaap.events.broker` as its own
   step when you want an OAAP node as the receiver. **Decided: a
   Mosquitto, which Jörg wants to run as an OAAP app or service — under
   the security requirements of §6.4.**
7. **Attempt every minute or every five?** Recommended: every minute
   with the backoff; change it only if the handshake shows in the
   measurements.

## 9. Stages

1. **The client and the run, against a fake broker** (§2, §6.1–6.2, §5
   state and backoff): `metrics.py` or a sibling file for the packets,
   `oaap metrics sender set|show|test|remove`, the step in the unit.
   Tests: acknowledgement before deletion, a crash between `PUBACK` and
   `queue_ack` resends, an unreachable broker backs off and loses
   nothing, a refused login waits the long time, a certificate error
   sends nothing, the secret never appears in any output.
2. **Showing it** (§7): the lines in `oaap metrics queue` and on the
   health page.
3. **A real broker**: measured against a Mosquitto with TLS on our own
   network, including an outage of the broker and of the network with a
   real backlog caught up, and a real reboot of the node in the middle
   of a run.
4. **The receiver as an OAAP app** (§6.4): Mosquitto with generated
   password and ACL files, two kinds of account (node, reader),
   commands to add and revoke them, TLS only, and the conformance tests
   of §6.4 measured against it.
5. *Later, own step:* node and reader keys as principals of
   `oaap.events.broker` (§6.3, §6.4), so that one set of accounts can
   serve an OAAP node as receiver.

## 10. Out of scope

Alerts and thresholds on the received data; dashboards on the receiving
side; per-instance or per-tenant series (RFC-0051 §9); forwarding
anything but the three node series; MQTT 5; a bridge between brokers;
retention and storage on the broker.

---

## Deutsche Zusammenfassung

**Worum es geht:** Die Warteschlange aus RFC-0051 Stufe 3 füllt sich,
aber nichts liest sie. Dieser RFC beschreibt den **Sender**, der sie an
einen MQTT-Knoten weiterreicht.

**Was vorgeschlagen wird:**
- Der Sender ist ein **Schritt im minütlichen Host-Lauf**, direkt hinter
  dem Messer, ohne eigenen Prozess. Er schlägt **nie** den Lauf fehl, auch
  nicht, wenn die Gegenstelle tot ist: ein Fehler wird gezählt und
  angezeigt, mehr nicht.
- Er schickt die Zeilen **ältester zuerst** mit QoS 1 und „retained" an
  `oaap-node/<knoten>/metrics/<reihe>` und **löscht eine Zeile erst, wenn
  der Broker sie bestätigt hat** (das vorhandene `queue_ack`). Das heißt
  **mindestens einmal**: nach einem Absturz zwischen Bestätigung und
  Löschen kommt sie ein zweites Mal; der Empfänger erkennt sie an
  `(Knoten, Reihe, Minute)`.
- Ohne Bibliothek: ein **eigener, kleiner MQTT-3.1.1-Client** (Connect,
  Publish, Bestätigung, Trennen), getestet gegen einen Schein-Broker.
  Grund: der Wirt hat kein MQTT-Paket und soll keins brauchen.
- **TLS ist Pflicht**; Klartext nur mit ausdrücklicher Erlaubnis und nur
  in privaten Adressen. Ein nicht prüfbares Zertifikat stoppt den Lauf.
- Der **Knotenname** auf dem Draht ist ein vom Betreiber gewählter Name
  (Vorgabe: Hostname). Eindeutig hält ihn der Broker, indem ein Zugang
  nur unter **seinem** Namen schreiben darf.
- **Das Passwort** liegt in einer eigenen Datei (nur Root, in keinem
  Container, nicht im Backup) und wird **nie** ausgegeben. Konfiguriert
  wird mit `oaap metrics sender set|show|test|remove`.
- Bei Fehlern wartet der Sender 1, 2, 4 … bis 15 Minuten; bei **falschem
  Passwort** gleich 15 Minuten, damit der Knoten nicht gesperrt wird.
- **Sichtbar:** eine Zeile auf der Gesundheitsseite („ok, zuletzt vor
  1 Min." oder „nicht erreichbar seit … · 212 wartend · 0 verloren") und
  mehr Zeilen in `oaap metrics queue`.
- Es ist **keine** Destination (die gehört einem Mandanten und ist für
  Instanzen gedacht), sondern eine Einstellung des Knotens.

**Zu entscheiden (§8):** wo der Sender läuft, ob ein eigener Client,
Knotenname als Name, TLS-Pflicht, Passwort nicht im Backup, **der erste
Empfänger** (Empfehlung: ein einfacher Mosquitto, den du betreibst; der
Knotenschlüssel für den OAAP-Broker ist ein späterer Schritt) und
minütlich oder alle fünf Minuten.

**Entschieden (Jörg, 02.10.2026):** alle Empfehlungen übernommen. Als
Empfänger ein Mosquitto, der auch als OAAP-App laufen soll — mit
Sicherheitsvorgaben (neu, §6.4): **kein anonymer Zugang**; nur benannte
Konten, und zwar ein **Maschinenkonto je Knoten** (darf nur unter
`oaap-node/<eigener Name>/#` schreiben, nichts lesen) und ein
**Lesekonto je Mensch oder Werkzeug** (darf lesen, nie schreiben);
Themenrechte erzwingt der Broker in seiner ACL, erzeugt aus der
Kontenliste; nur TLS; Konten einzeln sperrbar; ohne lesbare Passwort-
oder ACL-Datei startet der Broker nicht; Passwörter nur als Hash. Ob der
Empfänger eine eigene OAAP-App oder der vorhandene `broker`-Dienst mit
neuen Schlüsselarten ist, bleibt für Stufe 4 offen; Empfehlung: erst die
App.

**Stand:** angenommen, nichts gebaut.
