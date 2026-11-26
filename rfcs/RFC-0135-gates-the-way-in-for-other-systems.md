# RFC-0135: Gates — The Way In for Other Systems

- **Status:** **Accepted (2026-11-26)** — D1–D9 decided by Jörg one at a time,
  all as recommended (§9). Nothing built; stage 0 (SM59) next.
- **Date:** 2026-11-26
- **Authors:** Jörg (the need: "eine Verwaltung, wo wir die Trigger/Tore pflegen
  und auch Zuordnungen von Tor zu Vorgangstyp + Agenten … später eine 1:n
  Zuordnung … Transparenz – eine Idee für den Zwilling"; "Ein Aufruf unserer
  Plattform wäre also idealerweise eine SM59-Destination mit Host/Port/Pfad";
  "ein als String generiertes Template des erwarteten Payloads"), Claude (design)
- **Depends on:** RFC-0027 (machine principals and keys), RFC-0134 (the case
  from SAP; this RFC replaces its §3/§3a), RFC-0127 (events), RFC-0120/0125
  (the twin), RFC-0061 (cases)
- **Changes (when accepted):** a platform capability "gates" (portal page,
  gateway route, identity: Basic with a key as password); `vorgaenge` gains a
  gate door; RFC-0134 §3/§3a are replaced; idea I-75 becomes this RFC, I-76
  (coupling) stays its own

## Summary

Other systems will start work in a tenant: SAP when it knows no answer, a
Node-RED flow, a web form, later more. Each needs a way in that its own people
can set up with their own tools, that is safe, and that someone can watch.

A **gate** is that way in: a named address of the tenant with its accesses, the
fields it expects and the **process** it starts. One process can have several
gates (SAP, Node-RED, a form), so a gate never *is* the process, it points to
it. Gates are kept on one page of the portal and appear in the twin, so the
operator sees every way in, when it was last used and whether a key runs out.

The first caller is SAP, and SAP sets the bar for "easy": an HTTP destination in
transaction **SM59** with host, port, path and user/password; a **connection
test** that is a plain GET; a payload it can fill from a **text template**
without building JSON in ABAP. What is easy for SAP is easy for everyone else.

## 1. Words

| Word | Meaning |
|---|---|
| **Gate** (Tor) | a named way in of one tenant: address, accesses, expected fields, target process, state |
| **Access** (Zugang) | one sender at one gate: a machine principal (RFC-0027) with a key limited to that gate, its own expiry, its own label ("SAP A4H 001") |
| **Process** (Prozess) | what a gate starts: a target door of an app with its parameters — first `vorgaenge`: queue, kind, field mapping; the lead specialist follows from the queue (RFC-0134) |
| **Field** (Feld) | one expected value: name, type, format, required, description, where it goes in the target |

## 2. The address and the calls

A gate lives on the tenant's place (RFC-0042/0115), under a reserved path:

```
https://bec.brandeis.de/gate/sap-support            (or <tenant>.<node>/gate/<name>)
```

| Call | Does |
|---|---|
| `GET /gate/<name>` | **ping** (§4): 200 with plain text when the access is valid |
| `POST /gate/<name>` | **deliver**: JSON *or* form fields; checked against the fields; the process starts; answer at once |
| `GET /gate/<name>/template?form=sample` | the payload as JSON with sample values |
| `GET /gate/<name>/template?form=placeholders` | the same with `"{field}"` placeholders, to fill in ABAP |
| `GET /gate/<name>/template?form=fields` | a text table: field, type, format, required, description |
| `GET /gate/<name>/<ref>` | the state of what this access delivered under `ref` (number, status, closing text) |

The templates need the access too: they describe a tenant's process.

**SM59, type G** (HTTP connection to external server): target host = the
tenant's host, port 443, path prefix `/gate/sap-support`, SSL active with the
platform's certificate in STRUST, logon "basic authentication" with user =
the gate's user name (§3) and password = the access's key. "Connection test"
sends a GET to the path prefix — the ping.

## 3. Logging in

1. **Bearer** as today: `Authorization: Bearer oaapk_…`.
2. **Basic**, new at the gateway: `Authorization: Basic base64(user:password)`,
   where the **password is the key** and the user is the gate's user name (by
   default the gate's name, `sap-support`). Identity takes Basic **only** when
   the password has the form of a platform key; any other Basic header belongs
   to the app behind and travels on untouched (the rule of I-44 for foreign
   bearers). A wrong user name with a right key is refused, so a key copied into
   the wrong destination fails visibly.
3. An access's key is limited to its gate (scope `oaap.gate:<tenant>/<name>`),
   reaches nothing else, and carries no roles worth asking about — the gate is
   the scope (as the cases door of RFC-0061 §3.2).

Failure answers are short text (or JSON on `Accept: application/json`), never a
login page: `401 Tor sap-support: Anmeldung fehlt oder Schlüssel ungültig`. An
unknown gate and a wrong key give the **same** answer, so the address tells a
stranger nothing.

## 4. The ping

`GET /gate/<name>` with a valid access answers `200 text/plain`:

```
OAAP-Tor: sap-support (Mandant bec)
Zugang: SAP A4H 001 · Schlüssel gültig bis 2027-02-24 (90 Tage)
Prozess: Vorgang in „SAP-Support“, Leitung: Leiter SAP
Felder: 5 (3 Pflicht) · Vorlage: /gate/sap-support/template?form=placeholders
Annahme: JSON oder Formularfelder · höchstens 64 KB · 600 je Stunde
Serverzeit: 2026-11-26T09:14:03Z · Plattform 0.1.38x
Zuletzt angenommen: 2026-11-26T08:59:41Z (V-2026-0142)
```

Nothing in it is a secret; all of it helps the person at SM59 who asks "why
does it not work". The ping is recorded (§7): a gate that is pinged but never
used, or used but never pinged, both say something.

## 5. Fields and templates

A gate's fields are a short list the tenant administrator keeps:

| Name | Type | Format | Required | Description | Goes to |
|---|---|---|---|---|---|
| `ref` | text | ≤ 120 | yes | the caller's own reference; the same `ref` twice is one delivery | case reference |
| `title` | text | ≤ 200 | yes | short description | case title |
| `text` | text | ≤ 20 000 | yes | what the person asked, what SAP knows | case text |
| `system` | text | `A4H/001` | no | system and client | technical field |
| `occurred` | timestamp | `YYYY-MM-DDThh:mm:ssZ` | no | when it happened | technical field |

Types: text, number, timestamp (always UTC with `Z`), date, yes/no, choice. The
three template forms are generated from this list, so they cannot drift from
what the gate accepts. The **placeholder** form says above itself which
characters must be escaped when a placeholder is replaced in JSON (`"`, `\`,
line breaks) — and the gate also takes the **same fields as form fields**
(`application/x-www-form-urlencoded`), which ABAP sets without any JSON
(`if_http_entity->set_form_field`). Unknown fields are refused with a sentence
that names them (D5): the template is the contract.

The answer of a delivery is JSON, or on `?answer=text` / `Accept: text/plain`
two lines an ABAP program reads without a parser:

```
number=V-2026-0142
ref=ZSUP-000815
```

## 6. Process

A gate points to exactly one process; a process can have many gates. A process
is a target door and its parameters. The first kind:

- **case** (`vorgaenge`): queue, kind, which fields become title, text,
  reference and technical fields. The lead and the work follow from the queue
  (RFC-0134 §4–§8). The gate hands over to the `vorgaenge` instance of the
  tenant through a platform door with **attested** headers (gate, access,
  tenant), like the feedback and cases doors today; `vorgaenge` trusts the
  gate, not the caller.

Later kinds (not in this RFC): a Node-RED flow (I-74), an event into the bus
(RFC-0127). The gate page shows per process which gates feed it.

## 7. Transparency: gates in the twin

Every gate is an asset of the tenant in the twin (RFC-0120/0125) with:
accesses (label, expiry, last use), last ping, last delivery, deliveries per
day, refusals per reason, target process. Each delivery and each refusal is an
event `oaap.gate.delivered` / `oaap.gate.refused` (RFC-0127) — without the
payload, which belongs to the target. The portal page shows a light per gate:
green (used in its usual rhythm), yellow (a key expires within 14 days, or
refusals), red (no access valid, or the target is gone). The platform keeps no
payloads; what was delivered is in the case.

## 8. Relation to RFC-0134 and I-76

- RFC-0134 §3/§3a (registered senders inside `vorgaenge`) are **replaced**: the
  sender list becomes the gate's accesses; `ref`, reading by `ref` and the note
  stay, now at the gate. RFC-0134 D1's intent — one way for every trigger —
  holds: the chat keeps filing through the MCP door, everything from outside
  comes through a gate.
- An access is handed over today by showing its key once (as RFC-0027). A
  **coupling file** with a redeem code (I-76) is the better hand-over and will
  plug in here; it is not part of this RFC.

## 9. Decisions

Each with a recommendation; to be decided one at a time.

- **D1 Where gates live.** (a) a platform capability: portal page „Tore“,
  route `/gate/<name>` on the tenant's place, the target is an app's door
  (recommended — one place for every way in, 1:n and the twin come with it);
  (b) inside `vorgaenge` only, as RFC-0134 §3 planned.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D2 Address.** (a) `/gate/<name>` on the tenant's host (recommended — one
  certificate, one host in SM59 for all gates); (b) a host of its own per gate.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D3 Logging in.** (a) Bearer and Basic with the key as password and the
  gate's user name, both per access (recommended); (b) Bearer only.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D4 Accesses.** (a) one machine principal per access, its key limited to the
  gate, own label and expiry, several per gate (recommended); (b) one shared
  key per gate.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D5 Payload.** (a) JSON and form fields, both checked against the field
  list; unknown fields refused with their names (recommended); (b) unknown
  fields kept as technical fields.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D6 Ping and refusals.** (a) the ping text of §4 for a valid access; the same
  short 401 for an unknown gate and a wrong key (recommended); (b) a ping
  without login that only says "gate exists".
  → **Decided 2026-11-26: (a)** (Jörg).
- **D7 Gate and process.** (a) separate objects, a gate points to one process, a
  process has many gates (recommended); (b) the gate holds its target itself.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D8 Transparency.** (a) twin asset per gate, events without payload, light on
  the portal page (recommended); (b) only a log on the gate page.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D9 Answer format.** (a) JSON by default, `number=…`/`ref=…` lines on request
  (recommended); (b) JSON only.
  → **Decided 2026-11-26: (a)** (Jörg).

## 10. Stages

- **Stage 0 — measure with SAP** (before building): an SM59 type G destination
  from `a4h` to a stub path on oaap-test or bec: Basic with a key as password
  (what SM59 sends exactly, including on the connection test), TLS with the
  platform certificate in STRUST, the GET of the connection test, a POST of a
  template filled in ABAP and of form fields. Jörg's side for SM59/ABAP, mine
  for the stub.
- **Stage 1 — the gate**: identity Basic-with-key, gate records and accesses
  (CLI first), route, ping, templates, delivery to `vorgaenge` with `ref`,
  reading by `ref`. Replaces RFC-0134 stage 1.
- **Stage 2 — the page and the twin**: portal page „Tore“ (gates, accesses,
  processes, light), twin assets, events.
- **Stage 3 — coupling** (I-76, own RFC) plugs into accesses.

## 11. Stage 0 prepared (2026-11-26)

A probe app `gate-probe` 0.1.0 runs on oaap-test, tenant `vuebung`, at
`https://gate-probe.vuebung.oaap-test.oaap-demo.duckdns.org/gate/probe`
(public route; the app checks Basic itself: user `probe`, password in
`test/.env` as `OAAP_TEST_GATEPROBE_PASSWORD`). It answers like a gate —
ping, three templates, JSON or form fields, strict fields (422 with names),
answer as JSON or `number=`/`ref=` lines — and records what arrived (method,
path, headers without secrets, authentication scheme and user, body up to 4 KB)
under `/gate/probe/log`. Checked from outside: 401 without login, ping 200,
templates, POST JSON 201, POST form fields with text answer 201, unknown field
422. Certificate chain: Let's Encrypt `YE1` → ISRG `Root YE` → `ISRG Root X2`
→ `ISRG Root X1` (for STRUST).

**SM59 connection test measured (2026-11-26, a4h → probe):** one `GET
/gate/probe`, **Basic sent pre-emptively** on the first request (no 401
challenge needed), user `probe`, answered 200 with the ping text. SM59 adds
`User-Agent: SAP NetWeaver Application Server (1.0;758)`, `sap-language: E` and
`sap-user: probe`; no `Accept`. TLS with the Let's Encrypt chain worked. For the
gate this means: Basic with the key as password works as designed (D3), the ping
is a plain GET on the path prefix (D6), and `sap-user` must be ignored, never
read as an identity. Open: the POST from ABAP (template and form fields) —
Jörg, later.

## Non-goals

- Storing payloads on the platform.
- Other targets than `vorgaenge` in stage 1.
- Outbound calls from OAAP to SAP (that is the MCP side, RFC-0134 §6).
- Client certificates in SM59 (possible later; user/password is what SAP
  people set up without help).

## Deutsche Zusammenfassung

Andere Systeme stoßen Arbeit im Mandanten an: SAP, wenn es keine Antwort weiß,
ein Node-RED-Flow, ein Webformular. Dafür gibt es **Tore**. Ein Tor ist ein
benannter Eingang des Mandanten unter `/gate/<name>` auf seiner Adresse. Es hat
**Zugänge** (je Absender ein Maschinenbenutzer mit eigenem Schlüssel und
Ablauf), eine **Feldliste** mit Typ, Format, Pflicht und Beschreibung und zeigt
auf genau einen **Prozess**. Ein Prozess kann viele Tore haben (1:n), das erste
Ziel ist ein Vorgang in einem Bereich mit leitendem Spezialisten (RFC-0134).

SAP setzt den Maßstab für „einfach“:
- **SM59 Typ G** mit Host, Port und Pfad; Anmeldung mit Benutzer und Passwort,
  wobei das Passwort der API-Schlüssel ist. Das Gateway lernt dafür neben
  `Bearer` auch Basic, aber nur, wenn das Passwort wie unser Schlüssel aussieht.
- Der **Verbindungstest** ist ein GET auf das Tor: Bei gültigem Zugang kommt ein
  Klartext mit Tor, Mandant, Zugang, Ablauf, Prozess, Feldern, Serverzeit und
  letzter Annahme. Unbekanntes Tor und falscher Schlüssel sehen gleich aus.
- **Vorlagen als Text:** mit Musterdaten, mit Platzhaltern `{feld}` und als
  Feldtabelle, alle aus derselben Feldliste erzeugt. Das Tor nimmt zusätzlich
  Formularfelder an, die ABAP ohne JSON setzt. Die Antwort gibt es auf Wunsch
  als zwei Zeilen `number=…` und `ref=…`.

Jedes Tor ist ein Asset im **Zwilling** mit letztem Ping, letzter Annahme,
Annahmen je Tag, Ablehnungen und Ablauf der Schlüssel, dazu Ereignisse ohne
Nutzlast und eine Ampel auf der Portalseite „Tore“. Das RFC ersetzt RFC-0134
§3/§3a (Absenderliste). Die Kopplungsdatei mit Einlösecode (I-76) kommt später
als eigenes RFC und hängt sich an die Zugänge. Stufe 0 misst vorher mit einer
echten SM59-Destination aus a4h.

**Entschieden am 26.11. (Jörg, einzeln, alle wie empfohlen):** D1 Tore als
Plattformfähigkeit mit Portalseite „Tore“; D2 Adresse `/gate/<name>` am
Mandanten; D3 Bearer und Basic (Schlüssel als Passwort); D4 ein Zugang je
Absender; D5 JSON und Formularfelder, unbekannte Felder abgelehnt; D6 Ping nur
mit gültigem Zugang, gleiche 401 für unbekanntes Tor und falschen Schlüssel; D7
Tor und Prozess getrennt (1:n); D8 Zwilling, Ereignisse und Ampel; D9 JSON und
auf Wunsch Textzeilen.
