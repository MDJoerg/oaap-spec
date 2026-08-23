# oaap.fleet.status — Read-Only Fleet Status Document

- **ID:** `oaap.fleet.status`
- **Version:** 0.1
- **Maturity:** draft (implemented by the reference 0.1.41)
- **Based on:** RFC-0021; RFC-0008 (`server_admin`), RFC-0010
  (throttling precedent), RFC-0019 (token hygiene precedent)

## Purpose

One machine-readable, **strictly read-only** status document per node,
so an operator's inner node can watch a fleet (including headless
internet nodes) without interactive logins and without any inbound
control channel. The watching side polls; the watched node never
connects anywhere (RFC-0021: the internal server connects outward).

## 1. The route

`GET /fleet/status` on the platform's gateway, on every published name
of the node. No session, no cookie; the gateway strips client-sent
identity headers exactly as on the deploy hook. Authorization is a
bearer **fleet key** (§2). Any failure — unknown key, missing header,
malformed value — receives the same 403 without detail (no chatter).
Repeated failures are braked per client address (5 failures in 5
minutes → 1 attempt/minute), in a throttle namespace of their own.

## 2. The fleet key

- Issued and revoked by `server_admin` **at the machine**:
  `oaap fleet key issue <label>` / `list` / `revoke <label>`. The
  label names the consumer (e.g. `fleetview@oaap-demo`) — that is what
  makes revocation meaningful.
- The key value is shown **exactly once** at issue time; only its
  SHA-256 digest is stored (deploy-token precedent, RFC-0019 hygiene).
  `list` shows labels and creation times, never key material.
- A fleet key authorizes **exactly one thing**: `GET /fleet/status` on
  this node. It is not a session, carries no roles, opens no other
  route, and cannot change anything.
- Issue and revoke are audited (`fleet-log.jsonl`); polls are not.
- Labels are unique; re-issuing requires an explicit revoke first.

## 3. The document

```json
{
  "schema": "oaap.fleet.status/0.1",
  "node": "oaap.joomp.de",
  "platform_version": "0.1.41",
  "profiles": [],
  "time": "2026-08-23T10:15:00Z",
  "core": [
    {"name": "identity", "state": "ok"},
    {"name": "gateway", "state": "ok"},
    {"name": "portal", "state": "ok"},
    {"name": "deploy-worker", "state": "ok"}
  ],
  "instances": [
    {"instance": "bdt-hub", "app": "bdt-hub", "version": "0.1.0",
     "channel": "production", "state": "ok",
     "origin": "promoted", "address": "hub.bdt.joomp.de"}
  ],
  "attention": [
    {"kind": "dns_drift", "detail": "name.example: points elsewhere"},
    {"kind": "confirmation_pending", "instance": "bdt-hub-test"}
  ]
}
```

Rules:

1. **Facts only, never secrets.** The document must not contain
   tokens, digests, key material, configuration values, or source
   URLs (a source URL can embed a credential). Implementations MUST
   build instance rows as a whitelist of named fields, never by
   copying registry entries. Of an instance's source only its **type**
   (`git`, `artifact`, `promoted`) may appear.
2. **`schema` is versioned.** Consumers talk to nodes of mixed
   platform versions during a rollout — the normal state of a fleet.
   Additive changes bump the minor; removals or renames need a new
   major and an RFC.
3. **States are one vocabulary:** `ok | warn | error | unknown`.
4. **`attention` is the machine-readable "needs a human".** Defined
   kinds today: `core_service_down`, `dns_drift`, `dns_unresolved`,
   `confirmation_pending`, `instance_unhealthy`. The list is open —
   consumers MUST tolerate unknown kinds. Everything in `attention`
   is derived from facts already elsewhere in the document or on the
   node; it adds urgency, not information channels.
5. **`node`** is the node's registered external hostname, or the host
   the poller addressed when none is registered.

## 4. Consumers

The first consumer is the fleet overview app (RFC-0021 §3): node list
and one fleet key per node are operator configuration (keys as secret
config values, never rendered back). A consumer MUST treat an
unreachable node as a state ("stale since \<last poll\>"), not as an
error page, and SHOULD poll at minute granularity — outage alerting
stays with dedicated probes (e.g. Uptime Kuma), and seconds-level
freshness belongs to the future telemetry capability.

## 5. Out of scope (deliberate, RFC-0021)

No write path, no commands, no self-healing, no push telemetry, no
metrics history, no auto-discovery. Partner-scoped views of fleet data
are stage 2 (RFC-0021 outlook) and live on the management node, never
on the watched node.

## Zusammenfassung auf Deutsch

Jeder Knoten beantwortet `GET /fleet/status` mit einem versionierten
JSON-Dokument: Plattformversion, Profile, Kerndienst-Ampeln,
Instanzliste (App, Version, Kanal, Zustand, Herkunftstyp, Adresse) und
einer `attention`-Liste („braucht einen Menschen": Kerndienst
ausgefallen, DNS-Drift, Name löst nicht auf, wartende Bestätigung,
Instanz ungesund — offen für weitere Arten, Konsumenten müssen
Unbekanntes tolerieren). Autorisiert wird mit einem **Flotten-
Schlüssel**: `sudo oaap fleet key issue <label>` zeigt ihn genau
einmal, gespeichert wird nur der SHA-256-Digest; `list` nennt nie
Schlüsselmaterial, `revoke` wirkt sofort; Ausstellung und Entzug
werden protokolliert, Abrufe nicht. Der Schlüssel kann **ausschließlich
diese eine Auskunft lesen** — keine Sitzung, keine Rollen, kein anderer
Weg. Eiserne Regel des Dokuments: **Fakten, nie Geheimnisse** — keine
Tokens, keine Config-Werte, keine Quell-URLs (dort können Zugangsdaten
stecken); Instanzzeilen entstehen als Whitelist, nie als Kopie des
Registry-Eintrags. Fehlversuche werden gebremst und antworten ohne
Auskunft. Erster Konsument ist die FleetView-App; Alarmierung bleibt
bei Uptime Kuma, Sekundenfrische und alles Schreibende sind bewusst
außen vor.
