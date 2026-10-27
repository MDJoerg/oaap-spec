# RFC-0064: The AI Gateway, Stage 2 — Suppliers Maintained in the App, Context on the Key, Volume Out Through a Report Interface

- **Status:** **Accepted (2026-10-27)** — Jörg took D1–D8 as
  recommended the same day; on D4 he confirmed the intent: bytes always,
  tokens where the supplier reports them. **Stage 1 built the same day**
  (`ai-gateway` 0.3.0, `oaap.ai.gateway` 0.3, §11), pushed, not
  deployed. **Stage 2 built 2026-10-27** (`ai-gateway` 0.4.0,
  `oaap.ai.gateway` 0.3.1, §12) and **measured on `oaap-test`** as
  0.4.1 (§13), which also fixes a fault older than this RFC: every real
  supplier had answered 404. Stages 3–4 not built.
- **Date:** 2026-10-27
- **Authors:** Claude (analysis & proposal), Jörg (requirement, decides)
- **Depends on:** RFC-0023 (the AI gateway: supply, placement,
  entitlement), RFC-0022 (account and tenant), RFC-0027 (API keys for
  machine principals), RFC-0019 (token hygiene)
- **Changes:** `oaap.ai.gateway` 0.2 → 0.3 (§2 key context, §5 volume
  and the snapshot rule, a new section for the report interface, the
  cost estimate struck); app `ai-gateway` 0.2.1 → 0.3.x

## Summary

The gateway exists and runs (`ai-gateway` 0.2.1, on `oaapx01` since
2026-08-24). It already issues and revokes keys and meters every request.
Three things stop it from being what Jörg now needs:

1. **Suppliers and aliases are text lines in the instance configuration**
   (`AIGW_SUPPLIERS`, `AIGW_SUPPLIER_KEYS`, `AIGW_ALIASES`). The app
   shows them but cannot edit them.
2. **The context on a key is half there and not kept per request.** Cost
   centre and project exist, application does not, and account is fixed
   to `default`. Usage rows carry only the key id, so changing a key's
   cost centre rewrites its history.
3. **Volume leaves the app nowhere.** Totals exist per key only. There
   are no charts, no grouping by context, and no interface a billing
   system could call.

This RFC fixes all three and leaves the money out on purpose. **The
gateway counts volume. It never prices it.** Invoices and cost reports
are produced *outside*, from the numbers it hands out.

## 1. The requirement (Jörg, 2026-10-27)

- Maintain real AI endpoints with their API keys, and offer them under
  **a model name of our own**.
- Issue and revoke our own gateway keys. Each key carries a **context**:
  account, project, cost centre, application.
- **Volume only, no prices:** number of calls, amount of data up and
  down.
- Show the volume **as charts, for internal use and research**.
- Make the same numbers available **through a web service**, so that
  invoices and cost reports can be produced externally.

The last point reverses nothing. RFC-0023 already said prices belong to
the contract with a supplier, not to the platform. The correction of
2026-10-27 confirms that: the earlier draft of this RFC proposed a
price list, and Jörg struck it.

## 2. What is measured: volume, in two units

Per request, at the **consumer side** of the gateway, meaning what the
holder of the key sent and received:

| Field | Meaning | Today |
| --- | --- | --- |
| `calls` | one per request answered on behalf of a known, unrevoked key (refusals for rate limit or an unknown model are not rows, as before) | yes (one row) |
| `in_tokens` / `out_tokens` | as reported by the supplier (`usage`) | yes, nullable |
| `bytes_up` | request body bytes received from the consumer | **no** |
| `bytes_down` | response body bytes sent to the consumer, streamed or not | **no** |
| `outcome` | `ok`, `ok_no_counts`, `budget`, `upstream_failed`, … | yes |

**Why both units.** Tokens are what suppliers bill and what an LLM
"costs". They are missing when a supplier does not report them, which
the gateway records honestly as `ok_no_counts` and never estimates.
Bytes are always known, because the gateway writes them itself. A report
that has to bill can choose its unit. A gap in one unit stays visible
next to the other instead of silently becoming zero.

Bytes are counted on the consumer side, not towards the supplier. The
two differ (the gateway rewrites `model` and adds `stream_options`), and
these are the books of *this* gateway's keys (`oaap.ai.gateway` §5).

A request with an unknown or revoked key is not attributed to anyone. It
gets the same 403 as today and appears in no report.

## 3. Context on the key, and the snapshot rule

A key carries:

- **Four fixed dimensions:** `account`, `project`, `cost_center`,
  `application`. They are free text, edited by the operator, empty
  allowed.
- **The responsible person** (`owner`, exists).
- **Up to five free labels** `name=value` (D3), for whatever the four do
  not cover, such as `course=adt-2026-11` or `customer=…`.

`tenant` stays as it is. It is filled by RFC-0022, not by hand.

> **The snapshot rule:** every usage row carries a copy of the key's
> context *as it was at the time of the request*.

This is the main structural change. Without it, changing the cost
centre of a key in March would move January onto the new cost centre,
and a report already sent to a customer would no longer reproduce. In
SAP terms, a document keeps the account assignment it was posted with.
It does not follow the master record.

Editing the context is allowed at any time. It is audited, and it takes
effect from the next request onwards.

## 4. Suppliers and model names maintained in the app

The operator page gains two forms:

- **Supplier:** name, base address, credential, traffic light. The
  credential is **write-only**: it can be set or replaced, never read
  back, and it appears in no response, page, error or usage row (as
  today, `oaap.ai.gateway` §4).
- **Model name** (today "alias"): our name → an ordered list of
  supplier:model, plus "as listed" or "green before yellow before red".
  The page calls it *model name* because that is what a consumer types
  in. The spec keeps *alias*.

The rules of RFC-0023 do not change. Failover happens only inside the
declared list, and a model name's light is the worst of its targets.

**Migration (D1):** on first start of 0.3, if the app's tables are
empty, the three configuration variables are imported once. From then
on the app's database is the truth, and the configuration page shows
the old lines as "imported on <date>, no longer read". Having two
places that both count means two truths, and sooner or later they
disagree.

## 5. Charts: internal, on the operator page

On the existing `admin` route, with no new role and no external
library. The app stays standard-library only, so the charts are
server-rendered SVG.

- Volume over time (day or month), stacked by one chosen dimension.
- Top N by dimension for a period.
- Share of outcomes: the place where `ok_no_counts` becomes visible.
- Filters: period, any dimension, model name, supplier.

**The charts and the report interface read through the same query
function.** If they did not, the chart and the invoice would disagree
one day, and nobody could say which one is right.

## 6. The report interface

```
GET /report/v1/usage?from=2026-10-01&to=2026-11-01
                    &group_by=cost_center,application,month
                    [&account=…&project=…&model=…&format=csv]
```

- `from` inclusive, `to` exclusive, in UTC. Any of the four dimensions,
  `owner`, `key`, `model`, `supplier`, `outcome`, `day`, `month` can be
  grouped by or filtered on.
- Returns per group `calls`, `in_tokens`, `out_tokens`,
  `calls_without_token_counts`, `bytes_up`, `bytes_down`. The response
  is JSON by default, with CSV available.
- **`complete_until`** in every response: the time up to which the
  numbers are final. The gateway writes a streamed row at the end of the
  stream, so a period is closed only when no request that started in it
  can still be open (the timeout, 600 s by default). Without this field
  a billing run at 00:00:05 would bill a month that later grows.
- `GET /report/v1/keys`: the keys with their current context, without
  key material, for mapping.

**Who may call it (D5):** a machine, not a person in a browser. The
recommendation is to build no new mechanism. The route is declared for
the role `admin`, and the external system uses a **platform API key for
a machine principal** (RFC-0027, Portal → Zugänge). The platform
authenticates, the app sees an identity with the role, and revoking it
happens in the portal like every other machine access. The consumer
keys (`sk-oaap-…`) never open `/report`. `GET /v1/usage` stays as it
is, and every consumer sees only their own usage.

## 7. Retention

Raw rows grow with every call. Recommendation (D6): keep raw rows for
**400 days**, roll them up per day (date × key × context snapshot ×
model name × supplier × model × outcome), and keep the daily rollup
indefinitely. Reports over closed periods read the rollup, so they
produce the same numbers before and after raw rows are deleted. Whether
this holds is a measurement and goes into the tests.

## 8. Stages

1. **Measuring right.** Snapshot columns, `application`, free labels,
   bytes up/down, context editable with audit. Rows written before 0.3
   get the key's *current* context once, marked `context=backfilled`.
   They are honest about being a reconstruction.
2. **Suppliers and model names in the app**, with the one-time import.
3. **Charts and the report interface** on one query function, and
   `complete_until`.
4. **Rollup and retention**, once a measurement shows the raw table
   matters. On `oaapx01` it does not today.

Stage 1 comes first, because every day without a snapshot and without
bytes is volume that can never be reported correctly afterwards.

## 9. Not part of this RFC

- **Prices, currencies, markups, invoices.** These are produced outside
  from §6.
- The Anthropic protocol on the gateway (`ANTHROPIC_BASE_URL`). That is
  a separate gap.
- Chaining (RFC-0023 stage 3) and tenant-facing gateways (stage 4).
- Monthly budgets. Today's budget is a lifetime token total (D8).
- Prompt or completion content. It remains unrecordable
  (`oaap.ai.gateway` §6), and the new columns are numbers and the
  operator's own text, never anything from a request body.

## 10. Decided (Jörg, 2026-10-27, D1–D8 as recommended)

| # | Question | Recommendation |
| --- | --- | --- |
| D1 | Where do suppliers and model names live? | In the app's database. Config variables imported once, then not read |
| D2 | Supplier credential at rest | Encrypted in `/data` with a key from a secret config variable `AIGW_MASTER_KEY`, so a backup of `/data` alone does not disclose it. Without that variable the app refuses to store credentials and says why |
| D3 | Context fields | Four fixed (account, project, cost centre, application) + owner + up to five free labels |
| D4 | "Data up/down": tokens or bytes? | Both. The external report chooses |
| D5 | Who calls `/report` | Platform API key for a machine principal (RFC-0027), role `admin`. No new key type |
| D6 | Retention | Raw rows 400 days, daily rollup indefinitely. Built in stage 4 |
| D7 | Platform or app | App, as decided in RFC-0023: a gateway is a service on a node. It shows as a tile like every app |
| D8 | Budget per month instead of lifetime | Not now. Note it in the idea store, decide when a customer needs it |

## 11. Stage 1 as built (2026-10-27)

- `ai-gateway` 0.3.0. New columns are added on every start through one
  path (`store.ADDED_COLUMNS`), for a new file and an existing one alike.
  Rows from before 0.3 receive the key's then-current context once,
  marked `ctx_source=backfilled`, and keep `NULL` bytes (unknown, not
  zero). The audit log records how many rows that touched.
- Bytes: `bytes_up` is the request body length, `bytes_down` the
  response body sent, streamed payload without chunk framing. Counted
  refusals (budget, no supplier, all suppliers failed) build their
  error body first, so its length is what the consumer receives.
- Context: issue form and CLI take all six fields; "Kontext ändern" on
  the operator page and `key context <label> …` at the machine. A
  revoked key refuses a new context. Each change is audited field by
  field with old → new.
- `GET /v1/usage` and the operator page show bytes.
- Tests: `test_gateway.py` 91 (26 new), `test_supply.py` 40, all green.
  Two deliberate faults (past rows following a context change; stream
  bytes counting chunk framing) were each caught by exactly one test.
- **Not measured on a node yet.** The real question there is whether
  the backfill behaves on `oaapx01`'s existing usage table.

## 12. Stage 2 as built (2026-10-27)

- `ai-gateway` 0.4.0. Three new tables (`suppliers`, `aliases`, `meta`).
  The rules that judge a supplier or an alias are now single functions
  (`supply.make_supplier`, `supply.make_alias`); the old configuration
  lines and the forms both pass through them.
- **D1:** on start, `catalog.import_config` takes the three variables
  over once (`imported`) and records `imported_at`; afterwards they are
  not read, and the page says so while they are still set. If the app
  already maintains suppliers itself, the variables are left lying
  (`skipped`), never merged.
- **D2:** `vault.py`, standard library only: HMAC-SHA256 as a PRF in
  counter mode plus an HMAC tag over version, nonce and ciphertext
  (encrypt-then-MAC), keys derived separately from `AIGW_MASTER_KEY`,
  which the manifest declares `secret: true, generate: token`. Without
  a usable master key (22 characters, as long as a generated token) a
  credential is refused with the remedy; a takeover that includes
  credentials **waits** (`blocked`): the configuration keeps working as
  before and the forms are locked, so there are never two truths.
- A credential that cannot be opened (another master key, a changed
  byte) removes its supplier from routing and is named; an alias that
  needs it becomes unusable rather than silently shorter.
- Forms: create, change (empty credential = unchanged, removal is a
  checkbox), delete. A supplier still in use cannot be deleted; deleting
  an alias names the keys restricted to it. Changes take effect without
  a restart; the routing tables are replaced as a whole, so a running
  request keeps the version it started with, and a model name deleted
  in between answers 400 instead of crashing.
- Found on the way, older than this stage: an admin POST refused with
  403 **before** reading its body. On Windows the connection then ended
  in a reset (1 of 5 test runs crashed), and on keep-alive the unread
  rest would have been read as the next request. The body is now read
  first; 8 of 8 runs green afterwards.
- `Dockerfile` lists modules one by one; `catalog.py` and `vault.py`
  were added — without that the container would not have started.
- Tests: `test_gateway.py` 113 (22 new, run in the post-takeover state
  with a master key; the closing scan now also proves the form-set
  credential is in no file in plain text), `test_catalog.py` 27 (new:
  vault, blocked takeover, wrong master key, skipped), `test_supply.py`
  40. Baits: storing the credential in plain text, and loading a
  supplier whose credential cannot be opened — both caught.
- Measured on `oaap-test` the same day, see §13.

## 13. Measured on `oaap-test` (2026-10-27, 0.3.0 → 0.4.1)

Instance `aigw-test` (channel test), linked to the node's Ollama with
`qwen2.5:0.5b`, plus a red supplier `fern` carrying a measurement
credential that is never called.

1. **0.3.0 installed** from the package at `a14861d`, configured with the
   three old variables, a key with context issued, four requests. The
   first two answered **404 from Ollama**: the gateway asked for
   `…/v1/v1/chat/completions`. The supplier base is documented up to
   `/v1` and the consumer path also begins with `/v1`; since 0.1 the two
   were concatenated. The paper supplier in the tests accepts any path,
   and no test compared it. **Fixed in 0.4.1** (`relay.upstream_url`): a
   base ending in `/v1` does not get it twice; a base without `/v1` — a
   workaround someone may have entered — keeps the path as it is. A new
   test compares the path; with the old line it fails.
2. **Update to 0.4.1 without `AIGW_MASTER_KEY`:** takeover `blocked`;
   `suppliers` empty, no `imported_at`, forms absent, the page heads
   "Noch nicht in die App übernommen"; the configuration kept working —
   real answers from Ollama, plain and streamed, with token counts from
   the end of the stream; all four usage rows kept, with bytes (364 B
   plain, 8,655 B streamed) and the context snapshot.
3. **`AIGW_MASTER_KEY` set** (generated on the node, never displayed):
   on the recreate the takeover ran — 2 suppliers, 2 model names,
   `imported_at`, `config.import` in the audit log; the credential stored
   as `v1:…`, the plain value in neither `gateway.db` nor its WAL; no
   load errors, so it opened again; forms present.
4. **A model name created through the form** appeared in `/v1/models`
   through the platform gateway and answered, **without a restart**
   (container start time still that of step 3). Deleting a supplier in
   use was refused, naming all three users.

**Not measured:** the page in a real browser behind the platform login;
`oaapx01` (Jörg: not yet).

## Deutsche Zusammenfassung

**Ausgangslage.** Das KI-Gateway gibt es (`ai-gateway` 0.2.1, seit 24.08.
auf oaapx01). Es stellt eigene Schlüssel aus, widerruft sie und misst
jede Anfrage. Drei Dinge fehlen: Die echten Endpunkte, ihre Keys und die
Modellnamen stehen als Textzeilen in der Instanz-Konfiguration und
lassen sich in der App nicht pflegen. Der Kontext am Schlüssel ist
unvollständig (Anwendung fehlt, Account steht fest auf `default`) und
wird nicht je Anfrage festgehalten. Nach außen gibt es weder Grafiken
noch eine Schnittstelle.

**Grundsatz nach Jörgs Korrektur:** Das Gateway **zählt Volumen und
bewertet es nie.** Preise und Rechnungen entstehen außerhalb, aus den
Zahlen, die es herausgibt.

**Gemessen** wird je Anfrage auf der Seite des Schlüsselinhabers: Anzahl
Aufrufe, Token rein/raus (laut Anbieter, ehrlich leer, wenn er keine
nennt) und **neu Bytes hoch/runter**. Bytes kennt das Gateway immer,
Token nicht immer. Deshalb liefert es beides, und der externe Bericht
wählt die Einheit.

**Kontext am Schlüssel:** Account, Projekt, Kostenstelle, Anwendung,
Verantwortliche(r) und bis zu fünf freie Etiketten. Der Kontext ist
jederzeit änderbar, jede Änderung wird protokolliert. Die wichtigste
Bauregel: **Jede Messzeile trägt eine Kopie des Kontexts zum Zeitpunkt
der Anfrage.** Wie in SAP behält ein Beleg die Kontierung, mit der er
gebucht wurde. Eine geänderte Kostenstelle verschiebt keine alten
Monate.

**Pflege in der App:** Formulare für Bezugsquellen (Adresse, Key,
Ampel) und Modellnamen. Der Key ist nur schreibbar und wird nie wieder
angezeigt. Die alten Konfigurationszeilen werden einmal übernommen und
danach nicht mehr gelesen.

**Grafiken** auf der Betreiber-Seite, nur intern: Verlauf, Top-N je
Dimension, Anteil der Ausgänge. **Schnittstelle** `GET /report/v1/usage`
mit Zeitraum, Gruppierung und Filtern nach jeder Dimension, als JSON oder
CSV. Grafiken und Schnittstelle lesen über **dieselbe Abfrage**, damit
Bild und Rechnung nie auseinanderlaufen. Jede Antwort sagt mit
`complete_until`, bis wann die Zahlen endgültig sind. Ein
Abrechnungslauf um 00:00:05 würde sonst einen Monat abrechnen, der noch
wächst.

**Zugang für das externe System:** kein neuer Mechanismus, sondern ein
Plattform-API-Schlüssel für einen Maschinen-Benutzer (RFC-0027, Portal
→ Zugänge). Das ist im Grunde ein Webservice wie ein OData-Service, den
ein Abrechnungslauf mit einem technischen Benutzer abfragt.

**Stufen:** (1) richtig messen: Kontext-Kopie, Bytes, Anwendung,
Etiketten. Das kommt zuerst, weil jeder Tag ohne Kontext-Kopie
verlorene Messung ist. (2) Pflege der Bezugsquellen in der App. (3)
Grafiken und Schnittstelle. (4) Verdichtung und Aufbewahrung, wenn
Messungen sie nötig machen.

**Stand 27.10.:** Stufe 1 gebaut (`ai-gateway` 0.3.0), lokal geprüft,
noch auf keinem Knoten. **Entschieden (27.10.):** D1–D8 wie empfohlen. Zu D4 hat Jörg bestätigt:
Bytes immer, Token, wenn der Anbieter sie nennt.
