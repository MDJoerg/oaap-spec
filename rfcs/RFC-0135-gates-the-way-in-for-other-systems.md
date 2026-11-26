# RFC-0135: Gates — The Way In for Other Systems

- **Status:** **Accepted (2026-11-26)** — D1–D9 decided by Jörg one at a time,
  all as recommended (§9). Stage 0: SM59 ping measured (§11). **Stage 1 built
  (2026-11-26, reference 0.1.383, `vorgaenge` 0.21.0), measured on oaap-test
  (§12), pushed.** **Stage 2a — the portal page „Tore“ — built (2026-11-26,
  reference 0.1.384), measured on oaap-test (§13), pushed.** **Stage 2b —
  fields on the page, German sentences, counts from the access log (D10 a),
  events, the twin — built (2026-11-26, reference 0.1.385), measured on
  oaap-test (§14), not pushed.**
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
- **D10 Where a delivery is counted** (raised in stage 2b: identity only
  judges the login, the outcome is the target's). (a) from the gateway's
  access log, which the node reads every minute anyway: every request of a
  gate is marked there, counted per gate and reason (recommended -- nothing
  on the way of a delivery changes, every later kind of target is counted
  alike; but up to a minute late, no access and no case number); (b) the
  delivery passes identity, which checks the fields and hands over (exact,
  but the payload crosses the security core and identity needs a way to the
  apps); (c) `vorgaenge` reports each outcome to a platform door (exact, but
  the platform believes the app, and every kind of target must report).
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

## 12. Stage 1 built (2026-11-26)

**What there is** (reference 0.1.383, `vorgaenge` 0.21.0; specs
`oaap.core.identity` 0.6.16 §2.15, `oaap.core.gateway` 0.2.25):

- `gates.py`, one module for the field list, the three templates, the check
  of a delivery and the ping text -- shared by appctl and identity and copied
  verbatim into `vorgaenge` (a test holds the two copies equal).
- `gates.json` beside `tenants.json` (owned by the node, read-only for
  identity): gates (name, user name, process, fields) and processes (kind
  `case`, queue, case kind, instance, label).
- `oaap gate list|show|add|remove|process|access|revoke` (CLI first, D1). An
  access is a machine principal `gate-<name>-<n>` with one key limited to
  `oaap.gate:<tenant>/<name>`; `access` prints the key once together with the
  SM59 parameters. Every change is audited (`gate.create`, `gate.process`,
  `gate.access`, `gate.revoke`, `gate.remove`).
- identity: Basic with the key as password at gates only, one check
  (`gate_access`) for ping, templates, delivery and reading, the same 401 for
  every failure, `sap-user` never read.
- gateway: a `/gate/*` block on the tenant's place (label host, own domain,
  apex for the default tenant); gate headers stripped there and on every
  instance site (cases block format 13).
- `vorgaenge`: `/platform/cases/gate` -- checks the delivery against the field
  list in the attested header, creates the case in the process's queue with
  the access as reporter, keeps the technical fields, one case per `ref` and
  access (also after closing), `GET .../<ref>` reads number, status and the
  last answer; JSON or `number=`/`ref=` lines.

**Measured on oaap-test** (tenant `vuebung`, gate `sap-support`, process to
`vuebung-vorgaenge`, from outside through the edge, 2026-11-26):

| Call | Answer |
|---|---|
| no login / wrong key / right key with wrong user / unknown gate | 401, the same sentence |
| ping with Basic and SM59's headers (`sap-user: MMUSTER`) | 200, ping text; `sap-user` ignored |
| ping with Bearer and `Accept: application/json` | 200, JSON |
| templates `placeholders`, `fields` | 200 |
| POST JSON with an unknown field | 422 `unbekannte Felder: prio` |
| POST JSON | 201 `V-2026-0016` |
| the same `ref` again | 200, the same number, `existing` |
| POST form fields, `?answer=text` | 201, `number=V-2026-0017` / `ref=…` |
| GET `/<ref>?answer=text` | 200, number, status, updated, answer |
| GET a foreign `ref` | 404 |
| POST > 64 KB | 413 |
| POST with forged `X-OAAP-Gate-*` headers | 201 -- the case names the real access |
| the gate's key at the `vorgaenge` instance site | 404, never reaches the app |

**Finding, fixed in the same stage:** a client that sent `ü` as Latin-1
(`%FC`, Windows curl) was stored with a replacement character, silently. Now
the gate decodes UTF-8 strictly, or ISO-8859-1 when the Content-Type says
`charset=iso-8859-1`; anything else is refused with a sentence that names the
way out. The placeholder template and the ping say so. Measured after the fix:
without charset 400 with the hint, with `charset=iso-8859-1` 201 and `Prüfung`
stored, UTF-8 201 and `Prüfung` stored. For SAP: send UTF-8, or name the
charset.

**Not yet:** the POST from ABAP (Jörg's side, steps prepared); stage 2 (portal
page „Tore“, twin assets, events, light, „last delivery“ in the ping); a rate
limit per access beyond the case app's 600 per gate and hour.

## 13. Stage 2a built: the page „Tore“ (2026-11-26)

Jörg: the people who set up an interface have no command line — gates belong
in the portal. **What there is** (reference 0.1.384; `oaap.core.portal`
0.3.64 §2.21, `oaap.core.identity` 0.6.17):

- **`/tore`** in the group *Kommunikation*, for `tenant_admin` and
  `server_admin` (`?tenant=` for the latter): per gate address, SM59 user,
  process and target, fields, last use and a **light** (red without target or
  valid access, yellow when a key runs out within 14 days, green otherwise);
  the accesses with expiry and last use; the processes with the gates that
  feed them. Forms for process, gate (a change keeps the fields), access,
  revoke, remove.
- Every change is one request **`gate-admin`**; the host judges role and
  tenant again from the actor's record (`appctl.gate_job`) and runs the same
  `cmd_gate` as the command line; refusals go to the tenant's log.
- **The key is made by the portal** and shown once with the SM59 parameters;
  the host and identity get only `generate_password_hash(secret)`
  (`issue_key(..., secret_hash=)`). One function `gate_issue_access` for CLI
  and portal.
- `test_gates_portal.py` (worker with the real identity, view, templates).

**Measured on oaap-test** (tenant `vuebung`, as its tenant_admin with the
gateway's headers at the portal, the ping from outside through the edge):

| Step | Answer |
|---|---|
| `GET /tore` | 200; gate `sap-support`, process with target `vuebung-vorgaenge`, light green |
| `POST /tore/access` | 200, the key shown once with SM59 path; the list afterwards names the access, no key |
| the same POST with a foreign `Origin` | 403 |
| ping from outside with Basic `sap-support:<key from the portal>` and `sap-user` | 200, ping text naming the access „Messung Portal 26.11.“ |
| wrong user, same key | 401 |
| template `fields` with the key | 200 |
| `POST /tore/revoke` | 303 „… closed: 1 key(s) revoked, principal deactivated“ |
| ping after revoking | 401 |
| tenant log | `gate.access` / `gate.revoke` with the person (`vuebung.carl`) |

**Findings:** (1) a request whose `X-OAAP-User` names nobody active is
refused by the host ("must be requested by a signed-in, active user") — as
designed; the page then shows every light red, because identity lists no keys
for an unknown actor. (2) The host's answers are the CLI's English sentences
on a German page (as on other portal pages that reuse CLI functions) — to be
given German sentences when the page grows.

**Not yet (stage 2b):** fields edited on the page, the twin asset per gate,
the events `oaap.gate.delivered` / `oaap.gate.refused`, counts per day and
refusal reason (the light's "usual rhythm"), "last delivery" in the ping.

## 14. Stage 2b built: counts, events, the twin (2026-11-26)

**What there is** (reference 0.1.385; `oaap.core.portal` 0.3.65,
`oaap.core.identity` 0.6.18, `oaap.events.bus` 0.11):

- **Fields on the page.** A field editor per gate (name, type, length,
  required, where it goes, choices, description, sample; two blank rows to
  add, a tick to remove). It is the request `gate-admin` op `fields`; the
  host runs the same `cmd_gate add` (`fields_doc`), keeps process and user,
  and judges the list with `gates.check_fields` -- the templates follow at
  once.
- **German sentences.** The page answers in German: one table
  (`appctl._GATE_DE`) turns every refusal of `cmd_gate`, `check_fields` and
  `acting_tenant` into the page's sentence; a test holds every `die()` of
  `cmd_gate` and every refusal of the field list against it; what it does
  not know stays visible as „Der Knoten lehnt ab: …“. A change that went
  through says what is now true ("Felder von „x“ gespeichert: 5 Felder, 3
  Pflicht").
- **Counting (D10 a).** Every request of a known gate carries `log_append
  oaap_gate <tenant>/<name>` into the gateway's access log -- the delivery
  route and the ping/template route; the rest of `/gate/` is not marked.
  The minutely sampler hands the marked lines it reads anyway
  (`traffic.measure`) to `gate_stats.fold`: per gate and UTC day
  deliveries (POST 2xx), pings (GET of the gate 2xx) and refusals by
  reason -- `anmeldung` (401), `zu_gross` (413), `zu_viele` (429), `ziel`
  (5xx), `inhalt` (any other POST); templates and reading by `ref` are not
  counted. Last delivery, ping and refusal. 30 days kept;
  `gate-stats.json` beside `gates.json` (0644, no secret). Only a gate
  `gates.json` knows is counted, so a forged field adds nothing.
- **Events** `oaap.gate.delivery.accepted.v1` / `oaap.gate.delivery.refused.v1`
  (platform types, publisher `node`, audience `tenant`, subject
  `gate:<name>`, data `gate`, `status`, `reason`) -- one per delivery and
  refusal, no payload, no access. The host keeps an outbox (at most 1000,
  7 days) and hands it every minute to the twin's `/internal/bus/platform`
  (`gate_events.py` in the twin's container, identity's rule: oldest
  first, stop at the first the bus cannot take yet). (The names differ from
  §7's sketch: a platform type has at least four parts, RFC-0127.)
- **The light** (§7) now also: yellow on refusals today, yellow when a gate
  used on at least three days is quiet for longer than three times its
  usual gap (at least two days); green „in Gebrauch“ with deliveries. One
  rule (`gates_view.light`) for the page and the twin.
- **The ping** ends with „Zuletzt angenommen: <time> (gezaehlt jede
  Minute)“ or „noch nie“; JSON `last_delivery`.
- **The page** shows per gate today, 14 days, and the last delivery, ping
  and refusal with its reason.
- **The twin** (RFC-0088's tenant reader, `assets_model` 0.2.0): the node
  answers for itself as `platform:tore` with the same rules as an app's
  door -- a **gate** (state, light, target, delivered and refused today,
  last delivery, last ping; a state series) and each valid **access**
  (expiry; relation *opens* the gate). Every five minutes, with the run
  that is there.

**Measured on oaap-test** (tenant `vuebung`, gate `sap-support`, from
outside through the edge with the existing access, 2026-11-26):

| Step | Answer |
|---|---|
| ping, delivery, unknown field, wrong key | 200, 201 `V-2026-0026`, 422 `unbekannte Felder: prio`, 401 |
| access log | the four lines carry `oaap_gate <tenant>/sap-support`, the 401 of forward_auth too |
| `gate-stats.json` after the next minute | 1 delivered, 1 ping, refused `anmeldung` 1, `inhalt` 1, with times |
| bus of the tenant | `…accepted.v1` (201), `…refused.v1` (422 `inhalt`, 401 `anmeldung`), `platform:node`, outbox empty |
| page „Tore“ | „1 angenommen, 2 abgelehnt (Anmeldung 1, Inhalt 1), 1 Ping“; light yellow „heute 2 abgelehnt“ |
| ping again | last line „Zuletzt angenommen: 2026-11-26T18:35:58Z (gezaehlt jede Minute)“ |
| field editor on a gate `mess-2b` | saved: „Felder von „mess-2b“ gespeichert: 5 Felder, 3 Pflicht“; without title: „Felder: genau ein Feld geht in den Titel.“; bad name: „Feldname „prio x“: …“; refusals in the tenant log; gate removed |
| twin of `vuebung` | `platform:tore/gate/sap-support` with light yellow, state idle, target, 2 delivered / 2 refused today, last delivery and ping; `…/access/sap-support · Messung Claude` |

**Not here:** the access and the case number of a delivery (the log has
neither; they are in the case); a rate limit per access.

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

**Stufe 1 gebaut (26.11., Referenz 0.1.383, `vorgaenge` 0.21.0, nicht
gepusht):** Tore werden mit `oaap gate` verwaltet (Prozess, Tor, Zugang,
Sperren, Entfernen). Ein Zugang ist ein Maschinenkonto mit einem Schlüssel nur
für dieses Tor. Die Plattform beantwortet Ping und Vorlagen und prüft die
Anmeldung (Basic mit Schlüssel als Passwort oder Bearer). Die Lieferung geht
mit beglaubigten Kopfzeilen an `vorgaenge`; dort wird gegen dieselbe Feldliste
geprüft und der Vorgang angelegt, einmal je `ref`. Lesen nach `ref` gibt
Nummer, Status und die letzte Antwort. Auf oaap-test von außen gemessen (§12),
alle Fälle wie vorgesehen. Befund, gleich behoben: Umlaute in Latin-1 wurden
still verfälscht; jetzt gilt UTF-8 streng oder `charset=iso-8859-1`, sonst
eine klare Ablehnung.

**Stufe 2a gebaut (26.11., Referenz 0.1.384, nicht gepusht):** die Portalseite
**„Tore“** (Kommunikation, für Mandanten- und Server-Admins): Tore mit Adresse,
SM59-Benutzer, Prozess und Ziel, Feldern, letzter Nutzung und Ampel; Zugänge;
Prozesse; Formulare für Prozess, Tor, Zugang, Entziehen, Entfernen. Jede
Änderung prüft der Knoten neu und führt sie mit derselben Funktion wie
`oaap gate` aus. Den Schlüssel macht das Portal und zeigt ihn einmal mit den
SM59-Angaben; Knoten und identity sehen nur den Hash. Auf oaap-test gemessen
(§13): Seite, Zugang, Ping von außen mit dem Portal-Schlüssel 200, Entziehen,
danach 401. Befund: die Rückmeldungen sind noch die englischen Sätze der
Kommandozeile. Noch offen (2b): Felder auf der Seite, Zwilling, Ereignisse,
Zählungen.

## Deutsche Zusammenfassung (Nachtrag: Stufe 2b, D10)

**D10 entschieden (Jörg, 26.11., wie empfohlen):** Gezählt wird aus dem
**Zugriffsprotokoll** des Gateways, das der Knoten ohnehin jede Minute
liest. Am Lieferweg ändert sich nichts, und jede künftige Zielart wird gleich
gezählt; dafür bis zu einer Minute Verzug, kein Zugang und keine
Vorgangsnummer (die stehen im Vorgang).

**Stufe 2b gebaut (26.11., Referenz 0.1.385, nicht gepusht):**
- **Felder auf der Seite:** ein Feld-Editor je Tor, geprüft vom Knoten mit
  derselben Regel wie `--fields`.
- **Deutsche Sätze:** Jede Absage und jede Bestätigung der Seite ist
  deutsch, aus einer Tabelle. Ein Test hält jede Absage der Kommandozeile
  dagegen.
- **Zählung:** Jede Anfrage eines Tors ist im Protokoll markiert. Je Tor und
  Tag zählt der Knoten Annahmen, Pings und Ablehnungen nach Grund (Anmeldung,
  Inhalt, zu groß, zu viele, Ziel), dazu die letzte Annahme, den letzten Ping
  und die letzte Ablehnung. 30 Tage, gefälschte Markierungen zählen nicht.
- **Ereignisse:** `oaap.gate.delivery.accepted.v1` und `…refused.v1`, je
  Lieferung und Ablehnung, ohne Nutzlast, freigebbar wie andere Typen des
  Mandanten.
- **Ampel:** zusätzlich gelb bei Ablehnungen heute oder wenn ein regelmäßig
  benutztes Tor ungewohnt still ist.
- **Ping:** nennt die letzte Annahme. Die **Seite** zeigt heute, 14 Tage und
  das Zuletzt.
- **Zwilling:** Tor und Zugänge als Assets des Mandanten, mit Ampel, Ziel,
  heutigen Zahlen und letzter Annahme.

Auf oaap-test von außen gemessen (§14): Lieferung, Ablehnungen, Zählung,
Ereignisse im Bus, Seite, Ping, Feld-Editor und Zwilling, alle wie
vorgesehen.
