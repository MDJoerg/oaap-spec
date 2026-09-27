# oaap.net.remote-access — A Person Inside One Instance Network, For a While

- **ID:** `oaap.net.remote-access`
- **Version:** 0.1
- **Maturity:** draft (0.1 is RFC-0044 stage 1, as staged by D2's
  consequence: the access object, its lifecycle, the tenant audit
  trail and the portal card. It carries **no traffic yet** — opening
  an access records who, for whom, which instance and until when, and
  it expires by itself, but the port forward of RFC-0044 §4 and the
  WireGuard peer of §5 are not built. Both hang on this stage, per
  Jörg's decision to build them together rather than in sequence.)
- **Based on:** RFC-0044 (the object, D1–D10), RFC-0038 (the diagnosis
  window and its sweep — the pattern this capability copies exactly,
  D2 there), RFC-0022 / `oaap.core.tenant` (the tenant audit log, an
  access belongs to exactly one tenant), RFC-0011 (node profiles —
  reserved for stage 2's WireGuard listener, not used yet), RFC-0027
  (API keys — the credential stage 2's port forward will reuse)

## 1. Purpose

RFC-0016 gave every instance its own Docker network, joined only by
its own containers and the gateway. Right for the app, inconvenient
for the person who has to look inside — a wrapped stack's own
Postgres, an admin port, a broker. This capability introduces the
object that makes looking inside a deliberate, time-boxed, recorded
act instead of a trip to the machine: an **access**.

What 0.1 delivers is the object and its lifecycle — open, list, close,
expire, and one line per event in the tenant's audit log. It does not
yet let anyone reach anything: RFC-0044 §7 already says the point of
an access is "the door", and 0.1 has not built a door, only the record
that one has been asked for. That is deliberate staging, not an
oversight — see Maturity above.

## 2. The object

```json
{ "id": "a4c1e7",
  "instance": "<instance name/key>",
  "tenant": "<uuid>",
  "shape": "forward",                          // forward | wireguard
  "target": {"service": "db", "port": 5432},    // forward only, else {}
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
- `holder` is free text in 0.1, defaulting to the opener. It is **not
  yet checked** against the tenant's user list — a limitation stated
  here on purpose, because 0.1 grants no traffic; real enforcement of
  "never someone outside [the tenant]" (RFC-0044 §1) arrives with
  stage 2's port forward, which checks the holder's own API key on
  every connection (RFC-0044 §4).

## 3. Lifecycle

- **Open.** Checks, on the host, not only in a form: the instance
  exists; `shape` is one of `forward`/`wireguard`; `hours` is one of
  `1`/`8`/`24` (RFC-0044 D3, default `8`, no extension — opening again
  is a new act with a new audit entry); a `forward` access names a
  service and a port. Writes the record and one tenant-audit line
  `access.opened` (who, for whom, instance, shape, target if any,
  hours).
- **List.** Open, unexpired accesses, optionally filtered by instance
  or tenant.
- **Close.** Removes the record early. Writes `access.closed`.
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

## 4. Roles (D1)

Opening or closing an access requires `server_admin`, or the
`tenant_admin` of the **instance's own tenant** — never another
tenant's `tenant_admin`, refused by the same cross-tenant check every
other portal action already runs. An access a `server_admin` opens is
recorded in the **tenant's** log, not a separate operator log (RFC-0022
§6: "access by the operator is itself an event").

## 5. Interface (CLI)

```
oaap app access open <instance> [--shape forward|wireguard]
    [--holder <name>] [--hours 1|8|24] [--service <name> --port <n>]
oaap app access list [<instance>]
oaap app access close <access-id>
oaap app access sweep
```

`oaap app access open` prints the record and says plainly that no
traffic follows in 0.1. The portal card offers the same four actions
on the instance page — open, the table of currently open accesses,
close, and (automatically, unseen) the sweep.

## 6. Security requirements

- **Default: no access.** No instance has an open access unless a
  person with the right role opened it.
- **A named holder**, even though 0.1 does not yet check it against
  the tenant's users (§2).
- **Always a TTL**, one of three fixed durations, never extended.
- **One tenant.** An access belongs to the instance's tenant; the
  cross-tenant check that guards every other portal action guards this
  one too.
- **Metadata always, payload never** (D7) — nothing this stage records
  is content; there is no content yet to record.
- **The spool is data, not trust.** Every check above runs again on
  the host when the portal queues an open or a close, exactly as
  RFC-0038's diagnosis window does.

## 7. What 0.1 explicitly does not do

- **No traffic.** Neither shape moves a single byte between a laptop
  and an instance network yet. §4 and §5 of RFC-0044 (the port forward
  and the WireGuard peer) are not built.
- **No firewall fence, no WireGuard listener, no node profile check.**
  RFC-0044 §2.2's host firewall rule and D4's `remote-access` node
  profile belong to stage 2, and are measured on a real node before
  either is offered anywhere (RFC-0044 D2's consequence).
- **No device access** (RFC-0044 D9) — a different object, a different
  fence, out of scope here.

## 8. Conformance tests

1. Opening an access on an unknown instance is refused.
2. Opening an access with a duration other than 1/8/24 hours is
   refused, with all three checked from a form value, not trusted.
3. Opening a `forward` access without a service and a port is refused.
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

## 9. Dependencies

RFC-0044, RFC-0038 (window/sweep pattern), RFC-0022 (tenant, audit
log), RFC-0027 (referenced for stage 2), RFC-0016 (instance networks —
the thing an access will eventually reach).

## Deutsche Zusammenfassung

**Worum es in dieser Stufe geht.** RFC-0044 will einen zeitlich
begrenzten Zugang eines Menschen in genau ein Instanznetz — als
eigenes Objekt, „Zugang" genannt. Diese erste Stufe (0.1) baut das
Objekt selbst: öffnen, auflisten, schließen, automatisch ablaufen, und
je Ereignis eine Zeile im Audit-Log des Mandanten. **Sie öffnet noch
keine wirkliche Verbindung** — wer heute einen Zugang öffnet, bekommt
einen Datensatz mit Ablaufzeit, aber noch keinen Weg zur Datenbank.
Das ist Absicht: Jörg hat entschieden, dass Portweiterleitung (b) und
WireGuard (a) zusammen gebaut werden, nicht nacheinander — aber
gebaut wird zuerst das Gerüst (Objekt, Portal-Karte, Protokoll,
Aufräumen), und die Firewall-Regel wird an einem echten Knoten
gemessen, bevor irgendwo eine WireGuard-Datei ausgegeben wird.

**Vorbild ist das Diagnose-Fenster** (RFC-0038): dieselbe Uhr (der
Minutentimer läuft schon), dieselbe Regel „nie verlängern, neu öffnen
ist ein neuer Vorgang", dieselbe Prüfung noch einmal auf dem Knoten,
weil die Warteschlange Daten ist, kein Vertrauen.

**Wer darf öffnen?** `server_admin`, und der `tenant_admin` genau des
Mandanten, dem die Instanz gehört (D1) — wie überall sonst im Portal.

**Noch offen (Stufe 2/3):** die eigentliche Portweiterleitung durch
das Gateway, der WireGuard-Zugang ins Netz, die Firewall-Regel, die
das durchsetzt, und der Knotenprofil-Schalter `remote-access`.
