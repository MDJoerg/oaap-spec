# oaap.events.bus — Events Between Apps, in the CloudEvents Envelope

- **ID:** `oaap.events.bus`
- **Version:** 0.1
- **Maturity:** draft (0.1: RFC-0127 stage 1 — envelope, catalogue in the
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

Whatever the publisher sends in a platform attribute is **replaced**, never
trusted (RFC-0127 security requirement 1). `oaapto` is reserved for 0.2 and
refused in 0.1 (`400`).

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

The gateway serves on that instance's site `handle /platform/events/*`: it
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
too. Refusals, each with a sentence: `400` (not an object, `oaapto`, a bad
`subject`), `403` (a type the app does not declare under `publishes`),
`409` (an `addressed` type before 0.2), `413` (`data` above 64 KB), `422`
(`data` against the schema, naming the first failing path), `429` (above 120
events a minute per instance; `Retry-After`).

### 2.6 The event store

Two tables in the tenant's twin schema, created by the twin's schema step
(`oaap.data.twin`):

- **`bus_events`** — append-only: `seq` (bigserial, the order), `id` (the
  ULID, unique), `type`, `source_instance`, `source_app`, `subject`, `time`,
  `data` (jsonb), `semantic`, `oaapto` (0.2). A tenant without a twin has no
  store: publishing answers `409` ("this tenant has no twin yet"), the feed
  answers empty. Retention 30 days by default (a later setting per
  tenant); the twin's own `events` table is untouched.
- **`bus_grants`** — one row per grant: `instance`, `type`, `subject_prefix`
  (optional filter), `granted_by`, `granted_at`, `revoked_by`, `revoked_at`.
  A revocation sets the two columns; a new grant is a new row.

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

### 2.8 The feed

```
GET $OAAP_EVENTS_URL/feed?since=<id>&limit=<1..200>
→ 200 {"events": [<CloudEvent>, …], "next": "<id of the last one>"}
```

Returns, in store order, the events of the instance's tenant whose type it
holds a live grant for (and whose `subject` starts with the grant's prefix,
when set), after `since` (exclusive; empty = from the oldest kept). An event
the instance published itself is not returned. `limit` defaults to 100. The
feed is the catch-up behind the push of 0.3 and stays for apps that prefer to
pull.

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

## 6. Dependencies

`oaap.apps.runtime` (manifest 0.21's `events` block, the instance key and its
life), `oaap.core.gateway` (the door), `oaap.core.identity` (the scope check),
`oaap.data.twin` (the schema the store lives in, the service that answers the
door), `oaap.core.tenant` (the tenant audit log for grant and revoke).

## 7. Maturity

`draft` — `beta` once tests 1–5 pass on `oaap-test` and the first pair of
RFC-0127 D12 runs there. Tests 1–5 passed on `oaap-test` on 2026-11-24
(reference 0.1.361, RFC-0127 §1.8); the first pair is step 1.5.

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
