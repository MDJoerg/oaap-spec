# oaap.events.bus — Events Between Apps, in the CloudEvents Envelope

- **ID:** `oaap.events.bus`
- **Version:** 0.6
- **Maturity:** draft (0.6: **the portal page "Ereignisse"** — the
  tenant's administrators see every instance's declared types, the state of
  each subscription and the push, the platform's types, and grant (with an
  optional subject prefix), revoke and resume there; audited in the tenant
  log, §2.13; reference 0.1.369, measured on `oaap-test` 2026-11-24,
  RFC-0127 §1.15. 0.5: **the twin in the envelope** (RFC-0127 D10)
  — `oaap.twin.object.created|changed|retired|statuschanged.v1`, audience
  `tenant`, granted by the tenant admin, copied by the relay only while
  granted, §2.12; reference 0.1.368, measured on `oaap-test` 2026-11-24,
  RFC-0127 §1.14. 0.4: **the platform publishes** — platform types
  in the platform's own catalogue, the first three from identity
  (`oaap.identity.person.activated|locked|unlocked.v1`, addressed to the
  instance that invited the person), the twin's internal door
  `/internal/bus/platform`, and an events block now provisions the tenant's
  store, §2.11; reference 0.1.367, measured on `oaap-test` 2026-11-24,
  RFC-0127 §1.13. 0.3.1: **what the bus keeps under an
  instance's name follows the instance** — removal revokes its grants and
  drops its push cursor and records, a rename carries them over, §2.7;
  found on `oaap-test` 2026-11-24, reference 0.1.364. 0.3: **the push into the app** —
  `events.endpoint`, one signed CloudEvent per POST through the gateway's
  internal listener, in store order, at least once, backoff, stop after 10
  failures, `oaap events resume`; the service `bus`, §2.10; reference
  0.1.363, measured on `oaap-test` 2026-11-24, RFC-0127 §1.10. 0.2: **addressed events** — `oaapto`, the
  platform's own record of who submitted to which case inbox, delivery to
  the named instance only, without a grant, §2.9; the events door serves
  only `/` and `/feed`; reference 0.1.362, measured on `oaap-test`
  2026-11-24, RFC-0127 §1.9. 0.1: RFC-0127 stage 1 — envelope, catalogue in the
  manifest, the publishing door, the tenant's event store, grants, the feed;
  addressed events and the push into the app follow as 0.2 and 0.3 of this
  spec, in the order of RFC-0127 §12.1). Built in reference 0.1.361 and
  measured on `oaap-test` 2026-11-24 (RFC-0127 §1.8).
- **Based on:** RFC-0127 (events as a platform capability, D1–D12),
  CloudEvents 1.0.2 (`specversion` `"1.0"`, JSON format, HTTP structured
  binding), RFC-0061 §3.2 (the door pattern of `cases: {submit: true}`),
  RFC-0027 D5 (instance-scoped keys), `oaap.data.twin` (the tenant schema the
  store lives in), `oaap.events.broker` 0.5 (only platform principals publish
  in a tenant's MQTT tree).

## 1. Purpose

An app says in its manifest which events it **publishes** and which it
**wants**. It publishes through a platform door, never on the broker; the
platform sets who sent it and when, checks it against the declared schema and
keeps it in the tenant's **event store**. A subscriber receives what the
tenant admin **granted** it (and, from 0.2, what was addressed to it). This is
the shape of RFC-0127; the transport underneath (store, feed, later push and
the broker branch) is the platform's.

Out of scope for 0.1: addressed events (`oaapto`, 0.2), the push into the app
(0.3), the broker branch `oaap/<tenant>/events/<type>` (RFC-0127 §9), platform
types (twin, identity — RFC-0127 stage 2), the portal page and the AsyncAPI
export (stage 2), webhooks out and receivers in (stage 3).

## 2. Interface

### 2.1 The envelope (RFC-0127 D1)

Every event the platform keeps or hands out is a CloudEvents 1.0 event in the
JSON format:

| Attribute | Set by | Value |
|---|---|---|
| `specversion` | platform | `"1.0"` |
| `id` | platform | a ULID (26 characters, Crockford base32, sortable by time) |
| `source` | platform | `urn:oaap:tenant:<tenant-id>:instance:<name>` |
| `type` | publisher, checked | a type the publishing app declares (§2.2) |
| `subject` | publisher | 1–200 characters; `urn:oaap:obj:<uuid>` for a twin object, else the publisher's own key |
| `time` | platform | RFC 3339, UTC, when the door accepted it |
| `datacontenttype` | platform | `application/json` |
| `dataschema` | platform | `urn:oaap:events:schema:<app-id>:<type>` |
| `data` | publisher | a JSON object, checked against the type's schema (§2.3) |
| `oaaptenant` | platform | the tenant id |
| `oaaporigin` | platform | `app:<app-id>` |
| `oaapsemantic` | platform, from the catalogue | the type's `semantic_id`, when it declares one |
| `oaapto` | publisher, checked (0.2) | only on an `addressed` type: `instance:<name>`, the one receiver (§2.9) |

Whatever the publisher sends in a platform attribute is **replaced**, never
trusted (RFC-0127 security requirement 1). `oaapto` is the publisher's,
checked against the platform's record (§2.9).

### 2.2 The manifest block `events` (manifest 0.21)

```yaml
events:
  publishes:
    - type: app.vorgaenge.case.statuschanged.v1   # required
      title: "Vorgang hat den Status gewechselt"   # required, ≤ 120
      subject: case                                # what `subject` holds, ≤ 40
      schema: events/case-statuschanged.json       # required, a file in the package
      semantic_id: oaap-aas:Cases/1/0/StatusChanged   # optional
      audience: tenant                             # addressed · tenant · listed
      listed: [bestand]                            # app ids, only with audience listed
      personal: false
  subscribes:
    - type: app.vorgaenge.case.statuschanged.v1    # required
      why: "Rückmeldung zum eigenen Auftrag"        # required, ≤ 200
      addressed_only: true                         # 0.2
  endpoint: /oaap/events                           # 0.3: where the push arrives
```

- **Type names**: `<namespace>.<entity>.<what>.v<major>`, lower case
  `a–z0–9`, 4–8 dot-separated levels, at most 120 characters. An app's own
  types start with `app.<its app id without dashes>.` (a level has no
  dash: `bestand-cds` → `app.bestandcds.`); `oaap.` is the platform's and `ext.`
  belongs to receivers (stage 3) — an app that declares either is refused at
  install. The major version is in the name; a breaking change is a new type.
- **At most 50** published and 50 subscribed types per app; a type appears
  once per list.
- **The schema** is a JSON file in the package, at most 32 KB, in the subset of
  JSON Schema of §2.3. A missing or invalid file refuses the install with the
  path and the reason.
- **`audience`** defaults to `tenant`. `addressed` types are accepted in the
  manifest from 0.1 but publish only from 0.2. `listed` names the app ids that
  may be granted the type.
- A node before manifest 0.21 **skips** the block (the tolerant runtime,
  RFC-0012 §8.2): the app installs without `OAAP_EVENTS_KEY` and without the
  door. An app therefore treats a missing key as "no events here", never as
  an error. A node that knows 0.21 checks the block at install: first its
  shape, then each schema file of the unpacked package; a fault refuses the
  install with the path and the reason.

- **`endpoint`** (0.3) is a path of the app (letters, digits, `. _ ~ - /`, no
  query), allowed only when the app subscribes to something. Without it the
  app pulls the feed.

### 2.3 The schema subset

A type's schema is checked by the platform, not by a library the node has to
install. The subset: `type` (`object`, `array`, `string`, `integer`,
`number`, `boolean`, `null`, or a list of them), `properties`, `required`,
`additionalProperties` (`false` or a schema), `items`, `enum`, `const`,
`minLength`/`maxLength`, `minimum`/`maximum`, `maxItems`, `pattern` (Python
`re`, searched), `description`/`title` (ignored). Any other keyword refuses
the schema at install (a schema the platform cannot check is not checked
silently). `data` must be an object at the top.

### 2.4 The catalogue on the node

At every install, update, promotion, rename and removal the node writes
`events-catalog.json` beside the registry (`/platform-apps` in the platform
services): per instance its tenant, app id, version and the validated
`publishes` (with the schema inline) and `subscribes`. An instance without an
`events` block has no entry. The twin service reads the file at every
request; nothing else is its source.

### 2.5 The key and the door

An instance whose manifest declares `events` gets, like `cases` (RFC-0061
§3.2), at install:

- `OAAP_EVENTS_KEY` — a key of the machine principal `instance:<name>`,
  limited to the scope `oaap.events:<name>`;
- `OAAP_EVENTS_URL` — `http://gateway:<its own port>/platform/events`.

Never for a rehearsal or a probe install. The key follows the instance like
the other instance keys (RFC-0062: removed with it, reissued on rename,
renewed before expiry). An update that drops the `events` block takes both
out of the environment.

The gateway serves on that instance's site exactly `/platform/events`,
`/platform/events/` and `/platform/events/feed` (0.2: nothing else under it
reaches the twin service — anything else is the static `/platform/*`, a 404): it
asks identity for exactly that scope, no roles, and the instance's tenant;
strips the path prefix; sets the source headers (instance, app, version,
tenant) and passes to the twin service at `/bus/v1/…`. The twin service
believes the source only when the principal identity names is
`instance:<the source instance>`.

**Publish:**

```
POST $OAAP_EVENTS_URL/            Content-Type: application/cloudevents+json
                                  (or application/json, the same body)
{ "type": "app.vorgaenge.case.statuschanged.v1", "subject": "V-2026-0042",
  "data": {"case": "V-2026-0042", "from": "open", "to": "in_progress"} }
→ 202 {"id": "01JD…", "type": "…", "time": "…"}
```

Binary mode (`ce-type`, `ce-subject` headers, `data` as the body) is accepted
too (`ce-oaapto` for an addressed one). Refusals, each with a sentence:
`400` (not an object, a bad `subject`, `oaapto` on a type that is not
addressed, an addressed type without a valid `oaapto`), `403` (a type the
app does not declare under `publishes`; an addressee it may not address,
§2.9), `409` (a tenant without a twin), `413` (`data` above 64 KB), `422`
(`data` against the schema, naming the first failing path), `429` (above 120
events a minute per instance; `Retry-After`).

### 2.6 The event store

Two tables in the tenant's twin schema, created by the twin's schema step
(`oaap.data.twin`):

- **`bus_events`** — append-only: `seq` (bigserial, the order), `id` (the
  ULID, unique), `type`, `source_instance`, `source_app`, `subject`, `time`,
  `data` (jsonb), `semantic`, `oaapto` (0.2). A tenant without a twin has no
  store: publishing answers `409` ("this tenant has no twin yet"), the feed
  answers empty. **Since 0.4 installing an instance with an `events` block
  provisions the tenant's twin schema** (idempotent, as a twin binding
  does) — measured 2026-11-24: a tenant whose apps bound no twin had no
  store, and the first platform event to its app was not kept. Retention 30 days by default (a later setting per
  tenant); the twin's own `events` table is untouched.
- **`bus_grants`** — one row per grant: `instance`, `type`, `subject_prefix`
  (optional filter), `granted_by`, `granted_at`, `revoked_by`, `revoked_at`.
  A revocation sets the two columns; a new grant is a new row.
- **`bus_relations`** (0.2) — the record of §2.9: `publisher`, `addressee`,
  `via` (`cases`), `first_at`, `last_at`, `times`; one row per pair.
- **`bus_deliveries`** (0.3) — the push's cursor per instance: `last_seq`,
  `failures`, `next_at`, `stopped_at`, `last_error`, `delivered`,
  `last_ok_at`; bookkeeping, the one bus table that is updated.

### 2.7 Grants (RFC-0127 D4)

A declared subscription delivers nothing until the tenant admin grants it.
In 0.1 on the node's command line (the portal page is RFC-0127 stage 2):

```
oaap events list   [--tenant <t>]                 # types, publishers, wishes, grants
oaap events grant  <instance> <type> [--subject-prefix <p>]
oaap events revoke <instance> <type>
```

A grant needs the instance to declare the type under `subscribes`, a
publisher of the type in the same tenant, and — for `listed` — the
subscriber's app id in the publisher's list. Every grant and revocation is
written to the tenant's audit log (`events.grant`, `events.revoke`). A
revocation stops the feed at once (§2.8).

**Grants follow the instance (0.3.1).** Removing an instance revokes its
live grants (`revoked_by` = `oaap (instance removed)`) and deletes its push
cursor (§2.10) and its records (§2.9); renaming it carries all three to the
new name. An instance installed again under a removed one's name starts
with nothing — the RFC-0062 rule for keys, applied to grants (measured on
`oaap-test` 2026-11-24: before 0.3.1 such an instance found its
predecessor's grant live).

### 2.8 The feed

```
GET $OAAP_EVENTS_URL/feed?since=<id>&limit=<1..200>
→ 200 {"events": [<CloudEvent>, …], "next": "<id of the last one>"}
```

Returns, in store order, the events of the instance's tenant whose type it
holds a live grant for (and whose `subject` starts with the grant's prefix,
when set) — and, from 0.2, the events **addressed to it** of a type it
declares under `subscribes`, without a grant — after `since` (exclusive;
empty = from the oldest kept). An event the instance published itself is not
returned; an addressed event never reaches anyone but its addressee, a grant
for the type included (grants on an addressed type are refused). `limit` defaults to 100. The
feed is the catch-up behind the push of 0.3 and stays for apps that prefer to
pull.

### 2.9 Addressed events (0.2, RFC-0127 §6.2, D5)

An `addressed` type reaches exactly one instance, the one `oaapto` names. The
publisher may name only an instance that **gave it something to address**,
and the platform decides that from **its own record**, never from what the
publisher says (Jörg, 2026-11-24: the case door records the pair):

- **The record.** The case door of an instance's site
  (`/platform/cases/submit`, RFC-0061 §3.2) asks, after identity has
  accepted that instance's own case key, a second question: `forward_auth`
  to the twin service at `/bus/v1/relate?from=<submitting instance>&to=<the
  inbox it passes to>`. The twin service checks that identity's principal is
  `instance:<from>` and both are instances of one tenant, and writes or
  counts the row (`publisher` = the inbox, `addressee` = the submitter,
  `via` = `cases`). It copies nothing back and answers 200 even when it
  cannot write (no twin, a database fault — logged): a case is never stopped
  by the record; the addressed event is refused later instead, visibly. The
  case request itself reaches the inbox unchanged.
- **The check at publish.** For an addressed type: `oaapto` is
  `instance:<name>`; `<name>` is an instance of the publisher's tenant that
  declares the type under `subscribes`; and the record holds the pair
  (publisher, `<name>`). Otherwise `403` with the reason.
- **Delivery.** The event is stored with `oaapto` and returned only in the
  addressee's feed (§2.8), without a grant; it is never part of a granted
  feed and never goes onto the broker branch (RFC-0127 §9).

In 0.2 the only source of the record is the case door — that is the pair
RFC-0127 D12 begins with. A further source (identity for an invitation,
RFC-0126) adds a `via`, not a new rule.

### 2.10 The push into the app (0.3, RFC-0127 D6)

An instance whose manifest declares `events.endpoint` receives what its feed
would return (§2.8 — granted and addressed, the same rule in one function),
pushed:

- **Who pushes.** The platform service `bus` (the twin's image, its own
  command, like the webhook service). It reads the catalogue, the signing
  secrets (`events-secrets.json`, root only, written from the instances'
  environment with every registry save) and each tenant's store.
- **How it reaches the app.** Through the gateway's internal listener, which
  answers the platform network only: `POST gateway:8099/e/<instance>` is
  rewritten to the declared path and passed to the service that owns it,
  inside the instance's own network; no identity header passes. Never the
  internet, never a public name.
- **What arrives.** One event per POST, the CloudEvents HTTP structured
  binding (`Content-Type: application/cloudevents+json`, the event of §2.1 as
  the body), `X-OAAP-Event-Id`, and `X-OAAP-Signature: t=<unix>,v1=<hex>`,
  HMAC-SHA256 with the instance's **`OAAP_EVENTS_SECRET`** over `<t>.<body>`
  (the twin webhooks' form). The app recomputes it, refuses a stale `t` (5
  minutes), answers 2xx, and is idempotent by `id`. `OAAP_EVENTS_SECRET` is
  minted once at install for an app with an endpoint (a reserved name).
- **Order and repetition.** Strictly in store order per instance (so also per
  subject); the cursor moves only after a 2xx, the next event waits. A failure
  waits 2^n seconds, at most an hour; after 10 failures in a row the push
  **stops** with the reason (`oaap events list` shows it) until
  `oaap events resume <instance>` (audited `events.resume`); the feed still
  serves meanwhile.
- **Where it starts.** An instance the service sees for the first time starts
  at the store's newest event; the past is the feed's.

### 2.11 Platform types (0.4, RFC-0127 stage 2)

The platform publishes in the same envelope and the same store. Its types are
in the **platform catalogue** (in the reference: `bus_model.PLATFORM_TYPES`),
not in a manifest; an app subscribes to them under `events.subscribes` like
to any other type, and a subscription to an `oaap.` type the platform does
not know is refused at install.

| Type | Publisher | Audience | `subject` | `data` |
|---|---|---|---|---|
| `oaap.identity.person.activated.v1` | identity | addressed | the person's user id | `user_id`, `ref` |
| `oaap.identity.person.locked.v1` | identity | addressed | the person's user id | `user_id`, `ref`, `by` (`app` · `admin`) |
| `oaap.identity.person.unlocked.v1` | identity | addressed | the person's user id | `user_id`, `ref`, `by` (`app` · `admin`) |

- **Meaning** (RFC-0126, Jörg 2026-11-24): *activated* is the person's
  **first login** through the tenant's place — not merely a set password;
  identity sees it without asking the realm. *locked* / *unlocked* follow a
  real change of the person's state, by the inviting app (`/people/v1/<id>/
  lock|unlock`) or by a tenant admin (portal, `by: admin`); repeating a lock
  that holds already says nothing. `ref` is the app's own reference from
  the invitation. No address and no name travel (thin, §8 of RFC-0127).
- **Who receives.** Only the instance that invited the person — the
  platform's own record `invited_by` is the relation (RFC-0127 §6.1's
  second case), so no grant exists or is needed for these types; a person
  no app invited produces no event.
- **The envelope.** `source` `urn:oaap:tenant:<tid>:identity`, `oaaporigin`
  `platform:identity`, `dataschema` `urn:oaap:events:schema:platform:<type>`,
  `oaapsemantic` from the platform catalogue, `oaapto` the inviting
  instance. Stored with `source_instance` `platform:<publisher>`, a value no
  instance name can take, so the feed's and the push's rule ("never its
  own") is unchanged.
- **The way in.** A platform service hands an event to the twin's
  **internal door** `POST /internal/bus/platform` with the platform key (the
  twin's `/internal/*` guard), body `{tenant, publisher, type, subject,
  data, to}`; never through the gateway. The door checks the type against
  the platform catalogue (`403` for another publisher or an app type), the
  schema (`422`), the addressee (same tenant, declares the type); an event
  nobody declared, or for a tenant without a store, answers `200` with
  `stored: false` and is not kept.
- **identity's outbox.** identity holds no database: it writes each event to
  `bus-outbox.json` first, then hands the queue to the door oldest first; it
  stops at the first event the twin cannot take yet (down, restarting) so
  the order per person holds, and tries again every 30 seconds; a refusal
  (4xx) is final and logged; items older than 7 days are dropped.

### 2.12 The twin in the envelope (0.5, RFC-0127 D10)

| Type | From the twin's kinds | `data` |
|---|---|---|
| `oaap.twin.object.created.v1` | `object.created` | `type`, `group`, `origin` |
| `oaap.twin.object.changed.v1` | `group.written`, `period.written`, `object.renamed`, `object.merged`, `object.unmerged` | `type`, `group`, `origin`, `change` (the kind) |
| `oaap.twin.object.retired.v1` | `object.retired` | `type`, `origin` |
| `oaap.twin.object.statuschanged.v1` | `status.changed` | `type`, `origin`, `from`, `to` |

- **Envelope.** `source` `urn:oaap:tenant:<tid>:twin`, `subject` the object
  URN `urn:oaap:obj:<uuid>`, **`oaaporigin` the origin as the twin names it**
  (`app:<id>`, `client:<label>`, `model:<id>`, …), `oaapsemantic` the
  semantic ID of the group's type, else of the object type, from the model
  registry (absent when neither declares one). Thin: no values; a status
  carries from/to but not the reason (free text). `type.created` has no
  event.
- **Audience `tenant`.** An app declares the types under `events.subscribes`;
  the tenant admin grants them (`oaap events grant`), optionally with a
  subject prefix. No publisher instance exists or is needed.
- **Copied only while granted** (Jörg, 2026-11-24). The relay (`oaap.data.twin`
  §2.13) writes a twin row into the store only while some instance of the
  tenant holds a live grant for its type, in the same transaction that moves
  its watermark — exactly once. An instance granted later sees events from
  then on; the twin's own change feed (`/twin/v1`) remains the way to read
  the past. Without the broker profile there is no relay and so no copy.

### 2.13 The portal page "Ereignisse" (0.6, RFC-0127 §6.1)

- **Who.** A `tenant_admin` of the tenant, and a `server_admin` in the
  tenant's context; the entry sits in the side bar under "Katalog & Daten".
  Anyone else gets `403`, and the entry is not shown.
- **What it shows.** Per instance with an `events` block: its app and
  version; the push (not started · delivered n · failures with the last
  error · stopped, with "Fortsetzen"); every subscribed type with its *why*
  and state — *granted* (by whom, the subject prefix), *addressed* (the
  app's own addressed type, no grant), *addressed by `<publisher>`* (an
  addressed platform type, no grant), *waiting* (with "Freigeben" when
  `grant_error` allows it, else its sentence); every published type with
  its meaning and audience. Below, the platform's types.
- **What it does.** Grant (optionally limited to subjects starting with a
  prefix, at most 200 printable characters), revoke, resume — the same rules
  as `oaap events grant|revoke|resume`, through the twin's internal routes
  `GET /internal/bus/overview` and `POST /internal/bus/grant|revoke|resume`
  (the portal relays the signed-in person; the twin checks the role and that
  the instance belongs to that person's tenant). `granted_by` / `revoked_by`
  name the person.
- **The record.** Each action is a line in the tenant audit log
  (`events.grant|revoke|resume`, who, the instance and type, the prefix),
  written by the twin, which mounts the audit directory to append — the
  third appender after appctl and identity.

## 3. Configuration

None in 0.1 beyond the manifest. The limits (64 KB, 120 a minute, 30 days)
are constants of the reference; they become tenant settings when a tenant
needs another value.

## 4. Security requirements

1. A publisher cannot set `id`, `source`, `time`, `dataschema`, `oaaptenant`,
   `oaaporigin` or `oaapsemantic`; tested by sending them.
2. An app publishes only the types it declares; an undeclared type is `403`.
3. No event crosses tenants: the store is the tenant's schema, the feed reads
   only it, a grant names only instances of that tenant.
4. A subscription delivers only after a grant; a revoked grant stops the feed
   at the next request.
5. Only the key scoped to `oaap.events:<name>` opens the door on `<name>`'s
   site; a person's session, another instance's key and an unscoped key are
   refused by identity before the twin service sees the request.
6. An app cannot publish on the broker (`oaap.events.broker` 0.5).
8. (0.3) The push reaches an app only through the internal listener, which
   refuses callers outside the platform network; every push is signed with
   the instance's own secret.
7. An addressed event reaches only the instance it names, and only an
   instance the platform's record shows submitting to the publisher; tested
   with no record, another tenant's instance and an instance that does not
   declare the type (0.2).
9. (0.4) Only a platform service holding the platform key publishes a
   platform type, and only its own types; an app cannot publish under
   `oaap.` (refused at install, `own_type_error`) nor reach the internal
   door (the gateway never serves `/internal/*`). An identity event about a
   person reaches only the instance that invited that person.

## 5. Conformance tests (described)

1. A probe app declaring one type publishes; the answer is `202` with an id;
   the stored event carries the platform's `source`, `time` and `oaaptenant`
   although the app sent others.
2. An undeclared type is `403`; `data` violating the schema is `422` naming
   the path; 65 KB of `data` is `413`; the 121st event within a minute is `429`.
3. A second probe app declaring the type under `subscribes` reads an empty
   feed; after `oaap events grant` it reads the event; after `revoke` it reads
   nothing new.
4. The same with the second app in another tenant: the grant is refused.
5. The door on the first app's site refuses the second app's key and a
   logged-in person.
6. (0.2) An instance opens a case through its case door; the record holds
   (inbox, instance), a second case counts it. An addressed event without
   a record is `403`; with one it reaches the addressee's feed without a
   grant and no other feed, a grant on another type included.
7. (0.3) With an endpoint and a grant, three published events arrive at the
   app once each, in order, signed; an addressed one too. The app answering
   503, and its container stopped, hold the cursor; afterwards the events
   arrive once, in order. Ten failures stop the push; `resume` delivers what
   waited. An app container calling `gateway:8099/e/<other>` gets 403.

## 6. Dependencies

`oaap.apps.runtime` (manifest 0.21's `events` block, the instance key and its
life), `oaap.core.gateway` (the door), `oaap.core.identity` (the scope check),
`oaap.data.twin` (the schema the store lives in, the service that answers the
door), `oaap.core.tenant` (the tenant audit log for grant and revoke).

## 7. Maturity

`draft` — `beta` once tests 1–5 pass on `oaap-test` and the first pair of
RFC-0127 D12 runs there. Tests 1–5 passed on `oaap-test` on 2026-11-24
(reference 0.1.361, RFC-0127 §1.8); test 6 on 2026-11-24 (0.1.362, §1.9);
the first pair is step 1.5.

## Deutsche Zusammenfassung (v0.1)

Diese Spec ist die erste Ausbaustufe des Ereignisbusses aus RFC-0127. Eine
App erklärt im Manifest (Version 0.21, Block `events`), welche Ereignisse sie
veröffentlicht, jedes mit Name, Titel und JSON-Schema im Paket. Sie erklärt
auch, welche sie empfangen möchte und warum. Veröffentlicht wird über eine
Tür der Plattform auf der eigenen Seite der Instanz: `POST
$OAAP_EVENTS_URL/` mit einem eigenen, auf diese Instanz beschränkten
Schlüssel, nach dem Muster der Vorgangstür. Die Plattform prüft Typ und
Schema. Absender, Zeit, Kennung und Mandant setzt sie selbst. Dann legt sie
das Ereignis im CloudEvents-Format in der Ereignisablage des Mandanten ab,
einer neuen Tabelle im Zwilling-Schema. Empfangen darf eine App nur, was der
Mandanten-Admin freigegeben hat. In 0.1 geschieht das über die Kommandozeile
(`oaap events grant/revoke/list`), die Portalseite kommt mit Stufe 2.
Abgeholt wird über einen Feed (`GET $OAAP_EVENTS_URL/feed?since=`).
Adressierte Ereignisse (0.2) und die Zustellung per Push in die App (0.3)
folgen als nächste Schritte von Stufe 1.

## Deutsche Zusammenfassung (Nachtrag v0.2)

0.2 bringt adressierte Ereignisse. Ein Typ mit `audience: addressed` geht an
genau eine Instanz, die `oaapto` nennt. Adressieren darf eine App nur eine
Instanz, die ihr vorher etwas gegeben hat. Das weiß die Plattform aus einer
eigenen Aufzeichnung, so wie du es entschieden hast: Reicht eine Instanz über
ihre Vorgangstür einen Vorgang ein, stellt das Gateway nach identity eine
zweite Frage an den Zwilling. Der merkt sich das Paar „Posteingang →
Einreicher“ (eine Zeile je Paar, danach wird gezählt). Die Einreichung selbst
läuft unverändert weiter, auch wenn die Aufzeichnung einmal nicht klappt.
Adressierte Ereignisse brauchen keine Freigabe und erscheinen nur im Feed des
Empfängers. Die Ereignistür lässt jetzt nur noch `/` und `/feed` durch.

## Deutsche Zusammenfassung (Nachtrag v0.3)

0.3 bringt den Push. Eine App nennt im Manifest einen Pfad
(`events.endpoint`). Ein neuer Plattformdienst `bus` schickt ihr dann jedes
freigegebene oder an sie adressierte Ereignis einzeln dorthin, im
CloudEvents-Format und mit einem Geheimnis signiert, das nur die Instanz
kennt (`OAAP_EVENTS_SECRET`). Der Weg führt über den internen Listener des
Gateways, also nur innerhalb des Knotens, nie übers Internet. Die Reihenfolge
bleibt erhalten, und jedes Ereignis kommt mindestens einmal an. Antwortet die
App nicht, wartet der Dienst immer länger (höchstens eine Stunde). Nach zehn
Fehlschlägen in Folge hält er an, bis jemand `oaap events resume` aufruft.
Der Feed bleibt daneben bestehen, zum Nachholen und für Apps, die lieber
selbst abholen.

## Deutsche Zusammenfassung (Nachtrag v0.3.1)

Was der Bus unter dem Namen einer Instanz festhält, folgt jetzt der Instanz:
Freigaben, der Stand des Pushs und die Einträge, wer wen adressieren darf.
Wird die Instanz entfernt, werden ihre Freigaben widerrufen und der Rest
gelöscht. Wird sie umbenannt, ziehen alle drei mit um. Gefunden auf
oaap-test: Eine neu installierte Probe mit dem Namen einer entfernten fand
deren Freigabe noch vor.

## Deutsche Zusammenfassung (Nachtrag v0.4)

Mit 0.4 veröffentlicht auch die Plattform selbst Ereignisse, im selben
Umschlag und im selben Speicher. Die ersten drei kommen von identity:
`activated` (eine von einer App eingeladene Person meldet sich zum ersten
Mal an), `locked` und `unlocked` (die App oder der Mandantenadmin sperrt
oder entsperrt sie, mit Angabe, wer es war). Sie gehen nur an die
einladende Instanz und brauchen deshalb keine Freigabe. Adresse und Name
reisen nicht mit, nur die Benutzer-ID und die eigene Referenz der App.
identity schreibt jedes Ereignis zuerst in eine kleine Ausgangsdatei und
liefert es dann über eine interne Tür des Zwillings ein. Ist der Zwilling
gerade nicht da, bleibt es liegen und geht später in der richtigen
Reihenfolge raus. Neu ist außerdem: Wird eine App mit `events`-Block
installiert, legt der Knoten den Ereignisspeicher des Mandanten an. Ohne
das ging auf oaap-test das erste Ereignis verloren.

## Deutsche Zusammenfassung (Nachtrag v0.5)

Der Zwilling spricht jetzt im selben Umschlag. Das Relais schreibt seine
Änderungen als `oaap.twin.object.created`, `changed`, `retired` und
`statuschanged` in den Ereignisspeicher des Mandanten, mit der Objekt-URN als
Betreff, der Herkunft so, wie der Zwilling sie nennt (`app:…`, `client:…`),
und der Semantik-ID des Typs. Werte reisen nicht mit. Eine App muss die Typen
erklären, und der Mandantenadmin muss sie freigeben. Kopiert wird nur,
solange eine Freigabe besteht (Jörgs Entscheidung). Was niemand hört, bleibt
allein im Journal des Zwillings. Kopie und Wasserstand des Relais stehen in
einer Transaktion, deshalb landet jede Änderung genau einmal im Speicher.
Die bisherigen MQTT-Nachrichten des Zwillings bleiben unverändert.

## Deutsche Zusammenfassung (Nachtrag v0.6)

Das Portal hat jetzt die Seite „Ereignisse“ (unter „Katalog & Daten“), nur für
die Admins des Mandanten. Sie zeigt je App, was sie veröffentlicht und was sie
empfangen möchte, mit Begründung und Stand, dazu den Stand der Zustellung.
Freigeben (auf Wunsch nur für Betreffe mit einem bestimmten Anfang),
Widerrufen und eine angehaltene Zustellung fortsetzen gehen dort mit einem
Klick, nach denselben Regeln wie auf der Kommandozeile. Jede dieser Aktionen
steht mit Namen im Protokoll des Mandanten. Darunter stehen die Ereignisse der
Plattform selbst.
