# RFC-0038: Instance Diagnostics — State, a Time-Boxed Diagnosis Window, and Restart

- **Status:** Draft (2026-09-15) — D1–D5 proposed, awaiting decision
- **Date:** 2026-09-15
- **Authors:** Jörg (need, "explicit activation, limited time", the
  restart question), Claude (design and write-up)
- **Depends on:** RFC-0008 (`server_admin`), RFC-0016 (per-app networks,
  multi-container apps), RFC-0022 (tenant audit log), RFC-0027 (API keys,
  preflight bypass), RFC-0030 (rehearsal instances)
- **Extends:** `oaap.core.portal` 2.4 (instance object page),
  `oaap.apps.runtime` (a restart operation, bounded container logs),
  `oaap.core.gateway` (a time-boxed per-instance access log),
  `oaap.core.tenant` 1.7 (new audit entries). Nothing is withdrawn.
- **Driver:** Jörg, 2026-09-15, while chasing a CORS error: *"Bei der
  Fehlersuche bin ich etwas mittellos."* He asked whether an instance's
  logs can be shown in the portal — gladly behind an extra activation and
  only for a limited time — and whether a manual restart from the portal
  makes sense.

## Summary

The instance object page gains three things, in rising order of
sensitivity:

1. **State** — always visible: running or not, since when, how often the
   container restarted, last exit code, killed for memory. Facts about
   the container, nothing it wrote.
2. **A diagnosis window** — opened explicitly, per instance, for at most
   an hour, audited. While it is open the page shows the **app's log**
   and the **gateway's view** of requests to this instance (method, path,
   status, and the CORS headers going in and out). When it closes, both
   stop and what was collected is deleted.
3. **Restart** — a button that recreates the instance's containers the
   same way a configuration save already does, with a confirmation and an
   audit entry.

And one prerequisite found while writing this: container logs on a node
are **unbounded** today and must get a size limit before the portal
points people at them.

## Motivation

### What an operator has today

| Question | Where the answer is today |
|---|---|
| Is the app running at all? | health page (up/down), nothing about restarts |
| Why did it crash / what does it complain about? | `sudo docker logs …` at the machine |
| Did my browser's request reach the app, and what came back? | nowhere for LAN names; the external access log only records the last hit |
| Can I just restart it? | only indirectly — save an unchanged config (does nothing) or change one |

Everything past the first row needs a terminal and Docker knowledge. The
portal is the administration surface (`oaap.core.portal` 1); for
diagnosis it currently is not.

### Real cases

- **The CORS search (2026-09-15).** A browser refuses a cross-origin
  call. What actually happened is decided between browser, gateway and
  app, and each has a different fingerprint: the preflight answered
  `303 → /auth/login` (no bypass on that route — instances before 0.1.83,
  or a rehearsal by design); `200` without `Access-Control-Allow-Origin`
  (the app does not answer CORS); `403` from `/verify` (the key or role
  does not fit); or a correct answer the browser still refuses (cookies
  sent, origin answered with `*`). The app's own log sees **none** of the
  first and third. The gateway sees all of them.
- **LiveKit on oaapx01 (CURRENT_STATE 135).** A restart loop, whose
  reason was one line in the container log: `LIVEKIT_API_SECRET` missing.
  The portal showed "down"; the reason needed SSH.
- **The 502 Jörg could not analyse (idea store, 2026-08-08).** Same
  shape: the gateway knew "connection refused", the app knew why, the
  person in front of the browser knew neither.

### Why not simply show logs all the time

Logs are written by the app, not by the platform. An app may log request
bodies, e-mail addresses, tokens it received — the platform cannot know
and cannot filter reliably. A permanently visible log would make every
administrator of an instance a permanent reader of whatever the app
chooses to print. Jörg's own suggestion is the right shape: **reading is
an act** — opened on purpose, for a while, and on record.

## Design

### D1 — State is always visible (proposed)

The object page's overview shows, per service container of the instance
(RFC-0016):

- state (running, restarting, exited, not present), **started at**;
- **restart count** and, when not running, **last exit code** and whether
  the kernel killed it for memory (`OOMKilled`);
- when the manifest declares a health check, its current verdict.

A restart count that rose within the last ten minutes is shown as a
warning (*"3 Neustarts seit 14:02 — die App startet vermutlich immer
wieder neu"*), with a pointer to the diagnosis window.

These are facts about the container, not content the app produced. They
need no window and no audit entry. The host writes them next to the
registry for the portal to read, the same pattern as the rehearsal
options view (RFC-0030) — the portal still never talks to the container
runtime.

### D2 — The diagnosis window (proposed)

**Who may open it:** whoever may administer the instance — `server_admin`,
and a `tenant_admin` for an instance of their own tenant (the same rule as
every other card on the page). It is their app and their data.

**How long:** the opener picks **15, 30 or 60 minutes** (default 30). The
window can be closed early. It cannot be extended; opening it again is a
new act with a new audit entry.

**What is recorded** in the tenant audit log (`oaap.core.tenant` 1.7):
opened (who, instance, duration), closed early (who), expired. Not the
contents.

**What the window shows**, both views read-only, with a *Aktualisieren*
button (no JavaScript, as everywhere on the page):

1. **App log** — the last *N* lines (default 200, at most 1000) of every
   service container, stdout and stderr, with timestamps, newest at the
   bottom, one section per service. Produced by the host on request and
   handed to the portal as a snapshot; the snapshot is deleted when the
   window closes.
2. **Gateway view** — see D3.

The page says above both views, in plain words: *"Logs können
vertrauliche Daten enthalten, die die App selbst schreibt. Öffnen Sie das
Fenster nur für die Fehlersuche."*

**On a rehearsal instance (RFC-0030)** the window works the same way. Its
log may show production data — which the person allowed to open it is
already allowed to see through the app.

### D3 — The gateway view: collected only while the window is open (proposed)

Today only external sites write an access log, and it is used for one
line on the health page. This RFC does **not** turn on permanent logging
for every instance. Instead:

- **Opening** the window adds an access log to exactly this instance's
  gateway sites (LAN port, automatic name, own names and aliases),
  written to a file of its own, and reloads the gateway. **Closing** or
  expiry removes it, reloads again, and deletes the file. A Caddy reload
  is graceful: open connections are not dropped.
- Collection therefore **starts** when the window opens. The page says
  so: *"Aufgezeichnet wird ab jetzt — rufen Sie die App danach noch einmal
  auf."*

Each request is shown as: time, method, path **without query string**,
status, duration, and whether it was answered by the app, refused by
`/verify`, redirected to login, or handed straight to the app as a
preflight. For CORS diagnosis, and only these headers:

- request: `Origin`, `Access-Control-Request-Method`,
  `Access-Control-Request-Headers`, and whether credentials were present
  (yes/no — never the value);
- response: `Access-Control-Allow-Origin`, `-Allow-Methods`,
  `-Allow-Headers`, `-Allow-Credentials`, `Vary`.

**Never shown and never written:** the query string (the gateway's own
access log keeps full URIs, and tokens have ended up in query strings
before), `Authorization`, `Cookie`, `Set-Cookie`, the `X-OAAP-*` identity
headers, bodies. A MUST in the gateway spec, not a property the reference
happens to inherit from Caddy's defaults.

The view MAY add one line of interpretation where the pattern is
unambiguous, e.g. *"Die Vorab-Anfrage (OPTIONS) wurde zur Anmeldung
umgeleitet — der Browser bricht hier ab."*

### D4 — Restart recreates, it does not merely restart (proposed)

A button **App neu starten** on the object page, with a confirmation that
names the consequence (*"Die App ist einige Sekunden nicht erreichbar.
Daten, Adresse, Version und Konfiguration bleiben."*).

It runs the operation a configuration save already runs: all service
containers of the instance are **recreated** from their recorded shape on
the instance network, links restored. Not `docker restart`:

- **One path.** Install, restore, config save and restart then produce
  the identical container. A second, lighter path would be the one that
  drifts.
- **It heals more.** A container that is "Up" but lost its network link
  or published port (the gateway case of 2026-08-07) comes back whole.
- **It is not new behaviour.** Files written inside the container
  outside declared storage are already lost on every deploy and config
  save; apps must not rely on them (`oaap.apps.runtime` storage rule).
  Restart makes that no worse.

Who: the same as D2. Refused while a deployment of the instance is
running (RFC-0024) — the page says so instead of queuing behind it.
Audit entry: who, when, instance. The outcome message reports the new
start time, so "did it restart?" is answered by D1, not by trust.

### D5 — Container logs get a size limit (proposed)

Docker's default `json-file` log driver keeps logs **without any limit**
unless configured. No OAAP node configures it: on oaap-test there is no
`/etc/docker/daemon.json`, and the portal container runs with an empty
log option map. A chatty app therefore fills the disk slowly, and a
diagnosis window pointing people at "the log" would be pointing at a file
that can be gigabytes.

Proposal: the platform sets the limit **per container**, at the one place
containers are created (`--log-opt max-size=10m --log-opt max-file=3`,
about 30 MB per container at most), not host-wide in `daemon.json` — a
node may run containers that are not OAAP's, and their owner decides for
them. Core services get the same limit in the compose file.

Existing app containers receive it at their next recreate (deploy, config
save, restart). No forced recreate of every app on update — that would
make an update an outage of every app for a benefit that can wait.

## Interfaces

- **Portal, instance object page:**
  - *Überblick*: state per service (D1), restart warning.
  - New tab **Diagnose**: open/close the window with duration choice,
    remaining time, the two views (D2, D3). Without an open window the
    tab explains what it would show and why it is closed by default.
  - *Verwaltung*: **App neu starten** (D4).
- **Host (spool worker):** actions `diagnose-open`, `diagnose-close`,
  `diagnose-logs` (snapshot), `restart`; a sweep that closes expired
  windows, the same shape as the rehearsal sweep. The host re-checks the
  requester's right on every action — the spool is data, not trust.
- **CLI, at the machine:** `oaap app logs <instance> [--tail N]
  [--service S]` and `oaap app restart <instance>`. No window at the
  machine: the person there already has Docker. `restart` is audited
  (actor `cli`), `logs` is not.

## Non-goals

- **No log storage, search or history.** No Loki, no retention beyond
  Docker's bounded files, no download button in this stage.
- **No live streaming.** Refresh by button; a stream needs a push channel
  the portal does not have and a window that closes cleanly on it.
- **No cross-node diagnosis.** FleetView stays read-only (RFC-0021 §4).
  A remote restart is a signed command and stays a separate RFC.
- **No shell into containers.** `docker exec` from the browser is a
  different order of power.
- **No logs of core services in the portal.** Identity, gateway, portal
  are the operator's at the machine; this RFC is about apps.

## Consequences

For the specification, after acceptance:

- **`oaap.core.portal` 2.4** — state facts, the Diagnose tab and its
  rules (who, duration, warning text, refresh, no JavaScript), the
  restart card; conformance tests.
- **`oaap.apps.runtime`** — the restart operation (= recreate, refused
  during a deployment), bounded container logs as a MUST of the
  reference container shape.
- **`oaap.core.gateway`** — the per-instance access log that exists only
  while a window is open, with the fields that MUST NOT be written.
- **`oaap.core.tenant` 1.7** — entries `diagnose.opened`,
  `diagnose.closed`, `diagnose.expired`, `instance.restarted`.

Build order proposal — each step useful on its own:

1. **D5 + D1 + D4** — log limit, state facts, restart. Small, no new
   privacy question.
2. **D2** — the window with the app log.
3. **D3** — the gateway view inside the window.

## Open for later

- **Correlation id** on the gateway's error page (RFC-0006 idea), findable
  in the gateway view — the step from "I saw a 502" to "this request".
- **Download of a window's snapshot** for handing to a supplier, audited.
- **Core-service logs for `server_admin`** in the same window shape.
- **Upstream error counts** ("12 × connection refused in the last hour")
  without an open window — needs a permanent, content-free counter.

## Deutsche Zusammenfassung

**Anlass:** Bei der Suche nach einem CORS-Fehler (15.09.) warst du im
Portal ohne Werkzeug. Deine Fragen waren: Kann man Logs im Portal zeigen,
mit extra Freischaltung und nur für begrenzte Zeit? Und ist ein Neustart
aus dem Portal sinnvoll?

**Der Vorschlag, drei Stufen nach Empfindlichkeit:**

- **D1 — Zustand, immer sichtbar:** läuft/läuft nicht, seit wann, wie oft
  neu gestartet, letzter Exit-Code, wegen Speichermangel beendet. Das sind
  Fakten über den Container, keine Inhalte der App. Steigt der
  Neustart-Zähler, warnt die Seite: „startet vermutlich immer wieder neu".
- **D2 — Diagnose-Fenster:** Es wird ausdrücklich geöffnet, je Instanz,
  für **15, 30 oder 60 Minuten**. Öffnen darf, wer die Instanz verwalten
  darf (`server_admin`, `tenant_admin` für den eigenen Mandanten).
  Verlängern gibt es nicht, ein erneutes Öffnen ist ein neuer Vorgang. Im
  Audit-Log stehen Öffnen, Schließen und Ablauf, nie die Inhalte. Das
  Fenster zeigt die **letzten Log-Zeilen** jedes Containers der App, mit
  „Aktualisieren"-Knopf und dem Warnhinweis, dass Logs vertrauliche Daten
  enthalten können. Beim Schließen wird alles Gesammelte gelöscht.
- **D3 — Gateway-Sicht im Fenster:** Die ist für CORS das Entscheidende.
  Nur solange das Fenster offen ist, protokolliert das Gateway die Anfragen
  an **diese eine** Instanz: Zeit, Methode, Pfad **ohne Query**, Status,
  wer geantwortet hat (App, Anmeldung, Rollenprüfung, Vorab-Anfrage) und
  die CORS-Kopfzeilen hin und zurück. **Nie** protokolliert werden
  Query-Parameter, `Authorization`, Cookies, Identitäts-Kopfzeilen und
  Inhalte. Aufgezeichnet wird erst ab dem Öffnen, die Seite sagt das.
- **D4 — „App neu starten":** mit Rückfrage und Audit-Eintrag. Technisch
  genau das, was heute schon das Speichern der Konfiguration tut: Die
  Container werden **neu erzeugt**, nicht nur neu angestoßen. Das ist ein
  einziger Weg für alles und heilt auch Container, die „laufen", aber ihr
  Netz verloren haben. Während eines Deployments wird der Neustart
  abgelehnt.
- **D5 — Log-Größe begrenzen (Nebenbefund):** Docker-Logs wachsen auf
  unseren Knoten heute **unbegrenzt**; auf oaap-test gibt es keine
  Einstellung dafür. Vorschlag: höchstens etwa 30 MB je Container
  (3 × 10 MB), gesetzt beim Anlegen des Containers und nicht global für
  Docker. Bestehende Apps bekommen die Grenze beim nächsten Neu-Erzeugen,
  ohne Zwangs-Neustart beim Update.

**Bewusst nicht:** kein Log-Archiv und keine Suche, kein Live-Stream,
keine Diagnose über Knotengrenzen (FleetView bleibt lesend), keine Shell
im Browser, keine Logs der Kerndienste im Portal.

**Kommandozeile an der Maschine:** `oaap app logs <instanz>` und
`oaap app restart <instanz>`.

**Bau-Reihenfolge:** (1) Log-Grenze, Zustand und Neustart, klein und ohne
neue Datenschutzfrage; (2) Fenster mit App-Log; (3) Gateway-Sicht.

**Deine Entscheidungen:** D1–D5. Besonders: ob `tenant_admin` das Fenster
öffnen darf (D2), ob 60 Minuten als Obergrenze passen (D2) und ob der
Neustart „neu erzeugen" statt „neu anstoßen" sein soll (D4).
