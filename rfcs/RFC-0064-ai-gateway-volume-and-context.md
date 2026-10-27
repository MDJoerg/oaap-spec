# RFC-0064: The AI Gateway, Stage 2 — Suppliers Maintained in the App, Context on the Key, Volume Out Through a Report Interface

- **Status:** **Accepted (2026-10-27)** — Jörg took D1–D8 as
  recommended the same day; on D4 he confirmed the intent: bytes always,
  tokens where the supplier reports them
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
| `calls` | one per request that reached a known, unrevoked key | yes (one row) |
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

**Entschieden (27.10.):** D1–D8 wie empfohlen. Zu D4 hat Jörg bestätigt:
Bytes immer, Token, wenn der Anbieter sie nennt.
