# oaap.fleet.status — Read-Only Fleet Status Document

- **ID:** `oaap.fleet.status`
- **Version:** 0.9 (what the node calls itself -- `alias`, `place`, `tags` beside `node`, `oaap.core.host` 2.6, RFC-0082, 2026-11-12; 0.8: the images in the `host` block — counts per state
  word and the oldest date, never an instance, a base or a package — and
  the attention kind `images_open`, `oaap.core.updates` 2.9, RFC-0071,
  2026-11-06; 0.7: the advisories in the `host` block — count, oldest
  date, stale, the number of uncovered packages, never a name — and
  two attention kinds for them, `oaap.core.updates` 2.8, RFC-0070,
  2026-11-06; 0.6: the reboot plan and the protections in the `host`
  block and three attention kinds for them, RFC-0069, 2026-11-05;
  0.5: the `host` block — the care state of the machine
  under the platform, `oaap.core.updates` 2.6 — and three attention
  kinds for it, 2026-11-05 after CVE-2026-98432; 0.4: an instance row's
  `state` may be `standby` — RFC-0059; 0.3 added `auto_address` and
  `auto_state` to instance rows, implemented by the reference 0.1.46)
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
  "schema": "oaap.fleet.status/0.6",
  "node": "oaap.joomp.de",
  "platform_version": "0.1.46",
  "profiles": [],
  "time": "2026-08-23T10:15:00Z",
  "host": {
    "measured": "2026-11-05T10:12:00Z",
    "os": "Debian GNU/Linux 13 (trixie)",
    "kernel_running": "6.12.111+deb13.1-amd64",
    "kernel_installed": "6.12.115+deb13.1-amd64",
    "reboot_required": true,
    "auto_updates": "ok",
    "auto_updates_last_run": "2026-11-05T06:42:00Z",
    "reboot_window": "04:15",
    "gateway_mptcp": "off",
    "advisories": {"open": 13, "oldest": "2026-08-14", "stale": false,
                   "read_at": "2026-11-05T21:15:00Z", "unknown": 4},
    "reboot_plan": {"at": "2026-11-07T03:15:00Z",
                    "at_local": "2026-11-07 04:15 CET",
                    "urgency": "critical", "source": "kernel",
                    "held": false, "overridden": true, "state": "planned"},
    "protections": {"count": 1, "until": "2026-11-12"}
  },
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
    {"kind": "confirmation_pending", "instance": "bdt-hub-test"},
    {"kind": "reboot_required",
     "detail": "running 6.12.111+deb13.1-amd64, installed 6.12.115+deb13.1-amd64"}
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
   The one extension (0.4): an **instance row's** `state` may also be
   `standby` — the instance is asleep on purpose (RFC-0059: `state:
   standby` or `waking` on its record). It is not healthy and not
   broken, it is *not running by choice*, and a consumer must not read
   it as either: it is never an `attention` item, and `auto_state` of a
   sleeping instance is `ok` (its name still answers — with the waking
   page). Core services and names never take it. A 0.3 consumer sees a
   value it does not know and must treat it as `unknown`.
4. **`attention` is the machine-readable "needs a human".** Defined
   kinds today: `core_service_down`, `dns_drift`, `dns_unresolved`,
   `confirmation_pending`, `instance_unhealthy`, and since 0.5 the
   three of the `host` block (rule 8): `reboot_required`,
   `auto_updates_off`, `gateway_mptcp`, and since 0.6 three more of
   the same block: `reboot_planned` (informational), `reboot_deferred`
   and `reboot_overdue`. The list is open —
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

8. **`host`** (0.5) is the **care state** of the machine under the
   platform — the one block about the operating system, defined by
   `oaap.core.updates` 2.6 and only summarised here. It exists because
   a fleet watcher is exactly who has to see "a fix is installed and
   this node has not been rebooted for ten weeks" (oaapx01, 2026-11-05,
   CVE-2026-98432): the platform had the fact and nobody had the view.

   The block is the node's **own latest measurement** with its time
   (`measured`), taken on the machine — a portal in a container cannot
   read the package database — and it is **omitted entirely** when the
   node has not measured yet (an older platform, or a node that has
   just been installed). Fields:

   - `os` — the distribution's own name for itself.
   - `kernel_running`, `kernel_installed` — the running kernel, and
     the newest installed kernel package **of the same flavour** (the
     suffix after the version; a node may hold several flavours).
   - `reboot_required` — `true` when the two differ. **By comparison,
     never by the distribution's marker file**: the marker is written
     by a hook that only exists on a node with the auto-update program
     installed, so its absence proves nothing (oaapx02, 2026-11-05: the
     marker said no, the kernel said yes).
   - `auto_updates` — rule 3 vocabulary: `ok` (the program is
     installed, its periodic switch is set, and its timer is active —
     all three), `warn` (installed, but not switched on or not
     scheduled — installing the package alone does **not** set the
     switch), `error` (not installed), `unknown`.
   - `auto_updates_last_run` — when it last ran; omitted when never.
   - `reboot_window` — `off`, or the local `HH:MM` at which the node
     reboots itself after a kernel update (`oaap.core.updates` 2.6.3).
     This is the one *setting* the block names, deliberately: a
     watcher has to know when a node will go away.
   - `gateway_mptcp` — `on | off | unknown`: whether the gateway's
     public listeners negotiate Multipath TCP (`oaap.core.gateway`
     0.2.18 says they must not). A fact about the listeners in the
     gateway's own network namespace, not a reachability claim.
   - `reboot_plan` (0.6, `oaap.core.updates` 2.7) — omitted when there
     is none; else `at` (ISO-8601 UTC), `at_local` (the node's own
     clock, for a human), `urgency` (`care | critical`), `source`
     (`kernel | manual`), `held` (`true` when live protections hold
     it), `overridden` (`true` when protections were overridden by a
     `critical` plan), `state` (`planned | rebooting | overdue`).
     Never the reason: that is a person's words and stays in the
     tenant log.
   - `advisories` (0.7, `oaap.core.updates` 2.8) — omitted when the
     node never read an advisory list; else `open` (a number, or `null`
     when no list could ever be read — a consumer MUST NOT read null as
     0), `oldest` (the oldest open advisory's date, `""` when none),
     `stale` (`true` when the list is older than two days), `read_at`,
     `unknown` (how many installed packages come from archives the list
     does not cover — a count, not the names). **Never a package
     name**: the names of open advisories are a map of the node's open
     doors and stay with its `server_admin`. Two `attention` kinds
     derive from it: `advisories_open` (detail: count and oldest date)
     and `advisories_stale` (detail: when the list was read).
   - `images` (0.8, `oaap.core.updates` 2.9) — omitted before the node
     read its images; else `instances` (how many), `open`, `behind`,
     `unknown`, `fresh`, `stale` (how many instances carry that word),
     `core_open` (platform containers with open advisories), `oldest`
     (the oldest open advisory in any instance's image). Counts only:
     which instance runs on which base with which open package is the
     node's (rule 1). The attention kind `images_open` derives from it.
   - `protections` (0.6) — omitted when none is live; else `count` and
     `until` (the latest end, a calendar day). Instance names are not
     repeated here: an instance's row already carries its name, and a
     fleet watcher needs to know *that* the node is held, not by whom.

   Three more `attention` kinds derive from these (0.6):
   `reboot_planned` (detail: time and urgency — informational, so a
   watcher knows a node will go away), `reboot_deferred` (a `care`
   plan held more than seven days past its announcement),
   `reboot_overdue` (the plan's time passed without a reboot).

   Nothing else: no package list, no file contents, no sources — rule
   1 holds for this block as for every other. Three `attention` kinds
   derive from it: `reboot_required` (detail: running and installed
   kernel), `auto_updates_off` (detail: which of the three parts is
   missing), `gateway_mptcp` (detail: the listeners that negotiate it).
   A 0.4 consumer ignores the block and the kinds, as rule 4 requires.

### What the node calls itself (0.9, RFC-0082)

```json
  "node": "oaap.joomp.de",
  "alias": "oaapx01",
  "place": "de/strato",
  "tags": ["kunde-cls"],
```

`node` stays what it was -- the name the node is reached by. `alias` is the
node's identifier (`oaap.core.host` 2.6; unset = its normalized hostname),
`place` its path (may be empty), `tags` a list (may be empty). A consumer
groups by `place` and `tags` and flags two nodes reporting one `alias`; a 0.8
consumer ignores the three fields (rule 4).

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

**0.9:** Das Dokument trägt neben `node` (dem Namen, unter dem der Knoten
erreicht wird) jetzt `alias`, `place` und `tags` -- wie sich der Knoten
intern nennt (`oaap.core.host` 2.6, RFC-0082). FleetView kann danach
gruppieren und doppelte Aliasse melden.


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
(RFC-0015). Alles additiv, 0.1- und 0.2-Konsumenten laufen weiter.

**Seit 0.4** kann der `state` einer **Instanzzeile** zusätzlich `standby`
sein (RFC-0059): die Instanz schläft mit Absicht. Das ist weder gesund
noch kaputt — also nie ein `attention`-Eintrag, und der automatische
Name einer schlafenden Instanz bleibt `ok` (er antwortet mit der
Weckseite). Kerndienste und Namen kennen den Wert nicht. Ein 0.3-
Konsument, der ihn nicht kennt, behandelt ihn als `unknown`.

**Seit 0.8** (RFC-0071) trägt der Block `host` die **Abbilder** als Zahlen:
wie viele Instanzen, wie viele mit offenen Meldungen im Abbild, Basis
weitergezogen, unbekannt, frisch, veraltet, Plattform-Container mit
offenen Meldungen, das älteste Datum — nie eine Instanz, eine Basis oder
ein Paket. Dazu die Aufmerksamkeitsart `images_open`.

**Seit 0.7** (RFC-0070) trägt der Block `host` die **Sicherheitsmeldungen**
als `advisories`: Anzahl offener Meldungen (`null`, wenn nie eine Liste
gelesen werden konnte — nie als 0 lesen), das Datum der ältesten,
„veraltet“, wann gelesen, und wie viele Pakete aus fremden Archiven nicht
abgedeckt sind. Nie ein Paketname — die Namen sind eine Karte der offenen
Türen und bleiben beim Server-Admin des Knotens. Dazu zwei
Aufmerksamkeitsarten: `advisories_open` und `advisories_stale`.

**Seit 0.6** (RFC-0069) trägt der Block `host` den **Neustart-Plan**
(`reboot_plan`: Zeitpunkt in UTC und in der Uhr des Knotens,
Dringlichkeit `care`/`critical`, Quelle `kernel`/`manual`, ob Schutze
ihn halten oder überstimmt wurden, Zustand geplant/startet/überfällig —
nie die Begründung, die bleibt im Mandanten-Log) und die **Schutze**
(`protections`: Anzahl und spätestes Ende, keine Instanznamen). Drei
weitere `attention`-Arten: `reboot_planned` (ein Knoten geht weg —
Information), `reboot_deferred` (ein Pflege-Plan über sieben Tage
gehalten), `reboot_overdue` (Termin verstrichen ohne Neustart).

**Seit 0.5** trägt das Dokument den Block **`host`** — den
**Pflegestand** der Maschine unter der Plattform (festgelegt in
`oaap.core.updates` 2.6, hier nur zusammengefasst): laufender Kernel,
neuester installierter Kernel derselben Bauart, daraus `reboot_required`
(durch Vergleich, nie aus der Markierungsdatei — die fehlt auf einem
Knoten ohne das Auto-Update-Programm und beweist dann nichts),
`auto_updates` (`ok` nur, wenn Programm, Schalter **und** Zeitgeber da
sind — das Paket allein setzt den Schalter nicht), der letzte Lauf, das
Neustart-Fenster (`off` oder `HH:MM`, die eine Einstellung, die ein
Flottenbeobachter kennen muss) und `gateway_mptcp` (ob die öffentlichen
Listener des Gateways Multipath TCP aushandeln — sollen sie nicht,
`oaap.core.gateway` 0.2.18). Gemessen vom Knoten selbst auf der
Maschine, mit Zeitstempel; fehlt ganz, solange der Knoten noch nicht
gemessen hat. Drei neue `attention`-Arten leiten sich daraus ab:
`reboot_required`, `auto_updates_off`, `gateway_mptcp`. Anlass war
CVE-2026-98432 am 05.11.2026: Der Fix lag zwei Tage installiert auf
einem Internet-Knoten, der zehn Wochen nicht neu gestartet worden war —
die Plattform hatte die Tatsache und niemand die Sicht. Autorisiert wird mit einem **Flotten-
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
