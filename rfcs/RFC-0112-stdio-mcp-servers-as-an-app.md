# RFC-0112: stdio MCP Servers as an App — a Bridge in Front of the MCP Gateway

- **Status:** **Draft (2026-11-20)** — D1–D11 open. Nothing built. The
  facts in §1 were measured the same day on oaap-test with a loose probe
  (`oaap-lab/stdio-probe`), not with a package and not through the
  platform's source doors.
- **Date:** 2026-11-20
- **Authors:** Jörg (the question, 2026-11-20: can we code with the chat
  and the landscape behind it; for SAP we need the ARC-1 MCP server, which
  speaks stdio and HTTP; could typical stdio MCP servers run in the
  platform "as a further ability of the MCP gateway"; "if authentication
  is needed, we should store or map it per user"), Claude (measurement,
  design)
- **Depends on:** RFC-0065 (MCP gateway; D2 "no stdio" stays), RFC-0073
  (apps as MCP sources, procedure I), RFC-0074 (the chat carries the
  person, procedure A), RFC-0111 (credentials in one place), RFC-0066
  (principal propagation), RFC-0068 (the closed tenant), RFC-0104 (the
  setup door)
- **Not part of this RFC:**
  - **stdio inside the MCP gateway.** The gateway holds the vault and the
    approvals; foreign code does not run next to them. RFC-0065 D2 stays
    as decided.
  - **A coding workspace for the chat** (a person's files, git, running
    code). ARC-1 keeps the code in SAP; for everything else the chat would
    need a workspace of its own — a later RFC.
  - **Installing arbitrary packages at run time** (`npx <anything>`); see
    D3 and stage 4.

## Summary

Many MCP servers speak only stdio: a program a client starts and talks to
through its standard input and output. The MCP gateway speaks only
Streamable HTTP, on purpose.

This RFC adds an app, `mcp-stdio`, that stands between the two. An
instance of it runs **one** stdio server from a catalogue built into its
image and offers it as an ordinary MCP source of the tenant (RFC-0073).
The gateway finds it, an operator approves its tools, and everything the
gateway does — the recorded text, effect classes, limits, usage rows —
applies unchanged.

Two things make this more than a wrapper:

1. **One process per person.** The platform tells the app who is calling.
   Each person gets their own process of the server, started with their
   own credentials, and never meets another person's process.
2. **Credentials from the one place** (RFC-0111). A server that expects
   `SAP_USER`/`SAP_PASSWORD` or `GITHUB_TOKEN` in its environment gets
   them from the person's slot at the moment its process starts. Nobody
   types a password into this app.

## 1. Facts (measured on 2026-11-20 on oaap-test)

A bridge of 200 lines (one child process per MCP session), image
`node:22-slim` with Python, six servers; the MCP gateway `mcpgw-test`
0.28.0. Scripts: `oaap-lab/stdio-probe`.

| # | Question | Result |
|---|---|---|
| F1 | Do typical stdio servers run behind a bridge? | Yes: `server-everything`, `server-filesystem`, `server-memory` (Node), `mcp-server-fetch`, `mcp-server-time` (Python), `arc-1` 1.5.1. Start 250–290 ms (Node), 800–900 ms (Python), 2 s (ARC-1). Calls 5–75 ms. |
| F2 | What does a process cost? | 66–81 MB resident each; ARC-1 150 MB; a minimal Python server 9 MB. Eight processes: 535 MB. |
| F3 | Does the gateway accept them? | Yes. Four servers entered by address; catalogs read (16 / 14 / 9 / 8 tools); one call each through a view with a key answered. |
| F4 | One process per person? | A credential `user:password` became two environment variables of the child. Two persons got two processes; the second person with the first one's session id: 404; no credential: 401. |
| F5 | ARC-1 without a bridge | `arc1 --transport http-streamable` with `ARC1_API_KEYS` starts without a reachable SAP system and is accepted by the gateway as well. |
| F6 | What the probe drops | Requests of a server to the client (elicitation, sampling, roots) and notifications; `server-everything` sent one, ARC-1 one. |

**Not measured:** ARC-1 against a real SAP system; the way through the
platform's source door with a person (procedures I and A); a credential
from a slot (RFC-0111 does not exist yet).

**Read, not measured (ARC-1 documentation, version 1.10.1):** in HTTP mode
ARC-1 validates OIDC tokens (issuer, audience; Keycloak is named) but
reaches SAP **as the person** only through BTP Destination Service plus
Cloud Connector, or through an experimental SAML bearer mode (S/4HANA
2020+, "test systems only"). Otherwise a hosted ARC-1 uses one shared SAP
user. In stdio mode it is single-user by design: credentials from the
environment. SAP's API policy classes the ADT API as internal; the ARC-1
README recommends confirming the intended use with SAP.

## 2. The app

### 2.1 One instance, one server (D1)

`mcp-stdio` is one package. An instance is configured with **one entry of
the catalogue** (`STDIO_SERVER=arc-1`) and that server's settings. A
tenant that wants ARC-1 and a GitHub server installs two instances.

Why not many servers in one instance: an MCP source is one door per
instance (RFC-0073), a light is per server, a closed network (RFC-0068) is
per instance — and a faulty or hostile server then shares nothing with
another one: no file system, no network, no process table.

### 2.2 The catalogue (D3)

The image carries a catalogue: per server the package with an **exact
version**, the command, the environment it understands (each variable
marked *setting*, *secret*, or *fixed*), which RFC-0111 slot shape fits,
whether it needs a working directory, and whether it needs the network.
Nothing is downloaded at run time; a closed tenant can run it. A newer
server version is a new version of the app, with the usual update and its
rehearsal — and because the gateway holds the approved text of every tool,
a changed description is caught there, not here.

First catalogue (proposal): `arc-1`, `server-filesystem`, `server-memory`,
`mcp-server-fetch`, `mcp-server-time`, `mcp-server-git`.

### 2.3 The door and the person

The manifest declares `mcp: {path: /mcp}`. The instance is then a source
of its tenant; the gateway enters it with access `platform`, light red, in
no view, until an operator approves.

A call arrives through the platform with the person's headers and the
assertion (procedure I for a client signed in at the realm, procedure A
for a chat). **The app needs no credential from the gateway** and the
gateway's procedure U is not involved. Without a person a call is refused,
except for a server marked `shared` (§2.4). The discovery door
(RFC-0073 §16) is answered from a process without credentials (D7).

### 2.4 Processes (D2)

- **One process per person**, kept across that person's MCP sessions and
  ended after `STDIO_IDLE_MINUTES` (default 10) without a call. The
  process is initialized once; later `initialize` requests of the same
  person are answered from what it said. (The probe started one per
  session; with 2 s and 150 MB for ARC-1 that is too dear for a chat that
  opens sessions often.)
- A server the catalogue marks **`shared`** (no credentials, no state per
  person — `time`) runs one process for everyone.
- Limits per instance: at most `STDIO_MAX_PROCESSES` (default 20) — the
  next person gets "busy, try again", never someone else's process; a
  memory limit per process; a start timeout; one restart after a crash,
  then the error goes to the caller.
- A process whose person's assertion can no longer be renewed (signed
  out, removed) is ended.

### 2.5 Credentials (RFC-0111)

In the instance's settings an administrator maps the server's secret
variables to a slot: `SAP_USER = sap-a4h.user`, `SAP_PASSWORD =
sap-a4h.password`. The instance needs the grant `receive` for that slot.

- When a person's process starts, the app fetches that person's value with
  their assertion and puts it into **that process's environment only**. It
  is written to no file and no log.
- No value: the call is refused with the sentence and the link of the
  slot's page; the chat's readiness check shows the same before the first
  call (RFC-0111 §3.3).
- The app remembers the value's **version**. Before a call, at most once a
  minute, it asks readiness; a new version ends the process, and the next
  call starts one with the new value. One change in one place reaches a
  running server within a minute.
- A technical slot works the same way without a person (RFC-0111 D11),
  for `shared` servers only.
- *Settings* that are not secret (`SAP_URL`, `SAP_CLIENT`,
  `SAP_ALLOWED_PACKAGES`) are the instance's configuration, set by the
  administrator. A person cannot change what the server may do.

### 2.6 What a process may touch

- It runs without root, without capabilities, on a read-only file system
  with a private temporary directory.
- A server that needs a working directory gets `/data/work/<person>`,
  never a shared one (D8).
- The environment contains only what the catalogue names — not the app's
  own key, not the instance's other variables.
- stderr is discarded. An administrator can switch on a ring of the last
  50 lines for a server, with every known secret value replaced (D9).
- Residual risk, named: processes of two persons of the **same** server
  run under the same user of the container; a hostile server could read a
  neighbour's environment. Separate user ids or a namespace per process
  are measured in stage 2 (D6).

### 2.7 Requests from the server to the client

Stage 1 tells the server that the client can neither be asked
(elicitation), nor sample, nor list roots — so a well-behaved server does
not try. Passing them through needs the server-to-client stream and is
stage 4; the gateway decides per view as today.

## 3. ARC-1, and the question of single sign-on

| Way | Person in SAP | Needs | When |
|---|---|---|---|
| ARC-1 HTTP, shared SAP user | no | — | **not offered** (no technical user behind a person) |
| ARC-1 stdio per person, user and password from the slot | yes | RFC-0111 stage 1 | stage 2 |
| ARC-1 stdio per person, SAP reached through a destination; the platform sets the person's password (`inject`) | yes, and ARC-1 never sees the password | RFC-0111 stage 2 and the *person shim* | stage 3 |
| the same with a destination of kind `principal_propagation` | yes, **without any password** (X.509 from the tenant's CA, `sap_user`) — this is SSO | the person shim; SAP set up as in RFC-0066 | stage 3 |

**The person shim:** ARC-1 does not know our assertion. For each process
the app opens a local address that forwards to the destination and adds
the person's current assertion; the process gets that address as
`SAP_URL`. Whether ARC-1 works through it (CSRF tokens, cookies, redirects
of SAP) has to be measured before it is promised.

ARC-1's own switches stay the first gate: an instance starts read-only
(`SAP_ALLOW_WRITES=false`, no data preview, no free SQL, packages `$TMP`).
An administrator opens them per instance; the gateway's effect classes
and the person's SAP authorizations are the second and third gate. A
tenant that wants "read" and "develop" side by side installs two
instances.

## 4. Security requirements (proposed)

1. No call without a person, except to a `shared` server.
2. A person never reaches another person's process — not by session id,
   not when the limit is reached, not after a restart.
3. A secret reaches only the environment of the one process of its person.
4. The app executes only what its catalogue names; no setting can add a
   command or an argument that is not a declared setting.
5. The instance can be put on a closed network; a server marked "no
   network" then has none.
6. Nothing a server writes to stderr reaches a log unmasked.
7. A value changed or deleted in its slot is not used for a new call
   after one minute at the latest.
8. The app answers the setup door (RFC-0104) for the mapping of §2.5 and
   refuses any field that carries a value.

## 5. Conformance (described; every line gets a bait)

1. Two persons call the same tool; each answer names its own person; the
   process ids differ.
2. Person B sends person A's session id → 404; A's process is untouched.
3. A call without a person to a non-`shared` server → refused, no process
   started.
4. No value in the slot → refused before a process starts, with the link.
5. The value changes → after at most a minute the next call runs in a new
   process with the new value.
6. The 21st person at a limit of 20 → "busy", nobody's process is reused.
7. A setting that tries to add an argument (`--allow-writes true` inside
   a URL field) → refused when saved.
8. The process environment contains no variable outside the catalogue.
9. A server that prints a secret to stderr → the ring shows it masked.
10. The gateway reads the catalog through the discovery door without a
    person and without a credential.

## 6. Stages

| Stage | What | Proof |
|---|---|---|
| **0** | Probe: bridge, six servers, gateway, one process per credential | done (§1) |
| **1** | Package `mcp-stdio` with the catalogue; one server per instance; source of the tenant; persons through procedures I and A; one process per person; servers **without** credentials (`time`, `fetch`, `filesystem`, `memory`) | a chat on oaap-test uses `filesystem` as two persons with two working directories |
| **2** | Credentials from slots (needs RFC-0111 stage 1); process separation measured (D6); ARC-1 per person with user and password | ARC-1 against a4h: two persons, `SY-UNAME` each their own; a changed password in one place |
| **3** | The person shim; ARC-1 through a destination with `inject` and with `principal_propagation` | ARC-1 against a4h without a password anywhere |
| **4** | Requests from the server to the client; further catalogue entries; whether and how packages outside the catalogue (D3) | — |

## 7. Decisions

- **D1 — One server per instance?** *Recommendation: yes* (§2.1). The
  price is one instance per server; the bridge itself is small.
- **D2 — One process per person, kept across sessions, ended when idle?**
  *Recommendation: yes*, 10 minutes, at most 20 per instance.
- **D3 — Where server code comes from:** only the catalogue in the image,
  or also packages an administrator names? *Recommendation: catalogue
  only* through stage 3. A package fetched at run time is foreign code
  with the persons' credentials in its environment; if it comes later,
  then with exact version, checksum, `server_admin` only.
- **D4 — The app's name and capability:** `mcp-stdio`; an app, no new
  platform capability. *Recommendation: yes.*
- **D5 — No shared SAP user, ever:** ARC-1's HTTP mode with one service
  user is not offered, not even read-only. *Recommendation: yes* — it is
  the rule of RFC-0066.
- **D6 — Separation between persons' processes of one server:** same
  container user (stage 1), then measure user ids or namespaces in
  stage 2. *Recommendation: yes;* stage 1 carries no credentials.
- **D7 — The catalog is read from a process without credentials.**
  *Recommendation: yes;* a server that shows its tools only after a login
  (none in the first catalogue) is read by the operator as a person, as
  with procedure P.
- **D8 — Working directory per person in the instance's data.**
  *Recommendation: yes*, in the backup like other instance data; no
  sharing between persons in this RFC.
- **D9 — stderr:** discarded, a masked ring on demand.
  *Recommendation: yes.*
- **D10 — First catalogue:** the six of §2.2? *Recommendation: yes;*
  ARC-1 at the version current when stage 2 is built.
- **D11 — ARC-1 and SAP's API policy:** the app's page states that ADT is
  classed as internal and that using it is the tenant's decision.
  *Recommendation: yes.*

## Deutsche Zusammenfassung

**Worum es geht:** Viele MCP-Server sprechen nur stdio — ein Programm, das
der Client startet und über Ein- und Ausgabe anspricht. Unser MCP-Gateway
spricht bewusst nur HTTP. Eine neue App `mcp-stdio` steht dazwischen: Eine
Instanz lässt **einen** stdio-Server aus einem Katalog laufen, der im
Abbild liegt, und bietet ihn als gewöhnliche MCP-Quelle des Mandanten an.
Das Gateway findet sie, ein Betreiber gibt Werkzeuge frei, und alles, was
das Gateway kann (festgehaltener Text, Wirkungsklassen, Grenzen,
Messzeilen), gilt unverändert. stdio im Gateway selbst gibt es weiter
nicht (RFC-0065 D2 bleibt).

**Zwei Dinge machen daraus mehr als eine Hülle:**

1. **Ein Prozess je Person.** Die Plattform sagt der App, wer ruft. Jede
   Person bekommt ihren eigenen Prozess mit ihren eigenen Zugangsdaten und
   trifft nie den Prozess einer anderen.
2. **Zugangsdaten aus der einen Stelle** (RFC-0111). Erwartet ein Server
   `SAP_USER`/`SAP_PASSWORD` oder ein Token in seiner Umgebung, bekommt er
   sie beim Start aus dem Fach der Person. Ändert die Person den Wert,
   läuft spätestens nach einer Minute ein neuer Prozess damit. In dieser
   App tippt niemand ein Passwort.

**Gemessen am 20.11. auf oaap-test** (lose Probe, kein Paket): Sechs
typische stdio-Server laufen hinter einer Brücke, auch ARC-1. Start 0,25
bis 0,9 Sekunden, ARC-1 zwei Sekunden; 66 bis 81 MB je Prozess, ARC-1
150 MB. Das Gateway liest die Kataloge und ruft die Werkzeuge. Zwei
Personen bekamen zwei getrennte Prozesse. **Nicht gemessen:** ARC-1 gegen
ein echtes SAP, der Weg über die Quellen-Tür mit Person, Zugangsdaten aus
einem Fach.

**ARC-1 und SSO:** ARC-1 bringt die Person von sich aus nur über BTP und
Cloud Connector ins SAP, sonst arbeitet es zentral mit einem gemeinsamen
Benutzer — das bieten wir nicht an. Unser Weg in drei Schritten: erst
Benutzer und Passwort je Person aus dem Fach (Stufe 2); dann erreicht
ARC-1 das SAP über eine Destination, und die Plattform setzt das Passwort
ein, ohne dass ARC-1 es sieht; schließlich dieselbe Destination mit
Zertifikat der Mandanten-CA — **ohne Passwort, das ist SSO** (Stufe 3).
Für die letzten beiden braucht es ein kleines Zwischenstück je Prozess,
das die Zusicherung der Person anhängt; ob ARC-1 damit sauber läuft, ist
zu messen.

**Sicherheit in Kürze:** kein Aufruf ohne Person; eine Instanz = ein
Server, damit ein Server nichts mit einem anderen teilt; nur Code aus dem
Katalog mit exakter Version, nichts wird zur Laufzeit geladen; ARC-1
startet nur lesend, der Verwalter öffnet mehr je Instanz. Benanntes
Restrisiko: Prozesse zweier Personen desselben Servers laufen zunächst
unter demselben Benutzer im Container; die Trennung wird in Stufe 2
gemessen, vorher gibt es dort keine Zugangsdaten.

**Nicht Teil:** ein Arbeitsbereich zum Coden außerhalb von SAP (Dateien,
Git, Ausführen) und beliebige Pakete zur Laufzeit.

**Stufen:** (0) Probe, erledigt; (1) Paket mit Katalog, Server ohne
Zugangsdaten, Personen über die Plattform; (2) Zugangsdaten aus Fächern,
ARC-1 je Person gegen a4h; (3) Zwischenstück, ARC-1 über Destination mit
eingesetztem Passwort und mit Zertifikat; (4) Rückfragen der Server,
weitere Katalogeinträge.

**Entscheidungen D1–D11** sind offen, Empfehlungen in §7: ein Server je
Instanz; ein Prozess je Person mit Leerlauf-Ende; nur der Katalog; nie ein
gemeinsamer SAP-Benutzer; Hinweis auf SAPs Einstufung der ADT-API.
