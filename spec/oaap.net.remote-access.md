# oaap.net.remote-access — A Person Inside One Instance Network, For a While

- **ID:** `oaap.net.remote-access`
- **Version:** 0.2
- **Maturity:** draft (0.1 was RFC-0044 stage 1, staged by D2's
  consequence: the access object, its lifecycle, the tenant audit
  trail and the portal card — no traffic yet. **0.2 adds stage 2's
  port forward (§4):** a `forward` access now carries real bytes,
  through the connect service, into the one container:port the
  access names. A `wireguard` access still opens only the record —
  §5's WireGuard peer and its host firewall fence are not built, and
  D2's consequence still requires measuring that fence on a real node
  before either is offered anywhere.)
- **Based on:** RFC-0044 (the object, D1–D10, §4 the port forward),
  RFC-0038 (the diagnosis window and its sweep — the pattern this
  capability's lifecycle copies exactly, D2 there), RFC-0022 /
  `oaap.core.tenant` (the tenant audit log, an access belongs to
  exactly one tenant), RFC-0027 (API keys — the holder's own key is
  the forward's only credential), RFC-0016 (instance networks — what
  a forward reaches, and how it is named), RFC-0033 §3.5 (the laptop
  client `oaap-expose.py`, which grew the `forward` verb this version
  needed)

## 1. Purpose

RFC-0016 gave every instance its own Docker network, joined only by
its own containers and the gateway. Right for the app, inconvenient
for the person who has to look inside — a wrapped stack's own
Postgres, an admin port, a broker. This capability introduces the
object that makes looking inside a deliberate, time-boxed, recorded
act instead of a trip to the machine: an **access**.

0.1 delivered the object and its lifecycle. 0.2 delivers the first of
its two shapes carrying real traffic: **a port forward** — one
container, one port, one holder, one WebSocket per TCP connection they
make. The second shape, a WireGuard peer into the whole instance
network, is still not built (§7).

## 2. The object

```json
{ "id": "a4c1e7",
  "instance": "<instance name/key>",
  "tenant": "<uuid>",
  "shape": "forward",                          // forward | wireguard
  "target": {"service": "db", "port": 5432,
            "container": "oaap-app-crm-db"},   // forward only, else {}
  "holder": "<name the opener gave, default: themselves>",
  "opened_by": "<who queued the open>",
  "opened": "<ISO instant, UTC>",
  "expires": "<ISO instant, UTC>",
  "hours": 8,
  "state": "open" }
```

- An access belongs to **exactly one instance** and therefore exactly
  one tenant (RFC-0022). `tenant` is resolved from the instance at
  open time, the same way every other tenant-scoped record on this
  node resolves it.
- **Not instance configuration.** An access is not stored on the
  instance's registry entry, is not part of any manifest, and is not
  carried by backup, restore or promotion (RFC-0044 §1) — it is an act,
  not configuration. It is kept in its own file
  (`apps/remote-access.json`), the same way `connect.json` and
  `twin-readers.json` hold acts rather than configuration.
- **`target.container` is resolved once, at open time**, from the
  instance's own service list (RFC-0016): a single-service instance
  resolves any name (there is nothing to disambiguate); a
  multi-service instance requires an exact match on the service name,
  refused otherwise. This is the ONE container:port a forward may ever
  reach — fixed when the access opens, never re-resolved from a
  connection's own request, and never influenced by anything the
  laptop client sends.
- `holder` is free text, defaulting to the opener. It is **not
  checked against the tenant's user list when the access opens** — but
  it IS the exact string every forward connection's identity check
  compares the caller's key to (§4): a holder that does not name a
  real, still-active user simply means nobody's key will ever match,
  which is refused the same way a wrong holder is.

## 3. Lifecycle

- **Open.** Checks, on the host, not only in a form: the instance
  exists; `shape` is one of `forward`/`wireguard`; `hours` is one of
  `1`/`8`/`24` (RFC-0044 D3, default `8`, no extension — opening again
  is a new act with a new audit entry); a `forward` access names a
  service that exists on the instance, and a port. For `forward`, the
  connect service is joined to the instance's network here too (§4) —
  refused, with nothing written, if that fails. Writes the record and
  one tenant-audit line `access.opened` (who, for whom, instance,
  shape, target if any, hours).
- **List.** Open, unexpired accesses, optionally filtered by instance
  or tenant.
- **Close.** Removes the record early. For `forward`, the connect
  service leaves the instance's network too, but only once no other
  open `forward` access on that same instance still needs it. Writes
  `access.closed`.
- **Expire.** The same removal, run by the sweep, once `expires` has
  passed. Writes `access.expired` instead of `access.closed` — same
  shape as RFC-0038's `diagnose.expired` vs `diagnose.closed`.
- **Sweep.** `oaap app access sweep` closes every access whose time is
  up. It runs every minute from the same timer RFC-0038's diagnosis
  sweep already uses (`oaap-instance-watch.service`/`.timer`) — one
  more `ExecStart` line, not a new timer. Idempotent, like its
  neighbor: running it with nothing to close changes nothing.
- **No extension.** RFC-0044 D3: never extended in place. A longer
  look is a new access, with its own audit line — the same reasoning
  RFC-0038 D2 gives for its window.

## 4. The port forward (RFC-0044 §4)

```
laptop                                    node
┌──────────────────────┐                ┌───────────────────────────────┐
│ psql -h localhost      oaap-expose.py  │ gateway  /connect/forward     │
│      -p 5433  ──────▶  forward         │  1. who? holder's own key     │
│                      ──WebSocket──────▶│  2. this access: alive,       │
│                        (one per        │     'forward', not expired?   │
│                         TCP conn)       │  3. dial the ONE container:  │
└──────────────────────┘                │     port the access names     │
                                          └───────────────────────────────┘
```

- **A single hop, never inter-node.** Unlike `oaap.net.connector`'s
  tunnel (which crosses to another node), a forward is entirely local
  to the node the access was opened on: the gateway passes
  `/connect/forward` to the connect service, exactly as it already
  passes `/connect/tunnel` (same route shape, own handler).
- **One WebSocket per TCP connection**, raw bytes both ways, no
  framing of its own. The laptop client listens on a local port; every
  connection there opens its own WebSocket, relayed 1:1. There is
  nothing to multiplex, so nothing is.
- **Checked on every connection, not once.** The client's
  `Authorization: Bearer <API key>` is verified against identity
  (RFC-0027), and the resulting principal must equal the access's
  `holder` exactly — a key that opens fine but belongs to someone else
  is refused (403) without saying whose access it actually is. An
  unknown, non-`forward`, or expired access id answers 404/410, never
  401 — the request named the wrong access, not a bad key.
- **The connect service reaches the target because appctl put it
  there.** It carries no Docker socket and joins no network on its
  own initiative — the network join happens exactly once, when an
  access of shape `forward` opens on that instance, and is undone
  once no such access remains open on it (§3). The dial itself names
  only `target.container:target.port` — nothing a connection can
  redirect.
- **No new node capability.** No listener, no port published, no
  firewall rule: the fence here is code (the fixed dial target), not
  configuration — RFC-0044 §4 says so explicitly, which is why this
  shape did not have to wait for a firewall fence measured on a real
  node the way §5's WireGuard peer does.
- **The laptop client:** `oaap-expose.py forward --access <id>
  --server <node> --local-port <n>` (RFC-0033 §3.5's client, same
  binary, opposite verb from `expose`). Reads the key from `OAAP_KEY`
  or a hidden prompt, never an argument — same rule as `expose`.

## 5. Roles (D1)

Opening or closing an access requires `server_admin`, or the
`tenant_admin` of the **instance's own tenant** — never another
tenant's `tenant_admin`, refused by the same cross-tenant check every
other portal action already runs. An access a `server_admin` opens is
recorded in the **tenant's** log, not a separate operator log (RFC-0022
§6: "access by the operator is itself an event"). This governs who may
**open and close the record**; §4's per-connection check is a separate
question answered by the holder's own key, not by this role.

## 6. Interface (CLI)

```
oaap app access open <instance> [--shape forward|wireguard]
    [--holder <name>] [--hours 1|8|24] [--service <name> --port <n>]
oaap app access list [<instance>]
oaap app access close <access-id>
oaap app access sweep
```

`oaap app access open` prints the record and, for `forward`, the exact
client command the holder runs next. The portal card offers the same
actions on the instance page's "Fernzugang" tab — open, the table of
currently open accesses (with the id, needed to run the client),
close, and (automatically, unseen) the sweep.

## 7. Security requirements

- **Default: no access.** No instance has an open access unless a
  person with the right role opened it.
- **A named holder, checked at connection time.** §2/§4: not checked
  against the tenant's users when the record is created, but every
  forward connection's identity check must resolve to that exact name.
- **Always a TTL**, one of three fixed durations, never extended.
- **One tenant.** An access belongs to the instance's tenant; the
  cross-tenant check that guards every other portal action guards this
  one too.
- **One fixed target, decided by the operator who opened it, never by
  the connection.** A forward's `target.container`/`target.port` are
  resolved once, at open time, from the instance's own declared
  services — nothing a laptop client sends can change or widen it.
- **Metadata always, payload never** (D7). The audit log records
  opening, closing, expiry and a `access.forward.connected` line per
  connection (who, instance, target) — never the bytes exchanged; the
  connect service does not parse the protocol running over a forward
  and makes no claim to.
- **The spool is data, not trust.** Every open/close check above runs
  again on the host when the portal queues one, exactly as RFC-0038's
  diagnosis window does; every §4 check runs again on the connect
  service for every single connection, not only the first.

## 8. What 0.2 explicitly does not do

- **No WireGuard.** §5's peer into the whole instance network, its
  `.conf`/QR issuance and its host firewall fence are not built. D2's
  consequence still applies: the firewall fence is measured on a real
  node before any of it is offered anywhere.
- **No node profile check.** D4's `remote-access` node profile gates
  the WireGuard listener only, which does not exist yet — a `forward`
  access needs no profile, exactly as RFC-0044 §4 says ("the port
  forward needs no profile: it rides the gateway").
- **No device access** (RFC-0044 D9) — a different object, a different
  fence, out of scope here.

## 9. Conformance tests

1. Opening an access on an unknown instance is refused.
2. Opening an access with a duration other than 1/8/24 hours is
   refused, with all three checked from a form value, not trusted.
3. Opening a `forward` access without a port is refused; naming a
   service the instance does not have is refused by name, not
   silently substituted.
4. An opened access appears in `oaap app access list` for its instance
   and disappears once closed.
5. Closing an unknown access id is refused.
6. `access sweep` closes an access whose `expires` has passed, and
   leaves an unexpired one alone.
7. Every open and close writes exactly one tenant-audit line, with the
   right actor and role; a denied attempt (wrong role) writes exactly
   one `access.opened`/`access.closed` line with `result: denied` and
   no record.
8. A `tenant_admin` may open and close an access on their own tenant's
   instance; the same request against another tenant's instance is
   refused before this capability's own role check runs (the shared
   cross-tenant guard).
9. The record written to `apps/remote-access.json` never appears in
   the instance's registry entry, a backup, or a promoted instance.
10. A `forward` connection with the holder's own key relays bytes
    exactly, both ways, over one WebSocket per TCP connection.
11. A `forward` connection with a key that verifies but is not the
    holder is refused (403), without revealing who the holder is.
12. A `forward` connection naming an unknown, non-`forward`, or
    expired access is refused (404/410), never mistaken for a bad key
    (401).
13. Two connections to the same `forward` access are independent —
    one ending does not affect the other.
14. Closing the last `forward` access of an instance makes the connect
    service leave that instance's network; closing one of several does
    not.

## 10. Dependencies

RFC-0044, RFC-0038 (window/sweep pattern), RFC-0022 (tenant, audit
log), RFC-0027 (the holder's own key, checked per connection), RFC-0016
(instance networks, container naming), RFC-0033 §3.5 (the laptop
client this version extended).

## Deutsche Zusammenfassung

**Worum es geht.** RFC-0044 will einen zeitlich begrenzten Zugang eines
Menschen in genau ein Instanznetz — als eigenes Objekt, „Zugang"
genannt. Stufe 1 (0.1) baute das Objekt selbst: öffnen, auflisten,
schließen, automatisch ablaufen, je Ereignis eine Zeile im Audit-Log.
**Stufe 2 (0.2, diese Fassung) lässt eine Portweiterleitung wirklich
Verkehr tragen:**

- Der/die Inhaber:in startet `oaap-expose.py forward --access <Id>
  --server <Knoten> --local-port <Port>` auf dem eigenen Rechner, mit
  dem **eigenen** API-Schlüssel (nicht dem der Person, die den Zugang
  geöffnet hat).
- Jede lokale Verbindung wird zu einem eigenen WebSocket zum Knoten,
  das roh, ohne eigene Rahmung, Bytes durchreicht — ein einziger
  Sprung, nie zwischen zwei Knoten.
- Der `connect`-Dienst prüft bei **jeder** Verbindung erneut: der
  Schlüssel gehört zur/zum Inhaber:in, der Zugang lebt noch, die Form
  ist `forward`. Er wählt das Ziel selbst — Dienst und Port stehen im
  Zugang, fest, seit dem Öffnen; die Anfrage liefert nur eine Id, nie
  eine Adresse.
- Der `connect`-Dienst tritt dem Instanznetz nur bei, solange dort ein
  offener `forward`-Zugang ist — appctl übernimmt das beim Öffnen und
  Schließen, kein Docker-Zugriff, keine Firewall-Regel nötig (§4 sagt
  ausdrücklich: „das Gateway wählt selbst das Ziel", keine
  Netzwerk-Öffnung wie bei WireGuard).

**Weiterhin nicht gebaut:** WireGuard (Form `wireguard`) — die Firewall-
Regel dafür wird zuerst an einem echten Knoten gemessen, bevor
irgendwo eine WireGuard-Datei ausgegeben wird (D2). Auch kein
Knotenprofil `remote-access` — das gehört zur WireGuard-Stufe.

**Wer darf öffnen/schließen?** `server_admin`, und der `tenant_admin`
genau des Mandanten, dem die Instanz gehört (D1). Eine andere Frage
ist, wer eine geöffnete Portweiterleitung tatsächlich BENUTZEN darf —
das entscheidet allein der Inhaber-Name im Zugang, geprüft bei jeder
Verbindung.
