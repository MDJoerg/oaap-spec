# oaap.data.timeseries — Values Over Time

- **ID:** `oaap.data.timeseries`
- **Version:** 0.1
- **Maturity:** draft
- **Based on:** RFC-0086 (accepted 2026-11-12; D1 amended by Jörg: short
  texts as well as numbers); `oaap.data.twin` (every series belongs to a
  twin object; the twin's service serves this API with the twin's keys);
  `oaap.data.store` (the node's PostgreSQL); RFC-0051 (tiers with mean,
  minimum and maximum; a gap stays a gap); RFC-0085 (the first writer)

## 1. Purpose

Values over time, attached to a twin object: **numbers**, kept in tiers
that shrink with age, and short **texts** such as a status, kept as their
changes; queried by range and step. The default store is the node's
PostgreSQL with nothing added. Other stores may sit behind the same
driver interface; one conformance suite, run against every driver, keeps
the interface honest (§6).

## 2. Model

| Term | Meaning |
|---|---|
| **series** | one measured quantity of one twin object: `(object, measure, labels)` |
| **kind** | `number` or `text`, fixed at creation |
| **point** | `(t, x)` — a time in UTC (seconds or ISO-8601 with zone) and a value of the series' kind |
| **policy** | `standard`, `short` or `long` (§4), fixed at creation |
| **bucket** | one interval of a tier: `mean`, `min`, `max`, `count` |

- `object`: a twin object id of the caller's tenant. No object, no series.
- `measure`: `[a-z][a-z0-9_.]{0,62}`. `labels`: at most 8 pairs, names
  `[a-z][a-z0-9_]{0,31}`, values 1–64 characters; part of the identity.
- `unit`: free, at most 32 characters (UCUM spelling recommended).
- `expected_s` (optional, 1–86 400): the interval the writer promises;
  makes gaps of text series visible (§4.4).

### 2.1 Kinds

- **`number`** — a finite double. NaN and infinities are refused.
- **`text`** — at most **64 Unicode code points**, not empty, no control
  characters (Unicode category C), no line breaks. A longer value is
  **refused with a reason, never cut**. The bound is also the column type
  of the default driver. Messages, free text and log lines are events, not
  series.

## 3. Interface

Served by the twin's service under its gateway route `/twin/*`, with the
caller's twin credential; the tenant comes from the credential, never
from the request.

| Call | Does |
|---|---|
| `PUT /twin/series` | create or find: `object`, `measure`, `labels`, `kind`, `unit`, `policy`, `expected_s`; answers the series and whether it was created. A found series with another kind or policy is refused |
| `POST /twin/series/{id}/points` | append `{"points": [[t, x], …]}`, at most 10 000 |
| `POST /twin/points` | append for several series: `{"series": {"<id>": [[t, x], …]}}` |
| `GET /twin/series?object=…` | the series of an object |
| `GET /twin/series/{id}/range?from&to&step` | §4.3 / §4.4 |
| `GET /twin/series/{id}/latest` | the last point |
| `DELETE /twin/series/{id}` | removes the series and all its points; audited |

**Writing answers counts**, never silence: `written`, `duplicate`,
`refused` (with up to three reasons), `late`; text writes also
`extended`.

- **Idempotent:** a time a series already holds is a `duplicate`; the
  first value stands.
- **Late points** inside the raw retention are accepted; the buckets they
  touch are recomputed by the next roll-up, tier by tier upward. Older
  points are refused with a reason.
- A point more than **one hour in the future** is refused.
- **Limits per tenant:** 10 000 series (driver), 20 000 points per minute
  (service); refused with a reason.

## 4. Policies, tiers, reading

### 4.1 Policies

| Policy | raw | 5 min | 1 h | 1 day |
|---|---|---|---|---|
| `standard` | 7 days | 31 days | 400 days | 10 years |
| `short` | 2 days | 7 days | — | — |
| `long` | 31 days | 400 days | 10 years | 10 years |

A new policy is a change of this spec. Retention is honoured at the
granularity of a partition: raw data lives at most one day longer, a tier
at most one month longer.

### 4.2 Roll-up

A bucket is computed once its interval has closed **plus two intervals**
(a 5-minute bucket after 10 minutes, a day bucket after two days), from
the tier below: `mean` weighted by `count`, `min` of minima, `max` of
maxima, `count` summed. A bucket with no points is not written — a gap
stays a gap.

### 4.3 Reading numbers

`range` picks the **coarsest tier not coarser than `step`** that still
covers `from`; when `from` lies beyond that tier's retention it answers
from the next coarser tier that covers it and says so in `note`. No answer
has more than **2 000 buckets**; a wider request is answered coarser, with
a note. Buckets are re-aggregated to `step` from the chosen tier. Answer:
`{series, kind, tier, step, note, buckets: [{t, mean, min, max, count}]}`.

### 4.4 Text series

Kept as **state intervals** `(from, value, last_seen)`:

- the same value as the open interval moves `last_seen`;
- another value opens a new interval;
- with `expected_s`, a point more than **three** expected intervals after
  `last_seen` opens a new interval even with the same value, and the time
  between is a gap;
- a time already covered by an interval with the same value is a
  `duplicate`; a late other value inside the raw retention splits the
  interval it falls into.

Reading without `step`: the intervals clipped to `[from, to]`, each with
`open` when it still holds now. With `step`: per bucket the value at its
end (`at_end`), the number of states that began in it (`changes`) and the
value held longest (`longest`).

Text intervals are kept as long as the policy's longest tier, counted from
**`last_seen`**: a state that has held for years stays.

## 5. The default driver: PostgreSQL

- One schema per tenant, `ts_<tenant-id>`, own role, beside the twin's.
- `series`; `raw_<policy>` partitioned **by day**; `a5m_`, `a1h_`,
  `a1d_<policy>` partitioned **by month**; primary keys `(series_id, t)`,
  writes `ON CONFLICT DO NOTHING`.
- **Tables per policy** — retention is dropping partitions, and policies
  with different retention cannot share one.
- **`text_states` is not partitioned** (departure from RFC-0086 §5, which
  said yearly): an interval belongs to the time it was last seen, not to
  the time it began; dropping the partition of its first day would remove
  a state that still holds. The rows are few (RFC-0086 §4.4), expiry is a
  `DELETE` by `last_seen`. `value varchar(64)`.
- `marks` (rolled up to here per policy and tier), `dirty` (buckets late
  points invalidated), `counters` (per day: `duplicate`, `refused`,
  `late`, `partitions_dropped`, `text_states_expired`).
- **Job** (the store node's minutely unit): create today's and the next
  days' partitions, roll up, expire. It never fails the unit.
- A refused or failed call rolls its transaction back (an open
  transaction would hold its locks).
- PostgreSQL License only; no extension; the image of `oaap.data.store`.

## 6. Driver interface and conformance

A driver implements `ensure_schema`, `ensure_series`, `get_series`,
`list`, `drop_series`, `write`, `roll_up`, `expire`, `job`, `latest`,
`range`, `intervals`, `counters`, `size`, `export`, `import`. The driver
is chosen per node; the default is `postgres`. `export`/`import` use one
driver-neutral form (JSON lines: series, raw points, buckets, text
intervals); the default driver's backup is `pg_dump` of the schema.

**The conformance suite** (reference: `test/test_timeseries.py`) covers:
create-or-find and fixed kind/policy; series limit, and no open
transaction after a refusal; idempotency and counted duplicates; refusal
of points too old, too far ahead, not numbers, not finite; ISO times with
zone; gaps that stay gaps; minimum and maximum surviving raw → 5m → 1h →
1d; the weighted mean; late points recomputing their bucket and the tiers
above; tier choice by step and retention with notes; at most 2 000
buckets; partitions dropped on time and only for their own policy; text:
one row per change, gap after three intervals, 64 accepted and 65 refused
by the API and by the column, duplicates, late splits, per-step summary,
expiry by `last_seen`; the tenant boundary; the export/import round trip
and its idempotency. **A driver that fails it is not offered.**

## 7. Reference status (0.1)

Built in the reference: the driver and the suite (green on PostgreSQL 16,
with mutation counter-checks); a simulated year measured (RFC-0086 §10).
**Not yet built:** the HTTP interface in the twin's service (§3), the
provisioning of `ts_<tenant-id>` and its role, the minutely job and the
CLI — RFC-0086 stage 1's remaining steps.
