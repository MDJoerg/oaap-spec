# oaap.fleet.status — Read-Only Fleet Status Document

- **ID:** `oaap.fleet.status`
- **Version:** 0.3 (adds `auto_address` and `auto_state` to instance
  rows — additive, 0.1 and 0.2 consumers keep working; implemented by
  the reference 0.1.46)
- **Maturity:** draft
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
  "schema": "oaap.fleet.status/0.3",
  "node": "oaap.joomp.de",
  "platform_version": "0.1.46",
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
     "origin": "promoted", "address": "hub.bdt.joomp.de",
     "auto_address": "bdt-hub.oaap.joomp.de", "auto_state": "ok"}
  ],
  "names": [
    {"name": "oaap.joomp.de", "kind": "node", "state": "ok",
     "resolved": "203.0.113.7"},
    {"name": "hub.bdt.joomp.de", "kind": "instance",
     "instance": "bdt-hub", "state": "ok", "resolved": "203.0.113.7"}
  ],
  "public_ip": "203.0.113.7",
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
6. **`names`** (0.2) is the node's own DNS view of the names it has
   in DNS: the registered node hostname, each instance's **registered**
   canonical name and every alias (RFC-0018 vocabulary — the canonical
   name is the one an operator set, not the automatic one from rule 7).
   `kind` is `node | instance | alias` (`instance` names the owning
   instance); `state` is the node's own verdict from its half-hourly
   DNS watchdog — `ok` (points here), `warn` (points elsewhere),
   `error` (does not resolve), `unknown` (cannot compare: behind an
   edge, or IPv6-only). `resolved` lists the addresses the name
   resolved to, and is omitted when there are none. **`public_ip`**
   (0.2) is the address the node last saw for itself from the outside;
   omitted when unknown. Both fields are facts the health page already
   shows — port/reach verdicts (RFC-0015) stay out until a consumer
   needs them.

7. **`auto_address` and `auto_state`** (0.3) carry the instance's
   **automatic** name, `<instance>.<node host>`, and the node's verdict
   on it. They exist because that name is deliberately **absent from
   rule 6**: automatic names are served by a wildcard record, and a
   wildcard answers for every name under it — including names that
   were never installed. A DNS verdict on such a name could therefore
   never say anything the node hostname's own verdict does not already
   say. Publishing one DNS record per instance instead is possible but
   is NOT the standard: it would put the node's whole instance
   inventory into DNS, and the record would then have to be managed and
   watched per instance. So the automatic name gets the question that
   *can* fail instead — **is the instance reachable under this name on
   this node?**

   `auto_state` uses the vocabulary of rule 3: `ok` (a route for this
   name exists on the gateway and the instance answers behind it),
   `warn` (the route exists, the instance answers but is not healthy),
   `error` (no route exists for this name — the name would land on the
   catch-all, not on the app), `unknown` (the node cannot say). Both
   fields are **omitted** when the node publishes no external hostname
   at all: then there is no automatic name to speak about.

   What this verdict deliberately does NOT claim: that the name
   resolves for a given client, that TLS is in place for it, or that
   anything outside the node can reach it. Those are reach questions
   (RFC-0015) and stay where they are. `auto_state` is an **inside**
   statement, and the spec says so plainly so that no consumer renders
   it as "reachable from the internet".

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
Unbekanntes tolerieren). **Seit 0.2** zusätzlich `names` — die
DNS-Sicht des Knotens auf die Namen, die er in DNS stehen hat
(Knotenname, **registrierte** Instanz-Hauptnamen, Aliasse; Urteil des
halbstündlichen DNS-Wächters: zeigt hierher / zeigt woanders hin /
löst nicht auf / nicht vergleichbar) — und `public_ip` (die zuletzt
von außen gesehene eigene Adresse).

**Seit 0.3** trägt jede Instanzzeile ihren **automatischen** Namen
`<instanz>.<knoten>` als `auto_address` mit dem Urteil `auto_state`.
Der Grund: Automatische Namen stehen bewusst **nicht** in `names`. Sie
werden von einem Wildcard-Eintrag beantwortet, und ein Wildcard
antwortet für *jeden* Namen darunter — auch für nie installierte. Ein
DNS-Urteil darüber könnte deshalb nie etwas anderes sagen als das
Urteil über den Knotennamen selbst. Je Instanz einen eigenen
DNS-Eintrag anzulegen bleibt möglich, ist aber **nicht der Standard**:
Das legte das gesamte Instanz-Inventar des Knotens in DNS offen und
müsste je Instanz gepflegt und überwacht werden. Der automatische Name
bekommt darum die Frage, die tatsächlich schiefgehen kann: **Ist die
Instanz unter diesem Namen auf diesem Knoten erreichbar?** — `ok`
(Route vorhanden, Instanz antwortet), `warn` (Route vorhanden, Instanz
antwortet ungesund), `error` (keine Route: der Name landete auf dem
Auffangeintrag statt bei der App), `unknown`. Fehlt dem Knoten ein
externer Name, entfallen beide Felder. Ausdrücklich **keine** Aussage
über TLS, über Auflösbarkeit bei einem bestimmten Client oder über
Erreichbarkeit von außen — das bleibt Sache der Reach-Prüfungen
(RFC-0015). Alles additiv, 0.1- und 0.2-Konsumenten laufen weiter. Autorisiert wird mit einem **Flotten-
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
